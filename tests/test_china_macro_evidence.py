"""Zero-network tests for the display-only China macro evidence contract."""
from datetime import date
import json

import numpy as np
import pandas as pd
import pytest

from engine.china_macro_evidence import (
    SCHEMA, Snapshot, build_snapshot, finite, monthly, percentile,
    rolling_sum, true_credit_impulse,
)

AS_OF = date(2026, 9, 29)


def frame(values, dates=None):
    n = len(next(iter(values.values())))
    return pd.DataFrame(values, index=pd.to_datetime(dates) if dates is not None else pd.bdate_range(end="2026-09-28", periods=n))


def build(data):
    return build_snapshot(lambda group, name: data.get(f"{group}/{name}"), AS_OF)


def metric(result, ident):
    return next(m for panel in result["panels"].values() for m in panel["metrics"] if m["id"] == ident)


def tsf(n=36):
    idx = pd.date_range(end="2026-08-01", freq="MS", periods=n)
    return pd.DataFrame({"tsf_total": np.arange(n) + 1000., "govt_bonds": np.ones(n) * 500,
                         "availability_date": idx + pd.offsets.MonthBegin(1) + pd.Timedelta(days=15)}, index=idx)


@pytest.mark.parametrize("value", [None, True, False, float("nan"), float("inf"), float("-inf"), "bad"])
def test_non_numeric_is_not_a_value(value):
    assert finite(value) is None


def test_zero_is_a_real_value():
    assert finite(0) == 0
    r = build({"china_connect/southbound": frame({"net": [0.] * 25})})
    m = metric(r, "southbound_20")
    assert m["value"] == 0 and m["status"] == "recent"
    assert metric(r, "southbound_buy_days")["value"] == 0


def test_empty_sources_render_explicit_unavailable_and_json_finite():
    r = build({})
    assert r["schema"] == SCHEMA
    assert set(r["panels"]) == {"policy", "property", "flows", "sentiment"}
    assert all(p["recent"] == 0 for p in r["panels"].values())
    assert r["authority"] == "display_only" and r["replay_eligible"] is False
    assert r["publication_time_verified"] is False
    json.dumps(r, allow_nan=False)


def test_one_source_failure_does_not_erase_healthy_panel():
    def reader(group, name):
        if group == "china_credit":
            raise ValueError("broken parquet schema")
        return frame({"net": [1000.] * 22}) if (group, name) == ("china_connect", "southbound") else None
    r = build_snapshot(reader, AS_OF)
    assert "china_credit/tsf" in r["source_errors"]
    assert metric(r, "southbound_20")["value"] == 20.


def test_duplicate_source_dates_are_rejected_not_arbitrarily_deduplicated():
    r = build({"china_connect/southbound": frame({"net": [1000., 99999.]}, ["2026-09-28"] * 2)})
    assert metric(r, "southbound_1")["value"] is None
    assert "duplicate" in r["source_errors"]["china_connect/southbound"]


def test_future_reference_values_cannot_leak_into_snapshot():
    r = build({"china_connect/southbound": frame({"net": [1000., 99000.]}, ["2026-09-28", "2026-10-01"])})
    assert metric(r, "southbound_1")["value"] == 1.
    assert metric(r, "southbound_1")["reference_date"] == "2026-09-28"


def test_modelled_tsf_availability_is_not_observed_release_time():
    d = tsf()
    d.loc[d.index[-1], "availability_date"] = "2026-10-16"
    r = build({"china_credit/tsf": d})
    m = metric(r, "tsf_month")
    assert m["reference_date"] == "2026-07-01"
    assert m["source"]["publication_time"] is None
    assert m["source"]["revision_vintage"] is None


def test_monthly_growth_is_the_correct_trailing_flow_growth_not_gdp_impulse():
    d = tsf()
    r = build({"china_credit/tsf": d})
    expected = (d.tsf_total.iloc[-12:].sum() / d.tsf_total.iloc[-24:-12].sum() - 1) * 100
    m = metric(r, "financing_growth")
    assert m["value"] == round(expected, 1)
    assert "NOT GDP-normalized" in m["method_en"]
    assert all("credit_impulse" != k for k in r)


def test_missing_month_is_not_a_twelve_row_year():
    d = tsf().drop(tsf().index[-6])
    r = build({"china_credit/tsf": d})
    assert metric(r, "financing_growth")["value"] is None
    assert metric(r, "tsf_12m")["value"] is None
    assert metric(r, "tsf_month")["value"] is not None


def test_duplicate_calendar_month_is_not_silently_chosen():
    s = pd.Series([1., 2.], index=pd.to_datetime(["2026-01-01", "2026-01-20"]))
    assert monthly(s).empty


