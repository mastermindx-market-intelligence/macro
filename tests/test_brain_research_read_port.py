"""Brain research reads converge on the Research Read port (F11).

Fake port only. No network, no store, no PDF extractor.
"""
from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.neuralweb import brain_market_intel as bmi

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
PRO = {"user_id": "u-pro-f11"}
REPORT_ID = "desk-note-1"
PUBLISHED_AT = "2026-10-06T12:00:00Z"
PDF_SHA = "a" * 64
TEXT_SHA = "b" * 64
# Q-F11-9. Neighbouring research notes are English-only, so this sentence is too.
STALE_SENTENCE = (
    " The research library has not refreshed on schedule; reports newer than "
    "its last refresh may be missing."
)
# GAP: Brain has no path that emits a rights-safe RIO summary. This suite pins
# that none is dressed up as evidence. Do not build one here.
RIO_QUOTE = "RIO_SECRET_QUOTE_NEVER_LEAK"

_SEAM_NAMES = (
    "_load_corpus_document",
    "_load_evidence_document",
    "_select_evidence",
    "_evidence_requested",
)
_CORPUS_READS = frozenset({
    "get_document",
    "get_evidence_document",
    "find_evidence_passages",
    "corpus_connection",
    "sha_index",
    "search",
})
_FORBIDDEN_ARGUMENT_KEYS = frozenset({
    "tier", "user", "user_id", "user_ctx", "entitlement", "principal",
    "principal_id",
})


def _seed(root: Path) -> None:
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


def _source(*, state="SOURCE_FRESH", degradation=()):
    return {"state": state, "known_degradation": list(degradation)}


def _passage(
    text: str,
    match_text: str,
    *,
    terms=None,
    page_start=None,
    page_end=None,
    start_char=0,
    with_match=True,
):
    match_at = text.find(match_text)
    row = {
        "schema": "research.evidence_passage.v1",
        "report_id": REPORT_ID,
        "title": "Apple Demand Monitor",
        "institution": "Example Bank",
        "published_at": PUBLISHED_AT,
        "source_pdf_sha256": PDF_SHA,
        "extracted_text_sha256": TEXT_SHA,
        "text": text,
        "page_start": page_start,
        "page_end": page_end,
        "start_byte": 0,
        "end_byte": len(text.encode("utf-8")),
        "coverage_state": "FULL_TEXT",
        "replay_state": "EXACT",
    }
    if with_match:
        row.update({
            "start_char": start_char,
            "end_char": start_char + len(text),
            "match_start_char": start_char + match_at,
            "match_end_char": start_char + match_at + len(match_text),
            "match_text": match_text,
            "matched_terms": list(terms if terms is not None else ["aapl", "demand"]),
        })
    return row


def _evidence_result(
    *,
    evidence_state,
    coverage_state,
    passages=(),
    source=None,
    scope=None,
):
    result = {
        "schema": "research_vault.evidence_result.v1",
        "ok": True,
        "report_id": REPORT_ID,
        "evidence_state": evidence_state,
        "coverage_state": coverage_state,
        "source": source if source is not None else _source(),
        "rio_state": "NOT_REQUESTED",
        "rio_summary": RIO_QUOTE,
        "passages": list(passages),
    }
    if scope is not None:
        result.update(scope)
    return result


