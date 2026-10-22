"""Synthetic original-result retention; no real producer, root or publication."""
from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path

import pytest

from tests.test_qledger_conversion_candidate import fixture, native_fixture, prepare_native
from engine import qledger_store_protocol as p, qledger_store_native as n
from engine.qledger_store import NativeClaimsWrite
from scripts.ci.qledger_publication import NativeOperationReceipt
from engine import qledger_original_result as result


@pytest.fixture
def original(tmp_path, native_fixture):
    repo, _, _, limits, receipt = native_fixture
    plan = p.plan_append(receipt.original_base_snapshot, transaction_id="native:original",
                         serialized_rows=[b'{"original":"fixed-clock"}\n'], limits=limits)
    intent = n.NativeClaimsIntent(receipt.operation_id, receipt.lane_id, "native:original")
    write = NativeClaimsWrite(intent, plan, repo / p.BASE_PATH)
    candidate = prepare_native(native_fixture, native_operation_receipt=NativeOperationReceipt(
        intent.operation_id, intent.lane_id, plan._before, plan.snapshot, (intent.transaction_id,), limits))
    prepared = result.prepare_original_result(write, candidate=candidate, result_id="fixture-original", limits=limits)
    root = tmp_path / "owner-evidence"
    root.mkdir(mode=0o700)
    return write, prepared, root, root / "fixture-original", limits, candidate


def read(original, **changes):
    write, prepared, root, path, limits, _ = original
    kwargs = dict(owner_root=root, result_path=path, expected_result_id=prepared.result_id,
        expected_manifest_digest=prepared.manifest_digest, expected_claims_path=write.claims_path,
        expected_intent=write.intent, limits=limits)
    kwargs.update(changes)
    return result.read_original_result(**kwargs)


def test_retained_result_survives_process_inputs_and_git_object_loss(original):
    write, prepared, root, path, limits, candidate = original
    retained = result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    assert retained.manifest_digest == prepared.manifest_digest
    # Git is deliberately unavailable afterwards: the result contains original
    # native bytes, roots, transactions and the explicit operation/object binding.
    oid = candidate.candidate_oid
    (write.claims_path.parents[2] / ".git/objects" / oid[:2] / oid[2:]).unlink()
    restored = read(original)
    assert restored.write.intent == write.intent and restored.write.claims_path == write.claims_path
    assert restored.write.plan._before.root_bytes == write.plan._before.root_bytes
    assert restored.write.plan.snapshot.root_bytes == write.plan.snapshot.root_bytes
    with p.open_logical_bytes(restored.write.plan.snapshot) as stream:
        actual = stream.read()
    with p.open_logical_bytes(write.plan.snapshot) as stream:
        assert actual == stream.read()
    assert restored.candidate_oid == candidate.candidate_oid
    assert restored.native_operation_receipt.authorized_transaction_ids == (write.intent.transaction_id,)
    assert result.require_retained_original(write, restored).manifest_digest == prepared.manifest_digest


def test_missing_or_boolean_retention_never_calls_native_apply(original):
    write, _, _, _, _, _ = original
    class Session:
        def apply_prepared(self, plan):
            pytest.fail("unretained input reached native apply")
    for missing in (None, True, object()):
        with pytest.raises(p.SnapshotIntegrityError):
            result.apply_retained_original(Session(), write, missing)


def test_manifest_loss_blocks_apply_even_with_previous_readback(original):
    write, prepared, root, path, _, _ = original
    retained = result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    (path / "manifest.json").unlink()
    class Session:
        def apply_prepared(self, plan):
            pytest.fail("lost manifest reached apply")
    with pytest.raises(p.SnapshotIntegrityError):
        result.apply_retained_original(Session(), write, retained)


