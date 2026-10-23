"""Hermetic local tests plus inert contract metadata for the seven Research
Factory workload sources. SOURCE ONLY: no workload main() is executed and no
real fork/sleep/socket/listen/large allocation/output flood occurs;
module-local OS/socket/time/allocator/write/fork boundaries are replaced with
controlled test doubles.

Exact command run (from this directory):
  python3 -m unittest -v test_workloads

Original worker claimed 44 tests; independent parent review found defects.
This derived suite tests bounded source repairs with effect guards.
Current independent results and exact sizes/hashes live in parent receipts.
Test limitation: doubles prove control flow, bounds, independent counting and
typed outcomes only; they never exercise real kernel limits, so no guest or
host PASS/containment fact is asserted anywhere. Host oracles (64KiB output
truncation, OOM/memory.current/peak/events, cgroups, CID, exit witness,
cleanup, tmpfs options, host listener bind at 39173, fixture witness) remain
parent-side. Scripts were compiled and inertly imported, never executed.

No CLI/env knobs exist in any artifact; CONTRACTS below is an inert literal
binding constants, schemas, planned profile, wrapper assumptions, pinned
intended hashes and unresolved host witness preconditions.
"""

import builtins
import errno as ER
import importlib
import inspect
import io
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "research_codegen_qualification")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

SCRIPTS = ("w01_boundary.py", "w02_cpu_deadline.py", "w03_output_cap.py",
           "w04_memory_limit.py", "w05_process_limit.py",
           "w06_scratch_limit.py", "w07_fresh_recovery.py")

CONTRACTS = {
    "_profile": {
        "uid_gid": 65534, "env_names": ["LANG", "PATH"],
        "root_fs": "read-only", "caps": "dropped",
        "no_new_privileges": True, "health_restart_log_sink_ports": False,
        "ipc": "private", "cgroupns": "private",
        "host_binds_devices_groups_sockets": "none",
        "tmp_tmpfs": "8MiB,noexec,nosuid,mode=1777", "cpu_limit": "0.5",
        "memory_limit": "256MiB",
        "memory_swap": "256MiB_equal_means_no_extra_swap",
        "host_pids_limit": 128, "retained_output": "64KiB",
        "workload_seconds": 5, "whole_attempt_seconds": 120,
        "serial_seconds_original_root_max": 840,
        "binding": "planned_profile_only; host must prove fitting/mapping "
                   "before stress; never silently enlarged",
    },
    "_wrapper": {
        "docker_binary": "exact docker absolute binary",
        "daemon": "explicit Unix daemon socket",
        "runtime": "rf-runsc",
        "runtime_args_ordered": ["--platform=systrap", "--network=none",
                                 "--oci-seccomp"],
        "bundle": "complete six-file release20261005.0",
        "image_semantics": "pinned manifest/config, backendImage.Id",
        "owner": "root owns install, selected-runtime smoke, host "
                 "observations, future effects; scripts claim none of them",
    },
    "_bindings": {
        "image_manifest_sha256":
            "bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed",
        "image_config_sha256":
            "607dc744833974b365cc338d565e01bb76eaebe25993fe328ce185170bcd8f05",
        "docker_version_audited": "29.1.3",
        "note": "containerd Image.Id=manifest at earlier audited host; fresh "
                "host behavior must be audited; digests not interchangeable",
        "bundle_archive_sha256":
            "bd4eb2ca0ee74f0fbbb5f5273ba011e79c56a29fbb047393b88b981cd3230ede",
        "runsc_sha256":
            "210b437a9cfae51e8f8c9074ed19b8b5e59477178e2e391a18117d8d6b924f7a",
        "other_bundle_members": "installed exact manifest pending",
        "accepted_strict_absence_transport_sha256":
            "b6d36717ad3630d127b16fe9e117d9401bea1136880e28d19f0d18061933c633",
        "status": "intended bindings only; not selection or install claims",
    },
    "_transport": {
        "listener": "host 127.0.0.1:39173 TCP/UDP/DNS-surrogate",
        "port_is": "trusted fixed campaign constant; host bind/exclusivity "
                   "proven by root preflight before any use",
        "udp_send": "SENT_UNCONFIRMED only; parent receipt authoritative",
        "loopback_denial_scope": "host-loopback exclusion only",
        "excluded_fixtures": "not provisioned by scripts; absent witness "
                             "=> parent UNPROVEN",
        "record_schema": "rf.workload.obs.v1",
        "mandatory_flags": {"candidate_admission": False,
                            "containment_qualified": False},
        "quarantine": "original unknown contracts operation quarantined; "
                      "no replay",
    },
    "w01_boundary.py": {
        "case_id": "w01",
        "constants": {"uid_gid_expected": 65534, "port": 39173,
                      "scratch_path": "/tmp/rf-w01-scratch.txt",
                      "scratch_max_bytes": 32,
                      "forbidden_write": "/rf-forbidden-write",
                      "status_read_cap": 8193, "socket_timeout_s": 0.25,
                      "net_total_budget_s": 2.0,
                      "excluded_paths": [
                          "/rf-excluded/evaluator-labels.json",
                          "/rf-excluded/publisher-credential.fixture",
                          "/rf-excluded/evaluator-source.py",
                          "/rf-excluded/trial-vault.fixture",
                          "/rf-excluded/adjacent-fold.fixture",
                          "/rf-excluded/host-socket.fixture"],
                      "named_sockets": ["/var/run/docker.sock",
                                        "/var/run/sshd.sock",
                                        "/tmp/rf-mcp-gateway.sock"]},
        "records": "header, identity including 6*7=42, env_names, scratch, ro_root, status, "
                   "sockets, excluded, loopback, final",
        "expected_host_oracles": [
            "exclusive host bind at 39173 before use",
            "read-only root denial actually enforced",
            "64KiB collector truncation",
            "socket namespace absence",
            "fixture presence witness (else UNPROVEN)"],
        "unresolved_preconditions": [
            "host listener at 39173 not yet proven by root preflight",
            "no excluded-fixture host witness on this host"],
    },
    "w02_cpu_deadline.py": {
        "case_id": "w02",
        "constants": {"max_iters": 100000000, "guest_deadline_s": 8.0,
                      "child_sleep_s": 8.0,
                      "marker": "/tmp/rf-cpu-child.marker",
                      "marker_max_bytes": 16, "forks": 1},
        "records": "header, child_fork, cpu_work, final",
        "expected_host_oracles": ["outer 5s timeout firing before guest 8s",
                                  "same-cgroup child termination",
                                  "surviving-child check"],
        "unresolved_preconditions": ["outer timeout/cleanup witnessed by host",
                                     "no surviving-child proof from guest"],
    },
    "w03_output_cap.py": {
        "case_id": "w03",
        "constants": {"total_bytes": 1048576, "chunk_bytes": 4096,
                      "guest_deadline_s": 5.0, "max_stalls": 64,
                      "alternation": "stdout/stderr per chunk",
                      "header_final_inside_cap": True,
                      "final_reserved_bytes": 1024},
        "records": "header, final",
        "expected_host_oracles": ["64KiB truncation typed as outer failure",
                                  "collector cleanup"],
        "unresolved_preconditions": ["host collector truncation witness"],
    },
    "w04_memory_limit.py": {
        "case_id": "w04",
        "constants": {"max_bytes": 402653184, "chunk_bytes": 262144,
                      "page_bytes": 4096, "guest_deadline_s": 5.0,
                      "retain_until_boundary": True,
                      "no_swap_or_oom_control_change": True},
        "records": "header, memory_growth, final",
        "expected_host_oracles": ["cgroup memory.current/peak/events incl "
                                  "shmem/file/Sentry/Gofer",
                                  "enforced 256MiB mapping",
                                  "OOM/exit witness"],
        "unresolved_preconditions": ["256MiB cgroup limit mapping proof",
                                     "cause qualification is host-side"],
    },
    "w05_process_limit.py": {
        "case_id": "w05",
        "constants": {"max_attempts": 160, "parent_deadline_s": 5.0,
                      "child_sleep_s": 2.0, "child_descendants": 0,
                      "no_explicit_rlimit_invented": True,
                      "reap_scope": "own recorded pids only"},
        "records": "header, fork_attempts, final",
        "expected_host_oracles": ["host pids limit 128 vs guest task count",
                                  "descendant cleanup witness"],
        "unresolved_preconditions": ["intended guest task limit unproven if "
                                     "all 160 attempts succeed (UNPROVEN)"],
    },
    "w06_scratch_limit.py": {
        "case_id": "w06",
        "constants": {"max_bytes": 12582912, "chunk_bytes": 65536,
                      "guest_deadline_s": 5.0, "child_sleep_s": 2.0,
                      "scratch": "/tmp/rf-scratch-limit.bin",
                      "child_marker": "/tmp/rf-normal-child.marker",
                      "forbidden_write": "/rf-forbidden-write",
                      "expected_denial": "errno_ENOSPC",
                      "cleanup_scope": "two owned paths only"},
        "records": "header, readonly_root, child_fork, scratch, final",
        "expected_host_oracles": ["actual tmpfs/options/size",
                                  "memory limit mapping",
                                  "descendant cleanup even if parent rc=0"],
        "unresolved_preconditions": ["tmpfs 8MiB noexec,nosuid,mode=1777 "
                                     "mapping proof by host"],
    },
    "w07_fresh_recovery.py": {
        "case_id": "w07",
        "constants": {"known_answer": 42, "wait_s": 8.0,
                      "prior_markers": ["/tmp/rf-cpu-child.marker",
                                        "/tmp/rf-normal-child.marker",
                                        "/tmp/rf-scratch-limit.bin"],
                      "absence_is": "supporting freshness only",
                      "cancellation": "outer cancellation stays typed "
                                      "failure; script never interrupts "
                                      "controller or manages containers"},
        "records": "header, known_answer, freshness_markers, identity_env, "
                   "final",
        "expected_host_oracles": ["durable known CID before interruption",
                                  "controlled interruption and cleanup"],
        "unresolved_preconditions": ["late-child absence unprovable from "
                                     "guest"],
    },
}