class RecordingAdapter:
    """In-process stand-in for BrainResearchAdapter. Records every call."""

    def __init__(self, *, segments=None, coverage="FULL_TEXT", text_layer="full",
                 find_result=None, source=None, error=None, report=None):
        self.segments = list(segments or [])
        self.coverage = coverage
        self.text_layer = text_layer
        self.find_result = find_result
        self.source = source if source is not None else _source()
        self.error = error
        self.report = report if report is not None else {
            "title": "Corpus Title",
            "institution": "Corpus Co",
            "side": "sell",
            "published_at": "2026-01-01T00:00:00Z",
        }
        self.calls: list[dict] = []

    def call(self, tool, arguments, *, server_context):
        self.calls.append({
            "tool": tool,
            "arguments": dict(arguments) if isinstance(arguments, dict) else arguments,
            "server_context": server_context,
        })
        if self.error is not None:
            raise self.error
        if tool == "research_fetch":
            return self._fetch(arguments)
        if tool == "research_find_evidence":
            return {
                "schema": "brain.research_port.v1",
                "tool": tool,
                "result": self.find_result,
            }
        raise AssertionError(tool)

    def _fetch(self, arguments):
        selectors = arguments.get("selectors") or {}
        start = selectors.get("segment_start", 0)
        count = selectors.get("max_segments", 4)
        window = self.segments[start:start + count]
        return {
            "schema": "brain.research_port.v1",
            "tool": "research_fetch",
            "result": {
                "schema": "research_vault.fetch_result.v1",
                "ok": True,
                "available": True,
                "report_id": arguments.get("report_id"),
                "report": self.report,
                "source": self.source,
                "coverage_state": self.coverage,
                "text_layer_state": self.text_layer,
                "segment_count_total": len(self.segments),
                "segments": window,
            },
        }

    def tools(self):
        return [call["tool"] for call in self.calls]


def _segment(text: str, start: int) -> dict:
    raw = text.encode("utf-8")
    return {
        "segment_index": 0,
        "page_start": None,
        "page_end": None,
        "start_byte": start,
        "end_byte": start + len(raw),
        "text": text,
    }


def _segments_from_pages(pages: list[str]) -> list[dict]:
    out = []
    cursor = 0
    for text in pages:
        out.append(_segment(text, cursor))
        cursor += len(text.encode("utf-8"))
    return out


@pytest.fixture(autouse=True)
def _no_remote_store(monkeypatch, tmp_path):
    """Keep a base-tree corpus fallback, and every new test, off the network."""
    monkeypatch.setenv("RESEARCH_LOCAL_STORE", str(tmp_path / "no-store"))
    for name in (
        "R2_RESEARCH_BUCKET",
        "R2_RESEARCH_ENDPOINT",
        "R2_RESEARCH_ACCESS_KEY_ID",
        "R2_RESEARCH_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def _install(monkeypatch, adapter: RecordingAdapter) -> RecordingAdapter:
    monkeypatch.setattr(bmi, "_brain_research_adapter", lambda: adapter, raising=False)
    return adapter


def _stub_quota(monkeypatch, *, allowed=True):
    from engine.research_vault import view_ratelimit

    calls: list[tuple] = []

    def allow(user_id, ip, root=None, now=None):
        calls.append((user_id, ip, now))
        return allowed, {"remaining": 11 if allowed else 0, "limit": 12}

    monkeypatch.setattr(view_ratelimit, "allow", allow)
    return calls


def _report(root, query="", *, user_ctx=PRO, report_id=REPORT_ID):
    return bmi.search_research(
        root, query, mode="report", report_id=report_id,
        user_ctx=user_ctx, now=NOW,
    )


def _scope(**over):
    block = {
        "searched_char_count": 40,
        "text_layer_state": "full",
        "page_count": 2,
    }
    block.update(over)
    return block


def test_specific_evidence_is_the_literal_port_passage(tmp_path, monkeypatch):
    """(b) Ground a specific question in the literal port passage. Fails on the base tree."""
    _seed(tmp_path)
    text = "The desk raised AAPL demand estimates after channel checks."
    match = "AAPL demand"
    bare = "synthesized-from-missing-match-fields " + ("x" * 40)
    adapter = _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
        evidence_state="FOUND",
        coverage_state="FULL_TEXT",
        passages=[
            _passage(text, match),
            _passage(bare, bare[:8], with_match=False),
        ],
        scope=_scope(searched_char_count=len(text)),
    )))
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "AAPL demand")

    assert adapter.calls, "research_find_evidence was not called"
    assert adapter.tools() == ["research_find_evidence"]
    evidence = result["evidence"]
    assert evidence["schema"] == "brain.research_evidence.v1"
    assert evidence["status"] == "matched"
    assert len(evidence["passages"]) == 1
    projected = evidence["passages"][0]
    assert projected["text"] == text
    assert projected["match_text"] == match
    assert "synthesized-from-missing-match-fields" not in projected["text"]
    assert len(debits) == 1
    for call in adapter.calls:
        assert _FORBIDDEN_ARGUMENT_KEYS.isdisjoint(call["arguments"])
        ctx = call["server_context"]
        assert ctx.principal_id == PRO["user_id"]
        assert ctx.entitlement == "pro"
        assert ctx.surface == "brain"
        assert "fetch" in ctx.scopes and "find_evidence" in ctx.scopes


