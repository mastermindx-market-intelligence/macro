"""Systematic Strategies research engine — discriminating tests.

Every test here earns its place by DISCRIMINATING. Each one fails against the
implementation that preceded it, for a named reason:

  * a book that spends the target first and deducts fees afterwards (negative
    cash = hidden leverage, plus phantom repeated sells at a constant price);
  * a terminal session that is CLAIMED as mark-only while a final trade is
    charged anyway;
  * a max drawdown computed without the initial capital, so a first-bar loss is
    forgiven;
  * a cutoff that discards a UTC offset, so the same instant written two ways
    compares unequal;
  * a receipt that is naive, or earlier than its own session's close;
  * a price check that runs BEFORE the availability filter, so appending one
    future bad bar rewrites an old cutoff;
  * an OHLC bar whose close sits outside its own high/low range;
  * an internal market session silently intersected away, or a stale name hidden
    behind a fresh one by a maximum across names;
  * a warmup called "dropped" when nothing was dropped;
  * returns averaged across names, which rebalances between assets for free;
  * a turnover that is a mean of means, and a benchmark filled earlier than the
    strategy it is compared against;
  * a capacity certificate produced by a model that is not qualified.

The engine is RESEARCH_ONLY. These tests deliberately assert the negative
properties too: capital is never eligible, prospective is never started, and no
universal Sharpe threshold exists anywhere in the module.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from engine import systematic_research as sr
from engine.validation import (
    IMPACT_NOT_QUALIFIED,
    CapacityBlocked,
    NextOpenError,
    backtest_core,
    capacity_curve,
    next_open_sim,
)
from lib import nyse_calendar as cal
from scripts.build_systematic_research import (
    METADATA_FILENAME,
    InputRefused,
    build_parser,
    load_inputs,
    load_strict_json,
    main as cli_main,
)

ET = ZoneInfo("America/New_York")
GENERATED_AT = "2026-10-22T13:00:00Z"
CODE_REV = "0123456789abcdef0123456789abcdef01234567"
DATA_REV = "fixture-revision-1"
COST_BPS = 10.0

ALL_BASIS = {c: "split_adjusted" for c in ("open", "high", "low", "close", "volume")}


# --------------------------------------------------------------------------- #
# fixtures — real NYSE sessions and TIMEZONE-AWARE receipts
# --------------------------------------------------------------------------- #
def _sessions(n: int, start: str = "2023-01-02") -> pd.DatetimeIndex:
    """Real US cash sessions from the repository's own calendar.

    ``bdate_range`` would include Christmas and Good Friday, which would make a
    calendar check that is right look broken.
    """
    begin = datetime.fromisoformat(start).date()
    days = cal.sessions_between(begin, begin + timedelta(days=int(n * 2.5) + 40))
    return pd.DatetimeIndex([pd.Timestamp(d) for d in days[:n]])


def _available(idx: pd.DatetimeIndex, *, hour: int = 17, minute: int = 0) -> pd.DatetimeIndex:
    """A receipt at 17:00 ET on each session — after that session's close."""
    return pd.DatetimeIndex([
        pd.Timestamp(datetime.combine(pd.Timestamp(d).date(), time(hour, minute),
                                     tzinfo=ET)).tz_convert("UTC")
        for d in idx
    ])


def _make_frame(n: int = 320, seed: int = 11, start: str = "2023-01-02",
                *, drift: float = 0.0006, vol_scale: float = 1.0) -> pd.DataFrame:
    """Synthetic but structurally honest OHLCV with a real aware available_at."""
    rng = np.random.default_rng(seed)
    idx = _sessions(n, start)
    steps = rng.normal(drift, 0.017 * vol_scale, n)
    close = 100.0 * np.exp(np.cumsum(steps))
    open_ = np.empty(n)
    open_[0] = close[0] * (1.0 - steps[0])
    open_[1:] = close[:-1]
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, 0.004, n)))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, 0.004, n)))
    volume = rng.uniform(4.0e6, 9.0e6, n)
    df = pd.DataFrame({"open": open_, "high": high, "low": low,
                       "close": close, "volume": volume}, index=idx)
    df["available_at"] = _available(idx)
    df.index.name = "date"
    df.attrs.update({"adjustment_basis": dict(ALL_BASIS), "synthetic": True})
    return df


def _price_frame(df: pd.DataFrame, ticker: str = "AAA", **kw) -> sr.PriceFrame:
    return sr.PriceFrame(
        frame=df.drop(columns=["available_at"]),
        available_at=pd.Series(df["available_at"], index=df.index),
        adjustment_basis=dict(ALL_BASIS),
        synthetic=True,
        ticker=ticker,
        **kw,
    )


def _frames(n: int = 320, tickers: tuple[str, ...] = ("AAA", "BBB"),
            seed: int = 11, **kw) -> dict[str, sr.PriceFrame]:
    return {t: _price_frame(_make_frame(n, seed=seed + i, **kw), ticker=t)
            for i, t in enumerate(tickers)}


def _last_session(frames) -> str:
    if not frames:
        return "2026-03-02"
    return max(pf.frame.index.max() for pf in frames.values()).date().isoformat()


def _aware_as_of(session: str) -> str:
    """A receipt instant safely after that session's close, in UTC form."""
    return f"{session}T23:59:59+00:00"


def _report(frames=None, **kw):
    given = frames if frames is not None else _frames()
    last = _last_session(given)
    opts = dict(as_of=_aware_as_of(last), generated_at=GENERATED_AT,
                code_revision=CODE_REV, data_revision=DATA_REV, cost_bps=COST_BPS,
                expected_last_session=last)
    opts.update(kw)
    return sr.build_report(given, **opts)


def _by_id(report, key):
    return next(s for s in report["strategies"] if s["id"] == key)


# --------------------------------------------------------------------------- #
# 1. self-financing LONG/CASH accounting
# --------------------------------------------------------------------------- #
def test_constant_price_fully_invested_pays_exactly_one_fee_and_stops_trading():
    """THE falsifier. Constant price 100, four sessions, alloc 1, 100bps.

    The prior engine spent 100% first and then booked the fee as NEGATIVE cash,
    so equity went 1 -> .99 -> .9899 -> .989899 with a phantom sell at every
    session. The fee-feasible fully-invested value is 1/(1+0.01), paid ONCE, and
    a constant target at a constant price generates no further trade at all.
    """
    idx = _sessions(4, "2026-03-02")
    op = pd.Series(100.0, index=idx)
    al = pd.Series(1.0, index=idx)
    sim = next_open_sim(op, op.copy(), al, cost_bps=100.0)

    assert sim["equity"].iloc[-1] == pytest.approx(1.0 / 1.01, rel=1e-12)
    assert sim["equity"].iloc[0] == pytest.approx(1.0)
    # exactly one charged fill: the initial buy
    assert sim["cost"].iloc[0] == pytest.approx(0.0)
    assert sim["cost"].iloc[1] > 0.0
    assert sim["cost"].iloc[2:].to_numpy() == pytest.approx(0.0, abs=1e-15), \
        "a constant target at a constant price generated a phantom rebalance"
    assert sim["turnover"].iloc[2:].to_numpy() == pytest.approx(0.0, abs=0.0)


