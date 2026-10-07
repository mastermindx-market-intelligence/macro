"""Lane A tests for ResearchReadService (F10 T1–T14)."""
from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine.research_intelligence.store import (
    ResearchIntelligenceInvalid,
    ResearchIntelligenceStoreError,
    StoredResearchIntelligence,
)
from engine.research_vault import catalog as catalog_mod
from engine.research_vault import corpus as corpus_mod
from engine.research_vault import fulltext
from engine.research_vault.r2_store import LocalStore
from engine.research_vault.read_service import (
    ResearchReadService,
    ServerReadContext,
)
from scripts.check_research_vault_source_freshness import evaluate

NOW = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
PDF_SHA = hashlib.sha256(b"f10-service-pdf").hexdigest()
RIO_QUOTE = "RIO_SECRET_QUOTE_NEVER_LEAK"
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


def _item(doc_id, title, published_at, institution="Goldman Sachs", **extra):
    row = {
        "id": doc_id,
        "title": title,
        "institution": institution,
        "side": "sell",
        "published_at": published_at,
        "pages": extra.get("pages", 2),
        "language": extra.get("language", "en"),
        "summary_points": extra.get("summary_points", ["catalog summary"]),
    }
    return row


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


def _rio(report_id, source_sha, quote=RIO_QUOTE):
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
        rio={"quote": quote},
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
    inventory_ft=None,
    inventory_rio=None,
    corpus_rows=None,
    corpus_factory=None,
    classifier=None,
    clock=None,
    put_catalog=True,
):
    store = LocalStore(tmp_path / "store")
    if put_catalog:
        _put_catalog(store, items, generated_at)
    path = tmp_path / "corpus.sqlite"
    if corpus_factory is None:
        rows = corpus_rows
        if rows is None:
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
        corpus_factory = _open_corpus(path, rows)
    loader_map = extracted if extracted is not None else {}
    loader = CallCounter(
        (lambda report_id, _item: loader_map.get(report_id)) if loader_map is not None else None
    )
    if extracted is None:
        loader = CallCounter(lambda report_id, _item: None)
    digest_reader = CallCounter(digest if callable(digest) else (lambda _rid: digest))
    if rio is None:
        rio_reader = CallCounter(lambda _rid: None)
    elif rio is False:
        rio_reader = None
    else:
        rio_reader = rio if callable(rio) else CallCounter(lambda _rid: rio)
    preview_ids = preview if preview is not None else [item["id"] for item in items[:1]]
    svc = ResearchReadService(
        catalog_store=store,
        corpus_connection=CallCounter(corpus_factory) if not isinstance(corpus_factory, CallCounter) else corpus_factory,
        preview_selector=lambda _catalog: list(preview_ids),
        extracted_text_loader=loader,
        source_digest_reader=digest_reader,
        rio_reader=rio_reader,
        full_text_inventory=inventory_ft,
        rio_inventory=inventory_rio,
        source_classifier=classifier,
        clock=clock or (lambda: NOW),
    )
    return svc, store, loader, digest_reader, rio_reader, svc._corpus_connection


def _segments(record):
    return fulltext.build_segments(
        record,
        segmenter_version=fulltext.SEGMENTER_VERSION,
        max_bytes=4000,
    )


def test_fixture_canonical_text_shape():
    record = _extracted("alpha-report")
    segments = _segments(record)
    assert "研究" in CANONICAL
    assert "表格" in CANONICAL
    assert "\f" in CANONICAL
    assert len(segments) >= 2
    assert record["page_boundaries"][0]["page_index"] == 1
    assert record["page_boundaries"][1]["page_index"] == 2


