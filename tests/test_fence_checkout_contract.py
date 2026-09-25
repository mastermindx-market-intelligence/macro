from __future__ import annotations

import importlib.util
import inspect
import tempfile
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "fences.yml"
CANARY_CONTRACT_PATH = ROOT / "tests" / "test_ci_canary_workflows.py"
HOLD_SUITE_PATH = ROOT / "tests" / "test_ship_loop_hold_wrapper.py"
LIVE_CHECK_STEP = "self-mod-fence live check (loop PR + immutable → BLOCKED)"
#: Hold-suite tests the fast fence deliberately does NOT call, each mapped to its written
#: reason. Empty: every test function in the suite runs inside fence-pack.
HOLD_SUITE_NOT_CALLED: dict[str, str] = {}


def _document() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _named_step(job: dict, name: str) -> dict:
    matches = [step for step in job["steps"] if step.get("name") == name]
    assert len(matches) == 1, (name, [step.get("name") for step in job["steps"]])
    return matches[0]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_canary_contract_module():
    return _load_module(CANARY_CONTRACT_PATH, "fence_owned_ci_canary_contract")


def _load_hold_suite_module():
    return _load_module(HOLD_SUITE_PATH, "fence_owned_ship_loop_hold_contract")


def _suite_tests(module) -> dict:
    """The functions pytest would collect from ``module`` (default ``test`` prefix)."""
    return {
        name: value
        for name, value in vars(module).items()
        if name.startswith("test") and inspect.isfunction(value)
    }


def _collected_cases(module) -> list[tuple[str, dict]]:
    """One ``(name, params)`` per case pytest collects: each parametrized value set."""
    cases = []
    for name, function in _suite_tests(module).items():
        grid = [{}]
        for mark in getattr(function, "pytestmark", ()):
            if mark.name != "parametrize":
                continue
            spec = {**dict(zip(("argnames", "argvalues"), mark.args)), **mark.kwargs}
            argnames = spec["argnames"]
            names = (
                [part.strip() for part in argnames.split(",")]
                if isinstance(argnames, str)
                else list(argnames)
            )
            rows = [
                dict(zip(names, values if len(names) > 1 else (values,)))
                for values in spec["argvalues"]
            ]
            grid = [{**params, **row} for params in grid for row in rows]
        cases.extend((name, params) for params in grid)
    return cases


def _recording(name: str, function, calls: list):
    """Stand in for a suite test: bind the arguments as the real call would, run nothing."""
    signature = inspect.signature(function)

    def record(*args, **kwargs):
        calls.append((name, dict(signature.bind(*args, **kwargs).arguments)))

    return record


def test_same_repo_fence_checkout_is_bounded_sparse_and_blob_filtered() -> None:
    job = _document()["jobs"]["fence-pack"]
    checkout = next(step for step in job["steps"] if step.get("uses") == "actions/checkout@v4")
    options = checkout["with"]

    assert options["filter"] == "blob:none"
    assert options["fetch-depth"] == 256
    assert options["sparse-checkout-cone-mode"] is False

    sparse = {line.strip() for line in str(options["sparse-checkout"]).splitlines() if line.strip()}
    required = {
        "/.github/",
        "/config/",
        "/engine/metabolism/",
        "/engine/neuralweb/",
        "/engine/foresight_leadlag.py",
        "/engine/theme_placebo.py",
        "/engine/qledger_falsifier.py",
        "/lib/",
        "/scripts/",
        "/templates/",
        "/tests/",
        "/site/chat.html",
        "/data/neuralweb/capability_audit.jsonl",
        "/data/metabolism/key_ledger.jsonl",
        "/data/metabolism/journal/",
        "/data/ai_costs/usage.jsonl",
        "/config.yml",
    }
    assert required <= sparse
    assert "/site/" not in sparse
    assert "/data/" not in sparse


