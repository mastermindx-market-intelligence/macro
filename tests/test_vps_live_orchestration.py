from __future__ import annotations

import email.message
import fcntl
import shlex
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
from datetime import datetime, timedelta, timezone
from importlib import import_module, util as importlib_util
from pathlib import Path
from types import SimpleNamespace

import pytest
import pandas as pd

from engine.release_actuals import receipts_from_payload
from scripts import build_intraday_flow as bif
from scripts import vps_live_orchestrator as vlo
from scripts import watch_release_publications as wrp
from scripts.build_intraday_flow_quotes import build_payload as build_flow_quotes
from scripts.check_vps_live_health import evaluate as evaluate_live_health

FOMC_STATEMENT = """
    <html><body>
    <p>July 29, 2026</p>
    <p>The Federal Open Market Committee approved the following statement
    for release by a 9 – 3 vote:</p>
    <p>The Committee decided to maintain the target range for the federal
    funds rate at 3-1/2 to 3-3/4 percent.</p>
    <p>Voting against the monetary policy action were Beth M. Hammack,
    Neel Kashkari, and Lorie K. Logan, who preferred to raise the target
    range for the federal funds rate by 1/4 percentage point at this
    meeting.</p>
    </body></html>
""".encode()

CPI_ENTRY_TEXT = """
Consumer Price Index for All Urban Consumers rose 0.2 percent in June 2026.
The index for all items rose 2.7 percent over the last 12 months.
The index for all items less food and energy rose 0.3 percent in June
(seasonally adjusted); the index for all items less food and energy rose
2.9 percent over the year.
"""

# A feed entry is publication evidence, NOT an authoritative CPI facts document.
# The watcher must fetch this dated BLS release, verify its period and then parse.
CPI_JULY_14_PAGE = b"""
<html><body><h1>CONSUMER PRICE INDEX - JUNE 2026</h1>
<p>The Consumer Price Index for All Urban Consumers (CPI-U) increased 0.2 percent
on a seasonally adjusted basis in June after rising 0.1 percent in May.</p>
<p>Over the last 12 months, the all items index increased 2.7 percent
before seasonal adjustment.</p>
<p>The index for all items less food and energy rose 0.3 percent in June.</p>
<p>The index for all items less food and energy rose 2.9 percent over the
past 12 months.</p></body></html>
"""

BEA_JULY_30_FEED = b"""
<rss version="2.0"><channel>
  <item name="GDP">
    <title>GDP (Advance Estimate), 2nd Quarter 2026</title>
    <link>https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026</link>
    <guid>https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026</guid>
    <description>Real GDP release for the second quarter of 2026.</description>
    <data><main><current><infoDate>Q2 2026</infoDate></current></main></data>
    <pubDate>Thu, 30 Jul 2026 08:30:00 -0400</pubDate>
  </item>
  <item name="Personal Income and Outlays">
    <title>Personal Income and Outlays, June 2026</title>
    <link>https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026</link>
    <guid>https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026</guid>
    <description>Personal income and PCE release for June 2026.</description>
    <data><main><current><infoDate>June 2026</infoDate></current></main></data>
    <pubDate>Thu, 30 Jul 2026 08:30:00 -0400</pubDate>
  </item>
</channel></rss>
"""

BEA_ADVANCED_FEED = BEA_JULY_30_FEED.replace(
    b"</channel>",
    b"""
  <item name="GDP">
    <title>GDP, Third Quarter 2026</title>
    <link>https://www.bea.gov/news/2026/gdp-third-quarter-2026</link>
    <description>Later release retained beside the July archive entries.</description>
    <pubDate>Fri, 07 Aug 2026 08:30:00 -0400</pubDate>
  </item>
</channel>""",
)

GDP_JULY_30_PAGE = b"""
<html><body><h1>GDP (Advance Estimate), Second Quarter 2026</h1>
<p>Real gross domestic product (GDP) increased at an annual rate of 3.0
percent in the second quarter of 2026, according to the advance estimate.
In the first quarter, real GDP increased 2.1 percent.</p>
</body></html>
"""

PCE_JULY_30_PAGE = b"""
<html><body><h1>Personal Income and Outlays, June 2026</h1>
<p>From the preceding month, the PCE price index decreased 0.1 percent.
Excluding food and energy, the PCE price index increased 0.2 percent.</p>
<p>From the same month one year ago, the PCE price index increased 2.3
percent. Excluding food and energy, the PCE price index increased 2.7 percent.</p>
<p>Personal income increased $90.0 billion in June.</p>
</body></html>
"""

CLAIMS_JULY_30_PAGE = b"""
<html><body><h1>Unemployment Insurance Weekly Claims - July 30, 2026</h1>
<p>In the week ending July 25, the advance figure for seasonally adjusted
initial claims was 219,000, an increase of 2,000 from the previous week's
revised level. The 4-week moving average was 221,500.</p>
</body></html>
"""

DOL_JULY_30_LISTING = b"""
<div class="view-content"><div class="dol-feed-block">
  <div data-history-node-id="fixture"
       about="/newsroom/releases/eta/eta20260730">
    <p class="dol-date-text">July 30, 2026</p>
    <a href="/newsroom/releases/eta/eta20260730">
      <h3><span>Unemployment Insurance Weekly Claims Report</span></h3>
    </a>
    <div class="field--name-field-press-body">
      <p>In the week ending July 25, the advance figure for seasonally adjusted
      initial claims was 219,000, an increase of 2,000 from the previous week's
      revised level. The 4-week moving average was 221,500.</p>
    </div>
  </div>
</div></div>
"""


def _bls_cpi_feed(*, event_date: str, content: str = CPI_ENTRY_TEXT) -> bytes:
    return f"""
    <feed xmlns="http://www.w3.org/2005/Atom">
      <id>bls.gov:feed:cpi</id>
      <title>Consumer Price Index</title>
      <entry>
        <title>Consumer Price Index — June 2026</title>
        <id>https://www.bls.gov/news.release/archives/cpi_{datetime.strptime(event_date, '%Y-%m-%d'):%m%d%Y}.htm</id>
        <published>{event_date}T07:50:00-04:00</published>
        <link href="https://www.bls.gov/news.release/archives/cpi_{datetime.strptime(event_date, '%Y-%m-%d'):%m%d%Y}.htm"/>
        <content type="html"><![CDATA[{content}]]></content>
      </entry>
    </feed>
    """.encode()


def _http_result(body: bytes, *, last_modified: str = "Tue, 14 Jul 2026 12:30:00 GMT"):
    return {
        "status": 200,
        "body": body,
        "fingerprint": __import__("hashlib").sha256(body).hexdigest(),
        "etag": '"fixture"',
        "last_modified": last_modified,
        "content_type": "text/html",
    }


def _cpi_feed_or_detail(spec, *, event_date: str):
    # The producer must not promote facts from a feed summary.  Return the
    # current dated release document on the second HTTP request.
    if spec.url.endswith("cpi_07142026.htm"):
        return _http_result(CPI_JULY_14_PAGE)
    return _http_result(_bls_cpi_feed(event_date=event_date))


def _release_detail_outage(monkeypatch):
    """A BLS entry is available immediately, but its dated document returns 429."""
    from urllib.error import HTTPError

    start = datetime(2026, 7, 14, 12, 31, tzinfo=timezone.utc)
    key = "cpi:2026-07-14"
    archive = "https://www.bls.gov/news.release/archives/cpi_07142026.htm"
    calls = []
    blocked = [True]
    monkeypatch.setattr(wrp, "SOURCES", tuple(s for s in wrp.SOURCES if s.source_id == "bls_cpi"))

    def fetch(spec, prior, timeout):
        calls.append(spec.url)
        if spec.feed_kind:
            return _http_result(_bls_cpi_feed(event_date="2026-07-14"))
        assert spec.url == archive
        if blocked[0]:
            err = HTTPError(archive, 429, "rate limited", {"Retry-After": "60"}, None)
            err.retry_after_s = 60  # _fetch converts the actual response header.
            raise err
        return {**_http_result(CPI_JULY_14_PAGE), "url": archive}

    state, _ = wrp.detect(now=start, state={}, fetcher=fetch)
    assert state["publications"][key]["status"] == "published_unparsed"
    return start, key, archive, calls, blocked, fetch, state


def test_archive_rate_limit_survives_restart_during_hot_window(monkeypatch):
    start, key, archive, calls, blocked, fetch, state = _release_detail_outage(monkeypatch)
    for seconds in (2, 4, 15, 59):
        state, _ = wrp.detect(now=start + timedelta(seconds=seconds),
                              state=json.loads(json.dumps(state)), fetcher=fetch)
    assert calls.count(archive) == 1
    blocked[0] = False
    state, _ = wrp.detect(now=start + timedelta(seconds=60), state=state, fetcher=fetch)
    assert calls.count(archive) == 2
    assert state["publications"][key]["data_ready"] is True


def test_feed_only_cpi_recovers_after_date_ages_out(monkeypatch):
    start, key, archive, calls, blocked, fetch, state = _release_detail_outage(monkeypatch)
    before = state["publications"][key].copy()
    assert before["source_url"].endswith("/feed/cpi.rss")  # digest is for RSS bytes
    blocked[0] = False
    calls.clear()
    state, _ = wrp.detect(now=start + timedelta(days=18), state=state, fetcher=fetch)
    assert calls == [archive]
    row = state["publications"][key]
    assert row["data_ready"] is True and row["status"] == "published"
    assert row["source_url"] == row["actual"]["source_url"] == archive
    assert row["reference_period"] == before["reference_period"] == "June 2026"
    assert row["detected_at"] == before["detected_at"]
    assert row["source_sha256"] != before["source_sha256"]


@pytest.mark.parametrize("observed_link", [
    None, "https://www.bls.gov/news.release/archives/cpi_06102026.htm",
    "https://www.bls.gov.evil.test/news.release/archives/cpi_07142026.htm",
])
def test_feed_only_cpi_never_guesses_an_unobserved_archive(monkeypatch, observed_link):
    start, key, _, calls, blocked, fetch, state = _release_detail_outage(monkeypatch)
    state["publications"][key]["feed_entry_document_url"] = observed_link
    calls.clear()
    blocked[0] = False
    state, _ = wrp.detect(now=start + timedelta(days=18), state=state, fetcher=fetch)
    assert not calls
    assert state["publications"][key]["data_ready"] is False


def test_release_watcher_seeds_before_release_then_detects_change():
    before = datetime(2026, 7, 14, 12, 25, tzinfo=timezone.utc)  # 08:25 ET
    after = datetime(2026, 7, 14, 12, 31, tzinfo=timezone.utc)   # 08:31 ET

    def seed_fetcher(spec, prior, timeout):
        assert spec.source_id == "bls_cpi"
        return _http_result(_bls_cpi_feed(event_date="2026-06-10"))

    state, payload = wrp.detect(now=before, state={}, fetcher=seed_fetcher)
    assert [row["type"] for row in payload["due"]] == ["CPI"]
    assert payload["publications"] == []

    def changed_fetcher(spec, prior, timeout):
        if spec.feed_kind:
            assert prior["fingerprint"]
        return _cpi_feed_or_detail(spec, event_date="2026-07-14")

    state, payload = wrp.detect(now=after, state=state, fetcher=changed_fetcher)
    assert len(payload["publications"]) == 1
    publication = payload["publications"][0]
    assert publication["type"] == "CPI"
    assert publication["status"] == "published"
    assert publication["data_ready"] is True
    assert publication["actual"]["headline_mom"] == 0.2
    assert publication["actual"]["core_mom"] == 0.3
    assert publication["source_url"].startswith(
        "https://www.bls.gov/news.release/archives/cpi_"
    )
    assert publication["source_released_at"] == "2026-07-14T12:30:00+00:00"
    assert publication["source_time_basis"] == "scheduled_embargo_floor"
    assert publication["is_context_only"] is True
    # The faster display path must remain admissible to the existing
    # downstream canonical first-print reconciliation, not die on a parser bump.
    cpi_receipts = [row for row in receipts_from_payload(payload) if row["release"].startswith("cpi_")]
    assert {row["release"] for row in cpi_receipts} == {"cpi_headline", "cpi_core"}
    assert all(row["parser_version"] == 2 for row in cpi_receipts)


def test_release_watcher_cold_start_recovers_from_official_date():
    after = datetime(2026, 7, 14, 12, 35, tzinfo=timezone.utc)

    def fetcher(spec, prior, timeout):
        return _cpi_feed_or_detail(spec, event_date="2026-07-14")

    _, payload = wrp.detect(now=after, state={}, fetcher=fetcher)
    assert [row["type"] for row in payload["publications"]] == ["CPI"]
    assert payload["publications"][0]["data_ready"] is True


def test_release_watcher_does_not_bootstrap_old_miss_as_live_failure():
    now = datetime(2026, 7, 28, 12, 1, tzinfo=timezone.utc)

    def unexpected_fetch(*_args, **_kwargs):
        raise AssertionError("an untracked historical release must not be fetched")

    state, payload = wrp.detect(now=now, state={}, fetcher=unexpected_fetch)

    assert all(
        row["event_id"] != "claims:2026-07-23"
        for row in payload["events"]
    )
    assert all(
        row["status"] != "verification_delayed"
        for row in payload["events"]
    )
    expected_coverage = {
        event_type: now.isoformat()
        for event_type in wrp.RESULT_EVENT_TYPES
    }
    assert state["coverage_started_at_by_type"] == expected_coverage
    assert payload["coverage_started_at_by_type"] == expected_coverage

    next_state, next_payload = wrp.detect(
        now=now + timedelta(minutes=1),
        state=state,
        fetcher=unexpected_fetch,
    )
    assert next_state["coverage_started_at_by_type"] == expected_coverage
    assert next_payload["coverage_started_at_by_type"] == expected_coverage


def test_release_watcher_migration_matches_july_30_production_bootstrap():
    now = datetime(2026, 7, 30, 4, 7, tzinfo=timezone.utc)
    fomc_publication = {
        "event_id": "fomc:2026-07-29",
        "type": "FOMC",
        "date": "2026-07-29",
        "time_et": "14:00",
        "status": "published",
        "data_ready": True,
        "actual": {"action": "hold"},
    }
    state = {
        "schema": "release_publication_state.v2",
        "sources": {},
        "publications": {"fomc:2026-07-29": fomc_publication},
    }

    def fetcher(spec, prior, timeout):
        assert spec.source_id == "fed_fomc"
        return _http_result(
            FOMC_STATEMENT,
            last_modified="Wed, 29 Jul 2026 18:00:15 GMT",
        )

    _, payload = wrp.detect(now=now, state=state, fetcher=fetcher)

    event_ids = {row["event_id"] for row in payload["events"]}
    assert "fomc:2026-07-29" in event_ids
    assert "claims:2026-07-23" not in event_ids
    assert all(
        row["status"] != "verification_delayed"
        for row in payload["events"]
    )


def test_new_non_fomc_coverage_immediately_recovers_outside_fast_window():
    after_fast_window = datetime(2026, 7, 14, 20, 7, tzinfo=timezone.utc)
    calls: list[str] = []

    def fetcher(spec, prior, timeout):
        calls.append(spec.source_id)
        return _cpi_feed_or_detail(spec, event_date="2026-07-14")

    _, payload = wrp.detect(
        now=after_fast_window,
        state={},
        fetcher=fetcher,
    )

    publication = next(
        row for row in payload["publications"] if row["type"] == "CPI"
    )
    assert publication["status"] == "published"
    assert publication["data_ready"] is True
    assert calls == ["bls_cpi", "bls_cpi"]


def test_release_watcher_retains_precoverage_publication_evidence():
    now = datetime(2026, 7, 28, 12, 1, tzinfo=timezone.utc)
    publication = {
        "event_id": "claims:2026-07-23",
        "type": "CLAIMS",
        "date": "2026-07-23",
        "time_et": "08:30",
        "status": "published",
        "data_ready": True,
        "actual": {"initial_claims": 217_000},
    }
    state = {
        "schema": "release_publication_state.v2",
        "sources": {},
        "publications": {"claims:2026-07-23": publication},
    }

    def unexpected_fetch(*_args, **_kwargs):
        raise AssertionError("retained historical evidence must not be refetched")

    _, payload = wrp.detect(now=now, state=state, fetcher=unexpected_fetch)

    retained = next(
        row
        for row in payload["events"]
        if row["event_id"] == "claims:2026-07-23"
    )
    assert retained["status"] == "published"
    assert retained["actual"]["initial_claims"] == 217_000


def _july_30_fetcher(spec, prior, timeout):
    if spec.source_id in ("bea_gdp", "bea_pce") and spec.url.endswith("rss.xml"):
        return _http_result(
            BEA_JULY_30_FEED,
            last_modified="Thu, 30 Jul 2026 12:30:01 GMT",
        )
    if spec.source_id == "bea_gdp":
        return _http_result(
            GDP_JULY_30_PAGE,
            last_modified="Thu, 30 Jul 2026 12:30:02 GMT",
        )
    if spec.source_id == "bea_pce":
        return _http_result(
            PCE_JULY_30_PAGE,
            last_modified="Thu, 30 Jul 2026 12:30:03 GMT",
        )
    if spec.source_id == "dol_claims":
        assert spec.url == "https://www.dol.gov/index.php/newsroom/releases/eta"
        return _http_result(
            DOL_JULY_30_LISTING,
            last_modified="Thu, 30 Jul 2026 12:30:04 GMT",
        )
    raise AssertionError(f"unexpected source {spec.source_id}: {spec.url}")


def test_three_simultaneous_releases_publish_independent_verified_results():
    after = datetime(2026, 7, 30, 12, 31, tzinfo=timezone.utc)
    calls: list[str] = []

    def fetcher(spec, prior, timeout):
        calls.append(spec.url)
        return _july_30_fetcher(spec, prior, timeout)

    state, payload = wrp.detect(now=after, state={}, fetcher=fetcher)

    publications = {row["type"]: row for row in payload["publications"]}
    assert set(publications) == {"GDP", "PCE", "CLAIMS"}
    assert all(row["status"] == "published" for row in publications.values())
    assert all(row["data_ready"] is True for row in publications.values())
    assert publications["GDP"]["actual"]["real_gdp_annualized"] == 3.0
    assert publications["PCE"]["actual"]["core_mom"] == 0.2
    assert publications["CLAIMS"]["actual"]["initial_claims"] == 219_000
    assert len({row["event_id"] for row in publications.values()}) == 3
    assert calls.count("https://apps.bea.gov/rss/rss.xml") == 1
    assert set(state["publications"]) == {
        "gdp:2026-07-30",
        "pce:2026-07-30",
        "claims:2026-07-30",
    }
    assert all(
        row["source_released_at"] == "2026-07-30T12:30:00+00:00"
        for event_type, row in publications.items()
        if event_type in ("GDP", "PCE")
    )


def test_bea_verified_document_bindings_survive_feed_304_and_reobservation():
    first_tick = datetime(2026, 7, 30, 12, 31, tzinfo=timezone.utc)
    state, payload = wrp.detect(now=first_tick, state={}, fetcher=_july_30_fetcher)
    first = {
        row["type"]: row
        for row in payload["publications"]
        if row["type"] in ("GDP", "PCE")
    }

    page_sha = {
        "GDP": __import__("hashlib").sha256(GDP_JULY_30_PAGE).hexdigest(),
        "PCE": __import__("hashlib").sha256(PCE_JULY_30_PAGE).hexdigest(),
    }
    feed_sha = __import__("hashlib").sha256(BEA_JULY_30_FEED).hexdigest()
    assert first["GDP"]["source_url"] != first["PCE"]["source_url"]
    assert all(
        row["actual"]["source_url"] == row["source_url"] for row in first.values()
    )
    assert first["GDP"]["source_sha256"] == page_sha["GDP"]
    assert first["PCE"]["source_sha256"] == page_sha["PCE"]
    assert page_sha["GDP"] != page_sha["PCE"] != feed_sha

    bound_fields = (
        "actual",
        "source_url",
        "content_sha256",
        "source_sha256",
        "source_released_at",
        "source_time_basis",
        "reference_period",
        "verified_at",
    )

    def binding(row):
        return {field: row.get(field) for field in bound_fields}

    expected = {event_type: binding(row) for event_type, row in first.items()}
    feed_calls: list[str] = []

    def not_modified_fetcher(spec, prior, timeout):
        if spec.source_id in ("bea_gdp", "bea_pce") and spec.url.endswith("rss.xml"):
            feed_calls.append(spec.url)
            assert prior["fingerprint"] == feed_sha
            return {
                "status": 304,
                "body": b"",
                "fingerprint": prior["fingerprint"],
                "etag": prior["etag"],
                "last_modified": prior["last_modified"],
                "content_type": prior["content_type"],
            }
        if spec.source_id in ("bea_gdp", "bea_pce"):
            raise AssertionError("a feed 304 must not fetch a release detail page")
        return _july_30_fetcher(spec, prior, timeout)

    state, payload = wrp.detect(
        now=first_tick + timedelta(minutes=1),
        state=state,
        fetcher=not_modified_fetcher,
    )
    after_304 = {
        row["type"]: row
        for row in payload["publications"]
        if row["type"] in ("GDP", "PCE")
    }
    assert feed_calls == ["https://apps.bea.gov/rss/rss.xml"]
    assert {
        event_type: binding(row) for event_type, row in after_304.items()
    } == expected
    assert all(row["source_sha256"] != feed_sha for row in after_304.values())

    _, payload = wrp.detect(
        now=first_tick + timedelta(minutes=2),
        state=state,
        fetcher=_july_30_fetcher,
    )
    reobserved = {
        row["type"]: row
        for row in payload["publications"]
        if row["type"] in ("GDP", "PCE")
    }
    assert {
        event_type: binding(row) for event_type, row in reobserved.items()
    } == expected


