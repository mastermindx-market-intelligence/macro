"""Real owner fixture closure for exact house-output feature capabilities."""
from __future__ import annotations

import copy
import json
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import getcontext

import pytest

from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_identity as identity
from engine.neuralweb import market_memory_projection as projection
from engine.neuralweb import market_memory_trusted as trusted
from tests.test_market_memory_trusted import (
    _candidate, _capture, _raw_regime, SNAPSHOT_CLOCK, IDENTITY_CLOCK,
    CAPTURE_CLOCK, DEPLOYED_COMMIT,
)


class Policy:
    policy_id = "test.authenticated_application_policy.v1"

    def __init__(self, denied=()):
        self.denied = set(denied)
        self.calls = []

    def check(self, action, resource):
        self.calls.append((action, copy.deepcopy(resource)))
        if action in self.denied:
            raise PermissionError("denied")


@pytest.fixture
def owner(tmp_path, monkeypatch):
    candidate = _candidate(monkeypatch, tmp_path)
    stored = _capture(candidate)
    reader = trusted.TrustedFileAsKnownAtReader(candidate.public)
    generation = reader.read_pinned_generation()
    return candidate, stored, reader, generation


_DEFAULT = object()


def load(owner, policy=_DEFAULT, **overrides):
    _, stored, reader, generation = owner
    arguments = {"query_id": stored.capture_receipt["query_id"],
                 "subject_id": stored.packet["subject"]["subject_id"],
                 "query_cutoff": "2026-08-10T10:00:10Z", "policy": Policy() if policy is _DEFAULT else policy}
    arguments.update(overrides)
    return features.read_episode_feature_capability(reader, generation, **arguments)


def test_exact_owner_capability_and_fixed_descriptor(owner):
    policy = Policy()
    capability = load(owner, policy)
    value = features.disclose_episode_features(capability, policy=policy)
    assert value["context_id"] == owner[1].packet["context_id"]
    assert value["owner"]["generation_id"] == owner[3].generation_id
    assert value["coordinates"][0]["source_binary64_hex"] == float(0.133).hex()
    assert value["coordinates"][0]["unit"] == "dimensionless_house_regime_score"
    assert value["measurement_period"]["precision"] == "date"
    assert value["source_usage_admission"]["comparison_eligible_at_projection"] is True
    assert value["source_usage_admission"]["fit_eligible"] is False
    assert value["component_source_receipts_authenticated"] is False
    assert value["authority"]["may_train_prophet"] is False
    descriptor = features.fixed_comparison_descriptor()
    assert descriptor["mode"] == "fixed_domain_range"
    assert descriptor["fit_status"] == "not_performed"
    assert [x["weight"] for x in descriptor["coordinates"]] == ["0.2"] * 5
    assert [x["scale"] for x in descriptor["coordinates"][:2]] == ["2", "2"]
    assert "training_membership_sha256" not in descriptor
    assert "forbidden" not in json.dumps(value)


def test_rights_refused_before_owner_method(owner, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("owner read occurred before rights authorization")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader,
                        "read_pinned_capture_projections", forbidden)
    with pytest.raises(features.EpisodeFeatureAccessError):
        load(owner, Policy({"read_retained_macro_feature"}))


@pytest.mark.parametrize("policy", [True, False, None, object()])
def test_literal_permission_flag_is_not_policy(owner, policy):
    with pytest.raises(features.EpisodeFeatureAccessError):
        load(owner, policy=policy)


def test_truthy_policy_return_is_not_authorization(owner):
    class BooleanPolicy(Policy):
        def check(self, *args):
            return True
    with pytest.raises(features.EpisodeFeatureAccessError):
        load(owner, BooleanPolicy())


def test_disclosure_rechecks_rights_and_detaches_values(owner):
    policy = Policy()
    capability = load(owner, policy)
    first = features.disclose_episode_features(capability, policy=policy)
    first["coordinates"][0]["value_q18"] = "9"
    second = features.disclose_episode_features(capability, policy=policy)
    assert second["coordinates"][0]["value_q18"] != "9"
    policy.denied.add("disclose_retained_macro_feature")
    with pytest.raises(features.EpisodeFeatureAccessError):
        features.disclose_episode_features(capability, policy=policy)
    assert sum(action == "disclose_retained_macro_feature" for action, _ in policy.calls) == 3


def test_no_dict_or_public_constructor_capability(owner):
    with pytest.raises(features.EpisodeFeatureError):
        features.EpisodeFeatureCapability(b"{}", b"{}")
    with pytest.raises(features.EpisodeFeatureError):
        features.disclose_episode_features({}, policy=Policy())
    capability = load(owner)
    with pytest.raises(FrozenInstanceError):
        capability._body = b"{}"