def test_self_mod_live_check_uses_exact_synthetic_parents_and_fails_closed() -> None:
    job = _document()["jobs"]["fence-pack"]
    live = _named_step(job, LIVE_CHECK_STEP)
    command = live["run"]

    assert 'git rev-list --parents -n 1 "$GITHUB_SHA"' in command
    assert "expected one synthetic merge with exactly two parents" in command

    merge_base = 'MERGE_BASE=$(git merge-base "$TESTED_BASE_SHA" "$SUBJECT_HEAD_SHA")'
    assert command.count(merge_base) == 2
    first_probe = command.index(merge_base)
    fetch = command.index("git fetch")
    second_probe = command.rindex(merge_base)
    assert first_probe < fetch < second_probe
    assert command.count("git fetch") == 1

    for required in (
        "--no-tags",
        "--no-recurse-submodules",
        "--filter=blob:none",
        "--deepen=4096",
        '"+$TESTED_BASE_SHA:refs/ci-fence/base"',
        '"+$SUBJECT_HEAD_SHA:refs/ci-fence/head"',
        "initial bounded checkout did not reach the exact PR merge base",
        "exact-parent ancestry deepening failed",
        "could not establish exact PR ancestry after bounded exact-parent deepening",
    ):
        assert required in command

    for forbidden in (
        "origin/${{ github.base_ref",
        "origin/main",
        "refs/pull/",
        "--unshallow",
        "--depth=0",
    ):
        assert forbidden not in command

    assert (
        'git log --format="%B" "$MERGE_BASE..$SUBJECT_HEAD_SHA" '
        '> "$TRAILERS_FILE"' in command
    )
    assert (
        'git diff --name-only -z "$MERGE_BASE" "$SUBJECT_HEAD_SHA"' in command
    )


def test_both_live_fences_use_only_bounded_file_handles() -> None:
    """Pin the absence that closes #5898's pre-Python E2BIG failure.

    The same-repository fast path and fork fallback used to reconstruct both
    unbounded populations in shell variables and expand them into argv. A parser
    unit test cannot catch that wiring regression, so assert the executable
    workflow source itself never restores either retired shape.
    """
    document = _document()
    commands = {
        job_id: str(_named_step(document["jobs"][job_id], LIVE_CHECK_STEP)["run"])
        for job_id in ("fence-pack", "fork-self-mod-fence")
    }
    for job_id, command in commands.items():
        assert 'SELF_MOD_INPUT_DIR="$RUNNER_TEMP/self-mod-fence"' in command
        assert '--write-files-file-from-nul "$FILES_FILE"' in command
        assert '--files-file "$FILES_FILE"' in command
        assert '--trailers-file "$TRAILERS_FILE"' in command
        assert "git diff --name-only -z" in command
        assert '> "$TRAILERS_FILE"' in command
        assert "FILES=$(" not in command, job_id
        assert "TRAILERS=$(" not in command, job_id
        assert "--files $FILES" not in command, job_id
        assert '--files "$FILES"' not in command, job_id
        assert "--trailers $TRAILERS" not in command, job_id
        assert '--trailers "$TRAILERS"' not in command, job_id
        assert "GITHUB_ENV" not in command, job_id

    fork = commands["fork-self-mod-fence"]
    assert (
        "git diff --name-only -z "
        "origin/${{ github.base_ref || 'main' }}...HEAD" in fork
    )
    assert (
        'git log --format="%B" '
        "origin/${{ github.base_ref || 'main' }}..HEAD" in fork
    )


def test_self_mod_fence_suite_pins_checkout_contract() -> None:
    job = _document()["jobs"]["fence-pack"]
    suite = _named_step(job, "self-mod-fence test suite")["run"]
    assert "tests/test_self_mod_fence.py" in suite
    assert "tests/test_fence_checkout_contract.py" in suite


def test_hosted_merge_control_canary_contract_executes_in_fast_fence() -> None:
    """Reuse the canonical W1-A assertions inside the always-on PR fence.

    ``workflow-yaml`` also names ``test_ci_canary_workflows.py``, but that logical
    job is ``gate: data`` and therefore is not a PR merge precondition. Loading the
    canonical module here makes the hosted-canary safety contract execute in the
    already-required ``fence-pack`` without copying the assertions or adding a
    parallel CI workflow.
    """
    contract = _load_canary_contract_module()
    contract.test_canaries_are_dispatch_only_and_not_merge_authority()
    contract.test_merge_control_hosted_canary_is_read_only_main_pinned_and_non_acting()


