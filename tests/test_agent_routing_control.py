import json
import importlib.util
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".claude" / "hooks" / "model_routing_guard.py"
RETURN_GUARD = ROOT / ".claude" / "hooks" / "agent_return_guard.py"
CONTEXT = ROOT / ".claude" / "hooks" / "agent_routing_context.py"
REGISTRY = ROOT / ".claude" / "agent-routing.json"
PROFILE = ROOT / "scripts" / "fable_harness_profile.py"
profile_spec = importlib.util.spec_from_file_location("fable_harness_profile", PROFILE)
profile = importlib.util.module_from_spec(profile_spec)
profile_spec.loader.exec_module(profile)


def run_hook(script: Path, payload: dict):
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(ROOT)
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def commission(route: str, *, return_labels=True):
    base = {
        "census": [
            ("MISSION", "Map the complete current ingestion path for the commissioned subsystem."),
            ("WHY", "Fable needs verified current state before freezing the next architecture."),
            ("SCOPE", "Only the named subsystem and its direct contracts."),
            ("OUT OF SCOPE", "No implementation, redesign, or adjacent recommendations."),
            ("QUESTIONS", "Trace sources, transforms, consumers, and unresolved dead paths."),
            ("NOT DONE UNLESS", "Every material pipeline claim has exact file:line evidence and unknowns are explicit."),
            ("EVIDENCE REQUIRED", "Exact file:line receipts and commands used to establish coverage."),
        ],
        "build": [
            ("MISSION", "Implement the frozen parser contract and its regression tests exactly as specified."),
            ("WHY", "This packet realizes one frozen vertical slice of the parent architecture."),
            ("SCOPE", "Parser implementation and directly associated tests only."),
            ("OUT OF SCOPE", "No redesign, dependency migration, or unrelated cleanup."),
            ("FROZEN SPEC", "Preserve the existing public interface and add only the requested field handling."),
            ("OWNED FILES", "engine/example.py and tests/test_example.py."),
            ("TESTS", "Run the targeted parser tests and any directly affected contract tests."),
            ("NOT DONE UNLESS", "All specified behavior exists and the targeted test receipts are green."),
        ],
        "orchestration": [
            ("MISSION", "Design the bounded multi-wave architecture for this irreversible cross-repo program."),
            ("WHY", "The parent requires frontier judgment across conflicting architectural constraints."),
            ("SCOPE", "Architecture and wave decomposition only."),
            ("OUT OF SCOPE", "No mechanical census, implementation, or bulk verification."),
            ("NOT DONE UNLESS", "The architecture resolves the named tradeoffs and has explicit acceptance gates."),
        ],
    }[route]
    lines = [f"ROUTE: {route}"]
    if route == "orchestration":
        lines += [
            "FABLE-WHY: orchestration: This program has irreversible cross-repo decisions that ordinary draft-and-review cannot recover."
        ]
    for key, value in base:
        lines += ["", f"{key}:", value]
    ret = "STATUS / RESULT / EVIDENCE / GAPS / DEVIATIONS" if return_labels else "Give a useful answer."
    lines += ["", "RETURN:", ret]
    return "\n".join(lines)


def direct_payload(sub: str, prompt: str, model=None):
    ti = {"subagent_type": sub, "prompt": prompt}
    if model is not None:
        ti["model"] = model
    return {"tool_name": "Agent", "tool_input": ti}


def denial(cp):
    if not cp.stdout.strip():
        return ""
    data = json.loads(cp.stdout)
    return data["hookSpecificOutput"]["permissionDecisionReason"]


def native_binding(project=ROOT):
    if project != ROOT:
        compiler_spec = importlib.util.spec_from_file_location(
            "workspace_fable_harness_profile", project / "scripts/fable_harness_profile.py")
        compiler = importlib.util.module_from_spec(compiler_spec)
        compiler_spec.loader.exec_module(compiler)
    else:
        compiler = profile
    return compiler.compile_profile(project, "native_leaf", "2.1.259")["settings_fragment"]["env"]


def test_valid_census_uses_scout_sonnet_pin():
    cp = run_hook(GUARD, direct_payload("scout", commission("census")))
    assert cp.returncode == 0
    assert cp.stdout == ""


