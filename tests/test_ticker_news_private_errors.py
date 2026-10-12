"""Private-error coverage the framework defaults cannot give this router.

Pins the D1 catch-all (decoded-slash, trailing-slash and other unmatched
ticker-news paths stay private) and the D2 route class (query-validation 422s
on this router carry the private headers) without touching any other router's
default 422 behavior. W12 adds the bare root and non-GET unknown paths to the
private 404 family. Store, receipts and universe are tmp_path fixtures.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest

from engine import qbus_news_store as store_mod
from engine.qbus_news_contract import normalize_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
_SECURITY_NVDA = "SEC:US-XNAS-NVDA"
_TITLE = "Nvidia launches accelerator"

_TICKER_NEWS_PREFIX = "/api/ticker-news"
_CATCH_ALL_PATH = "/api/ticker-news/{rest:path}"
_BARE_ROOT_PATH = "/api/ticker-news"
_CATCH_ALL_PATHS = frozenset({_CATCH_ALL_PATH, _BARE_ROOT_PATH})
_REAL_PATHS = frozenset(
    {
        "/api/ticker-news/stories/{story_id}",
        "/api/ticker-news/{ticker}/changes",
        "/api/ticker-news/{ticker}",
        "/api/ticker-news/{ticker}/stream",
    }
)
_EXPECTED_PATHS = _REAL_PATHS | _CATCH_ALL_PATHS
_NON_GET_METHODS = ["POST", "PUT", "PATCH", "DELETE"]


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


def _rights(now: datetime) -> dict:
    return {
        "schema": "qbus.news_rights_receipt.v1",
        "receipt_id": "receipt-fixture-private-errors",
        "owner_ref": "owner-ref-fixture",
        "status": "approved",
        "source": "benzinga",
        "product_id": "product-fixture",
        "audiences": ["site_full"],
        "effective_at": _iso(now - timedelta(hours=1)),
        "expires_at": _iso(now + timedelta(days=30)),
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": True,
            "teaser_display": True,
            "body_display": False,
            "image_display": False,
            "derivative_processing": True,
        },
    }


def _universe(now: datetime) -> dict:
    return {
        "owner": "fixture.security_reference",
        "revision": "fixture-r1",
        "complete": True,
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
    user_id: str = "user-private-errors",
):
    from app import ticker_news

    now = datetime.now(UTC)
    db = _make_db(tmp_path)
    monkeypatch.setenv("MM_TICKER_NEWS_DB", str(db))
    rights_path = tmp_path / "rights.json"
    _write(rights_path, _rights(now))
    monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(rights_path))
    universe_path = tmp_path / "universe.json"
    _write(universe_path, _universe(now))
    monkeypatch.setenv("MM_TICKER_NEWS_UNIVERSE", str(universe_path))
    monkeypatch.delenv("MM_TICKER_NEWS_HEALTH", raising=False)
    ticker_news._reset_rate_limit_for_tests()
    return {
        "ticker_news": ticker_news,
        "client": _client(
            ticker_news,
            user_id=user_id,
            authenticated=True,
        ),
        "db": db,
        "now": now,
    }


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


def _app_routes(app):
    """Flatten lazy included routers so per-module declaration order is visible."""
    out = []
    for route in app.routes:
        inner = getattr(route, "original_router", None)
        if inner is not None and hasattr(inner, "routes"):
            out.extend(_app_routes(inner))
        else:
            out.append(route)
    return out


def test_route_order_catch_all_is_last_and_shadows_nothing():
    import app.main as main_mod

    flat = _app_routes(main_mod.app)
    paths = [getattr(route, "path", "") for route in flat]
    ticker_news_paths = [p for p in paths if p.startswith(_TICKER_NEWS_PREFIX)]
    assert set(ticker_news_paths) == _EXPECTED_PATHS
    assert _CATCH_ALL_PATH in ticker_news_paths
    real_positions = [index for index, path in enumerate(paths) if path in _REAL_PATHS]
    catch_all_positions = [
        index for index, path in enumerate(paths) if path in _CATCH_ALL_PATHS
    ]
    assert real_positions and catch_all_positions
    assert max(real_positions) < min(catch_all_positions)
    last_catch_all = max(catch_all_positions)
    after = paths[last_catch_all + 1 :]
    assert not [p for p in after if p.startswith(_TICKER_NEWS_PREFIX)]
    catch_all_method_sets = [
        route.methods
        for route in flat
        if getattr(route, "path", "") == _CATCH_ALL_PATH
    ]
    assert {"GET"} in catch_all_method_sets
    assert set(_NON_GET_METHODS) in catch_all_method_sets


def test_trailing_slash_is_private_404(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    response = surface["client"].get(
        "/api/ticker-news/NVDA/",
        follow_redirects=False,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "not found"
    assert not response.history
    _assert_private(response)


def test_multi_segment_unknown_path_is_private_404(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    response = surface["client"].get(
        "/api/ticker-news/NVDA/x/y",
        follow_redirects=False,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "not found"
    _assert_private(response)

    unauthenticated = _client(
        surface["ticker_news"],
        user_id="user-private-errors",
        authenticated=False,
    ).get("/api/ticker-news/NVDA/x")
    assert unauthenticated.status_code == 401
    _assert_private(unauthenticated)


# Records, without changing, the non-private 405 a non-GET gets on a real GET
# route: the router answers before authentication and without private headers.
def test_non_get_on_real_routes_is_recorded_unchanged(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    story_id = _story_id(surface["db"])
    real_paths = [
        f"/api/ticker-news/stories/{story_id}",
        "/api/ticker-news/NVDA/changes",
        "/api/ticker-news/NVDA",
        "/api/ticker-news/NVDA/stream",
    ]
    clients = [
        (
            "authenticated",
            surface["client"],
        ),
        (
            "unauthenticated",
            _client(
                surface["ticker_news"],
                user_id="user-private-errors",
                authenticated=False,
            ),
        ),
    ]
    for method in _NON_GET_METHODS:
        for path in real_paths:
            for label, client in clients:
                response = client.request(method, path, follow_redirects=False)
                assert response.status_code == 405, (label, method, path, response.text)
                assert response.json() == {"detail": "Method Not Allowed"}
                assert response.headers.get("allow") == "GET"
                assert sorted(response.headers.keys()) == [
                    "allow",
                    "content-length",
                    "content-type",
                ]
                assert "cache-control" not in response.headers


def test_bare_root_is_private_404_without_redirect(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    response = surface["client"].get("/api/ticker-news", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["detail"] == "not found"
    assert "location" not in response.headers
    assert not response.history
    _assert_private(response)

    unauthenticated = _client(
        surface["ticker_news"],
        user_id="user-private-errors",
        authenticated=False,
    ).get("/api/ticker-news", follow_redirects=False)
    assert unauthenticated.status_code == 401
    assert "location" not in unauthenticated.headers
    _assert_private(unauthenticated)


def test_empty_rest_is_private_404(monkeypatch, tmp_path):
    # W12: the private 422 for empty rest was replaced by the catch-all 404.
    surface = _arm(monkeypatch, tmp_path)
    response = surface["client"].get("/api/ticker-news/", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["detail"] == "not found"
    assert "location" not in response.headers
    _assert_private(response)

    unauthenticated = _client(
        surface["ticker_news"],
        user_id="user-private-errors",
        authenticated=False,
    ).get("/api/ticker-news/", follow_redirects=False)
    assert unauthenticated.status_code == 401
    _assert_private(unauthenticated)


def test_double_slash_rest_still_private_422(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    response = surface["client"].get("/api/ticker-news//x", follow_redirects=False)
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid ticker"
    _assert_private(response)


def test_non_get_unknown_paths_are_private_404(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    unauthenticated = _client(
        surface["ticker_news"],
        user_id="user-private-errors",
        authenticated=False,
    )
    unknown_paths = [
        "/api/ticker-news",
        "/api/ticker-news/",
        "/api/ticker-news/a/b/c",
        "/api/ticker-news/NVDA/",
        "/api/ticker-news/NVDA/unknown",
        "/api/ticker-news/stories/",
    ]
    for method in _NON_GET_METHODS:
        for path in unknown_paths:
            response = surface["client"].request(method, path, follow_redirects=False)
            assert response.status_code == 404, (method, path, response.text)
            assert response.json() == {"detail": "not found"}
            assert "location" not in response.headers
            _assert_private(response)

            unauth = unauthenticated.request(method, path, follow_redirects=False)
            assert unauth.status_code == 401, (method, path, unauth.text)
            assert "location" not in unauth.headers
            _assert_private(unauth)


def test_non_get_bad_ticker_unknown_path_is_private_422(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    get_response = surface["client"].get(
        "/api/ticker-news/bad%20ticker/x",
        follow_redirects=False,
    )
    post_response = surface["client"].post(
        "/api/ticker-news/bad%20ticker/x",
        follow_redirects=False,
    )
    for label, response in (("GET", get_response), ("POST", post_response)):
        assert response.status_code == 422, (label, response.text)
        assert response.json()["detail"] == "invalid ticker"
        _assert_private(response)
    assert get_response.json() == post_response.json()


def test_existing_routes_still_win(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    client = surface["client"]
    story_id = _story_id(surface["db"])

    snapshot = client.get("/api/ticker-news/NVDA")
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["schema"] == "ticker_news.snapshot.v1"
    assert snapshot.json()["rows"]

    changes = client.get("/api/ticker-news/NVDA/changes")
    assert changes.status_code == 200, changes.text
    assert changes.json()["schema"] == "ticker_news.changes.v1"

    story = client.get(f"/api/ticker-news/stories/{story_id}")
    assert story.status_code == 200, story.text
    assert story.json()["schema"] == "ticker_news.story.v1"

    # A syntactically valid but unbound ticker on the stream route gets the
    # stream handler's own universe refusal, never the catch-all's 404.
    stream = client.get("/api/ticker-news/AAPL/stream")
    assert stream.status_code == 404, stream.text
    assert stream.json()["detail"] == "ticker not in qualified news universe"


def test_include_router_keeps_route_class_on_real_app():
    from app.ticker_news import _PrivateValidationRoute
    import app.main as main_mod

    flat = _app_routes(main_mod.app)
    inside = [
        route
        for route in flat
        if getattr(route, "path", "").startswith(_TICKER_NEWS_PREFIX)
    ]
    assert inside
    assert all(isinstance(route, _PrivateValidationRoute) for route in inside)
    outside = [
        route
        for route in flat
        if isinstance(route, APIRoute)
        and not getattr(route, "path", "").startswith(_TICKER_NEWS_PREFIX)
    ]
    assert outside
    assert any(not isinstance(route, _PrivateValidationRoute) for route in outside)


def test_validation_422_scope_outside_router_unchanged(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    ticker_news = surface["ticker_news"]
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
        "id": "scope-user",
        "email": "user@example.test",
    }

    @app.get("/other")
    def other(limit: int = Query(default=5, ge=1)):
        return {"limit": limit}

    client = TestClient(app)
    outside = client.get("/other?limit=0")
    assert outside.status_code == 422
    assert outside.headers.get("cache-control") != "private, no-store"

    inside = client.get("/api/ticker-news/NVDA?limit=0")
    assert inside.status_code == 422, inside.text
    assert isinstance(inside.json()["detail"], list)
    _assert_private(inside)
