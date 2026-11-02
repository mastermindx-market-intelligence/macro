"""Discriminating synthetic tests for the Market Memory descriptive accounting reducer.

All fixtures are synthetic. Assertions use hand-computed fractions. These tests
say nothing about any real study, real annotation or real data provenance.
"""

import copy
import json
import random

import pytest

from engine.research_factory.market_memory_evidence_accounting import (
    LEDGER_CELLS,
    EvidenceAccountingError,
    summarize_evidence_accounting,
)

COND = ["no_memory", "recency", "fixed_l1"]


def base(tasks=(), observations=()):
    return {
        "schema": "market_memory.evidence_accounting_input.v1",
        "conditions": list(COND),
        "tasks": list(tasks),
        "observations": list(observations),
    }


def tsk(tid, answerability="answerable", facets=("f1",), cluster=None, k=3):
    return {
        "task_id": tid,
        "cluster_id": cluster,
        "answerability": answerability,
        "required_facet_ids": list(facets),
        "k": k,
    }


def obs(tid, cond, state="answered", assessment="unresolved", claims=(), retrieved=()):
    return {
        "task_id": tid,
        "condition": cond,
        "state": state,
        "answer_assessment": assessment,
        "claims": list(claims),
        "retrieved": list(retrieved),
    }


def clm(cid, material=True, verdict="supported", critical=False):
    return {"claim_id": cid, "material": material, "verdict": verdict, "critical": critical}


def itm(iid, relevance=2, facets=()):
    return {"item_id": iid, "relevance": relevance, "facet_ids": list(facets)}


def answered_all(tid, **kw):
    return [obs(tid, c, **kw) for c in COND]


def cell(summary, tid, cond):
    return next(r for r in summary["per_task"] if r["task_id"] == tid)["conditions"][cond]


def ledger(summary, cond):
    return summary["per_condition"][cond]["task_ledger"]


# ---------------------------------------------------------------------------
# scope / framing invariants
# ---------------------------------------------------------------------------


def test_summary_frame_is_descriptive_only():
    out = summarize_evidence_accounting(base())
    assert out["schema"] == "market_memory.evidence_accounting_summary.v1"
    assert out["assessment"] == "DESCRIPTIVE_ONLY_NOT_STUDY_ACCEPTANCE"
    assert out["operational_admission"] is False
    assert out["statistical_inference"] == {
        "confidence_intervals": None,
        "effective_n": None,
        "reason": "NOT_REGISTERED",
    }
    assert out["clarifications"]["ratings_provenance"] == "CALLER_SUPPLIED_NOT_AUTHENTICATED_BY_THIS_API"
    assert "PASS" not in json.dumps(out) and "NO_GO" not in json.dumps(out)


def test_output_is_json_native():
    out = summarize_evidence_accounting(base([tsk("t1")]))
    assert json.loads(json.dumps(out)) == out


# ---------------------------------------------------------------------------
# ledger basics
# ---------------------------------------------------------------------------


def test_empty_input():
    out = summarize_evidence_accounting(base())
    assert out["task_count"] == 0
    for cond in COND:
        led = ledger(out, cond)
        assert all(led[name] == 0 for name in LEDGER_CELLS)
        assert led["sum"] == 0 and led["total_task_count"] == 0
        support = out["per_condition"][cond]["support"]
        assert support["supported_share"]["status"] == "EMPTY_DENOMINATOR"
        assert support["support_precision"]["status"] == "EMPTY_DENOMINATOR"
        assert support["identification_bounds"]["lower"]["value"] is None
    pc = out["paired_coverage_contrast"]
    assert pc["included_task_count"] == 0 and pc["total_task_count"] == 0
    assert pc["mean_paired_difference"]["status"] == "EMPTY_DENOMINATOR"
    assert pc["cluster_mean_difference"]["status"] == "EMPTY_DENOMINATOR"
    assert out["critical_claim_count"] == 0


