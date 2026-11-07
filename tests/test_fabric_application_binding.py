"""Real owner/policy/manifest composition, with synthetic qualification only.

No production application mode is enrolled or qualified by these tests. The
internal transport fixture stands in for a future owner-qualified implementation;
it does not patch the policy or capability decision, and never sends a request.
"""
from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path

import pytest
import yaml

from engine import fabric_inference_client as client_module
from engine import provider_production_modes as owner

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def binding(tmp_path, monkeypatch):
    cfgdir = tmp_path / "config"
    cfgdir.mkdir()
    policy = json.loads((ROOT / "config/provider_workloads.v1.json").read_text())
    (cfgdir / "provider_workloads.v1.json").write_text(json.dumps(policy))
    document = json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())
    transport = owner._ApplicationFabricTransport(
        "http://127.0.0.1:8311/v1", "TEST_FABRIC_PROXY_TOKEN",
        "fixture-provider", "fixture-model", "unknown", "fabric:fixture",
        "fixture_capability", qualified=True, application_allowed=True,
    )
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", transport)
    row = {k: getattr(transport, k) for k in owner._APPLICATION_IDENTITY_FIELDS}
    row.update(transport_id="fixture_v1", enabled=True, application_allowed=True,
               qualification=owner.PROFILE_QUALIFIED_CANARY,
               qualification_ref="fixture:qualified-source-only", qualified_until=time.time()+3600)
    document["application_fabric_modes"] = {"shared_fabric": row}
    manifest = {"capabilities": [{"capability_id": "fixture_capability",
                 "secret_ref": "TEST_FABRIC_PROXY_TOKEN", "kill_state": "active",
                 "allowed_lanes": ["admin-orchestrator", "brain"]}]}
    events = []
    original_secret = owner._resolve_credential
    original_client = client_module.FabricInferenceClient

    def secret(mode, env):
        events.append("credential")
        return original_secret(mode, env)

    def client(**kwargs):
        events.append("client")
        return original_client(**kwargs)

    monkeypatch.setattr(owner, "_resolve_credential", secret)
    monkeypatch.setattr(client_module, "FabricInferenceClient", client)
    monkeypatch.setenv("TEST_FABRIC_PROXY_TOKEN", "synthetic-proxy-token-for-offline-test")
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    for module, name in [(owner.provider_health, "record_attempt"), (owner.ai_costs, "record_usage")]:
        monkeypatch.setattr(module, name, lambda **kw: pytest.fail("factory wrote a usage/health effect"))

    def save():
        (cfgdir / "provider_production_modes.v1.json").write_text(json.dumps(document))
        (cfgdir / "capability_manifest.yml").write_text(yaml.safe_dump(manifest))

    def make(cfg=None, **kwargs):
        return owner.make_application_fabric_factory(
            mode_id="shared_fabric", lane="admin-orchestrator", root=tmp_path,
            workload_cfg=cfg if cfg is not None else {
                "workload_profile": "site_interactive", "provider_order": ["fabric"]},
            **kwargs,
        )

    save()
    return tmp_path, row, document, manifest, events, save, make, transport


def test_real_composition_returns_only_actual_owner_identity_and_fresh_clients(binding):
    _, _, _, _, events, _, make, _ = binding
    factory = make()
    a, b = factory(), factory()
    assert set(a) == {"client", "model", "provider", "cost_basis", "cap_id"}
    assert a["client"] is not b["client"]
    assert {k: v for k, v in a.items() if k != "client"} == {
        "model": "fixture-model", "provider": "fixture-provider",
        "cost_basis": "unknown", "cap_id": "fabric:fixture"}
    assert events == ["credential", "client", "credential", "client"]


@pytest.mark.parametrize("profile", [None, "", "unknown", "development_agent", "fable_orchestration"])
def test_invalid_or_native_profile_refuses_before_secret(binding, profile):
    _, _, _, _, events, _, make, _ = binding
    with pytest.raises(ValueError):
        make({"workload_profile": profile, "provider_order": ["fabric"]})()
    assert events == []


