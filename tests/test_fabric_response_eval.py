"""Response evaluation through the real shared Fabric owner and native B/A.

Only qualification, credentials and upstream responses are synthetic. The
parser, callback lifecycle, SQLite settlement and shared usage sink stay real.
"""
import json
import os
import re
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine.neuralweb import response_eval as ev
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
_CLIENT = transport.FabricInferenceClient
REQUESTED = "requested-deepseek-model"
JUDGEMENT = json.dumps({"scores": ev.RUBRIC, "tags": [], "note": "Supplied context only."})
ANSWER = "Supplied evidence is incomplete. Watch the stated conditions."


def packet(text, *, model=MODEL, finish="stop", tool=False):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "unsolicited-1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
        finish = "tool_calls"
    return {"model": model, "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


@pytest.fixture
def evaluation(selected, monkeypatch):
    state = selected
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    state.fast = {}
    monkeypatch.setattr(ev, "_brain_fast_lane", lambda _root: dict(state.fast))
    state.closes, state.operations = [], []
    original_close, original_begin = _CLIENT.close, auth.begin_operation

    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)

    def begin(*args, **kwargs):
        operation = original_begin(*args, **kwargs)
        state.operations.append((operation, tuple(operation.providers)))
        return operation

    monkeypatch.setattr(_CLIENT, "close", close)
    monkeypatch.setattr(auth, "begin_operation", begin)

    def plans(*responses):
        pending = list(responses)
        def upstream():
            assert pending, "unexpected additional provider step"
            state.native.response_status, state.native.response = pending.pop(0)
        state.native.on_upstream = upstream
    state.plans = plans
    state.judge = ev.judge_via_llm_auth(state.root, model=REQUESTED)
    state.answer = ev.answer_via_llm_auth(state.root, model=REQUESTED)
    return state


def closed(state, count):
    assert len(state.operations) == len(state.closes) == count
    assert all(re.fullmatch(r"app:[0-9a-f]{32}", value) for value in state.closes)
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


def invoke(state, caller):
    return state.judge("Grade the supplied answer.") if caller == "judge" else state.answer("Frozen doctrine.", "Frozen packet.")


def row():
    return {"id": "fixture-evaluation", "question": "What does the supplied evidence show?",
            "answer": ANSWER, "lane": "fast", "lang": "en", "flags": {}}


def test_factories_are_pure_and_selected_judgement_uses_observed_model(evaluation):
    state = evaluation
    assert state.judge.model_id == state.answer.model_id == ""
    assert state.events == state.operations == state.closes == state.costs == state.native.posts == []
    assert state.native.rows("leases") == []
    state.plans((200, packet(JUDGEMENT)))
    result = ev.score_response(row(), state.judge)
    assert result["judged"] and result["judged_at_model"] == MODEL != REQUESTED
    assert result["total"] == 100
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["model"] == MODEL and state.costs[0]["stage"] == "response_eval_judge"
    assert state.costs[0]["input_tokens"] == 11
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["max_tokens"] == ev.JUDGE_MAX_TOKENS
    assert request["stream"] is False and "tools" not in request
    closed(state, 1)


def test_parse_reask_is_two_steps_on_one_original_turn_account_and_binding(evaluation):
    state = evaluation
    state.plans((200, packet("Complete but not JSON.")), (200, packet(JUDGEMENT)))
    assert state.judge("Grade.") == JUDGEMENT and state.judge.model_id == MODEL
    closed(state, 1)
    requests, leases = state.native.rows("application_requests"), state.native.rows("leases")
    assert len(requests) == len(state.native.posts) == len(state.costs) == 2
    assert len(leases) == 1 and leases[0]["state"] == "released"
    assert {request["turn_id"] for request in requests} == {state.closes[0]}
    assert {request["request_id"] for request in requests} == {state.closes[0] + ":brain:0", state.closes[0] + ":brain:1"}
    assert all(post[2] == "Bearer fixture-provider-a" for post in state.native.posts)
    assert all(cost["input_tokens"] == 11 and cost["output_tokens"] == 7 and cost["model"] == MODEL
               for cost in state.costs)
    assert auth.fabric_usage(state.operations[0][1][0])["input_tokens"] == 22


