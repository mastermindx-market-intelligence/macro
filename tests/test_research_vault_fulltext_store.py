"""Stored canonical full-text derivative: reader, bounded producer, ingest hook."""
from __future__ import annotations

import ast
import functools
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from engine.research_intelligence import vault_head
from engine.research_vault import catalog as catalog_mod
from engine.research_vault import corpus as corpus_mod
from engine.research_vault import fulltext
from engine.research_vault import fulltext_store
from engine.research_vault import fulltext_writer
from engine.research_vault import ingest as ingest_mod
from engine.research_vault.r2_store import LocalStore
from engine.research_vault.read_service import (
    SEGMENT_MAX_BYTES,
    ResearchReadService,
    ServerReadContext,
)

REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
ALL_SCOPES = frozenset({"status", "search", "fetch", "find_evidence"})

_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n"
    b"%%EOF\n"
)

FORBIDDEN = (
    "engine.research_vault.ingest",
    "engine.research_vault.probe",
    "engine.research_intelligence.vault_head",
    "engine.press",
    "app",
    "pypdf",
    "PyPDF2",
    "pdfminer",
    "fitz",
    "pymupdf",
    "pdfplumber",
    "pdftotext",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(label: str = "canonical research body") -> str:
    return (label + " ") * 80


def _extractor(text: str):
    return lambda _pdf: text


def _put_pdf(store, report_id: str, pdf: bytes = _MINIMAL_PDF) -> str:
    store.put_bytes(f"research_vault/{report_id}.pdf", pdf, "application/pdf")
    return _sha(pdf)


def _put_receipt(store, report_id: str, digest: str | None, *, receipt_id: str | None = None) -> None:
    body: dict = {}
    if receipt_id is not None:
        body["id"] = receipt_id
    else:
        body["id"] = report_id
    if digest is not None:
        body["content_sha256"] = digest
    store.put_bytes(
        fulltext_store.receipt_key(report_id),
        json.dumps(body).encode("utf-8"),
        "application/json",
    )


def _arm(store, report_id: str, pdf: bytes = _MINIMAL_PDF, digest: str | None = None) -> str:
    sha = _put_pdf(store, report_id, pdf)
    _put_receipt(store, report_id, sha if digest is None else digest)
    return sha


def _item(report_id: str, published_at: str = "2026-10-01T00:00:00Z", **extra) -> dict:
    row = {
        "id": report_id,
        "title": extra.get("title", "Desk Note"),
        "institution": extra.get("institution", "Goldman Sachs"),
        "side": "sell",
        "published_at": published_at,
        "summary_points": ["catalog summary"],
    }
    return row


def _cat(*items: dict) -> dict:
    return {"items": list(items)}


class RecordingStore:
    """Delegates to LocalStore and records strict reads plus conditional puts."""

    def __init__(self, inner):
        self.inner = inner
        self.gets: list[tuple[str, object]] = []
        self.conditional_puts: list[tuple[str, bool]] = []
        self.pdf_reads: list[str] = []

    def get_bytes_strict_bounded(self, key, maximum_bytes=None, **kwargs):
        self.gets.append((key, maximum_bytes))
        if isinstance(key, str) and key.lower().endswith(".pdf"):
            self.pdf_reads.append(key)
        return self.inner.get_bytes_strict_bounded(key, maximum_bytes, **kwargs)

    def get_bytes(self, key):
        if isinstance(key, str) and key.lower().endswith(".pdf"):
            self.pdf_reads.append(key)
        return self.inner.get_bytes(key)

    def get_bytes_strict(self, key):
        if isinstance(key, str) and key.lower().endswith(".pdf"):
            self.pdf_reads.append(key)
        return self.inner.get_bytes_strict(key)

    def put_bytes_strict_conditional(self, key, data, *, expected_version, content_type="application/octet-stream"):
        ok = self.inner.put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type,
        )
        self.conditional_puts.append((key, bool(ok)))
        return ok

    def validate_strict_conditional_write_capability(self):
        return self.inner.validate_strict_conditional_write_capability()

    def put_bytes(self, key, data, content_type="application/octet-stream"):
        return self.inner.put_bytes(key, data, content_type)

    def list_prefix(self, prefix):
        return self.inner.list_prefix(prefix)

    def exists(self, key):
        return self.inner.exists(key)