def test_absent_profile_is_not_fabric_permission(binding):
    _, _, _, _, events, _, make, _ = binding
    with pytest.raises(owner.ApplicationFabricBindingError, match="workload_denied"):
        make({"provider_order": ["fabric"]})()
    assert events == []


def test_host_profile_can_supply_permission_but_cannot_be_weakened(binding, monkeypatch):
    root, _, _, _, events, _, make, _ = binding
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_batch")
    factory = make({"provider_order": ["fabric"]})
    assert factory()["model"] == "fixture-model"
    events.clear()
    path = root / "config/provider_workloads.v1.json"
    policy = json.loads(path.read_text())
    policy["profiles"]["site_batch"]["allowed_providers"].remove("fabric")
    path.write_text(json.dumps(policy))
    with pytest.raises(owner.ApplicationFabricBindingError, match="workload_denied"):
        make()()
    assert events == []
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "")
    with pytest.raises(ValueError):
        make()()
    assert events == []


@pytest.mark.parametrize("key,value", [
    ("base_url", "https://attacker.invalid/v1"), ("base_url", "http://127.0.0.1:9999/v1"),
    ("model", "other-model"), ("provider_id", "fabric"), ("cost_basis", "subscription"),
    ("cap_id", "wrong:cap"), ("capability_id", "claude_code_oauth"),
    ("secret_ref", "DEEPSEEK_API_KEY"), ("transport_id", "unknown"),
    ("enabled", 1), ("application_allowed", "true"), ("qualification", {}),
    ("qualified_until", True), ("qualified_until", 10**400),
])
def test_metadata_tamper_refuses_before_secret(binding, key, value):
    _, row, _, _, events, save, make, _ = binding
    row[key] = value
    save()
    with pytest.raises(owner.ApplicationFabricBindingError):
        make()()
    assert events == []


@pytest.mark.parametrize("key,value,code", [
    ("enabled", False, "disabled"),
    ("qualification", owner.PROFILE_UNQUALIFIED_PENDING_CANARY, "unqualified"),
    ("application_allowed", False, "not_permitted"),
    ("qualification_ref", None, "qualification_expired"),
    ("qualified_until", None, "qualification_expired"),
    ("qualified_until", 1, "qualification_expired"),
])
def test_owner_revocation_is_fresh_on_an_existing_factory(binding, key, value, code):
    _, row, _, _, events, save, make, _ = binding
    factory = make()
    factory()
    events.clear()
    row[key] = value
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match=code):
        factory()
    assert events == []


@pytest.mark.parametrize("change", ["kill", "lane", "ref", "remove"])
def test_real_manifest_revocation_or_wrong_ref_never_uses_cached_permission(binding, change):
    _, _, _, manifest, events, save, make, _ = binding
    factory = make()
    factory()
    events.clear()
    cap = manifest["capabilities"][0]
    if change == "kill": cap["kill_state"] = "killed"
    if change == "lane": cap["allowed_lanes"] = ["different-lane"]
    if change == "ref": cap["secret_ref"] = "OTHER_PROXY_TOKEN"
    if change == "remove": manifest["capabilities"] = []
    save()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory()
    assert events == []


def test_configuration_cannot_promote_held_experiential_transport(binding):
    _, row, _, _, events, save, make, _ = binding
    held = owner._APPLICATION_FABRIC_TRANSPORTS["experiential_proxy_v1"]
    row.update({k: getattr(held, k) for k in owner._APPLICATION_IDENTITY_FIELDS})
    row["transport_id"] = "experiential_proxy_v1"
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="unqualified"):
        make()()
    assert events == []


def test_native_qualification_is_not_application_permission(binding, monkeypatch):
    _, _, _, _, events, _, make, transport = binding
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1",
                        dataclasses.replace(transport, application_allowed=False))
    with pytest.raises(owner.ApplicationFabricBindingError, match="not_permitted"):
        make()()
    assert events == []


