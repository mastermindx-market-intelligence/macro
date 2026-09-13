#!/usr/bin/env python3
"""Explicit native-CLI conformance fixture; never contacts a model provider.

The operator must supply --run, an installed Claude binary, source root, and a
new evidence path. Each case uses a fresh temporary HOME/config/workspace and a
fixed loopback-only Anthropic protocol oracle. This is not an Executive launcher
or proof of real-model cognition, billing, account identity, or production use.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CASES = ("leaf_result", "ten_fable", "router_only", "premium_override", "incomplete_commission", "leaf_turn_limit")
MARKER = "MMX_NATIVE_LEAF_FIXTURE_7114"
ROOT_MARKER = "MMX_NATIVE_PARENT_FIXTURE_7114"
VALUE = "MMX_FIXTURE_VALUE_63c17f"
MAX_REQUEST_BYTES = 2_000_000
MAX_REQUESTS = 24


def census_prompt() -> str:
    return ("ROUTE: census\nMISSION:\nRead the one fixture file and return its exact value. "
            + MARKER + "\nWHY:\nNative protocol and tool-scope qualification only.\n"
            "SCOPE:\nThe supplied fixture.txt file in this disposable workspace.\n"
            "OUT OF SCOPE:\nNo writes, external requests, shell commands or real inference.\n"
            "QUESTIONS:\nWhat exact value is in fixture.txt?\n"
            "NOT DONE UNLESS:\nThe exact value is read using the native Read tool and returned.\n"
            "EVIDENCE REQUIRED:\nThe fixture file path and its exact value.\n"
            "RETURN:\nSTATUS / RESULT / EVIDENCE / GAPS / DEVIATIONS")


def fable_prompt() -> str:
    return ("ROUTE: orchestration\n"
            "FABLE-WHY: orchestration: Fixed fixture of a claimed cross-repository ambiguity.\n"
            "MISSION:\nResolve the specified cross-system architecture tradeoff. " + MARKER + "\n"
            "WHY:\nProtocol fixture, not authority or a real frontier task.\n"
            "SCOPE:\nOnly the fixed test question.\n"
            "OUT OF SCOPE:\nNo actual provider or project work.\n"
            "NOT DONE UNLESS:\nReturn a bounded answer with the explicit tradeoff.\n"
            "RETURN:\nSTATUS / RESULT / EVIDENCE / GAPS / DEVIATIONS")


def text_parts(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(text_parts(item) for item in value)
    if isinstance(value, dict) and value.get("type") in {"text", "tool_result"}:
        return text_parts(value.get("text", value.get("content", "")))
    return ""


def answer(blocks: list[dict], model: str, *, stream: bool) -> tuple[str, bytes]:
    stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
    message = {"id": "msg_fixture", "type": "message", "role": "assistant",
               "model": model, "content": blocks, "stop_reason": stop,
               "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}
    if not stream:
        return "application/json", json.dumps(message).encode()
    events = [{"type": "message_start", "message": {**message, "content": [], "stop_reason": None}}]
    for i, block in enumerate(blocks):
        if block["type"] == "text":
            start = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": block["text"]}
        else:
            start = {**block, "input": {}}
            delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
        events.extend([{"type": "content_block_start", "index": i, "content_block": start},
                       {"type": "content_block_delta", "index": i, "delta": delta},
                       {"type": "content_block_stop", "index": i}])
    events.extend([{"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None},
                    "usage": {"output_tokens": 1}}, {"type": "message_stop"}])
    return "text/event-stream", "".join("event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n" for e in events).encode()


class Oracle:
    """Bounded fixed responses; observes tool consumption, not model quality."""
    def __init__(self, case: str, workspace: Path):
        self.case, self.workspace = case, workspace
        self.records: list[dict] = []
        self.parent_consumed = False
        self.leaf_read = False
        self.started = False

    def respond(self, request: dict) -> list[dict]:
        if len(self.records) >= MAX_REQUESTS:
            raise ValueError("fixture request budget exceeded")
        messages = request.get("messages", [])
        user_text = "\n".join(text_parts(b) for m in messages if m.get("role") == "user"
                              for b in (m.get("content") if isinstance(m.get("content"), list) else [{"type": "text", "text": m.get("content", "")}])
                              if isinstance(b, dict) and b.get("type") == "text")
        leaf = MARKER in user_text
        auxiliary = not leaf and (ROOT_MARKER not in user_text or not request.get("tools"))
        results = [b for m in messages if m.get("role") == "user"
                   for b in (m.get("content") if isinstance(m.get("content"), list) else [])
                   if isinstance(b, dict) and b.get("type") == "tool_result"]
        self.records.append({"role": "auxiliary" if auxiliary else "leaf" if leaf else "parent", "model": request.get("model"),
                             "tools": [t.get("name") for t in request.get("tools", [])],
                             "tool_result_ids": [b.get("tool_use_id") for b in results],
                             "tool_results": len(results), "error_results": sum(bool(b.get("is_error")) for b in results),
                             "denial_codes": sorted({code for b in results for code in (
                                 "NATIVE_MODEL_PIN_REQUIRED", "NATIVE_LEAF_ONLY", "ROUTER_REQUIRED",
                                 "HARNESS_INPUT_INVALID", "Blocked ROUTE census", "InputValidationError",
                                 "No such tool available", "Agent type", "permission") if code in text_parts(b)}),
                             "error_excerpts": [text_parts(b)[:800].replace(str(self.workspace), "<fixture-workspace>")
                                                for b in results if b.get("is_error")]})
        # Native CLI may make a no-tools model probe before the actual task.
        # It cannot consume the one planned Agent emission or count as a parent.
        if auxiliary:
            return [{"type": "text", "text": "FIXTURE_AUXILIARY_OK"}]
        if leaf and self.case == "leaf_turn_limit":
            turn = sum(r["role"] == "leaf" for r in self.records)
            if turn > 14:
                return [{"type": "text", "text": "NATIVE_TURN_LIMIT_NOT_ENFORCED"}]
            return [{"type": "tool_use", "id": "toolu_loop_" + str(turn), "name": "Read",
                     "input": {"file_path": str(self.workspace / "fixture.txt")}}]
        if leaf:
            self.leaf_read = any(b.get("tool_use_id") == "toolu_read" and VALUE in text_parts(b) and not b.get("is_error") for b in results)
            if not results:
                return [{"type": "tool_use", "id": "toolu_read", "name": "Read",
                         "input": {"file_path": str(self.workspace / "fixture.txt")}}]
            return [{"type": "text", "text": "STATUS: PASS\nRESULT: " + VALUE + "\nEVIDENCE: fixture.txt\nGAPS: none\nDEVIATIONS: none" if self.leaf_read else "STATUS: FAIL\nRESULT: fixture read failed"}]
        if not self.started:
            self.started = True
            count = 10 if self.case == "ten_fable" else 1
            return [{"type": "tool_use", "id": "toolu_agent_" + str(i), "name": "Agent",
                     "input": {"description": "Bounded native fixture", "prompt": (fable_prompt() if count == 10 else
                                          "ROUTE: census\nMISSION: Read the fixture and return its contents."
                                          if self.case == "incomplete_commission" else census_prompt()),
                               "subagent_type": "orchestrator" if count == 10 else "scout",
                               "model": "fable" if count == 10 else "opus" if self.case == "premium_override" else "sonnet"}} for i in range(count)]
        self.parent_consumed = any(b.get("tool_use_id") == "toolu_agent_0" and VALUE in text_parts(b) and not b.get("is_error") for b in results)
        return [{"type": "text", "text": "NATIVE_FIXTURE_FINISHED"}]


def handler_for(oracle: Oracle):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_REQUEST_BYTES:
                self.send_error(413)
                return
            request = json.loads(self.rfile.read(size))
            if self.path.split("?")[0] == "/v1/messages/count_tokens":
                kind, body = "application/json", b'{"input_tokens":100}'
            elif self.path.split("?")[0] == "/v1/messages":
                kind, body = answer(oracle.respond(request), request.get("model", "fixture"), stream=request.get("stream", False))
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Handler


def profile_digest(profile: dict) -> str:
    return hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def isolated_environment(home: Path, workspace: Path, port: int, fragment: dict) -> dict:
    # Deliberately not os.environ.copy(): no inherited provider, proxy, OAuth or
    # process-injection secrets. The dummy key is valid only for this fake server.
    return {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(home),
            "TMPDIR": str(home), "CLAUDE_CONFIG_DIR": str(home / ".claude"),
            "CLAUDE_PROJECT_DIR": str(workspace), "ANTHROPIC_API_KEY": "fixture-not-a-real-key",
            "ANTHROPIC_BASE_URL": "http://127.0.0.1:" + str(port),
            "DISABLE_NONESSENTIAL_TRAFFIC": "1", "DISABLE_TELEMETRY": "1",
            "DISABLE_ERROR_REPORTING": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
            "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1", **fragment["env"]}


def run_case(binary: Path, root: Path, profile: dict, case: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="mmx-native-7114-") as tmp:
        home = Path(tmp) / "home"
        workspace = Path(tmp) / "workspace"
        home.mkdir(); workspace.mkdir()
        for relative in (".claude/hooks/model_routing_guard.py", ".claude/hooks/agent_routing_context.py",
                         ".claude/agent-routing.json", ".claude/agents/scout.md"):
            path = workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, path)
        (workspace / "fixture.txt").write_text(VALUE + "\n")
        # Use the compiler's actual argv without injecting missing hooks in the
        # fixture. The isolated workspace deliberately has no settings.json, so
        # ambient configuration cannot conceal a missing profile consumer.
        oracle = Oracle(case, workspace)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(oracle))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        args = [str(binary), "--setting-sources", "", *profile["cli_arguments"],
                "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                "--tools", "Read,Grep,Glob,Agent", "--allowedTools", "Read,Grep,Glob,Agent",
                "--no-session-persistence", "--model", "sonnet", "--effort", "medium",
                "--max-turns", "20" if case == "leaf_turn_limit" else "6", "--output-format", "json"]
        args += ["-p", ROOT_MARKER + " Run the fixed native conformance task. This is a deterministic local protocol fixture, not real model inference."]
        env = isolated_environment(home, workspace, server.server_port, profile["settings_fragment"])
        timed_out = False
        try:
            proc = subprocess.Popen(args, cwd=workspace, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            try:
                out, err = proc.communicate(timeout=45)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    out, err = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    out, err = proc.communicate(timeout=5)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=3)
        native = json.loads(out) if out.lstrip().startswith(b"{") else {}
        stats = {key: native.get("subagent_stats", {}).get(key) for key in
                 ("spawned", "completed", "failed", "max_depth", "spawned_by_subagents")}
        leaf = [r for r in oracle.records if r["role"] == "leaf"]
        parents = [r for r in oracle.records if r["role"] == "parent"]
        passed = proc.returncode == 0 and not timed_out and bool(oracle.records)
        if case == "leaf_result":
            passed = passed and oracle.leaf_read and oracle.parent_consumed and len(leaf) == 2 and stats["spawned"] == 1
            passed = passed and all(not ({"Bash", "Write", "Edit", "Agent", "Skill", "Workflow"} & set(r["tools"])) for r in leaf)
        elif case == "leaf_turn_limit":
            passed = (passed and 1 <= len(leaf) <= 14 and stats["spawned"] == 1
                      and len(parents) == 2 and parents[-1]["tool_result_ids"] == ["toolu_agent_0"]
                      and stats["completed"] + stats["failed"] == 1)
        else:
            expected_errors = 10 if case == "ten_fable" else 1
            passed = (passed and not leaf and stats["spawned"] == 0 and len(parents) == 2
                      and parents[-1]["error_results"] == expected_errors
                      and parents[-1]["tool_results"] == expected_errors
                      and set(parents[-1]["tool_result_ids"]) == {"toolu_agent_" + str(i) for i in range(expected_errors)})
        if case == "premium_override":
            passed = passed and "NATIVE_MODEL_PIN_REQUIRED" in parents[-1]["denial_codes"]
        if case == "incomplete_commission":
            passed = passed and "Blocked ROUTE census" in parents[-1]["denial_codes"]
        passed = passed and b"NATIVE_FIXTURE_FINISHED" in out
        diagnostic = (out + b"\n" + err).decode("utf-8", errors="replace")[:2000]
        diagnostic = diagnostic.replace(str(home), "<fixture-home>").replace(str(workspace), "<fixture-workspace>")
        return {"case": case, "passed": bool(passed), "native_subagent_stats": stats,
                "compiled_profile_sha256": profile_digest(profile), "returncode": proc.returncode,
                "timed_out": timed_out, "requests": oracle.records, "leaf_read_value": oracle.leaf_read,
                "parent_consumed_result": oracle.parent_consumed, "stdout_bytes": len(out),
                "stderr_bytes": len(err), "stdout_sha256": hashlib.sha256(out).hexdigest(),
                "stderr_sha256": hashlib.sha256(err).hexdigest(),
                "completion_marker": b"NATIVE_FIXTURE_FINISHED" in out,
                "failure_diagnostic": diagnostic if not passed else None,
                "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "fixture_hook_projection": False,
                "cli_usage_is_synthetic": True,
                "compiled_hooks_present": bool(profile["settings_fragment"].get("hooks")), "real_model_inference": False,
                "production_adoption": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--case", choices=CASES, action="append")
    args = parser.parse_args()
    if args.evidence.exists():
        parser.error("evidence already exists; reconcile the previous run instead of overwriting")
    binary, root = args.binary.resolve(strict=True), args.source_root.resolve(strict=True)
    version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    spec = importlib.util.spec_from_file_location("native_profile", root / "scripts/fable_harness_profile.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    profiles = {mode: module.compile_profile(root, mode, version) for mode in module.MODES}
    results = [run_case(binary, root, profiles["router_only" if case == "router_only" else "native_leaf"], case) for case in (args.case or CASES)]
    receipt = {"schema": "mastermind.fable_native_cli_conformance/v1", "cli_version": version,
               "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
               "compiler_sha256": hashlib.sha256((root / "scripts/fable_harness_profile.py").read_bytes()).hexdigest(),
               "source_sha256": profiles["native_leaf"]["source_sha256"], "results": results,
               "passed": all(r["passed"] for r in results), "fixture_only": True,
               "real_model_inference": False, "executive_jobs_created": 0}
    with args.evidence.open("x") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True); handle.write("\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
