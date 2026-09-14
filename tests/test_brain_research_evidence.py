"""R1B: Brain report questions return source-bound Research Vault evidence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from engine.neuralweb import brain_market_intel as bmi

NOW = datetime(2026, 9, 13, 16, 0, tzinfo=timezone.utc)
PRO = {"user_id": "u-pro-r1b"}
REPORT_ID = "desk-note-1"
PUBLISHED_AT = "2026-09-13T12:00:00Z"
PDF_SHA = "a" * 64


def _seed(root) -> None:
    directory = root / "data" / "research_vault"
    directory.mkdir(parents=True, exist_ok=True)
    item = {
        "id": REPORT_ID,
        "title": "Apple Demand Monitor",
        "institution": "Example Bank",
        "side": "sell",
        "published_at": PUBLISHED_AT,
        "summary_points": ["Channel checks point to improving demand."],
        "tags": [], "tickers": ["AAPL"], "top_pick": False,
    }
    (directory / "catalog.json").write_text(json.dumps({
        "schema": "research_vault.catalog.v1",
        "generated_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": 1,
        "items": [item],
    }), encoding="utf-8")
    (directory / "excerpts.json").write_text(json.dumps({
        "schema": 1,
        "excerpts": {REPORT_ID: ["Public opening paragraph."]},
    }), encoding="utf-8")


def _document(body: str, **over) -> dict:
    row = {
        "doc_id": REPORT_ID,
        "title": "Corpus title",
        "institution": "Example Bank",
        "side": "sell",
        "published_at": PUBLISHED_AT,
        "summary": "Corpus summary",
        "body": body,
        "text_layer": "full",
        "pages": 2,
        "char_count": len(body),
        "content_sha256": PDF_SHA,
    }
    row.update(over)
    return row


def _stub_documents(monkeypatch, body: str, **over):
    from engine.research_vault import corpus

    evidence_calls: list[str] = []
    legacy_calls: list[str] = []
    row = _document(body, **over)

    def evidence(doc_id, store_factory=None):
        evidence_calls.append(doc_id)
        return dict(row)

    def legacy(doc_id, store_factory=None):
        legacy_calls.append(doc_id)
        return {key: row.get(key) for key in corpus.DOCUMENT_FIELDS}

    monkeypatch.setattr(corpus, "get_evidence_document", evidence)
    monkeypatch.setattr(corpus, "get_document", legacy)
    return evidence_calls, legacy_calls


def _stub_quota(monkeypatch, *, allowed=True):
    from engine.research_vault import view_ratelimit

    calls: list[tuple] = []

    def allow(user_id, ip, root=None, now=None):
        calls.append((user_id, ip, now))
        return allowed, {"remaining": 11 if allowed else 0, "limit": 12}

    monkeypatch.setattr(view_ratelimit, "allow", allow)
    return calls


def _report(root, query: str) -> dict:
    return bmi.search_research(
        root, query, mode="report", report_id=REPORT_ID,
        user_ctx=PRO, now=NOW,
    )


def test_meaningful_question_returns_exact_passage_binding_and_open_link(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    body = (
        "Opening boilerplate about the publication. "
        + ("unrelated material " * 80)
        + "\fThe desk raised AAPL demand estimates after channel checks."
    )
    evidence_calls, legacy_calls = _stub_documents(monkeypatch, body)
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "ＡＡＰＬ demand")

    assert result["schema"] == "brain.research_report.v1"
    assert result["report"]["body_truncated"] is True
    assert "AAPL demand" in result["report"]["body_text"]
    assert "Opening boilerplate" not in result["report"]["body_text"]
    assert evidence_calls == [REPORT_ID] and legacy_calls == []
    assert len(debits) == 1
    evidence = result["evidence"]
    assert evidence["schema"] == "brain.research_evidence.v1"
    assert evidence["status"] == "matched"
    assert evidence["query"] == "ＡＡＰＬ demand"
    assert evidence["report_id"] == REPORT_ID
    assert evidence["published_at"] == PUBLISHED_AT
    assert evidence["source_binding"]["content_sha256"] == PDF_SHA
    assert evidence["source_binding"]["stored_body_sha256"]
    assert evidence["source_binding"]["coverage"] == "complete"
    assert evidence["access"] == {"decision": "allowed", "metered": True}

    passage = evidence["passages"][0]
    assert passage["match_text"] == "AAPL demand"
    assert passage["matched_terms"] == ["aapl", "demand"]
    assert passage["locator"]["kind"] == "page_text_span"
    assert passage["locator"]["page"] == 2

    # Rights-safe link (R5 requirement 3): passage-level open_url carries only
    # doc+page — never publisher/match text, never a `find=` param.
    parsed_passage = urlparse(passage["open_url"])
    assert parsed_passage.scheme == "https" and parsed_passage.netloc == "mastermind-x.com"
    assert parsed_passage.path == "/research_vault.html"
    assert parse_qs(parsed_passage.query) == {"doc": [REPORT_ID]}
    assert parse_qs(parsed_passage.fragment) == {"page": ["2"]}
    assert "find" not in passage["open_url"]
    assert "AAPL demand" not in passage["open_url"]

    # Top-level evidence.open_url may additionally carry the bounded,
    # NFKC-normalized user query once, in the fragment, as `q=`.
    parsed_top = urlparse(evidence["open_url"])
    assert parse_qs(parsed_top.query) == {"doc": [REPORT_ID]}
    top_fragment = parse_qs(parsed_top.fragment)
    assert top_fragment["page"] == ["2"]
    assert top_fragment["q"] == ["AAPL demand"]
    assert "find" not in evidence["open_url"]
    assert passage["open_url"] != evidence["open_url"]

    assert "query-centered" in result["note"].lower()
    assert "open source" in result["note"].lower()


def test_no_matching_passage_is_unmetered_and_body_is_omitted(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    evidence_calls, legacy_calls = _stub_documents(
        monkeypatch, "This report only discusses oil supply."
    )
    debits = _stub_quota(monkeypatch)
    result = _report(tmp_path, "semiconductor inventories")

    assert evidence_calls == [REPORT_ID] and legacy_calls == []
    assert debits == []
    assert result["quota"] is None
    assert result["report"]["body_text"] == ""
    assert result["report"]["body_truncated"] is False
    evidence = result["evidence"]
    assert evidence["status"] == "no_matching_passage"
    assert evidence["passages"] == []
    assert evidence["access"] == {"decision": "not_served", "metered": False}
    params = parse_qs(urlparse(evidence["open_url"]).query)
    assert params == {"doc": [REPORT_ID]}
    assert "no matching passage" in result["note"].lower()
    assert "not charged" in result["note"].lower()
    assert "same report" in result["note"].lower()
    assert "empty query" in result["note"].lower()


def test_partial_no_match_names_the_searched_prefix_and_its_counts(
        tmp_path, monkeypatch):
    """A failed lexical search cannot imply absence from an omitted source tail."""
    _seed(tmp_path)
    body = "This report only discusses oil supply."
    _stub_documents(monkeypatch, body, char_count=len(body) + 500)
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "semiconductor inventories")

    assert result["evidence"]["status"] == "no_matching_passage"
    assert debits == []
    note = result["note"].lower()
    assert "stored prefix" in note
    assert f"({len(body)} of {len(body) + 500} source characters)" in note
    assert "does not prove" in note and "omitted tail" in note


def test_no_match_discloses_complete_partial_and_unknown_coverage_distinctly(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    body = "This report only discusses oil supply."
    debits = _stub_quota(monkeypatch)
    notes = {}

    for name, char_count in {
        "complete": len(body),
        "prefix_partial": len(body) + 500,
        "unknown": None,
    }.items():
        _stub_documents(monkeypatch, body, char_count=char_count)
        result = _report(tmp_path, "semiconductor inventories")
        assert result["evidence"]["status"] == "no_matching_passage"
        notes[name] = result["note"].lower()

    assert "stored prefix" not in notes["complete"]
    assert "stored prefix" in notes["prefix_partial"]
    assert "coverage could not be verified" in notes["unknown"]
    assert "absence is not evidence" in notes["unknown"]
    assert len(set(notes.values())) == 3
    assert debits == []


def test_generic_intent_variants_and_noise_keep_the_legacy_full_note_path(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    evidence_calls, legacy_calls = _stub_documents(
        monkeypatch, "The complete stored argument."
    )
    debits = _stub_quota(monkeypatch)

    generic_queries = (
        "Summarize this report.",
        "Can you please summarize this report?",
        "What does this note argue",
        "What is the main argument of this paper?",
        "总结这份报告",
        "请概括这篇研究的主要观点",
        "in", "is it", "what is the", "to be or not to be", "", "x",
    )
    for query in generic_queries:
        result = _report(tmp_path, query)
        assert result["report"]["body_text"] == "The complete stored argument."
        assert result["report"]["body_truncated"] is False
        assert result["evidence"] is None

    assert evidence_calls == []
    assert legacy_calls == [REPORT_ID] * len(generic_queries)
    assert len(debits) == len(generic_queries)


# R5 MAJOR-1 / MAJOR-2(a): the commission's required EN/ZH CATEGORY/STRUCTURE
# generic-intent coverage — not a sentence table, but the classifier must
# recognize each of these shapes as "no residual topic" regardless of phrasing.
_REQUIRED_GENERIC_QUERIES = (
    "Summarize",
    "Please provide an overview",
    "Explain what this report says",
    "Give me the gist of this report",
    "Tell me about this paper",
    "What are the key takeaways from this note?",
    "Break down this research note",
    "What's the thesis of this paper?",
    "Walk me through this report",
    "TL;DR",
    "Please summarise this Example Bank note in bullet points",
    "Summarize the Goldman report",
    "请总结一下",
    "帮我概括一下",
    "这篇讲了什么",
    "这份报告说了什么",
    "请帮我分析这篇研究",
    "主要观点是什么",
)

# The residual-topic controls the same commission requires to STAY on the
# evidence path — generic-sounding vocabulary with a real topic attached must
# never be swallowed by the generic classifier.
_REQUIRED_RESIDUAL_TOPIC_QUERIES = (
    "Summarize inflation expectations",
    "What does this report say about AAPL demand?",
    "Explain the report's view on semiconductor inventories",
    "请总结通胀预期",
    "这篇如何讨论苹果需求",
    "分析美联储利率决议",
)


def test_required_en_zh_generic_phrasings_keep_the_legacy_full_note_path(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    evidence_calls, legacy_calls = _stub_documents(
        monkeypatch, "The complete stored argument about inflation."
    )
    debits = _stub_quota(monkeypatch)

    for query in _REQUIRED_GENERIC_QUERIES:
        result = _report(tmp_path, query)
        assert result["evidence"] is None, query
        assert result["report"]["body_text"] == \
            "The complete stored argument about inflation.", query
        assert result["report"]["body_truncated"] is False, query

    assert evidence_calls == []
    assert legacy_calls == [REPORT_ID] * len(_REQUIRED_GENERIC_QUERIES)
    assert len(debits) == len(_REQUIRED_GENERIC_QUERIES)


def test_generic_intent_with_a_residual_topic_uses_evidence_selection(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    evidence_calls, legacy_calls = _stub_documents(
        monkeypatch, "Inflation expectations are rising."
    )
    debits = _stub_quota(monkeypatch)

    result = _report(
        tmp_path, "Summarize this report's discussion of inflation expectations"
    )

    assert result["evidence"]["status"] == "matched"
    assert evidence_calls == [REPORT_ID]
    assert legacy_calls == []
    assert len(debits) == 1


def test_required_residual_topic_phrasings_use_evidence_selection(
        tmp_path, monkeypatch):
    """R5 MAJOR-1/MAJOR-2(a): each of these must NOT be classified generic —
    a real topic word survives the intent/scaffolding strip, so evidence is
    always populated (whether or not the seeded body happens to match)."""
    _seed(tmp_path)
    body = (
        "本报告认为美联储的利率决议结果将影响通胀预期。"
        " The desk raised AAPL demand estimates after semiconductor "
        "inventory checks."
    )
    evidence_calls, legacy_calls = _stub_documents(monkeypatch, body)
    _stub_quota(monkeypatch)

    for query in _REQUIRED_RESIDUAL_TOPIC_QUERIES:
        result = _report(tmp_path, query)
        assert result["evidence"] is not None, query
        assert result["evidence"]["status"] in {
            "matched", "no_matching_passage",
        }, query

    assert legacy_calls == []
    assert evidence_calls == [REPORT_ID] * len(_REQUIRED_RESIDUAL_TOPIC_QUERIES)


def test_unavailable_evidence_body_is_disclosed_and_unmetered(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    evidence_calls, legacy_calls = _stub_documents(
        monkeypatch, "", text_layer="none", char_count=0
    )
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "AAPL demand")

    assert evidence_calls == [REPORT_ID] and legacy_calls == []
    assert debits == []
    assert result["quota"] is None
    assert result["report"]["body_text"] == ""
    assert result["evidence"]["status"] == "body_unavailable"
    assert result["evidence"]["access"] == {
        "decision": "not_served", "metered": False,
    }
    assert "scanned/image-only" in result["note"]


def test_matched_selector_without_usable_text_is_not_called_an_extraction_failure(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    _stub_documents(monkeypatch, "AAPL demand is accelerating.")
    debits = _stub_quota(monkeypatch)
    monkeypatch.setattr(bmi, "_select_evidence", lambda document, query: {
        "status": "matched",
        "passages": [],
        "source_binding": {
            "coverage": "complete",
            "stored_char_count": 28,
            "source_char_count": 28,
            "tail_omitted": False,
        },
    })

    result = _report(tmp_path, "AAPL demand")

    assert result["evidence"]["status"] == "body_unavailable"
    assert result["report"]["body_text"] == ""
    assert debits == []
    assert "no usable passage text was available" in result["note"].lower()
    assert "not reachable right now" not in result["note"].lower()


def test_missing_source_identity_fails_closed_and_gives_an_honest_note(
        tmp_path, monkeypatch):
    """R5 requirement 2: an unverifiable content_sha256 must give an honest
    source-identity note — never a scan/extraction claim — and must never
    serve or charge for a full-text view."""
    _seed(tmp_path)
    evidence_calls, legacy_calls = _stub_documents(
        monkeypatch, "AAPL demand is accelerating.",
        content_sha256="not-a-valid-sha",
    )
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "AAPL demand")

    assert evidence_calls == [REPORT_ID] and legacy_calls == []
    assert debits == []
    assert result["quota"] is None
    assert result["report"]["body_text"] == ""
    assert result["evidence"]["status"] == "body_unavailable"
    assert result["evidence"]["passages"] == []
    assert result["evidence"]["source_binding"]["content_sha256"] == ""
    note = result["note"].lower()
    assert "source-identity" in note or "source identity" in note
    assert "scanned/image-only" not in result["note"]
    assert "not reachable right now" not in note


def test_denied_evidence_view_leaks_no_passage_or_body(tmp_path, monkeypatch):
    _seed(tmp_path)
    _stub_documents(monkeypatch, "AAPL demand is accelerating.")
    debits = _stub_quota(monkeypatch, allowed=False)

    result = _report(tmp_path, "AAPL demand")

    assert len(debits) == 1
    assert result["error"] == "view_limit_reached"
    assert "report" not in result
    assert "evidence" not in result
    assert "AAPL demand is accelerating" not in json.dumps(result)


def test_exhausted_report_preflight_is_uniform_and_skips_all_document_reads(
        tmp_path, monkeypatch):
    """No exhausted request may reveal whether its terms occur in the paid body."""
    from engine.research_vault import view_ratelimit

    _seed(tmp_path)
    evidence_calls, legacy_calls = _stub_documents(
        monkeypatch, "AAPL demand is accelerating."
    )
    debits = _stub_quota(monkeypatch)
    peeks: list[tuple] = []
    selector_calls: list[str] = []
    original_select = bmi._select_evidence

    def peek(user_id, ip, now=None):
        peeks.append((user_id, ip, now))
        return {"remaining": 0, "limit": 12}

    def select(document, query):
        selector_calls.append(query)
        return original_select(document, query)

    monkeypatch.setattr(view_ratelimit, "peek", peek)
    monkeypatch.setattr(bmi, "_select_evidence", select)

    envelopes = []
    for query in ("summarize this report", "AAPL demand"):
        result = _report(tmp_path, query)
        assert result["error"] == "view_limit_reached"
        assert set(result) == {"schema", "error", "note", "report_id", "remaining", "limit"}
        assert "report" not in result and "evidence" not in result
        envelopes.append(result)

    assert len(peeks) == 2
    assert envelopes[0] == envelopes[1]
    assert selector_calls == []
    assert evidence_calls == []
    assert legacy_calls == []
    assert debits == []


def test_evidence_peek_failure_fails_open_and_a_served_match_still_debits(
        tmp_path, monkeypatch):
    """Read-only limiter trouble preserves availability but never skips the debit."""
    from engine.research_vault import view_ratelimit

    _seed(tmp_path)
    _stub_documents(monkeypatch, "AAPL demand is accelerating.")
    debits = _stub_quota(monkeypatch)
    peeks: list[tuple] = []

    def peek(user_id, ip, now=None):
        peeks.append((user_id, ip, now))
        raise OSError("read-only limiter state")

    monkeypatch.setattr(view_ratelimit, "peek", peek)
    result = _report(tmp_path, "AAPL demand")

    assert result["evidence"]["status"] == "matched"
    assert len(peeks) == 1
    assert len(debits) == 1


def test_evidence_mode_whole_response_obeys_the_existing_response_cap(
        tmp_path, monkeypatch):
    """R5 BLOCKER-1 (H-1 fix): passage mode cannot hide an over-cap text field
    outside body_text. Unlike the predecessor's short-atom query (which
    de-duplicated to a few tokens and never drove the defect), this uses a long
    Han run that actually MATCHES, so a per-node or per-response escape would be
    caught. Reuses the pre-existing owner invariant's per-node `_walk` shape
    (tests/test_brain_market_intel.py:1637) — no key anywhere, including a field
    added later, may exceed the cap — plus the commission's recursive-sum check."""
    _seed(tmp_path)
    han_run = "甲乙丙丁戊己庚辛壬癸" * 2000  # 20,000 Han chars, one unsegmented atom
    body = "前言。" + han_run + "。结论。"
    _stub_documents(monkeypatch, body)
    _stub_quota(monkeypatch)

    result = _report(tmp_path, han_run)

    def _walk(node):
        if isinstance(node, str):
            assert len(node) <= bmi.REPORT_BODY_MAX_CHARS
        elif isinstance(node, dict):
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(result)

    def string_total(node):
        if isinstance(node, str):
            return len(node)
        elif isinstance(node, dict):
            return sum(string_total(value) for value in node.values())
        elif isinstance(node, list):
            return sum(string_total(value) for value in node)
        return 0

    assert string_total(result) <= bmi.REPORT_BODY_MAX_CHARS
    assert result["evidence"]["status"] == "matched"
    assert len(result["evidence"]["passages"][0]["text"]) < len(han_run)
    assert len(result["evidence"]["passages"][0]["match_text"]) < len(han_run)


