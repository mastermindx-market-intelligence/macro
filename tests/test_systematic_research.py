"""Systematic Strategies research engine — discriminating tests.

Every test here earns its place by DISCRIMINATING: it fails if the engine
grants a post-close entrant an overnight gap it could not have held, if it turns
missing liquidity into zero impact, if it invents a zero for a metric it could
not compute, if it leaks future rows into a cutoff, or if two identical runs
disagree. A test that would still pass against a naive implementation is not
included.

The engine is RESEARCH_ONLY. These tests deliberately assert the negative
properties too: capital is never eligible, prospective is never started, and no
universal Sharpe threshold exists anywhere in the module.
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
import pandas as pd
import pytest

from engine import systematic_research as sr
from engine.validation import (
    CapacityBlocked,
    NextOpenError,
    backtest_core,
    next_open_sim,
)
from scripts.build_systematic_research import (
    METADATA_FILENAME,
    InputRefused,
    build_parser,
    load_inputs,
    main as cli_main,
)

GENERATED_AT = "2026-10-22T09:00:00Z"
AS_OF = "2026-03-02"
CODE_REV = "0123456789abcdef0123456789abcdef01234567"
DATA_REV = "fixture-revision-1"
COST_BPS = 10.0

ALL_BASIS = {c: "split_adjusted" for c in ("open", "high", "low", "close", "volume")}


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _sessions(n: int, start: str = "2023-01-02") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def _make_frame(n: int = 320, seed: int = 11, start: str = "2023-01-02",
                *, drift: float = 0.0006, out_name: str = "fixture") -> pd.DataFrame:
    """Synthetic but structurally honest OHLCV with a real available_at column."""
    rng = np.random.default_rng(seed)
    idx = _sessions(n, start)
    steps = rng.normal(drift, 0.017, n)
    close = 100.0 * np.exp(np.cumsum(steps))
    open_ = np.empty(n)
    open_[0] = close[0] * (1.0 - steps[0])
    open_[1:] = close[:-1]
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, 0.004, n)))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, 0.004, n)))
    volume = rng.uniform(4.0e6, 9.0e6, n)
    df = pd.DataFrame({"open": open_, "high": high, "low": low,
                       "close": close, "volume": volume}, index=idx)
    df["available_at"] = pd.DatetimeIndex(idx) + pd.Timedelta(hours=21)
    df.index.name = "date"
    df.attrs.update({"adjustment_basis": dict(ALL_BASIS), "synthetic": True,
                     "source": out_name})
    return df


def _price_frame(df: pd.DataFrame, ticker: str = "AAA", **kw) -> sr.PriceFrame:
    attrs = df.attrs
    return sr.PriceFrame(
        frame=df.drop(columns=["available_at"]),
        available_at=pd.Series(df["available_at"], index=df.index),
        adjustment_basis=attrs.get("adjustment_basis", dict(ALL_BASIS)),
        synthetic=attrs.get("synthetic", True),
        source=attrs.get("source", "fixture"),
        ticker=ticker,
        **kw,
    )


def _frames(n: int = 320, tickers: tuple[str, ...] = ("AAA", "BBB"),
            seed: int = 11, **kw) -> dict[str, sr.PriceFrame]:
    return {t: _price_frame(_make_frame(n, seed=seed + i, **kw), ticker=t)
            for i, t in enumerate(tickers)}


def _last_session(frames) -> str:
    if not frames:
        return AS_OF
    return max(pf.frame.index.max() for pf in frames.values()).date().isoformat()


def _report(frames=None, **kw):
    given = frames if frames is not None else _frames()
    opts = dict(as_of=_last_session(given), generated_at=GENERATED_AT,
                code_revision=CODE_REV, data_revision=DATA_REV, cost_bps=COST_BPS,
                expected_last_session=_last_session(given))
    opts.update(kw)
    return sr.build_report(given, **opts)


def _by_id(report, key):
    return next(s for s in report["strategies"] if s["id"] == key)


# --------------------------------------------------------------------------- #
# 1. timing — the closed-bar law
# --------------------------------------------------------------------------- #
def test_post_close_entrant_cannot_capture_the_next_open_gap():
    """+10% happens at open[t+1]. An allocation decided from close[t] fills AT
    open[t+1], so it earns nothing of it. A close-to-close engine would hand it
    the whole move."""
    idx = pd.bdate_range("2024-01-01", periods=5)
    open_ = pd.Series([100.0, 100.0, 100.0, 110.0, 110.0], index=idx)
    close = pd.Series([100.0, 100.0, 100.0, 110.0, 110.0], index=idx)
    # decided long from close of session 2 (which closed at 100), fills at open 3 (110)
    alloc = pd.Series([0.0, 0.0, 1.0, 1.0, 0.0], index=idx)

    honest = next_open_sim(open_, close, alloc, cost_bps=0.0)
    assert honest["pos"].iloc[3] == 1.0, "the fill must be at the NEXT open, not the signal close"
    assert honest["ret"].max() == pytest.approx(0.0), "a post-close entrant captured the gap"
    assert honest["benchmark_open_to_open"].max() == pytest.approx(0.10)

    # The legacy close-to-close engine DOES hand the same decision the gap, which
    # is exactly why it is not the engine for closed-bar signals.
    legacy = backtest_core(close, alloc, cost_bps=0.0)
    assert float(legacy["net"].max()) == pytest.approx(0.10)


def test_overnight_gap_is_retained_by_whoever_already_held_it():
    """The same +10% gap IS earned by a position that filled before it."""
    idx = pd.bdate_range("2024-01-01", periods=5)
    open_ = pd.Series([100.0, 100.0, 100.0, 110.0, 110.0], index=idx)
    close = pd.Series([100.0, 100.0, 100.0, 110.0, 110.0], index=idx)
    # decided from close of session 1, fills at open 2 (100) — before the gap
    alloc = pd.Series([0.0, 1.0, 1.0, 1.0, 0.0], index=idx)

    sim = next_open_sim(open_, close, alloc, cost_bps=0.0)
    assert sim["pos"].iloc[2] == 1.0
    assert sim["ret"].iloc[2] == pytest.approx(0.10), "overnight held risk was discarded"


def test_session_zero_opens_flat_because_there_is_no_prior_close():
    idx = pd.bdate_range("2024-01-01", periods=4)
    open_ = pd.Series([100.0, 100.0, 130.0, 160.0], index=idx)
    close = open_.copy()
    alloc = pd.Series([1.0, 1.0, 1.0, 0.0], index=idx)   # "long" on the very first bar
    sim = next_open_sim(open_, close, alloc, cost_bps=0.0)
    assert sim["pos"].iloc[0] == 0.0
    assert sim["equity"].iloc[0] == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# 2. costs — explicit, on real notional, both directions
# --------------------------------------------------------------------------- #
def test_cost_is_charged_on_the_initial_buy_and_on_the_sale():
    idx = pd.bdate_range("2024-01-01", periods=5)
    open_ = pd.Series([100.0, 100.0, 100.0, 110.0, 110.0], index=idx)
    close = open_.copy()
    alloc = pd.Series([0.0, 1.0, 1.0, 0.0, 0.0], index=idx)   # buy at open 2, sell at open 4
    sim = next_open_sim(open_, close, alloc, cost_bps=10.0)

    assert sim["pos"].iloc[2] == 1.0 and sim["pos"].iloc[4] == 0.0
    buy = sim["cost"].iloc[2]
    sell = sim["cost"].iloc[4]
    rate = COST_BPS / 1e4
    assert buy == pytest.approx(1.0 * rate, rel=1e-9), "the initial buy was free"
    assert sell > 0.0, "the sale was free"
    # Both legs are paid. The book also rebalances between them (a marked book is
    # not frozen), so the total is at least the two explicit legs, never less.
    assert sim["total_cost_fraction"] == pytest.approx(float(sim["cost"].sum()), rel=1e-9)
    assert sim["total_cost_fraction"] >= buy + sell - 1e-12
    assert sim["equity"].iloc[-1] < sim["gross_equity"].iloc[-1]


def test_book_stays_bounded_long_and_cash_with_no_leverage_and_no_short():
    idx = _sessions(120)
    rng = np.random.default_rng(3)
    close = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, 120))), index=idx)
    open_ = close.shift(1).fillna(close.iloc[0])
    alloc = pd.Series(rng.choice([0.0, 0.35, 0.7, 1.0], 120), index=idx)
    sim = next_open_sim(open_, close, alloc, cost_bps=25.0)

    assert sim["pos"].min() >= 0.0 and sim["pos"].max() <= 1.0
    assert sim["equity"].min() > 0.0
    assert (sim["turnover"] >= 0.0).all()


@pytest.mark.parametrize("bad_cost", [-0.0001, float("nan"), float("inf")])
def test_negative_or_non_finite_cost_is_refused_not_turned_into_a_rebate(bad_cost):
    idx = _sessions(10)
    close = pd.Series(np.linspace(100.0, 110.0, 10), index=idx)
    with pytest.raises(NextOpenError, match="cost_bps"):
        next_open_sim(close, close, pd.Series(1.0, index=idx), cost_bps=bad_cost)


# --------------------------------------------------------------------------- #
# 3. bad fills are refused, never zeroed
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("column,value", [
    ("open", 0.0), ("open", -1.0), ("open", float("nan")),
    ("close", 0.0), ("close", float("inf")),
])
def test_non_positive_or_non_finite_price_refuses_instead_of_granting_zero_return(column, value):
    idx = _sessions(10)
    frame = pd.DataFrame({c: np.linspace(100.0, 110.0, 10) for c in
                          ("open", "high", "low", "close")}, index=idx)
    frame.loc[frame.index[4], column] = value
    alloc = pd.Series(1.0, index=idx)
    with pytest.raises(NextOpenError, match="not_positive_finite"):
        next_open_sim(frame["open"], frame["close"], alloc, cost_bps=0.0)


def test_non_finite_allocation_is_refused_rather_than_read_as_flat():
    idx = _sessions(10)
    close = pd.Series(np.linspace(100.0, 110.0, 10), index=idx)
    alloc = pd.Series(1.0, index=idx)
    alloc.iloc[5] = float("nan")
    with pytest.raises(NextOpenError, match="allocation_not_finite"):
        next_open_sim(close, close, alloc, cost_bps=0.0)


@pytest.mark.parametrize("bad", [-0.01, 1.01, 2.0])
def test_allocation_outside_long_cash_bounds_is_refused(bad):
    idx = _sessions(10)
    close = pd.Series(np.linspace(100.0, 110.0, 10), index=idx)
    alloc = pd.Series(0.5, index=idx)
    alloc.iloc[3] = bad
    with pytest.raises(NextOpenError, match="allocation_outside_long_cash_bounds"):
        next_open_sim(close, close, alloc, cost_bps=0.0)


# --------------------------------------------------------------------------- #
# 4. liquidity blocks capacity instead of becoming zero impact
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("adv_value", [0.0, -1.0, float("nan")])
def test_missing_or_non_positive_adv_blocks_capacity(adv_value):
    idx = _sessions(30)
    close = pd.Series(np.linspace(100.0, 130.0, 30), index=idx)
    alloc = pd.Series(1.0, index=idx)
    with pytest.raises(CapacityBlocked, match="dollar_adv"):
        next_open_sim(close, close, alloc, cost_bps=0.0,
                      dollar_adv=pd.Series(adv_value, index=idx), aum_usd=1e6)


def test_partial_impact_configuration_is_refused_not_silently_dropped():
    idx = _sessions(30)
    close = pd.Series(np.linspace(100.0, 130.0, 30), index=idx)
    alloc = pd.Series(1.0, index=idx)
    with pytest.raises(NextOpenError, match="impact_config_incomplete"):
        next_open_sim(close, close, alloc, cost_bps=0.0,
                      dollar_adv=pd.Series(1e8, index=idx))
    with pytest.raises(NextOpenError, match="impact_config_incomplete"):
        next_open_sim(close, close, alloc, cost_bps=0.0, aum_usd=1e6)


def test_report_blocks_when_liquidity_cannot_support_the_requested_capacity():
    zero_volume = _frames(tickers=("AAA",))
    for pf in zero_volume.values():
        pf.frame["volume"] = 0.0
    report = _report(zero_volume, aum_usd=5e6)
    assert report["status"] == "inputs_blocked"
    assert report["data_health"]["state"] == "blocked"
    for row in report["strategies"]:
        assert row["historical"]["state"] == "unavailable"
        assert row["historical"]["net_sharpe"] is None
        assert row["capital_eligible"] is False
        assert any("BLOCKED" in b for b in row["blockers"])


def test_capacity_is_not_claimed_when_impact_was_never_modelled():
    report = _report()
    for row in report["strategies"]:
        joined = " ".join(row["historical"]["limitations"])
        assert "NOT modelled" in joined
        assert "capacity_usd" not in json.dumps(report)   # no capacity number exists


# --------------------------------------------------------------------------- #
# 5. point-in-time discipline
# --------------------------------------------------------------------------- #
def test_prices_and_metadata_after_the_cutoff_never_enter_it():
    df = _make_frame(300)
    early = sr.PriceFrame(
        frame=df.drop(columns=["available_at"]),
        available_at=pd.Series(df["available_at"], index=df.index),
        adjustment_basis=dict(ALL_BASIS), synthetic=True, ticker="AAA",
    )
    clean, reasons, detail = sr.validate_price_frame(early, sr._cutoff("2023-11-06"))
    assert reasons == []
    kept_through = clean.index.max()
    assert detail["future_rows_excluded"] == int((df.index > kept_through).sum())
    assert (df.index > kept_through).sum() > 0, "the fixture must actually contain future rows"
    assert clean.index.max() == df.index[df.index <= kept_through].max()
    assert len(clean) < len(df), "future rows entered the cutoff"


def test_appending_future_rows_cannot_change_reported_history():
    """Append-future invariance: the discriminating test. A reader that forgets
    the cutoff leaks tomorrow into today's Sharpe."""
    base = _frames()
    cutoff = _last_session(base)          # the cutoff must NOT move with the data
    base_report = _report(base, as_of=cutoff, expected_last_session=cutoff)
    assert _by_id(base_report, "tsmom_200")["historical"]["state"] == "available"

    extended = {}
    for ticker, pf in base.items():
        extra = _make_frame(40, seed=777, start="2026-06-01")   # strictly after cutoff
        grown = pd.concat([pf.frame, extra.drop(columns=["available_at"])])
        avail = pd.concat([pf.available_at,
                           pd.Series(extra["available_at"], index=extra.index)])
        assert avail.max() > pd.Timestamp(cutoff) + pd.Timedelta(days=1)
        extended[ticker] = sr.PriceFrame(
            frame=grown, available_at=avail, adjustment_basis=dict(ALL_BASIS),
            synthetic=True, ticker=ticker)
    grown_report = _report(extended, as_of=cutoff, expected_last_session=cutoff)

    for key in sr.CANDIDATE_KEYS:
        before = _by_id(base_report, key)["historical"]
        after = _by_id(grown_report, key)["historical"]
        assert after == before, f"{key} history moved when only future rows were appended"


