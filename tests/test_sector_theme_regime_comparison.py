"""Source-clocked comparison scanner counterexamples, no real data or I/O."""
from __future__ import annotations

from copy import deepcopy

from engine.sector_theme_owner_bridge import preview_us_theme_packet
from engine.sector_theme_regime_comparison import compose_regime_comparison
from tests.test_sector_theme_owner_bridge import fixture, quote, END, DECISION


def second(*, shares_a=False):
    p = fixture()
    p["group_id"] = "UTILITIES"
    p["group_kind"] = "sector"
    p["cohort_id"] = "fixture-utilities"
    p["membership_revision"] = "utility-rev1"
    p["membership_asof"]["basket_id"] = "UTILITIES"
    p["membership_asof"]["members"] = ["CCC", "DDD"]
    p["member_identities"] = {
        "CCC": {"security_id": "SEC_CCC", "issuer_id": "ISS_CCC",
                "resolution_state": "RESOLVED",
                "available_at": p["member_identities"]["AAA"]["available_at"]},
        "DDD": {"security_id": "SEC_DDD", "issuer_id": "ISS_DDD",
                "resolution_state": "RESOLVED",
                "available_at": p["member_identities"]["AAA"]["available_at"]},
    }
    p["market"]["member_rows"] = {
        "CCC": quote(.06), "DDD": quote(.04),
    }
    p["market"]["parent"] = None
    p["market"]["parent_id"] = None
    if shares_a:
        p["membership_asof"]["members"] = ["AAA", "DDD"]
        p["member_identities"]["AAA"] = fixture()["member_identities"]["AAA"]
        del p["member_identities"]["CCC"]
        p["market"]["member_rows"]["AAA"] = quote(.06)
        del p["market"]["member_rows"]["CCC"]
    return p


def preview_pairs(*, shares_a=False):
    return {
        "AI_INDUSTRIAL_INFRA": preview_us_theme_packet(fixture()),
        "UTILITIES": preview_us_theme_packet(second(shares_a=shares_a)),
    }


def test_p3a_01_two_groups_are_compatible_not_ranked():
    result = compose_regime_comparison(preview_pairs())
    assert result["schema"] == "sector_theme_regime_comparison/v1"
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert [p["group_id"] for p in result["groups"]] == [
        "AI_INDUSTRIAL_INFRA", "UTILITIES"]
    assert [p["kind"] for p in result["groups"]] == ["theme", "sector"]
    assert result["sort_basis"] == "canonical_group_id_not_performance_rank"
    assert result["comparison_basis"]["benchmark_id"] == "SPY"
    assert result["ranking_authority"] is False
    assert result["forecast_or_trading_authority"] is False
    assert result["customer_publication"] is False


def test_p3a_02_known_rs_and_breadth_are_numeric_not_classified_from_scores():
    result = compose_regime_comparison(preview_pairs())
    theme, sector = result["groups"]
    assert theme["equal_weight_full_cohort_return"]["value"] == .035
    assert sector["equal_weight_full_cohort_return"]["value"] == .05
    assert theme["positive_return_breadth"]["identification_bounds"] == [1.0, 1.0]
    assert sector["rs_parent"]["status"] == "unmeasured"
    assert "flow_score" not in repr(result)


def test_p3a_03_shared_name_is_not_counted_as_independent_evidence():
    result = compose_regime_comparison(preview_pairs(shares_a=True))
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert result["security_overlap"] == [{
        "member_id": "SEC_AAA",
        "group_ids": ["AI_INDUSTRIAL_INFRA", "UTILITIES"],
    }]
    assert result["issuer_overlap"] == [{
        "issuer_id": "ISS_AAA",
        "group_ids": ["AI_INDUSTRIAL_INFRA", "UTILITIES"],
    }]
    assert result["no_independent_votes_from_duplicate_securities"] is True
    assert result["no_independent_votes_from_duplicate_issuers"] is True


def test_p3a_04_market_benchmark_identity_change_refuses_comparison():
    data = preview_pairs()
    data["UTILITIES"] = preview_us_theme_packet({
        **second(), "market": {**second()["market"], "benchmark_id": "QQQ"}
    })
    result = compose_regime_comparison(data)
    assert result["status"] == "HELD"
    assert result["reason"] == "cross_group_time_benchmark_or_price_basis_mismatch"


def test_p3a_05_different_market_clock_refuses_apples_to_oranges():
    p = second()
    p["market"]["decision_at"] = "2026-10-29T20:10:00+00:00"
    data = preview_pairs()
    data["UTILITIES"] = preview_us_theme_packet(p)
    assert compose_regime_comparison(data)["reason"] == (
        "cross_group_time_benchmark_or_price_basis_mismatch")


def test_p3a_06_different_session_and_adjustment_basis_refused():
    p = second()
    p["market"]["session_basis"] = "overnight"
    p["market"]["benchmark"]["session_basis"] = "overnight"
    for row in p["market"]["member_rows"].values():
        row["session_basis"] = "overnight"
    data = preview_pairs()
    data["UTILITIES"] = preview_us_theme_packet(p)
    assert compose_regime_comparison(data)["reason"] == (
        "cross_group_time_benchmark_or_price_basis_mismatch")

    p = second()
    p["market"]["price_basis"] = "total_return_adjusted"
    p["market"]["benchmark"]["price_basis"] = "total_return_adjusted"
    for row in p["market"]["member_rows"].values():
        row["price_basis"] = "total_return_adjusted"
    data["UTILITIES"] = preview_us_theme_packet(p)
    assert compose_regime_comparison(data)["reason"] == (
        "cross_group_time_benchmark_or_price_basis_mismatch")


