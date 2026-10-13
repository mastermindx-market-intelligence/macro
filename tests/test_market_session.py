"""Exchange closure behavior: real notices, retained session dates, and asset scope."""
from datetime import date, datetime, timezone

import pytest


def clock(value):
    return datetime.fromisoformat(value)


@pytest.mark.parametrize("market,instant,state,expected,next_open", [
    ("cn", "2026-10-07T03:00:00+00:00", "holiday", "2026-09-30", "2026-10-08T09:30:00+08:00"),
    ("hk", "2026-10-07T03:00:00+00:00", "open", "2026-10-06", "2026-10-07T13:00:00+08:00"),
    ("connect", "2026-10-07T03:00:00+00:00", "holiday", "2026-09-30", "2026-10-08T09:30:00+08:00"),
    ("us", "2026-07-03T15:00:00+00:00", "holiday", "2026-07-02", "2026-07-06T09:30:00-04:00"),
    ("ca", "2026-12-28T16:00:00+00:00", "holiday", "2026-12-24", "2026-12-29T09:30:00-05:00"),
])
def test_status_separates_market_closure_from_completed_data(market, instant, state, expected, next_open):
    from lib.market_session import session_status
    result = session_status(market, clock(instant))
    assert result["state"] == state
    assert result["open"] is (state == "open")
    assert result["expected_session"] == expected
    assert result["next_open"] == next_open
    assert result["calendar_verified"] is True
    assert result["data_frozen"] is (state == "holiday")
    assert clock(result["valid_until"]) > clock(instant)


def test_national_day_holds_expected_data_then_releases_on_first_settled_session():
    from lib.market_session import session_freshness
    held = session_freshness("CN", date(2026, 9, 30), clock("2026-10-07T10:00:00+00:00"))
    assert (held["state"], held["lag_sessions"], held["expected_closure"]) == ("current", 0, True)
    assert held["observed_session"] == "2026-09-30"
    resumed = session_freshness("CN", "2026-09-30", clock("2026-10-08T09:00:00+00:00"))
    assert (resumed["state"], resumed["lag_sessions"], resumed["expected_closure"]) == ("late", 1, False)


def test_a_preholiday_outage_stays_late_during_closure():
    from lib.market_session import session_freshness
    result = session_freshness("CN", "2026-09-29", clock("2026-10-07T10:00:00+00:00"))
    assert result["state"] == "late"
    assert result["lag_sessions"] == 1
    assert result["lag_calendar_days"] == 1
    assert result["expected_closure"] is True


@pytest.mark.parametrize("observed,state", [(None, "missing"), ("2026-10-01", "invalid"),
                                           ("2026-10-08", "invalid"), ("not-a-date", "invalid")])
def test_missing_non_session_and_future_data_are_never_excused(observed, state):
    from lib.market_session import session_freshness
    assert session_freshness("CN", observed, clock("2026-10-07T03:00:00+00:00"))["state"] == state


def test_valid_developing_row_does_not_advance_expected_completed_session():
    from lib.market_session import session_freshness
    result = session_freshness("CN", "2026-10-08", clock("2026-10-08T02:00:00+00:00"))
    assert result["state"] == "current"
    assert result["expected_session"] == "2026-09-30"
    assert result["developing"] is True


@pytest.mark.parametrize("market,instant,state,expected", [
    ("HK", "2026-02-16T04:09:00+00:00", "open", "2026-02-13"),
    ("HK", "2026-02-16T04:10:00+00:00", "postclose", "2026-02-13"),
    ("HK", "2026-02-16T05:30:00+00:00", "postclose", "2026-02-16"),
    ("US", "2026-11-27T17:59:00+00:00", "open", "2026-11-25"),
    ("US", "2026-11-27T18:00:00+00:00", "postclose", "2026-11-25"),
    ("US", "2026-11-27T19:00:00+00:00", "postclose", "2026-11-27"),
    ("CA", "2026-12-24T18:00:00+00:00", "postclose", "2026-12-23"),
])
def test_half_day_cash_status_and_daily_settle_cutoff_differ(market, instant, state, expected):
    from lib.market_session import session_status
    result = session_status(market, clock(instant))
    assert result["state"] == state
    assert result["expected_session"] == expected
    assert result["early_close"] is True
    assert result["data_frozen"] is False


