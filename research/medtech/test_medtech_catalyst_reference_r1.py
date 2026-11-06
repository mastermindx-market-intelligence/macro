from copy import deepcopy

import pytest

from medtech_catalyst_reference_r1 import apply_market_revision, qualify_case


def event(
    pathway="PMA_ORIGINAL",
    decision="approved",
    public_at="2021-09-07T11:00:00Z",
    *,
    source_id="FDA:P180051/S001",
    device_id="OCS-HEART",
    applicant="TransMedics, Inc.",
    submission_id="P180051/S001",
    indication_id="DONOR_HEART_EX_VIVO_PERFUSION",
    territory="US",
):
    return {
        "pathway": pathway,
        "decision_state": decision,
        "public_at": public_at,
        "source_id": source_id,
        "device_id": device_id,
        "applicant": applicant,
        "submission_id": submission_id,
        "indication_id": indication_id,
        "territory": territory,
    }


def exposure(event_data=None, rights="owned", materiality="core"):
    bound = event_data or event()
    materiality_basis = {
        "core": "focused_pure_play",
        "material": "segment_material",
        "immaterial": "diversified_immaterial",
        "unknown": "unresolved",
    }[materiality]
    rights_basis = {
        "owned": "applicant_owned",
        "licensed": "exclusive_license",
        "unresolved": "unresolved",
    }[rights]
    issuer_id = "ISS:US-XNAS-TMDX"
    security_id = "SEC:US-XNAS-TMDX"
    relationship_id = "REL:TMDX:OCS-HEART:P180051-S001:US"
    return {
        "issuer_id": issuer_id,
        "security_id": security_id,
        "relationship_issuer_id": issuer_id,
        "relationship_security_id": security_id,
        "rights_state": rights,
        "materiality_state": materiality,
        "relationship_id": relationship_id,
        "rights_source_id": "TMDX:10-Q:2021Q3:OCS-HEART-RIGHTS",
        "rights_public_at": "2021-09-01T12:00:00Z",
        "materiality_source_id": "TMDX:10-Q:2021Q3:SEGMENT",
        "materiality_public_at": "2021-09-01T12:00:00Z",
        "materiality_basis": materiality_basis,
        "materiality_issuer_id": issuer_id,
        "materiality_security_id": security_id,
        "materiality_relationship_id": relationship_id,
        "device_id": bound["device_id"],
        "applicant": bound["applicant"],
        "submission_id": bound["submission_id"],
        "indication_id": bound["indication_id"],
        "territory": bound["territory"],
        "regulatory_source_id": bound["source_id"],
        "rights_basis": rights_basis,
        "license_term_id": "LICENSE:TMDX:OCS-HEART:US" if rights == "licensed" else None,
    }


def commercial(
    manufacturing="ready",
    launch="ready",
    coverage="not_applicable",
    adoption="early",
    *,
    public_at="2021-09-02T12:00:00Z",
    event_data=None,
    exposure_data=None,
):
    bound_event = event_data or event()
    bound_exposure = exposure_data or exposure(bound_event)
    return {
        "manufacturing_readiness": manufacturing,
        "launch_readiness": launch,
        "coverage_state": coverage,
        "adoption_state": adoption,
        "public_at": public_at,
        "source_id": "TMDX:COMMERCIAL-READINESS:2021-09-02",
        "bound_case": {
            "issuer_id": bound_exposure["issuer_id"],
            "security_id": bound_exposure["security_id"],
            "relationship_id": bound_exposure["relationship_id"],
            "device_id": bound_event["device_id"],
            "applicant": bound_event["applicant"],
            "submission_id": bound_event["submission_id"],
            "indication_id": bound_event["indication_id"],
            "territory": bound_event["territory"],
            "regulatory_source_id": bound_event["source_id"],
        },
    }


def options(
    *,
    observation_state="observed",
    as_of="2021-09-07T11:30:00Z",
    issuer_id="ISS:US-XNAS-TMDX",
    security_id="SEC:US-XNAS-TMDX",
):
    return {
        "observation_state": observation_state,
        "as_of": as_of,
        "source_id": "OPTIONS:QUALIFIED-SNAPSHOT",
        "issuer_id": issuer_id,
        "security_id": security_id,
        "coverage": "listed-options-complete-for-snapshot",
        "latency": "t_plus_1",
    }


def market_observation(
    *,
    reference_price=39.69,
    observed_at="2021-09-07T12:00:00Z",
    security_id="SEC:US-XNAS-TMDX",
    source_id="MARKET:QUALIFIED-SNAPSHOT",
):
    return {
        "security_id": security_id,
        "source_id": source_id,
        "reference_price": reference_price,
        "observed_at": observed_at,
    }


