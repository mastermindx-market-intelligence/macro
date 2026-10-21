"""Native synthetic captures exercise fitted ranking, not installed admission."""
from decimal import localcontext, Inexact, Rounded, ROUND_DOWN
import json

import pytest

from engine.neuralweb import market_memory_fitted_retrieval as retrieval
from engine.neuralweb import market_memory_fitted_normalization as fitted
from engine.neuralweb import market_memory_episode_retrieval as baseline
from engine.neuralweb import market_memory_episode_features as features
from engine.research_factory import market_memory_fitted_use as use
from tests.test_market_memory_fitted_normalization import native_training
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_retained_context_cohort import capture, owner, load, CUTOFF

METHOD = baseline.RetainedContextMethodSpec(0, 0, "historical_hypothetical")


def result(native_training, *, k=32, method=METHOD):
    population, query, window, *_ = native_training
    normalizer = fitted.fit_registered_normalizer(window, population, policy=Policy())
    cap = retrieval.retrieve_fitted_contexts(normalizer, population, query, policy=Policy(),
                                             k=k, eligibility=method)
    return cap, retrieval.disclose_fitted_retrieval(cap, policy=Policy())


def test_complete_eligible_pool_survives_baseline_top_one(native_training):
    cap, value = result(native_training)
    assert len(baseline.disclose_episode_retrieval(cap._eligibility, policy=Policy())["selected"]) == 1
    assert value["denominator"] == {"expected_captures": 3, "accounted_captures": 3,
                                     "eligible_representatives": 2, "returned": 2}
    assert [row["distance_q18"] for row in value["selected"]] == ["0.100000000000000000"] * 2
    assert [row["candidate"]["context_id"] for row in value["selected"]] == sorted(
        row["candidate"]["context_id"] for row in value["selected"])
    assert value["claims"]["normalization_parameters_fitted"]
    assert not value["claims"]["operational_study_admission"]
    assert not value["claims"]["historical_fit_existence_authenticated"]
    assert value["claims"]["effective_n"] == "not_estimated"


def test_fitted_rank_can_select_a_candidate_outside_baseline_top_one(native_training, tmp_path, monkeypatch):
    population, _, window, a, b, old_query = native_training
    normalizer = fitted.fit_registered_normalizer(window, population, policy=Policy())
    far_same_category = capture(tmp_path, monkeypatch, session="2026-08-09", growth=0.9, cycle="early")
    new_query = capture(tmp_path, monkeypatch, session="2026-08-13", growth=0.2, cycle="early")
    reader, pin = owner(tmp_path)
    new_population = load(reader, pin, new_query)
    query = features.read_episode_feature_capability(reader, pin,
        query_id=new_query.capture_receipt["query_id"], subject_id=new_query.packet["subject"]["subject_id"],
        query_cutoff=CUTOFF, policy=Policy())
    cap = retrieval.retrieve_fitted_contexts(normalizer, new_population, query, policy=Policy(),
                                             k=1, eligibility=METHOD)
    value = retrieval.disclose_fitted_retrieval(cap, policy=Policy())
    original = baseline.disclose_episode_retrieval(cap._eligibility, policy=Policy())
    assert original["selected"][0]["candidate"]["context_id"] == far_same_category.packet["context_id"]
    assert value["selected"][0]["candidate"]["context_id"] == old_query.packet["context_id"]
    assert value["denominator"]["eligible_representatives"] == 4
    assert value["selected"][0]["distance_q18"] == "0.200000000000000000"


def test_native_purge_exclusions_and_abstention_remain_authoritative(native_training, monkeypatch):
    method = baseline.RetainedContextMethodSpec(2, 0, "historical_hypothetical")
    original = native_training[2]
    body = json.loads(original._body)
    body["eligibility_method_spec"] = method.disclosure()
    window = use.TrainingWindowCapability(retrieval.cohort.canonical(body), original._selection, _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: window)
    fixture = (*native_training[:2], window, *native_training[3:])
    _, value = result(fixture, method=method)
    assert value["status"] == "ABSTAINED"
    assert value["selected"] == []
    assert sorted(row["reason"] for row in value["accounting"]) == ["query_self", "registered_purge", "registered_purge"]
    assert value["denominator"]["accounted_captures"] == 3


def test_historical_normalizer_cannot_be_presented_as_current_mode(native_training):
    with pytest.raises(retrieval.FittedRetrievalError, match="registered_fitted_mode_mismatch"):
        result(native_training, method=baseline.RetainedContextMethodSpec(0, 0, "current_contextual_support"))


