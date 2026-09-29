from copy import deepcopy

import pytest

from medtech_catalyst_reference_r1 import apply_market_revision, qualify_case


def event(pathway="PMA_ORIGINAL", decision="approved", public_at="2021-09-07T11:00:00Z"):
    return {
        "pathway": pathway,
        "decision_state": decision,
        "public_at": public_at,
        "source_id": "FDA:P180051",
        "device_id": "OCS-HEART",
        "applicant": "TransMedics, Inc.",
    }


def exposure(rights="owned", materiality="core"):
    return {"issuer_id": "US:TMDX", "rights_state": rights, "materiality_state": materiality}


def commercial(manufacturing="ready", launch="ready", coverage="not_applicable", adoption="early"):
    return {
        "manufacturing_readiness": manufacturing,
        "launch_readiness": launch,
        "coverage_state": coverage,
        "adoption_state": adoption,
    }


def qualify(**kwargs):
    return qualify_case(
        event=kwargs.get("event", event()),
        exposure=kwargs.get("exposure", exposure()),
        commercial=kwargs.get("commercial", commercial()),
        options=kwargs.get("options"),
        as_of=kwargs.get("as_of", "2021-09-07T12:00:00Z"),
    )


def test_pma_approval_and_510k_clearance_keep_distinct_labels():
    assert qualify()["event"]["marketing_status"] == "FDA_APPROVED"
    cleared = qualify(event=event("510K", "cleared"))
    assert cleared["event"]["marketing_status"] == "FDA_CLEARED"
    with pytest.raises(ValueError, match="invalid for 510K"):
        qualify(event=event("510K", "approved"))


def test_future_publication_is_refused_even_when_decision_is_positive():
    result = qualify(as_of="2021-09-07T10:59:59Z")
    assert result["disposition"] == "WITHHELD_TEMPORAL"
    assert result["reasons"] == ["EVENT_NOT_PUBLIC_AT_CUTOFF"]


def test_unresolved_rights_withhold_the_security_join():
    result = qualify(exposure=exposure(rights="unresolved"))
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert result["recommendation_eligible"] is False


def test_diversified_issuer_materiality_unknown_does_not_become_a_pick():
    result = qualify(exposure=exposure(materiality="unknown"))
    assert result["disposition"] == "REVIEW_MATERIALITY"
    assert result["native_event_probability"] is None


def test_immaterial_clearance_is_context_only():
    result = qualify(event=event("510K", "cleared"), exposure=exposure(materiality="immaterial"))
    assert result["disposition"] == "CONTEXT_ONLY_IMMATERIAL"


def test_authorization_does_not_imply_commercial_readiness():
    result = qualify(commercial=commercial(manufacturing="partial", launch="not_ready", coverage="unknown", adoption="not_demonstrated"))
    assert result["disposition"] == "AUTHORIZED_AWAITING_COMMERCIAL_PROOF"
    assert set(result["commercial"]["gaps"]) == {
        "MANUFACTURING_NOT_READY",
        "LAUNCH_NOT_READY",
        "COVERAGE_NOT_ESTABLISHED",
        "ADOPTION_NOT_ESTABLISHED",
    }


def test_complete_research_inputs_reach_candidate_review_but_not_recommendation():
    result = qualify()
    assert result["disposition"] == "CANDIDATE_REVIEW"
    assert result["recommendation_eligible"] is False
    assert result["recommendation"] is None
    assert result["conditional_equity_values"] is None


def test_pending_event_does_not_inherit_positive_probability():
    result = qualify(event=event(decision="pending"))
    assert result["disposition"] == "RESEARCHING_EVENT_OUTCOME"
    assert result["native_event_probability"] is None


def test_options_context_cannot_change_native_regulatory_probability():
    result = qualify(options={
        "observation_state": "observed",
        "as_of": "2021-09-07T11:30:00Z",
        "source_id": "OPTIONS:QUALIFIED-SNAPSHOT",
        "coverage": "listed-options-complete-for-snapshot",
        "latency": "t_plus_1",
    })
    assert result["expectations"]["state"] == "QUALIFIED_CONTEXT"
    assert result["expectations"]["can_change_native_event_probability"] is False
    assert result["native_event_probability"] is None


def test_unqualified_options_are_not_silently_used():
    result = qualify(options={"observation_state": "estimated"})
    assert result["expectations"]["state"] == "UNQUALIFIED"
    assert result["expectations"]["use"] == "none"


def test_price_only_revision_preserves_event_and_disposition():
    base = qualify()
    before_event = deepcopy(base["event"])
    revised = apply_market_revision(base, reference_price=39.69, observed_at="2021-09-07T20:00:00Z")
    assert revised["event"] == before_event
    assert revised["disposition"] == base["disposition"]
    assert revised["market_revision"]["effect"] == "PRICE_CONTEXT_ONLY"


def test_timezone_is_required_for_knowledge_clock():
    with pytest.raises(ValueError, match="timezone"):
        qualify(event=event(public_at="2021-09-07T11:00:00"))
