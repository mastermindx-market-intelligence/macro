"""Calendar correctness at the provider/consumer boundary; no network calls."""
from datetime import datetime, timezone
from pathlib import Path
import time

import pytest

from engine.market_calendar.contracts import massive_dividend, reconcile_events, yahoo_earning
from engine.market_calendar.providers import SourceFailure, YAHOO_FIELDS, massive_pages, yahoo_body, yahoo_earnings
from engine.market_calendar.snapshot import enrich
from app.market_calendar_projection import public_view
from scripts.build_market_calendar import build

NOW = "2026-11-14T18:00:00+00:00"


@pytest.fixture(autouse=True)
def no_supplemental_network(monkeypatch):
    monkeypatch.setattr("scripts.build_market_calendar.yahoo_economics", lambda *a, **k: (
        [], {"complete": True, "pages": 1, "expectedRecords": 0}))


def earning(symbol="ZERO", date="2026-11-17T21:00:00Z", **values):
    return {"ticker": symbol, "companyshortname": symbol + " Company", "intradaymarketcap": 3e9,
            "eventname": "Q3 2026 Earnings Announcement", "startdatetime": date,
            "startdatetimetype": "AMC", "epsestimate": 0, "epsactual": 0,
            "epssurprisepct": 0, **values}


def page(rows, total):
    return {"finance": {"result": [{"total": total, "documents": [{
        "columns": [{"id": field} for field in YAHOO_FIELDS],
        "rows": [[row.get(field) for field in YAHOO_FIELDS] for row in rows],
    }]}]}}


class Response:
    status_code = 200
    def __init__(self, value): self.value = value
    def json(self): return self.value


def test_zero_unknown_basis_and_session_placeholders_are_lossless():
    event = yahoo_earning(earning(), NOW)
    assert event["earnings"]["epsActual"] == 0
    assert event["earnings"]["epsEstimate"] == 0
    assert event["status"] == "reported"
    assert event["confirmation"] == "unknown"
    assert event["scheduledAt"] is None
    assert event["session"] == "after_close"
    assert event["earnings"]["currency"] is None
    assert event["earnings"]["epsBasis"] == "unspecified"
    assert yahoo_earning(earning(date="2026-11-17"), NOW)["date"] == "2026-11-17"
    assert yahoo_earning(earning(date="2026-11-17T00:00:00Z", startdatetimetype=""), NOW)["date"] == "2026-11-17"


def test_query_includes_last_day_without_cap_or_most_active_filter():
    body = yahoo_body("2026-11-16", "2026-11-22", 100)
    assert body["offset"] == 100
    assert body["query"]["operands"][-1] == {"operator": "LT", "operands": ["startdatetime", "2026-11-23"]}
    assert len(body["query"]["operands"]) == 4


def test_pagination_overlap_never_claims_complete():
    pages = [page([earning(f"A{i}") for i in range(100)], 200),
             page([earning(f"A{i}") for i in range(99,199)], 200)]
    events, meta = yahoo_earnings("2026-11-16", "2026-11-22", NOW, time.monotonic()+5,
                                  post=lambda *a, **k: Response(pages.pop(0)))
    assert len(events) == 199
    assert not meta["complete"]
    assert meta["error"] == "overlapping_pages"


def test_massive_continuation_cannot_exfiltrate_credentials():
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return Response({"results": [], "next_url": "https://evil.invalid/stocks/v1/dividends"})
    with pytest.raises(SourceFailure, match="invalid_continuation"):
        massive_pages("/stocks/v1/dividends", {}, "fixture-key", time.monotonic()+5, get)
    assert calls == ["https://api.massive.com/stocks/v1/dividends"]


def test_dividend_currency_case_and_newer_ratio_cap():
    event = massive_dividend({"id":"cash", "ticker":"TpC", "ex_dividend_date":"2026-11-17",
                              "cash_amount":25, "currency":"GBp"}, NOW)
    assert event["dividend"]["currency"] == "GBp"
    enriched = enrich([event], {"TpC":{"market_cap":20, "date":"2026-11-12"}}, {})
    enriched = enrich(enriched, {"TpC":{"market_cap":21, "date":"2026-11-13"},
                                "TPC":{"market_cap":999, "date":"2026-11-13"}}, {})
    assert enriched[0]["marketCap"] == 21
    assert enriched[0]["capAsOf"] == "2026-11-13"


def test_new_observation_supersedes_retained_week_but_same_observation_conflicts():
    old = yahoo_earning(earning(), NOW)
    new = yahoo_earning(earning(date="2026-11-24T21:00:00Z"), "2026-11-15T18:00:00+00:00")
    merged = reconcile_events([old, new], [old], new["observedAt"])
    assert len(merged) == 1 and merged[0]["date"] == "2026-11-24"
    assert merged[0]["changes"][-1]["before"] == "2026-11-17"
    assert not merged[0]["scheduleConflict"]
    new["observedAt"] = NOW
    assert reconcile_events([old, new], [], NOW)[0]["scheduleConflict"]


