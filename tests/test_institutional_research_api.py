"""Transport privacy and exact-selection controls for the entitled consumer."""
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

import app.institutional_research as api
import app.paywall as paywall

PATH = "/api/forensics/v1/institutional/reported-holding"
SELECTION = {
    "filer_cik": "0001904423", "report_period": "2026-06-30",
    "accession": "0001904423-26-000004", "infotable_sk": "4611686018427387905",
    "decision_cutoff": "2026-08-27T09:22:23.700168Z",
    "generation_id": "i13fgen_" + "a" * 64,
}
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer existing-user-session"}


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


@pytest.fixture
def world(monkeypatch):
    calls = []
    def require_user(authorization):
        calls.append(("auth", authorization))
        if authorization != HEADERS["Authorization"]:
            raise HTTPException(401, "missing bearer token")
        return {"id": "existing-user"}
    def entitlement(user, *, always):
        assert always is True
        calls.append(("entitlement", user["id"]))
        return user
    # Exercise the actual shared dependency wrapper, without importing the
    # application's unrelated startup services or making a Supabase request.
    monkeypatch.setitem(sys.modules, "app.main", SimpleNamespace(require_user=require_user))
    monkeypatch.setattr(paywall, "enforce_site_full", entitlement)
    def read(**kwargs):
        calls.append(("owner", kwargs))
        return {"state": "AVAILABLE_UNQUALIFIED", "k3e_admissible": False}
    monkeypatch.setattr(api, "_read_holding_context", read)
    app = FastAPI()
    app.include_router(api.router)
    return app, TestClient(app), calls


def test_exact_read_is_lossless_and_auth_precedes_native_owner(world):
    _, client, calls = world
    response = client.post(PATH, json=SELECTION, headers=HEADERS)
    assert response.status_code == 200
    private(response)
    assert [x[0] for x in calls] == ["auth", "entitlement", "owner"]
    assert calls[-1][1] == {**SELECTION, "infotable_sk": 4611686018427387905}
    assert response.json() == {"state": "AVAILABLE_UNQUALIFIED", "k3e_admissible": False}


@pytest.mark.parametrize("state", ["UNAVAILABLE", "REFUSED", "AVAILABLE_UNQUALIFIED"])
def test_native_quarantine_results_are_not_promoted(world, monkeypatch, state):
    _, client, _ = world
    expected = {"state": state, "context": {"refusals": ["FILING_NOT_FOUND"], "k3e_admissible": False}, "authority": {"can_rank": False}}
    monkeypatch.setattr(api, "_read_holding_context", lambda **_: expected)
    response = client.post(PATH, json=SELECTION, headers=HEADERS)
    assert response.status_code == 200 and response.json() == expected
    private(response)


@pytest.mark.parametrize("field,value", [
    ("infotable_sk", 4611686018427387905), ("infotable_sk", True),
    ("infotable_sk", "04611686018427387905"), ("infotable_sk", "9223372036854775808"),
    ("filer_cik", "1904423"), ("accession", "../private"),
    ("report_period", "2026-02-30"), ("report_period", "20260630"),
    ("decision_cutoff", "2026-08-27T09:22:23"),
    ("decision_cutoff", "2026-08-27T09:22:23-04:00"),
    ("generation_id", "https://foreign.invalid/private"), ("generation_id", 1),
    ("owner_semantics", {"resolved": True}), ("store_path", "/private"),
])
def test_untrusted_selection_never_reaches_owner(world, field, value):
    _, client, calls = world
    response = client.post(PATH, json={**SELECTION, field: value}, headers=HEADERS)
    assert response.status_code == 400
    assert all(call[0] != "owner" for call in calls)
    private(response)


@pytest.mark.parametrize("body", [b'{"filer_cik":1,"filer_cik":2}', b'NaN', b'[]', b'{}', b'\xff', b'[' * 1500 + b']' * 1500])
def test_malformed_json_is_private_and_bounded(world, body):
    _, client, calls = world
    response = client.post(PATH, content=body, headers=HEADERS)
    assert response.status_code == 400
    private(response)
    assert all(call[0] != "owner" for call in calls)


