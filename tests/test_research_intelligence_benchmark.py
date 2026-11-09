from __future__ import annotations

import hashlib
import json
import stat

from engine.research_intelligence.benchmark import (
    BENCHMARK_CONTRACT_SHA256,
    BENCHMARK_VERSION,
    CASE_SCHEMA,
    OBSERVATION_SCHEMA,
    aggregate_results,
    build_benchmark_request,
    score_raw_output,
    score_rio,
)
from engine.research_intelligence.extractor import _identity, build_prompt
from engine.research_intelligence.schema import SCHEMA
from engine.research_intelligence.selection import (
    SELECTOR_VERSION,
    build_selection_catalog,
)
from scripts.research_intelligence_benchmark import _write_json


Q0 = "AMD server demand accelerated by 35% year over year as cloud buyers raised orders."
Q1 = "Management expects GPU supply to normalize by the December quarter."
Q2 = "A product launch in October is the next demand catalyst."
Q3 = "The thesis would weaken if AMD cloud orders fall below last year's level."
BODY = " ".join((Q0, Q1, Q2, Q3))
DOCUMENT = {
    "id": "bench-doc-001",
    "source_type": "institutional_research",
    "source_name": "Fixture Research",
    "institution": "Fixture Research",
    "desk": "Semiconductors",
    "title": "AMD server demand",
    "published_at": "2026-09-18T12:00:00Z",
}
_HORIZONS = {0: "current", 1: "December quarter", 2: "October", 3: "future"}


def _case() -> dict:
    return {
        "schema": CASE_SCHEMA,
        "case_id": "fixture-amd-001",
        "source_content_sha256": hashlib.sha256(BODY.encode("utf-8")).hexdigest(),
        "document": dict(DOCUMENT),
        "expected": {
            "claims": [
                {"quote_span": Q0, "numbers": ["35%"], "entities": ["AMD"]},
                {"quote_span": Q1, "numbers": [], "entities": []},
                {"quote_span": Q2, "numbers": [], "entities": []},
                {"quote_span": Q3, "numbers": [], "entities": ["AMD"]},
            ],
            "thesis_direction": "bullish",
            "thesis_support_claim_indices": [0],
            "thesis_concepts": [
                ["stronger", "strengthening"],
                ["cloud"],
                ["demand"],
            ],
            "analysis_support": {
                "forecasts": [[1]],
                "catalysts": [[2]],
                "falsifiers": [[3]],
            },
            "analysis_semantics": {
                "forecasts": [
                    {
                        "support_claim_indices": [1],
                        "concept_groups": [
                            ["supply"],
                            ["normalize", "normalization"],
                            ["december"],
                        ],
                    }
                ],
                "catalysts": [
                    {
                        "support_claim_indices": [2],
                        "concept_groups": [
                            ["october"],
                            ["launch"],
                            ["catalyst"],
                        ],
                    }
                ],
                "falsifiers": [
                    {
                        "support_claim_indices": [3],
                        "concept_groups": [
                            ["falling", "fall"],
                            ["cloud"],
                            ["orders"],
                            ["weaken", "weakened"],
                        ],
                    }
                ],
            },
        },
    }


def _catalog() -> tuple[dict, dict]:
    """The exact body-bound W1 selection catalog this fixture must answer."""
    identity = _identity(DOCUMENT, BODY)
    catalog = build_selection_catalog(identity, BODY)
    texts = [unit["text"] for unit in catalog["units"]]
    # Every gold quote must be an admitted catalog unit, otherwise the current
    # W1 protocol could never produce the gold claim and the case would be
    # unscoreable rather than wrong.
    assert texts == [Q0, Q1, Q2, Q3]
    return identity, catalog


