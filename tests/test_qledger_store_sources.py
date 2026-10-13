"""Synthetic-only acceptance for inactive Git/locked-local QLedger sources."""

from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zlib

import pytest

from engine import qledger_store_protocol as p
from engine import qledger_store_sources as s


def digest(payload):
    return sha256(payload).hexdigest()


@pytest.fixture
def limits():
    return p.ProtocolLimits(
        base_bytes=8192, part_bytes=256, page_bytes=4096, root_bytes=4096,
        descriptor_bytes=1024, leaf_entries=2, fanout=2, index_levels=3,
        history_operations=32, reference_visits=4096, snapshot_members=128,
        snapshot_bytes=524288, logical_bytes=32768, input_rows=1024,
        publication_objects=1024, git_blob_bytes=16384,
    )


def members(limits, raw=b'{"id":0}\n', *, history=True):
    ref = p.MemberRef(p.BASE_PATH, digest(raw), len(raw))
    root = p.RootRecord(ref, None, 0, len(raw), digest(raw), limits.fingerprint)
    values = {p.BASE_PATH: raw, p.ROOT_PATH: p.encode_root(root, limits=limits)}
    snapshot = p.verify_snapshot(p.InMemorySource(values, snapshot_id="fixture:start"),
                                 root, limits=limits)
    if history:
        for i in range(3):
            plan = p.plan_append(snapshot, transaction_id=f"tx{i}",
                                 serialized_rows=[b'{"same":true}\n'], limits=limits)
            values.update(plan.members)
            values[p.ROOT_PATH] = plan.root_bytes
            snapshot = plan.snapshot
    return values, snapshot


def write_members(root, values):
    root.mkdir(parents=True, exist_ok=True)
    for name, payload in values.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def git(root, *args, input_bytes=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="")
    return subprocess.run(["git", "-C", str(root), *args], input=input_bytes,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True, env=env, timeout=10).stdout


def git_store(root, values):
    write_members(root, values)
    git(root, "init", "-q")
    git(root, "config", "user.name", "Synthetic QLedger Test")
    git(root, "config", "user.email", "synthetic@example.invalid")
    git(root, "config", "core.hooksPath", str(root / "no-hooks"))
    git(root, "add", "--", "data/qledger")
    tree = git(root, "write-tree").decode().strip()
    return tree


def contents(snapshot):
    with p.open_logical_bytes(snapshot) as stream:
        return stream.read()


def assert_error(code, action):
    with pytest.raises(p.SnapshotIntegrityError) as caught:
        action()
    if code is not None:
        assert caught.value.code == code
    return caught.value