def test_bea_known_feed_bound_state_repairs_only_from_successful_detail_page(
    tmp_path: Path,
):
    first_tick = datetime(2026, 7, 30, 12, 31, tzinfo=timezone.utc)
    state, payload = wrp.detect(now=first_tick, state={}, fetcher=_july_30_fetcher)
    feed_sha = __import__("hashlib").sha256(BEA_JULY_30_FEED).hexdigest()
    recorded_bad_sha = (
        "29ae0bad7d568ca7ea59be2f74461b5dcf5da4393ff816544254cd47507f13e1"
    )
    page_sha = __import__("hashlib").sha256(PCE_JULY_30_PAGE).hexdigest()
    assert feed_sha != recorded_bad_sha
    pce_key = "pce:2026-07-30"
    corrupted = state["publications"][pce_key]
    assert corrupted["actual"]["source_url"] == corrupted["source_url"]
    corrupted["content_sha256"] = recorded_bad_sha
    corrupted["source_sha256"] = recorded_bad_sha

    bad_payload = {
        **payload,
        "publications": list(state["publications"].values()),
    }
    bad_receipt = next(
        row
        for row in receipts_from_payload(
            bad_payload,
            defects_path=tmp_path / "no-defects.json",
        )
        if row["release"] == "pce_headline"
    )

    def failed_detail_fetcher(spec, prior, timeout):
        if spec.source_id == "bea_pce" and not spec.url.endswith("rss.xml"):
            raise TimeoutError("detail unavailable")
        return _july_30_fetcher(spec, prior, timeout)

    state, failed_payload = wrp.detect(
        now=first_tick + timedelta(minutes=1),
        state=state,
        fetcher=failed_detail_fetcher,
    )
    still_bound_to_feed = next(
        row for row in failed_payload["publications"] if row["event_id"] == pce_key
    )
    assert still_bound_to_feed["source_sha256"] == recorded_bad_sha
    assert still_bound_to_feed["actual"] == corrupted["actual"]

    state, repaired_payload = wrp.detect(
        now=first_tick + timedelta(minutes=2),
        state=state,
        fetcher=_july_30_fetcher,
    )
    repaired = next(
        row for row in repaired_payload["publications"] if row["event_id"] == pce_key
    )
    repaired_receipt = next(
        row
        for row in receipts_from_payload(repaired_payload)
        if row["release"] == "pce_headline"
    )

    assert repaired["source_sha256"] == page_sha
    assert repaired["content_sha256"] == page_sha
    assert repaired["actual"]["source_url"] == repaired["source_url"]
    assert repaired_receipt["source_sha256"] == page_sha
    assert repaired_receipt["receipt_id"] != bad_receipt["receipt_id"]


def test_bea_feed_entry_parse_cannot_promote_when_detail_fetch_fails(monkeypatch):
    after = datetime(2026, 7, 30, 12, 31, tzinfo=timezone.utc)
    original_parse = wrp._parse_actual

    def false_positive_feed_parser(spec, body):
        if spec.source_id == "bea_pce":
            return {
                "headline_mom": -0.1,
                "core_mom": 0.2,
                "reference_period": "2026-06",
            }
        return original_parse(spec, body)

    monkeypatch.setattr(wrp, "_parse_actual", false_positive_feed_parser)

    def failed_detail_fetcher(spec, prior, timeout):
        if spec.source_id == "bea_pce" and not spec.url.endswith("rss.xml"):
            raise TimeoutError("detail unavailable")
        return _july_30_fetcher(spec, prior, timeout)

    _, payload = wrp.detect(now=after, state={}, fetcher=failed_detail_fetcher)
    pce = next(row for row in payload["publications"] if row["type"] == "PCE")
    pce_receipts = [
        receipt
        for receipt in receipts_from_payload(payload)
        if receipt["release"] in {"pce_headline", "pce_core"}
    ]

    assert pce["status"] == "published_unparsed"
    assert pce["data_ready"] is False
    assert "actual" not in pce
    assert pce["source_url"] == "https://apps.bea.gov/rss/rss.xml"
    assert pce["source_sha256"] == __import__("hashlib").sha256(
        BEA_JULY_30_FEED
    ).hexdigest()
    assert pce_receipts == []


def _aged_known_bad_pce_state():
    first_tick = datetime(2026, 7, 30, 12, 31, tzinfo=timezone.utc)
    state, _ = wrp.detect(now=first_tick, state={}, fetcher=_july_30_fetcher)
    pce = state["publications"]["pce:2026-07-30"]
    recorded_bad_sha = (
        "29ae0bad7d568ca7ea59be2f74461b5dcf5da4393ff816544254cd47507f13e1"
    )
    pce["source_sha256"] = recorded_bad_sha
    pce["content_sha256"] = recorded_bad_sha
    # Mirror the two immutable July 30 production receipt identities governed
    # by official_actual_defects.json; the later detail replay corrects core.
    pce["actual"]["core_mom"] = 0.1
    return state


def test_aged_governed_pce_defect_forces_feed_and_detail_repair():
    state = _aged_known_bad_pce_state()
    repair_tick = datetime(2026, 8, 10, 16, 7, tzinfo=timezone.utc)
    calls = []

    def repair_fetcher(spec, prior, timeout):
        calls.append((spec.url, dict(prior)))
        assert prior == {}
        if spec.source_id == "bea_pce" and spec.url.endswith("rss.xml"):
            return _http_result(BEA_ADVANCED_FEED)
        if spec.source_id == "bea_pce":
            return _http_result(PCE_JULY_30_PAGE)
        raise AssertionError(f"unexpected repair source: {spec.url}")

    state, payload = wrp.detect(
        now=repair_tick,
        state=state,
        fetcher=repair_fetcher,
    )
    repaired = next(
        row for row in payload["publications"] if row["event_id"] == "pce:2026-07-30"
    )
    repair = state[wrp.DEFECT_REPAIR_STATE_KEY]["pce:2026-07-30"]
    page_sha = __import__("hashlib").sha256(PCE_JULY_30_PAGE).hexdigest()
    feed_sha = __import__("hashlib").sha256(BEA_ADVANCED_FEED).hexdigest()
    eligible = [
        receipt
        for receipt in receipts_from_payload(payload)
        if receipt["release"] in {"pce_headline", "pce_core"}
    ]

    assert feed_sha != repair["recorded_source_sha256"]
    assert calls == [
        ("https://apps.bea.gov/rss/rss.xml", {}),
        (
            "https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026",
            {},
        ),
    ]
    assert repaired["source_sha256"] == page_sha
    assert repaired["content_sha256"] == page_sha
    assert repaired["actual"]["source_url"] == repaired["source_url"]
    assert repair["status"] == "repaired"
    assert repair["attempts"] == 1
    assert repair["attempt_limit"] == 3
    assert repair["repaired_source_sha256"] == page_sha
    assert len(repair["defect_receipt_ids"]) == 2
    assert {receipt["source_sha256"] for receipt in eligible} == {page_sha}
    assert {receipt["release"] for receipt in eligible} == {
        "pce_headline",
        "pce_core",
    }


def test_aged_unlisted_binding_is_not_admitted_to_repair_queue():
    state = _aged_known_bad_pce_state()
    pce = state["publications"]["pce:2026-07-30"]
    pce["source_sha256"] = "f" * 64
    pce["content_sha256"] = "f" * 64
    calls = []

    def unexpected_fetcher(spec, prior, timeout):
        calls.append(spec.url)
        raise AssertionError(f"unlisted binding fetched: {spec.url}")

    state, _ = wrp.detect(
        now=datetime(2026, 8, 10, 16, 7, tzinfo=timezone.utc),
        state=state,
        fetcher=unexpected_fetcher,
    )

    assert calls == []
    assert state[wrp.DEFECT_REPAIR_STATE_KEY] == {}


def test_governed_defect_loader_handles_json_list_root(tmp_path: Path, monkeypatch):
    defects_path = tmp_path / "official_actual_defects.json"
    defects_path.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(wrp, "OFFICIAL_ACTUAL_DEFECTS_PATH", defects_path)

    assert wrp._governed_source_binding_defects() == []


def test_aged_governed_pce_defect_failure_is_quarantined_and_bounded():
    state = _aged_known_bad_pce_state()
    repair_tick = datetime(2026, 8, 10, 16, 7, tzinfo=timezone.utc)
    calls = []

    def failed_repair_fetcher(spec, prior, timeout):
        calls.append((spec.url, dict(prior)))
        assert prior == {}
        if spec.source_id == "bea_pce" and spec.url.endswith("rss.xml"):
            return _http_result(BEA_ADVANCED_FEED)
        if spec.source_id == "bea_pce":
            raise TimeoutError("detail unavailable")
        raise AssertionError(f"unexpected repair source: {spec.url}")

    state, payload = wrp.detect(
        now=repair_tick,
        state=state,
        fetcher=failed_repair_fetcher,
    )
    repair = state[wrp.DEFECT_REPAIR_STATE_KEY]["pce:2026-07-30"]
    bad_sha = repair["recorded_source_sha256"]
    quarantined = next(
        row for row in payload["publications"] if row["event_id"] == "pce:2026-07-30"
    )
    assert repair["status"] == "retry_wait"
    assert repair["attempts"] == 1
    assert repair["next_attempt_at"] == (
        repair_tick + timedelta(minutes=60)
    ).isoformat()
    assert quarantined["source_sha256"] == bad_sha
    assert not any(
        receipt["release"] in {"pce_headline", "pce_core"}
        for receipt in receipts_from_payload(payload)
    )

    calls_before_backoff = len(calls)
    state, _ = wrp.detect(
        now=repair_tick + timedelta(minutes=30),
        state=state,
        fetcher=failed_repair_fetcher,
    )
    assert len(calls) == calls_before_backoff
    assert state[wrp.DEFECT_REPAIR_STATE_KEY]["pce:2026-07-30"]["attempts"] == 1

    state, _ = wrp.detect(
        now=repair_tick + timedelta(minutes=60),
        state=state,
        fetcher=failed_repair_fetcher,
    )
    second = state[wrp.DEFECT_REPAIR_STATE_KEY]["pce:2026-07-30"]
    assert second["attempts"] == 2
    assert second["next_attempt_at"] == (
        repair_tick + timedelta(minutes=180)
    ).isoformat()

    state, _ = wrp.detect(
        now=repair_tick + timedelta(minutes=180),
        state=state,
        fetcher=failed_repair_fetcher,
    )
    exhausted = state[wrp.DEFECT_REPAIR_STATE_KEY]["pce:2026-07-30"]
    assert exhausted["status"] == "exhausted"
    assert exhausted["attempts"] == wrp.DEFECT_REPAIR_MAX_ATTEMPTS
    assert exhausted["next_attempt_at"] is None
    assert exhausted["last_error"] == "TimeoutError"
    assert len(calls) == wrp.DEFECT_REPAIR_MAX_ATTEMPTS * 2

    calls_at_exhaustion = len(calls)
    state, _ = wrp.detect(
        now=repair_tick + timedelta(days=1),
        state=state,
        fetcher=failed_repair_fetcher,
    )
    assert len(calls) == calls_at_exhaustion
    assert state[wrp.DEFECT_REPAIR_STATE_KEY]["pce:2026-07-30"] == exhausted


def test_one_same_day_parser_failure_does_not_block_sibling_results():
    after = datetime(2026, 7, 30, 12, 31, tzinfo=timezone.utc)

    def fetcher(spec, prior, timeout):
        if spec.source_id == "bea_pce" and not spec.url.endswith("rss.xml"):
            return _http_result(
                b"<html>Personal Income and Outlays parser format changed</html>",
                last_modified="Thu, 30 Jul 2026 12:30:03 GMT",
            )
        return _july_30_fetcher(spec, prior, timeout)

    _, payload = wrp.detect(now=after, state={}, fetcher=fetcher)
    publications = {row["type"]: row for row in payload["publications"]}

    assert publications["GDP"]["data_ready"] is True
    assert publications["CLAIMS"]["data_ready"] is True
    assert publications["PCE"]["status"] == "published_unparsed"
    assert publications["PCE"]["data_ready"] is False
    assert publications["PCE"]["parser"]["name"] == "pce"


def test_gdp_feed_item_cannot_cross_publish_same_day_pce():
    after = datetime(2026, 7, 30, 12, 31, tzinfo=timezone.utc)
    gdp_only_feed = BEA_JULY_30_FEED.replace(
        BEA_JULY_30_FEED[
            BEA_JULY_30_FEED.index(b'<item name="Personal Income and Outlays">'):
            BEA_JULY_30_FEED.index(b"</channel>")
        ],
        b"",
    )

    def fetcher(spec, prior, timeout):
        if spec.source_id in ("bea_gdp", "bea_pce") and spec.url.endswith("rss.xml"):
            return _http_result(gdp_only_feed)
        if spec.source_id == "bea_gdp":
            return _http_result(GDP_JULY_30_PAGE)
        if spec.source_id == "dol_claims":
            return _http_result(DOL_JULY_30_LISTING)
        raise AssertionError(f"PCE detail should not be fetched: {spec.url}")

    _, payload = wrp.detect(now=after, state={}, fetcher=fetcher)
    publications = {row["type"]: row for row in payload["publications"]}
    assert set(publications) == {"GDP", "CLAIMS"}
    pce = next(row for row in payload["events"] if row["type"] == "PCE")
    assert pce["status"] == "awaiting_publication"


def test_non_fomc_unparsed_release_retries_and_self_heals_next_day():
    retry_tick = datetime(2026, 7, 15, 12, 45, tzinfo=timezone.utc)
    event = {
        "event_id": "cpi:2026-07-14",
        "type": "CPI",
        "date": "2026-07-14",
        "time_et": "08:30",
        "label": "CPI (consumer prices)",
        "label_zh": "消费者物价指数（CPI）",
        "status": "published_unparsed",
        "data_ready": False,
        "detected_at": "2026-07-14T12:31:00+00:00",
    }
    state = {
        "schema": "release_publication_state.v2",
        "sources": {},
        "publications": {"cpi:2026-07-14": event},
    }

    def fetcher(spec, prior, timeout):
        assert spec.source_id == "bls_cpi"
        return _cpi_feed_or_detail(spec, event_date="2026-07-14")

    _, payload = wrp.detect(now=retry_tick, state=state, fetcher=fetcher)
    recovered = next(row for row in payload["publications"] if row["type"] == "CPI")
    assert recovered["status"] == "published"
    assert recovered["data_ready"] is True
    assert recovered["actual"]["headline_mom"] == 0.2


def test_event_id_is_canonical_even_for_same_type_and_date():
    first = {"event_id": "claims:2026-07-30:advance", "type": "CLAIMS", "date": "2026-07-30"}
    second = {"event_id": "claims:2026-07-30:revision", "type": "CLAIMS", "date": "2026-07-30"}
    assert wrp._event_key(first) != wrp._event_key(second)  # noqa: SLF001


def test_schedule_coverage_is_explicit_and_fails_visible_at_exhaustion():
    current = wrp.schedule_coverage(datetime(2026, 7, 30).date())
    assert current["status"] == "ok"
    assert current["next_by_type"]["NFP"] == "2026-08-07"
    assert current["next_by_type"]["FOMC"] == "2026-09-16"

    exhausted = wrp.schedule_coverage(datetime(2027, 12, 31).date())
    assert exhausted["status"] == "incomplete"
    assert {"FOMC", "CPI", "NFP", "GDP", "PCE"}.issubset(
        exhausted["missing_or_too_distant"]
    )


def test_fomc_watcher_publishes_verified_decision_facts():
    after = datetime(2026, 7, 29, 18, 0, 30, tzinfo=timezone.utc)  # 14:00:30 ET

    def fetcher(spec, prior, timeout):
        assert spec.source_id == "fed_fomc"
        assert spec.url.endswith("/monetary20260729a.htm")
        assert prior == {}
        return _http_result(
            FOMC_STATEMENT,
            last_modified="Wed, 29 Jul 2026 18:00:15 GMT",
        )

    _, payload = wrp.detect(now=after, state={}, fetcher=fetcher)
    assert payload["schema"] == "release_publications.v2"
    assert [row["type"] for row in payload["due"]] == ["FOMC"]
    publication = payload["publications"][0]
    assert publication["status"] == "published"
    assert publication["data_ready"] is True
    assert publication["scheduled_at"] == "2026-07-29T14:00:00-04:00"
    assert publication["source_released_at"] == "2026-07-29T18:00:15+00:00"
    assert publication["parser"] == {"name": "fomc", "version": 2}
    assert publication["source_url"].endswith("/monetary20260729a.htm")
    assert publication["actual"] == {
        "kind": "policy_rate",
        "action": "hold",
        "target_low": 3.5,
        "target_high": 3.75,
        "unit": "percent",
        "vote_for": 9,
        "vote_against": 3,
        "dissent_preference": "hike",
        "dissent_basis_points": 25,
        "headline_en": "Fed holds at 3.50%–3.75%",
        "headline_zh": "美联储维持利率在 3.50%–3.75%",
        "summary_en": (
            "Fed holds at 3.50%–3.75% on a 9–3 vote. "
            "Dissenters preferred a rate increase of 25 basis points."
        ),
        "summary_zh": (
            "美联储维持利率在 3.50%–3.75%，表决结果为 9–3。 "
            "反对者倾向于加息 25 个基点。"
        ),
        "source_url": (
            "https://www.federalreserve.gov/newsevents/pressreleases/"
            "monetary20260729a.htm"
        ),
    }
    event = next(row for row in payload["events"] if row["type"] == "FOMC")
    assert event["status"] == "published"
    assert event["actual"]["action"] == "hold"
    assert all(row["event_id"] != event["event_id"] for row in payload["upcoming"])
    assert payload["poll_window"]["per_type_after_min"]["FOMC"] == 1440


def test_fomc_lifecycle_stops_calling_past_event_upcoming_on_source_delay():
    after = datetime(2026, 7, 29, 18, 2, tzinfo=timezone.utc)  # 14:02 ET

    def unavailable(spec, prior, timeout):
        raise RuntimeError("official source unavailable")

    _, payload = wrp.detect(now=after, state={}, fetcher=unavailable)
    event = next(row for row in payload["events"] if row["type"] == "FOMC")
    assert event["status"] == "awaiting_publication"
    assert payload["publications"] == []
    assert payload["source_health"][0]["status"] == "error"
    assert payload["source_health"][0]["error"] == "RuntimeError"
    assert "official source unavailable" not in json.dumps(payload)


def test_fomc_parser_handles_page_visible_before_scheduled_time():
    before = datetime(2026, 7, 29, 17, 59, 30, tzinfo=timezone.utc)
    after = datetime(2026, 7, 29, 18, 0, 1, tzinfo=timezone.utc)
    statement = (
        b"July 29, 2026 Federal Open Market Committee decided to maintain the "
        b"target range for the federal funds rate at 3-1/2 to 3-3/4 percent."
    )

    calls: list[bool] = []

    def fetcher(spec, prior, timeout):
        calls.append(bool(prior))
        if prior:
            return {
                "status": 304,
                "body": b"",
                "fingerprint": prior["fingerprint"],
                "etag": prior["etag"],
                "last_modified": prior["last_modified"],
                "content_type": prior["content_type"],
            }
        return _http_result(
            statement,
            last_modified="Wed, 29 Jul 2026 17:59:00 GMT",
        )

    state, payload = wrp.detect(now=before, state={}, fetcher=fetcher)
    assert payload["publications"] == []
    _, payload = wrp.detect(now=after, state=state, fetcher=fetcher)
    # The post-time conditional request is realistically a 304. The watcher
    # retries once without validators so the deterministic parser gets bytes.
    assert calls == [False, True, False]
    assert payload["publications"][0]["actual"]["target_high"] == 3.75


