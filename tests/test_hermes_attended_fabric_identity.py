"""Source-supported attended inference still requires the incumbent enrollment."""
from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import socket
import time

import pytest

from engine import provider_production_modes as owner
from engine.neuralweb import capability_broker
from tests.test_fabric_service_identity import identity

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "hermes_attended_fabric"
TRANSPORT = "native_go_hermes_attended_v1"
AUTO_TRANSPORT = "native_fabric_hermes_attended_auto_v1"
LANE = "hermes-attended"
WORKLOAD = "hermes_attended"

# A disabled row is exercised only in the existing disposable owner fixture.
# The shipped owner deliberately has no enrolled application record.
ATTENDED_HELD_MODE = {
    "transport_id": TRANSPORT,
    "base_url": "http://127.0.0.1:50142/v1",
    "secret_ref": "HERMES_ATTENDED_FABRIC_APPLICATION_TOKEN",
    "provider_id": "go",
    "model": "glm-5.3-flash",
    "cost_basis": "unknown",
    "cap_id": "fabric:go_hermes_attended",
    "capability_id": "fabric_application_go_hermes_attended",
    "enabled": False,
    "application_allowed": False,
    "qualification": "UNQUALIFIED_PENDING_CANARY",
    "qualification_ref": None,
    "qualified_until": None,
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        pytest.fail("service identity qualification must not open a network connection")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def qualified_attended(identity, transport_id=TRANSPORT):
    _, _, _, install, qualify, make, _, _ = identity
    transport, row = qualify(transport_id,
        route_scope={"schema": "mastermind.application_route_scope.v1", "pools": ["go"]})
    capabilities = [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active", "allowed_lanes": [LANE]}]
    install({SERVICE: row}, capabilities)
    factory = make(lane=LANE, profile=WORKLOAD, service_mode_id=SERVICE)
    return factory, row, capabilities


def test_shipped_declaration_is_strict_inference_and_has_no_enrollment():
    document = json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())
    assert document["application_fabric_modes"] == {}
    transport = owner._APPLICATION_FABRIC_TRANSPORTS[TRANSPORT]
    relation = owner._SERVICE_FABRIC_RELATIONS[SERVICE]
    assert (relation.lane, relation.workload, relation.transport_id,
            relation.automatic_transport_id) == (LANE, WORKLOAD, TRANSPORT, AUTO_TRANSPORT)
    assert transport.qualified is True and transport.application_allowed is True
    assert transport.metadata_read is False and transport.automatic is False
    assert transport.protocol == "native_application_v1"
    assert transport.execution_surface == "inference"
    for field in owner._APPLICATION_IDENTITY_FIELDS:
        assert getattr(transport, field) == ATTENDED_HELD_MODE[field]
    policy = json.loads((ROOT / "config/provider_workloads.v1.json").read_text())
    assert policy["profiles"][WORKLOAD] == {
        "execution_surface": "inference", "allowed_providers": ["fabric"]}
    assert capability_broker.resolve(transport.capability_id, LANE, root=ROOT)["allowed"] is False


@pytest.mark.parametrize("action", ["inspect", "bind"])
@pytest.mark.parametrize("configured", [False, True])
def test_unenrolled_or_disabled_attended_mode_refuses_before_credentials(identity, action, configured):
    _, _, events, install, _, make, _, _ = identity
    install({SERVICE: copy.deepcopy(ATTENDED_HELD_MODE)} if configured else {}, [])
    factory = make(lane=LANE, profile=WORKLOAD, service_mode_id=SERVICE)
    reason = "fabric_application_disabled" if configured else "fabric_application_binding_missing"
    with pytest.raises(owner.ApplicationFabricBindingError, match=reason):
        factory.inspect() if action == "inspect" else factory._bind_with_workload(
            operation_id="hermes:held-original-admission")
    assert events == []


@pytest.mark.parametrize("source_flag,error", [
    ("qualified", "fabric_application_unqualified"),
    ("application_allowed", "fabric_application_not_permitted"),
])
@pytest.mark.parametrize("transport_id", [TRANSPORT, AUTO_TRANSPORT])
def test_configuration_cannot_grant_source_qualification(identity, source_flag, error, transport_id):
    _, _, events, _, _, _, _, monkeypatch = identity
    factory, _, _ = qualified_attended(identity, transport_id)
    transport = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, transport_id,
                        replace(transport, **{source_flag: False}))
    with pytest.raises(owner.ApplicationFabricBindingError, match=error):
        factory._bind_with_workload(operation_id="hermes:unqualified-original-admission")
    assert events == []