def child_lock(lock_path, mode, timeout=0.15):
    code = '''
from pathlib import Path
import sys
from engine.qledger_store_sources import claims_lock
from engine.qledger_store_protocol import SnapshotIntegrityError
try:
    with claims_lock(Path(sys.argv[1]), mode=sys.argv[2], timeout=float(sys.argv[3])):
        print("ACQUIRED")
except SnapshotIntegrityError as e:
    print(e.code)
'''
    result = subprocess.run([sys.executable, "-c", code, str(lock_path), mode, str(timeout)],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.mark.parametrize("raw", [b"", b"unterminated", b'{broken}\n\n', b'{"id":"\xe6\xbc\xa2"}\r\n'])
def test_local_complete_history_exact_bytes_and_post_release_capture(tmp_path, limits, raw):
    values, expected = members(limits, raw)
    root = tmp_path / "store"
    write_members(root, values)
    lock = root / s.LOCK_RELATIVE_PATH
    with s.claims_lock(lock, mode="shared", timeout=0) as lease:
        pin = s.pin_local_root(root, lease=lease, limits=limits)
        assert pin == digest(values[p.ROOT_PATH])
        source = s.LockedLocalSource(root, lease=lease, expected_root_digest=pin, limits=limits)
        snapshot = s.verify_source_snapshot(source, limits=limits)
        refs = source.iter_members()
        assert {r.path for r in refs} == set(values)
        assert all(r.digest == digest(values[r.path]) and r.size == len(values[r.path]) for r in refs)
        assert snapshot.receipt.complete
        assert contents(snapshot) == contents(expected)
    assert contents(snapshot) == contents(expected)
    assert_error("SOURCE_CLOSED", lambda: source.read_member(p.BASE_PATH))
    assert_error("SOURCE_CLOSED", lambda: source.iter_members())
    assert_error("SOURCE_CLOSED", lambda: source.snapshot_id)
    assert_error("SOURCE_CLOSED", lambda: lease.open_root_fd(root))
    assert lock.is_file()


def test_git_pinned_tree_survives_head_and_worktree_changes(tmp_path, limits):
    values, expected = members(limits)
    repo = tmp_path / "repo"
    tree = git_store(repo, values)
    original = git(repo, "commit-tree", tree, input_bytes=b"synthetic original\n").decode().strip()
    git(repo, "update-ref", "refs/heads/main", original)
    git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    source = s.GitTreeSource(repo, tree_oid=tree, limits=limits)
    identity = source.snapshot_id
    changed, _ = members(limits, b'changed legacy bytes\n', history=False)
    write_members(repo, changed)
    git(repo, "add", "--", "data/qledger")
    other_tree = git(repo, "write-tree").decode().strip()
    other = git(repo, "commit-tree", other_tree, "-p", original, input_bytes=b"synthetic other\n").decode().strip()
    git(repo, "update-ref", "refs/heads/main", other, original)
    (repo / p.BASE_PATH).unlink()
    (repo / p.ROOT_PATH).unlink()
    snapshot = s.verify_source_snapshot(source, limits=limits)
    assert contents(snapshot) == contents(expected)
    assert source.snapshot_id == identity
    refs = source.iter_members()
    assert {ref.path for ref in refs} == set(values)
    assert git(repo, "rev-parse", "HEAD").decode().strip() == other


@pytest.mark.parametrize("holder, contender, result", [
    ("shared", "shared", "ACQUIRED"),
    ("shared", "exclusive", "LOCK_TIMEOUT"),
    ("exclusive", "shared", "LOCK_TIMEOUT"),
    ("exclusive", "exclusive", "LOCK_TIMEOUT"),
])
def test_two_process_lock_exclusion_and_stable_inode(tmp_path, limits, holder, contender, result):
    values, _ = members(limits, history=False)
    root = tmp_path / "store"
    write_members(root, values)
    lock = root / s.LOCK_RELATIVE_PATH
    with s.claims_lock(lock, mode=holder, timeout=0) as lease:
        inode = lock.stat().st_ino
        assert lease.root == root and lease.mode == holder
        assert child_lock(lock, contender) == result
        assert lock.stat().st_ino == inode
    assert child_lock(lock, "exclusive") == "ACQUIRED"
    assert lock.stat().st_ino == inode


def test_exception_releases_lock_without_unlink(tmp_path, limits):
    root = tmp_path / "store"
    write_members(root, members(limits, history=False)[0])
    lock = root / s.LOCK_RELATIVE_PATH
    class DeliberateFailure(Exception):
        pass
    with pytest.raises(DeliberateFailure):
        with s.claims_lock(lock, mode="exclusive", timeout=0):
            inode = lock.stat().st_ino
            raise DeliberateFailure
    assert lock.stat().st_ino == inode
    assert child_lock(lock, "exclusive") == "ACQUIRED"


def test_lease_is_opaque_and_qualified_for_root_and_mode(tmp_path, limits):
    values, _ = members(limits, history=False)
    root, other = tmp_path / "one", tmp_path / "two"
    write_members(root, values)
    write_members(other, values)
    assert_error("MALFORMED", s.ClaimsLockLease)
    with pytest.raises(p.SnapshotIntegrityError):
        with s.claims_lock(tmp_path / "unrelated.lock", mode="shared", timeout=0):
            pytest.fail("unrelated lock qualified")
    with s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="shared", timeout=0) as lease:
        assert_error("MALFORMED", lambda: lease.assert_valid(root, exclusive=True))
        assert_error("MALFORMED", lambda: lease.assert_valid(root, exclusive=1))
        assert_error("MALFORMED", lambda: lease.open_root_fd(other))
        assert_error("MALFORMED", lambda: s.LockedLocalSource(other, lease=lease,
                     expected_root_digest=digest(values[p.ROOT_PATH]), limits=limits))
        fd = lease.open_root_fd(root)
        try:
            assert os.fstat(fd).st_ino == root.stat().st_ino
        finally:
            os.close(fd)
        lease.assert_valid(root)
        with pytest.raises(FrozenInstanceError):
            lease._mode = "exclusive"


