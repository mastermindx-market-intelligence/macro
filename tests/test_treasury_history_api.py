"""Internal transport negatives; fake identities, synthetic native data only."""
import importlib
import importlib.util

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def test_api_contract_exists():
    assert importlib.util.find_spec("app.treasury_history") is not None


@pytest.fixture
def api(monkeypatch):
    mod = importlib.import_module("app.treasury_history")
    reads, auths = [], []

    def user(authorization):
        auths.append(authorization)
        if authorization != "Bearer synthetic-qualified":
            raise HTTPException(401, "unauthenticated")
        return {"id": "synthetic-user"}

    def read(*args, **kw):
        reads.append(kw)
        return {"schema": "treasury.daily_history.v1", "status": "stale",
                "source": {"origin": "FRED", "source_id": "DGS3MO"}, "points": []}

    monkeypatch.setattr(mod, "require_site_full_user", user)
    monkeypatch.setattr(mod, "read_history", read)
    app = FastAPI()
    app.include_router(mod.router)
    return mod, app, reads, auths


def get(app, *, peer="127.0.0.1", headers=None, query=None):
    q = query or {"start": "2026-10-13", "end": "2026-10-19", "expected_through": "2026-10-16"}
    with TestClient(app, client=(peer, 12345)) as client:
        return client.get("/api/internal/treasury-history", params=q,
                          headers=headers if headers is not None else {"Authorization": "Bearer synthetic-qualified"})


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization, Cookie"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


@pytest.mark.parametrize("peer", ["203.0.113.1", "localhost", "testclient", "::ffff:127.0.0.1"])
def test_external_socket_peers_never_reach_auth_or_native_read(api, peer):
    _, app, reads, auths = api
    r = get(app, peer=peer)
    assert r.status_code == 401
    assert reads == auths == []
    private(r)


@pytest.mark.parametrize("edge", ["", "127.0.0.1", "203.0.113.1", "spoof"])
def test_any_edge_peer_header_denied_even_for_authenticated_loopback(api, edge):
    _, app, reads, auths = api
    r = get(app, headers={"Authorization": "Bearer synthetic-qualified", "X-MM-Peer": edge})
    assert r.status_code == 401
    assert reads == auths == []
    private(r)


@pytest.mark.parametrize("authorization", [None, "Bearer invalid"])
def test_missing_or_invalid_user_never_reads_native_input(api, authorization):
    _, app, reads, _ = api
    r = get(app, headers={} if authorization is None else {"Authorization": authorization})
    assert r.status_code == 401
    assert reads == []
    private(r)


def test_site_full_denial_remains_403(api, monkeypatch):
    mod, app, reads, _ = api
    def deny(_):
        raise HTTPException(403, "site_full_required")
    monkeypatch.setattr(mod, "require_site_full_user", deny)
    r = get(app)
    assert r.status_code == 403 and reads == []
    private(r)


@pytest.mark.parametrize("query", [{}, {"start": "bad", "end": "2026-10-19", "expected_through": "2026-10-16"},
    {"start": "2026-10-19", "end": "2026-10-13", "expected_through": "2026-10-16"},
    {"start": "2000-01-01", "end": "2026-10-19", "expected_through": "2026-10-16"}])
def test_bad_query_private_422_before_native_read(api, query):
    _, app, reads, _ = api
    with TestClient(app, client=("127.0.0.1", 1)) as c:
        r = c.get("/api/internal/treasury-history", params=query,
                  headers={"Authorization": "Bearer synthetic-qualified"})
    assert r.status_code == 422 and reads == []
    private(r)


def test_same_box_valid_user_uses_fixed_native_reader(api):
    _, app, reads, auths = api
    r = get(app)
    assert r.status_code == 200
    assert r.json()["status"] == "stale"
    assert auths == ["Bearer synthetic-qualified"] and len(reads) == 1
    assert "synthetic-user" not in r.text and "Bearer" not in r.text
    private(r)


def test_unexpected_error_is_sanitized_and_private(api, monkeypatch):
    mod, app, _, _ = api
    def fail(*args, **kwargs):
        raise RuntimeError("private-path-secret")
    monkeypatch.setattr(mod, "read_history", fail)
    r = get(app)
    assert r.status_code == 503
    assert "private-path-secret" not in r.text
    private(r)


def test_reuses_existing_guards_and_real_app_mount():
    mod = importlib.import_module("app.treasury_history")
    from app.prophet_lab import _hub_prophet_authorized, require_site_full_user
    assert mod.require_site_full_user is require_site_full_user
    assert mod._hub_prophet_authorized is _hub_prophet_authorized
    from pathlib import Path
    source = (Path(__file__).parents[1] / "app/main.py").read_text()
    assert "app.include_router(treasury_history_router)" in source
