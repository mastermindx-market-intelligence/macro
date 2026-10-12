"""Published US cash-equity sessions for current collection and live status.

The registered ``lib.nyse_calendar`` owner keeps its exact historical contract.
This adapter applies complete official notices and published early closes without
changing that module or the existing consumers that depend on its immutable bytes.
Unknown years retain its historical rules; verification remains in market_session.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from lib import nyse_calendar as _legacy
from lib.exchange_holidays import announced_holidays, early_close

ET = _legacy.ET

__all__ = [
    "ET", "holidays", "is_session", "last_session_on_or_before",
    "expected_last_session", "sessions_between",
]


def holidays(year: int) -> frozenset[date]:
    """Official annual closures, with the registered historical-rule fallback."""
    announced = announced_holidays("US", year)
    return frozenset(announced) if announced is not None else _legacy.holidays(year)


def is_session(day: date) -> bool:
    """Full and shortened cash sessions, preserving historical one-off closures."""
    return (day.weekday() < 5
            and day not in holidays(day.year)
            and day not in _legacy.ONE_OFF_CLOSURES)


def last_session_on_or_before(day: date) -> date:
    """Most recent cash session on or before day, using the published slate."""
    for _ in range(30):
        if is_session(day):
            return day
        day -= timedelta(days=1)
    raise ValueError("no US cash session found in the prior 30 days")


def expected_last_session(now: datetime | None = None) -> date:
    """Daily bar due after 14:00 ET on published half days, otherwise 17:00 ET.

    Published US half days close at 13:00 ET; both paths keep a one-hour settle
    buffer. Naive datetimes retain the pipeline's UTC convention.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(ET)
    day = local.date()
    settled = time(14) if early_close("US", day) is not None else time(17)
    if is_session(day) and local.time() >= settled:
        return day
    return last_session_on_or_before(day - timedelta(days=1))


def sessions_between(start: date, end: date) -> list[date]:
    """Inclusive ascending session dates; preserve the NYSE list-returning API."""
    result = []
    day = start
    while day <= end:
        if is_session(day):
            result.append(day)
        day += timedelta(days=1)
    return result