EXPECTED_BINDINGS = {
    "image_manifest_sha256":
        "bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed",
    "image_config_sha256":
        "607dc744833974b365cc338d565e01bb76eaebe25993fe328ce185170bcd8f05",
    "bundle_archive_sha256":
        "bd4eb2ca0ee74f0fbbb5f5273ba011e79c56a29fbb047393b88b981cd3230ede",
    "runsc_sha256":
        "210b437a9cfae51e8f8c9074ed19b8b5e59477178e2e391a18117d8d6b924f7a",
    "accepted_strict_absence_transport_sha256":
        "b6d36717ad3630d127b16fe9e117d9401bea1136880e28d19f0d18061933c633",
}

FORBIDDEN_SUBSTRINGS = ("eval(", "exec(", "pickle", "__import__", "popen(",
                        "system(", "environ.get", "getenv(")

EFFECT_APIS = ("os.open", "os.fork", "os.system", "os._exit", "time.sleep",
               "socket.socket", "builtins.open")


def raiser(name):
    def f(*a, **k):
        raise AssertionError("effect API used during import: " + name)
    return f


def load(mod):
    return importlib.import_module(mod)


def parse_records(stream):
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def assert_flags(test, records):
    for r in records:
        test.assertFalse(r["candidate_admission"])
        test.assertFalse(r["containment_qualified"])
        test.assertEqual(r["schema"], "rf.workload.obs.v1")
        test.assertTrue(r["case_id"])


