"""Context consumers through the actual shared owner and pinned native gateway.

Only qualification, credentials, supplied source data and upstream replies are
synthetic. Annotation/candidate gates and the original watermark remain real.
"""
import copy
from datetime import date, timedelta
import json
import os
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import commodity_news as commodity, fabric_inference_client as transport, llm_auth as auth
from engine.influence import extract as influence
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
_CLIENT = transport.FabricInferenceClient
REQUESTED = "requested-claude-model"
HEADLINES = [{"title": "Oil supply was interrupted by a storm.", "domain": "fixture.invalid",
              "seendate": "20261105T000000Z", "url": "https://fixture.invalid/news"}]
CAUSE = {"evidence": "Oil supply was interrupted", "cause": "supply_disruption", "confidence": "high"}
SOURCE = "Fixture Leader advises Fixture Company on product research."
EDGE = {"src": "Fixture Leader", "rel": "ADVISES", "dst": "Fixture Company", "citation": SOURCE}


def packet(text, *, model=MODEL, finish="stop", tool=False):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "unsolicited-1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
        finish = "tool_calls"
    return {"model": model, "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


@pytest.fixture
def contexts(selected, monkeypatch):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"] += ["commodity-news", "influence-extract"]
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    state.commodity_cfg = {"enabled": True, "llm_classify": True, "llm_model": REQUESTED}
    state.influence_cfg = {**influence._DEFAULTS, "extract": True, "model": REQUESTED}
    monkeypatch.setattr(commodity, "_cfg", lambda: state.commodity_cfg)
    monkeypatch.setattr(commodity, "_fetch_gdelt", lambda *_: (copy.deepcopy(HEADLINES), None))
    monkeypatch.setattr(influence, "_cfg", lambda: state.influence_cfg)
    monkeypatch.setattr(influence, "_news_items", lambda *_: [{"source_id": "fixture-source-1",
        "text": SOURCE, "url": "https://fixture.invalid/source", "source_type": "news", "time": "2026-11-05"}])
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
            assert pending, "unexpected additional provider request"
            state.native.response_status, state.native.response = pending.pop(0)
        state.native.on_upstream = upstream
    state.plans = plans
    state.commodity = lambda: commodity.annotate_event("oil", date.today(), "An observed price move.")
    state.influence = lambda: influence.run(root=state.root)
    return state


def closed(state, count):
    assert len(state.operations) == len(state.closes) == count
    assert all(re.fullmatch(r"app:[0-9a-f]{32}", value) for value in state.closes)
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


def accepted(state, caller):
    result = getattr(state, caller)()
    return (result, result["likely_cause"] is not None) if caller == "commodity" else (result, result["extracted"] > 0)


def test_public_commodity_exact_schema_actual_model_usage_and_fresh_operations(contexts):
    state = contexts
    state.plans((200, packet(json.dumps(CAUSE))), (200, packet(json.dumps({**CAUSE, "confidence": "low"}))))
    first, second = state.commodity(), state.commodity()
    assert first["schema"] == "commodity_news.v1" and first["is_context_only"] is True
    assert first["disclaimer"] == commodity.DISCLAIMER_TEXT and first["headlines"] == HEADLINES
    assert first["likely_cause"] == {**CAUSE, "model": MODEL, "applied_threshold": "high"}
    assert second["likely_cause"]["cause"] == "unknown"
    assert second["likely_cause"]["model"] == MODEL
    assert len(set(state.closes)) == 2
    closed(state, 2)
    assert len(state.native.posts) == len(state.costs) == 2
    for _, raw, _ in state.native.posts:
        request = json.loads(raw)
        assert request["model"] == MODEL and "output_config" not in request
        assert json.dumps(commodity.CLASSIFY_SCHEMA, sort_keys=True) in request["messages"][0]["content"]
    assert all(row["lane"] == "commodity-news" and row["stage"] == "commodity_news"
               and row["model"] == MODEL and row["input_tokens"] == 11 for row in state.costs)
    assert all(row["state"] == "released" for row in state.native.rows("leases"))


def test_public_influence_citations_candidates_and_original_watermark(contexts):
    state = contexts
    unsupported = [{**EDGE, "citation": "A fabricated unrelated sentence."},
                   {**EDGE, "rel": "PROMOTES"}]
    state.plans((200, packet(json.dumps({"edges": [EDGE, *unsupported]}))))
    result = state.influence()
    assert result == {"extracted": 1, "processed": 1, "reason": "ok"}
    rows = influence.load_candidates(state.root)
    assert len(rows) == 1
    row = rows[0]
    assert row["src"] == EDGE["src"] and row["dst"] == EDGE["dst"] and row["rel"] == "ADVISES"
    assert row["provenance"] == "INFERRED" and row["confidence"] == 0.5 and row["status"] == "candidate"
    assert SOURCE.lower() in row["citation"].lower()
    assert state.influence() == {"extracted": 0, "processed": 0, "reason": "ok"}
    assert influence.load_candidates(state.root) == rows
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state, 1)
    assert state.costs[0]["lane"] == "influence-extract" and state.costs[0]["stage"] == "influence_extract"
    assert state.costs[0]["model"] == MODEL
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["messages"][0]["content"] == influence._SYSTEM


