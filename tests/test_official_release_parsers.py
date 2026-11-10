from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.official_release_parsers import (
    extract_feed_entry,
    parse_actual,
    parse_claims_actual,
    parse_cpi_actual,
    parse_gdp_actual,
    parse_nfp_actual,
    parse_pce_actual,
    parse_ppi_actual,
)


BLS_CPI_ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>bls.gov:feed:cpi</id>
  <title>Consumer Price Index</title>
  <entry>
    <title>CPI for all items falls 0.4% in June; gasoline down</title>
    <link href="https://www.bls.gov/news.release/archives/cpi_07142026.htm"/>
    <id>cpi-2026_07_14__07_50_27</id>
    <content>In June, the Consumer Price Index for All Urban Consumers fell 0.4
    percent, seasonally adjusted, and rose 3.5 percent over the last 12 months,
    not seasonally adjusted. The index for all items less food and energy was
    unchanged in June (SA); up 2.6 percent over the year (NSA).</content>
    <published>2026-07-14T07:50:27.969-04:00</published>
  </entry>
  <entry>
    <title>CPI for all items rises 0.5% in May</title>
    <link href="https://www.bls.gov/news.release/archives/cpi_06102026.htm"/>
    <id>cpi-2026_06_10__08_30_00</id>
    <content>In May, the Consumer Price Index for All Urban Consumers rose 0.5
    percent, seasonally adjusted, and rose 4.2 percent over the last 12 months.
    The index for all items less food and energy increased 0.2 percent in May
    (SA); up 2.9 percent over the year (NSA).</content>
    <published>2026-06-10T08:30:00-04:00</published>
  </entry>
</feed>
"""


BEA_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item name="Gross Domestic Product by State">
      <title>Gross Domestic Product by State, 1st Quarter 2026</title>
      <link>https://www.bea.gov/news/2026/gdp-by-state</link>
      <description>State GDP release that must not match the national event.</description>
      <pubDate>Thu, 30 Jul 2026 08:30:00 EDT</pubDate>
    </item>
    <item name="GDP">
      <title>GDP (Advance Estimate), 2nd Quarter 2026</title>
      <link>www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026</link>
      <guid>www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026</guid>
      <description>Real gross domestic product (GDP) increased at an annual rate
      of 3.0 percent in the second quarter of 2026.</description>
      <data><main><current><infoDate>Q2 2026</infoDate></current></main></data>
      <pubDate>Thu, 30 Jul 2026 08:30:00 EDT</pubDate>
    </item>
    <item name="Personal Income and Outlays">
      <title>Personal Income and Outlays, June 2026</title>
      <link>https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026</link>
      <guid>https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026</guid>
      <description>Personal income increased in June.</description>
      <data><main><current><infoDate>June 2026</infoDate></current></main></data>
      <pubDate>Thu, 30 Jul 2026 08:30:00 EDT</pubDate>
    </item>
    <item name="GDP">
      <title>GDP (Third Estimate), 1st Quarter 2026</title>
      <link>https://www.bea.gov/news/2026/gdp-third-estimate-1q</link>
      <description>Real GDP increased 2.1 percent.</description>
      <pubDate>Thu, 25 Jun 2026 08:30:00 EDT</pubDate>
    </item>
  </channel>
</rss>
"""


DOL_ETA_LISTING = b"""
<div class="view-content">
  <div class="dol-feed-block">
    <div data-history-node-id="other"
         about="/newsroom/releases/eta/eta20260723-other">
      <p class="dol-date-text">July 23, 2026</p>
      <a href="/newsroom/releases/eta/eta20260723-other">
        <h3><span>Apprenticeship announcement</span></h3>
      </a>
      <div class="field--name-field-press-body"><p>Unrelated release.</p></div>
    </div>
  </div>
  <div class="dol-feed-block">
    <div data-history-node-id="185964"
         about="/newsroom/releases/eta/eta20260723">
      <p class="dol-date-text">July 23, 2026</p>
      <a href=" /newsroom/releases/eta/eta20260723 ">
        <h3><span>Unemployment Insurance Weekly Claims Report</span></h3>
      </a>
      <div class="field--name-field-press-body"><p>In the week ending July 18,
      the advance figure for seasonally adjusted initial claims was 187,000, a
      decrease of 22,000 from the previous week's revised level. The previous
      week's level was revised up by 1,000 from 208,000 to 209,000. The 4-week
      moving average was 207,500, a decrease of 7,250 from the previous week's
      revised average.</p></div>
    </div>
  </div>
</div>
"""


