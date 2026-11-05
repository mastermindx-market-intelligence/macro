"""Current-source full-body discovery and correction regressions."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

import pytest

from engine.research_vault import corpus, fulltext, fulltext_store
from engine.research_vault import fulltext_index as index

PDF = "a" * 64
NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)


def item(rid="report-a"):
    return {"id": rid, "title": "Research", "institution": "Example", "side": "sell", "published_at": "2026-10-17T00:00:00Z", "summary_points": []}


def record(text, rid="report-a", digest=PDF, layer="full"):
    return fulltext.build_extracted_text(report_id=rid, source_pdf_sha256=digest,
        text=text, extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION,
        page_count=1, text_layer_state=layer)


@pytest.fixture
def env(tmp_path):
    conn = corpus.open_db(tmp_path / "corpus.sqlite")
    text = "oldprefix " + "alpha " * 11000 + " originaltail café"
    corpus.upsert(conn, item(), text, facts={"content_sha256": PDF, "text_layer": "full"})
    cat = {"schema": "research_vault.catalog.v1", "generated_at": "2026-10-18T00:00:00Z", "items": [item()]}
    yield conn, cat, text
    conn.close()


def stage(conn, cat, records, digests=None, **limits):
    return index.stage(conn, cat, record_loader=lambda rid: records.get(rid),
        source_digest_reader=lambda rid: (digests or {"report-a": PDF}).get(rid),
        max_rows=limits.get("max_rows", 20), max_body_bytes=limits.get("max_body_bytes", 1000000))


def hits(conn, query, **kwargs):
    return [r["id"] for r in corpus.search(conn, query, **kwargs)]


def test_tail_is_discovered_only_after_exact_full_body_stage(env):
    conn, cat, text = env
    assert hits(conn, "originaltail") == []
    result = stage(conn, cat, {"report-a": record(text)})
    assert result["full"] == 1
    assert hits(conn, "originaltail") == ["report-a"]
    row = conn.execute("SELECT body,fulltext_binding FROM documents").fetchone()
    assert row["body"] == text
    assert json.loads(row["fulltext_binding"])["extracted_text_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert index.discovery_coverage(conn, cat, {"report-a"}) == "FULL_TEXT"


def test_correction_with_unknown_revision_removes_prefix_and_tail(env):
    conn, cat, text = env
    stage(conn, cat, {"report-a": record(text)})
    stage(conn, cat, {}, digests={"report-a": "b" * 64})
    assert hits(conn, "oldprefix") == []
    assert hits(conn, "originaltail") == []
    assert index.discovery_coverage(conn, cat, {"report-a"}) != "FULL_TEXT"


def test_same_current_pdf_missing_derivative_keeps_only_legacy_prefix(env):
    conn, cat, text = env
    stage(conn, cat, {"report-a": record(text)})
    stage(conn, cat, {})
    assert hits(conn, "oldprefix") == ["report-a"]
    assert hits(conn, "originaltail") == []
    assert index.discovery_coverage(conn, cat, {"report-a"}) != "FULL_TEXT"


def test_digest_moves_after_record_load_refuses_upgrade_and_clears_body(env):
    conn, cat, text = env
    index.stage(conn, cat, record_loader=lambda _: record(text),
        source_digest_reader=lambda _: "b" * 64, max_rows=20, max_body_bytes=1000000)
    assert hits(conn, "oldprefix") == []
    assert hits(conn, "originaltail") == []


def test_legacy_upsert_resets_binding_and_tail_postings(env):
    conn, cat, text = env
    stage(conn, cat, {"report-a": record(text)})
    corpus.upsert(conn, item(), text, facts={"content_sha256": PDF})
    assert hits(conn, "originaltail") == []
    assert conn.execute("SELECT fulltext_binding FROM documents").fetchone()[0] is None
    assert index.discovery_coverage(conn, cat, {"report-a"}) != "FULL_TEXT"


def test_catalog_mismatch_never_certifies_full_text(env):
    conn, cat, text = env
    stage(conn, cat, {"report-a": record(text)})
    changed = dict(cat, generated_at="2026-10-19T00:00:00Z")
    assert index.discovery_coverage(conn, changed, {"report-a"}) != "FULL_TEXT"


@pytest.mark.parametrize("layer,text", [("thin", "short text"), ("none", "")])
def test_thin_and_none_are_separate_from_full_coverage(env, layer, text):
    conn, cat, _ = env
    result = stage(conn, cat, {"report-a": record(text, layer=layer)})
    assert result[layer] == 1 and result["full"] == 0
    assert index.discovery_coverage(conn, cat, {"report-a"}) != "FULL_TEXT"


def test_aggregate_budget_removes_previous_full_qualification(env):
    conn, cat, text = env
    stage(conn, cat, {"report-a": record(text)})
    result = stage(conn, cat, {"report-a": record(text)}, max_body_bytes=10)
    assert result["budget_skipped"] == 1
    assert hits(conn, "originaltail") == []
    assert index.discovery_coverage(conn, cat, {"report-a"}) != "FULL_TEXT"


def test_row_limit_refuses_before_read_or_mutation(env):
    conn, cat, text = env
    with pytest.raises(ValueError):
        index.stage(conn, cat, record_loader=lambda _: pytest.fail("must not load"),
            source_digest_reader=lambda _: PDF, max_rows=0, max_body_bytes=1000)
    assert hits(conn, "oldprefix") == ["report-a"]


def test_incomplete_migration_cannot_upgrade(env):
    conn, cat, text = env
    conn.execute("ALTER TABLE documents DROP COLUMN fulltext_binding")
    with pytest.raises(ValueError):
        stage(conn, cat, {"report-a": record(text)})
    assert hits(conn, "originaltail") == []


def test_stage_failure_rolls_back_whole_snapshot(env):
    conn, cat, text = env
    other = item("report-b");cat["items"].append(other)
    corpus.upsert(conn, other, "second", facts={"content_sha256": PDF})
    def loader(rid):
        if rid == "report-b":
            raise OSError("unavailable original source")
        return record(text)
    with pytest.raises(OSError):
        index.stage(conn, cat, record_loader=loader, source_digest_reader=lambda _: PDF,
            max_rows=20, max_body_bytes=1000000)
    assert hits(conn, "originaltail") == []


def test_visible_cohort_precedes_limit_and_does_not_expand_empty_queries(env):
    conn, _, _ = env
    for rid in ("report-b", "report-c"):
        corpus.upsert(conn, item(rid), "uniquephrase")
    result = hits(conn, "uniquephrase", limit=1, allowed_ids={"report-c"})
    assert result == ["report-c"]
    assert hits(conn, "", allowed_ids={"report-c"}) == []
    assert hits(conn, "uniquephrase", allowed_ids=set()) == []


def test_large_cohort_uses_bounded_sql_parameters(env):
    conn, _, _ = env
    corpus.upsert(conn, item("report-z"), "uniquephrase")
    previous = conn.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 4)
    try:
        allowed = {f"report-{i}" for i in range(4000)} | {"report-z"}
        assert hits(conn, "uniquephrase", allowed_ids=allowed) == ["report-z"]
    finally:
        conn.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, previous)



def service(conn, cat, tmp_path, preview=None, entitlement="pro"):
    from engine.research_vault import catalog
    from engine.research_vault.r2_store import LocalStore
    from engine.research_vault.read_service import ResearchReadService, ServerReadContext
    store = LocalStore(tmp_path / "store")
    blob = catalog.serialize(cat, NOW)
    store.put_bytes(catalog.CATALOG_KEY, blob)
    published = json.loads(blob)
    class Borrow:
        def execute(self, *args, **kwargs):
            return conn.execute(*args, **kwargs)
        def close(self):
            pass
    svc = ResearchReadService(catalog_store=store, corpus_connection=Borrow,
        preview_selector=lambda _: list(preview or []), clock=lambda: NOW)
    ctx = ServerReadContext(principal_id="private-pilot", entitlement=entitlement,
        scopes=frozenset({"search", "status"}), surface="brain")
    return svc, ctx, published


def test_actual_service_reports_bound_full_discovery_and_tail(env, tmp_path):
    conn, cat, text = env
    svc, ctx, published = service(conn, cat, tmp_path)
    stage(conn, published, {"report-a": record(text)})
    result = svc.search(caller_context=ctx, query="originaltail", filters={}, limit=1, cursor=None)
    assert result["coverage_state"] == "FULL_TEXT"
    assert [r["report_id"] for r in result["candidates"]] == ["report-a"]


def test_actual_service_cannot_reuse_old_publication_binding(env, tmp_path):
    conn, cat, text = env
    stage(conn, cat, {"report-a": record(text)})
    svc, ctx, _ = service(conn, cat, tmp_path)
    result = svc.search(caller_context=ctx, query="originaltail", filters={}, limit=1, cursor=None)
    assert result["coverage_state"] != "FULL_TEXT"
    assert "FULL_TEXT_PARTIAL" in result["source"]["known_degradation"]


def test_actual_service_filters_admitted_cohort_before_limit(env, tmp_path):
    conn, cat, _ = env
    corpus.upsert(conn, item("unadmitted"), "needle")
    corpus.upsert(conn, item(), "needle padding padding padding padding")
    svc, ctx, _ = service(conn, cat, tmp_path)
    result = svc.search(caller_context=ctx, query="needle", filters={}, limit=1, cursor=None)
    assert [r["report_id"] for r in result["candidates"]] == ["report-a"]


def test_same_pdf_multiple_reports_do_not_lose_corpus_presence(env, tmp_path):
    conn, cat, text = env
    other = item("report-b");cat["items"].append(other)
    corpus.upsert(conn, other, text, facts={"content_sha256": PDF})
    svc, ctx, published = service(conn, cat, tmp_path)
    stage(conn, published, {"report-a": record(text), "report-b": record(text, rid="report-b")}, digests={"report-a": PDF, "report-b": PDF})
    result = svc.search(caller_context=ctx, query="originaltail", filters={}, limit=5, cursor=None)
    assert result["corpus_state"] == "AVAILABLE"
    assert result["coverage_state"] == "FULL_TEXT"
    assert len(result["candidates"]) == 2



def test_distinct_qualified_extractor_must_be_explicit_and_is_not_relabelled(env):
    conn, cat, text = env
    actual = record(text)
    actual["extractor_name"] = "pdftotext-layout"
    actual["extractor_version"] = "26.06.0"
    assert stage(conn, cat, {"report-a": actual})["full"] == 0
    assert hits(conn, "originaltail") == []
    result = index.stage(conn, cat, record_loader=lambda _: actual,
        source_digest_reader=lambda _: PDF, max_rows=20, max_body_bytes=1000000,
        extractor_identity=("pdftotext-layout", "26.06.0"))
    assert result["full"] == 1
    binding = json.loads(conn.execute("SELECT fulltext_binding FROM documents").fetchone()[0])
    assert (binding["extractor_name"], binding["extractor_version"]) == ("pdftotext-layout", "26.06.0")
    assert index.discovery_coverage(conn, cat, {"report-a"}) == "FULL_TEXT"


def test_unchanged_full_body_does_not_rebuild_fts_at_each_checkpoint(env):
    conn, cat, text = env
    records = {'report-a': record(text)}
    stage(conn, cat, records)
    before = conn.total_changes
    stage(conn, cat, records)
    # Only the publication descriptor is refreshed; no body/FTS row rewrites.
    assert conn.total_changes - before == 1
    assert hits(conn, 'originaltail') == ['report-a']
