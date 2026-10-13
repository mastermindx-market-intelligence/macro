"""history_gap_count counts missing sessions inside the assessed window.

Weekday series reuse the replay suite's builders. The US and China cases go
through each market's adapter and that market's own session calendar.
Closes are synthetic levels around 100. Nothing here is a forecast.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

import lib.pullback_observation as observation
from lib import cn_calendar, nyse_calendar
from lib.cn_pullback_observation import LicensedCloses as CnCloses
from lib.cn_pullback_observation import snapshot as cn_snapshot
from lib.pullback_observation import _next_observation, observe
from lib.us_pullback_observation import LicensedCloses as UsCloses
from lib.us_pullback_observation import snapshot as us_snapshot
from tests.test_pullback_depth_copy_states import soup_of
from tests.test_pullback_scenario_replay import session, weekday_closes


def _read(rows, is_session=session):
    read = observe(
        rows,
        expected_session=date.fromisoformat(rows[-1][0]),
        is_session=is_session,
    )
    assert read["available"] is True and read["quality"] == "current", read.get("quality")
    assert type(read["history_gap_count"]) is int
    return read


def _sessions_between(earlier, later, is_session):
    """ISO sessions strictly between two dates. Bounded by the hole itself."""
    found = []
    probe = earlier + timedelta(days=1)
    span = (later - earlier).days
    for _ in range(max(span - 1, 0)):
        if is_session(probe):
            found.append(probe.isoformat())
        probe += timedelta(days=1)
    return found


def _drop(rows, indexes):
    omitted = [rows[i][0] for i in indexes]
    kept = [row for row in rows if row[0] not in set(omitted)]
    return kept, omitted


def _gap_lines(read):
    node = soup_of(read, "us").select_one('[data-signal="gaps"]')
    assert node is not None
    return node.select_one(".l-en").get_text(), node.select_one(".l-zh").get_text()


def _three_missing_rows():
    """Three consecutive weekday sessions omitted inside a short decline."""
    full = weekday_closes([100.0] * 70 + [98.0, 97.0, 96.0, 95.0, 95.5, 96.0])
    return _drop(full, (71, 72, 73))


def test_t1_three_consecutive_missing_sessions_count_three():
    rows, omitted = _three_missing_rows()
    kept = [row[0] for row in rows]
    before = date.fromisoformat(max(day for day in kept if day < omitted[0]))
    after = date.fromisoformat(min(day for day in kept if day > omitted[-1]))
    assert _sessions_between(before, after, session) == omitted
    read = _read(rows)
    assert read["history_gap_count"] == 3
    path = read["price_path"]["dates"]
    assert path[0] < omitted[0] and omitted[-1] < path[-1]
    en, zh = _gap_lines(read)
    assert "3 sessions missing" in en
    assert en == "3 sessions missing from the closes used for this assessment"
    assert "缺少3个交易日" in zh
    assert zh == "本次评估所用收盘价缺少3个交易日"


def test_t2_two_separate_one_session_holes_count_two():
    full = weekday_closes([100.0] * 90)
    rows, omitted = _drop(full, (40, 70))
    assert date.fromisoformat(omitted[1]) - date.fromisoformat(omitted[0]) > timedelta(days=2)
    read = _read(rows)
    assert read["history_gap_count"] == 2
    path0 = read["price_path"]["dates"][0]
    assert all(day > path0 for day in omitted)
    for day in omitted:
        kept = [row[0] for row in rows]
        before = date.fromisoformat(max(stamp for stamp in kept if stamp < day))
        after = date.fromisoformat(min(stamp for stamp in kept if stamp > day))
        assert _sessions_between(before, after, session) == [day]


def test_t3_a_hole_entirely_before_the_window_counts_zero():
    full = weekday_closes([100.0] * 120)
    rows, omitted = _drop(full, (2,))
    read = _read(rows)
    assert read["history_gap_count"] == 0
    first = date.fromisoformat(read["price_path"]["dates"][0])
    assert date.fromisoformat(omitted[0]) < first - timedelta(days=40)
    assert soup_of(read, "us").select_one('[data-signal="gaps"]') is None


def test_t4_hole_on_the_window_edge_is_counted():
    # 120 flat closes. After one omission the trailing window's first drawn
    # close is kept index 56, so original index 56 is the session between
    # the close just before the window and that first drawn close.
    full = weekday_closes([100.0] * 120)
    rows, omitted = _drop(full, (56,))
    read = _read(rows)
    first = read["price_path"]["dates"][0]
    prior = rows[next(i for i, row in enumerate(rows) if row[0] == first) - 1][0]
    assert prior < omitted[0] < first
    assert _sessions_between(
        date.fromisoformat(prior), date.fromisoformat(first), session,
    ) == omitted
    assert read["history_gap_count"] == 1


def test_t5_no_holes_publish_zero_and_omit_the_line():
    read = _read(weekday_closes([100.0] * 70 + [96.0, 95.0]))
    assert read["history_gap_count"] == 0
    assert soup_of(read, "us").select_one('[data-signal="gaps"]') is None


def test_t6_one_missing_session_is_singular():
    full = weekday_closes([100.0] * 70 + [96.0, 95.0, 94.0])
    rows, omitted = _drop(full, (-2,))
    read = _read(rows)
    assert read["history_gap_count"] == 1
    path = read["price_path"]["dates"]
    assert path[0] < omitted[0] < path[-1]
    en, zh = _gap_lines(read)
    assert "1 session missing" in en
    assert "sessions missing" not in en
    assert en == "1 session missing from the closes used for this assessment"
    assert "缺少1个交易日" in zh
    assert zh == "本次评估所用收盘价缺少1个交易日"


def _sessions_ending(is_session, last, n):
    days = []
    day = last
    for _ in range(n * 4 + 40):
        if is_session(day):
            days.append(day)
        if len(days) == n:
            break
        day -= timedelta(days=1)
    assert len(days) == n and days[0] == last
    days.reverse()
    return [(stamp.isoformat(), 100.0) for stamp in days]


def _adapter_read(snapshot, closes_type, now, rows):
    out = snapshot(
        now=now,
        read=lambda _expected: closes_type(rows=list(rows)),
        observer=observe,
    )
    assert out["available"] is True and out["quality"] == "current", out.get("quality")
    assert type(out["history_gap_count"]) is int
    return out


def _holiday_case(snapshot, closes_type, *, is_session, holiday, omitted, last, now, market):
    assert is_session(last) and is_session(omitted)
    assert not is_session(holiday)
    assert snapshot is us_snapshot or snapshot is cn_snapshot
    rows = _sessions_ending(is_session, last, 80)
    assert holiday.isoformat() not in {row[0] for row in rows}
    assert omitted.isoformat() in {row[0] for row in rows}
    full = _adapter_read(snapshot, closes_type, now, rows)
    assert full["market"] == market
    drawn = [date.fromisoformat(day) for day in full["price_path"]["dates"]]
    assert any(earlier < holiday < later for earlier, later in zip(drawn, drawn[1:]))
    assert full["history_gap_count"] == 0
    kept = [row for row in rows if row[0] != omitted.isoformat()]
    earlier = max(date.fromisoformat(row[0]) for row in kept if row[0] < holiday.isoformat())
    later = min(date.fromisoformat(row[0]) for row in kept if row[0] > holiday.isoformat())
    assert holiday not in {
        date.fromisoformat(day) for day in _sessions_between(earlier, later, is_session)
    }
    assert _sessions_between(earlier, later, is_session) == [omitted.isoformat()]
    gapped = _adapter_read(snapshot, closes_type, now, kept)
    assert gapped["market"] == market
    assert gapped["history_gap_count"] == 1


def test_t7_us_holiday_is_not_a_missing_session():
    # Independence Day 2025 is a Friday NYSE closure. The Thursday before it
    # is a real session; only that Thursday may count.
    last = date(2025, 7, 11)
    now = datetime(2025, 7, 11, 22, 0, tzinfo=timezone.utc)
    assert nyse_calendar.expected_last_session(now) == last
    _holiday_case(
        us_snapshot, UsCloses,
        is_session=nyse_calendar.is_session,
        holiday=date(2025, 7, 4), omitted=date(2025, 7, 3),
        last=last, now=now, market="us",
    )


def test_t7_cn_holiday_is_not_a_missing_session():
    # Qingming 2025-04-04 is a Friday SSE/SZSE closure. The Thursday before
    # it is a real session; only that Thursday may count.
    last = date(2025, 4, 11)
    now = datetime(2025, 4, 11, 9, 30, tzinfo=timezone.utc)
    assert cn_calendar.expected_last_session(now) == last
    _holiday_case(
        cn_snapshot, CnCloses,
        is_session=cn_calendar.is_session,
        holiday=date(2025, 4, 4), omitted=date(2025, 4, 3),
        last=last, now=now, market="cn",
    )


def test_t8_break_counter_fails_the_three_session_hole(monkeypatch):
    def break_count(previous, current, is_session):
        # The retired counter: one per break, not one per missing session.
        return 0 if _next_observation(previous, current, is_session) else 1

    monkeypatch.setattr(observation, "_missing_expected", break_count)
    rows, _omitted = _three_missing_rows()
    read = _read(rows)
    with pytest.raises(AssertionError):
        assert read["history_gap_count"] == 3
    assert read["history_gap_count"] == 1
