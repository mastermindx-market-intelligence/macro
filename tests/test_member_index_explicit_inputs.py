"""Independent legacy numerical parity and explicit close-index consumer proof."""
from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from engine import basket_index, sector_cycles
from lib import config, adjusted_price_capture
from tests.fixtures import base_basket_index_7885 as baseline


def inputs(case="ordinary", count=365):
    idx = pd.bdate_range(end="2026-11-03", periods=count).as_unit("ns")
    x = np.arange(count, dtype=float)
    frames = {}
    for i, ticker in enumerate(("A", "B", "C", "D")):
        close = 50 + i * 20 + x * (.04 + i * .02) + np.sin(x / (9 + i))
        frames[ticker] = pd.DataFrame({"open": close * .999, "high": close * 1.01,
            "low": close * .99, "close": close, "volume": 1000 + x % 20 * (i + 1)}, index=idx)
    members = [{"ticker": t, "added": str(idx[30 if t == "C" else 0].date()),
                "weight": i + 1} for i, t in enumerate(frames)]
    if case == "late":
        frames["C"].iloc[:150] = np.nan
    elif case in ("tail5", "tail6"):
        frames["C"].iloc[-int(case[-1]):] = np.nan
    elif case == "interior":
        frames["C"].iloc[180:200] = np.nan
    elif case == "removed":
        members[2]["removed"] = str(idx[-2].date())
        frames["C"].iloc[-6:] = np.nan
    return members, idx, frames


def wide(frames, field):
    return pd.concat({t: frame[field] for t, frame in frames.items() if field in frame}, axis=1)


def install_loaders(monkeypatch, frames):
    monkeypatch.setattr(baseline, "_load_member_ohlcv", lambda t: None if t not in frames else frames[t].copy())
    monkeypatch.setattr(basket_index, "_load_member_ohlcv", lambda t: None if t not in frames else frames[t].copy())


CASES = ("ordinary", "late", "tail5", "tail6", "interior", "removed")
MODES = [(mode, pit, alpha_pit) for mode in ("equal", "relevance", "alpha") for pit in (True, False)
         for alpha_pit in ((True, False) if mode == "alpha" else (True,))]


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("mode,pit,alpha_pit", MODES)
def test_full_legacy_candle_matches_literal_base_exactly(case, mode, pit, alpha_pit, monkeypatch):
    members, idx, frames = inputs(case)
    install_loaders(monkeypatch, frames)
    kwargs = dict(mode=mode, pit=pit, alpha_pit=alpha_pit, conv_map={"A": 90, "C": 25})
    expected, expected_meta = baseline.consolidated_candle(members, idx, **kwargs)
    observed, meta = basket_index.consolidated_candle(members, idx, **kwargs)
    pd.testing.assert_frame_equal(expected, observed, check_exact=True)
    assert meta == expected_meta


@pytest.mark.parametrize("case", CASES)
def test_close_only_path_matches_original_current_member_index_without_range_fields(case, monkeypatch):
    members, idx, frames = inputs(case)
    install_loaders(monkeypatch, frames)
    old, old_meta = baseline.consolidated_candle(members, idx, mode="equal", pit=False)
    close = wide(frames, "close")
    volume = wide(frames, "volume")
    observed, meta = basket_index.member_index_from_inputs(members, idx, close=close, volume=volume)
    pd.testing.assert_series_equal(observed, old["close"].replace([np.inf, -np.inf], np.nan).dropna(),
                                   check_exact=True)
    assert meta["n_live"] == old_meta["n_live"]
    assert meta["n_stale_tail"] == old_meta["n_stale_tail"]
    assert meta["coverage_pct"] == old_meta["coverage_pct"]
    assert "n_with_ohlcv" not in meta
    if case == "tail5":
        assert meta["n_stale_tail"] == 0 and meta["n_live"] == 4
    if case == "tail6":
        assert meta["n_stale_tail"] == 1 and meta["n_live"] == 3
    if case in ("interior", "removed"):
        assert meta["n_stale_tail"] == 0


def forbidden(*args, **kwargs):
    raise AssertionError("Ambient loader/config/store/cache reached")


def test_explicit_entry_and_sector_adapter_have_no_ambient_effects_or_input_mutation(monkeypatch, caplog):
    members, idx, frames = inputs()
    close, volume = wide(frames, "close"), wide(frames, "volume")
    before_members, before_close, before_volume = deepcopy(members), close.copy(), volume.copy()
    for owner, name in ((basket_index, "_load_member_ohlcv"), (basket_index, "deep_calendar"),
                        (basket_index.data_store, "read"), (config, "load"), (config, "data_dir"),
                        (pd, "read_parquet")):
        monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setattr(basket_index, "_CACHE", object())
    observed, meta = basket_index.member_index_from_inputs(members, idx, close=close, volume=volume)
    candle = sector_cycles.member_candle_from_inputs(members, idx, close=close, volume=volume)
    assert isinstance(candle, sector_cycles.MemberIndexCandle)
    pd.testing.assert_series_equal(candle.close, observed, check_exact=True)
    assert candle.n_live == 4 and candle.coverage_pct == 1
    assert meta["status"] == "available" and not caplog.records
    assert members == before_members
    pd.testing.assert_frame_equal(close, before_close)
    pd.testing.assert_frame_equal(volume, before_volume)
    observed.iloc[-1] = -1
    second, _ = basket_index.member_index_from_inputs(members, idx, close=close, volume=volume)
    assert second.iloc[-1] > 0
    assert not hasattr(candle, "open") and not hasattr(candle, "high")


