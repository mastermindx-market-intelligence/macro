"""Whitespace-only extracted text is a typed no-text layer (F3).

pdftotext on an image-only PDF emits one form feed per page. text_facts used
to stamp those rows text_layer='thin' (chars > 0) instead of the honest
'none', and _reextract_bodies never revisited them. Census run 37289367732
found marketdesk-irfsjldm8xi-9d962a and marketdesk-megf17hsiv1-847d35 in
that state.

No R2. LocalStore + a monkeypatched extractor, same idiom as the body
re-extraction section of tests/test_research_vault.py.
"""
from __future__ import annotations

import hashlib

import pytest

from engine.research_vault import corpus as corpus_mod
from engine.research_vault import fulltext
from engine.research_vault import ingest as ingest_mod
from engine.research_vault import probe as probe_mod
from engine.research_vault.r2_store import LocalStore
from tests.test_research_vault import (
    _MINIMAL_PDF,
    _REEXTRACTED_BODY,
    _row,
    _seed_frozen_row,
)

_FF = "\f\f"
_FFF = "\f\f\f"
_SOURCE_SHA = hashlib.sha256(b"synthetic-pdf-a").hexdigest()


def _extracted(*, text, state, pages=2):
    return fulltext.build_extracted_text(
        report_id="synthetic-report",
        source_pdf_sha256=_SOURCE_SHA,
        text=text,
        extractor_name="pdftotext",
        extractor_version="poppler-layout-v1",
        page_count=pages,
        text_layer_state=state,
    )


def _hand_artifact(text: str, state: str) -> dict:
    """A structurally valid artifact, including a matching text hash."""
    encoded = text.encode("utf-8")
    return {
        "schema": fulltext.EXTRACTED_TEXT_SCHEMA,
        "report_id": "synthetic-report",
        "source_pdf_sha256": _SOURCE_SHA,
        "extractor_name": "pdftotext",
        "extractor_version": "poppler-layout-v1",
        "extracted_text_sha256": hashlib.sha256(encoded).hexdigest(),
        "char_count": len(text),
        "byte_count": len(encoded),
        "page_count": 2,
        "page_boundaries": fulltext.page_boundaries(text),
        "text_layer_state": state,
        "computed_at": "",
        "text": text,
    }


# T1 — probe.text_facts
def test_t1_text_facts_whitespace_only_is_none():
    """Pin: form-feed-only and whitespace-only bodies are text_layer='none'."""
    form_feeds = probe_mod.text_facts(_FFF, 3)
    assert form_feeds["text_layer"] == "none"
    assert form_feeds["char_count"] == 3
    assert form_feeds["word_count"] == 0

    whitespace = probe_mod.text_facts(" \n\t", None)
    assert whitespace["text_layer"] == "none"
    assert whitespace["char_count"] == 3
    assert whitespace["word_count"] == 0

    assert probe_mod.text_facts("", 1)["text_layer"] == "none"
    assert probe_mod.text_facts(None, 1)["text_layer"] == "unavailable"
    assert probe_mod.text_facts("x" * 10, 1)["text_layer"] == "thin"
    assert probe_mod.text_facts("x" * 5000, 1)["text_layer"] == "full"


# T2 — fulltext.build_extracted_text
def test_t2_build_extracted_text_blank_requires_none():
    """Pin: whitespace-only text is blank and requires text_layer_state='none'."""
    artifact = _extracted(text=_FF, state="none")
    assert artifact["extracted_text_sha256"] == hashlib.sha256(
        _FF.encode("utf-8")
    ).hexdigest()
    assert artifact["text"] == _FF

    with pytest.raises(ValueError):
        _extracted(text=_FF, state="thin")

    with pytest.raises(ValueError):
        _extracted(text="abc", state="none")

    unavailable = _extracted(text=None, state="unavailable")
    assert unavailable["text"] == ""
    assert unavailable["text_layer_state"] == "unavailable"


# T3 — artifact validator
def test_t3_validator_accepts_form_feed_none_rejects_thin():
    """Pin: _validate_extracted_text emptiness is decided on text.strip()."""
    none_artifact = _hand_artifact(_FF, "none")
    assert fulltext._validate_extracted_text(none_artifact) == _FF.encode("utf-8")

    thin_artifact = _hand_artifact(_FF, "thin")
    with pytest.raises(ValueError):
        fulltext._validate_extracted_text(thin_artifact)