def _analysis(
    *,
    thesis_summary: str = (
        "The note argues stronger cloud demand supports the AMD server outlook."
    ),
    mechanism: list[str] | None = None,
    direction: str = "bullish",
    forecasts: list[dict] | None = None,
    catalysts: list[dict] | None = None,
    falsifiers: list[dict] | None = None,
) -> dict:
    return {
        "thesis": {
            "summary": thesis_summary,
            "direction": direction,
            "mechanism": (
                ["cloud ordering raises server demand"]
                if mechanism is None
                else mechanism
            ),
            "conviction": "moderate",
            "support_claim_indices": [0],
        },
        "assumptions": [],
        "forecasts": (
            [
                {
                    "statement": "Supply is expected to normalize by the December quarter.",
                    "horizon": "December quarter",
                    "confidence": "",
                    "support_claim_indices": [1],
                }
            ]
            if forecasts is None
            else forecasts
        ),
        "catalysts": (
            [
                {
                    "statement": "The October product launch is a catalyst.",
                    "support_claim_indices": [2],
                }
            ]
            if catalysts is None
            else catalysts
        ),
        "falsifiers": (
            [
                {
                    "statement": "Falling cloud orders would weaken the thesis.",
                    "support_claim_indices": [3],
                }
            ]
            if falsifiers is None
            else falsifiers
        ),
        "counterarguments": [],
        "implications": [],
        "belief_delta": {"statement": "", "support_claim_indices": []},
        "consensus_relation": {"statement": "", "support_claim_indices": []},
        "uncertainties": [],
    }


def _payload(
    *,
    units: tuple[int, ...] = (0, 1, 2, 3),
    numbers: dict[int, list[str]] | None = None,
    entities: dict[int, list[str]] | None = None,
    analysis: dict | None = None,
) -> dict:
    """A compliant answer to the CURRENT W1 prompt: selections plus analysis."""
    identity, catalog = _catalog()
    numbers = {0: ["35%"]} if numbers is None else numbers
    entities = {0: ["AMD"], 3: ["AMD"]} if entities is None else entities
    selections = []
    for index in units:
        unit = catalog["units"][index]
        selections.append(
            {
                "evidence_id": unit["evidence_id"],
                "numbers": list(numbers.get(index, [])),
                "entities": list(entities.get(index, [])),
                "horizon": _HORIZONS.get(index, ""),
                "explicit": True,
            }
        )
    return {
        "selector": SELECTOR_VERSION,
        "document": identity,
        "catalog_sha256": catalog["catalog_sha256"],
        "selections": selections,
        "analysis": _analysis() if analysis is None else analysis,
    }


def _rio(*, include_falsifier: bool = True) -> dict:
    identity = _identity(DOCUMENT, BODY)
    claims = [
        {
            "statement": Q0,
            "evidence": [{"quote_span": Q0}],
            "numbers": ["35%"],
            "entities": ["AMD"],
            "horizon": "current",
            "explicit": True,
        },
        {
            "statement": Q1,
            "evidence": [{"quote_span": Q1}],
            "numbers": [],
            "entities": [],
            "horizon": "December quarter",
            "explicit": True,
        },
        {
            "statement": Q2,
            "evidence": [{"quote_span": Q2}],
            "numbers": [],
            "entities": [],
            "horizon": "October",
            "explicit": True,
        },
    ]
    if include_falsifier:
        claims.append(
            {
                "statement": Q3,
                "evidence": [{"quote_span": Q3}],
                "numbers": [],
                "entities": ["AMD"],
                "horizon": "future",
                "explicit": True,
            }
        )
    return {
        "schema": SCHEMA,
        "document": identity,
        "claims": claims,
        "analysis": {
            "thesis": {
                "summary": "The note argues stronger cloud demand supports the AMD server outlook.",
                "direction": "bullish",
                "mechanism": ["cloud ordering raises server demand"],
                "conviction": "moderate",
                "support_claim_indices": [0],
            },
            "assumptions": [],
            "forecasts": [
                {
                    "statement": "Supply is expected to normalize by the December quarter.",
                    "horizon": "December quarter",
                    "confidence": "",
                    "support_claim_indices": [1],
                }
            ],
            "catalysts": [
                {
                    "statement": "The October product launch is a catalyst.",
                    "support_claim_indices": [2],
                }
            ],
            "falsifiers": (
                [
                    {
                        "statement": "Falling cloud orders would weaken the thesis.",
                        "support_claim_indices": [3],
                    }
                ]
                if include_falsifier
                else []
            ),
            "counterarguments": [],
            "implications": [],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
            "uncertainties": [],
        },
        "authority": "descriptive_research_only",
    }