def test_observation_cannot_be_available_before_it_happened():
    df = _make_frame(40)
    early = pd.Series(df["available_at"], index=df.index)
    early.iloc[10] = df.index[10] - pd.Timedelta(days=2)
    pf = sr.PriceFrame(frame=df.drop(columns=["available_at"]), available_at=early,
                       adjustment_basis=dict(ALL_BASIS), synthetic=True, ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, df.index[-1])
    assert "available_at_before_observation" in reasons


def test_available_at_must_be_declared_for_every_session():
    df = _make_frame(40)
    pf = sr.PriceFrame(frame=df.drop(columns=["available_at"]),
                       available_at=pd.Series([pd.NaT] * 40, index=df.index),
                       adjustment_basis=dict(ALL_BASIS), synthetic=True, ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, df.index[-1])
    assert "available_at_not_declared" in reasons


def test_adjustment_basis_must_be_declared_and_must_agree_across_ohlcv():
    df = _make_frame(40)
    base = df.drop(columns=["available_at"])
    avail = pd.Series(df["available_at"], index=df.index)

    _c, undeclared, _ = sr.validate_price_frame(
        sr.PriceFrame(base, avail, adjustment_basis="", ticker="AAA"), df.index[-1])
    assert "adjustment_basis_not_declared" in undeclared

    mixed = dict(ALL_BASIS)
    mixed["close"] = "raw"
    _c, mismatch, _ = sr.validate_price_frame(
        sr.PriceFrame(base, avail, adjustment_basis=mixed, ticker="AAA"), df.index[-1])
    assert any(r.startswith("mixed_adjustment_basis") for r in mismatch), \
        "an adjusted open against a raw close is a fabricated fill"

    _c, agreed, _ = sr.validate_price_frame(
        sr.PriceFrame(base, avail, adjustment_basis="split_adjusted", ticker="AAA"),
        df.index[-1])
    assert agreed == []


