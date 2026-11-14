"""Read-only F04 evidence preview over existing Company Intelligence contracts.

This is a CURRENT snapshot consumer, not a new F04/GMI/evidence/rights owner.
No file or network I/O, publisher, model, forecast, rank, alert, or trading path.
The caller supplies complete pinned native F04/Company Intelligence snapshots and
an incumbent IssuerRegistry. Valid-time aliases are NOT historical knowledge-time
proof. No v2/v3 shadow, historical/PIT or economic-exposure fallback is attempted.

Only single-segment held UTF-8 source documents are supported in this slice.
Canonical verify_span is reused; the preview additionally checks every join,
whole-body integrity, locator consistency, and renders replayed bytes rather
than display_excerpt. Multi-segment, PDF and normalized document adapters remain
with their source owners. An address-only span never becomes a byte receipt.

source_use is a TRUSTED IN-PROCESS dependency supplied by the incumbent rights
owner, NOT an external JSON admission field or a new rights policy. It must decide
use of the exact document/span for internal_research at cutoff. No adapter is
installed here; omission/refusal/error produces no excerpt. Tests that inject True
are synthetic contract tests, not natural rights, source-authenticity or live proof.
Source stance is upstream-supplied context, not an inference or verified economics.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping, Sequence

from engine.company_intelligence.contracts import (
    ContractError, validate_context, validate_manifest as validate_company_manifest,
)
from engine.company_intelligence.documents import SourceDocument, SourceSpan, verify_span
from engine.company_intelligence.events import CompanyEvent
from engine.company_intelligence.identity import IssuerRegistry
from engine.earnings_narrative.contracts import sha256_bytes
from .contracts import canonical_json_bytes, canonical_json_sha256, validate_exposure, validate_manifest
from .views import derive_generation_id


@dataclass(frozen=True)
class NativeEvidence:
    """References to native source objects, never a new evidence-custody record."""
    event: CompanyEvent
    document: SourceDocument
    span: SourceSpan
    body: bytes
    stance: str = "context"


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _clock(value: object) -> datetime:
    if not isinstance(value, str):
        raise ContractError("snapshot clock must be an exact timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not _aware(parsed):
        raise ContractError("snapshot clock must be timezone aware")
    return parsed


def _members(theme_id, cutoff, contexts, company_manifest, exposures, manifest, registry):
    """Validate native snapshots with their owners, then perform consumer joins."""
    validate_company_manifest(company_manifest)
    validate_manifest(manifest, allow_unmaterialized_files=True)
    if not isinstance(registry, IssuerRegistry):
        raise ContractError("native issuer registry required")
    if set(contexts) != set(exposures) or len(contexts) != manifest["company_count"]:
        raise ContractError("snapshot company coverage differs")
    source = manifest["source"]["company_intelligence"]
    if (source["generation_id"] != company_manifest["generation_id"]
            or source["sha256"] != canonical_json_sha256(company_manifest)
            or derive_generation_id(exposures, manifest) != manifest["generation_id"]):
        raise ContractError("owner generation binding differs")
    stamp = _clock(manifest["generated_at"])
    if manifest["generated_at"] != company_manifest["generated_at"] or stamp > cutoff:
        raise ContractError("owner clocks differ or are future")
    if cutoff - stamp > timedelta(hours=36):
        return {}, "owner_snapshot_stale"
    members: dict[str, set[str]] = {}
    for ticker, exposure in sorted(exposures.items()):
        context = contexts[ticker]
        validate_context(context)
        validate_exposure(exposure)
        pin = exposure["company_intelligence"]
        if (context["company"]["ticker"] != ticker or exposure["company"]["ticker"] != ticker
                or context["generation_id"] != company_manifest["generation_id"]
                or context["generated_at"] != company_manifest["generated_at"]
                or exposure["generated_at"] != manifest["generated_at"]
                or exposure["generation_id"] != manifest["generation_id"]
                or pin["generation_id"] != context["generation_id"]
                or pin["context_sha256"] != canonical_json_sha256(context)
                or pin["latest_event_id"] != context["latest_event_id"]):
            raise ContractError("company/exposure join differs")
        parent_receipt = company_manifest["files"].get(f"companies/{ticker}.json", {})
        if (parent_receipt.get("sha256") != canonical_json_sha256(context)
                or parent_receipt.get("bytes") != len(canonical_json_bytes(context))):
            raise ContractError("parent file receipt differs from native context bytes")
        if manifest["files"]:
            receipt = manifest["files"].get(f"companies/{ticker}.json", {})
            if (receipt.get("sha256") != canonical_json_sha256(exposure)
                    or receipt.get("bytes") != len(canonical_json_bytes(exposure))):
                raise ContractError("materialized exposure receipt differs")
        if not any(item["theme_id"] == theme_id for item in exposure["exposures"]):
            continue
        try:
            resolved = registry.resolve_ticker(ticker, asof=cutoff.date())
        except (ValueError, LookupError):
            continue
        if resolved is not None:
            members.setdefault(resolved.company_id, set()).add(resolved.security_id)
    return members, None


def _qualify(row, cutoff, members, source_use):
    event, document, span = row.event, row.document, row.span
    if not (isinstance(event, CompanyEvent) and isinstance(document, SourceDocument)
            and isinstance(span, SourceSpan) and isinstance(row.body, bytes)):
        return None, "native_source_types_required"
    if row.stance not in {"support", "contradict", "context"}:
        return None, "unknown_source_stance"
    if event.state not in {"complete", "completed_partial", "corrected", "derived_ready", "distributed"}:
        return None, "event_not_current"
    if document.superseded_by_document_id is not None or document.is_duplicate or not document.holds_bytes:
        return None, "source_not_current"
    if document.event_id != event.event_id or document.document_id not in event.document_ids:
        return None, "event_document_join"
    if (span.document_id != document.document_id or span.document_version != document.revision
            or span.rights_profile != document.rights_profile):
        return None, "document_span_join"
    securities = members.get(event.company_id, set())
    if not securities or not securities.intersection(event.security_ids):
        return None, "issuer_security_join"
    clocks = (event.source_available_at, event.observed_at,
              document.published_at, document.available_at, document.fetched_at)
    if not all(_aware(c) for c in clocks):
        return None, "source_clock_missing"
    if max(clocks) > cutoff:
        return None, "source_from_future"
    if (event.observed_at < event.source_available_at
            or document.available_at < document.published_at
            or document.fetched_at < document.available_at):
        return None, "source_clock_order"
    if cutoff - document.published_at > timedelta(days=3):
        return None, "source_stale"
    if sha256_bytes(row.body) != document.content_sha256:
        return None, "body_digest_mismatch"
    if document.content_bytes is not None and document.content_bytes != len(row.body):
        return None, "body_length_mismatch"
    if len(row.body) > 2_000_000 or not span.is_replayable:
        return None, "source_not_replayable"
    receipt = span.receipt or {}
    locator = span.locator
    for key in ("segment_index", "span_start_byte", "span_end_byte"):
        number = receipt.get(key)
        located = locator.get(key)
        if (isinstance(number, bool) or not isinstance(number, int)
                or isinstance(located, bool) or not isinstance(located, int) or located != number):
            return None, "span_locator_mismatch"
    if receipt["segment_index"] != 0:
        return None, "single_segment_only"
    try:
        # This narrow adapter makes the whole held body the native segment.
        # It cannot accept unrelated segment text with a borrowed body hash.
        body_text = row.body.decode("utf-8")
        verify_span(span, segment_text=body_text, body_sha256=document.content_sha256)
        text = row.body[receipt["span_start_byte"]:receipt["span_end_byte"]].decode("utf-8")
    except (ValueError, TypeError, LookupError):
        return None, "native_span_replay_failed"
    if not text or len(text) > 4000:
        return None, "excerpt_unbounded_or_empty"
    try:
        allowed = callable(source_use) and source_use(document=document, span=span,
            purpose="internal_research", cutoff=cutoff) is True
    except Exception:
        allowed = False
    if not allowed:
        return None, "source_use_unavailable"
    return {"event_id": event.event_id, "issuer_id": event.company_id,
        "document_id": document.document_id, "document_version": document.revision,
        "supersedes_document_id": document.supersedes_document_id,
        "document_sha256": document.content_sha256, "span_id": span.span_id,
        "text_sha256": span.text_sha256, "text": text, "stance": row.stance,
        "classification": "upstream_context_label_not_verified_economics",
        "link_meaning": "basket_membership_only",
        "published_at": document.published_at.isoformat(),
        "known_at": max(event.observed_at, document.fetched_at).isoformat()}, None


def compile_factor_evidence(theme_id: str, *, cutoff: datetime,
        company_contexts: Mapping[str, Mapping[str, Any]], company_manifest: Mapping[str, Any],
        exposures: Mapping[str, Mapping[str, Any]], exposure_manifest: Mapping[str, Any],
        registry: IssuerRegistry, evidence: Sequence[NativeEvidence],
        source_use: Callable[..., bool] | None = None) -> dict[str, Any]:
    """Preview source context; the three-day/36-hour windows are pilot safety caps.

    Complete snapshot joins fail closed. Source-specific failures do not erase
    useful independently qualified records, but coverage shortfalls stay explicit.
    No source count is an independent-confirmation count, and no text is causal
    attribution. Movement/Prophet/Entry owners are intentionally not wired here.
    """
    if not isinstance(theme_id, str) or not theme_id or len(theme_id) > 96 or not _aware(cutoff):
        raise ValueError("bounded theme identity and aware cutoff required")
    if not isinstance(evidence, (list, tuple)) or len(evidence) > 1000:
        raise ValueError("at most 1000 native evidence references required")
    result = {"schema": "company_theme_exposure.factor_evidence_preview.v1",
        "mode": "CURRENT_SNAPSHOT_RESEARCH_ONLY", "theme_id": theme_id,
        "cutoff": cutoff.isoformat(), "status": "ATTRIBUTION_UNKNOWN",
        "causal_attribution": "UNPROVEN", "observed_movement": None,
        "supporting": [], "contradictory": [], "context": [], "refused": [],
        "conflicts": [], "distinct_event_count": 0, "independent_confirmation_count": None,
        "unknowns": ["price_causation_unproven", "source_independence_not_established",
                     "movement_owner_not_read", "native_rights_adapter_not_installed"],
        "authority": {"ranking": False, "alerts": False, "trading": False,
                      "propagation": False, "regime": False, "evidence_custody": False},
        "prophet_entry": {"status": "NOT_READ", "reason": "separate_qualified_owner_required"}}
    try:
        members, gap = _members(theme_id, cutoff, company_contexts, company_manifest,
                               exposures, exposure_manifest, registry)
    except (ValueError, TypeError, KeyError, AttributeError):
        members, gap = {}, "owner_snapshot_invalid"
    if gap:
        result["unknowns"].append(gap)
        return result
    admitted = []
    for row in evidence:
        if not isinstance(row, NativeEvidence):
            result["refused"].append({"span_id": None, "reason": "native_source_types_required"})
            continue
        item, reason = _qualify(row, cutoff, members, source_use)
        if reason:
            result["refused"].append({"span_id": getattr(row.span, "span_id", None), "reason": reason})
        else:
            admitted.append(item)
    versions = {}
    for item in admitted:
        key = (item["document_id"], item["document_version"])
        versions.setdefault(key, set()).add(item["document_sha256"])
    conflicted = {key for key, values in versions.items() if len(values) > 1}
    for key in sorted(conflicted):
        result["conflicts"].append({"document_id": key[0], "document_version": key[1],
            "reason": "document_version_conflict", "resolution": "UNRESOLVED"})
    # Refuse an inconsistent current selection; never become a correction owner.
    # The incumbent source selector must return one qualified current version.
    admitted_ids = {item["document_id"] for item in admitted}
    correction_pairs = {(item["document_id"], item["supersedes_document_id"])
        for item in admitted if item["supersedes_document_id"] in admitted_ids}
    correction_blocked = set()
    for successor, predecessor in sorted(correction_pairs):
        correction_blocked.update((successor, predecessor))
        result["conflicts"].append({"document_id": successor, "predecessor_document_id": predecessor,
            "reason": "correction_selection_required", "resolution": "UNRESOLVED"})
    has_contradiction = any(item["stance"] == "contradict" for item in admitted)
    seen = set()
    eligible_events = set()
    rendered = 0
    for item in sorted(admitted, key=lambda r: (r["event_id"], r["document_id"], r["span_id"],
            r["stance"], r["known_at"], r["published_at"], r["document_sha256"])):
        if ((item["document_id"], item["document_version"]) in conflicted
                or item["document_id"] in correction_blocked):
            continue
        key = (item["issuer_id"], item["event_id"], item["text_sha256"], item["stance"])
        eligible_events.add(item["event_id"])
        if key in seen:
            continue
        seen.add(key)
        if rendered >= 50:
            continue
        destination = {"support": "supporting", "contradict": "contradictory", "context": "context"}[item["stance"]]
        result[destination].append(item)
        rendered += 1
    result["distinct_event_count"] = len(eligible_events)
    result["omitted_excerpt_count"] = len(seen) - rendered
    if has_contradiction or result["conflicts"]:
        result["status"] = "CONFLICTING_EVIDENCE"
    elif result["supporting"]:
        result["status"] = "EVIDENCE_AVAILABLE"
    if result["refused"]:
        result["unknowns"].append("evidence_coverage_incomplete")
    if result["omitted_excerpt_count"]:
        result["unknowns"].append("excerpt_output_truncated")
    result["refused"].sort(key=lambda r: (r["span_id"] or "", r["reason"]))
    return result
