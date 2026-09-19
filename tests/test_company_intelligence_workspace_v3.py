from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from engine.company_intelligence.contracts import canonical_json_bytes
from engine.neuralweb import company_intelligence_reader as reader

from engine.company_intelligence.event_workspace import (
    MANIFEST_SCHEMA_V3,
    REVISION_INDEX_SCHEMA_V1,
    WorkspaceError,
    build_revision_index,
    build_revision_index_from_legacy,
    preview_generation_identity_v3,
    validate_revision_index,
    validate_workspace_manifest,
    write_workspace_generation,
    write_workspace_generation_v3,
)

EVENT_ID = "evt_cik0000320193_2026q3_results"


def _workspace(
    *,
    source_sha256: str,
    source_available_at: str,
    observed_at: str,
    state: str = "complete",
    fact_value: int = 100,
) -> dict:
    return {
        "schema": "event_workspace.v1",
        "event_id": EVENT_ID,
        "aliases": ["AAPL/2026Q3"],
        "issuer": {
            "company_id": "cik:0000320193",
            "display_name": "Apple Inc.",
            "listings": [],
        },
        "fiscal_period": {
            "year": 2026,
            "quarter": 3,
            "calendar_end": "2026-06-27",
        },
        "lifecycle": {
            "state": state,
            "observed_at": observed_at,
            "source_available_at": source_available_at,
        },
        "completeness": {},
        "facts": [{
            "schema": "event_fact.v1",
            "metric": "revenue",
            "value": fact_value,
            "unit": "USD",
            "period": "2026Q3",
            "basis": "reported",
            "source_span": None,
        }],
        "deltas": [],
        "guidance": [],
        "claims": [],
        "sources": [{
            "kind": "issuer_release",
            "document_id": "doc:issuer-release",
            "filing_key": {
                "cik": "0000320193",
                "accession": "0000320193-26-000018",
            },
            "source_sha256": source_sha256,
            "form": "8-K",
            "url": None,
            "receipt_state": "byte_replayed",
        }],
        "warnings": [],
        "generation_id": "",
        "generated_at": source_available_at,
        "authority": "context_only",
        "prophet_flags": {
            "may_rank": False,
            "may_size": False,
            "may_gate": False,
            "prophet_authority": False,
        },
        "claim_citations_pending": False,
        "qa_exchanges": [],
    }


def _read_generation(generation_dir: Path) -> tuple[dict, dict]:
    manifest = json.loads((generation_dir / "manifest.json").read_text(encoding="utf-8"))
    revision_index = json.loads(
        (generation_dir / "revision_index.json").read_text(encoding="utf-8")
    )
    return manifest, revision_index


def _mint(
    out_dir: Path,
    workspace: dict,
    *,
    generated_at: str,
    previous_generation_id: str | None = None,
    previous_manifest_sha256: str | None = None,
    previous_index: dict | None = None,
    previous_manifest: dict | None = None,
) -> tuple[Path, dict, dict]:
    index = build_revision_index(
        {EVENT_ID: workspace},
        previous_index=previous_index,
        previous_manifest=previous_manifest,
    )
    generation_dir = write_workspace_generation_v3(
        out_dir,
        {EVENT_ID: workspace},
        revision_index=index,
        generated_at=generated_at,
        previous_generation_id=previous_generation_id,
        previous_manifest_sha256=previous_manifest_sha256,
    )
    manifest, written_index = _read_generation(generation_dir)
    return generation_dir, manifest, written_index


def _manifest_sha(generation_dir: Path) -> str:
    from hashlib import sha256

    return sha256((generation_dir / "manifest.json").read_bytes()).hexdigest()


def test_v3_writer_terminates_with_authenticated_relative_self_row(tmp_path: Path) -> None:
    workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    generation_dir, manifest, revision_index = _mint(
        tmp_path,
        workspace,
        generated_at="2026-07-30T20:31:05Z",
    )

    assert manifest["schema"] == MANIFEST_SCHEMA_V3
    assert revision_index["schema"] == REVISION_INDEX_SCHEMA_V1
    receipt = manifest["revision_index"]
    body = (generation_dir / receipt["path"]).read_bytes()
    assert receipt["bytes"] == len(body)

    from hashlib import sha256

    assert receipt["sha256"] == sha256(body).hexdigest()
    row = revision_index["events"][EVENT_ID][-1]
    assert row["workspace_generation_ref"] == "self"
    assert row["generated_at"] is None
    assert row["workspace_receipt"] is None
    validate_workspace_manifest(manifest)
    validate_revision_index(revision_index, manifest=manifest)


