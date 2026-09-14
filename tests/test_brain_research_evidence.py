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
    assert passage["open_url"] == evidence["open_url"]
    parsed = urlparse(evidence["open_url"])
    assert parsed.scheme == "https" and parsed.netloc == "mastermind-x.com"
    assert parsed.path == "/research_vault.html"
    params = parse_qs(parsed.query)
    assert params == {
        "doc": [REPORT_ID], "find": ["AAPL demand"], "page": ["2"]
    }
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
    """Passage mode cannot hide an over-cap text field outside body_text."""
    _seed(tmp_path)
    _stub_documents(monkeypatch, "AAPL demand " + ("supporting context " * 5000))
    _stub_quota(monkeypatch)

    result = _report(tmp_path, "AAPL demand " + ("unmatched-term " * 5000))

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
