"""Wire tests against ephemeral loopback only: no real gateway/pool credentials."""
from __future__ import annotations

import copy
import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from engine.fabric_inference_client import FabricInferenceClient, FabricInferenceError

MODEL = "fabric-fixture-model"
TOKEN = "synthetic-loopback-token-00000000"


def completion(*, text="Market context.", tools=None, usage=True, model=MODEL, finish=None):
    return {"model": model, "choices": [{"index": 0, "finish_reason": finish or ("tool_calls" if tools else "stop"),
        "message": {"role": "assistant", "content": text, "tool_calls": tools}}],
        "usage": {"prompt_tokens": 13, "completion_tokens": 7} if usage else None}


def tool(identifier="read-1", arguments='{"symbol":"AAPL"}'):
    return {"id": identifier, "type": "function", "function": {"name": "read", "arguments": arguments}}


def chunk(content=None, *, tools=None, finish=None, usage=None, model=MODEL):
    delta = {}
    if content is not None:
        delta["content"] = content
    if tools is not None:
        delta["tool_calls"] = tools
    return {"model": model, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}], "usage": usage}


def sse(value):
    data = json.dumps(value, ensure_ascii=False).encode() if not isinstance(value, bytes) else value
    return b"data: " + data + b"\r\n\r\n"


@contextmanager
def server(*plans):
    calls, scripts = [], list(plans)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            calls.append({"path": self.path, "headers": dict(self.headers), "body": json.loads(body)})
            plan = scripts.pop(0) if scripts else {"status": 500, "body": b"unexpected request"}
            try:
                if callable(plan):
                    plan(self)
                    return
                if plan.get("disconnect"):
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.close_connection = True
                    return
                data = plan.get("body")
                if data is None:
                    data = json.dumps(plan.get("json", completion()), ensure_ascii=False).encode()
                self.send_response(plan.get("status", 200))
                self.send_header("Content-Type", plan.get("content_type", "application/json"))
                self.send_header("Content-Length", str(plan.get("declared_length", len(data))))
                self.send_header("Connection", "close")
                for name, value in plan.get("headers", {}).items():
                    self.send_header(name, value)
                self.end_headers()
                size = plan.get("fragment", len(data) or 1)
                for start in range(0, len(data), size):
                    self.wfile.write(data[start:start + size])
                    self.wfile.flush()
                self.close_connection = True
            except (BrokenPipeError, ConnectionResetError, OSError):
                self.close_connection = True

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/v1", calls
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(2)


def client(url, **kwargs):
    return FabricInferenceClient(base_url=url, proxy_token=TOKEN, model=MODEL, **kwargs)


def request(**changes):
    result = {"model": MODEL, "system": "Use supplied facts.",
              "messages": [{"role": "user", "content": "Explain the context."}],
              "max_tokens": 200, "request_id": "turn-1:brain:0"}
    result.update(changes)
    return result


def test_blocking_wire_uses_gateway_path_identity_and_real_usage(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    with server({"json": completion()}) as (url, calls):
        response = client(url).messages.create(**request())
    assert response.model == MODEL and response.stop_reason == "end_turn"
    assert response.content[0].model_dump() == {"type": "text", "text": "Market context."}
    assert (response.usage.input_tokens, response.usage.output_tokens) == (13, 7)
    assert len(calls) == 1 and calls[0]["path"] == "/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer " + TOKEN
    assert calls[0]["headers"]["Idempotency-Key"] == "turn-1:brain:0"
    assert calls[0]["body"]["messages"][0] == {"role": "system", "content": "Use supplied facts."}


def test_tools_round_trip_uses_complete_objects_and_preserves_ids():
    with server({"json": completion(text=None, tools=[tool()])}, {"json": completion()}) as (url, calls):
        c = client(url)
        tools = [{"name": "read", "description": "Read evidence.", "input_schema": {"type": "object"}}]
        first = c.messages.create(**request(tools=tools))
        assert first.content[0].input == {"symbol": "AAPL"}
        history = request()["messages"] + [{"role": "assistant", "content": first.content},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "read-1", "content": '{"price":100}'}]}]
        c.messages.create(**request(messages=history, tools=tools, request_id="turn-1:brain:1"))
    sent = calls[1]["body"]
    assert sent["tools"][0]["function"]["parameters"] == {"type": "object"}
    assert sent["messages"][-2]["tool_calls"][0]["id"] == "read-1"
    assert sent["messages"][-1] == {"role": "tool", "tool_call_id": "read-1", "content": '{"price":100}'}
    assert len(calls) == 2


