from __future__ import annotations

import hashlib

import pytest

from engine.research_vault import read_port


PDF = hashlib.sha256(b"pdf").hexdigest()
TEXT = hashlib.sha256(b"text-artifact").hexdigest()


def _source(state="SOURCE_FRESH"):
    return read_port.source_state(
        state=state,
        catalog_generated_at="2026-10-05T08:00:00Z",
        latest_report_published_at="2026-10-05T07:30:00Z",
        source_age_hours=0.5,
        report_count=2778,
        known_degradation=[],
    )


def _passage(text="literal source sentence"):
    raw = text.encode("utf-8")
    return read_port.evidence_passage(
        report_id="r1",
        title="Institutional report",
        institution="Example Bank",
        published_at="2026-10-05T07:30:00Z",
        source_pdf_sha256=PDF,
        extracted_text_sha256=TEXT,
        extractor_name="pdftotext",
        extractor_version="poppler-layout-v1",
        segmenter_version="page-byte-v1",
        segment_index=2,
        page_start=7,
        page_end=7,
        start_byte=1000,
        end_byte=1000 + len(raw),
        text=text,
        coverage_state="FULL_TEXT",
    )


def test_status_can_be_successful_while_producer_is_stale():
    result = read_port.status_result(
        source=_source("PRODUCER_STALE"),
        corpus_state="AVAILABLE",
        full_text_coverage=0.7,
        rio_coverage=0.2,
    )
    assert result["ok"] is True
    assert result["source"]["state"] == "PRODUCER_STALE"


def test_stale_source_is_not_an_operational_failure_code():
    assert "SOURCE_STALE" not in read_port.FAILURE_CODES
    with pytest.raises(ValueError, match="unsupported failure"):
        read_port.failure("SOURCE_STALE")


def test_evidence_passage_hashes_literal_utf8_bytes():
    text = "Literal α evidence."
    passage = _passage(text)
    assert passage["passage_text_sha256"] == hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()
    assert passage["replay_state"] == "EXACT"


def test_evidence_passage_refuses_byte_range_that_does_not_match_text():
    with pytest.raises(ValueError, match="byte range"):
        read_port.evidence_passage(
            report_id="r1",
            title="Institutional report",
            institution="Example Bank",
            published_at="2026-10-05",
            source_pdf_sha256=PDF,
            extracted_text_sha256=TEXT,
            extractor_name="pdftotext",
            extractor_version="v1",
            segmenter_version="s1",
            segment_index=0,
            page_start=1,
            page_end=1,
            start_byte=0,
            end_byte=999,
            text="short",
            coverage_state="FULL_TEXT",
        )


def test_found_requires_literal_passage_even_when_rio_is_current():
    with pytest.raises(ValueError, match="FOUND requires"):
        read_port.evidence_result(
            report_id="r1",
            evidence_state="FOUND",
            coverage_state="FULL_TEXT",
            source=_source(),
            passages=[],
            rio_state="CURRENT",
        )


def test_not_found_may_report_current_rio_without_converting_to_evidence():
    result = read_port.evidence_result(
        report_id="r1",
        evidence_state="NOT_FOUND",
        coverage_state="FULL_TEXT",
        source=_source(),
        passages=[],
        rio_state="CURRENT",
    )
    assert result["ok"] is True
    assert result["rio_state"] == "CURRENT"
    assert result["evidence_state"] == "NOT_FOUND"
    assert result["passages"] == []


def test_unavailable_evidence_is_typed_not_an_empty_success_guess():
    result = read_port.evidence_result(
        report_id="r1",
        evidence_state="UNAVAILABLE",
        coverage_state="NO_TEXT_LAYER",
        source=_source(),
        passages=[],
        rio_state="MISSING",
    )
    assert result["evidence_state"] == "UNAVAILABLE"
    assert result["coverage_state"] == "NO_TEXT_LAYER"


def test_partial_requires_at_least_one_literal_passage():
    with pytest.raises(ValueError, match="PARTIAL requires"):
        read_port.evidence_result(
            report_id="r1",
            evidence_state="PARTIAL",
            coverage_state="PARTIAL_CORPUS",
            source=_source(),
            passages=[],
        )


def test_passage_report_identity_must_match_result():
    with pytest.raises(ValueError, match="report_id mismatch"):
        read_port.evidence_result(
            report_id="different",
            evidence_state="FOUND",
            coverage_state="FULL_TEXT",
            source=_source(),
            passages=[_passage()],
        )


def test_failure_is_closed_and_sanitized_shape():
    failure = read_port.failure(
        "REPORT_NOT_ENTITLED",
        retryable=False,
    )
    assert failure == {
        "schema": "research_vault.read_failure.v1",
        "ok": False,
        "code": "REPORT_NOT_ENTITLED",
        "message": "report is not visible to this caller",
        "retryable": False,
    }
    assert "bucket" not in failure
    assert "credential" not in failure


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_source_age_refuses_nonfinite_or_negative_values(value):
    with pytest.raises(ValueError, match="source_age_hours"):
        read_port.source_state(
            state="SOURCE_FRESH",
            catalog_generated_at=None,
            latest_report_published_at=None,
            source_age_hours=value,
            report_count=1,
        )


def test_status_coverage_ratios_are_bounded():
    with pytest.raises(ValueError, match="coverage ratios"):
        read_port.status_result(
            source=_source(),
            corpus_state="AVAILABLE",
            full_text_coverage=1.01,
            rio_coverage=0,
        )


def test_failure_does_not_accept_caller_supplied_exception_prose():
    with pytest.raises(TypeError):
        read_port.failure(
            "INTERNAL_UNAVAILABLE",
            message="s3://private-bucket secret=should-never-reflect",
        )


def test_source_degradation_is_closed_code_not_arbitrary_prose():
    with pytest.raises(ValueError, match="degradation"):
        read_port.source_state(
            state="PRODUCER_STALE",
            catalog_generated_at=None,
            latest_report_published_at=None,
            source_age_hours=100,
            report_count=2778,
            known_degradation=["bucket=/secret/path"],
        )

    source = read_port.source_state(
        state="PRODUCER_STALE",
        catalog_generated_at=None,
        latest_report_published_at=None,
        source_age_hours=100,
        report_count=2778,
        known_degradation=["PRODUCER_STALE", "PARTIAL_CORPUS"],
    )
    assert source["known_degradation"] == ["PRODUCER_STALE", "PARTIAL_CORPUS"]
