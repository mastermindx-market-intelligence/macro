"""Tests for the Bottom Ledger P1 — the policy-free bottom-calling learning instrument.

Covers (design: research/signal_engine/BOTTOM_LEDGER_DESIGN.md, PR #3182):
* engine.bottom_ruler.grade_call: exact synthetic pins (known trough / undercut → hand-computed
  numbers), the close_only fallback basis, and immature → None at both window boundaries.
* engine.bottom_ruler.cohort_table / pinpoint: aggregation + pin5/held/broke fractions.
* scripts.grade_bottom_calls: idempotent accrual (second run = byte-identical parquet, no
  regrades), snapshot-shape tolerance (missing lane / missing washout payload), and baseline
  determinism (two builds byte-identical). All store writes are redirected to tmp_path — the
  real data/ tree is never touched (MM_DATA_GUARD; conftest sessionfinish guard).

The grade arithmetic pins here are derived independently by hand (see the module docstring of
each test), so a drift in engine.bottom_ruler that still matched bottom_ruler_study.py would
still break these — they anchor the yardstick to ground truth, not just to the study copy.
"""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import bottom_ruler as BR  # noqa: E402
import scripts.grade_bottom_calls as G  # noqa: E402


# ---------------------------------------------------------------------------
# synthetic OHLC builders — n=90, signal at i=15 (i-PRE=5>=0, i+H=75<90 matured)
# ---------------------------------------------------------------------------
_N, _I = 90, 15


def _series(close, high=None, low=None):
    idx = pd.bdate_range("2024-01-01", periods=_N)
    c = pd.Series(close, index=idx)
    h = pd.Series(high, index=idx) if high is not None else None
    lo = pd.Series(low, index=idx) if low is not None else None
    return idx, c, h, lo


# ---------------------------------------------------------------------------
# grade_call — exact hand-computed pins
# ---------------------------------------------------------------------------
def test_grade_call_deep_undercut_exact():
    """Trough 95 AFTER the signal (t_off=+5); floor F=99 (trailing-20d low, dip is after i);
    forward low 95 undercuts F by 1-95/99=4.04% → 'deep'. MFE spike 130, fwd close 110.
    All numbers are exact under next-close fill=100."""
    i = _I
    close = np.full(_N, 100.0)
    high = np.full(_N, 101.0)
    low = np.full(_N, 99.0)
    low[i + 5] = 95.0           # eventual trough, +5 days from signal
    high[i + 10] = 130.0        # MFE spike (inside high[f+1:i+H+1])
    close[i + BR.H] = 110.0     # fwd60 endpoint
    idx, c, h, lo = _series(close, high, low)

    g = BR.grade_call(c, h, lo, idx[i])
    assert g is not None
    assert g["prox"] == pytest.approx(100 / 95 - 1)        # 0.0526315…
    assert g["t_off"] == 5
    assert g["undercut"] == pytest.approx(1 - 95 / 99)     # 0.0404040…
    assert g["undercut_class"] == "deep"
    assert g["mfe60"] == pytest.approx(130 / 100 - 1)      # 0.30
    assert g["mae60"] == pytest.approx(95 / 100 - 1)       # -0.05
    assert g["fwd60"] == pytest.approx(110 / 100 - 1)      # 0.10
    assert g["basis"] == "ohlc"
    assert BR.pinpoint(g) is False                          # prox 5.26% > 5%


def test_grade_call_pinpoint_and_held_exact():
    """Trough 98 two days BEFORE the signal (t_off=-2); prox 2.04% → pinpoint. Forward low
    never dips below the floor (98) → undercut 0 → 'held'."""
    i = _I
    close = np.full(_N, 100.0)
    high = np.full(_N, 101.0)
    low = np.full(_N, 99.0)
    low[i - 2] = 98.0           # trough already in before the signal
    high[i + 10] = 120.0
    close[i + BR.H] = 105.0
    idx, c, h, lo = _series(close, high, low)

    g = BR.grade_call(c, h, lo, idx[i])
    assert g["t_off"] == -2
    assert g["prox"] == pytest.approx(100 / 98 - 1)        # 0.0204…
    assert g["undercut"] == 0.0
    assert g["undercut_class"] == "held"
    assert BR.pinpoint(g) is True


def test_grade_call_close_only_basis():
    """high/low absent → basis close_only, trough taken from the close series."""
    i = _I
    close = np.full(_N, 100.0)
    close[i + 5] = 95.0
    close[i + BR.H] = 108.0
    idx, c, _, _ = _series(close)

    g = BR.grade_call(c, None, None, idx[i])
    assert g is not None
    assert g["basis"] == "close_only"
    assert g["prox"] == pytest.approx(100 / 95 - 1)
    # floor from close = 100 (dip is after i); undercut 1-95/100 = 0.05 → 'deep' (>0.03,<=0.10)
    assert g["undercut"] == pytest.approx(0.05)
    assert g["undercut_class"] == "deep"


