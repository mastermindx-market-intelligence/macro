"""Prospective issuance writer for the Grey Deer SPY pullback forward log.

Synthetic closes only. Clock and HEAD are monkeypatched. Ledger files go to
``tmp_path``. No price store, no network, no repo ``data/`` write.

Run from the repo root:
    python3 -m pytest tests/test_grey_deer_pullback_forward.py -rA -q
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib.nyse_calendar import ET, is_session
from scripts.research import grey_deer_pullback_stage1 as s1

import engine.grey_deer_pullback_forward as fwd

ISSUE_FIELDS = {
    "schema",
    "evidence_class",
    "asof",
    "ticker",
    "horizon",
    "config_id",
    "population",
    "kind",
    "is_gate",
    "probability",
    "quantile",
    "abstention_reason",
    "inputs_digest",
    "code_sha",
    "recipe_fingerprint",
    "prereg_blob",
    "prereg_path",
    "issued_at",
    "writer_lane",
    "writer_identity",
    "collect_lane_env",
    "backfill",
    "rerun",
    "intraday",
    "fit_block_id",
    "training_end_asof",
    "issue_receipt",
    "realized_A",
    "Y",
    "graded_at",
    "grader_sha",
}
REFUSAL_FIELDS = {
    "schema",
    "refused_at",
    "reason",
    "asof",
    "ticker",
    "horizon",
    "config_id",
    "writer_lane",
    "attempt_digest",
}
ISSUED_IDS = (
    "B0",
    "B1-20",
    "B1-63",
    "B2-21",
    "B2-63",
    "M3-ALL@C=1.0",
    "M3-ALL@C=0.1",
    "Q0",
    "Q1",
    "Q3-ALL",
)
GATE_IDS = frozenset({"M3-ALL@C=1.0", "Q3-ALL"})
HEAD = "a" * 40
STORE = "synthetic-store-v1"


def _at(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """ET civil time as an aware UTC instant (the writer's clock contract)."""
    return datetime(year, month, day, hour, minute, tzinfo=ET).astimezone(timezone.utc)


def _sessions_from(start: date, n: int) -> list[date]:
    out: list[date] = []
    day = start
    while len(out) < n:
        if is_session(day):
            out.append(day)
        day += timedelta(days=1)
        if day.year > start.year + 30:
            raise RuntimeError(f"not enough sessions after {start}")
    return out


def _sessions_ending(end: date, n: int) -> list[date]:
    out: list[date] = []
    day = end
    while len(out) < n:
        if is_session(day):
            out.append(day)
        day -= timedelta(days=1)
        if day.year < 1990:
            raise RuntimeError(f"not enough sessions before {end}")
    out.reverse()
    if out[-1] != end:
        raise RuntimeError(f"{end} is not a session")
    if out[0] < date.fromisoformat(s1.WINDOW_START):
        raise RuntimeError(f"series starting {out[0]} precedes WINDOW_START")
    return out


def _gbm_prices(n: int, seed: int) -> np.ndarray:
    """Seeded GBM with clustered volatility and occasional gaps down."""
    rng = np.random.default_rng(seed)
    log_sig = np.empty(n)
    log_sig[0] = math.log(0.01)
    for i in range(1, n):
        log_sig[i] = 0.92 * log_sig[i - 1] + 0.08 * math.log(0.01) + float(rng.normal(0.0, 0.25))
    sigma = np.exp(np.clip(log_sig, math.log(0.004), math.log(0.08)))
    rets = rng.normal(0.0, 1.0, n) * sigma
    crash = rng.random(n) < 0.03
    rets = rets - crash * rng.uniform(0.06, 0.14, n)
    rets[0] = 0.0
    return 400.0 * np.exp(np.cumsum(rets))


def _rising_prices(n: int, seed: int) -> np.ndarray:
    """Strictly positive daily moves, so forward-max-loss events do not occur."""
    rng = np.random.default_rng(seed)
    rets = np.abs(rng.normal(0.0008, 0.0004, n))
    rets[0] = 0.0005
    return 100.0 * np.exp(np.cumsum(rets))


def _series(dates: list[date], prices: np.ndarray) -> pd.Series:
    index = pd.DatetimeIndex(pd.to_datetime([day.isoformat() for day in dates]))
    return pd.Series(np.asarray(prices, dtype=float), index=index)


def _arm(monkeypatch, when: datetime, head: str = HEAD) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setenv("GREY_DEER_PULLBACK_WRITER_IDENTITY", "daily.yml:engine")
    monkeypatch.setattr(fwd, "_utc_now", lambda: when)
    monkeypatch.setattr(fwd, "_git_head", lambda: head)


def _read_jsonl(path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _assert_refusal_schema(row: dict) -> None:
    assert "probability" not in row
    assert "quantile" not in row
    if row["reason"] == "OBSERVER_NOT_ON_MAIN":
        assert set(row) == REFUSAL_FIELDS | {"population"}
        assert row["population"] == "P-active"
        assert row["horizon"] is None
        assert row["config_id"] is None
    else:
        assert set(row) == REFUSAL_FIELDS
    assert row["schema"] == fwd.REFUSAL_SCHEMA
    assert len(row["attempt_digest"]) == 64
    assert len(row["refused_at"]) == 25
    assert row["refused_at"].endswith("+00:00")


def _stage_id(issued_id: str) -> str:
    if issued_id == "M3-ALL@C=1.0":
        return "M3-ALL"
    if issued_id == "M3-ALL@C=0.1":
        return "M3-ALL-C0.1"
    return issued_id


def _compare_to_fits(scored: list[dict], fits: dict, close: pd.Series, t: int, h: int, block_i: int) -> dict:
    """Compare one horizon at row ``t`` and return tallies for the caller."""
    by_id = {row["config_id"]: row for row in scored if row["horizon"] == h}
    assert set(by_id) == set(ISSUED_IDS)
    tally = {"abstained": 0, "binary": 0, "quantile": 0}
    for issued_id, row in by_id.items():
        stage_id = _stage_id(issued_id)
        entry = fits["fits"][(h, block_i, stage_id)]
        s0 = int(entry["block"][0])
        pos = t - s0
        assert entry["block"][0] <= t <= entry["block"][1]
        issued = bool(entry["issued"][pos])
        reason = entry["reasons"][pos]
        reason = None if reason is None else str(reason)
        assert row["fit_block_id"] == f"b{block_i}"
        assert row["training_end_asof"] == pd.Timestamp(close.index[s0 - h]).strftime("%Y-%m-%d")
        assert row["kind"] == entry["kind"]
        assert row["population"] == "P-all"
        assert row["is_gate"] is (issued_id in GATE_IDS)
        if issued:
            assert row["abstention_reason"] is None
            if entry["kind"] == "binary":
                assert row["quantile"] is None
                assert row["probability"] == pytest.approx(float(entry["p"][pos]), abs=1e-12)
                tally["binary"] += 1
            else:
                assert row["probability"] is None
                for key in ("0.5", "0.8", "0.9"):
                    assert row["quantile"][key] == pytest.approx(float(entry["q"][key][pos]), abs=1e-12)
                tally["quantile"] += 1
        else:
            assert row["probability"] is None
            assert row["quantile"] is None
            assert row["abstention_reason"] == reason
            tally["abstained"] += 1
    return tally


# ── T1 ───────────────────────────────────────────────────────────────────────


def test_t1_score_asof_matches_run_fits():
    """Parity on >=6 asofs x 3 horizons x 10 configs, non-final blocks only."""
    n = 1050
    dates = _sessions_from(date.fromisoformat(s1.WINDOW_START), n)
    close = _series(dates, _gbm_prices(n, seed=20261013))
    labels = s1.build_labels(close)
    features = s1.build_features(close)
    fits = s1.run_fits(close, labels, features)

    # Final-block length >= 63 at every horizon, so stage 1 does not merge and
    # the prospective block id lines up with run_fits on the early blocks.
    picked: list[int] = []
    for block_i in (1, 2, 3):
        s0 = s1.FIRST_TEST_IDX + s1.BLOCK_LEN * (block_i - 1)
        picked.extend((s0, s0 + s1.BLOCK_LEN // 2))
    assert len(picked) >= 6

    blocks_seen = {h: set() for h in s1.HORIZONS}
    tally = {"abstained": 0, "binary": 0, "quantile": 0}
    compared = 0
    for t in picked:
        scored = fwd.score_asof(close.iloc[: t + 1])
        assert len(scored) == len(s1.HORIZONS) * len(ISSUED_IDS)
        for h in s1.HORIZONS:
            calendar = s1.fold_calendar_for_population(len(close), h)
            assert len(calendar) >= 4
            host = None
            for block_i, (s0, e0) in enumerate(calendar, start=1):
                if s0 <= t <= e0:
                    host = (block_i, s0, e0)
                    break
            assert host is not None
            block_i, s0, e0 = host
            assert block_i < len(calendar)  # non-final
            assert (e0 - s0 + 1) == s1.BLOCK_LEN
            blocks_seen[h].add(block_i)
            part = _compare_to_fits(scored, fits, close, t, h, block_i)
            for key, count in part.items():
                tally[key] += count
            compared += len(ISSUED_IDS)
    for h, seen in blocks_seen.items():
        assert len(seen) >= 3, h
    assert compared >= 6 * 3 * 10
    assert tally["binary"] >= 1
    assert tally["quantile"] >= 1

    # Force TRAINING_FOLD_THIN: a rising path has no loss events, so every
    # config except B0 abstains. Still has to match run_fits.
    thin_n = 800
    thin_dates = _sessions_from(date.fromisoformat(s1.WINDOW_START), thin_n)
    thin_close = _series(thin_dates, _rising_prices(thin_n, seed=11))
    thin_labels = s1.build_labels(thin_close)
    thin_features = s1.build_features(thin_close)
    thin_fits = s1.run_fits(thin_close, thin_labels, thin_features)
    t = s1.FIRST_TEST_IDX + 10
    thin_scored = fwd.score_asof(thin_close.iloc[: t + 1])
    for h in s1.HORIZONS:
        calendar = s1.fold_calendar_for_population(len(thin_close), h)
        block_i = next(i for i, (s0, e0) in enumerate(calendar, start=1) if s0 <= t <= e0)
        assert block_i < len(calendar)
        part = _compare_to_fits(thin_scored, thin_fits, thin_close, t, h, block_i)
        assert part["abstained"] >= 1
        reasons = {
            row["abstention_reason"]
            for row in thin_scored
            if row["horizon"] == h and row["config_id"] != "B0"
        }
        assert reasons == {"TRAINING_FOLD_THIN"}
        b0 = next(row for row in thin_scored if row["horizon"] == h and row["config_id"] == "B0")
        assert b0["abstention_reason"] is None
        assert b0["probability"] is not None
        tally["abstained"] += part["abstained"]
    assert tally["abstained"] >= 1


def test_t1_short_series_is_a_programming_error():
    dates = _sessions_from(date(2024, 1, 2), 30)
    close = _series(dates, _gbm_prices(30, seed=3))
    with pytest.raises(ValueError, match="FIRST_TEST_IDX"):
        fwd.score_asof(close)


# ── T2 ───────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("lane", [None, "render", "us", "Nightly"])
def test_t2_off_lane_writes_nothing(tmp_path, monkeypatch, lane):
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("GREY_DEER_PULLBACK_WRITER_IDENTITY", raising=False)
    if lane is not None:
        monkeypatch.setenv("COLLECT_LANE", lane)
    # A legacy alias must not arm this ledger.
    monkeypatch.setenv("US_LANE", "nightly")
    out = tmp_path / "out"
    close = _series([date(2024, 6, 3)], np.array([100.0]))
    result = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=out)
    assert not out.exists()
    assert list(tmp_path.iterdir()) == []
    _assert_refusal_schema(result)
    assert result["reason"] == "LANE"
    assert result["writer_lane"] == ("absent" if lane is None else lane)
    assert result["horizon"] is None
    assert result["config_id"] is None


def test_t2_bad_identity_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.delenv("GREY_DEER_PULLBACK_WRITER_IDENTITY", raising=False)
    out = tmp_path / "out"
    close = _series([date(2024, 6, 3)], np.array([100.0]))
    missing = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=out)
    assert not out.exists()
    _assert_refusal_schema(missing)
    assert missing["reason"] == "IDENTITY"
    assert missing["writer_lane"] == "nightly"

    monkeypatch.setenv("GREY_DEER_PULLBACK_WRITER_IDENTITY", "someone-else")
    # US_LANE set to a non-nightly value must not, by itself, refuse a nightly collect.
    monkeypatch.setenv("US_LANE", "render")
    wrong = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=out)
    assert not out.exists()
    assert wrong["reason"] == "IDENTITY"


# ── T3 ───────────────────────────────────────────────────────────────────────


def _long_ending(end: date, n: int = 400, seed: int = 5) -> pd.Series:
    return _series(_sessions_ending(end, n), _gbm_prices(n, seed=seed))


def test_t3_issue_window(tmp_path, monkeypatch):
    monday = date(2024, 6, 3)
    assert monday.weekday() == 0 and is_session(monday)
    close = _long_ending(monday, seed=21)

    _arm(monkeypatch, _at(2024, 6, 3, 20, 0))
    ok = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=tmp_path / "mon_ok")
    assert ok["issued"] == 30
    assert ok["duplicates"] == 0
    assert ok["refusals"] == ["OBSERVER_NOT_ON_MAIN"]
    issued = _read_jsonl(tmp_path / "mon_ok" / fwd.FORWARD_LOG_NAME)
    refused = _read_jsonl(tmp_path / "mon_ok" / fwd.REFUSAL_LOG_NAME)
    assert len(issued) == 30
    assert len(refused) == 1
    assert {row["asof"] for row in issued} == {"2024-06-03"}

    _arm(monkeypatch, _at(2024, 6, 3, 16, 30))
    early = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=tmp_path / "early")
    assert early["issued"] == 0
    assert early["refusals"] == ["CLOCK"]
    early_rows = _read_jsonl(tmp_path / "early" / fwd.REFUSAL_LOG_NAME)
    assert early_rows[0]["refused_at"] == _at(2024, 6, 3, 16, 30).astimezone(timezone.utc).isoformat(timespec="seconds")
    assert not (tmp_path / "early" / fwd.FORWARD_LOG_NAME).exists()

    _arm(monkeypatch, _at(2024, 6, 4, 10, 0))
    late_morning = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=tmp_path / "tue_am")
    assert late_morning["refusals"] == ["CLOCK"]

    _arm(monkeypatch, _at(2024, 6, 4, 20, 0))
    stale = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=tmp_path / "tue_pm")
    assert stale["refusals"] == ["BACKFILL_ASOF"]
    assert not (tmp_path / "tue_pm" / fwd.FORWARD_LOG_NAME).exists()

    friday = date(2024, 6, 7)
    assert friday.weekday() == 4 and is_session(friday)
    friday_close = _long_ending(friday, seed=22)
    _arm(monkeypatch, _at(2024, 6, 8, 3, 0))
    weekend = fwd.issue(friday_close, ticker="SPY", store_identity=STORE, out_dir=tmp_path / "fri")
    assert weekend["issued"] == 30
    assert weekend["refusals"] == ["OBSERVER_NOT_ON_MAIN"]
    assert {row["asof"] for row in _read_jsonl(tmp_path / "fri" / fwd.FORWARD_LOG_NAME)} == {"2024-06-07"}

    # Spring-forward boundary: Friday 2026-03-06 is still EST; the next open
    # is Monday 2026-03-09 at 09:30 EDT. Saturday 03:00 ET is inside the window.
    dst_asof = date(2026, 3, 6)
    assert dst_asof.weekday() == 4 and is_session(dst_asof)
    assert is_session(date(2026, 3, 9))
    dst_close = _long_ending(dst_asof, seed=23)
    _arm(monkeypatch, _at(2026, 3, 7, 3, 0))
    dst = fwd.issue(dst_close, ticker="SPY", store_identity=STORE, out_dir=tmp_path / "dst")
    assert dst["issued"] == 30
    assert dst["refusals"] == ["OBSERVER_NOT_ON_MAIN"]

    holiday = date(2024, 7, 4)
    assert not is_session(holiday)
    holiday_close = pd.Series([101.0], index=pd.to_datetime(["2024-07-04"]))
    _arm(monkeypatch, _at(2024, 7, 4, 20, 0))
    hol = fwd.issue(holiday_close, ticker="SPY", store_identity=STORE, out_dir=tmp_path / "hol")
    assert hol["refusals"] == ["NOT_A_SESSION"]
    assert _read_jsonl(tmp_path / "hol" / fwd.REFUSAL_LOG_NAME)[0]["asof"] == "2024-07-04"

    weekend_bar = pd.Series([102.0], index=pd.to_datetime(["2024-07-06"]))
    assert date(2024, 7, 6).weekday() == 5
    _arm(monkeypatch, _at(2024, 7, 6, 20, 0))
    sat = fwd.issue(weekend_bar, ticker="SPY", store_identity=STORE, out_dir=tmp_path / "sat")
    assert sat["refusals"] == ["NOT_A_SESSION"]


