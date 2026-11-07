"""Admin, Ask and AI Brief through real shared clients and paired native A/B.

Only qualification, credentials, data and the upstream replies are synthetic.
The existing HTTP handler, gateway, SQLite broker and all consumer loops run.
"""
from dataclasses import replace
import json
import os
from unittest.mock import Mock

import pytest

from admin import orchestrator_chat as admin
from engine import fabric_inference_client as transport
from engine import llm_auth as auth, master_brain as brief
from engine import provider_production_modes as owner
from engine.neuralweb import ask_brain as ask
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401
from tests.test_master_brain_fabric_composition import _brief_reply, _REAL_CACHE_GET, _REAL_CACHE_PUT


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
_CLIENT_TYPE = transport.FabricInferenceClient


def packet(text="Measured context is available.", *, model=MODEL, tool=None):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "read-1", "type": "function",
            "function": {"name": tool, "arguments": "{}"}}]
    result = {"choices": [{"index": 0, "message": message,
        "finish_reason": "tool_calls" if tool else "stop"}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}
    if model is not None:
        result["model"] = model
    return result


@pytest.fixture
def callers(selected, monkeypatch):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"] += [
        "admin-orchestrator", "ask-brain", "master-brain"]
    state.save()
    monkeypatch.setattr(owner, "__file__", str(state.root / "engine/provider_production_modes.py"))
    monkeypatch.setattr(admin, "_rate_ok", lambda: True)
    monkeypatch.setattr(admin, "_degraded_reply", lambda _root, reason: "Unavailable: " + reason)
    monkeypatch.setattr(ask, "_STATE_DIR", state.root / "quota")
    monkeypatch.setattr(ask, "_analyst_block", lambda _question: "")
    monkeypatch.setattr(brief, "_mb_reply_cache_get", _REAL_CACHE_GET)
    monkeypatch.setattr(brief, "_mb_reply_cache_put", _REAL_CACHE_PUT)
    data = state.root / "data/neuralweb"
    data.mkdir(parents=True)
    (data / "world_state.json").write_text(json.dumps({"regime": "measured", "is_context_only": True}))
    closes = []
    close = _CLIENT_TYPE.close
    def observed_close(client):
        closes.append(client.operation_id)
        return close(client)
    monkeypatch.setattr(_CLIENT_TYPE, "close", observed_close)
    state.closes = closes
    def plans(*responses):
        pending = list(responses)
        def next_response():
            assert pending, "unexpected replacement request"
            state.native.response_status, state.native.response = pending.pop(0)
        state.native.on_upstream = next_response
    state.plans = plans
    state.factory = lambda lane: owner.make_application_fabric_factory(
        mode_id="shared_fabric", lane=lane, root=state.root,
        workload_cfg={"provider_order": ["fabric"], "workload_profile": "site_interactive"})
    state.admin = lambda: admin.chat("Explain the pipeline state.", root=state.root,
        fabric_selected=True, fabric_provider_factory=state.factory("admin-orchestrator"),
        request_id="admin:original-turn")
    state.ask = lambda: ask.ask("What is the current macro regime?", user_id="native-caller",
        root=state.root, fabric_selected=True, fabric_provider_factory=state.factory("ask-brain"))
    state.brief = lambda **cfg: brief.synthesize({"macro": {"date": "2026-11-04"}},
        root=state.root, cfg={"max_tokens": 1000, "emit_theses": False, **cfg})
    return state


def test_admin_original_identity_two_steps_and_one_same_binding_close(callers):
    state = callers
    state.plans((200, packet(None, tool="read_health")), (200, packet()))
    result = state.admin()
    assert not result["degraded"] and result["usage_state"] == "known"
    assert result["tool_call_census"] == {"read_health": 1}
    requests = state.native.rows("application_requests")
    assert {row["turn_id"] for row in requests} == {"admin:original-turn"}
    assert [row["request_id"] for row in requests] == [
        "admin:original-turn:orchestrator:0", "admin:original-turn:orchestrator:1"]
    assert state.closes == ["admin:original-turn"]
    assert state.native.rows("leases")[0]["state"] == "released"
    assert len(state.costs) == 1 and state.costs[0]["input_tokens"] == 22


