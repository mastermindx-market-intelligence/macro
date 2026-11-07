"""Breaking's public draft/repair path through the real owner and native B/A.

Qualification, credentials and upstream replies are synthetic. The validator,
operation, HTTP transport, accounting and SQLite admission remain real.
"""
import copy
import json
import os
import re
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine.marketing import breaking_summary as breaking
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
_CLIENT = transport.FabricInferenceClient
ITEM = {"headline": "CPI rose 0.3 percent in June",
        "body_snippet": "Consumer prices increased 0.3 percent in June, the same gain as in May.",
        "source_name": "Fixture source", "source_tier": "official",
        "url": "https://fixture.invalid/release", "published_at": "2026-07-14T12:30:00Z"}
CLEAN = "The June CPI reading came in at 0.3% on the month."
DIRTY = "The June CPI reading came in at 7.9% on the month."


def packet(text, *, model=MODEL, finish="stop", tool=False):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "unexpected-1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
        finish = "tool_calls"
    return {"model": model, "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


def observe(state, monkeypatch):
    state.operations, state.closes = [], []
    original_begin, original_close = auth.begin_operation, _CLIENT.close

    def begin(*args, **kwargs):
        operation = original_begin(*args, **kwargs)
        state.operations.append((operation, tuple(operation.providers)))
        return operation

    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)

    monkeypatch.setattr(auth, "begin_operation", begin)
    monkeypatch.setattr(_CLIENT, "close", close)

    def plans(*responses):
        pending = list(responses)
        def upstream():
            assert pending, "unexpected additional provider request"
            state.native.response_status, state.native.response = pending.pop(0)
        state.native.on_upstream = upstream
    state.plans = plans


def closed(state, count=1):
    assert len(state.operations) == len(state.closes) == count
    assert all(re.fullmatch(r"app:[0-9a-f]{32}", value) for value in state.closes)
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


@pytest.fixture
def summary(selected, monkeypatch):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"].append("marketing-breaking")
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    monkeypatch.setattr("lib.config.load", Mock(side_effect=AssertionError("native model map prerequisite")))
    monkeypatch.setattr("engine.marketing.wire_voice.resolve_model_key",
                        Mock(side_effect=AssertionError("native wire model prerequisite")))
    state.item = copy.deepcopy(ITEM)
    state.cfg = {"llm": {"enabled": True, "model_key": "absent_native_model"}}
    state.wire = None
    observe(state, monkeypatch)
    state.run = lambda: breaking.summarize_item(state.item, state.cfg, wire=state.wire)
    return state


@pytest.mark.parametrize("wire", [None, {"_format": "flash"}])
def test_public_summary_selected_without_legacy_model_lookup_keeps_provenance(summary, wire):
    state = summary
    state.wire = wire
    state.plans((200, packet(CLEAN)))
    result = state.run()
    assert result == {"summary": CLEAN, "mode": "llm", "violations_seen": [],
        **{key: ITEM[key] for key in ("source_name", "source_tier", "url", "published_at")}}
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["max_tokens"] == 800
    assert request["stream"] is False and "tools" not in request
    assert ITEM["headline"] in request["messages"][-1]["content"]
    assert ITEM["body_snippet"] in request["messages"][-1]["content"]
    if wire:
        from engine.marketing.wire_voice import key_phrase_prompt_law
        assert key_phrase_prompt_law() in request["messages"][0]["content"]
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["lane"] == "marketing-breaking"
    assert state.costs[0]["stage"] == "marketing_breaking" and state.costs[0]["model"] == MODEL
    assert state.costs[0]["input_tokens"] == 11
    assert state.operations[0][1][0]["client"]._client._timeout == 90
    closed(state)


@pytest.mark.parametrize("repair", [CLEAN, DIRTY])
def test_validator_repair_uses_same_binding_account_and_single_turn(summary, repair):
    state = summary
    state.plans((200, packet(DIRTY)), (200, packet(repair)))
    result = state.run()
    assert result["mode"] == ("llm_repaired" if repair == CLEAN else "llm_fallback")
    assert result["summary"] == (CLEAN if repair == CLEAN else breaking._deterministic_summary(ITEM))
    assert any("7.9" in violation for violation in result["violations_seen"])
    if repair == DIRTY: assert any(v.startswith("repair:") for v in result["violations_seen"])
    rows = state.native.rows("application_requests")
    assert len(rows) == len(state.native.posts) == len(state.costs) == 2
    assert len({row["turn_id"] for row in rows}) == len(state.native.rows("leases")) == 1
    assert [row["request_id"] for row in rows] == [f"{rows[0]['turn_id']}:brain:{i}" for i in range(2)]
    assert len({post[2] for post in state.native.posts}) == 1
    requests = [json.loads(post[1]) for post in state.native.posts]
    assert all(req["model"] == MODEL and req["max_tokens"] == 800 for req in requests)
    assert "Rejected draft: " + DIRTY in requests[1]["messages"][-1]["content"]
    assert "Validator complaints:" in requests[1]["messages"][-1]["content"]
    assert sum(cost["input_tokens"] for cost in state.costs) == 22
    assert state.native.rows("leases")[0]["state"] == "released"
    closed(state)


