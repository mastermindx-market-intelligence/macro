"""Hermes joins the incumbent APPLICATION owner without borrowing another role."""
from __future__ import annotations

import time
import pytest

from engine import provider_production_modes as owner
from test_fabric_service_identity import identity


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
    assert not transport.qualified and not transport.application_allowed and not transport.metadata_read
    assert transport.protocol == "native_application_v1" and transport.secret_ref == secret_ref
    expected_host = "127.0.0.2" if service_id == "hermes_secretary_fabric" else "127.0.0.3"
    assert transport.base_url == f"http://{expected_host}:50142/v1"
    assert owner._SERVICE_FABRIC_RELATIONS[service_id].lane == lane
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
                  if key not in {row[1] for row in ROLES.values()}]
    for field in ("secret_ref", "cap_id", "capability_id"):
        values = {getattr(t, field) for t in transports}
        assert len(values) == len(ROLES)
        assert values.isdisjoint({getattr(t, field) for t in incumbents})
