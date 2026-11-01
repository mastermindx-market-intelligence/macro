from __future__ import annotations

import hashlib
import json

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
        "message": "research report is not visible to this caller",
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


_LEGACY_PASSAGE_KEYS = (
    "schema",
    "report_id",
    "title",
    "institution",
    "published_at",
    "source_pdf_sha256",
    "extracted_text_sha256",
    "extractor_name",
    "extractor_version",
    "segmenter_version",
    "segment_index",
    "page_start",
    "page_end",
    "start_byte",
    "end_byte",
    "passage_text_sha256",
    "text",
    "coverage_state",
    "replay_state",
    "open_source_ref",
)


def _match_kwargs(text="alpha MATCH omega", start=5000):
    match_at = text.index("MATCH")
    return {
        "start_char": start,
        "end_char": start + len(text),
        "match_start_char": start + match_at,
        "match_end_char": start + match_at + 5,
        "match_text": "MATCH",
        "matched_terms": ["match"],
    }


def _passage_with(text="literal source sentence", **kwargs):
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
        **kwargs,
    )


def test_evidence_passage_without_match_fields_is_byte_identical_v1():
    passage = _passage_with()
    assert tuple(passage) == _LEGACY_PASSAGE_KEYS
    assert len(_LEGACY_PASSAGE_KEYS) == 20
    assert len(passage) == 20
    assert passage == _passage()
    dumped = json.dumps(passage, sort_keys=False)
    assert "start_char" not in dumped
    assert "matched_terms" not in dumped
    assert read_port.EVIDENCE_SCHEMA == "research.evidence_passage.v1"


def test_evidence_passage_round_trips_absolute_match_locator():
    text = "alpha MATCH omega"
    kwargs = _match_kwargs(text=text, start=5000)
    passage = _passage_with(text, **kwargs)
    for key in read_port.EVIDENCE_MATCH_FIELDS:
        assert passage[key] == kwargs[key]
    assert isinstance(passage["matched_terms"], list)
    assert passage["matched_terms"] is not kwargs["matched_terms"]
    assert list(passage)[-6:] == list(read_port.EVIDENCE_MATCH_FIELDS)
    relative_start = passage["match_start_char"] - passage["start_char"]
    relative_end = passage["match_end_char"] - passage["start_char"]
    assert passage["text"][relative_start:relative_end] == passage["match_text"]
    assert json.loads(json.dumps(passage)) == passage


@pytest.mark.parametrize(
    "dropped",
    [*read_port.EVIDENCE_MATCH_FIELDS, "ONLY_MATCH_TEXT"],
)
def test_match_fields_partial_presence_is_value_error(dropped):
    text = "alpha MATCH omega"
    if dropped == "ONLY_MATCH_TEXT":
        with pytest.raises(ValueError, match="all present or all absent"):
            _passage_with(text, match_text="MATCH")
        return
    kwargs = _match_kwargs(text=text)
    kwargs[dropped] = None
    with pytest.raises(ValueError, match="all present or all absent"):
        _passage_with(text, **kwargs)


@pytest.mark.parametrize("field", read_port.EVIDENCE_MATCH_FIELDS[:4])
@pytest.mark.parametrize("bad", [True, -1, 1.0, "5"])
def test_match_offsets_refuse_bool_negative_and_non_int(field, bad):
    text = "alpha MATCH omega"
    kwargs = _match_kwargs(text=text)
    kwargs[field] = bad
    with pytest.raises(ValueError, match="nonnegative int"):
        _passage_with(text, **kwargs)


@pytest.mark.parametrize("mutate", ["before_start", "empty_match", "past_end"])
def test_match_offsets_refuse_incoherent_order(mutate):
    text = "alpha MATCH omega"
    kwargs = _match_kwargs(text=text)
    if mutate == "before_start":
        kwargs["match_start_char"] = kwargs["start_char"] - 1
        kwargs["match_end_char"] = kwargs["start_char"]
        kwargs["match_text"] = ""
    elif mutate == "empty_match":
        kwargs["match_end_char"] = kwargs["match_start_char"]
        kwargs["match_text"] = ""
    else:
        relative = kwargs["match_start_char"] - kwargs["start_char"]
        kwargs["match_end_char"] = kwargs["end_char"] + 1
        kwargs["match_text"] = text[relative:]
    assert kwargs["end_char"] - kwargs["start_char"] == len(text)
    with pytest.raises(ValueError, match="incoherent"):
        _passage_with(text, **kwargs)


def test_match_span_must_equal_text_length():
    text = "alpha MATCH omega"
    kwargs = _match_kwargs(text=text)
    kwargs["end_char"] = kwargs["start_char"] + len(text) + 1
    with pytest.raises(ValueError):
        _passage_with(text, **kwargs)


def test_match_text_must_equal_text_slice():
    text = "alpha MATCH omega"
    wrong = _match_kwargs(text=text)
    wrong["match_text"] = "MATCX"
    with pytest.raises(ValueError):
        _passage_with(text, **wrong)
    spaced = _match_kwargs(text=text)
    spaced["match_text"] = " MATCH"
    with pytest.raises(ValueError):
        _passage_with(text, **spaced)