def test_same_v3_inputs_and_mint_clock_reproduce_identical_bytes(tmp_path: Path) -> None:
    workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    first, first_manifest, first_index = _mint(
        tmp_path,
        workspace,
        generated_at="2026-07-30T20:31:05Z",
    )
    first_bytes = {
        relative: (first / relative).read_bytes()
        for relative in (
            "manifest.json",
            "revision_index.json",
            f"workspaces/{EVENT_ID}.json",
        )
    }
    second, second_manifest, second_index = _mint(
        tmp_path,
        workspace,
        generated_at="2026-07-30T20:31:05Z",
    )

    assert second == first
    assert second_manifest == first_manifest
    assert second_index == first_index
    assert {relative: (second / relative).read_bytes() for relative in first_bytes} == first_bytes


def test_v3_preview_uses_explicit_mint_clock_and_matches_writer(tmp_path: Path) -> None:
    workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    revision_index = build_revision_index({EVENT_ID: workspace})
    preview = preview_generation_identity_v3(
        {EVENT_ID: workspace},
        revision_index,
        "2026-07-30T20:31:05Z",
        previous_generation_id=None,
    )
    generation_dir = write_workspace_generation_v3(
        tmp_path,
        {EVENT_ID: workspace},
        revision_index=revision_index,
        generated_at="2026-07-30T20:31:05Z",
    )

    assert generation_dir.name == preview
    later_preview = preview_generation_identity_v3(
        {EVENT_ID: workspace},
        revision_index,
        "2026-09-18T20:56:33Z",
        previous_generation_id=None,
    )
    assert later_preview != preview


def test_source_correction_materializes_prior_self_and_appends_one_new_self(tmp_path: Path) -> None:
    first_workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    first_dir, first_manifest, first_index = _mint(
        tmp_path,
        first_workspace,
        generated_at="2026-07-30T20:31:05Z",
    )
    corrected_workspace = _workspace(
        source_sha256="b" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-09-18T20:56:33Z",
        state="corrected",
        fact_value=101,
    )
    second_dir, second_manifest, second_index = _mint(
        tmp_path,
        corrected_workspace,
        generated_at="2026-09-18T20:57:00Z",
        previous_generation_id=first_dir.name,
        previous_manifest_sha256=_manifest_sha(first_dir),
        previous_index=first_index,
        previous_manifest=first_manifest,
    )

    rows = second_index["events"][EVENT_ID]
    assert len(rows) == 2
    historical, current = rows
    assert historical["workspace_generation_ref"] == first_dir.name
    assert historical["generated_at"] == first_manifest["generated_at"]
    assert historical["workspace_receipt"] == first_manifest["files"][
        f"workspaces/{EVENT_ID}.json"
    ]
    assert current["workspace_generation_ref"] == "self"
    assert current["generated_at"] is None
    assert current["workspace_receipt"] is None
    assert second_manifest["generated_at"] == "2026-09-18T20:57:00Z"
    written_workspace = json.loads(
        (second_dir / "workspaces" / f"{EVENT_ID}.json").read_text(encoding="utf-8")
    )
    assert written_workspace["generated_at"] == "2026-09-18T20:57:00Z"
    assert written_workspace["lifecycle"]["source_available_at"] == "2026-07-30T20:30:28Z"
    validate_revision_index(second_index, manifest=second_manifest)


def test_same_source_sha_is_one_semantic_row_across_full_workspace_enrichment(tmp_path: Path) -> None:
    first_workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    first_dir, first_manifest, first_index = _mint(
        tmp_path,
        first_workspace,
        generated_at="2026-07-30T20:31:05Z",
    )
    enriched = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
        fact_value=105,
    )
    second_index = build_revision_index(
        {EVENT_ID: enriched},
        previous_index=first_index,
        previous_manifest=first_manifest,
    )

    assert len(second_index["events"][EVENT_ID]) == 1
    only = second_index["events"][EVENT_ID][0]
    assert only["workspace_generation_ref"] == first_dir.name
    assert only["workspace_receipt"] == first_manifest["files"][
        f"workspaces/{EVENT_ID}.json"
    ]


