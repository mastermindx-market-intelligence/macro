"""DeepSeek consumer wire/receipt support against synthetic loopback only.

These tests do not qualify native transports, enroll accounts, issue grants or
send provider traffic. Native admission remains the owner of usable routes.
"""
import copy
import hashlib
import json

import pytest

from engine import fabric_inference_client as client
from tests.test_fabric_inference_client import completion, server
from tests.test_fabric_native_application_client import send

MODEL = "deepseek-flash"
TURN = "deepseek-consumer:original"
STEP = TURN + ":brain:0"
TOKEN = "synthetic-deepseek-service-token-00000000"


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def inspection(*, exact=False, pools=("deepseek", "go")):
    scope = {"schema": "mastermind.application_route_scope.v1", "pools": list(pools)}
    return {
        "schema": client.EXACT_INSPECTION_SCHEMA if exact else client.AUTO_INSPECTION_SCHEMA,
        "requested_model": MODEL if exact else None,
        "route_scope": scope, "route_scope_digest": digest(scope),
        "output_limit_mode": "hard_maximum", "cap_id": "fixture-cap",
        "capability_id": "fixture-capability", "workload_policy": {"profiles": ["site_interactive"]},
        "transport_identity": "a" * 64,
    }


def route(snapshot, original):
    exact = snapshot["schema"] == client.EXACT_INSPECTION_SCHEMA
    return {
        "schema": "mastermind.fabric_application_route.v2" if exact else
                  "mastermind.fabric_application_route.v1",
        "requested_model": snapshot["requested_model"],
        "route_scope": copy.deepcopy(snapshot["route_scope"]),
        "route_scope_digest": snapshot["route_scope_digest"],
        "selection_digest": "b" * 64,
        "request_digest": digest({"path": "/v1/chat/completions", "payload": original}),
        "routed_request_digest": None if exact else
            digest({"path": "/v1/chat/completions", "payload": dict(original, model=MODEL)}),
        "pool": "deepseek", "selected_model": MODEL, "mode": "application",
        "protocol": "responses", "driver": "deepseek-commercial-api.responses",
        "profile": "fixture-profile", "source": "fixture-source", "recipe_digest": "c" * 64,
        "output_contract": {"mode": "hard_maximum", "max_tokens": original["max_tokens"]},
    }


def response(snapshot, original):
    payload = completion(model=MODEL)
    payload["application"] = {
        "schema": client.AUTO_SCHEMA, "disposition": "terminal", "turn_id": TURN,
        "request_id": STEP, "dispatch_permitted": False, "effect_unknown": False,
        "routing": route(snapshot, original), "usage": {"input_tokens": 13, "output_tokens": 7},
        "serving_model": MODEL,
    }
    return {
        "json": payload, "headers": {
            "X-MM-Application-Disposition": "terminal",
            "X-MM-Application-Turn-ID": TURN, "X-MM-Application-Request-ID": STEP,
        },
    }


def request(snapshot, *, request_id=STEP):
    return {
        "model": snapshot["requested_model"], "max_tokens": 128, "request_id": request_id,
        "system": "Use the supplied context.",
        "messages": [
            {"role": "user", "content": "First question."},
            {"role": "assistant", "content": "Earlier answer."},
            {"role": "user", "content": "Follow-up question."},
        ],
        "temperature": 0,
        "tools": [{"name": "read", "input_schema": {"type": "object",
                    "properties": {"symbol": {"type": "string"}}}}],
    }


def native(url, snapshot):
    return client.FabricInferenceClient(base_url=url, proxy_token=TOKEN,
        model=snapshot["requested_model"], protocol=client.NATIVE_PROTOCOL,
        operation_id=TURN, auto_inspection=snapshot)


def test_closed_scope_accepts_complete_ten_pool_vocabulary_without_mutating_input():
    value = {"schema": "mastermind.application_route_scope.v1",
             "pools": sorted(client.AUTO_POOLS)}
    before = copy.deepcopy(value)
    checked, commitment = client.validate_auto_route_scope(value)
    assert len(checked["pools"]) == 10 and "deepseek" in checked["pools"]
    assert commitment == digest(before)
    checked["pools"].clear()
    assert value == before


@pytest.mark.parametrize("pools", [[], ["deepseek", "deepseek"], ["go", "deepseek"],
                                   ["deepseek", "future-provider"], ["deepseek", False]])
def test_scope_remains_closed_and_canonical(pools):
    with pytest.raises(client.FabricInferenceError, match="fabric_auto_scope_invalid"):
        client.validate_auto_route_scope({"schema": "mastermind.application_route_scope.v1",
                                          "pools": pools})


