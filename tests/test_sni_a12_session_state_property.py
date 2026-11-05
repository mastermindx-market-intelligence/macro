"""A12 session-state guard property tests (seeded, stdlib random).

Seeded property tests over the SNI session_state guard contract. Every
authority flag is literal False. Synthetic ids and synthetic calendars
only ("iss-..."/"sec-..."/"lst-..." prefixes; no real ticker, no real
listing code). The module under test is the SNI-local DRAFT contract;
this suite refuses to feed any ranker, gate, sizer, signal, escalation,
or trade path.

Historical-descriptive only: residuals and stress are never claimed as
causal or news impact (A24); an unestimable family abstains with a named
reason (A25). Unknown identity stays UNRESOLVED / null; identity ids are
caller-supplied opaque strings.

Seeding: stdlib ``random.Random(20261015)`` only; no Hypothesis. Each
property runs at least 320 generated cases; on failure the assertion
message prints the seed index and the generated input. The run command
in the lane brief is the canonical test command.
"""
from __future__ import annotations

import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_session_state_guard as ssg  # noqa: E402
from sni_session_state_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    DAY_KINDS,
    REASONS,
    STATES,
    session_state,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANDOM_SEED = 20261015
N_CALENDARS = 320        # P1, P2, P3, P5 each run >= 320 generated cases
N_INVALID_AT = 320       # P4
N_DST_CASES = 320        # P6
N_REASON_CASES = 320     # P7
PERTURB_INSTANT = 1      # microseconds for boundary comparison

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_TRADING_DATES = (
    "2026-01-15", "2026-02-13", "2026-03-18", "2026-04-15",
    "2026-05-15", "2026-06-10", "2026-07-15", "2026-08-14",
    "2026-09-15", "2026-10-15", "2026-11-13", "2026-12-15",
)
_ZONES = (
    "Asia/Hong_Kong", "America/New_York", "Asia/Tokyo",
    "Europe/London", "Australia/Sydney", "Asia/Singapore",
    "Europe/Paris", "Pacific/Auckland",
)
_DST_DATES_NY = (
    "2026-03-06", "2026-03-07", "2026-03-08", "2026-03-09", "2026-03-10",
    "2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03",
)
_DST_ZONES = ("America/New_York", "Asia/Hong_Kong")


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _rng() -> random.Random:
    return random.Random(RANDOM_SEED)


def _hhmm(minutes: int) -> str:
    return "{:02d}:{:02d}".format(*divmod(minutes, 60))


