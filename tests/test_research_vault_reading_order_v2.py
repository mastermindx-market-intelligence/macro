"""Discriminating tests: additive reading_order.v2 candidate + versioned plane.

Legacy v1 behavior, keys, defaults, timing fields and the serving import
closure must be unchanged; the v2 candidate is opt-in only, keys on its own
immutable derivative plane, and is never counted as v1 by the default pass.
"""
from __future__ import annotations

import ast
import functools
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from engine.research_intelligence import vault_head
from engine.research_vault import corpus as corpus_mod
from engine.research_vault import fulltext
from engine.research_vault import fulltext_store
from engine.research_vault import fulltext_writer
from engine.research_vault import ingest as ingest_mod
from engine.research_vault import dev_reading_order_qualify as qualify
from engine.research_vault.r2_store import LocalStore

REPO = Path(__file__).resolve().parents[1]

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n"
    b"%%EOF\n"
)

V1 = fulltext_store.EXTRACTOR_VERSION
V2 = fulltext_store.READING_ORDER_EXTRACTOR_VERSION

# Identity proof pins (preimage/postimage contract).
V1_TAG = "v1-05b88d4d1e4a6efa"
V2_TAG = "v1-6a7bb9118ebf1e05"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(label: str = "canonical research body") -> str:
    return (label + " ") * 40


def _extractor(text: str):
    return lambda _pdf: text


def _arm(store, report_id: str, pdf: bytes = MINIMAL_PDF) -> str:
    store.put_bytes(f"research_vault/{report_id}.pdf", pdf, "application/pdf")
    digest = _sha(pdf)
    store.put_bytes(
        fulltext_store.receipt_key(report_id),
        json.dumps({"id": report_id, "content_sha256": digest}).encode("utf-8"),
        "application/json",
    )
    return digest


def _item(report_id: str, published_at: str = "2026-10-01T00:00:00Z") -> dict:
    return {
        "id": report_id,
        "title": "Desk Note",
        "institution": "Goldman Sachs",
        "side": "sell",
        "published_at": published_at,
        "summary_points": ["catalog summary"],
    }


class CountingStore:
    """Delegates to an inner store and counts strict reads."""

    def __init__(self, inner):
        self.inner = inner
        self.gets: list[str] = []

    def get_bytes_strict_bounded(self, key, maximum_bytes=None, **kwargs):
        self.gets.append(str(key))
        return self.inner.get_bytes_strict_bounded(key, maximum_bytes, **kwargs)

    def get_bytes_strict(self, key):
        self.gets.append(str(key))
        return self.inner.get_bytes_strict(key)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def _put_versioned_record(store, report_id: str, digest: str, text: str, version: str) -> str:
    record = fulltext.build_extracted_text(
        report_id=report_id,
        source_pdf_sha256=digest,
        text=text,
        extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=version,
        page_count=1,
        text_layer_state="full",
    )
    key = fulltext_store.derivative_key(report_id, digest, extractor_version=version)
    store.put_bytes(key, fulltext_store.encode_record(record), "application/json")
    return key