def test_partial_install_keeps_evidence_and_never_overwrites(original, monkeypatch):
    _, prepared, root, path, _, _ = original
    monkeypatch.setattr(result, "_sync_file", lambda fd: (_ for _ in ()).throw(OSError("fixture durability failure")))
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    assert path.exists() and not (path / "manifest.json").exists()
    before = {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    assert before == {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}
    with pytest.raises(p.SnapshotIntegrityError):
        read(original)


def test_complete_manifest_response_loss_reconciles_same_explicit_path(original, monkeypatch):
    _, prepared, root, path, _, _ = original
    sync = result._sync_dir
    def response_lost(fd):
        sync(fd)
        if (path / "manifest.json").exists() and os.fstat(fd).st_ino == root.stat().st_ino:
            raise OSError("fixture final retention return lost")
    monkeypatch.setattr(result, "_sync_dir", response_lost)
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    manifest = (path / "manifest.json").read_bytes()
    monkeypatch.setattr(result, "_sync_dir", sync)
    restored = read(original)
    assert restored.manifest_digest == sha256(manifest).hexdigest()
    assert restored.result_path == path and (path / "manifest.json").read_bytes() == manifest


@pytest.mark.parametrize("field", ["target", "intent", "digest", "identity", "profile"])
def test_foreign_binding_refuses(original, field):
    write, prepared, root, path, limits, _ = original
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    changes = {
        "target": {"expected_claims_path": root / p.BASE_PATH},
        "intent": {"expected_intent": replace(write.intent, operation_id="foreign")},
        "digest": {"expected_manifest_digest": "0" * 64},
        "identity": {"expected_result_id": "other-result"},
        "profile": {"limits": replace(limits, input_rows=limits.input_rows - 1)},
    }[field]
    with pytest.raises(p.SnapshotIntegrityError):
        read(original, **changes)


def test_root_must_exist_be_explicit_and_not_symlinked(original):
    _, prepared, root, path, _, _ = original
    missing = root / "missing"
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=missing, result_path=missing / prepared.result_id, prepared=prepared)
    assert not missing.exists()
    alias = root.parent / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=alias, result_path=alias / prepared.result_id, prepared=prepared)
    assert not path.exists()


def test_verified_retention_precedes_explicit_native_apply(original):
    write, prepared, root, path, limits, _ = original
    # Install ONLY a synthetic native base in this fixture's disposable checkout.
    for relative, payload in {**write.plan._before._members, p.ROOT_PATH: write.plan._before.root_bytes}.items():
        target = write.claims_path.parents[2] / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    retained = result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    with n.NativeClaimsSession(write.claims_path.parents[2], intent=write.intent, limits=limits) as session:
        outcome = result.apply_retained_original(session, write, retained)
    assert outcome.status == "materialized" and outcome.clock_status == "not_attempted"
    assert read(original).write.plan.root_bytes == write.plan.root_bytes


@pytest.mark.parametrize("level", ["root", "result", "members"])
def test_readback_rejects_directory_symlink_substitution(original, monkeypatch, level):
    _, prepared, root, path, _, _ = original
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    read_file = result._read
    substituted = []
    def replace_path(parent, name, maximum, identities):
        value = read_file(parent, name, maximum, identities)
        if name == "manifest.json" and not substituted:
            target = root if level == "root" else (path if level == "result" else path / "members")
            moved = target.with_name(target.name + "-moved")
            target.rename(moved)
            target.symlink_to(moved, target_is_directory=True)
            substituted.append(moved)
        return value
    monkeypatch.setattr(result, "_read", replace_path)
    with pytest.raises(p.SnapshotIntegrityError):
        read(original)
    assert substituted


@pytest.mark.parametrize("kind", ["oversize", "hash", "extra", "writable"])
def test_readback_enforces_exact_bounded_inventory(original, kind):
    _, prepared, root, path, limits, _ = original
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    member = next((path / "members").iterdir())
    if kind == "oversize":
        with member.open("r+b") as handle:
            handle.truncate(limits.snapshot_bytes + 1)
    elif kind == "hash":
        member.write_bytes(b"wrong-original-bytes")
    elif kind == "extra":
        (path / "members" / ("0" * 64)).write_bytes(b"foreign")
    else:
        (path / "members").chmod(0o777)
    with pytest.raises(p.SnapshotIntegrityError):
        read(original)


def test_non_overwriting_completed_result_and_tampered_object_binding(original):
    import json
    _, prepared, root, path, _, _ = original
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    before = (path / "manifest.json").read_bytes()
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    assert (path / "manifest.json").read_bytes() == before
    manifest = json.loads(before)
    manifest["git"]["candidate_oid"] = "0" * 40
    changed = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    (path / "manifest.json").write_bytes(changed)
    # Even a caller's altered hash cannot make a contradictory operation/object
    # binding pass the canonical commit identity check.
    with pytest.raises(p.SnapshotIntegrityError):
        read(original, expected_manifest_digest=sha256(changed).hexdigest())


