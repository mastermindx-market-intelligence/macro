"""Native enablement comes only from the selected source export."""
import copy
import json
from pathlib import Path

import pytest

from engine import provider_capacity_v2 as capacity
from engine import provider_native_capabilities as native
from tests.test_provider_native_capabilities import make_registry, make_row, expected_receipt


def registry(*, version=2, enabled=False, state="registered", generation=1):
    row = make_row(cid="cap.fixture", gen=generation, state=state)
    if version == 2:
        row["provider_enabled"] = enabled
    schema = native.REGISTRY_SCHEMA_V2 if version == 2 else native.REGISTRY_SCHEMA
    return make_registry([row], schema=schema)


def export(document):
    return native.registration_export(document, "cap.fixture", material_source_digest="a" * 64)


def acquired(document):
    selected = dict(export(document), source_release_commit="a" * 40,
                    previous_release_commit="b" * 40, source_receipt_digest="c" * 64)
    observation = {"capacity_capability_id": "cap.fixture", "capability_generation": 1,
        "source_receipt_digest": "c" * 64, "host_ref": "host.fixture", "boot_ref": "boot.fixture",
        "realm_generation": 1, "enrollment_receipt_digest": "d" * 64,
        "observed_at": "2026-10-18T00:00:00.000Z",
        "realm_auth": {"state": "unknown", "method": "unknown", "source_quality": "unknown"},
        "provider_health": {"state": "unknown", "error_class": None, "scope": "unknown", "observed_at": None},
        "cooling": {"active": None, "kind": None, "reset_at": None, "evidence": "unknown",
                    "scope": "unknown", "observed_at": None},
        "quota_horizons": [],
        "last_provider_outcome": {"class": "unknown", "observed_at": None, "scope": "unknown"}}
    return {"registration": selected, "observation": observation,
            "worker_source_config_digest": "e" * 64, "producer_sha256": "f" * 64}


def test_checked_in_successor_is_disabled_without_new_identity():
    document = json.loads((Path(__file__).resolve().parents[1] /
                           "config/provider_native_capabilities.v1.json").read_text())
    assert native.validate_registry(document) == document
    assert document["schema"] == native.REGISTRY_SCHEMA_V2
    row, = document["capabilities"]
    assert row["capacity_capability_id"] == "ncap_1474fe7261ff4652b5a5cd95b6d38fd1"
    assert row["capability_generation"] == 1
    assert row["registration_state"] == "registered"
    assert row["provider_enabled"] is False


def test_v1_normalization_export_and_unknown_enablement_stay_exact():
    document = registry(version=1)
    assert native.validate_registry(document) == document
    selected = export(document)
    assert selected["schema"] == native.REGISTRATION_EXPORT_SCHEMA
    assert "provider_enabled" not in selected
    assert capacity._normalize(acquired(document), 1)["slots"][0]["provider_enabled"] is None


@pytest.mark.parametrize("enabled", [False, True])
def test_v2_export_binds_bool_to_receipt_without_aliasing(enabled):
    document = registry(enabled=enabled)
    before = copy.deepcopy(document)
    selected = export(document)
    assert selected["schema"] == native.REGISTRATION_EXPORT_SCHEMA_V2
    assert selected["provider_enabled"] is enabled
    assert selected["registration_receipt_digest"] == expected_receipt(selected)
    selected["provider_enabled"] = not enabled
    assert document == before


def test_enablement_changes_receipt_without_changing_identity_or_generation():
    disabled, enabled = export(registry()), export(registry(enabled=True))
    assert disabled["registration_receipt_digest"] != enabled["registration_receipt_digest"]
    for key in ("capacity_capability_id", "capability_generation", "provider", "billing_mode",
                "credential_kind", "execution_surface", "registration_state", "material_source_digest"):
        assert disabled[key] == enabled[key]


@pytest.mark.parametrize("bad", [None, 0, 1, "false", "true", [], {}])
def test_enablement_requires_real_bool_in_registry_and_producer(bad):
    with pytest.raises(native.NativeCapabilityError, match="^invalid_provider_enabled$"):
        native.validate_registry(registry(enabled=bad))
    value = acquired(registry())
    value["registration"]["provider_enabled"] = bad
    with pytest.raises(ValueError, match="^NATIVE_CAPACITY_ENABLEMENT_REFUSED$"):
        capacity._normalize(value, 1)


