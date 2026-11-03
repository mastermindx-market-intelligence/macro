from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
MAIN_CONTROL_FILES = {
    "__init__.py",
    "run_ci_pack.py",
    "ci_semantic_proof.py",
    "ci_browser_dependency_inputs.py",
    "ci_browser_dependency_capture.py",
    "ci_apt_cold_acquisition.py",
    "ci_apt_native_plan.py",
    "ci_apt_native_stage.py",
    "ci_apt_transaction_contract.py",
    "ci_browser_native_setup.py",
    "ci_authority_paths.py",
    "ci_scope_dependencies.py",
    "audit_unrun_tests.py",
    "workflow_run_source.py",
    "resolve_ci_canary_ref.py",
    "select_ci_canary_packs.py",
    "monitor_ci_host_resources.py",
    "capture_ci_canary_receipt.py",
}
CONTROL_REPO_ROOT_ENV = "MASTERMIND_TRUSTED_CI_REPO_ROOT"
# The names a ci-pack step exports for its OWN plan. The same list, and its
# history, is tests/test_ci_pack.py::_isolate_pack_runner_planner_env.
PACK_PLANNER_ENV = frozenset(
    {
        "CI_CHANGED_FILES_FILE",
        "CI_CHANGED_FILES_JSON",
        "CI_SCOPE_MODE",
        "CI_DYNAMIC_MATRIX_MODE",
        "GITHUB_EVENT_NAME",
        "CI_SEMANTIC_ROLE",
        "CI_TESTED_TREE_SHA",
        "CI_SUBJECT_HEAD_SHA",
        "CI_BASE_SHA",
        "CI_ADMISSION_GENERATION",
    }
)
CONTROL_SPARSE_PATHS = {f"scripts/{filename}" for filename in MAIN_CONTROL_FILES}
CANDIDATE_SPARSE_PATTERNS = (
    "/*",
    "!/data/",
    "!/site/",
    "!/mockups/",
    "!/verify_shots/",
)


def workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def triggers(document: dict) -> set[str]:
    raw = document.get("on", document.get(True, {}))
    return set(raw) if isinstance(raw, dict) else {str(raw)}


def trusted_gate_step() -> dict:
    trust = workflow("trusted-ci-executor.yml")["jobs"]["trust-gate"]
    return next(
        step
        for step in trust["steps"]
        if step.get("name")
        == "admit direct dispatch or exact main-called same-repository PR"
    )