def _write_corpus(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE documents (doc_id TEXT, content_sha256 TEXT)")
    conn.executemany("INSERT INTO documents VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# version vocabulary and key contract
# ---------------------------------------------------------------------------


def test_version_vocabulary_is_closed_and_pins_the_proof_tags():
    assert V1 == "research_vault.ingest.extract_pdf_text.v1"
    assert V2 == "research_vault.ingest.extract_pdf_text.reading_order.v2"
    assert fulltext.SUPPORTED_EXTRACTOR_VERSIONS == (V1, V2)
    assert fulltext_store.DERIVATIVE_TAG == V1_TAG
    assert fulltext_store.READING_ORDER_DERIVATIVE_TAG == V2_TAG
    assert fulltext.resolve_extractor_version(V1) == V1
    assert fulltext.resolve_extractor_version(V2) == V2
    with pytest.raises(ValueError):
        fulltext.resolve_extractor_version("research_vault.ingest.extract_pdf_text.v3")
    with pytest.raises(ValueError):
        fulltext.resolve_extractor_version("")


@pytest.mark.parametrize("version,layout", [(V1, True), (V2, False)])
def test_direct_head_default_runs_the_selected_extractor(tmp_path, monkeypatch, version, layout):
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        body = _text("layout body" if "-layout" in argv else "reading order body")
        return subprocess.CompletedProcess(argv, 0, stdout=body.encode(), stderr=b"")

    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    monkeypatch.setattr(ingest_mod.subprocess, "run", run)
    monkeypatch.setattr(vault_head.vault_probe, "probe", lambda pdf: {"pages": 1})
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    result = vault_head.read_canonical_text(
        store, "note-a", expected_pdf_sha256=digest, extractor_version=version
    )
    assert result["state"] == "ok"
    assert len(calls) == 1
    assert ("-layout" in calls[0]) is layout
    assert result["body"] == _text("layout body" if layout else "reading order body")
    assert result["extractor_version"] == version


def test_cli_short_writes_preserve_every_output_byte(tmp_path, monkeypatch):
    original_write = qualify.os.write

    def short_write(fd, blob):
        return original_write(fd, blob[:7])

    monkeypatch.setattr(qualify.os, "write", short_write)
    receipt, _, out = _qualify(tmp_path)
    assert _sha((out / "candidate_body.txt").read_bytes()) == receipt["candidate_text_sha256"]
    assert _sha((out / "canonical_record.json").read_bytes()) == receipt["candidate_record_sha256"]
    assert json.loads((out / "qualification_receipt.json").read_text()) == receipt
    assert len(json.loads((out / "segments.json").read_text())) == receipt["segment_count"]


def test_cli_zero_progress_write_cannot_report_qualification(tmp_path, monkeypatch):
    monkeypatch.setattr(qualify.os, "write", lambda fd, blob: 0)
    with pytest.raises(OSError):
        _qualify(tmp_path)
    assert not (tmp_path / "out" / "qualification_receipt.json").exists()


def test_distinct_v1_v2_derivative_keys_same_revision():
    digest = "ab" * 32
    k1 = fulltext_store.derivative_key("note-a", digest)
    k2 = fulltext_store.derivative_key("note-a", digest, extractor_version=V2)
    assert k1 != k2
    assert k1.endswith(f"/{V1_TAG}.json")
    assert k2.endswith(f"/{V2_TAG}.json")
    assert k1.startswith(fulltext_store.FULLTEXT_PREFIX)
    assert not k1.lower().endswith(".pdf") and not k2.lower().endswith(".pdf")


def test_unsupported_version_rejected_before_any_io(tmp_path):
    store = CountingStore(LocalStore(tmp_path / "store"))
    with pytest.raises(ValueError):
        fulltext_store.derivative_key("note-a", "ab" * 32, extractor_version="v9")
    with pytest.raises(ValueError):
        fulltext_store.derivative_key("note-a", "ab" * 32, extractor_version="")
    # Reader: rejection happens before the first store read.
    assert fulltext_store.load_extracted_text_version(
        store, "note-a", {}, extractor_version="v9"
    ) is None
    assert store.gets == []
    with pytest.raises(ValueError):
        fulltext_store.derivative_key("note-a", "ab" * 32, extractor_version="v9")
    # decode_record never raises: an unsupported version decodes nothing.
    assert fulltext_store.decode_record(
        b"{}", "note-a", "ab" * 32, extractor_version="v9"
    ) is None
    # Deep-read head: rejected before the reader is even resolved.
    class _NoReadStore:
        pass

    result = vault_head.read_canonical_text(
        _NoReadStore(), "note-a", extractor_version="v9"
    )
    assert result["state"] == "unsupported_extractor_version"
    # A supported version reaches the reader-resolution miss instead.
    result_ok = vault_head.read_canonical_text(_NoReadStore(), "note-a")
    assert result_ok["state"] == "strict_source_read_unavailable"


# ---------------------------------------------------------------------------
# strict reader closure in both directions
# ---------------------------------------------------------------------------


def test_readers_are_strictly_version_closed(tmp_path):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    v2_key = _put_versioned_record(store, "note-a", digest, _text("v2 body"), V2)
    v1_key = fulltext_store.derivative_key("note-a", digest)
    assert v1_key != v2_key

    # Legacy reader: closed to v2, and serves None while v1 is missing.
    assert fulltext_store.load_extracted_text(store, "note-a", {}) is None
    # Explicit v2 reader: closed to v1 (absent here), serves the v2 record.
    loaded = fulltext_store.load_extracted_text_version(
        store, "note-a", {}, extractor_version=V2
    )
    assert loaded is not None
    assert loaded["extractor_version"] == V2

    # Now place v1 as well: each reader serves exactly its own version.
    _put_versioned_record(store, "note-a", digest, _text("v1 body"), V1)
    legacy = fulltext_store.load_extracted_text(store, "note-a", {})
    assert legacy is not None and legacy["extractor_version"] == V1
    assert legacy["text"] == _text("v1 body")
    v2 = fulltext_store.load_extracted_text_version(
        store, "note-a", {}, extractor_version=V2
    )
    assert v2["text"] == _text("v2 body")
    # Cross reads stay closed even when both objects exist.
    assert fulltext_store.decode_record(
        fulltext_store.encode_record(legacy), "note-a", digest, extractor_version=V2
    ) is None
    assert fulltext_store.decode_record(
        fulltext_store.encode_record(v2), "note-a", digest, extractor_version=V1
    ) is None


def test_simultaneous_v1_v2_objects_are_immutable_and_idempotent(tmp_path):
    inner = LocalStore(tmp_path / "store")
    store = CountingStore(inner)
    digest = _arm(store, "note-a")
    text = _text("shared")
    first_v1 = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor(text)
    )
    first_v2 = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest,
        extractor=_extractor(text), extractor_version=V2,
    )
    assert first_v1["state"] == "materialized"
    assert first_v2["state"] == "materialized"
    assert first_v1["key"] != first_v2["key"]
    blob_v1 = inner.get_bytes_strict_bounded(first_v1["key"], fulltext_store.FULLTEXT_MAX_BYTES)
    blob_v2 = inner.get_bytes_strict_bounded(first_v2["key"], fulltext_store.FULLTEXT_MAX_BYTES)
    assert blob_v1 != blob_v2

    # Re-runs are create-only idempotent on BOTH planes.
    again_v1 = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor(text)
    )
    again_v2 = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest,
        extractor=_extractor(text), extractor_version=V2,
    )
    assert again_v1["state"] == "already_current"
    assert again_v2["state"] == "already_current"
    assert inner.get_bytes_strict_bounded(first_v1["key"], fulltext_store.FULLTEXT_MAX_BYTES) == blob_v1
    assert inner.get_bytes_strict_bounded(first_v2["key"], fulltext_store.FULLTEXT_MAX_BYTES) == blob_v2


