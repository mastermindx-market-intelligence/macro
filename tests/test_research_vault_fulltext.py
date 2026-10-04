from __future__ import annotations

import hashlib

import pytest

from engine.research_vault import fulltext


PDF_A = hashlib.sha256(b"synthetic-pdf-a").hexdigest()
PDF_B = hashlib.sha256(b"synthetic-pdf-b").hexdigest()


def _artifact(text: str | None, *, source_sha: str = PDF_A, pages: int | None = 2):
    return fulltext.build_extracted_text(
        report_id="synthetic-report",
        source_pdf_sha256=source_sha,
        text=text,
        extractor_name="pdftotext",
        extractor_version="poppler-layout-v1",
        page_count=pages,
        text_layer_state="unavailable" if text is None else "full",
    )


def test_extracted_text_identity_preserves_exact_utf8_and_page_offsets():
    text = "Alpha  βeta\n表格\fSecond page\n"
    artifact = _artifact(text)

    encoded = text.encode("utf-8")
    assert artifact["schema"] == "research_vault.extracted_text.v1"
    assert artifact["text"] == text
    assert artifact["char_count"] == len(text)
    assert artifact["byte_count"] == len(encoded)
    assert artifact["extracted_text_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert artifact["source_pdf_sha256"] == PDF_A

    boundary = artifact["page_boundaries"]
    assert len(boundary) == 2
    assert boundary[0]["page_index"] == 1
    assert encoded[boundary[0]["start_byte"]:boundary[0]["end_byte"]].decode() == (
        "Alpha  βeta\n表格"
    )
    assert encoded[boundary[0]["end_byte"]:boundary[0]["separator_end_byte"]] == b"\f"
    assert encoded[boundary[1]["start_byte"]:boundary[1]["end_byte"]].decode() == (
        "Second page\n"
    )


def test_trailing_form_feed_does_not_fabricate_an_empty_page():
    artifact = _artifact("p1\fp2\f", pages=2)
    assert [x["page_index"] for x in artifact["page_boundaries"]] == [1, 2]
    assert artifact["page_boundaries"][-1]["separator_end_byte"] == artifact["byte_count"]


def test_extracted_text_build_is_deterministic_and_does_not_normalize():
    text = "A  B\r\nC\tD\n\nE"
    first = _artifact(text)
    second = _artifact(text)
    assert first == second
    assert first["text"] == text


def test_source_pdf_identity_is_independent_from_extracted_text_identity():
    text = "identical extracted body"
    a = _artifact(text, source_sha=PDF_A)
    b = _artifact(text, source_sha=PDF_B)

    assert a["source_pdf_sha256"] != b["source_pdf_sha256"]
    assert a["extracted_text_sha256"] == b["extracted_text_sha256"]


def test_unavailable_text_is_explicit_and_has_no_segments():
    artifact = _artifact(None, pages=7)
    assert artifact["text"] == ""
    assert artifact["text_layer_state"] == "unavailable"
    assert artifact["page_count"] == 7
    assert artifact["page_boundaries"] == []
    assert artifact["extracted_text_sha256"] == hashlib.sha256(b"").hexdigest()
    assert fulltext.build_segments(
        artifact, segmenter_version="page-byte-v1", max_bytes=64
    ) == []


def test_segments_are_contiguous_bounded_and_exactly_replayable():
    text = "page one αβγ\fpage two with more words\fpage three tail"
    artifact = _artifact(text, pages=3)
    segments = fulltext.build_segments(
        artifact, segmenter_version="page-byte-v1", max_bytes=24
    )

    assert segments
    assert [s["segment_index"] for s in segments] == list(range(len(segments)))
    assert segments[0]["start_byte"] == 0
    assert segments[-1]["end_byte"] == artifact["byte_count"]
    for left, right in zip(segments, segments[1:]):
        assert left["end_byte"] == right["start_byte"]
    for segment in segments:
        assert segment["end_byte"] - segment["start_byte"] <= 24
        assert segment["source_pdf_sha256"] == PDF_A
        assert segment["extracted_text_sha256"] == artifact["extracted_text_sha256"]
        assert segment["replay_state"] == "EXACT"
        assert fulltext.replay_segment(artifact, segment) == segment["text"]

    assert "".join(segment["text"] for segment in segments) == text


def test_segments_never_split_a_utf8_codepoint():
    text = "🙂" * 20 + "\f" + "漢字" * 20
    artifact = _artifact(text, pages=2)
    segments = fulltext.build_segments(
        artifact, segmenter_version="page-byte-v1", max_bytes=13
    )
    assert "".join(s["text"] for s in segments) == text
    assert all((s["end_byte"] - s["start_byte"]) <= 13 for s in segments)


def test_page_aware_segment_prefers_a_late_page_boundary():
    text = ("a" * 12) + "\f" + ("b" * 30)
    artifact = _artifact(text, pages=2)
    segments = fulltext.build_segments(
        artifact, segmenter_version="page-byte-v1", max_bytes=20
    )
    # First form-feed is at byte 12 and separator_end=13, inside latter half
    # of the 20-byte window, so the first segment closes exactly on page 1.
    assert segments[0]["end_byte"] == 13
    assert segments[0]["page_start"] == 1
    assert segments[0]["page_end"] == 1
    assert segments[1]["page_start"] == 2


def test_tail_evidence_past_legacy_60k_cap_is_addressable():
    prefix = ("institutional research line\n" * 2600)
    assert len(prefix) > 60_000
    tail = "TAIL-EVIDENCE-EXACT-REPLAY"
    text = prefix + "\f" + tail
    artifact = _artifact(text, pages=2)
    segments = fulltext.build_segments(
        artifact, segmenter_version="page-byte-v1", max_bytes=8192
    )

    matches = [s for s in segments if tail in s["text"]]
    assert len(matches) == 1
    match = matches[0]
    assert match["start_byte"] > 60_000
    assert fulltext.replay_segment(artifact, match).endswith(tail)


def test_extracted_text_tamper_is_rejected_before_segmentation():
    artifact = _artifact("trusted text")
    artifact["text"] = "tampered text"
    with pytest.raises(ValueError, match="text hash mismatch"):
        fulltext.build_segments(
            artifact, segmenter_version="page-byte-v1", max_bytes=64
        )


def test_segment_tamper_is_rejected_on_replay():
    artifact = _artifact("one two three four five")
    segment = fulltext.build_segments(
        artifact, segmenter_version="page-byte-v1", max_bytes=8
    )[0]
    segment["segment_text_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="segment text hash mismatch"):
        fulltext.replay_segment(artifact, segment)


def test_segment_budget_is_explicit_not_a_hidden_production_default():
    artifact = _artifact("text")
    with pytest.raises(TypeError):
        fulltext.build_segments(artifact, segmenter_version="page-byte-v1")
    with pytest.raises(ValueError, match="max_bytes"):
        fulltext.build_segments(
            artifact, segmenter_version="page-byte-v1", max_bytes=3
        )


def test_text_layer_state_contradictions_fail_closed():
    with pytest.raises(ValueError, match="requires text_layer_state=unavailable"):
        fulltext.build_extracted_text(
            report_id="x",
            source_pdf_sha256=PDF_A,
            text=None,
            extractor_name="pdftotext",
            extractor_version="poppler-layout-v1",
            page_count=1,
            text_layer_state="none",
        )

    with pytest.raises(ValueError, match="empty extracted text requires"):
        fulltext.build_extracted_text(
            report_id="x",
            source_pdf_sha256=PDF_A,
            text="",
            extractor_name="pdftotext",
            extractor_version="poppler-layout-v1",
            page_count=1,
            text_layer_state="full",
        )

    with pytest.raises(ValueError, match="conflicts with text_layer_state"):
        fulltext.build_extracted_text(
            report_id="x",
            source_pdf_sha256=PDF_A,
            text="real text",
            extractor_name="pdftotext",
            extractor_version="poppler-layout-v1",
            page_count=1,
            text_layer_state="none",
        )


def test_pdf_correction_invalidates_old_segment_replay():
    old = _artifact("same visible text", source_sha=PDF_A)
    corrected = _artifact("same visible text", source_sha=PDF_B)
    segment = fulltext.build_segments(
        old, segmenter_version="page-byte-v1", max_bytes=64
    )[0]

    with pytest.raises(ValueError, match="source_pdf_sha256"):
        fulltext.replay_segment(corrected, segment)
