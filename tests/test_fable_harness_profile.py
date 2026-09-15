"""Focused source-to-hook tests; these do not launch Claude or call providers."""
import importlib.util
import contextlib
import io
import runpy
from unittest import mock
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "scripts/fable_harness_profile.py"
spec = importlib.util.spec_from_file_location("fable_harness_profile", PROFILE_PATH)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
ENV_KEY = "MASTERMIND_NATIVE_DELEGATION_MODE"


@pytest.fixture
def project(tmp_path):
    dest = tmp_path / "project"
    for name in (profile.GUARD, profile.CONTEXT, profile.SETTINGS,
                 profile.REGISTRY, profile.SCOUT):
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return dest


def census_payload(tool="Agent"):
    return {
        "tool_name": tool,
        "tool_input": {
            "subagent_type": "scout", "model": "sonnet",
            "prompt": (
                "ROUTE: census\n"
                "MISSION: Trace the exact named source path and its current consumer.\n"
                "WHY: Recover implementation facts before the parent makes a decision.\n"
                "SCOPE: Only the named subsystem and directly connected interfaces.\n"
                "OUT OF SCOPE: No writes, architecture or adjacent recommendations.\n"
                "QUESTIONS: Identify the producer, consumer and disconnected paths.\n"
                "NOT DONE UNLESS: Each material claim has exact file and line evidence.\n"
                "EVIDENCE REQUIRED: Source locators and explicit unresolved gaps.\n"
                "RETURN: STATUS / RESULT / EVIDENCE / GAPS / DEVIATIONS\n"
            ),
        },
    }


def fable_payload(tool="Agent"):
    payload = census_payload(tool)
    payload["tool_input"].update(subagent_type="orchestrator", model="fable")
    payload["tool_input"]["prompt"] = payload["tool_input"]["prompt"].replace(
        "ROUTE: census", "ROUTE: orchestration\nFABLE-WHY: orchestration: "
        "This task requires exceptional architectural judgment across frozen interfaces.")
    return payload


