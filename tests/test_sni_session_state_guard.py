"""A12 session-state guard tests: malformed calendars refuse; a well-formed
owner-supplied trading day maps an offset-aware instant to a session state.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic calendars shaped like market-calendar owner
records; every wall-clock and zone literal lives here, never in the module.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_session_state_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    DAY_KINDS,
    REASONS,
    STATES,
    SessionStateVerdict,
    refuse_nonfalse_authority,
    session_state,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_session_state_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_HK_TZ = "Asia/Hong_Kong"
_US_TZ = "America/New_York"
_AT_MORNING = "2026-10-07T10:00:00+08:00"


class _Omit:
    pass


_OMIT = _Omit()


def _hk_day(**overrides):
    day = {
        "calendar_id": "SYN-CAL-HK-1",
        "owner_ref": "SYN-CAL-OWNER-HK-1",
        "timezone": _HK_TZ,
        "trading_date": "2026-10-07",
        "day_kind": "full",
        "sessions": (("09:30", "12:00"), ("13:00", "16:00")),
        "halts": (),
    }
    day.update(overrides)
    drop = [key for key, val in day.items() if val is _OMIT]
    for key in drop:
        del day[key]
    return day


def _us_day(**overrides):
    day = {
        "calendar_id": "SYN-CAL-US-1",
        "owner_ref": "SYN-CAL-OWNER-US-1",
        "timezone": _US_TZ,
        "trading_date": "2026-06-10",
        "day_kind": "full",
        "sessions": (("09:30", "16:00"),),
        "halts": (),
    }
    day.update(overrides)
    drop = [key for key, val in day.items() if val is _OMIT]
    for key in drop:
        del day[key]
    return day


def _assert_allowed(verdict, state):
    assert verdict.allowed is True, verdict
    assert verdict.reasons == ()
    assert verdict.state == state, (verdict.state, state)
    assert verdict.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False


def _assert_refused(verdict, *codes):
    assert verdict.allowed is False, verdict
    assert verdict.state is None, verdict.state
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    assert verdict.reasons == tuple(code for code in REASONS if code in got)
    assert verdict.authority_flags is AUTHORITY_FLAGS


# ---------------------------------------------------------------------------
# HK full day, half day, closed day
# ---------------------------------------------------------------------------


def test_a12_hk_full_day_five_instants():
    day = _hk_day()
    _assert_allowed(session_state(day, at="2026-10-07T09:00:00+08:00"), "pre_open")
    _assert_allowed(session_state(day, at="2026-10-07T10:00:00+08:00"), "open")
    _assert_allowed(session_state(day, at="2026-10-07T12:30:00+08:00"), "break")
    _assert_allowed(session_state(day, at="2026-10-07T14:00:00+08:00"), "open")
    _assert_allowed(session_state(day, at="2026-10-07T17:00:00+08:00"), "post_close")


def test_a12_hk_half_day_afternoon_post_close():
    day = _hk_day(
        trading_date="2026-12-24", day_kind="half", sessions=(("09:30", "12:00"),)
    )
    _assert_allowed(session_state(day, at="2026-12-24T10:30:00+08:00"), "open")
    _assert_allowed(session_state(day, at="2026-12-24T15:00:00+08:00"), "post_close")


def test_a12_closed_day_any_instant():
    day = _hk_day(trading_date="2026-01-01", day_kind="closed", sessions=())
    _assert_allowed(session_state(day, at="2026-01-01T03:00:00+08:00"), "closed_day")
    _assert_allowed(session_state(day, at="2026-01-01T12:30:00+08:00"), "closed_day")
    _assert_allowed(session_state(day, at="2026-01-01T22:00:00+08:00"), "closed_day")


# ---------------------------------------------------------------------------
# US DST transitions
# ---------------------------------------------------------------------------


def test_a12_us_dst_march_transition_changes_state():
    before = _us_day(trading_date="2026-03-06")
    after = _us_day(trading_date="2026-03-09")
    early = datetime(2026, 3, 6, 12, 0, tzinfo=ZoneInfo(_US_TZ)).utcoffset()
    late = datetime(2026, 3, 9, 12, 0, tzinfo=ZoneInfo(_US_TZ)).utcoffset()
    assert early != late
    v_before = session_state(before, at="2026-03-06T14:00:00+00:00")
    v_after = session_state(after, at="2026-03-09T14:00:00+00:00")
    _assert_allowed(v_before, "pre_open")
    _assert_allowed(v_after, "open")
    assert v_before.state != v_after.state


def test_a12_us_dst_november_transition_changes_state():
    before = _us_day(trading_date="2026-10-30")
    after = _us_day(trading_date="2026-11-02")
    early = datetime(2026, 10, 30, 12, 0, tzinfo=ZoneInfo(_US_TZ)).utcoffset()
    late = datetime(2026, 11, 2, 12, 0, tzinfo=ZoneInfo(_US_TZ)).utcoffset()
    assert early != late
    v_before = session_state(before, at="2026-10-30T13:45:00Z")
    v_after = session_state(after, at="2026-11-02T13:45:00Z")
    _assert_allowed(v_before, "open")
    _assert_allowed(v_after, "pre_open")
    assert v_before.state != v_after.state


# ---------------------------------------------------------------------------
# Halts
# ---------------------------------------------------------------------------


def test_a12_halt_during_open_is_halted():
    day = _hk_day(halts=(("2026-10-07T11:00:00+08:00", "2026-10-07T11:20:00+08:00"),))
    _assert_allowed(session_state(day, at="2026-10-07T10:50:00+08:00"), "open")
    _assert_allowed(session_state(day, at="2026-10-07T11:00:00+08:00"), "halted")
    _assert_allowed(session_state(day, at="2026-10-07T11:10:00+08:00"), "halted")
    _assert_allowed(session_state(day, at="2026-10-07T11:20:00+08:00"), "open")


def test_a12_halt_spanning_break_keeps_break():
    day = _hk_day(halts=(("2026-10-07T11:50:00+08:00", "2026-10-07T13:10:00+08:00"),))
    _assert_allowed(session_state(day, at="2026-10-07T11:55:00+08:00"), "halted")
    _assert_allowed(session_state(day, at="2026-10-07T12:30:00+08:00"), "break")
    _assert_allowed(session_state(day, at="2026-10-07T13:05:00+08:00"), "halted")
    _assert_allowed(session_state(day, at="2026-10-07T13:15:00+08:00"), "open")


def test_a12_halt_end_not_after_start_refused():
    day = _hk_day(halts=(("2026-10-07T11:20:00+08:00", "2026-10-07T11:00:00+08:00"),))
    _assert_refused(session_state(day, at=_AT_MORNING), "HALT_INVALID")


# ---------------------------------------------------------------------------
# Boundaries
# ---------------------------------------------------------------------------


def test_a12_boundary_session_bounds_half_open():
    day = _hk_day()
    _assert_allowed(session_state(day, at="2026-10-07T09:30:00+08:00"), "open")
    _assert_allowed(session_state(day, at="2026-10-07T12:00:00+08:00"), "break")
    _assert_allowed(session_state(day, at="2026-10-07T13:00:00+08:00"), "open")
    _assert_allowed(session_state(day, at="2026-10-07T16:00:00+08:00"), "post_close")


def test_a12_touching_sessions_no_break_gap():
    day = _hk_day(sessions=(("09:30", "12:00"), ("12:00", "16:00")))
    _assert_allowed(session_state(day, at="2026-10-07T11:59:00+08:00"), "open")
    _assert_allowed(session_state(day, at="2026-10-07T12:00:00+08:00"), "open")
    _assert_allowed(session_state(day, at="2026-10-07T15:00:00+08:00"), "open")


# ---------------------------------------------------------------------------
# One single-flip test per REASON
# ---------------------------------------------------------------------------


def test_a12_reason_calendar_missing():
    verdict = session_state(None, at=_AT_MORNING)
    _assert_refused(verdict, "CALENDAR_MISSING")
    assert verdict.reasons == ("CALENDAR_MISSING",)


def test_a12_reason_owner_ref_missing():
    _assert_refused(
        session_state(_hk_day(owner_ref=""), at=_AT_MORNING), "OWNER_REF_MISSING"
    )


def test_a12_reason_timezone_invalid():
    _assert_refused(
        session_state(_hk_day(timezone="Mars/Olympus_Mons"), at=_AT_MORNING),
        "TIMEZONE_INVALID",
    )


def test_a12_reason_date_invalid():
    _assert_refused(
        session_state(_hk_day(trading_date="2026-02-30"), at=_AT_MORNING),
        "DATE_INVALID",
    )


def test_a12_reason_day_kind_unknown():
    _assert_refused(
        session_state(_hk_day(day_kind="trading"), at=_AT_MORNING), "DAY_KIND_UNKNOWN"
    )


def test_a12_reason_session_time_invalid():
    day = _hk_day(sessions=(("09:30", "12:00"), ("13:00", "24:00")))
    _assert_refused(session_state(day, at=_AT_MORNING), "SESSION_TIME_INVALID")


def test_a12_reason_sessions_inconsistent():
    _assert_refused(
        session_state(_hk_day(day_kind="closed"), at=_AT_MORNING),
        "SESSIONS_INCONSISTENT",
    )


def test_a12_reason_halt_invalid():
    day = _hk_day(halts=(("2026-10-07T11:00:00", "2026-10-07T11:20:00+08:00"),))
    _assert_refused(session_state(day, at=_AT_MORNING), "HALT_INVALID")


def test_a12_reason_at_invalid():
    _assert_refused(
        session_state(_hk_day(), at="2026-10-07T10:00:00"), "AT_INVALID"
    )


def test_a12_reason_at_outside_trading_date():
    _assert_refused(
        session_state(_hk_day(), at="2026-10-08T09:30:00+08:00"),
        "AT_OUTSIDE_TRADING_DATE",
    )


# ---------------------------------------------------------------------------
# Extra session-consistency shapes
# ---------------------------------------------------------------------------


def test_a12_sessions_close_not_after_open():
    day = _hk_day(sessions=(("12:00", "12:00"), ("13:00", "16:00")))
    _assert_refused(session_state(day, at=_AT_MORNING), "SESSIONS_INCONSISTENT")


def test_a12_sessions_overlap_refused():
    day = _hk_day(sessions=(("09:30", "13:30"), ("13:00", "16:00")))
    _assert_refused(session_state(day, at=_AT_MORNING), "SESSIONS_INCONSISTENT")


def test_a12_sessions_out_of_order_refused():
    day = _hk_day(sessions=(("13:00", "16:00"), ("09:30", "12:00")))
    _assert_refused(session_state(day, at=_AT_MORNING), "SESSIONS_INCONSISTENT")


def test_a12_full_day_without_sessions_refused():
    _assert_refused(
        session_state(_hk_day(sessions=()), at=_AT_MORNING), "SESSIONS_INCONSISTENT"
    )


def test_a12_at_unparseable_or_non_string_refused():
    _assert_refused(session_state(_hk_day(), at="not-a-timestamp"), "AT_INVALID")
    _assert_refused(session_state(_hk_day(), at=None), "AT_INVALID")
    _assert_refused(session_state(_hk_day(), at="2026-10-07"), "AT_INVALID")


# ---------------------------------------------------------------------------
# De-dup and order
# ---------------------------------------------------------------------------


def test_a12_reasons_deduplicated_in_reasons_order():
    day = _hk_day(owner_ref="", timezone="Mars/Olympus_Mons", day_kind="whenever")
    verdict = session_state(day, at="2026-10-07T10:00:00")
    expected = (
        "OWNER_REF_MISSING",
        "TIMEZONE_INVALID",
        "DAY_KIND_UNKNOWN",
        "AT_INVALID",
    )
    assert verdict.reasons == expected
    assert len(verdict.reasons) == len(set(verdict.reasons))
    _assert_refused(verdict, *expected)


# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def test_a12_authority_refuses_nonfalse_values():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority({"rank_authority": False})
    for bad in (True, 0, None, ""):
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({"rank_authority": bad})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"trade_authority": 1})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority("not-a-mapping")


def test_a12_authority_flags_frozen_and_identity():
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    verdict = session_state(_hk_day(), at=_AT_MORNING)
    assert verdict.authority_flags is AUTHORITY_FLAGS


def test_a12_constants_contract():
    assert DAY_KINDS == ("full", "half", "closed")
    assert STATES == (
        "pre_open",
        "open",
        "break",
        "post_close",
        "closed_day",
        "halted",
    )
    assert REASONS == (
        "CALENDAR_MISSING",
        "OWNER_REF_MISSING",
        "TIMEZONE_INVALID",
        "DATE_INVALID",
        "DAY_KIND_UNKNOWN",
        "SESSION_TIME_INVALID",
        "SESSIONS_INCONSISTENT",
        "HALT_INVALID",
        "AT_INVALID",
        "AT_OUTSIDE_TRADING_DATE",
    )
    assert len(REASONS) == len(set(REASONS))
    with pytest.raises(ValueError):
        SessionStateVerdict(allowed=True, reasons=(), state="not_a_state")
    forced = SessionStateVerdict(allowed=True, reasons=("DATE_INVALID",), state="open")
    assert forced.allowed is False
    assert forced.state is None
    assert forced.reasons == ("DATE_INVALID",)


# ---------------------------------------------------------------------------
# Static scans
# ---------------------------------------------------------------------------


def test_a12_static_module_source_scan():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    assert re.search(r"\b\d{4,5}\.HK\b", source) is None
    for ticker in (
        "BABA",
        "TCEHY",
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "AMZN",
        "META",
        "TSLA",
    ):
        assert ticker not in source, ticker
    for banned in ("datetime.now", "utcnow", "date.today", "time.time", "open("):
        assert banned not in source, banned


def test_a12_static_no_wallclock_or_zone_literals():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert re.search(r"\b\d{1,2}:\d{2}\b", source) is None
    for zone_literal in ("Asia/", "America/", "Europe/", "UTC"):
        assert zone_literal not in source, zone_literal


# ---------------------------------------------------------------------------
# Adversarial id / code cases (G5, common T6)
# ---------------------------------------------------------------------------


def test_a12_adversarial_exact_string_no_normalisation():
    # Codes are compared as exact strings; nothing is case-folded, stripped,
    # or normalised. Zone and day-kind variants that a folder would silently
    # accept each refuse.
    trailing = session_state(_hk_day(timezone=_HK_TZ + " "), at=_AT_MORNING)
    _assert_refused(trailing, "TIMEZONE_INVALID")
    folded = session_state(_hk_day(timezone=_HK_TZ.casefold()), at=_AT_MORNING)
    _assert_refused(folded, "TIMEZONE_INVALID")
    lookalike = session_state(_hk_day(timezone="Americа/New_York"), at=_AT_MORNING)
    _assert_refused(lookalike, "TIMEZONE_INVALID")
    _assert_refused(
        session_state(_hk_day(day_kind="Full"), at=_AT_MORNING), "DAY_KIND_UNKNOWN"
    )
    _assert_refused(
        session_state(_hk_day(day_kind="full "), at=_AT_MORNING), "DAY_KIND_UNKNOWN"
    )
    _assert_refused(
        session_state(_hk_day(day_kind="hаlf"), at=_AT_MORNING), "DAY_KIND_UNKNOWN"
    )


def test_a12_adversarial_owner_ref_opaque():
    # Common T6 id-comparison does not apply to calendar_id/owner_ref here:
    # the guard never compares ids against a second side (there is no join),
    # so a trailing-space, case-variant, or Cyrillic look-alike owner_ref is
    # simply a distinct non-blank opaque string and is accepted. Ids are
    # never folded, stripped, or normalised; only blank/None refuse.
    _assert_allowed(
        session_state(_hk_day(owner_ref="SYN-CAL-OWNER-HK-1 "), at=_AT_MORNING),
        "open",
    )
    _assert_allowed(
        session_state(_hk_day(owner_ref="syn-cal-owner-hk-1"), at=_AT_MORNING),
        "open",
    )
    _assert_allowed(
        session_state(_hk_day(owner_ref="SYN-CAL-OWNER-HK-а1"), at=_AT_MORNING),
        "open",
    )
    _assert_refused(
        session_state(_hk_day(owner_ref=""), at=_AT_MORNING), "OWNER_REF_MISSING"
    )
    _assert_refused(
        session_state(_hk_day(owner_ref=None), at=_AT_MORNING), "OWNER_REF_MISSING"
    )


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_a12_positive_us_full_day_control():
    day = _us_day(trading_date="2026-06-10")
    _assert_allowed(session_state(day, at="2026-06-10T13:00:00Z"), "pre_open")
    _assert_allowed(session_state(day, at="2026-06-10T15:00:00Z"), "open")
    _assert_allowed(session_state(day, at="2026-06-10T21:00:00Z"), "post_close")