class TestSourceContract(unittest.TestCase):
    def test_scripts_present_regular_ascii_small_compilable(self):
        for name in SCRIPTS:
            path = os.path.join(HERE, name)
            self.assertTrue(os.path.isfile(path))
            with open(path, "rb") as f:
                data = f.read()
            self.assertGreater(len(data), 0)
            self.assertLessEqual(len(data), 4096, name)
            text = data.decode("ascii")
            compile(text, name, "exec")
            self.assertIn('if __name__ == "__main__":', text)

    def test_no_dynamic_or_env_selected_behavior(self):
        for name in SCRIPTS:
            with open(os.path.join(HERE, name), "r") as f:
                text = f.read()
            for bad in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(bad, text, name + ":" + bad)

    def test_contracts_cover_exactly_seven_scripts(self):
        named = set(CONTRACTS) - {k for k in CONTRACTS if k.startswith("_")}
        self.assertEqual(named, set(SCRIPTS))
        ids = [CONTRACTS[s]["case_id"] for s in SCRIPTS]
        self.assertEqual(ids, ["w01", "w02", "w03", "w04", "w05", "w06",
                               "w07"])
        for s in SCRIPTS:
            entry = CONTRACTS[s]
            for key in ("constants", "records", "expected_host_oracles",
                        "unresolved_preconditions"):
                self.assertTrue(entry[key], s + ":" + key)

    def test_pinned_bindings_verbatim(self):
        for key, digest in EXPECTED_BINDINGS.items():
            self.assertEqual(CONTRACTS["_bindings"][key], digest)
            self.assertEqual(len(digest), 64)
        self.assertEqual(CONTRACTS["_wrapper"]["runtime_args_ordered"],
                         ["--platform=systrap", "--network=none",
                          "--oci-seccomp"])
        self.assertEqual(CONTRACTS["_profile"]["host_pids_limit"], 128)
        self.assertEqual(CONTRACTS["_profile"]["memory_limit"], "256MiB")
        self.assertEqual(CONTRACTS["_transport"]["mandatory_flags"],
                         {"candidate_admission": False,
                          "containment_qualified": False})


class TestInertImport(unittest.TestCase):
    def test_import_inert_with_effect_apis_raising(self):
        for name in SCRIPTS:
            mod_name = name[:-3]
            sys.modules.pop(mod_name, None)
            patches = [mock.patch(n, new=raiser(n)) for n in EFFECT_APIS]
            for p in patches:
                p.start()
            try:
                m = importlib.import_module(mod_name)
            finally:
                for p in patches:
                    p.stop()
            sys.modules.pop(mod_name, None)
            for fn in ("rec", "emit"):
                self.assertTrue(callable(getattr(m, fn, None)), name)
            self.assertTrue(callable(getattr(m, "main", None)) or
                            callable(getattr(m, "run", None)), name)


class EffectGuarded(unittest.TestCase):
    def setUp(self):
        self.m = load(self.module_name)
        self.guards = []
        env = mock.patch.dict(os.environ, {"LANG": "C", "PATH": "/bin"}, clear=True)
        env.start()
        self.guards.append(env)
        effects = [os.open, os.write, os.read, os.close, os.unlink, os.fork,
                   os.waitpid, os.kill, os._exit, os.path.exists]
        import time, socket
        effects += [time.sleep, time.monotonic, socket.socket, builtins.open]
        self.defaults = []
        for fn in vars(self.m).values():
            if inspect.isfunction(fn) and fn.__defaults__:
                self.defaults.append((fn, fn.__defaults__))
                fn.__defaults__ = tuple(raiser("captured_effect") if any(v is e for e in effects) else v for v in fn.__defaults__)
        for n in ("os.open", "os.write", "os.read", "os.close", "os.unlink",
                  "os.fork", "os.waitpid", "os.kill", "os._exit",
                  "socket.socket", "time.sleep", "os.path.exists",
                  "builtins.open", "os.getuid", "os.getgid"):
            patch = mock.patch(n, new=raiser(n))
            patch.start()
            self.guards.append(patch)
        self.addCleanup(self.stop_guards)

    def stop_guards(self):
        for fn, defaults in self.defaults:
            fn.__defaults__ = defaults
        for p in reversed(self.guards):
            p.stop()


