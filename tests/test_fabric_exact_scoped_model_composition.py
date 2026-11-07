"""Exact scoped models through real C/auth/client/B/picker/A/H.

The supplied Mastermind checkout is pinned by file identity. Grants,
qualification, service credentials and the loopback upstream are synthetic.
No account enrollment, provider entitlement or deployment is established.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from engine import fabric_inference_client as transport
from engine import llm_auth as auth, provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401

_CLIENT = transport.FabricInferenceClient
SOURCE_ROOT = os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT")
pytestmark = pytest.mark.skipif(not SOURCE_ROOT, reason="paired exact-scoped Mastermind source required")
MODEL = "qwen3.8-flash"
NATIVE_PINS = {
    "candidate/commission_deadline.py": "fade630ed75c1b93334a5711a6df7a554fbd24ee",
    "candidate/go_shim.py": "066d87cd23275204fb6d30af45ac03db1d4dbb4f",
    "candidate/lease_broker.py": "d8577c6ee5cc9bd3e7fc22905530f4755b860ae0",
    "candidate/go_lease_gateway.py": "e21b6d6a4e4230fce5f55d90820c6391d4b79324",
    "candidate/go_lease_capability.py": "38856700331b3fb3a7706a5745e23fb7b3d18cf0",
    "candidate/application_http_transports.py": "c37181993a36da216c77778ebaeaae3ebe190a09",
    "candidate/provider_outcome.py": "981f35a01183e83fdb9f0b8a4175b290cdeb85f8",
    "candidate/quota_circuit.py": "1583a6ba773e56dbc3f295b65ffc08dea2d31d48",
    "candidate/pick.py": "d17447c3c9f472b061733e36fa49a7f8d7e34ee5",
    "candidate/pool_ledger.py": "61dc4d5e83172e6c647d058ec844f00a0b3955a6",
    "source/model_tier.py": "96093c2747d2dda69b3f2255cb84e656355c87ea",
    "source/pool_status.py": "02922043357d63b4bcfa3791899df27a5c42be12",
    "tests/_offline_boundary.py": "e511ab65fe1cd30bf4d2addac6700ca43c3468da",
    "tests/test_go_application_handler_composition.py": "13ebd6bcee5167926807d7ccdc63bcabed0cf1b1",
    "tests/test_application_turn_admission.py": "4cc542888358bf6b46a1e78c581af5ef2f7178aa",
    "tests/test_application_registered_pool_selection.py": "754d6d8c1a6391fcfefdbd26417f87944403ea2b",
    "tests/test_application_registered_pool_composition.py": "3c1bb6f596fa8821af19c71eb2ea2327147b19eb",
    "tests/test_application_auto_request.py": "6e990aa3be10cea5dc6ee19c621bd0b3583de909",
    "tests/test_application_cross_pool_auto.py": "0d70a47906a23176d5eaed71a4575e925a500341"
}


@pytest.fixture
def exact_native():
    root = Path(SOURCE_ROOT).resolve() / "ops/native_fabric/quota_continuity"
    for relative, expected in NATIVE_PINS.items():
        raw = (root / relative).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == expected, relative
    previous_path = list(sys.path)
    sys.path[:0] = [str(root / "tests"), str(root / "candidate"), str(root / "source"),
                   str(Path(SOURCE_ROOT).resolve())]
    for name in ("lease_broker", "go_lease_gateway", "go_lease_capability", "application_http_transports"):
        loaded = sys.modules.get(name)
        if loaded is not None:
            assert Path(loaded.__file__).resolve() == root / "candidate" / (name + ".py")
    from test_application_cross_pool_auto import CrossPoolHTTPFixture
    native = CrossPoolHTTPFixture()
    try:
        native.setUp()
        for grant in native.document["application_grants"]:
            grant["workloads"] = ["site_batch"]
        native.save()
        native.configure(["go", "bailian", "codex-native"], workload="site_batch")
        native.response = native.responses["bailian"]
        yield native
    finally:
        native.doCleanups()
        sys.path[:] = previous_path


@pytest.fixture
def exact(binding, exact_native, monkeypatch):
    root, row, document, manifest, events, save, make, previous = binding
    native = exact_native
    monkeypatch.setattr(transport, "FabricInferenceClient", _CLIENT)
    scope = {"schema": "mastermind.application_route_scope.v1", "pools": ["bailian", "codex-native", "go"]}
    shared = replace(previous, protocol=transport.NATIVE_PROTOCOL, automatic=True,
                     provider_id=None, model=None, base_url=f"http://127.0.0.1:{native.server.server_port}/v1")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", shared)
    row.update({key: getattr(shared, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
    row["route_scope"] = scope
    transport_id = "native_fabric_macro_batch_auto_v1"
    actual = replace(owner._APPLICATION_FABRIC_TRANSPORTS[transport_id],
        base_url=f"http://127.0.0.1:{native.server.server_port}/v1",
        secret_ref="MACRO_APPLICATION_TOKEN", qualified=True, application_allowed=True)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, transport_id, actual)
    batch = {**{key: getattr(actual, key) for key in owner._APPLICATION_IDENTITY_FIELDS},
        "transport_id": transport_id, "enabled": True, "application_allowed": True,
        "qualification": owner.PROFILE_QUALIFIED_CANARY, "qualification_ref": "fixture:exact-batch",
        "qualified_until": time.time() + 3600, "route_scope": scope}
    document["application_fabric_modes"]["macro_batch_fabric"] = batch
    manifest["capabilities"].append({"capability_id": actual.capability_id, "secret_ref": actual.secret_ref,
        "kill_state": "active", "allowed_lanes": ["catalyst-tone"]})
    from test_application_registered_pool_composition import SERVICE_TOKEN
    monkeypatch.setenv(actual.secret_ref, SERVICE_TOKEN)
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    save()
    def factory():
        return owner.make_application_fabric_factory(
            mode_id="shared_fabric", lane="catalyst-tone", root=root,
            workload_cfg={"provider_order": ["fabric"], "workload_profile": "site_batch"})
    return SimpleNamespace(root=root, native=native, row=row, batch=batch, manifest=manifest,
        document=document, events=events, save=save, factory=factory, token=SERVICE_TOKEN)


def call_kwargs(**changes):
    return dict({"model": MODEL, "system": "Be exact.",
        "messages": [{"role": "user", "content": "Exact evidence question. /no_think"}],
        "max_tokens": 128, "temperature": 0, "reasoning_effort": "none", "stream": False}, **changes)


def bound(state, operation="exact:original", *, prior=False):
    factory = state.factory().with_requested_model(MODEL)
    snapshot = factory.inspect()
    return auth.build_fabric_provider(factory.with_inspection(snapshot), request_id=operation,
        workload_cfg={"workload_profile": "site_batch", "usage_sink": "none"},
        prior_admission_possible=prior), snapshot


def test_pure_immutable_narrowing_precedes_fresh_configuration_and_capability_reads(exact):
    factory = exact.factory()
    with patch.object(owner, "_application_fabric_mode", side_effect=AssertionError("configuration read")), \
         patch.object(owner, "_resolve_credential", side_effect=AssertionError("credential")), \
         patch.object(transport, "FabricInferenceClient", side_effect=AssertionError("client")):
        narrowed = factory.with_requested_model(MODEL)
        assert narrowed.with_requested_model(MODEL) == narrowed
    assert factory._requested_model is None
    assert narrowed._requested_model == MODEL
    with patch.object(owner, "_application_fabric_mode", wraps=owner._application_fabric_mode) as config:
        snapshot = narrowed.inspect()
    assert config.call_count >= 1
    assert exact.events == []
    assert snapshot["schema"] == transport.EXACT_INSPECTION_SCHEMA
    assert snapshot["requested_model"] == MODEL
    assert "provider" not in snapshot and "model" not in snapshot
    assert snapshot["workload_policy"]["profiles"] == ["site_batch"]
    assert exact.native.rows("leases") == []


@pytest.mark.parametrize("model", [None, "", False, 5, " qwen3.8-flash", "qwen3.8-flash ", "bad\nmodel"])
def test_invalid_narrowing_is_pure_and_refuses(exact, model):
    with pytest.raises(owner.ApplicationFabricBindingError):
        exact.factory().with_requested_model(model)
    assert exact.events == [] and exact.native.rows("leases") == []


def test_model_and_inspection_commitments_cannot_be_retargeted(exact):
    factory = exact.factory()
    automatic = factory.inspect()
    assert automatic["schema"] == transport.AUTO_INSPECTION_SCHEMA and automatic["requested_model"] is None
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.with_inspection(automatic).with_requested_model(MODEL)
    narrowed = factory.with_requested_model(MODEL)
    snapshot = narrowed.inspect()
    assert snapshot["transport_identity"] != automatic["transport_identity"]
    with pytest.raises(owner.ApplicationFabricBindingError):
        narrowed.with_requested_model("qwen3.8-max")
    frozen = narrowed.with_inspection(snapshot)
    snapshot["route_scope"]["pools"].clear()
    assert frozen.inspect()["route_scope"]["pools"]
    exact.batch["route_scope"] = {"schema": "mastermind.application_route_scope.v1", "pools": ["go"]}
    exact.save()
    with pytest.raises(owner.ApplicationFabricBindingError):
        frozen.inspect()
    assert exact.events == [] and exact.native.rows("leases") == []


@pytest.mark.parametrize("tamper", ["profile", "capability", "token", "service"])
def test_fresh_owner_and_workload_checks_precede_credentials(exact, tamper):
    factory = exact.factory().with_requested_model(MODEL)
    snapshot = factory.inspect()
    if tamper == "profile":
        caller = {"workload_profile": "site_interactive"}
    else:
        caller = {"workload_profile": "site_batch"}
        if tamper == "capability":
            exact.manifest["capabilities"][-1]["kill_state"] = "killed"
        elif tamper == "token":
            exact.batch["secret_ref"] = "TEST_FABRIC_PROXY_TOKEN"
        else:
            exact.batch["transport_id"] = "native_fabric_macro_analysis_auto_v1"
        exact.save()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.with_inspection(snapshot)._bind_with_workload(caller, operation_id="exact:refuse")
    assert exact.events == [] and exact.native.rows("leases") == []


def test_actual_c_b_a_h_exact_request_result_usage_and_close(exact):
    provider, inspection = bound(exact)
    assert provider["model"] == MODEL and provider["provider"] is None
    response = provider["client"].messages.create(**call_kwargs())
    assert response.model == MODEL and response.content[0].text == "Bailian fixture answer."
    observation = auth.fabric_observation(provider)
    assert observation is response.application_observation
    document = observation.document
    route = document["routing"]
    assert route["schema"] == "mastermind.fabric_application_route.v2"
    assert route["requested_model"] == route["selected_model"] == document["serving_model"] == MODEL
    assert route["pool"] == "bailian" and route["routed_request_digest"] is None
    expected_step, original = transport._request(
        {**call_kwargs(), "request_id": "exact:original:brain:0"}, MODEL, False, exact_scoped=True)
    request = exact.native.rows("application_requests")[0]
    assert route["request_digest"] == request["request_digest"] == transport._auto_request_digest(json.loads(original))
    assert request["routed_request_digest"] is None and request["state"] == "terminal"
    assert transport.validate_auto_observation(document, inspection, operation_id="exact:original",
        request_id=expected_step, request_digest=route["request_digest"], routed_request_digest=None,
        max_tokens=128, require_success=True) == document
    wire = json.loads(exact.native.logical_posts[0].body)
    assert wire["model"] == MODEL and wire["temperature"] == 0
    assert wire["reasoning"] == {"effort": "none"} and wire["stream"] is False
    assert wire["max_output_tokens"] == 128 and "/no_think" in json.dumps(wire["input"])
    assert auth.fabric_usage(provider)["usage_state"] == "known"
    assert (auth.fabric_usage(provider)["input_tokens"], auth.fabric_usage(provider)["output_tokens"]) == (11, 7)
    before = observation.document
    auth.close_fabric_provider(provider)
    assert auth.fabric_observation(provider).document == before
    assert len(exact.native.logical_posts) == len(exact.native.rows("leases")) == 1
    assert exact.native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("changes", [
    {"model": "qwen3.8-max"}, {"temperature": False}, {"temperature": 1},
    {"reasoning_effort": "low"}, {"stream": True}, {"tools": []}, {"stop_sequences": []},
])
def test_unsupported_exact_call_refuses_without_admission(exact, changes):
    provider, _ = bound(exact)
    with pytest.raises(auth.FabricProviderError):
        provider["client"].messages.create(**call_kwargs(**changes))
    assert exact.native.rows("leases") == [] and exact.native.logical_posts == []


@pytest.mark.parametrize("omitted", ["temperature", "reasoning_effort"])
def test_partial_control_pair_refuses_without_admission(exact, omitted):
    provider, _ = bound(exact)
    kwargs = call_kwargs()
    kwargs.pop(omitted)
    with pytest.raises(auth.FabricProviderError):
        provider["client"].messages.create(**kwargs)
    assert exact.native.rows("leases") == [] and exact.native.logical_posts == []


def test_v2_and_fixed_clients_do_not_inherit_new_control_fields(exact):
    automatic = exact.factory()
    provider = auth.build_fabric_provider(automatic, request_id="auto:controls",
        workload_cfg={"workload_profile": "site_batch"})
    with pytest.raises(auth.FabricProviderError):
        provider["client"].messages.create(**call_kwargs(model=None))
    assert exact.native.rows("leases") == []
    with pytest.raises(transport.FabricInferenceError):
        transport._request({**call_kwargs(), "request_id": "fixed:step"}, MODEL, False)
    snapshot = exact.factory().with_requested_model(MODEL).inspect()
    with pytest.raises(transport.FabricInferenceError):
        _CLIENT(base_url=f"http://127.0.0.1:{exact.native.server.server_port}/v1",
            proxy_token=exact.token, model=None, protocol=transport.NATIVE_PROTOCOL,
            operation_id="wrong:binding", auto_inspection=snapshot)


def test_terminal_served_mismatch_preserves_actual_usage_without_answer(exact):
    exact.native.response["model"] = "qwen3.8-max"
    provider, inspection = bound(exact)
    with pytest.raises(auth.FabricProviderError):
        provider["client"].messages.create(**call_kwargs())
    document = auth.fabric_observation(provider).document
    assert document["routing"]["selected_model"] == MODEL
    assert document["serving_model"] == "qwen3.8-max"
    assert auth.fabric_usage(provider)["completed_input_tokens"] == 11
    assert len(exact.native.logical_posts) == 1
    with pytest.raises(transport.FabricInferenceError):
        transport.validate_auto_observation(document, inspection, operation_id="exact:original",
            request_id=document["request_id"], request_digest=document["routing"]["request_digest"],
            routed_request_digest=None, max_tokens=128, require_success=True)


@pytest.mark.parametrize("corruption", ["version", "requested", "selected", "routed_digest", "shape"])
def test_correlated_malformed_route_retains_usage_but_no_pool_attribution(exact, corruption):
    handler = exact.native.server.RequestHandlerClass
    original_delivery = handler._application_delivery
    def corrupt(instance, observed):
        body = json.loads(observed.body)
        route = body["application"]["routing"]
        if corruption == "version":
            route["schema"] = "mastermind.fabric_application_route.v1"
        elif corruption == "requested":
            route["requested_model"] = None
        elif corruption == "selected":
            route["selected_model"] = "qwen3.8-max"
        elif corruption == "routed_digest":
            route["routed_request_digest"] = "a" * 64
        else:
            body["application"]["routing"] = []
        return original_delivery(instance, replace(observed, body=json.dumps(body).encode()))
    provider, _ = bound(exact)
    with patch.object(handler, "_application_delivery", corrupt):
        with pytest.raises(auth.FabricProviderError) as error:
            provider["client"].messages.create(**call_kwargs())
    assert error.value.effect_unknown is True
    usage = auth.fabric_usage(provider)
    assert (usage["completed_input_tokens"], usage["completed_output_tokens"]) == (11, 7)
    assert usage["usage_state"] == "unknown"
    assert auth.fabric_observation(provider) is None
    assert json.loads(provider["_fabric_usage_observations"][0][3])["provider"] == "unknown"
    assert len(exact.native.logical_posts) == 1


def test_original_receipt_recovery_never_sends_or_counts_usage_twice(exact):
    first, _ = bound(exact)
    first["client"].messages.create(**call_kwargs())
    auth.close_fabric_provider(first)
    restored, _ = bound(exact, prior=True)
    with pytest.raises(auth.FabricProviderError):
        restored["client"].messages.create(**call_kwargs())
    assert auth.fabric_observation(restored) is None
    assert auth.fabric_usage(restored)["usage_state"] == "unknown"
    assert auth.fabric_usage(restored)["completed_input_tokens"] == 0
    assert len(exact.native.logical_posts) == len(exact.native.rows("application_requests")) == 1
