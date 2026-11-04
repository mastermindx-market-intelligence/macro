"""Paired, hermetic proof through the actual shared gateway and public Brain.

Set MM_FABRIC_GATEWAY_SOURCE_ROOT to a checkout of the pinned Mastermind source.
The gateway owns real durable admissions; only its external HTTP transport is
replaced. A loopback HTTP bridge feeds its ASGI handler. This bridge buffers
responses, so incremental delivery is proved separately by the adapter wire
suite. This is source composition evidence, not live account qualification.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from engine.fabric_inference_client import FabricInferenceClient
from engine.neuralweb import brain_gateway as brain

SOURCE_ROOT = os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT")
pytestmark = pytest.mark.skipif(not SOURCE_ROOT, reason="paired Mastermind checkout required")
GATEWAY_BLOB = "9404753b3571e6eb6887c414cab0648c00197023"
MODEL = "fabric-composition-model"
PROXY_TOKEN = "synthetic-proxy-token-for-composition"
PROVIDER_KEYS = ("synthetic-provider-key-one", "synthetic-provider-key-two")


@pytest.fixture(scope="module")
def gateway_module():
    path = Path(SOURCE_ROOT) / "ops/native_fabric/experiential_proxy/gateway.py"
    raw = path.read_bytes()
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == GATEWAY_BLOB
    spec = importlib.util.spec_from_file_location("_fabric_owner_gateway_composition", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


class BytesStream(httpx.AsyncByteStream):
    def __init__(self, body):
        self.body = body

    async def __aiter__(self):
        yield self.body


def packet(*, tool=False, usage=True):
    message = {"role": "assistant", "content": "Reading context." if tool else "The grounded market context is available."}
    if tool:
        message["tool_calls"] = [{"id": "read-1", "type": "function", "function": {
            "name": "get_movers", "arguments": "{}"}}]
    return {"model": MODEL, "choices": [{"index": 0, "message": message,
            "finish_reason": "tool_calls" if tool else "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7} if usage else None}


def streamed(result):
    message = result["choices"][0]["message"]
    delta = {"content": message["content"]}
    if message.get("tool_calls"):
        delta["tool_calls"] = [{"index": i, **item} for i, item in enumerate(message["tool_calls"])]
    frames = [{"model": MODEL, "choices": [{"index": 0, "delta": delta,
        "finish_reason": result["choices"][0]["finish_reason"]}], "usage": None}]
    if result["usage"] is not None:
        frames.append({"model": MODEL, "choices": [], "usage": result["usage"]})
    return b"".join(b"data: " + json.dumps(frame).encode() + b"\n\n" for frame in frames) + b"data: [DONE]\n\n"


@contextmanager
def owner_gateway(module, tmp_path, plans):
    calls, wire_calls, remaining = [], [], list(plans)

    async def upstream(request):
        body = json.loads(request.content)
        calls.append({"url": str(request.url), "headers": dict(request.headers), "body": body})
        assert remaining, "unexpected additional provider inference"
        plan = remaining.pop(0)
        if isinstance(plan, Exception):
            raise plan
        if isinstance(plan, int):
            return httpx.Response(plan, stream=BytesStream(b'{"error":"synthetic refusal"}'),
                                  headers={"content-type": "application/json"})
        streaming = body.get("stream") is True
        data = streamed(plan) if streaming else json.dumps(plan).encode()
        return httpx.Response(200, stream=BytesStream(data), headers={
            "content-type": "text/event-stream" if streaming else "application/json"})

    app = module.create_app(module.Settings(api_keys=PROVIDER_KEYS, proxy_token=PROXY_TOKEN,
        state_dir=tmp_path / "gateway-state", safe_rpm_shared=20),
        transport=httpx.MockTransport(upstream))
    with TestClient(app, client=("127.0.0.1", 44111)) as asgi:
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                wire_calls.append(self.path)
                response = asgi.post(self.path, content=body, headers=dict(self.headers), follow_redirects=False)
                self.send_response(response.status_code)
                self.send_header("Content-Type", response.headers.get("content-type", "application/json"))
                self.send_header("Content-Length", str(len(response.content)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(response.content)
                self.close_connection = True

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        httpd.daemon_threads = True
        thread = threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_port}/v1", calls, wire_calls, asgi
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(2)


@pytest.fixture
def public_brain(monkeypatch, tmp_path):
    costs, tokens = [], []
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr(brain, "_record_token_usage", lambda *args: tokens.append(args))
    monkeypatch.setattr(brain, "_log_brain_response", lambda **kw: None)
    monkeypatch.setattr(brain, "_load_brain_config", lambda *a: {"lanes": {"pro": {"tool_budget": 1}}})
    monkeypatch.setattr(brain, "_resolve_tier", lambda *a: {"tier": "pro", "status": "active"})
    monkeypatch.setattr(brain, "_check_and_increment_quota", lambda *a, **k: (True, {"remaining": 9}))
    monkeypatch.setattr(brain, "_ensure_thread", lambda *a, **k: None)
    monkeypatch.setattr(brain._native_facts, "plan_native_facts", lambda *a, **k: None)
    monkeypatch.setattr(brain, "_all_brain_tool_schemas", lambda *a, **k: [{
        "name": "get_movers", "description": "Read local context.",
        "input_schema": {"type": "object", "properties": {}}}])
    tool = Mock(return_value={"items": [], "is_context_only": True})
    monkeypatch.setattr(brain, "_dispatch_brain_tool", tool)
    monkeypatch.setattr(brain, "_instant_answer", Mock(side_effect=AssertionError("legacy inference")))
    monkeypatch.setattr("engine.llm_auth._oauth_pool_candidates", Mock(side_effect=AssertionError("native credential discovery")))
    return costs, tokens, tool, dict(message="Explain the market context.", user_id="composition-user",
        lane="pro", root=tmp_path, context={"request_id": "forged"}, fabric_selected=True)


def invoke(url, kwargs, streaming, *, token=PROXY_TOKEN):
    def factory():
        return {"client": FabricInferenceClient(base_url=url, proxy_token=token, model=MODEL),
                "model": MODEL, "provider": "experiential_labs", "cost_basis": "metered",
                "cap_id": "fabric_composition_fixture"}

    if streaming:
        events = [json.loads(line[6:]) for line in brain.chat_stream(
            **kwargs, fabric_provider_factory=factory) if line.startswith("data: ")]
        assert events[-1]["type"] == "done"
        return events[-1], "".join(event.get("text", "") for event in events if event["type"] == "delta")
    result = brain.chat(**kwargs, fabric_provider_factory=factory)
    return result, result["reply"]


def status(asgi):
    result = asgi.get("/statusz", headers={"Authorization": "Bearer " + PROXY_TOKEN})
    assert result.status_code == 200
    return result.json()


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("second_usage", [False, True])
def test_public_brain_tool_turn_uses_actual_gateway_admissions(gateway_module, tmp_path, public_brain,
                                                            streaming, second_usage):
    costs, tokens, tool, kwargs = public_brain
    with owner_gateway(gateway_module, tmp_path, [packet(tool=True), packet(usage=second_usage)]) as (url, calls, wire, asgi):
        result, answer = invoke(url, kwargs, streaming)
        snapshot = status(asgi)
    assert not result.get("degraded") and "grounded market context" in answer
    assert len(calls) == len(wire) == 2 and tool.call_count == 1
    assert snapshot["shared_used_in_window"] == 2 and snapshot["pending"] == 0
    assert all(slot["inflight"] == 0 for slot in snapshot["slots"])
    ids = [call["headers"]["idempotency-key"] for call in calls]
    assert ids[0].endswith(":brain:0") and ids[1].endswith(":brain:1")
    assert ids[0].rsplit(":", 1)[0] == ids[1].rsplit(":", 1)[0] and "forged" not in ids[0]
    assert all(call["url"] == gateway_module.UPSTREAM + "/chat/completions" for call in calls)
    assert [call["headers"]["authorization"] for call in calls] == ["Bearer " + key for key in PROVIDER_KEYS]
    assert all(call["body"]["model"] == MODEL for call in calls)
    assert calls[1]["body"]["messages"][-2]["role"] == "tool"
    assert len(costs) == 1 and costs[0]["provider"] == "experiential_labs"
    assert costs[0]["input_tokens"] == (22 if second_usage else 11)
    assert costs[0]["output_tokens"] == (14 if second_usage else 7)
    if not streaming:
        assert result["usage"]["usage_state"] == ("known" if second_usage else "unknown")
        assert result["usage"]["input_tokens"] == (22 if second_usage else None)


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("failure", [429, 502, httpx.ReadError("synthetic transport interruption")])
def test_actual_gateway_failure_never_replays_or_rotates(gateway_module, tmp_path, public_brain, streaming, failure):
    costs, tokens, tool, kwargs = public_brain
    with owner_gateway(gateway_module, tmp_path, [failure]) as (url, calls, wire, asgi):
        result, answer = invoke(url, kwargs, streaming)
        snapshot = status(asgi)
    assert result.get("degraded") and len(calls) == len(wire) == 1
    assert snapshot["shared_used_in_window"] == 1 and all(slot["inflight"] == 0 for slot in snapshot["slots"])
    assert tool.call_count == 0 and not costs
    assert "synthetic" not in answer


def test_gateway_auth_refusal_does_not_reserve_or_contact_upstream(gateway_module, tmp_path, public_brain):
    costs, tokens, tool, kwargs = public_brain
    with owner_gateway(gateway_module, tmp_path, []) as (url, calls, wire, asgi):
        result, _ = invoke(url, kwargs, False, token="different-synthetic-proxy-token-000")
        snapshot = status(asgi)
    assert result["degraded"] and len(wire) == 1 and calls == []
    assert snapshot["shared_used_in_window"] == 0 and not costs and tool.call_count == 0
