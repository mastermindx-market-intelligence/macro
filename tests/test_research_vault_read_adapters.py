"""Lane B tests for Brain and MCP adapter shims (F10 T15–T19)."""
from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine.research_intelligence.store import StoredResearchIntelligence
from engine.research_vault import catalog as catalog_mod
from engine.research_vault import corpus as corpus_mod
from engine.research_vault import fulltext
from engine.research_vault.r2_store import LocalStore
from engine.research_vault.read_adapters import (
    ARGUMENT_SCHEMAS,
    FORBIDDEN_ARGUMENT_KEYS,
    TOOL_NAMES,
    BrainResearchAdapter,
    McpResearchAdapter,
)
from engine.research_vault.read_port import failure as port_failure
from engine.research_vault.read_service import ResearchReadService, ServerReadContext

NOW = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
PDF_SHA = hashlib.sha256(b"f10-service-pdf").hexdigest()
ALL_SCOPES = frozenset({"status", "search", "fetch", "find_evidence"})
PAGE1 = "研究 hyperscaler " + ("alpha pipeline capacity " * 220)
PAGE2 = "表格 omega " + ("beta excerpt unique " * 220)
CANONICAL = PAGE1 + "\f" + PAGE2
CORPUS_BODY = "WRONG CORPUS BODY hyperscaler 表格 研究 this must not become evidence"


class CallCounter:
    def __init__(self, impl=None):
        self.calls = 0
        self.impl = impl

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.impl is None:
            return None
        return self.impl(*args, **kwargs)


class SpyPort:
    """Port stand-in that records whether any operation was reached."""

    def __init__(self):
        self.calls = 0

    def _hit(self, **_kwargs):
        self.calls += 1
        return {"ok": True, "schema": "spy"}

    def status(self, *, caller_context):
        return self._hit(caller_context=caller_context)

    def search(self, *, caller_context, query, filters, limit, cursor):
        return self._hit(
            caller_context=caller_context,
            query=query,
            filters=filters,
            limit=limit,
            cursor=cursor,
        )

    def fetch(self, *, caller_context, report_id, selectors):
        return self._hit(
            caller_context=caller_context,
            report_id=report_id,
            selectors=selectors,
        )

    def find_evidence(self, *, caller_context, report_id, query, max_passages):
        return self._hit(
            caller_context=caller_context,
            report_id=report_id,
            query=query,
            max_passages=max_passages,
        )


def _item(doc_id, title, published_at, institution="Goldman Sachs", **extra):
    return {
        "id": doc_id,
        "title": title,
        "institution": institution,
        "side": "sell",
        "published_at": published_at,
        "pages": extra.get("pages", 2),
        "language": extra.get("language", "en"),
        "summary_points": extra.get("summary_points", ["catalog summary"]),
    }


def _extracted(report_id, text=CANONICAL, layer="full", pdf_sha=PDF_SHA):
    return fulltext.build_extracted_text(
        report_id=report_id,
        source_pdf_sha256=pdf_sha,
        text=text,
        extractor_name="pdftotext",
        extractor_version="poppler-layout-v1",
        page_count=2 if text and "\f" in text else 1,
        text_layer_state="unavailable" if text is None else layer,
    )


def _rio(report_id, source_sha):
    return StoredResearchIntelligence(
        document_id=report_id,
        artifact_sha256=hashlib.sha256(b"rio-artifact").hexdigest(),
        rio_sha256=hashlib.sha256(b"rio-body").hexdigest(),
        source_content_sha256=source_sha,
        artifact_key="research_vault/intelligence/v1/artifact",
        pointer_key="research_vault/intelligence/v1/pointer",
        pointer_version="1",
        is_latest=True,
        receipt={},
        rio={"quote": "unused"},
    )


def _ctx(entitlement="pro", scopes=ALL_SCOPES, principal="user-1", surface="brain"):
    return ServerReadContext(
        principal_id=None if entitlement == "anonymous" else principal,
        entitlement=entitlement,
        scopes=frozenset(scopes),
        surface=surface,
    )


