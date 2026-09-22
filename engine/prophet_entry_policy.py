"""Deterministic policy-owner facts for Prophet B4 Availability.

This module owns only strategy policy facts that no incumbent data/geometry owner
can truthfully answer.  The first bounded vertical is session eligibility for
Early Leadership / Sector Rotation.  It composes the existing NYSE session
calendar and early-close-aware RTH window; it does not create a second calendar,
quote source, entry-geometry engine, ranking signal, plan, or trade authority.

Extended-hours eligibility intentionally fails closed in v1.  The repository's
extended-quote plane is not yet an accepted execution/fillability source for this
strategy, so premarket/after-hours opportunity research cannot be laundered into
B4 entry permission.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from hashlib import sha256
import json
from typing import Any

from engine.prophet_strategy_definition import (
    ENTRY_POLICY_VERSION,
    STRATEGY_ID,
    validate_strategy_definition,
)
from engine.session_digest import ET, session_window_et
from lib import nyse_calendar

SCHEMA = "prophet.entry_policy_fact/v1"
SESSION_POLICY_VERSION = "early-leadership-sector-rotation-session-rth-v1"
GATE = "session_eligibility"


class EntryPolicyContractError(ValueError):
    """Raised when an entry-policy fact cannot be proven from owner inputs."""


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
        raise EntryPolicyContractError(f"entry policy is not canonical JSON: {exc}") from exc


def _parse_decision_at(value: object) -> datetime:
    if not isinstance(value, str):
        raise EntryPolicyContractError("decision_at must be an offset-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EntryPolicyContractError("decision_at must be an offset-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EntryPolicyContractError("decision_at must be offset-aware")
    return parsed


def _parse_session(value: object) -> date:
    if not isinstance(value, str):
        raise EntryPolicyContractError("market_session must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise EntryPolicyContractError("market_session must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise EntryPolicyContractError("market_session must be canonical YYYY-MM-DD")
    return parsed


def _policy_material(strategy_definition_id: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "gate": GATE,
        "strategy_id": STRATEGY_ID,
        "strategy_definition_id": strategy_definition_id,
        "entry_policy_version": ENTRY_POLICY_VERSION,
        "session_policy_version": SESSION_POLICY_VERSION,
        "calendar_owner": "lib.nyse_calendar.is_session",
        "window_owner": "engine.session_digest.session_window_et",
        "window_semantics": "[open,close)",
        "extended_hours": "FAIL_CLOSED_PENDING_ACCEPTED_SOURCE_AND_FILLABILITY",
        "authority": {
            "can_rank": False,
            "can_admit_candidate": False,
            "can_size": False,
            "can_execute": False,
            "can_trade": False,
        },
    }


def evaluate_session_eligibility(
    *,
    strategy_definition: Mapping[str, Any],
    decision_at: str,
    market_session: str,
) -> dict[str, object]:
    """Return one deterministic B4 ``session_eligibility`` owner fact.

    V1 permits new-entry Availability only during the actual NYSE regular-hours
    window for the exact market session.  Holiday/weekend dates, premarket,
    after-hours, early-close tail time, and session/date mismatches fail closed.
    """

    validate_strategy_definition(strategy_definition)
    strategy_definition_id = str(strategy_definition["strategy_definition_id"])
    decision = _parse_decision_at(decision_at)
    session = _parse_session(market_session)
    decision_et = decision.astimezone(ET)

    policy_material = _policy_material(strategy_definition_id)
    policy_receipt = "pep:" + sha256(_canonical_json(policy_material).encode("utf-8")).hexdigest()

    session_open: datetime | None = None
    session_close: datetime | None = None
    verdict = "FAIL"
    phase = "NON_SESSION"
    reason = "NON_SESSION_DATE"

    if nyse_calendar.is_session(session):
        session_open, session_close = session_window_et(session)
        if decision_et.date() != session:
            phase = "WRONG_SESSION"
            reason = "DECISION_NOT_IN_MARKET_SESSION_DATE"
        elif decision_et < session_open:
            phase = "PREMARKET"
            reason = "PREMARKET_NOT_ELIGIBLE_V1"
        elif decision_et >= session_close:
            phase = "AFTER_HOURS"
            reason = "POST_RTH_NOT_ELIGIBLE_V1"
        else:
            verdict = "PASS"
            phase = "RTH"
            reason = "INSIDE_ACTUAL_RTH_WINDOW"

    session_material = {
        "market_session": market_session,
        "session_exists": bool(nyse_calendar.is_session(session)),
        "session_open": session_open.isoformat() if session_open else None,
        "session_close": session_close.isoformat() if session_close else None,
    }
    session_receipt = "pes:" + sha256(_canonical_json(session_material).encode("utf-8")).hexdigest()

    payload = {
        **policy_material,
        "decision_at": decision.isoformat(),
        "market_session": market_session,
        "decision_et": decision_et.isoformat(),
        "session_phase": phase,
        "session_open": session_open.isoformat() if session_open else None,
        "session_close": session_close.isoformat() if session_close else None,
        "extended_hours_eligible": False,
        "verdict": verdict,
        "reason": reason,
        "policy_receipt": policy_receipt,
        "session_receipt": session_receipt,
    }
    payload["fact_receipt"] = (
        "pepf:" + sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    )
    return payload