def test_all_tasks_implicitly_missing():
    out = summarize_evidence_accounting(base([tsk("t1"), tsk("t2")]))
    assert out["task_count"] == 2
    for cond in COND:
        led = ledger(out, cond)
        assert led["missing"] == 2 and led["sum"] == 2
    row = cell(out, "t1", "recency")
    assert row["record_present"] is False and row["state"] == "missing"
    assert row["coverage"]["status"] == "NOT_OBSERVED"
    assert row["coverage"]["denominator"] == 1
    assert row["omission_count"] is None
    assert row["retrieval_precision"]["status"] == "NOT_OBSERVED"


def test_explicit_missing_keeps_record_present_true():
    tasks = [tsk("a"), tsk("b")]
    obss = [obs("a", c, state="missing", assessment="not_applicable") for c in COND]
    out = summarize_evidence_accounting(base(tasks, obss))
    for cond in COND:
        assert ledger(out, cond)["missing"] == 2
    assert cell(out, "a", "recency")["record_present"] is True
    assert cell(out, "b", "recency")["record_present"] is False


def test_answerable_incorrect_partition():
    obss = answered_all("t1", assessment="incorrect")
    out = summarize_evidence_accounting(base([tsk("t1")], obss))
    for cond in COND:
        led = ledger(out, cond)
        assert led["answerable_answered_incorrect"] == 1
        assert led["sum"] == 1 == led["total_task_count"]
        assert set(LEDGER_CELLS) <= set(led), "no ledger cell may silently disappear"


def test_correct_incorrect_unresolved_counters():
    tasks = [tsk("c"), tsk("w"), tsk("u")]
    obss = (
        answered_all("c", assessment="correct")
        + answered_all("w", assessment="incorrect")
        + answered_all("u", assessment="unresolved")
    )
    out = summarize_evidence_accounting(base(tasks, obss))
    led = ledger(out, "fixed_l1")
    assert led["answerable_answered_correct"] == 1
    assert led["answerable_answered_incorrect"] == 1
    assert led["answerable_answered_unresolved"] == 1
    assert led["sum"] == 3


def test_unanswerable_asserted_and_correct_rejected():
    obss = answered_all("t1", assessment="incorrect")
    out = summarize_evidence_accounting(base([tsk("t1", answerability="unanswerable")], obss))
    assert ledger(out, "recency")["unanswerable_asserted"] == 1
    bad = base([tsk("t1", answerability="unanswerable")], answered_all("t1", assessment="correct"))
    with pytest.raises(EvidenceAccountingError):
        summarize_evidence_accounting(bad)


def test_unknown_answerability_cells():
    tasks = [tsk("u", answerability="unknown"), tsq := tsk("a", answerability="unknown")]
    obss = answered_all("u", assessment="unresolved") + [
        obs("a", c, state="abstained", assessment="not_applicable") for c in COND
    ]
    out = summarize_evidence_accounting(base(tasks, obss))
    led = ledger(out, "no_memory")
    assert led["unknown_answerability_answered"] == 1
    assert led["unknown_answerability_abstained"] == 1
    assert led["sum"] == 2
    for assessment in ("correct", "incorrect"):
        bad = base([tsk("u", answerability="unknown")], answered_all("u", assessment=assessment))
        with pytest.raises(EvidenceAccountingError):
            summarize_evidence_accounting(bad)


# ---------------------------------------------------------------------------
# support accounting
# ---------------------------------------------------------------------------


def test_full_denominator_with_unresolved_and_inference():
    claims = [
        clm("c1", verdict="supported"),
        clm("c2", verdict="supported"),
        clm("c3", verdict="unresolved"),
        clm("c4", verdict="attributed_inference"),
    ]
    obss = [obs("t1", c, assessment="unresolved", claims=claims) for c in COND]
    out = summarize_evidence_accounting(base([tsk("t1", facets=())], obss))
    support = out["per_condition"]["fixed_l1"]["support"]
    mat = support["material_claims"]
    assert mat["total"] == 4 and mat["supported"] == 2
    assert mat["unresolved"] == 1 and mat["attributed_inference"] == 1
    share = support["supported_share"]
    assert (share["numerator"], share["denominator"]) == (2, 4)
    assert share["value"] == 0.5 and share["status"] == "OK"
    precision = support["support_precision"]
    assert precision["value"] is None
    assert precision["status"] == "UNRESOLVED_MATERIAL_CLAIMS"
    bounds = support["identification_bounds"]
    assert (bounds["lower"]["numerator"], bounds["lower"]["denominator"]) == (2, 4)
    assert (bounds["upper"]["numerator"], bounds["upper"]["denominator"]) == (4, 4)
    assert bounds["upper"]["value"] == 1.0
    assert bounds["interpretation"] == "DESCRIPTIVE_BOUNDS_NOT_CONFIDENCE_INTERVALS"


