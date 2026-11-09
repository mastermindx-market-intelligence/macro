"""FOMC's real parser/validator/partial-result contract over selected native B/A."""
import copy
import json
import os
import threading
import time
from unittest.mock import Mock

import pytest

from engine import llm_auth as auth
from engine.marketing import fomc_desk as fomc
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401
from tests.test_fabric_marketing_breaking import packet, observe, closed
from tests.test_marketing_fomc_desk import (  # noqa: F401
    june, july, diff, facts, sheet, CLEAN_ANALYSIS, CLEAN_HOOK, CLEAN_RELAY,
    CLEAN_REPLY, DIRTY_REPLY, _reply, seeded_root, july_page, desk_cfg, NOW, JULY,
)


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
ALL_DIRTY = _reply(["Traders now price a 70 percent chance of a cut."],
                   "A 70 percent probability of a cut.", "A 70 percent probability of a cut.")


@pytest.fixture
def desk(selected, monkeypatch, sheet):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"].append("marketing-fomc")
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    monkeypatch.setattr(fomc, "_resolve_model_id", Mock(side_effect=AssertionError("native model prerequisite")))
    state.cfg = {"fomc_desk": {"llm": {"enabled": True}}}
    state.sheet = sheet
    observe(state, monkeypatch)
    state.run = lambda: fomc.write_copy(state.sheet, cfg=state.cfg)
    return state


def test_public_desk_uses_one_selected_operation_and_real_45_second_budget(desk):
    state = desk
    state.plans((200, packet(CLEAN_REPLY)))
    result = state.run()
    assert result["mode"] == "llm" and result["provider"] == "fabric"
    assert result["analysis"] == CLEAN_ANALYSIS and result["hook"] == CLEAN_HOOK and result["relay"] == CLEAN_RELAY
    assert not any(result["violations"].values()) and result["latency_ms"] >= 0
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["max_tokens"] == fomc.DEFAULT_MAX_TOKENS
    assert request["messages"][0]["content"] == fomc.build_system_prompt()
    assert request["messages"][1]["content"] == fomc.build_user_message(state.sheet)
    assert "tools" not in request and request["stream"] is False
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["lane"] == "marketing-fomc" and state.costs[0]["stage"] == "fomc_desk"
    assert state.costs[0]["model"] == MODEL and state.costs[0]["input_tokens"] == 11
    assert state.operations[0][1][0]["client"]._client._timeout == 45
    closed(state)


@pytest.mark.parametrize("repair,mode", [(CLEAN_REPLY, "llm_repair"), (DIRTY_REPLY, "partial"),
                                          (ALL_DIRTY, "fallback_validation")],
                         ids=["clean", "partial", "all_invalid"])
def test_one_validator_repair_preserves_completed_repair_semantics(desk, repair, mode):
    state = desk
    state.plans((200, packet(DIRTY_REPLY)), (200, packet(repair)))
    result = state.run()
    parsed = fomc.parse_sections(repair)
    assert result["mode"] == mode
    assert {key: result[key] for key in ("analysis", "hook", "relay")} == parsed
    assert result["violations"] == fomc.validate_copy(parsed, state.sheet)
    if mode == "fallback_validation":
        assert all(result["violations"].values()) and result["relay"] != CLEAN_RELAY
    requests = [json.loads(post[1]) for post in state.native.posts]
    assert len(requests) == len(state.costs) == 2
    assert [cost["stage"] for cost in state.costs] == ["fomc_desk", "fomc_desk_repair"]
    assert requests[1]["messages"][2] == {"role": "assistant", "content": DIRTY_REPLY.strip()}
    assert requests[1]["messages"][3]["content"] == fomc.build_repair_message(
        [v for group in fomc.validate_copy(fomc.parse_sections(DIRTY_REPLY), state.sheet).values() for v in group])
    rows = state.native.rows("application_requests")
    assert len({row["turn_id"] for row in rows}) == len(state.native.rows("leases")) == 1
    assert len({post[2] for post in state.native.posts}) == 1
    assert state.native.rows("leases")[0]["state"] == "released"
    closed(state)


@pytest.mark.parametrize("failure", ["empty", "blank", "tools", "refusal", "truncated", "http", "mismatch", "unknown"])
@pytest.mark.parametrize("repair", [False, True])
def test_unavailable_response_never_rebinds_and_repair_keeps_valid_original_partial(desk, monkeypatch, failure, repair):
    state = desk
    response = packet(CLEAN_REPLY)
    choice = response["choices"][0]
    if failure == "empty": choice["message"]["content"] = ""
    elif failure == "blank": choice["message"]["content"] = "  "
    elif failure == "tools": choice.update(packet(None, tool=True)["choices"][0])
    elif failure == "refusal": choice["finish_reason"] = "content_filter"
    elif failure == "truncated": choice["finish_reason"] = "length"
    elif failure == "mismatch": response["model"] = "different-observed-model"
    responses = ([(200, packet(DIRTY_REPLY))] if repair else []) + [(503 if failure == "http" else 200, response)]
    state.plans(*responses)
    if failure == "unknown":
        original_reply = state.native.on_upstream
        def reply():
            original_reply()
            if len(state.native.posts) == len(responses):
                monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
        state.native.on_upstream = reply
    result = state.run()
    assert result["mode"] == ("partial" if repair else "fallback_provider")
    assert result["relay"] == (CLEAN_RELAY if repair else "")
    assert len(state.native.posts) == len(state.costs) == len(responses)
    assert sum(cost["input_tokens"] for cost in state.costs) == 11 * len(responses)
    if failure == "unknown":
        usage = auth.fabric_usage(state.operations[0][1][0])
        assert usage["input_tokens"] is None and usage["completed_input_tokens"] == 11 * len(responses)
        assert not state.operations[0][1][0]["_fabric_close"]["closed"]
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        assert state.native.rows("application_requests")[-1]["state"] == "unknown"
    closed(state)


