"""tests/test_account_actions.py — app/account_actions.py (MO-B F12-13, MO-PAID-078).

The macro account panel had four controls that did nothing. ``templates/account.js`` had
called ``/api/account/password``, ``/api/account/email``, ``/api/account/signout-everywhere``
and ``/api/account/delete`` since the card shipped, and no handler for any of them existed
anywhere in ``app/`` — while the panel's API base resolved to ``window.MM_API``
(``https://app.mastermind-x.com``), a host with none of those routes and no CORS headers.
This suite pins the repair: four registered routes, the caller's own token as the only
credential that acts, a deletion INTAKE that can never invent a receipt, a bounded and
rate-limited upstream, a plain-word EN+ZH sentence for every failure, and no dead handler
left on the panel.

RED-FIRST — what fails on origin/main and why. t1–t6 cannot even be collected there:
``app/account_actions.py`` does not exist, so ``from app import account_actions`` below
raises ``ModuleNotFoundError`` and every one of them errors before asserting anything. The
client-side cases also fail on their own terms against origin/main's ``templates/account.js``:

  * t6 (no-dead-handler) — the four ``api('/api/account…')`` POSTs are absent from
    ``app.main.app.routes`` because no router declares them; all four 404 on the live host.
  * t8 (API base) — origin/main's line 29 is
    ``var API = (window.MM_API || '').replace(/\\/+$/, '');`` with no host test at all, so
    every call leaves for the Terminal host. The assertion that the line carries the
    ``mastermind-x.com`` host test fails, as does the release-key one.
  * t9 (copy) — ``delete_warn`` is 'This permanently deletes your account and data.' /
    '这将永久删除你的账户及数据。' and ``delete_go`` is 'Delete permanently' / '永久删除', so
    the "no 'permanently'" and "no '永久'" assertions fail; ``del_ok`` and ``del_open`` do
    not exist, so their lookups fail too.
  * t7 (site pair) — passes on origin/main (both sides carry the OLD bytes) and exists to
    stop this PR landing a one-sided edit, the #6170 failure mode.

Offline: no Supabase, no network. ``urllib.request.urlopen`` is stubbed with a recorder in
the shape of ``tests/test_account_prefs.py``'s ``_Auth`` — it keeps
``(method, url, headers, payload)`` for every call — and ``app.main.require_user`` is
monkeypatched. Those are the same two seams the account_prefs suite uses.

TRANSPORT: the requests below are driven straight through the ASGI callable
(``_asgi_call``), NOT through ``fastapi.testclient.TestClient``. The ``billing-emails`` job
that names this suite installs no ``httpx`` (see ``tests/test_account_team_fields.py``'s
header for why widening that line is avoided — it would split the shared venv with the
sibling billing jobs), and ``importorskip`` would turn the whole suite into a green no-op
in CI, which proves nothing. Calling the app as the ASGI3 callable it is exercises the
same stack TestClient would — routing, ``Depends``/``Header`` resolution, Pydantic body
parsing, the ``HTTPException`` -> 401 mapping and ``JSONResponse`` serialisation — with no
extra dependency, so CI and a local run execute identical assertions.
"""
from __future__ import annotations

import asyncio
import io
import json
from json import dumps as json_dumps
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import account_actions, billing  # noqa: E402

ACCOUNT_JS = ROOT / "templates" / "account.js"
SITE_ACCOUNT_JS = ROOT / "site" / "account.js"
THEME_JS = ROOT / "templates" / "theme.js"
SITE_THEME_JS = ROOT / "site" / "theme.js"

SUPABASE_URL = "https://proj.supabase.test"
SERVICE_KEY = "service-role-test-key"
ANON_KEY = "anon-publishable-test-key"
CALLER_TOKEN = "caller-jwt-token"
AUTHZ = f"Bearer {CALLER_TOKEN}"

USER = {"id": "9c1f-user", "email": "reader@example.com",
        "user_metadata": {"display_name": "Ada"}}

RELEASE_KEY = "20260913-account-actions"
PASSWORD = "a-long-enough-secret"
NEW_EMAIL = "new@example.com"
FOUR_ROUTES = ("/api/account/password", "/api/account/email",
               "/api/account/signout-everywhere", "/api/account/delete")
ROW = {"receipt_code": "MMX-DEL-20260913-3K7QZM2A",
       "requested_at": "2026-09-13T07:00:00Z", "status": "received"}


# --------------------------------------------------------------------------- #
# seams
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, body: bytes, status: int):
        self._body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status


class Call:
    def __init__(self, method, url, headers, payload, timeout):
        self.method = method
        self.url = url
        # urllib capitalises header names ('Content-Type' -> 'Content-type'), so the
        # assertions below compare case-insensitively on purpose.
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.payload = payload
        self.timeout = timeout

    @property
    def authorization(self) -> str:
        return self.headers.get("authorization", "")