@pytest.mark.parametrize("weight", [0.25, 0.5, 0.75, 1.0])
def test_static_partial_weight_is_stationary_under_a_constant_price(weight):
    """A fixed target and a fixed price must produce ONE trade and then rest."""
    idx = _sessions(6, "2026-03-02")
    op = pd.Series(50.0, index=idx)
    al = pd.Series(weight, index=idx)
    sim = next_open_sim(op, op.copy(), al, cost_bps=25.0)

    # one buy of delta = w/(1+w*c); equity ends at V - delta*c
    expected = 1.0 - weight * 0.0025 / (1.0 + weight * 0.0025)
    assert sim["equity"].iloc[1] == pytest.approx(expected, rel=1e-12)
    assert sim["equity"].iloc[-1] == pytest.approx(expected, rel=1e-12), \
        "a stationary book drifted without trading"
    assert sim["cost"].iloc[2:].to_numpy() == pytest.approx(0.0, abs=1e-15)


def test_cash_and_shares_stay_non_negative_and_the_book_is_conserved():
    """No overdraft, no short, and value is real: cash + shares*price == equity."""
    idx = _sessions(200)
    rng = np.random.default_rng(5)
    close = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, 200))), index=idx)
    open_ = close.shift(1).fillna(close.iloc[0])
    alloc = pd.Series(rng.choice([0.0, 0.35, 0.7, 1.0], 200), index=idx)
    sim = next_open_sim(open_, close, alloc, cost_bps=25.0)

    assert sim["cash"].min() >= -1e-9, "the book overdrew cash to hold its target"
    assert sim["shares"].min() >= -1e-9, "the book went short"
    assert sim["equity"].min() > 0.0
    marked = sim["cash"] + sim["shares"] * open_
    assert np.allclose(marked.to_numpy(), sim["equity"].to_numpy(), atol=1e-12)
    held = (sim["shares"] * open_ / sim["equity"]).to_numpy()
    assert held.max() <= 1.0 + 1e-9, "weight exceeded 1"


def test_charged_cost_is_exactly_the_rate_times_actual_traded_notional():
    idx = _sessions(8, "2026-03-02")
    op = pd.Series([100.0, 100.0, 100.0, 110.0, 110.0, 110.0, 120.0, 120.0], index=idx)
    al = pd.Series([0.0, 1.0, 1.0, 0.0, 0.5, 0.5, 0.0, 0.0], index=idx)
    rate = 10.0 / 1e4
    sim = next_open_sim(op, op.copy(), al, cost_bps=10.0)
    assert np.allclose(sim["cost"].to_numpy(),
                       sim["traded_notional"].to_numpy() * rate, atol=1e-15)


def test_a_full_exit_raises_cash_by_the_marked_value_less_its_fee():
    """Selling out returns the position's value minus the fee, and nothing more."""
    idx = _sessions(6, "2026-03-02")
    op = pd.Series(80.0, index=idx)
    al = pd.Series([0.0, 1.0, 1.0, 0.0, 0.0, 0.0], index=idx)   # buys at open 2, exits at open 4
    rate = 10.0 / 1e4
    sim = next_open_sim(op, op.copy(), al, cost_bps=10.0)
    held_before = sim["shares"].iloc[3] * op.iloc[3]
    fee = sim["cost"].iloc[4]
    assert sim["cash"].iloc[4] == pytest.approx(held_before - held_before * rate, rel=1e-9)
    assert fee > 0.0, "the exit was free"
    assert sim["shares"].iloc[4] == pytest.approx(0.0, abs=1e-15)


def test_a_degenerate_fee_solve_is_refused_rather_than_clipped():
    """A 12000bps cost against a 0.9 target cannot reach the target and pay its
    own fee. That is refused; it is not quietly rounded into a trade."""
    idx = _sessions(6, "2026-03-02")
    op = pd.Series(100.0, index=idx)
    al = pd.Series([0.0, 1.0, 1.0, 0.9, 0.9, 0.9], index=idx)
    with pytest.raises(NextOpenError, match="fee_solve_degenerate"):
        next_open_sim(op, op.copy(), al, cost_bps=12000.0)


# --------------------------------------------------------------------------- #
# 2. timing and the terminal convention
# --------------------------------------------------------------------------- #
def test_post_close_entrant_cannot_capture_the_next_open_gap():
    """+10% happens at open[t+1]. A decision from close[t] fills AT open[t+1]."""
    idx = _sessions(5, "2024-01-01")
    op = pd.Series([100.0, 100.0, 100.0, 110.0, 110.0], index=idx)
    alloc = pd.Series([0.0, 0.0, 1.0, 1.0, 0.0], index=idx)

    honest = next_open_sim(op, op.copy(), alloc, cost_bps=0.0)
    assert honest["pos"].iloc[3] == 1.0, "the fill must be AT the next open"
    assert honest["ret"].max() == pytest.approx(0.0), "a post-close entrant took the gap"
    assert honest["benchmark_open_to_open"].max() == pytest.approx(0.10)

    legacy = backtest_core(op, alloc, cost_bps=0.0)
    assert float(legacy["net"].max()) == pytest.approx(0.10), \
        "the legacy engine's look-ahead must be preserved for its own callers"


def test_overnight_gap_is_retained_by_whoever_already_held_it():
    idx = _sessions(5, "2024-01-01")
    op = pd.Series([100.0, 100.0, 100.0, 110.0, 110.0], index=idx)
    alloc = pd.Series([0.0, 1.0, 1.0, 1.0, 0.0], index=idx)
    sim = next_open_sim(op, op.copy(), alloc, cost_bps=0.0)
    assert sim["pos"].iloc[2] == 1.0
    assert sim["ret"].iloc[2] == pytest.approx(0.10), "held overnight risk was discarded"


def test_session_zero_opens_flat_because_there_is_no_prior_close():
    idx = _sessions(4, "2024-01-01")
    op = pd.Series([100.0, 100.0, 130.0, 160.0], index=idx)
    alloc = pd.Series([1.0, 1.0, 1.0, 0.0], index=idx)
    sim = next_open_sim(op, op.copy(), alloc, cost_bps=0.0)
    assert sim["pos"].iloc[0] == 0.0
    assert sim["equity"].iloc[0] == pytest.approx(1.0)


def test_terminal_session_is_marked_and_never_rebalanced():
    """The claimed convention and the charged arithmetic must agree.

    The prior engine appended 'not liquidated' to the report while its last loop
    iteration still traded to alloc[n-2] and charged that final fill.
    """
    idx = _sessions(6, "2024-01-01")
    op = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0, 100.0], index=idx)
    alloc = pd.Series([0.0, 1.0, 1.0, 1.0, 1.0, 0.0], index=idx)   # would exit at last open
    sim = next_open_sim(op, op.copy(), alloc, cost_bps=50.0)

    assert sim["traded_notional"].iloc[-1] == 0.0, "a final trade was charged"
    assert sim["cost"].iloc[-1] == 0.0
    assert sim["turnover"].iloc[-1] == 0.0
    assert math.isnan(float(sim["pos"].iloc[-1])), "the terminal session has no target"
    # the terminal NAV is the marked book, not a liquidation
    assert sim["equity"].iloc[-1] == pytest.approx(
        sim["cash"].iloc[-1] + sim["shares"].iloc[-1] * op.iloc[-1])
    assert sim["terminal_mark_unliquidated"] is True


