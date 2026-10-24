"""Evidence semantics: real zero, negative weights, clock separation and event chronology."""
import json
from pathlib import Path

import pytest
from engine.china_altdata_desk import build_desk, event_rows, instrument_href

FIXTURE = Path(__file__).parent / "fixtures" / "china_altdata_desk.json"


def fixture_desk(**changes):
    raw = json.loads(FIXTURE.read_text())
    raw.update(changes)
    return build_desk(**raw)


def test_coverage_is_not_agreement_and_negative_weights_reverse_direction():
    row = dict(ticker="600000.SS", name="Example", convergence=.2, value=.8,
               margin=0, lhb=.9, block=-.6, flags=[])
    desk = fixture_desk(rows=[row])
    result = desk["rows"][0]
    assert result["available"] == 4  # finite zero is real coverage
    assert result["agreeing"] == 2
    assert result["conflicting"] == 1
    legs = {s["key"]:s for s in result["sources"]}
    assert legs["lhb"]["direction"] == "cautionary"
    assert legs["block"]["direction"] == "constructive"
    assert legs["margin"]["direction"] == "neutral"
    assert legs["flow"]["value"] is None
    assert legs["value"]["asof"] is None  # never the build date


def test_source_catalog_retains_vintage_range_and_date_basis():
    rows = [dict(ticker="600000.SS",name="A",convergence=.2,value=.5,
                 source_asof={"value":"2026-08-24"},source_date_kind={"value":"snapshot"},flags=[]),
            dict(ticker="600001.SS",name="B",convergence=.3,value=.7,
                 source_asof={"value":"2026-10-23"},source_date_kind={"value":"snapshot"},flags=[])]
    desk = fixture_desk(rows=rows)
    source = desk["sources"][0]
    assert (source["oldest_asof"],source["asof"]) == ("2026-08-24","2026-10-23")
    assert source["date_kind"] == "snapshot"
    assert desk["rows"][0]["sources"][0]["date_kind"] == "snapshot"


def test_neutral_composite_has_split_counts_not_fabricated_confidence():
    desk = fixture_desk(rows=[dict(ticker="600000.SS", name="Example",
                                  convergence=0, value=.5, margin=-.5, flags=[])])
    row = desk["rows"][0]
    assert row["side"] == "mixed"
    assert row["agreeing"] is None and row["conflicting"] is None
    assert (row["constructive"], row["cautionary"], row["neutral"]) == (1,1,0)


def test_prior_comparisons_use_dated_values_and_correct_units():
    part = {"date":"2026-10-22","turnover_z20":0,"margin_chg_5d":-1,"southbound_net":10000,
            "previous_observation":{"date":"2026-10-21","turnover_z20":0,"margin_chg_5d":-2,"southbound_net":0}}
    desk = fixture_desk(participation=part)
    metrics = {m["key"]:m for m in desk["participation"]["metrics"]}
    assert metrics["turnover_z20"]["change"] == 0
    assert metrics["margin_chg_5d"]["change"] == 1
    assert metrics["margin_chg_5d"]["change_unit_en"] == "pp"
    assert metrics["southbound_net"]["change"] == 1
    assert metrics["qvix_z"]["change"] is None
    assert "2026-10-21" in desk["briefing"][0]["detail_en"]
    for invalid in ("2026-10-22","2099-01-01","invalid"):
        part["previous_observation"]["date"] = invalid
        invalid_desk = fixture_desk(participation=part)
        assert all(m["change"] is None for m in invalid_desk["participation"]["metrics"])
        assert "unavailable" in invalid_desk["briefing"][0]["detail_en"]


def test_latest_partial_date_does_not_displace_dated_evidence():
    desk = fixture_desk()
    h = desk["data_health"]
    assert desk["observation_date"] == "2026-10-22"
    assert h["latest_date"] == "2026-10-23"
    assert h["lag_calendar_days"] == 1 and h["state"] == "partial"
    assert h["available"] == 5 and h["expected"] == 6
    assert desk["participation"]["observed_universe"] == 1875
    assert desk["participation"]["projection_kind"] == "current_source_recomputation"
    assert "not_point_in_time" in desk["participation"]["history_qualification"]
    assert desk["universe"]["total"] == 19


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "bad"])
def test_nonfinite_and_malformed_values_stay_missing(value):
    desk = fixture_desk(rows=[dict(ticker="600000.SS",name="Example",convergence=value,value=value,flags=[])])
    assert desk["rows"][0]["side"] == "insufficient"
    assert desk["rows"][0]["available"] == 0
    assert desk["rows"][0]["sources"][0]["value"] is None
    json.dumps(desk, allow_nan=False)