@pytest.mark.parametrize("lane,profile,order", [
    ("hermes-secretary", WORKLOAD, ["fabric"]),
    ("hermes-meta-ceo", WORKLOAD, ["fabric"]),
    ("brain", WORKLOAD, ["fabric"]),
    ("admin-orchestrator", WORKLOAD, ["fabric"]),
    (LANE, "site_interactive", ["fabric"]),
    (LANE, "development_agent", ["fabric"]),
    (LANE, WORKLOAD, ["fabric", "anthropic"]),
    (LANE, WORKLOAD, ["fabric", "fabric"]),
])
def test_attended_cannot_borrow_role_workload_or_provider_order(identity, lane, profile, order):
    root, _, events, _, _, _, _, _ = identity
    with pytest.raises(owner.ApplicationFabricBindingError):
        owner.make_application_fabric_factory(mode_id="shared_fabric", lane=lane, root=root,
            service_mode_id=SERVICE, workload_cfg={"workload_profile": profile, "provider_order": order})
    assert events == []


@pytest.mark.parametrize("field,value", [
    ("base_url", "http://127.0.0.2:50142/v1"),
    ("secret_ref", "HERMES_SECRETARY_FABRIC_APPLICATION_TOKEN"),
    ("provider_id", "glm"),
    ("model", "deepseek-v4.1-flash"),
    ("cap_id", "fabric:go_hermes_secretary"),
    ("capability_id", "fabric_application_go_hermes_secretary"),
    ("transport_id", "native_go_hermes_secretary_v1"),
    ("route_scope", {"schema": "mastermind.application_route_scope.v1", "pools": ["go"]}),
])
def test_attended_identity_and_route_variant_are_closed(identity, field, value):
    _, _, events, install, _, _, _, _ = identity
    factory, row, capabilities = qualified_attended(identity)
    row[field] = value
    install({SERVICE: row}, capabilities)
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory._bind_with_workload(operation_id="hermes:changed-original-admission")
    assert events == []


@pytest.mark.parametrize("prior", [False, True])
def test_real_factory_preserves_original_operation_and_uncertainty(identity, prior):
    _, _, events, _, _, _, _, _ = identity
    factory, _, _ = qualified_attended(identity)
    inspection = factory.inspect()
    assert events == []
    operation = "hermes:original-attended-admission"
    bound, workload = factory.with_inspection(inspection)._bind_with_workload(
        operation_id=operation, prior_admission_possible=prior)
    assert bound["client"].operation_id == operation
    assert bound["client"]._native is True
    assert bound["client"]._prior_admission_possible is prior
    assert bound["client"]._admission_possible is prior
    assert bound["client"].model == bound["model"] == "glm-5.3-flash"
    assert bound["provider"] == "go" and bound["cost_basis"] == "unknown"
    assert bound["cap_id"] == "fabric:go_hermes_attended"
    assert workload.receipt()["execution_surface"] == "inference"
    assert workload.profiles == (WORKLOAD,)
    assert events == [("credential", "HERMES_ATTENDED_FABRIC_APPLICATION_TOKEN"), "client"]