def test_fomc_unparseable_official_statement_is_not_reported_as_healthy():
    after = datetime(2026, 7, 29, 18, 3, 30, tzinfo=timezone.utc)
    changed_format = (
        b"<html><body>July 29, 2026 Federal Open Market Committee "
        b"target range decision expressed in an unsupported format.</body></html>"
    )

    def fetcher(spec, prior, timeout):
        return _http_result(
            changed_format,
            last_modified="Wed, 29 Jul 2026 18:00:15 GMT",
        )

    _, payload = wrp.detect(now=after, state={}, fetcher=fetcher)
    publication = payload["publications"][0]
    assert publication["status"] == "published_unparsed"
    assert publication["data_ready"] is False
    event = next(row for row in payload["events"] if row["type"] == "FOMC")
    assert event["status"] == "published_unparsed"

    health = _healthy_vps_status()
    health["checks"]["release_publications"].update(
        {
            "event_status": {"published_unparsed": 1, "scheduled": 3},
            "max_publication_lag_min": 3.5,
        }
    )
    assert any(
        "official publication detected" in failure
        and "remain unparsed 3.5m after schedule" in failure
        for failure in evaluate_live_health(health, now=after)
    )


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 7, 30, 1, 0, tzinfo=timezone.utc),  # Jul 29 21:00 ET
        datetime(2026, 7, 30, 5, 0, tzinfo=timezone.utc),  # Jul 30 01:00 ET
    ],
)
def test_fomc_cold_start_recovers_through_24_hour_watch_window(now):
    def fetcher(spec, prior, timeout):
        assert spec.source_id == "fed_fomc"
        return _http_result(
            FOMC_STATEMENT,
            last_modified="Wed, 29 Jul 2026 18:00:15 GMT",
        )

    _, payload = wrp.detect(now=now, state={}, fetcher=fetcher)
    publication = next(row for row in payload["publications"] if row["type"] == "FOMC")
    assert publication["data_ready"] is True
    assert publication["actual"]["action"] == "hold"


def test_fomc_missing_result_stays_delayed_after_24_hour_poll_window():
    after_window = datetime(2026, 7, 30, 18, 1, tzinfo=timezone.utc)
    state = {
        "schema": "release_publication_state.v2",
        "coverage_started_at_by_type": {
            "FOMC": "2026-07-29T17:30:00+00:00",
        },
        "sources": {},
        "publications": {},
    }

    def no_fomc_fetch(spec, prior, timeout):
        assert spec.source_id != "fed_fomc"
        return _http_result(b"unrelated same-day release page")

    _, payload = wrp.detect(now=after_window, state=state, fetcher=no_fomc_fetch)
    event = next(
        row for row in payload["events"] if row["event_id"] == "fomc:2026-07-29"
    )
    assert event["status"] == "verification_delayed"
    assert all(row["type"] != "FOMC" for row in payload["due"])


def test_fomc_unparsed_result_stays_unhealthy_after_24_hours():
    after_window = datetime(2026, 7, 30, 18, 1, tzinfo=timezone.utc)
    event = {
        "event_id": "fomc:2026-07-29",
        "type": "FOMC",
        "date": "2026-07-29",
        "time_et": "14:00",
        "label": "FOMC rate decision",
        "label_zh": "美联储议息会议",
        "status": "published_unparsed",
        "data_ready": False,
        "detected_at": "2026-07-29T18:00:30+00:00",
    }
    state = {
        "schema": "release_publication_state.v2",
        "sources": {},
        "publications": {"FOMC:2026-07-29": event},
    }

    def no_fomc_fetch(spec, prior, timeout):
        assert spec.source_id != "fed_fomc"
        return _http_result(b"unrelated same-day release page")

    _, payload = wrp.detect(now=after_window, state=state, fetcher=no_fomc_fetch)
    retained = next(
        row for row in payload["events"] if row["event_id"] == "fomc:2026-07-29"
    )
    assert retained["status"] == "published_unparsed"
    assert any(
        row["event_id"] == "fomc:2026-07-29"
        for row in payload["publications"]
    )

    health = _healthy_vps_status()
    health["checks"]["release_publications"].update(
        {
            "event_status": {"published_unparsed": 1},
            "unparsed_publications": 1,
            "max_publication_lag_min": 1441,
        }
    )
    assert any(
        "remain unparsed" in failure
        for failure in evaluate_live_health(health, now=after_window)
    )


def test_fomc_unparsed_result_retries_and_recovers_after_fast_window():
    retry_tick = datetime(2026, 7, 30, 18, 15, tzinfo=timezone.utc)
    event = {
        "event_id": "fomc:2026-07-29",
        "type": "FOMC",
        "date": "2026-07-29",
        "time_et": "14:00",
        "label": "FOMC rate decision",
        "label_zh": "美联储议息会议",
        "status": "published_unparsed",
        "data_ready": False,
        "detected_at": "2026-07-29T18:00:30+00:00",
    }
    state = {
        "schema": "release_publication_state.v2",
        "sources": {},
        "publications": {"FOMC:2026-07-29": event},
    }

    def fetcher(spec, prior, timeout):
        if spec.source_id == "fed_fomc":
            return _http_result(
                FOMC_STATEMENT,
                last_modified="Wed, 29 Jul 2026 18:00:15 GMT",
            )
        return _http_result(b"unrelated same-day release page")

    _, payload = wrp.detect(now=retry_tick, state=state, fetcher=fetcher)
    recovered = next(
        row for row in payload["publications"]
        if row["event_id"] == "fomc:2026-07-29"
    )
    assert recovered["status"] == "published"
    assert recovered["data_ready"] is True
    assert recovered["actual"]["action"] == "hold"


def test_atomic_publish_rejects_invalid_json(tmp_path: Path):
    source = tmp_path / "bad.json"
    target = tmp_path / "public" / "bad.json"
    source.write_text("{bad")
    with pytest.raises(ValueError, match="invalid JSON"):
        vlo.atomic_publish(source, target)
    assert not target.exists()


def test_atomic_publish_makes_browser_artifact_readable(tmp_path: Path):
    source = tmp_path / "good.json"
    target = tmp_path / "public" / "good.json"
    source.write_text('{"ok":true}')
    vlo.atomic_publish(source, target)
    assert target.stat().st_mode & 0o777 == 0o644


def test_quote_snapshot_quality_rejects_empty_or_low_coverage(tmp_path: Path):
    path = tmp_path / "quotes.json"
    path.write_text('{"quotes":{},"meta":{"requested":25,"resolved":0}}')
    assert "quality too low" in (
        vlo.quote_snapshot_error(path, min_resolved=5, min_coverage=0.2) or ""
    )
    path.write_text(
        json.dumps(
            {
                "quotes": {f"S{i}": {"price": i + 1} for i in range(5)},
                "meta": {"requested": 25, "resolved": 5},
            }
        )
    )
    assert vlo.quote_snapshot_error(
        path, min_resolved=5, min_coverage=0.2
    ) is None


def test_board_quote_filter_keeps_only_leaders_with_real_prices():
    payload = build_flow_quotes(
        {"leaders": [{"ticker": "AMD"}, {"ticker": "AAPL"}, {"ticker": "MISS"}]},
        {
            "ts": 123,
            "asof": "2026-08-20T16:00:00+00:00",
            "source": "snapshot",
            "quotes": {
                "AAPL": {"price": 200.0},
                "AMD": {"price": "150.25"},
                "MISS": {"price": None},
                "SPY": {"price": 700.0},
            },
            "meta": {"requested": 2000, "resolved": 1900},
        },
    )
    assert set(payload["quotes"]) == {"AAPL", "AMD"}
    assert payload["meta"]["requested"] == 3
    assert payload["meta"]["resolved"] == 2
    assert payload["meta"]["upstream_resolved"] == 1900


def test_datetime_index_named_ts_is_normalized_for_today_bars(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    now_et = pd.Timestamp.now(tz="America/New_York").normalize()
    index = pd.DatetimeIndex(
        [now_et + pd.Timedelta(hours=10), now_et + pd.Timedelta(hours=11)],
        name="ts",
    ).tz_convert("UTC")
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000.0, 2000.0],
        },
        index=index,
    )
    intraday = tmp_path / "intraday"
    intraday.mkdir()
    (intraday / "AAPL.parquet").touch()
    monkeypatch.setattr(bif.pd, "read_parquet", lambda _: frame.copy())

    rows = bif._today_bars("AAPL", tmp_path)

    assert len(rows) == 2
    assert rows[-1]["close"] == 102.0


def test_flow_pulse_quality_rejects_age_fresh_no_data(tmp_path: Path):
    path = tmp_path / "flow_pulse.json"
    path.write_text(json.dumps({
        "mode": "no_data", "n_tickers": 2,
        "tickers": [
            {"ticker": "AAPL", "bars_today": 0},
            {"ticker": "AMD", "bars_today": 0},
        ],
    }))
    assert "mode=no_data" in (vlo.flow_pulse_error(path, min_coverage=0.8) or "")
    path.write_text(json.dumps({
        "mode": "fastpath", "n_tickers": 2, "n_universe": 2,
        "source_asof": "2026-10-13T14:10:00+00:00",
        "tickers": [
            {"ticker": "AAPL", "bars_today": 4},
            {"ticker": "AMD", "bars_today": 4},
        ],
    }))
    assert vlo.flow_pulse_error(path, min_coverage=0.8) is None


def test_intraday_flow_symbols_resolves_exact_disclosed_board(tmp_path: Path):
    path = tmp_path / "base.json"
    path.write_text(json.dumps({
        "leaders": [
            {"ticker": "SNOW"},
            {"symbol": "aapl"},
            {"ticker": "SNOW"},
            {"ticker": ""},
        ],
    }))
    assert vlo.intraday_flow_symbols(path) == ["AAPL", "SNOW"]


def test_bars_lane_requests_exact_intraday_flow_symbols(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    monkeypatch.setattr(vlo, "intraday_flow_symbols", lambda path: ["AAPL", "SNOW"])
    calls = []
    orch = vlo.Orchestrator(
        live_dir=tmp_path / "public" / "live",
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
    )

    def module(name, module, args, **kwargs):
        calls.append((name, module, args))
        return vlo.TaskResult(name, "ok", 0.01)

    monkeypatch.setattr(orch, "module", module)
    orch.bars()

    assert calls[0][0:2] == ("intraday_bars", "scripts.build_polygon_intraday")
    assert calls[0][2][calls[0][2].index("--symbols") + 1] == "AAPL,SNOW"
    assert calls[1][0:2] == ("intraday_flow", "scripts.build_intraday_flow")


def test_command_can_publish_private_state_outside_public_root(tmp_path: Path):
    source = tmp_path / "stage" / "quotes_full.json"
    source.parent.mkdir()

    def runner(*args, **kwargs):
        source.write_text('{"quotes":{}}')
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    orch = vlo.Orchestrator(
        live_dir=tmp_path / "public",
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        runner=runner,
    )
    target = orch.state_dir / "quotes_full.json"
    result = orch.command(
        "private_snapshot",
        ["fixture"],
        outputs=((source, target),),
        timeout=1,
    )
    assert result.status == "ok"
    assert result.published == ("quotes_full.json",)
    assert target.stat().st_mode & 0o777 == 0o600


def test_snapshot_lane_requests_private_quote_provenance(tmp_path: Path):
    orch = vlo.Orchestrator(
        live_dir=tmp_path / "public" / "live",
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
    )
    calls: list[tuple[str, str, list[str]]] = []

    def module(name, module, args, **kwargs):
        calls.append((name, module, list(args)))
        if name == "full_quotes":
            target = orch.state_dir / "quotes_full.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(
                    {
                        "quotes": {"AAPL": {"price": 100.0}},
                        "meta": {"requested": 100, "resolved": 100},
                    }
                )
            )
        return vlo.TaskResult(name, "ok", 0.0)

    orch.module = module  # type: ignore[method-assign]
    orch.snapshot()

    full = next(call for call in calls if call[0] == "full_quotes")
    assert full[0:2] == ("full_quotes", "scripts.build_live_quotes")
    assert "--private-provenance" in full[2]
    assert [name for name, _module, args in calls
            if "--private-provenance" in args] == ["full_quotes"]


def test_private_full_snapshot_does_not_disclose_provenance_in_public_intraday_output(
    tmp_path: Path, monkeypatch,
):
    from scripts import build_intraday_flow_quotes as public_quotes
    from scripts import build_live_quotes as full_quotes

    raw = {
        "REAL": {"price": 100.0, "quote_ts": "2026-10-08T14:30:00+00:00",
                 "quote_ts_synthetic": False, "source": "fixture",
                 "price_basis": "trade", "prev_close": 99.0, "currency": "USD",
                 "delay_min": 1.0, "day_volume": 1000, "day_high": 101.0,
                 "day_low": 98.0},
        "SYNTH": {"price": 50.0, "quote_ts": "2026-10-08T14:30:01+00:00",
                  "quote_ts_synthetic": True, "source": "fixture",
                  "price_basis": "day", "prev_close": 50.0, "currency": "USD",
                  "delay_min": 0.0},
        "UNDISCLOSED": {"price": 25.0, "quote_ts": "2026-10-08T14:30:00+00:00",
                        "quote_ts_synthetic": False},
    }
    snapshot = {
        "ts": 1791469800000, "asof": "2026-10-08T14:30:00+00:00",
        "source": "snapshot",
        "quotes": full_quotes.to_worker_quotes(raw, include_private_provenance=True),
        "meta": {"requested": 3, "resolved": 3},
    }
    snapshot["quotes"]["REAL"]["internal_owner_receipt"] = "private-sentinel"
    original_snapshot = json.loads(json.dumps(snapshot))
    base_path = tmp_path / "base.json"
    private_path = tmp_path / "quotes_full.json"
    public_path = tmp_path / "public" / "intraday_quotes.json"
    base_path.write_text(json.dumps({"leaders": [{"ticker": "REAL"},
                                               {"ticker": "SYNTH"}]}))
    private_path.write_text(json.dumps(snapshot))
    private_bytes = private_path.read_bytes()
    monkeypatch.setattr(sys, "argv", ["build_intraday_flow_quotes", "--base",
                       str(base_path), "--quotes", str(private_path), "--out",
                       str(public_path)])

    assert public_quotes.main() == 0
    published = json.loads(public_path.read_text())

    assert set(published["quotes"]) == {"REAL", "SYNTH"}
    for row in published["quotes"].values():
        assert "quote_ts" not in row
        assert "quote_ts_synthetic" not in row
        assert "internal_owner_receipt" not in row
    assert published["quotes"]["REAL"] == {
        "price": 100.0, "ts": 1791469800000, "source": "fixture", "basis": "trade",
        "prevClose": 99.0, "changePct": 1.01, "currency": "USD", "delayMin": 1.0,
        "vol": 1000, "hi": 101.0, "lo": 98.0,
    }
    assert published["quotes"]["SYNTH"] == {
        "price": 50.0, "ts": None, "source": "fixture", "basis": "day",
        "prevClose": 50.0, "changePct": 0.0, "currency": "USD", "delayMin": 0.0,
        "tsSynthetic": True,
    }
    assert published["ts"] == snapshot["ts"]
    assert published["asof"] == snapshot["asof"]
    assert published["meta"]["requested"] == published["meta"]["resolved"] == 2
    assert json.loads(private_path.read_text()) == original_snapshot
    assert private_path.read_bytes() == private_bytes


def test_command_does_not_publish_stale_required_output(tmp_path: Path):
    source = tmp_path / "stage" / "overlay.json"
    target = tmp_path / "public" / "overlay.json"
    source.parent.mkdir()
    source.write_text('{"stale":true}')
    target.parent.mkdir()
    target.write_text('{"last_good":true}')

    def runner(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="silent no-op", stderr="")

    orch = vlo.Orchestrator(
        live_dir=tmp_path / "public",
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        runner=runner,
    )
    result = orch.command(
        "silent_noop",
        ["fixture"],
        outputs=((source, target),),
        timeout=1,
    )
    assert result.status == "failed"
    assert result.published == ()
    assert json.loads(target.read_text()) == {"last_good": True}


def test_main_returns_nonzero_when_lane_has_failed_task(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    class FakeOrchestrator:
        def __init__(self, **kwargs):
            self.results = [vlo.TaskResult("fixture", "failed", 0.01)]

        def fast(self):
            return None

        def write_status(self, lane, started_at):
            return None

    lock = (tmp_path / "fast.lock").open("a+")
    monkeypatch.setattr(vlo, "_lock_lane", lambda state_dir, lane: lock)
    monkeypatch.setattr(vlo, "Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "vps_live_orchestrator",
            "--lane",
            "fast",
            "--live-dir",
            str(tmp_path / "live"),
            "--state-dir",
            str(tmp_path / "state"),
            "--data-dir",
            str(tmp_path / "data"),
        ],
    )
    assert vlo.main() == 1


def test_fast_lane_staggers_overlay_and_risk(tmp_path: Path):
    even = vlo.Orchestrator(
        live_dir=tmp_path / "live",
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        now=datetime(2026, 7, 20, 14, 2, tzinfo=timezone.utc),
    )
    even_names: list[str] = []
    even.module = lambda name, *args, **kwargs: even_names.append(name) or vlo.TaskResult(  # type: ignore[method-assign]
        name, "ok", 0.0
    )
    even.fast()
    assert "live_overlay" in even_names
    assert "risk_state" not in even_names

    odd = vlo.Orchestrator(
        live_dir=tmp_path / "live2",
        state_dir=tmp_path / "state2",
        data_dir=tmp_path / "data2",
        now=datetime(2026, 7, 20, 14, 3, tzinfo=timezone.utc),
    )
    odd_names: list[str] = []
    odd.module = lambda name, *args, **kwargs: odd_names.append(name) or vlo.TaskResult(  # type: ignore[method-assign]
        name, "ok", 0.0
    )
    odd.fast()
    assert "risk_state" in odd_names
    assert "turn_notifications" in odd_names
    assert "live_overlay" not in odd_names


def test_display_lane_publishes_a_tile_only_snapshot(tmp_path: Path):
    """The display universe now carries the scraped board leg beside the ~35 macro
    tiles, so `resolved/requested` is no longer a ~1.0 ratio: a Yahoo outage on the
    A-share leg alone lands a perfectly good tile-only snapshot near 21%. Under the
    old 0.20 floor that (plus any one missing tile) REFUSED the publish and froze
    the served quotes.json for every page — the tiles included. Pin the display
    lane's own thresholds against that shape."""
    validator = None
    orch = vlo.Orchestrator(
        live_dir=tmp_path / "live",
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        now=datetime(2026, 8, 13, 2, 4, tzinfo=timezone.utc),
    )

    def capture(name, *args, **kwargs):
        nonlocal validator
        if name == "display_quotes":
            validator = kwargs.get("validator")
        return vlo.TaskResult(name, "ok", 0.0)

    orch.module = capture  # type: ignore[method-assign]
    orch.fast()
    assert validator is not None, "display_quotes lane no longer runs"

    path = tmp_path / "quotes.json"
    # tiles resolve, every board symbol fails -> must still publish
    path.write_text(
        json.dumps({"quotes": {f"T{i}": {"price": i + 1.0} for i in range(34)},
                    "meta": {"requested": 168, "resolved": 34}})
    )
    assert validator(path) is None
    # a collapsed fetch is still refused
    path.write_text(json.dumps({"quotes": {}, "meta": {"requested": 168, "resolved": 0}}))
    assert "quality too low" in (validator(path) or "")


def test_status_is_external_and_lane_scoped(tmp_path: Path):
    orch = vlo.Orchestrator(
        live_dir=tmp_path / "live",
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
    )
    orch.results.append(vlo.TaskResult("fixture", "ok", 0.01, returncode=0))
    orch.write_status("fast", datetime.now(timezone.utc))
    public = json.loads((tmp_path / "live" / "orchestrator_status.json").read_text())
    assert public["lanes"]["fast"]["ok"] is True
    assert public["lanes"]["fast"]["tasks"][0]["name"] == "fixture"


