"""SNI-local A12 session-state evidence for the S2 clock law (commission 8659).

This file consumes owner-supplied session calendars through s2_clocklaw
(engine.qledger CLOCK_CALENDARS -> lib.nyse_calendar / lib.hk_calendar).
It does not mint issuer or security identifiers, does not implement a
calendar, and does not feed a ranker, gate, sizer, signal, escalation, or
trade path. Halt and half-day session state are named gaps; they are not
built here.
"""
from __future__ import annotations

import datetime as dt
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from s2_clocklaw import (  # noqa: E402
    CLOCK_CALENDARS,
    MARKET_HK,
    MARKET_US,
    SESSION_SPAN_START,
    SESSION_SPAN_END,
    ClockLawFailure,
    first_session_after,
    first_session_after_disclosure_date,
    session_dates,
    session_part,
    to_utc,
)

HK_TZ = "Asia/Hong_Kong"
US_TZ = "America/New_York"
UTC = dt.timezone.utc

# Wednesday 2024-06-12 is a session on both modelled calendars.
_HK_SESSION_DAY = dt.date(2024, 6, 12)

_HK_2024_PUBLISHED_CLOSURES = (
    dt.date(2024, 2, 12),
    dt.date(2024, 2, 13),
    dt.date(2024, 3, 29),
    dt.date(2024, 4, 1),
    dt.date(2024, 12, 25),
    dt.date(2024, 12, 26),
)
_US_2024_PUBLISHED_CLOSURES = (
    dt.date(2024, 3, 29),
    dt.date(2024, 7, 4),
    dt.date(2024, 11, 28),
    dt.date(2024, 12, 25),
)

_LUNCH_EDGES = (
    ((9, 29, 59), "pre_open"),
    ((9, 30, 0), "in_session"),
    ((11, 59, 59), "in_session"),
    ((12, 0, 0), "midday_break"),
    ((12, 59, 59), "midday_break"),
    ((13, 0, 0), "in_session"),
    ((15, 59, 59), "in_session"),
    ((16, 0, 0), "after_close"),
)


def _hkt_on(day: dt.date, h: int, m: int, s: int = 0) -> dt.datetime:
    return to_utc(dt.datetime(day.year, day.month, day.day, h, m, s), HK_TZ)


def _et_on(day: dt.date, h: int, m: int, s: int = 0) -> dt.datetime:
    return to_utc(dt.datetime(day.year, day.month, day.day, h, m, s), US_TZ)


def _last_session_before(cal, d: dt.date) -> dt.date:
    cand = d - dt.timedelta(days=1)
    for _ in range(15):
        if cal.is_session(cand):
            return cand
        cand -= dt.timedelta(days=1)
    raise AssertionError(f"no modelled session before {d}")


def _next_session_after(cal, d: dt.date) -> dt.date:
    cand = d + dt.timedelta(days=1)
    for _ in range(15):
        if cal.is_session(cand):
            return cand
        cand += dt.timedelta(days=1)
    raise AssertionError(f"no modelled session after {d}")


def _holiday_skip(market: str, holiday: dt.date, tz: str) -> tuple[dt.date, dt.date, dt.date]:
    cal = CLOCK_CALENDARS[market]
    prev = _last_session_before(cal, holiday)
    cal_next = _next_session_after(cal, prev)
    got = first_session_after(_et_on(prev, 16, 30) if tz == US_TZ else _hkt_on(prev, 16, 30), market)
    return prev, cal_next, got


def test_clk_01_hk_lunch_boundaries() -> None:
    cal = CLOCK_CALENDARS[MARKET_HK]
    assert cal.is_session(_HK_SESSION_DAY)
    for (h, m, s), expected in _LUNCH_EDGES:
        t = _hkt_on(_HK_SESSION_DAY, h, m, s)
        assert session_part(t, MARKET_HK) == expected, (
            f"{h:02d}:{m:02d}:{s:02d} HKT -> {session_part(t, MARKET_HK)}")


