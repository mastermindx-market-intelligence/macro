"""Deterministic quality benchmark for grounded Research Intelligence outputs.

This is an evaluation harness, not a model router or source store. Real source
bodies and gold annotations stay in private operator inputs. Results retain only
hashes, counts, and scores so licensed text is not copied into benchmark receipts.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from statistics import mean
from typing import Any, Callable, Iterable

from engine.qual_extraction import citation_normalize, quote_span_verified

from .extractor import _identity, _parse_json, build_prompt, parse_model_output
from .schema import validate_rio

CASE_SCHEMA = "mastermind.research_intelligence.benchmark_case.v1"
RESULT_SCHEMA = "mastermind.research_intelligence.benchmark_result.v1"
AGGREGATE_SCHEMA = "mastermind.research_intelligence.benchmark_aggregate.v1"
REQUEST_SCHEMA = "mastermind.research_intelligence.benchmark_request.v1"
OBSERVATION_SCHEMA = "mastermind.research_intelligence.benchmark_observation.v1"

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
    "grounding_precision",
    "thesis_support_recall",
    "thesis_semantic_accuracy",
    "analysis_category_recall",
    "analysis_semantic_recall",
    "direction_accuracy",
)
_COUNT_KEYS = (
    "expected_claims",
    "matched_claims",
    "expected_numbers",
    "matched_numbers",
    "expected_entities",
    "matched_entities",
    "emitted_claims",
    "grounded_claims",
    "emitted_numbers",
    "grounded_numbers",
    "emitted_entities",
    "evidence_grounded_entities",
    "emitted_analysis_rows",
    "grounded_analysis_rows",
    "expected_thesis_support",
    "matched_thesis_support",
    "thesis_semantic_expected",
    "thesis_semantic_correct",
    "expected_analysis_categories",
    "matched_analysis_categories",
    "expected_analysis_semantics",
    "matched_analysis_semantics",
    "direction_expected",
    "direction_correct",
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return _sha256_text(payload)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


_LATENCY_SOURCES = {"operator_wall_clock", "provider_reported", "unavailable"}
_TOKEN_SOURCES = {"provider_reported", "operator_measured", "unavailable"}
_COST_BASES = {"marginal_api", "amortized_subscription", "unavailable"}


def _bounded_optional_int(
    value: Any,
    *,
    label: str,
    maximum: int,
) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0 or value > maximum:
        raise ValueError(f"{label} is outside its integer boundary")
    return value


def normalize_observation(value: Any) -> dict[str, Any] | None:
    """Normalize operator-supplied run economics; never grants serving provenance."""
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("schema") != OBSERVATION_SCHEMA:
        raise ValueError("unexpected benchmark observation schema")
    expected_keys = {
        "schema",
        "latency_ms",
        "latency_source",
        "input_tokens",
        "output_tokens",
        "token_source",
        "effective_cost_microusd",
        "cost_basis",
    }
    if set(value) != expected_keys:
        raise ValueError("benchmark observation fields are invalid")

    latency_ms = _bounded_optional_int(
        value.get("latency_ms"),
        label="latency_ms",
        maximum=3_600_000,
    )
    input_tokens = _bounded_optional_int(
        value.get("input_tokens"),
        label="input_tokens",
        maximum=100_000_000,
    )
    output_tokens = _bounded_optional_int(
        value.get("output_tokens"),
        label="output_tokens",
        maximum=10_000_000,
    )
    effective_cost = _bounded_optional_int(
        value.get("effective_cost_microusd"),
        label="effective_cost_microusd",
        maximum=10_000_000_000,
    )
    latency_source = value.get("latency_source")
    token_source = value.get("token_source")
    cost_basis = value.get("cost_basis")
    if latency_source not in _LATENCY_SOURCES:
        raise ValueError("unsupported latency_source")
    if token_source not in _TOKEN_SOURCES:
        raise ValueError("unsupported token_source")
    if cost_basis not in _COST_BASES:
        raise ValueError("unsupported cost_basis")
    if (latency_ms is None) != (latency_source == "unavailable"):
        raise ValueError("latency value/source disagree")
    if (
        (input_tokens is None and output_tokens is None)
        != (token_source == "unavailable")
    ):
        raise ValueError("token values/source disagree")
    if (effective_cost is None) != (cost_basis == "unavailable"):
        raise ValueError("cost value/basis disagree")
    return {
        "schema": OBSERVATION_SCHEMA,
        "latency_ms": latency_ms,
        "latency_source": latency_source,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "token_source": token_source,
        "effective_cost_microusd": effective_cost,
        "cost_basis": cost_basis,
    }


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


def _strings(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    out: list[str] = []
    for raw in value:
        if not isinstance(raw, str) or raw != raw.strip() or not raw:
            raise ValueError(f"{label} contains invalid text")
        if raw not in out:
            out.append(raw)
    return out


def _concept_groups(value: Any, *, label: str) -> list[list[str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    groups: list[list[str]] = []
    for group_index, raw_group in enumerate(value):
        alternatives = _strings(
            raw_group,
            label=f"{label}[{group_index}]",
        )
        normalized = []
        for alternative in alternatives:
            text = _norm(alternative)
            if not text:
                raise ValueError(f"{label}[{group_index}] contains empty normalized text")
            if text not in normalized:
                normalized.append(text)
        if not normalized:
            raise ValueError(f"{label}[{group_index}] requires at least one alternative")
        groups.append(normalized)
    return groups


def _contains_phrase(haystack: str, phrase: str) -> bool:
    haystack_tokens = _norm(haystack).split()
    phrase_tokens = _norm(phrase).split()
    if not phrase_tokens or len(phrase_tokens) > len(haystack_tokens):
        return False
    width = len(phrase_tokens)
    return any(
        haystack_tokens[index : index + width] == phrase_tokens
        for index in range(len(haystack_tokens) - width + 1)
    )


def _concepts_match(text: str, groups: list[list[str]]) -> bool:
    return bool(groups) and all(
        any(_contains_phrase(text, alternative) for alternative in alternatives)
        for alternatives in groups
    )


def _analysis_row_text(field: str, row: dict[str, Any]) -> str:
    pieces = [str(row.get("statement") or "")]
    if field == "forecasts":
        pieces.extend(
            [
                str(row.get("horizon") or ""),
                str(row.get("confidence") or ""),
            ]
        )
    elif field == "implications":
        pieces.extend(str(value) for value in row.get("assets") or [])
        pieces.append(str(row.get("direction") or ""))
        pieces.append(str(row.get("order") or ""))
    return " ".join(piece for piece in pieces if piece)


def _analysis_row_count(rio: dict[str, Any]) -> int:
    analysis = rio["analysis"]
    count = 1  # thesis
    count += sum(len(analysis.get(field) or []) for field in _ANALYSIS_FIELDS)
    count += int(bool((analysis.get("belief_delta") or {}).get("statement")))
    count += int(bool((analysis.get("consensus_relation") or {}).get("statement")))
    return count


def _grounding_counts(
    raw_rio: dict[str, Any],
    grounded_rio: dict[str, Any],
) -> dict[str, int]:
    emitted_claims = len(raw_rio["claims"])
    grounded_claims = len(grounded_rio["claims"])
    emitted_numbers = sum(len(claim["numbers"]) for claim in raw_rio["claims"])
    grounded_numbers = sum(len(claim["numbers"]) for claim in grounded_rio["claims"])
    emitted_entities = sum(len(claim["entities"]) for claim in raw_rio["claims"])
    evidence_grounded_entities = 0
    for claim in grounded_rio["claims"]:
        for entity in claim["entities"]:
            if any(
                quote_span_verified(evidence["quote_span"], entity, minimum_chars=1)
                for evidence in claim["evidence"]
            ):
                evidence_grounded_entities += 1
    return {
        "emitted_claims": emitted_claims,
        "grounded_claims": grounded_claims,
        "emitted_numbers": emitted_numbers,
        "grounded_numbers": grounded_numbers,
        "emitted_entities": emitted_entities,
        "evidence_grounded_entities": evidence_grounded_entities,
        "emitted_analysis_rows": _analysis_row_count(raw_rio),
        "grounded_analysis_rows": _analysis_row_count(grounded_rio),
    }


def _grounding_precision(counts: dict[str, int]) -> float:
    ratios: list[float] = []
    for emitted_key, grounded_key in (
        ("emitted_claims", "grounded_claims"),
        ("emitted_numbers", "grounded_numbers"),
        ("emitted_entities", "evidence_grounded_entities"),
        ("emitted_analysis_rows", "grounded_analysis_rows"),
    ):
        emitted = counts[emitted_key]
        if emitted:
            ratios.append(counts[grounded_key] / emitted)
    return round(mean(ratios), 6) if ratios else 1.0


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
    seen_quotes: set[str] = set()
    for claim_index, raw in enumerate(raw_claims):
        if not isinstance(raw, dict):
            raise ValueError("expected claim must be an object")
        quote = raw.get("quote_span")
        if not isinstance(quote, str) or quote != quote.strip() or not quote:
            raise ValueError("expected claim quote must be exact non-empty text")
        if not quote_span_verified(source_body, quote, require_complete_clause=True):
            raise ValueError("expected claim quote is not grounded in source body")
        normalized_quote = _norm(quote)
        if normalized_quote in seen_quotes:
            raise ValueError("benchmark case contains duplicate expected claim quotes")
        seen_quotes.add(normalized_quote)
        numbers = _strings(raw.get("numbers"), label=f"claims[{claim_index}].numbers")
        entities = _strings(raw.get("entities"), label=f"claims[{claim_index}].entities")
        for number in numbers:
            if not quote_span_verified(quote, number, minimum_chars=1):
                raise ValueError("expected number is not grounded in its claim quote")
        for entity in entities:
            if not quote_span_verified(quote, entity, minimum_chars=1):
                raise ValueError("expected entity is not grounded in its claim quote")
        claims.append(
            {
                "quote_span": quote,
                "numbers": numbers,
                "entities": entities,
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

    thesis_concepts = _concept_groups(
        expected.get("thesis_concepts"),
        label="thesis_concepts",
    )

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

    raw_semantics = expected.get("analysis_semantics") or {}
    if not isinstance(raw_semantics, dict):
        raise ValueError("analysis_semantics must be an object")
    unknown_semantics = set(raw_semantics) - set(_ANALYSIS_FIELDS)
    if unknown_semantics:
        raise ValueError(
            f"unsupported analysis_semantics fields: {sorted(unknown_semantics)!r}"
        )
    analysis_semantics: dict[str, list[dict[str, Any]]] = {}
    for field in _ANALYSIS_FIELDS:
        entries = raw_semantics.get(field) or []
        if not isinstance(entries, list):
            raise ValueError(f"analysis_semantics.{field} must be a list")
        normalized_entries: list[dict[str, Any]] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"analysis_semantics.{field}[{index}] must be an object")
            support = _indices(
                entry.get("support_claim_indices"),
                claim_count,
                label=f"analysis_semantics.{field}[{index}].support_claim_indices",
            )
            concepts = _concept_groups(
                entry.get("concept_groups"),
                label=f"analysis_semantics.{field}[{index}].concept_groups",
            )
            if not support or not concepts:
                raise ValueError("analysis semantic expectation requires support and concepts")
            normalized_entries.append(
                {
                    "support_claim_indices": support,
                    "concept_groups": concepts,
                }
            )
        analysis_semantics[field] = normalized_entries

    return {
        "schema": CASE_SCHEMA,
        "case_id": case_id,
        "source_content_sha256": source_hash,
        "document": identity,
        "expected": {
            "claims": claims,
            "thesis_direction": direction,
            "thesis_support_claim_indices": thesis_support,
            "thesis_concepts": thesis_concepts,
            "analysis_support": analysis_support,
            "analysis_semantics": analysis_semantics,
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
        "gold_contract_sha256": _sha256_json(checked["expected"]),
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
        "thesis_semantic": 1 if checked["expected"]["thesis_concepts"] else 0,
        "analysis_categories": sum(
            len(rows) for rows in checked["expected"]["analysis_support"].values()
        ),
        "analysis_semantics": sum(
            len(rows) for rows in checked["expected"]["analysis_semantics"].values()
        ),
        "direction": 1 if checked["expected"]["thesis_direction"] else 0,
    }


def _score_counts(
    checked: dict[str, Any],
    *,
    claim_hits: int = 0,
    number_hits: int = 0,
    entity_hits: int = 0,
    thesis_hits: int = 0,
    thesis_semantic_correct: int = 0,
    category_hits: int = 0,
    semantic_hits: int = 0,
    direction_correct: int = 0,
    grounding_counts: dict[str, int] | None = None,
) -> dict[str, int]:
    counts = _expected_counts(checked)
    grounding = grounding_counts or {
        "emitted_claims": 0,
        "grounded_claims": 0,
        "emitted_numbers": 0,
        "grounded_numbers": 0,
        "emitted_entities": 0,
        "evidence_grounded_entities": 0,
        "emitted_analysis_rows": 0,
        "grounded_analysis_rows": 0,
    }
    return {
        "expected_claims": counts["claims"],
        "matched_claims": claim_hits,
        "expected_numbers": counts["numbers"],
        "matched_numbers": number_hits,
        "expected_entities": counts["entities"],
        "matched_entities": entity_hits,
        **grounding,
        "expected_thesis_support": counts["thesis_support"],
        "matched_thesis_support": thesis_hits,
        "thesis_semantic_expected": counts["thesis_semantic"],
        "thesis_semantic_correct": thesis_semantic_correct,
        "expected_analysis_categories": counts["analysis_categories"],
        "matched_analysis_categories": category_hits,
        "expected_analysis_semantics": counts["analysis_semantics"],
        "matched_analysis_semantics": semantic_hits,
        "direction_expected": counts["direction"],
        "direction_correct": direction_correct,
    }


def _metrics_from_counts(
    state: str,
    counts: dict[str, int],
) -> dict[str, float | None]:
    if state not in {"ok", "invalid_output"}:
        raise ValueError("unsupported benchmark result state")
    valid = state == "ok"
    return {
        "validity": 1.0 if valid else 0.0,
        "claim_recall": (
            _ratio(counts["matched_claims"], counts["expected_claims"])
            if valid
            else (0.0 if counts["expected_claims"] else None)
        ),
        "number_recall": (
            _ratio(counts["matched_numbers"], counts["expected_numbers"])
            if valid
            else (0.0 if counts["expected_numbers"] else None)
        ),
        "entity_recall": (
            _ratio(counts["matched_entities"], counts["expected_entities"])
            if valid
            else (0.0 if counts["expected_entities"] else None)
        ),
        "grounding_precision": (
            _grounding_precision(counts) if valid else 0.0
        ),
        "thesis_support_recall": (
            _ratio(
                counts["matched_thesis_support"],
                counts["expected_thesis_support"],
            )
            if valid
            else (0.0 if counts["expected_thesis_support"] else None)
        ),
        "thesis_semantic_accuracy": (
            float(counts["thesis_semantic_correct"])
            if valid and counts["thesis_semantic_expected"]
            else (0.0 if counts["thesis_semantic_expected"] else None)
        ),
        "analysis_category_recall": (
            _ratio(
                counts["matched_analysis_categories"],
                counts["expected_analysis_categories"],
            )
            if valid
            else (0.0 if counts["expected_analysis_categories"] else None)
        ),
        "analysis_semantic_recall": (
            _ratio(
                counts["matched_analysis_semantics"],
                counts["expected_analysis_semantics"],
            )
            if valid
            else (0.0 if counts["expected_analysis_semantics"] else None)
        ),
        "direction_accuracy": (
            float(counts["direction_correct"])
            if valid and counts["direction_expected"]
            else (0.0 if counts["direction_expected"] else None)
        ),
    }


def _zero_metrics(checked: dict[str, Any]) -> dict[str, float | None]:
    return _metrics_from_counts("invalid_output", _score_counts(checked))


def _supported_gold_indices(
    support: list[int],
    output_to_gold: dict[int, int],
) -> set[int]:
    return {output_to_gold[index] for index in support if index in output_to_gold}


def _maximum_bipartite_matches(
    left_count: int,
    right_count: int,
    can_match: Callable[[int, int], bool],
) -> int:
    """Maximum one-to-one matches; one output row cannot satisfy multiple gold rows."""
    right_to_left: dict[int, int] = {}

    def augment(left: int, seen: set[int]) -> bool:
        for right in range(right_count):
            if right in seen or not can_match(left, right):
                continue
            seen.add(right)
            owner = right_to_left.get(right)
            if owner is None or augment(owner, seen):
                right_to_left[right] = left
                return True
        return False

    matched = 0
    for left in range(left_count):
        matched += int(augment(left, set()))
    return matched


def _score_grounded(
    checked: dict[str, Any],
    obj: dict[str, Any],
    *,
    grounding_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
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
    entity_hits = 0
    for gold_index, gold in enumerate(gold_claims):
        candidate = output_by_gold.get(gold_index)
        candidate_numbers = set(candidate["numbers"]) if candidate else set()
        candidate_entities = (
            {str(x).casefold() for x in candidate["entities"]} if candidate else set()
        )
        number_hits += sum(number in candidate_numbers for number in gold["numbers"])
        entity_hits += sum(
            entity.casefold() in candidate_entities for entity in gold["entities"]
        )

    thesis = obj["analysis"]["thesis"]
    thesis_gold = _supported_gold_indices(thesis["support_claim_indices"], output_to_gold)
    expected_thesis = set(checked["expected"]["thesis_support_claim_indices"])
    thesis_hits = len(expected_thesis & thesis_gold)

    category_hits = 0
    for field, expectations in checked["expected"]["analysis_support"].items():
        observed_sets = [
            _supported_gold_indices(row["support_claim_indices"], output_to_gold)
            for row in obj["analysis"][field]
        ]
        category_hits += _maximum_bipartite_matches(
            len(expectations),
            len(observed_sets),
            lambda expected_index, observed_index: set(
                expectations[expected_index]
            )
            <= observed_sets[observed_index],
        )

    thesis_semantic_correct = 0
    thesis_concepts = checked["expected"]["thesis_concepts"]
    if thesis_concepts:
        thesis_text = " ".join(
            [
                str(thesis.get("summary") or ""),
                *(str(value) for value in thesis.get("mechanism") or []),
            ]
        )
        thesis_semantic_correct = int(_concepts_match(thesis_text, thesis_concepts))

    semantic_hits = 0
    for field, expectations in checked["expected"]["analysis_semantics"].items():
        observed = obj["analysis"][field]
        observed_support = [
            _supported_gold_indices(row["support_claim_indices"], output_to_gold)
            for row in observed
        ]
        semantic_hits += _maximum_bipartite_matches(
            len(expectations),
            len(observed),
            lambda expected_index, observed_index: (
                set(expectations[expected_index]["support_claim_indices"])
                <= observed_support[observed_index]
                and _concepts_match(
                    _analysis_row_text(field, observed[observed_index]),
                    expectations[expected_index]["concept_groups"],
                )
            ),
        )

    expected_direction = checked["expected"]["thesis_direction"]
    direction_correct = int(
        bool(expected_direction) and thesis["direction"] == expected_direction
    )
    score_counts = _score_counts(
        checked,
        claim_hits=claim_hits,
        number_hits=number_hits,
        entity_hits=entity_hits,
        thesis_hits=thesis_hits,
        thesis_semantic_correct=thesis_semantic_correct,
        category_hits=category_hits,
        semantic_hits=semantic_hits,
        direction_correct=direction_correct,
        grounding_counts=grounding_counts,
    )
    metrics = _metrics_from_counts("ok", score_counts)
    return {
        "case_id": checked["case_id"],
        "source_content_sha256": checked["source_content_sha256"],
        "metrics": metrics,
        "overall_score": _mean_available(metrics.values()),
        "counts": score_counts,
    }


def score_rio(case: Any, source_body: str, rio: Any) -> dict[str, Any]:
    """Re-ground and score one RIO against exact private gold annotations."""
    checked = validate_case(case, source_body)
    raw = json.dumps(
        rio,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    obj = parse_model_output(
        raw,
        expected_document_id=checked["document"]["id"],
        expected_document=checked["document"],
        source_body=source_body,
    )
    return _score_grounded(checked, obj)


def score_raw_output(
    case: Any,
    source_body: str,
    raw_output: str,
    *,
    candidate_label: str,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Re-ground raw model text through W1, then emit a text-free benchmark receipt."""
    checked = validate_case(case, source_body)
    label = str(candidate_label or "").strip()
    if not label or len(label) > 240:
        raise ValueError("candidate_label is required")
    system, user = build_prompt(checked["document"], source_body)
    checked_observation = normalize_observation(observation)
    base = {
        "schema": RESULT_SCHEMA,
        "case_id": checked["case_id"],
        "candidate_label": label,
        "provenance_state": "operator_label_only",
        "source_content_sha256": checked["source_content_sha256"],
        "gold_contract_sha256": _sha256_json(checked["expected"]),
        "prompt_sha256": _sha256_text(system + "\n" + user),
        "output_sha256": _sha256_text(str(raw_output or "")),
        "observation": checked_observation,
    }
    try:
        raw_obj = _parse_json(str(raw_output or ""))
        normalized_raw = validate_rio(
            raw_obj,
            expected_document_id=checked["document"]["id"],
            expected_document=checked["document"],
            require_grounded_claims=False,
        )
        rio = parse_model_output(
            str(raw_output or ""),
            expected_document_id=checked["document"]["id"],
            expected_document=checked["document"],
            source_body=source_body,
        )
        scored = _score_grounded(
            checked,
            rio,
            grounding_counts=_grounding_counts(normalized_raw, rio),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        score_counts = _score_counts(checked)
        metrics = _metrics_from_counts("invalid_output", score_counts)
        return {
            **base,
            "state": "invalid_output",
            "error_class": type(exc).__name__[:120],
            "metrics": metrics,
            "overall_score": _mean_available(metrics.values()),
            "counts": score_counts,
        }
    return {
        **base,
        "state": "ok",
        "metrics": scored["metrics"],
        "overall_score": scored["overall_score"],
        "counts": scored["counts"],
    }


def _validated_result(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != RESULT_SCHEMA:
        raise ValueError("unexpected benchmark result schema")
    label = str(raw.get("candidate_label") or "").strip()
    case_id = str(raw.get("case_id") or "").strip()
    state = raw.get("state")
    observation = normalize_observation(raw.get("observation"))
    if not label or not case_id or state not in {"ok", "invalid_output"}:
        raise ValueError("benchmark result identity/state is malformed")
    if raw.get("provenance_state") != "operator_label_only":
        raise ValueError("benchmark result provenance state is invalid")
    for field in (
        "source_content_sha256",
        "gold_contract_sha256",
        "prompt_sha256",
        "output_sha256",
    ):
        if not _is_sha256(raw.get(field)):
            raise ValueError(f"benchmark result {field} is invalid")

    counts = raw.get("counts")
    if not isinstance(counts, dict) or set(counts) != set(_COUNT_KEYS):
        raise ValueError("benchmark result counts are malformed")
    checked_counts: dict[str, int] = {}
    for key in _COUNT_KEYS:
        value = counts[key]
        if type(value) is not int or value < 0:
            raise ValueError("benchmark result count is invalid")
        checked_counts[key] = value
    for expected_key, matched_key in (
        ("expected_claims", "matched_claims"),
        ("expected_numbers", "matched_numbers"),
        ("expected_entities", "matched_entities"),
        ("emitted_claims", "grounded_claims"),
        ("emitted_numbers", "grounded_numbers"),
        ("emitted_entities", "evidence_grounded_entities"),
        ("emitted_analysis_rows", "grounded_analysis_rows"),
        ("expected_thesis_support", "matched_thesis_support"),
        ("thesis_semantic_expected", "thesis_semantic_correct"),
        ("expected_analysis_categories", "matched_analysis_categories"),
        ("expected_analysis_semantics", "matched_analysis_semantics"),
        ("direction_expected", "direction_correct"),
    ):
        if checked_counts[matched_key] > checked_counts[expected_key]:
            raise ValueError("benchmark matched count exceeds expected count")
    if checked_counts["thesis_semantic_expected"] not in {0, 1}:
        raise ValueError("benchmark thesis_semantic_expected must be 0 or 1")
    if checked_counts["thesis_semantic_correct"] not in {0, 1}:
        raise ValueError("benchmark thesis_semantic_correct must be 0 or 1")
    if checked_counts["direction_expected"] not in {0, 1}:
        raise ValueError("benchmark direction_expected must be 0 or 1")
    if checked_counts["direction_correct"] not in {0, 1}:
        raise ValueError("benchmark direction_correct must be 0 or 1")
    if state == "invalid_output" and any(
        checked_counts[key]
        for key in (
            "matched_claims",
            "matched_numbers",
            "matched_entities",
            "grounded_claims",
            "grounded_numbers",
            "evidence_grounded_entities",
            "grounded_analysis_rows",
            "matched_thesis_support",
            "thesis_semantic_correct",
            "matched_analysis_categories",
            "matched_analysis_semantics",
            "direction_correct",
        )
    ):
        raise ValueError("invalid benchmark output cannot retain matched credit")

    metrics = raw.get("metrics")
    if not isinstance(metrics, dict) or set(metrics) != set(_METRIC_KEYS):
        raise ValueError("benchmark result metrics are malformed")
    checked_metrics: dict[str, float | None] = {}
    for key in _METRIC_KEYS:
        value = metrics[key]
        if value is None:
            checked_metrics[key] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("benchmark metric must be numeric or null")
        number = float(value)
        if not math.isfinite(number) or number < 0.0 or number > 1.0:
            raise ValueError("benchmark metric is outside [0,1]")
        checked_metrics[key] = number

    recomputed_metrics = _metrics_from_counts(state, checked_counts)
    for key in _METRIC_KEYS:
        supplied = checked_metrics[key]
        expected = recomputed_metrics[key]
        if supplied is None or expected is None:
            if supplied is not expected:
                raise ValueError("benchmark metrics disagree with counts/state")
            continue
        if abs(supplied - expected) > 0.000001:
            raise ValueError("benchmark metrics disagree with counts/state")

    overall = raw.get("overall_score")
    if isinstance(overall, bool) or not isinstance(overall, (int, float)):
        raise ValueError("benchmark overall_score is invalid")
    overall_number = float(overall)
    recomputed_overall = _mean_available(recomputed_metrics.values())
    if (
        not math.isfinite(overall_number)
        or abs(overall_number - recomputed_overall) > 0.000001
    ):
        raise ValueError("benchmark overall_score disagrees with metrics")

    return {
        **raw,
        "candidate_label": label,
        "case_id": case_id,
        "metrics": recomputed_metrics,
        "overall_score": recomputed_overall,
        "counts": checked_counts,
        "observation": observation,
    }


def _mean_optional_int(values: Iterable[int | None]) -> float | None:
    present = [int(value) for value in values if value is not None]
    return round(mean(present), 3) if present else None


def _aggregate_observations(items: list[dict[str, Any]]) -> dict[str, Any]:
    observations = [item.get("observation") for item in items]
    present = [value for value in observations if isinstance(value, dict)]
    latency_sources = sorted(
        {
            value["latency_source"]
            for value in present
            if value["latency_source"] != "unavailable"
        }
    )
    token_sources = sorted(
        {
            value["token_source"]
            for value in present
            if value["token_source"] != "unavailable"
        }
    )
    cost_bases = sorted(
        {
            value["cost_basis"]
            for value in present
            if value["cost_basis"] != "unavailable"
        }
    )
    return {
        "provenance_state": "operator_supplied_observation",
        "observed_case_count": len(present),
        "mean_latency_ms": _mean_optional_int(
            value["latency_ms"] for value in present
        ),
        "mean_input_tokens": _mean_optional_int(
            value["input_tokens"] for value in present
        ),
        "mean_output_tokens": _mean_optional_int(
            value["output_tokens"] for value in present
        ),
        "mean_effective_cost_microusd": _mean_optional_int(
            value["effective_cost_microusd"] for value in present
        ),
        "latency_sources": latency_sources,
        "token_sources": token_sources,
        "cost_bases": cost_bases,
    }


def aggregate_results(results: Iterable[Any]) -> dict[str, Any]:
    """Aggregate only directly comparable, text-free case receipts by candidate."""
    groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    bindings: dict[str, tuple[str, str, str]] = {}
    metric_shapes: dict[str, tuple[bool, ...]] = {}
    expected_shapes: dict[str, tuple[int, int, int, int, int, int, int, int]] = {}

    for raw in results:
        item = _validated_result(raw)
        label = item["candidate_label"]
        case_id = item["case_id"]
        if case_id in groups[label]:
            raise ValueError("duplicate benchmark case for candidate")
        groups[label][case_id] = item

        binding = (
            item["source_content_sha256"],
            item["prompt_sha256"],
            item["gold_contract_sha256"],
        )
        prior_binding = bindings.setdefault(case_id, binding)
        if prior_binding != binding:
            raise ValueError(
                "benchmark source, prompt, or gold contract differs across candidates"
            )

        shape = tuple(item["metrics"][key] is None for key in _METRIC_KEYS)
        prior_shape = metric_shapes.setdefault(case_id, shape)
        if prior_shape != shape:
            raise ValueError("benchmark metric applicability differs across candidates")

        counts = item["counts"]
        expected_shape = (
            counts["expected_claims"],
            counts["expected_numbers"],
            counts["expected_entities"],
            counts["expected_thesis_support"],
            counts["thesis_semantic_expected"],
            counts["expected_analysis_categories"],
            counts["expected_analysis_semantics"],
            counts["direction_expected"],
        )
        prior_expected = expected_shapes.setdefault(case_id, expected_shape)
        if prior_expected != expected_shape:
            raise ValueError("benchmark gold counts differ across candidates")

    if not groups:
        return {
            "schema": AGGREGATE_SCHEMA,
            "ranking_basis": "private_gold_grounded_extraction_metrics",
            "promotion_authority": "none",
            "case_set_sha256": _sha256_text("[]"),
            "candidates": [],
        }

    case_sets = {frozenset(items) for items in groups.values()}
    if len(case_sets) != 1:
        raise ValueError("candidate case coverage differs")
    case_ids = sorted(next(iter(case_sets)))
    binding_payload = [
        [
            case_id,
            bindings[case_id][0],
            bindings[case_id][1],
            bindings[case_id][2],
        ]
        for case_id in case_ids
    ]
    case_set_sha256 = _sha256_text(
        json.dumps(binding_payload, separators=(",", ":"), ensure_ascii=False)
    )

    rows: list[dict[str, Any]] = []
    for label, by_case in groups.items():
        items = [by_case[case_id] for case_id in case_ids]
        metric_means: dict[str, float | None] = {}
        for key in _METRIC_KEYS:
            values = [item["metrics"][key] for item in items]
            present = [float(value) for value in values if value is not None]
            metric_means[key] = round(mean(present), 6) if present else None
        rows.append(
            {
                "candidate_label": label,
                "provenance_state": "operator_label_only",
                "case_count": len(items),
                "valid_case_count": sum(item["state"] == "ok" for item in items),
                "mean_overall_score": round(
                    mean(float(item["overall_score"]) for item in items), 6
                ),
                "metrics": metric_means,
                "run_observations": _aggregate_observations(items),
            }
        )
    rows.sort(key=lambda row: (-row["mean_overall_score"], row["candidate_label"]))
    return {
        "schema": AGGREGATE_SCHEMA,
        "ranking_basis": "private_gold_grounded_extraction_metrics",
        "promotion_authority": "none",
        "case_set_sha256": case_set_sha256,
        "candidates": rows,
    }
