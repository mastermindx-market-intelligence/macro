from __future__ import annotations

import errno
import hashlib
import inspect
import json
import os
import shutil
import stat
import subprocess
import sys
import textwrap
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


def _claims_identity_event(day="2026-07-30"):
    return {"event_id": "claims:" + day, "type": "CLAIMS", "date": day,
            "time_et": "08:30", "label": "Initial jobless claims", "is_context_only": True}


def _claims_identity_tick(monkeypatch, body, *, state=None, day="2026-07-30", hour=15, minute=0):
    event = _claims_identity_event(day)
    monkeypatch.setattr(wrp, "scheduled_releases", lambda *a, **k: [event])
    if state is None:
        state = {"coverage_started_at_by_type": {"CLAIMS": day + "T12:00:00+00:00"},
                 "sources": {}, "publications": {}}
    now = datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=timezone.utc)
    return wrp.detect(now=now, state=state, fetcher=lambda *a: _http_result(body))


def test_claims_identity_undated_or_other_week_listing_cannot_publish(monkeypatch):
    for body in (
        DOL_JULY_30_LISTING.replace(b"20260730", b"20260723").replace(b"July 30, 2026", b"July 23, 2026"),
        DOL_JULY_30_LISTING.replace(b"20260730", b"20260806").replace(b"July 30, 2026", b"August 6, 2026"),
        CLAIMS_JULY_30_PAGE,  # raw claims-shaped page is not a dated listing entry
        DOL_JULY_30_LISTING.replace(b"July 30, 2026", b"July 23, 2026"),  # even with matching URL
        DOL_JULY_30_LISTING.replace(b"July 30, 2026", b"July 32, 2026"),
    ):
        _, payload = _claims_identity_tick(monkeypatch, body)
        assert not any(row.get("data_ready") for row in payload["publications"])
        assert all("actual" not in row for row in payload["publications"])


def test_claims_identity_wrong_reference_week_cannot_be_verified(monkeypatch):
    _, payload = _claims_identity_tick(monkeypatch, DOL_JULY_30_LISTING.replace(b"July 25", b"July 18"))
    row = payload["publications"][0]
    assert row["status"] == "published_unparsed" and row["data_ready"] is False
    assert "actual" not in row


def test_claims_identity_printed_date_supports_dol_path_forms(monkeypatch):
    for path in (b"/newsroom/releases/eta/eta20260730", b"/index.php/newsroom/releases/eta/eta20260730", b"/node/186182"):
        body = DOL_JULY_30_LISTING.replace(b"/newsroom/releases/eta/eta20260730", path)
        _, payload = _claims_identity_tick(monkeypatch, body)
        row = payload["publications"][0]
        assert row["data_ready"] is True
        assert row["actual"]["initial_claims"] == 219_000
        assert row["source_document_date"] == "2026-07-30"
        assert row["source_url"] == "https://www.dol.gov/index.php" + path.decode().removeprefix("/index.php")
        assert wrp._claims_publication_is_bound(row)


def test_claims_identity_node_needs_own_date_not_another_nodes_date(monkeypatch):
    other = DOL_JULY_30_LISTING.replace(b"/newsroom/releases/eta/eta20260730", b"/node/111")
    other = other.replace(b"July 30, 2026", b"July 23, 2026").replace(b"219,000", b"999,000")
    correct = DOL_JULY_30_LISTING.replace(b"/newsroom/releases/eta/eta20260730", b"/node/222")
    correct = correct.replace(b"<h3>", b"<img src='icon.png'><br/><h3>")
    _, payload = _claims_identity_tick(monkeypatch, other + correct)
    row = payload["publications"][0]
    assert row["actual"]["initial_claims"] == 219_000
    assert row["source_url"].endswith("/node/222")


def test_claims_identity_holiday_and_year_boundary_reference(monkeypatch):
    for day, printed, week, expected in (
        ("2026-11-25", b"November 25, 2026", b"November 21", "November 21, 2026"),
        ("2026-01-02", b"January 2, 2026", b"December 27", "December 27, 2025"),
    ):
        body = DOL_JULY_30_LISTING.replace(b"20260730", day.replace("-", "").encode())
        body = body.replace(b"July 30, 2026", printed).replace(b"July 25", week)
        _, payload = _claims_identity_tick(monkeypatch, body, day=day)
        row = payload["publications"][0]
        assert row["data_ready"] is True
        assert row["actual"]["reference_period"] == expected
        assert all(metric["period"] == expected for metric in row["actual"]["metrics"])


def test_claims_identity_withdraws_retained_bad_value_and_existing_retry_recovers(monkeypatch):
    source_url = "https://www.dol.gov/index.php/newsroom/releases/eta"
    bad = {**_claims_identity_event(), "source_id": "dol_claims", "status": "published",
           "data_ready": True, "source_url": source_url, "source_sha256": "a" * 64,
           "content_sha256": "a" * 64, "verified_at": "2026-07-30T12:30:41+00:00",
           "actual": {"initial_claims": 194000, "reference_period": "July 18, 2026", "source_url": source_url}}
    state = {"coverage_started_at_by_type": {"CLAIMS": "2026-07-30T12:00:00+00:00"},
             "sources": {}, "publications": {"claims:2026-07-30": bad}}
    old_listing = DOL_JULY_30_LISTING.replace(b"20260730", b"20260723")
    state2, payload = _claims_identity_tick(monkeypatch, old_listing, state=state, hour=23, minute=15)
    row = payload["publications"][0]
    assert row["status"] == "published_unparsed" and row["data_ready"] is False
    assert "actual" not in row and "verified_at" not in row
    assert row["source_url"] == source_url and row["source_sha256"] == "a" * 64
    assert "withdrawn" in row["note"]
    assert bad["data_ready"] is True  # never mutate the caller's prior observation
    _, recovered = _claims_identity_tick(monkeypatch, DOL_JULY_30_LISTING, state=state2, hour=23, minute=30)
    row = recovered["publications"][0]
    assert row["data_ready"] is True and row["actual"]["initial_claims"] == 219_000
    assert wrp._claims_publication_is_bound(row)


def test_claims_identity_keeps_verified_facts_when_listing_rolls_forward(monkeypatch):
    state, payload = _claims_identity_tick(monkeypatch, DOL_JULY_30_LISTING)
    before = dict(payload["publications"][0])
    future_listing = DOL_JULY_30_LISTING.replace(b"20260730", b"20260806").replace(b"July 30, 2026", b"August 6, 2026")
    _, payload2 = _claims_identity_tick(monkeypatch, future_listing, state=state, minute=15)
    assert payload2["publications"][0] == before


