from __future__ import annotations

import copy
import math

import pytest

from lib.bonds_explanation_view import build_bonds_explanation_view


def _inputs():
    bond = {
        "as_of": "2026-10-02",
        "fed_path": {"implied_bp_12m": 83, "policy_rate": 3.88},
        "pillars": {
            "curve": {
                "ntfs": 1.03,
                "uninversion_alarm": False,
                "move_taxonomy": "bear_steepener",
            },
            "credit": {
                "hy_oas": 3.24,
                "ig_oas": 0.86,
                "distress_band": "normal",
                "direction": "widening",
            },
            "real_inflation": {
                "real_10y": 2.88,
                "breakeven_10y": 2.36,
                "term_premium": 1.0203,
                "tp_repriced_positive": True,
            },
            "stress": {
                "move": 107.29,
                "move_band": "normal",
                "move_pctile": 0.976,
                "sofr_iorb_bp": -3.0,
                "repo_stress": False,
                "reserve_scarcity": False,
            },
        },
    }
    transmission = {
        "asof": "2026-10-02",
        "state": {
            "rates": {
                "real_10y": 2.88,
                "real_10y_chg_22d_bp": 43.0,
                "real_10y_chg_63d_bp": 58.0,
                "direction": "rising",
                "regime": "restrictive",
            }
        },
        "yield_curve": {
            "regime": {
                "key": "bear_steepener",
                "slope_chg_bp": 2.0,
                "term_premium_dir": "rising",
                "term_premium_chg_bp": 27.0,
                "window_d": 21,
            },
            "momentum": {
                "real10y_speed_bp": 58.0,
                "nom10y_speed_bp": 69.0,
                "front2y_speed_bp": 59.0,
                "window_d": 63,
            },
            "slopes": {
                "2s10s": {"value": 0.45, "chg_63d_bp": 9.0, "inverted": False},
                "3m10y": {"value": 1.09, "chg_63d_bp": 40.0, "inverted": False},
            },
            "recession": {
                "ntfs": 1.03,
                "n_flags": 0,
                "risk": "low",
                "uninversion": False,
            },
        },
        "breakeven_decomp": {
            "as_of": "2026-10-02",
            "velocity_bp": {"chg_63d_bp": 11.0, "chg_20d_bp": 1.0},
            "direction": "flat",
            "trend": "uptrend",
            "cause_badge": {"cause": "quiet"},
        },
    }
    regime = {
        "asof": "2026-10-02",
        "conditions": {
            "systemic_stress": {
                "state": "calm",
                "trend": "rising",
                "ofr_fsi": -2.349,
                "functional": {"funding": -0.153},
            }
        },
    }
    return bond, transmission, regime


def _mechanism(view, key):
    return next(x for x in view["mechanisms"] if x["key"] == key)


def _statuses(row):
    return {
        "supports": {x["family"] for x in row["supports"]},
        "contradicts": {x["family"] for x in row["contradicts"]},
        "missing": {x["family"] for x in row["missing"]},
    }


def _walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def test_current_like_inputs_produce_five_named_mechanisms_without_score_or_probability():
    bond, transmission, regime = _inputs()
    frozen = copy.deepcopy((bond, transmission, regime))

    view = build_bonds_explanation_view(bond, transmission, regime)

    assert view["schema"] == "mastermind.bonds_explanation_view.v1"
    assert view["as_of"] == "2026-10-02"
    assert view["source_status"]["state"] == "aligned"
    assert [row["key"] for row in view["mechanisms"]] == [
        "policy_real_rate",
        "growth_cuts",
        "inflation_reflation",
        "term_premium_supply",
        "funding_liquidity",
    ]
    assert _mechanism(view, "policy_real_rate")["state"] == "supported"
    assert _mechanism(view, "growth_cuts")["state"] == "contradicted"
    assert _mechanism(view, "inflation_reflation")["state"] == "mixed"
    assert _mechanism(view, "term_premium_supply")["state"] == "supported"
    assert _mechanism(view, "funding_liquidity")["state"] == "contradicted"

    forbidden = {"score", "probability", "confidence", "confidence_pct", "probability_pct"}
    assert not forbidden.intersection(_walk_keys(view))
    assert (bond, transmission, regime) == frozen


