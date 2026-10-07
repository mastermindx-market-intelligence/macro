"""Official exchange notices and session-completion regressions; synthetic, no I/O."""
from datetime import date, datetime, time, timedelta, timezone

import pytest

from lib import cn_calendar as cn, hk_calendar as hk
from lib import us_cash_calendar as us, tsx_calendar as ca

CALENDARS = {"CN": cn, "HK": hk, "US": us, "CA": ca}
SLATES = {
    ("CN", 2026): "01-01 01-02 02-16 02-17 02-18 02-19 02-20 02-23 04-06 05-01 05-04 05-05 06-19 09-25 10-01 10-02 10-05 10-06 10-07",
    ("HK", 2026): "01-01 02-17 02-18 02-19 04-03 04-06 04-07 05-01 05-25 06-19 07-01 10-01 10-19 12-25",
    ("HK", 2027): "01-01 02-08 02-09 03-26 03-29 04-05 05-13 06-09 07-01 09-16 10-01 10-08 12-27",
    ("US", 2026): "01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25",
    ("US", 2027): "01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24",
    ("CA", 2026): "01-01 02-16 04-03 05-18 07-01 08-03 09-07 10-12 12-25 12-28",
}
HALVES = {
    ("HK", 2026): ("02-16 12-24 12-31", time(12, 10), time(13, 30)),
    ("HK", 2027): ("02-05 12-24 12-31", time(12, 10), time(13, 30)),
    ("US", 2026): ("11-27 12-24", time(13), time(14)),
    ("US", 2027): ("11-26", time(13), time(14)),
    ("CA", 2026): ("12-24", time(13), time(14)),
}


def dates(year, text):
    return {date.fromisoformat(f"{year}-{md}") for md in text.split()}


@pytest.mark.parametrize("market,year", SLATES)
def test_exact_announced_weekday_slates_replace_approximations(market, year):
    from lib.exchange_holidays import announced_holidays

    expected = dates(year, SLATES[market, year])
    assert set(announced_holidays(market, year)) == expected
    assert CALENDARS[market].holidays(year) == frozenset(expected)
    assert all(not CALENDARS[market].is_session(d) for d in expected)


@pytest.mark.parametrize("market,text", [
    ("HK", "2026-02-16 2026-09-25 2026-09-28 2026-12-28 2027-02-05 2027-05-03 2027-12-28"),
    ("US", "2026-07-02 2027-12-31"),
    ("CA", "2026-01-19 2026-04-06 2026-05-25 2026-06-19 2026-09-30 2026-11-11 2026-11-26"),
])
def test_real_open_dates_are_not_deleted(market, text):
    expected = {date.fromisoformat(s) for s in text.split()}
    for d in expected:
        assert CALENDARS[market].is_session(d), d


@pytest.mark.parametrize("md", ["01-04", "02-14", "02-28", "05-09", "09-20", "10-10"])
def test_cn_government_makeup_weekends_remain_exchange_closed(md):
    assert not cn.is_session(date.fromisoformat(f"2026-{md}"))


def test_cn_long_closure_completion_and_spring_festival_tail():
    for day in range(1, 8):
        assert cn.expected_last_session(datetime(2026, 10, day, 22, tzinfo=cn.CST)) == date(2026, 9, 30)
    assert cn.expected_last_session(datetime(2026, 10, 8, 16, 59, tzinfo=cn.CST)) == date(2026, 9, 30)
    assert cn.expected_last_session(datetime(2026, 10, 8, 17, tzinfo=cn.CST)) == date(2026, 10, 8)
    assert cn.expected_last_session(datetime(2026, 2, 23, 22, tzinfo=cn.CST)) == date(2026, 2, 13)
    assert cn.last_session_on_or_before(date(2026, 2, 23)) == date(2026, 2, 13)


@pytest.mark.parametrize("market,year", HALVES)
def test_exact_half_day_dates_and_settle_boundaries(market, year):
    from lib.exchange_holidays import early_close

    text, close, settled = HALVES[market, year]
    half_dates = dates(year, text)
    cal = CALENDARS[market]
    zone = {"HK": hk.HKT, "US": us.ET, "CA": ca.TORONTO}[market]
    d = date(year, 1, 1)
    while d.year == year:
        assert early_close(market, d) == (close if d in half_dates else None)
        d += timedelta(days=1)
    for d in half_dates:
        assert cal.is_session(d)
        at = datetime.combine(d, settled, zone)
        previous = cal.last_session_on_or_before(d - timedelta(days=1))
        assert cal.expected_last_session(at - timedelta(microseconds=1)) == previous
        assert cal.expected_last_session(at) == d
        assert cal.expected_last_session(at.astimezone(timezone.utc)) == d
        assert cal.expected_last_session(at.astimezone(timezone.utc).replace(tzinfo=None)) == d


