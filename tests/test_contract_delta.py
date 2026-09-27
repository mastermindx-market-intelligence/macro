"""Contract for scripts/check_contract_delta.py, the differential merge-train gate.

Five things are pinned here, matching the five ways this gate could quietly
stop doing its job:

  1. DELTA SEMANTICS — a finding present identically on head and base must never
     fail the job (that is the whole point: an absolute validator here would
     re-jam the fleet at PR level the moment main itself carries one inherited
     finding), a finding new on head must always fail it, and a finding fixed on
     head (present only on base) must neither fail nor even print.
  2. NO DRIFT — this script, tests/test_ci_pack.py's own absolute check, and
     scripts/audit_unrun_tests.py's own gate must all reference the SAME
     function objects, never independently re-derived copies that can diverge.
  3. WIRING — the ci.yml job exists, is fenced to pull_request events (so a
     main-proof push/dispatch run never even attempts a diff it has no base
     for), its run step actually calls the script with --base, ci-gate's needs
     include it, and ci-gate's enforcement step treats a `skipped` result (every
     non-pull_request event) as OK — plus the new suite (this file) is itself
     wired into a job, or scripts/audit_unrun_tests.py's gate would flag it as
     one more unwired suite in the very lane whose job is finding those.
  4. SPARSE EXACTNESS — both head and base bind the tested commit's tracked-path
     inventory before deriving closure, so omitted non-Python leaves remain
     visible without materializing the generated-heavy site/data trees.
  5. CONTROL-PLANE CLASSES (2026-09-27) — the packing probes, skip-only gates
     and trigger gaps get the same delta law as 1, share their guards'
     functions as in 2, read the probe ceilings from the one test that owns
     them, and the base worker's bootstrap rows equal the shared functions'.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
from dataclasses import dataclass
import inspect

import json
import os
import signal
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest
import yaml

from scripts import check_ci_trigger_closure as TRIGGER
from scripts import check_contract_delta as CCD
from scripts import check_skip_only_suites as SKIP
from scripts import run_ci_pack as PACK
from scripts.run_ci_pack import curated_exclusive_closure_findings as PACK_CLOSURE_FN
from scripts.audit_unrun_tests import gated_unrun_suites as AUDIT_SUITES_FN
import tests.test_ci_pack as test_ci_pack_module

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"


# ─────────────────────────────────────────────────────────────────────────────
# 1. delta semantics
# ─────────────────────────────────────────────────────────────────────────────

def test_introduced_finding_reds() -> None:
    head = {"closure": {"job-a": ["engine/x.py"]}, "suites": []}
    base = {"closure": {}, "suites": []}
    delta = CCD.compute_delta(head, base)
    assert delta["introduced_closure"] == [("job-a", "engine/x.py")]
    assert delta["inherited_closure"] == []
    assert CCD.has_introduced_findings(delta) is True


def test_introduced_unwired_suite_reds() -> None:
    head = {"closure": {}, "suites": ["tests/test_new.py"]}
    base = {"closure": {}, "suites": []}
    delta = CCD.compute_delta(head, base)
    assert delta["introduced_suites"] == ["tests/test_new.py"]
    assert CCD.has_introduced_findings(delta) is True


def test_inherited_only_finding_does_not_red() -> None:
    """Identical on both sides -- pre-existing, main law: never fail on this."""
    head = {"closure": {"job-a": ["engine/x.py"]}, "suites": ["tests/test_a.py"]}
    base = {"closure": {"job-a": ["engine/x.py"]}, "suites": ["tests/test_a.py"]}
    delta = CCD.compute_delta(head, base)
    assert delta["introduced_closure"] == []
    assert delta["introduced_suites"] == []
    assert delta["inherited_closure"] == [("job-a", "engine/x.py")]
    assert delta["inherited_suites"] == ["tests/test_a.py"]
    assert CCD.has_introduced_findings(delta) is False


def test_fixed_on_head_does_not_red_or_appear_anywhere() -> None:
    """Present on base only (this PR fixed it) -- not this PR's problem to report."""
    head = {"closure": {}, "suites": []}
    base = {"closure": {"job-a": ["engine/x.py"]}, "suites": ["tests/test_a.py"]}
    delta = CCD.compute_delta(head, base)
    assert delta == {
        "introduced_closure": [],
        "inherited_closure": [],
        "introduced_suites": [],
        "inherited_suites": [],
    }
    assert CCD.has_introduced_findings(delta) is False


def test_partial_overlap_reds_only_the_new_pair() -> None:
    """A job already broken on base still reds for a genuinely NEW uncovered path.

    Finding identity is (job_id, path) pairs, not job_id alone -- see the module
    docstring. A job that already had one inherited miss must not get amnesty
    for adding a second, different one.
    """
    head = {"closure": {"job-a": ["a.py", "b.py"]}, "suites": []}
    base = {"closure": {"job-a": ["a.py"]}, "suites": []}
    delta = CCD.compute_delta(head, base)
    assert delta["introduced_closure"] == [("job-a", "b.py")]
    assert delta["inherited_closure"] == [("job-a", "a.py")]
    assert CCD.has_introduced_findings(delta) is True


def test_empty_both_sides_is_a_clean_delta() -> None:
    delta = CCD.compute_delta({"closure": {}, "suites": []}, {"closure": {}, "suites": []})
    assert not CCD.has_introduced_findings(delta)
    assert CCD.format_report(delta) == []


# ─────────────────────────────────────────────────────────────────────────────
# report formatting -- house law: every annotation is a bare, line-starting print
# ─────────────────────────────────────────────────────────────────────────────

def test_format_report_error_lines_cover_only_introduced_findings() -> None:
    delta = {
        "introduced_closure": [("job-a", "a.py")],
        "inherited_closure": [("job-b", "b.py")],
        "introduced_suites": ["tests/test_new.py"],
        "inherited_suites": ["tests/test_old.py"],
    }
    lines = CCD.format_report(delta)
    errors = [line for line in lines if line.startswith("::error")]
    notices = [line for line in lines if line.startswith("::notice")]
    assert len(errors) == 2
    assert len(notices) == 2
    assert all(line.startswith("::error title=contract-delta::") for line in errors)
    assert all(line.startswith("::notice title=contract-delta::") for line in notices)
    assert any("job-a" in line and "a.py" in line for line in errors)
    assert any("tests/test_new.py" in line for line in errors)
    assert any("job-b" in line and "b.py" in line for line in notices)
    assert any("tests/test_old.py" in line for line in notices)
    # Every line START with the annotation token -- a prefixed logger call
    # (`log.warning("::warning ...")`) silently drops the annotation in GitHub
    # Actions; this house law is CI-guarded elsewhere (test_gh_annotation_line_start),
    # pinned locally too since these lines are built by hand, not via that helper.
    assert all(line.startswith("::") for line in lines)