def _bls_cpi_feed(*, event_date: str, content: str = CPI_ENTRY_TEXT) -> bytes:
    return f"""
    <feed xmlns="http://www.w3.org/2005/Atom">
      <id>bls.gov:feed:cpi</id>
      <title>Consumer Price Index</title>
      <entry>
        <title>Consumer Price Index — June 2026</title>
        <id>https://www.bls.gov/news.release/archives/cpi_{event_date.replace('-', '')}.htm</id>
        <published>{event_date}T07:50:00-04:00</published>
        <link href="https://www.bls.gov/news.release/archives/cpi_{event_date.replace('-', '')}.htm"/>
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
        assert prior["fingerprint"]
        return _http_result(_bls_cpi_feed(event_date="2026-07-14"))

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


def test_release_watcher_cold_start_recovers_from_official_date():
    after = datetime(2026, 7, 14, 12, 35, tzinfo=timezone.utc)

    def fetcher(spec, prior, timeout):
        return _http_result(_bls_cpi_feed(event_date="2026-07-14"))

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
        return _http_result(_bls_cpi_feed(event_date="2026-07-14"))

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
    assert calls == ["bls_cpi"]


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
        return _http_result(_bls_cpi_feed(event_date="2026-07-14"))

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


def test_regime_self_heal_runs_after_the_us_close():
    """VPS cutover must retain a pass after the just-settled US session."""
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "regime-self-heal.yml").read_text()

    # Keep the morning recovery pass for a missed prior close. 21:15 UTC is
    # 16:15 EST / 17:15 EDT, safely after the regular US close year-round.
    assert '- cron: "5 14 * * 1-5"' in workflow
    assert '- cron: "15 21 * * 1-5"' in workflow


def test_regime_self_heal_dispatches_macro_render_only_after_repair_push():
    """A fresh canonical pointer must reach the existing static render carrier."""
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "regime-self-heal.yml").read_text()

    assert "actions: write" in workflow
    assert "id: commit" in workflow
    assert 'echo "changed=false" >> "$GITHUB_OUTPUT"' in workflow
    assert 'echo "changed=true" >> "$GITHUB_OUTPUT"' in workflow
    assert "if: ${{ steps.commit.outputs.changed == 'true' }}" in workflow
    assert "gh workflow run render.yml" in workflow
    assert '--ref main' in workflow
    assert '-f scope=macro' in workflow
    assert '-f runner=macstudio' in workflow


@pytest.mark.parametrize(
    ("checkout_kind", "repair_changed"),
    [("main", True), ("main", False), ("feature", True), ("detached", True)],
    ids=["main-repair", "main-noop", "feature-refused", "detached-refused"],
)
def test_regime_self_heal_binds_repair_push_to_main(
    tmp_path, checkout_kind, repair_changed
):
    """The actual commit step must not publish to a configured decoy ref."""
    import os
    import subprocess

    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github" / "workflows" / "regime-self-heal.yml").read_text()
    )
    job = workflow["jobs"]["reconcile"]
    assert job["if"] == (
        "${{ github.ref == 'refs/heads/main' && "
        "(github.event_name == 'workflow_dispatch' || vars.VPS_LIVE_PRIMARY == 'true') }}"
    )
    checkout = next(
        step for step in job["steps"]
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout["with"]["ref"] == "main"
    commit = next(step for step in job["steps"] if step.get("id") == "commit")
    dispatch = next(
        step for step in job["steps"]
        if step.get("name") == "dispatch visible Macro render"
    )
    assert dispatch["if"] == "${{ steps.commit.outputs.changed == 'true' }}"

    # Only local temporary repositories are used. Inherited Git config must
    # not redirect these operations or supply a worktree/index from CI.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    })

    def git(*args, cwd=tmp_path):
        return subprocess.run(
            ["git", *args], cwd=cwd, env=env, check=True,
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()

    remote = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    work = tmp_path / "work"
    git("init", "--bare", "--initial-branch=main", str(remote))
    git("init", "--initial-branch=main", str(seed))
    git("config", "user.name", "Fixture", cwd=seed)
    git("config", "user.email", "fixture@example.invalid", cwd=seed)
    paths = (
        "data/regime/latest.json",
        "data/market_state/latest.json",
        "data/reflexes/example.json",
    )
    baseline = '{"marker":"baseline"}\n'
    repaired = '{"marker":"repaired"}\n'
    for relative in paths:
        target = seed / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(baseline, encoding="utf-8")
    # Execute the actual shared main-push guard inside the local checkout.
    policy = seed / "scripts" / "ci" / "push_retry.sh"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_bytes((root / "scripts" / "ci" / "push_retry.sh").read_bytes())
    git("add", ".", cwd=seed)
    git("commit", "-m", "fixture baseline", cwd=seed)
    git("remote", "add", "origin", str(remote), cwd=seed)
    git("push", "origin", "HEAD:refs/heads/main", "HEAD:refs/heads/decoy", cwd=seed)
    git("clone", str(remote), str(work))
    git("config", "user.name", "Fixture", cwd=work)
    git("config", "user.email", "fixture@example.invalid", cwd=work)
    # A bare git push would update decoy and leave the rendered main stale.
    git("config", "remote.origin.push", "HEAD:refs/heads/decoy", cwd=work)
    if checkout_kind == "feature":
        git("checkout", "-b", "feature", cwd=work)
    elif checkout_kind == "detached":
        git("checkout", "--detach", cwd=work)
    if repair_changed:
        for relative in paths:
            (work / relative).write_text(repaired, encoding="utf-8")

    def remote_heads():
        listing = git(
            "--git-dir", str(remote), "for-each-ref",
            "--format=%(refname) %(objectname)", "refs/heads",
        )
        return dict(line.split(" ", 1) for line in listing.splitlines())

    before_refs = remote_heads()
    before_head = git("rev-parse", "HEAD", cwd=work)
    before_index = git("ls-files", "--stage", cwd=work)
    before_status = git("status", "--porcelain=v1", cwd=work)
    output = tmp_path / "github-output"
    env["GITHUB_OUTPUT"] = str(output)
    env["GITHUB_WORKSPACE"] = str(work)
    result = subprocess.run(
        ["bash", "-c", commit["run"]], cwd=work, env=env,
        capture_output=True, text=True, timeout=30,
    )
    output_lines = output.read_text().splitlines()
    assert output_lines[0] == "changed=false"
    # GitHub uses the last value when the same output name is written twice.
    outputs = dict(line.split("=", 1) for line in output_lines)
    after_refs = remote_heads()

    if checkout_kind != "main":
        assert result.returncode != 0
        assert "canonical regime repair requires local main branch" in result.stdout
        assert outputs["changed"] == "false"
        assert after_refs == before_refs
        assert git("rev-parse", "HEAD", cwd=work) == before_head
        assert git("ls-files", "--stage", cwd=work) == before_index
        assert git("status", "--porcelain=v1", cwd=work) == before_status
        assert git("config", "user.name", cwd=work) == "Fixture"
        for relative in paths:
            assert (work / relative).read_text() == repaired
    elif repair_changed:
        assert result.returncode == 0, result.stdout + result.stderr
        assert outputs["changed"] == "true"
        assert after_refs.keys() == before_refs.keys()
        assert after_refs["refs/heads/main"] != before_refs["refs/heads/main"]
        assert after_refs["refs/heads/decoy"] == before_refs["refs/heads/decoy"]
        assert git("rev-parse", "HEAD", cwd=work) == after_refs["refs/heads/main"]
        for relative in paths:
            assert git(
                "--git-dir", str(remote), "show", f"refs/heads/main:{relative}"
            ) == repaired.strip()
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert outputs["changed"] == "false"
        assert after_refs == before_refs
        assert git("rev-parse", "HEAD", cwd=work) == before_head


def test_live_setup_retires_legacy_only_after_smoke_and_timer_enable():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app" / "deploy" / "live-setup.sh").read_text()
    smoke = text.index("systemctl start macro-live-fast.service")
    enable = text.index("systemctl enable --now")
    retire = text.index('grep -v "macro-live')
    assert smoke < enable < retire
    assert "first install failed; restoring legacy-only ownership" in text
    assert 'systemd-analyze verify "${unit_sources[@]}"' in text


def test_live_rollback_is_non_destructive_and_restores_legacy_writer():
    root = Path(__file__).resolve().parents[1]
    text = (root / "app" / "deploy" / "live-rollback.sh").read_text()
    assert "systemctl disable --now" in text
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
    enable_block = live_setup.split("systemctl enable --now")[1].split("\n\n")[0]
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


# ─────────────────────────────────────────────────────────────────────────────
# Coherent domain generation publication
#
# The per-file publisher (atomic_publish) makes ONE artifact visible at a
# time. A domain generation is several artifacts that must agree with one
# another, selected by exactly one pointer, so these tests pin the properties
# that make the bundle coherent: one selected generation, content-bound
# hashes, capture-once semantics, a retained previous selection on failure,
# idempotence, a fencing expectation, path safety, private modes and no
# default public activation.
# ─────────────────────────────────────────────────────────────────────────────


def _gen_validator(candidate: Path) -> str | None:
    """A validator in the module's own convention: an error string, or None."""
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"unreadable JSON: {exc}"
    if not isinstance(payload, dict) or not payload:
        return "payload is empty"
    return None


def _gen_request(
    tmp_path: Path,
    *,
    generation_id: str = "g1",
    domain: str = "sector",
    lane: str = "fast",
    artifacts: tuple[tuple[str, dict], ...] = (
        ("free.json", {"a": 1}),
        ("paid.json", {"b": 2}),
    ),
    source_revision: str = "rev-1",
    computed_at: str | None = "2026-11-05T00:00:00+00:00",
    input_identity: dict | None = None,
    validator=_gen_validator,
    source_dir: str = "src",
) -> "vlo.GenerationRequest":
    members = []
    for name, payload in artifacts:
        source = tmp_path / source_dir / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(json.dumps(payload), encoding="utf-8")
        members.append(
            vlo.GenerationArtifact(
                name=name, source=source, validator=validator
            )
        )
    return vlo.GenerationRequest(
        generation_id=generation_id,
        domain=domain,
        lane=lane,
        source_revision=source_revision,
        artifacts=tuple(members),
        input_identity=input_identity or {"sector_cycle": "2026-11-05"},
        computed_at=computed_at,
    )


def _gen_orchestrator(tmp_path: Path, *, now: datetime | None = None) -> "vlo.Orchestrator":
    live_dir = tmp_path / "public" / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    return vlo.Orchestrator(
        live_dir=live_dir,
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        now=now,
    )