def test_inherited_lease_refuses_forked_process_without_unlocking_parent(tmp_path, limits):
    root = tmp_path / "store"
    write_members(root, members(limits, history=False)[0])
    # Pytest has service threads. Exercise actual fork/child-release behavior
    # in a fresh single-threaded process, without suppressing a warning.
    probe = '''
from pathlib import Path
import json, os, subprocess, sys
from engine import qledger_store_sources as s
from engine.qledger_store_protocol import SnapshotIntegrityError
root = Path(sys.argv[1])
manager = s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="exclusive", timeout=0)
lease = manager.__enter__()
try:
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        try:
            try:
                lease.assert_valid(root, exclusive=True)
                result = b"BAD_ACCEPTED"
            except SnapshotIntegrityError as exc:
                result = exc.code.encode("ascii")
            manager.__exit__(None, None, None)
            os.write(write_fd, result)
        except BaseException:
            os.write(write_fd, b"UNEXPECTED_CHILD_ERROR")
        finally:
            os.close(write_fd)
            os._exit(0)
    os.close(write_fd)
    result = os.read(read_fd, 128).decode("ascii")
    os.close(read_fd)
    _, status = os.waitpid(pid, 0)
    contender = """from pathlib import Path
import sys
from engine.qledger_store_sources import claims_lock
from engine.qledger_store_protocol import SnapshotIntegrityError
try:
    with claims_lock(Path(sys.argv[1]), mode='exclusive', timeout=0):
        print('BAD_ACQUIRED')
except SnapshotIntegrityError as exc:
    print(exc.code)
"""
    other = subprocess.run([sys.executable, "-c", contender, str(root / s.LOCK_RELATIVE_PATH)],
                           capture_output=True, text=True, timeout=3)
    print(json.dumps({"lease": result, "child_exit": os.waitstatus_to_exitcode(status),
                      "contender_exit": other.returncode, "contender": other.stdout.strip()}))
finally:
    manager.__exit__(None, None, None)
'''
    result = subprocess.run([sys.executable, "-c", probe, str(root)],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"lease": "SOURCE_CLOSED", "child_exit": 0,
                                       "contender_exit": 0, "contender": "LOCK_TIMEOUT"}


@pytest.mark.parametrize("timeout", [True, -1, float("inf"), float("nan"), 31, "0"])
def test_lock_timeout_type_and_limit_rejection(tmp_path, timeout):
    with pytest.raises(p.SnapshotIntegrityError):
        with s.claims_lock(tmp_path / s.LOCK_RELATIVE_PATH, mode="shared", timeout=timeout):
            pytest.fail("invalid timeout acquired")


@pytest.mark.parametrize("mode", ["SHARED", "unknown", 1, None])
def test_lock_mode_rejection(tmp_path, mode):
    with pytest.raises(p.SnapshotIntegrityError):
        with s.claims_lock(tmp_path / s.LOCK_RELATIVE_PATH, mode=mode, timeout=0):
            pytest.fail("invalid mode acquired")


def test_local_source_detects_root_pin_member_and_namespace_changes(tmp_path, limits):
    values, _ = members(limits)
    root = tmp_path / "store"
    write_members(root, values)
    with s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="exclusive", timeout=0) as lease:
        assert_error("SOURCE_CHANGED", lambda: s.LockedLocalSource(root, lease=lease,
                     expected_root_digest="0" * 64, limits=limits))
        source = s.LockedLocalSource(root, lease=lease, expected_root_digest=digest(values[p.ROOT_PATH]), limits=limits)
        (root / p.BASE_PATH).write_bytes(b"different")
        assert_error("SOURCE_CHANGED", lambda: s.verify_source_snapshot(source, limits=limits))
        (root / p.BASE_PATH).write_bytes(values[p.BASE_PATH])
        source = s.LockedLocalSource(root, lease=lease, expected_root_digest=digest(values[p.ROOT_PATH]), limits=limits)
        extra = b"orphan\n"
        (root / (p.PART_PREFIX + digest(extra) + ".jsonl")).write_bytes(extra)
        assert_error("SOURCE_CHANGED", lambda: source.iter_members())