def test_policy_row_uses_real_front_end_and_market_path_with_explicit_horizons():
    bond, transmission, regime = _inputs()
    row = _mechanism(build_bonds_explanation_view(bond, transmission, regime), "policy_real_rate")
    status = _statuses(row)

    assert {"real_rates", "front_end", "policy_path"} <= status["supports"]
    real = next(x for x in row["supports"] if x["family"] == "real_rates")
    assert real["value"] == 58.0
    assert real["unit"] == "bp"
    assert real["horizon"] == "63d"
    assert real["source_as_of"] == "2026-10-02"
    assert real["basis"] == "observed"
    path = next(x for x in row["supports"] if x["family"] == "policy_path")
    assert path["basis"] == "market_price"
    assert "forecast" in path["limit"]["en"].lower()


def test_growth_cut_row_preserves_credit_widening_but_does_not_override_low_recession_state():
    bond, transmission, regime = _inputs()
    row = _mechanism(build_bonds_explanation_view(bond, transmission, regime), "growth_cuts")
    status = _statuses(row)

    assert row["state"] == "contradicted"
    assert "credit" in status["supports"]
    assert {"recession", "front_end", "policy_path"} <= status["contradicts"]
    credit = next(x for x in row["supports"] if x["family"] == "credit")
    assert "normal" in credit["claim"]["en"].lower()
    assert "widen" in credit["claim"]["en"].lower()


def test_inflation_row_calls_contribution_mixed_when_breakevens_rise_but_real_rates_move_more():
    bond, transmission, regime = _inputs()
    row = _mechanism(build_bonds_explanation_view(bond, transmission, regime), "inflation_reflation")
    status = _statuses(row)

    assert row["state"] == "mixed"
    assert "breakevens" in status["supports"]
    assert "decomposition" in status["contradicts"]
    decomp = next(x for x in row["contradicts"] if x["family"] == "decomposition")
    assert decomp["observed"] == {"real_yield_bp": 58.0, "breakeven_bp": 11.0, "nominal_yield_bp": 69.0}
    assert "dominant" in decomp["claim"]["en"].lower()


def test_term_premium_support_is_model_evidence_and_supply_confirmation_remains_missing():
    bond, transmission, regime = _inputs()
    row = _mechanism(build_bonds_explanation_view(bond, transmission, regime), "term_premium_supply")
    status = _statuses(row)

    assert row["state"] == "supported"
    assert "term_premium_model" in status["supports"]
    assert {"second_term_premium_model", "supply_auction"} <= status["missing"]
    tp = next(x for x in row["supports"] if x["family"] == "term_premium_model")
    assert tp["basis"] == "model_estimate"
    assert tp["value"] == 27.0
    assert tp["horizon"] == "21d"
    assert "not observed fact" in tp["limit"]["en"].lower()


def test_funding_row_keeps_rates_vol_relative_elevation_inside_one_family_and_plumbing_calm():
    bond, transmission, regime = _inputs()
    row = _mechanism(build_bonds_explanation_view(bond, transmission, regime), "funding_liquidity")
    status = _statuses(row)

    assert row["state"] == "contradicted"
    assert {"rates_vol", "repo", "systemic_funding"} <= status["contradicts"]
    assert "market_depth_collateral" in status["missing"]
    rv = next(x for x in row["contradicts"] if x["family"] == "rates_vol")
    assert rv["observed"]["band"] == "normal"
    assert rv["observed"]["percentile"] == pytest.approx(0.976)
    assert "high percentile" in rv["claim"]["en"].lower()