@pytest.mark.parametrize("bad", [
    {"close": np.zeros(6)},
    {"open": np.full(6, -5.0)},
    {"high": np.full(6, np.nan)},
    {"volume": np.full(6, np.nan)},
    {"volume": np.full(6, -1.0)},
])
def test_structurally_invalid_prices_block_the_instrument(bad):
    idx = _sessions(6)
    frame = pd.DataFrame({c: np.linspace(100.0, 110.0, 6)
                          for c in ("open", "high", "low", "close")}, index=idx)
    frame["volume"] = np.full(6, 1e6)
    for col, values in bad.items():
        frame[col] = values
    pf = sr.PriceFrame(frame=frame, available_at=pd.Series(idx, index=idx),
                       adjustment_basis=dict(ALL_BASIS), ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, idx[-1])
    assert reasons, "an invalid price column produced no blocking reason"


def test_duplicate_or_unsorted_sessions_block_the_instrument():
    idx = _sessions(6)
    frame = pd.DataFrame({c: np.linspace(100.0, 110.0, 6)
                          for c in ("open", "high", "low", "close", "volume")}, index=idx)
    dup = pd.concat([frame, frame.iloc[[2]]]).sort_index(ascending=False)
    pf = sr.PriceFrame(frame=dup, available_at=pd.Series(dup.index, index=dup.index),
                       adjustment_basis=dict(ALL_BASIS), ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, dup.index[-1])
    assert "session_index_not_chronological" in reasons
    assert "session_index_not_unique" in reasons