def test_caller_cannot_change_registered_purge_or_embargo(native_training):
    with pytest.raises(retrieval.FittedRetrievalError, match="registered_fitted_eligibility_method"):
        result(native_training, method=baseline.RetainedContextMethodSpec(1, 0, "historical_hypothetical"))


def test_query_from_different_generation_is_rejected_before_fitted_math(native_training, tmp_path, monkeypatch):
    population, query, window, _, _, stored_query = native_training
    normalizer = fitted.fit_registered_normalizer(window, population, policy=Policy())
    capture(tmp_path, monkeypatch, session="2026-08-13", growth=0.8)
    reader, pin = owner(tmp_path)
    newer_population = load(reader, pin, stored_query)
    monkeypatch.setattr(retrieval.distance, "compare_coordinates", lambda *a: pytest.fail("mixed-owner fitted math"))
    with pytest.raises(retrieval.FittedRetrievalError, match="query_exact_fitted_population_owner"):
        retrieval.retrieve_fitted_contexts(normalizer, newer_population, query, policy=Policy(),
                                           k=1, eligibility=METHOD)


@pytest.mark.parametrize("k", [True, False, 0, -1, 33, float("nan")])
def test_invalid_count_refuses_before_any_source_or_fit_read(k):
    with pytest.raises(retrieval.FittedRetrievalError, match="finite_positive_k"):
        retrieval.retrieve_fitted_contexts(None, None, None, policy=True, k=k, eligibility=METHOD)


def test_no_unsealed_normalizer_or_result_grants_access(native_training):
    population, query, window, *_ = native_training
    cap, raw = result(native_training)
    with pytest.raises(retrieval.FittedRetrievalError):
        retrieval.disclose_fitted_retrieval(raw, policy=Policy())
    with pytest.raises(retrieval.FittedRetrievalError):
        retrieval.FittedRetrievalCapability(b"{}", cap._normalizer, cap._eligibility)
    with pytest.raises(fitted.FittedNormalizationError):
        retrieval.retrieve_fitted_contexts(json.loads(cap._normalizer._body), population, query,
                                           policy=Policy(), k=1, eligibility=METHOD)


def test_unreturned_comparison_revocation_blocks_reused_result(native_training):
    _, _, _, a, b, _ = native_training
    cap, value = result(native_training, k=1)
    selected = value["selected"][0]["candidate"]["context_id"]
    loser = b if selected == a.packet["context_id"] else a
    class DeniedLoser(Policy):
        def check(self, action, resource):
            if action == "compare_retained_macro_feature" and resource.get("query_id") == loser.capture_receipt["query_id"]:
                raise PermissionError("unreturned use revoked")
            super().check(action, resource)
    with pytest.raises(features.EpisodeFeatureAccessError):
        retrieval.disclose_fitted_retrieval(cap, policy=DeniedLoser())


def test_revocation_during_fitted_arithmetic_never_returns_result(native_training, monkeypatch):
    population, query, window, *_ = native_training
    normalizer = fitted.fit_registered_normalizer(window, population, policy=Policy())
    class Revoking(Policy):
        revoked = False
        def check(self, action, resource):
            if self.revoked and action == "compare_retained_macro_feature":
                raise PermissionError("revoked during arithmetic")
            super().check(action, resource)
    policy = Revoking()
    original = retrieval.distance.compare_coordinates
    def revoke(*args):
        value = original(*args)
        policy.revoked = True
        return value
    monkeypatch.setattr(retrieval.distance, "compare_coordinates", revoke)
    with pytest.raises(features.EpisodeFeatureAccessError):
        retrieval.retrieve_fitted_contexts(normalizer, population, query, policy=policy, k=1, eligibility=METHOD)


def test_selected_training_owner_change_revokes_existing_retrieval(native_training, monkeypatch):
    cap, _ = result(native_training)
    window = native_training[2]
    changed = use.TrainingWindowCapability(window._body, b"different-selected-owner", _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: changed)
    with pytest.raises(use.FittedUseError, match="window_changed"):
        retrieval.disclose_fitted_retrieval(cap, policy=Policy())


def test_future_append_and_hostile_decimal_leave_pinned_result_unchanged(native_training, tmp_path, monkeypatch):
    _, before = result(native_training)
    capture(tmp_path, monkeypatch, session="2026-08-21", growth=-0.99)
    with localcontext() as context:
        context.prec, context.rounding = 2, ROUND_DOWN
        context.traps[Inexact] = context.traps[Rounded] = True
        original = repr(context)
        _, after = result(native_training)
        assert repr(context) == original
    assert before == after