def test_every_hold_suite_regression_is_called_inside_the_fast_fence(monkeypatch) -> None:
    """The completeness half: the hold contract's call list cannot go stale silently.

    That list is the suite's only route into CI, and nothing checked it. By PR #8000 it
    had fallen 14 tests behind the suite, so the #6608 WAITING regression, every PARKED
    message test and every source-law parity test ran in no CI job at all. This runs
    the contract once with each suite test swapped for a recorder, then requires every
    case pytest would collect, each parametrized value included, to have been called
    with arguments its signature accepts, unless ``HOLD_SUITE_NOT_CALLED`` names the
    test with a reason. The real calls, and the real assertions, run in the contract.
    """
    hold = _load_hold_suite_module()
    expected = _collected_cases(hold)
    calls: list[tuple[str, dict]] = []
    for name, function in _suite_tests(hold).items():
        setattr(hold, name, _recording(name, function, calls))
    monkeypatch.setitem(globals(), "_load_hold_suite_module", lambda: hold)

    test_hold_wrapper_regressions_execute_inside_the_fast_fence()

    def was_called(name: str, params: dict) -> bool:
        return any(
            called == name and all(key in bound and bound[key] == params[key] for key in params)
            for called, bound in calls
        )

    uncalled = [
        name + (f"[{params}]" if params else "")
        for name, params in expected
        if name not in HOLD_SUITE_NOT_CALLED and not was_called(name, params)
    ]
    assert not uncalled, (
        "hold-suite tests dark in CI: call them in "
        "test_hold_wrapper_regressions_execute_inside_the_fast_fence, or name them in "
        f"HOLD_SUITE_NOT_CALLED with the reason: {uncalled}"
    )
    suite = {name for name, _ in expected}
    assert set(HOLD_SUITE_NOT_CALLED) <= suite, "an exemption names a test the suite lacks"
    assert all(reason.strip() for reason in HOLD_SUITE_NOT_CALLED.values())
    assert not set(HOLD_SUITE_NOT_CALLED) & {name for name, _ in calls}, (
        "an exempted test is called after all: drop its HOLD_SUITE_NOT_CALLED entry"
    )