def test_lock_replacement_is_not_accepted_as_same_lease(tmp_path, limits):
    root = tmp_path / "store"
    write_members(root, members(limits, history=False)[0])
    lock = root / s.LOCK_RELATIVE_PATH
    with s.claims_lock(lock, mode="exclusive", timeout=0) as lease:
        lock.rename(lock.with_name("old-lock"))
        lock.write_bytes(b"")
        assert_error("SOURCE_CHANGED", lambda: lease.assert_valid(root))
    assert lock.exists()  # This invocation never deletes a replacement lock.


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "directory"])
def test_local_nonregular_or_alias_member_rejected_without_blocking(tmp_path, limits, kind):
    values, _ = members(limits, history=False)
    root = tmp_path / "store"
    write_members(root, values)
    target = root / p.BASE_PATH
    target.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(values[p.BASE_PATH])
    if kind == "symlink":
        target.symlink_to(outside)
    elif kind == "hardlink":
        os.link(outside, target)
    elif kind == "fifo":
        os.mkfifo(target)
    else:
        target.mkdir()
    with s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="shared", timeout=0) as lease:
        assert_error("MALFORMED", lambda: s.LockedLocalSource(root, lease=lease,
                     expected_root_digest=digest(values[p.ROOT_PATH]), limits=limits))


def test_symlink_ancestor_and_symlink_lock_rejected(tmp_path, limits):
    root = tmp_path / "store"
    write_members(root, members(limits, history=False)[0])
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(p.SnapshotIntegrityError):
        with s.claims_lock(alias / s.LOCK_RELATIVE_PATH, mode="shared", timeout=0):
            pytest.fail("symlink ancestor accepted")
    lock = root / s.LOCK_RELATIVE_PATH
    other = tmp_path / "other-lock"
    other.write_bytes(b"")
    lock.symlink_to(other)
    with pytest.raises(p.SnapshotIntegrityError):
        with s.claims_lock(lock, mode="shared", timeout=0):
            pytest.fail("symlink lock accepted")


@pytest.mark.parametrize("transport", ["git", "local"])
@pytest.mark.parametrize("damage", ["missing_part", "bad_part", "missing_root", "bad_root", "oversize_base", "oversize_part", "unsafe_member", "inventory_limit"])
def test_real_transport_rejects_bad_snapshot_before_success(tmp_path, limits, transport, damage):
    values, _ = members(limits)
    part = next(name for name in values if name.startswith(p.PART_PREFIX))
    effective = limits
    if damage == "missing_part":
        del values[part]
    elif damage == "bad_part":
        values[part] = b"corrupt\n"
    elif damage == "missing_root":
        del values[p.ROOT_PATH]
    elif damage == "bad_root":
        values[p.ROOT_PATH] = b"{}"
    elif damage == "oversize_base":
        values[p.BASE_PATH] = b"x" * (limits.base_bytes + 1)
    elif damage == "oversize_part":
        values[part] = b"x" * (limits.part_bytes + 1)
    elif damage == "unsafe_member":
        values[p.PART_PREFIX + "not-content-addressed.jsonl"] = b"x\n"
    else:
        effective = replace(limits, snapshot_members=2)
    root = tmp_path / "store"
    if transport == "git":
        tree = git_store(root, values)
        with pytest.raises(p.SnapshotIntegrityError):
            source = s.GitTreeSource(root, tree_oid=tree, limits=effective)
            s.verify_source_snapshot(source, limits=effective)
    else:
        write_members(root, values)
        with s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="shared", timeout=0) as lease:
            with pytest.raises(p.SnapshotIntegrityError):
                source = s.LockedLocalSource(root, lease=lease,
                    expected_root_digest=digest(values.get(p.ROOT_PATH, b"")), limits=effective)
                s.verify_source_snapshot(source, limits=effective)