@pytest.mark.parametrize(
    "holiday",
    [
        pytest.param(
            dt.date(2024, 2, 12),
            marks=pytest.mark.xfail(
                strict=True,
                reason="FINDING: 2024-02-12 skip lands on published HKEX closure 2024-02-13",
            ),
        ),
        pytest.param(
            dt.date(2024, 2, 13),
            marks=pytest.mark.xfail(
                strict=True,
                reason="FINDING: 2024-02-13 published HKEX LNY closure is a session in the HK calendar",
            ),
        ),
        dt.date(2024, 3, 29),
        dt.date(2024, 4, 1),
        dt.date(2024, 12, 25),
        dt.date(2024, 12, 26),
    ],
)
def test_clk_02_hk_holidays(holiday: dt.date) -> None:
    cal = CLOCK_CALENDARS[MARKET_HK]
    sessions = set(session_dates(cal))
    published = frozenset(_HK_2024_PUBLISHED_CLOSURES)
    assert holiday.isoformat() not in sessions
    prev, cal_next, got = _holiday_skip(MARKET_HK, holiday, HK_TZ)
    assert got == cal_next
    assert cal_next not in published
    assert got != holiday or holiday not in published


@pytest.mark.xfail(strict=True, reason="A12-GAP: half days now honoured via lib.exchange_holidays.early_close, but the owner publishes no 2024 HK notice (2024-02-09 returns None); flips when the owner adds it")
def test_clk_03_hk_half_days() -> None:
    # HKEX 2024-02-09 is Lunar New Year's Eve (morning-only session).
    # Clock-law session_part is wall-clock only and labels 14:00 HKT in_session.
    t = _hkt_on(dt.date(2024, 2, 9), 14, 0, 0)
    assert session_part(t, MARKET_HK) == "after_close"


@pytest.mark.parametrize("holiday", _US_2024_PUBLISHED_CLOSURES)
def test_clk_04_us_holidays(holiday: dt.date) -> None:
    cal = CLOCK_CALENDARS[MARKET_US]
    sessions = set(session_dates(cal))
    published = frozenset(_US_2024_PUBLISHED_CLOSURES)
    assert holiday.isoformat() not in sessions
    prev, cal_next, got = _holiday_skip(MARKET_US, holiday, US_TZ)
    assert got == cal_next
    assert cal_next not in published


def test_clk_05_us_dst_transitions() -> None:
    cases = (
        (dt.date(2024, 3, 8), dt.datetime(2024, 3, 8, 14, 30, tzinfo=UTC)),
        (dt.date(2024, 3, 11), dt.datetime(2024, 3, 11, 13, 30, tzinfo=UTC)),
        (dt.date(2024, 11, 1), dt.datetime(2024, 11, 1, 13, 30, tzinfo=UTC)),
        (dt.date(2024, 11, 4), dt.datetime(2024, 11, 4, 14, 30, tzinfo=UTC)),
    )
    for day, open_utc in cases:
        assert CLOCK_CALENDARS[MARKET_US].is_session(day)
        got_open = _et_on(day, 9, 30, 0)
        assert got_open == open_utc
        assert session_part(open_utc - dt.timedelta(seconds=1), MARKET_US) == "pre_open"
        assert session_part(open_utc, MARKET_US) == "in_session"

    t_0308 = dt.datetime(2024, 3, 8, 13, 45, tzinfo=UTC)
    t_0311 = dt.datetime(2024, 3, 11, 13, 45, tzinfo=UTC)
    assert session_part(t_0308, MARKET_US) == "pre_open"
    assert session_part(t_0311, MARKET_US) == "in_session"


def test_clk_06_hk_has_no_dst() -> None:
    for day in (dt.date(2024, 3, 11), dt.date(2024, 11, 4)):
        open_utc = _hkt_on(day, 9, 30, 0)
        assert open_utc == dt.datetime(day.year, day.month, day.day, 1, 30, tzinfo=UTC)
        assert session_part(open_utc, MARKET_HK) == "in_session"
        assert session_part(open_utc - dt.timedelta(seconds=1), MARKET_HK) == "pre_open"


