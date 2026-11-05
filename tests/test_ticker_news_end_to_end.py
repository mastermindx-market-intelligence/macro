"""Synthetic source -> qbus store -> private API end-to-end qualification."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import ticker_news
from collectors import benzinga_news
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_receipts import write_health_receipt
from engine.qbus_news_store import NewsStore
from engine.qbus_news_universe import qualify_universe


UTC = timezone.utc
T0 = datetime.now(UTC) - timedelta(seconds=10)


def _universe_payload() -> dict:
    return {
        "owner": "test.security_reference.sp500",
        "revision": "synthetic-sp500-r1",
        "complete": True,
        "truncated": False,
        "effective_at": (T0 - timedelta(days=1)).isoformat(),
        "known_at": (T0 - timedelta(minutes=1)).isoformat(),
        "fresh_until": (T0 + timedelta(days=1)).isoformat(),
        "securities": [
            {
                "security_id": "SEC:US-XNAS-NVDA",
                "ticker": "NVDA",
                "aliases": ["NVDA"],
                "valid_from": (T0 - timedelta(days=100)).isoformat(),
                "valid_to": None,
                "known_at": (T0 - timedelta(minutes=1)).isoformat(),
            },
            {
                "security_id": "SEC:US-XNAS-AVGO",
                "ticker": "AVGO",
                "aliases": ["AVGO"],
                "valid_from": (T0 - timedelta(days=100)).isoformat(),
                "valid_to": None,
                "known_at": (T0 - timedelta(minutes=1)).isoformat(),
            },
        ],
    }


def _rights(now: datetime, *, approved: bool = True) -> dict:
    return {
        "schema": "qbus.news_rights_receipt.v1",
        "receipt_id": "synthetic-rights",
        "owner_ref": "test/source-rights",
        "status": "approved" if approved else "denied",
        "source": "benzinga",
        "product_id": "synthetic-benzinga-commercial",
        "audiences": ["site_full"],
        "effective_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": True,
            "teaser_display": True,
            "body_display": False,
            "image_display": False,
            "derivative_processing": False,
        },
    }


def _health(now: datetime) -> dict:
    return {
        "schema": "qbus.news_health.v1",
        "source": "benzinga",
        "state": "live",
        "observed_at": now.isoformat(),
        "last_successful_catchup": (now - timedelta(seconds=1)).isoformat(),
        "last_stream_event_at": None,
        "gap_unresolved": False,
        "connect_attempts": 1,
        "disconnects": 0,
        "catchups_failed": 0,
    }


def _article(
    *,
    item_id: int,
    title: str,
    updated_at: datetime,
    ticker: str,
) -> dict:
    return {
        "id": item_id,
        "created": (updated_at - timedelta(minutes=1)).isoformat(),
        "updated": updated_at.isoformat(),
        "title": title,
        "teaser": f"teaser:{title}",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "stocks": [{"name": ticker}],
        "channels": [{"name": "News"}],
        "tags": [{"name": "breaking"}],
    }


def _removed(*, item_id: int, updated_at: datetime) -> dict:
    return {
        "id": item_id,
        "action": "removed",
        "updated": updated_at.isoformat(),
    }


class DeltaClient:
    def __init__(self, batches):
        self.batches = list(batches)

    def fetch_delta(self, *, cursor_epoch, observed_at):
        assert self.batches, "unexpected extra delta fetch"
        revisions = self.batches.pop(0)
        return benzinga_news.DeltaBatch(
            revisions=tuple(revisions),
            query_since_epoch=max(0, (cursor_epoch or 0) - 2),
            next_cursor_epoch=int(observed_at.timestamp()),
            gap_unresolved=False,
            hold_reasons=(),
            news_pages=1,
            removed_pages=1,
        )


def _normalize_article(payload: dict, received_at: datetime):
    return normalize_news(
        payload,
        transport="benzinga_rest",
        received_at=received_at,
    )


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
        "id": "synthetic-user",
        "sub": "synthetic-user",
    }
    return app


@pytest.fixture
def composition(monkeypatch, tmp_path):
    db = tmp_path / "qbus.sqlite3"
    universe_path = tmp_path / "news_universe.json"
    rights_path = tmp_path / "rights.json"
    health_path = tmp_path / "health.json"

    universe_path.write_text(json.dumps(_universe_payload()), encoding="utf-8")
    rights_path.write_text(json.dumps(_rights(T0)), encoding="utf-8")
    write_health_receipt(health_path, _health(T0))

    with NewsStore(db, source_key="benzinga-rest"):
        pass

    monkeypatch.setenv("MM_TICKER_NEWS_DB", str(db))
    monkeypatch.setenv("MM_TICKER_NEWS_UNIVERSE", str(universe_path))
    monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(rights_path))
    monkeypatch.setenv("MM_TICKER_NEWS_HEALTH", str(health_path))
    monkeypatch.setattr(ticker_news, "_rate_or_429", lambda user: None)
    ticker_news._reset_rate_limit_for_tests()

    return {
        "db": db,
        "universe_path": universe_path,
        "rights_path": rights_path,
        "health_path": health_path,
        "client": TestClient(_app()),
    }


def test_source_store_api_restart_correction_reassignment_and_removal(composition):
    db = composition["db"]
    api = composition["client"]
    universe = qualify_universe(_universe_payload(), asof=T0)
    assert universe.status == "qualified"

    create = _normalize_article(
        _article(
            item_id=101,
            title="Nvidia launches new AI accelerator",
            updated_at=T0,
            ticker="NVDA",
        ),
        T0 + timedelta(seconds=1),
    )
    with NewsStore(db, source_key="benzinga-rest") as store:
        first = benzinga_news.catch_up_once(
            client=DeltaClient([(create,)]),
            store=store,
            universe=universe,
            observed_at=T0 + timedelta(seconds=2),
        )
        assert first.committed is True
        first_cursor = store.current_cursor()
        assert first_cursor is not None

    initial = api.get("/api/ticker-news/NVDA")
    assert initial.status_code == 200
    payload = initial.json()
    assert payload["state"] == "live"
    assert payload["rows"][0]["title"] == "Nvidia launches new AI accelerator"
    story_id = payload["rows"][0]["story_id"]
    first_sequence = payload["rows"][0]["sequence"]

    correction_time = T0 + timedelta(minutes=2)
    corrected = _normalize_article(
        _article(
            item_id=101,
            title="Broadcom named in corrected accelerator story",
            updated_at=correction_time,
            ticker="AVGO",
        ),
        correction_time + timedelta(seconds=1),
    )
    with NewsStore(db, source_key="benzinga-rest") as reopened:
        assert reopened.current_cursor() == first_cursor
        second = benzinga_news.catch_up_once(
            client=DeltaClient([(corrected,)]),
            store=reopened,
            universe=universe,
            observed_at=correction_time + timedelta(seconds=2),
        )
        assert second.committed is True
        assert reopened.current_cursor() != first_cursor

    old_ticker = api.get("/api/ticker-news/NVDA")
    assert old_ticker.status_code == 200
    assert old_ticker.json()["state"] == "quiet"
    assert old_ticker.json()["rows"] == []

    new_ticker = api.get("/api/ticker-news/AVGO")
    assert new_ticker.status_code == 200
    assert new_ticker.json()["rows"][0]["title"] == "Broadcom named in corrected accelerator story"

    changes_old = api.get(
        f"/api/ticker-news/NVDA/changes?after_sequence={first_sequence}"
    )
    assert changes_old.status_code == 200
    assert any(
        "SEC:US-XNAS-NVDA" in row["security_ids"]
        and "SEC:US-XNAS-AVGO" in row["security_ids"]
        for row in changes_old.json()["rows"]
    )

    detail = api.get(f"/api/ticker-news/stories/{story_id}")
    assert detail.status_code == 200
    assert detail.json()["members"][0]["title"] == "Broadcom named in corrected accelerator story"

    remove_time = T0 + timedelta(minutes=4)
    removed = _normalize_article(
        _removed(item_id=101, updated_at=remove_time),
        remove_time + timedelta(seconds=1),
    )
    with NewsStore(db, source_key="benzinga-rest") as reopened:
        third = benzinga_news.catch_up_once(
            client=DeltaClient([(removed,)]),
            store=reopened,
            universe=universe,
            observed_at=remove_time + timedelta(seconds=2),
        )
        assert third.committed is True

    after_remove = api.get("/api/ticker-news/AVGO")
    assert after_remove.status_code == 200
    assert after_remove.json()["state"] == "quiet"
    assert after_remove.json()["rows"] == []
    assert api.get(f"/api/ticker-news/stories/{story_id}").status_code == 404


def test_midstream_rights_revocation_emits_restricted_and_stops(composition):
    rights_path = composition["rights_path"]

    async def run():
        stream = ticker_news._sse_events(
            ticker="NVDA",
            user={"id": "synthetic-user"},
            after_sequence=999999,
            poll_seconds=0,
            max_cycles=3,
        )
        first = await anext(stream)
        assert first == ": heartbeat\n\n"

        rights_path.write_text(
            json.dumps(_rights(datetime.now(UTC), approved=False)),
            encoding="utf-8",
        )
        second = await anext(stream)
        assert "event: restricted" in second
        with pytest.raises(StopAsyncIteration):
            await anext(stream)

    asyncio.run(run())


def test_disk_full_rolls_back_revision_state_index_and_cursor(monkeypatch, tmp_path):
    db = tmp_path / "qbus.sqlite3"
    universe = qualify_universe(_universe_payload(), asof=T0)
    revision = _normalize_article(
        _article(
            item_id=202,
            title="Synthetic disk-full story",
            updated_at=T0,
            ticker="NVDA",
        ),
        T0 + timedelta(seconds=1),
    )

    original = NewsStore._persist_revision

    def disk_full(self, incoming):
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(NewsStore, "_persist_revision", disk_full)
    with NewsStore(db, source_key="benzinga-rest") as store:
        with pytest.raises(sqlite3.OperationalError, match="disk is full"):
            benzinga_news.catch_up_once(
                client=DeltaClient([(revision,)]),
                store=store,
                universe=universe,
                observed_at=T0 + timedelta(seconds=2),
            )
        assert store.current_cursor() is None
        assert store.counts()["revisions"] == 0
        assert store.counts()["states"] == 0
        assert store.counts()["security_index"] == 0
        assert store.counts()["changes"] == 0

    monkeypatch.setattr(NewsStore, "_persist_revision", original)