def test_request_is_exact_w1_prompt_and_marked_private():
    request = build_benchmark_request(_case(), BODY)
    assert request["visibility"] == "private_source_bound"
    assert request["case_id"] == "fixture-amd-001"
    assert request["benchmark_version"] == BENCHMARK_VERSION
    assert request["benchmark_contract_sha256"] == BENCHMARK_CONTRACT_SHA256
    assert BODY in request["user_prompt"]
    assert request["source_content_sha256"] == hashlib.sha256(BODY.encode()).hexdigest()
    assert len(request["gold_contract_sha256"]) == 64


def test_request_carries_the_current_w1_selector_prompt_verbatim():
    request = build_benchmark_request(_case(), BODY)
    system, user = build_prompt(DOCUMENT, BODY)
    assert request["system_prompt"] == system
    assert request["user_prompt"] == user
    assert request["prompt_sha256"] == hashlib.sha256(
        (system + "\n" + user).encode("utf-8")
    ).hexdigest()
    # The prepared request is the current W1 contract, not a replayed one.
    assert SELECTOR_VERSION in request["system_prompt"]
    assert "EVIDENCE CATALOG" in request["user_prompt"]


def test_perfect_grounded_output_scores_all_available_dimensions():
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    assert result["state"] == "ok"
    assert result["overall_score"] == 1.0
    assert all(value in (1.0, None) for value in result["metrics"].values())
    assert result["counts"]["matched_claims"] == 4
    assert result["counts"]["expected_thesis_support"] == 1
    assert result["counts"]["matched_thesis_support"] == 1
    assert result["counts"]["thesis_semantic_expected"] == 1
    assert result["counts"]["thesis_semantic_correct"] == 1
    assert result["counts"]["expected_analysis_semantics"] == 3
    assert result["counts"]["matched_analysis_semantics"] == 3
    assert result["counts"]["direction_expected"] == 1
    assert result["counts"]["direction_correct"] == 1
    assert result["provenance_state"] == "operator_label_only"
    assert len(result["gold_contract_sha256"]) == 64


def test_rio_shaped_answer_is_not_a_valid_current_w1_answer():
    # The current W1 contract makes the system assemble claim text, so a raw
    # RIO is not a compliant answer. It earns zero credit rather than being
    # silently scored on a different protocol.
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_rio()),
        candidate_label="rio-shaped-model",
    )
    assert result["state"] == "invalid_output"
    assert result["overall_score"] == 0.0
    assert result["counts"]["matched_claims"] == 0


def test_missing_claim_reduces_recall_and_category_score():
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload(units=(0, 1, 2), analysis=_analysis(falsifiers=[]))),
        candidate_label="model-b",
    )
    assert result["state"] == "ok"
    assert result["metrics"]["claim_recall"] == 0.75
    assert result["metrics"]["analysis_category_recall"] == 0.666667
    assert result["overall_score"] < 1.0


def test_invalid_output_fails_closed_and_receipt_contains_no_source_text():
    result = score_raw_output(
        _case(),
        BODY,
        "not json and not a grounded W1 answer",
        candidate_label="broken-model",
    )
    serialized = json.dumps(result)
    assert result["state"] == "invalid_output"
    assert result["metrics"]["validity"] == 0.0
    assert result["overall_score"] == 0.0
    assert result["counts"]["matched_claims"] == 0
    assert result["counts"]["matched_thesis_support"] == 0
    assert result["counts"]["thesis_semantic_correct"] == 0
    assert result["counts"]["matched_analysis_semantics"] == 0
    assert result["counts"]["direction_correct"] == 0
    assert Q0 not in serialized
    assert Q1 not in serialized
    assert BODY not in serialized


def test_source_hash_mismatch_is_rejected():
    case = _case()
    case["source_content_sha256"] = "0" * 64
    try:
        score_raw_output(case, BODY, json.dumps(_payload()), candidate_label="model-a")
    except ValueError as exc:
        assert "source hash" in str(exc)
    else:
        raise AssertionError("source mismatch must fail closed")


def test_duplicate_gold_claim_is_rejected():
    case = _case()
    case["expected"]["claims"].append(dict(case["expected"]["claims"][0]))
    try:
        build_benchmark_request(case, BODY)
    except ValueError as exc:
        assert "duplicate expected claim" in str(exc)
    else:
        raise AssertionError("duplicate gold claims must fail closed")


