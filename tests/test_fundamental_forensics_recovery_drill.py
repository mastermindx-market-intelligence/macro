"""FIF V0-b recovery drill tests: A47 restart/restore/rollback, A18 write loss.

Scenarios run against the in-memory strict conditional store double, a real
local-directory store, or both. Fault injection uses the double's test-only
hooks (``raw_put``/``drop``/the commit-phase flags) and small subclasses —
the frozen owner module ``production_datasets.py`` is never edited.
"""
from __future__ import annotations

import functools
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics import production_datasets as PDS
from engine.fundamental_forensics import recovery_drill as RD
from engine.fundamental_forensics.financial_intelligence_packet import EntityInput
from engine.fundamental_forensics.query_service import (
    CanonicalEntityBinding,
    fip1_fixture_dataset,
)

ROOT = Path(__file__).resolve().parents[1]

ISSUER = "mmx.issuer.fip1"
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


# Minimum fixture code, copied from
# tests/test_fundamental_forensics_production_dataset_store.py (not imported).
def _material(
    *,
    admitted_at: datetime = T_ADMITTED,
    supersedes: str | None = None,
) -> PDS.ProductionDatasetMaterial:
    base = fip1_fixture_dataset(ROOT)
    return PDS.ProductionDatasetMaterial(
        binding=_FIP1_BINDING,
        entity=_FIP1_ENTITY,
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=admitted_at,
        source_recorded_at_floor=T_FLOOR,
        supersedes_generation=supersedes,
    )


def _local_store(tmp_path: Path, name: str):
    directory = tmp_path / name
    directory.mkdir(parents=True, exist_ok=True)
    return PDS.build_production_dataset_store(local_dir=directory)


def _make_store(kind: str, tmp_path: Path, name: str):
    if kind == "memory":
        return PDS.InMemoryStrictConditionalStore()
    return _local_store(tmp_path, name)


def _entries_by_role(manifest: RD.BackupManifest) -> dict[str, list[RD.BackupEntry]]:
    out: dict[str, list[RD.BackupEntry]] = {}
    for entry in manifest.entries:
        out.setdefault(entry.role, []).append(entry)
    return out


@functools.lru_cache(maxsize=1)
def _baseline_generation_id() -> str:
    """The deterministic generation id of the baseline material (A17)."""
    scratch = PDS.InMemoryStrictConditionalStore()
    return PDS.publish_production_dataset(scratch, _material()).generation_id


