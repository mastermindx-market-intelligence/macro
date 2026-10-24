"""Fail-closed evidence for destructive metabolism worktree GC.

These tests never remove a real worktree and do not need network or GitHub.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import metabolism_gc as gc_mod  # noqa: E402


class GCFailClosedTests(unittest.TestCase):
    def test_revparse_error_with_plausible_stdout_is_protected(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            fake = subprocess.CompletedProcess(["git"], 128, str(root), "permission denied")
            with patch.object(gc_mod.subprocess, "run", return_value=fake):
                self.assertTrue(gc_mod._is_live_main_checkout(root))

    def test_revparse_unknown_empty_stdout_protected(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            fake = subprocess.CompletedProcess(["git"], 0, "", "")
            with patch.object(gc_mod.subprocess, "run", return_value=fake):
                self.assertTrue(gc_mod._is_live_main_checkout(root))

    def test_lsof_rc2_permission_error_means_occupied(self):
        with TemporaryDirectory() as t:
            fake = subprocess.CompletedProcess(["lsof"], 2, "", "permission denied")
            with patch.object(gc_mod.subprocess, "run", return_value=fake):
                self.assertTrue(gc_mod._has_open_files(Path(t)))

    def test_lsof_rc1_with_diagnostics_means_occupied(self):
        with TemporaryDirectory() as t:
            fake = subprocess.CompletedProcess(["lsof"], 1, "", "partial failure")
            with patch.object(gc_mod.subprocess, "run", return_value=fake):
                self.assertTrue(gc_mod._has_open_files(Path(t)))

    def test_lsof_rc1_clean_empty_is_only_safe_negative(self):
        with TemporaryDirectory() as t:
            fake = subprocess.CompletedProcess(["lsof"], 1, "", "")
            with patch.object(gc_mod.subprocess, "run", return_value=fake):
                self.assertFalse(gc_mod._has_open_files(Path(t)))

    def test_gc_non_dry_run_never_calls_remove_without_proof(self):
        with TemporaryDirectory() as t:
            repo = Path(t) / "owner"
            path = Path(t) / "wf_candidate"
            repo.mkdir()
            path.mkdir()
            candidate = {"path": path, "branch": "wf_candidate", "locked": False}
            with patch.object(gc_mod, "_list_worktrees", return_value=[candidate]), \
                 patch.object(gc_mod, "_is_live_main_checkout", return_value=False), \
                 patch.object(gc_mod, "_has_open_files", return_value=False), \
                 patch.object(gc_mod, "_branch_merged_into_main", return_value=True), \
                 patch.object(gc_mod, "_journal_is_terminal", return_value=True), \
                 patch.object(gc_mod, "_ready_for_delete", return_value=False), \
                 patch.object(gc_mod.subprocess, "run") as shell:
                result = gc_mod.gc(repo, dry_run=False)
            self.assertEqual(result["reaped"], [])
            self.assertEqual(result["skipped_safety"], [str(path)])
            shell.assert_not_called()

    def test_gc_dry_run_is_only_a_candidate_not_deletion(self):
        with TemporaryDirectory() as t:
            repo = Path(t) / "owner"
            path = Path(t) / "wf_candidate"
            repo.mkdir()
            path.mkdir()
            candidate = {"path": path, "branch": "wf_candidate", "locked": False}
            with patch.object(gc_mod, "_list_worktrees", return_value=[candidate]), \
                 patch.object(gc_mod, "_is_live_main_checkout", return_value=False), \
                 patch.object(gc_mod, "_has_open_files", return_value=False), \
                 patch.object(gc_mod, "_branch_merged_into_main", return_value=True), \
                 patch.object(gc_mod, "_ready_for_delete") as admitted, \
                 patch.object(gc_mod.subprocess, "run") as shell:
                result = gc_mod.gc(repo, dry_run=True)
            self.assertEqual(result["reaped"], [str(path)])
            shell.assert_not_called()
            admitted.assert_not_called()

    def test_locked_worktree_hard_denied(self):
        with TemporaryDirectory() as t:
            repo = Path(t) / "owner"
            path = Path(t) / "wf_candidate"
            repo.mkdir()
            path.mkdir()
            self.assertFalse(gc_mod._ready_for_delete(repo, path, "wf_candidate", locked=True))

    def test_unproven_worktree_hard_denied(self):
        with TemporaryDirectory() as t:
            repo = Path(t) / "owner"
            path = Path(t) / "wf_candidate"
            repo.mkdir()
            path.mkdir()
            self.assertFalse(gc_mod._ready_for_delete(repo, path, "wf_candidate"))

    def test_main_never_implicitly_deletes_remote_propose_branches(self):
        """Even a non-dry-run local GC must not authorize remote pruning."""
        with TemporaryDirectory() as t:
            root = Path(t)
            with patch.object(gc_mod, "reap_propose_branches",
                              return_value={"deleted": [], "skipped": [], "errors": []}) as remote, \
                 patch.object(gc_mod, "compact_insight_bus",
                              return_value={"retained": 0, "archived": 0, "errors": []}), \
                 patch.object(gc_mod, "gc", return_value={
                     "inspected": 0, "reaped": [], "skipped_alive": [],
                     "skipped_safety": [], "errors": []}):
                self.assertEqual(gc_mod.main(["--root", str(root)]), 0)
                remote.assert_called_once_with(root, dry_run=True)

    def test_no_force_flag_in_deletion_command(self):
        source = inspect.getsource(gc_mod.gc)
        self.assertNotIn('"remove", "--force"', source)
        self.assertIn('"worktree", "remove", str(wt_path)', source)


if __name__ == "__main__":
    unittest.main()