def test_direct_rio_scoring_rechecks_source_grounding():
    rio = _rio()
    fabricated = "Fabricated evidence says AMD demand rose by 99%."
    for claim in rio["claims"]:
        claim["statement"] = fabricated
        claim["evidence"] = [{"quote_span": fabricated}]
        claim["numbers"] = ["99%"]
        claim["entities"] = ["AMD"]
    try:
        score_rio(_case(), BODY, rio)
    except ValueError:
        pass
    else:
        raise AssertionError("direct RIO scoring must not trust fabricated evidence")


def test_direct_rio_scoring_reports_real_grounding_counts():
    result = score_rio(_case(), BODY, _rio())
    assert result["counts"]["emitted_claims"] == 4
    assert result["counts"]["grounded_claims"] == 4
    assert result["counts"]["emitted_numbers"] == 1
    assert result["counts"]["grounded_numbers"] == 1
    assert result["counts"]["emitted_entities"] == 2
    assert result["counts"]["evidence_grounded_entities"] == 2


def test_aggregate_ranks_by_mean_score_without_source_text():
    good = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="strong-model",
    )
    weak = score_raw_output(
        _case(),
        BODY,
        "invalid",
        candidate_label="weak-model",
    )
    aggregate = aggregate_results([weak, good])
    assert aggregate["candidates"][0]["candidate_label"] == "strong-model"
    assert aggregate["candidates"][0]["mean_overall_score"] == 1.0
    assert aggregate["candidates"][1]["mean_overall_score"] == 0.0
    assert len(aggregate["case_set_sha256"]) == 64
    assert BODY not in json.dumps(aggregate)


def test_aggregate_refuses_unequal_case_coverage():
    first = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    other_case = _case()
    other_case["case_id"] = "fixture-amd-002"
    second = score_raw_output(
        other_case,
        BODY,
        json.dumps(_payload()),
        candidate_label="model-b",
    )
    try:
        aggregate_results([first, second])
    except ValueError as exc:
        assert "case coverage differs" in str(exc)
    else:
        raise AssertionError("unequal case coverage must not produce a ranking")


def test_aggregate_refuses_tampered_scores():
    first = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    second = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-b",
    )
    second["overall_score"] = 0.123
    try:
        aggregate_results([first, second])
    except ValueError as exc:
        assert "overall_score disagrees" in str(exc)
    else:
        raise AssertionError("tampered score must fail closed")


def test_private_prompt_writer_forces_owner_only_permissions(tmp_path):
    target = tmp_path / "request.json"
    target.write_text("old", encoding="utf-8")
    target.chmod(0o644)
    _write_json(target, {"secret": Q0}, private=True)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert json.loads(target.read_text(encoding="utf-8")) == {"secret": Q0}


def test_aggregate_refuses_different_gold_contract_for_same_source_and_prompt():
    first = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    changed_gold = _case()
    changed_gold["expected"]["thesis_direction"] = "bearish"
    second = score_raw_output(
        changed_gold,
        BODY,
        json.dumps(_payload()),
        candidate_label="model-b",
    )
    assert first["source_content_sha256"] == second["source_content_sha256"]
    assert first["prompt_sha256"] == second["prompt_sha256"]
    assert first["gold_contract_sha256"] != second["gold_contract_sha256"]
    try:
        aggregate_results([first, second])
    except ValueError as exc:
        assert "gold contract differs" in str(exc)
    else:
        raise AssertionError("different private gold must never produce a ranking")


def test_aggregate_refuses_metric_tampering_even_when_overall_is_recomputed():
    first = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    second = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-b",
    )
    second["metrics"]["claim_recall"] = 0.5
    present = [
        float(value)
        for value in second["metrics"].values()
        if value is not None
    ]
    second["overall_score"] = round(sum(present) / len(present), 6)
    try:
        aggregate_results([first, second])
    except ValueError as exc:
        assert "metrics disagree with counts/state" in str(exc)
    else:
        raise AssertionError("tampered metric must fail even with matching overall")


def test_invalid_output_cannot_retain_matched_credit():
    result = score_raw_output(
        _case(),
        BODY,
        "invalid",
        candidate_label="broken-model",
    )
    result["counts"]["matched_claims"] = 1
    try:
        aggregate_results([result])
    except ValueError as exc:
        assert "invalid benchmark output cannot retain matched credit" in str(exc)
    else:
        raise AssertionError("invalid output cannot keep matched benchmark credit")


