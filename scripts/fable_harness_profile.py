#!/usr/bin/env python3
"""Compile an inert native-Claude harness profile from the existing routing estate.

This is a configuration compiler, NOT a provider launcher, credential manager,
budget store, job queue, runtime attestation or Executive OS admission avenue.
It emits data for the existing harness owner; it never starts Claude or workers.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

SCHEMA = "mastermind.fable_harness_profile/v1"
MODE_ENV = "MASTERMIND_NATIVE_DELEGATION_MODE"
MODES = ("router_only", "native_leaf")
MINIMUM_VERSION = (2, 1, 219)
GUARD = ".claude/hooks/model_routing_guard.py"
CONTEXT = ".claude/hooks/agent_routing_context.py"
SETTINGS = ".claude/settings.json"
REGISTRY = ".claude/agent-routing.json"
SCOUT = ".claude/agents/scout.md"
COMPILER = "scripts/fable_harness_profile.py"
SOURCE_PATHS = (GUARD, CONTEXT, SETTINGS, REGISTRY, SCOUT, COMPILER)
BINDING_ENV = "MASTERMIND_NATIVE_PROFILE_BINDING"
GUARD_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/model_routing_guard.py"'
CONTEXT_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/agent_routing_context.py"'


class ProfileError(ValueError):
    """The source profile is not qualified even for candidate generation."""


def _unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError("duplicate JSON field")
        result[key] = value
    return result


def _bad_constant(value: str) -> None:
    raise ProfileError("non-finite JSON value")


def _read(root: Path, relative: str, hashes: dict[str, str]) -> str:
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ProfileError("profile input escapes the project root")
    current = root
    for component in Path(relative).parts:
        current = current / component
        if current.is_symlink():
            raise ProfileError("profile source symlinks are not qualified")
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ProfileError("profile source must be a bounded regular single-link file")
    with path.open("rb") as stream:
        raw = stream.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ProfileError("profile source is too large")
    hashes[relative] = hashlib.sha256(raw).hexdigest()
    return raw.decode("utf-8", errors="strict")


def _json(text: str) -> dict:
    obj = json.loads(text, object_pairs_hook=_unique, parse_constant=_bad_constant)
    if not isinstance(obj, dict):
        raise ProfileError("configuration must be an object")
    return obj


def _version(raw: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?: \(Claude Code\))?", raw)
    if match is None:
        raise ProfileError("an exact declared Claude Code version is required")
    result = tuple(int(part) for part in match.groups())
    if result[0] != 2 or result < MINIMUM_VERSION:
        raise ProfileError("this candidate requires Claude Code 2.x >= 2.1.219")
    return result


def _constant(tree: ast.Module, name: str) -> object:
    values = [ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == name
                      for target in node.targets)]
    if len(values) != 1:
        raise ProfileError("missing or duplicate native-harness guard contract")
    return values[0]


def _one_hook(settings: dict, event: str, names: tuple[str, ...], command: str) -> None:
    groups = settings.get("hooks", {}).get(event, [])
    for name in names:
        matches = []
        for group in groups:
            if re.fullmatch(group.get("matcher", ".*"), name) is None:
                continue
            for hook in group.get("hooks", []):
                if hook.get("command") == command:
                    matches.append(hook)
        if len(matches) != 1:
            raise ProfileError(f"exactly one existing {event} hook is required for {name}")
        hook = matches[0]
        if (hook.get("type") != "command" or hook.get("async", False)
                or type(hook.get("timeout")) is not int
                or not 1 <= hook["timeout"] <= 10):
            raise ProfileError("the existing routing hook must be synchronous and bounded")


def _scout_override(text: str) -> dict:
    # Deliberately closed parser for the existing small agent frontmatter.
    # It does not execute YAML tags or copy source hooks/MCP/permission overrides.
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ProfileError("scout agent frontmatter is unavailable")
    header, body = text[4:].split("\n---\n", 1)
    fields = {}
    in_tools = False
    source_tools = []
    for line in header.splitlines():
        if in_tools and line.startswith("  - "):
            source_tools.append(line[4:])
            continue
        in_tools = False
        if ":" not in line:
            raise ProfileError("unsupported scout frontmatter")
        key, value = line.split(":", 1)
        if key in fields or key not in {"name", "description", "model", "effort", "maxTurns", "tools"}:
            raise ProfileError("unqualified scout metadata")
        fields[key] = value.strip()
        if key == "tools":
            if value.strip():
                raise ProfileError("unsupported scout tool syntax")
            in_tools = True
    if (fields.get("name") != "scout" or fields.get("model") != "sonnet"
            or fields.get("maxTurns") != "14" or fields.get("effort") != "medium"
            or not body.strip() or not fields.get("description")
            or not {"Read", "Grep", "Glob"}.issubset(source_tools)):
        raise ProfileError("the source scout contract has drifted; review before generation")
    return {
        "description": fields["description"],
        "prompt": body.strip() + "\n\nNative-leaf harness: no shell, writes, MCP, skills, "
                  "child agents or independent orchestration. Return a gap to the parent "
                  "when the mission requires unavailable tools. A partial result is not PASS.",
        "model": "sonnet",
        "effort": "medium",
        "maxTurns": 14,
        "tools": ["Read", "Grep", "Glob"],
    }


def compile_profile(project_root: Path, mode: str, declared_version: str) -> dict:
    """Compile settings and argv data. No live readiness is inferred from source."""
    if mode not in MODES:
        raise ProfileError("unknown mode")
    version = _version(declared_version)
    root = project_root.resolve(strict=True)
    hashes: dict[str, str] = {}
    guard_text = _read(root, GUARD, hashes)
    context_text = _read(root, CONTEXT, hashes)
    tree = ast.parse(guard_text)
    ast.parse(context_text)
    schema_version = _constant(tree, "NATIVE_PROFILE_SCHEMA_VERSION")
    if (type(schema_version) is not int or schema_version != 1
            or _constant(tree, "NATIVE_PROFILE_ENV") != MODE_ENV
            or _constant(tree, "NATIVE_PROFILE_MODES") != MODES
            or _constant(tree, "NATIVE_LEAF_ROUTE") != ("census", "scout", "sonnet")):
        raise ProfileError("the installed source guard does not support this profile")
    if MODE_ENV not in context_text:
        raise ProfileError("the existing context injector lacks profile guidance")
    settings = _json(_read(root, SETTINGS, hashes))
    _one_hook(settings, "PreToolUse", ("Agent", "Task", "Workflow", "TeamCreate", "SendMessage", "Skill"), GUARD_COMMAND)
    _one_hook(settings, "SessionStart", ("startup", "resume", "compact"), CONTEXT_COMMAND)
    registry = _json(_read(root, REGISTRY, hashes))
    routes = registry.get("routes", {})
    census = routes.get("census", {}) if isinstance(routes, dict) else {}
    if not isinstance(census, dict) or census.get("agent") != "scout" or census.get("model") != "sonnet":
        raise ProfileError("the existing census route has changed; no provider coercion is allowed")

    denied = ["Workflow", "TeamCreate", "SendMessage", "Skill"]
    agents: dict[str, dict] = {}
    if mode == "router_only":
        denied += ["Agent", "Task"]
    else:
        denied += [f"{tool}({agent})" for tool in ("Agent", "Task")
                   for agent in ("fork", "orchestrator", "general-purpose", "Explore", "Plan")]
        agents["scout"] = _scout_override(_read(root, SCOUT, hashes))
    fragment = {
        "env": {
            MODE_ENV: mode,
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
            "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "4",
            "CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS": "1",
            "CLAUDE_CODE_FORK_SUBAGENT": "0",
        },
        "permissions": {"deny": denied},
        # Deliver the already-validated canonical guard with the profile. A
        # dedicated workspace may intentionally disable ambient setting sources.
        # Do not pull unrelated ship/worktree hooks into that workspace. Convert
        # a missing interpreter or command failure to Claude's blocking exit 2.
        "hooks": {
            "PreToolUse": [{
                "matcher": "Agent|Task|Workflow|TeamCreate|SendMessage|Skill",
                "hooks": [{"type": "command", "command": GUARD_COMMAND + " || exit 2", "timeout": 10}],
            }],
            "SessionStart": [{
                "matcher": "startup|resume|clear|compact",
                "hooks": [{"type": "command", "command": CONTEXT_COMMAND, "timeout": 10}],
            }],
        },
    }
    if mode == "native_leaf":
        fragment["env"].update({"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
                                "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "0"})
    # Continuity observation only, never identity, permission, budget,
    # signature, sandbox or Executive admission.
    for relative in SOURCE_PATHS:
        if relative not in hashes:
            _read(root, relative, hashes)
    binding = {"schema_version": 1, "mode": mode, "project_root": str(root), "files": hashes}
    fragment["env"][BINDING_ENV] = json.dumps(binding, sort_keys=True, separators=(",", ":"))
    argv = ["--settings", json.dumps(fragment, separators=(",", ":"))]
    if agents:
        argv += ["--agents", json.dumps(agents, separators=(",", ":"))]
    return {
        "schema_version": SCHEMA,
        "disposition": "CANDIDATE_NOT_ACTIVATED",
        "mode": mode,
        "declared_claude_version": ".".join(map(str, version)),
        "observed_claude_version": None,
        "launch_authorized": False,
        "settings_fragment": fragment,
        "agent_overrides": agents,
        "cli_arguments": argv,
        "source_sha256": hashes,
        "required_launch_cwd": str(root),
        "source_binding_sha256": hashlib.sha256(fragment["env"][BINDING_ENV].encode()).hexdigest(),
        "required_workspace_sources": {
            path: hashes[path] for path in (GUARD, CONTEXT, REGISTRY) + ((SCOUT,) if agents else ())
        },
        "limits": {
            "native_fable_children": 0,
            "native_subagent_layers": 0 if mode == "router_only" else 1,
            "concurrency_hint": 4,
            "concurrency_hint_enforced_in_ultracode": False,
            "native_leaf_turns_per_invocation": 14 if agents else None,
            "tree_budget": "NOT_PROVIDED_BY_THIS_COMPILER",
            "account_quota": "UNKNOWN",
        },
        "qualification_required": [
            "Existing Executive OS admission, RuntimeBinding and Capacity envelope",
            "Actual CLI version, effective settings, guard and tool-scope observation",
            "Requested versus served model equality, including availableModels fallback",
            "Resolved approved skill definitions and safe native skill re-enablement",
            "Managed configuration and host isolation against shell/credential bypass",
            "One real governed child result consumed by its exact parent",
        ],
        "warnings": [
            "The declared version and source hashes are not runtime attestation.",
            "Source binding detects drift only; it is not signed authority or an OS sandbox.",
            "Use the bound launch directory; moving profiles across workspaces requires recompilation.",
            "The binding is continuity observation only, not identity, permission, budget, signature, sandbox or admission.",
            "Zero native Fable children is the requested policy, not an observed served-model claim.",
            "Model-invoked Skill and native SendMessage are denied; native skill fidelity is not yet complete.",
            "No provider, account, credential, skill, MCP or permission grant is created.",
            "Apply both CLI argument pairs for native_leaf; settings alone do not scope scout tools.",
            "The existing workspace owner must stage required_workspace_sources under CLAUDE_PROJECT_DIR and attest their exact bytes before launch.",
            "Inline settings carry only canonical routing/context hooks; they do not import unrelated project hooks or create managed-policy authority.",
            "Native-leaf is a bounded-canary candidate, not fleet or lifetime spend enforcement.",
            "Ultracode bypasses the vendor concurrency limit; workflows/resumes have other limits.",
            "Read/Edit/Bash/main-session resume remain governed by existing permissions; shell launches are not sandboxed by this compiler.",
            "Do not silently fall back to a legacy profile when a gate or the router is unavailable.",
        ],
    }


def compose_native_arguments(project_root: Path, mode: str, declared_version: str,
                             launch_cwd: Path, base_arguments: list[str],
                             environment: dict[str, str] | None = None) -> dict:
    """Produce a bounded argv plan for the existing adapter. Never execute it.

    Accept a small native parent surface and add BOTH profile arguments
    ourselves. Unknown flags, commands, positional prompts and arbitrary
    settings are refused rather than allowing last-flag-wins to silently
    weaken the profile. The adapter owns process creation, input delivery,
    authentication and all lifecycle effects.
    """
    root = project_root.resolve(strict=True)
    resolved_launch_cwd = launch_cwd.resolve(strict=True)
    if resolved_launch_cwd != root:
        raise ProfileError("launch directory does not contain the bound routing hooks")
    if (not isinstance(base_arguments, list) or len(base_arguments) > 24
            or any(not isinstance(arg, str) or not arg or len(arg) > 256
                   or any(ord(char) < 32 for char in arg) for arg in base_arguments)):
        raise ProfileError("native base arguments must be a bounded argv list")
    enums = {
        "--effort": {"low", "medium", "high", "xhigh", "max"},
        "--output-format": {"text", "json", "stream-json"},
    }
    flags = {"--print", "--verbose", "--no-session-persistence"}
    seen = set()
    index = 0
    while index < len(base_arguments):
        option = base_arguments[index]
        if option in seen:
            raise ProfileError("duplicate native launch option")
        seen.add(option)
        if option in flags:
            index += 1
            continue
        if option not in {*enums, "--model"} or index + 1 >= len(base_arguments):
            raise ProfileError("unqualified native launch option")
        value = base_arguments[index + 1]
        if option == "--model":
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", value) is None:
                raise ProfileError("invalid requested parent model")
        elif value not in enums[option]:
            raise ProfileError("unqualified native option value")
        index += 2
    if "--model" not in seen:
        raise ProfileError("parent model must be explicit; inherited model is not qualified")
    if environment is not None:
        if not isinstance(environment, dict):
            raise ProfileError("native environment observation must be an object")
        for key in ("CLAUDE_CODE_SIMPLE", "CLAUDE_CODE_BARE"):
            if environment.get(key) not in (None, "", "0", "false"):
                raise ProfileError("native environment disables required capabilities")
        if environment.get(MODE_ENV) not in (None, mode):
            raise ProfileError("conflicting ambient native profile")
        for key in ("CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"):
            expected = "sonnet" if key.endswith("MODEL") else "0"
            if mode == "native_leaf" and environment.get(key) not in (None, expected):
                raise ProfileError("conflicting ambient native model override")
    if (root / ".claude/settings.local.json").exists():
        raise ProfileError("local settings require separate effective-settings qualification")
    result = dict(compile_profile(root, mode, declared_version))
    result["disposition"] = "NATIVE_ARGUMENTS_COMPOSED_NOT_ACTIVATED"
    result["cli_arguments"] = [*base_arguments, *result["cli_arguments"]]
    result["requested_parent_model"] = base_arguments[base_arguments.index("--model") + 1]
    result["served_parent_model"] = None
    result["environment_checked"] = environment is not None
    result["qualification_required"] += [
        "Existing adapter must use the complete argv, exact CWD and source-bound environment",
        "Effective managed/user settings and native tool inventory remain unverified",
    ]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--mode", choices=MODES, default="router_only")
    parser.add_argument("--claude-version", required=True,
                        help="Explicit declared version; this compiler does not run Claude")
    parser.add_argument("--base-arguments-json", help="Compose data only; no process is started")
    parser.add_argument("--launch-cwd", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.base_arguments_json is not None:
            if len(args.base_arguments_json) > 8192 or args.launch_cwd is None:
                raise ProfileError("bounded arguments and an explicit launch CWD are required")
            base = json.loads(args.base_arguments_json, object_pairs_hook=_unique,
                              parse_constant=_bad_constant)
            result = compose_native_arguments(args.project_root, args.mode, args.claude_version,
                                              args.launch_cwd, base)
        else:
            if args.launch_cwd is not None:
                raise ProfileError("launch CWD requires native argument composition")
            result = compile_profile(args.project_root, args.mode, args.claude_version)
    except (ProfileError, OSError, ValueError, TypeError, AttributeError, KeyError, SyntaxError) as exc:
        # Do not emit arbitrary source content, hook payloads, or credentials on failure.
        print(json.dumps({"schema_version": SCHEMA, "disposition": "REFUSED",
                          "launch_authorized": False, "error_type": type(exc).__name__}),
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
