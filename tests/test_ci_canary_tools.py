from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from itertools import count
from pathlib import Path

import pytest
import yaml

from scripts import ci_semantic_proof as SEMANTIC
from scripts import run_ci_pack as RUN_PACK


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SELECT = load("select_ci_canary_packs", ROOT / "scripts" / "select_ci_canary_packs.py")
RESOLVE = load("resolve_ci_canary_ref", ROOT / "scripts" / "resolve_ci_canary_ref.py")
PREWARM = ROOT / "ops" / "runner-host" / "pc" / "mastermind_ci_prewarm.py"
ADMISSION = load(
    "runner_admission", ROOT / "ops" / "runner-host" / "common" / "runner_admission.py"
)
CLEANUP = load(
    "runner_cleanup", ROOT / "ops" / "runner-host" / "common" / "runner_cleanup.py"
)
RESOURCE_GUARD = load(
    "mastermind_ci_resource_guard",
    ROOT / "ops" / "runner-host" / "pc" / "mastermind_ci_resource_guard.py",
)
COMPARE = load("compare_ci_canary_receipts", ROOT / "scripts" / "compare_ci_canary_receipts.py")
CAPTURE = load("capture_ci_canary_receipt", ROOT / "scripts" / "capture_ci_canary_receipt.py")
MONITOR = load(
    "monitor_ci_host_resources", ROOT / "scripts" / "monitor_ci_host_resources.py"
)


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def cache_fixture(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init")
    git(source, "config", "user.name", "Canary Test")
    git(source, "config", "user.email", "canary@example.invalid")
    (source / "tracked.txt").write_text("cache-backed\n", encoding="utf-8")
    git(source, "add", "tracked.txt")
    git(source, "commit", "-m", "seed")
    sha = git(source, "rev-parse", "HEAD")
    cache = tmp_path / "cache.git"
    subprocess.run(["git", "clone", "--bare", str(source), str(cache)], check=True, capture_output=True)
    git(cache, "remote", "set-url", "origin", "https://github.com/mastermindx-market-intelligence/macro.git")
    (cache / ".mastermind-cache-identity.json").write_text(
        json.dumps({"schema": "mastermind.ci_git_cache.v1", "repository": "mastermindx-market-intelligence/macro"}) + "\n",
        encoding="utf-8",
    )
    for path in sorted(cache.rglob("*"), reverse=True):
        if path.is_symlink():
            continue
        mode = path.stat().st_mode
        path.chmod(mode & ~(stat.S_IWGRP | stat.S_IWOTH))
    cache.chmod(cache.stat().st_mode & ~(stat.S_IWGRP | stat.S_IWOTH))
    return cache, sha


def run_prewarm(cache: Path, workspace: Path, sha: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            str(PREWARM),
            "--cache",
            str(cache),
            "--workspace",
            str(workspace),
            "--repository",
            "mastermindx-market-intelligence/macro",
            "--repository-url",
            "https://github.com/mastermindx-market-intelligence/macro.git",
            "--base-sha",
            sha,
            "--expected-owner-uid",
            str(os.getuid()),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_shared_cache_prewarm_materializes_without_origin(tmp_path: Path) -> None:
    cache, sha = cache_fixture(tmp_path)
    workspace = tmp_path / "workspace"
    result = run_prewarm(cache, workspace, sha)
    assert result.returncode == 0, result.stdout + result.stderr
    assert git(workspace, "rev-parse", "HEAD") == sha
    assert (workspace / "tracked.txt").read_text(encoding="utf-8") == "cache-backed\n"
    assert (workspace / ".git" / "objects" / "info" / "alternates").read_text(encoding="utf-8").strip() == str((cache / "objects").resolve())


def test_missing_cache_fails_before_workspace_initialization(tmp_path: Path) -> None:
    result = run_prewarm(tmp_path / "absent.git", tmp_path / "workspace", "0" * 40)
    assert result.returncode == 66
    assert "shared cache unavailable" in result.stdout
    assert not (tmp_path / "workspace" / ".git").exists()


def test_wrong_cache_identity_fails_closed(tmp_path: Path) -> None:
    cache, sha = cache_fixture(tmp_path)
    marker = cache / ".mastermind-cache-identity.json"
    marker.chmod(0o644)
    marker.write_text(
        json.dumps({"schema": "mastermind.ci_git_cache.v1", "repository": "somewhere/else"}),
        encoding="utf-8",
    )
    result = run_prewarm(cache, tmp_path / "workspace", sha)
    assert result.returncode == 66
    assert "identity mismatch" in result.stdout


def test_selector_uses_current_weights_not_a_fixed_pack_number() -> None:
    plan = {
        "schema": SELECT._PLAN_SCHEMA,
        "packs": [
            {"index": 0, "weight": 2, "jobs": ["small"]},
            {"index": 7, "weight": 99, "jobs": ["heavy"]},
            {"index": 4, "weight": 50, "jobs": ["middle"]},
        ],
    }
    assert [item["index"] for item in SELECT.select(plan, 1)] == [7]
    assert [item["index"] for item in SELECT.select(plan, 3)] == [7, 4, 0]


def test_selector_schema_literal_matches_the_live_planner_and_refuses_a_stale_one() -> None:
    """The 2026-08-25 (#6351) defect: a hardcoded 'ci.pack_plan.v1' literal here
    rejected every plan.json the pack runner actually emits (schema
    'ci.pack_plan.v2'), so the canary's own `select` step could never
    succeed. This selector must stay a stdlib-only self-contained script (it
    is copied alone into a trusted-control directory outside the untrusted
    candidate checkout — see the comment in select_ci_canary_packs.py), so it
    cannot import scripts.ci_semantic_proof.PLAN_SCHEMA directly; pin the
    literal against the live constant here instead, and pin that a
    stale/foreign schema is still refused.
    """
    from scripts import ci_semantic_proof as SEMANTIC

    assert SELECT._PLAN_SCHEMA == SEMANTIC.PLAN_SCHEMA == "ci.pack_plan.v2"
    stale_plan = {
        "schema": "ci.pack_plan.v1",
        "packs": [{"index": 0, "weight": 1, "jobs": ["only"]}],
    }
    with pytest.raises(ValueError, match="unexpected CI plan schema"):
        SELECT.select(stale_plan, 1)


def _fragment(**overrides: object) -> dict:
    base = {
        "schema": "ci.semantic_fragment.v1",
        "workflow_run_id": "123",
        "workflow": "infrastructure-selfhosted-ci-canary",
        "event": "workflow_dispatch",
        "role": "pr_head",
        "tested_tree_sha": "a" * 40,
        "subject_head_sha": "b" * 40,
        "base_sha": "c" * 40,
        "plan_sha256": "d" * 64,
        "pack_index": 0,
        "infrastructure": [],
        "jobs": [{"logical_job_id": "demo", "outcome": "passed"}],
    }
    base.update(overrides)
    return base


def _receipt(**overrides: object) -> dict:
    base = {
        "tested_sha": "a" * 40,
        "base_sha": "c" * 40,
        "pack": 0,
        "plan_sha256": "d" * 64,
        "logical_jobs": ["demo"],
        "executed_jobs": ["demo"],
        "failed_jobs": [],
        "result": "passed",
    }
    base.update(overrides)
    return base


def test_compare_never_touches_merge_authority_reconciliation() -> None:
    """Diagnostic-only comparator (#6351 spec C.6): this workflow never calls
    scripts.merge_on_green, and the comparator must never import
    ci_semantic_proof.reconcile_evidence or any other merge-gating entry
    point — only the pure canonicalization helpers.
    """
    assert not hasattr(COMPARE, "reconcile_evidence")
    assert not hasattr(COMPARE, "merge_on_green")
    tree = ast.parse(
        (ROOT / "scripts" / "compare_ci_canary_receipts.py").read_text(encoding="utf-8")
    )
    imported_names = {
        alias.asname or alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "merge_on_green" not in imported_names
    assert "reconcile_evidence" not in imported_names


def test_compare_requires_strict_canonical_fragment_equality() -> None:
    hosted = _receipt()
    selfhosted = _receipt()
    hosted_fragment = _fragment()
    selfhosted_fragment = _fragment()
    assert COMPARE.compare(hosted, selfhosted, hosted_fragment, selfhosted_fragment) == {}

    # Identical identity, different content -> canonical digest catches it.
    diverged = _fragment(jobs=[{"logical_job_id": "demo", "outcome": "failed"}])
    mismatches = COMPARE.compare(hosted, selfhosted, hosted_fragment, diverged)
    assert "fragment_canonical_sha256" in mismatches


def test_compare_flags_fragment_identity_mismatch_before_the_digest() -> None:
    hosted = _receipt()
    selfhosted = _receipt()
    hosted_fragment = _fragment()
    wrong_identity = _fragment(tested_tree_sha="f" * 40)
    mismatches = COMPARE.compare(hosted, selfhosted, hosted_fragment, wrong_identity)
    assert "fragment_tested_tree_sha" in mismatches
    # Identity validation happens FIRST and short-circuits the byte compare.
    assert "fragment_canonical_sha256" not in mismatches


def test_compare_flags_wrong_fragment_schema() -> None:
    hosted = _receipt()
    selfhosted = _receipt()
    hosted_fragment = _fragment()
    bad_schema = _fragment(schema="ci.semantic_fragment.v0")
    mismatches = COMPARE.compare(hosted, selfhosted, hosted_fragment, bad_schema)
    assert "selfhosted_fragment_schema" in mismatches


def test_compare_cross_checks_fragment_identity_against_the_receipt() -> None:
    hosted = _receipt(tested_sha="a" * 40)
    selfhosted = _receipt(tested_sha="a" * 40)
    hosted_fragment = _fragment(tested_tree_sha="e" * 40)
    selfhosted_fragment = _fragment(tested_tree_sha="e" * 40)
    mismatches = COMPARE.compare(hosted, selfhosted, hosted_fragment, selfhosted_fragment)
    assert mismatches == {
        "fragment_receipt_identity": {
            "hosted_fragment_tested_tree_sha": "e" * 40,
            "hosted_receipt_tested_sha": "a" * 40,
        }
    }


def test_capture_receipt_records_fragment_reference_and_bumps_schema(tmp_path: Path) -> None:
    """Materialization-receipt amendment (D, #6351): the receipt now carries
    a v2 schema and a reference to the semantic fragment the same pack
    invocation emitted, so a reader can cross-check receipt identity
    against fragment identity without re-deriving it.
    """
    plan = {"plan_sha256": "d" * 64, "packs": [{"index": 0, "jobs": ["demo"]}]}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    log_path = tmp_path / "pack.log"
    log_path.write_text("::group::demo — proof\nok\nCI_PACK_FAILED_JOBS=[]\n", encoding="utf-8")
    fragment_path = tmp_path / "fragment.json"
    fragment_path.write_text(
        json.dumps({"schema": "ci.semantic_fragment.v1", "plan_sha256": "d" * 64}),
        encoding="utf-8",
    )
    output_path = tmp_path / "receipt.json"
    result = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "capture_ci_canary_receipt.py"),
            "--log", str(log_path),
            "--plan", str(plan_path),
            "--pack", "0",
            "--exit-code", "0",
            "--tested-sha", "a" * 40,
            "--base-sha", "b" * 40,
            "--runner-kind", "selfhosted",
            "--runner-name", "test-runner",
            "--fragment", str(fragment_path),
            "--output", str(output_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(output_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "ci.selfhosted_canary_receipt.v2"
    assert receipt["fragment_schema"] == "ci.semantic_fragment.v1"
    assert receipt["fragment_plan_sha256"] == "d" * 64
    assert receipt["prewarm_seconds"] is None


def test_capture_receipt_tolerates_a_missing_fragment_reference(tmp_path: Path) -> None:
    plan = {"plan_sha256": "d" * 64, "packs": [{"index": 0, "jobs": ["demo"]}]}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    log_path = tmp_path / "pack.log"
    log_path.write_text("ok\n", encoding="utf-8")
    output_path = tmp_path / "receipt.json"
    result = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "capture_ci_canary_receipt.py"),
            "--log", str(log_path),
            "--plan", str(plan_path),
            "--pack", "0",
            "--exit-code", "0",
            "--tested-sha", "a" * 40,
            "--base-sha", "b" * 40,
            "--runner-kind", "hosted",
            "--runner-name", "test-runner",
            "--output", str(output_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(output_path.read_text(encoding="utf-8"))
    assert receipt["fragment_schema"] is None
    assert receipt["fragment_plan_sha256"] is None


def test_capture_enriches_non_authoritative_execution_timing(
    tmp_path: Path,
) -> None:
    tested = "a" * 40
    head = tested
    base = tested
    plan = RUN_PACK.plan_from_workflow(
        ROOT / ".github" / "ci" / "legacy-jobs.yml",
        changed_from=None,
        scope_mode="active",
        pack_count=12,
        changed_files_file=None,
        workflow_run_id="123",
        workflow_name="ci",
        event="workflow_dispatch",
        role="main",
        tested_tree_sha=tested,
        subject_head_sha=head,
        base_sha=base,
        gate="code",
    )
    pack_index = next(
        index for index, jobs in enumerate(plan.pack_jobs) if len(jobs) > 1
    )
    selected = list(plan.pack_jobs[pack_index])
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan.to_dict()), encoding="utf-8")
    log_path = tmp_path / "pack.log"
    log_path.write_text("CI_PACK_FAILED_JOBS=[]\n", encoding="utf-8")
    observations_path = tmp_path / "observations.jsonl"
    observations_path.write_text(
        json.dumps(
            {
                "logical_job_id": selected[0],
                "phase": "dependency_install",
                "status": "observed",
                "started_monotonic_ns": 100,
                "ended_monotonic_ns": 130,
                "duration_ns": 30,
            }
        )
        + "\n"
        + json.dumps(
            {
                "logical_job_id": selected[0],
                "phase": "test",
                "status": "observed",
                "started_monotonic_ns": 140,
                "ended_monotonic_ns": 200,
                "duration_ns": 60,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    phase_path = tmp_path / "phase-monotonic.txt"
    phase_path.write_text(
        "job_start 10\n"
        "checkout_start 20\n"
        "checkout_end 30\n"
        "executor_setup_start 31\n"
        "executor_setup_end 40\n"
        "pack_execution_start 41\n"
        "pack_execution_end 70\n"
        "job_end 80\n",
        encoding="utf-8",
    )
    receipt_path = tmp_path / "receipt.json"
    timing_path = tmp_path / "execution-timing.jsonl"
    env = {
        **os.environ,
        "GITHUB_REPOSITORY": "mastermindx-market-intelligence/macro",
        "GITHUB_RUN_ATTEMPT": "2",
    }
    result = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "capture_ci_canary_receipt.py"),
            "--log", str(log_path),
            "--plan", str(plan_path),
            "--pack", str(pack_index),
            "--exit-code", "0",
            "--tested-sha", tested,
            "--base-sha", base,
            "--runner-kind", "selfhosted",
            "--runner-name", "pc-ci-1",
            "--runner-profile", RUN_PACK.RUNNER_CONTRACT,
            "--timing-observations", str(observations_path),
            "--phase-monotonic", str(phase_path),
            "--timing-output", str(timing_path),
            "--output", str(receipt_path),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    rows = [
        json.loads(line)
        for line in timing_path.read_text(encoding="utf-8").splitlines()
    ]
    assert rows
    expected_identity = {
        "schema": "ci.execution_timing.v1",
        "repository": "mastermindx-market-intelligence/macro",
        "workflow_run_id": "123",
        "workflow_run_attempt": 2,
        "subject_head_sha": head,
        "base_sha": base,
        "tested_tree_sha": tested,
        "plan_sha256": plan.plan_sha256,
        "pack_index": pack_index,
        "runner_kind": "selfhosted",
        "runner_name": "pc-ci-1",
        "runner_profile": RUN_PACK.RUNNER_CONTRACT,
    }
    assert all(
        {key: row[key] for key in expected_identity} == expected_identity
        for row in rows
    )
    by_phase = {(row["logical_job_id"], row["phase"]): row for row in rows}
    assert by_phase[(None, "queue")]["status"] == "missing"
    assert by_phase[(None, "checkout")]["duration_ns"] == 10
    assert by_phase[(None, "executor_setup")]["duration_ns"] == 9
    assert by_phase[(None, "pack_execution")]["duration_ns"] == 29
    assert by_phase[(None, "pack_completion")]["duration_ns"] == 70
    assert by_phase[(selected[0], "dependency_install")]["duration_ns"] == 30
    assert by_phase[(selected[0], "test")]["duration_ns"] == 60
    assert all(
        by_phase[(job_id, phase)]["status"] in {"observed", "missing"}
        for job_id in selected
        for phase in ("dependency_install", "test")
    )

    with pytest.raises(SEMANTIC.SemanticProofError, match="plan schema"):
        SEMANTIC._expected_plan(rows[0])
    with pytest.raises(SEMANTIC.SemanticProofError, match="fragment schema"):
        SEMANTIC.reconcile_evidence(plan.to_dict(), [rows[0]])
    with pytest.raises(SEMANTIC.SemanticProofError, match="evidence schema"):
        SEMANTIC._validate_evidence(rows[0])


def test_malformed_timing_degrades_without_changing_the_receipt(
    tmp_path: Path,
) -> None:
    tested = "a" * 40
    plan = {
        "workflow_run_id": "123",
        "tested_tree_sha": tested,
        "subject_head_sha": tested,
        "base_sha": tested,
        "plan_sha256": "d" * 64,
        "packs": [{"index": 0, "jobs": ["demo"]}],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    log_path = tmp_path / "pack.log"
    log_path.write_text("CI_PACK_FAILED_JOBS=[]\n", encoding="utf-8")
    empty_observations = tmp_path / "empty-observations.jsonl"
    empty_observations.write_text("", encoding="utf-8")
    reversed_phase = tmp_path / "reversed-phase-monotonic.txt"
    reversed_phase.write_text(
        "job_start 80\n"
        "checkout_start 30\n"
        "checkout_end 20\n"
        "executor_setup_start 40\n"
        "executor_setup_end 31\n"
        "pack_execution_start 70\n"
        "pack_execution_end 41\n"
        "job_end 10\n",
        encoding="utf-8",
    )
    baseline_receipt = tmp_path / "baseline-receipt.json"
    degraded_receipt = tmp_path / "degraded-receipt.json"
    timing_path = tmp_path / "execution-timing.jsonl"
    common = [
        "python3",
        str(ROOT / "scripts" / "capture_ci_canary_receipt.py"),
        "--log", str(log_path),
        "--plan", str(plan_path),
        "--pack", "0",
        "--exit-code", "0",
        "--tested-sha", tested,
        "--base-sha", tested,
        "--runner-kind", "selfhosted",
        "--runner-name", "pc-ci-1",
        "--runner-profile", RUN_PACK.RUNNER_CONTRACT,
    ]
    baseline = subprocess.run(
        [*common, "--output", str(baseline_receipt)],
        text=True,
        capture_output=True,
        check=False,
    )
    degraded = subprocess.run(
        [
            *common,
            "--timing-observations", str(empty_observations),
            "--phase-monotonic", str(reversed_phase),
            "--timing-output", str(timing_path),
            "--output", str(degraded_receipt),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    assert degraded.returncode == 0, degraded.stdout + degraded.stderr
    assert degraded_receipt.read_bytes() == baseline_receipt.read_bytes()
    assert "::warning title=ci timing telemetry degraded::" in degraded.stdout
    rows = [
        json.loads(line)
        for line in timing_path.read_text(encoding="utf-8").splitlines()
    ]
    assert rows
    assert all(row["status"] == "missing" for row in rows)
    assert {(row["logical_job_id"], row["phase"]) for row in rows} == {
        (None, "queue"),
        (None, "checkout"),
        (None, "executor_setup"),
        (None, "pack_execution"),
        (None, "pack_completion"),
        ("demo", "dependency_install"),
        ("demo", "test"),
    }


def _assert_invalid_raw_timing_is_non_authoritative(
    tmp_path: Path,
    raw_observations: bytes,
) -> None:
    """Run the receipt CLI against a malformed raw timing sidecar.

    A timing-input rejection must leave the already-established canary receipt
    and its passed pack verdict byte-for-byte untouched, while still producing
    a complete missing-row sidecar when the final timing destination works.
    """
    tested = "a" * 40
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "workflow_run_id": "123",
                "tested_tree_sha": tested,
                "subject_head_sha": tested,
                "base_sha": tested,
                "plan_sha256": "d" * 64,
                "packs": [{"index": 0, "jobs": ["demo"]}],
            }
        ),
        encoding="utf-8",
    )
    log_path = tmp_path / "pack.log"
    log_path.write_text("CI_PACK_FAILED_JOBS=[]\n", encoding="utf-8")
    observations_path = tmp_path / "observations.jsonl"
    observations_path.write_bytes(raw_observations)
    phase_path = tmp_path / "phase-monotonic.txt"
    phase_path.write_text(
        "job_start 10\n"
        "checkout_start 20\n"
        "checkout_end 30\n"
        "executor_setup_start 31\n"
        "executor_setup_end 40\n"
        "pack_execution_start 41\n"
        "pack_execution_end 70\n"
        "job_end 80\n",
        encoding="utf-8",
    )
    baseline_receipt = tmp_path / "baseline-receipt.json"
    degraded_receipt = tmp_path / "degraded-receipt.json"
    timing_path = tmp_path / "execution-timing.jsonl"
    common = [
        sys.executable,
        str(ROOT / "scripts" / "capture_ci_canary_receipt.py"),
        "--log", str(log_path),
        "--plan", str(plan_path),
        "--pack", "0",
        "--exit-code", "0",
        "--tested-sha", tested,
        "--base-sha", tested,
        "--runner-kind", "selfhosted",
        "--runner-name", "pc-ci-1",
        "--runner-profile", RUN_PACK.RUNNER_CONTRACT,
    ]
    baseline = subprocess.run(
        [*common, "--output", str(baseline_receipt)],
        text=True,
        capture_output=True,
        check=False,
    )
    degraded = subprocess.run(
        [
            *common,
            "--timing-observations", str(observations_path),
            "--phase-monotonic", str(phase_path),
            "--timing-output", str(timing_path),
            "--output", str(degraded_receipt),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    assert degraded.returncode == 0, degraded.stdout + degraded.stderr
    assert degraded_receipt.read_bytes() == baseline_receipt.read_bytes()
    assert json.loads(degraded_receipt.read_text(encoding="utf-8"))["result"] == "passed"
    assert "::warning title=ci timing telemetry degraded::" in degraded.stdout
    rows = [
        json.loads(line)
        for line in timing_path.read_text(encoding="utf-8").splitlines()
    ]
    assert {(row["logical_job_id"], row["phase"]) for row in rows} == {
        (None, "queue"),
        (None, "checkout"),
        (None, "executor_setup"),
        (None, "pack_execution"),
        (None, "pack_completion"),
        ("demo", "dependency_install"),
        ("demo", "test"),
    }
    by_phase = {(row["logical_job_id"], row["phase"]): row for row in rows}
    assert all(
        by_phase[("demo", phase)]["status"] == "missing"
        for phase in ("dependency_install", "test")
    )


def test_duplicate_raw_timing_observations_degrade_without_receipt_or_verdict_impact(
    tmp_path: Path,
) -> None:
    observation = {
        "logical_job_id": "demo",
        "phase": "test",
        "status": "observed",
        "started_monotonic_ns": 100,
        "ended_monotonic_ns": 130,
        "duration_ns": 30,
    }
    _assert_invalid_raw_timing_is_non_authoritative(
        tmp_path,
        (json.dumps(observation) + "\n" + json.dumps(observation) + "\n").encode(),
    )


def test_oversized_raw_timing_observations_degrade_without_receipt_or_verdict_impact(
    tmp_path: Path,
) -> None:
    _assert_invalid_raw_timing_is_non_authoritative(
        tmp_path,
        b"x" * (4 * 1024 * 1024 + 1),
    )


def test_deeply_nested_raw_timing_json_degrades_without_receipt_or_verdict_impact(
    tmp_path: Path,
) -> None:
    _assert_invalid_raw_timing_is_non_authoritative(
        tmp_path,
        b"[" * 10_000 + b"0" + b"]" * 10_000 + b"\n",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [("logical_job_id", []), ("phase", {})],
    ids=("non-hashable-logical-job-id", "non-hashable-phase"),
)
def test_non_hashable_raw_timing_fields_degrade_without_receipt_or_verdict_impact(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    observation = {
        "logical_job_id": "demo",
        "phase": "test",
        "status": "observed",
        "started_monotonic_ns": 100,
        "ended_monotonic_ns": 130,
        "duration_ns": 30,
    }
    observation[field] = value
    _assert_invalid_raw_timing_is_non_authoritative(
        tmp_path,
        (json.dumps(observation) + "\n").encode(),
    )


def test_unwritable_final_timing_output_degrades_without_receipt_or_verdict_impact(
    tmp_path: Path,
) -> None:
    tested = "a" * 40
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "workflow_run_id": "123",
                "tested_tree_sha": tested,
                "subject_head_sha": tested,
                "base_sha": tested,
                "plan_sha256": "d" * 64,
                "packs": [{"index": 0, "jobs": ["demo"]}],
            }
        ),
        encoding="utf-8",
    )
    log_path = tmp_path / "pack.log"
    log_path.write_text("CI_PACK_FAILED_JOBS=[]\n", encoding="utf-8")
    baseline_receipt = tmp_path / "baseline-receipt.json"
    degraded_receipt = tmp_path / "degraded-receipt.json"
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("not a directory\n", encoding="utf-8")
    common = [
        "python3",
        str(ROOT / "scripts" / "capture_ci_canary_receipt.py"),
        "--log", str(log_path),
        "--plan", str(plan_path),
        "--pack", "0",
        "--exit-code", "0",
        "--tested-sha", tested,
        "--base-sha", tested,
        "--runner-kind", "selfhosted",
        "--runner-name", "pc-ci-1",
        "--runner-profile", RUN_PACK.RUNNER_CONTRACT,
    ]
    baseline = subprocess.run(
        [*common, "--output", str(baseline_receipt)],
        text=True,
        capture_output=True,
        check=False,
    )
    degraded = subprocess.run(
        [
            *common,
            "--timing-output", str(blocked_parent / "execution-timing.jsonl"),
            "--output", str(degraded_receipt),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    assert degraded.returncode == 0, degraded.stdout + degraded.stderr
    assert degraded_receipt.read_bytes() == baseline_receipt.read_bytes()
    assert json.loads(degraded_receipt.read_text(encoding="utf-8"))["result"] == "passed"
    assert "::warning title=ci timing telemetry degraded::" in degraded.stdout


def test_trusted_executor_publishes_timing_without_gate_authority() -> None:
    executor = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "trusted-ci-executor.yml").read_text(
            encoding="utf-8"
        )
    )
    steps = executor["jobs"]["trusted-pack"]["steps"]
    execute = next(
        step
        for step in steps
        if step.get("name") == "execute the frozen logical pack and retain its actual result"
    )
    receipt = next(
        step
        for step in steps
        if step.get("name") == "write trusted self-hosted receipt"
    )
    timing_upload = next(
        step
        for step in steps
        if step.get("name") == "publish non-authoritative execution timing"
    )
    marker_lines = [
        line.strip()
        for step in steps
        if isinstance(step, dict)
        for line in str(step.get("run", "")).splitlines()
        if "time.monotonic_ns()" in line
    ]
    for marker in (
        "job_start",
        "checkout_start",
        "checkout_end",
        "executor_setup_start",
        "executor_setup_end",
        "pack_execution_start",
        "pack_execution_end",
        "job_end",
    ):
        assert any(marker in line for line in marker_lines)
    assert all(line.endswith("|| true") for line in marker_lines)
    assert "--emit-timing-observations" in execute["run"]
    assert "--timing-observations" in receipt["run"]
    assert "--phase-monotonic" in receipt["run"]
    assert "--timing-output" in receipt["run"]
    assert timing_upload["if"] == "always()"
    assert timing_upload["continue-on-error"] is True
    assert timing_upload["timeout-minutes"] == 5
    assert timing_upload["with"]["if-no-files-found"] == "warn"
    assert timing_upload["with"]["name"] == (
        "trusted-ci-execution-timing-${{ matrix.pack }}"
    )
    required_artifact_indices = [
        index
        for index, step in enumerate(steps)
        if step.get("with", {}).get("name")
        in {
            "trusted-ci-receipt-${{ matrix.pack }}",
            "trusted-ci-fragment-${{ matrix.pack }}",
        }
    ]
    timing_index = steps.index(timing_upload)
    assert len(required_artifact_indices) == 2
    assert all(index < timing_index for index in required_artifact_indices)

    ci = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    gate = json.dumps(ci["jobs"]["ci-gate"], sort_keys=True)
    assert "execution-timing" not in gate
    assert "timing-observations" not in gate


def test_main_dispatch_freezes_parent_as_the_changed_from_base(monkeypatch) -> None:
    tested = "a" * 40
    parent = "b" * 40

    def fake_git(*args: str) -> str:
        assert args[0] == "rev-parse"
        return tested if args[1].endswith("^{commit}") else parent

    monkeypatch.setattr(RESOLVE, "git", fake_git)
    result = RESOLVE.resolve("mastermindx-market-intelligence/macro", tested, 0, "")
    assert result["tested_ref"] == tested
    assert result["tested_sha"] == tested
    assert result["base_sha"] == parent
    assert result["head_ref"] == "main"
    assert result["contamination_sha"] == parent


def test_pr_dispatch_uses_the_fetched_merge_parent_when_api_base_is_stale(
    monkeypatch,
) -> None:
    """The merge ref is the tested tree; its first parent is its tested base.

    GitHub's pull-request ``base.sha`` can lag the first parent of the current
    synthetic merge ref while the PR head and immutable merge SHA remain exact.
    """
    merge = "a" * 40
    tested_base = "b" * 40
    head = "c" * 40
    stale_api_base = "d" * 40
    monkeypatch.setattr(
        RESOLVE,
        "pull_request",
        lambda *_: {
            "state": "open",
            "merge_commit_sha": merge,
            "base": {"ref": "main", "sha": stale_api_base},
            "head": {
                "ref": "codex/ci-p3bb-production-route-6351",
                "sha": head,
                "repo": {"full_name": "mastermindx-market-intelligence/macro"},
            },
        },
    )

    def fake_git(*args: str) -> str:
        if args[0] == "fetch":
            return ""
        if args[0] == "check-ref-format":
            return args[2]
        revisions = {
            "refs/ci-canary/pull/7/merge^{commit}": merge,
            f"{merge}^1": tested_base,
            f"{merge}^2": head,
        }
        return revisions[args[1]]

    monkeypatch.setattr(RESOLVE, "git", fake_git)
    result = RESOLVE.resolve(
        "mastermindx-market-intelligence/macro", "e" * 40, 7, "token"
    )
    assert result["tested_sha"] == merge
    assert result["base_sha"] == tested_base
    assert result["head_sha"] == head
    assert result["head_ref"] == "codex/ci-p3bb-production-route-6351"
    assert result["contamination_sha"] == tested_base


def test_pr_dispatch_requires_fetched_merge_sha_and_head_to_match_api(monkeypatch) -> None:
    merge = "a" * 40
    base = "b" * 40
    head = "c" * 40
    monkeypatch.setattr(
        RESOLVE,
        "pull_request",
        lambda *_: {
            "state": "open",
            "merge_commit_sha": merge,
            "base": {"ref": "main", "sha": base},
            "head": {
                "ref": "codex/ci-p3bb-production-route-6351",
                "sha": head,
                "repo": {"full_name": "mastermindx-market-intelligence/macro"},
            },
        },
    )

    def fake_git(*args: str) -> str:
        if args[0] == "fetch":
            return ""
        if args[0] == "check-ref-format":
            return args[2]
        revisions = {
            "refs/ci-canary/pull/7/merge^{commit}": merge,
            f"{merge}^1": base,
            f"{merge}^2": head,
        }
        return revisions[args[1]]

    monkeypatch.setattr(RESOLVE, "git", fake_git)
    result = RESOLVE.resolve(
        "mastermindx-market-intelligence/macro", "d" * 40, 7, "token"
    )
    assert result["tested_sha"] == merge
    assert result["base_sha"] == base
    assert result["head_sha"] == head

    monkeypatch.setattr(RESOLVE, "git", lambda *args: "e" * 40 if args[0] != "fetch" else "")
    try:
        RESOLVE.resolve("mastermindx-market-intelligence/macro", "d" * 40, 7, "token")
    except RESOLVE.ResolutionError as exc:
        assert "merge" in str(exc)
    else:
        raise AssertionError("mismatched merge/API parents must fail closed")


REPO = "mastermindx-market-intelligence/macro"
MERGE_SHA = "a" * 40
PR_HEAD_SHA = "c" * 40
PRE_MERGE_MAIN = "b" * 40


def _merged_pr(**overrides: object) -> dict[str, object]:
    """PR #7203's shape after its mid-run merge (2026-09-16, run 35073695150)."""
    payload: dict[str, object] = {
        "state": "closed",
        "merged_at": "2026-09-16T08:27:45Z",
        "merge_commit_sha": MERGE_SHA,
        "commits": 3,
        "base": {"ref": "main", "sha": "d" * 40},
        "head": {
            "ref": "claude/astra-fabric-packet-2026-09-16",
            "sha": PR_HEAD_SHA,
            "repo": {"full_name": REPO},
        },
    }
    payload.update(overrides)
    return payload


def _merged_git(
    calls: list[tuple[str, ...]],
    *,
    parents: tuple[str, ...],
    shallow: str = "true",
    walked_base: str = PRE_MERGE_MAIN,
    fetched: str = MERGE_SHA,
):
    def fake_git(*args: str) -> str:
        calls.append(args)
        if args[0] == "fetch":
            return ""
        if args[0] == "check-ref-format":
            return args[2]
        if args == ("rev-parse", "--is-shallow-repository"):
            return shallow
        if args[0] == "rev-list":
            assert args[1:4] == ("--parents", "-n", "1")
            return " ".join([args[4], *parents])
        if args[0] == "rev-parse" and args[1] == "refs/ci-canary/pull/7/merged^{commit}":
            return fetched
        if args[0] == "rev-parse" and args[1] == f"{MERGE_SHA}~3":
            return walked_base
        raise AssertionError(f"unexpected git call {args!r}")

    return fake_git


def _on_main(*_: object) -> dict[str, object]:
    return {"status": "ahead", "ahead_by": 12, "behind_by": 0}


def test_open_pr_keeps_the_synthetic_merge_ref_and_never_consults_compare(
    monkeypatch,
) -> None:
    merge = "a" * 40
    monkeypatch.setattr(
        RESOLVE,
        "pull_request",
        lambda *_: {
            "state": "open",
            "merged_at": None,
            "merge_commit_sha": merge,
            "base": {"ref": "main", "sha": "d" * 40},
            "head": {"ref": "claude/open", "sha": PR_HEAD_SHA, "repo": {"full_name": REPO}},
        },
    )

    def refuse_compare(*_: object) -> dict[str, object]:
        raise AssertionError("an open PR must never consult the compare endpoint")

    monkeypatch.setattr(RESOLVE, "compare_commits", refuse_compare)
    calls: list[tuple[str, ...]] = []

    def fake_git(*args: str) -> str:
        calls.append(args)
        if args[0] == "fetch":
            return ""
        if args[0] == "check-ref-format":
            return args[2]
        return {
            "refs/ci-canary/pull/7/merge^{commit}": merge,
            f"{merge}^1": PRE_MERGE_MAIN,
            f"{merge}^2": PR_HEAD_SHA,
        }[args[1]]

    monkeypatch.setattr(RESOLVE, "git", fake_git)
    result = RESOLVE.resolve(REPO, "e" * 40, 7, "token")
    assert result["source_kind"] == "same-repository-pr-merge"
    assert result["tested_ref"] == "refs/pull/7/merge"
    assert result["tested_sha"] == merge
    assert result["base_sha"] == result["contamination_sha"] == PRE_MERGE_MAIN
    assert ("fetch", "--no-tags", "origin", "+refs/pull/7/merge:refs/ci-canary/pull/7/merge") in calls
    assert not any(args[0] == "rev-list" for args in calls)


def test_merged_pr_resolves_to_its_merge_commit_on_main(monkeypatch) -> None:
    """A PR merged after its run began is tested at the exact commit that landed.

    Squash and rebase both leave a single-parent merge commit; the base walks
    back the PR's frozen commit count so a rebase lands on the pre-merge main
    tip exactly and a squash over-reaches, never under-reaches.
    """
    monkeypatch.setattr(RESOLVE, "pull_request", lambda *_: _merged_pr())
    compared: list[tuple[str, ...]] = []

    def compare(*args: str) -> dict[str, object]:
        compared.append(args)
        return _on_main()

    monkeypatch.setattr(RESOLVE, "compare_commits", compare)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(RESOLVE, "git", _merged_git(calls, parents=(PRE_MERGE_MAIN[:20] + "f" * 20,)))
    result = RESOLVE.resolve(REPO, "e" * 40, 7, "token")
    assert result == {
        "source_kind": "same-repository-pr-merged",
        "tested_ref": MERGE_SHA,
        "tested_sha": MERGE_SHA,
        "base_sha": PRE_MERGE_MAIN,
        "head_sha": PR_HEAD_SHA,
        "head_ref": "claude/astra-fabric-packet-2026-09-16",
        "contamination_sha": PRE_MERGE_MAIN,
    }
    assert compared == [(REPO, MERGE_SHA, "main", "token")]
    fetch = next(args for args in calls if args[0] == "fetch")
    assert fetch == (
        "fetch", "--no-tags", "--depth=4", "origin",
        f"+{MERGE_SHA}:refs/ci-canary/pull/7/merged",
    )
    assert calls.index(fetch) > calls.index(("check-ref-format", "--branch", "claude/astra-fabric-packet-2026-09-16"))
    assert ("rev-parse", f"{MERGE_SHA}~3") in calls
    assert not any("refs/pull/7/merge" in " ".join(args) for args in calls)


def test_merged_single_commit_pr_uses_the_merge_commit_parent_without_deepening_a_full_clone(
    monkeypatch,
) -> None:
    monkeypatch.setattr(RESOLVE, "pull_request", lambda *_: _merged_pr(commits=1))
    monkeypatch.setattr(RESOLVE, "compare_commits", _on_main)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        RESOLVE, "git", _merged_git(calls, parents=(PRE_MERGE_MAIN,), shallow="false")
    )
    result = RESOLVE.resolve(REPO, "e" * 40, 7, "token")
    assert result["source_kind"] == "same-repository-pr-merged"
    assert result["base_sha"] == PRE_MERGE_MAIN
    fetch = next(args for args in calls if args[0] == "fetch")
    assert "--depth=2" not in fetch and not any(arg.startswith("--depth") for arg in fetch)
    assert not any(args[0] == "rev-parse" and "~" in args[1] for args in calls)


def test_merged_pr_merge_commit_binds_its_second_parent_to_the_frozen_head(
    monkeypatch,
) -> None:
    monkeypatch.setattr(RESOLVE, "pull_request", lambda *_: _merged_pr())
    monkeypatch.setattr(RESOLVE, "compare_commits", _on_main)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        RESOLVE, "git", _merged_git(calls, parents=(PRE_MERGE_MAIN, PR_HEAD_SHA))
    )
    result = RESOLVE.resolve(REPO, "e" * 40, 7, "token")
    assert result["base_sha"] == PRE_MERGE_MAIN
    assert not any(args[0] == "rev-parse" and "~" in args[1] for args in calls)

    monkeypatch.setattr(
        RESOLVE, "git", _merged_git([], parents=(PRE_MERGE_MAIN, "9" * 40))
    )
    with pytest.raises(RESOLVE.ResolutionError, match="second parent"):
        RESOLVE.resolve(REPO, "e" * 40, 7, "token")


def test_closed_unmerged_pr_is_refused_before_any_network_or_git_work(monkeypatch) -> None:
    monkeypatch.setattr(
        RESOLVE,
        "pull_request",
        lambda *_: _merged_pr(merged_at=None, merge_commit_sha="a" * 40),
    )

    def refuse(*_: object) -> object:
        raise AssertionError("a closed-unmerged PR must be refused before compare/git")

    monkeypatch.setattr(RESOLVE, "compare_commits", refuse)
    monkeypatch.setattr(RESOLVE, "git", refuse)
    with pytest.raises(RESOLVE.ResolutionError, match=r"#7 is not open \(state=closed, not merged\)"):
        RESOLVE.resolve(REPO, "e" * 40, 7, "token")


def test_merged_pr_whose_merge_commit_is_not_on_main_is_refused_before_fetching(
    monkeypatch,
) -> None:
    monkeypatch.setattr(RESOLVE, "pull_request", lambda *_: _merged_pr())
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(RESOLVE, "git", _merged_git(calls, parents=(PRE_MERGE_MAIN,)))
    for relation in (
        {"status": "diverged", "ahead_by": 3, "behind_by": 1},
        {"status": "behind", "ahead_by": 0, "behind_by": 1},
        {"status": "ahead", "ahead_by": 3},
        {},
    ):
        monkeypatch.setattr(RESOLVE, "compare_commits", lambda *_, r=relation: r)
        with pytest.raises(RESOLVE.ResolutionError, match="not reachable on main"):
            RESOLVE.resolve(REPO, "e" * 40, 7, "token")
    assert not any(args[0] in {"fetch", "rev-list"} for args in calls)


def test_merged_pr_keeps_every_existing_refusal(monkeypatch) -> None:
    monkeypatch.setattr(RESOLVE, "compare_commits", _on_main)
    monkeypatch.setattr(RESOLVE, "git", _merged_git([], parents=(PRE_MERGE_MAIN,)))
    cases = [
        (
            _merged_pr(head={"ref": "x", "sha": PR_HEAD_SHA, "repo": {"full_name": "fork/macro"}}),
            "not same-repository",
        ),
        (_merged_pr(base={"ref": "release", "sha": "d" * 40}), "does not target main"),
        (_merged_pr(merge_commit_sha=""), "no 40-character merge commit SHA"),
        (_merged_pr(merge_commit_sha=None), "no 40-character merge commit SHA"),
        (_merged_pr(commits=0), "invalid commit count"),
        (_merged_pr(commits="3"), "invalid commit count"),
    ]
    for payload, message in cases:
        monkeypatch.setattr(RESOLVE, "pull_request", lambda *_, p=payload: p)
        with pytest.raises(RESOLVE.ResolutionError, match=message):
            RESOLVE.resolve(REPO, "e" * 40, 7, "token")


def test_merged_pr_fetched_commit_must_be_the_api_merge_commit(monkeypatch) -> None:
    monkeypatch.setattr(RESOLVE, "pull_request", lambda *_: _merged_pr())
    monkeypatch.setattr(RESOLVE, "compare_commits", _on_main)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        RESOLVE, "git", _merged_git(calls, parents=(PRE_MERGE_MAIN,), fetched="f" * 40)
    )
    with pytest.raises(RESOLVE.ResolutionError, match="does not match the API merge commit"):
        RESOLVE.resolve(REPO, "e" * 40, 7, "token")
    assert not any(args[0] == "rev-list" for args in calls)


def test_host_admission_accepts_only_the_main_dispatch_canary() -> None:
    allowed = {
        "MASTERMIND_CI_PROFILE": "pc-ci",
        "GITHUB_REPOSITORY": "mastermindx-market-intelligence/macro",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": (
            "mastermindx-market-intelligence/macro/.github/workflows/"
            "selfhosted-ci-canary.yml@refs/heads/main"
        ),
        "GITHUB_JOB": "selfhosted-pack",
    }
    assert ADMISSION.decision(allowed)[0]
    for key, value in (
        ("GITHUB_EVENT_NAME", "pull_request"),
        ("GITHUB_REF", "refs/pull/7/merge"),
        ("GITHUB_WORKFLOW_REF", "mastermindx-market-intelligence/macro/.github/workflows/rogue.yml@refs/heads/main"),
        ("GITHUB_REPOSITORY", "attacker/fork"),
    ):
        mutated = {**allowed, key: value}
        assert not ADMISSION.decision(mutated)[0]