def test_cutover_guards_keep_manual_recovery():
    root = Path(__file__).resolve().parents[1]
    # live-quotes.yml is NOT in this list (2026-07-30). It is the only writer of
    # the `live-data` branch, and that branch feeds three consumers the VPS does
    # not serve: the browser's fallback, marketing-publish's tape gate, and the
    # Hot Tape radar. Gating it on the cutover variable is what froze the branch on
    # 2026-07-27 and starved the radar on 2026-07-29, so the gate is gone and the
    # job always runs — which preserves manual recovery trivially rather than
    # conditionally. The cadence invariant that replaces this assertion lives in
    # test_marketing_forward_booking.test_live_quotes_outpaces_its_tightest_consumer.
    for name in ("intraday-fastpath.yml", "intraday.yml", "btc-live.yml"):
        text = (root / ".github" / "workflows" / name).read_text()
        assert "vars.VPS_LIVE_PRIMARY != 'true'" in text
        assert "github.event_name == 'workflow_dispatch'" in text
    live_quotes = (root / ".github" / "workflows" / "live-quotes.yml").read_text()
    assert "vars.VPS_LIVE_PRIMARY" not in live_quotes, (
        "live-quotes must stay ungated — it is the sole writer of `live-data`, and "
        "every time it has been gated the tape gate and the radar went dark")
    external = (root / ".github" / "workflows" / "vps-live-heartbeat.yml").read_text()
    assert "runs-on: ubuntu-latest" in external
    assert "vars.VPS_LIVE_PRIMARY == 'true'" in external
    self_heal = (root / ".github" / "workflows" / "regime-self-heal.yml").read_text()
    assert "vars.VPS_LIVE_PRIMARY == 'true'" in self_heal
    assert "scripts.refresh_regime_if_stale" in self_heal
    assert "data/regime/latest.json data/market_state/latest.json data/reflexes/" in self_heal
    legacy = (root / ".github" / "workflows" / "heartbeat.yml").read_text()
    assert 'VPS_LIVE_PRIMARY: ${{ vars.VPS_LIVE_PRIMARY }}' in legacy


def test_live_setup_retires_legacy_only_after_smoke_and_timer_enable():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app" / "deploy" / "live-setup.sh").read_text()
    smoke = text.index("systemctl start macro-live-fast.service")
    enable = text.index("systemctl enable --now")
    retire = text.index('grep -v "macro-live')
    assert smoke < enable < retire
    assert "previous units and timer intent restored" in text
    assert 'systemd-analyze verify "${unit_sources[@]}"' in text


def test_live_rollback_is_non_destructive_and_restores_legacy_writer():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app" / "deploy" / "live-rollback.sh").read_text()
    assert 'systemctl disable "$unit"' in text
    assert 'stop_live_unit "macro-live-$lane.service"' in text
    assert 'flock -n 9' in text
    assert "systemctl stop" in text
    assert "/usr/local/bin/macro-live" in text
    assert 'mv "$PUBLIC_DIR" "$backup_dir"' in text
    assert "rm -rf" not in text


#: The instant every caller of :func:`_healthy_vps_status` grades against. Named so
#: the prophet_live clocks below are stamped RELATIVE to it: that grader reads absolute
#: `pass_ts`/`quote_asof` (deliberately — a frozen "age" scalar stops ageing the moment
#: the producer dies, which is the shape of the 2026-08 silent freeze), so a hardcoded
#: literal here would rot into a scheduled red the way this file's header warns about.
_HEALTHY_STATUS_NOW = datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)


def _healthy_vps_status() -> dict:
    # prophet_live was added to the dead-man by #6464 but this fixture was not given a
    # healthy entry, so the four tests below asserted "no failures" against a payload the
    # new grader correctly failed — red on main from that merge. Healed here rather than
    # by loosening the grader: the grader is right, the fixture was simply incomplete.
    _fresh = (_HEALTHY_STATUS_NOW - timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
    return {
        "status": "ok",
        "checks": {
            "prophet_live": {
                "schema": "prophet_live.states/v1",
                "expected_now": True,
                "status": "live",
                "reason": None,
                "pass_ts": _fresh,
                "quote_asof": _fresh,
                "session_et": "2026-07-20",
                "pack_ok": True,
                "pack_as_of": "2026-07-17",
                "pack_expected": "2026-07-17",
                "producer": "vps:macro-live-prophet",
                "state_counts": {"dormant": 1203, "near": 340, "forming": 12},
            },
            "quotes": {"age_min": 1, "requested": 25, "resolved": 20},
            "release_publications": {
                "schema": "release_publications.v2",
                "age_min": 1,
                "event_status": {"published": 1, "scheduled": 3},
                "max_publication_lag_min": 0,
            },
            "orchestrator": {
                "age_min": 1,
                "lanes": {
                    "fast": {"ok": True, "age_min": 1},
                    "snapshot": {"ok": True, "age_min": 4},
                    "bars": {"ok": True, "age_min": 30},
                },
            },
            "basket_pulse": {"age_min": 4},
            "overlay": {"age_min": 2},
            "risk_state": {"age_min": 2},
            "china_risk_state": {"age_min": 2},
            "flow_pulse": {
                "age_min": 30,
                "mode": "fastpath",
                "n_tickers": 116,
                "with_bars": 116,
                "n_universe": 116,
                "source_asof": (
                    _HEALTHY_STATUS_NOW - timedelta(minutes=40)
                ).isoformat().replace("+00:00", "Z"),
            },
            "intraday_quotes": {
                "requested": 116,
                "resolved": 116,
                "coverage": 1.0,
                "source_asof": (
                    _HEALTHY_STATUS_NOW - timedelta(minutes=20)
                ).isoformat().replace("+00:00", "Z"),
                "built_at": _fresh,
            },
        },
    }


def test_vps_health_contract_covers_us_live_lanes():
    now = datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    assert evaluate_live_health(_healthy_vps_status(), now=now) == []


def test_vps_health_contract_reports_failed_or_stale_lane():
    payload = _healthy_vps_status()
    payload["checks"]["orchestrator"]["lanes"]["snapshot"] = {
        "ok": False,
        "age_min": 22,
    }
    failures = evaluate_live_health(
        payload,
        now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
    )
    assert "lane snapshot: last run was not healthy" in failures
    assert any("lane snapshot: stale" in failure for failure in failures)


def test_vps_health_contract_rejects_age_fresh_no_data_pulse():
    payload = _healthy_vps_status()
    payload["checks"]["flow_pulse"].update({"mode": "no_data", "with_bars": 0})
    failures = evaluate_live_health(
        payload,
        now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
    )
    assert "flow_pulse: semantically unavailable (mode=no_data)" in failures


def test_vps_health_contract_reports_semantically_late_release():
    payload = _healthy_vps_status()
    payload["checks"]["release_publications"].update(
        {
            "event_status": {"awaiting_publication": 1, "scheduled": 3},
            "max_publication_lag_min": 2.5,
        }
    )
    failures = evaluate_live_health(
        payload,
        now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
    )
    assert (
        "release_publications: official result still unavailable 2.5m after schedule"
        in failures
    )


def test_vps_health_contract_reports_schedule_exhaustion():
    payload = _healthy_vps_status()
    payload["checks"]["release_publications"].update(
        {
            "schedule_status": "incomplete",
            "missing_schedule_types": ["FOMC", "CPI"],
        }
    )
    failures = evaluate_live_health(
        payload,
        now=datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc),
    )
    assert (
        "release_publications: official schedule coverage is incomplete (FOMC, CPI)"
        in failures
    )


def test_vps_health_contract_does_not_require_equity_lanes_on_weekend():
    payload = _healthy_vps_status()
    del payload["checks"]["orchestrator"]["lanes"]["snapshot"]
    del payload["checks"]["orchestrator"]["lanes"]["bars"]
    del payload["checks"]["basket_pulse"]
    del payload["checks"]["flow_pulse"]
    assert evaluate_live_health(
        payload,
        now=datetime(2026, 7, 19, 15, 0, tzinfo=timezone.utc),
    ) == []


# ─────────────────────────────────────────────────────────────────────────────
# Live-breadth truth boundary — /api/status semantic health (FROZEN CONTRACT §6)
# ─────────────────────────────────────────────────────────────────────────────

def _healthy_breadth_check() -> dict:
    return {
        "usable": True,
        "unusable_reason": None,
        "feed_status": "ok",
        "session": "rth",
        "source_asof": "2026-07-20T14:44:00Z",
        "source_age_min": 4.0,
        "delay_min": 19,
        "producer": "vps:macro-live-breadth",
        "coverage_n": 1503,
        "coverage_pct": 100.2,
        "adv": 900,
        "dec": 580,
    }


def test_breadth_health_is_absent_ok():
    """A box that has not deployed the macro-live-breadth lane yet must not red
    the whole dead-man — same ABSENT-OK precedent as cn_prophet_live."""
    payload = _healthy_vps_status()
    assert "breadth" not in payload["checks"]
    assert evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    ) == []


def test_breadth_health_passes_during_the_live_window_when_healthy():
    payload = _healthy_vps_status()
    payload["checks"]["breadth"] = _healthy_breadth_check()
    assert evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)  # weekday, in window
    ) == []


def test_breadth_health_fails_when_unusable_during_the_live_window():
    payload = _healthy_vps_status()
    payload["checks"]["breadth"] = _healthy_breadth_check()
    payload["checks"]["breadth"]["usable"] = False
    payload["checks"]["breadth"]["unusable_reason"] = "source_stale"
    failures = evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    )
    assert any("breadth: not usable" in f and "source_stale" in f for f in failures)


def test_breadth_health_fails_on_stale_source_clock():
    payload = _healthy_vps_status()
    payload["checks"]["breadth"] = _healthy_breadth_check()
    # Source snapshot 40 min before `now` — the ABSOLUTE stamp is what is graded.
    payload["checks"]["breadth"]["source_asof"] = "2026-07-20T14:20:00Z"
    payload["checks"]["breadth"]["source_age_min"] = 40.0
    failures = evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    )
    assert any("breadth: source stale" in f for f in failures)


def test_breadth_health_catches_a_producer_that_stopped_writing():
    """A dead producer must red the dead-man, not read healthy.

    `source_age_min` is frozen at BUILD time. A lane that died three hours ago
    keeps serving an artifact that still says `source_age_min: 4.0` and
    `usable: true` forever, so grading that field would declare a stopped
    producer perfectly healthy — the exact blindness a dead-man exists to
    prevent. Only the absolute `source_asof` keeps ageing after the writer
    stops, so it is what gets graded.
    """
    payload = _healthy_vps_status()
    breadth = _healthy_breadth_check()
    # Everything the payload says about itself still looks fresh...
    assert breadth["source_age_min"] == 4.0 and breadth["usable"] is True
    # ...but nothing has been written for three hours.
    breadth["source_asof"] = "2026-07-20T11:44:00Z"
    breadth["age_min"] = 180.0
    payload["checks"]["breadth"] = breadth
    failures = evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    )
    assert any("breadth: source stale" in f for f in failures), failures
    assert any("producer that stopped writing" in f for f in failures), failures


def test_breadth_health_fails_closed_without_an_absolute_source_stamp():
    payload = _healthy_vps_status()
    breadth = _healthy_breadth_check()
    breadth.pop("source_asof")
    breadth.pop("source_age_min")
    payload["checks"]["breadth"] = breadth
    failures = evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    )
    assert any("breadth: missing or invalid source_asof" in f for f in failures)


def test_breadth_health_fails_on_low_coverage():
    payload = _healthy_vps_status()
    payload["checks"]["breadth"] = _healthy_breadth_check()
    payload["checks"]["breadth"]["coverage_pct"] = 40.0
    failures = evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    )
    assert any("breadth: coverage low" in f for f in failures)


def test_breadth_health_fails_on_missing_producer():
    payload = _healthy_vps_status()
    payload["checks"]["breadth"] = _healthy_breadth_check()
    payload["checks"]["breadth"]["producer"] = ""
    failures = evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    )
    assert any("breadth: missing producer" in f for f in failures)


def test_breadth_health_requires_nothing_when_session_closed():
    """Stale last-session data outside a session is legitimate evidence of
    nothing being wrong — never a fault, even inside what would otherwise be
    the live window's hour (explicit spec requirement)."""
    payload = _healthy_vps_status()
    payload["checks"]["breadth"] = _healthy_breadth_check()
    payload["checks"]["breadth"]["session"] = "closed"
    payload["checks"]["breadth"]["usable"] = False
    payload["checks"]["breadth"]["source_age_min"] = 999.0
    assert evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    ) == []


def test_breadth_health_requires_nothing_on_the_weekend():
    payload = _healthy_vps_status()
    payload["checks"]["breadth"] = _healthy_breadth_check()
    payload["checks"]["breadth"]["usable"] = False
    payload["checks"]["breadth"]["source_age_min"] = 999.0
    assert evaluate_live_health(
        payload, now=datetime(2026, 7, 19, 15, 0, tzinfo=timezone.utc)  # Sunday
    ) == []


def test_breadth_health_requires_only_parsing_outside_the_live_window():
    """Weekday, session open, but outside UTC hour 14..20 — require only that
    the key parses; report nothing about freshness/coverage/usable."""
    payload = _healthy_vps_status()
    payload["checks"]["breadth"] = _healthy_breadth_check()
    payload["checks"]["breadth"]["usable"] = False
    payload["checks"]["breadth"]["source_age_min"] = 999.0
    assert evaluate_live_health(
        payload, now=datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)  # weekday, before window
    ) == []


# ─────────────────────────────────────────────────────────────────────────────
# Live-breadth canonical production ownership (FROZEN CONTRACT §7)
# ─────────────────────────────────────────────────────────────────────────────

def test_live_setup_installs_and_arms_the_breadth_lane():
    root = Path(__file__).resolve().parents[1]
    live_setup = (root / "app" / "deploy" / "live-setup.sh").read_text()
    assert "macro-live-breadth.service macro-live-breadth.timer" in live_setup
    enable_block = live_setup.rsplit("systemctl enable --now", 1)[1].split("\n\n")[0]
    assert "macro-live-breadth.timer" in enable_block


def test_breadth_unit_pair_exists_and_uses_the_shared_env_file():
    root = Path(__file__).resolve().parents[1]
    service = (root / "app" / "deploy" / "macro-live-breadth.service").read_text()
    timer = (root / "app" / "deploy" / "macro-live-breadth.timer").read_text()
    assert "EnvironmentFile=-/etc/macro-live.env" in service
    assert "ExecStart=/opt/macro/.venv/bin/python -m scripts.live_breadth_poller --once" in service
    assert "Environment=MACRO_LIVE_PRODUCER=vps:macro-live-breadth" in service
    assert "Unit=macro-live-breadth.service" in timer


def test_breadth_vps_lane_never_publishes_via_git():
    """The VPS lane publishes by atomic rename into $MACRO_LIVE_DIR — the path
    Caddy serves first, no-store — so it must NOT carry --publish.

    Two independent reasons, both load-bearing:

    1. Ownership. --publish is the GitHub BACKSTOP's mechanism (it commits
       site/live/breadth.json to main so the STATIC fallback advances). If the
       VPS lane also published, two writers would claim primary ownership of the
       same artifact, which is exactly the state this wave exists to end.
    2. It would hard-fail every two minutes. With MACRO_LIVE_DIR set, the output
       path is OUTSIDE the git work tree, so `git add -f` returns "is outside
       repository", publish() returns False, and --once --publish now (correctly)
       exits non-zero. Verified by direct run against a temp MACRO_LIVE_DIR.
    """
    root = Path(__file__).resolve().parents[1]
    service = (root / "app" / "deploy" / "macro-live-breadth.service").read_text()
    exec_line = next(
        line for line in service.splitlines() if line.startswith("ExecStart=")
    )
    assert "--publish" not in exec_line, (
        "the VPS breadth lane must not git-publish: it would contend with the GH "
        "backstop for primary ownership AND fail on every tick, because "
        "$MACRO_LIVE_DIR is outside the git work tree"
    )

    # The backstop is the one that DOES publish — the other half of the split.
    workflow = (root / ".github" / "workflows" / "live-breadth.yml").read_text()
    assert "--once --publish" in workflow


def test_update_sh_self_arms_the_breadth_lane_on_a_running_box():
    """live-setup.sh alone is not ownership: it is a manual operator act, and the
    unit did not exist when it last ran on the box. update.sh is what actually
    installs a NEW live lane on an already-provisioned VPS, via the same
    absent-file self-arming clause macro-live-prophet uses.
    """
    root = Path(__file__).resolve().parents[1]
    update = (root / "app" / "deploy" / "update.sh").read_text()
    assert "app/deploy/macro-live-breadth" in update
    assert "[ ! -f /etc/systemd/system/macro-live-breadth.timer ]" in update
    assert "systemctl enable --now macro-live-breadth.timer" in update
    # A oneshot must never be restarted out of band — that would burn a Polygon
    # snapshot off-schedule. Only the timer is re-armed.
    assert "systemctl restart macro-live-breadth.service" not in update


def test_caddy_serves_live_store_without_cache():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app" / "deploy" / "Caddyfile").read_text()
    assert "@vps_public_live" in text
    assert "@vps_external" in text
    assert "handle /live/quotes.json" in text
    assert "/live/intraday_quotes.json" in text
    assert "/live/flow_pulse.json" in text
    assert "handle /live/release_publications.json" in text
    assert "root * /var/lib/macro-live/public" in text
    assert 'Cache-Control "no-store"' in text
    # Only explicitly reviewed market-display and official-event facts bypass
    # auth. All other external live artifacts stay inside the fail-closed route.
    assert "handle /live/*" not in text
    protected = text[text.index("handle @reg_asset {") : text.index("@gate_html {")]
    assert "rewrite /api/regwall/check" in protected
    assert "rewrite /api/paywall/check" in protected
    assert "handle @vps_external" in protected