def test_grade_call_immature_returns_none_both_boundaries():
    """< PRE bars before OR < H bars after the signal → None (matured-only, frozen grades)."""
    idx, c, _, _ = _series(np.full(_N, 100.0))
    assert BR.grade_call(c, None, None, idx[85]) is None    # i+H = 145 > n
    assert BR.grade_call(c, None, None, idx[5]) is None      # i-PRE = -5 < 0


def test_grade_call_missing_flag_date_returns_none():
    idx, c, _, _ = _series(np.full(_N, 100.0))
    assert BR.grade_call(c, None, None, pd.Timestamp("1999-01-01")) is None


def test_undercut_class_thresholds():
    """held ≤0.5% / probed ≤3% / deep ≤10% / broke >10% (frozen study thresholds)."""
    assert BR._undercut_class(0.0) == "held"
    assert BR._undercut_class(0.005) == "held"
    assert BR._undercut_class(0.0051) == "probed"
    assert BR._undercut_class(0.03) == "probed"
    assert BR._undercut_class(0.0301) == "deep"
    assert BR._undercut_class(0.10) == "deep"
    assert BR._undercut_class(0.1001) == "broke"


# ---------------------------------------------------------------------------
# cohort_table / pinpoint
# ---------------------------------------------------------------------------
def test_cohort_table_aggregates_and_rates():
    rows = [
        {"source": "board_buy", "lane": "bottom", "prox": 0.02, "undercut": 0.0,
         "undercut_class": "held", "mfe60": 0.1, "fwd60": 0.05},
        {"source": "board_buy", "lane": "bottom", "prox": 0.08, "undercut": 0.15,
         "undercut_class": "broke", "mfe60": 0.2, "fwd60": -0.03},
        {"source": "prophet_plan", "lane": "long", "prox": 0.04, "undercut": 0.01,
         "undercut_class": "probed", "mfe60": 0.3, "fwd60": 0.12},
        # ungraded row (prox None) must be skipped by the cohort summary.
        {"source": "board_buy", "lane": "bottom", "prox": None},
    ]
    tbl = BR.cohort_table(rows, by=["source", "lane"])
    by_key = {(r["source"], r["lane"]): r for r in tbl}
    bb = by_key[("board_buy", "bottom")]
    assert bb["n"] == 2                       # the None row excluded
    assert bb["pin5"] == pytest.approx(0.5)   # one of two prox ≤ 0.05
    assert bb["held_pct"] == pytest.approx(0.5)
    assert bb["broke_pct"] == pytest.approx(0.5)
    assert bb["prox_med"] == pytest.approx(0.05)
    pp = by_key[("prophet_plan", "long")]
    assert pp["n"] == 1 and pp["pin5"] == pytest.approx(1.0)
    # deterministic sorted order by the by-key tuple
    assert [(r["source"], r["lane"]) for r in tbl] == sorted(
        (r["source"], r["lane"]) for r in tbl)


def test_pinpoint_none_and_missing_prox():
    assert BR.pinpoint(None) is False
    assert BR.pinpoint({}) is False
    assert BR.pinpoint({"prox": 0.05}) is True
    assert BR.pinpoint({"prox": 0.0501}) is False


# ---------------------------------------------------------------------------
# grader — accrual, idempotency, shape tolerance, baseline determinism
# ---------------------------------------------------------------------------
def _snapshot_line(as_of, buy=None, watch=None):
    import json
    return json.dumps({"as_of": as_of, "buy": buy or [], "watch": watch or []})


@pytest.fixture()
def _grader_env(tmp_path, monkeypatch):
    """Redirect every grader store/source path into tmp_path (nothing touches real data/)."""
    snaps = tmp_path / "snapshots.jsonl"
    plans = tmp_path / "plans"
    plans.mkdir()
    monkeypatch.setattr(G, "SNAPSHOTS_JSONL", snaps)
    monkeypatch.setattr(G, "PROPHET_PLANS_DIR", plans)
    # price readers point at empty dirs → immature/ungradeable, so nothing matures in these tests
    monkeypatch.setattr(G, "STOCKS_DIR", tmp_path / "stocks_empty")
    monkeypatch.setattr(G, "YAHOO_DIR", tmp_path / "yahoo_empty")
    rows_path = tmp_path / "rows.parquet"
    emit_path = tmp_path / "us_bottom_ledger.json"
    return snaps, plans, rows_path, emit_path


