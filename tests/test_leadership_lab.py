"""Leadership Lab contracts. Missing APIs fail explicitly before implementation."""
from __future__ import annotations

from copy import deepcopy
from importlib import import_module, util
import math

import pytest


def api(module, name):
    path = f"engine.leadership_lab.{module}"
    assert util.find_spec(path) is not None, f"{path} is not implemented"
    result = getattr(import_module(path), name, None)
    assert callable(result), f"{path}.{name} is not implemented"
    return result


SESSIONS = ["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25",
            "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]


def prices():
    return ({d: 100 + 10 * i for i, d in enumerate(SESSIONS)},
            {d: 100 + i for i, d in enumerate(SESSIONS)})


def window(stock=None, benchmark=None, **kw):
    s, b = prices()
    return api("measurement", "benchmark_window")(
        s if stock is None else stock, b if benchmark is None else benchmark,
        sessions=SESSIONS, through=SESSIONS[-1], lookback=kw.pop("lookback", 4), **kw)


def test_window_endpoints_are_lookback_minus_skip_not_extra_formation():
    result = window(skip=1)
    assert result["start_session"] == SESSIONS[5]
    assert result["end_session"] == SESSIONS[8]
    assert result["formation_sessions"] == 3
    assert result["relative_wealth_return"] == pytest.approx((180 / 150) / (108 / 105) - 1)
    assert result["stock_return"] == pytest.approx(.2)


def test_returns_compound_instead_of_sum_simple_returns():
    dates = SESSIONS[:3]
    result = api("measurement", "benchmark_window")(
        dict(zip(dates, [100, 150, 100])), dict.fromkeys(dates, 100),
        sessions=dates, through=dates[-1], lookback=2)
    assert result["stock_return"] == 0
    assert result["relative_wealth_return"] == 0


def test_future_rows_cannot_change_window():
    s, b = prices()
    before = window(s, b)
    s["2026-10-05"] = 90000
    b["2026-10-05"] = 1
    assert window(s, b) == before


@pytest.mark.parametrize("missing", [SESSIONS[5], SESSIONS[7], SESSIONS[-1]])
def test_missing_any_required_stock_session_is_not_forward_filled(missing):
    s, b = prices()
    del s[missing]
    result = window(s, b, skip=1)
    assert result["status"] == "UNAVAILABLE"
    assert result["relative_wealth_return"] is None
    assert "MISSING_STOCK_SESSION" in result["reasons"]


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), 0, -1, True])
def test_invalid_benchmark_price_never_becomes_flat_or_positive_return(bad):
    s, b = prices()
    b[SESSIONS[7]] = bad
    assert window(s, b)["status"] == "UNAVAILABLE"


def test_short_history_keeps_named_horizon_unavailable():
    result = window(lookback=252, skip=21)
    assert result["relative_wealth_return"] is None
    assert "INSUFFICIENT_HISTORY" in result["reasons"]


@pytest.mark.parametrize("sessions", [SESSIONS[::-1], SESSIONS + [SESSIONS[-1]], ["bad"]])
def test_invalid_calendar_rejected(sessions):
    s, b = prices()
    with pytest.raises(ValueError):
        api("measurement", "benchmark_window")(s, b, sessions=sessions,
                                                through=SESSIONS[-1], lookback=4)


@pytest.mark.parametrize("lookback,skip", [(0, 0), (4, 4), (4, -1), (True, 0)])
def test_invalid_window_parameters_rejected(lookback, skip):
    with pytest.raises(ValueError):
        window(lookback=lookback, skip=skip)


def test_rs_ties_are_average_ranks_and_not_probabilities():
    result = api("measurement", "percentile_ranks")(
        {"A": 1, "B": 1, "C": 2, "D": 3}, eligible=["A", "B", "C", "D"], min_observed=2)
    assert result["ranks"]["A"] == result["ranks"]["B"] == pytest.approx(1 + 98 / 6)
    assert result["ranks"]["D"] == 99
    assert result["forecast_probability"] is None
    assert result["eligible_count"] == 4


