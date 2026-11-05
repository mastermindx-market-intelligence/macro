"""Binding tests for ticker-news rights and health receipts at the Macro API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json


UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def _rights(now: datetime, **overrides):
    payload = {
        "schema": "qbus.news_rights_receipt.v1",
        "receipt_id": "rights-a",
        "owner_ref": "source-rights/BENZINGA-A",
        "status": "approved",
        "source": "benzinga",
        "product_id": "benzinga-newsfeed-commercial",
        "audiences": ["site_full"],
        "effective_at": _iso(now - timedelta(days=1)),
        "expires_at": _iso(now + timedelta(days=30)),
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": True,
            "teaser_display": False,
            "body_display": False,
            "image_display": False,
            "derivative_processing": False,
        },
    }
    payload.update(overrides)
    return payload


def _health(now: datetime, **overrides):
    payload = {
        "schema": "qbus.news_health.v1",
        "source": "benzinga",
        "state": "live",
        "observed_at": _iso(now - timedelta(seconds=3)),
        "last_successful_catchup": _iso(now - timedelta(seconds=8)),
        "last_stream_event_at": None,
        "gap_unresolved": False,
        "connect_attempts": 1,
        "disconnects": 0,
        "catchups_failed": 0,
    }
    payload.update(overrides)
    return payload


def test_api_rights_binding_is_off_without_receipt_path(monkeypatch):
    from app import ticker_news

    monkeypatch.delenv("MM_TICKER_NEWS_RIGHTS", raising=False)
    assert ticker_news._rights_for_user({"id": "u"}) is None


def test_api_rights_binding_maps_valid_owner_receipt(monkeypatch, tmp_path):
    from app import ticker_news

    now = datetime.now(UTC)
    path = tmp_path / "rights.json"
    path.write_text(json.dumps(_rights(now)), encoding="utf-8")
    monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(path))

    rights = ticker_news._rights_for_user({"id": "u"})

    assert rights is not None
    assert rights.allowed_sources == frozenset({"benzinga"})
    assert rights.allow_title is True
    assert rights.allow_url is True
    assert rights.allow_teaser is False


def test_api_rights_binding_fails_closed_on_expired_receipt(monkeypatch, tmp_path):
    from app import ticker_news

    now = datetime.now(UTC)
    path = tmp_path / "rights.json"
    path.write_text(
        json.dumps(
            _rights(
                now,
                effective_at=_iso(now - timedelta(days=2)),
                expires_at=_iso(now - timedelta(seconds=1)),
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(path))

    assert ticker_news._rights_for_user({"id": "u"}) is None


def test_api_health_binding_is_unavailable_without_receipt_path(monkeypatch):
    from app import ticker_news

    monkeypatch.delenv("MM_TICKER_NEWS_HEALTH", raising=False)
    health = ticker_news._source_health()
    assert health["state"] == "unavailable"
    assert health["reason"] == "receipt_path_unset"


def test_api_health_binding_reads_fresh_runtime_receipt(monkeypatch, tmp_path):
    from app import ticker_news

    now = datetime.now(UTC)
    path = tmp_path / "health.json"
    path.write_text(json.dumps(_health(now)), encoding="utf-8")
    monkeypatch.setenv("MM_TICKER_NEWS_HEALTH", str(path))

    health = ticker_news._source_health()

    assert health["state"] == "live"
    assert health["reason"] == "fresh"
    assert health["last_successful_catchup"] is not None


def test_api_health_binding_downgrades_stale_catchup(monkeypatch, tmp_path):
    from app import ticker_news

    now = datetime.now(UTC)
    path = tmp_path / "health.json"
    path.write_text(
        json.dumps(
            _health(
                now,
                observed_at=_iso(now - timedelta(seconds=3)),
                last_successful_catchup=_iso(now - timedelta(minutes=10)),
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MM_TICKER_NEWS_HEALTH", str(path))

    health = ticker_news._source_health()

    assert health["state"] == "degraded"
    assert health["reason"] == "catchup_stale"

def test_api_universe_path_defaults_to_derived_qbus_artifact(monkeypatch, tmp_path):
    from app import ticker_news

    monkeypatch.delenv("MM_TICKER_NEWS_UNIVERSE", raising=False)
    monkeypatch.setattr(ticker_news.config, "data_dir", lambda: tmp_path)

    assert ticker_news._universe_path() == tmp_path / "qbus" / "news_universe.json"


def test_api_universe_path_env_override_wins(monkeypatch, tmp_path):
    from app import ticker_news

    custom = tmp_path / "custom-universe.json"
    monkeypatch.setenv("MM_TICKER_NEWS_UNIVERSE", str(custom))

    assert ticker_news._universe_path() == custom
