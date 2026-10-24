"""Changed-risk discriminators for optional PDF-block selection and persistence."""
import copy
import hashlib
import json
from xml.sax.saxutils import escape

import pytest

from engine.research_vault import fulltext, source_layout as layout
from engine.research_vault.r2_store import LocalStore
from engine.research_intelligence import selection
from engine.research_intelligence.extractor import _identity, analyze_document
from engine.research_intelligence.store import (
    ResearchIntelligenceInvalid, persist_analysis, load_latest_research_intelligence,
    validate_analysis_for_persistence,
)

GOOD = "The analysts expect healthy demand next year."
ROW1 = "We prefer growth exposure in Asia"
ROW2 = "The yield curve depends on central bank policy."
TAIL = "Regional valuations remain attractive for investors."
BODY = GOOD + " " + ROW1 + "\n" + ROW2 + " " + TAIL
DOC = {"id": "layout-fixture", "source_type": "institutional_research"}


def record(text=BODY):
    return fulltext.build_extracted_text(
        report_id=DOC["id"], source_pdf_sha256="a" * 64, text=text,
        extractor_name="pdftotext", extractor_version=fulltext.EXTRACTOR_VERSION_READING_ORDER_V2,
        page_count=len(fulltext.page_boundaries(text)), text_layer_state="full",
    )


def xml(pages):
    out = '<html xmlns="http://www.w3.org/1999/xhtml"><body><doc>'
    for blocks in pages:
        out += "<page><flow>"
        for block in blocks:
            out += "<block><line>" + "".join("<word>" + escape(w) + "</word>" for w in block.split()) + "</line></block>"
        out += "</flow></page>"
    return (out + "</doc></body></html>").encode()


def fixture():
    r = record()
    raw = xml([[GOOD, ROW1, ROW2, TAIL]])
    scope = layout.build_layout_scope(r, raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())
    return r, scope


def build(r, scope):
    return selection.build_selection_catalog(_identity(DOC, r["text"]), r["text"], source_record=r, layout_scope=scope)