def qualify(**kwargs):
    event_value = kwargs.get("event", event())
    exposure_value = kwargs.get("exposure", exposure(event_value))
    commercial_value = kwargs.get(
        "commercial",
        commercial(event_data=event_value, exposure_data=exposure_value),
    )
    return qualify_case(
        event=event_value,
        exposure=exposure_value,
        commercial=commercial_value,
        options=kwargs.get("options"),
        as_of=kwargs.get("as_of", "2021-09-07T12:00:00Z"),
    )


def test_pma_approval_and_510k_clearance_keep_distinct_labels():
    assert qualify()["event"]["marketing_status"] == "FDA_APPROVED"
    cleared_event = event(
        "510K",
        "cleared",
        source_id="FDA:K241234",
        submission_id="K241234",
        indication_id="PREDICATE-EQUIVALENT-USE",
    )
    cleared = qualify(event=cleared_event)
    assert cleared["event"]["marketing_status"] == "FDA_CLEARED"
    with pytest.raises(ValueError, match="invalid for 510K"):
        qualify(event=event("510K", "approved"))


def test_future_publication_is_refused_and_decision_facts_are_redacted():
    result = qualify(as_of="2021-09-07T10:59:59Z")
    assert result["disposition"] == "WITHHELD_TEMPORAL"
    assert result["reasons"] == ["EVENT_NOT_PUBLIC_AT_CUTOFF"]
    assert result["event"]["knowledge_state"] == "WITHHELD_TEMPORAL"
    assert result["event"]["decision_state"] is None
    assert result["event"]["marketing_status"] is None
    assert result["event"]["positive_decision"] is None
    assert result["event"]["public_at"] is None
    assert result["event"]["source_id"] is None
    assert result["exposure"]["relationship"]["bound_case"]["regulatory_source_id"] is None


def test_unresolved_rights_withhold_the_security_join():
    result = qualify(exposure=exposure(rights="unresolved"))
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert result["exposure"]["rights_state"] == "unresolved"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert result["exposure"]["relationship"]["state"] == "UNRESOLVED"
    assert result["exposure"]["materiality_evidence"]["state"] == "UNRESOLVED"
    assert result["commercial"]["state"] == "COMMERCIAL_UNQUALIFIED"
    assert "COMMERCIAL_RELATIONSHIP_UNRESOLVED" in result["commercial"]["gaps"]
    assert result["recommendation_eligible"] is False


def test_diversified_issuer_materiality_unknown_does_not_become_a_pick():
    result = qualify(exposure=exposure(materiality="unknown"))
    assert result["disposition"] == "REVIEW_MATERIALITY"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert result["native_event_probability"] is None


def test_immaterial_clearance_is_context_only():
    cleared_event = event(
        "510K",
        "cleared",
        source_id="FDA:K241234",
        submission_id="K241234",
        indication_id="PREDICATE-EQUIVALENT-USE",
    )
    result = qualify(event=cleared_event, exposure=exposure(cleared_event, materiality="immaterial"))
    assert result["disposition"] == "CONTEXT_ONLY_IMMATERIAL"


def test_authorization_does_not_imply_commercial_readiness():
    result = qualify(
        commercial=commercial(
            manufacturing="partial",
            launch="not_ready",
            coverage="unknown",
            adoption="not_demonstrated",
        )
    )
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
    assert result["exposure"]["relationship"]["state"] == "RESOLVED"
    assert result["exposure"]["materiality_evidence"]["state"] == "RESOLVED"
    assert result["recommendation_eligible"] is False
    assert result["recommendation"] is None
    assert result["conditional_equity_values"] is None


def test_pending_event_does_not_inherit_positive_probability():
    result = qualify(event=event(decision="pending"))
    assert result["disposition"] == "RESEARCHING_EVENT_OUTCOME"
    assert result["native_event_probability"] is None


def test_options_context_cannot_change_native_regulatory_probability():
    result = qualify(options=options())
    assert result["expectations"]["state"] == "QUALIFIED_CONTEXT"
    assert result["expectations"]["can_change_native_event_probability"] is False
    assert result["native_event_probability"] is None