def test_host_admission_accepts_exact_main_four_slot_preflight_only() -> None:
    allowed = {
        "MASTERMIND_CI_PROFILE": "pc-ci",
        "GITHUB_REPOSITORY": "mastermindx-market-intelligence/macro",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": (
            "mastermindx-market-intelligence/macro/.github/workflows/"
            "selfhosted-ci-canary.yml@refs/heads/main"
        ),
        "GITHUB_JOB": "four-slot-preflight",
    }
    assert ADMISSION.decision(allowed)[0]

    for key, value in (
        ("MASTERMIND_CI_PROFILE", "pc-render"),
        ("GITHUB_REPOSITORY", "attacker/fork"),
        ("GITHUB_EVENT_NAME", "pull_request"),
        ("GITHUB_REF", "refs/heads/candidate"),
        (
            "GITHUB_WORKFLOW_REF",
            "mastermindx-market-intelligence/macro/.github/workflows/"
            "selfhosted-ci-canary.yml@refs/heads/candidate",
        ),
        ("GITHUB_JOB", "four-slot-preflight-shadow"),
    ):
        assert not ADMISSION.decision({**allowed, key: value})[0]


def test_host_admission_accepts_only_the_main_dispatch_trusted_executor_pack() -> None:
    allowed = {
        "MASTERMIND_CI_PROFILE": "pc-ci",
        "GITHUB_REPOSITORY": "mastermindx-market-intelligence/macro",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": (
            "mastermindx-market-intelligence/macro/.github/workflows/"
            "trusted-ci-executor.yml@refs/heads/main"
        ),
        "GITHUB_JOB": "trusted-pack",
    }
    assert ADMISSION.decision(allowed)[0]
    for key, value in (
        ("GITHUB_EVENT_NAME", "workflow_call"),
        ("GITHUB_REF", "refs/pull/7/merge"),
        (
            "GITHUB_WORKFLOW_REF",
            "mastermindx-market-intelligence/macro/.github/workflows/"
            "trusted-ci-executor.yml@refs/heads/candidate",
        ),
        (
            "GITHUB_WORKFLOW_REF",
            "mastermindx-market-intelligence/macro/.github/workflows/"
            "hostile-main-caller.yml@refs/heads/main",
        ),
        ("GITHUB_REPOSITORY", "attacker/fork"),
        ("GITHUB_JOB", "rogue-pack"),
    ):
        mutated = {**allowed, key: value}
        assert not ADMISSION.decision(mutated)[0]


