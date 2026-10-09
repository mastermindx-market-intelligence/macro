"""Pure BioCatalyst consumer of Company Intelligence non-fiscal source events.

This adapter allocates no event, company, issuer, security, asset, or relationship
identity. It validates the Company Intelligence owner wire at the selected
composite cut and carries that identity into Bio's generation input.
"""
from __future__ import annotations

from typing import Any

from engine.company_intelligence.contracts import validate_company_catalyst_event


_INPUT_KEYS = {
    "event_fact_ref", "event_family", "event_revision_ref", "revision_is_current",
    "occurrence", "timing", "company_id", "issuer_cik", "document_refs",
    "public_evidence", "asset_mentions", "relationship_claims", "authority",
}


def project_company_event_input(
    event: object,
    *,
    generation_cutoff: object,
) -> dict[str, Any]:
    """Carry one validated owner event into the composed Bio input cut."""
    owner = validate_company_catalyst_event(
        event, generation_cutoff=generation_cutoff
    )
    projected = {
        "event_fact_ref": owner["event_id"],
        "event_family": owner["event_family"],
        "event_revision_ref": owner["revision_ref"],
        "revision_is_current": owner["revision_is_current"],
        "occurrence": owner["occurrence"],
        "timing": owner["timing"],
        "company_id": owner["company_id"],
        "issuer_cik": owner["issuer_cik"],
        "document_refs": list(owner["document_refs"]),
        "public_evidence": list(owner["public_evidence"]),
        "asset_mentions": list(owner["asset_mentions"]),
        "relationship_claims": list(owner["relationship_claims"]),
        "authority": {
            "classification": owner["authority"]["classification"],
            "decision_authority": False,
            "allowed_uses": list(owner["authority"]["allowed_uses"]),
            "forbidden_uses": list(owner["authority"]["forbidden_uses"]),
        },
    }
    assert set(projected) == _INPUT_KEYS
    return projected


def _exact_utc_timestamp(value: object, *, field: str) -> tuple[str, "datetime"]:
    from datetime import datetime, timezone

    if not isinstance(value, str) or "T" not in value:
        raise ValueError(f"{field} requires an explicit timezone")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} requires an explicit timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} requires an explicit timezone")
    utc = parsed.astimezone(timezone.utc)
    return utc.isoformat(timespec="seconds").replace("+00:00", "Z"), utc


def resolve_current_event_identity(
    event: object,
    *,
    issuer_master: object,
    alias_table: object,
    identity_cut_date: object,
    identity_observed_at: object,
    generation_cutoff: object,
) -> dict[str, Any]:
    """Resolve one Company event to the existing CURRENT issuer/security owners.

    The output is a generation-input projection, not a historical identity
    claim and not a security allocator. Multiple issuers/share classes are
    retained rather than ranked or collapsed.
    """
    from datetime import date, datetime
    from engine.company_intelligence.contracts import ContractError
    from lib.dataos.identity import IssuerMaster, VendorAliasTable

    if not isinstance(issuer_master, IssuerMaster):
        raise ContractError("issuer_master must be the canonical IssuerMaster reader")
    if not isinstance(alias_table, VendorAliasTable):
        raise ContractError("alias_table must be the canonical VendorAliasTable reader")
    if not isinstance(identity_cut_date, date) or isinstance(identity_cut_date, datetime):
        raise ContractError("identity_cut_date must be a calendar date")

    owner = validate_company_catalyst_event(
        event, generation_cutoff=generation_cutoff
    )
    try:
        observed_literal, observed_time = _exact_utc_timestamp(
            identity_observed_at, field="identity_observed_at"
        )
        _cutoff_literal, cutoff_time = _exact_utc_timestamp(
            generation_cutoff, field="generation_cutoff"
        )
    except ValueError as exc:
        raise ContractError(str(exc)) from exc
    if observed_time > cutoff_time:
        raise ContractError("identity_observed_at exceeds generation cutoff")

    issuer_ids = issuer_master.issuers_for_cik(owner["issuer_cik"])
    known_security_ids = {row.security_id for row in issuer_master.rows}
    issuers: list[dict[str, Any]] = []
    for issuer_id in issuer_ids:
        securities: list[dict[str, Any]] = []
        for security_id in issuer_master.securities_of_issuer(issuer_id):
            if security_id not in known_security_ids:
                raise ContractError("identity projection referenced an unknown security")
            if issuer_master.security_state_of(security_id) is not None:
                raise ContractError("identity projection referenced a superseded security")
            listing_key = issuer_master.listing_key_of_security(security_id)
            if listing_key is None:
                raise ContractError("identity projection security has no current listing key")
            display_symbol = alias_table.vendor_symbol_for(
                "store", security_id, identity_cut_date
            )
            securities.append({
                "security_id": security_id,
                "listing_key": listing_key,
                "display_symbol": display_symbol,
                "symbol_observed_on": identity_cut_date.isoformat(),
                "state": "active",
            })
        issuers.append({
            "issuer_id": issuer_id,
            "securities": securities,
        })

    state = "unresolved" if not issuers else ("resolved" if len(issuers) == 1 else "ambiguous")
    return {
        "state": state,
        "company_id": owner["company_id"],
        "issuer_cik": owner["issuer_cik"],
        "identity_scope": "current_only",
        "identity_observed_at": observed_literal,
        "identity_cut_date": identity_cut_date.isoformat(),
        "issuers": issuers,
    }