def _put_catalog(store, items, generated_at):
    document = {
        "schema": catalog_mod.SCHEMA,
        "generated_at": "",
        "count": 0,
        "institutions": [],
        "items": list(items),
    }
    store.put_bytes(catalog_mod.CATALOG_KEY, catalog_mod.serialize(document, generated_at))
    return document


def _open_corpus(path: Path, rows):
    conn = corpus_mod.open_db(path)
    for item, body, facts in rows:
        corpus_mod.upsert(conn, item, body, facts=facts)
    conn.close()

    def factory():
        return corpus_mod.open_db(path)

    return factory


def _service(
    tmp_path,
    *,
    items,
    generated_at=NOW,
    extracted=None,
    digest=None,
    rio=None,
    preview=None,
):
    store = LocalStore(tmp_path / "store")
    _put_catalog(store, items, generated_at)
    rows = []
    for item in items:
        rows.append(
            (
                item,
                CORPUS_BODY,
                {
                    "content_sha256": PDF_SHA,
                    "text_layer": "full",
                    "char_count": len(CORPUS_BODY),
                    "pages": 2,
                },
            )
        )
    corpus_factory = _open_corpus(tmp_path / "corpus.sqlite", rows)
    loader_map = extracted if extracted is not None else {}
    loader = CallCounter(lambda report_id, _item: loader_map.get(report_id))
    digest_reader = CallCounter(digest if callable(digest) else (lambda _rid: digest))
    if rio is None:
        rio_reader = CallCounter(lambda _rid: None)
    else:
        rio_reader = rio if callable(rio) else CallCounter(lambda _rid: rio)
    preview_ids = preview if preview is not None else [item["id"] for item in items[:1]]
    svc = ResearchReadService(
        catalog_store=store,
        corpus_connection=CallCounter(corpus_factory),
        preview_selector=lambda _catalog: list(preview_ids),
        extracted_text_loader=loader,
        source_digest_reader=digest_reader,
        rio_reader=rio_reader,
        clock=lambda: NOW,
    )
    return svc


def _adapters(port):
    return BrainResearchAdapter(port), McpResearchAdapter(port)


def _fresh_items():
    published = (NOW - timedelta(hours=1)).isoformat()
    return [
        _item("alpha-report", "Alpha Note", published),
        _item("beta-report", "Beta Note", published, institution="Bernstein"),
        _item("gamma-report", "Gamma Note", published),
    ]


def _stale_items():
    return [
        _item("alpha-report", "Alpha Note", "2026-09-01T12:00:00+00:00"),
        _item("beta-report", "Beta Note", "2026-08-20T12:00:00+00:00", institution="Bernstein"),
        _item("gamma-report", "Gamma Note", "2026-08-01T12:00:00+00:00"),
    ]


def _parity_calls(brain, mcp, ctx):
    return (
        (
            "research_status",
            {},
            lambda tool, arguments: brain.call(tool, arguments, server_context=ctx),
            lambda tool, arguments: mcp.call_tool(tool, arguments, server_context=ctx),
        ),
        (
            "research_search",
            {"query": "hyperscaler", "filters": {}, "limit": 10, "cursor": None},
            lambda tool, arguments: brain.call(tool, arguments, server_context=ctx),
            lambda tool, arguments: mcp.call_tool(tool, arguments, server_context=ctx),
        ),
        (
            "research_fetch",
            {"report_id": "alpha-report", "selectors": {}},
            lambda tool, arguments: brain.call(tool, arguments, server_context=ctx),
            lambda tool, arguments: mcp.call_tool(tool, arguments, server_context=ctx),
        ),
        (
            "research_find_evidence",
            {"report_id": "alpha-report", "query": "hyperscaler", "max_passages": 3},
            lambda tool, arguments: brain.call(tool, arguments, server_context=ctx),
            lambda tool, arguments: mcp.call_tool(tool, arguments, server_context=ctx),
        ),
    )


