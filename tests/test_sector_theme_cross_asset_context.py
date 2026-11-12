"""P4a research-only date/rights/source context tests; no market data I/O."""
from copy import deepcopy
from datetime import datetime, timezone
from math import inf, nan

import pytest

from engine.sector_theme_owner_bridge import preview_us_theme_packet
from engine.sector_theme_cross_asset_context import compose_sector_theme_cross_asset_context
from tests.test_sector_theme_owner_bridge import fixture


def preview():
    return preview_us_theme_packet(fixture())


def context():
    return {
        "market_concentration": {
            "owner": "engine.cross_asset.snapshot",
            "source_revision": "fixture-concentration-v1",
            "available_at": "2026-10-29T20:01:00+00:00",
            "snapshot": {
                "asof": "2026-10-29", "verdict": "concentrated",
                "markets": ["US", "China", "Dollar"],
                "window_d": 63, "absorption_ratio": .65,
            },
        },
        "credit_window": {
            "owner": "engine.credit_window.window_state",
            "source_revision": "fixture-credit-v1",
            "available_at": "2026-10-29T19:59:00+00:00",
            "snapshot": {
                "SCORED": False, "research_only": True, "as_of": "2026-10-28",
                "segments": [
                    {"key": "hy", "state": "neutral", "n_inputs": 3,
                     "low_confidence": False, "inputs": [
                         {"key": "spread_range", "state": "open", "as_of": "2026-10-28"},
                         {"key": "spread_drift", "state": "neutral", "as_of": "2026-10-27"},
                         {"key": "rates_vol", "state": "shut", "as_of": "2026-10-28"},
                     ]},
                    {"key": "ig", "state": "not_evaluable", "n_inputs": 1,
                     "low_confidence": True, "inputs": [
                         {"key": "spread_range", "state": "unknown", "as_of": None},
                         {"key": "spread_drift", "state": "unknown", "as_of": None},
                         {"key": "rates_vol", "state": "neutral", "as_of": "2026-10-28"},
                     ]},
                ],
            },
        },
        "bond_transmission": {
            "owner": "engine.bond_cross_asset.snapshot",
            "source_revision": "fixture-bond-v1",
            "available_at": "2026-10-29T19:57:00+00:00",
            "snapshot": {
                "as_of": "2026-10-28",
                "interpretation_scope": "contemporaneous_association_not_lead_or_causal_effect",
                "assets": [{"key": "spx", "driver_key": "hy_oas",
                            "beta": -.7, "corr": -.42, "n": 156}],
            },
        },
    }


def held(c, reason, p=None):
    result = compose_sector_theme_cross_asset_context(p if p is not None else preview(), c)
    assert result["status"] == "HELD"
    assert result["reason"] == reason
    assert result["contexts"] == {}
    assert result["customer_publication"] is False
    assert result["ranking_authority"] is False
    assert result["predictive_authority"] is False
    assert result["alert_or_trading_authority"] is False


def test_p4a_01_valid_owner_reports_are_coarse_research_only():
    c = context()
    before = deepcopy(c)
    p = preview()
    result = compose_sector_theme_cross_asset_context(p, c)
    assert c == before
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert result["group_id"] == "AI_INDUSTRIAL_INFRA"
    assert result["same_clock_market_join_proven"] is False
    assert result["independent_hedge_relationship_proven"] is False
    assert result["source_rights_and_vintage_qualification"] == "unverified"
    assert result["alert_or_trading_authority"] is False
    assert result["contexts"]["market_concentration"]["absorption_ratio"] == .65
    assert result["contexts"]["credit_window"]["calendar_lag_days"] == 1
    assert result["contexts"]["credit_window"]["credit_segments"][0]["input_as_of"]["spread_drift"]["as_of"] == "2026-10-27"
    assert result["contexts"]["bond_transmission"]["associations"]["spx"]["overlap_weekly_n"] == 156
    assert all(x["intraday_confirmation"] is False for x in result["contexts"].values())
    assert all(x["original_availability_authenticated"] is False for x in result["contexts"].values())


def test_p4a_02_no_owner_contexts_keeps_all_explicit_unmeasured():
    result = compose_sector_theme_cross_asset_context(preview(), {})
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert set(result["contexts"]) == {"market_concentration", "credit_window", "bond_transmission"}
    assert all(v["status"] == "UNMEASURED" for v in result["contexts"].values())


def test_p4a_03_unrecognized_owner_or_extra_data_never_goes_unlabelled():
    c = context()
    c["new_correlator"] = {"owner": "unknown"}
    held(c, "unknown_or_malformed_owner_context")