def test_unqualified_options_are_not_silently_used():
    result = qualify(options=options(observation_state="estimated"))
    assert result["expectations"]["state"] == "UNQUALIFIED"
    assert result["expectations"]["use"] == "none"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("coverage", "none"),
        ("latency", "unknown"),
    ],
)
def test_options_require_admissible_coverage_and_latency_before_qualification(field, replacement):
    payload = options()
    payload[field] = replacement
    result = qualify(options=payload)
    assert result["expectations"]["state"] == "UNQUALIFIED"
    assert result["expectations"]["use"] == "none"
    assert result["expectations"]["coverage"] == payload["coverage"]
    assert result["expectations"]["latency"] == payload["latency"]


def test_qualified_options_retain_coverage_and_latency_for_audit():
    payload = options()
    result = qualify(options=payload)
    assert result["expectations"]["state"] == "QUALIFIED_CONTEXT"
    assert result["expectations"]["coverage"] == "listed-options-complete-for-snapshot"
    assert result["expectations"]["latency"] == "t_plus_1"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("issuer_id", "ISS:US-XNYS-OTHER"),
        ("security_id", "SEC:US-XNYS-OTHER"),
    ],
)
def test_options_snapshot_must_bind_to_the_listed_case(field, replacement):
    payload = options()
    payload[field] = replacement
    result = qualify(options=payload)
    assert result["expectations"]["state"] == "UNQUALIFIED"
    assert result["expectations"]["use"] == "none"
    assert result["expectations"][field] == replacement


def test_qualified_options_retain_listing_identity_for_audit():
    result = qualify(options=options())
    assert result["expectations"]["issuer_id"] == "ISS:US-XNAS-TMDX"
    assert result["expectations"]["security_id"] == "SEC:US-XNAS-TMDX"


def test_empty_supplied_options_are_malformed_not_unavailable():
    with pytest.raises(ValueError, match="options missing required fields"):
        qualify(options={})


def test_price_only_revision_preserves_event_and_disposition():
    base = qualify()
    before_event = deepcopy(base["event"])
    before_exposure = deepcopy(base["exposure"])
    revised = apply_market_revision(base, observation=market_observation())
    assert revised["event"] == before_event
    assert revised["exposure"] == before_exposure
    assert revised["disposition"] == base["disposition"]
    assert revised["market_revision"]["effect"] == "PRICE_CONTEXT_ONLY"


@pytest.mark.parametrize("reference_price", [float("nan"), float("inf"), float("-inf")])
def test_market_revision_requires_a_finite_price(reference_price):
    with pytest.raises(ValueError, match="finite positive"):
        apply_market_revision(
            qualify(),
            observation=market_observation(reference_price=reference_price),
        )


def test_market_revision_after_case_cutoff_is_refused():
    with pytest.raises(ValueError, match="no later than case.as_of"):
        apply_market_revision(
            qualify(),
            observation=market_observation(observed_at="2025-01-01T20:00:00Z"),
        )


def test_market_revision_must_bind_to_case_security():
    with pytest.raises(ValueError, match="security_id must match"):
        apply_market_revision(
            qualify(),
            observation=market_observation(security_id="SEC:US-XNYS-OTHER"),
        )


def test_market_revision_retains_security_and_source_for_audit():
    revised = apply_market_revision(qualify(), observation=market_observation())
    assert revised["market_revision"]["security_id"] == "SEC:US-XNAS-TMDX"
    assert revised["market_revision"]["source_id"] == "MARKET:QUALIFIED-SNAPSHOT"


def test_timezone_is_required_for_event_knowledge_clock():
    with pytest.raises(ValueError, match="timezone"):
        qualify(event=event(public_at="2021-09-07T11:00:00"))


@pytest.mark.parametrize(
    ("layer", "field"),
    [
        ("exposure", "rights_public_at"),
        ("exposure", "materiality_public_at"),
        ("commercial", "public_at"),
        ("options", "as_of"),
    ],
)
def test_every_supplied_evidence_layer_requires_a_timezone_qualified_clock(layer, field):
    kwargs = {}
    if layer == "exposure":
        payload = exposure()
        payload[field] = "2021-09-01T12:00:00"
        kwargs["exposure"] = payload
    elif layer == "commercial":
        payload = commercial()
        payload[field] = "2021-09-02T12:00:00"
        kwargs["commercial"] = payload
    else:
        payload = options()
        payload[field] = "2021-09-07T11:30:00"
        kwargs["options"] = payload
    with pytest.raises(ValueError, match="timezone"):
        qualify(**kwargs)