def test_hold_wrapper_regressions_execute_inside_the_fast_fence() -> None:
    """Execute the canonical HOLD state regressions in required fences.

    ``audit_unrun_tests.py`` understands direct legacy-manifest ownership only, so
    the separate waiver records this intentional transitive fast-fence ownership.
    This is the executable half: every canonical regression is invoked here rather
    than copied into a second assertion set.

    fence-pack calls these functions without pytest, from a sparse checkout with no
    ``.claude/``, ``CLAUDE.md``, ``AGENTS.md`` or ``.cursor/``. Fixtures are supplied as
    a ``pytest.MonkeyPatch.context()`` and a temporary directory, never ``capsys``, and
    parametrized cases iterate the suite's own constants rather than copies. Every test
    function in the suite is called here; one that genuinely cannot run here belongs in
    ``HOLD_SUITE_NOT_CALLED`` with its reason, never simply off this list.
    ``test_every_hold_suite_regression_is_called_inside_the_fast_fence`` enforces both.
    """
    hold = _load_hold_suite_module()
    hold.test_exact_sol_hold_protocol_is_recognized()
    for mutation in hold.UNSAFE_HOLD_MUTATIONS:
        hold.test_incomplete_or_unsafe_hold_fails_closed(mutation)
    hold.test_markdown_protocol_fields_are_not_required_to_be_plain_text()
    hold.test_hold_block_still_refuses_branches_outside_the_two_sanctioned_namespaces()
    hold.test_parked_message_separates_ship_terminal_from_dialogue_terminal()
    hold.test_parked_message_requires_truthful_continuation_receipt_before_yield()
    hold.test_parked_message_claims_no_slack_state_and_creates_no_successor()
    hold.test_parked_message_still_forbids_every_release_action()
    with pytest.MonkeyPatch.context() as monkeypatch:
        hold.test_parked_message_is_pure_and_needs_no_probe_or_network(monkeypatch)
    # CLAUDE.md, AGENTS.md and .cursor/ are outside fence-pack's sparse checkout; the
    # suite reads a law file from exact HEAD whenever it is absent on disk.
    for relative in hold.PARITY_FILES:
        hold.test_source_law_agrees_ship_attempt_is_not_the_reciprocal_dialogue(relative)
        hold.test_source_law_never_calls_parked_session_terminal(relative)
    hold.test_source_law_keeps_hold_a_hard_merge_barrier()
    hold.test_cursor_rule_no_longer_orders_the_session_closed_at_parked()

    with tempfile.TemporaryDirectory() as raw:
        tmp_path = Path(raw)
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_lawful_concluded_green_hold_becomes_parked(monkeypatch, tmp_path)
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_lawful_sol_authority_branch_parks_after_unsafe_branch(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_lawful_sol_authority_branch_parks_before_first_unsafe_branch(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_unsafe_branch_hold_exception_is_sol_namespace_only(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_red_or_pending_claude_hold_does_not_park(monkeypatch, tmp_path)
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_pending_sol_hold_waits_before_first_unsafe_branch_remediation(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_red_sol_hold_repairs_check_without_branch_remediation(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_pending_ordinary_claude_hold_waits_instead_of_demanding_a_forbidden_merge(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_red_ordinary_claude_hold_repairs_the_check_and_never_merges(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_green_ordinary_hold_still_parks_and_pending_still_never_parks(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_main_parked_branch_emits_exactly_the_composed_message(
                monkeypatch, tmp_path
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_dirty_or_not_exactly_pushed_hold_does_not_park(monkeypatch, tmp_path)
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_hold_probe_spends_no_github_quota_outside_candidate_branches(
                monkeypatch, tmp_path
            )
        for branch in hold.ANCHOR_REPLAY_BRANCHES:
            with pytest.MonkeyPatch.context() as monkeypatch:
                hold.test_hold_whose_ci_yml_run_has_not_published_waits_instead_of_parking(
                    monkeypatch, tmp_path, branch
                )
        with pytest.MonkeyPatch.context() as monkeypatch:
            hold.test_same_hold_parks_once_ci_gate_and_every_pack_concluded_success(
                monkeypatch, tmp_path
            )
        for verdict in hold.UNPROVEN_ANCHOR_VERDICTS:
            with pytest.MonkeyPatch.context() as monkeypatch:
                hold.test_no_red_rollup_without_a_clean_anchor_verdict_never_parks(
                    monkeypatch, tmp_path, verdict
                )

    hold.test_stop_hook_routes_through_wrapper_but_keeps_original_guard_as_delegate()
    hold.test_ci_yml_still_proves_draft_heads_so_a_hold_can_reach_parked()


def test_agent_os_record_contract_runs_inside_the_existing_fast_fence() -> None:
    job = _document()["jobs"]["fence-pack"]
    checkout = next(step for step in job["steps"] if step.get("uses") == "actions/checkout@v4")
    sparse = {
        line.strip()
        for line in str(checkout["with"]["sparse-checkout"]).splitlines()
        if line.strip()
    }
    assert "/agentos/" in sparse

    step = _named_step(job, "agent-os record contract")
    assert step["id"] == "agent_os_record_contract"
    assert step["continue-on-error"] is True
    assert step["run"] == "python3 scripts/agentos.py validate"


def test_agent_os_record_contract_feeds_the_existing_self_mod_context() -> None:
    job = _document()["jobs"]["fence-pack"]
    publish = _named_step(job, "publish required fence contexts")
    assert publish["env"]["AGENT_OS_RECORD_CONTRACT"] == (
        "${{ steps.agent_os_record_contract.outcome }}"
    )

    script = publish["with"]["script"]
    self_mod_start = script.index("name: 'self-mod-fence'")
    capability_start = script.index("name: 'capability-broker'")
    self_mod_block = script[self_mod_start:capability_start]
    assert "process.env.AGENT_OS_RECORD_CONTRACT" in self_mod_block
    assert script.count("process.env.AGENT_OS_RECORD_CONTRACT") == 1
    assert "name: 'agent-os-record-contract'" not in script


def test_agent_os_record_contract_failure_reaches_fence_pack_terminal_result() -> None:
    job = _document()["jobs"]["fence-pack"]
    aggregate = _named_step(job, "fail pack when any fence failed")
    assert aggregate["env"]["AGENT_OS_RECORD_CONTRACT"] == (
        "${{ steps.agent_os_record_contract.outcome }}"
    )
    assert '"$AGENT_OS_RECORD_CONTRACT"' in aggregate["run"]


def test_fork_self_mod_fence_runs_the_same_canonical_agent_os_validator() -> None:
    job = _document()["jobs"]["fork-self-mod-fence"]
    commands = [step.get("run") for step in job["steps"]]
    assert commands.count("python3 scripts/agentos.py validate") == 1