@pytest.mark.parametrize("failure", ["empty", "blank", "tools", "refusal", "truncated", "http", "mismatch", "unknown"])
def test_noncompletion_never_enters_validator_repair(summary, monkeypatch, failure):
    state = summary
    response = packet(CLEAN)
    choice = response["choices"][0]
    if failure == "empty": choice["message"]["content"] = ""
    elif failure == "blank": choice["message"]["content"] = "  "
    elif failure == "tools": choice.update(packet(None, tool=True)["choices"][0])
    elif failure == "refusal": choice["finish_reason"] = "content_filter"
    elif failure == "truncated": choice["finish_reason"] = "length"
    elif failure == "mismatch": response["model"] = "different-observed-model"
    elif failure == "unknown":
        monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    state.plans((503 if failure == "http" else 200, response))
    result = state.run()
    assert result["mode"] == "deterministic" and result["violations_seen"] == []
    assert result["summary"] == breaking._deterministic_summary(ITEM)
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["model"] == ("different-observed-model" if failure == "mismatch" else MODEL)
    assert state.native.rows("application_requests")[0]["state"] == ("unknown" if failure == "unknown" else "terminal")
    if failure == "unknown":
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    closed(state)


def test_unknown_repair_keeps_known_usage_and_never_rebinds(summary, monkeypatch):
    state = summary
    state.plans((200, packet(DIRTY)), (200, packet(CLEAN)))
    original = state.native.on_upstream
    def reply():
        original()
        if len(state.native.posts) == 2:
            monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    state.native.on_upstream = reply
    assert state.run()["mode"] == "llm_fallback"
    assert len(state.native.posts) == len(state.costs) == 2
    assert [row["state"] for row in state.native.rows("application_requests")] == ["terminal", "unknown"]
    usage = auth.fabric_usage(state.operations[0][1][0])
    assert usage["input_tokens"] is None and usage["completed_input_tokens"] == 22
    assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    closed(state)


def test_grant_step_limit_refuses_repair_without_new_operation(summary):
    state = summary
    state.native.grant["max_steps"] = 1
    state.native.save()
    state.plans((200, packet(DIRTY)))
    assert state.run()["mode"] == "llm_fallback"
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    closed(state)


def test_fresh_invocations_have_distinct_clients_and_turns(summary):
    state = summary
    state.plans((200, packet(CLEAN)), (200, packet(CLEAN)))
    assert state.run()["mode"] == state.run()["mode"] == "llm"
    assert len(set(state.closes)) == 2
    assert len({id(providers[0]["client"]) for _, providers in state.operations}) == 2
    assert len(state.native.rows("leases")) == len(state.costs) == 2
    closed(state, 2)


def test_receipt_only_repeat_cannot_produce_or_bill_another_summary(summary, monkeypatch):
    state = summary
    monkeypatch.setattr(auth.secrets, "token_hex", lambda _length: "b" * 32)
    state.plans((200, packet(CLEAN)))
    assert state.run()["mode"] == "llm"
    assert state.run()["mode"] == "deterministic"
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    closed(state, 2)


def test_close_unknown_preserves_completed_summary(summary, monkeypatch):
    state = summary
    monkeypatch.setattr(state.native.gateway, "close_application_turn", Mock(side_effect=OSError("uncommitted close")))
    state.plans((200, packet(CLEAN)))
    assert state.run()["mode"] == "llm"
    assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state)


def test_nullable_usage_does_not_fabricate_zero_or_invalidate_completed_text(summary):
    state = summary
    response = packet(CLEAN)
    response["usage"]["prompt_tokens"] = None
    state.plans((200, response))
    assert state.run()["mode"] == "llm"
    assert state.costs == [] and len(state.native.posts) == 1
    assert auth.fabric_usage(state.operations[0][1][0])["input_tokens"] is None
    closed(state)