def test_live_data_orphan_push_clears_the_index_sparse_safely(tmp_path):
    """`git rm -rf --cached .` does not empty the index under a sparse checkout.

    live-quotes.yml gained a sparse cone on 2026-07-30 to stop its checkout
    blowing the job timeout. That silently broke the orphan-branch push: `git rm`
    HONOURS sparse rules and refuses to touch entries outside the cone, so `.`
    expanded to the few in-cone paths and left the rest staged — measured 30,896
    surviving entries, turning the single-file `live-data` branch into a full-tree
    snapshot on every 5-minute push. Nothing would have alerted: quotes.json stays
    at the top of the tree, so raw.githubusercontent keeps serving it and every
    consumer looks healthy while the branch grows a whole tree per tick.

    Executable, not a grep: the failure is git BEHAVIOUR under a config, and a
    text assertion would have passed the broken version just as happily.
    """
    import subprocess

    def git(*args, **kw):
        return subprocess.run(("git",) + args, cwd=repo, capture_output=True,
                              text=True, **kw)

    repo = tmp_path / "r"
    repo.mkdir()
    git("init", "-q", "-b", "main")
    git("config", "user.name", "t")
    git("config", "user.email", "t@t")
    # A tree with in-cone and out-of-cone paths, mirroring the real lane.
    for rel in ("engine/x.py", "site/stocks/big.json", "data/baskets/ohlcv/a.parquet"):
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "base")
    git("sparse-checkout", "set", "engine")          # the cone the lane now uses

    (repo / "quotes.json").write_text('{"quotes":{}}', encoding="utf-8")
    git("checkout", "--orphan", "live-data-tmp")

    # The OLD line, to prove the trap is real and not folklore.
    git("rm", "-rf", "--cached", ".")
    survivors = [l for l in git("ls-files", "--cached").stdout.splitlines() if l]
    assert survivors, (
        "`git rm -rf --cached .` emptied the index under a sparse checkout — if "
        "git changed this, simplify the workflow back and delete this test")

    # The shipped line must clear it regardless.
    git("read-tree", "--empty")
    assert not [l for l in git("ls-files", "--cached").stdout.splitlines() if l]
    git("add", "-f", "quotes.json")
    git("commit", "-qm", "live quotes")
    tree = [l for l in git("ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines() if l]
    assert tree == ["quotes.json"], tree

    # …and the workflow must actually use it.
    body = (Path(__file__).resolve().parents[1] / ".github" / "workflows" /
            "live-quotes.yml").read_text(encoding="utf-8")
    assert "git read-tree --empty" in body, (
        "the orphan push no longer clears the index sparse-safely")
    # Comment lines are allowed to NAME the trap — that is how the next reader
    # learns why read-tree is there. Only a live command line is a regression.
    commands = [l for l in body.splitlines() if not l.lstrip().startswith("#")]
    assert not [l for l in commands if "git rm -rf --cached" in l], (
        "the sparse-unsafe index clear is back in live-quotes.yml")


# Regression coverage for the 2026-09-16 production FOMC parser miss. Kept in this
# existing CI-owned suite so publication recovery does not mutate CI authority merely
# to make its regression executable.
FOMC_SEPTEMBER_16_RECOVERY_STATEMENT = b"""
<html><body>
<p>September 16, 2026</p>
<p>The Federal Open Market Committee approved the following statement for release
by a 12 - 0 vote:</p>
<p>The Committee decided to raise the target range for the federal funds rate by
1/4 percentage point to 3-3/4 to 4 percent, in support of the Federal Reserve's
dual mandate.</p>
</body></html>
"""

CLAIMS_SEPTEMBER_10_RECOVERY_LISTING = b"""
<div class="view-content"><div class="dol-feed-block">
  <div data-history-node-id="fixture"
       about="/newsroom/releases/eta/eta20260910">
    <p class="dol-date-text">September 10, 2026</p>
    <a href="/newsroom/releases/eta/eta20260910">
      <h3><span>Unemployment Insurance Weekly Claims Report</span></h3>
    </a>
    <div class="field--name-field-press-body">
      <p>In the week ending September 5, the advance figure for seasonally adjusted
      initial claims was 206,000, a decrease of 1,000 from the previous week's
      revised level. The 4-week moving average was 206,000.</p>
    </div>
  </div>
</div></div>
"""


def _recovery_claims_event() -> dict[str, object]:
    return {
        "event_id": "claims:2026-09-10",
        "type": "CLAIMS",
        "date": "2026-09-10",
        "time_et": "08:30",
        "scheduled_at": "2026-09-10T08:30:00-04:00",
        "label": "Initial jobless claims",
        "label_zh": "初请失业金人数",
        "schedule_source": "computed",
        "is_context_only": True,
    }


def _recovery_fomc_event() -> dict[str, object]:
    return {
        "event_id": "fomc:2026-09-16",
        "type": "FOMC",
        "date": "2026-09-16",
        "time_et": "14:00",
        "scheduled_at": "2026-09-16T14:00:00-04:00",
        "label": "FOMC rate decision",
        "label_zh": "美联储议息会议",
        "schedule_source": "federal_reserve",
        "is_context_only": True,
    }


def _recovery_claims_state() -> dict[str, object]:
    return {
        "schema": "release_publication_state.v2",
        "coverage_started_at_by_type": {
            "CLAIMS": "2026-09-10T12:00:00+00:00",
        },
        "sources": {},
        "publications": {},
    }


def test_fomc_parser_accepts_explicit_change_size_before_target_range() -> None:
    actual = wrp.parse_fomc_actual(FOMC_SEPTEMBER_16_RECOVERY_STATEMENT)

    assert actual is not None
    assert actual["action"] == "hike"
    assert actual["target_low"] == 3.75
    assert actual["target_high"] == 4.0
    assert actual["vote_for"] == 12
    assert actual["vote_against"] == 0


def test_fomc_change_size_statement_publishes_with_parser_v2(monkeypatch) -> None:
    event = _recovery_fomc_event()
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [event])

    def fetcher(spec, prior, timeout):
        assert spec.source_id == "fed_fomc"
        return _http_result(FOMC_SEPTEMBER_16_RECOVERY_STATEMENT)

    _, payload = wrp.detect(
        now=datetime(2026, 9, 16, 18, 3, tzinfo=timezone.utc),
        state={},
        fetcher=fetcher,
    )

    publication = payload["publications"][0]
    assert publication["status"] == "published"
    assert publication["actual"]["action"] == "hike"
    assert publication["parser"] == {"name": "fomc", "version": 2}


def test_dol_overdue_release_retries_through_retention_and_self_heals(monkeypatch) -> None:
    event = _recovery_claims_event()
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [event])
    calls = []

    def fetcher(spec, prior, timeout):
        calls.append(spec.url)
        assert spec.source_id == "dol_claims"
        assert spec.url == "https://www.dol.gov/index.php/newsroom/releases/eta"
        return _http_result(CLAIMS_SEPTEMBER_10_RECOVERY_LISTING)

    new_state, payload = wrp.detect(
        now=datetime(2026, 9, 16, 18, 15, tzinfo=timezone.utc),
        state=_recovery_claims_state(),
        fetcher=fetcher,
    )

    assert calls == ["https://www.dol.gov/index.php/newsroom/releases/eta"]
    publication = next(
        row for row in payload["publications"]
        if row["event_id"] == "claims:2026-09-10"
    )
    assert publication["status"] == "published"
    assert publication["data_ready"] is True
    assert publication["actual"]["initial_claims"] == 206_000
    assert publication["actual"]["change"] == -1_000
    assert publication["source_url"] == (
        "https://www.dol.gov/index.php/newsroom/releases/eta/eta20260910"
    )

    source = new_state["sources"]["dol_claims:claims:2026-09-10"]
    assert source["attempt_count"] == 1
    assert source["first_attempt_at"] == "2026-09-16T18:15:00+00:00"
    assert source["last_attempt_at"] == "2026-09-16T18:15:00+00:00"
    assert source["last_attempt_status"] == "ok"
    assert source["last_success_at"] == "2026-09-16T18:15:00+00:00"


def test_overdue_source_failure_lineage_survives_then_recovers(monkeypatch) -> None:
    event = _recovery_claims_event()
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [event])
    first_tick = datetime(2026, 9, 16, 18, 15, tzinfo=timezone.utc)

    def failing_fetcher(spec, prior, timeout):
        raise TimeoutError("official source timed out")

    failed_state, failed_payload = wrp.detect(
        now=first_tick,
        state=_recovery_claims_state(),
        fetcher=failing_fetcher,
    )

    key = "dol_claims:claims:2026-09-10"
    failed = failed_state["sources"][key]
    assert failed["attempt_count"] == 1
    assert failed["first_attempt_at"] == first_tick.isoformat()
    assert failed["last_attempt_at"] == first_tick.isoformat()
    assert failed["last_attempt_status"] == "error"
    assert failed["last_error"] == "TimeoutError"
    assert failed["last_error_at"] == first_tick.isoformat()
    assert failed_payload["source_health"] == [
        {
            "source_id": "dol_claims",
            "event_id": "claims:2026-09-10",
            "status": "error",
            "error": "TimeoutError",
        }
    ]

    def unexpected_fetcher(spec, prior, timeout):
        raise AssertionError("non-periodic ticks must not hot-loop an overdue source")

    retained_state, retained_payload = wrp.detect(
        now=datetime(2026, 9, 16, 18, 16, tzinfo=timezone.utc),
        state=failed_state,
        fetcher=unexpected_fetcher,
    )
    assert retained_state["sources"][key] == failed
    assert retained_payload["source_health"] == []

    def recovering_fetcher(spec, prior, timeout):
        return _http_result(CLAIMS_SEPTEMBER_10_RECOVERY_LISTING)

    recovered_state, recovered_payload = wrp.detect(
        now=datetime(2026, 9, 16, 18, 30, tzinfo=timezone.utc),
        state=retained_state,
        fetcher=recovering_fetcher,
    )
    recovered = recovered_state["sources"][key]
    assert recovered["attempt_count"] == 2
    assert recovered["last_attempt_status"] == "ok"
    assert recovered["last_success_at"] == "2026-09-16T18:30:00+00:00"
    assert recovered["last_error"] == "TimeoutError"
    assert recovered["last_error_at"] == first_tick.isoformat()
    publication = next(
        row for row in recovered_payload["publications"]
        if row["event_id"] == "claims:2026-09-10"
    )
    assert publication["status"] == "published"


# ===========================================================================
# B1.LIVE.1 / B1.LIVE.2 — the official-release publication lane owns its own
# timing and the incumbent producer stays the single writer. Every test here
# FAILS on the pre-B1.LIVE.1 tree except the one marked PRESERVATION.
# ===========================================================================

CPI_SCHEDULED_2026_10_14 = datetime(2026, 10, 14, 12, 30, tzinfo=timezone.utc)
CPI_ARCHIVE_URL = "https://www.bls.gov/news.release/archives/cpi_10142026.htm"
CPI_SEPTEMBER_PAGE = b"""
<html><body><h1>CONSUMER PRICE INDEX - SEPTEMBER 2026</h1>
<p>The Consumer Price Index for All Urban Consumers (CPI-U) increased 0.2 percent
on a seasonally adjusted basis in September after rising 0.1 percent in August.</p>
<p>Over the last 12 months, the all items index increased 2.7 percent
before seasonal adjustment.</p>
<p>The index for all items less food and energy rose 0.3 percent in September.</p>
<p>The index for all items less food and energy rose 2.9 percent over the
past 12 months.</p></body></html>
"""
_CPI_EVENT = {
    "event_id": "cpi:2026-10-14",
    "type": "CPI",
    "date": "2026-10-14",
    "time_et": "08:30",
    "label": "CPI (consumer prices)",
    "label_zh": "consumer prices",
    "schedule_source": "static",
    "scheduled_at": "2026-10-14T08:30:00-04:00",
    "is_sep": False,
    "is_context_only": True,
}


def _cpi_row(*, last_probe_at: str | None = None, **overrides) -> dict:
    """One retained source row. ``last_probe_at=None`` keeps ONLY the fields
    that predate the pacing change, so a preservation test stays valid on the
    pre-patch tree."""
    row = {
        "source_id": "bls_cpi",
        "attempt_count": 3,
        "last_attempt_status": "ok",
        "last_success_at": last_probe_at,
        "checked_at": last_probe_at,
        "source_url": "https://www.bls.gov/feed/cpi.rss",
        "fingerprint": "c" * 64,
        "etag": '"fixture"',
        "last_modified": "Wed, 14 Oct 2026 12:30:00 GMT",
        "content_type": "application/atom+xml",
    }
    if last_probe_at:
        row.update({
            "first_attempt_at": last_probe_at,
            "last_attempt_at": last_probe_at,
            wrp.PROBE_LAST_AT_KEY: last_probe_at,
            wrp.PROBE_NEXT_AT_KEY: last_probe_at,
            wrp.PROBE_INTERVAL_KEY: wrp.NORMAL_PROBE_INTERVAL_S,
            wrp.PROBE_FAILURES_KEY: 0,
            wrp.PROBE_RETRY_AFTER_KEY: None,
            wrp.PROBE_BACKOFF_KEY: None,
        })
    row.update(overrides)
    return row


def _cpi_state(*, row: dict | None = None, publication: dict | None = None) -> dict:
    state = {
        "schema": "release_publication_state.v2",
        "coverage_started_at_by_type": {
            event_type: "2026-10-01T00:00:00+00:00"
            for event_type in wrp.RESULT_EVENT_TYPES
        },
        "sources": {"bls_cpi:cpi:2026-10-14": row or _cpi_row()},
        "publications": {},
        wrp.DEFECT_REPAIR_STATE_KEY: {},
    }
    if publication is not None:
        state["publications"]["cpi:2026-10-14"] = publication
    return state


def _cpi_publication(
    *, data_ready: bool = False, parser_version: int = 1, period: str = "September 2026"
) -> dict:
    return {
        "event_id": "cpi:2026-10-14",
        "type": "CPI",
        "date": "2026-10-14",
        "time_et": "08:30",
        "scheduled_at": "2026-10-14T12:30:00+00:00",
        "status": "published" if data_ready else "published_unparsed",
        "data_ready": data_ready,
        "source_id": "bls_cpi",
        "source_url": CPI_ARCHIVE_URL,
        "source_sha256": "a" * 64,
        "content_sha256": "a" * 64,
        "reference_period": period,
        "parser": {"name": "cpi", "version": parser_version},
        "extraction": {
            "status": "incomplete",
            "attempted_parser": {"name": "cpi", "version": parser_version},
        },
    }


def _cpi_calls(calls: list[str]) -> list[str]:
    return [url for url in calls if url.endswith("cpi.rss")]


def _cpi_fetcher(calls: list[str], body: bytes | None = None):
    def fetcher(spec, prior, timeout):
        calls.append(spec.url)
        if body is None:
            return {**_http_result(_bls_cpi_feed(event_date="2026-10-14")), "url": spec.url}
        return {**_http_result(body), "url": spec.url}

    return fetcher


def _release_payload(now: datetime) -> dict:
    return {"schema": "release_publications.v2", "built": now.isoformat(),
            "events": [], "due": [], "publications": [], "source_health": []}


def _dedicated_release_installed(tmp_path: Path, monkeypatch):
    marker = tmp_path / "macro-live-releases.timer"
    marker.write_text("installed but not necessarily enabled")
    monkeypatch.setattr(vlo, "RELEASE_TIMER_PATH", marker)


def test_fast_lane_no_longer_invokes_the_release_writer(tmp_path: Path, monkeypatch):
    """ONE writer, one lane: the fast lane must not run the producer.

    The release watcher used to be the FIRST leaf of the fast lane, so the
    fast lane's 60s timer and 150s oneshot timeout were also the
    publication's timing. The producer now belongs to its own lane.
    """
    _dedicated_release_installed(tmp_path, monkeypatch)
    orch = vlo.Orchestrator(
        live_dir=tmp_path / "live",
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        now=datetime(2026, 10, 14, 15, 1, tzinfo=timezone.utc),
    )
    names: list[str] = []
    orch.module = lambda name, *args, **kwargs: names.append(name) or vlo.TaskResult(  # type: ignore[method-assign]
        name, "ok", 0.0
    )
    orch.fast()
    assert "release_publications" not in names
    assert "display_quotes" in names


def test_release_lane_publishes_while_the_fast_leaves_are_broken(tmp_path: Path, monkeypatch):
    """A slow/failing quote leaf must not be able to delay a publication."""
    _dedicated_release_installed(tmp_path, monkeypatch)
    live = tmp_path / "live"
    stage = tmp_path / "stage"
    stage.mkdir()

    def runner(args, **kwargs):
        module = args[2] if len(args) > 2 else ""
        if module == "scripts.watch_release_publications":
            live.mkdir(exist_ok=True)
            (live / "release_publications.json").write_text(
                json.dumps(_release_payload(datetime(2026, 10, 14, 3, 1, tzinfo=timezone.utc))),
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="wrote", stderr="")
        raise subprocess.TimeoutExpired(args, 45)

    fast = vlo.Orchestrator(
        live_dir=live,
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        runner=runner,
        now=datetime(2026, 10, 14, 3, 1, tzinfo=timezone.utc),
    )
    fast.stage_dir = stage
    fast.fast()
    assert [result.name for result in fast.results] == ["display_quotes"]
    assert all(result.status == "timeout" for result in fast.results)

    releases = vlo.Orchestrator(
        live_dir=live,
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        runner=runner,
        now=datetime(2026, 10, 14, 3, 1, tzinfo=timezone.utc),
    )
    releases.stage_dir = stage
    releases.releases()
    assert [result.name for result in releases.results] == ["release_publications"]
    assert releases.results[0].status == "ok"
    published = json.loads((live / "release_publications.json").read_text())
    assert published["schema"] == "release_publications.v2"


def test_release_lane_idle_tick_costs_no_producer_run_and_no_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The timer may wake often; the request rate stays with the state."""
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [_CPI_EVENT])
    live = tmp_path / "live"
    live.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    artifact = live / "release_publications.json"
    now = datetime(2026, 10, 14, 15, 1, tzinfo=timezone.utc)
    artifact.write_text(json.dumps(_release_payload(now - timedelta(seconds=10))))
    stamp = int((now - timedelta(seconds=10)).timestamp())
    os.utime(artifact, (stamp, stamp))
    (state_dir / "release_publications_state.json").write_text(
        json.dumps(
            _cpi_state(row=_cpi_row(last_probe_at=(now - timedelta(seconds=30)).isoformat()))
        ),
        encoding="utf-8",
    )
    orch = vlo.Orchestrator(
        live_dir=live, state_dir=state_dir, data_dir=tmp_path / "data", now=now
    )
    calls: list[str] = []
    orch.module = lambda name, *args, **kwargs: calls.append(name) or vlo.TaskResult(  # type: ignore[method-assign]
        name, "ok", 0.0
    )
    orch.releases()
    assert calls == []


def test_release_lane_refreshes_the_public_heartbeat_when_nothing_is_due(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The published sidecar is a heartbeat: it must not go stale.

    The external dead-man fails closed once release_publications.json is more
    than five minutes old, so an idle lane still refreshes it on the bounded
    heartbeat interval.
    """
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [_CPI_EVENT])
    live = tmp_path / "live"
    live.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    artifact = live / "release_publications.json"
    now = datetime(2026, 10, 14, 15, 1, tzinfo=timezone.utc)
    artifact.write_text(json.dumps(_release_payload(now - timedelta(seconds=90))))
    stale = int(
        (now - timedelta(seconds=vlo.RELEASE_HEARTBEAT_MAX_AGE_S + 30)).timestamp()
    )
    os.utime(artifact, (stale, stale))
    (state_dir / "release_publications_state.json").write_text(
        json.dumps(
            _cpi_state(row=_cpi_row(last_probe_at=(now - timedelta(seconds=30)).isoformat()))
        ),
        encoding="utf-8",
    )
    orch = vlo.Orchestrator(
        live_dir=live, state_dir=state_dir, data_dir=tmp_path / "data", now=now
    )
    calls: list[str] = []
    orch.module = lambda name, *args, **kwargs: calls.append(name) or vlo.TaskResult(  # type: ignore[method-assign]
        name, "ok", 0.0
    )
    orch.releases()
    assert calls == ["release_publications"]


def test_source_probe_is_fast_inside_the_hot_window_and_slow_outside_it():
    """Hot window vs ordinary cadence, measured on the retained state."""
    scheduled = CPI_SCHEDULED_2026_10_14
    calls: list[str] = []
    fetcher = _cpi_fetcher(calls)

    # 30 seconds after the last probe, INSIDE the bounded hot window: the fast
    # cadence says the row is due again.
    hot = _cpi_state(row=_cpi_row(last_probe_at=(scheduled - timedelta(seconds=30)).isoformat()))
    wrp.detect(now=scheduled, state=hot, fetcher=fetcher)
    assert _cpi_calls(calls) == ["https://www.bls.gov/feed/cpi.rss"]

    # The same row 30 seconds after a probe but 30 minutes after the schedule:
    # outside the hot window the ordinary cadence applies, so a 30-second-old
    # probe is NOT due and the source is left alone.
    calls.clear()
    idle = _cpi_state(
        row=_cpi_row(last_probe_at=(scheduled + timedelta(minutes=29, seconds=30)).isoformat())
    )
    _, idle_payload = wrp.detect(
        now=scheduled + timedelta(minutes=30), state=idle, fetcher=fetcher
    )
    assert _cpi_calls(calls) == []
    health = [row for row in idle_payload["source_health"] if row["source_id"] == "bls_cpi"]
    assert health and health[0]["status"] == "paced"


def test_already_verified_release_returns_to_the_ordinary_pace():
    """A verified release leaves the hot window immediately."""
    scheduled = CPI_SCHEDULED_2026_10_14
    calls: list[str] = []
    publication = _cpi_publication(data_ready=True)
    publication["actual"] = {"headline_mom": 0.2, "core_mom": 0.3}
    state = _cpi_state(
        row=_cpi_row(last_probe_at=(scheduled - timedelta(seconds=2)).isoformat()),
        publication=publication,
    )
    _, payload = wrp.detect(now=scheduled, state=state, fetcher=_cpi_fetcher(calls))
    assert _cpi_calls(calls) == []
    health = [row for row in payload["source_health"] if row["source_id"] == "bls_cpi"]
    assert health and health[0]["status"] == "paced"


def test_transient_failure_backs_off_then_recovers_without_faking_success():
    """A failing source is backed off, then recovers — and never lies."""
    scheduled = CPI_SCHEDULED_2026_10_14
    calls: list[str] = []

    def failing(spec, prior, timeout):
        calls.append(spec.url)
        raise urllib.error.URLError("upstream refused the connection")

    state = _cpi_state(
        row=_cpi_row(last_probe_at=(scheduled - timedelta(seconds=30)).isoformat())
    )
    failed_state, _ = wrp.detect(now=scheduled, state=state, fetcher=failing)
    row = failed_state["sources"]["bls_cpi:cpi:2026-10-14"]
    assert row["last_attempt_status"] == "error"
    assert row["last_error"] == "URLError"
    assert row["consecutive_failures"] == 1
    # The retained last success stays truthful: a failure never invents one.
    assert row["last_success_at"] == (scheduled - timedelta(seconds=30)).isoformat()
    # The bounded backoff keeps the fast loop off the failing source.
    assert row["backoff_until"] == (scheduled + timedelta(seconds=5)).isoformat()
    plan = wrp.tick_due(now=scheduled + timedelta(seconds=1), state=failed_state)
    assert [
        entry["event_key"]
        for entry in plan["due_rows"]
        if entry["source_id"] == "bls_cpi"
    ] == []

    recovered_state, _ = wrp.detect(
        now=scheduled + timedelta(seconds=6),
        state=failed_state,
        fetcher=_cpi_fetcher(calls),
    )
    recovered = recovered_state["sources"]["bls_cpi:cpi:2026-10-14"]
    assert recovered["last_attempt_status"] == "ok"
    assert recovered["consecutive_failures"] == 0
    assert recovered["last_success_at"] == (scheduled + timedelta(seconds=6)).isoformat()
    # The earlier failure lineage is not erased by the recovery.
    assert recovered["last_error"] == "URLError"