def test_empty_material_claims_are_unmeasurable():
    obss = [obs("t1", c, assessment="unresolved", claims=[]) for c in COND]
    out = summarize_evidence_accounting(base([tsk("t1", facets=())], obss))
    support = out["per_condition"]["fixed_l1"]["support"]
    assert support["material_claims"]["total"] == 0
    assert support["supported_share"]["status"] == "EMPTY_DENOMINATOR"
    assert support["supported_share"]["value"] is None
    assert support["identification_bounds"]["lower"]["value"] is None
    assert support["identification_bounds"]["upper"]["value"] is None


def test_nonmaterial_claims_counted_separately():
    claims = [clm("m1", verdict="supported"), clm("n1", False, "contradicted"), clm("n2", False, "unsupported")]
    obss = [obs("t1", c, assessment="unresolved", claims=claims) for c in COND]
    out = summarize_evidence_accounting(base([tsk("t1", facets=())], obss))
    support = out["per_condition"]["fixed_l1"]["support"]
    assert support["material_claims"]["total"] == 1
    assert support["material_claims"]["verdict_counts"]["supported"] == 1
    assert support["nonmaterial_claims"]["total"] == 2
    assert support["nonmaterial_claims"]["verdict_counts"]["contradicted"] == 1
    assert support["supported_share"]["value"] == 1.0
    assert support["support_precision"]["status"] == "OK"


def test_critical_claims_preserved_globally_and_per_condition():
    claims = [clm("k1", verdict="contradicted", critical=True), clm("p1", verdict="supported")]
    obss = [obs("t1", c, assessment="unresolved", claims=claims) for c in COND]
    out = summarize_evidence_accounting(base([tsk("t1", facets=())], obss))
    assert out["critical_claim_count"] == 3
    assert out["per_condition"]["fixed_l1"]["support"]["critical_claim_count"] == 1
    row = cell(out, "t1", "fixed_l1")
    assert row["claim_counts"]["critical"] == 1
    mat = out["per_condition"]["fixed_l1"]["support"]["material_claims"]
    assert mat["verdict_counts"]["contradicted"] == 1
    assert mat["supported"] == 1 and mat["total"] == 2


# ---------------------------------------------------------------------------
# retrieval accounting
# ---------------------------------------------------------------------------


def test_facet_union_dedup_across_items():
    retrieved = [itm("i1", 2, ["f1"]), itm("i2", 2, ["f1", "f2"])]
    obss = [obs("t1", c, retrieved=retrieved) for c in COND]
    out = summarize_evidence_accounting(base([tsk("t1", facets=["f1", "f2"])], obss))
    cov = cell(out, "t1", "fixed_l1")["coverage"]
    assert (cov["numerator"], cov["denominator"]) == (2, 2)
    assert cov["value"] == 1.0
    assert cell(out, "t1", "fixed_l1")["omission_count"] == 0


def test_zero_return_vs_all_irrelevant_precision():
    zero = [obs("tz", c, retrieved=[]) for c in COND]
    out = summarize_evidence_accounting(base([tsk("tz")], zero))
    row = cell(out, "tz", "recency")
    assert row["coverage"]["value"] == 0.0 and row["coverage"]["status"] == "OK"
    assert row["retrieval_precision"]["status"] == "EMPTY_DENOMINATOR"
    assert row["retrieval_precision"]["value"] is None
    assert row["omission_count"] == 1

    retrieved = [itm("i1", 0, ["f1"]), itm("i2", 1, ["f1"])]
    irr = [obs("ti", c, retrieved=retrieved) for c in COND]
    out = summarize_evidence_accounting(base([tsk("ti")], irr))
    row = cell(out, "ti", "recency")
    assert row["coverage"]["value"] == 0.0
    prec = row["retrieval_precision"]
    assert (prec["numerator"], prec["denominator"]) == (0, 2)
    assert prec["value"] == 0.0
    assert row["omission_count"] == 1
    assert row["relevance_2_item_count"] == 0