def test_clk_07_span_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    # session_dates stops at SESSION_SPAN_END. The underlying calendars continue,
    # so first_session_after of an after-close instant on the last span session
    # returns the next real session in 2028. It does not wrap to SESSION_SPAN_START
    # and it does not return None.
    assert SESSION_SPAN_END == dt.date(2027, 12, 31)
    observed_next = {
        MARKET_HK: dt.date(2028, 1, 4),
        MARKET_US: dt.date(2028, 1, 3),
    }
    tz = {MARKET_HK: HK_TZ, MARKET_US: US_TZ}
    for market, expected in observed_next.items():
        last = dt.date.fromisoformat(session_dates(CLOCK_CALENDARS[market])[-1])
        assert last == SESSION_SPAN_END
        nxt = first_session_after(to_utc(dt.datetime(2027, 12, 31, 16, 30), tz[market]), market)
        assert isinstance(nxt, dt.date)
        assert nxt == expected
        assert nxt > last
        assert nxt != SESSION_SPAN_START

    # Fail-closed branch: when next_session_strictly_after returns None,
    # first_session_after raises ClockLawFailure (must not return a date).
    import s2_clocklaw as clocklaw
    monkeypatch.setattr(clocklaw, "next_session_strictly_after", lambda *a, **k: None)
    t = to_utc(dt.datetime(2027, 12, 31, 16, 30), US_TZ)
    with pytest.raises(ClockLawFailure, match="no session found after"):
        first_session_after(t, MARKET_US)


@pytest.mark.xfail(strict=True, reason="A12-GAP trading halts not modelled")
def test_clk_08_halt_gap_named() -> None:
    # Desired: an event during a declared single-stock halt is classified halted.
    # Public API is (t_avail_utc, market) only; 10:00 HKT on a session day is
    # in_session because the clock law has no halt input.
    t = _hkt_on(_HK_SESSION_DAY, 10, 0, 0)
    assert session_part(t, MARKET_HK) == "halted"


def _exercise_clock_law_surface() -> None:
    """Every clock-law call used above, for the no-network purity pin."""
    for (h, m, s), _expected in _LUNCH_EDGES:
        session_part(_hkt_on(_HK_SESSION_DAY, h, m, s), MARKET_HK)
    for holiday in _HK_2024_PUBLISHED_CLOSURES:
        CLOCK_CALENDARS[MARKET_HK].is_session(holiday)
        _holiday_skip(MARKET_HK, holiday, HK_TZ)
    session_part(_hkt_on(dt.date(2024, 2, 9), 14, 0, 0), MARKET_HK)
    for holiday in _US_2024_PUBLISHED_CLOSURES:
        CLOCK_CALENDARS[MARKET_US].is_session(holiday)
        _holiday_skip(MARKET_US, holiday, US_TZ)
    for day, hour, minute in (
        (dt.date(2024, 3, 8), 14, 30),
        (dt.date(2024, 3, 11), 13, 30),
        (dt.date(2024, 11, 1), 13, 30),
        (dt.date(2024, 11, 4), 14, 30),
    ):
        open_utc = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
        session_part(open_utc, MARKET_US)
        session_part(open_utc - dt.timedelta(seconds=1), MARKET_US)
        to_utc(dt.datetime(day.year, day.month, day.day, 9, 30, 0), US_TZ)
    session_part(dt.datetime(2024, 3, 8, 13, 45, tzinfo=UTC), MARKET_US)
    session_part(dt.datetime(2024, 3, 11, 13, 45, tzinfo=UTC), MARKET_US)
    for day in (dt.date(2024, 3, 11), dt.date(2024, 11, 4)):
        session_part(_hkt_on(day, 9, 30, 0), MARKET_HK)
        to_utc(dt.datetime(day.year, day.month, day.day, 9, 30, 0), HK_TZ)
    for market, tzname in ((MARKET_HK, HK_TZ), (MARKET_US, US_TZ)):
        session_dates(CLOCK_CALENDARS[market])
        first_session_after(to_utc(dt.datetime(2027, 12, 31, 16, 30), tzname), market)
    first_session_after_disclosure_date(dt.date(2024, 6, 12), MARKET_US)
    session_part(_hkt_on(_HK_SESSION_DAY, 10, 0, 0), MARKET_HK)


def test_clk_09_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a, **_k):
        raise AssertionError("clock law must not use network or git")

    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(socket, "socket", _boom)
    _exercise_clock_law_surface()