def test_curve_horizons_compare_same_slope_only_and_name_other_slope_as_context():
    bond, transmission, regime = _inputs()
    view = build_bonds_explanation_view(bond, transmission, regime)
    hz = view["curve_horizons"]

    assert hz["state"] == "aligned"
    assert hz["current"] == {
        "slope": "2s10s",
        "horizon": "21d",
        "change_bp": 2.0,
        "direction": "steepening",
        "source_as_of": "2026-10-02",
    }
    assert hz["longer_same_slope"]["slope"] == "2s10s"
    assert hz["longer_same_slope"]["horizon"] == "63d"
    assert hz["longer_same_slope"]["change_bp"] == 9.0
    assert hz["context"][0]["slope"] == "3m10y"
    assert "recession" in hz["context"][0]["meaning"]["en"].lower()


def test_same_slope_opposite_sign_is_horizon_disagreement_not_collapsed_direction():
    bond, transmission, regime = _inputs()
    transmission["yield_curve"]["slopes"]["2s10s"]["chg_63d_bp"] = -14.0

    hz = build_bonds_explanation_view(bond, transmission, regime)["curve_horizons"]

    assert hz["state"] == "disagreement"
    assert hz["current"]["direction"] == "steepening"
    assert hz["longer_same_slope"]["direction"] == "flattening"
    assert "different windows" in hz["explanation"]["en"].lower()


def test_regime_date_mismatch_withholds_only_funding_join_not_unrelated_mechanisms():
    bond, transmission, regime = _inputs()
    regime["asof"] = "2026-10-01"

    view = build_bonds_explanation_view(bond, transmission, regime)

    assert view["source_status"]["state"] == "date_mismatch"
    assert view["source_status"]["dates"]["systemic_stress"] == "2026-10-01"
    assert _mechanism(view, "policy_real_rate")["state"] == "supported"
    assert _mechanism(view, "growth_cuts")["state"] == "contradicted"
    assert _mechanism(view, "inflation_reflation")["state"] == "mixed"
    assert _mechanism(view, "term_premium_supply")["state"] == "supported"
    funding = _mechanism(view, "funding_liquidity")
    assert funding["state"] == "withheld"
    systemic = next(x for x in funding["contradicts"] if x["family"] == "systemic_funding")
    assert systemic["source_as_of"] == "2026-10-01"
    assert funding["withheld_reason"]["en"]
    assert view["withheld_reason"] is None


def test_missing_inputs_become_missing_not_zero_neutral_or_false_confirmation():
    bond, transmission, regime = _inputs()
    transmission["yield_curve"]["momentum"]["real10y_speed_bp"] = None
    bond["fed_path"]["implied_bp_12m"] = None
    bond["pillars"]["stress"]["repo_stress"] = None
    regime["conditions"]["systemic_stress"]["state"] = None

    view = build_bonds_explanation_view(bond, transmission, regime)

    policy = _mechanism(view, "policy_real_rate")
    assert {"real_rates", "policy_path"} <= _statuses(policy)["missing"]
    assert policy["state"] == "insufficient"
    funding = _mechanism(view, "funding_liquidity")
    assert {"repo", "systemic_funding"} <= _statuses(funding)["missing"]
    for row in view["mechanisms"]:
        for item in row["supports"] + row["contradicts"] + row["missing"]:
            if item["status"] == "missing":
                assert item.get("value") is None


def test_boolean_and_nonfinite_numeric_inputs_are_missing_not_one_or_nan():
    bond, transmission, regime = _inputs()
    transmission["yield_curve"]["momentum"]["real10y_speed_bp"] = True
    transmission["yield_curve"]["momentum"]["front2y_speed_bp"] = math.nan
    bond["fed_path"]["implied_bp_12m"] = float("inf")

    row = _mechanism(build_bonds_explanation_view(bond, transmission, regime), "policy_real_rate")

    assert {"real_rates", "front_end", "policy_path"} <= _statuses(row)["missing"]
    assert row["state"] == "insufficient"


def test_funding_stress_can_be_supported_only_when_canonical_stress_owners_fire():
    bond, transmission, regime = _inputs()
    bond["pillars"]["stress"].update({
        "move_band": "elevated",
        "repo_stress": True,
        "reserve_scarcity": True,
        "sofr_iorb_bp": 18.0,
    })
    regime["conditions"]["systemic_stress"].update({"state": "stress", "trend": "rising"})

    row = _mechanism(build_bonds_explanation_view(bond, transmission, regime), "funding_liquidity")

    assert row["state"] == "supported"
    assert {"rates_vol", "repo", "systemic_funding"} <= _statuses(row)["supports"]


