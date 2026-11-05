"""C19 WP24-G: the short-pressure availability leg never prints absent or
censored lending supply as an exact share count.

IBKR writes '>10000000' for abundant supply. collectors/ibkr_borrow.py parses
that to avail_unlimited=True with avail_shares NA: a censored LOWER bound, not
a count. When no borrow capture covers the date (the accrual starts
2026-08-05) or the capture carries no quote for a name, availability is
ABSENT and must read as absent, never as "lending supply not scarce".

Hermetic: synthetic frames only. An empty borrow frame stands in for "no
capture", so load_borrow_panel() (a data/ read) is never called.
"""
import pandas as pd

from engine import short_pressure as sp

ASOF = "2026-08-01"
N = 300
BORROW_COLUMNS = ["ticker", "fee_pct", "avail_shares", "avail_unlimited", "date"]


def _panel(rows):
    df = pd.DataFrame(rows)
    df["settlement_date"] = pd.to_datetime(df["settlement_date"])
    df["knowable_date"] = df["settlement_date"] + pd.Timedelta(days=10)
    if "is_listed" not in df:
        df["is_listed"] = True
    if "dtc_capped" not in df:
        df["dtc_capped"] = df["days_to_cover"] >= sp.DTC_SENTINEL
    return df


def _wide_panel(settlement="2026-07-15", n=N):
    return _panel([
        {"ticker": f"T{i:04d}", "days_to_cover": 1.0 + i * 0.01,
         "si_change_pct": 1.0, "short_shares": 1e6, "settlement_date": settlement,
         "is_listed": True, "avg_daily_vol": 5e5}
        for i in range(n)])


def _tickers(n=N):
    return [f"T{i:04d}" for i in range(n)]


def _borrow(tickers, avail_shares, avail_unlimited, date="2026-07-30"):
    n = len(tickers)
    return pd.DataFrame({
        "ticker": list(tickers),
        "fee_pct": [0.5] * n,
        "avail_shares": [avail_shares] * n,
        "avail_unlimited": [avail_unlimited] * n,
        "date": pd.to_datetime([date] * n),
    })


def _availability(ticker, asof, si_panel, borrow):
    xs = sp.cross_section(asof=asof, si_panel=si_panel, borrow=borrow)
    out = sp.axes(ticker, xs=xs)
    assert out is not None, f"{ticker} missing from the cross-section"
    legs = [leg for leg in out["legs"] if leg["axis"] == "availability"]
    assert len(legs) == 1, out["legs"]
    return out, legs[0]


def test_no_capture_at_asof_reads_as_absent_not_abundant():
    empty = pd.DataFrame({c: [] for c in BORROW_COLUMNS})
    _, leg = _availability("T0000", "2020-01-01",
                           _wide_panel(settlement="2019-12-13"), empty)
    assert leg["value"] is None
    assert leg["reading"] == "no availability quote"
    assert leg["elevated"] is None


def test_capture_dated_after_asof_is_not_used():
    borrow = _borrow(_tickers(), float("nan"), True, date="2026-08-10")
    _, leg = _availability("T0000", ASOF, _wide_panel(), borrow)
    assert leg["value"] is None
    assert leg["reading"] == "no availability quote"


def test_unlimited_supply_prints_no_number():
    borrow = _borrow(_tickers(), float("nan"), True)
    _, leg = _availability("T0000", ASOF, _wide_panel(), borrow)
    assert leg["value"] is None
    assert leg["reading"] == "lending supply not scarce"
    assert not any(ch.isdigit() for ch in leg["reading"])
    assert leg["elevated"] is None


def test_unlimited_flag_wins_over_a_numeric_share_count():
    # '>10000000' is a lower bound: even if a writer also stored 10,000,000 as
    # shares, the leg must not present it as an exact count.
    borrow = _borrow(_tickers(), 10_000_000.0, True)
    _, leg = _availability("T0000", ASOF, _wide_panel(), borrow)
    assert leg["value"] is None
    assert leg["reading"] == "lending supply not scarce"


def test_exact_supply_prints_the_count():
    borrow = _borrow(_tickers(), 450_000.0, False)
    _, leg = _availability("T0000", ASOF, _wide_panel(), borrow)
    assert leg["value"] == 450_000.0
    assert leg["reading"] == "450,000 shares available to borrow"
    assert leg["elevated"] is None


def test_capture_without_a_quote_for_this_name_reads_as_absent():
    borrow = _borrow(_tickers()[1:], 450_000.0, False)
    _, leg = _availability("T0000", ASOF, _wide_panel(), borrow)
    assert leg["value"] is None
    assert leg["reading"] == "no availability quote"
    _, quoted = _availability("T0001", ASOF, _wide_panel(), borrow)
    assert quoted["value"] == 450_000.0


def test_availability_never_enters_the_measured_count():
    for shares, unlimited in ((float("nan"), True), (450_000.0, False)):
        borrow = _borrow(_tickers(), shares, unlimited)
        out, leg = _availability("T0000", ASOF, _wide_panel(), borrow)
        assert leg["elevated"] is None
        assert out["measured_count"] == sum(
            1 for x in out["legs"] if x["elevated"] is not None)