def test_source_sha_cycle_a_b_a_remains_three_semantic_rows(tmp_path: Path) -> None:
    workspace_a1 = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    dir_a1, manifest_a1, index_a1 = _mint(
        tmp_path,
        workspace_a1,
        generated_at="2026-07-30T20:31:05Z",
    )
    workspace_b = _workspace(
        source_sha256="b" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-08-15T12:00:00Z",
        state="corrected",
        fact_value=101,
    )
    dir_b, manifest_b, index_b = _mint(
        tmp_path,
        workspace_b,
        generated_at="2026-08-15T12:00:05Z",
        previous_generation_id=dir_a1.name,
        previous_manifest_sha256=_manifest_sha(dir_a1),
        previous_index=index_a1,
        previous_manifest=manifest_a1,
    )
    workspace_a2 = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-09-18T20:56:33Z",
        state="corrected",
        fact_value=102,
    )
    _dir_a2, manifest_a2, index_a2 = _mint(
        tmp_path,
        workspace_a2,
        generated_at="2026-09-18T20:57:00Z",
        previous_generation_id=dir_b.name,
        previous_manifest_sha256=_manifest_sha(dir_b),
        previous_index=index_b,
        previous_manifest=manifest_b,
    )

    assert [row["source_sha256"] for row in index_a2["events"][EVENT_ID]] == [
        "a" * 64,
        "b" * 64,
        "a" * 64,
    ]
    assert index_a2["events"][EVENT_ID][-1]["workspace_generation_ref"] == "self"
    validate_revision_index(index_a2, manifest=manifest_a2)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda rows: rows.insert(0, dict(rows[-1])),
        lambda rows: rows.append(dict(rows[-1])),
        lambda rows: rows.__setitem__(0, {**rows[0], "workspace_generation_ref": "self"}),
    ],
    ids=("self-not-final", "duplicate-self", "historical-self"),
)
def test_self_row_is_unique_and_final(
    tmp_path: Path,
    mutate,
) -> None:
    workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    first_dir, first_manifest, first_index = _mint(
        tmp_path,
        workspace,
        generated_at="2026-07-30T20:31:05Z",
    )
    correction = _workspace(
        source_sha256="b" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-09-18T20:56:33Z",
        state="corrected",
        fact_value=101,
    )
    _second_dir, second_manifest, second_index = _mint(
        tmp_path,
        correction,
        generated_at="2026-09-18T20:57:00Z",
        previous_generation_id=first_dir.name,
        previous_manifest_sha256=_manifest_sha(first_dir),
        previous_index=first_index,
        previous_manifest=first_manifest,
    )
    rows = second_index["events"][EVENT_ID]
    mutate(rows)

    with pytest.raises(WorkspaceError, match="self"):
        validate_revision_index(second_index, manifest=second_manifest)


def test_v3_manifest_rejects_an_unauthenticated_index_sidecar(tmp_path: Path) -> None:
    workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    _generation_dir, manifest, _revision_index = _mint(
        tmp_path,
        workspace,
        generated_at="2026-07-30T20:31:05Z",
    )
    unauthenticated = dict(manifest)
    unauthenticated.pop("revision_index")

    with pytest.raises(WorkspaceError, match="keys mismatch"):
        validate_workspace_manifest(unauthenticated)


BASE = "https://company-intelligence-v3.example/company_intelligence"


def _v3_server(
    generation_dirs: list[Path],
    *,
    current: Path,
    fetch_calls: list[str],
    overrides: dict[str, bytes] | None = None,
):
    objects: dict[str, bytes] = {}
    for generation_dir in generation_dirs:
        generation_id = generation_dir.name
        prefix = f"{BASE}/event_workspaces/generations/{generation_id}"
        objects[f"{prefix}/manifest.json"] = (
            generation_dir / "manifest.json"
        ).read_bytes()
        revision_index_path = generation_dir / "revision_index.json"
        if revision_index_path.exists():
            objects[f"{prefix}/revision_index.json"] = revision_index_path.read_bytes()
        for workspace_path in sorted((generation_dir / "workspaces").glob("*.json")):
            objects[f"{prefix}/workspaces/{workspace_path.name}"] = workspace_path.read_bytes()
    objects[f"{BASE}/event_workspaces/manifest.json"] = (
        current / "manifest.json"
    ).read_bytes()
    objects.update(overrides or {})

    def fake_fetch(url: str, *, limit: int, allow_404: bool = False) -> bytes | None:
        fetch_calls.append(url)
        body = objects.get(url)
        if body is None:
            if allow_404:
                return None
            raise reader.CompanyIntelligenceReadError(f"404: {url}")
        if len(body) > limit:
            raise reader.CompanyIntelligenceReadError(f"object exceeds bound: {url}")
        return body

    return fake_fetch


def _two_revision_v3_chain(tmp_path: Path) -> tuple[Path, Path]:
    first_workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    first_dir, first_manifest, first_index = _mint(
        tmp_path,
        first_workspace,
        generated_at="2026-07-30T20:31:05Z",
    )
    corrected_workspace = _workspace(
        source_sha256="b" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-09-18T20:56:33Z",
        state="corrected",
        fact_value=101,
    )
    second_dir, _manifest, _index = _mint(
        tmp_path,
        corrected_workspace,
        generated_at="2026-09-18T20:57:00Z",
        previous_generation_id=first_dir.name,
        previous_manifest_sha256=_manifest_sha(first_dir),
        previous_index=first_index,
        previous_manifest=first_manifest,
    )
    return first_dir, second_dir


