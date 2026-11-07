"""Hermes source support keeps the incumbent runtime authorization boundary.

All configuration/capabilities/credentials are disposable fixtures. Positive
cases use the published candidate's descriptors without replacing source flags.
No network, provider request, native grant or installed configuration is used.
"""
from __future__ import annotations

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
CASES = (
    ("hermes_attended_fabric", "hermes-attended", "hermes_attended", "native_go_hermes_attended_v1"),
    ("hermes_attended_fabric", "hermes-attended", "hermes_attended", "native_fabric_hermes_attended_auto_v1"),
    ("hermes_secretary_fabric", "hermes-secretary", "site_interactive", "native_go_hermes_secretary_v1"),
    ("hermes_meta_fabric", "hermes-meta-ceo", "site_interactive", "native_go_hermes_meta_v1"),
    ("hermes_secretary_fabric", "hermes-secretary", "site_interactive", "native_fabric_hermes_secretary_auto_v1"),
    ("hermes_meta_fabric", "hermes-meta-ceo", "site_interactive", "native_fabric_hermes_meta_auto_v1"),
)
CASE_IDS = [case[3] for case in CASES]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        pytest.fail("source support qualification attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def configured(identity, case):
    _, _, _, install, _, make, _, monkeypatch = identity
    service, lane, workload, transport_id = case
    transport = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
    # Deliberately do not call identity.qualify or replace this descriptor.
    row = {name: getattr(transport, name) for name in owner._APPLICATION_IDENTITY_FIELDS}
    row.update(transport_id=transport_id, enabled=True, application_allowed=True,
        qualification=owner.PROFILE_QUALIFIED_CANARY,
        qualification_ref="fixture:hermes-source-support", qualified_until=time.time() + 3600)
    if transport.automatic:
        row["route_scope"] = {"schema": "mastermind.application_route_scope.v1", "pools": ["go"]}
    capabilities = [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active", "allowed_lanes": [lane]}]
    install({service: row}, capabilities)
    monkeypatch.setenv(transport.secret_ref, "synthetic-source-support-credential")
    factory = make(lane=lane, profile=workload, service_mode_id=service)
    return transport, row, capabilities, factory


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
@pytest.mark.parametrize("prior", [False, True])
def test_source_supported_factory_binds_without_flag_overrides(identity, case, prior):
    _, _, events, _, _, _, _, _ = identity
    transport, _, _, factory = configured(identity, case)
    assert transport.qualified and transport.application_allowed
    assert not transport.metadata_read and transport.execution_surface == "inference"
    assert transport.protocol == "native_application_v1"
    original = owner._APPLICATION_FABRIC_TRANSPORTS[case[3]]
    assert original is transport
    inspected = factory.inspect()
    assert events == []
    operation = "hermes:original-source-support:" + case[3]
    bound, workload = factory.with_inspection(inspected)._bind_with_workload(
        operation_id=operation, prior_admission_possible=prior)
    assert owner._APPLICATION_FABRIC_TRANSPORTS[case[3]] is original
    assert bound["client"].operation_id == operation
    assert bound["client"]._native is True
    assert bound["client"]._prior_admission_possible is prior
    assert bound["client"]._admission_possible is prior
    assert bound["client"].model == transport.model
    assert workload.profiles == (case[2],)
    assert workload.receipt()["execution_surface"] == "inference"
    assert events == [("credential", transport.secret_ref), "client"]
    if transport.automatic:
        assert inspected["requested_model"] is None
        assert inspected["route_scope"]["pools"] == ["go"]
    else:
        assert bound["provider"] == "go" and bound["cost_basis"] == "unknown"
    events.clear()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.prepare_admin_pool_reader()
    assert events == []


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
@pytest.mark.parametrize("action", ["inspect", "bind"])
def test_shipped_empty_configuration_refuses_before_credentials(identity, case, action):
    _, _, events, install, _, make, _, monkeypatch = identity
    assert json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())["application_fabric_modes"] == {}
    service, lane, workload, transport_id = case
    transport = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
    assert capability_broker.resolve(transport.capability_id, lane, root=ROOT)["allowed"] is False
    install({}, [])
    monkeypatch.setenv(transport.secret_ref, "synthetic-unenrolled-credential")
    factory = make(lane=lane, profile=workload, service_mode_id=service)
    with pytest.raises(owner.ApplicationFabricBindingError, match="fabric_application_binding_missing"):
        factory.inspect() if action == "inspect" else factory._bind_with_workload(
            operation_id="hermes:unenrolled-original-admission")
    assert events == []


def revoke(row, capabilities, change):
    if change == "disabled":
        row["enabled"] = False
    elif change == "not_permitted":
        row["application_allowed"] = False
    elif change == "unqualified":
        row["qualification"] = "UNQUALIFIED_PENDING_CANARY"
    elif change == "no_qualification_ref":
        row["qualification_ref"] = None
    elif change == "expired":
        row["qualified_until"] = time.time() - 1
    elif change == "capability_held":
        capabilities[0]["kill_state"] = "held"
    elif change == "wrong_lane":
        capabilities[0]["allowed_lanes"] = ["unrelated-lane"]
    elif change == "wrong_credential_ref":
        capabilities[0]["secret_ref"] = "UNRELATED_INTERNAL_REFERENCE"
    else:
        raise AssertionError(change)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
@pytest.mark.parametrize("change", ["disabled", "not_permitted", "unqualified", "no_qualification_ref",
    "expired", "capability_held", "wrong_lane", "wrong_credential_ref"])
def test_runtime_authority_still_precedes_credential_and_client(identity, case, change):
    _, _, events, install, _, _, _, _ = identity
    _, row, capabilities, factory = configured(identity, case)
    revoke(row, capabilities, change)
    install({case[0]: row}, capabilities)
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory._bind_with_workload(operation_id="hermes:refused-source-support")
    assert events == []


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
@pytest.mark.parametrize("change", ["disabled", "expired", "capability_held", "wrong_lane"])
def test_frozen_inspection_rechecks_current_runtime_authority(identity, case, change):
    _, _, events, install, _, _, _, _ = identity
    _, row, capabilities, factory = configured(identity, case)
    frozen = factory.with_inspection(factory.inspect())
    assert events == []
    revoke(row, capabilities, change)
    install({case[0]: row}, capabilities)
    with pytest.raises(owner.ApplicationFabricBindingError):
        frozen._bind_with_workload(operation_id="hermes:revoked-original-admission")
    assert events == []


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
@pytest.mark.parametrize("flag,code", [
    ("qualified", "fabric_application_unqualified"),
    ("application_allowed", "fabric_application_not_permitted"),
])
def test_source_revocation_remains_effective(identity, case, flag, code):
    _, _, events, _, _, _, _, monkeypatch = identity
    transport, _, _, factory = configured(identity, case)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, case[3],
                        replace(transport, **{flag: False}))
    with pytest.raises(owner.ApplicationFabricBindingError, match=code):
        factory._bind_with_workload(operation_id="hermes:source-revoked")
    assert events == []


