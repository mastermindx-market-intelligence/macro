"""Immutable exchange-published cash-equity holiday notices, verified 2026-10-07.

This is a bounded source table, not a calendar engine. Full annual notices replace
legacy holiday approximations in the existing calendars; absent years return None
and retain those calendars' historical fallback. Dates list weekday closures only.
Early closes remain sessions. Times are local and include HKEX's latest CAS end
(12:10); store-completion settle buffers belong to the existing calendar modules.

CN: SSE/SZSE 2026 notices. HK: SEHK 2026/2027 circulars. US: NYSE 2026/2027
with Nasdaq independently corroborating 2026 only. CA: TSX/TSXV 2026; only
2027 New Year's Day is independently verified, so 2027 is NOT a verified year.
JP: JPX 2026/2027 cash-equity notices, verified 2026-10-08.
No network, filesystem, dependencies, government-workday inference or runtime
holiday calculation. Extend only from a complete official annual exchange notice.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, time
from types import MappingProxyType

_VERIFIED_ON = date(2026, 10, 7)
_SSE = "https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml"
_SZSE = "https://www.szse.cn/disclosure/notice/t20251222_618087.html"
_HK_2026 = "https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/SEHK/2025/ce_SEHK_CT_075_2025.pdf"
_HK_2027 = "https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/SEHK/2026/ce_SEHK_CT_077_2026.pdf"
_NYSE = "https://www.nyse.com/trade/hours-calendars"
_NASDAQ = "https://www.nasdaq.com/market-activity/stock-market-holiday-schedule"
_JPX = "https://www.jpx.co.jp/english/corporate/about-jpx/calendar/"
_TSX = "https://www.tsx.com/en/trading/calendars-and-trading-hours/calendar"


def _slate(year: int, groups: tuple[tuple[str, str], ...]) -> Mapping[date, str]:
    """Freeze explicit published month-day entries, with no observance arithmetic."""
    return MappingProxyType({
        date.fromisoformat(f"{year}-{md}"): name
        for name, days in groups for md in days.split()
    })


_ANNOUNCED = MappingProxyType({
    ("JP", 2026): _slate(2026, (
        ("New Year's Day", "01-01"),
        ("Market Holiday", "01-02 12-31"),
        ("Coming of Age Day", "01-12"),
        ("National Foundation Day", "02-11"),
        ("Emperor's Birthday", "02-23"),
        ("Vernal Equinox", "03-20"),
        ("Showa Day", "04-29"),
        ("Greenery Day", "05-04"),
        ("Children's Day", "05-05"),
        ("Constitution Memorial Day observed", "05-06"),
        ("Marine Day", "07-20"),
        ("Mountain Day", "08-11"),
        ("Respect for the Aged Day", "09-21"),
        ("Holiday", "09-22"),
        ("Autumnal Equinox", "09-23"),
        ("Sports Day", "10-12"),
        ("Culture Day", "11-03"),
        ("Labor Thanksgiving Day", "11-23"),
    )),
    ("JP", 2027): _slate(2027, (
        ("New Year's Day", "01-01"),
        ("Market Holiday", "12-31"),
        ("Coming of Age Day", "01-11"),
        ("National Foundation Day", "02-11"),
        ("Emperor's Birthday", "02-23"),
        ("Vernal Equinox observed", "03-22"),
        ("Showa Day", "04-29"),
        ("Constitution Memorial Day", "05-03"),
        ("Greenery Day", "05-04"),
        ("Children's Day", "05-05"),
        ("Marine Day", "07-19"),
        ("Mountain Day", "08-11"),
        ("Respect for the Aged Day", "09-20"),
        ("Autumnal Equinox", "09-23"),
        ("Sports Day", "10-11"),
        ("Culture Day", "11-03"),
        ("Labor Thanksgiving Day", "11-23"),
    )),
    ("CN", 2026): _slate(2026, (
        ("New Year's Day", "01-01 01-02"),
        ("Spring Festival", "02-16 02-17 02-18 02-19 02-20 02-23"),
        ("Qingming Festival", "04-06"),
        ("Labour Day", "05-01 05-04 05-05"),
        ("Dragon Boat Festival", "06-19"),
        ("Mid-Autumn Festival", "09-25"),
        ("National Day", "10-01 10-02 10-05 10-06 10-07"),
    )),
    ("HK", 2026): _slate(2026, (
        ("New Year's Day", "01-01"),
        ("Lunar New Year", "02-17 02-18 02-19"),
        ("Good Friday", "04-03"),
        ("Easter Monday", "04-06"),
        ("Ching Ming Festival", "04-07"),
        ("Labour Day", "05-01"),
        ("Buddha's Birthday", "05-25"),
        ("Tuen Ng Festival", "06-19"),
        ("Hong Kong SAR Establishment Day", "07-01"),
        ("National Day", "10-01"),
        ("Chung Yeung Festival", "10-19"),
        ("Christmas Day", "12-25"),
    )),
    ("HK", 2027): _slate(2027, (
        ("New Year's Day", "01-01"),
        ("Lunar New Year", "02-08 02-09"),
        ("Good Friday", "03-26"),
        ("Easter Monday", "03-29"),
        ("Ching Ming Festival", "04-05"),
        ("Buddha's Birthday", "05-13"),
        ("Tuen Ng Festival", "06-09"),
        ("Hong Kong SAR Establishment Day", "07-01"),
        ("Day following Mid-Autumn Festival", "09-16"),
        ("National Day", "10-01"),
        ("Chung Yeung Festival", "10-08"),
        ("Christmas holiday", "12-27"),
    )),
    ("US", 2026): _slate(2026, (
        ("New Year's Day", "01-01"),
        ("Martin Luther King Jr. Day", "01-19"),
        ("Washington's Birthday", "02-16"),
        ("Good Friday", "04-03"),
        ("Memorial Day", "05-25"),
        ("Juneteenth", "06-19"),
        ("Independence Day", "07-03"),
        ("Labor Day", "09-07"),
        ("Thanksgiving", "11-26"),
        ("Christmas Day", "12-25"),
    )),
    ("US", 2027): _slate(2027, (
        ("New Year's Day", "01-01"),
        ("Martin Luther King Jr. Day", "01-18"),
        ("Washington's Birthday", "02-15"),
        ("Good Friday", "03-26"),
        ("Memorial Day", "05-31"),
        ("Juneteenth", "06-18"),
        ("Independence Day", "07-05"),
        ("Labor Day", "09-06"),
        ("Thanksgiving", "11-25"),
        ("Christmas Day", "12-24"),
    )),
    ("CA", 2026): _slate(2026, (
        ("New Year's Day", "01-01"),
        ("Family Day", "02-16"),
        ("Good Friday", "04-03"),
        ("Victoria Day", "05-18"),
        ("Canada Day", "07-01"),
        ("Civic Holiday", "08-03"),
        ("Labour Day", "09-07"),
        ("Thanksgiving", "10-12"),
        ("Christmas Day", "12-25"),
        ("Boxing Day", "12-28"),
    )),
})

_PARTIAL = MappingProxyType({
    ("CA", 2027): _slate(2027, (("New Year's Day", "01-01"),)),
})

_HALF_NAMES = MappingProxyType({
    ("HK", 2026): _slate(2026, (
        ("Lunar New Year's Eve (early close)", "02-16"),
        ("Christmas Eve (early close)", "12-24"),
        ("New Year's Eve (early close)", "12-31"),
    )),
    ("HK", 2027): _slate(2027, (
        ("Lunar New Year's Eve (early close)", "02-05"),
        ("Christmas Eve (early close)", "12-24"),
        ("New Year's Eve (early close)", "12-31"),
    )),
    ("US", 2026): _slate(2026, (
        ("Day after Thanksgiving (early close)", "11-27"),
        ("Christmas Eve (early close)", "12-24"),
    )),
    ("US", 2027): _slate(2027, (
        ("Day after Thanksgiving (early close)", "11-26"),
    )),
    ("CA", 2026): _slate(2026, (
        ("Christmas Eve (early close)", "12-24"),
    )),
})
_HALF_TIMES = MappingProxyType({
    (market, day): time(12, 10) if market == "HK" else time(13)
    for (market, _year), names in _HALF_NAMES.items() for day in names
})

_YEAR_SOURCES = MappingProxyType({
    "JP": MappingProxyType({2026: (_JPX,), 2027: (_JPX,)}),
    "CN": MappingProxyType({2026: (_SSE, _SZSE)}),
    "HK": MappingProxyType({2026: (_HK_2026,), 2027: (_HK_2027,)}),
    "US": MappingProxyType({2026: (_NYSE, _NASDAQ), 2027: (_NYSE,)}),
    "CA": MappingProxyType({2026: (_TSX,)}),
})
_COVERAGE = MappingProxyType({
    market: MappingProxyType({
        "verified_years": frozenset(year_sources),
        "source_urls": tuple(dict.fromkeys(url for urls in year_sources.values() for url in urls)),
        "year_source_urls": year_sources,
        "partial_years": frozenset(year for m, year in _PARTIAL if m == market),
        "partial_source_urls": MappingProxyType({2027: (_TSX,)} if market == "CA" else {}),
        "verified_on": date(2026, 10, 8) if market == "JP" else _VERIFIED_ON,
    })
    for market, year_sources in _YEAR_SOURCES.items()
})

_NAMES_ZH = MappingProxyType({
    "Market Holiday": "市场休市日",
    "Coming of Age Day": "成人节",
    "National Foundation Day": "建国纪念日",
    "Emperor's Birthday": "天皇诞生日",
    "Vernal Equinox": "春分日",
    "Vernal Equinox observed": "春分日补休日",
    "Showa Day": "昭和之日",
    "Greenery Day": "绿之日",
    "Children's Day": "儿童节",
    "Constitution Memorial Day": "宪法纪念日",
    "Constitution Memorial Day observed": "宪法纪念日补休日",
    "Marine Day": "海之日",
    "Mountain Day": "山之日",
    "Respect for the Aged Day": "敬老日",
    "Holiday": "国民休假日",
    "Autumnal Equinox": "秋分日",
    "Sports Day": "体育节",
    "Culture Day": "文化节",
    "Labor Thanksgiving Day": "勤劳感谢日",
    "New Year's Day": "元旦",
    "Spring Festival": "春节",
    "Qingming Festival": "清明节",
    "Labour Day": "劳动节",
    "Dragon Boat Festival": "端午节",
    "Mid-Autumn Festival": "中秋节",
    "National Day": "国庆节",
    "Lunar New Year": "农历新年",
    "Good Friday": "耶稣受难节",
    "Easter Monday": "复活节星期一",
    "Ching Ming Festival": "清明节",
    "Buddha's Birthday": "佛诞",
    "Tuen Ng Festival": "端午节",
    "Hong Kong SAR Establishment Day": "香港特别行政区成立纪念日",
    "Chung Yeung Festival": "重阳节",
    "Day following Mid-Autumn Festival": "中秋节翌日",
    "Christmas Day": "圣诞节",
    "Christmas holiday": "圣诞节假期",
    "Martin Luther King Jr. Day": "马丁·路德·金纪念日",
    "Washington's Birthday": "华盛顿诞辰",
    "Memorial Day": "阵亡将士纪念日",
    "Juneteenth": "六月节",
    "Independence Day": "独立日",
    "Labor Day": "劳动节",
    "Thanksgiving": "感恩节",
    "Family Day": "家庭日",
    "Victoria Day": "维多利亚日",
    "Canada Day": "加拿大日",
    "Civic Holiday": "公民假日",
    "Boxing Day": "节礼日",
    "Lunar New Year's Eve (early close)": "农历除夕（半日市）",
    "Christmas Eve (early close)": "圣诞前夕（半日市）",
    "New Year's Eve (early close)": "除夕（半日市）",
    "Day after Thanksgiving (early close)": "感恩节翌日（半日市）",
})


def announced_holidays(market: str, year: int) -> Mapping[date, str] | None:
    """A complete official annual weekday-closure slate, or None for fallback.

    Canonical markets are CN, HK, US, CA, JP. Unknown keys are rejected; an absent
    year (including a partial annual notice) never claims complete verification.
    """
    calendar_coverage(market)
    return _ANNOUNCED.get((market, year))


def early_close(market: str, day: date) -> time | None:
    """Latest scheduled cash-equity close, in local time, for published half days."""
    calendar_coverage(market)
    return _HALF_TIMES.get((market, day))


def calendar_coverage(market: str) -> Mapping[str, object]:
    """Immutable coverage and source provenance, without annual extrapolation."""
    return _COVERAGE[market]


def holiday_name(market: str, day: date, language: str = "en") -> str | None:
    """Published full/half-day name, including partial notices; no rule inference."""
    calendar_coverage(market)
    if language not in ("en", "zh"):
        raise ValueError(f"unsupported holiday language: {language}")
    key = (market, day.year)
    names = _ANNOUNCED.get(key, _PARTIAL.get(key, {}))
    name = names.get(day) or _HALF_NAMES.get(key, {}).get(day)
    return _NAMES_ZH[name] if name and language == "zh" else name
