"""Hermes joins the incumbent APPLICATION owner without borrowing another role."""
from __future__ import annotations

import time
from dataclasses import replace
import pytest

from engine import provider_production_modes as owner
from tests.test_fabric_service_identity import identity


ROLES = {
    "hermes_secretary_fabric": ("hermes-secretary", "native_go_hermes_secretary_v1",
                                "HERMES_SECRETARY_FABRIC_APPLICATION_TOKEN"),
    "hermes_meta_fabric": ("hermes-meta-ceo", "native_go_hermes_meta_v1",
                           "HERMES_META_FABRIC_APPLICATION_TOKEN"),
}


@pytest.mark.parametrize("service_id", ROLES)
def test_unqualified_role_refuses_even_with_config_and_secret(identity, service_id):
    _, _, events, install, _, make, _, monkeypatch = identity
    lane, transport_id, secret_ref = ROLES[service_id]
    transport = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
    assert transport.qualified and transport.application_allowed and not transport.metadata_read
    assert transport.protocol == "native_application_v1" and transport.secret_ref == secret_ref
    expected_host = "127.0.0.2" if service_id == "hermes_secretary_fabric" else "127.0.0.3"
    assert transport.base_url == f"http://{expected_host}:50142/v1"
    assert owner._SERVICE_FABRIC_RELATIONS[service_id].lane == lane
    # A legitimate source revocation still beats otherwise eligible runtime data.
    transport = replace(transport, qualified=False, application_allowed=False)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, transport_id, transport)
    row = {k: getattr(transport, k) for k in owner._APPLICATION_IDENTITY_FIELDS}
    row.update(transport_id=transport_id, enabled=True, application_allowed=True,
               qualification=owner.PROFILE_QUALIFIED_CANARY,
               qualification_ref="fixture:configuration-cannot-enroll", qualified_until=time.time() + 3600)
    install({service_id: row}, [{"capability_id": transport.capability_id,
        "secret_ref": secret_ref, "kill_state": "active", "allowed_lanes": [lane]}])
    monkeypatch.setenv(secret_ref, "synthetic-unqualified-role-token")
    with pytest.raises(owner.ApplicationFabricBindingError, match="fabric_application_unqualified"):
        make(lane=lane, service_mode_id=service_id).inspect()
    assert events == []


@pytest.mark.parametrize("service_id", ROLES)
def test_qualified_original_factory_retains_role_operation_and_no_admin_view(identity, service_id):
    _, _, events, install, qualify, make, _, _ = identity
    lane, transport_id, secret_ref = ROLES[service_id]
    transport, row = qualify(transport_id)
    install({service_id: row}, [{"capability_id": transport.capability_id,
        "secret_ref": secret_ref, "kill_state": "active", "allowed_lanes": [lane]}])
    factory = make(lane=lane, service_mode_id=service_id)
    inspected = factory.inspect()
    assert events == []
    operation = "hermes:fixture-original-admission"
    bound, workload = factory.with_inspection(inspected)._bind_with_workload(
        operation_id=operation, prior_admission_possible=False)
    assert bound["client"].operation_id == operation
    assert bound["client"]._native is True
    assert bound["model"] == transport.model
    assert bound["cap_id"] == transport.cap_id
    assert events == [("credential", secret_ref), "client"]


@pytest.mark.parametrize("service_id", ROLES)
@pytest.mark.parametrize("borrowed_lane", ["brain", "ask-brain", "mastermind-chat", "admin-orchestrator"])
def test_hermes_relation_cannot_borrow_another_consumer_lane(identity, service_id, borrowed_lane):
    _, _, events, _, _, make, _, _ = identity
    with pytest.raises(owner.ApplicationFabricBindingError):
        make(lane=borrowed_lane, service_mode_id=service_id).inspect()
    assert events == []


def test_roles_never_share_capability_credential_or_attribution():
    transports = [owner._APPLICATION_FABRIC_TRANSPORTS[row[1]] for row in ROLES.values()]
    incumbents = [value for key, value in owner._APPLICATION_FABRIC_TRANSPORTS.items()
                  if key not in {row[1] for row in ROLES.values()}
                  and key not in {owner._SERVICE_FABRIC_RELATIONS[s].automatic_transport_id for s in ROLES}]
    for field in ("secret_ref", "cap_id", "capability_id"):
        values = {getattr(t, field) for t in transports}
        assert len(values) == len(ROLES)
        assert values.isdisjoint({getattr(t, field) for t in incumbents})