def test_growth_break_can_be_supported_without_turning_it_into_a_probability():
    bond, transmission, regime = _inputs()
    transmission["yield_curve"]["recession"].update({"risk": "high", "n_flags": 3, "ntfs": -0.45})
    transmission["yield_curve"]["momentum"]["front2y_speed_bp"] = -70.0
    bond["fed_path"]["implied_bp_12m"] = -100
    bond["pillars"]["credit"].update({"distress_band": "elevated", "direction": "widening"})

    row = _mechanism(build_bonds_explanation_view(bond, transmission, regime), "growth_cuts")

    assert row["state"] == "supported"
    assert {"recession", "front_end", "policy_path", "credit"} <= _statuses(row)["supports"]
    assert "probability" not in set(_walk_keys(row))


def test_curve_horizon_missing_is_insufficient_not_flat():
    bond, transmission, regime = _inputs()
    transmission["yield_curve"]["regime"]["slope_chg_bp"] = None

    hz = build_bonds_explanation_view(bond, transmission, regime)["curve_horizons"]

    assert hz["state"] == "insufficient"
    assert hz["current"]["direction"] is None


def test_populated_breakeven_family_without_its_own_date_withholds_only_inflation_join():
    bond, transmission, regime = _inputs()
    transmission["breakeven_decomp"]["as_of"] = None

    view = build_bonds_explanation_view(bond, transmission, regime)

    assert view["source_status"]["state"] == "insufficient"
    assert "breakevens" in view["source_status"]["missing_dates"]
    inflation = _mechanism(view, "inflation_reflation")
    assert inflation["state"] == "withheld"
    be = next(x for x in inflation["supports"] if x["family"] == "breakevens")
    assert be["source_as_of"] is None
    assert inflation["withheld_reason"]["en"]
    assert _mechanism(view, "policy_real_rate")["state"] == "supported"
    assert _mechanism(view, "growth_cuts")["state"] == "contradicted"
    assert _mechanism(view, "term_premium_supply")["state"] == "supported"
    assert _mechanism(view, "funding_liquidity")["state"] == "contradicted"
    assert view["withheld_reason"] is None


def test_populated_systemic_family_without_regime_date_withholds_only_funding_join():
    bond, transmission, regime = _inputs()
    regime["asof"] = None

    view = build_bonds_explanation_view(bond, transmission, regime)

    assert view["source_status"]["state"] == "insufficient"
    assert "systemic_stress" in view["source_status"]["missing_dates"]
    funding = _mechanism(view, "funding_liquidity")
    assert funding["state"] == "withheld"
    systemic = next(x for x in funding["contradicts"] if x["family"] == "systemic_funding")
    assert systemic["source_as_of"] is None
    assert funding["withheld_reason"]["en"]
    assert _mechanism(view, "policy_real_rate")["state"] == "supported"
    assert _mechanism(view, "growth_cuts")["state"] == "contradicted"
    assert _mechanism(view, "inflation_reflation")["state"] == "mixed"
    assert _mechanism(view, "term_premium_supply")["state"] == "supported"
    assert view["withheld_reason"] is None


def test_absent_optional_family_is_missing_evidence_not_a_global_date_failure():
    bond, transmission, regime = _inputs()
    transmission["breakeven_decomp"] = {}
    regime["conditions"]["systemic_stress"] = {}

    view = build_bonds_explanation_view(bond, transmission, regime)

    assert view["source_status"]["state"] == "aligned"
    assert view["source_status"]["missing_dates"] == []
    assert _mechanism(view, "inflation_reflation")["state"] == "insufficient"
    assert "systemic_funding" in _statuses(_mechanism(view, "funding_liquidity"))["missing"]


