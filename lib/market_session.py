"""One pure projection of the incumbent cash-equity calendars.

Calendar status and data health are independent: a closure stops the completed
session clock, never repairs an observation that was already missing or invalid.
No network, scheduler, persistence, trading decision, or public-holiday inference.
Stock Connect uses the verified 2026 eligibility intersection of the two venues;
its completed-day clock conservatively waits for both venue settle buffers.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from lib import cn_calendar, hk_calendar, nyse_calendar, tsx_calendar
from lib.exchange_holidays import calendar_coverage, early_close, holiday_name

_CALENDARS = {"CN": cn_calendar, "HK": hk_calendar, "US": nyse_calendar, "CA": tsx_calendar}
_ZONES = {"CN": "Asia/Shanghai", "HK": "Asia/Hong_Kong",
          "US": "America/New_York", "CA": "America/Toronto", "CONNECT": "Asia/Hong_Kong"}
_CONNECT_SOURCE = (
    "https://www.hkex.com.hk/-/media/HKEX-Market/Mutual-Market/Stock-Connect/"
    "Reference-Materials/Trading-Hour,-Trading-and-Settlement-Calendar/2026-Calendar_pdf_e.pdf"
)
# Cash equity/index symbols only. Unrecognized foreign suffixes, derivatives and
# currencies deliberately have no cash-calendar owner.
_INDEX_MARKETS = {
    "^GSPC": "us", "^DJI": "us", "^IXIC": "us", "^NDX": "us", "^RUT": "us",
    "^VIX": "us", "^HSI": "hk", "^HSCE": "hk", "^HSTECH": "hk",
    "^HSCC": "hk", "^HSIL": "hk",
    "^GSPTSE": "ca", "^SPCDNX": "ca", "000001.SS": "cn", "000300.SS": "cn",
}


def _market(market: str) -> str:
    key = str(market).upper()
    if key not in _ZONES:
        raise KeyError(f"unsupported cash market: {market}")
    return key


def _now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _day(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def market_local_date(market: str, now: datetime | None = None) -> date:
    return _now(now).astimezone(ZoneInfo(_ZONES[_market(market)])).date()


def cash_market_for_symbol(symbol: str) -> str | None:
    symbol = str(symbol or "").strip().upper()
    for suffix, market in ((".SS", "cn"), (".SZ", "cn"), (".BJ", "cn"),
                           (".HK", "hk"), (".TO", "ca"), (".V", "ca")):
        if symbol.endswith(suffix):
            return market
    if symbol in _INDEX_MARKETS:
        return _INDEX_MARKETS[symbol]
    if not symbol or any(char in symbol for char in "=^/"):
        return None
    if re.fullmatch(r"[A-Z][A-Z0-9]{0,9}(?:[-.][A-Z])?", symbol):
        # A single class suffix (BRK-B/BRK.B) is still a US share; multi-letter
        # pairs such as BTC-USD and market suffixes such as .TO route elsewhere.
        if "." in symbol:  # Unknown single-letter suffix could be a foreign venue.
            return "us" if symbol in {"BRK.A", "BRK.B", "BF.A", "BF.B"} else None
        return "us"
    return None


def is_session_date(market: str, day: date) -> bool:
    key, day = _market(market), _day(day)
    if key == "CONNECT":
        return cn_calendar.is_session(day) and hk_calendar.is_session(day)
    return _CALENDARS[key].is_session(day)


def expected_session(market: str, now: datetime | None = None) -> date:
    key, now = _market(market), _now(now)
    if key != "CONNECT":
        return _CALENDARS[key].expected_last_session(now)
    day = min(cn_calendar.expected_last_session(now), hk_calendar.expected_last_session(now))
    while not is_session_date(key, day):
        day -= timedelta(days=1)
    return day


def missed_sessions(market: str, observed_date: date, expected_date: date) -> int:
    """Count sessions strictly after observed and through expected (all venues)."""
    key, first, last = _market(market), _day(observed_date), _day(expected_date)
    return sum(is_session_date(key, first + timedelta(days=offset))
               for offset in range(1, max(0, (last - first).days) + 1))


def calendar_verified(market: str, year: int) -> bool:
    """Whether a complete official annual notice has been incorporated."""
    market = _market(market)
    if market == "CONNECT":
        return year == 2026
    return year in calendar_coverage(market)["verified_years"]


def _windows(market: str, day: date) -> list[tuple[time, time]]:
    if market == "CN":
        # Final fixed-price session follows the 15:00 auction. Daily bars are
        # still due only at the incumbent 17:00 completion buffer.
        return [(time(9, 30), time(11, 30)), (time(13), time(15, 30))]
    if market == "CONNECT":
        # Conservative joint cash window; eligibility is separate from the
        # venue's local open flag (HK may trade while Connect is unavailable).
        if early_close("HK", day):
            return [(time(9, 30), time(11, 30))]
        return [(time(9, 30), time(11, 30)), (time(13), time(15))]
    close = early_close(market, day)
    if market == "HK":
        return [(time(9, 30), close)] if close else [
            (time(9, 30), time(12)), (time(13), time(16, 10))]
    return [(time(9, 30), close or time(16))]


def _next_open(market: str, local: datetime) -> datetime:
    day = local.date()
    for offset in range(370):
        candidate = day + timedelta(days=offset)
        if not is_session_date(market, candidate):
            continue
        for start, _ in _windows(market, candidate):
            opening = datetime.combine(candidate, start, local.tzinfo)
            if opening > local:
                return opening
    raise ValueError(f"no upcoming session found for {market}")


def _holiday(market: str, day: date, language: str) -> str | None:
    if market != "CONNECT":
        return holiday_name(market, day, language)
    names = [holiday_name(venue, day, language) for venue in ("CN", "HK")
             if not is_session_date(venue, day)]
    return " / ".join(dict.fromkeys(name for name in names if name)) or None


def session_status(market: str, now: datetime | None = None) -> dict:
    """Serializable local status, provenance and next state-change boundary.

    An expired projection must be refreshed by its incumbent producer. Consumers
    must not continue presenting its open/closure assertion after valid_until.
    Unpublished years keep legacy calendar arithmetic available, but status and
    freshness explicitly withhold verified-closure exemptions.
    """
    key, now = _market(market), _now(now)
    zone = _ZONES[key]
    local = now.astimezone(ZoneInfo(zone))
    day = local.date()
    verified = calendar_verified(key, day.year)
    scheduled = is_session_date(key, day)
    windows = _windows(key, day)
    hm = local.time().replace(tzinfo=None)
    if not verified:
        state = "unverified"
    elif not scheduled:
        state = "weekend" if day.weekday() >= 5 else "holiday"
    elif any(start <= hm < end for start, end in windows):
        state = "open"
    elif hm < windows[0][0]:
        state = "preopen"
    elif hm >= windows[-1][1]:
        state = "postclose"
    else:
        state = "lunch"

    tomorrow = datetime.combine(day + timedelta(days=1), time(), local.tzinfo)
    boundaries = [tomorrow]
    if scheduled:
        boundaries.extend(datetime.combine(day, boundary, local.tzinfo)
                          for window in windows for boundary in window)
        # Expected completed session changes after the vendor settle buffer,
        # independently of cash open/closed status.
        settle = (time(17) if key == "CONNECT" and early_close("HK", day) else
                  time(17, 30) if key == "CONNECT" else
                  time(17) if key == "CN" else
                  time(13, 30) if key == "HK" and early_close(key, day) else
                  time(17, 30) if key == "HK" else
                  time(14) if early_close(key, day) else time(17))
        boundaries.append(datetime.combine(day, settle, local.tzinfo))
    valid_until = min(boundary for boundary in boundaries if boundary > local)
    previous = day - timedelta(days=1)
    while not is_session_date(key, previous):
        previous -= timedelta(days=1)
    sources = ([_CONNECT_SOURCE] if key == "CONNECT" else
               list(calendar_coverage(key)["year_source_urls"].get(day.year, ())))
    return {
        "region": key.lower(), "open": state == "open" if verified else None,
        "state": state, "local_time": local.strftime("%Y-%m-%d %H:%M %Z"),
        "timezone": zone, "session_date": day.isoformat(),
        "holiday_name": _holiday(key, day, "en"),
        "holiday_name_zh": _holiday(key, day, "zh"),
        "next_open": _next_open(key, local).isoformat(),
        "expected_session": expected_session(key, now).isoformat(),
        "calendar_verified": verified,
        "checked_at": now.astimezone(timezone.utc).isoformat(),
        "valid_until": valid_until.isoformat(),
        "early_close": bool(early_close("HK" if key == "CONNECT" else key, day)),
        "data_frozen": verified and not scheduled,
        "closed_since": (previous + timedelta(days=1)).isoformat() if not scheduled else None,
        "source_urls": sources,
    }


def session_freshness(market: str, observed_date, now: datetime | None = None) -> dict:
    key, now = _market(market), _now(now)
    today = market_local_date(key, now)
    expected = expected_session(key, now)
    verified = calendar_verified(key, today.year)
    result = {
        "market": key, "observed_session": None, "expected_session": expected.isoformat(),
        "lag_sessions": None, "lag_calendar_days": None, "state": "missing",
        "calendar_verified": verified,
        "expected_closure": verified and not is_session_date(key, today),
        "developing": False,
    }
    if observed_date is None:
        return result
    try:
        observed = _day(observed_date)
    except (ValueError, TypeError, OverflowError):
        return {**result, "state": "invalid"}
    result["observed_session"] = observed.isoformat()
    result["lag_calendar_days"] = max(0, (expected - observed).days)
    if observed > today or observed.weekday() >= 5:
        return {**result, "state": "invalid"}
    if not calendar_verified(key, observed.year) and observed.year >= today.year:
        return {**result, "state": "unverified"}
    # Legacy historical arithmetic may be approximate. Only a verified annual
    # notice can prove that an otherwise valid provider weekday was not a session.
    if calendar_verified(key, observed.year) and not is_session_date(key, observed):
        return {**result, "state": "invalid"}
    lag = missed_sessions(key, observed, expected)
    result.update(lag_sessions=lag, developing=observed > expected)
    result["state"] = ("unverified" if not verified else "late" if lag else "current")
    return result