def test_universe_denominator_does_not_drop_missing_observations():
    result = api("measurement", "percentile_ranks")(
        {"A": 1, "B": 2}, eligible=["A", "B", "C"], min_observed=2)
    assert result["coverage"] == pytest.approx(2 / 3)
    assert result["status"] == "UNAVAILABLE"
    assert result["ranks"] == {"A": None, "B": None, "C": None}


@pytest.mark.parametrize("values", [{"A": 1, "B": 1}, {"A": 1}])
def test_constant_or_thin_population_not_given_flattering_percentiles(values):
    result = api("measurement", "percentile_ranks")(values, eligible=list(values), min_observed=2)
    assert result["status"] == "UNAVAILABLE"
    assert all(v is None for v in result["ranks"].values())


def point(price=100, eps=5, **updates):
    result = dict(price=price, eps=eps, forecast_period="FY2027", currency="USD",
                  accounting_basis="adjusted_diluted", share_basis="split-basis-2026-01",
                  known_at="2026-09-01T21:00:00Z", observed_at="2026-09-01T21:01:00Z",
                  source_ref="owner:example:immutable-1")
    result.update(updates)
    return result


def bridge(start=None, end=None):
    return api("measurement", "earnings_multiple_bridge")(
        point() if start is None else start,
        point(price=150, eps=6, known_at="2026-10-02T21:00:00Z",
              observed_at="2026-10-02T21:01:00Z", source_ref="owner:example:immutable-2") if end is None else end,
        cutoff="2026-10-03T00:00:00Z")


def test_earnings_multiple_bridge_preserves_interaction_and_log_identity():
    result = bridge()
    assert result["status"] == "ILLUSTRATIVE_CALCULATION"
    assert result["price_return"] == pytest.approx(.5)
    assert result["eps_change"] == pytest.approx(.2)
    assert result["multiple_change"] == pytest.approx(.25)
    assert result["interaction"] == pytest.approx(.05)
    assert result["eps_log_contribution"] + result["multiple_log_contribution"] == pytest.approx(math.log(1.5))
    assert result["forecast_probability"] is None
    assert result["causal_claim"] is False


@pytest.mark.parametrize("field,value", [("eps", 0), ("eps", -1), ("eps", float("nan")),
                                         ("price", -1), ("price", True), ("source_ref", "")])
def test_invalid_or_unsupported_valuation_inputs_abstain(field, value):
    result = bridge(end=point(**{field: value}))
    assert result["status"] == "UNAVAILABLE"
    assert result["price_return"] is None


@pytest.mark.parametrize("field,value", [("forecast_period", "NTM-rolling-other"),
                                         ("currency", "CAD"), ("accounting_basis", "GAAP"),
                                         ("share_basis", "post-split")])
def test_incompatible_basis_cannot_manufacture_rerating(field, value):
    assert bridge(end=point(**{field: value}))["status"] == "UNAVAILABLE"


@pytest.mark.parametrize("field,value", [("known_at", "2026-10-04T00:00:00Z"),
                                         ("observed_at", "2026-10-04T00:00:00Z"),
                                         ("known_at", "2026-09-01"),
                                         ("observed_at", "2026-09-01T20:00:00Z")])
def test_future_naive_or_reversed_evidence_clocks_abstain(field, value):
    assert bridge(end=point(**{field: value}))["status"] == "UNAVAILABLE"


def inputs():
    alpha = {"as_of": "2026-10-02", "per_ticker": {
        "A": {"alpha": 2., "rs": 90., "rs3m": 91., "rs6m": 85., "rs12m": 80., "entry": "extended"},
        "B": {"alpha": 1., "rs": 95.}, "C": {"alpha": None, "rs": None}}, "buy": True}
    factors = {"as_of": "2026-10-02", "table": [
        {"ticker": "A", "name": "Alpha", "sector": "Technology", "quality": 1., "value": 2.},
        {"ticker": "B", "name": "Beta", "sector": "Technology", "quality": 2., "value": 1.}]}
    baskets = {"as_of": "2026-10-02", "baskets": [
        {"id": "theme-1", "name": "Theme One", "members": [{"symbol": "A"}, {"symbol": "B"}, {"symbol": "MISSING"}]}]}
    return alpha, factors, baskets


