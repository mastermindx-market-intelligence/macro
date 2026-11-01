"""Exhaustive ranking and failure semantics on genuine original owner captures."""
from __future__ import annotations

import copy
from decimal import Inexact, Rounded, ROUND_DOWN, localcontext

import pytest

from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_comparison as comparison
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from tests.test_market_memory_retained_context_cohort import capture, owner, load, CUTOFF
from tests.test_market_memory_episode_features import Policy

METHOD = retrieval.RetainedContextMethodSpec(0, 0, "historical_hypothetical")


def corpus(tmp_path, monkeypatch):
    a = capture(tmp_path, monkeypatch, session="2026-08-10", growth=0.0)
    b = capture(tmp_path, monkeypatch, session="2026-08-11", growth=0.4)
    q = capture(tmp_path, monkeypatch, session="2026-08-12", growth=0.2)
    reader, pin = owner(tmp_path)
    population = load(reader, pin, q)
    query = features.read_episode_feature_capability(
        reader, pin, query_id=q.capture_receipt["query_id"],
        subject_id=q.packet["subject"]["subject_id"], query_cutoff=CUTOFF, policy=Policy())
    return population, query, a, b, q


def result(population, query, *, policy=None, method=METHOD, k=32):
    policy = Policy() if policy is None else policy
    cap = retrieval.retrieve_retained_contexts(population, query, policy=policy, k=k, method=method)
    return cap, retrieval.disclose_episode_retrieval(cap, policy=policy)


def test_exhaustive_nonempty_ranking_and_complete_denominator(tmp_path, monkeypatch):
    population, query, a, b, q = corpus(tmp_path, monkeypatch)
    _, value = result(population, query)
    assert value["status"] == "MATCHES"
    assert value["denominator"] == {"expected_captures": 3, "accounted_captures": 3,
                                    "eligible_representatives": 2, "returned": 2}
    assert [r["candidate"]["context_id"] for r in value["selected"]] == sorted(
        [a.packet["context_id"], b.packet["context_id"]])
    assert [r["distance_q18"] for r in value["selected"]] == ["0.020000000000000001"] * 2
    assert sum(row["reason"] == "query_self" for row in value["accounting"]) == 1
    assert value["claims"]["effective_n"] == "not_estimated"
    assert not value["claims"]["W2C_timely_admission"]
    assert not value["claims"]["fit_eligible"]
    assert value["method_spec"]["label_interval_coverage"] == "not_established"


def test_earliest_masked_capture_not_replaced_and_empty_is_honest(tmp_path, monkeypatch):
    capture(tmp_path, monkeypatch, liquidity="unknown")
    capture(tmp_path, monkeypatch, growth=0.5, seconds=60)
    q = capture(tmp_path, monkeypatch, session="2026-08-11")
    reader, pin = owner(tmp_path)
    population = load(reader, pin, q)
    query = features.read_episode_feature_capability(reader, pin,
        query_id=q.capture_receipt["query_id"], subject_id=q.packet["subject"]["subject_id"],
        query_cutoff=CUTOFF, policy=Policy())
    _, value = result(population, query)
    assert value["status"] == "ABSTAINED"
    assert value["denominator"]["expected_captures"] == 3
    assert sorted(row["reason"] for row in value["accounting"]) == [
        "query_self", "registered_coordinates_unavailable", "revision_sibling"]