@pytest.mark.parametrize("model", [MODEL, "other-model", None])
def test_admin_terminal_failure_keeps_actual_model_and_known_usage(callers, model):
    state = callers
    state.plans((503 if model != "other-model" else 200, packet(model=model)))
    result = state.admin()
    assert result["degraded"] and result["usage_state"] == "known"
    assert result["input_tokens"] == 11
    assert len(state.costs) == len(state.native.posts) == len(state.closes) == 1
    assert state.costs[0]["model"] == model and state.costs[0]["input_tokens"] == 11
    assert state.native.rows("leases")[0]["state"] == "released"


def test_admin_unknown_commit_keeps_known_observation_and_original_hold(callers, monkeypatch):
    state = callers
    state.plans((200, packet()))
    monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    result = state.admin()
    assert result["usage_state"] == "unknown" and result["input_tokens"] is None
    assert result["completed_step_usage"]["input_tokens"] == 11
    assert len(state.costs) == len(state.native.posts) == len(state.closes) == 1
    assert state.costs[0]["note"] == admin._FABRIC_PARTIAL_KNOWN_NOTE
    assert state.native.rows("application_requests")[0]["state"] == "unknown"
    assert state.native.rows("leases")[0]["state"] in {"held", "rented"}


@pytest.mark.parametrize("request_id", [" admin:original-turn ", "admin/original-turn"])
def test_admin_invalid_original_identity_refuses_before_credentials(callers, monkeypatch, request_id):
    state = callers
    secret = Mock(side_effect=AssertionError("credential before identity validation"))
    monkeypatch.setattr(owner, "_resolve_credential", secret)
    result = admin.chat("Explain the pipeline state.", root=state.root,
        fabric_selected=True, fabric_provider_factory=state.factory("admin-orchestrator"),
        request_id=request_id)
    assert result["degraded"]
    secret.assert_not_called()
    assert state.native.posts == state.costs == state.closes == []
    assert state.native.rows("leases") == []


@pytest.mark.parametrize("synthesis", [False, True])
def test_admin_local_tool_refusal_preserves_native_terminal_usage(callers, monkeypatch, synthesis):
    state = callers
    dispatched = []
    dispatch = admin._dispatch_tool
    def observed_dispatch(name, *args):
        dispatched.append(name)
        return dispatch(name, *args)
    monkeypatch.setattr(admin, "_dispatch_tool", observed_dispatch)
    first = packet(None, tool="read_health")
    second = packet(None, tool="read_health")
    if synthesis:
        monkeypatch.setattr(admin, "_MAX_TOOL_CALLS", 1)
        second["choices"][0]["message"]["tool_calls"][0]["id"] = "unsolicited-2"
    state.plans((200, first), (200, second))
    result = state.admin()
    assert result["degraded"] and result["reason"] == "fabric_tool_call_malformed"
    assert result["usage_state"] == "known" and result["input_tokens"] == 22
    assert dispatched == ["read_health"]
    assert len(state.costs) == 1 and state.costs[0]["input_tokens"] == 22
    assert len(state.native.posts) == 2 and state.closes == ["admin:original-turn"]
    assert state.native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("boundary", ["rate", "history", "accounting"])
def test_admin_all_postbind_boundaries_close_once(callers, monkeypatch, boundary):
    state = callers
    state.plans((200, packet()))
    if boundary == "rate":
        monkeypatch.setattr(admin, "_rate_ok", lambda: False)
        assert state.admin()["reason"] == "rate_cap"
    else:
        method = "_sanitize_history" if boundary == "history" else "_fabric_account_turn"
        monkeypatch.setattr(admin, method, Mock(side_effect=RuntimeError("boundary")))
        with pytest.raises(RuntimeError, match="boundary"):
            state.admin()
    assert state.closes == ["admin:original-turn"]
    assert len(state.native.posts) == (1 if boundary == "accounting" else 0)
    if boundary != "accounting":
        assert state.native.rows("leases") == []


@pytest.mark.parametrize("local", [False, True])
def test_ask_two_actual_models_use_shared_grouped_writer_and_local_zero(callers, monkeypatch, local):
    state = callers
    if local:
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1",
                            replace(state.transport, cost_basis="local"))
        state.row["cost_basis"] = "local"
        state.save()
    state.plans((200, packet(None, tool="read_world_state")), (200, packet(model="other-model")))
    result = state.ask()
    assert result["mode"] == "unavailable" and result["usage"]["input_tokens"] == 22
    assert [row["model"] for row in state.costs] == [MODEL, "other-model"]
    assert all(row["lane"] == "ask-brain" and row["input_tokens"] == 11 for row in state.costs)
    if local:
        assert all(row["est_cost_usd"] == 0.0 for row in state.costs)
    assert len(state.native.posts) == 2 and len(state.closes) == 1
    assert len(state.native.rows("leases")) == 1
    assert state.native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("failure", ["unknown_model", "unknown_commit"])
