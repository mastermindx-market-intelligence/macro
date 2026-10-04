"""Deterministic full-text and segment derivatives for Research Vault.

This module is deliberately pure. It does not read R2, publish objects, open the
legacy FTS corpus, or call an extractor. The incumbent ingest owner supplies the
exact raw pdftotext result plus measured PDF identity; this module binds those
bytes to an explicit text identity and a replayable segment address space.

No whitespace normalization is performed. Form-feed page separators emitted by
pdftotext are retained byte-for-byte.
"""
from __future__ import annotations

import hashlib
from typing import Any

EXTRACTED_TEXT_SCHEMA = "research_vault.extracted_text.v1"
SEGMENT_SCHEMA = "research_vault.segment.v1"
REPLAY_EXACT = "EXACT"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty")
    return value


def _require_sha256(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase sha256")
    return value


def page_boundaries(text: str) -> list[dict[str, int]]:
    """Return 1-based page byte spans from literal form-feed separators.

    start_byte and end_byte cover page text only. separator_end_byte additionally
    consumes the following form feed when one exists, which makes adjacent
    page-aligned segments contiguous over the exact source bytes.

    A trailing form feed does not fabricate an extra empty page. Interior empty
    pages are retained because they are part of the source layout.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not text:
        return []

    parts = text.split("\f")
    boundaries: list[dict[str, int]] = []
    cursor = 0
    for index, part in enumerate(parts):
        has_separator = index < len(parts) - 1
        if index == len(parts) - 1 and part == "" and text.endswith("\f"):
            break
        encoded = part.encode("utf-8")
        start = cursor
        end = start + len(encoded)
        separator_end = end + (1 if has_separator else 0)
        boundaries.append(
            {
                "page_index": index + 1,
                "start_byte": start,
                "end_byte": end,
                "separator_end_byte": separator_end,
            }
        )
        cursor = separator_end
    return boundaries


def build_extracted_text(
    *,
    report_id: str,
    source_pdf_sha256: str,
    text: str | None,
    extractor_name: str,
    extractor_version: str,
    page_count: int | None,
    text_layer_state: str,
    computed_at: str = "",
) -> dict[str, Any]:
    """Build the canonical private full-text derivative.

    text=None means extraction was unavailable. The stored canonical text is then
    the empty string, but text_layer_state must preserve that epistemic
    distinction, normally unavailable.

    computed_at is metadata, not identity. Leaving it blank keeps hermetic builds
    byte-for-byte deterministic.
    """
    report_id = _require_text(report_id, "report_id")
    source_pdf_sha256 = _require_sha256(source_pdf_sha256, "source_pdf_sha256")
    extractor_name = _require_text(extractor_name, "extractor_name")
    extractor_version = _require_text(extractor_version, "extractor_version")
    text_layer_state = _require_text(text_layer_state, "text_layer_state")
    if page_count is not None and (type(page_count) is not int or page_count < 0):
        raise ValueError("page_count must be a nonnegative int or None")

    canonical_text = "" if text is None else text
    if not isinstance(canonical_text, str):
        raise TypeError("text must be str or None")
    encoded = canonical_text.encode("utf-8")
    boundaries = page_boundaries(canonical_text)

    return {
        "schema": EXTRACTED_TEXT_SCHEMA,
        "report_id": report_id,
        "source_pdf_sha256": source_pdf_sha256,
        "extractor_name": extractor_name,
        "extractor_version": extractor_version,
        "extracted_text_sha256": _sha256(encoded),
        "char_count": len(canonical_text),
        "byte_count": len(encoded),
        "page_count": page_count,
        "page_boundaries": boundaries,
        "text_layer_state": text_layer_state,
        "computed_at": computed_at if isinstance(computed_at, str) else "",
        "text": canonical_text,
    }


def _validate_extracted_text(artifact: dict[str, Any]) -> bytes:
    if not isinstance(artifact, dict) or artifact.get("schema") != EXTRACTED_TEXT_SCHEMA:
        raise ValueError("unsupported extracted-text artifact")
    _require_text(artifact.get("report_id"), "report_id")
    _require_sha256(artifact.get("source_pdf_sha256"), "source_pdf_sha256")
    digest = _require_sha256(
        artifact.get("extracted_text_sha256"), "extracted_text_sha256"
    )
    text = artifact.get("text")
    if not isinstance(text, str):
        raise ValueError("extracted-text artifact text must be str")
    encoded = text.encode("utf-8")
    if _sha256(encoded) != digest:
        raise ValueError("extracted-text artifact text hash mismatch")
    if artifact.get("byte_count") != len(encoded):
        raise ValueError("extracted-text artifact byte_count mismatch")
    if artifact.get("char_count") != len(text):
        raise ValueError("extracted-text artifact char_count mismatch")
    if artifact.get("page_boundaries") != page_boundaries(text):
        raise ValueError("extracted-text artifact page boundaries mismatch")
    return encoded


def _safe_utf8_end(data: bytes, start: int, hard_end: int) -> int:
    """Return an exclusive UTF-8 boundary not past hard_end."""
    if hard_end >= len(data):
        return len(data)
    end = hard_end
    while end > start and (data[end] & 0xC0) == 0x80:
        end -= 1
    if end <= start:
        raise ValueError("segment max_bytes is smaller than the next UTF-8 codepoint")
    return end


def _pages_for_span(
    boundaries: list[dict[str, int]], start: int, end: int
) -> tuple[int | None, int | None]:
    touched = [
        boundary["page_index"]
        for boundary in boundaries
        if start < boundary["separator_end_byte"]
        and end > boundary["start_byte"]
    ]
    if not touched:
        return None, None
    return touched[0], touched[-1]


def build_segments(
    extracted: dict[str, Any],
    *,
    segmenter_version: str,
    max_bytes: int,
) -> list[dict[str, Any]]:
    """Build deterministic, exact-replay segments over canonical UTF-8 bytes.

    The production byte budget is intentionally supplied by the caller rather
    than frozen here. F5 benchmarking chooses that policy later. Whenever a page
    separator falls in the latter half of the current byte window, the segment
    ends on that separator; otherwise it uses the largest safe UTF-8 boundary.
    """
    segmenter_version = _require_text(segmenter_version, "segmenter_version")
    if type(max_bytes) is not int or max_bytes < 4:
        raise ValueError("max_bytes must be an int >= 4")

    data = _validate_extracted_text(extracted)
    if not data:
        return []

    boundaries = extracted["page_boundaries"]
    segments: list[dict[str, Any]] = []
    start = 0
    index = 0

    while start < len(data):
        safe_end = _safe_utf8_end(data, start, min(len(data), start + max_bytes))
        minimum_preferred = start + max(1, max_bytes // 2)
        page_aligned = [
            boundary["separator_end_byte"]
            for boundary in boundaries
            if minimum_preferred <= boundary["separator_end_byte"] <= safe_end
            and boundary["separator_end_byte"] > start
        ]
        end = page_aligned[-1] if page_aligned else safe_end
        if end <= start:
            raise ValueError("segmenter made no progress")

        segment_bytes = data[start:end]
        segment_text = segment_bytes.decode("utf-8")
        page_start, page_end = _pages_for_span(boundaries, start, end)
        segments.append(
            {
                "schema": SEGMENT_SCHEMA,
                "report_id": extracted["report_id"],
                "source_pdf_sha256": extracted["source_pdf_sha256"],
                "extracted_text_sha256": extracted["extracted_text_sha256"],
                "extractor_version": extracted["extractor_version"],
                "segmenter_version": segmenter_version,
                "segment_max_bytes": max_bytes,
                "segment_index": index,
                "page_start": page_start,
                "page_end": page_end,
                "start_byte": start,
                "end_byte": end,
                "segment_text_sha256": _sha256(segment_bytes),
                "replay_state": REPLAY_EXACT,
                "text": segment_text,
            }
        )
        start = end
        index += 1

    return segments


def replay_segment(
    extracted: dict[str, Any],
    segment: dict[str, Any],
) -> str:
    """Replay and verify one segment exactly from the extracted-text artifact."""
    data = _validate_extracted_text(extracted)
    if not isinstance(segment, dict) or segment.get("schema") != SEGMENT_SCHEMA:
        raise ValueError("unsupported segment artifact")
    for field in ("report_id", "source_pdf_sha256", "extracted_text_sha256"):
        if segment.get(field) != extracted.get(field):
            raise ValueError(f"segment {field} does not match extracted text")
    start = segment.get("start_byte")
    end = segment.get("end_byte")
    if (
        type(start) is not int
        or type(end) is not int
        or start < 0
        or end <= start
        or end > len(data)
    ):
        raise ValueError("segment byte range is invalid")
    replay = data[start:end]
    if _sha256(replay) != segment.get("segment_text_sha256"):
        raise ValueError("segment text hash mismatch")
    text = replay.decode("utf-8")
    if segment.get("text") != text:
        raise ValueError("segment stored text mismatch")
    return text