def test_short_rolling_window_is_unavailable_not_partial_sum():
    r = build({"china_connect/southbound": frame({"net": [1000.] * 19})})
    assert metric(r, "southbound_20")["value"] is None
    assert metric(r, "southbound_5")["value"] == 5.
    assert metric(r, "southbound_buy_days")["value"] is None


def test_null_latest_window_does_not_borrow_old_result():
    d = frame({"net": [1000.] * 25 + [np.nan]})
    r = build({"china_connect/southbound": d})
    assert metric(r, "southbound_1")["value"] is None
    assert metric(r, "southbound_20")["value"] is None
    assert metric(r, "southbound_20")["status"] == "unavailable"
    assert metric(r, "southbound_20")["chart"]["vals"][-1] is None


def test_aggregate_flow_conversion_matches_headline_chart_and_api():
    d = frame({"net": [1000.] * 19 + [-6553.87]})
    r = build({"china_connect/southbound": d})
    m = metric(r, "southbound_1")
    assert m["value"] == -6.55 and m["unit"] == "CNY bn"
    assert m["chart"]["vals"][-1] == pytest.approx(-6.55387)
    n = metric(r, "southbound_20")
    assert n["value"] == 12.45
    assert round(n["chart"]["vals"][-1], 2) == n["value"]
    assert "latest session; 20-session buying" in r["panels"]["flows"]["headline_en"]


def test_buy_frequency_is_not_a_streak():
    r = build({"china_connect/southbound": frame({"net": [1000., -1000.] * 10})})
    assert metric(r, "southbound_buy_days")["value"] == 10
    assert "NOT a consecutive" in metric(r, "southbound_buy_days")["method_en"]


def test_financing_currency_conversion_and_full_window():
    r = build({"china_margin/balance": frame({"net_fin_buy": [-24.6] * 20})})
    assert metric(r, "margin_net20")["value"] == -49.2
    assert metric(r, "margin_net20")["unit"] == "CNY bn"


def test_no_divide_by_zero_turnover_or_government_share():
    r = build({"china_margin/daily_trade": frame({"margin_trade_amt": [100.], "trade_amt_ratio": [0.]}),
               "china_credit/tsf": frame({"tsf_total": [0.], "govt_bonds": [100.]}, ["2026-08-01"])})
    assert metric(r, "turnover")["value"] is None
    assert metric(r, "government_share")["value"] is None
    json.dumps(r, allow_nan=False)


def test_government_and_negative_tsf_components_are_kept_without_zero_imputation():
    d = tsf()
    d.loc[d.index[-1], "trust"] = -233.
    r = build({"china_credit/tsf": d})
    mix = {x["id"]: x["value"] for x in r["tsf_mix"]}
    assert mix["govt_bonds"] == 50 and mix["trust"] == -23.3
    assert mix["rmb_loans"] is None and mix["other_residual"] is None


def test_tsf_mix_reconciles_only_when_all_components_known():
    d = tsf()
    for c in ["rmb_loans", "fx_loans", "corp_bonds", "entrust", "trust", "accept_bills", "equity"]:
        d[c] = 10.
    r = build({"china_credit/tsf": d})
    assert sum(x["value"] for x in r["tsf_mix"]) == pytest.approx(d.tsf_total.iloc[-1] / 10)


def test_m1_definition_break_not_spliced():
    r = build({"china_macro/money_supply": frame({"m1_yoy": [1., 2., 4.1], "m2_yoy": [2., 4., 7.5]}, ["2024-12-01", "2025-01-01", "2026-08-01"])})
    m = metric(r, "money_spread")
    assert m["chart"]["dates"][0] == "2025-01-01"
    assert m["value"] == -3.4
    assert "Pre-2025 history is excluded" in m["method_en"]


def test_aged_climate_cannot_count_as_recent_recovery_evidence():
    r = build({"china_property/climate": frame({"climate": [91.45]}, ["2025-12-01"])})
    m = metric(r, "climate")
    assert m["value"] == 91.45 and m["status"] == "stale"
    assert m["reference_date"] == "2025-12-01" and m["age_days"] > 250


def test_rrr_is_bank_cohort_historical_reference_not_current_policy_assertion():
    r = build({"china_macro/rrr": frame({"rrr_big": [9.], "rrr_change": [-.5]}, ["2025-05-07"])})
    m = metric(r, "rrr_record")
    assert m["status"] == "reference"
    assert m["reference_date"] == "2025-05-07"
    assert "weighted-average" in m["method_en"]


def test_home_denominator_exact_and_partial_coverage_explicit():
    base = {"new_rising": [15.], "new_falling": [49.], "new_flat": [6.], "cities": [70.]}
    r = build({"china_property/home_price": frame(base, ["2026-08-01"])})
    assert metric(r, "home_falling")["value"] == 70.0
    assert metric(r, "home_net")["value"] == -34
    base.update(new_rising=[10.], new_falling=[24.], cities=[40.])
    r = build({"china_property/home_price": frame(base, ["2026-08-01"])})
    assert metric(r, "home_falling")["value"] == 60.
    assert metric(r, "home_falling")["status"] == "partial"
    assert "incomplete or aged" in r["panels"]["property"]["headline_en"]


