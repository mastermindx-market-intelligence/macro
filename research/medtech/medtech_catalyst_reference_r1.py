"""Research-only MedTech Catalyst Intelligence reference contract.

This module does not predict FDA outcomes, rank securities, or issue recommendations.
It pins distinctions that a later production implementation must preserve:
regulatory pathway/decision, public-knowledge time, evidence-backed security rights,
issuer materiality, commercial readiness, market expectations, and recommendation
admission.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
from typing import Any, Mapping


PATHWAY_STATES: dict[str, frozenset[str]] = {
    "PMA_ORIGINAL": frozenset({"pending", "approved", "denied", "withdrawn"}),
    "PMA_PANEL_TRACK_SUPPLEMENT": frozenset({"pending", "approved", "denied", "withdrawn"}),
    "PMA_OTHER_SUPPLEMENT": frozenset({"pending", "approved", "denied", "withdrawn"}),
    "510K": frozenset({"pending", "cleared", "nse", "withdrawn"}),
    "DE_NOVO": frozenset({"pending", "granted", "declined", "withdrawn"}),
    "HDE": frozenset({"pending", "approved", "denied", "withdrawn"}),
}

POSITIVE_DECISIONS = {
    ("PMA_ORIGINAL", "approved"),
    ("PMA_PANEL_TRACK_SUPPLEMENT", "approved"),
    ("PMA_OTHER_SUPPLEMENT", "approved"),
    ("510K", "cleared"),
    ("DE_NOVO", "granted"),
    ("HDE", "approved"),
}

MARKETING_LABEL = {
    ("PMA_ORIGINAL", "approved"): "FDA_APPROVED",
    ("PMA_PANEL_TRACK_SUPPLEMENT", "approved"): "FDA_APPROVED_SUPPLEMENT",
    ("PMA_OTHER_SUPPLEMENT", "approved"): "FDA_APPROVED_SUPPLEMENT",
    ("510K", "cleared"): "FDA_CLEARED",
    ("DE_NOVO", "granted"): "FDA_DE_NOVO_GRANTED",
    ("HDE", "approved"): "FDA_HDE_APPROVED",
}

RIGHTS_STATES = frozenset({"owned", "licensed", "unresolved"})
MATERIALITY_STATES = frozenset({"core", "material", "immaterial", "unknown"})
READINESS_STATES = frozenset({"ready", "partial", "not_ready", "unknown"})
COVERAGE_STATES = frozenset({"covered", "partially_covered", "not_covered", "unknown", "not_applicable"})
ADOPTION_STATES = frozenset({"demonstrated", "early", "not_demonstrated", "unknown"})
OPTIONS_COVERAGE_STATES = frozenset({"listed-options-complete-for-snapshot"})
OPTIONS_LATENCY_STATES = frozenset({"t_plus_1"})
RIGHTS_BASIS_BY_STATE = {
    "owned": frozenset({"applicant_owned", "subsidiary_owned"}),
    "licensed": frozenset({"exclusive_license", "nonexclusive_license"}),
    "unresolved": frozenset({"unresolved"}),
}
MATERIALITY_BASIS_BY_STATE = {
    "core": frozenset({"focused_pure_play"}),
    "material": frozenset({"segment_material"}),
    "immaterial": frozenset({"diversified_immaterial"}),
    "unknown": frozenset({"unresolved"}),
}


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc(value: str, *, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must carry a timezone")
    return parsed.astimezone(timezone.utc)


def _require(mapping: Mapping[str, Any], names: tuple[str, ...], *, owner: str) -> None:
    missing = [name for name in names if mapping.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{owner} missing required fields: {', '.join(missing)}")


def _commercial_state(commercial: Mapping[str, Any]) -> tuple[str, list[str]]:
    _require(
        commercial,
        (
            "manufacturing_readiness",
            "launch_readiness",
            "coverage_state",
            "adoption_state",
            "public_at",
            "source_id",
        ),
        owner="commercial",
    )
    manufacturing = str(commercial["manufacturing_readiness"])
    launch = str(commercial["launch_readiness"])
    coverage = str(commercial["coverage_state"])
    adoption = str(commercial["adoption_state"])
    if manufacturing not in READINESS_STATES or launch not in READINESS_STATES:
        raise ValueError("commercial readiness state is invalid")
    if coverage not in COVERAGE_STATES:
        raise ValueError("coverage_state is invalid")
    if adoption not in ADOPTION_STATES:
        raise ValueError("adoption_state is invalid")

    gaps: list[str] = []
    if manufacturing != "ready":
        gaps.append("MANUFACTURING_NOT_READY")
    if launch != "ready":
        gaps.append("LAUNCH_NOT_READY")
    if coverage not in {"covered", "not_applicable"}:
        gaps.append("COVERAGE_NOT_ESTABLISHED")
    if adoption not in {"demonstrated", "early"}:
        gaps.append("ADOPTION_NOT_ESTABLISHED")
    return ("COMMERCIAL_READY" if not gaps else "COMMERCIAL_UNQUALIFIED", gaps)


def _commercial_binding_reasons(
    event: Mapping[str, Any],
    exposure: Mapping[str, Any],
    commercial: Mapping[str, Any],
) -> list[str]:
    bound_case = commercial.get("bound_case")
    if not isinstance(bound_case, Mapping):
        return ["COMMERCIAL_BOUND_CASE_MISSING"]

    reasons: list[str] = []
    required = {
        "issuer_id": "COMMERCIAL_ISSUER_MISSING",
        "security_id": "COMMERCIAL_SECURITY_MISSING",
        "relationship_id": "COMMERCIAL_RELATIONSHIP_MISSING",
        "device_id": "COMMERCIAL_DEVICE_MISSING",
        "applicant": "COMMERCIAL_APPLICANT_MISSING",
        "submission_id": "COMMERCIAL_SUBMISSION_MISSING",
        "indication_id": "COMMERCIAL_INDICATION_MISSING",
        "territory": "COMMERCIAL_TERRITORY_MISSING",
        "regulatory_source_id": "COMMERCIAL_REGULATORY_SOURCE_MISSING",
    }
    for field, reason in required.items():
        if bound_case.get(field) in (None, ""):
            reasons.append(reason)

    exposure_comparisons = (
        ("issuer_id", "issuer_id", "COMMERCIAL_ISSUER_MISMATCH"),
        ("security_id", "security_id", "COMMERCIAL_SECURITY_MISMATCH"),
        ("relationship_id", "relationship_id", "COMMERCIAL_RELATIONSHIP_MISMATCH"),
    )
    for bound_field, exposure_field, reason in exposure_comparisons:
        value = bound_case.get(bound_field)
        if value not in (None, "") and value != exposure.get(exposure_field):
            reasons.append(reason)

    event_comparisons = (
        ("device_id", "device_id", "COMMERCIAL_DEVICE_MISMATCH"),
        ("applicant", "applicant", "COMMERCIAL_APPLICANT_MISMATCH"),
        ("submission_id", "submission_id", "COMMERCIAL_SUBMISSION_MISMATCH"),
        ("indication_id", "indication_id", "COMMERCIAL_INDICATION_MISMATCH"),
        ("territory", "territory", "COMMERCIAL_TERRITORY_MISMATCH"),
        ("regulatory_source_id", "source_id", "COMMERCIAL_REGULATORY_SOURCE_MISMATCH"),
    )
    for bound_field, event_field, reason in event_comparisons:
        value = bound_case.get(bound_field)
        if value not in (None, "") and value != event.get(event_field):
            reasons.append(reason)
    return reasons


def _relationship_reasons(event: Mapping[str, Any], exposure: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    required = {
        "relationship_id": "RELATIONSHIP_ID_MISSING",
        "rights_source_id": "RIGHTS_SOURCE_MISSING",
        "relationship_issuer_id": "RELATIONSHIP_ISSUER_MISSING",
        "relationship_security_id": "RELATIONSHIP_SECURITY_MISSING",
        "device_id": "RELATIONSHIP_DEVICE_MISSING",
        "applicant": "RELATIONSHIP_APPLICANT_MISSING",
        "submission_id": "RELATIONSHIP_SUBMISSION_MISSING",
        "indication_id": "RELATIONSHIP_INDICATION_MISSING",
        "territory": "RELATIONSHIP_TERRITORY_MISSING",
        "regulatory_source_id": "RELATIONSHIP_REGULATORY_SOURCE_MISSING",
        "rights_basis": "RIGHTS_BASIS_MISSING",
    }
    for field, reason in required.items():
        if exposure.get(field) in (None, ""):
            reasons.append(reason)

    security_comparisons = (
        ("relationship_issuer_id", "issuer_id", "RELATIONSHIP_ISSUER_MISMATCH"),
        ("relationship_security_id", "security_id", "RELATIONSHIP_SECURITY_MISMATCH"),
    )
    for relationship_field, exposure_field, reason in security_comparisons:
        value = exposure.get(relationship_field)
        if value not in (None, "") and value != exposure.get(exposure_field):
            reasons.append(reason)

    comparisons = (
        ("device_id", "device_id", "RELATIONSHIP_DEVICE_MISMATCH"),
        ("applicant", "applicant", "RELATIONSHIP_APPLICANT_MISMATCH"),
        ("submission_id", "submission_id", "RELATIONSHIP_SUBMISSION_MISMATCH"),
        ("indication_id", "indication_id", "RELATIONSHIP_INDICATION_MISMATCH"),
        ("territory", "territory", "RELATIONSHIP_TERRITORY_MISMATCH"),
        ("regulatory_source_id", "source_id", "RELATIONSHIP_REGULATORY_SOURCE_MISMATCH"),
    )
    for exposure_field, event_field, reason in comparisons:
        value = exposure.get(exposure_field)
        if value not in (None, "") and value != event.get(event_field):
            reasons.append(reason)

    rights = str(exposure["rights_state"])
    basis = exposure.get("rights_basis")
    if basis not in (None, "") and basis not in RIGHTS_BASIS_BY_STATE[rights]:
        reasons.append("RIGHTS_BASIS_INCONSISTENT")
    if rights == "licensed" and exposure.get("license_term_id") in (None, ""):
        reasons.append("LICENSE_TERM_UNRESOLVED")
    return reasons


def _materiality_reasons(exposure: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    required = {
        "materiality_source_id": "MATERIALITY_SOURCE_MISSING",
        "materiality_basis": "MATERIALITY_BASIS_MISSING",
        "materiality_issuer_id": "MATERIALITY_ISSUER_MISSING",
        "materiality_security_id": "MATERIALITY_SECURITY_MISSING",
        "materiality_relationship_id": "MATERIALITY_RELATIONSHIP_MISSING",
    }
    for field, reason in required.items():
        if exposure.get(field) in (None, ""):
            reasons.append(reason)

    comparisons = (
        ("materiality_issuer_id", "issuer_id", "MATERIALITY_ISSUER_MISMATCH"),
        ("materiality_security_id", "security_id", "MATERIALITY_SECURITY_MISMATCH"),
        ("materiality_relationship_id", "relationship_id", "MATERIALITY_RELATIONSHIP_MISMATCH"),
    )
    for materiality_field, exposure_field, reason in comparisons:
        value = exposure.get(materiality_field)
        if value not in (None, "") and value != exposure.get(exposure_field):
            reasons.append(reason)

    materiality = str(exposure["materiality_state"])
    basis = exposure.get("materiality_basis")
    if basis not in (None, "") and basis not in MATERIALITY_BASIS_BY_STATE[materiality]:
        reasons.append("MATERIALITY_BASIS_INCONSISTENT")
    return reasons


def _expectations_state(
    options: Mapping[str, Any] | None,
    *,
    cutoff: datetime,
    issuer_id: str,
    security_id: str,
) -> tuple[dict[str, Any], bool]:
    if options is None:
        return (
            {
                "state": "UNAVAILABLE",
                "observed": False,
                "as_of": None,
                "source_id": None,
                "issuer_id": None,
                "security_id": None,
                "coverage": None,
                "latency": None,
                "can_change_native_event_probability": False,
                "use": "none",
            },
            False,
        )

    if not isinstance(options, Mapping):
        raise ValueError("options must be a mapping")
    _require(
        options,
        (
            "observation_state",
            "as_of",
            "source_id",
            "issuer_id",
            "security_id",
            "coverage",
            "latency",
        ),
        owner="options",
    )
    observed_at = _utc(str(options["as_of"]), field="options.as_of")
    if observed_at > cutoff:
        return (
            {
                "state": "WITHHELD_TEMPORAL",
                "observed": False,
                "as_of": None,
                "source_id": None,
                "issuer_id": None,
                "security_id": None,
                "coverage": None,
                "latency": None,
                "can_change_native_event_probability": False,
                "use": "none",
            },
            True,
        )

    options_issuer_id = str(options["issuer_id"])
    options_security_id = str(options["security_id"])
    coverage = str(options["coverage"])
    latency = str(options["latency"])
    observed = options.get("observation_state") == "observed"
    identity_qualified = (
        options_issuer_id == issuer_id
        and options_security_id == security_id
    )
    qualified = (
        observed
        and identity_qualified
        and coverage in OPTIONS_COVERAGE_STATES
        and latency in OPTIONS_LATENCY_STATES
    )
    if not qualified:
        return (
            {
                "state": "UNQUALIFIED",
                "observed": observed,
                "as_of": _iso(observed_at),
                "source_id": options["source_id"],
                "issuer_id": options_issuer_id,
                "security_id": options_security_id,
                "coverage": coverage,
                "latency": latency,
                "can_change_native_event_probability": False,
                "use": "none",
            },
            False,
        )
    return (
        {
            "state": "QUALIFIED_CONTEXT",
            "observed": True,
            "as_of": _iso(observed_at),
            "source_id": options["source_id"],
            "issuer_id": options_issuer_id,
            "security_id": options_security_id,
            "coverage": coverage,
            "latency": latency,
            "can_change_native_event_probability": False,
            "use": "expectations_reaction_and_timing_only",
        },
        False,
    )


def qualify_case(
    *,
    event: Mapping[str, Any],
    exposure: Mapping[str, Any],
    commercial: Mapping[str, Any],
    as_of: str,
    options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fail-closed research disposition for one device catalyst case."""
    _require(
        event,
        (
            "pathway",
            "decision_state",
            "public_at",
            "source_id",
            "device_id",
            "applicant",
            "submission_id",
            "indication_id",
            "territory",
        ),
        owner="event",
    )
    pathway = str(event["pathway"])
    decision = str(event["decision_state"])
    if pathway not in PATHWAY_STATES:
        raise ValueError("unsupported regulatory pathway")
    if decision not in PATHWAY_STATES[pathway]:
        raise ValueError(f"decision_state {decision!r} is invalid for {pathway}")

    cutoff = _utc(as_of, field="as_of")
    event_public_at = _utc(str(event["public_at"]), field="event.public_at")

    _require(
        exposure,
        (
            "issuer_id",
            "security_id",
            "rights_state",
            "materiality_state",
            "rights_public_at",
            "materiality_public_at",
        ),
        owner="exposure",
    )
    rights = str(exposure["rights_state"])
    materiality = str(exposure["materiality_state"])
    if rights not in RIGHTS_STATES:
        raise ValueError("rights_state is invalid")
    if materiality not in MATERIALITY_STATES:
        raise ValueError("materiality_state is invalid")
    rights_public_at = _utc(str(exposure["rights_public_at"]), field="exposure.rights_public_at")
    materiality_public_at = _utc(
        str(exposure["materiality_public_at"]),
        field="exposure.materiality_public_at",
    )

    readiness_state, readiness_gaps = _commercial_state(commercial)
    commercial_public_at = _utc(str(commercial["public_at"]), field="commercial.public_at")
    commercial_binding_reasons = _commercial_binding_reasons(event, exposure, commercial)
    if commercial_binding_reasons:
        commercial_state = "COMMERCIAL_UNQUALIFIED"
        commercial_gaps = ["COMMERCIAL_CASE_BINDING_UNRESOLVED", *commercial_binding_reasons]
    else:
        commercial_state = readiness_state
        commercial_gaps = readiness_gaps
    expectations, options_future = _expectations_state(
        options,
        cutoff=cutoff,
        issuer_id=str(exposure["issuer_id"]),
        security_id=str(exposure["security_id"]),
    )

    event_future = event_public_at > cutoff
    rights_future = rights_public_at > cutoff
    materiality_future = materiality_public_at > cutoff
    commercial_future = commercial_public_at > cutoff

    relationship_reasons = _relationship_reasons(event, exposure)
    materiality_reasons = _materiality_reasons(exposure)
    relationship_resolved = not relationship_reasons and rights != "unresolved"
    relationship_qualified = relationship_resolved and not rights_future
    materiality_resolved = not materiality_reasons and relationship_qualified

    if not relationship_qualified:
        commercial_state = "COMMERCIAL_UNQUALIFIED"
        commercial_gaps = list(dict.fromkeys([
            "COMMERCIAL_CASE_BINDING_UNRESOLVED",
            "COMMERCIAL_RELATIONSHIP_UNRESOLVED",
            *commercial_gaps,
        ]))

    effective_rights = rights if relationship_qualified else "unresolved"
    effective_materiality = (
        materiality
        if materiality_resolved and not materiality_future and not rights_future
        else "unknown"
    )

    positive = (pathway, decision) in POSITIVE_DECISIONS
    marketing_status = MARKETING_LABEL.get((pathway, decision), "NOT_POSITIVELY_AUTHORIZED")

    temporal_reasons: list[str] = []
    if event_future:
        temporal_reasons.append("EVENT_NOT_PUBLIC_AT_CUTOFF")
    if rights_future:
        temporal_reasons.append("RIGHTS_NOT_PUBLIC_AT_CUTOFF")
    if materiality_future:
        temporal_reasons.append("MATERIALITY_NOT_PUBLIC_AT_CUTOFF")
    if commercial_future:
        temporal_reasons.append("COMMERCIAL_NOT_PUBLIC_AT_CUTOFF")
    if options_future:
        temporal_reasons.append("OPTIONS_NOT_PUBLIC_AT_CUTOFF")

    reasons: list[str] = []
    if temporal_reasons:
        disposition = "WITHHELD_TEMPORAL"
        reasons.extend(temporal_reasons)
    elif effective_rights == "unresolved":
        disposition = "WITHHELD_IDENTITY_RIGHTS"
        if relationship_reasons:
            reasons.extend(["RELATIONSHIP_BINDING_UNRESOLVED", *relationship_reasons])
        else:
            reasons.append("ISSUER_RIGHTS_UNRESOLVED")
    elif not positive:
        disposition = "RESEARCHING_EVENT_OUTCOME"
        reasons.append("POSITIVE_MARKETING_DECISION_NOT_ESTABLISHED")
    elif effective_materiality == "unknown":
        disposition = "REVIEW_MATERIALITY"
        if materiality_reasons:
            reasons.extend(["MATERIALITY_EVIDENCE_UNRESOLVED", *materiality_reasons])
        else:
            reasons.append("ISSUER_MATERIALITY_UNRESOLVED")
    elif effective_materiality == "immaterial":
        disposition = "CONTEXT_ONLY_IMMATERIAL"
        reasons.append("EVENT_IMMATERIAL_TO_ISSUER")
    elif commercial_state != "COMMERCIAL_READY":
        disposition = "AUTHORIZED_AWAITING_COMMERCIAL_PROOF"
        reasons.extend(commercial_gaps)
    else:
        disposition = "CANDIDATE_REVIEW"

    event_view = {
        "pathway": pathway,
        "decision_state": None if event_future else decision,
        "marketing_status": None if event_future else marketing_status,
        "knowledge_state": "WITHHELD_TEMPORAL" if event_future else "PUBLIC_AT_CUTOFF",
        "public_at": None if event_future else _iso(event_public_at),
        "source_id": None if event_future else event["source_id"],
        "device_id": event["device_id"],
        "applicant": event["applicant"],
        "submission_id": event["submission_id"],
        "indication_id": event["indication_id"],
        "territory": event["territory"],
        "positive_decision": None if event_future else positive,
    }

    if rights_future:
        relationship_view = {
            "state": "WITHHELD_TEMPORAL",
            "relationship_id": None,
            "source_id": None,
            "public_at": None,
            "rights_basis": None,
            "license_term_id": None,
            "territory": None,
            "bound_case": None,
        }
    elif relationship_resolved:
        relationship_view = {
            "state": "RESOLVED",
            "relationship_id": exposure["relationship_id"],
            "source_id": exposure["rights_source_id"],
            "public_at": _iso(rights_public_at),
            "rights_basis": exposure["rights_basis"],
            "license_term_id": exposure.get("license_term_id"),
            "territory": exposure["territory"],
            "bound_case": {
                "issuer_id": exposure["relationship_issuer_id"],
                "security_id": exposure["relationship_security_id"],
                "device_id": exposure["device_id"],
                "applicant": exposure["applicant"],
                "submission_id": exposure["submission_id"],
                "indication_id": exposure["indication_id"],
                "regulatory_source_id": None if event_future else exposure["regulatory_source_id"],
            },
        }
    else:
        relationship_view = {
            "state": "UNRESOLVED",
            "relationship_id": None,
            "source_id": exposure.get("rights_source_id") or None,
            "public_at": _iso(rights_public_at),
            "rights_basis": None,
            "license_term_id": None,
            "territory": None,
            "bound_case": None,
        }

    if materiality_future:
        materiality_view = {
            "state": "WITHHELD_TEMPORAL",
            "source_id": None,
            "public_at": None,
            "basis": None,
        }
    elif materiality_resolved:
        materiality_view = {
            "state": "RESOLVED",
            "source_id": exposure["materiality_source_id"],
            "public_at": _iso(materiality_public_at),
            "basis": exposure["materiality_basis"],
        }
    else:
        materiality_view = {
            "state": "UNRESOLVED",
            "source_id": exposure.get("materiality_source_id") or None,
            "public_at": _iso(materiality_public_at),
            "basis": None,
        }

    if commercial_future:
        commercial_view = {
            "state": "WITHHELD_TEMPORAL",
            "gaps": [],
            "source_id": None,
            "public_at": None,
        }
    else:
        commercial_view = {
            "state": commercial_state,
            "gaps": commercial_gaps,
            "source_id": commercial["source_id"],
            "public_at": _iso(commercial_public_at),
        }

    return {
        "schema": "catalyst.medtech.reference_disposition/v1",
        "as_of": _iso(cutoff),
        "event": event_view,
        "exposure": {
            "issuer_id": exposure["issuer_id"],
            "security_id": exposure["security_id"],
            "rights_state": effective_rights,
            "materiality_state": effective_materiality,
            "relationship": relationship_view,
            "materiality_evidence": materiality_view,
        },
        "commercial": commercial_view,
        "expectations": expectations,
        "disposition": disposition,
        "reasons": reasons,
        "native_event_probability": None,
        "conditional_equity_values": None,
        "recommendation_eligible": False,
        "recommendation": None,
        "authority": "RESEARCH_REFERENCE_ONLY",
    }


