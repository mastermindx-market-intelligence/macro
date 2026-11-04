"""Composition tests for the Fabric-injected orchestrator chat path.

The Fabric binding is TRUSTED, server-owned dependency injection: the admin
server stores it on the HTTP server and the Handler forwards it from the
server object alone.  A request body can never supply or override it.

Everything here is SYNTHETIC: a fake Anthropic-shaped client stands in for the
Fabric adapter.  No provider, gateway, credential, network or admin-service
access of any kind, and every persisted/logged state is redirected to a
temporary repo root.

Covered:
  1. selected + missing/invalid binding => zero candidate discovery, zero model calls
  2. explicit False keeps the legacy path; a malformed selection fails safely
  3. one read-only tool response then synthesis: distinct/stable request ids,
     the bound model every round, exact tool ids, only the whitelisted tool
  4. first-round and later-round failures: no downgrade, no candidate, no
     transport retry, no client reconstruction, completed-step usage retained
  5. empty response / unknown usage / model mismatch / malformed tool argument:
     deterministic refusal, no hidden second inference, no fabricated zero usage
  6. two turns on one factory: independent clients, a failed turn does not
     poison the next one
  7. the Handler boundary forwards the server-owned injection; body-supplied
     values cannot override it; auth rejection still prevents inference
  8. advice filter, rate cap and the read-only tool policy still apply
  9. usage state, tool validation, the bounded tool budget, the workload-floor
     refusal, and containment of an unexpected adapter failure
"""
from __future__ import annotations

import copy
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from admin import orchestrator_chat, server


# ---------------------------------------------------------------------------
# Synthetic Anthropic-shaped client
# ---------------------------------------------------------------------------

class _Block:
    """A content block with model_dump(), like the adapter's blocks."""

    def __init__(self, type: str, **fields):
        self.type = type
        for key, value in fields.items():
            setattr(self, key, value)

    def model_dump(self) -> dict:
        out = {"type": self.type}
        for key in ("text", "id", "name", "input"):
            if hasattr(self, key):
                out[key] = getattr(self, key)
        return out


class _Usage:
    def __init__(self, input_tokens=None, output_tokens=None):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Response:
    """An Anthropic-shaped response: content blocks + model + stop_reason + usage."""

    def __init__(self, content, *, model: str, stop_reason: str, usage=None):
        self.content = content
        self.model = model
        self.stop_reason = stop_reason
        self.usage = usage


class _FakeMessages:
    def __init__(self, owner):
        self._owner = owner

    def create(self, **kwargs):
        owner = self._owner
        recorded = dict(kwargs)
        # The loop keeps ONE message list and appends to it, so snapshot the
        # state as it was AT the call.
        recorded["messages"] = copy.deepcopy(kwargs.get("messages", []))
        owner.calls.append(recorded)
        if not owner.steps:
            raise AssertionError("unexpected extra model call")
        step = owner.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step