def test_evidence_mode_whole_response_cap_escalates_across_several_long_atoms(
        tmp_path, monkeypatch):
    """The BLOCKER-1 falsifier's escalated case: several long Han runs must not
    each smuggle their full length through multiple passages."""
    _seed(tmp_path)
    chunk = "子丑寅卯辰巳午未申酉" * 800  # 8,000 Han chars
    body = f"{chunk}。分隔一。{chunk}。分隔二。{chunk}"
    _stub_documents(monkeypatch, body)
    _stub_quota(monkeypatch)

    result = _report(tmp_path, chunk)

    def string_total(node):
        if isinstance(node, str):
            return len(node)
        elif isinstance(node, dict):
            return sum(string_total(value) for value in node.values())
        elif isinstance(node, list):
            return sum(string_total(value) for value in node)
        return 0

    assert string_total(result) <= bmi.REPORT_BODY_MAX_CHARS
    assert result["evidence"]["status"] == "matched"


def test_brain_projection_never_exports_corpus_only_query_too_short_status():
    projected = bmi._project_evidence(
        {
            "status": "query_too_short",
            "passages": [],
            "source_binding": {},
        },
        report_id=REPORT_ID, published_at=PUBLISHED_AT,
        query="in", allowed=False,
    )

    assert projected["status"] == "body_unavailable"