def test_second_parse_failure_returns_none_without_a_third_step(evaluation):
    state = evaluation
    state.plans((200, packet("First non-JSON text.")), (200, packet("Second non-JSON text.")))
    assert state.judge("Grade.") is None and state.judge.model_id == ""
    assert len(state.native.posts) == len(state.costs) == 2
    closed(state, 1)


@pytest.mark.parametrize("caller", ["judge", "answer"])
def test_native_socket_deadline_does_not_turn_timeout_into_parse_reask(evaluation, monkeypatch, caller):
    state = evaluation
    state.native.slow = True
    monkeypatch.setattr(state.native.go, "APPLICATION_IO_TIMEOUT_S", 0.08)
    assert invoke(state, caller) is None and getattr(state, caller).model_id == ""
    assert len(state.native.posts) == 1 and state.costs == []
    assert state.native.rows("application_requests")[0]["state"] == "unknown"
    provider = state.operations[0][1][0]
    assert auth.fabric_usage(provider)["input_tokens"] is None
    assert not provider["_fabric_close"]["closed"]
    closed(state, 1)


@pytest.mark.parametrize("caller", ["judge", "answer"])
@pytest.mark.parametrize("failure", ["empty", "blank", "tools", "refusal", "truncated", "http", "mismatch", "unknown"])
def test_terminal_or_uncertain_response_never_authorizes_parse_reask(evaluation, monkeypatch, caller, failure):
    state = evaluation
    response = packet(JUDGEMENT if caller == "judge" else ANSWER)
    choice = response["choices"][0]
    if failure == "empty": choice["message"]["content"] = ""
    elif failure == "blank": choice["message"]["content"] = "  "
    elif failure == "tools": choice.update(packet(None, tool=True)["choices"][0])
    elif failure == "refusal": choice["finish_reason"] = "content_filter"
    elif failure == "truncated": choice["finish_reason"] = "length"
    elif failure == "mismatch": response["model"] = "different-observed-model"
    state.plans((503 if failure == "http" else 200, response))
    if failure == "unknown":
        monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before settlement")))
    assert invoke(state, caller) is None and getattr(state, caller).model_id == ""
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["model"] == ("different-observed-model" if failure == "mismatch" else MODEL)
    assert state.costs[0]["input_tokens"] == 11
    closed(state, 1)
    if failure == "unknown":
        assert state.native.rows("application_requests")[0]["state"] == "unknown"
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        provider = state.operations[0][1][0]
        assert auth.fabric_usage(provider)["input_tokens"] is None
        assert not provider["_fabric_close"]["closed"]
    else:
        assert state.native.rows("application_requests")[0]["state"] == "terminal"
        assert state.native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("observed_second_usage", [True, False])
def test_second_step_unknown_preserves_observed_subtotals_and_original_hold(evaluation, monkeypatch, observed_second_usage):
    state = evaluation
    second = packet(JUDGEMENT)
    if not observed_second_usage:
        second["usage"] = {"prompt_tokens": None, "completion_tokens": None}
    state.plans((200, packet("Not JSON.")), (200, second))
    original = state.native.gateway.complete_application
    completed = []
    def complete(*args, **kwargs):
        completed.append(True)
        if len(completed) == 2:
            raise OSError("second step before settlement")
        return original(*args, **kwargs)
    monkeypatch.setattr(state.native.gateway, "complete_application", complete)
    assert state.judge("Grade.") is None and state.judge.model_id == ""
    assert len(state.native.posts) == len(completed) == 2
    assert len(state.costs) == (2 if observed_second_usage else 1)
    provider = state.operations[0][1][0]
    usage = auth.fabric_usage(provider)
    assert usage["input_tokens"] is None and usage["output_tokens"] is None
    assert usage["completed_input_tokens"] == (22 if observed_second_usage else 11)
    assert usage["completed_output_tokens"] == (14 if observed_second_usage else 7)
    assert not provider["_fabric_close"]["closed"]
    assert len(state.native.rows("leases")) == 1
    assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
    closed(state, 1)


def test_complete_text_with_nullable_usage_may_reask_without_fabricating_zero(evaluation):
    state = evaluation
    first = packet("Not JSON.")
    first["usage"]["prompt_tokens"] = None
    state.plans((200, first), (200, packet(JUDGEMENT)))
    assert state.judge("Grade.") == JUDGEMENT
    assert len(state.native.posts) == 2 and len(state.costs) == 1
    assert auth.fabric_usage(state.operations[0][1][0])["input_tokens"] is None
    assert state.judge.model_id == MODEL
    closed(state, 1)