@pytest.mark.parametrize("service_id", ROLES)
@pytest.mark.parametrize("pools", [["go"], ["bailian", "go"]])
def test_auto_role_retains_original_identity_and_null_model(identity, service_id, pools):
    _, _, events, install, qualify, make, _, _ = identity
    lane, fixed_id, secret_ref = ROLES[service_id]
    relation = owner._SERVICE_FABRIC_RELATIONS[service_id]
    fixed = owner._APPLICATION_FABRIC_TRANSPORTS[fixed_id]
    automatic = owner._APPLICATION_FABRIC_TRANSPORTS[relation.automatic_transport_id]
    assert automatic.qualified and automatic.application_allowed and not automatic.metadata_read
    for name in ("base_url", "secret_ref", "cap_id", "capability_id"):
        assert getattr(automatic, name) == getattr(fixed, name)
    scope = {"schema": "mastermind.application_route_scope.v1", "pools": pools}
    transport, row = qualify(relation.automatic_transport_id, route_scope=scope)
    install({service_id: row}, [{"capability_id": transport.capability_id,
        "secret_ref": secret_ref, "kill_state": "active", "allowed_lanes": [lane]}])
    factory = make(lane=lane, service_mode_id=service_id)
    inspected = factory.inspect()
    assert events == [] and inspected["requested_model"] is None and inspected["route_scope"] == scope
    bound, _ = factory.with_inspection(inspected)._bind_with_workload(
        operation_id="hermes:original-auto-admission", prior_admission_possible=False)
    assert set(bound) == {"schema", "client", "inspection"}
    assert bound["client"].model is None and bound["client"].auto_inspection == inspected
    assert bound["client"].operation_id == "hermes:original-auto-admission"
    assert events == [("credential", secret_ref), "client"]


@pytest.mark.parametrize("service_id", ROLES)
@pytest.mark.parametrize("pools", [["go"], ["bailian", "go"]])
def test_exact_role_narrows_original_scope_without_new_identity(identity, service_id, pools):
    _, _, events, install, qualify, make, _, _ = identity
    lane, _, secret_ref = ROLES[service_id]
    relation = owner._SERVICE_FABRIC_RELATIONS[service_id]
    scope = {"schema": "mastermind.application_route_scope.v1", "pools": pools}
    transport, row = qualify(relation.automatic_transport_id, route_scope=scope)
    install({service_id: row}, [{"capability_id": transport.capability_id,
        "secret_ref": secret_ref, "kill_state": "active", "allowed_lanes": [lane]}])
    original = make(lane=lane, service_mode_id=service_id)
    exact = original.with_requested_model("fixture-model")
    inspected = exact.inspect()
    assert inspected["schema"] == "mastermind.fabric_application_inspection.v3"
    assert inspected["requested_model"] == "fixture-model" and inspected["route_scope"] == scope
    assert original._requested_model is None and events == []
    frozen = exact.with_inspection(inspected).with_requested_model("fixture-model")
    bound, _ = frozen._bind_with_workload(operation_id="hermes:original-exact", prior_admission_possible=False)
    assert bound["schema"] == "mastermind.fabric_application_binding.v3"
    assert bound["client"].model == "fixture-model" and bound["inspection"] == inspected
    assert bound["client"].operation_id == "hermes:original-exact"
    assert events == [("credential", secret_ref), "client"]


@pytest.mark.parametrize("service_id", ROLES)
def test_exact_role_cannot_reinterpret_a_frozen_auto_commitment(identity, service_id):
    _, _, events, install, qualify, make, _, _ = identity
    lane, _, secret_ref = ROLES[service_id]
    relation = owner._SERVICE_FABRIC_RELATIONS[service_id]
    transport, row = qualify(relation.automatic_transport_id,
        route_scope={"schema": "mastermind.application_route_scope.v1", "pools": ["go"]})
    install({service_id: row}, [{"capability_id": transport.capability_id,
        "secret_ref": secret_ref, "kill_state": "active", "allowed_lanes": [lane]}])
    original = make(lane=lane, service_mode_id=service_id)
    auto = original.with_inspection(original.inspect())
    with pytest.raises(owner.ApplicationFabricBindingError, match="fabric_application_identity_changed"):
        auto.with_requested_model("fixture-model")
    exact = original.with_requested_model("fixture-model")
    with pytest.raises(owner.ApplicationFabricBindingError, match="fabric_application_identity_changed"):
        exact.with_inspection(exact.inspect()).with_requested_model("other-model")
    assert events == []
