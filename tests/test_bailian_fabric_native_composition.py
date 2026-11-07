"""Actual Admin/shared-client -> B/A/H -> loopback Responses composition.

Qualification, credentials and upstream replies are synthetic. This proves
the product code path and source pair, not production availability or policy.
"""
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from admin import orchestrator_chat as admin
from engine import fabric_inference_client as client
from engine import llm_auth as auth
from engine import provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401

SOURCE_ROOT = os.environ.get("MM_FABRIC_HTTP_SOURCE_ROOT")
pytestmark = pytest.mark.skipif(not SOURCE_ROOT, reason="paired HTTP native source required")
_CLIENT = client.FabricInferenceClient
NATIVE = "ops/native_fabric/quota_continuity/"
PINS = {
    "control_plane/codex_provider_realm.py": "eeea4c0fafc7e6df5c534c731cb6046bbe4d3f37",
    "control_plane/provider_protocols.py": "92452237ac3956e8104e45ab9ee386c2fa016b76",
    "control_plane/fs_security.py": "16617789dc115b5748a3e72cc0d9a53fbc368918",
    NATIVE + "candidate/commission_deadline.py": "fade630ed75c1b93334a5711a6df7a554fbd24ee",
    NATIVE + "candidate/go_shim.py": "34736f256c5f32f72dcbb93517e60dda01164baf",
    NATIVE + "candidate/lease_broker.py": "552594fd45ddf19da1f850ac59491baa0aafa4ed",
    NATIVE + "candidate/go_lease_gateway.py": "e77a5805231b055bd776ce37b3566aba6d9c9027",
    NATIVE + "candidate/go_lease_capability.py": "13e6b2d43cbb2933512e6e46d27a431e7813af88",
    NATIVE + "candidate/application_http_transports.py": "b0b8404b45dd0a3e73a34430c2ef3a28b1edbf6d",
    NATIVE + "candidate/provider_outcome.py": "4236303eb3abfa7c9dcad4d3e1a5454f15600c98",
    NATIVE + "candidate/quota_circuit.py": "b119865ba77908eaf971e86e923075d7da365ffc",
    NATIVE + "source/model_tier.py": "96093c2747d2dda69b3f2255cb84e656355c87ea",
    NATIVE + "source/pool_status.py": "02922043357d63b4bcfa3791899df27a5c42be12",
    NATIVE + "source/application_http_transports.py.preimage": "a116d8c671594552dd5c14f46f91981cd7c15f43",
    NATIVE + "rollout/application_http_realm_projection.py": "684c54d5c9d8dbdd5bc046d123af31d20fc99dd1",
    NATIVE + "tests/_offline_boundary.py": "e511ab65fe1cd30bf4d2addac6700ca43c3468da",
    NATIVE + "tests/test_application_turn_admission.py": "efe876eec40dc8885dbc0059915f2401146be969",
    NATIVE + "tests/test_go_application_handler_composition.py": "13ebd6bcee5167926807d7ccdc63bcabed0cf1b1",
    NATIVE + "tests/test_bailian_application_handler_composition.py": "7726a3e76de484afb4835f54ae8074273efa767e",
}