def test_v2_create_conflict_requires_exact_existing_bytes(tmp_path):
    inner = LocalStore(tmp_path / "store")
    digest = _arm(inner, "note-a")
    record = fulltext.build_extracted_text(
        report_id="note-a", source_pdf_sha256=digest, text=_text("alpha"),
        extractor_name=fulltext_store.EXTRACTOR_NAME, extractor_version=V2,
        page_count=1, text_layer_state="full",
    )
    key = fulltext_store.derivative_key("note-a", digest, extractor_version=V2)
    # Occupied by well-formed but DIFFERENT deterministic bytes.
    other = fulltext.build_extracted_text(
        report_id="note-a", source_pdf_sha256=digest, text=_text("beta"),
        extractor_name=fulltext_store.EXTRACTOR_NAME, extractor_version=V2,
        page_count=1, text_layer_state="full",
    )
    inner.put_bytes(key, fulltext_store.encode_record(other), "application/json")
    result = fulltext_writer.materialize(
        inner, "note-a", expected_pdf_sha256=digest,
        extractor=_extractor(_text("alpha")), extractor_version=V2,
    )
    assert result["state"] == "existing_invalid"
    assert inner.get_bytes_strict_bounded(
        key, fulltext_store.FULLTEXT_MAX_BYTES
    ) == fulltext_store.encode_record(other)


# ---------------------------------------------------------------------------
# materialize stamps the ACTUAL chosen version
# ---------------------------------------------------------------------------


def test_materialize_stamps_actual_chosen_version(tmp_path):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    v1 = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor(_text("x"))
    )
    assert v1["state"] == "materialized"
    legacy = fulltext_store.load_extracted_text(store, "note-a", {})
    assert legacy["extractor_version"] == V1

    v2 = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest,
        extractor=_extractor(_text("x")), extractor_version=V2,
    )
    assert v2["state"] == "materialized"
    candidate = fulltext_store.load_extracted_text_version(
        store, "note-a", {}, extractor_version=V2
    )
    assert candidate is not None
    assert candidate["extractor_version"] == V2
    assert candidate["extractor_name"] == fulltext_store.EXTRACTOR_NAME