def test_git_symlink_member_and_non_tree_pin_rejected(tmp_path, limits):
    values, _ = members(limits, history=False)
    root = tmp_path / "repo"
    tree = git_store(root, values)
    blob = git(root, "rev-parse", f"{tree}:{p.BASE_PATH}").decode().strip()
    assert_error("MALFORMED", lambda: s.GitTreeSource(root, tree_oid=blob, limits=limits))
    path = root / p.BASE_PATH
    path.unlink()
    path.symlink_to(tmp_path / "external")
    git(root, "add", "--", p.BASE_PATH)
    changed = git(root, "write-tree").decode().strip()
    assert_error("MALFORMED", lambda: s.GitTreeSource(root, tree_oid=changed, limits=limits))


@pytest.mark.parametrize("tree_id", ["HEAD", "main", "a" * 39, "a" * 41, "A" * 40, None, 1])
def test_git_requires_explicit_full_object_id(tmp_path, limits, tree_id):
    assert_error("MALFORMED", lambda: s.GitTreeSource(tmp_path, tree_oid=tree_id, limits=limits))


def test_git_missing_promised_object_never_invokes_transport(tmp_path, limits, monkeypatch):
    values, _ = members(limits, history=False)
    root = tmp_path / "repo"
    tree = git_store(root, values)
    oid = git(root, "rev-parse", f"{tree}:{p.BASE_PATH}").decode().strip()
    (root / ".git" / "objects" / oid[:2] / oid[2:]).unlink()
    marker = tmp_path / "forbidden-transport-invoked"
    binary = tmp_path / "bin"
    binary.mkdir()
    helper = binary / "git-remote-qltest"
    helper.write_text("#!/bin/sh\n: > '" + str(marker) + "'\nexit 1\n")
    helper.chmod(0o700)
    git(root, "config", "remote.origin.url", "qltest://forbidden")
    git(root, "config", "remote.origin.promisor", "true")
    git(root, "config", "core.repositoryformatversion", "1")
    git(root, "config", "extensions.partialClone", "origin")
    monkeypatch.setenv("PATH", str(binary) + os.pathsep + os.environ["PATH"])
    observed = []
    real_popen = s.subprocess.Popen
    def checked(*args, **kwargs):
        env = kwargs["env"]
        assert env["GIT_NO_LAZY_FETCH"] == "1"
        assert env["GIT_ALLOW_PROTOCOL"] == ""
        assert env["GIT_NO_REPLACE_OBJECTS"] == "1"
        observed.append(args[0])
        return real_popen(*args, **kwargs)
    monkeypatch.setattr(s.subprocess, "Popen", checked)
    assert_error("MISSING", lambda: s.GitTreeSource(root, tree_oid=tree, limits=limits))
    assert observed and not marker.exists()
    assert all("fetch" not in command for command in observed)


@pytest.mark.parametrize("object_kind", ["blob", "tree"])
def test_git_object_bytes_must_match_pinned_oid(tmp_path, limits, object_kind):
    values, _ = members(limits, history=False)
    root = tmp_path / "repo"
    tree = git_store(root, values)
    if object_kind == "blob":
        oid = git(root, "rev-parse", f"{tree}:{p.BASE_PATH}").decode().strip()
        payload = b"X" * len(values[p.BASE_PATH])
    else:
        oid = tree
        payload = git(root, "cat-file", "tree", tree).replace(b"data\x00", b"date\x00")
    raw = object_kind.encode() + b" " + str(len(payload)).encode() + b"\x00" + payload
    object_path = root / ".git" / "objects" / oid[:2] / oid[2:]
    # Git created this synthetic loose object read-only. Replace the owned
    # fixture file; do not alter host permissions or a real repository object.
    object_path.unlink()
    object_path.write_bytes(zlib.compress(raw))
    with pytest.raises(p.SnapshotIntegrityError) as caught:
        source = s.GitTreeSource(root, tree_oid=tree, limits=limits)
        s.verify_source_snapshot(source, limits=limits)
    assert caught.value.code == "HASH"