def test_upstream_retry_after_is_honoured_instead_of_hammering_the_source(
    monkeypatch: pytest.MonkeyPatch,
):
    """A blocked source (429/503) is left alone for as long as it asked."""
    headers = email.message.Message()
    headers["Retry-After"] = "120"

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 429, "Too Many Requests", headers, None
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        wrp._fetch(wrp.SOURCES[1], {}, 1.0)
    assert excinfo.value.retry_after_s == 120

    now = datetime(2026, 10, 14, 12, 30, tzinfo=timezone.utc)
    row = wrp._fail_source_attempt(
        {"consecutive_failures": 0},
        now=now,
        source_url="https://www.bls.gov/feed/cpi.rss",
        error="HTTPError",
        interval_s=wrp.HOT_PROBE_INTERVAL_S,
        retry_after_s=120,
    )
    assert row["retry_after_at"] == (now + timedelta(seconds=120)).isoformat()
    blocked = wrp._probe_blocked_until(row)
    assert blocked == now + timedelta(seconds=120)
    assert wrp._probe_due_at(
        row, now=now, interval_s=wrp.HOT_PROBE_INTERVAL_S, blocked_until=blocked
    ) == now + timedelta(seconds=120)


def test_retained_cpi_archive_catch_up_still_works_and_keeps_its_budget():
    """PRESERVATION: the incumbent archive catch-up still recovers the facts.

    The repair recovers an already-detected but unparsed release from its
    dated BLS archive. It keeps its bounded 3-attempt budget and is not
    re-armed by a tick.
    """
    state = _cpi_state(publication=_cpi_publication())
    now = datetime(2026, 10, 26, 13, 0, tzinfo=timezone.utc)
    calls: list[str] = []
    new_state, _ = wrp.detect(now=now, state=state, fetcher=_cpi_fetcher(calls, CPI_SEPTEMBER_PAGE))
    assert CPI_ARCHIVE_URL in calls
    repaired = new_state["publications"]["cpi:2026-10-14"]
    assert repaired["status"] == "published"
    assert repaired["data_ready"] is True
    assert repaired["actual"]["headline_mom"] == 0.2
    assert repaired["actual"]["core_mom"] == 0.3
    assert repaired["actual"]["reference_period"] == "September 2026"
    repair = new_state[wrp.DEFECT_REPAIR_STATE_KEY]["cpi:2026-10-14"]
    assert repair["status"] == "repaired"
    assert repair["attempts"] == 1
    assert repair["attempt_limit"] == 3

    calls.clear()
    retained_state, _ = wrp.detect(
        now=now + timedelta(seconds=2),
        state=new_state,
        fetcher=_cpi_fetcher(calls, CPI_SEPTEMBER_PAGE),
    )
    assert CPI_ARCHIVE_URL not in calls
    assert retained_state[wrp.DEFECT_REPAIR_STATE_KEY]["cpi:2026-10-14"]["attempts"] == 1


@pytest.mark.parametrize("error", [
    TimeoutError("dated report timed out"),
    urllib.error.HTTPError(CPI_ARCHIVE_URL, 503, "unavailable", {}, None),
    urllib.error.HTTPError(CPI_ARCHIVE_URL, 429, "rate limited", {}, None),
])
def test_historical_cpi_recovers_after_prolonged_transport_outage(monkeypatch, error):
    monkeypatch.setattr(wrp, "SOURCES", tuple(s for s in wrp.SOURCES if s.source_id == "bls_cpi"))
    key = "cpi:2026-10-14"
    start = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)
    detected = "2026-10-14T12:31:17+00:00"
    state = _cpi_state(publication={**_cpi_publication(), "detected_at": detected})
    calls = []
    for hour, expected_calls in [(0, 1), (0.5, 1), (1, 2), (2, 2), (3, 3),
                                 (6, 3), (7, 4), (12, 4), (13, 5), (18, 5), (19, 6), (48, 7)]:
        def fetch(spec, prior, timeout):
            assert spec.url == CPI_ARCHIVE_URL
            calls.append(spec.url)
            if hour < 48:
                raise error
            return {**_http_result(CPI_SEPTEMBER_PAGE), "url": spec.url}

        state, _ = wrp.detect(now=start + timedelta(hours=hour),
                              state=json.loads(json.dumps(state)), fetcher=fetch)
        assert len(calls) == expected_calls
        assert state["publications"][key]["data_ready"] is (hour == 48)
    assert state["publications"][key]["detected_at"] == detected
    assert state[wrp.DEFECT_REPAIR_STATE_KEY][key]["attempts"] == 1


@pytest.mark.parametrize("prior_evidence,expected_calls", [
    ("matched_timeout", 1), ("different_archive", 0), ("different_time", 0),
    ("ambiguous_http", 0), ("unverified_content", 0),
])
def test_historical_cpi_legacy_exhaustion_requires_matching_transport_evidence(
    monkeypatch, prior_evidence, expected_calls,
):
    monkeypatch.setattr(wrp, "SOURCES", tuple(s for s in wrp.SOURCES if s.source_id == "bls_cpi"))
    key = "cpi:2026-10-14"
    start = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)
    def unavailable(spec, prior, timeout):
        raise TimeoutError("archive not reachable")

    state, _ = wrp.detect(now=start, state=_cpi_state(publication=_cpi_publication()), fetcher=unavailable)
    source = state["sources"][f"bls_cpi:{key}"]
    record = state[wrp.DEFECT_REPAIR_STATE_KEY][key]
    # Old writers charged the final socket failure to the document budget.
    record.update(status="exhausted", attempts=3, next_attempt_at=None)
    record.pop("archive_budget_version", None)
    if prior_evidence == "different_archive":
        source["source_url"] = "https://www.bls.gov/feed/cpi.rss"
    elif prior_evidence == "different_time":
        source["last_error_at"] = (start - timedelta(days=1)).isoformat()
    elif prior_evidence == "ambiguous_http":
        source["last_error"] = record["last_error"] = "HTTPError"
    elif prior_evidence == "unverified_content":
        record["last_error"] = "detail_document_unverified"

    calls = []
    # An unverified document spends the one restored attempt. A later
    # healthy response must not open a fourth validation attempt.
    def wrong_document(spec, prior, timeout):
        calls.append(spec.url)
        return {**_http_result(CPI_SEPTEMBER_PAGE), "url": "https://www.bls.gov/feed/cpi.rss"}

    state, _ = wrp.detect(now=start + timedelta(hours=48), state=state, fetcher=wrong_document)
    state, _ = wrp.detect(now=start + timedelta(hours=96), state=json.loads(json.dumps(state)),
                          fetcher=_cpi_fetcher(calls, CPI_SEPTEMBER_PAGE))
    assert len(calls) == expected_calls
    assert state[wrp.DEFECT_REPAIR_STATE_KEY][key]["attempts"] == 3
    assert state["publications"][key]["data_ready"] is False


def test_permanent_cpi_archive_error_keeps_three_attempt_limit(monkeypatch):
    monkeypatch.setattr(wrp, "SOURCES", tuple(s for s in wrp.SOURCES if s.source_id == "bls_cpi"))
    start = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)
    state = _cpi_state(publication=_cpi_publication())
    calls = []

    def gone(spec, prior, timeout):
        calls.append(spec.url)
        raise urllib.error.HTTPError(spec.url, 410, "gone", {}, None)

    for hour in (0, 1, 3, 48):
        state, _ = wrp.detect(now=start + timedelta(hours=hour),
                              state=json.loads(json.dumps(state)), fetcher=gone)
    assert calls == [CPI_ARCHIVE_URL] * 3
    record = state[wrp.DEFECT_REPAIR_STATE_KEY]["cpi:2026-10-14"]
    assert (record["attempts"], record["status"]) == (3, "exhausted")


def test_governed_repair_bypasses_the_source_pacing():
    """A due governed repair is never held back by the ordinary pacing.

    The repair carries its OWN backoff and attempt budget; the ordinary
    per-source cadence must not add a second, longer wait in front of it.
    """
    state = _cpi_state(
        row=_cpi_row(last_probe_at="2026-10-26T12:59:30+00:00"),
        publication=_cpi_publication(),
    )
    calls: list[str] = []
    new_state, _ = wrp.detect(
        now=datetime(2026, 10, 26, 13, 0, tzinfo=timezone.utc),
        state=state,
        fetcher=_cpi_fetcher(calls, CPI_SEPTEMBER_PAGE),
    )
    # The source row was probed 30 seconds ago, so the ordinary one-minute
    # cadence would skip it; the governed repair is due and must bypass it.
    assert CPI_ARCHIVE_URL in calls
    assert new_state["publications"]["cpi:2026-10-14"]["data_ready"] is True
    assert new_state[wrp.DEFECT_REPAIR_STATE_KEY]["cpi:2026-10-14"]["attempts"] == 1


def test_parser_upgrade_bypasses_the_pacing_exactly_once():
    """A parser deployment retries once, immediately, and not again.

    The moment is deliberately OUTSIDE the hot window but inside the poll
    window, so the ordinary one-minute cadence would skip the row. The
    deployed parser has never tried this row, so the upgrade must bypass
    that pacing exactly once.
    """
    now = CPI_SCHEDULED_2026_10_14 + timedelta(minutes=30)
    state = _cpi_state(
        row=_cpi_row(last_probe_at=(now - timedelta(seconds=2)).isoformat()),
        publication=_cpi_publication(parser_version=1),
    )
    calls: list[str] = []

    def fetcher(spec, prior, timeout):
        calls.append(spec.url)
        body = CPI_JULY_14_PAGE if spec.url.endswith(".htm") else _bls_cpi_feed(
            event_date="2026-10-14"
        )
        return {**_http_result(body), "url": spec.url}

    new_state, _ = wrp.detect(now=now, state=state, fetcher=fetcher)
    assert _cpi_calls(calls) == ["https://www.bls.gov/feed/cpi.rss"]
    attempted = new_state["publications"]["cpi:2026-10-14"]["extraction"][
        "attempted_parser"
    ]
    assert attempted == {"name": "cpi", "version": 2}
    # The upgrade was CONSUMED, not re-armed by every tick.
    assert "cpi:2026-10-14" not in wrp._parser_upgrade_keys(
        [_CPI_EVENT], new_state["publications"]
    )

    calls.clear()
    wrp.detect(now=now + timedelta(seconds=2), state=new_state, fetcher=fetcher)
    assert _cpi_calls(calls) == []


