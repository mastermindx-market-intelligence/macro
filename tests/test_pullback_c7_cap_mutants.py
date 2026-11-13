"""Killers for the C7-cap mutants that survive the served-page suite (lane MT8).

Each test pins one behavior of scripts/verify_risk_radar_pullback_served.py's
400-day cap that the served contract left unpinned: the default --now, the
UTC-offset arithmetic, the exact refusal details, and the exact 400-day
boundary. Synthetic stamps only; no network, no market data.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.verify_risk_radar_pullback_served import (
    MAX_AHEAD,
    _check_c7,
    _parse_now,
    _parse_valid_until,
)

NOW = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
VU = "2026-10-01T09:00:00+00:00"
CAP_DETAIL = "valid_until is more than 400 days ahead; the page script expires it"


def test_offset_is_applied_not_dropped():
    assert _parse_valid_until("2026-10-01T09:00:00-04:00") == datetime(
        2026, 10, 1, 13, 0, tzinfo=timezone.utc)


def test_offset_is_applied_east():
    assert _parse_valid_until("2026-10-01T09:00:00+05:30") == datetime(
        2026, 10, 1, 3, 30, tzinfo=timezone.utc)


def test_default_now_is_aware_utc():
    now = _parse_now(None)
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_default_now_enforces_the_cap_against_the_real_clock():
    ok, detail = _check_c7("underway", "2030-01-01T00:00:00+00:00", True, _parse_now(None))
    assert ok is False
    assert detail == CAP_DETAIL


def test_parse_now_strips_surrounding_space():
    assert _parse_now(" 2026-10-01T08:00:00+00:00 ") == NOW


def test_phase_gate_detail_is_exact():
    assert _check_c7("monitoring", VU, True, NOW) == (
        False, "phase monitoring is not underway|stabilizing|recovering")


def test_phase_gate_missing_detail_is_exact():
    assert _check_c7(None, None, True, NOW) == (
        False, "phase <missing> is not underway|stabilizing|recovering")


def test_expiry_boundary_is_inclusive():
    assert _check_c7("underway", "2026-10-01T08:00:00+00:00", True, NOW) == (
        False, "expired: valid_until <= now")


def test_cap_boundary_exactly_400_days_is_current():
    vu = (NOW + MAX_AHEAD).isoformat()
    assert _check_c7("underway", vu, True, NOW) == (True, "phase underway is active")


def test_cap_boundary_one_second_past_400_days_is_refused():
    # The page script reads whole seconds only, so one second is the least
    # step past the cap a served stamp can take.
    vu = (NOW + MAX_AHEAD + timedelta(seconds=1)).isoformat()
    ok, detail = _check_c7("underway", vu, True, NOW)
    assert ok is False
    assert detail == CAP_DETAIL


def test_require_active_message_is_pinned():
    assert _check_c7("underway", VU, False, NOW) == (True, "require-active not set")


def test_unparseable_valid_until_detail_is_pinned():
    assert _check_c7("underway", "not-a-stamp", True, NOW) == (
        False, "valid_until missing or unparseable")


def test_none_valid_until_is_a_refusal_not_a_crash():
    assert _check_c7("underway", None, True, NOW) == (
        False, "valid_until missing or unparseable")


def test_empty_valid_until_detail_is_pinned():
    assert _check_c7("underway", "", True, NOW) == (
        False, "valid_until missing or unparseable")