# --------------------------------------------------------------------------- #
# 6. determinism and strict finite JSON
# --------------------------------------------------------------------------- #
def test_identical_inputs_and_config_produce_byte_identical_json():
    first = sr.dumps(_report(_frames()))
    second = sr.dumps(_report(_frames()))
    assert first == second
    assert json.loads(first) == json.loads(second)


def test_no_nan_or_infinity_can_be_serialised():
    text = sr.dumps(_report())
    assert "NaN" not in text and "Infinity" not in text
    # json.loads with the permissive parser would happily accept them; the report
    # must parse under the strict one too.
    json.loads(text, parse_constant=lambda c: pytest.fail(f"non-finite token {c}"))
    with pytest.raises(ValueError):
        sr.dumps({"x": float("nan")})
    with pytest.raises(ValueError):
        sr.dumps({"x": float("inf")})
    with pytest.raises(ValueError):
        sr.dumps({"a": [{"b": -float("inf")}]})


def test_report_identity_order_is_stable_and_sorted():
    report = _report()
    assert [s["id"] for s in report["strategies"]] == sorted(sr.CANDIDATE_KEYS)
    assert list(report) == ["schema", "generated_at", "as_of", "mode",
                            "live_orders_enabled", "status", "source", "summary",
                            "strategies", "data_health", "limitations"]
    for row in report["strategies"]:
        assert row["instruments"] == sorted(row["instruments"])
        assert row["blockers"] == sorted(row["blockers"])
        assert len(set(row["invalidation"])) == len(row["invalidation"])
        assert row["historical"]["limitations"] == sorted(row["historical"]["limitations"])