def test_v3_reader_fetches_only_indexed_semantic_workspaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_dir, second_dir = _two_revision_v3_chain(tmp_path)
    fetch_calls: list[str] = []
    monkeypatch.setattr(
        reader,
        "_fetch_bytes",
        _v3_server(
            [first_dir, second_dir],
            current=second_dir,
            fetch_calls=fetch_calls,
        ),
    )

    revisions = reader.read_event_source_revisions(EVENT_ID, base_url=BASE)

    assert [item["source_sha256"] for item in revisions] == ["a" * 64, "b" * 64]
    assert [item["generation_id"] for item in revisions] == [first_dir.name, second_dir.name]
    current_prefix = f"{BASE}/event_workspaces/generations/{second_dir.name}"
    predecessor_prefix = f"{BASE}/event_workspaces/generations/{first_dir.name}"
    assert f"{current_prefix}/revision_index.json" in fetch_calls
    assert f"{predecessor_prefix}/manifest.json" not in fetch_calls
    assert fetch_calls.count(f"{predecessor_prefix}/workspaces/{EVENT_ID}.json") == 1
    assert fetch_calls.count(f"{current_prefix}/workspaces/{EVENT_ID}.json") == 1


def test_v3_reader_refuses_corrupt_index_bytes_before_workspace_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_dir, second_dir = _two_revision_v3_chain(tmp_path)
    fetch_calls: list[str] = []
    index_url = (
        f"{BASE}/event_workspaces/generations/{second_dir.name}/revision_index.json"
    )
    monkeypatch.setattr(
        reader,
        "_fetch_bytes",
        _v3_server(
            [first_dir, second_dir],
            current=second_dir,
            fetch_calls=fetch_calls,
            overrides={index_url: b'{"schema":"corrupt"}\n'},
        ),
    )

    with pytest.raises(reader.WorkspaceChainIntegrityError, match="revision index"):
        reader.read_event_source_revisions(EVENT_ID, base_url=BASE)

    assert not any(f"/workspaces/{EVENT_ID}.json" in url for url in fetch_calls)


def test_v3_reader_refuses_index_metadata_that_disagrees_with_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_dir, second_dir = _two_revision_v3_chain(tmp_path)
    manifest, revision_index = _read_generation(second_dir)
    revision_index["events"][EVENT_ID][-1]["source_sha256"] = "c" * 64
    index_body = canonical_json_bytes(revision_index)
    manifest["revision_index"]["bytes"] = len(index_body)
    manifest["revision_index"]["sha256"] = sha256(index_body).hexdigest()
    manifest_body = canonical_json_bytes(manifest)
    prefix = f"{BASE}/event_workspaces/generations/{second_dir.name}"
    overrides = {
        f"{BASE}/event_workspaces/manifest.json": manifest_body,
        f"{prefix}/manifest.json": manifest_body,
        f"{prefix}/revision_index.json": index_body,
    }
    fetch_calls: list[str] = []
    monkeypatch.setattr(
        reader,
        "_fetch_bytes",
        _v3_server(
            [first_dir, second_dir],
            current=second_dir,
            fetch_calls=fetch_calls,
            overrides=overrides,
        ),
    )

    with pytest.raises(
        reader.WorkspaceChainIntegrityError,
        match="source_sha256 metadata disagrees with the index",
    ):
        reader.read_event_source_revisions(EVENT_ID, base_url=BASE)


