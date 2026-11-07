"""Shared service identity owner relation: units without live credentials spend."""
from __future__ import annotations

import json
import os
import time
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from engine import fabric_inference_client as client_module
from engine import provider_production_modes as owner

ROOT = Path(__file__).resolve().parents[1]
RELATIONS = owner._SERVICE_FABRIC_RELATIONS
HOST = "shared_fabric"
AUTO_SCOPE = {"schema": "mastermind.application_route_scope.v1", "pools": ["bailian", "go"]}


def fixture_lane(relation):
    return relation.lane or "identity-unit"


@pytest.fixture
def identity(tmp_path, monkeypatch):
    cfgdir = tmp_path / "config"
    cfgdir.mkdir()
    (cfgdir / "provider_workloads.v1.json").write_text(
        (ROOT / "config/provider_workloads.v1.json").read_text())
    document = json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())
    assert document.get("application_fabric_modes") == {}
    events = []
    original_secret = owner._resolve_credential
    original_client = client_module.FabricInferenceClient

    def secret(mode, env):
        events.append(("credential", getattr(mode, "secret_ref", None)))
        return original_secret(mode, env)

    def client(**kwargs):
        events.append("client")
        return original_client(**kwargs)

    monkeypatch.setattr(owner, "_resolve_credential", secret)
    monkeypatch.setattr(client_module, "FabricInferenceClient", client)
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    for module, name in [(owner.provider_health, "record_attempt"), (owner.ai_costs, "record_usage")]:
        monkeypatch.setattr(module, name, lambda **kw: pytest.fail("usage/health effect"))

    def install(records, capabilities):
        document["application_fabric_modes"] = records
        (cfgdir / "provider_production_modes.v1.json").write_text(json.dumps(document))
        (cfgdir / "capability_manifest.yml").write_text(yaml.safe_dump({"capabilities": capabilities}))

    def qualify(transport_id, *, route_scope=None, **fields):
        base = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
        transport = replace(base, qualified=True, application_allowed=True, **fields)
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, transport_id, transport)
        monkeypatch.setenv(transport.secret_ref, "synthetic-token-for-offline-test-" + transport.secret_ref)
        row = {k: getattr(transport, k) for k in owner._APPLICATION_IDENTITY_FIELDS}
        row.update(transport_id=transport_id, enabled=True, application_allowed=True,
                   qualification=owner.PROFILE_QUALIFIED_CANARY,
                   qualification_ref="fixture:service-identity", qualified_until=time.time() + 3600)
        if transport.automatic:
            row["route_scope"], _ = client_module.validate_auto_route_scope(
                AUTO_SCOPE if route_scope is None else route_scope)
        return transport, row

    def make(*, lane="admin-orchestrator", profile="site_interactive", service_mode_id=None, mode_id=HOST):
        return owner.make_application_fabric_factory(
            mode_id=mode_id, lane=lane, root=tmp_path,
            workload_cfg={"workload_profile": profile, "provider_order": ["fabric"]},
            service_mode_id=service_mode_id)

    def admin_fixture():
        transport = owner._ApplicationFabricTransport(
            "http://127.0.0.1:8311/v1", "TEST_ADMIN_TOKEN", "fixture", "fixture-model",
            "unknown", "fabric:fixture", "fixture_admin_cap", qualified=True, application_allowed=True)
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", transport)
        monkeypatch.setenv("TEST_ADMIN_TOKEN", "synthetic-admin-token-for-offline-test")
        row = {k: getattr(transport, k) for k in owner._APPLICATION_IDENTITY_FIELDS}
        row.update(transport_id="fixture_v1", enabled=True, application_allowed=True,
                   qualification=owner.PROFILE_QUALIFIED_CANARY, qualification_ref="fixture:admin",
                   qualified_until=time.time() + 3600)
        return transport, row

    return tmp_path, document, events, install, qualify, make, admin_fixture, monkeypatch


@pytest.mark.parametrize("service_id", sorted(RELATIONS))
def test_each_relation_binds_only_its_lane_workload_and_transport(identity, service_id):
    _, _, events, install, qualify, make, _, _ = identity
    rel = RELATIONS[service_id]
    transport, row = qualify(rel.transport_id or rel.automatic_transport_id)
    install({service_id: row}, [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active",
        "allowed_lanes": [fixture_lane(rel)]}])
    factory = make(lane=fixture_lane(rel), profile=rel.workload, service_mode_id=service_id)
    assert factory.mode_id == HOST and factory.service_mode_id == service_id
    snapshot = factory.inspect()
    assert events == []
    bound, _ = factory.with_inspection(snapshot)._bind_with_workload(
        operation_id="unit-" + service_id)
    if transport.automatic:
        scope, digest = client_module.validate_auto_route_scope(AUTO_SCOPE)
        assert set(bound) == {"schema", "client", "inspection"}
        assert bound["schema"] == client_module.AUTO_BINDING_SCHEMA
        assert client_module.validate_auto_inspection(snapshot) == snapshot
        assert snapshot["requested_model"] is None
        assert snapshot["output_limit_mode"] == "hard_maximum"
        assert snapshot["route_scope"] == scope and snapshot["route_scope_digest"] == digest
        assert snapshot["cap_id"] == transport.cap_id
        assert bound["inspection"] == snapshot
        assert bound["client"].auto_inspection == snapshot
        assert bound["client"].model is None
        assert bound["client"].application_observation is None
    else:
        assert bound["model"] == transport.model and bound["cap_id"] == transport.cap_id
    assert events == [("credential", transport.secret_ref), "client"]
    events.clear()
    with pytest.raises(owner.ApplicationFabricBindingError):
        make(lane=fixture_lane(rel), profile="site_interactive" if rel.workload != "site_interactive" else "site_batch",
             service_mode_id=service_id)
    with pytest.raises(owner.ApplicationFabricBindingError):
        make(lane="admin-orchestrator", profile=rel.workload, service_mode_id=service_id).inspect()
    assert events == []