class OversizePdfStore(RecordingStore):
    def get_bytes_strict_bounded(self, key, maximum_bytes=None, **kwargs):
        self.gets.append((key, maximum_bytes))
        if isinstance(key, str) and key.lower().endswith(".pdf"):
            self.pdf_reads.append(key)
            raise ValueError("bounded pdf read exceeded")
        return self.inner.get_bytes_strict_bounded(key, maximum_bytes, **kwargs)


class RaisingStore:
    def __init__(self, inner, *, raise_on):
        self.inner = inner
        self.raise_on = raise_on
        self.gets: list[str] = []

    def get_bytes_strict_bounded(self, key, maximum_bytes=None, **kwargs):
        self.gets.append(key)
        if self.raise_on == "any" or (self.raise_on == "derivative" and "fulltext/" in str(key)):
            raise RuntimeError("store down")
        return self.inner.get_bytes_strict_bounded(key, maximum_bytes, **kwargs)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def _pending(store, items, corpus, **kwargs):
    kwargs.setdefault("tool_available", lambda: True)
    kwargs.setdefault("run_started", 0.0)
    kwargs.setdefault("clock", lambda: 0.0)
    return fulltext_writer.materialize_pending(
        store, _cat(*items), corpus, **kwargs,
    )


def _write_corpus(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE documents (doc_id TEXT, content_sha256 TEXT)")
    conn.executemany("INSERT INTO documents VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


def _ctx():
    return ServerReadContext(
        principal_id="user-1",
        entitlement="pro",
        scopes=ALL_SCOPES,
        surface="brain",
    )


def _put_catalog(store, items):
    document = {
        "schema": catalog_mod.SCHEMA,
        "generated_at": "",
        "count": 0,
        "institutions": [],
        "items": list(items),
    }
    store.put_bytes(catalog_mod.CATALOG_KEY, catalog_mod.serialize(document, NOW))


def _corpus_factory(path: Path, rows):
    conn = corpus_mod.open_db(path)
    for item, body, facts in rows:
        corpus_mod.upsert(conn, item, body, facts=facts)
    conn.close()

    def factory():
        return corpus_mod.open_db(path)

    return factory


def _service(store, path: Path, item: dict):
    _put_catalog(store, [item])
    factory = _corpus_factory(path, [(
        item,
        "corpus body is not the canonical text",
        {"content_sha256": "ab" * 32, "text_layer": "full", "char_count": 10, "pages": 1},
    )])

    def _fresh(payload, *, now, source="catalog", **kwargs):
        return {
            "status": "SOURCE_FRESH",
            "age_hours": 1,
            "latest_report_at": item["published_at"],
            "invalid_published_at": 0,
        }

    return ResearchReadService(
        catalog_store=store,
        corpus_connection=factory,
        preview_selector=lambda _catalog: [item["id"]],
        extracted_text_loader=functools.partial(fulltext_store.load_extracted_text, store),
        source_digest_reader=functools.partial(fulltext_store.source_digest, store),
        full_text_inventory=functools.partial(fulltext_store.fulltext_inventory, store),
        rio_inventory=lambda: (),
        source_classifier=_fresh,
        clock=lambda: NOW,
    )


def _derivative_tag(schema, name, version, segmenter) -> str:
    payload = json.dumps(
        [schema, name, version, segmenter],
        separators=(",", ":"),
    ).encode("utf-8")
    return "v1-" + hashlib.sha256(payload).hexdigest()[:16]


def _is_forbidden(name: str) -> bool:
    return any(name == item or name.startswith(item + ".") for item in FORBIDDEN)


def _module_file(name: str) -> Path | None:
    if not name or name.startswith("."):
        return None
    parts = name.split(".")
    candidate = REPO.joinpath(*parts)
    module = candidate.with_suffix(".py")
    if module.is_file():
        return module
    init = candidate / "__init__.py"
    if init.is_file():
        return init
    return None


def _parents(name: str) -> list[str]:
    parts = name.split(".")
    return [".".join(parts[:index]) for index in range(1, len(parts))]


def _import_targets(module: str, path: Path, node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.level:
        parts = module.split(".")
        if path.name != "__init__.py":
            parts = parts[:-1]
        drop = node.level - 1
        if drop:
            parts = parts[:-drop]
        base_parts = parts
        if node.module:
            base_parts = parts + node.module.split(".")
        base = ".".join(base_parts)
        targets = [base] if base else []
        for alias in node.names:
            child = f"{base}.{alias.name}" if base else alias.name
            if _module_file(child) is not None:
                targets.append(child)
        return targets
    base = node.module or ""
    targets = [base] if base else []
    for alias in node.names:
        child = f"{base}.{alias.name}" if base else alias.name
        if _module_file(child) is not None:
            targets.append(child)
        elif not base:
            targets.append(alias.name)
    return targets


def import_closure(root: str) -> tuple[set[str], list[tuple[str, int, str]]]:
    """Transitive first-party import closure, including function-local imports."""
    recorded: set[str] = set()
    edges: list[tuple[str, int, str]] = []
    visited: set[str] = set()
    queue = [root]
    while queue:
        name = queue.pop()
        if name in visited:
            continue
        visited.add(name)
        recorded.add(name)
        path = _module_file(name)
        if path is None:
            continue
        for parent in _parents(name):
            if parent not in visited:
                queue.append(parent)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for target in _import_targets(name, path, node):
                if not target:
                    continue
                edges.append((str(path), getattr(node, "lineno", 0), target))
                recorded.add(target)
                if _module_file(target) is not None and target not in visited:
                    queue.append(target)
    return recorded, edges


def _runtime_modules(statement: str) -> list[str]:
    proc = subprocess.run(
        [sys.executable, "-c", statement],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_t1_idempotent_create_only(tmp_path):
    inner = LocalStore(tmp_path / "store")
    store = RecordingStore(inner)
    digest = _arm(store, "note-a")
    text = _text("alpha")
    first = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor(text),
    )
    blob = inner.get_bytes_strict_bounded(first["key"], fulltext_store.FULLTEXT_MAX_BYTES)
    second = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor(text),
    )
    again = inner.get_bytes_strict_bounded(first["key"], fulltext_store.FULLTEXT_MAX_BYTES)
    assert first["state"] == "materialized"
    assert second["state"] == "already_current"
    assert blob == again
    assert sum(1 for _key, ok in store.conditional_puts if ok) == 1

    corpus = tmp_path / "missing.sqlite"
    _arm(store, "note-b")
    item = _item("note-b")
    materializer = functools.partial(fulltext_writer.materialize, extractor=_extractor(text))
    first_pass = _pending(store, [item], corpus, materializer=materializer)
    second_pass = _pending(store, [item], corpus, materializer=materializer)
    assert first_pass["materialized"] == 1
    assert second_pass["attempted"] == 0
    assert second_pass["materialized"] == 0


def test_t1_partial_listing_reaches_materializer_as_already_current(tmp_path, monkeypatch):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    text = _text("alpha")
    seeded = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor(text),
    )
    assert seeded["state"] == "materialized"
    monkeypatch.setattr(fulltext_store, "list_derivatives", lambda _store: frozenset())
    seen: list[str] = []

    def _materializer(store_arg, report_id, *, expected_pdf_sha256):
        seen.append(report_id)
        return fulltext_writer.materialize(
            store_arg, report_id, expected_pdf_sha256=expected_pdf_sha256, extractor=_extractor(text),
        )

    result = _pending(store, [_item("note-a")], tmp_path / "missing.sqlite", materializer=_materializer)
    assert seen == ["note-a"]
    assert result["already_current"] == 1
    assert result["materialized"] == 0


def test_t2_revision_replacement_hides_stale_and_keeps_v1(tmp_path):
    store = LocalStore(tmp_path / "store")
    pdf_v1 = _MINIMAL_PDF
    pdf_v2 = _MINIMAL_PDF + b"\n% v2\n"
    sha_v1 = _arm(store, "note-a", pdf_v1)
    text = _text("revision")
    first = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=sha_v1, extractor=_extractor(text),
    )
    assert first["state"] == "materialized"
    v1_key = first["key"]
    v1_blob = store.get_bytes(v1_key)

    sha_v2 = _sha(pdf_v2)
    store.put_bytes(f"research_vault/note-a.pdf", pdf_v2, "application/pdf")
    _put_receipt(store, "note-a", sha_v2)
    assert fulltext_store.load_extracted_text(store, "note-a", {}) is None

    corpus = tmp_path / "corpus.sqlite"
    _write_corpus(corpus, [("note-a", sha_v2)])
    passed = _pending(
        store, [_item("note-a")], corpus,
        materializer=functools.partial(fulltext_writer.materialize, extractor=_extractor(text)),
    )
    assert passed["materialized"] == 1
    loaded = fulltext_store.load_extracted_text(store, "note-a", {})
    assert loaded is not None
    assert loaded["source_pdf_sha256"] == sha_v2
    assert store.get_bytes(v1_key) == v1_blob
    assert fulltext_store.derivative_key("note-a", sha_v1) != fulltext_store.derivative_key("note-a", sha_v2)