def test_legacy_seed_excludes_current_bad_clock_and_reintroduces_truthful_self() -> None:
    old_workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    old_workspace["generation_id"] = "1" * 24
    old_workspace["generated_at"] = "2026-07-30T20:31:05Z"
    current_workspace = _workspace(
        source_sha256="b" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-09-18T20:56:33Z",
        state="corrected",
        fact_value=101,
    )
    current_workspace["generation_id"] = "2" * 24
    current_workspace["generated_at"] = "2026-07-30T20:31:05Z"
    legacy_revisions = {
        EVENT_ID: [
            {
                "generation_id": "1" * 24,
                "source_sha256": "a" * 64,
                "source_available_at": "2026-07-30T20:30:28Z",
                "observed_at": "2026-07-30T20:31:00Z",
                "lifecycle_state": "complete",
                "form": "8-K",
                "workspace_receipt": {"bytes": 100, "sha256": "c" * 64},
                "workspace": old_workspace,
            },
            {
                "generation_id": "2" * 24,
                "source_sha256": "b" * 64,
                "source_available_at": "2026-07-30T20:30:28Z",
                "observed_at": "2026-09-18T20:56:33Z",
                "lifecycle_state": "corrected",
                "form": "8-K",
                "workspace_receipt": {"bytes": 110, "sha256": "d" * 64},
                "workspace": current_workspace,
            },
        ]
    }

    index = build_revision_index_from_legacy(
        {EVENT_ID: current_workspace},
        legacy_revisions,
        current_generation_id="2" * 24,
        migration_generated_at="2026-09-18T21:00:00Z",
    )

    rows = index["events"][EVENT_ID]
    assert len(rows) == 2
    assert rows[0]["workspace_generation_ref"] == "1" * 24
    assert rows[0]["generated_at"] == "2026-07-30T20:31:05Z"
    assert rows[0]["generated_at_basis"] == "WORKSPACE_ENVELOPE"
    assert rows[-1]["workspace_generation_ref"] == "self"
    assert rows[-1]["generated_at"] is None
    assert rows[-1]["generated_at_basis"] == "ENCLOSING_MANIFEST"
    assert rows[-1]["source_sha256"] == "b" * 64
    validate_revision_index(index)


def test_v3_reader_refuses_marker_that_differs_from_immutable_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_dir, second_dir = _two_revision_v3_chain(tmp_path)
    immutable_manifest, _revision_index = _read_generation(second_dir)
    divergent_marker = dict(immutable_manifest)
    divergent_marker["status"] = "degraded"
    marker_url = f"{BASE}/event_workspaces/manifest.json"
    fetch_calls: list[str] = []
    monkeypatch.setattr(
        reader,
        "_fetch_bytes",
        _v3_server(
            [first_dir, second_dir],
            current=second_dir,
            fetch_calls=fetch_calls,
            overrides={marker_url: canonical_json_bytes(divergent_marker)},
        ),
    )

    with pytest.raises(reader.WorkspaceChainIntegrityError, match="marker"):
        reader.read_event_source_revisions(EVENT_ID, base_url=BASE)

    assert not any(url.endswith("/revision_index.json") for url in fetch_calls)


def test_v3_reader_typed_refuses_an_unknown_manifest_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_dir, second_dir = _two_revision_v3_chain(tmp_path)
    manifest, _revision_index = _read_generation(second_dir)
    unknown = dict(manifest)
    unknown["schema"] = "event_workspace_manifest.v4"
    unknown_body = canonical_json_bytes(unknown)
    prefix = f"{BASE}/event_workspaces/generations/{second_dir.name}"
    fetch_calls: list[str] = []
    monkeypatch.setattr(
        reader,
        "_fetch_bytes",
        _v3_server(
            [first_dir, second_dir],
            current=second_dir,
            fetch_calls=fetch_calls,
            overrides={
                f"{BASE}/event_workspaces/manifest.json": unknown_body,
                f"{prefix}/manifest.json": unknown_body,
            },
        ),
    )

    with pytest.raises(reader.WorkspaceChainIntegrityError, match="unsupported"):
        reader.read_event_source_revisions(EVENT_ID, base_url=BASE)

    assert not any(f"/workspaces/{EVENT_ID}.json" in url for url in fetch_calls)


def test_v3_reader_recomputes_generation_identity_and_refuses_dropped_middle_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_a1 = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    dir_a1, manifest_a1, index_a1 = _mint(
        tmp_path,
        workspace_a1,
        generated_at="2026-07-30T20:31:05Z",
    )
    workspace_b = _workspace(
        source_sha256="b" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-08-15T12:00:00Z",
        state="corrected",
        fact_value=101,
    )
    dir_b, manifest_b, index_b = _mint(
        tmp_path,
        workspace_b,
        generated_at="2026-08-15T12:00:05Z",
        previous_generation_id=dir_a1.name,
        previous_manifest_sha256=_manifest_sha(dir_a1),
        previous_index=index_a1,
        previous_manifest=manifest_a1,
    )
    workspace_a2 = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-09-18T20:56:33Z",
        state="corrected",
        fact_value=102,
    )
    dir_a2, manifest_a2, index_a2 = _mint(
        tmp_path,
        workspace_a2,
        generated_at="2026-09-18T20:57:00Z",
        previous_generation_id=dir_b.name,
        previous_manifest_sha256=_manifest_sha(dir_b),
        previous_index=index_b,
        previous_manifest=manifest_b,
    )

    dropped = json.loads(json.dumps(index_a2))
    del dropped["events"][EVENT_ID][1]
    dropped_body = canonical_json_bytes(dropped)
    forged_manifest = json.loads(json.dumps(manifest_a2))
    forged_manifest["revision_index"]["bytes"] = len(dropped_body)
    forged_manifest["revision_index"]["sha256"] = sha256(dropped_body).hexdigest()
    forged_manifest_body = canonical_json_bytes(forged_manifest)
    prefix = f"{BASE}/event_workspaces/generations/{dir_a2.name}"
    fetch_calls: list[str] = []
    monkeypatch.setattr(
        reader,
        "_fetch_bytes",
        _v3_server(
            [dir_a1, dir_b, dir_a2],
            current=dir_a2,
            fetch_calls=fetch_calls,
            overrides={
                f"{BASE}/event_workspaces/manifest.json": forged_manifest_body,
                f"{prefix}/manifest.json": forged_manifest_body,
                f"{prefix}/revision_index.json": dropped_body,
            },
        ),
    )

    with pytest.raises(
        reader.WorkspaceChainIntegrityError,
        match="generation identity|consecutive source",
    ):
        reader.audit_v3_generation_identity(forged_manifest, base_url=BASE)


