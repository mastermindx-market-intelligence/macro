"""Tiingo provider contract, source-rights and News Intelligence wiring regression tests.

No external network, real credential, production receipts or live storage.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from engine import tiingo_news as tn
from engine import qbus_news_receipts as rights

UTC = timezone.utc
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)


def article(**overrides):
    row = {
        "id": 81234,
        "title": "Chipmaker reports strong new demand for next-generation memory",
        "url": "https://www.reuters.com/technology/memory-81234",
        "source": "reuters.com",
        "publishedDate": "2026-10-09T07:00:00Z",
        "crawlDate": "2026-10-09T07:10:00Z",
        "description": "Quarterly demand increased after a new product launch.",
        "tickers": ["MU", "MU", "AMD"],
        "tags": ["Earnings", "Semiconductors"],
    }
    row.update(overrides)
    return row


def receipt(**overrides):
    row = {
        "schema": "qbus.news_rights_receipt.v1",
        "status": "approved",
        "receipt_id": "test-owner-tiingo-r1",
        "owner_ref": "source-rights/verified-contract-id-test-only",
        "source": "tiingo",
        "product_id": "tiingo-business-news-explicit-contract-test",
        "audiences": ["site_full"],
        "effective_at": "2026-10-01T00:00:00+00:00",
        "expires_at": "2026-11-01T00:00:00+00:00",
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
    row.update(overrides)
    return row


def test_article_keeps_three_clock_domains_and_source_metadata():
    obs = tn.normalize_article(article(), received_at=NOW)
    assert obs["provider"] == "tiingo"
    assert obs["provider_id"] == 81234
    assert obs["published_at"] == "2026-10-09T07:00:00+00:00"
    assert obs["provider_crawled_at"] == "2026-10-09T07:10:00+00:00"
    assert obs["first_available_at"] == NOW.isoformat()
    assert obs["is_historical_backfill"] is False
    assert obs["publication_crawl_delay_seconds"] == 600
    assert obs["tickers"] == ["MU", "AMD"]


def test_backfill_and_future_crawl_never_backdate_local_availability():
    old = tn.normalize_article(article(), received_at=datetime(2026, 10, 11, tzinfo=UTC))
    assert old["is_historical_backfill"]
    assert old["first_available_at"] == "2026-10-11T00:00:00+00:00"
    future = tn.normalize_article(article(crawlDate="2026-10-10T07:10:00Z"), received_at=NOW)
    assert future["first_available_at"] == "2026-10-10T07:10:00+00:00"
    assert future["is_historical_backfill"] is False


@pytest.mark.parametrize("overrides", [
    {"id": True},
    {"id": ""},
    {"title": "   "},
    {"url": "file:///etc/passwd"},
    {"url": "https://user:pass@reuters.com/a"},
    {"source": "reuters.com/../../bad"},
    {"publishedDate": "2026-10-09T07:00:00"},
    {"crawlDate": "not-a-date"},
    {"publishedDate": "2026-10-10T07:00:00Z"},
    {"tickers": "MU"},
    {"tags": ["ok", 42]},
    {"description": "a" * (tn.MAX_DESCRIPTION + 1)},
])
def test_article_validation_drops_malformed_records(overrides):
    with pytest.raises(tn.TiingoArticleError):
        tn.normalize_article(article(**overrides), received_at=NOW)


def test_aware_received_at_required():
    with pytest.raises(tn.TiingoArticleError, match="received_at_invalid"):
        tn.normalize_article(article(), received_at=NOW.replace(tzinfo=None))


def test_fetch_uses_header_auth_and_sorted_bounded_payload():
    captured = {}
    class Response:
        status_code = 200
        def json(self):
            return [article()]
    def fake_get(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()
    rows, status = tn.fetch_articles("fake-token-test-only", limit=1, get=fake_get)
    assert status == "ok" and rows == [article()]
    assert captured["url"] == tn.ENDPOINT
    assert "fake-token" not in captured["url"]
    assert captured["headers"]["Authorization"] == "Token fake-token-test-only"
    assert captured["params"] == {"sortBy": "crawlDate", "limit": 1}
    assert captured["timeout"] <= 20


def test_fetch_unavailable_and_bad_response_fail_closed():
    assert tn.fetch_articles("")[1] == "no_key"
    assert tn.fetch_articles("stub", limit=0)[1] == "invalid_limit"
    class Response:
        status_code = 403
    assert tn.fetch_articles("stub", get=lambda *a, **kw: Response())[1] == "http_403"
    class Malformed:
        status_code = 200
        def json(self):
            return {"articles": []}
    assert tn.fetch_articles("stub", get=lambda *a, **kw: Malformed())[1] == "invalid_response"
    def failure(*args, **kwargs):
        raise RuntimeError("sensitive upstream request details")
    assert tn.fetch_articles("stub", get=failure)[1] == "request_failed"


def test_audit_records_bad_rows_without_article_text():
    bad = article(id=False)
    report = tn.audit_sample([article(), bad, article(id=81235, source="bloomberg.com")], received_at=NOW)
    assert report["sample_rows"] == 3
    assert report["valid_rows"] == 2
    assert report["invalid_reasons"]["id_invalid"] == 1
    assert report["unique_ids"] == 2
    assert report["ticker_tag_rate"] == 1
    assert report["description_rate"] == 1
    assert report["source_count"] == 2
    assert report["crawl_delay_minutes_p50"] == 10
    assert "Chipmaker" not in json.dumps(report)


def test_tiingo_rights_require_explicit_product_derivatives_and_audience():
    assert rights.parse_rights_receipt(receipt(), now=NOW, source="tiingo").source == "tiingo"
    assert rights.parse_rights_receipt(receipt(), now=NOW, source="tiingo").rights.allowed_sources == frozenset({"tiingo"})
    # Existing Benzinga call sites continue to assume Benzinga by default.
    with pytest.raises(rights.NewsReceiptError, match="rights_source"):
        rights.parse_rights_receipt(receipt(), now=NOW)
    caps = dict(receipt()["capabilities"], derivative_processing=False)
    with pytest.raises(rights.NewsReceiptError, match="derivative_processing"):
        rights.parse_rights_receipt(receipt(capabilities=caps), now=NOW, source="tiingo")
    with pytest.raises(rights.NewsReceiptError, match="rights_audience_not_permitted"):
        rights.parse_rights_receipt(receipt(audiences=["internal_only"]), now=NOW, source="tiingo")
    with pytest.raises(rights.NewsReceiptError):
        rights.parse_rights_receipt(receipt(), now=NOW, source="unlicensed_vendor")


def test_tiingo_file_loader_fails_closed_and_preserves_vendor_scope(tmp_path):
    path = tmp_path / "approved-test-only.json"
    path.write_text(json.dumps(receipt()))
    assert rights.load_rights_receipt(path, now=NOW) is None
    assert rights.load_rights_receipt(path, now=NOW, source="tiingo") is not None
    path.write_text(json.dumps(receipt(status="denied")))
    assert rights.load_rights_receipt(path, now=NOW, source="tiingo") is None


def test_financial_integration_disabled_by_default_and_no_side_effects(monkeypatch):
    from engine import financial_news as fin
    monkeypatch.setattr(fin.config, "secret", lambda name: None)
    monkeypatch.setattr(fin._tiingo_news_api, "fetch_articles", lambda *a, **kw: pytest.fail("disabled feed fetched"))
    monkeypatch.setattr(fin._qbus, "append_items", lambda *a, **kw: pytest.fail("disabled feed stored"))
    assert fin._tiingo_articles(NOW) == ([], "disabled", {})


def test_financial_integration_requires_rights_even_with_token(monkeypatch):
    from engine import financial_news as fin
    env = {"TIINGO_NEWS_ENABLED": "1", "TIINGO_NEWS_RIGHTS_FILE": "/no/approved/receipt",
           "TIINGO_API_KEY": "test-token"}
    monkeypatch.setattr(fin.config, "secret", lambda name: env.get(name))
    monkeypatch.setattr(fin._tiingo_news_api, "fetch_articles", lambda *a, **kw: pytest.fail("rights denied"))
    assert fin._tiingo_articles(NOW)[1] == "rights_denied"


def test_financial_integration_filters_sources_and_uses_single_qbus_batch(monkeypatch, tmp_path):
    from engine import financial_news as fin
    path = tmp_path / "tiingo-rights.json"
    path.write_text(json.dumps(receipt()))
    env = {"TIINGO_NEWS_ENABLED": "1", "TIINGO_NEWS_RIGHTS_FILE": str(path),
           "TIINGO_API_KEY": "test-token"}
    monkeypatch.setattr(fin.config, "secret", lambda name: env.get(name))
    raw = [
        article(),
        article(id=81235, source="random-unknown-domain.example", url="https://random-unknown-domain.example/article"),
        article(id=81236, tickers=[]),
    ]
    monkeypatch.setattr(fin._tiingo_news_api, "fetch_articles", lambda *a, **kw: (raw, "ok"))
    stored = []
    monkeypatch.setattr(fin._qbus, "append_items", lambda rows: stored.append(rows))
    items, state, audit = fin._tiingo_articles(NOW, _received_at=NOW)
    assert state == "ok" and len(items) == 1
    assert items[0]["provider_id"] == 81234
    assert items[0]["url"] == ""  # rights denied source-link display
    assert items[0]["summary"] == ""  # rights denied description/teaser display
    assert items[0]["first_available_at"] == NOW.isoformat()
    assert len(stored) == 1 and len(stored[0]) == 1  # no per-article Parquet rewrite
    assert stored[0][0]["_crawled_at"] == NOW.isoformat()
    assert audit["filtered_source"] == 1
    assert audit["filtered_untagged"] == 1
    assert audit["eligible_articles"] == 1


def test_rights_revoked_while_fetching_deny_commit(monkeypatch, tmp_path):
    from engine import financial_news as fin
    path = tmp_path / "test-rights.json"
    path.write_text(json.dumps(receipt()), encoding="utf-8")
    env = {"TIINGO_NEWS_ENABLED": "1", "TIINGO_NEWS_RIGHTS_FILE": str(path),
           "TIINGO_API_KEY": "test-token"}
    monkeypatch.setattr(fin.config, "secret", lambda name: env.get(name))

    def revoked_during_fetch(*a, **kw):
        path.write_text(json.dumps(receipt(status="denied")), encoding="utf-8")
        return [article()], "ok"

    monkeypatch.setattr(fin._tiingo_news_api, "fetch_articles", revoked_during_fetch)
    monkeypatch.setattr(fin._qbus, "append_items", lambda *a, **kw: pytest.fail("revoked feed stored"))
    assert fin._tiingo_articles(NOW, _received_at=NOW)[1] == "rights_changed"


def test_tiingo_stories_flow_into_ticker_index_without_changing_other_provider_schema(
    monkeypatch, tmp_path
):
    from engine import financial_news as fin
    from engine import news_common as nc
    monkeypatch.setattr(fin, "_cache_path", lambda day: tmp_path / "financial-news.json")
    monkeypatch.setattr(fin, "_cfg", lambda: {"enabled": True})
    monkeypatch.setattr(nc, "build_entity_map", lambda: {
        "tickers": {"MU": {"name": "Micron", "is_mag7": False}},
        "sectors": {},
        "baskets": {},
    })
    h = {
        "title": "Chipmaker reports strong new demand for next-generation memory",
        "url": "", "source": "reuters.com", "domain": "reuters.com",
        "seendate": NOW.isoformat(), "summary": "", "tickers": ["MU"],
        "sentiment": None, "tier": 1, "quality": 80,
        "_id": nc.event_id("Chipmaker reports strong new demand for next-generation memory", "reuters.com"),
        "provider": "tiingo", "data_attribution": "Data sourced by Tiingo",
    }
    monkeypatch.setattr(fin, "_tiingo_articles", lambda now: ([h], "ok", {"eligible_articles": 1}))
    monkeypatch.setattr(fin, "_polygon_news", lambda *a: ([], "no_key"))
    monkeypatch.setattr(fin, "_finnhub_news", lambda *a: ([], [], "no_key"))
    monkeypatch.setattr(fin, "_quiver_news", lambda *a: [])
    monkeypatch.setattr(fin, "_rss_news", lambda *a: {"market": [], "company": [], "sectors": {}})
    monkeypatch.setattr(fin, "_gdelt_thematic", lambda *a: {
        "market": [], "sectors": {}, "detail": "no_rows",
    })
    monkeypatch.setattr(fin._qbus, "read_items", lambda: None)
    result = fin.feed(today=NOW.date(), use_cache=False)
    assert result["schema"] == "financial_news.v1"
    assert "MU" in result["by_ticker"]
    assert result["by_ticker"]["MU"][0]["provider"] == "tiingo"
    assert result["providers_detail"]["tiingo"] == "ok"
    assert "tiingo" not in result["providers"]  # prior boolean schema intentionally preserved
    assert "Data sourced by Tiingo" in result["disclaimer"]