@pytest.mark.parametrize("case", [case for case in CASES if "_auto_" in case[3]],
                         ids=[case[3] for case in CASES if "_auto_" in case[3]])
def test_exact_selection_preserves_the_original_role_scope(identity, case):
    _, _, events, _, _, _, _, _ = identity
    _, _, _, original = configured(identity, case)
    exact = original.with_requested_model("fixture-host-selected-model")
    inspection = exact.inspect()
    assert original._requested_model is None
    assert inspection["requested_model"] == "fixture-host-selected-model"
    assert inspection["route_scope"]["pools"] == ["go"]
    assert events == []
    bound, _ = exact.with_inspection(inspection)._bind_with_workload(
        operation_id="hermes:strict-original-admission", prior_admission_possible=True)
    assert bound["client"].model == "fixture-host-selected-model"
    assert bound["client"]._prior_admission_possible is True


def test_attended_auto_retains_the_original_purpose_and_closed_defaults():
    relation = owner._SERVICE_FABRIC_RELATIONS["hermes_attended_fabric"]
    assert relation.automatic_transport_id == "native_fabric_hermes_attended_auto_v1"
    assert relation.lane == "hermes-attended"
    assert relation.workload == "hermes_attended"
    assert owner._ApplicationFabricTransport.__dataclass_fields__["qualified"].default is False
    assert owner._ApplicationFabricTransport.__dataclass_fields__["application_allowed"].default is False
