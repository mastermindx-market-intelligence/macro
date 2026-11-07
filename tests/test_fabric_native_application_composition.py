"""Actual Macro owner/client -> pinned native B/A -> synthetic loopback upstream.

Set MM_FABRIC_GATEWAY_SOURCE_ROOT to Mastermind8af48bc. The test reuses its
real Broker/SQLite/gateway/handler fixture; only credentials, qualification,
provider responses and lifecycle helpers are synthetic. No deployment claim.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from engine import fabric_inference_client as transport
from engine import llm_auth as auth, news_translate
from engine import provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401

SOURCE_ROOT = os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT")
pytestmark = pytest.mark.skipif(not SOURCE_ROOT, reason="paired Mastermind8af checkout required")
MODEL = "fixture-model"
PINS = {
    "candidate/commission_deadline.py": "fade630ed75c1b93334a5711a6df7a554fbd24ee",
    "candidate/go_shim.py": "2c7bb5a9719f4a94bd57a30b5c1bc90d171573df",
    "candidate/lease_broker.py": "166930f1b91753b764c4f6561ec309830f2cb332",
    "candidate/go_lease_gateway.py": "b9fa884e88481e9f0e80a18b19dd79d343130bd1",
    "candidate/go_lease_capability.py": "4224b4988a7b13e1a3b703f2e3fe7ddbbac88a03",
    "candidate/provider_outcome.py": "4236303eb3abfa7c9dcad4d3e1a5454f15600c98",
    "candidate/quota_circuit.py": "b119865ba77908eaf971e86e923075d7da365ffc",
    "source/model_tier.py": "96093c2747d2dda69b3f2255cb84e656355c87ea",
    "source/pool_status.py": "02922043357d63b4bcfa3791899df27a5c42be12",
    "tests/_offline_boundary.py": "e511ab65fe1cd30bf4d2addac6700ca43c3468da",
    "tests/test_go_application_handler_composition.py": "13ebd6bcee5167926807d7ccdc63bcabed0cf1b1",
    "tests/test_application_turn_admission.py": "efe876eec40dc8885dbc0059915f2401146be969",
}


def native_fixture(source_root, pins, *, module_name):
    """Load the same real native fixture from one explicitly pinned source."""
    root = Path(source_root).resolve() / "ops/native_fabric/quota_continuity"
    for relative, expected in pins.items():
        raw = (root / relative).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == expected, relative
    original_path = list(sys.path)
    sys.path[:0] = [str(root / "tests"), str(root / "candidate"), str(root / "source")]
    for name in ("lease_broker", "go_lease_gateway", "go_lease_capability"):
        loaded = sys.modules.get(name)
        if loaded is not None:
            assert Path(loaded.__file__).resolve() == root / "candidate" / (name + ".py")
    spec = importlib.util.spec_from_file_location(module_name,
        root / "tests/test_go_application_handler_composition.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    fixture = module.NativeApplicationHTTPFixture()
    fixture.setUp()
    try:
        yield fixture
    finally:
        fixture.doCleanups()
        sys.modules.pop(spec.name, None)
        sys.path[:] = original_path


@pytest.fixture
def native(monkeypatch):
    yield from native_fixture(SOURCE_ROOT, PINS, module_name="_native_application_pair_8af")


@pytest.fixture
def selected(binding, native, monkeypatch):
    root, row, document, manifest, events, save, make, previous = binding
    selected_transport = replace(previous,
        base_url=f"http://127.0.0.1:{native.server.server_port}/v1",
        secret_ref=native.service.credential_ref, provider_id="go", model=MODEL,
        protocol=transport.NATIVE_PROTOCOL)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", selected_transport)
    row.update({key: getattr(selected_transport, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
    manifest["capabilities"][0]["secret_ref"] = native.service.credential_ref
    manifest["capabilities"][0]["allowed_lanes"].append("application")
    save()
    monkeypatch.setenv(native.service.credential_ref, native.service.credential)
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_interactive")
    monkeypatch.setattr(auth, "_repo_root", lambda: root)
    monkeypatch.setattr(auth, "_oauth_pool_candidates", Mock(side_effect=AssertionError("legacy discovery")))
    monkeypatch.setattr("lib.config.secret", Mock(side_effect=AssertionError("legacy credential")))
    costs, health = [], []
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: health.append(kw))

    def operation(identifier="turn-1", *, prior_admission_possible=False, **changes):
        cfg = {"provider_order": ["oauth", "anthropic"], "workload_profile": "site_interactive",
               "usage_lane": "application", **changes}
        return auth.begin_operation(auth.build_providers(cfg), operation_id=identifier,
            prior_admission_possible=prior_admission_possible)

    return SimpleNamespace(root=root, native=native, row=row, document=document,
        manifest=manifest, events=events, save=save, make=make, transport=selected_transport,
        operation=operation, costs=costs, health=health)


def kwargs(model=MODEL, **changes):
    return {"model": model, "max_tokens": 100,
        "messages": [{"role": "user", "content": "Explain the supplied context."}], **changes}


def invoke(client, model):
    result = client.messages.create(**kwargs(model))
    return result.content[0].text, None, result


def test_actual_owner_two_tool_steps_one_native_turn_then_original_close(selected):
    state, native = selected, selected.native
    native.response["choices"][0].update(finish_reason="tool_calls", message={
        "role": "assistant", "content": None, "tool_calls": [{"id": "read-1", "type": "function",
        "function": {"name": "read", "arguments": '{"symbol":"fixture"}'}}]})
    operation = state.operation()
    provider = operation.providers[0]
    tools = [{"name": "read", "input_schema": {"type": "object"}}]
    def two_steps(client, model):
        first = client.messages.create(**kwargs(model, tools=tools))
        assert first.content[0].input == {"symbol": "fixture"}
        native.response["choices"][0].update(finish_reason="stop", message={
            "role": "assistant", "content": "Grounded final context."})
        history = kwargs()["messages"] + [{"role": "assistant", "content": first.content},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "read-1", "content": "Observed evidence."}]}]
        final = client.messages.create(**kwargs(model, tools=tools, messages=history))
        return final.content[0].text, None, final
    result = auth.make_call(operation.providers, two_steps, context="native-pair")
    assert result == ("Grounded final context.", None, "fabric")
    assert len(native.rows("leases")) == 1 and len(native.posts) == 2
    assert {r["turn_id"] for r in native.rows("application_requests")} == {"turn-1"}
    assert [r["request_id"] for r in native.rows("application_requests")] == ["turn-1:brain:0", "turn-1:brain:1"]
    assert all(post[2] == "Bearer fixture-provider-a" for post in native.posts)
    assert all(json.loads(post[1])["stream"] is False for post in native.posts)
    assert len(state.costs) == 1 and state.costs[0]["input_tokens"] == 22
    operation.close()
    assert provider["_fabric_close"]["closed"] is True
    assert native.rows("leases")[0]["state"] == "released"
    assert len(native.posts) == 2 and provider["model"] == MODEL


@pytest.mark.parametrize("outcome", ["upstream4xx", "upstream5xx", "mismatch"])
def test_original_terminal_failure_records_actual_observed_usage_once(selected, outcome):
    native = selected.native
    native.response_status = 429 if outcome == "upstream4xx" else 503 if outcome == "upstream5xx" else 200
    actual = "other-model" if outcome == "mismatch" else MODEL
    native.response["model"] = actual
    operation = selected.operation()
    provider = operation.providers[0]
    with pytest.raises(auth.FabricProviderError) as caught:
        auth.make_call(operation.providers, invoke)
    assert not caught.value.effect_unknown
    assert provider["_fabric_native_disposition"] == "terminal"
    assert provider["model"] == MODEL and provider["_fabric_last_observation"]["serving_model"] == actual
    assert len(selected.costs) == 1 and selected.costs[0]["model"] == actual
    assert (selected.costs[0]["input_tokens"], selected.costs[0]["output_tokens"]) == (11, 7)
    with pytest.raises(auth.FabricProviderError):
        auth.make_call(operation.providers, invoke)
    operation.close()
    assert len(native.posts) == len(selected.costs) == 1
    assert native.rows("application_requests")[0]["state"] == "terminal"


def test_observed_usage_survives_unknown_native_settlement(selected):
    native = selected.native
    operation = selected.operation()
    provider = operation.providers[0]
    with patch.object(native.gateway, "complete_application", side_effect=OSError("fixture before commit")):
        with pytest.raises(auth.FabricProviderError) as caught:
            auth.make_call(operation.providers, invoke)
    assert caught.value.effect_unknown and native.rows("application_requests")[0]["state"] == "unknown"
    assert len(native.posts) == len(selected.costs) == 1
    assert selected.costs[0]["input_tokens"] == 11 and "turn_total_unknown" in selected.costs[0]["note"]
    usage = auth.fabric_usage(provider)
    assert usage["input_tokens"] is None and usage["completed_input_tokens"] == 11
    operation.close()
    assert not provider["_fabric_close"]["closed"]
    assert native.rows("leases")[0]["state"] in {"held", "rented"}
    assert len(native.posts) == len(selected.costs) == 1


def test_receipt_only_recovery_after_revocation_has_no_second_answer_or_usage(selected):
    native = selected.native
    original = selected.operation()
    assert auth.make_call(original.providers, invoke)[0] == "Fixture answer."
    original.close()
    native.grant["enabled"] = False
    native.save()
    native.router.prices["models"].clear()
    recovery = selected.operation()
    provider = recovery.providers[0]
    with patch.object(native.router, "reserve_application_account", side_effect=AssertionError("fresh admission during recovery")):
        with pytest.raises(auth.FabricProviderError) as caught:
            auth.make_call(recovery.providers, invoke)
    assert not caught.value.effect_unknown and not provider["_fabric_pending"]
    assert provider["_fabric_native_disposition"] == "terminal_receipt_only"
    assert auth.fabric_usage(provider)["usage_state"] == "unknown"
    assert len(native.posts) == len(selected.costs) == 1
    recovery.close()
    assert provider["_fabric_close"]["closed"] is True
    assert len(native.rows("leases")) == 1


def test_original_pending_request_cannot_be_replayed_by_a_fresh_local_binding(selected):
    native = selected.native
    native.block = threading.Event()
    first = selected.operation()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(auth.make_call, first.providers, invoke)
            assert native.arrived.wait(2)
            second = selected.operation()
            retained = second.providers[0]
            with pytest.raises(auth.FabricProviderError) as caught:
                auth.make_call(second.providers, invoke)
            assert caught.value.effect_unknown and retained["_fabric_native_disposition"] == "pending"
            second.close()
            assert not retained["_fabric_close"]["closed"]
            native.block.set()
            assert future.result(timeout=3)[0] == "Fixture answer."
        first.close()
    finally:
        native.block.set()
    assert len(native.posts) == len(native.rows("leases")) == len(selected.costs) == 1


def test_close_and_concurrent_retained_callback_cannot_double_capture_late_usage(selected):
    native = selected.native
    native.block = threading.Event()
    operation = selected.operation()
    retained = list(operation.providers)
    provider = retained[0]
    real_close = native.gateway.close_application_turn
    close_calls = []
    def close(**kw):
        close_calls.append(kw)
        return real_close(**kw)
    try:
        with patch.object(native.gateway, "close_application_turn", side_effect=close):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(auth.make_call, retained, invoke)
                assert native.arrived.wait(2)
                operation.close()
                assert not provider["_fabric_close"]["closed"]
                assert native.rows("leases")[0]["state"] in {"held", "rented"}
                with pytest.raises(auth.FabricProviderError, match="callback_in_progress"):
                    auth.make_call(retained, invoke)
                native.block.set()
                with pytest.raises(auth.FabricProviderError):
                    future.result(timeout=3)
                with pytest.raises(auth.FabricProviderError):
                    auth.make_call(retained, invoke)
            operation.close()
    finally:
        native.block.set()
    assert len(close_calls) == 1 and len(native.posts) == 1 and len(selected.costs) == 1
    assert selected.costs[0]["input_tokens"] == 11
    assert native.rows("application_requests")[0]["state"] == "terminal"
    # A honors the earlier close intent only after its actual terminal receipt.
    assert native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("tokens", [(10**12, 7), (10**12+1, 7), (11, None), (True, 7)])
def test_partial_and_oversized_raw_usage_remains_unknown_without_fabricated_rows(selected, tokens):
    native = selected.native
    native.response["usage"] = {"prompt_tokens": tokens[0], "completion_tokens": tokens[1]}
    operation = selected.operation()
    provider = operation.providers[0]
    auth.make_call(operation.providers, invoke)
    operation.close()
    known = tokens == (10**12, 7)
    assert len(selected.costs) == (1 if known else 0)
    usage = auth.fabric_usage(provider)
    assert usage["usage_state"] == ("known" if known else "unknown")
    if not known:
        assert usage["input_tokens"] is None and usage["completed_input_tokens"] == 0
    receipt = json.loads(native.rows("application_requests")[0]["terminal_receipt"])
    assert provider["_fabric_last_observation"]["input_tokens"] == receipt["usage"]["input_tokens"]
    assert provider["_fabric_last_observation"]["output_tokens"] == receipt["usage"]["output_tokens"]


def test_callback_with_two_actual_models_attributes_usage_separately(selected):
    native = selected.native
    operation = selected.operation()
    provider = operation.providers[0]
    def changed_provider(client, model):
        client.messages.create(**kwargs(model))
        native.response["model"] = "other-model"
        return invoke(client, model)
    with pytest.raises(auth.FabricProviderError):
        auth.make_call(operation.providers, changed_provider)
    operation.close()
    assert [row["model"] for row in selected.costs] == [MODEL, "other-model"]
    assert all(row["input_tokens"] == 11 for row in selected.costs)
    assert provider["model"] == MODEL and len(native.posts) == 2


def test_complete_error_usage_with_unknown_serving_model_is_not_lost_or_relabelled(selected):
    selected.native.response_status = 503
    selected.native.response.pop("model")
    operation = selected.operation()
    provider = operation.providers[0]
    with pytest.raises(auth.FabricProviderError):
        auth.make_call(operation.providers, invoke)
    operation.close()
    assert auth.fabric_usage(provider)["input_tokens"] == 11
    assert provider["_fabric_last_observation"]["serving_model"] is None
    assert len(selected.costs) == 1 and selected.costs[0]["model"] is None
    assert selected.costs[0]["input_tokens"] == 11 and provider["model"] == MODEL


def test_already_bound_operation_retains_original_identity_or_refuses_mismatch(selected):
    operation = selected.operation("bound-original")
    retained = operation.providers
    assert auth.begin_operation(retained).operation_id == "bound-original"
    assert auth.begin_operation(retained, operation_id="bound-original").operation_id == "bound-original"
    with pytest.raises(auth.FabricProviderError, match="identity_mismatch"):
        auth.begin_operation(retained, operation_id="different-original")
    operation.close()
    assert selected.native.posts == [] and selected.native.rows("leases") == []


def test_trusted_restored_admission_survives_prebyte_failure_and_closes_original(selected):
    first = selected.operation()
    auth.make_call(first.providers, invoke)
    # The existing caller's journal says this ORIGINAL turn may own admission.
    # A new client must retain that fact even if its recovery socket fails.
    restored = selected.operation(prior_admission_possible=True)
    provider = restored.providers[0]
    with patch.object(transport._NativeConnection, "connect", side_effect=ConnectionRefusedError("fixture before bytes")):
        with pytest.raises(auth.FabricProviderError) as caught:
            auth.make_call(restored.providers, invoke)
    assert caught.value.effect_unknown
    assert auth.fabric_usage(provider)["usage_state"] == "unknown"
    restored.close()
    assert provider["_fabric_close"]["attempted"] and provider["_fabric_close"]["closed"]
    assert selected.native.rows("leases")[0]["state"] == "released"
    assert len(selected.native.posts) == len(selected.costs) == 1


def test_close_error_never_masks_known_usage_or_repeats_an_attempt(selected):
    operation = selected.operation()
    provider = operation.providers[0]
    auth.make_call(operation.providers, invoke)
    native_client = provider["client"]._client
    with patch.object(native_client, "close", side_effect=OSError("fixture local close failure")) as close:
        operation.close()
        operation.close()
    assert close.call_count == 1 and provider["_fabric_close"]["effect_unknown"]
    assert auth.fabric_usage(provider)["input_tokens"] == 11 and len(selected.costs) == 1


def test_pristine_or_known_prebyte_failure_never_sends_close(selected, monkeypatch):
    pristine = selected.operation()
    provider = pristine.providers[0]
    pristine.close()
    assert provider["_fabric_close"]["attempted"] is False
    operation = selected.operation("before-bytes")
    provider = operation.providers[0]
    def fail(_):
        raise ConnectionRefusedError("fixture offline socket")
    monkeypatch.setattr(transport._NativeConnection, "connect", fail)
    with pytest.raises(auth.FabricProviderError) as caught:
        auth.make_call(operation.providers, invoke)
    assert not caught.value.effect_unknown
    operation.close()
    assert provider["_fabric_close"]["attempted"] is False
    assert selected.native.rows("leases") == [] and selected.native.posts == []
    assert selected.costs == []


def test_usage_sink_none_preserves_known_error_observation_and_health(selected):
    selected.native.response_status = 503
    operation = selected.operation(usage_sink="none")
    provider = operation.providers[0]
    with pytest.raises(auth.FabricProviderError):
        auth.make_call(operation.providers, invoke)
    operation.close()
    assert selected.costs == [] and len(selected.health) == 1
    assert auth.fabric_usage(provider)["input_tokens"] == 11


def test_native_recipe_and_inspection_are_pure_and_original_id_fails_before_secret(selected):
    factory = selected.make()
    snapshot = factory.inspect()
    assert len(snapshot["transport_identity"]) == 64
    assert selected.events == [] and selected.native.rows("leases") == []
    with pytest.raises(auth.FabricProviderError):
        auth.build_fabric_provider(factory, request_id="unchanged/original")
    assert selected.events == [] and selected.native.posts == []
    operation = selected.operation()
    assert selected.events == ["credential", "client"]
    operation.close()


@pytest.mark.parametrize("field,value", [("protocol", transport.LEGACY_PROTOCOL),
    ("base_url", "http://127.0.0.1:12345/v1"), ("secret_ref", "OTHER_NATIVE_SERVICE_TOKEN")])
def test_valid_same_model_transport_change_invalidates_inspection_and_cache(selected, monkeypatch, field, value):
    factory = selected.make()
    inspected = factory.inspect()
    narrowed = factory.with_inspection(inspected)
    before = news_translate._fabric_cache_identity(inspected, "shared_fabric", {}, "en")
    changed = replace(selected.transport, **{field: value})
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", changed)
    selected.row.update({key: getattr(changed, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
    if field == "secret_ref":
        selected.manifest["capabilities"][0]["secret_ref"] = value
        monkeypatch.setenv(value, selected.native.service.credential)
    selected.save()
    after = factory.inspect()
    assert after["model"] == inspected["model"] and after["transport_identity"] != inspected["transport_identity"]
    assert news_translate._fabric_cache_identity(after, "shared_fabric", {}, "en") != before
    with pytest.raises(auth.FabricProviderError):
        auth.build_fabric_provider(narrowed, request_id="turn-1")
    assert selected.events == [] and selected.native.rows("leases") == [] and selected.native.posts == []