def recover(alpha=None, factors=None, baskets=None, **kw):
    a, f, b = inputs()
    return api("recovery", "recover_snapshot")(
        a if alpha is None else alpha, f if factors is None else factors,
        b if baskets is None else baskets, source_ref="a" * 40,
        reference_session=kw.pop("reference_session", "2026-10-02"), **kw)


def test_recovery_preserves_full_population_and_changes_no_inputs():
    a, f, b = inputs()
    before = deepcopy((a, f, b))
    result = recover(a, f, b, limit=1)
    assert (a, f, b) == before
    assert result["recovered_count"] == 3
    assert len(result["rows"]) == 3
    assert len(result["shortlist"]) == 1
    assert result["shortlist"][0]["ticker"] == "A"
    assert result["pit_qualification"] == "UNATTESTED_ROW_CLOCKS"


def test_sort_is_descriptive_and_does_not_rewrite_candidate_population():
    result = recover(sort_by="legacy_rs")
    assert result["shortlist"][0]["ticker"] == "B"
    assert {r["ticker"] for r in result["rows"]} == {"A", "B", "C"}
    assert all(v is False for v in result["authority"].values())
    assert result["forecast_probability"] is None


def test_untrusted_upstream_permissions_and_probabilities_not_projected():
    a, f, b = inputs()
    a["per_ticker"]["A"].update(buy=True, probability=.99, rank_authority=True)
    result = recover(a, f, b)
    assert "buy" not in result["rows"][0]
    assert "probability" not in result["rows"][0]
    assert result["forecast_probability"] is None


def test_group_missing_members_remain_in_denominator_and_not_independent_support():
    group = recover()["groups"][0]
    assert group["member_count"] == 3
    assert group["observed_count"] == 2
    assert group["coverage"] == pytest.approx(2 / 3)
    assert group["independence_status"] == "NOT_QUALIFIED"
    assert group["historical_membership_qualified"] is False


def test_mixed_date_enrichment_is_excluded_not_claimed_current():
    a, f, b = inputs()
    f["as_of"] = "2026-10-01"
    b["as_of"] = "2026-10-03"
    result = recover(a, f, b)
    assert result["groups"] == []
    assert all(r["legacy_top_score"] is None for r in result["rows"])
    assert "FACTORS_DATE_MISMATCH" in result["gaps"]
    assert "BASKETS_DATE_MISMATCH" in result["gaps"]


def test_stale_source_remains_stale_after_rebuild():
    result = recover(reference_session="2026-10-05")
    assert result["status"] == "STALE_RECOVERED_SNAPSHOT"
    assert result["source_session"] == "2026-10-02"


def test_future_source_cannot_populate_recovery():
    result = recover(reference_session="2026-10-01")
    assert result["status"] == "UNAVAILABLE"
    assert result["rows"] == []
    assert "FUTURE_ALPHA_SOURCE" in result["gaps"]


def test_nonfinite_legacy_values_are_null_not_json_nan():
    a, f, b = inputs()
    a["per_ticker"]["A"]["alpha"] = float("nan")
    result = recover(a, f, b)
    import json
    json.dumps(result, allow_nan=False)
    assert next(r for r in result["rows"] if r["ticker"] == "A")["legacy_alpha"] is None


def test_unresolved_group_members_cannot_disappear_from_coverage_denominator():
    a, f, b = inputs()
    b["baskets"][0]["members"].append({"name": "Unresolved member"})
    group = recover(a, f, b)["groups"][0]
    assert group["member_count"] == 4
    assert group["unknown_member_count"] == 1
    assert group["coverage"] == pytest.approx(.5)


def test_same_rolling_ntm_label_does_not_establish_constant_forecast_period():
    result = bridge(start=point(forecast_period="NTM"), end=point(price=150, eps=6, forecast_period="NTM"))
    assert result["status"] == "UNAVAILABLE"
    assert result["price_return"] is None