def test_ordinal_relevance_1_does_not_cover():
    obss = [obs("t1", c, retrieved=[itm("i1", 1, ["f1"])]) for c in COND]
    out = summarize_evidence_accounting(base([tsk("t1")], obss))
    cov = cell(out, "t1", "fixed_l1")["coverage"]
    assert (cov["numerator"], cov["denominator"]) == (0, 1)
    assert cell(out, "t1", "fixed_l1")["relevance_2_item_count"] == 0


def test_unobserved_states_do_not_fill_zero_performance():
    tasks = [tsk("t1", facets=["f1", "f2"])]
    obss = [
        obs("t1", "no_memory", state="source_unavailable", assessment="not_applicable"),
        obs("t1", "recency", state="pending", assessment="not_applicable"),
        obs("t1", "fixed_l1", state="censored", assessment="not_applicable"),
    ]
    out = summarize_evidence_accounting(base(tasks, obss))
    row = cell(out, "t1", "no_memory")
    assert row["coverage"]["status"] == "NOT_OBSERVED"
    assert row["coverage"]["numerator"] is None
    assert row["coverage"]["denominator"] == 2, "registered facet denominator preserved"
    assert row["omission_count"] is None
    assert ledger(out, "no_memory")["source_unavailable"] == 1
    assert ledger(out, "recency")["pending"] == 1
    assert ledger(out, "fixed_l1")["censored"] == 1


def test_empty_required_facets_give_empty_denominator_coverage():
    obss = [obs("t1", c, retrieved=[itm("i1", 2, [])]) for c in COND]
    out = summarize_evidence_accounting(base([tsk("t1", facets=())], obss))
    row = cell(out, "t1", "fixed_l1")
    assert row["coverage"]["status"] == "EMPTY_DENOMINATOR"
    assert row["omission_count"] is None


# ---------------------------------------------------------------------------
# paired contrast
# ---------------------------------------------------------------------------


def test_negative_signed_gain_is_not_abs():
    tasks = [tsk("t1", facets=["f1", "f2"])]
    obss = (
        [obs("t1", "no_memory", retrieved=[])]
        + [obs("t1", "recency", retrieved=[itm("r1", 2, ["f1"])])]
        + [obs("t1", "fixed_l1", retrieved=[itm("x1", 2, [])])]
    )
    out = summarize_evidence_accounting(base(tasks, obss))
    pc = out["paired_coverage_contrast"]
    assert pc["included_task_ids"] == ["t1"]
    diff = pc["per_task_differences"][0]["signed_difference"]
    assert (diff["numerator"], diff["denominator"]) == (-1, 2)
    assert diff["value"] == -0.5
    assert pc["mean_paired_difference"]["numerator"] == -1
    assert pc["mean_paired_difference"]["value"] == -0.5


def test_paired_missing_exclusion_preserves_counts():
    tasks = [tsk("a", facets=["f1"]), tsk("b", facets=["f1"])]
    obss = (
        [obs("a", c, retrieved=[itm("a1", 2, ["f1"])]) for c in COND]
        + [obs("b", "no_memory", retrieved=[])]
        + [obs("b", "fixed_l1", retrieved=[])]
    )
    out = summarize_evidence_accounting(base(tasks, obss))
    pc = out["paired_coverage_contrast"]
    assert pc["total_task_count"] == 2 and pc["included_task_count"] == 1
    assert pc["included_task_ids"] == ["a"]
    assert pc["excluded_tasks"] == [
        {"task_id": "b", "fixed_l1_status": "OK", "recency_status": "NOT_OBSERVED"}
    ]
    assert ledger(out, "recency")["missing"] == 1
    assert ledger(out, "recency")["sum"] == 2
    assert pc["included_vs_total"] == {"included": 1, "total": 2}


