"""Source-aware Pressure Watch dates; no I/O, scheduling, or ledger mutation.

Massive stock-day files are normally ready about 11:00 ET the following day.
Source: https://massive.com/docs/flat-files/stocks/day-aggregates (2026-09-16).
An observed newer source date wins over this conservative availability estimate.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from collections.abc import Mapping

from lib.nyse_calendar import ET, is_session, last_session_on_or_before, sessions_between


def _date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def expected_source_session(now: datetime | None = None) -> date:
    """Expected stock-day file session, respecting next-day delivery and DST."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(ET)
    lag = 1 if local.time() >= time(11) else 2
    return last_session_on_or_before(local.date() - timedelta(days=lag))


def next_source_due(evaluated: date) -> str:
    """Browser expiry scalar; reuse the exchange calendar, never duplicate it in JS."""
    following = sessions_between(evaluated + timedelta(days=1), evaluated + timedelta(days=14))
    due_day = following[0] + timedelta(days=1)
    return datetime.combine(due_day, time(11), tzinfo=ET).astimezone(timezone.utc).isoformat()


def assess(payload: Mapping, *, source_asof: str | None = None,
           expected_asof: str | None = None, board_asof: str | None = None) -> dict:
    """Keep event identity, completed evaluation, source availability and clock separate."""
    event = _date(payload.get("asof"))
    evaluated = _date(payload.get("evaluated_through") if "evaluated_through" in payload else payload.get("asof"))
    expected = _date(expected_asof or board_asof) or evaluated
    source = _date(source_asof)
    market = _date(board_asof)
    result = {"status": "unknown", "stale": True,
              "evaluated_through": evaluated.isoformat() if evaluated else None,
              "event_asof": event.isoformat() if event else None,
              "source_asof": source.isoformat() if source else None,
              "expected_asof": expected.isoformat() if expected else None,
              "expires_utc": None}
    # Validate each supplied reference before normalizing calendar dates.
    # Missing optional values are distinct from explicitly malformed values.
    if not evaluated or not expected:
        return result
    if any(raw is not None and parsed is None for raw, parsed in (
            (source_asof, source), (expected_asof, _date(expected_asof)),
            (board_asof, market), (payload.get("asof"), event))):
        return result
    try:
        if any(d is not None and not is_session(d) for d in (evaluated, event, source)):
            return result
        if expected_asof is not None and not is_session(expected):
            return result
        expected = last_session_on_or_before(expected)
        market = last_session_on_or_before(market) if market else None
    except (OverflowError, ValueError):
        return result
    if ((event and evaluated < event)
            or (market and any(d and d > market for d in (evaluated, source, expected)))):
        return result
    result["expected_asof"] = expected.isoformat()
    # Invalid/future input must be rejected before any deadline arithmetic.
    try:
        result["expires_utc"] = next_source_due(evaluated)
    except (OverflowError, ValueError, IndexError):
        return result
    required = max(expected, source) if source else expected
    if evaluated < required:
        status = "source_delayed" if source and evaluated >= source and source < expected else "processing_delayed"
    elif expected_asof is not None and market and evaluated < market:
        status = "awaiting_source"
    else:
        status = "current"
    result.update(status=status, stale=status in {"processing_delayed", "source_delayed"})
    return result