@pytest.mark.parametrize(
    ("layer", "reason"),
    [
        ("rights", "RIGHTS_NOT_PUBLIC_AT_CUTOFF"),
        ("materiality", "MATERIALITY_NOT_PUBLIC_AT_CUTOFF"),
        ("commercial", "COMMERCIAL_NOT_PUBLIC_AT_CUTOFF"),
        ("options", "OPTIONS_NOT_PUBLIC_AT_CUTOFF"),
    ],
)
def test_future_evidence_in_any_layer_withholds_the_case(layer, reason):
    kwargs = {}
    if layer == "rights":
        payload = exposure()
        payload["rights_public_at"] = "2025-01-01T12:00:00Z"
        kwargs["exposure"] = payload
    elif layer == "materiality":
        payload = exposure()
        payload["materiality_public_at"] = "2025-01-01T12:00:00Z"
        kwargs["exposure"] = payload
    elif layer == "commercial":
        kwargs["commercial"] = commercial(public_at="2025-01-01T12:00:00Z")
    else:
        kwargs["options"] = options(as_of="2025-01-01T12:00:00Z")
    result = qualify(**kwargs)
    assert result["disposition"] == "WITHHELD_TEMPORAL"
    assert reason in result["reasons"]


def test_future_rights_and_materiality_claims_are_redacted():
    payload = exposure()
    payload["rights_public_at"] = "2025-01-01T12:00:00Z"
    payload["materiality_public_at"] = "2025-01-01T12:00:00Z"
    result = qualify(exposure=payload)
    assert result["exposure"]["rights_state"] == "unresolved"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert result["exposure"]["relationship"]["state"] == "WITHHELD_TEMPORAL"
    assert result["exposure"]["relationship"]["relationship_id"] is None
    assert result["exposure"]["materiality_evidence"]["state"] == "WITHHELD_TEMPORAL"
    assert result["exposure"]["materiality_evidence"]["basis"] is None


def test_future_rights_keep_public_materiality_unresolved_until_the_join_is_public():
    payload = exposure()
    payload["rights_public_at"] = "2025-01-01T12:00:00Z"
    result = qualify(exposure=payload)
    assert result["disposition"] == "WITHHELD_TEMPORAL"
    assert result["exposure"]["rights_state"] == "unresolved"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert result["exposure"]["relationship"]["state"] == "WITHHELD_TEMPORAL"
    assert result["exposure"]["materiality_evidence"]["state"] == "UNRESOLVED"
    assert result["exposure"]["materiality_evidence"]["basis"] is None


def test_future_commercial_and_options_payloads_are_redacted():
    result = qualify(
        commercial=commercial(public_at="2025-01-01T12:00:00Z"),
        options=options(as_of="2025-01-01T12:00:00Z"),
    )
    assert result["commercial"] == {
        "state": "WITHHELD_TEMPORAL",
        "gaps": [],
        "source_id": None,
        "public_at": None,
    }
    assert result["expectations"]["state"] == "WITHHELD_TEMPORAL"
    assert result["expectations"]["as_of"] is None
    assert result["expectations"]["source_id"] is None
    assert result["expectations"]["issuer_id"] is None
    assert result["expectations"]["security_id"] is None


@pytest.mark.parametrize(
    ("field", "replacement", "reason"),
    [
        ("device_id", "OTHER-DEVICE", "RELATIONSHIP_DEVICE_MISMATCH"),
        ("applicant", "Other Applicant", "RELATIONSHIP_APPLICANT_MISMATCH"),
        ("submission_id", "P000000", "RELATIONSHIP_SUBMISSION_MISMATCH"),
        ("indication_id", "OTHER-INDICATION", "RELATIONSHIP_INDICATION_MISMATCH"),
        ("territory", "EU", "RELATIONSHIP_TERRITORY_MISMATCH"),
        ("regulatory_source_id", "FDA:OTHER", "RELATIONSHIP_REGULATORY_SOURCE_MISMATCH"),
        ("relationship_issuer_id", "ISS:US-XNYS-OTHER", "RELATIONSHIP_ISSUER_MISMATCH"),
        ("relationship_security_id", "SEC:US-XNYS-OTHER", "RELATIONSHIP_SECURITY_MISMATCH"),
    ],
)
def test_relationship_mismatch_cannot_validate_rights_or_materiality(field, replacement, reason):
    payload = exposure()
    payload[field] = replacement
    result = qualify(exposure=payload)
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert result["exposure"]["rights_state"] == "unresolved"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert result["exposure"]["relationship"]["state"] == "UNRESOLVED"
    assert reason in result["reasons"]