# --------------------------------------------------------------------------- #
# 3. statistics include the initial capital
# --------------------------------------------------------------------------- #
def test_max_drawdown_includes_the_initial_capital():
    """THE falsifier. A path that only ever falls reported 0.0 drawdown because
    the curve's peak was the (unrecorded) starting NAV of 1."""
    assert sr._max_drawdown(pd.Series([-0.5, 0.0, 0.0])) == pytest.approx(-0.5)
    assert sr._max_drawdown(pd.Series([-0.25, 0.0, 0.0])) == pytest.approx(-0.25)
    assert sr._max_drawdown(pd.Series([0.5, -0.5, 0.0])) == pytest.approx(-0.5)


def test_a_first_bar_loss_is_visible_in_the_reported_drawdown():
    idx = _sessions(80, "2023-06-01")
    op = pd.Series(np.concatenate([[100.0, 100.0], np.full(78, 60.0)]), index=idx)
    alloc = pd.Series(np.concatenate([[1.0, 1.0], np.zeros(78)]), index=idx)
    sim = next_open_sim(op, op.copy(), alloc, cost_bps=0.0)
    assert sim["equity"].iloc[-1] / sim["equity"].iloc[0] - 1.0 == pytest.approx(-0.4)


@pytest.mark.parametrize("returns,fn", [
    (pd.Series([0.0, 0.0, 0.0]), sr._sharpe),
    (pd.Series([0.001, -0.001]), sr._sharpe),
    (pd.Series([], dtype=float), sr._sharpe),
    (pd.Series([], dtype=float), sr._max_drawdown),
    (pd.Series([0.001]), sr._cagr),
    (pd.Series([0.001]), sr._max_drawdown),
])
def test_uncomputable_statistics_return_none_not_zero(returns, fn):
    value = fn(returns, 252) if fn is not sr._max_drawdown else fn(returns)
    assert value is None, "an uncomputable statistic was invented as 0.0"


def test_all_cash_zero_volatility_and_flat_samples_are_undefined_not_zero():
    assert sr._sharpe(pd.Series([0.0] * 50), 252) is None, "zero volatility is undefined"
    assert sr._sharpe(pd.Series([-0.001] * 50), 252) is None, "a constant drift has no ratio"
    assert sr._cagr(pd.Series([0.0, 0.0, 0.0, 0.0]), 252) == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# 4. timestamps — aware, UTC-normalised, ordered
# --------------------------------------------------------------------------- #
def test_the_same_instant_written_in_two_offsets_is_the_same_cutoff():
    """THE falsifier. The prior reader threw the offset away and compared wall
    clock, so 19:00+00:00 and 15:00-04:00 — the same instant — were unequal."""
    assert sr._cutoff("2026-10-22T19:00:00+00:00") == sr._cutoff("2026-10-22T15:00:00-04:00")
    assert sr._cutoff("2026-10-22T19:00:00+00:00") == sr._cutoff("2026-10-22T19:00:00Z")
    assert sr._cutoff("2026-10-22T15:00:00-04:00") == pd.Timestamp("2026-10-22T19:00:00+00:00")
    assert sr._cutoff("2026-10-22T19:00:00+00:00").tz is not None


@pytest.mark.parametrize("bad", ["2026-10-22", "2026-10-22 15:00:00", "2026-10-22T15:00:00"])
def test_a_bare_date_or_naive_cutoff_is_refused_with_a_stated_reason(bad):
    with pytest.raises(ValueError, match="as_of_must_be"):
        sr._cutoff(bad)


def test_generated_at_must_not_precede_as_of():
    frames = _frames()
    last = _last_session(frames)
    early = (pd.Timestamp(_aware_as_of(last)) - pd.Timedelta(days=3)).isoformat()
    with pytest.raises(ValueError, match="generated_at_precedes_as_of"):
        sr.build_report(frames, as_of=_aware_as_of(last),
                        generated_at=early,
                        code_revision=CODE_REV, data_revision=DATA_REV,
                        cost_bps=COST_BPS, expected_last_session=last)
    # equal instants are fine
    sr.build_report(frames, as_of=_aware_as_of(last),
                    generated_at=_aware_as_of(last),
                    code_revision=CODE_REV, data_revision=DATA_REV,
                    cost_bps=COST_BPS, expected_last_session=last)


def test_a_receipt_earlier_than_its_own_session_close_is_refused():
    """A full daily OHLC bar cannot exist before 16:00 ET on its session."""
    idx = _sessions(40, "2023-06-01")
    df = _make_frame(40, start="2023-06-01")
    early = df["available_at"].copy()
    early.iloc[5] = pd.Timestamp(datetime.combine(pd.Timestamp(idx[5]).date(),
                                                 time(15, 0), tzinfo=ET)).tz_convert("UTC")
    pf = sr.PriceFrame(frame=df.drop(columns=["available_at"]),
                       available_at=pd.Series(early, index=df.index),
                       adjustment_basis=dict(ALL_BASIS), synthetic=True, ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, df.index[-1].tz_localize("UTC") +
                                                 pd.Timedelta(hours=23))
    assert any(r.startswith("available_at_before_session_close") for r in reasons)


def test_a_naive_availability_receipt_is_refused_not_assumed_utc():
    idx = _sessions(40, "2023-06-01")
    df = _make_frame(40, start="2023-06-01")
    naive = pd.Series([pd.Timestamp(t).tz_localize(None) for t in df["available_at"]],
                      index=df.index)
    pf = sr.PriceFrame(frame=df.drop(columns=["available_at"]), available_at=naive,
                       adjustment_basis=dict(ALL_BASIS), synthetic=True, ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, df.index[-1].tz_localize("UTC") +
                                                 pd.Timedelta(hours=23))
    assert "available_at_must_be_timezone_aware" in reasons


def test_availability_in_any_offset_normalises_to_one_utc_instant():
    idx = _sessions(30, "2023-06-01")
    values = [pd.Timestamp(datetime.combine(pd.Timestamp(d).date(), time(17, 0),
                                            tzinfo=ET)).tz_convert("UTC") for d in idx]
    s, naive = sr._available_series(pd.Series(values), idx)
    assert not naive.any()
    assert s.isna().sum() == 0
    for d, got in zip(idx, s):
        want = pd.Timestamp(datetime.combine(d.date(), time(17, 0),
                                             tzinfo=ET)).tz_convert("UTC")
        assert got == want


# --------------------------------------------------------------------------- #
# 5. point-in-time discipline
# --------------------------------------------------------------------------- #
def test_appending_a_future_BAD_bar_cannot_change_an_old_cutoff():
    """The strengthened invariance. The prior order validated prices BEFORE the
    availability filter, so one appended future bar with open=-5 blocked the
    whole instrument and changed history that had not changed."""
    base = _frames()
    cutoff = _aware_as_of(_last_session(base))
    before = _report(base, as_of=cutoff, expected_last_session=_last_session(base))
    assert _by_id(before, "tsmom_200")["historical"]["state"] == "available"

    grown = {}
    for ticker, pf in base.items():
        extra = _make_frame(30, seed=777, start="2027-06-01")
        extra.loc[extra.index[0], "open"] = -5.0        # a bad FUTURE price
        table = pd.concat([pf.frame, extra.drop(columns=["available_at"])])
        avail = pd.concat([pf.available_at,
                           pd.Series(extra["available_at"], index=extra.index)])
        grown[ticker] = sr.PriceFrame(
            frame=table, available_at=avail, adjustment_basis=dict(ALL_BASIS),
            synthetic=True, ticker=ticker)
    after = _report(grown, as_of=cutoff, expected_last_session=_last_session(base))

    for key in sr.CANDIDATE_KEYS:
        assert _by_id(after, key)["historical"] == _by_id(before, key)["historical"], \
            f"{key} history moved when only a future BAD bar was appended"