def test_host_admission_accepts_only_main_gated_same_repo_pr_executor_pack(
    tmp_path: Path,
) -> None:
    pr_number = "6505"
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "base": {"ref": "main"},
                    "head": {
                        "repo": {
                            "full_name": "mastermindx-market-intelligence/macro"
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    allowed = {
        "MASTERMIND_CI_PROFILE": "pc-ci",
        "GITHUB_REPOSITORY": "mastermindx-market-intelligence/macro",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REF": f"refs/pull/{pr_number}/merge",
        "GITHUB_WORKFLOW_REF": (
            "mastermindx-market-intelligence/macro/.github/workflows/"
            f"ci.yml@refs/pull/{pr_number}/merge"
        ),
        "GITHUB_JOB": "trusted-pack",
        "GITHUB_EVENT_PATH": str(event_path),
    }
    assert ADMISSION.decision(allowed)[0]
    for key, value in (
        ("GITHUB_EVENT_NAME", "workflow_dispatch"),
        ("GITHUB_REF", "refs/pull/6506/merge"),
        (
            "GITHUB_WORKFLOW_REF",
            "mastermindx-market-intelligence/macro/.github/workflows/rogue.yml@refs/pull/6505/merge",
        ),
        ("GITHUB_JOB", "rogue-pack"),
        ("GITHUB_EVENT_PATH", str(tmp_path / "missing-event.json")),
    ):
        assert not ADMISSION.decision({**allowed, key: value})[0]

    for name, payload in (
        (
            "fork.json",
            {
                "pull_request": {
                    "base": {"ref": "main"},
                    "head": {"repo": {"full_name": "attacker/fork"}},
                }
            },
        ),
        (
            "release-base.json",
            {
                "pull_request": {
                    "base": {"ref": "release"},
                    "head": {
                        "repo": {
                            "full_name": "mastermindx-market-intelligence/macro"
                        }
                    },
                }
            },
        ),
    ):
        mutated_event = tmp_path / name
        mutated_event.write_text(json.dumps(payload), encoding="utf-8")
        assert not ADMISSION.decision(
            {**allowed, "GITHUB_EVENT_PATH": str(mutated_event)}
        )[0]


def test_cache_update_disables_automatic_maintenance() -> None:
    script = (ROOT / "ops" / "runner-host" / "pc" / "mastermind_ci_cache_update.sh").read_text(
        encoding="utf-8"
    )
    assert "fetch --no-auto-maintenance" in script
    assert "config gc.auto 0" in script
    assert "config maintenance.auto false" in script


def test_host_admission_m1_nightly_2_accepts_dispatch_and_workflow_run_options_intel() -> None:
    """AD-1T2 — the M1 runner-2 profile admits the options-intel producer on
    BOTH `workflow_dispatch` and `workflow_run`, plus the pre-existing m1
    canary tuple. Every other (event, workflow, job, ref, repository)
    mutation must be refused — that is the whole point of the profile.
    """

    base = {
        "MASTERMIND_CI_PROFILE": "m1-nightly-2",
        "GITHUB_REPOSITORY": "mastermindx-market-intelligence/macro",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": (
            "mastermindx-market-intelligence/macro/.github/workflows/"
            "options-intel.yml@refs/heads/main"
        ),
        "GITHUB_JOB": "options_intel",
    }

    for event in ("workflow_dispatch", "workflow_run"):
        allowed = {**base, "GITHUB_EVENT_NAME": event}
        assert ADMISSION.decision(allowed)[0], (
            f"m1-nightly-2 must admit options-intel via {event}"
        )

    canary = {**base, "GITHUB_EVENT_NAME": "workflow_dispatch",
              "GITHUB_WORKFLOW_REF": (
                  "mastermindx-market-intelligence/macro/.github/workflows/"
                  "m1-runner-canary.yml@refs/heads/main"
              ),
              "GITHUB_JOB": "m1-service-canary"}
    assert ADMISSION.decision(canary)[0], "m1-nightly-2 must still admit the M1 canary tuple"

    for key, value in (
        ("MASTERMIND_CI_PROFILE", "m1-canary"),
        ("GITHUB_REPOSITORY", "attacker/fork"),
        ("GITHUB_REF", "refs/pull/7/merge"),
        ("GITHUB_REF", "refs/heads/candidate"),
        ("GITHUB_WORKFLOW_REF",
         "mastermindx-market-intelligence/macro/.github/workflows/options-intel.yml@refs/heads/candidate"),
        ("GITHUB_WORKFLOW_REF",
         "mastermindx-market-intelligence/macro/.github/workflows/daily.yml@refs/heads/main"),
        ("GITHUB_WORKFLOW_REF",
         "mastermindx-market-intelligence/macro/.github/workflows/rogue.yml@refs/heads/main"),
        ("GITHUB_JOB", "rogue-producer"),
        ("GITHUB_JOB", "engine"),
        ("GITHUB_EVENT_NAME", "pull_request"),
        ("GITHUB_EVENT_NAME", "schedule"),
        ("GITHUB_EVENT_NAME", "push"),
    ):
        mutated = {**base, "GITHUB_EVENT_NAME": "workflow_dispatch", key: value}
        assert not ADMISSION.decision(mutated)[0], (
            f"m1-nightly-2 must refuse {key}={value!r}; would otherwise silently widen "
            "the store-bearing host's admission surface"
        )


def test_runner_admission_hook_js_wires_m1_nightly_2_profile() -> None:
    """The shared hook maps the m1-nightly-2 filename to its profile, and the
    script binding is the only line that selects which profile runs.
    """

    hook = (
        ROOT / "ops" / "runner-host" / "common" / "runner_admission_hook.js"
    ).read_text(encoding="utf-8")
    assert '"runner_admission_m1_nightly_2.js": "m1-nightly-2"' in hook, (
        "the m1-nightly-2 filename must map to its own profile in the shared hook"
    )
    # the shared hook profile map must NOT carry any inline guard / mutation
    # surface that would silently widen admission — its sole job is to set
    # MASTERMIND_CI_PROFILE and pass through to runner_admission.py
    assert "process.env.MASTERMIND_CI_PROFILE" not in hook
    assert "process.env.PATH" not in hook

    m1 = (ROOT / "ops" / "runner-host" / "m1" / "run_guarded_runner.sh").read_text(
        encoding="utf-8"
    )
    # the canary default is preserved for every existing M1 runner
    assert 'ACTIONS_RUNNER_HOOK_JOB_STARTED="$guard_root/runner_admission_m1_canary.js"' in m1
    assert "MASTERMIND_CI_PROFILE=m1-canary" in m1
    # and the m1-nightly-2 root now binds the new profile + hook
    assert 'runner_admission_m1_nightly_2.js' in m1
    assert "MASTERMIND_CI_PROFILE=m1-nightly-2" in m1
    # the binding is fail-closed and driven by the *configured* agentName
    # written into `.runner` by the official `config.sh` registration —
    # NEVER by the directory basename of the runner root. The M1 LaunchAgent
    # invokes the wrapper with `/Users/chriswong/actions-runner-2`, whose
    # basename is `actions-runner-2`, not `m1-nightly-2`; trusting the
    # basename here would silently leave every M1 listener on the canary
    # profile. The wrapper delegates the binding to the pure helper.
    assert 'basename "$runner_root"' not in m1
    assert '"$guard_root/runner_binding.py" "$runner_root"' in m1
    # The wrapper validates the exact `RUNNER_BINDING=` prefix, strips it
    # into `binding_payload`, and calls the helper with the rawjson +
    # key contract the helper's --extract-profile subcommand enforces.
    # Pinning this here keeps the wrapper from regressing to the previous
    # broken call that passed the prefixed line without the key (helper
    # exited 64 — wrapper would never have selected a profile).
    assert 'case "$binding_line" in' in m1
    assert 'RUNNER_BINDING=*)' in m1
    assert 'binding_payload=${binding_line#RUNNER_BINDING=}' in m1
    assert '"$guard_root/runner_binding.py" --extract-profile "$binding_payload" profile' in m1
    assert "exit 78" in m1
    # the canary default does NOT depend on any case branch against the
    # basename — the only branch is the profile-name case derived from the
    # helper's JSON output, so an additional `actions-runner-N` root
    # without a matching `(root, agentName)` pair in the helper refuses.
    assert "case \"$(basename" not in m1
    # the helper module is checked in alongside the wrapper
    assert (ROOT / "ops" / "runner-host" / "common" / "runner_binding.py").is_file()


# ── AD-1T2: runner_binding.py — fail-closed trusted-local-identity ────────────
# These tests exercise the actual helper used by run_guarded_runner.sh with
# production-shaped (canonical root, configured agentName) pairs. We do NOT
# create real `/Users/...` paths on CI: the helper's `CANONICAL_BINDINGS`
# module dict is monkey-patched to point at a `tmp_path` so the resolver
# still performs the exact-match check on real fs objects.

import plistlib  # noqa: E402  — local import keeps the module's surface stable

BINDING = load(
    "runner_binding", ROOT / "ops" / "runner-host" / "common" / "runner_binding.py"
)


def _write_runner_identity(runner_root: Path, agent_name: str) -> Path:
    """Materialise a production-shaped ``.runner`` plist at ``runner_root``.

    The real GitHub Actions runner writes ``.runner`` as an XML plist via
    ``config.sh``; ``plutil -extract agentName raw -o -`` reads it back.
    Mirror that shape here so the helper's extractor is exercised on real
    bytes, not on a fake.
    """
    runner_file = runner_root / ".runner"
    with runner_file.open("wb") as handle:
        plistlib.dump({"agentName": agent_name}, handle)
    return runner_file


@pytest.fixture
def canonical_bindings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Yield ``(canonical_root_for_m1_nightly_2, agent_name)`` and patch the
    helper's table so the production-shaped path is the tmp path.  Three
    canonical roots are wired in (m1-nightly-2, m1-nightly-1, m1-light-1) so
    every binding decision is covered without materialising /Users.
    """

    runner_2 = tmp_path / "actions-runner-2"
    runner_1 = tmp_path / "actions-runner-1"
    runner_3 = tmp_path / "actions-runner-3"
    for root in (runner_2, runner_1, runner_3):
        root.mkdir()

    monkeypatch.setitem(
        BINDING.CANONICAL_BINDINGS,
        (str(runner_2), "m1-nightly-2"),
        "m1-nightly-2",
    )
    monkeypatch.setitem(
        BINDING.CANONICAL_BINDINGS,
        (str(runner_1), "m1-nightly-1"),
        "m1-canary",
    )
    monkeypatch.setitem(
        BINDING.CANONICAL_BINDINGS,
        (str(runner_3), "m1-light-1"),
        "m1-canary",
    )
    return {
        "runner_2": runner_2,
        "runner_1": runner_1,
        "runner_3": runner_3,
        "agent_m1_nightly_2": "m1-nightly-2",
        "agent_m1_nightly_1": "m1-nightly-1",
        "agent_m1_light_1": "m1-light-1",
    }


@pytest.fixture
def portable_plutil(tmp_path: Path) -> Path:
    """Stage the portable plutil stub for tests that drive the helper
    directly (not through the wrapper harness). Pair with a
    ``monkeypatch.setattr(BINDING, "PLUTIL_BIN", str(stub))`` so the
    module's ``_plutil_agent_name`` consults the stub instead of the
    system ``/usr/bin/plutil`` (which may be absent on Linux CI).
    """
    return _stage_portable_plutil(tmp_path)


def _plutil_extract_agent_name(runner_file: str) -> str:
    """Mirror the production ``/usr/bin/plutil -extract agentName raw -o -``
    extractor so the helper is exercised against the real plist bytes written
    by :func:`_write_runner_identity`. ``plistlib`` parses XML and binary plist
    formats identically to ``plutil``.
    """
    with open(runner_file, "rb") as handle:
        document = plistlib.load(handle)
    value = document.get("agentName", "")
    assert isinstance(value, str), (
        f"plistlib parsed a non-string agentName: {value!r} from {runner_file}"
    )
    return value


def test_runner_binding_binds_production_shaped_m1_nightly_2(
    canonical_bindings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production case: ``/Users/chriswong/actions-runner-2`` with
    ``.runner`` carrying ``agentName="m1-nightly-2"`` binds the producer
    profile. RED-first on the previous (basename-based) head because the
    real runner root basename is ``actions-runner-2``, not ``m1-nightly-2``.
    """

    runner_root = canonical_bindings["runner_2"]
    _write_runner_identity(runner_root, "m1-nightly-2")

    profile, agent_name = BINDING.resolve_profile(
        str(runner_root),
        isfile=os.path.isfile,
        isdir=os.path.isdir,
        extract_agent_name=_plutil_extract_agent_name,
    )
    assert profile == "m1-nightly-2", (
        "production-shaped (root=actions-runner-2, agentName=m1-nightly-2) "
        "must bind the m1-nightly-2 producer profile"
    )
    assert agent_name == "m1-nightly-2"


def test_runner_binding_refuses_missing_runner_identity_file(
    canonical_bindings,
) -> None:
    """A runner root with no ``.runner`` file refuses (exit 78 in the
    wrapper). RED-first on the previous head: missing .runner must NOT
    silently fall back to the canary profile.
    """

    runner_root = canonical_bindings["runner_2"]
    # intentionally do NOT write a .runner file
    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            str(runner_root),
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=_plutil_extract_agent_name,
        )
    assert ".runner" in str(excinfo.value)