def test_evidence_projection_rejects_invalid_binding_types_and_preserves_only_schema(
        ):
    projected = bmi._project_evidence(
        {
            "status": "no_matching_passage",
            "source_binding": {
                "content_sha256": "not-a-sha",
                "stored_body_sha256": "also-not-a-sha",
                "coverage": "complete-but-unproved",
                "source_char_count": True,
                "stored_char_count": 1.5,
                "tail_omitted": "yes",
                "page_count": True,
            },
        },
        report_id=REPORT_ID, published_at=PUBLISHED_AT, query="query", allowed=False,
    )

    assert projected["source_binding"] == {
        "report_id": REPORT_ID,
        "published_at": PUBLISHED_AT,
        "content_sha256": "",
        "stored_body_sha256": "",
        "coverage": "unknown",
        "source_char_count": None,
        "stored_char_count": None,
        "tail_omitted": None,
        "text_layer": "",
        "page_count": None,
    }

    invalid_tail = bmi._project_evidence(
        {
            "status": "no_matching_passage",
            "source_binding": {
                "coverage": "complete",
                "source_char_count": 10,
                "stored_char_count": 10,
                "tail_omitted": "no",
            },
        },
        report_id=REPORT_ID, published_at=PUBLISHED_AT, query="query", allowed=False,
    )
    assert invalid_tail["source_binding"]["coverage"] == "unknown"
    assert invalid_tail["source_binding"]["source_char_count"] is None
    assert invalid_tail["source_binding"]["tail_omitted"] is None