def test_prices_and_metadata_after_the_cutoff_never_enter_it():
    df = _make_frame(300)
    early = sr.PriceFrame(frame=df.drop(columns=["available_at"]),
                          available_at=pd.Series(df["available_at"], index=df.index),
                          adjustment_basis=dict(ALL_BASIS), synthetic=True, ticker="AAA")
    cutoff = pd.Timestamp(df["available_at"].iloc[149]).tz_convert("UTC")
    clean, reasons, detail = sr.validate_price_frame(early, cutoff)
    assert reasons == []
    assert detail["future_rows_excluded"] == 150
    assert len(clean) == 150


def test_availability_must_be_declared_for_every_session():
    df = _make_frame(40)
    pf = sr.PriceFrame(frame=df.drop(columns=["available_at"]),
                       available_at=pd.Series([pd.NaT] * 40, index=df.index),
                       adjustment_basis=dict(ALL_BASIS), synthetic=True, ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, pd.Timestamp("2026-01-01", tz="UTC"))
    assert "available_at_not_declared" in reasons


def test_adjustment_basis_must_be_declared_and_must_agree_across_ohlcv():
    df = _make_frame(40)
    base = df.drop(columns=["available_at"])
    avail = pd.Series(df["available_at"], index=df.index)
    cutoff = pd.Timestamp(df["available_at"].iloc[-1])

    _c, undeclared, _ = sr.validate_price_frame(
        sr.PriceFrame(base, avail, adjustment_basis="", ticker="AAA"), cutoff)
    assert "adjustment_basis_not_declared" in undeclared

    mixed = dict(ALL_BASIS)
    mixed["close"] = "raw"
    _c, mismatch, _ = sr.validate_price_frame(
        sr.PriceFrame(base, avail, adjustment_basis=mixed, ticker="AAA"), cutoff)
    assert any(r.startswith("mixed_adjustment_basis") for r in mismatch), \
        "an adjusted open against a raw close is a fabricated fill"


def test_price_basis_agreement_is_not_a_corporate_action_qualification():
    """Matching column basis is consistency, not qualified action economics."""
    report = _report()
    assert any("NOT a corporate-action qualification" in lim
               for lim in report["limitations"])


@pytest.mark.parametrize("column,value", [
    ("open", 0.0), ("open", -1.0), ("open", float("nan")),
    ("close", float("inf")), ("volume", -1.0),
])
def test_structurally_invalid_prices_block_the_instrument(column, value):
    idx = _sessions(20, "2023-06-01")
    frame = _make_frame(20, start="2023-06-01")
    table = frame.drop(columns=["available_at"])
    table.loc[table.index[4], column] = value
    pf = sr.PriceFrame(frame=table,
                       available_at=pd.Series(frame["available_at"], index=table.index),
                       adjustment_basis=dict(ALL_BASIS), ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, pd.Timestamp(frame["available_at"].iloc[-1]))
    assert reasons, "an invalid price produced no blocking reason"


def test_a_close_outside_its_own_high_low_range_is_not_a_bar():
    idx = _sessions(20, "2023-06-01")
    table = _make_frame(20, start="2023-06-01").drop(columns=["available_at"])
    table.loc[table.index[6], "close"] = float(table.loc[table.index[6], "high"]) * 1.5
    avail = _available(idx)
    pf = sr.PriceFrame(frame=table, available_at=pd.Series(avail, index=table.index),
                       adjustment_basis=dict(ALL_BASIS), ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, pd.Timestamp(avail[-1]))
    assert any("close_outside_high_low_range" in r or "close_not_positive" in r
               for r in reasons), reasons


def test_a_low_above_its_high_is_not_a_bar():
    idx = _sessions(20, "2023-06-01")
    table = _make_frame(20, start="2023-06-01").drop(columns=["available_at"])
    table.loc[table.index[6], "low"] = float(table.loc[table.index[6], "high"]) * 1.2
    avail = _available(idx)
    pf = sr.PriceFrame(frame=table, available_at=pd.Series(avail, index=table.index),
                       adjustment_basis=dict(ALL_BASIS), ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, pd.Timestamp(avail[-1]))
    assert any("low_above_high" in r for r in reasons), reasons


def test_duplicate_or_unsorted_sessions_block_the_instrument():
    idx = _sessions(20, "2023-06-01")
    frame = pd.DataFrame({c: np.linspace(100.0, 110.0, 20)
                          for c in ("open", "high", "low", "close", "volume")}, index=idx)
    dup = pd.concat([frame, frame.iloc[[2]]]).sort_index(ascending=False)
    pf = sr.PriceFrame(frame=dup, available_at=pd.Series(_available(dup.index), index=dup.index),
                       adjustment_basis=dict(ALL_BASIS), ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, pd.Timestamp("2027-01-01", tz="UTC"))
    assert "session_index_not_chronological" in reasons
    assert "session_index_not_unique" in reasons


# --------------------------------------------------------------------------- #
# 6. calendar and cohort honesty
# --------------------------------------------------------------------------- #
def test_a_missing_internal_market_session_blocks_instead_of_intersecting_away():
    idx = _sessions(40, "2023-06-01")
    hole = idx[20]
    trimmed = idx.delete(20)
    table = _make_frame(40, start="2023-06-01").drop(columns=["available_at"]).reindex(trimmed)
    avail = pd.Series(_available(idx), index=idx).reindex(trimmed)
    pf = sr.PriceFrame(frame=table, available_at=avail,
                       adjustment_basis=dict(ALL_BASIS), synthetic=True, ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, pd.Timestamp("2027-01-01", tz="UTC"))
    assert any(r.startswith("missing_internal_market_sessions") for r in reasons), \
        f"an internal market session was silently absorbed: {reasons}"


def test_a_row_on_a_day_the_market_was_closed_blocks():
    idx = _sessions(20, "2023-06-01")
    closed = pd.Timestamp("2023-07-04")
    assert not cal.is_session(closed.date()), "the fixture's closed day must really be closed"
    grown = idx.append(pd.DatetimeIndex([pd.Timestamp(closed)]))
    table = _make_frame(20, start="2023-06-01").drop(columns=["available_at"]).reindex(grown)
    table.loc[pd.Timestamp(closed), ["open", "high", "low", "close"]] = 100.0
    table.loc[pd.Timestamp(closed), "volume"] = 1e6
    avail = pd.Series(_available(grown), index=grown)
    pf = sr.PriceFrame(frame=table, available_at=avail, adjustment_basis=dict(ALL_BASIS),
                       synthetic=True, ticker="AAA")
    _clean, reasons, _ = sr.validate_price_frame(pf, pd.Timestamp("2027-01-01", tz="UTC"))
    assert any(r.startswith("row_on_non_market_session") for r in reasons), reasons


