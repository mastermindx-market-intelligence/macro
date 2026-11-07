"""Public Brain buffering/cleanup through the real native application service.

Reuses the existing paired A/B HTTP/SQLite fixture and public Brain fixture.
Only provider responses, business data and persistence destinations are synthetic.
"""
from __future__ import annotations

import json
import importlib
import os
import threading
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import llm_auth as auth, provider_production_modes as owner
from engine.neuralweb import brain_gateway as brain
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401
from tests.test_fabric_gateway_composition import public_brain  # noqa: F401


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")


def packet(text="Grounded final response.", *, tool=False, model=MODEL):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "read-1", "type": "function", "function": {
            "name": "get_movers", "arguments": "{}"}}]
    return {"model": model, "choices": [{"index": 0, "message": message,
        "finish_reason": "tool_calls" if tool else "stop"}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


def event(line):
    return json.loads(line[6:]) if line.startswith("data: ") else {}


@pytest.fixture
def turn(selected, public_brain, monkeypatch, request):
    costs, tokens, tool, kwargs = public_brain
    writes, logs, providers, closes = [], [], [], []
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_interactive")
    monkeypatch.setattr(brain, "_ensure_thread", lambda *a, **k: "native-thread")
    monkeypatch.setattr(brain, "_append_message", lambda *a, **k: writes.append((a, k)))
    monkeypatch.setattr(brain, "_log_brain_response", lambda **k: logs.append(k))
    monkeypatch.setattr(brain, "_TERMINAL_TOOL_BUDGET_FLOOR", 1)
    monkeypatch.setattr(auth._FabricMessages, "stream", Mock(side_effect=AssertionError("upstream stream")))
    build, close = auth.build_fabric_provider, auth.close_fabric_provider
    def bound(*args, **changes):
        provider = build(*args, **changes)
        providers.append(provider)
        return provider
    def closed(provider):
        closes.append(provider)
        return close(provider)
    monkeypatch.setattr(auth, "build_fabric_provider", bound)
    monkeypatch.setattr(auth, "close_fabric_provider", closed)
    if getattr(request, "param", None) == "local":
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1",
                            replace(selected.transport, cost_basis="local"))
        selected.row["cost_basis"] = "local"
        selected.save()
    factory = owner.make_application_fabric_factory(
        mode_id="shared_fabric", lane="brain", root=selected.root,
        workload_cfg={"provider_order": ["fabric"], "workload_profile": "site_interactive"})
    kwargs.update(root=selected.root, fabric_provider_factory=factory,
                  context={"page": "terminal", "request_id": "untrusted-request"})
    def plans(*responses):
        remaining = list(responses)
        def reply():
            assert remaining, "unexpected replacement provider request"
            status, response = remaining.pop(0)
            selected.native.response_status, selected.native.response = status, response
        selected.native.on_upstream = reply
    return SimpleNamespace(native=selected.native, costs=costs, tokens=tokens, tool=tool,
        kwargs=kwargs, writes=writes, logs=logs, providers=providers, closes=closes, plans=plans)


def assistant_turns(turn):
    return [args[2] for args, _ in turn.writes if args[1] == "assistant"]


@pytest.mark.parametrize("turn", ["local"], indirect=True)
def test_actual_local_completion_preserves_shared_zero_cost_semantics(turn):
    turn.plans((200, packet()))
    result = brain.chat(**turn.kwargs)
    assert not result["degraded"]
    assert len(turn.costs) == 1 and turn.costs[0]["cost_basis"] == "local"
    assert turn.costs[0]["est_cost_usd"] == 0.0
    assert len(turn.closes) == len(turn.native.posts) == 1


@pytest.mark.parametrize("streaming", [False, True])
def test_public_tool_only_and_final_steps_share_one_native_turn_and_close_once(turn, streaming):
    turn.plans((200, packet(None, tool=True)), (200, packet()))
    if streaming:
        events = [event(line) for line in brain.chat_stream(**turn.kwargs)]
        result = events[-1]
        assert "".join(e.get("text", "") for e in events if e.get("type") == "delta") == "Grounded final response."
    else:
        result = brain.chat(**turn.kwargs)
        assert result["reply"] == "Grounded final response."
    assert not result["degraded"]
    assert len(turn.native.posts) == 2 and turn.tool.call_count == 1
    assert all(json.loads(post[1])["stream"] is False for post in turn.native.posts)
    requests = turn.native.rows("application_requests")
    assert len({row["turn_id"] for row in requests}) == 1
    assert [row["request_id"].rsplit(":", 1)[-1] for row in requests] == ["0", "1"]
    assert "untrusted-request" not in requests[0]["turn_id"]
    assert len(turn.native.rows("leases")) == 1
    assert turn.native.rows("leases")[0]["state"] == "released"
    assert len(turn.closes) == len(turn.costs) == len(turn.tokens) == 1
    assert turn.costs[0]["input_tokens"] == 22
    assert assistant_turns(turn) == ["Grounded final response."]


@pytest.mark.parametrize("boundary", ["meta", "tool", "delta", "done"])
def test_producer_close_settles_safe_result_at_each_delivery_boundary(turn, boundary):
    turn.plans(*(((200, packet(None, tool=True)), (200, packet())) if boundary == "tool"
                 else ((200, packet()),)))
    producer = brain.chat_stream(**turn.kwargs)
    try:
        for line in producer:
            if event(line).get("type") == boundary:
                break
        else:
            pytest.fail("requested delivery boundary absent")
    finally:
        producer.close()
    assert len(turn.closes) == 1
    if boundary == "meta":
        assert not turn.native.posts and not turn.native.rows("leases")
        assert not turn.costs and not turn.tokens and not assistant_turns(turn)
    else:
        assert len(turn.native.posts) == len(turn.costs) == len(turn.tokens) == 1
        assert turn.native.rows("leases")[0]["state"] == "released"
        assert turn.costs[0]["input_tokens"] == 11
        assert assistant_turns(turn) == ([] if boundary == "tool" else ["Grounded final response."])
    assert turn.tool.call_count == 0


@pytest.mark.parametrize("failure", ["terminal", "different_model", "unknown_commit"])
def test_failed_synthesis_never_persists_stub_or_tool_narration_and_keeps_usage(turn, monkeypatch, failure):
    turn.plans((200, packet("Earlier tool narration must not become the answer.", tool=True)),
               (503 if failure == "terminal" else 200,
                packet(model="other-model" if failure == "different_model" else MODEL)))
    if failure == "unknown_commit":
        original = turn.native.gateway.complete_application
        def unsettled(dispatch_id, *, terminal_receipt):
            if len(turn.native.posts) == 2:
                raise OSError("fixture interrupted native settlement")
            return original(dispatch_id, terminal_receipt=terminal_receipt)
        monkeypatch.setattr(turn.native.gateway, "complete_application", unsettled)
    events = [event(line) for line in brain.chat_stream(**turn.kwargs)]
    assert events[-1]["degraded"]
    assert not assistant_turns(turn)
    assert all("Earlier tool narration" not in e.get("text", "") for e in events)
    assert len(turn.native.posts) == 2 and turn.tool.call_count == 1
    assert len(turn.closes) == len(turn.tokens) == 1
    assert sum(row["input_tokens"] for row in turn.costs) == 22
    assert [row["model"] for row in turn.costs] == ([MODEL, "other-model"] if failure == "different_model" else [MODEL])
    assert turn.providers[0]["model"] == MODEL
    if failure == "unknown_commit":
        assert events[-1]["usage"]["input_tokens"] is None
        assert events[-1]["usage"]["completed_input_tokens"] == 22
        assert "turn_total_unknown" in turn.costs[0]["note"]
        assert turn.native.rows("application_requests")[-1]["state"] == "unknown"
    assert all(log["answer"] == "" for log in turn.logs)


@pytest.mark.parametrize("streaming", [False, True])
def test_postbind_preloop_exception_closes_pristine_binding(turn, monkeypatch, streaming):
    monkeypatch.setattr(brain, "_image_blocks", Mock(side_effect=RuntimeError("fixture preloop failure")))
    with pytest.raises(RuntimeError, match="preloop failure"):
        list(brain.chat_stream(**turn.kwargs)) if streaming else brain.chat(**turn.kwargs)
    assert len(turn.providers) == len(turn.closes) == 1
    assert not turn.native.posts and not turn.native.rows("leases") and not turn.costs


@pytest.mark.parametrize("streaming", [False, True])
def test_final_usage_writer_exception_cannot_skip_close_or_replay(turn, monkeypatch, streaming):
    turn.plans((200, packet()))
    monkeypatch.setattr(brain, "_record_token_usage", Mock(side_effect=RuntimeError("fixture final writer")))
    with pytest.raises(RuntimeError, match="final writer"):
        list(brain.chat_stream(**turn.kwargs)) if streaming else brain.chat(**turn.kwargs)
    assert len(turn.native.posts) == len(turn.closes) == len(turn.costs) == 1
    assert turn.native.rows("leases")[0]["state"] == "released"


def test_full_response_screen_precedes_any_selected_prose(turn, monkeypatch):
    turn.plans((200, packet("Raw model prose that must not reach the widget.")))
    screens = []
    def screen(text, citations):
        screens.append(text)
        return "Screened final context.", True
    # Native fixture teardown restores sys.modules. Resolve the current lazy
    # import, not a stale attribute retained by the parent package from a prior case.
    monkeypatch.setattr(importlib.import_module("engine.neuralweb.ask_brain"), "_post_filter_advice", screen)
    producer = brain.chat_stream(**turn.kwargs)
    try:
        for line in producer:
            payload = event(line)
            if payload.get("type") == "delta":
                assert screens and payload["text"] == "Screened final context.", (payload, len(turn.native.posts), screens)
                break
    finally:
        producer.close()
    assert assistant_turns(turn) == ["Screened final context."]
    assert len(turn.closes) == len(turn.costs) == 1


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("invalid", ["unoffered", "schema"])
def test_invalid_second_tool_blocks_the_entire_actual_batch(turn, monkeypatch, streaming, invalid):
    response = packet("Invalid batch prose must remain private.", tool=True)
    second = {"id": "read-2", "type": "function", "function": {
        "name": "unoffered_tool" if invalid == "unoffered" else "get_movers",
        "arguments": '{"limit":"not-an-integer"}'}}
    response["choices"][0]["message"]["tool_calls"].append(second)
    monkeypatch.setattr(brain, "_all_brain_tool_schemas", lambda *a, **k: [{
        "name": "get_movers", "description": "Read local context.", "input_schema": {
            "type": "object", "properties": {"limit": {"type": "integer"}}}}])
    turn.plans((200, response))
    if streaming:
        events = [event(line) for line in brain.chat_stream(**turn.kwargs)]
        result = events[-1]
        assert not any(e.get("type") == "tool" or "Invalid batch prose" in e.get("text", "") for e in events)
    else:
        result = brain.chat(**turn.kwargs)
        assert "Invalid batch prose" not in result["reply"]
    assert result["degraded"] and not assistant_turns(turn)
    assert not turn.tool.called
    assert len(turn.native.posts) == len(turn.closes) == len(turn.costs) == 1


@pytest.mark.parametrize("stop", [False, True])
def test_actual_brain_run_survives_subscriber_detach_or_stop(turn, stop):
    from app import brain_runs
    turn.plans((200, packet()))
    turn.native.block = threading.Event()
    run = brain_runs.start(brain.chat_stream(**turn.kwargs),
                           user_id=turn.kwargs["user_id"], lane="pro")
    try:
        follower = brain_runs.follow(run, interval=0.05)
        next(follower)
        follower.close()
        assert turn.native.arrived.wait(2)
        if stop:
            assert brain_runs.cancel(run.run_id, turn.kwargs["user_id"])
        assert not run.done and not turn.closes
        turn.native.block.set()
        with run._cv:
            assert run._cv.wait_for(lambda: run.done, timeout=3)
        assert len(turn.native.posts) == len(turn.costs) == len(turn.closes) == 1
        assert assistant_turns(turn) == ["Grounded final response."]
        assert sum(event(line).get("type") == "done" for line in run.events) == 1
        assert turn.native.rows("leases")[0]["state"] == "released"
    finally:
        turn.native.block.set()
        with run._cv:
            run._cv.wait_for(lambda: run.done, timeout=3)
        with brain_runs._runs_lock:
            brain_runs._runs.pop(run.run_id, None)
