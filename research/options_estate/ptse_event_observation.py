"""Pure PTSE adapter for incumbent US forward event-calendar context.

This module performs no I/O, schedule construction, source fetch, historical
backfill, scoring, gating, forecast, lifecycle, publication, or trade effect.

It consumes an already-issued event_calendar.json artifact from the existing
engine.event_calendar / scripts.build_feeds owner plus explicit out-of-band
availability/provenance binding supplied by that owner.

Only the next prospective CPI, NFP and FOMC event after the PTSE decision clock
are adapted. An absent row is UNAVAILABLE; it is never interpreted as "no event"
or as a negative feature. Current forward-schedule context does not establish
historical revision/known-negative coverage for C1 or any PIT replay.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from typing import Any, Final

from research.options_estate.ptse_contract import (
    EvidenceGrade,
    EvidenceRef,
    GRADES,
    OwnerFact,
    _time,
)

EVENT_TYPES: Final = ("CPI", "NFP", "FOMC")
_ET: Final = ZoneInfo("America/New_York")


class PTSEEventAdapterError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEEventAdapterError(code)


@dataclass(frozen=True)
class EventCalendarBinding:
    owner_ref: str
    artifact_ref: EvidenceRef
    known_at_earliest: str
    known_at_latest: str
    known_at_precision: str
    known_at_evidence_ref: EvidenceRef
    valid_until: str
    evidence_grade: EvidenceGrade
    population_ref: EvidenceRef
    instrument_id: str
    session_scope: str
    calculation_version: str
    limitations: tuple[str, ...]


def _ref(ref: Mapping[str, Any]) -> dict[str, str]:
    if (
        not isinstance(ref, Mapping)
        or set(ref) != {"owner_ref", "artifact_id", "sha256"}
        or not all(isinstance(ref.get(k), str) and ref.get(k) for k in ref)
    ):
        _fail("EVIDENCE_REF_INVALID")
    digest = ref.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        _fail("EVIDENCE_REF_INVALID")
    return dict(ref)


def _binding(binding: EventCalendarBinding, *, decision_at: str) -> bool:
    artifact_ref = _ref(binding.artifact_ref)
    _ref(binding.known_at_evidence_ref)
    _ref(binding.population_ref)
    if (
        not isinstance(binding.owner_ref, str)
        or not binding.owner_ref
        or artifact_ref["owner_ref"] != binding.owner_ref
    ):
        _fail("OWNER_BINDING_INVALID")
    if binding.known_at_precision not in {"EXACT", "INTERVAL", "DATE_ONLY"}:
        _fail("KNOWN_AT_PRECISION_INVALID")
    if binding.session_scope not in {"REGULAR", "EXTENDED", "ALL", "OWNER_DEFINED"}:
        _fail("SESSION_SCOPE_INVALID")
    if binding.evidence_grade not in GRADES:
        _fail("EVIDENCE_GRADE_INVALID")
    if (
        not isinstance(binding.instrument_id, str)
        or not binding.instrument_id
        or not isinstance(binding.calculation_version, str)
        or not binding.calculation_version
    ):
        _fail("IDENTITY_INVALID")
    if not binding.limitations or any(
        not isinstance(item, str) or not item for item in binding.limitations
    ):
        _fail("LIMITATIONS_REQUIRED")

    earliest = _time(binding.known_at_earliest, "event.known_at_earliest")
    latest = _time(binding.known_at_latest, "event.known_at_latest")
    decision = _time(decision_at, "event.decision_at")
    expiry = _time(binding.valid_until, "event.valid_until")
    if earliest > latest:
        _fail("KNOWN_AT_ORDER_INVALID")
    if binding.known_at_precision == "EXACT" and earliest != latest:
        _fail("KNOWN_AT_PRECISION_INVALID")
    if binding.known_at_precision == "DATE_ONLY" and earliest == latest:
        _fail("KNOWN_AT_PRECISION_INVALID")
    if latest > decision:
        _fail("NOT_KNOWN_AT_DECISION")
    return expiry <= decision


def _date(value: Any) -> date:
    if not isinstance(value, str):
        _fail("EVENT_DATE_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail("EVENT_DATE_INVALID")
    if parsed.isoformat() != value:
        _fail("EVENT_DATE_INVALID")
    return parsed


def _event_timestamp(row: Mapping[str, Any]) -> datetime:
    day = _date(row.get("date"))
    raw = row.get("time_et")
    if not isinstance(raw, str) or len(raw) != 5 or raw[2] != ":":
        _fail("EVENT_TIME_UNAVAILABLE")
    try:
        hh, mm = (int(part) for part in raw.split(":"))
        wall = time(hour=hh, minute=mm)
    except (ValueError, TypeError):
        _fail("EVENT_TIME_INVALID")
    return datetime.combine(day, wall, tzinfo=_ET).astimezone(timezone.utc)


def _known_at(binding: EventCalendarBinding) -> dict[str, Any]:
    return {
        "earliest": binding.known_at_earliest,
        "latest": binding.known_at_latest,
        "precision": binding.known_at_precision,
        "evidence_ref": _ref(binding.known_at_evidence_ref),
    }


def _coverage(binding: EventCalendarBinding, *, present: bool) -> dict[str, Any]:
    return {
        "numerator": 1 if present else 0,
        "denominator": 1,
        "missing_count": 0 if present else 1,
        "population_ref": _ref(binding.population_ref),
    }


def _scope(binding: EventCalendarBinding) -> dict[str, Any]:
    return {
        "instrument_id": binding.instrument_id,
        "session_scope": binding.session_scope,
        "population_ref": _ref(binding.population_ref),
        "position_scope": "NOT_APPLICABLE",
        "side_semantics": "NOT_APPLICABLE",
    }


def _iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def _limitations(binding: EventCalendarBinding, source: str | None) -> list[str]:
    out = list(binding.limitations) + [
        "event_calendar is display/context-only; PTSE does not convert impact into a risk score or gate.",
        "Current forward-schedule presence does not establish historical schedule revision or known-negative coverage.",
        "An absent event row is missing optional context and never proves that no event exists.",
    ]
    if source == "static":
        out.append(
            "Static schedule fallback is current forward context, not historical publication-vintage evidence."
        )
    elif source == "fred":
        out.append(
            "Current FRED release-date output is not by itself a historical first-known or revision-lineage receipt."
        )
    elif source is not None:
        out.append(
            "Owner source label is preserved verbatim; PTSE grants it no stronger provenance class."
        )
    return out


def _present_fact(
    *,
    feature_id: str,
    value: str,
    unit: str,
    event_time: datetime,
    method_kind: str,
    source: str,
    binding: EventCalendarBinding,
    stale: bool,
) -> OwnerFact:
    return {
        "feature_id": feature_id,
        "owner_ref": binding.owner_ref,
        "source_artifact_ref": _ref(binding.artifact_ref),
        "economic_time": _iso_z(event_time),
        "economic_time_role": "SCHEDULED_EVENT",
        "known_at": _known_at(binding),
        "valid_until": binding.valid_until,
        "value": value,
        "unit": unit,
        "status": "STALE" if stale else "OBSERVED",
        "method_kind": method_kind,
        "calculation_version": binding.calculation_version,
        "evidence_grade": binding.evidence_grade,
        "coverage": _coverage(binding, present=True),
        "source_scope": _scope(binding),
        "limitations": _limitations(binding, source),
        "null_reason": "SOURCE_EXPIRED_AT_DECISION" if stale else None,
    }


def _missing_fact(
    *,
    feature_id: str,
    unit: str,
    binding: EventCalendarBinding,
) -> OwnerFact:
    return {
        "feature_id": feature_id,
        "owner_ref": binding.owner_ref,
        "source_artifact_ref": _ref(binding.artifact_ref),
        "economic_time": binding.known_at_latest,
        "economic_time_role": "OBSERVATION",
        "known_at": None,
        "valid_until": binding.valid_until,
        "value": None,
        "unit": unit,
        "status": "UNAVAILABLE",
        "method_kind": "OBSERVATION",
        "calculation_version": binding.calculation_version,
        "evidence_grade": binding.evidence_grade,
        "coverage": _coverage(binding, present=False),
        "source_scope": _scope(binding),
        "limitations": _limitations(binding, None),
        "null_reason": "EVENT_NOT_PRESENT_IN_OWNER_WINDOW_NO_NEGATIVE_INFERENCE",
    }


def adapt_event_calendar(
    payload: Mapping[str, Any],
    binding: EventCalendarBinding,
    *,
    market_session: str,
    decision_at: str,
) -> list[OwnerFact]:
    """Adapt current forward CPI/NFP/FOMC context without constructing a calendar."""

    stale = _binding(binding, decision_at=decision_at)
    if not isinstance(payload, Mapping):
        _fail("EVENT_CALENDAR_OBJECT_REQUIRED")
    if payload.get("schema_version") != 1 or payload.get("is_context_only") is not True:
        _fail("EVENT_CALENDAR_SCHEMA_INVALID")
    if payload.get("asof") != market_session:
        _fail("EVENT_CALENDAR_SESSION_MISMATCH")

    horizon = payload.get("horizon_days")
    if type(horizon) is not int or horizon <= 0 or horizon > 366:
        _fail("EVENT_CALENDAR_HORIZON_INVALID")
    rows = payload.get("us_macro")
    if not isinstance(rows, list):
        _fail("EVENT_CALENDAR_ROWS_INVALID")

    session_day = _date(market_session)
    decision = _time(decision_at, "event.decision_at")
    by_type: dict[str, list[tuple[datetime, str]]] = {
        kind: [] for kind in EVENT_TYPES
    }

    for row in rows:
        if not isinstance(row, Mapping):
            _fail("EVENT_ROW_INVALID")
        kind = row.get("type")
        if kind not in EVENT_TYPES:
            continue
        if row.get("is_context_only") is not True:
            _fail("EVENT_AUTHORITY_INVALID")
        source = row.get("source")
        if (
            not isinstance(source, str)
            or not source
            or source != source.strip()
            or any(ord(ch) < 32 for ch in source)
        ):
            _fail("EVENT_SOURCE_INVALID")
        stamp = _event_timestamp(row)
        day = stamp.astimezone(_ET).date()
        if day < session_day or (day - session_day).days > horizon:
            _fail("EVENT_OUTSIDE_OWNER_WINDOW")
        if stamp > decision:
            by_type[kind].append((stamp, source))

    facts: list[OwnerFact] = []
    for kind in EVENT_TYPES:
        candidates = sorted(set(by_type[kind]), key=lambda item: (item[0], item[1]))
        if candidates:
            event_time = candidates[0][0]
            same_time = {source for stamp, source in candidates if stamp == event_time}
            if len(same_time) != 1:
                _fail("EVENT_SOURCE_CONFLICT")
            source = next(iter(same_time))
            facts.append(
                _present_fact(
                    feature_id=f"event_calendar.next_{kind.lower()}_at",
                    value=_iso_z(event_time),
                    unit="TIMESTAMP",
                    event_time=event_time,
                    method_kind="DETERMINISTIC_COMPUTATION",
                    source=source,
                    binding=binding,
                    stale=stale,
                )
            )
            facts.append(
                _present_fact(
                    feature_id=f"event_calendar.next_{kind.lower()}_source",
                    value=source,
                    unit="STATE",
                    event_time=event_time,
                    method_kind="OBSERVATION",
                    source=source,
                    binding=binding,
                    stale=stale,
                )
            )
        else:
            facts.append(
                _missing_fact(
                    feature_id=f"event_calendar.next_{kind.lower()}_at",
                    unit="TIMESTAMP",
                    binding=binding,
                )
            )
            facts.append(
                _missing_fact(
                    feature_id=f"event_calendar.next_{kind.lower()}_source",
                    unit="STATE",
                    binding=binding,
                )
            )

    facts.sort(key=lambda fact: fact["feature_id"])
    return facts


__all__ = [
    "EVENT_TYPES",
    "PTSEEventAdapterError",
    "EventCalendarBinding",
    "adapt_event_calendar",
]