def test_t2_revision_mismatch_writes_nothing(tmp_path):
    store = LocalStore(tmp_path / "store")
    pdf_v1 = _MINIMAL_PDF
    sha_v2 = _sha(pdf_v1 + b"\n% v2\n")
    _arm(store, "note-b", pdf_v1)
    before = set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX))
    result = fulltext_writer.materialize(
        store, "note-b", expected_pdf_sha256=sha_v2, extractor=_extractor(_text()),
    )
    assert result["state"] == "revision_mismatch"
    assert set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX)) == before


def test_t2_shaless_receipt_is_digest_unknown_without_pdf_read(tmp_path):
    inner = LocalStore(tmp_path / "store")
    store = RecordingStore(inner)
    _put_pdf(store, "note-c")
    _put_receipt(store, "note-c", None)
    assert fulltext_store.load_extracted_text(store, "note-c", {}) is None
    result = _pending(store, [_item("note-c")], tmp_path / "missing.sqlite")
    assert result["digest_unknown"] == 1
    assert result["attempted"] == 0
    assert store.pdf_reads == []


def test_t2_source_digest_follows_receipt_and_rejects_id_mismatch(tmp_path):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-d")
    assert fulltext_store.source_digest(store, "note-d") == digest
    _put_receipt(store, "note-d", digest, receipt_id="other-note")
    assert fulltext_store.source_digest(store, "note-d") is None