def test_unrelated_top_level_listing_cannot_inherit_bound_device_rights():
    payload = exposure()
    payload["issuer_id"] = "ISS:US-XNYS-UNRELATED"
    payload["security_id"] = "SEC:US-XNYS-UNRELATED"
    result = qualify(exposure=payload)
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert result["exposure"]["rights_state"] == "unresolved"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert "RELATIONSHIP_ISSUER_MISMATCH" in result["reasons"]
    assert "RELATIONSHIP_SECURITY_MISMATCH" in result["reasons"]


def test_relationship_security_identity_is_required_as_evidence():
    payload = exposure()
    del payload["relationship_security_id"]
    result = qualify(exposure=payload)
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert "RELATIONSHIP_SECURITY_MISSING" in result["reasons"]


def test_relationship_mismatch_also_blocks_commercial_qualification():
    event_value = event()
    exposure_value = exposure(event_value)
    exposure_value["relationship_security_id"] = "SEC:US-XNYS-OTHER"
    commercial_value = commercial(event_data=event_value, exposure_data=exposure_value)
    result = qualify(
        event=event_value,
        exposure=exposure_value,
        commercial=commercial_value,
    )
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert result["commercial"]["state"] == "COMMERCIAL_UNQUALIFIED"
    assert "COMMERCIAL_RELATIONSHIP_UNRESOLVED" in result["commercial"]["gaps"]


def test_claimed_owned_core_without_relationship_provenance_fails_closed():
    payload = exposure()
    payload["relationship_id"] = ""
    payload["rights_source_id"] = ""
    result = qualify(exposure=payload)
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert "RELATIONSHIP_ID_MISSING" in result["reasons"]
    assert "RIGHTS_SOURCE_MISSING" in result["reasons"]


@pytest.mark.parametrize(
    ("field", "replacement", "reason"),
    [
        ("materiality_issuer_id", "ISS:US-XNYS-OTHER", "MATERIALITY_ISSUER_MISMATCH"),
        ("materiality_security_id", "SEC:US-XNYS-OTHER", "MATERIALITY_SECURITY_MISMATCH"),
        ("materiality_relationship_id", "REL:OTHER", "MATERIALITY_RELATIONSHIP_MISMATCH"),
    ],
)
def test_materiality_evidence_must_bind_to_the_listed_case(field, replacement, reason):
    payload = exposure()
    payload[field] = replacement
    result = qualify(exposure=payload)
    assert result["disposition"] == "REVIEW_MATERIALITY"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert reason in result["reasons"]


def test_materiality_listing_identity_is_required_as_evidence():
    payload = exposure()
    del payload["materiality_security_id"]
    result = qualify(exposure=payload)
    assert result["disposition"] == "REVIEW_MATERIALITY"
    assert "MATERIALITY_SECURITY_MISSING" in result["reasons"]


@pytest.mark.parametrize(
    ("field", "replacement", "reason"),
    [
        ("issuer_id", "ISS:US-XNYS-OTHER", "COMMERCIAL_ISSUER_MISMATCH"),
        ("security_id", "SEC:US-XNYS-OTHER", "COMMERCIAL_SECURITY_MISMATCH"),
        ("relationship_id", "REL:OTHER", "COMMERCIAL_RELATIONSHIP_MISMATCH"),
        ("device_id", "OTHER-DEVICE", "COMMERCIAL_DEVICE_MISMATCH"),
    ],
)
def test_commercial_evidence_must_bind_to_the_qualified_case(field, replacement, reason):
    payload = commercial()
    payload["bound_case"][field] = replacement
    result = qualify(commercial=payload)
    assert result["disposition"] == "AUTHORIZED_AWAITING_COMMERCIAL_PROOF"
    assert result["commercial"]["state"] == "COMMERCIAL_UNQUALIFIED"
    assert "COMMERCIAL_CASE_BINDING_UNRESOLVED" in result["commercial"]["gaps"]
    assert reason in result["commercial"]["gaps"]
    assert reason in result["reasons"]


def test_missing_commercial_bound_case_blocks_candidate_review():
    payload = commercial()
    del payload["bound_case"]
    result = qualify(commercial=payload)
    assert result["disposition"] == "AUTHORIZED_AWAITING_COMMERCIAL_PROOF"
    assert result["commercial"]["state"] == "COMMERCIAL_UNQUALIFIED"
    assert "COMMERCIAL_BOUND_CASE_MISSING" in result["commercial"]["gaps"]


def test_materiality_without_provenance_is_treated_as_unknown():
    payload = exposure()
    payload["materiality_source_id"] = ""
    result = qualify(exposure=payload)
    assert result["disposition"] == "REVIEW_MATERIALITY"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert "MATERIALITY_SOURCE_MISSING" in result["reasons"]