def test_shipped_owner_has_no_enrolled_application_mode(binding):
    root, _, document, _, events, save, make, _ = binding
    shipped = json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())
    assert shipped["application_fabric_modes"] == {}
    document["application_fabric_modes"] = shipped["application_fabric_modes"]
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="binding_missing"):
        make()()
    assert events == []


@pytest.mark.parametrize("order", [None, [], ["oauth", "fabric"], ["fabric", "fabric"], "fabric"])
def test_selection_cannot_hide_a_mixed_or_implicit_provider_order(binding, order):
    _, _, _, _, events, _, make, _ = binding
    with pytest.raises(owner.ApplicationFabricBindingError, match="provider_order_invalid"):
        make({"workload_profile": "site_interactive", "provider_order": order})
    assert events == []


def test_startup_configuration_is_snapshotted_but_policy_is_fresh(binding):
    _, _, _, _, _, _, make, _ = binding
    cfg = {"workload_profile": "site_interactive", "provider_order": ["fabric"]}
    factory = make(cfg)
    cfg["workload_profile"] = "development_agent"
    cfg["provider_order"].append("oauth")
    assert factory()["model"] == "fixture-model"


def test_actual_provider_builder_composes_owner_host_and_caller_policy(binding, monkeypatch):
    from engine import llm_auth

    _, _, _, _, events, _, make, _ = binding
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_batch")
    providers = llm_auth.build_providers(
        {"workload_profile": "portfolio_analysis", "provider_order": ["oauth", "deepseek"]},
        fabric_selected=True, fabric_provider_factory=make(), request_id="owner-composition-1",
    )
    assert len(providers) == 1 and llm_auth.is_fabric_provider(providers[0])
    receipt = providers[0]["workload_policy"]
    assert receipt["profiles"] == ["site_batch", "site_interactive", "portfolio_analysis"]
    assert receipt["allowed_order"] == ["fabric"] and receipt["denied_order"] == []
    assert providers[0]["model"] == "fixture-model"
    assert events == ["credential", "client"]


@pytest.mark.parametrize("profile", [None, "", "unknown", "development_agent"])
def test_actual_caller_profile_cannot_be_erased_by_startup_factory(binding, profile):
    from engine import llm_auth

    _, _, _, _, events, _, make, _ = binding
    with pytest.raises(llm_auth.FabricProviderError):
        llm_auth.build_providers(
            {"workload_profile": profile}, fabric_selected=True,
            fabric_provider_factory=make(), request_id="owner-composition-invalid",
        )
    assert events == []


def test_stricter_caller_profile_intersects_startup_permission(binding):
    from engine import llm_auth

    root, _, _, _, events, _, make, _ = binding
    path = root / "config/provider_workloads.v1.json"
    policy = json.loads(path.read_text())
    policy["profiles"]["portfolio_analysis"]["allowed_providers"].remove("fabric")
    path.write_text(json.dumps(policy))
    with pytest.raises(llm_auth.FabricProviderError):
        llm_auth.build_providers(
            {"workload_profile": "portfolio_analysis"}, fabric_selected=True,
            fabric_provider_factory=make(), request_id="owner-composition-strict",
        )
    assert events == []


def test_arbitrary_factory_still_cannot_claim_host_workload_qualification(binding, monkeypatch):
    from engine import llm_auth

    _, _, _, _, events, _, make, _ = binding
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_interactive")
    with pytest.raises(llm_auth.FabricProviderError, match="workload_policy_unqualified"):
        llm_auth.build_fabric_provider(lambda: make()(), request_id="forged-owner")
    assert events == []


def test_missing_proxy_credential_never_constructs_a_client(binding, monkeypatch):
    _, _, _, _, events, _, make, _ = binding
    monkeypatch.delenv("TEST_FABRIC_PROXY_TOKEN")
    with pytest.raises(owner.ApplicationFabricBindingError, match="unconfigured"):
        make()()
    assert events == ["credential"]