def test_t3_exact_tail_replay(tmp_path):
    pages = []
    for number in range(1, 121):
        page = f"第{number}页 研究报告 " + ("alpha beta 研究 gamma " * 30)
        if len(page) < 700:
            page = page + (" x" * (700 - len(page)))
        if number >= 119:
            page += " TAIL-SENTINEL 尾句 唯一标记"
        pages.append(page)
    text = "\f".join(pages)
    sentinel = "TAIL-SENTINEL 尾句 唯一标记"
    char_at = text.find(sentinel)
    byte_at = len(text[:char_at].encode("utf-8"))
    assert char_at > 60000
    assert byte_at > 60000

    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "tail-note")
    result = fulltext_writer.materialize(
        store, "tail-note", expected_pdf_sha256=digest, extractor=_extractor(text),
    )
    assert result["state"] == "materialized"
    record = fulltext_store.load_extracted_text(store, "tail-note", {})
    assert record is not None
    segments = fulltext.build_segments(
        dict(record),
        segmenter_version=fulltext.SEGMENTER_VERSION,
        max_bytes=SEGMENT_MAX_BYTES,
    )
    segment = next(row for row in segments if sentinel in row["text"])
    assert segment["start_byte"] > 60000
    replayed = fulltext.replay_segment(dict(record), segment)
    canonical = record["text"].encode("utf-8")[segment["start_byte"]:segment["end_byte"]].decode("utf-8")
    assert replayed == canonical
    assert isinstance(replayed, str)
    assert sentinel in replayed


def test_t4_no_text_layer_serves_no_text_layer(tmp_path):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "scan-note")
    result = fulltext_writer.materialize(
        store, "scan-note", expected_pdf_sha256=digest, extractor=lambda _pdf: "\f\f\f",
    )
    assert result["state"] == "no_text_layer"
    record = fulltext_store.load_extracted_text(store, "scan-note", {})
    assert record is not None
    assert record["text_layer_state"] == "none"
    assert record["text"] == ""

    item = _item("scan-note", "2026-10-06T00:00:00+00:00")
    service = _service(store, tmp_path / "corpus.sqlite", item)
    fetched = service.fetch(caller_context=_ctx(), report_id="scan-note", selectors={})
    assert fetched["ok"] is True
    assert fetched["coverage_state"] == "NO_TEXT_LAYER"
    assert fetched["coverage_state"] != "EXTRACTION_UNAVAILABLE"