class _CountingStore:
    """Delegating store proxy that records every write-path call.

    Proves the read-only drill functions (``audit_issuer``,
    ``reconcile_effect_unknown``) and the already-present restore path perform
    zero writes.
    """

    def __init__(self, inner) -> None:
        self._inner = inner
        self.conditional_puts: list[tuple[str, str | None]] = []
        self.unconditional_puts: list[str] = []

    # -- read protocol (delegated verbatim, VersionedBytes pass through) ------
    def get_bytes(self, key: str):
        return self._inner.get_bytes(key)

    def get_bytes_strict(self, key: str):
        return self._inner.get_bytes_strict(key)

    def get_bytes_strict_bounded(self, key: str, maximum_bytes: int):
        return self._inner.get_bytes_strict_bounded(key, maximum_bytes)

    def get_bytes_strict_bounded_versioned(self, key: str, maximum_bytes: int):
        return self._inner.get_bytes_strict_bounded_versioned(key, maximum_bytes)

    def list_prefix(self, prefix: str):
        return self._inner.list_prefix(prefix)

    def exists(self, key: str):
        return self._inner.exists(key)

    def upload_time(self, key: str):
        return self._inner.upload_time(key)

    # -- write protocol (counted) ----------------------------------------------
    def put_bytes_strict_conditional(
        self, key: str, data: bytes, *, expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        self.conditional_puts.append((key, expected_version))
        return self._inner.put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        self.unconditional_puts.append(key)
        return self._inner.put_bytes(key, data, content_type=content_type)

    def assert_zero_writes(self) -> None:
        assert self.conditional_puts == []
        assert self.unconditional_puts == []


class _LostPointerResponseStore(PDS.InMemoryStrictConditionalStore):
    """A18 double: the pointer CAS response is lost, the commit lands late.

    The conditional put for the issuer's latest pointer records the payload and
    raises a transport timeout; the commit happens only when the test flushes.
    That is the "write response lost, immediate absence or delayed commit"
    class: the publish cannot prove the outcome, yet the write may land after
    the read-back. Every other write behaves normally.
    """

    def __init__(self) -> None:
        super().__init__()
        self.pending: list[tuple[str, bytes]] = []
        self.lose_pointer_response = False

    def put_bytes_strict_conditional(
        self, key: str, data: bytes, *, expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        if self.lose_pointer_response and key == PDS.production_latest_key(ISSUER):
            self.pending.append((key, bytes(data)))
            self.lose_pointer_response = False
            raise RuntimeError("pointer response lost; commit may be delayed")
        return super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )

    def flush_delayed_commit(self) -> None:
        for key, payload in self.pending:
            self.raw_put(key, payload)
        self.pending.clear()


class _OneByteCorruptingStore(PDS.InMemoryStrictConditionalStore):
    """Restore-target double: one object byte lands damaged in the target."""

    def __init__(self, key: str) -> None:
        super().__init__()
        self._key = key

    def put_bytes_strict_conditional(
        self, key: str, data: bytes, *, expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        if key == self._key:
            damaged = bytearray(data)
            damaged[-1] = damaged[-1] ^ 0x01
            data = bytes(damaged)
        return super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )


class _CommitThenLoseResponseStore(PDS.InMemoryStrictConditionalStore):
    """Restore double: one key's conditional put COMMITS, then the response is lost."""

    def __init__(self, key: str) -> None:
        super().__init__()
        self._key = key

    def put_bytes_strict_conditional(
        self, key: str, data: bytes, *, expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        committed = super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )
        if key == self._key:
            raise RuntimeError("response lost after commit")
        return committed


class _CommitThenDenyStore(PDS.InMemoryStrictConditionalStore):
    """Restore double: one key's conditional put COMMITS but returns False."""

    def __init__(self, key: str) -> None:
        super().__init__()
        self._key = key

    def put_bytes_strict_conditional(
        self, key: str, data: bytes, *, expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        committed = super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )
        if key == self._key:
            return False
        return committed


class _UnlistableStore:
    """Read-protocol store double with NO list surface (the typed listing gap)."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def get_bytes(self, key: str):
        return self._inner.get_bytes(key)

    def get_bytes_strict(self, key: str):
        return self._inner.get_bytes_strict(key)

    def get_bytes_strict_bounded(self, key: str, maximum_bytes: int):
        return self._inner.get_bytes_strict_bounded(key, maximum_bytes)

    def get_bytes_strict_bounded_versioned(self, key: str, maximum_bytes: int):
        return self._inner.get_bytes_strict_bounded_versioned(key, maximum_bytes)


# ---------------------------------------------------------------------------
# (a) A47 restart: a NEW store object over the same local directory
# ---------------------------------------------------------------------------


def test_restart_new_store_object_sees_same_generation_and_clock(tmp_path) -> None:
    store = _local_store(tmp_path, "source")
    publication = PDS.publish_production_dataset(store, _material())

    reopened = PDS.build_production_dataset_store(local_dir=tmp_path / "source")
    first = PDS.load_latest_generation(store, ISSUER)
    second = PDS.load_latest_generation(reopened, ISSUER)
    assert first is not None and second is not None
    assert second.generation_id == first.generation_id == publication.generation_id
    assert second.admitted_at == first.admitted_at
    summary = PDS.latest_generation_summary(reopened, ISSUER)
    assert summary == {
        "dataset_generation_id": publication.generation_id,
        "admitted_at": publication.admitted_at,
    }


# ---------------------------------------------------------------------------
# (b) A47 backup -> restore: exact bytes, idempotent, never overwrites
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["memory", "local"])
def test_backup_restore_round_trip_is_exact_and_idempotent(tmp_path, kind) -> None:
    source = _make_store(kind, tmp_path, "source")
    publication = PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    assert manifest.issuer_id == ISSUER
    assert manifest.generation_id == publication.generation_id
    roles = _entries_by_role(manifest)
    assert len(roles["pointer"]) == 1
    assert len(roles["manifest"]) == 1
    assert len(roles["object"]) == len(PDS.PRODUCTION_DATASET_ROLES)
    assert roles["pointer"][0].key == PDS.production_latest_key(ISSUER)
    assert roles["manifest"][0].key == PDS.production_manifest_key(
        ISSUER, publication.generation_id
    )

    # to_dict is deterministic and sorted by key; from_dict rebuilds it exactly.
    document = manifest.to_dict()
    listed_keys = [row["key"] for row in document["entries"]]
    assert listed_keys == sorted(listed_keys)
    assert RD.BackupManifest.from_dict(document) == manifest

    payloads = RD.backup_bytes(source, manifest)
    assert set(payloads) == {entry.key for entry in manifest.entries}

    target = _make_store(kind, tmp_path, "target")
    receipt = RD.restore_issuer(target, manifest, payloads)
    assert receipt.verified is True
    assert receipt.pointer == "restored"
    assert receipt.already_present == ()
    immutable_keys = [e.key for e in manifest.entries if e.role != "pointer"]
    assert sorted(receipt.written) == sorted(immutable_keys)
    # byte-identical pointer, manifest, and objects
    for entry in manifest.entries:
        assert target.get_bytes(entry.key) == payloads[entry.key]
        assert source.get_bytes(entry.key) == payloads[entry.key]
    restored = PDS.load_latest_generation(target, ISSUER)
    original = PDS.load_latest_generation(source, ISSUER)
    assert restored is not None and original is not None
    assert restored.generation_id == original.generation_id
    assert restored.admitted_at == original.admitted_at

    # Second restore: every key already present, ZERO writes (counted).
    counting = _CountingStore(target)
    again = RD.restore_issuer(counting, manifest, payloads)
    assert again.verified is True
    assert again.pointer == "kept_existing"
    assert sorted(again.already_present) == sorted(immutable_keys)
    assert again.written == ()
    counting.assert_zero_writes()


def test_restore_refuses_different_bytes_and_never_overwrites(tmp_path) -> None:
    source = _make_store("memory", tmp_path, "source")
    PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    payloads = RD.backup_bytes(source, manifest)
    target = PDS.InMemoryStrictConditionalStore()
    RD.restore_issuer(target, manifest, payloads)

    object_entries = [e for e in manifest.entries if e.role == "object"]
    hostile_key = object_entries[0].key
    intact_key = object_entries[1].key
    target.drop(hostile_key)
    target.raw_put(hostile_key, b"hostile different bytes")
    intact_before = target.get_bytes(intact_key)

    counting = _CountingStore(target)
    with pytest.raises(PDS.ProductionDatasetError, match="restore target holds different bytes"):
        RD.restore_issuer(counting, manifest, payloads)
    counting.assert_zero_writes()
    # Originals intact: the hostile bytes and every other key are untouched.
    assert target.get_bytes(hostile_key) == b"hostile different bytes"
    assert target.get_bytes(intact_key) == intact_before


def test_restore_keeps_existing_pointer_naming_another_generation() -> None:
    source = PDS.InMemoryStrictConditionalStore()
    g1 = PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    payloads = RD.backup_bytes(source, manifest)

    target = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(target, _material())  # the same deterministic g1
    g2 = PDS.publish_production_dataset(
        target, _material(admitted_at=T_LATER, supersedes=g1.generation_id)
    )
    pointer_key = PDS.production_latest_key(ISSUER)
    before = target.get_bytes(pointer_key)

    counting = _CountingStore(target)
    receipt = RD.restore_issuer(counting, manifest, payloads)
    counting.assert_zero_writes()
    # An existing pointer naming another generation is KEPT, not overwritten:
    # the outcome carries both generation ids and nothing is written (MAJOR-2).
    assert receipt.pointer == "kept_existing"
    assert receipt.pointer_generation_id == g1.generation_id
    assert receipt.kept_pointer_generation_id == g2.generation_id
    immutable_keys = [e.key for e in manifest.entries if e.role != "pointer"]
    assert sorted(receipt.already_present) == sorted(immutable_keys)
    assert receipt.written == ()
    assert receipt.restored == ()
    assert target.get_bytes(pointer_key) == before
    latest = PDS.load_latest_generation(target, ISSUER)
    assert latest is not None and latest.generation_id == g2.generation_id
    # The restored generation itself still loads and verifies.
    assert receipt.verified is True


def test_restore_keeps_unparseable_existing_pointer_without_naming_a_generation() -> None:
    source = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    payloads = RD.backup_bytes(source, manifest)

    target = PDS.InMemoryStrictConditionalStore()
    RD.restore_issuer(target, manifest, payloads)
    pointer_key = PDS.production_latest_key(ISSUER)
    target.drop(pointer_key)
    target.raw_put(pointer_key, b"{not a pointer")
    before = target.get_bytes(pointer_key)

    counting = _CountingStore(target)
    receipt = RD.restore_issuer(counting, manifest, payloads)
    counting.assert_zero_writes()
    assert receipt.pointer == "kept_existing"
    # The kept pointer cannot be decoded; the receipt refuses to guess.
    assert receipt.kept_pointer_generation_id is None
    assert target.get_bytes(pointer_key) == before


def test_restore_labels_echo_confirmed_object_write_restored_not_already_present() -> None:
    source = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    payloads = RD.backup_bytes(source, manifest)
    object_key = next(e.key for e in manifest.entries if e.role == "object")

    target = _CommitThenLoseResponseStore(object_key)
    receipt = RD.restore_issuer(target, manifest, payloads)
    # The drill's own write, confirmed by read-back after the lost
    # response: "restored", never "already_present" (MINOR-1).
    assert object_key in receipt.restored
    assert object_key not in receipt.already_present
    assert object_key not in receipt.written
    assert receipt.pointer == "restored"
    assert receipt.verified is True
    assert target.get_bytes(object_key) == payloads[object_key]

    # The other label: replaying the same backup finds every immutable key
    # genuinely pre-existing -> "already_present", with zero writes.
    counting = _CountingStore(target)
    again = RD.restore_issuer(counting, manifest, payloads)
    counting.assert_zero_writes()
    immutable_keys = [e.key for e in manifest.entries if e.role != "pointer"]
    assert sorted(again.already_present) == sorted(immutable_keys)
    assert again.restored == ()
    assert again.written == ()
    assert again.pointer == "kept_existing"


def test_restore_labels_denied_but_committed_object_write_restored() -> None:
    source = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    payloads = RD.backup_bytes(source, manifest)
    object_key = next(e.key for e in manifest.entries if e.role == "object")

    target = _CommitThenDenyStore(object_key)
    receipt = RD.restore_issuer(target, manifest, payloads)
    # Falsy CAS signal with exact bytes on read-back after a verified
    # absence: still the drill's own write -> "restored" (MINOR-1).
    assert object_key in receipt.restored
    assert object_key not in receipt.already_present
    assert receipt.verified is True
    assert target.get_bytes(object_key) == payloads[object_key]


def test_restore_labels_echo_confirmed_pointer_write_restored() -> None:
    source = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    payloads = RD.backup_bytes(source, manifest)

    target = _CommitThenLoseResponseStore(PDS.production_latest_key(ISSUER))
    receipt = RD.restore_issuer(target, manifest, payloads)
    # The drill's pointer write evidently committed: "restored", not
    # "kept_existing" (MINOR-1).
    assert receipt.pointer == "restored"
    assert receipt.kept_pointer_generation_id is None
    assert receipt.pointer_generation_id == manifest.generation_id
    assert receipt.verified is True
    latest = PDS.load_latest_generation(target, ISSUER)
    assert latest is not None and latest.generation_id == manifest.generation_id


def test_restore_refuses_tampered_payloads(tmp_path) -> None:
    source = _make_store("memory", tmp_path, "source")
    PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    payloads = RD.backup_bytes(source, manifest)
    entry = next(e for e in manifest.entries if e.role == "object")

    damaged = dict(payloads)
    damaged[entry.key] = payloads[entry.key] + b"x"  # same key, wrong digest
    with pytest.raises(PDS.ProductionDatasetError, match="payload digest mismatch"):
        RD.restore_issuer(PDS.InMemoryStrictConditionalStore(), manifest, damaged)

    missing = {k: v for k, v in payloads.items() if k != entry.key}
    with pytest.raises(PDS.ProductionDatasetError, match="keys are inexact"):
        RD.restore_issuer(PDS.InMemoryStrictConditionalStore(), manifest, missing)

    empty = dict(payloads)
    empty[entry.key] = b""
    with pytest.raises(PDS.ProductionDatasetError, match="payload is missing"):
        RD.restore_issuer(PDS.InMemoryStrictConditionalStore(), manifest, empty)


def test_backup_manifest_from_dict_is_strict(tmp_path) -> None:
    source = _make_store("memory", tmp_path, "source")
    PDS.publish_production_dataset(source, _material())
    document = RD.backup_issuer(source, ISSUER).to_dict()

    bad_digest = json.loads(json.dumps(document))
    bad_digest["entries"][0]["sha256_hex"] = "not-a-digest"
    with pytest.raises(PDS.ProductionDatasetError):
        RD.BackupManifest.from_dict(bad_digest)

    bad_pointer_key = json.loads(json.dumps(document))
    pointer_row = next(r for r in bad_pointer_key["entries"] if r["role"] == "pointer")
    pointer_row["key"] = "fundamental_forensics/production-datasets/v1/elsewhere/latest.json"
    with pytest.raises(PDS.ProductionDatasetError):
        RD.BackupManifest.from_dict(bad_pointer_key)

    extra_key = json.loads(json.dumps(document))
    extra_key["unexpected"] = True
    with pytest.raises(PDS.ProductionDatasetError):
        RD.BackupManifest.from_dict(extra_key)


# ---------------------------------------------------------------------------
# (c) A47 lost publication: manifest present, pointer absent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["memory", "local"])
def test_lost_publication_audit_demands_publisher_repoint(tmp_path, kind) -> None:
    store = _make_store(kind, tmp_path, "source")
    publication = PDS.publish_production_dataset(store, _material(), skip_pointer=True)
    assert store.get_bytes(PDS.production_latest_key(ISSUER)) is None

    counting = _CountingStore(store)
    state = RD.audit_issuer(counting, ISSUER)
    counting.assert_zero_writes()
    assert state.state == "pointer_absent_generation_present"
    assert state.recovery == "publisher_repoint_required"
    assert state.generation_id is None
    assert publication.generation_id in state.manifest_generation_ids
    # The audit wrote no pointer.
    assert store.get_bytes(PDS.production_latest_key(ISSUER)) is None


@pytest.mark.parametrize("kind", ["memory", "local"])
def test_audit_states_admitted_and_absent(tmp_path, kind) -> None:
    store = _make_store(kind, tmp_path, "source")
    absent = RD.audit_issuer(store, ISSUER)
    assert absent.state == "absent"
    assert absent.recovery is None
    assert absent.manifest_generation_ids == ()

    publication = PDS.publish_production_dataset(store, _material())
    state = RD.audit_issuer(store, ISSUER)
    assert state.state == "admitted"
    assert state.generation_id == publication.generation_id
    assert state.recovery is None


def test_audit_pointer_unverifiable_when_generation_cannot_load() -> None:
    store = PDS.InMemoryStrictConditionalStore()
    publication = PDS.publish_production_dataset(store, _material())
    store.drop(PDS.production_manifest_key(ISSUER, publication.generation_id))
    counting = _CountingStore(store)
    state = RD.audit_issuer(counting, ISSUER)
    counting.assert_zero_writes()
    assert state.state == "pointer_unverifiable"


def test_audit_pointer_unverifiable_on_local_corruption(tmp_path) -> None:
    store = _local_store(tmp_path, "source")
    publication = PDS.publish_production_dataset(store, _material())
    manifest = RD.backup_issuer(store, ISSUER)
    object_key = next(e.key for e in manifest.entries if e.role == "object")
    path = tmp_path / "source" / object_key
    payload = path.read_bytes()
    path.write_bytes(payload[:-1] + bytes([payload[-1] ^ 0x01]))
    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_latest_generation(store, ISSUER)
    state = RD.audit_issuer(store, ISSUER)
    assert state.state == "pointer_unverifiable"


def test_audit_listing_unsupported_is_a_typed_gap() -> None:
    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, _material(), skip_pointer=True)
    assert RD.audit_issuer(_UnlistableStore(store), ISSUER).state == "listing_unsupported"

    class _ExplodingListStore(_UnlistableStore):
        def list_prefix(self, prefix: str):
            raise RuntimeError("list path down")

    assert RD.audit_issuer(_ExplodingListStore(store), ISSUER).state == "listing_unsupported"


# ---------------------------------------------------------------------------
# (d) A18 effect unknown: lost write response, delayed commit, no replay
# ---------------------------------------------------------------------------


def test_effect_unknown_delayed_pointer_commit_reconciles_landed_zero_writes() -> None:
    store = _LostPointerResponseStore()
    store.lose_pointer_response = True
    with pytest.raises(PDS.ProductionDatasetEffectUnknownError):
        PDS.publish_production_dataset(store, _material())

    # The pointer write's effect on its ORIGINAL target is unknown: the
    # manifest landed, the pointer did not (yet). No replay, no failover.
    expected = _baseline_generation_id()
    assert store.get_bytes(PDS.production_latest_key(ISSUER)) is None
    counting = _CountingStore(store)
    assert (
        RD.reconcile_effect_unknown(counting, ISSUER, expected)
        == "manifest_landed_pointer_not_advanced"
    )
    counting.assert_zero_writes()

    # The delayed commit lands; read-only same-carrier reconciliation proves it.
    store.flush_delayed_commit()
    generation = PDS.load_latest_generation(store, ISSUER)
    assert generation is not None and generation.generation_id == expected
    counting_again = _CountingStore(store)
    assert RD.reconcile_effect_unknown(counting_again, ISSUER, expected) == "landed"
    counting_again.assert_zero_writes()


def test_effect_unknown_write_never_lands_reconciles_not_landed_zero_writes() -> None:
    store = PDS.InMemoryStrictConditionalStore()
    store.raise_on_conditional_after_commit = True
    store.drop_after_commit = True
    with pytest.raises(PDS.ProductionDatasetEffectUnknownError):
        PDS.publish_production_dataset(store, _material())

    expected = _baseline_generation_id()
    counting = _CountingStore(store)
    assert RD.reconcile_effect_unknown(counting, ISSUER, expected) == "not_landed"
    counting.assert_zero_writes()
    # Nothing at all landed for this issuer.
    assert RD.audit_issuer(store, ISSUER).state == "absent"


def test_reconcile_corrupt_pointer_raises_effect_unknown_zero_writes() -> None:
    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, _material())
    pointer_key = PDS.production_latest_key(ISSUER)
    store.drop(pointer_key)
    store.raw_put(pointer_key, b"{not a pointer")

    counting = _CountingStore(store)
    # A corrupt pointer proves nothing about landing (A18): the outcome on
    # the original target stays EFFECT_UNKNOWN — never "not_landed" and
    # never replayed (MAJOR-1).
    with pytest.raises(PDS.ProductionDatasetEffectUnknownError):
        RD.reconcile_effect_unknown(counting, ISSUER, _baseline_generation_id())
    counting.assert_zero_writes()


@pytest.mark.parametrize("kind", ["memory", "local"])
def test_reconcile_outcomes_on_both_store_kinds(tmp_path, kind) -> None:
    store = _make_store(kind, tmp_path, "source")
    g1 = PDS.publish_production_dataset(store, _material())
    assert RD.reconcile_effect_unknown(store, ISSUER, g1.generation_id) == "landed"

    g2 = PDS.publish_production_dataset(
        store, _material(admitted_at=T_LATER, supersedes=g1.generation_id)
    )
    assert RD.reconcile_effect_unknown(store, ISSUER, g1.generation_id) == (
        "pointer_names_other_generation"
    )
    assert RD.reconcile_effect_unknown(store, ISSUER, g2.generation_id) == "landed"

    fresh = _make_store(kind, tmp_path, "fresh")
    assert RD.reconcile_effect_unknown(fresh, ISSUER, g2.generation_id) == "not_landed"

    staged = _make_store(kind, tmp_path, "staged")
    PDS.publish_production_dataset(
        staged, _material(admitted_at=T_LATER, supersedes=g1.generation_id), skip_pointer=True
    )
    assert RD.reconcile_effect_unknown(staged, ISSUER, g2.generation_id) == (
        "manifest_landed_pointer_not_advanced"
    )


# ---------------------------------------------------------------------------
# (e) A47 rollback: a correction (supersede), never a rewind
# ---------------------------------------------------------------------------


def test_rollback_is_a_correction_the_owner_refuses_to_rewind() -> None:
    store = PDS.InMemoryStrictConditionalStore()
    g1 = PDS.publish_production_dataset(store, _material(admitted_at=T_ADMITTED))
    g2 = PDS.publish_production_dataset(
        store, _material(admitted_at=T_LATER, supersedes=g1.generation_id)
    )

    # Any public-API attempt to make latest name G1 again is refused by the
    # owner: the stale-pointer rewind guard in _publish_pointer raises
    # "stale production dataset cannot rewind independent latest pointer"
    # (engine/fundamental_forensics/production_datasets.py:791-794; the same
    # refusal rides _pointer_after_failed_cas at :725-727).
    with pytest.raises(
        PDS.ProductionDatasetError,
        match="stale production dataset cannot rewind independent latest pointer",
    ):
        PDS.publish_production_dataset(store, _material(admitted_at=T_ADMITTED))

    state = RD.audit_issuer(store, ISSUER)
    assert state.state == "admitted"
    assert state.generation_id == g2.generation_id
    latest = PDS.load_latest_generation(store, ISSUER)
    assert latest is not None and latest.generation_id == g2.generation_id
    # Originals intact: BOTH manifests remain loadable.
    assert PDS.load_generation(store, ISSUER, g1.generation_id).generation_id == g1.generation_id
    assert PDS.load_generation(store, ISSUER, g2.generation_id).generation_id == g2.generation_id

    counting = _CountingStore(store)
    assert RD.reconcile_effect_unknown(counting, ISSUER, g1.generation_id) == (
        "pointer_names_other_generation"
    )
    counting.assert_zero_writes()

    # The drill exposes no rewind surface at all.
    assert not hasattr(RD, "rewind_latest_pointer")
    rewindish = sorted(
        name
        for name in set(vars(RD)) | set(RD.__all__)
        if "rewind" in name.lower() or "rollback" in name.lower()
    )
    assert rewindish == []


# ---------------------------------------------------------------------------
# (f) corruption in a restored target: unverified restore, unverifiable pointer
# ---------------------------------------------------------------------------


def test_corrupted_restore_target_is_unverified_and_audit_flags_it(tmp_path) -> None:
    source = _make_store("memory", tmp_path, "source")
    PDS.publish_production_dataset(source, _material())
    manifest = RD.backup_issuer(source, ISSUER)
    payloads = RD.backup_bytes(source, manifest)
    object_key = next(e.key for e in manifest.entries if e.role == "object")

    target = _OneByteCorruptingStore(object_key)
    receipt = RD.restore_issuer(target, manifest, payloads)
    # The write phase "succeeded" but the generation cannot load: the restore
    # is not complete and the receipt says so.
    assert receipt.verified is False
    assert object_key in receipt.written
    assert receipt.pointer == "restored"

    with pytest.raises(PDS.ProductionDatasetError):
        PDS.load_generation(target, ISSUER, manifest.generation_id)

    counting = _CountingStore(target)
    state = RD.audit_issuer(counting, ISSUER)
    counting.assert_zero_writes()
    assert state.state == "pointer_unverifiable"


# ---------------------------------------------------------------------------
# (g) CLI round trip on local-directory stores
# ---------------------------------------------------------------------------


def _run_cli(*argv: str):
    return subprocess.run(
        [sys.executable, "scripts/fif_recovery_drill.py", *argv],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_cli_backup_restore_audit_round_trip(tmp_path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    store = PDS.build_production_dataset_store(local_dir=source_dir)
    publication = PDS.publish_production_dataset(store, _material())

    out_dir = tmp_path / "backup"
    result = _run_cli(
        "backup", "--local-store", str(source_dir), "--issuer", ISSUER, "--out", str(out_dir)
    )
    assert result.returncode == 0, result.stderr
    document = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert document["generation_id"] == publication.generation_id
    assert document["issuer_id"] == ISSUER
    stored = {path.name for path in (out_dir / "objects").iterdir()}
    assert stored == {row["sha256_hex"] for row in document["entries"]}

    target_dir = tmp_path / "target"
    result = _run_cli(
        "restore", "--from", str(out_dir), "--local-store", str(target_dir), "--issuer", ISSUER
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout.strip().splitlines()[-1])
    assert receipt["verified"] is True
    assert receipt["pointer"] == "restored"
    assert receipt["already_present"] == []

    target = PDS.build_production_dataset_store(local_dir=target_dir)
    generation = PDS.load_latest_generation(target, ISSUER)
    assert generation is not None
    assert generation.generation_id == publication.generation_id
    assert generation.admitted_at == T_ADMITTED

    audit = _run_cli("audit", "--local-store", str(target_dir), "--issuer", ISSUER)
    assert audit.returncode == 0, audit.stderr
    assert json.loads(audit.stdout)["state"] == "admitted"


def test_cli_help_for_every_subcommand() -> None:
    for argv in (["--help"], ["backup", "--help"], ["restore", "--help"], ["audit", "--help"]):
        result = _run_cli(*argv)
        assert result.returncode == 0, result.stderr
        assert "usage" in result.stdout.lower()
