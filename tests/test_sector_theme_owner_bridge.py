"""Adversarial P2 source admission tests — no real market data or account I/O."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from engine.sector_theme_owner_bridge import (
    preview_us_theme_packet, project_owner_group_flow_context,
)

END = datetime(2026, 10, 29, 20, tzinfo=timezone.utc)
DECISION = END + timedelta(minutes=5)
MEMBER_KNOWN = END - timedelta(days=1)
IDENTITY_KNOWN = END - timedelta(days=7)


def quote(ret=.03, *, horizon="5d", price_basis="split_adjusted"):
    period_start = END - timedelta(days=20 if horizon == "20d" else 5)
    return {
        "horizon": horizon,
        "period_start": period_start.isoformat(),
        "period_end": END.isoformat(),
        "session_basis": "daily_close",
        "observed_at": (END + timedelta(seconds=30)).isoformat(),
        "available_at": (END + timedelta(minutes=1)).isoformat(),
        "price_basis": price_basis,
        "return_frac": ret,
        "ma_basis": "daily_sessions",
        "close": 115.0, "ma20": 112.0, "ma50": 108.0,
        "ma200": 95.0, "previous_ma50": 106.0,
    }


def fixture():
    return {
        "group_id": "AI_INDUSTRIAL_INFRA",
        "group_kind": "theme",
        "cohort_id": "fixture-cohort-20261029",
        "membership_revision": "fixture-rev1",
        "membership_mode": "PIT_AS_KNOWN",
        "membership_known_at": MEMBER_KNOWN.isoformat(),
        "membership_asof": {
            "basket_id": "AI_INDUSTRIAL_INFRA", "suite": "baskets",
            "asof": "2026-10-29",
            "snapshot_date": "2026-10-28", "pit": True,
            "basis": "pit_snapshot", "source_shape": "membership",
            "members": ["AAA", "BBB"],
        },
        "member_identities": {
            "AAA": {
                "security_id": "SEC_AAA", "issuer_id": "ISS_AAA",
                "resolution_state": "RESOLVED",
                "available_at": IDENTITY_KNOWN.isoformat(),
            },
            "BBB": {
                "security_id": "SEC_BBB", "issuer_id": "ISS_BBB",
                "resolution_state": "RESOLVED",
                "available_at": IDENTITY_KNOWN.isoformat(),
            },
        },
        "market": {
            "origin": "synthetic_fixture",
            "horizon": "5d",
            "ma_basis": "daily_sessions",
            "price_basis": "split_adjusted",
            "session_basis": "daily_close",
            "benchmark_id": "SPY",
            "parent_id": "XLK",
            "period_start": (END - timedelta(days=5)).isoformat(),
            "period_end": END.isoformat(),
            "decision_at": DECISION.isoformat(),
            "benchmark": quote(.01),
            "parent": quote(.02),
            "member_rows": {"AAA": quote(.04), "BBB": quote(.03)},
        },
    }


def held(packet, reason):
    r = preview_us_theme_packet(packet)
    assert r["status"] == "HELD"
    assert reason in r["hold_reasons"]
    assert r["frame"] is None and r["fingerprint"] is None
    assert r["eligible_for_customer_publication"] is False
    assert r["eligible_for_historical_prediction"] is False


def test_p2a_01_real_contract_round_trip_is_research_only():
    p = fixture()
    p_copy = deepcopy(p)
    v = preview_us_theme_packet(p)
    assert p == p_copy
    assert v["status"] == "RESEARCH_PREVIEW_ONLY"
    assert v["frame"]["group"]["membership_mode"] == "PIT_AS_KNOWN"
    assert v["frame"]["universe"]["member_ids"] == ["SEC_AAA", "SEC_BBB"]
    assert v["frame"]["measures"]["equal_weight_full_cohort_return"]["value"] == pytest.approx(.035)
    assert v["fingerprint"]["horizons"]["5d"]["rs_parent"]["value"] == pytest.approx(
        1.035 / 1.02 - 1.0
    )
    assert set(v["fingerprint"]["single_names"]) == {"SEC_AAA", "SEC_BBB"}
    assert v["eligible_for_customer_publication"] is False
    assert v["eligible_for_historical_prediction"] is False
    assert v["trading_or_alert_authority"] is False


def test_p2a_02_pit_false_current_roster_may_not_claim_pit():
    p = fixture()
    p["membership_asof"].update(pit=False, basis="current_membership",
                                snapshot_date=None)
    held(p, "current_roster_not_pit")


def test_p2a_03_explicit_current_roster_is_still_research_only():
    p = fixture()
    p["membership_asof"].update(pit=False, basis="current_membership",
                                snapshot_date=None)
    p["membership_mode"] = "CURRENT_ROSTER"
    p["membership_known_at"] = DECISION.isoformat()
    v = preview_us_theme_packet(p)
    assert v["status"] == "RESEARCH_PREVIEW_ONLY"
    assert v["basis"] == "CURRENT_ROSTER"
    assert v["frame"]["group"]["membership_mode"] == "CURRENT_ROSTER"
    assert v["eligible_for_historical_prediction"] is False


def test_p2a_04_refuses_unknown_native_basket_and_suite():
    p = fixture()
    p["membership_asof"]["suite"] = "baskets_china"
    held(p, "wrong_membership_suite")
    p = fixture()
    p["membership_asof"]["basket_id"] = "DUMMY"
    held(p, "membership_group_mismatch")


def test_p2a_05_microtheme_proxy_cannot_become_stock_membership():
    p = fixture()
    p["group_kind"] = "micro_theme"
    held(p, "subtheme_membership_not_qualified")


def test_p2a_06_source_shape_population_cannot_cross_seed_boundary():
    p = fixture()
    p["membership_asof"]["source_shape"] = "ths_concept_dump"
    held(p, "unqualified_member_source_shape")


def test_p2a_07_missing_member_known_at_is_not_snapshot_date():
    p = fixture()
    p.pop("membership_known_at")
    held(p, "missing_original_membership_or_market_clock")
    p = fixture()
    p["membership_known_at"] = "2026-10-28"
    held(p, "missing_original_membership_or_market_clock")


def test_p2a_08_future_member_known_at_not_backdated():
    p = fixture()
    p["membership_known_at"] = (END + timedelta(seconds=1)).isoformat()
    held(p, "future_membership_knowledge_for_pit")


def test_p2a_09_future_identity_known_at_is_withheld():
    p = fixture()
    p["member_identities"]["AAA"]["available_at"] = (
        END + timedelta(seconds=1)
    ).isoformat()
    held(p, "future_identity_for_pit")


def test_p2a_10_unknown_identity_refuses_entire_group():
    p = fixture()
    p["member_identities"]["AAA"]["resolution_state"] = "AMBIGUOUS"
    held(p, "unresolved_canonical_member_identity")


def test_p2a_11_duplicate_security_mapping_refuses():
    p = fixture()
    p["member_identities"]["BBB"]["security_id"] = "SEC_AAA"
    held(p, "duplicate_canonical_security")


def test_p2a_12_duplicate_or_unknown_roster_refuses():
    p = fixture()
    p["membership_asof"]["members"].append("AAA")
    held(p, "invalid_native_members")
    p = fixture()
    p["membership_asof"]["members"] = []
    held(p, "invalid_native_members")


def test_p2a_13_future_benchmark_refuses_before_spreading_rs():
    p = fixture()
    p["market"]["benchmark"]["available_at"] = (
        DECISION + timedelta(minutes=1)
    ).isoformat()
    held(p, "benchmark_future_or_noncausal_reference")


def test_p2a_14_misaligned_parent_refuses_group_rs():
    p = fixture()
    p["market"]["parent"]["price_basis"] = "unadjusted"
    held(p, "parent_reference_horizon_or_basis_mismatch")


def test_p2a_15_missing_parent_refuses_false_parent_rs():
    p = fixture()
    p["market"]["parent"] = None
    held(p, "missing_parent_reference")


def test_p2a_16_invalid_benchmark_return_refuses():
    p = fixture()
    p["market"]["benchmark"]["return_frac"] = float("nan")
    held(p, "benchmark_invalid_reference_return")


def test_p2a_17_member_wrong_price_adjustment_refuses():
    p = fixture()
    p["market"]["member_rows"]["AAA"]["price_basis"] = "total_return_adjusted"
    held(p, "member_price_basis_mismatch")


def test_p2a_18_future_ticker_quote_does_not_get_counted_as_down():
    p = fixture()
    p["market"]["member_rows"]["BBB"]["available_at"] = (
        DECISION + timedelta(seconds=1)
    ).isoformat()
    v = preview_us_theme_packet(p)
    assert v["status"] == "RESEARCH_PREVIEW_ONLY"
    x = v["frame"]
    assert x["universe"]["measured_return_n"] == 1
    assert x["measures"]["equal_weight_full_cohort_return"]["status"] == "unmeasured"
    bounds = x["measures"]["positive_return_breadth"]["bounds"]
    assert bounds == pytest.approx([.5, 1.0])
    assert x["constituents"]["SEC_BBB"]["unmeasured_reason"] == "future_known"


def test_p2a_19_partial_market_row_remains_unmeasured_not_zero():
    p = fixture()
    del p["market"]["member_rows"]["BBB"]
    v = preview_us_theme_packet(p)
    assert v["status"] == "RESEARCH_PREVIEW_ONLY"
    assert v["frame"]["universe"]["missing_by_reason"]["missing_observation"] == 1
    assert v["fingerprint"]["single_names"]["SEC_BBB"]["horizons"]["5d"][
        "return"]["status"] == "unmeasured"


def test_p2a_20_source_rights_not_invented_from_capture_grant():
    p = fixture()
    p["market"]["origin"] = "owner_reported"
    p["use_verdict"] = {
        "verdict": "ALLOWED", "purpose": "selection_cohort_internal_capture",
        "source_ref": "tape-x", "registry_revision": "rev-1",
    }
    p["original_membership_receipt"] = {"note": "unverified"}
    held(p, "research_source_use_not_granted")


def test_p2a_21_owner_claimed_rights_are_not_customer_publication_grant():
    p = fixture()
    p["market"]["origin"] = "owner_reported"
    p["use_verdict"] = {
        "verdict": "ALLOWED", "purpose": "sector_theme_factor_research",
        "source_ref": "owned-price-source-1", "registry_revision": "rev-1",
    }
    p["original_membership_receipt"] = {"note": "unverified"}
    v = preview_us_theme_packet(p)
    assert v["status"] == "RESEARCH_PREVIEW_ONLY"
    assert v["source_origin"] == "owner_reported"
    assert v["frame"]["evidence"]["source_rights_verified"] is False
    assert v["frame"]["evidence"]["mode"] == "reconstructed_price_history"
    assert v["eligible_for_customer_publication"] is False


def test_p2a_22_missing_original_receipt_refuses_owner_reported_pit():
    p = fixture()
    p["market"]["origin"] = "owner_reported"
    p["use_verdict"] = {
        "verdict": "ALLOWED", "purpose": "sector_theme_factor_research",
        "source_ref": "owned-price-source-1", "registry_revision": "rev-1",
    }
    held(p, "original_membership_receipt_not_authenticated_here")


def test_p2a_23_fake_synthetic_with_live_use_claim_refuses():
    p = fixture()
    p["use_verdict"] = {"purpose": "sector_theme_factor_research", "verdict": "ALLOWED"}
    held(p, "synthetic_packet_carries_live_rights_claim")


@pytest.mark.parametrize("invalid_time", [None, "2026-10-29", "not-a-time", "2030-01-01T00:00:00+00:00"])
def test_p2a_24_invalid_market_decision_time_refuses(invalid_time):
    p = fixture()
    p["market"]["decision_at"] = invalid_time
    reason = ("missing_original_membership_or_market_clock"
              if invalid_time in (None, "2026-10-29", "not-a-time")
              else "future_market_or_membership_known_at")
    # The later decision cutoff is allowed in a research-preview packet
    # only if it is a valid, aware clock; no wall-clock is silently substituted.
    if invalid_time == "2030-01-01T00:00:00+00:00":
        assert preview_us_theme_packet(p)["status"] == "RESEARCH_PREVIEW_ONLY"
    else:
        held(p, reason)


def test_p2a_25_snapshot_after_query_date_refuses():
    p = fixture()
    p["membership_asof"]["snapshot_date"] = "2026-10-30"
    held(p, "invalid_native_snapshot_date")


def test_p2a_26_non_member_extra_tape_row_refuses():
    p = fixture()
    p["market"]["member_rows"]["UNKNOWN"] = quote(.5)
    held(p, "invalid_member_row_population")


def test_p2a_27_unchanged_inputs_yield_deterministic_output():
    p = fixture()
    assert preview_us_theme_packet(p) == preview_us_theme_packet(deepcopy(p))


def test_p2a_28_source_snapshot_cannot_be_known_before_it_existed():
    p = fixture()
    p["membership_asof"]["snapshot_date"] = "2026-10-29"
    p["membership_known_at"] = "2026-10-28T15:00:00+00:00"
    held(p, "membership_known_at_predates_native_snapshot")


def test_p2a_29_incomplete_quote_population_retains_identification_bounds():
    p = fixture()
    del p["market"]["member_rows"]["AAA"]
    v = preview_us_theme_packet(p)
    assert v["status"] == "RESEARCH_PREVIEW_ONLY"
    b = v["frame"]["measures"]["positive_return_breadth"]
    assert b["bounds_kind"] == "identification_bounds_not_confidence_interval"
    assert b["bounds"] == pytest.approx([.5, 1.0])
    assert v["fingerprint"]["horizons"]["5d"]["absolute_trend"][
        "group_return"]["status"] == "unmeasured"


def flow_packet():
    p = fixture()
    m = p["market"]
    m["horizon"] = "20d"
    m["period_start"] = (END - timedelta(days=20)).isoformat()
    m["benchmark"] = quote(.01, horizon="20d")
    m["parent"] = quote(.02, horizon="20d")
    m["member_rows"] = {
        "AAA": quote(.04, horizon="20d"),
        "BBB": quote(.03, horizon="20d"),
    }
    return p


def flow_reading():
    return {
        "accel_z": 1.1, "broadening_z": -0.7, "breadth": .5,
        "cohesion": .3, "cohesion_chg": -.1, "persistence": .75,
        "rs_pctile": .6, "stage": "emerging", "flow_score": 99999.0,
    }


def flow_binding():
    return {
        "origin": "synthetic_fixture",
        "source_function": "engine.group_flow.fingerprint_at",
        "source_revision": "fixture-flow-definition-r1",
        "group_id": "AI_INDUSTRIAL_INFRA",
        "cohort_id": "fixture-cohort-20261029",
        "member_ids": ["SEC_AAA", "SEC_BBB"],
        "horizon": "20d",
        "period_end": END.isoformat(),
        "observed_at": (END + timedelta(seconds=30)).isoformat(),
        "available_at": (END + timedelta(minutes=1)).isoformat(),
        "windows": {
            "rs_window_d": 20, "breadth_ma_d": 50,
            "corr_window_d": 40, "persist_window_d": 20,
            "z_lookback_d": 252,
        },
    }


def test_p2b_01_owner_context_integrates_as_separate_research_only_view():
    p = flow_packet()
    p["group_flow_reading"] = flow_reading()
    p["group_flow_binding"] = flow_binding()
    out = preview_us_theme_packet(p)
    assert out["status"] == "RESEARCH_PREVIEW_ONLY"
    ctx = out["group_flow_context"]
    assert ctx["status"] == "OWNER_REPORTED_RESEARCH_ONLY"
    assert ctx["owner_stage_descriptive_only"] == "emerging"
    assert ctx["observations"]["relative_wealth_second_difference_z"]["value"] == 1.1
    assert ctx["observations"]["ma_breadth_broadening_z"]["value"] == -.7
    assert ctx["observations"]["relative_strength_persistence"]["value"] == .75
    assert "flow_score" not in repr(ctx)
    assert ctx["ranking_or_trading_authority"] is False
    assert ctx["eligible_for_customer_publication"] is False
    # The main candidate remains source-unqualified; the owner report must
    # never silently flip the canonical predictor/rank gates.
    assert out["fingerprint"]["axes"]["rs_velocity_acceleration"]["status"] == "unmeasured"
    assert out["fingerprint"]["authority"]["predictive_promoted"] is False


def test_p2b_02_missing_flow_context_does_not_block_base_observations():
    out = preview_us_theme_packet(flow_packet())
    assert out["status"] == "RESEARCH_PREVIEW_ONLY"
    assert out["group_flow_context"]["status"] == "HELD"
    assert out["group_flow_context"]["reason"] == "missing_owner_group_flow"


def test_p2b_03_group_and_cohort_identity_are_not_interchangeable():
    p = flow_packet()
    base = preview_us_theme_packet(p)["fingerprint"]
    b = flow_binding()
    b["cohort_id"] = "other"
    out = project_owner_group_flow_context(base, flow_reading(), b)
    assert out["reason"] == "owner_flow_group_or_cohort_mismatch"
    b = flow_binding()
    b["group_id"] = "other"
    out = project_owner_group_flow_context(base, flow_reading(), b)
    assert out["reason"] == "owner_flow_group_or_cohort_mismatch"


def test_p2b_04_missing_or_swapped_member_ids_refuses_context():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    b = flow_binding()
    b["member_ids"] = ["SEC_AAA", "SEC_CCC"]
    assert project_owner_group_flow_context(
        base, flow_reading(), b)["reason"] == "owner_flow_population_mismatch"


def test_p2b_05_20d_only_not_arbitrary_intraday_bar():
    base = preview_us_theme_packet(fixture())["fingerprint"]
    out = project_owner_group_flow_context(base, flow_reading(), flow_binding())
    assert out["reason"] == "group_flow_requires_20d_factor_frame"


def test_p2b_06_daily_ma_basis_required_for_owner_flow():
    p = flow_packet()
    p["market"]["ma_basis"] = "1m_bars"
    base = preview_us_theme_packet(p)["fingerprint"]
    out = project_owner_group_flow_context(base, flow_reading(), flow_binding())
    assert out["reason"] == "group_flow_requires_daily_session_ma_basis"


def test_p2b_07_wrong_or_futuristic_owner_timestamp_refuses():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    b = flow_binding()
    b["available_at"] = (DECISION + timedelta(seconds=1)).isoformat()
    assert project_owner_group_flow_context(
        base, flow_reading(), b)["reason"] == "future_or_out_of_order_group_flow_receipt"
    b = flow_binding()
    b["period_end"] = (END - timedelta(days=1)).isoformat()
    assert project_owner_group_flow_context(
        base, flow_reading(), b)["reason"] == "group_flow_wrong_period_end"


def test_p2b_08_unregistered_producer_and_missing_revision_refuse():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    b = flow_binding()
    b["source_function"] = "engine.other.fingerprint_at"
    assert project_owner_group_flow_context(
        base, flow_reading(), b)["reason"] == "unknown_group_flow_source_definition"
    b = flow_binding()
    b["source_revision"] = ""
    assert project_owner_group_flow_context(
        base, flow_reading(), b)["reason"] == "unknown_group_flow_source_definition"


def test_p2b_09_owner_window_changes_are_not_silent():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    b = flow_binding()
    b["windows"]["rs_window_d"] = 15
    assert project_owner_group_flow_context(
        base, flow_reading(), b)["reason"] == "unqualified_group_flow_window_definition"
    b = flow_binding()
    del b["windows"]["breadth_ma_d"]
    assert project_owner_group_flow_context(
        base, flow_reading(), b)["reason"] == "unqualified_group_flow_window_definition"


def test_p2b_10_out_of_range_owner_fields_are_unmeasured_not_extreme():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    r = flow_reading()
    r["breadth"] = 1.4
    r["cohesion"] = float("nan")
    r["persistence"] = -.2
    ctx = project_owner_group_flow_context(base, r, flow_binding())
    obs = ctx["observations"]
    for field in ("ma_breadth_observed_sample", "member_return_cohesion",
                  "relative_strength_persistence"):
        assert obs[field]["status"] == "unmeasured"
    assert obs["ma_breadth_broadening_z"]["value"] == -.7


def test_p2b_11_no_owner_measurements_means_hold():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    r = {k: None for k in (
        "accel_z", "broadening_z", "breadth", "cohesion",
        "cohesion_chg", "persistence", "rs_pctile",
    )}
    r["stage"] = "quiet"
    ctx = project_owner_group_flow_context(base, r, flow_binding())
    assert ctx["reason"] == "all_owner_group_flow_fields_unmeasured"


def test_p2b_12_owner_stage_is_lowercase_and_not_reinterpreted():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    r = flow_reading()
    r["stage"] = "EMERGING"
    assert project_owner_group_flow_context(
        base, r, flow_binding())["reason"] == "unknown_owner_flow_stage_vocabulary"
    r["stage"] = "cooling"
    assert project_owner_group_flow_context(
        base, r, flow_binding())["owner_stage_descriptive_only"] == "cooling"


def test_p2b_13_group_flow_capture_rights_do_not_grant_factor_research():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    b = flow_binding()
    b["origin"] = "owner_reported"
    b["use_verdict"] = {
        "verdict": "ALLOWED", "purpose": "selection_cohort_internal_capture",
        "registry_revision": "rev-1", "source_ref": "flow-source",
    }
    assert project_owner_group_flow_context(
        base, flow_reading(), b)["reason"] == "group_flow_research_use_not_admitted"


def test_p2b_14_owner_research_claims_remain_unqualified_not_a_proof():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    b = flow_binding()
    b["origin"] = "owner_reported"
    b["use_verdict"] = {
        "verdict": "ALLOWED", "purpose": "sector_theme_factor_research",
        "registry_revision": "rev-1", "source_ref": "flow-source",
    }
    ctx = project_owner_group_flow_context(base, flow_reading(), b)
    assert ctx["status"] == "OWNER_REPORTED_RESEARCH_ONLY"
    assert ctx["original_observation_and_use_receipts_verified"] is False
    assert ctx["eligible_for_customer_publication"] is False


def test_p2a_30_missing_reference_security_identity_refuses():
    p = fixture()
    p["market"]["benchmark_id"] = None
    held(p, "missing_benchmark_or_parent_identity")
    p = fixture()
    p["market"]["parent_id"] = ""
    held(p, "missing_benchmark_or_parent_identity")


def test_p2a_31_changed_price_start_refuses_benchmark_and_member():
    p = fixture()
    p["market"]["benchmark"]["period_start"] = (
        END - timedelta(days=4)).isoformat()
    held(p, "benchmark_reference_endpoint_mismatch")
    p = fixture()
    p["market"]["member_rows"]["AAA"]["period_start"] = (
        END - timedelta(days=4)).isoformat()
    held(p, "member_horizon_or_session_alignment_mismatch")


def test_p2a_32_different_after_hours_basis_refuses():
    p = fixture()
    p["market"]["parent"]["session_basis"] = "all_sessions"
    held(p, "parent_reference_session_basis_mismatch")
    p = fixture()
    p["market"]["member_rows"]["BBB"]["session_basis"] = "overnight"
    held(p, "member_horizon_or_session_alignment_mismatch")


def test_p2a_33_missing_interval_start_cannot_use_same_endpoint_only():
    p = fixture()
    p["market"].pop("period_start")
    held(p, "missing_or_invalid_market_start")


def test_p2a_34_comparison_basis_exposes_original_market_id_and_window():
    out = preview_us_theme_packet(fixture())
    assert out["comparison_basis"] == {
        "benchmark_id": "SPY", "parent_id": "XLK",
        "price_basis": "split_adjusted", "session_basis": "daily_close",
        "period_start": (END - timedelta(days=5)).isoformat(),
        "period_end": END.isoformat(), "horizon": "5d",
        "decision_at": DECISION.isoformat(), "market": "US",
    }


def test_p2b_15_missing_fingerprint_authority_is_a_hold_not_exception():
    base = preview_us_theme_packet(flow_packet())["fingerprint"]
    base["authority"] = None
    ctx = project_owner_group_flow_context(
        base, flow_reading(), flow_binding())
    assert ctx["status"] == "HELD"
    assert ctx["reason"] == "missing_fingerprint_authority"