def test_missing_or_future_market_observation_never_reads_calm():
    for part in ({}, {"date":"2099-01-01","regime":"dormant","turnover_z20":0,"margin_chg_5d":0}):
        desk = fixture_desk(participation=part)
        assert desk["participation"]["regime_en"] == "Unavailable"
        assert desk["data_health"]["state"] == "unavailable"
        assert all(m["value"] is None for m in desk["participation"]["metrics"])
        assert "Calm" not in json.dumps(desk)


def test_future_company_input_is_not_current_directional_evidence():
    desk = fixture_desk(rows=[dict(ticker="600000.SS",name="Example",convergence=.5,value=.5,
                                  source_asof={"value":"2099-01-01"},flags=[])])
    row = desk["rows"][0]
    assert row["side"] == "insufficient" and row["alignment"] is None
    assert row["sources"][0]["state"] == "future"
    assert row["sources"][0]["direction"] == "unavailable"
    assert row["available"] == 0 and row["neutral"] == 0
    assert desk["sources"][0]["available"] == 0


def test_events_preserve_period_stage_and_denominator_without_hype():
    desk = fixture_desk()
    events = desk["events"]
    assert events[0]["type"] == "unlock" and events[0]["horizon"] == "upcoming"
    assert "10.5× existing free float" in events[0]["detail_en"]
    earnings = next(e for e in events if e["type"]=="earnings")
    assert earnings["date"] is None and earnings["horizon"] == "undated"
    assert "2026Q3" in earnings["detail_en"] and "comparison base" in earnings["detail_en"]
    assert "265430" not in earnings["detail_en"]
    assert earnings["reported_change"] == 265430.305
    buyback = next(e for e in events if e["type"]=="buyback")
    assert "Planned: CNY 3.00" in buyback["detail_en"] and "Executed: CNY 0.00" in buyback["detail_en"]
    assert buyback["stage"] == "实施中"
    assert desk["event_health"]["n_fresh"] == 6


def test_event_duplicates_and_missing_names():
    record={"secCode":"920493","secName":"并行科技","date":"2026-10-15"}
    events=event_rows({"inquiry":{"letters":[record,dict(record)]}},"2026-10-24")
    assert len(events)==1 and events[0]["name"]=="并行科技"
    assert events[0]["href"] is None  # do not guess an exchange from a bare code


def test_distinct_earnings_metrics_revisions_and_buyback_stages_are_retained():
    earnings = {"ticker":"600000.SS", "quarter":"2026Q3", "type":"预增", "pct_change":40}
    buyback = {"ticker":"600000.SS", "date":"2026-10-21", "plan_amt_yi":3, "progress":"董事会预案"}
    events = event_rows({"preannounce":{"top_movers":[earnings, dict(earnings),
                              dict(earnings, pct_change=60), dict(earnings, metric="扣非净利润")]},
                         "buyback":{"top":[buyback,dict(buyback, progress="实施中")]}}, "2026-10-24")
    assert len(events) == 5
    assert len({e["id"] for e in events}) == 5
    assert {e["stage"] for e in events if e["type"] == "buyback"} == {"董事会预案", "实施中"}


def test_filing_links_are_supplied_official_urls_and_metric_context_is_retained():
    from engine.china_altdata_desk import filing_href
    assert filing_href("finalpage/2026-10-15/1225607603.PDF") == "https://static.cninfo.com.cn/finalpage/2026-10-15/1225607603.PDF"
    assert filing_href("finalpage/../secret.pdf") is None
    url = "https://reportdocs.static.szse.cn/files/example.pdf"
    record = {"secCode":"920493","secName":"Example","date":"2026-10-15","pdf_url":url,
              "title":"Exchange questions","metric":"扣非净利润","report_period":"2026Q3"}
    event = event_rows({"inquiry":{"letters":[record]}},"2026-10-24")[0]
    assert event["filing_href"] == url and event["href"] is None
    assert event["reported_metric"] == "扣非净利润" and event["reported_period"] == "2026Q3"
    for unsafe in ("javascript:alert(1)","https://szse.cn.evil.test/a","https://user@szse.cn/a","http://szse.cn/a",None):
        assert filing_href(unsafe) is None


def test_safe_company_destinations():
    assert instrument_href("600000.SS") == "china_lookup.html#600000.SS"
    for ticker in ("javascript:alert(1)","600000.SS\" onclick=\"alert(1)", "//evil.test"):
        assert instrument_href(ticker) is None