def test_restricted_yahoo_stops_all_partitions_and_future_builds(monkeypatch, tmp_path):
    calls = []
    def denied(*args, **kwargs):
        calls.append(args)
        raise SourceFailure("restricted")
    monkeypatch.setattr("scripts.build_market_calendar.yahoo_earnings", denied)
    monkeypatch.setattr("scripts.build_market_calendar.secret", lambda name: None)
    result = build({}, datetime.fromisoformat(NOW), root=tmp_path)
    assert len(calls) == 1 and result["_yahoo_restricted"]
    build(result, datetime(2026,11,23,tzinfo=timezone.utc), root=tmp_path)
    assert len(calls) == 1


def test_large_private_universe_is_paged_before_http_projection():
    events = [yahoo_earning(earning(f"A{i}"), NOW) for i in range(9500)]
    snapshot = {"schema":"market-calendar.v1", "asOf":NOW, "from":"2026-11-02", "to":"2027-01-24", "events":events, "sources":[]}
    view = public_view(snapshot, datetime.fromisoformat(NOW), {}, "2026-11-16", "2026-11-22")
    assert len(view["events"]) == 2000 and view["nextCursor"] == 2000
    assert "_ratios" not in view
    assert view["total"] >= 9500
    second = public_view(snapshot, datetime.fromisoformat(NOW), {}, "2026-11-16", "2026-11-22", 2000, view["snapshotId"])
    assert not {e["id"] for e in view["events"]} & {e["id"] for e in second["events"]}
    with pytest.raises(ValueError, match="snapshot changed"):
        public_view(snapshot, datetime.fromisoformat(NOW), {}, "2026-11-16", "2026-11-22", 2000, "2026-11-13T18:00:00+00:00")
    with pytest.raises(ValueError, match="snapshot changed"):
        public_view(snapshot, datetime.fromisoformat(NOW), {"built": NOW}, "2026-11-16", "2026-11-22", 2000, view["snapshotId"])


