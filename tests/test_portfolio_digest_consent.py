"""Digest preference API: bind the user's observed revision, never rebase/retry.

Transport and authentication are replaced only at their existing seams. No live
database, account, mail transport or enrollment setting is used.
"""
from __future__ import annotations

import asyncio
import json
import socket
from urllib.error import HTTPError

import pytest
from fastapi import FastAPI

from app import account_prefs as prefs

UID = "00000000-0000-4000-8000-000000000101"
OTHER = "00000000-0000-4000-8000-000000000102"
R0 = "00000000-0000-4000-8000-000000000201"
R1 = "00000000-0000-4000-8000-000000000202"
R2 = "00000000-0000-4000-8000-000000000203"
PATH = "/api/account/prefs/portfolio-digest"


def row(enabled=False, revision=R0, **extra):
    return {"user_id": UID, "portfolio_digest_opt_in": enabled,
            "portfolio_digest_revision": revision, "marketing_opt_out": False, **extra}


def applied(enabled, revision=R1, **extra):
    return {"status": "applied", "state": row(enabled, revision, **extra)}


class _Response:
    def __init__(self, status, headers, content):
        self.status_code = status
        self.headers = {name.decode().lower(): value.decode() for name, value in headers}
        self.text = content.decode()

    def json(self):
        return json.loads(self.text)


class _AsgiClient:
    """Use the billing owner's direct ASGI idiom, including headers and parsing."""
    def __init__(self, app):
        self.app = app

    def get(self, path):
        return self._call("GET", path)

    def put(self, path, json=None):
        return self._call("PUT", path, json)

    def _call(self, method, path, body=None):
        payload = b"" if body is None else json.dumps(body).encode()
        headers = [(b"host", b"testserver")]
        if body is not None:
            headers.append((b"content-type", b"application/json"))
        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
                 "http_version": "1.1", "method": method, "scheme": "http",
                 "path": path, "raw_path": path.encode(), "query_string": b"",
                 "root_path": "", "headers": headers, "client": ("testclient", 50000),
                 "server": ("testserver", 80)}
        messages = []
        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}
        async def send(message):
            messages.append(message)
        asyncio.run(self.app(scope, receive, send))
        start = next(message for message in messages if message["type"] == "http.response.start")
        content = b"".join(message.get("body", b"") for message in messages
                           if message["type"] == "http.response.body")
        return _Response(start["status"], start.get("headers", []), content)


