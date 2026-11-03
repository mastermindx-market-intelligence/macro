"""Pure owner-local projection over already-validated guidance/fact mappings.

T06 (Semiconductor Theme Intelligence B): management-history projection.
This module NEVER reads from disk, NEVER touches the network, NEVER
imports a scoring/ranking/forecast module, NEVER computes a midpoint
arithmetic itself, and NEVER stores historical estimates.  Every value
it surfaces is either an echo of an input the caller passed in, or a
fiat classification (range membership, refusal reason, position) over
those inputs.  Midpoints come ONLY from native receipts the caller
hands in via ``native_derivations``; the closed ``derived`` slot is the
sole channel for them and is intentionally empty when those receipts
are absent.

The output schema is ``management_sequence_assessment.v1``.  The shape
is closed and the module owns every literal it returns — no string
templates, no formatting, no LLM — so downstream rankers/consumers can
depend on a strict contract.
"""
from __future__ import annotations

import math
from typing import Any, Mapping


SCHEMA = "management_sequence_assessment.v1"


# Closed vocabulary for refusal reasons.  Adding a new reason requires a
# contract amendment — see carrier PR #7870 frozen API.  Order here is the
# canonical precedence order: a prior mismatch earlier in this tuple wins
# over a later one even when several apply simultaneously.
_REFUSAL_REASONS: tuple[str, ...] = (
    "fiscal_period_mismatch",
    "metric_mismatch",
    "unit_mismatch",
    "basis_change",
    "currency_mismatch",
    "perimeter_change",
    "definition_change",
    "range_missing",
)


class GuidanceHistoryError(ValueError):
    """Raised on any contract violation.  Short snake_case codes only."""


# ─────────────────────────────────────────────────────────────────────────────
# Required key vocabularies
# ─────────────────────────────────────────────────────────────────────────────

_OUTLOOK_REQUIRED: tuple[str, ...] = (
    "schema", "metric", "low", "high", "unit", "horizon", "status", "source_span",
)
# Keys that the echo carries (schema is validated for presence but not echoed —
# the closed role shape is what the contract pins).
_OUTLOOK_ECHO: tuple[str, ...] = (
    "metric", "low", "high", "unit", "horizon", "status", "source_span",
)
_OUTLOOK_OPTIONAL: tuple[str, ...] = ("basis", "currency", "perimeter", "definition")

_ACTUAL_REQUIRED: tuple[str, ...] = (
    "metric", "value", "unit", "fiscal_period", "source_span",
)
_ACTUAL_OPTIONAL: tuple[str, ...] = ("basis", "currency", "perimeter", "definition")

_DERIVATION_KEYS: tuple[str, ...] = ("prior_midpoint", "next_outlook_midpoint")


# ─────────────────────────────────────────────────────────────────────────────
# Pure input validation
# ─────────────────────────────────────────────────────────────────────────────


def _require_mapping(obj: Any, role: str) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise GuidanceHistoryError(f"missing:{role}")
    return obj


def _require_keys(obj: Mapping[str, Any], role: str, keys: tuple[str, ...]) -> None:
    for key in keys:
        if key not in obj:
            raise GuidanceHistoryError(f"missing:{role}.{key}")