class _Upstream:
    """Records every upstream call and answers from a queue of ``(status, body)`` pairs.

    The queue is consumed in order and the LAST entry repeats, so a route that makes two
    calls (the delete 409 read-back) can be scripted without padding.
    """

    def __init__(self):
        self.calls: list[Call] = []
        self._answers: list[tuple[int, object]] = [(200, {})]
        self._raise: BaseException | None = None

    def answers(self, *pairs) -> "_Upstream":
        """Script the answers: ``(status, body)`` pairs, the last one repeating."""
        self._answers = list(pairs) or [(200, {})]
        self._raise = None
        return self

    def fails_with(self, exc: BaseException) -> "_Upstream":
        """Make every call die before it is answered — the network leg."""
        self._raise = exc
        return self

    def urlopen(self, req, timeout=None):
        payload = json.loads(req.data.decode("utf-8")) if req.data else None
        self.calls.append(Call(req.get_method(), req.full_url, dict(req.headers),
                               payload, timeout))
        if self._raise is not None:
            raise self._raise
        status, body = self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]
        raw = b"" if body is None else json.dumps(body).encode("utf-8")
        if status >= 400:
            # A FRESH HTTPError per call: one instance's body can only be read once.
            raise urllib.error.HTTPError(req.full_url, status, "upstream", {},
                                         io.BytesIO(raw))
        return _Resp(raw, status)

    def only(self) -> Call:
        assert len(self.calls) == 1, f"expected 1 upstream call, saw {len(self.calls)}"
        return self.calls[0]


def _http_error(status: int, body: dict | None = None) -> urllib.error.HTTPError:
    raw = json.dumps(body if body is not None else {}).encode("utf-8")
    return urllib.error.HTTPError(SUPABASE_URL, status, "upstream", {}, io.BytesIO(raw))


class _noop:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _shed:
    """Drain every upstream permit for the length of a ``with`` block."""

    def __enter__(self):
        for _ in range(account_actions._UPSTREAM_LIMIT):
            assert account_actions._UPSTREAM_SEM.acquire(blocking=False)
        return self

    def __exit__(self, *exc):
        for _ in range(account_actions._UPSTREAM_LIMIT):
            account_actions._UPSTREAM_SEM.release()
        return False


def _age_out_every_bucket() -> None:
    """Rewrite the recorded timestamps to just outside the window.

    ``_allow`` reads the clock off ``time.monotonic``; bending the buckets states the same
    fact without patching the ``time`` module for the whole interpreter.
    """
    old = account_actions.time.monotonic() - account_actions._RATE_WINDOW_SECONDS - 1.0
    with account_actions._rate_lock:
        for bucket in account_actions._rate_buckets.values():
            for index in range(len(bucket)):
                bucket[index] = old


@pytest.fixture(autouse=True)
def _isolate_rate_limit():
    account_actions._reset_rate_limit_for_tests()
    yield
    account_actions._reset_rate_limit_for_tests()


@pytest.fixture
def up(monkeypatch) -> _Upstream:
    recorder = _Upstream()
    monkeypatch.setattr(urllib.request, "urlopen", recorder.urlopen)
    monkeypatch.setattr(billing, "SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", SERVICE_KEY)
    import app.main as main
    monkeypatch.setattr(main, "SUPABASE_ANON_KEY", ANON_KEY)
    monkeypatch.setattr(main, "require_user", lambda authorization: dict(USER))
    return recorder


class _Response:
    """The two things every assertion below reads: the status and the parsed body."""

    def __init__(self, status_code: int, body: object):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class _AsgiClient:
    """A minimal TestClient stand-in: same ``.post(...)`` shape, no httpx."""

    def __init__(self, app):
        self.app = app

    def post(self, path: str, json=None, headers: dict | None = None) -> _Response:
        return _asgi_call(self.app, path, json, headers)


def _asgi_call(app, path: str, body: object, headers: dict | None) -> _Response:
    """Drive one POST through the real ASGI stack and read back what it answered."""
    payload = b"" if body is None else json_dumps(body).encode("utf-8")
    raw = [(name.lower().encode(), value.encode()) for name, value in (headers or {}).items()]
    if body is not None:
        raw.append((b"content-type", b"application/json"))
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": "POST", "scheme": "http",
        "path": path, "raw_path": path.encode(), "query_string": b"",
        "root_path": "", "headers": raw, "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    messages: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    start = next(m for m in messages if m["type"] == "http.response.start")
    chunks = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return _Response(start["status"], json.loads(chunks) if chunks else None)


@pytest.fixture
def client() -> _AsgiClient:
    app = FastAPI()
    app.include_router(account_actions.router)
    return _AsgiClient(app)


def _post(client, path, body=None):
    return client.post(path, json=body, headers={"Authorization": AUTHZ})


def _assert_plain_failure(resp, status: int) -> dict:
    """The copy contract: one status, one plain EN sentence, one plain ZH sentence."""
    assert resp.status_code == status
    data = resp.json()
    assert data.get("ok") is False, data
    assert isinstance(data.get("error"), str) and data["error"].strip()
    assert isinstance(data.get("error_zh"), str) and data["error_zh"].strip()
    assert "detail" not in data, "FastAPI's default body is not read by account.js"
    return data


def _unauthenticated(monkeypatch, client, path, body, up):
    """require_user's own 401 stands, and nothing upstream is touched at all."""
    import app.main as main

    def _reject(authorization):
        raise HTTPException(401, "missing bearer token")

    monkeypatch.setattr(main, "require_user", _reject)
    assert _post(client, path, body).status_code == 401
    assert up.calls == []