def test_p3a_07_roster_modes_are_exposed_per_group_not_laundered_into_pit():
    p = second()
    p["membership_asof"].update(pit=False, basis="current_membership",
                                snapshot_date=None)
    p["membership_mode"] = "CURRENT_ROSTER"
    p["membership_known_at"] = DECISION.isoformat()
    data = preview_pairs()
    data["UTILITIES"] = preview_us_theme_packet(p)
    result = compose_regime_comparison(data)
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert result["groups"][1]["membership_basis"] == "CURRENT_ROSTER"
    assert result["input_rights_and_original_receipts_authenticated"] is False
    assert result["customer_publication"] is False


def test_p3a_08_held_source_must_not_disappear_from_comparison():
    data = preview_pairs()
    data["UTILITIES"] = preview_us_theme_packet(None)
    result = compose_regime_comparison(data)
    assert result["status"] == "HELD"
    assert result["groups"] == []
    assert result["reason"] == "held_or_noncanonical_input"


def test_p3a_09_tampered_fp_authority_or_score_cannot_appear():
    data = preview_pairs()
    data["UTILITIES"]["fingerprint"]["authority"]["ranking_authority"] = True
    result = compose_regime_comparison(data)
    assert result["status"] == "HELD"
    assert result["reason"] == "fingerprint_claims_decision_authority"


def test_p3a_10_tampered_narrative_probability_cannot_be_shown():
    data = preview_pairs()
    p = data["AI_INDUSTRIAL_INFRA"]
    p["explanation"]["group_cards"].append({
        "tag": "dreamed_up",
        "source_status": "unqualified_descriptive_preview",
        "forecast_probability": .9, "trade_recommendation": None,
    })
    result = compose_regime_comparison(data)
    assert result["reason"] == "unsupported_narrative_claim"


def test_p3a_11_source_group_id_and_population_mismatch_are_refused():
    data = preview_pairs()
    data["UTILITIES"]["frame"]["group"]["group_id"] = "DIFFERENT"
    assert compose_regime_comparison(data)["reason"] == (
        "group_id_or_membership_basis_mismatch")
    data = preview_pairs()
    data["UTILITIES"]["fingerprint"]["group"]["member_ids"] = ["SEC_CCC"]
    assert compose_regime_comparison(data)["reason"] == (
        "invalid_or_mismatched_group_population")


def test_p3a_12_zero_or_missing_indicators_are_unmeasured_not_zero():
    p = second()
    p["market"]["member_rows"].pop("DDD")
    data = preview_pairs()
    data["UTILITIES"] = preview_us_theme_packet(p)
    result = compose_regime_comparison(data)
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    row = result["groups"][1]
    assert row["measured_return_n"] == 1
    assert row["equal_weight_full_cohort_return"]["status"] == "unmeasured"
    assert row["positive_return_breadth"]["identification_bounds"] == [.5, 1.0]


def test_p3a_13_unknown_or_duplicate_input_id_is_blocked():
    data = preview_pairs()
    data[None] = data.pop("UTILITIES")
    assert compose_regime_comparison(data)["reason"] == "invalid_group_key"
    data = preview_pairs()
    data["DIFFERENT"] = data.pop("UTILITIES")
    assert compose_regime_comparison(data)["reason"] == (
        "group_id_or_membership_basis_mismatch")


def test_p3a_14_no_mutation_or_unstable_rank():
    data = preview_pairs()
    original = deepcopy(data)
    a = compose_regime_comparison(data)
    b = compose_regime_comparison(data)
    assert data == original and a == b
    assert all(x.get("source_evidence_status")
               == "unqualified_preview_not_customer_publishable"
               for x in a["groups"])


def test_p3a_15_single_group_is_descriptive_not_fake_peer_ranking():
    data = {"AI_INDUSTRIAL_INFRA": preview_us_theme_packet(fixture())}
    x = compose_regime_comparison(data)
    assert x["status"] == "RESEARCH_PREVIEW_ONLY"
    assert len(x["groups"]) == 1
    assert x["ranking_authority"] is False


def test_p3a_16_two_share_classes_same_issuer_no_duplicate_security():
    p = second()
    p["member_identities"]["CCC"]["issuer_id"] = "ISS_AAA"
    data = preview_pairs()
    data["UTILITIES"] = preview_us_theme_packet(p)
    report = compose_regime_comparison(data)
    assert report["status"] == "RESEARCH_PREVIEW_ONLY"
    assert report["security_overlap"] == []
    assert report["issuer_overlap"] == [{
        "issuer_id": "ISS_AAA",
        "group_ids": ["AI_INDUSTRIAL_INFRA", "UTILITIES"],
    }]
    assert report["groups"][1]["population_n"] == 2
    assert report["groups"][1]["unique_issuer_n"] == 2


def test_p3a_17_multiple_securities_same_issuer_within_group_disclosed():
    p = second()
    p["member_identities"]["DDD"]["issuer_id"] = "ISS_CCC"
    data = preview_pairs()
    data["UTILITIES"] = preview_us_theme_packet(p)
    report = compose_regime_comparison(data)
    assert report["status"] == "RESEARCH_PREVIEW_ONLY"
    assert report["groups"][1]["population_n"] == 2
    assert report["groups"][1]["unique_issuer_n"] == 1
    assert report["groups"][1]["security_breadth_not_independent_issuer_breadth"] is True


def test_p3a_18_forged_issuer_mapping_or_count_must_not_relabel_coverage():
    data = preview_pairs()
    data["UTILITIES"]["issuer_by_security_id"] = {"SEC_CCC": "ISS_CCC"}
    assert compose_regime_comparison(data)["reason"] == (
        "missing_or_invalid_security_issuer_mapping")
    data = preview_pairs()
    data["UTILITIES"]["unique_issuer_n"] = 999
    assert compose_regime_comparison(data)["reason"] == (
        "invalid_unique_issuer_population")