def test_legacy_seed_preserves_distinct_revisions_with_equal_legacy_mint_clocks() -> None:
    collapsed_clock = "2026-07-30T20:31:05Z"
    revisions = []
    for generation_id, source_sha, observed_at, state, value in (
        ("1" * 24, "a" * 64, "2026-07-30T20:31:00Z", "complete", 100),
        ("2" * 24, "b" * 64, "2026-08-15T12:00:00Z", "corrected", 101),
        ("3" * 24, "c" * 64, "2026-09-18T20:56:33Z", "corrected", 102),
    ):
        workspace = _workspace(
            source_sha256=source_sha,
            source_available_at="2026-07-30T20:30:28Z",
            observed_at=observed_at,
            state=state,
            fact_value=value,
        )
        workspace["generation_id"] = generation_id
        workspace["generated_at"] = collapsed_clock
        revisions.append({
            "generation_id": generation_id,
            "source_sha256": source_sha,
            "source_available_at": "2026-07-30T20:30:28Z",
            "observed_at": observed_at,
            "lifecycle_state": state,
            "form": "8-K",
            "workspace_receipt": {
                "bytes": 100 + value,
                "sha256": str(value)[-1] * 64,
            },
            "workspace": workspace,
        })

    current_workspace = dict(revisions[-1]["workspace"])
    index = build_revision_index_from_legacy(
        {EVENT_ID: current_workspace},
        {EVENT_ID: revisions},
        current_generation_id="3" * 24,
        migration_generated_at="2026-09-19T00:00:00Z",
    )

    rows = index["events"][EVENT_ID]
    assert [row["source_sha256"] for row in rows] == ["a" * 64, "b" * 64, "c" * 64]
    assert [row["generated_at"] for row in rows] == [
        collapsed_clock, "2026-09-19T00:00:00Z", None,
    ]
    assert [row["generated_at_basis"] for row in rows] == [
        "WORKSPACE_ENVELOPE", "V3_MIGRATION_MINT", "ENCLOSING_MANIFEST",
    ]
    assert rows[-1]["workspace_generation_ref"] == "self"


def test_v3_generation_identity_binds_effective_private_alias_projection() -> None:
    first = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    first["_aliases"] = {
        "canonical_event_id": EVENT_ID,
        "company_intelligence_ids": ["cie_private_alias_a"],
        "earnings_narrative_keys": ["AAPL/2026Q3"],
        "public_slugs": ["aapl-2026q3-call-record"],
    }
    second = json.loads(json.dumps(first))
    second["_aliases"]["company_intelligence_ids"] = ["cie_private_alias_b"]

    first_index = build_revision_index({EVENT_ID: first})
    second_index = build_revision_index({EVENT_ID: second})
    first_id = preview_generation_identity_v3(
        {EVENT_ID: first},
        first_index,
        "2026-07-30T20:31:05Z",
    )
    second_id = preview_generation_identity_v3(
        {EVENT_ID: second},
        second_index,
        "2026-07-30T20:31:05Z",
    )

    assert first_id != second_id


def test_revision_index_must_cover_every_current_manifest_workspace(tmp_path: Path) -> None:
    workspace = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    _generation_dir, manifest, index = _mint(
        tmp_path,
        workspace,
        generated_at="2026-07-30T20:31:05Z",
    )
    other_event = "evt_cik0000882184_2026q3_results"
    forged = json.loads(json.dumps(manifest))
    forged["files"][f"workspaces/{other_event}.json"] = {
        "bytes": 1,
        "sha256": "f" * 64,
    }
    forged["event_count"] = 2
    validate_workspace_manifest(forged)

    with pytest.raises(WorkspaceError, match="cover"):
        validate_revision_index(index, manifest=forged)