def test_concurrent_producers_cannot_write_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """One writer lock covers load -> detect -> state+output write.

    The lock is inside the producer, so it also covers a manual invocation
    and any retired cron remnant — not just the release lane's own name.
    """
    state_dir = tmp_path / "state"
    out = tmp_path / "release_publications.json"
    writes: list[str] = []

    def fake_detect(*, now, state, timeout=8.0):
        writes.append(now.isoformat())
        time.sleep(0.3)
        return (
            {"schema": "release_publication_state.v2"},
            {
                "schema": "release_publications.v2",
                "built": now.isoformat(),
                "due": [],
                "events": [],
                "publications": [],
                "source_health": [],
            },
        )

    monkeypatch.setattr(wrp, "detect", fake_detect)
    monkeypatch.setattr(
        sys,
        "argv",
        ["watch_release_publications", "--out", str(out), "--state-dir", str(state_dir)],
    )
    results: list[int] = []
    threads = [
        threading.Thread(target=lambda: results.append(wrp.main())) for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [0, wrp.PRODUCER_BUSY_EXIT]
    assert len(writes) == 1
    assert json.loads(out.read_text())["schema"] == "release_publications.v2"


def test_producer_lock_is_released_for_the_next_writer(tmp_path: Path):
    """A busy producer must not wedge the lane permanently."""
    state_dir = tmp_path / "state"
    lock = wrp.producer_lock(state_dir)
    assert lock is not None
    try:
        assert wrp.producer_lock(state_dir) is None
    finally:
        lock.close()
    again = wrp.producer_lock(state_dir)
    assert again is not None
    again.close()


def test_release_lane_units_installer_and_rollback_are_wired():
    """The new lane must be installed, armed, drained and rolled back."""
    root = Path(__file__).resolve().parents[1]
    service = (root / "app" / "deploy" / "macro-live-releases.service").read_text()
    timer = (root / "app" / "deploy" / "macro-live-releases.timer").read_text()
    assert "--lane releases" in service
    assert "Unit=macro-live-releases.service" in timer
    # EXPLICIT BOUNDS on the wake cadence: the wake period plus systemd's own
    # coalescing slop must stay inside the 5s source-probe gap target.
    assert "OnUnitInactiveSec=2s" in timer
    assert "AccuracySec=100ms" in timer
    assert "RandomizedDelaySec=0" in timer

    setup = (root / "app" / "deploy" / "live-setup.sh").read_text()
    assert "macro-live-releases.service macro-live-releases.timer" in setup
    assert "systemctl start macro-live-releases.service" in setup
    assert "release_publications.v2" in setup
    # The incumbent writer is drained BEFORE the new lane is armed, so two
    # release writers can never overlap.
    drain = setup.index("stop_live_unit macro-live-fast.service")
    arm = setup.index("systemctl enable --now")
    smoke = setup.index("systemctl start macro-live-releases.service")
    assert drain < smoke < arm

    rollback = (root / "app" / "deploy" / "live-rollback.sh").read_text()
    assert "lanes=(fast releases snapshot bars prophet closepass breadth)" in rollback
    assert 'stop_live_unit "macro-live-$lane.service"' in rollback
    # The rollback keeps the last-good artifacts and the retained state.
    assert 'mv "$PUBLIC_DIR" "$backup_dir"' in rollback
    assert "rm -rf" not in rollback


def test_release_lane_bounds_are_explicit_and_self_consistent():
    """Every pacing parameter carries an explicit bound."""
    assert wrp.HOT_PROBE_INTERVAL_S <= wrp.MAX_SOURCE_PROBE_GAP_S
    assert wrp.NORMAL_PROBE_INTERVAL_S >= 60
    assert wrp.ERROR_BACKOFF_BASE_S <= wrp.ERROR_BACKOFF_MAX_S
    assert wrp.RETRY_AFTER_MAX_S > 0
    assert wrp.HOT_WINDOW_LEAD < wrp.HOT_WINDOW_TRAIL
    assert wrp.UNRESOLVED_PROBE_INTERVAL_S == wrp.UNRESOLVED_RETRY_INTERVAL_MIN * 60


def test_idle_release_lane_leaves_the_shared_public_status_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A lane that wakes on a short timer must not rewrite a public artifact
    (and fsync it) on every wake."""
    real_now = datetime.now(timezone.utc).replace(microsecond=0)
    et = real_now.astimezone(wrp.NY)
    event_at = (real_now - timedelta(hours=3)).astimezone(wrp.NY)
    event = {
        "event_id": f"cpi:{event_at.date().isoformat()}",
        "type": "CPI",
        "date": event_at.date().isoformat(),
        "time_et": event_at.strftime("%H:%M"),
        "label": "CPI (consumer prices)",
        "label_zh": "consumer prices",
        "schedule_source": "static",
        "scheduled_at": event_at.isoformat(),
        "is_sep": False,
        "is_context_only": True,
    }
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *args, **kwargs: [event])
    live = tmp_path / "live"
    live.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    artifact = live / "release_publications.json"
    artifact.write_text(json.dumps(_release_payload(real_now)), encoding="utf-8")
    os.utime(artifact, (int(real_now.timestamp()), int(real_now.timestamp())))
    state = {
        "schema": "release_publication_state.v2",
        "coverage_started_at_by_type": {
            event_type: "2026-01-01T00:00:00+00:00"
            for event_type in wrp.RESULT_EVENT_TYPES
        },
        "sources": {
            f"bls_cpi:{event['event_id']}": _cpi_row(
                last_probe_at=(real_now - timedelta(seconds=30)).isoformat()
            )
        },
        "publications": {},
        wrp.DEFECT_REPAIR_STATE_KEY: {},
    }
    (state_dir / "release_publications_state.json").write_text(json.dumps(state), encoding="utf-8")
    public = live / "orchestrator_status.json"
    public.write_text(
        json.dumps({"schema": "vps_live_orchestrator.v1", "updated_at": "x", "lanes": {}}),
        encoding="utf-8",
    )
    before = public.stat().st_mtime_ns
    producer_calls: list[str] = []

    def fake_module(self, name, module, module_args, **kwargs):
        # The producer is NOT spawned here: this test is about when the lane
        # decides to run it, not about what the producer does.
        producer_calls.append(name)
        stage = Path(module_args[list(module_args).index("--out") + 1])
        stage.parent.mkdir(parents=True, exist_ok=True)
        stage.write_text(json.dumps(_release_payload(real_now)), encoding="utf-8")
        return vlo.TaskResult(name, "ok", 0.0)

    monkeypatch.setattr(vlo.Orchestrator, "module", fake_module)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "vps_live_orchestrator",
            "--lane",
            "releases",
            "--live-dir",
            str(live),
            "--state-dir",
            str(state_dir),
            "--data-dir",
            str(tmp_path / "data"),
        ],
    )
    assert vlo.main() == 0
    assert producer_calls == []
    assert public.stat().st_mtime_ns == before
    assert not (state_dir / "status-releases.json").exists()

    # A stale public heartbeat forces the producer to run, and only then does
    # the lane write its own status.
    stale = real_now - timedelta(seconds=vlo.RELEASE_HEARTBEAT_MAX_AGE_S + 60)
    artifact.write_text(json.dumps(_release_payload(stale)))
    os.utime(artifact, (int(stale.timestamp()), int(stale.timestamp())))
    assert vlo.main() == 0
    assert producer_calls == ["release_publications"]
    assert (state_dir / "status-releases.json").exists()
    assert "releases" in json.loads(public.read_text())["lanes"]


# Transaction regressions: exercise the real watcher entry point and canonical
# publication path, not a stand-in parent copy or a mock-only success signal.
def _watcher_argv(monkeypatch, state_dir, out, now):
    monkeypatch.setattr(sys, "argv", [
        "watch_release_publications", "--out", str(out),
        "--state-dir", str(state_dir), "--now", now.isoformat(),
    ])


def test_producer_holds_lock_until_final_public_replacement(tmp_path, monkeypatch):
    now = datetime(2026, 10, 14, 12, 31, tzinfo=timezone.utc)
    state_dir, out = tmp_path / "state", tmp_path / "public.json"
    _watcher_argv(monkeypatch, state_dir, out, now)
    monkeypatch.setattr(wrp, "detect", lambda **kw: ({}, _release_payload(now)))
    real_write = wrp.atomic_write_json
    entered, finish = threading.Event(), threading.Event()
    results, errors = [], []

    def paused_write(path, payload, **kwargs):
        if path == out:
            entered.set()
            assert finish.wait(5), "test did not release final replacement"
        return real_write(path, payload, **kwargs)

    def first_writer():
        try:
            results.append(wrp.main())
        except BaseException as exc:
            errors.append(exc)

    monkeypatch.setattr(wrp, "atomic_write_json", paused_write)
    thread = threading.Thread(target=first_writer)
    thread.start()
    try:
        assert entered.wait(5)
        assert (state_dir / "release_publications_state.json").exists()
        assert not out.exists()
        assert wrp.main() == wrp.PRODUCER_BUSY_EXIT
    finally:
        finish.set()
        thread.join(5)
    assert not thread.is_alive() and not errors
    assert results == [0]
    assert json.loads(out.read_text())["built"] == now.isoformat()
    assert out.stat().st_mode & 0o777 == 0o644
    assert (state_dir / "release_publications_state.json").stat().st_mode & 0o777 == 0o600


def test_state_advance_public_failure_self_heals_on_ordinary_tick(tmp_path, monkeypatch):
    now = datetime(2026, 10, 14, 12, 31, tzinfo=timezone.utc)
    state_dir, out = tmp_path / "state", tmp_path / "live/release_publications.json"
    old = _release_payload(now - timedelta(seconds=10))
    wrp.atomic_write_json(out, old, mode=0o644)
    old_bytes = out.read_bytes()
    _watcher_argv(monkeypatch, state_dir, out, now)
    candidate = _release_payload(now)
    candidate["publications"] = [{"event_id": "cpi:2026-10-14", "data_ready": True}]
    monkeypatch.setattr(wrp, "detect", lambda **kw: (dict(kw["state"]), candidate))
    real_write = wrp.atomic_write_json

    def fail_public(path, payload, **kwargs):
        if path == out:
            raise OSError("controlled failed public replacement")
        return real_write(path, payload, **kwargs)

    monkeypatch.setattr(wrp, "atomic_write_json", fail_public)
    with pytest.raises(OSError):
        wrp.main()
    assert out.read_bytes() == old_bytes
    state = json.loads((state_dir / "release_publications_state.json").read_text())
    assert state["publication_candidate_sha256"] == wrp.publication_digest(candidate)
    monkeypatch.setattr(wrp, "atomic_write_json", real_write)
    monkeypatch.setattr(wrp, "tick_due", lambda **kw: {"probe_due": False})
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        assert Path(args[args.index("--out") + 1]) == out
        return SimpleNamespace(returncode=wrp.main(), stdout="", stderr="")

    orch = vlo.Orchestrator(live_dir=out.parent, state_dir=state_dir,
        data_dir=tmp_path / "data", now=now, runner=runner)
    orch.releases()
    assert len(calls) == 1  # The fresh old heartbeat must not hide the lost write.
    assert out.read_bytes() != old_bytes
    assert json.loads(out.read_text()) == candidate
    assert orch.results[0].status == "ok"
    assert not orch.results[0].published


@pytest.mark.parametrize("defect", ["schema", "rows", "clock", "nonfinite"])
def test_invalid_candidate_never_changes_state_or_public(tmp_path, monkeypatch, defect):
    now = datetime(2026, 10, 14, 12, 31, tzinfo=timezone.utc)
    state_dir, out = tmp_path / "state", tmp_path / "public.json"
    state_path = state_dir / "release_publications_state.json"
    wrp.atomic_write_json(state_path, {"sentinel": "last-good"})
    wrp.atomic_write_json(out, _release_payload(now), mode=0o644)
    before = state_path.read_bytes(), out.read_bytes()
    candidate = _release_payload(now)
    if defect == "schema": candidate["schema"] = "wrong"
    elif defect == "rows": candidate["publications"] = ["not an object"]
    elif defect == "clock": candidate["built"] = "2026-10-14T12:31:00"
    else: candidate["invalid_number"] = float("nan")
    monkeypatch.setattr(wrp, "detect", lambda **kw: ({}, candidate))
    _watcher_argv(monkeypatch, state_dir, out, now)
    with pytest.raises(ValueError):
        wrp.main()
    assert (state_path.read_bytes(), out.read_bytes()) == before
    lock = wrp.producer_lock(state_dir)
    assert lock is not None
    lock.close()


@pytest.mark.parametrize("artifact", ["missing", "stale", "invalid", "future"])
def test_zero_exit_cannot_report_unusable_public_artifact_healthy(tmp_path, monkeypatch, artifact):
    now = datetime(2026, 10, 14, 12, 31, tzinfo=timezone.utc)
    out = tmp_path / "live/release_publications.json"
    if artifact != "missing":
        payload = _release_payload(now - timedelta(minutes=5))
        if artifact == "invalid": payload["publications"] = None
        if artifact == "future": payload["built"] = (now + timedelta(minutes=5)).isoformat()
        wrp.atomic_write_json(out, payload, mode=0o644)
    before = out.read_bytes() if out.exists() else None
    monkeypatch.setattr(wrp, "tick_due", lambda **kw: {"probe_due": True})
    orch = vlo.Orchestrator(live_dir=out.parent, state_dir=tmp_path / "state",
        data_dir=tmp_path / "data", now=now,
        runner=lambda *a, **kw: SimpleNamespace(returncode=0, stdout="", stderr=""))
    orch.releases()
    assert orch.results[0].status == "invalid"
    assert not orch.results[0].published
    assert (out.read_bytes() if out.exists() else None) == before


def test_lock_io_error_is_not_a_successful_busy_skip(tmp_path, monkeypatch):
    def broken_lock(*args):
        raise OSError("controlled lock I/O failure")
    monkeypatch.setattr(wrp.fcntl, "flock", broken_lock)
    with pytest.raises(OSError):
        wrp.producer_lock(tmp_path / "state")


def test_parser_upgrade_honors_upstream_backoff(tmp_path):
    now = CPI_SCHEDULED_2026_10_14 + timedelta(minutes=30)
    row = _cpi_row(last_probe_at=(now - timedelta(seconds=2)).isoformat())
    row["retry_after_at"] = (now + timedelta(seconds=120)).isoformat()
    row["backoff_until"] = (now + timedelta(seconds=30)).isoformat()
    state = _cpi_state(row=row, publication=_cpi_publication(parser_version=1))
    calls = []
    new_state, _ = wrp.detect(now=now, state=state,
        fetcher=_cpi_fetcher(calls, CPI_SEPTEMBER_PAGE))
    assert _cpi_calls(calls) == []
    assert "cpi:2026-10-14" in wrp._parser_upgrade_keys(
        [_CPI_EVENT], new_state["publications"])
    wrp.detect(now=now + timedelta(seconds=121), state=new_state,
        fetcher=_cpi_fetcher(calls, CPI_SEPTEMBER_PAGE))
    assert _cpi_calls(calls)


def test_fast_compatibility_exists_only_until_dedicated_unit_install(tmp_path, monkeypatch):
    marker = tmp_path / "release.timer"
    monkeypatch.setattr(vlo, "RELEASE_TIMER_PATH", marker)
    for installed in (False, True):
        if installed: marker.symlink_to("/dev/null")  # A deliberate mask owns the lane.
        orch = vlo.Orchestrator(live_dir=tmp_path / "live", state_dir=tmp_path / "state",
            data_dir=tmp_path / "data", now=datetime(2026, 10, 14, 3, 1, tzinfo=timezone.utc))
        calls = []
        def release_tick():
            calls.append("releases")
            orch.idle = True
        orch.releases = release_tick
        orch.module = lambda name, *a, **kw: calls.append(name) or vlo.TaskResult(name, "ok", 0)
        orch.fast()
        assert ("releases" in calls) is not installed
        assert "display_quotes" in calls
        assert not orch.idle


# Execute the actual deployment scripts against a hermetic systemd model.
ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / "app/deploy/update.sh"
SERVICE = "macro-live-releases.service"
TIMER = "macro-live-releases.timer"

STUB = r'''
import datetime, fcntl, json, os, pathlib, shutil, sys
root = pathlib.Path(os.environ["DEPLOY_FIXTURE_DIR"])
state_file = root / "manager.json"
state = json.loads(state_file.read_text())
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "trace.jsonl").open("a") as output:
    output.write(json.dumps([name, *args]) + "\n")
def save():
    state_file.write_text(json.dumps(state))
def finish(rc=0):
    save()
    raise SystemExit(rc)
if name == "journalctl": finish()
if name == "id": print(0); finish()
if name == "crontab":
    if args == ["-l"]: print("# retained crontab")
    else: (root / "crontab").write_text(pathlib.Path(args[0]).read_text())
    finish()
if name == "systemd-analyze":
    finish(1 if os.environ.get("FAIL_PREFLIGHT") else 0)
if name == "install":
    if os.environ.get("FAIL_INSTALL") and args[-1].endswith(".timer") and not (root / "install_failed").exists():
        (root / "install_failed").touch()
        finish(1)
    shutil.copyfile(args[-2], args[-1]); finish()
if name == "flock":
    try:
        fcntl.flock(int(args[-1]), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        finish(1)
    finish()
action = args[0]
unit = args[-1]
row = state.setdefault(unit, {})
if action == "is-enabled": finish(0 if row.get("enabled") else 1)
if action == "is-active": finish(0 if row.get("active") else 1)
if action == "show":
    prop = args[args.index("-p")+1]
    present = (root / "units" / unit).exists()
    if prop == "LoadState": print("loaded" if present else "not-found")
    elif prop == "ActiveState": print("active" if row.get("active") else "inactive")
    else: print(100 if row.get("active") and unit.endswith(".service") else 0)
    finish()
if action == "stop":
    if os.environ.get("FAIL_STOP_UNIT") == unit: finish(1)
    if unit == "macro-live-releases.service" and state.get("smoke_started") and os.environ.get("FAIL_ROLLBACK_DRAIN"):
        row["active"] = True; finish(1)
    if not (root / "units" / unit).exists(): finish(1)
    row["active"] = False; finish()
if action == "daemon-reload": finish()
if action == "disable":
    row["active"] = False; row["enabled"] = False; finish()
if action == "enable":
    row["enabled"] = True; row["active"] = "--now" in args; finish()
if action == "start":
    if unit == "macro-live-releases.service":
        assert not state["macro-live-fast.timer"].get("active")
        assert not state["macro-live-fast.service"].get("active")
        # A manual fast process must also be excluded throughout handoff.
        with (root / "state/fast.lock").open("a") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise AssertionError("dedicated writer started without owning fast.lock")
        state["smoke_started"] = True
        row["active"] = bool(os.environ.get("FAIL_ROLLBACK_DRAIN"))
        if not os.environ.get("STALE_SMOKE"):
            (root / "live/release_publications.json").write_text(json.dumps({
                "built": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "schema": "release_publications.v2", "due": [], "source_health": [],
                "events": [], "publications": []}))
        finish(1 if os.environ.get("FAIL_SMOKE") else 0)
    if unit == "macro-live-fast.service":
        with (root / "state/fast.lock").open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        (root / "live/orchestrator_status.json").write_text("{}")
        (root / "live/quotes.json").write_text('{"meta":{"resolved":20}}')
        row["active"] = False
        finish(1 if os.environ.get("FAIL_FAST_SMOKE") else 0)
    row["active"] = True; finish()
raise AssertionError((name, args))
'''


@pytest.fixture
def deploy(tmp_path):
    for path in ("units", "state", "live", "bin", "app/app/deploy", "app/.venv/bin"):
        (tmp_path / path).mkdir(parents=True, exist_ok=True)
    for unit in ("macro-live-fast.service", "macro-live-fast.timer", SERVICE, TIMER):
        (tmp_path / "app/app/deploy" / unit).write_text("[Unit]\nDescription=fixture\n")
        if "fast" in unit:
            (tmp_path / "units" / unit).write_text("existing fast unit\n")
    (tmp_path / "app/.venv/bin/python").symlink_to(sys.executable)
    manager = {
        "macro-live-fast.timer": {"enabled": True, "active": True},
        "macro-live-fast.service": {"active": True},
    }
    (tmp_path / "manager.json").write_text(json.dumps(manager))
    for name in ("systemctl", "systemd-analyze", "install", "flock", "journalctl"):
        path = tmp_path / "bin" / name
        path.write_text("#!" + sys.executable + "\n" + STUB)
        path.chmod(0o755)
    (tmp_path / "live/release_publications.json").write_text(
        '{"built":"2000-01-01T00:00:00+00:00","events":[],"publications":[]}')
    return tmp_path


def run_deploy(root, **faults):
    source = UPDATE.read_text()
    helpers = source.split("# BEGIN W1B5_UNIT_STOP_HELPERS\n", 1)[1].split(
        "# END W1B5_UNIT_STOP_HELPERS", 1)[0]
    handoff = source.split("# BEGIN RELEASE_LANE_RECONCILIATION\n", 1)[1].split(
        "# END RELEASE_LANE_RECONCILIATION", 1)[0]
    handoff = handoff.replace("/etc/systemd/system", str(root / "units"))
    handoff = handoff.replace("/var/lib/macro-live/state", str(root / "state"))
    handoff = handoff.replace("/var/lib/macro-live/public/live", str(root / "live"))
    handoff = handoff.replace("/etc/macro-live.env", str(root / "no-env"))
    script = "set -euo pipefail\nAPP_DIR=" + shlex.quote(str(root / "app"))
    script += "\nCHANGED=''\nRECONCILED=0\n" + helpers + handoff
    result = subprocess.run(["bash"], input=script, text=True, capture_output=True,
        env={**os.environ, "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"],
             "DEPLOY_FIXTURE_DIR": str(root), **faults}, timeout=20)
    state = json.loads((root / "manager.json").read_text())
    calls = [json.loads(line) for line in (root / "trace.jsonl").read_text().splitlines()]
    return result, state, calls


def test_missing_lane_migrates_on_repository_noop_and_is_idempotent(deploy):
    result, state, calls = run_deploy(deploy)
    assert result.returncode == 0, result.stderr
    assert state[TIMER] == {"enabled": True, "active": True}
    assert state["macro-live-fast.timer"]["active"]
    stop = calls.index(["systemctl", "stop", "macro-live-fast.service"])
    smoke = calls.index(["systemctl", "start", SERVICE])
    arm = calls.index(["systemctl", "enable", "--now", TIMER])
    assert stop < smoke < arm
    (deploy / "trace.jsonl").unlink()
    result, _, calls = run_deploy(deploy)
    assert result.returncode == 0, result.stderr
    assert not any(call[1] in ("start", "stop", "enable") for call in calls)


@pytest.mark.parametrize("fault", ["FAIL_PREFLIGHT", "FAIL_INSTALL", "FAIL_SMOKE", "STALE_SMOKE"])
def test_failed_handoff_preserves_or_restores_legacy_ownership(deploy, fault):
    result, state, calls = run_deploy(deploy, **{fault: "1"})
    assert result.returncode != 0
    assert state["macro-live-fast.timer"]["active"]
    assert not (deploy / "units" / TIMER).exists()
    assert not state.get(TIMER, {}).get("enabled")
    if fault == "FAIL_PREFLIGHT":
        assert not any(call[1] == "stop" for call in calls)
    if fault in ("FAIL_SMOKE", "STALE_SMOKE"):
        smoke = calls.index(["systemctl", "start", SERVICE])
        drain = calls.index(["systemctl", "stop", SERVICE], smoke)
        resume = calls.index(["systemctl", "start", "macro-live-fast.timer"], drain)
        assert smoke < drain < resume


def test_uncertain_dedicated_writer_never_restores_fast_ownership(deploy):
    result, state, calls = run_deploy(deploy, FAIL_SMOKE="1", FAIL_ROLLBACK_DRAIN="1")
    assert result.returncode != 0
    assert not state["macro-live-fast.timer"]["active"]
    assert (deploy / "units" / TIMER).exists()
    assert ["systemctl", "start", "macro-live-fast.timer"] not in calls
    assert "dedicated writer not drained" in result.stderr


def test_manual_fast_invocation_blocks_handoff_even_with_inactive_service(deploy):
    with (deploy / "state/fast.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result, state, calls = run_deploy(deploy)
    assert result.returncode != 0
    assert ["systemctl", "start", SERVICE] not in calls
    assert not (deploy / "units" / TIMER).exists()
    assert state["macro-live-fast.timer"]["active"]


def test_installed_but_disabled_release_timer_stays_paused_on_unit_update(deploy):
    for unit in (SERVICE, TIMER):
        (deploy / "units" / unit).write_text("previous unit revision\n")
    result, state, calls = run_deploy(deploy)
    assert result.returncode == 0, result.stderr
    assert not state.get(TIMER, {}).get("enabled")
    assert not state.get(TIMER, {}).get("active")
    assert ["systemctl", "start", SERVICE] not in calls
    assert ["systemctl", "enable", "--now", TIMER] not in calls


def test_paused_live_plane_defers_first_handoff(deploy):
    state = json.loads((deploy / "manager.json").read_text())
    state["macro-live-fast.timer"]["active"] = False
    (deploy / "manager.json").write_text(json.dumps(state))
    result, _, calls = run_deploy(deploy)
    assert result.returncode == 0, result.stderr
    assert ["systemctl", "start", SERVICE] not in calls
    assert not (deploy / "units" / TIMER).exists()


def test_masked_release_timer_is_preserved(deploy):
    (deploy / "units" / TIMER).symlink_to("/dev/null")
    result, _, calls = run_deploy(deploy)
    assert result.returncode == 0, result.stderr
    assert (deploy / "units" / TIMER).is_symlink()
    assert not any(call[1] in ("start", "stop", "enable") for call in calls)



def run_setup_transaction(root, *, fail_after_smoke=False, **faults):
    source = (ROOT / "app/deploy/live-setup.sh").read_text()
    transaction = source.split("# BEGIN LIVE_SETUP_TRANSACTION\n", 1)[1].split(
        "# END LIVE_SETUP_TRANSACTION", 1)[0]
    smoke = 'log "[3/6] systemd services + timers"' + source.split(
        'log "[3/6] systemd services + timers"', 1)[1].split(
        'log "[5/6] enable replacement timers"', 1)[0]
    for lane in ("fast", "releases", "snapshot", "bars", "prophet", "closepass", "breadth"):
        for suffix in ("service", "timer"):
            unit = f"macro-live-{lane}.{suffix}"
            target = root / "app/app/deploy" / unit
            if not target.exists(): target.write_text("[Unit]\nDescription=new fixture\n")
    script = "set -euo pipefail\n"
    for key, value in {
        "APP_DIR": root / "app", "BASE_DIR": root, "STATE_DIR": root / "state",
        "PUBLIC_DIR": root / "live", "LIVE_DIR": root / "live", "VENV": root / "app/.venv",
    }.items():
        script += key + "=" + shlex.quote(str(value)) + "\n"
    script += 'log() { echo "$*"; }\n' + transaction + smoke
    script += "\nexit 23\n" if fail_after_smoke else "\nsetup_complete=1\n"
    script = script.replace("/etc/systemd/system", str(root / "units"))
    result = subprocess.run(["bash"], input=script, text=True, capture_output=True,
        env={**os.environ, "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"],
             "DEPLOY_FIXTURE_DIR": str(root), **faults}, timeout=25)
    state = json.loads((root / "manager.json").read_text())
    calls = [json.loads(line) for line in (root / "trace.jsonl").read_text().splitlines()]
    return result, state, calls


@pytest.mark.parametrize("fault", ["FAIL_PREFLIGHT", "FAIL_INSTALL", "FAIL_SMOKE", "FAIL_FAST_SMOKE"])
def test_setup_failure_restores_original_unit_bytes_and_timer_intent(deploy, fault):
    before = {p.name: p.read_bytes() for p in (deploy / "units").iterdir()}
    result, state, calls = run_setup_transaction(deploy, **{fault: "1"})
    assert result.returncode != 0
    assert {p.name: p.read_bytes() for p in (deploy / "units").iterdir()} == before
    assert state["macro-live-fast.timer"]["active"]
    assert state["macro-live-fast.timer"]["enabled"]
    assert not state.get(TIMER, {}).get("enabled")
    assert (deploy / "live/release_publications.json").exists()
    if fault == "FAIL_FAST_SMOKE":
        smoke = calls.index(["systemctl", "start", "macro-live-fast.service"])
        drain = calls.index(["systemctl", "stop", "macro-live-fast.service"], smoke)
        resume = calls.index(["systemctl", "start", "macro-live-fast.timer"], drain)
        assert smoke < drain < resume


def test_setup_uncertain_writer_preserves_units_and_does_not_resume_legacy(deploy):
    result, state, calls = run_setup_transaction(deploy, FAIL_SMOKE="1", FAIL_ROLLBACK_DRAIN="1")
    assert result.returncode != 0
    assert (deploy / "units" / TIMER).exists()
    assert not state["macro-live-fast.timer"]["active"]
    assert ["systemctl", "start", "macro-live-fast.timer"] not in calls
    assert "rollback held" in result.stdout


def test_setup_preserves_preexisting_disabled_release_ownership(deploy):
    for unit in (SERVICE, TIMER):
        (deploy / "units" / unit).write_text("previous release bytes\n")
    result, state, calls = run_setup_transaction(deploy, fail_after_smoke=True)
    assert result.returncode == 23
    assert (deploy / "units" / TIMER).read_text() == "previous release bytes\n"
    assert not state.get(TIMER, {}).get("active")
    assert not state.get(TIMER, {}).get("enabled")
    assert ["systemctl", "start", SERVICE] not in calls


def test_first_setup_failure_withdraws_public_only_after_all_writers_drain(deploy):
    for p in (deploy / "units").iterdir(): p.unlink()
    (deploy / "manager.json").write_text("{}")
    result, state, calls = run_setup_transaction(deploy, fail_after_smoke=True)
    assert result.returncode == 23
    assert not (deploy / "live").exists()
    backups = list(deploy.glob("public.failed.*"))
    assert len(backups) == 1 and (backups[0] / "release_publications.json").exists()
    assert (deploy / "state/fast.lock").exists()
    assert (deploy / "state/release_publications.lock").exists()
    assert not list((deploy / "units").iterdir())
    assert all(not row.get("active") for row in state.values() if isinstance(row, dict))



def run_rollback(root, **faults):
    source = (ROOT / "app/deploy/live-rollback.sh").read_text()
    source = source.replace('BASE_DIR="/var/lib/macro-live"', "BASE_DIR=" + shlex.quote(str(root)))
    source = source.replace('PUBLIC_DIR="$BASE_DIR/public"', 'PUBLIC_DIR="$BASE_DIR/live"')
    source = source.replace("/etc/systemd/system", str(root / "units"))
    source = source.replace("/etc/macro-live.env", str(root / "no-env"))
    for name in ("id", "crontab"):
        path = root / "bin" / name
        path.write_text("#!" + sys.executable + "\n" + STUB)
        path.chmod(0o755)
    result = subprocess.run(["bash"], input=source, text=True, capture_output=True,
        env={**os.environ, "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"],
             "DEPLOY_FIXTURE_DIR": str(root), **faults}, timeout=25)
    return result, json.loads((root / "manager.json").read_text())


def test_rollback_preserves_last_good_files_until_manual_publisher_is_drained(deploy):
    before = (deploy / "live/release_publications.json").read_bytes()
    with (deploy / "state/release_publications.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result, state = run_rollback(deploy)
    assert result.returncode != 0
    assert (deploy / "live/release_publications.json").read_bytes() == before
    assert not (deploy / "crontab").exists()
    assert not state["macro-live-fast.timer"]["active"]
    result, state = run_rollback(deploy)
    assert result.returncode == 0, result.stderr
    assert not (deploy / "live").exists()
    saved = list(deploy.glob("public.rollback.*"))
    assert len(saved) == 1 and (saved[0] / "release_publications.json").read_bytes() == before
    assert "/usr/local/bin/macro-live" in (deploy / "crontab").read_text()


def test_rollback_failed_service_drain_cannot_withdraw_public_artifacts(deploy):
    result, state = run_rollback(deploy, FAIL_STOP_UNIT="macro-live-fast.service")
    assert result.returncode != 0
    assert (deploy / "live/release_publications.json").exists()
    assert not (deploy / "crontab").exists()
    assert state["macro-live-fast.service"]["active"]


# ─────────────────────────────────────────────────────────────────────────────
# D04-A — quote/pulse source clocks, universe-true pulse coverage, ABSENT-OK dead-man
# ─────────────────────────────────────────────────────────────────────────────

def _epoch_ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def test_quotes_payload_never_stamps_build_time_as_source_clock():
    ms = _epoch_ms("2026-10-13T14:00:00+00:00")
    payload = build_flow_quotes(
        {"leaders": [{"ticker": "AAA"}, {"ticker": "BBB"}]},
        {
            "quotes": {
                "AAA": {"price": 10.0, "ts": ms},
                "BBB": {"price": 20.0, "ts": ms + 60_000},
            },
            "meta": {},
        },
    )
    assert payload["asof"] is None
    assert payload["ts"] is None
    assert payload["meta"]["upstream_asof"] is None


def test_quotes_meta_source_asof_is_median_of_real_quote_clocks():
    leaders = [{"ticker": name} for name in ("AAA", "BBB", "CCC", "DDD", "EEE")]
    priced = {
        "AAA": {"price": 10.0, "ts": _epoch_ms("2026-10-13T14:00:00+00:00")},
        "BBB": {"price": 11.0, "ts": _epoch_ms("2026-10-13T14:10:00+00:00")},
        "CCC": {"price": 12.0, "ts": _epoch_ms("2026-10-13T14:20:00+00:00")},
        "DDD": {
            "price": 13.0,
            "ts": _epoch_ms("2026-10-13T15:59:00+00:00"),
            "tsSynthetic": True,
        },
        "EEE": {"price": 14.0},
    }
    payload = build_flow_quotes(
        {"leaders": leaders},
        {"quotes": priced, "meta": {}},
    )
    assert payload["meta"]["source_asof"] == "2026-10-13T14:10:00+00:00"
    assert isinstance(payload["meta"]["built_at"], str) and payload["meta"]["built_at"]
    datetime.fromisoformat(payload["meta"]["built_at"])
    assert payload["meta"]["requested"] == 5
    assert payload["meta"]["resolved"] == 5
    assert payload["meta"]["coverage"] == 1.0

    synthetic_only = build_flow_quotes(
        {"leaders": [{"ticker": "DDD"}, {"ticker": "EEE"}]},
        {
            "quotes": {
                "DDD": {
                    "price": 13.0,
                    "ts": _epoch_ms("2026-10-13T15:59:00+00:00"),
                    "tsSynthetic": True,
                },
                "EEE": {"price": 14.0},
            },
            "meta": {},
        },
    )
    assert synthetic_only["meta"]["source_asof"] is None


def test_quote_validator_rejects_board_payload_without_source_clock(tmp_path: Path):
    import inspect

    path = tmp_path / "intraday_quotes.json"
    path.write_text(json.dumps({
        "quotes": {f"S{i}": {"price": float(i + 1)} for i in range(5)},
        "meta": {"requested": 5, "resolved": 5, "source_asof": None},
    }))
    assert vlo.quote_snapshot_error(path, min_resolved=5, min_coverage=0.9) is None

    missing = vlo.quote_snapshot_error(
        path, min_resolved=5, min_coverage=0.9, require_source_clock=True,
    )
    assert isinstance(missing, str) and missing and "source clock" in missing

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["meta"]["source_asof"] = "2026-10-13T14:10:00+00:00"
    path.write_text(json.dumps(payload))
    assert vlo.quote_snapshot_error(
        path, min_resolved=5, min_coverage=0.9, require_source_clock=True,
    ) is None

    payload["meta"]["source_asof"] = "garbage"
    path.write_text(json.dumps(payload))
    garbage = vlo.quote_snapshot_error(
        path, min_resolved=5, min_coverage=0.9, require_source_clock=True,
    )
    assert isinstance(garbage, str) and garbage

    module_src = inspect.getsource(vlo)
    snapshot_src = inspect.getsource(vlo.Orchestrator.snapshot)
    assert module_src.count("require_source_clock=True") == 1
    assert snapshot_src.count("require_source_clock=True") == 1


def test_fastpath_stamps_source_clock_from_bars_not_build_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    now_et = pd.Timestamp.now(tz="America/New_York").normalize()
    start_9 = (now_et + pd.Timedelta(hours=9)).tz_convert("UTC")
    start_10 = (now_et + pd.Timedelta(hours=10)).tz_convert("UTC")
    index = pd.DatetimeIndex([start_9, start_10], name="ts")
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000.0, 2000.0],
        },
        index=index,
    )
    intraday = tmp_path / "intraday"
    intraday.mkdir()
    (intraday / "AAA.parquet").touch()
    monkeypatch.setattr(bif.pd, "read_parquet", lambda _: frame.copy())
    monkeypatch.delenv("MACRO_INTRADAY_DIR", raising=False)
    monkeypatch.setattr(bif, "_resolve_universe", lambda cfg, data_root: ["AAA"])

    today = datetime.now(timezone.utc).date()
    as_of = datetime(today.year, today.month, today.day, 16, 0, tzinfo=timezone.utc)
    site = tmp_path / "site"
    bif._run_fastpath({}, tmp_path, site, as_of_arg=as_of.isoformat())
    pulse = json.loads((site / "live" / "flow_pulse.json").read_text(encoding="utf-8"))

    assert datetime.fromisoformat(pulse["source_asof"]) == start_10.to_pydatetime()
    assert datetime.fromisoformat(pulse["as_of"]) == as_of
    assert pulse["stale"] is False
    assert bif._today_bars("AAA", tmp_path)[-1]["ts"]


def test_fastpath_failed_ticker_stays_in_denominator_as_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    def today_bars(ticker: str, data_root: Path) -> list[dict]:
        if ticker == "BBB":
            raise RuntimeError("boom")
        return [
            {
                "ts": "2026-10-13T13:00:00+00:00",
                "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0,
            },
            {
                "ts": "2026-10-13T14:00:00+00:00",
                "open": 1.5, "high": 2.5, "low": 1.0, "close": 2.0, "volume": 200.0,
            },
        ]

    monkeypatch.setattr(bif, "_resolve_universe", lambda cfg, data_root: ["AAA", "BBB", "CCC"])
    monkeypatch.setattr(bif, "_today_bars", today_bars)
    site = tmp_path / "site"
    bif._run_fastpath({}, tmp_path, site)
    pulse = json.loads((site / "live" / "flow_pulse.json").read_text(encoding="utf-8"))

    assert pulse["n_tickers"] == 3
    assert pulse["n_universe"] == 3
    bbb = next(row for row in pulse["tickers"] if row["ticker"] == "BBB")
    assert bbb["bars_today"] is None
    assert bbb["error"] == "RuntimeError"
    for key in (
        "vwap", "cum_vol", "vol_durability", "higher_lows", "rvol_tod",
        "session_high", "session_low", "bars_above_vwap",
        "last_close", "last_high", "last_low",
    ):
        assert bbb.get(key) is None
    assert pulse["mode"] == "fastpath"


def test_flow_pulse_validator_measures_coverage_against_universe(tmp_path: Path):
    path = tmp_path / "flow_pulse.json"
    clock = "2026-10-13T14:10:00+00:00"

    def rows(with_bars: int, total: int) -> list[dict]:
        out = [{"ticker": f"T{i}", "bars_today": 2} for i in range(with_bars)]
        out.extend(
            {"ticker": f"E{i}", "bars_today": None, "error": "RuntimeError"}
            for i in range(total - with_bars)
        )
        return out

    path.write_text(json.dumps({
        "mode": "fastpath",
        "source_asof": clock,
        "n_universe": 10,
        "n_tickers": 8,
        "tickers": rows(8, 8),
    }))
    assert vlo.flow_pulse_error(path, min_coverage=0.80) is not None

    path.write_text(json.dumps({
        "mode": "fastpath",
        "source_asof": clock,
        "n_universe": 10,
        "n_tickers": 10,
        "tickers": rows(8, 10),
    }))
    assert vlo.flow_pulse_error(path, min_coverage=0.80) is None

    path.write_text(json.dumps({
        "mode": "fastpath",
        "source_asof": clock,
        "n_universe": 10,
        "n_tickers": 10,
        "tickers": rows(7, 10),
    }))
    assert vlo.flow_pulse_error(path, min_coverage=0.80) is not None

    path.write_text(json.dumps({
        "mode": "fastpath",
        "n_universe": 10,
        "n_tickers": 10,
        "tickers": rows(8, 10),
    }))
    assert vlo.flow_pulse_error(path, min_coverage=0.80) is not None


def _no_source_clock_failure(failures: list[str]) -> bool:
    return not any(
        failure.startswith("flow_pulse: source")
        or failure.startswith("flow_pulse: missing source_asof")
        or failure.startswith("flow_pulse: invalid source_asof")
        or failure.startswith("intraday_quotes:")
        for failure in failures
    )


def test_deadman_ages_pulse_and_board_quotes_from_source_clocks():
    now = _HEALTHY_STATUS_NOW
    stale = _healthy_vps_status()
    stale["checks"]["flow_pulse"]["source_asof"] = (
        now - timedelta(minutes=180)
    ).isoformat().replace("+00:00", "Z")
    stale["checks"]["intraday_quotes"] = {
        "source_asof": (now - timedelta(minutes=120)).isoformat().replace("+00:00", "Z"),
    }
    failures = evaluate_live_health(stale, now=now)
    assert any(failure.startswith("flow_pulse: source stale") for failure in failures), failures
    assert any(failure.startswith("intraday_quotes: source stale") for failure in failures), failures

    removed = _healthy_vps_status()
    removed["checks"]["flow_pulse"].pop("source_asof", None)
    removed["checks"].pop("intraday_quotes", None)
    failures = evaluate_live_health(removed, now=now)
    assert "flow_pulse: missing source_asof" in failures, failures
    assert "intraday_quotes: missing source_asof" in failures, failures

    missing = _healthy_vps_status()
    missing["checks"]["flow_pulse"].pop("source_asof", None)
    missing["checks"]["intraday_quotes"] = {"status": "missing"}
    failures = evaluate_live_health(missing, now=now)
    assert "flow_pulse: missing source_asof" in failures, failures
    assert "intraday_quotes: missing source_asof" in failures, failures

    absent = _healthy_vps_status()
    absent["checks"]["flow_pulse"]["source_asof"] = None
    absent["checks"]["intraday_quotes"] = {"source_asof": None}
    failures = evaluate_live_health(absent, now=now)
    assert "flow_pulse: missing source_asof" in failures, failures
    assert "intraday_quotes: missing source_asof" in failures, failures

    errored = _healthy_vps_status()
    errored["checks"]["flow_pulse"].pop("source_asof", None)
    errored["checks"]["intraday_quotes"] = {"error": "unavailable", "age_min": 3}
    failures = evaluate_live_health(errored, now=now)
    assert "flow_pulse: missing source_asof" in failures, failures
    assert "intraday_quotes: missing source_asof" in failures, failures

    fresh = _healthy_vps_status()
    fresh["checks"]["flow_pulse"]["source_asof"] = (
        now - timedelta(minutes=100)
    ).isoformat().replace("+00:00", "Z")
    fresh["checks"]["intraday_quotes"] = {
        "source_asof": (now - timedelta(minutes=20)).isoformat().replace("+00:00", "Z"),
    }
    assert _no_source_clock_failure(evaluate_live_health(fresh, now=now))

    unparseable = _healthy_vps_status()
    unparseable["checks"]["flow_pulse"]["source_asof"] = "not-a-time"
    unparseable["checks"]["intraday_quotes"] = {"source_asof": "not-a-time"}
    failures = evaluate_live_health(unparseable, now=now)
    assert "flow_pulse: invalid source_asof" in failures
    assert "intraday_quotes: invalid source_asof" in failures

    for when in (
        datetime(2026, 7, 20, 14, 30, tzinfo=timezone.utc),
        datetime(2026, 7, 20, 20, 30, tzinfo=timezone.utc),
        datetime(2026, 7, 19, 15, 0, tzinfo=timezone.utc),
    ):
        for variant in (stale, removed):
            failures = evaluate_live_health(variant, now=when)
            assert _no_source_clock_failure(failures), (when.isoformat(), variant.get("checks", {}).get("flow_pulse"), failures)


def _load_projection() -> "object":
    """Pull app.live_status_projection in a way that pins the absent-module defect
    instead of failing collection at PR time (the washout-turn-organ job imports
    this test file without the serving stack)."""
    spec = importlib_util.find_spec("app.live_status_projection")
    assert spec is not None, "projection module absent"
    return import_module("app.live_status_projection")


def test_status_projection_carries_pulse_source_clock_and_universe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    projection = _load_projection()

    now_et = pd.Timestamp.now(tz="America/New_York").normalize()
    start_9 = (now_et + pd.Timedelta(hours=9)).tz_convert("UTC")
    start_10 = (now_et + pd.Timedelta(hours=10)).tz_convert("UTC")
    index = pd.DatetimeIndex([start_9, start_10], name="ts")
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000.0, 2000.0],
        },
        index=index,
    )

    intraday = tmp_path / "intraday"
    intraday.mkdir()
    (intraday / "AAA.parquet").touch()
    (intraday / "BBB.parquet").touch()

    bars_by_ticker = {"AAA": frame.copy(), "BBB": frame.iloc[0:0].copy()}
    monkeypatch.setattr(bif.pd, "read_parquet", lambda p: bars_by_ticker[p.name.replace(".parquet", "")].copy())
    monkeypatch.delenv("MACRO_INTRADAY_DIR", raising=False)
    monkeypatch.setattr(bif, "_resolve_universe", lambda cfg, data_root: ["AAA", "BBB"])

    today = datetime.now(timezone.utc).date()
    as_of = datetime(today.year, today.month, today.day, 16, 0, tzinfo=timezone.utc)
    site = tmp_path / "site"
    bif._run_fastpath({}, tmp_path, site, as_of_arg=as_of.isoformat())
    pulse = json.loads((site / "live" / "flow_pulse.json").read_text(encoding="utf-8"))

    expected = {
        "mode": pulse["mode"],
        "n_tickers": pulse["n_tickers"],
        "with_bars": 1,
        "n_universe": pulse["n_universe"],
        "source_asof": pulse["source_asof"],
    }
    result = projection.flow_pulse_fields(pulse)
    assert result == expected
    assert list(result) == [
        "mode", "n_tickers", "with_bars", "n_universe", "source_asof",
    ]

    empty = projection.flow_pulse_fields({})
    assert empty == {"mode": None, "n_tickers": None, "with_bars": 0, "n_universe": None, "source_asof": None}


def test_status_projection_carries_board_quote_meta():
    projection = _load_projection()

    base_iso = "2026-10-13T14:00:00+00:00"
    leaders = [{"ticker": name} for name in ("AAA", "BBB", "CCC")]
    priced = {
        "AAA": {"price": 10.0, "ts": _epoch_ms("2026-10-13T14:00:00+00:00")},
        "BBB": {"price": 11.0, "ts": _epoch_ms("2026-10-13T14:10:00+00:00")},
        "CCC": {"price": 12.0, "ts": _epoch_ms("2026-10-13T14:20:00+00:00")},
    }
    payload = build_flow_quotes(
        {"leaders": leaders},
        {"quotes": priced, "meta": {}},
    )

    expected = {
        "requested": payload["meta"]["requested"],
        "resolved": payload["meta"]["resolved"],
        "coverage": payload["meta"]["coverage"],
        "source_asof": payload["meta"]["source_asof"],
        "built_at": payload["meta"]["built_at"],
    }
    result = projection.intraday_quotes_fields(payload)
    assert result == expected
    assert list(result) == ["requested", "resolved", "coverage", "source_asof", "built_at"]
    assert result["source_asof"] == "2026-10-13T14:10:00+00:00"

    assert projection.intraday_quotes_fields({}) == {
        "requested": None, "resolved": None, "coverage": None, "source_asof": None, "built_at": None,
    }
    assert projection.intraday_quotes_fields({"meta": "x"}) == {
        "requested": None, "resolved": None, "coverage": None, "source_asof": None, "built_at": None,
    }


def test_deadman_composes_real_board_through_status_projection():
    projection = _load_projection()

    now = _HEALTHY_STATUS_NOW
    base_iso = (now - timedelta(minutes=20)).isoformat()
    leaders = [{"ticker": name} for name in ("AAA", "BBB", "CCC")]
    priced = {
        "AAA": {"price": 10.0, "ts": _epoch_ms(base_iso)},
        "BBB": {"price": 11.0, "ts": _epoch_ms(base_iso)},
        "CCC": {"price": 12.0, "ts": _epoch_ms(base_iso)},
    }
    board = build_flow_quotes({"leaders": leaders}, {"quotes": priced, "meta": {}})

    pulse = {
        "mode": "fastpath",
        "n_tickers": 116,
        "n_universe": 116,
        "source_asof": (now - timedelta(minutes=40)).isoformat().replace("+00:00", "Z"),
        "tickers": [{"ticker": f"T{i}", "bars_today": 2} for i in range(116)],
    }

    status = _healthy_vps_status()
    status["checks"]["intraday_quotes"] = projection.intraday_quotes_fields(board)
    status["checks"]["flow_pulse"].update(projection.flow_pulse_fields(pulse))

    failures = evaluate_live_health(status, now=now)
    assert _no_source_clock_failure(failures), failures

    aged_board = build_flow_quotes(
        {"leaders": leaders},
        {"quotes": {k: {"price": v["price"], "ts": _epoch_ms((now - timedelta(minutes=120)).isoformat())} for k, v in priced.items()}, "meta": {}},
    )
    aged_pulse = dict(pulse, source_asof=(now - timedelta(minutes=180)).isoformat().replace("+00:00", "Z"))
    status_stale = _healthy_vps_status()
    status_stale["checks"]["intraday_quotes"] = projection.intraday_quotes_fields(aged_board)
    status_stale["checks"]["flow_pulse"].update(projection.flow_pulse_fields(aged_pulse))
    stale_failures = evaluate_live_health(status_stale, now=now)
    assert any(failure.startswith("flow_pulse: source stale") for failure in stale_failures), stale_failures
    assert any(failure.startswith("intraday_quotes: source stale") for failure in stale_failures), stale_failures

    clockless_board = build_flow_quotes(
        {"leaders": [{"ticker": "AAA"}, {"ticker": "BBB"}]},
        {"quotes": {"AAA": {"price": 10.0}, "BBB": {"price": 11.0}}, "meta": {}},
    )
    status_clockless = _healthy_vps_status()
    status_clockless["checks"]["intraday_quotes"] = projection.intraday_quotes_fields(clockless_board)
    clockless_failures = evaluate_live_health(status_clockless, now=now)
    assert "intraday_quotes: missing source_asof" in clockless_failures, clockless_failures


def test_projection_module_imports_without_the_serving_stack():
    """Subprocess import of app.live_status_projection must not pull in fastapi,
    starlette, or pydantic — the washout-turn-organ job installs none of them."""
    import subprocess

    completed = subprocess.run(
        [sys.executable, "-c",
         "import sys, app.live_status_projection;"
         "print(sorted(m for m in sys.modules if m.split('.')[0] in ('fastapi','starlette','pydantic')))"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "[]", completed.stdout
