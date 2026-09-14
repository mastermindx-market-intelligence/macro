"""R1B source-bound passage selection over the existing Research Vault corpus."""
from __future__ import annotations

import hashlib

from engine.research_vault import corpus


def _doc(body: str, **over) -> dict:
    row = {
        "doc_id": "desk-note-1",
        "body": body,
        "text_layer": "full",
        "content_sha256": "a" * 64,
        "char_count": len(body),
        "pages": 0,
    }
    row.update(over)
    return row


def test_passage_is_centered_on_a_late_match_not_the_document_prefix():
    body = "Opening boilerplate. " + ("unrelated context " * 180) + (
        "Semiconductor inventories are falling faster than demand."
    ) + (" trailing context" * 80)

    result = corpus.find_evidence_passages(_doc(body), "semiconductor inventories")

    assert result["status"] == "matched"
    passage = result["passages"][0]
    assert "Semiconductor inventories" in passage["text"]
    assert passage["locator"]["start_char"] > 1_000
    assert passage["text"] == body[
        passage["locator"]["start_char"]:passage["locator"]["end_char"]
    ]
    assert "Opening boilerplate" not in passage["text"]


def test_width_case_and_original_source_text_are_both_preserved():
    body = "The desk raised AAPL demand estimates after channel checks."

    result = corpus.find_evidence_passages(_doc(body), "ＡＡＰＬ demand")

    passage = result["passages"][0]
    assert passage["match_text"] == "AAPL demand"
    assert "AAPL demand" in passage["text"]
    assert "ＡＡＰＬ" not in passage["text"], "matching normalizes; evidence remains verbatim"
    assert passage["matched_terms"] == ["aapl", "demand"]


def test_ascii_identifiers_match_at_boundaries_not_inside_longer_symbols():
    body = "AAPLX rallied first. Later, AAPL fell after the guide."

    result = corpus.find_evidence_passages(_doc(body), "AAPL", window_chars=40)

    passage = result["passages"][0]
    assert passage["match_text"] == "AAPL"
    assert passage["locator"]["match_start_char"] == body.index("AAPL", body.index("Later"))
    assert passage["locator"]["match_start_char"] != 0, "AAPLX is not an AAPL hit"


def test_cjk_phrase_matches_literally_without_translating_the_source():
    body = "前言。半導體庫存正在下降，但需求仍然穩健。結論。"

    result = corpus.find_evidence_passages(_doc(body), "半導體庫存")

    assert result["status"] == "matched"
    assert result["passages"][0]["match_text"] == "半導體庫存"
    assert result["passages"][0]["matched_terms"] == ["半導體庫存"]


def test_page_locator_is_emitted_only_from_a_real_form_feed_map():
    body = "page one has no match\fpage two discusses credit spreads in depth"

    mapped = corpus.find_evidence_passages(_doc(body, pages=2), "credit spreads")
    unmapped = corpus.find_evidence_passages(
        _doc(body.replace("\f", "\n"), pages=2), "credit spreads"
    )

    assert mapped["passages"][0]["locator"]["kind"] == "page_text_span"
    assert mapped["passages"][0]["locator"]["page"] == 2
    assert unmapped["passages"][0]["locator"]["kind"] == "text_span"
    assert "page" not in unmapped["passages"][0]["locator"]


def test_source_binding_names_exact_pdf_and_stored_body_digests_and_coverage():
    body = "prefix target passage"
    result = corpus.find_evidence_passages(
        _doc(body, char_count=len(body) + 500, pages=7), "target"
    )

    binding = result["source_binding"]
    assert binding == {
        "content_sha256": "a" * 64,
        "stored_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "coverage": "prefix_partial",
        "source_char_count": len(body) + 500,
        "stored_char_count": len(body),
        "tail_omitted": True,
        "text_layer": "full",
        "page_count": 7,
    }


def test_source_binding_fails_closed_for_invalid_or_contradictory_lengths():
    """Bad source counts must never claim complete coverage or an omitted tail."""
    body = "stored evidence body"
    cases = (
        (len(body) + 1, "prefix_partial", True),
        (len(body), "complete", False),
        (None, "unknown", None),
        ("not-a-count", "unknown", None),
        (-1, "unknown", None),
        (0, "unknown", None),
        (len(body) - 1, "unknown", None),
        (True, "unknown", None),
        (False, "unknown", None),
    )

    for char_count, coverage, tail_omitted in cases:
        result = corpus.find_evidence_passages(
            _doc(body, char_count=char_count), "evidence"
        )
        binding = result["source_binding"]
        assert binding["coverage"] == coverage, char_count
        assert binding["tail_omitted"] is tail_omitted, char_count


def test_no_match_and_noise_query_are_distinct_and_never_manufacture_a_passage():
    body = "Only oil supply is discussed."

    no_match = corpus.find_evidence_passages(_doc(body), "semiconductors")
    noise = corpus.find_evidence_passages(_doc(body), "x")

    assert no_match["status"] == "no_matching_passage"
    assert no_match["passages"] == []
    assert noise["status"] == "query_too_short"
    assert noise["passages"] == []


def test_entitled_reader_adds_evidence_metadata_without_widening_legacy_reader(
        tmp_path, monkeypatch):
    import sqlite3

    db_path = tmp_path / "corpus.sqlite"
    conn = corpus.open_db(db_path)
    body = "page one\fpage two target"
    corpus.upsert(
        conn,
        {
            "id": "desk-note-1",
            "title": "Desk note",
            "institution": "Example Bank",
            "side": "sell",
            "published_at": "2026-09-13T12:00:00Z",
            "summary_points": ["A measured summary"],
            "language": "en",
            "pages": 2,
        },
        body,
        facts={
            "pages": 2,
            "language": "en",
            "char_count": len(body) + 80,
            "word_count": 5,
            "text_layer": "full",
            "content_sha256": "b" * 64,
            "byte_size": 1234,
        },
    )
    conn.close()

    def _connect(store_factory=None):
        opened = sqlite3.connect(db_path)
        opened.row_factory = sqlite3.Row
        return opened

    monkeypatch.setattr(corpus, "corpus_connection", _connect)

    legacy = corpus.get_document("desk-note-1")
    evidence = corpus.get_evidence_document("desk-note-1")

    assert set(legacy) == set(corpus.DOCUMENT_FIELDS)
    assert set(evidence) == set(corpus.EVIDENCE_DOCUMENT_FIELDS)
    assert evidence["pages"] == 2
    assert evidence["char_count"] == len(body) + 80
    assert evidence["content_sha256"] == "b" * 64
    assert evidence["body"] == body
