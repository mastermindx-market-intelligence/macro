"""Focused synthetic helper checks only. Never calls outer_run or inner_run."""
import base64
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path("/tmp/market-os-beta-namespace-probe.py")
POSTREAD = Path("/tmp/market-os-beta-accepted-postread-v3.stdout.json")
raw = SOURCE.read_bytes()
compile(raw, str(SOURCE), "exec")
spec = importlib.util.spec_from_file_location("namespace_review", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
source_sha = hashlib.sha256(raw).hexdigest()
print("SYNTHETIC_HELPERS_ONLY; no namespace/service/host or operational probe invocation", flush=True)
print("source", str(SOURCE), "bytes", len(raw), "sha256", source_sha, flush=True)
checked = []


def check(name, fn):
    fn()
    checked.append(name)
    print("PASS", name, flush=True)


def rejects(fn, error=m.ProbeError):
    try:
        fn()
    except error:
        return
    raise AssertionError("expected refusal")


postraw = POSTREAD.read_bytes()
post = json.loads(postraw)
binding = {
    "schema": "mastermind.attended.beta_namespace_binding.v1",
    "probe_sha256": source_sha, "protected_owner_R": post["protected_owner_R"],
    "accepted_postread_sha256": hashlib.sha256(postraw).hexdigest(),
    "accepted_postread_base64": base64.b64encode(postraw).decode(),
    "uid": 987, "gid": 981, "public_relative_path": "coverage.json",
    "cache_probe_nonce": "c" * 32,
}


def binding_checks():
    got, evidence, service = m.parse_binding(json.dumps(binding))
    assert evidence["all_checks_pass"] is True
    assert service["MainPID"] == "2427329" and got["uid"] == 987
    broken = dict(post, checks=dict(post["checks"], runtime_record_valid=None))
    brokenraw = json.dumps(broken).encode()
    bad = dict(binding, accepted_postread_base64=base64.b64encode(brokenraw).decode(),
               accepted_postread_sha256=hashlib.sha256(brokenraw).hexdigest())
    rejects(lambda: m.parse_binding(json.dumps(bad)))
    rejects(lambda: m.public_relative("../coverage.json"))


check("exact retained postread binding; missing/None gate and traversal refuse", binding_checks)


def credentials():
    status = {"Uid": [987] * 4, "Gid": [981] * 4, "Groups": [981],
              "CapInh": 0, "CapPrm": 0, "CapEff": 0, "CapBnd": 0,
              "CapAmb": 0, "NoNewPrivs": 1}
    m.require_credentials(status, 987, 981, [981])
    for changed in (dict(status, CapEff=1), dict(status, NoNewPrivs=0),
                    dict(status, Uid=[0] * 4), dict(status, Groups=[])):
        rejects(lambda c=changed: m.require_credentials(c, 987, 981, [981]))


check("exact dropped credentials; root, capability, NNP and group mismatch refuse", credentials)


def mounts():
    raw_table = (
        "10 10 8:1 / / rw - ext4 /dev/x rw\n"
        "11 10 8:1 /data /opt/data rw - ext4 /dev/x rw\n"
        "12 11 8:1 /data /opt/data ro - ext4 /dev/x rw\n"
        "13 12 8:1 /space\\040dir /opt/data/space\\040dir ro - ext4 /dev/x rw\n"
    ).encode()
    table = m.parse_mountinfo(raw_table)
    assert table[13]["point"] == "/opt/data/space dir"
    assert m.mount_ancestor(table, 12, 13)
    assert not m.mount_ancestor(table, 12, 11)
    with patch.object(m, "kernel_read", return_value=b"pos:\t0\nmnt_id:\t12\n"), \
         patch.object(m.os, "fstat", return_value=SimpleNamespace(st_dev=os.makedev(8, 1))):
        selected = m.fd_mount(99, table)
    assert selected["id"] == 12 and selected["options"] == ["ro"]
    assert selected["super_options"] == ["rw"]


check("escaped mount path and actual descriptor ID select ro stacked bind over rw superblock", mounts)

real_open, real_write, real_fsync = os.open, os.write, os.fsync


def fixture_chain(directory):
    class Chain:
        def __init__(self, *unused):
            self.fd = None
        def __enter__(self):
            self.fd = real_open(directory, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
            self.original = os.fstat(self.fd)
            return self
        def verify(self):
            assert m.identity(os.fstat(self.fd), True) == m.identity(self.original, True)
            assert m.inode(os.stat(directory)) == m.inode(self.original)
        def __exit__(self, *unused):
            os.close(self.fd)
    return Chain


def refusal_checks():
    with tempfile.TemporaryDirectory(prefix="namespace-refusal-fixture-") as directory:
        leaf = Path(directory) / "data.json"
        leaf.write_bytes(b'{"public":true}\n')
        before = leaf.read_bytes()
        meta = dict(m.info(leaf.stat()), path="/fixture/data.json",
                    sha256=hashlib.sha256(before).hexdigest(), mount={"options": ["ro"]})
        with patch.object(m, "DirectoryChain", fixture_chain(directory)):
            opened = m.refusal("/fixture/data.json", meta, {})
            assert opened["opened"] and not opened["accepted_denial"]
            assert leaf.read_bytes() == before and m.info(leaf.stat()) == {
                k: meta[k] for k in m.info(leaf.stat())}
            for err, accepted in ((errno.EROFS, True), (errno.EACCES, True),
                                  (errno.EPERM, True), (errno.ENOENT, False),
                                  (errno.ELOOP, False)):
                seen = []
                def fail_open(name, flags, *args, **kwargs):
                    assert name == "data.json"
                    seen.append(flags)
                    raise OSError(err, "synthetic denial")
                with patch.object(m.os, "open", side_effect=fail_open):
                    got = m.refusal("/fixture/data.json", meta, {})
                assert got["accepted_denial"] is accepted
                assert seen == [os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW]
            rw = dict(meta, mount={"options": ["rw"]})
            with patch.object(m.os, "open", side_effect=OSError(errno.EACCES, "synthetic")):
                assert not m.refusal("/fixture/data.json", rw, {})["accepted_denial"]


check("existing data open success closes unchanged; exact flags/errno/ro qualification", refusal_checks)


def cache_case(kind):
    with tempfile.TemporaryDirectory(prefix="namespace-cache-fixture-") as directory:
        name = ".market-os-namespace-acceptance-" + "d" * 32
        path = Path(directory) / name
        result = {}
        original_term = signal.signal(signal.SIGTERM, m.interrupted)
        patches = []
        if kind == "collision":
            path.write_bytes(b"existing unrelated fixture")
        if kind == "short_write":
            patches.append(patch.object(m.os, "write",
                side_effect=lambda fd, value: real_write(fd, value[:7])))
        if kind == "fsync_failure":
            patches.append(patch.object(m.os, "fsync",
                side_effect=OSError(errno.EIO, "synthetic fsync failure")))
        if kind == "term_after_write":
            def term_write(fd, value):
                written = real_write(fd, value)
                os.kill(os.getpid(), signal.SIGTERM)
                return written
            patches.append(patch.object(m.os, "write", side_effect=term_write))
        if kind == "term_after_create":
            def term_open(leaf, flags, *args, **kwargs):
                fd = real_open(leaf, flags, *args, **kwargs)
                assert leaf == name
                os.kill(os.getpid(), signal.SIGTERM)
                return fd
            patches.append(patch.object(m.os, "open", side_effect=term_open))
        if kind == "replaced":
            def replace_then_fail(fd):
                path.unlink()
                path.write_bytes(b"replacement must survive")
                raise OSError(errno.EIO, "synthetic concurrent replacement")
            patches.append(patch.object(m.os, "fsync", side_effect=replace_then_fail))
        try:
            for item in patches:
                item.start()
            with patch.object(m, "DirectoryChain", fixture_chain(directory)), \
                 patch.object(m, "fd_mount", return_value={"options": ["rw"]}):
                if kind == "success":
                    m.own_cache_file(os.geteuid(), os.getegid(), "d" * 32, {}, result)
                else:
                    expected_error = (OSError if kind in
                                      ("fsync_failure", "collision", "replaced") else m.ProbeError)
                    rejects(lambda: m.own_cache_file(
                        os.geteuid(), os.getegid(), "d" * 32, {}, result), expected_error)
        finally:
            for item in reversed(patches):
                item.stop()
            signal.signal(signal.SIGTERM, original_term)
        if kind == "collision":
            assert not result["created"] and path.read_bytes() == b"existing unrelated fixture"
        elif kind == "replaced":
            assert result["cleanup_unresolved"] and not result["cleanup_complete"]
            assert path.read_bytes() == b"replacement must survive"
        else:
            assert result["created"] and result["cleanup_complete"] and not path.exists()
            if kind == "success":
                assert result["create_read"]["pass"] and result["update_read"]["pass"]
            if kind == "short_write":
                assert result["last_write"]["written"] == 7


for kind in ("success", "short_write", "fsync_failure", "term_after_write",
             "term_after_create", "collision", "replaced"):
    check("private cache " + kind + " with identity-bound exact cleanup", lambda k=kind: cache_case(k))


def timeout_receipt():
    class FakeChild:
        pid, returncode = 999999, None
        def communicate(self, *args, **kwargs):
            raise subprocess.TimeoutExpired(["synthetic-owned-child"], kwargs.get("timeout", 0))
        def poll(self):
            return None
        def terminate(self):
            self.terminated = True
        def kill(self):
            self.killed = True
    child = FakeChild()
    result = {}
    with patch.object(m.subprocess, "Popen", return_value=child):
        rejects(lambda: m.bounded_child(["never-executed"], b"no code", result),
                subprocess.TimeoutExpired)
    assert child.terminated and child.killed
    assert result["owned_probe_forced_kill"] and result["owned_probe_completion_unresolved"]
    assert result["cache_cleanup_unobserved"]


check("final child-wait timeout retains forced-kill and unobserved completion flags", timeout_receipt)
assert SOURCE.read_bytes() == raw, "source changed during focused validation"
print(json.dumps({"synthetic_check_groups_passed": len(checked),
                  "source_sha256": source_sha,
                  "operational_namespace_probe_run": False,
                  "scope": "pure helpers and isolated temporary fixtures; real own-process "
                  "TERM signals only in the two cache bookkeeping checks"},
                 sort_keys=True), flush=True)