def test_runner_binding_refuses_malformed_runner_identity_file(
    canonical_bindings, tmp_path: Path
) -> None:
    """A ``.runner`` file the production extractor cannot parse refuses.
    RED-first: malformed .runner used to silently bind the canary profile
    because the basename of actions-runner-2 never matched the basename
    case; the new helper refuses ANY non-empty property-list parse error.
    """

    runner_root = canonical_bindings["runner_2"]
    runner_root.mkdir(exist_ok=True)
    (runner_root / ".runner").write_text("this is not a plist", encoding="utf-8")

    def malformed_extractor(_path: str) -> str:
        raise plistlib.InvalidFileException("not a plist")

    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            str(runner_root),
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=malformed_extractor,
        )
    assert "unreadable" in str(excinfo.value)


def test_runner_binding_refuses_empty_agent_name(
    canonical_bindings,
) -> None:
    """``agentName`` present but empty refuses. RED-first: the previous
    wrapper did not consult the .runner file at all.
    """

    runner_root = canonical_bindings["runner_2"]
    _write_runner_identity(runner_root, "")

    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            str(runner_root),
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=_plutil_extract_agent_name,
        )
    assert "agentName" in str(excinfo.value)


def test_runner_binding_refuses_other_root_claiming_m1_nightly_2(
    canonical_bindings, tmp_path: Path
) -> None:
    """An UNRELATED runner root whose ``.runner`` claims
    ``agentName="m1-nightly-2"`` refuses — never gets the producer profile.
    RED-first: the previous basename-based wrapper matched any root whose
    directory name was ``m1-nightly-2`` and bound the producer profile;
    a hostile clone at /Users/chriswong/actions-runner-evil with a forged
    ``.runner`` would have been admitted. The new helper requires BOTH
    the canonical root AND the configured agentName to match.
    """

    other_root = tmp_path / "actions-runner-evil"
    other_root.mkdir()
    _write_runner_identity(other_root, "m1-nightly-2")

    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            str(other_root),
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=_plutil_extract_agent_name,
        )
    assert "canonical binding" in str(excinfo.value)
    assert "actions-runner-evil" in str(excinfo.value)


def test_runner_binding_refuses_canonical_root_wrong_identity(
    canonical_bindings,
) -> None:
    """The canonical actions-runner-2 root with the WRONG agentName refuses
    (e.g. a misconfigured ``.runner`` carrying ``m1-nightly-1`` would
    otherwise silently widen admission).
    """

    runner_root = canonical_bindings["runner_2"]
    _write_runner_identity(runner_root, "m1-nightly-1")

    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            str(runner_root),
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=_plutil_extract_agent_name,
        )
    assert "canonical binding" in str(excinfo.value)


def test_runner_binding_preserves_existing_canary_m1_nightly_1(
    canonical_bindings,
) -> None:
    """The existing M1 canary listener at the actions-runner-1 root retains
    the m1-canary profile. RED-first on the previous head would have
    refused because the previous wrapper hardcoded m1-canary as the default
    for any non-m1-nightly-2 basename — the new helper makes that
    canary retention a deliberate (root, agentName) match.
    """

    runner_root = canonical_bindings["runner_1"]
    _write_runner_identity(runner_root, "m1-nightly-1")

    profile, agent_name = BINDING.resolve_profile(
        str(runner_root),
        isfile=os.path.isfile,
        isdir=os.path.isdir,
        extract_agent_name=_plutil_extract_agent_name,
    )
    assert profile == "m1-canary"
    assert agent_name == "m1-nightly-1"


def test_runner_binding_preserves_existing_canary_m1_light_1(
    canonical_bindings,
) -> None:
    """The third M1 canary listener at the actions-runner-3 root retains
    the m1-canary profile.
    """

    runner_root = canonical_bindings["runner_3"]
    _write_runner_identity(runner_root, "m1-light-1")

    profile, agent_name = BINDING.resolve_profile(
        str(runner_root),
        isfile=os.path.isfile,
        isdir=os.path.isdir,
        extract_agent_name=_plutil_extract_agent_name,
    )
    assert profile == "m1-canary"
    assert agent_name == "m1-light-1"


def test_runner_binding_refuses_non_absolute_runner_root(
    canonical_bindings,
) -> None:
    """A relative runner_root path refuses. RED-first: the previous wrapper
    passed whatever LaunchAgent handed it to ``basename`` without checking
    the path was absolute, so a misconfigured plist could not fail closed.
    """

    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            "relative/actions-runner-2",
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=_plutil_extract_agent_name,
        )
    assert "absolute" in str(excinfo.value)


def test_runner_binding_refuses_missing_runner_root(
    canonical_bindings, tmp_path: Path
) -> None:
    """A runner_root path that does not exist refuses. The wrapper would
    have falled through to the ``*)`` case and silently bound the canary
    profile; the new helper refuses with the actionable root cause.
    """

    ghost = tmp_path / "actions-runner-ghost"
    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            str(ghost),
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=_plutil_extract_agent_name,
        )
    assert "does not exist" in str(excinfo.value) or "not a directory" in str(
        excinfo.value
    )


def test_runner_binding_main_module_emits_run_50_binding_for_canonical(
    canonical_bindings,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    portable_plutil: Path,
) -> None:
    """The helper's CLI emits a single ``RUNNER_BINDING=`` JSON line and
    exits 0 for a canonical pair. RED-first: the previous wrapper did not
    produce a receipt; the new helper surfaces the (root, agentName,
    profile) tuple to ``_diag`` for post-incident forensics.

    The helper's production ``_plutil_agent_name`` references
    ``/usr/bin/plutil`` directly via the module-level ``PLUTIL_BIN``
    constant; on Linux CI that binary is absent, so the test patches
    ``PLUTIL_BIN`` to the staged portable stub. The production module
    keeps ``/usr/bin/plutil`` unchanged.
    """

    runner_root = canonical_bindings["runner_2"]
    _write_runner_identity(runner_root, "m1-nightly-2")

    monkeypatch.setattr(BINDING, "PLUTIL_BIN", str(portable_plutil))
    monkeypatch.setattr(sys, "argv", ["runner_binding.py", str(runner_root)])
    rc = BINDING.main()
    assert rc == 0
    out_lines = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("RUNNER_BINDING=")
    ]
    assert len(out_lines) == 1
    payload = json.loads(out_lines[0].split("=", 1)[1])
    assert payload["profile"] == "m1-nightly-2"
    assert payload["agent_name"] == "m1-nightly-2"
    assert payload["runner_root"] == str(runner_root)