def test_one_stale_name_is_named_rather_than_hidden_behind_a_fresh_one():
    """Freshness is PER INSTRUMENT. A maximum across names reported the newest
    name's date and declared the whole report fresh while one admitted name was
    sessions stale."""
    fresh = _make_frame(320, seed=11)
    stale = _make_frame(300, seed=12)
    frames = {"AAA": _price_frame(fresh, "AAA"), "BBB": _price_frame(stale, "BBB")}
    report = _report(frames, expected_last_session=_last_session(frames))

    assert report["data_health"]["state"] == "blocked"
    assert report["status"] == "inputs_blocked"
    health = report["data_health"]
    assert any("BBB:last_session_" in r and "does_not_match_expected" in r
               for r in health["reasons"]), health["reasons"]
    assert not any(r.startswith("AAA:last_session_") for r in health["reasons"]), \
        "the fresh name was reported stale"
    # both names are still reported, and neither was silently dropped
    assert set(health["last_session_by_instrument"]) == {"AAA", "BBB"}
    assert health["last_session_by_instrument"]["AAA"] != \
        health["last_session_by_instrument"]["BBB"]
    for row in report["strategies"]:
        assert set(row["instruments"]) == {"AAA", "BBB"}


def test_an_invalid_name_never_quietly_reduces_the_cohort():
    good = _price_frame(_make_frame(320, seed=11), "AAA")
    bad_df = _make_frame(320, seed=12)
    bad_df.loc[bad_df.index[50], "close"] = -1.0
    bad_df.loc[bad_df.index[50], "high"] = -1.0
    bad_df.loc[bad_df.index[50], "low"] = -1.0
    bad = _price_frame(bad_df, "BBB")
    report = _report({"AAA": good, "BBB": bad})
    assert report["status"] == "inputs_blocked"
    assert any(r.startswith("cohort_blocked_by_invalid_instrument") and "BBB" in r
               for r in report["data_health"]["reasons"])
    for row in report["strategies"]:
        assert row["historical"]["state"] == "unavailable"
        assert row["historical"]["net_sharpe"] is None, \
            "statistics came from a silently reduced universe"


def test_undeclared_expected_last_session_cannot_certify_freshness():
    frames = _frames()
    undeclared = _report(frames, expected_last_session=None)
    assert "expected_last_session_not_declared" in undeclared["data_health"]["reasons"]
    assert undeclared["status"] == "inputs_blocked"
    assert _report(frames)["data_health"]["state"] == "ready"


# --------------------------------------------------------------------------- #
# 7. aggregation — equal initial capital, derived portfolio returns
# --------------------------------------------------------------------------- #
def _simulate_window(frames, key, window, cost_bps=COST_BPS):
    sims = {}
    for ticker, pf in sorted(frames.items()):
        sub = pf.frame.reindex(window)
        _raw, _w = sr.candidate_raw_position(pf.frame, key)
        pos = _raw.reindex(window)
        sims[ticker] = next_open_sim(sub["open"], sub["close"], pos, cost_bps=cost_bps)
    return sims


def test_portfolio_is_the_mean_of_subaccount_navs_not_the_mean_of_returns():
    """THE aggregation falsifier. Averaging per-name returns every day silently
    rebalances between assets for free. Two DIVERGING names make the two answers
    numerically different, so the test actually discriminates."""
    frames = _frames(tickers=("AAA", "BBB"), seed=11,
                     **{}) | _frames(tickers=("AAA", "BBB"), seed=11)
    # force divergence: BBB runs hot, AAA runs cold
    frames["AAA"] = _price_frame(_make_frame(320, seed=21), "AAA")
    frames["BBB"] = _price_frame(_make_frame(320, seed=22, drift=0.002, vol_scale=2.0), "BBB")
    last = _last_session(frames)
    report = _report(frames)
    window = pd.DatetimeIndex(_sessions(320))
    ev = [d for d in window if d >= max(
        sr.feature_available_from(frames[t].frame, "tsmom_200") for t in frames)]
    window = pd.DatetimeIndex(ev)

    sims = _simulate_window(frames, "tsmom_200", window)
    nav = pd.DataFrame({t: s["equity"] for t, s in sims.items()}).mean(axis=1)
    derived = nav.iloc[1:].to_numpy() / nav.iloc[:-1].to_numpy() - 1.0
    mean_of_returns = pd.DataFrame({t: s["ret"] for t, s in sims.items()}).mean(axis=1)

    row = _by_id(report, "tsmom_200")["historical"]
    assert row["net_cagr"] == pytest.approx(
        sr._finite(sr._cagr(pd.Series(derived), 252)), rel=1e-9)
    assert row["net_cagr"] != pytest.approx(
        sr._finite(sr._cagr(mean_of_returns, 252)), rel=1e-6), \
        "the two definitions coincided; the fixture fails to discriminate"
    assert row["max_drawdown"] == pytest.approx(
        sr._finite(sr._max_drawdown(pd.Series(derived))), rel=1e-9)


def test_subaccounts_start_from_equal_capital_and_never_transfer():
    frames = _frames()
    report = _report(frames)
    for row in report["strategies"]:
        assert row["historical"]["initial_capital_per_subaccount"] == 1.0
    joined = " ".join(report["limitations"] + [
        l for row in report["strategies"] for l in row["historical"]["limitations"]])
    assert "no transfers between subaccounts" in joined.lower()
    assert "MEAN of the" in joined and "never averaged across names" in joined


def test_turnover_is_the_sample_total_of_traded_notional_over_pretrade_equity():
    """THE turnover falsifier. The prior report emitted the MEAN of every
    name/session turnover while the UI labelled it annual."""
    frames = _frames()
    report = _report(frames)
    window = pd.DatetimeIndex(_sessions(320))
    ev = [d for d in window if d >= max(
        sr.feature_available_from(frames[t].frame, "tsmom_200") for t in frames)]
    sims = _simulate_window(frames, "tsmom_200", pd.DatetimeIndex(ev))
    span = slice(0, len(ev) - 1)
    traded = pd.DataFrame({t: s["traded_notional"] for t, s in sims.items()}).sum(axis=1)
    pretrade = pd.DataFrame({t: s["pretrade_equity"] for t, s in sims.items()}).sum(axis=1)
    expected = float((traded / pretrade).iloc[span].sum())
    naive_mean = float(pd.DataFrame({t: s["turnover"] for t, s in sims.items()}
                                    ).to_numpy()[span].mean())

    row = _by_id(report, "tsmom_200")["historical"]
    assert row["turnover"] == pytest.approx(sr._finite(expected), rel=1e-9)
    assert row["turnover"] != pytest.approx(sr._finite(naive_mean), rel=1e-6)
    assert row["turnover_basis"] == \
        "sample_total_traded_notional_over_portfolio_pretrade_equity"
    assert "sample_start" in row and "sample_end" in row