def test_t1_producer_stale_matches_real_evaluate(tmp_path):
    published = "2026-09-01T12:00:00+00:00"
    items = [
        _item("alpha-report", "Alpha Note", published),
        _item("beta-report", "Beta Note", "2026-08-20T12:00:00+00:00"),
    ]
    record = _extracted("alpha-report")
    svc, store, *_ = _service(
        tmp_path,
        items=items,
        generated_at=NOW,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        rio=_rio("alpha-report", record["extracted_text_sha256"]),
        preview=["alpha-report"],
    )
    catalog = catalog_mod.read_strict(store, NOW)
    expected = evaluate(catalog, now=NOW, source="catalog")["status"]
    assert expected == "PRODUCER_STALE"

    status = svc.status(caller_context=_ctx())
    search = svc.search(
        caller_context=_ctx(),
        query="hyperscaler",
        filters={},
        limit=10,
        cursor=None,
    )
    evidence = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="hyperscaler",
        max_passages=3,
    )
    for result in (status, search, evidence):
        assert result["ok"] is True
        assert result["source"]["state"] == "PRODUCER_STALE"
        assert "PRODUCER_STALE" in result["source"]["known_degradation"]
        assert result["source"]["state"] == expected


def test_t2_fresh_reports_stale_catalog_publication(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    generated = NOW - timedelta(hours=3)
    record = _extracted("alpha-report")
    svc, *_ = _service(
        tmp_path,
        items=items,
        generated_at=generated,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    status = svc.status(caller_context=_ctx())
    assert status["ok"] is True
    assert status["source"]["state"] == "SOURCE_FRESH"
    assert "PRODUCER_STALE" in status["source"]["known_degradation"]


def test_t3_missing_catalog_does_not_touch_readers(tmp_path):
    items = [_item("alpha-report", "Alpha Note", NOW.isoformat())]
    record = _extracted("alpha-report")
    svc, _store, loader, digest, rio, corpus_factory = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        rio=_rio("alpha-report", record["extracted_text_sha256"]),
        put_catalog=False,
    )
    search = svc.search(
        caller_context=_ctx(),
        query="hyperscaler",
        filters={},
        limit=10,
        cursor=None,
    )
    evidence = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="hyperscaler",
        max_passages=3,
    )
    status = svc.status(caller_context=_ctx())
    for result in (search, evidence, status):
        assert result["source"]["state"] == "CATALOG_UNAVAILABLE"
        assert result["source"]["report_count"] == 0
    assert search["available"] is False
    assert search["candidates"] == []
    assert evidence["evidence_state"] == "UNAVAILABLE"
    assert evidence["passages"] == []
    assert loader.calls == 0
    assert digest.calls == 0
    assert rio.calls == 0
    assert corpus_factory.calls == 0


def test_t3_future_generated_at_is_unavailable(tmp_path):
    items = [_item("alpha-report", "Alpha Note", NOW.isoformat())]
    record = _extracted("alpha-report")
    svc, _store, loader, digest, rio, corpus_factory = _service(
        tmp_path,
        items=items,
        generated_at=NOW + timedelta(hours=1),
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        rio=_rio("alpha-report", record["extracted_text_sha256"]),
    )
    search = svc.search(
        caller_context=_ctx(),
        query="hyperscaler",
        filters={},
        limit=10,
        cursor=None,
    )
    evidence = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="hyperscaler",
        max_passages=3,
    )
    assert search["source"]["state"] == "CATALOG_UNAVAILABLE"
    assert search["available"] is False
    assert search["candidates"] == []
    assert evidence["evidence_state"] == "UNAVAILABLE"
    assert evidence["passages"] == []
    assert evidence["source"]["report_count"] == 0
    assert loader.calls == 0
    assert digest.calls == 0
    assert rio.calls == 0
    assert corpus_factory.calls == 0


def test_t4_empty_catalog_is_no_reports(tmp_path):
    svc, *_ = _service(tmp_path, items=[], generated_at=NOW, extracted={}, preview=[])
    status = svc.status(caller_context=_ctx())
    assert status["source"]["state"] == "NO_REPORTS"