# T4 — blank-thin repair restamps 'none' and quiesces
def test_t4_blank_thin_repair_restamps_none_and_quiesces(tmp_path, monkeypatch):
    """Pin: a published blank-thin row is a candidate; restamping to 'none'
    drops it out of candidacy on the next pass."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _FFF)
    store = LocalStore(tmp_path / "store")
    conn = corpus_mod.open_db(tmp_path / "corpus.sqlite")
    _seed_frozen_row(store, conn, "blank-thin-scan", text_layer="thin", body=_FFF)

    first = ingest_mod._reextract_bodies(store, conn)
    assert first["checked"] == 1
    assert _row(conn, "blank-thin-scan")["text_layer"] == "none"

    second = ingest_mod._reextract_bodies(store, conn)
    assert second["checked"] == 0
    conn.close()


# T5 — blank-thin whose PDF now yields real text is filled
def test_t5_blank_thin_fills_real_body_and_is_searchable(tmp_path, monkeypatch):
    """Pin: a whitespace-only stored body is empty for the fill decision."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _REEXTRACTED_BODY)
    store = LocalStore(tmp_path / "store")
    conn = corpus_mod.open_db(tmp_path / "corpus.sqlite")
    _seed_frozen_row(store, conn, "blank-thin-now-full",
                     text_layer="thin", body=_FFF)

    out = ingest_mod._reextract_bodies(store, conn)
    assert out["bodies"] == 1
    row = _row(conn, "blank-thin-now-full")
    assert row["body"] == _REEXTRACTED_BODY
    assert row["text_layer"] == "full"
    hits = corpus_mod.search(conn, "hyperscaler")
    assert [h["id"] for h in hits] == ["blank-thin-now-full"]
    conn.close()


# T6 — a real thin body is not a candidate
def test_t6_real_thin_body_is_not_a_candidate(tmp_path, monkeypatch):
    """Pin: a 'thin' row holding real text is left byte-for-byte."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _REEXTRACTED_BODY)
    store = LocalStore(tmp_path / "store")
    conn = corpus_mod.open_db(tmp_path / "corpus.sqlite")
    original = "cover sheet labels only"
    _seed_frozen_row(store, conn, "real-thin", text_layer="thin", body=original)

    out = ingest_mod._reextract_bodies(store, conn)
    assert out["checked"] == 0
    row = _row(conn, "real-thin")
    assert row["body"] == original
    assert row["text_layer"] == "thin"
    conn.close()


# T7 — missing vault PDF leaves a blank-thin row untouched
def test_t7_blank_thin_missing_pdf_is_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _FFF)
    store = LocalStore(tmp_path / "store")
    conn = corpus_mod.open_db(tmp_path / "corpus.sqlite")
    _seed_frozen_row(store, conn, "blank-thin-no-pdf", text_layer="thin",
                     body=_FFF, with_pdf=False)

    out = ingest_mod._reextract_bodies(store, conn)
    assert out["pdf_missing"] == 1
    assert out["checked"] == 0
    row = _row(conn, "blank-thin-no-pdf")
    assert row["text_layer"] == "thin"
    assert row["body"] == _FFF
    conn.close()


# T8 — unavailable, then blank-thin, then NULL; cap=1
def test_t8_order_unavailable_then_blank_thin_then_null(tmp_path, monkeypatch):
    """Pin: CASE groups unavailable first, blank-thin second, NULL last."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _REEXTRACTED_BODY)
    store = LocalStore(tmp_path / "store")
    conn = corpus_mod.open_db(tmp_path / "corpus.sqlite")
    # Dates are adversarial: NULL is newest, unavailable is oldest. A
    # published_at-only order would pick the NULL row first.
    _seed_frozen_row(store, conn, "row-unavailable",
                     text_layer="unavailable", body="",
                     published_at="2026-07-01T09:00:00Z")
    _seed_frozen_row(store, conn, "row-blank-thin",
                     text_layer="thin", body=_FFF,
                     published_at="2026-07-15T09:00:00Z")
    _seed_frozen_row(store, conn, "row-null",
                     text_layer=None, body="",
                     published_at="2026-07-31T09:00:00Z")

    first = ingest_mod._reextract_bodies(store, conn, cap=1)
    assert first["checked"] == 1
    assert _row(conn, "row-unavailable")["text_layer"] == "full"
    assert _row(conn, "row-blank-thin")["text_layer"] == "thin"
    assert _row(conn, "row-null")["text_layer"] is None

    second = ingest_mod._reextract_bodies(store, conn, cap=1)
    assert second["checked"] == 1
    assert _row(conn, "row-blank-thin")["text_layer"] == "full"
    assert _row(conn, "row-null")["text_layer"] is None
    conn.close()
