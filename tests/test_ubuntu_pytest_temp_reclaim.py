"""Offline safety regression tests for the existing sentinel's pytest-only helper."""
import getpass
import importlib.util
import os
from pathlib import Path
import re
import stat
import tempfile
import time
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "ubuntu_pytest_temp_reclaim.py"
spec = importlib.util.spec_from_file_location("ubuntu_pytest_temp_reclaim", SOURCE)
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)
LEAF = "garbage-11111111-2222-4333-8444-555555555555"
YOUNG = "garbage-aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class GeneratedGarbageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.username = getpass.getuser()
        self.base = self.root / ("pytest-of-" + self.username)
        self.base.mkdir(mode=0o700)
        self.old = self.base / LEAF
        self.old.mkdir(mode=0o700)
        self.old.joinpath("generated.txt").write_text("fixture only")
        old = time.time() - 72 * 3600
        os.utime(self.old, (old, old))

    def test_default_is_report_only(self):
        report = gc.reclaim(self.username, tmp_root=str(self.root))
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["deleted"], 0)
        self.assertFalse(report["applied"])
        self.assertFalse(report["source_delete_enabled"])
        self.assertTrue(self.old.exists())

    def test_fresh_and_symlink_entries_never_eligible(self):
        (self.base / YOUNG).mkdir()
        linked = self.base / "garbage-ffffeeee-dddd-4ccc-8bbb-000000000000"
        linked.symlink_to(self.old, target_is_directory=True)
        report = gc.reclaim(self.username, tmp_root=str(self.root))
        self.assertEqual(report["candidate_count"], 1)
        self.assertTrue(linked.is_symlink())

    def test_protects_regular_pytest_generations(self):
        generation = self.base / "pytest-123"
        generation.mkdir()
        (self.base / "pytest-current").symlink_to(generation, target_is_directory=True)
        report = gc.reclaim(self.username, tmp_root=str(self.root))
        self.assertEqual(report["candidate_count"], 1)
        self.assertTrue(generation.exists())

    def test_untrusted_base_refused(self):
        self.base.chmod(0o755)
        with self.assertRaisesRegex(gc.Refusal, "pytest_base_untrusted"):
            gc.reclaim(self.username, tmp_root=str(self.root))

    def test_unknown_owner_or_path_refused(self):
        with self.assertRaisesRegex(gc.Refusal, "invalid_username"):
            gc.reclaim("../../../etc", tmp_root=str(self.root))
        with self.assertRaisesRegex(gc.Refusal, "pytest_base_unavailable"):
            gc.reclaim("zzznonexistentaccount999", tmp_root=str(self.root))

    def test_bounds_fail_closed(self):
        with self.assertRaisesRegex(gc.Refusal, "invalid_reclamation_bounds"):
            gc.reclaim(self.username, min_age_hours=23, tmp_root=str(self.root))
        with self.assertRaisesRegex(gc.Refusal, "invalid_reclamation_bounds"):
            gc.reclaim(self.username, max_dirs=13, tmp_root=str(self.root))

    def test_current_process_reference_is_veto(self):
        with self.assertRaisesRegex(gc.Refusal, "live_process_reference"):
            gc._check_procs([Path(os.getcwd())])

    def test_mount_child_is_veto(self):
        with self.root.joinpath("mountinfo").open("w") as f:
            f.write("30 20 8:1 / " + str(self.old / "nested") + " rw - ext4 /dev/root rw\n")
        with self.assertRaisesRegex(gc.Refusal, "mounted_subtree_present"):
            gc._check_mounts([self.old], str(self.root / "mountinfo"))

    def test_only_known_basename_is_considered(self):
        (self.base / "garbage-custom-project").mkdir()
        (self.base / "scratch-11111111-2222-4333-8444-555555555555").mkdir()
        report = gc.reclaim(self.username, tmp_root=str(self.root))
        self.assertEqual(report["candidate_count"], 1)

    def test_untrusted_receipt_refused_before_file_creation(self):
        with self.assertRaisesRegex(gc.Refusal, "ledger_directory_untrusted"):
            gc._receipt(self.root / "log.jsonl", {"event": "test"})
        self.assertFalse((self.root / "log.jsonl").exists())

    def test_apply_not_allowed_in_arbitrary_fixture_directory(self):
        with mock.patch.object(gc.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(gc.Refusal, "requires_root_and_canonical_tmp"):
                gc.reclaim(self.username, apply=True, tmp_root=str(self.root))
        self.assertTrue(self.old.exists())


if __name__ == "__main__":
    unittest.main()