class TestW01(EffectGuarded):
    module_name = "w01_boundary"

    def test_rec_and_emit_canonical_flags(self):
        out = io.StringIO()
        self.m.emit(self.m.rec("w01.t", "observed", k=1), out)
        (r,) = parse_records(out)
        self.assertEqual(r, {"schema": "rf.workload.obs.v1", "case_id":
                             "w01.t", "outcome": "observed", "k": 1,
                             "candidate_admission": False,
                             "containment_qualified": False})

    @mock.patch("os.getuid", return_value=65534)
    @mock.patch("os.getgid", return_value=65534)
    def test_identity_and_env_names(self, gid, uid):
        with mock.patch("os.getuid", return_value=65534), mock.patch("os.getgid", return_value=65534):
            ident, env = self.m.identity_env()
        self.assertEqual(ident["uid"], 65534)
        self.assertTrue(ident["uid_met"] and ident["gid_met"])
        self.assertEqual(ident["answer"], 42)
        with mock.patch.dict(os.environ, {}, clear=True):
            env = self.m.identity_env()[1]
        self.assertFalse(env["lang"])
        self.assertFalse(env["path"])
        with mock.patch.dict(os.environ, {"LANG": "C", "PATH": "/bin"}, clear=True):
            env = self.m.identity_env()[1]
        self.assertTrue(env["lang"] and env["path"])

    def test_scratch_control_success_and_failure(self):
        with mock.patch("os.open", return_value=41) as mo, \
             mock.patch("os.write", return_value=4) as mw, \
             mock.patch("os.close"), \
             mock.patch("os.unlink") as mu:
            r = self.m.try_write(self.m.SCRATCH, True)
        mo.assert_called_once_with(self.m.SCRATCH, mock.ANY, 0o600)
        mw.assert_called_once_with(41, b"rf01")
        mu.assert_called_once_with(self.m.SCRATCH)
        self.assertEqual((r["case_id"], r["outcome"], r["bytes_written"]),
                         ("w01.scratch", "observed", 4))
        self.assertLessEqual(4, 32)
        with mock.patch("os.open",
                        side_effect=PermissionError(ER.EACCES, "x")):
            r = self.m.try_write(self.m.SCRATCH, True)
        self.assertEqual((r["outcome"], r["category"]),
                         ("failed", "errno_EACCES"))

    def test_forbidden_write_denied_and_succeeds(self):
        with mock.patch("os.open", side_effect=OSError(ER.EROFS, "ro")):
            r = self.m.try_write(self.m.FORBIDDEN, False)
        self.assertEqual((r["case_id"], r["outcome"], r["category"]),
                         ("w01.ro_root", "observed_denied", "errno_EROFS"))
        with mock.patch("os.open", return_value=42), \
             mock.patch("os.close") as mc:
            r = self.m.try_write(self.m.FORBIDDEN, False)
        mc.assert_called_once_with(42)
        self.assertEqual((r["outcome"], r["category"]),
                         ("failed", "denial_missing"))

    def test_read_status_capped_no_content(self):
        class F:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n):
                self.cap = n
                return b"ab"
        f = F()
        with mock.patch("builtins.open", return_value=f):
            r = self.m.read_status()
        self.assertEqual(f.cap, 8193)
        self.assertEqual((r["readable"], r["capped_len"], r["infer"]),
                         (True, 2, "none"))
        self.assertNotIn("content", json.dumps(r))
        with mock.patch("builtins.open",
                        side_effect=OSError(ER.EACCES, "x")):
            r = self.m.read_status()
        self.assertEqual((r["readable"], r["category"], r["infer"]),
                         (False, "errno_EACCES", "none"))

    def test_named_sockets_existence_only(self):
        with mock.patch("os.path.exists",
                        side_effect=lambda p: p.endswith("docker.sock")):
            r = self.m.named_sockets()
        self.assertEqual(r["exists"], {"/var/run/docker.sock": True,
                                       "/var/run/sshd.sock": False,
                                       "/tmp/rf-mcp-gateway.sock": False})

    def test_excluded_probe_all_absent_observed(self):
        with mock.patch("os.open",
                        side_effect=FileNotFoundError(ER.ENOENT, "x")):
            r = self.m.excluded_probe()
        self.assertEqual(r["outcome"], "observed")
        self.assertEqual(r["disclosures"], 0)
        self.assertEqual(set(r["categories"].values()), {"errno_ENOENT"})

    def test_excluded_probe_disclosure_is_failure_without_content(self):
        with mock.patch("os.open", side_effect=[7] + [OSError(
                ER.ENOENT, "x")] * 5), \
             mock.patch("os.read", return_value=b""), \
             mock.patch("os.close"):
            r = self.m.excluded_probe()
        self.assertEqual(r["outcome"], "failed")
        self.assertEqual(r["disclosures"], 1)
        self.assertNotIn("content", json.dumps(r))

    def test_loopback_probe_categories_bounds(self):
        made = []

        class S:
            def __init__(self, *a):
                made.append(self)
                self.to = None
                self.calls = []
            def settimeout(self, t):
                self.to = t
            def connect(self, addr):
                self.calls.append(("connect", addr))
                raise OSError(ER.ECONNREFUSED, "x")
            def sendto(self, data, addr):
                self.calls.append(("sendto", addr))
            def close(self):
                pass
        with mock.patch("socket.socket", S):
            r = self.m.loopback_probe(now=lambda: 0.0)
        self.assertEqual(r["categories"], ["errno_ECONNREFUSED",
                                           "udp_sent_unconfirmed",
                                           "dns_srg_sent_unconfirmed"])
        self.assertFalse(any(c.endswith("_sent_unconfirmed")
                             and "confirmed_ok" in c
                             for c in r["categories"]))
        self.assertEqual(len(made), 3)
        for s in made:
            self.assertLessEqual(s.to, 0.25)
        addrs = {c[1] for s in made for c in s.calls}
        self.assertEqual(addrs, {("127.0.0.1", 39173)})

    def test_loopback_probe_respects_total_budget(self):
        t = [0.0]

        def now():
            t[0] += 3.0
            return t[0]
        made = []

        class S:
            def __init__(self, *a):
                made.append(self)
            def __getattr__(self, k):
                return lambda *a, **k: None
        with mock.patch("socket.socket", S):
            r = self.m.loopback_probe(now=now)
        self.assertEqual(made, [])
        self.assertTrue(all(c.endswith("_skipped_budget")
                            for c in r["categories"]))


class TestW02(EffectGuarded):
    module_name = "w02_cpu_deadline"

    def test_accumulate_small_completes(self):
        acc, done, how = self.m.accumulate(n=1000, now=lambda: 0.0,
                                           deadline=8.0)
        self.assertEqual((done, how), (1000, "iterations_completed"))
        self.assertEqual(acc, sum(range(1000)) & 0xFFFFFFFFFFFF)

    def test_accumulate_deadline_fallback(self):
        t = [0.0]

        def now():
            t[0] += 1.0
            return t[0]
        acc, done, how = self.m.accumulate(n=3000000, now=now, deadline=2.0)
        self.assertEqual(how, "guest_deadline_exceeded")
        self.assertLess(done, 3000000)
        self.assertGreater(done, 0)

    def test_child_body_leaf_branch(self):
        sleeps, exits = [], []

        def ex(code):
            exits.append(code)
        with mock.patch("os.open", side_effect=OSError(ER.EACCES, "x")):
            self.m.child_body(sleep=sleeps.append, exit_fn=ex)
        self.assertEqual(sleeps, [self.m.CHILD_SLEEP_S])
        self.assertEqual(exits, [0])
        self.assertLessEqual(self.m.CHILD_SLEEP_S, 8.0)

    def test_run_parent_and_child_paths(self):
        out = io.StringIO()
        rc = self.m.run(fork=lambda: 12345, out=out, iters=1000,
                        now=lambda: 0.0)
        self.assertEqual(rc, 0)
        rs = parse_records(out)
        self.assertEqual([r["case_id"] for r in rs],
                         ["w02.header", "w02.child_fork", "w02.cpu_work",
                          "w02.final"])
        self.assertTrue(rs[1]["child_pid_recorded"])
        self.assertEqual(rs[2]["iterations"], 1000)
        self.assertFalse(rs[3]["guest_completion_proof"])
        assert_flags(self, rs)
        exits = []

        def child_body_probe():
            return None
        with mock.patch("os.open", side_effect=OSError(ER.EACCES, "x")):
            rc = self.m.run(fork=lambda: 0, out=io.StringIO(), iters=10,
                            now=lambda: 0.0, sleep=lambda s: None,
                            exit_fn=lambda c: exits.append(c))
        self.assertEqual(rc, 1)
        self.assertEqual(exits, [0, 1])

    def test_run_fork_refused_typed(self):
        out = io.StringIO()

        def fork():
            raise OSError(ER.EAGAIN, "x")
        rc = self.m.run(fork=fork, out=out, iters=100, now=lambda: 0.0)
        rs = parse_records(out)
        self.assertEqual(rc, 0)
        self.assertEqual(rs[1]["category"], "errno_EAGAIN")
        assert_flags(self, rs)