def _gen_selection(tmp_path: Path, domain: str = "sector") -> dict:
    path = tmp_path / "state" / "generations" / domain / "current.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_generation_publishes_one_coherent_selected_generation(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert result.status == "published", result.detail

    root = tmp_path / "state" / "generations" / "sector"
    selection = _gen_selection(tmp_path)
    assert selection["generation_id"] == "g1"
    assert selection["domain"] == "sector"

    # Exactly one generation exists, and the pointer names it.
    generations = sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and entry.name != ".staging"
    )
    assert generations == ["g1"], generations

    manifest = json.loads((root / "g1" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == vlo.GENERATION_SCHEMA
    assert manifest["content_id"] == selection["content_id"]
    assert [row["name"] for row in manifest["artifacts"]] == ["free.json", "paid.json"]
    for row in manifest["artifacts"]:
        body = (root / "g1" / row["name"]).read_bytes()
        assert hashlib.sha256(body).hexdigest() == row["sha256"]
        assert len(body) == row["bytes"]

    # A consumer is handed a store-relative path, never an absolute one.
    assert not Path(selection["generation_dir"]).is_absolute()
    assert selection["generation_dir"] == "sector/g1"


def test_generation_rejects_missing_corrupt_and_mismatched_artifacts(tmp_path):
    orch = _gen_orchestrator(tmp_path)

    # Missing source.
    missing = _gen_request(tmp_path)
    os_missing = missing.artifacts[0].source
    os_missing.unlink()
    result = orch.publish_generation(missing, expected_current_content_id=None)
    assert result.status == "rejected", result.detail
    assert "does not exist" in (result.detail or "")
    assert not (tmp_path / "state" / "generations" / "sector" / "current.json").exists()

    # Corrupt artifact: the validator refuses it, so nothing is selected.
    corrupt = _gen_request(
        tmp_path, generation_id="g2", source_dir="src2",
        artifacts=(("free.json", {"a": 1}),),
        validator=lambda candidate: "payload failed the sector gate",
    )
    result = orch.publish_generation(corrupt, expected_current_content_id=None)
    assert result.status == "rejected", result.detail
    assert "failed validation" in (result.detail or "")
    assert not (tmp_path / "state" / "generations" / "sector" / "current.json").exists()

    # A good generation, then the SAME generation id with different bytes.
    good = _gen_request(tmp_path, generation_id="g3", source_dir="src3")
    first = orch.publish_generation(good, expected_current_content_id=None)
    assert first.status == "published", first.detail
    changed = _gen_request(
        tmp_path, generation_id="g3", source_dir="src4",
        artifacts=(("free.json", {"a": 999}), ("paid.json", {"b": 2})),
    )
    result = orch.publish_generation(changed, expected_current_content_id=first.content_id)
    assert result.status == "rejected", result.detail
    assert "immutable" in (result.detail or "")
    # The previous selection still stands.
    assert _gen_selection(tmp_path)["content_id"] == first.content_id


def test_generation_captures_source_bytes_once_and_publishes_the_validated_bytes(tmp_path):
    """A producer that rewrites its source mid-capture cannot change the bundle."""
    source = tmp_path / "src" / "free.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({"a": 1}), encoding="utf-8")
    validated: list[bytes] = []

    def rewriting_validator(candidate: Path) -> str | None:
        validated.append(candidate.read_bytes())
        source.write_text(json.dumps({"a": 999}), encoding="utf-8")
        return None

    request = vlo.GenerationRequest(
        generation_id="g1",
        domain="sector",
        lane="fast",
        source_revision="rev-1",
        artifacts=(
            vlo.GenerationArtifact(
                name="free.json", source=source, validator=rewriting_validator
            ),
        ),
        input_identity={"sector_cycle": "2026-11-05"},
    )
    orch = _gen_orchestrator(tmp_path)
    result = orch.publish_generation(request, expected_current_content_id=None)
    assert result.status == "published", result.detail

    published = (
        tmp_path / "state" / "generations" / "sector" / "g1" / "free.json"
    ).read_bytes()
    assert published == validated[0]
    assert json.loads(published) == {"a": 1}
    # The source was rewritten after the capture; the bundle was not.
    assert json.loads(source.read_text(encoding="utf-8")) == {"a": 999}


def test_interrupted_promotion_keeps_the_previous_selection(tmp_path, monkeypatch):
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    assert first.status == "published", first.detail
    selection_before = (tmp_path / "state" / "generations" / "sector" / "current.json").read_bytes()

    real_atomic_write_json = vlo.atomic_write_json

    def failing_selection(path, payload, **kwargs):
        if path.name == vlo._GENERATION_SELECTION_NAME:
            raise OSError("simulated promotion failure")
        return real_atomic_write_json(path, payload, **kwargs)

    monkeypatch.setattr(vlo, "atomic_write_json", failing_selection)
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "rejected", second.detail
    assert "could not publish the generation selection" in (second.detail or "")

    # The previous selection is untouched and still published.
    selection_after = (tmp_path / "state" / "generations" / "sector" / "current.json").read_bytes()
    assert selection_after == selection_before
    assert _gen_selection(tmp_path)["generation_id"] == "g1"


def test_generation_capture_failure_keeps_the_previous_selection(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    assert first.status == "published", first.detail

    def exploding_validator(candidate: Path) -> str | None:
        raise RuntimeError("validator exploded")

    broken = _gen_request(
        tmp_path, generation_id="g2", source_dir="src2",
        artifacts=(("free.json", {"a": 1}),),
        validator=exploding_validator,
    )
    result = orch.publish_generation(broken, expected_current_content_id=first.content_id)
    assert result.status == "rejected", result.detail
    assert "validator raised" in (result.detail or "")
    assert _gen_selection(tmp_path)["generation_id"] == "g1"
    # No half-built generation directory is left behind.
    root = tmp_path / "state" / "generations" / "sector"
    assert sorted(
        entry.name for entry in root.iterdir() if entry.is_dir()
    ) == [".staging", "g1"]


def test_generation_publish_is_idempotent_for_the_same_content(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    request = _gen_request(tmp_path)
    first = orch.publish_generation(request, expected_current_content_id=None)
    assert first.status == "published", first.detail

    selection_path = tmp_path / "state" / "generations" / "sector" / "current.json"
    manifest_path = (
        tmp_path / "state" / "generations" / "sector" / "g1" / "manifest.json"
    )
    selection_before = selection_path.read_bytes()
    manifest_before = manifest_path.read_bytes()

    second = orch.publish_generation(request, expected_current_content_id=first.content_id)
    assert second.status == "unchanged", second.detail
    assert second.content_id == first.content_id
    # Nothing was rewritten: neither the selection nor the immutable manifest.
    assert selection_path.read_bytes() == selection_before
    assert manifest_path.read_bytes() == manifest_before


def test_generation_fences_a_stale_expected_selection(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    assert first.status == "published", first.detail

    # The caller believed there was no selection; one is published now.
    stale = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=None,
    )
    assert stale.status == "rejected", stale.detail
    assert "does not match the published selection" in (stale.detail or "")

    # A wrong expectation is refused too.
    wrong = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id="sha256:not-the-current-one",
    )
    assert wrong.status == "rejected", wrong.detail

    # The exact expectation the caller observed is accepted.
    fresh = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert fresh.status == "published", fresh.detail
    assert _gen_selection(tmp_path)["generation_id"] == "g2"


def test_generation_rejects_unsafe_artifact_names(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    # The source exists and is valid, so the ONLY reason these attempts can be
    # refused is the artifact NAME. A missing source would let a name check
    # regress unnoticed.
    source = tmp_path / "src" / "x.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({"a": 1}), encoding="utf-8")
    for name, fragment in (
        ("../escape.json", "clean relative path"),
        (str(tmp_path / "absolute-escape.json"), "absolute"),
        ("manifest.json", "reserved generation file"),
        ("nested/../escape.json", "clean relative path"),
        ("a/../../escape.json", "clean relative path"),
        ("", "empty"),
        ("current.json", "reserved generation file"),
    ):
        # The member is built by hand: an unsafe name must never be used as a
        # source path, even inside the test.
        member = vlo.GenerationArtifact(
            name=name,
            source=source,
            validator=_gen_validator,
        )
        request = vlo.GenerationRequest(
            generation_id="g1",
            domain="sector",
            lane="fast",
            source_revision="rev-1",
            artifacts=(member,),
            input_identity={"sector_cycle": "2026-11-05"},
        )
        result = orch.publish_generation(request, expected_current_content_id=None)
        assert result.status == "rejected", (name, result.detail)
        assert fragment in (result.detail or ""), (name, result.detail)
    assert not (tmp_path / "state" / "generations" / "sector" / "current.json").exists()

    # Duplicate names.
    duplicate = vlo.GenerationRequest(
        generation_id="g1",
        domain="sector",
        lane="fast",
        source_revision="rev-1",
        artifacts=(
            vlo.GenerationArtifact(
                name="free.json", source=tmp_path / "src" / "free.json",
                validator=_gen_validator,
            ),
            vlo.GenerationArtifact(
                name="free.json", source=tmp_path / "src" / "paid.json",
                validator=_gen_validator,
            ),
        ),
        input_identity={"sector_cycle": "2026-11-05"},
    )
    result = orch.publish_generation(duplicate, expected_current_content_id=None)
    assert result.status == "rejected", result.detail
    assert "duplicate artifact name" in (result.detail or "")

    # A name that is a sibling directory of another name.
    sibling = vlo.GenerationRequest(
        generation_id="g1",
        domain="sector",
        lane="fast",
        source_revision="rev-1",
        artifacts=(
            vlo.GenerationArtifact(
                name="a", source=tmp_path / "src" / "free.json",
                validator=_gen_validator,
            ),
            vlo.GenerationArtifact(
                name="a/b.json", source=tmp_path / "src" / "paid.json",
                validator=_gen_validator,
            ),
        ),
        input_identity={"sector_cycle": "2026-11-05"},
    )
    result = orch.publish_generation(sibling, expected_current_content_id=None)
    assert result.status == "rejected", result.detail
    assert "sibling directory" in (result.detail or "")


def test_generation_refuses_a_symlinked_source(tmp_path):
    real = tmp_path / "real.json"
    real.write_text(json.dumps({"a": 1}), encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(real)
    request = vlo.GenerationRequest(
        generation_id="g1",
        domain="sector",
        lane="fast",
        source_revision="rev-1",
        artifacts=(
            vlo.GenerationArtifact(
                name="free.json", source=link, validator=_gen_validator
            ),
        ),
        input_identity={"sector_cycle": "2026-11-05"},
    )
    orch = _gen_orchestrator(tmp_path)
    result = orch.publish_generation(request, expected_current_content_id=None)
    assert result.status == "rejected", result.detail
    assert "symlink" in (result.detail or "")
    assert not (tmp_path / "state" / "generations" / "sector" / "current.json").exists()


def test_generation_artifacts_and_store_are_private(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert result.status == "published", result.detail

    root = tmp_path / "state" / "generations"
    domain_dir = root / "sector"
    generation_dir = domain_dir / "g1"
    assert stat.S_IMODE((domain_dir / "current.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((generation_dir / "manifest.json").stat().st_mode) == 0o600
    for name in ("free.json", "paid.json"):
        assert stat.S_IMODE((generation_dir / name).stat().st_mode) == 0o600
    assert stat.S_IMODE(domain_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(generation_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(root.stat().st_mode) == 0o700


def test_generation_store_never_activates_public_serving(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert result.status == "published", result.detail

    # Nothing was written into the served tree.
    served = [
        path
        for path in (tmp_path / "public").rglob("*")
        if path.is_file()
    ]
    assert served == [], served

    # The store lives under the private state root.
    assert (tmp_path / "state" / "generations" / "sector" / "current.json").is_file()

    # A store inside the served tree is refused outright.
    public = tmp_path / "public"
    bad = vlo.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        generations_root=public / "live" / "generations",
        state_dir=tmp_path / "state",
        expected_current_content_id=None,
        public_root=public,
    )
    assert bad.status == "rejected", bad.detail
    assert "served tree" in (bad.detail or "")


def test_generation_refuses_a_missing_validator(tmp_path):
    """A bundle does not establish upstream freshness, so a validator is required."""
    request = vlo.GenerationRequest(
        generation_id="g1",
        domain="sector",
        lane="fast",
        source_revision="rev-1",
        artifacts=(
            vlo.GenerationArtifact(
                name="free.json", source=tmp_path / "src" / "free.json", validator=None
            ),
        ),
        input_identity={"sector_cycle": "2026-11-05"},
    )
    orch = _gen_orchestrator(tmp_path)
    result = orch.publish_generation(request, expected_current_content_id=None)
    assert result.status == "rejected", result.detail
    assert "no validator" in (result.detail or "")
    assert not (tmp_path / "state" / "generations" / "sector" / "current.json").exists()


def test_generation_keeps_source_and_publication_clocks_distinct(tmp_path):
    published = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    orch = _gen_orchestrator(tmp_path, now=published)
    request = _gen_request(
        tmp_path, source_revision="rev-9", computed_at="2026-11-05T00:00:00+00:00"
    )
    result = orch.publish_generation(request, expected_current_content_id=None)
    assert result.status == "published", result.detail

    manifest = json.loads(
        (
            tmp_path / "state" / "generations" / "sector" / "g1" / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["source_revision"] == "rev-9"
    assert manifest["computed_at"] == "2026-11-05T00:00:00+00:00"
    assert manifest["published_at"] == published.isoformat()
    # The publication clock never stands in for the source clock.
    assert manifest["published_at"] != manifest["computed_at"]
    assert manifest["input_identity"] == {"sector_cycle": "2026-11-05"}

    # A naive clock is read as UTC by the publisher, and the publisher never
    # rewrites the caller's declared source clocks.
    naive_result = vlo.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2", domain="sector2"),
        generations_root=tmp_path / "state" / "generations",
        state_dir=tmp_path / "state",
        expected_current_content_id=None,
        now=datetime(2026, 11, 6, 12, 0),
    )
    assert naive_result.status == "published", naive_result.detail
    naive_manifest = json.loads(
        (
            tmp_path / "state" / "generations" / "sector2" / "g2" / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert naive_manifest["published_at"] == "2026-11-06T12:00:00+00:00"
    assert naive_manifest["computed_at"] == "2026-11-05T00:00:00+00:00"
    assert naive_manifest["source_revision"] == "rev-1"


def test_generation_rollback_selects_a_retained_generation(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "published", second.detail

    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert rollback.status == "published", rollback.detail
    selection = _gen_selection(tmp_path)
    assert selection["generation_id"] == "g1"
    assert selection["content_id"] == first.content_id
    # The rolled-back generation is still intact and content-bound.
    manifest = json.loads(
        (
            tmp_path / "state" / "generations" / "sector" / "g1" / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    for row in manifest["artifacts"]:
        body = (tmp_path / "state" / "generations" / "sector" / "g1" / row["name"]).read_bytes()
        assert hashlib.sha256(body).hexdigest() == row["sha256"]

    # A stale expectation cannot roll the selection back a second time.
    again = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert again.status == "rejected", again.detail


def test_generation_rollback_refuses_a_tampered_retained_generation(tmp_path):
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "published", second.detail

    tampered = (
        tmp_path / "state" / "generations" / "sector" / "g1" / "free.json"
    )
    tampered.write_text(json.dumps({"a": "tampered"}), encoding="utf-8")
    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert rollback.status == "rejected", rollback.detail
    assert "does not match its recorded hash" in (rollback.detail or "")
    # The current selection is untouched by the refused rollback.
    assert _gen_selection(tmp_path)["generation_id"] == "g2"


# ─────────────────────────────────────────────────────────────────────────────
# Regressions for the defects the parent source review found in the coherent
# generation primitive. Each one names the single behaviour it protects.
# ─────────────────────────────────────────────────────────────────────────────


def _gen_store(tmp_path: Path, domain: str = "sector") -> Path:
    return tmp_path / "state" / "generations" / domain


def _gen_manifest_path(
    tmp_path: Path, generation_id: str, domain: str = "sector"
) -> Path:
    return _gen_store(tmp_path, domain) / generation_id / "manifest.json"


def test_generation_rollback_refuses_an_unsafe_domain_before_any_effect(tmp_path):
    """An unsafe domain never reaches the lock, the store or the pointer."""
    orch = _gen_orchestrator(tmp_path)
    for domain in ("../escape", "..", "/absolute", "a/b", "with space"):
        result = orch.select_generation(
            domain=domain,
            expected_current_content_id=None,
            target_content_id="a" * 64,
        )
        assert result.status == "rejected", (domain, result.detail)
    # No effect at all: the store was never created and nothing escaped it.
    assert not (tmp_path / "state" / "generations").exists()
    assert not (tmp_path / "escape").exists()

    # A target that is not a sha256 digest is refused before it can name a
    # generation.
    bad_target = orch.select_generation(
        domain="sector",
        expected_current_content_id=None,
        target_content_id="not-a-digest",
    )
    assert bad_target.status == "rejected", bad_target.detail
    assert "sha256" in (bad_target.detail or "")


def test_generation_refuses_to_overwrite_a_corrupt_selection(tmp_path):
    """A corrupt pointer is not an absent one: it is refused, not replaced."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    assert first.status == "published", first.detail
    selection_path = _gen_store(tmp_path) / "current.json"

    for corrupt in ("{not json", "[]", '{"schema": "some-other-schema"}'):
        selection_path.write_text(corrupt, encoding="utf-8")
        result = orch.publish_generation(
            _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
            expected_current_content_id=None,
        )
        assert result.status == "rejected", (corrupt, result.detail)
        # The damaged pointer is preserved, not silently overwritten.
        assert selection_path.read_text(encoding="utf-8") == corrupt

    # The rollback path refuses a corrupt pointer too.
    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=None,
        target_content_id="a" * 64,
    )
    assert rollback.status == "rejected", rollback.detail
    assert selection_path.read_text(encoding="utf-8") == corrupt


def test_generation_rollback_refuses_an_empty_or_forged_manifest(tmp_path):
    """A retained generation is only usable when its manifest backs itself."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "published", second.detail

    manifest_path = _gen_manifest_path(tmp_path, "g1")
    original = manifest_path.read_text(encoding="utf-8")

    # An empty manifest file is not a manifest.
    manifest_path.write_text("", encoding="utf-8")
    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert rollback.status == "rejected", rollback.detail

    # A manifest that declares no artifacts is not a generation.
    manifest = json.loads(original)
    manifest["artifacts"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert rollback.status == "rejected", rollback.detail
    assert "no artifacts" in (rollback.detail or "")

    # A manifest that claims a content id it cannot back up is refused: the
    # content id is recomputed from the manifest's own contents.
    forged = "f" * 64
    manifest = json.loads(original)
    manifest["content_id"] = forged
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=forged,
    )
    assert rollback.status == "rejected", rollback.detail
    assert "content id does not match" in (rollback.detail or "")
    assert _gen_selection(tmp_path)["generation_id"] == "g2"


def test_generation_refuses_to_reuse_tampered_retained_bytes(tmp_path):
    """Corruption never produces a successful reuse or an 'unchanged'."""
    orch = _gen_orchestrator(tmp_path)
    request = _gen_request(tmp_path, generation_id="g1", source_dir="src1")
    first = orch.publish_generation(request, expected_current_content_id=None)
    assert first.status == "published", first.detail

    # Tamper with the retained generation's bytes.
    (_gen_store(tmp_path) / "g1" / "free.json").write_text(
        json.dumps({"a": "tampered"}), encoding="utf-8"
    )

    # Publishing the same content again must NOT report it as unchanged.
    again = orch.publish_generation(
        request, expected_current_content_id=first.content_id
    )
    assert again.status == "rejected", again.detail
    assert "not reusable" in (again.detail or "")

    # Rolling back to the already-selected content must NOT report it as
    # unchanged either.
    unchanged = orch.select_generation(
        domain="sector",
        expected_current_content_id=first.content_id,
        target_content_id=first.content_id,
    )
    assert unchanged.status == "rejected", unchanged.detail


def test_generation_refuses_a_validator_that_changes_the_staged_bundle(tmp_path):
    """A validator is read-only by contract; the staged set is verified."""
    orch = _gen_orchestrator(tmp_path)

    # A validator that rewrites its own target.
    def rewriting_own_target(candidate: Path) -> str | None:
        candidate.write_text(json.dumps({"a": 999}), encoding="utf-8")
        return None

    result = orch.publish_generation(
        _gen_request(
            tmp_path,
            generation_id="g1",
            source_dir="src1",
            artifacts=(("free.json", {"a": 1}),),
            validator=rewriting_own_target,
        ),
        expected_current_content_id=None,
    )
    assert result.status == "rejected", result.detail
    assert "changed after validation" in (result.detail or "")
    assert not (_gen_store(tmp_path) / "current.json").exists()

    # A validator that rewrites an EARLIER member of the same bundle.
    def rewriting_earlier_member(candidate: Path) -> str | None:
        if candidate.name == "paid.json":
            (candidate.parent / "free.json").write_text(
                json.dumps({"a": 999}), encoding="utf-8"
            )
        return None

    result = orch.publish_generation(
        _gen_request(
            tmp_path,
            generation_id="g2",
            source_dir="src2",
            validator=rewriting_earlier_member,
        ),
        expected_current_content_id=None,
    )
    assert result.status == "rejected", result.detail
    assert "changed after validation" in (result.detail or "")

    # A validator that adds a member to the bundle.
    def adding_member(candidate: Path) -> str | None:
        (candidate.parent / "extra.json").write_text(
            json.dumps({"x": 1}), encoding="utf-8"
        )
        return None

    result = orch.publish_generation(
        _gen_request(
            tmp_path,
            generation_id="g3",
            source_dir="src3",
            validator=adding_member,
        ),
        expected_current_content_id=None,
    )
    assert result.status == "rejected", result.detail
    assert "unexpected member" in (result.detail or "")
    assert not (_gen_store(tmp_path) / "current.json").exists()


def test_generation_publishes_a_nested_member_and_refuses_an_extra_directory(tmp_path):
    """A nested member's directory belongs to the bundle; an extra one does not."""
    orch = _gen_orchestrator(tmp_path)
    nested = orch.publish_generation(
        _gen_request(
            tmp_path,
            generation_id="g1",
            source_dir="src1",
            artifacts=(("nested/free.json", {"a": 1}), ("paid.json", {"b": 2})),
        ),
        expected_current_content_id=None,
    )
    assert nested.status == "published", nested.detail
    assert (_gen_store(tmp_path) / "g1" / "nested" / "free.json").is_file()

    # A validator that leaves an empty directory behind is refused.
    def adding_directory(candidate: Path) -> str | None:
        (candidate.parent / "empty").mkdir()
        return None

    extra = orch.publish_generation(
        _gen_request(
            tmp_path,
            generation_id="g2",
            source_dir="src2",
            artifacts=(("free.json", {"a": 1}),),
            validator=adding_directory,
        ),
        expected_current_content_id=nested.content_id,
    )
    assert extra.status == "rejected", extra.detail
    assert "unexpected directory" in (extra.detail or "")
    assert _gen_selection(tmp_path)["generation_id"] == "g1"


def test_generation_refuses_a_reserved_generation_id(tmp_path):
    """A generation may not take the selection pointer's own name."""
    orch = _gen_orchestrator(tmp_path)
    for name in ("current.json", "manifest.json"):
        result = orch.publish_generation(
            _gen_request(
                tmp_path,
                generation_id=name,
                source_dir="src-" + name.replace(".", "-"),
            ),
            expected_current_content_id=None,
        )
        assert result.status == "rejected", (name, result.detail)
        assert "reserved" in (result.detail or "")
    # The selection pointer was never turned into a generation directory.
    assert not (_gen_store(tmp_path) / "current.json").exists()


def test_generation_refuses_a_symlinked_retained_generation(tmp_path):
    """A symlinked generation is never selected."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "published", second.detail

    domain_dir = _gen_store(tmp_path)
    outside = tmp_path / "outside" / "g1"
    outside.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(domain_dir / "g1", outside)
    (domain_dir / "g1").rename(tmp_path / "g1-original")
    (domain_dir / "g1").symlink_to(outside)

    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert rollback.status == "rejected", rollback.detail
    # The pointer is untouched by the refused rollback.
    assert _gen_selection(tmp_path)["generation_id"] == "g2"


def test_generation_refuses_a_symlinked_member_of_a_retained_generation(tmp_path):
    """A member of a retained generation must be an ordinary file."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "published", second.detail

    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text(json.dumps({"a": 1}), encoding="utf-8")
    member = _gen_store(tmp_path) / "g1" / "free.json"
    member.unlink()
    member.symlink_to(elsewhere)

    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert rollback.status == "rejected", rollback.detail
    assert "symlink" in (rollback.detail or "")


def test_generation_refuses_a_symlinked_domain_directory(tmp_path):
    """The private hierarchy is verified, not followed."""
    store = tmp_path / "other" / "generations"
    store.mkdir(parents=True)
    (store / "sector").symlink_to(tmp_path / "real-sector")
    result = vlo.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        generations_root=store,
        state_dir=tmp_path / "state",
        expected_current_content_id=None,
    )
    assert result.status == "rejected", result.detail
    assert "symlink" in (result.detail or "")


def test_generation_refuses_an_oversized_source(tmp_path, monkeypatch):
    """The capture is bounded: at most the limit plus one byte is read."""
    orch = _gen_orchestrator(tmp_path)
    limit = 16
    real_read = os.read
    read_bytes = 0

    def counting_read(fd, count):
        nonlocal read_bytes
        chunk = real_read(fd, count)
        read_bytes += len(chunk)
        return chunk

    monkeypatch.setattr(vlo.os, "read", counting_read)
    with monkeypatch.context() as bounded:
        bounded.setattr(vlo, "MAX_GENERATION_ARTIFACT_BYTES", limit)
        result = orch.publish_generation(
            _gen_request(
                tmp_path,
                generation_id="g1",
                source_dir="src1",
                artifacts=(("free.json", {"a": "x" * 4096}),),
            ),
            expected_current_content_id=None,
        )
    assert result.status == "rejected", result.detail
    assert "limit" in (result.detail or "")
    # The size is judged from the bytes actually read through one descriptor,
    # so the capture happened and it stayed bounded: the oversized source was
    # never loaded into memory.
    assert 0 < read_bytes <= limit + 1
    assert not (_gen_store(tmp_path) / "current.json").exists()


def test_generation_refuses_a_source_that_grows_past_the_limit(tmp_path, monkeypatch):
    """A source that grows while it is read is bounded and refused."""
    orch = _gen_orchestrator(tmp_path)
    source = tmp_path / "src" / "free.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({"a": 1}), encoding="utf-8")

    real_read = os.read
    grew = False

    def growing_read(fd, count):
        nonlocal grew
        if not grew and os.fstat(fd).st_ino == source.stat().st_ino:
            grew = True
            with open(source, "ab") as handle:
                handle.write(b" " * 64)
        return real_read(fd, count)

    monkeypatch.setattr(vlo.os, "read", growing_read)
    with monkeypatch.context() as bounded:
        bounded.setattr(vlo, "MAX_GENERATION_ARTIFACT_BYTES", 16)
        result = orch.publish_generation(
            vlo.GenerationRequest(
                generation_id="g1",
                domain="sector",
                lane="fast",
                source_revision="rev-1",
                artifacts=(
                    vlo.GenerationArtifact(
                        name="free.json", source=source, validator=_gen_validator
                    ),
                ),
                input_identity={"sector_cycle": "2026-11-05"},
            ),
            expected_current_content_id=None,
        )
    assert result.status == "rejected", result.detail
    assert "limit" in (result.detail or "")
    assert not (_gen_store(tmp_path) / "current.json").exists()


def test_generation_classifies_a_failure_after_the_pointer_moved(tmp_path, monkeypatch):
    """A failure after the pointer moved is reconciled, not called a rejection."""
    orch = _gen_orchestrator(tmp_path)
    real_atomic_write_json = vlo.atomic_write_json

    def failing_selection(path, payload, **kwargs):
        real_atomic_write_json(path, payload, **kwargs)
        if path.name == vlo._GENERATION_SELECTION_NAME:
            raise OSError("simulated failure after the pointer was replaced")
        return None

    monkeypatch.setattr(vlo, "atomic_write_json", failing_selection)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    # The pointer really did move, so the attempt is NOT a rejection.
    assert result.status == "published", result.detail
    assert _gen_selection(tmp_path)["generation_id"] == "g1"


def test_generation_reports_an_uncertain_pointer(tmp_path, monkeypatch):
    """When the pointer cannot be read back, no outcome is claimed."""
    orch = _gen_orchestrator(tmp_path)
    real_atomic_write_json = vlo.atomic_write_json

    def unreadable_selection(path, payload, **kwargs):
        real_atomic_write_json(path, payload, **kwargs)
        if path.name == vlo._GENERATION_SELECTION_NAME:
            path.unlink()
            path.mkdir()
            raise OSError("simulated failure after the pointer was replaced")
        return None

    monkeypatch.setattr(vlo, "atomic_write_json", unreadable_selection)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert result.status == "uncertain", result.detail
    assert result.status not in ("rejected", "published")


def test_generation_rollback_classifies_a_failure_after_the_move(tmp_path, monkeypatch):
    """The rollback path reconciles a pointer failure the same way."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "published", second.detail

    real_atomic_write_json = vlo.atomic_write_json

    def failing_selection(path, payload, **kwargs):
        real_atomic_write_json(path, payload, **kwargs)
        if path.name == vlo._GENERATION_SELECTION_NAME:
            raise OSError("simulated failure after the pointer was replaced")
        return None

    monkeypatch.setattr(vlo, "atomic_write_json", failing_selection)
    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert rollback.status == "published", rollback.detail
    assert _gen_selection(tmp_path)["generation_id"] == "g1"


def test_generation_fsyncs_the_directory_that_holds_the_pointer(tmp_path, monkeypatch):
    """The pointer's directory entry is durable, not just its bytes."""
    orch = _gen_orchestrator(tmp_path)
    synced: list[Path] = []
    real_fsync_dir = vlo._fsync_dir

    def recording_fsync_dir(path):
        synced.append(Path(path))
        return real_fsync_dir(path)

    monkeypatch.setattr(vlo, "_fsync_dir", recording_fsync_dir)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert result.status == "published", result.detail
    domain_dir = _gen_store(tmp_path)
    # The directory that holds the selection pointer is fsynced.
    assert domain_dir in synced
    # The generation directory's own entry is fsynced into its parent.
    assert domain_dir.parent in synced


# ─────────────────────────────────────────────────────────────────────────────
# Repairs to the coherent-generation primitive and its one read seam
# ─────────────────────────────────────────────────────────────────────────────


def _gen_pointer(tmp_path: Path, domain: str = "sector") -> Path:
    return tmp_path / "state" / "generations" / domain / "current.json"


def _gen_store_root(tmp_path: Path) -> Path:
    return tmp_path / "state" / "generations"


def test_generation_refuses_a_selection_that_names_another_generation_directory(tmp_path):
    """A pointer whose directory is not its own generation is not a selection."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    assert first.status == "published", first.detail

    pointer = _gen_pointer(tmp_path)
    selection = json.loads(pointer.read_text(encoding="utf-8"))
    selection["generation_dir"] = "sector/g2"
    pointer.write_text(json.dumps(selection, sort_keys=True), encoding="utf-8")
    tampered = pointer.read_bytes()

    again = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=first.content_id
    )
    assert again.status == "rejected", again.detail
    assert again.status != "unchanged"
    assert "not its own generation" in (again.detail or "")
    # The damaged pointer is preserved for an operator, not overwritten.
    assert pointer.read_bytes() == tampered


def test_generation_refuses_a_selection_whose_artifact_list_disagrees_with_the_manifest(tmp_path):
    """The pointer's redundant artifact list is bound to the verified manifest."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    assert first.status == "published", first.detail

    pointer = _gen_pointer(tmp_path)
    selection = json.loads(pointer.read_text(encoding="utf-8"))
    selection["artifacts"] = [
        row for row in selection["artifacts"] if row["name"] != "paid.json"
    ]
    pointer.write_text(json.dumps(selection, sort_keys=True), encoding="utf-8")
    tampered = pointer.read_bytes()

    again = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=first.content_id
    )
    assert again.status == "rejected", again.detail
    assert again.status != "unchanged"
    assert "artifact list does not match" in (again.detail or "")
    assert pointer.read_bytes() == tampered


def test_generation_refuses_a_corrupt_pointer_with_a_valid_request_generation(tmp_path):
    """A corrupt selection is refused, not healed by the next valid request."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    assert first.status == "published", first.detail

    # The generation the pointer names no longer matches its own manifest.
    (_gen_store(tmp_path) / "g1" / "free.json").write_text(
        json.dumps({"a": "tampered"}), encoding="utf-8"
    )
    pointer = _gen_pointer(tmp_path)
    pointer_before = pointer.read_bytes()

    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "rejected", second.detail
    assert second.status != "unchanged"
    # The corrupt pointer still stands: it was not overwritten with a fresh one.
    assert pointer.read_bytes() == pointer_before
    assert json.loads(pointer_before)["generation_id"] == "g1"
    # The refused request was never materialised.
    assert not (_gen_store(tmp_path) / "g2").exists()


def test_generation_refuses_a_symlinked_selection_pointer(tmp_path):
    """A symlinked pointer is refused, not followed and not replaced."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    assert first.status == "published", first.detail

    pointer = _gen_pointer(tmp_path)
    target = tmp_path / "pointer-target.json"
    target.write_text(pointer.read_text(encoding="utf-8"), encoding="utf-8")
    pointer.unlink()
    pointer.symlink_to(target)

    again = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=first.content_id
    )
    assert again.status == "rejected", again.detail
    assert "symlink" in (again.detail or "")
    assert pointer.is_symlink()
    assert os.readlink(pointer) == str(target)


def test_generation_refuses_a_dangling_selection_pointer_symlink(tmp_path):
    """A dangling pointer symlink is not an ABSENT selection."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    assert first.status == "published", first.detail

    pointer = _gen_pointer(tmp_path)
    pointer.unlink()
    pointer.symlink_to(tmp_path / "missing-target.json")

    again = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=first.content_id
    )
    assert again.status == "rejected", again.detail
    assert "symlink" in (again.detail or "")
    # It was not treated as an absent selection and healed by an overwrite.
    assert pointer.is_symlink()
    assert not pointer.exists()

    # The rollback path must not heal it either: a caller that observed no
    # selection cannot turn a dangling pointer into one.
    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=None,
        target_content_id=first.content_id,
    )
    assert rollback.status == "rejected", rollback.detail
    assert pointer.is_symlink()
    assert not pointer.exists()


def test_generation_publish_reports_a_failed_directory_fsync_before_the_pointer_moves(
    tmp_path, monkeypatch
):
    """A durability failure before the pointer replacement leaves the old state."""
    orch = _gen_orchestrator(tmp_path)
    domain_dir = _gen_store(tmp_path)
    pointer = domain_dir / "current.json"
    real_fsync_dir = vlo._fsync_dir

    def failing_fsync_dir(path):
        path = Path(path)
        if path == domain_dir and not pointer.exists():
            # The generation directory is already in place; its entry into the
            # domain directory cannot be made durable.
            if any(
                entry.is_dir() and entry.name != ".staging"
                for entry in domain_dir.iterdir()
            ):
                raise OSError(errno.EIO, "simulated directory fsync failure")
        return real_fsync_dir(path)

    monkeypatch.setattr(vlo, "_fsync_dir", failing_fsync_dir)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert result.status == "rejected", result.detail
    assert "durable" in (result.detail or "")
    # The pointer never moved, so the previous state still stands.
    assert not pointer.exists()
    # The generation directory WAS applied, and its directory entry is not
    # known to be durable: the effect and its durability are separate facts.
    assert result.durability == "unconfirmed"
    assert (_gen_store(tmp_path) / "g1").is_dir()


def test_generation_publish_reports_applied_but_unconfirmed_when_the_pointer_fsync_fails(
    tmp_path, monkeypatch
):
    """A visible rename with a failed fsync is APPLIED, and durability is unconfirmed."""
    orch = _gen_orchestrator(tmp_path)
    domain_dir = _gen_store(tmp_path)
    pointer = domain_dir / "current.json"
    real_fsync_dir = vlo._fsync_dir

    def failing_fsync_dir(path):
        path = Path(path)
        if path == domain_dir and pointer.exists():
            raise OSError(errno.EIO, "simulated directory fsync failure")
        return real_fsync_dir(path)

    monkeypatch.setattr(vlo, "_fsync_dir", failing_fsync_dir)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    # The rename is visible: the pointer really did move.
    assert result.status == "published", result.detail
    assert result.status != "unchanged"
    assert result.status != "rejected"
    # The EFFECT and the DURABILITY are separate facts.
    assert result.durability == "unconfirmed"
    assert pointer.exists()
    assert _gen_selection(tmp_path)["generation_id"] == "g1"


def test_generation_rollback_reports_applied_but_unconfirmed_when_the_pointer_fsync_fails(
    tmp_path, monkeypatch
):
    """The rollback path keeps the effect and the durability apart too."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    assert first.status == "published", first.detail
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "published", second.detail

    domain_dir = _gen_store(tmp_path)
    pointer = domain_dir / "current.json"
    real_fsync_dir = vlo._fsync_dir

    def failing_fsync_dir(path):
        path = Path(path)
        if path == domain_dir and pointer.exists():
            raise OSError(errno.EIO, "simulated directory fsync failure")
        return real_fsync_dir(path)

    monkeypatch.setattr(vlo, "_fsync_dir", failing_fsync_dir)
    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert rollback.status == "published", rollback.detail
    assert rollback.durability == "unconfirmed"
    # The rollback really landed.
    assert _gen_selection(tmp_path)["generation_id"] == "g1"


def test_generation_publish_reports_a_confirmed_durability_on_the_normal_path(tmp_path):
    """The normal path confirms the pointer's durability explicitly."""
    orch = _gen_orchestrator(tmp_path)
    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert result.status == "published", result.detail
    assert result.durability == "confirmed"


def test_generation_directory_fsync_does_not_suppress_permission_or_descriptor_failures(
    tmp_path, monkeypatch
):
    """The generation primitive's directory fsync suppresses nothing."""
    directory = tmp_path / "store"
    directory.mkdir()

    def permission_fsync(fd):
        raise OSError(errno.EPERM, "simulated permission failure")

    monkeypatch.setattr(vlo.os, "fsync", permission_fsync)
    with pytest.raises(OSError) as strict:
        vlo._fsync_dir(directory)
    assert strict.value.errno == errno.EPERM

    def descriptor_fsync(fd):
        raise OSError(errno.EBADF, "simulated descriptor failure")

    monkeypatch.setattr(vlo.os, "fsync", descriptor_fsync)
    with pytest.raises(OSError) as strict:
        vlo._fsync_dir(directory)
    assert strict.value.errno == errno.EBADF

    def unsupported_fsync(fd):
        raise OSError(errno.EINVAL, "simulated unsupported filesystem")

    monkeypatch.setattr(vlo.os, "fsync", unsupported_fsync)
    # The generation primitive CLAIMS durability: an unsupported filesystem is
    # an explicit failure, never a silently accepted loss.
    with pytest.raises(OSError):
        vlo._fsync_dir(directory)


def test_generation_refuses_a_fifo_source_without_hanging(tmp_path):
    """A FIFO is refused on its identity; it never parks the publisher."""
    fifo = tmp_path / "pipe.json"
    os.mkfifo(fifo)
    repo_root = Path(__file__).resolve().parents[1]
    program = textwrap.dedent(
        """
        import sys
        from pathlib import Path

        sys.path.insert(0, sys.argv[1])
        from scripts import vps_live_orchestrator as vlo

        source = Path(sys.argv[2])
        try:
            vlo._read_source_bytes(source, limit=1024)
        except vlo.GenerationRejected as exc:
            print("REJECTED", exc)
        else:
            print("ACCEPTED")

        scratch = Path(sys.argv[3])
        (scratch / "public" / "live").mkdir(parents=True, exist_ok=True)
        orch = vlo.Orchestrator(
            live_dir=scratch / "public" / "live",
            state_dir=scratch / "state",
            data_dir=scratch / "data",
        )
        request = vlo.GenerationRequest(
            generation_id="g1",
            domain="sector",
            lane="fast",
            source_revision="rev-1",
            artifacts=(
                vlo.GenerationArtifact(
                    name="free.json", source=source, validator=lambda candidate: None
                ),
            ),
            input_identity={"cycle": "2026-11-06"},
        )
        result = orch.publish_generation(request, expected_current_content_id=None)
        print("PUBLISH", result.status)
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", program, str(repo_root), str(fifo), str(tmp_path / "scratch")],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert "REJECTED" in completed.stdout
    assert "not a regular file" in completed.stdout
    # The whole publication path refuses the FIFO too.
    assert "PUBLISH rejected" in completed.stdout


def test_generation_publication_has_no_validator_opt_out(tmp_path):
    """The production wrapper has no escape hatch around the semantic validator."""
    assert "require_validator" not in inspect.signature(vlo.publish_generation).parameters
    assert (
        "require_validator"
        not in inspect.signature(vlo.Orchestrator.publish_generation).parameters
    )
    orch = _gen_orchestrator(tmp_path)
    with pytest.raises(TypeError):
        orch.publish_generation(
            _gen_request(tmp_path),
            expected_current_content_id=None,
            require_validator=False,
        )


def test_selected_generation_read_returns_one_verified_snapshot(tmp_path):
    """The read seam returns the manifest and the verified member bytes."""
    orch = _gen_orchestrator(tmp_path)
    published = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert published.status == "published", published.detail

    snapshot = vlo.read_selected_generation(
        generations_root=_gen_store_root(tmp_path),
        domain="sector",
        members=["free.json", "paid.json"],
    )
    assert snapshot.domain == "sector"
    assert snapshot.generation_id == "g1"
    assert snapshot.content_id == published.content_id
    assert snapshot.generation_dir == "sector/g1"
    assert snapshot.manifest["generation_id"] == "g1"
    assert sorted(snapshot.members) == ["free.json", "paid.json"]
    assert json.loads(snapshot.members["free.json"]) == {"a": 1}
    assert json.loads(snapshot.members["paid.json"]) == {"b": 2}

    # Only the requested members are returned.
    partial = vlo.read_selected_generation(
        generations_root=_gen_store_root(tmp_path),
        domain="sector",
        members=["free.json"],
    )
    assert list(partial.members) == ["free.json"]

    # The snapshot is immutable.
    with pytest.raises(TypeError):
        snapshot.members["free.json"] = b"tampered"


def test_selected_generation_read_cannot_mix_members_across_a_pointer_change(
    tmp_path, monkeypatch
):
    """A pointer that moves mid-read cannot mix one generation's members."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    assert first.status == "published", first.detail
    second = orch.publish_generation(
        _gen_request(
            tmp_path,
            generation_id="g2",
            source_dir="src2",
            artifacts=(("free.json", {"a": 3}), ("paid.json", {"b": 4})),
        ),
        expected_current_content_id=first.content_id,
    )
    assert second.status == "published", second.detail

    store = _gen_store_root(tmp_path)
    pointer = store / "sector" / "current.json"
    g1_manifest = json.loads(
        (store / "sector" / "g1" / "manifest.json").read_text(encoding="utf-8")
    )
    older_selection = {
        "schema": vlo.GENERATION_SELECTION_SCHEMA,
        "domain": "sector",
        "generation_id": "g1",
        "content_id": first.content_id,
        "generation_dir": "sector/g1",
        "published_at": g1_manifest["published_at"],
        "selected_at": g1_manifest["published_at"],
        "artifacts": g1_manifest["artifacts"],
    }

    real_read_json_state = vlo._read_json_state

    def swapping_read(path, **kwargs):
        state, payload = real_read_json_state(path, **kwargs)
        if Path(path).name == vlo._GENERATION_SELECTION_NAME and state == "ok":
            # A concurrent publisher moves the pointer after the reader's
            # capture and before its member reads.
            vlo.atomic_write_json(pointer, older_selection, mode=0o600, sort_keys=True)
        return state, payload

    monkeypatch.setattr(vlo, "_read_json_state", swapping_read)

    snapshot = vlo.read_selected_generation(
        generations_root=store, domain="sector", members=["free.json", "paid.json"]
    )
    # One captured selection, one generation, one set of members.
    assert snapshot.generation_id == "g2"
    assert snapshot.content_id == second.content_id
    assert snapshot.manifest["generation_id"] == "g2"
    assert json.loads(snapshot.members["free.json"]) == {"a": 3}
    assert json.loads(snapshot.members["paid.json"]) == {"b": 4}


def test_selected_generation_read_returns_the_bytes_it_verified(tmp_path, monkeypatch):
    """The members are the bytes the verifier hashed, not a later re-read."""
    orch = _gen_orchestrator(tmp_path)
    orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    store = _gen_store_root(tmp_path)
    real_capture = vlo._verify_retained_generation_capture

    def capture_then_tamper(
        directory, *, domain, expected_content_id=None, capture_names=None
    ):
        manifest, error, captured = real_capture(
            directory,
            domain=domain,
            expected_content_id=expected_content_id,
            capture_names=capture_names,
        )
        if captured:
            for name in captured:
                (directory / name).write_bytes(b"tampered")
        return manifest, error, captured

    monkeypatch.setattr(vlo, "_verify_retained_generation_capture", capture_then_tamper)
    snapshot = vlo.read_selected_generation(
        generations_root=store, domain="sector", members=["free.json"]
    )
    assert json.loads(snapshot.members["free.json"]) == {"a": 1}


def test_selected_generation_read_rejects_an_absent_member(tmp_path):
    """A required member that the selected generation does not hold is refused."""
    orch = _gen_orchestrator(tmp_path)
    orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    with pytest.raises(vlo.SelectedGenerationUnavailable):
        vlo.read_selected_generation(
            generations_root=_gen_store_root(tmp_path),
            domain="sector",
            members=["free.json", "missing.json"],
        )


def test_selected_generation_read_rejects_a_corrupt_member(tmp_path):
    """A member whose bytes do not match the manifest is refused."""
    orch = _gen_orchestrator(tmp_path)
    orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    member = _gen_store(tmp_path) / "g1" / "free.json"
    member.write_text(json.dumps({"a": "tampered"}), encoding="utf-8")
    with pytest.raises(vlo.SelectedGenerationUnavailable):
        vlo.read_selected_generation(
            generations_root=_gen_store_root(tmp_path),
            domain="sector",
            members=["free.json"],
        )


def test_selected_generation_read_refuses_a_symlinked_pointer(tmp_path):
    """The read seam does not follow a symlinked pointer."""
    orch = _gen_orchestrator(tmp_path)
    orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    pointer = _gen_pointer(tmp_path)
    target = tmp_path / "pointer-target.json"
    target.write_text(pointer.read_text(encoding="utf-8"), encoding="utf-8")
    pointer.unlink()
    pointer.symlink_to(target)
    with pytest.raises(vlo.SelectedGenerationUnavailable):
        vlo.read_selected_generation(
            generations_root=_gen_store_root(tmp_path),
            domain="sector",
            members=["free.json"],
        )


def test_selected_generation_read_writes_nothing(tmp_path):
    """The read seam creates no directory, no lock file and no mutation."""
    orch = _gen_orchestrator(tmp_path)
    orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    state_dir = tmp_path / "state"

    def tree_state(root: Path) -> dict:
        entries = {}
        for path in sorted(root.rglob("*")):
            info = path.lstat()
            if path.is_symlink():
                entries[str(path)] = ("symlink", os.readlink(path))
            elif path.is_dir():
                entries[str(path)] = ("dir", info.st_mtime_ns)
            else:
                entries[str(path)] = (
                    "file",
                    info.st_size,
                    info.st_mtime_ns,
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
        return entries

    before = tree_state(state_dir)
    snapshot = vlo.read_selected_generation(
        generations_root=_gen_store_root(tmp_path),
        domain="sector",
        members=["free.json"],
    )
    assert snapshot.generation_id == "g1"
    assert tree_state(state_dir) == before


def test_bundle_member_read_is_bounded_and_refuses_links_and_fifos(tmp_path):
    """A member is read within a bound, and a link or a FIFO is refused."""
    member = tmp_path / "member.json"
    member.write_bytes(b"x" * 64)

    data, error = vlo._read_bundle_member(member, limit=8)
    assert error is None
    # The read stops at the bound instead of loading the whole member.
    assert len(data) == 9

    link = tmp_path / "link.json"
    link.symlink_to(member)
    data, error = vlo._read_bundle_member(link, limit=8)
    assert data is None
    assert error == "is a symlink"

    fifo = tmp_path / "pipe.json"
    os.mkfifo(fifo)
    data, error = vlo._read_bundle_member(fifo, limit=8)
    assert data is None
    assert error == "is not a regular file"


def test_generation_reports_a_member_that_disappears_as_a_rejection_not_an_exception(
    tmp_path, monkeypatch
):
    """A member that vanishes mid-read is reported, never raised at the caller."""
    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert first.status == "published", first.detail

    def disappearing_member(member, *, limit):
        raise FileNotFoundError(member)

    monkeypatch.setattr(vlo, "_read_bundle_member", disappearing_member)
    again = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=first.content_id
    )
    assert again.status == "rejected", again.detail

    with pytest.raises(vlo.SelectedGenerationUnavailable):
        vlo.read_selected_generation(
            generations_root=_gen_store_root(tmp_path),
            domain="sector",
            members=["free.json"],
        )


def test_generation_refuses_a_symlinked_pointer_that_looks_absent(tmp_path):
    """A dangling pointer is not healed into a selection by an absent fence."""
    orch = _gen_orchestrator(tmp_path)
    orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    pointer = _gen_pointer(tmp_path)
    pointer.unlink()
    pointer.symlink_to(tmp_path / "missing-target.json")

    result = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=None,
    )
    assert result.status == "rejected", result.detail
    assert "symlink" in (result.detail or "")
    assert pointer.is_symlink()


def test_generation_refuses_a_fifo_pointer_as_unreadable_not_absent(tmp_path):
    """A FIFO pointer is classified, not waited on and not taken for absence.

    The check runs in an isolated subprocess with a strict deadline: a
    publisher that waits on the pointer would park the lane, and that has to
    be a FAILURE of this test rather than a hang of the suite.
    """
    scratch = tmp_path / "scratch"
    pointer = scratch / "state" / "generations" / "sector" / "current.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(pointer)
    repo_root = Path(__file__).resolve().parents[1]
    program = textwrap.dedent(
        """
        import sys
        from pathlib import Path

        sys.path.insert(0, sys.argv[1])
        from scripts import vps_live_orchestrator as vlo

        pointer = Path(sys.argv[2])
        scratch = Path(sys.argv[3])
        (scratch / "public" / "live").mkdir(parents=True, exist_ok=True)
        orch = vlo.Orchestrator(
            live_dir=scratch / "public" / "live",
            state_dir=scratch / "state",
            data_dir=scratch / "data",
        )
        source = scratch / "free.json"
        source.write_text("{}")
        request = vlo.GenerationRequest(
            generation_id="g1",
            domain="sector",
            lane="fast",
            source_revision="rev-1",
            artifacts=(
                vlo.GenerationArtifact(
                    name="free.json", source=source, validator=lambda candidate: None
                ),
            ),
            input_identity={"cycle": "2026-11-06"},
        )
        result = orch.publish_generation(request, expected_current_content_id=None)
        print("PUBLISH", result.status, (result.detail or ""))
        """
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            program,
            str(repo_root),
            str(pointer),
            str(scratch),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert "PUBLISH rejected" in completed.stdout
    assert "unreadable" in completed.stdout
    assert pointer.is_fifo()


def test_generation_refuses_a_json_corrupt_pointer_with_a_valid_request_generation(
    tmp_path,
):
    """A pointer that is not JSON at all is refused, not overwritten."""
    orch = _gen_orchestrator(tmp_path)
    pointer = _gen_pointer(tmp_path)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text("{not json", encoding="utf-8")
    before = pointer.read_bytes()

    result = orch.publish_generation(
        _gen_request(tmp_path), expected_current_content_id=None
    )
    assert result.status == "rejected", result.detail
    assert pointer.read_bytes() == before

    rollback = orch.select_generation(
        domain="sector",
        expected_current_content_id=None,
        target_content_id="0" * 64,
    )
    assert rollback.status == "rejected", rollback.detail
    assert pointer.read_bytes() == before


def test_selected_generation_read_refuses_a_pointer_that_names_another_generation(tmp_path):
    """The read seam applies the same pointer binding as the publisher."""
    orch = _gen_orchestrator(tmp_path)
    orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    pointer = _gen_pointer(tmp_path)
    selection = json.loads(pointer.read_text(encoding="utf-8"))
    selection["generation_dir"] = "sector/g2"
    pointer.write_text(json.dumps(selection, sort_keys=True), encoding="utf-8")

    with pytest.raises(vlo.SelectedGenerationUnavailable):
        vlo.read_selected_generation(
            generations_root=_gen_store_root(tmp_path),
            domain="sector",
            members=["free.json"],
        )


def test_selected_generation_read_refuses_a_pointer_whose_artifact_list_disagrees(tmp_path):
    """The read seam binds the pointer's artifact list to the verified manifest."""
    orch = _gen_orchestrator(tmp_path)
    orch.publish_generation(_gen_request(tmp_path), expected_current_content_id=None)
    pointer = _gen_pointer(tmp_path)
    selection = json.loads(pointer.read_text(encoding="utf-8"))
    selection["artifacts"] = [
        row for row in selection["artifacts"] if row["name"] != "paid.json"
    ]
    pointer.write_text(json.dumps(selection, sort_keys=True), encoding="utf-8")

    with pytest.raises(vlo.SelectedGenerationUnavailable):
        vlo.read_selected_generation(
            generations_root=_gen_store_root(tmp_path),
            domain="sector",
            members=["free.json"],
        )


# Parent integration regressions: truthful readback, retained-target discovery,
# and unchanged legacy atomic-write behavior.
def _gen_failed_write_case(tmp_path, operation):
    orch = _gen_orchestrator(tmp_path)
    selections = []
    prior_id = None
    for n in range(1, 4):
        result = orch.publish_generation(
            _gen_request(
                tmp_path, generation_id=f"g{n}", source_dir=f"src{n}",
                artifacts=(("free.json", {"value": n}), ("paid.json", {"value": n})),
            ),
            expected_current_content_id=prior_id,
        )
        assert result.status == "published", result.detail
        selections.append(_gen_selection(tmp_path))
        prior_id = result.content_id
    if operation == "publish":
        request = _gen_request(tmp_path, generation_id="g4", source_dir="src4")
        invoke = lambda: orch.publish_generation(
            request, expected_current_content_id=prior_id
        )
    else:
        invoke = lambda: orch.select_generation(
            domain="sector",
            expected_current_content_id=prior_id,
            target_content_id=selections[0]["content_id"],
        )
    return invoke, selections[-1], selections[1]


@pytest.mark.parametrize("operation", ["publish", "rollback"])
@pytest.mark.parametrize("field", ["generation_dir", "artifacts", "published_at"])
def test_generation_failed_write_requires_complete_verified_target(
    tmp_path, monkeypatch, operation, field
):
    invoke, _, _ = _gen_failed_write_case(tmp_path, operation)
    real_write = vlo.atomic_write_json

    def corrupt_selection(path, payload, **kwargs):
        if path.name != vlo._GENERATION_SELECTION_NAME:
            return real_write(path, payload, **kwargs)
        corrupt = json.loads(json.dumps(payload))
        if field == "generation_dir":
            corrupt[field] = "sector/does-not-exist"
        elif field == "artifacts":
            corrupt[field][0]["sha256"] = "0" * 64
        else:
            corrupt[field] = "1900-01-01T00:00:00+00:00"
        real_write(path, corrupt, **kwargs)
        raise OSError("failure after an invalid pointer became visible")

    monkeypatch.setattr(vlo, "atomic_write_json", corrupt_selection)
    result = invoke()
    assert result.status == "uncertain", result.detail
    assert result.durability == "unconfirmed"
    with pytest.raises(vlo.SelectedGenerationUnavailable):
        vlo.read_selected_generation(
            generations_root=_gen_store_root(tmp_path), domain="sector",
            members=("free.json",),
        )


@pytest.mark.parametrize("operation", ["publish", "rollback"])
def test_generation_failed_write_does_not_mistake_foreign_selection_for_prior(
    tmp_path, monkeypatch, operation
):
    invoke, prior, foreign = _gen_failed_write_case(tmp_path, operation)
    assert foreign["content_id"] != prior["content_id"]
    real_write = vlo.atomic_write_json

    def substitute_selection(path, payload, **kwargs):
        if path.name != vlo._GENERATION_SELECTION_NAME:
            return real_write(path, payload, **kwargs)
        real_write(path, foreign, **kwargs)
        raise OSError("another valid selection is visible")

    monkeypatch.setattr(vlo, "atomic_write_json", substitute_selection)
    result = invoke()
    assert result.status == "uncertain", result.detail
    assert _gen_selection(tmp_path) == foreign
    # Validity by itself does not prove either outcome of this attempted write.
    snapshot = vlo.read_selected_generation(
        generations_root=_gen_store_root(tmp_path), domain="sector",
        members=("free.json",),
    )
    assert snapshot.content_id == foreign["content_id"]


@pytest.mark.parametrize("operation", ["publish", "rollback"])
def test_generation_failed_write_can_establish_exact_verified_prior(
    tmp_path, monkeypatch, operation
):
    invoke, prior, _ = _gen_failed_write_case(tmp_path, operation)
    real_write = vlo.atomic_write_json

    def refuse_selection(path, payload, **kwargs):
        if path.name == vlo._GENERATION_SELECTION_NAME:
            raise OSError("failure before pointer replacement")
        return real_write(path, payload, **kwargs)

    monkeypatch.setattr(vlo, "atomic_write_json", refuse_selection)
    result = invoke()
    assert result.status == "rejected", result.detail
    assert _gen_selection(tmp_path) == prior
    snapshot = vlo.read_selected_generation(
        generations_root=_gen_store_root(tmp_path), domain="sector",
        members=("free.json",),
    )
    assert snapshot.content_id == prior["content_id"]


@pytest.mark.parametrize("had_prior", [False, True])
def test_generation_absent_readback_is_unchanged_only_if_absence_was_captured(
    tmp_path, monkeypatch, had_prior
):
    orch = _gen_orchestrator(tmp_path)
    prior_id = None
    if had_prior:
        prior = orch.publish_generation(
            _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
            expected_current_content_id=None,
        )
        assert prior.status == "published", prior.detail
        prior_id = prior.content_id
    request = _gen_request(tmp_path, generation_id="g2", source_dir="src2")
    real_write = vlo.atomic_write_json

    def absent_selection(path, payload, **kwargs):
        if path.name == vlo._GENERATION_SELECTION_NAME:
            path.unlink(missing_ok=True)
            raise OSError("no selection exists after failure")
        return real_write(path, payload, **kwargs)

    monkeypatch.setattr(vlo, "atomic_write_json", absent_selection)
    result = orch.publish_generation(request, expected_current_content_id=prior_id)
    assert result.status == ("uncertain" if had_prior else "rejected"), result.detail
    assert not _gen_pointer(tmp_path).exists()


def test_generation_rollback_skips_invalid_orphan_shadow_and_preserves_it(tmp_path):
    import shutil

    orch = _gen_orchestrator(tmp_path)
    first = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g1", source_dir="src1"),
        expected_current_content_id=None,
    )
    second = orch.publish_generation(
        _gen_request(tmp_path, generation_id="g2", source_dir="src2"),
        expected_current_content_id=first.content_id,
    )
    assert first.status == second.status == "published"
    orphan = _gen_store(tmp_path) / "aaa-orphan"
    shutil.copytree(_gen_store(tmp_path) / "g1", orphan)
    before = {str(p.relative_to(orphan)): p.read_bytes()
              for p in orphan.rglob("*") if p.is_file()}
    result = orch.select_generation(
        domain="sector", expected_current_content_id=second.content_id,
        target_content_id=first.content_id,
    )
    assert result.status == "published", result.detail
    assert _gen_selection(tmp_path)["generation_dir"] == "sector/g1"
    assert before == {str(p.relative_to(orphan)): p.read_bytes()
                      for p in orphan.rglob("*") if p.is_file()}


def test_legacy_atomic_write_does_not_add_directory_fsync(tmp_path, monkeypatch):
    import stat

    real_fsync = vlo.os.fsync
    calls = []

    def only_file_fsync(fd):
        kind = "directory" if stat.S_ISDIR(vlo.os.fstat(fd).st_mode) else "file"
        calls.append(kind)
        if kind == "directory":
            raise OSError(errno.EINVAL, "directory fsync unsupported")
        return real_fsync(fd)

    monkeypatch.setattr(vlo.os, "fsync", only_file_fsync)
    target = tmp_path / "legacy.json"
    vlo.atomic_write_json(target, {"legacy": True})
    assert json.loads(target.read_text()) == {"legacy": True}
    assert calls == ["file"]
    with pytest.raises(vlo.DurabilityUnconfirmed):
        vlo.atomic_write_json(target, {"strict": True}, require_durable=True)
    assert json.loads(target.read_text()) == {"strict": True}
    assert calls == ["file", "file", "directory"]


def test_publication_receipt_hashes_exact_copied_bytes(tmp_path: Path):
    source = tmp_path / "source.json"
    target = tmp_path / "public" / "quotes.json"
    body = b'{"quotes":{"SPY":{"price":600}},"meta":{"requested":1,"resolved":1}}'
    source.write_bytes(body)
    digest = vlo.atomic_publish(source, target)
    assert target.read_bytes() == body
    assert digest == hashlib.sha256(body).hexdigest()


@pytest.mark.parametrize("invocation,expected", [("a" * 32, "a" * 32), ("invalid", None)])
def test_private_lane_receipt_binds_invocation_and_original_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, invocation: str, expected: str | None
):
    monkeypatch.setenv("INVOCATION_ID", invocation)
    source = tmp_path / "stage" / "quotes.json"
    source.parent.mkdir()
    target = tmp_path / "public" / "live" / "quotes.json"
    body = json.dumps({
        "quotes": {f"S{i}": {"price": i + 1} for i in range(5)},
        "meta": {"requested": 5, "resolved": 5},
    }).encode()

    def runner(args, **kwargs):
        source.write_bytes(body)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    orch = vlo.Orchestrator(live_dir=target.parent, state_dir=tmp_path / "state",
                            data_dir=tmp_path / "data", runner=runner)
    result = orch.command("display_quotes", ["fixture"], outputs=((source, target),),
                          timeout=1, validator=lambda path: vlo.quote_snapshot_error(
                              path, min_resolved=5, min_coverage=0.10))
    assert result.status == "ok"
    assert result.publication_sha256 == {"live/quotes.json": hashlib.sha256(body).hexdigest()}
    # A later writer cannot alter the earlier producer's provenance.
    target.write_text('{"later_writer":true}')
    orch.write_status("fast", datetime.now(timezone.utc))
    private = json.loads((tmp_path / "state/status-fast.json").read_text())
    assert private["invocation_id"] == expected
    assert private["tasks"][0]["publication_sha256"] == result.publication_sha256
    assert private["tasks"][0]["publication_sha256"]["live/quotes.json"] != hashlib.sha256(target.read_bytes()).hexdigest()
    public = json.loads((target.parent / "orchestrator_status.json").read_text())
    assert "invocation_id" not in public["lanes"]["fast"]
    assert "publication_sha256" not in public["lanes"]["fast"]["tasks"][0]