# --------------------------------------------------------------------------- #
# t1 — password
# --------------------------------------------------------------------------- #
def test_t1_password_success_puts_to_auth_with_the_caller_token(client, up):
    resp = _post(client, "/api/account/password", {"password": PASSWORD})
    assert resp.status_code == 200 and resp.json() == {"ok": True}
    call = up.only()
    assert call.method == "PUT"
    assert call.url == f"{SUPABASE_URL}/auth/v1/user"
    assert call.payload == {"password": PASSWORD}
    assert call.authorization == AUTHZ
    assert SERVICE_KEY not in call.authorization
    assert call.headers["apikey"] == ANON_KEY
    assert call.timeout == 4
    assert "/auth/v1/admin" not in call.url


@pytest.mark.parametrize("password", [None, "", "short", "x" * 7, "x" * 73])
def test_t1_password_length_is_enforced_locally(client, up, password):
    resp = _post(client, "/api/account/password",
                 None if password is None else {"password": password})
    _assert_plain_failure(resp, 400)
    assert up.calls == [], "an unusable password must never reach Supabase"


def test_t1_password_unauthenticated_is_401_with_zero_upstream_calls(client, up, monkeypatch):
    _unauthenticated(monkeypatch, client, "/api/account/password", {"password": PASSWORD}, up)


def test_t1_password_upstream_500_is_a_plain_502(client, up):
    up.fails_with(_http_error(500))
    _assert_plain_failure(_post(client, "/api/account/password", {"password": PASSWORD}), 502)
    assert len(up.calls) == 1


def test_t1_password_network_failure_is_a_plain_502(client, up):
    up.fails_with(urllib.error.URLError("dns"))
    _assert_plain_failure(_post(client, "/api/account/password", {"password": PASSWORD}), 502)
    assert len(up.calls) == 1


def test_t1_password_weak_upstream_refusal_is_a_plain_400(client, up):
    """The upstream wording is classified, never echoed — it can carry a limit or an enum."""
    up.answers((422, {"msg": "Password should be at least 6 characters."}))
    data = _assert_plain_failure(_post(client, "/api/account/password",
                                       {"password": PASSWORD}), 400)
    assert data["error"] == account_actions.COPY["password_weak"][0]
    assert "at least 6" not in data["error"]


def test_t1_password_expired_caller_token_is_a_plain_401(client, up):
    up.answers((401, {"msg": "invalid claim: missing required claim"}))
    data = _assert_plain_failure(_post(client, "/api/account/password",
                                       {"password": PASSWORD}), 401)
    assert data["error"] == account_actions.COPY["session_expired"][0]
    assert "claim" not in data["error"]


def test_t1_password_same_as_current_is_a_plain_400(client, up):
    up.answers((400, {"error_description":
                      "New password should be different from the old password."}))
    data = _assert_plain_failure(_post(client, "/api/account/password",
                                       {"password": PASSWORD}), 400)
    assert data["error"] == account_actions.COPY["password_same"][0]


# --------------------------------------------------------------------------- #
# t2 — email
# --------------------------------------------------------------------------- #
def test_t2_email_success_reports_that_a_confirmation_is_required(client, up):
    resp = _post(client, "/api/account/email", {"email": NEW_EMAIL})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "confirmation_required": True}
    call = up.only()
    assert (call.method, call.url) == ("PUT", f"{SUPABASE_URL}/auth/v1/user")
    assert call.payload == {"email": NEW_EMAIL}
    assert call.authorization == AUTHZ
    assert SERVICE_KEY not in call.authorization
    assert call.headers["apikey"] == ANON_KEY


@pytest.mark.parametrize("address", [
    "", "reader.example.com", "reader@", "@example.com", "a@b@example.com",
    "reader@example", "reader@.example.com", "reader@example..com", "reader@example.com.",
    "rea der@example.com", "x" * 250 + "@e.com",
])
def test_t2_email_syntax_is_checked_locally(client, up, address):
    _assert_plain_failure(_post(client, "/api/account/email", {"email": address}), 400)
    assert up.calls == []


def test_t2_email_unauthenticated_is_401_with_zero_upstream_calls(client, up, monkeypatch):
    _unauthenticated(monkeypatch, client, "/api/account/email", {"email": NEW_EMAIL}, up)


@pytest.mark.parametrize("status, body, key", [
    (429, {"error_description": "Rate limit exceeded"}, "rate_limited"),
    (400, {"msg": "New email should not be the same as the current email"}, "email_same"),
    (422, {"error": "User already registered"}, "email_taken"),
    (400, {"msg": "a refusal we have no specific sentence for"}, "email_refused"),
])
def test_t2_email_upstream_refusals_are_plain_sentences(client, up, status, body, key):
    up.answers((status, body))
    data = _assert_plain_failure(_post(client, "/api/account/email",
                                       {"email": NEW_EMAIL}), 400)
    assert data["error"] == account_actions.COPY[key][0]
    assert data["error_zh"] == account_actions.COPY[key][1]
    # The vendor's own wording never reaches a screen: it can name an enum, a column or
    # somebody else's address.
    for fragment in ("already registered", "rate limit exceeded", "same as the current",
                     "no specific sentence"):
        assert fragment not in data["error"].lower()
        assert fragment not in data["error_zh"]


def test_t2_email_upstream_500_is_a_plain_502(client, up):
    up.answers((503, {}))
    _assert_plain_failure(_post(client, "/api/account/email", {"email": NEW_EMAIL}), 502)


def test_t2_email_network_failure_is_a_plain_502(client, up):
    up.fails_with(urllib.error.URLError("reset"))
    _assert_plain_failure(_post(client, "/api/account/email", {"email": NEW_EMAIL}), 502)