@pytest.mark.parametrize("first", [DIRTY_REPLY, ALL_DIRTY], ids=["partial", "all_invalid"])
def test_grant_step_limit_preserves_existing_partial_or_all_invalid_outcome(desk, first):
    state = desk
    state.native.grant["max_steps"] = 1
    state.native.save()
    state.plans((200, packet(first)))
    result = state.run()
    assert result["mode"] == ("partial" if first == DIRTY_REPLY else "fallback_validation")
    assert result["relay"] == fomc.parse_sections(first)["relay"]
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    closed(state)


def test_complete_unstructured_draft_gets_only_its_validator_repair(desk):
    state = desk
    state.plans((200, packet("A complete answer without the required sections.")),
                (200, packet(CLEAN_REPLY)))
    assert state.run()["mode"] == "llm_repair"
    assert len(state.native.posts) == len(state.costs) == 2
    assert len(state.native.rows("leases")) == 1
    closed(state)


@pytest.mark.parametrize("boundary", ["parse_sections", "validate_copy"])
@pytest.mark.parametrize("repair", [False, True])
def test_parser_or_validator_exception_closes_without_an_extra_inference(desk, monkeypatch, boundary, repair):
    state = desk
    original = getattr(fomc, boundary)
    calls = []
    def broken(*args, **kwargs):
        calls.append(args)
        if len(calls) == (2 if repair else 1): raise ValueError("local copy validation unavailable")
        return original(*args, **kwargs)
    monkeypatch.setattr(fomc, boundary, broken)
    responses = ([(200, packet(DIRTY_REPLY))] if repair else []) + [(200, packet(CLEAN_REPLY))]
    state.plans(*responses)
    result = state.run()
    assert result["mode"] == ("partial" if repair else "fallback_validation")
    assert result["relay"] == (CLEAN_RELAY if repair else "")
    if not repair: assert all(v == ["copy_validation_unavailable"] for v in result["violations"].values())
    assert len(state.native.posts) == len(state.costs) == len(responses)
    closed(state)


def test_repair_expiry_keeps_original_partial_known_usage_and_original_effect_custody(desk, monkeypatch):
    state = desk
    state.cfg["fomc_desk"]["llm"]["client_timeout_s"] = 1.0
    state.plans((200, packet(DIRTY_REPLY)), (200, packet(CLEAN_REPLY)))
    original_reply = state.native.on_upstream
    gate, settled = threading.Event(), threading.Event()
    def reply():
        original_reply()
        if len(state.native.posts) == 2: state.native.block = gate
    state.native.on_upstream = reply
    original_complete = state.native.gateway.complete_application
    def complete(*args, **kwargs):
        result = original_complete(*args, **kwargs)
        if len(state.native.posts) == 2: settled.set()
        return result
    monkeypatch.setattr(state.native.gateway, "complete_application", complete)
    started = time.monotonic()
    try:
        result = state.run()
        assert result["mode"] == "partial" and result["relay"] == CLEAN_RELAY
        assert time.monotonic() - started < 3
        assert len(state.native.posts) == 2 and len(state.costs) == 1
        assert state.costs[0]["input_tokens"] == 11
        usage = auth.fabric_usage(state.operations[0][1][0])
        assert usage["input_tokens"] is None and usage["completed_input_tokens"] == 11
        assert not state.operations[0][1][0]["_fabric_close"]["closed"]
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        closed(state)
    finally:
        gate.set()
        assert settled.wait(3), "original delayed synthetic response did not settle"
    assert len(state.native.posts) == 2
    assert all(row["state"] == "terminal" for row in state.native.rows("application_requests"))


@pytest.mark.parametrize("field,value", [(auth.APPLICATION_MODE_CFG_KEY, None),
    (auth.APPLICATION_MODE_CFG_KEY, ""), (auth.APPLICATION_MODE_CFG_KEY, "UNKNOWN"),
    ("workload_profile", None), ("workload_profile", ""), ("workload_profile", "development_agent"),
    ("client_timeout_s", True), ("client_timeout_s", "45"), ("client_timeout_s", 0),
    ("client_timeout_s", float("inf")), ("client_timeout_s", 10**400)])