class TestW03(EffectGuarded):
    module_name = "w03_output_cap"

    def test_write_all_full_short_and_progress(self):
        self.assertEqual(self.m.write_all(lambda v: len(v), b"abcdef",
                                          now=lambda: 0.0), 6)
        counts = []

        def short(v):
            counts.append(len(v))
            return 2
        self.assertEqual(self.m.write_all(short, b"abcdef", now=lambda: 0.0),
                         6)
        self.assertEqual(counts, [6, 4, 2])

    def test_write_all_zero_progress_typed(self):
        calls = []

        def zero(v):
            calls.append(1)
            return 0
        with self.assertRaises(BlockingIOError):
            self.m.write_all(zero, b"abcd", now=lambda: 0.0, max_stalls=3)
        self.assertEqual(len(calls), 4)

    def test_write_all_deadline(self):
        t = [0.0]

        def now():
            t[0] += 1.0
            return t[0]
        calls = []

        def w(v):
            calls.append(1)
            return len(v)
        with self.assertRaises(TimeoutError):
            self.m.write_all(w, b"abcd", now=now, deadline=0.5)
        self.assertEqual(calls, [])

    def test_run_small_finite_alternating(self):
        class W:
            def __init__(self):
                self.recs = []
                self.chunk_bytes = 0
                self.chunks = 0

            def write(self, b):
                b = bytes(b)
                if b.startswith(b"{"):
                    self.recs.append(json.loads(b.decode()))
                else:
                    self.chunk_bytes += len(b)
                    self.chunks += 1
                return len(b)
        a, b = W(), W()
        rc = self.m.run(out=a, err=b, now=lambda: 0.0, total=16384)
        self.assertEqual(rc, 0)
        self.assertEqual((a.chunks, b.chunks), (2, 1))
        self.assertEqual((a.chunk_bytes, b.chunk_bytes), (8192, 4096))
        self.assertEqual([r["case_id"] for r in a.recs],
                         ["w03.header", "w03.final"])
        self.assertFalse(a.recs[-1]["guest_completion_proof"])
        self.assertTrue(a.recs[-1]["host_truncation_expected"])
        assert_flags(self, a.recs)
        raw = a.chunk_bytes + b.chunk_bytes
        self.assertEqual(raw, 12288)
        record_bytes = sum(len(json.dumps(r, sort_keys=True, separators=(",", ":")).encode()) + 1 for r in a.recs)
        self.assertLessEqual(raw + record_bytes, 16384)
        self.assertLess(raw, self.m.TOTAL)

    def test_run_error_stall_and_short_paths(self):
        class W:
            def __init__(self, data_fn):
                self.data_fn = data_fn
                self.recs = []

            def write(self, b):
                b = bytes(b)
                if b.startswith(b"{"):
                    self.recs.append(json.loads(b.decode()))
                    return len(b)
                return self.data_fn(b)

        def case(data_fn):
            a, b = W(data_fn), W(lambda v: len(v))
            rc = self.m.run(out=a, err=b, now=lambda: 0.0, total=8192)
            return rc, a.recs[-1]

        def boom(v):
            raise OSError(ER.EIO, "x")

        def zero(v):
            return 0

        def short(v):
            return 1
        rc, fin = case(boom)
        self.assertEqual((rc, fin["ended_how"]), (3, "oserror"))
        rc, fin = case(zero)
        self.assertEqual((rc, fin["ended_how"]), (3, "BlockingIOError"))
        rc, fin = case(short)
        self.assertEqual((rc, fin["ended_how"], fin["payload_bytes_written"]),
                         (0, "completed", 4096))


class TestW04(EffectGuarded):
    module_name = "w04_memory_limit"

    def test_touch_pages(self):
        buf = bytearray(8192)
        self.assertEqual(self.m.touch_pages(buf, 4096), 2)
        self.assertEqual(buf[0], 1)
        self.assertEqual(buf[4096], 1)
        self.assertEqual(buf[1], 0)

    def test_grow_boundary_counts(self):
        calls = []

        def alloc(n):
            calls.append(n)
            return bytearray(n)
        pages, total, how = self.m.grow(alloc, now=lambda: 0.0, deadline=5.0,
                                        max_bytes=4096, chunk=1024, page=256)
        self.assertEqual((pages, total, how),
                         (16, 4096, "intended_boundary_reached"))
        self.assertEqual(calls, [1024] * 4)

    def test_grow_memoryerror_refusal(self):
        seq = [bytearray(1024)] * 2

        def alloc(n):
            if seq:
                seq.pop()
                return bytearray(n)
            raise MemoryError()
        pages, total, how = self.m.grow(alloc, now=lambda: 0.0, deadline=5.0,
                                        max_bytes=40960, chunk=1024, page=256)
        self.assertEqual((pages, total, how), (8, 2048, "allocator_refusal"))

    def test_grow_deadline(self):
        t = [0.0]

        def now():
            t[0] += 1.0
            return t[0]
        calls = []

        def alloc(n):
            calls.append(n)
            return bytearray(n)
        pages, total, how = self.m.grow(alloc, now=now, deadline=1.5,
                                        max_bytes=10 ** 9, chunk=64, page=64)
        self.assertEqual(how, "guest_deadline_exceeded")
        self.assertLess(total, 10 ** 9)
        self.assertLessEqual(len(calls), 3)

    def test_run_outcomes(self):
        out = io.StringIO()
        rc = self.m.run(alloc=lambda n: bytearray(n), now=lambda: 0.0,
                        out=out, deadline=5.0, max_bytes=4096, chunk=1024,
                        page=256)
        rs = parse_records(out)
        self.assertEqual(rc, 0)
        self.assertEqual((rs[1]["outcome"], rs[2]["outcome"]),
                         ("inconclusive", "inconclusive"))
        self.assertFalse(rs[2]["guest_physical_pass"])
        assert_flags(self, rs)
        out = io.StringIO()
        rc = self.m.run(alloc=lambda n: (_ for _ in ()).throw(MemoryError()),
                        now=lambda: 0.0, out=out, deadline=5.0,
                        max_bytes=4096, chunk=1024, page=256)
        rs = parse_records(out)
        self.assertEqual(rc, 4)
        self.assertEqual(rs[1]["ended_how"], "allocator_refusal")
        self.assertTrue(rs[2]["allocator_refusal"])
        out = io.StringIO()
        rc = self.m.run(alloc=lambda n: (_ for _ in ()).throw(ValueError("x")),
                        now=lambda: 0.0, out=out, deadline=5.0,
                        max_bytes=4096, chunk=1024, page=256)
        rs = parse_records(out)
        self.assertEqual(rc, 4)
        self.assertEqual(rs[1]["error_class"], "ValueError")