def test_bls_atom_selector_requires_exact_event_date() -> None:
    selected = extract_feed_entry("bls_cpi", BLS_CPI_ATOM, date(2026, 6, 10))

    assert selected is not None
    assert selected["entry_id"] == "cpi-2026_06_10__08_30_00"
    assert selected["source_url"].endswith("cpi_06102026.htm")
    assert selected["source_released_at"] == "2026-06-10T12:30:00+00:00"
    assert selected["reference_period"] == "May 2026"
    assert b"rose 0.5" in selected["body"]
    # A future calendar date must not be paired with the feed's newest item.
    assert extract_feed_entry("bls_cpi", BLS_CPI_ATOM, "2026-08-12") is None


def test_bea_rss_selects_independent_same_day_gdp_and_pce_items() -> None:
    gdp = extract_feed_entry("bea_gdp", BEA_RSS, "2026-07-30")
    pce = extract_feed_entry("bea_pce_rss", BEA_RSS, "2026-07-30")

    assert gdp is not None and pce is not None
    assert gdp["title"] == "GDP (Advance Estimate), 2nd Quarter 2026"
    assert gdp["reference_period"] == "Q2 2026"
    assert gdp["source_url"].startswith("https://www.bea.gov/")
    assert pce["title"] == "Personal Income and Outlays, June 2026"
    assert pce["reference_period"] == "June 2026"
    assert gdp["source_url"] != pce["source_url"]
    assert extract_feed_entry("bea_gdp", BEA_RSS, "2026-07-31") is None


def test_feed_selector_fails_closed_for_bad_input() -> None:
    assert extract_feed_entry("unknown", BLS_CPI_ATOM, "2026-07-14") is None
    assert extract_feed_entry("bls_ppi", BLS_CPI_ATOM, "2026-07-14") is None
    assert extract_feed_entry("bls_cpi", b"<not-closed", "2026-07-14") is None
    assert extract_feed_entry("bls_cpi", BLS_CPI_ATOM, "not-a-date") is None


def test_dol_listing_selector_uses_exact_deterministic_release_path() -> None:
    selected = extract_feed_entry("dol_claims", DOL_ETA_LISTING, "2026-07-23")

    assert selected is not None
    assert selected["entry_id"] == "/newsroom/releases/eta/eta20260723"
    assert selected["source_url"] == (
        "https://www.dol.gov/index.php/newsroom/releases/eta/eta20260723"
    )
    assert selected["source_released_at"] is None
    assert selected["title"] == "Unemployment Insurance Weekly Claims Report"
    actual = parse_actual("claims", selected["body"])
    assert actual is not None
    assert actual["initial_claims"] == 187_000
    assert actual["reference_period"] == "July 18, 2026"
    assert extract_feed_entry("dol_claims", DOL_ETA_LISTING, "2026-07-30") is None


def test_cpi_parser_extracts_headline_and_core_changes() -> None:
    selected = extract_feed_entry("bls_cpi", BLS_CPI_ATOM, "2026-07-14")
    assert selected is not None

    actual = parse_cpi_actual(selected["body"])

    assert actual is not None
    assert actual["headline_mom"] == -0.4
    assert actual["headline_yoy"] == 3.5
    assert actual["core_mom"] == 0.0
    assert actual["core_yoy"] == 2.6
    assert actual["reference_period"] == "June 2026"
    assert [row["metric_id"] for row in actual["metrics"]] == [
        "cpi_headline_mom",
        "cpi_core_mom",
        "cpi_headline_yoy",
        "cpi_core_yoy",
    ]
    assert all(row["period"] == "June 2026" for row in actual["metrics"])
    assert actual["headline_en"] == "CPI -0.4% m/m; core +0.0%"
    assert actual["headline_zh"]


