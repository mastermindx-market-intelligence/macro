"""Hermetic arithmetic, causality and null-behavior tests; never investment validation."""
import copy

import numpy as np
import pandas as pd
import pytest

from engine.darkflow_index import Policy, build_index, canonical_symbol, decompose


@pytest.fixture
def inputs():
    dates = pd.bdate_range("2026-01-05", periods=8)
    panel, prices = [], []
    for i, date in enumerate(dates):
        for ticker, close, short in [("A", 10, 20 + i), ("B", 100, 60 + i)]:
            panel.append(dict(date=date, ticker=ticker, short_vol=short,
                              short_exempt=2.5, total_vol=100.5))
            prices.append(dict(date=date, ticker=ticker, close=close))
    membership = pd.DataFrame([dict(ticker=t, start_date="2020-01-01", end_date=None, src="sp500")
                               for t in ["A", "B"]])
    return dict(panel=pd.DataFrame(panel), prices=pd.DataFrame(prices), membership=membership,
                sectors={"A": "Tech", "B": "Tech"}, sessions=list(dates),
                asof=str(dates[-1].date()), known_at="2026-01-14T23:30:00Z",
                price_basis="unadjusted", policy=Policy(min_market_names=1, min_sector_names=1, percentile_min=3))


def test_dollar_weighted_and_short_exempt_not_added(inputs):
    r = build_index(**inputs)
    expected = 100 * (10 * 27 + 100 * 67) / (10 * 100.5 + 100 * 100.5)
    assert r["current"]["value"] == pytest.approx(expected, abs=5e-5)
    assert r["current"]["value"] != pytest.approx((27 + 67) / 2 / 100.5 * 100)
    assert r["trade_authority"] is False
    assert r["provider_parity_verified"] is False


def test_missing_current_never_relabels_prior_as_current(inputs):
    inputs["prices"] = inputs["prices"].iloc[:-2]
    r = build_index(**inputs)
    assert r["current"]["value"] is None
    assert r["current"]["state"] == "insufficient_coverage"
    assert r["last_complete"]["date"] < r["asof"]
    assert r["current"]["change_1d_pp"] is None
    assert r["attribution_5d"]["state"] == "unavailable"


def test_zero_short_is_valid_not_missing(inputs):
    inputs["panel"]["short_vol"] = 0
    inputs["panel"]["short_exempt"] = 0
    r = build_index(**inputs)
    assert r["current"]["value"] == 0
    assert r["current"]["state"] == "observed"
    assert r["current"]["change_5d_pp"] == 0
    assert r["current"]["percentile"] == 50


@pytest.mark.parametrize("field,value", [("short_vol", -1), ("short_vol", 101),
    ("short_vol", np.nan), ("short_exempt", 99), ("total_vol", 0), ("total_vol", np.inf)])
def test_invalid_share_records_cannot_enter_gauge(inputs, field, value):
    inputs["panel"].loc[inputs["panel"].index[-1], field] = value
    r = build_index(**inputs)
    assert r["current"]["value"] is None
    assert r["current"]["observed_names"] == 1


@pytest.mark.parametrize("basis", ["adjusted", "unknown", "total_return", ""])
def test_adjusted_or_unknown_price_basis_refused(inputs, basis):
    inputs["price_basis"] = basis
    with pytest.raises(ValueError, match="Raw contemporaneous"):
        build_index(**inputs)


def test_duplicate_prices_are_ambiguous_not_double_counted(inputs):
    inputs["prices"] = pd.concat([inputs["prices"], inputs["prices"].tail(1)])
    r = build_index(**inputs)
    assert r["current"]["value"] is None
    assert r["quality"]["prices"]["duplicate_rows"] == 2


def test_future_records_do_not_leak(inputs):
    reference = build_index(**inputs)
    future = inputs["panel"].tail(2).assign(date=pd.Timestamp("2030-01-01"), short_vol=100)
    inputs["panel"] = pd.concat([inputs["panel"], future])
    px = inputs["prices"].tail(2).assign(date=pd.Timestamp("2030-01-01"), close=10000)
    inputs["prices"] = pd.concat([inputs["prices"], px])
    candidate = build_index(**inputs)
    assert candidate["current"] == reference["current"]
    assert candidate["history"] == reference["history"]


