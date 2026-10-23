"""Pure rates context for existing Entry Radar replay episodes.

Research context only: no I/O, candidate selection, outcome attachment, scoring,
ranking, gating, sizing, trade authority, or historical-vintage certification.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime, timezone
import math
from typing import Any

SCHEMA = "entry_radar.rates_context.v1"
SOURCE_SCHEMA = "yield_momentum.v1"
TENORS = ("2y", "5y", "10y", "20y", "30y")
AUTHORITY = {
    "can_rank": False,
    "can_score": False,
    "can_size": False,
    "can_gate": False,
    "can_trade": False,
}


def _day(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    try:
        import pandas as pd
        stamp = pd.Timestamp(value)
        return None if pd.isna(stamp) else stamp.date()
    except Exception:
        return None


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _tenor_row(tenor: str, source: Mapping[str, Any], *,
               decision_session: date,
               decision_at: datetime | None) -> dict[str, Any]:
    issues: list[str] = []
    observed = source.get("last_observed")
    observed = observed if isinstance(observed, Mapping) else {}
    obs_day = _day(observed.get("as_of") or source.get("as_of"))
    level = _number(observed.get("level"))
    if level is None:
        level = _number(source.get("level"))
    previous_day = _day(observed.get("previous_as_of"))
    previous_level = _number(observed.get("previous_level"))
    available = _instant(source.get("available_at"))
    historical = bool(source.get("historical_availability_qualified"))
    if observed:
        historical = historical and bool(
            observed.get("historical_availability_qualified"))

    usable = True
    replay_qualified = False
    if obs_day is None or level is None:
        issues.append("missing_observation")
        usable = False
    elif obs_day > decision_session:
        issues.append("observation_after_decision_session")
        usable = False
    elif obs_day == decision_session:
        if not historical or decision_at is None or available is None:
            issues.append("same_session_without_intraday_receipt")
            usable = False
        elif available > decision_at:
            issues.append("availability_after_decision")
            usable = False
        else:
            replay_qualified = True
    elif historical and available is not None and decision_at is not None:
        replay_qualified = available <= decision_at

    change_bp = None
    velocity_raw = source.get("velocity_bp")
    velocity_raw = velocity_raw if isinstance(velocity_raw, Mapping) else {}
    velocity = {h: _number(velocity_raw.get(h)) for h in ("5d", "22d", "63d")}
    acceleration = _number(source.get("acceleration_bp"))
    source_turn = source.get("turn_watch")
    source_turn = source_turn if isinstance(source_turn, str) else None
    path_qualified = bool(source.get("path_qualified"))

    if previous_day is not None and previous_level is not None and level is not None:
        if previous_day >= obs_day:
            issues.append("invalid_previous_observation")
        else:
            change_bp = round((level - previous_level) * 100.0, 1)
            declared = _number(observed.get("change_bp"))
            if declared is not None and declared != change_bp:
                issues.append("declared_change_mismatch")

    return {
        "source_column": source.get("source_column") or ("us" + tenor),
        "source_id": source.get("source_id"),
        "observation_date": obs_day.isoformat() if obs_day else None,
        "level": level if usable else None,
        "last_change_bp": change_bp if usable else None,
        "velocity_bp": velocity if usable else {h: None for h in velocity},
        "acceleration_bp": acceleration if usable else None,
        "source_turn_watch": source_turn if usable else None,
        "path_qualified": bool(usable and path_qualified),
        "previous_observation_date": previous_day.isoformat() if previous_day else None,
        "previous_level": previous_level if usable else None,
        "age_calendar_days": (
            (decision_session - obs_day).days if usable and obs_day else None),
        "availability_used": (
            available.isoformat() if usable and replay_qualified and available else None),
        "usable_for_corrected_history": bool(usable),
        "as_observed_qualified": bool(usable and replay_qualified),
        "historical_availability_qualified": bool(historical),
        "issues": issues,
    }


def project(artifact: Any, *, decision_session: date | str,
            decision_at: str | datetime | None = None) -> dict[str, Any]:
    """Project raw dated rate facts onto one already-selected opportunity date."""
    session = _day(decision_session)
    raw = artifact if isinstance(artifact, Mapping) else {}
    if raw.get("schema") != SOURCE_SCHEMA or session is None:
        issues = ["unsupported_source_schema"] if raw.get("schema") != SOURCE_SCHEMA else [
            "invalid_decision_session"]
        return {
            "schema": SCHEMA, "status": "unavailable", "decision_session": None,
            "tenors": {}, "coverage": {"usable_tenors": 0, "easing_tenors": 0,
                                      "rising_tenors": 0, "flat_tenors": 0},
            "as_observed_replay_certified": False,
            "authority": dict(AUTHORITY), "issues": issues,
        }
    decision_dt = (
        decision_at.astimezone(timezone.utc)
        if isinstance(decision_at, datetime) and decision_at.tzinfo is not None
        else _instant(decision_at)
    )
    rows = raw.get("series")
    rows = rows if isinstance(rows, Mapping) else {}
    tenors = {
        tenor: _tenor_row(tenor, row, decision_session=session,
                          decision_at=decision_dt)
        for tenor in TENORS
        if isinstance((row := rows.get(tenor)), Mapping)
    }
    usable = [row for row in tenors.values()
              if row["usable_for_corrected_history"]]
    changes = [row["last_change_bp"] for row in usable
               if row["last_change_bp"] is not None]
    coverage = {
        "usable_tenors": len(usable),
        "easing_tenors": sum(v < 0 for v in changes),
        "rising_tenors": sum(v > 0 for v in changes),
        "flat_tenors": sum(v == 0 for v in changes),
    }
    front_long_state = "unavailable"
    front, long = tenors.get("2y"), tenors.get("10y")
    if front and long and front["usable_for_corrected_history"] and long["usable_for_corrected_history"]:
        fchg, lchg = front["last_change_bp"], long["last_change_bp"]
        if fchg is not None and lchg is not None:
            if fchg < 0 and lchg < 0:
                front_long_state = "both_easing"
            elif fchg > 0 and lchg > 0:
                front_long_state = "both_rising"
            elif fchg < 0 < lchg:
                front_long_state = "front_easing_long_rising"
            elif lchg < 0 < fchg:
                front_long_state = "front_rising_long_easing"
            else:
                front_long_state = "mixed_flat"
    return {
        "schema": SCHEMA,
        "status": "available_context" if usable else "unavailable",
        "decision_session": session.isoformat(),
        "decision_at": decision_dt.isoformat() if decision_dt else None,
        "tenors": tenors,
        "coverage": coverage,
        "front_long_state": front_long_state,
        "as_observed_replay_certified": bool(
            usable and all(row["as_observed_qualified"] for row in usable)),
        "authority": dict(AUTHORITY),
        "issues": [],
        "limitations": [
            "Corrected-history context is not historical decision-time proof.",
            "No same-session use without a qualified prior availability instant.",
            "Tenor counts are descriptive and are not a fused score or signal.",
        ],
    }


def attach(record: Mapping[str, Any], artifact: Any, *,
           decision_at: str | datetime | None = None) -> dict[str, Any]:
    """Copy one existing replay row and append context without changing identity."""
    out = deepcopy(dict(record))
    out["rates_context"] = project(
        artifact, decision_session=record.get("session"),
        decision_at=decision_at)
    return out