# Verbatim opening paragraphs of the real October 14, 2026 CPI news release
# (September 2026 data). BLS moved the 12-month clause in front of the verb
# ("Over the last 12 months, the all items index increased 3.7 percent ...")
# and re-ordered the core label ("The all items less food and energy index
# rose 2.6 percent over the year"), which parser v1 patterns missed — the
# release sat in published_unparsed for weeks. This fixture pins the healed
# behavior against the real phrasing.
BLS_CPI_OCTOBER_ENTRY = b"""The Consumer Price Index for All Urban Consumers (CPI-U) increased 0.6 percent on a seasonally adjusted basis in
September after rising 0.4 percent in August, the U.S. Bureau of Labor Statistics reported today. Over the last 12
months, the all items index increased 3.7 percent before seasonal adjustment.

The index for gasoline rose 9.1 percent in September, accounting for over half of the monthly all items increase. The
energy index increased 5.2 percent over the month following a 2.1-percent increase in August. The shelter index rose 0.4
percent in September after rising 0.3 percent in August. The index for food was unchanged in September, as the index for
food away from home increased 0.2 percent and the index for food at home fell 0.1 percent.

The index for all items less food and energy rose 0.3 percent in September, as it did in August. Indexes that increased
over the month include recreation, used cars and trucks, education, airline fares, medical care, and apparel. Conversely,
the index for communication was among the small number of major indexes that decreased in September.

The all items index rose 3.7 percent for the 12 months ending September, a larger increase than the 3.4-percent increase
reported for the 12 months ending in August. The all items less food and energy index rose 2.6 percent over the year,
following a 2.4-percent increase over the 12 months ending August. The energy index increased 20.4 percent for the 12
months ending September. The food index increased 2.5 percent over the last year."""


def test_cpi_parser_handles_october_2026_reordered_phrasing() -> None:
    actual = parse_cpi_actual(BLS_CPI_OCTOBER_ENTRY)

    assert actual is not None
    assert actual["headline_mom"] == 0.6
    assert actual["headline_yoy"] == 3.7
    assert actual["core_mom"] == 0.3
    assert actual["core_yoy"] == 2.6
    assert actual["headline_en"] == "CPI +0.6% m/m; core +0.3%"
    assert "3.7% headline and 2.6% core" in actual["summary_en"]


def _november_cpi_document() -> bytes:
    return (Path(__file__).parent / "fixtures" / "cpi_2026_11_10_reduced.html").read_bytes()


def test_cpi_officially_unavailable_yearly_values_do_not_hide_monthly_result() -> None:
    actual = parse_cpi_actual(_november_cpi_document())

    assert actual is not None
    assert actual["reference_period"] == "October 2026"
    assert actual["headline_mom"] == 0.4
    assert actual["core_mom"] == 0.3
    assert actual["headline_yoy"] is None
    assert actual["core_yoy"] is None
    assert [(m["metric_id"], m["value"]) for m in actual["metrics"]] == [
        ("cpi_headline_mom", 0.4), ("cpi_core_mom", 0.3)
    ]
    assert {m["metric_id"] for m in actual["unavailable_metrics"]} == {
        "cpi_headline_yoy", "cpi_core_yoy"
    }
    assert all(m["reason"] == "official_prior_year_data_unavailable"
               and m["comparison_period"] == "October 2025"
               for m in actual["unavailable_metrics"])
    assert actual["monthly_comparison"] == {
        "reference_period": "September 2026", "headline_mom": 0.6, "core_mom": 0.3
    }
    assert "0.6% to 0.4%" in actual["summary_en"]
    assert "held at 0.3%" in actual["summary_en"]
    assert "not published" in actual["summary_en"]
    assert "同比" in actual["summary_zh"] and "未发布" in actual["summary_zh"]