def test_long_port_passage_is_clipped_at_1200_and_keeps_match_text(tmp_path, monkeypatch):
    _seed(tmp_path)
    match = "AAPL demand"
    text = ("alpha " * 200) + match + (" omega" * 200)
    assert len(text) > 1200
    _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
        evidence_state="FOUND",
        coverage_state="FULL_TEXT",
        passages=[_passage(text, match)],
        scope=_scope(searched_char_count=len(text)),
    )))
    _stub_quota(monkeypatch)

    result = _report(tmp_path, "AAPL demand")
    projected = result["evidence"]["passages"][0]
    assert len(projected["text"]) <= 1200
    assert projected["match_text"] == match
    assert match in projected["text"]


def test_no_evidence_stays_no_evidence(tmp_path, monkeypatch):
    """(c) NOT_FOUND is not dressed with a summary."""
    _seed(tmp_path)
    _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
        evidence_state="NOT_FOUND",
        coverage_state="FULL_TEXT",
        passages=[],
        scope=_scope(),
    )))
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "semiconductor inventories")

    assert result["evidence"]["status"] == "no_matching_passage"
    assert result["evidence"]["passages"] == []
    assert result["report"]["body_text"] == ""
    assert debits == []
    assert result["quota"] is None
    blob = json.dumps(result)
    assert RIO_QUOTE not in blob
    assert bmi._REPORT_NO_EVIDENCE in result["note"]
    assert "Coverage could not be verified" not in result["note"]


def test_no_rio_summary_is_ever_emitted_as_evidence(tmp_path, monkeypatch):
    """GAP: no Brain path on this tree emits a rights-safe RIO summary."""
    _seed(tmp_path)
    pages = _segments_from_pages(["The complete stored argument."])
    _install(monkeypatch, RecordingAdapter(
        segments=pages,
        find_result=_evidence_result(
            evidence_state="NOT_FOUND",
            coverage_state="FULL_TEXT",
            scope=_scope(),
        ),
    ))
    _stub_quota(monkeypatch)

    generic = _report(tmp_path, "Summarize this report.")
    assert generic["evidence"] is None
    assert RIO_QUOTE not in json.dumps(generic)

    specific = _report(tmp_path, "semiconductor inventories")
    assert specific["evidence"]["passages"] == []
    assert RIO_QUOTE not in json.dumps(specific)


def _seam_function(tree: ast.AST, name: str) -> ast.AST:
    for node in tree.body:  # type: ignore[attr-defined]
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing seam {name}")


