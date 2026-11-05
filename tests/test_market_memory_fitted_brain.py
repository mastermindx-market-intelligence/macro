"""Genuine synthetic fitted capabilities through the bounded Brain projection.

The selected training-registration owner is the explicit existing fixture
stand-in. No installed owner, actual fit/query store, study or tool is activated.
"""
import copy
import json

import pytest

from engine.neuralweb import brain_analogues as brain
from engine.neuralweb import market_memory_episode_retrieval as baseline
from engine.neuralweb import market_memory_fitted_evidence as evidence
from engine.neuralweb import market_memory_fitted_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.research_factory import market_memory_fitted_use as use
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_fitted_evidence import fitted_selection
from tests.test_market_memory_fitted_normalization import native_training
from tests.test_market_memory_retained_context_cohort import owner


@pytest.fixture
def fitted_pair(native_training, tmp_path):
    selection, native = fitted_selection(native_training, k=2)
    reader, pin = owner(tmp_path)
    packet = evidence.build_fitted_evidence_packet(selection, reader, pin, policy=Policy())
    return selection, packet, native


def test_genuine_fitted_projection_preserves_native_identity_and_exact_source(fitted_pair):
    selection, packet, native = fitted_pair
    policy = Policy()
    assert not hasattr(policy, "disclosure")
    value = brain.get_fitted_retained_market_context(selection, packet, policy=policy)
    original = evidence.disclose_fitted_evidence_packet(packet, policy=policy)
    assert value["schema"] == "brain.retained_fitted_market_context.v2"
    assert value["available"] is True and value["status"] == "MATCHES"
    for key in ("query", "method", "index_id", "index_content_sha256", "membership_sha256",
                "selection_sha256", "retrieval_id", "denominator", "coverage"):
        assert value[key] == native[key]
    assert value["owner"] == native["query_owner"]
    assert value["neighbors"] == original["selected"]
    assert value["source_cards"] == original["source_cards"]
    assert value["state_differences"] == original["state_differences"]
    assert value["selection_claims"] == native["claims"]
    assert all(flag is False for flag in value["claims"].values())
    assert value["selection_claims"]["normalization_parameters_fitted"] is True
    assert value["selection_claims"]["historical_fit_existence_authenticated"] is False
    assert value["selection_claims"]["operational_study_admission"] is False
    assert sum(value["exclusion_counts"].values()) == len(native["accounting"])
    assert len(cohort.canonical(value)) <= 64 * 1024
    assert value["context_id"].startswith("mmbrainfittedcontext_")


def test_different_genuine_selection_and_packet_cannot_be_joined(fitted_pair, native_training):
    selection, packet, _ = fitted_pair
    other, _ = fitted_selection(native_training, k=1)
    with pytest.raises(evidence.FittedEvidenceError, match="exact_brain_fitted_evidence_selection"):
        brain.get_fitted_retained_market_context(other, packet, policy=Policy())


@pytest.mark.parametrize("serialized", ["selection", "packet"])
def test_serialized_results_are_not_capabilities(fitted_pair, serialized):
    selection, packet, native = fitted_pair
    if serialized == "selection":
        selection = native
    else:
        packet = evidence.disclose_fitted_evidence_packet(packet, policy=Policy())
    with pytest.raises((retrieval.FittedRetrievalError, evidence.FittedEvidenceError)):
        brain.get_fitted_retained_market_context(selection, packet, policy=Policy())


def test_brain_bound_refuses_instead_of_truncating_source_cards(fitted_pair, monkeypatch):
    selection, packet, _ = fitted_pair
    monkeypatch.setattr(brain, "RETAINED_CONTEXT_MAX_BYTES", 100)
    with pytest.raises(evidence.FittedEvidenceError, match="brain_fitted_evidence_byte_bound"):
        brain.get_fitted_retained_market_context(selection, packet, policy=Policy())


def test_native_large_k_is_not_silently_reduced_for_brain(native_training, tmp_path):
    selection, _ = fitted_selection(native_training, k=9)
    reader, pin = owner(tmp_path)
    packet = evidence.build_fitted_evidence_packet(selection, reader, pin, policy=Policy())
    with pytest.raises(evidence.FittedEvidenceError, match="brain_fitted_context_limit"):
        brain.get_fitted_retained_market_context(selection, packet, policy=Policy())


def test_final_current_rights_check_prevents_mid_projection_revocation(fitted_pair, monkeypatch):
    selection, packet, _ = fitted_pair
    revoked = False

    class CurrentPolicy(Policy):
        def check(self, action, resource):
            if revoked:
                raise ValueError("source_rights_revoked")
            return super().check(action, resource)

    canonical = cohort.canonical

    def revoke_after_projection(value):
        nonlocal revoked
        body = canonical(value)
        if isinstance(value, dict) and value.get("schema") == "brain.retained_fitted_market_context.v2":
            revoked = True
        return body

    monkeypatch.setattr(cohort, "canonical", revoke_after_projection)
    with pytest.raises(ValueError, match="source_usage_not_admitted"):
        brain.get_fitted_retained_market_context(selection, packet, policy=CurrentPolicy())
    assert revoked


def test_returned_projection_is_detached(fitted_pair):
    selection, packet, _ = fitted_pair
    first = brain.get_fitted_retained_market_context(selection, packet, policy=Policy())
    expected = copy.deepcopy(first)
    first["source_cards"].clear()
    first["method"]["method_id"] = "changed"
    assert brain.get_fitted_retained_market_context(selection, packet, policy=Policy()) == expected


def test_changed_packet_order_cannot_reach_brain(fitted_pair, monkeypatch):
    selection, packet, _ = fitted_pair
    disclose = evidence.disclose_fitted_evidence_packet

    def reordered(capability, *, policy):
        value = disclose(capability, policy=policy)
        value["source_cards"] = list(reversed(value["source_cards"]))
        return value

    monkeypatch.setattr(evidence, "disclose_fitted_evidence_packet", reordered)
    with pytest.raises(evidence.FittedEvidenceError, match="ordered_brain_fitted_source_join"):
        brain.get_fitted_retained_market_context(selection, packet, policy=Policy())


def test_abstained_projection_keeps_query_evidence_without_inventing_neighbors(
        native_training, tmp_path, monkeypatch):
    # Same explicit synthetic registration-owner stand-in as the native suite.
    method = baseline.RetainedContextMethodSpec(2, 0, "historical_hypothetical")
    original_window = native_training[2]
    body = json.loads(original_window._body)
    body["eligibility_method_spec"] = method.disclosure()
    window = use.TrainingWindowCapability(cohort.canonical(body),
                                          original_window._selection, _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: window)
    fixture = (*native_training[:2], window, *native_training[3:])
    selection, native = fitted_selection(fixture, k=2, method=method)
    reader, pin = owner(tmp_path)
    packet = evidence.build_fitted_evidence_packet(selection, reader, pin, policy=Policy())
    value = brain.get_fitted_retained_market_context(selection, packet, policy=Policy())
    assert value["status"] == native["status"] == "ABSTAINED"
    assert value["reason"] == native["reason"]
    assert value["neighbors"] == [] and value["denominator"]["returned"] == 0
    assert [card["role"] for card in value["source_cards"]] == ["query"]
    assert value["exclusion_counts"] == {"query_self": 1, "registered_purge": 2}
    assert all(flag is False for flag in value["claims"].values())