def test_cached_comparison_rechecks_current_comparison_rights(owner):
    policy = Policy()
    capability = load(owner, policy)
    before = features.disclose_episode_features(capability, policy=policy, for_comparison=True)
    policy.denied.add("compare_retained_macro_feature")
    after = features.disclose_episode_features(capability, policy=policy)
    assert after["source_usage_admission"]["comparison_eligible_at_projection"] is True
    assert after["current_usage"]["comparison_authorized"] is False
    assert after["current_usage"]["comparison_eligible"] is False
    assert after["projection_id"] == before["projection_id"]
    assert after["coordinates"] == before["coordinates"]
    with pytest.raises(features.EpisodeFeatureAccessError):
        features.disclose_episode_features(capability, policy=policy, for_comparison=True)


def test_invalid_input_fails_before_policy_and_owner_read(owner):
    policy = Policy()
    with pytest.raises(features.EpisodeFeatureError):
        load(owner, policy, query_id="../latest.json")
    assert policy.calls == []


def test_accidental_capability_corruption_rejected(owner):
    capability = load(owner)
    object.__setattr__(capability, "_body", b"{}")
    with pytest.raises(features.EpisodeFeatureError):
        features.disclose_episode_features(capability, policy=Policy())


def test_fit_refusal_and_separate_comparison_admission(owner):
    policy = Policy({"compare_retained_macro_feature"})
    capability = load(owner, policy)
    value = features.disclose_episode_features(capability, policy=policy)
    assert value["source_usage_admission"]["capture_available"] is True
    assert value["source_usage_admission"]["comparison_eligible_at_projection"] is False
    with pytest.raises(features.EpisodeFeatureAccessError, match="source_usage_not_admitted"):
        features.require_fit_admission(capability, policy=policy)


@pytest.mark.parametrize("cutoff", ["2026-08-10T09:59:59Z", "2026-08-10T10:00:01Z"])
def test_future_observation_is_not_historical_feature(owner, cutoff):
    with pytest.raises(features.EpisodeFeatureError, match="not_available"):
        load(owner, query_cutoff=cutoff)


@pytest.mark.parametrize("cutoff", ["2026-08-10", "2026-08-10T10:00:10+00:00", "2026-99-10T10:00:10Z"])
def test_cutoff_precision_and_format_are_exact(owner, cutoff):
    with pytest.raises(features.EpisodeFeatureError):
        load(owner, query_cutoff=cutoff)


def test_wrong_subject_and_generation_rejected(owner):
    with pytest.raises(features.EpisodeFeatureSourceError):
        load(owner, subject_id="mmsecurity_" + "f" * 64)
    wrong = (*owner[:3], replace(owner[3], generation_sha256="f" * 64))
    with pytest.raises(features.EpisodeFeatureSourceError):
        load(wrong)


def test_tampered_original_feature_rejected(owner):
    candidate, stored, _, _ = owner
    ref = stored.capture_receipt["feature_snapshot"]
    path = candidate.public / ref["object_key"]
    path.write_bytes(b"{}")
    with pytest.raises(features.EpisodeFeatureSourceError):
        load(owner)


def test_unknown_mask_retained_with_authenticated_owner(tmp_path, monkeypatch):
    candidate = _candidate(monkeypatch, tmp_path)
    raw = _raw_regime()
    raw["liquidity_overlay"] = "unknown"
    body = (json.dumps(raw, sort_keys=True) + "\n").encode()
    candidate.source.write_bytes(body)
    snapshot = projection.build_macro_regime_snapshot(candidate.source)
    stored = trusted.capture_trusted_regime_context(
        candidate.public, candidate.private, snapshot=snapshot,
        identity_evidence=candidate.identity_evidence, raw_source_body=body,
        deployed_commit=DEPLOYED_COMMIT)
    reader = trusted.TrustedFileAsKnownAtReader(candidate.public)
    value = features.disclose_episode_features(
        load((candidate, stored, reader, reader.read_pinned_generation())), policy=Policy())
    coordinate = next(x for x in value["coordinates"] if x["id"] == "liquidity_overlay")
    assert coordinate["status"] == "unavailable" and coordinate["value"] is None
    assert len(value["coordinates"]) == 5
    assert value["source_usage_admission"]["comparison_eligible_at_projection"] is False


@pytest.mark.parametrize("number", [True, float("nan"), float("inf"), -1.1, 1.1])
def test_hostile_numeric_coordinates_refused(number):
    with pytest.raises(features.EpisodeFeatureError):
        features._numeric(number, "growth_score")


def test_numeric_convention_ignores_ambient_decimal_context():
    original = getcontext().prec
    try:
        getcontext().prec = 6
        first = features._numeric(0.133, "growth_score")
        getcontext().prec = 30
        assert features._numeric(0.133, "growth_score") == first
    finally:
        getcontext().prec = original