@pytest.mark.parametrize("old,new", [
    (b"BLS cannot publish 12-month percent changes for", b"Publication explanation omitted for"),
    (b"October 2026 for indexes where", b"September 2026 for indexes where"),
    (b"October 2025 data are unavailable", b"September 2025 data are unavailable"),
    (b"12-mos.<br />ended<br />Oct. 2026", b"12-mos.<br />ended<br />Sep. 2026"),
    (b'cpi_pressa.r.1 cpi_pressa.h.1.9"><span class="datavalue">-</span>',
     b'cpi_pressa.r.1 cpi_pressa.h.1.9"><span class="datavalue">N/A</span>'),
    (b'cpi_pressa.r.1.3 cpi_pressa.h.1.9"><span class="datavalue">-</span>',
     b'cpi_pressa.r.1.3 cpi_pressa.h.1.9"><span class="datavalue">37.4</span>'),
    (b'cpi_pressa.r.1 cpi_pressa.h.1.2 cpi_pressa.h.2.8"><span class="datavalue">0.4</span>',
     b'cpi_pressa.r.1 cpi_pressa.h.1.2 cpi_pressa.h.2.8"><span class="datavalue">0.5</span>'),
    (b"index for all items less food and energy rose 0.3 percent in October",
     b"index for all items less food and energy rose N/A percent in October"),
])
def test_cpi_missingness_requires_current_series_and_monthly_evidence(old: bytes, new: bytes) -> None:
    body = _november_cpi_document()
    assert old in body
    assert parse_cpi_actual(body.replace(old, new)) is None


def test_cpi_absent_yearly_prose_is_not_official_unavailability() -> None:
    body = _november_cpi_document().split(b"<table", 1)[0]
    assert parse_cpi_actual(body) is None


@pytest.mark.parametrize("annual_prose", [
    b"The all items less food and energy index rose 2.6 percent over the year.",
    b"Over the last 12 months, the all items index increased 3.7 percent. "
    b"The all items less food and energy index rose 2.6 percent over the year.",
])
def test_cpi_conflicting_yearly_prose_and_missing_table_cell_is_rejected(annual_prose: bytes) -> None:
    body = _november_cpi_document().replace(
        b"</PRE>", annual_prose + b"</PRE>"
    )
    assert parse_cpi_actual(body) is None


def test_cpi_official_missingness_preserves_zero_monthly_value() -> None:
    body = _november_cpi_document().replace(
        b"index for all items less food and energy rose 0.3 percent in October",
        b"index for all items less food and energy was unchanged in October"
    ).replace(
        b'cpi_pressa.r.1.3 cpi_pressa.h.1.2 cpi_pressa.h.2.8"><span class="datavalue">0.3</span>',
        b'cpi_pressa.r.1.3 cpi_pressa.h.1.2 cpi_pressa.h.2.8"><span class="datavalue">0.0</span>'
    )
    actual = parse_cpi_actual(body)
    assert actual is not None and actual["core_mom"] == 0.0
    assert actual["core_yoy"] is None


def _november_cpi_feed() -> bytes:
    # Exact observed entry content; XML envelope is reduced for replay.
    return b'''<feed xmlns="http://www.w3.org/2005/Atom">
    <id>bls:feed:cpi</id><title>Consumer Price Index</title><entry>
    <title>CPI for all items increases 0.4% in October; shelter rises</title>
    <link href="https://www.bls.gov/news.release/archives/cpi_11102026.htm"/>
    <id>cpi-2026_11_10__07_55_47</id>
    <content>In October, the Consumer Price Index for All Urban Consumers rose 0.4 percent,
    seasonally adjusted (SA). The index for all items less food and energy rose 0.3
    percent in October (SA).</content><published>2026-11-10T07:55:47.272-05:00</published>
    </entry></feed>'''


