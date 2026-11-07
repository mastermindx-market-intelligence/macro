"""Public Hot Tape/reply journeys through the shared owner and actual native B/A."""
import copy
import json
import os
import time
from unittest.mock import Mock

import pytest

from engine import llm_auth as auth
from engine.marketing import hot_tape_llm as hot, reply_voice as reply
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401
from tests.test_fabric_marketing_breaking import packet, observe, closed
from tests.test_marketing_hot_tape_llm import BY_ID
from tests.test_marketing_reply_voice import DRAFT, VOICED, PARENT, WHITELIST


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")


@pytest.fixture(params=["hot", "reply"])
def event(selected, monkeypatch, request):
    state = selected
    state.kind = request.param
    state.module = hot if state.kind == "hot" else reply
    state.lane = "hot-tape-wire" if state.kind == "hot" else "reply-voice"
    state.context = "hot_tape_wire" if state.kind == "hot" else "reply_voice"
    state.manifest["capabilities"][0]["allowed_lanes"].append(state.lane)
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    monkeypatch.setattr(state.module, "_resolve_model_id",
                        Mock(side_effect=AssertionError("native model prerequisite")))
    state.module.reset_stats()
    state.cfg = {"enabled": True, "max_calls_per_run": 25}
    if state.kind == "hot":
        entry = copy.deepcopy(next(iter(BY_ID.values())))
        state.input = entry["packet"]
        state.clean = entry["good_phrasing"]
        state.dirty = "$SNDK seems like it will keep falling."
        state.fallback = "Deterministic engine wire."
        state.run = lambda: hot.phrase_or_fallback(state.input, state.input.get("trigger", "fixture"),
            state.fallback, cfg=state.cfg)
    else:
        state.clean, state.dirty, state.fallback = VOICED, "Spreads widened 13.5% this week.", DRAFT
        state.run = lambda: reply.voice_or_fallback(DRAFT, family="missing_variable", account="kelly",
            parent_text=PARENT, numbers_whitelist=WHITELIST, cfg=state.cfg)
    observe(state, monkeypatch)
    return state


def test_public_consumer_uses_real_selected_operation_and_five_second_budget(event):
    state = event
    state.plans((200, packet(state.clean)))
    result = state.run()
    assert result["mode"] == "llm" and result["text"] == state.clean
    assert result["provider"] == "fabric" and result["violations"] == []
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["stream"] is False and "tools" not in request
    assert state.operations[0][1][0]["client"]._client._timeout == 5.0
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["lane"] == state.lane and state.costs[0]["stage"] == state.context
    assert state.costs[0]["model"] == MODEL and state.costs[0]["input_tokens"] == 11
    closed(state)


@pytest.mark.parametrize("valid", [True, False])
def test_only_one_validator_repair_uses_original_turn_account_and_budget(event, valid):
    state = event
    state.plans((200, packet(state.dirty)), (200, packet(state.clean if valid else state.dirty)))
    result = state.run()
    expected = ("llm_repair" if state.kind == "hot" else "llm") if valid else "fallback_validation"
    assert result["mode"] == expected
    assert result["text"] == (state.clean if valid else state.fallback)
    assert len(state.native.posts) == len(state.costs) == 2
    assert [cost["stage"] for cost in state.costs] == [state.context, state.context + "_repair"]
    assert len({row["turn_id"] for row in state.native.rows("application_requests")}) == 1
    assert len(state.native.rows("leases")) == len({post[2] for post in state.native.posts}) == 1
    assert state.native.rows("leases")[0]["state"] == "released"
    if state.kind == "reply":
        assert reply.fallback_stats()["repairs"] == 1
        assert len(reply._CALL_TIMES) == 2
    else:
        assert hot._CALLS_THIS_RUN == 2
    closed(state)


