"""Chinese original news: transport -> canonical universe -> incumbent store -> API.

All content, identities and rights receipts below are synthetic fixtures. These
tests do not establish a real publisher licence, live coverage or deployment.
"""
from concurrent.futures import Future
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import ticker_news
from collectors.benzinga_news import route_revision
from engine.finlight_news import FinlightNewsClient, FinlightPollBatch, FinlightPollError
from engine.qbus_news_contract import normalize_finlight_news, normalize_news, NewsContractError
from engine.qbus_news_intake import SupplementalNewsIntake
from engine.qbus_news_receipts import parse_rights_receipt, NewsReceiptError, write_health_receipt
from engine.qbus_news_store import NewsStore, NewsReadRights
from engine.qbus_news_universe import qualify_universe
from engine.qbus_news_universe_snapshot import build_news_universe_snapshot, NewsUniverseSnapshotError
from engine.qbus_news_editorial import company_reference_context, company_reference
from scripts.run_qbus_news import main

NOW = datetime.now(timezone.utc) - timedelta(seconds=10)
HK = "SEC:HK-XHKG-00700"
CN = "SEC:CN-XSHG-600519"
US = "SEC:US-XNAS-AAPL"


def owner_inputs():
    securities = [US, CN, HK, "SEC:CN-XSHE-000001", "SEC:HK-XHKG-00001"]
    master = [{"security_id": sid, "listing_key": sid.removeprefix("SEC:"),
               "issuer_id": None, "issuer_state": "NO_ISSUER_EVIDENCE",
               "security_state": None, "superseded_by": None} for sid in securities]
    aliases = [
        {"vendor": vendor, "vendor_symbol": symbol, "security_id": sid,
         "valid_from": None, "valid_to": None}
        for vendor, symbol, sid in [
            ("membership", "AAPL", US), ("yahoo_fetch", "AAPL", US),
            ("theme_graph_native", "600519.SH", CN),
            ("theme_graph_native", "0700.HK", HK),
            ("theme_graph_native", "000001.SZ", securities[3]),
            ("theme_graph_native", "0001.HK", securities[4]),
        ]
    ]
    return dict(current_rows=[{"symbol": "AAPL"}], pit_rows=[],
                alias_rows=aliases, security_rows=master, observed_at=NOW, min_count=1)


def universe_payload():
    return build_news_universe_snapshot(**owner_inputs(), include_cn_hk=True)


def universe():
    return qualify_universe(universe_payload(), asof=NOW)


def article(title="腾讯控股发布季度业绩，收入增长10%", *, ticker="0700", exchange="XHKG",
            link="https://www.cls.cn/detail/fixture-hk"):
    return {"source": "www.cls.cn", "link": link, "title": title, "language": "zh",
            "publishDate": (NOW - timedelta(minutes=1)).isoformat(),
            "companies": [{"ticker": ticker, "exchange": exchange,
                           "otherListings": [{"ticker": "TCEHY", "exchangeCode": "OTCM"}]}],
            "summary": "Provider-generated text must not become an original excerpt",
            "content": "Never retain a scraped body", "sentiment": "positive"}


def rights_payload(source="finlight:cls.cn"):
    return {
        "schema": "qbus.news_rights_receipt.v1", "receipt_id": "fixture-" + source,
        "owner_ref": "tests/fixture-only-not-a-licence", "status": "approved",
        "source": source, "provider": "finlight" if source.startswith("finlight:") else None,
        "publisher_rights_ref": "tests/synthetic-publisher-grant",
        "product_id": "fixture-only", "audiences": ["site_full"],
        "effective_at": (NOW-timedelta(days=1)).isoformat(),
        "expires_at": (NOW+timedelta(days=1)).isoformat(),
        "capabilities": {"internal_ingestion": True, "historical_retention": True,
                         "headline_display": True, "source_link_display": True,
                         "teaser_display": False, "derivative_processing": True},
    }


class Response:
    def __init__(self, rows=(), *, page=1, status=200, page_size=100):
        self.status_code, self.closed = status, False
        self.payload = {"status": "ok", "page": page, "pageSize": page_size, "articles": list(rows)}

    def iter_content(self, chunk_size):
        yield json.dumps(self.payload, ensure_ascii=False).encode()

    def close(self):
        self.closed = True


class Session:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def client(session):
    return FinlightNewsClient("fixture-key", session=session, clock=lambda: NOW)


