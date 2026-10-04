"""Deterministic policy-owner facts for Prophet B4 Availability.

This module owns only strategy policy facts that no incumbent data/geometry owner
can truthfully answer.  The first bounded vertical is session eligibility for
Early Leadership / Sector Rotation.  It composes the existing NYSE full-day
session calendar with an era-stamped RTH execution-window law frozen here; it does
not promote a descriptive/coverage helper into gate authority, create a second
session-existence calendar, quote source, entry-geometry engine, ranking signal,
plan, or trade authority.

Extended-hours eligibility intentionally fails closed in v2.  The repository's
extended-quote plane is not yet an accepted execution/fillability source for this
strategy, so premarket/after-hours opportunity research cannot be laundered into
B4 entry permission.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time
from hashlib import sha256
import json
import math
from typing import Any
from zoneinfo import ZoneInfo

from engine.prophet_strategy_definition import (
    ENTRY_POLICY_VERSION,
    STRATEGY_ID,
    validate_strategy_definition,
)
from lib import nyse_calendar

SCHEMA = "prophet.entry_policy_fact/v1"
SESSION_POLICY_VERSION = "early-leadership-sector-rotation-session-rth-v2"
SESSION_POLICY_ERA = "NYSE_RTH_2026"
GATE = "session_eligibility"

RISK_POLICY_VERSION = "early-leadership-sector-rotation-risk-atr-v1"
RISK_POLICY_ERA = "B4_RISK_ATR_2_0_2026_09_22"
RISK_GATE = "risk_ceiling"
RISK_ATR_CEILING = 2.0

LIQUIDITY_POLICY_VERSION = "early-leadership-sector-rotation-nbbo-fillability-v1"
LIQUIDITY_POLICY_ERA = "B4_NBBO_FILLABILITY_2026_09_22"
LIQUIDITY_GATE = "liquidity_fillability"
LIQUIDITY_MAX_FULL_SPREAD_BPS = 50.0
LIQUIDITY_MAX_NBBO_AGE_SECONDS = 300.0
LIQUIDITY_NBBO_SOURCE = "polygon_lastQuote"
LIQUIDITY_SOURCE_LICENSE = "vendor_terms_personal_use"

GAP_POLICY_VERSION = "early-leadership-sector-rotation-gap-velocity-v1"
GAP_POLICY_ERA = "B4_GAP_VELOCITY_ATR_2026_09_22"
GAP_GATE = "gap_velocity"
GAP_MAX_OPEN_ATR = 1.5
GAP_MAX_MOVE_FROM_OPEN_ATR = 1.0
GAP_MAX_SESSION_MOVE_ATR = 1.5

ET = ZoneInfo("America/New_York")
_RTH_OPEN_ET = time(9, 30)
_RTH_REGULAR_CLOSE_ET = time(16, 0)
_RTH_EARLY_CLOSE_ET = time(13, 0)
_SUPPORTED_SESSION_YEARS = frozenset({2026})
# Exact shortened sessions for the bounded execution-policy era.  2026-07-03 is
# a full closure (Independence Day observed), not an early close, and is therefore
# intentionally absent.  Extending this set/year is an explicit policy mutation.
_EARLY_CLOSE_DATES = frozenset({date(2026, 11, 27), date(2026, 12, 24)})


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


def _execution_session_window_et(session: date) -> tuple[datetime, datetime]:
    """Return the B4-owned RTH execution window for the frozen policy era.

    ``lib.nyse_calendar`` remains the owner of whether a cash-equity session exists.
    The clock window is intentionally owned here because the repository's other
    early-close helper is descriptive/coverage-tier and explicitly has no gate
    authority.  An unsupported year is unavailable policy, never a guessed PASS.
    """
    if session.year not in _SUPPORTED_SESSION_YEARS:
        raise EntryPolicyContractError(
            f"market_session outside {SESSION_POLICY_ERA} session policy era"
        )
    close = _RTH_EARLY_CLOSE_ET if session in _EARLY_CLOSE_DATES else _RTH_REGULAR_CLOSE_ET
    return (
        datetime.combine(session, _RTH_OPEN_ET, tzinfo=ET),
        datetime.combine(session, close, tzinfo=ET),
    )


def _policy_material(strategy_definition_id: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "gate": GATE,
        "strategy_id": STRATEGY_ID,
        "strategy_definition_id": strategy_definition_id,
        "entry_policy_version": ENTRY_POLICY_VERSION,
        "session_policy_version": SESSION_POLICY_VERSION,
        "session_policy_era": SESSION_POLICY_ERA,
        "calendar_owner": "lib.nyse_calendar.is_session",
        "execution_window_owner": "engine.prophet_entry_policy._execution_session_window_et",
        "execution_schedule_source": "NYSE_HOLIDAYS_AND_TRADING_HOURS_2026",
        "execution_schedule_verified_on": "2026-09-22",
        "supported_session_years": sorted(_SUPPORTED_SESSION_YEARS),
        "rth_open_et": _RTH_OPEN_ET.isoformat(),
        "regular_close_et": _RTH_REGULAR_CLOSE_ET.isoformat(),
        "early_close_et": _RTH_EARLY_CLOSE_ET.isoformat(),
        "early_close_dates": sorted(day.isoformat() for day in _EARLY_CLOSE_DATES),
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

    V2 permits new-entry Availability only during the frozen-era NYSE regular-hours
    execution window for the exact market session.  Holiday/weekend dates, premarket,
    after-hours, early-close tail time, and session/date mismatches fail closed.
    """

    validate_strategy_definition(strategy_definition)
    strategy_definition_id = str(strategy_definition["strategy_definition_id"])
    decision = _parse_decision_at(decision_at)
    session = _parse_session(market_session)
    if session.year not in _SUPPORTED_SESSION_YEARS:
        raise EntryPolicyContractError(
            f"market_session outside {SESSION_POLICY_ERA} session policy era"
        )
    decision_et = decision.astimezone(ET)

    policy_material = _policy_material(strategy_definition_id)
    policy_receipt = "pep:" + sha256(_canonical_json(policy_material).encode("utf-8")).hexdigest()

    session_open: datetime | None = None
    session_close: datetime | None = None
    verdict = "FAIL"
    phase = "NON_SESSION"
    reason = "NON_SESSION_DATE"

    if nyse_calendar.is_session(session):
        session_open, session_close = _execution_session_window_et(session)
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