def test_accrual_counts_by_source_and_shape_tolerance(_grader_env):
    snaps, plans, rows_path, emit_path = _grader_env
    import json
    # new-shape buy (lane+conviction+signal), old-shape buy (bare), a watch WITH washout payload,
    # and a watch WITHOUT one (must be ignored — payload not landed yet).
    snaps.write_text("\n".join([
        _snapshot_line("2026-06-30",
                       buy=[{"ticker": "AAA", "lane": "bottom",
                             "conviction": {"score": 0.8}, "signal": {"tier_cascade": "T2"}},
                            {"ticker": "BBB"}],  # old shape, no lane
                       watch=[{"ticker": "CCC", "washout": {"tier": "W1", "weeks_at_floor": 4,
                                                            "late_pct": 0.12}},
                              {"ticker": "DDD"}]),  # no washout payload → skipped
    ]) + "\n")
    (plans / "p1.json").write_text(json.dumps(
        {"asset": "EEE", "signal_date": "2026-06-30", "direction": "long",
         "_conviction_score": 0.6, "_act_level": "act"}))

    doc = G.run_pipeline(rows_path, emit_path, accrue=True,
                         as_of=pd.Timestamp("2026-07-01"), quiet=True)
    assert doc["schema"] == "bottom_ledger/v1"
    assert doc["accrual_by_source"] == {"board_buy": 2, "prophet_plan": 1, "washout_watch": 1}
    assert doc["n_accruing"] == 4
    assert doc["n_matured"] == 0                         # no price history → nothing matures
    assert doc["first_maturity_est"] == G.FIRST_MATURITY_EST
    assert doc["summary"]["pin5"] is None                # nulls printed while unmatured
    assert doc["cohorts"] == []
    # the old-shape buy defaulted lane → "unknown"; washout carried its tier
    store = pd.read_parquet(rows_path)
    lanes = dict(zip(store["ticker"], store["lane"]))
    assert lanes["BBB"] == "unknown"
    assert lanes["CCC"] == "washout"
    assert "DDD" not in set(store["ticker"])             # no-payload watch was not accrued


def test_canonical_prophet_projection_error_fails_closed(tmp_path, monkeypatch, capsys):
    """A corrupt canonical correction store never falls back to raw plan clocks."""
    import json

    root = tmp_path / "repo"
    plans = root / "site" / "prophet" / "plans"
    corrections = root / "data" / "prophet" / "plan_corrections.jsonl"
    plans.mkdir(parents=True)
    corrections.parent.mkdir(parents=True)
    (plans / "bad.json").write_text(json.dumps({
        "schema": "prophet.trade_plan/v1",
        "id": "BAD-BULL-20260702",
        "asset": "BAD",
        "direction": "BULL",
        "signal_date": "2026-07-02",
    }), encoding="utf-8")
    corrections.write_text("{not-json}\n", encoding="utf-8")
    snapshots = root / "data" / "bottom_calls" / "snapshots.jsonl"
    monkeypatch.setattr(G, "SNAPSHOTS_JSONL", snapshots)
    monkeypatch.setattr(G, "PROPHET_PLANS_DIR", plans)

    flags = G.collect_flags()

    assert [row for row in flags if row.get("source") == "prophet_plan"] == []
    assert "canonical Prophet flags withheld" in capsys.readouterr().out


def test_canonical_prophet_flags_obey_date_family_and_both_quarantines(
    tmp_path, monkeypatch
):
    """Legacy formation aliases never become learning dates; all quarantine authority wins."""
    from types import SimpleNamespace
    from engine import prophet_integrity as integrity

    root = tmp_path / "repo"
    plans_dir = root / "site" / "prophet" / "plans"
    plans_dir.mkdir(parents=True)
    monkeypatch.setattr(G, "PROPHET_PLANS_DIR", plans_dir)
    monkeypatch.setattr(
        G, "SNAPSHOTS_JSONL", root / "data" / "bottom_calls" / "missing.jsonl"
    )

    plans = {
        "LEGACY-BULL-20260601": {
            "id": "LEGACY-BULL-20260601", "asset": "LEGACY", "direction": "BULL",
            "signal_date": "2026-06-01", "signal_date_basis": "legacy_formation_alias",
            "price_basis_date": "2026-08-07",
        },
        "EVENT-BULL-20260806": {
            "id": "EVENT-BULL-20260806", "asset": "EVENT", "direction": "BULL",
            "signal_date": "2026-08-06", "signal_date_basis": "tier_event_date",
        },
        "OBS-BULL-20260805": {
            "id": "OBS-BULL-20260805", "asset": "OBS", "direction": "BULL",
            "signal_date": "2026-07-01", "observed_date": "2026-08-05",
            "signal_date_basis": "tier_observation",
        },
        "UNKNOWN-BULL-20260701": {
            "id": "UNKNOWN-BULL-20260701", "asset": "UNKNOWN", "direction": "BULL",
            "signal_date": "2026-07-01",
        },
        "PLANQ-BULL-20260805": {
            "id": "PLANQ-BULL-20260805", "asset": "PLANQ", "direction": "BULL",
            "signal_date": "2026-08-05", "signal_date_basis": "tier_event_date",
        },
        "LEDGERQ-BULL-20260805": {
            "id": "LEDGERQ-BULL-20260805", "asset": "LEDGERQ", "direction": "BULL",
            "signal_date": "2026-08-05", "signal_date_basis": "tier_event_date",
        },
    }
    monkeypatch.setattr(
        integrity,
        "load_effective_plans",
        lambda _root: SimpleNamespace(
            plans=plans, quarantined_ids=frozenset({"PLANQ-BULL-20260805"})
        ),
    )
    monkeypatch.setattr(
        integrity,
        "load_effective_ledger",
        lambda _root: SimpleNamespace(
            quarantined_ids=frozenset({"LEDGERQ-BULL-20260805"})
        ),
    )

    flags = [row for row in G.collect_flags() if row["source"] == "prophet_plan"]
    by_id = {row["source_ref"]: row["flag_date"] for row in flags}
    assert by_id == {
        "LEGACY-BULL-20260601": "2026-08-07",
        "EVENT-BULL-20260806": "2026-08-06",
        "OBS-BULL-20260805": "2026-08-05",
    }