def test_mismatched_breakeven_date_withholds_cross_source_decomposition_claim():
    bond, transmission, regime = _inputs()
    transmission["breakeven_decomp"]["as_of"] = "2026-10-01"

    view = build_bonds_explanation_view(bond, transmission, regime)
    row = _mechanism(view, "inflation_reflation")
    status = _statuses(row)

    assert view["source_status"]["state"] == "date_mismatch"
    assert row["state"] == "withheld"
    assert row["withheld_reason"]["en"]
    assert "decomposition" in status["missing"]
    assert "decomposition" not in status["supports"]
    assert "decomposition" not in status["contradicts"]
    item = next(x for x in row["missing"] if x["family"] == "decomposition")
    assert "dates" in item["claim"]["en"].lower()


def test_mismatched_bond_and_transmission_dates_withhold_term_premium_level_change_join():
    bond, transmission, regime = _inputs()
    bond["as_of"] = "2026-10-01"

    view = build_bonds_explanation_view(bond, transmission, regime)
    row = _mechanism(view, "term_premium_supply")
    status = _statuses(row)

    assert view["source_status"]["state"] == "date_mismatch"
    assert row["state"] == "withheld"
    assert row["withheld_reason"]["en"]
    assert "term_premium_model" in status["missing"]
    assert "term_premium_model" not in status["supports"]
    item = next(x for x in row["missing"] if x["family"] == "term_premium_model")
    assert "dates" in item["claim"]["en"].lower()


def test_breakeven_date_mismatch_withholds_only_inflation_join():
    bond, transmission, regime = _inputs()
    transmission["breakeven_decomp"]["as_of"] = "2026-10-01"

    view = build_bonds_explanation_view(bond, transmission, regime)

    assert view["source_status"]["state"] == "date_mismatch"
    assert _mechanism(view, "inflation_reflation")["state"] == "withheld"
    assert _mechanism(view, "policy_real_rate")["state"] == "supported"
    assert _mechanism(view, "growth_cuts")["state"] == "contradicted"
    assert _mechanism(view, "term_premium_supply")["state"] == "supported"
    assert _mechanism(view, "funding_liquidity")["state"] == "contradicted"


def test_curve_horizon_explanation_names_actual_current_window():
    bond, transmission, regime = _inputs()
    transmission["yield_curve"]["regime"]["window_d"] = 10

    hz = build_bonds_explanation_view(bond, transmission, regime)["curve_horizons"]

    assert hz["current"]["horizon"] == "10d"
    assert "10-day and 63-day" in hz["explanation"]["en"]
    assert "21-day" not in hz["explanation"]["en"]


@pytest.mark.parametrize(
    ("family", "mutate", "affected", "unaffected"),
    [
        (
            "bond_health",
            lambda b, t, r: b.__setitem__("as_of", "2026-02-30"),
            {"policy_real_rate", "growth_cuts", "term_premium_supply", "funding_liquidity"},
            {"inflation_reflation"},
        ),
        (
            "transmission",
            lambda b, t, r: t.__setitem__("asof", "2026-02-30"),
            {"policy_real_rate", "growth_cuts", "inflation_reflation", "term_premium_supply"},
            {"funding_liquidity"},
        ),
        (
            "breakevens",
            lambda b, t, r: t["breakeven_decomp"].__setitem__("as_of", "2026-02-30"),
            {"inflation_reflation"},
            {"policy_real_rate", "growth_cuts", "term_premium_supply", "funding_liquidity"},
        ),
        (
            "systemic_stress",
            lambda b, t, r: r.__setitem__("asof", "2026-02-30"),
            {"funding_liquidity"},
            {"policy_real_rate", "growth_cuts", "inflation_reflation", "term_premium_supply"},
        ),
    ],
)
def test_impossible_calendar_dates_fail_closed_only_for_consuming_mechanisms(
    family, mutate, affected, unaffected
):
    bond, transmission, regime = _inputs()
    mutate(bond, transmission, regime)

    view = build_bonds_explanation_view(bond, transmission, regime)
    states = {row["key"]: row["state"] for row in view["mechanisms"]}

    assert view["source_status"]["state"] == "insufficient"
    assert family in view["source_status"]["missing_dates"]
    assert all(states[key] == "withheld" for key in affected)
    assert all(states[key] != "withheld" for key in unaffected)