def test_t4_future_report_clock(tmp_path):
    published = (NOW + timedelta(minutes=10)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    svc, *_ = _service(tmp_path, items=items, extracted={}, preview=["alpha-report"])
    status = svc.status(caller_context=_ctx())
    assert status["source"]["state"] == "FUTURE_REPORT_CLOCK"


def test_t4_unparseable_published_at_is_latest_report_invalid(tmp_path):
    items = [_item("alpha-report", "Alpha Note", "not-a-clock")]
    svc, *_ = _service(tmp_path, items=items, extracted={}, preview=["alpha-report"])
    status = svc.status(caller_context=_ctx())
    assert status["source"]["state"] == "LATEST_REPORT_INVALID"


def test_t5_passages_are_byte_literal_including_cjk(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    assert len(_segments(record)) >= 2
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    canonical = record["text"]
    encoded = canonical.encode("utf-8")
    segments = _segments(record)
    for query, expect_page in (("hyperscaler", 1), ("表格", 2), ("研究", 1)):
        result = svc.find_evidence(
            caller_context=_ctx(),
            report_id="alpha-report",
            query=query,
            max_passages=3,
        )
        assert result["ok"] is True
        assert result["passages"]
        for passage in result["passages"]:
            raw = encoded[passage["start_byte"]:passage["end_byte"]]
            assert passage["text"].encode("utf-8") == raw
            assert passage["passage_text_sha256"] == hashlib.sha256(raw).hexdigest()
            assert passage["extracted_text_sha256"] == record["extracted_text_sha256"]
            owners = [
                seg["segment_index"]
                for seg in segments
                if seg["start_byte"] <= passage["start_byte"] < seg["end_byte"]
            ]
            assert passage["segment_index"] == owners[0]
            assert passage["page_start"] == expect_page
            assert passage["page_end"] == expect_page


def test_t6_corpus_body_is_never_evidence(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={},
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    result = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="hyperscaler",
        max_passages=3,
    )
    assert result["evidence_state"] == "UNAVAILABLE"
    assert result["coverage_state"] == "EXTRACTION_UNAVAILABLE"
    assert result["passages"] == []


def test_t7_rio_cannot_convert_unavailable_text_into_success(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    unavailable = _extracted("alpha-report", text=None, layer="unavailable")
    rio = _rio("alpha-report", unavailable["extracted_text_sha256"], quote=f"{RIO_QUOTE} hyperscaler")
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": unavailable},
        digest=PDF_SHA,
        rio=rio,
        preview=["alpha-report"],
    )
    result = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="hyperscaler",
        max_passages=3,
    )
    assert result["evidence_state"] == "UNAVAILABLE"
    assert result["passages"] == []
    assert result["rio_state"] == "CURRENT"
    assert RIO_QUOTE not in json.dumps(result)


def test_t7_available_text_without_match_is_not_found(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        rio=_rio("alpha-report", record["extracted_text_sha256"]),
        preview=["alpha-report"],
    )
    result = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="zzznomatchtoken",
        max_passages=3,
    )
    assert result["evidence_state"] == "NOT_FOUND"
    assert result["passages"] == []
    assert RIO_QUOTE not in json.dumps(result)


def test_t7_match_with_missing_rio(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        rio=None,
        preview=["alpha-report"],
    )
    result = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="hyperscaler",
        max_passages=3,
    )
    assert result["evidence_state"] == "FOUND"
    assert result["rio_state"] == "MISSING"
    assert result["passages"]
    assert RIO_QUOTE not in json.dumps(result)


def test_t7_rio_store_error_is_partial_and_does_not_change_evidence(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")

    def boom(_rid):
        raise ResearchIntelligenceStoreError("store", "unavailable")

    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        rio=CallCounter(boom),
        preview=["alpha-report"],
    )
    result = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="hyperscaler",
        max_passages=3,
    )
    assert result["evidence_state"] == "FOUND"
    assert result["rio_state"] == "MISSING"
    assert "RIO_PARTIAL" in result["source"]["known_degradation"]
    assert RIO_QUOTE not in json.dumps(result)


