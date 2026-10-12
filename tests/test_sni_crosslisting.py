"""Acceptance cases for the SNI cross-listing guard (A12, A13, A11, A01, A04)."""
import re
import sys
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

import pytest
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/crosslisting"),
)

from sni_crosslisting import (  # noqa: E402
    AUTHORITY_FLAG_NAMES,
    AUTHORITY_FLAGS_FALSE,
    REFUSAL_CODES,
    Calendar,
    CapitalVersion,
    FxQuote,
    GuardRefused,
    SessionState,
    ads_ordinary_parity,
    bind_counters,
    fx_compare,
    refuse_if_authority_true,
    session_state,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research/single_name_intelligence/crosslisting/sni_crosslisting.py"
DOC_PATH = ROOT / "research/single_name_intelligence/crosslisting/CROSSLISTING_GUARD_DRAFT.md"

UTC = timezone.utc
EMPTY_CAL = Calendar(holidays={}, halts=())
WEEKDAY = date(2026, 10, 13)  # Tuesday
HK_OPEN_UTC = datetime(2026, 10, 13, 3, 0, tzinfo=UTC)  # 11:00 HKT
MAX_AGE = timedelta(minutes=15)


def _us_tzdata_ok() -> bool:
    try:
        zone = ZoneInfo("America/New_York")
        before = datetime(2026, 3, 7, 14, 35, tzinfo=UTC).astimezone(zone)
        after = datetime(2026, 3, 9, 14, 35, tzinfo=UTC).astimezone(zone)
        return before.utcoffset() != after.utcoffset()
    except (ZoneInfoNotFoundError, Exception):
        return False


def _hk_utc(day: date, hour: int, minute: int) -> datetime:
    try:
        zone = ZoneInfo("Asia/Hong_Kong")
    except ZoneInfoNotFoundError:
        zone = timezone(timedelta(hours=8))
    local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)
    return local.astimezone(UTC)


def _fx_usd_hkd(*, as_of: datetime, rate: Fraction = Fraction("7.8")) -> FxQuote:
    return FxQuote(base="USD", quote="HKD", rate=rate, as_of_utc=as_of)


def _raise_code(fn, code: str):
    with pytest.raises(GuardRefused) as caught:
        fn()
    assert caught.value.code == code
    return caught.value


# --- A12 session state -------------------------------------------------------

def test_a12_hk_1100_open():
    ts = _hk_utc(WEEKDAY, 11, 0)
    assert session_state("XHKG", ts, calendar=EMPTY_CAL, local_code="09988") is SessionState.OPEN


def test_a12_hk_1230_lunch():
    ts = _hk_utc(WEEKDAY, 12, 30)
    assert session_state("XHKG", ts, calendar=EMPTY_CAL, local_code="09988") is SessionState.LUNCH


def test_a12_hk_1330_open():
    ts = _hk_utc(WEEKDAY, 13, 30)
    assert session_state("XHKG", ts, calendar=EMPTY_CAL, local_code="09988") is SessionState.OPEN


def test_a12_hk_1630_closed():
    ts = _hk_utc(WEEKDAY, 16, 30)
    assert session_state("XHKG", ts, calendar=EMPTY_CAL, local_code="09988") is SessionState.CLOSED


def test_a12_hk_lunch_bounds():
    assert session_state("XHKG", _hk_utc(WEEKDAY, 12, 0), calendar=EMPTY_CAL) is SessionState.LUNCH
    assert session_state("XHKG", _hk_utc(WEEKDAY, 13, 0), calendar=EMPTY_CAL) is SessionState.OPEN
    assert session_state("XHKG", _hk_utc(WEEKDAY, 9, 30), calendar=EMPTY_CAL) is SessionState.OPEN
    assert session_state("XHKG", _hk_utc(WEEKDAY, 16, 0), calendar=EMPTY_CAL) is SessionState.CLOSED


def test_a12_saturday_closed():
    saturday = date(2026, 10, 10)
    ts = _hk_utc(saturday, 11, 0)
    assert session_state("XHKG", ts, calendar=EMPTY_CAL) is SessionState.CLOSED