def test_cpi_watcher_recovers_same_event_through_verified_detail(monkeypatch) -> None:
    import hashlib
    from datetime import datetime, timezone
    from scripts import watch_release_publications as watcher
    from engine.release_actuals import receipts_from_payload, receipt_integrity_errors

    event = {"event_id": "cpi:2026-11-10", "type": "CPI", "date": "2026-11-10",
             "time_et": "08:30", "label": "CPI", "label_zh": "消费者价格指数"}
    monkeypatch.setattr(watcher, "scheduled_releases", lambda *a, **kw: [event])
    calls = []
    document = _november_cpi_document()
    def fetch(spec, prior, timeout):
        calls.append(spec.url)
        body = _november_cpi_feed() if spec.feed_kind else document
        return {"status": 200, "body": body, "fingerprint": hashlib.sha256(body).hexdigest()}
    original_detected = "2026-11-10T13:30:39.365933+00:00"
    state = {"publications": {event["event_id"]: {
        **event, "status": "published_unparsed", "data_ready": False,
        "detected_at": original_detected, "first_seen_at": original_detected,
    }}}
    updated, payload = watcher.detect(
        now=datetime(2026, 11, 10, 13, 31, tzinfo=timezone.utc), state=state, fetcher=fetch
    )
    row = next(r for r in payload["publications"] if r["event_id"] == event["event_id"])
    assert row["status"] == "published" and row["data_ready"] is True
    assert row["detected_at"] == original_detected
    assert row["source_sha256"] == hashlib.sha256(document).hexdigest()
    assert row["source_url"].endswith("/cpi_11102026.htm")
    assert row["actual"]["reference_period"] == "October 2026"
    assert calls == ["https://www.bls.gov/feed/cpi.rss",
                     "https://www.bls.gov/news.release/archives/cpi_11102026.htm"]
    receipts = receipts_from_payload(payload)
    assert sorted((r["release"], r["actual"]) for r in receipts) == [
        ("cpi_core", 0.3), ("cpi_headline", 0.4)
    ]
    assert all(not receipt_integrity_errors(r) for r in receipts)
    assert updated["publications"][event["event_id"]]["data_ready"] is True

    # Retrying the same official document retains one event and its original
    # detection/evidence tuple rather than manufacturing a second detection.
    again, next_payload = watcher.detect(
        now=datetime(2026, 11, 10, 13, 32, tzinfo=timezone.utc), state=updated, fetcher=fetch
    )
    assert len(next_payload["publications"]) == 1
    assert next_payload["publications"][0]["detected_at"] == original_detected
    assert next_payload["publications"][0]["source_sha256"] == row["source_sha256"]
    assert receipts_from_payload(next_payload) == receipts


@pytest.mark.parametrize("old,new", [
    (b"Tuesday, November 10, 2026", b"Wednesday, October 14, 2026"),
    (b"CONSUMER PRICE INDEX - OCTOBER 2026", b"CONSUMER PRICE INDEX - SEPTEMBER 2026"),
    (b"Transmission of material in this release is embargoed until", b"Unverified header"),
])
def test_cpi_detail_header_mismatch_does_not_promote_feed(old: bytes, new: bytes) -> None:
    import hashlib
    from scripts import watch_release_publications as watcher
    spec = next(s for s in watcher.SOURCES if s.source_id == "bls_cpi")
    feed = _november_cpi_feed()
    detail = _november_cpi_document().replace(old, new)
    # A stale release may mention the next release date in its footer.
    detail += b"Next CPI release: November 10, 2026. Reference period: October 2026."
    def fetch(*args):
        return {"status": 200, "body": detail, "fingerprint": hashlib.sha256(detail).hexdigest()}
    doc, evidence, error = watcher._prepare_official_document(
        spec=spec, event={"date": "2026-11-10"},
        result={"status": 200, "body": feed}, source_state={}, state_key="test",
        fetcher=fetch, timeout=1, checked_at="2026-11-10T13:31:00+00:00"
    )
    assert evidence is True and error == "CpiDetailIdentityMismatch"
    assert doc["binding_kind"] == "feed_entry"
    assert parse_cpi_actual(doc["body"]) is None


def test_cpi_complete_feed_does_not_add_detail_dependency() -> None:
    from scripts import watch_release_publications as watcher
    spec = next(s for s in watcher.SOURCES if s.source_id == "bls_cpi")
    def unexpected_fetch(*args):
        pytest.fail("Complete CPI feed should not fetch a detail page")
    doc, evidence, error = watcher._prepare_official_document(
        spec=spec, event={"date": "2026-07-14"}, result={"status": 200, "body": BLS_CPI_ATOM},
        source_state={}, state_key="test", fetcher=unexpected_fetch, timeout=1,
        checked_at="2026-07-14T12:31:00+00:00"
    )
    assert evidence is True and error is None
    assert parse_cpi_actual(doc["body"])["core_mom"] == 0.0


