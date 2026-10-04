"""Read-only Opportunity Lifecycle context over canonical Prophet B1/B3/B4.

This module is a presentation projection inside the existing Prophet Lab owner.
It creates no candidate, episode, strategy, entry verdict, forecast, plan, store,
rank, gate, or trading authority. It only binds one already-validated B3 row
to an optional already-validated B4 Availability receipt.

A missing B4 receipt is deliberately not rendered as ``entry_open=False``:
unknown permission is not a negative permission verdict. Likewise, private
Plan/position state, cross-domain evidence summaries and forecast heads remain
explicitly unjoined until their canonical owners are supplied by a later
authorized consumer.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Mapping, Sequence

from engine.prophet_candidate_state import validate_candidate_state_projection
from engine.prophet_entry_availability import validate_entry_availability
from engine.prophet_lab.contracts import ALL_FALSE_AUTHORITY


SCHEMA = "prophet.lab_opportunity_context/v1"
B3_SCHEMA = "prophet.candidate_state_projection/v1"
B4_SCHEMA = "prophet.entry_availability/v1"

_UNJOINED_USER_STATE = {
    "state": "NOT_JOINED",
    "plan_ref": None,
    "position_ref": None,
    "reason": "PRIVATE_OWNER_NOT_READ",
}
_UNJOINED_EVIDENCE = {
    "status": "NOT_JOINED",
    "support": None,
    "contradiction": None,
    "next_observable": None,
    "reason": "OPPORTUNITY_EVIDENCE_NOT_JOINED",
}
_UNQUALIFIED_FORECAST = {
    "qualified": False,
    "heads": None,
    "reason": "NO_QUALIFIED_OLI_FORECAST",
}


class OpportunityContextContractError(ValueError):
    """Raised when owner identities/clocks cannot be joined without guessing."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpportunityContextContractError(f"{field} must be non-empty text")
    return value


def _candidate_row(
    candidate_projection: Mapping[str, object],
    episode_id: str,
) -> Mapping[str, object]:
    validate_candidate_state_projection(candidate_projection)
    if candidate_projection.get("schema") != B3_SCHEMA:
        raise OpportunityContextContractError("candidate projection schema mismatch")
    rows = candidate_projection.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise OpportunityContextContractError("candidate projection rows must be a list")
    matches = [
        row for row in rows
        if isinstance(row, Mapping) and row.get("episode_id") == episode_id
    ]
    if len(matches) != 1:
        raise OpportunityContextContractError(
            "episode_id must resolve to exactly one canonical B3 row"
        )
    return matches[0]


def _unavailable_entry(row: Mapping[str, object]) -> dict[str, object]:
    owner = row.get("entry_availability")
    if owner != {"state": "UNAVAILABLE_DATA", "reason": "B4_NOT_AVAILABLE"}:
        raise OpportunityContextContractError(
            "B3 unavailable-entry sentinel is not canonical"
        )
    return {
        "owner_schema": B4_SCHEMA,
        "state": "UNAVAILABLE_DATA",
        "entry_open": None,
        "reason": "B4_NOT_AVAILABLE",
        "availability_id": None,
        "evaluated_at": None,
        "market_session": None,
        "strategy": None,
        "current_price": None,
        "zone": None,
        "invalidation": None,
        "chase_state": None,
        "owner_status": None,
        "blockers": ["B4_NOT_AVAILABLE"],
        "reasons": [],
        "source_receipts": [],
    }


def _bound_entry(
    candidate_projection: Mapping[str, object],
    row: Mapping[str, object],
    availability: Mapping[str, object],
) -> dict[str, object]:
    validate_entry_availability(availability)

    bindings = {
        "episode_id": row.get("episode_id"),
        "candidate_generation_id": candidate_projection.get("candidate_generation_id"),
        "candidate_state_projection_id": candidate_projection.get("projection_id"),
        "security_id": row.get("security_id"),
        "identity_epoch": row.get("identity_epoch"),
        "market_session": candidate_projection.get("market_session"),
    }
    for field, expected in bindings.items():
        if availability.get(field) != expected:
            raise OpportunityContextContractError(
                f"B4 {field} does not match the selected B3 owner identity"
            )

    strategy = {
        "strategy_definition_id": availability.get("strategy_definition_id"),
        "strategy_id": availability.get("strategy_id"),
        "strategy_version": availability.get("strategy_version"),
        "horizon": availability.get("horizon"),
        "horizon_role": availability.get("horizon_role"),
        "entry_policy_version": availability.get("entry_policy_version"),
    }
    return {
        "owner_schema": B4_SCHEMA,
        "state": availability.get("state"),
        "entry_open": availability.get("entry_open"),
        "reason": None,
        "availability_id": availability.get("availability_id"),
        "evaluated_at": availability.get("evaluated_at"),
        "market_session": availability.get("market_session"),
        "strategy": strategy,
        "current_price": {
            "value": availability.get("current_price"),
            "basis": availability.get("current_price_basis"),
            "asof": availability.get("quote_asof"),
            "age_seconds": availability.get("quote_age_seconds"),
        },
        "zone": deepcopy(availability.get("zone")),
        "invalidation": deepcopy(availability.get("invalidation")),
        "chase_state": availability.get("chase_state"),
        "owner_status": availability.get("owner_status"),
        "blockers": list(availability.get("blockers") or []),
        "reasons": list(availability.get("reasons") or []),
        "source_receipts": list(availability.get("source_receipts") or []),
    }