def test_materialize_v2_resolves_the_known_reading_order_extractor(tmp_path, monkeypatch):
    calls: list[str] = []

    def _fake_reading_order(pdf_bytes):
        calls.append("v2")
        return _text("reading order body")

    monkeypatch.setattr(
        ingest_mod, "extract_pdf_text_reading_order_v2", _fake_reading_order
    )
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    result = fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor_version=V2
    )
    assert result["state"] == "materialized"
    assert calls == ["v2"]
    record = fulltext_store.load_extracted_text_version(
        store, "note-a", {}, extractor_version=V2
    )
    assert record is not None and record["text"] == _text("reading order body")


def test_materialize_v2_sha_mismatch_writes_nothing(tmp_path):
    store = LocalStore(tmp_path / "store")
    _arm(store, "note-b")
    before = set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX))
    result = fulltext_writer.materialize(
        store, "note-b", expected_pdf_sha256="cd" * 32,
        extractor=_extractor(_text()), extractor_version=V2,
    )
    assert result["state"] == "revision_mismatch"
    assert set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX)) == before


def test_materialize_v2_no_text_layer_stamps_none_on_its_own_key(tmp_path):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "scan-note")
    result = fulltext_writer.materialize(
        store, "scan-note", expected_pdf_sha256=digest,
        extractor=lambda _pdf: "\f\f\f", extractor_version=V2,
    )
    assert result["state"] == "no_text_layer"
    record = fulltext_store.load_extracted_text_version(
        store, "scan-note", {}, extractor_version=V2
    )
    assert record is not None
    assert record["text_layer_state"] == "none"
    assert record["text"] == ""
    assert record["extractor_version"] == V2
    # The v1 plane is untouched.
    assert fulltext_store.load_extracted_text(store, "scan-note", {}) is None


# ---------------------------------------------------------------------------
# segments: exact replay and byte-faithful form feeds on the v2 record
# ---------------------------------------------------------------------------


def test_v2_segments_replay_exactly_with_form_feeds(tmp_path):
    pages = [f"page {n} " + ("alpha beta gamma " * 20) for n in range(1, 8)]
    text = "\f".join(pages) + "\f"
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "paged-note")
    result = fulltext_writer.materialize(
        store, "paged-note", expected_pdf_sha256=digest,
        extractor=_extractor(text), extractor_version=V2,
    )
    assert result["state"] == "materialized"
    record = fulltext_store.load_extracted_text_version(
        store, "paged-note", {}, extractor_version=V2
    )
    assert record is not None
    # Form feeds retained byte-for-byte; boundaries match the raw separators.
    assert record["text"].encode("utf-8") == text.encode("utf-8")
    assert record["page_boundaries"] == fulltext.page_boundaries(text)
    segments = fulltext.build_segments(
        dict(record), segmenter_version=fulltext.SEGMENTER_VERSION, max_bytes=512
    )
    assert segments
    canonical = record["text"].encode("utf-8")
    for segment in segments:
        replayed = fulltext.replay_segment(dict(record), segment)
        assert replayed == canonical[segment["start_byte"]:segment["end_byte"]].decode("utf-8")
        assert replayed == segment["text"]


# ---------------------------------------------------------------------------
# materialize_pending: default never opts in and never counts v2 as v1
# ---------------------------------------------------------------------------


def _pending(store, items, corpus, **kwargs):
    kwargs.setdefault("tool_available", lambda: True)
    kwargs.setdefault("run_started", 0.0)
    kwargs.setdefault("clock", lambda: 0.0)
    return fulltext_writer.materialize_pending(
        store, {"items": list(items)}, corpus, **kwargs
    )


def test_pending_default_materializes_missing_v1_even_when_v2_exists(tmp_path):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    # Only the v2 object exists for this exact revision.
    _put_versioned_record(store, "note-a", digest, _text("v2 body"), V2)
    v2_key = fulltext_store.derivative_key("note-a", digest, extractor_version=V2)
    v2_blob = store.get_bytes(v2_key)
    corpus = tmp_path / "corpus.sqlite"
    _write_corpus(corpus, [("note-a", digest)])

    out = _pending(
        store, [_item("note-a")], corpus,
        materializer=functools.partial(
            fulltext_writer.materialize, extractor=_extractor(_text("v1 body"))
        ),
    )
    # v2 is NOT counted as current: the default pass still owes v1.
    assert out["already_current"] == 0
    assert out["materialized"] == 1
    v1_key = fulltext_store.derivative_key("note-a", digest)
    assert v1_key in set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX))
    legacy = fulltext_store.load_extracted_text(store, "note-a", {})
    assert legacy is not None and legacy["extractor_version"] == V1
    # The v2 object is byte-identical afterwards (immutable, untouched).
    assert store.get_bytes(v2_key) == v2_blob