def poll(c, **kwargs):
    return c.poll(since=NOW-timedelta(days=1), allowed_publishers=frozenset({"cls.cn"}), **kwargs)


def test_original_chinese_transport_identity_and_minimum_fields():
    response = Response([article()])
    session = Session([response])
    batch = poll(client(session))
    revision = batch.revisions[0]
    assert revision.title == article()["title"]
    assert revision.provider_tickers == ("00700.HK",)
    assert revision.source == "finlight:cls.cn"
    assert revision.teaser == revision.body_sha256 == ""
    assert "language:zh" in revision.tags
    entity = next(tag.removeprefix("finlight_entity:") for tag in revision.tags if tag.startswith("finlight_entity:"))
    assert json.loads(entity) == {"ticker": "0700", "exchange": "XHKG", "symbol": "00700.HK"}
    assert revision.published_at < revision.received_at
    assert revision.updated_at is None
    assert batch.complete and response.closed
    url, request = session.calls[0]
    assert url == "https://api.finlight.me/v2/articles"
    assert request["headers"]["X-API-KEY"] == "fixture-key"
    assert request["allow_redirects"] is False
    assert request["json"]["language"] == "zh"
    assert request["json"]["includeEntities"] is True
    assert request["json"]["sources"] == ["cls.cn", "www.cls.cn"]


@pytest.mark.parametrize(("ticker", "mic", "expected"), [
    ("600519", "XSHG", ("600519.SS",)),
    ("600519.SH", "XSHG", ("600519.SS",)),
    ("000001", "XSHE", ("000001.SZ",)),
    ("1", "XHKG", ("00001.HK",)),
    ("0700", "XHKG", ("00700.HK",)),
    ("00700.HK", "XHKG", ("00700.HK",)),
    ("000001", "XSHG", ()), ("600519.SZ", "XSHG", ()),
    ("TCEHY", "OTCM", ()), ("700", "", ()), ("430047.BJ", "XBSE", ()),
])
def test_exchange_qualified_entities_do_not_infer_listings(ticker, mic, expected):
    row = article(ticker=ticker, exchange=mic)
    row["companies"][0]["primaryListing"] = {"ticker": "600519", "exchangeCode": "XSHG"}
    assert normalize_finlight_news(row, received_at=NOW).provider_tickers == expected


def test_only_explicit_direct_entities_can_attach_both_a_and_h():
    row = article()
    row["companies"].append({"ticker": "600519", "exchange": "XSHG"})
    revision = normalize_finlight_news(row, received_at=NOW)
    assert set(route_revision(revision, universe()).security_ids) == {CN, HK}
    assert US not in route_revision(revision, universe()).security_ids


@pytest.mark.parametrize("change", [
    {"language": "en"}, {"publishDate": "2026-10-01T10:00:00"},
    {"link": "https://cls.cn.evil.example/1"}, {"source": "cls.cn/garbage"},
    {"companies": None}, {"publishDate": (NOW+timedelta(days=1)).isoformat()},
])
def test_untrusted_language_identity_url_and_clocks_are_rejected(change):
    row = {**article(), **change}
    with pytest.raises(NewsContractError):
        normalize_finlight_news(row, received_at=NOW)


def test_empty_grants_make_no_request_and_http_errors_do_not_expose_secrets():
    session = Session([])
    result = client(session).poll(since=NOW-timedelta(days=1), allowed_publishers=frozenset())
    assert result.pages == 0 and result.complete and session.calls == []
    for status, code in [(401, "finlight_auth_rejected"), (429, "finlight_rate_limited"),
                         (302, "finlight_http_error")]:
        with pytest.raises(FinlightPollError, match=code) as error:
            poll(client(Session([Response(status=status)])))
        assert "fixture-key" not in str(error.value)


def test_missing_entity_entitlement_and_malformed_page_are_not_successful_empty():
    row = {**article(), "companies": None}
    with pytest.raises(FinlightPollError, match="finlight_entities_unavailable"):
        poll(client(Session([Response([row])])))
    with pytest.raises(FinlightPollError, match="finlight_malformed_page"):
        poll(client(Session([Response([], page=2)])))
    with pytest.raises(FinlightPollError, match="finlight_malformed_page"):
        poll(client(Session([Response([], page_size=20)])))