def test_semantic_anchor_recall_rejects_generic_text_with_correct_support():
    analysis = _analysis(
        thesis_summary="The note presents a constructive server outlook.",
        mechanism=["fundamental conditions support the thesis"],
        forecasts=[
            {
                "statement": "Conditions may improve later.",
                "horizon": "",
                "confidence": "",
                "support_claim_indices": [1],
            }
        ],
        catalysts=[
            {
                "statement": "A future event could matter.",
                "support_claim_indices": [2],
            }
        ],
        falsifiers=[
            {
                "statement": "The thesis could fail under adverse conditions.",
                "support_claim_indices": [3],
            }
        ],
    )

    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload(analysis=analysis)),
        candidate_label="generic-supported-model",
    )
    assert result["state"] == "ok"
    assert result["metrics"]["thesis_support_recall"] == 1.0
    assert result["metrics"]["analysis_category_recall"] == 1.0
    assert result["metrics"]["thesis_semantic_accuracy"] == 0.0
    assert result["metrics"]["analysis_semantic_recall"] == 0.0
    assert result["counts"]["matched_analysis_semantics"] == 0
    assert result["overall_score"] < 1.0


def test_semantic_gold_changes_gold_contract_hash():
    first = _case()
    changed = _case()
    changed["expected"]["analysis_semantics"]["forecasts"][0]["concept_groups"][1] = [
        "tighten",
        "tightening",
    ]
    first_request = build_benchmark_request(first, BODY)
    changed_request = build_benchmark_request(changed, BODY)
    assert first_request["prompt_sha256"] == changed_request["prompt_sha256"]
    assert (
        first_request["gold_contract_sha256"]
        != changed_request["gold_contract_sha256"]
    )


def test_aggregate_explicitly_grants_no_model_promotion_authority():
    good = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    aggregate = aggregate_results([good])
    assert aggregate["ranking_basis"] == "private_gold_grounded_extraction_metrics"
    assert aggregate["promotion_authority"] == "none"


def test_one_output_row_cannot_satisfy_two_gold_analysis_expectations():
    case = json.loads(json.dumps(_case()))
    case["expected"]["analysis_support"] = {
        "forecasts": [[1], [2]],
    }
    case["expected"]["analysis_semantics"] = {
        "forecasts": [
            {
                "support_claim_indices": [1],
                "concept_groups": [["supply"], ["normalize"], ["december"]],
            },
            {
                "support_claim_indices": [2],
                "concept_groups": [["october"], ["launch"], ["catalyst"]],
            },
        ],
    }

    analysis = _analysis(
        forecasts=[
            {
                "statement": (
                    "Supply should normalize by December and the October launch "
                    "is the next catalyst."
                ),
                "horizon": "December and October",
                "confidence": "moderate",
                "support_claim_indices": [1, 2],
            }
        ],
        catalysts=[],
        falsifiers=[],
    )

    result = score_raw_output(
        case,
        BODY,
        json.dumps(_payload(analysis=analysis)),
        candidate_label="one-row-for-two-expectations",
    )
    assert result["state"] == "ok"
    assert result["counts"]["expected_analysis_categories"] == 2
    assert result["counts"]["matched_analysis_categories"] == 1
    assert result["counts"]["expected_analysis_semantics"] == 2
    assert result["counts"]["matched_analysis_semantics"] == 1
    assert result["metrics"]["analysis_category_recall"] == 0.5
    assert result["metrics"]["analysis_semantic_recall"] == 0.5


def test_grounding_precision_penalizes_ungrounded_model_annotations():
    # The current W1 contract forbids the model from writing claim text, so
    # the surviving fabrication surface is the model's own number/entity
    # annotations on a selected source slice.
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(
            _payload(
                numbers={0: ["35%", "99%"]},
                entities={0: ["AMD", "NVIDIA"], 3: ["AMD"]},
            )
        ),
        candidate_label="salvageable-but-noisy-model",
    )
    assert result["state"] == "ok"
    assert result["metrics"]["claim_recall"] == 1.0
    assert result["metrics"]["analysis_semantic_recall"] == 1.0
    assert result["metrics"]["grounding_precision"] < 1.0
    assert result["counts"]["emitted_claims"] == 4
    assert result["counts"]["grounded_claims"] == 4
    assert result["counts"]["emitted_numbers"] == 2
    assert result["counts"]["grounded_numbers"] == 1
    assert result["counts"]["emitted_entities"] == 3
    assert result["counts"]["evidence_grounded_entities"] == 2


