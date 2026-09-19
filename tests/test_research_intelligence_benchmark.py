from __future__ import annotations

import hashlib
import json
import stat

from engine.research_intelligence.benchmark import (
    CASE_SCHEMA,
    aggregate_results,
    build_benchmark_request,
    score_raw_output,
    score_rio,
)
from engine.research_intelligence.extractor import _identity
from engine.research_intelligence.schema import SCHEMA
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
    assert BODY in request["user_prompt"]
    assert request["source_content_sha256"] == hashlib.sha256(BODY.encode()).hexdigest()
    assert len(request["gold_contract_sha256"]) == 64


def test_perfect_grounded_output_scores_all_available_dimensions():
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_rio()),
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


def test_missing_claim_reduces_recall_and_category_score():
    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(_rio(include_falsifier=False)),
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
        "not json and not a grounded RIO",
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
        score_raw_output(case, BODY, json.dumps(_rio()), candidate_label="model-a")
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


def test_aggregate_ranks_by_mean_score_without_source_text():
    good = score_raw_output(
        _case(),
        BODY,
        json.dumps(_rio()),
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
        json.dumps(_rio()),
        candidate_label="model-a",
    )
    other_case = _case()
    other_case["case_id"] = "fixture-amd-002"
    second = score_raw_output(
        other_case,
        BODY,
        json.dumps(_rio()),
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
        json.dumps(_rio()),
        candidate_label="model-a",
    )
    second = score_raw_output(
        _case(),
        BODY,
        json.dumps(_rio()),
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
        json.dumps(_rio()),
        candidate_label="model-a",
    )
    changed_gold = _case()
    changed_gold["expected"]["thesis_direction"] = "bearish"
    second = score_raw_output(
        changed_gold,
        BODY,
        json.dumps(_rio()),
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
        json.dumps(_rio()),
        candidate_label="model-a",
    )
    second = score_raw_output(
        _case(),
        BODY,
        json.dumps(_rio()),
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
    rio = _rio()
    rio["analysis"]["thesis"]["summary"] = "The note presents a constructive server outlook."
    rio["analysis"]["thesis"]["mechanism"] = ["fundamental conditions support the thesis"]
    rio["analysis"]["forecasts"][0]["statement"] = "Conditions may improve later."
    rio["analysis"]["forecasts"][0]["horizon"] = ""
    rio["analysis"]["catalysts"][0]["statement"] = "A future event could matter."
    rio["analysis"]["falsifiers"][0]["statement"] = "The thesis could fail under adverse conditions."

    result = score_raw_output(
        _case(),
        BODY,
        json.dumps(rio),
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
        json.dumps(_rio()),
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

    rio = _rio()
    rio["analysis"]["forecasts"] = [
        {
            "statement": (
                "Supply should normalize by December and the October launch "
                "is the next catalyst."
            ),
            "horizon": "December and October",
            "confidence": "moderate",
            "support_claim_indices": [1, 2],
        }
    ]
    rio["analysis"]["catalysts"] = []
    rio["analysis"]["falsifiers"] = []

    result = score_raw_output(
        case,
        BODY,
        json.dumps(rio),
        candidate_label="one-row-for-two-expectations",
    )
    assert result["state"] == "ok"
    assert result["counts"]["expected_analysis_categories"] == 2
    assert result["counts"]["matched_analysis_categories"] == 1
    assert result["counts"]["expected_analysis_semantics"] == 2
    assert result["counts"]["matched_analysis_semantics"] == 1
    assert result["metrics"]["analysis_category_recall"] == 0.5
    assert result["metrics"]["analysis_semantic_recall"] == 0.5
