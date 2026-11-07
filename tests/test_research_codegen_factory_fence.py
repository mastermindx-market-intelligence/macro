"""Inert codegen metadata must never enter a legacy evaluator or writer."""
from __future__ import annotations

import builtins
import json

import pytest

from engine.research_factory.schema import validate_candidate
from scripts.research_factory_run import _route_candidate, run


def candidate():
    return {
        "schema": "research_factory.candidate.v1", "authority": "display_only",
        "candidate_id": "rf-test-legacy", "created_at": "2026-10-12T00:00:00Z",
        "source": "human", "candidate_type": "external_idea", "domain": "entry",
        "status": "registered", "hypothesis": "Synthetic contract fixture",
        "mechanism": "No research execution", "artifacts": {},
    }


@pytest.mark.parametrize("marker", [
    {"candidate_type": "code_candidate"},
    {"source": "research_codegen"},
    {"domain": "research_codegen"},
    {"candidate_id": "rf-codegen-inert"},
    {"artifacts": {"codegen_manifest_ref": "inert-reference"}},
    {"artifacts": {"nested": [{"schema": "research_codegen.manifest.v1"}]}},
])
@pytest.mark.parametrize("legacy_route", [
    {"domain": "oracle"}, {"source": "cortex"}, {"source": "alpha_grammar"},
])
def test_reserved_markers_refuse_before_legacy_adapter_import(monkeypatch, tmp_path, marker, legacy_route):
    row = candidate() | legacy_route | marker
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("engine.research_factory.adapter_"):
            pytest.fail(f"codegen reached legacy adapter: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    result = _route_candidate(row, data_dir=tmp_path, count=True, dry_run=False)
    assert result["action"] == "error"
    assert result["adapter_result"] is None
    assert "RF-16" in result["reason"]
    assert any("RF-16" in error for error in validate_candidate(row))


@pytest.mark.parametrize("dry_run", [True, False])
def test_runner_cannot_transition_reserved_record(tmp_path, dry_run):
    row = candidate() | {"domain": "oracle", "artifacts": {"codegen_manifest": {}}}
    source = tmp_path / "candidates.jsonl"
    source.write_text(json.dumps(row) + "\n")
    before = source.read_bytes()
    summary = run(rf_dir=tmp_path, data_dir=tmp_path, dry_run=dry_run, count=True)
    assert summary["routes"][0]["action"] == "error"
    assert summary["transitions_attempted"] == 0
    assert source.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["candidates.jsonl"]


def test_ordinary_legacy_candidate_remains_valid():
    assert validate_candidate(candidate()) == []


@pytest.mark.parametrize("filename", ["candidates.jsonl", "transitions.jsonl", "paper_monitor.jsonl"])
@pytest.mark.parametrize("writer", ["append", "permissive_append", "bulk"])
def test_canonical_writers_refuse_reserved_metadata_without_changing_file(tmp_path, filename, writer):
    from engine.research_factory.ledger import append_row, write_jsonl

    target = tmp_path / filename
    original = b'{"retained":"original evidence"}\n'
    target.write_bytes(original)
    row = candidate() | {"artifacts": {"codegen_manifest_ref": "inert-reference"}}
    with pytest.raises(ValueError, match="RF-16"):
        if writer == "bulk":
            write_jsonl(target, [row])
        elif writer == "permissive_append":
            append_row(target, row, validate_fn=lambda _: [])
        else:
            append_row(target, row)
    assert target.read_bytes() == original


def test_bounded_walk_rejects_cycle_but_preserves_shared_json_values():
    from engine.research_factory.codegen_boundary import codegen_refusal

    shared = {"ref": "legacy"}
    assert codegen_refusal({"a": shared, "b": shared}) is None
    cyclic = []
    cyclic.append(cyclic)
    assert "acyclic" in codegen_refusal(cyclic)
    assert "limit" in codegen_refusal([None] * 4097)
    # The size check runs before inspecting keys or allocating dictionary children.
    assert "limit" in codegen_refusal({i: None for i in range(4097)})