def test_wrong_agent_for_route_is_denied():
    cp = run_hook(GUARD, direct_payload("builder", commission("census")))
    assert "requires subagent_type 'scout'" in denial(cp)


def test_wrong_model_override_is_denied():
    cp = run_hook(GUARD, direct_payload("scout", commission("census"), model="opus"))
    assert "pinned to 'sonnet'" in denial(cp)


def test_matching_redundant_model_override_is_allowed():
    cp = run_hook(GUARD, direct_payload("scout", commission("census"), model="sonnet"))
    assert cp.stdout == ""


def test_missing_route_is_denied():
    cp = run_hook(
        GUARD,
        direct_payload("scout", "MISSION:\nMap the repository carefully and return evidence."),
    )
    assert "requires a semantic `ROUTE: <name>`" in denial(cp)


def test_fork_is_denied_as_cost_bypass():
    cp = run_hook(GUARD, direct_payload("fork", "Investigate the repository."))
    assert "forked subagents inherit" in denial(cp)


def test_judgment_cannot_be_spawned():
    prompt = "ROUTE: judgment\nMISSION:\nMake the final architecture decision for this program."
    cp = run_hook(GUARD, direct_payload("analyst", prompt, model="fable"))
    assert "main-loop-only" in denial(cp)


def test_valid_fable_orchestration_requires_explicit_fable():
    cp = run_hook(
        GUARD,
        direct_payload("orchestrator", commission("orchestration"), model="fable"),
    )
    assert cp.stdout == ""


def test_fable_orchestration_without_why_is_denied():
    prompt = commission("orchestration").replace(
        "FABLE-WHY: orchestration: This program has irreversible cross-repo decisions that ordinary draft-and-review cannot recover.\n",
        "",
    )
    cp = run_hook(GUARD, direct_payload("orchestrator", prompt, model="fable"))
    assert "missing valid" in denial(cp)


def _opus_orchestration(with_skill=True):
    # The Opus seat (operator 2026-08-17) spends no fable, so it carries no
    # FABLE-WHY; what it must carry instead is the fable-mode skill directive.
    prompt = commission("orchestration").replace(
        "FABLE-WHY: orchestration: This program has irreversible cross-repo decisions that ordinary draft-and-review cannot recover.\n",
        "",
    )
    if with_skill:
        prompt += "\n\nInvoke the fable-mode skill (Skill tool) before substantive work."
    return prompt


def test_opus_orchestration_with_fable_mode_skill_is_allowed():
    cp = run_hook(GUARD, direct_payload("orchestrator", _opus_orchestration(), model="opus"))
    assert cp.returncode == 0
    assert cp.stdout == ""


def test_opus_orchestration_without_fable_mode_skill_is_denied():
    cp = run_hook(
        GUARD, direct_payload("orchestrator", _opus_orchestration(with_skill=False), model="opus")
    )
    assert "fable-mode" in denial(cp)


def test_orchestration_on_other_models_is_still_denied():
    cp = run_hook(GUARD, direct_payload("orchestrator", _opus_orchestration(), model="sonnet"))
    assert "explicit model 'fable'" in denial(cp)


def test_under_specified_commission_is_denied():
    prompt = commission("census").replace(
        "\nQUESTIONS:\nTrace sources, transforms, consumers, and unresolved dead paths.", ""
    )
    cp = run_hook(GUARD, direct_payload("scout", prompt))
    assert "QUESTIONS" in denial(cp)


def test_return_instruction_must_request_standard_packet():
    cp = run_hook(
        GUARD, direct_payload("scout", commission("census", return_labels=False))
    )
    assert "RETURN must request" in denial(cp)


def test_workflow_without_routing_is_denied():
    payload = {
        "tool_name": "Workflow",
        "tool_input": {"script": "const x = await agent('do the thing', {label:'x'})"},
    }
    cp = run_hook(GUARD, payload)
    assert "no model:/agentType routing" in denial(cp)


def test_workflow_fable_requires_audit_line():
    payload = {
        "tool_name": "Workflow",
        "tool_input": {"script": "const x = await agent('judge', {model:'fable'})"},
    }
    cp = run_hook(GUARD, payload)
    assert "without a script-level FABLE-WHY" in denial(cp)