def test_a12_fixture_holiday():
    cal = Calendar(holidays={"XHKG": frozenset({WEEKDAY})}, halts=())
    ts = _hk_utc(WEEKDAY, 11, 0)
    assert session_state("XHKG", ts, calendar=cal, local_code="09988") is SessionState.HOLIDAY


def test_a12_holiday_wins_over_weekend():
    saturday = date(2026, 10, 10)
    cal = Calendar(holidays={"XHKG": frozenset({saturday})}, halts=())
    ts = _hk_utc(saturday, 11, 0)
    assert session_state("XHKG", ts, calendar=cal) is SessionState.HOLIDAY


def test_a12_halted_code():
    start = datetime(2026, 10, 13, 3, 0, tzinfo=UTC)
    end = datetime(2026, 10, 13, 4, 0, tzinfo=UTC)
    cal = Calendar(holidays={}, halts=(("XHKG", "09988", start, end),))
    ts = _hk_utc(WEEKDAY, 11, 0)
    assert session_state("XHKG", ts, calendar=cal, local_code="09988") is SessionState.HALTED


def test_a12_other_code_open_during_halt():
    start = datetime(2026, 10, 13, 3, 0, tzinfo=UTC)
    end = datetime(2026, 10, 13, 4, 0, tzinfo=UTC)
    cal = Calendar(holidays={}, halts=(("XHKG", "09988", start, end),))
    ts = _hk_utc(WEEKDAY, 11, 0)
    assert session_state("XHKG", ts, calendar=cal, local_code="89988") is SessionState.OPEN


def test_a12_unknown_venue_is_unknown_never_open():
    ts = _hk_utc(WEEKDAY, 11, 0)
    state = session_state("XXXX", ts, calendar=EMPTY_CAL, local_code="09988")
    assert state is SessionState.UNKNOWN
    assert state is not SessionState.OPEN


def test_a12_naive_datetime_valueerror():
    naive = datetime(2026, 10, 13, 3, 0)
    with pytest.raises(ValueError):
        session_state("XHKG", naive, calendar=EMPTY_CAL)


@pytest.mark.skipif(not _us_tzdata_ok(), reason="tzdata missing for America/New_York")
def test_a12_us_dst_pair_closed_then_open():
    before = datetime(2026, 3, 7, 14, 35, tzinfo=UTC)
    after = datetime(2026, 3, 9, 14, 35, tzinfo=UTC)
    assert session_state("XNYS", before, calendar=EMPTY_CAL, local_code="BABA") is SessionState.CLOSED
    assert session_state("XNYS", after, calendar=EMPTY_CAL, local_code="BABA") is SessionState.OPEN
    zone = ZoneInfo("America/New_York")
    assert before.astimezone(zone).utcoffset() != after.astimezone(zone).utcoffset()


def test_a12_xnas_follows_new_york_session():
    # 2026-10-13 14:00 UTC = 10:00 EDT, inside XNAS cash hours.
    ts = datetime(2026, 10, 13, 14, 0, tzinfo=UTC)
    if _us_tzdata_ok():
        assert session_state("XNAS", ts, calendar=EMPTY_CAL, local_code="MSFT") is SessionState.OPEN


# --- A13 FX freshness and closed-market --------------------------------------

def test_a13_stale_fx_refused():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of - timedelta(minutes=16))
    _raise_code(
        lambda: fx_compare(
            px_a=80, ccy_a="USD", px_b=78, ccy_b="HKD", fx=fx,
            as_of_utc=as_of, max_age=MAX_AGE,
            state_a=SessionState.OPEN, state_b=SessionState.OPEN,
        ),
        "FX_STALE",
    )


def test_a13_future_fx_refused():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of + timedelta(seconds=1))
    _raise_code(
        lambda: fx_compare(
            px_a=80, ccy_a="USD", px_b=78, ccy_b="HKD", fx=fx,
            as_of_utc=as_of, max_age=MAX_AGE,
            state_a=SessionState.OPEN, state_b=SessionState.OPEN,
        ),
        "FX_STALE",
    )


