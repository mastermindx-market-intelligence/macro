"""Exact-index composition on the genuine synthetic retained owners."""
import copy
from hashlib import sha256

import pytest

from engine.neuralweb import market_memory_exact_index as index
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from tests.test_market_memory_episode_retrieval import corpus, result, METHOD
from tests.test_market_memory_retained_context_cohort import capture, owner, load, CUTOFF
from tests.test_market_memory_episode_features import Policy


def test_index_binds_complete_native_manifest_features_and_frozen_baseline(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    cap = index.build_exact_retained_index(population, policy=Policy())
    value = index.disclose_exact_retained_index(cap, policy=Policy())
    native = cohort.disclose_retained_context_cohort(population, policy=Policy())
    assert value["manifest_sha256"] == sha256(population._body).hexdigest()
    assert value["membership_sha256"] == native["membership_sha256"]
    assert value["expected_capture_count"] == len(value["inventory"]) == 3
    assert [r["context_id"] for r in value["inventory"]] == [r["context_id"] for r in native["rows"]]
    assert value["normalizer"] == features.fixed_comparison_descriptor()
    assert value["fit_artifact_ref"] is None
    assert value["fit_status"] == "not_performed"
    assert value["historical_index_existence_authenticated"] is False
    assert value["training_eligible"] is value["operational_admission"] is False
    assert set(value["source_refs"]) == {"features", "comparison", "cohort", "retrieval"}
    assert value == index.disclose_exact_retained_index(
        index.build_exact_retained_index(population, policy=Policy()), policy=Policy())


def test_actual_native_retrieval_and_byte_reproduction(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    cap = index.build_exact_retained_index(population, policy=Policy())
    expected, original = result(population, query)
    actual = index.retrieve_exact_retained_index(cap, query, policy=Policy(), k=32, method=METHOD)
    assert type(actual) is retrieval.EpisodeRetrievalCapability
    assert retrieval.disclose_episode_retrieval(actual, policy=Policy()) == original
    proof = index.reproduce_exact_retained_retrieval(cap, query, expected, policy=Policy(), method=METHOD)
    assert proof["byte_exact_reproduction"] is True
    assert proof["selection_sha256"] == original["selection_sha256"]
    assert proof["denominator"] == original["denominator"]
    assert proof["result_sha256"] == sha256(cohort.canonical(original)).hexdigest()
    assert proof["evaluation_acceptance"] is proof["operational_admission"] is False
    proof["denominator"]["returned"] = 999
    assert index.reproduce_exact_retained_retrieval(cap, query, expected,
        policy=Policy(), method=METHOD)["denominator"]["returned"] == 2


@pytest.mark.parametrize("action", ["disclose_retained_macro_cohort", "verify_retained_macro_retention",
    "use_retained_house_output_cohort_for_contextual_comparison", "disclose_retained_macro_feature"])
def test_current_rights_apply_to_index_disclosure(tmp_path, monkeypatch, action):
    population, *_ = corpus(tmp_path, monkeypatch)
    cap = index.build_exact_retained_index(population, policy=Policy())
    with pytest.raises((cohort.RetainedContextAccessError, features.EpisodeFeatureAccessError)):
        index.disclose_exact_retained_index(cap, policy=Policy({action}))


def test_unreturned_capture_revocation_precedes_native_retrieval(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    cap = index.build_exact_retained_index(population, policy=Policy())
    _, selected = result(population, query, k=1)
    victim = next(r["capture_id"] for r in cohort.disclose_retained_context_cohort(population,
        policy=Policy())["rows"] if r["capture_id"] != selected["selected"][0]["candidate"]["capture_id"])
    class Revoked(Policy):
        def check(self, action, resource):
            if action == "disclose_retained_macro_capture" and resource.get("capture_id") == victim:
                raise PermissionError("revoked unreturned capture")
            return super().check(action, resource)
    monkeypatch.setattr(retrieval, "retrieve_retained_contexts", lambda *a, **k: pytest.fail("retrieval after revocation"))
    with pytest.raises(cohort.RetainedContextAccessError):
        index.retrieve_exact_retained_index(cap, query, policy=Revoked(), k=1, method=METHOD)


def test_final_rights_recheck_after_retrieval(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    cap = index.build_exact_retained_index(population, policy=Policy())
    class Revoking(Policy):
        revoked = False
        def check(self, action, resource):
            if self.revoked and action == "verify_retained_macro_retention":
                raise PermissionError("revoked")
            return super().check(action, resource)
    policy = Revoking()
    native = retrieval.retrieve_retained_contexts
    def revoke(*args, **kwargs):
        value = native(*args, **kwargs)
        policy.revoked = True
        return value
    monkeypatch.setattr(retrieval, "retrieve_retained_contexts", revoke)
    with pytest.raises(cohort.RetainedContextAccessError):
        index.retrieve_exact_retained_index(cap, query, policy=policy, k=1, method=METHOD)


def test_plain_json_and_public_constructor_are_not_index_capabilities(tmp_path, monkeypatch):
    population, *_ = corpus(tmp_path, monkeypatch)
    cap = index.build_exact_retained_index(population, policy=Policy())
    value = index.disclose_exact_retained_index(cap, policy=Policy())
    with pytest.raises(index.ExactIndexError, match="owner_verified"):
        index.disclose_exact_retained_index(value, policy=Policy())
    with pytest.raises(index.ExactIndexError, match="owner_verified"):
        index.ExactRetainedIndexCapability(b"{}", population)
    value["inventory"] = []
    altered = copy.copy(cap)
    body = cohort.canonical(value)
    object.__setattr__(altered, "_body", body)
    object.__setattr__(altered, "_digest", sha256(body).hexdigest())
    with pytest.raises(index.ExactIndexError, match="original_exact_index_changed"):
        index.disclose_exact_retained_index(altered, policy=Policy())


def test_reproduction_rejects_raw_result_and_changed_registered_method(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    cap = index.build_exact_retained_index(population, policy=Policy())
    expected, raw = result(population, query)
    with pytest.raises(retrieval.EpisodeRetrievalError):
        index.reproduce_exact_retained_retrieval(cap, query, raw, policy=Policy(), method=METHOD)
    with pytest.raises(index.ExactIndexError, match="owner_or_method_mismatch"):
        index.reproduce_exact_retained_retrieval(cap, query, expected, policy=Policy(),
            method=retrieval.RetainedContextMethodSpec(1, 0, "historical_hypothetical"))


def test_post_cutoff_append_preserves_original_index_and_reproduction(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    cap = index.build_exact_retained_index(population, policy=Policy())
    before = index.disclose_exact_retained_index(cap, policy=Policy())
    expected, _ = result(population, query)
    proof = index.reproduce_exact_retained_retrieval(cap, query, expected, policy=Policy(), method=METHOD)
    capture(tmp_path, monkeypatch, session="2026-08-13", growth=-0.9)
    assert index.disclose_exact_retained_index(cap, policy=Policy()) == before
    assert index.reproduce_exact_retained_retrieval(cap, query, expected, policy=Policy(), method=METHOD) == proof


def test_exact_generation_mismatch_cannot_reproduce_prior_manifest(tmp_path, monkeypatch):
    population, query, _, _, q = corpus(tmp_path, monkeypatch)
    expected, _ = result(population, query)
    capture(tmp_path, monkeypatch, session="2026-08-13")
    reader, pin = owner(tmp_path)
    newer = load(reader, pin, q)
    cap = index.build_exact_retained_index(newer, policy=Policy())
    with pytest.raises(index.ExactIndexError, match="owner_or_method_mismatch"):
        index.reproduce_exact_retained_retrieval(cap, query, expected, policy=Policy(), method=METHOD)


def test_masked_representative_and_revision_sibling_keep_denominator(tmp_path, monkeypatch):
    capture(tmp_path, monkeypatch, liquidity="unknown")
    capture(tmp_path, monkeypatch, growth=0.5, seconds=60)
    q = capture(tmp_path, monkeypatch, session="2026-08-11")
    reader, pin = owner(tmp_path)
    population = load(reader, pin, q)
    query = features.read_episode_feature_capability(reader, pin,
        query_id=q.capture_receipt["query_id"], subject_id=q.packet["subject"]["subject_id"],
        query_cutoff=CUTOFF, policy=Policy())
    cap = index.build_exact_retained_index(population, policy=Policy())
    value = index.disclose_exact_retained_index(cap, policy=Policy())
    assert len(value["inventory"]) == 3
    assert any(row["projection_id"] is None for row in value["inventory"])
    actual = retrieval.disclose_episode_retrieval(index.retrieve_exact_retained_index(cap,
        query, policy=Policy(), k=32, method=METHOD), policy=Policy())
    assert actual["status"] == "ABSTAINED"
    assert actual["denominator"]["expected_captures"] == 3
    assert actual["denominator"]["returned"] == 0


def test_fixed_source_usage_cannot_become_training_by_indexing(tmp_path, monkeypatch):
    population, query, *_ = corpus(tmp_path, monkeypatch)
    index.build_exact_retained_index(population, policy=Policy())
    with pytest.raises(features.EpisodeFeatureAccessError, match="source_usage_not_admitted"):
        features.require_fit_admission(query, policy=Policy())


def test_index_has_an_explicit_finite_byte_bound(tmp_path, monkeypatch):
    population, *_ = corpus(tmp_path, monkeypatch)
    monkeypatch.setattr(index, "MAX_INDEX_BYTES", 1)
    with pytest.raises(index.ExactIndexError, match="byte_limit"):
        index.build_exact_retained_index(population, policy=Policy())
