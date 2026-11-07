"""Executable qualification for macro-update's embedded source owner.

The Linux subprocess cases use real flock/exec and private fixture paths. The
systemd fixture records manager behavior; it is not production manager acceptance.
No test invokes an installed updater, real systemd action, network or provider.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "app/deploy"
SOURCE = (DEPLOY / "update.sh").read_text()
PY_SOURCE = SOURCE.split("<<'MMX_LIVE_SOURCE_PY'\n", 1)[1].split("\nMMX_LIVE_SOURCE_PY\n", 1)[0]
OWNER_BLOCK = re.split(r"(?m)^# END LIVE_SOURCE_OWNER$", SOURCE.split("# BEGIN LIVE_SOURCE_OWNER\n", 1)[1], maxsplit=1)[0]


def module():
    value = types.ModuleType("embedded_source_owner_under_test")
    exec(compile(PY_SOURCE, str(DEPLOY / "update.sh") + ":embedded", "exec"), value.__dict__)
    return value


def wait_for(path: Path, process: subprocess.Popen, seconds: float = 5):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if path.exists():
            return
        if process.poll() is not None:
            out, err = process.communicate()
            raise AssertionError(f"fixture process exited {process.returncode}: {out!r} {err!r}")
        time.sleep(0.01)
    raise AssertionError(f"fixture process did not reach {path.name}")


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux filesystem and process contract")
class SourceOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".mmx-source-owner-test-", dir=Path.home())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.m = module()
        self.m.ROOT_UID, self.m.ROOT_GID = os.getuid(), os.getgid()
        for name, path in {
            "APP": "repo", "OWNER": "bin/macro-update", "LOCK": "locks/source.lock",
            "STATE": "runtime/state", "UNIT_DIR": "units", "CGROUP": "cgroups", "BOOT_ID": "boot-id",
        }.items():
            setattr(self.m, name, self.root / path)
        self.m.PENDING = self.m.STATE / "source-update.pending"
        self.m.CAPSULES = self.m.STATE / "source-update-capsules"
        for path in (self.m.APP / "app/deploy", self.m.OWNER.parent, self.m.LOCK.parent,
                     self.m.UNIT_DIR, self.m.CGROUP):
            path.mkdir(parents=True, mode=0o700)
        self.m.BOOT_ID.write_text("11111111-1111-1111-1111-111111111111\n")
        (self.m.CGROUP / "cgroup.controllers").write_text("cpu memory io")
        self.m.GIT = shutil.which("git")
        self.m.SYNC = shutil.which("true")
        self.m.BASH = shutil.which("bash")
        self.state = self.root / "systemd.json"
        self.events = self.root / "events.jsonl"
        state = {}
        for unit in self.m.UNITS:
            body = (DEPLOY / unit).read_bytes()
            (self.m.APP / "app/deploy" / unit).write_bytes(body)
            installed = self.m.UNIT_DIR / unit
            installed.write_bytes(body)
            installed.chmod(0o644)
            state[unit] = {"LoadState": "loaded", "ActiveState": "active" if unit.endswith(".timer") else "inactive",
                           "MainPID": "0", "ControlPID": "0", "ControlGroup": "",
                           "FragmentPath": str(installed), "DropInPaths": "", "NeedDaemonReload": "no",
                           "enabled": "enabled" if unit.endswith(".timer") else "static"}
        self.state.write_text(json.dumps(state))
        self.m.SYSTEMCTL = str(self.root / "systemctl")
        Path(self.m.SYSTEMCTL).write_text(
            "#!" + sys.executable + "\n"
            "import sys,json\nfrom pathlib import Path\n"
            f"p=Path({str(self.state)!r}); e=Path({str(self.events)!r})\n"
            "d=json.loads(p.read_text()); a=sys.argv[1:]\n"
            "with e.open('a') as f: f.write(json.dumps(a)+'\\n')\n"
            "if a[0]=='show':\n"
            " u=d.get(a[-1], {'LoadState':'not-found','ActiveState':'inactive','MainPID':'0','ControlPID':'0'})\n"
            " print(u.get(a[2],''))\n"
            "elif a[0]=='is-enabled':\n"
            " v=d.get(a[-1],{}).get('enabled','not-found'); print(v)\n"
            " sys.exit(0 if v in ('enabled','static') else 1)\n"
            "elif a[0] in ('start','stop'):\n"
            " u=d[a[1]]\n"
            " if u.get('fail_'+a[0]): sys.exit(1)\n"
            " u['ActiveState']='active' if a[0]=='start' else 'inactive'\n"
            " p.write_text(json.dumps(d))\n"
            "elif a[0]=='daemon-reload':\n"
            " for u in d.values(): u['NeedDaemonReload']='no'\n"
            " p.write_text(json.dumps(d))\n"
            "else: sys.exit(91)\n"
        )
        Path(self.m.SYSTEMCTL).chmod(0o755)
        for name in self.m.HELPERS:
            target = self.m.APP / "app/deploy" / name
            body = (DEPLOY / name).read_bytes()
            if name == "market-memory-options-unit-boundary.sh":
                # This fixture maps the production root principal to its owner,
                # just as the embedded Python owner's ROOT_UID/ROOT_GID do.
                import pwd, grp
                principal = pwd.getpwuid(os.getuid()).pw_name + ":" + grp.getgrgid(os.getgid()).gr_name
                self.assertEqual(body.count(b"root:root:644"), 1)
                body = body.replace(b"root:root:644", (principal + ":644").encode())
            target.write_bytes(body)
            target.chmod(0o644)
        for name in ("live-setup.sh",) + self.m.ANCILLARY_UNITS:
            target = self.m.APP / "app/deploy" / name
            target.write_bytes((DEPLOY / name).read_bytes())
            target.chmod(0o644)
        engine = self.m.APP / "engine"
        engine.mkdir()
        (engine / "value.py").write_text("VALUE = 'old'\n")
        self.m.OWNER.write_text("#!/usr/bin/env bash\n# fixture owner\n")
        self.m.OWNER.chmod(0o755)
        (self.m.APP / "app/deploy/update.sh").write_text(SOURCE)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Source barrier fixture")
        self.git("add", ".")
        self.git("commit", "-qm", "old fixture")
        self.old = self.git("rev-parse", "HEAD")
        (engine / "value.py").write_text("VALUE = 'new'\n")
        self.git("add", ".")
        self.git("commit", "-qm", "new fixture")
        self.new = self.git("rev-parse", "HEAD")
        self.git("reset", "--hard", "-q", self.old)
        self.owner = self.m.sha(self.m.OWNER.read_bytes())

    def git(self, *args):
        return subprocess.check_output([self.m.GIT, "-C", str(self.m.APP), *args], text=True,
                                       stderr=subprocess.STDOUT).strip()

    def states(self, changes=None):
        data = json.loads(self.state.read_text())
        for unit, values in (changes or {}).items():
            data[unit].update(values)
        if changes:
            self.state.write_text(json.dumps(data))
        return data

    def actions(self):
        return [json.loads(line) for line in self.events.read_text().splitlines()] if self.events.exists() else []

    def prepare(self):
        entry = self.m.entry_capture(self.owner)
        self.m.prepare(self.owner, self.old, self.new, entry.name)
        return self.m.read_pending(self.owner)

    def ready(self, *, timers=None):
        if timers:
            self.states(timers)
        journal, manifest, capsule = self.prepare()
        self.git("reset", "--hard", "-q", self.new)
        for unit in manifest["timers"]:
            self.states({unit: {"ActiveState": "inactive"}})
        journal["phase"] = "SOURCE_READY"
        journal["mirrors"] = {"site": "complete", "news": "absent", "research": "absent"}
        (self.m.APP / "site.served").mkdir(exist_ok=True)
        self.m.write_journal(journal)
        return journal, manifest, capsule

    def runtime_owner(self, child):
        substitutions = {
            'Path("/opt/macro")': repr(self.m.APP),
            'Path("/usr/local/bin/macro-update")': repr(self.m.OWNER),
            'Path("/run/lock/macro-live-source.lock")': repr(self.m.LOCK),
            'Path("/var/lib/macro-live/state")': repr(self.m.STATE),
            'Path("/etc/systemd/system")': repr(self.m.UNIT_DIR),
            'Path("/sys/fs/cgroup")': repr(self.m.CGROUP),
            'Path("/proc/sys/kernel/random/boot_id")': repr(self.m.BOOT_ID),
        }
        block = OWNER_BLOCK
        for old, replacement in substitutions.items():
            # Path repr uses PosixPath; keep the deployed Path constructor.
            block = block.replace(old, replacement.replace("PosixPath(", "Path("))
        block = block.replace('ROOT_UID = 0', f'ROOT_UID = {os.getuid()}')
        block = block.replace('ROOT_GID = 0', f'ROOT_GID = {os.getgid()}')
        block = block.replace('/usr/bin/python3 -I -S -', sys.executable + ' -I -S -')
        block = block.replace('GIT = "/usr/bin/git"', 'GIT = ' + repr(self.m.GIT))
        block = block.replace('SYSTEMCTL = "/usr/bin/systemctl"', 'SYSTEMCTL = ' + repr(self.m.SYSTEMCTL))
        block = block.replace('/var/lock/macro-update.lock', str(self.root / "updater.lock"))
        self.m.OWNER.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + block +
                               "\necho UPDATER_BODY_ENTERED >&2\nexit 93\n")
        self.m.OWNER.chmod(0o755)
        python = self.m.APP / ".venv/bin/python"
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_text("#!" + sys.executable + "\n" + child)
        python.chmod(0o755)
        self.owner = self.m.sha(self.m.OWNER.read_bytes())

    def launch(self, *args, pass_fds=()):
        process = subprocess.Popen([self.m.BASH, str(self.m.OWNER), *args],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=pass_fds)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        return process

    def test_snapshot_deadline_and_revision_survive_source_lock_wait(self):
        tick = [0.0]
        def flock(fd, operation):
            if tick[0] < 50:
                tick[0] = 50.0
                raise BlockingIOError
        with mock.patch.object(self.m, "owner_identity", return_value=self.owner), \
             mock.patch.object(self.m, "open_lock", return_value=8), \
             mock.patch.object(self.m, "verify_lock"), \
             mock.patch.object(self.m, "read_pending", return_value=None), \
             mock.patch.object(self.m, "git", return_value=self.old) as git, \
             mock.patch.object(self.m.os, "close"), \
             mock.patch.object(self.m.os, "set_inheritable"), \
             mock.patch.object(self.m.os, "chdir") as chdir, \
             mock.patch.object(self.m.os, "execv", side_effect=RuntimeError("fixture exec")) as execute, \
             mock.patch.object(self.m.fcntl, "flock", side_effect=flock), \
             mock.patch.object(self.m.time, "monotonic", side_effect=lambda: tick[0]), \
             mock.patch.object(self.m.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "fixture exec"):
                self.m.main(["fixture-descriptor", "run", "snapshot"])
        command = execute.call_args.args[1]
        self.assertEqual(float(command[command.index("--deadline-monotonic") + 1]), 400.0)
        self.assertEqual(command[command.index("--source-revision") + 1], self.old)
        self.assertEqual(command[command.index("--source-lock-fd") + 1], "8")
        git.assert_called_once_with("rev-parse", "HEAD", timeout=5.0)
        chdir.assert_called_once_with(self.m.APP)

    def test_snapshot_deadline_expiry_during_lock_wait_never_executes(self):
        tick = [0.0]
        def blocked(fd, operation):
            tick[0] += 200.0
            raise BlockingIOError
        with mock.patch.object(self.m, "owner_identity", return_value=self.owner), \
             mock.patch.object(self.m, "open_lock", return_value=8), \
             mock.patch.object(self.m.os, "close"), \
             mock.patch.object(self.m.os, "set_inheritable"), \
             mock.patch.object(self.m.os, "execv") as execute, \
             mock.patch.object(self.m, "git") as git, \
             mock.patch.object(self.m.fcntl, "flock", side_effect=blocked), \
             mock.patch.object(self.m.time, "monotonic", side_effect=lambda: tick[0]), \
             mock.patch.object(self.m.time, "sleep"):
            with self.assertRaisesRegex(self.m.Refusal, "budget exhausted waiting"):
                self.m.main(["fixture-descriptor", "run", "snapshot"])
        execute.assert_not_called()
        git.assert_not_called()

    def test_real_live_entry_binds_release_and_canonical_cwd(self):
        self.runtime_owner(
            "import os,sys,json,time\nfrom pathlib import Path\n"
            "print(json.dumps({'argv':sys.argv,'cwd':str(Path.cwd()),"
            "'lock_inode':os.fstat(8).st_ino,'entered':time.monotonic()}))\n")
        foreign = self.root / "foreign"
        foreign.mkdir()
        for lane, budget in (("snapshot", 400), ("bars", 880), ("sector-inputs", 880)):
            with self.subTest(lane=lane):
                process = subprocess.Popen([self.m.BASH, str(self.m.OWNER), "--live-lane", lane],
                    cwd=foreign, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.addCleanup(lambda process=process: process.kill() if process.poll() is None else None)
                out, err = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, err.decode())
                observed = json.loads(out)
                argv = observed["argv"]
                self.assertEqual(argv[argv.index("--lane") + 1], lane)
                self.assertEqual(observed["cwd"], str(self.m.APP))
                self.assertEqual(argv[argv.index("--source-revision") + 1], self.old)
                self.assertEqual(argv[argv.index("--source-lock-fd") + 1], "8")
                self.assertEqual(observed["lock_inode"], self.m.LOCK.stat().st_ino)
                remaining = float(argv[argv.index("--deadline-monotonic") + 1]) - observed["entered"]
                self.assertGreater(remaining, 0)
                self.assertLess(remaining, budget)
        self.assertEqual(self.m.LANES, ("fast", "snapshot", "bars"))
        self.assertEqual(len(self.m.UNITS), 6)

    def test_embedded_program_and_shell_compile(self):
        compile(PY_SOURCE, "source-owner", "exec")
        subprocess.run([self.m.BASH, "-n", str(DEPLOY / "update.sh")], check=True)

    def test_true_absence_and_unsafe_parent_are_distinct(self):
        self.assertFalse(self.m.pending_exists())
        self.m.STATE.parent.mkdir(parents=True)
        self.m.STATE.symlink_to(self.root / "missing")
        with self.assertRaises(self.m.Refusal):
            self.m.pending_exists()

    def test_pending_lstat_permission_error_is_not_absence(self):
        self.m.directory(self.m.STATE, create=True)
        original = Path.lstat
        def lstat(path, *args, **kwargs):
            if path == self.m.PENDING:
                raise PermissionError("fixture denied")
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, "lstat", lstat):
            with self.assertRaises(PermissionError):
                self.m.pending_exists()

    def test_pending_malformed_types_refuse_without_blocking(self):
        self.m.directory(self.m.STATE, create=True)
        for kind in ("directory", "fifo", "symlink", "invalid", "oversized", "duplicate"):
            with self.subTest(kind=kind):
                if kind == "directory": self.m.PENDING.mkdir()
                elif kind == "fifo": os.mkfifo(self.m.PENDING)
                elif kind == "symlink": self.m.PENDING.symlink_to(self.root / "missing")
                else:
                    body = {"invalid": b"not json", "oversized": b"x" * 65537,
                            "duplicate": b'{"schema":1,"schema":2}'}[kind]
                    self.m.PENDING.write_bytes(body)
                    self.m.PENDING.chmod(0o600)
                start = time.monotonic()
                with self.assertRaises((self.m.Refusal, OSError, ValueError)):
                    self.m.read_pending(self.owner)
                self.assertLess(time.monotonic() - start, 1)
                if kind == "directory": self.m.PENDING.rmdir()
                else: self.m.PENDING.unlink()

    def test_setup_uses_preflight_revision_without_recapture(self):
        entry = self.m.entry_capture(self.owner)
        self.git("reset", "--hard", "-q", self.new)
        with mock.patch.object(self.m, "owner_identity", return_value=self.owner), \
             mock.patch.object(self.m, "git", side_effect=AssertionError("must not recapture HEAD")), \
             mock.patch("builtins.print") as output:
            self.m.main(["fixture-fd", "entry-old", entry.name])
        output.assert_called_once_with(self.old)
        with self.assertRaises(self.m.Refusal):
            self.m.entry_old("f" * 64, entry.name)
        with self.assertRaises(self.m.Refusal):
            self.m.entry_old(self.owner, "../entry")
        helper = entry / "helpers" / self.m.HELPERS[0]
        helper.write_bytes(helper.read_bytes() + b"changed")
        with self.assertRaises(self.m.Refusal):
            self.m.entry_old(self.owner, entry.name)

    def test_entry_captures_before_mutable_import(self):
        entry = self.m.entry_capture(self.owner)
        name = self.m.HELPERS[0]
        original = (entry / "helpers" / name).read_bytes()
        (self.m.APP / "app/deploy" / name).write_text("corrupt checkout")
        _, values = self.m.entry_read(self.owner, entry.name, self.old)
        self.assertEqual(values["helpers/" + name], original)
        with self.assertRaises(self.m.Refusal):
            self.m.entry_capture(self.owner)

    def test_pending_recovery_does_not_consult_checkout_or_git(self):
        journal, manifest, capsule = self.prepare()
        for name in self.m.HELPERS:
            (self.m.APP / "app/deploy" / name).write_text("not an executable helper")
        with mock.patch.object(self.m, "git", side_effect=AssertionError("mutable Git read")):
            found = self.m.read_pending(self.owner)
        self.assertEqual(found[1]["old"], self.old)
        self.assertEqual(found[1]["new"], self.new)
        self.assertEqual(found[2], capsule)

    def test_incompatible_owner_and_corrupted_capsule_refuse(self):
        _, _, capsule = self.prepare()
        with self.assertRaises(self.m.Refusal):
            self.m.read_pending("0" * 64)
        helper = capsule / "helpers" / self.m.HELPERS[0]
        helper.write_text("changed")
        with self.assertRaises(self.m.Refusal):
            self.m.read_pending(self.owner)

    def test_pending_prevents_new_target_and_owner_replacement(self):
        self.prepare()
        with self.assertRaises(self.m.Refusal):
            self.m.prepare(self.owner, self.old, self.new, "0" * 32)
        with self.assertRaises(self.m.Refusal):
            self.m.replace_owner("/proc/1/fd/255", self.new)

    def test_initial_partial_and_public_footprint_are_not_fresh(self):
        (self.m.UNIT_DIR / self.m.UNITS[0]).unlink()
        with self.assertRaises(self.m.Refusal):
            self.m.unit_inventory()
        for unit in self.m.UNITS[1:]:
            (self.m.UNIT_DIR / unit).unlink()
        self.state.write_text("{}")
        self.assertEqual(self.m.unit_inventory(), ("absent", {}))
        (self.m.STATE.parent / "public").mkdir(parents=True)
        with self.assertRaises(self.m.Refusal):
            self.m.unit_inventory()

    def test_mask_runtime_enablement_and_transitional_intent_refuse(self):
        unit = "macro-live-fast.timer"
        for changes in ({"enabled": "masked"}, {"enabled": "enabled-runtime"},
                        {"enabled": "disabled", "ActiveState": "activating"}):
            with self.subTest(changes=changes):
                self.states({unit: changes})
                with self.assertRaises(self.m.Refusal):
                    self.m.unit_inventory()

    def test_stable_lock_rejects_symlink_wrong_mode_and_replaced_inode(self):
        self.m.LOCK.symlink_to(self.root / "missing")
        with self.assertRaises(OSError):
            self.m.open_lock()
        self.m.LOCK.unlink()
        fd = self.m.open_lock()
        try:
            self.m.LOCK.chmod(0o666)
            with self.assertRaises(self.m.Refusal):
                self.m.verify_lock(fd)
            self.m.LOCK.chmod(0o600)
            moved = self.m.LOCK.with_suffix(".retired")
            self.m.LOCK.rename(moved)
            self.m.LOCK.touch(mode=0o600)
            with self.assertRaises(self.m.Refusal):
                self.m.verify_lock(fd)
        finally:
            os.close(fd)

    def test_four_timer_combinations_restore_without_enabling_or_restarting(self):
        unit = "macro-live-fast.timer"
        for enabled in ("enabled", "disabled"):
            for active in (True, False):
                with self.subTest(enabled=enabled, active=active):
                    self.git("reset", "--hard", "-q", self.old)
                    self.states({u: {"enabled": "disabled", "ActiveState": "inactive"}
                                 for u in self.m.UNITS if u.endswith(".timer")})
                    self.states({unit: {"enabled": enabled, "ActiveState": "active" if active else "inactive"}})
                    journal, manifest, capsule = self.ready()
                    before = len(self.actions())
                    self.m.restore(journal, manifest, capsule)
                    actions = self.actions()[before:]
                    self.assertEqual([a for a in actions if a[0] == "start"], [["start", unit]] if active else [])
                    self.assertFalse(any(a[0] in ("enable", "restart") for a in actions))
                    self.assertEqual(self.states()[unit]["enabled"], enabled)
                    self.assertFalse(self.m.pending_exists())

    def test_one_held_timer_does_not_block_other_restorations(self):
        journal, manifest, capsule = self.ready()
        self.states({"macro-live-bars.timer": {"enabled": "masked"}})
        with self.assertRaises(self.m.Refusal):
            self.m.restore(journal, manifest, capsule)
        for unit in ("macro-live-fast.timer", "macro-live-snapshot.timer"):
            self.assertEqual(self.states()[unit]["ActiveState"], "active")
        self.assertTrue(self.m.pending_exists())
        self.assertEqual(self.m.read_pending(self.owner)[0]["phase"], "RESTORING")

    def test_already_active_start_receipt_is_reconciled_without_replay(self):
        journal, manifest, capsule = self.ready()
        unit = "macro-live-fast.timer"
        journal["restoration"][unit] = "starting"
        self.m.write_journal(journal)
        self.states({unit: {"ActiveState": "active"}})
        before = len(self.actions())
        self.m.restore(journal, manifest, capsule)
        self.assertNotIn(["start", unit], self.actions()[before:])

    def test_ambiguous_start_and_later_disable_keep_original_journal(self):
        journal, manifest, capsule = self.ready()
        unit = "macro-live-fast.timer"
        journal["restoration"][unit] = "starting"
        self.m.write_journal(journal)
        with self.assertRaises(self.m.Refusal):
            self.m.restore(journal, manifest, capsule)
        self.assertNotIn(["start", unit], self.actions())
        self.assertEqual(self.m.read_pending(self.owner)[1]["new"], self.new)

    def test_reboot_never_rearms_disabled_manual_timer(self):
        journal, manifest, capsule = self.ready(timers={
            "macro-live-fast.timer": {"enabled": "disabled", "ActiveState": "active"}})
        self.m.BOOT_ID.write_text("22222222-2222-2222-2222-222222222222")
        with self.assertRaises(self.m.Refusal):
            self.m.restore(journal, manifest, capsule)
        self.assertEqual(self.states()["macro-live-fast.timer"]["ActiveState"], "inactive")
        self.assertTrue(self.m.pending_exists())

    def test_ready_requires_target_and_clean_executable_source(self):
        journal, manifest, capsule = self.prepare()
        with self.assertRaises(self.m.Refusal):
            self.m.source_ready(manifest, journal)
        self.git("reset", "--hard", "-q", self.new)
        self.m.source_ready(manifest, journal)
        (self.m.APP / "engine/value.py").write_text("unexpected source")
        with self.assertRaises(self.m.Refusal):
            self.m.source_ready(manifest, journal)

    def test_ready_recovery_refuses_a_lost_completed_mirror(self):
        journal, manifest, capsule = self.ready()
        (self.m.APP / "site.served").rmdir()
        before = len(self.actions())
        with self.assertRaisesRegex(self.m.Refusal, "completed mirror destination is missing"):
            self.m.restore(journal, manifest, capsule)
        self.assertTrue(self.m.pending_exists())
        self.assertFalse(any(a[0] == "start" for a in self.actions()[before:]))

    def test_restoration_durability_failure_does_not_continue_or_retire(self):
        journal, manifest, capsule = self.ready()
        original = self.m.write_journal
        calls = []
        def write(value):
            calls.append(dict(value["restoration"]))
            original(value)
            if len(calls) == 2:
                raise self.m.EffectNeedsReadback("visible starting receipt; fsync failed")
        before = len(self.actions())
        with mock.patch.object(self.m, "write_journal", side_effect=write):
            with self.assertRaises(self.m.EffectNeedsReadback):
                self.m.restore(journal, manifest, capsule)
        self.assertEqual(len(calls), 2)
        self.assertTrue(self.m.pending_exists())
        self.assertFalse(any(a[0] == "start" for a in self.actions()[before:]))
        self.assertFalse((capsule / "completion.json").exists())

    def test_pre_replacement_journal_failure_stops_all_sibling_writes(self):
        journal, manifest, capsule = self.ready()
        original = self.m.write_journal
        calls = []
        def write(value):
            calls.append(dict(value["restoration"]))
            if len(calls) == 2:
                raise OSError("fixture disk failure before replacement")
            original(value)
        before = len(self.actions())
        with mock.patch.object(self.m, "write_journal", side_effect=write):
            with self.assertRaises(OSError):
                self.m.restore(journal, manifest, capsule)
        self.assertEqual(len(calls), 2)
        self.assertFalse(any(a[0] == "start" for a in self.actions()[before:]))
        disk = self.m.read_pending(self.owner)[0]
        self.assertEqual(set(disk["restoration"].values()), {"pending"})

    def test_unprepared_capsule_retirement_preserves_transaction_evidence(self):
        entry = self.m.entry_capture(self.owner)
        self.m.retire_entry(entry.name)
        self.assertFalse(entry.exists())
        first = self.m.entry_capture(self.owner)
        second = self.m.entry_capture(self.owner)
        self.m.retire_unprepared_entries()
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())
        _, _, prepared = self.prepare()
        with self.assertRaises(self.m.Refusal):
            self.m.retire_entry(prepared.name)
        self.assertTrue((prepared / "manifest.json").exists())

    def test_cgroup_descendants_and_wrong_identity_refuse(self):
        unit = "macro-live-fast.service"
        self.states({unit: {"ControlGroup": "/system.slice/" + unit}})
        root = self.m.CGROUP / "system.slice" / unit
        (root / "child").mkdir(parents=True)
        (root / "cgroup.procs").write_text("")
        (root / "child/cgroup.procs").write_text("12345\n")
        with self.assertRaises(self.m.Refusal):
            self.m.check_cgroup(unit)
        (root / "child/cgroup.procs").write_text("")
        self.m.check_cgroup(unit)
        self.states({unit: {"ControlGroup": "/foreign.service"}})
        with self.assertRaises(self.m.Refusal):
            self.m.check_cgroup(unit)

    def test_atomic_replace_keeps_open_inode_and_reports_postrename_fsync_failure(self):
        target = self.m.OWNER
        old = target.read_bytes()
        with target.open("rb") as stream:
            self.m.atomic_write(target, b"successor", 0o755)
            self.assertEqual(stream.read(), old)
            self.assertEqual(target.read_bytes(), b"successor")
        original = self.m.sync_dir
        def fail_parent(path):
            if path == target.parent:
                raise OSError("injected durability failure after rename")
            return original(path)
        with mock.patch.object(self.m, "sync_dir", fail_parent):
            with self.assertRaises(self.m.EffectNeedsReadback) as effect:
                self.m.atomic_write(target, b"visible but fsync unproven", 0o755)
            self.assertIn("expected sha256=", str(effect.exception))
        self.assertEqual(target.read_bytes(), b"visible but fsync unproven")

    @unittest.skipUnless(sys.platform.startswith("linux"), "real /proc Bash fd and exec require Linux")
    def test_runtime_preserves_exact_python_exit_status_and_no_fallthrough(self):
        for code in (0, 75, 23):
            with self.subTest(code=code):
                self.runtime_owner(f"import sys\nsys.exit({code})\n")
                process = self.launch("--live-lane", "fast")
                out, err = process.communicate(timeout=5)
                self.assertEqual(process.returncode, code, err.decode())
                self.assertNotIn(b"UPDATER_BODY_ENTERED", err)
                shutil.rmtree(self.m.APP / ".venv")

    @unittest.skipUnless(sys.platform.startswith("linux"), "real /proc Bash fd and exec require Linux")
    def test_runtime_holds_shared_lock_through_python_exec(self):
        entered, release = self.root / "entered", self.root / "release"
        self.runtime_owner(
            "import os,time\nfrom pathlib import Path\n"
            f"Path({str(entered)!r}).write_text(str(os.fstat(8).st_ino))\n"
            f"p=Path({str(release)!r})\n"
            "while not p.exists(): time.sleep(0.01)\n"
        )
        process = self.launch("--live-lane", "snapshot")
        wait_for(entered, process)
        fd = self.m.open_lock()
        try:
            self.assertEqual(int(entered.read_text()), os.fstat(fd).st_ino)
            with self.assertRaises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release.touch()
            out, err = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, err.decode())
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)

    @unittest.skipUnless(sys.platform.startswith("linux"), "real /proc Bash fd and exec require Linux")
    def test_runtime_does_not_take_or_unlock_inherited_updater_mutex(self):
        self.runtime_owner("import sys\nsys.exit(0)\n")
        path = self.root / "updater.lock"
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        second = os.open(path, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.dup2(fd, 9, inheritable=True)
            process = self.launch("--live-lane", "bars", pass_fds=(9,))
            out, err = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, err.decode())
            with self.assertRaises(BlockingIOError):
                fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            for descriptor in {fd, second, 9}:
                try: os.close(descriptor)
                except OSError: pass

    @unittest.skipUnless(sys.platform.startswith("linux"), "real /proc Bash fd and exec require Linux")
    def test_pending_runtime_admission_is_closed_until_source_ready(self):
        self.runtime_owner("import sys\nsys.exit(0)\n")
        journal, manifest, capsule = self.prepare()
        for phase in ("PREPARED", "GUARDS_READY", "MUTATING", "SOURCE_READY", "RESTORING"):
            with self.subTest(phase=phase):
                journal["phase"] = phase
                if phase in ("SOURCE_READY", "RESTORING"):
                    journal["mirrors"] = {"site": "complete", "news": "absent", "research": "absent"}
                self.m.write_journal(journal)
                if phase in ("SOURCE_READY", "RESTORING"):
                    self.git("reset", "--hard", "-q", self.new)
                process = self.launch("--live-lane", "fast")
                out, err = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0 if phase in ("SOURCE_READY", "RESTORING") else 75, err.decode())

    def integration_owner(self):
        """Execute the real owner, guard helpers, pull selection and mirror block."""
        self.runtime_owner("raise SystemExit(0)\n")
        prefix = self.m.OWNER.read_text().split("\necho UPDATER_BODY_ENTERED", 1)[0]
        def block(name):
            return re.search(r"(?ms)^# BEGIN " + name + r"\n.*?^# END " + name + r"$", SOURCE).group()
        preflight = SOURCE[SOURCE.index("# Resolve recovery before executing"):SOURCE.index("\n\nOPTIONS_TIMER_WAS_ENABLED=")]
        mutation = SOURCE[SOURCE.index('CHANGED=""\nREPO_UPDATED=0'):SOURCE.index("\n# Reconcile artifact selection")]
        transaction = block("LIVE_SOURCE_TRANSACTION").replace("/etc/systemd/system", str(self.m.UNIT_DIR))
        stop = block("W1B5_UNIT_STOP_HELPERS").replace("/etc/systemd/system", str(self.m.UNIT_DIR))
        mutation = mutation.replace("/etc/caddy/Caddyfile", str(self.root / "Caddyfile"))
        self.remote_target = self.root / "remote-target"
        self.remote_target.write_text(self.new)
        (self.root / "Caddyfile").write_text("# no mover redirect\n")
        (self.m.APP / "app/deploy/Caddyfile").write_text("# no mover redirect\n")
        for rel in ("site", "properties/news", "properties/research"):
            directory = self.m.APP / rel
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "index.html").write_text("fixture " + rel)
        copy = self.root / "copy.py"
        copy.write_text("import sys,shutil\nshutil.copytree(sys.argv[1],sys.argv[2],dirs_exist_ok=True)\n")
        log = self.root / "log-event.py"
        log.write_text("import sys,json\nfrom pathlib import Path\n" +
                       f"with Path({str(self.events)!r}).open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n")
        import shlex
        q = shlex.quote
        harness = f"""