def test_ask_retains_known_error_observation_without_inventing_identity(callers, monkeypatch, failure):
    state = callers
    actual = None if failure == "unknown_model" else MODEL
    state.plans((503 if failure == "unknown_model" else 200, packet(model=actual)))
    if failure == "unknown_commit":
        monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    result = state.ask()
    assert result["mode"] == "unavailable"
    assert (result["usage"]["usage_state"] == "unknown") is (failure == "unknown_commit")
    assert len(state.costs) == len(state.native.posts) == len(state.closes) == 1
    assert state.costs[0]["model"] == actual and state.costs[0]["input_tokens"] == 11


def test_ai_brief_cache_hit_reads_no_credential_or_client_and_closes_no_binding(callers, monkeypatch):
    state = callers
    state.plans((200, packet(_brief_reply())))
    first = state.brief()
    assert first["served_by"] == "go" and len(state.closes) == 1
    secret = Mock(side_effect=AssertionError("credential on cache hit"))
    monkeypatch.setattr(owner, "_resolve_credential", secret)
    second = state.brief()
    assert second["served_by"] == "cache" and second["summary"] == first["summary"]
    secret.assert_not_called()
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 1


@pytest.mark.parametrize("rewrite", [False, True])
def test_ai_brief_truncated_native_result_never_becomes_clean_cache(callers, rewrite):
    state = callers
    truncated = packet(_brief_reply())
    truncated["choices"][0]["finish_reason"] = "length"
    plans = [(200, packet(_brief_reply("neural_web conditions.")))] if rewrite else []
    state.plans(*plans, (200, truncated))
    result = state.brief()
    assert result["summary"] == "Measured conditions remain mixed."
    assert result["degraded_reason"] == "truncated"
    assert len(state.native.posts) == (2 if rewrite else 1)
    assert len(state.closes) == 1
    assert not list((state.root / "data/master_brain/reply_cache").glob("*.txt"))
    assert state.native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("changed", ["endpoint", "protocol", "workload", "output"])
def test_ai_brief_same_model_cache_identity_includes_transport_policy_and_output(callers, monkeypatch, changed):
    state = callers
    state.plans((200, packet(_brief_reply())))
    assert state.brief()["served_by"] == "go"
    cfg = {}
    if changed in {"endpoint", "protocol"}:
        update = {"base_url": "http://127.0.0.1:50142/v1"} if changed == "endpoint" else {"protocol": transport.LEGACY_PROTOCOL}
        replacement = replace(state.transport, **update)
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", replacement)
        state.row.update({key: getattr(replacement, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
        state.save()
    elif changed == "workload":
        cfg["workload_profile"] = "site_interactive"
    else:
        cfg["max_tokens"] = 1100
    secret = Mock(side_effect=RuntimeError("no second binding"))
    monkeypatch.setattr(owner, "_resolve_credential", secret)
    second = state.brief(**cfg)
    assert second["served_by"] != "cache" and second["degraded_reason"]
    secret.assert_called_once()
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 1


def test_ai_brief_cold_fill_refuses_inspection_race_before_credential(callers, monkeypatch):
    state = callers
    def change_after_inspection(*args):
        replacement = replace(state.transport, base_url="http://127.0.0.1:50142/v1")
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", replacement)
        state.row["base_url"] = replacement.base_url
        state.save()
        return None
    monkeypatch.setattr(brief, "_mb_reply_cache_get", change_after_inspection)
    secret = Mock(side_effect=AssertionError("credential before inspection comparison"))
    monkeypatch.setattr(owner, "_resolve_credential", secret)
    result = state.brief()
    assert result["degraded_reason"] and result["served_by"] is None
    secret.assert_not_called()
    assert state.native.posts == state.costs == state.closes == []
    assert state.native.rows("leases") == []
    assert not list((state.root / "data/master_brain/reply_cache").glob("*.txt"))
