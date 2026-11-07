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

# The Admin HTTP surface uses its own existing auth/session/CSRF owner. These
# cases exercise that surface plus its real read tool, adapter and gateway.
@pytest.fixture
def authenticated_admin(monkeypatch, tmp_path):
    from collections import deque
    from admin import orchestrator_chat as admin_chat
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("ADMIN_DEPLOYED", "0")
    monkeypatch.setenv("ADMIN_PASSWORD", "synthetic-admin-composition-password")
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "synthetic-admin-composition-session-secret")
    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    monkeypatch.delenv("AI_COSTS_STATE_ROOT", raising=False)
    monkeypatch.setattr(admin_chat, "ROOT", tmp_path)
    monkeypatch.setattr(admin_chat, "_RATE_EVENTS", deque())
    for name in ("_resolve_candidates", "_discover_pool_candidates", "_build_client"):
        monkeypatch.setattr(admin_chat, name, Mock(side_effect=AssertionError("legacy admin inference")))
    health = tmp_path / "data/neuralweb/health.json"
    health.parent.mkdir(parents=True)
    health.write_text(json.dumps({"overall_status": "composition-fixture",
        "as_of": "2026-11-04", "lobes": [], "cortex": {"run_status": "fixture"}}))
    return admin_chat


@contextmanager
def admin_surface(factory=None, *, selected=True):
    from admin import server
    httpd = server._build_server("127.0.0.1", 0, fabric_selected=selected,
                                 fabric_provider_factory=factory)
    httpd.daemon_threads = True
    thread = threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{httpd.server_port}",
                          trust_env=False, timeout=10) as client:
            yield client
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(2)


def admin_factory(url):
    return Mock(side_effect=lambda: {
        "client": FabricInferenceClient(base_url=url, proxy_token=PROXY_TOKEN, model=MODEL),
        "model": MODEL, "provider": "experiential_labs", "cost_basis": "metered",
        "cap_id": "fabric_admin_composition_fixture"})


def admin_login(client):
    from admin import auth
    response = client.post("/api/login", json={"password": "synthetic-admin-composition-password"})
    assert response.status_code == 200 and response.json()["ok"]
    client.headers[auth.CSRF_HEADER] = client.cookies[auth.CSRF_COOKIE]