def test_registered_purge_and_embargo_reconcile_before_selection(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    _, value = result(population, query,
                      method=retrieval.RetainedContextMethodSpec(1, 1, "current_contextual_support"))
    assert value["denominator"]["returned"] == 1
    assert sorted(row["reason"] for row in value["accounting"]) == [
        "numerically_eligible", "query_self", "registered_purge"]
    # These are registered calendar separation windows, not asserted target intervals.
    assert value["method_spec"]["label_interval_coverage"] == "not_established"


def test_disclosure_current_rights_and_final_boundary(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    cap, raw = result(population, query)
    with pytest.raises(retrieval.EpisodeRetrievalError, match="capability_required"):
        retrieval.disclose_episode_retrieval(raw, policy=Policy())
    with pytest.raises(retrieval.EpisodeRetrievalError, match="capability_required"):
        retrieval.EpisodeRetrievalCapability(b"{}", population, query, ())
    with pytest.raises(features.EpisodeFeatureAccessError):
        retrieval.disclose_episode_retrieval(cap, policy=Policy({"compare_retained_macro_feature"}))
    assert features.disclose_episode_features(query, policy=Policy({"compare_retained_macro_feature"}))
    original = comparison.compare_episode_features
    class RevokingPolicy(Policy):
        revoked = False
        def check(self, action, resource):
            if self.revoked and action == "compare_retained_macro_feature":
                raise PermissionError("revoked")
            return super().check(action, resource)
    policy = RevokingPolicy()
    def revoke_after_math(*args, **kwargs):
        record = original(*args, **kwargs)
        policy.revoked = True
        return record
    monkeypatch.setattr(comparison, "compare_episode_features", revoke_after_math)
    with pytest.raises(features.EpisodeFeatureAccessError):
        result(population, query, policy=policy)


def test_stable_selection_and_declared_arithmetic_under_hostile_context(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    _, before = result(population, query)
    with localcontext() as context:
        context.traps[Inexact] = context.traps[Rounded] = True
        context.prec = 2
        context.Emin, context.Emax, context.rounding = -2, 2, ROUND_DOWN
        hostile = copy.copy(context)
        _, after = result(population, query)
        assert repr(context) == repr(hostile)
        assert dict(context.flags) == dict(hostile.flags)
        assert dict(context.traps) == dict(hostile.traps)
    assert after == before


@pytest.mark.parametrize("k", [True, False, 0, -1, 33, float("nan")])
def test_k_is_bounded_exact_int_before_any_source_read(k):
    with pytest.raises(retrieval.EpisodeRetrievalError, match="finite_positive_k"):
        retrieval.retrieve_retained_contexts(None, None, policy=True, k=k, method=METHOD)


@pytest.mark.parametrize("days", [True, -1, 367, float("inf")])
def test_immutable_method_exclusion_parameters_fail_closed(days):
    with pytest.raises(retrieval.EpisodeRetrievalError):
        retrieval.RetainedContextMethodSpec(days, 0, "historical_hypothetical")


def test_future_append_does_not_change_original_selection(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    _, before = result(population, query)
    capture(tmp_path, monkeypatch, session="2026-08-13", growth=0.2)
    _, after = result(population, query)
    assert before["selection_sha256"] == after["selection_sha256"]
    assert before == after



def test_policy_provenance_change_does_not_change_source_membership_or_selection(tmp_path, monkeypatch):
    population, query, a, b, q = corpus(tmp_path, monkeypatch)
    _, before = result(population, query)
    class OtherPolicy(Policy):
        policy_id = "test.other_authorized_policy.v1"
    policy = OtherPolicy()
    reader, pin = owner(tmp_path)
    other_population = load(reader, pin, q, policy=policy)
    other_query = features.read_episode_feature_capability(reader, pin,
        query_id=q.capture_receipt["query_id"], subject_id=q.packet["subject"]["subject_id"],
        query_cutoff=CUTOFF, policy=policy)
    _, after = result(other_population, other_query, policy=policy)
    assert before["membership_sha256"] == after["membership_sha256"]
    assert before["selection_sha256"] == after["selection_sha256"]
    assert before["selected"][0]["comparison_id"] != after["selected"][0]["comparison_id"]


def test_revoked_unreturned_compared_candidate_blocks_cached_counts(tmp_path, monkeypatch):
    population, query, a, b, q = corpus(tmp_path, monkeypatch)
    cap, value = result(population, query, k=1)
    selected = value["selected"][0]["candidate"]["context_id"]
    loser = b if a.packet["context_id"] == selected else a
    class DeniedLoser(Policy):
        def check(self, action, resource):
            if (action == "compare_retained_macro_feature"
                    and resource.get("query_id") == loser.capture_receipt["query_id"]):
                raise PermissionError("unreturned comparison use revoked")
            return super().check(action, resource)
    with pytest.raises(features.EpisodeFeatureAccessError):
        retrieval.disclose_episode_retrieval(cap, policy=DeniedLoser())


def test_query_cutoff_mismatch_and_no_outcome_input(tmp_path, monkeypatch):
    population, query, a, b, q = corpus(tmp_path, monkeypatch)
    reader, pin = owner(tmp_path)
    later_query = features.read_episode_feature_capability(reader, pin,
        query_id=q.capture_receipt["query_id"], subject_id=q.packet["subject"]["subject_id"],
        query_cutoff="2026-08-21T12:00:00Z", policy=Policy())
    with pytest.raises(retrieval.EpisodeRetrievalError, match="cutoff_mismatch"):
        result(population, later_query)
    with pytest.raises(TypeError):
        retrieval.retrieve_retained_contexts(population, query, policy=Policy(), k=1,
                                            method=METHOD, outcomes=[])



def test_method_identity_binds_exact_source_and_refuses_changed_dependency(monkeypatch):
    from pathlib import Path
    from hashlib import sha256
    value = METHOD.disclosure()
    assert value["cohort_source_ref"]["sha256"] == sha256(Path(cohort.__file__).read_bytes()).hexdigest()
    assert value["retrieval_source_ref"]["sha256"] == sha256(Path(retrieval.__file__).read_bytes()).hexdigest()
    monkeypatch.setitem(retrieval._IMPORTED_DEPENDENCY_SHA256, "P1", "f" * 64)
    with pytest.raises(retrieval.EpisodeRetrievalError, match="dependency_source_mismatch"):
        METHOD.disclosure()



def test_registered_P1_dependency_reference_tracks_subject_permission_repair():
    from pathlib import Path
    from hashlib import sha256
    assert METHOD.disclosure()["P1_source_sha256"] == sha256(Path(features.__file__).read_bytes()).hexdigest()
