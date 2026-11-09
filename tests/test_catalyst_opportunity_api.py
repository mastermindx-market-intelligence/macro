"""Entitled router boundary tests; test principals do not prove live entitlement."""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import catalyst_opportunity as route
from engine.catalyst_opportunity import reader
from engine.catalyst_opportunity.projection import build_opportunity_view

URL = "/api/catalyst-opportunities/v1"
NOW = datetime(2026, 10, 17, 15, tzinfo=timezone.utc)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"id": "test-only-principal"}
    with TestClient(app) as value:
        yield value


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"


def envelope():
    return build_opportunity_view({"schema":1, "region":"us", "as_of":"2026-10-16",
                                   "n_themes":0, "themes":[]},
                                  assessed_at=NOW, received_at=NOW)


@pytest.mark.parametrize("status", [401, 403])
def test_auth_precedes_even_invalid_query_and_source_read(client, monkeypatch, status):
    def denied():
        raise HTTPException(status, "test denial", headers=route._PRIVATE_HEADERS)
    client.app.dependency_overrides[route.require_site_full_user] = denied
    monkeypatch.setattr(reader, "read_current_view", lambda *_: pytest.fail("unauthorized read"))
    response = client.get(URL + "?path=/private&as_of=2020-01-01")
    assert response.status_code == status
    private(response)


@pytest.mark.parametrize("query", ["?as_of=2020-01-01", "?root=/private", "?x=1&x=2", "?theme=defense"])
def test_query_cannot_select_source_or_time(client, monkeypatch, query):
    monkeypatch.setattr(reader, "read_current_view", lambda *_: pytest.fail("invalid query read"))
    response = client.get(URL + query)
    assert response.status_code == 400
    private(response)


def test_success_is_exact_owner_generation(client, monkeypatch):
    data = envelope()
    seen = []
    def source(root):
        seen.append(root)
        return data
    monkeypatch.setattr(reader, "read_current_view", source)
    response = client.get(URL)
    assert response.status_code == 200 and response.json() == data
    assert seen == [route._REPO_ROOT]
    private(response)


def test_stale_remains_inspectable_and_never_restamped(client, monkeypatch):
    data = envelope()
    data["status"] = "stale"
    data["as_of"] = "2026-10-01"
    monkeypatch.setattr(reader, "read_current_view", lambda *_: data)
    response = client.get(URL)
    assert response.status_code == 200
    assert response.json()["as_of"] == "2026-10-01"
    private(response)


def test_unavailable_is_503_not_empty_healthy(client, monkeypatch):
    data = build_opportunity_view(None, assessed_at=NOW, received_at=NOW)
    monkeypatch.setattr(reader, "read_current_view", lambda *_: data)
    response = client.get(URL)
    assert response.status_code == 503 and response.json()["status"] == "unavailable"
    private(response)


def test_failure_sanitized_and_permit_released(client, monkeypatch):
    def broken(*_):
        raise RuntimeError("private provider token and /private/path")
    monkeypatch.setattr(reader, "read_current_view", broken)
    response = client.get(URL)
    assert response.status_code == 503
    assert response.json() == {"error":"CATALYST_UNAVAILABLE"}
    private(response)
    monkeypatch.setattr(reader, "read_current_view", lambda *_: envelope())
    assert client.get(URL).status_code == 200


def test_busy_does_not_queue_more_file_reads(client, monkeypatch):
    assert route._READ_ADMISSION.acquire(blocking=False)
    assert route._READ_ADMISSION.acquire(blocking=False)
    try:
        monkeypatch.setattr(reader, "read_current_view", lambda *_: pytest.fail("busy read"))
        response = client.get(URL)
        assert response.status_code == 503 and response.json()["error"] == "CATALYST_BUSY"
        private(response)
    finally:
        route._READ_ADMISSION.release()
        route._READ_ADMISSION.release()


def test_bad_serialization_is_private_failure(client, monkeypatch):
    monkeypatch.setattr(reader, "read_current_view", lambda *_: {"status":"ready", "bad":object()})
    response = client.get(URL)
    assert response.status_code == 503
    private(response)


def test_actual_app_mount_present():
    main = (Path(__file__).resolve().parents[1] / "app/main.py").read_text()
    assert "from app.catalyst_opportunity import router as catalyst_opportunity_router" in main
    assert "app.include_router(catalyst_opportunity_router)" in main
