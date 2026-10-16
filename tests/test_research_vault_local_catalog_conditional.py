"""Causal LocalStore tests for the canonical catalog conditional ceiling.

The producer commits ``research_vault/catalog.json`` at up to its own
``CATALOG_MAX_BYTES`` (16 MiB); every other conditional key keeps the
historical 16 KiB predecessor ceiling. These tests exercise the real
``LocalStore`` conditional write path (cross-process lock, no-follow
descriptor walk, staged replace) around both bounds, including the exact
serialized size of the actually committed production catalog
(3,598,794 bytes). The original unconditional 16 KiB cap aborted the
predecessor read of that catalog before the CAS comparison could run.
"""
import json

import pytest

from engine.research_vault.r2_store import (
    BoundedReadTooLarge,
    HARD_MAX_STRICT_CONDITIONAL_OBJECT_BYTES,
    LocalStore,
)

CATALOG_KEY = "research_vault/catalog.json"
CATALOG_ALLOWANCE = 16 * 1024 * 1024
LEGACY_LIMIT = HARD_MAX_STRICT_CONDITIONAL_OBJECT_BYTES
COMMITTED_CATALOG_BYTES = 3_598_794  # actual committed production catalog size


def _store(tmp_path):
    return LocalStore(tmp_path / "store")


def _synthetic_catalog(target_bytes: int) -> bytes:
    """One deterministic synthetic catalog of an exact serialized size."""
    doc = {"schema": "synthetic-catalog", "count": 2959, "items": []}
    prefix = json.dumps(doc, separators=(",", ":"))[:-1]
    member = '"synthetic_padding":"'
    padding = target_bytes - len(prefix) - len(",") - len(member) - len('"}')
    assert padding > 0, target_bytes
    raw = (prefix + "," + member + "x" * padding + '"}').encode()
    assert len(raw) == target_bytes
    json.loads(raw)  # stays one valid JSON document
    return raw


def _seed(store, key, body):
    assert store.put_bytes(key, body)
    assert store.get_bytes(key) == body


def test_committed_size_catalog_conditional_write_succeeds(tmp_path):
    store = _store(tmp_path)
    original = _synthetic_catalog(COMMITTED_CATALOG_BYTES)
    _seed(store, CATALOG_KEY, original)
    version = LocalStore._local_version(original)
    # The producer reads the predecessor through the catalog allocation.
    readback = store.get_bytes_strict_bounded_versioned(CATALOG_KEY, CATALOG_ALLOWANCE)
    assert readback.data == original
    assert readback.version == version
    replacement = _synthetic_catalog(COMMITTED_CATALOG_BYTES + 11)
    assert store.put_bytes_strict_conditional(
        CATALOG_KEY, replacement, expected_version=version)
    assert store.get_bytes(CATALOG_KEY) == replacement
    assert store.get_bytes_strict_bounded_versioned(
        CATALOG_KEY, CATALOG_ALLOWANCE).version == LocalStore._local_version(replacement)


def test_stale_and_create_only_expectations_never_touch_oversize_catalog(tmp_path):
    store = _store(tmp_path)
    original = _synthetic_catalog(COMMITTED_CATALOG_BYTES)
    _seed(store, CATALOG_KEY, original)
    stale = LocalStore._local_version(b"stale synthetic predecessor")
    assert not store.put_bytes_strict_conditional(
        CATALOG_KEY, b"never", expected_version=stale)
    assert not store.put_bytes_strict_conditional(
        CATALOG_KEY, b"never", expected_version=None)
    assert store.get_bytes(CATALOG_KEY) == original


def test_exact_catalog_allowance_boundary_still_succeeds(tmp_path):
    store = _store(tmp_path)
    original = _synthetic_catalog(CATALOG_ALLOWANCE)
    _seed(store, CATALOG_KEY, original)
    assert store.put_bytes_strict_conditional(
        CATALOG_KEY, b"replacement at the exact allowance",
        expected_version=LocalStore._local_version(original))


def test_catalog_allowance_ends_at_the_producer_allocation(tmp_path):
    store = _store(tmp_path)
    original = _synthetic_catalog(CATALOG_ALLOWANCE + 1)
    _seed(store, CATALOG_KEY, original)
    with pytest.raises(BoundedReadTooLarge):
        store.put_bytes_strict_conditional(
            CATALOG_KEY, b"never", expected_version=LocalStore._local_version(original))
    assert store.get_bytes(CATALOG_KEY) == original


@pytest.mark.parametrize("key", [
    "research_vault/nested/catalog.json",
    "research_vault/catalog.json.bak",
    "research_vault/CATALOG.json",
    "research_inbox/catalog.json",
])
def test_noncanonical_keys_keep_the_legacy_ceiling(tmp_path, key):
    store = _store(tmp_path)
    original = b"p" * (LEGACY_LIMIT + 1)
    _seed(store, key, original)
    version = LocalStore._local_version(original)
    with pytest.raises(BoundedReadTooLarge):
        store.put_bytes_strict_conditional(key, b"never", expected_version=version)
    assert store.get_bytes(key) == original
    # Below the legacy ceiling the same key still conditionally writes.
    small = b"within the legacy ceiling"
    _seed(store, key, small)
    assert store.put_bytes_strict_conditional(
        key, b"replacement below the legacy ceiling",
        expected_version=LocalStore._local_version(small))


def test_catalog_allowance_matches_the_producer_constant():
    from engine.research_vault import producer_generation
    from engine.research_vault import r2_store
    assert r2_store._CONDITIONAL_CATALOG_MAX_BYTES == producer_generation.CATALOG_MAX_BYTES
