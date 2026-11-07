"""Actual public Cold Read -> shared owner/client -> pinned native B/A.

Qualification, credentials, account data and upstream answers are isolated
fixtures. The memo, policy, operation, usage capture and native effects are real.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
import re
import threading
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine import provider_production_modes as owner
from engine.marketing import cold_read as cold
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
CLIENT = transport.FabricInferenceClient
POST = "More info on this - a supplied economic release"
VERDICT = {"blocked": True, "category": "dangling_reference", "reason": "no antecedent"}


def packet(text=None):
    return {"model": MODEL, "choices": [{"index": 0, "finish_reason": "stop",
        "message": {"role": "assistant", "content": text if text is not None else json.dumps(VERDICT)}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


@pytest.fixture
def screen(selected, monkeypatch):
    state = selected
    cold._MEMO.clear();cold.reset_run_budget()
    state.manifest["capabilities"][0]["allowed_lanes"].append("marketing-cold-read")
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    monkeypatch.setattr(cold, "_providers", Mock(side_effect=AssertionError("legacy provider discovery")))
    state.cfg = {"enabled": True, "model_id": "unrelated-legacy-model", "max_tokens": 500}
    state.native.response = packet()
    state.operations, state.closes = [], []
    original_begin, original_close = auth.begin_operation, CLIENT.close

    def begin(*args, **kwargs):
        operation = original_begin(*args, **kwargs)
        state.operations.append((operation, tuple(operation.providers)))
        return operation

    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)

    monkeypatch.setattr(auth, "begin_operation", begin)
    monkeypatch.setattr(CLIENT, "close", close)
    state.run = lambda text=POST, **kwargs: cold.cold_read_verdict(text,
        provenance=kwargs.pop("provenance", "press_lane"), cfg=state.cfg, **kwargs)
    yield state
    cold._MEMO.clear();cold.reset_run_budget()


def closed(state, count):
    assert len(state.operations) == len(state.closes) == count
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)
    assert all(re.fullmatch(r"app:[0-9a-f]{32}", identifier) for identifier in state.closes)


def test_public_selected_cold_and_warm_use_actual_identity_and_no_warm_effect(screen, monkeypatch):
    state = screen
    first = state.run(_call=Mock(side_effect=AssertionError("native caller seam")))
    assert first == {**VERDICT, "mode": "read", "action": "shadow"}
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["max_tokens"] == 200
    assert request["messages"][0]["content"] == cold.prompt_for(POST)[0]
    assert request["messages"][1]["content"] == cold.prompt_for(POST)[1]
    assert "tools" not in request and request["stream"] is False
    assert len(state.costs) == 1 and state.costs[0]["model"] == MODEL
    assert state.costs[0]["lane"] == "marketing-cold-read" and state.costs[0]["stage"] == "marketing_cold_read"
    provider = state.operations[0][1][0]
    assert provider["client"]._client._timeout == 30.0
    entry = cold._MEMO[cold._text_key(POST)]
    assert entry["evidence"]["model"] == MODEL and entry["evidence"]["usage"]["input_tokens"] == 11
    # JSON serialization rejects retained factories, clients or live operations.
    json.dumps(cold._MEMO)
    events = list(state.events)
    monkeypatch.setattr(owner, "_resolve_credential", Mock(side_effect=AssertionError("warm credential")))
    state.cfg["action"] = "hold"
    assert state.run() == {**first, "action": "hold"}
    assert state.events == events and len(state.native.posts) == len(state.costs) == 1
    assert cold._reads_this_run == 1
    assert state.native.rows("leases")[0]["state"] == "released"
    closed(state, 1)


@pytest.mark.parametrize("gate", ["config", "environment", "lane", "empty"])
def test_disarmed_or_out_of_scope_never_inspects_or_binds(screen, monkeypatch, gate):
    state = screen
    monkeypatch.setattr(owner.ApplicationFabricFactory, "inspect", Mock(side_effect=AssertionError("disarmed inspection")))
    if gate == "config": state.cfg["enabled"] = False
    elif gate == "environment": monkeypatch.delenv("MARKETING_LLM_ENABLED")
    result = state.run("" if gate == "empty" else POST,
                       provenance="content_studio" if gate == "lane" else "press_lane")
    assert not result["blocked"] and result["mode"] in {"off", "skipped"}
    assert state.events == state.native.posts == state.operations == state.costs == []


@pytest.mark.parametrize("value", [None, "", "UNKNOWN"])
def test_invalid_present_selection_precedes_native_memo_or_credential_discovery(screen, monkeypatch, value):
    state = screen
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg[auth.APPLICATION_MODE_CFG_KEY] = value
    cold._MEMO[cold._text_key(POST)] = {**VERDICT, "mode": "read"}
    assert state.run()["mode"] == "unavailable"
    assert state.events == state.native.posts == state.operations == []


@pytest.mark.parametrize("value", [None, "", "development_agent", "fable_orchestration"])
def test_invalid_or_native_agent_profile_cannot_serve_a_selected_warm_entry(screen, value):
    state = screen
    assert state.run()["mode"] == "read"
    events = list(state.events)
    state.cfg["workload_profile"] = value
    result = state.run()
    assert result["mode"] == "unavailable" and not result["blocked"]
    assert state.events == events and len(state.native.posts) == 1
    closed(state, 1)


def test_permission_revocation_prevents_warm_reuse(screen):
    state = screen
    state.run();events = list(state.events)
    state.row["application_allowed"] = False;state.save()
    assert state.run()["mode"] == "unavailable"
    assert state.events == events and len(state.native.posts) == 1


def test_native_memo_is_not_relabelled_and_actual_identity_change_refills(screen, monkeypatch):
    state = screen
    cold._MEMO[cold._text_key(POST)] = {"blocked": False, "category": "none", "reason": "", "mode": "read"}
    assert state.run()["blocked"]
    changed = replace(state.transport, cap_id="fabric:changed")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", changed)
    state.row["cap_id"] = changed.cap_id;state.save()
    assert state.run()["blocked"]
    assert len(state.native.posts) == 2 and len(set(state.closes)) == 2


def test_identity_change_between_inspection_and_binding_stops_before_credentials(screen, monkeypatch):
    state = screen
    original = owner.ApplicationFabricFactory.with_inspection
    def change(factory, identity):
        narrowed = original(factory, identity)
        changed = replace(state.transport, cap_id="fabric:changed")
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", changed)
        state.row["cap_id"] = changed.cap_id;state.save()
        return narrowed
    monkeypatch.setattr(owner.ApplicationFabricFactory, "with_inspection", change)
    assert state.run()["mode"] == "unavailable"
    assert state.events == state.native.posts == state.operations == state.costs == []


@pytest.mark.parametrize("change", ["prompt", "tokens", "timeout"])
def test_completed_cache_commits_prompt_and_request_settings(screen, monkeypatch, change):
    state = screen
    state.run()
    if change == "prompt": monkeypatch.setattr(cold, "_SYSTEM", cold._SYSTEM + "\nSame bounded task.")
    elif change == "tokens": state.cfg["max_tokens"] = 100
    else: state.cfg["client_timeout_s"] = 10
    assert state.run()["mode"] == "read" and len(state.native.posts) == 2
    assert cold._reads_this_run == 2


def test_racing_same_text_has_one_binding_one_budget_charge_and_no_waiting_queue(screen):
    state = screen
    state.native.block = threading.Event()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(state.run)
            assert state.native.arrived.wait(2)
            second = state.run()
            assert second["mode"] == "unavailable" and not second["blocked"]
            assert cold._reads_this_run == 1 and len(state.operations) == 1
            state.native.block.set()
            assert first.result(timeout=3)["mode"] == "read"
    finally:
        state.native.block.set()
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state, 1)


def test_unknown_original_survives_reset_selector_removal_and_eviction_pressure(screen, monkeypatch):
    state = screen
    monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    first = state.run()
    assert first["mode"] == "unavailable" and first["reason"] == "fabric_operation_unresolved"
    original = cold._MEMO[cold._text_key(POST)]
    assert original["_read_state"] == "held"
    cold.reset_run_budget()
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    for i in range(cold._MEMO_CAP - 1):
        cold._MEMO[str(i)] = {"blocked": False, "category": "none", "reason": "", "mode": "read"}
    assert state.run() == first
    # A native-only completed insertion may evict completed rows, never the hold.
    state.cfg["env_gate"] = ""
    assert state.run("different supplied text", _call=lambda *_: '{"blocked":false}')["mode"] == "read"
    assert cold._MEMO[cold._text_key(POST)] is original
    state.cfg[auth.APPLICATION_MODE_CFG_KEY] = ""
    assert state.run()["mode"] == "unavailable"
    assert len(state.native.posts) == len(state.operations) == len(state.costs) == 1
    assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
    json.dumps(cold._MEMO)


def test_full_unresolved_memo_refuses_new_reads_without_evicting(screen, monkeypatch):
    state = screen
    monkeypatch.setattr(cold, "_MEMO_CAP", 1)
    monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    state.run();cold.reset_run_budget()
    events = list(state.events)
    result = state.run("another supplied text")
    assert result["mode"] == "unavailable" and result["reason"] == "unresolved_read_memo_full"
    assert state.events == events and len(state.native.posts) == 1 and len(cold._MEMO) == 1
    assert cold._reads_this_run == 0


@pytest.mark.parametrize("fault", ["empty", "blank", "tools", "refusal", "truncated", "http",
                                  "mismatch", "invalid-json", "unrecognized-veto"])
def test_unusable_completion_is_unavailable_and_never_automatically_reasked(screen, fault):
    state = screen
    response = packet();choice = response["choices"][0]
    if fault == "empty": choice["message"]["content"] = ""
    elif fault == "blank": choice["message"]["content"] = "  "
    elif fault == "tools":
        choice["finish_reason"] = "tool_calls"
        choice["message"]["tool_calls"] = [{"id": "tool1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]
    elif fault == "refusal": choice["finish_reason"] = "content_filter"
    elif fault == "truncated": choice["finish_reason"] = "length"
    elif fault == "http": state.native.response_status = 503
    elif fault == "mismatch": response["model"] = "unexpected-model"
    elif fault == "invalid-json": choice["message"]["content"] = "unusable prose"
    else: choice["message"]["content"] = '{"blocked":true,"category":"tone","reason":"too dry"}'
    state.native.response = response
    for _ in range(2):
        result = state.run()
        assert not result["blocked"] and result["mode"] == "unavailable"
    assert len(state.native.posts) == len(state.operations) == 1
    closed(state, 1)


def test_known_response_with_unknown_usage_is_not_an_uncertain_effect(screen):
    state = screen
    state.native.response["usage"]["completion_tokens"] = None
    assert state.run()["mode"] == "read"
    entry = cold._MEMO[cold._text_key(POST)]
    assert entry["_read_state"] == "complete" and entry["evidence"]["model"] == MODEL
    assert entry["evidence"]["usage"]["usage_state"] == "unknown"
    assert entry["evidence"]["usage"]["input_tokens"] is None and state.costs == []
    assert state.run()["mode"] == "read" and len(state.native.posts) == 1
    assert state.native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("usage_known", [True, False])
def test_close_unknown_preserves_valid_verdict_under_fresh_same_identity(screen, monkeypatch, usage_known):
    state = screen
    if not usage_known:
        state.native.response["usage"]["completion_tokens"] = None
    monkeypatch.setattr(CLIENT, "close", Mock(side_effect=OSError("close acknowledgement lost")))
    first = state.run()
    assert first["mode"] == "read" and first["blocked"]
    entry = cold._MEMO[cold._text_key(POST)]
    assert entry["_read_state"] == "held" and entry["evidence"]["model"] == MODEL
    assert entry["evidence"]["usage"]["input_tokens"] == (11 if usage_known else None)
    assert state.run() == first and len(state.native.posts) == 1
    assert len(state.costs) == (1 if usage_known else 0)
    state.row["application_allowed"] = False;state.save()
    assert state.run()["mode"] == "unavailable"
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert state.run()["mode"] == "unavailable" and len(state.native.posts) == 1
    assert cold._MEMO[cold._text_key(POST)] is entry


def test_prebind_credential_absence_does_not_cache_unavailability_after_recovery(screen, monkeypatch):
    state = screen
    monkeypatch.delenv(state.native.service.credential_ref)
    assert state.run()["mode"] == "unavailable"
    assert cold._text_key(POST) not in cold._MEMO and cold._reads_this_run == 1
    assert state.operations == state.native.posts == []
    monkeypatch.setenv(state.native.service.credential_ref, state.native.service.credential)
    assert state.run()["mode"] == "read"
    assert cold._reads_this_run == 2 and len(state.native.posts) == 1
    closed(state, 1)


def test_original_receipt_only_supplies_no_verdict_and_no_replacement_completion(screen, monkeypatch):
    state = screen
    monkeypatch.setattr(cold.secrets, "token_hex", lambda _n: "a" * 32)
    assert state.run()["mode"] == "read"
    cold._MEMO.clear()  # Explicit test of a new local process's absent memo.
    assert state.run()["mode"] == "unavailable"
    entry = cold._MEMO[cold._text_key(POST)]
    assert entry["_read_state"] == "complete"
    assert entry["evidence"]["native_disposition"] == "terminal_receipt_only"
    assert entry["evidence"]["model"] is None
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state, 2)


def test_per_run_budget_and_distinct_text_operations_remain_bounded(screen):
    state = screen
    state.cfg["max_reads_per_run"] = 1
    assert state.run()["mode"] == "read"
    assert state.run("second supplied text")["mode"] == "budget_exhausted"
    cold.reset_run_budget()
    assert state.run("second supplied text")["mode"] == "read"
    assert len(set(state.closes)) == len(state.native.posts) == 2


@pytest.mark.parametrize("key,value", [("max_tokens", 0), ("max_tokens", True), ("max_tokens", None),
    ("client_timeout_s", 0), ("client_timeout_s", True), ("client_timeout_s", float("nan"))])
def test_invalid_request_boundaries_refuse_before_credential_or_memo_claim(screen, key, value):
    state = screen
    state.cfg[key] = value
    assert state.run()["mode"] == "unavailable"
    assert state.events == state.operations == state.native.posts == [] and cold._reads_this_run == 0