@pytest.mark.parametrize("second_usage", [False, True])
def test_authenticated_admin_tool_turn_uses_actual_gateway(gateway_module, tmp_path,
                                                         authenticated_admin, second_usage):
    first = packet(tool=True)
    first["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "read_health"
    with owner_gateway(gateway_module, tmp_path, [first, packet(usage=second_usage)]) as (url, calls, wire, asgi):
        factory = admin_factory(url)
        with admin_surface(factory) as client:
            admin_login(client)
            response = client.post("/api/orchestrator/chat", json={
                "message": "Read the service health.", "history": [],
                "fabric_selected": False, "fabric_provider_factory": "forged",
                "request_id": "forged-request"})
            assert response.status_code == 200
            result = response.json()
        snapshot = status(asgi)
    assert not result["degraded"] and result["mode"] == "live"
    assert result["provider"] == "experiential_labs" and result["model"] == MODEL
    assert result["usage_state"] == ("known" if second_usage else "unknown")
    assert result["input_tokens"] == (22 if second_usage else None)
    assert factory.call_count == 1 and len(calls) == len(wire) == 2
    assert snapshot["shared_used_in_window"] == 2 and snapshot["pending"] == 0
    assert all(slot["inflight"] == 0 for slot in snapshot["slots"])
    ids = [call["headers"]["idempotency-key"] for call in calls]
    assert ids == [f"{result['request_id']}:orchestrator:{n}" for n in range(2)]
    assert "forged" not in ids[0]
    tool_result = next(m for m in calls[1]["body"]["messages"] if m["role"] == "tool")
    assert json.loads(tool_result["content"])["overall_status"] == "composition-fixture"
    usage_path = tmp_path / "data/ai_costs/usage.jsonl"
    rows = [json.loads(line) for line in usage_path.read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["provider"] == "experiential_labs"
    assert rows[0]["input_tokens"] == (22 if second_usage else 11)
    if not second_usage:
        assert "partial known usage" in rows[0]["note"]


@pytest.mark.parametrize("failure", [429, httpx.ReadError("synthetic interruption")])
def test_admin_later_gateway_failure_preserves_completed_usage(gateway_module, tmp_path,
                                                               authenticated_admin, failure):
    first = packet(tool=True)
    first["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "read_health"
    with owner_gateway(gateway_module, tmp_path, [first, failure]) as (url, calls, wire, asgi):
        with admin_surface(admin_factory(url)) as client:
            admin_login(client)
            response = client.post("/api/orchestrator/chat", json={"message": "Read service health."})
            result = response.json()
        snapshot = status(asgi)
    assert result["degraded"] and result["reason"] == "fabric_inference_failed"
    assert result["usage_state"] == "unknown" and result["input_tokens"] is None
    assert result["completed_step_usage"]["input_tokens"] == 11
    assert len(calls) == len(wire) == 2 and snapshot["shared_used_in_window"] == 2
    assert all(slot["inflight"] == 0 for slot in snapshot["slots"])
    rows = [json.loads(line) for line in (tmp_path / "data/ai_costs/usage.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["input_tokens"] == 11
    assert "partial known usage" in rows[0]["note"] and "synthetic" not in result["reply"]


@pytest.mark.parametrize("authenticated", [False, True])
def test_admin_auth_and_csrf_refuse_before_gateway(gateway_module, tmp_path,
                                                 authenticated_admin, authenticated):
    with owner_gateway(gateway_module, tmp_path, []) as (url, calls, wire, asgi):
        factory = admin_factory(url)
        with admin_surface(factory) as client:
            if authenticated:
                admin_login(client)
                from admin import auth
                del client.headers[auth.CSRF_HEADER]
            response = client.post("/api/orchestrator/chat", json={"message": "Read service health."})
        snapshot = status(asgi)
    assert response.status_code == (403 if authenticated else 401)
    assert factory.call_count == 0 and calls == wire == []
    assert snapshot["shared_used_in_window"] == 0


def configure_owned_application(monkeypatch, root, url, *, service_mode_id=None):
    """Synthetic qualification; use the real owner, policy and capability broker."""
    import time
    import yaml
    from engine import provider_production_modes as owner

    config = root / "config"
    config.mkdir(exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "config"
    (config / "provider_workloads.v1.json").write_bytes(
        (source / "provider_workloads.v1.json").read_bytes())
    transport = owner._ApplicationFabricTransport(
        url, "TEST_FABRIC_PROXY_TOKEN", "fixture-provider", MODEL, "unknown",
        "fabric:paired-owner", "paired_owner_capability",
        qualified=True, application_allowed=True,
    )
    transport_id, record_id = "paired_fixture_v1", "shared_fabric"
    lanes = ["brain", "admin-orchestrator"]
    if service_mode_id is not None:
        from dataclasses import replace
        transport_id, lane = {
            "macro_brain_fabric": ("native_go_macro_brain_v1", "brain"),
            "macro_ask_fabric": ("native_go_macro_ask_v1", "ask-brain"),
        }[service_mode_id]
        record_id, lanes = service_mode_id, [lane]
        # This fixture proves startup identity with the historical HTTP owner;
        # native B/A protocol is independently exercised by its paired suite.
        transport = replace(owner._APPLICATION_FABRIC_TRANSPORTS[transport_id],
            base_url=url, provider_id="fixture-provider", model=MODEL, cost_basis="unknown",
            protocol="openai_chat_v1", qualified=True, application_allowed=True)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, transport_id, transport)
    document = json.loads((source / "provider_production_modes.v1.json").read_text())
    row = {key: getattr(transport, key) for key in owner._APPLICATION_IDENTITY_FIELDS}
    row.update(transport_id=transport_id, enabled=True, application_allowed=True,
               qualification=owner.PROFILE_QUALIFIED_CANARY,
               qualification_ref="fixture:paired-source-only", qualified_until=time.time()+3600)
    document["application_fabric_modes"] = {record_id: row}
    (config / "provider_production_modes.v1.json").write_text(json.dumps(document))
    manifest = {"capabilities": [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active", "allowed_lanes": lanes}]}
    path = config / "capability_manifest.yml"
    path.write_text(yaml.safe_dump(manifest))
    monkeypatch.setenv(transport.secret_ref, PROXY_TOKEN)
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "shared_fabric")
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_interactive")
    return path, manifest


def test_admin_startup_owner_reaches_gateway_and_observes_revocation(
        gateway_module, tmp_path, authenticated_admin, monkeypatch):
    import yaml
    from admin import paths

    first = packet(tool=True)
    first["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "read_health"
    with owner_gateway(gateway_module, tmp_path, [first, packet()]) as (url, calls, wire, asgi):
        path, manifest = configure_owned_application(monkeypatch, tmp_path, url)
        monkeypatch.setattr(paths, "ROOT", tmp_path)
        # Use real startup selection; even an explicit false cannot weaken it.
        with admin_surface(selected=False) as client:
            admin_login(client)
            result = client.post("/api/orchestrator/chat", json={
                "message": "Read service health.", "fabric_selected": False,
                "fabric_provider_factory": "forged", "workload_profile": "development_agent"}).json()
            assert not result["degraded"] and result["provider"] == "fixture-provider"
            assert result["model"] == MODEL and result["input_tokens"] == 22
            manifest["capabilities"][0]["kill_state"] = "killed"
            path.write_text(yaml.safe_dump(manifest))
            refused = client.post("/api/orchestrator/chat", json={"message": "Read again."}).json()
            assert refused["degraded"]
        snapshot = status(asgi)
    assert len(calls) == len(wire) == 2 and snapshot["shared_used_in_window"] == 2
    rows = [json.loads(line) for line in (tmp_path / "data/ai_costs/usage.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["provider"] == "fixture-provider"


@pytest.mark.parametrize("streaming", [False, True])
def test_public_http_startup_owner_composes_real_brain_and_gateway(
        gateway_module, tmp_path, public_brain, monkeypatch, streaming):
    import app.main as main

    costs, tokens, tool, _ = public_brain
    monkeypatch.setattr(main, "REPO", tmp_path)
    monkeypatch.setattr(main, "_brain_track_event", lambda *a: None)
    monkeypatch.setattr(main, "_brain_throttle_check", lambda *a: None)
    # Save/restorable server state before running the actual startup compositor.
    monkeypatch.setattr(main.app.state, "fabric_selected", False, raising=False)
    monkeypatch.setattr(main.app.state, "fabric_provider_factory", None, raising=False)
    monkeypatch.setattr(main.app.state, "ask_fabric_selected", False, raising=False)
    monkeypatch.setattr(main.app.state, "ask_fabric_provider_factory", None, raising=False)
    user = {"id": "owner-http-" + str(streaming), "email": "", "user_metadata": {}}
    main.app.dependency_overrides[main._brain_user_or_guest] = lambda: user
    try:
        with owner_gateway(gateway_module, tmp_path, [packet(tool=True), packet()]) as (url, calls, wire, asgi):
            configure_owned_application(monkeypatch, tmp_path, url, service_mode_id="macro_brain_fabric")
            main._configure_brain_fabric()
            with TestClient(main.app) as client:
                route = "/api/brain/stream" if streaming else "/api/brain/chat"
                response = client.post(route, json={"message": "Explain the market context.",
                    "lane": "pro", "fabric_selected": False, "fabric_provider_factory": "forged"})
                assert response.status_code == 200, response.text
                if streaming:
                    events = [json.loads(x[6:]) for x in response.text.splitlines() if x.startswith("data: ")]
                    result = next(e for e in reversed(events) if e["type"] == "done")
                    run_id = next(e["run_id"] for e in events if e["type"] == "run")
                    assert client.get(f"/api/brain/runs/{run_id}").status_code == 200
                else:
                    result = response.json()
                assert not result.get("degraded")
            snapshot = status(asgi)
        assert len(calls) == len(wire) == 2 and tool.call_count == 1
        assert snapshot["shared_used_in_window"] == 2 and snapshot["pending"] == 0
        assert len(costs) == 1 and costs[0]["provider"] == "fixture-provider"
        assert costs[0]["input_tokens"] == 22
    finally:
        main.app.dependency_overrides.pop(main._brain_user_or_guest, None)


def test_shared_news_and_cached_auditor_reach_real_owner_gateway(gateway_module, tmp_path, monkeypatch):
    import yaml
    from engine import llm_auth, news_llm
    from engine.marketing import copy_auditor

    news_reply = packet()
    news_reply["choices"][0]["message"]["content"] = json.dumps([
        {"i": 0, "summary": "Measured observation.", "importance": 60, "tone": "neutral"}])
    audit_reply = packet()
    audit_reply["choices"][0]["message"]["content"] = json.dumps({
        "verdicts": [{"n": 1, "verdict": "keep", "codes": [], "note": "Supported."}]})
    costs = []
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: None)
    monkeypatch.setattr("lib.config.secret", Mock(side_effect=AssertionError("legacy credentials")))
    monkeypatch.setattr(news_llm, "_cfg", lambda: {"enabled": True})
    monkeypatch.setattr(news_llm, "_classify_model", lambda: "legacy-model")
    monkeypatch.setattr(copy_auditor, "_PROVIDER_CACHE", {})
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    with owner_gateway(gateway_module, tmp_path, [news_reply, audit_reply, audit_reply]) as (url, calls, wire, asgi):
        path, manifest = configure_owned_application(monkeypatch, tmp_path, url)
        manifest["capabilities"][0]["allowed_lanes"] += ["news-llm", "marketing-auditor"]
        path.write_text(yaml.safe_dump(manifest))
        monkeypatch.setattr(llm_auth, "_repo_root", lambda: tmp_path)
        headlines = news_llm.annotate([{"title": "Measured news"}])
        assert headlines[0]["summary"] == "Measured observation."
        posts = [{"text": "Measured observation."}]
        assert copy_auditor.audit_batch(posts)["ok"]
        assert copy_auditor.audit_batch(posts)["ok"]
        assert len(copy_auditor._PROVIDER_CACHE) == 1
        snapshot = status(asgi)
    assert len(calls) == len(wire) == len(costs) == 3
    assert len({call["headers"]["idempotency-key"] for call in calls}) == 3
    assert all(row["provider"] == "fixture-provider" and row["model"] == MODEL for row in costs)
    assert snapshot["shared_used_in_window"] == 3 and snapshot["pending"] == 0


@pytest.mark.parametrize("rewrite_fails", [False, True])
def test_ai_brief_intentional_rewrite_uses_real_owner_gateway(gateway_module, tmp_path, monkeypatch, rewrite_fails):
    import yaml
    from engine import master_brain, provider_production_modes as owner

    draft = packet()
    draft["choices"][0]["message"]["content"] = json.dumps({"summary": "neural_web conditions."})
    final = packet()
    final["choices"][0]["message"]["content"] = json.dumps({"summary": "Measured conditions."})
    costs = []
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: None)
    monkeypatch.setattr(master_brain, "_client", Mock(side_effect=AssertionError("legacy client")))
    monkeypatch.setattr(master_brain, "_is_deepseek_lane", Mock(side_effect=AssertionError("legacy route")))
    plans = [draft, httpx.ReadError("synthetic interrupted rewrite") if rewrite_fails else final]
    with owner_gateway(gateway_module, tmp_path, plans) as (url, calls, wire, asgi):
        path, manifest = configure_owned_application(monkeypatch, tmp_path, url)
        manifest["capabilities"][0]["allowed_lanes"].append("master-brain")
        path.write_text(yaml.safe_dump(manifest))
        monkeypatch.setattr(owner, "__file__", str(tmp_path / "engine/provider_production_modes.py"))
        brief = master_brain.synthesize({"macro": {"date": "2026-11-04"}},
            cfg={"max_tokens": 1000, "emit_theses": False}, root=tmp_path)
        snapshot = status(asgi)
    assert brief["served_by"] == "fixture-provider" and brief["model"] == MODEL
    assert brief["summary"] == ("neural_web conditions." if rewrite_fails else "Measured conditions.")
    assert bool(brief["degraded_reason"]) is rewrite_fails
    assert len(calls) == len(wire) == 2 and len(costs) == (1 if rewrite_fails else 2)
    ids = [call["headers"]["idempotency-key"] for call in calls]
    assert ids[0].endswith(":brain:0") and ids[1].endswith(":brain:1")
    assert ids[0].rsplit(":", 1)[0] == ids[1].rsplit(":", 1)[0]
    assert snapshot["shared_used_in_window"] == 2
