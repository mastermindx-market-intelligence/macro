"""Outcome-blind PB-D quality receipts over existing Company Intelligence objects.

This is a pure research adapter, not an event store, classifier, source retriever,
or signal.  It cannot certify that a reviewer is human or that an annotation was
actually made at its asserted time.  Durable, independently captured owner and
review receipts remain the producer's responsibility.  A synthetic packet proves
the mechanics only.  Nothing here enrolls the frozen PB-D experiment.
Every retained structured field has a closed shape. This can reject explicit
outcome fields, but cannot authenticate the truth or outcome blindness of free
prose supplied by a producer or reviewer.

``build_quality_receipt`` accepts JSON data.  ``source_documents`` maps existing
document IDs to unmodified ``SourceDocument.to_payload()`` values; ``events`` is
a list of derived annotations with these fields:

* event_id, event_version, owner_receipt_id, issuer_id, focal_proposition_id/text;
* evidence: existing claim_id, issuer_id/relevance (``direct``), source_span.v1,
  public_time_precision (``second`` or ``minute``), clock_status (``verified``),
  and new_information (a strict boolean);
* roots: root_family_id, origin_id, origin_document_id, origin_claim_id,
  supports_proposition_id, support_kind (``proposition`` or ``mechanism_link``),
  mechanism_link, claim_ids, dependencies, and lineage_complete;
* materiality: what_changed, mechanism, dimension, direction, significance_basis
  (scale/duration/risk), significance_rationale, horizon, contingency,
  alternative_explanation, falsifier, new_information_document_id; scale also
  requires magnitude and denominator;
* tag_details: optional structured STRATEGIC_OPTION, GOVERNMENT_LINKED,
  FINANCING_LINKED and EXPECTATION_CHANGE receipts;
* reviews: exactly two independent receipts, with reviewer_id, review_receipt_id,
  completed_at, independent=True, outcome_blind=True, packet_sha256, labels and
  root_pairs. Every label has value TRUE/FALSE/UNKNOWN, reason, evidence_refs.
  Each pair has root_family_ids, independent_generation,
  shared_evidentiary_failure (both tri-state), reason and evidence_refs.
  Disagreements require a distinct third ``adjudication`` receipt naming both
  original review_receipt_ids in ``resolves_review_receipt_ids``.

The coverage annotation contains issuer_id, status=complete, candidate_event_ids,
provider_receipt_ids, missing_sources=[], source_version, classifier_version,
covered_from, covered_through, available_at, observed_at, and two reviews of the
candidate set. The scope must exactly equal (freshness_start, decision_cut]; the
end precedes receipt availability, observation, and review, all by the cut.
Consequently a final prospective watermark and its review must be at the cut.
This conservative mechanics boundary does not establish that a live provider or
human-review workflow can meet it. Coverage reviewers use the same review header
and ``candidate_set_complete=True``. Use the two packet-digest helpers before
recording reviews; reviewers must have seen that exact packet by the cut.

Body text is supplied separately in ``source_bodies[document_id]``. This first
adapter supports exact UTF-8 body spans at segment zero. A supplied
``source_segments[span_id]`` must equal that body; unsupported segmentation stays
UNKNOWN. Existing CI validators replay the source digest, revision and span.
Document/body/segment maps may contain only IDs explicitly referenced by the
event evidence. Context must be represented as reviewed, source-linked evidence;
unchecked unused objects are refused, rather than retained in the review packet.
Optional Evidence Foundation references are validated but never counted as
verified roots: their declarative independence components grant no authority.
Any supplied numerical baseline, correction pointer, or reference knowledge clock
must also be admissible to the reviewers by the cut, even if its secondary label
is unknown. A genuinely absent baseline contains no future value and does not
block otherwise resolved primary fields.

All timestamps require a timezone and intraday precision. The caller supplies
the actual exchange-calendar cut[d-3], not a three-calendar-day approximation.
Receipt digests establish integrity, not external authenticity. Append later
corrections with ``append_source_correction``; never rebuild an original primary
exposure using subsequently corrected evidence.
"""
from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from .documents import DocumentError, FilingKey, SourceDocument, SourceSpan, verify_span
from .events import EventError, parse_canonical_event_id
from .identity import company_id_for_cik


SCHEMA = "pb_d_quality.v1"
SPEC_VERSION = "PB_D_EVENT_QUALITY_LABEL_SPEC/v1.0"
SPEC_COMMIT = "df2091915159dab94f316718caa9b2662098eae4"
OPERATION_ID = "PB-D-T2-EVENT-QUALITY-20261007"
AUTHORITY_FLAGS = {key: False for key in (
    "can_rank", "can_gate", "can_size", "can_originate", "can_open_entry",
)}