def test_runner_binding_main_module_refuses_with_exit_78_and_emits_gh_error(
    canonical_bindings, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The helper's CLI emits a line-start ``::error`` annotation and
    exits 78 (EX_CONFIG) for any refused binding. The wrapper exits 78
    BEFORE Runner.Listener starts, so launchd retries the listener after
    the host operator fixes the real fault.
    """

    runner_root = canonical_bindings["runner_2"]
    # no .runner file at all — refused binding

    monkeypatch.setattr(sys, "argv", ["runner_binding.py", str(runner_root)])
    rc = BINDING.main()
    captured = capsys.readouterr()
    assert rc == 78
    assert captured.out.startswith("::error title=runner-binding::"), (
        f"refusal must emit a line-start GitHub annotation; got: {captured.out!r}"
    )
    assert ".runner" in captured.out


def test_runner_binding_extract_profile_subcommand(
    canonical_bindings, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The helper's ``--extract-profile`` subcommand pulls a single field
    out of a previously-emitted ``RUNNER_BINDING=`` line. The wrapper uses
    this rather than ``jq`` so the helper module owns the schema contract.
    """

    binding_line = json.dumps(
        {
            "schema": "runner.binding.v1",
            "runner_root": "/Users/chriswong/actions-runner-2",
            "agent_name": "m1-nightly-2",
            "profile": "m1-nightly-2",
        },
        sort_keys=True,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["runner_binding.py", "--extract-profile", binding_line, "profile"],
    )
    rc = BINDING.main()
    assert rc == 0
    assert capsys.readouterr().out == "m1-nightly-2"


def test_runner_binding_extract_profile_refuses_malformed_input(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """``--extract-profile`` on a non-JSON line emits ``::error`` and
    exits 78 — the wrapper would never silently fall back to the canary
    profile from a corrupt receipt.
    """

    monkeypatch.setattr(
        sys,
        "argv",
        ["runner_binding.py", "--extract-profile", "not-json{", "profile"],
    )
    rc = BINDING.main()
    captured = capsys.readouterr()
    assert rc == 78
    assert captured.out.startswith("::error title=runner-binding::")


# ── AD-1T2 round 2: wrapper must pass rawjson + key, not the prefixed line ──
# The previous wrapper called the helper with `--extract-profile
# "$binding_line"` (no key). The helper's main() requires exactly two positional
# args after `--extract-profile` (rawjson + key) and exits 64 when the key is
# omitted — so the wrapper never reached the profile-name case branch and
# the listener never received an admission surface. These tests pin the
# helper's strict CLI contract and the wrapper's prefix-stripping + key
# delegation so the regression cannot return.


def test_runner_binding_extract_profile_omitted_key_exits_64(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """``--extract-profile`` with no key exits 64 (EX_USAGE) — the previous
    wrapper hit this on every M1 invocation and the wrapper's own
    ``|| { exit 78; }`` translated the helper's usage error into a
    confusing 78 with the helper's usage message instead of a structured
    ``::error title=runner-binding::`` annotation. RED-first on the
    previous (prefix-broken) head.
    """
    monkeypatch.setattr(
        sys,
        "argv",
        ["runner_binding.py", "--extract-profile", json.dumps({"profile": "m1-nightly-2"})],
    )
    rc = BINDING.main()
    captured = capsys.readouterr()
    assert rc == 64
    # helper must print a usage hint, NOT a line-start ::error
    assert "usage: runner_binding.py --extract-profile" in captured.err
    assert not captured.out.startswith("::error")


def test_runner_binding_extract_profile_prefixed_payload_exits_78(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """``--extract-profile`` on a payload that still carries the
    ``RUNNER_BINDING=`` prefix exits 78 with a line-start ``::error`` —
    the helper refuses to ``json.loads()`` the prefixed text and the
    wrapper's prefix-validation + strip step exists precisely so this
    refusal never reaches the wrapper.
    """
    prefixed = 'RUNNER_BINDING={"schema":"runner.binding.v1","profile":"m1-nightly-2"}'
    monkeypatch.setattr(
        sys,
        "argv",
        ["runner_binding.py", "--extract-profile", prefixed, "profile"],
    )
    rc = BINDING.main()
    captured = capsys.readouterr()
    assert rc == 78
    assert captured.out.startswith("::error title=runner-binding::")
    assert "could not extract" in captured.out


# ── AD-1T2 round 3: portable plutil stub so the test suite runs on Linux CI
# The production helper's ``_plutil_agent_name`` shells out to
# ``/usr/bin/plutil``; on Linux runners that binary is absent, so the three
# tests that drive the helper's real CLI through ``main()`` (initial
# resolution of a canonical binding) cannot exercise the production path.
# The wrapper-harness tests already stage a portable stub at the helper
# level via :func:`_stage_helper_with_bindings`; the standalone
# ``test_runner_binding_main_module_emits_run_50_binding_for_canonical``
# test is patched through the ``portable_plutil`` fixture. These two tests
# pin the portability contract directly: the module's ``_plutil_agent_name``
# path round-trips a canonical binding through the portable stub, and a
# malformed plist still surfaces as ``RunnerBindingRefused("unreadable ...")``.


def test_runner_binding_module_uses_the_portable_plutil_stub(
    canonical_bindings, monkeypatch: pytest.MonkeyPatch, portable_plutil: Path
) -> None:
    """Drive ``resolve_profile`` with the module's REAL
    ``_plutil_agent_name`` (no injection) and the production-shaped
    ``(root=actions-runner-2, agentName=m1-nightly-2)`` canonical pair.
    ``PLUTIL_BIN`` is redirected to the portable stub so this test runs
    on hosts without ``/usr/bin/plutil`` (Linux CI). RED-first on the
    previous head: the production ``_plutil_agent_name`` called
    ``/usr/bin/plutil`` via ``subprocess.run``; on Linux CI it raised
    ``FileNotFoundError`` and the helper's ``except Exception`` block
    wrapped it as ``RunnerBindingRefused("unreadable .runner at ...")``,
    so this assertion failed on every Linux CI run. The portable stub
    re-implements ONLY the production contract so the real code path is
    still exercised.
    """
    runner_root = canonical_bindings["runner_2"]
    _write_runner_identity(runner_root, "m1-nightly-2")
    monkeypatch.setattr(BINDING, "PLUTIL_BIN", str(portable_plutil))

    profile, agent_name = BINDING.resolve_profile(
        str(runner_root),
        isfile=os.path.isfile,
        isdir=os.path.isdir,
        extract_agent_name=BINDING._plutil_agent_name,
    )
    assert profile == "m1-nightly-2"
    assert agent_name == "m1-nightly-2"


def test_portable_plutil_stub_refuses_malformed_metadata(
    canonical_bindings, monkeypatch: pytest.MonkeyPatch, portable_plutil: Path
) -> None:
    """The portable plutil stub surfaces a non-zero exit (and a stderr
    line) for a malformed plist, so the helper's real
    ``_plutil_agent_name`` subprocess fails and ``resolve_profile`` wraps
    it as ``RunnerBindingRefused("unreadable .runner at ...")``. RED-first:
    a stub that silently returned an empty string would leave the helper
    with an empty ``agentName``, which the existing empty-string test
    would refuse — but the failure would carry the wrong cause ("missing
    agentName") instead of the actionable root cause
    ("unreadable .runner at ...").
    """
    runner_root = canonical_bindings["runner_2"]
    runner_root.mkdir(exist_ok=True)
    (runner_root / ".runner").write_text("this is not a plist", encoding="utf-8")
    monkeypatch.setattr(BINDING, "PLUTIL_BIN", str(portable_plutil))

    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            str(runner_root),
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=BINDING._plutil_agent_name,
        )
    assert "unreadable" in str(excinfo.value)


def test_runner_binding_module_forces_absence_of_production_plutil(
    canonical_bindings, monkeypatch: pytest.MonkeyPatch, portable_plutil: Path
) -> None:
    """Force ``PLUTIL_BIN`` at a path where the production
    ``/usr/bin/plutil`` cannot exist (a tmp_path-relative file that is
    never created) and prove the suite still passes once the stub is in
    place. This is the explicit "force absence of production plutil
    path" test the META-CEO round-3 ruling called for: it does NOT rely
    on the system ``/usr/bin/plutil`` being present, present-but-broken,
    or absent — only the staged stub is consulted by the helper's real
    ``_plutil_agent_name`` subprocess call.
    """
    runner_root = canonical_bindings["runner_2"]
    _write_runner_identity(runner_root, "m1-nightly-2")

    # 1. Confirm the absence: PLUTIL_BIN pointed at a path that does not
    #    exist on the host makes the real _plutil_agent_name fail with
    #    FileNotFoundError, which the helper wraps as RunnerBindingRefused.
    missing = portable_plutil.parent / "absent-plutil-forced-missing"
    assert not missing.exists()
    monkeypatch.setattr(BINDING, "PLUTIL_BIN", str(missing))
    with pytest.raises(BINDING.RunnerBindingRefused) as excinfo:
        BINDING.resolve_profile(
            str(runner_root),
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=BINDING._plutil_agent_name,
        )
    assert "unreadable" in str(excinfo.value)

    # 2. Repoint to the portable stub and prove the same canonical pair
    #    round-trips. The same _plutil_agent_name code path is exercised;
    #    only the binary it shells out to has changed.
    monkeypatch.setattr(BINDING, "PLUTIL_BIN", str(portable_plutil))
    profile, agent_name = BINDING.resolve_profile(
        str(runner_root),
        isfile=os.path.isfile,
        isdir=os.path.isdir,
        extract_agent_name=BINDING._plutil_agent_name,
    )
    assert profile == "m1-nightly-2"
    assert agent_name == "m1-nightly-2"


# ── AD-1T2 round 2: wrapper-level harness driving the REAL helper ─────────
# These tests run the real wrapper script against a temp runner_root +
# temp guard_root. The temp guard_root stages a copy of the real
# runner_binding.py with CANONICAL_BINDINGS rewritten to include the temp
# runner_root path, plus no-op disk/log guards and a fake
# Runner.Listener that records the env it was launched with. The wrapper
# delegates profile extraction to the real helper CLI on every invocation,
# so any drift between the wrapper and the helper's --extract-profile
# contract fails here, not only in the wrapper's static text.


_CANONICAL_BINDINGS_RE = re.compile(
    r"^CANONICAL_BINDINGS: dict\[tuple\[str, str\], str\] = \{.*?^\}",
    re.DOTALL | re.MULTILINE,
)

_PLUTIL_BIN_RE = re.compile(
    r'^PLUTIL_BIN\s*=\s*"/usr/bin/plutil"\s*$',
    re.MULTILINE,
)

#: Test-only portable plutil stub implementing the production M1 wrapper
#: contract ``/usr/bin/plutil -extract agentName raw -o - <file>`` using
#: the stdlib ``plistlib`` so the test suite runs unchanged on macOS,
#: Linux, and Windows CI without a system plutil binary. The production
#: ``runner_binding.py`` keeps ``/usr/bin/plutil``; the test harness
#: rewrites ``PLUTIL_BIN`` in the staged helper copy to point at this
#: stub. See :func:`_stage_portable_plutil` and the ``portable_plutil``
#: fixture for the staging paths.
_PORTABLE_PLUTIL_STUB = (
    "#!/usr/bin/env python3\n"
    '"""Portable plutil stub — test harness only (production uses /usr/bin/plutil)."""\n'
    "import plistlib\n"
    "import sys\n"
    "\n"
    "\n"
    "def main() -> int:\n"
    "    args = sys.argv[1:]\n"
    '    expected = ["-extract", "agentName", "raw", "-o", "-"]\n'
    "    if len(args) < 6 or args[:5] != expected:\n"
    '        sys.stderr.write(\n'
    '            "portable plutil stub: unsupported invocation: "\n'
    "            + repr(args)\n"
    '            + "\\n"\n'
    "        )\n"
    "        return 2\n"
    "    runner_file = args[5]\n"
    "    try:\n"
    '        with open(runner_file, "rb") as handle:\n'
    "            document = plistlib.load(handle)\n"
    "    except Exception as exc:\n"
    '        sys.stderr.write(\n'
    '            "portable plutil stub: cannot parse "\n'
    "            + runner_file\n"
    '            + ": " + str(exc) + "\\n"\n'
    "        )\n"
    "        return 1\n"
    '    value = document.get("agentName")\n'
    "    if not isinstance(value, str):\n"
    '        sys.stderr.write(\n'
    '            "portable plutil stub: agentName is not a string in "\n'
    "            + runner_file\n"
    '            + "\\n"\n'
    "        )\n"
    "        return 1\n"
    "    sys.stdout.write(value)\n"
    "    return 0\n"
    "\n"
    "\n"
    'if __name__ == "__main__":\n'
    "    raise SystemExit(main())\n"
)


def _stage_portable_plutil(directory: Path) -> Path:
    """Write the portable plutil stub to ``directory/plutil`` and chmod
    0755. Returns the absolute path of the staged executable.
    """
    stub = directory / "plutil"
    stub.write_text(_PORTABLE_PLUTIL_STUB, encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _stage_helper_with_bindings(
    guard_root: Path,
    bindings: dict[tuple[str, str], str],
    *,
    plutil_bin: Path,
) -> Path:
    """Stage a copy of ``runner_binding.py`` at ``guard_root`` whose
    ``CANONICAL_BINDINGS`` literal is rewritten to include the test's
    temp ``(runner_root, agent_name)`` pairs AND whose ``PLUTIL_BIN`` is
    rewritten to point at the staged portable plutil stub. The helper's
    ``resolve_profile`` consults ``CANONICAL_BINDINGS`` at import time so
    the rewrite is necessary for the wrapper's subprocess invocation to
    see the temp path as a canonical pair; the ``PLUTIL_BIN`` rewrite is
    necessary so the helper does not depend on a system ``/usr/bin/plutil``
    that may be absent on Linux CI.
    """
    real = (
        ROOT / "ops" / "runner-host" / "common" / "runner_binding.py"
    ).read_text(encoding="utf-8")
    new_lines = ",\n".join(
        f"    {k!r}: {v!r}" for k, v in bindings.items()
    )
    new_block = f"CANONICAL_BINDINGS: dict[tuple[str, str], str] = {{\n{new_lines}\n}}"
    patched, count = _CANONICAL_BINDINGS_RE.subn(new_block, real, count=1)
    assert count == 1, "did not substitute CANONICAL_BINDINGS in helper copy"
    patched, count = _PLUTIL_BIN_RE.subn(
        f"PLUTIL_BIN = {str(plutil_bin)!r}", patched, count=1
    )
    assert count == 1, "did not rewrite PLUTIL_BIN in helper copy"
    target = guard_root / "runner_binding.py"
    target.write_text(patched, encoding="utf-8")
    target.chmod(0o755)
    return target


def _stage_wrapper_harness(
    tmp_path: Path,
    *,
    agent_name: str,
    runner_basename: str,
    bindings: dict[tuple[str, str], str],
) -> tuple[Path, Path, Path]:
    """Stage a temp runner_root + guard_root for an end-to-end wrapper
    invocation. Returns ``(runner_root, guard_root, listener_log)``.

    The real ``runner_binding.py`` is staged at ``guard_root`` with the
    caller's ``bindings`` so the production (canonical root, configured
    agentName) check runs against real fs objects; disk and log guards
    are no-op stubs so the wrapper reaches the binding step on every
    invocation; the fake ``Runner.Listener`` writes the env it was
    launched with to ``listener_log`` so the caller can pin
    ACTIONS_RUNNER_HOOK_JOB_STARTED / MASTERMIND_CI_PROFILE /
    RUNNER_BINDING without parsing stdout.
    """
    runner_root = tmp_path / runner_basename
    runner_root.mkdir()
    (runner_root / "_diag").mkdir()
    with (runner_root / ".runner").open("wb") as handle:
        plistlib.dump({"agentName": agent_name}, handle)

    bin_dir = runner_root / "bin"
    bin_dir.mkdir()
    listener_log = runner_root / "listener_receipt.json"
    listener = bin_dir / "Runner.Listener"
    listener.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        f"with open({str(listener_log)!r}, 'w') as handle:\n"
        "    json.dump({'env': dict(os.environ), 'argv': sys.argv}, handle)\n",
        encoding="utf-8",
    )
    listener.chmod(0o755)

    guard_root = tmp_path / "guard"
    guard_root.mkdir()
    plutil_bin = _stage_portable_plutil(guard_root)
    _stage_helper_with_bindings(guard_root, bindings, plutil_bin=plutil_bin)
    for name in (
        "runner_disk_guard.py",
        "runner_log_maintenance.py",
    ):
        stub = guard_root / name
        stub.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        stub.chmod(0o755)
    for name in (
        "runner_admission_m1_canary.js",
        "runner_admission_m1_nightly_2.js",
    ):
        (guard_root / name).write_text("// fake admission hook\n", encoding="utf-8")

    return runner_root, guard_root, listener_log


def _run_wrapper(
    runner_root: Path, guard_root: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(ROOT / "ops" / "runner-host" / "m1" / "run_guarded_runner.sh"),
            str(runner_root),
            str(guard_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_wrapper_invokes_real_helper_for_m1_nightly_2(tmp_path: Path) -> None:
    """End-to-end happy path: the wrapper invokes the real
    ``runner_binding.py`` twice (initial resolution + delegated
    ``--extract-profile``), selects the nightly hook + profile for the
    m1-nightly-2 binding, and launches ``Runner.Listener`` with the
    matching env. RED-first on the previous (no-key) head because the
    delegated extraction exited 64 and the wrapper never reached the
    listener launch.
    """
    runner_root_path = str(tmp_path / "actions-runner-2")
    runner_root, guard_root, listener_log = _stage_wrapper_harness(
        tmp_path,
        agent_name="m1-nightly-2",
        runner_basename="actions-runner-2",
        bindings={(runner_root_path, "m1-nightly-2"): "m1-nightly-2"},
    )

    result = _run_wrapper(runner_root, guard_root)

    assert result.returncode == 0, (
        f"wrapper should bind m1-nightly-2 to its producer profile and "
        f"start the listener; got rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert listener_log.is_file(), "Runner.Listener was never launched"
    receipt = json.loads(listener_log.read_text(encoding="utf-8"))
    env = receipt["env"]
    assert env["MASTERMIND_CI_PROFILE"] == "m1-nightly-2"
    assert env["ACTIONS_RUNNER_HOOK_JOB_STARTED"] == str(
        guard_root / "runner_admission_m1_nightly_2.js"
    )
    assert env["RUNNER_BINDING"].startswith("RUNNER_BINDING=")
    payload = json.loads(env["RUNNER_BINDING"].split("=", 1)[1])
    assert payload["profile"] == "m1-nightly-2"
    assert payload["agent_name"] == "m1-nightly-2"
    assert receipt["argv"][-3:] == ["run", "--startuptype", "service"]


def test_wrapper_invokes_real_helper_for_m1_canary_default(tmp_path: Path) -> None:
    """The existing canary default (m1-nightly-1 root → m1-canary profile)
    is preserved end-to-end: the wrapper still launches the listener with
    the canary hook + profile when the binding helper returns
    ``m1-canary``. RED-first on the previous (no-key) head because the
    delegated extraction would have exited 64 for this root too — the
    previous wrapper would never have selected any profile.
    """
    runner_root_path = str(tmp_path / "actions-runner-1")
    runner_root, guard_root, listener_log = _stage_wrapper_harness(
        tmp_path,
        agent_name="m1-nightly-1",
        runner_basename="actions-runner-1",
        bindings={(runner_root_path, "m1-nightly-1"): "m1-canary"},
    )

    result = _run_wrapper(runner_root, guard_root)

    assert result.returncode == 0, (
        f"wrapper should preserve the canary default for m1-nightly-1; "
        f"got rc={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert listener_log.is_file(), "Runner.Listener was never launched"
    receipt = json.loads(listener_log.read_text(encoding="utf-8"))
    env = receipt["env"]
    assert env["MASTERMIND_CI_PROFILE"] == "m1-canary"
    assert env["ACTIONS_RUNNER_HOOK_JOB_STARTED"] == str(
        guard_root / "runner_admission_m1_canary.js"
    )


def test_wrapper_refuses_when_helper_emits_wrong_prefix(tmp_path: Path) -> None:
    """If the initial resolver emits something other than the exact
    ``RUNNER_BINDING=`` prefix, the wrapper exits 78 BEFORE the listener
    starts and surfaces a structured ``::error title=runner-binding::``
    annotation. RED-first on the previous (no-prefix-validation) head
    because the wrapper would have forwarded the malformed line straight
    to ``--extract-profile`` and trusted whatever the helper returned.
    """
    runner_root_path = str(tmp_path / "actions-runner-2")
    runner_root, guard_root, listener_log = _stage_wrapper_harness(
        tmp_path,
        agent_name="m1-nightly-2",
        runner_basename="actions-runner-2",
        bindings={(runner_root_path, "m1-nightly-2"): "m1-nightly-2"},
    )
    # Replace the staged helper with a fake initial resolver that omits
    # the RUNNER_BINDING= prefix; the delegated --extract-profile call
    # still returns m1-nightly-2 so any regression that swallows the
    # prefix-validation step would land on the nightly branch instead of
    # the expected 78.
    (guard_root / "runner_binding.py").write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "if len(sys.argv) >= 2 and sys.argv[1] == '--extract-profile':\n"
        "    sys.stdout.write(sys.argv[3] and 'm1-nightly-2' or '')\n"
        "    sys.exit(0)\n"
        "sys.stdout.write(\n"
        "    'PROFILE_NOT_BINDING=' + json.dumps(\n"
        "        {'schema': 'runner.binding.v1', 'profile': 'm1-nightly-2'}\n"
        "    )\n"
        ")\n"
        "sys.stdout.flush()\n",
        encoding="utf-8",
    )
    (guard_root / "runner_binding.py").chmod(0o755)

    result = _run_wrapper(runner_root, guard_root)

    assert result.returncode == 78
    assert "RUNNER_BINDING= prefix" in result.stderr
    assert "::error title=runner-binding::" in result.stderr
    assert not listener_log.exists(), (
        "wrapper must not launch Runner.Listener when the binding line "
        "fails prefix validation"
    )


def test_wrapper_refuses_when_extract_profile_fails(tmp_path: Path) -> None:
    """If the initial resolver emits a well-formed ``RUNNER_BINDING=``
    line but the delegated ``--extract-profile`` step refuses (helper
    exits 78 on a malformed receipt), the wrapper exits 78 BEFORE the
    listener starts. RED-first on the previous (no-key) head because the
    delegated extraction exited 64 with the helper's usage message — the
    previous wrapper's ``|| { exit 78; }`` swallowed the 64 and the
    wrapper would have surfaced a confusing usage message rather than a
    structured ``::error``.
    """
    runner_root_path = str(tmp_path / "actions-runner-2")
    runner_root, guard_root, listener_log = _stage_wrapper_harness(
        tmp_path,
        agent_name="m1-nightly-2",
        runner_basename="actions-runner-2",
        bindings={(runner_root_path, "m1-nightly-2"): "m1-nightly-2"},
    )
    # Replace the staged helper: initial resolver emits the expected
    # prefix; delegated --extract-profile refuses (78) with the
    # production line-start ::error annotation.
    (guard_root / "runner_binding.py").write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "if len(sys.argv) >= 2 and sys.argv[1] == '--extract-profile':\n"
        "    sys.stdout.write(\n"
        "        '::error title=runner-binding::synthetic extraction failure'\n"
        "        + chr(10)\n"
        "    )\n"
        "    sys.stdout.flush()\n"
        "    sys.exit(78)\n"
        "sys.stdout.write(\n"
        "    'RUNNER_BINDING=' + json.dumps(\n"
        "        {\n"
        "            'schema': 'runner.binding.v1',\n"
        "            'runner_root': sys.argv[1],\n"
        "            'agent_name': 'm1-nightly-2',\n"
        "            'profile': 'm1-nightly-2',\n"
        "        }\n"
        "    )\n"
        ")\n"
        "sys.stdout.flush()\n",
        encoding="utf-8",
    )
    (guard_root / "runner_binding.py").chmod(0o755)

    result = _run_wrapper(runner_root, guard_root)

    assert result.returncode == 78
    assert "could not extract profile from" in result.stderr
    assert "::error title=runner-binding::" in result.stderr
    assert not listener_log.exists(), (
        "wrapper must not launch Runner.Listener when extraction refuses"
    )


def test_runner_service_seals_runtime_and_binds_host_admission() -> None:
    unit = (
        ROOT / "ops" / "runner-host" / "pc" / "actions-runner-ci.service.template"
    ).read_text(encoding="utf-8")
    assert "ACTIONS_RUNNER_HOOK_JOB_STARTED=/usr/local/libexec/mastermind-ci-admission-pc-ci.js" in unit
    assert "ACTIONS_RUNNER_HOOK_JOB_COMPLETED" not in unit
    assert "Restart=always" in unit
    assert "RestartSec=5" in unit
    assert "StartLimitIntervalSec=0" in unit
    assert "StartLimitBurst" not in unit
    assert "--refusal-backoff-seconds 300" in unit
    assert "TimeoutStartSec=10min" in unit
    assert "MASTERMIND_CI_RUNNER_ROOT=__RUNNER_ROOT__" in unit
    assert "ReadOnlyPaths=__RUNNER_ROOT__ /var/cache/mastermind-ci/macro.git" in unit
    assert "ReadWritePaths=__RUNNER_ROOT__/_work __RUNNER_ROOT__/_diag" in unit
    assert "ReadWritePaths=__RUNNER_ROOT__ " not in unit
    assert "UMask=0022" in unit
    assert "UMask=0027" not in unit
    pc_wrapper = (
        ROOT / "ops" / "runner-host" / "pc" / "mastermind_ci_runner.sh"
    ).read_text(encoding="utf-8")
    assert "ACTIONS_RUNNER_HOOK_JOB_STARTED=/usr/local/libexec/mastermind-ci-admission-pc-ci.js" in pc_wrapper
    assert "/usr/bin/python3 -I /usr/local/libexec/runner_cleanup.py" in pc_wrapper
    assert 'run --startuptype service --once' in pc_wrapper
    assert 'MASTERMIND_CI_RUNNER_ROOT="$runner_root"' in pc_wrapper
    m1 = (ROOT / "ops" / "runner-host" / "m1" / "run_guarded_runner.sh").read_text(
        encoding="utf-8"
    )
    assert 'ACTIONS_RUNNER_HOOK_JOB_STARTED="$guard_root/runner_admission_m1_canary.js"' in m1
    assert "MASTERMIND_CI_PROFILE=m1-canary" in m1
    # AD-1T2 binding must go through the helper, not the directory basename.
    assert 'basename "$runner_root"' not in m1
    assert '"$guard_root/runner_binding.py" "$runner_root"' in m1
    hook = (
        ROOT / "ops" / "runner-host" / "common" / "runner_admission_hook.js"
    ).read_text(encoding="utf-8")
    assert 'spawnSync("/usr/bin/python3", ["-I", script]' in hook
    assert '"GITHUB_EVENT_PATH"' in hook
    assert "process.env.PATH" not in hook
    assert "process.env.MASTERMIND_CI_PROFILE" not in hook


def test_pc_windows_boot_recovery_preserves_existing_runner_authority() -> None:
    recovery = (
        ROOT
        / "ops"
        / "runner-host"
        / "pc"
        / "windows"
        / "Start-MastermindWslBootRecovery.ps1"
    ).read_text(encoding="utf-8")
    installer = (
        ROOT
        / "ops"
        / "runner-host"
        / "pc"
        / "windows"
        / "Install-MastermindWslBootRecovery.ps1"
    ).read_text(encoding="utf-8")

    # Windows owns only WSL residency. Microsoft documents that systemd services
    # do not keep a WSL instance alive, so a one-shot `/bin/true` wake is a false
    # recovery: it can briefly revive listeners and then strand them again. The
    # scheduled task must hold one inert foreground keepalive while GitHub/systemd
    # retain runner registration, labels, routing, and listener restart authority.
    assert "--exec /bin/sh -c $keepalive" in recovery
    assert "while :; do sleep 3600; done" in recovery
    assert "/bin/true" not in recovery
    assert "exit 0" not in recovery
    assert "Register-ScheduledTask" in installer
    assert "New-ScheduledTaskTrigger -AtStartup" in installer
    assert "New-ScheduledTaskTrigger -AtLogOn" in installer
    assert "-ExecutionTimeLimit (New-TimeSpan -Seconds 0)" in installer
    assert "-MultipleInstances IgnoreNew" in installer
    assert "-LogonType S4U" in installer
    assert "-RestartCount 999" in installer
    assert "while ($true)" in recovery
    assert "$failureCount++" in recovery
    assert "$MaxRetrySeconds" in recovery
    assert "failed attempts=" not in recovery
    assert "[int]$Attempts" not in recovery
    assert "exit 1" not in recovery
    for forbidden in ("pc-ci-4", "ci-linux", "config.sh", "Runner.Listener"):
        assert forbidden not in recovery
        assert forbidden not in installer


def test_pc_windows_boot_recovery_pins_highest_task_run_level() -> None:
    installer = (
        ROOT
        / "ops"
        / "runner-host"
        / "pc"
        / "windows"
        / "Install-MastermindWslBootRecovery.ps1"
    ).read_text(encoding="utf-8")
    assert "-RunLevel Highest" in installer


def test_pc_windows_boot_recovery_rejects_unsafe_distribution_names() -> None:
    installer = (
        ROOT
        / "ops"
        / "runner-host"
        / "pc"
        / "windows"
        / "Install-MastermindWslBootRecovery.ps1"
    ).read_text(encoding="utf-8")
    assert "$Distribution -notmatch '^[A-Za-z0-9._ -]+$'" in installer
    assert ".Replace('\"', '\"\"')" not in installer


def test_pc_windows_boot_recovery_seals_privileged_action_path() -> None:
    installer = (
        ROOT
        / "ops"
        / "runner-host"
        / "pc"
        / "windows"
        / "Install-MastermindWslBootRecovery.ps1"
    ).read_text(encoding="utf-8")
    assert "SetAccessRuleProtection($true, $false)" in installer
    assert "S-1-5-18" in installer
    assert "S-1-5-32-544" in installer
    assert "AreAccessRulesProtected" in installer
    assert "Get-FileHash" in installer
    assert "[System.IO.FileAttributes]::ReparsePoint" in installer


def test_pc_windows_boot_recovery_whatif_is_non_mutating() -> None:
    installer = (
        ROOT
        / "ops"
        / "runner-host"
        / "pc"
        / "windows"
        / "Install-MastermindWslBootRecovery.ps1"
    ).read_text(encoding="utf-8")
    should_process = installer.index("if ($PSCmdlet.ShouldProcess")
    assert installer.find("New-Item", 0, should_process) == -1
    assert installer.find("Copy-Item", 0, should_process) == -1
    assert installer.index("New-Item", should_process) > should_process
    assert installer.index("Copy-Item", should_process) > should_process


def test_resource_refusal_backoff_only_delays_an_unsafe_retry() -> None:
    sleeps: list[int] = []
    RESOURCE_GUARD.refusal_backoff([], 300, sleep=sleeps.append)
    assert sleeps == []
    RESOURCE_GUARD.refusal_backoff(["critical disk pressure"], 300, sleep=sleeps.append)
    assert sleeps == [300]


def test_listener_startup_cleanup_scrubs_all_pc_job_state_and_recreates_runtime_dirs(
    tmp_path: Path, monkeypatch
) -> None:
    runner = tmp_path / "runner-1"
    work = runner / "_work"
    (work / "_temp").mkdir(parents=True)
    (work / "_temp" / "current-event.json").write_text("{}", encoding="utf-8")
    (work / "macro" / "macro").mkdir(parents=True)
    (work / "macro" / "macro" / "sentinel").write_text("old", encoding="utf-8")
    (work / "_actions").mkdir()
    (work / "_tool").symlink_to(work / "macro", target_is_directory=True)
    private_tmp = tmp_path / "private-tmp"
    private_tmp.mkdir()
    (private_tmp / "prior-job").write_text("old", encoding="utf-8")
    monkeypatch.setattr(CLEANUP, "PC_CI_ROOTS", {runner})
    assert CLEANUP.scrub_pc_state(runner, (private_tmp,)) >= 4
    assert not (work / "_temp" / "current-event.json").exists()
    assert list((work / "_temp").iterdir()) == []
    assert list((work / "_home").iterdir()) == []
    assert not (work / "macro").exists()
    assert not (work / "_actions").exists()
    assert not (work / "_tool").exists()
    assert list(private_tmp.iterdir()) == []


def test_start_admission_has_no_workspace_mutation_api() -> None:
    assert not hasattr(ADMISSION, "scrub_pc_state")
    assert not hasattr(ADMISSION, "remove_entry")


# ── C3R-A: four-slot diagnostic selection ────────────────────────────────────
# The canary must be able to select FOUR distinct non-empty packs so the fourth
# PC CI slot can be exercised diagnostically. Selection stays weight-ordered and
# still refuses to invent a pack when the plan cannot supply one.


def _four_pack_plan() -> dict:
    return {
        "schema": SELECT._PLAN_SCHEMA,
        "packs": [
            {"index": 0, "weight": 2, "jobs": ["small"]},
            {"index": 7, "weight": 99, "jobs": ["heavy"]},
            {"index": 4, "weight": 50, "jobs": ["middle"]},
            {"index": 2, "weight": 30, "jobs": ["fourth"]},
            {"index": 9, "weight": 0, "jobs": []},
        ],
    }


def test_selector_admits_four_distinct_non_empty_packs() -> None:
    chosen = SELECT.select(_four_pack_plan(), 4)
    indices = [item["index"] for item in chosen]
    assert indices == [7, 4, 2, 0], "four-slot selection stays weight-ordered"
    assert len(set(indices)) == 4, "every selected pack must be distinct"
    assert all(item["jobs"] for item in chosen), "no empty pack may be selected"


def test_selector_refuses_four_slots_when_the_plan_cannot_fill_them() -> None:
    thin = {
        "schema": SELECT._PLAN_SCHEMA,
        "packs": [
            {"index": 0, "weight": 2, "jobs": ["a"]},
            {"index": 1, "weight": 1, "jobs": ["b"]},
            {"index": 2, "weight": 3, "jobs": ["c"]},
            {"index": 3, "weight": 9, "jobs": []},
        ],
    }
    with pytest.raises(ValueError, match="only 3 non-empty pack"):
        SELECT.select(thin, 4)


def test_selector_cli_emits_a_four_entry_matrix_for_every_slot_identity(
    tmp_path: Path,
) -> None:
    """hosted-control, selfhosted-pack and compare all fan out over
    `needs.plan.outputs.matrix`, so proving the selector emits four distinct pack
    identities is what proves all three matrices carry four at slots=4.
    """
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_four_pack_plan()), encoding="utf-8")
    output = tmp_path / "github-output"
    output.write_text("", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "select_ci_canary_packs.py"),
            "--plan",
            str(plan_path),
            "--count",
            "4",
            "--github-output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    values = dict(
        line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines() if line
    )
    matrix = json.loads(values["matrix"])
    assert matrix == {"include": [{"pack": 7}, {"pack": 4}, {"pack": 2}, {"pack": 0}]}
    assert len({entry["pack"] for entry in matrix["include"]}) == 4
    assert values["primary_pack"] == "7"


def test_selector_cli_refuses_a_fifth_slot(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_four_pack_plan()), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "select_ci_canary_packs.py"),
            "--plan",
            str(plan_path),
            "--count",
            "5",
            "--github-output",
            str(tmp_path / "github-output"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "invalid choice" in completed.stderr


# ── C3R-A: aggregate cgroup-v2 slice evidence ────────────────────────────────
# Four CI candidates share one enforced envelope, so per-candidate host-global
# numbers stop being evidence: they cannot tell "CI is inside its budget" from
# "the guest happens to be quiet". The monitor therefore binds each candidate to
# the immutable /mastermind.slice/mastermind-ci.slice hierarchy and REFUSES rather than falling
# back to host-global metrics — a green produced by the wrong cgroup is worse
# than no green at all, because it reads as proof.


def _write_slice_tree(
    root: Path, cgroup: str, at_slice: bool = True, **overrides: str
) -> Path:
    """Populate cgroup files for a fixture.

    The AGGREGATE counters and the envelope live on the slice node, not on a
    candidate's leaf `.service` (measured on the real host). So by default the
    metric files are written at the slice node and the candidate path is merely
    created, which is what membership needs. Pass at_slice=False to plant decoy
    values on the leaf and prove they are never reported.
    """
    node = root / cgroup.lstrip("/")
    node.mkdir(parents=True, exist_ok=True)
    if at_slice:
        chain = "/".join(MONITOR.expected_slice_chain(MONITOR.EXPECTED_SLICE))
        if cgroup.lstrip("/").startswith(chain):
            node = root / chain
            node.mkdir(parents=True, exist_ok=True)
    files = {
        "cpu.stat": (
            "usage_usec 1000000\nuser_usec 700000\nsystem_usec 300000\n"
            "nr_periods 400\nnr_throttled 20\nthrottled_usec 50000\n"
        ),
        "cpu.max": "800000 100000\n",
        "memory.high": "10737418240\n",
        "memory.max": "12884901888\n",
        "memory.swap.max": "2147483648\n",
        "memory.current": "1073741824\n",
        "memory.peak": "2147483648\n",
        "memory.swap.current": "0\n",
        "memory.events": "low 0\nhigh 3\nmax 0\noom 0\noom_kill 0\n",
        "pids.current": "42\n",
        "pids.events": "max 0\n",
        "cpu.pressure": (
            "some avg10=1.50 avg60=1.00 avg300=0.50 total=1234\n"
            "full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n"
        ),
        "memory.pressure": (
            "some avg10=0.10 avg60=0.05 avg300=0.01 total=99\n"
            "full avg10=0.02 avg60=0.01 avg300=0.00 total=11\n"
        ),
        "io.pressure": (
            "some avg10=0.20 avg60=0.10 avg300=0.05 total=77\n"
            "full avg10=0.03 avg60=0.01 avg300=0.00 total=7\n"
        ),
    }
    files.update(overrides)
    for name, body in files.items():
        if body is None:
            continue
        (node / name).write_text(body, encoding="utf-8")
    return node


def _proc_cgroup(tmp_path: Path, cgroup: str) -> Path:
    path = tmp_path / "proc-self-cgroup"
    path.write_text(f"0::{cgroup}\n", encoding="utf-8")
    return path


# The REAL systemd layout: `-` in a slice name is a cgroup path separator, so
# mastermind-ci.slice is a child of an implicit mastermind.slice. This constant
# was originally written without the parent and every fixture inherited the
# error, which is why no test caught the refusal that stopped pc-ci-1 on the host.
CI_CGROUP = (
    "/mastermind.slice/mastermind-ci.slice/"
    "actions.runner.macro.pc-ci-4.service"
)


def test_monitor_binds_a_candidate_to_the_expected_ci_slice(tmp_path: Path) -> None:
    assert MONITOR.EXPECTED_SLICE == "mastermind-ci.slice"
    root = tmp_path / "cgroup"
    _write_slice_tree(root, CI_CGROUP)
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, CI_CGROUP))
    assert sample["status"] == "bound"
    assert sample["cgroup"] == CI_CGROUP
    assert sample["cpu"]["usage_usec"] == 1_000_000
    assert sample["cpu"]["nr_periods"] == 400
    assert sample["cpu"]["nr_throttled"] == 20
    assert sample["cpu"]["throttled_usec"] == 50_000
    assert sample["cpu_max"] == "800000 100000"
    assert sample["memory"]["current"] == 1_073_741_824
    assert sample["memory"]["peak"] == 2_147_483_648
    assert sample["memory"]["swap_current"] == 0
    assert sample["memory_events"]["high"] == 3
    assert sample["pids"]["current"] == 42
    assert sample["pressure"]["memory"]["full"]["avg10"] == 0.02
    assert sample["pressure"]["io"]["some"]["total"] == 77