def test_evidence_passage_projection_rejects_malformed_locators():
    """R5 requirement 6: strict nonnegative-int validation, coherent span
    ordering, and no Python-repr leak of a non-string text field — the whole
    passage is omitted (fail closed), never a raised exception or a coerced
    guess."""
    good_raw = {
        "text": "some text", "match_text": "text",
        "matched_terms": ["text"],
        "locator": {
            "kind": "text_span", "start_char": 0, "end_char": 9,
            "match_start_char": 5, "match_end_char": 9,
        },
    }
    assert bmi._project_evidence_passage(good_raw, REPORT_ID) is not None

    malformed_locators = (
        {"start_char": "abc", "end_char": 9, "match_start_char": 5, "match_end_char": 9},
        {"start_char": "0", "end_char": "9", "match_start_char": "5", "match_end_char": "9"},
        {"start_char": 0.0, "end_char": 9.0, "match_start_char": 5.0, "match_end_char": 9.0},
        {"start_char": -5, "end_char": 9, "match_start_char": 5, "match_end_char": 9},
        {"start_char": 0, "end_char": 9, "match_start_char": True, "match_end_char": 9},
        {"start_char": 0, "end_char": 9, "match_start_char": 5, "match_end_char": 3.9},
        {"start_char": 0, "end_char": 9, "match_start_char": 5, "match_end_char": 5},
        {"start_char": 5, "end_char": 9, "match_start_char": 0, "match_end_char": 3},
        {"start_char": 0, "end_char": 3, "match_start_char": 5, "match_end_char": 9},
    )
    for locator in malformed_locators:
        raw = {**good_raw, "locator": locator}
        assert bmi._project_evidence_passage(raw, REPORT_ID) is None, locator

    non_string_text = {**good_raw, "text": {"a": 1}}
    assert bmi._project_evidence_passage(non_string_text, REPORT_ID) is None

    non_string_match_text = {**good_raw, "match_text": [1, 2, 3]}
    assert bmi._project_evidence_passage(non_string_match_text, REPORT_ID) is None

    unsupported_kind = {**good_raw, "locator": {**good_raw["locator"], "kind": "score"}}
    projected = bmi._project_evidence_passage(unsupported_kind, REPORT_ID)
    assert projected["locator"]["kind"] == "text_span"


