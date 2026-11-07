"""Held Go recipe through the real policy, manifest and native client owners.

All qualification and credentials are disposable fixture premises. No source
recipe is enabled, service enrolled, provider called or quota admitted here.
"""
from dataclasses import asdict, replace
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
import yaml

from engine import fabric_inference_client as client
from engine import provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = "native_go_application_v1"
_CLIENT = client.FabricInferenceClient
EXPECTED = {
    "base_url": "http://127.0.0.1:50142/v1",
    "secret_ref": "MACRO_FABRIC_APPLICATION_TOKEN",
    "provider_id": "go", "model": "deepseek-v4.1-flash",
    "cost_basis": "unknown", "cap_id": "fabric:go_application",
    "capability_id": "fabric_application_go",
    "protocol": client.NATIVE_PROTOCOL,
    "qualified": False, "application_allowed": False,
    "native_recipe_digest": None, "metadata_read": True,
    "automatic": False, "execution_surface": "inference",
}


@pytest.fixture
def go(binding, monkeypatch):
    root, row, document, manifest, events, save, make, _ = binding
    transport = owner._APPLICATION_FABRIC_TRANSPORTS[TRANSPORT]
    row.update({key: getattr(transport, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
    row["transport_id"] = TRANSPORT
    manifest["capabilities"] = [{"capability_id": transport.capability_id,
        "secret_ref": transport.secret_ref, "kill_state": "active",
        "allowed_lanes": ["admin-orchestrator"]}]
    monkeypatch.setenv(transport.secret_ref, "synthetic-native-application-token-for-isolated-tests")
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: pytest.fail("network effect"))
    save()
    def qualified_shape(**changes):
        candidate = replace(transport, qualified=True, application_allowed=True, **changes)
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, TRANSPORT, candidate)
        return candidate
    return SimpleNamespace(root=root, row=row, document=document, manifest=manifest,
        events=events, save=save, make=make, transport=transport, qualify=qualified_shape)


def test_closed_recipe_remains_held_without_enrollment_or_experiential_change():
    assert asdict(owner._APPLICATION_FABRIC_TRANSPORTS[TRANSPORT]) == EXPECTED
    assert owner._APPLICATION_MODE_IDS == frozenset({"shared_fabric"})
    experiential = owner._APPLICATION_FABRIC_TRANSPORTS["experiential_proxy_v1"]
    assert asdict(experiential) == {
        "base_url": "http://127.0.0.1:8311/v1", "secret_ref": "FABRIC_PROXY_TOKEN",
        "provider_id": "experiential", "model": "glm-5.3-uncensored", "cost_basis": "unknown",
        "cap_id": "fabric:experiential_proxy", "capability_id": "fabric_application_proxy",
        "qualified": False, "application_allowed": False, "protocol": client.LEGACY_PROTOCOL,
        "native_recipe_digest": None, "metadata_read": False,
        "automatic": False, "execution_surface": "inference",
    }
    assert json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())["application_fabric_modes"] == {}
    manifest = yaml.safe_load((ROOT / "config/capability_manifest.yml").read_text())
    assert all(row.get("capability_id") != "fabric_application_go" for row in manifest["capabilities"])


@pytest.mark.parametrize("qualified,permitted", [(False, False), (False, True), (True, False)])
def test_configuration_cannot_promote_either_source_hold(go, monkeypatch, qualified, permitted):
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, TRANSPORT,
        replace(go.transport, qualified=qualified, application_allowed=permitted))
    factory = go.make()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.inspect()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory._bind_with_workload(operation_id="admin:original-turn")
    assert go.events == []


@pytest.mark.parametrize("key,value", [
    ("base_url", "http://127.0.0.1:8311/v1"), ("secret_ref", "DEEPSEEK_API_KEY"),
    ("provider_id", "deepseek"), ("model", "deepseek-chat"),
    ("cost_basis", "subscription"), ("cap_id", "fabric:other"),
    ("capability_id", "other_capability"), ("protocol", client.LEGACY_PROTOCOL),
])
def test_config_cannot_retarget_a_future_qualified_shape(go, key, value):
    go.qualify()
    go.row[key] = value
    go.save()
    with pytest.raises(owner.ApplicationFabricBindingError):
        go.make()._bind_with_workload(operation_id="admin:original-turn")
    assert go.events == []


@pytest.mark.parametrize("change", ["lane", "reference", "kill", "workload"])
def test_real_capability_and_workload_refusals_precede_credentials(go, change):
    go.qualify()
    cap = go.manifest["capabilities"][0]
    if change == "lane": cap["allowed_lanes"] = ["other-lane"]
    if change == "reference": cap["secret_ref"] = "OTHER_APPLICATION_TOKEN"
    if change == "kill": cap["kill_state"] = "killed"
    go.save()
    cfg = {"provider_order": ["fabric"], "workload_profile": "production"} if change == "workload" else None
    with pytest.raises(ValueError):
        go.make(cfg)._bind_with_workload(operation_id="admin:original-turn")
    assert go.events == []


def test_future_shape_uses_original_id_and_exact_raw_native_binding_without_admission(go):
    go.qualify()
    factory = go.make()
    identity = factory.inspect()
    assert go.events == []
    bound, _ = factory.with_inspection(identity)._bind_with_workload(operation_id="admin:original-turn")
    assert set(bound) == {"client", "model", "provider", "cost_basis", "cap_id"}
    assert {key: value for key, value in bound.items() if key != "client"} == {
        "model": "deepseek-v4.1-flash", "provider": "go", "cost_basis": "unknown",
        "cap_id": "fabric:go_application"}
    actual = bound["client"]
    assert type(actual) is _CLIENT and actual._native is True
    assert actual.operation_id == "admin:original-turn"
    assert go.events == ["credential", "client"]
    actual.close()


@pytest.mark.parametrize("operation_id", [None, "admin/original-turn", " admin:original-turn "])
def test_native_original_id_is_required_before_secret(go, operation_id):
    go.qualify()
    with pytest.raises(client.FabricInferenceError, match="fabric_native_identity_invalid"):
        go.make()._bind_with_workload(operation_id=operation_id)
    assert go.events == []


@pytest.mark.parametrize("change", ["endpoint", "protocol", "reference", "workload"])
def test_inspected_future_shape_cannot_bind_after_identity_or_policy_change(go, monkeypatch, change):
    transport = go.qualify()
    factory = go.make()
    narrowed = factory.with_inspection(factory.inspect())
    cfg = None
    if change == "workload":
        cfg = {"provider_order": ["fabric"], "workload_profile": "site_batch"}
    else:
        changes = {"endpoint": {"base_url": "http://127.0.0.1:50143/v1"},
            "protocol": {"protocol": client.LEGACY_PROTOCOL},
            "reference": {"secret_ref": "OTHER_APPLICATION_TOKEN"}}[change]
        replacement = replace(transport, **changes)
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, TRANSPORT, replacement)
        go.row.update({key: getattr(replacement, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
        go.manifest["capabilities"][0]["secret_ref"] = replacement.secret_ref
        go.save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="identity_changed"):
        narrowed._bind_with_workload(cfg, operation_id="admin:original-turn")
    assert go.events == []