def _finite_positive_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EntryPolicyContractError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise EntryPolicyContractError(f"{field} must be finite and > 0")
    return number


def _risk_policy_material(strategy_definition_id: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "gate": RISK_GATE,
        "strategy_id": STRATEGY_ID,
        "strategy_definition_id": strategy_definition_id,
        "entry_policy_version": ENTRY_POLICY_VERSION,
        "horizon": "2_15_SESSIONS",
        "horizon_role": "new_entry",
        "scientific_status": "CONTROL_ONLY",
        "authority_tier": "SHADOW_ONLY",
        "risk_policy_version": RISK_POLICY_VERSION,
        "risk_policy_era": RISK_POLICY_ERA,
        "method": "STRUCTURAL_INVALIDATION_DISTANCE_ATR",
        "risk_atr_ceiling": RISK_ATR_CEILING,
        "threshold_status": "INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED",
        "calibration_requirement": "PROSPECTIVE_OR_OOS_SAME_TAPE_WITH_COSTS",
        "geometry_owner": "incumbent_entry_owner_invalidation",
        "volatility_input": "owner_supplied_atr",
        "universal_percent_ceiling": None,
        "authority": {
            "can_rank": False,
            "can_admit_candidate": False,
            "can_size": False,
            "can_execute": False,
            "can_trade": False,
        },
    }


def evaluate_risk_ceiling(
    *,
    strategy_definition: Mapping[str, Any],
    current_price: float,
    invalidation_price: float,
    atr: float,
) -> dict[str, object]:
    """Return the shadow/control B4 ``risk_ceiling`` owner fact.

    The policy deliberately avoids a universal percent-of-price stop rule.  It
    measures the incumbent structural invalidation distance in ATR units and
    applies one era-stamped operation constant.  The constant is not a calibrated
    optimum and cannot establish promotion, sizing, execution or trade authority.
    """

    validate_strategy_definition(strategy_definition)
    strategy_definition_id = str(strategy_definition["strategy_definition_id"])
    price = _finite_positive_number(current_price, "current_price")
    invalidation = _finite_positive_number(invalidation_price, "invalidation_price")
    atr_value = _finite_positive_number(atr, "atr")

    risk_distance = price - invalidation
    risk_atr_raw = risk_distance / atr_value
    risk_pct_raw = 100.0 * risk_distance / price

    if risk_distance <= 0:
        verdict = "FAIL"
        reason = "STRUCTURAL_INVALIDATION_NOT_BELOW_PRICE"
    elif risk_atr_raw <= RISK_ATR_CEILING:
        verdict = "PASS"
        reason = "STRUCTURAL_RISK_WITHIN_ATR_CEILING"
    else:
        verdict = "FAIL"
        reason = "STRUCTURAL_RISK_ABOVE_ATR_CEILING"

    policy_material = _risk_policy_material(strategy_definition_id)
    policy_receipt = "pep:" + sha256(_canonical_json(policy_material).encode("utf-8")).hexdigest()

    payload = {
        **policy_material,
        "current_price": price,
        "invalidation_price": invalidation,
        "atr": atr_value,
        "risk_to_invalidation_atr": round(risk_atr_raw, 6),
        "risk_to_invalidation_pct": round(risk_pct_raw, 6),
        "verdict": verdict,
        "reason": reason,
        "policy_receipt": policy_receipt,
    }
    payload["fact_receipt"] = (
        "pepf:" + sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    )
    return payload