def test_worker_return_contract_accepts_complete_packet():
    payload = {
        "hook_event_name": "SubagentStop",
        "agent_type": "scout",
        "stop_hook_active": False,
        "last_assistant_message": (
            "STATUS: PASS\n"
            "RESULT:\nMapped the full current pipeline and its direct consumer.\n"
            "EVIDENCE:\nengine/x.py:10-41; config/y.yml:3-8.\n"
            "GAPS:\nnone\n"
            "DEVIATIONS:\nnone\n"
        ),
    }
    cp = run_hook(RETURN_GUARD, payload)
    assert cp.returncode == 0


def test_worker_return_contract_blocks_missing_evidence():
    payload = {
        "hook_event_name": "SubagentStop",
        "agent_type": "researcher",
        "stop_hook_active": False,
        "last_assistant_message": (
            "STATUS: PASS\nRESULT:\nThe research is complete.\nGAPS:\nnone\nDEVIATIONS:\nnone\n"
        ),
    }
    cp = run_hook(RETURN_GUARD, payload)
    assert cp.returncode == 2
    assert "missing/empty EVIDENCE" in cp.stderr


def test_worker_return_contract_blocks_none_evidence():
    payload = {
        "hook_event_name": "SubagentStop",
        "agent_type": "reviewer",
        "stop_hook_active": False,
        "last_assistant_message": (
            "STATUS: PASS\nRESULT:\nNo material findings found.\nEVIDENCE:\nnone\n"
            "GAPS:\nnone\nDEVIATIONS:\nnone\n"
        ),
    }
    cp = run_hook(RETURN_GUARD, payload)
    assert cp.returncode == 2
    assert "EVIDENCE cannot be empty" in cp.stderr


def test_worker_return_contract_one_retry_only():
    payload = {
        "hook_event_name": "SubagentStop",
        "agent_type": "scout",
        "stop_hook_active": True,
        "last_assistant_message": "I think it is done.",
    }
    cp = run_hook(RETURN_GUARD, payload)
    assert cp.returncode == 0


def test_registry_agent_frontmatter_models_are_consistent():
    registry = json.loads(REGISTRY.read_text())
    for route, spec in registry["routes"].items():
        agent = spec.get("agent")
        if not agent or route == "orchestration":
            continue
        text = (ROOT / ".claude" / "agents" / f"{agent}.md").read_text()
        m = re.search(r"(?mi)^model:\s*(\S+)", text)
        assert m, (route, agent)
        assert m.group(1).strip("'\"").lower() == spec["model"], (route, agent)


def test_settings_wire_all_three_control_hooks():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
    assert "SubagentStop" in settings["hooks"]
    text = json.dumps(settings)
    assert "model_routing_guard.py" in text
    assert "agent_return_guard.py" in text
    assert "agent_routing_context.py" in text


def test_context_hook_exposes_compact_route_map():
    cp = run_hook(CONTEXT, {})
    assert cp.returncode == 0
    assert "census->scout(sonnet)" in cp.stdout
    assert "judgment->Fable main loop" in cp.stdout
    assert "ROUTE orchestration" in cp.stdout


def test_registry_cost_tiers_cannot_silently_drift():
    registry = json.loads(REGISTRY.read_text())
    routes = registry["routes"]
    assert routes["extract"]["model"] == "haiku"
    # Build returned to Sonnet by standing operator order 2026-08-17, reversing the
    # 2026-07-21 "Opus builds code" order. The design lane (2026-07-18) and the
    # review lane did NOT reverse — they stay Opus, asserted as a closed set below.
    assert routes["build"]["model"] == "sonnet"
    assert {r for r, s in routes.items() if s["model"] == "sonnet"} == {
        "census", "research", "draft", "build"
    }
    assert {r for r, s in routes.items() if s["model"] == "opus"} == {
        "analysis", "debug", "review", "design"
    }
    assert {r for r, s in routes.items() if s["model"] == "fable"} == {
        "judgment", "orchestration"
    }
    assert routes["judgment"]["main_loop_only"] is True
    assert routes["orchestration"]["requires_fable_why"] is True
    # Opus may hold the orchestrator seat only under the fable-mode doctrine
    # (operator 2026-08-17); the skill it names must actually exist.
    assert routes["orchestration"]["opus_alternative"] == {
        "model": "opus",
        "requires_skill": "fable-mode",
    }
    assert (ROOT / ".claude" / "skills" / "fable-mode" / "SKILL.md").is_file()