@pytest.mark.parametrize(
    ("terms", "accepted"),
    [
        (["term"] * (read_port.EVIDENCE_MATCHED_TERMS_MAX + 1), False),
        (["a" * (read_port.EVIDENCE_MATCHED_TERM_MAX_CHARS + 1)], False),
        ([""], False),
        (
            ["a" * read_port.EVIDENCE_MATCHED_TERM_MAX_CHARS]
            * read_port.EVIDENCE_MATCHED_TERMS_MAX,
            True,
        ),
    ],
)
def test_matched_terms_bounds(terms, accepted):
    text = "alpha MATCH omega"
    kwargs = _match_kwargs(text=text)
    kwargs["matched_terms"] = terms
    if accepted:
        passage = _passage_with(text, **kwargs)
        assert passage["matched_terms"] == list(terms)
    else:
        with pytest.raises(ValueError):
            _passage_with(text, **kwargs)


def test_matched_terms_refuse_string_and_non_str():
    text = "alpha MATCH omega"
    as_string = _match_kwargs(text=text)
    as_string["matched_terms"] = "match"
    with pytest.raises(ValueError):
        _passage_with(text, **as_string)
    mixed = _match_kwargs(text=text)
    mixed["matched_terms"] = ["match", 7]
    with pytest.raises(ValueError):
        _passage_with(text, **mixed)
    as_tuple = _match_kwargs(text=text)
    as_tuple["matched_terms"] = ("match",)
    passage = _passage_with(text, **as_tuple)
    assert passage["matched_terms"] == ["match"]
    assert isinstance(passage["matched_terms"], list)


def test_match_bound_constants_are_pinned():
    assert read_port.EVIDENCE_MATCHED_TERMS_MAX == 16
    assert read_port.EVIDENCE_MATCHED_TERM_MAX_CHARS == 120


def _evidence_kwargs(**overrides):
    payload = {
        "report_id": "r1",
        "evidence_state": "NOT_FOUND",
        "coverage_state": "FULL_TEXT",
        "source": _source(),
        "passages": [],
        "rio_state": "NOT_REQUESTED",
    }
    payload.update(overrides)
    return payload


def test_evidence_result_absent_search_scope_is_byte_identical():
    bare = read_port.evidence_result(**_evidence_kwargs())
    explicit = read_port.evidence_result(
        **_evidence_kwargs(
            searched_char_count=None,
            text_layer_state=None,
            page_count=None,
        )
    )
    assert json.dumps(bare) == json.dumps(explicit)
    assert list(bare) == list(explicit)
    assert list(bare) == [
        "schema",
        "ok",
        "report_id",
        "evidence_state",
        "coverage_state",
        "source",
        "rio_state",
        "passages",
    ]


@pytest.mark.parametrize(
    ("searched", "layer", "pages"),
    [
        (0, "none", 1),
        (12, "thin", 3),
        (100, "full", 2),
    ],
)
def test_evidence_result_search_scope_round_trip_and_key_order(searched, layer, pages):
    result = read_port.evidence_result(
        **_evidence_kwargs(
            evidence_state="FOUND",
            passages=[_passage()],
            searched_char_count=searched,
            text_layer_state=layer,
            page_count=pages,
        )
    )
    assert result["searched_char_count"] == searched
    assert result["text_layer_state"] == layer
    assert result["page_count"] == pages
    assert list(result)[-4:] == [
        "passages",
        "searched_char_count",
        "text_layer_state",
        "page_count",
    ]


@pytest.mark.parametrize(
    "coverage",
    ["NO_TEXT_LAYER", "EXTRACTION_UNAVAILABLE", "PREFIX_ONLY_LEGACY"],
)
def test_search_scope_requires_full_text_coverage(coverage):
    with pytest.raises(ValueError, match="FULL_TEXT"):
        read_port.evidence_result(
            **_evidence_kwargs(
                evidence_state="UNAVAILABLE",
                coverage_state=coverage,
                searched_char_count=10,
                text_layer_state="full",
                page_count=1,
            )
        )


@pytest.mark.parametrize("value", [True, -1, 1.0])
def test_searched_char_count_refuses_non_literal_nonnegative(value):
    with pytest.raises(ValueError):
        read_port.evidence_result(
            **_evidence_kwargs(
                searched_char_count=value,
                text_layer_state="full",
                page_count=1,
            )
        )


@pytest.mark.parametrize("layer", ["", "FULL", "unavailable", "bogus"])
def test_search_scope_refuses_bad_text_layer(layer):
    with pytest.raises(ValueError):
        read_port.evidence_result(
            **_evidence_kwargs(
                searched_char_count=4,
                text_layer_state=layer,
                page_count=1,
            )
        )


@pytest.mark.parametrize("pages", [0, True, None])
def test_search_scope_refuses_bad_page_count(pages):
    with pytest.raises(ValueError):
        read_port.evidence_result(
            **_evidence_kwargs(
                searched_char_count=4,
                text_layer_state="full",
                page_count=pages,
            )
        )


@pytest.mark.parametrize(
    "present",
    [
        {"searched_char_count": 3},
        {"text_layer_state": "full"},
        {"page_count": 2},
        {"searched_char_count": 3, "text_layer_state": "full"},
        {"searched_char_count": 3, "page_count": 2},
        {"text_layer_state": "thin", "page_count": 2},
    ],
)
def test_search_scope_partial_blocks_are_refused(present):
    with pytest.raises(ValueError, match="all present or all absent"):
        read_port.evidence_result(**_evidence_kwargs(**present))
