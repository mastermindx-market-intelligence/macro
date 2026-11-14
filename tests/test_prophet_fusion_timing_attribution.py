"""Attribution is an outcome comparator, never a new prediction or favorable-day filter."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import prophet_fusion_timing_attribution as a
from scripts.prophet_fusion_mechanisms import MechanismRefusal


@pytest.fixture
def control_case():
    pool = pd.DataFrame({
        "ticker": ["A", "A", "A", "B", "B"],
        "date": pd.to_datetime(["2020-01-02", "2020-01-03", "2020-02-03", "2020-01-02", "2020-01-03"]),
        "month": ["2020-01", "2020-01", "2020-02", "2020-01", "2020-01"],
        "horizon": [21] * 5,
        "control_net_excess": [.01, .03, .09, -.05, -.03],
        "control_net_return": [.02, .04, .10, -.04, -.02],
    })
    events = pd.DataFrame({
        "ticker": ["A", "A", "B"], "date": pd.to_datetime(["2020-01-02", "2020-02-03", "2020-01-03"]),
        "trigger": ["technical_core_t12"] * 3, "horizon": [21] * 3,
        "net_excess": [.01, .09, -.03], "net_return": [.02, .10, -.02],
        "market_uptrend": [True, True, False], "no_volatility_stress": [True, False, True],
    })
    return events, pool


def test_controls_are_matched_by_asset_month_and_horizon(control_case):
    events, pool = control_case
    frame = a.attach_controls(events, pool)
    assert frame["control_net_excess"].tolist() == pytest.approx([.02, .09, -.04])
    assert frame["timing_residual_net_excess"].tolist() == pytest.approx([-.01, .0, .01])
    assert frame["control_dates"].tolist() == [2, 1, 2]


def test_missing_control_is_not_imputed_as_neutral(control_case):
    events, pool = control_case
    with pytest.raises(MechanismRefusal, match="WITHOUT"):
        a.attach_controls(events, pool.loc[pool.ticker.eq("A")])


def test_duplicate_control_date_cannot_inflate_weight(control_case):
    events, pool = control_case
    with pytest.raises(MechanismRefusal, match="DUPLICATE"):
        a.attach_controls(events, pd.concat([pool, pool.iloc[:1]], ignore_index=True))


def test_attribution_does_not_mutate_primary_events(control_case):
    events, pool = control_case
    before = events.copy(deep=True)
    a.attach_controls(events, pool)
    pd.testing.assert_frame_equal(before, events)


def test_secondary_report_has_no_pvalue_or_promotion(control_case):
    events, pool = control_case
    spec = {"triggers": ["technical_core_t12"], "contexts": ["unfiltered", "market_uptrend", "no_volatility_stress"]}
    summaries = a.summarize(a.attach_controls(events, pool), spec)
    assert len(summaries) == 6
    assert all(row["promotion_eligible"] is False for row in summaries)
    assert summaries[0]["timing_residual_net_excess"] == pytest.approx(0)
    assert summaries[0]["minimum_control_dates_per_event_month"] == 1
    text = a.render({"summaries": summaries})
    assert "not a new primary test" in text
    assert "No p-values" in text
    assert "never a historical decision input" in text


def test_control_pool_uses_all_known_days_not_only_bullish_trigger_days():
    dates = pd.bdate_range("2018-01-01", periods=420)
    rng = np.random.default_rng(88)
    prices = pd.Series(100 * np.exp(np.cumsum(rng.normal(.0002, .008, len(dates)))), index=dates)
    spec = {"start": str(dates[280].date()), "end": str(dates[320].date()), "primary_round_trip_cost_bps": 25}
    observations = pd.DataFrame({"signal": pd.Series(False, index=dates, dtype="boolean")}, index=dates)
    pool = a.control_pool(prices, prices, observations, spec, "A")
    assert len(pool) == 41 * 2
    assert pool["control_net_excess"].lt(0).all()  # identical asset/benchmark; only friction remains
    assert set(pool["horizon"]) == {21, 63}
    assert pool["date"].nunique() == 41


def test_unavailable_observation_removes_current_and_three_following_controls():
    dates = pd.bdate_range("2018-01-01", periods=420)
    rng = np.random.default_rng(89)
    prices = pd.Series(100 * np.exp(np.cumsum(rng.normal(.0002, .008, len(dates)))), index=dates)
    spec = {"start": str(dates[280].date()), "end": str(dates[320].date()), "primary_round_trip_cost_bps": 25}
    observations = pd.DataFrame({"signal": pd.Series(False, index=dates, dtype="boolean")}, index=dates)
    observations.loc[dates[300], "signal"] = pd.NA
    pool = a.control_pool(prices, prices, observations, spec, "A")
    assert len(pool) == (41 - 4) * 2
    assert not pool["date"].isin(dates[300:304]).any()


def test_constant_market_is_not_a_measured_no_stress_control():
    dates = pd.bdate_range("2018-01-01", periods=420)
    prices = pd.Series(100., index=dates)
    spec = {"start": str(dates[280].date()), "end": str(dates[320].date()), "primary_round_trip_cost_bps": 25}
    observations = pd.DataFrame({"signal": False}, index=dates)
    with pytest.raises(MechanismRefusal, match="NO_COMMON_QUALIFIED"):
        a.control_pool(prices, prices, observations, spec, "A")