@pytest.mark.parametrize("link", [
    b"https://www.bls.gov/news.release/archives/cpi_10142026.htm",
    b"https://www.bls.gov/news.release/cpi.nr0.htm",
    b"https://www.bea.gov/news.release/archives/cpi_11102026.htm",
])
def test_cpi_detail_requires_exact_dated_bls_archive(link: bytes) -> None:
    from scripts import watch_release_publications as watcher
    spec = next(s for s in watcher.SOURCES if s.source_id == "bls_cpi")
    feed = _november_cpi_feed().replace(
        b"https://www.bls.gov/news.release/archives/cpi_11102026.htm", link
    )
    def unexpected_fetch(*args):
        pytest.fail("Mismatched CPI archive must not be fetched")
    doc, evidence, error = watcher._prepare_official_document(
        spec=spec, event={"date": "2026-11-10"}, result={"status": 200, "body": feed},
        source_state={}, state_key="test", fetcher=unexpected_fetch, timeout=1,
        checked_at="2026-11-10T13:31:00+00:00"
    )
    assert evidence is True and error == "CpiDetailIdentityMismatch"
    assert doc["binding_kind"] == "feed_entry" and parse_cpi_actual(doc["body"]) is None


def test_cpi_detail_304_retries_original_reader_without_validators() -> None:
    import hashlib
    from scripts import watch_release_publications as watcher
    spec = next(s for s in watcher.SOURCES if s.source_id == "bls_cpi")
    document = _november_cpi_document()
    calls = []
    def fetch(spec, prior, timeout):
        calls.append(prior)
        return ({"status": 304} if len(calls) == 1 else
                {"status": 200, "body": document, "fingerprint": hashlib.sha256(document).hexdigest()})
    doc, evidence, error = watcher._prepare_official_document(
        spec=spec, event={"date": "2026-11-10"},
        result={"status": 200, "body": _november_cpi_feed()},
        source_state={"test:document": {"etag": "old"}}, state_key="test",
        fetcher=fetch, timeout=1, checked_at="2026-11-10T13:31:00+00:00"
    )
    assert calls == [{"etag": "old"}, {}]
    assert evidence is True and error is None and doc["binding_kind"] == "detail_document"
    assert parse_cpi_actual(doc["body"])["core_yoy"] is None


def test_cpi_preembargo_feed_and_detail_do_not_publish_early(monkeypatch) -> None:
    import hashlib
    from datetime import datetime, timezone
    from scripts import watch_release_publications as watcher
    event = {"event_id": "cpi:2026-11-10", "type": "CPI", "date": "2026-11-10",
             "time_et": "08:30", "label": "CPI"}
    monkeypatch.setattr(watcher, "scheduled_releases", lambda *a, **kw: [event])
    def fetch(spec, prior, timeout):
        body = _november_cpi_feed() if spec.feed_kind else _november_cpi_document()
        return {"status": 200, "body": body, "fingerprint": hashlib.sha256(body).hexdigest()}
    state, payload = watcher.detect(
        now=datetime(2026, 11, 10, 13, 29, 59, tzinfo=timezone.utc), state={}, fetcher=fetch
    )
    assert not payload["publications"] and not state["publications"]
    state, payload = watcher.detect(
        now=datetime(2026, 11, 10, 13, 30, tzinfo=timezone.utc), state=state, fetcher=fetch
    )
    assert len(payload["publications"]) == 1 and payload["publications"][0]["data_ready"] is True


def test_cpi_parser_never_binds_neighbouring_yearly_figure_as_core() -> None:
    # Short October-style paragraphs: the legacy 180-character window would
    # cross from the core m/m sentence into the energy sentence and bind
    # 20.4 as core YoY. The anchored October pattern must win first.
    body = (
        b"The Consumer Price Index for All Urban Consumers increased 0.6 percent on a "
        b"seasonally adjusted basis in September. Over the last 12 months, the all items "
        b"index increased 3.7 percent before seasonal adjustment. The index for all items "
        b"less food and energy rose 0.3 percent in September. The energy index increased "
        b"20.4 percent over the year. The all items less food and energy index rose 2.6 "
        b"percent over the year."
    )

    actual = parse_cpi_actual(body)

    assert actual is not None
    assert actual["headline_yoy"] == 3.7
    assert actual["core_yoy"] == 2.6


def test_cpi_parser_accepts_sibling_core_yearly_phrasings() -> None:
    body = (
        b"The Consumer Price Index for All Urban Consumers increased 0.6 percent on a "
        b"seasonally adjusted basis in September. Over the last 12 months, the all items "
        b"index increased 3.7 percent before seasonal adjustment. The index for all items "
        b"less food and energy rose 0.3 percent in September. The all items less food and "
        b"energy index rose 2.6 percent over the last year."
    )

    actual = parse_cpi_actual(body)

    assert actual is not None
    assert actual["core_yoy"] == 2.6