@pytest.mark.parametrize("kind", ["append", "replace"])
def test_restore_original_plan_preserves_raw_single_transaction_and_refuses_extra_history(kind):
    limits = p.ProtocolLimits(base_bytes=64, part_bytes=64, snapshot_bytes=1048576)
    raw = b"malformed\n"
    root = p.RootRecord(p.MemberRef(p.BASE_PATH, sha256(raw).hexdigest(), len(raw)),
                        None, 0, len(raw), sha256(raw).hexdigest(), limits.fingerprint)
    base = p.verify_snapshot(p.InMemorySource({p.BASE_PATH: raw}, snapshot_id="fixture:original"), root, limits=limits)
    if kind == "append":
        original = p.plan_append(base, transaction_id="original", serialized_rows=[b"duplicate\n", b"duplicate\n"], limits=limits)
    else:
        original = p.plan_replace_view(base, transaction_id="original", expected_view_digest=base.root.logical_digest,
                                       replacement_rows=[b"raw-replacement\n"], limits=limits)
    restored = p.restore_original_plan(base, original.snapshot, transaction_id="original", limits=limits)
    assert restored.root_bytes == original.root_bytes and restored.transaction == original.transaction
    assert restored.members == original.members
    with pytest.raises(p.SnapshotIntegrityError):
        p.restore_original_plan(base, original.snapshot, transaction_id="foreign", limits=limits)
    later = p.plan_append(original.snapshot, transaction_id="later", serialized_rows=[b"later\n"], limits=limits)
    with pytest.raises(p.SnapshotIntegrityError):
        p.restore_original_plan(base, later.snapshot, transaction_id="original", limits=limits)


def test_member_growth_after_census_cannot_exceed_actual_read_budget(fixture, tmp_path, monkeypatch):
    from tests.test_qledger_conversion_candidate import prepare
    from engine.qledger_store_sources import GitTreeSource, verify_source_snapshot
    from tests.test_qledger_conversion_candidate import git
    repo, _, _, raw, limits = fixture
    # A valid small fixture with a supported large per-part ceiling exposes the
    # distinct aggregate allocation boundary; no large real claims are read.
    limits = replace(limits, part_bytes=4 * 1024 * 1024)
    converted = prepare(fixture, limits=limits)
    git(repo, "update-ref", "refs/remotes/origin/main", converted.candidate_oid)
    base = verify_source_snapshot(GitTreeSource(repo, tree_oid=converted.tree_oid, limits=limits), limits=limits)
    plan = p.plan_append(base, transaction_id="original", serialized_rows=[b"new-original\n"], limits=limits)
    intent = n.NativeClaimsIntent("operation:native", "lane:native", "original")
    write = NativeClaimsWrite(intent, plan, repo / p.BASE_PATH)
    receipt = NativeOperationReceipt(intent.operation_id, intent.lane_id, base, plan.snapshot, ("original",), limits)
    candidate = prepare_native((repo, converted.candidate_oid, raw, limits, receipt), native_operation_receipt=receipt)
    prepared = result.prepare_original_result(write, candidate=candidate, result_id="growth-original", limits=limits)
    root = tmp_path / "growth-evidence"
    root.mkdir(mode=0o700)
    path = root / prepared.result_id
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    native_part = next(payload for relative, payload in base._members.items() if relative.startswith(p.PART_PREFIX))
    target_digest = sha256(native_part).hexdigest()
    read_file = result._read
    consumed, grew = [], []
    def grow_then_read(parent, name, maximum, identities):
        if name == target_digest and not grew:
            # Census already happened. The now-stable file is individually
            # within part_bytes, but exceeds the remaining total by one byte.
            size = limits.snapshot_bytes - sum(consumed) + 1
            (path / "members" / name).write_bytes(b"x" * size)
            grew.append(size)
        payload = read_file(parent, name, maximum, identities)
        consumed.append(len(payload))
        assert sum(consumed) <= limits.snapshot_bytes, "reader allocated past aggregate budget"
        return payload
    monkeypatch.setattr(result, "_read", grow_then_read)
    with pytest.raises(p.SnapshotIntegrityError):
        result.read_original_result(owner_root=root, result_path=path,
            expected_result_id=prepared.result_id, expected_manifest_digest=prepared.manifest_digest,
            expected_claims_path=write.claims_path, expected_intent=write.intent, limits=limits)
    assert grew and sum(consumed) <= limits.snapshot_bytes


def test_growth_during_read_never_allocates_an_extra_probe_byte(tmp_path, monkeypatch):
    target = tmp_path / "original"
    target.write_bytes(b"a")
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    real_read = result.os.read
    observed = []
    def grow(fd, count):
        if not observed:
            with target.open("ab") as handle:
                handle.write(b"b")
        block = real_read(fd, count)
        observed.append(len(block))
        assert sum(observed) <= 1, "read exceeded exact remaining byte budget"
        return block
    monkeypatch.setattr(result.os, "read", grow)
    try:
        with pytest.raises(p.SnapshotIntegrityError):
            result._read(fd, "original", 1, [])
    finally:
        os.close(fd)
    assert sum(observed) <= 1