def test_p4a_04_unknown_or_forged_p2_packet_fails_before_lookups():
    for obj in (None, {}, "owner", []):
        result = compose_sector_theme_cross_asset_context(obj, context())
        assert result["status"] == "HELD"
        assert result["reason"] == "unqualified_sector_theme_preview"
    p = preview()
    p["eligible_for_historical_prediction"] = True
    held(context(), "unqualified_sector_theme_preview", p)
    p = preview()
    p["trading_or_alert_authority"] = True
    held(context(), "unqualified_sector_theme_preview", p)


def test_p4a_05_price_frame_and_decision_time_must_match():
    for k in ("period_end", "decision_at"):
        p = preview()
        p["comparison_basis"][k] = "2026-10-31T00:00:00+00:00"
        held(context(), "incompatible_sector_theme_clock", p)
    p = preview()
    p["frame"]["clock"]["period_end"] = "0001-01-01T00:00:00+14:00"
    held(context(), "incompatible_sector_theme_clock", p)


def test_p4a_06_date_resolution_is_not_same_clock_intraday_confirmation():
    r = compose_sector_theme_cross_asset_context(preview(), context())
    assert all(x["intraday_confirmation"] is False for x in r["contexts"].values())
    assert all(x["source_authenticity_verified"] is False for x in r["contexts"].values())
    assert r["contexts"]["credit_window"]["interpretation"].endswith("not_intraday_signal")


@pytest.mark.parametrize("kind", ("market_concentration", "credit_window", "bond_transmission"))
def test_p4a_07_future_source_asof_rejected(kind):
    c = context()
    dayfield = "asof" if kind == "market_concentration" else "as_of"
    c[kind]["snapshot"][dayfield] = "2026-10-30"
    held(c, "incompatible_"+kind+"_observation_clock")


@pytest.mark.parametrize("kind", ("market_concentration", "credit_window", "bond_transmission"))
def test_p4a_08_future_available_at_rejected(kind):
    c = context()
    c[kind]["available_at"] = "2026-10-29T20:05:01+00:00"
    held(c, "incompatible_"+kind+"_observation_clock")


@pytest.mark.parametrize("clock", (
    "2026-10-29T20:00:00", "0001-01-01T00:00:00+14:00",
    "9999-12-31T23:59:59-14:00", "2026-10-29",
))
def test_p4a_09_bad_or_overflow_known_at_is_held(clock):
    c = context()
    c["credit_window"]["available_at"] = clock
    held(c, "incompatible_credit_window_observation_clock")


@pytest.mark.parametrize("kind", ("market_concentration", "credit_window", "bond_transmission"))
def test_p4a_10_owner_identity_or_revision_must_be_exact(kind):
    c = context()
    c[kind]["owner"] = "engine.new_source"
    held(c, "unbound_"+kind+"_owner")
    c = context()
    c[kind]["source_revision"] = None
    held(c, "unbound_"+kind+"_owner")


def test_p4a_11_market_absorption_requires_real_fraction_not_bool_or_fake_sample():
    for v in (None, True, False, -0.5, 1.1, inf, nan, {}, "0.4"):
        c = context()
        c["market_concentration"]["snapshot"]["absorption_ratio"] = v
        held(c, "invalid_market_concentration_owner_fields")
    for markets in (["US", "US", "Dollar"], [[], {}, "Dollar"], ["US"]):
        c = context()
        c["market_concentration"]["snapshot"]["markets"] = markets
        held(c, "invalid_market_concentration_owner_fields")


def test_p4a_12_owner_unknown_concentration_is_unmeasured_not_zero():
    c = context()
    c["market_concentration"]["snapshot"]["verdict"] = "unknown"
    c["market_concentration"]["snapshot"].pop("absorption_ratio")
    r = compose_sector_theme_cross_asset_context(preview(), c)
    assert r["status"] == "RESEARCH_PREVIEW_ONLY"
    assert r["contexts"]["market_concentration"]["status"] == "UNMEASURED"


def test_p4a_13_credit_authority_marker_must_remain_false():
    for field, value in (("SCORED", True), ("research_only", False)):
        c = context()
        c["credit_window"]["snapshot"][field] = value
        held(c, "invalid_credit_window_owner_fields")


def test_p4a_14_credit_input_vintages_cannot_be_postdated():
    c = context()
    c["credit_window"]["snapshot"]["segments"][0]["inputs"][1]["as_of"] = "2026-10-29"
    held(c, "invalid_credit_window_owner_fields")