def call_hook(project, mode, payload=None, raw=None, context=False, env_overrides=None):
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)
    if mode is None:
        env.pop(ENV_KEY, None)
    else:
        env[ENV_KEY] = mode
    if mode == "native_leaf":
        env.update({"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
                    "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "0"})
    for key, value in (env_overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    # Exercise the actual script entrypoint in-process for the policy matrix.
    # Separate tests below retain subprocess checks of the generated profile.
    output = io.StringIO()
    input_text = raw if raw is not None else json.dumps(payload or {})
    with mock.patch.dict(os.environ, env, clear=True), \
            mock.patch.object(sys, "stdin", io.StringIO(input_text)), \
            contextlib.redirect_stdout(output):
        try:
            runpy.run_path(str(project / (profile.CONTEXT if context else profile.GUARD)),
                           run_name="__main__")
        except SystemExit as exc:
            assert exc.code in (0, None)
    return output.getvalue()



def refusal(output):
    data = json.loads(output)
    decision = data["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert "updatedInput" not in decision
    return decision["permissionDecisionReason"]


@pytest.mark.parametrize("mode", profile.MODES)
def test_profile_producer_to_real_hook_consumer(project, mode):
    bundle = profile.compile_profile(project, mode, "2.1.219 (Claude Code)")
    args = bundle["cli_arguments"]
    settings = json.loads(args[args.index("--settings") + 1])
    assert settings == bundle["settings_fragment"]
    assert bundle["launch_authorized"] is False
    assert bundle["observed_claude_version"] is None
    assert bundle["limits"]["account_quota"] == "UNKNOWN"
    assert set(settings["hooks"]) == {"PreToolUse", "SessionStart"}
    guard = settings["hooks"]["PreToolUse"][0]["hooks"][0]
    assert guard == {"type": "command", "command": profile.GUARD_COMMAND + " || exit 2", "timeout": 10}
    assert "ship_loop_guard.py" not in json.dumps(settings["hooks"])
    assert set(bundle["required_workspace_sources"]) == {profile.GUARD, profile.CONTEXT, profile.REGISTRY} | ({profile.SCOUT} if mode == "native_leaf" else set())
    mode_from_real_fragment = settings["env"][ENV_KEY]
    assert refusal(call_hook(project, mode_from_real_fragment, fable_payload()))
    allowed = call_hook(project, mode_from_real_fragment, census_payload())
    if mode == "router_only":
        assert "ROUTER_REQUIRED" in refusal(allowed)
        assert "Agent" in settings["permissions"]["deny"]
        assert "Task" in settings["permissions"]["deny"]
        assert bundle["agent_overrides"] == {}
    else:
        assert allowed == ""  # No permission grant or input rewrite.
        agents = json.loads(args[args.index("--agents") + 1])
        assert agents["scout"]["tools"] == ["Read", "Grep", "Glob"]
        assert agents["scout"]["model"] == "sonnet"
        assert agents["scout"]["maxTurns"] == 14
        assert agents["scout"]["effort"] == "medium"
        assert "Bash" not in agents["scout"]["tools"]
        assert set(agents) == {"scout"}
    assert bundle["limits"]["concurrency_hint_enforced_in_ultracode"] is False
    assert "Workflow" in settings["permissions"]["deny"]
    assert "TeamCreate" in settings["permissions"]["deny"]
    assert "SendMessage" in settings["permissions"]["deny"]
    assert "Skill" in settings["permissions"]["deny"]
    assert settings["env"]["CLAUDE_CODE_FORK_SUBAGENT"] == "0"


@pytest.mark.parametrize("mode", profile.MODES)
@pytest.mark.parametrize("tool", ["Agent", "Task"])
def test_ten_fable_requests_all_refused_without_provider_calls(project, mode, tool):
    decisions = [refusal(call_hook(project, mode, fable_payload(tool))) for _ in range(10)]
    assert len(decisions) == 10
    assert all(decisions)


@pytest.mark.parametrize("mode", profile.MODES)
@pytest.mark.parametrize("script_input", [
    {}, {"scriptPath": "/unreadable/workflow.js"},
    {"script": "// FABLE-WHY: orchestration: A supposedly important census task.\n"
               "await Promise.all(Array.from({length:10},()=>agent('census',{model:'fable'})));"},
    {"script": "const model='sonnet'; await agent('unrouted census');"},
])
def test_workflow_never_uses_regex_as_admission(project, mode, script_input):
    assert "ROUTER_REQUIRED" in refusal(call_hook(
        project, mode, {"tool_name": "Workflow", "tool_input": script_input}))


@pytest.mark.parametrize("agent_id", ["nested-1", "", None, 0])
def test_native_leaf_cannot_delegate(project, agent_id):
    payload = census_payload()
    payload["agent_id"] = agent_id
    assert "NATIVE_LEAF_ONLY" in refusal(call_hook(project, "native_leaf", payload))


def test_main_agent_type_does_not_misidentify_root_as_nested(project):
    payload = census_payload()
    payload["agent_type"] = "orchestrator"  # --agent main session, no agent_id.
    assert call_hook(project, "native_leaf", payload) == ""


@pytest.mark.parametrize("key,value", [
    ("resume", "old-fable"), ("resume", None), ("resume_id", "prior"),
    ("agent_id", "old"), ("team_name", "team"), ("tools", ["Bash"]),
    ("mcpServers", ["all"]), ("permissionMode", "bypassPermissions"),
    ("unknown_new_field", True), ("agent_type", "scout"),
])
def test_unqualified_launch_escape_fields_are_denied(project, key, value):
    payload = census_payload()
    payload["tool_input"][key] = value
    assert refusal(call_hook(project, "native_leaf", payload))


@pytest.mark.parametrize("model", [None, "inherit", "fable", "opus", "claude-sonnet-4-6", "not-sonnet", {}, 1])
def test_native_leaf_requires_exact_explicit_model(project, model):
    payload = census_payload()
    if model is None:
        payload["tool_input"].pop("model")
    else:
        payload["tool_input"]["model"] = model
    assert "NATIVE_MODEL_PIN_REQUIRED" in refusal(call_hook(project, "native_leaf", payload))


@pytest.mark.parametrize("agent", ["fork", "orchestrator", "builder", "Explore", "general-purpose"])
def test_native_leaf_cannot_expand_its_role(project, agent):
    payload = census_payload()
    payload["tool_input"]["subagent_type"] = agent
    assert "NATIVE_LEAF_ONLY" in refusal(call_hook(project, "native_leaf", payload))


@pytest.mark.parametrize("mode", ["router_only", "native_leaf", "", "unexpected"])
@pytest.mark.parametrize("raw", ["", "{", "[]", "null", '{"tool_name":"Agent","tool_name":"Read"}',
                                 '{"tool_name":"Agent","tool_input":{"x":NaN}}'])
def test_profiled_malformed_input_fails_closed(project, mode, raw):
    assert "HARNESS_INPUT_INVALID" in refusal(call_hook(project, mode, raw=raw))


def test_oversize_input_fails_closed(project):
    assert "HARNESS_INPUT_INVALID" in refusal(call_hook(project, "native_leaf", raw=" " * 262145))


@pytest.mark.parametrize("mode", ["", "typo"])
def test_unknown_mode_never_falls_back(project, mode):
    assert "HARNESS_PROFILE_INVALID" in refusal(call_hook(project, mode, census_payload()))


def test_duplicate_or_conflicting_routes_are_not_accepted(project):
    payload = census_payload()
    payload["tool_input"]["prompt"] += "\nROUTE: census\n"
    assert "exactly one ROUTE" in refusal(call_hook(project, "native_leaf", payload))


def test_original_route_contract_still_applies(project):
    payload = census_payload()
    payload["tool_input"]["prompt"] = "ROUTE: census\nMISSION: A deliberately incomplete but long enough mission."
    assert "required section" in refusal(call_hook(project, "native_leaf", payload))


def test_registry_failure_is_closed_in_profile(project):
    (project / profile.REGISTRY).write_text('{"routes": []}')
    assert "fail-closed" in refusal(call_hook(project, "native_leaf", census_payload()))


def test_unexpected_guard_error_is_closed_without_echoing_source(project):
    (project / profile.REGISTRY).write_text('{"routes": {"census": "SECRET_SENTINEL"}}')
    out = call_hook(project, "native_leaf", census_payload())
    assert "HARNESS_GUARD_ERROR" in refusal(out)
    assert "SECRET_SENTINEL" not in out


@pytest.mark.parametrize("mode", profile.MODES)
def test_nonlaunch_native_tools_remain_unchanged(project, mode):
    assert call_hook(project, mode, {"tool_name": "Read", "tool_input": {"file_path": "x.py"}}) == ""


@pytest.mark.parametrize("mode", profile.MODES)
def test_context_does_not_advertise_a_native_fable_exception(project, mode):
    out = call_hook(project, mode, context=True)
    assert mode.upper() in out
    assert "Exceptional Fable child =" not in out
    assert "existing Executive OS" in out
    assert "UNKNOWN/BLOCKED" in out


def test_legacy_sessions_are_not_silently_reconfigured(project):
    assert call_hook(project, None, census_payload()) == ""
    assert call_hook(project, None, fable_payload()) == ""
    assert "Exceptional Fable child =" in call_hook(project, None, context=True)


@pytest.mark.parametrize("version", ["", "latest", "v2.1.219", "2.1.216", "2.1.218", "3.0.0", "2.1.219-beta"])
def test_compiler_refuses_unknown_or_unsupported_versions(project, version):
    with pytest.raises(profile.ProfileError):
        profile.compile_profile(project, "router_only", version)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "async", "wrong_command", "no_task"])
def test_compiler_refuses_unqualified_existing_hook_wiring(project, mutation):
    path = project / profile.SETTINGS
    data = json.loads(path.read_text())
    group = data["hooks"]["PreToolUse"][0]
    if mutation == "missing":
        group["hooks"] = []
    elif mutation == "duplicate":
        group["hooks"] *= 2
    elif mutation == "async":
        group["hooks"][0]["async"] = True
    elif mutation == "wrong_command":
        group["hooks"][0]["command"] = "echo approved"
    else:
        group["matcher"] = "Agent|Workflow"
    path.write_text(json.dumps(data))
    with pytest.raises(profile.ProfileError):
        profile.compile_profile(project, "router_only", "2.1.219")


def test_compiler_refuses_registry_drift_instead_of_coercing_foreign_model(project):
    path = project / profile.REGISTRY
    data = json.loads(path.read_text())
    data["routes"]["census"]["model"] = "minimax"
    path.write_text(json.dumps(data))
    with pytest.raises(profile.ProfileError):
        profile.compile_profile(project, "native_leaf", "2.1.219")


def test_compiler_refuses_legacy_guard(project):
    path = project / profile.GUARD
    path.write_text(path.read_text().replace("NATIVE_PROFILE_SCHEMA_VERSION = 1", "NATIVE_PROFILE_SCHEMA_VERSION = 2"))
    with pytest.raises(profile.ProfileError):
        profile.compile_profile(project, "router_only", "2.1.219")


def test_source_hashes_bind_exact_input_bytes(project):
    a = profile.compile_profile(project, "router_only", "2.1.219")
    path = project / profile.CONTEXT
    path.write_text(path.read_text() + "\n# Source changed\n")
    b = profile.compile_profile(project, "router_only", "2.1.219")
    assert a["source_sha256"][profile.CONTEXT] != b["source_sha256"][profile.CONTEXT]
    assert b["launch_authorized"] is False


def test_compiler_does_not_execute_hook_source(project):
    path = project / profile.GUARD
    path.write_text(path.read_text() + "\nraise RuntimeError('DO_NOT_EXECUTE_SOURCE')\n")
    assert profile.compile_profile(project, "router_only", "2.1.219")["launch_authorized"] is False


def test_profile_cli_is_inert_and_emits_consumer_arguments(project):
    cp = subprocess.run([sys.executable, str(PROFILE_PATH), "--project-root", str(project),
                         "--mode", "native_leaf", "--claude-version", "2.1.219"],
                        text=True, capture_output=True, timeout=5, check=False)
    assert cp.returncode == 0, cp.stderr
    out = json.loads(cp.stdout)
    assert out["disposition"] == "CANDIDATE_NOT_ACTIVATED"
    assert out["launch_authorized"] is False
    assert "--agents" in out["cli_arguments"]
    assert all(flag not in out["cli_arguments"] for flag in ("--dangerously-skip-permissions", "--model"))


@pytest.mark.parametrize("mode", profile.MODES)
def test_real_hook_process_consumes_compiled_profile(project, mode):
    bundle = profile.compile_profile(project, mode, "2.1.219")
    env = os.environ.copy()
    env.update(bundle["settings_fragment"]["env"])
    env["CLAUDE_PROJECT_DIR"] = str(project)
    cp = subprocess.run([sys.executable, str(project / profile.GUARD)],
                        input=json.dumps(fable_payload()), text=True,
                        capture_output=True, env=env, timeout=5, check=False)
    assert cp.returncode == 0, cp.stderr
    assert refusal(cp.stdout)


@pytest.mark.parametrize("mode", profile.MODES)
@pytest.mark.parametrize("tool", ["SendMessage", "Skill", "TeamCreate"])
def test_non_agent_launch_and_resume_surfaces_are_refused(project, mode, tool):
    payload = {"tool_name": tool, "tool_input": {"to": "prior-fable", "skill": "census"}}
    assert "ROUTER_REQUIRED" in refusal(call_hook(project, mode, payload))


@pytest.mark.parametrize("key,value", [
    ("CLAUDE_CODE_SUBAGENT_MODEL", "fable"),
    ("CLAUDE_CODE_SUBAGENT_MODEL", "inherit"),
    ("CLAUDE_CODE_SUBAGENT_MODEL", None),
    ("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "1"),
    ("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "true"),
    ("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", None),
])
def test_ambient_model_override_is_not_spend_authority(project, key, value):
    assert "NATIVE_MODEL_ENV_REQUIRED" in refusal(call_hook(
        project, "native_leaf", census_payload(), env_overrides={key: value}))


def test_compiler_rejects_boolean_schema_version(project):
    path = project / profile.GUARD
    path.write_text(path.read_text().replace("NATIVE_PROFILE_SCHEMA_VERSION = 1",
                                             "NATIVE_PROFILE_SCHEMA_VERSION = True"))
    with pytest.raises(profile.ProfileError):
        profile.compile_profile(project, "router_only", "2.1.219")


@pytest.mark.parametrize("mode", profile.MODES)
def test_compiled_guard_missing_source_is_blocking_exit_two(project, mode):
    bundle = profile.compile_profile(project, mode, "2.1.239")
    command = bundle["settings_fragment"]["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    (project / profile.GUARD).unlink()
    result = subprocess.run(["/bin/sh", "-c", command], input="{}", text=True,
                            capture_output=True, env={"PATH": os.defpath,
                            "CLAUDE_PROJECT_DIR": str(project)})
    assert result.returncode == 2


def test_native_fixture_uses_compiled_argv_without_hook_injection():
    source = (ROOT / "tests/fable_native_cli_conformance.py").read_text()
    assert '*profile["cli_arguments"]' in source
    assert 'json.dumps(settings)' not in source
    assert 'source_settings' not in source