def test_licensed_rights_require_a_bound_license_term():
    payload = exposure(rights="licensed")
    payload["license_term_id"] = ""
    result = qualify(exposure=payload)
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert result["exposure"]["rights_state"] == "unresolved"
    assert "LICENSE_TERM_UNRESOLVED" in result["reasons"]


def test_missing_required_clock_is_refused_instead_of_defaulted():
    payload = exposure()
    del payload["rights_public_at"]
    with pytest.raises(ValueError, match="rights_public_at"):
        qualify(exposure=payload)


# Synthetic publication-clock regression; no observed data or scheduled-date API.
SYNTHETIC_CUTOFF = "2030-01-02T12:00:00Z"
SYNTHETIC_BEFORE = "2030-01-01T12:00:00Z"
SYNTHETIC_AFTER = "2030-01-03T12:00:00Z"


def _invented_event_clock_inputs(*, public_at=SYNTHETIC_BEFORE, decision="approved"):
    event = {
        "pathway": "PMA_ORIGINAL", "decision_state": decision,
        "public_at": public_at, "source_id": "SYNTHETIC:EVENT:A",
        "device_id": "SYNTHETIC:DEVICE", "applicant": "Invented Applicant",
        "submission_id": "SYNTHETIC:SUBMISSION", "indication_id": "SYNTHETIC:USE",
        "territory": "US",
    }
    exposure = {
        "issuer_id": "SYNTHETIC:ISSUER", "security_id": "SYNTHETIC:SECURITY",
        "relationship_issuer_id": "SYNTHETIC:ISSUER",
        "relationship_security_id": "SYNTHETIC:SECURITY",
        "rights_state": "owned", "materiality_state": "core",
        "relationship_id": "SYNTHETIC:RELATIONSHIP", "rights_source_id": "SYNTHETIC:RIGHTS",
        "rights_public_at": SYNTHETIC_BEFORE, "rights_basis": "applicant_owned",
        "materiality_source_id": "SYNTHETIC:MATERIALITY", "materiality_public_at": SYNTHETIC_BEFORE,
        "materiality_basis": "focused_pure_play", "materiality_issuer_id": "SYNTHETIC:ISSUER",
        "materiality_security_id": "SYNTHETIC:SECURITY",
        "materiality_relationship_id": "SYNTHETIC:RELATIONSHIP",
        **{key: event[key] for key in ("device_id", "applicant", "submission_id", "indication_id", "territory")},
        "regulatory_source_id": event["source_id"],
    }
    commercial = {
        "manufacturing_readiness": "ready", "launch_readiness": "ready",
        "coverage_state": "not_applicable", "adoption_state": "early",
        "public_at": SYNTHETIC_BEFORE, "source_id": "SYNTHETIC:COMMERCIAL",
        "bound_case": {key: exposure[key] for key in (
            "issuer_id", "security_id", "relationship_id", "device_id", "applicant",
            "submission_id", "indication_id", "territory", "regulatory_source_id",
        )},
    }
    return dict(event=event, exposure=exposure, commercial=commercial, as_of=SYNTHETIC_CUTOFF)


@pytest.mark.parametrize("public_at", [SYNTHETIC_BEFORE, SYNTHETIC_CUTOFF])
def test_public_event_at_or_before_cutoff_can_qualify(public_at):
    result = qualify_case(**_invented_event_clock_inputs(public_at=public_at))
    assert result["disposition"] == "CANDIDATE_REVIEW"
    assert result["exposure"]["relationship"]["state"] == "RESOLVED"
    assert result["exposure"]["materiality_evidence"]["state"] == "RESOLVED"
    assert result["commercial"]["state"] == "COMMERCIAL_READY"
    assert result["recommendation_eligible"] is False


def test_public_pending_event_is_not_future_publication():
    # An announced future schedule is public knowledge. This R1 API models the
    # publication clock and pending outcome, not a separate scheduled-event date.
    result = qualify_case(**_invented_event_clock_inputs(public_at=SYNTHETIC_BEFORE, decision="pending"))
    assert result["event"]["knowledge_state"] == "PUBLIC_AT_CUTOFF"
    assert result["event"]["decision_state"] == "pending"
    assert result["disposition"] == "RESEARCHING_EVENT_OUTCOME"
    assert result["native_event_probability"] is None