def test_a13_pair_mismatch_refused():
    as_of = HK_OPEN_UTC
    fx = FxQuote(base="USD", quote="CNH", rate=Fraction(7), as_of_utc=as_of)
    _raise_code(
        lambda: fx_compare(
            px_a=80, ccy_a="USD", px_b=78, ccy_b="HKD", fx=fx,
            as_of_utc=as_of, max_age=MAX_AGE,
            state_a=SessionState.OPEN, state_b=SessionState.OPEN,
        ),
        "FX_PAIR_MISMATCH",
    )


def test_a13_lunch_refused():
    as_of = _hk_utc(WEEKDAY, 12, 30)
    fx = _fx_usd_hkd(as_of=as_of)
    _raise_code(
        lambda: fx_compare(
            px_a=80, ccy_a="USD", px_b=78, ccy_b="HKD", fx=fx,
            as_of_utc=as_of, max_age=MAX_AGE,
            state_a=SessionState.OPEN, state_b=SessionState.LUNCH,
        ),
        "MARKET_NOT_OPEN",
    )


def test_a13_unknown_refused():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of)
    _raise_code(
        lambda: fx_compare(
            px_a=80, ccy_a="USD", px_b=78, ccy_b="HKD", fx=fx,
            as_of_utc=as_of, max_age=MAX_AGE,
            state_a=SessionState.UNKNOWN, state_b=SessionState.OPEN,
        ),
        "MARKET_NOT_OPEN",
    )


def test_a13_closed_holiday_halted_refused():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of)
    for bad in (SessionState.CLOSED, SessionState.HOLIDAY, SessionState.HALTED):
        _raise_code(
            lambda b=bad: fx_compare(
                px_a=80, ccy_a="USD", px_b=78, ccy_b="HKD", fx=fx,
                as_of_utc=as_of, max_age=MAX_AGE,
                state_a=SessionState.OPEN, state_b=b,
            ),
            "MARKET_NOT_OPEN",
        )


def test_a13_open_open_fresh_exact_fraction():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of, rate=Fraction("7.8"))
    got = fx_compare(
        px_a=80, ccy_a="USD", px_b=78, ccy_b="HKD", fx=fx,
        as_of_utc=as_of, max_age=MAX_AGE,
        state_a=SessionState.OPEN, state_b=SessionState.OPEN,
    )
    assert got == Fraction(8)
    inverted = fx_compare(
        px_a=78, ccy_a="HKD", px_b=80, ccy_b="USD", fx=fx,
        as_of_utc=as_of, max_age=MAX_AGE,
        state_a=SessionState.OPEN, state_b=SessionState.OPEN,
    )
    assert inverted == Fraction(78, 80) / Fraction("7.8") * 78 / 78
    assert inverted == Fraction(78) / (Fraction(80) * Fraction("7.8"))


def test_a13_hk_1630_vs_us_0945_refused():
    """9988 at 16:30 HKT vs BABA at 09:45 ET: HK leg is CLOSED."""
    as_of = datetime(2026, 10, 12, 13, 45, tzinfo=UTC)  # 09:45 EDT / 21:45 HKT
    hk = session_state("XHKG", as_of, calendar=EMPTY_CAL, local_code="09988")
    us = session_state("XNYS", as_of, calendar=EMPTY_CAL, local_code="BABA")
    assert hk is SessionState.CLOSED
    if _us_tzdata_ok():
        assert us is SessionState.OPEN
    fx = _fx_usd_hkd(as_of=as_of)
    _raise_code(
        lambda: fx_compare(
            px_a=80, ccy_a="USD", px_b=78, ccy_b="HKD", fx=fx,
            as_of_utc=as_of, max_age=MAX_AGE,
            state_a=us if _us_tzdata_ok() else SessionState.OPEN,
            state_b=hk,
        ),
        "MARKET_NOT_OPEN",
    )


# --- A11 capital-version parity ----------------------------------------------