@pytest.mark.parametrize("headline", [
    b"Over the last 12 months, the all items index increased 3.7 percent before seasonal adjustment. ",
    b"The index for all items rose 3.7 percent over the last 12 months. ",
])
@pytest.mark.parametrize("core_yearly", [
    b"",
    b"The all items less food and energy index rose N/A percent over the year.",
    b"The index for all items less food and energy rose N/A percent over the year.",
    b"The all items less food and energy index rose 2.6 over the year.",
])
def test_cpi_missing_core_yearly_never_uses_neighbouring_index(headline, core_yearly):
    body = (
        b"The Consumer Price Index for All Urban Consumers increased 0.6 percent on a "
        b"seasonally adjusted basis in September. " + headline
        + b"The index for all items less food and energy rose 0.3 percent in September. "
        + b"The energy index increased 20.4 percent over the year. " + core_yearly
    )
    assert parse_cpi_actual(body) is None


@pytest.mark.parametrize("label", [
    b"The all items less food and energy index",
    b"The index for all items less food and energy",
])
@pytest.mark.parametrize(("change", "expected"), [
    (b"was unchanged", 0.0),
    (b"fell 0.2 percent", -0.2),
    (b"rose 2.6 percent", 2.6),
])
def test_cpi_core_yearly_clause_binds_zero_negative_and_positive(label, change, expected):
    body = (
        b"The Consumer Price Index for All Urban Consumers increased 0.6 percent on a "
        b"seasonally adjusted basis in September. Over the last 12 months, the all items "
        b"index increased 3.7 percent before seasonal adjustment. The index for all items "
        b"less food and energy rose 0.3 percent in September. The energy index increased "
        b"20.4 percent over the year. " + label + b" " + change + b" over the year."
    )
    actual = parse_cpi_actual(body)
    assert actual is not None
    assert actual["core_yoy"] == expected
    assert next(row["value"] for row in actual["metrics"] if row["metric_id"] == "cpi_core_yoy") == expected
    assert "20.4" not in actual["summary_en"]
    assert "20.4" not in actual["summary_zh"]


PPI_ENTRY = b"""
PPI for final demand declines 0.3% in June; goods fall 1.4%, services increase 0.2%
The Producer Price Index for final demand fell 0.3 percent in June. Prices for
final demand goods decreased 1.4 percent, and the index for final demand services
moved up 0.2 percent. Prices for final demand increased 5.5 percent for the
12 months ended in June.
"""


def test_ppi_parser_extracts_goods_services_and_yearly_change() -> None:
    actual = parse_ppi_actual(PPI_ENTRY)

    assert actual is not None
    assert actual["headline_mom"] == -0.3
    assert actual["goods_mom"] == -1.4
    assert actual["services_mom"] == 0.2
    assert actual["headline_yoy"] == 5.5
    assert actual["reference_period"] is None
    assert {row["metric_id"] for row in actual["metrics"]} == {
        "ppi_headline_mom",
        "ppi_headline_yoy",
        "ppi_goods_mom",
        "ppi_services_mom",
    }
    assert "PPI -0.3%" in actual["headline_en"]
    assert actual["summary_zh"]


@pytest.mark.parametrize(
    ("release", "payroll_change", "unemployment_rate"),
    [
        (
            b"""Both total nonfarm payroll employment (+57,000) and the
            unemployment rate (4.2 percent) changed little in June.""",
            57_000,
            4.2,
        ),
        (
            b"""Total nonfarm payroll employment edged down by 92,000 in
            February, and the unemployment rate changed little at 4.4
            percent.""",
            -92_000,
            4.4,
        ),
    ],
)
def test_nfp_parser_handles_parenthetical_and_directional_payrolls(
    release: bytes,
    payroll_change: int,
    unemployment_rate: float,
) -> None:
    actual = parse_nfp_actual(release)

    assert actual is not None
    assert actual["payroll_change"] == payroll_change
    assert actual["unemployment_rate"] == unemployment_rate
    assert [row["metric_id"] for row in actual["metrics"]] == [
        "nfp_payroll_change",
        "nfp_unemployment_rate",
    ]
    assert actual["headline_en"]
    assert actual["headline_zh"]