def test_future_publication_preserves_direct_redaction():
    result = qualify_case(**_invented_event_clock_inputs(public_at=SYNTHETIC_AFTER))
    assert result["disposition"] == "WITHHELD_TEMPORAL"
    assert result["reasons"] == ["EVENT_NOT_PUBLIC_AT_CUTOFF"]
    for field in ("source_id", "public_at", "decision_state", "marketing_status", "positive_decision"):
        assert result["event"][field] is None


def test_future_publication_cannot_resolve_dependent_claims():
    result = qualify_case(**_invented_event_clock_inputs(public_at=SYNTHETIC_AFTER))
    assert result["exposure"]["rights_state"] == "unresolved"
    assert result["exposure"]["relationship"]["state"] != "RESOLVED"
    assert result["exposure"]["materiality_state"] == "unknown"
    assert result["exposure"]["materiality_evidence"]["state"] != "RESOLVED"
    assert result["commercial"]["state"] != "COMMERCIAL_READY"


def test_redacted_future_source_cannot_change_historical_output():
    inputs = _invented_event_clock_inputs(public_at=SYNTHETIC_AFTER)
    before = deepcopy(inputs)
    matching = qualify_case(**inputs)
    assert inputs == before
    inputs["event"]["source_id"] = "SYNTHETIC:EVENT:B"
    changed_hidden_source = qualify_case(**inputs)
    assert matching["event"] == changed_hidden_source["event"]
    assert matching == changed_hidden_source


def test_public_source_mismatch_remains_fail_closed():
    inputs = _invented_event_clock_inputs()
    inputs["event"]["source_id"] = "SYNTHETIC:EVENT:B"
    result = qualify_case(**inputs)
    assert result["disposition"] == "WITHHELD_IDENTITY_RIGHTS"
    assert "RELATIONSHIP_REGULATORY_SOURCE_MISMATCH" in result["reasons"]
    assert "COMMERCIAL_REGULATORY_SOURCE_MISMATCH" in result["commercial"]["gaps"]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source_id", "SYNTHETIC:EVENT:B"),
        ("device_id", "SYNTHETIC:OTHER-DEVICE"),
        ("applicant", "Other Invented Applicant"),
        ("submission_id", "SYNTHETIC:OTHER-SUBMISSION"),
        ("indication_id", "SYNTHETIC:OTHER-USE"),
        ("territory", "SYNTHETIC:OTHER-TERRITORY"),
        ("decision_state", "denied"),
        ("public_at", "2030-01-04T12:00:00Z"),
    ],
)
def test_unpublished_event_facts_cannot_change_dependent_states_or_gaps(field, replacement):
    inputs = _invented_event_clock_inputs(public_at=SYNTHETIC_AFTER)
    before = qualify_case(**inputs)
    inputs["event"][field] = replacement
    after = qualify_case(**inputs)
    for layer in ("exposure", "commercial", "expectations", "disposition", "reasons"):
        assert before[layer] == after[layer]


def test_future_event_preserves_independent_public_evidence_and_diagnostics():
    inputs = _invented_event_clock_inputs(public_at=SYNTHETIC_AFTER)
    inputs["commercial"]["manufacturing_readiness"] = "not_ready"
    result = qualify_case(**inputs)
    assert result["exposure"]["relationship"]["source_id"] == "SYNTHETIC:RIGHTS"
    assert result["exposure"]["relationship"]["public_at"] == SYNTHETIC_BEFORE
    assert result["exposure"]["materiality_evidence"]["source_id"] == "SYNTHETIC:MATERIALITY"
    assert result["exposure"]["materiality_evidence"]["public_at"] == SYNTHETIC_BEFORE
    assert result["commercial"]["source_id"] == "SYNTHETIC:COMMERCIAL"
    assert result["commercial"]["public_at"] == SYNTHETIC_BEFORE
    assert "MANUFACTURING_NOT_READY" in result["commercial"]["gaps"]
    inputs["commercial"]["bound_case"]["issuer_id"] = "SYNTHETIC:OTHER-ISSUER"
    mismatch = qualify_case(**inputs)
    assert "COMMERCIAL_ISSUER_MISMATCH" in mismatch["commercial"]["gaps"]


