"""S2 clock law (IL §1 s(c), E4): session placement on both clocks.

Pins: pre-open -> same session; in-session, HK midday break and after-close ->
next session; DISCLOSURE_DATE -> first session strictly after the date;
EVENT_DATE is excluded upstream (never an anchor); HKT->UTC conversion; and
the packet's 05:30 ET case (news_id 12157537: 2026-05-13 17:30 HKT =
09:30Z = 05:30 ET -> s_US = 2026-05-13, s_HK = 2026-05-14).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from s2_clocklaw import (first_session_after,  # noqa: E402
                         first_session_after_disclosure_date, session_part,
                         to_utc)
from s2_selection import t_avail_for_event_row  # noqa: E402

HK = "Asia/Hong_Kong"


def _utc(y, mo, d, h, mi):
    return dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc)


def test_hkt_to_utc_conversion() -> None:
    t = to_utc(dt.datetime(2026, 5, 13, 17, 30), HK)
    assert t.utcoffset() == dt.timedelta(0)
    assert (t.hour, t.minute) == (9, 30) and t.day == 13


def test_preopen_maps_to_same_session_us() -> None:
    # 05:30 ET on a session day: strictly before the 09:30 regular open
    assert first_session_after(_utc(2026, 5, 13, 9, 30), "US") == dt.date(2026, 5, 13)


def test_packet_anchor_0530_et_case() -> None:
    t_avail, quality = t_avail_for_event_row(dt.datetime(2026, 5, 13, 17, 30))
    assert quality == "PUBLISHER_STATED"
    assert t_avail == _utc(2026, 5, 13, 9, 30)
    assert t_avail.astimezone(dt.timezone(dt.timedelta(hours = -4))).hour == 5
    assert first_session_after(t_avail, "US") == dt.date(2026, 5, 13)
    assert first_session_after(t_avail, "HK") == dt.date(2026, 5, 14)


def test_in_session_and_after_close_map_to_next_session_us() -> None:
    # 10:00 ET in-session on 2026-05-13 -> next NYSE session
    assert first_session_after(_utc(2026, 5, 13, 14, 0), "US") == dt.date(2026, 5, 14)
    # 20:00 ET after the close -> next session
    assert first_session_after(_utc(2026, 5, 14, 0, 0), "US") == dt.date(2026, 5, 14)


def test_exactly_at_open_is_not_strictly_before() -> None:
    # 09:30:00 ET exactly: the open is not strictly after t_avail -> next session
    assert first_session_after(_utc(2026, 5, 13, 13, 30), "US") == dt.date(2026, 5, 14)


def test_hk_midday_break_maps_to_next_session() -> None:
    # 12:30 HKT midday break on a session day -> next HK session
    t = to_utc(dt.datetime(2026, 5, 13, 12, 30), HK)
    assert session_part(t, "HK") == "midday_break"
    assert first_session_after(t, "HK") == dt.date(2026, 5, 14)


def test_hk_after_close_maps_to_next_session() -> None:
    # 16:31 HKT after the 16:00 close (news_id 12280990)
    t = to_utc(dt.datetime(2026, 8, 12, 16, 31), HK)
    assert session_part(t, "HK") == "after_close"
    assert first_session_after(t, "HK") == dt.date(2026, 8, 13)
    # same instant is pre-open in New York (04:31 ET) -> same US session
    assert session_part(t, "US") == "pre_open"
    assert first_session_after(t, "US") == dt.date(2026, 8, 12)


def test_weekend_release_maps_to_next_week_session() -> None:
    # 2026-08-23 is a Sunday; 18:06 HKT -> s_US = Monday 2026-08-24
    t = to_utc(dt.datetime(2026, 8, 23, 18, 6), HK)
    assert first_session_after(t, "US") == dt.date(2026, 8, 24)
    assert first_session_after(t, "HK") == dt.date(2026, 8, 24)


def test_disclosure_date_maps_strictly_after_on_both_clocks() -> None:
    d = dt.date(2026, 5, 13)
    assert first_session_after_disclosure_date(d, "US") == dt.date(2026, 5, 14)
    assert first_session_after_disclosure_date(d, "HK") == dt.date(2026, 5, 14)
    # a Friday disclosure lands on the next session, never the weekend
    assert first_session_after_disclosure_date(dt.date(2026, 5, 15), "US") == dt.date(2026, 5, 18)


def test_event_date_quality_is_inadmissible() -> None:
    from s2_collapse import ADMISSIBLE_QUALITIES
    assert "EVENT_DATE" not in ADMISSIBLE_QUALITIES
    assert "SNAPSHOT_DATE" not in ADMISSIBLE_QUALITIES
    assert "CORRUPTED" not in ADMISSIBLE_QUALITIES
    assert "PUBLISHER_STATED" in ADMISSIBLE_QUALITIES
    assert "DISCLOSURE_DATE" in ADMISSIBLE_QUALITIES
    assert "CRAWL_BOUNDED" in ADMISSIBLE_QUALITIES