def test_bottom_ledger_projects_corrected_prophet_row_without_mutating_raw(
    tmp_path, monkeypatch
):
    """Keep-union raw history may retain an old date, but only the corrected row learns."""
    from types import SimpleNamespace
    from engine import prophet_integrity as integrity

    root = tmp_path / "repo"
    plans_dir = root / "site" / "prophet" / "plans"
    plans_dir.mkdir(parents=True)
    monkeypatch.setattr(G, "PROPHET_PLANS_DIR", plans_dir)
    plans = {
        "LEGACY-BULL-20260601": {
            "id": "LEGACY-BULL-20260601", "asset": "LEGACY", "direction": "BULL",
            "signal_date": "2026-06-01", "signal_date_basis": "legacy_formation_alias",
            "price_basis_date": "2026-08-07",
        },
        "PLANQ-BULL-20260805": {
            "id": "PLANQ-BULL-20260805", "asset": "PLANQ", "direction": "BULL",
            "signal_date": "2026-08-05", "signal_date_basis": "tier_event_date",
        },
    }
    monkeypatch.setattr(
        integrity,
        "load_effective_plans",
        lambda _root: SimpleNamespace(
            plans=plans, quarantined_ids=frozenset({"PLANQ-BULL-20260805"})
        ),
    )
    monkeypatch.setattr(
        integrity,
        "load_effective_ledger",
        lambda _root: SimpleNamespace(quarantined_ids=frozenset()),
    )

    raw = pd.DataFrame([
        G._flag_row(
            flag_date="2026-06-01", ticker="LEGACY", source="prophet_plan",
            source_ref="LEGACY-BULL-20260601",
        ),
        G._flag_row(
            flag_date="2026-08-07", ticker="LEGACY", source="prophet_plan",
            source_ref="LEGACY-BULL-20260601",
        ),
        G._flag_row(
            flag_date="2026-08-05", ticker="PLANQ", source="prophet_plan",
            source_ref="PLANQ-BULL-20260805",
        ),
        G._flag_row(
            flag_date="2026-08-05", ticker="NOPROV", source="prophet_plan",
        ),
        G._flag_row(flag_date="2026-08-05", ticker="BOARD", source="board_buy"),
    ])[G.STORE_COLS]
    before = raw.copy(deep=True)

    effective, excluded, error = G._project_effective_store(raw)

    assert error is None
    assert excluded == 3
    assert list(zip(effective["source"], effective["ticker"], effective["flag_date"])) == [
        ("prophet_plan", "LEGACY", "2026-08-07"),
        ("board_buy", "BOARD", "2026-08-05"),
    ]
    pd.testing.assert_frame_equal(raw, before)


def test_grader_idempotent_byte_identical_parquet(_grader_env):
    snaps, plans, rows_path, emit_path = _grader_env
    snaps.write_text(_snapshot_line("2026-06-30",
                     buy=[{"ticker": "AAA", "lane": "bottom"}]) + "\n")
    as_of = pd.Timestamp("2026-07-01")
    G.run_pipeline(rows_path, emit_path, accrue=True, as_of=as_of, quiet=True)
    first = rows_path.read_bytes()
    # second accrue with the SAME inputs must not re-append or re-grade → identical bytes
    G.run_pipeline(rows_path, emit_path, accrue=True, as_of=as_of, quiet=True)
    assert rows_path.read_bytes() == first


def test_read_only_run_does_not_write_rows(_grader_env):
    """accrue=False (non-nightly) must NOT create/advance the rows store (only re-emit)."""
    snaps, plans, rows_path, emit_path = _grader_env
    snaps.write_text(_snapshot_line("2026-06-30", buy=[{"ticker": "AAA"}]) + "\n")
    G.run_pipeline(rows_path, emit_path, accrue=False,
                   as_of=pd.Timestamp("2026-07-01"), quiet=True)
    assert not rows_path.exists()                        # no forward advance
    assert emit_path.exists()                            # display artifact still emitted


def test_frozen_grade_never_regraded(_grader_env, monkeypatch):
    """A row already graded=True is never regraded, even if grade_call would now return a value."""
    snaps, plans, rows_path, emit_path = _grader_env
    snaps.write_text(_snapshot_line("2026-06-30", buy=[{"ticker": "AAA"}]) + "\n")
    # first accrue: no prices → ungraded
    G.run_pipeline(rows_path, emit_path, accrue=True,
                   as_of=pd.Timestamp("2026-07-01"), quiet=True)
    store = pd.read_parquet(rows_path)
    # force the row to graded=True with a sentinel grade, persist it
    store.loc[:, "graded"] = True
    store.loc[:, "prox"] = 0.123
    G._atomic_write_parquet(rows_path, store)
    # spy: grade_call must never be called for an already-graded row
    called = {"n": 0}
    real = BR.grade_call
    monkeypatch.setattr(BR, "grade_call", lambda *a, **k: (called.__setitem__("n", called["n"] + 1), real(*a, **k))[1])
    G.run_pipeline(rows_path, emit_path, accrue=True,
                   as_of=pd.Timestamp("2027-01-01"), quiet=True)
    assert called["n"] == 0
    assert pd.read_parquet(rows_path)["prox"].iloc[0] == pytest.approx(0.123)


