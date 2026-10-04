"""Prospective cross-session transfer capture harness.

Research-only and production-inert. This module enforces the source-first
prospective protocol without creating a new event, ledger, or data plane.

Stage 1: admit_source_event freezes first-disclosure source facts and protocol
eligibility only. Optional source resolution: amend_source_state can attach a
later corroboration/confirmation receipt to that same event, but may not move
the first-disclosure clock, change cohort eligibility, or mint a second event.
Stage 2: freeze_matched_controls deterministically selects the frozen prior/next
same-clock controls from completed observed SMH sessions plus admitted-event dates.
It requires an exact source-completeness cutoff and refuses to certify the cutoff's
still-open UTC calendar day, preventing a late same-day event from contaminating a control.
Stage 3: measure_us_response and measure_control_us_response read the incumbent
U.S. minute transport only and compute the already-frozen +5 to +35 minute constructions.
Stage 4: gate_hk_outcome_read validates that source admission, control selection,
and every required U.S. measurement are frozen and mutually consistent before
a downstream research scorer is allowed to open the HSI outcome.
Stage 5: score_hsi_outcome invokes that gate before transport, then reads only
ephemeral Yahoo ^HSI adjusted OHLC needed for the frozen event/control next-open
geometry. It persists nothing and emits no pooled, ranking, or trading state.

No pre-gate capture step reads Hong Kong outcomes, picks controls from outcomes, persists
vendor bars, emits alerts, ranks opportunities, or grants trading authority.

V1 primary:
    SMH return(+5 to +35) - QQQ return(+5 to +35)
V1.1 challenger:
    QQQ return(+5 to +35) - SPY return(+5 to +35)

The challenger was development-selected after HK outcomes were visible, so its
prospective clock begins strictly after the V1.1 amendment commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from research import event_microstructure_study as study  # noqa: E402
from scripts.research import replay_event_microstructure as replay  # noqa: E402

SCHEMA_ADMISSION = "research.cross_session_transfer_admission.v1"
SCHEMA_SOURCE_AMENDMENT = "research.cross_session_transfer_source_amendment.v1"
SCHEMA_CONTROLS = "research.cross_session_transfer_matched_controls.v1"
SCHEMA_US = "research.cross_session_transfer_us_measurement.v1"
SCHEMA_CONTROL_US = "research.cross_session_transfer_control_us_measurement.v1"
SCHEMA_HK_GATE = "research.cross_session_transfer_hk_outcome_gate.v1"
SCHEMA_HK_SCORE = "research.cross_session_transfer_hsi_outcome.v1"

V1_PROTOCOL_COMMIT = "0f9d4d88cf78b06ab9985d32be9df5c2bc929fd2"
V1_PROTOCOL_FROZEN_AT = datetime(2026, 9, 26, 11, 16, 23, tzinfo=timezone.utc)
V1_1_AMENDMENT_COMMIT = "d45af4450a31425a207866c33fc88a311713f7a4"
V1_1_CHALLENGER_FROZEN_AT = datetime(2026, 9, 26, 21, 41, 1, tzinfo=timezone.utc)

SOURCE_STATES = frozenset({"SOURCE_RESOLVED", "SOURCE_CONFOUNDED", "SOURCE_UNRESOLVED"})
EVENT_CLASSES = frozenset(
    {
        "physical_energy_shipping_security",
        "ceasefire_deescalation_or_escalation",
        "official_policy_or_operational_change",
    }
)
US_SYMBOLS = ("SPY", "QQQ", "SMH")
START_OFFSET_MINUTES = 5
END_OFFSET_MINUTES = 35
BAR_TOLERANCE_MINUTES = 2
MAX_CONTROL_SESSION_DISTANCE = 10
HK_LOOKAHEAD_CALENDAR_DAYS = 21

AUTHORITY = {
    "tier": "research",
    "context_only": True,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_alert": False,
    "may_execute": False,
    "may_trade": False,
    "may_write_market_memory": False,
    "may_write_qledger": False,
    "may_write_chronicle": False,
}


class CaptureContractError(ValueError):
    """Raised when prospective capture would violate the frozen protocol."""


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc(value: str, field: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise CaptureContractError(f"{field} is required")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise CaptureContractError(f"{field} must be ISO-8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise CaptureContractError(f"{field} must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _day(value: str, field: str) -> date:
    raw = str(value or "").strip()
    if not raw:
        raise CaptureContractError(f"{field} is required")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise CaptureContractError(f"{field} must be YYYY-MM-DD") from exc


def _date_values(values: Sequence[Any], field: str) -> list[date]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise CaptureContractError(f"{field} must be an array of YYYY-MM-DD values")
    out = sorted({_day(str(value), f"{field}[{idx}]") for idx, value in enumerate(values)})
    if not out:
        raise CaptureContractError(f"{field} must not be empty")
    return out


def _date_digest(values: Sequence[date]) -> str:
    payload = json.dumps(
        [value.isoformat() for value in values],
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _anchor_on_day(day: date, source_clock: datetime) -> datetime:
    return datetime(
        day.year,
        day.month,
        day.day,
        source_clock.hour,
        source_clock.minute,
        source_clock.second,
        source_clock.microsecond,
        tzinfo=timezone.utc,
    )


def admit_source_event(
    *,
    event_id: str,
    event_time: str,
    available_at: str,
    observed_at: str,
    event_class: str,
    source_state: str,
    source_name: str,
    source_ref: str,
    headline: str,
) -> dict[str, Any]:
    """Freeze source facts without touching any market outcome."""
    eid = str(event_id or "").strip()
    if not eid:
        raise CaptureContractError("event_id is required")
    if event_class not in EVENT_CLASSES:
        raise CaptureContractError(f"unsupported event_class: {event_class}")
    if source_state not in SOURCE_STATES:
        raise CaptureContractError(f"unsupported source_state: {source_state}")
    if not str(source_name or "").strip():
        raise CaptureContractError("source_name is required")
    if not str(source_ref or "").strip():
        raise CaptureContractError("source_ref is required")
    if not str(headline or "").strip():
        raise CaptureContractError("headline is required")

    event = {
        "event_id": eid,
        "event_time": _iso(_utc(event_time, "event_time")),
        "available_at": _iso(_utc(available_at, "available_at")),
        "observed_at": _iso(_utc(observed_at, "observed_at")),
    }
    known_at = study.knowledge_time(event, mode="public_reconstruction")

    primary_eligible = known_at > V1_PROTOCOL_FROZEN_AT
    challenger_eligible = known_at > V1_1_CHALLENGER_FROZEN_AT
    clean_primary = primary_eligible and source_state == "SOURCE_RESOLVED"
    state = (
        "PROSPECTIVE_V1_1"
        if challenger_eligible
        else "PROSPECTIVE_V1_ONLY"
        if primary_eligible
        else "DEVELOPMENT_ONLY"
    )

    return {
        "schema": SCHEMA_ADMISSION,
        "authority": dict(AUTHORITY),
        "state": state,
        "event_id": eid,
        "event_time": event["event_time"],
        "available_at": event["available_at"],
        "observed_at": event["observed_at"],
        "event_class": event_class,
        "source_state": source_state,
        "source_name": str(source_name).strip(),
        "source_ref": str(source_ref).strip(),
        "headline": str(headline).strip(),
        "primary_v1_eligible": primary_eligible,
        "challenger_v1_1_eligible": challenger_eligible,
        "clean_primary_eligible": clean_primary,
        "protocol_receipts": {
            "primary_v1_commit": V1_PROTOCOL_COMMIT,
            "primary_v1_frozen_at": _iso(V1_PROTOCOL_FROZEN_AT),
            "challenger_v1_1_commit": V1_1_AMENDMENT_COMMIT,
            "challenger_v1_1_frozen_at": _iso(V1_1_CHALLENGER_FROZEN_AT),
        },
        "outcome_state": "NOT_READ",
        "persistence": "none_stdout_only",
    }


def amend_source_state(
    admission: Mapping[str, Any],
    *,
    source_available_at: str,
    observed_at: str,
    source_state: str,
    source_name: str,
    source_ref: str,
    headline: str,
) -> dict[str, Any]:
    """Attach later source resolution without moving the first-disclosure event clock."""
    if admission.get("schema") != SCHEMA_ADMISSION:
        raise CaptureContractError("admission schema mismatch")
    if admission.get("outcome_state") != "NOT_READ":
        raise CaptureContractError("source-state amendment is forbidden after outcome read")
    if source_state not in SOURCE_STATES:
        raise CaptureContractError(f"unsupported source_state: {source_state}")
    if not str(source_name or "").strip():
        raise CaptureContractError("source_name is required")
    if not str(source_ref or "").strip():
        raise CaptureContractError("source_ref is required")
    if not str(headline or "").strip():
        raise CaptureContractError("headline is required")

    first_available = _utc(
        str(admission.get("available_at") or ""),
        "admission.available_at",
    )
    resolution_available = _utc(source_available_at, "source_available_at")
    resolution_observed = _utc(observed_at, "observed_at")
    if resolution_available < first_available:
        raise CaptureContractError(
            "source resolution cannot predate the frozen first-disclosure clock"
        )
    if resolution_observed < resolution_available:
        raise CaptureContractError(
            "source resolution observed_at cannot predate source_available_at"
        )

    return {
        "schema": SCHEMA_SOURCE_AMENDMENT,
        "authority": dict(AUTHORITY),
        "state": admission.get("state"),
        "event_id": str(admission.get("event_id") or ""),
        "event_time": str(admission.get("event_time") or ""),
        # First disclosure remains the only measurement/prospective anchor.
        "available_at": _iso(first_available),
        "observed_at": str(admission.get("observed_at") or ""),
        "event_class": str(admission.get("event_class") or ""),
        "source_state_before": str(admission.get("source_state") or ""),
        "source_state_after": source_state,
        "first_disclosure": {
            "source_name": str(admission.get("source_name") or ""),
            "source_ref": str(admission.get("source_ref") or ""),
            "headline": str(admission.get("headline") or ""),
        },
        "source_resolution": {
            "source_available_at": _iso(resolution_available),
            "observed_at": _iso(resolution_observed),
            "source_name": str(source_name).strip(),
            "source_ref": str(source_ref).strip(),
            "headline": str(headline).strip(),
        },
        # A later confirmation is provenance on the same event, never a fresh event.
        "independent_event": False,
        "measurement_anchor_at": _iso(first_available),
        "primary_v1_eligible": admission.get("primary_v1_eligible") is True,
        "challenger_v1_1_eligible": admission.get("challenger_v1_1_eligible") is True,
        # Preserve the admission-time clean slice. Later corroboration cannot upgrade it.
        "clean_primary_eligible": admission.get("clean_primary_eligible") is True,
        "protocol_receipts": dict(admission.get("protocol_receipts") or {}),
        "outcome_state": "NOT_READ",
        "persistence": "none_stdout_only",
    }


def _control_side(
    *,
    event_date: date,
    sessions: Sequence[date],
    excluded_dates: set[date],
    source_coverage_through: date,
    side: str,
) -> dict[str, Any]:
    if side == "prior":
        ordered = [day for day in reversed(sessions) if day < event_date]
    elif side == "next":
        ordered = [day for day in sessions if day > event_date]
    else:
        raise CaptureContractError("control side must be prior or next")

    covered = [day for day in ordered if day <= source_coverage_through]
    for distance, day in enumerate(covered[:MAX_CONTROL_SESSION_DISTANCE], start=1):
        if day not in excluded_dates:
            return {
                "status": "SELECTED",
                "control_date": day.isoformat(),
                "session_distance": distance,
            }

    if side == "next" and len(covered) < MAX_CONTROL_SESSION_DISTANCE:
        return {
            "status": "PENDING_OBSERVED_SESSION",
            "control_date": None,
            "session_distance": None,
        }
    if side == "prior" and len(covered) < MAX_CONTROL_SESSION_DISTANCE:
        return {
            "status": "DATA_GAP_INSUFFICIENT_HISTORY",
            "control_date": None,
            "session_distance": None,
        }
    return {
        "status": "DATA_GAP",
        "control_date": None,
        "session_distance": None,
    }


def freeze_matched_controls(
    admission: Mapping[str, Any],
    *,
    observed_session_dates: Sequence[Any],
    admitted_event_dates: Sequence[Any],
    source_coverage_complete_through: str,
) -> dict[str, Any]:
    """Freeze calendar-only matched controls without inspecting any return or HK outcome."""
    if admission.get("schema") != SCHEMA_ADMISSION:
        raise CaptureContractError("admission schema mismatch")
    if admission.get("primary_v1_eligible") is not True:
        raise CaptureContractError("event predates the V1 prospective boundary")
    if admission.get("outcome_state") != "NOT_READ":
        raise CaptureContractError("matched-control freeze is forbidden after outcome read")

    available = _utc(str(admission.get("available_at") or ""), "admission.available_at")
    event_date = available.date()
    coverage_cutoff = _utc(
        source_coverage_complete_through,
        "source_coverage_complete_through",
    )
    # A control date is clean only after the ENTIRE UTC calendar date has elapsed.
    # The cutoff's own date is therefore never certified, even when the cutoff is
    # late in that day. Example: 2026-10-03T00:00Z certifies through 2026-10-02.
    coverage = coverage_cutoff.date() - timedelta(days=1)
    if coverage < event_date:
        raise CaptureContractError(
            "source completeness cutoff must certify the full admitted event date"
        )

    sessions = _date_values(observed_session_dates, "observed_session_dates")
    admitted = _date_values(admitted_event_dates, "admitted_event_dates")
    excluded = set(admitted)
    excluded.add(event_date)
    admitted_with_event = sorted(excluded)

    prior = _control_side(
        event_date=event_date,
        sessions=sessions,
        excluded_dates=excluded,
        source_coverage_through=coverage,
        side="prior",
    )
    next_ = _control_side(
        event_date=event_date,
        sessions=sessions,
        excluded_dates=excluded,
        source_coverage_through=coverage,
        side="next",
    )

    for side in (prior, next_):
        if side["status"] == "SELECTED":
            day = _day(side["control_date"], "control_date")
            side["control_anchor_at"] = _iso(_anchor_on_day(day, available))
        else:
            side["control_anchor_at"] = None

    statuses = {prior["status"], next_["status"]}
    state = (
        "COMPLETE"
        if statuses == {"SELECTED"}
        else "PENDING"
        if "PENDING_OBSERVED_SESSION" in statuses
        else "PARTIAL"
        if "SELECTED" in statuses
        else "DATA_GAP"
    )

    covered_sessions = [day for day in sessions if day <= coverage]
    return {
        "schema": SCHEMA_CONTROLS,
        "authority": dict(AUTHORITY),
        "state": state,
        "event_id": str(admission.get("event_id") or ""),
        "event_available_at": _iso(available),
        "event_date": event_date.isoformat(),
        "clock_utc": available.strftime("%H:%M:%SZ"),
        "source_coverage_complete_through": _iso(coverage_cutoff),
        "source_coverage_certified_calendar_through": coverage.isoformat(),
        "selection_law": {
            "session_source": "observed_smh_sessions_only",
            "exclude_every_admitted_source_event_date": True,
            "max_observed_session_distance": MAX_CONTROL_SESSION_DISTANCE,
            "return_based_replacement_allowed": False,
        },
        "calendar_receipt": {
            "provided_session_count": len(sessions),
            "covered_session_count": len(covered_sessions),
            "first": sessions[0].isoformat(),
            "last": sessions[-1].isoformat(),
            "sha256": _date_digest(sessions),
        },
        "admitted_event_date_receipt": {
            "count_including_current_event": len(admitted_with_event),
            "sha256": _date_digest(admitted_with_event),
        },
        "prior": prior,
        "next": next_,
        "outcome_state": "NOT_READ",
        "persistence": "none_stdout_only",
    }


def _window_return(points: Sequence[Mapping[str, Any]], *, anchor: datetime) -> float | None:
    rows = study._points(points)  # noqa: SLF001 - reuse one research clock kernel
    start = study._first_at_or_after(  # noqa: SLF001
        rows,
        anchor + timedelta(minutes=START_OFFSET_MINUTES),
        tolerance_minutes=BAR_TOLERANCE_MINUTES,
    )
    end = study._first_at_or_after(  # noqa: SLF001
        rows,
        anchor + timedelta(minutes=END_OFFSET_MINUTES),
        tolerance_minutes=BAR_TOLERANCE_MINUTES,
    )
    if start is None or end is None or end[0] <= start[0]:
        return None
    return round(study._return_bps(start[1], end[1]), 6)  # noqa: SLF001


def _measure_us_constructions(
    *,
    session: date,
    anchor: datetime,
    challenger_eligible: bool,
    transport: Callable[[str, Mapping[str, Any]], list[dict[str, Any]]] | None = None,
) -> tuple[dict[str, float | None], dict[str, Any], float | None, float | None]:
    get = transport or replay.default_transport()
    fetched = {
        symbol: replay.fetch_session(symbol, session, transport=get)
        for symbol in US_SYMBOLS
    }
    returns = {
        symbol: _window_return(receipt["points"], anchor=anchor)
        for symbol, receipt in fetched.items()
    }

    primary = None
    if returns["SMH"] is not None and returns["QQQ"] is not None:
        primary = round(returns["SMH"] - returns["QQQ"], 6)

    challenger = None
    if challenger_eligible and returns["QQQ"] is not None and returns["SPY"] is not None:
        challenger = round(returns["QQQ"] - returns["SPY"], 6)
    return returns, fetched, primary, challenger


def measure_us_response(
    admission: Mapping[str, Any],
    *,
    transport: Callable[[str, Mapping[str, Any]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Measure frozen U.S. response geometry and never read HK outcomes."""
    if admission.get("schema") != SCHEMA_ADMISSION:
        raise CaptureContractError("admission schema mismatch")
    if admission.get("primary_v1_eligible") is not True:
        raise CaptureContractError("event predates the V1 prospective boundary")

    available = _utc(str(admission.get("available_at") or ""), "admission.available_at")
    session = available.date()
    returns, fetched, primary, challenger = _measure_us_constructions(
        session=session,
        anchor=available,
        challenger_eligible=admission.get("challenger_v1_1_eligible") is True,
        transport=transport,
    )

    return {
        "schema": SCHEMA_US,
        "authority": dict(AUTHORITY),
        "event_id": str(admission.get("event_id") or ""),
        "available_at": _iso(available),
        "session": session.isoformat(),
        "geometry": {
            "start_offset_minutes": START_OFFSET_MINUTES,
            "end_offset_minutes": END_OFFSET_MINUTES,
            "bar_tolerance_minutes": BAR_TOLERANCE_MINUTES,
            "reanchor_allowed": False,
        },
        "primary_v1": {
            "construction": "SMH_minus_QQQ",
            "return_bps": primary,
            "eligible": True,
        },
        "challenger_v1_1": {
            "construction": "QQQ_minus_SPY",
            "return_bps": challenger,
            "eligible": admission.get("challenger_v1_1_eligible") is True,
        },
        "nuisance_baselines_bps": {
            "SPY": returns["SPY"],
            "QQQ": returns["QQQ"],
            "SMH": returns["SMH"],
        },
        "sources": {
            symbol: {
                key: value
                for key, value in receipt.items()
                if key != "points"
            }
            for symbol, receipt in fetched.items()
        },
        "hk_outcome_state": "NOT_READ_BY_THIS_HARNESS",
        "matched_control_state": "NOT_SELECTED_BY_THIS_HARNESS",
        "persistence": "none_stdout_only",
    }


