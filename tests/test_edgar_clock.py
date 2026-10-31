"""Tests for lib/edgar_clock.py — EDGAR acceptance clocks as true UTC (prereg §10 A2).

The submissions-JSON helper must agree with the frozen WP31 evaluator's
``_edgar_json_acceptance_utc`` on every input, so readers migrated onto
``lib.edgar_clock`` keep the clock the evaluator was preregistered on.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.edgar_clock import ET, sgml_acceptance_utc, submissions_acceptance_utc
from scripts import c19_wp31_sources as sources

UTC = timezone.utc

# 2026 DST transitions in UTC: spring forward 2026-03-08 07:00Z, fall back 2026-11-01 06:00Z.
_TRANSITIONS = (datetime(2026, 3, 8, 7, tzinfo=UTC), datetime(2026, 11, 1, 6, tzinfo=UTC))
# 01:00-01:59 EST on spring-forward Sunday: the one hour a corrupted JSON clock resolves late.
_SPRING_HOUR = (datetime(2026, 3, 8, 6, tzinfo=UTC), _TRANSITIONS[0])


def _steps(start: datetime, end: datetime, step: timedelta) -> list[datetime]:
    out, t = [], start
    while t <= end:
        out.append(t)
        t += step
    return out


def _parity_grid() -> list[datetime]:
    """Hourly through 2026, every 15 min across both transition weeks, every
    minute within 6 h of each transition."""
    grid = _steps(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 12, 31, 23, tzinfo=UTC),
                  timedelta(hours=1))
    for lo, hi in ((datetime(2026, 3, 6, tzinfo=UTC), datetime(2026, 3, 11, tzinfo=UTC)),
                   (datetime(2026, 10, 30, tzinfo=UTC), datetime(2026, 11, 4, tzinfo=UTC))):
        grid += _steps(lo, hi, timedelta(minutes=15))
    for t in _TRANSITIONS:
        grid += _steps(t - timedelta(hours=6), t + timedelta(hours=6), timedelta(minutes=1))
    return sorted(set(grid))


def _json_form(j: datetime) -> str:
    return j.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _wall_stamp(u: datetime) -> str:
    return u.astimezone(ET).strftime("%Y%m%d%H%M%S")


def _near_transition(u: datetime) -> bool:
    return any(abs(u - t) <= timedelta(hours=6) for t in _TRANSITIONS)


def _in_spring_hour(u: datetime) -> bool:
    return _SPRING_HOUR[0] <= u < _SPRING_HOUR[1]


def _corrupted_json(u: datetime) -> str:
    # The JSON clock modelled as the true instant shifted by the NY offset at that
    # instant (reads 4 h / 5 h late).  A2 saw daytime filings only, where shifting by
    # the offset at the JSON clock instead gives the same value.
    return _json_form(u - u.astimezone(ET).utcoffset())


# --- form (a): submissions-JSON acceptanceDateTime ---------------------------------


def test_submissions_clock_edt_and_est_pins() -> None:
    assert submissions_acceptance_utc("2026-07-30T00:04:53.000Z") == datetime(2026, 7, 29, 20, 4, 53, tzinfo=UTC)
    assert submissions_acceptance_utc("2026-01-29T02:04:38.000Z") == datetime(2026, 1, 28, 21, 4, 38, tzinfo=UTC)


def test_submissions_clock_dst_transitions_are_unresolvable() -> None:
    assert submissions_acceptance_utc("2026-03-08T09:00:00Z") is None   # spring-forward hour
    assert submissions_acceptance_utc("2026-11-01T08:00:00Z") is None   # fall-back hour


def test_submissions_clock_matches_the_frozen_evaluator_on_the_grid() -> None:
    frozen = sources._edgar_json_acceptance_utc
    mismatches = []
    for j in _parity_grid():
        for value in (_json_form(j), j, j.replace(tzinfo=None)):
            if submissions_acceptance_utc(value) != frozen(value):
                mismatches.append(value)
    assert mismatches == []


@pytest.mark.parametrize("value", [
    None, "", "   ", "garbage", "2026-13-01T00:00:00Z", "2026-07-30", "2026-07-30T00:04:53+02:00",
    "20260729160453", 20260729160453, 1785370000.0, b"2026-07-30T00:04:53Z",
    datetime(2026, 7, 30, 0, 4, 53), datetime(2026, 7, 30, 0, 4, 53, tzinfo=ET),
])
def test_submissions_clock_matches_the_frozen_evaluator_on_odd_input(value) -> None:
    assert submissions_acceptance_utc(value) == sources._edgar_json_acceptance_utc(value)


def test_submissions_clock_is_right_or_unresolved_outside_the_spring_hour() -> None:
    late = []
    for u in _parity_grid():
        got = submissions_acceptance_utc(_corrupted_json(u))
        if _in_spring_hour(u):
            late.append(got - u)
        else:
            assert got == u or (got is None and _near_transition(u)), u
    # Inside the spring hour the round-trip check passes on the wrong side of the
    # transition: every value resolves exactly one hour late (no EDGAR filings then).
    assert late and set(late) == {timedelta(hours=1)}


# --- form (b): SGML header ACCEPTANCE-DATETIME --------------------------------------


def test_sgml_clock_edt_and_est_pins() -> None:
    assert sgml_acceptance_utc("20260729160453") == datetime(2026, 7, 29, 20, 4, 53, tzinfo=UTC)
    assert sgml_acceptance_utc("20260128160438") == datetime(2026, 1, 28, 21, 4, 38, tzinfo=UTC)
    assert sgml_acceptance_utc(" 20260128160438\n") == datetime(2026, 1, 28, 21, 4, 38, tzinfo=UTC)


@pytest.mark.parametrize("value", [
    "20260308023000",   # skipped by spring forward
    "20261101013000",   # repeated by fall back
    None, "", "2026072916045", "202607291604530", "20261332000000", "2026-07-29T16:04:53",
    20260729160453, "2026072916045x",
])
def test_sgml_clock_refuses_unresolvable_and_malformed(value) -> None:
    assert sgml_acceptance_utc(value) is None


def test_sgml_clock_round_trips_every_unambiguous_wall_time() -> None:
    for u in _parity_grid():
        got = sgml_acceptance_utc(_wall_stamp(u))
        assert got == u or (got is None and _near_transition(u)), u


def test_both_forms_name_the_same_instant() -> None:
    # One filing, two clocks: the header wall time and the corrupted JSON value.
    resolved = 0
    for u in _parity_grid():
        a = submissions_acceptance_utc(_corrupted_json(u))
        b = sgml_acceptance_utc(_wall_stamp(u))
        if a is None or b is None:
            continue
        if _in_spring_hour(u):
            assert (a, b) == (u + timedelta(hours=1), u), u   # the header clock exposes it
        else:
            assert a == b == u, u
            resolved += 1
    assert resolved > 8000