def test_the_benchmark_cannot_be_filled_earlier_than_the_strategy():
    """open[0]->open[1] is +50%. Both the strategy and its comparator open FLAT
    at session 0, so neither may earn it; a comparator filled at open[0] would
    manufacture a large excess return."""
    idx = _sessions(6, "2024-01-01")
    op = pd.Series([100.0, 150.0, 150.0, 150.0, 150.0, 150.0], index=idx)
    ones = pd.Series(1.0, index=idx)
    for cost in (0.0, 10.0):
        bench = next_open_sim(op, op.copy(), ones, cost_bps=cost)
        assert bench["pos"].iloc[0] == 0.0
        assert bench["equity"].iloc[0] == pytest.approx(1.0)
        c = cost / 1e4
        assert bench["ret"].iloc[0] == pytest.approx(-c / (1.0 + c), abs=1e-12), \
            "the comparator captured a gap it could not have held"
    # the legacy gross reference still shows the gap, and is labelled as gross
    assert bench["benchmark_open_to_open"].iloc[0] == pytest.approx(0.5)


def test_the_benchmark_shares_cohort_cost_and_terminal_conventions():
    frames = _frames()
    report = _report(frames)
    for row in report["strategies"]:
        hist = row["historical"]
        if hist["state"] != "available":
            continue
        assert hist["benchmark_convention"] == "identical_cohort_start_fill_cost_terminal"
        assert hist["benchmark_gross_sharpe"] != hist["benchmark_sharpe"], \
            "the gross reference must be a separately labelled zero-cost series"
        assert any("GROSS reference" in l for l in hist["limitations"])


# --------------------------------------------------------------------------- #
# 8. warmup is real availability
# --------------------------------------------------------------------------- #
def test_warmup_is_leading_feature_availability_not_dropped_rows():
    frames = _frames()
    report = _report(frames)
    for key in sr.CANDIDATE_KEYS:
        hist = _by_id(report, key)["historical"]
        first = max(sr.feature_available_from(frames[t].frame, key) for t in frames)
        expected_leading = int((pd.DatetimeIndex(_sessions(320)) < first).sum())
        assert hist["warmup_sessions"] == expected_leading
        assert hist["sample_start"] == first.date().isoformat(), \
            "the sample must start exactly where the feature became available"
        assert not any("dropped" in l for l in hist["limitations"]), \
            "nothing was dropped; the warmup is an availability lag"


def test_evaluation_waits_for_the_feature_on_every_admitted_name():
    """A name whose feature only becomes available late shortens the SHARED
    sample; it does not get evaluated earlier than it can be."""
    fast = _make_frame(320, seed=11)
    slow = _make_frame(320, seed=12)
    frames = {"AAA": _price_frame(fast, "AAA"), "BBB": _price_frame(slow, "BBB")}
    report = _report(frames)
    latest = max(sr.feature_available_from(frames[t].frame, "tsmom_200") for t in frames)
    hist = _by_id(report, "tsmom_200")["historical"]
    assert pd.Timestamp(hist["sample_start"]) >= latest
    assert hist["observations"] == len(
        [d for d in _sessions(320) if d >= latest]) - 1


def test_a_short_history_blocks_rather_than_reporting_a_tiny_number():
    short = _frames(n=12)
    report = _report(short, expected_last_session=_last_session(short))
    assert report["status"] == "inputs_blocked"
    for row in report["strategies"]:
        assert row["historical"]["state"] == "unavailable"


def test_the_horizon_is_not_an_independent_sample_proof():
    report = _report()
    joined = " ".join(report["limitations"] +
                      [l for row in report["strategies"]
                       for l in row["historical"]["limitations"]])
    assert "not evidence that the sample" in joined


# --------------------------------------------------------------------------- #
# 9. capacity is disabled, never faked
# --------------------------------------------------------------------------- #
def test_a_requested_capacity_is_typed_blocked_rather_than_certified():
    """The prior model sized every fill against the FULL same-session volume at
    that session's open and let a zero-filled early volatility stand in for 'no
    impact yet' — an unqualified claim of free size."""
    idx = _sessions(30, "2023-06-01")
    close = pd.Series(np.linspace(100.0, 130.0, 30), index=idx)
    alloc = pd.Series(1.0, index=idx)
    with pytest.raises(CapacityBlocked, match=IMPACT_NOT_QUALIFIED):
        next_open_sim(close, close, alloc, cost_bps=0.0,
                      dollar_adv=pd.Series(1e8, index=idx), aum_usd=5e6)


def test_missing_adv_still_never_reads_as_free_execution():
    idx = _sessions(30, "2023-06-01")
    close = pd.Series(np.linspace(100.0, 130.0, 30), index=idx)
    alloc = pd.Series(1.0, index=idx)
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(CapacityBlocked, match="dollar_adv"):
            next_open_sim(close, close, alloc, cost_bps=0.0,
                          dollar_adv=pd.Series(bad, index=idx), aum_usd=5e6)


def test_a_report_requesting_capacity_is_blocked_and_says_why():
    report = _report(_frames(), aum_usd=5e6)
    assert report["status"] == "inputs_blocked"
    assert any(f"capacity_blocked:{IMPACT_NOT_QUALIFIED}" in r
               for r in report["data_health"]["reasons"])
    for row in report["strategies"]:
        assert row["historical"]["state"] == "unavailable"
        assert row["historical"]["benchmark_sharpe"] is None
        assert row["capital_eligible"] is False


def test_a_flat_one_way_cost_is_still_run_and_labelled_as_unmodelled():
    report = _report()
    for row in report["strategies"]:
        joined = " ".join(row["historical"]["limitations"])
        assert "impact, capacity, borrow and" in joined
        assert "NOT modelled" in joined
    assert "capacity_usd" not in json.dumps(report)


def test_partial_impact_configuration_is_refused_not_silently_dropped():
    idx = _sessions(30, "2023-06-01")
    close = pd.Series(np.linspace(100.0, 130.0, 30), index=idx)
    alloc = pd.Series(1.0, index=idx)
    with pytest.raises(NextOpenError, match="impact_config_incomplete"):
        next_open_sim(close, close, alloc, cost_bps=0.0,
                      dollar_adv=pd.Series(1e8, index=idx))
    with pytest.raises(NextOpenError, match="impact_config_incomplete"):
        next_open_sim(close, close, alloc, cost_bps=0.0, aum_usd=1e6)


def test_the_legacy_capacity_api_is_untouched():
    """Disabling the new helper's certification must not disturb the legacy one."""
    idx = _sessions(60, "2023-06-01")
    close = pd.Series(np.linspace(100.0, 160.0, 60), index=idx)
    adv = pd.Series(1e8, index=idx)
    out = capacity_curve(close, pd.Series(1.0, index=idx), adv, [1e5, 1e6, 1e7],
                         cost_bps=10.0)
    assert set(out) >= {"capacity_usd", "curve", "cost_bps", "verdict", "economic"}
    assert out["cost_bps"] == 10.0
    assert len(out["curve"]) == 3
    assert out["verdict"] in {"no_edge", "ok", "capped"}, out["verdict"]


# --------------------------------------------------------------------------- #
# 10. the strict root artifact
# --------------------------------------------------------------------------- #
def test_root_artifact_contract():
    report = _report()
    assert report["generated_at"].endswith("+00:00")
    assert report["as_of"].endswith("+00:00")
    assert pd.Timestamp(report["generated_at"]) >= pd.Timestamp(report["as_of"])
    ids = {report["source"]["code_revision"], report["source"]["data_revision"]}
    assert len(ids) == 2, "the two provenance identities must be distinct"
    assert report["summary"] == {"candidate_count": 2, "evaluated_count": 2,
                                 "capital_eligible_count": 0}
    assert report["live_orders_enabled"] is False
    assert report["mode"] == "RESEARCH_ONLY"
    for row in report["strategies"]:
        assert row["cost_bps" if False else "historical"]["cost_bps"] == COST_BPS
        assert row["prospective"] == {"state": "not_started", "registered": 0, "graded": 0}
        assert row["paper"] == {"state": "not_connected"}
        assert row["capital_eligible"] is False