def _assert_adapter_parity(brain, mcp, ctx):
    for tool, arguments, brain_call, mcp_call in _parity_calls(brain, mcp, ctx):
        brain_env = brain_call(tool, arguments)
        mcp_env = mcp_call(tool, arguments)
        assert brain_env["result"] == mcp_env["structuredContent"]
        result = brain_env["result"]
        assert result.get("ok") is True
        if "candidates" in result:
            brain_ids = [row["report_id"] for row in result["candidates"]]
            mcp_ids = [row["report_id"] for row in mcp_env["structuredContent"]["candidates"]]
            assert brain_ids == mcp_ids
        if "coverage_state" in result:
            assert result["coverage_state"] == mcp_env["structuredContent"]["coverage_state"]
        if "source" in result:
            assert result["source"]["state"] == mcp_env["structuredContent"]["source"]["state"]


def test_t15_brain_result_equals_mcp_structured_content_fresh_and_stale(tmp_path):
    items_fresh = _fresh_items()
    items_stale = _stale_items()
    record = _extracted("alpha-report")
    rio = _rio("alpha-report", record["extracted_text_sha256"])
    cases = (
        (tmp_path / "fresh", items_fresh, NOW, "SOURCE_FRESH"),
        (tmp_path / "stale", items_stale, NOW, "PRODUCER_STALE"),
    )
    ctx = _ctx("pro")
    for root, items, generated_at, expected_state in cases:
        svc = _service(
            root,
            items=items,
            generated_at=generated_at,
            extracted={"alpha-report": record},
            digest=PDF_SHA,
            rio=rio,
            preview=["alpha-report", "beta-report"],
        )
        brain, mcp = _adapters(svc)
        _assert_adapter_parity(brain, mcp, ctx)
        status = brain.call("research_status", {}, server_context=ctx)["result"]
        search = brain.call(
            "research_search",
            {"query": "hyperscaler", "filters": {}, "limit": 10, "cursor": None},
            server_context=ctx,
        )["result"]
        fetched = brain.call(
            "research_fetch",
            {"report_id": "alpha-report", "selectors": {}},
            server_context=ctx,
        )["result"]
        evidence = brain.call(
            "research_find_evidence",
            {"report_id": "alpha-report", "query": "hyperscaler", "max_passages": 3},
            server_context=ctx,
        )["result"]
        for result in (status, search, fetched, evidence):
            assert result["source"]["state"] == expected_state


def test_t16_forbidden_keys_never_reach_the_port():
    spy = SpyPort()
    brain, mcp = _adapters(spy)
    ctx = _ctx("pro")
    expected = port_failure("INVALID_REQUEST")
    for key in sorted(FORBIDDEN_ARGUMENT_KEYS):
        arguments = {"query": "hyperscaler", key: "attacker"}
        spy.calls = 0
        brain_env = brain.call("research_search", arguments, server_context=ctx)
        assert spy.calls == 0
        assert brain_env["result"] == expected
        mcp_env = mcp.call_tool("research_search", arguments, server_context=ctx)
        assert spy.calls == 0
        assert mcp_env["structuredContent"] == expected
        assert mcp_env["isError"] is True


def test_t16_anonymous_and_pro_diverge_through_both_adapters(tmp_path):
    items = _fresh_items()
    record = _extracted("alpha-report")
    svc = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        preview=["alpha-report", "beta-report"],
    )
    brain, mcp = _adapters(svc)
    arguments = {"query": "hyperscaler", "filters": {}, "limit": 10, "cursor": None}
    anon = _ctx("anonymous")
    pro = _ctx("pro")
    brain_anon = brain.call("research_search", arguments, server_context=anon)["result"]
    brain_pro = brain.call("research_search", arguments, server_context=pro)["result"]
    mcp_anon = mcp.call_tool("research_search", arguments, server_context=anon)["structuredContent"]
    mcp_pro = mcp.call_tool("research_search", arguments, server_context=pro)["structuredContent"]
    assert brain_anon == mcp_anon
    assert brain_pro == mcp_pro
    anon_ids = {row["report_id"] for row in brain_anon["candidates"]}
    pro_ids = {row["report_id"] for row in brain_pro["candidates"]}
    assert anon_ids == {row["report_id"] for row in mcp_anon["candidates"]}
    assert pro_ids == {row["report_id"] for row in mcp_pro["candidates"]}
    assert anon_ids <= {"alpha-report", "beta-report"}
    assert pro_ids == {"alpha-report", "beta-report", "gamma-report"}
    assert anon_ids != pro_ids