def test_bounded_pagination_resumes_without_advancing_coverage_early():
    session = Session([Response([article()] * 100), Response([], page=2)])
    c = client(session)
    first = poll(c, max_pages=1)
    assert not first.complete and first.next_url == "finlight-page:2"
    second = poll(c, next_url=first.next_url, through=first.through)
    assert second.complete and second.pages == 1
    assert session.calls[1][1]["json"]["page"] == 2
    with pytest.raises(FinlightPollError, match="finlight_invalid_cursor"):
        poll(c, next_url="https://evil.example/?key=fixture-key")


def test_universe_extension_preserves_sp500_and_uses_current_alias_owner():
    base = build_news_universe_snapshot(**owner_inputs())
    extended = universe_payload()
    assert len(base["securities"]) == 1
    assert extended["cn_hk_count"] == 4
    bindings = {item.alias: item.security_id for item in universe().alias_bindings}
    assert bindings["AAPL"] == US
    assert bindings["0700.HK"] == bindings["00700.HK"] == bindings["700.HK"] == HK
    assert bindings["600519.SH"] == bindings["600519.SS"] == CN
    assert bindings["0001.HK"] != bindings["000001.SZ"]
    assert "700" not in bindings and "000001" not in bindings
    assert all(item["known_at"] == NOW.isoformat() for item in extended["securities"])


def test_cn_hk_extension_never_weakens_missing_owner_alias_failure():
    inputs = owner_inputs()
    inputs["alias_rows"] = [r for r in inputs["alias_rows"] if r["security_id"] != HK]
    with pytest.raises(NewsUniverseSnapshotError, match="cn_hk_identity_unqualified"):
        build_news_universe_snapshot(**inputs, include_cn_hk=True)
    inputs = owner_inputs()
    inputs["alias_rows"] = [r for r in inputs["alias_rows"] if r["vendor"] != "membership"]
    with pytest.raises(NewsUniverseSnapshotError, match="membership_alias_unresolved"):
        build_news_universe_snapshot(**inputs, include_cn_hk=True)


def test_transport_access_does_not_grant_publisher_display_rights():
    row = rights_payload()
    assert parse_rights_receipt(row, now=NOW).source == "finlight:cls.cn"
    for edit, code in [
        ({"publisher_rights_ref": ""}, "rights_publisher_grant_required"),
        ({"provider": "massive"}, "rights_provider_mismatch"),
        ({"source": "finlight"}, "rights_source"),
        ({"expires_at": NOW.isoformat()}, "rights_expired"),
        ({"capabilities": {**row["capabilities"], "source_link_display": False}},
         "capability_source_link_display_required"),
    ]:
        with pytest.raises(NewsReceiptError, match=code):
            parse_rights_receipt({**row, **edit}, now=NOW)


class ControlledPool:
    def submit(self, fn, **kwargs):
        self.future = Future()
        return self.future

    def shutdown(self, **kwargs):
        pass


def controlled_intake(store, grants):
    intake = SupplementalNewsIntake(
        client=SimpleNamespace(poll=lambda **kw: None), store=store,
        rights_provider=lambda: grants, universe_provider=universe,
        clock=lambda: NOW, monotonic=lambda: 0, provider="finlight",
    )
    intake._pool.shutdown()
    intake._pool = ControlledPool()
    return intake


def test_supplemental_cursor_is_separate_and_revocation_blocks_commit(tmp_path):
    path = tmp_path/"q.db"
    grants = [parse_rights_receipt(rights_payload(), now=NOW)]
    with NewsStore(path, source_key="benzinga-rest") as primary, NewsStore(
        path, source_key="finlight-chinese-news"
    ) as chinese:
        primary.commit((), expected_cursor=None, next_cursor="existing-primary")
        intake = controlled_intake(chinese, grants)
        intake.pump()
        grants.clear()
        intake._pool.future.set_result(FinlightPollBatch(
            (normalize_finlight_news(article(), received_at=NOW),), NOW, True, 1,
        ))
        intake.pump()
        assert chinese.current_cursor() is None
        assert primary.current_cursor() == "existing-primary"
        assert intake.health()["provider"] == "finlight"
        assert intake.health()["state"] == "restricted"
        intake.close()