def test_p4a_15_credit_n_observed_and_confidence_must_agree():
    for field, value in (("n_inputs", 2), ("low_confidence", True)):
        c = context()
        c["credit_window"]["snapshot"]["segments"][0][field] = value
        held(c, "invalid_credit_window_owner_fields")


def test_p4a_16_credit_unknown_inputs_not_treated_as_informative():
    r = compose_sector_theme_cross_asset_context(preview(), context())
    ig = r["contexts"]["credit_window"]["credit_segments"][1]
    assert ig["observed_inputs_n"] == 1
    assert ig["owner_state"] == "not_evaluable"
    assert ig["input_as_of"]["spread_range"]["as_of"] is None


def test_p4a_17_bond_sample_not_an_independent_hedge_or_forward_claim():
    r = compose_sector_theme_cross_asset_context(preview(), context())
    a = r["contexts"]["bond_transmission"]["associations"]["spx"]
    assert a["relationship_stability"] == "unmeasured_not_a_conditional_hedge"
    assert r["independent_hedge_relationship_proven"] is False
    assert a["contemporaneous_corr"] == -.42


def test_p4a_18_bond_invalid_corr_or_sample_is_held_not_silent():
    for k,v in (("n",0),("n",103),("n",True),("beta",inf),("beta",{}),
                ("corr",nan),("corr",1.1),("corr",True)):
        c = context()
        c["bond_transmission"]["snapshot"]["assets"][0][k] = v
        held(c, "invalid_bond_transmission_owner_fields")


def test_p4a_19_bond_absent_assets_is_unmeasured_not_observed_zero():
    c = context()
    c["bond_transmission"]["snapshot"]["assets"] = []
    r = compose_sector_theme_cross_asset_context(preview(), c)
    assert r["contexts"]["bond_transmission"]["status"] == "UNMEASURED"


def test_p4a_20_dont_copy_any_caller_data_by_reference():
    c = context()
    r = compose_sector_theme_cross_asset_context(preview(), c)
    assert r["status"] == "RESEARCH_PREVIEW_ONLY"
    expected = r["contexts"]["credit_window"]["credit_segments"][0]["input_as_of"]["spread_range"]["owner_state"]
    c["credit_window"]["snapshot"]["segments"][0]["inputs"][0]["state"] = "shut"
    assert r["contexts"]["credit_window"]["credit_segments"][0]["input_as_of"]["spread_range"]["owner_state"] == expected


def test_p4a_21_bond_correlation_owner_not_arbitrary_model_text():
    c = context()
    c["bond_transmission"]["snapshot"]["interpretation_scope"] = "proven_hedge_lead_indicator"
    held(c, "invalid_bond_transmission_owner_fields")


def test_p4a_22_rights_or_vintage_exaggeration_in_source_preview_is_held():
    p = preview()
    p["eligible_for_customer_publication"] = True
    held(context(), "unqualified_sector_theme_preview", p)


def test_p4a_23_bad_nested_credit_inputs_never_raise():
    for payload in (None, {}, [None], [{"key": {}}, None], [{"key": ["hy"]}]):
        c = context()
        c["credit_window"]["snapshot"]["segments"] = payload
        held(c, "invalid_credit_window_owner_fields")


def test_p4a_24_nonexistent_snapshot_does_not_hide_other_owner_read():
    c = context()
    del c["market_concentration"]
    r = compose_sector_theme_cross_asset_context(preview(), c)
    assert r["status"] == "RESEARCH_PREVIEW_ONLY"
    assert r["contexts"]["market_concentration"]["status"] == "UNMEASURED"
    assert r["contexts"]["credit_window"]["status"] == "OWNER_REPORTED_RESEARCH_CONTEXT"
    assert r["contexts"]["bond_transmission"]["status"] == "OWNER_REPORTED_RESEARCH_CONTEXT"



def test_p4a_25_frame_or_fingerprint_authority_tamper_is_held():
    for path, value in (
        (("frame", "authority", "ranking_authority"), True),
        (("frame", "evidence", "source_rights_verified"), True),
        (("frame", "evidence", "original_known_at_receipts_verified"), True),
        (("frame", "group", "group_id"), "forged"),
        (("frame", "group", "membership_mode"), "CURRENT_ROSTER"),
        (("fingerprint", "group", "group_id"), "forged"),
    ):
        p = preview()
        obj = p
        for k in path[:-1]:
            obj = obj[k]
        obj[path[-1]] = value
        held(context(), "missing_sector_theme_basis", p)


def test_p4a_26_wrong_frame_horizon_rejected():
    p = preview()
    p["frame"]["clock"]["horizon"] = "1m"
    held(context(), "incompatible_sector_theme_clock", p)
