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
        (len(body) + 1, "prefix_partial", True, len(body) + 1),
        (len(body), "complete", False, len(body)),
        (None, "unknown", None, None),
        ("not-a-count", "unknown", None, None),
        (str(len(body)), "unknown", None, None),
        (float(len(body)), "unknown", None, None),
        (-1, "unknown", None, None),
        (0, "unknown", None, None),
        (len(body) - 1, "unknown", None, None),
        (True, "unknown", None, None),
        (False, "unknown", None, None),
        (len(body) - 0.5, "unknown", None, None),
    )

    for char_count, coverage, tail_omitted, source_char_count in cases:
        result = corpus.find_evidence_passages(
            _doc(body, char_count=char_count), "evidence"
        )
        binding = result["source_binding"]
        assert binding["coverage"] == coverage, char_count
        assert binding["tail_omitted"] is tail_omitted, char_count
        assert binding["source_char_count"] is source_char_count, char_count


def test_evidence_integer_helper_accepts_only_literal_nonnegative_ints():
    assert corpus._evidence_int(0) == 0
    assert corpus._evidence_int(7) == 7
    for malformed in (True, False, "7", " 7 ", 7.0, 1.5, -0.5, -1, None):
        assert corpus._evidence_int(malformed) is None, malformed


def test_source_binding_rejects_coercible_page_counts():
    body = "stored evidence body"
    assert corpus._source_binding(_doc(body, pages=7), body)["page_count"] == 7
    for malformed in ("7", " 7 ", 7.0, True, False, 0, -1, 1.5, None):
        binding = corpus._source_binding(_doc(body, pages=malformed), body)
        assert binding["page_count"] is None, malformed


def test_no_match_and_noise_query_are_distinct_and_never_manufacture_a_passage():
    body = "Only oil supply is discussed."

    no_match = corpus.find_evidence_passages(_doc(body), "semiconductors")
    noise = corpus.find_evidence_passages(_doc(body), "x")

    assert no_match["status"] == "no_matching_passage"
    assert no_match["passages"] == []
    assert noise["status"] == "query_too_short"
    assert noise["passages"] == []


def test_passage_window_is_bounded_independent_of_match_length():
    """R5 BLOCKER-1: an arbitrarily long single atom (one unsegmented Han run)
    must not widen the emitted window past the configured cap, and the locator
    must stay coherent (start <= match_start < match_end <= end)."""
    han_run = "甲乙丙丁戊己庚辛壬癸" * 2000  # 20,000 Han chars, one atom
    body = "前言。" + han_run + "。结论。"

    result = corpus.find_evidence_passages(_doc(body), han_run, window_chars=900)

    assert result["status"] == "matched"
    passage = result["passages"][0]
    cap = max(80, 900)
    assert len(passage["text"]) <= cap
    assert len(passage["match_text"]) <= cap
    locator = passage["locator"]
    assert 0 <= locator["start_char"] <= locator["match_start_char"]
    assert locator["match_start_char"] < locator["match_end_char"]
    assert locator["match_end_char"] <= locator["end_char"]
    assert locator["end_char"] - locator["start_char"] <= cap
    assert passage["text"] == body[locator["start_char"]:locator["end_char"]]
    assert passage["match_text"] == body[
        locator["match_start_char"]:locator["match_end_char"]
    ]


def test_passage_window_bounded_escalates_across_several_long_atoms():
    """Three separated 8,000-char Han runs must not each smuggle their full
    length through — every passage individually obeys the window cap."""
    chunk = "子丑寅卯辰巳午未申酉" * 800  # 8,000 Han chars
    body = f"{chunk}。ASCII break。{chunk}。ASCII break two。{chunk}"

    result = corpus.find_evidence_passages(_doc(body), chunk, window_chars=900)

    assert result["status"] == "matched"
    cap = max(80, 900)
    for passage in result["passages"]:
        assert len(passage["text"]) <= cap
        assert len(passage["match_text"]) <= cap


def test_ascii_identifier_matches_adjacent_to_han_script():
    """R5 MAJOR-2(b): Han is not an ASCII identifier continuation, so a Latin
    ticker/acronym directly against Chinese prose must still match — but a
    genuinely longer ASCII sibling (AAPLX) must still be rejected."""
    fed = corpus.find_evidence_passages(_doc("美联储fed决议维持利率不变。"), "fed")
    assert fed["status"] == "matched"
    assert fed["passages"][0]["match_text"] == "fed"

    gdp = corpus.find_evidence_passages(_doc("上半年GDP增长放缓。"), "GDP")
    assert gdp["status"] == "matched"
    assert gdp["passages"][0]["match_text"] == "GDP"

    cpi = corpus.find_evidence_passages(_doc("本月CPI数据超预期。"), "CPI")
    assert cpi["status"] == "matched"

    aapl = corpus.find_evidence_passages(_doc("苹果AAPL公司业绩强劲。"), "AAPL")
    assert aapl["status"] == "matched"
    assert aapl["passages"][0]["match_text"] == "AAPL"

    decoy = corpus.find_evidence_passages(_doc("苹果AAPLX决议。"), "AAPL")
    assert decoy["status"] == "no_matching_passage", "AAPLX is not an AAPL hit"