# ── T4 ───────────────────────────────────────────────────────────────────────


def test_t4_keep_first_is_byte_identical(tmp_path, monkeypatch):
    monday = date(2024, 6, 3)
    close = _long_ending(monday, seed=31)
    out = tmp_path / "out"
    _arm(monkeypatch, _at(2024, 6, 3, 20, 0))
    first = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=out)
    assert first["issued"] == 30
    log = out / fwd.FORWARD_LOG_NAME
    digest = hashlib.sha256(log.read_bytes()).hexdigest()
    refusals_before = (out / fwd.REFUSAL_LOG_NAME).read_bytes()

    second = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=out)
    assert hashlib.sha256(log.read_bytes()).hexdigest() == digest
    assert second["issued"] == 0
    assert second["duplicates"] == 30
    assert second["refusals"].count("DUPLICATE_KEY") == 30
    assert second["refusals"][-1] == "OBSERVER_NOT_ON_MAIN"
    new_refusals = (out / fwd.REFUSAL_LOG_NAME).read_bytes()[len(refusals_before):]
    parsed = [json.loads(line) for line in new_refusals.decode().splitlines() if line.strip()]
    assert [row["reason"] for row in parsed] == ["DUPLICATE_KEY"] * 30 + ["OBSERVER_NOT_ON_MAIN"]
    for row in parsed:
        _assert_refusal_schema(row)

    changed = close.copy()
    changed.iloc[-1] = float(changed.iloc[-1]) + 1.0
    third = fwd.issue(changed, ticker="SPY", store_identity=STORE, out_dir=out)
    assert hashlib.sha256(log.read_bytes()).hexdigest() == digest
    assert third["issued"] == 0
    assert third["duplicates"] == 30