def test_missing_volume_is_unavailable_and_supplied_volume_is_not_forward_filled():
    members, idx, frames = inputs()
    close, volume = wide(frames, "close"), wide(frames, "volume")
    without, missing = basket_index.member_index_from_inputs(members, idx, close=close)
    assert missing["coverage_pct"] is None and missing["n_live_with_volume"] is None
    volume.loc[idx[-1], ["B", "C", "D"]] = np.nan
    with_volume, known = basket_index.member_index_from_inputs(members, idx, close=close, volume=volume)
    pd.testing.assert_series_equal(without, with_volume, check_exact=True)
    assert known["n_live_with_volume"] == 1 and known["coverage_pct"] == .25
    volume.loc[idx[-1], "A"] = 0
    _, zero = basket_index.member_index_from_inputs(members, idx, close=close, volume=volume)
    assert zero["coverage_pct"] == 0


@pytest.mark.parametrize("raw_count,available", [(299, False), (300, False), (301, True)])
def test_three_hundred_session_floor_counts_constructed_returns(raw_count, available):
    members, idx, frames = inputs(count=raw_count)
    observed, meta = basket_index.member_index_from_inputs(members, idx, close=wide(frames, "close"))
    assert (observed is not None) is available
    assert meta["index_sessions"] == raw_count - 1
    assert meta["reason"] == (None if available else "insufficient_index_history")
    candle = sector_cycles.member_candle_from_inputs(members, idx, close=wide(frames, "close"))
    assert (candle is not None) is available


def test_resolved_member_gate_is_distinct_and_is_not_a_daily_three_live_floor():
    members, idx, frames = inputs()
    two = wide(frames, "close").loc[:, ["A", "B"]]
    absent, meta = basket_index.member_index_from_inputs(members, idx, close=two)
    assert absent is None and meta["n_with_close"] == 2
    three_members = deepcopy(members[:3])
    three_members[2]["removed"] = str(idx[70].date())
    full, meta = basket_index.member_index_from_inputs(three_members, idx, close=wide(frames, "close"))
    assert full is not None and meta["n_live"] == 2
    with pytest.raises(ValueError, match="Ambiguous"):
        basket_index.member_index_from_inputs([members[0], members[1], members[0]], idx, close=two)


def test_first_return_keeps_original_denominator_and_is_not_rebased_to_one():
    idx = pd.bdate_range(end="2026-11-03", periods=310)
    x = np.arange(len(idx))
    close = pd.DataFrame({"A": 100 * 1.01 ** x, "B": 200 * 1.01 ** x,
                          "C": np.r_[np.nan, 50 * 1.01 ** x[1:]]}, index=idx)
    members = [{"ticker": ticker, "added": "2026-10-01"} for ticker in close]
    full, meta = basket_index.member_index_from_inputs(members, idx, close=close)
    assert full.iloc[0] == pytest.approx(1 + .02 / 3)
    assert full.index[0] == idx[1] and meta["pit"] is False


@pytest.mark.parametrize("kind", ("duplicate", "timezone", "reverse", "null_date", "nonnumeric", "negative", "infinite"))
def test_explicit_invalid_prices_or_calendars_refuse_without_repair(kind):
    members, idx, frames = inputs()
    close = wide(frames, "close")
    if kind == "duplicate":
        close = pd.concat([close, close[["A"]]], axis=1)
    elif kind == "timezone":
        idx = idx.tz_localize("UTC")
    elif kind == "reverse":
        close = close.iloc[::-1]
    elif kind == "null_date":
        idx = pd.DatetimeIndex([pd.NaT, *idx[1:]])
    elif kind == "nonnumeric":
        close["A"] = "100"
    elif kind == "negative":
        close.iloc[0, 0] = -1
    elif kind == "infinite":
        close.iloc[0, 0] = np.inf
    with pytest.raises(ValueError):
        basket_index.member_index_from_inputs(members, idx, close=close)


def test_projection_bound_precedes_union_allocation(monkeypatch):
    members, idx, frames = inputs()
    monkeypatch.setattr(adjusted_price_capture, "MAX_PANEL_CELLS", len(idx) * 3)
    with pytest.raises(ValueError, match="projection"):
        basket_index.member_index_from_inputs(members, idx, close=wide(frames, "close"))
