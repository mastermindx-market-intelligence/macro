"""Tests for engine/europe_news_intel.py (spec A-F02-W2-4, MO-PAID-034).

All tests are OFFLINE: urllib.request.urlopen is monkeypatched, nothing hits the
network, and nothing reads or writes the real repo data/ directory (parquet
paths — both this module's and engine.qbus's — are redirected to tmp_path)."""
from __future__ import annotations

import inspect
import re
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import pytest

from engine import europe_news_intel as eni
from engine import qbus
from engine import qkernel
from lib import config


# --------------------------------------------------------------------------- #
# shared fixtures / helpers
# --------------------------------------------------------------------------- #
_FAKE_CFG: dict = {
    "enabled": True,
    "sources": [
        {"key": "ec_presscorner", "url": "https://example.invalid/ec.rss",
         "publisher": "European Commission", "tier": 1, "jurisdiction": "EU",
         "lang": "en", "expected_cadence_hours": 24,
         "rights_basis": "CC BY 4.0 (Commission Decision 2011/833/EU)",
         "rights_state": "VERIFIED_PUBLIC_REUSE"},
        {"key": "boe_news", "url": "https://example.invalid/boe.rss",
         "publisher": "Bank of England", "tier": 1, "jurisdiction": "UK",
         "lang": "en", "expected_cadence_hours": 168,
         "rights_basis": "Open Government Licence v3.0",
         "rights_state": "VERIFIED_PUBLIC_REUSE"},
        {"key": "ecb_press", "url": "https://example.invalid/ecb.rss",
         "publisher": "European Central Bank", "tier": 1, "jurisdiction": "EA",
         "lang": "en", "expected_cadence_hours": 24,
         "rights_basis": "UNVERIFIED — no quotable commercial clause",
         "rights_state": "UNVERIFIED_EXCLUDED",
         "detail": "no quotable commercial-reuse clause"},
    ],
}


class _FakeResp:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_urlopen(monkeypatch, *, data: bytes | None = None, exc: Exception | None = None):
    def _fake(req, timeout=20):  # noqa: ARG001
        if exc is not None:
            raise exc
        return _FakeResp(data or b"")
    monkeypatch.setattr(urllib.request, "urlopen", _fake)


_EMPTY_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Empty</title></channel></rss>"""

_ONE_ITEM_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item>
  <title>Commission adopts EU Guidelines on exclusionary abuses of dominance</title>
  <link>https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1769</link>
  <description>The European Commission has adopted Guidelines on Article 102.</description>
  <category>POLICY_AREA=COMPETY,ANTITRUST</category>
  <pubDate>Sat, 05 Sep 2026 22:00:00 GMT</pubDate>
</item>
</channel></rss>"""

_FIVE_ITEM_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>Item one antitrust guidance</title><link>https://ec.europa.eu/a1</link>
  <description>One</description><pubDate>Sat, 05 Sep 2026 10:00:00 GMT</pubDate></item>
<item><title>Item two merger clearance</title><link>https://ec.europa.eu/a2</link>
  <description>Two</description><pubDate>Sat, 05 Sep 2026 11:00:00 GMT</pubDate></item>
<item><title>Item three state aid decision</title><link>https://ec.europa.eu/a3</link>
  <description>Three</description><pubDate>Sat, 05 Sep 2026 12:00:00 GMT</pubDate></item>
<item><title>Item four cartel fine</title><link>https://ec.europa.eu/a4</link>
  <description>Four</description><pubDate>Sat, 05 Sep 2026 13:00:00 GMT</pubDate></item>
<item><title>Item five dominance ruling</title><link>https://ec.europa.eu/a5</link>
  <description>Five</description><pubDate>Sat, 05 Sep 2026 14:00:00 GMT</pubDate></item>