# ── T5 ───────────────────────────────────────────────────────────────────────


def _session_bar() -> pd.Series:
    return _series([date(2024, 6, 3)], np.array([100.0]))


def test_t5_unfrozen_panel(tmp_path, monkeypatch):
    _arm(monkeypatch, _at(2024, 6, 3, 20, 0))
    result = fwd.issue(_session_bar(), ticker="QQQ", store_identity=STORE, out_dir=tmp_path / "out")
    assert result["refusals"] == ["UNFROZEN_PANEL"]
    assert result["issued"] == 0
    rows = _read_jsonl(tmp_path / "out" / fwd.REFUSAL_LOG_NAME)
    assert len(rows) == 1
    _assert_refusal_schema(rows[0])
    assert rows[0]["ticker"] == "QQQ"
    assert not (tmp_path / "out" / fwd.FORWARD_LOG_NAME).exists()


def test_t5_prereg_mismatch(tmp_path, monkeypatch):
    _arm(monkeypatch, _at(2024, 6, 3, 20, 0))
    root = tmp_path / "repo"
    dest = root / s1.PREREG_PATH
    dest.parent.mkdir(parents=True)
    original = (fwd.REPO_ROOT / s1.PREREG_PATH).read_bytes()
    dest.write_bytes(original + b"\nnot the frozen prereg\n")
    monkeypatch.setattr(fwd, "REPO_ROOT", root)
    altered = fwd.issue(_session_bar(), ticker="SPY", store_identity=STORE, out_dir=tmp_path / "altered")
    assert altered["refusals"] == ["PREREG_MISMATCH"]
    assert _read_jsonl(tmp_path / "altered" / fwd.REFUSAL_LOG_NAME)[0]["reason"] == "PREREG_MISMATCH"

    empty = tmp_path / "missing_repo"
    empty.mkdir()
    monkeypatch.setattr(fwd, "REPO_ROOT", empty)
    missing = fwd.issue(_session_bar(), ticker="SPY", store_identity=STORE, out_dir=tmp_path / "missing")
    assert missing["refusals"] == ["PREREG_MISMATCH"]