@pytest.mark.parametrize("invalid", [None, [], {}, {"cause": "supply_disruption"},
    {**CAUSE, "extra": "unexpected"}, {**CAUSE, "cause": "invented"},
    {**CAUSE, "confidence": "certain"}, {**CAUSE, "evidence": 7}, "not-json"])
def test_commodity_closed_schema_rejects_before_business_acceptance(contexts, invalid):
    state = contexts
    state.plans((200, packet(invalid if invalid == "not-json" else json.dumps(invalid))))
    result = state.commodity()
    assert result["likely_cause"] is None and result["degraded_reason"] == "llm_error"
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state, 1)


@pytest.mark.parametrize("caller", ["commodity", "influence"])
@pytest.mark.parametrize("failure", ["empty", "blank", "tools", "refusal", "truncated", "http", "mismatch", "unknown"])
def test_selected_failure_never_retries_or_produces_annotation_or_candidate(contexts, monkeypatch, caller, failure):
    state = contexts
    text = json.dumps(CAUSE if caller == "commodity" else {"edges": [EDGE]})
    response = packet(text)
    choice = response["choices"][0]
    if failure == "empty": choice["message"]["content"] = ""
    elif failure == "blank": choice["message"]["content"] = "  "
    elif failure == "tools": choice.update(packet(None, tool=True)["choices"][0])
    elif failure == "refusal": choice["finish_reason"] = "content_filter"
    elif failure == "truncated": choice["finish_reason"] = "length"
    elif failure == "mismatch": response["model"] = "different-observed-model"
    state.plans((503 if failure == "http" else 200, response))
    if failure == "unknown":
        monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    result, useful = accepted(state, caller)
    assert not useful
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state, 1)
    assert state.costs[0]["model"] == ("different-observed-model" if failure == "mismatch" else MODEL)
    assert state.costs[0]["input_tokens"] == 11
    if failure == "unknown":
        assert state.native.rows("application_requests")[0]["state"] == "unknown"
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        provider = state.operations[0][1][0]
        assert auth.fabric_usage(provider)["input_tokens"] is None and not provider["_fabric_close"]["closed"]
    else:
        assert state.native.rows("application_requests")[0]["state"] == "terminal"
        assert state.native.rows("leases")[0]["state"] == "released"
    if caller == "influence":
        assert result["processed"] == 1 and influence.load_candidates(state.root) == []
        assert state.influence()["processed"] == 0
        assert len(state.native.posts) == 1


@pytest.mark.parametrize("caller", ["commodity", "influence"])
def test_nullable_usage_is_not_filled_with_zero(contexts, caller):
    state = contexts
    response = packet(json.dumps(CAUSE if caller == "commodity" else {"edges": [EDGE]}))
    response["usage"]["prompt_tokens"] = None
    state.plans((200, response))
    assert accepted(state, caller)[1]
    assert state.costs == [] and len(state.native.posts) == 1
    closed(state, 1)
    assert auth.fabric_usage(state.operations[0][1][0])["input_tokens"] is None


