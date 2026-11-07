"""Explicit generic AUTO workload authorities through real C/B/SQLite A.

Qualification, credentials, grants and upstream output are synthetic. The actual
factory maps each declared profile to its separate authenticated native service.
"""
from dataclasses import replace
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from engine import fabric_inference_client as transport
from engine import llm_auth as auth, provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_service_auto_composition import auto_native, auto_services, MODEL, _fixed  # noqa: F401

AUTHORITIES = (
    ("macro_batch_fabric", "site_batch", "native_fabric_macro_batch_auto_v1",
     ["catalyst-tone", "master-brain", "macro-news", "china-news", "china-news-intel",
      "catalyst-stock", "qual-extraction", "translate-profiles", "special-situations", "trumpflow-extract"]),
    ("macro_analysis_fabric", "lobe_analysis", "native_fabric_macro_analysis_auto_v1", ["cortex"]),
    ("macro_portfolio_fabric", "portfolio_analysis", "native_fabric_macro_portfolio_auto_v1",
     ["research-portfolio"]),
)


@pytest.fixture
def auto_workloads(auto_services, monkeypatch):
    state = auto_services
    native = state.native
    scope = {"schema": "mastermind.application_route_scope.v1", "pools": ["go"]}
    bindings = list(state.bindings)
    templates = [dict(row) for row in state.grants if row["principal_id"] == "shared_fabric"]
    grants = list(state.grants)
    for record, profile, transport_id, lanes in AUTHORITIES:
        base = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
        credential = "synthetic-" + record + "-credential-0123456789abcdef"
        monkeypatch.setenv(base.secret_ref, credential)
        state.credentials[record] = credential
        state.workloads[record] = profile
        state.records[record] = {**{key: getattr(base, key) for key in owner._APPLICATION_IDENTITY_FIELDS},
            "transport_id": transport_id, "enabled": True, "application_allowed": True,
            "qualification": owner.PROFILE_QUALIFIED_CANARY,
            "qualification_ref": "fixture:" + record, "qualified_until": time.time() + 3600,
            "route_scope": scope}
        state.manifest["capabilities"].append({"capability_id": base.capability_id,
            "secret_ref": base.secret_ref, "kill_state": "active", "allowed_lanes": lanes})
        grants.extend({**row, "grant_id": record + "-" + row["grant_id"],
            "principal_id": record, "credential_ref": base.secret_ref,
            "admission_root": "service:" + record, "workloads": [profile]} for row in templates)
        bindings.append(native.go.ApplicationServiceBinding(record, "vps", profile,
            base.secret_ref, credential,
            selection_purpose=native.go.ApplicationSelectionPurpose(native.purposes["go"]),
            route_scope=native.go.ApplicationRouteScope(scope)))
        state.factories[record] = lambda profile=profile, lane=lanes[0]: owner.make_application_fabric_factory(
            mode_id="shared_fabric", lane=lane, root=state.root,
            workload_cfg={"provider_order": ["fabric"], "workload_profile": profile})
    native.server.shutdown()
    native.server.server_close()
    native.document["application_grants"] = grants
    native.save()
    native.service = bindings[0]
    native.services = tuple(bindings)
    native.server = native.go.make_server(native.router, lease_gateway=native.gateway,
        application_services=native.services, application_http_binding=native.http_binding,
        application_native_bindings=(native.native_binding,), worker_capabilities_enabled=False)
    native.server.handle_error = lambda *args: None
    native._serve(native.server)
    for record, row in state.records.items():
        transport_id = row["transport_id"]
        base = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
        selected = replace(base, base_url=f"http://127.0.0.1:{native.server.server_port}/v1")
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, transport_id, selected)
        row.update({key: getattr(selected, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
    state.bindings, state.grants = tuple(bindings), tuple(grants)
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    return state


@pytest.mark.parametrize("record,profile,transport_id,lanes", AUTHORITIES)
def test_generic_auto_profile_reaches_distinct_native_authority(auto_workloads, record, profile, transport_id, lanes):
    state = auto_workloads
    factory = state.factories[record]()
    assert factory.service_mode_id is None and factory._effective_record_id() == record
    assert factory.workload_decision().receipt()["profiles"] == [profile]
    _, provider = state.bind(record, "profile-" + profile)
    def call(client, model):
        result = client.messages.create(model=model, max_tokens=128, system="Synthetic system",
            messages=[{"role": "user", "content": "Synthetic request"}])
        return result.content[0].text, None, result
    try:
        assert auth.make_call([provider], call, context=lanes[0])[0]
    finally:
        auth.close_fabric_provider(provider)
    turn = state.native.rows("application_turns")[0]
    assert turn["principal_id"] == record
    assert turn["workload"] == profile
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 1
    assert all(row["state"] == "released" for row in state.native.rows("leases"))
    assert state.costs[0]["model"] == MODEL and state.costs[0]["provider"] == "go"


@pytest.mark.parametrize("startup,caller", [("site_interactive", "site_batch"),
    ("site_batch", "site_interactive"), ("lobe_analysis", "portfolio_analysis")])
def test_auto_authority_cannot_absorb_another_explicit_caller_profile(auto_workloads, startup, caller, monkeypatch):
    state = auto_workloads
    record = next((record for record, profile, _, _ in AUTHORITIES if profile == startup), "shared_fabric")
    factory = state.factories[record]()
    credential = Mock(side_effect=AssertionError("credential crossed"))
    monkeypatch.setattr(owner, "_resolve_credential", credential)
    with pytest.raises(owner.ApplicationFabricBindingError, match="workload_authority_mismatch"):
        factory.inspect({"provider_order": ["fabric"], "workload_profile": caller})
    assert not credential.called and not state.native.posts


@pytest.mark.parametrize("record,profile,transport_id,lanes", AUTHORITIES)
def test_missing_generic_authority_never_borrows_admin(auto_workloads, record, profile, transport_id, lanes):
    state = auto_workloads
    del state.records[record]
    state.save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="binding_missing"):
        state.factories[record]().inspect()
    assert not state.native.posts and not state.events


def test_generic_authority_keeps_actual_caller_capability_lane(auto_workloads):
    state = auto_workloads
    factory = owner.make_application_fabric_factory(mode_id="shared_fabric", lane="ungranted-lane",
        root=state.root, workload_cfg={"provider_order": ["fabric"], "workload_profile": "site_batch"})
    with pytest.raises(owner.ApplicationFabricBindingError, match="capability_denied"):
        factory.inspect()
    assert not state.native.posts and not state.events