# --------------------------------------------------------------------------- #
# 7. blocked inputs are stable, reasoned, and never invented as zeros
# --------------------------------------------------------------------------- #
def test_missing_inputs_produce_stable_blocked_reasons_with_null_metrics():
    report = _report({})
    assert report["status"] == "inputs_blocked"
    assert report["data_health"]["state"] == "blocked"
    assert "no_usable_instrument" in report["data_health"]["reasons"]
    assert report["data_health"]["last_session"] is None
    assert report["summary"] == {"candidate_count": 2, "evaluated_count": 0,
                                 "capital_eligible_count": 0}
    assert len(report["strategies"]) == 2, "both candidates must still be reported"
    for row in report["strategies"]:
        assert row["status"] == "blocked"
        hist = row["historical"]
        assert hist["state"] == "unavailable"
        for metric in ("net_sharpe", "net_cagr", "max_drawdown", "turnover",
                       "benchmark_sharpe", "sample_start", "sample_end"):
            assert hist[metric] is None, f"{metric} was invented as 0/None-free instead of null"
        assert row["capital_eligible"] is False
    # stable: the same empty input yields the identical reason set every time
    assert _report({})["data_health"]["reasons"] == report["data_health"]["reasons"]


def test_short_common_history_blocks_rather_than_reporting_a_tiny_number():
    report = _report(_frames(n=320, tickers=("AAA", "BBB")))
    short = _report(_frames(n=12, tickers=("AAA", "BBB")),
                    as_of="2023-01-20", expected_last_session="2023-01-20")
    assert short["status"] == "inputs_blocked" or all(
        s["historical"]["state"] == "unavailable" for s in short["strategies"])
    assert report["summary"]["candidate_count"] == 2


