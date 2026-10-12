"""Session-clock and expiry boundaries for both pullback snapshot adapters.

Synthetic only: a stub ``read`` hands back a one-row LicensedCloses and a stub
``observer`` returns the owner's own unavailable shape, so every test here
exercises only the market-calendar clock logic — expected session, successor
session, and valid_until — never a source, a price path, or a forecast.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest

from lib import cn_calendar, nyse_calendar
from lib import cn_pullback_observation as cn_pb
from lib import pullback_depth as core
from lib import us_pullback_observation as us_pb
from lib.pullback_depth import LicensedCloses

CST, ET = cn_calendar.CST, nyse_calendar.ET
# One synthetic settled close; the observer stub never reads it.
_STUB_ROW = ("2026-01-05", 100.0)


def stub_read(expected):
    return LicensedCloses(rows=[_STUB_ROW])


def stub_observer(rows, *, expected_session, is_session):
    # The owner's own unavailable shape: passes observe_closes' schema gate
    # without exercising a single price rule.
    return core.unavailable(expected_session, "stub_clock_only")


def cn_snapshot(now):
    return cn_pb.snapshot(now=now, read=stub_read, observer=stub_observer)


def us_snapshot(now):
    return us_pb.snapshot(now=now, read=stub_read, observer=stub_observer)


def U(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)


# ── K1 — the 17:00 settle buffer rolls the expected session ──────────────────

def test_cn_before_the_settle_buffer_the_prior_session_is_expected():
    before = cn_snapshot(U(2026, 3, 10, 8, 59))   # 16:59 CST
    at = cn_snapshot(U(2026, 3, 10, 9, 0))        # 17:00 CST
    assert before["quality"] == "stub_clock_only"
    assert before["expected_session"] == "2026-03-09"
    assert at["expected_session"] == "2026-03-10"
    # Settling the session rolls the expiry to the NEXT session's settle.
    assert before["valid_until"] == "2026-03-10T09:00:00+00:00"
    assert at["valid_until"] == "2026-03-11T09:00:00+00:00"


def test_us_before_the_settle_buffer_the_prior_session_is_expected():
    before = us_snapshot(U(2026, 6, 9, 20, 59))   # 16:59 EDT
    at = us_snapshot(U(2026, 6, 9, 21, 0))        # 17:00 EDT
    assert before["expected_session"] == "2026-06-08"
    assert at["expected_session"] == "2026-06-09"
    assert before["valid_until"] == "2026-06-09T21:00:00+00:00"
    assert at["valid_until"] == "2026-06-10T21:00:00+00:00"


# ── K2 — a Friday view expires at the next session's settle ──────────────────

def test_cn_friday_expiry_lands_on_mondays_settle():
    out = cn_snapshot(U(2026, 3, 13, 10, 0))      # 18:00 CST Friday
    assert out["expected_session"] == "2026-03-13"
    assert out["valid_until"] == "2026-03-16T09:00:00+00:00"   # Mon 17:00 CST


def test_cn_friday_expiry_skips_a_holiday_monday():
    # Qingming 2026 is observed Monday 04-06 on the announced slate, so the
    # first session after Friday 04-03 is Tuesday 04-07.
    assert cn_calendar.is_session(date(2026, 4, 3))
    assert not cn_calendar.is_session(date(2026, 4, 6))
    out = cn_snapshot(U(2026, 4, 3, 10, 0))
    assert out["valid_until"] == "2026-04-07T09:00:00+00:00"   # Tue 17:00 CST


def test_us_friday_expiry_lands_on_mondays_settle():
    out = us_snapshot(U(2026, 6, 12, 21, 30))     # 17:30 EDT Friday
    assert out["expected_session"] == "2026-06-12"
    assert out["valid_until"] == "2026-06-15T21:00:00+00:00"   # Mon 17:00 EDT


def test_us_friday_expiry_skips_memorial_day_monday():
    out = us_snapshot(U(2026, 5, 22, 21, 30))
    assert out["expected_session"] == "2026-05-22"
    assert out["valid_until"] == "2026-05-26T21:00:00+00:00"   # Tue 17:00 EDT


# ── K3 — CN long closures: valid_until jumps past the whole span ─────────────

def test_cn_expiry_spans_the_2026_golden_week_closure():
    # Announced 2026 slate: 10-01..10-07 closed (weekday legs 1, 2, 5, 6, 7);
    # the first post-holiday session is Thursday 10-08.
    settled = cn_snapshot(U(2026, 9, 30, 10, 0))   # 18:00 CST Wednesday
    mid = cn_snapshot(U(2026, 10, 5, 4, 0))        # Monday inside the closure
    assert settled["expected_session"] == mid["expected_session"] == "2026-09-30"
    assert (settled["valid_until"] == mid["valid_until"]
            == "2026-10-08T09:00:00+00:00")        # Thu 10-08 17:00 CST


def test_cn_expiry_spans_the_2026_spring_festival_closure():
    # Announced 2026 slate: 02-16..02-20 plus 02-23 closed; trading resumes
    # Tuesday 02-24, so Friday 02-13's view stays valid across the whole span.
    settled = cn_snapshot(U(2026, 2, 13, 10, 0))
    mid = cn_snapshot(U(2026, 2, 18, 4, 0))
    assert settled["expected_session"] == mid["expected_session"] == "2026-02-13"
    assert (settled["valid_until"] == mid["valid_until"]
            == "2026-02-24T09:00:00+00:00")        # Tue 02-24 17:00 CST


# ── K4 — US holidays and DST transitions in the expiry's UTC hour ────────────

def test_us_expiry_hour_shifts_across_the_spring_dst_transition():
    before = parse(us_snapshot(U(2026, 3, 5, 23, 0))["valid_until"])   # Thu 18:00 EST
    after = parse(us_snapshot(U(2026, 3, 6, 23, 0))["valid_until"])    # Fri 18:00 EST
    # The same 17:00 ET settle serializes one hour earlier in UTC after the
    # spring-forward; the local view keeps the wall clock and flips the offset.
    assert (before.hour, before.astimezone(ET).utcoffset()) == (
        22, timedelta(hours=-5))                                       # EST
    assert (after.hour, after.astimezone(ET).utcoffset()) == (
        21, timedelta(hours=-4))                                       # EDT
    assert after.astimezone(ET).hour == 17
    assert after.date() == date(2026, 3, 9)   # first session after spring-forward


def test_us_expiry_hour_shifts_across_the_fall_dst_transition():
    before = parse(us_snapshot(U(2026, 10, 29, 21, 30))["valid_until"])
    after = parse(us_snapshot(U(2026, 10, 30, 21, 30))["valid_until"])
    assert (before.hour, before.astimezone(ET).utcoffset()) == (
        21, timedelta(hours=-4))                                       # EDT
    assert (after.hour, after.astimezone(ET).utcoffset()) == (
        22, timedelta(hours=-5))                                       # EST
    assert after.astimezone(ET).hour == 17
    assert after.date() == date(2026, 11, 2)   # first session after fall-back


def test_us_expiry_stays_on_est_after_the_fall_back():
    out = us_snapshot(U(2026, 11, 5, 22, 30))     # 17:30 EST Thursday
    assert out["valid_until"] == "2026-11-06T22:00:00+00:00"


def test_us_expiry_skips_thanksgiving_2026():
    out = us_snapshot(U(2026, 11, 25, 22, 0))     # 17:00 EST exactly: Wednesday settled
    assert out["expected_session"] == "2026-11-25"
    assert out["valid_until"] == "2026-11-27T22:00:00+00:00"   # Friday, past Thursday


def test_us_expiry_skips_the_observed_independence_day_2026():
    # July 4 2026 is a Saturday; the announced slate closes Friday 07-03.
    out = us_snapshot(U(2026, 7, 2, 21, 0))
    assert out["expected_session"] == "2026-07-02"
    assert out["valid_until"] == "2026-07-06T21:00:00+00:00"   # Monday


def test_us_expiry_skips_good_friday_2026():
    out = us_snapshot(U(2026, 4, 2, 21, 0))
    assert out["expected_session"] == "2026-04-02"
    assert out["valid_until"] == "2026-04-06T21:00:00+00:00"   # Easter Monday


# ── K5 — the view never expires itself, minute by minute ────────────────────

def _fortnight(snapshot_of, start: datetime, local_zone, is_session):
    steps = (14 * 24 * 60) // 37 + 1
    for step in range(steps):
        now = start + timedelta(minutes=37 * step)
        out = snapshot_of(now)
        produced = parse(out["produced_at"])
        valid = parse(out["valid_until"])
        assert produced == now.astimezone(timezone.utc), step
        assert valid > produced, step
        local = valid.astimezone(local_zone)
        assert local.time() == time(17, 0), step
        assert is_session(local.date()), step
        assert local.date() > date.fromisoformat(out["expected_session"]), step


def test_cn_every_odd_offset_across_a_fortnight_produces_before_it_expires():
    # The window covers the 2026 Golden Week closure end to end.
    _fortnight(cn_snapshot, U(2026, 9, 28, 0, 0), CST, cn_calendar.is_session)


def test_us_every_odd_offset_across_a_fortnight_produces_before_it_expires():
    # The window covers the November 2026 fall-back transition end to end.
    _fortnight(us_snapshot, U(2026, 10, 30, 0, 0), ET, nyse_calendar.is_session)


# ── K6 — the clock contract at the boundary ──────────────────────────────────

@pytest.mark.parametrize("snapshot_of", [cn_snapshot, us_snapshot], ids=["cn", "us"])
@pytest.mark.parametrize("bad_now", [
    datetime(2026, 6, 9, 12, 0),                    # naive
    "2026-06-09T12:00:00+00:00",                    # not a datetime at all
])
def test_non_aware_now_is_refused(snapshot_of, bad_now):
    with pytest.raises(ValueError):
        snapshot_of(bad_now)


def test_cn_an_offset_clock_reads_as_the_same_instant():
    via_cst = cn_snapshot(datetime(2026, 3, 10, 2, 0,
                                   tzinfo=timezone(timedelta(hours=8))))
    via_utc = cn_snapshot(U(2026, 3, 9, 18, 0))
    assert via_cst == via_utc


def test_us_an_offset_clock_reads_as_the_same_instant():
    via_est = us_snapshot(datetime(2026, 6, 9, 13, 0,
                                   tzinfo=timezone(timedelta(hours=-5))))
    via_utc = us_snapshot(U(2026, 6, 9, 18, 0))
    assert via_est == via_utc


# ── K7 — behaviour beyond the encoded calendar tables ────────────────────────

def test_cn_beyond_the_encoded_tables_the_calendar_degrades_without_raising():
    # lib/cn_calendar encodes the lunar/festival tables through 2030 and the
    # official 2026 notice; past them holidays() falls back to the fixed-date
    # core (Jan 1, May 1, Oct 1-7) plus weekends. Actual behaviour: the
    # snapshot still answers — no ValueError — and the successor is a plain
    # next-weekday session, since June carries no encoded closure.
    out = cn_snapshot(U(2101, 6, 1, 12, 0))
    valid = parse(out["valid_until"])
    assert valid > parse(out["produced_at"])
    assert valid.astimezone(CST).time() == time(17, 0)
    assert valid.astimezone(CST).date() - date.fromisoformat(
        out["expected_session"]) <= timedelta(days=4)


def test_us_beyond_the_encoded_tables_the_rules_still_answer():
    # lib/nyse_calendar computes every year from rules, so nothing is "beyond"
    # it; the same graceful shape holds.
    out = us_snapshot(U(2101, 6, 1, 12, 0))
    valid = parse(out["valid_until"])
    assert valid > parse(out["produced_at"])
    assert valid.astimezone(ET).time() == time(17, 0)
    assert valid.astimezone(ET).date() - date.fromisoformat(
        out["expected_session"]) <= timedelta(days=4)


def test_cn_raises_when_no_successor_session_exists(monkeypatch):
    # The documented refusal path: an unbroken closure longer than the
    # successor horizon (MAX_LEGIT_CLOSURE_DAYS + 7 = 18 days) leaves the
    # adapter unable to place the next settle, and it raises rather than guess.
    closed = frozenset(date(2026, 3, 7) + timedelta(days=i) for i in range(25))
    monkeypatch.setattr(cn_calendar, "ONE_OFF_CLOSURES", closed)
    with pytest.raises(ValueError, match="successor"):
        cn_snapshot(U(2026, 3, 6, 10, 0))


def test_us_raises_when_no_successor_session_exists(monkeypatch):
    closed = frozenset(date(2026, 3, 7) + timedelta(days=i) for i in range(25))
    monkeypatch.setattr(nyse_calendar, "ONE_OFF_CLOSURES", closed)
    with pytest.raises(ValueError, match="successor"):
        us_snapshot(U(2026, 3, 6, 23, 0))
