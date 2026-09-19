from __future__ import annotations

import hashlib
import json

from engine.research_intelligence.benchmark import (
    CASE_SCHEMA,
    aggregate_results,
    build_benchmark_request,
    score_raw_output,
)
from engine.research_intelligence.extractor import _identity
from engine.research_intelligence.schema import SCHEMA


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
            "analysis_support": {
                "forecasts": [[1]],
                "catalysts": [[2]],
                "falsifiers": [[3]],
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
    assert result["provenance_state"] == "operator_label_only"


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
    assert BODY not in json.dumps(aggregate)