def test_none_preserves_admin_inspection_and_child_cannot_be_host(identity):
    _, _, events, install, _, make, admin_fixture, monkeypatch = identity
    transport, row = admin_fixture()
    install({HOST: row}, [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active",
        "allowed_lanes": ["admin-orchestrator"]}])
    factory = make()
    assert factory.service_mode_id is None and factory.mode_id == HOST
    identity_snap = factory.inspect()
    assert set(identity_snap) == {"provider", "model", "cap_id", "capability_id",
                                  "cost_basis", "workload_policy", "transport_identity"}
    assert events == []
    narrowed = factory.with_inspection(identity_snap)
    assert narrowed.service_mode_id is None
    bound = narrowed()
    assert bound["provider"] == "fixture" and events == [("credential", "TEST_ADMIN_TOKEN"), "client"]
    with pytest.raises(owner.ApplicationFabricBindingError):
        make(mode_id="mastermind_text_fabric", lane="mastermind-text", profile="site_batch")
    with pytest.raises(owner.ApplicationFabricBindingError):
        owner.ApplicationFabricFactory(
            "mastermind_text_fabric", "mastermind-text", Path("/tmp"), True, "site_batch", ("fabric",),
            service_mode_id=None)


@pytest.mark.parametrize("service_id", sorted(RELATIONS))
def test_missing_invalid_cross_role_and_metadata_refuse_before_secret(identity, service_id):
    tmp_path, _, events, install, qualify, make, _, monkeypatch = identity
    rel = RELATIONS[service_id]
    transport, row = qualify(rel.transport_id or rel.automatic_transport_id)
    # missing record
    install({}, [{"capability_id": transport.capability_id, "secret_ref": transport.secret_ref,
                  "kill_state": "active", "allowed_lanes": [fixture_lane(rel)]}])
    factory = make(lane=fixture_lane(rel), profile=rel.workload, service_mode_id=service_id)
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.inspect()
    assert events == []
    # transport swap with admin transport id
    admin, bad = qualify("native_go_application_v1")
    install({service_id: bad}, [{"capability_id": admin.capability_id, "secret_ref": admin.secret_ref,
                                 "kill_state": "active", "allowed_lanes": [fixture_lane(rel)]}])
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.inspect()
    assert events == []
    # correct record but wrong capability lane
    install({service_id: row}, [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active",
        "allowed_lanes": ["admin-orchestrator"]}])
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory._bind_with_workload(operation_id="unit-denied")
    assert events == []
    # metadata denied on child
    install({service_id: row}, [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active", "allowed_lanes": [fixture_lane(rel)]}])
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.prepare_admin_pool_reader()
    assert events == []
    # host record cannot adopt child transport
    host_row = dict(row)
    install({HOST: host_row}, [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active",
        "allowed_lanes": ["admin-orchestrator"]}])
    admin_factory = make()
    with pytest.raises(owner.ApplicationFabricBindingError):
        admin_factory.inspect()
    assert events == []
    # configured child missing host env stays unselected; invalid child stays selected without factory
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE", raising=False)
    assert owner.configured_application_fabric(
        lane=fixture_lane(rel), workload_profile=rel.workload, root=tmp_path,
        service_mode_id=service_id) == (False, None)
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "not-a-host")
    selected, factory = owner.configured_application_fabric(
        lane=fixture_lane(rel), workload_profile=rel.workload, root=tmp_path,
        service_mode_id=service_id)
    assert selected is True and factory is None