def apply_market_revision(
    case: Mapping[str, Any],
    *,
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Add identified cutoff-qualified market context without rewriting case evidence."""
    if not isinstance(case, Mapping):
        raise ValueError("case must be a mapping")
    if not isinstance(observation, Mapping):
        raise ValueError("market_observation must be a mapping")
    _require(
        observation,
        ("security_id", "source_id", "reference_price", "observed_at"),
        owner="market_observation",
    )
    exposure_view = case.get("exposure")
    if not isinstance(exposure_view, Mapping):
        raise ValueError("case exposure is required")
    case_security_id = str(exposure_view.get("security_id") or "")
    if not case_security_id:
        raise ValueError("case exposure security_id is required")
    observation_security_id = str(observation["security_id"])
    if observation_security_id != case_security_id:
        raise ValueError("market_observation.security_id must match case exposure security_id")
    reference_price = observation["reference_price"]
    if not isinstance(reference_price, (int, float)) or isinstance(reference_price, bool):
        raise ValueError("reference_price must be finite positive")
    try:
        normalized_price = float(reference_price)
    except (OverflowError, ValueError) as exc:
        raise ValueError("reference_price must be finite positive") from exc
    if not math.isfinite(normalized_price) or normalized_price <= 0:
        raise ValueError("reference_price must be finite positive")
    case_cutoff = _utc(str(case.get("as_of") or ""), field="case.as_of")
    observed = _utc(str(observation["observed_at"]), field="market_observation.observed_at")
    if observed > case_cutoff:
        raise ValueError("market_observation.observed_at must be no later than case.as_of")
    result = deepcopy(dict(case))
    before_event = deepcopy(result.get("event"))
    before_exposure = deepcopy(result.get("exposure"))
    before_commercial = deepcopy(result.get("commercial"))
    result["market_revision"] = {
        "security_id": observation_security_id,
        "source_id": observation["source_id"],
        "reference_price": normalized_price,
        "observed_at": _iso(observed),
        "effect": "PRICE_CONTEXT_ONLY",
    }
    if result.get("event") != before_event:
        raise AssertionError("market revision must not mutate regulatory evidence")
    if result.get("exposure") != before_exposure:
        raise AssertionError("market revision must not mutate rights or materiality evidence")
    if result.get("commercial") != before_commercial:
        raise AssertionError("market revision must not mutate commercial evidence")
    return result
