"""Guards for cross-session source-timing research.

This module owns no exchange calendar, feed, price store, alert, ranking, or trade
authority. It validates caller-supplied source censuses and refuses population
timing inference until enumeration coverage is explicitly complete.

Regional session intervals must come from an admitted external calendar owner.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

CENSUS_SCHEMA = "research.cross_session_source_timing_census_raw.v0"
COMPLETE_COVERAGE = "complete"
INCOMPLETE_COVERAGE = "retrieval_incomplete"

RELIEF_DIRECTIONS = frozenset({"relief", "implementation_relief"})
CONTROL_DIRECTIONS = frozenset(
    {
        "escalation",
        "implementation_escalation",
        "denial_or_breakdown",
        "mixed_conflict",
        "neutral_process",
    }
)
KNOWN_DIRECTIONS = RELIEF_DIRECTIONS | CONTROL_DIRECTIONS


class CensusContractError(ValueError):
    """Raised when a source census cannot support the requested inference."""


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise CensusContractError(f"{field} must be a non-empty ISO-8601 string")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise CensusContractError(f"{field} is not valid ISO-8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise CensusContractError(f"{field} must be timezone-aware")
    return dt.astimezone(timezone.utc)


def validate_census(census: Mapping[str, Any]) -> dict[str, Any]:
    """Validate corpus identity, clocks, uniqueness, and inference firewall."""
    if census.get("schema") != CENSUS_SCHEMA:
        raise CensusContractError("unsupported census schema")

    window = census.get("census_window")
    if not isinstance(window, Mapping):
        raise CensusContractError("census_window is required")
    start = _utc(window.get("start"), "census_window.start")
    end = _utc(window.get("end"), "census_window.end")
    if start > end:
        raise CensusContractError("census window start cannot exceed end")

    coverage = census.get("coverage")
    if not isinstance(coverage, Mapping):
        raise CensusContractError("coverage is required")
    coverage_status = str(coverage.get("status") or "").strip()
    frequency_allowed = coverage.get("primary_timing_frequency_test_allowed")
    if not isinstance(frequency_allowed, bool):
        raise CensusContractError(
            "coverage.primary_timing_frequency_test_allowed must be boolean"
        )
    if coverage_status != COMPLETE_COVERAGE and frequency_allowed:
        raise CensusContractError(
            "incomplete coverage cannot allow a primary timing-frequency test"
        )
    if coverage_status == COMPLETE_COVERAGE and not frequency_allowed:
        raise CensusContractError(
            "complete coverage must explicitly allow the primary timing-frequency test"
        )

    rows = census.get("rows")
    if not isinstance(rows, list):
        raise CensusContractError("rows must be a list")

    seen: set[str] = set()
    eligible = 0
    outcome_context = 0
    directions: dict[str, int] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CensusContractError(f"rows[{idx}] must be an object")
        event_id = str(row.get("event_id") or "").strip()
        if not event_id:
            raise CensusContractError(f"rows[{idx}].event_id is required")
        if event_id in seen:
            raise CensusContractError(f"duplicate event_id: {event_id}")
        seen.add(event_id)

        available_at = _utc(row.get("available_at"), f"rows[{idx}].available_at")
        if not start <= available_at <= end:
            raise CensusContractError(
                f"{event_id} is outside the frozen census window"
            )

        direction = str(row.get("direction") or "").strip()
        if direction not in KNOWN_DIRECTIONS:
            raise CensusContractError(
                f"{event_id} has unsupported direction: {direction}"
            )
        directions[direction] = directions.get(direction, 0) + 1

        if row.get("timing_primary_eligible") is True:
            eligible += 1
        elif row.get("timing_primary_eligible") not in (False, None):
            raise CensusContractError(
                f"{event_id}.timing_primary_eligible must be boolean or null"
            )

        if row.get("outcome_context_exposed") is True:
            outcome_context += 1
        elif row.get("outcome_context_exposed") not in (False, None):
            raise CensusContractError(
                f"{event_id}.outcome_context_exposed must be boolean or null"
            )

    declared_count = (census.get("counts") or {}).get("recovered_unique_clusters")
    if declared_count is not None and declared_count != len(rows):
        raise CensusContractError(
            "counts.recovered_unique_clusters does not equal len(rows)"
        )

    firewall = census.get("outcome_firewall")
    if not isinstance(firewall, Mapping):
        raise CensusContractError("outcome_firewall is required")
    if firewall.get("prospective_holdout_not_opened") is not True:
        raise CensusContractError(
            "prospective_holdout_not_opened must remain true in the raw census"
        )
    if coverage_status != COMPLETE_COVERAGE and (
        firewall.get("timing_frequency_not_computed") is not True
    ):
        raise CensusContractError(
            "incomplete census must record timing_frequency_not_computed=true"
        )

    return {
        "schema": CENSUS_SCHEMA,
        "rows": len(rows),
        "unique_event_ids": len(seen),
        "timing_primary_eligible": eligible,
        "outcome_context_exposed": outcome_context,
        "coverage_status": coverage_status,
        "primary_timing_frequency_test_allowed": frequency_allowed,
        "directions": dict(sorted(directions.items())),
    }


def classify_from_authoritative_intervals(
    available_at: str,
    *,
    cash_sessions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify one event from caller-supplied authoritative cash sessions.

    Each session must contain timezone-aware open_at and close_at clocks. The
    function does not know weekends, holidays, half-days, lunch breaks, or
    exchange rules. Those remain the supplying calendar owner's responsibility.
    """
    event = _utc(available_at, "available_at")
    sessions: list[tuple[datetime, datetime]] = []
    for idx, raw in enumerate(cash_sessions):
        if not isinstance(raw, Mapping):
            raise CensusContractError(f"cash_sessions[{idx}] must be an object")
        opened = _utc(raw.get("open_at"), f"cash_sessions[{idx}].open_at")
        closed = _utc(raw.get("close_at"), f"cash_sessions[{idx}].close_at")
        if opened >= closed:
            raise CensusContractError(
                f"cash_sessions[{idx}] open_at must precede close_at"
            )
        sessions.append((opened, closed))

    sessions.sort()
    for prior, current in zip(sessions, sessions[1:]):
        if prior[1] > current[0]:
            raise CensusContractError("cash sessions cannot overlap")

    active = next(
        ((opened, closed) for opened, closed in sessions if opened <= event < closed),
        None,
    )
    if active is not None:
        return {
            "available_at": event.isoformat().replace("+00:00", "Z"),
            "cash_open": True,
            "previous_close_at": None,
            "next_open_at": None,
            "minutes_since_previous_close": None,
            "minutes_until_next_open": None,
            "calendar_source": "caller_supplied_authoritative_intervals",
        }

    previous_close = max(
        (closed for _, closed in sessions if closed <= event),
        default=None,
    )
    next_open = min(
        (opened for opened, _ in sessions if opened > event),
        default=None,
    )
    return {
        "available_at": event.isoformat().replace("+00:00", "Z"),
        "cash_open": False,
        "previous_close_at": (
            None
            if previous_close is None
            else previous_close.isoformat().replace("+00:00", "Z")
        ),
        "next_open_at": (
            None
            if next_open is None
            else next_open.isoformat().replace("+00:00", "Z")
        ),
        "minutes_since_previous_close": (
            None
            if previous_close is None
            else round((event - previous_close).total_seconds() / 60.0, 6)
        ),
        "minutes_until_next_open": (
            None
            if next_open is None
            else round((next_open - event).total_seconds() / 60.0, 6)
        ),
        "calendar_source": "caller_supplied_authoritative_intervals",
    }


