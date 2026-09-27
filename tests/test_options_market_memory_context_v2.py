import hashlib
import json
from pathlib import Path
from dataclasses import replace

import engine.options_market_memory_context_v2 as context_v2
from engine.options_market_memory_context_v2 import (
    RefusalCode,
    SourceManifest,
    SourceSpec,
    build_audit_plan,
    canonical_stream_hash,
    merge_sorted_runs,
    scan_jsonl,
    validate_audit_plan,
    write_sorted_runs,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in rows))


def test_scan_and_canonical_hash_are_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "owners.jsonl"
    rows = [{"id": "b", "schema": "owner", "value": 2}, {"id": "a", "schema": "owner", "value": 1}]
    _write_jsonl(path, rows)
    observed: list[dict] = []
    result = scan_jsonl(SourceSpec(path, "owners"), observed.append)
    assert result.accepted
    assert result.snapshot is not None
    digest, count, size = canonical_stream_hash(observed)
    assert digest == hashlib.sha256(b'{"id":"b","schema":"owner","value":2}\n{"id":"a","schema":"owner","value":1}\n').hexdigest()
    assert (count, size) == (2, len(b'{"id":"b","schema":"owner","value":2}\n{"id":"a","schema":"owner","value":1}\n'))


def test_mutation_refusal_is_typed(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "owners.jsonl"
    _write_jsonl(path, [{"id": "a", "schema": "owner"}])
    original = context_v2.FileIdentity.from_stat
    calls = 0

    def changing_stat(cls, stat):
        nonlocal calls
        calls += 1
        identity = original(stat)
        if calls > 1:
            return replace(identity, mtime_ns=identity.mtime_ns + 1)
        return identity

    monkeypatch.setattr(context_v2.FileIdentity, "from_stat", classmethod(changing_stat))
    result = scan_jsonl(SourceSpec(path, "owners"))
    assert result.refusal is not None
    assert result.refusal.code is RefusalCode.SOURCE_MUTATED


def test_malformed_and_duplicate_rows_refuse(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.jsonl"
    malformed.write_text('{"schema":"owner","id":"a"}\nnot-json\n')
    result = scan_jsonl(SourceSpec(malformed, "owners"))
    assert result.refusal is not None
    assert result.refusal.code is RefusalCode.MALFORMED_ROW

    duplicate = tmp_path / "duplicate.jsonl"
    _write_jsonl(duplicate, [{"schema": "owner", "id": "a"}, {"schema": "owner", "id": "a"}])
    plan = build_audit_plan(SourceManifest((SourceSpec(duplicate, "owners"),)), tmp_path / "runs")
    assert not hasattr(plan, "trusted_context")
    assert plan.code is RefusalCode.DUPLICATE_OWNER_CONFLICT


def test_manifest_records_explicit_exclusion(tmp_path: Path) -> None:
    consumed = tmp_path / "owners.jsonl"
    excluded = tmp_path / "adjacent.jsonl"
    _write_jsonl(consumed, [{"schema": "owner", "id": "a"}])
    manifest = SourceManifest(
        (SourceSpec(consumed, "owner-ledger"),),
        (SourceSpec(excluded, "adjacent-derivation", consumed=False, exclusion_reason="derived, not an owner ledger"),),
    )
    plan = build_audit_plan(manifest, tmp_path / "runs")
    assert hasattr(plan, "excluded")
    assert plan.excluded[0]["reason"] == "derived, not an owner ledger"


def test_sorted_runs_merge_without_silent_truncation(tmp_path: Path) -> None:
    rows = [{"schema": "owner", "id": str(i)} for i in range(7, -1, -1)]
    runs = write_sorted_runs(rows, tmp_path / "runs", max_rows=2)
    merged = list(merge_sorted_runs(runs))
    assert [row["id"] for row in merged] == [str(i) for i in range(8)]
    digest, count, _ = canonical_stream_hash(merged)
    assert count == len(rows)
    assert len(digest) == 64


def test_two_sources_use_distinct_runs_and_preserve_all_rows(tmp_path: Path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    _write_jsonl(first, [{"schema": "owner", "id": "a"}, {"schema": "owner", "id": "b"}])
    _write_jsonl(second, [{"schema": "owner", "id": "c"}, {"schema": "owner", "id": "d"}])
    run_dir = tmp_path / "runs"
    plan = build_audit_plan(
        SourceManifest((SourceSpec(first, "first"), SourceSpec(second, "second"))),
        run_dir,
        max_rows_per_run=1,
    )
    assert plan.row_count == 4
    assert len(plan.run_paths) == 4
    assert len({path.name for path in plan.run_paths}) == 4


def test_plan_is_inert_and_validates(tmp_path: Path) -> None:
    source = tmp_path / "owners.jsonl"
    _write_jsonl(source, [{"schema": "owner", "id": "a"}])
    plan = build_audit_plan(SourceManifest((SourceSpec(source, "owners"),)), tmp_path / "runs")
    assert validate_audit_plan(plan) is None
    assert plan.trusted_context is False
    assert plan.published is False