# --------------------------------------------------------------------------- #
# t3 — sign out everywhere
# --------------------------------------------------------------------------- #
def test_t3_signout_everywhere_posts_global_scope_with_the_caller_token(client, up):
    up.answers((204, None))
    resp = client.post("/api/account/signout-everywhere", headers={"Authorization": AUTHZ})
    assert resp.status_code == 200 and resp.json() == {"ok": True}
    call = up.only()
    assert call.method == "POST"
    assert call.url == f"{SUPABASE_URL}/auth/v1/logout?scope=global"
    assert call.payload is None
    assert call.authorization == AUTHZ
    assert SERVICE_KEY not in call.authorization
    assert "/auth/v1/admin" not in call.url


def test_t3_signout_everywhere_accepts_a_200_too(client, up):
    up.answers((200, {}))
    assert client.post("/api/account/signout-everywhere",
                       headers={"Authorization": AUTHZ}).json() == {"ok": True}


def test_t3_signout_everywhere_unauthenticated_is_401(client, up, monkeypatch):
    _unauthenticated(monkeypatch, client, "/api/account/signout-everywhere", None, up)


def test_t3_signout_everywhere_upstream_401_is_a_plain_401(client, up):
    up.answers((401, {"msg": "invalid claim"}))
    data = _assert_plain_failure(
        client.post("/api/account/signout-everywhere", headers={"Authorization": AUTHZ}), 401)
    assert data["error"] == account_actions.COPY["session_expired"][0]


def test_t3_signout_everywhere_other_refusal_is_a_plain_400(client, up):
    up.answers((404, {"msg": "not found"}))
    data = _assert_plain_failure(
        client.post("/api/account/signout-everywhere", headers={"Authorization": AUTHZ}), 400)
    assert data["error"] == account_actions.COPY["signout_refused"][0]


def test_t3_signout_everywhere_upstream_500_is_a_plain_502(client, up):
    up.fails_with(_http_error(500))
    _assert_plain_failure(
        client.post("/api/account/signout-everywhere", headers={"Authorization": AUTHZ}), 502)


def test_t3_signout_everywhere_network_failure_is_a_plain_502(client, up):
    up.fails_with(urllib.error.URLError("tls"))
    _assert_plain_failure(
        client.post("/api/account/signout-everywhere", headers={"Authorization": AUTHZ}), 502)


