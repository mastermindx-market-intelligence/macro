from datetime import date, time
import pytest
from lib.exchange_holidays import announced_holidays, calendar_coverage, holiday_name, early_close

EXPECTED={2026:"01-01 01-02 01-12 02-11 02-23 03-20 04-29 05-04 05-05 05-06 07-20 08-11 09-21 09-22 09-23 10-12 11-03 11-23 12-31",2027:"01-01 01-11 02-11 02-23 03-22 04-29 05-03 05-04 05-05 07-19 08-11 09-20 09-23 10-11 11-03 11-23 12-31"}
@pytest.mark.parametrize("year",[2026,2027])
def test_full_official_weekday_slate_only(year):
    actual=announced_holidays("JP",year)
    assert set(actual)=={date.fromisoformat(f"{year}-{md}") for md in EXPECTED[year].split()}
    assert all(day.weekday()<5 for day in actual)
    assert all(holiday_name("JP",day,"en") and holiday_name("JP",day,"zh") for day in actual)
    assert all(early_close("JP",day) is None for day in actual)
@pytest.mark.parametrize("year",[2025,2028,2030])
def test_no_annual_extrapolation(year):
    assert announced_holidays("JP",year) is None
    assert year not in calendar_coverage("JP")["verified_years"]
def test_independent_verification_date_and_immutable_provenance():
    c=calendar_coverage("JP")
    assert c["verified_years"]==frozenset({2026,2027})
    assert c["verified_on"]==date(2026,10,8)
    assert c["source_urls"]==("https://www.jpx.co.jp/english/corporate/about-jpx/calendar/",)
    assert not c["partial_years"] and not c["partial_source_urls"]
    with pytest.raises(TypeError): c["verified_on"]=date(2000,1,1)
    with pytest.raises(TypeError): c["year_source_urls"][2025]=()
    with pytest.raises(TypeError): announced_holidays("JP",2026)[date(2026,1,5)]="invented"
def test_existing_venues_keep_original_dates_sources_and_half_closes():
    for market in ["CN","HK","US","CA"]:
        assert calendar_coverage(market)["verified_on"]==date(2026,10,7)
    assert holiday_name("CN",date(2026,10,7),"zh")=="国庆节"
    assert early_close("HK",date(2026,12,24))==time(12,10)
    assert early_close("US",date(2026,11,27))==time(13)
    assert announced_holidays("CA",2027) is None
    assert holiday_name("CA",date(2027,1,1))=="New Year's Day"
def test_japan_unannounced_dates_are_not_inferred_and_bad_language_rejected():
    assert holiday_name("JP",date(2026,5,3)) is None
    assert holiday_name("JP",date(2027,3,21)) is None
    assert holiday_name("JP",date(2026,9,22))=="Holiday"
    with pytest.raises(ValueError):holiday_name("JP",date(2026,1,1),"xx")
    with pytest.raises(KeyError):announced_holidays("ZZ",2026)
