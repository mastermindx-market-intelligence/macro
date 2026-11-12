"""IPO calendar refreshes preserve the existing deal-status precedence.

Synthetic Nasdaq responses, real temporary Parquet, and native Radar consumers.
No network or repository data writes.
"""
from datetime import datetime, timezone
from itertools import product

import pandas as pd
import pytest
import requests

from collectors import ipo_calendar as ic
from engine import ipo_radar as ir


STATUSES = ("filed", "upcoming", "priced", "withdrawn")
# Independent statement of the documented ordering, including terminal ties.
RANK = {"filed": 0, "upcoming": 1, "priced": 3, "withdrawn": 3}


def _payload(status, deal_id="one", company="Fresh Co", price="24.00"):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = {"dealID": deal_id, "proposedTickerSymbol": "TEST", "companyName": company,
           "proposedExchange": "NASDAQ", "proposedSharePrice": price,
           "sharesOffered": "1000000", "dollarValueOfSharesOffered": "$24000000",
           "pricedDate": today if status == "priced" else None,
           "expectedPriceDate": today if status == "upcoming" else None,
           "filedDate": today, "withdrawDate": today if status == "withdrawn" else None}
    section = {"rows": [row]}
    if status == "upcoming":
        section = {"upcomingTable": section}
    return {"data": {status: section}}


