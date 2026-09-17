"""Pure What Matters Next composition over already-admitted owner projections.

The first executable slice intentionally composes issuer-disclosure Company
Intelligence events with CURRENT Data OS issuer/security identity.  It does not
allocate event/issuer/security/asset/relationship identities and does not invent
probability, materiality, historical-response or incorporation estimates.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import quote

from engine.biocatalyst.company_event_adapter import project_company_event_input
from engine.biocatalyst.research_priority import classify_research_priority
from engine.company_intelligence.contracts import ContractError

_ROW_KEYS = {
    "row_key", "event_fact_ref", "event_family", "event_revision_ref",
    "revision_is_current", "occurrence", "timing", "issuer", "assets",
    "relationships", "economic_exposure_state", "evidence", "revision_summary",
    "research_priority", "probability", "materiality", "historical_response",
    "incorporation", "missingness", "links",
}
_IDENTITY_KEYS = {
    "state", "company_id", "issuer_cik", "identity_scope",
    "identity_observed_at", "identity_cut_date", "issuers",
}


def _utc(value: object, *, field: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or "T" not in value:
        raise ContractError(f"{field} requires an explicit timezone")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{field} requires an explicit timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{field} requires an explicit timezone")
    utc = parsed.astimezone(timezone.utc)
    return utc.isoformat(timespec="seconds").replace("+00:00", "Z"), utc


def _estimate_slot(kind: str) -> dict[str, Any]:
    return {
        "state": "NOT_ESTIMABLE",
        "value": None,
        "reason_code": f"{kind.upper()}_OWNER_NOT_ADMITTED",
        "method_ref": None,
        "as_of": None,
        "evidence_refs": [],
    }


def _validate_identity_projection(
    identity: object,
    *,
    company_id: str,
    issuer_cik: str,
    evaluation_cutoff: object,
) -> dict[str, Any]:
    if not isinstance(identity, Mapping) or set(identity) != _IDENTITY_KEYS:
        raise ContractError("identity_projection shape invalid")
    state = identity.get("state")
    if state not in {"resolved", "unresolved", "ambiguous"}:
        raise ContractError("identity_projection state invalid")
    if identity.get("company_id") != company_id or identity.get("issuer_cik") != issuer_cik:
        raise ContractError("identity_projection does not bind the selected company event")
    if identity.get("identity_scope") != "current_only":
        raise ContractError("identity_projection must be current_only")
    observed_literal, observed = _utc(
        identity.get("identity_observed_at"), field="identity_observed_at"
    )
    _cutoff_literal, cutoff = _utc(evaluation_cutoff, field="evaluation_cutoff")
    if observed > cutoff:
        raise ContractError("identity_observed_at exceeds evaluation cutoff")
    cut_date = identity.get("identity_cut_date")
    if not isinstance(cut_date, str) or len(cut_date) != 10:
        raise ContractError("identity_cut_date invalid")
    issuers = identity.get("issuers")
    if not isinstance(issuers, list):
        raise ContractError("identity_projection issuers must be a list")
    if state == "resolved" and len(issuers) != 1:
        raise ContractError("resolved identity requires exactly one issuer")
    if state == "unresolved" and issuers:
        raise ContractError("unresolved identity must not carry issuer candidates")
    if state == "ambiguous" and len(issuers) < 2:
        raise ContractError("ambiguous identity requires multiple candidates")
    return {**dict(identity), "identity_observed_at": observed_literal}


def _admitted_issuer(identity: Mapping[str, Any], *, company_id: str) -> dict[str, Any]:
    state = identity["state"]
    if state != "resolved":
        return {
            "state": state,
            "issuer_id": None,
            "company_id": company_id,
            "relationship_role": None,
            "identity_scope": "unavailable",
            "identity_observed_at": identity["identity_observed_at"],
            "securities": [],
        }
    raw = identity["issuers"][0]
    if not isinstance(raw, Mapping) or set(raw) != {"issuer_id", "securities"}:
        raise ContractError("resolved issuer projection shape invalid")
    issuer_id = raw.get("issuer_id")
    securities = raw.get("securities")
    if not isinstance(issuer_id, str) or not issuer_id.startswith("ISS:"):
        raise ContractError("resolved issuer_id invalid")
    if not isinstance(securities, list) or not securities:
        raise ContractError("resolved issuer must retain at least one active security")
    rendered: list[dict[str, Any]] = []
    for security in securities:
        if not isinstance(security, Mapping) or set(security) != {
            "security_id", "listing_key", "display_symbol", "symbol_observed_on", "state"
        }:
            raise ContractError("security projection shape invalid")
        if security.get("state") != "active":
            raise ContractError("current WMN row cannot navigate a non-active security")
        rendered.append(dict(security))
    return {
        "state": "resolved",
        "issuer_id": issuer_id,
        "company_id": company_id,
        "relationship_role": "issuer",
        "identity_scope": "current_only",
        "identity_observed_at": identity["identity_observed_at"],
        "securities": rendered,
    }


def _stock_links(issuer: Mapping[str, Any]) -> list[dict[str, str]]:
    if issuer.get("state") != "resolved":
        return []
    links: list[dict[str, str]] = []
    for security in issuer.get("securities", []):
        symbol = security.get("display_symbol")
        if not isinstance(symbol, str) or not symbol:
            continue
        links.append({
            "security_id": security["security_id"],
            "relationship_role": "issuer",
            "href": f"stock.html?ticker={quote(symbol, safe='')}",
        })
    return links


def compose_company_event_rows(
    event: object,
    *,
    identity_projection: object,
    source_health: str,
    evaluation_cutoff: object,
    anchor_date: object,
) -> list[dict[str, Any]]:
    """Compose the first bounded company-disclosure WMN row.

    Ambiguous/unresolved CIK joins remain one unjoined row: candidate issuers are
    retained in the generation's identity projection, not promoted into admitted
    stock links.  A single resolved issuer retains every active share class.
    """
    owner = project_company_event_input(event, generation_cutoff=evaluation_cutoff)
    identity = _validate_identity_projection(
        identity_projection,
        company_id=owner["company_id"],
        issuer_cik=owner["issuer_cik"],
        evaluation_cutoff=evaluation_cutoff,
    )
    issuer = _admitted_issuer(identity, company_id=owner["company_id"])
    rp_identity_state = "resolved" if issuer["state"] == "resolved" else "unresolved"
    priority_input = {
        "event_fact_ref": owner["event_fact_ref"],
        "exposure_ref": None,
        "revision_is_current": owner["revision_is_current"],
        "occurrence": owner["occurrence"],
        "source_health": source_health,
        "identity_state": rp_identity_state,
        "timing_state": owner["timing"]["state"],
        "lower_date": owner["timing"]["lower_date"],
        "upper_date": owner["timing"]["upper_date"],
        # The current event port does not yet attest which revision was material.
        "last_material_revision_known_at": None,
    }
    priority = classify_research_priority(
        priority_input,
        evaluation_cutoff=evaluation_cutoff,
        anchor_date=anchor_date,
    )

    identity_missing = []
    if issuer["state"] == "unresolved":
        identity_missing = ["CURRENT_ISSUER_UNRESOLVED"]
    elif issuer["state"] == "ambiguous":
        identity_missing = ["AMBIGUOUS_CURRENT_CIK"]
    source_missing = [] if source_health == "current" else ["SOURCE_NOT_CURRENT"]
    estimate_reasons = [
        "PROBABILITY_OWNER_NOT_ADMITTED",
        "MATERIALITY_OWNER_NOT_ADMITTED",
        "HISTORICAL_RESPONSE_OWNER_NOT_ADMITTED",
        "INCORPORATION_OWNER_NOT_ADMITTED",
    ]
    row = {
        "row_key": {
            "event_fact_ref": owner["event_fact_ref"],
            "issuer_id": issuer["issuer_id"],
        },
        "event_fact_ref": owner["event_fact_ref"],
        "event_family": owner["event_family"],
        "event_revision_ref": owner["event_revision_ref"],
        "revision_is_current": owner["revision_is_current"],
        "occurrence": owner["occurrence"],
        "timing": dict(owner["timing"]),
        "issuer": issuer,
        "assets": [],
        "relationships": [],
        "economic_exposure_state": "unresolved",
        "evidence": [],
        "revision_summary": {
            "revision_ref": owner["event_revision_ref"],
            "revision_is_current": owner["revision_is_current"],
            "last_material_revision_known_at": None,
        },
        "research_priority": priority,
        "probability": _estimate_slot("probability"),
        "materiality": _estimate_slot("materiality"),
        "historical_response": _estimate_slot("historical_response"),
        "incorporation": _estimate_slot("incorporation"),
        "missingness": {
            "source": source_missing,
            "identity": identity_missing,
            "asset": ["ASSET_PORT_NOT_ADMITTED"],
            "economic": ["ECONOMIC_EXPOSURE_UNRESOLVED"],
            "estimates": estimate_reasons,
        },
        "links": {"stock_research": _stock_links(issuer)},
    }
    if set(row) != _ROW_KEYS:
        raise AssertionError("WMN row contract drift")
    return [row]