def test_streamed_body_does_not_trust_content_length(world):
    _, client, calls = world
    response = client.post(PATH, content=iter([b"x" * 2048] * 3), headers={**HEADERS, "Content-Length": "1"})
    assert response.status_code == 413
    private(response)
    assert all(call[0] != "owner" for call in calls)


def test_omitted_generation_uses_only_the_native_current_pointer(world):
    _, client, calls = world
    response = client.post(PATH, json={k: v for k, v in SELECTION.items() if k != "generation_id"}, headers=HEADERS)
    assert response.status_code == 200
    assert calls[-1][1]["generation_id"] is None


def test_content_type_is_private_and_checked_after_auth(world):
    _, client, calls = world
    response = client.post(PATH, content=b"{}", headers={"Authorization": HEADERS["Authorization"]})
    assert response.status_code == 415
    private(response)
    assert [x[0] for x in calls] == ["auth", "entitlement"]


def test_auth_denial_happens_before_request_body_is_read(world):
    app, _, calls = world
    output = []
    async def receive():
        raise AssertionError("unauthenticated body must not be consumed")
    async def send(message):
        output.append(message)
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": "POST", "scheme": "http", "path": PATH, "raw_path": PATH.encode(),
             "query_string": b"", "headers": [], "client": ("127.0.0.1", 1234), "server": ("test", 80)}
    asyncio.run(app(scope, receive, send))
    assert output[0]["status"] == 401
    headers = {k.decode(): v.decode() for k, v in output[0]["headers"]}
    assert headers["cache-control"] == "private, no-store"
    assert [x[0] for x in calls] == ["auth"]


def test_entitlement_denial_is_private_and_does_not_read_owner(world, monkeypatch):
    _, client, calls = world
    def denied(*_, **__):
        raise HTTPException(403, "site_full required", headers={"cache-control": "public"})
    monkeypatch.setattr(paywall, "enforce_site_full", denied)
    response = client.post(PATH, content=b"x" * 5000, headers=HEADERS)
    assert response.status_code == 403
    private(response)
    assert all(call[0] != "owner" for call in calls)


@pytest.mark.parametrize("method", ["GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"])
def test_other_methods_are_entitled_then_refused(world, method):
    _, client, calls = world
    denied = client.request(method, PATH)
    assert denied.status_code == 401
    private(denied)
    response = client.request(method, PATH, headers=HEADERS)
    assert response.status_code == 405 and response.headers["allow"] == "POST"
    private(response)
    assert all(call[0] != "owner" for call in calls)


@pytest.mark.parametrize("failure", ["exception", "oversized", "nonfinite"])
def test_backend_failure_cannot_disclose_private_details(world, monkeypatch, failure):
    _, client, _ = world
    def backend(**_):
        if failure == "exception":
            raise RuntimeError("secret https://private.bucket.invalid/object-key")
        return {"data": "x" * 65536} if failure == "oversized" else {"data": float("nan")}
    monkeypatch.setattr(api, "_read_holding_context", backend)
    response = client.post(PATH, json=SELECTION, headers=HEADERS)
    assert response.status_code == 503
    private(response)
    assert response.json() == {"detail": "institutional research temporarily unavailable"}


def test_router_is_mounted_without_optional_import_suppression():
    text = (Path(__file__).resolve().parents[1] / "app/main.py").read_text()
    assert "from app.institutional_research import router as institutional_research_router" in text
    assert "app.include_router(institutional_research_router)" in text


def test_body_receive_failure_is_private_after_auth_and_never_reads_owner(world):
    app, _, calls = world
    output = []
    async def receive():
        raise RuntimeError('private stream implementation detail')
    async def send(message):
        output.append(message)
    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
             'method': 'POST', 'scheme': 'http', 'path': PATH, 'raw_path': PATH.encode(),
             'query_string': b'', 'headers': [(k.lower().encode(), v.encode()) for k, v in HEADERS.items()],
             'client': ('127.0.0.1', 1234), 'server': ('test', 80)}
    asyncio.run(app(scope, receive, send))
    assert output[0]['status'] == 400
    assert dict(output[0]['headers'])[b'cache-control'] == b'private, no-store'
    assert b'private stream' not in b''.join(x.get('body', b'') for x in output)
    assert [x[0] for x in calls] == ['auth', 'entitlement']