# ─────────────────────────────────────────────────────────────────────────────
# 2. no drift -- shared implementation, pinned by object identity
# ─────────────────────────────────────────────────────────────────────────────

def test_curated_exclusive_closure_findings_is_the_shared_implementation() -> None:
    """check_contract_delta and tests/test_ci_pack.py must import the SAME
    scripts.run_ci_pack function -- module identity, not merely equal output.

    Equal output would still pass if one caller quietly forked its own copy of
    the covered/uncovered comparison; identity is the only check that catches
    that fork on day one instead of the day the two copies disagree.
    """
    assert CCD.curated_exclusive_closure_findings is PACK_CLOSURE_FN
    assert test_ci_pack_module.curated_exclusive_closure_findings is PACK_CLOSURE_FN


def test_gated_unrun_suites_is_the_shared_implementation() -> None:
    assert CCD.gated_unrun_suites is AUDIT_SUITES_FN


def test_head_findings_binds_exact_tree_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Omitted tracked leaves remain visible while contract-delta derives head scope."""
    tree = tmp_path / "tree"
    manifest = tree / CCD.MANIFEST_REL
    manifest.parent.mkdir(parents=True)
    manifest.write_text("jobs: {}\n", encoding="utf-8")
    sha = "1" * 40
    events: list[tuple] = []

    monkeypatch.setattr(CCD, "ROOT", tree)
    monkeypatch.setattr(
        CCD,
        "_git",
        lambda *args, cwd: sha + "\n",
    )

    def write_inventory(output: Path, tested_tree_sha: str, *, root: Path):
        events.append(("write", output, tested_tree_sha, root))
        output.write_text("fixture", encoding="utf-8")
        return object()

    @contextmanager
    def activate_inventory(source: Path, tested_tree_sha: str, *, root: Path):
        events.append(("enter", source, tested_tree_sha, root, source.exists()))
        yield object()
        events.append(("exit",))

    monkeypatch.setattr(CCD, "write_tracked_path_inventory", write_inventory, raising=False)
    monkeypatch.setattr(
        CCD, "planner_tracked_path_inventory", activate_inventory, raising=False
    )

    def closure_findings(path: Path):
        assert events[-1][0] == "enter"
        assert path == manifest
        return {"unrun-picks-boards": ["site/theme.css"]}  # ci-trigger-closure: data — fixture finding name, never opened

    def suite_findings():
        assert events[-1][0] == "enter"
        return ["tests/test_unwired.py"]

    monkeypatch.setattr(CCD, "curated_exclusive_closure_findings", closure_findings)
    monkeypatch.setattr(CCD, "gated_unrun_suites", suite_findings)

    assert CCD._head_findings() == {
        "closure": {"unrun-picks-boards": ["site/theme.css"]},  # ci-trigger-closure: data — fixture finding name, never opened
        "suites": ["tests/test_unwired.py"],
    }
    assert [event[0] for event in events] == ["write", "enter", "exit"]
    assert events[0][2:] == (sha, tree)
    assert events[1][2:4] == (sha, tree)
    assert events[1][4] is True


def test_base_worker_binds_exact_tree_inventory_before_census() -> None:
    """Head/base symmetry requires the detached-tree worker to use the same oracle."""
    source = CCD._WORKER_SOURCE
    assert "write_tracked_path_inventory" in source
    assert "planner_tracked_path_inventory" in source
    assert "with _tracked_tree_inventory():" in source


def test_base_worker_inventory_bootstrap_cannot_swallow_internal_import_errors() -> None:
    """Only a genuinely old base may lack the inventory API; broken imports must red."""
    helper = CCD._WORKER_SOURCE.split(
        "@contextmanager\ndef _tracked_tree_inventory():", 1
    )[1].split(
        "\n\ntry:\n    from scripts.run_ci_pack", 1
    )[0]
    assert "except ModuleNotFoundError as exc:" in helper
    assert 'if exc.name != "scripts.ci_scope_dependencies":' in helper
    assert "except ImportError:" not in helper


def test_worker_bootstrap_fallback_tries_the_canonical_functions_first() -> None:
    """The base-tree subprocess worker must attempt the SAME shared functions
    before falling back to the primitive-level bootstrap reconstruction (see
    the module docstring's "BOOTSTRAP FALLBACK" section) -- every base commit
    from the moment this gate merges shares the real implementation; only a
    base that predates this PR takes the fallback branch.
    """
    assert (
        "from scripts.run_ci_pack import curated_exclusive_closure_findings"
        in CCD._WORKER_SOURCE
    )
    assert (
        "from scripts.audit_unrun_tests import gated_unrun_suites"
        in CCD._WORKER_SOURCE
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. wiring pins
# ─────────────────────────────────────────────────────────────────────────────

def _ci_jobs() -> dict:
    doc = yaml.safe_load(CI_WORKFLOW.read_text())
    return doc["jobs"]


def _step_named(job: dict, name: str) -> dict | None:
    for step in job.get("steps", []):
        if isinstance(step, dict) and step.get("name") == name:
            return step
    return None


def test_ci_yml_carries_a_contract_delta_job_gated_to_pull_request() -> None:
    jobs = _ci_jobs()
    assert "contract-delta" in jobs, "ci.yml must declare a contract-delta job"
    job = jobs["contract-delta"]
    assert job.get("if") == "github.event_name == 'pull_request'", (
        "contract-delta must never attempt to run on a push/workflow_dispatch "
        "main-proof event -- it has no PR base to diff against there"
    )
    assert job.get("runs-on") == "ubuntu-latest"
    # 25 -> 45 (2026-08-19, PR #6013 cancellation): the job is off the
    # critical path (packs run ~30 min regardless), so this pins a floor, not
    # an exact value -- a further raise for more margin must not red this.
    assert job.get("timeout-minutes", 0) >= 45


def test_contract_delta_binds_to_the_exact_tested_merge_parent() -> None:
    """A long-lived PR must compare against the base GitHub actually tested.

    `pull_request.base.sha` is the PR event's historical base snapshot.  GitHub's
    pull-request checkout is instead the synthetic merge commit whose first parent
    is the current tested base and whose second parent is the exact PR head.  The
    gate must derive from that immutable merge object so current-main debt remains
    inherited while candidate-added debt remains introduced.
    """
    jobs = _ci_jobs()
    job = jobs["contract-delta"]
    resolver = _step_named(job, "resolve the exact tested PR merge base")
    assert resolver is not None
    assert resolver.get("env", {}).get("EXPECTED_PR_HEAD") == (
        "${{ github.event.pull_request.head.sha }}"
    )
    resolver_run = resolver.get("run", "")
    assert "git rev-parse HEAD" in resolver_run
    assert "GITHUB_SHA" in resolver_run
    assert "git cat-file -p HEAD" in resolver_run
    assert "sed -n 's/^parent //p'" in resolver_run
    assert '"$#" -ne 2' in resolver_run
    assert '"$tested_head" != "$EXPECTED_PR_HEAD"' in resolver_run
    assert 'base_sha=$tested_base' in resolver_run

    blob = "\n".join(
        step.get("run", "") for step in job.get("steps", []) if isinstance(step, dict)
    )
    assert "scripts/check_contract_delta.py" in blob
    assert "--base" in blob
    assert "steps.contract-merge.outputs.base_sha" in blob
    assert "github.event.pull_request.base.sha" not in blob


def test_contract_delta_merge_resolver_selects_current_tested_base(
    tmp_path: Path,
) -> None:
    """Main movement after PR creation must be inherited, not candidate debt.

    Build the exact topology that exposed #7496: a candidate forks from an old
    base, main moves independently, and GitHub tests a two-parent synthetic merge.
    The workflow resolver must return the synthetic merge's first parent (current
    tested main), never the old creation base, and must bind the second parent to
    the exact PR head.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    _git("config", "user.email", "contract-delta@example.invalid", cwd=repo)
    _git("config", "user.name", "Contract Delta Test", cwd=repo)

    (repo / "root.txt").write_text("root\n", encoding="utf-8")
    _git("add", "root.txt", cwd=repo)
    _git("commit", "-m", "creation base", cwd=repo)
    creation_base = _git("rev-parse", "HEAD", cwd=repo).strip()

    _git("switch", "-c", "candidate", cwd=repo)
    (repo / "candidate.txt").write_text("candidate debt\n", encoding="utf-8")
    _git("add", "candidate.txt", cwd=repo)
    _git("commit", "-m", "candidate", cwd=repo)
    pr_head = _git("rev-parse", "HEAD", cwd=repo).strip()

    _git("switch", "main", cwd=repo)
    (repo / "main-debt.txt").write_text("current main debt\n", encoding="utf-8")
    _git("add", "main-debt.txt", cwd=repo)
    _git("commit", "-m", "main moved after PR creation", cwd=repo)
    tested_base = _git("rev-parse", "HEAD", cwd=repo).strip()
    assert tested_base != creation_base

    _git("merge", "--no-ff", "candidate", "-m", "synthetic tested merge", cwd=repo)
    tested_merge = _git("rev-parse", "HEAD", cwd=repo).strip()
    # actions/checkout@v4 with fetch-depth: 1 marks the tested merge itself as a
    # shallow boundary.  Revision-walking commands then hide its parents even
    # though the raw commit object still carries both `parent` headers.  Reproduce
    # that hosted topology so this regression cannot accidentally pass only in a
    # full local clone.
    (repo / ".git" / "shallow").write_text(tested_merge + "\n", encoding="utf-8")
    assert _git("show", "-s", "--format=%P", "HEAD", cwd=repo).strip() == ""
    raw_parents = [
        line.split(" ", 1)[1]
        for line in _git("cat-file", "-p", "HEAD", cwd=repo).splitlines()
        if line.startswith("parent ")
    ]
    assert raw_parents == [tested_base, pr_head]

    resolver = _step_named(_ci_jobs()["contract-delta"], "resolve the exact tested PR merge base")
    assert resolver is not None
    output = tmp_path / "github-output"
    env = {
        **os.environ,
        "GITHUB_SHA": tested_merge,
        "EXPECTED_PR_HEAD": pr_head,
        "GITHUB_OUTPUT": str(output),
    }
    subprocess.run(
        ["bash", "-c", resolver["run"]],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    resolved = dict(
        line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines()
    )
    assert resolved == {"base_sha": tested_base, "head_sha": pr_head}
    assert resolved["base_sha"] != creation_base

    bad = subprocess.run(
        ["bash", "-c", resolver["run"]],
        cwd=repo,
        env={**env, "EXPECTED_PR_HEAD": creation_base},
        check=False,
        capture_output=True,
        text=True,
    )
    assert bad.returncode != 0
    assert "second parent does not match the exact PR head" in bad.stderr


def test_ci_gate_needs_contract_delta() -> None:
    jobs = _ci_jobs()
    gate = jobs["ci-gate"]
    needs = gate.get("needs")
    assert isinstance(needs, list) and "contract-delta" in needs


def test_ci_gate_enforcement_step_treats_skip_as_ok() -> None:
    jobs = _ci_jobs()
    gate = jobs["ci-gate"]
    step = _step_named(gate, "enforce contract-delta verdict")
    assert step is not None, "ci-gate must carry an explicit contract-delta enforcement step"
    assert step.get("env", {}).get("CONTRACT_DELTA_RESULT") == (
        "${{ needs.contract-delta.result }}"
    )
    run = step.get("run", "")
    # Gated specifically on the literal string "failure", never on
    # non-"success" -- the latter would fail ci-gate on every non-pull_request
    # event, where contract-delta is `skipped` by design (see the job's own
    # `if:`, pinned above) and must read as OK.
    assert '$CONTRACT_DELTA_RESULT" = "failure"' in run
    assert '!= "success"' not in run and '!="success"' not in run


def test_legacy_jobs_ci_control_plane_job_runs_the_new_suite() -> None:
    """This file must be wired somewhere, or audit_unrun_tests.py's own gate --
    the very lane this gate exists to make pre-mergeable -- would flag it.

    Its home moved from workflow-yaml (gate: data, never run on a pull request)
    to ci-control-plane-contracts on 2026-09-25, and it must stay on the code
    gate: a contract for a PR gate that only runs after the merge proves
    nothing about the PR."""
    doc = yaml.safe_load(MANIFEST.read_text())
    job = doc["jobs"]["ci-control-plane-contracts"]
    blob = "\n".join(
        step.get("run", "") for step in job.get("steps", []) if isinstance(step, dict)
    )
    assert "tests/test_contract_delta.py" in blob
    assert job.get("gate", "code") == "code"


# ─────────────────────────────────────────────────────────────────────────────
# 4. base-tree materialization — mirrors the caller's sparse cone, placed under
#    the configured temp root, always cleaned up
# ─────────────────────────────────────────────────────────────────────────────

def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _make_repo(tmp_path: Path) -> Path:
    """A two-commit repo with a code dir and a generated-artifact dir."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "t@example.com", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    (repo / "engine").mkdir()
    (repo / "data").mkdir()
    (repo / "engine" / "x.py").write_text("X = 1\n")
    (repo / "data" / "big.txt").write_text("generated\n")
    (repo / "README.md").write_text("root\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "base", cwd=repo)
    (repo / "engine" / "x.py").write_text("X = 2\n")
    _git("commit", "-q", "-am", "head", cwd=repo)
    return repo


def test_full_caller_gets_a_full_base_tree(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setenv(CCD.TEMP_ROOT_ENV, str(tmp_path))
    tree, sha, cleanup = CCD.materialize_base_tree("HEAD~1", repo_root=repo)
    try:
        assert tree.parent == tmp_path and tree.name.startswith("contract-delta-base-")
        assert sha == _git("rev-parse", "HEAD~1", cwd=repo).strip()
        assert (tree / "engine" / "x.py").read_text() == "X = 1\n"
        assert (tree / "data" / "big.txt").exists(), "a full caller keeps the full base tree"
    finally:
        cleanup()
    assert not tree.exists()
    assert str(tree) not in _git("worktree", "list", "--porcelain", cwd=repo)


def test_sparse_caller_gets_a_base_tree_with_the_same_cone(tmp_path: Path, monkeypatch) -> None:
    """The whole point: no more 3.8 GiB full base under a 0.4 GiB sparse head."""
    repo = _make_repo(tmp_path)
    _git("sparse-checkout", "set", "--cone", "--", "engine", cwd=repo)
    assert not (repo / "data").exists()
    assert CCD.caller_sparse_cone(repo) == ["engine"]
    monkeypatch.setenv(CCD.TEMP_ROOT_ENV, str(tmp_path))
    tree, _sha, cleanup = CCD.materialize_base_tree("HEAD~1", repo_root=repo)
    try:
        assert (tree / "engine" / "x.py").read_text() == "X = 1\n"
        assert (tree / "README.md").exists(), "cone mode always materializes root files"
        assert not (tree / "data").exists(), "the omitted directory must stay omitted"
        assert _git("config", "--get", "core.sparseCheckout", cwd=tree).strip() == "true"
        assert _git("status", "--porcelain", cwd=tree) == ""
    finally:
        cleanup()
    assert not tree.exists()


def test_caller_sparse_cone_is_none_for_a_full_checkout(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert CCD.caller_sparse_cone(repo) is None


def test_temp_root_precedence(tmp_path: Path, monkeypatch) -> None:
    override = tmp_path / "override"
    override.mkdir()
    monkeypatch.setenv(CCD.TEMP_ROOT_ENV, str(override))
    assert CCD.base_tree_temp_root() == override
    monkeypatch.setenv(CCD.TEMP_ROOT_ENV, str(tmp_path / "does-not-exist"))
    assert CCD.base_tree_temp_root() is None, "a dangling override falls back to the system temp dir"
    monkeypatch.delenv(CCD.TEMP_ROOT_ENV)
    monkeypatch.setattr(CCD, "STORAGE_POLICY", tmp_path / "no-policy.json")
    assert CCD.base_tree_temp_root() is None
    # a policy whose volume is not mounted must not be used (never mint onto a
    # replacement directory on the internal disk)
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"mount_point": str(tmp_path / "vol"), "root": str(tmp_path / "vol" / "ws")}))
    (tmp_path / "vol" / "ws").mkdir(parents=True)
    monkeypatch.setattr(CCD, "STORAGE_POLICY", policy)
    assert CCD.base_tree_temp_root() is None


def test_sigterm_handler_raises_system_exit() -> None:
    """A cancelled CI job must unwind through run()'s finally (worktree cleanup)."""
    with pytest.raises(SystemExit) as excinfo:
        CCD._raise_on_sigterm(signal.SIGTERM, None)
    assert excinfo.value.code == 128 + signal.SIGTERM


# ─────────────────────────────────────────────────────────────────────────────
# 5. control-plane classes (2026-09-27): packing probes, skip-only gates and
#    trigger gaps, which ci-control-plane-contracts' path scope cannot see
# ─────────────────────────────────────────────────────────────────────────────

# The three probe NAMES, as fixtures. A bare string naming a tracked file is a
# read to the closure census (scripts/ci_scope_dependencies.py), and
# build_free_content.py's import closure would then land in this suite's job,
# ci-control-plane-contracts, whose paths do not (and must not) cover it:
# widening them would put that job on the very probes it measures. These
# tests hand the names to fakes and never open them.
# ci-trigger-closure: data — probe file NAMES handed to fakes, never opened
INDEX_PROBE, FREE_CONTENT_PROBE, PLAN_BOOK_PROBE = (
    "templates/index.html",
    "scripts/build_free_content.py",
    "engine/prophet/plan_book.py",
)

def _probe(
    probe: str = INDEX_PROBE,
    *,
    jobs: int = 134,
    weight: int = 5_501,
    packs: int = 10,
    max_jobs: int = 134,
    max_weight: int = 5_800,
    max_packs: int = 10,
) -> dict:
    """One packing-probe row; the defaults are templates/index.html on main at
    the time of writing, at (not over) its 134-job ceiling."""
    return {
        "probe": probe,
        "jobs": jobs,
        "weight": weight,
        "packs": packs,
        "max_jobs": max_jobs,
        "max_weight": max_weight,
        "max_packs": max_packs,
        "job_ids": [f"job-{index:03d}" for index in range(jobs)],
        "reason": "fixture",
    }


def _skip_row(test: str = "tests/test_x.py", gate: str = "hypothesis") -> dict:
    return {
        "test": test,
        "gate": gate,
        "needs": [gate],
        "why": [f"pytest.importorskip({gate!r})"],
        "naming_jobs": ["job-b", "job-a"],
        "satisfying_jobs": [],
        "status": "SKIP-ONLY",
    }


def _gap_row(test: str = "tests/test_x.py", gaps: tuple[str, ...] = ("engine/x.py",)) -> dict:
    return {
        "test": test,
        "run_by": [".github/ci/legacy-jobs.yml::job-a"],
        "filters": [".github/workflows/fences.yml"],
        "subjects": sorted(gaps),
        "gaps": list(gaps),
        "why": {gap: f"open({gap!r})" for gap in gaps},
        "self_reachable": True,
        "data_marked": {},
        "status": "GAP",
    }


def _payload(**classes) -> dict:
    return {
        "closure": {},
        "suites": [],
        "probes": [_probe()],
        "skip_only": [],
        "trigger_gaps": [],
        **classes,
    }


def test_a_probe_newly_over_its_ceiling_reds() -> None:
    """The #8033 review's shape: one suite starts reading templates/index.html
    and the probe goes from its 134-job ceiling to 135."""
    delta = CCD.compute_delta(_payload(probes=[_probe(jobs=135)]), _payload())
    assert delta["introduced_probes"] == [
        CCD.ProbeFinding(INDEX_PROBE, "jobs", 135, 134, 134, ("job-134",))
    ]
    assert delta["inherited_probes"] == []
    assert CCD.has_introduced_findings(delta) is True


def test_a_probe_breach_inherited_from_the_base_does_not_red() -> None:
    over = _payload(probes=[_probe(jobs=135)])
    delta = CCD.compute_delta(over, copy.deepcopy(over))
    assert delta["introduced_probes"] == []
    assert delta["inherited_probes"] == [
        CCD.ProbeFinding(INDEX_PROBE, "jobs", 135, 134, 135, ())
    ]
    assert CCD.has_introduced_findings(delta) is False


def test_a_head_pushed_further_over_an_inherited_breach_reds() -> None:
    """Magnitude, not just (probe, axis): an already-breached probe gives no
    amnesty to a PR that selects still more jobs for it."""
    delta = CCD.compute_delta(
        _payload(probes=[_probe(jobs=136)]), _payload(probes=[_probe(jobs=135)])
    )
    assert delta["introduced_probes"] == [
        CCD.ProbeFinding(INDEX_PROBE, "jobs", 136, 134, 135, ("job-135",))
    ]
    assert CCD.has_introduced_findings(delta) is True


def test_a_head_that_shrinks_an_inherited_breach_does_not_red() -> None:
    delta = CCD.compute_delta(
        _payload(probes=[_probe(jobs=135)]), _payload(probes=[_probe(jobs=137)])
    )
    assert delta["introduced_probes"] == []
    assert [finding.base for finding in delta["inherited_probes"]] == [137]
    assert CCD.has_introduced_findings(delta) is False


def test_a_probe_fixed_on_head_is_silent() -> None:
    delta = CCD.compute_delta(_payload(), _payload(probes=[_probe(jobs=135)]))
    assert delta["introduced_probes"] == [] and delta["inherited_probes"] == []
    assert CCD.format_report(delta) == []


def test_each_probe_axis_is_its_own_finding() -> None:
    """Weight and packs breach without a single new job: the same jobs, heavier."""
    head = _payload(probes=[
        _probe(weight=5_900),
        _probe(FREE_CONTENT_PROBE, jobs=131, weight=6_001, packs=11,
               max_jobs=132, max_weight=9_000),
    ])
    base = _payload(probes=[
        _probe(),
        _probe(FREE_CONTENT_PROBE, jobs=131, weight=5_269, packs=9,
               max_jobs=132, max_weight=9_000),
    ])
    delta = CCD.compute_delta(head, base)
    assert delta["introduced_probes"] == [
        CCD.ProbeFinding(FREE_CONTENT_PROBE, "packs", 11, 10, 9, ()),
        CCD.ProbeFinding(INDEX_PROBE, "weight", 5_900, 5_800, 5_501, ()),
    ]


def test_a_new_skip_only_gate_reds() -> None:
    delta = CCD.compute_delta(_payload(skip_only=[_skip_row()]), _payload())
    assert delta["introduced_skip_only"] == [
        CCD.SkipOnlyFinding("tests/test_x.py", "hypothesis", ("hypothesis",), ("job-a", "job-b"))
    ]
    assert CCD.has_introduced_findings(delta) is True


def test_an_inherited_skip_only_gate_does_not_red() -> None:
    same = _payload(skip_only=[_skip_row()])
    delta = CCD.compute_delta(same, copy.deepcopy(same))
    assert delta["introduced_skip_only"] == []
    assert [(f.test, f.gate) for f in delta["inherited_skip_only"]] == [
        ("tests/test_x.py", "hypothesis")
    ]
    assert CCD.has_introduced_findings(delta) is False


def test_a_second_gate_on_an_already_skip_only_suite_still_reds() -> None:
    """Identity is (suite, gate), so an inherited gate is no amnesty for a new one."""
    delta = CCD.compute_delta(
        _payload(skip_only=[_skip_row(), _skip_row(gate="numpy")]),
        _payload(skip_only=[_skip_row()]),
    )
    assert [(f.test, f.gate) for f in delta["introduced_skip_only"]] == [("tests/test_x.py", "numpy")]
    assert [(f.test, f.gate) for f in delta["inherited_skip_only"]] == [("tests/test_x.py", "hypothesis")]


def test_a_new_trigger_gap_reds() -> None:
    delta = CCD.compute_delta(_payload(trigger_gaps=[_gap_row()]), _payload())
    assert delta["introduced_trigger_gaps"] == [
        CCD.TriggerGapFinding(
            "tests/test_x.py",
            "engine/x.py",
            "open('engine/x.py')",
            (".github/workflows/fences.yml",),
            (".github/ci/legacy-jobs.yml::job-a",),
        )
    ]
    assert CCD.has_introduced_findings(delta) is True


def test_an_inherited_trigger_gap_does_not_red() -> None:
    same = _payload(trigger_gaps=[_gap_row()])
    delta = CCD.compute_delta(same, copy.deepcopy(same))
    assert delta["introduced_trigger_gaps"] == []
    assert [(f.test, f.subject) for f in delta["inherited_trigger_gaps"]] == [
        ("tests/test_x.py", "engine/x.py")
    ]
    assert CCD.has_introduced_findings(delta) is False


def test_a_new_subject_on_a_suite_with_an_inherited_gap_still_reds() -> None:
    delta = CCD.compute_delta(
        _payload(trigger_gaps=[_gap_row(gaps=("engine/x.py", "engine/y.py"))]),
        _payload(trigger_gaps=[_gap_row()]),
    )
    assert [(f.test, f.subject) for f in delta["introduced_trigger_gaps"]] == [
        ("tests/test_x.py", "engine/y.py")
    ]
    assert [(f.test, f.subject) for f in delta["inherited_trigger_gaps"]] == [
        ("tests/test_x.py", "engine/x.py")
    ]


def test_a_base_that_predates_a_guard_counts_every_head_finding_as_introduced() -> None:
    """`null` is what the worker ships for a guard module the base does not
    have: nothing can be inherited from it, and the log says why."""
    head = _payload(skip_only=[_skip_row()])
    base = _payload(skip_only=None)
    delta = CCD.compute_delta(head, base)
    assert [(f.test, f.gate) for f in delta["introduced_skip_only"]] == [("tests/test_x.py", "hypothesis")]
    notices = [line for line in CCD.measurement_lines(head, base) if line.startswith("::notice")]
    assert len(notices) == 1
    assert notices[0].startswith("::notice title=contract-delta::") and "skip_only" in notices[0]


def test_control_plane_keys_appear_only_for_the_classes_a_payload_carries() -> None:
    delta = CCD.compute_delta(
        {"closure": {}, "suites": [], "probes": [_probe()]},
        {"closure": {}, "suites": []},
    )
    assert set(delta) == {
        "introduced_closure", "inherited_closure", "introduced_suites",
        "inherited_suites", "introduced_probes", "inherited_probes",
    }


def test_format_report_covers_the_control_plane_classes() -> None:
    head = _payload(
        probes=[_probe(jobs=135), _probe(PLAN_BOOK_PROBE, jobs=128, max_jobs=127)],
        skip_only=[_skip_row(), _skip_row("tests/test_old.py")],
        trigger_gaps=[_gap_row(), _gap_row("tests/test_old.py", ("engine/old.py",))],
    )
    base = _payload(
        probes=[_probe(), _probe(PLAN_BOOK_PROBE, jobs=128, max_jobs=127)],
        skip_only=[_skip_row("tests/test_old.py")],
        trigger_gaps=[_gap_row("tests/test_old.py", ("engine/old.py",))],
    )
    lines = CCD.format_report(CCD.compute_delta(head, base))
    errors = [line for line in lines if line.startswith("::error title=contract-delta::")]
    notices = [line for line in lines if line.startswith("::notice title=contract-delta::")]
    assert len(errors) == 3 and len(notices) == 3 and len(lines) == 6
    probe_error, skip_error, gap_error = errors
    assert INDEX_PROBE in probe_error and "135 jobs" in probe_error
    assert "ceiling 134" in probe_error and "job-134" in probe_error
    assert "PACKING_PROBES" in probe_error
    assert "tests/test_x.py" in skip_error and "`hypothesis`" in skip_error
    assert "tests/test_x.py reads engine/x.py" in gap_error
    assert "# ci-trigger-closure: data" in gap_error
    assert PLAN_BOOK_PROBE in notices[0] and "128" in notices[0]
    assert "tests/test_old.py" in notices[1]
    assert "engine/old.py" in notices[2]


def test_measurement_lines_print_both_sides_of_every_probe_and_the_census_seconds() -> None:
    head = _payload(probes=[_probe(jobs=135)], timings={"probes": 1.25, "closure_and_suites": 2.0})
    base = _payload(timings={"probes": 1.0})
    lines = CCD.measurement_lines(head, base)
    assert lines == [
        "contract-delta: probe templates/index.html: head 135 jobs / 5,501 s / 10 packs; "
        "base 134 jobs / 5,501 s / 10 packs; ceilings 134 / 5,800 / 10",
        "contract-delta: head census seconds: closure_and_suites 2.0, probes 1.2",
        "contract-delta: base census seconds: probes 1.0",
    ]


def test_an_incomplete_census_is_a_refusal_not_a_pass() -> None:
    with pytest.raises(CCD.ContractDeltaError, match="missing"):
        CCD._require_control_plane_classes({"closure": {}, "suites": []}, "base 0123456789ab")
    with pytest.raises(CCD.ContractDeltaError, match="malformed"):
        CCD._require_control_plane_classes(_payload(probes={}), "head")
    with pytest.raises(CCD.ContractDeltaError, match="guard module"):
        CCD._require_control_plane_classes(_payload(skip_only=None), "head")
    CCD._require_control_plane_classes(_payload(skip_only=None), "base 0123456789ab")


def _fake_run(monkeypatch: pytest.MonkeyPatch, *, head: dict, base: dict) -> tuple[int, dict]:
    """`run()` with every tree, git and subprocess edge replaced by fixtures."""
    spec = {"probes": [[INDEX_PROBE, 134, 5_800]], "max_packs": 10}
    calls: dict = {}

    def start_worker(tree: Path, given_spec: dict) -> str:
        calls["spec"] = given_spec
        return "proc"

    monkeypatch.setattr(CCD, "packing_probe_spec", lambda suite: spec)
    monkeypatch.setattr(
        CCD,
        "materialize_base_tree",
        lambda ref, *, repo_root: (Path("/base"), "b" * 40, lambda: calls.setdefault("cleaned", True)),
    )
    monkeypatch.setattr(CCD, "_start_worker", start_worker)
    monkeypatch.setattr(CCD, "_finish_worker", lambda proc, tree: copy.deepcopy(base))
    monkeypatch.setattr(
        CCD, "_head_findings", lambda: {"closure": head["closure"], "suites": head["suites"]}
    )
    monkeypatch.setattr(
        CCD,
        "_head_control_plane_findings",
        lambda given: {
            **{name: copy.deepcopy(head[name]) for name in CCD.CONTROL_PLANE_CLASSES},
            "timings": {},
        },
    )
    code = CCD.run("origin/main")
    assert calls == {"spec": spec, "cleaned": True}
    return code, calls


@pytest.mark.parametrize(
    "name, finding",
    [
        ("probes", [_probe(jobs=135)]),
        ("skip_only", [_skip_row()]),
        ("trigger_gaps", [_gap_row()]),
    ],
)
def test_run_reds_only_on_what_the_head_introduces(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, name: str, finding: list
) -> None:
    """End to end through `run()`: introduced reds, inherited never does, fixed is silent."""
    clean = _payload()
    dirty = {**_payload(), name: finding}

    code, _ = _fake_run(monkeypatch, head=dirty, base=clean)
    out = capsys.readouterr().out
    assert code == 1
    assert "::error title=contract-delta::" in out
    assert "contract-delta: 1 introduced, 0 inherited (base bbbbbbbbbbbb)" in out

    code, _ = _fake_run(monkeypatch, head=dirty, base=dirty)
    out = capsys.readouterr().out
    assert code == 0, "an inherited finding must never red"
    assert "::error" not in out and "::notice title=contract-delta::" in out
    assert "contract-delta: 0 introduced, 1 inherited" in out

    code, _ = _fake_run(monkeypatch, head=clean, base=dirty)
    out = capsys.readouterr().out
    assert code == 0
    assert "::error" not in out and "::notice" not in out


def test_packing_probe_functions_are_the_shared_implementation() -> None:
    assert CCD.packing_probe_measurements is PACK.packing_probe_measurements
    assert CCD.packing_probe_breaches is PACK.packing_probe_breaches
    assert test_ci_pack_module.packing_probe_measurements is PACK.packing_probe_measurements
    assert test_ci_pack_module.packing_probe_breaches is PACK.packing_probe_breaches


def test_skip_only_and_trigger_gap_findings_are_the_shared_implementation() -> None:
    """Contract-delta diffs exactly the rows each guard's own main fails on."""
    assert CCD.skip_only_findings is SKIP.skip_only_findings
    assert CCD.trigger_gap_findings is TRIGGER.trigger_gap_findings
    assert "bad = skip_only_findings(rows)" in inspect.getsource(SKIP.main)
    assert "bad = trigger_gap_findings(rows)" in inspect.getsource(TRIGGER.main)


def test_probe_ceilings_are_read_from_the_test_that_owns_them() -> None:
    spec = CCD.packing_probe_spec(ROOT / CCD.PACKING_PROBE_SUITE_REL)
    assert spec == {
        "probes": [list(probe) for probe in test_ci_pack_module.PACKING_PROBES],
        "max_packs": test_ci_pack_module.PACKING_PROBE_MAX_PACKS,
    }
    assert json.loads(json.dumps(spec)) == spec, "the spec rides the worker's argv as JSON"


def test_probe_spec_accepts_an_annotated_literal(tmp_path: Path) -> None:
    suite = tmp_path / "test_ci_pack.py"
    suite.write_text(
        "PACKING_PROBES: tuple = (('a.py', 1, 2_000),)\nPACKING_PROBE_MAX_PACKS: int = 3\n"
    )
    assert CCD.packing_probe_spec(suite) == {"probes": [["a.py", 1, 2000]], "max_packs": 3}


@pytest.mark.parametrize(
    "source",
    [
        "",
        "PACKING_PROBES = ()\nPACKING_PROBE_MAX_PACKS = 10\n",
        "PACKING_PROBES = (('a.py', 1, 2),)\n",
        "PACKING_PROBES = tuple([('a.py', 1, 2)])\nPACKING_PROBE_MAX_PACKS = 10\n",
        "PACKING_PROBES = (('a.py', 1, 2), ('a.py', 3, 4))\nPACKING_PROBE_MAX_PACKS = 10\n",
        "PACKING_PROBES = (('a.py', True, 2),)\nPACKING_PROBE_MAX_PACKS = 10\n",
        "PACKING_PROBES = (('a.py', 0, 2),)\nPACKING_PROBE_MAX_PACKS = 10\n",
        "PACKING_PROBES = (('a.py', 1),)\nPACKING_PROBE_MAX_PACKS = 10\n",
        "PACKING_PROBES = (('', 1, 2),)\nPACKING_PROBE_MAX_PACKS = 10\n",
        "PACKING_PROBES = (('a.py', 1, 2),)\nPACKING_PROBE_MAX_PACKS = '10'\n",
        "PACKING_PROBES = (('a.py', 1, 2),\nPACKING_PROBE_MAX_PACKS = 10\n",
    ],
)
def test_a_malformed_probe_spec_is_a_refusal(tmp_path: Path, source: str) -> None:
    """Never an empty probe set: that would pass every PR without measuring."""
    suite = tmp_path / "test_ci_pack.py"
    suite.write_text(source)
    with pytest.raises(CCD.ContractDeltaError):
        CCD.packing_probe_spec(suite)


def test_a_missing_probe_suite_is_a_refusal(tmp_path: Path) -> None:
    with pytest.raises(CCD.ContractDeltaError):
        CCD.packing_probe_spec(tmp_path / "absent.py")


def test_start_worker_hands_the_head_spec_to_the_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict = {}

    class FakePopen:
        def __init__(self, args: list, **kwargs) -> None:
            seen["args"], seen["kwargs"] = args, kwargs

    monkeypatch.setattr(CCD.subprocess, "Popen", FakePopen)
    spec = {"probes": [["a.py", 1, 2]], "max_packs": 3}
    CCD._start_worker(tmp_path, spec)
    assert seen["args"][:3] == [sys.executable, "-c", CCD._WORKER_SOURCE]
    assert json.loads(seen["args"][3]) == spec
    assert seen["kwargs"]["cwd"] == tmp_path


def test_worker_emits_every_control_plane_class_from_both_branches() -> None:
    source = CCD._WORKER_SOURCE
    assert CCD._WORKER_CONTROL_PLANE_SOURCE in source
    assert "SPEC = json.loads(sys.argv[1])" in source
    assert source.count("control = _control_plane_findings()") == 2
    assert source.count(
        'print(json.dumps({"closure": closure, "suites": suites, **control}))'
    ) == 2


def test_worker_tries_the_shared_control_plane_functions_first() -> None:
    source = CCD._WORKER_CONTROL_PLANE_SOURCE
    for name in ("packing_probe_measurements", "skip_only_findings", "trigger_gap_findings"):
        assert f'getattr(pack, "{name}", None)' in source or f'getattr(guard, "{name}", None)' in source
    assert "except ImportError" not in source, "a broken guard import must red, not read as absent"


def _worker_helpers(spec: dict, modules: dict) -> dict:
    """The worker's control-plane helpers, exec'd against `modules` (by name).

    A module mapped to an exception raises it on import; an unmapped one is
    absent from the base.
    """
    def import_module(name: str):
        found = modules.get(name)
        if found is None:
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        if isinstance(found, BaseException):
            raise found
        return found

    namespace = {
        "importlib": types.SimpleNamespace(import_module=import_module),
        "time": time,
        "MANIFEST": Path(CCD.MANIFEST_REL),
        "SPEC": spec,
    }
    exec(compile(CCD._WORKER_CONTROL_PLANE_SOURCE, "<worker control plane>", "exec"), namespace)
    return namespace


@dataclass(frozen=True)
class _Job:
    job_id: str
    weight: int


def test_worker_probe_bootstrap_matches_the_shared_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This PR's own base has no packing_probe_measurements, so its worker takes
    the bootstrap. Its rows must equal the shared function's for the same
    planner answers, or every probe would read as moved on that one run.

    The weights cover the pack formula's floor (no job: 1 pack), a round-up
    (650 s: 2 packs) and its 12-pack cap (7,000 s).
    """
    jobs = [_Job("a", 400), _Job("b", 250), _Job("c", 7_000)]
    selections = {"x.html": {"a", "b"}, "y.py": {"c"}, "z.py": set()}

    def load_legacy_jobs(path: Path) -> list[_Job]:
        return list(jobs)

    def infer_job_scopes(loaded: list[_Job]) -> tuple[list[_Job], str]:
        return loaded, "note"

    def select_jobs(loaded: list[_Job], changed: list[str]) -> tuple[list[_Job], str]:
        (path,) = changed
        return [job for job in loaded if job.job_id in selections[path]], f"because {path}"

    for name, fn in (
        ("load_legacy_jobs", load_legacy_jobs),
        ("infer_job_scopes", infer_job_scopes),
        ("select_jobs", select_jobs),
    ):
        monkeypatch.setattr(PACK, name, fn)
    probes = [("x.html", 1, 600), ("y.py", 5, 9_000), ("z.py", 1, 1)]
    spec = {"probes": [list(probe) for probe in probes], "max_packs": 10}
    shared = PACK.packing_probe_measurements(Path(CCD.MANIFEST_REL), probes, max_packs=10)
    assert [row["packs"] for row in shared] == [2, 12, 1]

    predates = types.SimpleNamespace(
        load_legacy_jobs=load_legacy_jobs,
        infer_job_scopes=infer_job_scopes,
        select_jobs=select_jobs,
        PACK_TARGET_SECONDS=PACK.PACK_TARGET_SECONDS,
    )
    assert _worker_helpers(spec, {"scripts.run_ci_pack": predates})["_probe_rows"]() == shared
    assert _worker_helpers(spec, {"scripts.run_ci_pack": PACK})["_probe_rows"]() == shared


def test_worker_guard_rows_match_the_guards_own_findings() -> None:
    skip_rows = [
        {"test": "t1", "status": "SKIP-ONLY"},
        {"test": "t2", "status": "OK"},
        {"test": "t3", "status": "UNRUN"},
    ]

    def trigger_census(depth: int) -> list[dict]:
        return [{"test": "g", "status": "GAP", "depth": depth}, {"test": "ok", "status": "OK"}]

    predates = {
        "scripts.check_skip_only_suites": types.SimpleNamespace(census=lambda: list(skip_rows)),
        "scripts.check_ci_trigger_closure": types.SimpleNamespace(census=trigger_census),
    }
    helpers = _worker_helpers({}, predates)
    assert helpers["_skip_only_rows"]() == SKIP.skip_only_findings(skip_rows)
    assert helpers["_trigger_gap_rows"]() == TRIGGER.trigger_gap_findings(trigger_census(1))
    assert helpers["_trigger_gap_rows"]()[0]["depth"] == 1, "the gate's census depth is 1"

    canonical = _worker_helpers({}, {
        "scripts.check_skip_only_suites": types.SimpleNamespace(skip_only_findings=lambda: ["skip"]),
        "scripts.check_ci_trigger_closure": types.SimpleNamespace(trigger_gap_findings=lambda: ["gap"]),
    })
    assert canonical["_skip_only_rows"]() == ["skip"]
    assert canonical["_trigger_gap_rows"]() == ["gap"]


def test_worker_treats_only_a_missing_guard_as_predating_it() -> None:
    absent = _worker_helpers({}, {})
    assert absent["_skip_only_rows"]() is None
    assert absent["_trigger_gap_rows"]() is None
    broken = _worker_helpers({}, {
        "scripts.check_skip_only_suites": ModuleNotFoundError("No module named 'numpy'", name="numpy"),
    })
    with pytest.raises(ModuleNotFoundError):
        broken["_skip_only_rows"]()


def test_worker_control_plane_payload_carries_every_class_and_its_seconds() -> None:
    helpers = _worker_helpers({"probes": [], "max_packs": 10}, {
        "scripts.run_ci_pack": types.SimpleNamespace(
            packing_probe_measurements=lambda manifest, probes, max_packs: []
        ),
        "scripts.check_skip_only_suites": types.SimpleNamespace(skip_only_findings=lambda: []),
        "scripts.check_ci_trigger_closure": types.SimpleNamespace(trigger_gap_findings=lambda: []),
    })
    payload = helpers["_control_plane_findings"]()
    assert set(payload) == {"probes", "skip_only", "trigger_gaps", "timings"}
    assert set(payload["timings"]) == set(CCD.CONTROL_PLANE_CLASSES)


def test_head_control_plane_findings_bind_the_tree_inventory_and_the_head_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = tmp_path / "tree"
    sha = "2" * 40
    events: list[str] = []
    probe_calls: list = []

    monkeypatch.setattr(CCD, "ROOT", tree)
    monkeypatch.setattr(CCD, "_git", lambda *args, cwd: sha + "\n")

    def write_inventory(output: Path, tested_tree_sha: str, *, root: Path):
        events.append("write")
        output.write_text("fixture", encoding="utf-8")

    @contextmanager
    def activate_inventory(source: Path, tested_tree_sha: str, *, root: Path):
        events.append("enter")
        yield object()
        events.append("exit")

    def measure(manifest: Path, probes: list, *, max_packs: int) -> list[dict]:
        assert events[-1] == "enter"
        probe_calls.append((manifest, probes, max_packs))
        return [{"probe": INDEX_PROBE, "job_ids": ("b", "a")}]

    def skip_findings() -> list[dict]:
        assert events[-1] == "enter"
        return [{"test": "tests/test_x.py", "needs": ("numpy",)}]

    def gap_findings() -> list[dict]:
        assert events[-1] == "enter"
        return []

    monkeypatch.setattr(CCD, "write_tracked_path_inventory", write_inventory)
    monkeypatch.setattr(CCD, "planner_tracked_path_inventory", activate_inventory)
    monkeypatch.setattr(CCD, "packing_probe_measurements", measure)
    monkeypatch.setattr(CCD, "skip_only_findings", skip_findings)
    monkeypatch.setattr(CCD, "trigger_gap_findings", gap_findings)

    payload = CCD._head_control_plane_findings(
        {"probes": [[INDEX_PROBE, 134, 5_800]], "max_packs": 10}
    )
    assert events == ["write", "enter", "exit"]
    assert probe_calls == [
        (tree / CCD.MANIFEST_REL, [(INDEX_PROBE, 134, 5_800)], 10)
    ]
    # JSON round-tripped: tuples arrive as lists, exactly as the worker's rows do.
    assert payload["probes"] == [{"probe": INDEX_PROBE, "job_ids": ["b", "a"]}]
    assert payload["skip_only"] == [{"test": "tests/test_x.py", "needs": ["numpy"]}]
    assert payload["trigger_gaps"] == []
    assert set(payload["timings"]) == set(CCD.CONTROL_PLANE_CLASSES)