def test_source_identity_fails_closed_for_missing_or_malformed_content_sha256():
    """R5 requirement 2: a source-bound passage requires a canonical lowercase
    64-hex content_sha256. Any other shape must yield no passages/body, zero
    debit-eligible status, and an unpolluted binding — never a match."""
    body = "The desk raised AAPL demand estimates after channel checks."
    bad_hashes = (
        None, "", "   ", "not-a-sha", "a" * 63, "a" * 65,
        "A" * 64, " " + ("a" * 64), ("a" * 64) + " ",
        "g" * 64,  # non-hex
        12345, 1.5, True, [], {},
    )
    for bad in bad_hashes:
        result = corpus.find_evidence_passages(
            _doc(body, content_sha256=bad), "AAPL demand"
        )
        assert result["status"] == "body_unavailable", bad
        assert result["passages"] == [], bad
        assert result["source_binding"]["content_sha256"] == "", bad

    # A genuinely valid digest still matches — the gate is precise, not blanket.
    good = corpus.find_evidence_passages(
        _doc(body, content_sha256="a" * 64), "AAPL demand"
    )
    assert good["status"] == "matched"


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


def _malformed_body_doc(body) -> dict:
    return {
        "doc_id": "desk-note-1",
        "body": body,
        "text_layer": "full",
        "content_sha256": "a" * 64,
        "char_count": 0,
        "pages": 0,
    }


def test_non_string_body_values_fail_closed_without_python_repr_evidence():
    """A corpus body is publisher text only when it is already a string."""
    cases = (
        {"topic": "AAPL demand estimates"},
        ["AAPL demand estimates are rising."],
        ("AAPL demand",),
        12345,
        1.5,
        True,
    )
    for malformed in cases:
        doc = (
            _doc(malformed, char_count=0)
            if isinstance(malformed, (dict, list, tuple))
            else _malformed_body_doc(malformed)
        )
        result = corpus.find_evidence_passages(doc, "AAPL demand")
        assert result["status"] == "body_unavailable", malformed
        assert result["passages"] == [], malformed
        assert result["source_binding"]["stored_char_count"] == 0, malformed
        assert result["source_binding"]["stored_body_sha256"] == hashlib.sha256(b"").hexdigest(), malformed


def _long_window_body() -> str:
    return ("prefix " * 5_000) + (
        "AAPL demand estimates rose sharply this quarter."
    ) + (" suffix" * 5_000)


def test_caller_sized_window_is_clamped_to_frozen_safe_maximum():
    body = _long_window_body()

    result = corpus.find_evidence_passages(
        _doc(body), "AAPL demand", window_chars=10**9)

    assert result["status"] == "matched"
    passage = result["passages"][0]
    assert len(passage["text"]) <= corpus.EVIDENCE_WINDOW_CHARS
    assert len(passage["match_text"]) <= corpus.EVIDENCE_WINDOW_CHARS
    assert (passage["locator"]["end_char"]
            - passage["locator"]["start_char"]) <= corpus.EVIDENCE_WINDOW_CHARS


def test_nonliteral_window_values_use_the_safe_default_without_coercion():
    body = _long_window_body()
    baseline = corpus.find_evidence_passages(_doc(body), "AAPL demand")
    expected = baseline["passages"][0]

    for malformed in (True, False, "900", "50", 900.0, 50.0, None):
        result = corpus.find_evidence_passages(
            _doc(body), "AAPL demand", window_chars=malformed)
        assert result["status"] == "matched", malformed
        passage = result["passages"][0]
        assert passage["locator"] == expected["locator"], malformed
        assert passage["text"] == expected["text"], malformed


def test_literal_window_values_clamp_to_existing_safe_interval():
    body = _long_window_body()

    small = corpus.find_evidence_passages(
        _doc(body), "AAPL demand", window_chars=40)
    large = corpus.find_evidence_passages(
        _doc(body), "AAPL demand", window_chars=5_000)

    assert len(small["passages"][0]["text"]) <= 80
    assert len(large["passages"][0]["text"]) <= corpus.EVIDENCE_WINDOW_CHARS
