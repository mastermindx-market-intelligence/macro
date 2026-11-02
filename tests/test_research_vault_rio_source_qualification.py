"""RIO CURRENT requires verified source identity, including empty-layer fast paths."""
import pytest
import hashlib
from dataclasses import replace
from tests.test_research_vault_read_service import _service, _item, _extracted, _rio, _ctx, PDF_SHA

@pytest.mark.parametrize("operation",["fetch","find_evidence"])
@pytest.mark.parametrize("layer",["full","thin","none","unavailable"])
def test_matching_old_rio_is_stale_without_verified_current_source(tmp_path,operation,layer):
    rid="rio-source-report"
    text=None if layer=="unavailable" else "" if layer=="none" else "hyperscaler source"
    record=_extracted(rid,text=text,layer=layer)
    stored=_rio(rid,record["extracted_text_sha256"])
    svc,_,_,digest,_,_=_service(tmp_path,items=[_item(rid,"RIO source","2026-10-05T11:00:00+00:00")],extracted={rid:record},digest=hashlib.sha256(b"new PDF revision").hexdigest(),rio=stored)
    result=svc.fetch(caller_context=_ctx(),report_id=rid,selectors={}) if operation=="fetch" else svc.find_evidence(caller_context=_ctx(),report_id=rid,query="hyperscaler",max_passages=3)
    assert result["rio_state"]=="STALE"
    assert not result.get("segments",[]) and not result.get("passages",[])
    assert digest.calls==(1 if layer in {"full","thin"} else 0)
    if operation=="fetch":
        assert result["rio_artifact_sha256"]==stored.artifact_sha256
    else:
        assert result["evidence_state"]=="UNAVAILABLE"

@pytest.mark.parametrize("operation",["fetch","find_evidence"])
@pytest.mark.parametrize("layer",["full","thin"])
def test_source_verified_full_or_thin_matching_text_rio_remains_current(tmp_path,operation,layer):
    rid="rio-current-report"
    record=_extracted(rid,text="hyperscaler source",layer=layer)
    svc,_,loader,digest,_,_=_service(tmp_path,items=[_item(rid,"RIO current","2026-10-05T11:00:00+00:00")],extracted={rid:record},digest=PDF_SHA,rio=_rio(rid,record["extracted_text_sha256"]))
    result=svc.fetch(caller_context=_ctx(),report_id=rid,selectors={}) if operation=="fetch" else svc.find_evidence(caller_context=_ctx(),report_id=rid,query="hyperscaler",max_passages=3)
    assert result["rio_state"]=="CURRENT"
    assert result["coverage_state"]=="FULL_TEXT"
    assert loader.calls==digest.calls==1


@pytest.mark.parametrize("operation", ["fetch", "find_evidence"])
def test_current_rio_retains_partial_source_context_degradation(tmp_path, operation):
    """Current revision identity does not imply exhaustive model context."""
    rid = "rio-partial-context-report"
    record = _extracted(rid, text="hyperscaler source", layer="full")
    stored = replace(_rio(rid, record["extracted_text_sha256"]), receipt={
        "source_context": {
            "coverage": "PARTIAL_SOURCE_CONTEXT",
            "exhaustive_source_coverage": False,
        },
    })
    svc, *_ = _service(tmp_path,
        items=[_item(rid, "RIO partial context", "2026-10-05T11:00:00+00:00")],
        extracted={rid: record}, digest=PDF_SHA, rio=stored)
    result = (svc.fetch(caller_context=_ctx(), report_id=rid, selectors={})
        if operation == "fetch" else svc.find_evidence(
            caller_context=_ctx(), report_id=rid, query="hyperscaler", max_passages=3))
    assert result["rio_state"] == "CURRENT"
    assert result["coverage_state"] == "FULL_TEXT"
    assert "RIO_PARTIAL" in result["source"]["known_degradation"]