class TriState(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class UnknownReason(str, Enum):
    COVERAGE_INCOMPLETE = "coverage_incomplete"
    COVERAGE_CLOCK_MISSING = "coverage_clock_missing"
    COVERAGE_SCOPE_MISMATCH = "coverage_scope_mismatch"
    CANDIDATE_SET_MISMATCH = "candidate_set_mismatch"
    EVENT_IDENTITY_UNVERIFIED = "event_identity_unverified"
    EVENT_IDENTITY_COLLISION = "event_identity_collision"
    ISSUER_MISMATCH = "issuer_mismatch"
    INCIDENTAL_ISSUER = "incidental_issuer"
    SOURCE_MISSING = "source_missing"
    SOURCE_INVALID = "source_invalid"
    SOURCE_BYTES_MISSING = "source_bytes_missing"
    SOURCE_RECEIPT_INVALID = "source_receipt_invalid"
    SOURCE_SEGMENT_UNVERIFIED = "source_segment_unverified"
    RIGHTS_UNVERIFIED = "rights_unverified"
    PUBLIC_CLOCK_UNVERIFIED = "public_clock_unverified"
    CLOCK_MISSING = "clock_missing"
    CLOCK_CONTRADICTION = "clock_contradiction"
    EVIDENCE_AFTER_CUT = "evidence_after_cut"
    REVIEW_MISSING = "review_missing"
    REVIEW_NOT_INDEPENDENT = "review_not_independent"
    REVIEW_NOT_BLIND = "review_not_blind"
    REVIEW_PACKET_MISMATCH = "review_packet_mismatch"
    REVIEW_AFTER_CUT = "review_after_cut"
    REVIEW_BEFORE_EVIDENCE = "review_before_evidence"
    UNRESOLVED_DISAGREEMENT = "unresolved_disagreement"
    REVIEW_LABEL_UNKNOWN = "review_label_unknown"
    ROOT_LINEAGE_UNVERIFIED = "root_lineage_unverified"
    ROOT_SCOPE_MISMATCH = "root_scope_mismatch"
    ROOT_PAIR_UNREVIEWED = "root_pair_unreviewed"
    MATERIALITY_UNSUPPORTED = "materiality_unsupported"
    EXPECTATION_BASELINE_MISSING = "expectation_baseline_missing"
    EXPECTATION_NOT_COMPARABLE = "expectation_not_comparable"
    SECONDARY_TAG_UNSUPPORTED = "secondary_tag_unsupported"
    LABEL_CONFLICT = "label_conflict"
    EVIDENCE_REFERENCE_INVALID = "evidence_reference_invalid"
    RAW_ATTENTION_UNKNOWN = "raw_attention_unknown"


TAGS = (
    "ATTENTION_ONLY", "VERIFIED_MATERIAL_EVENT", "EXPECTATION_CHANGE",
    "STRATEGIC_OPTION", "GOVERNMENT_LINKED", "FINANCING_LINKED",
    "INDEPENDENT_EVIDENCE_2PLUS", "SYNDICATED_SINGLE_ROOT", "NO_MATERIAL_EVENT",
)
TRUE, FALSE, UNKNOWN = (state.value for state in TriState)
_EVENT_KEYS = frozenset({
    "event_id", "event_version", "owner_receipt_id", "issuer_id",
    "focal_proposition_id", "focal_proposition_text", "evidence", "roots",
    "materiality", "tag_details", "reviews", "adjudication", "evidence_references",
    "occurred_at", "correction_links",
})

# These shapes restrict the adapter's annotation surface, not the closed CI
# owner contracts. Native validators still own document, span and reference
# semantics. Missing non-tri-state values may represent absence; extra fields
# and structured data in scalar slots are never silently retained.
_TRI = "tri_state"
_EF_REF = "evidence_foundation_reference"
_NUMBER = (int, float, str)
_LABEL_SHAPE = {"value": _TRI, "reason": str, "evidence_refs": [str]}
_PAIR_SHAPE = {"root_family_ids": [str], "independent_generation": _TRI,
               "shared_evidentiary_failure": _TRI, "reason": str, "evidence_refs": [str]}
_REVIEW_HEADER = {"reviewer_id": str, "review_receipt_id": str, "completed_at": str,
                  "independent": bool, "outcome_blind": bool, "packet_sha256": str}
_EVENT_REVIEW = {**_REVIEW_HEADER, "labels": {tag: _LABEL_SHAPE for tag in TAGS}, "root_pairs": [_PAIR_SHAPE]}
_ADJUDICATION = {**_EVENT_REVIEW, "resolves_review_receipt_ids": [str]}
_COVERAGE_SHAPE = {
    "issuer_id": str, "status": str, "candidate_event_ids": [str],
    "provider_receipt_ids": [str], "missing_sources": [str],
    "source_version": str, "classifier_version": str,
    "covered_from": str, "covered_through": str, "available_at": str, "observed_at": str,
    "reviews": [{**_REVIEW_HEADER, "candidate_set_complete": bool}],
}
_DOCUMENT_SHAPE = {
    **{key: str for key in ("schema", "authority", "document_id", "event_id", "document_kind",
                            "source_class", "content_sha256", "fetched_at", "published_at",
                            "available_at", "supersedes_document_id", "superseded_by_document_id",
                            "rights_profile", "rights_state", "presented_fiscal_label")},
    "revision": int, "content_bytes": int, "holds_bytes": bool,
    "filing_key": {"cik": str, "accession": str},
}
_SPAN_SHAPE = {
    **{key: str for key in ("schema", "authority", "span_id", "document_id", "text_sha256",
                            "display_excerpt", "rights_profile", "receipt_state", "unreplayable_reason")},
    "document_version": int,
    "locator": {"kind": str, "sub_kind": str, "segment_index": int, "span_start_byte": int,
                "span_end_byte": int, "chapter": str, "speaker": str, "role": str,
                "page": (int, str), "table": (int, str), "row": (int, str),
                "column": (int, str), "region": [(int, float)]},
    "receipt": {"source_sha256": str, "segment_index": int, "segment_sha256": str,
                "segment_bytes": int, "span_start_byte": int, "span_end_byte": int, "text_sha256": str},
}
_BASELINE_SHAPE = {
    **{key: str for key in ("issuer_id", "period", "basis", "units", "currency", "owner_receipt_id",
                            "rights_profile", "rights_state", "available_at", "observed_at")},
    "value": _NUMBER,
}
_TAG_DETAIL_SHAPES = {
    "EXPECTATION_CHANGE": {"baseline_id": str, "baseline_type": str,
                           "prior": _BASELINE_SHAPE, "current": _BASELINE_SHAPE},
    "STRATEGIC_OPTION": {**{key: str for key in ("resources", "funding_basis", "continuing_validity",
                                                  "causal_path", "milestone", "falsifier")}, "evidence_refs": [str]},
    "GOVERNMENT_LINKED": {"action": str, "causal_role": str, "status": str, "evidence_refs": [str]},
    "FINANCING_LINKED": {"terms": str, "causal_role": str, "covenants": str,
                         "commitment": str, "evidence_refs": [str]},
}
_CORRECTION_POINTER = {key: str for key in (
    "correction_receipt_id", "original_claim_id", "corrected_claim_id", "original_document_id",
    "corrected_document_id", "reason", "correction_kind", "available_at", "observed_at",
)}
_EVENT_SHAPE = {
    **{key: str for key in ("event_id", "owner_receipt_id", "issuer_id", "focal_proposition_id",
                            "focal_proposition_text", "occurred_at")},
    "event_version": (int, str),
    "evidence": [{"claim_id": str, "issuer_id": str, "issuer_relevance": str,
                  "source_span": _SPAN_SHAPE, "public_time_precision": str,
                  "clock_status": str, "new_information": bool}],
    "roots": [{"root_family_id": str, "origin_id": str, "origin_document_id": str,
               "origin_claim_id": str, "supports_proposition_id": str, "support_kind": str,
               "mechanism_link": str, "claim_ids": [str], "dependencies": [str], "lineage_complete": bool}],
    "materiality": {key: str for key in ("what_changed", "mechanism", "dimension", "direction",
                                         "significance_basis", "significance_rationale", "horizon",
                                         "contingency", "alternative_explanation", "falsifier",
                                         "new_information_document_id", "magnitude", "denominator")},
    "tag_details": _TAG_DETAIL_SHAPES, "reviews": [_EVENT_REVIEW], "adjudication": _ADJUDICATION,
    "evidence_references": [_EF_REF], "correction_links": [_CORRECTION_POINTER],
}
_RESULT_SHAPE = {"value": _TRI, "reasons": [str], "evidence_refs": [str]}
_EVENT_RESULT_SHAPE = {
    **{key: str for key in ("event_id", "owner_receipt_id", "focal_proposition_id", "first_usable_at",
                            "completed_at", "review_packet_sha256")},
    "event_version": (int, str), "tags": {tag: _RESULT_SHAPE for tag in TAGS},
    "material_in_window": _RESULT_SHAPE, "fresh_independent_evidence_2plus": _RESULT_SHAPE,
    "q": _TRI, "q_reasons": [str], "root_family_ids": [str], "review_receipt_ids": [str], "adjudicated": bool,
}
_QUALITY_RECEIPT_SHAPE = {
    **{key: str for key in ("schema", "operation_id", "spec_version", "spec_commit", "authority",
                            "evidence_mode", "issuer_id", "decision_cut", "freshness_start",
                            "decision_cut_new_york", "ticker_at_cut", "completed_at",
                            "display_anchor_event_id", "coverage_packet_sha256", "input_sha256", "receipt_sha256")},
    "authority_flags": {key: bool for key in AUTHORITY_FLAGS}, "enrolled": bool, "raw_attention": bool,
    "q": _TRI, "q_reasons": [str], "tags": {tag: _RESULT_SHAPE for tag in TAGS},
    "positive_tag_event_ids": {tag: [str] for tag in TAGS}, "event_receipts": [_EVENT_RESULT_SHAPE],
    "positive_event_ids": [str], "correction_links": [_CORRECTION_POINTER],
    "input_packet": {"events": [_EVENT_SHAPE], "coverage": _COVERAGE_SHAPE,
                     "source_documents": ("map", _DOCUMENT_SHAPE)},
    "replayed_input_hashes": {"source_bodies": ("map", str), "source_segments": ("map", str)},
}


class QualityContractError(ValueError):
    """Malformed input, as opposed to legitimate missing research evidence."""


def _snapshot(value: Any) -> Any:
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if count > 100_000 or depth > 32:
            raise QualityContractError("input exceeds the bounded JSON contract")
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise QualityContractError("JSON keys must be strings")
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
        elif type(item) not in {str, int, float, bool, type(None)}:
            raise QualityContractError("inputs must be exact JSON data")
        elif type(item) is float and not math.isfinite(item):
            raise QualityContractError("nonfinite JSON number")
    return json.loads(_canonical(value))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _instant(value: Any) -> datetime:
    if type(value) is not str or "T" not in value or len(value) < 20:
        raise QualityContractError("a timezone-qualified intraday timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualityContractError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise QualityContractError("timestamp timezone is missing")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _text(value: Any) -> bool:
    return type(value) is str and bool(value.strip())


def _strings(value: Any, *, nonempty: bool = False) -> bool:
    return type(value) is list and (bool(value) or not nonempty) and all(_text(v) for v in value) and len(value) == len(set(value))


def _state(value: Any) -> str:
    if type(value) is not str or value not in {TRUE, FALSE, UNKNOWN}:
        raise QualityContractError("labels must be exactly TRUE, FALSE or UNKNOWN")
    return value


def _shape(value: Any, shape: Any, path: str) -> None:
    """Reject extra fields and arbitrary containers before anything is retained."""
    if shape == _TRI:
        _state(value)
        return
    if value is None:
        return  # Explicit missingness is adjudicated by the semantic gates.
    if shape == _EF_REF:
        try:
            from lib.evidence_foundation import validate_reference
            validate_reference(value)
        except (ImportError, ValueError, TypeError, KeyError, OSError) as exc:
            raise QualityContractError(f"{path} is not an owner-validated Evidence Foundation reference") from exc
        return
    if type(shape) is dict:
        if type(value) is not dict:
            raise QualityContractError(f"{path} must be an object")
        extra = set(value) - set(shape)
        if extra:
            raise QualityContractError(f"{path} has unsupported fields: {', '.join(sorted(extra))}")
        for key, child in value.items():
            _shape(child, shape[key], f"{path}.{key}")
    elif type(shape) is list:
        if type(value) is not list:
            raise QualityContractError(f"{path} must be an array")
        for index, child in enumerate(value):
            _shape(child, shape[0], f"{path}[{index}]")
    elif type(shape) is tuple and shape[0] == "map":
        if type(value) is not dict:
            raise QualityContractError(f"{path} must be an ID-keyed object")
        for key, child in value.items():
            _shape(child, shape[1], f"{path}[{key}]")
    elif type(value) not in (shape if type(shape) is tuple else (shape,)):
        raise QualityContractError(f"{path} has an unsupported scalar type")


def _document_map_shape(documents: Any) -> None:
    if type(documents) is not dict:
        raise QualityContractError("source_documents must be an ID-keyed object")
    _shape(documents, ("map", _DOCUMENT_SHAPE), "source_documents")
    for document_id, payload in documents.items():
        if type(payload) is dict and payload.get("document_id") is not None and payload["document_id"] != document_id:
            raise QualityContractError("source document map key disagrees with its native ID")


def _packet_shape(events, coverage, documents, bodies=None, segments=None):
    if type(events) is not list or type(coverage) is not dict:
        raise QualityContractError("events and coverage must be an array and object")
    _shape(events, [_EVENT_SHAPE], "events")
    _shape(coverage, _COVERAGE_SHAPE, "coverage")
    _document_map_shape(documents)
    referenced_documents, referenced_spans = set(), set()
    for event in events:
        if type(event) is not dict:
            raise QualityContractError("each event must be an object")
        entries = event.get("evidence") or []
        for entry in entries:
            span = entry.get("source_span") if type(entry) is dict else None
            if type(span) is dict:
                if _text(span.get("document_id")):
                    referenced_documents.add(span["document_id"])
                if _text(span.get("span_id")):
                    referenced_spans.add(span["span_id"])
    if set(documents) - referenced_documents:
        raise QualityContractError("source_documents contains an unreferenced owner ID")
    for name, values, allowed in (("source_bodies", bodies, referenced_documents),
                                  ("source_segments", segments, referenced_spans)):
        if values is not None:
            _shape(values, ("map", str), name)
            if type(values) is not dict or set(values) - allowed:
                raise QualityContractError(f"{name} contains an unreferenced owner ID")


def _result(value: str, *reasons: UnknownReason | str, refs: Sequence[str] = ()) -> dict[str, Any]:
    return {"value": value, "reasons": sorted({str(r.value if isinstance(r, UnknownReason) else r) for r in reasons}), "evidence_refs": sorted(set(refs))}


def _unknown(*reasons: UnknownReason | str) -> dict[str, Any]:
    return _result(UNKNOWN, *reasons)


def _scope(issuer_id: str, decision_cut: str, freshness_start: str) -> dict[str, str]:
    if type(issuer_id) is not str or company_id_for_cik(issuer_id) != issuer_id:
        raise QualityContractError("issuer_id must already be a canonical owner CIK ID")
    cut, start = _instant(decision_cut), _instant(freshness_start)
    if start >= cut:
        raise QualityContractError("freshness_start must precede decision_cut")
    return {"issuer_id": issuer_id, "decision_cut": _iso(cut), "freshness_start": _iso(start)}


def review_packet_sha256(issuer_id: str, *, decision_cut: str, freshness_start: str,
                         event: Mapping[str, Any], source_documents: Mapping[str, Any]) -> str:
    """Digest the frozen event/source packet before independent annotation."""
    data = _snapshot({"event": event, "source_documents": source_documents})
    if type(data["event"]) is not dict:
        raise QualityContractError("event must be an object")
    _shape(data["event"], _EVENT_SHAPE, "event")
    _document_map_shape(data["source_documents"])
    data["event"] = {k: v for k, v in data["event"].items() if k not in {"reviews", "adjudication"}}
    return _digest({"spec_commit": SPEC_COMMIT, **_scope(issuer_id, decision_cut, freshness_start), **data})


def coverage_packet_sha256(issuer_id: str, *, decision_cut: str, freshness_start: str,
                           coverage: Mapping[str, Any]) -> str:
    """Digest the captured provider candidate set, including its missingness."""
    value = _snapshot(coverage)
    if type(value) is not dict:
        raise QualityContractError("coverage must be an object")
    _shape(value, _COVERAGE_SHAPE, "coverage")
    packet = {k: v for k, v in value.items() if k != "reviews"}
    return _digest({"spec_commit": SPEC_COMMIT, **_scope(issuer_id, decision_cut, freshness_start), "coverage": packet})


def _review_header(review: Any, *, digest: str, cut: datetime,
                   available: datetime | None) -> tuple[datetime | None, list[UnknownReason]]:
    if type(review) is not dict or not all(_text(review.get(k)) for k in ("reviewer_id", "review_receipt_id")):
        return None, [UnknownReason.REVIEW_MISSING]
    reasons = []
    if review.get("independent") is not True:
        reasons.append(UnknownReason.REVIEW_NOT_INDEPENDENT)
    if review.get("outcome_blind") is not True:
        reasons.append(UnknownReason.REVIEW_NOT_BLIND)
    if review.get("packet_sha256") != digest:
        reasons.append(UnknownReason.REVIEW_PACKET_MISMATCH)
    try:
        completed = _instant(review.get("completed_at"))
    except QualityContractError:
        return None, reasons + [UnknownReason.CLOCK_MISSING]
    if completed > cut:
        reasons.append(UnknownReason.REVIEW_AFTER_CUT)
    if available is not None and completed < available:
        reasons.append(UnknownReason.REVIEW_BEFORE_EVIDENCE)
    return completed, reasons


def _reviews(packet: Mapping[str, Any], *, digest: str, cut: datetime,
             available: datetime | None, coverage: bool = False):
    rows = packet.get("reviews")
    if type(rows) is not list or len(rows) != 2:
        return [], None, [UnknownReason.REVIEW_MISSING]
    times, reasons = [], []
    for row in rows:
        stamp, failures = _review_header(row, digest=digest, cut=cut, available=available)
        reasons.extend(failures)
        if stamp is not None:
            times.append(stamp)
        if coverage and (type(row) is not dict or row.get("candidate_set_complete") is not True):
            reasons.append(UnknownReason.COVERAGE_INCOMPLETE)
    if all(type(row) is dict for row in rows):
        for key in ("reviewer_id", "review_receipt_id"):
            if rows[0].get(key) == rows[1].get(key):
                reasons.append(UnknownReason.REVIEW_NOT_INDEPENDENT)
    if reasons:
        return [], None, reasons
    return rows, max(times), []


def _adjudicator(event, reviews, *, digest, cut, available):
    row = event.get("adjudication")
    if row is None:
        return None, None
    prior_completion = max(_instant(review["completed_at"]) for review in reviews)
    stamp, reasons = _review_header(row, digest=digest, cut=cut, available=max(prior_completion, available) if available else prior_completion)
    if not reasons and row.get("reviewer_id") not in {r["reviewer_id"] for r in reviews} and row.get("review_receipt_id") not in {r["review_receipt_id"] for r in reviews}:
        if _strings(row.get("resolves_review_receipt_ids")) and sorted(row["resolves_review_receipt_ids"]) == sorted(r["review_receipt_id"] for r in reviews):
            return row, stamp
    return None, None


def _label(row, tag, claims):
    labels = row.get("labels", {})
    if type(labels) is not dict or tag not in labels:
        return _unknown(UnknownReason.REVIEW_MISSING)
    label = labels[tag]
    if type(label) is not dict:
        raise QualityContractError("review labels must carry value, reason and evidence_refs")
    value = _state(label.get("value"))
    refs = label.get("evidence_refs")
    if not _text(label.get("reason")) or not _strings(refs) or not set(refs) <= claims:
        return _unknown(UnknownReason.REVIEW_MISSING)
    if value == TRUE and not refs:
        return _unknown(UnknownReason.SOURCE_MISSING)
    return _result(value, UnknownReason.REVIEW_LABEL_UNKNOWN if value == UNKNOWN else "reviewed_present" if value == TRUE else "reviewed_absent", refs=refs)


def _consensus(reviews, adjudicator, tag, claims):
    left, right = (_label(row, tag, claims) for row in reviews)
    if left["value"] == right["value"]:
        return _result(left["value"], *left["reasons"], *right["reasons"], refs=left["evidence_refs"] + right["evidence_refs"])
    if adjudicator is not None:
        return _label(adjudicator, tag, claims)
    return _unknown(UnknownReason.UNRESOLVED_DISAGREEMENT)


def _native_document(payload):
    if type(payload) is not dict or payload.get("schema") != "source_document.v1" or payload.get("authority") != "context_only":
        raise QualityContractError("not an owner source_document.v1 payload")
    allowed = {field.name for field in fields(SourceDocument)}
    if set(payload) - allowed != {"schema", "authority"}:
        raise QualityContractError("unknown source document fields")
    kwargs = {k: v for k, v in payload.items() if k in allowed}
    if kwargs.get("filing_key") is not None:
        kwargs["filing_key"] = FilingKey(**kwargs["filing_key"])
    return SourceDocument(**kwargs)


def _native_span(payload):
    if type(payload) is not dict or payload.get("schema") != "source_span.v1" or payload.get("authority") != "context_only":
        raise QualityContractError("not an owner source_span.v1 payload")
    allowed = {field.name for field in fields(SourceSpan)}
    if set(payload) - allowed != {"schema", "authority"}:
        raise QualityContractError("unknown source span fields")
    return SourceSpan(**{k: v for k, v in payload.items() if k in allowed})


def _evidence(event, documents, bodies, segments, *, issuer, cut, start):
    records, reasons, usable = {}, [], []
    entries = event.get("evidence")
    if type(entries) is not list or not entries:
        return {}, [UnknownReason.SOURCE_MISSING], None
    for entry in entries:
        if type(entry) is not dict or not _text(entry.get("claim_id")) or entry["claim_id"] in records:
            reasons.append(UnknownReason.SOURCE_RECEIPT_INVALID)
            continue
        record = {"entry": entry, "fresh": UNKNOWN, "document_id": None, "usable_at": None}
        records[entry["claim_id"]] = record
        if entry.get("issuer_id") != issuer:
            reasons.append(UnknownReason.ISSUER_MISMATCH)
        if entry.get("issuer_relevance") != "direct":
            reasons.append(UnknownReason.INCIDENTAL_ISSUER)
        try:
            span = _native_span(entry.get("source_span"))
            payload = documents.get(span.document_id)
            if payload is None:
                reasons.append(UnknownReason.SOURCE_MISSING)
                continue
            doc = _native_document(payload)
            record["document_id"] = doc.document_id
            if not _text(span.span_id) or type(span.document_version) is not int or doc.document_id != span.document_id or doc.event_id != event.get("event_id") or span.document_version != doc.revision:
                reasons.append(UnknownReason.SOURCE_RECEIPT_INVALID)
            if doc.filing_key is not None and company_id_for_cik(doc.filing_key.cik) != issuer:
                reasons.append(UnknownReason.ISSUER_MISMATCH)
            if doc.rights_state not in {"public_primary", "licensed"} or not _text(doc.rights_profile) or doc.rights_profile == "rp_unknown_v1" or span.rights_profile != doc.rights_profile:
                reasons.append(UnknownReason.RIGHTS_UNVERIFIED)
            body = bodies.get(doc.document_id)
            if type(body) is not str or doc.holds_bytes is not True:
                reasons.append(UnknownReason.SOURCE_BYTES_MISSING)
            else:
                encoded = body.encode("utf-8")
                if sha256(encoded).hexdigest() != doc.content_sha256 or doc.content_bytes != len(encoded):
                    raise DocumentError("document bytes do not match the owner digest/length")
                segment = segments.get(span.span_id, body)
                receipt = dict(span.receipt or {})
                # A source hash alone does not prove that an arbitrary segment
                # came from those bytes. Authenticate the owner address before
                # asking the native verifier to replay its hash and byte slice.
                if segment != body or type(receipt.get("segment_index")) is not int or receipt.get("segment_index") != 0:
                    reasons.append(UnknownReason.SOURCE_SEGMENT_UNVERIFIED)
                elif any(type(receipt.get(key)) is not int or type(span.locator.get(key)) is not int or receipt.get(key) != span.locator.get(key) for key in ("segment_index", "span_start_byte", "span_end_byte")) or receipt.get("span_start_byte", 0) >= receipt.get("span_end_byte", 0):
                    raise DocumentError("span locator does not authenticate the replay address")
                else:
                    verify_span(span, segment_text=body, body_sha256=doc.content_sha256)
                    quoted = encoded[receipt["span_start_byte"]:receipt["span_end_byte"]].decode("utf-8")
                    if span.display_excerpt is not None and span.display_excerpt not in quoted:
                        raise DocumentError("display excerpt is not part of the authenticated source span")
            try:
                public, available, observed = (_instant(payload.get(k)) for k in ("published_at", "available_at", "fetched_at"))
            except QualityContractError:
                reasons.append(UnknownReason.CLOCK_MISSING)
                continue
            if not public <= available <= observed:
                reasons.append(UnknownReason.CLOCK_CONTRADICTION)
                continue
            first_usable = max(public, available, observed)
            record["usable_at"] = first_usable
            usable.append(first_usable)
            if first_usable > cut:
                reasons.append(UnknownReason.EVIDENCE_AFTER_CUT)
                continue
            if entry.get("public_time_precision") not in {"second", "minute"} or entry.get("clock_status") != "verified":
                reasons.append(UnknownReason.PUBLIC_CLOCK_UNVERIFIED)
                continue
            if type(entry.get("new_information")) is not bool:
                reasons.append(UnknownReason.PUBLIC_CLOCK_UNVERIFIED)
                continue
            record["public_at"] = public
            record["fresh"] = TRUE if start < public <= cut and entry["new_information"] else FALSE
        except (DocumentError, QualityContractError, TypeError, ValueError, KeyError):
            reasons.append(UnknownReason.SOURCE_RECEIPT_INVALID)
    return records, reasons, max(usable) if usable else None


def _context_clocks(event, cut):
    """Gate retained optional context even when its secondary label is UNKNOWN."""
    reasons, known = [], []

    def captured(row):
        if type(row) is not dict:
            reasons.append(UnknownReason.CLOCK_MISSING)
            return
        try:
            available, observed = _instant(row.get("available_at")), _instant(row.get("observed_at"))
        except QualityContractError:
            reasons.append(UnknownReason.CLOCK_MISSING)
            return
        if available > observed:
            reasons.append(UnknownReason.CLOCK_CONTRADICTION)
        if max(available, observed) > cut:
            reasons.append(UnknownReason.EVIDENCE_AFTER_CUT)
        known.append(max(available, observed))

    occurrence = event.get("occurred_at")
    if occurrence is not None:
        try:
            occurred = _instant(occurrence)
            if occurred > cut:
                reasons.append(UnknownReason.EVIDENCE_AFTER_CUT)
        except QualityContractError:
            reasons.append(UnknownReason.CLOCK_MISSING)
    details = event.get("tag_details") or {}
    expectation = details.get("EXPECTATION_CHANGE") or {}
    for name in ("prior", "current"):
        vintage = expectation.get(name)
        # An absent baseline has no value to leak and does not block Q. A
        # supplied numerical vintage must have actually existed in the packet.
        if type(vintage) is dict and any(vintage.get(key) is not None for key in ("value", "available_at", "observed_at")):
            captured(vintage)
    for link in event.get("correction_links") or []:
        captured(link)
    for reference in event.get("evidence_references") or []:
        if type(reference) is not dict:
            reasons.append(UnknownReason.EVIDENCE_REFERENCE_INVALID)
            continue
        captured_reference = False
        for clock in reference["clocks"]:
            # Future contract validity/review deadlines are not knowledge clocks.
            if clock["class"] in {"world_valid", "review_due"}:
                continue
            if clock["value_state"] != "known":
                reasons.append(UnknownReason.CLOCK_MISSING)
                continue
            if clock["grain"] == "date":
                if clock["value"] >= cut.date().isoformat():
                    reasons.append(UnknownReason.PUBLIC_CLOCK_UNVERIFIED)
                    continue
                stamp = _instant(clock["value"] + "T23:59:59.999999Z")
            else:
                stamp = _instant(clock["value"])
            if stamp > cut:
                reasons.append(UnknownReason.EVIDENCE_AFTER_CUT)
            known.append(stamp)
            if clock["class"] in {"observed", "system_recorded", "belief_or_build"}:
                captured_reference = True
        if not captured_reference:
            reasons.append(UnknownReason.CLOCK_MISSING)
    return reasons, max(known) if known else None


def _pair_assessment(row, pair, claims, origin_claims):
    entries = row.get("root_pairs", [])
    if type(entries) is not list:
        return UNKNOWN
    matches = [item for item in entries if type(item) is dict and _strings(item.get("root_family_ids")) and set(item["root_family_ids"]) == set(pair)]
    if len(matches) != 1:
        return UNKNOWN
    item = matches[0]
    if not _text(item.get("reason")) or not _strings(item.get("evidence_refs"), nonempty=True) or not set(item["evidence_refs"]) <= claims or not origin_claims <= set(item["evidence_refs"]):
        return UNKNOWN
    generation = _state(item.get("independent_generation"))
    failure = _state(item.get("shared_evidentiary_failure"))
    if generation == FALSE or failure == TRUE:
        return FALSE
    return TRUE if generation == TRUE and failure == FALSE else UNKNOWN


def _root_quality(event, records, reviews, adjudicator):
    roots = event.get("roots")
    if type(roots) is not list or not roots:
        unknown = _unknown(UnknownReason.ROOT_LINEAGE_UNVERIFIED)
        return unknown, unknown, unknown, [], None
    by_id = {}
    for root in roots:
        if type(root) is not dict or not all(_text(root.get(k)) for k in ("root_family_id", "origin_id", "origin_document_id", "origin_claim_id")):
            unknown = _unknown(UnknownReason.ROOT_LINEAGE_UNVERIFIED)
            return unknown, unknown, unknown, [], None
        if root["root_family_id"] in by_id or root.get("lineage_complete") is not True or not _strings(root.get("dependencies")) or not _strings(root.get("claim_ids"), nonempty=True):
            unknown = _unknown(UnknownReason.ROOT_LINEAGE_UNVERIFIED)
            return unknown, unknown, unknown, [], None
        if root.get("supports_proposition_id") != event.get("focal_proposition_id") or root.get("support_kind") not in {"proposition", "mechanism_link"} or (root.get("support_kind") == "mechanism_link" and not _text(root.get("mechanism_link"))):
            unknown = _unknown(UnknownReason.ROOT_SCOPE_MISMATCH)
            return unknown, unknown, unknown, [], None
        claims = root["claim_ids"]
        origin = records.get(root["origin_claim_id"])
        if not set(claims) <= set(records) or root["origin_claim_id"] not in claims or origin is None or origin["document_id"] != root["origin_document_id"]:
            unknown = _unknown(UnknownReason.ROOT_LINEAGE_UNVERIFIED)
            return unknown, unknown, unknown, [], None
        by_id[root["root_family_id"]] = root
    # Every retained manifestation belongs to a reviewed focal root. A copied
    # source cannot silently become a second root or disappear from the scope.
    if set().union(*(set(root["claim_ids"]) for root in roots)) != set(records):
        unknown = _unknown(UnknownReason.ROOT_LINEAGE_UNVERIFIED)
        return unknown, unknown, unknown, [], None
    ancestors = {}
    for name in by_id:
        seen, active = set(), set()
        def visit(node):
            if node in active or node not in by_id:
                raise QualityContractError("root dependency cycle or absent origin")
            if node in seen:
                return
            active.add(node)
            for parent in by_id[node]["dependencies"]:
                visit(parent)
            active.remove(node)
            seen.add(node)
        try:
            visit(name)
        except QualityContractError:
            unknown = _unknown(UnknownReason.ROOT_LINEAGE_UNVERIFIED)
            return unknown, unknown, unknown, [], None
        ancestors[name] = seen
    pairs, fresh_pairs, fresh_pair_times = [], [], []
    names = sorted(by_id)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            pair = (left, right)
            origin_claims = {by_id[name]["origin_claim_id"] for name in pair}
            a, b = (_pair_assessment(row, pair, set(records), origin_claims) for row in reviews)
            state = a if a == b else _pair_assessment(adjudicator, pair, set(records), origin_claims) if adjudicator else UNKNOWN
            # Explicit shared provenance is decisive even if labels say TRUE.
            source_origins = [records[by_id[name]["origin_claim_id"]] for name in pair]
            same_document = source_origins[0]["document_id"] == source_origins[1]["document_id"]
            same_body = source_origins[0]["entry"]["source_span"].get("receipt", {}).get("source_sha256") == source_origins[1]["entry"]["source_span"].get("receipt", {}).get("source_sha256")
            if len(origin_claims) != 2 or same_document or same_body or by_id[left]["origin_id"] == by_id[right]["origin_id"] or ancestors[left] & ancestors[right]:
                state = FALSE
            pairs.append(state)
            freshness = [records[by_id[name]["origin_claim_id"]]["fresh"] for name in pair]
            fresh_pairs.append(FALSE if state == FALSE or FALSE in freshness else TRUE if state == TRUE and freshness == [TRUE, TRUE] else UNKNOWN)
            if fresh_pairs[-1] == TRUE:
                support = set().union(*(set(by_id[name]["claim_ids"]) for name in ancestors[left] | ancestors[right]))
                fresh_pair_times.append(max(records[claim]["usable_at"] for claim in support))
    def fold(values):
        if TRUE in values:
            return _result(TRUE, refs=names)
        if UNKNOWN in values:
            return _unknown(UnknownReason.ROOT_PAIR_UNREVIEWED)
        return _result(FALSE, "fewer_than_two_verified_independent_roots", refs=names)
    independent, fresh = fold(pairs), fold(fresh_pairs)
    manifestations = {record["document_id"] for record in records.values()}
    # Shared dependencies are one effective origin; publisher count is unused.
    origins = set().union(*(ancestors[name] for name in names))
    terminal_origins = {name for name in origins if not by_id[name]["dependencies"]}
    if independent["value"] == TRUE:
        syndicated = _result(FALSE, "independent_second_root", refs=names)
    elif independent["value"] == UNKNOWN:
        syndicated = _unknown(UnknownReason.ROOT_PAIR_UNREVIEWED)
    else:
        single = len({by_id[name]["origin_id"] for name in terminal_origins}) == 1
        syndicated = _result(TRUE if single and len(manifestations) >= 2 else FALSE, "reviewed_manifestation_lineage", refs=names)
    return independent, fresh, syndicated, names, min(fresh_pair_times) if fresh_pair_times else None


def _intersect(reviewed, derived):
    if reviewed["value"] == UNKNOWN:
        return reviewed
    if derived["value"] == UNKNOWN:
        return derived
    if reviewed["value"] != derived["value"]:
        return _unknown(UnknownReason.LABEL_CONFLICT)
    return _result(reviewed["value"], *reviewed["reasons"], *derived["reasons"], refs=reviewed["evidence_refs"])


def _materiality(event, label, records):
    if label["value"] != TRUE:
        return label, label
    detail = event.get("materiality", {})
    required = ("what_changed", "mechanism", "dimension", "direction", "significance_rationale", "horizon", "contingency", "alternative_explanation", "falsifier", "new_information_document_id")
    if type(detail) is not dict or not all(_text(detail.get(k)) for k in required) or detail.get("significance_basis") not in {"scale", "duration", "risk"} or detail.get("dimension") not in {"revenue", "cost", "cash_flow", "capital", "risk", "option"}:
        missing = _unknown(UnknownReason.MATERIALITY_UNSUPPORTED)
        return missing, missing
    if detail["significance_basis"] == "scale" and not all(_text(detail.get(k)) for k in ("magnitude", "denominator")):
        missing = _unknown(UnknownReason.MATERIALITY_UNSUPPORTED)
        return missing, missing
    sources = [row for row in records.values() if row["document_id"] == detail["new_information_document_id"]]
    if not sources:
        missing = _unknown(UnknownReason.MATERIALITY_UNSUPPORTED)
        return missing, missing
    fresh = {row["fresh"] for row in sources}
    if len(fresh) != 1 or UNKNOWN in fresh:
        return label, _unknown(UnknownReason.PUBLIC_CLOCK_UNVERIFIED)
    in_window = next(iter(fresh))
    windowed = _result(in_window, "no_new_material_information_in_window" if in_window == FALSE else "reviewed_material_information_in_window", refs=label["evidence_refs"])
    return windowed, windowed


def _secondary(event, tag, label, records, *, issuer, cut, reviewed_at):
    if label["value"] == UNKNOWN:
        return label
    details = event.get("tag_details", {})
    if type(details) is not dict:
        raise QualityContractError("tag_details must be a JSON object")
    detail = details.get(tag)
    if tag == "EXPECTATION_CHANGE":
        if type(detail) is not dict:
            return _unknown(UnknownReason.EXPECTATION_BASELINE_MISSING)
        prior, current = detail.get("prior"), detail.get("current")
        try:
            if not _text(detail.get("baseline_id")) or detail.get("baseline_type") not in {"consensus", "guidance", "contract", "analyst", "frozen_model", "historical_base_rate"}:
                raise QualityContractError("baseline identity missing")
            if type(prior) is not dict or type(current) is not dict:
                raise QualityContractError("missing vintages")
            for row in (prior, current):
                if row.get("issuer_id") != issuer or not all(_text(row.get(k)) for k in ("period", "basis", "units", "currency", "owner_receipt_id", "rights_profile")) or row["rights_profile"] == "rp_unknown_v1" or row.get("rights_state") not in {"public_primary", "licensed"}:
                    raise QualityContractError("unusable baseline receipt")
                baseline_available, baseline_observed = _instant(row.get("available_at")), _instant(row.get("observed_at"))
                if baseline_available > baseline_observed or baseline_observed > min(cut, reviewed_at):
                    raise QualityContractError("baseline clock is contradictory or was not available to both raters")
            if any(prior[key] != current[key] for key in ("issuer_id", "period", "basis", "units", "currency")):
                raise QualityContractError("incomparable vintages")
            first_public = min(row["public_at"] for row in records.values() if row.get("fresh") == TRUE)
            if max(_instant(prior["available_at"]), _instant(prior["observed_at"])) >= first_public:
                raise QualityContractError("baseline did not precede the event")
            values = []
            for row in (prior, current):
                if type(row.get("value")) not in {int, float, str}:
                    raise QualityContractError("non-numeric baseline")
                value = Decimal(str(row["value"]))
                if not value.is_finite():
                    raise QualityContractError("nonfinite baseline")
                values.append(value)
            return _intersect(label, _result(TRUE if values[0] != values[1] else FALSE))
        except (QualityContractError, KeyError, ValueError, InvalidOperation):
            return _unknown(UnknownReason.EXPECTATION_NOT_COMPARABLE)
    if label["value"] != TRUE:
        return label
    required = {
        "STRATEGIC_OPTION": ("resources", "funding_basis", "continuing_validity", "causal_path", "milestone", "falsifier"),
        "GOVERNMENT_LINKED": ("action", "causal_role"),
        "FINANCING_LINKED": ("terms", "causal_role", "covenants"),
    }[tag]
    valid = type(detail) is dict and all(_text(detail.get(k)) for k in required) and _strings(detail.get("evidence_refs"), nonempty=True) and set(detail["evidence_refs"]) <= set(records)
    if tag == "GOVERNMENT_LINKED":
        valid = valid and detail.get("status") in {"proposed", "approved", "effective"}
    if tag == "FINANCING_LINKED":
        valid = valid and detail.get("commitment") in {"committed", "conditional"}
    return label if valid else _unknown(UnknownReason.SECONDARY_TAG_UNSUPPORTED)


def _event_receipt(event, documents, bodies, segments, *, scope, coverage_ok):
    cut, start = _instant(scope["decision_cut"]), _instant(scope["freshness_start"])
    reasons = []
    if type(event) is not dict or set(event) - _EVENT_KEYS:
        raise QualityContractError("unknown event annotation fields; outcomes are not inputs")
    event_id = event.get("event_id")
    try:
        native_issuer, _, _ = parse_canonical_event_id(event_id)
        if native_issuer != scope["issuer_id"] or event.get("issuer_id") != native_issuer:
            reasons.append(UnknownReason.ISSUER_MISMATCH)
    except EventError:
        reasons.append(UnknownReason.EVENT_IDENTITY_UNVERIFIED)
    version = event.get("event_version")
    if not (_text(version) or type(version) is int and version > 0) or not all(_text(event.get(k)) for k in ("owner_receipt_id", "focal_proposition_id", "focal_proposition_text")):
        reasons.append(UnknownReason.EVENT_IDENTITY_UNVERIFIED)
    records, evidence_reasons, available = _evidence(event, documents, bodies, segments, issuer=scope["issuer_id"], cut=cut, start=start)
    reasons.extend(evidence_reasons)
    if event.get("focal_proposition_id") not in records:
        reasons.append(UnknownReason.ROOT_SCOPE_MISMATCH)
    context_reasons, context_available = _context_clocks(event, cut)
    reasons.extend(context_reasons)
    if context_available is not None:
        available = max(available, context_available) if available else context_available
    digest = review_packet_sha256(**scope, event=event, source_documents=documents)
    reviews, completed, review_reasons = _reviews(event, digest=digest, cut=cut, available=available)
    reasons.extend(review_reasons)
    adjudicator, adjudicated = _adjudicator(event, reviews, digest=digest, cut=cut, available=available) if reviews else (None, None)
    if adjudicated is not None:
        completed = max(completed, adjudicated)
    if not coverage_ok:
        reasons.append(UnknownReason.COVERAGE_INCOMPLETE)
    if reasons:
        tags = {tag: _unknown(*reasons) for tag in TAGS}
        material_fresh = fresh = _unknown(*reasons)
        roots = []
    else:
        tags = {tag: _consensus(reviews, adjudicator, tag, set(records)) for tag in TAGS}
        independent, fresh, syndicated, roots, pair_available = _root_quality(event, records, reviews, adjudicator)
        tags["INDEPENDENT_EVIDENCE_2PLUS"] = _intersect(tags["INDEPENDENT_EVIDENCE_2PLUS"], independent)
        tags["SYNDICATED_SINGLE_ROOT"] = _intersect(tags["SYNDICATED_SINGLE_ROOT"], syndicated)
        if tags["INDEPENDENT_EVIDENCE_2PLUS"]["value"] == UNKNOWN:
            fresh = tags["INDEPENDENT_EVIDENCE_2PLUS"]
        tags["VERIFIED_MATERIAL_EVENT"], material_fresh = _materiality(event, tags["VERIFIED_MATERIAL_EVENT"], records)
        for tag in ("EXPECTATION_CHANGE", "STRATEGIC_OPTION", "GOVERNMENT_LINKED", "FINANCING_LINKED"):
            tags[tag] = _secondary(event, tag, tags[tag], records, issuer=scope["issuer_id"], cut=cut, reviewed_at=min(_instant(review["completed_at"]) for review in reviews))
        if pair_available is not None and material_fresh["value"] == TRUE:
            material_document = event["materiality"]["new_information_document_id"]
            material_available = min(record["usable_at"] for record in records.values() if record["document_id"] == material_document)
            available = max(pair_available, material_available)
        for opposite in ("ATTENTION_ONLY", "NO_MATERIAL_EVENT"):
            if tags[opposite]["value"] == TRUE and material_fresh["value"] == TRUE:
                tags[opposite] = _unknown(UnknownReason.LABEL_CONFLICT)
                tags["VERIFIED_MATERIAL_EVENT"] = material_fresh = _unknown(UnknownReason.LABEL_CONFLICT)
    q = UNKNOWN if UNKNOWN in (material_fresh["value"], fresh["value"]) else TRUE if material_fresh["value"] == fresh["value"] == TRUE else FALSE
    primary_reasons = sorted(set(material_fresh["reasons"] + fresh["reasons"])) if q == UNKNOWN else []
    return {
        "event_id": event_id, "event_version": version, "owner_receipt_id": event.get("owner_receipt_id"),
        "focal_proposition_id": event.get("focal_proposition_id"), "tags": tags,
        "material_in_window": material_fresh, "fresh_independent_evidence_2plus": fresh,
        "q": q, "q_reasons": primary_reasons, "root_family_ids": roots,
        "first_usable_at": _iso(available) if available else None,
        "completed_at": _iso(completed) if completed else None,
        "review_packet_sha256": digest,
        "review_receipt_ids": [row["review_receipt_id"] for row in reviews] + ([adjudicator["review_receipt_id"]] if adjudicator else []),
        "adjudicated": adjudicator is not None,
    }


def build_quality_receipt(issuer_id: str, *, decision_cut: str, freshness_start: str,
                          events: Sequence[Mapping[str, Any]], coverage: Mapping[str, Any],
                          source_documents: Mapping[str, Any], source_bodies: Mapping[str, str] | None = None,
                          source_segments: Mapping[str, str] | None = None,
                          ticker_at_cut: str | None = None, raw_attention: bool | None = None,
                          synthetic: bool = False) -> dict[str, Any]:
    """Build a deterministic, unregistered issuer/cut research-quality receipt.

    Missing evidence returns typed UNKNOWN. Malformed JSON/tri-state values or
    unexpected event fields raise QualityContractError. Candidate coverage gates
    Q before positive events are considered. Unknown secondary tags alone never
    block Q. Caller data are copied; no clock, network, filesystem or store is
    consulted except an optional owner's Evidence Foundation validator.
    """
    scope = _scope(issuer_id, decision_cut, freshness_start)
    cut = _instant(scope["decision_cut"])
    if raw_attention is not None and type(raw_attention) is not bool or type(synthetic) is not bool:
        raise QualityContractError("attention/synthetic flags must be strict booleans")
    if ticker_at_cut is not None and type(ticker_at_cut) is not str:
        raise QualityContractError("ticker_at_cut must be a string or absent")
    data = _snapshot({"events": events, "coverage": coverage, "source_documents": source_documents,
                      "source_bodies": {} if source_bodies is None else source_bodies,
                      "source_segments": {} if source_segments is None else source_segments})
    if type(data["events"]) is not list or any(type(event) is not dict for event in data["events"]):
        raise QualityContractError("events must be a JSON list of annotations")
    for key in ("coverage", "source_documents", "source_bodies", "source_segments"):
        if type(data[key]) is not dict:
            raise QualityContractError(f"{key} must be a JSON object")
    _packet_shape(data["events"], data["coverage"], data["source_documents"], data["source_bodies"], data["source_segments"])
    cov = data["coverage"]
    ids = [event.get("event_id") for event in data["events"]]
    coverage_reasons = []
    if not all(_text(value) for value in ids) or len(ids) != len(set(ids)):
        coverage_reasons.append(UnknownReason.EVENT_IDENTITY_COLLISION)
    if not _strings(cov.get("candidate_event_ids")) or sorted(cov["candidate_event_ids"]) != sorted(ids, key=str):
        coverage_reasons.append(UnknownReason.CANDIDATE_SET_MISMATCH)
    if cov.get("status") != "complete" or cov.get("missing_sources") != [] or not _strings(cov.get("provider_receipt_ids"), nonempty=True) or not all(_text(cov.get(k)) for k in ("source_version", "classifier_version")):
        coverage_reasons.append(UnknownReason.COVERAGE_INCOMPLETE)
    coverage_available = None
    try:
        covered_from, covered_through, available, observed = (_instant(cov.get(key)) for key in ("covered_from", "covered_through", "available_at", "observed_at"))
        if cov.get("issuer_id") != issuer_id or covered_from != _instant(scope["freshness_start"]) or covered_through != cut:
            coverage_reasons.append(UnknownReason.COVERAGE_SCOPE_MISMATCH)
        if not covered_through <= available <= observed:
            coverage_reasons.append(UnknownReason.CLOCK_CONTRADICTION)
        if observed > cut or available > cut:
            coverage_reasons.append(UnknownReason.EVIDENCE_AFTER_CUT)
        coverage_available = max(available, observed)
    except QualityContractError:
        coverage_reasons.append(UnknownReason.COVERAGE_CLOCK_MISSING)
    # A captured candidate set cannot be reviewed before its covered evidence.
    # Missing source clocks remain unknown again in the per-event native replay.
    for event in data["events"]:
        entries = event.get("evidence", [])
        if type(entries) is not list:
            continue
        for entry in entries:
            span = entry.get("source_span") if type(entry) is dict else None
            document = data["source_documents"].get(span.get("document_id")) if type(span) is dict and type(span.get("document_id")) is str else None
            if type(document) is not dict:
                continue
            try:
                latest = max(_instant(document.get(key)) for key in ("published_at", "available_at", "fetched_at"))
                coverage_available = max(coverage_available, latest) if coverage_available else latest
            except QualityContractError:
                coverage_reasons.append(UnknownReason.CLOCK_MISSING)
    cov_digest = coverage_packet_sha256(**scope, coverage=cov)
    _, coverage_completed, failures = _reviews(cov, digest=cov_digest, cut=cut, available=coverage_available, coverage=True)
    coverage_reasons.extend(failures)
    coverage_ok = not coverage_reasons
    rows = [_event_receipt(event, data["source_documents"], data["source_bodies"], data["source_segments"], scope=scope, coverage_ok=coverage_ok) for event in sorted(data["events"], key=lambda row: str(row.get("event_id")))]
    unresolved = [row for row in rows if row["q"] == UNKNOWN]
    positive = [row for row in rows if row["q"] == TRUE]
    q = UNKNOWN if coverage_reasons or unresolved else TRUE if positive else FALSE
    reasons = sorted({reason.value for reason in coverage_reasons} | {reason for row in unresolved for reason in row["q_reasons"]})
    tags, scopes = {}, {}
    for tag in TAGS:
        values = [row["tags"][tag]["value"] for row in rows]
        state = TRUE if TRUE in values else UNKNOWN if UNKNOWN in values else FALSE
        selected = [row["tags"][tag] for row in rows if row["tags"][tag]["value"] == state]
        tag_reasons = [reason for label in selected for reason in label["reasons"]]
        refs = [ref for label in selected for ref in label["evidence_refs"]]
        tags[tag] = _result(state, *(tag_reasons or ["reviewed_empty_candidate_set"]), refs=refs) if coverage_ok else _unknown(*coverage_reasons)
        scopes[tag] = [row["event_id"] for row in rows if row["tags"][tag]["value"] == TRUE]
    material_states = [row["material_in_window"]["value"] for row in rows]
    no_material = UNKNOWN if not coverage_ok or UNKNOWN in material_states else FALSE if TRUE in material_states else TRUE
    no_material_reasons = list(coverage_reasons) if not coverage_ok else [reason for row in rows if row["material_in_window"]["value"] == UNKNOWN for reason in row["material_in_window"]["reasons"]]
    if no_material != UNKNOWN:
        no_material_reasons = ["complete_review_no_material_event" if no_material == TRUE else "material_event_present"]
    tags["NO_MATERIAL_EVENT"] = _result(no_material, *no_material_reasons)
    attention = UNKNOWN if not coverage_ok else FALSE if raw_attention is False or no_material == FALSE else TRUE if raw_attention is True and no_material == TRUE else UNKNOWN
    attention_reasons = [] if attention != UNKNOWN else [UnknownReason.RAW_ATTENTION_UNKNOWN] if raw_attention is None and coverage_ok else no_material_reasons
    if attention != UNKNOWN:
        attention_reasons = ["attention_with_no_material_event" if attention == TRUE else "raw_attention_false" if raw_attention is False else "material_event_present"]
    tags["ATTENTION_ONLY"] = _result(attention, *attention_reasons)
    positive.sort(key=lambda row: (_instant(row["first_usable_at"]), row["event_id"]))
    times = [coverage_completed] + [_instant(row["completed_at"]) if row["completed_at"] else None for row in rows]
    completed = max(times) if all(time is not None for time in times) else None
    # Retain immutable owner/review payloads and content digests, not redistributable
    # raw source text. The body/segment availability hashes still bind input audit.
    packet = {"events": data["events"], "coverage": cov, "source_documents": data["source_documents"]}
    replay = {key: {name: sha256(text.encode("utf-8")).hexdigest() if type(text) is str else None for name, text in data[key].items()} for key in ("source_bodies", "source_segments")}
    receipt = {
        "schema": SCHEMA, "operation_id": OPERATION_ID, "spec_version": SPEC_VERSION, "spec_commit": SPEC_COMMIT,
        "authority": "research_only", "authority_flags": dict(AUTHORITY_FLAGS), "enrolled": False,
        "evidence_mode": "synthetic_mechanics_only" if synthetic else "producer_supplied_receipts_unenrolled",
        **scope, "decision_cut_new_york": cut.astimezone(ZoneInfo("America/New_York")).isoformat(),
        "ticker_at_cut": ticker_at_cut, "raw_attention": raw_attention,
        "q": q, "q_reasons": reasons, "completed_at": _iso(completed) if completed else None,
        "tags": tags, "positive_tag_event_ids": scopes, "event_receipts": rows,
        "positive_event_ids": [row["event_id"] for row in positive] if q == TRUE else [],
        "display_anchor_event_id": positive[0]["event_id"] if q == TRUE else None,
        "coverage_packet_sha256": cov_digest, "input_packet": packet,
        "input_sha256": _digest({"packet": packet, "replayed_input_hashes": replay}),
        "replayed_input_hashes": replay, "correction_links": [],
    }
    receipt["receipt_sha256"] = _digest(receipt)
    return receipt


def verify_quality_receipt(receipt: Mapping[str, Any]) -> bool:
    """Verify serialization integrity and the closed, all-false wire boundary.

    This is not a signature check, enrollment check or evidence re-evaluation.
    Consumers must bind issuer and both cut timestamps to their own observation.
    Optional Evidence Foundation references use their fixed owner contract
    validator; no source bodies, provider state, or market outcomes are read.
    """
    try:
        value = _snapshot(receipt)
        if type(value) is not dict or value.get("schema") != SCHEMA or value.get("operation_id") != OPERATION_ID or value.get("spec_version") != SPEC_VERSION or value.get("spec_commit") != SPEC_COMMIT:
            return False
        if set(value) != set(_QUALITY_RECEIPT_SHAPE):
            return False
        _shape(value, _QUALITY_RECEIPT_SHAPE, "receipt")
        packet, replay = value["input_packet"], value["replayed_input_hashes"]
        if type(packet) is not dict or type(replay) is not dict:
            return False
        _packet_shape(packet["events"], packet["coverage"], packet["source_documents"], replay["source_bodies"], replay["source_segments"])
        if value["correction_links"] != []:
            return False  # Later corrections belong in the separate wrapper.
        flags = value.get("authority_flags")
        if type(flags) is not dict or set(flags) != set(AUTHORITY_FLAGS) or any(flag is not False for flag in flags.values()) or value.get("authority") != "research_only" or value.get("enrolled") is not False:
            return False
        _scope(value["issuer_id"], value["decision_cut"], value["freshness_start"])
        _state(value["q"])
        if type(value.get("tags")) is not dict or set(value["tags"]) != set(TAGS) or not _strings(value.get("q_reasons")):
            return False
        for label in value["tags"].values():
            if type(label) is not dict or not _strings(label.get("reasons")) or not _strings(label.get("evidence_refs")):
                return False
            _state(label["value"])
        if value["completed_at"] is not None:
            _instant(value["completed_at"])
        expected = value.pop("receipt_sha256")
        return type(expected) is str and expected == _digest(value)
    except (QualityContractError, ValueError, TypeError, KeyError, OverflowError):
        return False


def append_source_correction(receipt: Mapping[str, Any], *, correction: Mapping[str, Any]) -> dict[str, Any]:
    """Append a later native source revision without changing the as-known Q.

    correction requires original_claim_id, corrected_claim_id, reason,
    correction_kind (source_correction/mapping_error/time_travel), and an existing
    ``source_document.v1`` in corrected_document. The native successor must link
    the original source document, preserve its event ID and advance revision by
    one. A mapping/time-travel exception requests quarantine; it never rewrites
    the primary exposure or automatically produces corrected-truth labels.
    """
    original, link = _snapshot(receipt), _snapshot(correction)
    _shape(link, {"original_claim_id": str, "corrected_claim_id": str, "reason": str,
                  "correction_kind": str, "corrected_document": _DOCUMENT_SHAPE}, "correction")
    if not verify_quality_receipt(original):
        raise QualityContractError("original receipt integrity failed")
    if type(link) is not dict or not all(_text(link.get(k)) for k in ("original_claim_id", "corrected_claim_id", "reason")) or link.get("correction_kind") not in {"source_correction", "mapping_error", "time_travel"}:
        raise QualityContractError("correction receipt is incomplete")
    evidence = [entry for event in original["input_packet"]["events"] for entry in event.get("evidence", []) if entry.get("claim_id") == link["original_claim_id"]]
    if len(evidence) != 1:
        raise QualityContractError("correction must resolve one original owner claim")
    old_id = evidence[0]["source_span"]["document_id"]
    old = _native_document(original["input_packet"]["source_documents"][old_id])
    new = _native_document(link.get("corrected_document"))
    if new.event_id != old.event_id or new.document_id == old.document_id or new.revision != old.revision + 1 or new.supersedes_document_id not in {old.document_id, old.content_sha256}:
        raise QualityContractError("correction does not preserve the owner's revision identity")
    payload = link["corrected_document"]
    public, available, observed = (_instant(payload.get(k)) for k in ("published_at", "available_at", "fetched_at"))
    if not public <= available <= observed or max(available, observed) <= _instant(original["decision_cut"]):
        raise QualityContractError("later correction must carry a later first-known clock")
    wrapper = {
        "schema": "pb_d_quality_correction.v1", "authority": "research_only", "authority_flags": dict(AUTHORITY_FLAGS),
        "original_receipt": original, "original_receipt_sha256": original["receipt_sha256"],
        "primary_q": original["q"], "correction_links": [link],
        "quarantine_required": link["correction_kind"] in {"mapping_error", "time_travel"},
        "corrected_truth_state": "not_evaluated",
    }
    wrapper["receipt_sha256"] = _digest(wrapper)
    return wrapper