# --------------------------------------------------------------------------- #
# t4 — deletion intake
# --------------------------------------------------------------------------- #
def test_t4_delete_success_inserts_with_the_caller_token_and_returns_the_receipt(client, up):
    up.answers((201, [dict(ROW)]))
    resp = _post(client, "/api/account/delete", {"confirm": "Reader@Example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True and data["already_open"] is False
    assert data["receipt"] == ROW
    call = up.only()
    assert call.method == "POST"
    assert call.url == f"{SUPABASE_URL}/rest/v1/account_lifecycle_requests"
    assert call.payload["user_id"] == USER["id"]
    assert call.payload["kind"] == "deletion"
    assert call.payload["status"] == "received"
    assert set(call.payload) == {"user_id", "kind", "status", "receipt_code"}
    assert re.fullmatch(r"MMX-DEL-\d{8}-[0-9A-HJKMNP-TV-Z]{8}",
                        call.payload["receipt_code"]), call.payload["receipt_code"]
    # Authorization carries the CALLER's token so RLS is the authority; the service-role
    # key only names the project on apikey and must never be the thing that acts.
    assert call.authorization == AUTHZ
    assert SERVICE_KEY not in call.authorization
    assert call.headers["apikey"] == SERVICE_KEY
    assert call.headers["prefer"] == "return=representation"


@pytest.mark.parametrize("confirm", ["", "reader@example.co", "someone.else@example.com",
                                     "reader", "reader@example.comx"])
def test_t4_delete_confirm_mismatch_is_400_with_zero_upstream_calls(client, up, confirm):
    data = _assert_plain_failure(_post(client, "/api/account/delete", {"confirm": confirm}), 400)
    assert data["error"] == account_actions.COPY["delete_confirm"][0]
    assert data["error_zh"] == account_actions.COPY["delete_confirm"][1]
    assert up.calls == []


def test_t4_delete_confirm_tolerates_only_outer_whitespace(client, up):
    """The reader pasted it from an email; the case may differ. Nothing looser than that."""
    up.answers((201, [dict(ROW)]))
    assert _post(client, "/api/account/delete",
                 {"confirm": "  reader@example.com  "}).status_code == 200


def test_t4_delete_reports_the_stores_echo_not_the_code_it_minted(client, up):
    """A receipt is a fact about a stored row. If the store echoes a different code than the
    one we proposed, the store's is the only one that may reach the reader — reporting ours
    would be the fabricated receipt this route exists never to produce."""
    stored = dict(ROW, receipt_code="MMX-DEL-20260913-ZZZZZZZZ")
    up.answers((201, [stored]))
    data = _post(client, "/api/account/delete", {"confirm": "reader@example.com"}).json()
    minted = up.only().payload["receipt_code"]
    assert minted != stored["receipt_code"]
    assert data["receipt"]["receipt_code"] == "MMX-DEL-20260913-ZZZZZZZZ"


def test_t4_delete_files_the_token_owners_row_not_a_body_claim(client, up, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "require_user", lambda authorization: dict(USER))
    up.answers((201, [dict(ROW)]))
    resp = client.post("/api/account/delete",
                       json={"confirm": "reader@example.com", "user_id": "attacker-uuid"},
                       headers={"Authorization": AUTHZ})
    assert resp.status_code == 200
    assert up.only().payload["user_id"] == USER["id"]
    assert "attacker-uuid" not in json.dumps(up.only().payload)


def test_t4_delete_identity_without_an_email_is_refused_before_the_store(client, up, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "require_user",
                        lambda authorization: {"id": USER["id"], "user_metadata": {}})
    data = _assert_plain_failure(_post(client, "/api/account/delete",
                                       {"confirm": "reader@example.com"}), 400)
    assert data["error"] == account_actions.COPY["delete_no_email"][0]
    assert up.calls == []


def test_t4_delete_unauthenticated_is_401_with_zero_upstream_calls(client, up, monkeypatch):
    _unauthenticated(monkeypatch, client, "/api/account/delete",
                     {"confirm": "reader@example.com"}, up)


def test_t4_delete_conflict_reads_back_the_open_row_with_the_caller_token(client, up):
    up.answers(
        (409, {"code": "23505",
               "message": 'duplicate key value violates unique constraint '
                          '"account_lifecycle_one_open_deletion"'}),
        (200, [dict(ROW, status="in_progress")]),
    )
    resp = _post(client, "/api/account/delete", {"confirm": "reader@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True and data["already_open"] is True
    assert data["receipt"]["receipt_code"] == ROW["receipt_code"]
    assert data["receipt"]["status"] == "in_progress"
    insert, readback = up.calls
    assert insert.method == "POST"
    assert readback.method == "GET"
    assert readback.url.startswith(f"{SUPABASE_URL}/rest/v1/account_lifecycle_requests?")
    assert "select=receipt_code,requested_at,status" in readback.url
    assert f"user_id=eq.{USER['id']}" in readback.url
    assert "kind=eq.deletion" in readback.url
    assert "status=in.(received,in_progress)" in readback.url
    assert "order=requested_at.desc" in readback.url and "limit=1" in readback.url
    assert readback.authorization == AUTHZ
    assert SERVICE_KEY not in readback.authorization
    assert readback.headers["apikey"] == SERVICE_KEY


def test_t4_delete_conflict_without_a_readable_open_row_is_503_and_no_receipt(client, up):
    """A 409 whose read-back comes up empty must NOT be answered with the code we minted."""
    up.answers((409, {"code": "23505", "message": "duplicate key"}), (200, []))
    data = _assert_plain_failure(_post(client, "/api/account/delete",
                                       {"confirm": "reader@example.com"}), 503)
    assert data["error"] == account_actions.COPY["delete_not_recorded"][0]
    assert "receipt" not in data
    assert len(up.calls) == 2


def test_t4_delete_conflict_whose_readback_fails_is_503(client, up):
    up.answers((409, {"code": "23505"}), (500, {"message": "boom"}))
    _assert_plain_failure(_post(client, "/api/account/delete",
                                {"confirm": "reader@example.com"}), 503)


@pytest.mark.parametrize("answers, leg", [
    ([(500, {"message": "boom"})], "store 5xx"),
    ([(401, {"message": "jwt expired"})], "store 401"),
    ([(403, {"message": "RLS refused"})], "store 403"),
    ([(201, [])], "201 with no representation"),
    ([(201, [{"requested_at": "x", "status": "received"}])], "201 with no receipt code"),
    ([(201, "not-a-row")], "201 with a body that is not a row"),
    ([(201, [dict(ROW)])], "no upstream permit"),
    (None, "network"),
])
def test_t4_delete_store_failures_are_503_with_no_receipt(client, up, answers, leg):
    """``leg`` names the failure; every one of them is the same honest answer."""
    if leg == "network":
        up.fails_with(urllib.error.URLError("dns"))
    else:
        up.answers(*answers)
    with (_shed() if leg == "no upstream permit" else _noop()):
        data = _assert_plain_failure(_post(client, "/api/account/delete",
                                           {"confirm": "reader@example.com"}), 503)
    assert data["error"] == account_actions.COPY["delete_not_recorded"][0]
    assert data["error_zh"] == account_actions.COPY["delete_not_recorded"][1]
    assert "receipt" not in data and "already_open" not in data
    if leg == "no upstream permit":
        assert up.calls == [], "a shed request must not reach the store"


def test_t4_receipt_code_is_utc_dated_crockford_base32_and_never_repeats():
    code = account_actions._receipt_code()
    assert re.fullmatch(r"MMX-DEL-\d{8}-[0-9A-HJKMNP-TV-Z]{8}", code), code
    tail = code.split("-")[-1]
    for ambiguous in "ILOU":
        assert ambiguous not in tail, "Crockford base32 excludes I, L, O and U"
    assert len({account_actions._receipt_code() for _ in range(200)}) == 200


# --------------------------------------------------------------------------- #
# legs shared by all four routes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path, body", [
    ("/api/account/password", {"password": PASSWORD}),
    ("/api/account/email", {"email": NEW_EMAIL}),
    ("/api/account/signout-everywhere", None),
    ("/api/account/delete", {"confirm": "reader@example.com"}),
])
def test_a_shed_upstream_is_a_plain_503_and_never_a_success(client, up, path, body):
    with _shed():
        resp = _post(client, path, body)
    data = _assert_plain_failure(resp, 503)
    assert up.calls == [], "a shed request must not reach the vendor"
    if path != "/api/account/delete":
        assert data["error"] == account_actions.COPY["busy"][0]


@pytest.mark.parametrize("path, body", [
    ("/api/account/password", {"password": PASSWORD}),
    ("/api/account/email", {"email": NEW_EMAIL}),
    ("/api/account/signout-everywhere", None),
    ("/api/account/delete", {"confirm": "reader@example.com"}),
])
def test_no_route_puts_a_secret_on_authorization(client, up, path, body):
    if path == "/api/account/delete":
        up.answers((201, [dict(ROW)]))
    elif path == "/api/account/signout-everywhere":
        up.answers((204, None))
    else:
        up.answers((200, {}))
    _post(client, path, body)
    assert up.calls, "expected the route to reach the vendor"
    for call in up.calls:
        assert call.authorization == AUTHZ
        assert SERVICE_KEY not in call.authorization
        assert ANON_KEY not in call.authorization
        assert "/auth/v1/admin" not in call.url
        assert call.method in ("PUT", "POST", "GET")
        assert call.timeout == 4


def test_no_route_updates_or_deletes_anything(client, up):
    """This service files a request. It never advances, cancels or removes one."""
    up.answers((201, [dict(ROW)]))
    _post(client, "/api/account/delete", {"confirm": "reader@example.com"})
    for call in up.calls:
        assert call.method == "POST"
        assert "account_lifecycle_requests" in call.url
        assert "?" not in call.url.split("/rest/v1/", 1)[1]


# --------------------------------------------------------------------------- #
# t5 — rate limit
# --------------------------------------------------------------------------- #
def test_t5_the_sixth_password_in_the_window_is_429(client, up):
    limit = account_actions._RATE_LIMITS["password"]
    assert limit == 5
    for _ in range(limit):
        assert _post(client, "/api/account/password", {"password": PASSWORD}).status_code == 200
    data = _assert_plain_failure(_post(client, "/api/account/password",
                                       {"password": PASSWORD}), 429)
    assert data["error"] == account_actions.COPY["rate_limited"][0]
    assert data["error_zh"] == account_actions.COPY["rate_limited"][1]
    assert len(up.calls) == limit, "a refused call must not reach the vendor"


def test_t5_the_window_slides_rather_than_banning(client, up):
    limit = account_actions._RATE_LIMITS["password"]
    for _ in range(limit):
        assert _post(client, "/api/account/password", {"password": PASSWORD}).status_code == 200
    assert _post(client, "/api/account/password", {"password": PASSWORD}).status_code == 429
    _age_out_every_bucket()
    assert _post(client, "/api/account/password", {"password": PASSWORD}).status_code == 200


def test_t5_limits_are_keyed_by_user_and_by_ip(client, up, monkeypatch):
    """One noisy account cannot spend another's budget — and one address cannot either."""
    limit = account_actions._RATE_LIMITS["password"]
    for _ in range(limit):
        assert _post(client, "/api/account/password", {"password": PASSWORD}).status_code == 200
    keys = set(account_actions._rate_buckets)
    assert any(k.startswith("password:user:") for k in keys), keys
    assert any(k.startswith("password:ip:") for k in keys), keys

    import app.main as main
    monkeypatch.setattr(main, "require_user",
                        lambda authorization: dict(USER, id="someone-else"))
    assert _post(client, "/api/account/password", {"password": PASSWORD}).status_code == 429, \
        "a different account behind the same address is still held by the IP leg"


def test_t5_each_action_has_its_own_budget(client, up):
    """Spending the password budget must not lock the reader out of their own email change."""
    up.answers((200, {}))
    for _ in range(account_actions._RATE_LIMITS["password"] + 1):
        _post(client, "/api/account/password", {"password": PASSWORD})
    assert _post(client, "/api/account/email", {"email": NEW_EMAIL}).status_code == 200


def test_t5_signout_gets_its_own_larger_budget(client, up):
    up.answers((204, None))
    limit = account_actions._RATE_LIMITS["signout-everywhere"]
    assert limit == 10
    for _ in range(limit):
        assert client.post("/api/account/signout-everywhere",
                           headers={"Authorization": AUTHZ}).status_code == 200
    _assert_plain_failure(
        client.post("/api/account/signout-everywhere", headers={"Authorization": AUTHZ}), 429)


def test_t5_the_limiter_dict_is_capped():
    """A spray of identities must not grow process memory without bound."""
    for index in range(account_actions._RATE_MAX_KEYS + 40):
        account_actions._allow("password", f"user-{index}", f"ip-{index}")
    assert len(account_actions._rate_buckets) <= account_actions._RATE_MAX_KEYS + 2


def test_t5_reset_helper_clears_every_bucket():
    assert account_actions._allow("password", "someone", "1.2.3.4")
    assert account_actions._rate_buckets
    account_actions._reset_rate_limit_for_tests()
    assert account_actions._rate_buckets == {}


# --------------------------------------------------------------------------- #
# t6 — no dead handler
# --------------------------------------------------------------------------- #
_CALL_RE = re.compile(r"api\(\s*'(/api/[^']+)'")
_METHOD_RE = re.compile(r"method:\s*'([A-Z]+)'")
_ACT_RE = re.compile(r'data-act="([^"]+)"')


def _panel_api_calls(src: str) -> set[tuple[str, str]]:
    """Every (path, method) the panel can put on the wire. No method in the opts => GET."""
    found: set[tuple[str, str]] = set()
    for match in _CALL_RE.finditer(src):
        window = src[match.end():match.end() + 60]
        method = _METHOD_RE.search(window)
        found.add((match.group(1), method.group(1) if method else "GET"))
    return found


def _onClick_cases(src: str) -> set[str]:
    start = src.index("function onClick(e)")
    end = src.index("\n  function ", start)
    return set(re.findall(r"case '([^']+)':", src[start:end]))


def _registered_routes(routes=None, seen=None) -> set[tuple[str, str]]:
    """Every (path, method) the mounted app answers, walked through nested routers.

    ``app.include_router`` no longer flattens: on FastAPI >= 0.14 an included router is one
    ``_IncludedRouter`` entry holding the sub-router, so reading ``app.routes`` alone reports
    the panel's four routes as missing even when they are mounted and serving. Walk the tree
    by whatever attribute carries the children — this stays true across both shapes.
    """
    import app.main as main
    seen = seen if seen is not None else set()
    table: set[tuple[str, str]] = set()
    for route in (main.app.routes if routes is None else routes):
        if id(route) in seen:
            continue
        seen.add(id(route))
        path, methods = getattr(route, "path", None), getattr(route, "methods", None)
        if path and methods:
            table.update((path, method.upper()) for method in methods)
        for attr in ("routes", "router", "original_router"):
            child = getattr(route, attr, None)
            children = getattr(child, "routes", None) if attr != "routes" else child
            if children:
                table |= _registered_routes(children, seen)
    return table


def test_t6_every_panel_api_call_has_a_registered_route():
    """The RED heart of this packet: on origin/main the four POSTs match nothing."""
    registered = _registered_routes()
    calls = _panel_api_calls(ACCOUNT_JS.read_text(encoding="utf-8"))
    assert calls, "found no api() calls — did account.js change shape?"
    missing = sorted(c for c in calls if c not in registered)
    assert not missing, (
        f"account.js calls these with no FastAPI route to answer them: {missing}. "
        "A control that cannot be answered must not be rendered.")
    for path in FOUR_ROUTES:
        assert (path, "POST") in registered, path


def test_t6_every_rendered_data_act_has_an_onclick_case():
    src = ACCOUNT_JS.read_text(encoding="utf-8")
    rendered = set(_ACT_RE.findall(src))
    handled = _onClick_cases(src)
    assert rendered, "found no data-act attributes — did account.js change shape?"
    assert handled, "found no onClick cases — did account.js change shape?"
    assert not sorted(rendered - handled), \
        f"rendered controls with no handler: {sorted(rendered - handled)}"


def test_t6_no_error_branch_falls_back_to_a_body_the_server_never_sends():
    """R4: every panel error branch reads the plain-word helper."""
    src = ACCOUNT_JS.read_text(encoding="utf-8")
    assert "r.data.error || T('err')" not in src
    assert "function errText(r)" in src
    assert src.count("errText(r)") >= 4, "the helper plus its three call sites"
    for branch in ("mmacc-email-msg", "mmacc-pw-msg", "mmacc-del-msg"):
        assert f"'{branch}', errText(r), 'bad'" in src, branch


# --------------------------------------------------------------------------- #
# t7 — the deployed artifact is not stale
# --------------------------------------------------------------------------- #
def test_t7_site_account_js_is_byte_identical_to_the_template():
    assert ACCOUNT_JS.read_bytes() == SITE_ACCOUNT_JS.read_bytes()


def test_t7_site_theme_js_equals_what_the_emitter_produces():
    """``site/theme.js`` is NOT a plain copy: ``lib.site_assets.emit_theme_js`` bakes the
    public Supabase config, the mm_brain version and the Terminal overlay into it, so
    byte-equality with the template is impossible by design and was never the law. The law
    (``ui.template_site_sync``, enforced by ``scripts/check_template_site_sync.py``) is that
    the committed site copy equals the emitter's output from the committed template.
    """
    from lib.site_assets import emit_theme_js
    assert emit_theme_js(THEME_JS) == SITE_THEME_JS.read_text(encoding="utf-8")
    for path in (THEME_JS, SITE_THEME_JS):
        assert f"account.js?v={RELEASE_KEY}" in path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# t8 — API base text contract
# --------------------------------------------------------------------------- #
def test_t8_api_base_is_same_origin_on_mastermind_x_hosts():
    src = ACCOUNT_JS.read_text(encoding="utf-8")
    lines = [ln for ln in src.splitlines() if ln.strip().startswith("var API =")]
    assert len(lines) == 1, lines
    line = lines[0]
    assert r"/(^|\.)mastermind-x\.com$/i.test(location.hostname || '')" in line
    assert r"(window.MM_API || '').replace(/\/+$/, '')" in line
    # The reason is written down where the next reader will trip over it.
    assert "CORS" in src.split("var API =")[0][-400:]


def test_t8_the_release_key_moved_with_the_payload_it_busts():
    """account.js is served ``immutable, max-age=31536000`` at a hand-written key."""
    src = ACCOUNT_JS.read_text(encoding="utf-8")
    assert f"nav_market.js?v={RELEASE_KEY}" in src
    assert "20260814-sf-inter-font-upgrade" not in src


# --------------------------------------------------------------------------- #
# t9 — copy
# --------------------------------------------------------------------------- #
CJK_PUNCT = "，。；：、！？（）「」『』—…·"
CJK_IDEOGRAPH = re.compile(r"[\u4e00-\u9fff]")
BANNED = ("falsifier", "refuted", "validated", "证伪")
#: Sentence copy added or rewritten by this packet must carry CJK punctuation. A button
#: label must not: '发送申请。' is not how a button reads, so labels are held to "real
#: Chinese" only, and the sentences carry the punctuation requirement.
SENTENCE_KEYS = ("delete_warn", "del_ok", "del_open")
LABEL_KEYS = ("delete_acct", "delete_go")


def _entry(src: str, key: str) -> tuple[str, str]:
    match = re.search(rf"\b{key}:\s*\[(.*?)\]", src, re.S)
    assert match, f"no STR entry for {key}"
    parts = re.findall(r"'((?:[^'\\]|\\.)*)'", match.group(1), re.S)
    assert len(parts) == 2, (key, parts)
    return parts[0], parts[1]


def test_t9_every_added_panel_string_has_a_real_chinese_twin():
    src = ACCOUNT_JS.read_text(encoding="utf-8")
    for key in SENTENCE_KEYS + LABEL_KEYS:
        en, zh = _entry(src, key)
        assert en.strip() and zh.strip(), key
        assert CJK_IDEOGRAPH.search(zh), f"{key} ZH twin has no Chinese in it"
        if key in SENTENCE_KEYS:
            assert any(ch in zh for ch in CJK_PUNCT), f"{key} ZH twin has no CJK punctuation"
        if key in ("del_ok", "del_open"):
            assert "{code}" in en and "{code}" in zh, key


def test_t9_no_deletion_control_claims_an_immediate_deletion():
    """F8: this control FILES a request. It deletes nothing, so it must not say it does."""
    src = ACCOUNT_JS.read_text(encoding="utf-8")
    assert "permanently" not in src.lower()
    assert "永久" not in src
    for key in SENTENCE_KEYS + LABEL_KEYS + ("delete_type", "danger"):
        en, zh = _entry(src, key)
        assert "permanently" not in en.lower() and "永久" not in zh, key


def test_t9_the_panel_never_shows_a_forbidden_word():
    src = ACCOUNT_JS.read_text(encoding="utf-8")
    for word in BANNED:
        assert word not in src.lower(), word


@pytest.mark.parametrize("key", sorted(account_actions.COPY))
def test_t9_every_server_sentence_is_plain_and_bilingual(key):
    en, zh = account_actions.COPY[key]
    assert en.strip().endswith("."), key
    assert CJK_IDEOGRAPH.search(zh), key
    assert any(ch in zh for ch in CJK_PUNCT), f"{key} ZH twin has no CJK punctuation"
    assert not re.search(r"\b[1-5]\d\d\b", en + zh), f"{key} shows an HTTP status on screen"
    for token in ("_", "None", "null", "Traceback", "supabase", "postgrest"):
        assert token not in en and token not in zh.lower(), f"{key} shows machine text"
    for word in BANNED:
        assert word not in en.lower() and word not in zh, key


def test_t9_the_specified_sentences_are_verbatim():
    """Five sentences the frozen spec dictates word for word."""
    expected = {
        "busy": ("The account service is busy. Nothing was changed. "
                 "Please try again in a moment.",
                 "账户服务繁忙，未做任何改动。请稍后再试。"),
        "no_answer": ("The account service did not answer. Nothing was changed. "
                      "Please try again in a moment.",
                      "账户服务没有响应，未做任何改动。请稍后再试。"),
        "rate_limited": ("Too many attempts. Please wait a few minutes and try again.",
                         "尝试次数过多，请几分钟后再试。"),
        "delete_confirm": ("Type the email on this account to confirm.",
                           "请输入此账户的邮箱以确认。"),
        "delete_not_recorded": ("We could not record your request, so nothing was filed and "
                                "nothing was changed. Please try again later.",
                                "我们无法记录你的请求，因此没有提交任何申请，"
                                "你的账户也没有任何改动。请稍后再试。"),
    }
    for key, pair in expected.items():
        assert account_actions.COPY[key] == pair, key


# --------------------------------------------------------------------------- #
# module-level safety invariants
# --------------------------------------------------------------------------- #
def test_module_never_names_an_admin_endpoint_or_a_service_role_authorization():
    src = (ROOT / "app" / "account_actions.py").read_text(encoding="utf-8")
    assert "/auth/v1/admin" not in src.replace("``/auth/v1/admin/*`` is never called", "")
    assert 'f"Bearer {service_key}"' not in src
    assert "Authorization\": service_key" not in src
    assert 'f"Bearer {token}"' in src


def test_every_route_depends_on_the_canonical_identity_check():
    """``Depends(_current_user)`` is what makes 401 require_user's own, not a local notion."""
    for route in account_actions.router.routes:
        calls = [dep.call for dep in route.dependant.dependencies]
        assert account_actions._current_user in calls, route.path


def test_a_route_nobody_registered_answers_404(client):
    assert client.post("/api/account/not-a-route", {}, {"Authorization": AUTHZ}).status_code == 404


def test_router_declares_exactly_the_four_routes():
    declared = {(route.path, tuple(sorted(route.methods)))
                for route in account_actions.router.routes}
    assert declared == {(path, ("POST",)) for path in FOUR_ROUTES}