def test_baseline_deterministic(monkeypatch, tmp_path):
    """Two build_baseline() runs over the same panel produce byte-identical JSON."""
    import json
    # tiny synthetic panel so the test is fast and self-contained
    stocks = tmp_path / "stocks"
    stocks.mkdir()
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2015-01-01", periods=400)
    for t in ("AAA", "BBB"):
        walk = 100 + np.cumsum(rng.normal(0, 1, len(idx)))
        df = pd.DataFrame({"close": walk, "high": walk + 1, "low": walk - 1,
                           "volume": 1e6}, index=idx)
        df.to_parquet(stocks / f"{t}.parquet")
    monkeypatch.setattr(G, "STOCKS_DIR", stocks)
    d1 = G.build_baseline()
    d2 = G.build_baseline()
    s1 = json.dumps(d1, ensure_ascii=False, indent=1, default=str, sort_keys=True)
    s2 = json.dumps(d2, ensure_ascii=False, indent=1, default=str, sort_keys=True)
    assert s1 == s2
    assert d1["schema"] == "bottom_ruler_baseline/v1"


# ---------------------------------------------------------------------------
# CLOCK CONTRACT (engine/ledger_clock.py)
#
# Regression home for the production failure of 2026-09-17: the nightly advancer derived
# `as_of` with `pd.Timestamp.utcnow()` (tz-AWARE) and compared it against `pd.Timestamp(
# flag_date)` (tz-naive, because every producer writes a plain YYYY-MM-DD), so
# `mature_rows()` raised
#     TypeError: Cannot compare tz-naive and tz-aware timestamps
# on EVERY run since the instrument was born — before its first write. `|| true` in
# daily.yml swallowed it, so the nightly reported success while neither
# data/bottom_ledger/rows.parquet nor site/factordata/us_bottom_ledger.json ever existed.
#
# WHY THE SUITE DID NOT CATCH IT: every pre-existing pipeline test points the price readers
# at EMPTY directories, so `_read_prices` returns None and every row is skipped BEFORE the
# maturity comparison is ever reached. `_maturing_env` below closes that gap — it ships real
# price parquets so rows actually mature, which is the only way this line gets executed.
# ---------------------------------------------------------------------------
import json as _json  # noqa: E402

from engine import ledger_clock as LC  # noqa: E402


def _write_prices(dirpath, tickers, *, start="2026-01-01", periods=200, tz=None):
    """Write OHLC price parquets with a V-shaped path so grades are well-defined."""
    dirpath.mkdir(parents=True, exist_ok=True)
    idx = pd.bdate_range(start, periods=periods, tz=tz)
    n = len(idx)
    trough = n // 3
    close = np.concatenate([np.linspace(120, 90, trough), np.linspace(90, 135, n - trough)])
    for t in tickers:
        pd.DataFrame({"close": close, "high": close * 1.01,
                      "low": close * 0.99, "volume": 1_000_000.0},
                     index=idx).to_parquet(dirpath / f"{t}.parquet")
    return idx


@pytest.fixture()
def _maturing_env(tmp_path, monkeypatch):
    """Like `_grader_env`, but with REAL price history so rows genuinely mature."""
    snaps = tmp_path / "snapshots.jsonl"
    plans = tmp_path / "plans"
    plans.mkdir()
    stocks = tmp_path / "stocks"
    idx = _write_prices(stocks, ["AAA", "BBB"])
    monkeypatch.setattr(G, "SNAPSHOTS_JSONL", snaps)
    monkeypatch.setattr(G, "PROPHET_PLANS_DIR", plans)
    monkeypatch.setattr(G, "STOCKS_DIR", stocks)
    monkeypatch.setattr(G, "YAHOO_DIR", tmp_path / "yahoo_empty")
    # a flag with >= H trading bars of history on both sides
    flag = str(idx[G.BR.PRE + 5].date())
    snaps.write_text(_snapshot_line(flag, buy=[{"ticker": "AAA", "lane": "bottom"},
                                               {"ticker": "BBB", "lane": "bottom"}]) + "\n")
    return snaps, plans, tmp_path / "rows.parquet", tmp_path / "us_bottom_ledger.json", flag


# --- the contract itself ---------------------------------------------------
def test_ledger_clock_is_date_only_tz_naive_and_midnight():
    """Date-only, UTC-aware, offset-bearing and clock-bearing inputs all land on one form."""
    for value in ["2026-09-17",
                  dt.date(2026, 9, 17),
                  pd.Timestamp("2026-09-17"),
                  pd.Timestamp("2026-09-17 15:30"),            # naive + clock
                  pd.Timestamp("2026-09-17", tz="UTC"),        # UTC-aware
                  "2026-09-17T20:00:00-04:00",                 # offset-bearing
                  np.datetime64("2026-09-17")]:
        got = LC.to_ledger_date(value)
        assert got.tz is None, f"{value!r} kept a timezone"
        assert got == pd.Timestamp("2026-09-17"), f"{value!r} -> {got!r}"
        assert LC.ledger_date_str(value) == "2026-09-17"