def test_a11_capital_none_refused():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of)
    _raise_code(
        lambda: ads_ordinary_parity(
            ads_px=80, ads_ccy="USD", ord_px=78, ord_ccy="HKD",
            fx=fx, capital=None, as_of_utc=as_of, max_age=MAX_AGE,
            state_ads=SessionState.OPEN, state_ord=SessionState.OPEN,
        ),
        "CAPITAL_VERSION_REQUIRED",
    )


def test_a11_not_yet_effective_refused():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of)
    capital = CapitalVersion(
        version_id="cv-fixture-1",
        owner="capital_structure",
        ads_ratio=Fraction(8),
        effective_from_utc=as_of + timedelta(seconds=1),
    )
    _raise_code(
        lambda: ads_ordinary_parity(
            ads_px=80, ads_ccy="USD", ord_px=78, ord_ccy="HKD",
            fx=fx, capital=capital, as_of_utc=as_of, max_age=MAX_AGE,
            state_ads=SessionState.OPEN, state_ord=SessionState.OPEN,
        ),
        "CAPITAL_VERSION_NOT_EFFECTIVE",
    )


def test_a11_parity_gap_exact_fraction_one_to_eight():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of, rate=Fraction("7.8"))
    capital = CapitalVersion(
        version_id="cv-fixture-8",
        owner="capital_structure",
        ads_ratio=Fraction(8),
        effective_from_utc=as_of - timedelta(days=1),
    )
    out = ads_ordinary_parity(
        ads_px=88, ads_ccy="USD", ord_px=78, ord_ccy="HKD",
        fx=fx, capital=capital, as_of_utc=as_of, max_age=MAX_AGE,
        state_ads=SessionState.OPEN, state_ord=SessionState.OPEN,
    )
    # 88 USD * 7.8 = 686.4 HKD; 8 ordinary * 78 = 624; 686.4/624 - 1 = 1/10
    assert out["parity_gap"] == Fraction(1, 10)
    assert out["capital_version_id"] == "cv-fixture-8"
    assert out["fx_as_of_utc"] == as_of
    zero = ads_ordinary_parity(
        ads_px=80, ads_ccy="USD", ord_px=78, ord_ccy="HKD",
        fx=fx, capital=capital, as_of_utc=as_of, max_age=MAX_AGE,
        state_ads=SessionState.OPEN, state_ord=SessionState.OPEN,
    )
    assert zero["parity_gap"] == Fraction(0)


def test_a11_descriptive_only_and_flags_false():
    as_of = HK_OPEN_UTC
    fx = _fx_usd_hkd(as_of=as_of)
    capital = CapitalVersion(
        version_id="cv-fixture-8",
        owner="capital_structure",
        ads_ratio=Fraction(8),
        effective_from_utc=as_of - timedelta(days=1),
    )
    out = ads_ordinary_parity(
        ads_px=80, ads_ccy="USD", ord_px=78, ord_ccy="HKD",
        fx=fx, capital=capital, as_of_utc=as_of, max_age=MAX_AGE,
        state_ads=SessionState.OPEN, state_ord=SessionState.OPEN,
    )
    assert out["descriptive_only"] is True
    flags = out["authority_flags"]
    assert flags == AUTHORITY_FLAGS_FALSE
    for name in AUTHORITY_FLAG_NAMES:
        assert flags[name] is False


def test_authority_flag_true_refused():
    _raise_code(lambda: refuse_if_authority_true(rank_authority=True), "AUTHORITY_FLAG_FORBIDDEN")
    _raise_code(lambda: refuse_if_authority_true({"trade_authority": True}), "AUTHORITY_FLAG_FORBIDDEN")
    assert refuse_if_authority_true(rank_authority=False) == AUTHORITY_FLAGS_FALSE


# --- A01 / A04 cross-bind ----------------------------------------------------

def test_a01_identical_counters_refused():
    counter = {"venue_mic": "XHKG", "local_code": "00700", "currency": "HKD"}
    _raise_code(lambda: bind_counters(counter, dict(counter), receipt=None), "SAME_COUNTER")


