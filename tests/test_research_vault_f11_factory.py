"""Actual F11 factory with revision-bound stored artifacts, no mocked text loader."""
import hashlib
import json

import pytest
from datetime import datetime, timezone

from engine.research_vault import catalog, fulltext, fulltext_store, read_runtime
from engine.research_vault.r2_store import LocalStore
from engine.research_vault.read_adapters import BrainResearchAdapter
from engine.research_vault.read_service import ServerReadContext


def test_actual_factory_fetches_current_canonical_derivative_and_refuses_correction(tmp_path):
    class AuditedStore(LocalStore):
        def __init__(self, root):
            super().__init__(root)
            self.strict_reads = []
        def get_bytes_strict(self, key):
            self.strict_reads.append(key)
            return super().get_bytes_strict(key)
        def get_bytes_strict_bounded(self, key, maximum_bytes):
            self.strict_reads.append(key)
            return super().get_bytes_strict_bounded(key, maximum_bytes)
        def list_prefix(self, *args, **kwargs):
            raise AssertionError("fetch/evidence must not qualify text through filename listing")

    store = AuditedStore(tmp_path / "store")
    rid = "f11-factory-record"
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    pdf_sha = hashlib.sha256(b"synthetic source PDF identity").hexdigest()
    item = {"id": rid, "title": "Synthetic factory note", "institution": "Example Bank",
            "side": "sell", "published_at": "2026-10-05T11:00:00+00:00",
            "pages": 1, "summary_points": ["Synthetic summary"]}
    store.put_bytes(catalog.CATALOG_KEY, catalog.serialize({"schema": catalog.SCHEMA,
        "generated_at": "", "count": 0, "institutions": [], "items": [item]}, now))
    text = "研究 factorysentinel current canonical evidence. " * 80
    record = fulltext.build_extracted_text(report_id=rid, source_pdf_sha256=pdf_sha,
        text=text, extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION, page_count=1, text_layer_state="full")
    receipt_key = fulltext_store.receipt_key(rid)
    derivative_key = fulltext_store.derivative_key(rid, pdf_sha)
    store.put_bytes(receipt_key, json.dumps({"id": rid, "content_sha256": pdf_sha}).encode())
    store.put_bytes(derivative_key, fulltext_store.encode_record(record))
    svc = read_runtime.build_read_service(catalog_store=store,
        corpus_connection=lambda: None, clock=lambda: now)
    assert svc._source_classifier is not None
    ctx = ServerReadContext(principal_id="synthetic-user", entitlement="pro",
        scopes=frozenset({"fetch", "find_evidence"}), surface="brain")
    adapter = BrainResearchAdapter(svc)
    fetched = adapter.call("research_fetch", {"report_id": rid, "selectors": {}}, server_context=ctx)["result"]
    assert fetched["coverage_state"] == "FULL_TEXT"
    assert fetched["text_revision"]["source_pdf_sha256"] == pdf_sha
    assert fetched["text_revision"]["extracted_text_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert "".join(s["text"] for s in fetched["segments"]) == text
    assert store.strict_reads.count(receipt_key) == 2
    assert derivative_key in store.strict_reads
    assert not any(k.endswith(".pdf") for k in store.strict_reads)
    evidence = adapter.call("research_find_evidence", {"report_id": rid, "query": "factorysentinel", "max_passages": 3}, server_context=ctx)["result"]
    assert evidence["evidence_state"] == "FOUND"
    assert evidence["passages"]
    assert all(p["source_pdf_sha256"] == pdf_sha for p in evidence["passages"])
    assert all(text.encode()[p["start_byte"]:p["end_byte"]].decode() == p["text"]
               for p in evidence["passages"])
    corrected_sha = hashlib.sha256(b"corrected source PDF identity").hexdigest()
    store.put_bytes(receipt_key, json.dumps({"id": rid, "content_sha256": corrected_sha}).encode())
    changed = adapter.call("research_fetch", {"report_id": rid, "selectors": {}}, server_context=ctx)["result"]
    assert changed["coverage_state"] == "EXTRACTION_UNAVAILABLE"
    assert changed["text_revision"] is None
    assert changed["segments"] == []


@pytest.mark.parametrize("derivative_state", ["stale", "corrupt", "no_text"])
def test_factory_status_does_not_certify_filename_inventory(tmp_path, derivative_state):
    class ListedStore(LocalStore):
        list_calls = 0
        def list_prefix(self, *args, **kwargs):
            self.list_calls += 1
            return super().list_prefix(*args, **kwargs)

    store = ListedStore(tmp_path / "store")
    rid = "f11-inventory-record"
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    old_sha = hashlib.sha256(b"old synthetic PDF").hexdigest()
    current_sha = hashlib.sha256(b"current synthetic PDF").hexdigest()
    item = {"id": rid, "title": "Synthetic inventory note", "institution": "Example Bank",
            "side": "sell", "published_at": "2026-10-05T11:00:00+00:00",
            "pages": 1, "summary_points": ["Synthetic summary"]}
    store.put_bytes(catalog.CATALOG_KEY, catalog.serialize({"schema": catalog.SCHEMA,
        "generated_at": "", "count": 0, "institutions": [], "items": [item]}, now))
    store.put_bytes(fulltext_store.receipt_key(rid),
                    json.dumps({"id": rid, "content_sha256": current_sha}).encode())
    if derivative_state == "corrupt":
        store.put_bytes(fulltext_store.derivative_key(rid, current_sha), b"not a canonical object")
    else:
        sha = old_sha if derivative_state == "stale" else current_sha
        record = fulltext.build_extracted_text(report_id=rid, source_pdf_sha256=sha,
            text="synthetic old text" if derivative_state == "stale" else "",
            extractor_name=fulltext_store.EXTRACTOR_NAME,
            extractor_version=fulltext_store.EXTRACTOR_VERSION, page_count=1,
            text_layer_state="full" if derivative_state == "stale" else "none")
        store.put_bytes(fulltext_store.derivative_key(rid, sha), fulltext_store.encode_record(record))
    # The unchanged planner helper really sees all three names. It proves no
    # current/full-text qualification and therefore is not a status authority.
    assert fulltext_store.fulltext_inventory(store) == frozenset({rid})
    store.list_calls = 0
    service = read_runtime.build_read_service(catalog_store=store,
        corpus_connection=lambda: None, clock=lambda: now)
    ctx = ServerReadContext(principal_id="synthetic-user", entitlement="pro",
        scopes=frozenset({"status", "fetch"}), surface="brain")
    status = service.status(caller_context=ctx)
    # Frozen None-inventory semantics: zero with degradation means unavailable
    # measurement basis, not a measured census with zero qualified documents.
    assert status["full_text_coverage"] == 0.0
    assert "FULL_TEXT_PARTIAL" in status["source"]["known_degradation"]
    assert service._full_text_inventory is None
    assert store.list_calls == 0
    fetched = service.fetch(caller_context=ctx, report_id=rid, selectors={})
    assert fetched["coverage_state"] == ("NO_TEXT_LAYER" if derivative_state == "no_text" else "EXTRACTION_UNAVAILABLE")
    assert fetched["segments"] == []
    assert store.list_calls == 0
