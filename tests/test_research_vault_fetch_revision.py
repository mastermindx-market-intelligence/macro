"""Canonical paging identity with the actual read service and Brain adapter."""
from __future__ import annotations

import copy
import hashlib
import runpy
from pathlib import Path

import pytest

from engine.neuralweb import brain_market_intel as bmi
from engine.research_vault import fulltext, read_service
from engine.research_vault.read_adapters import BrainResearchAdapter

# Incumbent synthetic fixture helpers; never a real store or private report.
HELPERS = runpy.run_path(str(Path(__file__).with_name("test_research_vault_read_service.py")))
RID = "paged-revision-fixture"
TEXT = ("旧" * 1000 + "\f") * 12


def _record(text=TEXT, *, pdf_sha="a" * 64, extractor_version="poppler-layout-v1"):
    return fulltext.build_extracted_text(
        report_id=RID, source_pdf_sha256=pdf_sha, text=text,
        extractor_name="pdftotext", extractor_version=extractor_version,
        page_count=max(1, text.count("\f")), text_layer_state="full",
    )


def _setup(tmp_path, monkeypatch, *, text=TEXT, correction=None, mutate=None):
    current = {RID: _record(text)}
    svc, _, loader, digest, *_ = HELPERS["_service"](
        tmp_path, items=[HELPERS["_item"](RID, "Paging fixture", HELPERS["NOW"].isoformat())],
        extracted=current, digest=lambda rid: current[rid]["source_pdf_sha256"],
    )
    adapter = BrainResearchAdapter(svc)

    class Wrapper:
        def __init__(self):
            self.calls = 0
            self.pages = []

        def call(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2 and correction is not None:
                current[RID] = correction
            result = copy.deepcopy(adapter.call(*args, **kwargs))
            if mutate is not None:
                mutate(result["result"], self.calls)
            self.pages.append(result["result"])
            return result

    wrapper = Wrapper()
    monkeypatch.setattr(bmi, "_brain_research_adapter", lambda: wrapper)
    return wrapper, svc, loader, digest


def _load():
    return bmi._load_corpus_document(RID, principal_id="synthetic-principal")


def test_same_length_correction_discards_every_old_and_new_byte(tmp_path, monkeypatch):
    wrapper, *_ = _setup(tmp_path, monkeypatch, correction=_record(TEXT.replace("旧", "新"), pdf_sha="b" * 64))
    assert _load() is None
    assert wrapper.calls == 2
    assert all(page["coverage_state"] == "FULL_TEXT" for page in wrapper.pages)


def test_same_text_corrected_pdf_is_a_different_revision(tmp_path, monkeypatch):
    wrapper, *_ = _setup(tmp_path, monkeypatch, correction=_record(TEXT, pdf_sha="b" * 64))
    assert _load() is None
    assert wrapper.calls == 2


def test_uniform_utf8_whole_body_and_one_loader_per_fetch(tmp_path, monkeypatch):
    wrapper, _, loader, digest = _setup(tmp_path, monkeypatch)
    doc = _load()
    assert doc["body"] == TEXT
    assert wrapper.calls == 3
    assert loader.calls == digest.calls == wrapper.calls
    identity = wrapper.pages[0]["text_revision"]
    assert identity == wrapper.pages[-1]["text_revision"]
    assert identity["char_count"] == len(TEXT)
    assert identity["byte_count"] == len(TEXT.encode("utf-8"))
    assert identity["extracted_text_sha256"] == hashlib.sha256(TEXT.encode()).hexdigest()


def test_bounded_prefix_preserves_coherent_revision_without_fullbody_claim(tmp_path, monkeypatch):
    text = ("旧" * 1000 + "\f") * 20
    wrapper, *_ = _setup(tmp_path, monkeypatch, text=text)
    doc = _load()
    assert text.startswith(doc["body"])
    assert len(doc["body"]) > bmi.REPORT_BODY_MAX_CHARS
    assert len(doc["body"]) < len(text)
    assert wrapper.calls == 3
    assert "full_body_hash_validated" not in doc


@pytest.mark.parametrize("key,value", [
    ("extractor_name", "other"), ("extractor_version", "other-v2"),
    ("segmenter_version", "other-v2"), ("segment_max_bytes", 3999),
    ("source_pdf_sha256", "c" * 64), ("extracted_text_sha256", "c" * 64),
    ("char_count", len(TEXT) + 1), ("byte_count", len(TEXT.encode()) + 1),
])
def test_every_revision_member_must_agree_across_pages(tmp_path, monkeypatch, key, value):
    def mutate(result, call):
        if call == 2:
            result["text_revision"][key] = value
    wrapper, *_ = _setup(tmp_path, monkeypatch, mutate=mutate)
    assert _load() is None
    assert wrapper.calls == 2


@pytest.mark.parametrize("key,value", [
    ("schema", "unknown"), ("source_pdf_sha256", "A" * 64),
    ("extracted_text_sha256", None), ("extractor_name", ""),
    ("extractor_version", 4), ("segmenter_version", " "),
    ("segment_max_bytes", True), ("char_count", False), ("byte_count", -1),
])
def test_malformed_revision_never_exposes_partial_body(tmp_path, monkeypatch, key, value):
    def mutate(result, _call):
        result["text_revision"][key] = value
    _setup(tmp_path, monkeypatch, mutate=mutate)
    assert _load() is None


@pytest.mark.parametrize("replacement", [None, {}, "revision"])
def test_missing_or_partial_identity_fails_closed(tmp_path, monkeypatch, replacement):
    def mutate(result, _call):
        result["text_revision"] = replacement
    _setup(tmp_path, monkeypatch, mutate=mutate)
    assert _load() is None


@pytest.mark.parametrize("key,value", [
    ("report_id", "other-report"), ("coverage_state", "PREFIX_ONLY_LEGACY"),
    ("text_layer_state", "thin"), ("segment_count_total", 100),
    ("segment_count_total", True), ("available", False), ("ok", False),
])
def test_envelope_drift_discards_body(tmp_path, monkeypatch, key, value):
    def mutate(result, call):
        if call == 2:
            result[key] = value
    _setup(tmp_path, monkeypatch, mutate=mutate)
    assert _load() is None


@pytest.mark.parametrize("key,value", [
    ("segment_index", True), ("segment_index", 2), ("start_byte", 1),
    ("start_byte", False), ("end_byte", 1001), ("end_byte", True),
    ("text", ""),
])
def test_bad_segment_indices_or_utf8_spans_discard_body(tmp_path, monkeypatch, key, value):
    def mutate(result, _call):
        result["segments"][0][key] = value
    _setup(tmp_path, monkeypatch, mutate=mutate)
    assert _load() is None


def test_second_page_gap_fails(tmp_path, monkeypatch):
    def gap(result, call):
        if call == 2:
            result["segments"][0]["start_byte"] += 1
    _setup(tmp_path, monkeypatch, mutate=gap)
    assert _load() is None


@pytest.mark.parametrize("key,value", [
    ("extracted_text_sha256", "f" * 64), ("char_count", len(TEXT) + 1),
    ("byte_count", len(TEXT.encode()) + 1),
])
def test_uniform_but_false_complete_body_identity_is_rejected(tmp_path, monkeypatch, key, value):
    def mutate(result, _call):
        result["text_revision"][key] = value
    _setup(tmp_path, monkeypatch, mutate=mutate)
    assert _load() is None


def test_unqualified_fetch_has_null_revision_and_no_segments(tmp_path, monkeypatch):
    _, svc, *_ = _setup(tmp_path, monkeypatch)
    svc._source_digest_reader = None
    result = svc.fetch(caller_context=HELPERS["_ctx"](), report_id=RID, selectors={})
    assert result["coverage_state"] == "EXTRACTION_UNAVAILABLE"
    assert result["text_revision"] is None
    assert result["segments"] == []


def test_premature_empty_page_discards_collected_prefix(tmp_path, monkeypatch):
    def mutate(result, call):
        if call == 2:
            result["segments"] = []
    _setup(tmp_path, monkeypatch, mutate=mutate)
    assert _load() is None


def test_bad_later_segment_after_prefix_cap_also_discards_body(tmp_path, monkeypatch):
    text = ("旧" * 1000 + "\f") * 20
    def mutate(result, call):
        if call == 3:
            result["segments"][-1]["end_byte"] += 1
    _setup(tmp_path, monkeypatch, text=text, mutate=mutate)
    assert _load() is None


def test_actual_record_extractor_revision_change_fails(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, correction=_record(TEXT, extractor_version="corrected-extractor-v2"))
    assert _load() is None


def test_actual_service_segmentation_policy_change_fails(tmp_path, monkeypatch):
    _, svc, *_ = _setup(tmp_path, monkeypatch)
    adapter = BrainResearchAdapter(svc)
    calls = []
    class ChangedPolicy:
        def call(self, *args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                monkeypatch.setattr(read_service, "SEGMENT_MAX_BYTES", 3500)
            return adapter.call(*args, **kwargs)
    monkeypatch.setattr(bmi, "_brain_research_adapter", ChangedPolicy)
    assert _load() is None
    assert len(calls) == 2