def _forbidden_in(fn: ast.AST) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Attribute) and (
            node.attr in _CORPUS_READS or node.attr == "r2_store"
        ):
            hits.append(node.attr)
        elif isinstance(node, ast.Name) and (
            node.id in _CORPUS_READS or node.id == "r2_store"
        ):
            hits.append(node.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in _CORPUS_READS or "r2_store" in node.value:
                hits.append(node.value)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", None) or ""
            names = [module, *[alias.name for alias in node.names]]
            for name in names:
                if name in _CORPUS_READS or "r2_store" in name:
                    hits.append(name)
    return hits


def test_seams_do_not_read_corpus_or_r2():
    """AST denylist over the four seams. Fails on the base tree."""
    source = Path(bmi.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders: dict[str, list[str]] = {}
    for name in _SEAM_NAMES:
        hits = _forbidden_in(_seam_function(tree, name))
        if hits:
            offenders[name] = hits
    assert not offenders, offenders


def test_missing_user_makes_zero_port_calls(tmp_path, monkeypatch):
    _seed(tmp_path)
    adapter = _install(monkeypatch, RecordingAdapter(
        segments=_segments_from_pages(["secret body"]),
    ))
    debits = _stub_quota(monkeypatch)

    for ctx in (None, {}, {"user_id": ""}, {"user_id": "   "}, {"ip_hint": "1.2.3.4"}):
        result = _report(tmp_path, "AAPL demand", user_ctx=ctx)
        assert result["error"] == "pro_required", ctx
        assert result["schema"] == "brain.research_report.v1"

    assert adapter.calls == []
    assert debits == []


def test_port_exception_is_excerpt_only_and_uncharged(tmp_path, monkeypatch):
    _seed(tmp_path)
    _install(monkeypatch, RecordingAdapter(error=RuntimeError("port down")))
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "")

    assert result["schema"] == "brain.research_report.v1"
    assert result["report"]["body_text"] == ""
    assert result["quota"] is None
    assert debits == []
    assert result["note"].endswith(bmi._REPORT_EXCERPT_ONLY)
    assert "scanned/image-only" not in result["note"]


def test_evidence_port_exception_is_excerpt_only_and_uncharged(tmp_path, monkeypatch):
    _seed(tmp_path)
    _install(monkeypatch, RecordingAdapter(error=RuntimeError("port down")))
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "AAPL demand")

    assert result["evidence"]["status"] == "body_unavailable"
    assert result["report"]["body_text"] == ""
    assert result["quota"] is None
    assert debits == []
    assert result["note"].endswith(bmi._REPORT_EXCERPT_ONLY)


def test_ledger_debits_only_text_that_is_served(tmp_path, monkeypatch):
    _seed(tmp_path)
    generic = _install(monkeypatch, RecordingAdapter(
        segments=_segments_from_pages(["The complete stored argument."]),
    ))
    debits = _stub_quota(monkeypatch)
    served = _report(tmp_path, "Summarize this report.")
    assert served["report"]["body_text"] == "The complete stored argument."
    assert served["evidence"] is None
    assert len(debits) == 1
    assert generic.tools() == ["research_fetch"]

    empty = RecordingAdapter(
        segments=[],
        coverage="FULL_TEXT",
        text_layer="full",
    )
    _install(monkeypatch, empty)
    before = len(debits)
    blank = _report(tmp_path, "Summarize this report.")
    assert blank["report"]["body_text"] == ""
    assert len(debits) == before

    unavailable = RecordingAdapter(find_result=_evidence_result(
        evidence_state="UNAVAILABLE",
        coverage_state="EXTRACTION_UNAVAILABLE",
    ))
    _install(monkeypatch, unavailable)
    before = len(debits)
    failed = _report(tmp_path, "AAPL demand")
    assert failed["evidence"]["status"] == "body_unavailable"
    assert failed["note"].endswith(bmi._REPORT_EXCERPT_ONLY)
    assert len(debits) == before

    missing = RecordingAdapter(find_result=_evidence_result(
        evidence_state="NOT_FOUND",
        coverage_state="FULL_TEXT",
        scope=_scope(),
    ))
    _install(monkeypatch, missing)
    before = len(debits)
    quiet = _report(tmp_path, "semiconductor inventories")
    assert quiet["evidence"]["status"] == "no_matching_passage"
    assert len(debits) == before