def test_pending_default_stays_default_when_v1_exists(tmp_path):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    text = _text("v1 body")
    assert fulltext_writer.materialize(
        store, "note-a", expected_pdf_sha256=digest, extractor=_extractor(text)
    )["state"] == "materialized"
    corpus = tmp_path / "corpus.sqlite"
    _write_corpus(corpus, [("note-a", digest)])
    # The revision is current on the v1 plane, so the default pass opts into
    # nothing: no attempt, and no v2 object is ever created.
    out = _pending(store, [_item("note-a")], corpus)
    assert out["candidates"] == 0
    assert out["attempted"] == 0
    assert fulltext_store.derivative_key("note-a", digest, extractor_version=V2) \
        not in set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX))

    # With a partially-visible listing the item is retried as class A and the
    # create-only v1 write is idempotent (already_current), never a v2 write.
    import pytest

    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(fulltext_store, "list_derivatives", lambda _s: frozenset())
        out2 = _pending(
            store, [_item("note-a")], corpus,
            materializer=functools.partial(
                fulltext_writer.materialize, extractor=_extractor(text)
            ),
        )
    finally:
        monkey.undo()
    assert out2["attempted"] == 1
    assert out2["already_current"] == 1
    assert out2["materialized"] == 0
    assert fulltext_store.derivative_key("note-a", digest, extractor_version=V2) \
        not in set(store.list_prefix(fulltext_store.FULLTEXT_PREFIX))


# ---------------------------------------------------------------------------
# the incumbent v1 extractor keeps its exact subprocess shape
# ---------------------------------------------------------------------------


def _stub_pdftotext(monkeypatch):
    """Stub ingest.subprocess.run; returns the argv lists it was called with."""
    calls: list[list[str]] = []

    class _Result:
        returncode = 0
        stderr = b""
        stdout = b"stubbed body\n"

    def _run(argv, **kwargs):
        calls.append(list(argv))
        return _Result()

    monkeypatch.setattr(ingest_mod.subprocess, "run", _run)
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    return calls


def test_v1_subprocess_shape_is_unchanged_v2_omits_layout(tmp_path, monkeypatch):
    calls = _stub_pdftotext(monkeypatch)
    pdf = MINIMAL_PDF + b"% argv-probe\n"
    assert ingest_mod.extract_pdf_text(pdf) == "stubbed body\n"
    assert ingest_mod.extract_pdf_text_reading_order_v2(pdf) == "stubbed body\n"
    assert len(calls) == 2
    v1_argv, v2_argv = calls
    # v1 keeps the exact incumbent command: pdftotext -layout <tmp> -
    assert v1_argv[0] == "pdftotext" and v1_argv[1] == "-layout" and v1_argv[3] == "-"
    assert v1_argv[2].endswith(".pdf")
    # v2 is the same idiom minus the -layout flag: pdftotext <tmp> -
    assert v2_argv == ["pdftotext", v2_argv[1], "-"]
    assert v2_argv[1].endswith(".pdf")
    assert "-layout" not in v2_argv


def test_ingest_module_exports_v1_unchanged_and_v2_candidate():
    assert ingest_mod.READING_ORDER_EXTRACTOR_VERSION == V2
    assert ingest_mod.extract_pdf_text.__doc__.startswith(
        "Extract text from PDF bytes using ``pdftotext -layout``."
    )
    assert ingest_mod.extract_pdf_text_reading_order_v2.__doc__.startswith(
        "Extract text with pdftotext's DEFAULT reading order"
    )


# ---------------------------------------------------------------------------
# read_canonical_text binds the requested version even for an injected extractor
# ---------------------------------------------------------------------------