def test_v3_reader_does_not_fetch_unrelated_current_workspaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_event_id = "evt_cik0000320193_2026q4_results"
    first = _workspace(
        source_sha256="a" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-07-30T20:31:00Z",
    )
    other = json.loads(json.dumps(first))
    other["event_id"] = other_event_id
    other["aliases"] = ["AAPL/2026Q4"]
    other["fiscal_period"]["quarter"] = 4
    other["facts"][0]["period"] = "2026Q4"

    first_workspaces = {EVENT_ID: first, other_event_id: other}
    first_index = build_revision_index(first_workspaces)
    first_dir = write_workspace_generation_v3(
        tmp_path,
        first_workspaces,
        revision_index=first_index,
        generated_at="2026-07-30T20:31:05Z",
    )
    first_manifest, first_index = _read_generation(first_dir)

    corrected = _workspace(
        source_sha256="b" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-09-18T20:56:33Z",
        state="corrected",
        fact_value=101,
    )
    second_workspaces = {EVENT_ID: corrected, other_event_id: other}
    second_index = build_revision_index(
        second_workspaces,
        previous_index=first_index,
        previous_manifest=first_manifest,
    )
    second_dir = write_workspace_generation_v3(
        tmp_path,
        second_workspaces,
        revision_index=second_index,
        generated_at="2026-09-18T20:57:00Z",
        previous_generation_id=first_dir.name,
        previous_manifest_sha256=_manifest_sha(first_dir),
    )

    fetch_calls: list[str] = []
    monkeypatch.setattr(
        reader,
        "_fetch_bytes",
        _v3_server(
            [first_dir, second_dir],
            current=second_dir,
            fetch_calls=fetch_calls,
        ),
    )

    revisions = reader.read_event_source_revisions(EVENT_ID, base_url=BASE)

    assert [item["source_sha256"] for item in revisions] == ["a" * 64, "b" * 64]
    unrelated_current = (
        f"{BASE}/event_workspaces/generations/{second_dir.name}/"
        f"workspaces/{other_event_id}.json"
    )
    assert unrelated_current not in fetch_calls

def test_legacy_seed_uses_migration_mint_for_collapsed_historical_clock() -> None:
    mint = "2026-09-19T12:00:00Z"
    revisions = []
    specs = (
        ("1" * 24, "a" * 64, "2026-07-30T20:31:00Z", "2026-07-30T20:31:05Z", "complete", 100),
        ("2" * 24, "b" * 64, "2026-09-18T20:56:33Z", "2026-07-30T20:31:05Z", "corrected", 101),
        ("3" * 24, "c" * 64, "2026-09-19T04:41:41Z", "2026-07-30T20:31:05Z", "corrected", 102),
    )
    current = None
    for generation_id, source_sha, observed_at, generated_at, state, value in specs:
        workspace = _workspace(
            source_sha256=source_sha,
            source_available_at="2026-07-30T20:30:28Z",
            observed_at=observed_at,
            state=state,
            fact_value=value,
        )
        workspace["generation_id"] = generation_id
        workspace["generated_at"] = generated_at
        revisions.append({
            "generation_id": generation_id,
            "source_sha256": source_sha,
            "source_available_at": "2026-07-30T20:30:28Z",
            "observed_at": observed_at,
            "lifecycle_state": state,
            "form": "8-K",
            "workspace_receipt": {"bytes": 100 + value, "sha256": source_sha},
            "workspace": workspace,
        })
        current = workspace

    index = build_revision_index_from_legacy(
        {EVENT_ID: current},
        {EVENT_ID: revisions},
        current_generation_id="3" * 24,
        migration_generated_at=mint,
    )
    first, corrected, current_row = index["events"][EVENT_ID]
    assert first["generated_at"] == "2026-07-30T20:31:05Z"
    assert first["generated_at_basis"] == "WORKSPACE_ENVELOPE"
    assert corrected["generated_at"] == mint
    assert corrected["generated_at_basis"] == "V3_MIGRATION_MINT"
    assert current_row["workspace_generation_ref"] == "self"
    assert current_row["generated_at"] is None
    assert current_row["generated_at_basis"] == "ENCLOSING_MANIFEST"