def test_t5_sha_mismatch(tmp_path, monkeypatch):
    _arm(monkeypatch, _at(2024, 6, 3, 20, 0), head=HEAD)
    supplied = fwd.issue(
        _session_bar(),
        ticker="SPY",
        store_identity=STORE,
        out_dir=tmp_path / "supplied",
        code_sha="b" * 40,
    )
    assert supplied["refusals"] == ["SHA_MISMATCH"]
    assert not (tmp_path / "supplied" / fwd.FORWARD_LOG_NAME).exists()

    monkeypatch.setattr(fwd, "_git_head", lambda: "")
    blank = fwd.issue(_session_bar(), ticker="SPY", store_identity=STORE, out_dir=tmp_path / "blank")
    assert blank["refusals"] == ["SHA_MISMATCH"]
    _assert_refusal_schema(_read_jsonl(tmp_path / "blank" / fwd.REFUSAL_LOG_NAME)[0])


def test_t5_digest_missing(tmp_path, monkeypatch):
    _arm(monkeypatch, _at(2024, 6, 3, 20, 0))
    result = fwd.issue(_session_bar(), ticker="SPY", store_identity="", out_dir=tmp_path / "out")
    assert result["refusals"] == ["DIGEST_MISSING"]
    assert result["issued"] == 0
    row = _read_jsonl(tmp_path / "out" / fwd.REFUSAL_LOG_NAME)[0]
    _assert_refusal_schema(row)
    assert row["reason"] == "DIGEST_MISSING"
    assert not (tmp_path / "out" / fwd.FORWARD_LOG_NAME).exists()