def _observation(
    *,
    latency_ms=1200,
    input_tokens=12000,
    output_tokens=1800,
    effective_cost_microusd=42000,
    cost_basis="marginal_api",
):
    return {
        "schema": OBSERVATION_SCHEMA,
        "latency_ms": latency_ms,
        "latency_source": "operator_wall_clock",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "token_source": "provider_reported",
        "effective_cost_microusd": effective_cost_microusd,
        "cost_basis": cost_basis,
    }


def test_run_economics_are_aggregated_but_do_not_change_quality_score():
    baseline = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    observed = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-b",
        observation=_observation(),
    )
    assert baseline["overall_score"] == observed["overall_score"] == 1.0

    aggregate = aggregate_results([baseline, observed])
    by_label = {
        row["candidate_label"]: row
        for row in aggregate["candidates"]
    }
    assert by_label["model-a"]["run_observations"]["observed_case_count"] == 0
    economics = by_label["model-b"]["run_observations"]
    assert economics["observed_case_count"] == 1
    assert economics["mean_latency_ms"] == 1200
    assert economics["mean_input_tokens"] == 12000
    assert economics["mean_output_tokens"] == 1800
    assert economics["mean_effective_cost_microusd"] == 42000
    assert economics["cost_bases"] == ["marginal_api"]
    assert aggregate["promotion_authority"] == "none"


def test_run_observation_rejects_cost_value_without_cost_basis():
    observation = _observation()
    observation["cost_basis"] = "unavailable"
    try:
        score_raw_output(
            _case(),
            BODY,
            json.dumps(_payload()),
            candidate_label="model-a",
            observation=observation,
        )
    except ValueError as exc:
        assert "cost value/basis disagree" in str(exc)
    else:
        raise AssertionError("benchmark must not accept ambiguous cost semantics")


def test_subscription_cost_basis_is_kept_distinct_from_marginal_api_cost():
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="subscription-model",
        observation=_observation(
            effective_cost_microusd=9000,
            cost_basis="amortized_subscription",
        ),
    )
    aggregate = aggregate_results([result])
    economics = aggregate["candidates"][0]["run_observations"]
    assert economics["cost_bases"] == ["amortized_subscription"]
    assert economics["provenance_state"] == "operator_supplied_observation"


def test_semantic_precision_penalizes_extra_unmatched_analysis_rows():
    analysis = _analysis(
        forecasts=[
            {
                "statement": "Supply is expected to normalize by the December quarter.",
                "horizon": "December quarter",
                "confidence": "",
                "support_claim_indices": [1],
            },
            {
                "statement": "General conditions could matter later.",
                "horizon": "future",
                "confidence": "low",
                "support_claim_indices": [1],
            },
        ]
    )
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload(analysis=analysis)),
        candidate_label="verbose-model",
    )
    assert result["state"] == "ok"
    assert result["metrics"]["analysis_semantic_recall"] == 1.0
    assert result["metrics"]["analysis_semantic_precision"] == 0.75
    assert result["counts"]["expected_analysis_semantics"] == 3
    assert result["counts"]["matched_analysis_semantics"] == 3
    assert result["counts"]["observed_analysis_semantic_rows"] == 4
    assert result["overall_score"] < 1.0


def test_aggregate_refuses_cross_generation_receipt():
    first = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    second = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-b",
    )
    second["benchmark_contract_sha256"] = "0" * 64
    try:
        aggregate_results([first, second])
    except ValueError as exc:
        assert "contract hash is invalid" in str(exc)
    else:
        raise AssertionError("benchmark generations must never be mixed")


def test_aggregate_exposes_frozen_benchmark_generation():
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_payload()),
        candidate_label="model-a",
    )
    aggregate = aggregate_results([result])
    assert aggregate["benchmark_version"] == BENCHMARK_VERSION
    assert aggregate["benchmark_contract_sha256"] == BENCHMARK_CONTRACT_SHA256
