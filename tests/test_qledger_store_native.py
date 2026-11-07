"""Synthetic acceptance for the inactive native QLedger materializer.

Every store below is rooted in pytest's temporary directory. No production
writer, financial store, Git publisher, clock hook, or format selector is used.
"""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from engine import qledger_store_native as native
from engine.qledger_store_native import (
    ClaimsStorageError,
    NativeClaimsIntent,
    NativeClaimsSession,
    StorageStatus,
    materialize_plan,
)
from engine.qledger_store_protocol import (
    BASE_PATH,
    PAGE_PREFIX,
    PART_PREFIX,
    ROOT_PATH,
    MemberRef,
    ProtocolLimits,
    RootRecord,
    SnapshotIntegrityError,
    encode_root,
    open_logical_bytes,
    plan_append,
)
from engine.qledger_store_sources import LOCK_RELATIVE_PATH, claims_lock


REPO_ROOT = Path(__file__).resolve().parents[1]


def _intent(tx="tx-1"):
    return NativeClaimsIntent("synthetic-operation", "qualitative-intelligence", tx)


def _store(tmp_path, *, base=b"", limits=None):
    root = tmp_path / "native-store"
    assert REPO_ROOT not in root.resolve().parents and root.resolve() != REPO_ROOT
    (root / BASE_PATH).parent.mkdir(parents=True)
    (root / BASE_PATH).write_bytes(base)
    limits = limits or ProtocolLimits()
    digest = sha256(base).hexdigest()
    record = RootRecord(MemberRef(BASE_PATH, digest, len(base)), None, 0, len(base), digest, limits.fingerprint)
    (root / ROOT_PATH).write_bytes(encode_root(record, limits=limits))
    return root, limits


def _tree(root):
    result = {}
    for path in root.rglob("*"):
        info = path.lstat()
        payload = path.read_bytes() if stat.S_ISREG(info.st_mode) else (
            os.readlink(path) if stat.S_ISLNK(info.st_mode) else None
        )
        result[path.relative_to(root).as_posix()] = (info.st_mode, payload)
    return result


def _bytes(snapshot):
    with open_logical_bytes(snapshot) as stream:
        return stream.read()


def _plan(root, limits, *, tx="tx-1", rows=(b'{"id":"new"}\n',)):
    with NativeClaimsSession(root, intent=_intent(tx), limits=limits) as session:
        return plan_append(
            session.read_snapshot(), transaction_id=tx, serialized_rows=rows, limits=limits,
        )


def _apply(root, limits, plan, *, intent=None):
    with claims_lock(root / LOCK_RELATIVE_PATH, mode="exclusive", timeout=0.1) as lease:
        return materialize_plan(
            plan, root=root, lease=lease, intent=intent or _intent(),
            expected_root_digest=plan.expected_root_digest, limits=limits,
        )


def _install_members(root, plan):
    for path, payload in plan.members.items():
        member = root / path
        member.parent.mkdir(parents=True, exist_ok=True)
        member.write_bytes(payload)


def _no_effect(*args, **kwargs):
    pytest.fail("an effect occurred before complete validation or during a no-op")


def test_native_append_preserves_unterminated_base_and_duplicate_bytes(tmp_path):
    base = b'{"id":"unterminated"}'
    rows = [b'{"id":"duplicate","value":1}\n'] * 2
    root, limits = _store(tmp_path, base=base)
    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        before = session.read_snapshot()
        result = session.append_serialized_rows(iter(rows))
        assert _bytes(session.read_snapshot()) == base + b"".join(rows)
        assert before.root.operation_count == 0
        assert session.read_snapshot().root.operation_count == 1
    assert result.status is StorageStatus.MATERIALIZED
    assert result.root_visibility == "visible" and result.durability_status == "confirmed"
    assert result.clock_status == result.candidate_validation == result.publication_status == "not_attempted"
    assert result.written_members and not result.retained_temporaries
    assert (root / BASE_PATH).read_bytes() == base