def test_read_only_routes_are_not_pointed_at_authoring_agents():
    # A cheap MODEL is not a cheap AGENT IDENTITY. `build` is legitimately Sonnet
    # (operator 2026-08-17), so the tier alone no longer separates read-only work
    # from authoring work — the agent identity does. The extraction/census/research
    # routes must never resolve to the builder or designer, whose contracts assume
    # an owned-files write mandate, and the build route must keep its own agent.
    registry = json.loads(REGISTRY.read_text())
    for route in ("extract", "census", "research"):
        assert registry["routes"][route]["agent"] not in {"builder", "designer"}
        assert registry["routes"][route]["model"] in {"haiku", "sonnet"}
    assert registry["routes"]["build"]["agent"] == "builder"
    assert registry["routes"]["design"]["agent"] == "designer"


# First-use grammar comes from the existing registry, not a copied rulebook.
def _template_context(project=ROOT, mode=None, env=None):
    env = os.environ.copy() if env is None else {**os.environ, **env}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.pop("MASTERMIND_NATIVE_DELEGATION_MODE", None)
    supplied_binding = env.get(profile.BINDING_ENV)
    env.pop(profile.BINDING_ENV, None)
    if mode is not None:
        env["MASTERMIND_NATIVE_DELEGATION_MODE"] = mode
        if mode == "native_leaf":
            env.update(native_binding(project) if supplied_binding is None
                       else {profile.BINDING_ENV: supplied_binding})
    context = project / ".claude/hooks/agent_routing_context.py" if project != ROOT else CONTEXT
    cp = subprocess.run([sys.executable, "-B", str(context)], input=json.dumps({"cwd": str(project)}),
                        text=True, capture_output=True, env=env, cwd=project, timeout=10)
    assert cp.returncode == 0, cp.stderr
    assert cp.stderr == ""
    return cp.stdout


def _templates(text):
    return dict(re.findall(
        r"COMMISSION TEMPLATE ([a-z][a-z0-9_-]*)\n```text\n(.*?)\n```",
        text, re.S))


def _filled_template(text):
    return re.sub(r"<[A-Z][A-Z0-9 /_-]*>",
                  "Verify the bounded fixture contract and return exact source evidence.", text)


def _registry_fixture(tmp_path, registry):
    folder = tmp_path / ".claude"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "agent-routing.json").write_text(json.dumps(registry))


def _native_project(tmp_path, registry):
    project = tmp_path / "project"
    for relative in (".claude/hooks/model_routing_guard.py",
                     ".claude/hooks/agent_routing_context.py",
                     ".claude/settings.json", ".claude/agents/scout.md",
                     "scripts/fable_harness_profile.py"):
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    _registry_fixture(project, registry)
    return project.resolve()


@pytest.mark.parametrize("route", ["extract", "census", "research", "draft",
                                 "analysis", "debug", "build", "review", "design",
                                 "orchestration"])
def test_first_use_template_has_exact_registry_sections(route):
    text = _template_context()
    templates = _templates(text)
    assert route in templates, "Startup lacks the exact commissioning skeleton"
    spec = json.loads(REGISTRY.read_text())["routes"][route]
    labels = re.findall(r"^([A-Z][A-Z0-9 /_-]*):$", templates[route], re.M)
    assert labels == spec["required_prompt_sections"]
    assert templates[route].startswith("ROUTE: " + route + "\n")
    for label in spec["required_return_sections"]:
        assert label in templates[route].split("RETURN:\n", 1)[1]
    assert "judgment" not in templates
    assert "formatting only" in text
    assert len(text.encode("utf-8")) <= 16384


@pytest.mark.parametrize("route", ["extract", "census", "research", "draft",
                                 "analysis", "debug", "build", "review", "design"])