@pytest.fixture
def api_composition(tmp_path, monkeypatch):
    db, up, rp, cp, hp = [tmp_path/name for name in ("q.db", "universe.json", "us.json", "cn.json", "health.json")]
    up.write_text(json.dumps(universe_payload()))
    rp.write_text(json.dumps(rights_payload("benzinga")))
    cp.write_text(json.dumps(rights_payload()))
    health = {
        "schema": "qbus.news_health.v1", "source": "benzinga", "state": "live",
        "observed_at": NOW.isoformat(), "last_successful_catchup": NOW.isoformat(),
        "last_stream_event_at": None, "gap_unresolved": False,
        "connect_attempts": 1, "disconnects": 0, "catchups_failed": 0,
        "additional_sources": [{"provider": "finlight", "state": "available",
                                "last_successful_poll": NOW.isoformat(),
                                "publishers": ["cls.cn"], "accepted_reports": 2, "delivery": "polled"}],
    }
    write_health_receipt(hp, health)
    for name, value in [("DB", db), ("UNIVERSE", up), ("RIGHTS", rp), ("HEALTH", hp)]:
        monkeypatch.setenv("MM_TICKER_NEWS_" + name, str(value))
    monkeypatch.setenv("MM_TICKER_NEWS_ADDITIONAL_RIGHTS", json.dumps([str(cp)]))
    monkeypatch.setattr(ticker_news, "_rate_or_429", lambda user: None)
    ticker_news._reset_rate_limit_for_tests()
    chinese_rows = [article(), article("贵州茅台发布年度业绩", ticker="600519", exchange="XSHG",
                                      link="https://www.cls.cn/detail/fixture-cn")]
    # Real adapter request decoding, normalization, intake drain and store commit.
    batch = poll(client(Session([Response(chinese_rows)])))
    with NewsStore(db, source_key="finlight-chinese-news") as store:
        intake = controlled_intake(store, [parse_rights_receipt(rights_payload(), now=NOW)])
        intake.pump()
        intake._pool.future.set_result(batch)
        intake.pump()
        assert intake.health()["state"] == "available"
        intake.close()
    with NewsStore(db, source_key="benzinga-rest") as store:
        us = normalize_news({"id": "us-fixture", "title": "Apple launches a new product",
                             "created": NOW.isoformat(), "updated": NOW.isoformat(),
                             "url": "https://www.benzinga.com/fixture", "stocks": ["AAPL"]},
                            transport="benzinga_rest", received_at=NOW)
        store.commit((route_revision(us, universe()),), expected_cursor=None, next_cursor="us-1")
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {"id": "fixture-user"}
    return TestClient(app), cp, hp, up, rp


def test_real_ticker_api_preserves_original_chinese_and_listing_scope(api_composition):
    api, *_ = api_composition
    hk = api.get("/api/ticker-news/0700.HK?view=news")
    assert hk.status_code == 200
    payload = hk.json()
    assert payload["security_id"] == HK
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["title"] == article()["title"]
    assert payload["rows"][0]["source"] == "finlight:cls.cn"
    assert payload["rows"][0]["publisher"] == "cls.cn"
    assert payload["rows"][0]["language"] == "zh"
    assert payload["rows"][0]["annotation"] is None
    assert payload["rows"][0]["teaser"] == ""
    assert payload["source_health"]["state"] == "unavailable"  # primary US wire excluded
    assert payload["source_health"]["additional_sources"][0]["state"] == "available"
    assert hk.headers["cache-control"] == "private, no-store"
    cn = api.get("/api/ticker-news/600519.SH?view=news").json()
    assert cn["security_id"] == CN and [r["title"] for r in cn["rows"]] == ["贵州茅台发布年度业绩"]
    us = api.get("/api/ticker-news/AAPL?view=news").json()
    assert us["state"] == "live" and us["rows"][0]["title"] == "Apple launches a new product"
    assert api.get("/api/ticker-news/700").status_code == 404
    assert api.get("/api/ticker-news/0001.HK").json()["rows"] == []


def test_expired_chinese_grant_hides_cached_rows_without_affecting_us(api_composition):
    api, chinese_receipt, *_ = api_composition
    row = rights_payload()
    row["expires_at"] = NOW.isoformat()
    chinese_receipt.write_text(json.dumps(row))
    hk = api.get("/api/ticker-news/00700.HK").json()
    assert hk["rows"] == [] and hk["state"] == "unavailable"
    assert api.get("/api/ticker-news/AAPL").json()["state"] == "live"


