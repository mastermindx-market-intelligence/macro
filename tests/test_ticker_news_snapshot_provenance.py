"""Additive snapshot provenance: universe_known_at and rights_basis (W11-07).

The two keys must come from the gating reads the snapshot route already makes
(one universe read, two rights-receipt reads per request) and must be null when
a test has patched the legacy seams. The parent snapshot key set is pinned so
the change stays strictly additive.
"""
from __future__ import annotations

import builtins
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from engine import qbus_news_store as store_mod
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_receipts import load_rights_receipt


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
_SECURITY_NVDA = "SEC:US-XNAS-NVDA"
_TITLE = "Nvidia launches accelerator"

RIGHTS_FILE = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "ticker_news_rights_alpaca_benzinga.json"
)

# Read from _snapshot_payload at the parent (app/ticker_news.py): the snapshot
# key set before W11-07, plus the optional first-page "flow" key.
PARENT_KEYS = frozenset(
    {
        "schema",
        "ticker",
        "security_id",
        "state",
        "rows",
        "next_cursor",
        "has_more",
        "source_health",
        "annotations",
    }
)

# Measured at the parent: one snapshot request reads the universe file once and
# the rights receipt file twice (rights gate + derivative gate).
MEASURED_PARENT_READS = {"universe": 1, "receipt": 2}


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def _z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _rights(now: datetime, **overrides) -> dict:
    payload = {
        "schema": "qbus.news_rights_receipt.v1",
        "receipt_id": "receipt-fixture-provenance",
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
    payload.update(overrides)
    return payload


def _universe(
    now: datetime,
    *,
    known_at: datetime | None = None,
    fresh_until: datetime | None = None,
) -> dict:
    known = now - timedelta(minutes=1) if known_at is None else known_at
    fresh = now + timedelta(days=1) if fresh_until is None else fresh_until
    return {
        "owner": "fixture.security_reference",
        "revision": "fixture-r1",
        "complete": True,
        "truncated": False,
        "effective_at": _iso(now - timedelta(days=1)),
        "known_at": _iso(known),
        "fresh_until": _iso(fresh),
        "securities": [
            {
                "security_id": _SECURITY_NVDA,
                "ticker": "NVDA",
                "aliases": ["NVDA"],
                "valid_from": _iso(now - timedelta(days=100)),
                "valid_to": None,
                "known_at": _iso(known),
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


def _arm(
    monkeypatch,
    tmp_path: Path,
    *,
    rights_payload: dict | None = None,
    rights_file: Path | None = None,
    universe_payload: dict | None = None,
):
    from app import ticker_news

    now = datetime.now(UTC)
    db = _make_db(tmp_path)
    monkeypatch.setenv("MM_TICKER_NEWS_DB", str(db))
    if rights_file is not None:
        monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(rights_file))
    else:
        rights_path = tmp_path / "rights.json"
        _write(rights_path, rights_payload or _rights(now))
        monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(rights_path))
    universe_path = tmp_path / "universe.json"
    _write(universe_path, universe_payload or _universe(now))
    monkeypatch.setenv("MM_TICKER_NEWS_UNIVERSE", str(universe_path))
    monkeypatch.delenv("MM_TICKER_NEWS_HEALTH", raising=False)
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
        "id": "user-provenance",
        "email": "user@example.test",
    }
    return {
        "ticker_news": ticker_news,
        "client": TestClient(app),
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


def _patch_seams(monkeypatch, surface) -> None:
    ticker_news = surface["ticker_news"]
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: _SECURITY_NVDA,
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: store_mod.NewsReadRights.all_internal(),
    )


def test_snapshot_keys_are_strict_superset(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    response = surface["client"].get("/api/ticker-news/NVDA")
    assert response.status_code == 200, response.text
    keys = set(response.json())
    assert PARENT_KEYS < keys
    assert keys - PARENT_KEYS == {"universe_known_at", "rights_basis", "flow", "change_sequence", "editorial_policy"}


def test_provenance_exact_values_against_committed_receipt(monkeypatch, tmp_path):
    now = datetime.now(UTC)
    surface = _arm(monkeypatch, tmp_path, rights_file=RIGHTS_FILE)
    response = surface["client"].get("/api/ticker-news/NVDA")
    assert response.status_code == 200, response.text
    body = response.json()

    expected = load_rights_receipt(RIGHTS_FILE, now=now, audience="site_full")
    assert expected is not None  # real now is inside the committed window
    assert body["rights_basis"] == {
        "receipt_id": expected.receipt_id,
        "source": expected.source,
        "provider": expected.provider,
        "effective_at": _z(expected.effective_at),
        "expires_at": _z(expected.expires_at),
    }
    assert "owner_ref" not in body["rights_basis"]
    assert "product_id" not in body["rights_basis"]
    assert "audience" not in body["rights_basis"]
    assert body["universe_known_at"] == _z(now - timedelta(minutes=1))


def test_stale_universe_surfaces_its_known_at(monkeypatch, tmp_path):
    now = datetime.now(UTC)
    stale_known_at = now - timedelta(days=3)
    surface = _arm(
        monkeypatch,
        tmp_path,
        universe_payload=_universe(now, known_at=stale_known_at),
    )
    response = surface["client"].get("/api/ticker-news/NVDA")
    assert response.status_code == 200, response.text
    assert response.json()["universe_known_at"] == _z(stale_known_at)


def test_expired_receipt_still_503(monkeypatch, tmp_path):
    now = datetime.now(UTC)
    surface = _arm(
        monkeypatch,
        tmp_path,
        rights_payload=_rights(
            now,
            receipt_id="receipt-fixture-expired-provenance",
            effective_at=_iso(now - timedelta(days=3)),
            expires_at=_iso(now - timedelta(seconds=5)),
        ),
    )
    response = surface["client"].get("/api/ticker-news/NVDA")
    assert response.status_code == 503
    assert response.json()["detail"] == "ticker news rights unavailable"
    _assert_private(response)


def test_patched_seams_give_null_provenance(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    _patch_seams(monkeypatch, surface)
    response = surface["client"].get("/api/ticker-news/NVDA")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "universe_known_at" in body
    assert body["universe_known_at"] is None
    assert "rights_basis" in body
    assert body["rights_basis"] is None


def test_provenance_does_not_leak_between_requests(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    first = surface["client"].get("/api/ticker-news/NVDA")
    assert first.status_code == 200, first.text
    assert first.json()["universe_known_at"] is not None
    assert first.json()["rights_basis"] is not None

    _patch_seams(monkeypatch, surface)
    second = surface["client"].get("/api/ticker-news/NVDA")
    assert second.status_code == 200, second.text
    assert second.json()["universe_known_at"] is None
    assert second.json()["rights_basis"] is None


def test_reads_per_snapshot_request_unchanged(monkeypatch, tmp_path):
    surface = _arm(monkeypatch, tmp_path)
    ticker_news = surface["ticker_news"]
    universe_path = Path(ticker_news._universe_path())
    rights_path = Path(ticker_news._rights_receipt_path())
    counts = {"universe": 0, "receipt": 0}

    def key_of(path) -> str | None:
        try:
            resolved = str(Path(path).resolve())
        except (OSError, TypeError, ValueError):
            return None
        if resolved == str(universe_path.resolve()):
            return "universe"
        if resolved == str(rights_path.resolve()):
            return "receipt"
        return None

    real_read_text = Path.read_text
    real_read_bytes = Path.read_bytes
    real_open = builtins.open

    def counting_read_text(self, *args, **kwargs):
        key = key_of(self)
        if key is not None:
            counts[key] += 1
        return real_read_text(self, *args, **kwargs)

    def counting_read_bytes(self, *args, **kwargs):
        key = key_of(self)
        if key is not None:
            counts[key] += 1
        return real_read_bytes(self, *args, **kwargs)

    def counting_open(file, *args, **kwargs):
        key = key_of(file)
        if key is not None:
            counts[key] += 1
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)
    monkeypatch.setattr(Path, "read_bytes", counting_read_bytes)
    monkeypatch.setattr(builtins, "open", counting_open)

    response = surface["client"].get("/api/ticker-news/NVDA")
    assert response.status_code == 200, response.text
    assert counts == MEASURED_PARENT_READS