# ── T6 ───────────────────────────────────────────────────────────────────────


def test_t6_row_schema(tmp_path, monkeypatch):
    monday = date(2024, 6, 3)
    close = _long_ending(monday, seed=41)
    out = tmp_path / "out"
    _arm(monkeypatch, _at(2024, 6, 3, 20, 0))
    result = fwd.issue(close, ticker="SPY", store_identity=STORE, out_dir=out)
    assert result["issued"] == 30

    raw = (out / fwd.FORWARD_LOG_NAME).read_bytes()
    assert raw.endswith(b"\n")
    lines = raw.splitlines(keepends=True)
    assert len(lines) == 30
    rows = []
    for line in lines:
        assert line.endswith(b"\n")
        again = json.dumps(
            json.loads(line), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode() + b"\n"
        assert again == line
        rows.append(json.loads(line))

    assert len(ISSUE_FIELDS) == 31
    configs = set()
    gates = set()
    for row in rows:
        assert set(row) == ISSUE_FIELDS
        assert row["schema"] == fwd.ISSUE_SCHEMA
        assert row["evidence_class"] == "GENUINELY_ISSUED"
        assert row["ticker"] == "SPY"
        assert row["asof"] == "2024-06-03"
        assert row["horizon"] in (5, 10, 21)
        assert row["population"] == "P-all"
        assert row["kind"] in ("binary", "quantile")
        assert row["is_gate"] is (row["config_id"] in GATE_IDS)
        assert row["writer_lane"] == "nightly"
        assert row["writer_identity"] == "daily.yml:engine"
        assert row["collect_lane_env"] == "nightly"
        assert row["backfill"] is False and row["rerun"] is False and row["intraday"] is False
        assert row["code_sha"] == HEAD
        assert len(row["recipe_fingerprint"]) == 64
        assert row["prereg_blob"] == s1.PREREG_BLOB
        assert row["prereg_path"] == s1.PREREG_PATH
        assert len(row["inputs_digest"]) == 64
        assert row["issued_at"].endswith("+00:00")
        assert row["realized_A"] is None
        assert row["Y"] is None
        assert row["graded_at"] is None
        assert row["grader_sha"] is None
        receipt = row["issue_receipt"]
        assert set(receipt) == {"contract", "epoch", "issued_at", "ledger_lane", "first_writer_wins"}
        assert receipt["contract"] == fwd.ISSUE_SCHEMA
        assert receipt["epoch"] == fwd.EPOCH
        assert receipt["issued_at"] == row["issued_at"]
        assert receipt["ledger_lane"] == "nightly"
        assert receipt["first_writer_wins"] is True
        assert (row["probability"] is None) or (row["quantile"] is None)
        if row["kind"] == "binary":
            assert row["quantile"] is None
            if row["abstention_reason"] is None:
                assert isinstance(row["probability"], float)
            else:
                assert row["probability"] is None
        else:
            assert row["probability"] is None
            if row["abstention_reason"] is None:
                q = row["quantile"]
                assert list(q) == ["0.5", "0.8", "0.9"]
                assert q["0.5"] <= q["0.8"] <= q["0.9"]
            else:
                assert row["quantile"] is None
        configs.add(row["config_id"])
        if row["is_gate"]:
            gates.add(row["config_id"])
    assert configs == set(ISSUED_IDS)
    assert gates == GATE_IDS
    assert sum(1 for row in rows if row["is_gate"]) == 6

    refusal_raw = (out / fwd.REFUSAL_LOG_NAME).read_bytes()
    for line in refusal_raw.splitlines(keepends=True):
        again = json.dumps(
            json.loads(line), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode() + b"\n"
        assert again == line
        _assert_refusal_schema(json.loads(line))


# ── T7 ───────────────────────────────────────────────────────────────────────


def _copy_recipe_tree(root: Path, source: Path) -> None:
    for rel in fwd.RECIPE_FILES:
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((source / rel).read_bytes())


def test_t7_recipe_fingerprint_and_inputs_digest(tmp_path, monkeypatch):
    origin = Path(fwd.REPO_ROOT)
    real_a = fwd.recipe_fingerprint()
    real_b = fwd.recipe_fingerprint()
    assert real_a == real_b
    assert len(real_a) == 64

    copied = tmp_path / "repo"
    _copy_recipe_tree(copied, origin)
    monkeypatch.setattr(fwd, "REPO_ROOT", copied)
    first = fwd.recipe_fingerprint()
    second = fwd.recipe_fingerprint()
    assert first == second == real_a
    target = copied / "engine" / "vol_forecast.py"
    target.write_bytes(target.read_bytes() + b"\n")
    assert fwd.recipe_fingerprint() != first

    clean = tmp_path / "clean"
    _copy_recipe_tree(clean, origin)
    monkeypatch.setattr(fwd, "REPO_ROOT", clean)
    entries = []
    for rel in fwd.RECIPE_FILES:
        data = (clean / rel).read_bytes()
        entries.append((rel, hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()))
    entries.sort()
    text = "".join(f"{path}\t{blob}\n" for path, blob in entries)
    text += f"prereg_blob\t{s1.PREREG_BLOB}\n"
    expect = hashlib.sha256(text.encode()).hexdigest()
    assert fwd.recipe_fingerprint() == expect

    dates = _sessions_ending(date(2024, 6, 3), 80)
    window = fwd._prepare_close(_series(dates, _gbm_prices(80, seed=9)))
    t = len(window) - 1
    base = fwd.inputs_digest(window, t, 5, "SPY", "store-a", "2024-01-02")
    assert base == fwd.inputs_digest(window, t, 5, "SPY", "store-a", "2024-01-02")
    nudged = window.copy()
    nudged.iloc[-1] = float(nudged.iloc[-1]) + 1e-9
    assert fwd.inputs_digest(nudged, t, 5, "SPY", "store-a", "2024-01-02") != base
    assert fwd.inputs_digest(window, t, 5, "SPY", "store-b", "2024-01-02") != base

    payload = fwd.inputs_digest_payload(window, t, 5, "SPY", "store-a", "2024-01-02")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    assert hashlib.sha256(encoded).hexdigest() == base
    with pytest.raises(fwd._DigestMissing):
        fwd.inputs_digest(window, t, 5, "SPY", "", "2024-01-02")


# ── T8 ───────────────────────────────────────────────────────────────────────


def test_t8_off_lane_does_not_open(tmp_path, monkeypatch):
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.setenv("US_LANE", "nightly")
    real_open = os.open

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("os.open called on an off-lane issue")

    # Patch for the call only. Leaving it in place breaks pytest teardown,
    # which opens files after the assertion has already passed.
    os.open = _forbidden
    try:
        out = tmp_path / "out"
        result = fwd.issue(_session_bar(), ticker="SPY", store_identity=STORE, out_dir=out)
        assert result["reason"] == "LANE"
        assert not out.exists()
        assert not (tmp_path / "data").exists()
    finally:
        os.open = real_open


def test_namespace_import_is_the_stage1_module():
    """The writer imports stage 1 as a namespace package, not a copied module."""
    assert fwd.s1 is s1
    assert fwd.s1.PREREG_BLOB == s1.PREREG_BLOB
    assert not any(
        token in Path(fwd.__file__).read_text(encoding="utf-8")
        for token in ("def fit_logistic", "def fit_quantile_lp", "def fit_b0")
    )