def test_duplicate_owner_keys_refuse_before_credential(binding):
    root, _, _, _, events, _, make, _ = binding
    path = root / "config/provider_production_modes.v1.json"
    text = path.read_text().replace('"enabled": true', '"enabled": false, "enabled": true')
    assert text != path.read_text()
    path.write_text(text)
    with pytest.raises(owner.ApplicationFabricBindingError, match="owner_config_invalid"):
        make()()
    assert events == []


@pytest.mark.parametrize("value", [None, "", "unknown", " shared_fabric", "shared_fabric"])
def test_service_startup_selection_preserves_presence_and_never_reads_a_secret(binding, monkeypatch, value):
    root, _, _, _, events, _, _, _ = binding
    if value is None:
        monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE", raising=False)
    else:
        monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", value)
    selected, factory = owner.configured_application_fabric(
        lane="admin-orchestrator", workload_profile="site_interactive", root=root)
    assert selected is (value is not None)
    assert (type(factory) is owner.ApplicationFabricFactory) is (value == "shared_fabric")
    assert events == []


@pytest.fixture
def native_purpose_binding(binding, monkeypatch):
    """Synthetic source qualification; no shipped transport is promoted."""
    root, row, document, manifest, events, save, make, transport = binding
    selected = dataclasses.replace(transport, protocol="native_application_v1",
        native_recipe_digest="a" * 64, execution_surface="native_agent")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", selected)
    return binding, selected


def test_native_purpose_uses_original_owner_and_empty_inference_allowlist(native_purpose_binding, monkeypatch):
    from engine import llm_auth

    binding, selected = native_purpose_binding
    root, _, _, _, events, _, make, _ = binding
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "fable_orchestration")
    monkeypatch.setattr(client_module, "_NativeConnection",
        lambda *args, **kwargs: pytest.fail("factory attempted admission or network"))
    factory = make({"workload_profile": "development_agent", "provider_order": ["fabric"],
                    "client_timeout_s": 17})
    caller = {"workload_profile": "lobe_maintenance", "client_timeout_s": 9}
    inspection = factory.inspect(caller)
    receipt = inspection["workload_policy"]
    assert receipt["execution_surface"] == "native_agent"
    assert receipt["profiles"] == ["fable_orchestration", "development_agent", "lobe_maintenance"]
    assert receipt["allowed_order"] == [] and receipt["denied_order"] == []
    assert events == []
    provider = llm_auth.build_fabric_provider(factory.with_inspection(inspection),
        request_id="native-purpose-original-1", workload_cfg=caller)
    assert provider["workload_policy"] == receipt
    bound_client = provider["client"]._client
    assert bound_client.operation_id == "native-purpose-original-1"
    assert bound_client._native_recipe_digest == selected.native_recipe_digest
    assert bound_client._timeout == 9
    assert events == ["credential", "client"]
    policy = json.loads((root / "config/provider_workloads.v1.json").read_text())
    assert all(policy["profiles"][name]["allowed_providers"] == [] for name in receipt["profiles"])


@pytest.mark.parametrize("profile", ["development_agent", "fable_orchestration", "lobe_maintenance"])
def test_native_wire_protocol_and_recipe_do_not_promote_inference_source(binding, monkeypatch, profile):
    _, _, _, _, events, _, make, transport = binding
    selected = dataclasses.replace(transport, protocol="native_application_v1", native_recipe_digest="a" * 64)
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", selected)
    with pytest.raises(ValueError):
        make({"workload_profile": profile, "provider_order": ["fabric"],
              "execution_surface": "native_agent"}).inspect()
    assert events == []
    assert make().inspect()["workload_policy"]["execution_surface"] == "inference"


@pytest.mark.parametrize("host,caller", [("site_interactive", "development_agent"),
    ("development_agent", "site_batch"), ("fable_orchestration", None),
    ("lobe_maintenance", ""), ("development_agent", "unregistered-purpose")])
def test_native_purpose_keeps_host_and_caller_intersection_closed(native_purpose_binding, monkeypatch, host, caller):
    binding, _ = native_purpose_binding
    _, _, _, _, events, _, make, _ = binding
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", host)
    factory = make({"workload_profile": "development_agent", "provider_order": ["fabric"]})
    with pytest.raises(ValueError):
        factory._bind_with_workload({"workload_profile": caller}, operation_id="native-purpose-refused")
    assert events == []