APP_DIR={q(str(self.m.APP))}
FIXTURE={q(str(self.root))}
LIVE_SOURCE_PURPOSE=update
LIVE_SETUP_ATTEMPT=""
OPTIONS_RUNTIME_CLOSURE_REGEX='^engine/'
OPTIONS_RECIPROCAL_CLOSURE_REGEX='^engine/'
OPTIONS_API_FENCE_MARKER="$FIXTURE/options-marker"
OPTIONS_DEFER_REARM_FOR_SELF_UPDATE=0
DISK_REFUSED=0
log_event() {{ {q(sys.executable)} {q(str(log))} "$@"; }}
disarm_options_timer() {{ log_event options-disarm; }}
stop_reciprocal_market_memory_writers() {{ log_event reciprocal-stop; }}
reconcile_ohlc_delivery() {{ log_event ohlc-reconcile; }}
systemctl() {{
 if [ "$1" = daemon-reload ] && [ -f "$FIXTURE/fail-reload" ]; then return 42; fi
 {q(self.m.SYSTEMCTL)} "$@"
}}
systemd-analyze() {{
 log_event unit-verify "$@"
 [ ! -f "$FIXTURE/fail-verify" ]
}}
git() {{
 if [ "$3" = fetch ]; then
  log_event git-fetch
  cat "$FIXTURE/remote-target" > "$APP_DIR/.git/FETCH_HEAD"
  if [ -f "$FIXTURE/fail-fetch" ]; then return 43; fi
 else
  if [ "$3" = reset ]; then log_event git-reset "$@"; fi
  command {q(self.m.GIT)} "$@"
  if [ "$3" = reset ] && [ -f "$FIXTURE/crash-after-reset" ]; then kill -KILL "$$"; fi
 fi
}}
rsync() {{
 local source="" destination="" argument=""
 for argument in "$@"; do source=$destination; destination=$argument; done
 log_event mirror "$source" "$destination"
 case "$source" in
  */properties/news/) [ ! -f "$FIXTURE/fail-news" ] || return 44 ;;
  */properties/research/) [ ! -f "$FIXTURE/fail-research" ] || return 45 ;;
  */site/) [ ! -f "$FIXTURE/fail-site" ] || return 46 ;;
 esac
 {q(sys.executable)} {q(str(copy))} "$source" "$destination"
}}
exec 9>"$FIXTURE/updater.lock"
flock -n 9 || exit 47
"""
        script = prefix + harness + preflight + "\n" + stop + "\n" + transaction + "\n"
        script += block("MACRO_UPDATE_PULL_SELECT") + "\n" + mutation + "\nlog_event transaction-returned\n"
        self.m.OWNER.write_text(script)
        self.m.OWNER.chmod(0o755)
        self.owner = self.m.sha(self.m.OWNER.read_bytes())
        subprocess.run([self.m.BASH, "-n", str(self.m.OWNER)], check=True)

    def integration_run(self):
        result = subprocess.run([self.m.BASH, str(self.m.OWNER)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=30)
        return result

    def test_integrated_first_adoption_installs_guards_and_mirrors_before_restore(self):
        self.integration_owner()
        result = self.integration_run()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        actions = self.actions()
        reload_at = next(i for i, a in enumerate(actions) if a == ["daemon-reload"])
        stop_at = next(i for i, a in enumerate(actions) if a == ["stop", "macro-live-fast.service"])
        reset_at = next(i for i, a in enumerate(actions) if a[0] == "git-reset")
        mirrors = [i for i, a in enumerate(actions) if a[0] == "mirror"]
        restore_at = next(i for i, a in enumerate(actions) if a == ["start", "macro-live-fast.timer"])
        self.assertLess(reload_at, stop_at)
        self.assertLess(stop_at, reset_at)
        self.assertLess(reset_at, min(mirrors))
        self.assertEqual(len(mirrors), 3)
        self.assertLess(max(mirrors), restore_at)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.new)
        self.assertFalse(self.m.pending_exists())
        self.assertFalse(any(a[0] in ("enable", "restart") for a in actions))

    def test_integrated_changed_fetch_head_cannot_redirect_crash_recovery(self):
        self.integration_owner()
        marker = self.root / "crash-after-reset"
        marker.touch()
        first = self.integration_run()
        self.assertEqual(first.returncode, -9)
        journal, manifest, capsule = self.m.read_pending(self.owner)
        self.assertEqual(journal["phase"], "MUTATING")
        self.assertEqual(manifest["old"], self.old)
        self.assertEqual(manifest["new"], self.new)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.new)
        marker.unlink()
        self.remote_target.write_text(self.old)
        (self.m.APP / ".git/FETCH_HEAD").write_text(self.old)
        before = len(self.actions())
        second = self.integration_run()
        self.assertEqual(second.returncode, 0, second.stderr.decode())
        later = self.actions()[before:]
        self.assertNotIn(["git-fetch"], later)
        resets = [a for a in later if a[0] == "git-reset"]
        self.assertEqual(len(resets), 1)
        self.assertEqual(resets[0][-1], self.new)
        self.assertEqual(len([a for a in later if a[0] == "mirror"]), 3)
        self.assertFalse(self.m.pending_exists())

    def test_integrated_mirror_failure_retains_pending_and_replays_original_mirrors(self):
        self.integration_owner()
        fail = self.root / "fail-news"
        fail.touch()
        first = self.integration_run()
        self.assertEqual(first.returncode, 44, first.stderr.decode())
        journal, manifest, capsule = self.m.read_pending(self.owner)
        self.assertEqual(journal["phase"], "MUTATING")
        self.assertEqual(journal["mirrors"], {"site": "complete", "news": "pending", "research": "pending"})
        fail.unlink()
        before = len(self.actions())
        second = self.integration_run()
        self.assertEqual(second.returncode, 0, second.stderr.decode())
        self.assertEqual(len([a for a in self.actions()[before:] if a[0] == "mirror"]), 3)

    def test_integrated_loaded_fragment_refusal_precedes_any_reset(self):
        self.integration_owner()
        self.states({"macro-live-fast.service": {"FragmentPath": "/foreign/unit.service"}})
        result = self.integration_run()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(a[0] == "git-reset" for a in self.actions()))
        self.assertEqual(self.git("rev-parse", "HEAD"), self.old)
        self.assertTrue(self.m.pending_exists())

    def test_integrated_source_ready_recovery_restores_without_fetch_reset_or_mirror(self):
        self.integration_owner()
        self.states({"macro-live-fast.timer": {"fail_start": True}})
        first = self.integration_run()
        self.assertNotEqual(first.returncode, 0)
        journal, manifest, capsule = self.m.read_pending(self.owner)
        self.assertEqual(journal["phase"], "RESTORING")
        self.assertEqual(self.states()["macro-live-snapshot.timer"]["ActiveState"], "active")
        # Reconcile the original ambiguous start through observed manager state.
        self.states({"macro-live-fast.timer": {"fail_start": False, "ActiveState": "active"}})
        before = len(self.actions())
        second = self.integration_run()
        self.assertEqual(second.returncode, 0, second.stderr.decode())
        self.assertFalse(any(a[0] in ("git-fetch", "git-reset", "mirror", "start")
                             for a in self.actions()[before:]))
        self.assertFalse(self.m.pending_exists())

    def test_integrated_foreign_head_refuses_before_mutating_units_or_source(self):
        self.integration_owner()
        fail = self.root / "fail-site"
        fail.touch()
        first = self.integration_run()
        self.assertNotEqual(first.returncode, 0)
        (self.m.APP / "engine/value.py").write_text("VALUE = 'foreign'\n")
        self.git("add", "engine/value.py")
        self.git("commit", "-qm", "foreign owner")
        foreign = self.git("rev-parse", "HEAD")
        fail.unlink()
        before = len(self.actions())
        second = self.integration_run()
        self.assertNotEqual(second.returncode, 0)
        self.assertIn(b"foreign HEAD", second.stderr)
        self.assertEqual(self.actions()[before:], [])
        self.assertEqual(self.git("rev-parse", "HEAD"), foreign)
        self.assertTrue(self.m.pending_exists())

    def test_integrated_no_change_repairs_loaded_drift_without_rearming_disabled_timer(self):
        self.integration_owner()
        self.remote_target.write_text(self.old)
        self.states({"macro-live-fast.timer": {"enabled": "disabled", "ActiveState": "inactive"},
                     "macro-live-snapshot.service": {"NeedDaemonReload": "yes"}})
        result = self.integration_run()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(["daemon-reload"], self.actions())
        self.assertFalse(any(a[0] in ("git-reset", "mirror") for a in self.actions()))
        self.assertNotIn(["start", "macro-live-fast.timer"], self.actions())
        self.assertEqual(self.states()["macro-live-fast.timer"]["enabled"], "disabled")

    def test_closed_unit_parser_rejects_hooks_duplicate_commands_and_wrong_timer(self):
        service = (DEPLOY / "macro-live-fast.service").read_bytes()
        timer = (DEPLOY / "macro-live-fast.timer").read_bytes()
        for bad in (service.replace(b"ExecStart=", b" ExecStartPre=/bin/true\nExecStart="),
                    service.replace(b"Type=oneshot", b"Type=oneshot\nSuccessExitStatus=75"),
                    service.replace(b"ExecStart=", b"ExecStart=/bin/true\nExecStart="),
                    service.replace(b"PrivateTmp=true", b"PrivateTmp=true\nKillMode=process")):
            with self.subTest(bad=hashlib.sha256(bad).hexdigest()):
                with self.assertRaises(self.m.Refusal):
                    self.m.reviewed_unit_shape("macro-live-fast.service", bad)
        with self.assertRaises(self.m.Refusal):
            self.m.reviewed_unit_shape("macro-live-fast.timer", timer.replace(b"fast.service", b"foreign.service"))

    def test_cgroup_original_path_survives_empty_post_stop_manager_property(self):
        unit = "macro-live-fast.service"
        group = "/original.slice/" + unit
        root = self.m.CGROUP / group.lstrip("/")
        root.mkdir(parents=True)
        (root / "cgroup.procs").write_text("43210\n")
        self.states({unit: {"ControlGroup": ""}})
        with self.assertRaises(self.m.Refusal):
            self.m.check_cgroup(unit, group)
        (root / "cgroup.procs").unlink()
        with self.assertRaises(self.m.Refusal):
            self.m.check_cgroup(unit, group)

    def test_unfinished_mirror_receipt_cannot_be_source_ready(self):
        journal, manifest, capsule = self.prepare()
        journal["phase"] = "SOURCE_READY"
        self.m.write_journal(journal)
        with self.assertRaises(self.m.Refusal):
            self.m.read_pending(self.owner)


    def setup_transaction(self, *, fresh=False, ancillary_present=False, existing_environment=True):
        if fresh:
            data = self.states()
            for unit in self.m.UNITS:
                (self.m.UNIT_DIR / unit).unlink()
                data.pop(unit, None)
            self.state.write_text(json.dumps(data))
        if ancillary_present:
            data = self.states()
            for unit in self.m.ANCILLARY_UNITS:
                installed = self.m.UNIT_DIR / unit
                installed.write_bytes((DEPLOY / unit).read_bytes())
                installed.chmod(0o644)
                data[unit] = {"LoadState": "loaded", "ActiveState": "inactive", "MainPID": "0",
                              "ControlPID": "0", "ControlGroup": "", "FragmentPath": str(installed),
                              "DropInPaths": "", "NeedDaemonReload": "no",
                              "enabled": "disabled" if unit.endswith(".timer") else "static"}
            self.state.write_text(json.dumps(data))
        if existing_environment:
            path = self.m.APP / ".venv/bin"
            path.mkdir(parents=True, exist_ok=True)
            (path / "python").write_text("#!" + sys.executable + "\nraise SystemExit(0)\n")
            (path / "python").chmod(0o755)
        entry = self.m.entry_capture(self.owner)
        self.m.prepare(self.owner, self.old, self.old, entry.name, "setup")
        journal, manifest, capsule = self.m.read_pending(self.owner)
        journal["phase"] = "MUTATING"
        self.m.write_journal(journal)
        return journal, manifest, capsule

    def setup_ready(self, **kwargs):
        journal, manifest, capsule = self.setup_transaction(**kwargs)
        for unit in self.m.CORE_TIMERS:
            if unit in self.states():
                self.states({unit: {"ActiveState": "inactive"}})
        with mock.patch.object(self.m, "qualify_environment"):
            self.m.setup_action("ready", journal, manifest, capsule)
        return journal, manifest, capsule

    def successful_smoke_effect(self):
        unit = "macro-live-fast.service"
        now = self.m.datetime.now(self.m.timezone.utc).isoformat()
        us = self.m.time.monotonic_ns() // 1000
        self.states({unit: {"ActiveState": "inactive", "MainPID": "0", "ControlPID": "0",
                           "InvocationID": "a" * 32, "Result": "success", "ExecMainStatus": "0",
                           "ExecMainCode": "1", "ExecMainStartTimestampMonotonic": str(us),
                           "ExecMainExitTimestampMonotonic": str(us + 1)}})
        status = {"schema": "vps_live_lane.v1", "lane": "fast", "ok": True, "invocation_id": "a" * 32,
                  "started_at": now, "finished_at": now,
                  "tasks": [{"name": "display_quotes", "status": "ok", "returncode": 0,
                             "published": ["live/quotes.json"],
                             "publication_sha256": {"live/quotes.json": self.m.sha(b'{"meta":{"resolved":5},"fixture":true}')}}]}
        self.m.STATE.mkdir(parents=True, exist_ok=True)
        (self.m.STATE / "status-fast.json").write_text(json.dumps(status))
        live = self.m.STATE.parent / "public/live"
        live.mkdir(parents=True, exist_ok=True)
        (live / "quotes.json").write_text('{"meta":{"resolved":5},"fixture":true}')
        return status

    def pass_setup_smoke(self, journal, manifest, capsule):
        original = self.m.run
        def run(args, **kwargs):
            if args[:2] == [self.m.SYSTEMCTL, "start"] and args[2] == "macro-live-fast.service":
                self.successful_smoke_effect()
                return ""
            return original(args, **kwargs)
        with mock.patch.object(self.m, "run", side_effect=run):
            self.m.setup_smoke(journal, manifest, capsule)

    def test_setup_captures_exact_script_units_and_preserves_existing_environment(self):
        journal, manifest, capsule = self.setup_transaction(ancillary_present=True)
        self.assertEqual(manifest["purpose"], "setup")
        self.assertEqual(manifest["old"], manifest["new"])
        self.assertEqual(manifest["setup"]["activate"], [])
        self.assertEqual(set(self.m.SETUP_MEMBERS), {x for x in manifest["members"] if x.startswith("setup/")})
        before = (self.m.APP / ".venv/bin/python").read_bytes()
        mode, path = self.m.setup_environment(manifest)
        self.assertEqual(mode, "reuse")
        self.assertEqual(path, self.m.APP / ".venv")
        with mock.patch.object(self.m, "qualify_environment") as qualified:
            self.m.publish_environment(manifest, journal)
        qualified.assert_called_once_with(path)
        self.assertEqual((path / "bin/python").read_bytes(), before)
        self.assertEqual(journal["phase"], "MUTATING")
        self.assertEqual(self.m.read_pending(self.owner)[0]["setup"]["stage"], "PACKAGES")

    def test_ordinary_updater_cannot_resume_or_retire_pending_setup(self):
        self.setup_transaction()
        for action in (["preflight", "update", ""], ["ready"], ["restore"]):
            with self.subTest(action=action), mock.patch.object(self.m, "owner_identity", return_value=self.owner):
                with self.assertRaises(self.m.Refusal):
                    self.m.main(["/proc/1/fd/255", *action])
        self.assertTrue(self.m.pending_exists())

    def test_setup_package_failure_is_nonadmitting_and_does_not_publish_environment(self):
        journal, manifest, capsule = self.setup_transaction(fresh=True, existing_environment=False)
        mode, path = self.m.setup_environment(manifest)
        self.assertEqual(mode, "prepare")
        self.assertFalse((self.m.APP / ".venv").exists())
        with mock.patch.object(self.m, "qualify_environment", side_effect=self.m.Refusal("missing dependency")):
            with self.assertRaises(self.m.Refusal):
                self.m.setup_action("ready", journal, manifest, capsule)
        self.assertFalse((self.m.APP / ".venv").exists())
        found = self.m.read_pending(self.owner)[0]
        self.assertEqual((found["phase"], found["setup"]["stage"]), ("MUTATING", "PACKAGES"))

    def test_fresh_environment_publishes_only_the_qualified_private_candidate(self):
        journal, manifest, capsule = self.setup_transaction(fresh=True, existing_environment=False)
        _, path = self.m.setup_environment(manifest)
        with mock.patch.object(self.m, "qualify_environment") as qualified:
            self.m.setup_action("bind-environment", journal, manifest, capsule)
        qualified.assert_called_once_with(path)
        self.assertTrue((self.m.APP / ".venv").is_symlink())
        self.assertEqual((self.m.APP / ".venv").resolve(), path)
        self.assertEqual(self.m.setup_environment(manifest), ("reuse", path))
        self.assertEqual(self.m.read_pending(self.owner)[0]["phase"], "MUTATING")

    def test_ready_setup_cannot_reenter_package_or_binding_mutation(self):
        journal, manifest, capsule = self.setup_ready()
        for action in ("environment", "bind-environment", "ready"):
            with self.subTest(action=action), mock.patch.object(self.m, "publish_environment") as publish:
                with self.assertRaises(self.m.Refusal):
                    self.m.setup_action(action, journal, manifest, capsule)
                publish.assert_not_called()
        self.assertEqual(self.m.read_pending(self.owner)[0]["phase"], "SOURCE_READY")

    def test_smoke_success_requires_a_new_invocation_and_fresh_producer_evidence(self):
        journal, manifest, capsule = self.setup_ready()
        self.successful_smoke_effect()
        original = self.m.run
        def no_new_run(args, **kwargs):
            if args == [self.m.SYSTEMCTL, "start", "macro-live-fast.service"]:
                return ""
            return original(args, **kwargs)
        with mock.patch.object(self.m, "run", side_effect=no_new_run):
            with self.assertRaisesRegex(self.m.Refusal, "no new guarded"):
                self.m.setup_smoke(journal, manifest, capsule)
        self.assertEqual(self.m.read_pending(self.owner)[0]["setup"]["smoke"]["phase"], "starting")

    def test_smoke_crash_after_publication_reconciles_original_invocation_without_restart(self):
        journal, manifest, capsule = self.setup_ready()
        original = self.m.write_journal
        def crash_after_publication(value):
            if value["setup"]["stage"] == "SMOKED":
                raise OSError("fixture crash before completed smoke receipt")
            original(value)
        with mock.patch.object(self.m, "write_journal", side_effect=crash_after_publication):
            with self.assertRaises(OSError):
                self.pass_setup_smoke(journal, manifest, capsule)
        journal, manifest, capsule = self.m.read_pending(self.owner)
        self.assertEqual(journal["setup"]["smoke"]["phase"], "starting")
        original_run = self.m.run
        def no_replay(args, **kwargs):
            if args[:2] == [self.m.SYSTEMCTL, "start"]:
                raise AssertionError("original smoke must not replay")
            return original_run(args, **kwargs)
        with mock.patch.object(self.m, "run", side_effect=no_replay):
            self.m.setup_smoke(journal, manifest, capsule)
        self.assertEqual(self.m.read_pending(self.owner)[0]["setup"]["stage"], "SMOKED")

    def test_smoke_failed_start_preserves_pending_and_refuses_old_publication(self):
        journal, manifest, capsule = self.setup_ready()
        self.successful_smoke_effect()
        self.states({"macro-live-fast.service": {"fail_start": True}})
        with self.assertRaises(self.m.Refusal):
            self.m.setup_smoke(journal, manifest, capsule)
        self.assertEqual(self.m.read_pending(self.owner)[0]["setup"]["stage"], "READY")
        self.assertTrue(self.m.pending_exists())
        self.assertFalse((capsule / "smoke-status.json").exists())

    def test_setup_restoration_keeps_pending_through_ancillary_and_cron_steps(self):
        self.states({"macro-live-fast.timer": {"enabled": "disabled", "ActiveState": "active"},
                     "macro-live-snapshot.timer": {"enabled": "enabled", "ActiveState": "inactive"}})
        journal, manifest, capsule = self.setup_ready(ancillary_present=True)
        self.pass_setup_smoke(journal, manifest, capsule)
        self.m.setup_arm(journal, manifest, capsule)
        self.assertTrue(self.m.pending_exists())
        self.assertFalse((capsule / "completion.json").exists())
        self.assertEqual(self.states()["macro-live-fast.timer"]["enabled"], "disabled")
        self.assertEqual(self.states()["macro-live-fast.timer"]["ActiveState"], "active")
        self.assertEqual(self.states()["macro-live-snapshot.timer"]["ActiveState"], "inactive")
        self.assertFalse(any(a[0] == "enable" for a in self.actions()))
        self.assertEqual(self.m.read_pending(self.owner)[0]["setup"]["stage"], "ARMED")

    def fixture_cron(self, body=b"* * * * * keep-me\n* * * * * macro-live\n"):
        path = self.root / "crontab-data"
        path.write_bytes(body)
        self.m.CRONTAB = str(self.root / "crontab")
        Path(self.m.CRONTAB).write_text("#!" + sys.executable + "\nimport sys\nfrom pathlib import Path\n"
            + f"p=Path({str(path)!r});e=Path({str(self.root / 'cron-writes')!r})\n"
            + "if sys.argv[1]=='-l': sys.stdout.buffer.write(p.read_bytes())\n"
            + "else: p.write_bytes(Path(sys.argv[1]).read_bytes());e.write_text('applied')\n")
        Path(self.m.CRONTAB).chmod(0o755)
        return path

    def test_cron_retirement_preserves_unrelated_entries_and_reads_back_postimage(self):
        journal, manifest, capsule = self.setup_ready(ancillary_present=True)
        self.pass_setup_smoke(journal, manifest, capsule)
        self.m.setup_arm(journal, manifest, capsule)
        path = self.fixture_cron()
        with mock.patch.object(self.m, "qualify_environment"):
            self.m.setup_action("finish", journal, manifest, capsule)
        self.assertEqual(path.read_bytes(), b"* * * * * keep-me\n")
        self.assertFalse(self.m.pending_exists())
        self.assertTrue((capsule / "completion.json").exists())
        completed = json.loads((capsule / "completion.json").read_text())
        final = completed["journal"]
        self.assertEqual(completed["manifest_sha256"], journal["manifest_sha256"])
        self.assertEqual(final["setup"]["smoke"]["invocation"], "a" * 32)
        self.assertEqual(final["setup"]["cron"]["phase"], "applied")
        raw = (json.dumps(final, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.assertEqual(completed["journal_sha256"], hashlib.sha256(raw).hexdigest())

    def test_cron_read_failure_cannot_become_an_empty_replacement(self):
        journal, manifest, capsule = self.setup_ready(ancillary_present=True)
        self.pass_setup_smoke(journal, manifest, capsule)
        self.m.setup_arm(journal, manifest, capsule)
        path = self.fixture_cron()
        Path(self.m.CRONTAB).write_text("#!" + sys.executable + "\nimport sys\nsys.exit(2)\n")
        with self.assertRaises(self.m.Refusal):
            self.m.retire_setup_cron(journal, manifest, capsule)
        self.assertEqual(path.read_bytes(), b"* * * * * keep-me\n* * * * * macro-live\n")
        self.assertFalse((self.root / "cron-writes").exists())
        self.assertTrue(self.m.pending_exists())

    def test_cron_applied_crash_is_reconciled_and_withdrawn_postimage_is_not_replayed(self):
        journal, manifest, capsule = self.setup_ready(ancillary_present=True)
        self.pass_setup_smoke(journal, manifest, capsule)
        self.m.setup_arm(journal, manifest, capsule)
        path = self.fixture_cron()
        original = self.m.write_journal
        def crash(value):
            if value["setup"]["cron"] and value["setup"]["cron"]["phase"] == "applied":
                raise OSError("fixture crash after cron install")
            original(value)
        with mock.patch.object(self.m, "write_journal", side_effect=crash):
            with self.assertRaises(OSError):
                self.m.retire_setup_cron(journal, manifest, capsule)
        journal, manifest, capsule = self.m.read_pending(self.owner)
        self.assertEqual(journal["setup"]["cron"]["phase"], "applying")
        path.write_bytes((capsule / "cron.before").read_bytes())
        with self.assertRaises(self.m.Refusal):
            self.m.retire_setup_cron(journal, manifest, capsule)
        path.write_bytes((capsule / "cron.after").read_bytes())
        (self.root / "cron-writes").unlink()
        self.m.retire_setup_cron(journal, manifest, capsule)
        self.assertFalse((self.root / "cron-writes").exists())
        self.assertEqual(self.m.read_pending(self.owner)[0]["setup"]["stage"], "CRON_RETIRED")

    def test_post_owner_replacement_readback_exception_requires_reconciliation(self):
        candidate = (self.m.APP / "app/deploy/update.sh").read_bytes()
        original = self.m.safe_read
        def read(path, *args, **kwargs):
            if path == self.m.OWNER:
                raise PermissionError("fixture denied after installed replacement")
            return original(path, *args, **kwargs)
        with mock.patch.object(self.m, "owner_identity", return_value=self.owner), \
             mock.patch.object(self.m, "safe_read", side_effect=read):
            with self.assertRaises(self.m.EffectNeedsReadback):
                self.m.replace_owner("/proc/1/fd/255", self.old)
        self.assertEqual(self.m.OWNER.read_bytes(), candidate)



    def test_dirty_setup_source_refuses_before_environment_import(self):
        journal, manifest, capsule = self.setup_transaction()
        (self.m.APP / "engine/value.py").write_text("DIRTY = True\n")
        with mock.patch.object(self.m, "qualify_environment") as imported:
            with self.assertRaises(self.m.Refusal):
                self.m.setup_action("bind-environment", journal, manifest, capsule)
            imported.assert_not_called()

    def test_environment_binding_cannot_replace_a_competing_destination(self):
        journal, manifest, capsule = self.setup_transaction(fresh=True, existing_environment=False)
        _, candidate = self.m.setup_environment(manifest)
        foreign = self.root / "foreign-environment"
        foreign.mkdir()
        original = os.symlink
        def race(source, target, *args, **kwargs):
            if Path(target) == self.m.APP / ".venv":
                original(str(foreign), target)
            return original(source, target, *args, **kwargs)
        with mock.patch.object(self.m, "qualify_environment"), mock.patch.object(self.m.os, "symlink", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.m.publish_environment(manifest, journal)
        self.assertEqual((self.m.APP / ".venv").resolve(), foreign)
        self.assertTrue(candidate.is_dir())

    def test_candidate_filesystem_durability_precedes_environment_binding(self):
        journal, manifest, capsule = self.setup_transaction(fresh=True, existing_environment=False)
        _, candidate = self.m.setup_environment(manifest)
        original = self.m.run
        def fail_candidate_sync(args, **kwargs):
            if args == [self.m.SYNC, "-f", str(candidate)]:
                raise self.m.Refusal("fixture candidate filesystem failed")
            return original(args, **kwargs)
        with mock.patch.object(self.m, "qualify_environment"), mock.patch.object(self.m, "run", side_effect=fail_candidate_sync):
            with self.assertRaises(self.m.Refusal):
                self.m.publish_environment(manifest, journal)
        self.assertFalse((self.m.APP / ".venv").is_symlink())

    def test_new_successful_invocation_cannot_claim_another_owners_publication(self):
        journal, manifest, capsule = self.setup_ready()
        original = self.m.run
        def run(args, **kwargs):
            if args == [self.m.SYSTEMCTL, "start", "macro-live-fast.service"]:
                row = self.successful_smoke_effect()
                row["invocation_id"] = "b" * 32
                (self.m.STATE / "status-fast.json").write_text(json.dumps(row))
                return ""
            return original(args, **kwargs)
        with mock.patch.object(self.m, "run", side_effect=run):
            with self.assertRaisesRegex(self.m.Refusal, "not bound"):
                self.m.setup_smoke(journal, manifest, capsule)
        self.assertEqual(self.m.read_pending(self.owner)[0]["setup"]["smoke"]["phase"], "starting")

    def test_smoke_requires_the_exact_bytes_published_by_its_invocation(self):
        journal, manifest, capsule = self.setup_ready()
        original = self.m.run
        def run(args, **kwargs):
            if args == [self.m.SYSTEMCTL, "start", "macro-live-fast.service"]:
                self.successful_smoke_effect()
                (self.m.STATE.parent / "public/live/quotes.json").write_text('{"other_writer":true}')
                return ""
            return original(args, **kwargs)
        with mock.patch.object(self.m, "run", side_effect=run):
            with self.assertRaisesRegex(self.m.Refusal, "quote bytes do not match"):
                self.m.setup_smoke(journal, manifest, capsule)
        self.assertFalse((capsule / "smoke-status.json").exists())

    def installed_fresh_fixture(self):
        data = self.states()
        for unit in self.m.UNITS + self.m.ANCILLARY_UNITS:
            target = self.m.UNIT_DIR / unit
            target.write_bytes((DEPLOY / unit).read_bytes())
            target.chmod(0o644)
            data[unit] = {"LoadState": "loaded", "ActiveState": "inactive", "MainPID": "0", "ControlPID": "0",
                          "ControlGroup": "", "FragmentPath": str(target), "DropInPaths": "", "NeedDaemonReload": "no",
                          "enabled": "disabled" if unit.endswith(".timer") else "static"}
        self.state.write_text(json.dumps(data))

    def test_fresh_activation_reconciles_boot_start_and_rechecks_enablement_durability(self):
        journal, manifest, capsule = self.setup_ready(fresh=True)
        self.installed_fresh_fixture()
        self.pass_setup_smoke(journal, manifest, capsule)
        unit = self.m.CORE_TIMERS[0]
        journal["setup"]["activation"][unit]["enable"] = "starting"
        self.m.write_journal(journal)
        self.states({unit: {"enabled": "enabled", "ActiveState": "active"}})
        self.m.BOOT_ID.write_text("22222222-2222-2222-2222-222222222222")
        original = self.m.run
        seen = []
        def run(args, **kwargs):
            seen.append(args)
            if args[:2] == [self.m.SYSTEMCTL, "enable"]:
                self.states({args[2]: {"enabled": "enabled"}})
                return ""
            return original(args, **kwargs)
        with mock.patch.object(self.m, "run", side_effect=run):
            self.m.setup_arm(journal, manifest, capsule)
        self.assertNotIn([self.m.SYSTEMCTL, "enable", unit], seen)
        self.assertNotIn([self.m.SYSTEMCTL, "start", unit], seen)
        self.assertIn([self.m.SYNC, "-f", str(self.m.UNIT_DIR)], seen)
        self.assertEqual(self.m.read_pending(self.owner)[0]["setup"]["stage"], "ARMED")

    def test_fresh_partial_enable_start_failure_remains_explicit_and_is_not_replayed(self):
        journal, manifest, capsule = self.setup_ready(fresh=True)
        self.installed_fresh_fixture()
        self.pass_setup_smoke(journal, manifest, capsule)
        unit = self.m.CORE_TIMERS[0]
        self.states({unit: {"fail_start": True}})
        original = self.m.run
        def run(args, **kwargs):
            if args[:2] == [self.m.SYSTEMCTL, "enable"]:
                self.states({args[2]: {"enabled": "enabled"}})
                return ""
            return original(args, **kwargs)
        with mock.patch.object(self.m, "run", side_effect=run):
            with self.assertRaises(self.m.Refusal):
                self.m.setup_arm(journal, manifest, capsule)
        journal, manifest, capsule = self.m.read_pending(self.owner)
        self.assertEqual(journal["setup"]["activation"][unit], {"enable": "done", "start": "starting"})
        before = len(self.actions())
        with self.assertRaises(self.m.Refusal):
            self.m.setup_arm(journal, manifest, capsule)
        self.assertFalse(any(a[0] == "start" for a in self.actions()[before:]))
        self.assertTrue(self.m.pending_exists())

    def test_advanced_setup_stage_cannot_hide_incomplete_effects(self):
        journal, manifest, capsule = self.setup_ready()
        journal["setup"]["stage"] = "ARMED"
        self.m.write_journal(journal)
        with self.assertRaises(self.m.Refusal):
            self.m.read_pending(self.owner)
        journal["setup"]["stage"] = "PACKAGES"
        self.m.write_journal(journal)
        with self.assertRaises(self.m.Refusal):
            self.m.read_pending(self.owner)

    def test_ready_setup_script_skips_all_package_and_unit_mutation(self):
        root = self.root / "script-runtime"
        attempt = "c" * 32
        directory = root / "state/source-update-capsules" / attempt / "setup"
        directory.mkdir(parents=True)
        state = self.root / "script-stage"
        state.write_text("READY")
        events = self.root / "script-actions"
        controller = self.root / "setup-controller"
        controller.write_text("#!" + sys.executable + "\nimport sys\nfrom pathlib import Path\n"
            + f"p=Path({str(state)!r});e=Path({str(events)!r});a=sys.argv[-1]\n"
            + "with e.open('a') as f:f.write(a+'\\n')\n"
            + "if a=='inspect': print(p.read_text())\n"
            + "elif a in ('smoke','arm','finish'): p.write_text({'smoke':'SMOKED','arm':'ARMED','finish':'COMPLETE'}[a])\n"
            + "else: raise SystemExit('ready recovery attempted mutation: '+a)\n")
        controller.chmod(0o755)
        script = (DEPLOY / "live-setup.sh").read_text().replace(
            'BASE_DIR="/var/lib/macro-live"', 'BASE_DIR=' + repr(str(root))).replace(
            "/usr/local/bin/macro-update", str(controller))
        script = script.replace('if [ "$(id -u)" -ne 0 ]; then', 'if [ 0 -ne 0 ]; then')
        target = directory / "live-setup.sh"
        target.write_text(script)
        result = subprocess.run([self.m.BASH, str(target), "--source-attempt", attempt],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events.read_text().splitlines(), ["inspect", "smoke", "inspect", "arm", "inspect", "finish"])
        self.assertEqual(state.read_text(), "COMPLETE")



if __name__ == "__main__":
    unittest.main(verbosity=2)