def test_t5_cap_stops_after_one_attempt(tmp_path):
    store = LocalStore(tmp_path / "store")
    items = [
        _item("note-old", "2026-01-01T00:00:00Z"),
        _item("note-new", "2026-08-01T00:00:00Z"),
        _item("note-blank", ""),
    ]
    for item in items:
        _put_receipt(store, item["id"], "ab" * 32)
    seen: list[str] = []

    def _materializer(_store, report_id, *, expected_pdf_sha256):
        seen.append(report_id)
        return {"state": "materialized", "report_id": report_id}

    result = _pending(
        store, items, tmp_path / "missing.sqlite", cap=1, materializer=_materializer,
    )
    assert result["attempted"] == 1
    assert result["aborted"] == "cap"
    assert result["remaining"] == 2
    assert seen == ["note-new"]


def test_t5_budget_stops_with_work_left(tmp_path):
    store = LocalStore(tmp_path / "store")
    items = [_item(f"note-{index}", "2026-08-01T00:00:00Z") for index in range(3)]
    for item in items:
        _put_receipt(store, item["id"], "cd" * 32)

    class _Clock:
        def __init__(self):
            self.now = 0.0

        def __call__(self):
            current = self.now
            self.now += 100.0
            return current

    result = _pending(
        store, items, tmp_path / "missing.sqlite",
        budget_s=150,
        clock=_Clock(),
        materializer=lambda _store, report_id, *, expected_pdf_sha256: {"state": "materialized"},
    )
    assert result["aborted"] == "budget"
    assert result["remaining"] >= 1


def test_t5_run_wall_attempts_nothing(tmp_path):
    store = LocalStore(tmp_path / "store")
    items = [_item("note-a"), _item("note-b")]
    for item in items:
        _put_receipt(store, item["id"], "ef" * 32)
    result = _pending(
        store, items, tmp_path / "missing.sqlite",
        run_started=4000.0,
        clock=lambda: 5000.0,
        run_wall_s=600.0,
        materializer=lambda *_args, **_kwargs: {"state": "materialized"},
    )
    assert result["attempted"] == 0
    assert result["aborted"] == "budget"
    assert result["remaining"] == result["candidates"] == 2


def test_t5_tool_absent_reads_no_pdf(tmp_path):
    inner = LocalStore(tmp_path / "store")
    store = RecordingStore(inner)
    _put_pdf(store, "note-a")
    _put_receipt(store, "note-a", _sha(_MINIMAL_PDF))
    result = _pending(
        store, [_item("note-a")], tmp_path / "missing.sqlite",
        tool_available=lambda: False,
    )
    assert result["aborted"] == "tool_unavailable"
    assert result["attempted"] == 0
    assert store.pdf_reads == []


def test_t5_oversized_pdf_uses_vault_head_cap(tmp_path):
    inner = LocalStore(tmp_path / "store")
    store = OversizePdfStore(inner)
    digest = _arm(store, "note-a")
    result = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor(_text()),
    )
    assert result["state"] == "too_large"
    pdf_calls = [item for item in store.gets if str(item[0]).lower().endswith(".pdf")]
    assert pdf_calls
    assert pdf_calls[0][1] == vault_head.MAX_PDF_BYTES


def test_t5_oversized_record_writes_nothing(tmp_path, monkeypatch):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    before = set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX))
    monkeypatch.setattr(fulltext_store, "FULLTEXT_MAX_BYTES", 400)
    result = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor("short body " * 8),
    )
    assert result["state"] == "too_large"
    assert set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX)) == before