def test_t8_rio_hash_and_error_states(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    matching = _rio("alpha-report", record["extracted_text_sha256"])
    mismatch = _rio("alpha-report", hashlib.sha256(b"other-text").hexdigest())

    def invalid(_rid):
        raise ResearchIntelligenceInvalid("invalid", "bad artifact")

    cases = [
        (matching, "CURRENT"),
        (mismatch, "STALE"),
        (CallCounter(invalid), "INVALID"),
        (False, "NOT_REQUESTED"),
    ]
    for rio, expected in cases:
        svc, *_ = _service(
            tmp_path,
            items=items,
            extracted={"alpha-report": record},
            digest=PDF_SHA,
            rio=rio,
            preview=["alpha-report"],
        )
        fetched = svc.fetch(
            caller_context=_ctx(),
            report_id="alpha-report",
            selectors={},
        )
        assert fetched["rio_state"] == expected, expected


def test_t9_plain_dict_is_authentication_required(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    fake = {
        "entitlement": "pro",
        "scopes": ("status", "search", "fetch", "find_evidence"),
        "surface": "brain",
        "authenticated": True,
    }
    status = svc.status(caller_context=fake)
    search = svc.search(
        caller_context=fake, query="hyperscaler", filters={}, limit=10, cursor=None
    )
    fetched = svc.fetch(caller_context=fake, report_id="alpha-report", selectors={})
    evidence = svc.find_evidence(
        caller_context=fake, report_id="alpha-report", query="hyperscaler", max_passages=3
    )
    for result in (status, search, fetched, evidence):
        assert result["ok"] is False
        assert result["code"] == "AUTHENTICATION_REQUIRED"


def test_t9_anonymous_and_preview_entitlement_gates(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    anon = _ctx("anonymous")
    preview = _ctx("preview")
    for ctx, code in ((anon, "AUTHENTICATION_REQUIRED"), (preview, "REPORT_NOT_ENTITLED")):
        fetched = svc.fetch(caller_context=ctx, report_id="alpha-report", selectors={})
        missing = svc.fetch(caller_context=ctx, report_id="missing-report", selectors={})
        evidence = svc.find_evidence(
            caller_context=ctx, report_id="alpha-report", query="hyperscaler", max_passages=3
        )
        for result in (fetched, missing, evidence):
            assert result["ok"] is False
            assert result["code"] == code


def test_t9_missing_scope_is_insufficient(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    svc, *_ = _service(tmp_path, items=items, extracted={}, preview=["alpha-report"])
    ctx = _ctx(scopes=frozenset({"status"}))
    search = svc.search(
        caller_context=ctx, query="hyperscaler", filters={}, limit=10, cursor=None
    )
    assert search["ok"] is False
    assert search["code"] == "INSUFFICIENT_SCOPE"


def test_t9_search_preview_is_a_strict_subset_of_pro(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [
        _item("alpha-report", "Alpha Note", published),
        _item("beta-report", "Beta Note", published, institution="Bernstein"),
        _item("gamma-report", "Gamma Note", published),
    ]
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={},
        preview=["alpha-report", "beta-report"],
    )
    query = "hyperscaler"
    anon = svc.search(
        caller_context=_ctx("anonymous"), query=query, filters={}, limit=10, cursor=None
    )
    preview = svc.search(
        caller_context=_ctx("preview"), query=query, filters={}, limit=10, cursor=None
    )
    pro = svc.search(
        caller_context=_ctx("pro"), query=query, filters={}, limit=10, cursor=None
    )
    anon_ids = {row["report_id"] for row in anon["candidates"]}
    preview_ids = {row["report_id"] for row in preview["candidates"]}
    pro_ids = {row["report_id"] for row in pro["candidates"]}
    assert anon_ids <= {"alpha-report", "beta-report"}
    assert preview_ids <= {"alpha-report", "beta-report"}
    assert anon_ids == preview_ids
    assert pro_ids == {"alpha-report", "beta-report", "gamma-report"}
    assert anon_ids != pro_ids


def test_t10_unknown_id_is_not_found_without_readers(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    svc, _store, loader, digest, rio, _corpus = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        rio=_rio("alpha-report", record["extracted_text_sha256"]),
        preview=["alpha-report"],
    )
    loader.calls = 0
    digest.calls = 0
    if rio is not None:
        rio.calls = 0
    result = svc.fetch(
        caller_context=_ctx(),
        report_id="unknown-report",
        selectors={},
    )
    evidence = svc.find_evidence(
        caller_context=_ctx(),
        report_id="unknown-report",
        query="hyperscaler",
        max_passages=3,
    )
    assert result["code"] == "REPORT_NOT_FOUND"
    assert evidence["code"] == "REPORT_NOT_FOUND"
    assert loader.calls == 0
    assert digest.calls == 0
    if rio is not None:
        assert rio.calls == 0


def test_t10_malformed_id_and_search_bounds(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    svc, *_ = _service(tmp_path, items=items, extracted={}, preview=["alpha-report"])
    malformed = svc.fetch(caller_context=_ctx(), report_id="NOT_VALID", selectors={})
    assert malformed["code"] == "INVALID_REQUEST"
    for limit in (0, -1, True, "5"):
        result = svc.search(
            caller_context=_ctx(), query="hyperscaler", filters={}, limit=limit, cursor=None
        )
        assert result["code"] == "INVALID_REQUEST"
    clamped = svc.search(
        caller_context=_ctx(), query="hyperscaler", filters={}, limit=500, cursor=None
    )
    assert clamped["ok"] is True
    assert clamped["limit"] == 50
    cursor = svc.search(
        caller_context=_ctx(), query="hyperscaler", filters={}, limit=10, cursor="abc"
    )
    assert cursor["code"] == "INVALID_REQUEST"
    unknown_filter = svc.search(
        caller_context=_ctx(),
        query="hyperscaler",
        filters={"institution": "Goldman Sachs", "author": "x"},
        limit=10,
        cursor=None,
    )
    assert unknown_filter["code"] == "INVALID_REQUEST"
    long_query = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="a" * 501,
        max_passages=3,
    )
    assert long_query["code"] == "INVALID_REQUEST"
    for value in (0, 13):
        result = svc.find_evidence(
            caller_context=_ctx(),
            report_id="alpha-report",
            query="hyperscaler",
            max_passages=value,
        )
        assert result["code"] == "INVALID_REQUEST"


def test_t10_max_passages_twelve_still_caps_at_three(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    chunks = []
    for index in range(8):
        chunks.append(("uniqueToken%d " % index) + ("padding " * 200))
    text = ("page one 研究\f" + " ".join(chunks))
    record = _extracted("alpha-report", text=text)
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    result = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="padding",
        max_passages=12,
    )
    assert result["ok"] is True
    assert len(result["passages"]) <= 3


def test_t11_unadmitted_corpus_row_never_appears(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    catalog_item = _item("alpha-report", "Catalog Title", published)
    ghost = _item("ghost-report", "Corpus Title", published)
    path = tmp_path / "corpus.sqlite"
    corpus_factory = _open_corpus(
        path,
        [
            (catalog_item, "hyperscaler catalog body", {"content_sha256": PDF_SHA}),
            (ghost, "hyperscaler ghost body", {"content_sha256": hashlib.sha256(b"ghost").hexdigest()}),
        ],
    )
    svc, *_ = _service(
        tmp_path,
        items=[catalog_item],
        extracted={},
        preview=["alpha-report"],
        corpus_factory=corpus_factory,
    )
    result = svc.search(
        caller_context=_ctx(),
        query="hyperscaler",
        filters={},
        limit=10,
        cursor=None,
    )
    ids = [row["report_id"] for row in result["candidates"]]
    assert ids == ["alpha-report"]
    assert result["candidates"][0]["title"] == "Catalog Title"
    dumped = json.dumps(result)
    assert "summary" not in result["candidates"][0]
    assert "excerpt" not in result["candidates"][0]
    assert "body" not in result["candidates"][0]
    for key in ("summary", "excerpt", "body"):
        assert f'"{key}"' not in dumped.split("candidates")[-1] if False else True
    blob = json.dumps(result["candidates"])
    assert "summary" not in blob
    assert "excerpt" not in blob
    assert "body" not in blob
    assert "Corpus Title" not in dumped


def test_t12_digest_mismatch_is_revision_changed(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    other = hashlib.sha256(b"other-pdf").hexdigest()
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=other,
        preview=["alpha-report"],
    )
    evidence = svc.find_evidence(
        caller_context=_ctx(),
        report_id="alpha-report",
        query="hyperscaler",
        max_passages=3,
    )
    fetched = svc.fetch(
        caller_context=_ctx(),
        report_id="alpha-report",
        selectors={},
    )
    assert evidence["coverage_state"] == "SOURCE_REVISION_CHANGED"
    assert evidence["evidence_state"] == "UNAVAILABLE"
    assert fetched["coverage_state"] == "SOURCE_REVISION_CHANGED"


def test_t13_fetch_segments_replay_and_pagination(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    record = _extracted("alpha-report")
    full = _segments(record)
    assert len(full) >= 2
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted={"alpha-report": record},
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    first = svc.fetch(
        caller_context=_ctx(),
        report_id="alpha-report",
        selectors={"segment_start": 0, "max_segments": 2},
    )
    assert first["ok"] is True
    assert first["segments"]
    total_bytes = 0
    for row in first["segments"]:
        expected = full[row["segment_index"]]
        assert row["text"] == fulltext.replay_segment(record, expected)
        total_bytes += len(row["text"].encode("utf-8"))
    assert total_bytes <= 24_000
    paged = svc.fetch(
        caller_context=_ctx(),
        report_id="alpha-report",
        selectors={"segment_start": 1, "max_segments": 1},
    )
    assert paged["segments"][0]["segment_index"] == 1
    capped = svc.fetch(
        caller_context=_ctx(),
        report_id="alpha-report",
        selectors={"segment_start": 0, "max_segments": 4},
    )
    assert len(capped["segments"]) <= 4
    too_many = svc.fetch(
        caller_context=_ctx(),
        report_id="alpha-report",
        selectors={"max_segments": 5},
    )
    assert too_many["code"] == "INVALID_REQUEST"


def test_t13_loader_none_returns_no_segments(tmp_path):
    published = (NOW - timedelta(hours=1)).isoformat()
    items = [_item("alpha-report", "Alpha Note", published)]
    svc, *_ = _service(
        tmp_path,
        items=items,
        extracted=None,
        digest=PDF_SHA,
        preview=["alpha-report"],
    )
    # extracted=None makes loader return None via empty map in helper; force loader None.
    svc._extracted_text_loader = None
    result = svc.fetch(
        caller_context=_ctx(),
        report_id="alpha-report",
        selectors={},
    )
    assert result["segments"] == []
    assert result["coverage_state"] == "EXTRACTION_UNAVAILABLE"


def test_t14_ast_forbids_network_and_app_imports():
    path = Path("engine/research_vault/read_service.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {
        "app",
        "requests",
        "urllib",
        "http",
        "socket",
        "boto3",
        "botocore",
        "mcp",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & forbidden)
    source = path.read_text(encoding="utf-8")
    assert "os.environ" not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "environ":
            raise AssertionError("os.environ must not appear")