@pytest.mark.parametrize("change", [{"native_recipe_digest": None}, {"native_recipe_digest": "bad"},
    {"protocol": "openai_chat_v1"}, {"automatic": True}, {"execution_surface": "unrecognized"}])
def test_native_purpose_requires_exact_source_recipe_before_secret(native_purpose_binding, monkeypatch, change):
    binding, selected = native_purpose_binding
    _, _, _, _, events, _, make, _ = binding
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", dataclasses.replace(selected, **change))
    with pytest.raises(ValueError):
        make({"workload_profile": "development_agent", "provider_order": ["fabric"]}).inspect()
    assert events == []


@pytest.mark.parametrize("change", ["expired", "unqualified", "permission", "capability", "policy"])
def test_native_purpose_rechecks_existing_qualification_and_policy(native_purpose_binding, change):
    binding, _ = native_purpose_binding
    root, row, _, manifest, events, save, make, _ = binding
    factory = make({"workload_profile": "development_agent", "provider_order": ["fabric"]})
    factory.inspect()
    if change == "expired": row["qualified_until"] = 1
    if change == "unqualified": row["qualification"] = owner.PROFILE_UNQUALIFIED_PENDING_CANARY
    if change == "permission": row["application_allowed"] = False
    if change == "capability": manifest["capabilities"][0]["kill_state"] = "killed"
    if change == "policy":
        path = root / "config/provider_workloads.v1.json"
        policy = json.loads(path.read_text())
        policy["profiles"]["development_agent"]["allowed_providers"] = ["fabric"]
        path.write_text(json.dumps(policy))
    save()
    with pytest.raises(ValueError):
        factory._bind_with_workload(operation_id="native-purpose-revoked")
    assert events == []


def test_native_purpose_cannot_be_set_in_an_owner_configuration_record(binding):
    _, row, _, _, events, save, make, _ = binding
    row["execution_surface"] = "native_agent"
    save()
    with pytest.raises(owner.ApplicationFabricBindingError): make().inspect()
    assert events == []


# The source-qualified AUTO implementations still require independent current
# application data and capability authority before a credential can be opened.
_AUTO_SOURCE_AUTHORITIES = (
    ("shared_fabric", "native_fabric_application_auto_v1", None, "admin-orchestrator", "site_interactive"),
    ("mastermind_text_fabric", "native_fabric_mastermind_text_auto_v1", "mastermind_text_fabric", "mastermind-text", "site_batch"),
    ("mastermind_chat_fabric", "native_fabric_mastermind_chat_auto_v1", "mastermind_chat_fabric", "mastermind-chat", "site_interactive"),
    ("macro_brain_fabric", "native_fabric_macro_brain_auto_v1", "macro_brain_fabric", "brain", "site_interactive"),
    ("macro_ask_fabric", "native_fabric_macro_ask_auto_v1", "macro_ask_fabric", "ask-brain", "site_interactive"),
    ("macro_batch_fabric", "native_fabric_macro_batch_auto_v1", None, "master-brain", "site_batch"),
    ("macro_analysis_fabric", "native_fabric_macro_analysis_auto_v1", None, "cortex", "lobe_analysis"),
    ("macro_portfolio_fabric", "native_fabric_macro_portfolio_auto_v1", None, "research-portfolio", "portfolio_analysis"),
)