def test_t6_reader_contract(tmp_path, monkeypatch):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-y")
    text = _text("reader")
    missing = fulltext_store.load_extracted_text(store, "note-y", {"unused": True})
    assert missing is None

    key = fulltext_store.derivative_key("note-y", digest)
    store.put_bytes(key, b"{not json", "application/json")
    assert fulltext_store.load_extracted_text(store, "note-y", {}) is None

    store.put_bytes(key, b'{"schema":"not-the-schema"}', "application/json")
    assert fulltext_store.load_extracted_text(store, "note-y", {}) is None

    foreign = fulltext.build_extracted_text(
        report_id="note-x",
        source_pdf_sha256=digest,
        text=text,
        extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION,
        page_count=1,
        text_layer_state="full",
    )
    store.put_bytes(key, fulltext_store.encode_record(foreign), "application/json")
    assert fulltext_store.load_extracted_text(store, "note-y", {}) is None

    mismatched = fulltext.build_extracted_text(
        report_id="note-y",
        source_pdf_sha256="12" * 32,
        text=text,
        extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION,
        page_count=1,
        text_layer_state="full",
    )
    store.put_bytes(key, fulltext_store.encode_record(mismatched), "application/json")
    assert fulltext_store.load_extracted_text(store, "note-y", {}) is None

    valid = fulltext.build_extracted_text(
        report_id="note-y",
        source_pdf_sha256=digest,
        text=text,
        extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION,
        page_count=1,
        text_layer_state="full",
    )
    store.put_bytes(key, fulltext_store.encode_record(valid), "application/json")
    monkeypatch.setattr(fulltext_store, "FULLTEXT_MAX_BYTES", 8)
    assert fulltext_store.load_extracted_text(store, "note-y", {}) is None
    monkeypatch.undo()

    raising_receipt = RaisingStore(store, raise_on="any")
    assert fulltext_store.load_extracted_text(raising_receipt, "note-y", {}) is None
    assert len(raising_receipt.gets) <= 2
    assert all(not str(item).lower().endswith(".pdf") for item in raising_receipt.gets)

    raising_object = RaisingStore(store, raise_on="derivative")
    assert fulltext_store.load_extracted_text(raising_object, "note-y", {}) is None
    assert 1 <= len(raising_object.gets) <= 2
    assert all(not str(item).lower().endswith(".pdf") for item in raising_object.gets)

    bare = LocalStore(tmp_path / "bare")
    assert fulltext_store.load_extracted_text(bare, "note-y", {}) is None
    _put_receipt(bare, "note-y", digest, receipt_id="someone-else")
    assert fulltext_store.load_extracted_text(bare, "note-y", {}) is None
    _put_receipt(bare, "note-y", None)
    assert fulltext_store.load_extracted_text(bare, "note-y", {}) is None

    counting = RecordingStore(store)
    monkeypatch.setattr(fulltext_store, "FULLTEXT_MAX_BYTES", fulltext_store.FULLTEXT_MAX_BYTES)
    loaded = fulltext_store.load_extracted_text(counting, "note-y", {"ignored": 1})
    assert loaded is not None
    assert loaded["report_id"] == "note-y"
    assert len(counting.gets) <= 2
    assert counting.pdf_reads == []


def test_t7_read_service_fetch_evidence_and_status(tmp_path):
    store = LocalStore(tmp_path / "store")
    report_id = "desk-note"
    phrase = "HYPERSENTINEL"
    text = _text("institutional capacity") + f" {phrase} remains the quoted span."
    digest = _arm(store, report_id)
    materialized = fulltext_writer.materialize(
        store, report_id, expected_pdf_sha256=digest, extractor=_extractor(text),
    )
    assert materialized["state"] == "materialized"
    item = _item(report_id, "2026-10-06T08:00:00+00:00", title="Capacity Note")
    service = _service(store, tmp_path / "corpus.sqlite", item)

    fetched = service.fetch(caller_context=_ctx(), report_id=report_id, selectors={})
    assert fetched["coverage_state"] == "FULL_TEXT"
    assert fetched["segments"]

    evidence = service.find_evidence(
        caller_context=_ctx(),
        report_id=report_id,
        query=phrase,
        max_passages=3,
    )
    assert evidence["evidence_state"] == "FOUND"
    record = fulltext_store.load_extracted_text(store, report_id, item)
    assert record is not None
    canonical = record["text"].encode("utf-8")
    assert evidence["passages"]
    for passage in evidence["passages"]:
        assert passage["text"] == canonical[passage["start_byte"]:passage["end_byte"]].decode("utf-8")
        assert phrase in passage["text"]

    status = service.status(caller_context=_ctx())
    assert status["full_text_coverage"] > 0
    assert "FULL_TEXT_PARTIAL" not in status["source"]["known_degradation"]


def test_pins_receipt_extractor_and_key_shape():
    assert fulltext_store.RECEIPT_PREFIX == ingest_mod.PROCESSED_PREFIX
    assert fulltext_store.EXTRACTOR_NAME == vault_head.EXTRACTOR_NAME
    assert fulltext_store.EXTRACTOR_VERSION == vault_head.EXTRACTOR_VERSION
    samples = (
        ("a", "ab" * 32),
        ("bernstein-2026-07-21-dc", "0" * 64),
        ("note-9", "f" * 64),
    )
    for report_id, digest in samples:
        key = fulltext_store.derivative_key(report_id, digest)
        assert key.startswith("research_vault/fulltext/v1/")
        assert not key.lower().endswith(".pdf")
        assert "research_vault/intelligence/" not in key
        assert key == (
            f"research_vault/fulltext/v1/{report_id}/{digest}/{fulltext_store.DERIVATIVE_TAG}.json"
        )


