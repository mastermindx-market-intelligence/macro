"""Provider contract regressions; fixtures are synthetic, no vendor credentials/network."""
import copy
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from engine import news_ai_feed as feed
from engine import news_common as nc

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)

def article(**changes):
    row = {"title": "Issuer reports quarterly results", "link": "https://www.reuters.com/example",
           "source": "www.reuters.com", "publishDate": "2026-09-24T11:30:00Z",
           "sentiment": "neutral", "confidence": "0.99", "companies": [
               {"ticker": "NVDA", "exchange": "XNAS", "confidence": "0.93"}]}
    row.update(changes)
    return row

@pytest.mark.parametrize("field", ["confidence", "relevance", "relevanceScore"])
def test_confidence_and_relevance_are_not_importance(field):
    assert feed._ai_importance({field: 0.99}) is None

@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -float("inf"), "NaN", "Infinity", -1, 101, [], {}])
def test_invalid_importance_is_missing_not_maximum(value):
    assert feed._ai_importance({"importance": value}) is None

@pytest.mark.parametrize("value,expected", [(0, 0), (0.6, 60), (1, 100), (40, 40), (100, 100), ("0.95",95)])
def test_explicit_importance_keeps_existing_scale(value, expected):
    assert feed._ai_importance({"importance": value, "confidence": 0.99}) == expected

def test_sentiment_confidence_preserved_without_priority_boost():
    a = feed._normalise_ai(article(confidence="0.10"), NOW)
    b = feed._normalise_ai(article(confidence="0.99"), NOW)
    assert a["ai_sentiment_confidence"] == 0.10
    assert b["ai_sentiment_confidence"] == 0.99
    assert a["ai_importance"] is None
    assert nc.rank_score(a,NOW) == nc.rank_score(b,NOW)

@pytest.mark.parametrize("value", [True, "NaN", "Infinity", -0.1, 1.01, [], {}])
def test_invalid_sentiment_confidence_is_null(value):
    assert feed._normalise_ai(article(confidence=value),NOW)["ai_sentiment_confidence"] is None

def test_provider_companies_flow_to_ticker_context_without_mutation():
    raw=article(); before=copy.deepcopy(raw)
    normalized=feed._normalise_ai(raw,NOW)
    assert normalized["tickers"] == ["NVDA"]
    assert raw == before

@pytest.mark.parametrize("venue", ["XLON", "XHKG", "ASX", "", None])
def test_foreign_or_unresolved_listing_never_aliases_us_ticker(venue):
    row=feed._normalise_ai(article(companies=[{"ticker":"ABC","exchange":venue,"country":"US"}]),NOW)
    assert row["tickers"] == []
    assert row["ai_ticker_exclusions"] == 1

def test_legacy_tickers_and_companies_share_existing_shape_gate():
    row=feed._normalise_ai(article(tickers=["aapl", "N/A", "ASX:PEX", "()", "AAPL"]),NOW)
    assert row["tickers"] == ["AAPL","NVDA"]
    assert row["ai_ticker_exclusions"] == 3

@pytest.mark.parametrize("stamp", [None, "", "not-a-date", float("nan"), float("inf"), True])
def test_missing_bad_publication_time_is_not_receipt_time(stamp):
    row=feed._normalise_ai(article(publishDate=stamp),NOW)
    assert row["seendate"] == ""
    assert row["_crawled_at"] == NOW.isoformat()
    assert row["timestamp_quality"] in ("CRAWL_BOUNDED","CORRUPTED")

def test_vendor_index_and_revision_clocks_do_not_replace_publication():
    row=feed._normalise_ai(article(publishDate="2026-09-20T10:00:00Z",
        createdAt="2026-09-24T11:00:00Z",revisedDate="2026-09-24T11:45:00Z"),NOW)
    assert row["seendate"] == "2026-09-20T10:00:00+00:00"
    assert row["provider_indexed_at"] == "2026-09-24T11:00:00+00:00"
    assert row["source_revised_at"] == "2026-09-24T11:45:00+00:00"
    assert row["timestamp_quality"] == "PUBLISHER_STATED"

@pytest.mark.parametrize("sentiment", [True, float("nan"), float("inf"), "not_positive", "unknown"])
def test_invalid_sentiment_is_unknown_not_direction(sentiment):
    assert feed._ai_sentiment({"sentiment":sentiment}) is None


def setup_http(monkeypatch, *, provider="finlight", rows=None, status=200, limit=50):
    calls=[]
    monkeypatch.setattr(feed,"_cfg",lambda:{"enabled":True,"provider":provider,"max_articles":limit})
    monkeypatch.setattr(feed,"_key",lambda cfg:"test-only-not-a-credential")
    def request(method, url, **kwargs):
        calls.append((method,url,kwargs))
        return SimpleNamespace(status_code=status,json=lambda:{"articles":rows if rows is not None else [article()]})
    monkeypatch.setitem(sys.modules,"requests",SimpleNamespace(
        post=lambda url,**kw:request("POST",url,**kw),get=lambda url,**kw:request("GET",url,**kw)))
    return calls