def test_membership_honors_removal_and_addition_dates(inputs):
    m = inputs["membership"]
    m.loc[m.ticker == "B", "start_date"] = inputs["asof"]
    r = build_index(**inputs)
    assert r["history"][-2]["expected_names"] == 1
    assert r["history"][-1]["expected_names"] == 2
    assert r["history"][-2]["value"] == pytest.approx(26 / 100.5 * 100, abs=5e-5)


def test_gap_is_not_forward_filled_or_skipped_for_one_day_change(inputs):
    missing = inputs["sessions"][-2]
    inputs["panel"] = inputs["panel"][inputs["panel"].date != missing]
    r = build_index(**inputs)
    assert r["history"][-2]["value"] is None
    assert r["current"]["change_1d_pp"] is None
    assert r["current"]["mean_5d"] is None


def test_percentile_uses_only_prior_window(inputs):
    inputs["panel"].loc[inputs["panel"].date == inputs["sessions"][-1], "short_vol"] = 3
    r = build_index(**inputs)
    assert r["current"]["percentile"] == 0
    assert r["current"]["percentile_observations"] == 7


def test_insufficient_history_has_no_fake_percentile(inputs):
    inputs["policy"] = Policy(min_market_names=1, min_sector_names=1, percentile_min=60)
    assert build_index(**inputs)["current"]["percentile"] is None


def test_exact_attribution_separates_ratio_weights_and_coverage(inputs):
    p = pd.DataFrame({"ticker": ["A", "B", "EXIT"], "ratio": [.2, .6, .8], "dollars": [100, 200, 50]})
    c = pd.DataFrame({"ticker": ["A", "B", "ENTRY"], "ratio": [.4, .5, .3], "dollars": [150, 100, 90]})
    r = decompose(c, p)
    actual = 100 * ((c.ratio * c.dollars).sum() / c.dollars.sum() - (p.ratio * p.dollars).sum() / p.dollars.sum())
    assert r["total_pp"] == pytest.approx(actual, abs=1e-8)
    assert r["ratio_pp"] + r["weight_pp"] + r["coverage_mix_pp"] == pytest.approx(actual, abs=2e-8)
    assert r["common_names"] == 2
    assert r["coverage_mix_pp"] != 0


def test_share_class_aliases_are_explicit_not_case_folding():
    assert canonical_symbol("BRK/B") == "BRK-B"
    assert canonical_symbol("BRK.B") == "BRK-B"
    assert canonical_symbol("BCpC") == "BCpC"


def test_empty_inputs_abstain(inputs):
    inputs["panel"] = inputs["panel"].iloc[:0]
    r = build_index(**inputs)
    assert r["current"]["value"] is None
    assert r["last_complete"] is None
    assert all(row["value"] is None for row in r["history"])


def test_content_identity_is_deterministic_and_value_sensitive(inputs):
    first = build_index(**inputs)
    assert first["generation"] == build_index(**inputs)["generation"]
    other = copy.deepcopy(inputs)
    other["panel"].loc[other["panel"].index[-1], "short_vol"] -= 1
    assert first["generation"] != build_index(**other)["generation"]


def test_ratio_velocity_and_acceleration_have_declared_units(inputs):
    r = build_index(**inputs)
    values = [row['value'] for row in r['history']]
    assert r['current']['velocity_3d_pp_per_session'] == pytest.approx((values[-1]-values[-4])/3, abs=1e-4)
    assert r['current']['acceleration_3d_pp_per_session2'] == pytest.approx((values[-1]-2*values[-4]+values[-7])/9, abs=1e-4)
    assert r['current']['acceleration_3d_pp_per_session2'] == pytest.approx(0, abs=1e-4)


def test_ratio_acceleration_does_not_skip_unobserved_sessions(inputs):
    day = inputs['sessions'][-3]
    inputs['panel'] = inputs['panel'][inputs['panel'].date != day]
    r = build_index(**inputs)
    assert r['current']['velocity_3d_pp_per_session'] is None
    assert r['current']['acceleration_3d_pp_per_session2'] is None