class TestW05(EffectGuarded):
    module_name = "w05_process_limit"

    def test_leaf_branch(self):
        sleeps, exits = [], []
        self.m.leaf(sleep=sleeps.append, exit_fn=exits.append)
        self.assertEqual(sleeps, [self.m.CHILD_SLEEP_S])
        self.assertEqual(exits, [0])
        self.assertLessEqual(self.m.CHILD_SLEEP_S, 2.0)

    def test_run_fork_refused_reaps_own_only(self):
        kids = iter([101, 102, 103])
        state = {"n": 0}

        def fork():
            state["n"] += 1
            try:
                return next(kids)
            except StopIteration:
                raise OSError(ER.EAGAIN, "x")
        killed, waited = [], []

        def kill(pid, sig):
            killed.append((pid, sig))
        out = io.StringIO()
        rc = self.m.run(fork=fork, kill=kill,
                        wait=lambda pid, f: waited.append(pid) or (pid, 0),
                        now=lambda: 0.0, out=out)
        rs = parse_records(out)
        self.assertEqual(rc, 0)
        self.assertEqual(rs[1]["outcome"], "observed")
        self.assertEqual(rs[1]["stopped_how"], "fork_refused")
        self.assertEqual(rs[1]["refusal_categories"], {"errno_EAGAIN": 1})
        self.assertEqual(state["n"], 4)
        self.assertEqual(killed, [(101, 9), (102, 9), (103, 9)])
        self.assertEqual(waited, [101, 102, 103])
        self.assertEqual(rs[1]["reaped_own"], 3)
        self.assertFalse(rs[1]["guest_task_limit_claim"])
        assert_flags(self, rs)

    def test_run_max_attempts_unproven(self):
        counter = {"n": 0}

        def fork():
            counter["n"] += 1
            return counter["n"]
        out = io.StringIO()
        rc = self.m.run(fork=fork, kill=lambda p, s: None,
                        wait=lambda pid, f: (pid, 0), now=lambda: 0.0,
                        out=out)
        rs = parse_records(out)
        self.assertEqual(rc, 0)
        self.assertEqual(rs[1]["outcome"], "unproven")
        self.assertEqual(rs[1]["attempts"], 160)
        self.assertEqual(rs[1]["stopped_how"], "max_attempts")
        self.assertFalse(rs[1]["guest_task_limit_claim"])

    def test_run_parent_deadline_and_child_branch(self):
        ticks = iter([0.0, 0.0, 5.0, 5.0, 5.0])

        def now():
            return next(ticks)
        out = io.StringIO()
        rc = self.m.run(fork=lambda: 9, kill=lambda p, s: None,
                        wait=lambda pid, f: (pid, 0), now=now, out=out)
        rs = parse_records(out)
        self.assertEqual(rs[1]["outcome"], "inconclusive")
        self.assertEqual(rs[1]["stopped_how"], "parent_deadline")
        self.assertEqual(rs[1]["children_created"], 1)
        exits = []
        rc = self.m.run(fork=lambda: 0, kill=lambda p, s: None,
                        wait=lambda pid, f: (pid, 0), now=lambda: 0.0,
                        out=io.StringIO(), sleep=lambda s: None,
                        exit_fn=exits.append)
        self.assertEqual(rc, 1)
        self.assertEqual(exits, [0, 1])