def test_invalid_caller_mode_profile_or_deadline_refuses_before_credentials(desk, monkeypatch, field, value):
    state = desk
    if field == auth.APPLICATION_MODE_CFG_KEY: monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["fomc_desk"]["llm"][field] = value
    before = copy.deepcopy(state.cfg)
    assert state.run()["mode"] == "fallback_provider" and state.cfg == before
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("direction", ["disappears", "appears"])
def test_selection_race_never_changes_family(desk, monkeypatch, direction):
    state = desk
    if direction == "appears":
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        monkeypatch.setattr(fomc, "_resolve_model_id", lambda: "legacy-model")
    original = auth.build_providers
    def build(cfg, **kwargs):
        if direction == "disappears": monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        else: monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return original(cfg, **kwargs)
    monkeypatch.setattr(auth, "build_providers", build)
    assert state.run()["mode"] == "fallback_provider"
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []


def test_disarmed_desk_and_revoked_capability_never_bind(desk, monkeypatch):
    state = desk
    state.cfg["fomc_desk"]["llm"]["enabled"] = False
    assert state.run()["mode"] == "off"
    state.cfg["fomc_desk"]["llm"]["enabled"] = True
    monkeypatch.delenv("MARKETING_LLM_ENABLED")
    assert state.run()["mode"] == "off"
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    state.manifest["capabilities"][0]["kill_state"] = "killed"
    state.save()
    assert state.run()["mode"] == "fallback_provider"
    assert state.events == state.operations == state.native.posts == []


def test_fresh_desk_invocations_own_distinct_clients_and_turns(desk):
    state = desk
    state.plans((200, packet(CLEAN_REPLY)), (200, packet(CLEAN_REPLY)))
    assert state.run()["mode"] == state.run()["mode"] == "llm"
    assert len(set(state.closes)) == 2
    assert len({id(providers[0]["client"]) for _, providers in state.operations}) == 2
    assert len(state.native.rows("leases")) == len(state.costs) == 2
    closed(state, 2)


def test_receipt_only_repeat_does_not_generate_or_charge_another_desk(desk, monkeypatch):
    state = desk
    monkeypatch.setattr(auth.secrets, "token_hex", lambda _length: "f" * 32)
    state.plans((200, packet(CLEAN_REPLY)))
    assert state.run()["mode"] == "llm"
    assert state.run()["mode"] == "fallback_provider"
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    closed(state, 2)


def test_unknown_close_preserves_completed_copy(desk, monkeypatch):
    state = desk
    monkeypatch.setattr(state.native.gateway, "close_application_turn", Mock(side_effect=OSError("uncommitted close")))
    state.plans((200, packet(CLEAN_REPLY)))
    assert state.run()["mode"] == "llm"
    assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state)


def test_nullable_usage_remains_unknown_while_valid_copy_survives(desk):
    state = desk
    response = packet(CLEAN_REPLY)
    response["usage"]["prompt_tokens"] = None
    state.plans((200, response))
    assert state.run()["mode"] == "llm"
    assert state.costs == [] and len(state.native.posts) == 1
    assert auth.fabric_usage(state.operations[0][1][0])["input_tokens"] is None
    closed(state)


@pytest.mark.parametrize("outcome", ["completed_invalid_repair", "unknown_repair", "first_validation_fault"])
def test_actual_fire_emits_only_the_safe_relay_and_does_not_refire(
    desk, monkeypatch, seeded_root, july_page, desk_cfg, outcome,
):
    from engine.marketing import fomc_statements, outbox

    state = desk
    if outcome == "first_validation_fault":
        state.plans((200, packet(CLEAN_REPLY)))
        monkeypatch.setattr(fomc, "parse_sections", Mock(side_effect=ValueError("local parser unavailable")))
    else:
        state.plans((200, packet(DIRTY_REPLY)),
                    (200, packet(ALL_DIRTY if outcome == "completed_invalid_repair" else CLEAN_REPLY)))
    if outcome == "unknown_repair":
        original_reply = state.native.on_upstream
        def reply():
            original_reply()
            if len(state.native.posts) == 2:
                monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
        state.native.on_upstream = reply
    report = fomc.fire(date_str=JULY, root=seeded_root, cfg=desk_cfg, now=NOW, html_text=july_page)
    assert report["fired"] is True and len(report["emitted"]) == 1
    relay = report["emitted"][0]
    assert relay["fomc_role"] == "relay" and relay["account"] == "mastermind_news"
    assert relay["event_class"] == "fomc"
    if outcome == "unknown_repair":
        assert report["mode"] == "partial" and relay["text"] == CLEAN_RELAY
        assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    else:
        assert report["mode"] == "fallback_validation" and relay["text"] != CLEAN_RELAY
        assert "3-1/2 to 3-3/4 percent" in relay["text"] and "9-3" in relay["text"]
    assert len(outbox.read_items_all(seeded_root)) == 1
    assert fomc_statements.is_collected(JULY, seeded_root)
    count = 1 if outcome == "first_validation_fault" else 2
    assert len(state.native.posts) == len(state.costs) == count
    closed(state)
    repeated = fomc.fire(date_str=JULY, root=seeded_root, cfg=desk_cfg, now=NOW, html_text=july_page)
    assert repeated["fired"] is False and repeated["emitted"] == []
    assert len(state.native.posts) == count and len(state.operations) == 1
