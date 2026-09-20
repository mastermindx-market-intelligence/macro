"""Contract for scripts/check_contract_delta.py, the differential merge-train gate.

Three things are pinned here, matching the three ways this gate could quietly
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
"""
from __future__ import annotations

from contextlib import contextmanager

import json
import signal
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import check_contract_delta as CCD
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
        return {"unrun-picks-boards": ["site/theme.css"]}

    def suite_findings():
        assert events[-1][0] == "enter"
        return ["tests/test_unwired.py"]

    monkeypatch.setattr(CCD, "curated_exclusive_closure_findings", closure_findings)
    monkeypatch.setattr(CCD, "gated_unrun_suites", suite_findings)

    assert CCD._head_findings() == {
        "closure": {"unrun-picks-boards": ["site/theme.css"]},
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


def test_contract_delta_run_step_calls_the_script_with_base() -> None:
    jobs = _ci_jobs()
    job = jobs["contract-delta"]
    blob = "\n".join(
        step.get("run", "") for step in job.get("steps", []) if isinstance(step, dict)
    )
    assert "scripts/check_contract_delta.py" in blob
    assert "--base" in blob
    assert "github.event.pull_request.base.sha" in blob


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


def test_legacy_jobs_workflow_yaml_job_runs_the_new_suite() -> None:
    """This file must be wired somewhere, or audit_unrun_tests.py's own gate --
    the very lane this gate exists to make pre-mergeable -- would flag it."""
    doc = yaml.safe_load(MANIFEST.read_text())
    job = doc["jobs"]["workflow-yaml"]
    blob = "\n".join(
        step.get("run", "") for step in job.get("steps", []) if isinstance(step, dict)
    )
    assert "tests/test_contract_delta.py" in blob


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
