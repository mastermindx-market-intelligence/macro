"""Failure and privacy matrix for the private ticker-news read API.

Pins status, detail, and private response headers for the four
``/api/ticker-news/*`` routes. Payload asserts name specific keys only.
Receipts, the universe file, and the store are tmp_path fixtures.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from engine import qbus_news_store as store_mod
from engine.qbus_news_contract import normalize_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
_SECURITY_NVDA = "SEC:US-XNAS-NVDA"
_TITLE = "Nvidia launches accelerator"
_TEASER = f"teaser:{_TITLE}"
_URL = "https://www.benzinga.com/news/1"
_FOREIGN_CURSOR = 424242

# Query values rejected by FastAPI before the route body runs.
_VALIDATION_PATHS = (
    "/api/ticker-news/NVDA?limit=0",
    "/api/ticker-news/NVDA?limit=10000",
    "/api/ticker-news/NVDA?cursor=0",
    "/api/ticker-news/NVDA/changes?limit=0",
    "/api/ticker-news/NVDA/changes?limit=10000",
    "/api/ticker-news/NVDA/changes?after_sequence=-1",
    "/api/ticker-news/NVDA/stream?after_sequence=-1",
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def _routed(item_id=1, title=_TITLE, minute=0):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (t - timedelta(seconds=1)).isoformat(),
            "updated": t.isoformat(),
            "title": title,
            "teaser": f"teaser:{title}",
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=t + timedelta(seconds=2),
    )
    return store_mod.RoutedRevision(
        revision=revision,
        security_ids=(_SECURITY_NVDA,),
        universe_revision="sp500-r1",
    )


def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "q.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([_routed()], expected_cursor=None, next_cursor="c1")
    return db


def _empty_db(tmp_path: Path) -> Path:
    db = tmp_path / "empty.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest"):
        pass
    return db


def _rights(now: datetime, **overrides) -> dict:
    capabilities = {
        "internal_ingestion": True,
        "historical_retention": True,
        "headline_display": True,
        "source_link_display": True,
        "teaser_display": True,
        "body_display": False,
        "image_display": False,
        "derivative_processing": False,
    }
    capabilities.update(overrides.pop("capabilities", {}))
    payload = {
        "schema": "qbus.news_rights_receipt.v1",
        "receipt_id": "receipt-fixture-n-matrix",
        "owner_ref": "owner-ref-fixture",
        "status": "approved",
        "source": "benzinga",
        "product_id": "product-fixture",
        "audiences": ["site_full"],
        "effective_at": _iso(now - timedelta(hours=1)),
        "expires_at": _iso(now + timedelta(days=30)),
        "capabilities": capabilities,
    }
    payload.update(overrides)
    return payload


def _universe(now: datetime, *, complete: bool = True) -> dict:
    return {
        "owner": "fixture.security_reference",
        "revision": "fixture-r1",
        "complete": complete,
        "truncated": False,
        "effective_at": _iso(now - timedelta(days=1)),
        "known_at": _iso(now - timedelta(minutes=1)),
        "fresh_until": _iso(now + timedelta(days=1)),
        "securities": [
            {
                "security_id": _SECURITY_NVDA,
                "ticker": "NVDA",
                "aliases": ["NVDA"],
                "valid_from": _iso(now - timedelta(days=100)),
                "valid_to": None,
                "known_at": _iso(now - timedelta(minutes=1)),
            }
        ],
    }


def _health(now: datetime, **overrides) -> dict:
    payload = {
        "schema": "qbus.news_health.v1",
        "source": "benzinga",
        "state": "live",
        "observed_at": _iso(now - timedelta(seconds=2)),
        "last_successful_catchup": _iso(now - timedelta(seconds=5)),
        "last_stream_event_at": None,
        "gap_unresolved": False,
        "connect_attempts": 1,
        "disconnects": 0,
        "catchups_failed": 0,
    }
    payload.update(overrides)
    return payload


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _assert_private(response) -> None:
    assert response.headers.get("cache-control") == "private, no-store"
    assert response.headers.get("vary") == "Authorization"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-robots-tag") == "noindex, noarchive"


def _story_id(db: Path) -> str:
    with store_mod.NewsStore.open_readonly(db, source_key="benzinga-rest") as store:
        rows = store.snapshot(
            _SECURITY_NVDA,
            limit=5,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        ).rows
    assert rows
    return rows[0].story_id


def _client(ticker_news, *, user_id: str, authenticated: bool):
    app = FastAPI()
    app.include_router(ticker_news.router)
    if authenticated:
        app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
            "id": user_id,
            "email": "user@example.test",
        }
    return TestClient(app)


def _arm(
    monkeypatch,
    tmp_path: Path,
    *,
    with_db: bool = True,
    with_rights: bool = True,
    with_universe: bool = True,
    user_id: str = "user-n-matrix",
    authenticated: bool = True,
):
    from app import ticker_news

    now = datetime.now(UTC)
    db = _make_db(tmp_path) if with_db else tmp_path / "missing-news.sqlite3"
    monkeypatch.setenv("MM_TICKER_NEWS_DB", str(db))
    rights_path = tmp_path / "rights.json"
    if with_rights:
        _write(rights_path, _rights(now))
        monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(rights_path))
    universe_path = tmp_path / "universe.json"
    if with_universe:
        _write(universe_path, _universe(now))
        monkeypatch.setenv("MM_TICKER_NEWS_UNIVERSE", str(universe_path))
    monkeypatch.delenv("MM_TICKER_NEWS_HEALTH", raising=False)
    ticker_news._reset_rate_limit_for_tests()
    return {
        "ticker_news": ticker_news,
        "client": _client(
            ticker_news,
            user_id=user_id,
            authenticated=authenticated,
        ),
        "db": db,
        "rights_path": rights_path,
        "universe_path": universe_path,
        "now": now,
    }


def _parse_sse(chunks: list[str]) -> list[tuple[str, dict]]:
    events = []
    for block in "".join(chunks).split("\n\n"):
        if not block.strip() or block.lstrip().startswith(":"):
            continue
        name = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        if name is not None:
            events.append((name, data))
    return events


def _collect_sse(ticker_news, *, on_chunk=None, **kwargs) -> list[tuple[str, dict]]:
    async def collect():
        out = []
        async for chunk in ticker_news._sse_events(**kwargs):
            out.append(chunk)
            if on_chunk is not None:
                on_chunk(chunk)
        return out

    return _parse_sse(asyncio.run(collect()))


@pytest.fixture(autouse=True)
def _isolate_ticker_news_env(monkeypatch):
    from app import ticker_news

    for name in (
        "MM_TICKER_NEWS_DB",
        "MM_TICKER_NEWS_RIGHTS",
        "MM_TICKER_NEWS_HEALTH",
        "MM_TICKER_NEWS_UNIVERSE",
    ):
        monkeypatch.delenv(name, raising=False)
    ticker_news._reset_rate_limit_for_tests()
    yield
    ticker_news._reset_rate_limit_for_tests()


def test_auth_denial_carries_private_headers_and_never_opens_store(monkeypatch, tmp_path):
    """401 from require_site_full_user keeps every private header and skips the store."""
    surface = _arm(monkeypatch, tmp_path, authenticated=False)
    story_id = _story_id(surface["db"])
    opened: list[str] = []
    original_open = store_mod.NewsStore.open_readonly.__func__

    def spy(cls, path, *, source_key, cluster_policy=None):
        opened.append(str(path))
        return original_open(
            cls,
            path,
            source_key=source_key,
            cluster_policy=cluster_policy,
        )

    monkeypatch.setattr(store_mod.NewsStore, "open_readonly", classmethod(spy))
    client = surface["client"]
    for path in (
        "/api/ticker-news/NVDA",
        "/api/ticker-news/NVDA/changes",
        "/api/ticker-news/NVDA/stream",
        f"/api/ticker-news/stories/{story_id}",
    ):
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.json()["detail"] == "missing bearer token"
        _assert_private(response)
    assert opened == []


def test_rights_receipt_failures_are_private_503_on_all_routes(monkeypatch, tmp_path):
    """Missing, expired, wrong-audience, and unapproved receipts fail closed."""
    surface = _arm(monkeypatch, tmp_path)
    now = surface["now"]
    story_id = _story_id(surface["db"])
    routes = (
        "/api/ticker-news/NVDA",
        "/api/ticker-news/NVDA/changes",
        "/api/ticker-news/NVDA/stream",
        f"/api/ticker-news/stories/{story_id}",
    )
    expired = _rights(
        now,
        receipt_id="receipt-fixture-expired",
        effective_at=_iso(now - timedelta(days=3)),
        expires_at=_iso(now - timedelta(seconds=5)),
    )
    cases = {
        "missing": None,
        "expired": expired,
        "wrong_audience": _rights(
            now,
            receipt_id="receipt-fixture-audience",
            audiences=["other_audience"],
        ),
        "not_approved": _rights(
            now,
            receipt_id="receipt-fixture-pending",
            status="pending",
        ),
    }
    for name, payload in cases.items():
        if payload is None:
            monkeypatch.delenv("MM_TICKER_NEWS_RIGHTS", raising=False)
        else:
            _write(surface["rights_path"], payload)
            monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(surface["rights_path"]))
        for path in routes:
            response = surface["client"].get(path)
            assert response.status_code == 503, (name, path, response.text)
            assert response.json()["detail"] == "ticker news rights unavailable"
            _assert_private(response)


def test_display_flags_hide_teaser_and_url_until_granted(monkeypatch, tmp_path):
    """teaser_display and source_link_display gate row fields on every read route.

    The store redacts a denied field to an empty string. A granted field carries
    the fixture teaser and URL.
    """
    surface = _arm(monkeypatch, tmp_path)
    story_id = _story_id(surface["db"])
    routes = {
        "snapshot": "/api/ticker-news/NVDA",
        "changes": "/api/ticker-news/NVDA/changes",
        "story": f"/api/ticker-news/stories/{story_id}",
    }
    cases = (
        ({"teaser_display": False, "source_link_display": True}, "", _URL),
        ({"teaser_display": True, "source_link_display": False}, _TEASER, ""),
        ({"teaser_display": True, "source_link_display": True}, _TEASER, _URL),
    )
    for capabilities, teaser, url in cases:
        _write(
            surface["rights_path"],
            _rights(
                surface["now"],
                receipt_id="receipt-fixture-display",
                capabilities=capabilities,
            ),
        )
        for kind, path in routes.items():
            response = surface["client"].get(path)
            assert response.status_code == 200, (kind, capabilities, response.text)
            _assert_private(response)
            body = response.json()
            rows = body["members"] if kind == "story" else body["rows"]
            assert rows, kind
            for row in rows:
                assert row["teaser"] == teaser, (kind, row["teaser"])
                assert row["url"] == url, (kind, row["url"])
                assert row["title"] == _TITLE


def test_missing_store_is_private_503_not_empty_success(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path, with_db=False)
    for path in (
        "/api/ticker-news/NVDA",
        "/api/ticker-news/NVDA/changes",
        "/api/ticker-news/stories/missing-story-fixture",
    ):
        response = surface["client"].get(path)
        assert response.status_code == 503, (path, response.text)
        assert response.json()["detail"] == "ticker news temporarily unavailable"
        assert "rows" not in response.json()
        _assert_private(response)


def test_universe_and_ticker_failures(monkeypatch, tmp_path):
    """Missing or unqualified universe is 503; unknown ticker is 404; bad syntax is 422."""
    surface = _arm(monkeypatch, tmp_path)
    ticker_news = surface["ticker_news"]
    client = surface["client"]
    now = surface["now"]
    ticker_routes = (
        "/api/ticker-news/{ticker}",
        "/api/ticker-news/{ticker}/changes",
        "/api/ticker-news/{ticker}/stream",
    )

    monkeypatch.setenv(
        "MM_TICKER_NEWS_UNIVERSE",
        str(tmp_path / "absent-universe.json"),
    )
    for template in ticker_routes:
        response = client.get(template.format(ticker="NVDA"))
        assert response.status_code == 503, response.text
        assert response.json()["detail"] == "ticker news universe unavailable"
        _assert_private(response)

    _write(surface["universe_path"], _universe(now, complete=False))
    monkeypatch.setenv("MM_TICKER_NEWS_UNIVERSE", str(surface["universe_path"]))
    for template in ticker_routes:
        response = client.get(template.format(ticker="NVDA"))
        assert response.status_code == 503, response.text
        assert response.json()["detail"] == "ticker news universe unavailable"
        _assert_private(response)

    _write(surface["universe_path"], _universe(now))
    for template in ticker_routes:
        response = client.get(template.format(ticker="AAPL"))
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == "ticker not in qualified news universe"
        _assert_private(response)

    for segment in ("A%20B", "A" * 40, "A..B"):
        for template in ticker_routes:
            response = client.get(template.format(ticker=segment))
            assert response.status_code == 422, (segment, template, response.text)
            assert response.json()["detail"] == "invalid ticker"
            _assert_private(response)

    user = {"id": "user-n-matrix", "email": "user@example.test"}
    for caller in (
        lambda: ticker_news.ticker_news_snapshot("../x", user=user),
        lambda: ticker_news.ticker_news_changes("../x", user=user),
        lambda: ticker_news.ticker_news_stream("../x", user=user),
    ):
        with pytest.raises(HTTPException) as raised:
            caller()
        assert raised.value.status_code == 422
        assert raised.value.detail == "invalid ticker"
        assert raised.value.headers["Cache-Control"] == "private, no-store"
        assert raised.value.headers["Vary"] == "Authorization"
        assert raised.value.headers["X-Robots-Tag"] == "noindex, noarchive"
        assert raised.value.headers["X-Content-Type-Options"] == "nosniff"


def test_http_slash_ticker_is_422_with_private_cache_control(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    response = surface["client"].get("/api/ticker-news/..%2Fx")
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid ticker"
    assert response.headers.get("cache-control") == "private, no-store"


def test_query_validation_rejects_out_of_range_queries(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    for path in _VALIDATION_PATHS:
        response = surface["client"].get(path)
        assert response.status_code == 422, (path, response.text)
        detail = response.json()["detail"]
        assert isinstance(detail, list) and detail
        assert detail[0]["loc"][0] == "query"
        assert detail[0]["type"] in {"greater_than_equal", "less_than_equal"}


def test_query_validation_422_carries_private_cache_control(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    for path in _VALIDATION_PATHS:
        response = surface["client"].get(path)
        assert response.status_code == 422, path
        assert response.headers.get("cache-control") == "private, no-store"
        assert response.headers.get("vary") == "Authorization"
        assert response.headers.get("x-robots-tag") == "noindex, noarchive"


def test_foreign_snapshot_cursor_returns_private_page(monkeypatch, tmp_path):
    """An int cursor no row uses is a page bound, not an outage.

    Snapshot treats cursor as an exclusive upper bound on cluster sequence.
    Cursor 424242 matches no row and still returns the older NVDA page.
    """
    surface = _arm(monkeypatch, tmp_path)
    response = surface["client"].get(f"/api/ticker-news/NVDA?cursor={_FOREIGN_CURSOR}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema"] == "ticker_news.snapshot.v1"
    assert body["ticker"] == "NVDA"
    assert body["rows"]
    assert all(row["sequence"] != _FOREIGN_CURSOR for row in body["rows"])
    assert body["next_cursor"] == body["rows"][-1]["sequence"]
    assert body.get("detail") != "ticker news temporarily unavailable"
    _assert_private(response)


def test_state_from_health_projection(monkeypatch, tmp_path):
    """_state_from_health projects source state; a missing health path stays unavailable."""
    from app import ticker_news

    project = ticker_news._state_from_health
    assert project({"state": "live"}, row_count=0) == "quiet"
    assert project({"state": "live"}, row_count=2) == "live"
    assert project({"state": "LIVE"}, row_count=0) == "quiet"
    for raw in ("catching_up", "degraded", "unavailable", "restricted"):
        assert project({"state": raw}, row_count=0) == raw
        assert project({"state": raw}, row_count=3) == raw
        assert project({"state": raw.upper()}, row_count=1) == raw
    assert project({"state": "not-a-state"}, row_count=1) == "degraded"
    assert project({}, row_count=1) == "degraded"

    monkeypatch.delenv("MM_TICKER_NEWS_HEALTH", raising=False)
    missing = ticker_news._source_health()
    assert missing["state"] == "unavailable"
    assert missing["reason"] == "receipt_path_unset"
    assert project(missing, row_count=4) == "unavailable"

    surface = _arm(monkeypatch, tmp_path)
    now = datetime.now(UTC)
    health_path = tmp_path / "health.json"
    _write(health_path, _health(now))
    monkeypatch.setenv("MM_TICKER_NEWS_HEALTH", str(health_path))
    live = surface["client"].get("/api/ticker-news/NVDA")
    assert live.status_code == 200, live.text
    assert live.json()["state"] == "live"
    assert live.json()["source_health"]["state"] == "live"
    assert live.json()["source_health"]["reason"] == "fresh"
    assert live.json()["rows"]
    _assert_private(live)

    empty = _empty_db(tmp_path)
    monkeypatch.setenv("MM_TICKER_NEWS_DB", str(empty))
    quiet = surface["client"].get("/api/ticker-news/NVDA")
    assert quiet.status_code == 200, quiet.text
    assert quiet.json()["state"] == "quiet"
    assert quiet.json()["rows"] == []
    _assert_private(quiet)

    monkeypatch.delenv("MM_TICKER_NEWS_HEALTH", raising=False)
    unavailable = surface["client"].get("/api/ticker-news/NVDA")
    assert unavailable.status_code == 200, unavailable.text
    assert unavailable.json()["state"] == "unavailable"
    assert unavailable.json()["source_health"]["state"] == "unavailable"
    assert unavailable.json()["source_health"]["reason"] == "receipt_path_unset"
    _assert_private(unavailable)


def test_rate_limit_429_carries_retry_after_and_private_headers(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path, user_id="rate-limit-user")
    ticker_news = surface["ticker_news"]
    client = surface["client"]
    limit = ticker_news._RATE_LIMIT_REQUESTS
    for index in range(limit):
        response = client.get("/api/ticker-news/NVDA")
        assert response.status_code == 200, index
    blocked = client.get("/api/ticker-news/NVDA/changes")
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "ticker news rate limit reached"
    assert blocked.headers.get("retry-after") == "60"
    _assert_private(blocked)


def test_sse_rights_revoked_between_cycles_emits_restricted_and_ends(
    monkeypatch, tmp_path
):
    surface = _arm(monkeypatch, tmp_path)
    ticker_news = surface["ticker_news"]
    def revoke_after_delivery(chunk):
        if chunk.startswith("event: upsert"):
            _write(
                surface["rights_path"],
                _rights(
                    surface["now"],
                    receipt_id="receipt-fixture-revoked",
                    status="revoked",
                ),
            )

    events = _collect_sse(
        ticker_news,
        on_chunk=revoke_after_delivery,
        ticker="NVDA",
        user={"id": "user-n-matrix"},
        after_sequence=0,
        poll_seconds=0,
        max_cycles=4,
    )
    upserts = [data for name, data in events if name == "upsert"]
    restricted = [item for item in events if item[0] == "restricted"]
    assert upserts
    assert upserts[0]["title"] == _TITLE
    assert len(restricted) == 1
    assert events[-1][0] == "restricted"
    assert restricted[0][1]["schema"] == "ticker_news.restricted.v1"
    assert restricted[0][1]["ticker"] == "NVDA"
    assert restricted[0][1]["detail"] == "ticker news rights unavailable"
    assert events.index(restricted[0]) > events.index(("upsert", upserts[0]))


def test_sse_store_unavailable_midstream_emits_unavailable_and_ends(
    monkeypatch, tmp_path
):
    surface = _arm(monkeypatch, tmp_path)
    ticker_news = surface["ticker_news"]
    def lose_store_after_delivery(chunk):
        if chunk.startswith("event: upsert"):
            monkeypatch.setattr(
                ticker_news, "_news_db_path",
                lambda: tmp_path / "store-gone.sqlite3",
            )

    events = _collect_sse(
        ticker_news,
        on_chunk=lose_store_after_delivery,
        ticker="NVDA",
        user={"id": "user-n-matrix"},
        after_sequence=0,
        poll_seconds=0,
        max_cycles=4,
    )
    upserts = [data for name, data in events if name == "upsert"]
    unavailable = [item for item in events if item[0] == "unavailable"]
    assert upserts
    assert upserts[0]["title"] == _TITLE
    assert len(unavailable) == 1
    assert events[-1][0] == "unavailable"
    assert unavailable[0][1]["schema"] == "ticker_news.unavailable.v1"
    assert unavailable[0][1]["ticker"] == "NVDA"
    assert unavailable[0][1]["detail"] == "ticker news temporarily unavailable"


def test_story_unknown_id_is_private_404_and_members_omit_denied_teaser(
    monkeypatch, tmp_path
):
    surface = _arm(monkeypatch, tmp_path)
    missing = surface["client"].get("/api/ticker-news/stories/missing-story-fixture")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "ticker news story not found"
    _assert_private(missing)

    _write(
        surface["rights_path"],
        _rights(
            surface["now"],
            receipt_id="receipt-fixture-no-teaser",
            capabilities={"teaser_display": False, "source_link_display": True},
        ),
    )
    story_id = _story_id(surface["db"])
    found = surface["client"].get(f"/api/ticker-news/stories/{story_id}")
    assert found.status_code == 200, found.text
    _assert_private(found)
    body = found.json()
    assert body["schema"] == "ticker_news.story.v1"
    assert body["story_id"] == story_id
    assert body["members"]
    for member in body["members"]:
        assert member["teaser"] == ""
        assert member["url"] == _URL
        assert member["title"] == _TITLE