def _configured_auto_source(binding, authority):
    root, _, document, manifest, events, save, _, _ = binding
    record, transport_id, service_mode, lane, workload = authority
    base = owner._APPLICATION_FABRIC_TRANSPORTS[transport_id]
    assert base.qualified and base.application_allowed
    row = {key: getattr(base, key) for key in owner._APPLICATION_IDENTITY_FIELDS}
    row.update(
        transport_id=transport_id, enabled=True, application_allowed=True,
        qualification=owner.PROFILE_QUALIFIED_CANARY,
        qualification_ref="fixture:source-support-runtime-gates",
        qualified_until=time.time() + 3600, admin_pool_view=False,
        route_scope={"schema": "mastermind.application_route_scope.v1", "pools": ["go"]},
    )
    document["application_fabric_modes"] = {record: row}
    if record != "shared_fabric":
        shared_id = "native_fabric_application_auto_v1"
        shared = owner._APPLICATION_FABRIC_TRANSPORTS[shared_id]
        document["application_fabric_modes"]["shared_fabric"] = {
            **row, **{key: getattr(shared, key) for key in owner._APPLICATION_IDENTITY_FIELDS},
            "transport_id": shared_id, "enabled": False, "application_allowed": False,
        }
    capability = {
        "capability_id": base.capability_id, "secret_ref": base.secret_ref,
        "kill_state": "active", "allowed_lanes": [lane],
    }
    manifest["capabilities"] = [capability]
    save()
    factory = owner.make_application_fabric_factory(
        mode_id="shared_fabric", lane=lane, root=root,
        workload_cfg={"provider_order": ["fabric"], "workload_profile": workload},
        service_mode_id=service_mode,
    )
    return factory, row, capability, document, manifest, events, save


@pytest.mark.parametrize("authority", _AUTO_SOURCE_AUTHORITIES, ids=lambda row: row[0])
@pytest.mark.parametrize("gate", [
    "empty", "disabled", "unqualified", "permission", "reference", "expiry",
    "capability_missing", "capability_killed", "capability_lane", "capability_ref",
])
def test_auto_source_support_cannot_supply_runtime_authority(binding, authority, gate):
    factory, row, capability, document, manifest, events, save = _configured_auto_source(binding, authority)
    assert factory.inspect() is not None
    assert events == []
    if gate == "empty":
        document["application_fabric_modes"] = {}
    elif gate == "disabled":
        row["enabled"] = False
    elif gate == "unqualified":
        row["qualification"] = "UNQUALIFIED_PENDING_CANARY"
    elif gate == "permission":
        row["application_allowed"] = False
    elif gate == "reference":
        row["qualification_ref"] = None
    elif gate == "expiry":
        row["qualified_until"] = time.time() - 1
    elif gate == "capability_missing":
        manifest["capabilities"] = []
    elif gate == "capability_killed":
        capability["kill_state"] = "killed"
    elif gate == "capability_lane":
        capability["allowed_lanes"] = ["unrelated-consumer"]
    elif gate == "capability_ref":
        capability["secret_ref"] = "OTHER_SYNTHETIC_TOKEN"
    save()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.inspect()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory()
    assert events == []


@pytest.mark.parametrize("authority", _AUTO_SOURCE_AUTHORITIES, ids=lambda row: row[0])
def test_auto_source_inspection_rechecks_real_capability_after_revocation(binding, authority):
    factory, _, capability, _, _, events, save = _configured_auto_source(binding, authority)
    inspection = factory.inspect()
    assert inspection is not None
    assert events == []
    capability["kill_state"] = "killed"
    save()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.inspect()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory()
    assert events == []


@pytest.mark.parametrize("fault", ["empty", "disabled", "metadata_permission", "capability_killed", "capability_ref"])
def test_auto_admin_metadata_requires_its_own_current_authority(binding, fault):
    factory, row, capability, document, _, events, save = _configured_auto_source(
        binding, _AUTO_SOURCE_AUTHORITIES[0]
    )
    row["admin_pool_view"] = True
    if fault == "empty":
        document["application_fabric_modes"] = {}
    elif fault == "disabled":
        row["enabled"] = False
    elif fault == "metadata_permission":
        row["admin_pool_view"] = False
    elif fault == "capability_killed":
        capability["kill_state"] = "killed"
    elif fault == "capability_ref":
        capability["secret_ref"] = "OTHER_SYNTHETIC_TOKEN"
    save()
    with pytest.raises(owner.ApplicationFabricBindingError):
        factory.prepare_admin_pool_reader()
    assert events == []
