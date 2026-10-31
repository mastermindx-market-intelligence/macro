"""The baselines share genuine inert-owner eligibility, never outcome labels."""
import copy

import pytest

from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.research_factory import market_memory_e0_baselines as baselines
from tests.market_memory_e0_fixtures import Policy, capture, owner, load, CUTOFF

METHOD = retrieval.RetainedContextMethodSpec(0, 0, "historical_hypothetical")


def build_inputs(tmp_path, monkeypatch, *, masked=False):
    older = capture(tmp_path, monkeypatch, session="2026-08-10", growth=0.2)
    newer = capture(tmp_path, monkeypatch, session="2026-08-11", growth=0.8,
                    liquidity="unknown" if masked else "contracting")
    if masked:
        capture(tmp_path, monkeypatch, session="2026-08-11", growth=0.2, seconds=60)
    query = capture(tmp_path, monkeypatch, session="2026-08-12", growth=0.2)
    capture(tmp_path, monkeypatch, session="2026-08-21", growth=0.2)
    reader, pin = owner(tmp_path)
    population = load(reader, pin, query)
    feature = features.read_episode_feature_capability(reader, pin,
        query_id=query.capture_receipt["query_id"], subject_id=query.packet["subject"]["subject_id"],
        query_cutoff=CUTOFF, policy=Policy())
    return population, feature, older, newer


def result(population, query, *, method=METHOD, k=1):
    cap = baselines.build_condition_selections(population, query, policy=Policy(), k=k, method=method)
    return cap, baselines.disclose_condition_selections(cap, policy=Policy())


def test_same_population_distinct_recency_and_fixed_choices(tmp_path, monkeypatch):
    population, query, older, newer = build_inputs(tmp_path, monkeypatch)
    cap, value = result(population, query)
    no_memory, recency, fixed = value["conditions"]
    assert no_memory == {"condition": "no_memory", "selected": [], "returned": 0,
                         "status": "WITHHELD_BY_CONDITION"}
    assert recency["selected"][0]["context_id"] == newer.packet["context_id"]
    assert fixed["selected"][0]["context_id"] == older.packet["context_id"]
    assert recency["returned"] == fixed["returned"] == value["requested_k"] == 1
    original = retrieval.disclose_episode_retrieval(cap._retrieval, policy=Policy())
    assert value["fixed_selection_sha256"] == original["selection_sha256"]
    assert value["accounting"] == original["accounting"]
    assert value["denominator"] == {"expected_captures": 4, "accounted_captures": 4,
                                    "eligible_representatives": 2}
    assert "outcome" not in repr(value["conditions"])
    assert not value["evaluation_performed"] and not value["operational_admission"]
    assert value["independent_episode_count"] == "not_established"
    assert "not_isolated_condition_cost" in value["cost_scope"]


def test_revision_and_missing_coordinates_never_expand_recency_population(tmp_path, monkeypatch):
    population, query, older, newer = build_inputs(tmp_path, monkeypatch, masked=True)
    _, value = result(population, query, k=8)
    assert value["denominator"]["expected_captures"] == 5
    assert value["denominator"]["eligible_representatives"] == 1
    for condition in value["conditions"][1:]:
        assert [ref["context_id"] for ref in condition["selected"]] == [older.packet["context_id"]]
    assert {r["reason"] for r in value["accounting"]} == {
        "numerically_eligible", "registered_coordinates_unavailable", "revision_sibling",
        "query_self", "future_capture"}


def test_registered_purge_applies_before_both_selections_and_empty_is_not_success(tmp_path, monkeypatch):
    population, query, *_ = build_inputs(tmp_path, monkeypatch)
    _, value = result(population, query, method=retrieval.RetainedContextMethodSpec(2, 0, METHOD.mode))
    assert value["denominator"]["eligible_representatives"] == 0
    assert all(c["status"] == "ABSTAINED" and c["selected"] == [] for c in value["conditions"][1:])
    assert value["conditions"][0]["status"] == "WITHHELD_BY_CONDITION"


def test_detached_reproducible_and_future_append_preserves_original(tmp_path, monkeypatch):
    population, query, *_ = build_inputs(tmp_path, monkeypatch)
    cap, before = result(population, query)
    changed = copy.deepcopy(before)
    changed["conditions"][1]["selected"].clear()
    assert baselines.disclose_condition_selections(cap, policy=Policy()) == before
    capture(tmp_path, monkeypatch, session="2026-08-22", growth=0.2)
    _, after = result(population, query)
    assert before == after
    with pytest.raises(baselines.E0BaselineError, match="sealed_condition_selections_required"):
        baselines.disclose_condition_selections(changed, policy=Policy())
    with pytest.raises(baselines.E0BaselineError):
        baselines.E0ConditionSelections(b"{}", cap._retrieval)


def test_current_revocation_of_unreturned_candidate_blocks_all_cached_conditions(tmp_path, monkeypatch):
    population, query, older, newer = build_inputs(tmp_path, monkeypatch)
    cap, _ = result(population, query)

    class Revoked(Policy):
        def check(self, action, resource):
            if action == "compare_retained_macro_feature" and resource.get("query_id") == newer.capture_receipt["query_id"]:
                raise PermissionError("unreturned fixed-method candidate revoked")
            return super().check(action, resource)

    with pytest.raises(features.EpisodeFeatureAccessError):
        baselines.disclose_condition_selections(cap, policy=Revoked())


def test_final_recheck_after_selection_and_no_outcome_interface(tmp_path, monkeypatch):
    population, query, *_ = build_inputs(tmp_path, monkeypatch)
    original = baselines.E0ConditionSelections.__init__

    class Revoking(Policy):
        revoked = False
        def check(self, action, resource):
            if self.revoked and action == "compare_retained_macro_feature":
                raise PermissionError("revoked after selection")
            return super().check(action, resource)

    policy = Revoking()

    def revoke(self, *args, **kwargs):
        original(self, *args, **kwargs)
        policy.revoked = True

    monkeypatch.setattr(baselines.E0ConditionSelections, "__init__", revoke)
    with pytest.raises(features.EpisodeFeatureAccessError):
        baselines.build_condition_selections(population, query, policy=policy, k=1, method=METHOD)
    with pytest.raises(TypeError):
        baselines.build_condition_selections(population, query, policy=Policy(), k=1, method=METHOD, outcomes=[])


@pytest.mark.parametrize("k", [True, 0, 9, 32, 33])
def test_invalid_budget_refuses_before_population_access(k):
    with pytest.raises(baselines.E0BaselineError, match="e0_task_k_bound"):
        baselines.build_condition_selections(None, None, policy=None, k=k, method=METHOD)


def test_budget_matches_existing_e0_tasks_and_accounting():
    import json
    from pathlib import Path
    from engine.research_factory.market_memory_evidence_accounting import MAX_RETRIEVED_PER_OBSERVATION
    schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/market_memory/e0_tasks.v1.schema.json").read_bytes())
    assert baselines.MAX_K == MAX_RETRIEVED_PER_OBSERVATION == schema["properties"]["tasks"]["items"]["properties"]["k"]["maximum"]