def run_trusted_gate(
    tmp_path: Path, **overrides: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    repository = "mastermindx-market-intelligence/macro"
    pr_number = "6390"
    output = tmp_path / "github-output"
    environment = {
        **os.environ,
        "GITHUB_OUTPUT": str(output),
        "EVENT_NAME": "pull_request",
        "TRUSTED_REF": f"refs/pull/{pr_number}/merge",
        "CALLER_WORKFLOW_REF": (
            f"{repository}/.github/workflows/ci.yml@refs/pull/{pr_number}/merge"
        ),
        "CALLED_WORKFLOW_REF": (
            f"{repository}/.github/workflows/"
            "trusted-ci-executor.yml@refs/heads/main"
        ),
        "CALLED_WORKFLOW_SHA": "a" * 40,
        "REPOSITORY": repository,
        "HEAD_REPOSITORY": repository,
        "BASE_REF": "main",
        "EVENT_PR_NUMBER": pr_number,
        "DISPATCH_PR_NUMBER": "",
        "REQUESTED_ROUTE": "hosted",
        "CALLER_WORKFLOW_SHA": "b" * 40,
        "CALLER_SHA": "b" * 40,
        "ADMITTED_MERGE": "",
        "ADMITTED_HEAD": "",
        "ADMITTED_BASE": "",
        "ADMITTED_PR": "",
        "ADMITTED_REPOSITORY_ID": "",
        "ADMISSION_GENERATION": "",
    }
    environment.update(overrides)
    result = subprocess.run(
        ["bash", "-c", trusted_gate_step()["run"]],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    values: dict[str, str] = {}
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            key, value = line.split("=", 1)
            values[key] = value
    return result, values


def test_p3bb_executor_stays_call_capable_after_production_route_activation() -> None:
    document = workflow("trusted-ci-executor.yml")
    assert triggers(document) == {"workflow_call", "workflow_dispatch"}
    trigger_config = document.get("on", document.get(True))
    assert set(trigger_config["workflow_call"]["inputs"]) == {'admission_generation', 'admitted_head', 'admitted_pr', 'admitted_repository_id', 'admitted_merge', 'admitted_base'}
    for value in trigger_config["workflow_call"]["inputs"].values():
        assert value["type"] == "string" and value["default"] == "" and value["required"] is False
    assert set(trigger_config["workflow_call"]["outputs"]) == {
        "matrix",
        "plan_sha",
        "tested_sha",
        "base_sha",
        "head_sha",
        "control_sha",
    }
    assert set(trigger_config["workflow_dispatch"]["inputs"]) == {"pr_number"}
    assert document["permissions"] == {"contents": "read", "pull-requests": "read"}

    trust = document["jobs"]["trust-gate"]
    assert trust["runs-on"] == "ubuntu-latest"
    assert trust["outputs"] == {
        "control_sha": "${{ steps.admit.outputs.control_sha }}",
        "pr_number": "${{ steps.admit.outputs.pr_number }}",
        "mode": "${{ steps.admit.outputs.mode }}",
        "semantic_workflow": "${{ steps.admit.outputs.semantic_workflow }}",
        "execution_route": "${{ steps.admit.outputs.execution_route }}",
    }
    gate = trusted_gate_step()
    assert gate["id"] == "admit"
    assert gate["env"] == {
        "EVENT_NAME": "${{ github.event_name }}",
        "TRUSTED_REF": "${{ github.ref }}",
        "CALLER_WORKFLOW_REF": "${{ github.workflow_ref }}",
        "CALLED_WORKFLOW_REF": "${{ job.workflow_ref }}",
        "CALLED_WORKFLOW_SHA": "${{ job.workflow_sha }}",
        "REPOSITORY": "${{ github.repository }}",
        "HEAD_REPOSITORY": "${{ github.event.pull_request.head.repo.full_name }}",
        "BASE_REF": "${{ github.base_ref }}",
        "EVENT_PR_NUMBER": "${{ github.event.pull_request.number }}",
        "DISPATCH_PR_NUMBER": "${{ inputs.pr_number }}",
        "REQUESTED_ROUTE": "${{ vars.CI_EXECUTION_ROUTE }}",
        "CALLER_WORKFLOW_SHA": "${{ github.workflow_sha }}",
        "CALLER_SHA": "${{ github.sha }}",
        "ADMITTED_MERGE": "${{ inputs.admitted_merge || '' }}",
        "ADMITTED_HEAD": "${{ inputs.admitted_head || '' }}",
        "ADMITTED_BASE": "${{ inputs.admitted_base || '' }}",
        "ADMITTED_PR": "${{ inputs.admitted_pr || '' }}",
        "ADMITTED_REPOSITORY_ID": "${{ inputs.admitted_repository_id || '' }}",
        "ADMISSION_GENERATION": "${{ inputs.admission_generation || '' }}",
    }

    production = workflow("ci.yml")
    assert production["jobs"]["trusted-ci"]["uses"] == (
        "mastermindx-market-intelligence/macro/.github/workflows/"
        "trusted-ci-executor.yml@main"
    )
    assert {
        production["jobs"][name]["runs-on"]
        for name in ("ci-plan", "ci-pack", "ci-gate")
    } == {"ubuntu-latest"}


def test_p3ba_accepts_exact_main_called_same_repo_pr_and_derives_identity(
    tmp_path: Path,
) -> None:
    result, outputs = run_trusted_gate(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert outputs == {
        "control_sha": "a" * 40,
        "pr_number": "6390",
        "mode": "production",
        "semantic_workflow": "ci",
        "execution_route": "hosted",
    }


def test_p3ba_keeps_the_direct_main_dispatch_canary(tmp_path: Path) -> None:
    repository = "mastermindx-market-intelligence/macro"
    result, outputs = run_trusted_gate(
        tmp_path,
        EVENT_NAME="workflow_dispatch",
        TRUSTED_REF="refs/heads/main",
        CALLER_WORKFLOW_REF=(
            f"{repository}/.github/workflows/"
            "trusted-ci-executor.yml@refs/heads/main"
        ),
        CALLED_WORKFLOW_REF=(
            f"{repository}/.github/workflows/"
            "trusted-ci-executor.yml@refs/heads/main"
        ),
        HEAD_REPOSITORY="",
        BASE_REF="",
        EVENT_PR_NUMBER="",
        DISPATCH_PR_NUMBER="6390",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert outputs == {
        "control_sha": "a" * 40,
        "pr_number": "6390",
        "mode": "dispatch",
        "semantic_workflow": "trusted-ci-executor",
        "execution_route": "pc",
    }


def test_p3ba_repository_route_pc_keeps_same_repo_calls_on_pc(tmp_path: Path) -> None:
    result, outputs = run_trusted_gate(tmp_path, REQUESTED_ROUTE="pc")
    assert result.returncode == 0, result.stdout + result.stderr
    assert outputs == {
        "control_sha": "a" * 40,
        "pr_number": "6390",
        "mode": "production",
        "semantic_workflow": "ci",
        "execution_route": "pc",
    }


def test_p3ba_unknown_or_empty_repository_route_fails_safe_to_hosted(
    tmp_path: Path,
) -> None:
    for route in ("", "hosted", "unexpected"):
        result, outputs = run_trusted_gate(tmp_path, REQUESTED_ROUTE=route)
        assert result.returncode == 0, result.stdout + result.stderr
        assert outputs["execution_route"] == "hosted"


@pytest.mark.parametrize(
    "overrides",
    [
        {"EVENT_NAME": "push"},
        {
            "CALLED_WORKFLOW_REF": (
                "mastermindx-market-intelligence/macro/.github/workflows/"
                "trusted-ci-executor.yml@main"
            )
        },
        {
            "CALLED_WORKFLOW_REF": (
                "mastermindx-market-intelligence/macro/.github/workflows/"
                "trusted-ci-executor.yml@refs/pull/6390/merge"
            )
        },
        {
            "CALLER_WORKFLOW_REF": (
                "mastermindx-market-intelligence/macro/.github/workflows/"
                "rogue.yml@refs/pull/6390/merge"
            )
        },
        {"HEAD_REPOSITORY": "attacker/fork"},
        {"BASE_REF": "release"},
        {"TRUSTED_REF": "refs/pull/6391/merge"},
        {"EVENT_PR_NUMBER": "6391"},
        {"DISPATCH_PR_NUMBER": "6390"},
        {"CALLED_WORKFLOW_SHA": "candidate"},
    ],
)
def test_p3ba_refuses_untrusted_call_contexts(
    tmp_path: Path, overrides: dict[str, str]
) -> None:
    result, outputs = run_trusted_gate(tmp_path, **overrides)
    assert result.returncode != 0
    assert outputs == {}


def test_p3ba_planner_uses_main_control_and_routes_one_or_all_exact_pr_packs() -> None:
    document = workflow("trusted-ci-executor.yml")
    plan = document["jobs"]["plan"]
    assert plan["runs-on"] == "ubuntu-latest"
    assert plan["needs"] == "trust-gate"
    assert {
        "matrix",
        "plan_sha",
        "tested_sha",
        "base_sha",
        "head_sha",
        "control_sha",
    } <= set(plan["outputs"])

    steps = plan["steps"]
    control_checkout = next(
        step for step in steps if step.get("name") == "checkout main-owned executor control code"
    )
    assert control_checkout["uses"] == "actions/checkout@v4"
    assert control_checkout["with"]["ref"] == (
        "${{ needs.trust-gate.outputs.control_sha }}"
    )
    assert control_checkout["with"]["persist-credentials"] is False

    resolve = next(step for step in steps if step.get("id") == "legacy-ref")
    assert "resolve_ci_canary_ref.py" in resolve["run"]
    assert '--github-sha "${{ needs.trust-gate.outputs.control_sha }}"' in resolve["run"]
    assert '--pr-number "${{ needs.trust-gate.outputs.pr_number }}"' in resolve["run"]
    candidate_checkout = next(
        step for step in steps if step.get("name") == "checkout the immutable PR candidate"
    )
    assert candidate_checkout["with"]["ref"] == "${{ steps.ref.outputs.tested_sha }}"
    assert candidate_checkout["with"]["persist-credentials"] is False

    planner = next(step for step in steps if step.get("id") == "plan")
    for token in (
        '--workflow-name "${{ needs.trust-gate.outputs.semantic_workflow }}"',
        '--event "${{ github.event_name }}"',
        "--role pr_head",
        "--gate code",
        "--tested-tree-sha",
        "--subject-head-sha",
        "--base-sha",
        "--changed-from",
    ):
        assert token in planner["run"]
    selector = next(step for step in steps if step.get("id") == "select")
    assert selector["env"] == {
        "EXECUTION_MODE": "${{ needs.trust-gate.outputs.mode }}",
        "FULL_MATRIX": "${{ steps.plan.outputs.matrix }}",
    }
    assert "--count 1" in selector["run"]
    assert "matrix=$FULL_MATRIX" in selector["run"]

    assert plan["outputs"]["execution_route"] == (
        "${{ needs.trust-gate.outputs.execution_route }}"
    )

    trusted_pack = document["jobs"]["trusted-pack"]
    assert trusted_pack["strategy"]["max-parallel"] == 3
    assert trusted_pack["if"] == "needs.plan.outputs.execution_route == 'pc'"
    assert trusted_pack["runs-on"] == {
        "group": "macro-home-canary",
        "labels": "ci-linux",
    }

    hosted_pack = document["jobs"]["legacy-hosted-pack"]
    assert hosted_pack["needs"] == "plan"
    assert hosted_pack["if"] == "needs.plan.outputs.execution_route == 'hosted'"
    assert hosted_pack["runs-on"] == "ubuntu-latest"
    assert "max-parallel" not in hosted_pack["strategy"]
    assert hosted_pack["strategy"]["matrix"] == (
        "${{ fromJSON(needs.plan.outputs.matrix) }}"
    )
    execute = next(
        step
        for step in hosted_pack["steps"]
        if step.get("name")
        == "execute the frozen logical pack and retain its semantic result"
    )
    assert (
        '"$RUNNER_TEMP/trusted-ci-control/scripts/run_ci_pack.py"'
        in execute["run"]
    )
    assert "--base-replay-budget-seconds 900" in execute["run"]
    assert "semantic_pack_rc=$pack_rc" in execute["run"]
    assert "exit $pack_rc" not in execute["run"]
    upload = next(
        step
        for step in hosted_pack["steps"]
        if step.get("name") == "publish the legacy caller semantic fragment"
    )
    assert upload["with"]["name"] == "trusted-ci-fragment-${{ matrix.pack }}"


def test_p4_hosted_planner_avoids_full_tree_materialization_without_narrowing_semantics() -> None:
    """Catch the production checkout jam without weakening exact-tree planning."""
    plan = workflow("trusted-ci-executor.yml")["jobs"]["plan"]
    steps = plan["steps"]

    control_checkout = next(
        step
        for step in steps
        if step.get("name") == "checkout main-owned executor control code"
    )
    control_patterns = {
        line.strip()
        for line in str(control_checkout["with"].get("sparse-checkout", "")).splitlines()
        if line.strip()
    }
    assert control_patterns == CONTROL_SPARSE_PATHS
    assert control_checkout["with"].get("sparse-checkout-cone-mode") is False

    candidate_checkout = next(
        step
        for step in steps
        if step.get("name") == "checkout the immutable PR candidate"
    )
    candidate_patterns = tuple(
        line.strip()
        for line in str(candidate_checkout["with"].get("sparse-checkout", "")).splitlines()
        if line.strip()
    )
    assert candidate_patterns == CANDIDATE_SPARSE_PATTERNS
    assert candidate_checkout["with"].get("sparse-checkout-cone-mode") is False

    inventory = next(
        (
            step
            for step in steps
            if step.get("name") == "bind exact tested-tree path inventory"
        ),
        None,
    )
    assert inventory is not None
    inventory_handle = "$RUNNER_TEMP/trusted-ci-tracked-paths/tracked-paths.v1"
    assert inventory["env"] == {
        CONTROL_REPO_ROOT_ENV: "${{ github.workspace }}",
    }
    assert (
        '"$RUNNER_TEMP/trusted-ci-control/scripts/ci_scope_dependencies.py"'
        in inventory["run"]
    )
    assert f'--write-tracked-paths "{inventory_handle}"' in inventory["run"]
    assert '--tested-tree-sha "${{ steps.ref.outputs.tested_sha }}"' in inventory["run"]

    planner = next(step for step in steps if step.get("id") == "plan")
    assert f'--tracked-paths-file "{inventory_handle}"' in planner["run"]
    assert steps.index(candidate_checkout) < steps.index(inventory) < steps.index(planner)


def test_p3ar_freezes_and_transports_the_complete_main_owned_control_bundle() -> None:
    document = workflow("trusted-ci-executor.yml")
    plan_steps = document["jobs"]["plan"]["steps"]
    preserve = next(
        step
        for step in plan_steps
        if step.get("name") == "freeze the complete main-owned control bundle"
    )
    for filename in MAIN_CONTROL_FILES:
        assert f"scripts/{filename}" in preserve["run"]
    assert "$RUNNER_TEMP/trusted-ci-control/scripts/" in preserve["run"]

    planner = next(step for step in plan_steps if step.get("id") == "plan")
    assert planner["env"][CONTROL_REPO_ROOT_ENV] == "${{ github.workspace }}"
    assert (
        '"$RUNNER_TEMP/trusted-ci-plan-runner/bin/python" -I '
        '"$RUNNER_TEMP/trusted-ci-control/scripts/run_ci_pack.py"'
    ) in planner["run"]
    assert 'bin/python" scripts/run_ci_pack.py' not in planner["run"]

    control_upload = next(
        step
        for step in plan_steps
        if step.get("uses") == "actions/upload-artifact@v4"
        and step["with"]["name"] == "trusted-ci-control"
    )
    assert control_upload["with"]["path"] == "${{ runner.temp }}/trusted-ci-control"
    assert control_upload["with"]["if-no-files-found"] == "error"

    pack_steps = document["jobs"]["trusted-pack"]["steps"]
    control_download_index = next(
        index
        for index, step in enumerate(pack_steps)
        if step.get("uses") == "actions/download-artifact@v4"
        and step["with"].get("name") == "trusted-ci-control"
    )
    materialize_index = next(
        index
        for index, step in enumerate(pack_steps)
        if step.get("name", "").startswith("materialize exact candidate")
    )
    assert control_download_index < materialize_index
    assert pack_steps[control_download_index]["with"]["path"] == (
        "${{ runner.temp }}/trusted-ci-control"
    )

    execute_step = next(
        step
        for step in pack_steps
        if step.get("name") == "execute the frozen logical pack and retain its actual result"
    )
    assert execute_step["env"][CONTROL_REPO_ROOT_ENV] == "${{ github.workspace }}"
    assert execute_step["env"]["CI_BASE_REF"] == "${{ github.base_ref || 'main' }}"
    assert execute_step["env"]["CI_HEAD_REF"] == "${{ needs.plan.outputs.head_ref }}"
    execute = execute_step["run"]
    assert (
        '"$RUNNER_TEMP/trusted-ci-pack-runner/bin/python" -I '
        '"$RUNNER_TEMP/trusted-ci-control/scripts/run_ci_pack.py"'
    ) in execute
    assert 'bin/python" scripts/run_ci_pack.py' not in execute

    receipt = next(
        step
        for step in pack_steps
        if step.get("name") == "write trusted self-hosted receipt"
    )["run"]
    assert "$RUNNER_TEMP/trusted-ci-control/scripts/capture_ci_canary_receipt.py" in receipt
    assert "$RUNNER_TEMP/trusted-ci-control/scripts/monitor_ci_host_resources.py" in execute


def admitted_gate_values():
    return dict(EVENT_NAME="workflow_dispatch", TRUSTED_REF="refs/heads/main",
        CALLER_WORKFLOW_REF="mastermindx-market-intelligence/macro/.github/workflows/ci.yml@refs/heads/main",
        DISPATCH_PR_NUMBER="", ADMITTED_MERGE="1" * 40, ADMITTED_HEAD="2" * 40,
        ADMITTED_BASE="3" * 40, ADMITTED_PR="123", ADMITTED_REPOSITORY_ID="456",
        ADMISSION_GENERATION="a" * 12, REQUESTED_ROUTE="pc")


def test_admitted_ci_main_caller_requires_typed_verified_handoff(tmp_path):
    result, outputs = run_trusted_gate(tmp_path, **admitted_gate_values())
    assert result.returncode == 0, result.stderr
    assert outputs == {"control_sha": "a" * 40, "pr_number": "", "mode": "admitted",
                       "semantic_workflow": "ci", "execution_route": "pc"}


@pytest.mark.parametrize("change", [
    {"ADMISSION_GENERATION": ""}, {"DISPATCH_PR_NUMBER": "123"},
    {"TRUSTED_REF": "refs/pull/123/merge"}, {"ADMITTED_MERGE": ""},
    {"ADMITTED_REPOSITORY_ID": "0"}, {"CALLER_WORKFLOW_SHA": "c" * 40},
    {"CALLER_WORKFLOW_REF": "mastermindx-market-intelligence/macro/.github/workflows/ci.yml@refs/heads/candidate"},
])
def test_admitted_context_cannot_use_other_caller_or_diagnostic_identity(tmp_path, change):
    args = admitted_gate_values()
    args.update(change)
    result, outputs = run_trusted_gate(tmp_path, **args)
    assert result.returncode != 0 and outputs == {}


def test_legacy_pr_cannot_smuggle_admission_inputs(tmp_path):
    result, outputs = run_trusted_gate(tmp_path, ADMISSION_GENERATION="a" * 12)
    assert result.returncode != 0 and outputs == {}


@pytest.mark.parametrize("mutation", [None, "fork", "head", "closed", "parents", "third-parent",
                                      "repository", "caller", "attempt", "generation", "unavailable"])
def test_admitted_subject_readback_is_bounded_and_never_uses_mutable_merge(tmp_path, monkeypatch, mutation):
    import io
    import urllib.request

    steps = workflow("trusted-ci-executor.yml")["jobs"]["plan"]["steps"]
    step = next(s for s in steps if s.get("id") == "admitted-ref")
    script = step["run"].split("<<'PYREAD'\n", 1)[1].rsplit("\nPYREAD", 1)[0]
    repository = "mastermindx-market-intelligence/macro"
    output = tmp_path / "output"
    environment = dict(admitted_gate_values(), GITHUB_RUN_ID="100", GITHUB_RUN_ATTEMPT="1",
        GITHUB_TOKEN="test-only", GITHUB_OUTPUT=str(output), REPOSITORY=repository,
        CALLER_REF=repository + "/.github/workflows/ci.yml@refs/heads/main",
        CALLER_WORKFLOW_SHA="b" * 40, CALLER_SHA="b" * 40)
    if mutation == "caller": environment["CALLER_REF"] = "candidate/.github/workflows/ci.yml@main"
    if mutation == "attempt": environment["GITHUB_RUN_ATTEMPT"] = "0"
    if mutation == "generation": environment["ADMISSION_GENERATION"] = "forged"
    for key, value in environment.items(): monkeypatch.setenv(key, value)
    repo = {"id": 456, "full_name": repository}
    pr = {"number": 123, "state": "open", "merge_commit_sha": "9" * 40,
          "head": {"sha": "2" * 40, "repo": dict(repo)},
          "base": {"sha": "8" * 40, "ref": "main", "repo": dict(repo)}}
    commit = {"sha": "1" * 40, "parents": [{"sha": "3" * 40}, {"sha": "2" * 40}]}
    if mutation == "fork": pr["head"]["repo"]["id"] = 999
    if mutation == "head": pr["head"]["sha"] = "7" * 40
    if mutation == "closed": pr["state"] = "closed"
    if mutation == "parents": commit["parents"].reverse()
    if mutation == "third-parent": commit["parents"].append({"sha": "4" * 40})
    if mutation == "repository": repo["id"] = True
    responses = {"": repo, "/pulls/123": pr, "/git/commits/" + "1" * 40: commit}
    requests = []

    class Reader:
        def open(self, request, timeout):
            assert 0 < timeout <= 20
            prefix = "https://api.github.com/repos/" + repository
            assert request.full_url.startswith(prefix)
            suffix = request.full_url[len(prefix):]
            requests.append(suffix)
            assert suffix in responses
            if mutation == "unavailable": raise OSError("unavailable")
            return io.BytesIO(json.dumps(responses[suffix]).encode())

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: Reader())
    if mutation is None:
        exec(compile(script, "protected-reader", "exec"), {})
        assert "base=" + "3" * 40 in output.read_text()
        assert "tested_commit=" + "1" * 40 in output.read_text()
        assert len(requests) == 3
    else:
        with pytest.raises(SystemExit): exec(compile(script, "protected-reader", "exec"), {})
        assert not output.exists()
        assert len(requests) <= 3
        if mutation == "unavailable": assert len(requests) == 1


def test_admitted_resolver_precedes_candidate_and_same_repo_gate_precedes_pc_eligibility():
    jobs = workflow("trusted-ci-executor.yml")["jobs"]
    steps = jobs["plan"]["steps"]
    resolve = next(s for s in steps if s.get("id") == "admitted-ref")
    normalize = next(s for s in steps if s.get("id") == "ref")
    candidate = next(s for s in steps if s.get("name") == "checkout the immutable PR candidate")
    assert steps.index(resolve) < steps.index(normalize) < steps.index(candidate)
    assert resolve["if"] == "needs.trust-gate.outputs.mode == 'admitted'"
    assert resolve["timeout-minutes"] == 3
    assert resolve["env"]["ADMITTED_MERGE"] == "${{ inputs.admitted_merge }}"
    assert resolve["env"]["CALLER_WORKFLOW_SHA"] == "${{ github.workflow_sha }}"
    assert "-I" in resolve["run"] and "/git/commits/" in resolve["run"]
    assert "actions/" not in resolve["run"]
    assert 'test "$ADMITTED_SAME_REPOSITORY" = true' in normalize["run"]
    assert jobs["trusted-pack"]["needs"] == "plan"
    assert jobs["trusted-pack"]["if"] == "needs.plan.outputs.execution_route == 'pc'"
    planner = next(s for s in steps if s.get("id") == "plan")
    assert "--admission-generation" in planner["run"]
    selector = next(s for s in steps if s.get("id") == "select")
    assert 'test "$EXECUTION_MODE" = admitted' in selector["run"]
    for name in ("legacy-hosted-pack", "trusted-pack"):
        execute = next(s for s in jobs[name]["steps"] if "run_ci_pack.py" in s.get("run", ""))
        assert "--expect-admission-generation" in execute["run"]
        assert 'if [ -n "$ADMISSION_GENERATION" ]' in execute["run"]


@pytest.mark.parametrize("same_repo,accepted", [("true", True), ("false", False), ("", False)])
def test_admitted_normalizer_refuses_fork_before_any_checkout(tmp_path, same_repo, accepted):
    steps = workflow("trusted-ci-executor.yml")["jobs"]["plan"]["steps"]
    step = next(s for s in steps if s.get("id") == "ref")
    output = tmp_path / "output"
    env = dict(os.environ, GITHUB_OUTPUT=str(output), MODE="admitted",
        ADMITTED_SAME_REPOSITORY=same_repo, ADMISSION_GENERATION="a" * 12,
        ADMITTED_TESTED="1" * 40, ADMITTED_BASE="2" * 40, ADMITTED_HEAD="3" * 40)
    result = subprocess.run(["bash", "-c", step["run"]], env=env, capture_output=True, text=True)
    assert (result.returncode == 0) is accepted
    if accepted:
        assert "head_ref=" + "3" * 40 in output.read_text()
    else:
        assert not output.exists()


@pytest.mark.parametrize("mutation", [None, "bytes", "extra-file", "extra-directory", "symlink", "rename"])
def test_control_transport_digest_refuses_changed_paths_or_bytes_before_execution(tmp_path, mutation):
    jobs = workflow("trusted-ci-executor.yml")["jobs"]
    steps = jobs["plan"]["steps"]
    seal = next(s for s in steps if s.get("id") == "bundle")
    candidate = next(s for s in steps if s.get("name") == "checkout the immutable PR candidate")
    assert steps.index(seal) < steps.index(candidate)
    control = tmp_path / "trusted-ci-control" / "scripts"
    control.mkdir(parents=True)
    original = control / "proof.py"
    original.write_text("raise RuntimeError('this code must never execute')\n")
    output = tmp_path / "output"
    env = dict(os.environ, RUNNER_TEMP=str(tmp_path), GITHUB_OUTPUT=str(output))
    env.pop("EXPECTED_CONTROL_DIGEST", None)
    result = subprocess.run(["bash", "-c", seal["run"]], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    env["EXPECTED_CONTROL_DIGEST"] = output.read_text().strip().split("=", 1)[1]
    if mutation == "bytes": original.write_text("changed\n")
    elif mutation == "extra-file": (control / "extra.py").write_text("extra\n")
    elif mutation == "extra-directory": (control / "extra").mkdir()
    elif mutation == "symlink": (control / "escape").symlink_to(tmp_path)
    elif mutation == "rename": original.rename(control / "other.py")
    for name in ("legacy-hosted-pack", "trusted-pack"):
        pack_steps = jobs[name]["steps"]
        verify = next(s for s in pack_steps if s.get("name") == "verify control bundle before any candidate execution")
        first_code = next(s for s in pack_steps if "scripts/run_ci_pack.py" in s.get("run", ""))
        assert pack_steps.index(verify) < pack_steps.index(first_code)
        result = subprocess.run(["bash", "-c", verify["run"]], env=env, capture_output=True, text=True)
        assert (result.returncode == 0) is (mutation is None), result.stderr


LEGACY_JOBS_MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"


def _declared_code_gate_job_count() -> int:
    """Count the manifest's ``gate: code`` jobs by reading the YAML directly.

    The bundle test below asserts that the frozen control bundle validated
    EVERY merge-gate job, not a subset — so it needs the expected count. That
    count used to be a literal (132, pinned 2026-08-26 on #6351) and rotted
    to a red every time a code-gated job was added to the manifest; nine
    landed between the pin and 2026-09-15 (last: #7164) with nothing on a PR
    to say so, because this suite's only home was then the ``gate: data`` job
    ``workflow-yaml`` (it runs in ``ci-control-plane-contracts``, on the code
    gate, since 2026-09-25). The count is derived here from the manifest so the
    assertion tracks the tree, and it is derived WITHOUT importing
    ``scripts.run_ci_pack`` on purpose: reusing the module under test's own
    ``load_legacy_jobs(gate="code")`` would make the check tautological. The
    default mirrors ``run_ci_pack.py``'s documented rule — an absent ``gate``
    is code, so nothing can leave the merge gate silently.
    """
    document = yaml.safe_load(LEGACY_JOBS_MANIFEST.read_text(encoding="utf-8"))
    jobs = document["jobs"]
    assert isinstance(jobs, dict) and jobs, "legacy manifest carries no jobs"
    return sum(1 for job in jobs.values() if (job or {}).get("gate", "code") == "code")


def test_p3ar_control_bundle_imports_without_candidate_control_modules(
    tmp_path: Path,
) -> None:
    control_scripts = tmp_path / "trusted-ci-control" / "scripts"
    control_scripts.mkdir(parents=True)
    for filename in MAIN_CONTROL_FILES:
        (control_scripts / filename).write_bytes((ROOT / "scripts" / filename).read_bytes())

    # The child below plans. Inside a PR ci-pack step the ambient environment
    # carries that pack's own plan: CI_CHANGED_FILES_FILE plus
    # GITHUB_EVENT_NAME=pull_request make run_ci_pack.py plan as a PR head, and
    # with no --changed-from it refuses ("PR semantic plan changed_from must
    # equal exact base_sha"). That red was PR #8033 ci-pack-0, job 108193042443,
    # the first time this suite ran on the PR code gate. What the bundle
    # imports does not depend on which lane runs the test, so the child plans
    # with the pack's plan identity removed.
    environment = {
        key: value for key, value in os.environ.items() if key not in PACK_PLANNER_ENV
    }
    environment["PYTHONPATH"] = str(control_scripts.parent)
    environment[CONTROL_REPO_ROOT_ENV] = str(ROOT)
    root_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {str(control_scripts.parent)!r}); "
                "from scripts.ci_scope_dependencies import ROOT; print(ROOT)"
            ),
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert root_probe.returncode == 0, root_probe.stdout + root_probe.stderr
    assert root_probe.stdout.strip() == str(ROOT.resolve())

    result = subprocess.run(
        [
            sys.executable,
            str(control_scripts / "run_ci_pack.py"),
            "--workflow",
            ".github/ci/legacy-jobs.yml",
            "--gate",
            "code",
            "--validate-only",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    expected = _declared_code_gate_job_count()
    assert expected > 0
    assert f"Validated {expected} legacy jobs" in result.stdout, (
        f"the frozen control bundle did not validate every gate: code job "
        f"(expected {expected}); stdout was:\n{result.stdout}"
    )


def test_p3a_selfhosted_job_uses_the_selected_group_and_negotiated_cache() -> None:
    document = workflow("trusted-ci-executor.yml")
    job = document["jobs"]["trusted-pack"]
    assert job["needs"] == "plan"
    assert job["runs-on"] == {
        "group": "macro-home-canary",
        "labels": "ci-linux",
    }
    steps = job["steps"]
    assert all(step.get("uses") != "actions/checkout@v4" for step in steps)

    prewarm_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name", "").startswith("prewarm exact base")
    )
    materialize_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name", "").startswith("materialize exact candidate")
    )
    assert prewarm_index < materialize_index
    assert "/usr/local/libexec/mastermind-ci-prewarm" in str(steps[prewarm_index])
    materialize = steps[materialize_index]["run"]
    for token in (
        "fetch.negotiationAlgorithm=skipping",
        "--filter=blob:none --depth=1",
        'origin "$TESTED_SHA"',
        "GIT_TERMINAL_PROMPT=0",
        "GIT_ASKPASS=/bin/false",
        "credential.helper=",
        "extraheader",
        "GIT_NO_LAZY_FETCH=1",
    ):
        assert token in materialize
    assert materialize.index("extraheader") < materialize.index("git -c credential.helper=")


def test_p3a_executor_consumes_one_frozen_plan_and_emits_existing_evidence() -> None:
    document = workflow("trusted-ci-executor.yml")
    steps = document["jobs"]["trusted-pack"]["steps"]
    execute = next(
        step
        for step in steps
        if step.get("name") == "execute the frozen logical pack and retain its actual result"
    )["run"]
    for token in (
        "--plan-json",
        "--changed-files-file",
        "--expect-plan-sha",
        "--expect-tested-tree-sha",
        "--expect-subject-head-sha",
        "--expect-base-sha",
        "--emit-semantic-fragment",
        "--gate code",
    ):
        assert token in execute
    assert "--changed-from" not in execute

    rendered = str(steps)
    assert "capture_ci_canary_receipt.py" in rendered
    assert "ci.semantic_fragment.v1" not in rendered  # emitted by the existing helper
    upload_names = {
        step["with"]["name"]
        for step in steps
        if step.get("uses") == "actions/upload-artifact@v4"
    }
    assert "trusted-ci-receipt-${{ matrix.pack }}" in upload_names
    assert "trusted-ci-fragment-${{ matrix.pack }}" in upload_names


def test_p3a_executor_has_no_secret_or_candidate_credential_surface() -> None:
    document = workflow("trusted-ci-executor.yml")
    rendered = str(document)
    for forbidden in (
        "secrets:",
        "pull_request_target",
        "persist-credentials: true",
        "ADMIN_GH_TOKEN",
        "MERGE_TOKEN",
        "macstudio",
        "render-linux",
        "m1-",
    ):
        assert forbidden not in rendered
    for job in document["jobs"].values():
        for step in job.get("steps", []) or []:
            if step.get("uses") == "actions/checkout@v4":
                assert step["with"]["persist-credentials"] is False
