"""Deterministic BioCatalyst Research Priority V1.

This is a research-triage policy, not a return/availability/position-sizing
model.  It consumes only the frozen time/evidence/missingness inputs selected by
R1B and deliberately ignores probability, materiality, sentiment and price.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Sequence


METHOD_ID = "biocatalyst.research_triage.v1"
_OCCURRENCES = {"uncorroborated", "corroborated", "cancelled", "withdrawn"}
_SOURCE_HEALTH = {"current", "stale", "partial", "unavailable"}
_IDENTITY_STATES = {"resolved", "unresolved"}
_TIMING_STATES = {"consistent", "conflicted"}
_LANE_ORDER = {"ACT_NOW": 0, "RECONCILE": 1, "RESEARCH_NEXT": 2, "MONITOR": 3}
_GAP_ORDER = (
    "SOURCE_NOT_CURRENT",
    "IDENTITY_UNRESOLVED",
    "TIMING_CONFLICT",
    "TIMING_INCOMPLETE",
    "PAST_UNCORROBORATED",
)
_AUTHORITY = {
    "classification": "research_priority_only",
    "trade_origination": False,
    "changes_availability": False,
    "position_sizing": False,
    "prophet_admission": False,
}
_REQUIRED = {
    "event_fact_ref",
    "exposure_ref",
    "revision_is_current",
    "occurrence",
    "source_health",
    "identity_state",
    "timing_state",
    "lower_date",
    "upper_date",
    "last_material_revision_known_at",
}
_ALLOWED = _REQUIRED | {"auxiliary_metadata", "id", "research_priority"}


class ResearchPriorityError(ValueError):
    """The owner-composed RP input is malformed or outruns its cutoff."""


def _civil(value: object, *, field: str, allow_null: bool = True) -> date | None:
    if value is None and allow_null:
        return None
    if not isinstance(value, str) or len(value) != 10:
        raise ResearchPriorityError(f"{field} must be YYYY-MM-DD or null")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ResearchPriorityError(f"{field} is not a valid calendar date") from exc
    if value != parsed.isoformat():
        raise ResearchPriorityError(f"{field} is not canonical YYYY-MM-DD")
    return parsed


def _utc_z(value: object, *, field: str, allow_null: bool = True) -> datetime | None:
    if value is None and allow_null:
        return None
    if not isinstance(value, str) or not value.endswith("Z") or "T" not in value:
        raise ResearchPriorityError(f"{field} must be a normalized UTC Z timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ResearchPriorityError(f"{field} must be a normalized UTC Z timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ResearchPriorityError(f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _validate_context(*, evaluation_cutoff: object, anchor_date: object) -> tuple[datetime, date]:
    cutoff = _utc_z(evaluation_cutoff, field="evaluation_cutoff", allow_null=False)
    anchor = _civil(anchor_date, field="anchor_date", allow_null=False)
    assert cutoff is not None and anchor is not None
    if cutoff.date() != anchor:
        raise ResearchPriorityError("anchor_date must be the evaluation cutoff UTC date")
    return cutoff, anchor


def interval_overlaps_horizon(
    lower: object,
    upper: object,
    *,
    anchor_date: object,
    days: int,
) -> bool:
    if days not in {7, 30, 90, 180, 365}:
        raise ResearchPriorityError("unsupported horizon")
    anchor = _civil(anchor_date, field="anchor_date", allow_null=False)
    lo = _civil(lower, field="lower_date")
    hi = _civil(upper, field="upper_date")
    assert anchor is not None
    if lo is None or hi is None:
        return False
    if lo > hi:
        raise ResearchPriorityError("lower_date exceeds upper_date")
    horizon_end = anchor + timedelta(days=days - 1)
    return hi >= anchor and lo <= horizon_end


def _validated_row(row: Mapping[str, Any], *, evaluation_cutoff: object, anchor_date: object) -> tuple[dict[str, Any], datetime, date, date | None, date | None, datetime | None]:
    if not isinstance(row, Mapping):
        raise ResearchPriorityError("research-priority input must be an object")
    missing = _REQUIRED - set(row)
    unknown = set(row) - _ALLOWED
    if missing or unknown:
        raise ResearchPriorityError(f"research-priority fields mismatch missing={sorted(missing)} unsupported={sorted(unknown)}")
    cutoff, anchor = _validate_context(evaluation_cutoff=evaluation_cutoff, anchor_date=anchor_date)
    event_ref = row.get("event_fact_ref")
    exposure_ref = row.get("exposure_ref")
    if not isinstance(event_ref, str) or not event_ref or len(event_ref) > 512:
        raise ResearchPriorityError("event_fact_ref invalid")
    if exposure_ref is not None and (not isinstance(exposure_ref, str) or not exposure_ref or len(exposure_ref) > 512):
        raise ResearchPriorityError("exposure_ref invalid")
    if not isinstance(row.get("revision_is_current"), bool):
        raise ResearchPriorityError("revision_is_current must be boolean")
    if row.get("occurrence") not in _OCCURRENCES:
        raise ResearchPriorityError("occurrence invalid")
    if row.get("source_health") not in _SOURCE_HEALTH:
        raise ResearchPriorityError("source_health invalid")
    if row.get("identity_state") not in _IDENTITY_STATES:
        raise ResearchPriorityError("identity_state invalid")
    if row.get("timing_state") not in _TIMING_STATES:
        raise ResearchPriorityError("timing_state invalid")
    lower = _civil(row.get("lower_date"), field="lower_date")
    upper = _civil(row.get("upper_date"), field="upper_date")
    if lower is not None and upper is not None and lower > upper:
        raise ResearchPriorityError("lower_date exceeds upper_date")
    revision_at = _utc_z(
        row.get("last_material_revision_known_at"),
        field="last_material_revision_known_at",
    )
    if revision_at is not None and revision_at > cutoff:
        raise ResearchPriorityError("knowledge timestamp exceeds evaluation cutoff")
    return dict(row), cutoff, anchor, lower, upper, revision_at


def classify_research_priority(
    row: Mapping[str, Any],
    *,
    evaluation_cutoff: object,
    anchor_date: object,
) -> dict[str, Any]:
    item, _cutoff, anchor, lower, upper, _revision_at = _validated_row(
        row, evaluation_cutoff=evaluation_cutoff, anchor_date=anchor_date
    )

    gaps: list[str] = []
    if item["source_health"] != "current":
        gaps.append("SOURCE_NOT_CURRENT")
    if item["identity_state"] == "unresolved":
        gaps.append("IDENTITY_UNRESOLVED")
    if item["timing_state"] == "conflicted":
        gaps.append("TIMING_CONFLICT")
    if lower is None or upper is None:
        gaps.append("TIMING_INCOMPLETE")
    if (
        item["occurrence"] == "uncorroborated"
        and upper is not None
        and upper < anchor
    ):
        gaps.append("PAST_UNCORROBORATED")
    gaps = [reason for reason in _GAP_ORDER if reason in gaps]

    if item["revision_is_current"] is False:
        return {
            "disposition": "EXCLUDE_SUPERSEDED",
            "method_id": METHOD_ID,
            "lane": None,
            "primary_reason": "SUPERSEDED_REVISION",
            "gap_reasons": gaps,
            "comparison_date": anchor.isoformat(),
            "authority": dict(_AUTHORITY),
        }

    occurrence = item["occurrence"]
    if occurrence in {"corroborated", "cancelled", "withdrawn"}:
        lane, primary = "MONITOR", "RESOLVED_HISTORY"
    elif item["source_health"] != "current":
        lane, primary = "RECONCILE", "SOURCE_NOT_CURRENT"
    elif item["identity_state"] == "unresolved":
        lane, primary = "RECONCILE", "IDENTITY_UNRESOLVED"
    elif item["timing_state"] == "conflicted":
        lane, primary = "RECONCILE", "TIMING_CONFLICT"
    elif lower is None or upper is None:
        lane, primary = "RECONCILE", "TIMING_INCOMPLETE"
    elif upper < anchor:
        lane, primary = "RECONCILE", "PAST_UNCORROBORATED"
    else:
        seven_end = anchor + timedelta(days=6)
        if lower >= anchor and upper <= seven_end:
            lane, primary = "ACT_NOW", "WINDOW_WITHIN_SEVEN_DAYS"
        elif interval_overlaps_horizon(
            lower.isoformat(), upper.isoformat(), anchor_date=anchor.isoformat(), days=90
        ):
            lane, primary = "RESEARCH_NEXT", "WINDOW_OVERLAPS_NINETY_DAYS"
        else:
            lane, primary = "MONITOR", "LATER_WINDOW"

    return {
        "disposition": "SELECTED",
        "method_id": METHOD_ID,
        "lane": lane,
        "primary_reason": primary,
        "gap_reasons": gaps,
        "comparison_date": anchor.isoformat(),
        "authority": dict(_AUTHORITY),
    }


def _date_sort(value: object) -> tuple[int, int]:
    parsed = _civil(value, field="sort_date")
    return (1, 0) if parsed is None else (0, parsed.toordinal())


def _revision_sort(value: object) -> tuple[int, float]:
    parsed = _utc_z(value, field="last_material_revision_known_at")
    return (1, 0.0) if parsed is None else (0, -parsed.timestamp())


def _exposure_sort(value: object) -> tuple[int, str]:
    return (1, "") if value is None else (0, str(value))


def sort_research_priority_rows(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Sort already-classified rows using the frozen lane/date/revision/ref order."""
    def key(row: Mapping[str, Any]):
        priority = row.get("research_priority")
        if not isinstance(priority, Mapping) or priority.get("lane") not in _LANE_ORDER:
            raise ResearchPriorityError("row lacks a selected research_priority lane")
        return (
            _LANE_ORDER[str(priority["lane"])],
            _date_sort(row.get("upper_date")),
            _date_sort(row.get("lower_date")),
            _revision_sort(row.get("last_material_revision_known_at")),
            str(row.get("event_fact_ref") or ""),
            _exposure_sort(row.get("exposure_ref")),
        )

    return sorted(rows, key=key)