def test_monitor_refuses_a_candidate_outside_the_ci_slice(tmp_path: Path) -> None:
    """A candidate still in system.slice must produce an explicit refusal, never
    a host-global substitute dressed up as slice evidence.
    """
    stray = "/system.slice/actions.runner.macro.pc-ci-4.service"
    root = tmp_path / "cgroup"
    _write_slice_tree(root, stray)
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, stray))
    assert sample["status"] == "refused"
    assert sample["cgroup"] == stray
    assert "mastermind-ci.slice" in sample["reason"]
    for key in ("cpu", "memory", "memory_events", "pids", "pressure", "cpu_max"):
        assert sample[key] is None, f"{key} must not carry a foreign-cgroup substitute"


def test_monitor_refuses_a_foreign_slice_that_merely_looks_similar(tmp_path: Path) -> None:
    stray = "/other-mastermind-ci.slice/actions.runner.macro.pc-ci-4.service"
    root = tmp_path / "cgroup"
    _write_slice_tree(root, stray)
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, stray))
    assert sample["status"] == "refused"


def test_monitor_refuses_a_slice_candidate_that_is_not_a_service(tmp_path: Path) -> None:
    stray = "/mastermind.slice/mastermind-ci.slice"
    root = tmp_path / "cgroup"
    _write_slice_tree(root, stray)
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, stray))
    assert sample["status"] == "refused"


def test_monitor_degrades_when_slice_evidence_is_unreadable(tmp_path: Path) -> None:
    root = tmp_path / "cgroup"
    (root / CI_CGROUP.lstrip("/")).mkdir(parents=True)
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, CI_CGROUP))
    assert sample["status"] == "degraded"
    assert sample["cgroup"] == CI_CGROUP
    assert sample["cpu"] is None
    assert sample["memory"]["current"] is None


def test_monitor_distinguishes_an_unavailable_field_from_an_observed_zero(
    tmp_path: Path,
) -> None:
    root = tmp_path / "cgroup"
    _write_slice_tree(root, CI_CGROUP, **{"memory.swap.current": None})
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, CI_CGROUP))
    assert sample["status"] == "bound"
    assert sample["memory"]["swap_current"] is None, "absent kernel field is not zero"
    assert sample["memory_events"]["oom_kill"] == 0, "an observed zero stays zero"


def test_monitor_reports_unavailable_when_the_candidate_cgroup_cannot_be_read(
    tmp_path: Path,
) -> None:
    sample = MONITOR.slice_sample(tmp_path / "cgroup", tmp_path / "absent-proc-file")
    assert sample["status"] == "unavailable"
    assert sample["cgroup"] is None
    assert sample["cpu"] is None


def _slice_sample(status: str = "bound", **overrides: object) -> dict:
    sample = {
        "status": status,
        "expected_slice": "mastermind-ci.slice",
        "cgroup": CI_CGROUP,
        "candidate_cgroup": CI_CGROUP,
        "aggregate_cgroup": "/mastermind.slice/mastermind-ci.slice",
        "candidate_identity": {"device": 1, "inode": 41},
        "aggregate_identity": {"device": 1, "inode": 40},
        "aggregate_metric_source": "parent_slice",
        "reason": None,
        "cpu": {
            "usage_usec": 1_000_000,
            "nr_periods": 400,
            "nr_throttled": 20,
            "throttled_usec": 50_000,
        },
        "cpu_max": "800000 100000",
        "limits": {
            "cpu.max": "800000 100000",
            "memory.high": "10737418240",
            "memory.max": "12884901888",
            "memory.swap.max": "2147483648",
        },
        "memory": {"current": 1 << 30, "peak": 2 << 30, "swap_current": 0},
        "memory_events": {"low": 0, "high": 3, "max": 0, "oom": 0, "oom_kill": 0},
        "pids": {"current": 42},
        "pids_events": {"max": 0},
        "pressure": {
            "cpu": {"some": {"avg10": 1.5, "total": 1234}, "full": {"avg10": 0.0, "total": 0}},
            "memory": {"some": {"avg10": 0.1, "total": 99}, "full": {"avg10": 0.02, "total": 11}},
            "io": {"some": {"avg10": 0.2, "total": 77}, "full": {"avg10": 0.03, "total": 7}},
        },
    }
    sample.update(overrides)
    return sample


_SAMPLE_TIMES = count(1)


def _host_sample(slice_payload: dict) -> dict:
    return {
        "time": float(next(_SAMPLE_TIMES)),
        "cpu_percent": 10.0,
        "load": [1.0, 1.0, 1.0],
        "memory_available_bytes": 32 << 30,
        "swap_used_bytes": 0,
        "disk_free_bytes": 100 << 30,
        "slice": slice_payload,
    }


def test_receipt_reduces_bound_slice_samples_into_window_deltas(tmp_path: Path) -> None:
    first = _slice_sample()
    last = _slice_sample(
        cpu={
            "usage_usec": 9_000_000,
            "nr_periods": 900,
            "nr_throttled": 45,
            "throttled_usec": 120_000,
        },
        memory={"current": 3 << 30, "peak": 5 << 30, "swap_current": 1 << 20},
        memory_events={"low": 0, "high": 11, "max": 2, "oom": 0, "oom_kill": 0},
        pids={"current": 61},
        pids_events={"max": 1},
        pressure={
            "cpu": {"some": {"avg10": 2.0, "total": 5234}, "full": {"avg10": 0.1, "total": 40}},
            "memory": {"some": {"avg10": 0.3, "total": 199}, "full": {"avg10": 0.05, "total": 31}},
            "io": {"some": {"avg10": 0.4, "total": 177}, "full": {"avg10": 0.06, "total": 27}},
        },
    )
    result = CAPTURE.slice_metrics([_host_sample(first), _host_sample(last)])

    assert result["status"] == "bound"
    assert result["samples"] == 2
    assert result["expected_slice"] == "mastermind-ci.slice"
    assert result["cgroups"] == [CI_CGROUP]
    assert result["cpu_max"] == "800000 100000"
    assert result["cpu_delta"] == {
        "usage_usec": 8_000_000,
        "nr_periods": 500,
        "nr_throttled": 25,
        "throttled_usec": 70_000,
    }
    assert result["memory_events_delta"] == {"low": 0, "high": 8, "max": 2, "oom": 0, "oom_kill": 0}
    assert result["pids_events_delta"] == {"max": 1}
    assert result["memory_current_peak_bytes"] == 3 << 30
    assert result["memory_swap_peak_bytes"] == 1 << 20
    assert result["pids_current_peak"] == 61
    assert result["pressure_total_delta"]["memory"]["full"] == 20
    assert result["pressure_total_delta"]["io"]["some"] == 100


def test_receipt_refuses_a_single_sample_as_a_missing_endpoint() -> None:
    result = CAPTURE.slice_metrics([_host_sample(_slice_sample())])

    assert result["status"] == "refused"
    assert result["samples"] == 1
    assert "distinct start and end samples" in result["reason"]
    for key in (
        "candidate_identity",
        "aggregate_identity",
        "cpu_max",
        "effective_limits",
        "cpu_delta",
        "memory_events_delta",
        "pids_events_delta",
        "pressure_total_delta",
        "memory_current_peak_bytes",
        "memory_swap_peak_bytes",
        "memory_peak_bytes_cgroup_lifetime",
        "pids_current_peak",
    ):
        assert result[key] is None, key


@pytest.mark.parametrize(
    ("case", "expected_status", "expected_reason"),
    [
        (
            "nonfinite_time",
            "refused",
            "aggregate samples are not strictly time ordered",
        ),
        ("non_bound_status", "unavailable", "slice metrics are unavailable"),
        (
            "malformed_parent",
            "refused",
            "aggregate cgroup is missing or not the fixed parent slice",
        ),
    ],
)
def test_single_sample_preserves_stronger_refusal_before_missing_endpoint(
    case: str, expected_status: str, expected_reason: str
) -> None:
    slice_payload = _slice_sample()
    sample = _host_sample(slice_payload)
    if case == "nonfinite_time":
        sample["time"] = float("nan")
    elif case == "non_bound_status":
        slice_payload.update(
            status="unavailable", reason="slice metrics are unavailable"
        )
    else:
        slice_payload["aggregate_cgroup"] = "/wrong.slice"

    result = CAPTURE.slice_metrics([sample])

    assert result["status"] == expected_status
    assert result["reason"] == expected_reason
    assert result["samples"] == 1


def test_receipt_labels_memory_peak_as_a_cgroup_lifetime_fact() -> None:
    """memory.peak is a cgroup-lifetime high-water mark. Presenting it as a
    run-local peak without a documented reset ceremony would overstate what the
    receipt observed.
    """
    result = CAPTURE.slice_metrics(
        [_host_sample(_slice_sample()), _host_sample(_slice_sample())]
    )
    assert "memory_peak_bytes_cgroup_lifetime" in result
    assert result["memory_peak_bytes_cgroup_lifetime"] == 2 << 30
    assert "memory_peak_bytes" not in result, "no unqualified run-local peak"
    assert result["memory_peak_is_run_local"] is False


