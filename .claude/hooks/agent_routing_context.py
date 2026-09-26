#!/usr/bin/env python3
"""SessionStart context injector for the semantic agent-routing control plane."""
from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path


def _section_labels(value: object) -> list[str]:
    """Validate display grammar only; the existing spawn guard owns admission."""
    if (not isinstance(value, list) or len(value) > 16
            or any(not isinstance(s, str) or not re.fullmatch(
                r"[A-Z][A-Z0-9 /_-]{1,48}", s) or s != " ".join(s.split())
                   for s in value)
            or len(set(value)) != len(value) or "ROUTE" in value):
        raise ValueError("invalid section contract")
    return value


def _commission_templates(routes: object, order: list[str]) -> str:
    if (not isinstance(routes, dict) or len(routes) > 32
            or any(not isinstance(name, str) or not re.fullmatch(
                r"[a-z][a-z0-9_-]{0,48}", name) for name in routes)):
        raise ValueError("invalid route contract")
    blocks = []
    for route in order:
        if route not in routes:
            continue
        spec = routes[route]
        if not isinstance(spec, dict):
            raise ValueError("invalid route contract")
        if spec.get("main_loop_only"):
            continue
        if any(not isinstance(spec.get(field), str) or not re.fullmatch(
                r"[A-Za-z0-9._-]{1,96}", spec[field]) for field in ("agent", "model")):
            raise ValueError("invalid display identity")
        sections = _section_labels(spec.get("required_prompt_sections"))
        returns = _section_labels(spec.get("required_return_sections"))
        if not sections or (returns and "RETURN" not in sections):
            raise ValueError("incomplete section contract")
        lines = ["ROUTE: " + route]
        for label in sections:
            value = " / ".join(returns) if label == "RETURN" and returns else "<" + label + ">"
            lines.extend([label + ":", value])
        blocks.append("COMMISSION TEMPLATE " + route + "\n```text\n"
                      + "\n".join(lines) + "\n```")
    text = "\n\n".join(blocks)
    if not text or len(text.encode("utf-8")) > 8192:
        raise ValueError("template context unavailable or oversized")
    return ("Commission templates are formatting only, not admission or launch authority. "
            "Copy only ONE block; replace every <SECTION> with task-specific content. "
            "Keep the exact SECTION: labels. Orchestration still requires its existing "
            "explicit-model and skill/audit gates.\n\n" + text)


def main() -> None:
    mode = os.environ.get("MASTERMIND_NATIVE_DELEGATION_MODE")
    if mode is not None:
        if mode not in {"router_only", "native_leaf"}:
            print("FABLE HARNESS INVALID: native delegation is refused. Repair the "
                  "launch profile; never fall back to an unprofiled session.")
            return
        # Reuse the existing guard's source check; context is not another policy owner.
        try:
            guard_path = Path(__file__).with_name("model_routing_guard.py")
            spec = importlib.util.spec_from_file_location("_native_routing_guard", guard_path)
            guard = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(guard)
            payload = guard._read_profile_payload()
            binding_error = guard.verify_native_source_binding(payload, mode)
        except Exception:
            binding_error = "HARNESS_BINDING_INVALID"
        if binding_error:
            print("FABLE HARNESS INVALID: source/workspace binding is not current. "
                  "Do not delegate or fall back. Recompile through the source owner.")
            return
        print(
            "FABLE HARNESS / " + mode.upper() + ": This profile narrows older "
            "FABLE-WHY examples; a prompt never grants budget or launch authority. "
            "Keep the native main-session tools within existing permissions. "
            "Choose the objective, work class, scope and acceptance; the existing "
            "Executive OS/Capacity router owns model, account and admission. "
            "Independent subproject leaders are governed child Jobs sharing the "
            "root envelope, not native Fable clones. Do not start provider CLIs "
            "from Bash or use teams/workflows to bypass admission. "
            "A missing router, quota observation or binding is UNKNOWN/BLOCKED, "
            "not free capacity. Do not create another queue or quota ledger. "
            "Load only granted, source-pinned skills/tools. Receive material "
            "returns through the existing event/dialogue path; do not poll with "
            "Fable. No live provider capacity or installed adoption is implied."
        )
        print("STRICT PROFILE SKILLS: model-invoked Skill is disabled until resolved skill "
          "definitions, fork/model overrides and injected commands are qualified. "
          "Read approved procedure files as reference context; do not execute embedded "
          "commands automatically. Native skills remain a required later fidelity gate, "
          "not a capability this candidate claims. Native SendMessage is also disabled "
          "because it can resume a stopped agent without an Agent launch.")
        if mode == "router_only":
            print("Native Agent/Task/Workflow/TeamCreate/SendMessage/Skill are disabled. There is no "
                  "native fallback when the router is unavailable.")
            return
        print("Native-leaf candidate only: ROUTE: census, subagent_type scout, "
              "explicit model sonnet, read-only Read/Grep/Glob tools, at most "
              "14 turns per invocation. No native resume, fork, Fable, teams "
              "or descendants. The concurrency hint is NOT enforced under "
              "ultracode and is NOT a lifetime, subtree or account budget. "
              "Use this mode only for a separately qualified bounded canary.")

    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    path = project / ".claude" / "agent-routing.json"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
        routes = registry["routes"]
        order = list(routes)  # The registry is the only route catalog.
        templates = _commission_templates(routes, ["census"] if mode == "native_leaf" else order)
    except (OSError, ValueError, TypeError, KeyError):
        print("COMMISSION_TEMPLATES_UNAVAILABLE: routing contract is unreadable or invalid; "
              "do not infer a launch. Restore the qualified source bundle.")
        return

    if mode == "native_leaf":
        spec = registry.get("routes", {}).get("census", {})
        print("Census commission fields: " + "/".join(spec.get("required_prompt_sections", []))
              + ". RETURN: STATUS/RESULT/EVIDENCE/GAPS/DEVIATIONS. "
              "Ask the parent for a governed worker when shell execution or writes are needed.")
        print(templates)
        return

    mappings = []
    contracts = []
    for route in order:
        spec = routes.get(route)
        if not spec:
            continue
        if spec.get("main_loop_only"):
            mappings.append(f"{route}->Fable main loop")
        else:
            mappings.append(f"{route}->{spec.get('agent')}({spec.get('model')})")
        required = spec.get("required_prompt_sections") or []
        if required and route not in {"orchestration"}:
            contracts.append(f"{route}=" + "/".join(required))

    print(
        "AGENT ROUTING CONTROL (hook-enforced direct-spawn amendment): For every direct Agent/Task delegation, "
        "Fable chooses semantic ROUTE, never a model tier. Use the exact custom agent in "
        ".claude/agent-routing.json; generic/general-purpose/Explore/Plan/fork are not "
        "routing bypasses. This supersedes older CLAUDE.md examples that name Explore/general-purpose for direct fan-out; the existing model-tier law itself is unchanged. "
        "Model overrides may not change the route's model family. Final judgment stays in Fable. "
        "Exceptional Fable child = ROUTE orchestration + orchestrator + explicit model fable + valid FABLE-WHY; "
        "for easier orchestration the same route may run explicit model opus with a fable-mode skill directive (no FABLE-WHY — no fable spent). "
        "ROUTES: " + "; ".join(mappings) + ". "
        "Commission fields (exact SECTION: labels): " + "; ".join(contracts) + ". "
        "Every normal worker RETURN must request STATUS/RESULT/EVIDENCE/GAPS/DEVIATIONS. "
        "If the spawn guard rejects a call, fix the route/commission; never evade the guard."
    )
    print(templates)


if __name__ == "__main__":
    main()
