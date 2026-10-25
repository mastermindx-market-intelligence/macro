"""Pure conversion planning; no production ledger or migration is exercised."""
from dataclasses import replace
from hashlib import sha256

import pytest

from engine import qledger_store_protocol as p
from engine.qledger_store_conversion import plan_legacy_conversion


@pytest.fixture
def limits():
    return p.ProtocolLimits(
        base_bytes=16, part_bytes=32, page_bytes=2048, root_bytes=4096,
        descriptor_bytes=1024, leaf_entries=4, fanout=4, index_levels=3,
        history_operations=32, reference_visits=4096, snapshot_members=1024,
        snapshot_bytes=524288, logical_bytes=4096, input_rows=1024,
        publication_objects=1024, git_blob_bytes=16384,
    )


def convert(raw, limits, **overrides):
    args = dict(source_id="fixture:original", expected_byte_count=len(raw),
                expected_logical_digest=sha256(raw).hexdigest(),
                transaction_id="conversion:one", limits=limits)
    args.update(overrides)
    return plan_legacy_conversion(raw, **args)


@pytest.mark.parametrize("tail", [
    b'\nmalformed\n' + '"文字"\r\n'.encode() + b'null\n',
    b'\n\xff\r\n\x00\n',
])
def test_above_base_bound_is_lossless_and_uses_existing_verified_plan(limits, tail):
    raw = b'{"same":1}\n' * 4 + tail
    result = convert(raw, limits)
    assert len(raw) > limits.base_bytes
    assert type(result.plan) is p.PublicationPlan
    p.validate_plan(result.plan, limits=limits)
    assert result.source_id == "fixture:original"
    assert result.byte_count == len(raw)
    assert result.logical_digest == sha256(raw).hexdigest()
    assert result.source_assurance == "CALLER_BYTES_ONLY_NOT_CUTOVER_ADMISSION"
    assert result.plan.snapshot.root.base.size == 0
    assert result.plan.snapshot.root.operation_count == 1
    assert result.plan.transaction.transaction_id == "conversion:one"
    assert result.members[p.BASE_PATH] == b""
    assert result.members[p.ROOT_PATH] == result.plan.root_bytes
    source = p.InMemorySource(result.members, snapshot_id="fixture:materialized")
    checked = p.verify_snapshot(source, result.plan.snapshot.root, limits=limits)
    with p.open_logical_bytes(checked) as stream:
        assert stream.read() == raw
    assert p.validate_publication(source, checked.root, (), limits=limits).accepted
    parts = [value for path, value in result.members.items() if path.startswith(p.PART_PREFIX)]
    assert len(parts) > 1 and all(len(value) <= limits.part_bytes for value in parts)
    with pytest.raises(TypeError):
        result.members[p.BASE_PATH] = b"changed"


@pytest.mark.parametrize("override", [
    {"expected_byte_count": 1}, {"expected_byte_count": True},
    {"expected_logical_digest": "0" * 64}, {"expected_logical_digest": "bad"},
    {"source_id": ""}, {"source_id": "bad\nsource"},
    {"transaction_id": "bad transaction"},
])
def test_invalid_source_witness_or_intent_is_refused(limits, override):
    with pytest.raises(p.SnapshotIntegrityError):
        convert(b"original\n", limits, **override)


@pytest.mark.parametrize("raw", [b"", b"unterminated", bytearray(b"mutable\n"), "text\n"])
def test_requires_nonempty_immutable_lf_terminated_bytes(limits, raw):
    args = dict(source_id="fixture", expected_byte_count=0,
                expected_logical_digest="0" * 64, transaction_id="one", limits=limits)
    with pytest.raises(p.SnapshotIntegrityError):
        plan_legacy_conversion(raw, **args)


@pytest.mark.parametrize("changes,raw", [
    ({}, b"x" * 32 + b"\n"),
    ({"logical_bytes": 4}, b"1234\n"),
    ({"input_rows": 1}, b"one\ntwo\n"),
    ({"snapshot_bytes": 8}, b"one\n"),
    ({"git_blob_bytes": 8}, b"one\n"),
])
def test_finite_existing_limits_are_not_weakened(limits, changes, raw):
    with pytest.raises(p.SnapshotIntegrityError):
        convert(raw, replace(limits, **changes))


def test_no_io_clocks_selection_or_domain_parsing(limits, monkeypatch):
    import builtins
    import os
    import subprocess
    from engine import qledger_store, qledger_store_native

    def forbidden(*args, **kwargs):
        raise AssertionError("conversion planner attempted an effect")

    # Restore before unrelated autouse-fixture teardown removes its own files.
    with monkeypatch.context() as effects:
        effects.setattr(builtins, "open", forbidden)
        effects.setattr(os, "open", forbidden)
        effects.setattr(subprocess, "run", forbidden)
        effects.setattr(qledger_store, "_production_claims_binding", forbidden)
        effects.setattr(qledger_store_native, "materialize_plan", forbidden)
        raw = b"not-json\n\nnot-json\n"
        assert convert(raw, limits).plan.snapshot.root.logical_size == len(raw)


def test_identity_is_explicit_and_distinguishes_same_bytes(limits):
    one = convert(b"a\n", limits)
    two = convert(b"a\n", limits, source_id="fixture:other")
    assert one.source_id != two.source_id
    assert one.plan.expected_root_digest == two.plan.expected_root_digest
    assert one.plan.transaction.digest == two.plan.transaction.digest
    # This is a content plan, not source custody or an authenticated Git witness.
    assert one.source_assurance == two.source_assurance


def test_forged_profile_cannot_raise_supported_ceiling(limits):
    object.__setattr__(limits, "part_bytes", 65 * 1024 * 1024)
    with pytest.raises(p.SnapshotIntegrityError, match="unsupported profile field part_bytes"):
        convert(b"a\n", limits)
