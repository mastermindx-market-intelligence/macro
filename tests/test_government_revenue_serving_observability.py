"""Serving attribution is evidence only; these ASGI fixtures are not A42 load proof."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json
import re

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import government_revenue as api
from app.main import _NoStoreAPI
from engine.government_revenue.dossiers import dossier_content_id
from tests.test_government_revenue_dossiers import _write_sources, _write_dossier_twins


PATHS = ("/api/government-revenue/dossier/company/LMT", "/api/government-revenue/company/LMT/awards?limit=8")
HEADERS = ("x-govrev-generation", "x-govrev-cache", "x-govrev-process-epoch", "server-timing")
PHASES = {"govrev_stat", "govrev_lock_wait", "govrev_read_decode", "govrev_validate", "govrev_route"}


@pytest.fixture
def serving(tmp_path, monkeypatch):
    _write_sources(tmp_path)
    payload = _write_dossier_twins(tmp_path)
    paths = (tmp_path / "data/government_revenue/dossiers.json", tmp_path / "site/government-revenue-data/dossiers.json")
    monkeypatch.setattr(api, "_DOSSIER_PATHS", paths)
    monkeypatch.setattr(api, "_DOSSIER_CACHE", {"state": None, "payload": None})
    app = FastAPI()
    app.include_router(api.router)
    app.add_middleware(_NoStoreAPI)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "fixture-only"}
    with TestClient(app) as client:
        yield client, app, payload, paths


def _phases(response):
    parts = response.headers["server-timing"].split(", ")
    assert all(re.fullmatch(r"govrev_[a-z_]+;dur=\d+\.\d{3}", p) for p in parts)
    return {p.split(";dur=")[0]: float(p.split(";dur=")[1]) for p in parts}


@pytest.mark.parametrize("path", PATHS)
def test_cold_warm_and_body_identity(serving, monkeypatch, path):
    client, _, payload, _ = serving
    validate = api.is_valid_dossier_payload
    calls = []
    monkeypatch.setattr(api, "is_valid_dossier_payload", lambda p: calls.append(p["content_id"]) or validate(p))
    cold = client.get(path)
    warm = client.get(path)
    assert cold.status_code == warm.status_code == 200
    assert cold.content == warm.content
    assert cold.json()["content_id"] == payload["content_id"]
    assert cold.headers["x-govrev-cache"] == "miss"
    assert warm.headers["x-govrev-cache"] == "hit"
    assert cold.headers["x-govrev-generation"] == payload["content_id"]
    assert cold.headers["x-govrev-process-epoch"] == warm.headers["x-govrev-process-epoch"]
    assert re.fullmatch(r"[0-9a-f]{24}", cold.headers["x-govrev-process-epoch"])
    assert calls == [payload["content_id"]]
    assert set(_phases(cold)) == set(_phases(warm)) == PHASES
    assert _phases(warm)["govrev_read_decode"] == _phases(warm)["govrev_validate"] == 0
    assert all(x >= 0 for x in _phases(cold).values())
    assert cold.headers["cache-control"] == warm.headers["cache-control"] == "private, no-store"
    # Compare to the original plain-function public projection, not telemetry's own body.
    if "/dossier/" in path:
        expected = api.dossier_company("LMT")
    else:
        expected = api.company_awards("LMT", q=None, agency=None, naics=None, psc=None, award_type=None,
                                     sort="effective_desc", cursor=None, limit=8)
    assert cold.json() == expected


def test_changed_generation_is_revalidated(serving, monkeypatch):
    client, _, payload, paths = serving
    first = client.get(PATHS[0])
    validate = api.is_valid_dossier_payload
    calls = []
    monkeypatch.setattr(api, "is_valid_dossier_payload", lambda p: calls.append(p["content_id"]) or validate(p))
    changed = dict(payload, as_of="2026-06-04")
    changed["content_id"] = dossier_content_id(changed)
    for path in paths:
        path.write_text(json.dumps(changed), encoding="utf-8")
    second = client.get(PATHS[0])
    assert second.status_code == 200
    assert second.headers["x-govrev-cache"] == "miss"
    assert second.headers["x-govrev-generation"] != first.headers["x-govrev-generation"]
    assert second.headers["x-govrev-generation"] == changed["content_id"]
    assert calls == [changed["content_id"]]


def test_concurrent_request_observations_are_isolated(serving):
    client, _, _, _ = serving
    barrier = Barrier(2)
    def read(path):
        barrier.wait(timeout=5)
        return client.get(path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(read, PATHS))
    assert all(r.status_code == 200 for r in responses)
    assert sorted(r.headers["x-govrev-cache"] for r in responses) == ["hit", "miss"]
    warm = next(r for r in responses if r.headers["x-govrev-cache"] == "hit")
    assert _phases(warm)["govrev_validate"] == 0


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("status", [401, 403])
def test_denial_before_artifact_reads_has_no_serving_metadata(serving, monkeypatch, path, status):
    client, app, _, _ = serving
    def denied():
        raise HTTPException(status, "fixture denied")
    def forbidden(*args, **kwargs):
        raise AssertionError("denied request read serving state")
    app.dependency_overrides[api.require_site_full_user] = denied
    monkeypatch.setattr(api, "_load_dossiers", forbidden)
    response = client.get(path)
    assert response.status_code == status
    assert not any(h in response.headers for h in HEADERS)
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("failure", ["mismatch", "invalid", "missing"])
def test_artifact_failures_keep_503_without_success_headers(serving, failure):
    client, _, _, paths = serving
    if failure == "mismatch":
        paths[1].write_text(paths[1].read_text() + " ")
    elif failure == "invalid":
        for path in paths:
            path.write_text('{}')
    else:
        paths[0].unlink()
    response = client.get(PATHS[0])
    assert response.status_code == 503
    assert not any(h in response.headers for h in HEADERS)


def test_header_allowlist_does_not_echo_request_or_paths(serving):
    client, _, _, paths = serving
    response = client.get(PATHS[1] + "&q=private-filter-value", headers={"Authorization": "Bearer private-test-token"})
    assert response.status_code == 200
    values = " ".join(response.headers[h] for h in HEADERS)
    assert not any(secret in values for secret in ("private-filter-value", "private-test-token", "fixture-only", str(paths[0]), "LMT"))


def test_process_epoch_is_stable_and_changes_after_fork(serving, monkeypatch):
    client, _, _, _ = serving
    before = client.get(PATHS[0]).headers["x-govrev-process-epoch"]
    real_pid = api.os.getpid()
    monkeypatch.setattr(api.os, "getpid", lambda: real_pid + 1)
    after = client.get(PATHS[0]).headers["x-govrev-process-epoch"]
    assert before != after


def test_bad_telemetry_never_changes_valid_route_result(serving, monkeypatch):
    client, _, _, _ = serving
    loader = api._load_dossiers
    def malformed(observation=None):
        payload = loader(observation)
        if observation is not None:
            observation["stat"] = "not a duration"
        return payload
    monkeypatch.setattr(api, "_load_dossiers", malformed)
    response = client.get(PATHS[0])
    assert response.status_code == 200
    assert response.json() == api.dossier_company("LMT")
    assert not any(h in response.headers for h in HEADERS)


def test_success_headers_preserve_existing_server_timing():
    from fastapi import Response
    response = Response(headers={"Server-Timing": "upstream;dur=12.000"})
    api._dossier_success_headers(response, {"cache": "hit"},
                                {"content_id": "grd1-" + "a" * 24}, api.time.perf_counter())
    timings = response.headers.getlist("server-timing")
    assert timings[0] == "upstream;dur=12.000"
    assert "govrev_route;dur=" in timings[1]