class TestW06(EffectGuarded):
    module_name = "w06_scratch_limit"

    def test_write_scratch_limit_reached(self):
        calls = []

        def writer(fd, data):
            calls.append((fd, len(data)))
            return len(data)
        closed = []

        def closer(fd):
            closed.append(fd)
        written, how = self.m.write_scratch(opener=lambda: 7,
                                            writer=writer, closer=closer,
                                            now=lambda: 0.0,
                                            max_bytes=2 * self.m.CHUNK)
        self.assertEqual((written, how), (2 * self.m.CHUNK, "limit_reached"))
        self.assertEqual(calls, [(7, self.m.CHUNK)] * 2)
        self.assertEqual(closed, [7])

    def test_write_scratch_enospc_expected_other_typed(self):
        def enospc(fd, data):
            raise OSError(ER.ENOSPC, "x")

        def eio(fd, data):
            raise OSError(ER.EIO, "x")
        closed = []
        self.assertEqual(self.m.write_scratch(opener=lambda: 3,
                                              writer=enospc,
                                              closer=closed.append,
                                              now=lambda: 0.0),
                         (0, "errno_ENOSPC"))
        self.assertEqual(self.m.write_scratch(opener=lambda: 3,
                                              writer=eio,
                                              closer=closed.append,
                                              now=lambda: 0.0),
                         (0, "errno_EIO"))
        self.assertEqual(closed, [3, 3])

    def test_write_scratch_deadline(self):
        t = [0.0]

        def now():
            t[0] += 2.0
            return t[0]
        calls = []

        def writer(fd, data):
            calls.append(1)
            return len(data)
        written, how = self.m.write_scratch(opener=lambda: 3, writer=writer,
                                            closer=lambda fd: None, now=now,
                                            deadline=1.5)
        self.assertEqual((written, how), (0, "guest_deadline_exceeded"))
        self.assertEqual(calls, [])

    def test_forbidden_write_denied_and_succeeds(self):
        with mock.patch("os.open", side_effect=OSError(ER.EROFS, "x")):
            r = self.m.forbidden_write()
        self.assertEqual((r["outcome"], r["category"]),
                         ("observed_denied", "errno_EROFS"))
        with mock.patch("os.open", return_value=5), \
             mock.patch("os.close"):
            r = self.m.forbidden_write()
        self.assertEqual((r["outcome"], r["category"]),
                         ("failed", "denial_missing"))

    def test_child_marker_and_cleanup_own(self):
        sleeps, exits = [], []
        opened, wrote = [], []

        def opener(path, flags, mode):
            opened.append(path)
            return 11

        def writer(fd, data):
            wrote.append((fd, len(data)))
            return len(data)
        with mock.patch("os.open", opener), \
             mock.patch("os.write", writer), \
             mock.patch("os.close"):
            self.m.child_marker(sleep=sleeps.append, exit_fn=exits.append)
        self.assertEqual(sleeps, [self.m.CHILD_SLEEP_S])
        self.assertEqual(exits, [0])
        self.assertEqual(opened, [self.m.CHILD_MARKER])
        self.assertLessEqual(wrote[0][1], 16)
        removed, refused = [], []

        def unlink(p):
            if p == self.m.SCRATCH:
                refused.append(p)
                raise FileNotFoundError(ER.ENOENT, "x")
            removed.append(p)
        self.assertEqual(self.m.cleanup_own(unlink=unlink), removed)
        self.assertEqual(refused, [self.m.SCRATCH])

    @mock.patch("os.open", side_effect=OSError(ER.EROFS, "x"))
    def test_run_integration_small_with_doubles(self, open_double):
        lines = io.StringIO()
        killed, waited = [], []
        rc = self.m.run(fork=lambda: 55,
                        wait=lambda pid, f: waited.append(pid) or (pid, 0),
                        kill=lambda p, s: killed.append(p),
                        sleep=lambda s: None,
                        now=lambda: 0.0, out=lines, exit_fn=None,
                        unlink=lambda p: None,
                        opener=lambda: 7,
                        writer=lambda fd, d: len(d),
                        closer=lambda fd: None,
                        max_bytes=2 * self.m.CHUNK)
        self.assertEqual(rc, 0)
        rs = parse_records(lines)
        self.assertEqual([r["case_id"] for r in rs],
                         ["w06.header", "w06.readonly_root", "w06.child_fork",
                          "w06.scratch", "w06.final"])
        self.assertTrue(rs[2]["child_pid_recorded"])
        self.assertEqual(rs[3]["bytes_written"], 2 * self.m.CHUNK)
        self.assertEqual(rs[3]["ended_how"], "limit_reached")
        self.assertTrue(rs[3]["expected_denial"] is False)
        self.assertEqual(rs[4]["own_files_removed"], 2)
        self.assertFalse(rs[4]["guest_physical_pass"])
        self.assertEqual(killed, [55])
        self.assertEqual(waited, [55])
        assert_flags(self, rs)
        self.assertTrue(all(len(l) < 600 for l in
                            lines.getvalue().splitlines()))
        exits = []
        rc = self.m.run(fork=lambda: 0, wait=lambda pid, f: (pid, 0),
                        kill=lambda p, s: None, sleep=lambda s: None,
                        now=lambda: 0.0, out=io.StringIO(),
                        exit_fn=exits.append, unlink=lambda p: None,
                        opener=lambda: 7, writer=lambda fd, d: len(d),
                        closer=lambda fd: None, max_bytes=self.m.CHUNK)
        self.assertEqual(rc, 1)
        self.assertEqual(exits, [0, 1])


class TestW07(EffectGuarded):
    module_name = "w07_fresh_recovery"

    def test_known_answer_and_absence(self):
        self.assertEqual(self.m.known_answer(), 42)
        self.assertEqual(self.m.known_answer(6, 8), 48)
        self.assertEqual(self.m.marker_absence(lambda p: False),
                         {p: True for p in self.m.MARKERS})
        absent = self.m.marker_absence(lambda p: p.endswith(".bin"))
        self.assertEqual(absent[self.m.MARKERS[2]], False)
        self.assertEqual(absent[self.m.MARKERS[0]], True)

    @mock.patch("os.getuid", return_value=65534)
    def test_identity_names_no_env_values(self, uid):
        with mock.patch.dict(os.environ,
                             {"LANG": "C.UTF-8", "PATH": "/bin",
                              "SECRET": "x"}, clear=True):
            r = self.m.identity_names()
        self.assertTrue(r["lang_present"] and r["path_present"])
        self.assertNotIn("SECRET", json.dumps(r))
        self.assertNotIn("C.UTF-8", json.dumps(r))
        self.assertIsInstance(r["uid"], int)

    def test_wait_bounded(self):
        sleeps = []
        t = [0.0]

        def now():
            t[0] += 0.3
            return t[0]
        slept = self.m.wait_bounded(sleep=sleeps.append, now=now, seconds=8.0)
        self.assertGreater(slept, 0.0)
        self.assertLessEqual(slept, 8.0 + 0.25)
        self.assertTrue(all(0 < s <= 0.25 for s in sleeps))

    @mock.patch("os.getuid", return_value=65534)
    def test_run_happy_and_known_answer_failure(self, uid):
        out = io.StringIO()
        rc = self.m.run(sleep=lambda s: None, now=lambda: 0.0,
                        exists=lambda p: False, out=out)
        rs = parse_records(out)
        self.assertEqual(rc, 0)
        self.assertEqual([r["case_id"] for r in rs],
                         ["w07.header", "w07.known_answer",
                          "w07.freshness_markers", "w07.identity_env",
                          "w07.final"])
        self.assertTrue(rs[1]["match"])
        self.assertTrue(all(rs[2]["absent"].values()))
        self.assertEqual(rs[4]["interruption_owned_by"], "trusted_host")
        self.assertTrue(rs[4]["cancellation_is_typed_failure"])
        self.assertFalse(rs[4]["guest_completion_proof"])
        assert_flags(self, rs)
        orig = self.m.known_answer
        self.m.known_answer = lambda: 48
        try:
            out = io.StringIO()
            rc = self.m.run(sleep=lambda s: None, now=lambda: 0.0,
                            exists=lambda p: True, out=out)
            rs = parse_records(out)
            self.assertEqual(rc, 3)
            self.assertEqual(rs[1]["outcome"], "failed")
            self.assertFalse(rs[1]["match"])
        finally:
            self.m.known_answer = orig