def _liquidity_policy_material(strategy_definition_id: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "gate": LIQUIDITY_GATE,
        "strategy_id": STRATEGY_ID,
        "strategy_definition_id": strategy_definition_id,
        "entry_policy_version": ENTRY_POLICY_VERSION,
        "horizon": "2_15_SESSIONS",
        "horizon_role": "new_entry",
        "scientific_status": "CONTROL_ONLY",
        "authority_tier": "SHADOW_ONLY",
        "liquidity_policy_version": LIQUIDITY_POLICY_VERSION,
        "liquidity_policy_era": LIQUIDITY_POLICY_ERA,
        "method": "DECISION_TIME_NBBO_SPREAD_AND_AGE_CONTROL",
        "max_full_spread_bps": LIQUIDITY_MAX_FULL_SPREAD_BPS,
        "max_nbbo_age_seconds": LIQUIDITY_MAX_NBBO_AGE_SECONDS,
        "required_nbbo_source": LIQUIDITY_NBBO_SOURCE,
        "source_license": LIQUIDITY_SOURCE_LICENSE,
        "threshold_status": "INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED",
        "threshold_rationale": "INITIAL_CONTROL_NOT_DERIVED_FROM_REPLAY_COST_TIERS",
        "calibration_requirement": "PROSPECTIVE_OR_OOS_SAME_TAPE_WITH_COSTS_AND_CAPACITY",
        "capacity_status": "NOT_MODELED_IN_V1",
        "basis_precondition": "REQUIRE_SEPARATE_ACCEPTED_IDENTITY_BASIS_OWNER",
        "authority": {
            "can_rank": False,
            "can_admit_candidate": False,
            "can_size": False,
            "can_execute": False,
            "can_trade": False,
        },
    }


def evaluate_liquidity_fillability(
    *,
    strategy_definition: Mapping[str, Any],
    decision_at: str,
    bid_price: float,
    ask_price: float,
    nbbo_asof: str,
    nbbo_source: str,
    source_license: str,
) -> dict[str, object]:
    """Return the shadow/control B4 ``liquidity_fillability`` owner fact.

    V1 deliberately asks only whether the observed decision-time NBBO is fresh and
    narrow enough for the first control.  It does not claim size/capacity, and the
    spread/age constants are operation constants pending prospective same-tape
    calibration.  Missing source, rights, basis or quote evidence is unavailable
    policy and must fail closed upstream rather than being repaired here.
    """

    validate_strategy_definition(strategy_definition)
    strategy_definition_id = str(strategy_definition["strategy_definition_id"])
    bid = _finite_positive_number(bid_price, "bid_price")
    ask = _finite_positive_number(ask_price, "ask_price")
    if ask <= bid:
        raise EntryPolicyContractError("ask_price must be > bid_price")
    if nbbo_source != LIQUIDITY_NBBO_SOURCE:
        raise EntryPolicyContractError(
            f"nbbo_source must be {LIQUIDITY_NBBO_SOURCE!r} for {LIQUIDITY_POLICY_ERA}"
        )
    if source_license != LIQUIDITY_SOURCE_LICENSE:
        raise EntryPolicyContractError(
            f"source_license must be {LIQUIDITY_SOURCE_LICENSE!r} for {LIQUIDITY_POLICY_ERA}"
        )

    decision = _parse_decision_at(decision_at)
    nbbo_time = _parse_decision_at(nbbo_asof)
    age_seconds_raw = (decision - nbbo_time).total_seconds()
    if age_seconds_raw < 0:
        raise EntryPolicyContractError("nbbo_asof cannot be after decision_at")

    midpoint = (bid + ask) / 2.0
    full_spread_bps_raw = 10_000.0 * (ask - bid) / midpoint
    half_spread_bps_raw = full_spread_bps_raw / 2.0

    if age_seconds_raw > LIQUIDITY_MAX_NBBO_AGE_SECONDS:
        verdict = "FAIL"
        reason = "NBBO_TOO_STALE_FOR_FILLABILITY_CONTROL"
    elif full_spread_bps_raw > LIQUIDITY_MAX_FULL_SPREAD_BPS:
        verdict = "FAIL"
        reason = "NBBO_SPREAD_ABOVE_FILLABILITY_CONTROL"
    else:
        verdict = "PASS"
        reason = "NBBO_FRESH_AND_WITHIN_SPREAD_CONTROL"

    policy_material = _liquidity_policy_material(strategy_definition_id)
    policy_receipt = "pep:" + sha256(_canonical_json(policy_material).encode("utf-8")).hexdigest()
    payload = {
        **policy_material,
        "decision_at": decision.isoformat(),
        "nbbo_asof": nbbo_time.isoformat(),
        "nbbo_age_seconds": round(age_seconds_raw, 6),
        "bid_price": bid,
        "ask_price": ask,
        "midpoint_price": round(midpoint, 6),
        "full_spread_bps": round(full_spread_bps_raw, 6),
        "half_spread_bps": round(half_spread_bps_raw, 6),
        "nbbo_source": nbbo_source,
        "verdict": verdict,
        "reason": reason,
        "policy_receipt": policy_receipt,
    }
    payload["fact_receipt"] = (
        "pepf:" + sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    )
    return payload


