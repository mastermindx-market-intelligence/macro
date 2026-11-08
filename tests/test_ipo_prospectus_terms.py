"""Discriminating retained-source and per-deal consumer checks, no network."""
import json
from pathlib import Path

import pandas as pd
import pytest

from engine.ipo_prospectus_terms import native_deals, parse_terms, price_path, qualified_deal

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-20T03:00:00Z"


@pytest.fixture(scope="module")
def source():
    rows = pd.read_parquet(ROOT / "data/ipo/lockups.parquet").reset_index()
    row = rows[rows.ticker == "CRCL"].iloc[0].to_dict()
    cal = pd.read_parquet(ROOT / "data/ipo/calendar.parquet")
    return row, cal[cal.ticker == "CRCL"].iloc[0].to_dict()


def test_native_terms_keep_conditional_and_unobserved_facts(source):
    row, cal = source
    result = qualified_deal(row, cal, as_of=NOW)
    assert result is not None
    assert result["offer_price"] == "31.00"
    assert (result["primary_shares"], result["secondary_shares"]) == (14800000, 19200000)
    assert (result["option_days"], result["option_max_shares"]) == (30, 5100000)
    assert result["lockup_earnings_quarter"] == "2025-09-30"
    assert result["employee_earnings_quarter"] == "2025-06-30"
    assert result["employee_release_percent"] == 15
    assert result["lockup_expiry"] is result["option_exercised"] is result["actual_float"] is None
    assert result["prospectus_date"] == "2025-06-04"
    assert result["first_trade_date"] == "2025-06-05"


@pytest.mark.parametrize("field,value", [
    ("cik", "0000000001"), ("accession", "0001193125-25-000001"),
    ("form", "S-1"), ("ticker", "OTHER"), ("primary_document", "other.htm"),
    ("filed_at", "2026-10-21T19:00:00Z"), ("prospectus_date", "2025-06-06"),
])
def test_wrong_identity_or_clock_refuses(source, field, value):
    row, cal = source
    assert qualified_deal({**row, field: value}, cal, as_of=NOW) is None


def test_historical_cutoff_cannot_see_later_acquisition(source):
    row, cal = source
    assert qualified_deal(row, cal, as_of="2025-06-06T00:00:00Z") is None


def test_bytes_receipt_and_calendar_must_agree(source):
    row, cal = source
    assert qualified_deal({**row, "prospectus_archive_content": row["prospectus_archive_content"] + b"x"}, cal, as_of=NOW) is None
    assert qualified_deal(row, {**cal, "offer_price": 30}, as_of=NOW) is None
    assert qualified_deal(row, {**cal, "shares": 34000001}, as_of=NOW) is None
    assert qualified_deal(row, {**cal, "is_spac": True}, as_of=NOW) is None
    assert qualified_deal(row, {**cal, "company": "Another Company"}, as_of=NOW) is None


def test_conflicting_or_follow_on_price_not_qualified(source):
    content = source[0]["prospectus_archive_content"]
    assert parse_terms(content + b"<p>The initial public offering price is $32.00 per share.</p>")["status"] == "unavailable"
    assert parse_terms(b"<p>Hypothetical IPO price $31.00, option 30 days, lock-up 180 days.</p>")["status"] == "unavailable"
    assert parse_terms(b"x" * (8 * 1024 * 1024 + 1))["status"] == "unavailable"


def test_hidden_conflicting_prose_not_a_visible_disclosure(source):
    content = source[0]["prospectus_archive_content"]
    assert parse_terms(content + b"<script>The initial public offering price is $32.00 per share.</script>")["offer_price"] == "31.00"


def test_path_uses_unadjusted_close_and_actual_dates():
    frame = pd.DataFrame({"close_price": [20, 83.23, float("nan"), 82.22, 90],
                          "close": [1, 2, 3, 4, 5], "volume": [10]*5},
                         index=pd.to_datetime(["2025-06-04", "2025-06-05", "2025-06-06", "2026-10-16", "2026-10-21"]))
    assert price_path(frame, first_trade_date="2025-06-05", as_of=NOW) == [
        {"date": "2025-06-05", "close": 83.23, "volume": 10},
        {"date": "2026-10-16", "close": 82.22, "volume": 10}]
    assert price_path(frame.drop(columns="close_price"), first_trade_date="2025-06-05", as_of=NOW) == []


def test_native_consumer_binds_deal_to_actual_price_path(monkeypatch):
    import requests
    def no_network(*args, **kwargs):
        raise AssertionError("consumer may not fetch")
    monkeypatch.setattr(requests.Session, "request", no_network)
    rows = native_deals(as_of=NOW)
    deal = next(row for row in rows if row["ticker"] == "CRCL")
    assert deal["prices"][0]["date"] == "2025-06-05"
    assert deal["prices"][0]["close"] == pytest.approx(83.2300033569)
    assert deal["prices"][-1]["date"] <= "2026-10-20"


def test_conditional_source_never_turns_into_a_standard_expiry(source, monkeypatch):
    from engine import ipo_lockup
    row, cal = source
    monkeypatch.setattr(ipo_lockup, "_today", lambda: pd.Timestamp("2025-07-01"))
    cache = pd.DataFrame([row]).set_index("ticker")
    assert ipo_lockup.lockup_rows(pd.DataFrame([cal]), cache) == []


def test_legacy_ttl_refresh_preserves_retained_filing(source, monkeypatch):
    from collectors import ipo_prospectus
    row, _ = source
    cache = pd.DataFrame([{**row, "as_of": "2000-01-01T00:00:00Z"}]).set_index("ticker")
    monkeypatch.setattr(ipo_prospectus, "load_lockups", lambda: cache)
    def unexpected_fetch(*args, **kwargs):
        raise AssertionError("day-count refresh must not replace retained filing bytes")
    monkeypatch.setattr(ipo_prospectus, "_ticker_cik_map", unexpected_fetch)
    result = ipo_prospectus.fetch_lockups(["CRCL"])
    pd.testing.assert_frame_equal(result, cache)
