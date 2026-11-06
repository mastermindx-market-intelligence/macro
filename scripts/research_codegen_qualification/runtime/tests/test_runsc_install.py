#!/usr/bin/env python3
"""Hermetic tests for the rf-runsc installer v2 correction.

Every engine test uses an injected fake command runner and a temporary
fictional filesystem (contract production paths resolved under a temp root),
plus a TEST-ONLY Contract with fictional pins/sizes.  The production Contract
constants are asserted intact and are never weakened or monkeypatched.
Nothing here touches a real daemon, config, socket, service or archive
download.  BoundedRunner unit tests spawn only /bin/cat, /bin/sleep and
/bin/false with injected budgets; no allowlisted production binary exists on
the test host and none is invoked.  No result asserts actual host acceptance.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import io
import itertools
import json
import os
import shutil
import stat
import tarfile
import tempfile
import unittest

import importlib.util

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "runsc_install", os.path.join(_HERE, "runsc_install.py"))
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

os.umask(0o022)

# ---- TEST-ONLY contract (fictional pins; production constants untouched) --- #
RUNSC_SIZE = 300000          # > 262144: proves the config cap never applies
SIDE_SIZES = {
    "gvisor-bin/checkpointgofer": 4000,
    "gvisor-bin/gvisor-sentry-prewarmer": 300,
    "gvisor-bin/gvisor_sentry": 5000,
    "gvisor-bin/runsc-fd-parking": 200,
    "gvisor-bin/runsc-metric-server": 6000,
}
TEST_MEMBER_SIZES = dict(SIDE_SIZES)
TEST_MEMBER_SIZES["runsc"] = RUNSC_SIZE
EXPANDED = sum(TEST_MEMBER_SIZES.values())
VERSION_TAG = "19700101.0"


def payload(tag: str, size: int, elf: bool = False) -> bytes:
    head = b"\x7fELF" if elf else b"#!/bin/sh\nmastermind-test\n"
    unit = (tag + "|0123456789abcdef|").encode()
    body = unit * (size // len(unit) + 2)
    return (head + body)[:size]


MEMBER_PAYLOADS = {"runsc": payload("runsc", RUNSC_SIZE, elf=True)}
for _n, _s in SIDE_SIZES.items():
    MEMBER_PAYLOADS[_n] = payload(_n.split("/")[-1], _s)
MEMBER_SHA = {n: hashlib.sha256(b).hexdigest()
              for n, b in MEMBER_PAYLOADS.items()}
RUNSC_SHA = MEMBER_SHA["runsc"]


def build_tar_bytes(members, with_dir=True):
    """members: list of (name, bytes).  Returns bzip2-compressed tar bytes."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:bz2") as tf:
        if with_dir:
            ti = tarfile.TarInfo(mod.GVISOR_BIN_DIR + "/")
            ti.type = tarfile.DIRTYPE
            ti.mode = 0o755
            tf.addfile(ti)
        for name, data in members:
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            ti.mode = 0o755
            tf.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


GOOD_ARCHIVE_BYTES = build_tar_bytes(
    [(n, MEMBER_PAYLOADS[n]) for n in
     ["runsc", "gvisor-bin/checkpointgofer", "gvisor-bin/gvisor-sentry-prewarmer",
      "gvisor-bin/gvisor_sentry", "gvisor-bin/runsc-fd-parking",
      "gvisor-bin/runsc-metric-server"]])
GOOD_ARCHIVE_SHA = hashlib.sha256(GOOD_ARCHIVE_BYTES).hexdigest()
GOOD_ARCHIVE_SIZE = len(GOOD_ARCHIVE_BYTES)

TEST_CONTRACT = mod.Contract(archive_sha256=GOOD_ARCHIVE_SHA,
                             archive_size=GOOD_ARCHIVE_SIZE,
                             runsc_member_sha256=RUNSC_SHA,
                             member_sizes=TEST_MEMBER_SIZES,
                             expanded_total=EXPANDED,
                             version_tag=VERSION_TAG)

SHIM_PAYLOAD = payload("shim", 900)


