"""Deterministic quality benchmark for grounded Research Intelligence outputs.

This is an evaluation harness, not a model router or source store.  Real source
bodies and gold annotations stay in private operator inputs.  Results retain only
hashes, counts, and scores so licensed text is not copied into benchmark receipts.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from statistics import mean
from typing import Any, Iterable

from engine.qual_extraction import citation_normalize, quote_span_verified

from .extractor import _identity, build_prompt, parse_model_output
from .schema import validate_rio

CASE_SCHEMA = "mastermind.research_intelligence.benchmark_case.v1"
RESULT_SCHEMA = "mastermind.research_intelligence.benchmark_result.v1"
AGGREGATE_SCHEMA = "mastermind.research_intelligence.benchmark_aggregate.v1"
REQUEST_SCHEMA = "mastermind.research_intelligence.benchmark_request.v1"

_DIRECTIONS = {"bullish", "bearish", "mixed", "neutral", "unclear"}
_ANALYSIS_FIELDS = (
    "assumptions",
    "forecasts",
    "catalysts",
    "falsifiers",
    "counterarguments",
    "implications",
    "uncertainties",
)
_METRIC_KEYS = (
    "validity",
    "claim_recall",
    "number_recall",
    "entity_recall",
    "thesis_support_recall",
    "analysis_category_recall",
    "direction_accuracy",
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _norm(value: Any) -> str:
    return " ".join(citation_normalize(str(value or "")).split())


def _ratio(hits: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(hits / total, 6)


def _mean_available(values: Iterable[float | None]) -> float:
    present = [float(value) for value in values if value is not None]
    return round(mean(present), 6) if present else 0.0


def _indices(value: Any, claim_count: int, *, label: str) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    out: list[int] = []
    for raw in value:
        if type(raw) is not int or raw < 0 or raw >= claim_count:
            raise ValueError(f"{label} contains an invalid claim index")
        if raw not in out:
            out.append(raw)
    return out


def validate_case(case: Any, source_body: str) -> dict[str, Any]:
    """Normalize one private benchmark case and bind it to exact source bytes."""
    if not isinstance(case, dict) or case.get("schema") != CASE_SCHEMA:
        raise ValueError("unexpected benchmark case schema")
    case_id = str(case.get("case_id") or "").strip()
    if not case_id or len(case_id) > 240:
        raise ValueError("case_id is required")
    if not isinstance(source_body, str) or not source_body.strip():
        raise ValueError("source_body is required")
    source_hash = _sha256_text(source_body)
    expected_hash = str(case.get("source_content_sha256") or "").strip()
    if expected_hash != source_hash:
        raise ValueError("benchmark case source hash does not match source body")

    document = case.get("document")
    if not isinstance(document, dict):
        raise ValueError("benchmark case document is required")
    identity = _identity(document, source_body)

    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise ValueError("benchmark case expected block is required")
    raw_claims = expected.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise ValueError("benchmark case requires expected claims")

    claims: list[dict[str, Any]] = []
    for raw in raw_claims:
        if not isinstance(raw, dict):
            raise ValueError("expected claim must be an object")
        quote = str(raw.get("quote_span") or "")
        if not quote_span_verified(source_body, quote, require_complete_clause=True):
            raise ValueError("expected claim quote is not grounded in source body")
        numbers = [str(x) for x in raw.get("numbers", []) if str(x)]
        entities = [str(x) for x in raw.get("entities", []) if str(x)]
        for number in numbers:
            if not quote_span_verified(quote, number, minimum_chars=1):
                raise ValueError("expected number is not grounded in its claim quote")
        for entity in entities:
            if not quote_span_verified(quote, entity, minimum_chars=1):
                raise ValueError("expected entity is not grounded in its claim quote")
        claims.append(
            {
                "quote_span": quote,
                "numbers": list(dict.fromkeys(numbers)),
                "entities": list(dict.fromkeys(entities)),
            }
        )

    claim_count = len(claims)
    thesis_support = _indices(
        expected.get("thesis_support_claim_indices"),
        claim_count,
        label="thesis_support_claim_indices",
    )
    direction = str(expected.get("thesis_direction") or "").strip().lower()
    if direction and direction not in _DIRECTIONS:
        raise ValueError("unsupported expected thesis direction")

    raw_support = expected.get("analysis_support") or {}
    if not isinstance(raw_support, dict):
        raise ValueError("analysis_support must be an object")
    analysis_support: dict[str, list[list[int]]] = {}
    unknown = set(raw_support) - set(_ANALYSIS_FIELDS)
    if unknown:
        raise ValueError(f"unsupported analysis_support fields: {sorted(unknown)!r}")
    for field in _ANALYSIS_FIELDS:
        entries = raw_support.get(field) or []
        if not isinstance(entries, list):
            raise ValueError(f"analysis_support.{field} must be a list")
        normalized_entries: list[list[int]] = []
        for index, entry in enumerate(entries):
            support = _indices(
                entry,
                claim_count,
                label=f"analysis_support.{field}[{index}]",
            )
            if not support:
                raise ValueError("analysis support expectation cannot be empty")
            normalized_entries.append(support)
        analysis_support[field] = normalized_entries

    return {
        "schema": CASE_SCHEMA,
        "case_id": case_id,
        "source_content_sha256": source_hash,
        "document": identity,
        "expected": {
            "claims": claims,
            "thesis_direction": direction,
            "thesis_support_claim_indices": thesis_support,
            "analysis_support": analysis_support,
        },
    }


def build_benchmark_request(case: Any, source_body: str) -> dict[str, Any]:
    """Build the exact W1 request for an operator-authorized model surface."""
    checked = validate_case(case, source_body)
    system, user = build_prompt(checked["document"], source_body)
    return {
        "schema": REQUEST_SCHEMA,
        "case_id": checked["case_id"],
        "source_content_sha256": checked["source_content_sha256"],
        "visibility": "private_source_bound",
        "system_prompt": system,
        "user_prompt": user,
        "prompt_sha256": _sha256_text(system + "\n" + user),
    }


def _expected_counts(checked: dict[str, Any]) -> dict[str, int]:
    claims = checked["expected"]["claims"]
    return {
        "claims": len(claims),
        "numbers": sum(len(row["numbers"]) for row in claims),
        "entities": sum(len(row["entities"]) for row in claims),
        "thesis_support": len(checked["expected"]["thesis_support_claim_indices"]),
        "analysis_categories": sum(
            len(rows) for rows in checked["expected"]["analysis_support"].values()
        ),
        "direction": 1 if checked["expected"]["thesis_direction"] else 0,
    }


def _zero_metrics(checked: dict[str, Any]) -> dict[str, float | None]:
    counts = _expected_counts(checked)
    return {
        "validity": 0.0,
        "claim_recall": 0.0 if counts["claims"] else None,
        "number_recall": 0.0 if counts["numbers"] else None,
        "entity_recall": 0.0 if counts["entities"] else None,
        "thesis_support_recall": 0.0 if counts["thesis_support"] else None,
        "analysis_category_recall": 0.0 if counts["analysis_categories"] else None,
        "direction_accuracy": 0.0 if counts["direction"] else None,
    }


def _supported_gold_indices(
    support: list[int],
    output_to_gold: dict[int, int],
) -> set[int]:
    return {output_to_gold[index] for index in support if index in output_to_gold}


def score_rio(case: Any, source_body: str, rio: Any) -> dict[str, Any]:
    """Score one already-grounded RIO against exact private gold annotations."""
    checked = validate_case(case, source_body)
    obj = validate_rio(
        rio,
        expected_document_id=checked["document"]["id"],
        expected_document=checked["document"],
    )
    gold_claims = checked["expected"]["claims"]
    gold_by_quote = {_norm(row["quote_span"]): index for index, row in enumerate(gold_claims)}

    output_to_gold: dict[int, int] = {}
    output_by_gold: dict[int, dict[str, Any]] = {}
    for output_index, claim in enumerate(obj["claims"]):
        gold_index = gold_by_quote.get(_norm(claim["statement"]))
        if gold_index is not None and gold_index not in output_by_gold:
            output_to_gold[output_index] = gold_index
            output_by_gold[gold_index] = claim

    claim_hits = len(output_by_gold)
    number_hits = 0
    number_total = 0
    entity_hits = 0
    entity_total = 0
    for gold_index, gold in enumerate(gold_claims):
        candidate = output_by_gold.get(gold_index)
        candidate_numbers = set(candidate["numbers"]) if candidate else set()
        candidate_entities = {str(x).casefold() for x in candidate["entities"]} if candidate else set()
        for number in gold["numbers"]:
            number_total += 1
            number_hits += int(number in candidate_numbers)
        for entity in gold["entities"]:
            entity_total += 1
            entity_hits += int(entity.casefold() in candidate_entities)

    thesis = obj["analysis"]["thesis"]
    thesis_gold = _supported_gold_indices(thesis["support_claim_indices"], output_to_gold)
    expected_thesis = set(checked["expected"]["thesis_support_claim_indices"])
    thesis_hits = len(expected_thesis & thesis_gold)

    category_hits = 0
    category_total = 0
    for field, expectations in checked["expected"]["analysis_support"].items():
        observed_sets = [
            _supported_gold_indices(row["support_claim_indices"], output_to_gold)
            for row in obj["analysis"][field]
        ]
        for expectation in expectations:
            category_total += 1
            target = set(expectation)
            category_hits += int(any(target <= observed for observed in observed_sets))

    expected_direction = checked["expected"]["thesis_direction"]
    metrics: dict[str, float | None] = {
        "validity": 1.0,
        "claim_recall": _ratio(claim_hits, len(gold_claims)),
        "number_recall": _ratio(number_hits, number_total),
        "entity_recall": _ratio(entity_hits, entity_total),
        "thesis_support_recall": _ratio(thesis_hits, len(expected_thesis)),
        "analysis_category_recall": _ratio(category_hits, category_total),
        "direction_accuracy": (
            float(thesis["direction"] == expected_direction) if expected_direction else None
        ),
    }
    return {
        "case_id": checked["case_id"],
        "source_content_sha256": checked["source_content_sha256"],
        "metrics": metrics,
        "overall_score": _mean_available(metrics.values()),
        "counts": {
            "expected_claims": len(gold_claims),
            "matched_claims": claim_hits,
            "expected_numbers": number_total,
            "matched_numbers": number_hits,
            "expected_entities": entity_total,
            "matched_entities": entity_hits,
            "expected_analysis_categories": category_total,
            "matched_analysis_categories": category_hits,
        },
    }


def score_raw_output(
    case: Any,
    source_body: str,
    raw_output: str,
    *,
    candidate_label: str,
) -> dict[str, Any]:
    """Re-ground raw model text through W1, then emit a text-free benchmark receipt."""
    checked = validate_case(case, source_body)
    label = str(candidate_label or "").strip()
    if not label or len(label) > 240:
        raise ValueError("candidate_label is required")
    system, user = build_prompt(checked["document"], source_body)
    base = {
        "schema": RESULT_SCHEMA,
        "case_id": checked["case_id"],
        "candidate_label": label,
        "provenance_state": "operator_label_only",
        "source_content_sha256": checked["source_content_sha256"],
        "prompt_sha256": _sha256_text(system + "\n" + user),
        "output_sha256": _sha256_text(str(raw_output or "")),
    }
    try:
        rio = parse_model_output(
            str(raw_output or ""),
            expected_document_id=checked["document"]["id"],
            expected_document=checked["document"],
            source_body=source_body,
        )
        scored = score_rio(checked, source_body, rio)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        metrics = _zero_metrics(checked)
        return {
            **base,
            "state": "invalid_output",
            "error_class": type(exc).__name__[:120],
            "metrics": metrics,
            "overall_score": _mean_available(metrics.values()),
            "counts": _expected_counts(checked),
        }
    return {
        **base,
        "state": "ok",
        "metrics": scored["metrics"],
        "overall_score": scored["overall_score"],
        "counts": scored["counts"],
    }


def aggregate_results(results: Iterable[Any]) -> dict[str, Any]:
    """Aggregate text-free case receipts by operator-provided candidate label."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in results:
        if not isinstance(raw, dict) or raw.get("schema") != RESULT_SCHEMA:
            raise ValueError("unexpected benchmark result schema")
        label = str(raw.get("candidate_label") or "").strip()
        metrics = raw.get("metrics")
        if not label or not isinstance(metrics, dict):
            raise ValueError("benchmark result is malformed")
        groups[label].append(raw)
    rows: list[dict[str, Any]] = []
    for label, items in groups.items():
        metric_means: dict[str, float | None] = {}
        for key in _METRIC_KEYS:
            values = [item["metrics"].get(key) for item in items]
            present = [float(value) for value in values if value is not None]
            metric_means[key] = round(mean(present), 6) if present else None
        rows.append(
            {
                "candidate_label": label,
                "provenance_state": "operator_label_only",
                "case_count": len(items),
                "valid_case_count": sum(item.get("state") == "ok" for item in items),
                "mean_overall_score": round(
                    mean(float(item.get("overall_score") or 0.0) for item in items), 6
                ),
                "metrics": metric_means,
            }
        )
    rows.sort(key=lambda row: (-row["mean_overall_score"], row["candidate_label"]))
    return {
        "schema": AGGREGATE_SCHEMA,
        "ranking_basis": "private_gold_deterministic_metrics",
        "candidates": rows,
    }
