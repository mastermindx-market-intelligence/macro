"""N0 Q5 gap: expired snapshot cursor and reconnect change catch-up (SERVER).

The task matrix (research/product_intelligence_local_delivery/N0_TICKER_NEWS_TASK_MATRIX_2026-10-06.md)
marks "Expired cursor / reconnect gap" as NOT COVERED at the API read plane. Ingest gap tests
exist; these pin the user-visible pagination and changes resume behavior.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

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


def _make_db(tmp_path, *, stories: int = 1) -> Path:
    db = tmp_path / "q.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        cursor = None
        for item_id in range(1, stories + 1):
            store.commit(
                [_routed(item_id=item_id, title=f"Story {item_id}", minute=item_id)],
                expected_cursor=cursor,
                next_cursor=f"c{item_id}",
            )
            cursor = f"c{item_id}"
    return db


def _app(monkeypatch, tmp_path, *, db=None):
    from app import ticker_news

    if db is None:
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
        lambda user: store_mod.NewsReadRights.all_internal(),
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
    return app, db


def test_expired_snapshot_cursor_returns_empty_honest_page(monkeypatch, tmp_path):
    """A stale pagination cursor below live history must not 422 or replay wrong rows."""
    app, _db = _app(monkeypatch, tmp_path, db=_make_db(tmp_path, stories=3))
    client = TestClient(app)

    live = client.get("/api/ticker-news/NVDA?limit=20")
    assert live.status_code == 200
    assert len(live.json()["rows"]) == 3

    expired = client.get("/api/ticker-news/NVDA?cursor=1&limit=20")
    assert expired.status_code == 200
    body = expired.json()
    assert body["schema"] == "ticker_news.snapshot.v1"
    assert body["rows"] == []
    assert body["has_more"] is False
    assert body["next_cursor"] == 1
    assert "flow" not in body


def test_reconnect_gap_changes_resume_without_duplicates(monkeypatch, tmp_path):
    """After new commits while disconnected, changes?after_sequence= resumes forward only."""
    app, db = _app(monkeypatch, tmp_path, db=_make_db(tmp_path, stories=1))
    client = TestClient(app)

    first = client.get("/api/ticker-news/NVDA/changes?after_sequence=0&limit=20")
    assert first.status_code == 200
    seq_after_first = first.json()["next_sequence"]
    assert seq_after_first >= 1

    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(item_id=2, title="Story 2", minute=2)],
            expected_cursor="c1",
            next_cursor="c2",
        )
        store.commit(
            [_routed(item_id=3, title="Story 3", minute=3)],
            expected_cursor="c2",
            next_cursor="c3",
        )

    catch_up = client.get(
        f"/api/ticker-news/NVDA/changes?after_sequence={seq_after_first}&limit=20"
    )
    assert catch_up.status_code == 200
    body = catch_up.json()
    ids = [row["source_item_id"] for row in body["rows"]]
    assert ids == ["2", "3"]
    assert body["next_sequence"] == body["rows"][-1]["sequence"]

    replay = client.get(
        f"/api/ticker-news/NVDA/changes?after_sequence={seq_after_first}&limit=20"
    )
    assert [row["source_item_id"] for row in replay.json()["rows"]] == ids
