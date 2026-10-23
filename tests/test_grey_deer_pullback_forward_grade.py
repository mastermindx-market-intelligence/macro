"""Synthetic tests for the Grey Deer pullback forward-log grader.

No price store, no network. Issue rows are fixtures shaped like design §2.1.
The clock and ``HEAD`` are monkeypatched. Admission is the writer's §1.1 helper.

Run:
    python3 -m pytest tests/test_grey_deer_pullback_forward_grade.py -rA -q
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import nyse_calendar  # noqa: E402
from scripts.research import grey_deer_pullback_stage1 as s1  # noqa: E402
from engine import grey_deer_pullback_forward_grade as grader  # noqa: E402
import scripts.research.grey_deer_pullback_readiness as readiness_mod  # noqa: E402

CLOCK = "2026-10-13T12:00:00+00:00"
HEAD = "a" * 40
STORE = "synthetic-store"
TICKER = "SPY"

# Design §2.2. The join key is top-level. There is no nested ``key``.
GRADE_FIELDS = {
    "schema",
    "asof",
    "ticker",
    "horizon",
    "config_id",
    "issue_line_sha256",
    "prereg_blob",
    "realized_A",
    "Y",
    "graded_at",
    "grader_sha",
    "grader_lane",
    "grade_inputs_digest",
    "revision_flag",
    "evidence_class",
}
KEY_FIELDS = {"asof", "ticker", "horizon", "config_id"}
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


def _sessions_from(start: date, n: int) -> list[date]:
    out: list[date] = []
    day = start
    while len(out) < n:
        if nyse_calendar.is_session(day):
            out.append(day)
        day += timedelta(days=1)
    return out


def _sessions_before(day: date, n: int) -> list[date]:
    out: list[date] = []
    cursor = day - timedelta(days=1)
    while len(out) < n:
        if nyse_calendar.is_session(cursor):
            out.append(cursor)
        cursor -= timedelta(days=1)
    out.reverse()
    return out


def _close_from_sessions(sessions: list[date], prices: np.ndarray) -> pd.Series:
    index = pd.DatetimeIndex(pd.to_datetime(sessions))
    return pd.Series(np.asarray(prices, dtype=float), index=index)


def _walk(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rets = np.clip(rng.normal(0.0001, 0.008, n), -0.03, 0.03)
    return 100.0 * np.exp(np.cumsum(rets))


def _base_issue() -> dict:
    issued_at = "2021-07-06T21:30:00+00:00"
    return {
        "schema": "grey_deer_pullback_forward_issue.v1",
        "evidence_class": "GENUINELY_ISSUED",
        "asof": "2021-07-06",
        "ticker": TICKER,
        "horizon": 5,
        "config_id": "B0",
        "population": "P-all",
        "kind": "binary",
        "is_gate": False,
        "probability": 0.04,
        "quantile": None,
        "abstention_reason": None,
        "inputs_digest": "ab" * 32,
        "code_sha": "cd" * 20,
        "recipe_fingerprint": "ef" * 32,
        "prereg_blob": s1.PREREG_BLOB,
        "prereg_path": s1.PREREG_PATH,
        "issued_at": issued_at,
        "writer_lane": "nightly",
        "writer_identity": "daily.yml:engine",
        "collect_lane_env": "nightly",
        "backfill": False,
        "rerun": False,
        "intraday": False,
        "fit_block_id": "block-0",
        "training_end_asof": "2021-04-01",
        "issue_receipt": {
            "contract": "grey_deer_pullback_forward_issue.v1",
            "epoch": "grey_deer_pullback_prospective.v1",
            "issued_at": issued_at,
            "ledger_lane": "nightly",
            "first_writer_wins": True,
        },
        "realized_A": None,
        "Y": None,
        "graded_at": None,
        "grader_sha": None,
    }


def _legal_issued_at(asof: str) -> str:
    """22:00Z is 17:00 EST and 18:00 EDT, inside the §1.3 window for that asof."""
    return f"{asof}T22:00:00+00:00"


def _et_stamp(day: date, hour: int, minute: int) -> str:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=nyse_calendar.ET).astimezone(
        timezone.utc
    ).isoformat(timespec="seconds")


def _issue(**overrides) -> dict:
    row = copy.deepcopy(_base_issue())
    row.update(overrides)
    if "issued_at" not in overrides:
        stamp = _legal_issued_at(str(row["asof"]))
        row["issued_at"] = stamp
        receipt = row.get("issue_receipt")
        if isinstance(receipt, dict):
            receipt["issued_at"] = stamp
    return row


def _line(row: dict) -> bytes:
    return (
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _write_lines(path: Path, chunks: list[bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(chunks))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    for raw in path.read_bytes().split(b"\n"):
        if not raw:
            continue
        rows.append(json.loads(raw.decode("utf-8")))
    return rows


def _canonical(obj: dict) -> bytes:
    return (
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def pin(monkeypatch, *, head: str = HEAD) -> None:
    monkeypatch.setattr(grader, "_utc_now", lambda value=CLOCK: value)
    monkeypatch.setattr(grader, "_git_head", lambda value=head: value)


def arm(monkeypatch, *, head: str = HEAD) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setenv("GREY_DEER_PULLBACK_GRADER_IDENTITY", "daily.yml:engine")
    pin(monkeypatch, head=head)


def _boom(*args, **kwargs):
    raise AssertionError(f"os.open must not be called on an off-lane grade: {args!r}")


def _one_mature(log_dir: Path, *, seed: int = 7, horizon: int = 5):
    """One issued row at a mature asof, plus the close series that grades it."""
    sessions = _sessions_from(date(2021, 7, 6), 80)
    close = _close_from_sessions(sessions, _walk(len(sessions), seed))
    asof_i = 40
    row = _issue(asof=sessions[asof_i].isoformat(), horizon=horizon, config_id="B0")
    raw = _line(row)
    _write_lines(log_dir / "forward_log.jsonl", [raw])
    return close, sessions, asof_i, row, raw


# ── T1 ───────────────────────────────────────────────────────────────────────


def test_t1_maturity_grades_only_mature_rows(tmp_path, monkeypatch):
    arm(monkeypatch)
    n = 400
    sessions = _sessions_from(date(2021, 7, 6), n)
    assert sessions[0] == date(2021, 7, 6)
    assert nyse_calendar.is_session(sessions[0])
    assert all(nyse_calendar.is_session(day) for day in sessions)
    close = _close_from_sessions(sessions, _walk(n, 20261013))
    close_window = close.loc[close.index >= pd.Timestamp(s1.WINDOW_START)]
    assert len(close_window) == n
    labels = s1.build_labels(close_window)

    rows = []
    expect_grade = []
    expect_immature = []
    for horizon in s1.HORIZONS:
        for position, kind in (
            (n - 1 - horizon, "mature"),
            (n - horizon, "immature"),
            (n - 30, "mature"),
        ):
            row = _issue(
                asof=sessions[position].isoformat(),
                horizon=horizon,
                config_id="B0",
            )
            rows.append(row)
            slot = expect_grade if kind == "mature" else expect_immature
            slot.append((row, position, horizon))

    log_dir = tmp_path / "log"
    issue_bytes = b"".join(_line(row) for row in rows)
    _write_lines(log_dir / "forward_log.jsonl", [_line(row) for row in rows])
    issue_hash = _sha256(issue_bytes)

    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)

    assert result["graded"] == len(expect_grade) == 6
    assert result["immature"] == len(expect_immature) == 3
    assert result["already_graded"] == 0
    assert result["asof_missing"] == 0
    assert result["prereg_mismatch"] == 0
    assert result["malformed"] == 0
    assert result["skipped_non_issued"] == 0
    assert result["refusals"] == []
    assert _sha256((log_dir / "forward_log.jsonl").read_bytes()) == issue_hash

    graded_path = log_dir / "forward_log_graded.jsonl"
    grades = _read_jsonl(graded_path)
    assert len(grades) == 6
    assert [g["graded_at"] for g in grades] == [CLOCK] * 6
    assert [g["grader_sha"] for g in grades] == [HEAD] * 6

    got = {(g["asof"], g["horizon"], g["config_id"]): g for g in grades}
    for row, position, horizon in expect_grade:
        key = (row["asof"], horizon, row["config_id"])
        assert key in got
        grade_row = got[key]
        assert type(grade_row["Y"]) is int
        assert abs(grade_row["realized_A"] - float(labels[horizon]["A"].iloc[position])) <= 1e-12
        assert grade_row["Y"] == (1 if bool(labels[horizon]["Y"].iloc[position]) else 0)
        assert not pd.isna(labels[horizon]["A"].iloc[position])
    for row, _position, horizon in expect_immature:
        key = (row["asof"], horizon, row["config_id"])
        assert key not in got
        assert pd.isna(labels[horizon]["A"].iloc[_position])
    names = sorted(path.name for path in log_dir.iterdir())
    assert names == ["forward_log.jsonl", "forward_log_graded.jsonl"]


# ── T2 ───────────────────────────────────────────────────────────────────────


def test_t2_event_and_non_event(tmp_path, monkeypatch):
    arm(monkeypatch)
    n = 40
    sessions = _sessions_from(date(2021, 7, 6), n)
    prices = np.full(n, 100.0)
    event_at = 8
    calm_at = 20
    prices[event_at + 2] = 90.0  # 10% drawdown inside the h=5 window, ratio 0.90
    close = _close_from_sessions(sessions, prices)
    rows = [
        _issue(asof=sessions[event_at].isoformat(), horizon=5, config_id="B0"),
        _issue(asof=sessions[calm_at].isoformat(), horizon=5, config_id="B0"),
    ]
    log_dir = tmp_path / "log"
    _write_lines(log_dir / "forward_log.jsonl", [_line(row) for row in rows])

    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)

    assert result["graded"] == 2
    assert result["immature"] == 0
    by_asof = {row["asof"]: row for row in _read_jsonl(log_dir / "forward_log_graded.jsonl")}
    event = by_asof[sessions[event_at].isoformat()]
    calm = by_asof[sessions[calm_at].isoformat()]
    assert type(event["Y"]) is int and event["Y"] == 1
    assert type(calm["Y"]) is int and calm["Y"] == 0
    assert event["realized_A"] == pytest.approx(0.10, abs=1e-12)
    assert calm["realized_A"] == pytest.approx(0.0, abs=1e-12)
    assert event["realized_A"] >= s1.THRESHOLD
    assert calm["realized_A"] < s1.THRESHOLD


# ── T3 ───────────────────────────────────────────────────────────────────────


def test_t3_keep_first_identical_rerun_and_conflict(tmp_path, monkeypatch):
    arm(monkeypatch)
    n = 400
    sessions = _sessions_from(date(2021, 7, 6), n)
    prices = _walk(n, 11)
    close = _close_from_sessions(sessions, prices)
    rows = []
    graded_slots = []
    for horizon in s1.HORIZONS:
        for position, kind in (
            (n - 1 - horizon, "mature"),
            (n - horizon, "immature"),
            (n - 30, "mature"),
        ):
            rows.append(_issue(asof=sessions[position].isoformat(), horizon=horizon, config_id="B0"))
            if kind == "mature":
                graded_slots.append((position, horizon))
    log_dir = tmp_path / "log"
    issue_path = log_dir / "forward_log.jsonl"
    _write_lines(issue_path, [_line(row) for row in rows])
    issue_hash = _sha256(issue_path.read_bytes())

    first = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)
    graded_path = log_dir / "forward_log_graded.jsonl"
    refusal_path = log_dir / "forward_log_refusals.jsonl"
    graded_hash = _sha256(graded_path.read_bytes())
    assert first["graded"] == 6
    assert not refusal_path.exists()

    second = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)
    assert second["graded"] == 0
    assert second["already_graded"] == first["graded"]
    assert second["refusals"] == []
    assert second["immature"] == 3
    assert _sha256(graded_path.read_bytes()) == graded_hash
    assert not refusal_path.exists()
    assert _sha256(issue_path.read_bytes()) == issue_hash

    window = close.loc[close.index >= pd.Timestamp(s1.WINDOW_START)]
    before = s1.build_labels(window)
    edited = close.copy()
    edited.iloc[n - 29] = 1.0
    window_after = edited.loc[edited.index >= pd.Timestamp(s1.WINDOW_START)]
    after = s1.build_labels(window_after)
    conflict_keys = set()
    unchanged = 0
    for position, horizon in graded_slots:
        a0 = float(before[horizon]["A"].iloc[position])
        a1 = float(after[horizon]["A"].iloc[position])
        key = (sessions[position].isoformat(), TICKER, horizon, "B0")
        if a0 != a1:
            conflict_keys.add(key)
        else:
            unchanged += 1
    assert conflict_keys, "the edited close must sit inside at least one graded window"

    third = grader.grade(edited, ticker=TICKER, store_identity=STORE, log_dir=log_dir)
    assert third["graded"] == 0
    assert third["already_graded"] == unchanged
    assert _sha256(graded_path.read_bytes()) == graded_hash
    assert len(_read_jsonl(graded_path)) == first["graded"]
    assert len(third["refusals"]) == len(conflict_keys)
    assert { (r["asof"], r["ticker"], r["horizon"], r["config_id"]) for r in third["refusals"] } == conflict_keys
    file_rows = _read_jsonl(refusal_path)
    assert len(file_rows) == len(conflict_keys)
    assert [row["reason"] for row in file_rows] == ["DUPLICATE_KEY"] * len(conflict_keys)
    for row in file_rows:
        assert set(row) == REFUSAL_FIELDS
        assert row["schema"] == "grey_deer_pullback_forward_refusal.v1"
        assert row["writer_lane"] == "nightly"
        assert row["refused_at"] == CLOCK
    assert _sha256(issue_path.read_bytes()) == issue_hash


# ── T4 ───────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("lane", "identity", "reason", "claimed"),
    [
        (None, "daily.yml:engine", "LANE", "absent"),
        ("render", "daily.yml:engine", "LANE", "render"),
        ("nightly", "daily.yml:render", "IDENTITY", "nightly"),
        (None, "wrong", "LANE", "absent"),
    ],
)
def test_t4_gates_write_nothing(tmp_path, monkeypatch, lane, identity, reason, claimed):
    pin(monkeypatch)
    if lane is None:
        monkeypatch.delenv("COLLECT_LANE", raising=False)
        monkeypatch.setenv("US_LANE", "nightly")
    else:
        monkeypatch.setenv("COLLECT_LANE", lane)
    monkeypatch.setenv("GREY_DEER_PULLBACK_GRADER_IDENTITY", identity)
    # Restore os.open before teardown. A session fixture writes a stamp with
    # os.open, and a patch that outlives the assertion fails that fixture.
    real_open = os.open
    monkeypatch.setattr(os, "open", _boom)

    log_dir = tmp_path / "log"
    close, _sessions, _i, _row, _raw = _one_mature(log_dir)
    issue_hash = _sha256((log_dir / "forward_log.jsonl").read_bytes())
    try:
        result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)
        missing = tmp_path / "missing"
        again = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=missing)
    finally:
        monkeypatch.setattr(os, "open", real_open)

    assert result["graded"] == 0
    assert result["already_graded"] == 0
    assert result["immature"] == 0
    assert [item["reason"] for item in result["refusals"]] == [reason]
    refusal = result["refusals"][0]
    assert set(refusal) == REFUSAL_FIELDS
    assert refusal["schema"] == "grey_deer_pullback_forward_refusal.v1"
    assert refusal["writer_lane"] == claimed
    assert refusal["asof"] is None
    assert refusal["ticker"] is None
    assert refusal["horizon"] is None
    assert refusal["config_id"] is None
    assert refusal["refused_at"] == CLOCK
    assert len(refusal["attempt_digest"]) == 64
    assert sorted(path.name for path in log_dir.iterdir()) == ["forward_log.jsonl"]
    assert _sha256((log_dir / "forward_log.jsonl").read_bytes()) == issue_hash
    assert not (log_dir / "forward_log_graded.jsonl").exists()
    assert not (log_dir / "forward_log_refusals.jsonl").exists()
    assert not missing.exists()
    assert again["graded"] == 0
    assert [item["reason"] for item in again["refusals"]] == [reason]


@pytest.mark.parametrize("bad_head", ["", "abc", "A" * 40, "g" * 40])
def test_t4_sha_mismatch_writes_refusal_and_grades_nothing(tmp_path, monkeypatch, bad_head):
    arm(monkeypatch, head=bad_head)
    log_dir = tmp_path / "log"
    close, _sessions, _i, _row, _raw = _one_mature(log_dir)
    issue_hash = _sha256((log_dir / "forward_log.jsonl").read_bytes())

    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)

    assert result["graded"] == 0
    assert result["already_graded"] == 0
    assert result["immature"] == 0
    assert result["malformed"] == 0
    assert len(result["refusals"]) == 1
    refusal = result["refusals"][0]
    assert refusal["reason"] == "SHA_MISMATCH"
    assert set(refusal) == REFUSAL_FIELDS
    assert refusal["writer_lane"] == "nightly"
    assert refusal["asof"] is None
    assert not (log_dir / "forward_log_graded.jsonl").exists()
    lines = (log_dir / "forward_log_refusals.jsonl").read_bytes().split(b"\n")
    lines = [line for line in lines if line]
    assert len(lines) == 1
    assert json.loads(lines[0])["reason"] == "SHA_MISMATCH"
    assert _canonical(json.loads(lines[0])) == lines[0] + b"\n"
    assert _sha256((log_dir / "forward_log.jsonl").read_bytes()) == issue_hash


# ── T5 ───────────────────────────────────────────────────────────────────────


def test_t5_filters(tmp_path, monkeypatch):
    arm(monkeypatch)
    pre = _sessions_before(date(2021, 7, 6), 5)
    main = _sessions_from(date(2021, 7, 6), 80)
    assert main[0] == date(2021, 7, 6)
    assert pre[-1] < date(2021, 7, 6)
    sessions = pre + main
    prices = np.full(len(sessions), 100.0)
    close = _close_from_sessions(sessions, prices)
    mature_asof = main[40].isoformat()
    pre_asof = pre[-1].isoformat()
    absent_asof = "1999-01-04"

    abstained = _issue(
        asof=mature_asof,
        horizon=5,
        config_id="B0",
        probability=None,
        abstention_reason="FIT_NONCONVERGENCE",
    )
    abstained_raw = _line(abstained)
    chunks = [
        abstained_raw,
        _line(_issue(asof=mature_asof, horizon=5, config_id="B1-20", backfill=True)),
        _line(_issue(asof=mature_asof, horizon=5, config_id="B1-63", rerun=True)),
        _line(_issue(asof=mature_asof, horizon=5, config_id="B2-21", intraday=True)),
        _line(_issue(asof=mature_asof, horizon=5, config_id="B2-63", evidence_class="RESEARCH")),
        _line(_issue(asof=mature_asof, horizon=5, config_id="Q0", writer_lane="render")),
        _line(_issue(asof=mature_asof, horizon=5, config_id="Q1", schema="grey_deer_pullback_forward_issue.v0")),
        _line(_issue(asof=mature_asof, horizon=63, config_id="M3-ALL@C=0.1")),
        b"{not-json\n",
        _line(_issue(asof=mature_asof, horizon=5, config_id="M3-ALL@C=1.0", prereg_blob="0" * 40)),
        _line(_issue(asof=absent_asof, horizon=5, config_id="Q3-ALL")),
        _line(_issue(asof=pre_asof, horizon=5, config_id="M3-ACT")),
        _line(_issue(asof=mature_asof, horizon=5, config_id="B0", ticker="QQQ")),
    ]

    log_dir = tmp_path / "log"
    _write_lines(log_dir / "forward_log.jsonl", chunks)
    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)

    assert result["graded"] == 1
    assert result["skipped_non_issued"] == 7
    assert result["prereg_mismatch"] == 1
    assert result["malformed"] == 1
    assert result["asof_missing"] == 2
    assert result["immature"] == 0
    assert result["already_graded"] == 0
    assert [item["reason"] for item in result["refusals"]] == ["PREREG_MISMATCH"]

    grades = _read_jsonl(log_dir / "forward_log_graded.jsonl")
    assert len(grades) == 1
    grade_row = grades[0]
    assert grade_row["issue_line_sha256"] == _sha256(abstained_raw[:-1])
    assert grade_row["asof"] == mature_asof
    assert grade_row["ticker"] == TICKER
    assert grade_row["horizon"] == 5
    assert grade_row["config_id"] == "B0"
    assert "key" not in grade_row
    assert type(grade_row["Y"]) is int and grade_row["Y"] == 0
    assert json.loads(abstained_raw)["abstention_reason"] == "FIT_NONCONVERGENCE"
    assert all(row["ticker"] == TICKER for row in grades)
    assert pre_asof not in {row["asof"] for row in grades}
    assert absent_asof not in {row["asof"] for row in grades}


# ── T6 ───────────────────────────────────────────────────────────────────────


def test_t6_revision_flag_null_without_callable(tmp_path, monkeypatch):
    arm(monkeypatch)
    log_dir = tmp_path / "log"
    close, _sessions, _i, _row, _raw = _one_mature(log_dir)
    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)
    assert result["graded"] == 1
    grade_row = _read_jsonl(log_dir / "forward_log_graded.jsonl")[0]
    assert grade_row["revision_flag"] is None


def test_t6_revision_flag_false_when_digest_matches(tmp_path, monkeypatch):
    arm(monkeypatch)
    log_dir = tmp_path / "log"
    close, sessions, asof_i, row, _raw = _one_mature(log_dir)
    seen = {}

    def fake(prefix, i, h, ticker, store_identity, training_end_asof):
        seen["args"] = (len(prefix), i, h, ticker, store_identity, training_end_asof)
        seen["last"] = float(prefix.iloc[-1])
        return row["inputs_digest"]

    result = grader.grade(
        close,
        ticker=TICKER,
        store_identity=STORE,
        log_dir=log_dir,
        recompute_inputs_digest=fake,
    )
    assert result["graded"] == 1
    grade_row = _read_jsonl(log_dir / "forward_log_graded.jsonl")[0]
    assert grade_row["revision_flag"] is False
    length, i, h, ticker, store_identity, training_end = seen["args"]
    assert length == i + 1
    assert h == 5
    assert ticker == TICKER
    assert store_identity == STORE
    assert training_end == row["training_end_asof"]
    assert seen["last"] == pytest.approx(float(close.loc[pd.Timestamp(sessions[asof_i])]))


def test_t6_revision_flag_true_when_digest_differs(tmp_path, monkeypatch):
    arm(monkeypatch)
    log_dir = tmp_path / "log"
    close, _sessions, _i, _row, _raw = _one_mature(log_dir)

    def fake(prefix, i, h, ticker, store_identity, training_end_asof):
        return "not-the-issue-digest"

    result = grader.grade(
        close,
        ticker=TICKER,
        store_identity=STORE,
        log_dir=log_dir,
        recompute_inputs_digest=fake,
    )
    assert result["graded"] == 1
    grade_row = _read_jsonl(log_dir / "forward_log_graded.jsonl")[0]
    assert grade_row["revision_flag"] is True


# ── T7 ───────────────────────────────────────────────────────────────────────


def test_t7_schema_canonical_json_and_line_hash(tmp_path, monkeypatch):
    arm(monkeypatch)
    log_dir = tmp_path / "log"
    close, sessions, asof_i, row, raw = _one_mature(log_dir, horizon=10)
    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)
    assert result["graded"] == 1

    graded_bytes = (log_dir / "forward_log_graded.jsonl").read_bytes()
    line = graded_bytes.split(b"\n")[0]
    parsed = json.loads(line)
    assert _canonical(parsed) == line + b"\n"
    assert set(parsed) == GRADE_FIELDS
    assert "key" not in parsed
    assert parsed["schema"] == "grey_deer_pullback_forward_grade.v1"
    assert parsed["evidence_class"] == "GRADE"
    assert parsed["grader_lane"] == "nightly"
    assert parsed["grader_sha"] == HEAD
    assert parsed["graded_at"] == CLOCK
    assert parsed["prereg_blob"] == s1.PREREG_BLOB == row["prereg_blob"]
    assert type(parsed["realized_A"]) is float
    assert type(parsed["Y"]) is int
    assert parsed["revision_flag"] is None
    assert parsed["issue_line_sha256"] == _sha256(raw[:-1])
    assert parsed["asof"] == sessions[asof_i].isoformat()
    assert parsed["horizon"] == 10
    assert parsed["ticker"] == TICKER
    assert parsed["config_id"] == "B0"

    window = close.loc[close.index >= pd.Timestamp(s1.WINDOW_START)]
    position = int(window.index.get_loc(pd.Timestamp(parsed["asof"])))
    horizon = parsed["horizon"]
    digest_payload = {
        "asof": parsed["asof"],
        "closes": [repr(float(c)) for c in window.iloc[position:position + horizon + 1]],
        "horizon": horizon,
        "store_identity": STORE,
        "ticker": TICKER,
    }
    expect = hashlib.sha256(
        json.dumps(
            digest_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()
    assert parsed["grade_inputs_digest"] == expect
    labels = s1.build_labels(window)
    assert abs(parsed["realized_A"] - float(labels[horizon]["A"].iloc[position])) <= 1e-12
    assert parsed["Y"] == (1 if bool(labels[horizon]["Y"].iloc[position]) else 0)


# ── guards that are part of the packet but not numbered T1-T7 ───────────────


def test_missing_issue_log_creates_nothing(tmp_path, monkeypatch):
    arm(monkeypatch)
    log_dir = tmp_path / "absent"
    sessions = _sessions_from(date(2021, 7, 6), 30)
    close = _close_from_sessions(sessions, np.full(30, 100.0))
    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)
    assert result["refusals"] == []
    assert all(result[key] == 0 for key in (
        "graded", "already_graded", "immature", "asof_missing",
        "prereg_mismatch", "malformed", "skipped_non_issued",
    ))
    assert not log_dir.exists()


def test_default_log_dir_does_not_create_data_tree(monkeypatch):
    arm(monkeypatch)
    root = Path(grader.__file__).resolve().parents[1]
    data = root / "data"
    existed = data.exists()
    target = data / "grey_deer_pullback" / "forward_log.jsonl"
    if target.exists():
        pytest.skip("issue log is present; refusing to grade the default path")
    sessions = _sessions_from(date(2021, 7, 6), 5)
    close = _close_from_sessions(sessions, np.full(5, 100.0))
    result = grader.grade(close, ticker=TICKER, store_identity=STORE)
    assert result["graded"] == 0
    assert result["refusals"] == []
    assert not target.exists()
    assert data.exists() is existed


def test_module_does_not_copy_label_math():
    source = Path(grader.__file__).read_text(encoding="utf-8")
    assert "future_min" not in source
    assert ".rolling(" not in source
    assert "SPLIT_LIKE_RATIO" not in source
    assert "clip(lower" not in source
    assert "om.forward_max_loss" in source
    assert "om.loss_event" in source


# ── probes from the forward-lane review ──────────────────────────────────────


def test_grade_schema_is_section_2_2_and_readiness_counts_it(tmp_path, monkeypatch):
    """Finding 1: the row the grader writes is the §2.2 object readiness can join."""
    arm(monkeypatch)
    log_dir = tmp_path / "log"
    close, sessions, asof_i, _row, _raw = _one_mature(log_dir)
    asof = sessions[asof_i].isoformat()
    row = _issue(asof=asof, horizon=5, config_id="M3-ALL@C=1.0")
    raw = _line(row)
    _write_lines(log_dir / "forward_log.jsonl", [raw])

    def same_digest(prefix, i, h, ticker, store_identity, training_end_asof):
        return row["inputs_digest"]

    result = grader.grade(
        close,
        ticker=TICKER,
        store_identity=STORE,
        log_dir=log_dir,
        recompute_inputs_digest=same_digest,
    )
    assert result["graded"] == 1
    grades = _read_jsonl(log_dir / "forward_log_graded.jsonl")
    assert len(grades) == 1
    parsed = grades[0]
    assert set(parsed) == GRADE_FIELDS
    assert KEY_FIELDS <= GRADE_FIELDS
    assert "key" not in parsed
    assert parsed["asof"] == asof
    assert parsed["ticker"] == TICKER
    assert parsed["horizon"] == 5
    assert parsed["config_id"] == "M3-ALL@C=1.0"
    assert type(parsed["Y"]) is int
    assert parsed["Y"] == (1 if parsed["realized_A"] >= s1.THRESHOLD else 0)
    assert parsed["revision_flag"] is False
    assert parsed["evidence_class"] == "GRADE"
    assert parsed["grader_lane"] == "nightly"

    usable = readiness_mod._usable_grade(parsed)
    assert usable is not None
    assert usable.key == (asof, TICKER, 5, "M3-ALL@C=1.0")
    payload = readiness_mod.readiness(log_dir)
    cell = next(
        item
        for cohort in payload["cohorts"]
        for item in cohort["cells"]
        if item["horizon"] == 5 and item["config_id"] == "M3-ALL@C=1.0"
    )
    assert cell["graded"] == 1
    assert cell["issued_sessions"] == 1

    nested_dir = tmp_path / "nested"
    _write_lines(nested_dir / "forward_log.jsonl", [raw])
    nested = {
        "schema": "grey_deer_pullback_forward_grade.v1",
        "key": {
            "asof": asof,
            "ticker": TICKER,
            "horizon": 5,
            "config_id": "M3-ALL@C=1.0",
        },
        "issue_line_sha256": _sha256(raw[:-1]),
        "prereg_blob": row["prereg_blob"],
        "realized_A": parsed["realized_A"],
        "Y": bool(parsed["Y"]),
        "graded_at": CLOCK,
        "grader_sha": HEAD,
        "grader_lane": "nightly",
        "grade_inputs_digest": "11" * 32,
        "revision_flag": False,
        "evidence_class": "GRADE",
    }
    nested_bytes = _canonical(nested)
    _write_lines(nested_dir / "forward_log_graded.jsonl", [nested_bytes])
    again = grader.grade(
        close,
        ticker=TICKER,
        store_identity=STORE,
        log_dir=nested_dir,
        recompute_inputs_digest=same_digest,
    )
    assert again["graded"] == 0
    assert again["already_graded"] == 1
    assert (nested_dir / "forward_log_graded.jsonl").read_bytes() == nested_bytes


def test_missing_session_inside_horizon_is_not_graded(tmp_path, monkeypatch):
    """Finding 2: a hole inside the next h sessions is immature. The full series grades."""
    arm(monkeypatch)
    asof = date(2021, 10, 13)
    assert nyse_calendar.is_session(asof)
    horizon = 5
    pre = _sessions_before(asof, 10)
    post = _sessions_from(asof + timedelta(days=1), horizon + 5)
    full_sessions = pre + [asof] + post
    full_close = _close_from_sessions(full_sessions, np.full(len(full_sessions), 100.0))
    dropped = post[0]
    gap_sessions = [day for day in full_sessions if day != dropped]
    gap_close = _close_from_sessions(gap_sessions, np.full(len(gap_sessions), 100.0))
    # The gapped positional window is long enough to look mature by bar count.
    assert len(gap_sessions) - gap_sessions.index(asof) - 1 >= horizon

    row = _issue(asof=asof.isoformat(), horizon=horizon, config_id="B0")
    full_dir = tmp_path / "full"
    gap_dir = tmp_path / "gap"
    _write_lines(full_dir / "forward_log.jsonl", [_line(row)])
    _write_lines(gap_dir / "forward_log.jsonl", [_line(row)])

    full = grader.grade(full_close, ticker=TICKER, store_identity=STORE, log_dir=full_dir)
    gap = grader.grade(gap_close, ticker=TICKER, store_identity=STORE, log_dir=gap_dir)
    assert full["graded"] == 1
    assert (full_dir / "forward_log_graded.jsonl").is_file()
    assert gap["graded"] == 0
    assert gap["immature"] == 1
    assert not (gap_dir / "forward_log_graded.jsonl").exists()


def test_prereg_mismatch_appends_refusal_and_grades_nothing(tmp_path, monkeypatch):
    """Finding 10: a foreign prereg blob is a PREREG_MISMATCH refusal, not a silent skip."""
    arm(monkeypatch)
    log_dir = tmp_path / "log"
    close, sessions, asof_i, _row, _raw = _one_mature(log_dir)
    foreign = "0" * 40
    assert foreign != s1.PREREG_BLOB
    row = _issue(asof=sessions[asof_i].isoformat(), horizon=5, config_id="B0", prereg_blob=foreign)
    _write_lines(log_dir / "forward_log.jsonl", [_line(row)])

    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)

    assert result["graded"] == 0
    assert result["prereg_mismatch"] == 1
    assert [item["reason"] for item in result["refusals"]] == ["PREREG_MISMATCH"]
    assert not (log_dir / "forward_log_graded.jsonl").exists()
    refusals = _read_jsonl(log_dir / "forward_log_refusals.jsonl")
    assert len(refusals) == 1
    assert refusals[0]["reason"] == "PREREG_MISMATCH"
    assert refusals[0]["asof"] == sessions[asof_i].isoformat()
    assert refusals[0]["config_id"] == "B0"
    assert set(refusals[0]) == REFUSAL_FIELDS


@pytest.mark.parametrize(
    "violation",
    [
        "collect_lane_env",
        "writer_identity",
        "code_sha",
        "prereg_blob",
        "inputs_digest",
        "Y",
        "issued_at_1659",
        "issued_at_0930",
        "saturday",
    ],
)
def test_issued_admission_excludes_each_single_field_violation(tmp_path, monkeypatch, violation):
    """Finding 5: each §1.1 miss excludes the row in the grader and in readiness."""
    arm(monkeypatch)
    if violation == "saturday":
        saturday = date(2024, 6, 1)
        assert saturday.weekday() == 5
        assert not nyse_calendar.is_session(saturday)
        following = _sessions_from(saturday + timedelta(days=1), 10)
        sessions = [saturday] + following
        close = _close_from_sessions(sessions, np.full(len(sessions), 100.0))
        bad = _issue(asof=saturday.isoformat(), horizon=5, config_id="B0")
    else:
        close, sessions, asof_i, _row, _raw = _one_mature(tmp_path / "seed")
        asof_day = sessions[asof_i]
        overrides: dict = {"asof": asof_day.isoformat(), "horizon": 5, "config_id": "B0"}
        if violation == "collect_lane_env":
            overrides["collect_lane_env"] = "render"
        elif violation == "writer_identity":
            overrides["writer_identity"] = "manual-edit"
        elif violation == "code_sha":
            overrides["code_sha"] = "abc"
        elif violation == "prereg_blob":
            overrides["prereg_blob"] = "abcd"
        elif violation == "inputs_digest":
            overrides["inputs_digest"] = "a" * 63
        elif violation == "Y":
            overrides["Y"] = 1
        elif violation == "issued_at_1659":
            overrides["issued_at"] = _et_stamp(asof_day, 16, 59)
        elif violation == "issued_at_0930":
            nxt = nyse_calendar.sessions_between(asof_day + timedelta(days=1), asof_day + timedelta(days=14))[0]
            overrides["issued_at"] = _et_stamp(nxt, 9, 30)
        bad = _issue(**overrides)

    log_dir = tmp_path / "log"
    _write_lines(log_dir / "forward_log.jsonl", [_line(bad)])
    result = grader.grade(close, ticker=TICKER, store_identity=STORE, log_dir=log_dir)
    assert result["graded"] == 0, violation
    assert result["skipped_non_issued"] == 1, violation
    assert result["refusals"] == [], violation
    assert not (log_dir / "forward_log_graded.jsonl").exists()

    payload = readiness_mod.readiness(log_dir)
    assert payload["cohorts"] == [], violation
    assert payload["excluded"]["non_issued_rows"] == 1, violation
