"""S2 clock law: first session s(c) (IL §1) and session-part classification.

s(c) is the first session on clock c whose REGULAR OPEN is strictly after
t_avail:
- a pre-open release maps to that same day;
- a release during the session, during the HK midday break or after the close
  maps to the next session (the HK afternoon re-open is not a session open);
- a DISCLOSURE_DATE anchor maps to the first session strictly after the date
  (qledger's +1 business-day embargo read as a calendar rule).
Every event gets an s on BOTH clocks whether or not it is graded on both.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from engine.qledger import (  # noqa: F401  (re-exported for one-clock callers)
    CLOCK_CALENDARS,
    MARKET_HK,
    MARKET_US,
    next_session_strictly_after,
)

_TZ_LOCAL = {
    MARKET_US: ZoneInfo("America/New_York"),
    MARKET_HK: ZoneInfo("Asia/Hong_Kong"),
}
_REGULAR_OPEN_LOCAL = {
    MARKET_US: time(9, 30),
    MARKET_HK: time(9, 30),
}
_MIDDAY_BREAK = {  # (start, end) local wall clock; HK only
    MARKET_HK: (time(12, 0), time(13, 0)),
}
_SESSION_END_LOCAL = {
    MARKET_US: time(16, 0),
    MARKET_HK: time(16, 0),
}

UTC = timezone.utc


class ClockLawFailure(RuntimeError):
    """The calendar could not place a session (fail closed)."""


def to_utc(naive: datetime, from_tz: str) -> datetime:
    """Attach a wall-clock zone to a naive publisher-stamped time, then UTC."""
    return naive.replace(tzinfo=ZoneInfo(from_tz)).astimezone(UTC)


def session_part(t_avail_utc: datetime, market: str) -> str:
    """pre_open | in_session | midday_break | after_close (metadata only)."""
    local = t_avail_utc.astimezone(_TZ_LOCAL[market])
    t = local.time()
    if t < _REGULAR_OPEN_LOCAL[market]:
        return "pre_open"
    brk = _MIDDAY_BREAK.get(market)
    if brk and brk[0] <= t < brk[1]:
        return "midday_break"
    if t < _SESSION_END_LOCAL[market]:
        return "in_session"
    return "after_close"


def first_session_after(t_avail_utc: datetime, market: str) -> date:
    """s(c): first session whose regular open is STRICTLY after t_avail."""
    local = t_avail_utc.astimezone(_TZ_LOCAL[market])
    d = local.date()
    cal = CLOCK_CALENDARS[market]
    if cal.is_session(d) and local.time() < _REGULAR_OPEN_LOCAL[market]:
        return d
    nxt = next_session_strictly_after(d, market)
    if nxt is None:
        raise ClockLawFailure(
            f"no session found after {d} on {market} (fail closed)")
    return nxt


def first_session_after_disclosure_date(d: date, market: str) -> date:
    """DISCLOSURE_DATE anchor: first session STRICTLY after the date, on both
    clocks (equal to qledger's +1 business-day embargo, read as calendar law)."""
    nxt = next_session_strictly_after(d, market)
    if nxt is None:
        raise ClockLawFailure(
            f"no session found strictly after {d} on {market} (fail closed)")
    return nxt


SESSION_SPAN_START = date(2019, 1, 1)
SESSION_SPAN_END = date(2027, 12, 31)


def session_dates(cal) -> list[str]:
    """Every modelled session in the span, ISO strings ascending (calendar
    arithmetic only — this is the absorption ruler of IL §3 step 4)."""
    out = []
    d = SESSION_SPAN_START
    one_day = timedelta(days=1)
    while d <= SESSION_SPAN_END:
        if cal.is_session(d):
            out.append(d.isoformat())
        d += one_day
    return out
