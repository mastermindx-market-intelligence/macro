"""Contract tests for the market_memory E0 critical-claim counter.

Synthetic, self-contained contract tests for
``engine.research_factory.market_memory_e0_critical_claims.score_critical_claims``.
Every fixture is built locally from the documented
``market_memory.evidence_accounting_input.v1`` shape; no repository, git or
private data is read and no real rating is inferred.  The function under test
is display-only counting, so these tests pin counts, verdict buckets,
registered denominators and always-false governance flags without requiring
any scientific acceptance verdict.
"""

import copy

import pytest

from engine.research_factory.market_memory_e0_critical_claims import (
    score_critical_claims,
)
from engine.research_factory.market_memory_evidence_accounting import EvidenceAccountingError

INPUT_SCHEMA = "market_memory.evidence_accounting_input.v1"
OUTPUT_SCHEMA = "market_memory.e0_critical_claim_counts.v1"
AUTHORITY = "display_only"
CONDITIONS = ["no_memory", "recency", "fixed_l1"]
VERDICTS = [
    "supported",
    "contradicted",
    "unsupported",
    "attributed_inference",
    "unresolved",
]
STATES = [
    "answered",
    "abstained",
    "missing",
    "source_unavailable",
    "pending",
    "censored",
]
COUNT_KEYS = [
    "all_claim_count",
    "material_claim_count",
    "critical_claim_count",
    "critical_unsupported_claim_count",
]
FLAG_NAMES = [
    "ratings_authenticated",
    "inferential_estimator_qualified",
    "acceptance_verdict_emitted",
    "operational_admission",
]
FORBIDDEN_KEYS = {
    "ci",
    "confidence_interval",
    "effective_n",
    "p_value",
    "pvalue",
    "variance",
    "acceptance_verdict",
    "pass",
    "passed",
    "financial_outcome",
    "financial_outcomes",
}


def zeros():
    """The four-claim-count block, all zero."""
    return {key: 0 for key in COUNT_KEYS}


def empty_verdict_map():
    return {verdict: [] for verdict in VERDICTS}


def cell(record_present, state, counts=None, verdict_ids=None):
    """A complete per-task cell with hand-computable defaults."""
    return {
        "record_present": record_present,
        "state": state,
        "counts": zeros() if counts is None else counts,
        "critical_claim_ids_by_verdict": (
            empty_verdict_map() if verdict_ids is None else verdict_ids
        ),
    }


def make_task(task_id, answerability="answerable", cluster_id=None, facets=(), k=3):
    return {
        "task_id": task_id,
        "cluster_id": cluster_id,
        "answerability": answerability,
        "required_facet_ids": list(facets),
        "k": k,
    }


def make_claim(claim_id, material=True, verdict="supported", critical=True):
    return {
        "claim_id": claim_id,
        "material": material,
        "verdict": verdict,
        "critical": critical,
    }


def make_item(item_id, relevance=1, facets=()):
    return {
        "item_id": item_id,
        "relevance": relevance,
        "facet_ids": list(facets),
    }


def make_observation(
    task_id,
    condition,
    state="answered",
    assessment=None,
    claims=(),
    retrieved=(),
):
    if assessment is None:
        assessment = "unresolved" if state == "answered" else "not_applicable"
    return {
        "task_id": task_id,
        "condition": condition,
        "state": state,
        "answer_assessment": assessment,
        "claims": list(claims),
        "retrieved": list(retrieved),
    }


def make_input(tasks=(), observations=()):
    return {
        "schema": INPUT_SCHEMA,
        "conditions": list(CONDITIONS),
        "tasks": list(tasks),
        "observations": list(observations),
    }


def as_indexed(entries, key):
    """Accept either a mapping keyed by name or a list of dicts carrying key."""
    if isinstance(entries, dict):
        return dict(entries)
    return {entry[key]: entry for entry in entries}


def cells_for(result, task_id):
    return as_indexed(result["per_task"], "task_id")[task_id]["conditions"]


def condition_aggregate(result, condition):
    return as_indexed(result["per_condition"], "condition")[condition]


