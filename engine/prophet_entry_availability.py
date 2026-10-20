"""Deterministic Prophet V4 B4 entry-availability contract.

This module is the strategy/horizon-specific Availability authority.  It does
not discover candidates, rank them, create entry geometry, or consume narrative
/intelligence scores.  It binds an accepted strategy definition to canonical
B1/B3 identity and *reads* already-owned deterministic entry facts.

Zone/chase/stop geometry remains owned by the incumbent entry owner; callers
must supply those facts with a receipt.  Missing, stale, ambiguous or unknown
required facts fail closed.  No favorable score/theme/model input can waive a
blocker because such fields are outside the closed input contract.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
import re

from engine.prophet_candidate_state import validate_candidate_state_projection
from engine.prophet_strategy_definition import (
    ENTRY_POLICY_VERSION,
    STRATEGY_ID,
    build_early_leadership_sector_rotation_definition,
    validate_strategy_definition,
)

SCHEMA = "prophet.entry_availability/v1"
DEFINITION = "availability-v1-2026-08-17"
HORIZON = "2_15_SESSIONS"
HORIZON_ROLE = "new_entry"

AVAILABILITY_STATES = frozenset(
    {
        "NOT_READY",
        "APPROACHING_ENTRY",
        "ENTRY_OPEN",
        "WAIT_PULLBACK",
        "RAN_DONT_CHASE",
        "INVALIDATED",
        "UNAVAILABLE_DATA",
    }
)

_OWNER_STATUSES = frozenset(
    {
        "buy_now",
        "partial",
        "await_confluence",
        "buy_soon",
        "watch",
        "wait_pullback",
        "hold",
        "extended",
        "bounce_wait",
        "topping",
        "exit",
        "avoid",
        "blocked",
    }
)
_PASS_FAIL_UNKNOWN = frozenset({"PASS", "FAIL", "UNKNOWN"})
_FRESHNESS = frozenset({"FRESH", "STALE", "UNKNOWN"})
_BASIS_STATE = frozenset({"RESOLVED", "AMBIGUOUS", "UNKNOWN"})
_EVENT_STATE = frozenset({"ACTIVE", "RETRACTED", "UNKNOWN"})
_INVALIDATION_STATE = frozenset({"CLEAR", "BREACHED", "UNKNOWN"})
_RFC3339_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_RECEIPT_RE = re.compile(r"^(?:sha256:|[a-z][a-z0-9_.-]*:).+")

_FACT_KEYS = {
    "decision_at",
    "market_session",
    "quote",
    "geometry",
    "deterministic_gates",
    "metric_inputs",
    "source_receipts",
}
_QUOTE_KEYS = {"price", "asof", "freshness", "basis_version", "source_receipt"}
_GEOMETRY_KEYS = {
    "owner_status",
    "zone_low",
    "zone_high",
    "chase_above",
    "invalidation_price",
    "basis_version",
    "source_receipt",
}
_GATE_KEYS = {
    "owner_confluence",
    "risk_ceiling",
    "liquidity_fillability",
    "gap_velocity",
    "source_health",
    "corporate_action_basis",
    "session_eligibility",
    "event_status",
    "structural_invalidation",
}
_METRIC_KEYS = {"first_trigger_price", "anchor_price", "atr"}


class EntryAvailabilityContractError(ValueError):
    """Raised when B4 inputs violate the closed deterministic contract."""


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise EntryAvailabilityContractError(
            f"entry availability is not canonical JSON: {exc}"
        ) from exc


def _closed_mapping(value: object, keys: set[str], field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise EntryAvailabilityContractError(f"{field} fields are not closed")
    return value


def _text(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ord(character) < 32 for character in value)
    ):
        raise EntryAvailabilityContractError(f"{field} must be non-empty text")
    return value


def _utc(value: object, field: str) -> datetime:
    text = _text(value, field)
    if not _RFC3339_UTC_RE.fullmatch(text):
        raise EntryAvailabilityContractError(f"{field} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:  # pragma: no cover - regex excludes ordinary failures
        raise EntryAvailabilityContractError(f"{field} is invalid") from exc
    return parsed.astimezone(timezone.utc)


def _session(value: object) -> str:
    text = _text(value, "market_session")
    if not _DATE_RE.fullmatch(text):
        raise EntryAvailabilityContractError("market_session must be YYYY-MM-DD")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise EntryAvailabilityContractError("market_session is invalid") from exc
    return text


def _finite_positive(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EntryAvailabilityContractError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise EntryAvailabilityContractError(f"{field} must be finite and > 0")
    return number


def _receipt(value: object, field: str) -> str:
    text = _text(value, field)
    if not _RECEIPT_RE.fullmatch(text):
        raise EntryAvailabilityContractError(f"{field} must be an owner receipt")
    return text


def _enum(value: object, allowed: frozenset[str], field: str) -> str:
    text = _text(value, field)
    if text not in allowed:
        raise EntryAvailabilityContractError(f"{field} has invalid value {text!r}")
    return text


def _candidate_row(
    candidate_projection: Mapping[str, object], episode_id: str
) -> Mapping[str, object]:
    validate_candidate_state_projection(candidate_projection)
    rows = candidate_projection.get("rows")
    assert isinstance(rows, list)  # guaranteed by owner validator
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("episode_id") == episode_id]
    if len(matches) != 1:
        raise EntryAvailabilityContractError("episode_id is not unique in canonical B3 projection")
    return matches[0]


def _strategy_identity(strategy_definition: Mapping[str, object]) -> dict[str, str]:
    validate_strategy_definition(strategy_definition)
    if strategy_definition.get("strategy_id") != STRATEGY_ID:
        raise EntryAvailabilityContractError("unsupported strategy definition")
    horizons = strategy_definition.get("horizons")
    entry = strategy_definition.get("entry_and_availability_requirements")
    if not isinstance(horizons, Mapping) or not isinstance(entry, Mapping):
        raise EntryAvailabilityContractError("strategy definition is incomplete")
    if horizons.get("primary") != HORIZON or horizons.get("horizon_role") != HORIZON_ROLE:
        raise EntryAvailabilityContractError("strategy horizon identity mismatch")
    if entry.get("entry_policy_version") != ENTRY_POLICY_VERSION:
        raise EntryAvailabilityContractError("entry policy identity mismatch")
    return {
        "strategy_definition_id": _text(
            strategy_definition.get("strategy_definition_id"), "strategy_definition_id"
        ),
        "strategy_id": STRATEGY_ID,
        "strategy_version": _text(strategy_definition.get("strategy_version"), "strategy_version"),
        "horizon": HORIZON,
        "horizon_role": HORIZON_ROLE,
        "entry_policy_version": ENTRY_POLICY_VERSION,
    }


def _metrics(
    *,
    price: float,
    zone_low: float,
    zone_high: float,
    invalidation: float,
    first_trigger: float,
    anchor: float,
    atr: float,
) -> dict[str, float]:
    if price < zone_low:
        distance = 100.0 * (zone_low / price - 1.0)
    elif price > zone_high:
        distance = 100.0 * (price / zone_high - 1.0)
    else:
        distance = 0.0
    return {
        "distance_to_zone_pct": round(distance, 6),
        "risk_to_invalidation_pct": round(100.0 * (price - invalidation) / price, 6),
        "move_since_first_trigger_pct": round(100.0 * (price / first_trigger - 1.0), 6),
        "move_since_anchor_pct": round(100.0 * (price / anchor - 1.0), 6),
        "extension_atr": round((price - zone_high) / atr, 6),
    }


def evaluate_entry_availability(
    candidate_projection: Mapping[str, object],
    *,
    episode_id: str,
    strategy_definition: Mapping[str, object],
    facts: Mapping[str, object],
) -> dict[str, object]:
    """Evaluate one B4 row from canonical B3 plus closed deterministic owner facts."""

    if not isinstance(facts, Mapping) or set(facts) != _FACT_KEYS:
        raise EntryAvailabilityContractError("decision facts fields are not closed")
    episode_id = _text(episode_id, "episode_id")
    row = _candidate_row(candidate_projection, episode_id)
    strategy = _strategy_identity(strategy_definition)

    decision_at_text = _text(facts.get("decision_at"), "decision_at")
    decision_at = _utc(decision_at_text, "decision_at")
    candidate_generated_at = _utc(
        candidate_projection.get("generated_at"), "candidate_projection.generated_at"
    )
    if candidate_generated_at > decision_at:
        raise EntryAvailabilityContractError(
            "candidate_projection.generated_at cannot be after decision_at"
        )
    market_session = _session(facts.get("market_session"))
    if candidate_projection.get("market_session") != market_session:
        raise EntryAvailabilityContractError("B3 and B4 market_session mismatch")

    quote = _closed_mapping(facts.get("quote"), _QUOTE_KEYS, "quote")
    geometry = _closed_mapping(facts.get("geometry"), _GEOMETRY_KEYS, "geometry")
    gates = _closed_mapping(
        facts.get("deterministic_gates"), _GATE_KEYS, "deterministic_gates"
    )
    metric_inputs = _closed_mapping(facts.get("metric_inputs"), _METRIC_KEYS, "metric_inputs")

    price = _finite_positive(quote.get("price"), "quote.price")
    quote_asof_text = _text(quote.get("asof"), "quote.asof")
    quote_asof = _utc(quote_asof_text, "quote.asof")
    if quote_asof > decision_at:
        raise EntryAvailabilityContractError("quote.asof cannot be after decision_at")
    quote_age_seconds = int((decision_at - quote_asof).total_seconds())
    quote_freshness = _enum(quote.get("freshness"), _FRESHNESS, "quote.freshness")
    quote_basis = _text(quote.get("basis_version"), "quote.basis_version")
    quote_receipt = _receipt(quote.get("source_receipt"), "quote.source_receipt")

    owner_status = _enum(geometry.get("owner_status"), _OWNER_STATUSES, "geometry.owner_status")
    zone_low = _finite_positive(geometry.get("zone_low"), "geometry.zone_low")
    zone_high = _finite_positive(geometry.get("zone_high"), "geometry.zone_high")
    chase_above = _finite_positive(geometry.get("chase_above"), "geometry.chase_above")
    invalidation = _finite_positive(
        geometry.get("invalidation_price"), "geometry.invalidation_price"
    )
    if zone_low > zone_high:
        raise EntryAvailabilityContractError("entry zone is inverted")
    if chase_above < zone_high:
        raise EntryAvailabilityContractError("chase boundary cannot be below zone high")
    geometry_basis = _text(geometry.get("basis_version"), "geometry.basis_version")
    geometry_receipt = _receipt(geometry.get("source_receipt"), "geometry.source_receipt")

    first_trigger = _finite_positive(
        metric_inputs.get("first_trigger_price"), "metric_inputs.first_trigger_price"
    )
    anchor = _finite_positive(metric_inputs.get("anchor_price"), "metric_inputs.anchor_price")
    atr = _finite_positive(metric_inputs.get("atr"), "metric_inputs.atr")
    metrics = _metrics(
        price=price,
        zone_low=zone_low,
        zone_high=zone_high,
        invalidation=invalidation,
        first_trigger=first_trigger,
        anchor=anchor,
        atr=atr,
    )

    source_receipts = facts.get("source_receipts")
    if not isinstance(source_receipts, Sequence) or isinstance(source_receipts, (str, bytes)):
        raise EntryAvailabilityContractError("source_receipts must be a list")
    receipts = sorted({_receipt(value, "source_receipts[]") for value in source_receipts})
    receipts = sorted(set(receipts + [quote_receipt, geometry_receipt]))

    gate_values = {
        "owner_confluence": _enum(gates.get("owner_confluence"), _PASS_FAIL_UNKNOWN, "owner_confluence"),
        "risk_ceiling": _enum(gates.get("risk_ceiling"), _PASS_FAIL_UNKNOWN, "risk_ceiling"),
        "liquidity_fillability": _enum(
            gates.get("liquidity_fillability"), _PASS_FAIL_UNKNOWN, "liquidity_fillability"
        ),
        "gap_velocity": _enum(gates.get("gap_velocity"), _PASS_FAIL_UNKNOWN, "gap_velocity"),
        "source_health": _enum(gates.get("source_health"), _PASS_FAIL_UNKNOWN, "source_health"),
        "corporate_action_basis": _enum(
            gates.get("corporate_action_basis"), _BASIS_STATE, "corporate_action_basis"
        ),
        "session_eligibility": _enum(
            gates.get("session_eligibility"), _PASS_FAIL_UNKNOWN, "session_eligibility"
        ),
        "event_status": _enum(gates.get("event_status"), _EVENT_STATE, "event_status"),
        "structural_invalidation": _enum(
            gates.get("structural_invalidation"), _INVALIDATION_STATE, "structural_invalidation"
        ),
    }

    blockers: list[str] = []
    reasons: list[str] = []
    lifecycle = row.get("episode_lifecycle")
    lifecycle_state = lifecycle.get("state") if isinstance(lifecycle, Mapping) else None

    state: str
    if lifecycle_state != "ACTIVE":
        state = "INVALIDATED"
        blockers.append(f"EPISODE_NOT_ACTIVE:{lifecycle_state}")
    elif gate_values["event_status"] == "RETRACTED":
        state = "INVALIDATED"
        blockers.append("EVENT_RETRACTED")
    elif gate_values["structural_invalidation"] == "BREACHED" or price <= invalidation:
        state = "INVALIDATED"
        blockers.append("STRUCTURAL_INVALIDATION_BREACHED")
    else:
        unavailable: list[str] = []
        if quote_freshness != "FRESH":
            unavailable.append("QUOTE_STALE" if quote_freshness == "STALE" else "QUOTE_FRESHNESS_UNKNOWN")
        # The incumbent live-price owner deliberately keeps two honest price
        # families: raw vendor prints for the tape and split/dividend-adjusted
        # levels for the armed geometry.  Equality is therefore NOT the resolution
        # test.  The upstream basis owner must prove the two planes comparable
        # (or fail closed) and reports that verdict through corporate_action_basis.
        # Requiring literal equality here would dark every truthful live read and
        # would pressure an adapter to fabricate an adjusted exchange print.
        if gate_values["corporate_action_basis"] != "RESOLVED":
            unavailable.append(
                "CORPORATE_ACTION_BASIS_AMBIGUOUS"
                if gate_values["corporate_action_basis"] == "AMBIGUOUS"
                else "CORPORATE_ACTION_BASIS_UNKNOWN"
            )
        if gate_values["source_health"] != "PASS":
            unavailable.append(
                "SOURCE_HEALTH_FAILED" if gate_values["source_health"] == "FAIL" else "SOURCE_HEALTH_UNKNOWN"
            )
        for key in (
            "owner_confluence",
            "risk_ceiling",
            "liquidity_fillability",
            "gap_velocity",
            "session_eligibility",
        ):
            if gate_values[key] == "UNKNOWN":
                unavailable.append(f"{key.upper()}_UNKNOWN")
        if gate_values["event_status"] == "UNKNOWN":
            unavailable.append("EVENT_STATUS_UNKNOWN")
        # The Early Leadership tactical policy already requires the incumbent
        # entry owner's numeric invalidation_price and hard-invalidates at or
        # below it above.  ``structural_invalidation`` is a separate optional
        # owner extension for a future entry-compatible thesis/falsifier fact:
        # BREACHED is non-waivable, but UNKNOWN must not deadlock the strategy
        # merely because no such additional owner contract exists yet.

        if unavailable:
            state = "UNAVAILABLE_DATA"
            blockers.extend(unavailable)
        elif price > chase_above:
            state = "RAN_DONT_CHASE"
            blockers.append("PAST_OWNER_CHASE_BOUNDARY")
        elif gate_values["risk_ceiling"] == "FAIL":
            state = "NOT_READY"
            blockers.append("RISK_TO_INVALIDATION_ABOVE_LANE_CEILING")
        elif gate_values["liquidity_fillability"] == "FAIL":
            state = "NOT_READY"
            blockers.append("LIQUIDITY_FILLABILITY_FAILED")
        elif gate_values["gap_velocity"] == "FAIL":
            state = "NOT_READY"
            blockers.append("GAP_VELOCITY_PROTECTION_FAILED")
        elif gate_values["session_eligibility"] == "FAIL":
            state = "NOT_READY"
            blockers.append("SESSION_NOT_ELIGIBLE")
        elif gate_values["owner_confluence"] == "FAIL":
            state = "APPROACHING_ENTRY"
            blockers.append("OWNER_CONFLUENCE_NOT_PASSED")
        elif owner_status in {"extended", "topping", "wait_pullback", "hold", "bounce_wait"}:
            state = "WAIT_PULLBACK"
            blockers.append("OWNER_STATUS_REQUIRES_PULLBACK")
        elif owner_status in {"exit", "avoid", "blocked"}:
            state = "NOT_READY"
            blockers.append("OWNER_STATUS_NOT_ACTIONABLE")
        elif owner_status in {"buy_soon", "await_confluence", "watch"}:
            state = "APPROACHING_ENTRY"
            reasons.append("OWNER_STATUS_APPROACHING")
        elif price < zone_low:
            state = "APPROACHING_ENTRY"
            blockers.append("CURRENT_PRICE_BELOW_OWNER_ZONE")
        elif price > zone_high:
            state = "WAIT_PULLBACK"
            blockers.append("CURRENT_PRICE_ABOVE_OWNER_ZONE")
        else:
            state = "ENTRY_OPEN"
            reasons.extend(
                [
                    "CURRENT_PRICE_INSIDE_OWNER_ZONE",
                    "OWNER_CONFLUENCE_PASSED",
                    "RISK_WITHIN_LANE_CEILING",
                    "LIQUIDITY_FILLABLE",
                    "FRESH_QUOTE",
                ]
            )

    if state not in AVAILABILITY_STATES:  # pragma: no cover - exhaustive branch guard
        raise EntryAvailabilityContractError("availability state is invalid")

    out: dict[str, object] = {
        "schema": SCHEMA,
        "definition": DEFINITION,
        "episode_id": episode_id,
        "candidate_generation_id": _text(
            row.get("candidate_generation_id"), "candidate_generation_id"
        ),
        "candidate_state_projection_id": _text(
            candidate_projection.get("projection_id"), "candidate_state_projection_id"
        ),
        "security_id": _text(row.get("security_id"), "security_id"),
        "identity_epoch": _text(row.get("identity_epoch"), "identity_epoch"),
        **strategy,
        "evaluated_at": decision_at_text,
        "market_session": market_session,
        "state": state,
        "entry_open": state == "ENTRY_OPEN",
        "zone": {"low": zone_low, "high": zone_high, "basis": geometry_basis},
        "current_price": price,
        "current_price_basis": quote_basis,
        "quote_asof": quote_asof_text,
        "quote_age_seconds": quote_age_seconds,
        "invalidation": {"price": invalidation, "kind": "structural", "basis": geometry_basis},
        **metrics,
        "chase_state": "past_boundary" if price > chase_above else "within_boundary",
        "owner_status": owner_status,
        "blockers": sorted(set(blockers)),
        "reasons": sorted(set(reasons)),
        "source_receipts": receipts,
    }
    material = dict(out)
    out["availability_id"] = "pea:" + sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()
    validate_entry_availability(out)
    return out


def validate_entry_availability(payload: Mapping[str, object]) -> None:
    """Validate one closed B4 output and its deterministic identity."""
    if not isinstance(payload, Mapping):
        raise EntryAvailabilityContractError("availability payload must be an object")
    expected = {
        "schema", "definition", "episode_id", "candidate_generation_id",
        "candidate_state_projection_id", "security_id", "identity_epoch",
        "strategy_definition_id", "strategy_id", "strategy_version", "horizon",
        "horizon_role", "entry_policy_version", "evaluated_at", "market_session",
        "state", "entry_open", "zone", "current_price", "current_price_basis",
        "quote_asof", "quote_age_seconds", "invalidation", "distance_to_zone_pct",
        "risk_to_invalidation_pct", "move_since_first_trigger_pct",
        "move_since_anchor_pct", "extension_atr", "chase_state", "owner_status",
        "blockers", "reasons", "source_receipts", "availability_id",
    }
    if set(payload) != expected:
        raise EntryAvailabilityContractError("availability output fields are not closed")
    if payload.get("schema") != SCHEMA or payload.get("definition") != DEFINITION:
        raise EntryAvailabilityContractError("availability schema/definition mismatch")
    accepted_strategy = _strategy_identity(
        build_early_leadership_sector_rotation_definition()
    )
    for field, value in accepted_strategy.items():
        if payload.get(field) != value:
            raise EntryAvailabilityContractError(
                f"availability {field} diverges from accepted strategy definition"
            )
    state = payload.get("state")
    if state not in AVAILABILITY_STATES:
        raise EntryAvailabilityContractError("availability state invalid")
    if payload.get("entry_open") is not (state == "ENTRY_OPEN"):
        raise EntryAvailabilityContractError("entry_open disagrees with availability state")
    if state == "ENTRY_OPEN" and payload.get("blockers"):
        raise EntryAvailabilityContractError("ENTRY_OPEN cannot carry blockers")
    material = {key: value for key, value in payload.items() if key != "availability_id"}
    expected_id = "pea:" + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    if payload.get("availability_id") != expected_id:
        raise EntryAvailabilityContractError("availability_id mismatch")