def measure_control_us_response(
    admission: Mapping[str, Any],
    control_selection: Mapping[str, Any],
    *,
    side: str,
    transport: Callable[[str, Mapping[str, Any]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Measure one frozen same-clock U.S. control and never read HK outcomes."""
    if admission.get("schema") != SCHEMA_ADMISSION:
        raise CaptureContractError("admission schema mismatch")
    if control_selection.get("schema") != SCHEMA_CONTROLS:
        raise CaptureContractError("control selection schema mismatch")
    if str(control_selection.get("event_id") or "") != str(admission.get("event_id") or ""):
        raise CaptureContractError("control selection event_id mismatch")
    if admission.get("outcome_state") != "NOT_READ":
        raise CaptureContractError("control measurement is forbidden after outcome read")
    if side not in {"prior", "next"}:
        raise CaptureContractError("control side must be prior or next")

    selected = control_selection.get(side)
    if not isinstance(selected, Mapping) or selected.get("status") != "SELECTED":
        raise CaptureContractError(f"{side} control is not frozen/selected")

    control_date = _day(str(selected.get("control_date") or ""), f"{side}.control_date")
    event_available = _utc(
        str(admission.get("available_at") or ""),
        "admission.available_at",
    )
    anchor = _anchor_on_day(control_date, event_available)
    returns, fetched, primary, challenger = _measure_us_constructions(
        session=control_date,
        anchor=anchor,
        challenger_eligible=admission.get("challenger_v1_1_eligible") is True,
        transport=transport,
    )

    return {
        "schema": SCHEMA_CONTROL_US,
        "authority": dict(AUTHORITY),
        "event_id": str(admission.get("event_id") or ""),
        "control_side": side,
        "control_date": control_date.isoformat(),
        "session_distance": selected.get("session_distance"),
        "control_anchor_at": _iso(anchor),
        "geometry": {
            "start_offset_minutes": START_OFFSET_MINUTES,
            "end_offset_minutes": END_OFFSET_MINUTES,
            "bar_tolerance_minutes": BAR_TOLERANCE_MINUTES,
            "reanchor_allowed": False,
        },
        "primary_v1": {
            "construction": "SMH_minus_QQQ",
            "return_bps": primary,
            "eligible": True,
        },
        "challenger_v1_1": {
            "construction": "QQQ_minus_SPY",
            "return_bps": challenger,
            "eligible": admission.get("challenger_v1_1_eligible") is True,
        },
        "nuisance_baselines_bps": {
            "SPY": returns["SPY"],
            "QQQ": returns["QQQ"],
            "SMH": returns["SMH"],
        },
        "sources": {
            symbol: {
                key: value
                for key, value in receipt.items()
                if key != "points"
            }
            for symbol, receipt in fetched.items()
        },
        "hk_outcome_state": "NOT_READ_BY_THIS_HARNESS",
        "persistence": "none_stdout_only",
    }


def _validate_event_us_measurement(
    admission: Mapping[str, Any],
    us_measurement: Mapping[str, Any],
) -> None:
    if us_measurement.get("schema") != SCHEMA_US:
        raise CaptureContractError("event U.S. measurement schema mismatch")
    if str(us_measurement.get("event_id") or "") != str(admission.get("event_id") or ""):
        raise CaptureContractError("event U.S. measurement event_id mismatch")
    if str(us_measurement.get("available_at") or "") != str(admission.get("available_at") or ""):
        raise CaptureContractError("event U.S. measurement clock mismatch")
    if us_measurement.get("hk_outcome_state") != "NOT_READ_BY_THIS_HARNESS":
        raise CaptureContractError("event U.S. measurement does not preserve HK outcome firewall")


def _validate_control_receipt(
    *,
    admission: Mapping[str, Any],
    controls: Mapping[str, Any],
    side: str,
    receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    selected = controls.get(side)
    if not isinstance(selected, Mapping):
        raise CaptureContractError(f"{side} control selection is malformed")
    status = str(selected.get("status") or "")
    if status == "PENDING_OBSERVED_SESSION":
        raise CaptureContractError(f"{side} matched control is still pending")
    if status == "SELECTED":
        if not isinstance(receipt, Mapping):
            raise CaptureContractError(f"{side} selected control measurement is required")
        if receipt.get("schema") != SCHEMA_CONTROL_US:
            raise CaptureContractError(f"{side} control measurement schema mismatch")
        if str(receipt.get("event_id") or "") != str(admission.get("event_id") or ""):
            raise CaptureContractError(f"{side} control measurement event_id mismatch")
        if receipt.get("control_side") != side:
            raise CaptureContractError(f"{side} control measurement side mismatch")
        if str(receipt.get("control_date") or "") != str(selected.get("control_date") or ""):
            raise CaptureContractError(f"{side} control measurement date mismatch")
        if str(receipt.get("control_anchor_at") or "") != str(selected.get("control_anchor_at") or ""):
            raise CaptureContractError(f"{side} control measurement clock mismatch")
        if receipt.get("hk_outcome_state") != "NOT_READ_BY_THIS_HARNESS":
            raise CaptureContractError(f"{side} control measurement violates HK outcome firewall")
        return {
            "status": status,
            "control_date": selected.get("control_date"),
            "measurement_present": True,
        }

    if status not in {"DATA_GAP", "DATA_GAP_INSUFFICIENT_HISTORY"}:
        raise CaptureContractError(f"unsupported {side} control status: {status}")
    if receipt is not None:
        raise CaptureContractError(
            f"{side} control is {status} and must not carry a measurement receipt"
        )
    return {
        "status": status,
        "control_date": None,
        "measurement_present": False,
    }


def gate_hk_outcome_read(
    admission: Mapping[str, Any],
    controls: Mapping[str, Any],
    us_measurement: Mapping[str, Any],
    *,
    prior_control_measurement: Mapping[str, Any] | None = None,
    next_control_measurement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a readiness receipt only after every pre-HK prerequisite is frozen."""
    if admission.get("schema") != SCHEMA_ADMISSION:
        raise CaptureContractError("admission schema mismatch")
    if admission.get("outcome_state") != "NOT_READ":
        raise CaptureContractError("HK outcome gate cannot run after outcome read")
    if controls.get("schema") != SCHEMA_CONTROLS:
        raise CaptureContractError("control selection schema mismatch")
    if str(controls.get("event_id") or "") != str(admission.get("event_id") or ""):
        raise CaptureContractError("control selection event_id mismatch")
    if controls.get("outcome_state") != "NOT_READ":
        raise CaptureContractError("control selection does not preserve outcome firewall")
    if controls.get("state") == "PENDING":
        raise CaptureContractError("matched controls are still pending")

    _validate_event_us_measurement(admission, us_measurement)
    prior = _validate_control_receipt(
        admission=admission,
        controls=controls,
        side="prior",
        receipt=prior_control_measurement,
    )
    next_ = _validate_control_receipt(
        admission=admission,
        controls=controls,
        side="next",
        receipt=next_control_measurement,
    )

    return {
        "schema": SCHEMA_HK_GATE,
        "authority": dict(AUTHORITY),
        "state": "READY_FOR_RESEARCH_HK_OUTCOME_READ",
        "event_id": str(admission.get("event_id") or ""),
        "event_available_at": str(admission.get("available_at") or ""),
        "primary_v1_eligible": admission.get("primary_v1_eligible") is True,
        "challenger_v1_1_eligible": admission.get("challenger_v1_1_eligible") is True,
        "controls": {
            "prior": prior,
            "next": next_,
        },
        "event_us_measurement_present": True,
        "research_hk_outcome_read_ready": True,
        "hk_outcome_state": "NOT_READ",
        "persistence": "none_stdout_only",
    }


def _finite_positive(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise CaptureContractError(f"{field} must be a positive finite number")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise CaptureContractError(f"{field} must be a positive finite number") from exc
    if not math.isfinite(out) or out <= 0:
        raise CaptureContractError(f"{field} must be a positive finite number")
    return out


def _hsi_rows(rows: Sequence[Mapping[str, Any]]) -> dict[date, dict[str, float]]:
    by_day: dict[date, dict[str, float]] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CaptureContractError(f"hsi_rows[{idx}] must be an object")
        day = _day(str(row.get("date") or ""), f"hsi_rows[{idx}].date")
        open_px = _finite_positive(row.get("open"), f"hsi_rows[{idx}].open")
        close_px = _finite_positive(row.get("close"), f"hsi_rows[{idx}].close")
        prior = by_day.get(day)
        current = {"open": open_px, "close": close_px}
        if prior is not None and prior != current:
            raise CaptureContractError(f"conflicting HSI OHLC for {day.isoformat()}")
        by_day[day] = current
    return by_day


def _hsi_gap(by_day: Mapping[date, Mapping[str, float]], anchor_day: date) -> dict[str, Any]:
    anchor = by_day.get(anchor_day)
    if anchor is None:
        return {
            "status": "DATA_GAP",
            "reason": "missing_anchor_close",
            "anchor_date": anchor_day.isoformat(),
            "target_open_date": None,
            "gap_bps": None,
        }
    later = sorted(day for day in by_day if day > anchor_day)
    if not later:
        return {
            "status": "DATA_GAP",
            "reason": "missing_later_open",
            "anchor_date": anchor_day.isoformat(),
            "anchor_close": anchor["close"],
            "target_open_date": None,
            "gap_bps": None,
        }
    target_day = later[0]
    target = by_day[target_day]
    return {
        "status": "MEASURED",
        "reason": None,
        "anchor_date": anchor_day.isoformat(),
        "anchor_close": anchor["close"],
        "target_open_date": target_day.isoformat(),
        "target_open": target["open"],
        "gap_bps": round((target["open"] / anchor["close"] - 1.0) * 10_000.0, 6),
    }


def _default_hsi_transport(start: date, end: date) -> list[dict[str, Any]]:
    """Ephemeral Yahoo ^HSI adjusted OHLC; no store writes."""
    import pandas as pd  # lazy: research-only path
    import yfinance as yf  # lazy: existing Yahoo provider family

    raw = yf.download(
        "^HSI",
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        return []
    if isinstance(raw.columns, pd.MultiIndex):
        if "^HSI" in set(map(str, raw.columns.get_level_values(-1))):
            raw = raw.xs("^HSI", axis=1, level=-1)
        elif "^HSI" in set(map(str, raw.columns.get_level_values(0))):
            raw = raw.xs("^HSI", axis=1, level=0)
    cols = {str(col).lower(): col for col in raw.columns}
    if "open" not in cols or "close" not in cols:
        raise CaptureContractError("Yahoo HSI response lacks Open/Close")
    out: list[dict[str, Any]] = []
    for idx, row in raw.iterrows():
        try:
            open_px = float(row[cols["open"]])
            close_px = float(row[cols["close"]])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(open_px) or not math.isfinite(close_px):
            continue
        out.append(
            {
                "date": pd.Timestamp(idx).tz_localize(None).date().isoformat(),
                "open": open_px,
                "close": close_px,
            }
        )
    return out


def _sign_agreement(us_bps: Any, hsi_bps: Any) -> bool | None:
    if us_bps is None or hsi_bps is None:
        return None
    try:
        us = float(us_bps)
        hk = float(hsi_bps)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(us) or not math.isfinite(hk):
        return None
    if us == 0 or hk == 0:
        return us == 0 and hk == 0
    return (us > 0) == (hk > 0)


def _score_pair(measurement: Mapping[str, Any], hsi: Mapping[str, Any]) -> dict[str, Any]:
    gap = hsi.get("gap_bps")
    primary = (measurement.get("primary_v1") or {}).get("return_bps")
    challenger = (measurement.get("challenger_v1_1") or {}).get("return_bps")
    return {
        "hsi": dict(hsi),
        "primary_v1": {
            "us_return_bps": primary,
            "sign_agreement": _sign_agreement(primary, gap),
        },
        "challenger_v1_1": {
            "us_return_bps": challenger,
            "eligible": (measurement.get("challenger_v1_1") or {}).get("eligible") is True,
            "sign_agreement": _sign_agreement(challenger, gap),
        },
    }


def score_hsi_outcome(
    admission: Mapping[str, Any],
    controls: Mapping[str, Any],
    us_measurement: Mapping[str, Any],
    *,
    prior_control_measurement: Mapping[str, Any] | None = None,
    next_control_measurement: Mapping[str, Any] | None = None,
    transport: Callable[[date, date], Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Read the frozen HSI endpoint only after every pre-HK receipt passes."""
    gate = gate_hk_outcome_read(
        admission,
        controls,
        us_measurement,
        prior_control_measurement=prior_control_measurement,
        next_control_measurement=next_control_measurement,
    )
    if gate.get("research_hk_outcome_read_ready") is not True:
        raise CaptureContractError("HK outcome gate did not reach ready state")

    event_day = _day(str(controls.get("event_date") or ""), "controls.event_date")
    selected_days = [event_day]
    for side in ("prior", "next"):
        selected = controls.get(side)
        if isinstance(selected, Mapping) and selected.get("status") == "SELECTED":
            selected_days.append(_day(str(selected.get("control_date") or ""), f"{side}.control_date"))

    start = min(selected_days)
    end = max(selected_days) + timedelta(days=HK_LOOKAHEAD_CALENDAR_DAYS)
    get = transport or _default_hsi_transport
    rows = list(get(start, end))
    by_day = _hsi_rows(rows)

    event_score = _score_pair(us_measurement, _hsi_gap(by_day, event_day))
    control_scores: dict[str, Any] = {}
    receipts = {
        "prior": prior_control_measurement,
        "next": next_control_measurement,
    }
    for side in ("prior", "next"):
        selected = controls.get(side) or {}
        if selected.get("status") == "SELECTED":
            day = _day(str(selected.get("control_date") or ""), f"{side}.control_date")
            receipt = receipts[side]
            assert isinstance(receipt, Mapping)  # gate proved this
            control_scores[side] = {
                "selection_status": "SELECTED",
                **_score_pair(receipt, _hsi_gap(by_day, day)),
            }
        else:
            control_scores[side] = {
                "selection_status": selected.get("status"),
                "hsi": {
                    "status": "DATA_GAP",
                    "reason": "control_not_selected",
                    "gap_bps": None,
                },
                "primary_v1": {
                    "us_return_bps": None,
                    "sign_agreement": None,
                },
                "challenger_v1_1": {
                    "us_return_bps": None,
                    "eligible": admission.get("challenger_v1_1_eligible") is True,
                    "sign_agreement": None,
                },
            }

    return {
        "schema": SCHEMA_HK_SCORE,
        "authority": dict(AUTHORITY),
        "state": "PROSPECTIVE_OUTCOME_RECORDED",
        "event_id": str(admission.get("event_id") or ""),
        "source_state": str(admission.get("source_state") or ""),
        "clean_primary_eligible": admission.get("clean_primary_eligible") is True,
        "pre_hk_gate": {
            "schema": gate.get("schema"),
            "state": gate.get("state"),
            "research_hk_outcome_read_ready": True,
        },
        "event": event_score,
        "controls": control_scores,
        "hsi_source": {
            "provider_family": "Yahoo/yfinance",
            "ticker": "^HSI",
            "auto_adjust": True,
            "persistence": "none",
            "canonical_hk_store_open_unavailable": True,
        },
        "pooled_claim_allowed": False,
        "product_or_trading_authority": False,
        "persistence": "none_stdout_only",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    admit = sub.add_parser("admit", help="freeze source facts only")
    admit.add_argument("--event-id", required=True)
    admit.add_argument("--event-time", required=True)
    admit.add_argument("--available-at", required=True)
    admit.add_argument("--observed-at", required=True)
    admit.add_argument("--event-class", required=True, choices=sorted(EVENT_CLASSES))
    admit.add_argument("--source-state", required=True, choices=sorted(SOURCE_STATES))
    admit.add_argument("--source-name", required=True)
    admit.add_argument("--source-ref", required=True)
    admit.add_argument("--headline", required=True)

    amend = sub.add_parser(
        "amend-source",
        help="record later source resolution without moving first disclosure",
    )
    amend.add_argument("--admission-file", required=True)
    amend.add_argument("--source-available-at", required=True)
    amend.add_argument("--observed-at", required=True)
    amend.add_argument("--source-state", required=True, choices=sorted(SOURCE_STATES))
    amend.add_argument("--source-name", required=True)
    amend.add_argument("--source-ref", required=True)
    amend.add_argument("--headline", required=True)

    controls = sub.add_parser(
        "freeze-controls",
        help="freeze calendar-only matched controls before any HK outcome read",
    )
    controls.add_argument("--admission-file", required=True)
    controls.add_argument("--session-calendar-file", required=True)
    controls.add_argument("--admitted-event-dates-file", required=True)
    controls.add_argument("--source-coverage-complete-through", required=True)

    measure = sub.add_parser("measure-us", help="measure fixed U.S. geometry only")
    measure.add_argument("--admission-file", required=True)

    measure_control = sub.add_parser(
        "measure-control-us",
        help="measure one already-frozen same-clock U.S. control only",
    )
    measure_control.add_argument("--admission-file", required=True)
    measure_control.add_argument("--control-selection-file", required=True)
    measure_control.add_argument("--side", required=True, choices=["prior", "next"])

    gate = sub.add_parser(
        "gate-hk-outcome",
        help="verify all frozen pre-HK receipts without reading the HK outcome",
    )
    gate.add_argument("--admission-file", required=True)
    gate.add_argument("--control-selection-file", required=True)
    gate.add_argument("--us-measurement-file", required=True)
    gate.add_argument("--prior-control-measurement-file")
    gate.add_argument("--next-control-measurement-file")

    score = sub.add_parser(
        "score-hsi",
        help="read frozen HSI outcomes only after all pre-HK receipts pass",
    )
    score.add_argument("--admission-file", required=True)
    score.add_argument("--control-selection-file", required=True)
    score.add_argument("--us-measurement-file", required=True)
    score.add_argument("--prior-control-measurement-file")
    score.add_argument("--next-control-measurement-file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "admit":
            result = admit_source_event(
                event_id=args.event_id,
                event_time=args.event_time,
                available_at=args.available_at,
                observed_at=args.observed_at,
                event_class=args.event_class,
                source_state=args.source_state,
                source_name=args.source_name,
                source_ref=args.source_ref,
                headline=args.headline,
            )
        elif args.command == "amend-source":
            with Path(args.admission_file).open("r", encoding="utf-8") as fh:
                admission = json.load(fh)
            result = amend_source_state(
                admission,
                source_available_at=args.source_available_at,
                observed_at=args.observed_at,
                source_state=args.source_state,
                source_name=args.source_name,
                source_ref=args.source_ref,
                headline=args.headline,
            )
        elif args.command == "freeze-controls":
            with Path(args.admission_file).open("r", encoding="utf-8") as fh:
                admission = json.load(fh)
            with Path(args.session_calendar_file).open("r", encoding="utf-8") as fh:
                session_payload = json.load(fh)
            with Path(args.admitted_event_dates_file).open("r", encoding="utf-8") as fh:
                event_payload = json.load(fh)
            session_dates = (
                session_payload.get("session_dates")
                if isinstance(session_payload, Mapping)
                else session_payload
            )
            admitted_dates = (
                event_payload.get("event_dates")
                if isinstance(event_payload, Mapping)
                else event_payload
            )
            result = freeze_matched_controls(
                admission,
                observed_session_dates=session_dates,
                admitted_event_dates=admitted_dates,
                source_coverage_complete_through=args.source_coverage_complete_through,
            )
        elif args.command == "measure-control-us":
            with Path(args.admission_file).open("r", encoding="utf-8") as fh:
                admission = json.load(fh)
            with Path(args.control_selection_file).open("r", encoding="utf-8") as fh:
                controls = json.load(fh)
            result = measure_control_us_response(
                admission,
                controls,
                side=args.side,
            )
        elif args.command in {"gate-hk-outcome", "score-hsi"}:
            with Path(args.admission_file).open("r", encoding="utf-8") as fh:
                admission = json.load(fh)
            with Path(args.control_selection_file).open("r", encoding="utf-8") as fh:
                controls = json.load(fh)
            with Path(args.us_measurement_file).open("r", encoding="utf-8") as fh:
                us_measurement = json.load(fh)
            prior_measurement = None
            if args.prior_control_measurement_file:
                with Path(args.prior_control_measurement_file).open("r", encoding="utf-8") as fh:
                    prior_measurement = json.load(fh)
            next_measurement = None
            if args.next_control_measurement_file:
                with Path(args.next_control_measurement_file).open("r", encoding="utf-8") as fh:
                    next_measurement = json.load(fh)
            if args.command == "gate-hk-outcome":
                result = gate_hk_outcome_read(
                    admission,
                    controls,
                    us_measurement,
                    prior_control_measurement=prior_measurement,
                    next_control_measurement=next_measurement,
                )
            else:
                result = score_hsi_outcome(
                    admission,
                    controls,
                    us_measurement,
                    prior_control_measurement=prior_measurement,
                    next_control_measurement=next_measurement,
                )
        else:
            with Path(args.admission_file).open("r", encoding="utf-8") as fh:
                admission = json.load(fh)
            result = measure_us_response(admission)
    except (CaptureContractError, study.StudyContractError, replay.ReplayContractError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