def test_pins_derivative_tag_tracks_segmenter_and_extractor():
    current = _derivative_tag(
        fulltext.EXTRACTED_TEXT_SCHEMA,
        fulltext_store.EXTRACTOR_NAME,
        fulltext_store.EXTRACTOR_VERSION,
        fulltext.SEGMENTER_VERSION,
    )
    assert fulltext_store.DERIVATIVE_TAG == current
    assert current != _derivative_tag(
        fulltext.EXTRACTED_TEXT_SCHEMA,
        fulltext_store.EXTRACTOR_NAME,
        fulltext_store.EXTRACTOR_VERSION,
        "other-segmenter",
    )
    assert current != _derivative_tag(
        fulltext.EXTRACTED_TEXT_SCHEMA,
        fulltext_store.EXTRACTOR_NAME,
        "other-extractor",
        fulltext.SEGMENTER_VERSION,
    )


def _seed_inbox(store):
    store.put_bytes("research_inbox/rep1.pdf", _MINIMAL_PDF, "application/pdf")
    sidecar = {
        "schema": "research_vault.sidecar.v1",
        "title": "DC Pipeline",
        "institution": "Bernstein",
        "published_at": "2026-07-21T14:00:00Z",
        "summary_points": ["Only 33% credible"],
    }
    store.put_bytes(
        "research_inbox/rep1.json",
        json.dumps(sidecar).encode("utf-8"),
        "application/json",
    )


def test_ingest_run_materializes_derivative(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _pdf: _text("ingested body"))
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    store = LocalStore(tmp_path / "store")
    _seed_inbox(store)
    summary = ingest_mod.run(store, tmp_path / "corpus.sqlite")
    assert summary.get("catalog_published") is True
    assert summary.get("fulltext_materialized", 0) >= 1
    assert any(
        key.startswith(fulltext_store.FULLTEXT_PREFIX) and key.endswith(".json")
        for key in store.list_prefix(fulltext_store.FULLTEXT_PREFIX)
    )


def test_ingest_run_survives_writer_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _pdf: _text("ingested body"))
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("writer blew up")

    monkeypatch.setattr(fulltext_writer, "materialize_pending", _boom)
    store = LocalStore(tmp_path / "store")
    _seed_inbox(store)
    summary = ingest_mod.run(store, tmp_path / "corpus.sqlite")
    assert summary.get("catalog_published") is True
    assert "error" not in summary
    assert summary["fulltext_aborted"] == "internal_error"


def test_ingest_dry_run_skips_fulltext(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _pdf: _text("ingested body"))
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    store = LocalStore(tmp_path / "store")
    _seed_inbox(store)
    summary = ingest_mod.run(store, tmp_path / "corpus.sqlite", dry_run=True)
    assert not any(str(key).startswith("fulltext_") for key in summary)
    assert store.list_prefix(fulltext_store.FULLTEXT_PREFIX) == []


def test_fulltext_store_import_closure_excludes_producer_and_pdf_stack():
    recorded, edges = import_closure("engine.research_vault.fulltext_store")
    offenders = [
        f"{path}:{line} -> {module}"
        for path, line, module in edges
        if _is_forbidden(module)
    ]
    forbidden_names = sorted(name for name in recorded if _is_forbidden(name))
    assert not offenders, "forbidden import edges:\n" + "\n".join(offenders)
    assert not forbidden_names, forbidden_names
    assert "engine.research_vault.fulltext_writer" not in recorded

    modules = _runtime_modules(
        "import json, sys, engine.research_vault.fulltext_store; "
        "print(json.dumps(sorted(sys.modules)))"
    )
    runtime_offenders = [name for name in modules if _is_forbidden(name)]
    assert not runtime_offenders, runtime_offenders


def test_closure_walker_positive_control_finds_probe_from_ingest():
    recorded, _edges = import_closure("engine.research_vault.ingest")
    assert "engine.research_vault.probe" in recorded


def test_runtime_closure_positive_control_vault_head_loads_ingest():
    modules = _runtime_modules(
        "import json, sys, engine.research_intelligence.vault_head; "
        "print(json.dumps(sorted(sys.modules)))"
    )
    assert "engine.research_vault.ingest" in modules