@pytest.fixture
def calendar_io(monkeypatch, tmp_path):
    monkeypatch.setattr(ic.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(ic, "_months", lambda *args: ["2026-11"])
    monkeypatch.setattr(ic.time, "sleep", lambda *args: None)
    # Fail instead of silently reaching a real provider if a fixture is missed.
    monkeypatch.setattr(requests.sessions.Session, "request",
                        lambda *args, **kwargs: pytest.fail("unexpected network request"))
    monkeypatch.setattr(ir, "_close", lambda ticker: None)

    def seed(status, *, legacy=False, deal_id="one"):
        rows = ic._rows_from_month(_payload(status, deal_id, "Cached Co", "20.00"))
        frame = pd.DataFrame(rows).set_index("deal_id")
        frame["as_of"] = "2026-10-30T00:00:00+00:00"
        frame["marketed_low"] = 16.0
        frame["marketed_high"] = 18.0
        (frame.reset_index() if legacy else frame).to_parquet(ic._cache_path())
        return frame

    def refresh(payload):
        monkeypatch.setattr(ic, "_get_json", lambda session, url: payload)
        return ic.fetch_ipo_calendar()

    return seed, refresh


@pytest.mark.parametrize("old,new", list(product(STATUSES, repeat=2)))
@pytest.mark.parametrize("legacy", [False, True])
def test_refresh_respects_cached_status_rank(calendar_io, old, new, legacy):
    seed, refresh = calendar_io
    before = seed(old, legacy=legacy)
    before_bytes = ic._cache_path().read_bytes()
    result = refresh(_payload(new))
    loaded = ic.load_calendar()
    pd.testing.assert_frame_equal(result, loaded, check_dtype=False)
    if RANK[new] < RANK[old]:
        pd.testing.assert_frame_equal(loaded, before, check_dtype=False)
        assert ic._cache_path().read_bytes() == before_bytes
    else:
        assert loaded.loc["one", "status"] == new
        assert loaded.loc["one", "company"] == "Fresh Co"
        assert loaded.loc["one", "as_of"] != before.loc["one", "as_of"]
        assert loaded.loc["one", "marketed_low"] == 16.0
        assert loaded.loc["one", "marketed_high"] == 18.0


@pytest.mark.parametrize("old,new", [("priced", "filed"), ("priced", "upcoming"),
                                    ("withdrawn", "filed"), ("withdrawn", "upcoming"),
                                    ("upcoming", "filed")])
def test_mixed_refresh_preserves_old_row_and_admits_new_deal(calendar_io, old, new):
    seed, refresh = calendar_io
    before = seed(old)
    payload = _payload(new, price="30.00-40.00")
    extra = _payload("priced", "two", "New Listing")
    payload["data"].update(extra["data"])
    result = refresh(payload)
    assert set(result.index) == {"one", "two"}
    pd.testing.assert_series_equal(result.loc["one"], before.loc["one"], check_dtype=False)
    assert result.loc["two", "status"] == "priced"
    assert result.loc["two", "company"] == "New Listing"
    pd.testing.assert_frame_equal(result, ic.load_calendar(), check_dtype=False)


def test_rejected_demotion_preserves_recent_listing_and_pipeline(calendar_io):
    seed, refresh = calendar_io
    before = seed("priced")
    old_recent = ir.recent_listings(before)
    old_pipeline = ir.pipeline_stats(before)
    assert len(old_recent) == 1 and old_pipeline["priced_90d"] == 1
    refresh(_payload("filed"))
    loaded = ic.load_calendar()
    assert ir.recent_listings(loaded) == old_recent
    assert ir.pipeline_stats(loaded) == old_pipeline


def test_forward_progression_keeps_marketed_range_and_terminal_refresh(calendar_io):
    _, refresh = calendar_io
    refresh(_payload("filed"))
    refresh(_payload("upcoming", price="14.00-16.00"))
    result = refresh(_payload("priced", price="18.00"))
    assert result.loc["one", "offer_price"] == 18.0
    assert result.loc["one", "marketed_low"] == 14.0
    assert result.loc["one", "marketed_high"] == 16.0
    corrected = refresh(_payload("priced", company="Corrected Co", price="19.00"))
    assert corrected.loc["one", "offer_price"] == 19.0
    assert corrected.loc["one", "company"] == "Corrected Co"
    assert corrected.loc["one", "marketed_low"] == 14.0


@pytest.mark.parametrize("payload", [None, {}, {"data": {}}, "blocked"])
def test_no_fresh_rows_keep_cache_byte_exact(calendar_io, payload):
    seed, refresh = calendar_io
    seed("priced")
    before_bytes = ic._cache_path().read_bytes()
    refresh(payload)
    assert ic._cache_path().read_bytes() == before_bytes


def test_month_sweep_still_resolves_precedence_and_ties(calendar_io, monkeypatch):
    _, _refresh = calendar_io
    monkeypatch.setattr(ic, "_months", lambda *args: ["2026-09", "2026-10", "2026-11"])
    replies = iter([_payload("priced", company="First"), _payload("filed"),
                    _payload("priced", company="Last equal-rank correction")])
    monkeypatch.setattr(ic, "_get_json", lambda *args: next(replies))
    result = ic.fetch_ipo_calendar()
    assert result.loc["one", "status"] == "priced"
    assert result.loc["one", "company"] == "Last equal-rank correction"


@pytest.mark.parametrize("case", ["demotion", "promotion", "empty", "blocked"])
def test_native_http_json_cache_path(calendar_io, monkeypatch, case):
    seed, _ = calendar_io
    before = seed("filed" if case == "promotion" else "priced")
    old_bytes = ic._cache_path().read_bytes()
    calls = []
    payload = ({"data": {}} if case == "empty" else
               _payload("priced" if case == "promotion" else "filed"))

    class Response:
        status_code = 403 if case == "blocked" else 200
        headers = {"content-type": "application/json"}

        def raise_for_status(self):
            assert self.status_code == 200

        def json(self):
            return payload

    def request(session, method, url, **kwargs):
        calls.append((method, url, kwargs["timeout"]))
        return Response()

    monkeypatch.setattr(requests.sessions.Session, "request", request)
    result = ic.fetch_ipo_calendar()
    assert calls == [("GET", ic.CALENDAR.format("2026-11"), 25)]
    if case == "promotion":
        assert result.loc["one", "status"] == "priced"
        assert result.loc["one", "company"] == "Fresh Co"
    else:
        pd.testing.assert_frame_equal(result, before, check_dtype=False)
        assert ic._cache_path().read_bytes() == old_bytes


def test_seeded_refresh_sequences_match_independent_rank_oracle(calendar_io):
    import random

    seed, refresh = calendar_io
    rng = random.Random(138)
    for sequence in range(64):
        expected = rng.choice(STATUSES)
        seed(expected)
        company = "Cached Co"
        for step in range(8):
            incoming = rng.choice(STATUSES)
            new_company = f"Sequence {sequence} step {step}"
            if RANK[incoming] >= RANK[expected]:
                expected, company = incoming, new_company
            actual = refresh(_payload(incoming, company=new_company))
            assert actual.loc["one", "status"] == expected
            assert actual.loc["one", "company"] == company
            assert len(actual) == 1
        pd.testing.assert_frame_equal(actual, ic.load_calendar(), check_dtype=False)