def get_flag(result, name):
    """Flags may be exposed as top-level fields or inside a flags mapping."""
    if name in result:
        return result[name]
    flags = result.get("flags")
    if isinstance(flags, dict) and name in flags:
        return flags[name]
    raise AssertionError("output must expose governance flag %r" % name)


def assert_no_forbidden_keys(node):
    """No inferential, acceptance or financial field may appear anywhere."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, "forbidden output key: %r" % key
            assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for value in node:
            assert_no_forbidden_keys(value)


def cross_product_input():
    """Six tasks x three conditions covering every verdict and state."""
    tasks = [
        make_task("t1", cluster_id="c1", facets=["f1", "f2"], k=4),
        make_task("t2", facets=["f1"], k=2),
        make_task("t3", answerability="unknown", k=1),
        make_task("t4", answerability="unanswerable", facets=["f3"], k=3),
        make_task("t5", facets=["f1"], k=2),
        make_task("t6", k=2),
    ]
    observations = [
        make_observation(
            "t1",
            "no_memory",
            assessment="correct",
            claims=[
                make_claim("cA", verdict="supported", critical=True),
                make_claim("cB", verdict="unsupported", critical=False),
                make_claim("cC", material=False, verdict="contradicted", critical=False),
            ],
            retrieved=[
                make_item("i1", relevance=2, facets=["f1"]),
                make_item("i2", relevance=0, facets=["f2"]),
                make_item("i3", relevance=1, facets=["f1"]),
            ],
        ),
        make_observation(
            "t1",
            "recency",
            state="abstained",
            retrieved=[make_item("i4", relevance=1, facets=["f1"])],
        ),
        make_observation("t1", "fixed_l1", state="pending"),
        make_observation(
            "t2",
            "no_memory",
            assessment="incorrect",
            claims=[
                make_claim("cA", verdict="unsupported", critical=True),
                make_claim("cD", verdict="contradicted", critical=True),
            ],
            retrieved=[make_item("i5", relevance=0, facets=["f1"])],
        ),
        make_observation("t2", "recency", state="source_unavailable"),
        make_observation(
            "t3",
            "no_memory",
            assessment="unresolved",
            claims=[make_claim("cE", verdict="unresolved", critical=True)],
            retrieved=[make_item("i6", relevance=2)],
        ),
        make_observation("t3", "recency", state="censored"),
        make_observation(
            "t4",
            "no_memory",
            assessment="incorrect",
            claims=[make_claim("cF", verdict="attributed_inference", critical=True)],
            retrieved=[make_item("i7", relevance=1, facets=["f3"])],
        ),
        make_observation(
            "t4",
            "recency",
            state="abstained",
            retrieved=[make_item("i8", relevance=0, facets=["f3"])],
        ),
        make_observation("t6", "no_memory", state="missing"),
    ]
    return make_input(tasks, observations)


def minimal_valid_input():
    tasks = [
        make_task("t1", facets=["f1"], k=2),
        make_task("t2", answerability="unknown", k=1),
    ]
    observations = [
        make_observation(
            "t1",
            "no_memory",
            claims=[make_claim("c1", verdict="supported", critical=True)],
            retrieved=[make_item("i1", relevance=1, facets=["f1"])],
        ),
        make_observation(
            "t2",
            "recency",
            assessment="unresolved",
            claims=[make_claim("c2", verdict="unresolved", critical=True)],
            retrieved=[make_item("i2", relevance=0)],
        ),
    ]
    return make_input(tasks, observations)


def test_output_envelope_and_always_false_flags():
    result = score_critical_claims(cross_product_input())
    assert result["schema"] == OUTPUT_SCHEMA
    assert result["authority"] == AUTHORITY
    assert result["input_schema"] == INPUT_SCHEMA
    assert result["conditions"] == CONDITIONS
    assert result["total_registered_tasks"] == 6
    assert [entry["task_id"] for entry in result["per_task"]] == [
        "t1",
        "t2",
        "t3",
        "t4",
        "t5",
        "t6",
    ]
    for name in FLAG_NAMES:
        assert get_flag(result, name) is False
    assert_no_forbidden_keys(result)


def test_empty_input_yields_zero_denominators_and_empty_aggregates():
    result = score_critical_claims(make_input())
    assert result["schema"] == OUTPUT_SCHEMA
    assert result["authority"] == AUTHORITY
    assert result["total_registered_tasks"] == 0
    assert result["per_task"] == []
    assert set(as_indexed(result["per_condition"], "condition")) == set(CONDITIONS)
    for condition in CONDITIONS:
        assert condition_aggregate(result, condition) == {
            "registered_task_count": 0,
            "recorded_task_count": 0,
            "unrecorded_task_count": 0,
            "state_counts": {state: 0 for state in STATES},
            "counts": zeros(),
            "critical_verdict_counts": {verdict: 0 for verdict in VERDICTS},
        }
    for name in FLAG_NAMES:
        assert get_flag(result, name) is False
    assert_no_forbidden_keys(result)


def test_per_task_entry_copies_task_fields_and_all_three_conditions():
    result = score_critical_claims(cross_product_input())
    per_task = as_indexed(result["per_task"], "task_id")
    entry = per_task["t5"]
    assert entry["task_id"] == "t5"
    assert entry["cluster_id"] is None
    assert entry["answerability"] == "answerable"
    assert entry["required_facet_ids"] == ["f1"]
    assert entry["k"] == 2
    assert set(entry["conditions"]) == set(CONDITIONS)
    for condition in CONDITIONS:
        assert entry["conditions"][condition] == cell(False, "missing")
    assert per_task["t1"]["cluster_id"] == "c1"
    assert per_task["t3"]["answerability"] == "unknown"
    assert per_task["t4"]["answerability"] == "unanswerable"


def test_explicit_missing_is_distinct_from_omitted_cell():
    result = score_critical_claims(cross_product_input())
    t6 = cells_for(result, "t6")
    assert t6["no_memory"] == cell(True, "missing")
    assert t6["recency"] == cell(False, "missing")
    assert t6["fixed_l1"] == cell(False, "missing")
    no_memory = condition_aggregate(result, "no_memory")
    assert no_memory["registered_task_count"] == 6
    assert no_memory["recorded_task_count"] == 5
    assert no_memory["unrecorded_task_count"] == 1
    assert no_memory["state_counts"] == {
        "answered": 4,
        "abstained": 0,
        "missing": 2,
        "source_unavailable": 0,
        "pending": 0,
        "censored": 0,
    }


def test_hand_computed_answered_cell_counts_and_verdict_buckets():
    result = score_critical_claims(cross_product_input())
    no_memory = cells_for(result, "t1")["no_memory"]
    assert no_memory["record_present"] is True
    assert no_memory["state"] == "answered"
    assert no_memory["counts"] == {
        "all_claim_count": 3,
        "material_claim_count": 2,
        "critical_claim_count": 1,
        "critical_unsupported_claim_count": 0,
    }
    assert no_memory["critical_claim_ids_by_verdict"] == {
        "supported": ["cA"],
        "contradicted": [],
        "unsupported": [],
        "attributed_inference": [],
        "unresolved": [],
    }


def test_joint_unsupported_counts_only_critical_and_unsupported_claims():
    result = score_critical_claims(cross_product_input())
    no_memory = cells_for(result, "t2")["no_memory"]
    assert no_memory["state"] == "answered"
    assert no_memory["counts"] == {
        "all_claim_count": 2,
        "material_claim_count": 2,
        "critical_claim_count": 2,
        "critical_unsupported_claim_count": 1,
    }
    assert no_memory["critical_claim_ids_by_verdict"] == {
        "supported": [],
        "contradicted": ["cD"],
        "unsupported": ["cA"],
        "attributed_inference": [],
        "unresolved": [],
    }
    assert cells_for(result, "t2")["fixed_l1"] == cell(False, "missing")
    assert (
        condition_aggregate(result, "no_memory")["counts"][
            "critical_unsupported_claim_count"
        ]
        == 1
    )


def test_supported_critical_and_noncritical_unsupported_not_joint_failures():
    value = make_input(
        tasks=[make_task("t1", k=2)],
        observations=[
            make_observation(
                "t1",
                "no_memory",
                claims=[
                    make_claim("c1", verdict="supported", critical=True),
                    make_claim("c2", verdict="unsupported", critical=False),
                ],
                retrieved=[make_item("i1", relevance=1)],
            )
        ],
    )
    result = score_critical_claims(value)
    no_memory = cells_for(result, "t1")["no_memory"]
    assert no_memory["counts"] == {
        "all_claim_count": 2,
        "material_claim_count": 2,
        "critical_claim_count": 1,
        "critical_unsupported_claim_count": 0,
    }
    assert no_memory["critical_claim_ids_by_verdict"]["supported"] == ["c1"]
    assert condition_aggregate(result, "no_memory")["critical_verdict_counts"] == {
        "supported": 1,
        "contradicted": 0,
        "unsupported": 0,
        "attributed_inference": 0,
        "unresolved": 0,
    }


def test_unknown_and_unresolved_buckets_are_preserved_not_penalised():
    result = score_critical_claims(cross_product_input())
    per_task = as_indexed(result["per_task"], "task_id")
    assert per_task["t3"]["answerability"] == "unknown"
    t3 = per_task["t3"]["conditions"]["no_memory"]
    assert t3["state"] == "answered"
    assert t3["counts"]["critical_claim_count"] == 1
    assert t3["counts"]["critical_unsupported_claim_count"] == 0
    assert t3["critical_claim_ids_by_verdict"]["unresolved"] == ["cE"]
    t4 = per_task["t4"]["conditions"]["no_memory"]
    assert t4["critical_claim_ids_by_verdict"]["attributed_inference"] == ["cF"]
    assert t4["counts"]["critical_unsupported_claim_count"] == 0


def test_non_answered_states_are_retained_with_zero_claim_counts():
    result = score_critical_claims(cross_product_input())
    assert cells_for(result, "t1")["recency"] == cell(True, "abstained")
    assert cells_for(result, "t1")["fixed_l1"] == cell(True, "pending")
    assert cells_for(result, "t2")["recency"] == cell(True, "source_unavailable")
    assert cells_for(result, "t3")["recency"] == cell(True, "censored")


def test_hand_computed_per_condition_aggregates():
    result = score_critical_claims(cross_product_input())
    no_memory = condition_aggregate(result, "no_memory")
    assert no_memory["counts"] == {
        "all_claim_count": 7,
        "material_claim_count": 6,
        "critical_claim_count": 5,
        "critical_unsupported_claim_count": 1,
    }
    assert no_memory["critical_verdict_counts"] == {
        "supported": 1,
        "contradicted": 1,
        "unsupported": 1,
        "attributed_inference": 1,
        "unresolved": 1,
    }
    recency = condition_aggregate(result, "recency")
    assert recency["registered_task_count"] == 6
    assert recency["recorded_task_count"] == 4
    assert recency["unrecorded_task_count"] == 2
    assert recency["state_counts"] == {
        "answered": 0,
        "abstained": 2,
        "missing": 2,
        "source_unavailable": 1,
        "pending": 0,
        "censored": 1,
    }
    assert recency["counts"] == zeros()
    assert recency["critical_verdict_counts"] == {verdict: 0 for verdict in VERDICTS}
    fixed_l1 = condition_aggregate(result, "fixed_l1")
    assert fixed_l1["recorded_task_count"] == 1
    assert fixed_l1["unrecorded_task_count"] == 5
    assert fixed_l1["state_counts"] == {
        "answered": 0,
        "abstained": 0,
        "missing": 5,
        "source_unavailable": 0,
        "pending": 1,
        "censored": 0,
    }
    assert fixed_l1["counts"] == zeros()


def test_state_counts_and_denominators_partition_every_condition():
    result = score_critical_claims(cross_product_input())
    per_condition = as_indexed(result["per_condition"], "condition")
    assert set(per_condition) == set(CONDITIONS)
    for condition in CONDITIONS:
        aggregate = per_condition[condition]
        assert aggregate["registered_task_count"] == result["total_registered_tasks"]
        assert (
            aggregate["recorded_task_count"] + aggregate["unrecorded_task_count"]
            == aggregate["registered_task_count"]
        )
        assert sum(aggregate["state_counts"].values()) == aggregate[
            "registered_task_count"
        ]
        for verdict in VERDICTS:
            assert isinstance(aggregate["critical_verdict_counts"][verdict], int)


def test_claim_id_scoping_reuse_across_cells_rejected_within_a_cell():
    tasks = [make_task("t1", k=2), make_task("t2", k=2)]
    observations = [
        make_observation(
            "t1",
            "no_memory",
            claims=[
                make_claim("dup", verdict="supported", critical=True),
                make_claim("solo", verdict="unresolved", critical=False),
            ],
            retrieved=[make_item("i1")],
        ),
        make_observation(
            "t1",
            "recency",
            claims=[make_claim("dup", verdict="unsupported", critical=True)],
            retrieved=[make_item("i2")],
        ),
        make_observation(
            "t2",
            "no_memory",
            claims=[make_claim("dup", verdict="contradicted", critical=False)],
            retrieved=[make_item("i3")],
        ),
    ]
    result = score_critical_claims(make_input(tasks, observations))
    t1 = cells_for(result, "t1")
    assert t1["no_memory"]["critical_claim_ids_by_verdict"]["supported"] == ["dup"]
    assert t1["recency"]["critical_claim_ids_by_verdict"]["unsupported"] == ["dup"]
    assert t1["no_memory"]["counts"]["all_claim_count"] == 2
    assert cells_for(result, "t2")["no_memory"]["counts"]["critical_claim_count"] == 0
    conflicting = make_input(
        tasks,
        observations
        + [
            make_observation(
                "t2",
                "recency",
                claims=[
                    make_claim("dup", verdict="supported", critical=True),
                    make_claim("dup", verdict="supported", critical=True),
                ],
                retrieved=[make_item("i4")],
            )
        ],
    )
    with pytest.raises(EvidenceAccountingError):
        score_critical_claims(conflicting)


def test_critical_claim_ids_sorted_lexically_inside_verdict_buckets():
    value = make_input(
        tasks=[make_task("t1", k=4)],
        observations=[
            make_observation(
                "t1",
                "fixed_l1",
                claims=[
                    make_claim("z9", verdict="unsupported", critical=True),
                    make_claim("a1", verdict="unsupported", critical=True),
                    make_claim("m5", verdict="unresolved", critical=True),
                    make_claim("b2", verdict="supported", critical=True),
                ],
                retrieved=[make_item("i1"), make_item("i2")],
            )
        ],
    )
    result = score_critical_claims(value)
    fixed_l1 = cells_for(result, "t1")["fixed_l1"]
    assert fixed_l1["counts"]["critical_unsupported_claim_count"] == 2
    assert fixed_l1["critical_claim_ids_by_verdict"] == {
        "supported": ["b2"],
        "contradicted": [],
        "unsupported": ["a1", "z9"],
        "attributed_inference": [],
        "unresolved": ["m5"],
    }


def test_input_is_not_mutated_and_output_is_detached():
    value = cross_product_input()
    snapshot = copy.deepcopy(value)
    result = score_critical_claims(value)
    assert value == snapshot
    result["total_registered_tasks"] = 999
    result["per_task"][0]["conditions"]["no_memory"]["counts"]["all_claim_count"] = 999
    fresh = score_critical_claims(cross_product_input())
    assert value == snapshot
    assert fresh != result
    assert fresh["total_registered_tasks"] == 6
    assert (
        fresh["per_task"][0]["conditions"]["no_memory"]["counts"]["all_claim_count"]
        == 3
    )


def test_task_and_observation_order_permutations_keep_output_stable():
    value = cross_product_input()
    baseline = score_critical_claims(value)
    reversed_input = make_input(
        tasks=list(reversed(value["tasks"])),
        observations=list(reversed(value["observations"])),
    )
    assert score_critical_claims(reversed_input) == baseline
    rotated_input = make_input(
        tasks=value["tasks"][3:] + value["tasks"][:3],
        observations=value["observations"][4:] + value["observations"][:4],
    )
    assert score_critical_claims(rotated_input) == baseline
    assert [entry["task_id"] for entry in baseline["per_task"]] == sorted(
        task["task_id"] for task in value["tasks"]
    )


def _set_schema(value):
    value["schema"] = "market_memory.evidence_accounting_input.v2"


def _extra_root_key(value):
    value["extra"] = 1


def _missing_root_key(value):
    value.pop("conditions")


def _conditions_not_exact_list(value):
    value["conditions"] = ["no_memory", "recency"]


def _tasks_not_a_list(value):
    value["tasks"] = {"t1": value["tasks"][0]}


def _duplicate_task_id(value):
    value["tasks"].append(make_task("t1"))


def _k_is_bool(value):
    value["tasks"][0]["k"] = True


def _k_below_range(value):
    value["tasks"][0]["k"] = 0


def _k_above_range(value):
    value["tasks"][0]["k"] = 9


def _k_not_int(value):
    value["tasks"][0]["k"] = "2"


def _task_extra_key(value):
    value["tasks"][0]["weight"] = 1


def _task_id_not_matching_pattern(value):
    value["tasks"][0]["task_id"] = "bad id!"


def _duplicate_required_facet(value):
    value["tasks"][0]["required_facet_ids"] = ["f1", "f1"]


def _facet_id_not_matching_pattern(value):
    value["tasks"][0]["required_facet_ids"] = ["bad facet"]


def _unknown_answerability(value):
    value["tasks"][0]["answerability"] = "maybe"


def _observation_unknown_task(value):
    value["observations"][0]["task_id"] = "ghost"


def _duplicate_task_condition_cell(value):
    value["observations"].append(
        make_observation(
            "t1",
            "no_memory",
            state="abstained",
            retrieved=[make_item("i9")],
        )
    )


def _observation_extra_key(value):
    value["observations"][0]["note"] = "x"


def _unknown_state(value):
    value["observations"][0]["state"] = "skipped"


def _unknown_assessment(value):
    value["observations"][0]["answer_assessment"] = "maybe"


def _answered_with_not_applicable(value):
    value["observations"][0]["answer_assessment"] = "not_applicable"


def _unanswerable_answered_correct(value):
    value["tasks"][1] = make_task("t2", answerability="unanswerable", k=1)
    value["observations"][1]["answer_assessment"] = "correct"


def _unknown_answerable_answered_non_unresolved(value):
    value["observations"][1]["answer_assessment"] = "incorrect"


def _non_answered_with_claims(value):
    value["observations"].append(
        make_observation(
            "t1",
            "recency",
            state="abstained",
            claims=[make_claim("c9", verdict="supported", critical=True)],
            retrieved=[make_item("i9")],
        )
    )


def _non_answered_with_non_default_assessment(value):
    value["observations"].append(
        make_observation(
            "t1",
            "recency",
            state="abstained",
            assessment="unresolved",
            retrieved=[make_item("i9")],
        )
    )


def _pending_with_retrieved(value):
    value["observations"].append(
        make_observation(
            "t1",
            "recency",
            state="pending",
            retrieved=[make_item("i9")],
        )
    )


def _missing_with_retrieved(value):
    value["observations"].append(
        make_observation(
            "t1",
            "recency",
            state="missing",
            retrieved=[make_item("i9")],
        )
    )


def _material_is_int(value):
    value["observations"][0]["claims"][0]["material"] = 1


def _critical_is_int(value):
    value["observations"][0]["claims"][0]["critical"] = 0


def _critical_claim_without_material(value):
    value["observations"][0]["claims"][0] = make_claim(
        "c1",
        material=False,
        verdict="supported",
        critical=True,
    )


def _unknown_verdict(value):
    value["observations"][0]["claims"][0]["verdict"] = "refuted"


def _claim_extra_key(value):
    value["observations"][0]["claims"][0]["score"] = 1


def _claim_missing_required_field(value):
    value["observations"][0]["claims"][0].pop("critical")


def _relevance_is_bool(value):
    value["observations"][0]["retrieved"][0]["relevance"] = True


def _relevance_above_range(value):
    value["observations"][0]["retrieved"][0]["relevance"] = 3


def _relevance_below_range(value):
    value["observations"][0]["retrieved"][0]["relevance"] = -1


def _duplicate_retrieved_item_id(value):
    value["observations"][0]["retrieved"].append(
        make_item("i1", relevance=2, facets=["f1"])
    )


def _retrieved_unregistered_facet(value):
    value["observations"][0]["retrieved"][0]["facet_ids"] = ["fX"]


def _duplicate_facets_inside_item(value):
    value["observations"][0]["retrieved"][0]["facet_ids"] = ["f1", "f1"]


def _retrieved_longer_than_k(value):
    value["observations"][0]["retrieved"].append(
        make_item("i3", relevance=1, facets=["f1"])
    )
    value["observations"][0]["retrieved"].append(make_item("i4", relevance=0))


def _retrieved_extra_key(value):
    value["observations"][0]["retrieved"][0]["rank"] = 1


INVALID_MUTATIONS = {
    "wrong_schema": _set_schema,
    "extra_root_key": _extra_root_key,
    "missing_root_key": _missing_root_key,
    "conditions_not_exact_list": _conditions_not_exact_list,
    "tasks_not_a_list": _tasks_not_a_list,
    "duplicate_task_id": _duplicate_task_id,
    "k_is_bool": _k_is_bool,
    "k_below_range": _k_below_range,
    "k_above_range": _k_above_range,
    "k_not_int": _k_not_int,
    "task_extra_key": _task_extra_key,
    "task_id_not_matching_pattern": _task_id_not_matching_pattern,
    "duplicate_required_facet": _duplicate_required_facet,
    "facet_id_not_matching_pattern": _facet_id_not_matching_pattern,
    "unknown_answerability": _unknown_answerability,
    "observation_unknown_task": _observation_unknown_task,
    "duplicate_task_condition_cell": _duplicate_task_condition_cell,
    "observation_extra_key": _observation_extra_key,
    "unknown_state": _unknown_state,
    "unknown_assessment": _unknown_assessment,
    "answered_with_not_applicable": _answered_with_not_applicable,
    "unanswerable_answered_correct": _unanswerable_answered_correct,
    "unknown_answerable_answered_non_unresolved": _unknown_answerable_answered_non_unresolved,
    "non_answered_with_claims": _non_answered_with_claims,
    "non_answered_with_non_default_assessment": _non_answered_with_non_default_assessment,
    "pending_with_retrieved": _pending_with_retrieved,
    "missing_with_retrieved": _missing_with_retrieved,
    "material_is_int": _material_is_int,
    "critical_is_int": _critical_is_int,
    "critical_claim_without_material": _critical_claim_without_material,
    "unknown_verdict": _unknown_verdict,
    "claim_extra_key": _claim_extra_key,
    "claim_missing_required_field": _claim_missing_required_field,
    "relevance_is_bool": _relevance_is_bool,
    "relevance_above_range": _relevance_above_range,
    "relevance_below_range": _relevance_below_range,
    "duplicate_retrieved_item_id": _duplicate_retrieved_item_id,
    "retrieved_unregistered_facet": _retrieved_unregistered_facet,
    "duplicate_facets_inside_item": _duplicate_facets_inside_item,
    "retrieved_longer_than_k": _retrieved_longer_than_k,
    "retrieved_extra_key": _retrieved_extra_key,
}


@pytest.mark.parametrize(
    "mutate",
    list(INVALID_MUTATIONS.values()),
    ids=list(INVALID_MUTATIONS),
)
def test_invalid_inputs_raise_evidence_accounting_error(mutate):
    value = minimal_valid_input()
    mutate(value)
    with pytest.raises(EvidenceAccountingError):
        score_critical_claims(value)
