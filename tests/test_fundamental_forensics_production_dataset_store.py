"""FIF D3 store tests: publication, A17 digest binding, A18 write-loss law.

All tests run against the in-memory strict conditional store double — never a
real bucket. The double refuses unconditional ``put_bytes`` so any accidental
fallback from the conditional-write law fails loudly.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics import production_datasets as PDS
from engine.fundamental_forensics.financial_intelligence_packet import EntityInput
from engine.fundamental_forensics.query_service import (
    CanonicalEntityBinding,
    fip1_fixture_dataset,
)

ROOT = Path(__file__).resolve().parents[1]

T_ADMITTED = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
T_FLOOR = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
T_LATER = T_ADMITTED + timedelta(days=2)

_FIP1_BINDING = CanonicalEntityBinding(
    entity_id="mmx.issuer.fip1",
    cik="0000999999",
    ticker="FIP1",
    source_entity_id="0000999999",
)
_FIP1_ENTITY = EntityInput(
    entity_id="mmx.issuer.fip1",
    cik="0000999999",
    ticker="FIP1",
    name="FIP1 Fixture",
    identity_basis="sec-cik",
    source_entity_id="0000999999",
)


def _material(*, admitted_at: datetime = T_ADMITTED) -> PDS.ProductionDatasetMaterial:
    base = fip1_fixture_dataset(ROOT)
    return PDS.ProductionDatasetMaterial(
        binding=_FIP1_BINDING,
        entity=_FIP1_ENTITY,
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=admitted_at,
        source_recorded_at_floor=T_FLOOR,
    )


def _publish(
    material: PDS.ProductionDatasetMaterial | None = None,
    store: PDS.InMemoryStrictConditionalStore | None = None,
) -> tuple[PDS.InMemoryStrictConditionalStore, PDS.ProductionDatasetPublication]:
    store = store if store is not None else PDS.InMemoryStrictConditionalStore()
    material = material if material is not None else _material()
    publication = PDS.publish_production_dataset(store, material)
    return store, publication


def _role_row(generation: PDS.ProductionDatasetGeneration, role: str) -> dict:
    return next(row for row in generation.manifest["objects"] if row["role"] == role)


# ---------------------------------------------------------------------------
# A17: a generation exists only when every component verifies
# ---------------------------------------------------------------------------


def test_generation_requires_all_role_objects_and_matching_digests() -> None:
    # Baseline: an intact publication loads and verifies.
    store, publication = _publish()
    generation = PDS.load_generation(store, "mmx.issuer.fip1", publication.generation_id)
    assert generation.generation_id == publication.generation_id

    # A missing role object is a hard failure, never a servable generation.
    store2, publication2 = _publish()
    generation2 = PDS.load_generation(store2, "mmx.issuer.fip1", publication2.generation_id)
    store2.drop(_role_row(generation2, "registry_json")["object_key"])
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_generation(store2, "mmx.issuer.fip1", publication2.generation_id)

    # A byte_length mismatch is a hard failure.
    store3, publication3 = _publish()
    generation3 = PDS.load_generation(store3, "mmx.issuer.fip1", publication3.generation_id)
    row3 = _role_row(generation3, "ledger_json")
    tampered = bytearray(store3.get_bytes(row3["object_key"]))
    tampered.extend(b" ")
    store3.raw_put(row3["object_key"], bytes(tampered))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_generation(store3, "mmx.issuer.fip1", publication3.generation_id)

    # A sha256 mismatch with unchanged length is a hard failure.
    store4, publication4 = _publish()
    generation4 = PDS.load_generation(store4, "mmx.issuer.fip1", publication4.generation_id)
    row4 = _role_row(generation4, "entity_json")
    payload4 = bytearray(store4.get_bytes(row4["object_key"]))
    payload4[0] = payload4[0] ^ 0x01
    store4.raw_put(row4["object_key"], bytes(payload4))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_generation(store4, "mmx.issuer.fip1", publication4.generation_id)

    # A truncated manifest is a hard failure.
    store5, publication5 = _publish()
    manifest_key5 = PDS.production_manifest_key("mmx.issuer.fip1", publication5.generation_id)
    truncated = store5.get_bytes(manifest_key5)[:10]
    store5.raw_put(manifest_key5, truncated)
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_generation(store5, "mmx.issuer.fip1", publication5.generation_id)

    # An inexact role set can never re-derive its own generation id.
    store6, publication6 = _publish()
    generation6 = PDS.load_generation(store6, "mmx.issuer.fip1", publication6.generation_id)
    manifest6 = dict(generation6.manifest)
    manifest6["objects"] = manifest6["objects"][:-1]
    store6.raw_put(
        PDS.production_manifest_key("mmx.issuer.fip1", publication6.generation_id),
        json.dumps(manifest6).encode("utf-8"),
    )
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_generation(store6, "mmx.issuer.fip1", publication6.generation_id)


def test_generation_id_binds_manifest_content() -> None:
    """Any byte change anywhere is a DIFFERENT generation id (A17)."""
    store1, publication1 = _publish(_material(admitted_at=T_ADMITTED))
    store2, publication2 = _publish(_material(admitted_at=T_LATER))
    assert publication1.generation_id != publication2.generation_id
    assert PDS.GENERATION_ID_RE.fullmatch(publication1.generation_id)
    assert publication1.generation_id.startswith("ffprods_")
    # latest advanced to the newer generation; the older one stays readable.
    latest = PDS.load_latest_generation(store2, "mmx.issuer.fip1")
    assert latest is not None and latest.generation_id == publication2.generation_id
    older = PDS.load_generation(store1, "mmx.issuer.fip1", publication1.generation_id)
    assert older.generation_id == publication1.generation_id


# ---------------------------------------------------------------------------
# A17/A18: create-only writes, read-back before pointer advance
# ---------------------------------------------------------------------------


def test_latest_pointer_advances_only_after_verified_writes() -> None:
    store, publication = _publish()
    generation = PDS.load_generation(store, "mmx.issuer.fip1", publication.generation_id)

    # Every immutable artifact was created conditionally (If-None-Match):
    # the six role objects, the manifest, and the pointer's first-ever CAS
    # (expected_version=None because no prior pointer exists).
    conditional_creates = [key for key, expected in store.conditional_writes if expected is None]
    assert len(conditional_creates) == len(generation.manifest["objects"]) + 2
    assert PDS.production_latest_key("mmx.issuer.fip1") in conditional_creates
    assert store.unconditional_writes == []

    # Idempotent republication: same bytes at the same keys succeeds without
    # any unconditional write and without moving latest.
    publication_again = PDS.publish_production_dataset(store, _material())
    assert publication_again.generation_id == publication.generation_id
    latest = PDS.load_latest_generation(store, "mmx.issuer.fip1")
    assert latest is not None and latest.generation_id == publication.generation_id

    # A create-only collision at the same key with DIFFERENT bytes is a hard
    # error, never an overwrite.
    hostile = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(hostile, _material())
    generation_h = PDS.load_latest_generation(hostile, "mmx.issuer.fip1")
    assert generation_h is not None
    manifest_key = PDS.production_manifest_key("mmx.issuer.fip1", generation_h.generation_id)
    good_bytes = hostile.get_bytes(manifest_key)
    hostile.drop(manifest_key)
    hostile.raw_put(manifest_key, good_bytes[:-1] + b"X")  # same key, different bytes
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.publish_production_dataset(hostile, _material())


# ---------------------------------------------------------------------------
# A18: EFFECT_UNKNOWN on the original target; newer pointer winners preserved
# ---------------------------------------------------------------------------


def test_ambiguous_write_preserves_effect_unknown_on_original_target() -> None:
    # 1. Conditional write RAISES after committing: same-carrier read-back
    #    reconciliation proves idempotent completion, and no unconditional
    #    write is ever attempted.
    store = PDS.InMemoryStrictConditionalStore()
    store.raise_on_conditional_after_commit = True
    publication = PDS.publish_production_dataset(store, _material())
    assert publication.generation_id
    assert store.unconditional_writes == []
    generation = PDS.load_latest_generation(store, "mmx.issuer.fip1")
    assert generation is not None and generation.generation_id == publication.generation_id

    # 2. Conditional write raises AND the object is absent on read-back: the
    #    effect on the ORIGINAL target stays unknown and the error class says
    #    so. Reconciliation (a re-run of publish) is the only remedy — the
    #    store never observed an unconditional write.
    store2 = PDS.InMemoryStrictConditionalStore()
    store2.raise_on_conditional_after_commit = True
    store2.drop_after_commit = True
    with pytest.raises(PDS.ProductionDatasetEffectUnknownError):
        PDS.publish_production_dataset(store2, _material())
    assert store2.unconditional_writes == []

    # 3. A store whose conditional writes fail outright cannot publish; the
    #    refusal class is EFFECT_UNKNOWN on the original target.
    class _RefusingStore(PDS.InMemoryStrictConditionalStore):
        def put_bytes_strict_conditional(
            self, key, data, *, expected_version, content_type="application/octet-stream"
        ):
            raise RuntimeError("write path down")

    with pytest.raises(PDS.ProductionDatasetEffectUnknownError):
        PDS.publish_production_dataset(_RefusingStore(), _material())

    # 4. A publish that dies mid-way (after the first generation is live)
    #    leaves the prior generation servable under the unchanged pointer.
    class _ManifestFails(PDS.InMemoryStrictConditionalStore):
        def __init__(self) -> None:
            super().__init__()
            self.armed = False

        def put_bytes_strict_conditional(
            self, key, data, *, expected_version, content_type="application/octet-stream"
        ):
            if self.armed and "/generations/" in key:
                raise RuntimeError("transport died before the manifest write")
            return super().put_bytes_strict_conditional(
                key, data, expected_version=expected_version, content_type=content_type
            )

    store4 = _ManifestFails()
    first = PDS.publish_production_dataset(store4, _material())
    store4.armed = True
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.publish_production_dataset(store4, _material(admitted_at=T_LATER))
    latest4 = PDS.load_latest_generation(store4, "mmx.issuer.fip1")
    assert latest4 is not None and latest4.generation_id == first.generation_id

    # 5. A newer concurrent pointer winner is preserved, never rewound.
    store5, newer = _publish(_material(admitted_at=T_LATER))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.publish_production_dataset(store5, _material(admitted_at=T_ADMITTED))
    latest5 = PDS.load_latest_generation(store5, "mmx.issuer.fip1")
    assert latest5 is not None and latest5.generation_id == newer.generation_id


# ---------------------------------------------------------------------------
# Pointer contract and material validation
# ---------------------------------------------------------------------------


def test_latest_pointer_is_absent_for_unknown_issuer() -> None:
    store, _ = _publish()
    assert PDS.load_latest_generation(store, "ISS:US-XNAS-NOPE") is None
    assert PDS.latest_generation_summary(store, "ISS:US-XNAS-NOPE") is None


def test_pointer_decode_is_fail_closed() -> None:
    # A pointer naming a foreign manifest key is malformed.
    store, publication = _publish()
    issuer = "mmx.issuer.fip1"
    pointer_key = PDS.production_latest_key(issuer)
    hostile = json.loads(store.get_bytes(pointer_key))
    hostile["manifest_key"] = "fundamental_forensics/production-datasets/v1/elsewhere.json"
    store.raw_put(pointer_key, json.dumps(hostile).encode("utf-8"))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_latest_generation(store, issuer)

    # A pointer naming a generation whose manifest is absent is a hard error,
    # never a silent miss.
    store2, publication2 = _publish()
    store2.drop(PDS.production_manifest_key(issuer, publication2.generation_id))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_latest_generation(store2, issuer)


def test_publication_requires_strict_conditional_store() -> None:
    class _LegacyStore:
        def get_bytes(self, key):
            return None

        def put_bytes(self, key, data, content_type="application/octet-stream"):
            return True

        def list_prefix(self, prefix):
            return []

        def exists(self, key):
            return False

        def upload_time(self, key):
            return None

    with pytest.raises(PDS.ProductionDatasetError):
        PDS.publish_production_dataset(_LegacyStore(), _material())


def test_material_validation_is_fail_closed() -> None:
    store = PDS.InMemoryStrictConditionalStore()
    # Entity disagreeing with the binding.
    bad_entity = EntityInput(
        entity_id="mmx.issuer.other",
        cik="0000999999",
        ticker="FIP1",
        name="FIP1 Fixture",
        identity_basis="sec-cik",
        source_entity_id="0000999999",
    )
    material = _material()
    object.__setattr__(material, "entity", bad_entity)
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.publish_production_dataset(store, material)
    # A naive (unaware) admission clock.
    material2 = _material()
    object.__setattr__(material2, "admitted_at", datetime(2026, 10, 1))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.publish_production_dataset(store, material2)
    # A recorded floor after admission.
    material3 = _material()
    object.__setattr__(material3, "source_recorded_at_floor", T_ADMITTED + timedelta(days=1))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.publish_production_dataset(store, material3)
    # A registry payload that cannot be rebuilt is refused before any write.
    material4 = _material()
    object.__setattr__(material4, "registry_payload", {"catalog": {}, "mappings": {}, "formulas": {}})
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.publish_production_dataset(store, material4)
    assert store.conditional_writes == []


# ---------------------------------------------------------------------------
# FIF P1: the additive statement_trees_json role (publish-time precompute)
# ---------------------------------------------------------------------------


def _aapl_packages_material() -> PDS.ProductionDatasetMaterial:
    from engine.fundamental_forensics.ixbrl_raw_ledger import (
        GOLDEN_AAPL_QUERY_ACCESSIONS,
        parse_and_convert_golden_packages,
    )
    from engine.fundamental_forensics.statement_graph import load_golden_aapl_package

    packages = [
        load_golden_aapl_package(ROOT, accession=accession)
        for accession in GOLDEN_AAPL_QUERY_ACCESSIONS
    ]
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    return PDS.ProductionDatasetMaterial(
        binding=CanonicalEntityBinding(
            entity_id="ISS:US-XNAS-AAPL",
            cik="0000320193",
            ticker="AAPL",
            source_entity_id="0000320193",
        ),
        entity=EntityInput(
            entity_id="ISS:US-XNAS-AAPL",
            cik="0000320193",
            ticker="AAPL",
            name="Apple Inc.",
            identity_basis="sec-cik",
            source_entity_id="0000320193",
        ),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=T_ADMITTED,
        packages=tuple(packages),
        security_id="SEC:US-XNAS-AAPL",
        listing_key="US-XNAS-AAPL",
    )


def test_statement_trees_role_is_additive_digest_bound_and_required_when_packages_exist() -> None:
    # Package-less publication: exactly the D3 six-role core, byte-for-byte
    # the same manifest shape (and generation id space) as before P1.
    store1, publication1 = _publish()
    generation1 = PDS.load_generation(store1, "mmx.issuer.fip1", publication1.generation_id)
    assert [row["role"] for row in generation1.manifest["objects"]] == list(
        PDS.PRODUCTION_DATASET_ROLES
    )
    with pytest.raises(PDS.ProductionDatasetError):
        generation1.statement_trees("0000320193-25-000079")

    # Package-carrying publication: the optional role is admitted, content-
    # addressed, and digest-bound exactly like the core roles.
    store2 = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store2, _aapl_packages_material())
    generation2 = PDS.load_latest_generation(store2, "ISS:US-XNAS-AAPL")
    assert generation2 is not None
    assert [row["role"] for row in generation2.manifest["objects"]] == [
        *PDS.PRODUCTION_DATASET_ROLES,
        *PDS.OPTIONAL_PRODUCTION_DATASET_ROLES,
    ]
    row = next(r for r in generation2.manifest["objects"] if r["role"] == "statement_trees_json")
    payload = store2.get_bytes(row["object_key"])
    assert payload is not None
    assert len(payload) == row["byte_length"]
    assert hashlib.sha256(payload).hexdigest() == row["sha256"]
    assert row["object_key"] == PDS.production_object_key(row["sha256"])
    trees = generation2.statement_trees("0000320193-25-000079")
    assert len(trees["statements"]) == 3
    with pytest.raises(PDS.ProductionDatasetError):
        generation2.statement_trees("0000320193-99-999999")

    # Damage classes: a dropped object or tampered bytes refuse the whole
    # generation at load (A17); a tree-less payload refuses the accessor.
    store2.drop(row["object_key"])
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_latest_generation(store2, "ISS:US-XNAS-AAPL")

    store3 = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store3, _aapl_packages_material())
    generation3 = PDS.load_latest_generation(store3, "ISS:US-XNAS-AAPL")
    assert generation3 is not None
    row3 = next(r for r in generation3.manifest["objects"] if r["role"] == "statement_trees_json")
    tampered = bytearray(store3.get_bytes(row3["object_key"]))
    tampered[0] = tampered[0] ^ 0x01
    store3.raw_put(row3["object_key"], bytes(tampered))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_latest_generation(store3, "ISS:US-XNAS-AAPL")


# ---------------------------------------------------------------------------
# A17: a failed component never completes a generation; a stale generation
# never rewinds latest
# ---------------------------------------------------------------------------


class _ReadBackLiesStore(PDS.InMemoryStrictConditionalStore):
    """Accepts every create but echoes different bytes for one key."""

    def __init__(self, lying_key: str) -> None:
        super().__init__()
        self._lying_key = lying_key

    def get_bytes_strict_bounded(self, key: str, maximum_bytes: int) -> bytes | None:
        payload = super().get_bytes_strict_bounded(key, maximum_bytes)
        if key == self._lying_key and payload:
            return payload[:-1] + bytes([payload[-1] ^ 0x01])
        return payload


def _role_keys() -> dict[str, str]:
    probe, publication = _publish()
    generation = PDS.load_generation(probe, "mmx.issuer.fip1", publication.generation_id)
    return {row["role"]: row["object_key"] for row in generation.manifest["objects"]}


def _manifest_keys(store: PDS.InMemoryStrictConditionalStore) -> list[str]:
    return [key for key in store.list_prefix("") if "/generations/" in key]


def test_a17_component_collision_leaves_no_manifest_and_no_latest() -> None:
    keys = _role_keys()
    for role in ("ledger_json", "registry_json", "lineage_evidence_json"):
        store = PDS.InMemoryStrictConditionalStore()
        store.raw_put(keys[role], b'{"planted":"different bytes"}')
        with pytest.raises(PDS.ProductionDatasetError, match="collision"):
            PDS.publish_production_dataset(store, _material())
        assert _manifest_keys(store) == [], role
        assert store.get_bytes(PDS.production_latest_key("mmx.issuer.fip1")) is None, role
        assert PDS.load_latest_generation(store, "mmx.issuer.fip1") is None, role


def test_a17_read_back_mismatch_is_not_completion() -> None:
    store = _ReadBackLiesStore(_role_keys()["entity_json"])
    with pytest.raises(PDS.ProductionDatasetError, match="read-back mismatch"):
        PDS.publish_production_dataset(store, _material())
    assert _manifest_keys(store) == []
    assert store.get_bytes(PDS.production_latest_key("mmx.issuer.fip1")) is None


def test_a17_stale_generation_is_kept_by_id_but_never_rewinds_latest() -> None:
    store, newer = _publish(_material(admitted_at=T_LATER))
    with pytest.raises(PDS.ProductionDatasetError, match="cannot rewind"):
        PDS.publish_production_dataset(store, _material(admitted_at=T_ADMITTED))
    latest = PDS.load_latest_generation(store, "mmx.issuer.fip1")
    assert latest is not None and latest.generation_id == newer.generation_id
    # The stale generation's objects and manifest were written and verified
    # before the pointer refused, so it stays loadable by exact id for audit.
    stale_id = PDS.publish_production_dataset(
        PDS.InMemoryStrictConditionalStore(), _material(admitted_at=T_ADMITTED), skip_pointer=True
    ).generation_id
    assert PDS.load_generation(store, "mmx.issuer.fip1", stale_id).generation_id == stale_id
    assert stale_id != newer.generation_id

    # An equal admission clock is stale too: a different generation admitted
    # at the same instant cannot replace latest.
    store2, first = _publish(_material(admitted_at=T_ADMITTED))
    rival = dataclasses.replace(_material(admitted_at=T_ADMITTED), source_recorded_at_floor=T_FLOOR + timedelta(days=1))
    with pytest.raises(PDS.ProductionDatasetError, match="cannot rewind"):
        PDS.publish_production_dataset(store2, rival)
    latest2 = PDS.load_latest_generation(store2, "mmx.issuer.fip1")
    assert latest2 is not None and latest2.generation_id == first.generation_id