def test_evidence_passage_projection_bounds_text_defensively():
    """Defense in depth: even if the corpus owner's own window cap were
    bypassed, the projector still bounds text/match_text independently."""
    huge = "x" * 50_000
    raw = {
        "text": huge, "match_text": huge, "matched_terms": [],
        "locator": {
            "kind": "text_span", "start_char": 0, "end_char": len(huge),
            "match_start_char": 0, "match_end_char": len(huge),
        },
    }
    projected = bmi._project_evidence_passage(raw, REPORT_ID)
    assert len(projected["text"]) < len(huge)
    assert len(projected["match_text"]) < len(huge)
    locator = projected["locator"]
    assert len(projected["text"]) == locator["end_char"] - locator["start_char"]
    relative_start = locator["match_start_char"] - locator["start_char"]
    relative_end = locator["match_end_char"] - locator["start_char"]
    assert projected["match_text"] == projected["text"][relative_start:relative_end]


def test_evidence_passage_projection_clips_around_a_late_match_coherently():
    text = ("x" * 25_000) + "AAPL demand" + ("y" * 25_000)
    match_start = text.index("AAPL demand")
    raw = {
        "text": text,
        "match_text": "AAPL demand",
        "matched_terms": ["aapl", "demand"],
        "locator": {
            "kind": "text_span",
            "start_char": 10_000,
            "end_char": 10_000 + len(text),
            "match_start_char": 10_000 + match_start,
            "match_end_char": 10_000 + match_start + len("AAPL demand"),
        },
    }

    projected = bmi._project_evidence_passage(raw, REPORT_ID)

    assert projected is not None
    assert len(projected["text"]) <= bmi._EVIDENCE_PASSAGE_TEXT_MAX_CHARS
    assert "AAPL demand" in projected["text"]
    locator = projected["locator"]
    assert len(projected["text"]) == locator["end_char"] - locator["start_char"]
    relative_start = locator["match_start_char"] - locator["start_char"]
    relative_end = locator["match_end_char"] - locator["start_char"]
    assert projected["match_text"] == "AAPL demand"
    assert projected["match_text"] == projected["text"][relative_start:relative_end]