def single_member_tar(name, data, truncate_to=None):
    """One-member tar (bz2-compressed).  Optionally truncated mid-member so
    the header declares more bytes than the stream actually holds."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        ti = tarfile.TarInfo(name)
        ti.size = len(data)
        ti.mode = 0o755
        tf.addfile(ti, io.BytesIO(data))
    raw = buf.getvalue()
    if truncate_to is not None:
        raw = raw[:truncate_to]
    import bz2
    return bz2.compress(raw)


# ---- config fixture (private sentinel values must never leak) -------------- #
SENTINEL_URL = "https://registry.internal.corp:5443"
SENTINEL_TOKEN = "s3cr3tTOKEN-value-9f8e7d6c"
CONFIG_OBJ = {
    "debug": False,
    "live-restore": True,
    "default-runtime": "runc",
    "data-root": "/var/lib/docker",
    "registry-mirrors": [SENTINEL_URL],
    "auths": {"reg.example.com": {"auth": SENTINEL_TOKEN}},
    "runtimes": {
        "nvidia": {"path": "nvidia-container-runtime", "runtimeArgs": []},
        "runc": {"path": "runc"},
    },
}
CONFIG_BYTES = (json.dumps(CONFIG_OBJ, indent=2) + "\n").encode("utf-8")

SHOW_OK = (
    b"ActiveState=active\nSubState=running\nLoadState=loaded\nCanReload=yes\n"
    b'ExecReload={ path=/bin/kill ; argv[]=/bin/kill -s HUP $MAINPID ; '
    b"ignore_errors=no ; start_time=[Mon 2026-10-13 12:00:00 UTC] }\n")
SHOW_FAILED = (
    b"ActiveState=failed\nSubState=failed\nLoadState=loaded\nCanReload=yes\n"
    b'ExecReload={ path=/bin/kill ; argv[]=/bin/kill -s HUP $MAINPID ; '
    b"ignore_errors=no ; start_time=[Mon 2026-10-13 12:00:00 UTC] }\n")
SHOW_NO_HUP = (
    b"ActiveState=active\nSubState=running\nLoadState=loaded\nCanReload=yes\n"
    b'ExecReload={ path=/bin/true ; argv[]=/bin/true ; ignore_errors=no }\n')


# The runtime entry path as the engine sees it (layout-resolved in tests):
# fixtures must script the daemon reporting the same resolved path.
RUNTIME_PATH_RESOLVED = [TEST_CONTRACT.runsc_path]


def entry():
    return {"path": RUNTIME_PATH_RESOLVED[0],
            "runtimeArgs": list(mod.RUNSC_RUNTIME_ARGS)}


def runtimes_json(with_rf=False):
    mapping = {
        "nvidia": {"path": "nvidia-container-runtime", "runtimeArgs": []},
        "runc": {"path": "runc"},
    }
    if with_rf:
        mapping["rf-runsc"] = entry()
    return (json.dumps(mapping) + "\n").encode("utf-8")


class Clock:
    def __init__(self, start=1000.0):
        self.t = float(start)

    def __call__(self):
        return self.t

    def bump(self, d=1.0):
        self.t += d


class FakeRunner:
    """Scripted fake command runner: records argv, replays finite responses,
    classifies exactly like the production runner and freezes on refusal."""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []
        self.frozen = False

    def script(self, **kw):
        self.responses.append(kw)

    def run(self, argv, timeout=None, role="main"):
        if self.frozen:
            raise mod.EffectFrozen()
        mod.validate_argv(argv, mod.ALLOWED_BINARIES)
        resp = dict(self.responses.pop(0)) if self.responses else {}
        resp.setdefault("rc", 0)
        resp.setdefault("out", b"")
        resp.setdefault("err", b"")
        resp.setdefault("timed_out", False)
        resp.setdefault("truncated", False)
        rec = {"binary": argv[0], "argv_tail": list(argv[1:4]), "argv": list(argv),
               "role": role, "rc": resp["rc"], "timed_out": resp["timed_out"],
               "truncated": resp["truncated"], "out_len": len(resp["out"]),
               "err_len": len(resp["err"]),
               "out_sha256": hashlib.sha256(resp["out"]).hexdigest(),
               "err_sha256": hashlib.sha256(resp["err"]).hexdigest()}
        self.calls.append(rec)
        refused, category = mod.classify_outcome(argv[0], resp["rc"],
                                                 resp["timed_out"],
                                                 len(resp["err"]) > 0)
        rec["refused"], rec["category"] = refused, category
        if refused:
            self.frozen = True
            raise mod.InstallError(category)
        return {"rc": resp["rc"], "out": resp["out"], "err": resp["err"],
                "timed_out": resp["timed_out"], "truncated": resp["truncated"]}

    def freeze(self):
        self.frozen = True


def script_preflight(r, rf_in_info=False, show=SHOW_OK, default=b"runc\n",
                     total=b"0\n", running=b"0\n"):
    r.script(out=b"29.1.3\n")                    # client version
    r.script(out=b"29.1.3\n")                    # server version
    r.script(out=b"mastermind-pc\n")             # info Name
    r.script(out=b"daemon-id-1234\n")            # info ID
    r.script(out=b"linux\n")                     # info OSType
    r.script(out=b"x86_64\n")                    # info Architecture
    r.script(out=total)                          # info Containers
    r.script(out=running)                        # info ContainersRunning
    r.script(out=default)                        # info DefaultRuntime
    r.script(out=runtimes_json(with_rf=rf_in_info))  # info Runtimes
    r.script(out=show)                           # systemctl show


def script_poll(r, rf=False, show=SHOW_OK, default=b"runc\n"):
    r.script(out=b"daemon-id-1234\n")
    r.script(out=show)
    r.script(out=runtimes_json(with_rf=rf))
    r.script(out=default)


def script_happy(r, polls_before_rf=2):
    script_preflight(r)
    r.script(rc=0, out=b"", err=b"")             # dockerd --validate
    r.script(rc=0, out=b"", err=b"")             # reload
    for _ in range(polls_before_rf):
        script_poll(r, rf=False)
    script_poll(r, rf=True)


class Fixture:
    """Temporary fictional filesystem mirroring the production layout."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="rf-runsc-test-")
        self.layout = mod.Layout.under_root(self.tmp)
        self.chown_calls = []
        os.makedirs(os.path.dirname(self.layout.daemon_json))
        self._write(self.layout.daemon_json, CONFIG_BYTES, 0o644)
        RUNTIME_PATH_RESOLVED[0] = self.layout.p(TEST_CONTRACT.runsc_path)
        self.archive_path = self.tmp + "/gvisor-x86_64.tar.bz2"
        self._write(self.archive_path, GOOD_ARCHIVE_BYTES, 0o644)
        self.scratch = self.tmp + "/scratch"
        os.mkdir(self.scratch, 0o700)
        self.binding_dict = {
            "schema": mod.BINDING_SCHEMA,
            "root_id": mod.ROOT_ID,
            "operation_id": "op-test-1",
            "effect_commission_token": "ROOT-EFFECT-COMMISSION-0001",
            "archive_path": self.archive_path,
            "member_sha256": dict(MEMBER_SHA),
            "operation_scratch_dir": self.scratch,
            "binary_version_path": TEST_CONTRACT.runsc_path,
        }
        self.binding_path = os.path.join(self.tmp, "binding.json")
        self.write_binding()
        self.runner = FakeRunner()
        self.clock = Clock()

    # -- fixture helpers -- #
    @staticmethod
    def _write(path, data, mode):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        try:
            os.write(fd, data)
            os.chmod(path, mode)
        finally:
            os.close(fd)

    @staticmethod
    def overwrite(path, data, mode):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        try:
            os.write(fd, data)
            os.chmod(path, mode)
        finally:
            os.close(fd)

    def write_binding(self, **changes):
        self.binding_dict.update(changes)
        raw = json.dumps(self.binding_dict, indent=2).encode("utf-8")
        if os.path.exists(self.binding_path):
            self.overwrite(self.binding_path, raw, 0o600)
        else:
            self._write(self.binding_path, raw, 0o600)
        self.binding_sha = hashlib.sha256(raw).hexdigest()

    @staticmethod
    def fake_rename_noreplace(src, dst):
        # Hermetic state-machine seam only; real Linux primitive tests remain separate.
        if os.path.lexists(dst):
            raise FileExistsError(errno.EEXIST, "fixture destination occupied", dst)
        os.rename(src, dst)

    def engine(self, **over):
        params = dict(
            contract=TEST_CONTRACT,
            euid=os.geteuid(),
            root_uid=os.geteuid(),
            root_gid=os.getegid(),
            chown_fn=lambda p, u, g: self.chown_calls.append((p, u, g)),
            rename_fn=self.fake_rename_noreplace,
            socket_inspector=lambda path, uid: {"is_socket": True,
                                                "uid": uid, "mode": 0o755},
            platform_probe=lambda: ("Linux", "x86_64"),
            disk_free_fn=lambda p: 1 << 40,
            monotonic=self.clock,
            budget=mod.Budget(monotonic=self.clock),
            sleeper=lambda s: self.clock.bump(1.0),
            settlement_window_seconds=60.0,
            settlement_interval_seconds=1.0,
        )
        params.update(over)
        return mod.InstallEngine(self.layout, self.runner, **params)

    def version_dir(self):
        return self.layout.p(TEST_CONTRACT.version_dir)

    def write_exact_bundle(self):
        d = self.version_dir()
        os.makedirs(d + "/" + mod.GVISOR_BIN_DIR)
        for name, data in MEMBER_PAYLOADS.items():
            self._write(d + "/" + name, data, 0o755)
        return d

    def config_now(self):
        with open(self.layout.daemon_json, "rb") as fh:
            return fh.read()

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def reloads_of(runner, role=None):
    out = []
    for c in runner.calls:
        if c["binary"] == mod.SUDO_BIN and "reload" in c["argv"]:
            if role is None or c["role"] == role:
                out.append(c)
    return out


class ProductionPinTests(unittest.TestCase):
    def test_production_contract_pins_are_intact(self):
        self.assertEqual(sum(mod.REQUIRED_MEMBERS.values()), 284471010)
        self.assertEqual(mod.REQUIRED_MEMBERS["runsc"], 109966750)
        self.assertEqual(mod.RUNSC_MEMBER_SHA256,
                         "210b437a9cfae51e8f8c9074ed19b8b5e59477178e2e391a18117d8d6b924f7a")
        self.assertEqual(mod.ARCHIVE_SHA256,
                         "bd4eb2ca0ee74f0fbbb5f5273ba011e79c56a29fbb047393b88b981cd3230ede")
        self.assertEqual(mod.ARCHIVE_SIZE_BYTES, 166822039)
        self.assertEqual(mod.ARCHIVE_MAX_BYTES, 200 * 1024 * 1024)
        self.assertEqual(mod.REQUIRED_MEMBERS["gvisor-bin/checkpointgofer"], 69128994)
        self.assertEqual(mod.REQUIRED_MEMBERS["gvisor-bin/gvisor-sentry-prewarmer"], 1416)
        self.assertEqual(mod.REQUIRED_MEMBERS["gvisor-bin/gvisor_sentry"], 52149808)
        self.assertEqual(mod.REQUIRED_MEMBERS["gvisor-bin/runsc-fd-parking"], 1320)
        self.assertEqual(mod.REQUIRED_MEMBERS["gvisor-bin/runsc-metric-server"], 53222722)
        self.assertEqual(mod.RUNSC_BINARY_PATH,
                         "/usr/local/lib/mastermind/research-factory/runsc/"
                         "20261005.0/runsc")
        self.assertEqual(mod.RUNSC_RUNTIME_ARGS,
                         ["--platform=systrap", "--network=none", "--oci-seccomp"])
        self.assertEqual(mod.EXPECTED_DOCKER_VERSION, "29.1.3")
        # the production contract is a distinct object from the test contract
        # and is never modified by tests
        self.assertIsNot(mod.PRODUCTION_CONTRACT, TEST_CONTRACT)
        self.assertEqual(mod.PRODUCTION_CONTRACT.member_sizes, mod.REQUIRED_MEMBERS)
        self.assertEqual(TEST_CONTRACT.member_sizes, TEST_MEMBER_SIZES)

    def test_runtime_entry_uses_root_selected_oci_seccomp(self):
        self.assertIn("--oci-seccomp", mod.RUNSC_RUNTIME_ARGS)
        self.assertIn("--platform=systrap", mod.RUNSC_RUNTIME_ARGS)
        self.assertIn("--network=none", mod.RUNSC_RUNTIME_ARGS)