def test_ledger_clock_reads_an_offset_at_its_own_wall_clock():
    """A stamped offset states which civil day it belongs to in the zone that stamped it.

    Converting to UTC first would file an Asian session a day early; this pins the rule.
    """
    assert LC.ledger_date_str(pd.Timestamp("2026-09-18 00:00", tz="Asia/Shanghai")) == "2026-09-18"
    assert LC.ledger_date_str(pd.Timestamp("2026-09-17 16:00", tz="US/Eastern")) == "2026-09-17"


def test_ledger_clock_today_is_tz_naive_and_equals_the_old_utcnow_default():
    """`today_ledger_date()` must preserve the previous default's VALUE without its tz.

    The old `pd.Timestamp.utcnow().normalize()` was the UTC civil date — correct in value,
    fatal in type. This is the exact regression: a tz-aware `as_of` is what crashed
    production, so the default must be tz-naive AND still the UTC civil date.
    """
    today = LC.today_ledger_date()
    assert today.tz is None
    assert today == today.normalize()
    assert today == pd.Timestamp(pd.Timestamp.now("UTC").date())


@pytest.mark.parametrize("wall,zone,ambiguous", [
    ("2026-03-08 03:30", "US/Eastern", None),     # spring forward (gap edge)
    ("2026-11-01 01:30", "US/Eastern", True),     # fall back, DST reading
    ("2026-11-01 01:30", "US/Eastern", False),    # fall back, standard reading
    ("2026-10-25 02:30", "Europe/Berlin", True),  # EU fall back
])
def test_ledger_clock_dst_boundaries_are_deterministic(wall, zone, ambiguous):
    """A DST offset change can never move a ledger date.

    Both readings of an ambiguous wall clock name the same civil day, so the ledger date is
    single-valued across a transition.
    """
    ts = (pd.Timestamp(wall).tz_localize(zone) if ambiguous is None
          else pd.Timestamp(wall).tz_localize(zone, ambiguous=ambiguous))
    assert LC.ledger_date_str(ts) == wall.split()[0]


def test_ledger_clock_rejects_rather_than_guesses():
    """An unreadable date is REJECTED — never coerced into a plausible-looking one."""
    for bad in [None, "", "   ", "not-a-date", pd.NaT, float("nan")]:
        with pytest.raises(LC.ClockContractError):
            LC.to_ledger_date(bad, field="flag_date")
        assert LC.to_ledger_date_or_none(bad) is None


# --- the exact production failure ------------------------------------------
def test_production_mixed_tz_maturity_comparison_no_longer_raises(_maturing_env):
    """THE production repro: a tz-aware `as_of` meeting a date-only `flag_date`.

    Before the contract this raised `TypeError: Cannot compare tz-naive and tz-aware
    timestamps` inside `mature_rows()` — the first statement after the price read — which is
    exactly how the nightly died before writing anything.
    """
    snaps, plans, rows_path, emit_path, flag = _maturing_env
    tz_aware_as_of = pd.Timestamp.now("UTC").normalize()      # what utcnow() produced
    assert tz_aware_as_of.tz is not None                      # the fixture is the real shape
    doc = G.run_pipeline(rows_path, emit_path, accrue=True, as_of=tz_aware_as_of, quiet=True)
    assert doc["advance"]["status"] == G.ADVANCE_ADVANCED
    assert doc["n_matured"] == 2                              # and it actually GRADED
    assert rows_path.exists()


def test_maturity_path_grades_and_freezes_with_real_prices(_maturing_env):
    """The coverage gap that let the crash ship: rows that genuinely mature.

    Every pre-existing pipeline test pointed the price readers at empty dirs, so the maturity
    comparison was never executed. This exercises it end to end.
    """
    snaps, plans, rows_path, emit_path, flag = _maturing_env
    doc = G.run_pipeline(rows_path, emit_path, accrue=True,
                         as_of=pd.Timestamp("2027-01-01"), quiet=True)
    assert doc["advance"]["n_newly_graded"] == 2
    store = pd.read_parquet(rows_path)
    assert bool(store["graded"].all())
    assert set(store["grade_asof"]) == {"2027-01-01"}         # contract-shaped, date-only
    for field in ("prox", "mfe60", "mae60", "fwd60", "undercut"):
        assert store[field].notna().all()


