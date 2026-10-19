"""Fail-closed proofs for bounded institutional 13F catalog accession scopes.

Every test runs against the native canonical K3E fixture world (real owner
``prepare_catalog_generation``/``publish_catalog_generation`` publication over
a local strict store) and proves the narrow-scope contract: one manifest, one
pointer read in pointer mode only, exactly the five selected artifacts, the
same rows as the full canonical load, and typed catalog errors for every
corruption, cutoff, and bound overflow.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

import engine.institutional_census.catalog_scope as catalog_scope
from engine.institutional_census.catalog import (
    HOLDING_BUCKET_ROLES,
    Institutional13FCatalogError,
    PublishedCatalogGeneration,
    catalog_pointer_key,
    holding_bucket_role,
    load_catalog_generation,
)
from engine.institutional_census.catalog_scope import (
    CatalogScopeNotAvailableAtCutoff,
    VerifiedCatalogAccessionScope,
    load_catalog_accession_scope,
)
from engine.institutional_census.models import Institutional13FError, utc_datetime
from engine.research_vault.r2_store import LocalStore
from lib.institutional_13f_adapter import select_effective_filing, select_security_row
from tests.test_institutional_census_k3e_projection import (
    ACCESSION,
    CUSIP,
    DECISION_CUTOFF,
    FILER_CIK,
    PUBLISHED_AT,
    REPORT_PERIOD,
    _world,
)

_SELECTED_ROLES = (
    "filings_parquet",
    holding_bucket_role(ACCESSION),
    "manager_relationships_parquet",
    "source_receipts_json",
    "coverage_json",
)


class _RecordingStore(LocalStore):
    """LocalStore that records every bounded-read key for narrowness proofs."""

    def __init__(self, root):
        super().__init__(root)
        self.bounded_read_keys: list[str] = []

    def get_bytes_strict_bounded(self, key, maximum_bytes=None, **kwargs):
        self.bounded_read_keys.append(str(key))
        return super().get_bytes_strict_bounded(key, maximum_bytes, **kwargs)


def _recording(world_store) -> _RecordingStore:
    return _RecordingStore(world_store.root)


def _descriptors(generation):
    return {item.role: item for item in generation.manifest.artifacts}


def _artifact_reads(read_keys, generation):
    keys = {item.object_key for item in generation.manifest.artifacts}
    return [key for key in read_keys if key in keys]


def _scope(store, **overrides):
    args = dict(
        report_period=REPORT_PERIOD,
        accession=ACCESSION,
        decision_cutoff=DECISION_CUTOFF,
    )
    args.update(overrides)
    return load_catalog_accession_scope(store, **args)


def _manager_row(accession=ACCESSION, sequence=1, ordinal=0):
    return {
        "accession": accession,
        "relationship_kind": "included_manager",
        "source_table": "OTHERMANAGER2",
        "manager_sequence": sequence,
        "other_manager_sk": ordinal,
        "manager_cik": "0000000002",
        "manager_name": "Reported manager",
        "form13f_file_number": "028-00002",
        "crd_number": "000000002",
        "sec_file_number": "801-000002",
    }


def test_scope_matches_full_generation_and_downloads_only_one_bucket(tmp_path):
    world_store, generation = _world(tmp_path)
    store = _recording(world_store)

    scope = _scope(store)
    scope_reads = list(store.bounded_read_keys)
    store.bounded_read_keys.clear()
    full = load_catalog_generation(store, report_period=REPORT_PERIOD)

    assert isinstance(scope, VerifiedCatalogAccessionScope)
    assert not isinstance(scope, PublishedCatalogGeneration)
    assert scope.generation_id == generation.generation_id == full.generation_id
    assert scope.manifest == full.manifest
    assert scope.current_generation_id == full.current_generation_id
    assert scope.pointer_read is True
    assert scope.superseded is False
    assert scope.validation_scope == "accession_bucket"
    with pytest.raises(dataclasses.FrozenInstanceError):
        scope.accession = "0000000009-26-000009"

    # Pointer mode: the pointer and the exact manifest once each, then exactly
    # the five selected artifacts -- and exactly one holdings bucket key.
    assert scope_reads.count(catalog_pointer_key(REPORT_PERIOD)) == 1
    assert scope_reads.count(generation.manifest.manifest_key) == 1
    artifact_reads = _artifact_reads(scope_reads, generation)
    assert len(artifact_reads) == 5
    bucket_keys = {
        item.object_key
        for item in generation.manifest.artifacts
        if item.role in HOLDING_BUCKET_ROLES
    }
    assert [key for key in artifact_reads if key in bucket_keys] == [
        _descriptors(generation)[holding_bucket_role(ACCESSION)].object_key
    ]
    assert scope.validated_roles == _SELECTED_ROLES

    # Same verified rows as the full canonical load, narrowed to the accession.
    assert list(scope.filings) == list(full.filings)
    assert list(scope.holdings) == [
        row for row in full.holdings if row["accession"] == ACCESSION
    ]
    assert list(scope.manager_relationships) == [
        row for row in full.manager_relationships if row["accession"] == ACCESSION
    ]
    assert [row["infotable_sk"] for row in scope.holdings] == [7]


def test_explicit_generation_scope_never_reads_the_pointer(tmp_path):
    world_store, generation = _world(tmp_path)
    store = _recording(world_store)

    scope = _scope(store, generation_id=generation.generation_id)

    assert catalog_pointer_key(REPORT_PERIOD) not in store.bounded_read_keys
    assert store.bounded_read_keys.count(generation.manifest.manifest_key) == 1
    assert len(_artifact_reads(store.bounded_read_keys, generation)) == 5
    assert scope.generation_id == generation.generation_id
    assert scope.current_generation_id is None
    assert scope.pointer_read is False
    assert scope.superseded is False


def test_scope_is_a_drop_in_for_existing_owner_helpers(tmp_path):
    world_store, generation = _world(tmp_path)
    scope = _scope(_recording(world_store))
    cutoff = utc_datetime(DECISION_CUTOFF, field="decision_cutoff")

    filing = select_effective_filing(
        scope, filer_cik=FILER_CIK, report_period=REPORT_PERIOD, cutoff=cutoff
    )
    expected = select_effective_filing(
        generation, filer_cik=FILER_CIK, report_period=REPORT_PERIOD, cutoff=cutoff
    )
    assert dict(filing) == dict(expected)
    assert filing["accession"] == ACCESSION

    row, quantity = select_security_row(scope, accession=ACCESSION, cusip=CUSIP)
    expected_row, expected_quantity = select_security_row(
        generation, accession=ACCESSION, cusip=CUSIP
    )
    assert dict(row) == dict(expected_row)
    assert quantity == expected_quantity == 125000


def test_scope_keeps_full_filing_lineage_but_only_accession_rows(tmp_path):
    second_accession = "0000000002-26-000001"
    world_store, generation = _world(
        tmp_path,
        manager_relationships=[
            _manager_row(sequence=1, ordinal=0),
            _manager_row(accession=second_accession, sequence=1, ordinal=2),
        ],
        second_filer=True,
    )
    scope = _scope(_recording(world_store))

    assert {str(row["accession"]) for row in scope.filings} == {
        ACCESSION,
        second_accession,
    }
    assert len(scope.filings) == len(generation.filings) == 2
    assert {str(row["accession"]) for row in scope.holdings} == {ACCESSION}
    assert {str(row["accession"]) for row in scope.manager_relationships} == {ACCESSION}
    assert len(scope.manager_relationships) == 1


@pytest.mark.parametrize("role", _SELECTED_ROLES)
def test_missing_selected_artifact_fails_closed_without_fallback(tmp_path, role):
    world_store, generation = _world(tmp_path)
    (world_store.root / _descriptors(generation)[role].object_key).unlink()

    with pytest.raises(Institutional13FCatalogError) as excinfo:
        _scope(world_store)

    assert "required object is missing" in str(excinfo.value)


@pytest.mark.parametrize("role", _SELECTED_ROLES)
def test_tampered_selected_artifact_fails_closed_on_digest(tmp_path, role):
    world_store, generation = _world(tmp_path)
    path = world_store.root / _descriptors(generation)[role].object_key
    payload = path.read_bytes()
    middle = len(payload) // 2
    path.write_bytes(payload[:middle] + bytes([payload[middle] ^ 0x01]) + payload[middle + 1:])

    with pytest.raises(Institutional13FCatalogError) as excinfo:
        _scope(world_store)

    assert "digest or byte length mismatch" in str(excinfo.value)


def test_pointer_mode_rejects_manifest_not_bound_by_pointer_before_sources(tmp_path):
    world_store, generation = _world(tmp_path)
    store = _recording(world_store)
    manifest_path = world_store.root / generation.manifest.manifest_key
    payload = manifest_path.read_bytes()
    manifest_path.write_bytes(payload[:-1] + b"x")

    with pytest.raises(Institutional13FCatalogError) as excinfo:
        _scope(store)

    assert "catalog pointer manifest hash or length is invalid" in str(excinfo.value)
    assert _artifact_reads(store.bounded_read_keys, generation) == []

    # Explicit mode binds the content-derived generation identity instead and
    # still fails closed on the same corruption without any pointer read.
    store.bounded_read_keys.clear()
    with pytest.raises(Institutional13FCatalogError):
        _scope(store, generation_id=generation.generation_id)
    assert catalog_pointer_key(REPORT_PERIOD) not in store.bounded_read_keys


def test_scope_refuses_generation_published_after_cutoff_before_downloads(tmp_path):
    world_store, generation = _world(tmp_path)
    store = _recording(world_store)

    with pytest.raises(CatalogScopeNotAvailableAtCutoff) as excinfo:
        _scope(store, decision_cutoff="2026-05-16T11:59:59Z")

    assert isinstance(excinfo.value, Institutional13FCatalogError)
    assert generation.generation_id in str(excinfo.value)
    assert _artifact_reads(store.bounded_read_keys, generation) == []
    assert store.bounded_read_keys.count(catalog_pointer_key(REPORT_PERIOD)) == 1

    store.bounded_read_keys.clear()
    with pytest.raises(CatalogScopeNotAvailableAtCutoff):
        _scope(
            store,
            generation_id=generation.generation_id,
            decision_cutoff=datetime(2026, 5, 16, 11, 59, 59, tzinfo=timezone.utc),
        )
    assert _artifact_reads(store.bounded_read_keys, generation) == []

    # A generation published exactly at the cutoff is knowable; a naive clock
    # is an invalid cutoff, not a cutoff absence.
    assert _scope(world_store, decision_cutoff=PUBLISHED_AT) is not None
    with pytest.raises(Institutional13FError) as excinfo:
        _scope(world_store, decision_cutoff="2026-05-16T12:00:00")
    assert "explicit UTC offset" in str(excinfo.value)


def test_selected_row_count_bound_fails_closed_before_downloads(tmp_path, monkeypatch):
    world_store, generation = _world(tmp_path)
    store = _recording(world_store)
    monkeypatch.setattr(catalog_scope, "SCOPE_MAX_SELECTED_ROW_COUNT", 0)

    with pytest.raises(Institutional13FCatalogError) as excinfo:
        _scope(store)

    assert "interactive row bound" in str(excinfo.value)
    assert _artifact_reads(store.bounded_read_keys, generation) == []


def test_selected_artifact_byte_bound_fails_closed_before_downloads(tmp_path, monkeypatch):
    world_store, generation = _world(tmp_path)
    store = _recording(world_store)
    monkeypatch.setattr(catalog_scope, "SCOPE_MAX_SELECTED_ARTIFACT_BYTES", 1)

    with pytest.raises(Institutional13FCatalogError) as excinfo:
        _scope(store)

    assert "interactive byte bound" in str(excinfo.value)
    assert _artifact_reads(store.bounded_read_keys, generation) == []


def test_parquet_row_group_byte_bound_fails_closed_before_decode(tmp_path, monkeypatch):
    world_store, generation = _world(tmp_path)
    store = _recording(world_store)
    monkeypatch.setattr(catalog_scope, "SCOPE_MAX_SELECTED_PARQUET_ROW_GROUP_BYTES", 1)

    with pytest.raises(Institutional13FCatalogError) as excinfo:
        _scope(store)

    assert "row-group byte bound" in str(excinfo.value)
    parquet_keys = {
        _descriptors(generation)[role].object_key
        for role in (
            "filings_parquet",
            holding_bucket_role(ACCESSION),
            "manager_relationships_parquet",
        )
    }
    assert parquet_keys <= set(_artifact_reads(store.bounded_read_keys, generation))


def test_unrelated_bucket_corruption_does_not_masquerade_as_verification(tmp_path):
    world_store, generation = _world(tmp_path)
    target_role = holding_bucket_role(ACCESSION)
    other = next(
        item
        for item in generation.manifest.artifacts
        if item.role in HOLDING_BUCKET_ROLES and item.role != target_role
    )
    path = world_store.root / other.object_key
    path.write_bytes(path.read_bytes() + b"corrupt")

    # The full canonical loader verifies every bucket and therefore rejects.
    with pytest.raises(Institutional13FCatalogError):
        load_catalog_generation(world_store, report_period=REPORT_PERIOD)

    # The accession scope only ever claimed its own narrow selection.
    scope = _scope(world_store)
    assert scope.validation_scope == "accession_bucket"
    assert set(scope.validated_roles) == {
        "filings_parquet",
        target_role,
        "manager_relationships_parquet",
        "source_receipts_json",
        "coverage_json",
    }
    assert scope.generation_id == generation.generation_id
    assert [row["infotable_sk"] for row in scope.holdings] == [7]


def test_scope_requires_strict_store_and_valid_identity_inputs(tmp_path):
    world_store, generation = _world(tmp_path)

    with pytest.raises(Institutional13FCatalogError) as excinfo:
        load_catalog_accession_scope(
            generation,
            report_period=REPORT_PERIOD,
            accession=ACCESSION,
            decision_cutoff=DECISION_CUTOFF,
        )
    assert "StrictBoundedReadStore" in str(excinfo.value)

    with pytest.raises(Institutional13FError):
        _scope(world_store, accession="not-an-accession")
    with pytest.raises(Institutional13FError):
        _scope(world_store, report_period="2026-13-40")
    with pytest.raises(Institutional13FError):
        _scope(world_store, generation_id="not-a-generation-id")
    with pytest.raises(Institutional13FCatalogError):
        _scope(world_store, generation_id="i13fgen_" + "0" * 64)


def test_scope_dataclass_rejects_impossible_construction(tmp_path):
    world_store, _ = _world(tmp_path)
    scope = _scope(world_store)
    kwargs = dict(
        manifest=scope.manifest,
        accession=ACCESSION,
        filings=(),
        holdings=(),
        manager_relationships=(),
        validated_roles=("filings_parquet",),
    )

    with pytest.raises(Institutional13FCatalogError):
        VerifiedCatalogAccessionScope(**kwargs, validation_scope="whole_generation")
    with pytest.raises(Institutional13FCatalogError):
        VerifiedCatalogAccessionScope(
            **{**kwargs, "validated_roles": ("filings_parquet", "filings_parquet")}
        )
    with pytest.raises(Institutional13FCatalogError):
        VerifiedCatalogAccessionScope(**kwargs, superseded=True)
    with pytest.raises(Institutional13FCatalogError):
        VerifiedCatalogAccessionScope(
            **kwargs, current_generation_id="i13fgen_" + "a" * 64
        )
    with pytest.raises(Institutional13FCatalogError):
        VerifiedCatalogAccessionScope(**kwargs, current_generation_id=scope.generation_id)
    with pytest.raises(Institutional13FCatalogError):
        VerifiedCatalogAccessionScope(**kwargs, pointer_read=True)

    # The 18-digit accession form normalizes into the same scope identity.
    assert _scope(world_store, accession="000000000126000001") == scope