def test_body_over_the_cap_is_sliced_like_slice_report_body(tmp_path, monkeypatch):
    _seed(tmp_path)
    page = "lorem ipsum dolor " * 400  # well over the per-page budget once joined
    segments = _segments_from_pages([page, page, page])
    prefix = page + page + page
    assert len(prefix) > bmi.REPORT_BODY_MAX_CHARS
    _install(monkeypatch, RecordingAdapter(segments=segments))
    _stub_quota(monkeypatch)

    result = _report(tmp_path, "")
    expected, truncated = bmi._slice_report_body(prefix)
    assert truncated is True
    assert result["report"]["body_truncated"] is True
    assert result["report"]["body_text"] == expected
    assert len(result["report"]["body_text"]) <= bmi.REPORT_BODY_MAX_CHARS


def test_paging_stops_at_exhaustion_within_the_hard_call_cap(tmp_path, monkeypatch):
    _seed(tmp_path)
    pages = [f"segment-{index:02d} " * 5 for index in range(10)]
    segments = _segments_from_pages(pages)
    adapter = _install(monkeypatch, RecordingAdapter(segments=segments))
    _stub_quota(monkeypatch)

    result = _report(tmp_path, "Summarize this report.")

    assert result["report"]["body_text"] == "".join(pages)
    assert result["report"]["body_truncated"] is False
    assert adapter.tools() == ["research_fetch"] * len(adapter.calls)
    assert 1 <= len(adapter.calls) <= 8
    starts = [call["arguments"]["selectors"]["segment_start"] for call in adapter.calls]
    assert starts == list(range(0, len(segments), 4))[:len(starts)]


def test_paging_stops_when_a_page_returns_zero_segments(tmp_path, monkeypatch):
    _seed(tmp_path)
    adapter = _install(monkeypatch, RecordingAdapter(segments=[]))
    adapter.segments_total_lie = 10  # type: ignore[attr-defined]

    def _fetch(arguments):
        return {
            "schema": "brain.research_port.v1",
            "tool": "research_fetch",
            "result": {
                "ok": True,
                "report": {"title": "T", "institution": "I", "side": "sell",
                           "published_at": PUBLISHED_AT},
                "source": _source(),
                "coverage_state": "FULL_TEXT",
                "text_layer_state": "full",
                "segment_count_total": 10,
                "segments": [],
            },
        }

    adapter._fetch = _fetch  # type: ignore[method-assign]
    _stub_quota(monkeypatch)

    result = _report(tmp_path, "")
    assert result["report"]["body_text"] == ""
    assert len(adapter.calls) == 1


def test_paging_stops_on_a_noncontiguous_segment(tmp_path, monkeypatch):
    _seed(tmp_path)
    first = _segment("kept prefix ", 0)
    gap = _segment("dropped", first["end_byte"] + 25)
    _install(monkeypatch, RecordingAdapter(segments=[first, gap]))
    _stub_quota(monkeypatch)

    result = _report(tmp_path, "")
    assert result["report"]["body_text"] == "kept prefix "
    assert "dropped" not in result["report"]["body_text"]


def test_form_feed_window_page_matches_the_legacy_corpus_page(tmp_path, monkeypatch):
    """Q-F11-6b: a window that crosses a form feed before the match."""
    from engine.research_vault import corpus

    _seed(tmp_path)
    body = "page one stays visible\fMATCHED_TERM sits on the next page"
    match = "MATCHED_TERM"
    legacy = corpus.find_evidence_passages(
        {
            "body": body,
            "char_count": len(body),
            "content_sha256": PDF_SHA,
            "text_layer": "full",
            "pages": 2,
        },
        match,
    )
    legacy_page = legacy["passages"][0]["locator"]["page"]
    assert legacy_page == body.count("\f", 0, body.index(match)) + 1
    _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
        evidence_state="FOUND",
        coverage_state="FULL_TEXT",
        passages=[_passage(body, match, page_start=1, page_end=2)],
        scope=_scope(searched_char_count=len(body), page_count=2),
    )))
    _stub_quota(monkeypatch)

    result = _report(tmp_path, match)
    locator = result["evidence"]["passages"][0]["locator"]
    assert locator["kind"] == "page_text_span"
    assert locator["page"] == legacy_page