def test_native_replace_uses_exact_caller_rows_and_retains_all_history(tmp_path):
    base = b'\n{"id":"a"}\nmalformed\n{"id":"b"}\n'
    root, limits = _store(tmp_path, base=base)
    with NativeClaimsSession(root, intent=_intent("append"), limits=limits) as session:
        session.append_serialized_rows([b'{"id":"c"}\n'])
    old_members = {path: value for path, value in _tree(root).items() if path.startswith((PART_PREFIX, PAGE_PREFIX))}
    rows = [b'{"id":"a","stamp":"caller"}\n', b'{"id":"b"}\n', b'{"id":"c"}\n']
    with NativeClaimsSession(root, intent=_intent("replacement"), limits=limits) as session:
        expected = session.read_snapshot().root.logical_digest
        result = session.replace_serialized_rows(rows, expected_view_digest=expected)
        assert _bytes(session.read_snapshot()) == b"".join(rows)
        assert session.read_snapshot().root.operation_count == 2
    assert result.status is StorageStatus.MATERIALIZED
    assert (root / BASE_PATH).read_bytes() == base
    for path, value in old_members.items():
        assert _tree(root)[path] == value


def test_native_empty_append_is_a_write_free_noop(tmp_path, monkeypatch):
    root, limits = _store(tmp_path, base=b'{"id":"base"}\n')
    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        before = _tree(root)
        monkeypatch.setattr(native, "_new_temp", _no_effect)
        result = session.append_serialized_rows([])
        assert _tree(root) == before
    assert result.status is StorageStatus.NOOP
    assert result.reason == "empty_append"
    assert result.clock_status == "not_attempted"
    assert not result.written_members and not result.created_directories