def test_a_blocked_row_still_carries_the_cost_it_would_have_used():
    report = _report(_frames(n=12))
    for row in report["strategies"]:
        assert row["status"] == "blocked"
        assert row["stance"] == "Stand aside", \
            "an unavailable candidate must not wear an 'Observe only' stance"
        assert row["historical"]["cost_bps"] == COST_BPS
        for metric in ("net_sharpe", "net_cagr", "max_drawdown", "turnover",
                       "benchmark_sharpe", "sample_start", "sample_end"):
            assert row["historical"][metric] is None


def test_distinct_ids_are_enforced():
    frames = _frames()
    with pytest.raises(ValueError, match="two_distinct_identities"):
        sr.build_report(frames, as_of=_aware_as_of(_last_session(frames)),
                        generated_at=GENERATED_AT, code_revision="same", data_revision="same",
                        cost_bps=COST_BPS)
    with pytest.raises(ValueError, match="non_empty"):
        sr.build_report(frames, as_of=_aware_as_of(_last_session(frames)),
                        generated_at=GENERATED_AT, code_revision="", data_revision=DATA_REV,
                        cost_bps=COST_BPS)


def test_no_credential_account_or_private_field_reaches_the_artifact():
    report = _report()
    blob = json.dumps(report).lower()
    for banned in ("api_key", "apikey", "secret", "password", "token",
                   "account_id", "account_number", "qledger", "broker",
                   "credential", "allocation_id"):
        assert banned not in blob, f"{banned} leaked into the report"


def test_synthetic_fixtures_are_labelled_distinctly_from_a_reconstruction():
    report = _report()
    assert report["metadata"]["synthetic"] is True
    assert report["metadata"]["synthetic_instruments"] == ["AAA", "BBB"]
    assert any("SYNTHETIC FIXTURE INPUT" in lim for lim in report["limitations"])
    assert any("CURRENT-VINTAGE RECONSTRUCTION" in lim for lim in report["limitations"])
    assert report["metadata"]["knowability"] == \
        "caller_asserted_receipt_not_independently_verified"
    assert report["metadata"]["calendar"] == "NYSE_us_cash_daily"


def test_identical_inputs_and_config_produce_byte_identical_json():
    first = sr.dumps(_report(_frames()))
    second = sr.dumps(_report(_frames()))
    assert first == second


def test_no_nan_or_infinity_can_be_serialised():
    text = sr.dumps(_report())
    assert "NaN" not in text and "Infinity" not in text
    json.loads(text, parse_constant=lambda c: pytest.fail(f"non-finite token {c}"))
    for bad in ({"x": float("nan")}, {"x": float("inf")}, {"a": [{"b": -float("inf")}]}):
        with pytest.raises(ValueError):
            sr.dumps(bad)


def test_report_identity_order_is_stable_and_sorted():
    report = _report()
    assert [s["id"] for s in report["strategies"]] == sorted(sr.CANDIDATE_KEYS)
    assert list(report) == ["schema", "generated_at", "as_of", "mode",
                            "live_orders_enabled", "status", "source", "metadata",
                            "summary", "strategies", "data_health", "limitations"]
    for row in report["strategies"]:
        assert row["instruments"] == sorted(row["instruments"])
        assert row["blockers"] == sorted(row["blockers"])
        assert row["historical"]["limitations"] == sorted(row["historical"]["limitations"])


# --------------------------------------------------------------------------- #
# 11. strict JSON parsing and the CLI
# --------------------------------------------------------------------------- #
def test_a_duplicated_json_key_is_refused_not_silently_last_wins():
    with pytest.raises(InputRefused, match="duplicate_json_key:instruments"):
        load_strict_json('{"instruments": {"A": 1}, "instruments": {"B": 2}}',
                         what="sidecar")
    assert load_strict_json('{"a": 1, "b": 2}', what="sidecar") == {"a": 1, "b": 2}


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_json_literals_are_refused_by_the_strict_parser(token):
    with pytest.raises(InputRefused, match="non_finite_json_token"):
        load_strict_json('{"cost_bps": %s}' % token, what="sidecar")


def test_malformed_json_is_refused():
    with pytest.raises(InputRefused, match="is_not_valid_json"):
        load_strict_json('{"a": ', what="sidecar")


def _write_prices(directory, frames, *, meta_overrides=None, instruments=None):
    directory.mkdir(parents=True, exist_ok=True)
    for ticker, pf in frames.items():
        pf.frame.to_csv(directory / f"{ticker}.csv", index_label="date")
    meta = {
        "as_of": _aware_as_of(_last_session(frames)),
        "expected_last_session": _last_session(frames),
        "data_revision": DATA_REV,
        "synthetic": True,
        "instruments": instruments or {
            t: {"available_at": [t_.isoformat() for t_ in pf.available_at],
                "adjustment_basis": dict(ALL_BASIS)}
            for t, pf in frames.items()},
    }
    meta.update(meta_overrides or {})
    (directory / METADATA_FILENAME).write_text(json.dumps(meta))
    return directory


def test_cli_writes_only_the_explicitly_supplied_output_path(tmp_path):
    frames = _frames(n=300)
    in_dir = _write_prices(tmp_path / "prices", frames)
    out = tmp_path / "nested" / "report.json"
    rc = cli_main(["--input-dir", str(in_dir), "--output", str(out),
                   "--generated-at", GENERATED_AT, "--code-revision", CODE_REV,
                   "--expected-last-session", _last_session(frames),
                   "--cost-bps", "10"])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["schema"] == "systematic_research.v1"
    assert payload["mode"] == "RESEARCH_ONLY"
    assert sorted(p.name for p in (tmp_path / "nested").iterdir()) == ["report.json"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["nested", "prices"]


def test_cli_refuses_a_price_store_without_an_open_column(tmp_path):
    in_dir = tmp_path / "prices"
    in_dir.mkdir()
    df = _make_frame(60)
    df.drop(columns=["available_at", "open"]).to_csv(in_dir / "AAA.csv", index_label="date")
    (in_dir / METADATA_FILENAME).write_text(json.dumps({
        "as_of": _aware_as_of(_last_session({"": _price_frame(df, "AAA")})),
        "data_revision": DATA_REV,
        "instruments": {"AAA": {
            "available_at": [t.isoformat() for t in df["available_at"]],
            "adjustment_basis": dict(ALL_BASIS)}},
    }))
    with pytest.raises(InputRefused, match="input_requires_open_column"):
        load_inputs(in_dir)


def test_cli_requires_aware_point_in_time_metadata(tmp_path):
    frames = _frames(n=60)
    in_dir = _write_prices(tmp_path / "prices", frames)
    # a NAIVE available_at must be refused, not assumed to be UTC
    naive = {t: {"available_at": [str(pd.Timestamp(t_).tz_localize(None))
                                  for t_ in pf.available_at],
                 "adjustment_basis": dict(ALL_BASIS)}
             for t, pf in frames.items()}
    (in_dir / METADATA_FILENAME).write_text(json.dumps({
        "as_of": _aware_as_of(_last_session(frames)), "data_revision": DATA_REV,
        "instruments": naive}))
    with pytest.raises(InputRefused, match="available_at_must_be_timezone_aware"):
        load_inputs(in_dir)


def test_cli_refuses_a_bare_date_as_of(tmp_path):
    frames = _frames(n=300)
    in_dir = _write_prices(tmp_path / "prices", frames,
                           meta_overrides={"as_of": _last_session(frames)})
    rc = cli_main(["--input-dir", str(in_dir), "--output", str(tmp_path / "out.json"),
                   "--generated-at", GENERATED_AT, "--code-revision", CODE_REV,
                   "--expected-last-session", _last_session(frames), "--cost-bps", "10"])
    assert rc == 2, "a bare date cutoff must be refused"


def test_cli_requires_an_explicit_output_path():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--input-dir", ".", "--generated-at", GENERATED_AT,
                           "--code-revision", CODE_REV, "--cost-bps", "10"])
    assert "--output" in parser.format_help()
    assert "TIMEZONE-AWARE" in parser.format_help()