@pytest.mark.parametrize("caller", ["judge", "answer"])
def test_receipt_only_recovery_has_no_second_answer_usage_or_parse_reask(evaluation, monkeypatch, caller):
    state = evaluation
    monkeypatch.setattr(auth.secrets, "token_hex", lambda _length: "d" * 32)
    state.plans((200, packet(JUDGEMENT if caller == "judge" else ANSWER)))
    assert invoke(state, caller) is not None and getattr(state, caller).model_id == MODEL
    assert invoke(state, caller) is None and getattr(state, caller).model_id == ""
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    closed(state, 2)


def test_independent_judgements_are_fresh_and_later_failure_clears_serving_evidence(evaluation, monkeypatch):
    state = evaluation
    state.plans((200, packet(JUDGEMENT)), (200, packet(JUDGEMENT)), (503, packet(JUDGEMENT)))
    assert ev.score_response(row(), state.judge)["judged_at_model"] == MODEL
    assert ev.score_response(row(), state.judge)["judged_at_model"] == MODEL
    failed = ev.score_response(row(), state.judge)
    assert not failed["judged"] and failed["judged_at_model"] == ""
    assert len(set(state.closes)) == len(state.native.posts) == len(state.costs) == 3
    assert len({id(providers[0]["client"]) for _, providers in state.operations}) == 3
    closed(state, 3)
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    assert not ev.score_response(row(), state.judge)["judged"] and state.judge.model_id == ""
    assert len(state.native.posts) == 3


def test_answer_is_one_frozen_request_with_actual_model_and_no_stale_success(evaluation, monkeypatch):
    state = evaluation
    state.plans((200, packet(ANSWER)), (503, packet(ANSWER)))
    assert state.answer("Frozen doctrine.", "Frozen packet.") == ANSWER
    assert state.answer.model_id == MODEL
    request = json.loads(state.native.posts[0][1])
    assert request["messages"] == [{"role": "system", "content": "Frozen doctrine."},
                                   {"role": "user", "content": "Frozen packet."}]
    assert request["max_tokens"] == ev.BENCHMARK_MAX_TOKENS and "tools" not in request
    assert state.answer("Frozen doctrine.", "Frozen packet.") is None
    assert state.answer.model_id == "" and len(state.native.posts) == 2
    assert all(cost["stage"] == "response_eval_benchmark" for cost in state.costs)
    closed(state, 2)
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    assert state.answer("Frozen doctrine.", "Frozen packet.") is None and state.answer.model_id == ""
    assert len(state.native.posts) == 2


def test_direct_selected_one_shot_preserves_shape_and_owns_one_operation(evaluation):
    state = evaluation
    state.plans((200, packet(ANSWER)))
    cfg = ev._llm_cfg(state.root, model=REQUESTED, fallback_model="requested-backup")
    assert ev._one_shot(cfg, "Frozen doctrine.", "Frozen packet.", max_tokens=73,
                        context="response_eval_benchmark") == ANSWER
    assert "workload_profile" not in cfg
    assert len(state.native.posts) == len(state.costs) == 1
    assert json.loads(state.native.posts[0][1])["max_tokens"] == 73
    closed(state, 1)


@pytest.mark.parametrize("caller", ["judge", "answer"])
@pytest.mark.parametrize("mode", ["", "UNKNOWN", "missing_mode"])
def test_invalid_host_selection_never_discovers_native_credentials(evaluation, monkeypatch, caller, mode):
    state = evaluation
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, mode)
    assert invoke(state, caller) is None and getattr(state, caller).model_id == ""
    assert state.events == state.closes == state.native.posts == state.costs == []
    assert state.native.rows("leases") == []


@pytest.mark.parametrize("caller", ["judge", "answer"])
@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_explicit_invalid_profile_is_preserved_and_never_binds(evaluation, caller, profile):
    state = evaluation
    state.fast["workload_profile"] = profile
    state.judge = ev.judge_via_llm_auth(state.root, model=REQUESTED)
    state.answer = ev.answer_via_llm_auth(state.root, model=REQUESTED)
    cfg = ev._llm_cfg(state.root, model=REQUESTED, fallback_model="requested-backup")
    assert cfg["workload_profile"] == profile
    assert invoke(state, caller) is None and getattr(state, caller).model_id == ""
    assert state.events == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("caller", ["judge", "answer"])
