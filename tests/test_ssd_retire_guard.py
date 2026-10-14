#!/usr/bin/env python3
"""Hermetic regression suite for existing SSD reaper guard (no real deletion)."""
import contextlib
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve()
REPO = HERE.parents[1] if (HERE.parents[1] / "scripts/worktree_gc.py").is_file() else None
if REPO is not None:
    sys.path.insert(0, str(REPO / "scripts/storage_cleanup"))
import ssd_retire_guard as guard


def git(*args):
    p = subprocess.run(("git",) + args, text=True, capture_output=True, timeout=35)
    if p.returncode != 0:
        raise AssertionError("git " + " ".join(args) + " " + p.stderr)
    return p.stdout.strip()


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mmx-gc-hermetic-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.primary = self.root / "repo"
        git("init", "-b", "main", str(self.primary))
        git("-C", str(self.primary), "config", "user.name", "Safety Test")
        git("-C", str(self.primary), "config", "user.email", "safety@example.invalid")
        (self.primary / "README.md").write_text("baseline\n")
        git("-C", str(self.primary), "add", "README.md")
        git("-C", str(self.primary), "commit", "-m", "baseline")
        git("-C", str(self.primary), "update-ref", "refs/remotes/origin/main", "HEAD")
        self.member = {"root": str(self.root / "pool")}
        self.worktree = self.root / "pool/claude/test/one"
        self.worktree.parent.mkdir(parents=True)
        git("-C", str(self.primary), "worktree", "add", "-b",
            "claude/ssd-test-one", "--lock", "--reason", guard.HELPER_LOCK,
            str(self.worktree), "HEAD")
        self.head = git("-C", str(self.worktree), "rev-parse", "HEAD")
        release = self.root / "fake-gc-release"
        release.mkdir()
        origin = REPO if REPO is not None else guard.GC_RELEASE
        source = {name: ((origin / ("scripts/" + name if name.endswith(".py") else "config/" + name))
                         if REPO is not None else origin / name)
                  for name in ("worktree_gc.py", "worktree_gc.json")}
        digests = {}
        for name, original in source.items():
            shutil.copyfile(str(original), str(release / name))
            digests[name] = {"sha256": hashlib.sha256((release / name).read_bytes()).hexdigest()}
        (release / "manifest.json").write_text(json.dumps({"source_repo": "mastermindx-market-intelligence/macro",
             "source_commit": guard.PINNED_COMMIT, "files": digests}))
        release_patch = patch.object(guard, "GC_RELEASE", release)
        release_patch.start()
        self.addCleanup(release_patch.stop)
        self.gc, self.cfg = guard.load_pinned_gc()
        self.cfg = dict(self.cfg)
        # A hermetic fixture simulates a 3+-day-old landed tree with known origin.
        self.cfg["min_age_days"] = 3
        self.real_activity = self.gc.activity_age_days
        self.gc.activity_age_days = lambda *a: (16.0, {"reflog_entry": 16.0})
        self.addCleanup(setattr, self.gc, "activity_age_days", self.real_activity)
        self.audit = self.root / "audit.jsonl"
        patcher = patch.object(guard, "AUDIT", self.audit)
        patcher.start()
        self.addCleanup(patcher.stop)

    def candidate(self):
        w = self.gc.Worktree(path=self.worktree, head=self.head,
                             branch="claude/ssd-test-one")
        self.gc.classify(w, self.primary, self.cfg, {}, {}, True,
                         self.root, __import__("time").time(), protected=[])
        return w

    def remove(self, w=None, **kw):
        return guard.remove_candidate(
            gc=self.gc, primary=self.primary, w=w or self.candidate(),
            cfg=self.cfg, procs={}, pr_states=kw.get("pr_states", {}),
            fetch_ok=kw.get("fetch_ok", True),
            protected=kw.get("protected", []),
            check_volume=kw.get("check_volume", lambda *_a, **_k: True),
            member=self.member)

    def test_bundle_signature_and_protection(self):
        self.assertTrue(guard.REQUIRED_HUMAN_ROOTS.issubset(
            set(self.cfg["human_driven_roots"])))
        self.assertGreaterEqual(self.cfg["min_age_days"], 3)

    def test_verified_landed_tree_removed_nonforce_branch_survives(self):
        w = self.candidate()
        self.assertEqual(w.verdict, "SAFE_MERGED")
        out = self.remove(w)
        self.assertEqual(out.get("remove_rc"), 0, out)
        self.assertFalse(self.worktree.exists())
        self.assertEqual(git("-C", str(self.primary), "rev-parse",
                             "refs/heads/claude/ssd-test-one"), self.head)
        self.assertEqual(guard.unresolved_effects(), [])

    def test_dirty_file_never_deleted(self):
        w = self.candidate()
        (self.worktree / "README.md").write_text("unique\n")
        out = self.remove(w)
        self.assertIn("dirty", out.get("skipped", ""))
        self.assertTrue(self.worktree.exists())

    def test_untracked_file_never_deleted(self):
        w = self.candidate()
        (self.worktree / "private-data.txt").write_text("unique")
        out = self.remove(w)
        self.assertIn("untracked", out.get("skipped", ""))
        self.assertTrue(self.worktree.exists())

    def test_ignored_cache_never_forced(self):
        w = self.candidate()
        with (self.worktree / ".gitignore").open("w") as f:
            f.write(".pytest_cache/\n")
        # .gitignore itself is untracked; commit it while preserving the tip proof.
        git("-C", str(self.worktree), "add", ".gitignore")
        git("-C", str(self.worktree), "commit", "-m", "ignore cache")
        self.head = git("-C", str(self.worktree), "rev-parse", "HEAD")
        git("-C", str(self.primary), "update-ref", "refs/remotes/origin/main", self.head)
        (self.worktree / ".pytest_cache").mkdir()
        (self.worktree / ".pytest_cache/temp.txt").write_text("cache")
        w = self.candidate()
        self.assertEqual(w.verdict, "SAFE_MERGED")
        out = self.remove(w)
        self.assertIn("ignored", out.get("skipped", ""))
        self.assertTrue(self.worktree.exists())

    def test_human_driven_denied_even_with_positive_completion(self):
        w = self.candidate()
        out = self.remove(w, protected=[self.root / "pool"])
        self.assertEqual(out.get("skipped"), "human-driven root")

    def test_operator_lock_denied(self):
        w = self.candidate()
        marker = pathlib.Path((self.worktree / ".git").read_text().split(": ",1)[1].strip())
        (marker / "locked").write_text("operator-hold")
        out = self.remove(w)
        self.assertIn("operator lock", out.get("skipped", ""))
        self.assertTrue(self.worktree.exists())

    def test_remote_unknown_fails_closed(self):
        w = self.candidate()
        self.assertIn("remote", self.remove(w, fetch_ok=False).get("skipped", ""))
        self.assertTrue(self.worktree.exists())

    def test_live_worker_fails_closed(self):
        w = self.candidate()
        with patch.object(self.gc, "proc_cwd_map", return_value={str(self.worktree): ["314:worker"]}):
            out = self.remove(w)
        self.assertIn("process using", out.get("skipped", ""))
        self.assertTrue(self.worktree.exists())

    def test_missing_volume_identity_fails_closed(self):
        w = self.candidate()
        def denied(*_a, **_k):
            raise RuntimeError("wrong UUID")
        out = self.remove(w, check_volume=denied)
        self.assertIn("SSD identity", out.get("skipped", ""))
        self.assertTrue(self.worktree.exists())

    def test_unresolved_effect_blocks_new_removal(self):
        w = self.candidate()
        guard.journal("BEGIN_REMOVE", self.worktree, "unknown")
        self.assertEqual(self.remove(w).get("skipped"), "earlier effect unresolved")
        self.assertTrue(self.worktree.exists())

    def test_corrupted_pin_fails_closed(self):
        fake = self.root / "release"
        fake.mkdir()
        (fake / "worktree_gc.py").write_text("# tampered")
        (fake / "worktree_gc.json").write_text("{}")
        (fake / "manifest.json").write_text(json.dumps({
            "source_repo": "mastermindx-market-intelligence/macro",
            "source_commit": guard.PINNED_COMMIT,
            "files": {"worktree_gc.py": {"sha256": "bad"},
                      "worktree_gc.json": {"sha256": "bad"}}}))
        with patch.object(guard, "GC_RELEASE", fake):
            with self.assertRaises(RuntimeError):
                guard.load_pinned_gc()


if __name__ == "__main__":
    unittest.main(verbosity=2)