def test_undeclared_expected_last_session_cannot_certify_freshness():
    """The freshness contract is explicit. The engine never guesses that a gap is
    a weekend rather than a stale feed."""
    frames = _frames()
    last = _last_session(frames)
    declared = _report(frames, expected_last_session=last)
    undeclared = _report(frames, expected_last_session=None)
    assert declared["data_health"]["state"] == "ready"
    assert "expected_last_session_not_declared" in undeclared["data_health"]["reasons"]
    assert undeclared["status"] == "inputs_blocked"


def test_last_session_that_contradicts_the_expectation_blocks():
    report = _report(_frames(), expected_last_session="2099-01-01")
    assert report["data_health"]["state"] == "blocked"
    assert any("does_not_match_expected" in r for r in report["data_health"]["reasons"])


# --------------------------------------------------------------------------- #
# 8. research-only posture
# --------------------------------------------------------------------------- #
def test_report_never_claims_capital_prospective_or_paper_authority():
    report = _report()
    assert report["mode"] == "RESEARCH_ONLY"
    assert report["live_orders_enabled"] is False
    assert report["summary"]["capital_eligible_count"] == 0
    for row in report["strategies"]:
        assert row["capital_eligible"] is False
        assert row["stance"] == "Observe only"
        assert row["status"] in ("research_only", "blocked")
        assert row["prospective"] == {"state": "not_started", "registered": 0, "graded": 0}
        assert row["paper"] == {"state": "not_connected"}


def test_no_universal_sharpe_promotion_threshold_exists_in_the_engine():
    """Discriminates against a promotion gate sneaking in: the module must contain
    no Sharpe/CAGR threshold that could flip a candidate out of research-only."""
    source = (sr.__file__ and open(sr.__file__, encoding="utf-8").read())
    for banned in ("min_sharpe", "sharpe_threshold", "sharpe_gate", "promotion_threshold",
                   "min_cagr", "cagr_threshold", "PASS_SHARPE", "SHARPE_GATE",
                   "promote_if", "is_promotable"):
        assert banned not in source, f"{banned} is a universal promotion threshold"
    # ...and the descriptive limitation is actually emitted, not just declared.
    report = _report()
    assert any("DESCRIPTIVE" in lim for lim in report["limitations"])
    for row in report["strategies"]:
        assert any("DESCRIPTIVE" in lim for lim in row["historical"]["limitations"])


def test_historical_aggregate_never_pools_names_as_independent_samples():
    """Statistics come from ONE equal-weight portfolio series over a COMMON window,
    not from averaging per-name Sharpes."""
    report = _report(_frames(tickers=("AAA", "BBB")))
    for row in report["strategies"]:
        if row["historical"]["state"] != "available":
            continue
        assert any("EQUAL-WEIGHT" in lim for lim in row["historical"]["limitations"])
        assert any("not pooled as independent samples" in lim
                   for lim in row["historical"]["limitations"])


def test_synthetic_fixtures_are_labelled_as_synthetic():
    report = _report(_frames())
    assert any("SYNTHETIC FIXTURE INPUT" in lim for lim in report["limitations"])


def test_terminal_mark_convention_is_disclosed():
    report = _report()
    for row in report["strategies"]:
        if row["historical"]["state"] == "available":
            assert any("NOT liquidated" in lim for lim in row["historical"]["limitations"])


def test_projections_are_not_emitted():
    report = _report()
    blob = json.dumps(report)
    for banned in ("projected_cagr", "expected_return", "win_probability",
                   "probability_of_profit", "forecast_cagr", "equity_curve"):
        assert banned not in blob, f"{banned} is a projection this engine must not emit"