def test_stream_is_incremental_and_final_message_does_not_issue_a_second_post():
    release = threading.Event()

    def held(handler):
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.wfile.write(sse(chunk("First ")))
        handler.wfile.flush()
        release.wait(2)
        handler.wfile.write(sse(chunk("中文 context.", finish="stop")))
        handler.wfile.write(sse({"model": MODEL, "choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 8}}))
        handler.wfile.write(sse(b"[DONE]"))
        handler.wfile.flush()
        handler.close_connection = True

    try:
        with server(held) as (url, calls):
            with client(url).messages.stream(**request()) as stream:
                iterator = stream.text_stream
                assert next(iterator) == "First "  # terminal bytes have not been released
                assert not release.is_set() and len(calls) == 1
                release.set()
                assert list(iterator) == ["中文 context."]
                final = stream.get_final_message()
            assert stream.get_final_message() is final
            assert final.content[0].text == "First 中文 context."
            assert final.usage.input_tokens == 5 and final.usage.output_tokens == 8
            assert calls[0]["body"]["stream_options"] == {"include_usage": True}
            assert len(calls) == 1
    finally:
        release.set()


def test_fragmented_stream_tool_arguments_wait_for_terminal_validation():
    frames = [chunk(tools=[{"index": 0, "id": "call-1", "type": "function", "function": {"name": "read", "arguments": '{"symbol":'}}]),
              chunk(tools=[{"index": 0, "function": {"arguments": '"台積電"}'}}]),
              chunk(finish="tool_calls")]
    body = b"".join(sse(f) for f in frames) + sse(b"[DONE]")
    with server({"body": body, "content_type": "text/event-stream", "fragment": 3}) as (url, calls):
        with client(url).messages.stream(**request()) as stream:
            assert list(stream.text_stream) == []
            final = stream.get_final_message()
    block = final.content[0]
    assert (block.type, block.id, block.name, block.input) == ("tool_use", "call-1", "read", {"symbol": "台積電"})
    assert final.usage.input_tokens is None and final.usage.output_tokens is None
    assert len(calls) == 1


@pytest.mark.parametrize("status", [301, 401, 403, 409, 429, 500, 502, 503])
def test_http_failures_never_retry_redirect_or_expose_body(status):
    with server({"status": status, "body": ("SECRET " + TOKEN).encode(),
                 "headers": {"Location": "http://example.invalid/steal"}}) as (url, calls):
        with pytest.raises(FabricInferenceError) as exc:
            client(url).messages.create(**request())
    assert exc.value.status_code == status
    assert TOKEN not in str(exc.value) and "SECRET" not in str(exc.value)
    assert len(calls) == 1


def test_unknown_request_latches_original_client_even_with_new_identity():
    with server({"disconnect": True}) as (url, calls):
        c = client(url)
        with pytest.raises(FabricInferenceError) as exc:
            c.messages.create(**request())
        assert exc.value.effect_unknown
        with pytest.raises(FabricInferenceError, match="fabric_effect_unknown"):
            c.messages.create(**request(request_id="not-a-retry"))
        assert len(calls) == 1


def test_successful_identity_cannot_be_dispatched_twice():
    with server({"json": completion()}) as (url, calls):
        c = client(url)
        c.messages.create(**request())
        with pytest.raises(FabricInferenceError, match="fabric_step_unavailable"):
            c.messages.create(**request())
        assert len(calls) == 1


@pytest.mark.parametrize("url", ["http://localhost:1/v1", "http://127.0.0.2:1/v1",
    "http://127.0.0.1/v1", "http://127.0.0.1:0/v1", "http://127.0.0.1:1/v1/",
    "http://token@127.0.0.1:1/v1", "http://127.0.0.1:1/v1?q=x", "http://127.0.0.1:1/v1#x",
    "http://[::1]:1/v1", "http://127.0.0.1:01/v1", "ftp://127.0.0.1:1/v1"])
def test_endpoint_refused_before_network(url):
    with pytest.raises(FabricInferenceError, match="fabric_endpoint_invalid"):
        client(url)


@pytest.mark.parametrize("timeout", [0, -1, True, "60", float("nan"), float("inf"), 901])
def test_timeout_requires_finite_bounded_number(timeout):
    with pytest.raises(FabricInferenceError, match="fabric_timeout_invalid"):
        client("http://127.0.0.1:1/v1", timeout_s=timeout)


@pytest.mark.parametrize("changes", [{"request_id": None}, {"request_id": "bad\nheader"},
    {"model": "another"}, {"max_tokens": 0}, {"max_tokens": True}, {"max_tokens": 32769},
    {"extra_body": {}}, {"temperature": float("nan")},
    {"messages": [{"role": "user", "content": [{"type": "image", "source": {}}]}]},
    {"messages": [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": [], "content": "x"}]}]}])
def test_invalid_request_never_opens_a_connection(changes):
    with server() as (url, calls):
        with pytest.raises(FabricInferenceError) as exc:
            client(url).messages.create(**request(**changes))
        assert not exc.value.effect_unknown and calls == []


@pytest.mark.parametrize("case", ["model", "json", "tool_args", "duplicate", "stop_mismatch", "multiple", "missing_stop"])
def test_invalid_completion_refuses_and_latches(case):
    payload = completion()
    if case == "model":
        payload["model"] = "wrong"
    elif case == "tool_args":
        payload = completion(tools=[tool(arguments='{"broken":')])
    elif case == "duplicate":
        payload = completion(tools=[tool(), tool()])
    elif case == "stop_mismatch":
        payload = completion(tools=[tool()], finish="stop")
    elif case == "multiple":
        payload["choices"].append(copy.deepcopy(payload["choices"][0]))
    elif case == "missing_stop":
        payload["choices"][0]["finish_reason"] = None
    plan = {"json": payload} if case != "json" else {"body": b'{"unfinished":'}
    with server(plan) as (url, calls):
        c = client(url)
        with pytest.raises(FabricInferenceError) as exc:
            c.messages.create(**request())
        assert exc.value.effect_unknown
        with pytest.raises(FabricInferenceError, match="fabric_effect_unknown"):
            c.messages.create(**request(request_id="next-step"))
        assert len(calls) == 1


@pytest.mark.parametrize("body", [sse(chunk("partial")), sse(chunk("partial", finish="stop")),
    sse(chunk("partial")) + sse(b"{broken"), sse(b"[DONE]")])
def test_stream_requires_complete_terminal_and_never_replays(body):
    with server({"body": body, "content_type": "text/event-stream"}) as (url, calls):
        c = client(url)
        with pytest.raises(FabricInferenceError):
            with c.messages.stream(**request()) as stream:
                list(stream.text_stream)
        with pytest.raises(FabricInferenceError, match="fabric_effect_unknown"):
            c.messages.create(**request(request_id="replacement"))
        assert len(calls) == 1


def test_abandoning_stream_closes_connection_without_claiming_cancellation():
    body = sse(chunk("partial")) + sse(chunk("rest", finish="stop")) + sse(b"[DONE]")
    with server({"body": body, "content_type": "text/event-stream"}) as (url, calls):
        c = client(url)
        with c.messages.stream(**request()) as stream:
            assert next(stream.text_stream) == "partial"
        assert stream.exchange.closed
        with pytest.raises(FabricInferenceError, match="fabric_effect_unknown"):
            c.messages.create(**request(request_id="other"))
        assert len(calls) == 1


def test_missing_or_invalid_usage_is_not_reported_as_zero():
    payloads = [completion(usage=False), completion(), completion()]
    payloads[1]["usage"] = {"prompt_tokens": True, "completion_tokens": -1}
    payloads[2]["usage"] = {"prompt_tokens": 0, "completion_tokens": 0}
    with server(*[{"json": p} for p in payloads]) as (url, _):
        c = client(url)
        results = [c.messages.create(**request(request_id=f"step-{i}")) for i in range(3)]
    assert all(r.usage.input_tokens is None and r.usage.output_tokens is None for r in results[:2])
    assert results[2].usage.input_tokens == results[2].usage.output_tokens == 0


def test_bounded_request_refuses_before_dispatch_and_response_limit_latches(monkeypatch):
    import engine.fabric_inference_client as mod
    with server({"body": b"x" * 2048}) as (url, calls):
        c = client(url)
        monkeypatch.setattr(mod, "MAX_REQUEST_BYTES", 1024)
        with pytest.raises(FabricInferenceError, match="fabric_request_too_large"):
            c.messages.create(**request(system="x" * 2048))
        assert calls == []
        monkeypatch.setattr(mod, "MAX_RESPONSE_BYTES", 1024)
        with pytest.raises(FabricInferenceError, match="fabric_response_too_large"):
            c.messages.create(**request())
        assert len(calls) == 1


def test_http_content_length_truncation_is_unknown_even_if_json_prefix_is_valid():
    body = json.dumps(completion()).encode()
    with server({"body": body, "declared_length": len(body) + 10}) as (url, calls):
        with pytest.raises(FabricInferenceError) as exc:
            client(url).messages.create(**request())
    assert exc.value.effect_unknown and len(calls) == 1
