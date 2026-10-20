"""Private Macro API tests for the live ticker-news read plane."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from engine import qbus_news_store as store_mod
from engine.qbus_news_contract import normalize_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)


def _routed(item_id=1, title="Nvidia launches accelerator", minute=0):
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
        security_ids=("SEC:US-XNAS-NVDA",),
        universe_revision="sp500-r1",
    )


def _make_db(tmp_path):
    db = tmp_path / "q.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([_routed()], expected_cursor=None, next_cursor="c1")
    return db


def _app(monkeypatch, tmp_path, *, rights=True):
    from app import ticker_news

    db = _make_db(tmp_path)
    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: (
            "SEC:US-XNAS-NVDA" if ticker.upper() == "NVDA" else None
        ),
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: (
            store_mod.NewsReadRights.all_internal() if rights else None
        ),
    )
    monkeypatch.setattr(
        ticker_news,
        "_source_health",
        lambda: {
            "state": "live",
            "last_successful_catchup": "2026-10-05T20:00:00+00:00",
        },
    )
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
        "id": "user-1",
        "email": "user@example.test",
    }
    return ticker_news, app, db


def test_snapshot_is_authenticated_private_and_returns_cluster_rows(monkeypatch, tmp_path):
    ticker_news, app, _db = _app(monkeypatch, tmp_path)
    response = TestClient(app).get("/api/ticker-news/NVDA?limit=20")

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "ticker_news.snapshot.v1"
    assert body["ticker"] == "NVDA"
    assert body["security_id"] == "SEC:US-XNAS-NVDA"
    assert body["state"] == "live"
    assert len(body["rows"]) == 1
    assert isinstance(body["rows"][0]["story_id"], str)
    assert body["rows"][0]["story_id"]
    assert body["rows"][0]["title"] == "Nvidia launches accelerator"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def test_auth_denial_happens_before_store_open(monkeypatch, tmp_path):
    from app import ticker_news

    opened = []
    monkeypatch.setattr(
        ticker_news,
        "_open_store",
        lambda: opened.append(True),
    )
    app = FastAPI()
    app.include_router(ticker_news.router)

    def deny():
        raise HTTPException(status_code=401, detail="authentication required")

    app.dependency_overrides[ticker_news.require_site_full_user] = deny
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 401
    assert opened == []


def test_unknown_source_rights_fail_closed_before_store_open(monkeypatch, tmp_path):
    from app import ticker_news

    opened = []
    monkeypatch.setattr(ticker_news, "_rights_for_user", lambda user: None)
    monkeypatch.setattr(ticker_news, "_open_store", lambda: opened.append(True))
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {"id": "u"}

    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 503
    assert response.json()["detail"] == "ticker news rights unavailable"
    assert opened == []


def test_unknown_ticker_is_404_without_guessing_security_id(monkeypatch, tmp_path):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path)
    response = TestClient(app).get("/api/ticker-news/ZZZZ")

    assert response.status_code == 404
    assert response.json()["detail"] == "ticker not in qualified news universe"


def test_changes_are_ticker_scoped_and_resume_after_sequence(monkeypatch, tmp_path):
    ticker_news, app, db = _app(monkeypatch, tmp_path)
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(item_id=2, title="Nvidia second story", minute=2)],
            expected_cursor="c1",
            next_cursor="c2",
        )

    response = TestClient(app).get(
        "/api/ticker-news/NVDA/changes?after_sequence=1&limit=20"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "ticker_news.changes.v1"
    assert body["ticker"] == "NVDA"
    assert [row["source_item_id"] for row in body["rows"]] == ["2"]
    assert body["next_sequence"] == body["rows"][-1]["sequence"]


def test_story_detail_respects_store_rights_and_missing_story_is_404(monkeypatch, tmp_path):
    ticker_news, app, db = _app(monkeypatch, tmp_path)
    with store_mod.NewsStore.open_readonly(db, source_key="benzinga-rest") as store:
        story_id = store.snapshot(
            "SEC:US-XNAS-NVDA",
            limit=10,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        ).rows[0].story_id

    ok = TestClient(app).get(f"/api/ticker-news/stories/{story_id}")
    missing = TestClient(app).get("/api/ticker-news/stories/cluster_missing")

    assert ok.status_code == 200
    assert ok.json()["schema"] == "ticker_news.story.v1"
    assert ok.json()["story_id"] == story_id
    assert ok.json()["item_count"] == 1
    assert missing.status_code == 404


def test_store_unavailable_is_503_not_empty_200(monkeypatch, tmp_path):
    from app import ticker_news

    monkeypatch.setattr(
        ticker_news,
        "_news_db_path",
        lambda: tmp_path / "missing.sqlite3",
    )
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: "SEC:US-XNAS-NVDA",
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: store_mod.NewsReadRights.all_internal(),
    )
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {"id": "u"}

    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 503
    assert response.json()["detail"] == "ticker news temporarily unavailable"


def test_sse_cycle_rechecks_rights_and_emits_removal_before_stopping(monkeypatch, tmp_path):
    from app import ticker_news

    db = _make_db(tmp_path)
    decisions = [
        store_mod.NewsReadRights.all_internal(),
        None,
    ]
    monkeypatch.setattr(
        ticker_news,
        "_news_db_path",
        lambda: db,
    )
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: "SEC:US-XNAS-NVDA",
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: decisions.pop(0),
    )

    async def collect():
        out = []
        async for chunk in ticker_news._sse_events(
            ticker="NVDA",
            user={"id": "u"},
            after_sequence=0,
            poll_seconds=0,
            max_cycles=2,
        ):
            out.append(chunk)
        return out

    chunks = asyncio.run(collect())
    joined = "".join(chunks)

    assert "event: upsert" in joined
    assert "Nvidia launches accelerator" in joined
    assert "event: restricted" in joined
    assert "ticker news rights unavailable" in joined


def test_rate_limit_is_bounded_per_authenticated_user(monkeypatch, tmp_path):
    ticker_news, app, _db = _app(monkeypatch, tmp_path)
    monkeypatch.setattr(ticker_news, "_RATE_LIMIT_REQUESTS", 2)
    client = TestClient(app)

    assert client.get("/api/ticker-news/NVDA").status_code == 200
    assert client.get("/api/ticker-news/NVDA").status_code == 200
    third = client.get("/api/ticker-news/NVDA")

    assert third.status_code == 429
    assert third.headers["retry-after"] == "60"


def test_live_source_with_no_ticker_rows_reports_quiet(monkeypatch, tmp_path):
    from app import ticker_news

    db = tmp_path / "q.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest"):
        pass
    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: "SEC:US-XNAS-NVDA",
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: store_mod.NewsReadRights.all_internal(),
    )
    monkeypatch.setattr(ticker_news, "_source_health", lambda: {"state": "live"})
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {"id": "u"}

    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    assert response.json()["state"] == "quiet"


def test_production_app_mounts_all_private_ticker_news_routes() -> None:
    import app.main as main_mod

    paths = main_mod.app.openapi().get("paths", {})
    expected = {
        "/api/ticker-news/{ticker}",
        "/api/ticker-news/{ticker}/changes",
        "/api/ticker-news/{ticker}/stream",
        "/api/ticker-news/stories/{story_id}",
    }
    assert expected <= set(paths)

    client = TestClient(main_mod.app, raise_server_exceptions=False)
    # Every paid news route must hit authentication, never fall through to a 404.
    assert client.get("/api/ticker-news/NVDA").status_code == 401
    assert client.get("/api/ticker-news/NVDA/changes").status_code == 401
    assert client.get("/api/ticker-news/NVDA/stream").status_code == 401
    assert client.get("/api/ticker-news/stories/ev2_missing").status_code == 401


def test_snapshot_default_initial_page_is_twenty(monkeypatch, tmp_path):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path)
    seen = []
    original = store_mod.NewsStore.snapshot

    def wrapped(self, security_id, *, limit, cursor, rights):
        seen.append(limit)
        return original(
            self,
            security_id,
            limit=limit,
            cursor=cursor,
            rights=rights,
        )

    monkeypatch.setattr(store_mod.NewsStore, "snapshot", wrapped)
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    assert seen == [20]