def test_native_retry_after_later_append_is_idempotent_and_clock_unknown(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    with NativeClaimsSession(root, intent=_intent("first"), limits=limits) as session:
        session.append_serialized_rows([b'{"id":"first"}\n'])
    with NativeClaimsSession(root, intent=_intent("later"), limits=limits) as session:
        session.append_serialized_rows([b'{"id":"later"}\n'])
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with NativeClaimsSession(root, intent=_intent("first"), limits=limits) as session:
        result = session.append_serialized_rows([b'{"id":"first"}\n'])
        assert _bytes(session.read_snapshot()) == b'{"id":"first"}\n{"id":"later"}\n'
    assert result.status is StorageStatus.ALREADY_APPLIED
    assert result.clock_status == result.durability_status == "uncertain"
    assert _tree(root) == before


@pytest.mark.parametrize("mode", ["append_conflict", "stale_replace", "input_limit"])
def test_native_planner_failures_precede_effects(tmp_path, monkeypatch, mode):
    limits = ProtocolLimits(input_rows=1) if mode == "input_limit" else ProtocolLimits()
    root, limits = _store(tmp_path, limits=limits)
    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        session.append_serialized_rows([b'{"id":"first"}\n'])
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        with pytest.raises(SnapshotIntegrityError) as caught:
            if mode == "append_conflict":
                session.append_serialized_rows([b'{"id":"different"}\n'])
            elif mode == "stale_replace":
                session.replace_serialized_rows([b'{"id":"replacement"}\n'], expected_view_digest="0" * 64)
            else:
                session.append_serialized_rows([b'{"id":1}\n', b'{"id":2}\n'])
    assert caught.value.code in {"CONFLICT", "LIMIT"}
    assert _tree(root) == before


@pytest.mark.parametrize("field", ["operation_id", "lane_id", "transaction_id"])
@pytest.mark.parametrize("value", ["", "../escape", "has\nnewline", 7])
def test_native_intent_requires_explicit_bounded_identity(field, value):
    fields = dict(operation_id="operation", lane_id="lane", transaction_id="transaction")
    fields[field] = value
    with pytest.raises(SnapshotIntegrityError, match="MALFORMED"):
        NativeClaimsIntent(**fields)


def test_native_requires_explicit_absolute_root_and_open_session(tmp_path):
    with pytest.raises(SnapshotIntegrityError, match="UNSAFE_PATH"):
        NativeClaimsSession(Path("relative"), intent=_intent(), limits=ProtocolLimits())
    root, limits = _store(tmp_path)
    session = NativeClaimsSession(root, intent=_intent(), limits=limits)
    with pytest.raises(SnapshotIntegrityError, match="SESSION"):
        session.read_snapshot()
    with session:
        captured = session.read_snapshot()
    assert _bytes(captured) == b""
    with pytest.raises(SnapshotIntegrityError, match="SESSION"):
        session.read_snapshot()
    with pytest.raises(SnapshotIntegrityError, match="SESSION"):
        with session:
            pass


def test_native_session_reuses_one_exclusive_lease_and_releases_on_exception(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    actual_lock = native.claims_lock
    calls = []

    def counted(*args, **kwargs):
        calls.append((args, kwargs))
        return actual_lock(*args, **kwargs)

    monkeypatch.setattr(native, "claims_lock", counted)
    with pytest.raises(ValueError, match="caller failure"):
        with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
            session.read_snapshot()
            session.append_serialized_rows([b'{"id":"one"}\n'])
            raise ValueError("caller failure")
    assert len(calls) == 1 and calls[0][1]["mode"] == "exclusive"
    lock_inode = (root / LOCK_RELATIVE_PATH).stat().st_ino
    with claims_lock(root / LOCK_RELATIVE_PATH, mode="exclusive", timeout=0):
        pass
    assert (root / LOCK_RELATIVE_PATH).stat().st_ino == lock_inode


def test_native_materializer_rejects_shared_lease_before_effects(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with claims_lock(root / LOCK_RELATIVE_PATH, mode="shared", timeout=0) as lease:
        with pytest.raises(ClaimsStorageError) as caught:
            materialize_plan(
                plan, root=root, lease=lease, intent=_intent(),
                expected_root_digest=plan.expected_root_digest, limits=limits,
            )
    assert caught.value.outcome.status is StorageStatus.FAILED_BEFORE_ROOT
    assert _tree(root) == before


@pytest.mark.parametrize("failure", ["unverified_plan", "wrong_intent", "wrong_expected_root"])
def test_native_public_plan_and_identity_validation_precedes_effects(tmp_path, monkeypatch, failure):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with claims_lock(root / LOCK_RELATIVE_PATH, mode="exclusive", timeout=0) as lease:
        with pytest.raises(ClaimsStorageError) as caught:
            materialize_plan(
                object() if failure == "unverified_plan" else plan,
                root=root, lease=lease,
                intent=_intent("other") if failure == "wrong_intent" else _intent(),
                expected_root_digest="0" * 64 if failure == "wrong_expected_root" else plan.expected_root_digest,
                limits=limits,
            )
    assert caught.value.outcome.status is StorageStatus.FAILED_BEFORE_ROOT
    assert _tree(root) == before


def test_native_stale_root_cas_preserves_newer_history(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    old_plan = _plan(root, limits)
    with NativeClaimsSession(root, intent=_intent("winner"), limits=limits) as session:
        session.append_serialized_rows([b'{"id":"winner"}\n'])
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with pytest.raises(ClaimsStorageError) as caught:
        _apply(root, limits, old_plan)
    assert caught.value.code == "CONFLICT"
    assert caught.value.outcome.status is StorageStatus.FAILED_BEFORE_ROOT
    assert _tree(root) == before


def test_native_existing_identical_immutable_members_are_reused(tmp_path):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    _install_members(root, plan)
    identities = {path: (root / path).stat().st_ino for path in plan.members}
    result = _apply(root, limits, plan)
    assert result.status is StorageStatus.MATERIALIZED
    assert not result.written_members
    assert set(result.reused_members) == set(plan.members)
    for path, payload in plan.members.items():
        assert (root / path).read_bytes() == payload
        assert (root / path).stat().st_ino == identities[path]


def test_native_existing_conflicting_immutable_member_is_never_overwritten(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    path = next(iter(plan.members))
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"foreign immutable bytes\n")
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with pytest.raises(ClaimsStorageError) as caught:
        _apply(root, limits, plan)
    assert caught.value.outcome.status is StorageStatus.FAILED_BEFORE_ROOT
    assert _tree(root) == before


@pytest.mark.parametrize("kind", ["root_file_symlink", "parts_symlink", "catalog_symlink", "member_symlink", "member_fifo"])
def test_native_unsafe_member_paths_fail_without_following_or_overwriting(tmp_path, monkeypatch, kind):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "sentinel").write_bytes(b"outside must remain unchanged")
    if kind == "root_file_symlink":
        (outside / "root").write_bytes((root / ROOT_PATH).read_bytes())
        (root / ROOT_PATH).unlink()
        (root / ROOT_PATH).symlink_to(outside / "root")
    elif kind in {"parts_symlink", "catalog_symlink"}:
        directory = PART_PREFIX.rstrip("/") if kind == "parts_symlink" else PAGE_PREFIX.rstrip("/")
        (root / directory).symlink_to(outside, target_is_directory=True)
    else:
        path = next(path for path in plan.members if path.startswith(PART_PREFIX))
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        if kind == "member_symlink":
            (root / path).symlink_to(outside / "sentinel")
        else:
            os.mkfifo(root / path)
    before, outside_before = _tree(root), _tree(outside)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with pytest.raises(SnapshotIntegrityError):
        _apply(root, limits, plan)
    assert _tree(root) == before and _tree(outside) == outside_before


@pytest.mark.parametrize("component", ["store", "data", "qledger"])
def test_native_symlink_ancestors_do_not_bind_a_writer_session(tmp_path, component):
    root, limits = _store(tmp_path)
    path = root if component == "store" else (root / "data" if component == "data" else root / "data/qledger")
    moved = tmp_path / "moved"
    path.rename(moved)
    path.symlink_to(moved, target_is_directory=True)
    before = _tree(moved)
    with pytest.raises(SnapshotIntegrityError):
        with NativeClaimsSession(root, intent=_intent(), limits=limits):
            pytest.fail("unsafe source acquired a native writer session")
    assert _tree(moved) == before


def test_native_partial_write_keeps_old_root_and_owned_partial_for_explicit_retry(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    old_root = (root / ROOT_PATH).read_bytes()
    actual_write = native._write_all

    def partial(fd, payload):
        os.write(fd, payload[:3])
        raise OSError("synthetic partial write")

    monkeypatch.setattr(native, "_write_all", partial)
    with pytest.raises(ClaimsStorageError) as caught:
        with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
            session.append_serialized_rows([b'{"id":"new"}\n'])
    failed = caught.value.outcome
    assert failed.status is StorageStatus.FAILED_BEFORE_ROOT
    assert failed.root_visibility == "unchanged" and failed.clock_status == "not_attempted"
    assert failed.retained_temporaries and (root / ROOT_PATH).read_bytes() == old_root
    partial_bytes = {path: (root / path).read_bytes() for path in failed.retained_temporaries}
    monkeypatch.setattr(native, "_write_all", actual_write)
    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        result = session.append_serialized_rows([b'{"id":"new"}\n'])
        assert _bytes(session.read_snapshot()) == b'{"id":"new"}\n'
    assert result.status is StorageStatus.MATERIALIZED
    assert {path: (root / path).read_bytes() for path in partial_bytes} == partial_bytes


def test_native_file_durability_failure_precedes_root_replacement(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    old_root = (root / ROOT_PATH).read_bytes()

    def failed_sync(fd):
        raise OSError("synthetic file durability failure")

    monkeypatch.setattr(native, "_sync_file", failed_sync)
    with pytest.raises(ClaimsStorageError) as caught:
        with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
            session.append_serialized_rows([b'{"id":"new"}\n'])
    result = caught.value.outcome
    assert result.status is StorageStatus.FAILED_BEFORE_ROOT
    assert result.retained_temporaries and not result.written_members
    assert (root / ROOT_PATH).read_bytes() == old_root


@pytest.mark.parametrize("failure", ["replace_return_uncertain", "root_directory_fsync"])
def test_native_after_root_failure_is_uncertain_and_retry_never_runs_clock_or_rewrites(tmp_path, monkeypatch, failure):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    actual_replace, actual_sync = native.os.replace, native._sync_dir

    if failure == "replace_return_uncertain":
        def uncertain_replace(*args, **kwargs):
            actual_replace(*args, **kwargs)
            raise OSError("synthetic lost replace acknowledgement")
        monkeypatch.setattr(native.os, "replace", uncertain_replace)
    else:
        def failed_root_sync(fd):
            if (root / ROOT_PATH).read_bytes() == plan.root_bytes:
                raise OSError("synthetic root directory durability failure")
            return actual_sync(fd)
        monkeypatch.setattr(native, "_sync_dir", failed_root_sync)

    with pytest.raises(ClaimsStorageError) as caught:
        _apply(root, limits, plan)
    result = caught.value.outcome
    assert result.status is StorageStatus.ROOT_EFFECT_UNCERTAIN
    assert result.clock_status == result.durability_status == "uncertain"
    assert result.candidate_root_digest == plan.snapshot.receipt.root_digest
    assert (root / ROOT_PATH).read_bytes() == plan.root_bytes
    if failure == "replace_return_uncertain":
        assert result.root_visibility == "unknown"
        assert result.uncertain_temporaries and not result.retained_temporaries
    else:
        assert result.root_visibility == "visible"
    monkeypatch.setattr(native.os, "replace", actual_replace)
    monkeypatch.setattr(native, "_sync_dir", actual_sync)
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        retry = session.append_serialized_rows([b'{"id":"new"}\n'])
    assert retry.status is StorageStatus.ALREADY_APPLIED
    assert retry.clock_status == "uncertain" and _tree(root) == before


def test_native_immutable_install_and_directory_durability_precede_root_visibility(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    events = []
    file_sync, dir_sync, replace = native._sync_file, native._sync_dir, native.os.replace

    def synced_file(fd):
        file_sync(fd)
        events.append(("file", os.fstat(fd).st_ino))

    def synced_directory(fd):
        dir_sync(fd)
        events.append(("directory", os.fstat(fd).st_ino))

    def checked_replace(*args, **kwargs):
        for path, payload in plan.members.items():
            target = root / path
            assert target.read_bytes() == payload
            assert ("file", target.stat().st_ino) in events
            assert ("directory", target.parent.stat().st_ino) in events
        events.append(("root_replace",))
        return replace(*args, **kwargs)

    monkeypatch.setattr(native, "_sync_file", synced_file)
    monkeypatch.setattr(native, "_sync_dir", synced_directory)
    monkeypatch.setattr(native.os, "replace", checked_replace)
    result = _apply(root, limits, plan)
    assert result.status is StorageStatus.MATERIALIZED
    assert events[-1][0] == "directory"
    assert ("root_replace",) in events


def test_native_root_change_after_member_install_is_preserved_as_conflict(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    other = _plan(root, limits, tx="other", rows=[b'{"id":"other"}\n'])
    _install_members(root, other)
    original_sync = native._sync_dir
    changed = False
    own_part = next(path for path in plan.members if path.startswith(PART_PREFIX))

    def race(fd):
        nonlocal changed
        original_sync(fd)
        if not changed and (root / own_part).exists():
            changed = True
            # A deliberately uncooperative synthetic writer. The materializer
            # must detect its new root, preserve it, and never roll it back.
            (root / ROOT_PATH).write_bytes(other.root_bytes)

    monkeypatch.setattr(native, "_sync_dir", race)
    with pytest.raises(ClaimsStorageError) as caught:
        _apply(root, limits, plan)
    assert changed
    assert caught.value.outcome.status is StorageStatus.FAILED_BEFORE_ROOT
    assert (root / ROOT_PATH).read_bytes() == other.root_bytes
    assert (root / own_part).read_bytes() == plan.members[own_part]


def test_native_complete_orphan_inventory_capacity_is_checked_before_effects(tmp_path, monkeypatch):
    limits = ProtocolLimits(snapshot_members=5)
    root, limits = _store(tmp_path, limits=limits)
    plan = _plan(root, limits)
    payload = b"synthetic orphan\n"
    orphan = root / (PART_PREFIX + sha256(payload).hexdigest() + ".jsonl")
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(payload)
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with pytest.raises(ClaimsStorageError) as caught:
        _apply(root, limits, plan)
    assert caught.value.outcome.status is StorageStatus.FAILED_BEFORE_ROOT
    assert caught.value.code in {"LIMIT", "NONRETRYABLE_CAPACITY"}
    assert _tree(root) == before


def test_native_failed_session_cannot_silently_continue(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)

    def fail(fd):
        raise OSError("durability denied")

    monkeypatch.setattr(native, "_sync_file", fail)
    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        with pytest.raises(ClaimsStorageError):
            session.append_serialized_rows([b'{"id":"new"}\n'])
        with pytest.raises(SnapshotIntegrityError, match="SESSION"):
            session.read_snapshot()


def test_native_two_processes_hold_read_dedupe_plan_cas_under_one_lease(tmp_path):
    root, limits = _store(tmp_path)
    script = r"""
from pathlib import Path
import sys, time
from engine.qledger_store_native import NativeClaimsIntent, NativeClaimsSession
from engine.qledger_store_protocol import ProtocolLimits, open_logical_bytes
root = Path(sys.argv[1])
with NativeClaimsSession(root, intent=NativeClaimsIntent("operation", "lane", sys.argv[2]), limits=ProtocolLimits(), lock_timeout=5) as session:
    with open_logical_bytes(session.read_snapshot()) as stream:
        present = stream.read()
    if b'{"id":"shared"}\n' not in present:
        time.sleep(0.1)
        result = session.append_serialized_rows([b'{"id":"shared"}\n'])
        print(result.status.value)
    else:
        print("deduped-under-lease")
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(root), tx],
            cwd=tmp_path, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        for tx in ["process-a", "process-b"]
    ]
    try:
        results = [worker.communicate(timeout=15) for worker in workers]
        assert [worker.returncode for worker in workers] == [0, 0], results
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
                worker.communicate(timeout=5)
    assert sorted(out.strip() for out, err in results) == ["deduped-under-lease", "materialized"]
    with NativeClaimsSession(root, intent=_intent("inspect"), limits=limits) as session:
        assert _bytes(session.read_snapshot()) == b'{"id":"shared"}\n'
        assert session.read_snapshot().root.operation_count == 1


def test_native_replace_retry_after_later_append_preserves_newer_view(tmp_path, monkeypatch):
    root, limits = _store(tmp_path, base=b'{"id":"old"}\n')
    with NativeClaimsSession(root, intent=_intent("replace"), limits=limits) as session:
        original_view = session.read_snapshot().root.logical_digest
        session.replace_serialized_rows([b'{"id":"replacement"}\n'], expected_view_digest=original_view)
    with NativeClaimsSession(root, intent=_intent("later"), limits=limits) as session:
        session.append_serialized_rows([b'{"id":"later"}\n'])
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with NativeClaimsSession(root, intent=_intent("replace"), limits=limits) as session:
        outcome = session.replace_serialized_rows(
            [b'{"id":"replacement"}\n'], expected_view_digest=original_view,
        )
        assert _bytes(session.read_snapshot()) == b'{"id":"replacement"}\n{"id":"later"}\n'
    assert outcome.status is StorageStatus.ALREADY_APPLIED
    assert outcome.clock_status == "uncertain" and _tree(root) == before


def test_native_expired_lease_cannot_materialize_a_valid_plan(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    plan = _plan(root, limits)
    with claims_lock(root / LOCK_RELATIVE_PATH, mode="exclusive", timeout=0) as lease:
        pass
    before = _tree(root)
    monkeypatch.setattr(native, "_new_temp", _no_effect)
    with pytest.raises(ClaimsStorageError) as caught:
        materialize_plan(
            plan, root=root, lease=lease, intent=_intent(),
            expected_root_digest=plan.expected_root_digest, limits=limits,
        )
    assert caught.value.outcome.status is StorageStatus.FAILED_BEFORE_ROOT
    assert _tree(root) == before


def test_native_lease_release_receipt_failure_does_not_erase_materialized_effect(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    actual_lock = native.claims_lock

    class LostReleaseReceipt:
        def __init__(self, context):
            self.context = context

        def __enter__(self):
            return self.context.__enter__()

        def __exit__(self, *args):
            self.context.__exit__(*args)
            raise OSError("synthetic release acknowledgement failure")

    monkeypatch.setattr(
        native, "claims_lock",
        lambda *args, **kwargs: LostReleaseReceipt(actual_lock(*args, **kwargs)),
    )
    session = NativeClaimsSession(root, intent=_intent(), limits=limits)
    with pytest.raises(ClaimsStorageError) as caught:
        with session:
            successful = session.append_serialized_rows([b'{"id":"materialized"}\n'])
    result = caught.value.outcome
    assert result.status is StorageStatus.ROOT_EFFECT_UNCERTAIN
    assert result.reason == "lease_release_failed"
    assert result.candidate_root_digest == successful.candidate_root_digest
    assert result.root_visibility == "visible" and result.durability_status == "confirmed"
    assert session.last_outcome is result
    with actual_lock(root / LOCK_RELATIVE_PATH, mode="exclusive", timeout=0):
        pass


def test_native_atomic_root_preserves_existing_mode_under_restrictive_umask(tmp_path):
    root, limits = _store(tmp_path)
    (root / ROOT_PATH).chmod(0o640)
    previous = os.umask(0o077)
    try:
        with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
            session.append_serialized_rows([b'{"id":"new"}\n'])
    finally:
        os.umask(previous)
    assert stat.S_IMODE((root / ROOT_PATH).stat().st_mode) == 0o640


@pytest.mark.parametrize("method", ["append", "replace"])
@pytest.mark.parametrize("failure", ["malformed_row", "serialization_error"])
def test_native_planning_failure_has_outcome_and_stops_bound_session(
    tmp_path, monkeypatch, method, failure,
):
    root, limits = _store(tmp_path, base=b'{"id":"before"}\n')
    intent = _intent("planning-failure")
    monkeypatch.setattr(native, "_new_temp", _no_effect)

    def broken_rows():
        yield b'{"id":"prepared-but-not-written"}\n'
        raise RuntimeError("synthetic caller serialization failure")

    with NativeClaimsSession(root, intent=intent, limits=limits) as session:
        snapshot = session.read_snapshot()
        before = _tree(root)
        rows = ["not-immutable-bytes"] if failure == "malformed_row" else broken_rows()
        with pytest.raises(ClaimsStorageError) as caught:
            if method == "append":
                session.append_serialized_rows(rows)
            else:
                session.replace_serialized_rows(
                    rows, expected_view_digest=snapshot.root.logical_digest,
                )
        outcome = caught.value.outcome
        assert outcome.status is StorageStatus.FAILED_BEFORE_ROOT
        assert outcome.reason == "planning_failed"
        assert outcome.intent is intent
        assert outcome.expected_root_digest == outcome.observed_root_digest == snapshot.receipt.root_digest
        assert outcome.candidate_root_digest is outcome.transaction_digest is None
        assert outcome.root_visibility == "unchanged"
        assert outcome.clock_status == outcome.durability_status == "not_attempted"
        assert not outcome.written_members and not outcome.retained_temporaries
        assert session.last_outcome is outcome
        if failure == "malformed_row":
            assert outcome.failure_code == "MALFORMED"
        else:
            planner_error = caught.value.__cause__
            assert isinstance(planner_error, SnapshotIntegrityError)
            assert outcome.failure_code == planner_error.code
            assert outcome.failure_message == str(planner_error)
            assert "RuntimeError" in outcome.failure_message
        for action in (
            session.read_snapshot,
            lambda: session.append_serialized_rows([]),
            lambda: session.replace_serialized_rows(
                [], expected_view_digest=snapshot.root.logical_digest,
            ),
        ):
            with pytest.raises(SnapshotIntegrityError, match="SESSION"):
                action()
            assert session.last_outcome is outcome
        assert _tree(root) == before
    with claims_lock(root / LOCK_RELATIVE_PATH, mode="exclusive", timeout=0.1):
        pass


@pytest.mark.parametrize("close_phase", ["before_close", "after_close"])
@pytest.mark.parametrize("failure_count", [1, 2])
def test_native_final_close_failures_preserve_confirmed_effect_and_attempt_each_fd_once(
    tmp_path, monkeypatch, close_phase, failure_count,
):
    root, limits = _store(tmp_path)
    old_root = (root / ROOT_PATH).read_bytes()
    real_close = os.close
    attempted = []
    withheld = []
    failures = []

    def close_fault(fd):
        final_directory = (
            sys._getframe(1).f_code.co_name == "materialize_plan"
            and stat.S_ISDIR(os.fstat(fd).st_mode)
        )
        if not final_directory:
            return real_close(fd)
        attempted.append(fd)
        should_fail = len(attempted) <= failure_count
        if should_fail and close_phase == "before_close":
            withheld.append(fd)
        else:
            real_close(fd)
        if should_fail:
            error = OSError(f"synthetic final close failure {len(attempted)}")
            failures.append(error)
            raise error

    try:
        with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
            monkeypatch.setattr(native.os, "close", close_fault)
            with pytest.raises(ClaimsStorageError) as caught:
                session.append_serialized_rows([b'{"id":"durably-visible"}\n'])
            outcome = caught.value.outcome
            assert len(attempted) == len(set(attempted)) == 4
            assert len(failures) == failure_count
            assert len(caught.value.__notes__) == failure_count
            assert caught.value.__cause__ is failures[0]
            assert outcome.status is StorageStatus.ROOT_EFFECT_UNCERTAIN
            assert outcome.reason == "descriptor_cleanup_failed"
            assert outcome.root_visibility == "visible"
            assert outcome.durability_status == "confirmed"
            assert outcome.clock_status == "not_attempted"
            assert outcome.failure_message == str(failures[0])
            assert (root / ROOT_PATH).read_bytes() != old_root
            assert outcome.candidate_root_digest == sha256((root / ROOT_PATH).read_bytes()).hexdigest()
            assert session.last_outcome is outcome
            with pytest.raises(SnapshotIntegrityError, match="SESSION"):
                session.read_snapshot()
    finally:
        monkeypatch.setattr(native.os, "close", real_close)
        # These are this fixture's deliberately withheld, still-owned fds.
        # The materializer must not retry their ambiguous failed close.
        for fd in withheld:
            real_close(fd)
    with claims_lock(root / LOCK_RELATIVE_PATH, mode="exclusive", timeout=0.1):
        pass


@pytest.mark.parametrize("failure_phase", ["before_root", "lost_root_ack"])
def test_native_cleanup_notes_preserve_prior_error_and_all_known_effect_facts(
    tmp_path, monkeypatch, failure_phase,
):
    root, limits = _store(tmp_path)
    old_root = (root / ROOT_PATH).read_bytes()
    real_close = os.close
    real_replace = os.replace
    attempted = []
    primary = SnapshotIntegrityError("CONFLICT", "synthetic primary storage failure")

    def close_fault(fd):
        final_directory = (
            sys._getframe(1).f_code.co_name == "materialize_plan"
            and stat.S_ISDIR(os.fstat(fd).st_mode)
        )
        real_close(fd)
        if final_directory:
            attempted.append(fd)
            if len(attempted) <= 2:
                raise OSError(f"synthetic secondary close failure {len(attempted)}")

    def fail_write(fd, payload):
        raise primary

    def replace_loses_ack(*args, **kwargs):
        real_replace(*args, **kwargs)
        raise primary

    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        monkeypatch.setattr(native.os, "close", close_fault)
        if failure_phase == "before_root":
            monkeypatch.setattr(native, "_write_all", fail_write)
        else:
            monkeypatch.setattr(native.os, "replace", replace_loses_ack)
        with pytest.raises(ClaimsStorageError) as caught:
            session.append_serialized_rows([b'{"id":"candidate"}\n'])
        outcome = caught.value.outcome
        assert len(attempted) == len(set(attempted)) == 4
        assert len(caught.value.__notes__) == 2
        assert all("synthetic secondary close failure" in note for note in caught.value.__notes__)
        assert caught.value.__cause__ is primary
        assert outcome.failure_code == primary.code
        assert outcome.failure_message == str(primary)
        assert outcome.reason != "descriptor_cleanup_failed"
        assert session.last_outcome is outcome
        if failure_phase == "before_root":
            assert outcome.status is StorageStatus.FAILED_BEFORE_ROOT
            assert outcome.root_visibility == "unchanged"
            assert outcome.durability_status == outcome.clock_status == "not_attempted"
            assert (root / ROOT_PATH).read_bytes() == old_root
            assert outcome.retained_temporaries
        else:
            assert outcome.status is StorageStatus.ROOT_EFFECT_UNCERTAIN
            assert outcome.root_visibility == "unknown"
            assert outcome.durability_status == outcome.clock_status == "uncertain"
            assert (root / ROOT_PATH).read_bytes() != old_root


def test_native_noop_final_close_failure_is_structured_without_root_effect(tmp_path, monkeypatch):
    root, limits = _store(tmp_path)
    real_close = os.close
    attempted = []

    def close_fault(fd):
        final_directory = (
            sys._getframe(1).f_code.co_name == "materialize_plan"
            and stat.S_ISDIR(os.fstat(fd).st_mode)
        )
        real_close(fd)
        if final_directory:
            attempted.append(fd)
            if len(attempted) == 1:
                raise OSError("synthetic no-op close acknowledgement lost")

    with NativeClaimsSession(root, intent=_intent(), limits=limits) as session:
        before = _tree(root)
        monkeypatch.setattr(native, "_new_temp", _no_effect)
        monkeypatch.setattr(native.os, "close", close_fault)
        with pytest.raises(ClaimsStorageError) as caught:
            session.append_serialized_rows([])
        outcome = caught.value.outcome
        assert len(attempted) == len(set(attempted)) == 2
        assert outcome.status is StorageStatus.FAILED_BEFORE_ROOT
        assert outcome.root_visibility == "unchanged"
        assert outcome.clock_status == outcome.durability_status == "not_attempted"
        assert not outcome.written_members and not outcome.retained_temporaries
        assert session.last_outcome is outcome
        assert _tree(root) == before
