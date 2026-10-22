"""Tiingo provider contract, source-rights and News Intelligence wiring regression tests.

No external network, real credential, production receipts or live storage.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
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
    with pytest.raises(tn.TiingoArticleError, match="clock_after_receipt"):
        tn.normalize_article(article(crawlDate="2026-10-10T07:10:00Z"), received_at=NOW)


@pytest.mark.parametrize("overrides", [
    {"id": True},
    {"id": ""},
    {"title": "   "},
    {"url": "file:///etc/passwd"},
    {"url": "https://user:pass@reuters.com/a"},
    {"url": "https://reuters.com/article?q=\u0022onclick"},
    {"source": "reuters.com<svg>"},
    {"source": "reuters.com/../../bad"},
    {"source": "bloomberg.com"},  # source-host disagreement cannot borrow credibility
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
        headers = {"Content-Type": "application/json; charset=utf-8"}
        closed = False
        def iter_content(self, chunk_size):
            yield json.dumps([article()]).encode()
        def close(self):
            self.closed = True
    def fake_get(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()
    rows, status = tn.fetch_articles("fake-token-test-only", limit=1, get=fake_get)
    assert status == "ok" and rows == [article()]
    assert captured["url"] == tn.ENDPOINT
    assert "fake-token" not in captured["url"]
    assert captured["headers"]["Authorization"] == "Token fake-token-test-only"
    assert captured["params"] == {
        "sortBy": "crawlDate", "limit": 1, "onlyWithTickers": "true"
    }
    assert captured["timeout"] == (5, 15)
    assert captured["allow_redirects"] is False
    assert captured["stream"] is True


def test_explicit_unfiltered_quality_sample_preserves_one_bounded_request():
    calls = []
    class Response:
        status_code = 200
        headers = {"Content-Type": "application/json"}
        closed = False
        def iter_content(self, chunk_size):
            yield b"[]"
        def close(self):
            self.closed = True

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    rows, state = tn.fetch_articles(
        "stub-test-only", limit=7, only_with_tickers=False, get=fake_get
    )
    assert rows == [] and state == "no_rows"
    assert len(calls) == 1
    assert calls[0][0] == tn.ENDPOINT
    assert calls[0][1]["params"] == {"sortBy": "crawlDate", "limit": 7}
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["stream"] is True


def test_non_boolean_news_ticker_filter_is_refused_before_network():
    def unexpected_request(*args, **kwargs):
        pytest.fail("invalid flag must not contact vendor")
    for invalid in ("true", 1, None, [], {}):
        rows, state = tn.fetch_articles(
            "stub-test-only", only_with_tickers=invalid, get=unexpected_request
        )
        assert rows == [] and state == "invalid_ticker_filter"


def test_fetch_unavailable_and_bad_response_fail_closed():
    assert tn.fetch_articles("")[1] == "no_key"
    assert tn.fetch_articles("stub", limit=0)[1] == "invalid_limit"
    class Response:
        status_code = 403
    assert tn.fetch_articles("stub", get=lambda *a, **kw: Response())[1] == "http_403"
    class Malformed:
        status_code = 200
        headers = {"Content-Type": "application/json"}
        def iter_content(self, chunk_size):
            yield b'{"articles": []}'
        def close(self):
            pass
    assert tn.fetch_articles("stub", get=lambda *a, **kw: Malformed())[1] == "invalid_response"
    def failure(*args, **kwargs):
        raise RuntimeError("sensitive upstream request details")
    assert tn.fetch_articles("stub", get=failure)[1] == "request_failed"


def test_audit_records_bad_rows_without_article_text():
    bad = article(id=False)
    report = tn.audit_sample([article(), bad, article(id=81235, source="bloomberg.com", url="https://bloomberg.com/story/81235")], received_at=NOW)
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
    # Tiingo still requires explicit qualification; incumbent source rules stay intact.
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
        article(id=81237, source="fakebloomberg.com", url="https://fakebloomberg.com/a"),
    ]
    monkeypatch.setattr(fin._tiingo_news_api, "fetch_articles", lambda *a, **kw: (raw, "ok"))
    stored = []
    import pandas as pd
    monkeypatch.setattr(fin.nc, "build_entity_map", lambda: {"tickers": {"MU": {}, "AMD": {}}})
    monkeypatch.setattr(fin._qbus, "append_items", lambda rows: (stored.append(rows), pd.DataFrame(rows))[1])
    items, state, audit = fin._tiingo_articles(NOW, _received_at=NOW)
    assert state == "ok" and len(items) == 1
    assert items[0]["provider_id"] == 81234
    assert items[0]["url"] == ""  # rights denied source-link display
    assert items[0]["summary"] == ""  # rights denied description/teaser display
    assert items[0]["first_available_at"] == NOW.isoformat()
    assert len(stored) == 1 and len(stored[0]) == 1  # no per-article Parquet rewrite
    assert stored[0][0]["_crawled_at"] == NOW.isoformat()
    assert audit["filtered_source"] == 2
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
    grant = rights.parse_rights_receipt(receipt(), now=NOW, source="tiingo")
    monkeypatch.setattr(fin, "_current_tiingo_context", lambda now: ("synthetic-section-test", grant))
    monkeypatch.setattr(fin, "_tiingo_articles", lambda now, **kw: ([h], "ok", {"eligible_articles": 1}))
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


@pytest.mark.parametrize("url", [
    "https://[broken/story", "https://reuters.com:invalid/story",
    "https://reuters.com:444/story", "https://reuters.com/a\\b",
    "https://reuters.com/a\nmore", "https://reuters.com/a\x7fmore",
])
def test_malformed_url_has_stable_refusal_not_an_uncaught_parser_error(url):
    with pytest.raises(tn.TiingoArticleError, match="url_invalid"):
        tn.normalize_article(article(url=url), received_at=NOW)


@pytest.mark.parametrize("received", [None, "2026-10-09", 0, False])
def test_non_datetime_receipt_is_rejected(received):
    with pytest.raises(tn.TiingoArticleError, match="received_at_invalid"):
        tn.normalize_article(article(), received_at=received)


@pytest.mark.parametrize("field", ["publishedDate", "crawlDate"])
def test_future_provider_clock_is_quarantined(field):
    with pytest.raises(tn.TiingoArticleError, match="clock_after_receipt"):
        tn.normalize_article(article(**{field: "2026-10-09T08:00:01Z"}), received_at=NOW)


def test_publication_fallback_and_delay_are_not_misrepresented_as_sla():
    obs = tn.normalize_article(article(), received_at=NOW)
    report = tn.audit_sample([article()], received_at=NOW)
    assert obs["publication_time_basis"] == "publisher_or_tiingo_discovery_fallback"
    assert obs["available_at"] == NOW.isoformat()
    assert report["editorial_accuracy"] == "not_measured"
    assert report["entity_precision"] == "not_measured"
    assert report["historical_completeness"] == "not_measured"


def test_provider_tags_resolve_only_unique_existing_universe_keys():
    universe = {"AAPL": {}, "MU": {}, "BRK-B": {}, "TPC": {}, "TpC": {}}
    resolution = tn.resolve_ticker_candidates(["aapl", "mu", "brk.b", "tpc", "unlisted"], universe)
    assert resolution["tickers"] == ["AAPL", "BRK-B", "MU"]
    assert resolution["ambiguous"] == ["tpc"]
    assert resolution["unresolved"] == ["unlisted"]
    assert "TPC" not in resolution["tickers"]
    assert universe == {"AAPL": {}, "MU": {}, "BRK-B": {}, "TPC": {}, "TpC": {}}


class _StreamResponse:
    def __init__(self, payload=b"[]", status=200, media="application/json"):
        self.payload = payload
        self.status_code = status
        self.headers = {"Content-Type": media}
        self.closed = False
    def iter_content(self, chunk_size):
        yield self.payload
    def close(self):
        self.closed = True


def test_historical_window_audit_refuses_valid_200_rows_outside_requested_dates():
    good = article(id=91001)
    old = article(
        id=91002, publishedDate="2026-07-18T08:00:00Z",
        crawlDate="2026-07-18T08:10:00Z",
    )
    result = tn.audit_requested_publication_window(
        [good, old], start_date=date(2026, 10, 9),
        end_date=date(2026, 10, 10), received_at=NOW,
    )
    assert result == {
        "sample_rows": 2,
        "within_window_rows": 1,
        "before_window_rows": 1,
        "after_window_rows": 0,
        "invalid_rows": 0,
        "window_status": "publication_dates_outside_requested_window",
        "no_out_of_window_or_malformed_rows": False,
        "historical_availability": "not_proven",
        "publication_clock_basis": "publisher_or_tiingo_discovery_fallback",
        "only_validates_requested_publication_date_bounds": True,
    }
    assert "Chipmaker" not in json.dumps(result)
    assert "reuters" not in json.dumps(result)
    assert "91002" not in json.dumps(result)


def test_historical_window_audit_accepts_bounds_without_claiming_completeness():
    result = tn.audit_requested_publication_window(
        [article(id=91003)], start_date=date(2026, 10, 9),
        end_date=date(2026, 10, 9), received_at=NOW,
    )
    assert result["within_window_rows"] == 1
    assert result["window_status"] == "published_date_window_observed"
    assert result["no_out_of_window_or_malformed_rows"] is True
    assert result["historical_availability"] == "not_proven"


def test_historical_window_audit_rejects_malformed_empty_and_future_windows():
    kwargs = dict(start_date=date(2026, 10, 9),
                  end_date=date(2026, 10, 9), received_at=NOW)
    bad = tn.audit_requested_publication_window(
        [article(id=False)], **kwargs
    )
    assert bad["window_status"] == "malformed_vendor_row"
    assert bad["invalid_rows"] == 1
    assert not bad["no_out_of_window_or_malformed_rows"]

    empty = tn.audit_requested_publication_window([], **kwargs)
    assert empty["window_status"] == "empty_response"
    assert not empty["no_out_of_window_or_malformed_rows"]

    future = tn.audit_requested_publication_window(
        [article()], start_date=date(2026, 10, 8),
        end_date=date(2026, 10, 8), received_at=NOW
    )
    assert future["after_window_rows"] == 1
    assert future["window_status"] == "publication_dates_outside_requested_window"
    assert not future["no_out_of_window_or_malformed_rows"]


@pytest.mark.parametrize("invalid_start,invalid_end", [
    ("2026-10-09", date(2026, 10, 10)),
    (date(2026, 10, 9), datetime(2026, 10, 10, tzinfo=UTC)),
    (date(2026, 10, 10), date(2026, 10, 9)),
])
def test_historical_window_audit_refuses_invalid_bounds(invalid_start, invalid_end):
    with pytest.raises(ValueError, match="publication_window_invalid"):
        tn.audit_requested_publication_window(
            [], start_date=invalid_start, end_date=invalid_end, received_at=NOW
        )
    with pytest.raises(ValueError, match="publication_window_invalid"):
        tn.audit_requested_publication_window(
            (), start_date=date(2026, 10, 9),
            end_date=date(2026, 10, 9), received_at=NOW,
        )


def test_aggregate_ticker_coverage_is_case_safe_and_no_raw_content_is_reported():
    universe = {"MU": {}, "TPC": {}, "TpC": {}, "AAPL": {}}
    rows = [
        article(id=91101, tickers=["mu"]),
        article(id=91102, tickers=["tpc"]),
        article(id=91103, tickers=["AAPL"]),
        article(id=91104, tickers=["UNKNOWN-CANDIDATE"]),
        article(id=91105, tickers=[]),
        article(id=91106, tickers=["mu", "tpc", "UNKNOWN-CANDIDATE"]),
        article(id=91107, tickers=["AAPL", "mu"]),
        article(id=False, tickers=["MU"]),
    ]
    audit = tn.audit_ticker_coverage(rows, universe, received_at=NOW)
    assert audit == {
        "sample_rows": 8,
        "valid_rows": 7,
        "ticker_tagged_rows": 6,
        "unique_canonical_match_rows": 4,
        "ambiguous_ticker_rows": 2,
        "unresolved_ticker_rows": 2,
        "matched_canonical_symbol_count": 2,
        "case_stranded_matched_rows": 3,
        "no_unique_match_rows": 2,
        "diagnostic_basis": "caller_universe_display_candidate_not_identity_grant",
    }
    assert "UNKNOWN-CANDIDATE" not in json.dumps(audit)
    assert "Chipmaker" not in json.dumps(audit)
    assert "reuters" not in json.dumps(audit)


def test_ticker_audit_builds_one_universe_index_per_sample(monkeypatch):
    build = tn._ticker_lookup_index
    calls = []

    def indexed_once(universe):
        calls.append(1)
        return build(universe)

    monkeypatch.setattr(tn, "_ticker_lookup_index", indexed_once)
    rows = [article(id=92000 + i, tickers=["mu"]) for i in range(20)]
    stats = tn.audit_ticker_coverage(rows, {"MU": {}}, received_at=NOW)
    assert stats["unique_canonical_match_rows"] == 20
    assert stats["case_stranded_matched_rows"] == 20
    assert calls == [1]


def test_empty_ticker_universe_does_not_invent_security_identities():
    report = tn.audit_ticker_coverage(
        [article(id=91201, tickers=["mu"])], {}, received_at=NOW
    )
    assert report["unique_canonical_match_rows"] == 0
    assert report["unresolved_ticker_rows"] == 1
    assert report["no_unique_match_rows"] == 1
    with pytest.raises(ValueError, match="ticker_universe_invalid"):
        tn.audit_ticker_coverage([], None, received_at=NOW)


@pytest.mark.parametrize("status", [301, 302, 401, 403, 429, 500])
def test_http_errors_and_redirects_make_one_request_and_close(status):
    response = _StreamResponse(status=status)
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return response
    assert tn.fetch_articles("fixture-token", get=get) == ([], f"http_{status}")
    assert len(calls) == 1
    assert calls[0][1]["allow_redirects"] is False
    assert response.closed


def test_response_byte_budget_is_enforced_and_response_closed(monkeypatch):
    monkeypatch.setattr(tn, "MAX_RESPONSE_BYTES", 10)
    response = _StreamResponse(b" " * 11)
    assert tn.fetch_articles("fixture-token", get=lambda *a, **kw: response) == ([], "response_too_large")
    assert response.closed


def test_response_deadline_is_enforced_and_response_closed(monkeypatch):
    clock = iter([0, 21])
    monkeypatch.setattr(tn, "monotonic", lambda: next(clock))
    response = _StreamResponse()
    assert tn.fetch_articles("fixture-token", get=lambda *a, **kw: response) == ([], "response_deadline")
    assert response.closed


@pytest.mark.parametrize("payload,media,expected", [
    (b"<html>login</html>", "text/html", "invalid_content_type"),
    (b"{}", "application/json", "invalid_response"),
    (b"[{},{}]", "application/json", "invalid_response"),
    (b"not-json", "application/json", "request_failed"),
])
def test_unusable_response_cannot_be_a_success(payload, media, expected):
    response = _StreamResponse(payload, media=media)
    assert tn.fetch_articles("fixture-token", limit=1, get=lambda *a, **kw: response) == ([], expected)
    assert response.closed


def test_tiingo_only_model_batch_never_acquires_a_provider(monkeypatch):
    from engine import news_llm
    row = {"provider": "tiingo", "title": "Example headline", "summary": ""}
    payload = [row]
    monkeypatch.setattr(news_llm, "_cfg", lambda: pytest.fail("model configuration accessed"))
    assert news_llm.annotate(payload) is payload
    assert row == {"provider": "tiingo", "title": "Example headline", "summary": ""}


def test_model_enrichment_cannot_copy_a_duplicate_into_tiingo(monkeypatch):
    from engine import news_llm
    from scripts import build_news
    tiingo = {"provider": "tiingo", "title": "Same headline", "domain": "reuters.com", "summary": ""}
    legacy = {"provider": "polygon", "title": "Same headline", "domain": "reuters.com", "summary": ""}
    calls = []
    def annotate(rows):
        calls.append(list(rows))
        assert all(row.get("provider") != "tiingo" for row in rows)
        for row in rows:
            row.update(summary="Fixture model summary", llm_importance=40)
        return rows
    monkeypatch.setattr(news_llm, "annotate", annotate)
    monkeypatch.setattr(news_llm, "provider_label", lambda: "fixture")
    monkeypatch.setattr(build_news.nc, "rank_score", lambda row, now: 1)
    build_news._enrich([[legacy, tiingo]])
    assert len(calls) == 1 and calls[0] == [legacy]
    assert legacy["summary"] == "Fixture model summary"
    assert tiingo["summary"] == ""
    assert "llm_importance" not in tiingo


def test_tiingo_only_build_enrichment_never_selects_model_credentials(monkeypatch):
    from engine import news_llm
    from scripts import build_news
    row = {"provider": "tiingo", "title": "Example headline", "summary": ""}
    monkeypatch.setattr(news_llm, "provider_label", lambda: pytest.fail("provider selected"))
    monkeypatch.setattr(build_news.nc, "rank_score", lambda row, now: 1)
    assert build_news._enrich([[row]]) == ""
    assert row["summary"] == ""


def test_compact_ticker_output_preserves_tiingo_lineage_without_claiming_first_seen(monkeypatch):
    from engine import financial_news as fin
    monkeypatch.setattr(fin.nc, "build_entity_map", lambda: {"tickers": {"MU": {}}})
    row = {
        "provider": "tiingo", "provider_id": 81234,
        "title": "Fixture headline", "url": "", "source": "reuters.com",
        "seendate": "2026-10-09T07:00:00Z", "summary": "",
        "provider_crawled_at": "2026-10-09T07:10:00+00:00",
        "first_available_at": NOW.isoformat(),
        "model_processing_allowed": True,
        "private_account_detail": "must-not-be-projected",
    }
    result = fin.mastermind_by_ticker({"by_ticker": {"MU": [row]}})["MU"]["top"][0]
    assert result["provider"] == "tiingo" and result["provider_id"] == 81234
    assert result["observation_received_at"] == NOW.isoformat()
    assert result["provider_crawled_at"] == row["provider_crawled_at"]
    assert result["publication_time_basis"] == tn.PUBLICATION_TIME_BASIS
    assert result["model_processing_allowed"] is False
    assert result["data_attribution"] == "Data sourced by Tiingo"
    assert "first_available_at" not in result
    assert "private_account_detail" not in result


def test_other_providers_keep_the_existing_compact_row_shape(monkeypatch):
    from engine import financial_news as fin
    monkeypatch.setattr(fin.nc, "build_entity_map", lambda: {"tickers": {"MU": {}}})
    row = {"provider": "polygon", "title": "Fixture legacy headline", "url": "u",
           "source": "Reuters", "seendate": "date", "summary": "summary"}
    result = fin.mastermind_by_ticker({"by_ticker": {"MU": [row]}})["MU"]["top"][0]
    assert set(result) == {"title", "url", "source", "published", "sentiment", "summary"}


def test_quality_snapshot_separates_provider_age_from_publication_lag():
    # One bounded observation only; repeat IDs/URLs are audit evidence, not
    # proof that the underlying publisher published multiple distinct stories.
    rows = [
        article(id=81, url="https://reuters.com/a"),
        article(id=81, url="https://reuters.com/a",
                publishedDate="2026-10-09T05:50:00Z", crawlDate="2026-10-09T06:00:00Z"),
        article(id=82, url="https://reuters.com/b",
                publishedDate="2026-10-09T03:50:00Z", crawlDate="2026-10-09T04:00:00Z"),
    ]
    report = tn.audit_sample(rows, received_at=NOW)
    assert report["valid_rows"] == 3
    assert report["duplicate_provider_id_rows"] == 1
    assert report["duplicate_url_rows"] == 1
    assert report["provider_crawl_to_observation_minutes_p50"] == 120.0
    assert report["observed_within_60m_of_provider_crawl_share"] == 0.3333
    assert report["reported_publication_to_crawl_minutes_p50"] == 10.0
    assert report["largest_source_share"] == 1.0
    assert report["apparent_age_scope"] == "one_observation_slice_not_provider_sla"
    assert "Chipmaker" not in json.dumps(report)
    assert "/reuters.com/a" not in json.dumps(report)


def test_quality_snapshot_empty_or_rejected_data_has_no_apparent_age_estimate():
    report = tn.audit_sample([article(id=True)], received_at=NOW)
    assert report["valid_rows"] == 0
    assert report["provider_crawl_to_observation_minutes_p50"] is None
    assert report["observed_within_60m_of_provider_crawl_share"] is None
    assert report["duplicate_provider_id_rows"] == 0
    assert report["largest_source_share"] is None


# Withdrawal regressions exercise the existing collector/cache/static artifacts.
# Every provider call and state path below is synthetic and isolated.
@pytest.fixture
def tiingo_runtime(monkeypatch, tmp_path):
    from datetime import timedelta
    import pandas as pd
    from engine import financial_news as fin
    now = datetime.now(UTC)
    grant = receipt(
        effective_at=(now - timedelta(days=1)).isoformat(),
        expires_at=(now + timedelta(days=1)).isoformat(),
    )
    path = tmp_path / "synthetic-tiingo-rights.json"
    path.write_text(json.dumps(grant))
    env = {"TIINGO_NEWS_ENABLED": "1", "TIINGO_NEWS_RIGHTS_FILE": str(path),
           "TIINGO_API_KEY": "synthetic-not-a-credential"}
    monkeypatch.setattr(fin.config, "secret", lambda key: env.get(key))
    monkeypatch.setattr(fin.config, "ROOT", tmp_path)
    monkeypatch.setattr(fin.config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(fin, "_cfg", lambda: {"enabled": True})
    monkeypatch.setattr(fin, "_cache_path", lambda day: tmp_path / "feed.json")
    universe = {
        "tickers": {t: {"name": t} for t in ("MU", "AMD", "MSFT", "SPY", "JPM", "BRK-B", "TPC", "TpC")},
        "sectors": {"XLK": {"tickers": ["MU", "MSFT"]}},
        "baskets": {"memory": {"tickers": ["MU", "MSFT"], "name": "Memory"}},
    }
    monkeypatch.setattr(fin.nc, "build_entity_map", lambda: universe)
    raw = [article(
        publishedDate=(now - timedelta(hours=1)).isoformat(),
        crawlDate=(now - timedelta(minutes=30)).isoformat(),
        tickers=["MU", "MSFT", "SPY"],
    )]
    calls = []
    def fetch(*args, **kwargs):
        calls.append("fetch")
        return raw, "ok"
    monkeypatch.setattr(fin._tiingo_news_api, "fetch_articles", fetch)
    real_append, real_read = fin._qbus.append_items, fin._qbus.read_items
    monkeypatch.setattr(fin._qbus, "append_items", lambda rows: pd.DataFrame(rows))
    monkeypatch.setattr(fin._qbus, "read_items", lambda: None)
    other = {
        "title": "Bank reports quarterly capital and operating results",
        "url": "https://reuters.com/test-other", "source": "reuters.com",
        "domain": "reuters.com", "seendate": now.isoformat(), "summary": "",
        "tickers": ["JPM"], "tier": 1, "quality": 70, "sentiment": None, "_id": "other",
    }
    monkeypatch.setattr(fin, "_polygon_news", lambda *a: ([dict(other)], "ok"))
    monkeypatch.setattr(fin, "_finnhub_news", lambda *a: ([], [], "no_key"))
    monkeypatch.setattr(fin, "_quiver_news", lambda *a: [])
    monkeypatch.setattr(fin, "_rss_news", lambda *a: {"market": [], "company": [], "sectors": {}})
    monkeypatch.setattr(fin, "_gdelt_thematic", lambda *a: {"market": [], "sectors": {}, "detail": "no_rows"})
    return {"fin": fin, "now": now, "path": path, "env": env, "grant": grant,
            "raw": raw, "calls": calls, "root": tmp_path,
            "real_append": real_append, "real_read": real_read}


def _change_tiingo_context(ctx, change):
    from datetime import timedelta
    grant = json.loads(ctx["path"].read_text())
    if change == "disabled":
        ctx["env"]["TIINGO_NEWS_ENABLED"] = "0"
    elif change == "path":
        alternate = ctx["root"] / "same-grant-new-path.json"
        alternate.write_text(json.dumps(grant))
        ctx["env"]["TIINGO_NEWS_RIGHTS_FILE"] = str(alternate)
    elif change == "denied":
        grant["status"] = "denied"
    elif change == "expired":
        grant["expires_at"] = (ctx["now"] - timedelta(seconds=1)).isoformat()
    elif change in ("source_link_display", "teaser_display"):
        grant["capabilities"][change] = True
    elif change == "derivative_processing":
        grant["capabilities"][change] = False
    elif change in ("owner_ref", "product_id"):
        grant[change] += "-changed"
    else:
        raise AssertionError(change)
    ctx["path"].write_text(json.dumps(grant))


@pytest.mark.parametrize("failure", ["none", "exception"])
def test_withdrawal_persistence_failure_cannot_return_display_success(tiingo_runtime, monkeypatch, failure):
    ctx = tiingo_runtime
    def append(rows):
        if failure == "exception":
            raise OSError("synthetic persistence failure")
        return None
    monkeypatch.setattr(ctx["fin"]._qbus, "append_items", append)
    rows, state, audit = ctx["fin"]._tiingo_articles(ctx["now"], _received_at=ctx["now"])
    assert rows == []
    assert state == "persistence_failed"
    assert audit["eligible_articles"] == 0
    assert not (ctx["root"] / "data" / "qbus" / "items.parquet").exists()


def test_withdrawal_real_persistence_preserves_first_receipt_and_honest_clocks(tiingo_runtime, monkeypatch):
    from datetime import timedelta
    import pandas as pd
    ctx = tiingo_runtime
    monkeypatch.setattr(ctx["fin"]._qbus, "append_items", ctx["real_append"])
    monkeypatch.setattr(ctx["fin"]._qbus, "read_items", ctx["real_read"])
    rows, state, audit = ctx["fin"]._tiingo_articles(ctx["now"], _received_at=ctx["now"])
    assert state == "ok" and audit["eligible_articles"] == 1
    assert rows[0]["publication_time_basis"] == tn.PUBLICATION_TIME_BASIS
    assert rows[0]["provider_crawled_at"] != rows[0]["observation_received_at"]
    later = ctx["now"] + timedelta(minutes=15)
    assert ctx["fin"]._tiingo_articles(later, _received_at=later)[1] == "ok"
    stored = ctx["real_read"]()
    assert len(stored) == 1
    assert stored.iloc[0]["timestamp_quality"] == "CRAWL_BOUNDED"
    assert pd.to_datetime(stored.iloc[0]["_crawled_at"], utc=True) == pd.Timestamp(ctx["now"])


@pytest.mark.parametrize("change", [
    "disabled", "path", "denied", "expired", "source_link_display",
    "teaser_display", "derivative_processing", "owner_ref", "product_id",
])
def test_withdrawal_whole_context_change_during_fetch_prevents_append(tiingo_runtime, monkeypatch, change):
    ctx = tiingo_runtime
    def fetch(*args, **kwargs):
        _change_tiingo_context(ctx, change)
        return ctx["raw"], "ok"
    monkeypatch.setattr(ctx["fin"]._tiingo_news_api, "fetch_articles", fetch)
    monkeypatch.setattr(ctx["fin"]._qbus, "append_items", lambda rows: pytest.fail("changed grant appended"))
    rows, state, _ = ctx["fin"]._tiingo_articles(ctx["now"], _received_at=ctx["now"])
    assert rows == [] and state == "rights_changed"


def test_withdrawal_nested_source_fields_change_is_not_hidden_by_same_receipt_id(tiingo_runtime, monkeypatch):
    from dataclasses import replace
    from engine.qbus_news_store import SourceReadRights
    ctx = tiingo_runtime
    grant = rights.parse_rights_receipt(ctx["grant"], now=ctx["now"], source="tiingo")
    current = [grant]
    monkeypatch.setattr(rights, "load_rights_receipt", lambda *a, **kw: current[0])
    def fetch(*args, **kwargs):
        current[0] = replace(grant, rights=replace(
            grant.rights, source_fields=(SourceReadRights("tiingo", True, False, False),)
        ))
        return ctx["raw"], "ok"
    monkeypatch.setattr(ctx["fin"]._tiingo_news_api, "fetch_articles", fetch)
    monkeypatch.setattr(ctx["fin"]._qbus, "append_items", lambda rows: pytest.fail("nested grant change appended"))
    assert ctx["fin"]._tiingo_articles(ctx["now"], _received_at=ctx["now"])[1] == "rights_changed"


@pytest.mark.parametrize("boundary", ["normalization", "append"])
def test_withdrawal_rechecks_after_normalization_and_persistence(tiingo_runtime, monkeypatch, boundary):
    import pandas as pd
    ctx = tiingo_runtime
    if boundary == "normalization":
        original = ctx["fin"]._normalise
        def normalize(*args, **kwargs):
            row = original(*args, **kwargs)
            _change_tiingo_context(ctx, "disabled")
            return row
        monkeypatch.setattr(ctx["fin"], "_normalise", normalize)
        monkeypatch.setattr(ctx["fin"]._qbus, "append_items", lambda rows: pytest.fail("revoked before append"))
    else:
        def append(rows):
            _change_tiingo_context(ctx, "disabled")
            return pd.DataFrame(rows)
        monkeypatch.setattr(ctx["fin"]._qbus, "append_items", append)
    rows, state, audit = ctx["fin"]._tiingo_articles(ctx["now"], _received_at=ctx["now"])
    assert rows == [] and state == "rights_changed"
    assert audit["eligible_articles"] == 0


def test_withdrawal_real_collector_routes_unique_lowercase_tags_only(tiingo_runtime):
    ctx = tiingo_runtime
    ctx["raw"][0]["tickers"] = ["mu", "brk.b", "tpc", "unknown"]
    rows, state, audit = ctx["fin"]._tiingo_articles(ctx["now"], _received_at=ctx["now"])
    assert state == "ok"
    assert rows[0]["tickers"] == ["BRK-B", "MU"]
    assert audit["ambiguous_ticker_tags"] == 1
    assert audit["unresolved_ticker_tags"] == 1


def _without_observation_clock(value):
    # Separate builds necessarily have different local receipt instants.
    if isinstance(value, dict):
        return {k: _without_observation_clock(v) for k, v in value.items()
                if k not in ("first_available_at", "observation_received_at")}
    if isinstance(value, list):
        return [_without_observation_clock(v) for v in value]
    return value


def _assert_no_tiingo_material(snapshot):
    def walk(value):
        if isinstance(value, dict):
            assert value.get("provider") != "tiingo"
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)
    walk(snapshot)
    assert "Data sourced by Tiingo" not in json.dumps(snapshot)
    assert "Chipmaker reports strong" not in json.dumps(snapshot)


@pytest.mark.parametrize("change", [
    "disabled", "denied", "expired", "source_link_display",
    "teaser_display", "derivative_processing", "owner_ref", "product_id", "legacy",
])
def test_withdrawal_fresh_cache_rebuilds_all_sections_and_counts(tiingo_runtime, change):
    ctx = tiingo_runtime
    before = ctx["fin"].feed(use_cache=False)
    assert before["market"] and before["sectors"]["XLK"]["headlines"]
    assert before["mag7"]["MSFT"]["headlines"] and before["baskets"]["memory"]["headlines"]
    assert "MU" in before["by_ticker"]
    if change == "legacy":
        before.pop("tiingo_binding", None)
        before["rejected"] = [{"title": "Old unmarked Tiingo rejection", "domain": "cnbc.com"}]
        (ctx["root"] / "feed.json").write_text(json.dumps(before))
        _change_tiingo_context(ctx, "disabled")
    else:
        _change_tiingo_context(ctx, change)
    # A changed-but-still-valid grant must rebuild, not relabel cached rows.
    previous_fetches = len(ctx["calls"])
    after = ctx["fin"].feed()
    baseline = ctx["fin"].feed(use_cache=False)
    for key in ("market", "sectors", "mag7", "baskets", "by_ticker", "sources", "counts", "rejected", "disclaimer"):
        assert _without_observation_clock(after[key]) == _without_observation_clock(baseline[key])
    if change in ("source_link_display", "teaser_display", "owner_ref", "product_id"):
        assert len(ctx["calls"]) == previous_fetches + 2
        assert after["tiingo_binding"] != before["tiingo_binding"]
    else:
        _assert_no_tiingo_material(after)
        assert after["counts"] == {"raw": 1, "tagged": 1, "tickers_covered": 1, "tickers_excluded": 0}
    assert "Old unmarked Tiingo rejection" not in json.dumps(after)


def test_withdrawal_unchanged_bound_cache_never_refetches_or_appends(tiingo_runtime, monkeypatch):
    ctx = tiingo_runtime
    before = ctx["fin"].feed(use_cache=False)
    monkeypatch.setattr(ctx["fin"]._tiingo_news_api, "fetch_articles", lambda *a, **kw: pytest.fail("cache refetched"))
    monkeypatch.setattr(ctx["fin"]._qbus, "append_items", lambda *a, **kw: pytest.fail("cache appended"))
    assert ctx["fin"].feed() == before


def test_withdrawal_rejected_tiingo_titles_are_not_exported(tiingo_runtime, monkeypatch):
    ctx = tiingo_runtime
    title = ctx["raw"][0]["title"]
    monkeypatch.setattr(ctx["fin"].nc, "low_value_reason", lambda t, d: "synthetic_preview" if t == title else None)
    result = ctx["fin"].feed(use_cache=False)
    assert title not in json.dumps(result)
    assert result["tiingo_quality_sample"]["filtered_quality"] == 1


def _static_builder(ctx, monkeypatch, candidate):
    import sys
    import types
    import engine
    from scripts import build_news as build
    modules = {
        "macro_news": dict(macro_headlines=lambda: None, upcoming_catalysts=lambda **kw: [],
                           DISCLAIMER_TEXT="", DISCLAIMER_TEXT_ZH="", THEME_LABEL={}),
        "news_rss": dict(start_reject_log=lambda: ([], None), stop_reject_log=lambda token: None),
        "news_ai_feed": dict(enabled=lambda: False),
        "china_news": dict(panel=lambda: None),
        "news_vector": dict(enabled=lambda: False, recent_panel=lambda: None),
        "macro_surprise": dict(build_release_cards=lambda **kw: None),
        "news_event_ledger": dict(persist_kept_events=lambda *a, **kw: 0,
                                 persist_reject_sample=lambda *a, **kw: 0),
    }
    for name, members in modules.items():
        module = types.ModuleType("engine." + name)
        module.__dict__.update(members)
        monkeypatch.setitem(sys.modules, "engine." + name, module)
        monkeypatch.setattr(engine, name, module, raising=False)
    monkeypatch.setattr(build.config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(ctx["fin"], "feed", lambda: candidate)
    monkeypatch.setattr(build, "_enrich", lambda sections: "")
    outdir = ctx["root"] / "site" / "news"
    outdir.mkdir(parents=True, exist_ok=True)
    return build, outdir


def _retain_unsafe_static(ctx, outdir, snapshot):
    legacy = dict(snapshot)
    legacy.pop("tiingo_binding", None)
    legacy["rejected"] = [{"title": "Old unmarked Tiingo rejection", "domain": "cnbc.com"}]
    (outdir / "financial.json").write_text(json.dumps(legacy))
    (outdir / "by_ticker.json").write_text(json.dumps({"tickers": ctx["fin"].mastermind_by_ticker(snapshot)}))
    (outdir / "rejected.json").write_text(json.dumps({"feeds": {"financial": legacy["rejected"]}}))


@pytest.mark.parametrize("candidate_missing", [False, True])
def test_withdrawal_static_never_darken_cannot_restore_revoked_rows(tiingo_runtime, monkeypatch, candidate_missing):
    ctx = tiingo_runtime
    old = ctx["fin"].feed(use_cache=False)
    _change_tiingo_context(ctx, "disabled")
    candidate = None if candidate_missing else ctx["fin"].feed(use_cache=False)
    build, outdir = _static_builder(ctx, monkeypatch, candidate)
    _retain_unsafe_static(ctx, outdir, old)
    vm = build.build(write=True)
    published = json.loads((outdir / "financial.json").read_text())
    assert vm["fin"] == published
    _assert_no_tiingo_material(published)
    assert published["counts"]["raw"] == (0 if candidate_missing else 1)
    for name in ("by_ticker.json", "rejected.json"):
        text = (outdir / name).read_text()
        assert "Chipmaker reports strong" not in text
        assert "Old unmarked Tiingo rejection" not in text
    if candidate_missing:
        assert json.loads((outdir / "by_ticker.json").read_text())["tickers"] == {}


@pytest.mark.parametrize("write", [False, True])
def test_withdrawal_grant_change_during_enrichment_withholds_html_and_json(tiingo_runtime, monkeypatch, write):
    ctx = tiingo_runtime
    candidate = ctx["fin"].feed(use_cache=False)
    build, outdir = _static_builder(ctx, monkeypatch, candidate)
    def enrich(sections):
        _change_tiingo_context(ctx, "teaser_display")
        return ""
    monkeypatch.setattr(build, "_enrich", enrich)
    vm = build.build(write=write)
    _assert_no_tiingo_material(vm["fin"])
    assert vm["fin"]["counts"]["raw"] == 0
    if write:
        assert json.loads((outdir / "financial.json").read_text()) == vm["fin"]


def _assert_cleared_static(ctx, outdir, vm):
    published = json.loads((outdir / "financial.json").read_text())
    assert vm["fin"] == published
    _assert_no_tiingo_material(published)
    assert published["counts"]["raw"] == 0
    assert json.loads((outdir / "by_ticker.json").read_text())["tickers"] == {}
    rejected = json.loads((outdir / "rejected.json").read_text())
    assert rejected["feeds"]["financial"] == []
    assert "Old unmarked Tiingo rejection" not in json.dumps(rejected)


@pytest.mark.parametrize("failed_name", ["financial.json", "by_ticker.json", "rejected.json"])
def test_withdrawal_required_artifact_failure_is_not_reported_success(tiingo_runtime, monkeypatch, failed_name):
    from pathlib import Path
    ctx = tiingo_runtime
    old = ctx["fin"].feed(use_cache=False)
    _change_tiingo_context(ctx, "disabled")
    build, outdir = _static_builder(ctx, monkeypatch, None)
    _retain_unsafe_static(ctx, outdir, old)
    original = Path.write_text
    def fail_required(path, text, *args, **kwargs):
        if path == outdir / failed_name:
            raise OSError("synthetic required withdrawal write failure")
        return original(path, text, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", fail_required)
    for _attempt in range(2):
        with pytest.raises(OSError, match="required withdrawal"):
            build.build(write=True)
        # A partial clear must not replace the qualification trigger with a
        # reusable empty snapshot before all dependent writes succeed.
        retained = json.loads((outdir / "financial.json").read_text())
        assert not ctx["fin"].financial_snapshot_reusable(retained)
    monkeypatch.setattr(Path, "write_text", original)
    _assert_cleared_static(ctx, outdir, build.build(write=True))


@pytest.mark.parametrize("failed_name", ["financial.json", "by_ticker.json", "rejected.json"])
@pytest.mark.parametrize("retained_projections", ["both", "financial_rejections_only"])
def test_withdrawal_missing_financial_snapshot_retries_orphan_clear(
    tiingo_runtime, monkeypatch, failed_name, retained_projections,
):
    from pathlib import Path
    ctx = tiingo_runtime
    old = ctx["fin"].feed(use_cache=False)
    _change_tiingo_context(ctx, "disabled")
    build, outdir = _static_builder(ctx, monkeypatch, None)
    _retain_unsafe_static(ctx, outdir, old)
    (outdir / "financial.json").unlink()
    if retained_projections == "financial_rejections_only":
        (outdir / "by_ticker.json").unlink()
    original = Path.write_text
    def fail_required(path, text, *args, **kwargs):
        if path == outdir / failed_name:
            raise OSError("synthetic orphan withdrawal write failure")
        return original(path, text, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", fail_required)
    for _attempt in range(2):
        with pytest.raises(OSError, match="orphan withdrawal"):
            build.build(write=True)
        assert not (outdir / "financial.json").exists()
    monkeypatch.setattr(Path, "write_text", original)
    _assert_cleared_static(ctx, outdir, build.build(write=True))


@pytest.mark.parametrize("financial_bucket_present", [False, True])
def test_withdrawal_macro_rss_only_rejections_do_not_invent_financial_snapshot(
    tiingo_runtime, monkeypatch, financial_bucket_present,
):
    import engine
    ctx = tiingo_runtime
    _change_tiingo_context(ctx, "disabled")
    build, outdir = _static_builder(ctx, monkeypatch, None)
    macro_rejected = [{"title": "Macro-only rejected headline"}]
    rss_rejected = [{"title": "RSS-only rejected headline"}]
    feeds = {"macro": macro_rejected, "rss": rss_rejected}
    if financial_bucket_present:
        feeds["financial"] = []
    (outdir / "rejected.json").write_text(json.dumps({"feeds": feeds}))
    monkeypatch.setattr(engine.macro_news, "macro_headlines",
                        lambda: {"headlines": [], "rejected": macro_rejected})
    monkeypatch.setattr(engine.news_rss, "start_reject_log", lambda: (rss_rejected, None))
    vm = build.build(write=True)
    assert vm["fin"] is None
    assert not (outdir / "financial.json").exists()
    assert not (outdir / "by_ticker.json").exists()
    rejected = json.loads((outdir / "rejected.json").read_text())
    assert rejected["feeds"] == {"macro": macro_rejected, "rss": rss_rejected, "financial": []}
    assert rejected["n_total"] == 2