class UnitTests(unittest.TestCase):
    def test_classify_rc0_stderr_technical_and_timeout(self):
        self.assertEqual(mod.classify_outcome(mod.SUDO_BIN, 0, False, False),
                         (False, None))
        self.assertEqual(mod.classify_outcome(mod.SUDO_BIN, 0, False, True),
                         (True, "CONTROL_STDERR_WITH_RC0"))
        self.assertEqual(mod.classify_outcome(mod.SYSTEMCTL_BIN, 0, False, True)[0],
                         True)
        self.assertEqual(mod.classify_outcome(mod.DOCKER_BIN, 0, False, True)[0], True)
        self.assertEqual(mod.classify_outcome(mod.DOCKERD_BIN, 0, False, True),
                         (False, None))  # validator stderr text is not a control error
        self.assertEqual(mod.classify_outcome(mod.SUDO_BIN, 1, False, False),
                         (True, "SUDO_NONZERO_AMBIGUOUS_REFUSAL"))
        self.assertEqual(mod.classify_outcome(mod.SYSTEMCTL_BIN, 126, False, False)[0],
                         True)
        self.assertEqual(mod.classify_outcome(mod.DOCKER_BIN, 1, False, False),
                         (True, "DOCKER_QUERY_UNVERIFIED_NONZERO"))
        self.assertEqual(mod.classify_outcome(mod.DOCKERD_BIN, 1, False, False),
                         (False, "VALIDATION_TECHNICAL_FAILURE"))
        self.assertEqual(mod.classify_outcome(mod.DOCKER_BIN, None, True, False),
                         (True, "COMMAND_TIMEOUT_UNKNOWN"))

    def test_validate_argv_structural_allowlist(self):
        good = [mod.SUDO_BIN, "-n", mod.SYSTEMCTL_BIN, "reload",
                mod.DOCKER_SERVICE_UNIT]
        mod.validate_argv(good, mod.ALLOWED_BINARIES)
        with self.assertRaises(mod.InstallError):
            mod.validate_argv(["/bin/sh", "-c", "id"], mod.ALLOWED_BINARIES)
        with self.assertRaises(mod.InstallError):
            mod.validate_argv([mod.SUDO_BIN, mod.SYSTEMCTL_BIN, "reload"],
                              mod.ALLOWED_BINARIES)
        with self.assertRaises(mod.InstallError):
            mod.validate_argv([mod.SUDO_BIN, "-l"], mod.ALLOWED_BINARIES)
        with self.assertRaises(mod.InstallError):
            mod.validate_argv([], mod.ALLOWED_BINARIES)

    def test_minimal_env_has_no_ambient_docker_context(self):
        runner = mod.BoundedRunner(mod.Budget())
        for key in mod.FORBIDDEN_ENV_KEYS:
            self.assertNotIn(key, runner.env)
            self.assertNotIn(key, mod.MINIMAL_ENV)

    def test_budget_main_and_rollback_reserves_are_independent(self):
        ticks = itertools.count(start=1000.0, step=1.0)
        b = mod.Budget(total_seconds=10.0, combined_output_bytes=100,
                       rollback_reserve_seconds=6.0, rollback_reserve_output_bytes=50,
                       monotonic=lambda: next(ticks))
        self.assertFalse(b.expired())
        b.spend_output(30)
        self.assertEqual(b.out_left(), 20)
        self.assertFalse(b.spend_output(21))
        self.assertEqual(b.out_left(True), 50)   # rollback reserve untouched
        seq2 = iter([1000.0, 1200.0, 1200.0])
        b2 = mod.Budget(total_seconds=10.0, rollback_reserve_seconds=6.0,
                        monotonic=lambda: next(seq2))
        self.assertTrue(b2.expired())
        seq3 = iter([1000.0, 1010.0, 1011.0, 1011.5])
        b3 = mod.Budget(total_seconds=10.0, rollback_reserve_seconds=6.0,
                        monotonic=lambda: next(seq3))
        self.assertTrue(b3.expired())
        b3.begin_rollback()
        self.assertTrue(b3.expired(rollback=True))  # total deadline cannot be renewed

    def test_json_strict_rejects_duplicate_keys_and_nonobject(self):
        with self.assertRaises(mod.InstallError) as ctx:
            mod.json_loads_strict('{"a":1,"a":2}', "x")
        self.assertEqual(ctx.exception.category, "DUPLICATE_JSON_KEY")
        with self.assertRaises(mod.InstallError) as ctx:
            mod.json_loads_strict("[1,2]", "x")
        self.assertEqual(ctx.exception.category, "CONFIG_TOPLEVEL_NOT_OBJECT")
        with self.assertRaises(mod.InstallError):
            mod.json_loads_strict('{"a":', "x")

    def test_check_ancestors_rejects_symlink_owner_and_mode(self):
        tmp = tempfile.mkdtemp(prefix="rf-anc-")
        try:
            good = tmp + "/etc/docker/daemon.json"
            os.makedirs(tmp + "/etc/docker")
            self.assertIsNone(mod.check_ancestors(good, os.geteuid(), base=tmp))
            os.chmod(tmp + "/etc", 0o777)
            with self.assertRaises(mod.InstallError):
                mod.check_ancestors(good, os.geteuid(), base=tmp)
            os.chmod(tmp + "/etc", 0o755)
            os.rename(tmp + "/etc/docker", tmp + "/etc/real")
            os.symlink("real", tmp + "/etc/docker")
            with self.assertRaises(mod.InstallError):
                mod.check_ancestors(good, os.geteuid(), base=tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_additive_proof_accepts_exact_addition_and_discriminates(self):
        cand = json.loads(CONFIG_BYTES.decode("utf-8"))
        cand["runtimes"]["rf-runsc"] = entry()
        added = mod.assert_exact_addition(CONFIG_OBJ, cand, entry())
        self.assertEqual(added, ["runtimes.rf-runsc"])
        bad = json.loads(json.dumps(cand))
        bad["live-restore"] = False
        with self.assertRaises(mod.InstallError) as ctx:
            mod.assert_exact_addition(CONFIG_OBJ, bad, entry())
        self.assertEqual(ctx.exception.category, "ADDITIVE_PROOF_FAILED")
        bad2 = json.loads(json.dumps(cand))
        bad2["runtimes"]["nvidia"]["path"] = "something-else"
        with self.assertRaises(mod.InstallError):
            mod.assert_exact_addition(CONFIG_OBJ, bad2, entry())
        bad3 = json.loads(json.dumps(cand))
        del bad3["debug"]
        with self.assertRaises(mod.InstallError):
            mod.assert_exact_addition(CONFIG_OBJ, bad3, entry())
        bad4 = json.loads(json.dumps(cand))
        bad4["runtimes"]["rf-runsc"]["runtimeArgs"] = ["--platform=systrap"]
        with self.assertRaises(mod.InstallError):
            mod.assert_exact_addition(CONFIG_OBJ, bad4, entry())

    def test_binding_rejects_missing_placeholder_and_wrong_member_set(self):
        fx = Fixture()
        try:
            base = dict(fx.binding_dict)
            mod.Binding(base, TEST_CONTRACT)  # ok
            for field in ("binary_version_path", "operation_scratch_dir",
                          "archive_path", "member_sha256",
                          "effect_commission_token"):
                missing = dict(base)
                missing.pop(field)
                with self.assertRaises(mod.InstallError):
                    mod.Binding(missing, TEST_CONTRACT)
            for placeholder in ("UNSET", "TBD", "PENDING", "PLACEHOLDER", "", "0" * 64):
                ph = dict(base)
                ph["effect_commission_token"] = placeholder
                with self.assertRaises(mod.InstallError) as ctx:
                    mod.Binding(ph, TEST_CONTRACT)
                self.assertEqual(ctx.exception.category, "BINDING_PIN_PLACEHOLDER")
            wrong_root = dict(base)
            wrong_root["root_id"] = "0" * 64
            with self.assertRaises(mod.InstallError):
                mod.Binding(wrong_root, TEST_CONTRACT)
            wrong_path = dict(base)
            wrong_path["binary_version_path"] = "/usr/local/bin/runsc"
            with self.assertRaises(mod.InstallError):
                mod.Binding(wrong_path, TEST_CONTRACT)
            wrong_members = dict(base)
            wrong_members["member_sha256"] = {k: v for k, v in base["member_sha256"].items()
                                              if k != "gvisor-bin/runsc-fd-parking"}
            with self.assertRaises(mod.InstallError) as ctx:
                mod.Binding(wrong_members, TEST_CONTRACT)
            self.assertEqual(ctx.exception.category, "BINDING_MEMBER_SET_UNEXPECTED")
            wrong_runsc = dict(base)
            wrong_runsc["member_sha256"] = dict(base["member_sha256"])
            wrong_runsc["member_sha256"]["runsc"] = "a" * 64
            with self.assertRaises(mod.InstallError) as ctx:
                mod.Binding(wrong_runsc, TEST_CONTRACT)
            self.assertEqual(ctx.exception.category, "BINDING_RUNSC_PIN_MISMATCH")
            weak_token = dict(base)
            weak_token["effect_commission_token"] = "root"
            with self.assertRaises(mod.InstallError):
                mod.Binding(weak_token, TEST_CONTRACT)
            rel_scratch = dict(base)
            rel_scratch["operation_scratch_dir"] = "relative/path"
            with self.assertRaises(mod.InstallError):
                mod.Binding(rel_scratch, TEST_CONTRACT)
        finally:
            fx.close()


class ArchiveTests(unittest.TestCase):
    """Archive-pin and member-scan discriminators against fictional fixtures.

    The 262144 B config cap must never apply to members: the synthetic runsc
    member here is 300000 bytes."""

    def setUp(self):
        self.fx = Fixture()
        self.engine = self.fx.engine()
        self.engine.binding = mod.Binding(dict(self.fx.binding_dict), TEST_CONTRACT)

    def tearDown(self):
        self.fx.close()

    def test_synthetic_member_above_config_cap_is_scanned(self):
        self.assertGreater(RUNSC_SIZE, mod.LIMITS["max_config_read_bytes"])
        facts = self.engine._scan_archive(staging_dir=None)
        self.assertEqual(sorted(facts["members_installed"]), sorted(TEST_MEMBER_SIZES))
        self.assertFalse(facts["shim_installed"])

    def test_optional_shim_member_tolerated_never_installed(self):
        data = build_tar_bytes(
            [(n, MEMBER_PAYLOADS[n]) for n in TEST_MEMBER_SIZES]
            + [(mod.OPTIONAL_SHIM_MEMBER, SHIM_PAYLOAD)])
        self.fx.overwrite(self.fx.archive_path, data, 0o644)
        facts = self.engine._scan_archive(staging_dir=None)
        self.assertFalse(facts["shim_installed"])

    def test_missing_sidecar_rejected(self):
        members = [(n, MEMBER_PAYLOADS[n]) for n in TEST_MEMBER_SIZES
                   if n != "gvisor-bin/runsc-metric-server"]
        self.fx.overwrite(self.fx.archive_path,
                          build_tar_bytes(members), 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertEqual(ctx.exception.category, "ARCHIVE_MEMBER_MISSING")

    def test_wrong_member_hash_rejected(self):
        tampered = dict(MEMBER_PAYLOADS)
        tampered["gvisor-bin/gvisor_sentry"] = payload("tampered", 5000)
        data = build_tar_bytes([(n, tampered[n]) for n in TEST_MEMBER_SIZES])
        self.fx.overwrite(self.fx.archive_path, data, 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertEqual(ctx.exception.category, "ARCHIVE_MEMBER_HASH_MISMATCH")

    def test_size_metadata_mismatch_rejected_before_stream(self):
        # header declares 5000 bytes for a member pinned at 4000: rejected
        # before any streaming
        self.fx.overwrite(self.fx.archive_path,
                          single_member_tar("gvisor-bin/checkpointgofer",
                                            payload("big", 5000)), 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertEqual(ctx.exception.category, "ARCHIVE_MEMBER_SIZE_MISMATCH")

    def test_short_stream_rejected(self):
        data = payload("short", 200)
        raw = single_member_tar("gvisor-bin/runsc-fd-parking", data,
                                truncate_to=512 + 100)
        self.fx.overwrite(self.fx.archive_path, raw, 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertEqual(ctx.exception.category, "ARCHIVE_MEMBER_SHORT_STREAM")

    def test_duplicate_member_rejected(self):
        members = [(n, MEMBER_PAYLOADS[n]) for n in TEST_MEMBER_SIZES]
        members.append(("gvisor-bin/runsc-fd-parking", MEMBER_PAYLOADS[
            "gvisor-bin/runsc-fd-parking"]))
        self.fx.overwrite(self.fx.archive_path, build_tar_bytes(members), 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertEqual(ctx.exception.category, "ARCHIVE_MEMBER_DUPLICATE")

    def test_traversal_member_rejected(self):
        members = [(n, MEMBER_PAYLOADS[n]) for n in TEST_MEMBER_SIZES]
        members.append(("../escape", b"x"))
        self.fx.overwrite(self.fx.archive_path, build_tar_bytes(members), 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertIn(ctx.exception.category,
                      ("ARCHIVE_MEMBER_UNSAFE", "ARCHIVE_MEMBER_UNEXPECTED"))

    def test_symlink_member_rejected(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:bz2") as tf:
            for n in TEST_MEMBER_SIZES:
                ti = tarfile.TarInfo(n)
                ti.size = len(MEMBER_PAYLOADS[n])
                ti.mode = 0o755
                tf.addfile(ti, io.BytesIO(MEMBER_PAYLOADS[n]))
            ti = tarfile.TarInfo("gvisor-bin/link")
            ti.type = tarfile.SYMTYPE
            ti.linkname = "/etc/passwd"
            tf.addfile(ti)
        self.fx.overwrite(self.fx.archive_path, buf.getvalue(), 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertEqual(ctx.exception.category, "ARCHIVE_MEMBER_TYPE_UNSAFE")

    def test_unexpected_extra_member_rejected(self):
        members = [(n, MEMBER_PAYLOADS[n]) for n in TEST_MEMBER_SIZES]
        members.append(("extra-tool", b"x" * 10))
        self.fx.overwrite(self.fx.archive_path, build_tar_bytes(members), 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertEqual(ctx.exception.category, "ARCHIVE_MEMBER_UNEXPECTED")

    def test_runsc_member_must_be_elf(self):
        notelf = b"MZ!" + payload("notelf", RUNSC_SIZE)[3:]
        members = [(n, MEMBER_PAYLOADS[n]) for n in TEST_MEMBER_SIZES]
        members[0] = ("runsc", notelf)
        self.fx.overwrite(self.fx.archive_path, build_tar_bytes(members), 0o644)
        with self.assertRaises(mod.InstallError) as ctx:
            self.engine._scan_archive(staging_dir=None)
        self.assertIn(ctx.exception.category,
                      ("ARCHIVE_RUNSC_NOT_ELF", "ARCHIVE_MEMBER_HASH_MISMATCH"))

    def test_script_sidecars_accepted_by_exact_bytes_into_stage(self):
        stage = self.fx.version_dir() + ".stage-x"
        os.makedirs(stage + "/" + mod.GVISOR_BIN_DIR)
        for name in SIDE_SIZES:
            self.assertNotEqual(MEMBER_PAYLOADS[name][:4], b"\x7fELF")
        facts = self.engine._scan_archive(staging_dir=stage)
        self.assertEqual(len(facts["members_installed"]), 6)
        for name in TEST_MEMBER_SIZES:
            with open(stage + "/" + name, "rb") as fh:
                self.assertEqual(fh.read(), MEMBER_PAYLOADS[name])


class NoEffectsAndPreconditionTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.close()

    def test_default_plan_is_no_effects_proposal(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = mod.main([])
        self.assertEqual(code, mod.EXIT_OK)
        plan = json.loads(buf.getvalue())
        self.assertEqual(plan["status"], "NO_EFFECTS_PROPOSAL")
        self.assertEqual(plan["limits"]["total_wall_seconds"], 180.0)
        self.assertIn("--oci-seccomp", plan["runtime_entry"]["runtimeArgs"])
        self.assertEqual(plan["archive"]["sha256"], mod.ARCHIVE_SHA256)
        self.assertEqual(plan["required_members"]["expanded_total_bytes"], 284471010)
        self.assertIn("open_action_time_gates", plan)
        self.assertEqual(self.fx.runner.calls, [])

    def test_execute_without_binding_and_sha_is_usage_error(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(mod.main(["--execute"]), mod.EXIT_USAGE)
            self.assertEqual(mod.main(["--execute", "--binding", "x"]),
                             mod.EXIT_USAGE)
            self.assertEqual(mod.main(["--plan", "extra"]), mod.EXIT_USAGE)

    def test_missing_binding_file_never_invokes_runner(self):
        code, receipt = self.fx.engine().execute(
            self.fx.layout.p("/nonexistent/binding.json"), "b" * 64)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("BINDING", receipt["status"])
        self.assertEqual(self.fx.runner.calls, [])

    def test_tampered_binding_sha_never_invokes_runner(self):
        code, receipt = self.fx.engine().execute(self.fx.binding_path, "c" * 64)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("BINDING_SHA_MISMATCH", receipt["status"])
        self.assertEqual(self.fx.runner.calls, [])
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)

    def test_placeholder_pin_fails_before_any_subprocess(self):
        self.fx.binding_dict["effect_commission_token"] = "TO_BE_BOUND"
        raw = json.dumps(self.fx.binding_dict, indent=2).encode("utf-8")
        path = os.path.join(self.fx.tmp, "ph.json")
        Fixture._write(path, raw, 0o600)
        code, receipt = self.fx.engine().execute(path,
                                                 hashlib.sha256(raw).hexdigest())
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("PIN_PLACEHOLDER", receipt["status"])
        self.assertEqual(self.fx.runner.calls, [])

    def test_non_linux_platform_gate_blocks_before_any_subprocess(self):
        code, receipt = self.fx.engine(
            platform_probe=lambda: ("Darwin", "x86_64")).execute(
            self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("PLATFORM_UNQUALIFIED", receipt["status"])
        self.assertEqual(self.fx.runner.calls, [])
        self.assertFalse(os.path.exists(self.fx.version_dir()))

    def test_production_layout_requires_root_euid_before_effects(self):
        prod = mod.Layout.production()
        engine = mod.InstallEngine(prod, self.fx.runner, contract=TEST_CONTRACT,
                                   euid=12345, platform_probe=lambda: ("Linux", "x86_64"),  # explicit synthetic nonroot
                                   chown_fn=lambda p, u, g: None)
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("NO_ROOT_EUID", receipt["status"])
        self.assertEqual(self.fx.runner.calls, [])

    def test_missing_scratch_fails_before_effects_and_creates_nothing(self):
        self.fx.write_binding(operation_scratch_dir=self.fx.tmp + "/absent-scratch")
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("SCRATCH_MISSING", receipt["status"])
        self.assertEqual(self.fx.runner.calls, [])
        self.assertFalse(os.path.exists(self.fx.tmp + "/absent-scratch"))
        self.assertFalse(os.path.exists(self.fx.version_dir()))

    def test_intent_write_failure_happens_before_any_effect(self):
        engine = self.fx.engine()
        original_writer = engine._write_receipt_file

        def failing_writer(path, obj):
            if path.endswith("intent.json"):
                raise OSError("simulated scratch failure")
            return original_writer(path, obj)
        engine._write_receipt_file = failing_writer
        script_preflight(self.fx.runner)  # must never be consumed
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_INTERNAL)
        self.assertIn("INTENT_WRITE_FAILED", receipt["status"])
        self.assertEqual(self.fx.runner.calls, [])
        self.assertFalse(os.path.exists(self.fx.version_dir()))
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)

    def test_preflight_gate_failures_stop_before_mutation(self):
        # scripted preflight order: 0=client version, 1=server version
        variants = [
            (0, b"29.0.2\n", "docker_client_29_1_3"),
            (1, b"29.0.2\n", "docker_server_29_1_3"),
        ]
        for index, bad, gate_key in variants:
            with self.subTest(gate=gate_key):
                fx = Fixture()
                try:
                    r = fx.runner
                    script_preflight(r)
                    r.responses[index] = {"err": b"", "out": bad}
                    code, receipt = fx.engine().execute(fx.binding_path,
                                                        fx.binding_sha)
                    self.assertEqual(code, mod.EXIT_BLOCKED)
                    self.assertIn("BLOCKED_PRE_EFFECT_GATE_" + gate_key,
                                  receipt["status"])
                    self.assertEqual(reloads_of(r), [])
                    self.assertFalse(os.path.exists(fx.version_dir()))
                    self.assertEqual(fx.config_now(), CONFIG_BYTES)
                finally:
                    fx.close()

    def test_nonzero_container_census_is_a_collision_gate(self):
        script_preflight(self.fx.runner, total=b"1\n")
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("containers_zero", receipt["status"])
        self.assertFalse(os.path.exists(self.fx.version_dir()))

    def test_exec_reload_without_hup_is_not_qualified(self):
        script_preflight(self.fx.runner, show=SHOW_NO_HUP)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("exec_reload_hup", receipt["status"])
        self.assertEqual(reloads_of(self.fx.runner), [])
        self.assertFalse(os.path.exists(self.fx.version_dir()))

    def test_archive_pin_mismatch_blocks_before_any_mutation(self):
        self.fx.overwrite(self.fx.archive_path, GOOD_ARCHIVE_BYTES + b"x", 0o644)
        script_preflight(self.fx.runner)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("ARCHIVE_SIZE_MISMATCH", receipt["status"])
        self.assertFalse(os.path.exists(self.fx.version_dir()))
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)

    def test_archive_hash_pin_mismatch_blocks(self):
        other = bytearray(GOOD_ARCHIVE_BYTES)
        other[-1] ^= 0xFF
        self.fx.overwrite(self.fx.archive_path, bytes(other), 0o644)
        script_preflight(self.fx.runner)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("ARCHIVE_PIN_MISMATCH", receipt["status"])
        self.assertFalse(os.path.exists(self.fx.version_dir()))

    def test_disk_insufficient_blocks_before_backup_or_bundle(self):
        script_preflight(self.fx.runner)
        code, receipt = self.fx.engine(disk_free_fn=lambda p: 1024).execute(
            self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("DISK_INSUFFICIENT", receipt["status"])
        self.assertFalse(os.path.exists(self.fx.version_dir()))
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)
        self.assertFalse(reloads_of(self.fx.runner))


class EffectFlowTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.close()

    def test_full_happy_path_delayed_registration_single_reload(self):
        script_happy(self.fx.runner, polls_before_rf=2)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_OK)
        self.assertEqual(receipt["status"], "OK_INSTALLED")
        cfg = json.loads(self.fx.config_now().decode("utf-8"))
        self.assertEqual(cfg["runtimes"]["rf-runsc"], entry())
        self.assertEqual(cfg["runtimes"]["nvidia"],
                         {"path": "nvidia-container-runtime", "runtimeArgs": []})
        self.assertEqual(cfg["default-runtime"], "runc")
        self.assertTrue(cfg["live-restore"])
        self.assertEqual(cfg["data-root"], "/var/lib/docker")
        # exact bundle: six files, exact bytes, 0755, chown root requested
        d = self.fx.version_dir()
        self.assertEqual(sorted(os.listdir(d)), ["gvisor-bin", "runsc"])
        for name, data in MEMBER_PAYLOADS.items():
            p = d + "/" + name
            with open(p, "rb") as fh:
                self.assertEqual(fh.read(), data)
            self.assertEqual(os.stat(p).st_mode & 0o777, 0o755)
        self.assertFalse(os.path.exists(d + "/containerd-shim-runsc-v1"))
        self.assertTrue(self.fx.chown_calls)
        backup = self.fx.scratch + "/daemon.json.preimage"
        self.assertEqual(os.stat(backup).st_mode & 0o777, 0o600)
        with open(backup, "rb") as fh:
            self.assertEqual(fh.read(), CONFIG_BYTES)
        self.assertEqual(len(reloads_of(self.fx.runner)), 1)  # ONE reload
        self.assertTrue(all("-n" in c["argv"] for c in reloads_of(self.fx.runner)))
        self.assertFalse(any("restart" in c["argv"] or "kill" in c["argv"]
                             for c in self.fx.runner.calls))
        self.assertTrue(receipt["config"]["committed"])
        self.assertFalse(receipt["config"]["commit_uncertain"])
        self.assertTrue(receipt["config"]["additive_diff_asserted"])
        self.assertEqual(receipt["backup"]["sha256"],
                         hashlib.sha256(CONFIG_BYTES).hexdigest())
        self.assertFalse(receipt["backup"]["body_exported"])
        self.assertEqual(receipt["settlement"]["outcome"], "VERIFIED")
        self.assertGreaterEqual(receipt["settlement"]["polls"], 3)
        self.assertTrue(receipt["bundle"]["created"])
        self.assertFalse(receipt["bundle"]["reused"])
        self.assertFalse(receipt["bundle"]["shim_installed"])
        self.assertTrue(receipt["service"]["exec_reload_uses_hup"])
        self.assertTrue(all(c["argv"][:3] == [mod.DOCKER_BIN, "--host",
                                              mod.DOCKER_SOCKET_ARG]
                            for c in self.fx.runner.calls
                            if c["binary"] == mod.DOCKER_BIN))

    def test_exact_existing_alias_and_bundle_reused_with_no_write_no_reload(self):
        cfg = json.loads(CONFIG_BYTES.decode("utf-8"))
        cfg["runtimes"]["rf-runsc"] = entry()
        self.fx.overwrite(self.fx.layout.daemon_json,
                          (json.dumps(cfg, indent=2) + "\n").encode("utf-8"), 0o644)
        self.fx.write_exact_bundle()
        r = self.fx.runner
        script_preflight(r, rf_in_info=True)
        script_poll(r, rf=True)
        cfg_before = self.fx.config_now()
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_OK)
        self.assertEqual(receipt["status"], "OK_REUSE_EXISTING")
        self.assertEqual(self.fx.config_now(), cfg_before)
        self.assertEqual(reloads_of(self.fx.runner), [])
        self.assertTrue(receipt["bundle"]["reused"])
        self.assertFalse(receipt["bundle"]["created"])

    def test_conflicting_alias_stops_without_writes(self):
        cfg = json.loads(CONFIG_BYTES.decode("utf-8"))
        cfg["runtimes"]["rf-runsc"] = {"path": "/elsewhere/runsc",
                                       "runtimeArgs": []}
        self.fx.overwrite(self.fx.layout.daemon_json,
                          (json.dumps(cfg, indent=2) + "\n").encode("utf-8"), 0o644)
        script_preflight(self.fx.runner, rf_in_info=True)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("ALIAS_CONFLICT", receipt["status"])
        self.assertFalse(os.path.exists(self.fx.version_dir()))

    def test_publish_collision_preserves_prior_empty_directory(self):
        os.makedirs(self.fx.version_dir())  # empty prior directory: never replaced
        script_happy(self.fx.runner)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("BUNDLE_COLLISION_PRESERVED", receipt["status"])
        self.assertEqual(os.listdir(self.fx.version_dir()), [])
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)
        self.assertFalse(reloads_of(self.fx.runner))

    def test_extra_destination_file_is_collision_never_adopted(self):
        d = self.fx.write_exact_bundle()
        self.fx._write(d + "/gvisor-bin/extra-file", b"extraneous", 0o755)
        script_happy(self.fx.runner)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("BUNDLE_COLLISION_PRESERVED", receipt["status"])
        self.assertTrue(os.path.exists(d + "/gvisor-bin/extra-file"))
        with open(d + "/gvisor-bin/extra-file", "rb") as fh:
            self.assertEqual(fh.read(), b"extraneous")
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)

    def test_publish_failure_retains_stage_and_no_partial_visible_version(self):
        def failing_rename(stage, dest):
            raise OSError(errno.EIO, "injected publish failure")
        script_happy(self.fx.runner)
        code, receipt = self.fx.engine(rename_fn=failing_rename).execute(
            self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("PUBLISH_FAILED", receipt["status"])
        self.assertFalse(os.path.exists(self.fx.version_dir()))
        parent = os.path.dirname(self.fx.version_dir())
        stages = [n for n in os.listdir(parent) if n.startswith(".stage-")]
        self.assertEqual(len(stages), 1)  # truthful retained stage
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)

    def test_renameat2_unavailable_fails_closed_with_no_plain_rename(self):
        def enosys_rename(stage, dest):
            raise OSError(errno.ENOSYS, "renameat2 unavailable")
        script_happy(self.fx.runner)
        code, receipt = self.fx.engine(rename_fn=enosys_rename).execute(
            self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("PUBLISH_PRIMITIVE_UNAVAILABLE", receipt["status"])
        self.assertFalse(os.path.exists(self.fx.version_dir()))
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)

    def test_real_renameat2_publishes_complete_directory_atomically(self):
        import sys
        if sys.platform != "linux":
            self.skipTest("actual Linux renameat2 unavailable; no substitute acceptance")
        # real filesystem semantics on a supported platform: the staged tree
        # becomes visible only through the single NOREPLACE rename
        script_happy(self.fx.runner, polls_before_rf=0)
        code, receipt = self.fx.engine(rename_fn=mod.rename_noreplace).execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_OK)
        self.assertEqual(receipt["status"], "OK_INSTALLED")
        d = self.fx.version_dir()
        self.assertEqual(sorted(os.listdir(d)), ["gvisor-bin", "runsc"])
        engine = self.fx.engine(rename_fn=mod.rename_noreplace)
        engine.binding = mod.Binding(dict(self.fx.binding_dict), TEST_CONTRACT)
        self.assertTrue(engine._verify_bundle_dir(d))

    def test_complete_exact_bundle_reused_when_destination_appears(self):
        self.fx.write_exact_bundle()
        script_happy(self.fx.runner)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_OK)
        self.assertEqual(receipt["status"], "OK_INSTALLED")
        self.assertTrue(receipt["bundle"]["reused"])
        self.assertFalse(receipt["bundle"]["created"])


class CommitAndRollbackTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.close()

    def _script_commit_failure_service_failed_then_rollback(self):
        script_preflight(self.fx.runner)
        r = self.fx.runner
        r.script(rc=0, out=b"", err=b"")                 # dockerd --validate
        r.script(rc=0, out=b"", err=b"")                 # install reload
        script_poll(r, rf=False, show=SHOW_FAILED)       # settled proven failure
        r.script(rc=0, out=b"", err=b"")                 # rollback reload
        script_poll(r, rf=False)                         # rollback settles
        r.script(out=b"0\n")                             # census total
        r.script(out=b"0\n")                             # census running

    def test_proven_service_failure_rolls_back_and_removes_new_bundle(self):
        self._script_commit_failure_service_failed_then_rollback()
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_OK)
        self.assertEqual(receipt["status"], "OK_ROLLED_BACK")
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)
        self.assertEqual(hashlib.sha256(self.fx.config_now()).hexdigest(),
                         hashlib.sha256(CONFIG_BYTES).hexdigest())
        self.assertFalse(os.path.exists(self.fx.version_dir()))
        with open(self.fx.scratch + "/daemon.json.preimage", "rb") as fh:
            self.assertEqual(fh.read(), CONFIG_BYTES)
        self.assertEqual(len(reloads_of(self.fx.runner)), 2)
        self.assertTrue(receipt["rollback"].get("new_bundle_removed"))
        self.assertEqual(receipt["rollback"]["restored_sha256"],
                         hashlib.sha256(CONFIG_BYTES).hexdigest())

    def test_reused_bundle_is_preserved_through_rollback(self):
        self.fx.write_exact_bundle()
        self._script_commit_failure_service_failed_then_rollback()
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_OK)
        self.assertEqual(receipt["status"], "OK_ROLLED_BACK")
        self.assertTrue(receipt["bundle"]["reused"])
        self.assertTrue(os.path.exists(self.fx.version_dir()))
        engine = self.fx.engine()
        engine.binding = mod.Binding(dict(self.fx.binding_dict), TEST_CONTRACT)
        self.assertTrue(engine._verify_bundle_dir(self.fx.version_dir()))
        self.assertNotIn("new_bundle_removed", receipt["rollback"])

    def test_intervening_writer_after_commit_denies_rollback(self):
        engine = self.fx.engine()
        r = self.fx.runner
        script_preflight(r)
        r.script(rc=0, out=b"", err=b"")
        r.script(rc=0, out=b"", err=b"")
        script_poll(r, rf=False, show=SHOW_FAILED)
        real_commit = engine._commit

        def commit_then_intervene(cand_bytes, cand_sha):
            real_commit(cand_bytes, cand_sha)
            self.fx.overwrite(self.fx.layout.daemon_json,
                              b'{"debug": true}\n', 0o644)
        engine._commit = commit_then_intervene
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        self.assertIn("STOP_ROLLBACK_DENIED_INTERVENING_WRITER", receipt["status"])
        self.assertEqual(self.fx.config_now(), b'{"debug": true}\n')
        with open(self.fx.scratch + "/daemon.json.preimage", "rb") as fh:
            self.assertEqual(fh.read(), CONFIG_BYTES)
        self.assertEqual(len(reloads_of(r)), 1)  # rollback reload never issued
        self.assertTrue(os.path.exists(self.fx.version_dir()))

    def test_backup_tampering_denies_rollback(self):
        engine = self.fx.engine()
        r = self.fx.runner
        script_preflight(r)
        r.script(rc=0, out=b"", err=b"")
        r.script(rc=0, out=b"", err=b"")
        script_poll(r, rf=False, show=SHOW_FAILED)
        original_write_backup = engine._write_backup

        def tamper_backup():
            original_write_backup()
            self.fx.overwrite(engine.backup_path, b'{"tampered": true}\n', 0o600)
        engine._write_backup = tamper_backup
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        self.assertIn("ROLLBACK_DENIED_BACKUP_INVALID", receipt["status"])
        self.assertEqual(len(reloads_of(r)), 1)
        self.assertTrue(os.path.exists(self.fx.version_dir()))

    def test_preimage_change_before_commit_blocks_never_commits(self):
        engine = self.fx.engine()
        r = self.fx.runner
        script_preflight(r)
        original_write_backup = engine._write_backup

        def intervene_before_commit():
            original_write_backup()
            self.fx.overwrite(self.fx.layout.daemon_json,
                              b'{"debug": true}\n', 0o644)
        engine._write_backup = intervene_before_commit
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_BLOCKED)
        self.assertIn("CONTROL_GAP_PREIMAGE_CHANGED", receipt["status"])
        self.assertFalse(receipt["config"]["committed"])
        self.assertEqual(self.fx.config_now(), b'{"debug": true}\n')
        self.assertEqual(reloads_of(r), [])

    def test_deadline_without_confirmation_is_unknown_and_freezes(self):
        r = self.fx.runner
        script_preflight(r)
        r.script(rc=0, out=b"", err=b"")                 # validate
        r.script(rc=0, out=b"", err=b"")                 # reload
        script_poll(r, rf=False)                         # readable, not yet
        script_poll(r, rf=False)                         # still not registered
        engine = self.fx.engine(settlement_window_seconds=1.0,
                                settlement_interval_seconds=1.0)
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        self.assertEqual(receipt["status"], "UNKNOWN_RELOAD_SETTLEMENT")
        self.assertEqual(receipt["settlement"]["outcome"], "DEADLINE_UNCONFIRMED")
        self.assertTrue(self.fx.runner.frozen)
        self.assertEqual(len(reloads_of(r)), 1)          # never retried
        self.assertEqual(len(reloads_of(r, "rollback")), 0)  # rollback frozen too
        self.assertTrue(receipt["config"]["committed"])
        self.assertTrue(os.path.exists(self.fx.version_dir()))  # preserved

    def test_rc0_reload_with_control_error_stderr_refuses_and_freezes(self):
        r = self.fx.runner
        script_preflight(r)
        r.script(rc=0, out=b"", err=b"")                 # validate
        r.script(rc=0, out=b"ignored\n",
                 err=b"permission denied while trying to connect\n")  # reload
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        self.assertIn("REFUSED_AT_RELOAD", receipt["status"])
        self.assertTrue(self.fx.runner.frozen)
        self.assertEqual(len(reloads_of(r)), 1)
        self.assertTrue(receipt["config"]["committed"])  # truthful partial state

    def test_permission_error_freezes_all_later_actions(self):
        engine = self.fx.engine()
        r = self.fx.runner
        script_preflight(r)

        def denying_chown(path, uid, gid):
            if path.endswith("daemon.json.preimage"):
                raise PermissionError(errno.EACCES, "injected denial")
        engine.chown_fn = denying_chown
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        self.assertIn("REFUSED_PERMISSION_DENIED", receipt["status"])
        self.assertTrue(self.fx.runner.frozen)
        self.assertEqual(reloads_of(r), [])
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)
        with self.assertRaises(mod.EffectFrozen):
            r.run([mod.SUDO_BIN, "-n", mod.SYSTEMCTL_BIN, "reload",
                   mod.DOCKER_SERVICE_UNIT])

    def test_mutation_timeout_is_uncertain_and_never_retried(self):
        r = self.fx.runner
        script_preflight(r)
        r.script(rc=0, out=b"", err=b"")                 # validate
        r.script(timed_out=True, rc=None)                # reload times out
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        self.assertIn("UNKNOWN_AT_RELOAD_TIMEOUT", receipt["status"])
        self.assertEqual(len(reloads_of(r)), 1)
        self.assertFalse(any("restart" in c["argv"] or "kill" in c["argv"]
                             for c in r.calls))

    def test_budget_exhaustion_stops_before_effects(self):
        ticks = itertools.count(start=1000.0, step=1000.0)
        engine = self.fx.engine(
            budget=mod.Budget(total_seconds=10.0, rollback_reserve_seconds=6.0,
                              monotonic=lambda: next(ticks)))
        script_preflight(self.fx.runner)
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        self.assertIn("BUDGET_EXCEEDED", receipt["status"])
        self.assertEqual(self.fx.runner.calls, [])
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)
        self.assertFalse(os.path.exists(self.fx.version_dir()))


class ReceiptAndBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.close()

    def test_phase_receipt_write_failure_prevents_later_phase(self):
        engine = self.fx.engine()
        r = self.fx.runner
        script_preflight(r)
        r.script(rc=0, out=b"", err=b"")                 # validate: never reached
        r.script(rc=0, out=b"", err=b"")                 # reload: never reached
        original_writer = engine._write_receipt_file

        def failing_writer(path, obj):
            if os.path.basename(path).startswith("phase_"):
                raise OSError("simulated scratch disk failure")
            return original_writer(path, obj)
        engine._write_receipt_file = failing_writer
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertNotEqual(code, mod.EXIT_OK)
        # the phase receipt for the first phase fails before any preflight
        # read: later phases (reads, validate, reload, commit) never happen
        self.assertEqual(len(r.calls), 0)
        self.assertFalse(reloads_of(r))
        self.assertTrue(os.path.exists(self.fx.scratch + "/intent.json"))
        self.assertFalse(any(n.startswith("phase_")
                             for n in os.listdir(self.fx.scratch)))
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)
        self.assertFalse(receipt["config"]["committed"])

    def test_final_receipt_write_failure_cannot_keep_success(self):
        engine = self.fx.engine()
        script_happy(self.fx.runner, polls_before_rf=0)
        original_writer = engine._write_receipt_file

        def flaky_writer(path, obj):
            if "final_" in os.path.basename(path):
                raise OSError("simulated disk failure")
            return original_writer(path, obj)
        engine._write_receipt_file = flaky_writer
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        self.assertEqual(receipt["status"], "UNCERTAIN_RECEIPT_WRITE_FAILED")
        self.assertEqual(receipt["pre_downgrade_status"], "OK_INSTALLED")
        self.assertTrue(receipt["receipt_write_failed"])
        self.assertTrue(receipt["config"]["committed"])
        op_files = os.listdir(self.fx.scratch)
        self.assertTrue(any(n.startswith("phase_") for n in op_files))
        self.assertFalse(any(n.startswith("final_") for n in op_files))

    def test_base_exception_is_recorded_truthfully_without_replay(self):
        engine = self.fx.engine()
        r = self.fx.runner
        script_preflight(r)

        def interrupting_commit(cand_bytes, cand_sha):
            raise KeyboardInterrupt()
        engine._commit = interrupting_commit
        code, receipt = engine.execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_INTERNAL)
        self.assertIn("INTERRUPTED", receipt["status"])
        self.assertEqual(self.fx.config_now(), CONFIG_BYTES)
        self.assertEqual(reloads_of(r), [])
        self.assertFalse(receipt["config"]["committed"])

    def test_no_private_config_values_or_token_in_artifacts(self):
        script_happy(self.fx.runner, polls_before_rf=0)
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_OK)
        backup = self.fx.scratch + "/daemon.json.preimage"
        self.assertEqual(os.stat(backup).st_mode & 0o777, 0o600)
        blobs = []
        for root, _dirs, files in os.walk(self.fx.scratch):
            for name in files:
                path = os.path.join(root, name)
                if path == backup:
                    continue  # the private backup is the sanctioned byte store
                with open(path, "rb") as fh:
                    blobs.append((path, fh.read()))
        blobs.append(("<returned-receipt>", json.dumps(receipt).encode("utf-8")))
        for path, data in blobs:
            self.assertNotIn(SENTINEL_TOKEN.encode(), data, path)
            self.assertNotIn(SENTINEL_URL.encode(), data, path)
            self.assertNotIn(b"ROOT-EFFECT-COMMISSION-0001", data, path)
        self.assertNotIn(CONFIG_BYTES, json.dumps(receipt).encode())
        self.assertNotIn(SENTINEL_TOKEN, json.dumps(receipt))
        self.assertNotIn(SENTINEL_URL, json.dumps(receipt))

    def test_error_receipts_never_contain_private_values(self):
        r = self.fx.runner
        script_preflight(r)
        r.script(rc=0, out=b"", err=b"")
        r.script(rc=126)                                 # reload refused
        code, receipt = self.fx.engine().execute(self.fx.binding_path,
                                                 self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_UNCERTAIN)
        blob = json.dumps(receipt)
        self.assertNotIn(SENTINEL_TOKEN, blob)
        self.assertNotIn(SENTINEL_URL, blob)
        self.assertNotIn("ROOT-EFFECT-COMMISSION-0001", blob)

    def test_no_sudo_probing_no_restart_and_pinned_socket_everywhere(self):
        script_happy(self.fx.runner, polls_before_rf=0)
        code, _ = self.fx.engine().execute(self.fx.binding_path, self.fx.binding_sha)
        self.assertEqual(code, mod.EXIT_OK)
        for call in self.fx.runner.calls:
            self.assertNotIn("-l", call["argv"])
            self.assertNotIn("restart", call["argv"])
            self.assertNotIn("kill", call["argv"])
            if call["binary"] == mod.DOCKER_BIN:
                self.assertEqual(call["argv"][:3],
                                 [mod.DOCKER_BIN, "--host", mod.DOCKER_SOCKET_ARG])
            if call["binary"] == mod.SUDO_BIN:
                self.assertEqual(call["argv"][1], "-n")