def test_failed_refresh_retains_original_values_and_clock(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.build_market_calendar.secret", lambda name: None)
    def good(start, end, observed, deadline, **kwargs):
        return [yahoo_earning(earning(date=start+"T21:00:00Z"), observed)], {"complete":True,"pages":1,"expectedRecords":1}
    monkeypatch.setattr("scripts.build_market_calendar.yahoo_earnings", good)
    first = build({}, datetime.fromisoformat(NOW), root=tmp_path)
    def fail(*a, **k): raise SourceFailure("provider_unavailable")
    monkeypatch.setattr("scripts.build_market_calendar.yahoo_earnings", fail)
    second = build(first, datetime(2026,11,15,18,tzinfo=timezone.utc), root=tmp_path)
    assert second["events"][0]["observedAt"] == NOW
    assert any(p["status"] == "stale" and p["asOf"] == NOW for p in second["_partitions"].values())


def test_provider_economics_preserves_raw_zero_prior_and_unknown_units():
    from engine.market_calendar.contracts import yahoo_economic
    event = yahoo_economic({"econ_release": "CPI YY", "country_code": "US",
        "startdatetime": "2026-11-17T13:30:00Z", "period": "Oct", "after_release_actual": "0",
        "consensus_estimate": "0.1", "prior_release_actual": "0.2", "originally_reported_actual": "0.3"}, NOW)
    assert event["economic"]["actualDisplay"] == "0"
    assert event["economic"]["consensusDisplay"] == "0.1"
    assert event["economic"]["originallyReportedDisplay"] == "0.3"
    assert event["economic"]["actual"] is None and event["economic"]["unit"] is None
    assert event["status"] == "reported" and event["confirmation"] == "unknown"
    assert event["importance"] == "unknown" and event["source"] == "yahoo-economic"
    placeholder = yahoo_economic({"econ_release": "FDI (YTD)*", "country_code": "CN",
        "startdatetime": "2026-11-21T00:00:00Z", "period": "Oct"}, NOW)
    assert placeholder["date"] == "2026-11-21" and placeholder["scheduledAt"] is None


def test_vendor_boundary_overfetch_does_not_invalidate_complete_in_range_data():
    rows = [earning("IN"), earning("BOUNDARY", date="2026-11-23T21:00:00Z")]
    events, meta = yahoo_earnings("2026-11-16", "2026-11-22", NOW, time.monotonic()+5,
                                  post=lambda *a, **k: Response(page(rows, 2)))
    assert meta["complete"] and [e["symbol"] for e in events] == ["IN"]


def test_weekends_use_the_existing_lane_only_for_private_calendar(tmp_path):
    from scripts.vps_live_orchestrator import Orchestrator
    owner = Orchestrator(live_dir=tmp_path/"public"/"live", state_dir=tmp_path/"state",
                         data_dir=tmp_path/"data", now=datetime.fromisoformat(NOW))
    calls = []
    owner.module = lambda name, module, args, **kw: calls.append((name, module, args, kw))
    owner.snapshot()
    assert len(calls) == 1 and calls[0][0] == "market_calendar"
    assert calls[0][3]["outputs"][0][1] == tmp_path/"state"/"market_calendar.json"
    assert "public" not in str(calls[0][3]["outputs"][0][1])


def test_yahoo_timeout_retains_pages_and_resumes_beyond_the_prefix():
    calls = []
    fail = [True]
    rows = [earning(f"A{i}") for i in range(150)]
    def post(*args, **kwargs):
        offset = kwargs["body"]["offset"]
        calls.append(offset)
        if offset == 100 and fail[0]:
            fail[0] = False
            raise TimeoutError("fixture timeout")
        return Response(page(rows[offset:offset+100], 150))
    first, meta = yahoo_earnings("2026-11-17", "2026-11-17", NOW, time.monotonic()+5, post)
    assert len(first) == 100 and not meta["complete"]
    assert meta["_resume"]["offset"] == 100
    final, finished = yahoo_earnings("2026-11-17", "2026-11-17", "2026-11-14T18:05:00+00:00",
                                    time.monotonic()+5, post, meta["_resume"])
    assert len(final) == 150 and finished["complete"]
    assert finished["asOf"] == NOW and finished["_resume"] is None
    assert calls == [0, 100, 0, 100, 0]


def test_yahoo_resume_rejects_a_reordered_source_head():
    first_rows = [earning(f"A{i}") for i in range(100)]
    def post(*args, **kwargs):
        if kwargs["body"]["offset"]:
            raise TimeoutError("fixture timeout")
        return Response(page(first_rows, 150))
    _, meta = yahoo_earnings("2026-11-17", "2026-11-17", NOW, time.monotonic()+5, post)
    _, changed = yahoo_earnings("2026-11-17", "2026-11-17", NOW, time.monotonic()+5,
        lambda *a, **k: Response(page(list(reversed(first_rows)), 150)), meta["_resume"])
    assert not changed["complete"] and changed["discard"]
    assert changed["error"] == "source_changed" and changed["_resume"] is None


def test_massive_timeout_retains_original_continuation_and_clock():
    calls, fail = [], [True]
    path = "/stocks/v1/dividends"
    def get(url, **kwargs):
        calls.append(url)
        if "cursor=" in url:
            if fail[0]:
                fail[0] = False
                raise TimeoutError("fixture timeout")
            return Response({"results": [{"id": "B", "ticker": "B"}]})
        return Response({"results": [{"id": "A", "ticker": "A"}],
                         "next_url": "https://api.massive.com"+path+"?cursor=fixture"})
    first, meta = massive_pages(path, {}, "fixture-key", time.monotonic()+5, get, observed_at=NOW)
    assert len(first) == 1 and not meta["complete"]
    final, complete = massive_pages(path, {}, "fixture-key", time.monotonic()+5, get,
                                    meta["_resume"], "2026-11-14T18:05:00+00:00")
    assert [r["id"] for r in final] == ["A", "B"] and complete["complete"]
    assert complete["asOf"] == NOW and calls[-1].endswith("cursor=fixture")


def test_failing_nearest_date_cannot_starve_other_dates_or_massive(monkeypatch, tmp_path):
    clock, earnings_calls, sources = [0.0], [], []
    monkeypatch.setattr("scripts.build_market_calendar.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("scripts.build_market_calendar.secret", lambda name: "fixture-key")
    def earnings(start, end, observed, deadline, **kwargs):
        earnings_calls.append(start)
        clock[0] += 2
        if start == "2026-11-14":
            raise SourceFailure("provider_unavailable")
        return [], {"complete": True, "pages": 1, "expectedRecords": 0}
    def economics(*args, **kwargs):
        clock[0] += 1
        return [], {"complete": True, "pages": 1, "expectedRecords": 0}
    def dividends(*args, **kwargs):
        sources.append("dividends"); clock[0] += 4
        return [], {"complete": True, "pages": 1, "expectedRecords": 0}
    def ratios(*args, **kwargs):
        sources.append("ratios"); clock[0] += 4
        return [], {"complete": True, "pages": 1, "expectedRecords": 0}
    monkeypatch.setattr("scripts.build_market_calendar.yahoo_earnings", earnings)
    monkeypatch.setattr("scripts.build_market_calendar.yahoo_economics", economics)
    monkeypatch.setattr("scripts.build_market_calendar.dividends", dividends)
    monkeypatch.setattr("scripts.build_market_calendar.massive_pages", ratios)
    first = build({}, datetime.fromisoformat(NOW), root=tmp_path)
    assert earnings_calls[0] == "2026-11-14"
    assert sources == ["dividends", "ratios"]
    assert any(p.get("completeAsOf") for p in first["_partitions"].values())
    count = len(earnings_calls); clock[0] = 0
    build(first, datetime(2026,11,14,18,5,tzinfo=timezone.utc), root=tmp_path)
    assert earnings_calls[count] != "2026-11-14"
