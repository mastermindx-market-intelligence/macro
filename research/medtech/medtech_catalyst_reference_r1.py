"""Research-only MedTech Catalyst Intelligence reference contract.

This module does not predict FDA outcomes, rank securities, or issue recommendations.
It pins distinctions that a later production implementation must preserve:
regulatory pathway/decision, public-knowledge time, issuer rights/materiality,
commercial readiness, market expectations, and recommendation admission.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
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
        ("manufacturing_readiness", "launch_readiness", "coverage_state", "adoption_state"),
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


def _expectations_state(options: Mapping[str, Any] | None) -> dict[str, Any]:
    if not options:
        return {
            "state": "UNAVAILABLE",
            "observed": False,
            "can_change_native_event_probability": False,
            "use": "none",
        }
    observed = options.get("observation_state") == "observed"
    required = ("as_of", "source_id", "coverage", "latency")
    complete = all(options.get(name) not in (None, "") for name in required)
    if not observed or not complete:
        return {
            "state": "UNQUALIFIED",
            "observed": observed,
            "can_change_native_event_probability": False,
            "use": "none",
        }
    return {
        "state": "QUALIFIED_CONTEXT",
        "observed": True,
        "can_change_native_event_probability": False,
        "use": "expectations_reaction_and_timing_only",
    }


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
        ("pathway", "decision_state", "public_at", "source_id", "device_id", "applicant"),
        owner="event",
    )
    pathway = str(event["pathway"])
    decision = str(event["decision_state"])
    if pathway not in PATHWAY_STATES:
        raise ValueError("unsupported regulatory pathway")
    if decision not in PATHWAY_STATES[pathway]:
        raise ValueError(f"decision_state {decision!r} is invalid for {pathway}")

    cutoff = _utc(as_of, field="as_of")
    public_at = _utc(str(event["public_at"]), field="event.public_at")
    future_knowledge = public_at > cutoff

    _require(exposure, ("issuer_id", "rights_state", "materiality_state"), owner="exposure")
    rights = str(exposure["rights_state"])
    materiality = str(exposure["materiality_state"])
    if rights not in RIGHTS_STATES:
        raise ValueError("rights_state is invalid")
    if materiality not in MATERIALITY_STATES:
        raise ValueError("materiality_state is invalid")

    commercial_state, commercial_gaps = _commercial_state(commercial)
    positive = (pathway, decision) in POSITIVE_DECISIONS
    marketing_status = MARKETING_LABEL.get((pathway, decision), "NOT_POSITIVELY_AUTHORIZED")

    reasons: list[str] = []
    if future_knowledge:
        disposition = "WITHHELD_TEMPORAL"
        reasons.append("EVENT_NOT_PUBLIC_AT_CUTOFF")
    elif rights == "unresolved":
        disposition = "WITHHELD_IDENTITY_RIGHTS"
        reasons.append("ISSUER_RIGHTS_UNRESOLVED")
    elif not positive:
        disposition = "RESEARCHING_EVENT_OUTCOME"
        reasons.append("POSITIVE_MARKETING_DECISION_NOT_ESTABLISHED")
    elif materiality == "unknown":
        disposition = "REVIEW_MATERIALITY"
        reasons.append("ISSUER_MATERIALITY_UNRESOLVED")
    elif materiality == "immaterial":
        disposition = "CONTEXT_ONLY_IMMATERIAL"
        reasons.append("EVENT_IMMATERIAL_TO_ISSUER")
    elif commercial_state != "COMMERCIAL_READY":
        disposition = "AUTHORIZED_AWAITING_COMMERCIAL_PROOF"
        reasons.extend(commercial_gaps)
    else:
        disposition = "CANDIDATE_REVIEW"

    expectations = _expectations_state(options)
    return {
        "schema": "catalyst.medtech.reference_disposition/v1",
        "as_of": cutoff.isoformat().replace("+00:00", "Z"),
        "event": {
            "pathway": pathway,
            "decision_state": decision,
            "marketing_status": marketing_status,
            "public_at": public_at.isoformat().replace("+00:00", "Z"),
            "source_id": event["source_id"],
            "device_id": event["device_id"],
            "applicant": event["applicant"],
            "positive_decision": positive,
        },
        "exposure": {
            "issuer_id": exposure["issuer_id"],
            "rights_state": rights,
            "materiality_state": materiality,
        },
        "commercial": {"state": commercial_state, "gaps": commercial_gaps},
        "expectations": expectations,
        "disposition": disposition,
        "reasons": reasons,
        "native_event_probability": None,
        "conditional_equity_values": None,
        "recommendation_eligible": False,
        "recommendation": None,
        "authority": "RESEARCH_REFERENCE_ONLY",
    }


def apply_market_revision(case: Mapping[str, Any], *, reference_price: float, observed_at: str) -> dict[str, Any]:
    """Add market context without rewriting regulatory or commercial evidence."""
    if not isinstance(reference_price, (int, float)) or reference_price <= 0:
        raise ValueError("reference_price must be positive")
    _utc(observed_at, field="observed_at")
    result = deepcopy(dict(case))
    before = deepcopy(result.get("event"))
    result["market_revision"] = {
        "reference_price": float(reference_price),
        "observed_at": observed_at,
        "effect": "PRICE_CONTEXT_ONLY",
    }
    if result.get("event") != before:
        raise AssertionError("market revision must not mutate regulatory evidence")
    return result
