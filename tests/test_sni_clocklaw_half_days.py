"""SNI-local A12 half-day session_part pin (commission 8659, CLKHD).

This file consumes owner-supplied published half-day closes through
lib.exchange_holidays.early_close. It does not mint issuer or security
identifiers, does not implement a calendar, and does not feed a ranker,
gate, sizer, signal, escalation, or trade path. Half-day dates and times
are never hard-coded; they are enumerated from the owner.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from s2_clocklaw import (  # noqa: E402
    CLOCK_CALENDARS,
    MARKET_HK,
    MARKET_US,
    SESSION_SPAN_END,
    SESSION_SPAN_START,
    ClockLawFailure,
    first_session_after,
    next_session_strictly_after,
    session_part,
    to_utc,
)
from lib.exchange_holidays import calendar_coverage, early_close  # noqa: E402

HK_TZ = "Asia/Hong_Kong"
US_TZ = "America/New_York"
_TZ = {MARKET_HK: HK_TZ, MARKET_US: US_TZ}
_ZONE = {MARKET_HK: ZoneInfo(HK_TZ), MARKET_US: ZoneInfo(US_TZ)}

_BASE_OPEN = dt.time(9, 30)
_BASE_END = dt.time(16, 0)
_BASE_MIDDAY = {MARKET_HK: (dt.time(12, 0), dt.time(13, 0))}

# Regular-session wall-clock edges from BASE session_part (not half-day times).
_FULL_DAY_EDGES = (
    dt.time(9, 0),
    dt.time(9, 29, 59),
    dt.time(9, 30),
    dt.time(11, 59, 59),
    dt.time(12, 0),
    dt.time(12, 59, 59),
    dt.time(13, 0),
    dt.time(15, 59, 59),
    dt.time(16, 0),
    dt.time(16, 1),
)


def _span_from_owner(market: str) -> tuple[dt.date, dt.date]:
    """Covered year span from calendar_coverage, unioned with the clock-law span."""
    cov = calendar_coverage(market)
    years = set(cov["verified_years"]) | set(cov.get("partial_years") or ())
    if years:
        owner_start = dt.date(min(years), 1, 1)
        owner_end = dt.date(max(years), 12, 31)
        return min(owner_start, SESSION_SPAN_START), max(owner_end, SESSION_SPAN_END)
    return SESSION_SPAN_START, SESSION_SPAN_END


def _enumerate_published_half_days(market: str) -> tuple[tuple[dt.date, dt.time], ...]:
    start, end = _span_from_owner(market)
    out: list[tuple[dt.date, dt.time]] = []
    d = start
    one = dt.timedelta(days=1)
    while d <= end:
        ec = early_close(market, d)
        if ec is not None:
            out.append((d, ec))
        d += one
    return tuple(out)


def _half_id(market: str, day: dt.date, ec: dt.time) -> str:
    return f"{market}-{day.isoformat()}-{ec.strftime('%H:%M')}"


HK_HALF_DAYS = _enumerate_published_half_days(MARKET_HK)
US_HALF_DAYS = _enumerate_published_half_days(MARKET_US)
ALL_HALF_DAYS = tuple(
    (MARKET_HK, day, ec) for day, ec in HK_HALF_DAYS
) + tuple(
    (MARKET_US, day, ec) for day, ec in US_HALF_DAYS
)


def _at_local(day: dt.date, clock: dt.time, tz: str) -> dt.datetime:
    naive = dt.datetime(
        day.year, day.month, day.day,
        clock.hour, clock.minute, clock.second, clock.microsecond,
    )
    return to_utc(naive, tz)


def _shift_clock(clock: dt.time, *, minutes: int) -> dt.time:
    base = dt.datetime(2000, 1, 1, clock.hour, clock.minute, clock.second)
    return (base + dt.timedelta(minutes=minutes)).time()


def _base_session_part(t_avail_utc: dt.datetime, market: str) -> str:
    """BASE wall-clock session_part (open 09:30, HK midday 12:00–13:00, end 16:00)."""
    t = t_avail_utc.astimezone(_ZONE[market]).time()
    if t < _BASE_OPEN:
        return "pre_open"
    brk = _BASE_MIDDAY.get(market)
    if brk and brk[0] <= t < brk[1]:
        return "midday_break"
    if t < _BASE_END:
        return "in_session"
    return "after_close"


def _base_first_session_after(t_avail_utc: dt.datetime, market: str) -> dt.date:
    """BASE first_session_after: regular open only; half-day close is unused."""
    local = t_avail_utc.astimezone(_ZONE[market])
    d = local.date()
    cal = CLOCK_CALENDARS[market]
    if cal.is_session(d) and local.time() < _BASE_OPEN:
        return d
    nxt = next_session_strictly_after(d, market)
    if nxt is None:
        raise ClockLawFailure(
            f"no session found after {d} on {market} (fail closed)")
    return nxt


def _label_before_ec(market: str, ec: dt.time) -> str:
    """One minute before a published early close is still in session.

    A half day has no midday break: HK's 12:10 early close is the end of the
    closing auction that follows the 12:00 continuous-session end, so 12:09
    is in_session, not midday_break.
    """
    del market, ec
    return "in_session"


def _half_day_probes(
    market: str, day: dt.date, ec: dt.time,
) -> list[tuple[dt.datetime, str]]:
    tz = _TZ[market]
    before = _shift_clock(ec, minutes=-1)
    return [
        (_at_local(day, dt.time(9, 0), tz), "pre_open"),
        (_at_local(day, before, tz), _label_before_ec(market, ec)),
        (_at_local(day, ec, tz), "after_close"),
        (_at_local(day, _shift_clock(ec, minutes=120), tz), "after_close"),
    ]


def check_half_day_labels(market: str, day: dt.date, ec: dt.time) -> None:
    """Assert session_part labels on one owner-published half day (clkhd_01/02)."""
    for t, expected in _half_day_probes(market, day, ec):
        got = session_part(t, market)
        local_t = t.astimezone(_ZONE[market]).time()
        assert got == expected, (
            f"{market} {day.isoformat()} local={local_t} ec={ec} "
            f"-> {got!r} expected {expected!r}"
        )


def _adjacent_full_days(market: str, day: dt.date) -> list[dt.date]:
    out = []
    for delta in (-1, 1):
        adj = day + dt.timedelta(days=delta)
        if early_close(market, adj) is None:
            out.append(adj)
    return out


def _full_day_probe_clocks(ec: dt.time) -> tuple[dt.time, ...]:
    extra = (_shift_clock(ec, minutes=-1), ec, _shift_clock(ec, minutes=120))
    seen: list[dt.time] = []
    for clock in _FULL_DAY_EDGES + extra:
        if clock not in seen:
            seen.append(clock)
    return tuple(seen)


def _probes_01_03() -> list[tuple[str, dt.datetime]]:
    probes: list[tuple[str, dt.datetime]] = []
    for market, day, ec in ALL_HALF_DAYS:
        for t, _expected in _half_day_probes(market, day, ec):
            probes.append((market, t))
        tz = _TZ[market]
        for adj in _adjacent_full_days(market, day):
            for clock in _full_day_probe_clocks(ec):
                probes.append((market, _at_local(adj, clock, tz)))
    return probes


def test_clkhd_00_published_set_nonempty() -> None:
    assert ALL_HALF_DAYS, "owner published no HK/US half days in the covered span"


@pytest.mark.parametrize(
    "day,ec",
    HK_HALF_DAYS,
    ids=[_half_id(MARKET_HK, d, ec) for d, ec in HK_HALF_DAYS],
)
def test_clkhd_01(day: dt.date, ec: dt.time) -> None:
    check_half_day_labels(MARKET_HK, day, ec)


@pytest.mark.parametrize(
    "day,ec",
    US_HALF_DAYS,
    ids=[_half_id(MARKET_US, d, ec) for d, ec in US_HALF_DAYS],
)
def test_clkhd_02(day: dt.date, ec: dt.time) -> None:
    check_half_day_labels(MARKET_US, day, ec)


@pytest.mark.parametrize(
    "market,day,ec",
    ALL_HALF_DAYS,
    ids=[_half_id(m, d, ec) for m, d, ec in ALL_HALF_DAYS],
)
def test_clkhd_03(market: str, day: dt.date, ec: dt.time) -> None:
    tz = _TZ[market]
    for adj in _adjacent_full_days(market, day):
        for clock in _full_day_probe_clocks(ec):
            t = _at_local(adj, clock, tz)
            got = session_part(t, market)
            expected = _base_session_part(t, market)
            assert got == expected, (
                f"{market} adjacent {adj.isoformat()} {clock} -> {got!r} BASE {expected!r}"
            )


def test_clkhd_04() -> None:
    for market, t in _probes_01_03():
        assert first_session_after(t, market) == _base_first_session_after(t, market)


def test_clkhd_05_mutant_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    import s2_clocklaw as clocklaw
    monkeypatch.setattr(clocklaw, "early_close", lambda m, d: None)
    assert HK_HALF_DAYS, "mutant catch needs at least one published HK half day"
    day, ec = HK_HALF_DAYS[0]
    with pytest.raises(AssertionError):
        check_half_day_labels(MARKET_HK, day, ec)
