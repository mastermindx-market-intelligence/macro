#!/usr/bin/env python3
"""PreToolUse guard for semantic agent routing, model control, and commission quality.

Direct Agent/Task spawns are type-checked against .claude/agent-routing.json:
ROUTE -> exact custom agent -> allowed model family -> required prompt contract.

This extends the older model-routing guard. Workflow scripts retain the existing
explicit-routing/FABLE-WHY checks because their internal agent() stages are
validated as code, not direct Agent tool calls.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Opt-in native harness restrictions, not a new model router or budget store.
# Unprofiled sessions retain their existing behavior during staged adoption.
NATIVE_PROFILE_SCHEMA_VERSION = 1
NATIVE_PROFILE_ENV = "MASTERMIND_NATIVE_DELEGATION_MODE"
NATIVE_PROFILE_MODES = ("router_only", "native_leaf")
NATIVE_LEAF_ROUTE = ("census", "scout", "sonnet")
MAX_PROFILE_INPUT_CHARS = 262144
NATIVE_LAUNCH_TOOLS = frozenset({
    "Agent", "Task", "Workflow", "TeamCreate", "SendMessage", "Skill",
})


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError("non-finite JSON value")


def _read_profile_payload() -> dict:
    raw = sys.stdin.read(MAX_PROFILE_INPUT_CHARS + 1)
    if len(raw) > MAX_PROFILE_INPUT_CHARS:
        raise ValueError("oversize hook input")
    payload = json.loads(raw, object_pairs_hook=_unique_object,
                         parse_constant=_reject_json_constant)
    if not isinstance(payload, dict):
        raise ValueError("hook input is not an object")
    return payload


def native_profile_refusal(payload: dict, mode: str) -> str | None:
    """Return a restriction only; never grant a Job, model spend or permission.

    native_leaf is an opt-in read-only census candidate, not a fleet budget.
    Its compiled CLI agent definition removes Bash, MCP and delegation tools.
    Actual settings/tool adoption is a separate runtime qualification gate.
    """
    if mode not in NATIVE_PROFILE_MODES:
        return "HARNESS_PROFILE_INVALID: unknown mode; do not fall back to legacy routing."
    tool = payload.get("tool_name")
    if not isinstance(tool, str) or not tool:
        return "HARNESS_INPUT_INVALID: missing tool identity."
    if tool not in NATIVE_LAUNCH_TOOLS:
        return None
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return "HARNESS_INPUT_INVALID: launch input must be an object."
    if mode == "router_only":
        return ("ROUTER_REQUIRED: native agent/workflow/team/skill launches and resume messages are "
                "disabled in this harness. Request the existing Executive OS child "
                "admission and router; if unavailable, report BLOCKED. Do not launch "
                "another provider CLI or switch carriers to evade this decision.")
    if tool not in {"Agent", "Task"}:
        return "ROUTER_REQUIRED: workflows, teams, skills and resume messages require governed admission."
    if "agent_id" in payload:
        return "NATIVE_LEAF_ONLY: a native helper cannot create descendants."
    if any(key in ti for key in ("resume", "resume_id", "agent_id", "team_name")):
        return "ROUTER_REQUIRED: resumed agents and teammates need reconciled admission."
    allowed_keys = {"description", "prompt", "subagent_type", "agent_type",
                    "model", "run_in_background", "isolation"}
    if set(ti) - allowed_keys:
        return "HARNESS_INPUT_INVALID: unqualified native launch field."
    if "subagent_type" in ti and "agent_type" in ti:
        return "HARNESS_INPUT_INVALID: ambiguous agent identity."
    sub = ti.get("subagent_type", ti.get("agent_type"))
    route, expected_agent, expected_model = NATIVE_LEAF_ROUTE
    if sub != expected_agent:
        return ("NATIVE_LEAF_ONLY: only the read-only scout census is admitted by "
                "this profile; independent leaders belong to Executive child Jobs.")
    # Exact alias required: no inheritance, Fable, full-ID guessing or substring match.
    if ti.get("model") != expected_model:
        return ("NATIVE_MODEL_PIN_REQUIRED: census must explicitly request sonnet; "
                "FABLE-WHY is an explanation, not budget or launch authority.")
    if (os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL") != expected_model
            or os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE") != "0"):
        return ("NATIVE_MODEL_ENV_REQUIRED: the compiled sonnet/default-model environment "
                "must be present; ambient force/inheritance is not qualified.")
    prompt = ti.get("prompt")
    if not isinstance(prompt, str):
        return "HARNESS_INPUT_INVALID: commission must be text."
    markers = ROUTE_RE.findall(prompt)
    if markers != [route]:
        return "NATIVE_LEAF_ONLY: exactly one ROUTE: census marker is required."
    if "run_in_background" in ti and type(ti["run_in_background"]) is not bool:
        return "HARNESS_INPUT_INVALID: run_in_background must be a boolean."
    if "isolation" in ti and ti["isolation"] != "worktree":
        return "HARNESS_INPUT_INVALID: unqualified isolation mode."
    return None


FABLE_OK_TYPES = {"orchestrator"}
# The line anchors are load-bearing: a mid-sentence prose mention ("we considered
# FABLE-WHY: creative: ...") must never count as the audit line. But the DOCUMENTED
# Workflow form of this line (CLAUDE.md §Model routing, operator re-enable
# 2026-07-18) is a JavaScript comment inside the script:
#     // FABLE-WHY: brainstorm: <specific reason>
# so a bare `^FABLE-WHY` anchor can never match it and would deny every
# fable-routed workflow stage. Leading comment markers/indentation are therefore
# allowed before the label — and nothing else.
FABLE_WHY_RE = re.compile(
    r"(?mi)^[ \t/#*\-]*FABLE-WHY\s*:\s*(orchestration|brainstorm|creative)\s*:\s*\S.{19,}$"
)
ROUTE_RE = re.compile(r"(?mi)^ROUTE\s*:\s*([a-z][a-z0-9_-]*)\s*$")
HEADER_RE = re.compile(r"(?mi)^\s*(?:#{1,6}\s*)?([A-Z][A-Z0-9 /_-]{1,48})\s*:\s*(.*)$")


def _project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()


def _load_registry() -> dict:
    path = _project_dir() / ".claude" / "agent-routing.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data.get("routes"), dict):
        raise ValueError("registry has no routes object")
    return data


def _deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    raise SystemExit(0)


def _allow() -> None:
    raise SystemExit(0)


def _model_family(model: str) -> str:
    m = (model or "").strip().lower()
    for fam in ("fable", "opus", "sonnet", "haiku"):
        if fam in m:
            return fam
    return m


def _frontmatter_model(subagent_type: str) -> str:
    if not subagent_type or not re.fullmatch(r"[\w-]+", subagent_type):
        return ""
    project = _project_dir()
    candidates = (
        project / ".claude" / "agents" / f"{subagent_type}.md",
        Path.home() / ".claude" / "agents" / f"{subagent_type}.md",
    )
    for path in candidates:
        try:
            if not path.is_file():
                continue
            head = path.read_text(encoding="utf-8", errors="replace")[:4096]
            m = re.search(r"(?mi)^\s*model\s*:\s*(\S+)", head)
            if m:
                return _model_family(m.group(1).strip().strip("'\""))
        except OSError:
            continue
    return ""


def _sections(text: str) -> dict[str, str]:
    matches = list(HEADER_RE.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = re.sub(r"\s+", " ", m.group(1).strip().upper())
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        inline = m.group(2).strip()
        tail = text[start:end].strip()
        content = "\n".join(x for x in (inline, tail) if x).strip()
        out[name] = content
    return out


def _validate_commission(prompt: str, spec: dict, route: str) -> None:
    sections = _sections(prompt)
    required = spec.get("required_prompt_sections") or []
    missing = [name for name in required if not sections.get(name, "").strip()]
    if missing:
        _deny(
            f"Blocked ROUTE {route}: commission is missing required section(s): "
            + ", ".join(missing)
            + ". Use exact `SECTION:` labels. The routing guard rejects under-specified "
              "worker prompts so cheap agents do not have to infer the mission."
        )

    mission = sections.get("MISSION", "").strip()
    if mission and len(mission) < 20:
        _deny(
            f"Blocked ROUTE {route}: MISSION is too vague ({len(mission)} chars). "
            "State one bounded objective with enough detail for a fresh worker to execute."
        )

    gates = sections.get("NOT DONE UNLESS", "").strip()
    if gates and len(gates) < 20:
        _deny(
            f"Blocked ROUTE {route}: NOT DONE UNLESS is too weak. "
            "Provide observable acceptance gates, not a generic completion phrase."
        )

    # Ensure the parent commission actually asks for the standardized return
    # packet that SubagentStop will validate.
    return_required = spec.get("required_return_sections") or []
    if return_required:
        ret = sections.get("RETURN", "").upper()
        absent = [name for name in return_required if name not in ret]
        if absent:
            _deny(
                f"Blocked ROUTE {route}: RETURN must request the standard evidence packet "
                f"labels {', '.join(return_required)}; missing {', '.join(absent)}."
            )


def _route_direct_spawn(ti: dict, tool: str, registry: dict) -> None:
    prompt = str(ti.get("prompt") or "")
    sub = str(ti.get("subagent_type") or ti.get("agent_type") or "").strip()
    explicit_model = str(ti.get("model") or "").strip()
    explicit_family = _model_family(explicit_model)

    route_match = ROUTE_RE.search(prompt)
    if not route_match:
        if sub == "fork":
            _deny(
                "Blocked: forked subagents inherit the parent context/model and bypass the "
                "cost-routing contract. Use a named ROUTE worker. If frontier context is "
                "truly required, keep the judgment in the main loop or use the gated "
                "ROUTE orchestration Fable child."
            )
        _deny(
            "Blocked: every direct Agent/Task spawn requires a semantic `ROUTE: <name>` "
            "line. Fable chooses the work class; .claude/agent-routing.json chooses the "
            "agent/model. Do not use generic/general-purpose/Explore/Plan as a routing bypass."
        )

    route = route_match.group(1).lower()
    spec = registry["routes"].get(route)
    if not spec:
        _deny(
            f"Blocked: unknown ROUTE {route!r}. Allowed routes: "
            + ", ".join(sorted(registry["routes"]))
        )

    if spec.get("main_loop_only"):
        _deny(
            f"Blocked: ROUTE {route} is main-loop-only. This work is final judgment/"
            "adjudication and must remain with Fable rather than being delegated."
        )

    expected_agent = str(spec.get("agent") or "")
    expected_model = _model_family(str(spec.get("model") or ""))

    if sub != expected_agent:
        _deny(
            f"Blocked ROUTE {route}: requires subagent_type {expected_agent!r}, got "
            f"{sub or 'default'!r}. Purpose: {spec.get('purpose', '')}"
        )

    if route == "orchestration":
        # Two legal forms (operator 2026-08-17): Fable (the exceptional child, with
        # its FABLE-WHY spend-audit line) or Opus running the fable-mode skill for
        # easier orchestration at half Fable's price. FABLE-WHY audits fable SPEND,
        # so the Opus form requires the skill directive instead of the audit line.
        opus_alt = spec.get("opus_alternative") or {}
        alt_family = _model_family(str(opus_alt.get("model") or ""))
        if alt_family and explicit_family == alt_family:
            skill = str(opus_alt.get("requires_skill") or "")
            if skill and skill.lower() not in prompt.lower():
                _deny(
                    "Blocked ROUTE orchestration on model 'opus': the commission must "
                    f"direct the worker to load the `{skill}` skill first (mention "
                    f"{skill!r} in the prompt). Opus holds the orchestrator seat only "
                    "under that doctrine; otherwise use explicit model 'fable' + FABLE-WHY."
                )
        elif explicit_family != "fable":
            _deny(
                "Blocked ROUTE orchestration: orchestrator requires explicit model 'fable' "
                "(with FABLE-WHY) or 'opus' with a fable-mode skill directive. "
                "Its frontmatter Opus model is a fail-safe floor, not permission to run the route."
            )
        else:
            if not FABLE_WHY_RE.search(prompt):
                _deny(
                    "Blocked ROUTE orchestration: missing valid "
                    "`FABLE-WHY: <orchestration|brainstorm|creative>: <specific reason>` "
                    "(specific reason must be at least 20 characters)."
                )
    else:
        # Named custom agents pin their model. If a caller redundantly supplies a model,
        # it may only match the registry; an upgrade/downgrade is a hard failure.
        if explicit_model and explicit_family != expected_model:
            _deny(
                f"Blocked ROUTE {route}: model override {explicit_model!r} resolves to "
                f"{explicit_family!r}, but this route is pinned to {expected_model!r}. "
                "Use the canonical custom agent without changing its model."
            )
        pinned = _frontmatter_model(expected_agent)
        if pinned != expected_model:
            _deny(
                f"Blocked ROUTE {route}: routing registry requires {expected_model!r} but "
                f".claude/agents/{expected_agent}.md pins {pinned or 'no model'!r}. "
                "The control plane is internally inconsistent; fix the registry/agent pair "
                "instead of spawning."
            )

    _validate_commission(prompt, spec, route)


def _validate_workflow(script: str) -> None:
    """Preserve the repo's existing Workflow cost guard."""
    script_has_fable_why = bool(FABLE_WHY_RE.search(script))

    if re.search(r"model\s*:\s*['\"`][^'\"`]*fable[^'\"`]*['\"`]", script, re.I):
        if not script_has_fable_why:
            _deny(
                "Blocked: workflow routes a stage to Fable without a script-level "
                "FABLE-WHY line. Reserve Fable for judge/synthesis stages, never bulk fan-out."
            )
    if re.search(r"agentType\s*:\s*['\"`]orchestrator['\"`]", script, re.I):
        if not script_has_fable_why:
            _deny(
                "Blocked: workflow uses agentType 'orchestrator' without a script-level "
                "FABLE-WHY line."
            )
    if "agent(" in script and "model" not in script and "agentType" not in script:
        _deny(
            "Blocked: workflow calls agent() with no model:/agentType routing; stages "
            "would inherit the session model."
        )


