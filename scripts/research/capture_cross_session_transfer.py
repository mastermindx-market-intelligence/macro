"""Prospective cross-session transfer capture harness.

Research-only and production-inert. This module enforces the source-first
prospective protocol without creating a new event, ledger, or data plane.

Stage 1: admit_source_event freezes first-disclosure source facts and protocol
eligibility only. Optional source resolution: amend_source_state can attach a
later corroboration/confirmation receipt to that same event, but may not move
the first-disclosure clock, change cohort eligibility, or mint a second event.
Stage 2: measure_us_response reads the incumbent U.S. minute transport only and
computes the already-frozen +5 to +35 minute constructions.

No capture step reads Hong Kong outcomes, picks controls from outcomes, persists
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
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from research import event_microstructure_study as study  # noqa: E402
from scripts.research import replay_event_microstructure as replay  # noqa: E402

SCHEMA_ADMISSION = "research.cross_session_transfer_admission.v1"
SCHEMA_SOURCE_AMENDMENT = "research.cross_session_transfer_source_amendment.v1"
SCHEMA_US = "research.cross_session_transfer_us_measurement.v1"

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
    get = transport or replay.default_transport()

    fetched = {
        symbol: replay.fetch_session(symbol, session, transport=get)
        for symbol in US_SYMBOLS
    }
    returns = {
        symbol: _window_return(receipt["points"], anchor=available)
        for symbol, receipt in fetched.items()
    }

    primary = None
    if returns["SMH"] is not None and returns["QQQ"] is not None:
        primary = round(returns["SMH"] - returns["QQQ"], 6)

    challenger = None
    if admission.get("challenger_v1_1_eligible") is True:
        if returns["QQQ"] is not None and returns["SPY"] is not None:
            challenger = round(returns["QQQ"] - returns["SPY"], 6)

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

    measure = sub.add_parser("measure-us", help="measure fixed U.S. geometry only")
    measure.add_argument("--admission-file", required=True)
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