def test_single_cluster_mean_matches_mean_difference():
    tasks = [tsk("a", facets=["f1"], cluster="c1"), tsk("b", facets=["f1"], cluster="c1")]
    obss = (
        [obs("a", "recency", retrieved=[]), obs("a", "fixed_l1", retrieved=[itm("a1", 2, ["f1"])])]
        + [obs("b", "recency", retrieved=[]), obs("b", "fixed_l1", retrieved=[])]
        + [obs(x, "no_memory", retrieved=[]) for x in ("a", "b")]
    )
    out = summarize_evidence_accounting(base(tasks, obss))
    pc = out["paired_coverage_contrast"]
    cm = pc["cluster_mean_difference"]
    assert cm["status"] == "OK" and cm["cluster_count"] == 1
    assert cm["value"] == 0.5
    assert cm["per_cluster_means"][0]["cluster_id"] == "c1"
    assert cm["per_cluster_means"][0]["task_count"] == 2
    mean = pc["mean_paired_difference"]
    assert (mean["numerator"], mean["denominator"]) == (1, 2)
    assert cm["value"] == mean["value"]


def test_multiple_clusters_are_equal_weighted_not_pooled():
    tasks = [tsk("a", facets=["f1"], cluster="c1"), tsk("b", facets=["f1"], cluster="c2")]
    obss = (
        [obs("a", "recency", retrieved=[]), obs("a", "fixed_l1", retrieved=[itm("a1", 2, ["f1"])])]
        + [obs("b", "recency", retrieved=[itm("b1", 2, ["f1"])]), obs("b", "fixed_l1", retrieved=[])]
        + [obs(x, "no_memory", retrieved=[]) for x in ("a", "b")]
    )
    out = summarize_evidence_accounting(base(tasks, obss))
    pc = out["paired_coverage_contrast"]
    cm = pc["cluster_mean_difference"]
    assert cm["cluster_count"] == 2 and cm["status"] == "OK"
    assert cm["value"] == 0.0, "mean of (+1, -1) is 0, not a pooled 0/2"
    assert pc["mean_paired_difference"]["numerator"] == 0


def test_unknown_cluster_membership_blocks_cluster_mean_only():
    tasks = [tsk("a", facets=["f1"], cluster=None)]
    obss = (
        [obs("a", "recency", retrieved=[]), obs("a", "fixed_l1", retrieved=[itm("a1", 2, ["f1"])])]
        + [obs("a", "no_memory", retrieved=[])]
    )
    out = summarize_evidence_accounting(base(tasks, obss))
    pc = out["paired_coverage_contrast"]
    cm = pc["cluster_mean_difference"]
    assert cm["status"] == "UNKNOWN_CLUSTER_MEMBERSHIP"
    assert cm["value"] is None and cm["cluster_count"] is None
    assert pc["mean_paired_difference"]["value"] == 1.0


# ---------------------------------------------------------------------------
# rejection cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["tasks"][0].update(k=0),
        lambda d: d["tasks"][0].update(k=9),
        lambda d: d["tasks"][0].update(k=True),
        lambda d: d["tasks"][0].update(k=2.0),
        lambda d: d["tasks"].append(d["tasks"][0]),
        lambda d: d["observations"].append(dict(d["observations"][0])),
        lambda d: d["tasks"][0].__setitem__("extra", 1),
        lambda d: d.update(extra=1),
        lambda d: d.update(schema="wrong.schema"),
        lambda d: d.update(conditions=["recency", "fixed_l1", "no_memory"]),
        lambda d: d["observations"][0].update(condition="other"),
        lambda d: d["observations"][0].update(task_id="ghost"),
        lambda d: (d["observations"][0].update(answer_assessment="not_applicable")),
        lambda d: d["observations"][0].update(state="abstained"),
        lambda d: d["observations"][0].update(state="abstained", answer_assessment="not_applicable", claims=[clm("x")]),
        lambda d: d["observations"][0].update(state="abstained", answer_assessment="not_applicable", retrieved=[itm("x1", 2, ["f1"])]),
        lambda d: d["observations"][0]["claims"].append(clm("c1")),
        lambda d: d["observations"][0]["retrieved"].append(itm("i1", 0, [])),
        lambda d: d["observations"][0]["retrieved"][0].update(facet_ids=["ghost_facet"]),
        lambda d: d["tasks"][0].update(required_facet_ids=["f1", 2]),
        lambda d: d["observations"][0]["claims"].append(clm("bad_crit", critical=True, material=False)),
        lambda d: d["tasks"].insert(0, tuple(d["tasks"][0].items())),
        lambda d: d["tasks"][0].update(required_facet_ids=["f1", "f1"]),
        lambda d: d["tasks"][0].update(task_id=""),
        lambda d: d["tasks"][0].update(task_id="_leading"),
        lambda d: d["tasks"][0].update(task_id="has space"),
        lambda d: d["tasks"][0].update(answerability="maybe"),
        lambda d: d["observations"][0].update(state="lost"),
    ],
)
def test_rejections(mutate):
    tasks = [tsk("t1")]
    obss = [
        obs(
            "t1",
            "recency",
            assessment="unresolved",
            claims=[clm("c1")],
            retrieved=[itm("i1", 2, ["f1"])],
        )
    ]
    data = base(tasks, obss)
    mutate(data)
    with pytest.raises(EvidenceAccountingError):
        summarize_evidence_accounting(data)