def test_with_inspection_keeps_role_and_cross_service_commitment_refuses(identity):
    _, _, events, install, qualify, make, _, _ = identity
    records, caps = {}, []
    snaps = {}
    for service_id, rel in RELATIONS.items():
        transport, row = qualify(rel.transport_id or rel.automatic_transport_id)
        records[service_id] = row
        caps.append({"capability_id": transport.capability_id, "secret_ref": transport.secret_ref,
                     "kill_state": "active", "allowed_lanes": [fixture_lane(rel)]})
    install(records, caps)
    for service_id, rel in RELATIONS.items():
        factory = make(lane=fixture_lane(rel), profile=rel.workload, service_mode_id=service_id)
        snaps[service_id] = factory.inspect()
    assert len({json.dumps(v, sort_keys=True) for v in snaps.values()}) == len(RELATIONS)
    text = make(lane="mastermind-text", profile="site_batch", service_mode_id="mastermind_text_fabric")
    chat = make(lane="mastermind-chat", profile="site_interactive", service_mode_id="mastermind_chat_fabric")
    narrowed = text.with_inspection(snaps["mastermind_text_fabric"])
    assert narrowed.service_mode_id == "mastermind_text_fabric"
    with pytest.raises(owner.ApplicationFabricBindingError):
        text.with_inspection(snaps["mastermind_chat_fabric"])._bind_with_workload(
            operation_id="unit-cross-text")
    with pytest.raises(owner.ApplicationFabricBindingError):
        chat.with_inspection(snaps["mastermind_text_fabric"])._bind_with_workload(
            operation_id="unit-cross-chat")
    assert events == []
    batch = make(lane="identity-unit", profile="site_batch", service_mode_id="macro_batch_fabric")
    with pytest.raises(owner.ApplicationFabricBindingError):
        batch.with_inspection(snaps["macro_analysis_fabric"])._bind_with_workload(
            operation_id="unit-cross-auto")
    assert events == []
    # empty/unknown/null caller profiles refuse before secret
    for profile in ("", "unknown", None):
        with pytest.raises(Exception):
            text.inspect({"workload_profile": profile})
    assert events == []


def test_configured_wires_literal_service_ids_and_direct_construction_validates(identity):
    tmp_path, _, events, install, qualify, make, _, monkeypatch = identity
    for service_id, rel in RELATIONS.items():
        transport, row = qualify(rel.transport_id or rel.automatic_transport_id)
        install({service_id: row}, [{"capability_id": transport.capability_id,
            "secret_ref": transport.secret_ref, "kill_state": "active", "allowed_lanes": [fixture_lane(rel)]}])
        monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", HOST)
        selected, factory = owner.configured_application_fabric(
            lane=fixture_lane(rel), workload_profile=rel.workload, root=tmp_path,
            service_mode_id=service_id)
        assert selected is True and factory.service_mode_id == service_id and factory.mode_id == HOST
        assert factory.inspect()["capability_id"] == transport.capability_id
    assert events == []
    with pytest.raises(owner.ApplicationFabricBindingError):
        owner.ApplicationFabricFactory(
            HOST, "mastermind-text", tmp_path, True, "site_batch", ("fabric",),
            service_mode_id="macro_brain_fabric")


def test_description_rejects_qualified_child_as_host_without_side_effects(identity):
    tmp_path, _, events, install, qualify, make, _, monkeypatch = identity
    rel = RELATIONS["mastermind_text_fabric"]
    transport, row = qualify(rel.transport_id or rel.automatic_transport_id)
    install({"mastermind_text_fabric": row}, [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active", "allowed_lanes": [fixture_lane(rel)]}])
    # The child itself is genuinely qualified and inspectable in its own relation.
    factory = make(lane=fixture_lane(rel), profile=rel.workload, service_mode_id="mastermind_text_fabric")
    assert factory.inspect()["capability_id"] == transport.capability_id
    for selector in ("mastermind_text_fabric", "macro_brain_fabric", "not-a-host", "", None):
        described = owner.describe_application_fabric_selection(selector, root=tmp_path)
        if selector is None:
            assert described == {"selected": False, "state": "legacy", "provider": None,
                                 "model": None, "blocker": None}
        else:
            assert described == {"selected": True, "state": "held", "provider": None,
                "model": None, "blocker": "fabric_application_selection_invalid"}
    assert os.environ.get("MM_PROVIDER_APPLICATION_MODE") != "mastermind_text_fabric"
    assert events == []


def test_auto_scope_change_refuses_before_credentials(identity):
    _, _, events, install, qualify, make, _, _ = identity
    rel = RELATIONS["macro_batch_fabric"]
    transport, row = qualify(rel.automatic_transport_id)
    caps = [{"capability_id": transport.capability_id, "secret_ref": transport.secret_ref,
             "kill_state": "active", "allowed_lanes": ["identity-unit"]}]
    install({"macro_batch_fabric": row}, caps)
    factory = make(lane="identity-unit", profile="site_batch", service_mode_id="macro_batch_fabric")
    snapshot = factory.inspect()
    narrowed = factory.with_inspection(snapshot)
    changed = dict(row)
    changed["route_scope"], _ = client_module.validate_auto_route_scope(
        {"schema": "mastermind.application_route_scope.v1", "pools": ["go"]})
    install({"macro_batch_fabric": changed}, caps)
    with pytest.raises(owner.ApplicationFabricBindingError):
        narrowed._bind_with_workload(operation_id="unit-changed-scope")
    assert events == []