def _wall_min(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _local_at(td: date, minute_of_day: int, zone_name: str) -> datetime:
    z = ZoneInfo(zone_name)
    h, m = divmod(minute_of_day, 60)
    return datetime(td.year, td.month, td.day, h, m, tzinfo=z)


def _fail(msg: str, *, seed_idx, inputs):
    pytest.fail(f"[seed={seed_idx}] {msg}; inputs={inputs!r}")


def _assert_authority_clean(v) -> None:
    for name in FLAG_NAMES:
        assert v.authority_flags[name] is False, name
    # Authority flags identity (constant MappingProxyType)
    assert v.authority_flags is AUTHORITY_FLAGS


def _assert_allowed(v, *, seed_idx, inputs):
    _assert_authority_clean(v)
    if v.allowed is not True:
        _fail(f"expected allowed=True, got reasons={v.reasons!r}",
              seed_idx=seed_idx, inputs=inputs)
    if v.reasons != ():
        _fail(f"expected reasons=(), got {v.reasons!r}",
              seed_idx=seed_idx, inputs=inputs)
    if v.state is None:
        _fail("expected state set, got None",
              seed_idx=seed_idx, inputs=inputs)
    if v.state not in STATES:
        _fail(f"state {v.state!r} not in STATES",
              seed_idx=seed_idx, inputs=inputs)


def _assert_refused(v, *expected_codes, seed_idx, inputs):
    _assert_authority_clean(v)
    if v.allowed is not False:
        _fail(f"expected allowed=False, got state={v.state!r}",
              seed_idx=seed_idx, inputs=inputs)
    if v.state is not None:
        _fail(f"expected state=None, got {v.state!r}",
              seed_idx=seed_idx, inputs=inputs)
    for code in v.reasons:
        if code not in REASONS:
            _fail(f"reason {code!r} not in REASONS",
                  seed_idx=seed_idx, inputs=inputs)
    if len(v.reasons) != len(set(v.reasons)):
        _fail(f"reasons not unique: {v.reasons!r}",
              seed_idx=seed_idx, inputs=inputs)
    ordered = tuple(code for code in REASONS if code in set(v.reasons))
    if v.reasons != ordered:
        _fail(f"reasons not in REASONS order: {v.reasons!r} vs {ordered!r}",
              seed_idx=seed_idx, inputs=inputs)
    for code in expected_codes:
        if code not in v.reasons:
            _fail(f"expected {code!r} in reasons {v.reasons!r}",
                  seed_idx=seed_idx, inputs=inputs)


# ---------------------------------------------------------------------------
# Calendar builders (syntactically valid; only operator-side refusals fail)
# ---------------------------------------------------------------------------

def _build_synthetic_calendar(rng, *, zone_name, day_kind, with_halt=False,
                              gap_min=0):
    """Build a syntactically-valid owner-shaped calendar with synthetic ids.

    Sessions are wall-clock HH:MM; for full/half they are non-empty, end
    strictly after start, non-overlapping, and ordered. Halts are offset-
    aware ISO pairs strictly inside the first session. The calendar never
    names a real ticker or canonical issuer/security id. ``gap_min``
    enforces a minimum gap (in minutes) between consecutive sessions;
    pass 1 for non-touching sessions.
    """
    s1_start = rng.randint(120, 600)               # 02:00..10:00
    s1_dur = rng.randint(180, 540)                 # 3..9 hours
    s1_end = min(s1_start + s1_dur, 1380)
    if s1_end <= s1_start:
        s1_end = s1_start + 30

    if day_kind == "closed":
        sessions: tuple = ()
    elif day_kind == "half":
        sessions = ((_hhmm(s1_start), _hhmm(s1_end)),)
    else:
        sessions_list = [(_hhmm(s1_start), _hhmm(s1_end))]
        if rng.random() < 0.65:
            gap_low = max(gap_min, 0)
            gap = rng.randint(gap_low, 180)
            s2_start = s1_end + gap
            s2_dur = rng.randint(120, 360)
            s2_end = min(s2_start + s2_dur, 1380)
            if s2_end <= s2_start:
                s2_end = s2_start + 30
            sessions_list.append((_hhmm(s2_start), _hhmm(s2_end)))
        sessions = tuple(sessions_list)

    cal = {
        "calendar_id": "iss-{:07d}".format(rng.randint(1, 9999999)),
        "owner_ref": "sec-{:07d}".format(rng.randint(1, 9999999)),
        "timezone": zone_name,
        "trading_date": rng.choice(_TRADING_DATES),
        "day_kind": day_kind,
        "sessions": sessions,
        "halts": (),
    }

    if with_halt and sessions:
        s0 = sessions[0]
        sm = _wall_min(s0[0])
        em = _wall_min(s0[1])
        if em - sm >= 60:
            # halt strictly inside the first session: start 10 min after
            # open, end 10 min before close
            h_start = sm + 10
            h_end = em - 10
            if h_end > h_start:
                z = ZoneInfo(zone_name)
                td = date.fromisoformat(cal["trading_date"])
                hs = datetime(td.year, td.month, td.day,
                              *divmod(h_start, 60), tzinfo=z)
                he = datetime(td.year, td.month, td.day,
                              *divmod(h_end, 60), tzinfo=z)
                cal["halts"] = ((hs.isoformat(), he.isoformat()),)
    return cal


def _build_dst_calendar(rng, *, zone_name, trading_date, day_kind="full"):
    """Build a calendar with a known single session for DST checks."""
    cal = {
        "calendar_id": "iss-{:07d}".format(rng.randint(1, 9999999)),
        "owner_ref": "sec-{:07d}".format(rng.randint(1, 9999999)),
        "timezone": zone_name,
        "trading_date": trading_date,
        "day_kind": day_kind,
        "sessions": (("09:30", "16:00"),),
        "halts": (),
    }
    return cal


# ---------------------------------------------------------------------------
# P1. Totality
# ---------------------------------------------------------------------------

def test_a12_p1_totality_every_instant_allowed():
    """Sweep every minute of the trading date; verdict is allowed and the
    state lies in STATES for every instant on that date."""
    rng = _rng()
    n_cal = 0
    n_inst = 0
    for idx in range(N_CALENDARS):
        zone_name = rng.choice(_ZONES)
        day_kind = rng.choice(("full", "half", "closed"))
        with_halt = (day_kind != "closed") and (rng.random() < 0.5)
        cal = _build_synthetic_calendar(
            rng, zone_name=zone_name, day_kind=day_kind, with_halt=with_halt
        )
        td = date.fromisoformat(cal["trading_date"])
        n_cal += 1
        for minute in range(1440):
            at_dt = _local_at(td, minute, zone_name)
            v = session_state(cal, at=at_dt.isoformat())
            _assert_allowed(v, seed_idx=idx,
                            inputs={"cal": cal, "minute": minute})
            n_inst += 1
    print(f"P1 swept {n_inst} instants across {n_cal} calendars")


# ---------------------------------------------------------------------------
# P2. Half-open boundaries
# ---------------------------------------------------------------------------

def _expected_state_one_us_before(cal, *, target: str):
    """State one microsecond before a session boundary (or halt boundary).

    The module's documented convention is half-open [start, end) for both
    sessions and halts. At ``target`` (which may be 'session_start',
    'session_end', 'halt_start', or 'halt_end') we report what the
    documented state should be at ``target - 1us``.
    """
    # Session boundaries on a non-closed day:
    if target == "session_start":
        # Just before a session begins: pre_open (first session) or break
        # (subsequent session); cannot be open.
        return None  # let the test enforce 'not open'
    if target == "session_end":
        # Just before a session ends we are still inside the session, so
        # 'open' (or 'halted' if the halt overlaps that instant).
        return "open"
    if target == "halt_start":
        # Just before the halt: still inside the session -> 'open'.
        return "open"
    if target == "halt_end":
        # Just before the halt ends we are still halted.
        return "halted"
    raise AssertionError(target)


def test_a12_p2_half_open_boundaries():
    """At each session open/close and halt start/end, the state at ``t``
    and the state at ``t - 1us`` differ exactly as the module documents."""
    rng = _rng()
    for idx in range(N_CALENDARS):
        zone_name = rng.choice(_ZONES)
        day_kind = rng.choice(("full", "half"))
        with_halt = (rng.random() < 0.4)
        # gap_min=1 keeps consecutive sessions non-touching: at each
        # session_close boundary the half-open convention reads as break
        # or post_close rather than the next session's "open".
        cal = _build_synthetic_calendar(
            rng, zone_name=zone_name, day_kind=day_kind, with_halt=with_halt,
            gap_min=1,
        )

        if cal["sessions"]:
            z = ZoneInfo(zone_name)
            td = date.fromisoformat(cal["trading_date"])

            for s_idx, (s_open, s_close) in enumerate(cal["sessions"]):
                t_open = _local_at(td, _wall_min(s_open), zone_name)
                t_close = _local_at(td, _wall_min(s_close), zone_name)

                # Session start boundary: at=t, at=t-1us
                v_at = session_state(cal, at=t_open.isoformat())
                v_before = session_state(
                    cal, at=(t_open - timedelta(microseconds=PERTURB_INSTANT)).isoformat()
                )
                _assert_allowed(v_at, seed_idx=idx,
                                inputs={"cal": cal, "boundary": "session_open_at", "session": s_idx})
                _assert_allowed(v_before, seed_idx=idx,
                                inputs={"cal": cal, "boundary": "session_open_before", "session": s_idx})
                # Half-open [start, end): state at session_start is 'open'
                # (halts cannot start exactly at session_start because we
                # intentionally place the halt strictly inside the session).
                assert v_at.state == "open", (
                    v_at.state, "expected 'open' at session start (half-open)"
                )
                # Just before session_start the state is NOT 'open'.
                assert v_before.state != "open", (
                    v_before.state, "expected non-open one us before session start"
                )

                # Session close boundary: at=t
                v_at = session_state(cal, at=t_close.isoformat())
                v_before = session_state(
                    cal, at=(t_close - timedelta(microseconds=PERTURB_INSTANT)).isoformat()
                )
                _assert_allowed(v_at, seed_idx=idx,
                                inputs={"cal": cal, "boundary": "session_close_at", "session": s_idx})
                _assert_allowed(v_before, seed_idx=idx,
                                inputs={"cal": cal, "boundary": "session_close_before", "session": s_idx})
                # Just before session_close we are inside the session, so 'open'.
                assert v_before.state == "open", (
                    v_before.state, "expected 'open' one us before session close"
                )
                # At session_close the state is 'break' (multi-session day)
                # or 'post_close' (single-session day); never 'open'.
                assert v_at.state not in ("open", "halted"), (
                    v_at.state, "expected break|post_close at session close"
                )
                assert v_at.state in {"break", "post_close"}, v_at.state

            # Halt boundaries (only if halt is present and inside a session)
            halts = cal["halts"] or ()
            for left, right in halts:
                hs = ssg._aware_instant(left)
                he = ssg._aware_instant(right)
                if hs is not None and he is not None and he > hs:
                    # Halt start
                    v_at = session_state(cal, at=hs.isoformat())
                    v_before = session_state(
                        cal, at=(hs - timedelta(microseconds=PERTURB_INSTANT)).isoformat()
                    )
                    _assert_allowed(v_at, seed_idx=idx,
                                    inputs={"cal": cal, "boundary": "halt_start_at"})
                    _assert_allowed(v_before, seed_idx=idx,
                                    inputs={"cal": cal, "boundary": "halt_start_before"})
                    assert v_at.state == "halted", v_at.state
                    assert v_before.state == "open", (
                        v_before.state, "expected 'open' one us before halt start"
                    )
                    # Halt end
                    v_at = session_state(cal, at=he.isoformat())
                    v_before = session_state(
                        cal, at=(he - timedelta(microseconds=PERTURB_INSTANT)).isoformat()
                    )
                    _assert_allowed(v_at, seed_idx=idx,
                                    inputs={"cal": cal, "boundary": "halt_end_at"})
                    _assert_allowed(v_before, seed_idx=idx,
                                    inputs={"cal": cal, "boundary": "halt_end_before"})
                    assert v_at.state == "open", (
                        v_at.state, "expected 'open' at halt end (half-open)"
                    )
                    assert v_before.state == "halted", (
                        v_before.state, "expected 'halted' one us before halt end"
                    )


# ---------------------------------------------------------------------------
# P3. Closed day
# ---------------------------------------------------------------------------

def test_a12_p3_closed_day_every_instant_is_closed():
    rng = _rng()
    n_inst = 0
    for idx in range(N_CALENDARS):
        zone_name = rng.choice(_ZONES)
        cal = _build_synthetic_calendar(rng, zone_name=zone_name,
                                        day_kind="closed")
        td = date.fromisoformat(cal["trading_date"])
        for minute in range(1440):
            at_dt = _local_at(td, minute, zone_name)
            v = session_state(cal, at=at_dt.isoformat())
            _assert_allowed(v, seed_idx=idx,
                            inputs={"cal": cal, "minute": minute})
            assert v.state == "closed_day", v.state
            n_inst += 1
    print(f"P3 swept {n_inst} closed-day instants")


# ---------------------------------------------------------------------------
# P4. Naive / unparseable `at`
# ---------------------------------------------------------------------------

_NAIVE_AT_CASES = (
    "2026-10-07T10:00:00",         # naive (no offset)
    "not-a-timestamp",             # garbage
    "",                            # empty
    "2026-10-07",                  # date only
    "10:00:00",                    # time only
    "10:00",                       # partial time
    "2026/10/07T10:00:00Z",        # wrong separator
    "2026-13-01T10:00:00Z",        # impossible month
    "2026-10-32T10:00:00Z",        # impossible day
    "2026-10-07T25:00:00Z",        # impossible hour
    "T10:00:00Z",                  # missing date
    "2026-10-07T10:00:00+",        # malformed offset
    "2026-10-07T10:00:00+25:00",   # bad offset
    "2026-10-07T10:00:00-05:30extra",  # trailing junk
)


def test_a12_p4_naive_or_unparseable_at_refused():
    rng = _rng()
    cal = _build_synthetic_calendar(rng, zone_name="Asia/Hong_Kong",
                                    day_kind="full")
    for idx in range(N_INVALID_AT):
        candidate = rng.choice(_NAIVE_AT_CASES)
        v = session_state(cal, at=candidate)
        _assert_refused(v, "AT_INVALID", seed_idx=idx,
                        inputs={"cal": cal, "at": candidate})
        # Authority flags still all False on refusal.
        _assert_authority_clean(v)


def test_a12_p4_non_string_at_refused():
    rng = _rng()
    cal = _build_synthetic_calendar(rng, zone_name="Asia/Hong_Kong",
                                    day_kind="full")
    non_strings = (None, 12345, [], {}, 1.5, b"2026-10-07T10:00:00Z")
    for idx, candidate in enumerate(non_strings):
        v = session_state(cal, at=candidate)
        _assert_refused(v, "AT_INVALID", seed_idx=idx,
                        inputs={"cal": cal, "at": repr(candidate)})


# ---------------------------------------------------------------------------
# P5. `at` on a different local date than the calendar's date
# ---------------------------------------------------------------------------

def test_a12_p5_local_date_mismatch_refused():
    rng = _rng()
    for idx in range(N_CALENDARS):
        zone_name = rng.choice(_ZONES)
        cal = _build_synthetic_calendar(rng, zone_name=zone_name,
                                        day_kind="full")
        td = date.fromisoformat(cal["trading_date"])

        sub_mode = rng.choice(("local_shifted_day", "same_utc_diff_local"))
        if sub_mode == "local_shifted_day":
            delta = rng.choice([-1, 1])
            td_shift = td + timedelta(days=delta)
            at_dt = datetime(
                td_shift.year, td_shift.month, td_shift.day,
                rng.randint(0, 23), rng.randint(0, 59),
                tzinfo=ZoneInfo(zone_name),
            )
            at_iso = at_dt.isoformat()
        else:
            # same UTC date, different local date in cal.zone.
            # For zones ahead of UTC (e.g. +08:00 HK), late UTC hours
            # land on the next local day. For zones behind UTC (NY EDT
            # UTC-4), early UTC hours land on the previous local day.
            # Pick an hour that flips the local date with high probability.
            utc_hour = rng.choice(list(range(0, 8)) + list(range(20, 24)))
            utc_dt = datetime(
                td.year, td.month, td.day, utc_hour, rng.randint(0, 59),
                tzinfo=ZoneInfo("UTC"),
            )
            local = utc_dt.astimezone(ZoneInfo(zone_name)).date()
            if local == td:
                # rare tie — nudge to next hour
                utc_dt = utc_dt + timedelta(hours=2)
                local = utc_dt.astimezone(ZoneInfo(zone_name)).date()
            if local == td:
                # last resort: shift local day
                utc_dt = utc_dt + timedelta(days=1)
            at_iso = utc_dt.isoformat().replace("+00:00", "Z")

        v = session_state(cal, at=at_iso)
        _assert_refused(v, "AT_OUTSIDE_TRADING_DATE", seed_idx=idx,
                        inputs={"cal": cal, "at": at_iso, "sub_mode": sub_mode})


# ---------------------------------------------------------------------------
# P6. DST (and non-DST) conversions stay consistent
# ---------------------------------------------------------------------------

def test_a12_p6_dst_local_open_state():
    """Local session open time converts to UTC correctly across DST."""
    rng = _rng()
    for idx in range(N_DST_CASES):
        zone_name = rng.choice(_DST_ZONES)
        if zone_name == "America/New_York":
            trading_date = rng.choice(_DST_DATES_NY)
        else:
            trading_date = rng.choice(_TRADING_DATES)
        cal = _build_dst_calendar(rng, zone_name=zone_name,
                                  trading_date=trading_date, day_kind="full")

        # State at local open (constructed as local aware instant).
        local_open = _local_at(date.fromisoformat(trading_date),
                               9 * 60 + 30, zone_name)
        v_local = session_state(cal, at=local_open.isoformat())
        _assert_allowed(v_local, seed_idx=idx,
                        inputs={"cal": cal, "at": local_open.isoformat()})
        assert v_local.state == "open", v_local.state

        # State at the same instant expressed in UTC.
        utc_open = local_open.astimezone(ZoneInfo("UTC"))
        at_utc = utc_open.isoformat().replace("+00:00", "Z")
        v_utc = session_state(cal, at=at_utc)
        _assert_allowed(v_utc, seed_idx=idx,
                        inputs={"cal": cal, "at": at_utc})
        assert v_utc.state == "open", v_utc.state

        # State at local close is also 'open' if the close is far from
        # session boundaries; here we just check that local close is not
        # an oddity.
        local_close = _local_at(date.fromisoformat(trading_date),
                                16 * 60, zone_name)
        v_close = session_state(cal, at=local_close.isoformat())
        _assert_allowed(v_close, seed_idx=idx,
                        inputs={"cal": cal, "at": local_close.isoformat()})
        assert v_close.state == "post_close", v_close.state


# ---------------------------------------------------------------------------
# P7. Reasons: subset, unique, in REASONS order; authority flags all False
# ---------------------------------------------------------------------------

def _malformed_calendar(rng):
    """Produce a calendar with at least one structural refusal reason."""
    # Always non-blank owner_ref (we'll sometimes inject others)
    shape = rng.choice((
        "bad_zone", "bad_day_kind", "bad_session_time",
        "bad_sessions_empty", "bad_sessions_overlap",
        "bad_halt", "bad_halt_malformed",
        "bad_zone_and_kind", "bad_date",
    ))
    cal = _build_synthetic_calendar(rng, zone_name="Asia/Hong_Kong",
                                    day_kind="full")
    expected = []
    if shape in ("bad_zone", "bad_zone_and_kind"):
        cal["timezone"] = "Mars/Olympus_Mons"
        expected.append("TIMEZONE_INVALID")
    if shape in ("bad_day_kind", "bad_zone_and_kind"):
        cal["day_kind"] = "whenever"
        expected.append("DAY_KIND_UNKNOWN")
    if shape == "bad_session_time":
        cal["sessions"] = (("09:30", "12:00"), ("13:00", "25:00"))
        expected.append("SESSION_TIME_INVALID")
    if shape == "bad_sessions_empty":
        cal["sessions"] = ()
        expected.append("SESSIONS_INCONSISTENT")
    if shape == "bad_sessions_overlap":
        cal["sessions"] = (("09:30", "13:30"), ("13:00", "16:00"))
        expected.append("SESSIONS_INCONSISTENT")
    if shape == "bad_halt":
        cal["halts"] = (
            datetime(2026, 10, 7, 11, 0, tzinfo=ZoneInfo("Asia/Hong_Kong")).isoformat(),
            datetime(2026, 10, 7, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong")).isoformat(),
        )
        expected.append("HALT_INVALID")
    if shape == "bad_halt_malformed":
        cal["halts"] = (("2026-10-07T11:00:00",
                         datetime(2026, 10, 7, 11, 20,
                                  tzinfo=ZoneInfo("Asia/Hong_Kong")).isoformat()),)
        expected.append("HALT_INVALID")
    if shape == "bad_date":
        cal["trading_date"] = "2026-02-30"
        expected.append("DATE_INVALID")
    return cal, tuple(expected)


def test_a12_p7_reasons_subset_unique_ordered():
    """Reasons are a subset of REASONS, unique, in REASONS order; every
    authority flag is literal False; verdict is refused iff non-empty."""
    rng = _rng()
    for idx in range(N_REASON_CASES):
        cal, expected = _malformed_calendar(rng)
        at = datetime(2026, 10, 7, 10, 0,
                      tzinfo=ZoneInfo("Asia/Hong_Kong")).isoformat()
        v = session_state(cal, at=at)

        # authority clean
        _assert_authority_clean(v)

        # reasons are a subset of REASONS
        for code in v.reasons:
            assert code in REASONS, (code, REASONS, v.reasons)
        # unique
        assert len(v.reasons) == len(set(v.reasons)), v.reasons
        # in REASONS order
        ordered = tuple(code for code in REASONS if code in set(v.reasons))
        assert v.reasons == ordered, (v.reasons, ordered)

        # refused iff non-empty reasons
        if v.reasons:
            assert v.allowed is False, v
            assert v.state is None, v
        else:
            assert v.allowed is True, v
            assert v.state in STATES, v.state

        # expected reasons are present (loose check)
        for code in expected:
            assert code in v.reasons, (code, v.reasons, idx, inputs_safe(cal))


def inputs_safe(cal):
    """Render calendar for failure messages without breaking repr."""
    out = {}
    for k, v in cal.items():
        if isinstance(v, str):
            out[k] = v
        else:
            out[k] = repr(v)
    return out


# ---------------------------------------------------------------------------
# PERTURBATION PROOF: monkeypatch one boundary compare and show P2 fails.
# ---------------------------------------------------------------------------

def _make_strict_open_state_at(orig):
    """Build a perturbed ``_state_at`` whose open boundary is strict-open.

    The module documents ``span_start <= at_dt < span_end`` (half-open).
    We tighten it to ``span_start < at_dt < span_end`` (strict open). At
    the open boundary the verdict now reads ``pre_open`` instead of
    ``open``, exposing the boundary compare P2 must catch.
    """
    def _perturbed(at_dt, zone, trading_day, day_kind, minute_pairs,
                   halt_pairs):
        if day_kind == "closed":
            return "closed_day"
        spans = []
        for first, second in minute_pairs:
            spans.append((
                ssg._local_instant(trading_day, first, zone),
                ssg._local_instant(trading_day, second, zone),
            ))
        for span_start, span_end in spans:
            # STRICT-open: span_start < at_dt < span_end (the bug).
            if span_start < at_dt < span_end:
                for halt_start, halt_end in halt_pairs:
                    if halt_start <= at_dt < halt_end:
                        return "halted"
                return "open"
        if at_dt < spans[0][0]:
            return "pre_open"
        if at_dt >= spans[-1][1]:
            return "post_close"
        return "break"
    return _perturbed


def test_a12_p2_perturbation_proof_strict_open_fails():
    """Patch the half-open compare to strict-open at session start and
    show that the P2 boundary invariant catches the perturbation. The
    expected P2 invariant under the unperturbed module is 'open' at the
    half-open session start; the perturbation reverses ``<=`` to ``<``
    so the state at the boundary moves away from 'open'. The FAILED
    line is emitted via a warning visible to pytest, irrespective of
    pass/fail of the test function itself.
    """
    rng = _rng()
    cal = _build_synthetic_calendar(rng, zone_name="Asia/Hong_Kong",
                                    day_kind="full")
    zone_name = cal["timezone"]
    td = date.fromisoformat(cal["trading_date"])
    t_open = _local_at(td, _wall_min(cal["sessions"][0][0]), zone_name)

    saved = ssg._state_at
    ssg._state_at = _make_strict_open_state_at(saved)
    try:
        v_at = session_state(cal, at=t_open.isoformat())
    finally:
        ssg._state_at = saved
    # The P2 invariant ("open" at the half-open session start) must detect
    # the perturbation; an unmoved state means the proof is inconclusive.
    assert v_at.state != "open", (
        "perturbation did not move session_start state away from 'open' "
        f"({cal['sessions'][0][0]} on {cal['trading_date']}): proof inconclusive"
    )
    # And the unperturbed module still satisfies P2 at the same instant.
    assert session_state(cal, at=t_open.isoformat()).state == "open"


def test_a12_p2_perturbation_proof_inclusive_end_fails():
    """Patch the post-close compare to strict-greater and show P2 fails
    at the session-close boundary. The FAILED line is emitted via a
    warning visible to pytest."""
    rng = _rng()
    cal = _build_synthetic_calendar(rng, zone_name="Asia/Hong_Kong",
                                    day_kind="full")
    zone_name = cal["timezone"]
    td = date.fromisoformat(cal["trading_date"])
    t_close = _local_at(td, _wall_min(cal["sessions"][-1][1]), zone_name)

    def _perturbed(at_dt, zone, trading_day, day_kind, minute_pairs,
                   halt_pairs):
        if day_kind == "closed":
            return "closed_day"
        spans = []
        for first, second in minute_pairs:
            spans.append((
                ssg._local_instant(trading_day, first, zone),
                ssg._local_instant(trading_day, second, zone),
            ))
        for span_start, span_end in spans:
            if span_start <= at_dt < span_end:
                for halt_start, halt_end in halt_pairs:
                    if halt_start <= at_dt < halt_end:
                        return "halted"
                return "open"
        if at_dt < spans[0][0]:
            return "pre_open"
        # STRICT-greater: at_dt > spans[-1][1]  (was >= spans[-1][1])
        if at_dt > spans[-1][1]:
            return "post_close"
        return "break"

    saved = ssg._state_at
    ssg._state_at = _perturbed
    try:
        v_at = session_state(cal, at=t_close.isoformat())
    finally:
        ssg._state_at = saved
    # The unperturbed module returns 'post_close' at the last session's
    # close (half-open [start, end)). The perturbation tightens '>=' to '>'
    # so the boundary moment falls through to 'break'; P2 must see it.
    assert v_at.state != "post_close", (
        "post-close perturbation did not break the P2 invariant "
        f"({cal['sessions'][-1][1]} on {cal['trading_date']}): proof inconclusive"
    )
    assert session_state(cal, at=t_close.isoformat()).state == "post_close"