@pytest.mark.parametrize("bad", [bytearray(b"tree\n"), memoryview(b"tree\n"), None])
def test_git_type_provider_cannot_pass_by_semantic_equality(tmp_path, limits, monkeypatch, bad):
    monkeypatch.setattr(s._GitRunner, "run", lambda *args, **kwargs: bad)
    assert_error("MALFORMED", lambda: s.GitTreeSource(tmp_path, tree_oid="a" * 40, limits=limits))


@pytest.mark.parametrize("bad", [bytearray(b"{}"), memoryview(b"{}"), {}, None])
def test_root_provider_must_return_exact_bytes(limits, bad):
    class Provider:
        snapshot_id = "synthetic"
        def read_member(self, path):
            return bad
    assert_error("MALFORMED", lambda: s.verify_source_snapshot(Provider(), limits=limits))


def test_mutable_identity_profile_and_source_fields_rejected(tmp_path, limits):
    values, _ = members(limits, history=False)
    class Provider:
        n = 0
        @property
        def snapshot_id(self):
            self.n += 1
            return f"fixture:{self.n}"
        def read_member(self, path):
            return values[path]
    assert_error(None, lambda: s.verify_source_snapshot(Provider(), limits=limits))
    assert_error("MALFORMED", lambda: s.verify_source_snapshot(Provider(), limits={}))
    root = tmp_path / "repo"
    tree = git_store(root, values)
    source = s.GitTreeSource(root, tree_oid=tree, limits=limits)
    with pytest.raises(FrozenInstanceError):
        source._tree_oid = "b" * 40
    with pytest.raises(TypeError):
        source._entries[p.BASE_PATH] = ("b" * 40, 0)


def test_transport_io_and_deadline_budgets_are_finite(tmp_path, limits):
    values, _ = members(limits, history=False)
    root = tmp_path / "repo"
    tree = git_store(root, values)
    source = s.GitTreeSource(root, tree_oid=tree, limits=limits)
    source._runner.budget.remaining = 0
    assert_error("LIMIT", lambda: source.read_member(p.BASE_PATH))
    source = s.GitTreeSource(root, tree_oid=tree, limits=limits)
    source._runner.budget.deadline = 0
    assert_error("LIMIT", lambda: source.snapshot_id)


def test_snapshot_profile_mismatch_and_retained_anchor_limit_remain_distinct(tmp_path, limits):
    values, _ = members(limits, history=False)
    root = tmp_path / "repo"
    tree = git_store(root, values)
    # Object is already in the accepted synthetic tree; a lower anchor budget
    # still rejects it independently of any new-object publication policy.
    narrow = replace(limits, base_bytes=1)
    assert_error("LIMIT", lambda: s.GitTreeSource(root, tree_oid=tree, limits=narrow))
    source = s.GitTreeSource(root, tree_oid=tree, limits=limits)
    changed = replace(limits, input_rows=limits.input_rows - 1)
    with pytest.raises(p.SnapshotIntegrityError):
        s.verify_source_snapshot(source, limits=changed)


def test_complete_historical_replacement_and_orphan_inventory(tmp_path, limits):
    values, snapshot = members(limits, b"malformed original tail", history=True)
    plan = p.plan_replace_view(snapshot, transaction_id="native-rewrite",
                              expected_view_digest=snapshot.root.logical_digest,
                              replacement_rows=[b'{"new":true}\n'], limits=limits)
    values.update(plan.members)
    values[p.ROOT_PATH] = plan.root_bytes
    orphan = b'{"orphan":true}\n'
    orphan_path = p.PART_PREFIX + digest(orphan) + ".jsonl"
    values[orphan_path] = orphan
    root = tmp_path / "repo"
    tree = git_store(root, values)
    source = s.GitTreeSource(root, tree_oid=tree, limits=limits)
    snapshot = s.verify_source_snapshot(source, limits=limits)
    assert contents(snapshot) == b'{"new":true}\n'
    assert source.read_member(p.BASE_PATH) == b"malformed original tail"
    assert orphan_path in {r.path for r in source.iter_members()}
    assert p.validate_publication(source, snapshot.root, introduced_blobs=[], limits=limits).accepted