def test_documented_finlight_post_reaches_real_normalizer(monkeypatch):
    calls=setup_http(monkeypatch)
    rows=feed.fetch(now=NOW)
    assert len(calls)==1
    method,url,kw=calls[0]
    assert method=="POST"
    assert url=="https://api.finlight.me/v2/articles"
    assert kw["json"]["includeEntities"] is True
    assert kw["json"]["pageSize"]==50
    assert "params" not in kw
    assert rows[0]["tickers"]==["NVDA"]
    assert rows[0]["ai_importance"] is None


def test_custom_provider_preserves_legacy_transport(monkeypatch):
    calls=setup_http(monkeypatch,provider="custom")
    assert feed.fetch(now=NOW)
    assert calls[0][0]=="GET"

@pytest.mark.parametrize("limit,expected",[(1000,100),(2,2),(-1,1),("bad",50)])
def test_finlight_page_size_is_bounded(monkeypatch,limit,expected):
    calls=setup_http(monkeypatch,limit=limit)
    assert feed.fetch(now=NOW)
    assert calls[0][2]["json"]["pageSize"]==expected


def test_bad_row_does_not_erase_later_valid_row(monkeypatch):
    calls=setup_http(monkeypatch,rows=[{"title":{"bad":"not text"}},article(title="Issuer increases annual revenue guidance")])
    rows=feed.fetch(now=NOW)
    assert len(rows)==1
    assert rows[0]["tickers"]==["NVDA"]
    assert len(calls)==1


def test_denial_has_no_retry_or_fake_success(monkeypatch):
    calls=setup_http(monkeypatch,status=403)
    assert feed.fetch(now=NOW)==[]
    assert len(calls)==1


def test_disabled_has_zero_network(monkeypatch):
    calls=setup_http(monkeypatch)
    monkeypatch.setattr(feed,"_cfg",lambda:{"enabled":False})
    assert feed.fetch(now=NOW)==[]
    assert calls==[]


def test_real_news_ordering_cannot_be_lifted_by_confidence(monkeypatch):
    from scripts import build_news
    from engine import news_llm
    monkeypatch.setattr(news_llm,"annotate",lambda rows:None)
    monkeypatch.setattr(news_llm,"provider_label",lambda:"")
    first=feed._normalise_ai(article(title="First issuer reports quarterly results",confidence="0.1",companies=[]),NOW)
    second=feed._normalise_ai(article(title="Second issuer reports quarterly results",confidence="0.99",companies=[]),NOW)
    rows=[first,second]
    build_news._enrich([rows])
    assert rows[0] is first
    assert rows[0]["rank_score"] == rows[1]["rank_score"]


def test_missing_key_has_zero_network(monkeypatch):
    calls=setup_http(monkeypatch)
    monkeypatch.setattr(feed,"_key",lambda cfg:None)
    assert feed.fetch(now=NOW)==[]
    assert calls==[]


def test_importance_numeric_overflow_is_unknown():
    assert feed._ai_importance({"importance":10**10000}) is None


def test_companies_primary_listing_uses_listing_country_not_domicile():
    row=feed._normalise_ai(article(companies=[
        {"country":"CN","primaryListing":{"ticker":"LI","exchangeCode":"NASDAQ","exchangeCountry":"US"}},
        {"country":"US","primaryListing":{"ticker":"ABC","exchangeCode":"LSE","exchangeCountry":"GB"}}]),NOW)
    assert row["tickers"]==["LI"]
    assert row["ai_ticker_exclusions"]==1


def test_disabled_feed_does_not_resolve_credentials(monkeypatch):
    monkeypatch.setattr(feed,"_cfg",lambda:{"enabled":False})
    def forbidden(cfg):
        raise AssertionError("disabled connector must not resolve a key")
    monkeypatch.setattr(feed,"_key",forbidden)
    assert feed.fetch(now=NOW)==[]


def test_primary_listing_does_not_overwrite_explicit_foreign_venue():
    row=feed._normalise_ai(article(companies=[{"ticker":"ABC","exchange":"LSE",
        "primaryListing":{"ticker":"ABC","exchangeCode":"NASDAQ","exchangeCountry":"US"}}]),NOW)
    assert row["tickers"]==[]
    assert row["ai_ticker_exclusions"]==1


def test_provider_contract_is_in_existing_source_gated_collector_job():
    from pathlib import Path
    import yaml
    manifest=Path(__file__).resolve().parents[1]/".github/ci/legacy-jobs.yml"
    job=yaml.safe_load(manifest.read_text())["jobs"]["collector-registry"]
    assert job["gate"]=="code"
    assert any("tests/test_news_ai_feed_contract.py" in step.get("run","")
               for step in job["steps"])
