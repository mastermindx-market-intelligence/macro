"""Supplied-frame numerical/provenance contracts; no live data or financial mocks."""
from copy import deepcopy
import json
import math

import numpy as np
import pandas as pd
import pytest

from engine import intl_inputs, intl_performance as owner
from engine.intl_performance_records import build_return_records as build
from lib import config, store


@pytest.fixture(autouse=True)
def no_data_reads(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("adapter attempted a collector/store read")
    monkeypatch.setattr(intl_inputs, "_intl_closes", forbidden)
    monkeypatch.setattr(store, "read", forbidden)


@pytest.fixture
def closes():
    dates = pd.date_range("2025-12-10", periods=30)
    return pd.DataFrame({
        "^N225": np.linspace(100., 129., 30),
        "USDJPY=X": np.linspace(100., 158., 30),
        "^FTSE": np.linspace(100., 129., 30),
        "GBPUSD=X": np.linspace(1., 1.29, 30),
    }, index=dates)


def record(frame, market="JP", horizon="1m"):
    result = build(frame, market_ids=[market], source_reference="fixture:owner-input")
    json.dumps(result, allow_nan=False)
    return next(row for row in result["records"] if row["horizon"] == horizon)


@pytest.mark.parametrize("market,expected,orientation,label", [
    ("JP", ((129/158)/(108/116)-1)*100, "local_per_USD", "Nikkei 225"),
    ("GB", ((129*1.29)/(108*1.08)-1)*100, "USD_per_local", "FTSE 100"),
])
def test_real_orientation_primary_identity_and_same_window(closes, market, expected, orientation, label):
    row = record(closes, market)
    local = (129/108-1)*100
    assert row["index_label"] == label
    assert row["fx_quote_orientation"] == orientation
    assert row["local"]["value"] == pytest.approx(local, abs=1e-12)
    assert row["usd"]["value"] == pytest.approx(expected, abs=1e-12)
    assert row["fx_contribution"]["value"] == pytest.approx(expected-local, abs=1e-12)
    assert row["local"]["window"] == row["usd"]["window"] == row["fx_contribution"]["window"]
    assert row["usd"]["window"]["start"] == closes.index[-22].isoformat()
    assert row["usd"]["window"]["calendar_policy"] == "owner_union_forward_fill"
    assert row["qualification"] == "not_evaluated"
    assert row["return_basis"] == "price"
    assert row["fx_contribution"]["unit"] == "percentage_points"


def test_fill_dates_are_actual_contributors_not_calculation_dates(closes):
    closes.loc[closes.index[-1], "^N225"] = np.nan
    closes.loc[closes.index[-2:], "USDJPY=X"] = np.nan
    row = record(closes)
    window = row["usd"]["window"]
    assert window["end"] == closes.index[-2].isoformat()
    assert window["endpoint_observations"]["price_end"] == closes.index[-2].isoformat()
    assert window["endpoint_observations"]["fx_end"] == closes.index[-3].isoformat()
    assert row["qualification"] == "not_evaluated"


def test_owner_leading_local_gap_uses_only_the_real_shared_suffix():
    dates = pd.date_range("2025-12-01", periods=35)
    px = np.arange(100., 135.); px[1::2] = np.nan
    fx = np.repeat(100., 35); fx[0] = np.nan
    frame = pd.DataFrame({"^N225": px, "USDJPY=X": fx}, index=dates)
    row = record(frame)
    assert row["local"]["window"] == row["usd"]["window"]
    assert row["usd"]["window"]["start"] == dates[-22].isoformat()
    assert row["usd"]["window"]["endpoint_observations"]["price_start"] == dates[-23].isoformat()
    assert row["usd"]["value"] == pytest.approx((134/112-1)*100)
    assert row["local"]["value"] == row["usd"]["value"]


def test_missing_fx_keeps_distinct_observed_local_calendar(closes):
    frame = closes[["^N225"]].copy()
    frame.iloc[-2, 0] = np.nan
    row = record(frame)
    assert row["usd"]["value"] is None
    assert row["fx_contribution"]["value"] is None
    assert row["local"]["window"]["calendar_policy"] == "observed_local_prices"
    assert row["local"]["window"]["start"] == frame.index[-23].isoformat()
    assert row["local"]["window"]["endpoint_observations"]["fx_start"] is None
    assert row["local"]["value"] == pytest.approx((129/107-1)*100)


@pytest.mark.parametrize("tz", [None, "Etc/GMT-14", "Etc/GMT+12"])
def test_ytd_preserves_local_year_timezone_and_timestamp_precision(tz):
    dates = pd.DatetimeIndex(["2025-12-31 23:30:00.123456789", "2026-01-01 00:30:00.123456789",
                              "2026-01-02 00:30:00.123456789"])
    if tz:
        dates = dates.tz_localize(tz)
    frame = pd.DataFrame({"^N225": [100., 110., 120.], "USDJPY=X": [100., 100., 100.]}, index=dates)
    before = frame.copy(deep=True)
    row = record(frame, horizon="ytd")
    assert row["local"]["value"] == pytest.approx(20.)
    assert row["local"]["window"]["start"] == dates[0].isoformat()
    assert row["local"]["window"]["end"] == dates[-1].isoformat()
    pd.testing.assert_frame_equal(frame, before)


def test_ytd_without_prior_year_and_short_horizons_are_explicit(closes):
    frame = closes.iloc[-2:]
    for row in build(frame, market_ids=["JP"])["records"]:
        for leg in ("local", "usd", "fx_contribution"):
            assert row[leg]["value"] is None
            assert row[leg]["reason"] == "insufficient_history"
    empty = frame.iloc[:0]
    assert build(empty, market_ids=["JP"])["numerical_status"] == "unavailable"


@pytest.mark.parametrize("bad", [True, np.bool_(True), "100", float("inf"), -float("inf"), 0., -1., 1+0j])
@pytest.mark.parametrize("column", ["^N225", "USDJPY=X"])
def test_invalid_observation_never_disappears_into_a_success(closes, column, bad):
    frame = closes.astype(object)
    # Even outside the selected endpoint window this invalid observation is not
    # silently filtered. Validation withholds the affected source-dependent leg.
    frame.loc[frame.index[0], column] = bad
    row = record(frame)
    assert row["usd"]["value"] is None
    assert row["usd"]["reason"] == "invalid_observation"
    assert row["fx_contribution"]["value"] is None
    assert (row["local"]["value"] is None) == (column == "^N225")
    # One broken market does not erase a separately valid market.
    assert record(frame, "GB")["usd"]["value"] is not None


@pytest.mark.parametrize("kind", ["reverse", "duplicate_date", "nat", "non_date", "duplicate_column"])
def test_invalid_geometry_refuses_without_sorting_or_deduplication(closes, kind):
    if kind == "reverse":
        frame = closes.iloc[::-1]
    elif kind == "duplicate_date":
        frame = pd.concat([closes.iloc[:1], closes])
    elif kind == "nat":
        frame = closes.set_axis(pd.DatetimeIndex([pd.NaT, *closes.index[1:]]))
    elif kind == "non_date":
        frame = closes.set_axis(range(len(closes)))
    else:
        frame = pd.concat([closes, closes[["^N225"]]], axis=1)
    before = frame.copy(deep=True)
    result = build(frame, market_ids=["JP"])
    assert result["numerical_status"] == "unavailable"
    assert result["reason"] == "invalid_geometry"
    assert result["records"] == []
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("selection", ["JP", b"JP", ["JP", "JP"], ["XX"], [True], [{}]])
def test_invalid_market_request_is_closed(closes, selection):
    with pytest.raises(ValueError, match="invalid_request"):
        build(closes, market_ids=selection)


def test_empty_selection_and_unknown_source_are_honest(closes):
    result = build(closes, market_ids=[])
    assert result["records"] == []
    assert result["reason"] == "no_markets"
    assert result["source_reference"] is None
    assert result["source_reference_reason"] == "unknown"
    for bad in [True, 3, "", "  "]:
        with pytest.raises(ValueError, match="invalid_request:source_reference"):
            build(closes, source_reference=bad)


@pytest.mark.parametrize("end", [100., 90., 100.04001, 100.04999])
def test_zero_losses_and_near_display_ties_remain_unrounded(end):
    frame = pd.DataFrame({"^N225": [100.]*21+[end], "USDJPY=X": [100.]*22},
                         index=pd.date_range("2025-12-01", periods=22))
    row = record(frame)
    assert row["local"]["value"] == pytest.approx((end/100-1)*100, abs=1e-12)
    assert row["local"]["numerical_status"] == "available"
    if end in (100.04001, 100.04999):
        assert row["local"]["value"] != round(row["local"]["value"], 1)


def test_derived_usd_overflow_is_null_and_local_survives():
    frame = pd.DataFrame({"^N225": [1e308]*30, "USDJPY=X": [1e-308]*30},
                         index=pd.date_range("2025-12-01", periods=30))
    row = record(frame)
    assert row["local"]["value"] == 0.
    assert row["usd"]["value"] is None
    assert row["usd"]["reason"] == "invalid_calculation"


def test_config_input_and_legacy_rounded_leaderboard_are_unchanged(closes):
    before = closes.copy(deep=True)
    config_before = deepcopy(config.load())
    legacy_before = owner.usd_leaderboard(closes)
    result = build(closes)
    assert list(dict.fromkeys(row["market_id"] for row in result["records"])) == list(intl_inputs.countries())
    assert [row["horizon"] for row in result["records"] if row["market_id"] == "JP"] == [
        *owner._pcfg()["horizons_d"], "ytd",
    ]
    assert config.load() == config_before
    pd.testing.assert_frame_equal(closes, before)
    assert owner.usd_leaderboard(closes) == legacy_before
    assert result["numerical_status"] == "partial"
    json.dumps(result, allow_nan=False)