@pytest.fixture(params=["source", "sealed"])
def native_http(monkeypatch, request):
    root = Path(SOURCE_ROOT).resolve()
    for path, expected in PINS.items():
        raw = (root / path).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == expected, path
    native = root / NATIVE
    for path in (root, native / "source", native / "candidate", native / "rollout", native / "tests"):
        monkeypatch.syspath_prepend(str(path))
    for name in ("lease_broker", "go_lease_gateway", "go_lease_capability", "application_http_transports"):
        loaded = sys.modules.get(name)
        if loaded is not None:
            assert Path(loaded.__file__).resolve() == native / "candidate" / (name + ".py")
    spec = importlib.util.spec_from_file_location("_paired_bailian_application_fixture",
        native / "tests/test_bailian_application_handler_composition.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    fixture = module.BailianHTTPFixture()
    fixture.setUp()
    try:
        if request.param == "sealed":
            from application_http_realm_projection import compile_projection_bytes, TRANSPORT_SOURCE_PATH, INPUT_SOURCES
            from go_lease_gateway import GoLeaseGateway
            import lease_broker

            inputs = {entry["path"]: (root / (NATIVE + "source/application_http_transports.py.preimage"
                if entry["path"] == TRANSPORT_SOURCE_PATH else entry["path"])).read_bytes()
                for entry in INPUT_SOURCES}
            projection = compile_projection_bytes(inputs)
            digest = hashlib.sha256(projection).hexdigest()
            fixture.driver = module.BailianResponsesDriver(
                transport=fixture.driver._transport, clock=lambda: fixture.clock[0],
                realm_projection=projection, projection_sha256=digest)
            fixture.http_binding = replace(fixture.http_binding,
                driver=fixture.driver, source_projection_sha256=digest)
            recipes = tuple(fixture.http_binding.recipe(model)
                for model in sorted(fixture.driver.identity.allowed_models))
            _, fixture.recipe_digest = lease_broker._application_http_recipe(
                fixture.http_binding.recipe("qwen3.8-flash"), pool="bailian", model="qwen3.8-flash")
            fixture.grant["recipe_digest"] = fixture.recipe_digest
            fixture.save()
            assert fixture.rows("leases") == fixture.rows("application_requests") == []
            fixture.gateway = GoLeaseGateway(str(fixture.directory / "leases.sqlite"),
                fixture.router.accounts, set(fixture.router.prices["models"]),
                clock=lambda: fixture.clock[0], signing_key=b"k" * 32,
                application_broker=fixture.broker, application_http_recipes=recipes,
                application_http_accounts=fixture.http_binding.accounts)
            fixture.server = fixture.go.make_server(fixture.router,
                lease_gateway=fixture.gateway, application_services=(fixture.service,),
                application_http_binding=fixture.http_binding, worker_capabilities_enabled=False)
            fixture.server.handle_error = lambda *args: None
            fixture._serve(fixture.server)
            fixture.sealed_projection_digest = digest
        else:
            fixture.sealed_projection_digest = None
        yield fixture
    finally:
        fixture.doCleanups()
        sys.modules.pop(spec.name, None)


@pytest.fixture
def selected_http(binding, native_http, monkeypatch):
    root, row, document, manifest, events, save, make, previous = binding
    native = native_http
    transport = replace(previous, base_url=f"http://127.0.0.1:{native.server.server_port}/v1",
        secret_ref=native.service.credential_ref, provider_id="bailian", model="qwen3.8-flash",
        protocol=client.NATIVE_PROTOCOL, native_recipe_digest=native.recipe_digest)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", transport)
    row.update({key: getattr(transport, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
    manifest["capabilities"][0]["secret_ref"] = native.service.credential_ref
    save()
    monkeypatch.setenv(native.service.credential_ref, native.service.credential)
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_interactive")
    monkeypatch.setattr(auth, "_repo_root", lambda: root)
    monkeypatch.setattr(auth, "_oauth_pool_candidates", Mock(side_effect=AssertionError("legacy discovery")))
    monkeypatch.setattr("lib.config.secret", Mock(side_effect=AssertionError("legacy credential")))
    monkeypatch.setattr(admin, "_rate_ok", lambda: True)
    monkeypatch.setattr(admin, "_degraded_reply", lambda _root, reason: "Unavailable: " + reason)
    costs, closes, health = [], [], []
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: health.append(kw))
    close = _CLIENT.close
    def observed_close(actual):
        closes.append(actual.operation_id)
        return close(actual)
    monkeypatch.setattr(_CLIENT, "close", observed_close)
    def chat():
        return admin.chat("Explain the measured pipeline state.", root=root,
            fabric_selected=True, fabric_provider_factory=make(), request_id="admin:bailian-original")
    return SimpleNamespace(root=root, row=row, document=document, manifest=manifest, events=events,
        save=save, make=make, transport=transport, native=native, costs=costs, closes=closes, health=health, chat=chat)


def test_admin_actual_two_step_response_one_admission_and_existing_usage_owner(selected_http):
    state = selected_http
    outputs = [
        [{"type": "function_call", "call_id": "read-1", "name": "read_health", "arguments": "{}"}],
        [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Measured pipeline context."}]}],
    ]
    def answer():
        assert outputs, "unexpected replacement request"
        state.native.response["output"] = outputs.pop(0)
    state.native.on_upstream = answer
    result = state.chat()
    assert not result["degraded"], result
    assert result["tool_call_census"] == {"read_health": 1}
    assert result["usage_state"] == "known" and result["input_tokens"] == 22
    assert len(state.native.posts) == 2 and len(state.native.rows("leases")) == 1
    assert state.closes == ["admin:bailian-original"]
    assert state.native.rows("leases")[0]["state"] == "released"
    assert {row["turn_id"] for row in state.native.rows("application_requests")} == {"admin:bailian-original"}
    assert len(state.costs) == 1 and state.costs[0]["model"] == "qwen3.8-flash"
    assert state.costs[0]["input_tokens"] == 22 and state.native.usage_rows() == []
    if state.native.sealed_projection_digest:
        assert state.native.http_binding.source_projection_sha256 == state.native.sealed_projection_digest
        assert state.native.http_binding.source_projection_sha256 != "a" * 64
        assert state.native.recipe_digest != state.native.sealed_projection_digest


@pytest.mark.parametrize("model", ["qwen3.8-flash", "different-model", None])
def test_admin_known_error_or_mismatch_preserves_actual_usage_and_releases(selected_http, model):
    state = selected_http
    state.native.response_status = 503 if model != "different-model" else 200
    if model is None:
        state.native.response.pop("model")
    else:
        state.native.response["model"] = model
    result = state.chat()
    assert result["degraded"] and result["usage_state"] == "known"
    assert result["input_tokens"] == 11
    assert len(state.costs) == len(state.native.posts) == len(state.closes) == 1
    assert state.costs[0]["model"] == model
    assert state.native.rows("leases")[0]["state"] == "released"


def test_admin_unknown_original_http_effect_does_not_redispatch_or_free(selected_http):
    state = selected_http
    state.native.partial = True
    result = state.chat()
    assert result["degraded"] and result["usage_state"] == "unknown"
    assert len(state.native.posts) == len(state.closes) == 1
    assert state.native.rows("application_requests")[0]["state"] == "unknown"
    assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
    assert state.costs == []


def test_inspection_commits_recipe_before_credential_and_native_header_is_required(selected_http, monkeypatch):
    state = selected_http
    factory = state.make()
    identity = factory.inspect()
    narrowed = factory.with_inspection(identity)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1",
        replace(state.transport, native_recipe_digest="b" * 64))
    with pytest.raises(owner.ApplicationFabricBindingError, match="identity_changed"):
        narrowed._bind_with_workload(operation_id="admin:original")
    assert state.events == state.native.posts == []
    result = state.chat()
    assert result["degraded"]
    assert state.native.rows("leases") == state.native.credential_reads == state.native.posts == state.costs == []


@pytest.mark.parametrize("value", ["", "b" * 63, True, "G" * 64])
def test_invalid_recipe_refuses_before_service_credential(selected_http, monkeypatch, value):
    state = selected_http
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1",
        replace(state.transport, native_recipe_digest=value))
    with pytest.raises(owner.ApplicationFabricBindingError, match="recipe_invalid"):
        state.make()._bind_with_workload(operation_id="admin:original")
    assert state.events == state.native.posts == []


def test_missing_http_recipe_refuses_before_native_admission_or_provider_credential(selected_http, monkeypatch):
    state = selected_http
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1",
        replace(state.transport, native_recipe_digest=None))
    result = state.chat()
    assert result["degraded"]
    assert state.native.rows("leases") == state.native.rows("application_requests") == []
    assert state.native.credential_reads == state.native.posts == state.costs == []


def test_recipe_cannot_be_sent_on_legacy_protocol(selected_http, monkeypatch):
    state = selected_http
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1",
        replace(state.transport, protocol=client.LEGACY_PROTOCOL))
    with pytest.raises(owner.ApplicationFabricBindingError, match="recipe_invalid"):
        state.make()._bind_with_workload(operation_id="admin:original")
    assert state.events == state.native.posts == []
    with pytest.raises(client.FabricInferenceError, match="fabric_recipe_invalid"):
        _CLIENT(base_url="http://127.0.0.1:8311/v1", proxy_token="synthetic-proxy-token-for-offline-test",
            model="qwen3.8-flash", protocol=client.LEGACY_PROTOCOL,
            native_recipe_digest=state.transport.native_recipe_digest)