def test_grade_call_resolves_a_tz_aware_price_index_instead_of_silently_returning_none():
    """The quiet twin of the crash.

    A tz-mismatched price index matched NO bar and `grade_call` returned None — so a row
    would accrue forever and never mature, with no error anywhere. All tz spellings must now
    produce the identical frozen grade.
    """
    idx = pd.bdate_range("2024-01-01", periods=90)
    close = np.linspace(100, 120, 90)
    base = BR.grade_call(pd.Series(close, index=idx), pd.Series(close * 1.01, index=idx),
                         pd.Series(close * 0.99, index=idx), "2024-01-22")
    assert base is not None
    for tz in ("America/New_York", "Asia/Shanghai", "UTC"):
        aware = pd.bdate_range("2024-01-01", periods=90, tz=tz)
        got = BR.grade_call(pd.Series(close, index=aware), pd.Series(close * 1.01, index=aware),
                            pd.Series(close * 0.99, index=aware), "2024-01-22")
        assert got == base, f"tz={tz} drifted from the naive grade"
    # and a tz-aware flag_date against a naive index
    assert BR.grade_call(pd.Series(close, index=idx), pd.Series(close * 1.01, index=idx),
                         pd.Series(close * 0.99, index=idx),
                         pd.Timestamp("2024-01-22", tz="UTC")) == base


# --- persisted rows, replay, and explicit --as-of --------------------------
def test_historical_persisted_dates_are_renormalized_without_touching_frozen_grades(_maturing_env):
    """A store written with datetime64 / tz-aware / clock-bearing dates is re-spelled once.

    Parquet preserves whatever the writer used, so a historical store can hold the SAME
    session under several spellings. Left alone the accrual identity (flag_date, ticker,
    source) would double-accrue it. Re-spelling is representation ONLY: no grade field and no
    `graded` flag may move.
    """
    snaps, plans, rows_path, emit_path, flag = _maturing_env
    G.run_pipeline(rows_path, emit_path, accrue=True,
                   as_of=pd.Timestamp("2027-01-01"), quiet=True)
    graded = pd.read_parquet(rows_path)
    assert bool(graded["graded"].all())
    frozen = graded.set_index("ticker")[G.GRADE_FIELDS].copy()

    # rewrite the persisted store with drifted date spellings for the SAME sessions
    drifted = graded.copy()
    drifted.loc[drifted.index[0], "flag_date"] = f"{flag}T00:00:00+00:00"   # tz-aware string
    drifted.loc[drifted.index[1], "flag_date"] = f"{flag} 09:30:00"        # clock-bearing
    G._atomic_write_parquet(rows_path, drifted)

    doc = G.run_pipeline(rows_path, emit_path, accrue=True,
                         as_of=pd.Timestamp("2027-01-02"), quiet=True)
    after = pd.read_parquet(rows_path)
    assert doc["advance"]["store_repairs"]["renormalized"] == 2
    assert set(after["flag_date"]) == {flag}          # one canonical spelling
    assert len(after) == len(graded)                  # the drift did NOT double-accrue
    assert doc["advance"]["n_newly_graded"] == 0      # nothing regraded
    pd.testing.assert_frame_equal(after.set_index("ticker")[G.GRADE_FIELDS], frozen)
    assert set(after["grade_asof"]) == {"2027-01-01"}  # original freeze stamp survives


def test_replay_grade_is_independent_of_as_of(_maturing_env, tmp_path):
    """Historical replay is deterministic: `as_of` gates ELIGIBILITY, never the grade.

    `grade_call` reads only [flag-PRE, flag+H], so a row graded at any matured `as_of` must
    produce identical numbers — which is what makes the one-grader freeze safe.
    """
    snaps, plans, rows_path, emit_path, flag = _maturing_env
    grades = {}
    for label, as_of in [("early", "2026-12-01"), ("late", "2028-06-15")]:
        rp, ep = tmp_path / f"{label}.parquet", tmp_path / f"{label}.json"
        G.run_pipeline(rp, ep, accrue=True, as_of=pd.Timestamp(as_of), quiet=True)
        s = pd.read_parquet(rp)
        assert bool(s["graded"].all())
        grades[label] = s.set_index("ticker")[G.GRADE_FIELDS]
    pd.testing.assert_frame_equal(grades["early"], grades["late"])


def test_explicit_as_of_gates_eligibility_deterministically(_maturing_env, tmp_path):
    """An `--as-of` before the maturity window grades nothing; after it, grades everything."""
    snaps, plans, rows_path, emit_path, flag = _maturing_env
    too_early = pd.Timestamp(flag) + pd.Timedelta(days=BR.H - 1)   # one day short of the gate
    doc = G.run_pipeline(rows_path, emit_path, accrue=True, as_of=too_early, quiet=True)
    assert doc["advance"]["n_newly_graded"] == 0
    assert doc["as_of"] == too_early.strftime("%Y-%m-%d")
    doc2 = G.run_pipeline(rows_path, emit_path, accrue=True,
                          as_of=pd.Timestamp("2027-01-01"), quiet=True)
    assert doc2["advance"]["n_newly_graded"] == 2


def test_cli_rejects_an_unreadable_as_of_instead_of_grading_blind(monkeypatch, capsys):
    """A run that cannot say WHEN it is must not grade anything."""
    monkeypatch.setattr(sys, "argv", ["grade_bottom_calls", "--as-of", "not-a-date"])
    with pytest.raises(SystemExit) as exc:
        G.main()
    assert exc.value.code == 2
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line.startswith("::error title=bottom-ledger-bad-as-of::")   # annotation law