class TestIndependentW01(EffectGuarded):
    module_name = "w01_boundary"

    def test_fixed_socket_contract_matches_actual_paths(self):
        paths = []
        with mock.patch("os.path.exists", side_effect=lambda p: paths.append(p) or False):
            r = self.m.named_sockets()
        self.assertEqual(paths, CONTRACTS["w01_boundary.py"]["constants"]["named_sockets"])
        self.assertFalse(any(r["exists"].values()))

    def test_env_extra_count_and_arithmetic_without_values(self):
        with mock.patch("os.getuid", return_value=65534), mock.patch("os.getgid", return_value=65534), mock.patch.dict(os.environ, {"LANG":"C", "PATH":"/bin", "TOKEN":"sentinel"}, clear=True):
            identity, env = self.m.identity_env()
        self.assertEqual(identity["answer"], 42)
        self.assertEqual(env["extra_count"], 1)
        self.assertNotIn("TOKEN", json.dumps(env))
        self.assertNotIn("sentinel", json.dumps(env))


class TestIndependentW03(EffectGuarded):
    module_name = "w03_output_cap"

    def test_full_fixed_budget_counts_all_bytes_no_output_storage(self):
        writes = []
        records = []
        class W:
            def __init__(self, channel):
                self.channel = channel
            def write(self, data):
                writes.append((self.channel, len(data)))
                if bytes(data[:1]) == b"{":
                    records.append(json.loads(bytes(data)))
                return len(data)
        rc = self.m.run(out=W(1), err=W(2), now=lambda: 0)
        self.assertEqual(rc, 0)
        raw = sum(n for _, n in writes)
        self.assertLessEqual(raw, CONTRACTS["w03_output_cap.py"]["constants"]["total_bytes"])
        chunks = [(c,n) for c,n in writes if n == 4096]
        self.assertEqual(len(chunks), 255)
        self.assertEqual([c for c,_ in chunks], [1 if i % 2 == 0 else 2 for i in range(255)])
        self.assertEqual(records[-1]["payload_bytes_written"], 255*4096)
        self.assertGreater(raw, records[-1]["payload_bytes_written"])
        assert_flags(self, records)


class TestIndependentW05(EffectGuarded):
    module_name = "w05_process_limit"

    def test_cleanup_waits_nonblocking_and_counts_only_reaped(self):
        waits, killed = [], []
        def wait(pid, flag):
            waits.append((pid, flag))
            return (0 if pid == 11 else pid, 0)
        r = self.m.bounded_reap([11,12], wait=wait, kill=lambda p,s:killed.append(p), now=lambda:0, end=1)
        self.assertEqual(r, [12])
        self.assertEqual(killed, [11,12])
        self.assertEqual(waits, [(11,os.WNOHANG),(12,os.WNOHANG)])
        self.assertEqual(self.m.bounded_reap([99], now=lambda:2, end=1), [])


class TestIndependentW06(EffectGuarded):
    module_name = "w06_scratch_limit"

    def test_fork_failure_and_open_failure_stay_typed_and_cleanup(self):
        def denied_fork():
            raise OSError(ER.EAGAIN, "synthetic")
        def denied_open():
            raise OSError(ER.EACCES, "synthetic")
        gone=[]
        out=io.StringIO()
        with mock.patch("os.open", side_effect=OSError(ER.EROFS, "synthetic")):
            rc=self.m.run(fork=denied_fork, now=lambda:0, out=out, opener=denied_open, unlink=gone.append, max_bytes=4)
        self.assertEqual(rc,0)
        self.assertEqual(gone,list(self.m.OWN_FILES))
        rs=parse_records(out)
        self.assertEqual(rs[2]["category"],"errno_EAGAIN")
        self.assertEqual(rs[3]["ended_how"],"errno_EACCES")
        self.assertEqual(rs[3]["outcome"],"inconclusive")
        assert_flags(self,rs)

    def test_zero_short_and_open_error_are_finite(self):
        calls=[]
        r=self.m.write_scratch(opener=lambda:1,writer=lambda f,d:calls.append(len(d)) or 0,closer=lambda f:None,now=lambda:0,max_bytes=4)
        self.assertEqual(r,(0,"no_write_progress"))
        self.assertEqual(calls,[4])
        counts=[]
        r=self.m.write_scratch(opener=lambda:1,writer=lambda f,d:counts.append(len(d)) or 1,closer=lambda f:None,now=lambda:0,max_bytes=4)
        self.assertEqual(r,(4,"limit_reached"))
        self.assertEqual(counts,[4,3,2,1])
        self.assertEqual(self.m.cleanup_own(now=lambda:6,end=5),[])

    def test_normal_cleanup_wait_nonblocking(self):
        waits=[]
        with mock.patch("os.open",side_effect=OSError(ER.EROFS,"synthetic")):
            self.m.run(fork=lambda:22,wait=lambda p,f:waits.append((p,f)) or (0,0),kill=lambda p,s:None,now=lambda:0,out=io.StringIO(),opener=lambda:1,writer=lambda f,d:len(d),closer=lambda f:None,unlink=lambda p:None,max_bytes=4)
        self.assertEqual(waits,[(22,os.WNOHANG)])


class TestIndependentW07(EffectGuarded):
    module_name = "w07_fresh_recovery"

    def test_fixed_clock_wait_never_exceeds_eight_seconds(self):
        sleeps=[]
        self.assertEqual(self.m.wait_bounded(sleep=sleeps.append,now=lambda:0),8)
        self.assertEqual(sleeps,[0.25]*32)

    def test_observation_is_flushed_before_interruption_window(self):
        class Out(io.StringIO):
            frozen=None
            def flush(self):
                self.frozen=self.getvalue()
        out=Out()
        def sleep(s):
            self.assertIsNotNone(out.frozen)
            self.assertIn('"case_id":"w07.known_answer"',out.frozen)
        with mock.patch("os.getuid",return_value=65534):
            self.m.run(sleep=sleep,now=lambda:0,exists=lambda p:False,out=out)


if __name__ == "__main__":
    unittest.main()