def test_page_guard_uses_scope_page_count_and_drops_only_without_the_block(
        tmp_path, monkeypatch):
    _seed(tmp_path)
    body = "page one\fMATCHED_TERM on page two"
    match = "MATCHED_TERM"
    _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
        evidence_state="FOUND",
        coverage_state="FULL_TEXT",
        passages=[_passage(body, match, page_start=1, page_end=2)],
        scope=_scope(searched_char_count=len(body), page_count=1),
    )))
    _stub_quota(monkeypatch)
    guarded = _report(tmp_path, match)
    assert guarded["evidence"]["passages"][0]["locator"]["kind"] == "text_span"
    assert "page" not in guarded["evidence"]["passages"][0]["locator"]

    _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
        evidence_state="FOUND",
        coverage_state="FULL_TEXT",
        passages=[_passage(body, match, page_start=1, page_end=2)],
        scope=None,
    )))
    unguarded = _report(tmp_path, match)
    locator = unguarded["evidence"]["passages"][0]["locator"]
    assert locator["kind"] == "page_text_span"
    assert locator["page"] == 2


def test_hundred_char_atom_survives_brains_term_trim(tmp_path, monkeypatch):
    """Q-F11-6a: Brain's 120-char trim is the binding cap, so 100 chars survive."""
    _seed(tmp_path)
    term = "甲" * 100
    text = "前言" + term + "后语"
    _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
        evidence_state="FOUND",
        coverage_state="FULL_TEXT",
        passages=[_passage(text, term, terms=[term])],
        scope=_scope(searched_char_count=len(text)),
    )))
    _stub_quota(monkeypatch)

    result = _report(tmp_path, term)
    terms = result["evidence"]["passages"][0]["matched_terms"]
    assert terms == [term]
    assert len(terms[0]) == 100


def test_scope_block_maps_complete_and_fails_closed_to_unknown(tmp_path, monkeypatch):
    _seed(tmp_path)
    _stub_quota(monkeypatch)

    def note_for(result):
        _install(monkeypatch, RecordingAdapter(find_result=result))
        return _report(tmp_path, "semiconductor inventories")["note"]

    complete = note_for(_evidence_result(
        evidence_state="NOT_FOUND",
        coverage_state="FULL_TEXT",
        scope=_scope(),
    ))
    absent = note_for(_evidence_result(
        evidence_state="NOT_FOUND",
        coverage_state="FULL_TEXT",
        scope=None,
    ))
    partial = note_for(_evidence_result(
        evidence_state="NOT_FOUND",
        coverage_state="FULL_TEXT",
        source=_source(degradation=("FULL_TEXT_PARTIAL",)),
        scope=_scope(),
    ))
    broken = note_for(_evidence_result(
        evidence_state="NOT_FOUND",
        coverage_state="FULL_TEXT",
        scope={"searched_char_count": 10, "text_layer_state": "full"},
    ))

    unverified = (
        " Coverage could not be verified; absence is not evidence that the "
        "source lacks the topic."
    )
    assert "Coverage could not be verified" not in complete
    assert bmi._REPORT_NO_EVIDENCE in complete
    for degraded in (absent, partial, broken):
        assert degraded.endswith(bmi._REPORT_NO_EVIDENCE + unverified)