def _gap_policy_material(strategy_definition_id: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "gate": GAP_GATE,
        "strategy_id": STRATEGY_ID,
        "strategy_definition_id": strategy_definition_id,
        "entry_policy_version": ENTRY_POLICY_VERSION,
        "horizon": "2_15_SESSIONS",
        "horizon_role": "new_entry",
        "scientific_status": "CONTROL_ONLY",
        "authority_tier": "SHADOW_ONLY",
        "gap_policy_version": GAP_POLICY_VERSION,
        "gap_policy_era": GAP_POLICY_ERA,
        "method": "OPEN_GAP_AND_DECISION_TIME_VELOCITY_ATR_CONTROL",
        "max_open_gap_atr": GAP_MAX_OPEN_ATR,
        "max_move_from_open_atr": GAP_MAX_MOVE_FROM_OPEN_ATR,
        "max_session_move_atr": GAP_MAX_SESSION_MOVE_ATR,
        "threshold_status": "INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED",
        "threshold_rationale": "INITIAL_CONTROL_NOT_DERIVED_FROM_STOCK_IDENTITY_OR_REPLAY_THRESHOLDS",
        "calibration_requirement": "PROSPECTIVE_OR_OOS_SAME_TAPE_WITH_COSTS",
        "price_family_precondition": "REQUIRE_SEPARATE_ACCEPTED_IDENTITY_BASIS_OWNER",
        "direction_semantics": "ABSOLUTE_DISLOCATION_CONTROL",
        "authority": {
            "can_rank": False,
            "can_admit_candidate": False,
            "can_size": False,
            "can_execute": False,
            "can_trade": False,
        },
    }


def evaluate_gap_velocity(
    *,
    strategy_definition: Mapping[str, Any],
    current_price: float,
    day_open: float,
    prev_close: float,
    atr: float,
) -> dict[str, object]:
    """Return the shadow/control B4 ``gap_velocity`` owner fact.

    The first control measures absolute open-gap, move-from-open and total session
    displacement in owner-supplied ATR units.  The constants are deliberately
    uncalibrated operation constants; they cannot establish promotion or waive the
    separate identity/basis, quote freshness, geometry or liquidity owners.
    """

    validate_strategy_definition(strategy_definition)
    strategy_definition_id = str(strategy_definition["strategy_definition_id"])
    price = _finite_positive_number(current_price, "current_price")
    open_price = _finite_positive_number(day_open, "day_open")
    prior = _finite_positive_number(prev_close, "prev_close")
    atr_value = _finite_positive_number(atr, "atr")

    open_gap_atr_raw = abs(open_price - prior) / atr_value
    move_from_open_atr_raw = abs(price - open_price) / atr_value
    session_move_atr_raw = abs(price - prior) / atr_value

    if open_gap_atr_raw > GAP_MAX_OPEN_ATR:
        verdict = "FAIL"
        reason = "OPEN_GAP_ABOVE_ATR_CONTROL"
    elif move_from_open_atr_raw > GAP_MAX_MOVE_FROM_OPEN_ATR:
        verdict = "FAIL"
        reason = "MOVE_FROM_OPEN_ABOVE_ATR_CONTROL"
    elif session_move_atr_raw > GAP_MAX_SESSION_MOVE_ATR:
        verdict = "FAIL"
        reason = "SESSION_MOVE_ABOVE_ATR_CONTROL"
    else:
        verdict = "PASS"
        reason = "GAP_AND_VELOCITY_WITHIN_ATR_CONTROL"

    policy_material = _gap_policy_material(strategy_definition_id)
    policy_receipt = "pep:" + sha256(_canonical_json(policy_material).encode("utf-8")).hexdigest()
    payload = {
        **policy_material,
        "current_price": price,
        "day_open": open_price,
        "prev_close": prior,
        "atr": atr_value,
        "open_gap_atr": round(open_gap_atr_raw, 6),
        "move_from_open_atr": round(move_from_open_atr_raw, 6),
        "session_move_atr": round(session_move_atr_raw, 6),
        "verdict": verdict,
        "reason": reason,
        "policy_receipt": policy_receipt,
    }
    payload["fact_receipt"] = (
        "pepf:" + sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    )
    return payload