def _reject_non_finite(value: Any, role: str, key: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise GuidanceHistoryError("non_finite")


# ─────────────────────────────────────────────────────────────────────────────
# Role echoing — fills missing optionals with explicit nulls
# ─────────────────────────────────────────────────────────────────────────────


def _echo_outlook_role(obj: Mapping[str, Any], role: str) -> dict[str, Any]:
    _require_keys(obj, role, _OUTLOOK_REQUIRED)
    echoed: dict[str, Any] = {key: obj[key] for key in _OUTLOOK_ECHO}
    for opt in _OUTLOOK_OPTIONAL:
        echoed[opt] = obj.get(opt, None)
    return echoed


def _echo_actual_role(obj: Mapping[str, Any], role: str) -> dict[str, Any]:
    _require_keys(obj, role, _ACTUAL_REQUIRED)
    echoed: dict[str, Any] = {key: obj[key] for key in _ACTUAL_REQUIRED}
    for opt in _ACTUAL_OPTIONAL:
        echoed[opt] = obj.get(opt, None)
    return echoed


# ─────────────────────────────────────────────────────────────────────────────
# Comparisons
# ─────────────────────────────────────────────────────────────────────────────


_OPTIONAL_DEFINITION_FIELDS: tuple[str, ...] = ("basis", "currency", "perimeter", "definition")


def _optional_equal(a: Any, b: Any) -> bool:
    """None == None counts as equal; None vs non-None is a MISMATCH."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a == b


def _classify_prior_vs_actual(
    prior: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> dict[str, Any]:
    """Closed result dict; first refusal reason wins (precedence order)."""
    # 1. fiscal_period_mismatch — checked first because it also gates the
    #    "is this a same-period surprise at all" question.
    if prior.get("horizon") != actual.get("fiscal_period"):
        return {"status": "refused", "reason": "fiscal_period_mismatch", "position": None}

    # 2. metric_mismatch
    if prior.get("metric") != actual.get("metric"):
        return {"status": "refused", "reason": "metric_mismatch", "position": None}

    # 3. unit_mismatch
    if prior.get("unit") != actual.get("unit"):
        return {"status": "refused", "reason": "unit_mismatch", "position": None}

    # 4. basis_change — None vs non-None is a MISMATCH (per frozen spec).
    if not _optional_equal(prior.get("basis"), actual.get("basis")):
        return {"status": "refused", "reason": "basis_change", "position": None}

    # 5. currency_mismatch
    if not _optional_equal(prior.get("currency"), actual.get("currency")):
        return {"status": "refused", "reason": "currency_mismatch", "position": None}

    # 6. perimeter_change
    if not _optional_equal(prior.get("perimeter"), actual.get("perimeter")):
        return {"status": "refused", "reason": "perimeter_change", "position": None}

    # 7. definition_change
    if not _optional_equal(prior.get("definition"), actual.get("definition")):
        return {"status": "refused", "reason": "definition_change", "position": None}

    # 8. range_missing — low and high must both be numbers (None counts as
    #    missing; we do not compute a midpoint even from one endpoint).
    low = prior.get("low")
    high = prior.get("high")
    if not (isinstance(low, (int, float)) and isinstance(high, (int, float))
            and not isinstance(low, bool) and not isinstance(high, bool)):
        return {"status": "refused", "reason": "range_missing", "position": None}

    value = actual.get("value")
    if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
        return {"status": "refused", "reason": "range_missing", "position": None}

    # Inclusive range membership, no delta / percentage / midpoint emitted.
    if value < low:
        position = "below_range"
    elif value > high:
        position = "above_range"
    else:
        position = "within_range"
    return {"status": "comparable", "reason": None, "position": position}


# ─────────────────────────────────────────────────────────────────────────────
# Native derivations — refuse to originate, only echo receipts
# ─────────────────────────────────────────────────────────────────────────────


def _derivation_status(
    derivations: Mapping[str, Any] | None,
    key: str,
) -> dict[str, Any]:
    """Ready ONLY when the named derivation has a numeric value, a non-empty
    receipt mapping, and a non-empty inputs list.  Anything else → unavailable
    with ``derivation_unowned``.  Never computes (low+high)/2."""
    if derivations is None:
        return {"status": "unavailable", "reason": "derivation_unowned"}
    payload = derivations.get(key)
    if not isinstance(payload, Mapping):
        return {"status": "unavailable", "reason": "derivation_unowned"}
    value = payload.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return {"status": "unavailable", "reason": "derivation_unowned"}
    # A receipt-backed value is still a number the page would display: NaN/inf is
    # refused exactly like every other numeric input (review nit, carrier #7870).
    _reject_non_finite(value, "native_derivations", key)
    receipt = payload.get("receipt")
    if not isinstance(receipt, Mapping) or len(receipt) == 0:
        return {"status": "unavailable", "reason": "derivation_unowned"}
    inputs = payload.get("inputs")
    if not isinstance(inputs, (list, tuple)) or len(inputs) == 0:
        return {"status": "unavailable", "reason": "derivation_unowned"}
    owner = payload.get("owner")
    if not isinstance(owner, str) or owner == "":
        return {"status": "unavailable", "reason": "derivation_unowned"}
    return {"status": "ready", "value": value, "receipt": receipt, "owner": owner}


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────


def assess_management_sequence(
    prior: Mapping[str, Any],
    actual: Mapping[str, Any],
    next_outlook: Mapping[str, Any],
    *,
    native_derivations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project prior_outlook / actual / new_outlook into a closed assessment.

    See module docstring and carrier PR #7870 for the frozen contract.
    """
    # Echo roles first so missing-key errors surface with the right code
    # even on otherwise-noisy inputs.
    roles = {
        "prior_outlook": _echo_outlook_role(_require_mapping(prior, "prior"), "prior"),
        "actual": _echo_actual_role(_require_mapping(actual, "actual"), "actual"),
        "new_outlook": _echo_outlook_role(_require_mapping(next_outlook, "next_outlook"), "next_outlook"),
    }

    # Reject NaN/inf on the numeric echo inputs.  Bool is a subclass of int
    # in Python; we treat bool as not-a-number here and refuse silently by
    # missing-key-shape checks (the range-missing branch).
    for field in ("low", "high"):
        if isinstance(roles["prior_outlook"][field], float):
            _reject_non_finite(roles["prior_outlook"][field], "prior", field)
        if isinstance(roles["new_outlook"][field], float):
            _reject_non_finite(roles["new_outlook"][field], "next_outlook", field)
    if isinstance(roles["actual"]["value"], float):
        _reject_non_finite(roles["actual"]["value"], "actual", "value")

    # New outlook concerns a later period — refuse any same-period read.
    if roles["new_outlook"]["horizon"] == roles["actual"]["fiscal_period"]:
        raise GuidanceHistoryError("new_outlook_same_period")

    prior_vs_actual = _classify_prior_vs_actual(prior, actual)
    comparisons = {
        "prior_vs_actual": prior_vs_actual,
        "actual_vs_new_outlook": {
            "status": "not_comparable",
            "reason": "different_period",
            "relationship": "next_outlook",
        },
    }

    derived = {
        key: _derivation_status(native_derivations, key)
        for key in _DERIVATION_KEYS
    }

    refused_deltas: list[str] = []
    for cmp_key, cmp_value in comparisons.items():
        if cmp_value.get("status") == "refused":
            refused_deltas.append(cmp_key)

    display = {
        "all_values_visible": True,
        "refused_deltas": refused_deltas,
    }

    limitations: list[str] = ["no_external_consensus"]
    for cmp_value in comparisons.values():
        if cmp_value.get("status") == "refused" and cmp_value.get("reason"):
            limitations.append(f"comparison_refused:{cmp_value['reason']}")
    # Two ABSENT optional definitions compare equal above (frozen spec), but
    # matching unknowns do not certify comparability: the producer never
    # established that basis / currency / perimeter / definition. Say so, per
    # field, as a limitation — additive, never a refusal (Industrials W12 item 2,
    # Consumer R10 item 3, disposition #7870 issuecomment-5809602368).
    for field in _OPTIONAL_DEFINITION_FIELDS:
        if roles["prior_outlook"].get(field) is None and roles["actual"].get(field) is None:
            limitations.append(f"definition_unqualified:{field}")
    # A prior outlook struck at a stated FX planning rate (TSMC: "1 US dollar
    # to N NT dollars") is compared against an actual translated at realised
    # rates. The comparison stays comparable — same metric, unit, basis and
    # currency — but a within/below/above read can be produced by FX drift
    # alone, so say so. Additive limitation, no new refusal reason (the closed
    # vocabulary stays frozen); the guidance item's fx_assumption itself is not
    # echoed by the frozen outlook role. Alignment review, #7870, 2026-09-24.
    if _require_mapping(prior, "prior").get("fx_assumption") is not None:
        limitations.append("fx_assumption_unreconciled")

    authority = {
        "can_rank": False,
        "can_gate": False,
        "can_size": False,
        "can_originate": False,
        "can_open_entry": False,
    }

    return {
        "schema": SCHEMA,
        "roles": roles,
        "comparisons": comparisons,
        "derived": derived,
        "display": display,
        "limitations": limitations,
        "authority": authority,
    }


__all__ = [
    "SCHEMA",
    "GuidanceHistoryError",
    "assess_management_sequence",
]