@pytest.fixture
def client(monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("external network attempted")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", "1")
    app = FastAPI()
    app.include_router(prefs.router)
    app.dependency_overrides[prefs._current_user] = lambda: {"id": UID}
    yield _AsgiClient(app)


def install(monkeypatch, result):
    calls = []
    def store(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if isinstance(result, BaseException):
            raise result
        return result
    monkeypatch.setattr(prefs, "_digest_pref_store", store)
    return calls


def test_get_exposes_only_exact_account_revision_and_private_cache(client, monkeypatch):
    calls = install(monkeypatch, [row(marketing_opt_out=True)])
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "marketing_opt_out": True, "revision": R0,
                               "user_id": UID, "enrollment_available": True}
    assert response.headers["cache-control"] == "private, no-store"
    assert calls == [("GET", f"email_prefs?user_id=eq.{UID}&select={prefs._DIGEST_PREF_FIELDS}", {})]


def test_absent_row_is_explicit_observation_not_an_implicit_enable(client, monkeypatch):
    calls = install(monkeypatch, [])
    response = client.get(PATH)
    assert response.json() == {"enabled": False, "marketing_opt_out": None, "revision": None,
                               "user_id": UID, "enrollment_available": True}
    response = client.put(PATH, json={"enabled": True})
    assert response.status_code == 409 and len(calls) == 1
    calls = install(monkeypatch, applied(True))
    response = client.put(PATH, json={"enabled": True, "expected_revision": None})
    assert response.status_code == 200 and response.json()["revision"] == R1
    assert calls == [("POST", "rpc/portfolio_digest_consent_set_v1", {"body": {
        "p_user_id": UID, "p_enabled": True, "p_expected_revision": None}})]


def test_enable_binds_the_received_revision_without_a_server_refresh(client, monkeypatch):
    calls = install(monkeypatch, applied(True, marketing_opt_out=True))
    response = client.put(PATH, json={"enabled": True, "expected_revision": R0})
    assert response.status_code == 200
    assert response.json() == {"enabled": True, "marketing_opt_out": True, "revision": R1,
                               "user_id": UID, "enrollment_available": True}
    assert len(calls) == 1 and calls[0][0] == "POST"
    assert calls[0][2]["body"] == {"p_user_id": UID, "p_enabled": True, "p_expected_revision": R0}


@pytest.mark.parametrize("current", [None, row(False, R1)])
def test_conflict_never_automatically_rebases_or_retries(client, monkeypatch, current):
    calls = install(monkeypatch, {"status": "stale_revision", "state": current})
    response = client.put(PATH, json={"enabled": True, "expected_revision": R0})
    assert response.status_code == 409 and len(calls) == 1
    assert calls[0][2]["body"]["p_expected_revision"] == R0
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["detail"]["state"]["revision"] == (None if current is None else R1)


def test_each_negative_writes_a_fence_even_when_already_false_or_enrollment_off(client, monkeypatch):
    monkeypatch.delenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED")
    calls = []
    revisions = iter([R1, R2])
    def store(method, path, **kwargs):
        calls.append((method, path, kwargs))
        assert kwargs["body"] == {"p_user_id": UID, "p_enabled": False, "p_expected_revision": None}
        return applied(False, next(revisions))
    monkeypatch.setattr(prefs, "_digest_pref_store", store)
    first = client.put(PATH, json={"enabled": False, "expected_revision": R0})
    second = client.put(PATH, json={"enabled": False})
    assert first.status_code == second.status_code == 200
    assert [first.json()["revision"], second.json()["revision"]] == [R1, R2]
    assert len(calls) == 2 and all(call[0] == "POST" for call in calls)


@pytest.mark.parametrize("code", [401, 403])
def test_definite_rpc_denial_is_distinct_from_a_lost_write_reply(client, monkeypatch, code):
    calls = install(monkeypatch, HTTPError("https://fixture.invalid", code, "private secret", {}, None))
    response = client.put(PATH, json={"enabled": False})
    assert response.status_code == 503 and response.json()["detail"] == "Digest preference change not applied"
    assert len(calls) == 1 and "private secret" not in response.text


@pytest.mark.parametrize("error", [OSError("private secret"), TimeoutError("private secret"),
                                  HTTPError("https://fixture.invalid", 502, "private secret", {}, None)])
def test_uncertain_rpc_reply_is_not_retried_or_read_back_as_proof(client, monkeypatch, error):
    calls = install(monkeypatch, error)
    response = client.put(PATH, json={"enabled": False})
    assert response.status_code == 503 and response.json()["detail"] == "Digest preference change unconfirmed"
    assert len(calls) == 1 and "private secret" not in response.text


@pytest.mark.parametrize("result", [
    None, [], {}, {"status": "queued", "state": row()},
    {"status": "applied", "state": None},
    applied(True, user_id=OTHER), applied("true"),
    applied(True, portfolio_digest_revision=None),
    applied(True, portfolio_digest_revision="bad"),
    applied(True, marketing_opt_out="false"), applied(True, revision=R0),
])
def test_unqualified_mutation_receipt_stays_unconfirmed(client, monkeypatch, result):
    calls = install(monkeypatch, result)
    response = client.put(PATH, json={"enabled": True, "expected_revision": R0})
    assert response.status_code == 503 and "unconfirmed" in response.json()["detail"]
    assert len(calls) == 1


@pytest.mark.parametrize("body", [
    {"enabled": "true", "expected_revision": R0},
    {"enabled": True, "expected_revision": 1},
    {"enabled": True, "expected_revision": False},
    {"enabled": True, "expected_revision": []},
    {"enabled": True, "expected_revision": "bad"},
    {"enabled": True, "expected_revision": R0, "user_id": OTHER},
])
def test_invalid_or_forged_input_never_reaches_the_store(client, monkeypatch, body):
    calls = install(monkeypatch, applied(True))
    response = client.put(PATH, json=body)
    assert response.status_code == 422 and not calls


@pytest.mark.parametrize("rows", [
    None, {}, [row(user_id=OTHER)], [row(portfolio_digest_revision=None)],
    [row(portfolio_digest_opt_in="true")], [row(marketing_opt_out=None)],
])
def test_unqualified_get_is_unavailable_not_an_absent_observation(client, monkeypatch, rows):
    install(monkeypatch, rows)
    response = client.get(PATH)
    assert response.status_code == 503
    assert response.headers["cache-control"] == "private, no-store"


def test_enrollment_remains_default_off_without_any_database_call(client, monkeypatch):
    monkeypatch.delenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED")
    calls = install(monkeypatch, applied(True))
    response = client.put(PATH, json={"enabled": True, "expected_revision": R0})
    assert response.status_code == 503 and not calls


def test_anonymous_actor_cannot_choose_a_target_account(client, monkeypatch):
    calls = install(monkeypatch, applied(True))
    client.app.dependency_overrides[prefs._current_user] = lambda: {}
    response = client.put(PATH, json={"enabled": True, "expected_revision": R0})
    assert response.status_code == 401 and not calls


@pytest.mark.parametrize("enabled", [False, True])
def test_observed_subject_cannot_mutate_a_different_authenticated_account(client, monkeypatch, enabled):
    calls = install(monkeypatch, applied(enabled))
    response = client.put(PATH, json={"enabled": enabled, "expected_revision": None,
                                     "expected_user_id": OTHER})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "digest_account_changed"
    assert calls == [], "the observed account is an assertion, never a target override"
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("enabled", [False, True])
def test_observed_subject_matching_auth_retains_one_owner_rpc(client, monkeypatch, enabled):
    calls = install(monkeypatch, applied(enabled))
    response = client.put(PATH, json={"enabled": enabled, "expected_revision": R0,
                                     "expected_user_id": UID})
    assert response.status_code == 200
    assert response.json()["user_id"] == UID
    assert response.json()["enrollment_available"] is True
    assert len(calls) == 1 and calls[0][2]["body"]["p_user_id"] == UID


@pytest.mark.parametrize("subject", [None, "", "not-a-uuid", "AAAAAAAA-0000-4000-8000-000000000101", 1, True, {}, []])
def test_observed_subject_must_be_explicit_canonical_uuid_when_supplied(client, monkeypatch, subject):
    calls = install(monkeypatch, applied(False))
    response = client.put(PATH, json={"enabled": False, "expected_user_id": subject})
    assert response.status_code == 422
    assert calls == []


@pytest.mark.parametrize("flag,available", [(None, False), ("0", False), ("true", False), ("1", True)])
def test_client_view_binds_actor_and_existing_enrollment_availability(client, monkeypatch, flag, available):
    if flag is None:
        monkeypatch.delenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", flag)
    calls = install(monkeypatch, [row(False, R0, marketing_opt_out=True)])
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "marketing_opt_out": True, "revision": R0,
                               "user_id": UID, "enrollment_available": available}
    assert len(calls) == 1 and calls[0][0] == "GET"


def test_observed_subject_withdrawal_stays_available_with_enrollment_off(client, monkeypatch):
    monkeypatch.delenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", raising=False)
    calls = install(monkeypatch, applied(False))
    response = client.put(PATH, json={"enabled": False, "expected_user_id": UID})
    assert response.status_code == 200
    assert response.json()["enrollment_available"] is False
    assert len(calls) == 1


def test_observed_subject_lost_reply_is_not_replayed(client, monkeypatch):
    calls = install(monkeypatch, RuntimeError("synthetic lost committed response"))
    response = client.put(PATH, json={"enabled": True, "expected_revision": R0,
                                     "expected_user_id": UID})
    assert response.status_code == 503
    assert response.json()["detail"] == "Digest preference change unconfirmed"
    assert len(calls) == 1
