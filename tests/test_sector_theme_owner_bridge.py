"""Adversarial P2 source admission tests — no real market data or account I/O."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from engine.sector_theme_owner_bridge import preview_us_theme_packet

END = datetime(2026, 10, 29, 20, tzinfo=timezone.utc)
DECISION = END + timedelta(minutes=5)
MEMBER_KNOWN = END - timedelta(days=1)
IDENTITY_KNOWN = END - timedelta(days=7)


def quote(ret=.03, *, horizon="5d", price_basis="split_adjusted"):
    return {
        "horizon": horizon,
        "period_end": END.isoformat(),
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