def test_future_head_addition_cannot_change_pinned_projection(owner, monkeypatch):
    initial = features.disclose_episode_features(load(owner), policy=Policy())
    candidate = owner[0]
    monkeypatch.setattr(projection, "_utc_now", lambda: SNAPSHOT_CLOCK + timedelta(seconds=5))
    monkeypatch.setattr(identity, "_utc_now", lambda: IDENTITY_CLOCK + timedelta(seconds=5))
    monkeypatch.setattr(trusted, "_utc_now", lambda: CAPTURE_CLOCK + timedelta(seconds=5))
    later = _candidate(monkeypatch, candidate.public.parent.parent, growth_score=0.2)
    # _candidate resets clocks: set the later observation explicitly again.
    monkeypatch.setattr(projection, "_utc_now", lambda: SNAPSHOT_CLOCK + timedelta(seconds=5))
    snapshot = projection.build_macro_regime_snapshot(later.source)
    monkeypatch.setattr(identity, "_utc_now", lambda: IDENTITY_CLOCK + timedelta(seconds=5))
    evidence = identity.build_current_spy_identity()
    monkeypatch.setattr(trusted, "_utc_now", lambda: CAPTURE_CLOCK + timedelta(seconds=5))
    trusted.capture_trusted_regime_context(candidate.public, candidate.private,
        snapshot=snapshot, identity_evidence=evidence, raw_source_body=later.raw_body,
        deployed_commit=DEPLOYED_COMMIT)
    assert features.disclose_episode_features(load(owner), policy=Policy()) == initial


def test_projection_bound_is_enforced(owner, monkeypatch):
    monkeypatch.setattr(features, "MAX_PROJECTION_BYTES", 128)
    with pytest.raises(features.EpisodeFeatureError, match="byte_bound"):
        load(owner)


def test_outcome_or_arbitrary_projection_arguments_are_not_inputs(owner):
    with pytest.raises(TypeError):
        load(owner, outcomes={"win": True})



def test_direct_api_actual_subject_denial_precedes_payload(owner, monkeypatch):
    _, stored, reader, generation = owner
    actual = stored.capture_receipt["subject"]["subject_id"]
    class DeniedActual(Policy):
        def check(self, action, resource):
            if resource.get("subject_id") == actual:
                raise PermissionError("actual capture subject denied")
            return super().check(action, resource)
    def forbidden(*args, **kwargs):
        pytest.fail("actual-subject payload before permission")
    monkeypatch.setattr(trusted, "_load_stored_with_feature", forbidden)
    with pytest.raises(features.EpisodeFeatureAccessError):
        load(owner, DeniedActual(), subject_id="mmsecurity_" + "f" * 64)


def test_direct_api_metadata_requires_distinct_query_bound_permission(owner, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("receipt metadata before permission")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_receipt", forbidden)
    with pytest.raises(features.EpisodeFeatureAccessError):
        load(owner, Policy({"read_retained_macro_capture_metadata"}))


@pytest.mark.parametrize("cached", [False, True])
def test_direct_api_source_receipt_rights_precede_payload_and_disclosure(owner, monkeypatch, cached):
    source = owner[1].capture_receipt["source_receipt_ids"][0]
    cap = load(owner) if cached else None
    class DeniedSource(Policy):
        def check(self, action, resource):
            if source in resource.get("source_receipt_ids", []):
                raise PermissionError("original source receipt denied")
            return super().check(action, resource)
    def forbidden(*args, **kwargs):
        pytest.fail("source-denied packet/feature read")
    monkeypatch.setattr(trusted, "_load_stored_with_feature", forbidden)
    with pytest.raises(features.EpisodeFeatureAccessError):
        if cached:
            features.disclose_episode_features(cap, policy=DeniedSource())
        else:
            load(owner, DeniedSource())


def test_direct_api_requested_subject_mismatch_refuses_before_payload(owner, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("mismatched subject payload was read")
    monkeypatch.setattr(trusted, "_load_stored_with_feature", forbidden)
    with pytest.raises(features.EpisodeFeatureSourceError, match="identity_or_allowlist_mismatch"):
        load(owner, subject_id="mmsecurity_" + "f" * 64)


def test_current_feature_policy_resource_is_original_capture_bound(owner):
    policy = Policy()
    cap = load(owner, policy)
    value = features.disclose_episode_features(cap, policy=policy, for_comparison=True)
    receipt = owner[1].capture_receipt
    for action, resource in policy.calls:
        if action in ("disclose_retained_macro_feature", "compare_retained_macro_feature"):
            assert resource["subject_id"] == receipt["subject"]["subject_id"]
            assert resource["source_receipt_ids"] == receipt["source_receipt_ids"]
            assert resource["capture_id"] == receipt["capture_id"]
            assert resource["context_id"] == receipt["context_id"]
            assert resource["packet_sha256"] == receipt["packet_sha256"]
    metadata = next(resource for action, resource in policy.calls
                    if action == "read_retained_macro_capture_metadata")
    assert "subject_id" not in metadata
    assert metadata["requested_subject_id"] == receipt["subject"]["subject_id"]