@pytest.mark.parametrize("caller", ["commodity", "influence"])
def test_receipt_only_recovery_never_becomes_a_second_answer(contexts, monkeypatch, caller):
    state = contexts
    monkeypatch.setattr(auth.secrets, "token_hex", lambda _length: "c" * 32)
    text = json.dumps(CAUSE if caller == "commodity" else {"edges": [EDGE]})
    state.plans((200, packet(text)))
    if caller == "commodity":
        assert state.commodity()["likely_cause"] is not None
        assert state.commodity()["likely_cause"] is None
    else:
        assert influence._call(SOURCE, state.influence_cfg)
        assert influence._call(SOURCE, state.influence_cfg) is None
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    closed(state, 2)


@pytest.mark.parametrize("caller", ["commodity", "influence"])
@pytest.mark.parametrize("mode", ["", "UNKNOWN", "missing_mode"])
def test_invalid_host_selection_never_discovers_native_credentials(contexts, monkeypatch, caller, mode):
    state = contexts
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, mode)
    assert not accepted(state, caller)[1]
    assert state.events == state.closes == state.native.posts == state.costs == []
    assert state.native.rows("leases") == []


@pytest.mark.parametrize("caller", ["commodity", "influence"])
@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_explicit_denied_profile_is_preserved_and_spends_nothing(contexts, caller, profile):
    state = contexts
    getattr(state, caller + "_cfg")["workload_profile"] = profile
    assert not accepted(state, caller)[1]
    assert state.events == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("caller", ["commodity", "influence"])
@pytest.mark.parametrize("mode", [None, "", "UNKNOWN"])
def test_invalid_caller_selection_cannot_fall_back(contexts, monkeypatch, caller, mode):
    state = contexts
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    getattr(state, caller + "_cfg")[auth.APPLICATION_MODE_CFG_KEY] = mode
    assert not accepted(state, caller)[1]
    assert state.events == state.closes == state.native.posts == state.costs == []


def test_feature_and_input_gates_never_bind(contexts, monkeypatch):
    state = contexts
    monkeypatch.setattr(auth, "begin_operation", Mock(side_effect=AssertionError("gated invocation bound")))
    state.commodity_cfg["enabled"] = False
    assert state.commodity() is None
    state.commodity_cfg["enabled"] = True
    assert commodity.annotate_event("oil", date.today() - timedelta(days=91))["degraded_reason"] == "outside_gdelt_window"
    state.commodity_cfg["llm_classify"] = False
    assert state.commodity()["likely_cause"] is None
    state.commodity_cfg["llm_classify"] = True
    monkeypatch.setenv("DISABLE_COMMODITY_NEWS_LLM", "1")
    assert state.commodity()["likely_cause"] is None
    monkeypatch.delenv("DISABLE_COMMODITY_NEWS_LLM")
    assert commodity._classify_cause("oil", "move", [], state.commodity_cfg) == (None, None)
    state.influence_cfg["extract"] = False
    assert state.influence() == {"extracted": 0, "reason": "disabled"}
    state.influence_cfg["extract"] = True
    monkeypatch.setattr(influence, "_news_items", lambda *_: [])
    assert state.influence() == {"extracted": 0, "processed": 0, "reason": "ok"}
    assert state.events == state.closes == state.native.posts == state.costs == []


def test_unselected_native_request_shape_and_requested_model_are_preserved(contexts, monkeypatch):
    state = contexts
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(model="different-native-observation", stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(CAUSE))], usage=None)
    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    provider = {"name": "anthropic", "model": REQUESTED, "client": client, "cred": "synthetic"}
    monkeypatch.setattr(auth, "build_providers", lambda *_args, **_kwargs: [provider])
    # Native make_call's SDK factory is outside this Fabric fixture. Keep the
    # native callback and actual ProviderOperation lifetime under observation.
    def native_call(providers, callback, **_kwargs):
        text, reason, _response = callback(client, providers[0]["model"])
        return text, reason, "anthropic"
    monkeypatch.setattr(auth, "make_call", native_call)
    result = state.commodity()
    assert result["likely_cause"]["model"] == REQUESTED
    assert calls[-1]["output_config"] == {"format": {"type": "json_schema", "schema": commodity.CLASSIFY_SCHEMA}}
    assert influence._call(SOURCE, state.influence_cfg)
    assert calls[-1]["system"] == [{"type": "text", "text": influence._SYSTEM, "cache_control": {"type": "ephemeral"}}]
    assert calls[-1]["model"] == REQUESTED and provider["model"] == REQUESTED
    assert state.closes == state.native.posts == state.costs == []