def test_lunch_and_makeup_weekends_have_distinct_status():
    from lib.market_session import session_status
    assert session_status("CN", clock("2026-10-08T04:00:00+00:00"))["state"] == "lunch"
    assert session_status("CN", clock("2026-10-10T02:00:00+00:00"))["state"] == "weekend"


def test_unpublished_year_is_explicit_and_cannot_supply_a_holiday_freshness_exemption():
    from lib.market_session import session_status, session_freshness
    now = clock("2027-10-06T03:00:00+00:00")
    status = session_status("CN", now)
    assert status["calendar_verified"] is False
    assert status["state"] == "unverified"
    assert status["data_frozen"] is False
    health = session_freshness("CN", "2027-09-30", now)
    assert health["state"] == "unverified"
    assert health["expected_closure"] is False


def test_connect_needs_both_venues_while_hk_trades_on_festival_eve():
    from lib.market_session import is_session_date, expected_session, missed_sessions
    assert is_session_date("HK", date(2026, 2, 16))
    assert not is_session_date("CONNECT", date(2026, 2, 16))
    now = clock("2026-10-07T10:00:00+00:00")
    assert expected_session("HK", now) == date(2026, 10, 7)
    assert expected_session("CONNECT", now) == date(2026, 9, 30)
    assert missed_sessions("HK", date(2026, 9, 30), date(2026, 10, 7)) == 4
    assert missed_sessions("CONNECT", date(2026, 9, 30), date(2026, 10, 7)) == 0


@pytest.mark.parametrize("symbol,market", [
    ("600519.SS", "cn"), ("000001.SZ", "cn"), ("920000.BJ", "cn"),
    ("0700.HK", "hk"), ("RY.TO", "ca"), ("ABC.V", "ca"),
    ("AAPL", "us"), ("BRK-B", "us"), ("^GSPC", "us"), ("^HSI", "hk"),
    ("^GSPTSE", "ca"), ("^HSCC", "hk"), ("^HSIL", "hk"),
    ("ES=F", None), ("GC=F", None), ("USDCNY=X", None),
    ("BTC-USD", None), ("ETH-USD", None), ("^N225", None), ("7203.T", None),
    ("VOD.L", None), ("", None),
])
def test_cash_calendar_never_freezes_derivatives_crypto_or_foreign_venues(symbol, market):
    from lib.market_session import cash_market_for_symbol
    assert cash_market_for_symbol(symbol) == market


def test_exchange_local_date_and_naive_utc_are_consistent():
    from lib.market_session import market_local_date, session_status
    assert market_local_date("CN", clock("2026-10-07T17:00:00+00:00")) == date(2026, 10, 8)
    assert session_status("US", datetime(2026, 7, 2, 14, 0))["state"] == "open"


def test_projection_is_json_serializable_and_does_not_fetch():
    import json
    from lib.market_session import session_status
    encoded = json.dumps(session_status("CN", clock("2026-10-07T03:00:00+00:00")), ensure_ascii=False)
    assert "National Day" in encoded
    assert "国庆" in encoded


def test_unknown_year_does_not_call_a_provider_weekday_invalid():
    from lib.market_session import session_freshness
    result = session_freshness("CN", "2027-10-01", clock("2027-10-01T10:00:00+00:00"))
    assert result["state"] == "unverified"
    assert result["expected_closure"] is False


def test_canadian_venture_index_uses_its_cash_exchange():
    from lib.market_session import cash_market_for_symbol
    assert cash_market_for_symbol("^SPCDNX") == "ca"


def test_connect_joint_window_closes_on_hk_half_day_and_expires_at_joint_settle():
    from lib.market_session import session_status
    result = session_status("CONNECT", clock("2026-12-24T05:00:00+00:00"))
    assert result["state"] == "postclose"
    assert result["open"] is False
    assert result["early_close"] is True
    assert result["expected_session"] == "2026-12-23"
    assert result["valid_until"] == "2026-12-24T17:00:00+08:00"
    settled = session_status("CONNECT", clock("2026-12-24T09:00:00+00:00"))
    assert settled["expected_session"] == "2026-12-24"


def test_unverified_historical_calendar_guess_cannot_invalidate_a_provider_weekday():
    from lib.market_session import session_freshness
    result = session_freshness("HK", "2021-12-28", clock("2026-10-07T10:00:00+00:00"))
    assert result["state"] == "late"
    assert result["observed_session"] == "2021-12-28"
    assert result["lag_sessions"] > 0