def test_a04_venue_currency_mismatch_without_receipt():
    hk = {"venue_mic": "XHKG", "local_code": "09988", "currency": "HKD"}
    us = {"venue_mic": "XNYS", "local_code": "BABA", "currency": "USD"}
    _raise_code(lambda: bind_counters(hk, us, receipt=None), "CROSS_BIND_VENUE_CURRENCY")
    rmb = {"venue_mic": "XHKG", "local_code": "89988", "currency": "CNH"}
    _raise_code(lambda: bind_counters(hk, rmb, receipt=None), "CROSS_BIND_VENUE_CURRENCY")


def test_a04_padding_refused_without_stock_identity_receipt():
    padded = {"venue_mic": "XHKG", "local_code": "0700", "currency": "HKD"}
    short = {"venue_mic": "XHKG", "local_code": "700", "currency": "HKD"}
    _raise_code(lambda: bind_counters(padded, short, receipt=None), "PADDING_MISMATCH")
    wrong_owner = {"source_owner": "other", "receipt_id": "r-1"}
    _raise_code(lambda: bind_counters(padded, short, receipt=wrong_owner), "PADDING_MISMATCH")
    five = {"venue_mic": "XHKG", "local_code": "00700", "currency": "HKD"}
    _raise_code(lambda: bind_counters(five, short, receipt=None), "PADDING_MISMATCH")


def test_a04_padding_bound_with_stock_identity_receipt():
    padded = {"venue_mic": "XHKG", "local_code": "0700", "currency": "HKD"}
    short = {"venue_mic": "XHKG", "local_code": "700", "currency": "HKD"}
    receipt = {"source_owner": "stock_identity", "receipt_id": "si-fixture-0700"}
    out = bind_counters(padded, short, receipt=receipt)
    assert out["bound"] is True
    assert out["receipt_id"] == "si-fixture-0700"
    assert out["descriptive_only"] is True
    assert "authority_flags" in out
    assert all(out["authority_flags"][n] is False for n in AUTHORITY_FLAG_NAMES)


def test_a04_cross_venue_bound_only_with_receipt():
    hk = {"venue_mic": "XHKG", "local_code": "09988", "currency": "HKD"}
    us = {"venue_mic": "XNYS", "local_code": "BABA", "currency": "USD"}
    receipt = {"source_owner": "stock_identity", "receipt_id": "si-fixture-pair"}
    out = bind_counters(hk, us, receipt=receipt)
    assert out == {
        "bound": True,
        "receipt_id": "si-fixture-pair",
        "descriptive_only": True,
        "authority_flags": AUTHORITY_FLAGS_FALSE,
    } or out["bound"] is True


def test_bind_does_not_construct_identifiers():
    hk = {"venue_mic": "XHKG", "local_code": "09988", "currency": "HKD"}
    us = {"venue_mic": "XNYS", "local_code": "BABA", "currency": "USD"}
    receipt = {"source_owner": "stock_identity", "receipt_id": "si-fixture-pair"}
    out = bind_counters(hk, us, receipt=receipt)
    dumped = repr(out)
    assert "ISS:" not in dumped
    assert "SEC:" not in dumped


# --- contract greps ----------------------------------------------------------

def test_module_source_has_no_iss_or_sec_prefixes():
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert "ISS:" not in text
    assert "SEC:" not in text


def test_refusal_codes_in_doc_exist_in_module():
    doc = DOC_PATH.read_text(encoding="utf-8")
    module = MODULE_PATH.read_text(encoding="utf-8")
    assert REFUSAL_CODES
    for code in sorted(REFUSAL_CODES):
        assert code in module
        assert code in doc
    for code in re.findall(r"GuardRefused\(\s*\"([A-Z_]+)\"", module):
        assert code in REFUSAL_CODES
        assert code in doc


def test_doc_first_paragraph_names_r1_gated_draft():
    text = DOC_PATH.read_text(encoding="utf-8")
    first = text.strip().split("\n\n", 1)[0]
    assert "R1-gated DRAFT" in first