# --------------------------------------------------------------------------- #
# 9. no account / QLedger / network / production side effects
# --------------------------------------------------------------------------- #
def test_import_and_evaluation_touch_no_account_ledger_or_network(tmp_path, monkeypatch):
    """Guards the real discipline: importing and evaluating must not open a
    socket, and must not write anywhere outside an explicit caller-supplied path."""
    import socket

    def _forbidden(*a, **k):
        raise AssertionError("the research engine opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)

    import importlib.util
    from pathlib import Path as _P

    root = _P(__file__).resolve().parents[1]

    def _fresh(relpath: str, alias: str):
        spec = importlib.util.spec_from_file_location(alias, root / relpath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        spec.loader.exec_module(module)          # a genuine cold import
        return module

    sr_mod = _fresh("engine/systematic_research.py", "_probe_engine")
    cli_mod = _fresh("scripts/build_systematic_research.py", "_probe_cli")
    assert sr_mod.SCHEMA == "systematic_research.v1"
    assert cli_mod.SCHEMA == "systematic_research.v1"

    before = sorted(p.name for p in tmp_path.iterdir())
    live = _frames()
    report = sr_mod.build_report(
        {t: sr_mod.PriceFrame(frame=pf.frame, available_at=pf.available_at,
                              adjustment_basis=pf.adjustment_basis,
                              synthetic=pf.synthetic, ticker=t)
         for t, pf in live.items()},
        as_of=_last_session(live), generated_at=GENERATED_AT, code_revision=CODE_REV,
        data_revision=DATA_REV, cost_bps=COST_BPS,
        expected_last_session=_last_session(live))
    sr_mod.dumps(report)
    after = sorted(p.name for p in tmp_path.iterdir())
    assert before == after, "import/evaluation wrote a file it was not given a path for"

    repo_root = __import__("pathlib").Path(__file__).resolve().parents[1]
    for guarded in ("data/qledger", "data/allocation", "data/accounts"):
        assert not (repo_root / guarded / "systematic_research.json").exists()


def test_cli_writes_only_the_explicitly_supplied_output_path(tmp_path):
    in_dir = tmp_path / "prices"
    in_dir.mkdir()
    df = _make_frame(300)
    df.drop(columns=["available_at"]).to_csv(in_dir / "AAA.csv", index_label="date")
    (in_dir / METADATA_FILENAME).write_text(json.dumps({
        "as_of": AS_OF,
        "expected_last_session": "2024-03-11",
        "data_revision": DATA_REV,
        "synthetic": True,
        "instruments": {"AAA": {
            "available_at": [t.isoformat() for t in df["available_at"]],
            "adjustment_basis": dict(ALL_BASIS),
        }},
    }))
    out = tmp_path / "nested" / "report.json"

    rc = cli_main(["--input-dir", str(in_dir), "--output", str(out),
                   "--generated-at", GENERATED_AT, "--code-revision", CODE_REV,
                   "--expected-last-session", "2024-03-11", "--cost-bps", "10"])
    assert rc == 0
    assert out.is_file()
    payload = json.loads(out.read_text())
    assert payload["schema"] == "systematic_research.v1"
    assert payload["mode"] == "RESEARCH_ONLY"
    assert sorted(p.name for p in (tmp_path / "nested").iterdir()) == ["report.json"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["nested", "prices"]


def test_cli_refuses_a_price_store_without_an_open_column(tmp_path):
    """The repository's own data/stocks store carries close/high/low/volume and no
    open. Substituting the close would fabricate a fill price."""
    in_dir = tmp_path / "prices"
    in_dir.mkdir()
    df = _make_frame(60)
    df.drop(columns=["available_at", "open"]).rename(
        columns={"close": "close", "high": "high", "low": "low", "volume": "volume"}
    ).to_csv(in_dir / "AAA.csv", index_label="date")
    (in_dir / METADATA_FILENAME).write_text(json.dumps({
        "as_of": AS_OF, "data_revision": DATA_REV,
        "instruments": {"AAA": {"available_at": [t.isoformat() for t in df["available_at"]],
                                "adjustment_basis": dict(ALL_BASIS)}},
    }))
    with pytest.raises(InputRefused, match="input_requires_open_column"):
        load_inputs(in_dir)


def test_cli_requires_declared_point_in_time_metadata(tmp_path):
    in_dir = tmp_path / "prices"
    in_dir.mkdir()
    df = _make_frame(60)
    df.drop(columns=["available_at"]).to_csv(in_dir / "AAA.csv", index_label="date")
    (in_dir / METADATA_FILENAME).write_text(json.dumps({
        "as_of": AS_OF, "data_revision": DATA_REV, "instruments": {"AAA": {}}}))
    with pytest.raises(InputRefused, match="available_at"):
        load_inputs(in_dir)


def test_cli_requires_an_explicit_output_path():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--input-dir", ".", "--generated-at", GENERATED_AT,
                           "--code-revision", CODE_REV, "--cost-bps", "10"])
    assert "--output" in (parser.format_help())


def test_cli_exposes_no_network_or_purchase_surface():
    parser = build_parser()
    options = {a.dest for a in parser._actions}
    for banned in ("url", "endpoint", "api_key", "token", "buy", "purchase", "schedule"):
        assert banned not in options


# --------------------------------------------------------------------------- #
# 10. legacy compatibility
# --------------------------------------------------------------------------- #
def test_legacy_backtest_core_callers_are_unchanged():
    """The next-open helper is additive; the close-to-close engine keeps its bytes."""
    idx = _sessions(60, start="2024-01-01")
    close = pd.Series(100.0 * np.exp(np.cumsum(np.linspace(0.001, 0.002, 60))), index=idx)
    alloc = pd.Series([0.0, 1.0] * 30, index=idx)
    bt = backtest_core(close, alloc, cost_bps=5.0)
    assert bt["pos"].iloc[0] == 0.0 and bt["pos"].iloc[1] == 0.0
    assert bt["pos"].iloc[2] == 1.0, "legacy fills the next bar, unchanged"
    assert float(bt["net"].iloc[2]) == pytest.approx(
        float(bt["gross"].iloc[2]) - 0.0005, rel=1e-9)
    assert "terminal_mark_unliquidated" not in bt   # legacy semantics untouched


def test_legacy_default_cost_is_still_costless():
    idx = _sessions(40, start="2024-01-01")
    close = pd.Series(np.linspace(100.0, 140.0, 40), index=idx)
    alloc = pd.Series([0.0, 1.0] * 20, index=idx)
    free = backtest_core(close, alloc, 0.0)
    assert free["net"].equals(free["gross"])


# --------------------------------------------------------------------------- #
# 11. statistics helpers refuse rather than invent
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("returns,fn", [
    (pd.Series([0.0, 0.0, 0.0]), sr._sharpe),
    (pd.Series([0.001, -0.001]), sr._sharpe),
    (pd.Series([0.001]), sr._cagr),
    (pd.Series([0.001]), sr._max_drawdown),
])
def test_uncomputable_statistics_return_none_not_zero(returns, fn):
    value = fn(returns, 252) if fn is not sr._max_drawdown else fn(returns)
    assert value is None, "an uncomputable statistic was invented as 0.0"


def test_a_genuinely_flat_path_reports_zero_cagr_not_null():
    """Discriminates the fix: 0.0 here is the ANSWER, not an invented zero."""
    assert sr._cagr(pd.Series([0.0, 0.0, 0.0, 0.0]), 252) == pytest.approx(0.0)


def test_constant_return_series_has_no_sharpe_rather_than_infinite():
    assert sr._sharpe(pd.Series([0.001] * 50), 252) is None


def test_extreme_growth_does_not_serialise_as_infinity():
    returns = pd.Series([0.9, -0.95, 5.0])
    assert sr._finite(sr._cagr(returns, 252)) is None or math.isfinite(sr._cagr(returns, 252))
    text = sr.dumps({"x": sr._cagr(returns, 252)})
    assert "Infinity" not in text


# --------------------------------------------------------------------------- #
# 12. candidates are exactly the two frozen registry entries
# --------------------------------------------------------------------------- #
def test_engine_uses_exactly_the_two_frozen_candidates_and_reuses_the_registry():
    from engine import strategy_signals as signals

    assert sr.CANDIDATE_KEYS == ("rsi2_oversold", "tsmom_200")
    registry = signals.by_key()
    for key in sr.CANDIDATE_KEYS:
        assert key in registry
        report = _report()
        row = _by_id(report, key)
        assert row["name"] == registry[key].name
        assert row["family"] == registry[key].family
        assert row["horizon_sessions"] == registry[key].horizon


def test_candidate_position_comes_from_the_installed_signal_callable():
    df = _make_frame(300).drop(columns=["available_at"])
    for key in sr.CANDIDATE_KEYS:
        pos, warmup = sr.candidate_raw_position(df, key)
        assert pos is not None, f"{key} produced no tradable position"
        assert len(pos) == len(df)
        assert warmup >= 0
        assert float(pos.min()) >= 0.0 and float(pos.max()) <= 1.0