def test_read_canonical_text_binds_requested_version_metadata(tmp_path):
    store = LocalStore(tmp_path / "store")
    digest = _arm(store, "note-a")
    result_v2 = vault_head.read_canonical_text(
        store, "note-a", extractor=_extractor(_text("bound")),
        expected_pdf_sha256=digest, extractor_version=V2,
    )
    assert result_v2["state"] == "ok"
    assert result_v2["extractor_version"] == V2
    assert result_v2["extractor_name"] == fulltext_store.EXTRACTOR_NAME
    result_v1 = vault_head.read_canonical_text(
        store, "note-a", extractor=_extractor(_text("bound")),
        expected_pdf_sha256=digest,
    )
    assert result_v1["extractor_version"] == V1
    # no_text_layer carries the chosen version too.
    scan = vault_head.read_canonical_text(
        store, "note-a", extractor=lambda _pdf: "\f\f",
        expected_pdf_sha256=digest, extractor_version=V2,
    )
    assert scan["state"] == "no_text_layer"
    assert scan["extractor_version"] == V2


# ---------------------------------------------------------------------------
# DEVELOPMENT-ONLY qualification CLI
# ---------------------------------------------------------------------------


def _qualify(tmp_path, *, development_only=True, report_id="note-a",
             source_sha=None, legacy_sha=None, out_name="out",
             layout_text=_text("layout body"), candidate_text=_text("candidate body"),
             pdf=MINIMAL_PDF):
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(pdf)
    kwargs = dict(
        development_only=development_only,
        pdf_path=str(pdf_path),
        report_id=report_id,
        source_sha256=source_sha if source_sha is not None else _sha(pdf),
        legacy_body_sha256=legacy_sha if legacy_sha is not None
        else _sha(layout_text.encode("utf-8")),
        out_dir=str(tmp_path / out_name),
        extract_layout=lambda _pdf: layout_text,
        extract_reading_order=lambda _pdf: candidate_text,
    )
    receipt = qualify.run_qualification(**kwargs)
    return receipt, pdf_path, Path(kwargs["out_dir"])


def test_cli_success_writes_exact_artifacts_and_never_mutates_input(tmp_path):
    before = (MINIMAL_PDF, MINIMAL_PDF)
    receipt, pdf_path, out = _qualify(tmp_path)
    # Input untouched: same bytes, same mtime_ns.
    assert pdf_path.read_bytes() == before[0]
    stat_before = pdf_path.stat()
    assert (stat_before.st_size, stat_before.st_mtime_ns) == (
        pdf_path.stat().st_size, pdf_path.stat().st_mtime_ns
    )

    body = (out / "candidate_body.txt").read_bytes()
    record_blob = (out / "canonical_record.json").read_bytes()
    segments_blob = (out / "segments.json").read_bytes()
    receipt_blob = (out / "qualification_receipt.json").read_bytes()
    assert body == _text("candidate body").encode("utf-8")
    assert _sha(body) == receipt["candidate_text_sha256"]
    assert _sha(record_blob) == receipt["candidate_record_sha256"]
    record = json.loads(record_blob)
    assert record["extractor_version"] == V2
    assert record["schema"] == fulltext.EXTRACTED_TEXT_SCHEMA
    assert record["source_pdf_sha256"] == _sha(MINIMAL_PDF)
    segments = json.loads(segments_blob)
    assert segments == fulltext.build_segments(
        record, segmenter_version=fulltext.SEGMENTER_VERSION, max_bytes=4000
    )
    assert receipt["all_segments_exact_replay"] is True
    assert receipt["legacy_body_verified"] is True
    assert receipt["distinct_derivative_keys"] is True
    assert receipt["model_calls"] == 0 and receipt["store_writes"] == 0
    assert receipt["candidate_status"] == "DEVELOPMENT_ONLY_NOT_ADOPTED"
    assert receipt["candidate_derivative_key"] == fulltext_store.derivative_key(
        "note-a", _sha(MINIMAL_PDF), extractor_version=V2
    )
    # All outputs are regular, owner-private files.
    for path in out.iterdir():
        assert path.is_file() and not path.is_symlink()
        assert path.stat().st_mode & 0o777 == 0o600
    assert receipt_blob  # nonempty


def test_cli_refuses_without_development_only(tmp_path):
    with pytest.raises(qualify.QualificationRefusal) as exc:
        _qualify(tmp_path, development_only=False)
    assert "--development-only" in exc.value.reason
    assert not (tmp_path / "out").exists()


