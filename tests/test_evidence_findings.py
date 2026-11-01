"""Recorded owner findings, never a fresh detector or evidence-tier authority."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest


def adapter():
    assert importlib.util.find_spec("admin.evidence_findings") is not None, (
        "A1 has no recorded typed-findings consumer"
    )
    return importlib.import_module("admin.evidence_findings")


def row():
    return {"pair_id": "regime-vs-market_state",
            "a": {"artifact": "data/regime/latest.json", "reading": "Q1, 63-day context"},
            "b": {"artifact": "data/world_state.json", "reading": "RISK_OFF, 5-day context"},
            "kind": "label-lag", "severity": "note", "as_of": "2026-10-12",
            "note": "The label lags the continuous scale.", "display_only": True}


def write_report(root, rows=None, **changes):
    document = {"schema": "neuralweb.confluence_graph.v1", "artifact_id": "confluence-graph",
                "asof": "2026-10-12", "produced_at": "2026-10-12T22:30:00Z",
                "produced_by": "engine/neuralweb/confluence.py", "tier": "display",
                "is_context_only": True, "display_only": True,
                "contradiction_records": [row()] if rows is None else rows,
                "gaps": ["oracle source unavailable"]}
    document.update(changes)
    path = root / "data/neuralweb/confluence_graph.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def outputs():
    return [{"artifact_id": "regime", "path": "data/regime/latest.json", "engine_id": "regime::macro"},
            {"artifact_id": "world", "path": "data/world_state.json", "engine_id": "world::macro"}]


def test_records_stay_context_without_inventing_impossible_contradiction(tmp_path):
    path = write_report(tmp_path)
    before = path.read_bytes()
    result = adapter().load_findings(tmp_path, outputs())
    assert result["status"] == "recorded"
    assert result["records"][0]["kind"] == "label-lag"
    assert result["records"][0]["severity"] == "note"
    assert result["records"][0]["a"]["reading"] == "Q1, 63-day context"
    assert result["records"][0]["b"]["reading"] == "RISK_OFF, 5-day context"
    assert result["records"][0]["engine_ids"] == ["regime::macro", "world::macro"]
    assert result["display_only"] is True and result["affects_evidence_status"] is False
    assert result["source"]["as_of"] == "2026-10-12"
    assert len(result["source"]["sha256"]) == 64
    assert result["gaps"] == ["oracle source unavailable"]
    assert result["numeric_attribution"]["status"] == "unavailable"
    assert result["numeric_attribution"]["reason"] == "no_request_scoped_subscriber_receipt"
    assert path.read_bytes() == before


def test_missing_malformed_and_empty_remain_distinct(tmp_path):
    mod = adapter()
    missing = mod.load_findings(tmp_path, [])
    assert missing["status"] == "unavailable" and missing["records"] is None
    path = write_report(tmp_path, rows=[], gaps=[])
    empty = mod.load_findings(tmp_path, [])
    assert empty["status"] == "recorded" and empty["records"] == []
    path.write_text("{broken")
    broken = mod.load_findings(tmp_path, [])
    assert broken["status"] == "unavailable" and broken["records"] is None
    assert broken["reason"] == "invalid_owner_artifact"


@pytest.mark.parametrize("mutation", [
    {"severity": "critical"}, {"display_only": False},
    {"kind": "impossible-contradiction"}, {"a": {"artifact": "/private/data.json", "reading": "bad"}},
])
def test_unsupported_rows_are_disclosed_without_adopting_authority(tmp_path, mutation):
    bad = {**row(), **mutation}
    write_report(tmp_path, rows=[row(), bad])
    result = adapter().load_findings(tmp_path, outputs())
    assert result["status"] == "partial"
    assert len(result["records"]) == 1 and result["rejected_records"] == 1
    assert result["records"][0]["severity"] == "note"
    assert "/private" not in json.dumps(result)


@pytest.mark.parametrize("changes", [
    {"display_only": False}, {"is_context_only": False}, {"tier": "action"},
    {"schema": "other.v1"}, {"contradiction_records": None}, {"gaps": None},
])
def test_wrong_owner_contract_is_unavailable(tmp_path, changes):
    write_report(tmp_path, **changes)
    result = adapter().load_findings(tmp_path, [])
    assert result["status"] == "unavailable" and result["records"] is None


def test_exact_path_binding_rejects_lookalikes_and_ambiguous_owners(tmp_path):
    write_report(tmp_path)
    ambiguous = outputs() + [{"path": "data/regime/latest.json", "engine_id": "other::owner"}]
    result = adapter().load_findings(tmp_path, ambiguous)
    assert result["records"][0]["engine_ids"] == ["world::macro"]
    assert result["records"][0]["a"]["binding"] == "ambiguous"
    decoy = [{"path": "backups/data/regime/latest.json", "engine_id": "regime::macro"}]
    result = adapter().load_findings(tmp_path, decoy)
    assert result["unbound_records"] == 1
    assert result["records"][0]["engine_ids"] == []


def test_detail_filters_only_exact_bound_records_and_retains_global_gap(tmp_path):
    other = row()
    other["a"] = {"artifact": "data/unknown.json", "reading": "unknown"}
    other["b"] = {"artifact": "data/other.json", "reading": "unknown"}
    write_report(tmp_path, rows=[row(), other])
    mod = adapter()
    global_view = mod.load_findings(tmp_path, outputs())
    detail = mod.for_engine(global_view, "world::macro")
    assert len(detail["records"]) == 1
    assert detail["global_unbound_records"] == 1
    assert detail["source"] == global_view["source"]
    assert mod.for_engine(global_view, "not-an-engine")["records"] == []


def test_actual_read_budget_precedes_json_decode(tmp_path, monkeypatch):
    mod = adapter()
    path = write_report(tmp_path)
    path.write_bytes(b"x" * 65)
    monkeypatch.setattr(mod, "MAX_ARTIFACT_BYTES", 64)
    def refuse_decode(*args, **kwargs):
        raise AssertionError("oversized bytes must not reach JSON decoding")
    monkeypatch.setattr(mod.json, "loads", refuse_decode)
    result = mod.load_findings(tmp_path, [])
    assert result["reason"] == "artifact_exceeds_read_budget"


def test_changed_artifact_is_not_mixed_into_a_success(tmp_path, monkeypatch):
    mod = adapter()
    path = write_report(tmp_path)
    original = mod.json.loads
    def concurrent_replace(raw):
        path.write_text("{}")
        return original(raw)
    monkeypatch.setattr(mod.json, "loads", concurrent_replace)
    result = mod.load_findings(tmp_path, [])
    assert result["status"] == "unavailable" and result["reason"] == "changed_during_read"


def test_artifact_correction_changes_digest_without_claiming_market_freshness(tmp_path):
    write_report(tmp_path)
    mod = adapter()
    before = mod.load_findings(tmp_path, outputs())
    corrected = row()
    corrected["note"] = "Correction retains original as-of date."
    write_report(tmp_path, rows=[corrected])
    after = mod.load_findings(tmp_path, outputs())
    assert after["source"]["sha256"] != before["source"]["sha256"]
    assert after["source"]["as_of"] == before["source"]["as_of"]
    assert after["current_source_qualification"] == "unavailable"


@pytest.mark.parametrize("kind", ["directory", "symlink", "fifo"])
def test_nonregular_owner_artifact_is_refused_before_read(tmp_path, kind):
    mod = adapter()
    path = write_report(tmp_path)
    raw = path.read_bytes()
    path.unlink()
    if kind == "directory":
        path.mkdir()
    elif kind == "symlink":
        target = tmp_path / "other.json"
        target.write_bytes(raw)
        path.symlink_to(target)
    else:
        os.mkfifo(path)
    result = mod.load_findings(tmp_path, [])
    assert result["status"] == "unavailable"
    assert result["reason"] == "owner_artifact_not_regular"


def test_replacement_between_metadata_and_open_is_nonblocking(tmp_path, monkeypatch):
    mod = adapter()
    path = write_report(tmp_path)
    real_open = mod.os.open
    def replace_with_fifo(target, flags, *args, **kwargs):
        path.unlink()
        os.mkfifo(path)
        return real_open(target, flags, *args, **kwargs)
    monkeypatch.setattr(mod.os, "open", replace_with_fifo)
    result = mod.load_findings(tmp_path, [])
    assert result["reason"] == "owner_artifact_not_regular"


def test_panel_detail_and_existing_cache_follow_recorded_correction(tmp_path, monkeypatch):
    from admin import intelligence_os as ios
    from scripts import build_output_health
    registry = {"engines": [{"engine_id": "regime::macro", "producer": "regime", "output_class": None},
                            {"engine_id": "world::macro", "producer": "world", "output_class": None}],
                "excluded": []}
    def derive_fixture(*args, **kwargs):
        return {"outputs": outputs(), "summary": {}, "generated": {}}, registry
    monkeypatch.setattr(build_output_health, "build_with_registry", derive_fixture)
    monkeypatch.setattr(ios, "_load_evidence_providers", lambda *args: {})
    ios._CACHE.clear()
    write_report(tmp_path)
    before_key = ios.recorded_snapshot_cache_identity(tmp_path)
    panel = ios.panel(tmp_path)
    assert "typed_findings" in panel, "the live A1 panel has no typed findings connection"
    detail = ios.engine_detail("world::macro", tmp_path)
    assert detail["typed_findings"]["records"] == panel["typed_findings"]["records"]
    assert detail["typed_findings"]["source"] == panel["typed_findings"]["source"]
    original_bands = [(e["engine_id"], e["evidence_status"]) for e in panel["engines"]]
    corrected = row()
    corrected["note"] = "New recorded correction, unchanged outcome authority."
    write_report(tmp_path, rows=[corrected])
    assert ios.recorded_snapshot_cache_identity(tmp_path) != before_key
    refreshed = ios.panel(tmp_path)
    assert refreshed["typed_findings"]["records"][0]["note"] == corrected["note"]
    assert [(e["engine_id"], e["evidence_status"]) for e in refreshed["engines"]] == original_bands
    assert ios.engine_detail("world::macro", tmp_path)["typed_findings"]["source"] == refreshed["typed_findings"]["source"]
    ios._CACHE.clear()