class BoundedRunnerTests(unittest.TestCase):
    """Real bounded-collection tests with harmless injected binaries only."""

    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.close()

    def test_streaming_collect_and_exact_output_cap(self):
        big = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
        try:
            big.write(os.urandom(100_000))
            big.close()
            runner = mod.BoundedRunner(mod.Budget(combined_output_bytes=200_000),
                                       binaries=frozenset({"/bin/cat"}))
            res = runner.run(["/bin/cat", big.name])
            self.assertFalse(res["truncated"])
            self.assertEqual(res["rc"], 0)
            self.assertEqual(len(res["out"]), 100_000)
            capped = mod.BoundedRunner(mod.Budget(combined_output_bytes=1024, rollback_reserve_output_bytes=0),
                                       binaries=frozenset({"/bin/cat"}))
            small = capped.run(["/bin/cat", big.name])
            self.assertTrue(small["truncated"])
            self.assertEqual(len(small["out"]), 1024)
            self.assertTrue(capped.calls[0]["truncated"])
        finally:
            os.unlink(big.name)

    def test_per_command_timeout_kills_child_and_classifies_unknown(self):
        runner = mod.BoundedRunner(mod.Budget(), binaries=frozenset({"/bin/sleep"}),
                                   per_command_timeout=0.4)
        with self.assertRaises(mod.InstallError) as ctx:
            runner.run(["/bin/sleep", "5"])
        self.assertEqual(ctx.exception.category, "COMMAND_TIMEOUT_UNKNOWN")
        self.assertTrue(runner.calls[0]["timed_out"])

    def test_refusal_raises_and_freezes_runner(self):
        runner = mod.BoundedRunner(mod.Budget(), binaries=frozenset({"/usr/bin/false"}))
        with self.assertRaises(mod.InstallError):
            runner.run(["/usr/bin/false"])
        self.assertTrue(runner.frozen)
        with self.assertRaises(mod.EffectFrozen):
            runner.run(["/usr/bin/false"])

    def test_non_allowlisted_binary_rejected_without_spawn(self):
        runner = mod.BoundedRunner(mod.Budget(), binaries=frozenset({"/bin/cat"}))
        with self.assertRaises(mod.InstallError) as ctx:
            runner.run(["/bin/rm", "-rf", "/"])
        self.assertEqual(ctx.exception.category, "COMMAND_NOT_ALLOWLISTED")

    def test_env_leak_guard(self):
        runner = mod.BoundedRunner(mod.Budget(), binaries=frozenset({"/bin/cat"}),
                                   env={"PATH": "/usr/bin", "DOCKER_HOST": "tcp://x"})
        with self.assertRaises(mod.InstallError) as ctx:
            runner.run(["/bin/cat", "/etc/hostname"])
        self.assertEqual(ctx.exception.category, "AMBIENT_ENV_LEAK")


class RenameNoreplaceTests(unittest.TestCase):
    def test_real_renameat2_noreplace_semantics(self):
        tmp = tempfile.mkdtemp(prefix="rf-rn2-")
        try:
            src = tmp + "/stage"
            dst = tmp + "/published"
            os.mkdir(src)
            with open(src + "/f", "wb") as fh:
                fh.write(b"x")
            mod.rename_noreplace(src, dst)
            self.assertTrue(os.path.isdir(dst))
            self.assertFalse(os.path.exists(src))
            src2 = tmp + "/stage2"
            os.mkdir(src2)
            with self.assertRaises(FileExistsError):
                mod.rename_noreplace(src2, dst)
            self.assertEqual(os.listdir(src2), [])  # prior preserved, no replace
        except OSError as exc:
            if exc.errno == errno.ENOSYS:
                self.skipTest("renameat2 unsupported on this platform")
            raise
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
