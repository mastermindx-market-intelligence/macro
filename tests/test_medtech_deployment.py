"""Isolated deployment refusal proofs; never inspect or mutate production roots."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import importlib.util
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import mock_open, patch

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prereqs = _load("medtech_deployment_prereqs", "app/deploy/medtech-prereqs.py")
boundary = _load("medtech_deployment_boundary", "app/deploy/medtech-api-boundary.py")


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.parent.chmod(0o700)
        self.fd = os.open(self.parent, prereqs.OPEN_DIRECTORY)
        self.addCleanup(os.close, self.fd)
        self.uid, self.gid = os.getuid(), os.getgid()
        anchor = os.fstat(self.fd)
        self.anchor_uid, self.anchor_gid = anchor.st_uid, anchor.st_gid

    def provision(self):
        prereqs._provision_at(self.fd, self.uid, self.gid,
                              anchor_uid=self.anchor_uid, anchor_gid=self.anchor_gid)

    def test_idempotent_anchors_preserve_existing_evidence(self):
        self.provision()
        root = self.parent / "medtech"
        retained = root / "private" / "retained-source"
        retained.write_bytes(b"unchanged original source")
        inode = retained.stat().st_ino
        self.provision()
        self.assertEqual(retained.read_bytes(), b"unchanged original source")
        self.assertEqual(retained.stat().st_ino, inode)
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o711)
        for name in ("private", "public"):
            self.assertEqual(stat.S_IMODE((root / name).stat().st_mode), 0o700)
        self.assertEqual(list((root / "public").iterdir()), [])

    def test_unsafe_existing_sibling_refused_before_creating_private(self):
        root = self.parent / "medtech"
        root.mkdir(mode=0o711)
        root.chmod(0o711)
        public = root / "public"
        public.mkdir(mode=0o755)
        public.chmod(0o755)
        with self.assertRaises(prereqs.PrerequisiteError):
            self.provision()
        self.assertFalse((root / "private").exists())
        self.assertEqual(stat.S_IMODE(public.stat().st_mode), 0o755)

    def test_symlink_and_regular_file_are_never_adopted(self):
        root = self.parent / "medtech"
        outside = self.parent / "outside"
        outside.mkdir()
        root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            self.provision()
        self.assertEqual(list(outside.iterdir()), [])
        root.unlink()
        root.write_bytes(b"not a directory")
        with self.assertRaises(OSError):
            self.provision()
        self.assertEqual(root.read_bytes(), b"not a directory")

    def test_wrong_owner_is_refused_without_repair(self):
        root = self.parent / "medtech"
        root.mkdir(mode=0o711)
        root.chmod(0o711)
        original = os.fstat
        root_inode = root.stat().st_ino

        def wrong_owner(descriptor):
            result = original(descriptor)
            if result.st_ino == root_inode:
                fields = list(result)
                fields[4] = self.uid + 1
                return os.stat_result(fields)
            return result

        with patch.object(prereqs.os, "fstat", side_effect=wrong_owner):
            with self.assertRaises(prereqs.PrerequisiteError):
                self.provision()
        self.assertEqual(list(root.iterdir()), [])

    def test_worker_identity_cannot_be_root_or_share_supplementary_groups(self):
        account = SimpleNamespace(pw_name="macro-medtech", pw_uid=123, pw_gid=124,
                                  pw_dir="/nonexistent", pw_shell="/usr/sbin/nologin")
        group = SimpleNamespace(gr_gid=124, gr_mem=[])
        with ExitStack() as stack:
            stack.enter_context(patch.object(prereqs.pwd, "getpwnam", return_value=account))
            stack.enter_context(patch.object(prereqs.grp, "getgrnam", return_value=group))
            stack.enter_context(patch.object(prereqs.pwd, "getpwall", return_value=[account]))
            groups = stack.enter_context(patch.object(prereqs.os, "getgrouplist", return_value=[124]))
            self.assertEqual(prereqs._identity(), (123, 124))
            groups.return_value = [124, 0]
            with self.assertRaises(prereqs.PrerequisiteError):
                prereqs._identity()
            groups.return_value = [124]
            account.pw_uid = 0
            with self.assertRaises(prereqs.PrerequisiteError):
                prereqs._identity()


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        for name in ("private", "public", "mask"):
            (root / name).mkdir(mode=0o700)
        (root / "mask").chmod(0)
        self.addCleanup((root / "mask").chmod, 0o700)
        self.private = (root / "private").stat()
        self.public = (root / "public").stat()
        self.mask = (root / "mask").stat()
        self.mountinfo = (
            "101 1 0:1 / /srv/medtech/public ro,nosuid - ext4 /dev/test rw\n"
            "102 1 0:2 /inaccessible/dir /srv/medtech/private ro,nosuid - tmpfs tmpfs rw\n"
        )
        self.state = {
            "LoadState": "loaded", "ActiveState": "active", "SubState": "running",
            "MainPID": "2345", "FragmentPath": str(boundary.INSTALLED_UNIT),
            "DropInPaths": "", "NeedDaemonReload": "no", "Transient": "no",
            "InvocationID": "a" * 32,
        }

    def validate(self, mountinfo=None, api_public=None, api_private=None):
        boundary._validate_namespace(
            self.mountinfo if mountinfo is None else mountinfo, self.public, self.private,
            self.public if api_public is None else api_public,
            self.mask if api_private is None else api_private,
        )

    def test_actual_inode_and_mount_evidence_accepts_fenced_api(self):
        self.validate()

    def test_missing_writable_or_unfenced_namespace_is_refused(self):
        cases = (
            (self.mountinfo.splitlines()[1], None, None),
            (self.mountinfo.splitlines()[0], None, None),
            (self.mountinfo.replace("/public ro,", "/public rw,"), None, None),
            (self.mountinfo, self.mask, None),
            (self.mountinfo, None, self.private),
            (self.mountinfo + "103 1 0:3 / /srv/medtech/public/nested rw - ext4 /dev/test rw\n", None, None),
            (self.mountinfo + "103 1 0:3 / /srv/medtech/private/nested ro - ext4 /dev/test rw\n", None, None),
            (self.mountinfo + self.mountinfo.splitlines()[0] + "\n", None, None),
        )
        for mounts, public, private in cases:
            with self.subTest(mounts=mounts, public=public, private=private):
                with self.assertRaises(boundary.BoundaryError):
                    self.validate(mounts, public, private)

    def test_unrelated_binfmt_mount_stack_does_not_block_refresh(self):
        unrelated = (
            "200 1 0:4 / /proc/sys/fs/binfmt_misc ro - autofs systemd rw\n"
            "201 1 0:5 / /proc/sys/fs/binfmt_misc rw - binfmt_misc binfmt_misc rw\n"
        )
        self.validate(self.mountinfo + unrelated)

    def test_unit_state_requires_exact_fragment_no_dropins_and_running_pid(self):
        self.assertEqual(boundary._validate_unit_state(self.state), 2345)
        for key, value in (("MainPID", "0"), ("ActiveState", "inactive"),
                           ("FragmentPath", "/run/systemd/system/macro-api.service"),
                           ("DropInPaths", "/etc/systemd/system/macro-api.service.d/local.conf"),
                           ("NeedDaemonReload", "yes"), ("InvocationID", "")):
            with self.subTest(key=key):
                with self.assertRaises(boundary.BoundaryError):
                    boundary._validate_unit_state({**self.state, key: value})

    def _attestation_fixtures(self, stack, *, changed_pid=False, changed_start=False):
        source = ("\n".join(boundary.REQUIRED_LINES) + "\n").encode()
        stack.enter_context(patch.object(boundary, "_read_safe_file", side_effect=lambda path, **kw:
                           b"MEDTECH_START_ON=2026-01-01\n" if path == boundary.ENVIRONMENT_FILE else source))
        after = {**self.state, "MainPID": "2346"} if changed_pid else self.state.copy()
        stack.enter_context(patch.object(boundary, "_unit_state", side_effect=[self.state, after]))
        stack.enter_context(patch.object(boundary, "_process_stamp", side_effect=[
            ("100", 4, 5), ("101" if changed_start else "100", 4, 5)]))
        stack.enter_context(patch.object(boundary, "_check_api_environment"))
        stack.enter_context(patch.object(boundary, "_host_directory", side_effect=lambda path:
                           self.public if path == boundary.PUBLIC_ROOT else self.private))
        stack.enter_context(patch.object(Path, "read_text", return_value=self.mountinfo))
        stack.enter_context(patch.object(boundary.os, "stat", side_effect=lambda path, **kw:
                           self.public if str(path).endswith("/public") else self.mask))

    def test_attestation_rejects_pid_change_and_pid_reuse_during_proof(self):
        with ExitStack() as stack:
            self._attestation_fixtures(stack)
            boundary.attest()
        for kwargs in ({"changed_pid": True}, {"changed_start": True}):
            with self.subTest(kwargs=kwargs), ExitStack() as stack:
                self._attestation_fixtures(stack, **kwargs)
                with self.assertRaises(boundary.BoundaryError):
                    boundary.attest()

    def test_environment_has_one_coverage_date_and_no_credentials_or_overrides(self):
        boundary._validate_environment(b"# Current-year references\nMEDTECH_START_ON=2026-01-01\n")
        for content in (b"", b"MEDTECH_START_ON=2026-02-30", b"MEDTECH_START_ON=9999-01-01",
                        b"MEDTECH_START_ON=2026-01-01\nAPI_KEY=secret",
                        b"MEDTECH_START_ON=2026-01-01\nPYTHONPATH=/tmp"):
            with self.subTest(content=content):
                with self.assertRaises((boundary.BoundaryError, ValueError)):
                    boundary._validate_environment(content)


    def test_running_api_publication_environment_must_match_the_fenced_root(self):
        expected = b"MEDTECH_PUBLIC_ROOT=/srv/medtech/public\0"
        with patch.object(Path, "open", mock_open(read_data=b"UNRELATED=value\0" + expected)) as opened:
            boundary._check_api_environment(2345)
            opened().read.assert_called_once_with(1048577)
        for content in (b"UNRELATED=value\0", b"MEDTECH_PUBLIC_ROOT=/tmp/unfenced\0",
                        expected + expected, b"X" * 1048577):
            with self.subTest(length=len(content)), patch.object(Path, "open", mock_open(read_data=content)):
                with self.assertRaises(boundary.BoundaryError):
                    boundary._check_api_environment(2345)


class WorkerSchedulingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = _load("medtech_deployment_worker", "scripts/medtech_worker.py")

    def test_low_space_on_either_filesystem_records_failure_before_acquisition(self):
        from tests.test_medtech import snapshot

        worker = self.worker
        for low_index in (0, 1):
            with self.subTest(low_index=low_index), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                private, public = root / "private", root / "public"
                private.mkdir()
                public.mkdir()
                payload = snapshot(root)
                generation = worker.publish_snapshot(public, payload)
                self.assertEqual(worker.read_snapshot(public), (payload, generation))
                state_db = private / "events.sqlite3"
                before = state_db.read_bytes()
                usage = [SimpleNamespace(free=8192), SimpleNamespace(free=8192)]
                usage[low_index] = SimpleNamespace(free=1023)
                with ExitStack() as stack:
                    disk = stack.enter_context(patch.object(worker.shutil, "disk_usage", side_effect=usage))
                    acquire = stack.enter_context(patch.object(worker, "fetch_batch"))
                    publish = stack.enter_context(patch.object(worker, "publish_snapshot"))
                    store = stack.enter_context(patch.object(worker, "EventStore"))
                    attempt = stack.enter_context(patch.object(worker, "record_attempt", wraps=worker.record_attempt))
                    with self.assertRaisesRegex(worker.MedTechError, "STORAGE_HEADROOM_LOW"):
                        worker.run(state_db=state_db, public_root=public,
                                   datasets=["510k", "pma"], start="2026-01-01", end="2026-01-01",
                                   min_free_bytes=1024)
                    acquire.assert_not_called()
                    publish.assert_not_called()
                    store.assert_not_called()
                    attempt.assert_called_once()
                    self.assertEqual(attempt.call_args.kwargs["status"], "failed")
                    self.assertEqual(attempt.call_args.kwargs["code"], "STORAGE_HEADROOM_LOW")
                    self.assertEqual(disk.call_args_list[0].args, (private,))
                    if low_index == 1:
                        self.assertEqual(disk.call_args_list[1].args, (public,))
                self.assertEqual(worker.read_snapshot(public), (payload, generation))
                self.assertEqual(state_db.read_bytes(), before)

    def test_free_space_floor_is_bounded_and_checks_new_roots_without_creating_them(self):
        worker = self.worker
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for value in (-1, True, 1.5, worker.MAX_FREE_BYTES + 1):
                with self.subTest(value=value), self.assertRaisesRegex(worker.MedTechError, "INVALID_FREE_SPACE_FLOOR"):
                    worker._check_storage_headroom(root / "private/state.db", root / "public", value)
            with patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=4096)) as disk:
                worker._check_storage_headroom(root / "private/state.db", root / "public", 4096)
                self.assertEqual([call.args for call in disk.call_args_list], [(root,), (root,)])
            self.assertEqual(list(root.iterdir()), [])

    def test_through_today_uses_utc_and_preserves_explicit_end(self):
        worker = self.worker
        base = ["medtech_worker.py", "--state-db", "/fixture/private/state.db", "--public-root",
                "/fixture/public", "--start", "2026-01-01"]
        now = datetime(2026, 10, 20, 0, 0, 1, tzinfo=timezone.utc)
        for extra, expected in ((["--through-today"], "2026-10-20"),
                                (["--end", "2026-05-01"], "2026-05-01")):
            with patch.object(sys, "argv", base + extra), patch.object(worker, "datetime") as clock:
                clock.now.return_value = now
                with patch.object(worker, "run", return_value={"state": "published"}) as run:
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(worker.main(), 0)
                    self.assertEqual(run.call_args.kwargs["end"], expected)
                    if extra == ["--through-today"]:
                        clock.now.assert_called_once_with(timezone.utc)
        for extra in ([], ["--end", "2026-05-01", "--through-today"],
                      ["--through-today", "--min-free-bytes", "-1"]):
            with patch.object(sys, "argv", base + extra), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    worker.main()
                self.assertEqual(caught.exception.code, 2)


class DeploymentWiringTests(unittest.TestCase):
    def test_api_guards_are_mandatory_and_roots_are_provisioned_before_review(self):
        api = (ROOT / "app/deploy/macro-api.service").read_text()
        # A predecessor updater must be able to start the new mandatory mounts.
        self.assertEqual(api.splitlines().count(
            "ExecStartPre=+/usr/bin/python3 -I /opt/macro/app/deploy/medtech-prereqs.py"), 1)
        self.assertNotIn("ExecStart=+", api)
        for line in boundary.REQUIRED_LINES:
            self.assertIn(line, api.splitlines())
        for name, review in (("update.sh", "if ! mm_reviewed_unit_file_ready"),
                             ("api-setup.sh", "REVIEWED_UNIT_NAMES=(")):
            source = (ROOT / "app/deploy" / name).read_text()
            marker = source.index("# BEGIN MEDTECH_PRIVATE_ROOTS")
            self.assertLess(marker, source.index(review, marker))
            block = source[marker:source.index("# END MEDTECH_PRIVATE_ROOTS", marker)]
            self.assertIn("medtech-prereqs.py", block)
            self.assertNotIn("systemctl", block)

    def test_worker_is_bounded_and_installer_stays_dark(self):
        unit = (ROOT / "app/deploy/macro-medtech.service").read_text().splitlines()
        for line in ("User=macro-medtech", "Group=macro-medtech", "CapabilityBoundingSet=",
                     "AmbientCapabilities=", "EnvironmentFile=/etc/macro-medtech.env",
                     "ExecStartPre=+/usr/bin/python3 -I /opt/macro/app/deploy/medtech-api-boundary.py",
                     "ProtectSystem=strict", "NoNewPrivileges=true", "Restart=no"):
            self.assertIn(line, unit)
        command = next(line for line in unit if line.startswith("ExecStart="))
        self.assertIn("--through-today --max-records 10000 --min-free-bytes 5368709120", command)
        self.assertNotIn("EnvironmentFile=/etc/macro-api.env", unit)
        installer = (ROOT / "app/deploy/medtech-setup.sh").read_text()
        commands = "\n".join(line for line in installer.splitlines() if not line.lstrip().startswith("#"))
        self.assertNotRegex(commands, r"systemctl\s+(?:enable|start|restart)")


if __name__ == "__main__":
    unittest.main()