def test_evidence_open_url_is_rights_safe_with_bounded_fragment_query():
    """R5 requirement 3: doc is the only query param; page/q live only in an
    optional fragment; no publisher/match text ever enters the URL, and there
    is no `find=` parameter at all."""
    bare = bmi._evidence_open_url(REPORT_ID)
    assert bare == f"https://mastermind-x.com/research_vault.html?doc={REPORT_ID}"

    with_page = bmi._evidence_open_url(REPORT_ID, page=2)
    assert with_page == (
        f"https://mastermind-x.com/research_vault.html?doc={REPORT_ID}#page=2"
    )

    with_q = bmi._evidence_open_url(REPORT_ID, page=2, q="AAPL demand")
    assert with_q.startswith(
        f"https://mastermind-x.com/research_vault.html?doc={REPORT_ID}#page=2&q="
    )
    assert "AAPL demand" not in with_q  # bounded/encoded, not raw
    assert "find" not in with_q

    # Invalid/nonpositive page is omitted, not clamped or coerced.
    assert bmi._evidence_open_url(REPORT_ID, page=0) == bare
    assert bmi._evidence_open_url(REPORT_ID, page=-3) == bare
    assert bmi._evidence_open_url(REPORT_ID, page="abc") == bare

    # Blank/whitespace-only q is omitted (a generic call has no user question).
    assert bmi._evidence_open_url(REPORT_ID, q="   ") == bare
    assert bmi._evidence_open_url(REPORT_ID, q="") == bare

    # There is no way to pass publisher/match text into this function at all.
    import inspect
    params = set(inspect.signature(bmi._evidence_open_url).parameters)
    assert "match_text" not in params
    assert "find" not in params


def test_evidence_link_query_is_nfkc_normalized_and_bounded():
    assert bmi._evidence_link_query("ＡＡＰＬ demand") == "AAPL demand"
    assert bmi._evidence_link_query("") == ""
    assert bmi._evidence_link_query("   ") == ""
    assert bmi._evidence_link_query(None) == ""
    long_query = "topic " * 200
    bounded = bmi._evidence_link_query(long_query)
    assert len(bounded) <= bmi._EVIDENCE_QUERY_MAX_CHARS


def test_tool_schema_tells_the_model_to_request_and_open_supporting_evidence():
    schema = bmi.RESEARCH_TOOL_SCHEMA
    description = schema["description"].lower()
    query_help = schema["input_schema"]["properties"]["query"]["description"].lower()
    mode_help = schema["input_schema"]["properties"]["mode"]["description"].lower()

    assert "supporting passage" in description
    assert "open source" in description
    assert "summarize this report" in query_help
    assert "what does this note argue" in query_help
    assert "empty query" in query_help
    assert "exact question" in query_help
    assert "report" in query_help and "ignored" not in query_help
    assert "query-centered" in mode_help
    # R5 requirement 5: Chinese factual retrieval is honestly scoped to literal
    # key terms/phrases, not an unsegmented sentence the selector cannot parse.
    assert "chinese" in query_help
    assert "key term" in query_help or "key phrase" in query_help



def test_sha_projection_accepts_only_canonical_lowercase_hex():
    assert bmi._sha256_or_empty("a" * 64) == "a" * 64
    for malformed in ("A" * 64, " " + ("a" * 64), ("a" * 64) + " "):
        assert bmi._sha256_or_empty(malformed) == ""


def test_malformed_projected_passage_is_unmetered_end_to_end(tmp_path, monkeypatch):
    """The raw selector is not debit authority: projection must validate the
    final passage first, and a fail-closed projection must consume zero quota."""
    _seed(tmp_path)
    _stub_documents(monkeypatch, "AAPL demand is accelerating.")
    debits = _stub_quota(monkeypatch)
    monkeypatch.setattr(bmi, "_select_evidence", lambda document, query: {
        "status": "matched",
        "passages": [{
            "text": "AAPL demand",
            "match_text": "AAPL demand",
            "matched_terms": ["aapl", "demand"],
            "locator": {
                "kind": "text_span",
                "start_char": "0",
                "end_char": "11",
                "match_start_char": "0",
                "match_end_char": "11",
            },
        }],
        "source_binding": {
            "content_sha256": PDF_SHA,
            "stored_body_sha256": "b" * 64,
            "coverage": "complete",
            "stored_char_count": 28,
            "source_char_count": 28,
            "tail_omitted": False,
            "text_layer": "full",
            "page_count": 1,
        },
    })

    result = _report(tmp_path, "AAPL demand")

    assert debits == []
    assert result["quota"] is None
    assert result["report"]["body_text"] == ""
    assert result["evidence"]["status"] == "body_unavailable"
    assert result["evidence"]["passages"] == []
    assert result["evidence"]["access"] == {
        "decision": "not_served", "metered": False,
    }
    assert "no usable passage text was available" in result["note"].lower()