def _walk_object_schemas(node):
    if isinstance(node, dict):
        is_object = node.get("type") == "object" or "properties" in node
        if is_object:
            yield node
        properties = node.get("properties")
        if isinstance(properties, dict):
            for child in properties.values():
                yield from _walk_object_schemas(child)
        for key, child in node.items():
            if key == "properties":
                continue
            yield from _walk_object_schemas(child)
    elif isinstance(node, list):
        for child in node:
            yield from _walk_object_schemas(child)


def test_t17_schemas_match_forbid_entitlement_keys_and_are_closed():
    brain, mcp = _adapters(SpyPort())
    brain_schemas = brain.tool_schemas()
    mcp_tools = mcp.list_tools()
    assert set(brain_schemas) == set(TOOL_NAMES)
    assert {row["name"] for row in mcp_tools} == set(TOOL_NAMES)
    assert len(mcp_tools) == 4
    for row in mcp_tools:
        assert row["inputSchema"] == brain_schemas[row["name"]]
        assert row["inputSchema"] == ARGUMENT_SCHEMAS[row["name"]]
    for schema in brain_schemas.values():
        for node in _walk_object_schemas(schema):
            assert node.get("additionalProperties") is False
            for name in node.get("properties") or {}:
                assert name not in FORBIDDEN_ARGUMENT_KEYS
    mutated = brain.tool_schemas()
    mutated["research_status"]["properties"]["entitlement"] = {"type": "string"}
    listed = mcp.list_tools()
    listed[0]["inputSchema"]["properties"]["principal_id"] = {"type": "string"}
    assert "entitlement" not in ARGUMENT_SCHEMAS["research_status"]["properties"]
    assert "principal_id" not in brain.tool_schemas()["research_status"]["properties"]
    assert "principal_id" not in mcp.list_tools()[0]["inputSchema"]["properties"]


def test_t18_mcp_envelope_roundtrip_and_ast_purity(tmp_path):
    items = _fresh_items()
    record = _extracted("alpha-report")
    svc = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    mcp = McpResearchAdapter(svc)
    ctx = _ctx("pro")
    success = mcp.call_tool(
        "research_search",
        {"query": "hyperscaler", "limit": 10},
        server_context=ctx,
    )
    assert json.loads(success["content"][0]["text"]) == success["structuredContent"]
    assert success["isError"] is (success["structuredContent"].get("ok") is not True)
    assert success["isError"] is False
    error = mcp.call_tool("not-a-tool", {}, server_context=ctx)
    assert json.loads(error["content"][0]["text"]) == error["structuredContent"]
    assert error["isError"] is (error["structuredContent"].get("ok") is not True)
    assert error["isError"] is True
    assert error["content"][0]["type"] == "text"

    path = Path("engine/research_vault/read_adapters.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {"mcp", "app", "requests", "urllib", "http", "socket"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & forbidden)


def test_t19_unknown_tool_and_non_mapping_arguments(tmp_path):
    items = _fresh_items()
    svc = _service(tmp_path, items=items, extracted={}, preview=["alpha-report"])
    brain, mcp = _adapters(svc)
    ctx = _ctx("pro")
    expected = port_failure("INVALID_REQUEST")
    unknown_brain = brain.call("research_delete", {}, server_context=ctx)
    unknown_mcp = mcp.call_tool("research_delete", {}, server_context=ctx)
    assert unknown_brain["result"] == expected
    assert unknown_mcp["structuredContent"] == expected
    for arguments in (None, [], "query", 1, True):
        brain_env = brain.call("research_status", arguments, server_context=ctx)
        mcp_env = mcp.call_tool("research_status", arguments, server_context=ctx)
        assert brain_env["result"] == expected
        assert mcp_env["structuredContent"] == expected