</channel></rss>"""


def _redirect_data_paths(monkeypatch, tmp_path: Path) -> None:
    """Redirect BOTH this module's and qbus's parquet paths to tmp_path so no
    test ever touches the real repo data/ directory."""
    monkeypatch.setattr(eni, "_events_path", lambda: tmp_path / "europe_events.parquet")
    monkeypatch.setattr(eni, "_coverage_path", lambda: tmp_path / "europe_coverage.parquet")
    monkeypatch.setattr(qbus, "_events_path", lambda: tmp_path / "qbus_items.parquet")


# --------------------------------------------------------------------------- #
# 1. keep-FIRST restatement never overwrites first_seen
# --------------------------------------------------------------------------- #
def _record(event_id_="ev1", first_seen="2026-09-01T00:00:00+00:00",
           seendate="2026-09-01T00:00:00+00:00", title="Original title"):
    return {
        "event_id": event_id_, "item_id": "item-" + event_id_,
        "first_seen_utc": first_seen, "seendate": seendate,
        "fetch_clock_utc": first_seen, "asof": "2026-09-01",
        "title": title, "url": "https://example.eu/a", "source": "ec_presscorner",
        "domain": "ec.europa.eu", "source_tier": 1, "lang": "en",
        "theme": "regulatory", "jurisdiction": "EU", "coverage_state": "COVERED",
        "timestamp_quality": "PUBLISHER_STATED", "body_sha256": "",
        "rights_basis": "CC BY 4.0",
    }


def test_keep_first_restatement_does_not_overwrite_first_seen():
    first = _record()
    merged = eni.accrue(None, [first])
    assert len(merged) == 1

    restatement = _record(first_seen="2026-09-05T00:00:00+00:00",
                          seendate="2026-09-05T00:00:00+00:00",
                          title="A restated, different title")
    merged2 = eni.accrue(merged, [restatement])

    assert len(merged2) == 1
    row = merged2.iloc[0]
    assert row["first_seen_utc"] == "2026-09-01T00:00:00+00:00"
    assert row["seendate"] == "2026-09-01T00:00:00+00:00"
    assert row["title"] == "Original title"


# --------------------------------------------------------------------------- #
# 2. unreachable source -> fetch_rss None, never raises; fetch_all -> SOURCE_OUTAGE
# --------------------------------------------------------------------------- #
def test_unreachable_source_returns_none_without_raising(monkeypatch):
    _patch_urlopen(monkeypatch, exc=urllib.error.URLError("simulated dns failure"))
    result = eni.fetch_rss("https://example.invalid/down.rss")
    assert result is None

    items, cov = eni.fetch_all(_FAKE_CFG, date(2026, 9, 6))
    assert cov["ec_presscorner"] == "SOURCE_OUTAGE"
    assert cov["boe_news"] == "SOURCE_OUTAGE"
    # ecb_press is rights-excluded and never fetched at all, also SOURCE_OUTAGE
    assert cov["ecb_press"] == "SOURCE_OUTAGE"
    assert items == []


# --------------------------------------------------------------------------- #
# 3. empty feed -> NO_COVERAGE, never collapsed into SOURCE_OUTAGE
# --------------------------------------------------------------------------- #
def test_empty_feed_is_no_coverage_not_outage(monkeypatch):
    _patch_urlopen(monkeypatch, data=_EMPTY_RSS)
    result = eni.fetch_rss("https://example.invalid/empty.rss")
    assert result == []

    items, cov = eni.fetch_all(_FAKE_CFG, date(2026, 9, 6))
    assert cov["ec_presscorner"] == "NO_COVERAGE"
    assert cov["boe_news"] == "NO_COVERAGE"
    assert cov["ecb_press"] == "SOURCE_OUTAGE"  # rights-excluded, never fetched


# --------------------------------------------------------------------------- #
# 4. ingest degrades and never raises when every source is down
# --------------------------------------------------------------------------- #
def test_ingest_degrades_and_never_raises_when_all_sources_down(monkeypatch, tmp_path):
    monkeypatch.setattr(eni, "_cfg", lambda: _FAKE_CFG)
    _redirect_data_paths(monkeypatch, tmp_path)
    _patch_urlopen(monkeypatch, exc=urllib.error.URLError("simulated dns failure"))

    result = eni.ingest(asof=date(2026, 9, 6))

    assert result is not None
    assert isinstance(result, dict)
    assert result["n_new"] == 0
    cov = result["coverage"]
    configured_keys = {s["key"] for s in _FAKE_CFG["sources"]}
    assert set(cov.keys()) == configured_keys
    for key in configured_keys:
        assert cov[key] in eni.COVERAGE_STATES


# --------------------------------------------------------------------------- #
# 5. event_key assignment via qbus is deterministic and order-independent
# --------------------------------------------------------------------------- #
def test_event_key_is_deterministic_and_order_independent():
    crawled_at = "2026-09-06T07:00:00+00:00"
    asof = date(2026, 9, 6)
    articles = [
        {"title": "Commission adopts EU Guidelines on exclusionary abuses",
         "link": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1769",
         "description": "Guidelines on Article 102 abuse of dominance.",
         "category": "POLICY_AREA=COMPETY,ANTITRUST",
         "pubDate": "Wed, 02 Sep 2026 22:00:00 GMT", "source_key": "ec_presscorner"},
        {"title": "Commission adopts EU Guidelines on exclusionary abuse of dominance",
         "link": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1769b",
         "description": "A near-duplicate restatement of the same guidance.",
         "category": "POLICY_AREA=COMPETY,ANTITRUST",
         "pubDate": "Wed, 02 Sep 2026 22:05:00 GMT", "source_key": "ec_presscorner"},
        {"title": "Bank of England statement on RTGS standards release",
         "link": "https://www.bankofengland.co.uk/news/2026/august/rtgs",
         "description": "A delay to the RTGS standards release.",
         "category": "", "pubDate": "Thu, 27 Aug 2026 14:16:29 +0100",
         "source_key": "boe_news"},
    ]
    cov = {"ec_presscorner": "COVERED", "boe_news": "COVERED", "ecb_press": "SOURCE_OUTAGE"}

    def _sources(cfg=None):
        return _FAKE_CFG["sources"]

    import unittest.mock as mock
    with mock.patch.object(eni, "sources", side_effect=_sources):
        records = eni.build_records(articles, crawled_at, asof, cov)
        rows = eni.build_qbus_rows(records, articles, crawled_at)

    forward = {r["item_id"]: r["event_key"]
              for r in qbus.assign_event_keys(rows)}
    backward = {r["item_id"]: r["event_key"]
               for r in qbus.assign_event_keys(list(reversed(rows)))}
    assert forward == backward
    assert len(forward) == 3


# --------------------------------------------------------------------------- #
# 6. classify_theme never returns an empty theme
# --------------------------------------------------------------------------- #
def test_theme_is_never_empty():
    assert eni.classify_theme("") == "policy_geo_other"
    assert eni.classify_theme("A totally unrelated headline about cats") == "policy_geo_other"
    assert "" not in {eni.classify_theme(t) for t in ("", "cats", "dogs playing")}


# --------------------------------------------------------------------------- #
# 7. no ambient-time calls outside the ingest boundary
# --------------------------------------------------------------------------- #
def test_no_ambient_time_in_library_code():
    src_path = Path(inspect.getfile(eni))
    full_text = src_path.read_text()
    ingest_src, ingest_start = inspect.getsourcelines(eni.ingest)
    ingest_end = ingest_start + len(ingest_src)

    pattern = re.compile(r"date\.today\(\)|datetime\.now\(")
    offenders = []
    for lineno, line in enumerate(full_text.splitlines(), start=1):
        if pattern.search(line) and not (ingest_start <= lineno < ingest_end):
            offenders.append((lineno, line))
    assert offenders == [], f"ambient clock read outside ingest(): {offenders}"

    # the single allowed crawled_at default line IS present, inside ingest.
    ingest_body = "".join(ingest_src)
    assert "datetime.now(timezone.utc)" in ingest_body


# --------------------------------------------------------------------------- #
# 8. no LLM, no second event store
# --------------------------------------------------------------------------- #
def test_no_llm_and_no_second_event_store():
    src_path = Path(inspect.getfile(eni))
    text = src_path.read_text()
    assert not re.search(r"openai|anthropic|deepseek|llm_", text, re.IGNORECASE)
    # Desk artifact carries a locally-minted event_id + title/url; event_key
    # lives only in qbus. read_events() is a parquet reader and never joins
    # qbus (the previous "item_id-only + read-back" claim was false).
    assert "event_id" in eni._COLUMNS
    assert "item_id" in eni._COLUMNS
    assert "title" in eni._COLUMNS
    assert "url" in eni._COLUMNS
    assert "event_key" not in eni._COLUMNS
    reader = inspect.getsource(eni.read_events)
    assert "assign_event_keys" not in reader
    assert "read_items" not in reader
    assert "qbus" not in reader


# --------------------------------------------------------------------------- #
# extra — real preflight-captured fixtures (spec §3.1) parse into the expected
# per-source field shape (§ preflight "Field-shape notes for the builder's
# parser fixture"). Not one of the frozen 9; belt-and-suspenders on the two
# live sources' actual wire shape rather than synthetic XML only.
# --------------------------------------------------------------------------- #
_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "europe_news_intel"


def test_ec_presscorner_fixture_parses_with_category_and_url_guid(monkeypatch):
    data = (_FIXTURE_DIR / "ec_presscorner.xml").read_bytes()
    _patch_urlopen(monkeypatch, data=data)
    items = eni.fetch_rss("https://example.invalid/ec.rss")
    assert items and len(items) >= 4
    first = items[0]
    assert first["title"]
    assert first["link"].startswith("https://ec.europa.eu/")
    assert "POLICY_AREA=" in first["category"]
    assert eni.clean_time(first["pubDate"])  # RFC-822, parses cleanly


def test_boe_news_fixture_parses_with_no_category(monkeypatch):
    data = (_FIXTURE_DIR / "boe_news.xml").read_bytes()
    _patch_urlopen(monkeypatch, data=data)
    items = eni.fetch_rss("https://example.invalid/boe.rss")
    assert items and len(items) >= 4
    first = items[0]
    assert first["title"]
    assert first["link"].startswith("https://www.bankofengland.co.uk/")
    assert first["category"] == ""  # boe_news carries no <category> tags
    assert eni.clean_time(first["pubDate"])


# --------------------------------------------------------------------------- #
# 9. isolation — nothing in the scoring path imports this module
# --------------------------------------------------------------------------- #
# Scoring-path denylist — modules that mint or consume ranks/scores/gates.
# A later UI packet that mentions the string 'europe_news_intel' in a template
# builder must not red this test; only an import into a scoring module does.
_SCORING_PATH_MODULES: tuple[str, ...] = (
    "engine/axes.py",
    "engine/regime.py",
    "engine/conditions.py",
    "engine/transition.py",
    "engine/run.py",
    "engine/inputs.py",
    "engine/cycles.py",
    "engine/equity_alloc.py",
    "engine/news_vector.py",
    "engine/prophet_bridge.py",
    "engine/prophet_stage_inputs.py",
    "engine/us_board_rank.py",
)

_IMPORT_EUROPE = re.compile(
    r"^\s*(?:from engine import europe_news_intel"
    r"|from engine\.europe_news_intel"
    r"|import engine\.europe_news_intel)\b",
    re.MULTILINE,
)


def test_nothing_in_the_scoring_path_imports_this_module():
    root = config.ROOT
    offenders: list[str] = []
    for rel in _SCORING_PATH_MODULES:
        path = root / rel
        assert path.is_file(), f"scoring-path denylist entry missing: {rel}"
        text = path.read_text()
        if _IMPORT_EUROPE.search(text):
            offenders.append(rel)
    assert offenders == []


# --------------------------------------------------------------------------- #
# MAJOR-2 — ingest() success path (item_id recovery, qbus emit, coverage)
# --------------------------------------------------------------------------- #
def test_ingest_success_persists_item_id_qbus_event_key_and_coverage(
        monkeypatch, tmp_path):
    monkeypatch.setattr(eni, "_cfg", lambda: _FAKE_CFG)
    _redirect_data_paths(monkeypatch, tmp_path)
    _patch_urlopen(monkeypatch, data=_ONE_ITEM_RSS)
    crawled_at = "2026-09-06T12:00:00+00:00"

    result = eni.ingest(asof=date(2026, 9, 6), crawled_at=crawled_at)

    assert result is not None
    assert result["n_new"] > 0
    assert result["n_qbus"] > 0
    assert result["coverage"]["ec_presscorner"] == "COVERED"

    desk = eni.read_events()
    assert desk is not None
    assert len(desk) == result["n_new"]
    assert desk["item_id"].astype(str).str.len().min() > 0
    assert (desk["item_id"].astype(str) != "").all()
    assert "event_key" not in desk.columns

    qbus_path = tmp_path / "qbus_items.parquet"
    assert qbus_path.exists()
    qdf = qbus.read_items()
    assert qdf is not None
    assert len(qdf) >= 1
    assert (qdf["event_key"].astype(str).str.len() > 0).all()
    assert (qdf["event_key"].astype(str) != "").all()
    assert set(qdf["desk"].unique()) == {eni.DESK}

    cov_path = tmp_path / "europe_coverage.parquet"
    assert cov_path.exists()
    import pandas as pd
    cov_df = pd.read_parquet(cov_path)
    ec = cov_df[cov_df["source_key"] == "ec_presscorner"]
    assert len(ec) == 1
    assert int(ec.iloc[0]["n_items"]) > 0
    assert ec.iloc[0]["coverage_state"] == "COVERED"


# --------------------------------------------------------------------------- #
# MAJOR-3 — max_per_source actually slices each feed
# --------------------------------------------------------------------------- #
def test_max_per_source_caps_items_per_source(monkeypatch):
    cfg = {**_FAKE_CFG, "max_per_source": 2}
    _patch_urlopen(monkeypatch, data=_FIVE_ITEM_RSS)
    items, cov = eni.fetch_all(cfg, date(2026, 9, 6),
                               crawled_at="2026-09-06T12:00:00+00:00")
    by_source: dict[str, list] = {}
    for it in items:
        by_source.setdefault(it["source_key"], []).append(it)
    assert len(by_source["ec_presscorner"]) == 2
    assert len(by_source["boe_news"]) == 2
    assert "ecb_press" not in by_source  # rights-excluded, never fetched
    assert sum(len(v) for v in by_source.values()) == 4
    assert cov["ec_presscorner"] == "COVERED"
    # A silent no-op of the slice (cap applied after items.extend) would
    # yield 5 items per verified source = 10.
    assert len(items) == 4


# --------------------------------------------------------------------------- #
# MAJOR-4 — qbus keeps same-title restatements; desk keep-FIRST on event_id
# --------------------------------------------------------------------------- #
def test_qbus_keeps_same_title_restatements_desk_dedups_on_event_id(monkeypatch):
    crawled_at = "2026-09-06T12:00:00+00:00"
    asof = date(2026, 9, 6)
    articles = [
        {"title": "Daily News",
         "link": "https://ec.europa.eu/commission/presscorner/detail/en/mex_26_1",
         "description": "First print of the daily news.",
         "category": "", "pubDate": "Sat, 05 Sep 2026 08:00:00 GMT",
         "source_key": "ec_presscorner"},
        {"title": "Daily News",
         "link": "https://ec.europa.eu/commission/presscorner/detail/en/mex_26_2",
         "description": "Restatement of the same daily news, different URL.",
         "category": "", "pubDate": "Sat, 05 Sep 2026 09:00:00 GMT",
         "source_key": "ec_presscorner"},
    ]
    cov = {"ec_presscorner": "COVERED", "boe_news": "COVERED",
           "ecb_press": "SOURCE_OUTAGE"}

    def _sources(cfg=None):  # noqa: ARG001
        return _FAKE_CFG["sources"]

    import unittest.mock as mock
    with mock.patch.object(eni, "sources", side_effect=_sources):
        records = eni.build_records(articles, crawled_at, asof, cov)
        rows = eni.build_qbus_rows(records, articles, crawled_at)

    assert len(records) == 2
    assert records[0]["event_id"] == records[1]["event_id"]
    assert records[0]["url"] != records[1]["url"]
    assert records[0]["item_id"] != records[1]["item_id"]
    # qkernel.item_id keys on host+title only — the collision this helper exists to avoid.
    assert qkernel.item_id("ec_presscorner", articles[0]["link"], "Daily News", "en") == \
        qkernel.item_id("ec_presscorner", articles[1]["link"], "Daily News", "en")
    assert len(rows) == 2

    keyed = qbus.assign_event_keys(rows)
    assert keyed[0]["item_id"] != keyed[1]["item_id"]
    assert keyed[0]["event_key"] == keyed[1]["event_key"]
    assert keyed[0]["event_key"].startswith("ev_")

    desk = eni.accrue(None, records)
    assert len(desk) == 1
    assert desk.iloc[0]["url"] == articles[0]["link"]

    # Recurring exact title on a later day still reaches qbus (desk stays 1).
    later = [{**articles[0],
              "link": "https://ec.europa.eu/commission/presscorner/detail/en/mex_26_9",
              "pubDate": "Mon, 07 Sep 2026 08:00:00 GMT"}]
    with mock.patch.object(eni, "sources", side_effect=_sources):
        later_recs = eni.build_records(later, "2026-09-07T12:00:00+00:00",
                                       date(2026, 9, 7), cov)
    assert len(later_recs) == 1
    assert later_recs[0]["event_id"] == records[0]["event_id"]
    desk2 = eni.accrue(desk, later_recs)
    assert len(desk2) == 1
    later_rows = eni.build_qbus_rows(later_recs, later, "2026-09-07T12:00:00+00:00")
    assert len(later_rows) == 1
    assert later_rows[0]["url"] == later[0]["link"]
    assert later_rows[0]["title"] == "Daily News"


# --------------------------------------------------------------------------- #
# MINOR-1 — weekly cadence uses 1x grace, not x3
# --------------------------------------------------------------------------- #
def test_weekly_source_flags_delayed_after_one_cadence_not_three():
    crawled_at = "2026-09-06T12:00:00+00:00"
    asof = date(2026, 9, 6)
    # 8 days stale — the preflight observation. 192h > 168h (1x) but
    # 192h < 504h (3x), so the old multiplier would have stayed COVERED.
    eight_day = "2026-08-29T12:00:00+00:00"
    assert eni._is_delayed(eight_day, asof, 168, crawled_at) is True
    two_day = "2026-09-04T12:00:00+00:00"
    assert eni._is_delayed(two_day, asof, 168, crawled_at) is False
    # Daily sources still use 3x (72h grace).
    seventy = "2026-09-03T14:00:00+00:00"  # 70h before crawled_at
    eighty = "2026-09-03T04:00:00+00:00"   # 80h before crawled_at
    assert eni._is_delayed(seventy, asof, 24, crawled_at) is False
    assert eni._is_delayed(eighty, asof, 24, crawled_at) is True


# --------------------------------------------------------------------------- #
# MINOR-2 — staleness anchors on crawled_at, not end-of-asof-day
# --------------------------------------------------------------------------- #
def test_staleness_uses_crawled_at_not_end_of_asof_day():
    asof = date(2026, 9, 6)
    crawled_at = "2026-09-06T12:00:00+00:00"
    # 68h before crawled_at (COVERED under 72h grace) but 80h before
    # 2026-09-06T23:59:59 (DELAYED if the old end-of-day anchor still ran).
    newest = "2026-09-03T16:00:00+00:00"
    assert eni._is_delayed(newest, asof, 24, crawled_at) is False
    # Same item with no crawled_at falls back to start of asof (60h) — COVERED.
    assert eni._is_delayed(newest, asof, 24, None) is False
    # And with a crawl clock that makes it 80h old — DELAYED.
    late_crawl = "2026-09-06T23:59:59+00:00"
    assert eni._is_delayed(newest, asof, 24, late_crawl) is True


# --------------------------------------------------------------------------- #
# MINOR-4 — jurisdiction tokens are word-bounded
# --------------------------------------------------------------------------- #
def test_jurisdiction_uk_eu_tokens_use_word_boundaries(monkeypatch):
    monkeypatch.setattr(eni, "sources", lambda cfg=None: _FAKE_CFG["sources"])
    # Unanchored "uk " used to match any word ending in uk + space.
    assert eni.jurisdiction_for("ec_presscorner", "the luk news update") == "EU"
    assert eni.jurisdiction_for("ec_presscorner", "the chuk market opened") == "EU"
    assert eni.jurisdiction_for("ec_presscorner", "the UK gilt auction") == "UK"
    assert eni.jurisdiction_for("ec_presscorner", "Bank of England statement") == "UK"
    # Unanchored "eu " used to match "nouveau ".
    assert eni.jurisdiction_for("ecb_press", "nouveau framework published") == "EA"
    assert eni.jurisdiction_for("boe_news", "EU member state consultation") == "EU"