def test_receipt_refuses_aggregate_numbers_when_any_sample_left_the_ci_slice() -> None:
    samples = [
        _host_sample(_slice_sample()),
        _host_sample(
            _slice_sample(
                "refused",
                cgroup="/system.slice/x.service",
                cpu=None,
                cpu_max=None,
                memory=None,
                memory_events=None,
                pids=None,
                pids_events=None,
                pressure=None,
                reason="candidate cgroup is not a .service under /mastermind-ci.slice",
            )
        ),
    ]
    result = CAPTURE.slice_metrics(samples)
    assert result["status"] == "refused"
    for key in (
        "cpu_delta",
        "memory_events_delta",
        "pids_events_delta",
        "pressure_total_delta",
        "memory_current_peak_bytes",
    ):
        assert result.get(key) is None, f"{key} must not be reported off refused evidence"
    assert "mastermind-ci.slice" in result["reason"]


def test_receipt_reports_degraded_without_partial_aggregate_numbers() -> None:
    result = CAPTURE.slice_metrics(
        [
            _host_sample(_slice_sample()),
            _host_sample(_slice_sample("degraded", cpu=None, memory_events=None)),
        ]
    )
    assert result["status"] == "degraded"
    assert result["cpu_delta"] is None


def test_receipt_reports_absent_slice_evidence_rather_than_inventing_it() -> None:
    result = CAPTURE.slice_metrics([])
    assert result["status"] == "absent"
    assert result["cpu_delta"] is None
    legacy = CAPTURE.slice_metrics([{"time": 1.0, "cpu_percent": 1.0}])
    assert legacy["status"] == "absent", "a pre-slice P1/P2 sample is absent, not bound"


def test_existing_host_metrics_reduction_is_unchanged_by_the_slice_extension(
    tmp_path: Path,
) -> None:
    """P1/P2 receipts must stay honestly readable: the host-global reduction keeps
    its exact previous keys and values whether or not slice evidence is present.
    """
    path = tmp_path / "metrics.jsonl"
    with_slice = _host_sample(_slice_sample())
    without_slice = {key: value for key, value in with_slice.items() if key != "slice"}
    path.write_text(json.dumps(with_slice) + "\n", encoding="utf-8")
    extended = CAPTURE.metrics(path)
    path.write_text(json.dumps(without_slice) + "\n", encoding="utf-8")
    legacy = CAPTURE.metrics(path)
    assert extended == legacy
    assert set(legacy) == {
        "samples",
        "cpu_peak_percent",
        "cpu_mean_percent",
        "load_peak_1m",
        "memory_available_min_bytes",
        "swap_used_peak_bytes",
        "disk_free_min_bytes",
    }


# ── C3R-A: aggregate CI slice + sealed fourth root ───────────────────────────
# One slice bounds pc-ci-1..4 together. The renderer stays OUTSIDE it: that is
# the whole point of an aggregate CI envelope, and it is why render must never
# inherit the slice or CI's KillMode=control-group.

SLICE_TEMPLATE = ROOT / "ops" / "runner-host" / "pc" / "mastermind-ci.slice.template"
CI_SERVICE_TEMPLATE = (
    ROOT / "ops" / "runner-host" / "pc" / "actions-runner-ci.service.template"
)


def test_ci_slice_template_carries_the_exact_frozen_envelope() -> None:
    unit = SLICE_TEMPLATE.read_text(encoding="utf-8")
    for directive in (
        "CPUQuota=800%",
        "CPUQuotaPeriodSec=100ms",
        "MemoryHigh=10G",
        "MemoryMax=12G",
        "MemorySwapMax=2G",
    ):
        assert directive in unit, f"frozen envelope lost {directive}"
    for accounting in (
        "CPUAccounting=true",
        "MemoryAccounting=true",
        "IOAccounting=true",
        "TasksAccounting=true",
    ):
        assert accounting in unit, f"{accounting} is required to receipt the counters"


def test_ci_slice_leaves_first_wave_tunables_deliberately_inherited() -> None:
    """AllowedCPUs/CPUWeight/IOWeight/TasksMax stay unset in this wave; their
    counters are receipted instead. Setting one needs a new measured carrier.
    """
    unit = SLICE_TEMPLATE.read_text(encoding="utf-8")
    for directive in ("AllowedCPUs=", "CPUWeight=", "IOWeight=", "TasksMax="):
        assert directive not in unit, f"{directive} requires a new measured carrier"


def test_ci_slice_is_ci_only_and_never_absorbs_render() -> None:
    unit = SLICE_TEMPLATE.read_text(encoding="utf-8")
    assert "render" in unit.lower(), "the template must state render is outside"
    directives = [line.split("=", 1)[0] for line in unit.splitlines() if "=" in line]
    assert "KillMode" not in directives, "KillMode belongs to the CI service"
    for forbidden in ("pc-render", "render-linux"):
        assert f"Slice={forbidden}" not in unit


def test_only_the_pc_ci_service_template_joins_the_ci_slice() -> None:
    """No checked-in render or cache unit may join the CI envelope."""
    joined = sorted(
        path.name
        for path in (ROOT / "ops" / "runner-host").rglob("*")
        if path.is_file()
        and path.suffix in {".template", ".service", ".timer", ".plist"}
        and "Slice=mastermind-ci.slice"
        in path.read_text(encoding="utf-8", errors="replace")
    )
    assert joined == ["actions-runner-ci.service.template"]


def test_pc_ci_service_joins_the_slice_without_losing_its_sandbox() -> None:
    unit = CI_SERVICE_TEMPLATE.read_text(encoding="utf-8")
    assert "Slice=mastermind-ci.slice" in unit
    # Every pre-existing seal survives the slice migration.
    for preserved in (
        "KillMode=control-group",
        "ReadOnlyPaths=__RUNNER_ROOT__ /var/cache/mastermind-ci/macro.git",
        "ReadWritePaths=__RUNNER_ROOT__/_work __RUNNER_ROOT__/_diag",
        "UMask=0022",
        "NoNewPrivileges=true",
        "ProtectSystem=strict",
        "InaccessiblePaths=/mnt/c /mnt/d /home/longr /root",
        "StartLimitIntervalSec=0",
    ):
        assert preserved in unit, f"slice migration dropped {preserved}"
    assert "--require-slice" in unit, "a slice-joined unit must demand its binding"


def test_cleanup_admits_exactly_the_fourth_sealed_root(tmp_path: Path) -> None:
    roots = {str(path) for path in CLEANUP.PC_CI_ROOTS}
    assert roots == {
        "/opt/mastermind-ci/runner-1",
        "/opt/mastermind-ci/runner-2",
        "/opt/mastermind-ci/runner-3",
        "/opt/mastermind-ci/runner-4",
    }


def test_cleanup_refuses_a_fifth_or_foreign_runner_root(tmp_path: Path) -> None:
    for name in ("runner-5", "runner-0", "render-1"):
        stray = tmp_path / name
        (stray / "_work").mkdir(parents=True)
        with pytest.raises(RuntimeError, match="sealed PC CI allowlist"):
            CLEANUP.scrub_pc_state(stray)


def test_resource_guard_thresholds_are_versioned_apart_from_slice_ceilings() -> None:
    """Guard thresholds and slice ceilings move independently: retuning a refusal
    threshold must not read as a change to the measured resource envelope.
    """
    assert RESOURCE_GUARD.THRESHOLDS_VERSION == (
        "mastermind.ci_resource_guard_thresholds.v1"
    )
    preflight = RESOURCE_GUARD.PREFLIGHT_PROFILES["four-slot-canary"]
    assert preflight["memory_available_min_bytes"] == 20 * 1024**3
    assert preflight["swap_used_max_bytes"] == 512 * 1024**2
    assert preflight["psi_full_avg10_max"] == 0.10
    assert RESOURCE_GUARD.PREFLIGHT_PROFILES["steady"]["memory_available_min_bytes"] == (
        4 * 1024**3
    )


def test_resource_guard_refuses_a_candidate_outside_the_ci_slice() -> None:
    reasons, evidence = RESOURCE_GUARD.slice_reasons(
        cgroup_root=Path("/nonexistent"),
        cgroup="/system.slice/actions.runner.macro.pc-ci-4.service",
        profile="steady",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert any("mastermind-ci.slice" in reason for reason in reasons)
    assert evidence["bound"] is False


def test_resource_guard_receipts_memory_events_without_gating_on_them(
    tmp_path: Path,
) -> None:
    """Superseded contract. This asserted a refusal on cumulative memory.events;
    the adversarial review showed `max` and `oom` are "was ABOUT TO" reclaim
    counters rather than kills, and that every field here is cumulative over the
    slice lifetime, so any of them as a gate strands the slot permanently. They
    are receipted as evidence and gate nothing.
    """
    root = tmp_path / "cgroup"
    _write_slice_tree(
        root, CI_CGROUP, **{"memory.events": "low 0\nhigh 0\nmax 1\noom 0\noom_kill 2\n"}
    )
    reasons, evidence = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="steady",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert reasons == []
    assert evidence["memory_events"]["oom_kill"] == 2
    assert evidence["memory_events"]["max"] == 1


def test_resource_guard_four_slot_preflight_gates_memory_swap_and_pressure(
    tmp_path: Path,
) -> None:
    root = tmp_path / "cgroup"
    _write_slice_tree(root, CI_CGROUP)
    clean, _ = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="four-slot-canary",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert clean == []

    thin, _ = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="four-slot-canary",
        memory_available_bytes=12 * 1024**3,
        swap_used_bytes=1024**3,
        require_slice=True,
    )
    assert any("20 GiB" in reason or "memory available" in reason for reason in thin)
    assert any("swap" in reason for reason in thin)

    _write_slice_tree(
        root,
        CI_CGROUP,
        **{
            "memory.pressure": (
                "some avg10=5.00 avg60=4.00 avg300=3.00 total=9999\n"
                "full avg10=0.90 avg60=0.50 avg300=0.20 total=500\n"
            )
        },
    )
    stalled, _ = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="four-slot-canary",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert any("pressure" in reason for reason in stalled)


def test_resource_guard_memory_floor_stays_guest_wide_for_render_headroom(
    tmp_path: Path,
) -> None:
    """The renderer lives OUTSIDE the CI slice, so a slice-local memory floor
    would be blind to it. The floor must stay a guest-wide MemAvailable read.
    """
    root = tmp_path / "cgroup"
    _write_slice_tree(root, CI_CGROUP, **{"memory.current": "1048576\n"})
    reasons, evidence = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="four-slot-canary",
        memory_available_bytes=2 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert reasons, "a nearly-idle slice must not excuse a starved guest"
    assert evidence["memory_floor_is_guest_wide"] is True


def test_cumulative_memory_high_reclaim_never_strands_a_listener(tmp_path: Path) -> None:
    """memory.events counters are CUMULATIVE over the slice lifetime. `high` is
    MemoryHigh reclaim working as designed; refusing a start on it would mean
    that once CI ever touched 10G, every later listener start refuses forever.
    Only real kills (max/oom/oom_kill) may gate a start.
    """
    root = tmp_path / "cgroup"
    _write_slice_tree(
        root,
        CI_CGROUP,
        **{"memory.events": "low 0\nhigh 4096\nmax 0\noom 0\noom_kill 0\n"},
    )
    reasons, evidence = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="four-slot-canary",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert reasons == [], "cumulative MemoryHigh reclaim must not wedge the slot"
    assert evidence["memory_events"]["high"] == 4096, "but it is still receipted"


def test_binding_alone_does_not_prove_the_envelope_is_enforced(tmp_path: Path) -> None:
    """systemd auto-creates an UNDEFINED slice, so a unit carrying
    `Slice=mastermind-ci.slice` binds successfully even when no slice file was
    ever installed -- it just inherits no limits. Binding therefore proves
    membership, not enforcement. Running a four-slot capacity diagnostic against
    an unenforced envelope would measure nothing while looking bound and green,
    so the stricter profile must refuse an unlimited cpu.max.
    """
    root = tmp_path / "cgroup"
    _write_slice_tree(root, CI_CGROUP, **{"cpu.max": "max 100000\n"})
    reasons, evidence = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="four-slot-canary",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert any("unenforced" in reason or "cpu.max" in reason for reason in reasons)
    assert evidence["cpu_max"] == "max 100000"

    # Steady state without --require-slice must NOT inherit this refusal:
    # pc-ci-1..3 run today without that opt-in, and this carrier installs
    # nothing. Once --require-slice is set, the exact parent envelope is
    # deliberately mandatory for every profile.
    steady, _ = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="steady",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=False,
    )
    assert steady == [], "an unenforced slice must not wedge today's three slots"


def test_enforced_envelope_passes_the_four_slot_preflight(tmp_path: Path) -> None:
    root = tmp_path / "cgroup"
    _write_slice_tree(root, CI_CGROUP, **{"cpu.max": "800000 100000\n"})
    reasons, evidence = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=CI_CGROUP,
        profile="four-slot-canary",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert reasons == []
    assert evidence["cpu_max"] == "800000 100000"


# ── C3R-A review repairs (adversarial review 2026-09-01) ─────────────────────


def test_no_cumulative_memory_event_counter_can_gate_a_start(tmp_path: Path) -> None:
    """REVIEW BLOCKER 1. Every memory.events counter is cumulative over the slice
    LIFETIME, and cgroup-v2 defines `max` and `oom` as "was ABOUT TO" reclaim /
    allocation-failure counters, not kills. Only `oom_kill` counts processes
    actually killed -- and it is cumulative too, so the guard cannot tell an
    OOM-kill three weeks ago from one a second ago. Gating a start on ANY of them
    strands the slot permanently after one transient event, which is the exact
    failure the `high` reasoning already rejected. They are evidence, not gates.
    """
    root = tmp_path / "cgroup"
    for events in (
        "low 0\nhigh 9\nmax 0\noom 0\noom_kill 0\n",
        "low 0\nhigh 0\nmax 7\noom 0\noom_kill 0\n",
        "low 0\nhigh 0\nmax 0\noom 5\noom_kill 0\n",
        "low 0\nhigh 0\nmax 0\noom 0\noom_kill 3\n",
    ):
        _write_slice_tree(root, CI_CGROUP, **{"memory.events": events})
        reasons, evidence = RESOURCE_GUARD.slice_reasons(
            cgroup_root=root,
            cgroup=CI_CGROUP,
            profile="four-slot-canary",
            memory_available_bytes=32 * 1024**3,
            swap_used_bytes=0,
            require_slice=True,
        )
        assert reasons == [], f"cumulative counters must not wedge the slot: {events!r}"
        assert evidence["memory_events"] is not None, "but they are still receipted"


def test_reducer_treats_any_unknown_status_as_non_bound() -> None:
    """REVIEW BLOCKER 2. Worst-status selection scanned a fixed whitelist, so a
    sample whose status was outside it became invisible and the window resolved
    to `bound` -- leaking foreign host numbers into aggregate fields and
    falsifying the docstring, the runbook and the workstream record.
    """
    forged = _slice_sample(
        "host-global-fallback",
        cgroup="/system.slice/whatever.service",
        memory={"current": 99_999_999, "peak": 1, "swap_current": 0},
    )
    result = CAPTURE.slice_metrics([_host_sample(_slice_sample()), _host_sample(forged)])
    assert result["status"] != "bound"
    assert result["memory_current_peak_bytes"] is None
    assert result["cpu_delta"] is None


def test_reducer_refuses_a_window_spanning_more_than_one_cgroup() -> None:
    """A candidate that changed cgroups mid-run has no honest aggregate: first/last
    deltas would silently straddle two different cgroups.
    """
    moved = _slice_sample(cgroup="/mastermind.slice/mastermind-ci.slice/actions.runner.macro.pc-ci-2.service")
    result = CAPTURE.slice_metrics([_host_sample(_slice_sample()), _host_sample(moved)])
    assert result["status"] != "bound"
    assert len(result["cgroups"]) == 2
    assert result["cpu_delta"] is None


def test_reducer_refuses_absent_required_first_sample_fields() -> None:
    """A missing required endpoint is unknown, never zero or a partial green.

    Exact review 5084468618 tightened the earlier per-key-null behavior: missing
    required acceptance keys poison the entire numeric window.
    """
    first = _slice_sample(
        cpu={"usage_usec": 10},
        pressure={"memory": {"full": {"avg10": 0.0, "total": 11}}},
    )
    last = _slice_sample(
        cpu={
            "usage_usec": 50,
            "nr_periods": 10_000,
            "nr_throttled": 9_000,
            "throttled_usec": 7_000_000,
        },
        pressure={
            "memory": {"full": {"avg10": 0.0, "total": 31}},
            "io": {"full": {"avg10": 0.0, "total": 900_000}},
        },
    )
    _assert_poisoned_window(
        CAPTURE.slice_metrics([_host_sample(first), _host_sample(last)])
    )


def test_monitor_degrades_when_any_core_acceptance_file_is_missing(tmp_path: Path) -> None:
    """REVIEW SHOULD-FIX 4. The degraded predicate was an `and`, so a slice with
    only memory.current readable reported `bound` with every acceptance counter
    None -- which an acceptance check for "zero memory.events delta" reads as
    satisfied.
    """
    root = tmp_path / "cgroup"
    node = root / CI_CGROUP.lstrip("/")
    node.mkdir(parents=True)
    (node / "memory.current").write_text("123\n", encoding="utf-8")
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, CI_CGROUP))
    assert sample["status"] == "degraded"
    assert CAPTURE.slice_metrics([_host_sample(sample)])["status"] == "degraded"


def test_monitor_anchors_the_slice_and_refuses_traversal(tmp_path: Path) -> None:
    """REVIEW NIT 9. Component-anywhere matching accepted a nested look-alike, and
    `..` was never normalised, so a forged cgroup could assemble fully `bound`
    evidence from a directory outside the slice entirely.
    """
    for stray in (
        "/foo/mastermind-ci.slice/x.service",
        "/user.slice/user-1000.slice/mastermind-ci.slice/evil.service",
        "/system.slice/x.service/mastermind-ci.slice/y.service",
        "/mastermind-ci.slice/../../system.slice/pc-render-1.service",
    ):
        root = tmp_path / "cgroup"
        _write_slice_tree(root, stray.replace("..", "dotdot"))
        sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, stray))
        assert sample["status"] == "refused", f"{stray} must be refused"
        assert sample["memory"] is None
    # The real, anchored shape still binds.
    root = tmp_path / "ok"
    _write_slice_tree(root, CI_CGROUP)
    assert MONITOR.slice_sample(root, _proc_cgroup(tmp_path, CI_CGROUP))["status"] == "bound"


def test_resource_guard_binding_check_is_anchored_too() -> None:
    for stray in (
        "/foo/mastermind-ci.slice/x.service",
        "/mastermind-ci.slice/../../system.slice/x.service",
    ):
        assert RESOURCE_GUARD.is_bound_to_ci_slice(stray) is False
    assert RESOURCE_GUARD.is_bound_to_ci_slice(CI_CGROUP) is True


# ── C3R-A: forward-compatible receipt identities (Sol ruling 2026-09-01) ─────
# Additive identities so the EXISTING receipt contract can carry four-slot and
# elastic evidence truthfully later. No second receipt format or store, no
# runtime behaviour change, and historical P1/P2/P4 receipts stay readable.


