"""Parent-owned contract discriminators; all examples are synthetic."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from engine.research_factory.market_memory_evidence_accounting import (
    EvidenceAccountingError,
    summarize_evidence_accounting,
)


def sample():
    return {
        "schema": "market_memory.evidence_accounting_input.v1",
        "conditions": ["no_memory", "recency", "fixed_l1"],
        "tasks": [{"task_id": "t1", "cluster_id": "a", "answerability": "answerable",
                   "required_facet_ids": ["f1"], "k": 1}],
        "observations": [{"task_id": "t1", "condition": "fixed_l1", "state": "abstained",
                          "answer_assessment": "not_applicable", "claims": [],
                          "retrieved": [{"item_id": "e1", "relevance": 2, "facet_ids": ["f1"]}]}],
    }


def test_abstention_can_retain_evidence_without_making_a_claim():
    result = summarize_evidence_accounting(sample())
    cell = result["per_task"][0]["conditions"]["fixed_l1"]
    assert cell["coverage"]["value"] == 1
    assert cell["retrieval_precision"]["value"] == 1
    assert cell["ledger_cell"] == "answerable_abstained"
    assert result["per_condition"]["fixed_l1"]["support"]["support_precision"]["value"] is None


def test_facet_from_another_task_is_not_a_valid_reference():
    value = sample()
    value["observations"][0].update(state="answered", answer_assessment="unresolved")
    other = deepcopy(value["tasks"][0])
    other.update(task_id="t2", required_facet_ids=["foreign"])
    value["tasks"].append(other)
    value["observations"][0]["retrieved"][0]["facet_ids"] = ["foreign"]
    with pytest.raises(EvidenceAccountingError):
        summarize_evidence_accounting(value)


@pytest.mark.parametrize("location", ["object_key", "condition"])
def test_string_subclasses_are_not_native_json_input(location):
    class ForeignString(str):
        pass

    value = sample()
    value["observations"] = []
    if location == "object_key":
        value[ForeignString("schema")] = value.pop("schema")
    else:
        value["conditions"][0] = ForeignString("no_memory")
    with pytest.raises(EvidenceAccountingError):
        summarize_evidence_accounting(value)


def test_unregistered_contradiction_recall_is_explicit():
    value = sample()
    value["observations"] = []
    result = summarize_evidence_accounting(value)
    for condition in value["conditions"]:
        recall = result["per_condition"][condition]["contradiction_recall"]
        assert recall == {"value": None, "status": "NOT_REGISTERED"}


def test_cluster_point_preserves_the_exact_signed_fraction():
    value = sample()
    value["observations"] = []
    for condition, facets in [("recency", []), ("fixed_l1", ["f1"])]:
        value["observations"].append({"task_id": "t1", "condition": condition,
            "state": "answered", "answer_assessment": "correct", "claims": [],
            "retrieved": [{"item_id": "x", "relevance": 2, "facet_ids": facets}]})
    cluster = summarize_evidence_accounting(value)["paired_coverage_contrast"]["cluster_mean_difference"]
    assert (cluster["numerator"], cluster["denominator"], cluster["value"]) == (1, 1, 1.0)


def test_frozen_parent_oracle_preserves_missingness_and_signed_cluster_weighting():
    root = Path(__file__).parent / "fixtures" / "market_memory_evidence_accounting"
    raw = (root / "synthetic_parent_input.json").read_bytes()
    oracle = json.loads((root / "synthetic_parent_oracle.json").read_text())
    assert hashlib.sha256(raw).hexdigest() == oracle["input_sha256"]
    assert oracle["worker_return_consumed"] is False
    expected = oracle["expected"]
    result = summarize_evidence_accounting(json.loads(raw))
    assert result["task_count"] == expected["registered_tasks"]
    for condition, counters in {
        "no_memory": ["answerable_abstained"],
        "recency": ["answerable_answered_correct", "answerable_answered_incorrect", "missing"],
        "fixed_l1": ["answerable_answered_correct", "answerable_answered_incorrect",
                     "answerable_answered_unresolved", "missing"],
    }.items():
        ledger = result["per_condition"][condition]["task_ledger"]
        assert ledger["sum"] == ledger["total_task_count"] == expected["cells_per_condition"]
        for counter in counters:
            assert ledger[counter] == expected[condition + "_" + counter]
    support = result["per_condition"]["fixed_l1"]["support"]
    claims = support["material_claims"]
    assert claims["total"] == expected["fixed_l1_material_denominator"]
    assert claims["supported"] == expected["fixed_l1_supported"]
    assert claims["unresolved"] + claims["attributed_inference"] == expected["fixed_l1_unresolved_or_attributed"]
    assert support["support_precision"]["value"] is expected["fixed_l1_support_precision"]
    for bound in ("lower", "upper"):
        ratio = support["identification_bounds"][bound]
        assert [ratio["numerator"], ratio["denominator"]] == expected["fixed_l1_identification_" + bound]
    assert result["critical_claim_count"] == expected["global_critical_claim_count"]
    assert result["per_condition"]["recency"]["support"]["critical_claim_count"] == 1
    paired = result["paired_coverage_contrast"]
    assert paired["total_task_count"] == expected["paired_total_tasks"]
    assert paired["included_task_ids"] == expected["paired_included"]
    assert [x["task_id"] for x in paired["excluded_tasks"]] == expected["paired_excluded"]
    for row in paired["per_task_differences"]:
        ratio = row["signed_difference"]
        assert [ratio["numerator"], ratio["denominator"]] == expected["signed_" + row["task_id"] + "_gain"]
    for key, name in [("mean_paired_difference", "observed_pair_only_mean"),
                      ("cluster_mean_difference", "cluster_equal_weight_descriptive_mean")]:
        ratio = paired[key]
        assert [ratio["numerator"], ratio["denominator"]] == expected[name]
    assert paired["cluster_mean_difference"]["cluster_count"] == expected["cluster_count"]
    assert result["operational_admission"] is False
    assert result["statistical_inference"]["confidence_intervals"] is None
    assert result["statistical_inference"]["effective_n"] is None
