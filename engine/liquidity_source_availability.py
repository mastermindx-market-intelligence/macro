"""Massive daily-file availability contract, separate from market recency.

The approximate next-calendar-day 11:00 ET schedule is a coverage floor, never
an observed publication/ingestion/known_at timestamp. An actually observed newer
completed-session file may be used before that floor advances.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from lib.nyse_calendar import expected_last_session, is_session

SCHEDULE_SOURCE = 'https://massive.com/docs/flat-files/stocks/day-aggregates'


def source_expected_session(recorded_at: datetime):
    if not isinstance(recorded_at, datetime) or recorded_at.utcoffset() is None:
        raise ValueError('aware recorded_at required')
    local = recorded_at.astimezone(ZoneInfo('America/New_York'))
    day = local.date() - timedelta(days=1 if local.time() >= time(11) else 2)
    for _ in range(20):
        if is_session(day):
            return day
        day -= timedelta(days=1)
    raise ValueError('source calendar unavailable')


def coverage_clock(recorded_at: datetime) -> dict:
    return {
        'market_completed_session': expected_last_session(recorded_at).isoformat(),
        'source_expected_session': source_expected_session(recorded_at).isoformat(),
        'schedule': 'approximately_11_ET_next_calendar_day',
        'schedule_source': SCHEDULE_SOURCE,
        'schedule_is_publication_evidence': False,
    }
