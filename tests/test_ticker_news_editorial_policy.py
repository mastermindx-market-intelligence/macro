"""Product regressions: rights and a vendor subscription do not imply curation."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engine.news_common import ticker_editorial_reason
from engine.qkernel import publisher_category, publisher_tier, source_tier
from engine.qbus_news_contract import normalize_news, normalize_massive_news
from engine.qbus_news_store import NewsStore, NewsReadRights, RoutedRevision
from engine.qbus_news_receipts import HEALTH_SCHEMA, parse_health_receipt

T0 = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)
SECURITY = "sec-NVDA"
GOOD = "Nvidia launches new AI accelerator"
OTHER = "Nvidia secures export approval for its data center chips"
FOOL = "Where Will VGT Be in 20 Years? Here's What History Suggests."
ZACKS = "AI Stock Sell-Off: Are Mag 7 Stocks Still Buys? ETFs in Focus"


def report(source, item, title, minute=1):
    clock = T0 + timedelta(minutes=minute)
    if source == "benzinga":
        rev = normalize_news({
            "id": item, "title": title, "url": "https://benzinga.com/news/" + item,
            "teaser": "Fictional test summary.", "created": T0.isoformat(),
            "updated": clock.isoformat(), "stocks": ["NVDA"],
        }, transport="benzinga_rest", received_at=clock)
    else:
        domain = source.removeprefix("massive:")
        rev = normalize_massive_news({
            "id": item, "title": title, "article_url": "https://" + domain + "/news/" + item,
            "description": "Fictional test summary.", "published_utc": clock.isoformat(),
            "tickers": ["NVDA"], "publisher": {"name": "Fixture", "homepage_url": "https://" + domain},
        }, received_at=clock)
    return RoutedRevision(rev, (SECURITY,), "fixture-universe")


def commit(store, rows):
    return store.commit(rows, expected_cursor=store.current_cursor(), next_cursor=str(store.counts()["revisions"] + len(rows)))


def rights(*sources):
    return NewsReadRights(frozenset(sources or ("benzinga",)))


def parsed_health(state="live", extra_state="available", publishers=None):
    clock = T0 + timedelta(hours=1)
    return parse_health_receipt({
        "schema": HEALTH_SCHEMA, "source": "benzinga", "state": state,
        "observed_at": clock.isoformat(), "last_successful_catchup": clock.isoformat(),
        "gap_unresolved": False,
        "additional_sources": [{"provider": "massive", "state": extra_state,
            "publishers": publishers if publishers is not None else ["fool.com", "globenewswire.com", "zacks.com"],
            "accepted_reports": 100, "last_successful_poll": clock.isoformat()}],
    }, now=clock)


def reader(db):
    return NewsStore.open_readonly(db, source_key="test", curated=True)


@pytest.mark.parametrize("domain,title,reason", [
    ("fool.com", FOOL, "publisher_excluded"),
    ("zacks.com", ZACKS, "publisher_excluded"),
    ("www.FOOL.com", GOOD, "publisher_excluded"),
    ("news.zacks.com", GOOD, "publisher_excluded"),
    ("tipranks.com", GOOD, "publisher_excluded"),
    ("benzinga.com", FOOL, "single_stock_advertorial"),
    ("cnbc.com", "5 Stocks to Buy Now", "stock_pick_roundup"),
    ("benzinga.com", "What to watch ahead of Nvidia earnings", "calendar_preview"),
    ("benzinga.com", "Nvidia reports after the closing bell", "calendar_preview"),
    ("benzinga.com", "Nvidia earnings preview: what to expect", "calendar_preview"),
    ("benzinga.com", "Closing bell: Nvidia reports record revenue", "calendar_preview"),
    ("benzinga.com", "Live updates: Nvidia reports record revenue after the closing bell", "calendar_preview"),
    ("benzinga.com", "Stocks making the biggest moves: Microsoft raises its dividend ahead of earnings", "calendar_preview"),
    ("benzinga.com", "Earnings calendar: Microsoft raises its dividend ahead of earnings", "calendar_preview"),
    ("benzinga.com", "Nvidia could report record revenue after the closing bell", "calendar_preview"),
    ("unknown.example", GOOD, "publisher_unreviewed"),
    ("notreuters.com", GOOD, "publisher_unreviewed"),
    ("reuters.com.attacker.example", GOOD, "publisher_unreviewed"),
    ("example.com", GOOD, "publisher_unreviewed"),
    ("globenewswire.com", "SHAREHOLDER ALERT: Deadline Reminder for Investors", "solicitation_press_release"),
])
def test_publisher_and_article_policy_catches_reported_leaks(domain, title, reason):
    assert ticker_editorial_reason(title, domain) == reason


@pytest.mark.parametrize("domain,title", [
    ("reuters.com", GOOD), ("www.bloomberg.com", OTHER),
    ("benzinga.com", "Nvidia raises quarterly dividend by 10%"),
    ("benzinga.com", "Microsoft raises its dividend ahead of earnings"),
    ("benzinga.com", "Nvidia reports record revenue after the closing bell"),
    ("benzinga.com", "Nvidia reports $20 billion in quarterly revenue before the open"),
    ("benzinga.com", "Aster secures FDA approval ahead of earnings"),
    ("globenewswire.com", "Aster reports record quarterly revenue"),
    ("businesswire.com", "Aster announces FDA approval of its new therapy"),
    ("cnbc.com", "Why did Nvidia shares fall after its earnings beat?"),
])
def test_factual_reporting_and_primary_announcements_survive(domain, title):
    assert ticker_editorial_reason(title, domain) is None


def test_canonical_tiers_do_not_upgrade_excluded_or_lookalike_publishers():
    assert source_tier("fool.com") == source_tier("zacks.com") == 0
    assert publisher_tier("notreuters.com") == publisher_tier("reuters.com.evil.test") == 0
    assert publisher_category("globenewswire.com") == "press_release"
    assert publisher_category("benzinga.com") == "reporting"


def test_filter_precedes_limit_and_pagination_and_preserves_raw_history(tmp_path):
    db = tmp_path / "news.sqlite3"
    with NewsStore(db, source_key="test") as store:
        commit(store, [report("benzinga", "good", GOOD), report("benzinga", "other", OTHER)])
        commit(store, [report("benzinga", str(i), f"Prediction: Nvidia shares will reach ${i + 1000}", i + 2) for i in range(35)])
        commit(store, [report("massive:fool.com", "f", FOOL), report("massive:zacks.com", "z", ZACKS)])
        before = store.counts()
    grant = rights("benzinga", "massive:fool.com", "massive:zacks.com")
    with reader(db) as store:
        first = store.snapshot(SECURITY, limit=1, cursor=None, rights=grant)
        assert len(first.rows) == 1 and first.has_more
        second = store.snapshot(SECURITY, limit=1, cursor=first.next_cursor, rights=grant)
        assert len(second.rows) == 1 and not second.has_more
        assert {first.rows[0].title, second.rows[0].title} == {GOOD, OTHER}
        assert store.counts() == before
        flow = store.news_flow(SECURITY, now=T0 + timedelta(hours=1), rights=grant)
        assert flow["reports_24h"] == 2 and flow["stories_24h"] == 2
        assert flow["provenance"]["sources_counted"] == ["benzinga"]
    with NewsStore.open_readonly(db, source_key="test") as store:
        assert len(store.snapshot(SECURITY, limit=100, cursor=None, rights=grant).rows) > 20


def test_group_details_and_source_counts_use_only_curated_reports(tmp_path):
    db = tmp_path / "news.sqlite3"
    grant = rights("massive:reuters.com", "massive:fool.com")
    with NewsStore(db, source_key="test") as store:
        commit(store, [report("massive:reuters.com", "r", GOOD), report("massive:fool.com", "f", GOOD)])
        raw = store.snapshot(SECURITY, limit=20, cursor=None, rights=grant)
        assert raw.rows[0].item_count == 2
        story_id = raw.rows[0].story_id
    with reader(db) as store:
        row = store.snapshot(SECURITY, limit=20, cursor=None, rights=grant).rows[0]
        detail = store.story(story_id, rights=grant)
        assert row.source_count == row.item_count == detail.source_count == detail.item_count == 1
        assert [member.source for member in detail.members] == ["massive:reuters.com"]
        changes = store.projected_changes_for_security(SECURITY, after_sequence=0, limit=50, rights=grant)
        assert len(changes.rows) == 1 and changes.rows[0].source == "massive:reuters.com"


def test_correction_to_advertorial_emits_removal_and_can_be_restored(tmp_path):
    db = tmp_path / "news.sqlite3"
    with NewsStore(db, source_key="test") as writer:
        commit(writer, [report("benzinga", "one", GOOD)])
        with reader(db) as store:
            snapshot = store.snapshot(SECURITY, limit=20, cursor=None, rights=rights())
            story_id = snapshot.rows[0].story_id
            commit(writer, [report("benzinga", "one", FOOL, 2)])
            page = store.projected_changes_for_security(SECURITY, after_sequence=snapshot.change_sequence, limit=50, rights=rights())
            assert len(page.rows) == 1 and page.rows[0].kind == "remove"
            assert page.rows[0].title == page.rows[0].teaser == page.rows[0].url == ""
            assert page.next_sequence > snapshot.change_sequence
            assert store.story(story_id, rights=rights()) is None
            assert store.news_flow(SECURITY, now=T0 + timedelta(hours=1), rights=rights())["reports_24h"] == 0
            commit(writer, [report("benzinga", "one", GOOD, 3)])
            restored = store.projected_changes_for_security(SECURITY, after_sequence=page.next_sequence, limit=50, rights=rights())
            assert len(restored.rows) == 1 and restored.rows[0].kind == "upsert"
            assert restored.rows[0].title == GOOD


def test_quality_never_grants_rights_or_uses_a_hidden_title(tmp_path):
    db = tmp_path / "news.sqlite3"
    with NewsStore(db, source_key="test") as writer:
        commit(writer, [report("massive:reuters.com", "r", GOOD)])
    with reader(db) as store:
        assert not store.snapshot(SECURITY, limit=20, cursor=None, rights=rights()).rows
        no_title = NewsReadRights(frozenset({"massive:reuters.com"}), allow_title=False)
        assert not store.snapshot(SECURITY, limit=20, cursor=None, rights=no_title).rows


def test_real_api_open_path_filters_snapshot_details_changes_and_labels_releases(monkeypatch, tmp_path):
    from app import ticker_news
    db = tmp_path / "news.sqlite3"
    sources = ("benzinga", "massive:fool.com", "massive:zacks.com", "massive:globenewswire.com")
    with NewsStore(db, source_key="test") as store:
        commit(store, [report("massive:fool.com", "f", FOOL), report("massive:zacks.com", "z", ZACKS)])
        excluded_id = store.snapshot(SECURITY, limit=20, cursor=None, rights=rights(*sources)).rows[0].story_id
        commit(store, [report("massive:globenewswire.com", "p", "Aster reports record quarterly revenue")])
    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(ticker_news, "_security_for_ticker", lambda ticker, now: SECURITY)
    monkeypatch.setattr(ticker_news, "_rights_for_user", lambda user: rights(*sources))
    monkeypatch.setattr(ticker_news, "_source_health", parsed_health)
    monkeypatch.setattr(ticker_news, "_derivative_permitted_after_rights", lambda: True)
    monkeypatch.setattr(ticker_news, "_flow_now", lambda: T0 + timedelta(hours=1))
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {"id": "editorial-fixture"}
    with TestClient(app) as client:
        response = client.get("/api/ticker-news/NVDA")
        assert response.status_code == 200
        payload = response.json()
        assert payload["editorial_policy"] == "ticker_news.curated.v1"
        assert len(payload["rows"]) == 1
        assert payload["rows"][0]["content_kind"] == "press_release"
        assert payload["flow"]["reports_24h"] == 1
        assert payload["source_health"]["additional_sources"] == [{
            "provider": "massive", "state": "available", "configured_publishers": ["globenewswire.com"],
            "last_successful_poll": (T0 + timedelta(hours=1)).isoformat(), "delivery": "polled",
        }]
        assert client.get("/api/ticker-news/stories/" + excluded_id).status_code == 404
        changes = client.get("/api/ticker-news/NVDA/changes").json()
        assert len(changes["rows"]) == 1 and changes["rows"][0]["content_kind"] == "press_release"
        assert response.headers["cache-control"] == "private, no-store"


def test_excluded_publisher_health_cannot_degrade_or_rescue_curated_delivery():
    from app import ticker_news
    raw = parsed_health(extra_state="unavailable", publishers=["fool.com", "zacks.com"])
    scoped = ticker_news._curated_health(raw, rights("benzinga", "massive:fool.com", "massive:zacks.com"))
    assert scoped["additional_sources"] == []
    assert ticker_news._state_from_health(scoped, row_count=1) == "live"
    assert len(raw["additional_sources"][0]["configured_publishers"]) == 2
    raw["state"] = "unavailable"
    raw["additional_sources"][0]["state"] = "available"
    scoped = ticker_news._curated_health(raw, rights("massive:fool.com", "massive:zacks.com"))
    assert ticker_news._state_from_health(scoped, row_count=0) == "unavailable"


def test_health_does_not_claim_a_title_restricted_publisher():
    from app import ticker_news
    scoped = ticker_news._curated_health({"state": "live"}, NewsReadRights(frozenset({"benzinga"}), allow_title=False))
    assert scoped["state"] == "unavailable"
    assert scoped["last_successful_catchup"] is None


@pytest.mark.parametrize("primary,additional,expected", [
    ("unavailable", "available", "degraded"),
    ("live", "unavailable", "degraded"),
    ("live", "available", "live"),
])
def test_curated_health_preserves_qualified_parsed_additional_source(primary, additional, expected):
    from app import ticker_news
    parsed = parsed_health(state=primary, extra_state=additional)
    scoped = ticker_news._curated_health(parsed, rights("benzinga", "massive:globenewswire.com"))
    extra = scoped["additional_sources"][0]
    assert extra["configured_publishers"] == ["globenewswire.com"]
    assert "accepted_reports_since_start" not in extra
    assert parsed["additional_sources"][0]["accepted_reports_since_start"] == 100
    assert ticker_news._state_from_health(scoped, row_count=1) == expected