# Future-rights relationship identity must not act as a commercial oracle.
def test_future_rights_relationship_id_is_not_a_commercial_oracle():
    inputs = _invented_event_clock_inputs()
    inputs["exposure"]["rights_public_at"] = SYNTHETIC_AFTER
    frozen = deepcopy(inputs)
    baseline = qualify_case(**inputs)
    assert inputs == frozen
    variant_inputs = deepcopy(inputs)
    variant_inputs["exposure"]["relationship_id"] = "SYNTHETIC:RELATIONSHIP:OTHER"
    variant_frozen = deepcopy(variant_inputs)
    variant = qualify_case(**variant_inputs)
    assert variant_inputs == variant_frozen
    assert variant == baseline
    assert baseline["disposition"] == "WITHHELD_TEMPORAL"
    assert baseline["commercial"]["state"] == "COMMERCIAL_UNQUALIFIED"
    assert "COMMERCIAL_RELATIONSHIP_UNRESOLVED" in baseline["commercial"]["gaps"]
    assert "COMMERCIAL_RELATIONSHIP_MISMATCH" not in baseline["commercial"]["gaps"]


def test_public_relationship_mismatch_still_detected():
    for rights_public_at in (SYNTHETIC_BEFORE, SYNTHETIC_CUTOFF):
        inputs = _invented_event_clock_inputs()
        inputs["exposure"]["rights_public_at"] = rights_public_at
        baseline = qualify_case(**inputs)
        assert "COMMERCIAL_RELATIONSHIP_MISMATCH" not in baseline["commercial"]["gaps"]
        mismatched = deepcopy(inputs)
        mismatched["exposure"]["relationship_id"] = "SYNTHETIC:RELATIONSHIP:OTHER"
        result = qualify_case(**mismatched)
        assert "COMMERCIAL_RELATIONSHIP_MISMATCH" in result["commercial"]["gaps"]
        assert result["commercial"]["state"] == "COMMERCIAL_UNQUALIFIED"


def test_future_rights_keep_commercial_required_relationship_check():
    inputs = _invented_event_clock_inputs()
    inputs["exposure"]["rights_public_at"] = SYNTHETIC_AFTER
    del inputs["commercial"]["bound_case"]["relationship_id"]
    result = qualify_case(**inputs)
    assert "COMMERCIAL_RELATIONSHIP_MISSING" in result["commercial"]["gaps"]
    assert "COMMERCIAL_RELATIONSHIP_MISMATCH" not in result["commercial"]["gaps"]


def test_future_rights_keep_readiness_diagnostics():
    inputs = _invented_event_clock_inputs()
    inputs["exposure"]["rights_public_at"] = SYNTHETIC_AFTER
    inputs["commercial"]["manufacturing_readiness"] = "not_ready"
    public_twin = deepcopy(inputs)
    public_twin["exposure"]["rights_public_at"] = SYNTHETIC_BEFORE
    future = qualify_case(**inputs)
    public = qualify_case(**public_twin)
    assert future["commercial"]["gaps"][:2] == [
        "COMMERCIAL_CASE_BINDING_UNRESOLVED",
        "COMMERCIAL_RELATIONSHIP_UNRESOLVED",
    ]
    assert future["commercial"]["gaps"][2:] == public["commercial"]["gaps"]
    assert public["commercial"]["gaps"]
    assert "COMMERCIAL_RELATIONSHIP_MISMATCH" not in future["commercial"]["gaps"]


def test_future_rights_keep_public_issuer_and_security_mismatches():
    inputs = _invented_event_clock_inputs()
    inputs["exposure"]["rights_public_at"] = SYNTHETIC_AFTER
    issuer_inputs = deepcopy(inputs)
    issuer_inputs["commercial"]["bound_case"]["issuer_id"] = "SYNTHETIC:ISSUER:OTHER"
    issuer_result = qualify_case(**issuer_inputs)
    assert "COMMERCIAL_ISSUER_MISMATCH" in issuer_result["commercial"]["gaps"]
    security_inputs = deepcopy(inputs)
    security_inputs["commercial"]["bound_case"]["security_id"] = "SYNTHETIC:SECURITY:OTHER"
    security_result = qualify_case(**security_inputs)
    assert "COMMERCIAL_SECURITY_MISMATCH" in security_result["commercial"]["gaps"]
    for result in (issuer_result, security_result):
        assert "COMMERCIAL_RELATIONSHIP_MISMATCH" not in result["commercial"]["gaps"]


def test_future_rights_keep_public_event_mismatch():
    inputs = _invented_event_clock_inputs()
    inputs["exposure"]["rights_public_at"] = SYNTHETIC_AFTER
    mismatched = deepcopy(inputs)
    mismatched["commercial"]["bound_case"]["device_id"] = "SYNTHETIC:DEVICE:OTHER"
    result = qualify_case(**mismatched)
    assert "COMMERCIAL_DEVICE_MISMATCH" in result["commercial"]["gaps"]
    assert "COMMERCIAL_RELATIONSHIP_MISMATCH" not in result["commercial"]["gaps"]
