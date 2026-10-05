"""Canonical model-consumer contract for Research Vault reads.

This module freezes semantics shared by future Brain and MCP adapters. It performs
no I/O, owns no authentication implementation, opens no R2 object and selects no
retrieval engine. Callers supply trusted server-side visibility context to an
implementation of ResearchReadPort.

Important distinction:
- producer freshness is a source-state annotation;
- a historically valid read can still be successful while the producer is stale;
- operational failures and authorization failures are separate typed errors.

Literal evidence is represented only by replayable source passages. RIO/model
synthesis is never accepted as evidence text by this contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

READ_SCHEMA = "research_vault.read.v1"
STATUS_SCHEMA = "research_vault.read_status.v1"
SEARCH_SCHEMA = "research_vault.search_result.v1"
FETCH_SCHEMA = "research_vault.fetch_result.v1"
EVIDENCE_SCHEMA = "research.evidence_passage.v1"
EVIDENCE_RESULT_SCHEMA = "research_vault.evidence_result.v1"
FAILURE_SCHEMA = "research_vault.read_failure.v1"

SOURCE_STATES = frozenset({
    "SOURCE_FRESH",
    "PRODUCER_STALE",
    "CATALOG_UNAVAILABLE",
    "NO_REPORTS",
    "LATEST_REPORT_INVALID",
    "FUTURE_REPORT_CLOCK",
})
COVERAGE_STATES = frozenset({
    "FULL_TEXT",
    "PREFIX_ONLY_LEGACY",
    "NO_TEXT_LAYER",
    "EXTRACTION_UNAVAILABLE",
    "SEGMENT_INDEX_PENDING",
    "PARTIAL_CORPUS",
    "SOURCE_REVISION_CHANGED",
})
RIO_STATES = frozenset({"CURRENT", "MISSING", "STALE", "INVALID", "NOT_REQUESTED"})
EVIDENCE_STATES = frozenset({"FOUND", "NOT_FOUND", "UNAVAILABLE", "PARTIAL"})

FAILURE_CODES = frozenset({
    "AUTHENTICATION_REQUIRED",
    "INSUFFICIENT_SCOPE",
    "REPORT_NOT_FOUND",
    "REPORT_NOT_ENTITLED",
    "SOURCE_BODY_UNAVAILABLE",
    "TEXT_LAYER_UNAVAILABLE",
    "FULL_TEXT_NOT_MATERIALIZED",
    "RETRIEVAL_UNAVAILABLE",
    "INVALID_REQUEST",
    "INTERNAL_UNAVAILABLE",
})

_MAX_TEXT_BYTES = 24_000
_MAX_PASSAGES = 12


def _require_text(value: Any, name: str, *, max_len: int = 2000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{name} must be nonempty")
    if len(out) > max_len:
        raise ValueError(f"{name} exceeds bound")
    return out


def _optional_text(value: Any, name: str, *, max_len: int = 2000) -> str | None:
    if value is None:
        return None
    return _require_text(value, name, max_len=max_len)


def _sha(value: Any, name: str) -> str:
    text = _require_text(value, name, max_len=64)
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{name} must be lowercase sha256")
    return text


def _nonnegative_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite nonnegative number")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return out


def _nonnegative_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative int")
    return value


def failure(
    code: str,
    *,
    message: str,
    retryable: bool = False,
) -> dict[str, Any]:
    if code not in FAILURE_CODES:
        raise ValueError(f"unsupported failure code: {code!r}")
    if type(retryable) is not bool:
        raise TypeError("retryable must be bool")
    return {
        "schema": FAILURE_SCHEMA,
        "ok": False,
        "code": code,
        "message": _require_text(message, "message", max_len=500),
        "retryable": retryable,
    }


def source_state(
    *,
    state: str,
    catalog_generated_at: str | None,
    latest_report_published_at: str | None,
    source_age_hours: float | int | None,
    report_count: int,
    known_degradation: Sequence[str] = (),
) -> dict[str, Any]:
    """Build bounded source/currentness state independently from read success."""
    if state not in SOURCE_STATES:
        raise ValueError(f"unsupported source state: {state!r}")
    if source_age_hours is not None:
        source_age_hours = _nonnegative_number(source_age_hours, "source_age_hours")
    report_count = _nonnegative_int(report_count, "report_count")
    degradation: list[str] = []
    for item in known_degradation:
        text = _require_text(item, "known_degradation item", max_len=240)
        if text not in degradation:
            degradation.append(text)
        if len(degradation) >= 24:
            break
    return {
        "state": state,
        "catalog_generated_at": _optional_text(
            catalog_generated_at, "catalog_generated_at", max_len=80
        ),
        "latest_report_published_at": _optional_text(
            latest_report_published_at, "latest_report_published_at", max_len=80
        ),
        "source_age_hours": source_age_hours,
        "report_count": report_count,
        "known_degradation": degradation,
    }


def status_result(
    *,
    source: Mapping[str, Any],
    corpus_state: str,
    full_text_coverage: float | int,
    rio_coverage: float | int,
) -> dict[str, Any]:
    """Status is successful observation even when source state is PRODUCER_STALE."""
    if source.get("state") not in SOURCE_STATES:
        raise ValueError("source state is missing or unsupported")
    corpus_state = _require_text(corpus_state, "corpus_state", max_len=80)
    ft = _nonnegative_number(full_text_coverage, "full_text_coverage")
    rio = _nonnegative_number(rio_coverage, "rio_coverage")
    if ft > 1 or rio > 1:
        raise ValueError("coverage ratios must be <= 1")
    return {
        "schema": STATUS_SCHEMA,
        "ok": True,
        "source": dict(source),
        "corpus_state": corpus_state,
        "full_text_coverage": ft,
        "rio_coverage": rio,
    }


def evidence_passage(
    *,
    report_id: str,
    title: str,
    institution: str,
    published_at: str,
    source_pdf_sha256: str,
    extracted_text_sha256: str,
    extractor_name: str,
    extractor_version: str,
    segmenter_version: str,
    segment_index: int,
    page_start: int | None,
    page_end: int | None,
    start_byte: int,
    end_byte: int,
    text: str,
    coverage_state: str,
    replay_state: str = "EXACT",
    open_source_ref: str | None = None,
) -> dict[str, Any]:
    """Construct one literal source-evidence passage.

    The text hash is computed here from exact UTF-8 bytes. This constructor does
    not claim the offsets are canonical; the Research Vault evidence owner must
    provide a passage already proven against the canonical segment/text artifact.
    """
    if coverage_state not in COVERAGE_STATES:
        raise ValueError("unsupported coverage_state")
    if replay_state != "EXACT":
        raise ValueError("evidence passage must be EXACT replay")
    segment_index = _nonnegative_int(segment_index, "segment_index")
    start_byte = _nonnegative_int(start_byte, "start_byte")
    end_byte = _nonnegative_int(end_byte, "end_byte")
    if end_byte <= start_byte:
        raise ValueError("end_byte must be greater than start_byte")
    if page_start is not None:
        page_start = _nonnegative_int(page_start, "page_start")
        if page_start == 0:
            raise ValueError("page_start is 1-based")
    if page_end is not None:
        page_end = _nonnegative_int(page_end, "page_end")
        if page_end == 0:
            raise ValueError("page_end is 1-based")
    if (page_start is None) != (page_end is None):
        raise ValueError("page_start/page_end must be both present or both absent")
    if page_start is not None and page_end < page_start:
        raise ValueError("page_end must be >= page_start")
    if not isinstance(text, str) or not text:
        raise ValueError("literal evidence text must be nonempty")
    raw = text.encode("utf-8")
    if len(raw) > _MAX_TEXT_BYTES:
        raise ValueError("evidence text exceeds byte bound")
    if len(raw) != end_byte - start_byte:
        raise ValueError("evidence byte range does not match UTF-8 text length")
    return {
        "schema": EVIDENCE_SCHEMA,
        "report_id": _require_text(report_id, "report_id", max_len=240),
        "title": _require_text(title, "title", max_len=500),
        "institution": _require_text(institution, "institution", max_len=200),
        "published_at": _require_text(published_at, "published_at", max_len=80),
        "source_pdf_sha256": _sha(source_pdf_sha256, "source_pdf_sha256"),
        "extracted_text_sha256": _sha(
            extracted_text_sha256, "extracted_text_sha256"
        ),
        "extractor_name": _require_text(extractor_name, "extractor_name", max_len=80),
        "extractor_version": _require_text(
            extractor_version, "extractor_version", max_len=120
        ),
        "segmenter_version": _require_text(
            segmenter_version, "segmenter_version", max_len=120
        ),
        "segment_index": segment_index,
        "page_start": page_start,
        "page_end": page_end,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "passage_text_sha256": hashlib.sha256(raw).hexdigest(),
        "text": text,
        "coverage_state": coverage_state,
        "replay_state": "EXACT",
        "open_source_ref": _optional_text(
            open_source_ref, "open_source_ref", max_len=500
        ),
    }


def evidence_result(
    *,
    report_id: str,
    evidence_state: str,
    coverage_state: str,
    source: Mapping[str, Any],
    passages: Sequence[Mapping[str, Any]] = (),
    rio_state: str = "NOT_REQUESTED",
) -> dict[str, Any]:
    """Build the find_evidence result without allowing RIO to masquerade as evidence."""
    if evidence_state not in EVIDENCE_STATES:
        raise ValueError("unsupported evidence_state")
    if coverage_state not in COVERAGE_STATES:
        raise ValueError("unsupported coverage_state")
    if rio_state not in RIO_STATES:
        raise ValueError("unsupported rio_state")
    if source.get("state") not in SOURCE_STATES:
        raise ValueError("source state is missing or unsupported")
    if len(passages) > _MAX_PASSAGES:
        raise ValueError("too many passages")

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(passages):
        if not isinstance(row, Mapping) or row.get("schema") != EVIDENCE_SCHEMA:
            raise ValueError(f"passages[{index}] is not literal evidence")
        if row.get("report_id") != report_id:
            raise ValueError(f"passages[{index}] report_id mismatch")
        if row.get("replay_state") != "EXACT":
            raise ValueError(f"passages[{index}] is not exact replay")
        rows.append(dict(row))

    if evidence_state == "FOUND" and not rows:
        raise ValueError("FOUND requires at least one literal passage")
    if evidence_state in {"NOT_FOUND", "UNAVAILABLE"} and rows:
        raise ValueError(f"{evidence_state} cannot carry literal passages")
    if evidence_state == "PARTIAL" and not rows:
        raise ValueError("PARTIAL requires the literal passages that were found")

    return {
        "schema": EVIDENCE_RESULT_SCHEMA,
        "ok": True,
        "report_id": _require_text(report_id, "report_id", max_len=240),
        "evidence_state": evidence_state,
        "coverage_state": coverage_state,
        "source": dict(source),
        "rio_state": rio_state,
        "passages": rows,
    }


@runtime_checkable
class ResearchReadPort(Protocol):
    """Semantic owner used by both Brain and MCP adapters.

    Principal/entitlement context is trusted server-side context. A model/tool
    schema must never expose a way to choose principal, tier, R2 bucket, root,
    credential or visibility policy.
    """

    def status(self, *, caller_context: Mapping[str, Any]) -> Mapping[str, Any]:
        ...

    def search(
        self,
        *,
        caller_context: Mapping[str, Any],
        query: str,
        filters: Mapping[str, Any],
        limit: int,
        cursor: str | None,
    ) -> Mapping[str, Any]:
        ...

    def fetch(
        self,
        *,
        caller_context: Mapping[str, Any],
        report_id: str,
        selectors: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ...

    def find_evidence(
        self,
        *,
        caller_context: Mapping[str, Any],
        report_id: str,
        query: str,
        max_passages: int,
    ) -> Mapping[str, Any]:
        ...