def main() -> None:
    mode = os.environ.get(NATIVE_PROFILE_ENV)
    try:
        payload = _read_profile_payload() if mode is not None else json.load(sys.stdin)
    except Exception:
        if mode is not None:
            _deny("HARNESS_INPUT_INVALID: malformed or oversized input; launch refused.")
        # Unprofiled compatibility only. Profiled launches always fail closed.
        return

    if mode is not None:
        refusal = native_profile_refusal(payload, mode)
        if refusal:
            _deny(refusal)

    tool = str(payload.get("tool_name") or "")
    ti = payload.get("tool_input") or {}
    if not isinstance(ti, dict):
        return

    if tool in ("Agent", "Task"):
        try:
            registry = _load_registry()
        except Exception as exc:
            _deny(
                "Blocked: agent routing registry could not be loaded; fail-closed to prevent "
                f"uncontrolled model spend ({type(exc).__name__}: {exc})."
            )
        _route_direct_spawn(ti, tool, registry)
        return

    if tool == "Workflow":
        script = str(ti.get("script") or "")
        if not script:
            sp = str(ti.get("scriptPath") or "")
            if sp and os.path.isfile(sp):
                try:
                    script = Path(sp).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    return
            else:
                return  # predefined workflow; versioned script is vetted in-repo
        _validate_workflow(script)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        if os.environ.get(NATIVE_PROFILE_ENV) is not None:
            _deny("HARNESS_GUARD_ERROR: policy evaluation failed; launch refused.")
        # Preserve compatibility only outside the explicitly selected harness.
        sys.exit(0)