def timing_frequency_summary(
    census: Mapping[str, Any],
    *,
    after_asia_close: Mapping[str, bool | None],
) -> dict[str, Any]:
    """Return the preregistered relief-vs-control timing table.

    Refuses to run unless coverage is explicitly complete. Session labels are
    caller-supplied outputs from authoritative calendar owners; missing labels
    remain missing rather than being inferred from UTC hour.
    """
    validation = validate_census(census)
    if validation["coverage_status"] != COMPLETE_COVERAGE:
        raise CensusContractError(
            "primary timing-frequency inference refused: census coverage is not complete"
        )
    if validation["primary_timing_frequency_test_allowed"] is not True:
        raise CensusContractError(
            "primary timing-frequency inference is not admitted by the census"
        )

    counts = {
        "relief": {"after_asia_close": 0, "other": 0, "missing": 0},
        "control": {"after_asia_close": 0, "other": 0, "missing": 0},
    }
    for row in census["rows"]:
        if row.get("timing_primary_eligible") is not True:
            continue
        event_id = str(row["event_id"])
        direction = str(row["direction"])
        cohort = "relief" if direction in RELIEF_DIRECTIONS else "control"
        label = after_asia_close.get(event_id)
        if label is None:
            counts[cohort]["missing"] += 1
        elif label:
            counts[cohort]["after_asia_close"] += 1
        else:
            counts[cohort]["other"] += 1

    def rate(group: Mapping[str, int]) -> float | None:
        denom = group["after_asia_close"] + group["other"]
        return None if denom == 0 else group["after_asia_close"] / denom

    relief_rate = rate(counts["relief"])
    control_rate = rate(counts["control"])
    return {
        "schema": "research.cross_session_timing_frequency_summary.v1",
        "coverage_status": COMPLETE_COVERAGE,
        "counts": counts,
        "relief_after_asia_close_rate": relief_rate,
        "control_after_asia_close_rate": control_rate,
        "difference_in_rates": (
            None
            if relief_rate is None or control_rate is None
            else relief_rate - control_rate
        ),
        "interpretation": (
            "descriptive timing distribution only; any asymmetry does not establish "
            "intent, manipulation, or investor targeting"
        ),
    }
