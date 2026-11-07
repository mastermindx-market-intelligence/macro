"""The incumbent owner's credential-free inspection path.

The owner publishes ONE set of eligibility checks, factored out of the real
binder. The inspection runs those same checks and stops at the same
refusals — it just stops BEFORE the credential, so a consumer that only needs
to NAME the selected transport (a cache identity, for instance) never has to
resolve a secret to learn what is in force.

No production application mode is enrolled or qualified by these tests: the
shipped owner document stays empty and the fixture transport is a synthetic
QUALIFICATION of the actual owner, not a configuration change.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine import provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]

#: The exact metadata the inspection is allowed to publish.
PUBLISHED = {"provider", "model", "cap_id", "capability_id", "cost_basis",
             "workload_policy", "transport_identity"}


def test_inspection_publishes_the_real_selected_identity_without_a_credential(binding):
    _, _, _, _, events, _, make, _ = binding
    factory = make()
    seen = factory.inspect()
    assert set(seen) == PUBLISHED
    assert seen["provider"] == "fixture-provider"
    assert seen["model"] == "fixture-model"
    assert seen["cap_id"] == "fabric:fixture"
    assert seen["capability_id"] == "fixture_capability"
    assert seen["cost_basis"] == "unknown"
    assert seen["workload_policy"] == factory.workload_decision().receipt()
    # No credential was resolved and no transport was constructed.
    assert events == []


def test_inspection_publishes_no_client_secret_token_admission_or_claim(binding):
    _, _, _, _, events, _, make, _ = binding
    seen = make().inspect()
    flat = json.dumps(seen, sort_keys=True, default=str).lower()
    for forbidden in ("client", "secret", "proxy_token", "token", "admission",
                      "claim", "credential", "base_url"):
        assert forbidden not in flat
    assert events == []


def test_inspection_metadata_is_not_a_binding_and_cannot_be_used_as_one(binding):
    _, _, _, _, events, _, make, _ = binding
    seen = make().inspect()
    # It is not a provider descriptor: no client, no credential, no model
    # override a caller could hand to the shared wrapper.
    assert "client" not in seen
    assert not callable(seen)
    from engine import llm_auth

    with pytest.raises(Exception):
        llm_auth.build_fabric_provider(seen, request_id="forged-inspection")
    assert events == []


@pytest.mark.parametrize("key,value,code", [
    ("enabled", False, "disabled"),
    ("qualification", owner.PROFILE_UNQUALIFIED_PENDING_CANARY, "unqualified"),
    ("application_allowed", False, "not_permitted"),
    ("qualification_ref", None, "qualification_expired"),
    ("qualified_until", None, "qualification_expired"),
    ("qualified_until", 1, "qualification_expired"),
])
def test_inspection_refuses_exactly_where_the_binder_refuses(binding, key, value, code):
    _, row, _, _, events, save, make, _ = binding
    factory = make()
    assert factory.inspect()["model"] == "fixture-model"
    assert events == []
    row[key] = value
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match=code):
        factory.inspect()
    with pytest.raises(owner.ApplicationFabricBindingError, match=code):
        factory()
    # Both refusals happened BEFORE any credential was read.
    assert events == []


def test_a_revoked_qualification_refuses_the_later_fill_not_the_earlier_inspection(binding):
    _, row, _, _, events, save, make, _ = binding
    factory = make()
    assert factory.inspect()["model"] == "fixture-model"
    row["qualified_until"] = 1
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="qualification_expired"):
        factory()
    assert events == []


def test_a_missing_credential_prevents_the_fill_but_not_the_inspection(binding, monkeypatch):
    _, _, _, _, events, _, make, _ = binding
    monkeypatch.delenv("TEST_FABRIC_PROXY_TOKEN")
    factory = make()
    # The IDENTITY of the selected transport is knowable without the secret...
    assert factory.inspect()["model"] == "fixture-model"
    # ...but the transport is not ready, and the readiness is not fabricated.
    with pytest.raises(owner.ApplicationFabricBindingError, match="unconfigured"):
        factory()
    assert events == ["credential"]


def test_a_capability_revocation_refuses_the_inspection(binding):
    _, _, _, manifest, events, save, make, _ = binding
    manifest["capabilities"][0]["kill_state"] = "killed"
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="capability_denied"):
        make().inspect()
    assert events == []


def test_a_wrong_capability_ref_refuses_the_inspection(binding):
    _, _, _, manifest, events, save, make, _ = binding
    manifest["capabilities"][0]["secret_ref"] = "OTHER_PROXY_TOKEN"
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="ref_mismatch"):
        make().inspect()
    assert events == []


@pytest.mark.parametrize("profile", [None, "", "unknown", "development_agent"])
def test_an_invalid_caller_profile_refuses_the_inspection(binding, profile):
    _, _, _, _, events, _, make, _ = binding
    factory = make()
    with pytest.raises(ValueError):
        factory.inspect({"workload_profile": profile})
    assert events == []


def test_the_inspection_uses_the_same_workload_receipt_the_binder_publishes(binding):
    _, _, _, _, events, _, make, _ = binding
    factory = make()
    seen = factory.inspect()
    bound, decision = factory._bind_with_workload()
    assert seen["workload_policy"] == decision.receipt()
    assert bound["model"] == seen["model"]
    assert bound["provider"] == seen["provider"]
    assert bound["cap_id"] == seen["cap_id"]
    assert bound["cost_basis"] == seen["cost_basis"]
    assert events == ["credential", "client"]


def test_the_inspection_does_not_qualify_an_unregistered_transport(binding):
    _, _, document, _, events, save, make, _ = binding
    shipped = json.loads((ROOT / "config/provider_production_modes.v1.json").read_text())
    assert shipped["application_fabric_modes"] == {}
    document["application_fabric_modes"] = shipped["application_fabric_modes"]
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="binding_missing"):
        make().inspect()
    assert events == []


def test_narrowed_owner_is_accepted_by_the_existing_shared_wrapper(binding):
    from engine import llm_auth

    _, _, _, _, events, _, make, _ = binding
    factory = make()
    snapshot = factory.inspect()
    narrowed = factory.with_inspection(snapshot)
    assert type(narrowed) is owner.ApplicationFabricFactory
    assert narrowed is not factory
    assert events == []
    provider = llm_auth.build_fabric_provider(narrowed, request_id="inspection:unchanged")
    assert provider["model"] == snapshot["model"]
    assert provider["cap_id"] == snapshot["cap_id"]
    assert events == ["credential", "client"]
    llm_auth.close_fabric_provider(provider)


def test_inspection_commitment_copies_nested_metadata_by_value(binding):
    _, _, _, _, events, _, make, _ = binding
    factory = make()
    snapshot = factory.inspect()
    narrowed = factory.with_inspection(snapshot)
    snapshot["model"] = "caller-chosen-model"
    snapshot["workload_policy"]["policy_hash"] = "caller-chosen-policy"
    assert narrowed.inspect()["model"] == "fixture-model"
    assert narrowed()["model"] == "fixture-model"
    assert events == ["credential", "client"]


def test_rebinding_an_observed_identity_cannot_retarget_a_narrowed_owner(binding, monkeypatch):
    _, row, _, _, events, save, make, transport = binding
    factory = make()
    narrowed = factory.with_inspection(factory.inspect())
    changed = replace(transport, model="other-valid-model")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", changed)
    row["model"] = changed.model
    save()
    current = factory.inspect()
    assert current["model"] == changed.model
    for action in (narrowed, narrowed.inspect, lambda: narrowed.with_inspection(current)):
        with pytest.raises(owner.ApplicationFabricBindingError, match="identity_changed"):
            action()
    assert events == []


@pytest.mark.parametrize("change", ["missing", "extra", "nonfinite", "unserializable"])
def test_invalid_inspection_metadata_is_refused_without_effects(binding, change):
    _, _, _, _, events, _, make, _ = binding
    factory = make()
    snapshot = factory.inspect()
    if change == "missing":
        snapshot.pop("model")
    elif change == "extra":
        snapshot["client"] = "not-a-client"
    elif change == "nonfinite":
        snapshot["workload_policy"]["policy_hash"] = float("nan")
    else:
        snapshot["model"] = object()
    with pytest.raises(owner.ApplicationFabricBindingError, match="inspection_invalid"):
        factory.with_inspection(snapshot)
    assert events == []


def test_forged_snapshot_cannot_grant_permission_or_skip_fresh_revocation(binding):
    _, row, _, _, events, save, make, _ = binding
    factory = make()
    snapshot = factory.inspect()
    snapshot["model"] = "unqualified-model"
    with pytest.raises(owner.ApplicationFabricBindingError, match="identity_changed"):
        factory.with_inspection(snapshot)()
    narrowed = factory.with_inspection(factory.inspect())
    row["enabled"] = False
    save()
    with pytest.raises(owner.ApplicationFabricBindingError, match="disabled"):
        narrowed()
    assert events == []