class _FakeClient:
    """Records every messages.create() call and replays scripted responses."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls: list[dict] = []
        self.messages = _FakeMessages(self)


def _descriptor(client, *, model="fabric-model-x", provider="fabric",
                cost_basis="metered", cap_id="fabric_cap_1") -> dict:
    return {"client": client, "model": model, "provider": provider,
            "cost_basis": cost_basis, "cap_id": cap_id}


def _factory(descriptor) -> callable:
    """A factory that hands out ONE descriptor; records how often it was called."""
    calls: list[int] = []

    def factory():
        calls.append(1)
        return descriptor

    factory.calls = calls
    return factory


class _SequencedFactory:
    """A factory that builds a FRESH client + descriptor on every call."""

    def __init__(self, outcomes):
        self.outcomes = [list(o) for o in outcomes]
        self.built: list[_FakeClient] = []

    def __call__(self):
        client = _FakeClient(self.outcomes[len(self.built)])
        self.built.append(client)
        return _descriptor(client)


def _text_response(text="answered", *, model="fabric-model-x", usage=None):
    return _Response([_Block("text", text=text)], model=model,
                     stop_reason="end_turn", usage=usage)


def _tool_response(block_id="toolu_01", name="read_health", tool_input=None,
                   *, model="fabric-model-x", usage=None):
    return _Response([_Block("tool_use", id=block_id, name=name,
                              input={} if tool_input is None else tool_input)],
                     model=model, stop_reason="tool_use", usage=usage)


# ---------------------------------------------------------------------------
# Fixtures — hermetic state
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _hermetic(monkeypatch, tmp_path):
    """No legacy keys, no shared rate budget, no ambient ledger shard."""
    for env in ("CORTEX_ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
                "ANTHROPIC_API_KEY", "METAB_KEYS_ENABLED", "AI_COSTS_SHARD",
                "AI_COSTS_STATE_ROOT", "MM_PROVIDER_WORKLOAD_PROFILE"):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setenv("CODEX_PROVIDER_ENABLED", "0")
    monkeypatch.setattr(orchestrator_chat, "_RATE_EVENTS", deque())
    monkeypatch.setattr(orchestrator_chat, "ROOT", tmp_path)
    return tmp_path


@pytest.fixture()
def _no_legacy_discovery(monkeypatch):
    """Any legacy candidate/secret discovery on a Fabric turn is a failure."""

    def forbidden(*_a, **_k):
        raise AssertionError("legacy candidate discovery must not run on the Fabric path")

    monkeypatch.setattr(orchestrator_chat, "_resolve_candidates", forbidden)
    monkeypatch.setattr(orchestrator_chat, "_discover_pool_candidates", forbidden)
    monkeypatch.setattr(orchestrator_chat, "_build_client", forbidden)


def _usage_rows(repo) -> list[dict]:
    p = Path(repo) / "data" / "ai_costs" / "usage.jsonl"
    if not p.is_file():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _chat_log_rows(repo) -> list[dict]:
    p = Path(repo) / "data" / "neuralweb" / "orchestrator_chat_log.jsonl"
    if not p.is_file():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _server(fabric_selected=False, fabric_provider_factory=None):
    httpd = server._build_server("127.0.0.1", 0,
                                 fabric_selected=fabric_selected,
                                 fabric_provider_factory=fabric_provider_factory)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, httpd.server_address[1]


def _post(port, path, body):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# 1. selected + missing / invalid binding => nothing else happens
# ---------------------------------------------------------------------------

def test_selected_without_factory_never_discovers_or_calls(tmp_path, _no_legacy_discovery):
    out = orchestrator_chat.chat("what did you do last night?", root=tmp_path,
                                 fabric_selected=True, fabric_provider_factory=None)
    assert out["ok"] is True
    assert out["degraded"] is True and out["mode"] == "degraded"
    assert out["reason"] == "fabric_binding_invalid"
    assert out["reply"].startswith("(degraded — fabric binding unavailable;")
    assert _usage_rows(tmp_path) == []


def test_selected_with_invalid_descriptor_never_discovers_or_calls(tmp_path,
                                                                  _no_legacy_discovery):
    cases = [
        ({"client": object(), "model": "m", "provider": "p",
          "cost_basis": "metered", "cap_id": "c"}, "descriptor_client_invalid"),
        ({"client": _FakeClient([]), "model": "m", "provider": "p",
          "cost_basis": "metered", "cap_id": "c", "extra": 1}, "descriptor_keys_invalid"),
        ({"client": _FakeClient([]), "model": "bad model", "provider": "p",
          "cost_basis": "metered", "cap_id": "c"}, "descriptor_model_invalid"),
        ({"client": _FakeClient([]), "model": "m", "provider": "p",
          "cost_basis": "free", "cap_id": "c"}, "descriptor_cost_basis_invalid"),
        ("not-a-dict", "descriptor_not_a_mapping"),
    ]
    for descriptor, reason in cases:
        factory = _factory(descriptor)
        out = orchestrator_chat.chat("hello", root=tmp_path, fabric_selected=True,
                                    fabric_provider_factory=factory)
        assert out["degraded"] is True, descriptor
        assert out["reason"] == reason, descriptor
        assert len(factory.calls) == 1
        assert _usage_rows(tmp_path) == []


def test_factory_exception_is_refused_without_leaking_detail(tmp_path, _no_legacy_discovery):
    def boom():
        raise RuntimeError("token=sk-secret-value endpoint=https://gw.internal")

    out = orchestrator_chat.chat("hello", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=boom)
    assert out["degraded"] is True
    assert out["reason"] == "fabric_binding_invalid"
    assert "sk-secret-value" not in out["reply"]
    assert "gw.internal" not in out["reply"]


# ---------------------------------------------------------------------------
# 2. explicit False keeps the legacy path; a malformed selection fails safely
# ---------------------------------------------------------------------------

def test_explicit_false_keeps_the_legacy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator_chat, "_resolve_candidates", lambda: [])
    factory = _factory(_descriptor(_FakeClient([])))
    out = orchestrator_chat.chat("hello", root=tmp_path, fabric_selected=False,
                                 fabric_provider_factory=factory)
    assert out["degraded"] is True
    assert out["reply"].startswith("(degraded — no LLM key;")
    assert factory.calls == []          # the legacy path never touches Fabric
    assert "reason" not in out          # the legacy degraded shape is unchanged


def test_missing_selection_defaults_to_the_legacy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator_chat, "_resolve_candidates", lambda: [])
    out = orchestrator_chat.chat("hello", root=tmp_path)
    assert out["degraded"] is True
    assert out["reply"].startswith("(degraded — no LLM key;")


def test_malformed_selection_fails_safely(tmp_path, _no_legacy_discovery):
    for bad in ("true", 1, 0, None, [], {}, object()):
        out = orchestrator_chat.chat("hello", root=tmp_path, fabric_selected=bad,
                                    fabric_provider_factory=_factory(
                                        _descriptor(_FakeClient([]))))
        assert out["degraded"] is True, bad
        assert out["mode"] == "degraded"
        assert out["reason"] == "invalid_fabric_selection", bad


# ---------------------------------------------------------------------------
# 3. one read-only tool response, then the synthesis
# ---------------------------------------------------------------------------

def test_tool_round_then_synthesis(tmp_path):
    client = _FakeClient([
        _tool_response("toolu_01", "read_health", {"limit": 1},
                       usage=_Usage(11, 5)),
        _Response([_Block("text", text="The pipeline ran; two lobes are stale.")],
                  model="fabric-model-x", stop_reason="end_turn", usage=_Usage(7, 3)),
    ])
    factory = _factory(_descriptor(client))
    out = orchestrator_chat.chat("status?", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=factory)

    assert out["ok"] is True and out["degraded"] is False and out["mode"] == "live"
    assert out["reply"] == "The pipeline ran; two lobes are stale."
    assert out["model"] == "fabric-model-x"
    assert out["provider"] == "fabric"
    assert out["cost_basis"] == "metered"
    assert out["cap_id"] == "fabric_cap_1"
    assert out["tool_call_census"] == {"read_health": 1}

    # Two model calls, the BOUND model on every round (no opus/sonnet downgrade).
    assert len(client.calls) == 2
    assert [c["model"] for c in client.calls] == ["fabric-model-x"] * 2
    assert all("temperature" not in c and "stop_sequences" not in c for c in client.calls)

    # Every intentional call carries "<turn id>:orchestrator:<step>", the step
    # index starting at 0 and advancing exactly once per call.
    turn_id = out["request_id"]
    assert turn_id and turn_id.isprintable() and len(turn_id) <= 64
    assert client.calls[0]["request_id"] == f"{turn_id}:orchestrator:0"
    assert client.calls[1]["request_id"] == f"{turn_id}:orchestrator:1"
    assert client.calls[0]["request_id"] != client.calls[1]["request_id"]

    # The assistant history is fed back as PLAIN blocks, tool ids preserved.
    second_messages = client.calls[1]["messages"]
    assistant = [m for m in second_messages if m["role"] == "assistant"]
    assert len(assistant) == 1
    block = assistant[0]["content"][0]
    assert isinstance(block, dict)
    assert block == {"type": "tool_use", "id": "toolu_01", "name": "read_health",
                     "input": {"limit": 1}}
    tool_message = [m for m in second_messages if m["role"] == "user"][-1]
    result_block = tool_message["content"][0]
    assert result_block["type"] == "tool_result"
    assert result_block["tool_use_id"] == "toolu_01"
    assert "available" in result_block["content"]

    # ONE cost aggregate for the turn (not one row per round).
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 18 and rows[0]["output_tokens"] == 8
    assert rows[0]["lane"] == "orchestrator-chat"
    assert rows[0]["provider"] == "fabric"
    assert rows[0]["cost_basis"] == "metered"
    assert rows[0]["model"] == "fabric-model-x"
    assert rows[0]["key_id"] == "fabric_cap_1"

    log_rows = _chat_log_rows(tmp_path)
    assert len(log_rows) == 1
    assert log_rows[0]["degraded"] is False
    assert log_rows[0]["usage_state"] == "known"
    assert log_rows[0]["tool_call_census"] == {"read_health": 1}


def test_explicit_request_id_is_honoured_and_stable(tmp_path):
    client = _FakeClient([
        _tool_response(usage=_Usage(1, 1)),
        _text_response("done", usage=_Usage(1, 1)),
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)),
                                 request_id="turn-abc-123")
    assert out["request_id"] == "turn-abc-123"
    assert client.calls[0]["request_id"] == "turn-abc-123:orchestrator:0"
    assert client.calls[1]["request_id"] == "turn-abc-123:orchestrator:1"


# ---------------------------------------------------------------------------
# 4. failures: no downgrade, no candidate, no retry, no client rebuild
# ---------------------------------------------------------------------------

def test_first_round_failure_is_terminal(tmp_path, _no_legacy_discovery):
    client = _FakeClient([RuntimeError("401 unauthorized")])
    factory = _factory(_descriptor(client))
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=factory)
    assert out["degraded"] is True
    assert out["reason"] == "fabric_inference_failed"
    assert len(client.calls) == 1          # no transport retry
    assert len(factory.calls) == 1         # no client reconstruction
    assert client.calls[0]["model"] == "fabric-model-x"
    assert "401" not in out["reply"]
    assert _usage_rows(tmp_path) == []


def test_later_round_failure_invalidates_the_total_but_keeps_the_completed_step(tmp_path):
    """A possibly dispatched transport failure invalidates the TURN TOTAL.

    The earlier completed step survives separately and is settled exactly once,
    but the failure is never reported as a fully known successful total.
    """
    client = _FakeClient([
        _tool_response("toolu_02", usage=_Usage(11, 5)),
        RuntimeError("503 upstream unavailable"),
    ])
    factory = _factory(_descriptor(client))
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=factory)

    assert out["degraded"] is True
    assert out["reason"] == "fabric_inference_failed"
    assert len(client.calls) == 2           # exactly the two intended calls
    assert len(factory.calls) == 1          # no client reconstruction
    assert client.calls[0]["request_id"] != client.calls[1]["request_id"]

    # The turn total is UNKNOWN — the request may have been dispatched.
    assert out["usage_state"] == "unknown"
    assert out["input_tokens"] is None and out["output_tokens"] is None
    assert out["est_cost_usd"] is None
    assert out["usage_uncertainty"] == "invalidated_transport"

    # The completed step's usage is retained, not erased.
    assert out["completed_step_usage"] == {"input_tokens": 11, "output_tokens": 5,
                                           "rounds": 1}
    # Settled exactly ONCE through the existing writer, explicitly labelled.
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 11 and rows[0]["output_tokens"] == 5
    assert rows[0]["note"] == orchestrator_chat._FABRIC_PARTIAL_KNOWN_NOTE
    assert rows[0]["provider"] == "fabric"
    assert rows[0]["model"] == "fabric-model-x"
    assert rows[0]["key_id"] == "fabric_cap_1"
    assert rows[0]["cost_basis"] == "metered"

    # The chat log carries the UNKNOWN totals, never the partial sum.
    log_rows = _chat_log_rows(tmp_path)
    assert len(log_rows) == 1
    assert log_rows[0]["degraded"] is True
    assert log_rows[0]["usage_state"] == "unknown"
    assert log_rows[0]["input_tokens"] is None
    assert log_rows[0]["output_tokens"] is None
    assert log_rows[0]["usage_uncertainty"] == "invalidated_transport"

    # No second accounting owner/table: the two incumbent artifacts are all.
    ledgers = sorted(p.relative_to(tmp_path).as_posix()
                     for p in (tmp_path / "data").rglob("*.jsonl"))
    assert ledgers == ["data/ai_costs/usage.jsonl",
                       "data/neuralweb/orchestrator_chat_log.jsonl"]


def test_no_fallback_model_is_ever_used(tmp_path):
    """The bound model is used for every round — there is no downgrade."""
    client = _FakeClient([
        _tool_response(usage=_Usage(1, 1)),
        RuntimeError("429 rate limited"),
    ])
    orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                           fabric_provider_factory=_factory(_descriptor(client)))
    assert [c["model"] for c in client.calls] == ["fabric-model-x", "fabric-model-x"]
    for call in client.calls:
        assert call["model"] not in ("claude-opus-4-8", "claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# 5. empty response / unknown usage / model mismatch / malformed tool argument
# ---------------------------------------------------------------------------

def test_empty_response_is_a_deterministic_refusal(tmp_path):
    client = _FakeClient([_Response([], model="fabric-model-x",
                                    stop_reason="end_turn", usage=_Usage(3, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_empty_response"
    assert len(client.calls) == 1           # no hidden second inference
    assert out["usage_state"] == "known"
    assert out["input_tokens"] == 3 and out["output_tokens"] == 1


def test_unknown_usage_is_never_fabricated_as_zero(tmp_path):
    client = _FakeClient([_Response([_Block("text", text="ok")],
                                    model="fabric-model-x", stop_reason="end_turn",
                                    usage=None)])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    # The answer is the model's; only the accounting is unknown.
    assert out["degraded"] is False
    assert out["reply"] == "ok"
    assert out["usage_state"] == "unknown"
    assert out["input_tokens"] is None and out["output_tokens"] is None
    assert out["est_cost_usd"] is None
    # Nothing is inserted into the ledger: a fabricated zero would read as free.
    assert _usage_rows(tmp_path) == []
    log_rows = _chat_log_rows(tmp_path)
    assert len(log_rows) == 1
    assert log_rows[0]["usage_state"] == "unknown"
    assert log_rows[0]["input_tokens"] is None


def test_model_mismatch_refuses_before_any_tool_action(tmp_path, monkeypatch):
    dispatched = []
    monkeypatch.setattr(orchestrator_chat, "_dispatch_tool",
                        lambda *a, **k: dispatched.append(a) or {})
    client = _FakeClient([_tool_response("toolu_03", usage=_Usage(1, 1),
                                         model="some-other-model")])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_model_mismatch"
    assert len(client.calls) == 1
    assert dispatched == []


@pytest.mark.parametrize("tool_input", ['{"limit": ', ["not", "an", "object"], 7])
def test_malformed_tool_argument_is_refused_without_dispatch(tmp_path, monkeypatch,
                                                             tool_input):
    dispatched = []
    monkeypatch.setattr(orchestrator_chat, "_dispatch_tool",
                        lambda *a, **k: dispatched.append(a) or {})
    client = _FakeClient([_tool_response("toolu_04", "read_health", tool_input,
                                         usage=_Usage(1, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_tool_call_malformed"
    assert len(client.calls) == 1
    assert dispatched == []


def test_unsupported_stop_reason_is_refused(tmp_path, monkeypatch):
    dispatched = []
    monkeypatch.setattr(orchestrator_chat, "_dispatch_tool",
                        lambda *a, **k: dispatched.append(a) or {})
    client = _FakeClient([_Response([_Block("tool_use", id="toolu_05", name="read_health",
                                             input={})],
                                    model="fabric-model-x", stop_reason="weird_reason",
                                    usage=_Usage(1, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_stop_reason_unsupported"
    assert dispatched == []


@pytest.mark.parametrize("stop_reason", ["end_turn", "max_tokens", "stop_sequence",
                                         "stop", "length"])
def test_terminal_stop_reasons_end_the_turn_without_a_tool(tmp_path, stop_reason):
    client = _FakeClient([_Response([_Block("text", text="terminal")],
                                    model="fabric-model-x", stop_reason=stop_reason,
                                    usage=_Usage(1, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is False
    assert out["reply"] == "terminal"
    assert len(client.calls) == 1


def test_descriptor_may_be_any_mapping_with_exactly_the_five_keys(tmp_path):
    from types import MappingProxyType

    client = _FakeClient([_text_response("ok", usage=_Usage(1, 1))])
    descriptor = MappingProxyType(_descriptor(client))
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(descriptor))
    assert out["degraded"] is False
    assert out["reply"] == "ok"


# ---------------------------------------------------------------------------
# 6. two turns on one factory -> independent clients
# ---------------------------------------------------------------------------

def test_two_turns_get_independent_clients(tmp_path):
    factory = _SequencedFactory([
        [RuntimeError("boom")],
        [_text_response("second turn", usage=_Usage(2, 2))],
    ])
    first = orchestrator_chat.chat("one", root=tmp_path, fabric_selected=True,
                                   fabric_provider_factory=factory)
    second = orchestrator_chat.chat("two", root=tmp_path, fabric_selected=True,
                                    fabric_provider_factory=factory)

    assert first["degraded"] is True and first["reason"] == "fabric_inference_failed"
    assert second["degraded"] is False and second["reply"] == "second turn"
    assert len(factory.built) == 2
    assert factory.built[0] is not factory.built[1]
    assert len(factory.built[0].calls) == 1
    assert len(factory.built[1].calls) == 1
    assert first["request_id"] != second["request_id"]


# ---------------------------------------------------------------------------
# 7. the Handler boundary
# ---------------------------------------------------------------------------

def test_handler_forwards_the_server_owned_injection(tmp_path):
    client = _FakeClient([_text_response("from fabric", usage=_Usage(3, 2))])
    factory = _factory(_descriptor(client))
    httpd, port = _server(True, factory)
    try:
        out = _post(port, "/api/orchestrator/chat", {
            "message": "hello",
            "history": [],
            # A body-supplied binding must never override the server's own.
            "fabric_selected": False,
            "fabric_provider_factory": "not-a-factory",
            "request_id": "attacker-supplied-id",
        })
    finally:
        httpd.shutdown()
        httpd.server_close()

    assert out["mode"] == "live"
    assert out["model"] == "fabric-model-x"
    assert out["reply"] == "from fabric"
    assert out["request_id"] != "attacker-supplied-id"
    assert len(factory.calls) == 1
    assert client.calls[0]["request_id"] == f"{out['request_id']}:orchestrator:0"


def test_body_cannot_enable_fabric_on_a_legacy_server(tmp_path):
    factory = _factory(_descriptor(_FakeClient([_text_response("never used")])))
    httpd, port = _server(False, factory)
    try:
        out = _post(port, "/api/orchestrator/chat", {
            "message": "hello",
            "fabric_selected": True,
            "fabric_provider_factory": "not-a-factory",
        })
    finally:
        httpd.shutdown()
        httpd.server_close()

    assert out["degraded"] is True
    assert out["reply"].startswith("(degraded — no LLM key;")
    assert factory.calls == []


def test_auth_rejection_prevents_inference(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "unit-test-password")
    calls = []
    factory = _factory(_descriptor(_FakeClient([_text_response("never used")])))
    factory.calls = calls
    httpd, port = _server(True, factory)
    try:
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            _post(port, "/api/orchestrator/chat", {"message": "hello"})
        assert excinfo.value.code == 401
    finally:
        httpd.shutdown()
        httpd.server_close()

    assert calls == []      # no binding resolution, no inference
    assert _usage_rows(tmp_path) == []


# ---------------------------------------------------------------------------
# 8. advice filter, rate cap and the read-only tool policy
# ---------------------------------------------------------------------------

def test_advice_filter_still_runs_on_the_fabric_path(tmp_path, monkeypatch):
    seen = []

    def fake_filter(text):
        seen.append(text)
        return ("[filtered] " + text, True)

    monkeypatch.setattr(orchestrator_chat, "_advice_filter", fake_filter)
    client = _FakeClient([_text_response("you should buy BTC", usage=_Usage(1, 1))])
    out = orchestrator_chat.chat("should I buy?", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert seen == ["you should buy BTC"]
    assert out["filtered"] is True
    assert out["reply"] == "[filtered] you should buy BTC"


def test_rate_cap_still_applies_to_the_fabric_path(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator_chat, "_RATE_EVENTS", deque([time.time()] * 20))
    client = _FakeClient([_text_response("never used", usage=_Usage(1, 1))])
    factory = _factory(_descriptor(client))
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=factory)
    assert out["degraded"] is True
    assert out["reason"] == "rate_cap"
    assert "rate cap 20 messages/hour reached" in out["reply"]
    assert client.calls == []                # no model call past the cap
    assert len(factory.calls) == 1           # the binding is still resolved once


def test_read_only_tool_policy_still_applies(tmp_path):
    client = _FakeClient([
        _tool_response("toolu_06", "write_config", {"path": "x"}, usage=_Usage(1, 1)),
        _text_response("I only read things.", usage=_Usage(1, 1)),
    ])
    out = orchestrator_chat.chat("change the config", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is False
    assert out["tool_call_census"] == {}     # a refused tool is never counted
    tool_message = [m for m in client.calls[1]["messages"] if m["role"] == "user"][-1]
    tool_result = tool_message["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_06"
    assert "tool not allowed" in tool_result["content"]


# ---------------------------------------------------------------------------
# 9. usage state: an unknown round poisons the aggregate
# ---------------------------------------------------------------------------

def test_missing_usage_after_a_known_round_poisons_the_aggregate(tmp_path):
    """A later response with no usage makes the TURN aggregate unknown.

    The earlier known round is not erased: it survives as the completed-step
    subtotal and is settled once, explicitly labelled.
    """
    client = _FakeClient([
        _tool_response("toolu_01", usage=_Usage(11, 5)),
        _Response([_Block("text", text="done")], model="fabric-model-x",
                  stop_reason="end_turn", usage=None),
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))

    assert out["degraded"] is False
    assert out["reply"] == "done"
    assert out["usage_state"] == "unknown"
    assert out["input_tokens"] is None and out["output_tokens"] is None
    assert out["est_cost_usd"] is None
    assert out["usage_uncertainty"] == "missing_usage"
    assert out["completed_step_usage"] == {"input_tokens": 11, "output_tokens": 5,
                                           "rounds": 1}
    # Settled exactly once, labelled as partial.
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 11 and rows[0]["output_tokens"] == 5
    assert rows[0]["note"] == orchestrator_chat._FABRIC_PARTIAL_KNOWN_NOTE
    # The chat log carries the UNKNOWN totals, never the partial sum.
    log_rows = _chat_log_rows(tmp_path)
    assert len(log_rows) == 1
    assert log_rows[0]["input_tokens"] is None
    assert log_rows[0]["output_tokens"] is None
    assert log_rows[0]["est_cost_usd"] is None
    assert log_rows[0]["usage_state"] == "unknown"
    assert log_rows[0]["usage_uncertainty"] == "missing_usage"


def test_a_later_known_response_cannot_erase_an_earlier_unknown(tmp_path):
    client = _FakeClient([
        _tool_response("toolu_01", usage=None),        # missing usage
        _text_response("done", usage=_Usage(7, 3)),    # known, but later
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))

    assert out["degraded"] is False
    assert out["reply"] == "done"
    assert out["usage_state"] == "unknown"
    assert out["input_tokens"] is None and out["output_tokens"] is None
    assert out["usage_uncertainty"] == "missing_usage"
    # The later known response is a completed step of its own, but it can
    # never become the turn's aggregate.
    assert out["completed_step_usage"] == {"input_tokens": 7, "output_tokens": 3,
                                           "rounds": 1}
    # That known step is settled exactly once, labelled partial; the row
    # carries the KNOWN step, never a fabricated aggregate.
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 7 and rows[0]["output_tokens"] == 3
    assert rows[0]["note"] == orchestrator_chat._FABRIC_PARTIAL_KNOWN_NOTE
    # The chat log still carries the UNKNOWN aggregate.
    log_rows = _chat_log_rows(tmp_path)
    assert len(log_rows) == 1
    assert log_rows[0]["input_tokens"] is None
    assert log_rows[0]["output_tokens"] is None
    assert log_rows[0]["usage_state"] == "unknown"


@pytest.mark.parametrize("bad_tokens", [
    (True, 5), (False, 5), (-1, 5), (1.5, 5), ("5", 5), (None, 5),
    (5, True), (5, -3), (5, 2.0), (5, "3"), (5, None),
])
def test_token_counts_that_are_not_exact_non_negative_integers_are_unknown(tmp_path,
                                                                           bad_tokens):
    client = _FakeClient([_text_response("done", usage=_Usage(*bad_tokens))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is False
    assert out["reply"] == "done"
    assert out["usage_state"] == "unknown"
    assert out["input_tokens"] is None and out["output_tokens"] is None
    assert _usage_rows(tmp_path) == []


# ---------------------------------------------------------------------------
# 10. an untrusted response invalidates the turn total
# ---------------------------------------------------------------------------

def test_model_mismatch_invalidates_the_turn_total(tmp_path):
    client = _FakeClient([
        _tool_response("toolu_01", usage=_Usage(11, 5)),
        _Response([_Block("text", text="x")], model="some-other-model",
                  stop_reason="end_turn", usage=_Usage(9, 9)),
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))

    assert out["degraded"] is True
    assert out["reason"] == "fabric_model_mismatch"
    assert out["usage_state"] == "unknown"
    assert out["input_tokens"] is None and out["output_tokens"] is None
    assert out["usage_uncertainty"] == "invalidated_untrusted"
    # The untrusted response's own usage is NOT counted; the earlier known
    # step survives separately.
    assert out["completed_step_usage"] == {"input_tokens": 11, "output_tokens": 5,
                                           "rounds": 1}
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 11 and rows[0]["output_tokens"] == 5
    assert rows[0]["note"] == orchestrator_chat._FABRIC_PARTIAL_KNOWN_NOTE


def test_valid_empty_response_keeps_its_actual_known_usage(tmp_path):
    """A valid, completed empty response keeps ITS OWN known usage."""
    client = _FakeClient([_Response([], model="fabric-model-x",
                                    stop_reason="end_turn", usage=_Usage(3, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_empty_response"
    assert out["usage_state"] == "known"
    assert out["input_tokens"] == 3 and out["output_tokens"] == 1
    assert "usage_uncertainty" not in out
    assert len(client.calls) == 1            # no hidden second inference
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 3 and rows[0]["output_tokens"] == 1
    assert rows[0]["note"] == ""             # a fully known row is not partial


# ---------------------------------------------------------------------------
# 11. request ids: one distinct id per call
# ---------------------------------------------------------------------------

def test_every_call_carries_a_distinct_step_id(tmp_path):
    client = _FakeClient([
        _tool_response("toolu_a", usage=_Usage(1, 1)),
        _tool_response("toolu_b", usage=_Usage(1, 1)),
        _text_response("done", usage=_Usage(1, 1)),
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    turn_id = out["request_id"]
    ids = [c["request_id"] for c in client.calls]
    assert ids == [f"{turn_id}:orchestrator:{i}" for i in range(3)]
    assert len(set(ids)) == 3


def test_absent_request_id_is_generated_once(tmp_path):
    client = _FakeClient([
        _tool_response(usage=_Usage(1, 1)),
        _text_response("done", usage=_Usage(1, 1)),
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    turn_id = out["request_id"]
    assert turn_id and turn_id.isprintable() and len(turn_id) <= 64
    # Generated once: every call of the turn derives from the SAME id.
    assert {c["request_id"] for c in client.calls} == {
        f"{turn_id}:orchestrator:0", f"{turn_id}:orchestrator:1"}


@pytest.mark.parametrize("bad", ["", "   ", "x" * 65, "bad\x00id", 7, True, [], {}])
def test_explicit_malformed_request_id_refuses_before_the_factory(tmp_path, bad):
    factory = _factory(_descriptor(_FakeClient([])))
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=factory, request_id=bad)
    assert out["degraded"] is True
    assert out["reason"] == "invalid_request_id"
    assert factory.calls == []          # no factory was ever constructed
    assert "request_id" not in out      # the malformed id is never echoed
    assert _usage_rows(tmp_path) == []


# ---------------------------------------------------------------------------
# 12. tool validation before ANY dispatch
# ---------------------------------------------------------------------------

def test_duplicate_tool_ids_are_refused_without_dispatch(tmp_path, monkeypatch):
    dispatched = []
    monkeypatch.setattr(orchestrator_chat, "_dispatch_tool",
                        lambda *a, **k: dispatched.append(a) or {})
    client = _FakeClient([_Response(
        [_Block("tool_use", id="toolu_dup", name="read_health", input={}),
         _Block("tool_use", id="toolu_dup", name="read_health", input={})],
        model="fabric-model-x", stop_reason="tool_use", usage=_Usage(1, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_tool_call_malformed"
    assert len(client.calls) == 1
    assert dispatched == []


@pytest.mark.parametrize("block_id,name", [
    ("", "read_health"),
    ("   ", "read_health"),
    ("toolu_01" * 40, "read_health"),
    ("toolu/../etc", "read_health"),
    ("toolu 01", "read_health"),
    ("toolu_01", ""),
    ("toolu_01", "read health"),
    ("toolu_01", "read_health" * 40),
    ("toolu_01", "read/health"),
    ("toolu_01\n", "read_health"),
    ("toolu_01", "read_health\n"),
    ("toolu_01\r", "read_health"),
    ("toolu_01", "read_health\r"),
])
def test_unsafe_or_unbounded_tool_id_or_name_is_refused_without_dispatch(
        tmp_path, monkeypatch, block_id, name):
    dispatched = []
    monkeypatch.setattr(orchestrator_chat, "_dispatch_tool",
                        lambda *a, **k: dispatched.append(a) or {})
    client = _FakeClient([_Response(
        [_Block("tool_use", id=block_id, name=name, input={})],
        model="fabric-model-x", stop_reason="tool_use", usage=_Usage(1, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_tool_call_malformed"
    assert len(client.calls) == 1
    assert dispatched == []


def test_tool_use_stop_without_a_tool_block_is_refused(tmp_path, monkeypatch):
    dispatched = []
    monkeypatch.setattr(orchestrator_chat, "_dispatch_tool",
                        lambda *a, **k: dispatched.append(a) or {})
    client = _FakeClient([_Response([_Block("text", text="no tool")],
                                    model="fabric-model-x", stop_reason="tool_use",
                                    usage=_Usage(1, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_tool_call_malformed"
    assert dispatched == []


def test_tool_block_next_to_a_terminal_stop_is_refused_without_dispatch(tmp_path,
                                                                       monkeypatch):
    dispatched = []
    monkeypatch.setattr(orchestrator_chat, "_dispatch_tool",
                        lambda *a, **k: dispatched.append(a) or {})
    client = _FakeClient([_Response(
        [_Block("text", text="all done"),
         _Block("tool_use", id="toolu_x", name="read_health", input={})],
        model="fabric-model-x", stop_reason="end_turn", usage=_Usage(1, 1))])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_tool_call_malformed"
    assert len(client.calls) == 1
    assert dispatched == []


# ---------------------------------------------------------------------------
# 13. the bounded tool budget
# ---------------------------------------------------------------------------

def _tool_round(block_id, narration=None, usage=_Usage(2, 1)):
    content = []
    if narration:
        content.append(_Block("text", text=narration))
    content.append(_Block("tool_use", id=block_id, name="read_health", input={}))
    return _Response(content, model="fabric-model-x", stop_reason="tool_use",
                     usage=usage)


def test_exhausted_tool_budget_synthesizes_instead_of_returning_narration(tmp_path):
    budget = orchestrator_chat._MAX_TOOL_CALLS
    steps = [_tool_round(f"toolu_{i:02d}", narration="still checking the pipeline.")
             for i in range(budget)]
    steps.append(_text_response("final synthesis", usage=_Usage(3, 2)))
    client = _FakeClient(steps)
    out = orchestrator_chat.chat("go", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))

    assert out["degraded"] is False
    # The earlier tool narration is NOT returned as a completed answer.
    assert out["reply"] == "final synthesis"
    assert out["tool_call_census"] == {"read_health": budget}
    # One extra, explicit synthesis step with tools=[] and its own next id.
    assert len(client.calls) == budget + 1
    assert client.calls[-1]["tools"] == []
    ids = [c["request_id"] for c in client.calls]
    assert ids == [f"{out['request_id']}:orchestrator:{i}"
                   for i in range(budget + 1)]
    assert len(set(ids)) == len(ids)


def test_synthesis_step_refuses_a_tool_response(tmp_path):
    budget = orchestrator_chat._MAX_TOOL_CALLS
    steps = [_tool_round(f"toolu_{i:02d}") for i in range(budget)]
    steps.append(_tool_round("toolu_late"))
    client = _FakeClient(steps)
    out = orchestrator_chat.chat("go", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_tool_call_malformed"
    assert len(client.calls) == budget + 1
    # The refused synthesis tool was never dispatched or counted.
    log_rows = _chat_log_rows(tmp_path)
    assert len(log_rows) == 1
    assert log_rows[0]["tool_call_census"] == {"read_health": budget}


def test_tool_budget_below_the_limit_does_not_synthesize(tmp_path):
    """The synthesis step happens only when the budget is actually spent."""
    budget = orchestrator_chat._MAX_TOOL_CALLS
    steps = [_tool_round(f"toolu_{i:02d}") for i in range(budget - 1)]
    steps.append(_text_response("plain answer", usage=_Usage(3, 2)))
    client = _FakeClient(steps)
    out = orchestrator_chat.chat("go", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is False
    assert out["reply"] == "plain answer"
    assert len(client.calls) == budget          # no extra synthesis call
    assert client.calls[-1]["tools"] != []      # tools were still offered


def test_duplicate_tool_id_across_rounds_is_refused(tmp_path, monkeypatch):
    """A tool id must not repeat anywhere in the turn."""
    dispatched = []
    monkeypatch.setattr(orchestrator_chat, "_dispatch_tool",
                        lambda *a, **k: dispatched.append(a) or {})
    client = _FakeClient([
        _tool_response("toolu_same", usage=_Usage(1, 1)),
        _tool_response("toolu_same", usage=_Usage(1, 1)),
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_tool_call_malformed"
    assert len(client.calls) == 2
    # Only the FIRST occurrence was dispatched; the repeat was refused.
    assert len(dispatched) == 1


def test_synthesis_usage_is_counted_in_the_turn_aggregate(tmp_path):
    budget = orchestrator_chat._MAX_TOOL_CALLS
    steps = [_tool_round(f"toolu_{i:02d}", usage=_Usage(2, 1))
             for i in range(budget)]
    steps.append(_text_response("synth", usage=_Usage(5, 4)))
    client = _FakeClient(steps)
    out = orchestrator_chat.chat("go", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is False
    assert out["usage_state"] == "known"
    assert out["input_tokens"] == 2 * budget + 5
    assert out["output_tokens"] == budget + 4
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 2 * budget + 5
    assert rows[0]["note"] == ""


# ---------------------------------------------------------------------------
# 14. the declared workload floor gate
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["", "   ", "declared-floor-1"])
def test_workload_profile_presence_refuses_before_the_factory(tmp_path, monkeypatch,
                                                              value):
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", value)
    factory = _factory(_descriptor(_FakeClient([])))
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=factory)
    assert out["degraded"] is True
    assert out["reason"] == "fabric_workload_profile_present"
    assert factory.calls == []          # the factory is never invoked
    if value.strip():
        assert value.strip() not in out["reply"]   # the value is never echoed
    assert _usage_rows(tmp_path) == []


# ---------------------------------------------------------------------------
# 15. review findings: narration, control characters, untrusted usage, surprises
# ---------------------------------------------------------------------------

def test_tool_narration_is_never_returned_as_a_completed_answer(tmp_path):
    """A valid but EMPTY terminal response refuses the turn.

    The narration of an earlier tool round must not become the answer: it is
    a degraded refusal, and the completed steps are still settled once.
    """
    client = _FakeClient([
        _Response([_Block("text", text="still checking the pipeline."),
                   _Block("tool_use", id="toolu_01", name="read_health", input={})],
                  model="fabric-model-x", stop_reason="tool_use", usage=_Usage(11, 5)),
        _Response([], model="fabric-model-x", stop_reason="end_turn",
                  usage=_Usage(7, 3)),
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_empty_response"
    assert "still checking" not in out["reply"]
    assert len(client.calls) == 2           # no hidden recovery call
    # The empty response is valid: it keeps its own known usage.
    assert out["usage_state"] == "known"
    assert out["input_tokens"] == 18 and out["output_tokens"] == 8
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 18 and rows[0]["output_tokens"] == 8
    assert rows[0]["note"] == ""


def test_refused_synthesis_tool_response_is_not_settled_as_a_known_step(tmp_path):
    """An untrusted response never settles its own usage as a known step."""
    budget = orchestrator_chat._MAX_TOOL_CALLS
    steps = [_tool_round(f"toolu_{i:02d}", usage=_Usage(2, 1))
             for i in range(budget)]
    steps.append(_tool_round("toolu_late", usage=_Usage(7, 3)))
    client = _FakeClient(steps)
    out = orchestrator_chat.chat("go", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_tool_call_malformed"
    assert out["usage_state"] == "unknown"
    assert out["input_tokens"] is None and out["output_tokens"] is None
    # Only the EARLIER completed steps are settled; the refused, untrusted
    # response contributes nothing.
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 2 * budget
    assert rows[0]["output_tokens"] == budget
    assert rows[0]["note"] == orchestrator_chat._FABRIC_PARTIAL_KNOWN_NOTE


class _Boom:
    """A response whose attribute access raises: an adapter-side surprise."""

    @property
    def model(self):
        raise RuntimeError("secret=sk-leak endpoint=https://gw.internal")


def test_an_unexpected_adapter_failure_is_contained_and_bounded(tmp_path):
    """chat() never raises and never leaks exception text."""
    client = _FakeClient([])
    client.steps = [_Boom()]
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["ok"] is True
    assert out["degraded"] is True
    assert out["reason"] == "fabric_inference_failed"
    assert "sk-leak" not in out["reply"]
    assert "gw.internal" not in out["reply"]
    assert out["usage_state"] == "unknown"
    assert _usage_rows(tmp_path) == []


def test_a_contained_failure_still_reports_the_dispatched_tools(tmp_path):
    """The chat log agrees with the ledger about what the turn did."""
    client = _FakeClient([
        _tool_response("toolu_01", "read_health", {}, usage=_Usage(11, 5)),
        _Boom(),
    ])
    out = orchestrator_chat.chat("hi", root=tmp_path, fabric_selected=True,
                                 fabric_provider_factory=_factory(_descriptor(client)))
    assert out["degraded"] is True
    assert out["reason"] == "fabric_inference_failed"
    log_rows = _chat_log_rows(tmp_path)
    assert len(log_rows) == 1
    assert log_rows[0]["tool_call_census"] == {"read_health": 1}
    rows = _usage_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 11 and rows[0]["output_tokens"] == 5
