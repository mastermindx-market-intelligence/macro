"""Regression tests for scripts/ci/ad1_execution_evidence.py.

``code_revision`` must report the *actual* Git HEAD of the repository that
contains the script, while ``GITHUB_SHA`` is retained separately as
``trigger_revision``: workflows check out or pull after the trigger, so the
executed code can differ from the triggering revision. An unresolvable
repository must emit null plus a status reason — never a silent fallback to
the trigger SHA.

Fixtures are small, real, throwaway Git repositories (no fabricated evidence):
the script is copied into each repository and executed as a subprocess, which
also proves the source root derives from the script's own location rather than
the caller's cwd. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "ci" / "ad1_execution_evidence.py"


def _fixture_git_env() -> dict[str, str]:
    """Isolated env for building fixtures; no host git config or hooks leak in."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        LC_ALL="C",
    )
    return env


def _git(repo: pathlib.Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, timeout=60, env=_fixture_git_env(),
    )
    if proc.returncode != 0:
        raise AssertionError(f"fixture git {args} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _fresh_dir(parent: pathlib.Path, name: str) -> pathlib.Path:
    path = parent / name
    path.mkdir(parents=True)
    return path


def run_evidence(script_path: pathlib.Path, cwd: pathlib.Path,
                 **env_extra: str) -> subprocess.CompletedProcess:
    """Run an evidence-script copy as a subprocess with a caller-controlled env."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True, text=True, timeout=120, cwd=str(cwd), env=env,
    )


def _record(proc: subprocess.CompletedProcess) -> dict:
    """Parse the fenced JSON evidence block out of the script's stdout."""
    out = proc.stdout
    start = out.index("```json") + len("```json")
    return json.loads(out[start:out.index("```", start)])


class ScriptRepo:
    """A real throwaway Git repository holding a copy of the evidence script."""

    def __init__(self, root: pathlib.Path, message: str = "evidence fixture") -> None:
        self.root = root
        (root / "scripts" / "ci").mkdir(parents=True)
        shutil.copyfile(SCRIPT, self.script_path)
        # A nonexistent hooks path: host core.hooksPath must not run here.
        # Test identity/signing/hooks are overridden; host configuration is not changed.
        hooks = root.parent / "disabled-hooks"
        _git(root, "init")
        _git(root, "add", ".")
        _git(root,
             "-c", f"core.hooksPath={hooks}", "-c", "commit.gpgsign=false",
             "-c", "user.name=ad1 evidence test",
             "-c", "user.email=ad1-evidence-test@example.invalid",
             "commit", "-m", message)

    @property
    def script_path(self) -> pathlib.Path:
        return self.root / "scripts" / "ci" / "ad1_execution_evidence.py"

    @property
    def head(self) -> str:
        return _git(self.root, "rev-parse", "HEAD")

    def run(self, cwd: pathlib.Path, **env_extra: str) -> subprocess.CompletedProcess:
        return run_evidence(self.script_path, cwd, **env_extra)


class Ad1SourceRevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="ad1-evidence-tests-")
        self.addCleanup(self._tmp.cleanup)
        self.base = pathlib.Path(self._tmp.name)
        self.repo = ScriptRepo(_fresh_dir(self.base, "repo"))
        self.unrelated = _fresh_dir(self.base, "unrelated-cwd")

    def run_script(self, cwd: pathlib.Path | None = None,
                   **env_extra: str) -> subprocess.CompletedProcess:
        extra = {"GITHUB_RUN_ID": "424242", "GITHUB_RUN_ATTEMPT": "1", **env_extra}
        return self.repo.run(cwd or self.unrelated, **extra)

    # -- the defect: trigger revision vs actually executed source -----------

    def test_code_revision_reports_actual_head_not_trigger(self):
        decoy = ScriptRepo(_fresh_dir(self.base, "decoy"),
                           message="decoy trigger fixture")
        trigger = decoy.head  # a real commit from a different throwaway repo
        self.assertNotEqual(trigger, self.repo.head)

        proc = self.run_script(PRODUCER_OUTCOME="success", GITHUB_SHA=trigger)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rec = _record(proc)

        self.assertEqual(rec["code_revision"], self.repo.head)
        self.assertEqual(rec["trigger_revision"], trigger)
        self.assertNotEqual(rec["code_revision"], rec["trigger_revision"])
        self.assertEqual(rec["code_revision_status"], "resolved")
        self.assertTrue(rec["produced_by_this_run"])
        self.assertEqual(rec["workflow_run"], "424242")

    def test_unrelated_cwd_and_foreign_repo_cwd_still_bind_script_repo(self):
        foreign = ScriptRepo(_fresh_dir(self.base, "foreign"))
        for cwd in (self.unrelated, foreign.root):
            with self.subTest(cwd=str(cwd)):
                proc = self.run_script(cwd=cwd, PRODUCER_OUTCOME="success",
                                       GITHUB_SHA=foreign.head)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                rec = _record(proc)
                self.assertEqual(rec["code_revision"], self.repo.head)

    def test_inherited_git_directory_does_not_override_script_repository(self):
        foreign = ScriptRepo(_fresh_dir(self.base, "foreign-env"), message="foreign env")
        proc = self.run_script(
            cwd=foreign.root, GIT_DIR=str(foreign.root / ".git"),
            GIT_WORK_TREE=str(foreign.root), GITHUB_SHA=foreign.head,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(_record(proc)["code_revision"], self.repo.head)

    # -- unresolvable sources: null + status, trigger kept separately -------

    def _copy_script_without_repo(self) -> pathlib.Path:
        # Separate temp root so no parent directory can contain a repository.
        tmp = tempfile.TemporaryDirectory(prefix="ad1-evidence-norepo-")
        self.addCleanup(tmp.cleanup)
        plain = pathlib.Path(tmp.name) / "plain"
        (plain / "scripts" / "ci").mkdir(parents=True)
        shutil.copyfile(SCRIPT, plain / "scripts" / "ci" / "ad1_execution_evidence.py")
        return plain

    def test_non_repository_reports_unavailable_with_trigger_separate(self):
        plain = self._copy_script_without_repo()
        trigger = self.repo.head
        proc = run_evidence(plain / "scripts" / "ci" / "ad1_execution_evidence.py",
                            cwd=self.unrelated, PRODUCER_OUTCOME="success",
                            GITHUB_SHA=trigger)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rec = _record(proc)
        self.assertIsNone(rec["code_revision"])
        self.assertIn("unavailable", str(rec["code_revision_status"]))
        self.assertEqual(rec["trigger_revision"], trigger)
        self.assertIn("could not resolve source code revision", proc.stdout)

    def test_missing_git_binary_reports_unavailable(self):
        empty_bin = _fresh_dir(self.base, "empty-bin")
        trigger = self.repo.head
        proc = self.run_script(PRODUCER_OUTCOME="success", GITHUB_SHA=trigger,
                               PATH=str(empty_bin))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rec = _record(proc)
        self.assertIsNone(rec["code_revision"])
        self.assertIn("git executable not found", str(rec["code_revision_status"]))
        self.assertEqual(rec["trigger_revision"], trigger)
        self.assertNotEqual(rec["code_revision"], rec["trigger_revision"])

    def test_repository_without_commits_reports_unavailable(self):
        empty_root = _fresh_dir(self.base, "empty-repo")
        _git(empty_root, "init")
        (empty_root / "scripts" / "ci").mkdir(parents=True)
        shutil.copyfile(SCRIPT, empty_root / "scripts" / "ci" / "ad1_execution_evidence.py")
        proc = run_evidence(empty_root / "scripts" / "ci" / "ad1_execution_evidence.py",
                            cwd=self.unrelated, PRODUCER_OUTCOME="success",
                            GITHUB_SHA=self.repo.head)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rec = _record(proc)
        self.assertIsNone(rec["code_revision"])
        self.assertIn("unavailable", str(rec["code_revision_status"]))
        self.assertEqual(rec["trigger_revision"], self.repo.head)

    # -- preserved producer/skip/artifact semantics --------------------------

    def test_producer_outcome_and_skip_semantics_preserved(self):
        cases = [
            ({"PRODUCER_OUTCOME": "success"}, True),
            ({"PRODUCER_OUTCOME": "failure"}, False),
            ({"PRODUCER_OUTCOME": "cancelled"}, False),
            ({"PRODUCER_OUTCOME": "skipped"}, False),
            ({"PRODUCER_OUTCOME": "success", "SKIP_REASON": "no-store-token"}, False),
            ({}, False),
        ]
        for env_extra, produced in cases:
            with self.subTest(env=env_extra):
                proc = self.run_script(cwd=self.repo.root, **env_extra)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                rec = _record(proc)
                self.assertIs(rec["produced_by_this_run"], produced)
                self.assertEqual(rec["producer_outcome"],
                                 env_extra.get("PRODUCER_OUTCOME") or "not-run")
                self.assertEqual(rec["skip_reason"],
                                 env_extra.get("SKIP_REASON") or None)
                self.assertEqual(rec["code_revision"], self.repo.head)
                if produced:
                    self.assertNotIn("did not produce", proc.stdout)
                else:
                    self.assertIn("did not produce", proc.stdout)

    def test_brief_fields_digest_and_warnings_preserved(self):
        site = _fresh_dir(self.repo.root, "site")
        brief = {
            "as_of_session": "s-2026-10-18",
            "oi_counted_date": "2026-10-17",
            "board_state": "OPEN",
            "receipt_id": "rcpt-abc123",
            "eligibility": {"eligible": 2, "source_coverage_pct": 87.5},
            "_run": {"store_resolution": "ok"},
        }
        payload = json.dumps(brief).encode()
        brief_path = site / "options_intel_brief.json"
        brief_path.write_bytes(payload)

        proc = self.run_script(cwd=self.repo.root, PRODUCER_OUTCOME="success")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rec = _record(proc)
        self.assertEqual(rec["output_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(rec["receipt_id"], "rcpt-abc123")
        self.assertEqual(rec["eligible"], 2)
        self.assertEqual(rec["source_coverage_pct"], 87.5)
        self.assertEqual(rec["store_resolution"], "ok")
        self.assertNotIn("artifact", rec)
        self.assertNotIn("did not produce", proc.stdout)
        self.assertNotIn("eligible=0", proc.stdout)

        # eligible=0 stays a published-but-flagged success
        brief_path.write_bytes(json.dumps({"eligibility": {"eligible": 0}}).encode())
        proc = self.run_script(cwd=self.repo.root, PRODUCER_OUTCOME="success")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(_record(proc)["eligible"], 0)
        self.assertIn("eligible=0", proc.stdout)

        # unreadable brief: evidence notes it, never crashes the night
        brief_path.write_bytes(b"{not-json")
        proc = self.run_script(cwd=self.repo.root, PRODUCER_OUTCOME="success")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(str(_record(proc)["artifact"]).startswith("UNREADABLE"))

    def test_absent_brief_still_records_absent(self):
        proc = self.run_script(cwd=self.unrelated, PRODUCER_OUTCOME="success",
                               GITHUB_SHA=self.repo.head)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rec = _record(proc)
        self.assertEqual(rec["artifact"], "ABSENT")
        self.assertEqual(rec["code_revision"], self.repo.head)
        self.assertEqual(rec["trigger_revision"], self.repo.head)


if __name__ == "__main__":
    unittest.main()
