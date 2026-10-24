"""Network-dark tests for Tiingo's future canonical SQLite news producer.

All owner grants and source articles here are synthetic. No vendor API, live
credentials, external publishing or production activation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import pytest

from engine import qbus_news_contract as contract
from engine import qbus_news_quality as quality
from engine import qbus_news_receipts as rights
from engine import tiingo_news

NOW = datetime(2026, 10, 9, 8, tzinfo=timezone.utc)


def normalized(source="reuters.com", **raw_overrides):
    item = {
        "id": 81234,
        "title": "Chipmaker reports quarterly revenue growth",
        "url": f"https://www.{source}/news/example-81234",
        "source": source,
        "publishedDate": "2026-10-09T07:00:00Z",
        "crawlDate": "2026-10-09T07:10:00Z",
        "description": "Quarterly results reported.",
        "tickers": ["MU", "AMD"],
        "tags": ["earnings"],
    }
    item.update(raw_overrides)
    return tiingo_news.normalize_article(item, received_at=NOW)


def synthetic_receipt(**overrides):
    payload = {
        "schema": rights.RIGHTS_SCHEMA,
        "status": "approved",
        "receipt_id": "synthetic-tiingo-rights-r1",
        "owner_ref": "SYNTHETIC-TEST-NOT-A-CONTRACT",
        "source": "tiingo",
        "product_id": "TEST-ONLY-tiingo-news",
        "audiences": ["site_full"],
        "effective_at": "2026-10-01T00:00:00Z",
        "expires_at": "2026-11-01T00:00:00Z",
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": False,
            "teaser_display": False,
            "body_display": False,
            "image_display": False,
            "derivative_processing": True,
        },
    }
    payload.update(overrides)
    return payload


def test_generic_benzinga_normalizer_never_aliases_tiingo_into_another_source():
    # Tiingo has its own validated normalized entrypoint; a generic transport
    # enum must not accidentally parse a Tiingo frame as massive/Benzinga.
    with pytest.raises(contract.NewsContractError, match="unsupported_transport"):
        contract.normalize_news(
            {"id": 81234, "title": "Report"}, transport="tiingo_rest",
            received_at=NOW,
        )


def test_tiingo_normalization_preserves_publisher_source_and_receipt_clock():
    news = contract.normalize_tiingo_news(normalized(), received_at=NOW)
    assert news.source == "tiingo:reuters.com"
    assert news.source_item_id == "81234"
    assert news.transport == "tiingo_rest"
    assert news.action == "updated" and not news.action_explicit
    assert news.version_clock_domain == "tiingo_provider_crawl"
    assert news.published_at.isoformat() == "2026-10-09T07:00:00+00:00"
    assert news.received_at == NOW
    assert news.version_at.isoformat() == "2026-10-09T07:10:00+00:00"
    assert news.provider_tickers == ("MU", "AMD")
    assert not news.body_sha256


def test_tiingo_normalization_refuses_unbound_or_mutated_identity():
    clean = normalized()
    for changes in (
        {"provider": "benzinga"},
        {"source": "fakebloomberg.com"},
        {"url": "https://evil.example/x"},
        {"received_at": "2026-10-09T06:00:00+00:00"},
        {"provider_id": True},
        {"tickers": "MU"},
    ):
        with pytest.raises(contract.NewsContractError):
            contract.normalize_tiingo_news({**clean, **changes}, received_at=NOW)


def test_tiingo_publisher_based_editorial_gate_uses_original_domain():
    assert quality.publisher_identity("tiingo:reuters.com") == "reuters.com"
    assert quality.curated_source("tiingo:reuters.com")
    assert not quality.curated_source("tiingo:fakebloomberg.com")
    assert not quality.curated_source("tiingo:fool.com")
    assert not quality.curated_source("tiingo:zacks.com")


def test_tiingo_receipt_defaults_to_no_authenticated_publisher_display(tmp_path: Path):
    p = tmp_path / "owner.json"
    p.write_text(json.dumps(synthetic_receipt()), encoding="utf-8")
    assert rights.load_rights_set([p], now=NOW) == ()  # historical default remains closed
    parsed = rights.load_rights_set([p], now=NOW, allow_tiingo=True)
    assert len(parsed) == 1
    assert parsed[0].source == "tiingo"
    assert parsed[0].rights.allows("tiingo", "title")
    assert not parsed[0].rights.allows("tiingo:reuters.com", "title")


def test_tiingo_explicit_publisher_grant_is_exact_and_field_narrow(tmp_path: Path):
    p = tmp_path / "owner.json"
    p.write_text(json.dumps(synthetic_receipt(
        licensed_publisher_domains=["reuters.com", "apnews.com"],
    )), encoding="utf-8")
    assert rights.load_rights_set([p], now=NOW) == ()  # historical default remains closed
    parsed = rights.load_rights_set([p], now=NOW, allow_tiingo=True)
    assert len(parsed) == 1
    grant = parsed[0].rights
    assert grant.allows("tiingo:reuters.com", "title")
    assert grant.allows("tiingo:apnews.com", "title")
    assert not grant.allows("tiingo:fakebloomberg.com", "title")
    assert not grant.allows("tiingo:reuters.com", "url")
    assert not grant.allows("tiingo:reuters.com", "teaser")


@pytest.mark.parametrize("publishers", [
    ["*.reuters.com"], ["example"], ["https://reuters.com"],
    ["reuters.com", "REUTERS.COM"], ["reuters.com", 42],
])
def test_tiingo_publisher_grant_rejects_wildcards_and_ambiguous_values(publishers):
    with pytest.raises(rights.NewsReceiptError):
        rights.parse_rights_receipt(synthetic_receipt(
            licensed_publisher_domains=publishers,
        ), now=NOW, source="tiingo")


def test_tiingo_no_cross_source_rights_borrowing():
    grant = rights.parse_rights_receipt(synthetic_receipt(
        licensed_publisher_domains=["reuters.com"],
    ), now=NOW, source="tiingo")
    for other in ("benzinga", "massive:reuters.com", "tiingo:reuters.com.evil.example"):
        assert not grant.rights.allows(other, "title")


def _qualified_universe():
    from datetime import timedelta
    from engine.qbus_news_universe import qualify_universe
    return qualify_universe({
        "owner": "SYNTHETIC-security-reference", "revision": "test-tiingo-news",
        "complete": True, "truncated": False,
        "effective_at": NOW - timedelta(days=1),
        "known_at": NOW - timedelta(hours=1),
        "fresh_until": NOW + timedelta(days=1),
        "securities": [{
            "security_id": "sec-MU", "ticker": "MU", "aliases": ["MU"],
            "valid_from": NOW - timedelta(days=100), "valid_to": None,
            "known_at": NOW - timedelta(days=100),
        }],
    }, asof=NOW)


def test_tiingo_sqlite_store_first_receipt_and_read_revocation(tmp_path: Path):
    """Synthetic accepted observation -> real SQLite writer -> rights read."""
    from datetime import timedelta
    from collectors.benzinga_news import route_revision
    from engine.qbus_news_store import NewsStore, NewsReadRights

    universe = _qualified_universe()
    assert universe.status == "qualified"
    grant = rights.parse_rights_receipt(synthetic_receipt(
        licensed_publisher_domains=["reuters.com"],
    ), now=NOW, source="tiingo")
    db = tmp_path / "synthetic.sqlite3"
    with NewsStore(db, source_key="test-only") as store:
        revision = contract.normalize_tiingo_news(
            normalized(tickers=["MU"]), received_at=NOW,
        )
        routed = route_revision(revision, universe)
        assert routed.security_ids == ("sec-MU",)
        first = store.commit_observations([routed])
        assert first.applied_states == 1
        accepted = store.snapshot("sec-MU", limit=20, cursor=None, rights=grant.rights)
        assert len(accepted.rows) == 1
        assert accepted.rows[0].source == "tiingo:reuters.com"
        assert accepted.rows[0].url == ""
        assert accepted.rows[0].teaser == ""
        # The actual curated, read-only API store must enforce the SAME
        # per-publisher rights, not merely accept a generic writer snapshot.
        from engine.qbus_news_editorial import NewsEditorialView
        with NewsStore.open_readonly(
            db, source_key="test-only", curated=True,
            editorial_view=NewsEditorialView(mode="all"),
        ) as reader:
            curated = reader.snapshot(
                "sec-MU", limit=20, cursor=None, rights=grant.rights,
            )
            assert len(curated.rows) == 1
            assert curated.rows[0].source == "tiingo:reuters.com"
            assert curated.rows[0].url == ""
            assert curated.rows[0].teaser == ""
            denied = NewsReadRights(frozenset())
            assert not reader.snapshot(
                "sec-MU", limit=20, cursor=None, rights=denied,
            ).rows
        # Different Mastermind receipt time, same publisher crawl/version and
        # source article identity: the first persisted observation survives.
        later = NOW + timedelta(minutes=15)
        later_obs = tiingo_news.normalize_article({
            "id": 81234, "title": "Chipmaker reports quarterly revenue growth",
            "url": "https://www.reuters.com/news/example-81234",
            "source": "reuters.com",
            "publishedDate": "2026-10-09T07:00:00Z",
            "crawlDate": "2026-10-09T07:10:00Z",
            "description": "Quarterly results reported.",
            "tickers": ["MU"], "tags": ["earnings"],
        }, received_at=later)
        duplicate = contract.normalize_tiingo_news(later_obs, received_at=later)
        second = store.commit_observations([route_revision(duplicate, universe)])
        assert second.applied_states == 0
        assert len(store.snapshot("sec-MU", limit=20, cursor=None, rights=grant.rights).rows) == 1
        # Revoked rights suppress the user read, without erasing historical
        # first-observation evidence from the sole qbus store.
        revoked = NewsReadRights(frozenset())
        assert not store.snapshot("sec-MU", limit=20, cursor=None, rights=revoked).rows
        assert len(store.snapshot("sec-MU", limit=20, cursor=None, rights=grant.rights).rows) == 1


def test_tiingo_sqlite_denied_publisher_cannot_borrow_another_grant(tmp_path: Path):
    from collectors.benzinga_news import route_revision
    from engine.qbus_news_store import NewsStore

    allowed = rights.parse_rights_receipt(synthetic_receipt(
        licensed_publisher_domains=["apnews.com"],
    ), now=NOW, source="tiingo").rights
    revision = contract.normalize_tiingo_news(
        normalized(tickers=["MU"]), received_at=NOW,
    )
    with NewsStore(tmp_path / "synthetic.sqlite3", source_key="test-only") as store:
        store.commit_observations([route_revision(revision, _qualified_universe())])
        assert not store.snapshot("sec-MU", limit=20, cursor=None, rights=allowed).rows


def test_api_tiingo_publisher_rights_need_explicit_flag_and_receipt(tmp_path: Path, monkeypatch):
    """The real API rights owner must not adopt Tiingo on receipt possession."""
    from datetime import timedelta
    from app import ticker_news as api

    now = datetime.now(timezone.utc)
    permitted = synthetic_receipt(licensed_publisher_domains=["reuters.com"])
    permitted["effective_at"] = (now - timedelta(hours=1)).isoformat()
    permitted["expires_at"] = (now + timedelta(hours=1)).isoformat()
    path = tmp_path / "test-only-rights.json"
    path.write_text(json.dumps(permitted))
    monkeypatch.delenv("MM_TICKER_NEWS_RIGHTS", raising=False)
    monkeypatch.setenv("MM_TICKER_NEWS_ADDITIONAL_RIGHTS", "[]")
    monkeypatch.setenv("TIINGO_NEWS_RIGHTS_FILE", str(path))
    monkeypatch.delenv("TIINGO_NEWS_ENABLED", raising=False)
    assert api._current_rights_receipts() == ()

    monkeypatch.setenv("TIINGO_NEWS_ENABLED", "1")
    admitted = api._current_rights_receipts()
    assert len(admitted) == 1 and admitted[0].source == "tiingo"
    assert admitted[0].rights.allows("tiingo:reuters.com", "title")
    assert not admitted[0].rights.allows("tiingo:reuters.com", "url")
    assert not admitted[0].rights.allows("tiingo:reuters.com", "teaser")

    path.write_text(json.dumps({**permitted, "status": "revoked"}))
    assert api._current_rights_receipts() == ()
    path.write_text(json.dumps(permitted))
    monkeypatch.setenv("TIINGO_NEWS_ENABLED", "0")
    assert api._current_rights_receipts() == ()


def test_api_revoking_tiingo_does_not_revoke_other_source(tmp_path: Path, monkeypatch):
    """A Tiingo owner receipt is source-local, not a replacement auth plane."""
    from datetime import timedelta
    from app import ticker_news as api

    now = datetime.now(timezone.utc)
    tiingo = synthetic_receipt(licensed_publisher_domains=["reuters.com"])
    tiingo["effective_at"] = (now - timedelta(hours=1)).isoformat()
    tiingo["expires_at"] = (now + timedelta(hours=1)).isoformat()
    primary = {
        **synthetic_receipt(),
        "receipt_id": "fixture-existing-benzinga",
        "source": "benzinga",
        "product_id": "fixture-benzinga",
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": False,
            "teaser_display": False,
            "derivative_processing": False,
        },
        "effective_at": tiingo["effective_at"],
        "expires_at": tiingo["expires_at"],
    }
    current = tmp_path / "fixture-benzinga.json"
    extra = tmp_path / "fixture-tiingo.json"
    current.write_text(json.dumps(primary))
    extra.write_text(json.dumps(tiingo))
    monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(current))
    monkeypatch.setenv("MM_TICKER_NEWS_ADDITIONAL_RIGHTS", "[]")
    monkeypatch.setenv("TIINGO_NEWS_ENABLED", "1")
    monkeypatch.setenv("TIINGO_NEWS_RIGHTS_FILE", str(extra))
    grant = api._rights_for_user({"synthetic": True})
    assert grant is not None
    assert grant.allows("benzinga", "title")
    assert grant.allows("tiingo:reuters.com", "title")

    extra.write_text(json.dumps({**tiingo, "status": "revoked"}))
    after = api._rights_for_user({"synthetic": True})
    assert after is not None and after.allows("benzinga", "title")
    assert not after.allows("tiingo:reuters.com", "title")