def test_cli_refuses_bad_pdf_hash_before_extraction(tmp_path):
    layout_calls: list[str] = []

    def _layout(_pdf):
        layout_calls.append("called")
        return _text("layout body")

    pdf = MINIMAL_PDF
    with pytest.raises(qualify.QualificationRefusal) as exc:
        qualify.run_qualification(
            development_only=True,
            pdf_path=str(_write_pdf(tmp_path, pdf)),
            report_id="note-a",
            source_sha256="ff" * 32,
            legacy_body_sha256=_sha(_text("layout body").encode("utf-8")),
            out_dir=str(tmp_path / "out"),
            extract_layout=_layout,
            extract_reading_order=lambda _pdf: _text("candidate body"),
        )
    assert "source sha mismatch" in exc.value.reason
    assert layout_calls == []  # refused BEFORE any extraction
    assert not (tmp_path / "out").exists()


def _write_pdf(tmp_path, pdf: bytes) -> Path:
    path = tmp_path / f"in-{_sha(pdf)[:8]}.pdf"
    path.write_bytes(pdf)
    return path


def test_cli_refuses_bad_legacy_body_hash_before_candidate_extraction(tmp_path):
    order: list[str] = []

    def _layout(_pdf):
        order.append("layout")
        return _text("layout body")

    def _candidate(_pdf):
        order.append("candidate")
        return _text("candidate body")

    pdf = MINIMAL_PDF
    with pytest.raises(qualify.QualificationRefusal) as exc:
        qualify.run_qualification(
            development_only=True,
            pdf_path=str(_write_pdf(tmp_path, pdf)),
            report_id="note-a",
            source_sha256=_sha(pdf),
            legacy_body_sha256=_sha(b"stale body"),
            out_dir=str(tmp_path / "out"),
            extract_layout=_layout,
            extract_reading_order=_candidate,
        )
    assert "legacy body sha mismatch" in exc.value.reason
    assert order == ["layout"]  # candidate extraction never ran
    assert not (tmp_path / "out").exists()


def test_cli_refuses_occupied_or_existing_output(tmp_path):
    occupied = tmp_path / "out"
    occupied.mkdir()
    (occupied / "stale.txt").write_text("x")
    with pytest.raises(qualify.QualificationRefusal) as exc:
        _qualify(tmp_path, out_name="out")
    assert "already exists" in exc.value.reason
    assert (occupied / "stale.txt").read_text() == "x"
    with pytest.raises(qualify.QualificationRefusal):
        _qualify(tmp_path, out_name="nested/missing")  # parent absent
    assert not (tmp_path / "nested").exists()


def test_cli_refuses_bad_report_id_and_bad_hash_inputs(tmp_path):
    with pytest.raises(qualify.QualificationRefusal):
        _qualify(tmp_path, report_id="Not A Slug")
    with pytest.raises(qualify.QualificationRefusal):
        _qualify(tmp_path, source_sha="ZZ" * 32)
    with pytest.raises(qualify.QualificationRefusal):
        _qualify(tmp_path, legacy_sha="short")
    candidates = list(tmp_path.glob("out*"))
    assert candidates == []


def test_cli_main_refusal_exit_codes(tmp_path, capsys):
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(MINIMAL_PDF)
    base = [
        "--pdf", str(pdf), "--report-id", "note-a",
        "--source-sha256", _sha(MINIMAL_PDF),
        "--legacy-body-sha256", _sha(_text("layout body").encode("utf-8")),
        "--out", str(tmp_path / "out"),
    ]
    assert qualify.main(base) == 2  # missing --development-only
    assert "development-only" in capsys.readouterr().err
    assert qualify.main(["--development-only"] + base[:-2] + ["--out", str(tmp_path / "o2")]) == 2
    assert not (tmp_path / "o2").exists()
    assert capsys.readouterr().err


def test_cli_unavailable_extractor_refuses_without_output(tmp_path):
    pdf = MINIMAL_PDF
    with pytest.raises(qualify.QualificationRefusal) as exc:
        qualify.run_qualification(
            development_only=True,
            pdf_path=str(_write_pdf(tmp_path, pdf)),
            report_id="note-a",
            source_sha256=_sha(pdf),
            legacy_body_sha256=_sha(_text("layout body").encode("utf-8")),
            out_dir=str(tmp_path / "out"),
            extract_layout=lambda _pdf: None,
            extract_reading_order=lambda _pdf: _text("candidate body"),
        )
    assert "legacy body cannot be verified" in exc.value.reason
    assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------------------