def test_large_public_excerpt_is_budgeted_before_evidence_debit(tmp_path, monkeypatch):
    """Every string in the final report envelope—not only body_text—shares the
    12k context ceiling. A giant public excerpt is trimmed before a paid evidence
    view is committed, while the valid source-bound passage remains usable."""
    _seed(tmp_path)
    excerpts = tmp_path / "data" / "research_vault" / "excerpts.json"
    excerpts.write_text(json.dumps({
        "schema": 1,
        "excerpts": {REPORT_ID: ["P" * 20_000]},
    }), encoding="utf-8")
    _stub_documents(monkeypatch, "AAPL demand is accelerating after channel checks.")
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "AAPL demand")

    def string_total(node):
        if isinstance(node, str):
            return len(node)
        if isinstance(node, dict):
            return sum(string_total(value) for value in node.values())
        if isinstance(node, list):
            return sum(string_total(value) for value in node)
        return 0

    assert string_total(result) <= bmi.REPORT_BODY_MAX_CHARS
    assert len(debits) == 1
    assert result["quota"] == {"remaining": 11, "limit": 12}
    assert result["evidence"]["status"] == "matched"
    assert result["evidence"]["passages"]
    assert "AAPL demand" in result["report"]["body_text"]
    assert sum(map(len, result["report"]["excerpt_paragraphs"])) < 20_000



def _recursive_string_total(node) -> int:
    if isinstance(node, str):
        return len(node)
    if isinstance(node, dict):
        return sum(_recursive_string_total(value) for value in node.values())
    if isinstance(node, list):
        return sum(_recursive_string_total(value) for value in node)
    return 0


def test_distinct_multi_atom_cjk_envelope_is_budgeted_before_one_debit(
        tmp_path, monkeypatch):
    """R6 discriminator for the passages × text × terms budget dimension."""
    _seed(tmp_path)
    atoms = [char * 160 for char in "甲乙丙丁戊己庚辛壬癸子丑"]
    phrase = " ".join(atoms)
    separator = "。" + ("背景材料" * 350) + "。"
    body = separator.join((phrase, phrase, phrase))
    _stub_documents(monkeypatch, body)
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, phrase)

    assert result["evidence"]["status"] == "matched"
    assert 1 <= len(result["evidence"]["passages"]) <= 3
    assert _recursive_string_total(result) <= bmi.REPORT_BODY_MAX_CHARS
    assert len(debits) == 1


def test_unmetered_no_match_still_obeys_whole_response_budget(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    excerpts = tmp_path / "data" / "research_vault" / "excerpts.json"
    excerpts.write_text(json.dumps({
        "schema": 1,
        "excerpts": {REPORT_ID: ["PUBLIC" * 4_000]},
    }), encoding="utf-8")
    _stub_documents(monkeypatch, "AAPL demand is accelerating.")
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "semiconductor inventories")

    assert result["evidence"]["status"] == "no_matching_passage"
    assert result["evidence"]["passages"] == []
    assert result["report"]["body_text"] == ""
    assert debits == []
    assert _recursive_string_total(result) <= bmi.REPORT_BODY_MAX_CHARS