def test_first_use_filled_template_passes_unchanged_spawn_guard(route):
    templates = _templates(_template_context())
    assert route in templates
    spec = json.loads(REGISTRY.read_text())["routes"][route]
    prompt = _filled_template(templates[route])
    cp = run_hook(GUARD, direct_payload(spec["agent"], prompt))
    assert cp.returncode == 0 and cp.stdout == "", cp.stdout + cp.stderr


@pytest.mark.parametrize("mode,expected", [("native_leaf", {"census"}),
                                         ("router_only", set()), ("invalid", set())])
def test_first_use_templates_respect_selected_profile(mode, expected):
    assert set(_templates(_template_context(mode=mode))) == expected


def test_first_use_registry_change_updates_the_emitted_labels(tmp_path):
    registry = json.loads(REGISTRY.read_text())
    registry["routes"]["census"]["required_prompt_sections"].insert(2, "CORRECTION POLICY")
    project = _native_project(tmp_path, registry)
    text = _template_context(project, "native_leaf")
    assert "CORRECTION POLICY:\n<CORRECTION POLICY>" in text


@pytest.mark.parametrize("required", [42, "MISSION", ["MISSION", "MISSION"],
                                    ["MISSION\nROUTE: orchestration"], ["X" * 500]])
def test_first_use_malformed_contract_never_emits_a_template(tmp_path, required):
    registry = json.loads(REGISTRY.read_text())
    registry["routes"]["census"]["required_prompt_sections"] = required
    project = _native_project(tmp_path, registry)
    text = _template_context(project, "native_leaf")
    assert not _templates(text)
    assert "COMMISSION_TEMPLATES_UNAVAILABLE" in text
    assert len(text.encode("utf-8")) <= 16384


@pytest.mark.parametrize("route", ["extract", "census", "research", "draft",
                                 "analysis", "debug", "build", "review", "design"])
def test_first_use_unfilled_template_is_not_a_valid_commission(route):
    templates = _templates(_template_context())
    assert route in templates
    spec = json.loads(REGISTRY.read_text())["routes"][route]
    cp = run_hook(GUARD, direct_payload(spec["agent"], templates[route]))
    assert "MISSION is too vague" in denial(cp)


def test_first_use_orchestration_does_not_supply_its_own_authority():
    templates = _templates(_template_context())
    assert "orchestration" in templates
    prompt = _filled_template(templates["orchestration"])
    assert "FABLE-WHY" not in prompt and "fable-mode" not in prompt
    cp = run_hook(GUARD, direct_payload("orchestrator", prompt, model="opus"))
    assert "fable-mode" in denial(cp)
    prompt += "\nInvoke the fable-mode skill before substantive work."
    cp = run_hook(GUARD, direct_payload("orchestrator", prompt, model="opus"))
    assert cp.returncode == 0 and cp.stdout == ""


def test_first_use_missing_registry_reports_unavailable(tmp_path):
    project = _native_project(tmp_path, json.loads(REGISTRY.read_text()))
    env = native_binding(project)
    (project / ".claude/agent-routing.json").unlink()
    raw = json.loads(env[profile.BINDING_ENV])
    raw["files"][profile.REGISTRY] = hashlib.sha256(b"").hexdigest()
    env[profile.BINDING_ENV] = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    (project / ".claude/agent-routing.json").write_bytes(b"")
    text = _template_context(project, "native_leaf", env)
    (project / ".claude/agent-routing.json").unlink()
    assert "COMMISSION_TEMPLATES_UNAVAILABLE" in text
    assert not _templates(text)


