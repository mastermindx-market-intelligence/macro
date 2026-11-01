"""Authenticated B03 source delivery; no query or disk work before entitlement."""
from __future__ import annotations

import importlib
import importlib.util
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from scripts.build_turn_watch import write_candidate_episode_input
from tests.test_prophet_early_observations import seed

URL = "/api/prophet/observations/v1"


def test_observation_route_is_available():
    assert importlib.util.find_spec("app.prophet_observations"), "B03 authenticated delivery is absent"


def test_optional_observation_runtime_does_not_break_app_startup_or_auth(tmp_path):
    """An eager B03 import must not make every API require the parquet runtime."""
    probe = r'''
import builtins
import sys

real_import = builtins.__import__
def without_parquet(name, *args, **kwargs):
    if name.split('.', 1)[0] == 'pyarrow':
        raise ModuleNotFoundError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = without_parquet

from fastapi.testclient import TestClient
import app.main as main
import app.prophet_observations as observations

assert 'engine.prophet_early_observations' not in sys.modules
client = TestClient(main.app)
denied = client.get('/api/prophet/observations/v1?limit=invalid')
assert denied.status_code == 401, denied.text
assert denied.headers['cache-control'] == 'private, no-store'
assert 'engine.prophet_early_observations' not in sys.modules

main.app.dependency_overrides[observations.require_site_full_user] = lambda: {'id': 'paid-fixture'}
unavailable = client.get('/api/prophet/observations/v1')
assert unavailable.status_code == 503, unavailable.text
assert unavailable.json() == {'error': 'OBSERVATIONS_UNAVAILABLE'}
assert unavailable.headers['cache-control'] == 'private, no-store'
assert unavailable.headers['vary'] == 'Authorization'
assert 'pyarrow' not in unavailable.text
'''
    environment = os.environ.copy()
    environment["BIOCATALYST_PUBLIC_ROOT"] = str(tmp_path / "not-provisioned")
    result = subprocess.run(
        [sys.executable, "-c", probe], cwd=Path(__file__).resolve().parents[1],
        env=environment, capture_output=True, text=True, timeout=45, check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def route(monkeypatch, tmp_path):
    mod = importlib.import_module("app.prophet_observations")
    monkeypatch.setattr(mod, "_DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(mod, "expected_last_session", lambda: date(2026, 10, 8))
    return mod


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


@pytest.fixture
def client(route):
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"id": "paid-fixture"}
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("denial", [401, 403])
def test_real_auth_chain_denies_before_query_or_source_read(route, monkeypatch, denial):
    import app.main as main
    import app.paywall as paywall

    calls = []
    def authenticate(_authorization):
        calls.append("authenticate")
        if denial == 401:
            raise HTTPException(401, "missing bearer token")
        return {"id": "free-fixture"}
    def entitle(_user, *, always=False):
        assert always is True
        calls.append("entitle")
        raise HTTPException(403, "site_full required")
    def source_read(*args, **kwargs):
        pytest.fail("denied user must not read the source")
    monkeypatch.setattr(main, "require_user", authenticate)
    monkeypatch.setattr(paywall, "enforce_site_full", entitle)
    monkeypatch.setattr(route, "read_current_observations", source_read)
    app = FastAPI()
    app.include_router(route.router)
    with TestClient(app) as c:
        response = c.get(URL + "?limit=invalid&ticker=../private")
    assert response.status_code == denial
    assert calls == (["authenticate"] if denial == 401 else ["authenticate", "entitle"])
    private(response)


def test_exact_search_reads_uncapped_source_on_each_request(client, tmp_path):
    path, _, rows, artifact = seed(tmp_path, tuple(f"N{i:03}" for i in range(60)) + ("AMZN",))
    response = client.get(URL, params={"security_id": "SEC:US-XNAS-AMZN", "limit": "1"})
    assert response.status_code == 200
    first = response.json()
    assert first["market"] == "US"
    assert first["reference_session"] == "2026-10-08"
    assert first["counts"] == {"source": 61, "matched": 1, "returned": 1}
    assert first["rows"][0]["ticker"] == "AMZN"
    assert all(v is False for v in first["rows"][0]["authority"].values())
    assert first["clocks"]["actual_clock_state"] == "NOT_RECORDED"
    assert str(tmp_path) not in response.text
    private(response)
    # Existing producer publishes a new receipt: no service restart/static rebuild.
    rows.pop()
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    response = client.get(URL, params={"ticker": "AMZN"})
    assert response.json()["counts"] == {"source": 60, "matched": 0, "returned": 0}
    conflict = client.get(URL, params={"snapshot": first["snapshot_id"], "offset": "1"})
    assert conflict.status_code == 409
    assert conflict.json()["error"] == "SNAPSHOT_CHANGED"
    private(conflict)


@pytest.mark.parametrize("query", [
    "?limit=0", "?offset=-1", "?ticker=AMZN*", "?limit=1&limit=2",
    "?root=/private", "?security_id=../AMZN", "?offset=" + "9" * 100,
])
def test_bad_queries_are_private_and_do_not_read_source(client, route, monkeypatch, query):
    monkeypatch.setattr(route, "read_current_observations",
                        lambda: pytest.fail("invalid query reached source"))
    response = client.get(URL + query)
    assert response.status_code == 400
    private(response)


def test_missing_source_is_not_empty_success(client):
    response = client.get(URL)
    assert response.status_code == 503
    assert response.json()["status"] == "UNAVAILABLE"
    assert response.json()["counts"]["source"] is None
    private(response)


def test_prior_source_retained_but_corrupt_latest_does_not_fall_back(client, tmp_path):
    seed(tmp_path, session="2026-10-06")
    prior = client.get(URL).json()
    assert prior["status"] == "RETAINED_PREVIOUS_SESSION"
    source, _, _, _ = seed(tmp_path)
    source.write_text("{broken")
    response = client.get(URL)
    assert response.status_code == 503
    assert response.json()["rows"] == []
    assert response.json()["reason"] == "SOURCE_MALFORMED"


def test_missing_identity_retains_ticker_and_future_source_is_not_delivered(client, tmp_path):
    old, _, _, _ = seed(tmp_path, session="2026-10-06")
    seed(tmp_path, tickers=("FUTURE",), session="2026-10-09")
    for path in (tmp_path / "data/reference").glob("*.parquet"):
        path.unlink()
    body = client.get(URL, params={"ticker": "AMZN"}).json()
    assert [r["ticker"] for r in body["rows"]] == ["AMZN"]
    assert body["rows"][0]["security_id"] is None
    assert body["status"] == "RETAINED_PREVIOUS_SESSION"


def test_filename_session_mismatch_is_unavailable(client, tmp_path):
    source, _, _, _ = seed(tmp_path, session="2026-10-06")
    source.rename(source.with_name("2026-10-08.json"))
    response = client.get(URL)
    assert response.status_code == 503
    assert response.json()["reason"] == "SOURCE_SESSION_MISMATCH"


def test_router_is_mounted_on_actual_application(route):
    import app.main as main
    previous = dict(main.app.dependency_overrides)
    main.app.dependency_overrides[route.require_site_full_user] = lambda: {"id": "paid-fixture"}
    try:
        response = TestClient(main.app).get(URL)
        assert response.status_code == 503  # Mounted, but the source is absent.
        assert response.json()["status"] == "UNAVAILABLE"
        private(response)
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous)