def test_error_is_valueerror_and_message_is_stable():
    with pytest.raises(ValueError, match="must be a JSON object"):
        summarize_evidence_accounting(["not", "a", "dict"])
    try:
        summarize_evidence_accounting(base([tsk("_bad_leading_underscore")], []))
        raise AssertionError("expected rejection")
    except EvidenceAccountingError as exc:
        assert "_bad_leading_underscore" not in str(exc)


def test_k_bound_enforced_against_retrieved():
    obss = [obs("t1", c, retrieved=[itm("i1", 2, []), itm("i2", 2, [])]) for c in COND]
    data = base([tsk("t1", k=1)], obss)
    with pytest.raises(EvidenceAccountingError):
        summarize_evidence_accounting(data)


# ---------------------------------------------------------------------------
# purity: immutability, detachment, determinism, no IO surface
# ---------------------------------------------------------------------------


def _rich_input():
    tasks = [
        tsk("t1", facets=["f1", "f2"], cluster="c1"),
        tsk("t2", facets=["f1"], cluster=None, answerability="unanswerable", k=2),
    ]
    obss = [
        obs("t1", "recency", assessment="unresolved", claims=[clm("c1", verdict="supported")], retrieved=[itm("i1", 2, ["f1"])]),
        obs("t1", "fixed_l1", assessment="unresolved", claims=[clm("c2", verdict="attributed_inference")], retrieved=[itm("i2", 1, ["f1"])]),
        obs("t1", "no_memory", state="abstained", assessment="not_applicable", retrieved=[]),
        obs("t2", "recency", state="abstained", assessment="not_applicable"),
    ]
    return base(tasks, obss)


def test_input_immutability_output_detachment_and_determinism():
    data = _rich_input()
    snapshot = copy.deepcopy(data)
    first = summarize_evidence_accounting(data)
    assert data == snapshot, "input must not be mutated"

    poison = copy.deepcopy(first)
    poison["task_count"] = 999
    poison["per_task"].pop()
    poison["per_condition"]["recency"]["support"]["material_claims"]["total"] = -5
    second = summarize_evidence_accounting(data)
    assert second == first, "poisoning a prior output must not affect later calls"
    assert data == snapshot


def test_input_order_does_not_change_aggregate_output():
    data = _rich_input()
    reference = summarize_evidence_accounting(data)
    rng = random.Random(20261014)
    for _ in range(5):
        shuffled = copy.deepcopy(data)
        rng.shuffle(shuffled["tasks"])
        rng.shuffle(shuffled["observations"])
        assert summarize_evidence_accounting(shuffled) == reference
    ids = [row["task_id"] for row in reference["per_task"]]
    assert ids == sorted(ids)


def test_module_has_no_io_surface():
    from engine.research_factory import market_memory_evidence_accounting as mod

    for name in ("open", "socket", "urlopen", "Path", "requests", "subprocess"):
        assert not hasattr(mod, name)