@pytest.mark.parametrize("defect", ["none", "missing_colon", "wrong_model", "duplicate_route"])
def test_first_use_native_leaf_keeps_all_launch_refusals(defect):
    templates = _templates(_template_context(mode="native_leaf"))
    assert "census" in templates
    prompt = _filled_template(templates["census"])
    model = "sonnet"
    if defect == "missing_colon":
        prompt = prompt.replace("QUESTIONS:", "QUESTIONS")
    elif defect == "wrong_model":
        model = "opus"
    elif defect == "duplicate_route":
        prompt += "\nROUTE: orchestration\n"
    env = {**os.environ, **native_binding(), "CLAUDE_PROJECT_DIR": str(ROOT),
           "MASTERMIND_NATIVE_DELEGATION_MODE": "native_leaf",
           "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
           "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "0"}
    cp = subprocess.run([sys.executable, "-B", str(GUARD)], text=True,
                        input=json.dumps({"cwd": str(ROOT), **direct_payload(
                            "scout", prompt, model=model)}),
                        capture_output=True, env=env, cwd=ROOT, timeout=10)
    assert cp.returncode == 0 and cp.stderr == ""
    if defect == "none":
        assert cp.stdout == ""
    else:
        assert json.loads(cp.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_first_use_native_leaf_requires_compiled_source_binding():
    templates = _templates(_template_context(mode="native_leaf"))
    prompt = _filled_template(templates["census"])
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT),
           "MASTERMIND_NATIVE_DELEGATION_MODE": "native_leaf",
           "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
           "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "0"}
    env.pop("MASTERMIND_NATIVE_PROFILE_BINDING", None)
    cp = subprocess.run([sys.executable, "-B", str(GUARD)], text=True,
                        input=json.dumps({"cwd": str(ROOT), **direct_payload(
                            "scout", prompt, model="sonnet")}),
                        capture_output=True, env=env, cwd=ROOT, timeout=10)
    assert cp.returncode == 0 and cp.stderr == ""
    assert "HARNESS_BINDING_REQUIRED" in denial(cp)


@pytest.mark.parametrize("broken", [None, [], {"census": None}])
def test_first_use_malformed_route_map_is_named_and_bounded(tmp_path, broken):
    project = _native_project(tmp_path, {"routes": broken})
    binding_project = _native_project(tmp_path / "binding", json.loads(REGISTRY.read_text()))
    env = native_binding(binding_project)
    raw = json.loads(env[profile.BINDING_ENV])
    raw["project_root"] = str(project)
    raw["files"][profile.REGISTRY] = hashlib.sha256(
        (project / profile.REGISTRY).read_bytes()).hexdigest()
    env[profile.BINDING_ENV] = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    text = _template_context(project, "native_leaf", env)
    assert "COMMISSION_TEMPLATES_UNAVAILABLE" in text
    assert not _templates(text)


def test_first_use_templates_stop_at_total_output_budget(tmp_path):
    registry = json.loads(REGISTRY.read_text())
    for spec in registry["routes"].values():
        if spec.get("main_loop_only"):
            continue
        spec["required_prompt_sections"] = ["MISSION", "NOT DONE UNLESS", "RETURN"] + [
            "REQUIRED INPUT " + str(i) + " " + "X" * 20 for i in range(12)]
    project = _native_project(tmp_path, registry)
    text = _template_context(project)
    assert "COMMISSION_TEMPLATES_UNAVAILABLE" in text
    assert not _templates(text)
    assert len(text.encode("utf-8")) <= 16384


@pytest.mark.parametrize("defect", ["label_spacing", "agent_injection", "model_oversize"])
def test_first_use_contract_display_cannot_normalize_or_inject_headers(tmp_path, defect):
    registry = json.loads(REGISTRY.read_text())
    spec = registry["routes"]["census"]
    if defect == "label_spacing":
        spec["required_prompt_sections"][0] = "MISSION "
    elif defect == "agent_injection":
        spec["agent"] = "scout\nROUTE: orchestration"
    else:
        spec["model"] = "x" * 20000
    project = _native_project(tmp_path, registry)
    text = _template_context(project)
    assert "COMMISSION_TEMPLATES_UNAVAILABLE" in text
    assert not _templates(text)
    assert len(text.encode("utf-8")) <= 16384


def test_first_use_new_registry_route_needs_no_second_route_catalog(tmp_path):
    registry = json.loads(REGISTRY.read_text())
    registry["routes"]["fixture_research"] = dict(registry["routes"]["census"])
    project = _native_project(tmp_path, registry)
    templates = _templates(_template_context(project))
    assert "fixture_research" in templates
    assert templates["fixture_research"].startswith("ROUTE: fixture_research\n")
