"""Exercise an exact installed router build against a closed in-memory transport.

Usage: <router-venv>/python admin/tests/prove_capacity_runtime.py <release-dir>
No production env is loaded, no listening socket opens, and no provider is called.
"""
import asyncio
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

import httpx

TOKEN = "capacity-observer-runtime-fixture-token"


class Chunks(httpx.AsyncByteStream):
    def __init__(self, value):
        self.value = value

    async def __aiter__(self):
        for offset in range(0, len(self.value), 11):
            yield self.value[offset:offset + 11]
            await asyncio.sleep(0)

    async def aclose(self):
        pass


def sse(events, done=False):
    result = b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events)
    return result + (b"data: [DONE]\n\n" if done else b"")


def reply(kind, streaming, usage=True):
    if kind == "anthropic":
        value = {"id": "msg_fixture", "type": "message", "role": "assistant", "model": "model-a",
                 "content": [{"type": "text", "text": "fixture output"}], "stop_reason": "end_turn"}
        if usage:
            value["usage"] = {"input_tokens": 11, "output_tokens": 7}
        if not streaming:
            return json.dumps(value).encode(), "application/json"
        return sse([
            {"type": "message_start", "message": {"usage": {"input_tokens": 11}} if usage else {}},
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "fixture output"}},
            {"type": "message_delta", "usage": {"output_tokens": 7}} if usage else {"type": "ping"},
            {"type": "message_stop"}]), "text/event-stream"
    if kind == "openai":
        if not streaming:
            value = {"id": "msg_fixture", "choices": [{"message": {"role": "assistant", "content": "fixture output"}, "finish_reason": "stop"}]}
            if usage:
                value["usage"] = {"prompt_tokens": 11, "completion_tokens": 7}
            return json.dumps(value).encode(), "application/json"
        events = [{"choices": [{"delta": {"role": "assistant"}}]},
                  {"choices": [{"delta": {"content": "fixture output"}}]},
                  {"choices": [{"delta": {}, "finish_reason": "stop"}]}]
        if usage:
            events.append({"choices": [], "usage": {"prompt_tokens": 11, "completion_tokens": 7}})
        return sse(events, done=True), "text/event-stream"
    value = {"id": "resp_fixture", "status": "completed", "model": "model-a",
             "output": [{"id": "msg_fixture", "type": "message", "role": "assistant",
                         "content": [{"type": "output_text", "text": "fixture output", "annotations": []}]}]}
    if usage:
        value["usage"] = {"input_tokens": 11, "output_tokens": 7}
    return sse([{"type": "response.created", "response": {"id": "resp_fixture"}},
                {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "fixture output"},
                {"type": "response.completed", "response": value}], done=True), "text/event-stream"


async def main(release):
    sys.path.insert(0, str(Path(release).resolve()))
    gateway = importlib.import_module("ops.native_fabric.unified_router.gateway")
    observer = importlib.import_module("ops.native_fabric.unified_router.capacity_fabric_observer")
    routes_module = importlib.import_module("ops.native_fabric.unified_router.routes")
    # Closed credential fixtures exist only in this proof process.
    gateway._route_authorization = lambda *args: "fixture-upstream-token"
    account = SimpleNamespace(id="fixture-account", exhausted=False, access_token="fixture-token", account_id="fixture-account")
    gateway.codex_oauth.read_accounts = lambda *args: [account]
    gateway._oauth_headers = lambda selected: {"authorization": "Bearer fixture-upstream-token"}
    wires = {"anthropic": routes_module.WIRE_ANTHROPIC, "openai": routes_module.WIRE_OPENAI,
             "responses": routes_module.WIRE_RESPONSES}
    checks = []
    for kind, wire in wires.items():
        for streaming in (False, True):
            for with_usage in (False, True):
                body, content_type = reply(kind, streaming, with_usage)

                async def handler(request):
                    assert request.url.host == "fixture.invalid", "unexpected egress target"
                    return httpx.Response(200, headers={"content-type": content_type}, stream=Chunks(body))

                with tempfile.TemporaryDirectory() as directory:
                    route = routes_module.Route(route_id="fixture-" + kind, kind="gateway", base_url="https://fixture.invalid",
                        wire=wire, models=("model-a",), priority=10, gateway_token_env="UNUSED_FIXTURE_TOKEN")
                    cfg = gateway.Settings(proxy_token=TOKEN, state_dir=Path(directory), routes=(route,),
                        auth_store=Path(directory) / "NO_LIVE_AUTH_STORE",
                        aliases=(("fabric/fast", ("model-a",)),), capacity_wait_s=0)
                    request_body = {"model": "fabric/fast", "max_tokens": 24, "stream": streaming,
                                    "messages": [{"role": "user", "content": "fixture input"}]}
                    outputs = []
                    for observed in (False, True):
                        app = gateway.create_app(cfg, transport=httpx.MockTransport(handler))
                        if observed:
                            observer.instrument_app(app, gateway)
                        async with app.router.lifespan_context(app):
                            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)), base_url="http://fixture") as client:
                                response = await client.post("/v1/messages", json=request_body,
                                    headers={"authorization": "Bearer " + TOKEN, "x-fabric-agent-id": "runtime-proof-agent"})
                                outputs.append((response.status_code, response.content, dict(response.headers)))
                    assert outputs[0] == outputs[1], (kind, streaming, with_usage, "wire output changed")
                    assert outputs[1][0] == 200, (kind, streaming, outputs[1][0])
                    snap = app.state.capacity_observer.snapshot(app)
                    record = snap["recent"][0]
                    assert record["state"] == "completed", (kind, streaming, record["state"])
                    assert len(record["attempts"]) == 1, (kind, "duplicate attempts")
                    assert record["requested_model"] == "fabric/fast"
                    assert record["route_id"] == route.route_id
                    assert record["usage"]["output_tokens"] == (7 if with_usage else None), (kind, "output", record["usage"])
                    assert record["usage"]["input_tokens"] == (11 if with_usage else None), (kind, "input", record["usage"])
                    assert record["usage_final"] is with_usage, (kind, "finality")
                    assert record["first_content_at"] is not None
                    assert "fixture input" not in json.dumps(snap) and "fixture output" not in json.dumps(snap)
                    checks.append({"wire": kind, "stream": streaming, "usage_reported": with_usage, "result": "PASS"})
    print(json.dumps({"result": "PASS", "release": str(release), "cases": checks,
                      "proof": "Exact gateway and translators; identical response status, headers and bytes; real provider usage or unknown; no network"}))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