def test_missing_v2_flag_and_flag_smuggled_into_v1_refuse():
    document = registry()
    del document["capabilities"][0]["provider_enabled"]
    with pytest.raises(native.NativeCapabilityError, match="^missing_capability_field$"):
        native.validate_registry(document)
    document = registry(version=1)
    document["capabilities"][0]["provider_enabled"] = True
    with pytest.raises(native.NativeCapabilityError, match="^unexpected_capability_field$"):
        native.validate_registry(document)
    value = acquired(registry(version=1))
    value["registration"]["provider_enabled"] = True
    with pytest.raises(ValueError, match="^NATIVE_CAPACITY_ENABLEMENT_REFUSED$"):
        capacity._normalize(value, 1)


def test_revocation_requires_disabled_policy_and_never_normalizes_as_live():
    with pytest.raises(native.NativeCapabilityError, match="^revoked_capability_enabled$"):
        native.validate_registry(registry(state="revoked", enabled=True))
    current = registry(state="revoked")
    assert native.validate_registry_transition(registry(enabled=True), current) == current
    with pytest.raises(ValueError, match="^NATIVE_CAPACITY_SOURCE_JOIN_REFUSED$"):
        capacity._normalize(acquired(current), 1)


def test_v1_to_v2_adoption_is_disabled_and_cannot_regress():
    assert native.validate_registry_transition(registry(version=1), registry()) == registry()
    with pytest.raises(native.NativeCapabilityError, match="^transition_enablement_not_disarmed$"):
        native.validate_registry_transition(registry(version=1), registry(enabled=True))
    with pytest.raises(native.NativeCapabilityError, match="^transition_schema_regressed$"):
        native.validate_registry_transition(registry(), registry(version=1))


@pytest.mark.parametrize("version", [1, 2])
def test_first_registration_starts_disabled(version):
    previous = registry(version=version)
    previous["capabilities"] = []
    assert native.validate_registry_transition(previous, registry()) == registry()
    with pytest.raises(native.NativeCapabilityError, match="^transition_enablement_not_disarmed$"):
        native.validate_registry_transition(previous, registry(enabled=True))


def test_new_capability_in_existing_domain_starts_disabled():
    current = registry()
    current["capabilities"].append(dict(current["capabilities"][0],
                                      capacity_capability_id="cap.second", provider_enabled=True))
    with pytest.raises(native.NativeCapabilityError, match="^transition_enablement_not_disarmed$"):
        native.validate_registry_transition(registry(), current)


def test_enable_disable_preserve_generation_and_revived_generation_starts_disabled():
    enabled = registry(enabled=True)
    assert native.validate_registry_transition(registry(), enabled) == enabled
    assert native.validate_registry_transition(enabled, registry()) == registry()
    with pytest.raises(native.NativeCapabilityError, match="^transition_registered_generation_changed$"):
        native.validate_registry_transition(registry(), registry(enabled=True, generation=2))
    with pytest.raises(native.NativeCapabilityError, match="^transition_capability_resurrection$"):
        native.validate_registry_transition(registry(state="revoked"), registry())
    with pytest.raises(native.NativeCapabilityError, match="^transition_enablement_not_disarmed$"):
        native.validate_registry_transition(registry(state="revoked"), registry(enabled=True, generation=2))
    revived = registry(generation=2)
    assert native.validate_registry_transition(registry(state="revoked"), revived) == revived


@pytest.mark.parametrize("enabled", [False, True])
def test_only_export_supplies_enablement_and_provider_facts_stay_unknown(monkeypatch, enabled):
    value = acquired(registry(enabled=enabled))
    monkeypatch.setenv("MINIMAX_ENABLED", str(not enabled))
    value["observation"]["provider_enabled"] = not enabled
    value["provider_enabled"] = not enabled
    row, = capacity._normalize(value, 1)["slots"]
    assert row["provider_enabled"] is enabled
    assert row["realm_auth"]["state"] == "unknown"
    assert row["provider_health"]["state"] == "unknown"
    assert row["cooling"]["active"] is None
    assert row["quota_horizons"] == []


@pytest.mark.parametrize("schema", [None, "", "mastermind.provider_native_capability_registration/v999", True])
def test_unknown_schema_cannot_supply_enablement(schema):
    value = acquired(registry(enabled=True))
    value["registration"]["schema"] = schema
    with pytest.raises(ValueError, match="^NATIVE_CAPACITY_ENABLEMENT_REFUSED$"):
        capacity._normalize(value, 1)


@pytest.mark.parametrize("key,replacement", [("capability_generation", 2), ("source_receipt_digest", "0" * 64)])
def test_source_join_still_rejects_changed_generation_or_receipt(key, replacement):
    value = acquired(registry(enabled=True))
    value["observation"][key] = replacement
    with pytest.raises(ValueError, match="^NATIVE_CAPACITY_SOURCE_JOIN_REFUSED$"):
        capacity._normalize(value, 1)