def compose_opportunity_context(
    candidate_projection: Mapping[str, object],
    *,
    episode_id: str,
    entry_availability: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Compose one zero-authority, identity-bound Prophet opportunity context.

    ``entry_availability`` is optional because the current native B4 runtime may
    truthfully be dark. When absent, the output retains ``UNAVAILABLE_DATA`` and
    ``entry_open=None`` rather than manufacturing a local permission verdict.
    """
    if not isinstance(candidate_projection, Mapping):
        raise OpportunityContextContractError("candidate_projection must be an object")
    episode_id = _text(episode_id, "episode_id")
    row = _candidate_row(candidate_projection, episode_id)

    entry = (
        _unavailable_entry(row)
        if entry_availability is None
        else _bound_entry(candidate_projection, row, entry_availability)
    )

    out: dict[str, object] = {
        "schema": SCHEMA,
        "identity": {
            "episode_id": row.get("episode_id"),
            "security_id": row.get("security_id"),
            "company_id": row.get("company_id"),
            "identity_epoch": row.get("identity_epoch"),
            "candidate_generation_id": candidate_projection.get("candidate_generation_id"),
            "candidate_state_projection_id": candidate_projection.get("projection_id"),
        },
        "decision_clock": {
            "market_session": candidate_projection.get("market_session"),
            "candidate_state_generated_at": candidate_projection.get("generated_at"),
        },
        "native_phase": {
            "episode_lifecycle": deepcopy(row.get("episode_lifecycle")),
            "emergence_state": deepcopy(row.get("emergence_state")),
            "maturity_state": deepcopy(row.get("maturity_state")),
        },
        "fresh_entry": entry,
        "user_state": deepcopy(_UNJOINED_USER_STATE),
        "evidence_summary": deepcopy(_UNJOINED_EVIDENCE),
        "forecast": deepcopy(_UNQUALIFIED_FORECAST),
        "authority": dict(ALL_FALSE_AUTHORITY),
    }
    validate_opportunity_context(out)
    return out


def validate_opportunity_context(payload: Mapping[str, object]) -> None:
    """Validate the closed presentation contract without re-deriving owner truth."""
    if not isinstance(payload, Mapping):
        raise OpportunityContextContractError("opportunity context must be an object")
    expected = {
        "schema", "identity", "decision_clock", "native_phase", "fresh_entry",
        "user_state", "evidence_summary", "forecast", "authority",
    }
    if set(payload) != expected:
        raise OpportunityContextContractError("opportunity context fields are not closed")
    if payload.get("schema") != SCHEMA:
        raise OpportunityContextContractError("opportunity context schema mismatch")
    if payload.get("authority") != ALL_FALSE_AUTHORITY:
        raise OpportunityContextContractError("Prophet Lab authority must remain all false")

    identity = payload.get("identity")
    if not isinstance(identity, Mapping) or set(identity) != {
        "episode_id", "security_id", "company_id", "identity_epoch",
        "candidate_generation_id", "candidate_state_projection_id",
    }:
        raise OpportunityContextContractError("identity block is not closed")
    for field in identity:
        _text(identity.get(field), f"identity.{field}")

    clock = payload.get("decision_clock")
    if not isinstance(clock, Mapping) or set(clock) != {
        "market_session", "candidate_state_generated_at",
    }:
        raise OpportunityContextContractError("decision_clock block is not closed")
    _text(clock.get("market_session"), "decision_clock.market_session")
    _text(clock.get("candidate_state_generated_at"), "decision_clock.candidate_state_generated_at")

    phase = payload.get("native_phase")
    if not isinstance(phase, Mapping) or set(phase) != {
        "episode_lifecycle", "emergence_state", "maturity_state",
    }:
        raise OpportunityContextContractError("native_phase block is not closed")

    entry = payload.get("fresh_entry")
    if not isinstance(entry, Mapping) or set(entry) != {
        "owner_schema", "state", "entry_open", "reason", "availability_id",
        "evaluated_at", "market_session", "strategy", "current_price", "zone",
        "invalidation", "chase_state", "owner_status", "blockers", "reasons",
        "source_receipts",
    }:
        raise OpportunityContextContractError("fresh_entry block is not closed")
    if entry.get("owner_schema") != B4_SCHEMA:
        raise OpportunityContextContractError("fresh_entry owner schema mismatch")
    if entry.get("state") == "UNAVAILABLE_DATA" and entry.get("availability_id") is None:
        if entry.get("entry_open") is not None or entry.get("reason") != "B4_NOT_AVAILABLE":
            raise OpportunityContextContractError(
                "missing B4 must remain unknown rather than a false verdict"
            )
    elif entry.get("entry_open") not in (True, False):
        raise OpportunityContextContractError("owner-issued B4 entry_open must be boolean")

    if payload.get("user_state") != _UNJOINED_USER_STATE:
        raise OpportunityContextContractError("private user state must remain unjoined")
    if payload.get("evidence_summary") != _UNJOINED_EVIDENCE:
        raise OpportunityContextContractError("cross-domain evidence must remain unjoined")
    if payload.get("forecast") != _UNQUALIFIED_FORECAST:
        raise OpportunityContextContractError("unqualified forecast must remain null")


__all__ = [
    "SCHEMA",
    "OpportunityContextContractError",
    "compose_opportunity_context",
    "validate_opportunity_context",
]