def test_pool_capability_cannot_be_substituted_for_service_credential(selected_http, monkeypatch):
    state = selected_http
    monkeypatch.setenv(state.native.service.credential_ref, "app2." + "f" * 40)
    with pytest.raises(client.FabricInferenceError, match="fabric_binding_invalid"):
        state.make()._bind_with_workload(operation_id="admin:original")
    assert state.native.rows("leases") == state.native.credential_reads == state.native.posts == []


def test_original_recipe_recovers_receipt_after_current_recipe_and_grant_change(selected_http, monkeypatch):
    state = selected_http
    import lease_broker

    def operation():
        providers = auth.build_providers(
            {"workload_profile": "site_interactive", "provider_order": ["fabric"]},
            fabric_selected=True, fabric_provider_factory=state.make(), request_id="http:recovery")
        return auth.begin_operation(providers, context="bailian-recovery")

    def invoke(actual_client, model):
        response = actual_client.messages.create(model=model, max_tokens=100,
            messages=[{"role": "user", "content": "Original supplied question."}])
        return response.content[0].text, None, response

    with operation() as original:
        assert auth.make_call(original.providers, invoke, context="bailian-recovery")[0] == "Bailian fixture answer."
    reads = list(state.native.credential_reads)
    state.native.grant["enabled"] = False
    state.native.save()
    changed = {**state.native.http_binding.recipe("qwen3.8-flash"), "source_projection_sha256": "b" * 64}
    state.native.gateway._application_http_recipes[("bailian", "qwen3.8-flash")] = lease_broker._application_http_recipe(
        changed, pool="bailian", model="qwen3.8-flash")
    monkeypatch.setattr(state.native.driver, "prepare_request", Mock(side_effect=AssertionError("recompiled original")))
    monkeypatch.setattr(state.native.driver, "preflight_credential", Mock(side_effect=AssertionError("credential on recovery")))
    with operation() as recovered:
        retained = recovered.providers[0]
        with pytest.raises(auth.FabricProviderError):
            auth.make_call(recovered.providers, invoke, context="bailian-recovery")
        assert retained["_fabric_native_disposition"] == "terminal_receipt_only"
        assert auth.fabric_usage(retained)["usage_state"] == "unknown"
    assert retained["_fabric_close"]["closed"]
    assert state.native.credential_reads == reads
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    assert state.closes == ["http:recovery", "http:recovery"]
    assert len(state.health) == 2 and state.health[0]["ok"] and not state.health[1]["ok"]