def test_pin_helper_rejects_fifo_root_without_opening_a_blocking_reader(tmp_path, limits):
    values, _ = members(limits, history=False)
    root = tmp_path / "store"
    write_members(root, values)
    path = root / p.ROOT_PATH
    path.unlink()
    os.mkfifo(path)
    with s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="shared", timeout=0) as lease:
        assert_error("MALFORMED", lambda: s.pin_local_root(root, lease=lease, limits=limits))


def test_root_directory_replacement_invalidates_lease(tmp_path, limits):
    root = tmp_path / "store"
    values, _ = members(limits, history=False)
    write_members(root, values)
    with s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="exclusive", timeout=0) as lease:
        root.rename(tmp_path / "former-store")
        write_members(root, values)
        assert_error("SOURCE_CHANGED", lambda: lease.assert_valid(root, exclusive=True))


def test_unrelated_qledger_file_does_not_change_claims_snapshot(tmp_path, limits):
    values, expected = members(limits)
    root = tmp_path / "store"
    write_members(root, values)
    with s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="shared", timeout=0) as lease:
        source = s.LockedLocalSource(root, lease=lease,
            expected_root_digest=digest(values[p.ROOT_PATH]), limits=limits)
        (root / "data/qledger/grades.jsonl").write_bytes(b"synthetic sibling\n")
        assert contents(s.verify_source_snapshot(source, limits=limits)) == contents(expected)
        assert "data/qledger/grades.jsonl" not in {r.path for r in source.iter_members()}


@pytest.mark.parametrize("transport", ["git", "local"])
def test_aggregate_orphan_inventory_bytes_are_bounded(tmp_path, limits, transport):
    values, _ = members(limits, history=False)
    for i in range(6):
        payload = bytes([65 + i]) * 200
        values[p.PART_PREFIX + digest(payload) + ".jsonl"] = payload
    narrow = replace(limits, snapshot_bytes=1500)
    root = tmp_path / "store"
    if transport == "git":
        tree = git_store(root, values)
        assert_error("LIMIT", lambda: s.GitTreeSource(root, tree_oid=tree, limits=narrow))
    else:
        write_members(root, values)
        with s.claims_lock(root / s.LOCK_RELATIVE_PATH, mode="shared", timeout=0) as lease:
            assert_error("LIMIT", lambda: s.LockedLocalSource(root, lease=lease,
                expected_root_digest=digest(values[p.ROOT_PATH]), limits=narrow))


def test_missing_cross_process_lock_support_is_not_a_thread_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "fcntl", None)
    with pytest.raises(p.SnapshotIntegrityError) as caught:
        with s.claims_lock(tmp_path / s.LOCK_RELATIVE_PATH, mode="shared", timeout=0):
            pytest.fail("unsupported lock silently accepted")
    assert caught.value.code == "UNSUPPORTED"


def test_output_overrun_stops_exact_owned_process_and_preserves_limit(tmp_path, limits, monkeypatch):
    binary = tmp_path / "bin"
    binary.mkdir()
    marker = tmp_path / "owned-pid"
    helper = binary / "git"
    helper.write_text("#!" + sys.executable + "\n"
                      "import os, sys, time\n"
                      "from pathlib import Path\n"
                      "Path(" + repr(str(marker)) + ").write_text(str(os.getpid()))\n"
                      "sys.stdout.buffer.write(b'x' * 128)\n"
                      "sys.stdout.buffer.flush()\n"
                      "time.sleep(60)\n")
    helper.chmod(0o700)
    monkeypatch.setenv("PATH", str(binary) + os.pathsep + os.environ["PATH"])
    began = time.monotonic()
    assert_error("LIMIT", lambda: s.GitTreeSource(tmp_path, tree_oid="a" * 40, limits=limits))
    assert time.monotonic() - began < 5
    pid = int(marker.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