@pytest.mark.parametrize("market,zone,d", [
    ("CN", cn.CST, date(2026, 10, 8)),
    ("HK", hk.HKT, date(2026, 9, 25)),
    ("US", us.ET, date(2026, 7, 2)),
    ("CA", ca.TORONTO, date(2026, 9, 30)),
])
def test_regular_day_buffers_unchanged_and_local_date_wins(market, zone, d):
    from lib.exchange_holidays import early_close

    cal = CALENDARS[market]
    assert early_close(market, d) is None
    settled = time(17, 30) if market == "HK" else time(17)
    at = datetime.combine(d, settled, zone)
    assert cal.expected_last_session(at - timedelta(microseconds=1)) == cal.last_session_on_or_before(d - timedelta(days=1))
    assert cal.expected_last_session(at) == d
    # Asian next local morning and American next UTC day keep the prior settled bar.
    later = at + timedelta(hours=8)
    assert cal.expected_last_session(later.astimezone(timezone.utc)) == d


@pytest.mark.parametrize("market,years", [
    ("CN", {2026}), ("HK", {2026, 2027}), ("US", {2026, 2027}), ("CA", {2026}),
])
def test_coverage_never_claims_unknown_year_verification(market, years):
    from lib.exchange_holidays import announced_holidays, calendar_coverage, early_close

    metadata = calendar_coverage(market)
    assert metadata["verified_years"] == frozenset(years)
    assert metadata["verified_on"] == date(2026, 10, 7)
    assert metadata["source_urls"]
    assert set(metadata["year_source_urls"]) == years
    assert announced_holidays(market, 2031) is None
    assert early_close(market, date(2031, 12, 24)) is None
    assert 2031 not in metadata["verified_years"]


def test_partial_ca_year_and_nyse_only_2027_provenance():
    from lib.exchange_holidays import announced_holidays, calendar_coverage, holiday_name

    assert announced_holidays("CA", 2027) is None
    assert calendar_coverage("CA")["partial_years"] == frozenset({2027})
    assert holiday_name("CA", date(2027, 1, 1)) == "New Year's Day"
    assert calendar_coverage("US")["year_source_urls"][2027] == ("https://www.nyse.com/trade/hours-calendars",)


def test_announcements_and_metadata_are_immutable_and_names_are_bilingual():
    from lib.exchange_holidays import announced_holidays, calendar_coverage, holiday_name

    holidays = announced_holidays("CN", 2026)
    with pytest.raises(TypeError):
        holidays[date(2026, 10, 8)] = "invented holiday"
    with pytest.raises(TypeError):
        calendar_coverage("CN")["verified_years"] = frozenset({2031})
    with pytest.raises(TypeError):
        calendar_coverage("CN")["year_source_urls"][2031] = ()
    assert holiday_name("CN", date(2026, 10, 7)) == "National Day"
    assert holiday_name("CN", date(2026, 10, 7), "zh") == "国庆节"
    assert holiday_name("HK", date(2026, 9, 25)) is None
    assert holiday_name("US", date(2026, 11, 27)) == "Day after Thanksgiving (early close)"


def test_historical_fallback_and_legacy_api_semantics():
    assert cn.is_session(date(2019, 2, 11))
    assert cn.is_session(date(2024, 2, 15))
    assert cn.is_session(date(2027, 5, 3))
    assert not hk.is_session(date(2017, 8, 23))
    assert not us.is_session(date(2025, 1, 9))
    assert us.is_session(date(2021, 12, 31))
    assert not ca.is_session(date(2021, 12, 28))
    start, end = date(2026, 8, 3), date(2026, 8, 4)
    assert us.sessions_between(start, end) == [start, end]
    for cal in (cn, hk, ca):
        assert cal.sessions_between(start, end) == 1
    assert cn.session_n_back(date(2026, 10, 8), 1) == date(2026, 9, 30)



def test_calendar_lookups_require_no_filesystem_network_or_subprocess(monkeypatch):
    import builtins
    import io
    import socket
    import subprocess
    from lib.exchange_holidays import announced_holidays, calendar_coverage, early_close, holiday_name

    def forbidden(*args, **kwargs):
        raise AssertionError("calendar lookup attempted external I/O")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(io, "open", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(subprocess, "run", forbidden)
        for (market, year), slate in SLATES.items():
            calendar_coverage(market)
            assert set(announced_holidays(market, year)) == dates(year, slate)
            for day in dates(year, slate):
                assert holiday_name(market, day)
                assert holiday_name(market, day, "zh")
                assert early_close(market, day) is None
                assert not CALENDARS[market].is_session(day)
            CALENDARS[market].expected_last_session(datetime(year, 8, 18, 23, tzinfo=timezone.utc))