# --- failure observability -------------------------------------------------
def test_failed_advance_is_stamped_in_the_artifact_and_reraises(_maturing_env, monkeypatch, capsys):
    """A dead advancer can never present as a fresh successful grading run.

    This is the property `|| true` destroyed: the store must be left untouched, the display
    artifact must say `advance.status == "failed"`, a line-start `::error` must be printed,
    and the exception must propagate so the process exits non-zero.
    """
    snaps, plans, rows_path, emit_path, flag = _maturing_env
    G.run_pipeline(rows_path, emit_path, accrue=True,
                   as_of=pd.Timestamp("2027-01-01"), quiet=True)
    good_store = rows_path.read_bytes()

    boom = TypeError("Cannot compare tz-naive and tz-aware timestamps")
    monkeypatch.setattr(G, "mature_rows", lambda *a, **k: (_ for _ in ()).throw(boom))
    with pytest.raises(TypeError):
        G.run_pipeline(rows_path, emit_path, accrue=True,
                       as_of=pd.Timestamp("2027-02-01"), quiet=True)

    assert rows_path.read_bytes() == good_store          # no partial advance, no regrade
    doc = _json.loads(emit_path.read_text(encoding="utf-8"))
    assert doc["advance"]["status"] == G.ADVANCE_FAILED
    assert "Cannot compare tz-naive and tz-aware timestamps" in doc["advance"]["error"]
    assert doc["advance"]["as_of"] == "2027-02-01"
    assert doc["n_matured"] == 2                         # last good state still reported
    errs = [l for l in capsys.readouterr().out.splitlines()
            if l.startswith("::error title=bottom-ledger-advance-failed::")]
    assert len(errs) == 1, "the failure must emit exactly one line-start ::error annotation"


def test_read_only_run_is_labelled_read_only_not_advanced(_grader_env):
    """A non-nightly re-emit must not look like a forward advance."""
    snaps, plans, rows_path, emit_path = _grader_env
    snaps.write_text(_snapshot_line("2026-06-30", buy=[{"ticker": "AAA"}]) + "\n")
    doc = G.run_pipeline(rows_path, emit_path, accrue=False,
                         as_of=pd.Timestamp("2026-07-01"), quiet=True)
    assert doc["advance"]["status"] == G.ADVANCE_READ_ONLY
    assert doc["advance"]["n_newly_graded"] is None


def test_unreadable_store_never_silently_becomes_an_empty_one(_maturing_env):
    """A corrupt store must NOT read as empty — that would re-accrue and regrade everything."""
    snaps, plans, rows_path, emit_path, flag = _maturing_env
    G.run_pipeline(rows_path, emit_path, accrue=True,
                   as_of=pd.Timestamp("2027-01-01"), quiet=True)
    rows_path.write_bytes(b"this is not a parquet file")
    with pytest.raises(RuntimeError, match="store unreadable"):
        G.run_pipeline(rows_path, emit_path, accrue=True,
                       as_of=pd.Timestamp("2027-01-02"), quiet=True)


def test_unreadable_capture_date_is_withheld_and_annotated(_grader_env, capsys):
    """A producer date the contract cannot read is withheld + announced, never accrued.

    Accruing it would create a row that can never mature and never explain why.
    """
    snaps, plans, rows_path, emit_path = _grader_env
    snaps.write_text("\n".join([
        _snapshot_line("2026-06-30", buy=[{"ticker": "AAA"}]),
        _snapshot_line("not-a-date", buy=[{"ticker": "BBB"}]),
    ]) + "\n")
    doc = G.run_pipeline(rows_path, emit_path, accrue=True,
                         as_of=pd.Timestamp("2026-07-01"), quiet=True)
    assert doc["accrual_by_source"] == {"board_buy": 1}
    warns = [l for l in capsys.readouterr().out.splitlines()
             if l.startswith("::warning title=bottom-ledger-unreadable-capture-date::")]
    assert len(warns) == 1


def test_grade_call_keeps_ohlc_alignment_when_close_has_holes():
    """`c.dropna()` can be SHORTER than high/low — the contract re-key must not mis-align.

    Guards the alignment path introduced with the clock contract: a ragged close must still
    resolve real high/low (basis "ohlc"), not silently degrade to the close_only fallback.
    """
    idx = pd.bdate_range("2024-01-01", periods=100)
    close = np.linspace(100, 130, 100).astype(float)
    close[5] = close[7] = np.nan
    hi = pd.Series(close * 1.01, index=idx).ffill()
    lo = pd.Series(close * 0.99, index=idx).ffill()
    got = BR.grade_call(pd.Series(close, index=idx), hi, lo, "2024-01-25")
    assert got is not None and got["basis"] == "ohlc"
    aware = pd.bdate_range("2024-01-01", periods=100, tz="America/New_York")
    assert BR.grade_call(pd.Series(close, index=aware),
                         pd.Series(hi.to_numpy(), index=aware),
                         pd.Series(lo.to_numpy(), index=aware), "2024-01-25") == got