@pytest.mark.parametrize("change", ["disabled", "expired", "capability_held", "capability_wrong_lane"])
def test_inspection_does_not_survive_lost_eligibility(identity, change):
    _, _, events, install, _, _, _, _ = identity
    factory, row, capabilities = qualified_attended(identity)
    frozen = factory.with_inspection(factory.inspect())
    if change == "disabled":
        row["enabled"] = False
    elif change == "expired":
        row["qualified_until"] = time.time() - 1
    elif change == "capability_held":
        capabilities[0]["kill_state"] = "held"
    else:
        capabilities[0]["allowed_lanes"] = ["hermes-secretary"]
    install({SERVICE: row}, capabilities)
    with pytest.raises(owner.ApplicationFabricBindingError):
        frozen._bind_with_workload(operation_id="hermes:revoked-original-admission")
    assert events == []


def test_attended_has_no_administrative_pool_view(identity):
    _, _, events, _, _, _, _, _ = identity
    factory, _, _ = qualified_attended(identity)
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.prepare_admin_pool_reader()
    assert events == []


def test_attended_variants_share_only_the_original_service_identity():
    attended = owner._APPLICATION_FABRIC_TRANSPORTS[TRANSPORT]
    automatic = owner._APPLICATION_FABRIC_TRANSPORTS[AUTO_TRANSPORT]
    others = [row for name, row in owner._APPLICATION_FABRIC_TRANSPORTS.items()
              if name not in {TRANSPORT, AUTO_TRANSPORT}]
    for field in ("secret_ref", "cap_id", "capability_id"):
        assert getattr(attended, field) == getattr(automatic, field)
        assert getattr(attended, field) not in {getattr(row, field) for row in others}
    assert automatic.base_url == attended.base_url
    assert automatic.model is None and automatic.provider_id is None
    assert automatic.automatic is True
    assert automatic.qualified is True and automatic.application_allowed is True
    assert automatic.metadata_read is False and automatic.execution_surface == "inference"
    assert automatic.protocol == "native_application_v1"


@pytest.mark.parametrize("model", [None, "glm-5.3-flash"])
def test_attended_auto_and_exact_use_the_original_factory_scope(identity, model):
    _, _, events, _, _, _, _, _ = identity
    factory, _, _ = qualified_attended(identity, AUTO_TRANSPORT)
    preliminary = factory.inspect()
    assert preliminary["schema"] == "mastermind.fabric_application_inspection.v2"
    assert preliminary["requested_model"] is None and events == []
    if model is not None:
        factory = factory.with_requested_model(model)
    inspected = factory.inspect()
    assert inspected["schema"] == ("mastermind.fabric_application_inspection.v3"
                                   if model else "mastermind.fabric_application_inspection.v2")
    assert inspected["requested_model"] == model
    assert inspected["route_scope"] == {
        "schema": "mastermind.application_route_scope.v1", "pools": ["go"]}
    operation = "hermes:original-attended-auto-admission"
    bound, workload = factory.with_inspection(inspected)._bind_with_workload(operation_id=operation)
    assert bound["inspection"] == inspected
    assert bound["client"].operation_id == operation
    assert bound["client"].model == model and bound["client"].auto_inspection == inspected
    assert workload.profiles == (WORKLOAD,)
    assert events == [("credential", "HERMES_ATTENDED_FABRIC_APPLICATION_TOKEN"), "client"]


@pytest.mark.parametrize("change", ["scope", "variant", "foreign_service"])
def test_attended_auto_frozen_identity_cannot_change_before_bind(identity, change):
    _, _, events, install, qualify, _, _, _ = identity
    factory, row, capabilities = qualified_attended(identity, AUTO_TRANSPORT)
    frozen = factory.with_inspection(factory.inspect())
    if change == "scope":
        row["route_scope"]["pools"] = ["bailian"]
    elif change == "variant":
        _, row = qualify(TRANSPORT)
    else:
        _, row = qualify("native_fabric_hermes_secretary_auto_v1")
    install({SERVICE: row}, capabilities)
    with pytest.raises(owner.ApplicationFabricBindingError):
        frozen._bind_with_workload(operation_id="hermes:changed-auto-admission")
    assert events == []