def test_receipt_carries_forward_compatible_identities_without_a_schema_break() -> None:
    receipt = CAPTURE.build_identity_fields(
        execution_profile_id="pc-ci.persistent.v1",
        admission_policy_version="mastermind.ci_resource_guard_thresholds.v1",
        workflow_job_queued_at=None,
        runner_job_started_at=None,
    )
    assert receipt["execution_profile_id"] == "pc-ci.persistent.v1"
    assert receipt["admission_policy_version"] == (
        "mastermind.ci_resource_guard_thresholds.v1"
    )
    assert receipt["workflow_job_queued_at"] is None
    assert receipt["runner_job_started_at"] is None
    assert receipt["queue_wait_seconds"] is None


def test_queue_wait_is_derived_only_from_two_ordered_timestamps() -> None:
    ordered = CAPTURE.build_identity_fields(
        execution_profile_id="pc-ci.persistent.v1",
        admission_policy_version="v1",
        workflow_job_queued_at="2026-09-01T10:00:00Z",
        runner_job_started_at="2026-09-01T10:02:30Z",
    )
    assert ordered["queue_wait_seconds"] == 150.0

    # An observed zero is a real measurement and must stay distinct from null.
    instant = CAPTURE.build_identity_fields(
        execution_profile_id="pc-ci.persistent.v1",
        admission_policy_version="v1",
        workflow_job_queued_at="2026-09-01T10:00:00Z",
        runner_job_started_at="2026-09-01T10:00:00Z",
    )
    assert instant["queue_wait_seconds"] == 0.0
    assert instant["queue_wait_seconds"] is not None


def test_queue_wait_is_null_when_unavailable_out_of_order_or_unparseable() -> None:
    for queued, started in (
        (None, "2026-09-01T10:02:30Z"),
        ("2026-09-01T10:00:00Z", None),
        (None, None),
        ("2026-09-01T10:02:30Z", "2026-09-01T10:00:00Z"),   # out of order
        ("not-a-timestamp", "2026-09-01T10:00:00Z"),
        ("", ""),
    ):
        fields = CAPTURE.build_identity_fields(
            execution_profile_id="pc-ci.persistent.v1",
            admission_policy_version="v1",
            workflow_job_queued_at=queued,
            runner_job_started_at=started,
        )
        assert fields["queue_wait_seconds"] is None, (queued, started)


def test_queue_wait_is_separate_from_checkout_dependency_test_and_wall_timing() -> None:
    """Sol ruling: keep checkout/dependency/test/wall timing separate. Queue wait
    measures time before the runner picked the job up; it must never be folded
    into an execution duration.
    """
    source = (ROOT / "scripts" / "capture_ci_canary_receipt.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build_identity_fields"
    )
    body = ast.dump(fn)
    for unrelated in ("checkout_seconds", "dependency_seconds", "test_seconds", "wall_seconds"):
        assert unrelated not in body, f"queue wait must not touch {unrelated}"


def test_identity_fields_are_additive_so_historical_receipts_stay_readable() -> None:
    """The receipt schema stays ci.selfhosted_canary_receipt.v2. A P1/P2/P4
    receipt simply lacks the new keys, and every pre-existing key keeps its
    exact name and meaning, so no comparator migration is needed.
    """
    source = (ROOT / "scripts" / "capture_ci_canary_receipt.py").read_text(encoding="utf-8")
    assert '"schema": "ci.selfhosted_canary_receipt.v2"' in source
    assert "ci.selfhosted_canary_receipt.v3" not in source
    added = set(
        CAPTURE.build_identity_fields(
            execution_profile_id="x",
            admission_policy_version="y",
            workflow_job_queued_at=None,
            runner_job_started_at=None,
        )
    )
    # None of the added names may collide with an existing receipt field.
    existing = {
        "schema", "runner_kind", "runner_name", "tested_sha", "base_sha", "pack",
        "plan_sha256", "logical_jobs", "executed_jobs", "failed_jobs", "exit_code",
        "result", "prewarm", "prewarm_seconds", "origin_fetch_seconds",
        "checkout_seconds", "dependency_seconds", "test_seconds", "wall_seconds",
        "cache_bytes_before", "cache_bytes_after", "workspace_object_bytes",
        "resources", "ci_slice", "fragment_schema", "fragment_plan_sha256",
    }
    assert added & existing == set(), added & existing
    # And the comparator's parity allowlist must not start reading them.
    comparator = (ROOT / "scripts" / "compare_ci_canary_receipts.py").read_text(encoding="utf-8")
    for name in added:
        assert f'"{name}"' not in comparator, f"{name} must not enter parity comparison"


def test_admission_policy_digest_tracks_thresholds_not_slice_ceilings() -> None:
    """Sol ruling: admission policy identity must be separate from slice
    ceilings. The digest is computed over the guard's threshold profiles only;
    the envelope lives in mastermind-ci.slice.template and is not an input.
    """
    digest = RESOURCE_GUARD.admission_policy_digest()
    assert digest == RESOURCE_GUARD.admission_policy_digest(), "must be stable"
    assert len(digest) == 16

    source = (
        ROOT / "ops" / "runner-host" / "pc" / "mastermind_ci_resource_guard.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "admission_policy_digest"
    )
    # Inspect executable code only: the docstring names the ceilings precisely to
    # say they are NOT inputs, and that sentence is worth keeping.
    statements = [node for node in fn.body if not (
        isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )]
    body = ast.dump(ast.Module(body=statements, type_ignores=[]))
    assert "PREFLIGHT_PROFILES" in body
    for ceiling in ("CPUQuota", "MemoryHigh", "MemoryMax", "MemorySwapMax", "cpu_max"):
        assert ceiling not in body, f"slice ceiling {ceiling} must not feed the digest"


# ── C3R-A follow-up: systemd slice names are a cgroup HIERARCHY ──────────────
# Found on the real host 2026-09-02, not by any test: systemd treats `-` in a
# slice unit name as a path separator, so `mastermind-ci.slice` is a CHILD of an
# implicit `mastermind.slice` and its cgroup is
#   /mastermind.slice/mastermind-ci.slice/<unit>.service
# never /mastermind-ci.slice/<unit>.service.
#
# The first anchored matcher required the slice at components[0], so a correctly
# configured pc-ci-1 was REFUSED with exit 78 and the slot could not start. The
# fix anchors on the full systemd-derived parent chain, which keeps the nested
# look-alike refusals that motivated anchoring in the first place.

REAL_HOST_CGROUP = (
    "/mastermind.slice/mastermind-ci.slice/"
    "actions.runner.mastermindx-market-intelligence-macro.pc-ci-1.service"
)


def test_expected_slice_chain_is_derived_from_the_systemd_name() -> None:
    assert MONITOR.expected_slice_chain("mastermind-ci.slice") == [
        "mastermind.slice",
        "mastermind-ci.slice",
    ]
    assert MONITOR.expected_slice_chain("solo.slice") == ["solo.slice"]
    assert MONITOR.expected_slice_chain("a-b-c.slice") == [
        "a.slice",
        "a-b.slice",
        "a-b-c.slice",
    ]


def test_monitor_binds_the_real_systemd_slice_path(tmp_path: Path) -> None:
    """The exact cgroup a live pc-ci listener reports once Slice= is set."""
    root = tmp_path / "cgroup"
    _write_slice_tree(root, REAL_HOST_CGROUP)
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, REAL_HOST_CGROUP))
    assert sample["status"] == "bound", sample["reason"]
    assert sample["cgroup"] == REAL_HOST_CGROUP
    assert sample["cpu"]["nr_periods"] == 400


def test_resource_guard_binds_the_real_systemd_slice_path() -> None:
    assert RESOURCE_GUARD.is_bound_to_ci_slice(REAL_HOST_CGROUP) is True


def test_slice_hierarchy_fix_still_refuses_every_nested_look_alike() -> None:
    """The anchoring that motivated the original fix must survive."""
    for stray in (
        "/user.slice/user-1000.slice/mastermind-ci.slice/evil.service",
        "/system.slice/x.service/mastermind.slice/mastermind-ci.slice/y.service",
        "/foo.slice/mastermind-ci.slice/x.service",
        "/mastermind.slice/other-mastermind-ci.slice/x.service",
        "/mastermind.slice/mastermind-ci.slice/../../system.slice/x.service",
        "/mastermind.slice/mastermind-ci.slice",
        "/system.slice/actions.runner.macro.pc-ci-1.service",
    ):
        assert MONITOR._is_bound_to_ci_slice(stray) is False, stray
        assert RESOURCE_GUARD.is_bound_to_ci_slice(stray) is False, stray


def test_aggregate_metrics_come_from_the_slice_node_not_the_candidate_leaf(
    tmp_path: Path,
) -> None:
    """Second real-host defect (2026-09-02): the envelope and the AGGREGATE
    counters live on the slice node, not on the candidate's leaf `.service`
    cgroup. Reading the leaf yields per-candidate numbers with no ceilings —
    and labelling those "aggregate" is exactly the false-proof shape this
    module exists to refuse. Measured on the host: the slice node carries
    cpu.max `800000 100000` while a leaf carries none.
    """
    root = tmp_path / "cgroup"
    slice_node = root / "mastermind.slice" / "mastermind-ci.slice"
    # Aggregate truth on the slice node.
    _write_slice_tree(root, "/mastermind.slice/mastermind-ci.slice")
    # Decoy per-candidate values on the leaf; these must NOT be reported.
    _write_slice_tree(
        root,
        REAL_HOST_CGROUP,
        at_slice=False,
        **{
            "memory.current": "999999999\n",
            "cpu.max": "max 100000\n",
            "cpu.stat": "usage_usec 7\nnr_periods 7\nnr_throttled 7\nthrottled_usec 7\n",
        },
    )
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, REAL_HOST_CGROUP))

    assert sample["status"] == "bound"
    assert sample["cgroup"] == REAL_HOST_CGROUP, "membership is still the candidate's"
    assert sample["slice_cgroup"] == "/mastermind.slice/mastermind-ci.slice"
    # Values must be the slice's, never the leaf decoys.
    assert sample["cpu_max"] == "800000 100000"
    assert sample["memory"]["current"] == 1_073_741_824
    assert sample["cpu"]["nr_periods"] == 400


def test_guard_reads_the_envelope_from_the_slice_node(tmp_path: Path) -> None:
    root = tmp_path / "cgroup"
    _write_slice_tree(root, "/mastermind.slice/mastermind-ci.slice")
    _write_slice_tree(root, REAL_HOST_CGROUP, at_slice=False, **{"cpu.max": "max 100000\n"})
    reasons, evidence = RESOURCE_GUARD.slice_reasons(
        cgroup_root=root,
        cgroup=REAL_HOST_CGROUP,
        profile="four-slot-canary",
        memory_available_bytes=32 * 1024**3,
        swap_used_bytes=0,
        require_slice=True,
    )
    assert evidence["cpu_max"] == "800000 100000", "envelope read from the slice"
    assert reasons == [], "an enforced envelope must not be called unenforced"


# C3R-A merged-substrate repair: every test below names a false-proof mutant.


def test_guard_and_monitor_require_one_direct_service_below_the_real_slice() -> None:
    for cgroup in (
        "/mastermind.slice/mastermind-ci.slice/outer.service/inner.scope",
        "/mastermind.slice/mastermind-ci.slice/nested/inner.service",
        "/mastermind.slice/mastermind-ci.slice/.service",
        "mastermind.slice/mastermind-ci.slice/runner.service",
        "/mastermind.slice/mastermind-ci.slice/runner.service/",
    ):
        assert RESOURCE_GUARD.is_bound_to_ci_slice(cgroup) is False, cgroup
        assert MONITOR._is_bound_to_ci_slice(cgroup) is False, cgroup


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("cpu.max", None),
        ("cpu.max", "800001 100000\n"),
        ("memory.high", "max\n"),
        ("memory.max", "not-a-number\n"),
        ("memory.swap.max", "2147483647\n"),
    ],
)
def test_guard_refuses_every_missing_or_drifted_parent_limit(
    tmp_path: Path, name: str, value: str | None
) -> None:
    root = tmp_path / "cgroup"
    node = _write_slice_tree(root, CI_CGROUP)
    path = node / name
    if value is None:
        path.unlink()
    else:
        path.write_text(value, encoding="utf-8")
    reasons, evidence = RESOURCE_GUARD.slice_reasons(
        root, CI_CGROUP, "four-slot-canary", 32 * 1024**3, 0, require_slice=True
    )
    assert any(name.split(".", 1)[0] in reason for reason in reasons)
    assert evidence["effective_limits"][name] != RESOURCE_GUARD.EXPECTED_LIMITS[name]


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("memory.pressure", None),
        ("io.pressure", "some avg10=0.00 total=1\n"),
        ("memory.pressure", "full total=1\n"),
        ("io.pressure", "full avg10=bad total=1\n"),
        ("memory.pressure", "full avg10=nan total=1\n"),
        ("io.pressure", "full avg10=inf total=1\n"),
        ("memory.pressure", "full avg10=0.10 total=1\n"),
    ],
)
def test_four_slot_preflight_requires_finite_strict_memory_and_io_psi(
    tmp_path: Path, name: str, content: str | None
) -> None:
    root = tmp_path / "cgroup"
    node = _write_slice_tree(root, CI_CGROUP)
    path = node / name
    if content is None:
        path.unlink()
    else:
        path.write_text(content, encoding="utf-8")
    reasons, _ = RESOURCE_GUARD.slice_reasons(
        root, CI_CGROUP, "four-slot-canary", 32 * 1024**3, 0, require_slice=True
    )
    assert any(name.split(".", 1)[0] in reason for reason in reasons)


def _assert_poisoned_window(result: dict) -> None:
    assert result["status"] != "bound"
    for key in (
        "cpu_delta",
        "memory_events_delta",
        "pids_events_delta",
        "pressure_total_delta",
        "memory_current_peak_bytes",
        "memory_swap_peak_bytes",
        "memory_peak_bytes_cgroup_lifetime",
        "pids_current_peak",
    ):
        assert result[key] is None, key


@pytest.mark.parametrize("family", ["cpu", "memory", "pids", "pressure"])
def test_reducer_refuses_each_cumulative_counter_decrease(family: str) -> None:
    first_slice = _slice_sample()
    last_slice = _slice_sample()
    if family == "cpu":
        last_slice["cpu"] = {**last_slice["cpu"], "usage_usec": 999_999}
    elif family == "memory":
        last_slice["memory_events"] = {**last_slice["memory_events"], "high": 2}
    elif family == "pids":
        first_slice["pids_events"] = {"max": 2}
        last_slice["pids_events"] = {"max": 1}
    else:
        first_slice["pressure"]["memory"]["full"]["total"] = 12
        last_slice["pressure"]["memory"]["full"]["total"] = 11
    _assert_poisoned_window(
        CAPTURE.slice_metrics([_host_sample(first_slice), _host_sample(last_slice)])
    )


def test_reducer_refuses_backward_time_and_candidate_or_parent_identity_swaps() -> None:
    first = _host_sample(_slice_sample())
    last = _host_sample(_slice_sample())
    last["time"] = first["time"] - 1
    _assert_poisoned_window(CAPTURE.slice_metrics([first, last]))
    for field in ("candidate_identity", "aggregate_identity"):
        left = _host_sample(_slice_sample())
        right_payload = _slice_sample()
        right_payload[field] = {"device": 9, "inode": 9}
        _assert_poisoned_window(CAPTURE.slice_metrics([left, _host_sample(right_payload)]))


def test_reducer_refuses_a_missing_middle_endpoint() -> None:
    first = _host_sample(_slice_sample())
    middle = {"time": first["time"] + 0.5}
    last = _host_sample(_slice_sample())
    _assert_poisoned_window(CAPTURE.slice_metrics([first, middle, last]))


@pytest.mark.parametrize(
    "limits",
    [
        None,
        {},
        {"cpu.max": "max 100000"},
        {
            "cpu.max": "800000 100000",
            "memory.high": "10737418240",
            "memory.max": "12884901888",
            "memory.swap.max": "2147483647",
        },
    ],
)
def test_reducer_refuses_missing_malformed_or_drifted_parent_limits(
    limits: object,
) -> None:
    first = _host_sample(_slice_sample(limits=limits))
    last = _host_sample(_slice_sample(limits=limits))
    _assert_poisoned_window(CAPTURE.slice_metrics([first, last]))


def test_reducer_refuses_cpu_max_that_disagrees_with_the_limit_tuple() -> None:
    first = _host_sample(_slice_sample(cpu_max="max 100000"))
    last = _host_sample(_slice_sample(cpu_max="max 100000"))
    _assert_poisoned_window(CAPTURE.slice_metrics([first, last]))


def test_monitor_receipts_freeze_candidate_and_parent_identity(tmp_path: Path) -> None:
    root = tmp_path / "cgroup"
    _write_slice_tree(root, CI_CGROUP)
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, CI_CGROUP))
    assert sample["candidate_cgroup"] == CI_CGROUP
    assert sample["aggregate_cgroup"] == "/mastermind.slice/mastermind-ci.slice"
    assert sample["aggregate_metric_source"] == "parent_slice"
    assert set(sample["candidate_identity"]) == {"device", "inode"}
    assert set(sample["aggregate_identity"]) == {"device", "inode"}
    assert sample["limits"] == {
        "cpu.max": "800000 100000",
        "memory.high": "10737418240",
        "memory.max": "12884901888",
        "memory.swap.max": "2147483648",
    }


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("cpu.stat", "usage_usec 1000000\nnr_periods 400\n"),
        ("memory.events", "high 0\nmax 0\n"),
        ("pids.events", ""),
        ("memory.pressure", "some avg10=0.00 total=1\n"),
        ("io.pressure", "full avg10=0.00 total=1\n"),
    ],
)
def test_monitor_degrades_when_required_acceptance_keys_are_missing(
    tmp_path: Path, name: str, content: str
) -> None:
    root = tmp_path / "cgroup"
    _write_slice_tree(root, CI_CGROUP, **{name: content})
    sample = MONITOR.slice_sample(root, _proc_cgroup(tmp_path, CI_CGROUP))
    assert sample["status"] == "degraded"
    assert "required" in sample["reason"]


def test_reducer_refuses_bound_samples_missing_required_acceptance_keys() -> None:
    for field, malformed in (
        ("cpu", {"usage_usec": 1}),
        ("memory_events", {"high": 0}),
        ("pids_events", {}),
        ("pressure", {"memory": {"full": {"total": 1}}}),
    ):
        first_payload = _slice_sample()
        last_payload = _slice_sample()
        first_payload[field] = malformed
        last_payload[field] = malformed
        _assert_poisoned_window(
            CAPTURE.slice_metrics(
                [_host_sample(first_payload), _host_sample(last_payload)]
            )
        )


def test_cleanup_refuses_symlinked_allowlisted_root_without_deleting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    foreign = tmp_path / "foreign"
    (foreign / "_work").mkdir(parents=True)
    marker = foreign / "_work" / "must-stay"
    marker.write_text("untouched", encoding="utf-8")
    sealed = tmp_path / "runner-4"
    sealed.symlink_to(foreign, target_is_directory=True)
    monkeypatch.setattr(CLEANUP, "PC_CI_ROOTS", frozenset({sealed}))
    with pytest.raises(RuntimeError, match="sealed PC CI allowlist"):
        CLEANUP.scrub_pc_state(sealed, temporary_roots=())
    assert marker.read_text(encoding="utf-8") == "untouched"