@pytest.mark.parametrize("counts", [(15, 49, 5, 70), (-5, 69, 6, 70), (15.5, 48.5, 6, 70), (15, 49, 6, 0)])
def test_incoherent_city_counts_are_not_national_statistics(counts):
    d = {k: [v] for k, v in zip(["new_rising", "new_falling", "new_flat", "cities"], counts)}
    r = build({"china_property/home_price": frame(d, ["2026-08-01"])})
    assert metric(r, "home_falling")["value"] is None
    assert metric(r, "home_net")["value"] is None


def test_construction_headline_and_chart_are_same_measure():
    rb = frame({"close": np.arange(70) + 100.})
    io = frame({"close": np.arange(70) + 200.})
    r = build({"china_property/rebar": rb, "china_property/iron_ore": io})
    m = metric(r, "construction_return")
    expect = (((169 / 106 - 1) + (269 / 206 - 1)) / 2) * 100
    assert m["value"] == round(expect, 1)
    assert m["chart"]["vals"][-1] == pytest.approx(expect)
    assert m["unit"] == "%" and "not measured construction demand" in m["method_en"]


def test_construction_requires_both_legs():
    r = build({"china_property/rebar": frame({"close": np.arange(70) + 100.})})
    assert metric(r, "construction_return")["value"] is None


def test_curve_same_session_and_basis_points():
    r = build({"china_property/cgb": frame({"cgb_10y": [1.679], "cgb_2y": [1.2716]})})
    m = metric(r, "curve_slope")
    assert m["value"] == 40.7 and m["unit"] == "bp"
    r = build({"china_property/cgb": frame({"cgb_10y": [1.679, np.nan], "cgb_2y": [np.nan, 1.2716]})})
    assert metric(r, "curve_slope")["value"] is None


def test_unverified_property_price_break_withholds_return_not_fake_adjustment():
    r = build({"china/512200.SS": frame({"close": [1., 1.05, 2.8, 1., 2.7]})})
    m = metric(r, "property_drawdown")
    assert m["value"] is None and m["chart"]["vals"] == []
    assert m["status"] == "quality_hold" and len(m["discontinuities"]) == 3


def test_verified_coherent_history_uses_available_peak_not_all_time_claim():
    r = build({"china/512200.SS": frame({"close": [1., 1.1, 1.0]})})
    m = metric(r, "property_drawdown")
    assert m["value"] == -9.1
    assert "not a proven all-time high" in m["method_en"]


def test_holdings_currency_uncertainty_not_laundered_into_cny_or_hkd():
    r = build({"china_connect/southbound": frame({"net": [1000.], "hold_mktcap": [119180.]})})
    m = metric(r, "southbound_holdings")
    assert m["value"] is None and m["status"] == "quality_hold"
    assert m["unverified_source_value"] == 11.92


def test_percentile_short_history_is_not_zero_percentile():
    assert percentile(pd.Series([1., 2., 3.]))["value"] is None
    d = frame({"fin_pct_float": np.arange(100)})
    m = metric(build({"china_margin/balance": d}), "margin_ratio")
    assert m["percentile"]["value"] == 100. and m["percentile"]["n"] == 100
    assert m["percentile"]["window"] == 252


def test_sentiment_different_sessions_never_become_one_headline_confirmation():
    r = build({"china_margin/balance": frame({"fin_pct_float": [2.68]}),
               "china_margin/daily_trade": frame({"margin_trade_amt": [100.], "trade_amt_ratio": [8.]}),
               "china_flows/limit_breadth": frame({"zt": [33.], "dt": [56.]}, ["2026-09-25"])})
    assert "Different observation dates" in r["panels"]["sentiment"]["headline_en"]


def test_true_impulse_requires_nominal_gdp_four_quarters_and_calendar_alignment():
    months = pd.date_range("2023-01-01", "2025-12-01", freq="MS")
    flows = pd.Series(100., index=months)
    quarters = pd.date_range("2023-03-31", "2025-12-31", freq="QE")
    gdp = pd.Series(10000., index=quarters)
    result = true_credit_impulse(flows, gdp)
    assert result.iloc[-1] == 0.
    assert true_credit_impulse(pd.Series(dtype=float), pd.Series(dtype=float)).empty


def test_read_is_cached_and_original_frame_unchanged():
    d = tsf()
    before = d.copy(deep=True)
    calls = []
    ctx = Snapshot(lambda g, n: calls.append((g, n)) or d, AS_OF)
    ctx.frame("china_credit", "tsf")
    ctx.frame("china_credit", "tsf")
    assert len(calls) == 1
    pd.testing.assert_frame_equal(d, before)