def test_unavailable_coverage_selects_the_existing_note(tmp_path, monkeypatch):
    _seed(tmp_path)
    _stub_quota(monkeypatch)

    def note_for(coverage):
        _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
            evidence_state="UNAVAILABLE",
            coverage_state=coverage,
        )))
        return _report(tmp_path, "AAPL demand")["note"]

    assert note_for("SOURCE_REVISION_CHANGED").endswith(bmi._REPORT_SOURCE_UNVERIFIED)
    assert note_for("NO_TEXT_LAYER").endswith(bmi._REPORT_SCAN_ONLY)
    assert note_for("EXTRACTION_UNAVAILABLE").endswith(bmi._REPORT_EXCERPT_ONLY)
    assert note_for("SEGMENT_INDEX_PENDING").endswith(bmi._REPORT_EXCERPT_ONLY)


def test_producer_stale_appends_one_sentence_and_other_codes_do_not(tmp_path, monkeypatch):
    _seed(tmp_path)
    pages = _segments_from_pages(["The complete stored argument."])
    _stub_quota(monkeypatch)

    def generic(source):
        _install(monkeypatch, RecordingAdapter(segments=pages, source=source))
        return _report(tmp_path, "Summarize this report.")["note"]

    fresh = generic(_source())
    other = generic(_source(degradation=("PARTIAL_CORPUS",)))
    stale = generic(_source(state="PRODUCER_STALE", degradation=("PRODUCER_STALE",)))

    assert other == fresh
    assert STALE_SENTENCE not in fresh
    assert stale == fresh + STALE_SENTENCE
    assert stale.endswith(STALE_SENTENCE)
    assert bmi._REPORT_NOTE.split("{")[0] in stale


def test_generic_scan_and_excerpt_notes_follow_the_fetch_layer(tmp_path, monkeypatch):
    _seed(tmp_path)
    _stub_quota(monkeypatch)

    _install(monkeypatch, RecordingAdapter(
        segments=[], coverage="NO_TEXT_LAYER", text_layer="none",
    ))
    scan = _report(tmp_path, "")
    assert scan["report"]["body_text"] == ""
    assert scan["quota"] is None
    assert scan["note"].endswith(bmi._REPORT_SCAN_ONLY)

    _install(monkeypatch, RecordingAdapter(
        segments=[], coverage="EXTRACTION_UNAVAILABLE", text_layer="",
    ))
    excerpt = _report(tmp_path, "")
    assert excerpt["note"].endswith(bmi._REPORT_EXCERPT_ONLY)

    _install(monkeypatch, RecordingAdapter(
        segments=_segments_from_pages(["   "]),
        coverage="FULL_TEXT",
        text_layer="",
    ))
    blank = _report(tmp_path, "")
    assert blank["report"]["body_text"] == ""
    assert blank["quota"] is None


def test_disagreement_on_passage_sha_fails_closed(tmp_path, monkeypatch):
    _seed(tmp_path)
    text = "The desk raised AAPL demand estimates."
    first = _passage(text, "AAPL demand")
    second = _passage("other AAPL demand text", "AAPL demand")
    second["source_pdf_sha256"] = "c" * 64
    _install(monkeypatch, RecordingAdapter(find_result=_evidence_result(
        evidence_state="FOUND",
        coverage_state="FULL_TEXT",
        passages=[first, second],
        scope=_scope(searched_char_count=len(text)),
    )))
    debits = _stub_quota(monkeypatch)

    result = _report(tmp_path, "AAPL demand")
    assert result["evidence"]["status"] == "body_unavailable"
    assert result["evidence"]["passages"] == []
    assert result["report"]["body_text"] == ""
    assert debits == []


def test_report_schema_and_fields_stay_the_whitelisted_set(tmp_path, monkeypatch):
    _seed(tmp_path)
    _install(monkeypatch, RecordingAdapter(
        segments=_segments_from_pages(["The complete stored argument."]),
    ))
    _stub_quota(monkeypatch)
    result = _report(tmp_path, "")
    assert result["schema"] == "brain.research_report.v1"
    assert set(result["report"]) == set(bmi.REPORT_FIELDS)
    assert set(result) == {"schema", "asof", "report", "quota", "evidence", "note"}
    assert "tier" not in result and "entitlement" not in result
