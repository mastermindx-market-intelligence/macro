"""Fail-closed catalyst readiness projection for Leadership Lab.

The incumbent Live Entry Radar owns catalyst context and its live episode identity.
This adapter only reports whether that owner has a usable live-source lane. It never
substitutes Prophet candidate episodes, constructs event context, infers absence, or
calculates a catalyst likelihood.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime

from engine.leadership_lab.measurement import session_date


_AUTHORITY = {
    "rank": False,
    "entry": False,
    "size": False,
    "execution": False,
    "trade": False,
}


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _aware(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return text


def _count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _ledger_state(ledger: object) -> dict:
    if not isinstance(ledger, Mapping) or ledger.get("schema") != "entry_radar.w5_ledger_state/v1":
        return {
            "status": "UNAVAILABLE_OWNER_LEDGER",
            "owner_state": None,
            "session": None,
            "updated_at": None,
            "observed_spool_events": None,
            "live_forward_rows": None,
            "forward_rows_total": None,
        }
    try:
        session = session_date(ledger.get("session"))
    except (TypeError, ValueError):
        session = None
    state = _text(ledger.get("state"))
    updated = _aware(ledger.get("updated_at"))
    observed = _count(ledger.get("observed_spool_events"))
    live_rows = _count(ledger.get("live_forward_rows"))
    total = _count(ledger.get("forward_rows_total"))
    if (
        session is None or state is None or updated is None
        or observed is None or live_rows is None or total is None
    ):
        status = "UNAVAILABLE_OWNER_LEDGER"
    elif state == "WAITING_FOR_LIVE_SOURCE":
        if observed == 0 and live_rows == 0 and total == 0 and ledger.get("spool_dir") is None:
            status = "UNAVAILABLE_LIVE_ENTRY_RADAR_SOURCE"
        else:
            status = "UNAVAILABLE_OWNER_LEDGER"
    else:
        status = "OWNER_STATE_PRESENT_CONTEXT_NOT_CONNECTED"
    return {
        "status": status,
        "owner_state": state,
        "session": session,
        "updated_at": updated,
        "observed_spool_events": observed,
        "live_forward_rows": live_rows,
        "forward_rows_total": total,
    }


def attach_catalyst_readiness(view: Mapping, ledger: Mapping | None) -> dict:
    """Attach source-readiness only; per-name context remains owner-supplied."""
    if (
        not isinstance(view, Mapping)
        or view.get("schema") != "mastermind.leadership_lab.recovery.v1"
        or not isinstance(view.get("current_context"), Mapping)
    ):
        raise ValueError("Leadership Lab current-context view required")
    rows = view.get("rows")
    shortlist = view.get("shortlist")
    if not isinstance(rows, list) or not isinstance(shortlist, list):
        raise ValueError("Leadership Lab rows and shortlist required")

    state = _ledger_state(ledger)
    if state["status"] == "UNAVAILABLE_LIVE_ENTRY_RADAR_SOURCE":
        reason = "LIVE_ENTRY_RADAR_LIVE_EPISODE_SOURCE_NOT_AVAILABLE"
    elif state["status"] == "OWNER_STATE_PRESENT_CONTEXT_NOT_CONNECTED":
        reason = "LIVE_CATALYST_CONTEXT_NOT_CONNECTED"
    else:
        reason = "CATALYST_OWNER_LEDGER_UNAVAILABLE"

    per_row = {
        "status": "UNAVAILABLE",
        "reason": reason,
        "catalyst_probability": None,
        "absence_inference_allowed": False,
        "authority": dict(_AUTHORITY),
    }

    result = deepcopy(dict(view))
    def enrich(raw: object) -> dict:
        if not isinstance(raw, Mapping):
            raise ValueError("Leadership Lab row must be a mapping")
        row = deepcopy(dict(raw))
        current = row.get("current_context")
        if not isinstance(current, Mapping):
            raise ValueError("Leadership Lab row current_context required")
        current = deepcopy(dict(current))
        current["catalyst"] = deepcopy(per_row)
        row["current_context"] = current
        return row

    result["rows"] = [enrich(row) for row in rows]
    result["shortlist"] = [enrich(row) for row in shortlist]
    result["current_context"] = deepcopy(dict(result["current_context"]))
    result["current_context"]["catalyst"] = {
        **state,
        "mode": "INCUMBENT_LIVE_ENTRY_RADAR_OWNER_ONLY",
        "absence_inference_allowed": False,
        "prophet_episode_substitution_allowed": False,
        "catalyst_probability": None,
        "authority": dict(_AUTHORITY),
    }
    return result