# relation-prompt guidance (prompt contract only; no new verifier)
# ---------------------------------------------------------------------------


def _analysis(claims=1, **overrides):
    value = {
        "thesis": {
            "summary": "The desk prefers duration on inflation surprises.",
            "direction": "neutral",
            "mechanism": [],
            "conviction": "",
            "support_claim_indices": [0],
        },
        "belief_delta": {"statement": "", "support_claim_indices": []},
        "consensus_relation": {"statement": "", "support_claim_indices": []},
    }
    value.update(overrides)
    return value


def test_relation_prompt_carries_direct_evidence_guidance():
    from engine.research_intelligence import selection

    prompt = selection.SELECTOR_SYSTEM_PROMPT
    # belief_delta: explicit source-reported change only, both sides supported.
    assert "ONLY an explicit source-reported prior-to-current view change" in prompt
    assert "cite selected claims supporting every side" in prompt
    assert "never invent a previous belief" in prompt
    assert "unstated baseline" in prompt
    # consensus_relation: both attributed positions at the same metric/scope/horizon.
    assert "same metric, scope, and horizon" in prompt
    assert "return an empty statement and []" in prompt
    # Modality preserved; support is not entailment; selector version unchanged.
    assert "perhaps, if, could, scenario" in prompt
    assert "NOT proof of entailment" in prompt
    assert selection.SELECTOR_VERSION == "mastermind.research_intelligence.selector.v3"
    # No third prompt-only original-body replay and no new lexical verifier:
    # the module still exposes exactly the incumbent public analysis validators.
    public = {name for name in vars(selection) if not name.startswith("_")}
    assert "verify_relation" not in public
    assert "entails" not in public


def test_relation_parser_accepts_abstention_and_rejects_malformed_support():
    from engine.research_intelligence.selection import _validate_selector_analysis

    # Empty abstaining relations remain canonical.
    _validate_selector_analysis(_analysis(), 1)
    # Supported relations with valid integer positions remain parseable.
    _validate_selector_analysis(
        _analysis(
            belief_delta={"statement": "The desk moved from easing to neutral.", "support_claim_indices": [0]},
            consensus_relation={"statement": "The author is above consensus.", "support_claim_indices": [0]},
        ),
        1,
    )
    # Malformed relation OBJECT shapes are raw-transport rejections.
    with pytest.raises(ValueError):
        _validate_selector_analysis(
            _analysis(consensus_relation={"statement": "x", "support_claim_indices": [0], "verdict": "agree"}),
            1,
        )
    with pytest.raises(ValueError):
        _validate_selector_analysis(
            _analysis(belief_delta={"statement": 5, "support_claim_indices": [0]}),
            1,
        )
    # Malformed relation SUPPORT is deliberately NOT a raw-transport rejection:
    # the unchanged canonical all-support law removes the whole assertion later.
    # The prompt-level guidance therefore adds no new verifier here — enforcement
    # is prompt guidance plus actual-result adjudication, exactly as scoped.
    _validate_selector_analysis(
        _analysis(consensus_relation={"statement": "above consensus", "support_claim_indices": [7]}),
        1,
    )
    _validate_selector_analysis(
        _analysis(belief_delta={"statement": "shifted", "support_claim_indices": ["0"]}),
        1,
    )


# ---------------------------------------------------------------------------
# serving import closure of the reader stays stdlib + corpus + fulltext
# ---------------------------------------------------------------------------


def test_fulltext_store_closure_has_no_ingest_or_pdf_stack():
    sys.path.insert(0, str(REPO))
    recorded: set[str] = set()
    root = fulltext_store
    assert root.__name__ == "engine.research_vault.fulltext_store"
    # Static: no ingest/probe/vault_head/pdf import edges in the module source.
    source = Path(root.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            recorded.add(name)
    forbidden = {
        "engine.research_vault.ingest", "engine.research_vault.probe",
        "engine.research_intelligence.vault_head", "engine.press",
        "pypdf", "PyPDF2", "pdfminer", "fitz", "pymupdf", "pdfplumber",
    }
    assert not (recorded & forbidden)
    runtime = subprocess.run(
        [sys.executable, "-c",
         "import json, sys, engine.research_vault.fulltext_store; "
         "print(json.dumps(sorted(sys.modules)))"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    )
    modules = set(json.loads(runtime.stdout))
    assert not (modules & forbidden)