def test_nfp_reference_period_never_captures_article_after_in() -> None:
    actual = parse_nfp_actual(
        b"""Total nonfarm payroll employment (+57,000) in the establishment
        survey changed little. The unemployment rate was 4.2 percent.
        Reference period: July 2026"""
    )

    assert actual is not None
    assert actual["reference_period"] == "July 2026"
    assert all(metric["period"] == "July 2026" for metric in actual["metrics"])


GDP_PAGE = b"""
<html>
  <head><title>GDP (Advance Estimate), Second Quarter 2026</title></head>
  <body>
    <p>Real gross domestic product (GDP) increased at an annual rate of 3.0
    percent in the second quarter of 2026 (April, May, and June), according to
    the advance estimate released today by the U.S. Bureau of Economic
    Analysis. In the first quarter, real GDP increased 2.1 percent.</p>
  </body>
</html>
"""


def test_gdp_page_parser_extracts_vintage_current_and_prior() -> None:
    actual = parse_gdp_actual(GDP_PAGE)

    assert actual is not None
    assert actual["real_gdp_annualized"] == 3.0
    assert actual["prior_real_gdp_annualized"] == 2.1
    assert actual["reference_period"] == "Q2 2026"
    assert actual["vintage"] == "advance"
    assert actual["metrics"] == [
        {
            "metric_id": "gdp_real_annualized",
            "value": 3.0,
            "unit": "percent_annualized",
            "period": "Q2 2026",
        }
    ]
    assert "Q2 2026" in actual["headline_en"]
    assert actual["summary_zh"]


PCE_PAGE = b"""
<html>
  <head><title>Personal Income and Outlays, June 2026</title></head>
  <body>
    <h1>Personal Income and Outlays, June 2026</h1>
    <p>From the preceding month, the PCE price index decreased 0.1 percent.
    Excluding food and energy, the PCE price index increased 0.2 percent.</p>
    <p>From the same month one year ago, the PCE price index increased 2.3
    percent. Excluding food and energy, the PCE price index increased 2.7
    percent.</p>
    <p>Personal income increased $90.0 billion in June.</p>
  </body>
</html>
"""


def test_pce_page_parser_extracts_monthly_and_yearly_inflation() -> None:
    actual = parse_pce_actual(PCE_PAGE)

    assert actual is not None
    assert actual["headline_mom"] == -0.1
    assert actual["core_mom"] == 0.2
    assert actual["headline_yoy"] == 2.3
    assert actual["core_yoy"] == 2.7
    assert actual["reference_period"] == "June 2026"
    assert len(actual["metrics"]) == 4
    assert actual["metrics"][0]["metric_id"] == "pce_headline_mom"
    assert actual["headline_zh"]


CLAIMS_PAGE = b"""
<html>
  <head><title>Unemployment Insurance Weekly Claims - July 23, 2026</title></head>
  <body>
    <p>In the week ending July 18, the advance figure for seasonally adjusted
    initial claims was 217,000, a decrease of 4,000 from the previous week's
    revised level. The previous week's level was revised up by 1,000 from
    220,000 to 221,000. The 4-week moving average was 224,500, a decrease of
    5,000 from the previous week's revised average.</p>
  </body>
</html>
"""


def test_claims_page_parser_extracts_level_change_prior_and_average() -> None:
    actual = parse_claims_actual(CLAIMS_PAGE)

    assert actual is not None
    assert actual["initial_claims"] == 217_000
    assert actual["change"] == -4_000
    assert actual["prior_initial_claims"] == 221_000
    assert actual["four_week_average"] == 224_500
    assert actual["reference_period"] == "July 18, 2026"
    assert [row["metric_id"] for row in actual["metrics"]] == [
        "claims_initial",
        "claims_change",
        "claims_four_week_avg",
    ]
    assert actual["headline_en"] == "Initial claims 217k (-4k)"
    assert actual["headline_zh"]


@pytest.mark.parametrize("parser_name", ["cpi", "ppi", "nfp", "gdp", "pce", "claims"])
def test_named_dispatch_is_fail_closed_and_bilingual(parser_name: str) -> None:
    assert parse_actual(parser_name, b"not an official release") is None
    assert parse_actual("not-a-parser", b"anything") is None
