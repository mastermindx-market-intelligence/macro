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
    if identity_cut_date > cutoff_time.date():
        raise ContractError("identity_cut_date exceeds generation cutoff")

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


def compose_wmn_owner_inputs(
    *,
    events: object,
    input_cut: object,
    issuer_master: object,
    alias_table: object,
    identity_cut_date: object,
    identity_observed_at: object,
    coverage: object,
) -> dict[str, Any]:
    """Compose the native owners' selected cut for the existing WMN publisher.

    The caller must independently admit Company events and the two Data OS
    sources, and bind these readers to the supplied cut. This pure projection
    does not attest those admissions, sample acceptance clocks, load a "latest"
    file, or publish anything. In particular, declared Data OS digests are not
    authenticated by passing an in-memory reader.

    Identity is recomputed with the canonical readers instead of accepting a
    caller-authored identity projection. The existing v2 validator owns the
    complete cut, event hash, coverage, clock and authority checks.
    """
    from engine.biocatalyst.what_matters_next import validate_current_wmn_inputs
    from engine.company_intelligence.contracts import (
        CATALYST_SOURCE_FACT_AUTHORITY,
        ContractError,
    )
    from lib.dataos.identity import IssuerMaster, VendorAliasTable

    if not isinstance(issuer_master, IssuerMaster):
        raise ContractError("issuer_master must be the canonical IssuerMaster reader")
    if not isinstance(alias_table, VendorAliasTable):
        raise ContractError("alias_table must be the canonical VendorAliasTable reader")
    if not isinstance(input_cut, dict) or "cutoff" not in input_cut:
        raise ContractError("input_cut must supply the owner-selected cutoff")
    if not isinstance(events, list) or len(events) > 100_000:
        raise ContractError("wmn_inputs events must be a bounded list")
    identities = {}
    for event in events:
        owner = validate_company_catalyst_event(
            event, generation_cutoff=input_cut["cutoff"]
        )
        identities[owner["event_id"]] = resolve_current_event_identity(
            owner,
            issuer_master=issuer_master,
            alias_table=alias_table,
            identity_cut_date=identity_cut_date,
            identity_observed_at=identity_observed_at,
            generation_cutoff=input_cut["cutoff"],
        )
    return validate_current_wmn_inputs({
        "contract_id": "biocatalyst_wmn_inputs.v2",
        "schema_version": "2.0.0",
        "input_cut": input_cut,
        "events": events,
        "relationships": [],
        "identity_projection": identities,
        "coverage": coverage,
        "authority": CATALYST_SOURCE_FACT_AUTHORITY,
    })


def compose_wmn_snapshot_inputs(
    *, events: object, input_cut: object, identity_read: object,
    identity_cut_date: object, coverage: object,
) -> dict[str, Any]:
    """Bind an existing native DataOS read to the current-only WMN cut.

    Consumes the incumbent file reader's result (including R26 promotion's
    readback). No read, promotion, source admission or publication is performed.
    The current-issuer reader consumes security_master.parquet, as specified by
    the existing R1B contract; issuer_master.parquet alone cannot bind its rows.
    The exact nanosecond read clock is checked before conservative upward
    conversion to the existing WMN wire's whole-second precision. Source authenticity and
    Company/source-purpose admission remain upstream obligations.
    """
    from datetime import datetime, timedelta, timezone
    from hashlib import sha256
    import json
    from engine.company_intelligence.contracts import ContractError
    from engine.entry_radar.replay.identity_observation_snapshot import IdentitySnapshotRead
    from lib.dataos.identity import (
        IssuerMaster, ReferenceReadReceipt, ReferenceSnapshot,
        validate_reference_snapshot,
    )

    if type(identity_read) is not IdentitySnapshotRead:
        raise ContractError("identity_read must be the native IdentitySnapshotRead")
    snapshot, receipt = identity_read.snapshot, identity_read.receipt
    if type(snapshot) is not ReferenceSnapshot or type(receipt) is not ReferenceReadReceipt:
        raise ContractError("identity_read requires native snapshot and receipt")
    checked_receipt = ReferenceReadReceipt.from_record(receipt.as_record())
    artifacts = dict(snapshot.artifact_bytes)
    if len(artifacts) != len(snapshot.artifact_bytes):
        raise ContractError("native snapshot has duplicate artifacts")
    records = json.loads(snapshot.master_json)
    validate_reference_snapshot(
        snapshot.receipt_bytes, artifacts, snapshot.receipt_bytes,
        alias_records=json.loads(snapshot.alias_json), master_records=records,
    )
    context = json.loads(snapshot.receipt_bytes)
    publication = context["publication"]
    if (checked_receipt.receipt_sha256 != sha256(snapshot.receipt_bytes).hexdigest()
            or checked_receipt.generation_id != publication["generation_id"]
            or checked_receipt.history_prefix_sha256 != publication["history_sha256"]
            or dict(checked_receipt.artifact_sha256) != {
                name: sha256(raw).hexdigest() for name, raw in artifacts.items()}):
        raise ContractError("native read receipt does not bind snapshot")
    history = context["identity_observations"]
    last = history["attempts"][-1] if history["attempts"] else history["anchor"]
    completed_ns = int(checked_receipt.read_completed_at_utc_ns)
    if completed_ns < int(last["owner_read_completed_at_utc_ns"]):
        raise ContractError("native read precedes owner observation")
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def clock_ns(value, field):
        import re
        if isinstance(value, str) and any(
                any(c != "0" for c in fraction)
                for fraction in re.findall(r"[.,](\d+)", value)):
            raise ContractError("native WMN cut clocks require whole seconds")
        try:
            _, instant = _exact_utc_timestamp(value, field=field)
        except ValueError as exc:
            raise ContractError(str(exc)) from exc
        delta = instant - epoch
        # The retained WMN v2 serializer emits whole seconds. Refuse cuts
        # whose normalization would silently change their selected clocks.
        if delta.microseconds:
            raise ContractError("native WMN cut clocks require whole seconds")
        return (delta.days * 86400 + delta.seconds) * 1_000_000_000

    if not isinstance(input_cut, dict) or not isinstance(input_cut.get("members"), list):
        raise ContractError("input_cut must supply native members")
    if completed_ns > clock_ns(input_cut.get("cutoff"), "input_cut.cutoff"):
        raise ContractError("native read exceeds input_cut cutoff")
    for contract, artifact in (("dataos_issuer_master.current", "security_master.parquet"),
                               ("dataos_vendor_aliases.current", "vendor_aliases.parquet")):
        members = [m for m in input_cut["members"]
                   if isinstance(m, dict) and m.get("contract_id") == contract]
        if len(members) != 1 or members[0].get("sha256") != sha256(artifacts[artifact]).hexdigest():
            raise ContractError("native DataOS member digest does not bind reader bytes")
        for field in ("observed_at", "accepted_at"):
            if clock_ns(members[0].get(field), field) < completed_ns:
                raise ContractError("native DataOS member clock precedes actual read")
    ids = [r.get("security_id") for r in records]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        raise ContractError("native security master requires unique nonempty security IDs")
    observed = epoch + timedelta(seconds=(completed_ns + 999_999_999) // 1_000_000_000)
    return compose_wmn_owner_inputs(
        events=events, input_cut=input_cut,
        issuer_master=IssuerMaster.from_records(records), alias_table=identity_read.alias_table(),
        identity_cut_date=identity_cut_date,
        identity_observed_at=observed.isoformat().replace("+00:00", "Z"), coverage=coverage,
    )