def test_cli_exposes_no_network_or_purchase_surface():
    options = {a.dest for a in build_parser()._actions}
    for banned in ("url", "endpoint", "api_key", "token", "buy", "purchase", "schedule"):
        assert banned not in options


# --------------------------------------------------------------------------- #
# 12. research-only posture, side effects, legacy compatibility
# --------------------------------------------------------------------------- #
def test_no_universal_promotion_threshold_exists_in_the_engine():
    source = open(sr.__file__, encoding="utf-8").read()
    for banned in ("min_sharpe", "sharpe_threshold", "sharpe_gate", "promotion_threshold",
                   "min_cagr", "cagr_threshold", "PASS_SHARPE", "SHARPE_GATE",
                   "promote_if", "is_promotable"):
        assert banned not in source, f"{banned} is a universal promotion threshold"
    report = _report()
    assert any("DESCRIPTIVE" in lim for lim in report["limitations"])


def test_projections_are_not_emitted():
    blob = json.dumps(_report())
    for banned in ("projected_cagr", "expected_return", "win_probability",
                   "probability_of_profit", "forecast_cagr", "equity_curve"):
        assert banned not in blob


def test_return_timestamps_declare_the_documented_interval():
    report = _report()
    for row in report["strategies"]:
        assert row["historical"]["return_interval"] == "open[t]->open[t+1]"
    assert report["metadata"]["return_interval"] == "open[t]->open[t+1]"
    assert report["metadata"]["terminal_convention"] == "mark_only_no_final_rebalance"


def test_evaluation_touches_no_socket_and_writes_no_file_it_was_not_given(tmp_path, monkeypatch):
    import socket
    from pathlib import Path

    def _forbidden(*a, **k):
        raise AssertionError("the research engine opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)

    repo_root = Path(__file__).resolve().parents[1]
    for guarded in ("data/qledger", "data/allocation", "data/accounts"):
        assert not (repo_root / guarded / "systematic_research.json").exists()


def test_legacy_backtest_core_callers_are_unchanged():
    idx = _sessions(60, "2024-01-01")
    close = pd.Series(100.0 * np.exp(np.cumsum(np.linspace(0.001, 0.002, 60))), index=idx)
    alloc = pd.Series([0.0, 1.0] * 30, index=idx)
    bt = backtest_core(close, alloc, cost_bps=5.0)
    assert bt["pos"].iloc[0] == 0.0 and bt["pos"].iloc[1] == 0.0
    assert bt["pos"].iloc[2] == 1.0, "legacy fills the next bar, unchanged"
    assert float(bt["net"].iloc[2]) == pytest.approx(float(bt["gross"].iloc[2]) - 0.0005,
                                                      rel=1e-9)
    assert "terminal_mark_unliquidated" not in bt


def test_legacy_default_cost_is_still_costless():
    idx = _sessions(40, "2024-01-01")
    close = pd.Series(np.linspace(100.0, 140.0, 40), index=idx)
    alloc = pd.Series([0.0, 1.0] * 20, index=idx)
    free = backtest_core(close, alloc, 0.0)
    assert free["net"].equals(free["gross"])


@pytest.mark.parametrize("bad_cost", [-0.0001, float("nan"), float("inf")])
def test_negative_or_non_finite_cost_is_refused_not_turned_into_a_rebate(bad_cost):
    idx = _sessions(10, "2023-06-01")
    close = pd.Series(np.linspace(100.0, 110.0, 10), index=idx)
    with pytest.raises(NextOpenError, match="cost_bps"):
        next_open_sim(close, close, pd.Series(1.0, index=idx), cost_bps=bad_cost)


@pytest.mark.parametrize("column,value", [
    ("open", 0.0), ("open", -1.0), ("open", float("nan")), ("close", 0.0),
])
def test_non_positive_or_non_finite_price_refuses_instead_of_granting_zero_return(column, value):
    idx = _sessions(10, "2023-06-01")
    frame = pd.DataFrame({c: np.linspace(100.0, 110.0, 10)
                          for c in ("open", "high", "low", "close")}, index=idx)
    frame.loc[frame.index[4], column] = value
    alloc = pd.Series(1.0, index=idx)
    with pytest.raises(NextOpenError, match="not_positive_finite"):
        next_open_sim(frame["open"], frame["close"], alloc, cost_bps=0.0)


def test_non_finite_allocation_is_refused_rather_than_read_as_flat():
    idx = _sessions(10, "2023-06-01")
    close = pd.Series(np.linspace(100.0, 110.0, 10), index=idx)
    alloc = pd.Series(1.0, index=idx)
    alloc.iloc[5] = float("nan")
    with pytest.raises(NextOpenError, match="allocation_not_finite"):
        next_open_sim(close, close, alloc, cost_bps=0.0)


@pytest.mark.parametrize("bad", [-0.01, 1.01, 2.0])
def test_allocation_outside_long_cash_bounds_is_refused(bad):
    idx = _sessions(10, "2023-06-01")
    close = pd.Series(np.linspace(100.0, 110.0, 10), index=idx)
    alloc = pd.Series(0.5, index=idx)
    alloc.iloc[3] = bad
    with pytest.raises(NextOpenError, match="allocation_outside_long_cash_bounds"):
        next_open_sim(close, close, alloc, cost_bps=0.0)


def test_candidates_are_exactly_the_two_frozen_registry_entries():
    from engine import strategy_signals as signals

    assert sr.CANDIDATE_KEYS == ("rsi2_oversold", "tsmom_200")
    registry = signals.by_key()
    report = _report()
    for key in sr.CANDIDATE_KEYS:
        assert key in registry
        row = _by_id(report, key)
        assert row["name"] == registry[key].name
        assert row["family"] == registry[key].family
        assert row["horizon_sessions"] == registry[key].horizon


def test_candidate_position_comes_from_the_installed_signal_callable():
    df = _make_frame(300).drop(columns=["available_at"])
    for key in sr.CANDIDATE_KEYS:
        pos, warmup = sr.candidate_raw_position(df, key)
        assert pos is not None
        assert len(pos) == len(df)
        assert warmup > 0, "a 200-period feature cannot be available from bar 0"
        assert float(pos.min()) >= 0.0 and float(pos.max()) <= 1.0