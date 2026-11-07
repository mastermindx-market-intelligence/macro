"""Pure Basic Materials economics calculations.

This module is a read-only F04 consumer. It performs no I/O, source admission,
identity allocation, permission checks, ranking, gating, sizing, or trading.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

AUTHORITY_CEILING = "research_display_only"
SCHEMA_ID = "market_ontology.materials_economics/v1"

_COMPARABLE_FIELDS = (
    "domain",
    "unit",
    "currency",
    "scale_text",
    "quantity_basis",
    "period_start",
    "period_end",
    "period_kind",
    "consolidation_basis",
    "valuation_basis",
    "inclusions",
    "exclusions",
)


def _decimal_text(value: Any) -> Decimal | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def compare_measures(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    relation: str,
) -> dict[str, Any]:
    """Compare two explicitly scoped measures using a closed relation vocabulary."""
    if relation != "same_period_spread":
        return {
            "state": "not_comparable",
            "relation": relation,
            "value_text": None,
            "input_refs": [],
            "reasons": ["unsupported_relation"],
        }

    reasons: list[str] = []
    for field in _COMPARABLE_FIELDS:
        lv = left.get(field)
        rv = right.get(field)
        if lv is None or rv is None:
            reasons.append(f"missing_basis:{field}")
        elif lv != rv:
            reasons.append(f"basis_mismatch:{field}")

    left_value = _decimal_text(left.get("value_text"))
    right_value = _decimal_text(right.get("value_text"))
    if left_value is None:
        reasons.append("invalid_value:left")
    if right_value is None:
        reasons.append("invalid_value:right")

    left_ref = left.get("evidence_id")
    right_ref = right.get("evidence_id")
    if not isinstance(left_ref, str) or not left_ref:
        reasons.append("missing_evidence:left")
    if not isinstance(right_ref, str) or not right_ref:
        reasons.append("missing_evidence:right")

    if reasons:
        return {
            "state": "not_comparable",
            "relation": relation,
            "value_text": None,
            "input_refs": [
                ref for ref in (left_ref, right_ref) if isinstance(ref, str) and ref
            ],
            "reasons": reasons,
        }

    assert left_value is not None and right_value is not None
    return {
        "state": "available",
        "relation": relation,
        "value_text": _format_decimal(left_value - right_value),
        "input_refs": [left_ref, right_ref],
        "reasons": [],
    }


_PERIOD_CHANGE_FIELDS = tuple(
    field for field in _COMPARABLE_FIELDS if field not in {"period_start", "period_end"}
)


def _change_between_periods(
    current: Mapping[str, Any], prior: Mapping[str, Any]
) -> dict[str, Any]:
    reasons: list[str] = []
    for field in _PERIOD_CHANGE_FIELDS:
        cv = current.get(field)
        pv = prior.get(field)
        if cv is None or pv is None:
            reasons.append(f"missing_basis:{field}")
        elif cv != pv:
            reasons.append(f"basis_mismatch:{field}")
    current_value = _decimal_text(current.get("value_text"))
    prior_value = _decimal_text(prior.get("value_text"))
    if current_value is None:
        reasons.append("invalid_value:current")
    if prior_value is None:
        reasons.append("invalid_value:prior")
    refs = [current.get("evidence_id"), prior.get("evidence_id")]
    if reasons:
        return {
            "state": "not_comparable",
            "value_text": None,
            "input_refs": [r for r in refs if isinstance(r, str) and r],
            "reasons": reasons,
        }
    assert current_value is not None and prior_value is not None
    return {
        "state": "available",
        "value_text": _format_decimal(current_value - prior_value),
        "input_refs": refs,
        "reasons": [],
    }


def _calculation(key: str, result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "key": key,
        "state": result["state"],
        "value_text": result["value_text"],
        "input_refs": list(result["input_refs"]),
        "reasons": list(result.get("reasons", ())),
    }


def compose_materials_economics(
    *,
    assertions: tuple[dict[str, Any], ...],
    identity_rows: tuple[dict[str, Any], ...],
    source_bindings: tuple[dict[str, Any], ...],
    route_receipts: tuple[dict[str, Any], ...],
    source_generation: str,
    rights_version: str,
    cutoff: dict[str, Any],
) -> dict[str, Any]:
    """Compose one pure, display-only Materials economic explanation."""
    del identity_rows, source_bindings, route_receipts  # adapter-owned until later T4 slice
    if not assertions:
        raise ValueError("assertions must not be empty")

    subjects = {row.get("subject_ref") for row in assertions}
    kinds = {row.get("analysis_kind") for row in assertions}
    if len(subjects) != 1 or None in subjects:
        raise ValueError("assertions must share one subject_ref")
    if kinds != {"unit_economics"}:
        raise ValueError("unsupported analysis_kind")

    by_metric = {row.get("metric_label"): row for row in assertions}
    required = ("price_prior", "cost_prior", "price_current", "cost_current")
    if any(name not in by_metric for name in required):
        missing = [name for name in required if name not in by_metric]
        raise ValueError(f"missing unit-economics metrics: {missing}")

    prior_margin = compare_measures(
        by_metric["price_prior"], by_metric["cost_prior"], relation="same_period_spread"
    )
    current_margin = compare_measures(
        by_metric["price_current"], by_metric["cost_current"], relation="same_period_spread"
    )
    price_change = _change_between_periods(
        by_metric["price_current"], by_metric["price_prior"]
    )
    cost_change = _change_between_periods(
        by_metric["cost_current"], by_metric["cost_prior"]
    )

    if any(
        result["state"] != "available"
        for result in (prior_margin, current_margin, price_change, cost_change)
    ):
        return {
            "schema": SCHEMA_ID,
            "authority_ceiling": AUTHORITY_CEILING,
            "display_only": True,
            "subject_ref": next(iter(subjects)),
            "analysis_kind": "unit_economics",
            "calculations": [],
            "explanation": {
                "code": "not_comparable",
                "lead": "The available measurements are not comparable on the required basis.",
                "does_not_prove": ["whole-company profitability"],
                "next_observation": "A comparable price-and-cost pair on the same product basis.",
            },
            "company_link": None,
            "limitations": ["comparison_unavailable", "company_link_unavailable"],
            "source_refs": sorted(
                {
                    ref
                    for row in assertions
                    for ref in (row.get("evidence_id"),)
                    if isinstance(ref, str) and ref
                }
            ),
            "provenance": {
                "source_generation": source_generation,
                "rights_version": rights_version,
                "cutoff": dict(cutoff),
            },
        }

    margin_change_value = (
        _decimal_text(current_margin["value_text"])
        - _decimal_text(prior_margin["value_text"])
    )
    assert margin_change_value is not None
    margin_change = {
        "state": "available",
        "value_text": _format_decimal(margin_change_value),
        "input_refs": current_margin["input_refs"] + prior_margin["input_refs"],
        "reasons": [],
    }

    price_delta = _decimal_text(price_change["value_text"])
    margin_delta = _decimal_text(margin_change["value_text"])
    assert price_delta is not None and margin_delta is not None
    if price_delta > 0 and margin_delta < 0:
        code = "price_up_margin_down"
        lead = (
            "Higher realization did not offset the larger cost increase; "
            "retained unit margin weakened."
        )
    else:
        code = "unit_economics_changed"
        lead = "Comparable price, cost, and retained unit margin changed."

    calculations = [
        _calculation("current_unit_margin", current_margin),
        _calculation("prior_unit_margin", prior_margin),
        _calculation("price_change", price_change),
        _calculation("cost_change", cost_change),
        _calculation("margin_change", margin_change),
    ]
    return {
        "schema": SCHEMA_ID,
        "authority_ceiling": AUTHORITY_CEILING,
        "display_only": True,
        "subject_ref": next(iter(subjects)),
        "analysis_kind": "unit_economics",
        "calculations": calculations,
        "explanation": {
            "code": code,
            "lead": lead,
            "does_not_prove": ["whole-company profitability"],
            "next_observation": (
                "A later comparable realized price-and-cost margin on the same product basis."
            ),
        },
        "company_link": None,
        "limitations": ["company_link_unavailable"],
        "source_refs": sorted(
            {
                row["evidence_id"]
                for row in assertions
                if isinstance(row.get("evidence_id"), str) and row["evidence_id"]
            }
        ),
        "provenance": {
            "source_generation": source_generation,
            "rights_version": rights_version,
            "cutoff": dict(cutoff),
        },
    }