def test_legacy_seed_rejects_migration_mint_before_collapsed_observation() -> None:
    workspace = _workspace(
        source_sha256="b" * 64,
        source_available_at="2026-07-30T20:30:28Z",
        observed_at="2026-09-18T20:56:33Z",
        state="corrected",
        fact_value=101,
    )
    workspace["generation_id"] = "2" * 24
    workspace["generated_at"] = "2026-07-30T20:31:05Z"
    revision = {
        "generation_id": "2" * 24,
        "source_sha256": "b" * 64,
        "source_available_at": "2026-07-30T20:30:28Z",
        "observed_at": "2026-09-18T20:56:33Z",
        "lifecycle_state": "corrected",
        "form": "8-K",
        "workspace_receipt": {"bytes": 201, "sha256": "b" * 64},
        "workspace": workspace,
    }
    with pytest.raises(WorkspaceError, match="migration mint"):
        build_revision_index_from_legacy(
            {EVENT_ID: workspace},
            {EVENT_ID: [revision]},
            current_generation_id="f" * 24,
            migration_generated_at="2026-09-17T20:56:33Z",
        )

def test_v3_reader_carries_migration_clock_without_rewriting_legacy_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collapsed = "2026-07-30T20:31:05Z"
    specs = (
        ("a" * 64, "2026-07-30T20:31:00Z", "complete", 100),
        ("b" * 64, "2026-09-18T20:56:33Z", "corrected", 101),
        ("c" * 64, "2026-09-19T04:41:41Z", "corrected", 102),
    )
    dirs = []
    revisions = []
    previous_id = None
    previous_sha = None
    current_workspace = None
    for source_sha, observed_at, state, value in specs:
        workspace = _workspace(
            source_sha256=source_sha,
            source_available_at="2026-07-30T20:30:28Z",
            observed_at=observed_at,
            state=state,
            fact_value=value,
        )
        generation = write_workspace_generation(
            tmp_path,
            {EVENT_ID: workspace},
            generated_at=collapsed,
            previous_generation_id=previous_id,
            previous_manifest_sha256=previous_sha,
        )
        manifest = json.loads((generation / "manifest.json").read_text())
        stored = json.loads(
            (generation / "workspaces" / f"{EVENT_ID}.json").read_text()
        )
        receipt = manifest["files"][f"workspaces/{EVENT_ID}.json"]
        revisions.append({
            "generation_id": generation.name,
            "source_sha256": source_sha,
            "source_available_at": "2026-07-30T20:30:28Z",
            "observed_at": observed_at,
            "lifecycle_state": state,
            "form": "8-K",
            "workspace_receipt": receipt,
            "workspace": stored,
        })
        dirs.append(generation)
        previous_id = generation.name
        previous_sha = _manifest_sha(generation)
        current_workspace = stored

    mint = "2026-09-19T12:00:00Z"
    index = build_revision_index_from_legacy(
        {EVENT_ID: current_workspace},
        {EVENT_ID: revisions},
        current_generation_id=dirs[-1].name,
        migration_generated_at=mint,
    )
    v3 = write_workspace_generation_v3(
        tmp_path,
        {EVENT_ID: current_workspace},
        revision_index=index,
        generated_at=mint,
        previous_generation_id=dirs[-1].name,
        previous_manifest_sha256=_manifest_sha(dirs[-1]),
    )
    fetch_calls: list[str] = []
    monkeypatch.setattr(
        reader,
        "_fetch_bytes",
        _v3_server([*dirs, v3], current=v3, fetch_calls=fetch_calls),
    )

    rows = reader.read_event_source_revisions(EVENT_ID, base_url=BASE)

    assert [row["source_sha256"] for row in rows] == [s[0] for s in specs]
    assert rows[0]["generated_at_basis"] == "WORKSPACE_ENVELOPE"
    assert rows[0]["generated_at"] == collapsed
    assert rows[1]["generated_at_basis"] == "V3_MIGRATION_MINT"
    assert rows[1]["generated_at"] == mint
    assert rows[1]["workspace"]["generated_at"] == collapsed
    assert rows[2]["generated_at_basis"] == "ENCLOSING_MANIFEST"
    assert rows[2]["generated_at"] == mint
    assert rows[2]["workspace"]["generated_at"] == mint


def test_revision_index_rejects_consecutive_duplicate_source_revision(
    tmp_path: Path,
) -> None:
    _first_dir, second_dir = _two_revision_v3_chain(tmp_path)
    manifest, revision_index = _read_generation(second_dir)
    duplicate = json.loads(json.dumps(revision_index["events"][EVENT_ID][0]))
    revision_index["events"][EVENT_ID].insert(1, duplicate)

    with pytest.raises(WorkspaceError, match="consecutive"):
        validate_revision_index(revision_index, manifest=manifest)