def test_oversized_selector_text_is_projected_before_body_and_debit(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    _stub_documents(monkeypatch, "AAPL demand is accelerating.")
    debits = _stub_quota(monkeypatch)
    source = ("x" * 7_000) + "AAPL demand" + ("y" * 7_000)
    match_start = source.index("AAPL demand")
    monkeypatch.setattr(bmi, "_select_evidence", lambda document, query: {
        "status": "matched",
        "passages": [{
            "text": source,
            "match_text": "AAPL demand",
            "matched_terms": ["aapl", "demand"],
            "locator": {
                "kind": "text_span",
                "start_char": 0,
                "end_char": len(source),
                "match_start_char": match_start,
                "match_end_char": match_start + len("AAPL demand"),
            },
        }],
        "source_binding": {
            "content_sha256": PDF_SHA,
            "stored_body_sha256": "b" * 64,
            "coverage": "complete",
            "stored_char_count": len(source),
            "source_char_count": len(source),
            "tail_omitted": False,
            "text_layer": "full",
            "page_count": 1,
        },
    })

    result = _report(tmp_path, "AAPL demand")

    passage = result["evidence"]["passages"][0]
    locator = passage["locator"]
    relative_start = locator["match_start_char"] - locator["start_char"]
    relative_end = locator["match_end_char"] - locator["start_char"]
    assert result["evidence"]["status"] == "matched"
    assert len(passage["text"]) <= bmi._EVIDENCE_PASSAGE_TEXT_MAX_CHARS
    assert passage["match_text"] == passage["text"][relative_start:relative_end]
    assert len(result["report"]["body_text"]) <= bmi._EVIDENCE_PASSAGE_TEXT_MAX_CHARS
    assert _recursive_string_total(result) <= bmi.REPORT_BODY_MAX_CHARS
    assert len(debits) == 1



def test_nonmatched_overflow_never_promotes_unmetered_passage_into_body(
        tmp_path, monkeypatch):
    """Budget fitting must not turn a corrupted non-match envelope into a free
    publisher-text response merely because projected passages are present."""
    _seed(tmp_path)
    _stub_documents(monkeypatch, "AAPL demand is accelerating.")
    debits = _stub_quota(monkeypatch)

    passages = []
    for index in range(3):
        token = f"SECRET{index:02d} "
        text = (token * 200)[:bmi._EVIDENCE_PASSAGE_TEXT_MAX_CHARS]
        start = index * len(text)
        passages.append({
            "text": text,
            "match_text": text,
            "matched_terms": [chr(65 + term) * 120 for term in range(12)],
            "locator": {
                "kind": "text_span",
                "start_char": start,
                "end_char": start + len(text),
                "match_start_char": start,
                "match_end_char": start + len(text),
            },
        })

    for selector_status in ("no_matching_passage", "body_unavailable"):
        monkeypatch.setattr(bmi, "_select_evidence", lambda document, query,
                            status=selector_status: {
            "status": status,
            "passages": passages,
            "source_binding": {
                "content_sha256": PDF_SHA,
                "stored_body_sha256": "b" * 64,
                "coverage": "complete",
                "stored_char_count": sum(len(p["text"]) for p in passages),
                "source_char_count": sum(len(p["text"]) for p in passages),
                "tail_omitted": False,
                "text_layer": "full",
                "page_count": 1,
            },
        })

        result = _report(tmp_path, "AAPL demand")

        assert result["evidence"]["status"] == selector_status
        assert result["evidence"]["access"] == {
            "decision": "not_served", "metered": False,
        }
        assert result["evidence"]["passages"] == []
        assert result["quota"] is None
        assert result["report"]["body_text"] == ""
        assert result["report"]["body_truncated"] is False
        assert "SECRET" not in json.dumps(result)
        assert _recursive_string_total(result) <= bmi.REPORT_BODY_MAX_CHARS

    assert debits == []


def test_malformed_passage_containers_fail_closed_without_exception_or_debit(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    _stub_documents(monkeypatch, "AAPL demand is accelerating.")
    debits = _stub_quota(monkeypatch)
    valid_passage = {
        "text": "AAPL demand",
        "match_text": "AAPL demand",
        "matched_terms": ["aapl", "demand"],
        "locator": {
            "kind": "text_span",
            "start_char": 0,
            "end_char": 11,
            "match_start_char": 0,
            "match_end_char": 11,
        },
    }
    binding = {
        "content_sha256": PDF_SHA,
        "stored_body_sha256": "b" * 64,
        "coverage": "complete",
        "stored_char_count": 28,
        "source_char_count": 28,
        "tail_omitted": False,
        "text_layer": "full",
        "page_count": 1,
    }

    for malformed in (123, object(), "not-a-list", {"passage": valid_passage},
                      (valid_passage,)):
        monkeypatch.setattr(bmi, "_select_evidence", lambda document, query,
                            value=malformed: {
            "status": "matched",
            "passages": value,
            "source_binding": binding,
        })

        result = _report(tmp_path, "AAPL demand")

        assert result["evidence"]["status"] == "body_unavailable", type(malformed)
        assert result["evidence"]["passages"] == [], type(malformed)
        assert result["report"]["body_text"] == "", type(malformed)
        assert result["report"]["body_truncated"] is False, type(malformed)
        assert result["quota"] is None, type(malformed)

    assert debits == []


def test_page_locator_and_binding_accept_only_literal_positive_ints():
    raw = {
        "text": "some text",
        "match_text": "text",
        "matched_terms": ["text"],
        "locator": {
            "kind": "page_text_span",
            "page": 2,
            "start_char": 0,
            "end_char": 9,
            "match_start_char": 5,
            "match_end_char": 9,
        },
    }
    projected = bmi._project_evidence_passage(raw, REPORT_ID)
    assert projected is not None
    assert projected["locator"]["page"] == 2

    for malformed in ("2", " 2 ", 2.0, True, False, 0, -1, 1.5, None):
        candidate = {
            **raw,
            "locator": {**raw["locator"], "page": malformed},
        }
        assert bmi._project_evidence_passage(candidate, REPORT_ID) is None, malformed

        envelope = bmi._project_evidence({
            "status": "no_matching_passage",
            "passages": [],
            "source_binding": {"page_count": malformed},
        }, report_id=REPORT_ID, published_at=PUBLISHED_AT,
            query="query", allowed=False)
        assert envelope["source_binding"]["page_count"] is None, malformed


def test_error_envelope_bounds_caller_report_id_under_shared_ceiling(tmp_path):
    _seed(tmp_path)
    caller_id = "x" * 50_000

    result = bmi.search_research(
        tmp_path, "AAPL demand", mode="report", report_id=caller_id,
        user_ctx=PRO, now=NOW,
    )

    assert result["error"] == "report_not_found"
    assert result["report_id"] != caller_id
    assert len(result["report_id"]) <= bmi._REPORT_META_MAX_CHARS
    assert _recursive_string_total(result) <= bmi.REPORT_BODY_MAX_CHARS


def test_limit_error_sanitizes_string_quota_metadata(tmp_path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.setattr(bmi, "_peek_report_view", lambda user_id, now: {
        "remaining": 0,
        "limit": "L" * 50_000,
    })

    result = _report(tmp_path, "AAPL demand")

    assert result["error"] == "view_limit_reached"
    assert result["remaining"] == 0
    assert result["limit"] is None
    assert _recursive_string_total(result) <= bmi.REPORT_BODY_MAX_CHARS
