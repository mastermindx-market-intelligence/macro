"""URL-only catalyst source context over the existing document/filing owners.

This is an offline, owner-internal projection. It is not an intake endpoint,
collector, rights grant, source-admission store, or public evidence upload API.
Callers must supply admitted owner records from one selected input cut. The
projection adds no historical-research, semantic-support, or decision authority.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping, Sequence

from engine.fundamental_forensics.disclosure_diff import DisclosureDocument, normalize_filing

from .contracts import (
    CATALYST_PUBLIC_EVIDENCE_CONTRACT,
    CATALYST_PUBLIC_EVIDENCE_MAX_BYTES,
    CATALYST_SOURCE_FACT_AUTHORITY,
    ContractError,
    _strict_knowledge_timestamp,
    validate_catalyst_public_evidence,
    validate_company_catalyst_event,
)
from .documents import DocumentRevisionChain, SourceSpan, text_span, verify_span


def _clock(value: object, *, field: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError(f"public evidence {field} is unavailable")
    # Retain subsecond knowledge when the existing owner supplies it.
    _literal, instant = _strict_knowledge_timestamp(value.isoformat(), field=field)
    return instant.isoformat().replace("+00:00", "Z")


def project_catalyst_public_evidence(
    *,
    event: object,
    document_chain: DocumentRevisionChain,
    source: DisclosureDocument,
    span: SourceSpan,
    generation_cutoff: object,
) -> dict[str, Any]:
    """Project a verified, current selected document as source context.

    The existing disclosure identity binds the public locator, exact body,
    accession and issuer. The Company owner binds that document and its span to
    the selected event. No fiscal workspace or financial parser is invoked.
    Excerpts remain null: public accessibility and a profile label do not grant
    this new port permission to redistribute source text.
    """
    owner = validate_company_catalyst_event(event, generation_cutoff=generation_cutoff)
    _literal, cutoff = _strict_knowledge_timestamp(generation_cutoff, field="generation_cutoff")
    if not owner["revision_is_current"] or owner["occurrence"] in {"cancelled", "withdrawn"}:
        raise ContractError("public evidence projection requires a current usable event revision")
    if (
        type(document_chain) is not DocumentRevisionChain
        or type(source) is not DisclosureDocument
        or type(span) is not SourceSpan
    ):
        raise ContractError("public evidence requires existing typed owner records")
    document = document_chain.latest()
    if (
        document_chain.event_id != owner["event_id"]
        or document.document_id not in owner["document_refs"]
        or document.document_id != source.document_id
        or document.document_id != span.document_id
        or type(span.document_version) is not int
        or document.revision != span.document_version
    ):
        raise ContractError("public evidence document/span does not bind the selected event revision")
    if document.superseded_by_document_id is not None or document.is_duplicate:
        raise ContractError("public evidence document is superseded or a duplicate delivery")
    if (
        document.filing_key is None
        or document.filing_key.cik != owner["issuer_cik"]
        or source.entity_cik != owner["issuer_cik"]
        or document.filing_key.accession != source.accession
    ):
        raise ContractError("public evidence filing identity does not bind the issuer")
    if (
        document.rights_state != "public_primary"
        or document.rights_profile != "rp_public_primary_v1"
        or span.rights_profile != document.rights_profile
    ):
        raise ContractError("public evidence source rights are not admitted for this projection")
    if document.source_class not in {"primary_filing", "issuer_release"}:
        raise ContractError("public evidence document source class is not admitted")
    if document.holds_bytes is not True or not isinstance(source.raw_source, str):
        raise ContractError("public evidence retained source bytes are unavailable")
    body = source.raw_source.encode("utf-8")
    if (
        not 0 < len(body) <= CATALYST_PUBLIC_EVIDENCE_MAX_BYTES
        or type(document.content_bytes) is not int
        or document.content_bytes != len(body)
        or sha256(body).hexdigest() != document.content_sha256
        or source.source_sha256 != document.content_sha256
    ):
        raise ContractError("public evidence document bytes do not reproduce owner hashes")

    # Replay the SAME existing allocator: URL/body metadata substitution must
    # not retain an older admitted document ID. This allocates no new authority.
    try:
        replay = normalize_filing({
            "accession": source.accession, "entity_cik": source.entity_cik,
            "form": source.form, "filed_at": source.filed_at,
            "report_date": source.report_date, "source_url": source.source_url,
            "content_type": source.content_type, "content": source.raw_source,
        })
    except (TypeError, ValueError, KeyError) as exc:
        raise ContractError("public evidence disclosure identity cannot be replayed") from exc
    if replay.document_id != source.document_id or replay.source_sha256 != document.content_sha256:
        raise ContractError("public evidence disclosure identity does not bind locator and bytes")

    receipt = dict(span.receipt or {})
    locator = dict(span.locator or {})
    if (
        not span.is_replayable
        or type(receipt.get("segment_index")) is not int
        or receipt.get("segment_index") != 0
        or receipt.get("segment_bytes") != len(body)
        or receipt.get("segment_sha256") != document.content_sha256
        or locator.get("kind") != "text_span"
        or type(locator.get("segment_index")) is not int
        or locator.get("segment_index") != 0
        or locator.get("span_start_byte") != receipt.get("span_start_byte")
        or locator.get("span_end_byte") != receipt.get("span_end_byte")
    ):
        raise ContractError("public evidence requires the complete source as receipt segment zero")
    verify_span(span, body_sha256=document.content_sha256, segment_text=source.raw_source)
    if set(locator) != {
        "kind", "sub_kind", "segment_index", "span_start_byte", "span_end_byte"
    }:
        raise ContractError("public evidence locator shape is not admitted")
    start, end = receipt["span_start_byte"], receipt["span_end_byte"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(body):
        raise ContractError("public evidence span bounds invalid")
    try:
        exact_text = body[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("public evidence span does not follow UTF-8 boundaries") from exc
    replayed_span = text_span(
        document_id=document.document_id, document_version=document.revision,
        body_sha256=document.content_sha256, segment_index=0,
        segment_text=source.raw_source, start_byte=start, end_byte=end,
        text=exact_text, rights_profile=document.rights_profile,
    )
    if replayed_span.span_id != span.span_id or replayed_span.locator != locator:
        raise ContractError("public evidence span identity does not reproduce its locator")

    projected = {
        "contract_id": CATALYST_PUBLIC_EVIDENCE_CONTRACT,
        "schema_version": "1.0.0", "scope": "event_source_context",
        "role": "source_context", "event_id": owner["event_id"],
        "event_revision_ref": owner["revision_ref"], "issuer_cik": owner["issuer_cik"],
        "document_ref": document.document_id, "document_revision": document.revision,
        "accession": source.accession, "document_content_sha256": document.content_sha256,
        "document_bytes": len(body), "span_ref": span.span_id,
        "span_start_byte": receipt["span_start_byte"], "span_end_byte": receipt["span_end_byte"],
        "span_text_sha256": span.text_sha256, "url": source.source_url,
        "label": "SEC source document", "excerpt": None,
        "source_class": document.source_class, "rights_profile": document.rights_profile,
        "rights_state": document.rights_state, "filed_on": source.filed_at,
        "source_available_at": _clock(document.available_at, field="source_available_at"),
        "observed_at": _clock(document.fetched_at, field="observed_at"),
        "projection_cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "authority": {
            **CATALYST_SOURCE_FACT_AUTHORITY,
            "allowed_uses": list(CATALYST_SOURCE_FACT_AUTHORITY["allowed_uses"]),
            "forbidden_uses": list(CATALYST_SOURCE_FACT_AUTHORITY["forbidden_uses"]),
        },
    }
    return validate_catalyst_public_evidence(
        projected, event_id=owner["event_id"], event_revision_ref=owner["revision_ref"],
        issuer_cik=owner["issuer_cik"], document_refs=owner["document_refs"],
        event_observed_at=owner["observed_at"], generation_cutoff=generation_cutoff,
    )


def attach_catalyst_public_evidence(
    event: object,
    evidence: Sequence[Mapping[str, Any]],
    *,
    generation_cutoff: object,
) -> dict[str, Any]:
    """Attach this cut's evidence under the compatible v1.1 event envelope.

    This does not relabel an old citation for a new event revision. Fresh
    attachment requires the same declared cut; subsequent validated reads may
    consume the retained projection at a later cutoff without rewriting clocks.
    """
    owner = validate_company_catalyst_event(event, generation_cutoff=generation_cutoff)
    _literal, cutoff = _strict_knowledge_timestamp(generation_cutoff, field="generation_cutoff")
    if not isinstance(evidence, (list, tuple)) or len(evidence) > 128:
        raise ContractError("public evidence attachment must be a bounded sequence")
    records = []
    for value in evidence:
        record = validate_catalyst_public_evidence(
            value, event_id=owner["event_id"], event_revision_ref=owner["revision_ref"],
            issuer_cik=owner["issuer_cik"], document_refs=owner["document_refs"],
            event_observed_at=owner["observed_at"], generation_cutoff=generation_cutoff,
        )
        _literal, evidence_cut = _strict_knowledge_timestamp(record["projection_cutoff"], field="projection_cutoff")
        if evidence_cut != cutoff:
            raise ContractError("public evidence attachment requires the same owner projection cut")
        records.append(record)
    owner["schema_version"] = "1.1.0"
    owner["public_evidence"] = sorted(records, key=lambda value: (value["document_ref"], value["span_ref"]))
    return validate_company_catalyst_event(owner, generation_cutoff=generation_cutoff)