@pytest.mark.parametrize("exact", [False, True])
def test_real_consumer_accepts_deepseek_route_and_retains_original_receipt(exact):
    snapshot = inspection(exact=exact)
    def reply(handler):
        send(handler, response(snapshot, calls[-1]["body"]))
    with server(reply) as (url, calls):
        transport = native(url, snapshot)
        result = transport.messages.create(**request(snapshot))
        document = result.application_observation.document
        routing = document["routing"]
        assert result.model == MODEL and result.usage.input_tokens == 13
        assert result.usage.output_tokens == 7 and result.content[0].text == "Market context."
        assert routing["pool"] == "deepseek" and routing["protocol"] == "responses"
        assert routing["selected_model"] == document["serving_model"] == MODEL
        assert calls[0]["body"]["model"] == snapshot["requested_model"]
        assert [item["role"] for item in calls[0]["body"]["messages"]] == [
            "system", "user", "assistant", "user"]
        assert calls[0]["body"]["tools"][0]["function"]["name"] == "read"
        assert calls[0]["headers"]["X-MM-Application-Route-Scope-Digest"] == snapshot["route_scope_digest"]
        with pytest.raises(client.FabricInferenceError, match="step_unavailable"):
            transport.messages.create(**request(snapshot))
        before = len(calls)
        for _ in range(2):
            checked = client.validate_auto_observation(
                document, snapshot, operation_id=TURN, request_id=STEP,
                request_digest=routing["request_digest"],
                routed_request_digest=routing["routed_request_digest"], max_tokens=128,
                expected_route=client.auto_route_identity(routing), require_success=True)
            assert checked == document
        assert len(calls) == before == 1


@pytest.mark.parametrize("fault", ["chat", "harness", "recipe", "scope", "request",
                                   "routed-request", "served-model"])
def test_posted_bad_deepseek_result_retains_counts_and_never_resends(fault):
    snapshot = inspection()
    def reply(handler):
        plan = response(snapshot, calls[-1]["body"])
        state = plan["json"]["application"]
        routing = state["routing"]
        if fault in {"chat", "harness"}:
            routing["protocol"] = fault
        elif fault == "recipe":
            routing["recipe_digest"] = None
        elif fault == "scope":
            routing["route_scope_digest"] = "f" * 64
        elif fault == "request":
            routing["request_digest"] = "f" * 64
        elif fault == "routed-request":
            routing["routed_request_digest"] = "f" * 64
        else:
            state["serving_model"] = plan["json"]["model"] = "deepseek-v4-pro"
        send(handler, plan)
    with server(reply) as (url, calls):
        transport = native(url, snapshot)
        with pytest.raises(client.FabricInferenceError) as first:
            transport.messages.create(**request(snapshot))
        assert first.value.observed_usage.input_tokens == 13
        assert first.value.observed_usage.output_tokens == 7
        assert first.value.serving_model == ("deepseek-v4-pro" if fault == "served-model" else MODEL)
        with pytest.raises(client.FabricInferenceError) as second:
            transport.messages.create(**request(snapshot, request_id=TURN + ":brain:1"))
        assert second.value is first.value
        assert len(calls) == 1


@pytest.mark.parametrize("pool,protocol,recipe", [
    ("go", "chat", None), ("bailian", "responses", "c" * 64),
    ("codex-native", "harness", "c" * 64), ("claude-native", "harness", "c" * 64),
    ("glm", "harness", "c" * 64), ("minimax", "harness", "c" * 64),
    ("grok", "harness", "c" * 64), ("cursor", "harness", "c" * 64),
    ("ocfree", "harness", "c" * 64), ("deepseek", "responses", "c" * 64),
])
def test_recorded_route_protocol_contracts_remain_pool_specific(pool, protocol, recipe):
    snapshot = inspection(pools=tuple(sorted(client.AUTO_POOLS)))
    routing = route(snapshot, {"model": None, "max_tokens": 128, "messages": []})
    routing.update(pool=pool, protocol=protocol, recipe_digest=recipe)
    document = {
        "schema": "mastermind.fabric_application_observation.v2", "disposition": "terminal",
        "effect_unknown": False, "turn_id": TURN, "request_id": STEP, "routing": routing,
        "serving_model": MODEL, "usage": {"input_tokens": None, "output_tokens": None},
    }
    def validate():
        return client.validate_auto_observation(document, snapshot, operation_id=TURN,
            request_id=STEP, request_digest=routing["request_digest"],
            routed_request_digest=routing["routed_request_digest"], max_tokens=128,
            require_success=True)
    assert validate() == document
    routing["protocol"] = "harness" if protocol != "harness" else "responses"
    with pytest.raises(client.FabricInferenceError, match="fabric_auto_route_invalid"):
        validate()
