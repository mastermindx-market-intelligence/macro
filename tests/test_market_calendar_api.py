"""Entitled API boundary. Fixture principals do not prove live access."""
import json
from datetime import datetime

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import market_calendar as route

URL = "/api/market-calendar/v1?from=2026-11-16&to=2026-11-22"


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"id": "fixture-only"}
    with TestClient(app) as value:
        yield value


@pytest.mark.parametrize("status", [401, 403])
def test_auth_precedes_query_and_private_file_read(client, monkeypatch, status):
    def denied():
        raise HTTPException(status, "fixture refusal", headers=route._PRIVATE_HEADERS)
    client.app.dependency_overrides[route.require_site_full_user] = denied
    monkeypatch.setattr(route, "read_json", lambda *_: pytest.fail("unauthorized private read"))
    response = client.get(URL + "&root=/private")
    assert response.status_code == status
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("query", ["", "?from=2026-02-31&to=2026-03-01",
    "?from=2026-11-01&to=2026-12-02", "?from=2026-11-16&to=2026-11-22&cursor=2000",
    "?from=2026-11-16&to=2026-11-22&from=2026-11-01", "?url=https://evil.invalid",
    "?from=2026-11-16junk&to=2026-11-22"])
def test_invalid_and_widened_queries_do_not_read(client, monkeypatch, query):
    monkeypatch.setattr(route, "read_json", lambda *_: pytest.fail("invalid query private read"))
    response = client.get("/api/market-calendar/v1" + query)
    assert response.status_code == 400


def test_private_artifact_is_read_per_request_and_not_network_fetched(client, monkeypatch, tmp_path):
    monkeypatch.setenv("MACRO_LIVE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("MACRO_LIVE_DIR", str(tmp_path))
    path = tmp_path / "market_calendar.json"
    snapshot = {"schema": "market-calendar.v1", "asOf": "2026-11-14T18:00:00+00:00",
                "from": "2026-11-02", "to": "2027-01-24", "events": [], "sources": [],
                "_ratios": {"private": "never export"}, "_yahoo_restricted": None}
    path.write_text(json.dumps(snapshot))
    response = client.get(URL)
    assert response.status_code == 200
    assert "_ratios" not in response.json()
    assert response.headers["cache-control"] == "private, no-store"
    before = response.json()["snapshotId"]
    snapshot["asOf"] = "2026-11-14T18:05:00+00:00"
    path.write_text(json.dumps(snapshot))
    assert client.get(URL).json()["snapshotId"] != before
    assert client.get(URL + "&cursor=1&revision=" + before).status_code == 503


def test_missing_or_malformed_artifact_is_unavailable_not_empty_success(client, monkeypatch, tmp_path):
    monkeypatch.setenv("MACRO_LIVE_STATE_DIR", str(tmp_path))
    assert client.get(URL).status_code == 503
    (tmp_path / "market_calendar.json").write_text("invalid private content")
    response = client.get(URL)
    assert response.status_code == 503
    assert response.json() == {"error": "CALENDAR_UNAVAILABLE"}


def test_current_publication_zero_and_withdrawal_update_without_rebuilding_calendar(client, monkeypatch, tmp_path):
    monkeypatch.setenv("MACRO_LIVE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("MACRO_LIVE_DIR", str(tmp_path))
    snapshot = {"schema": "market-calendar.v1", "asOf": "2026-11-14T18:00:00+00:00",
        "from": "2026-11-02", "to": "2027-01-24", "events": [], "sources": [],
        "_official_schedule": {"status": "ok", "asOf": "2026-11-14T18:00:00+00:00",
            "coverage": {"status": "ok", "horizon_days": 140}, "rows": [{
                "event_id": "claims:2026-11-19", "type": "CLAIMS", "date": "2026-11-19",
                "label": "Initial jobless claims", "schedule_source": "computed",
                "scheduled_at": "2026-11-19T08:30:00-05:00"}]}}
    (tmp_path / "market_calendar.json").write_text(json.dumps(snapshot))
    release = {"schema": "release_publications.v2", "built": "2026-11-19T13:31:00+00:00",
        "publications": [{"event_id": "claims:2026-11-19", "data_ready": True,
            "actual": {"metrics": [{"metric_id": "initial_claims", "value": 0, "unit": "claims"}]}}]}
    path = tmp_path / "release_publications.json"
    path.write_text(json.dumps(release))
    first = client.get(URL).json()
    assert first["events"][0]["economic"]["actual"] == 0
    assert first["sources"][0]["scheduleCoverage"]["horizon_days"] == 140
    release.update({"built": "2026-11-19T13:32:00+00:00", "events": [
        {"event_id": "claims:2026-11-19", "data_ready": False}]})
    path.write_text(json.dumps(release))
    second = client.get(URL).json()
    assert second["events"][0]["economic"]["actual"] is None
    assert second["snapshotId"] != first["snapshotId"]
    assert client.get(URL+"&cursor=1&revision="+first["snapshotId"]).status_code == 503