def provider(_system, user, **_kwargs):
    identity = json.loads(user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\n", 1)[0])
    catalog = json.loads(user.split("EVIDENCE CATALOG:\n", 1)[1].split("\n\n", 1)[0])
    out = {"selector": selection.SELECTOR_VERSION, "document": identity,
           "catalog_sha256": catalog["catalog_sha256"],
           "selections": [{"evidence_id": catalog["units"][0]["evidence_id"]}],
           "analysis": {"thesis": {"summary": "The research describes a favorable demand backdrop.",
                       "direction": "unclear", "support_claim_indices": [0]}}}
    return json.dumps(out), "synthetic", "synthetic"


def test_cross_row_rejected_but_complete_prose_retained():
    r, scope = fixture()
    ordinary = selection.build_selection_catalog(_identity(DOC, BODY), BODY)
    filtered = build(r, scope)
    assert any(ROW1 in u["text"] and ROW2 in u["text"] for u in ordinary["units"])
    assert {u["text"] for u in filtered["units"]} == {GOOD, TAIL}
    assert filtered["metadata"]["omitted_layout"] == 1
    assert filtered["catalog_sha256"] != ordinary["catalog_sha256"]
    assert filtered["units"][0] == ordinary["units"][0]
    context = selection.source_context_receipt(filtered)
    assert selection.validate_source_context_receipt(context, expected_content_sha256=r["extracted_text_sha256"]) == context


def test_parser_cannot_select_an_omitted_id_even_with_correct_hash():
    r, scope = fixture(); identity = _identity(DOC, BODY)
    ordinary = selection.build_selection_catalog(identity, BODY); filtered = build(r, scope)
    raw, _, _ = provider("", selection.build_selector_prompt(identity, BODY, source_record=r, layout_scope=scope)[1])
    out = json.loads(raw)
    omitted = next(u for u in ordinary["units"] if ROW1 in u["text"])
    out["selections"][0]["evidence_id"] = omitted["evidence_id"]
    with pytest.raises(ValueError, match="not in the body-bound catalog"):
        selection.parse_selector_output(json.dumps(out), identity, BODY, source_record=r, layout_scope=scope)
    assert filtered["catalog_sha256"] == out["catalog_sha256"]


def test_prompt_parser_store_share_one_scope_and_reopen(tmp_path):
    r, scope = fixture()
    result = analyze_document(DOC, BODY, model_id="synthetic", call=provider, source_record=r, layout_scope=scope)
    assert result["state"] == "ok"
    validate_analysis_for_persistence(result, source_body=BODY, source_record=r, layout_scope=scope)
    store = LocalStore(tmp_path / "store")
    written = persist_analysis(store, result, source_body=BODY, source_record=r, layout_scope=scope)
    reopened = load_latest_research_intelligence(LocalStore(tmp_path / "store"), DOC["id"])
    assert reopened.artifact_sha256 == written.artifact_sha256
    assert reopened.receipt["source_context"]["source_layout"]["scope_sha256"] == scope["scope_sha256"]
    assert len(json.dumps(reopened.receipt).encode()) < 10000
    with pytest.raises(ResearchIntelligenceInvalid):
        persist_analysis(store, result, source_body=BODY)


def test_persistence_rejects_injected_canonical_but_excluded_quote(tmp_path):
    r, scope = fixture()
    result = analyze_document(DOC, BODY, model_id="synthetic", call=provider, source_record=r, layout_scope=scope)
    bad = ROW1 + "\n" + ROW2
    result["rio"]["claims"][0].update(statement=bad, evidence=[{"quote_span": bad}])
    with pytest.raises(ResearchIntelligenceInvalid, match="outside the source-layout catalog"):
        persist_analysis(LocalStore(tmp_path / "store"), result, source_body=BODY, source_record=r, layout_scope=scope)
    assert not list((tmp_path / "store").rglob("*.json"))


def test_mutated_or_missing_scope_refuses_before_model_call():
    r, scope = fixture(); scope["blocks"][0]["end_byte"] = len(BODY.encode())
    calls = []
    out = analyze_document(DOC, BODY, model_id="synthetic", call=lambda *a, **k:calls.append(1), source_record=r, layout_scope=scope)
    assert out["state"] == "selection_unavailable" and out["error_code"] == "SOURCE_LAYOUT_INVALID"
    assert calls == []


@pytest.mark.parametrize("key,value", [("source_pdf_sha256", "b" * 64), ("report_id", "another-report"), ("scope_sha256", "0" * 64), ("schema", "unknown")])
def test_forged_scope_binding_fails_closed(key, value):
    r, scope = fixture(); scope[key] = value
    with pytest.raises(ValueError):
        build(r, scope)


def test_utf8_offsets_and_form_feed_pages_replay_original_bytes():
    first = "研究 demand expands across markets."
    second = "表格 growth is constrained by capacity."
    r = record(first + "\f" + second); raw = xml([[first], [second]])
    scope = layout.build_layout_scope(r, raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())
    data = r["text"].encode()
    assert [data[b["start_byte"]:b["end_byte"]].decode() for b in scope["blocks"]] == [first, second]
    assert scope["blocks"][1]["start_byte"] == len(first.encode()) + 1


def test_repeated_block_and_quote_are_ambiguous():
    r = record(GOOD + " " + GOOD); raw = xml([[GOOD]])
    scope = layout.build_layout_scope(r, raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())
    assert scope["blocks"] == [] and scope["unresolved_blocks"] == 1
    with pytest.raises(selection.SelectionUnavailable):
        build(r, scope)


def test_external_poppler_doctype_is_inert_but_internal_entities_refused():
    r, _ = fixture()
    raw = b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">' + xml([[GOOD, ROW1, ROW2, TAIL]])
    assert layout.build_layout_scope(r, raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())["blocks"]
    hostile = b'<!DOCTYPE html [<!ENTITY x "expanded">]>' + raw
    with pytest.raises(ValueError, match="entities refused"):
        layout.build_layout_scope(r, hostile, expected_layout_sha256=hashlib.sha256(hostile).hexdigest())


def test_layout_bounds_and_mismatch_refuse(monkeypatch):
    r, scope = fixture(); raw = scope["layout_xml"].encode()
    with pytest.raises(ValueError, match="identity"):
        layout.build_layout_scope(r, raw, expected_layout_sha256="0" * 64)
    with pytest.raises(ValueError):
        layout.build_layout_scope(record(BODY + "\f" + TAIL), raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())
    wrong = copy.deepcopy(r); wrong["text"] += "changed"
    with pytest.raises(ValueError):
        layout.build_layout_scope(wrong, raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(layout, "MAX_XML_BYTES", 5)
    with pytest.raises(ValueError, match="bound"):
        layout.build_layout_scope(r, raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())


def test_comparison_budget_is_enforced_before_search(monkeypatch):
    r, scope = fixture(); raw = scope["layout_xml"].encode()
    monkeypatch.setattr(layout, "MAX_COMPARISONS", 1)
    with pytest.raises(ValueError, match="comparison budget"):
        layout.build_layout_scope(r, raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())


def test_malformed_xml_and_wrong_source_version_refuse_before_call():
    r, _ = fixture()
    raw = b"<html><broken>"
    with pytest.raises(ValueError, match="malformed"):
        layout.build_layout_scope(r, raw, expected_layout_sha256=hashlib.sha256(raw).hexdigest())
    r["extractor_version"] = fulltext.EXTRACTOR_VERSION_V1
    good = xml([[GOOD, ROW1, ROW2, TAIL]])
    with pytest.raises(ValueError, match="v2"):
        layout.build_layout_scope(r, good, expected_layout_sha256=hashlib.sha256(good).hexdigest())


def test_stored_layout_receipt_cannot_rebind_another_report():
    r, scope = fixture()
    value = selection.source_context_receipt(build(r, scope))
    with pytest.raises(ValueError, match="layout binding"):
        selection.validate_source_context_receipt(value, expected_content_sha256=r["extracted_text_sha256"], expected_document_id="another-report")


def test_scope_xml_length_checked_before_utf8_expansion(monkeypatch):
    r, scope = fixture()
    monkeypatch.setattr(layout, "MAX_XML_BYTES", 4)
    scope["layout_xml"] = "表格" * 3
    with pytest.raises(ValueError, match="scope invalid"):
        layout.eligible_evidence_ids(r, {}, scope)



def test_provider_catalog_omits_private_layout_binding_but_retains_catalog_pin():
    r, scope = fixture()
    _system, user, catalog = selection.build_selector_prompt(
        _identity(DOC, r["text"]), r["text"], source_record=r, layout_scope=scope)
    sent = json.loads(user.split("EVIDENCE CATALOG:\n", 1)[1].split("\n\n", 1)[0])
    assert "source_layout" not in sent
    assert sent["catalog_sha256"] == catalog["catalog_sha256"]
    assert "source_layout" in selection.source_context_receipt(catalog)


def eligibility_catalog(count):
    statements = [f"Evidence number{i} describes continued demand growth for regional companies." for i in range(count)]
    text = "neutral " * 30000 + "\n" + "\n".join(statements)
    r = record(text)
    source = xml([statements])
    scope = layout.build_layout_scope(r, source, expected_layout_sha256=hashlib.sha256(source).hexdigest())
    catalog = {"document": {"id": r["report_id"], "content_sha256": r["extracted_text_sha256"]},
        "units": [{"evidence_id": f"unit-{i}", "text": statement} for i, statement in enumerate(statements)]}
    return r, scope, catalog


def test_eligibility_uses_reserved_byte_work_instead_of_token_alignment_budget():
    r, scope, catalog = eligibility_catalog(160)
    assert len(r["text"].encode()) * len(catalog["units"]) > layout.MAX_COMPARISONS
    result = layout.eligible_evidence_ids(r, catalog, scope)
    assert result["omitted_layout"] == 0
    assert len(result["allowed_evidence_ids"]) == 160


def test_eligibility_still_refuses_beyond_existing_analysis_reservation():
    assert 2 * layout.MAX_ELIGIBILITY_COMPARISONS <= selection.MAX_VERIFIER_WORK_BYTES
    r, scope, catalog = eligibility_catalog(400)
    with pytest.raises(ValueError, match="eligibility budget exceeded"):
        layout.eligible_evidence_ids(r, catalog, scope)
