"""Actual shared-provider/Brain composition, offline and without account discovery.

Transport protocol doubles exercise the incumbent consumers. Gateway wire tests
belong to test_fabric_inference_client; these do not claim live pool admission.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import llm_auth as auth
from engine.neuralweb import brain_gateway as gw


MODEL = "fabric-test-v1"


class Block(SimpleNamespace):
    def model_dump(self):
        return vars(self).copy()


def response(text="Grounded market context.", *, tokens=(11, 7), tool=False, model=MODEL):
    blocks = [Block(type="text", text=text)] if text is not None else []
    if tool:
        blocks.append(Block(type="tool_use", id="read_1", name="get_movers", input={}))
    return SimpleNamespace(
        model=model, content=blocks, stop_reason="tool_use" if tool else "end_turn",
        usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]) if tokens else None,
    )


class TransportFailure(RuntimeError):
    effect_unknown = True


class Client:
    def __init__(self, *steps):
        self.messages = self
        self.steps = list(steps)
        self.calls = []
        self.closed = 0

    def _step(self, method, kwargs):
        self.calls.append((method, kwargs))
        assert self.steps, "unexpected additional inference"
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    def create(self, **kwargs):
        return self._step("create", kwargs)

    @contextmanager
    def stream(self, **kwargs):
        step = self._step("stream", kwargs)
        if isinstance(step, dict):
            final, chunks, failure = step["response"], step["chunks"], step.get("failure")
        else:
            final, failure = step, None
            chunks = [b.text for b in final.content if b.type == "text"]

        class Stream:
            current_message_snapshot = final

            @property
            def text_stream(self):
                yield from chunks
                if failure:
                    raise failure

            def get_final_message(self):
                return final

        try:
            yield Stream()
        finally:
            self.closed += 1


def binding(client):
    return {"client": client, "model": MODEL, "provider": "minimax",
            "cost_basis": "subscription", "cap_id": "fabric_test_pool"}


def provider(client, request_id="turn-1"):
    return auth.build_fabric_provider(lambda: binding(client), request_id=request_id)


def call_args():
    return {"model": MODEL, "messages": [{"role": "user", "content": "Context?"}],
            "system": "Answer with grounded context.", "max_tokens": 200}


@pytest.fixture(autouse=True)
def isolated_writers(monkeypatch, tmp_path):
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    costs, tokens = [], []
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr(gw, "_record_token_usage", lambda *args: tokens.append(args))
    monkeypatch.setattr(gw, "_log_brain_response", lambda **kwargs: None)
    yield costs, tokens


@pytest.fixture
def loop_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(gw, "_all_brain_tool_schemas", lambda *a, **k: [{
        "name": "get_movers", "description": "Read local movers.",
        "input_schema": {"type": "object", "properties": {}},
    }])
    monkeypatch.setattr(gw, "_dispatch_brain_tool", lambda *a, **k: {"items": [], "is_context_only": True})
    return dict(message="Explain the market context.", lane="pro", history=[], context={},
                root=tmp_path, terminal_data_dir=tmp_path, terminal_hub_url="http://127.0.0.1:1",
                model=MODEL, max_tokens=200, tool_budget=1)


def loop(p, args, *, stream=False):
    kw = {**args, "client": p["client"], "providers": [p]}
    if not stream:
        return gw._run_brain_loop(**kw)
    usage, answer = [], []
    events = [json.loads(s[6:]) for s in gw._run_brain_loop_stream(
        **kw, meta_event={"type": "meta", "model": MODEL, "quota": {}},
        usage_out=usage, answer_out=answer) if s.startswith("data: ")]
    return events, usage, answer


def test_selected_binding_uses_only_private_factory_once(monkeypatch):
    factory = Mock(return_value=binding(Client(response())))
    monkeypatch.setattr(gw, "_load_brain_config", lambda *a: {"lanes": {"pro": {
        "provider_order": ["oauth", "anthropic"], "opus_key_env": "MUST_NOT_BE_READ"}}})
    ps = gw._build_lane_providers("pro", fabric_selected=True,
                                  fabric_provider_factory=factory, request_id="turn-1")
    assert len(ps) == 1 and auth.is_fabric_selection(ps)
    factory.assert_called_once_with()


@pytest.mark.parametrize("selected,factory,code", [
    (True, None, "fabric_binding_missing"),
    ("true", None, "fabric_selection_invalid"),
    (True, lambda: {}, "fabric_binding_invalid"),
])
def test_invalid_selection_refuses_before_discovery(monkeypatch, selected, factory, code):
    monkeypatch.setattr(gw, "_load_brain_config", lambda *a: {})
    with pytest.raises(auth.FabricProviderError, match=code):
        gw._build_lane_providers("pro", fabric_selected=selected,
                                 fabric_provider_factory=factory, request_id="turn-1")


def test_host_workload_floor_cannot_be_bypassed(monkeypatch):
    factory = Mock(return_value=binding(Client(response())))
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "production")
    with pytest.raises(auth.FabricProviderError, match="workload_policy_unqualified"):
        auth.build_fabric_provider(factory, request_id="turn-1")
    factory.assert_not_called()


@pytest.mark.parametrize("value", [None, "", "production"])
@pytest.mark.parametrize("location", ["global", "lane", "shared"])
def test_workload_selector_presence_survives_factory_composition(monkeypatch, value, location):
    factory = Mock(return_value=binding(Client(response())))
    cfg = {"workload_profile": value}
    with pytest.raises(auth.FabricProviderError, match="workload_policy_unqualified"):
        if location == "shared":
            auth.build_providers(cfg, fabric_selected=True, fabric_provider_factory=factory,
                                 request_id="turn-1")
        else:
            monkeypatch.setattr(gw, "_load_brain_config", lambda *a: cfg if location == "global"
                                else {"lanes": {"pro": cfg}})
            gw._build_lane_providers("pro", fabric_selected=True,
                                    fabric_provider_factory=factory, request_id="turn-1")
    factory.assert_not_called()


def test_unselected_config_and_mixed_list_fail_before_any_call():
    with pytest.raises(auth.FabricProviderError, match="binding_not_selected"):
        auth.build_providers({"provider_order": ["fabric", "anthropic"]})
    p = provider(Client(response()))
    callback = Mock(side_effect=AssertionError("must not execute"))
    with pytest.raises(auth.FabricProviderError, match="mixed_providers"):
        auth.make_call([p, {"name": "anthropic"}], callback)
    callback.assert_not_called()


def test_cache_hints_removed_only_at_protocol_positions():
    raw = Client(response())
    p = provider(raw)
    kw = call_args()
    kw["tools"] = [{"name": "read", "cache_control": {"type": "ephemeral"},
                    "input_schema": {"type": "object", "properties": {"cache_control": {"type": "string"}}}}]
    kw["messages"] = [{"role": "assistant", "content": [Block(
        type="tool_use", id="r1", name="read", input={"cache_control": "semantic"},
        cache_control={"type": "ephemeral"})]}]
    p["client"].messages.create(**kw)
    sent = raw.calls[0][1]
    assert sent["request_id"] == "turn-1:brain:0"
    assert "cache_control" not in sent["tools"][0]
    assert sent["messages"][0]["content"][0]["input"] == {"cache_control": "semantic"}
    assert "cache_control" not in sent["messages"][0]["content"][0]
    assert "cache_control" in kw["tools"][0]  # original reusable prompt untouched


@pytest.mark.parametrize("stream", [False, True])
def test_real_tool_loop_and_synthesis_use_distinct_steps(loop_inputs, stream):
    raw = Client(response("Reading context.", tool=True, tokens=(11, 3)),
                 response("The grounded result is available.", tokens=(17, 9)))
    p = provider(raw)
    result = loop(p, loop_inputs, stream=stream)
    assert [c[1]["request_id"] for c in raw.calls] == ["turn-1:brain:0", "turn-1:brain:1"]
    assert all(c[1]["model"] == MODEL for c in raw.calls)
    second_messages = raw.calls[1][1]["messages"]
    assert any(b.get("tool_use_id") == "read_1" for m in second_messages
               for b in (m["content"] if isinstance(m["content"], list) else [])
               if isinstance(b, dict))
    usage = result[1][0] if stream else result[4]
    assert (usage["input_tokens"], usage["output_tokens"], usage["usage_state"]) == (28, 12, "known")
    if stream:
        assert result[0][-1]["type"] == "done"
        assert not result[0][-1].get("degraded")
    else:
        assert "grounded result" in result[0]


@pytest.mark.parametrize("failure_kind", ["transport", "invalid_buffered"])
def test_buffered_failure_never_replays_or_leaks(loop_inputs, failure_kind, monkeypatch):
    # Public SSE uses one original wrapped completion for selected Fabric.
    # No draft is emitted before the complete response has been validated.
    if failure_kind == "transport":
        step = TransportFailure("SECRET provider detail must not escape")
    else:
        step = response("SECRET unvalidated model prose", tokens=None, tool=True)
        step.content.append(Block(type="unsupported", text="SECRET unsupported block"))
    raw = Client(step)
    p = provider(raw)
    dead = Mock(side_effect=AssertionError("global account state touched"))
    monkeypatch.setattr(gw, "_pool_cool_for_exc", dead)
    monkeypatch.setattr(gw, "_mark_provider_dead_if_auth", dead)
    monkeypatch.setattr(gw, "_dispatch_brain_tool", dead)
    monkeypatch.setattr(gw, "_create_failover", dead)
    events, usage, answer = loop(p, loop_inputs, stream=True)
    assert [c[0] for c in raw.calls] == ["create"]
    assert events[-1]["degraded"] is True
    assert usage[0]["input_tokens"] is None
    assert usage[0]["usage_state"] == "unknown"
    assert "SECRET" not in json.dumps(events)
    dead.assert_not_called()
    # The only display delta is the incumbent bounded failure notice.
    assert [e["text"] for e in events if e["type"] == "delta"] == [gw._DEGRADED_USER_MSG]
    assert not any(e["type"] in {"retract", "tool"} for e in events)
    assert answer == []


@pytest.mark.parametrize("stream", [False, True])
def test_failed_synthesis_preserves_completed_usage(loop_inputs, isolated_writers, stream):
    raw = Client(response("Checking.", tool=True, tokens=(11, 3)), TransportFailure("lost"))
    p = provider(raw)
    if stream:
        events, _, _ = loop(p, loop_inputs, stream=True)
        assert events[-1]["degraded"] is True
    else:
        with pytest.raises(auth.FabricProviderError):
            loop(p, loop_inputs)
    usage = gw._settle_fabric_usage(p, usage_lane="brain_pro", stage="brain-stream", user_id="u1", lane="pro")
    costs, tokens = isolated_writers
    assert usage["input_tokens"] is None and usage["completed_input_tokens"] == 11
    assert len(raw.calls) == 2 and len(costs) == len(tokens) == 1
    assert costs[0]["provider"] == "minimax" and costs[0]["model"] == MODEL
    assert costs[0]["input_tokens"] == 11 and "turn_total_unknown" in costs[0]["note"]


@pytest.mark.parametrize("bad", ["model", "tool_json", "duplicate_id", "unknown_block"])
def test_malformed_response_cannot_dispatch_tools(loop_inputs, monkeypatch, bad):
    resp = response(tool=True)
    if bad == "model":
        resp.model = "unexpected-model"
    elif bad == "tool_json":
        resp.content[-1].input = '{"incomplete":'
    elif bad == "duplicate_id":
        resp.content.append(resp.content[-1])
    else:
        resp.content.append(Block(type="thinking", text="unsupported"))
    raw = Client(resp)
    dispatch = Mock(side_effect=AssertionError("unvalidated tool dispatched"))
    monkeypatch.setattr(gw, "_dispatch_brain_tool", dispatch)
    with pytest.raises(auth.FabricProviderError):
        loop(provider(raw), loop_inputs)
    assert len(raw.calls) == 1
    dispatch.assert_not_called()


def test_missing_usage_is_unknown_and_creates_no_zero_cost_row(isolated_writers):
    p = provider(Client(response(tokens=None)))
    p["client"].messages.create(**call_args())
    usage = gw._settle_fabric_usage(p, usage_lane="brain_pro", stage="brain-chat", user_id="u1", lane="pro")
    assert usage["input_tokens"] is None and usage["output_tokens"] is None
    assert usage["usage_state"] == "unknown"
    assert isolated_writers == ([], [])


def test_response_log_preserves_explicit_unknown_but_legacy_defaults_stay_zero():
    from lib.mastermind_response_log import build_row
    fields = dict(surface="macro", question="Context?", answer="Context.",
                  model=MODEL, provider="minimax")
    unknown = json.loads(json.dumps(build_row(**fields, input_tokens=None, output_tokens=None)))
    assert unknown["input_tokens"] is None and unknown["output_tokens"] is None
    assert unknown["provider"] == "minimax"
    legacy = build_row(**fields)
    assert legacy["input_tokens"] == legacy["output_tokens"] == 0


def test_completed_empty_response_is_accounted_but_never_retried(isolated_writers):
    raw = Client(response(text="", tokens=(8, 0)))
    p = provider(raw)
    for _ in range(2):
        with pytest.raises(auth.FabricProviderError):
            p["client"].messages.create(**call_args())
    usage = gw._settle_fabric_usage(p, usage_lane="brain_pro", stage="brain-chat", user_id="u1", lane="pro")
    assert len(raw.calls) == 1 and usage["input_tokens"] == 8
    assert len(isolated_writers[0]) == 1


def test_cost_writer_failure_does_not_skip_token_backstop(monkeypatch, isolated_writers):
    p = provider(Client(response(tokens=(8, 2))))
    p["client"].messages.create(**call_args())
    monkeypatch.setattr("lib.ai_costs.record_usage", Mock(side_effect=OSError("ledger unavailable")))
    gw._settle_fabric_usage(p, usage_lane="brain_pro", stage="brain-chat", user_id="u1", lane="pro")
    assert isolated_writers[1] == [("u1", "pro", 8, 2)]


def test_abandoned_stream_closes_and_latches_only_its_turn():
    raw = Client({"response": response(), "chunks": ["first", "second"]})
    p = provider(raw)
    with p["client"].messages.stream(**call_args()) as stream:
        assert next(stream.text_stream) == "first"
        assert len(raw.calls) == 1 and raw.closed == 0
    assert raw.closed == 1 and auth.fabric_usage(p)["usage_state"] == "unknown"
    with pytest.raises(auth.FabricProviderError, match="effect_unknown"):
        p["client"].messages.create(**call_args())
    other = Client(response())
    fresh = provider(other, request_id="turn-2")
    fresh["client"].messages.create(**call_args())
    assert len(raw.calls) == len(other.calls) == 1


def test_final_message_after_context_uses_same_completed_response():
    raw = Client(response())
    p = provider(raw)
    with p["client"].messages.stream(**call_args()) as stream:
        assert list(stream.text_stream) == ["Grounded market context."]
    assert stream.get_final_message() is stream.get_final_message()
    assert auth.fabric_usage(p)["input_tokens"] == 11
    assert len(raw.calls) == 1


def test_callback_cannot_hide_uncertain_inference_as_success(isolated_writers):
    raw = Client(TransportFailure("unknown"))
    p = provider(raw)

    def swallows_failure(client, model):
        try:
            client.messages.create(**call_args())
        except auth.FabricProviderError:
            return "cached-looking fallback", None

    with pytest.raises(auth.FabricProviderError, match="effect_unknown"):
        auth.make_call([p], swallows_failure)
    assert len(raw.calls) == 1 and isolated_writers[0] == []


def test_shared_make_call_accounts_once_per_step_without_legacy_pool_writes(monkeypatch, isolated_writers):
    raw = Client(response(tokens=(0, 0)), response(tokens=(4, 2)))
    p = provider(raw)
    monkeypatch.setattr(auth, "_note_pool_success", Mock(side_effect=AssertionError("native pool write")))
    monkeypatch.setattr(auth, "is_dead", Mock(side_effect=AssertionError("native dead-key lookup")))

    def invoke(client, model):
        resp = client.messages.create(**call_args())
        return resp.content[0].text, None, resp

    for _ in range(2):
        assert auth.make_call([p], invoke, context="fabric-composition")[2] == "fabric"
    rows = isolated_writers[0]
    assert [(r["input_tokens"], r["output_tokens"]) for r in rows] == [(0, 0), (4, 2)]
    assert all(r["provider"] == "minimax" for r in rows)


@pytest.mark.parametrize("stream", [False, True])
def test_public_brain_uses_server_turn_identity_and_skips_instant_recovery(
        monkeypatch, loop_inputs, isolated_writers, stream):
    clients = []

    def factory():
        raw = Client(response())
        clients.append(raw)
        return binding(raw)

    monkeypatch.setattr(gw, "_resolve_tier", lambda *a: {"tier": "pro", "status": "active"})
    monkeypatch.setattr(gw, "_check_and_increment_quota", lambda *a, **k: (True, {"remaining": 9}))
    monkeypatch.setattr(gw, "_ensure_thread", lambda *a, **k: None)
    monkeypatch.setattr(gw._native_facts, "plan_native_facts", lambda *a, **k: None)
    monkeypatch.setattr(gw, "_instant_route", lambda *a, **k: object())
    instant = Mock(side_effect=AssertionError("instant request would allow recovery"))
    monkeypatch.setattr(gw, "_instant_answer", instant)
    kwargs = dict(message="Explain the market context.", user_id="fabric-user", lane="pro",
                  root=loop_inputs["root"],
                  context={"request_id": "attacker", "fabric_selected": False},
                  fabric_selected=True, fabric_provider_factory=factory)
    for _ in range(2):
        if stream:
            events = [json.loads(s[6:]) for s in gw.chat_stream(**kwargs) if s.startswith("data: ")]
            assert events[-1]["type"] == "done" and not events[-1].get("degraded")
        else:
            result = gw.chat(**kwargs)
            assert result["model"] == MODEL and not result["degraded"]
            assert result["usage"]["input_tokens"] == 11
    assert len(clients) == 2 and all(len(c.calls) == 1 for c in clients)
    ids = [c.calls[0][1]["request_id"] for c in clients]
    assert len(set(ids)) == 2 and all("attacker" not in i for i in ids)
    assert len(isolated_writers[0]) == 2
    instant.assert_not_called()


@pytest.mark.parametrize("path", ["/api/brain/chat", "/api/brain/stream"])
def test_http_binding_is_private_and_reconnect_does_not_restart(monkeypatch, path):
    from fastapi.testclient import TestClient
    import app.main as main

    captured = []
    factory = lambda: binding(Client(response()))

    def fake_chat(**kwargs):
        captured.append(kwargs)
        return {"ok": True, "reply": "Context.", "citations": [], "quota": {}}

    def fake_stream(**kwargs):
        captured.append(kwargs)
        yield 'data: {"type":"delta","text":"Context."}\n\n'
        yield 'data: {"type":"done","citations":[]}\n\n'

    monkeypatch.setattr(main.app.state, "fabric_selected", True, raising=False)
    monkeypatch.setattr(main.app.state, "fabric_provider_factory", factory, raising=False)
    monkeypatch.setattr(main, "_brain_track_event", lambda *args: None)
    monkeypatch.setattr(main, "_brain_throttle_check", lambda *args: None)
    monkeypatch.setattr(gw, "chat", fake_chat)
    monkeypatch.setattr(gw, "chat_stream", fake_stream)
    main.app.dependency_overrides[main._brain_user_or_guest] = lambda: {
        "id": "fabric-boundary-test", "email": "", "user_metadata": {}}
    try:
        client = TestClient(main.app)
        res = client.post(path, json={"message": "Market context?", "fabric_selected": False,
            "fabric_provider_factory": "attacker", "context": {"fabric_selected": False,
                "fabric_provider_factory": "attacker", "request_id": "attacker"}},
            headers={"X-Fabric-Selected": "false", "X-Fabric-Provider": "attacker"})
        assert res.status_code == 200, res.text
        assert len(captured) == 1
        assert captured[0]["fabric_selected"] is True
        assert captured[0]["fabric_provider_factory"] is factory
        if path.endswith("stream"):
            events = [json.loads(x[6:]) for x in res.text.splitlines() if x.startswith("data: ")]
            run_id = next(e["run_id"] for e in events if e["type"] == "run")
            again = client.get(f"/api/brain/runs/{run_id}")
            assert again.status_code == 200
            assert len(captured) == 1  # existing run owner replays, no second generator
    finally:
        main.app.dependency_overrides.pop(main._brain_user_or_guest, None)