def test_chinese_company_text_and_qualified_symbols_do_not_need_latin_case():
    ctx = company_reference_context(security_id=HK, ticker="00700.HK", universe_revision="fixture",
                                    names=("腾讯", "騰訊"), symbols=("0700.HK",))
    assert company_reference("腾讯发布业绩", "", ctx) == "headline"
    assert company_reference("騰訊發布業績", "", ctx) == "headline"
    assert company_reference("公司(0700.HK)发布业绩", "", ctx) == "headline"
    assert company_reference("销售额700万元", "", ctx) == "not_observed"


def test_chinese_opposite_headlines_are_not_fuzzy_collapsed(tmp_path):
    with NewsStore(tmp_path/"q.db", source_key="finlight-chinese-news") as store:
        rows = [article("腾讯控股第三季度收入增长10%", link="https://www.cls.cn/one"),
                article("腾讯控股第三季度收入下降10%", link="https://www.cls.cn/two")]
        store.commit(tuple(route_revision(normalize_finlight_news(r, received_at=NOW), universe())
                           for r in rows), expected_cursor=None, next_cursor="fixture")
        snapshot = store.snapshot(HK, cursor=None, limit=10,
                                  rights=NewsReadRights(frozenset({"finlight:cls.cn"})))
        assert len(snapshot.rows) == 2
        assert len({r.story_id for r in snapshot.rows}) == 2


def test_activation_requires_key_publisher_rights_and_both_market_selections(
    api_composition, monkeypatch, capsys, tmp_path,
):
    _, cp, hp, up, rp = api_composition
    monkeypatch.setenv("BENZINGA_API_KEY", "fixture-primary-key")
    monkeypatch.delenv("FINLIGHT_KEY", raising=False)
    args = ["--check-activation", "--finlight-news", "--rights-receipt", str(rp),
            "--universe-snapshot", str(up), "--health-path", str(hp)]
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "activation_chinese_sources_unqualified"
    monkeypatch.setenv("FINLIGHT_KEY", "fixture-chinese-key")
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["chinese_sources_enabled"] is True
    assert result["cn_universe_count"] == result["hk_universe_count"] == 2
    snapshot = build_news_universe_snapshot(**owner_inputs())
    up.write_text(json.dumps(snapshot))
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)["cn_universe_count"] == 0


@pytest.mark.parametrize("rows, expected_state, accepted, unattributed, invalid", [
    ([], "available", 0, 0, 0),
    ([article(ticker="600519", exchange="XSHE")], "degraded", 0, 1, 1),
    ([{**article(), "companies": []}], "degraded", 0, 1, 0),
    ([article(), article(ticker="600519", exchange="XSHE")], "degraded", 1, 1, 1),
    ([article(ticker="9988")], "available", 0, 0, 0),
])
def test_retrieval_health_distinguishes_empty_invalid_partial_and_outside_universe(
    tmp_path, rows, expected_state, accepted, unattributed, invalid,
):
    batch = poll(client(Session([Response(rows)])))
    with NewsStore(tmp_path/"health.db", source_key="finlight-chinese-news") as store:
        intake = controlled_intake(store, [parse_rights_receipt(rights_payload(), now=NOW)])
        intake.pump()
        intake._pool.future.set_result(batch)
        intake.pump()
        health = intake.health()
        assert health["state"] == expected_state
        assert health["last_batch"]["fetched"] == len(rows)
        assert health["last_batch"]["accepted"] == accepted
        assert health["last_batch"]["unattributed"] == unattributed
        assert health["last_batch"]["entity_invalid"] == invalid
        if rows and expected_state == "available":
            assert health["last_batch"]["out_of_universe"] == 1
        if expected_state == "degraded":
            assert ticker_news._state_from_health(
                {"state": "unavailable", "additional_sources": [health]}, row_count=accepted,
            ) == "degraded"
        intake.close()


def test_unreviewed_publisher_receipt_cannot_start_chinese_intake(tmp_path):
    grant = parse_rights_receipt(rights_payload("finlight:unknown.example"), now=NOW)
    with NewsStore(tmp_path/"unknown.db", source_key="finlight-chinese-news") as store:
        intake = controlled_intake(store, [grant])
        intake.pump()
        assert intake.health()["state"] == "restricted"
        assert intake.health()["publishers"] == []
        assert intake._pending is None
        intake.close()