@pytest.mark.parametrize("failure", ["empty", "blank", "tools", "refusal", "truncated", "http", "mismatch", "unknown"])
@pytest.mark.parametrize("repair", [False, True])
def test_unavailable_completion_never_rebinds_or_gets_an_extra_repair(event, monkeypatch, failure, repair):
    state = event
    response = packet(state.clean)
    choice = response["choices"][0]
    if failure == "empty": choice["message"]["content"] = ""
    elif failure == "blank": choice["message"]["content"] = "  "
    elif failure == "tools": choice.update(packet(None, tool=True)["choices"][0])
    elif failure == "refusal": choice["finish_reason"] = "content_filter"
    elif failure == "truncated": choice["finish_reason"] = "length"
    elif failure == "mismatch": response["model"] = "different-observed-model"
    responses = ([(200, packet(state.dirty))] if repair else []) + [(503 if failure == "http" else 200, response)]
    state.plans(*responses)
    if failure == "unknown":
        original = state.native.on_upstream
        def upstream():
            original()
            if len(state.native.posts) == len(responses):
                monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
        state.native.on_upstream = upstream
    result = state.run()
    assert result["mode"] == ("fallback_validation" if repair else "fallback_provider")
    assert result["text"] == state.fallback
    assert len(state.native.posts) == len(state.costs) == len(responses)
    assert len(state.native.rows("leases")) == 1
    if failure == "unknown":
        assert state.native.rows("application_requests")[-1]["state"] == "unknown"
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    closed(state)


def test_existing_business_call_cap_counts_repair_and_prevents_another_binding(event):
    state = event
    state.cfg["max_calls_per_run"] = 1
    state.plans((200, packet(state.dirty)))
    first = state.run()
    assert first["mode"] == "fallback_validation" and first["text"] == state.fallback
    assert state.run()["mode"] == "fallback_provider"
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state)


def test_distinct_events_have_distinct_operations_and_retained_global_caps(event):
    state = event
    state.plans((200, packet(state.clean)), (200, packet(state.clean)))
    assert state.run()["mode"] == state.run()["mode"] == "llm"
    assert len(set(state.closes)) == len(state.native.rows("leases")) == 2
    if state.kind == "reply": assert len(reply._CALL_TIMES) == 2
    else: assert hot._CALLS_THIS_RUN == 2
    closed(state, 2)


@pytest.mark.parametrize("event", ["reply"], indirect=True)
def test_reply_rolling_window_expires_without_resetting_each_operation(event):
    state = event
    state.cfg.update(max_calls_per_run=1, call_window_s=3600)
    state.plans((200, packet(state.clean)), (200, packet(state.clean)))
    assert state.run()["mode"] == "llm"
    assert state.run()["mode"] == "fallback_provider"
    reply._CALL_TIMES[0] = time.monotonic() - 3601
    assert state.run()["mode"] == "llm" and len(reply._CALL_TIMES) == 1
    closed(state, 2)


@pytest.mark.parametrize("field,value", [("selection", None), ("selection", ""), ("selection", {}),
                                          ("workload_profile", None), ("workload_profile", "")])
def test_explicit_invalid_selection_or_profile_cannot_fall_through_to_native(event, monkeypatch, field, value):
    state = event
    if field == "selection":
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV, raising=False)
    state.cfg[auth.APPLICATION_MODE_CFG_KEY if field == "selection" else field] = value
    assert state.run()["mode"] == "fallback_provider"
    assert state.native.posts == state.costs == state.operations == []


def test_selected_provider_family_cannot_change_during_build(event, monkeypatch):
    state = event
    monkeypatch.setattr(auth, "build_providers", Mock(return_value=[{"name": "oauth", "client": object(), "model": "legacy"}]))
    assert state.run()["mode"] == "fallback_provider"
    assert state.native.posts == state.costs == state.operations == []


def test_disabled_consumer_does_not_select_or_bind(event, monkeypatch):
    state = event
    state.cfg["enabled"] = False
    monkeypatch.setattr(auth, "application_mode_id", Mock(side_effect=AssertionError("disabled selection")))
    assert state.run()["mode"] == "off"
    assert state.native.posts == state.costs == state.operations == []


@pytest.mark.parametrize("repair", [False, True])
def test_validation_exception_keeps_deterministic_output_and_closes_original(event, monkeypatch, repair):
    state = event
    method = "validate_wire_copy" if state.kind == "hot" else "validate_reply_copy"
    original = getattr(state.module, method)
    calls = []
    def validate(*args, **kwargs):
        calls.append(args)
        if len(calls) == (2 if repair else 1): raise ValueError("local validator unavailable")
        return original(*args, **kwargs)
    monkeypatch.setattr(state.module, method, validate)
    state.plans(*(([(200, packet(state.dirty))] if repair else []) + [(200, packet(state.clean))]))
    result = state.run()
    assert result["mode"] == "fallback_validation" and result["text"] == state.fallback
    assert len(state.native.posts) == 1 + int(repair)
    closed(state)