@pytest.mark.parametrize("mode", [None, "", "UNKNOWN"])
def test_invalid_caller_selection_is_forwarded_without_native_fallback(evaluation, monkeypatch, caller, mode):
    state = evaluation
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.fast[auth.APPLICATION_MODE_CFG_KEY] = mode
    state.judge = ev.judge_via_llm_auth(state.root, model=REQUESTED)
    state.answer = ev.answer_via_llm_auth(state.root, model=REQUESTED)
    assert invoke(state, caller) is None and getattr(state, caller).model_id == ""
    assert state.events == state.closes == state.native.posts == state.costs == []


def test_mode_is_resolved_again_when_native_factory_is_invoked(evaluation, monkeypatch):
    state = evaluation
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    judge = ev.judge_via_llm_auth(state.root, model=REQUESTED)
    assert judge.model_id == REQUESTED
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    state.plans((200, packet(JUDGEMENT)))
    assert judge("Grade.") == JUDGEMENT and judge.model_id == MODEL
    closed(state, 1)


@pytest.mark.parametrize("caller", ["judge", "answer", "one_shot"])
def test_selected_recipe_cannot_discover_native_credentials_after_host_removal(evaluation, monkeypatch, caller):
    state = evaluation
    build = auth.build_providers
    def remove_selection(cfg, **kwargs):
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        return build(cfg, **kwargs)
    monkeypatch.setattr(auth, "build_providers", remove_selection)
    if caller == "one_shot":
        cfg = ev._llm_cfg(state.root, model=REQUESTED, fallback_model="requested-backup")
        result = ev._one_shot(cfg, "", "Grade.", max_tokens=73, context="response_eval_judge")
    else:
        result = invoke(state, caller)
    assert result is None
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("caller", ["judge", "answer"])
def test_selected_outer_invocation_refuses_removal_before_recipe_helper(evaluation, monkeypatch, caller):
    state = evaluation
    providers = ev._eval_providers
    def remove_selection(llm_auth, cfg, **kwargs):
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        return providers(llm_auth, cfg, **kwargs)
    monkeypatch.setattr(ev, "_eval_providers", remove_selection)
    assert invoke(state, caller) is None and getattr(state, caller).model_id == ""
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("caller", ["judge", "answer"])
def test_native_outer_invocation_cannot_switch_to_hidden_fabric_operation(evaluation, monkeypatch, caller):
    state = evaluation
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.judge = ev.judge_via_llm_auth(state.root, model=REQUESTED)
    state.answer = ev.answer_via_llm_auth(state.root, model=REQUESTED)
    original = ev._one_shot
    calls = []
    def enable_selection(cfg, system, user, *, max_tokens, context):
        calls.append(context)
        monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return original(cfg, system, user, max_tokens=max_tokens, context=context)
    monkeypatch.setattr(ev, "_one_shot", enable_selection)
    assert invoke(state, caller) is None
    assert len(calls) == (2 if caller == "judge" else 1)
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []


def test_capability_refusal_never_sends_or_falls_back(evaluation):
    state = evaluation
    state.manifest["capabilities"][0]["kill_state"] = "killed"
    state.save()
    assert state.judge("Grade.") is None and state.judge.model_id == ""
    assert state.native.posts == state.closes == state.costs == []
    assert state.native.rows("leases") == []


def test_native_factory_and_two_attempt_helper_contract_are_preserved(evaluation, monkeypatch):
    state = evaluation
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    calls = []
    def one_shot(cfg, system, user, *, max_tokens, context):
        calls.append((cfg, system, user, max_tokens, context))
        return "Not JSON." if len(calls) == 1 else JUDGEMENT
    monkeypatch.setattr(ev, "_one_shot", one_shot)
    judge = ev.judge_via_llm_auth(state.root, model=REQUESTED)
    assert judge.model_id == REQUESTED and judge("Grade.") == JUDGEMENT
    assert len(calls) == 2 and judge.model_id == REQUESTED
    assert calls[0][0]["provider_order"] == ["deepseek", "anthropic"]
    assert calls[0][0]["codex_provider"] is False and calls[0][0]["client_max_retries"] == 0
    assert calls[0][0]["client_timeout_s"] == ev._JUDGE_TIMEOUT_S
    assert "workload_profile" not in calls[0][0]
    assert state.events == state.closes == state.native.posts == state.costs == []