@pytest.mark.parametrize("field,value", [(auth.APPLICATION_MODE_CFG_KEY, None),
    (auth.APPLICATION_MODE_CFG_KEY, ""), (auth.APPLICATION_MODE_CFG_KEY, "UNKNOWN"),
    ("workload_profile", None), ("workload_profile", ""), ("workload_profile", "development_agent")])
def test_invalid_explicit_selection_or_profile_refuses_before_credentials(summary, monkeypatch, field, value):
    state = summary
    if field == auth.APPLICATION_MODE_CFG_KEY: monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["llm"][field] = value
    before = copy.deepcopy(state.cfg)
    assert state.run()["mode"] == "deterministic" and state.cfg == before
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("direction", ["disappears", "appears"])
def test_selection_race_cannot_change_provider_family(summary, monkeypatch, direction):
    state = summary
    if direction == "appears":
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        monkeypatch.setattr("lib.config.load", lambda: {"llm_models": {"absent_native_model": "legacy-model"}})
    original = auth.build_providers
    def build(cfg, **kwargs):
        if direction == "disappears": monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        else: monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return original(cfg, **kwargs)
    monkeypatch.setattr(auth, "build_providers", build)
    assert state.run()["mode"] == "deterministic"
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []


def test_disabled_and_override_paths_do_not_bind_or_repair(summary, monkeypatch):
    state = summary
    begin = Mock(side_effect=AssertionError("disabled path bound"))
    monkeypatch.setattr(auth, "begin_operation", begin)
    state.cfg["llm"]["enabled"] = False
    assert state.run()["mode"] == "deterministic"
    state.cfg["llm"]["enabled"] = True
    monkeypatch.delenv("MARKETING_LLM_ENABLED")
    assert state.run()["mode"] == "deterministic"
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    override = Mock(return_value=DIRTY)
    assert breaking.summarize_item(ITEM, state.cfg, _llm_override=override)["mode"] == "llm_fallback"
    override.assert_called_once_with(ITEM, state.cfg)
    begin.assert_not_called()
    assert state.events == state.native.posts == []


def test_standalone_summary_owns_and_closes_one_operation(summary):
    summary.plans((200, packet(CLEAN)))
    assert breaking._llm_summarize(ITEM, summary.cfg) == CLEAN
    assert len(summary.native.posts) == 1
    closed(summary)


@pytest.mark.parametrize("nested", [False, True])
def test_explicit_valid_selection_survives_both_existing_config_shapes(summary, monkeypatch, nested):
    state = summary
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["llm"][auth.APPLICATION_MODE_CFG_KEY] = "shared_fabric"
    if nested: state.cfg = {"breaking": state.cfg}
    before = copy.deepcopy(state.cfg)
    state.plans((200, packet(CLEAN)))
    assert state.run()["mode"] == "llm" and state.cfg == before
    closed(state)


def test_unexpected_local_validator_exception_still_closes_original_operation(summary, monkeypatch):
    state = summary
    state.plans((200, packet(CLEAN)))
    monkeypatch.setattr(breaking, "validate_summary", Mock(side_effect=ValueError("validator unavailable")))
    with pytest.raises(ValueError, match="validator unavailable"):
        state.run()
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state)


@pytest.mark.parametrize("bad", [None, (), ([], True, 800), ({"name": "fabric"}, True, 800)])
def test_supplied_invalid_bound_handle_never_rebinds(summary, bad):
    assert breaking._llm_summarize(ITEM, summary.cfg, _bound=bad) is None
    assert summary.events == summary.operations == summary.native.posts == []


@pytest.mark.parametrize("flag", [False, 1, "true"])
def test_supplied_bound_handle_cannot_hide_selected_terminal_screen(summary, flag):
    state = summary
    providers, _selected, cap = breaking._summary_recipe(ITEM, state.cfg, None)
    with auth.begin_operation(providers) as operation:
        assert breaking._llm_summarize(ITEM, state.cfg, _bound=(operation.providers, flag, cap)) is None
    assert state.native.posts == state.costs == []
    closed(state)


def test_closed_bound_handle_cannot_start_another_turn(summary):
    state = summary
    providers, selected, cap = breaking._summary_recipe(ITEM, state.cfg, None)
    operation = auth.begin_operation(providers)
    bound = (operation.providers, selected, cap)
    operation.close()
    assert breaking._llm_summarize(ITEM, state.cfg, _bound=bound) is None
    assert state.native.posts == []
    closed(state)
