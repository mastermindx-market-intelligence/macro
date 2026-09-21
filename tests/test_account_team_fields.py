"""tests/test_account_team_fields.py — GET /api/account `teams` field (B-F12-B5-3a).

Fully offline. ``urllib.request.urlopen`` is stubbed; there is no live PostgREST
probe and no production credential. The RLS-path assertion inspects the mocked
transport's outgoing headers.

Route-level cases call the ``account`` handler directly rather than TestClient:
the ``billing-emails`` job that names this suite does not install ``httpx``, and
widening that install line would split the shared venv with sibling billing jobs.
A handler that returns a dict without raising is FastAPI's 200 path. This deviation
from spec §2.5 is authorized by seat ruling R5 of the Round 2 rulings ("route tests
stay direct calls (disclosed)"); what direct calls cannot reach — FastAPI's
``Depends``/``Header`` resolution and the HTTP 200 status — is named in the PR's
GAPS section rather than claimed as covered.
"""
from __future__ import annotations

import builtins
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import team_membership  # noqa: E402

CALLER_TOKEN = "caller-access-token"
SERVICE_KEY = "service-role-test-key"
SUPABASE_URL = "https://proj.supabase.test"
USER_ID = "9c1f-user"
SUPABASE = (SUPABASE_URL, SERVICE_KEY)


class _Resp:
    def __init__(self, body=b"[]"):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


class _Transport:
    """Records every PostgREST call; optionally fails or returns a canned body."""

    def __init__(self, body=b"[]", error=None):
        self.calls: list = []
        self.timeouts: list = []
        self.body = body
        self.error = error

    def urlopen(self, req, timeout=None):
        self.calls.append(req)
        self.timeouts.append(timeout)
        if self.error is not None:
            raise self.error
        return _Resp(self.body)


def _hdr(req, name: str) -> str | None:
    """urllib capitalizes only the first letter (``apikey`` → ``Apikey``)."""
    cap = name[:1].upper() + name[1:] if name else name
    return (
        req.get_header(name)
        or req.get_header(cap)
        or req.headers.get(name)
        or req.headers.get(cap)
    )


def _http_error(code: int = 500, body: bytes = b'{"message":"nope"}') -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        f"{SUPABASE_URL}/rest/v1/team_members",
        code,
        "error",
        hdrs=None,
        fp=io.BytesIO(body),
    )


def _row(team_id: str, role: str, name: str) -> dict:
    return {"team_id": team_id, "role": role, "teams": {"name": name}}


def _fetch(monkeypatch, *, body=None, rows=None, error=None, token=CALLER_TOKEN,
           user_id=USER_ID, supabase=SUPABASE):
    if body is None:
        body = json.dumps(rows if rows is not None else []).encode()
    transport = _Transport(body=body, error=error)
    monkeypatch.setattr(urllib.request, "urlopen", transport.urlopen)
    result = team_membership.fetch_caller_teams(token, user_id, supabase)
    return result, transport


# --------------------------------------------------------------------------- #
# 1. RLS-path assertion — Authorization is the caller's token, never service role
# --------------------------------------------------------------------------- #
def test_rls_path_authorization_is_caller_token_never_service_role(monkeypatch):
    result, transport = _fetch(monkeypatch)
    assert result["status"] == "ok"
    assert len(transport.calls) == 1
    req = transport.calls[0]
    authz = _hdr(req, "Authorization")
    apikey = _hdr(req, "Apikey")
    assert authz == f"Bearer {CALLER_TOKEN}"
    assert apikey == SERVICE_KEY
    assert authz != f"Bearer {SERVICE_KEY}"
    assert SERVICE_KEY not in authz


# --------------------------------------------------------------------------- #
# 2. Own-row filter
# --------------------------------------------------------------------------- #
def test_own_row_filter_is_on_the_request_path(monkeypatch):
    _result, transport = _fetch(monkeypatch)
    url = transport.calls[0].get_full_url()
    assert f"user_id=eq.{urllib.parse.quote(USER_ID)}" in url


# --------------------------------------------------------------------------- #
# 3. Empty membership is ok, never collapsed with unavailable
# --------------------------------------------------------------------------- #
def test_empty_membership_is_ok_not_unavailable(monkeypatch):
    result, transport = _fetch(monkeypatch, rows=[])
    assert result == {"status": "ok", "items": [], "truncated": False}
    assert transport.calls  # a request WAS sent — empty is not "we could not check"


# --------------------------------------------------------------------------- #
# 4. One team, shape
# --------------------------------------------------------------------------- #
def test_one_team_shape(monkeypatch):
    result, _transport = _fetch(monkeypatch, rows=[_row("t-acme", "owner", "Acme")])
    assert result["status"] == "ok"
    assert result["truncated"] is False
    assert result["items"] == [
        {"team_id": "t-acme", "team_name": "Acme", "role": "owner"},
    ]


# --------------------------------------------------------------------------- #
# 5. Truncation — 21 rows → 20 items, truncated true
# --------------------------------------------------------------------------- #
def test_truncation_caps_at_20(monkeypatch):
    rows = [_row(f"t-{i}", "member", f"N{i}") for i in range(21)]
    result, _transport = _fetch(monkeypatch, rows=rows)
    assert result["status"] == "ok"
    assert result["truncated"] is True
    assert len(result["items"]) == 20


# --------------------------------------------------------------------------- #
# 6. Malformed row dropped; truncated still reflects the query cap
# --------------------------------------------------------------------------- #
def test_malformed_row_dropped_without_changing_truncated(monkeypatch):
    rows = [_row("t-bad", "superuser", "Nope")]
    rows += [_row(f"t-{i}", "member", f"N{i}") for i in range(20)]
    result, _transport = _fetch(monkeypatch, rows=rows)
    assert result["status"] == "ok"
    assert result["truncated"] is True
    assert all(item["role"] in ("owner", "admin", "member") for item in result["items"])
    assert "t-bad" not in {item["team_id"] for item in result["items"]}
    # first 20 of 21 include the bad row, so 19 well-formed items
    assert len(result["items"]) == 19


# --------------------------------------------------------------------------- #
# 7. Network failure → unavailable, no crash
# --------------------------------------------------------------------------- #
def test_network_failure_is_unavailable(monkeypatch):
    result, transport = _fetch(monkeypatch, error=OSError("supabase unreachable"))
    assert result == {"status": "unavailable", "items": [], "truncated": False}
    assert len(transport.calls) == 1


# --------------------------------------------------------------------------- #
# 8. Non-200 / malformed JSON → unavailable
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "error,body",
    [
        (_http_error(500), None),
        (_http_error(401), None),
        (None, b"not-json"),
        (None, b'{"error":"not a list"}'),
    ],
    ids=["http-500", "http-401", "malformed-json", "non-list-json"],
)
def test_non_200_or_malformed_json_is_unavailable(monkeypatch, error, body):
    kwargs = {"error": error} if error is not None else {"body": body}
    result, _transport = _fetch(monkeypatch, **kwargs)
    assert result == {"status": "unavailable", "items": [], "truncated": False}


# --------------------------------------------------------------------------- #
# 9–10. Hostile: missing token / user_id never fall back to service-role auth
# --------------------------------------------------------------------------- #
def test_missing_token_never_sends_a_request(monkeypatch):
    called = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
    for token in (None, ""):
        called.clear()
        result = team_membership.fetch_caller_teams(token, USER_ID, SUPABASE)
        assert result == {"status": "unavailable", "items": [], "truncated": False}
        assert called == []


def test_missing_user_id_never_sends_a_request(monkeypatch):
    called = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
    for user_id in ("", None):
        called.clear()
        result = team_membership.fetch_caller_teams(CALLER_TOKEN, user_id, SUPABASE)
        assert result == {"status": "unavailable", "items": [], "truncated": False}
        assert called == []


def test_extract_bearer_matches_require_user_contract():
    assert team_membership.extract_bearer("Bearer abc") == "abc"
    assert team_membership.extract_bearer("Bearer ") is None
    assert team_membership.extract_bearer("bearer abc") is None
    assert team_membership.extract_bearer(None) is None
    assert team_membership.extract_bearer("") is None


# --------------------------------------------------------------------------- #
# 11–12. Route-level: teams key present; a team-read failure never 500s
# --------------------------------------------------------------------------- #
USER = {
    "id": USER_ID,
    "email": "reader@example.com",
    "email_confirmed_at": "2026-01-01T00:00:00Z",
    "user_metadata": {"display_name": "Ada", "lang": "en", "theme": "dark"},
}

_ENT = {
    "tier": "essential",
    "features": ["site_full"],
    "status": "active",
    "current_period_end": "2026-12-01T00:00:00Z",
    "interval": "monthly",
}


def _patch_account_deps(monkeypatch, fetch):
    from app import billing
    import app.main as main

    monkeypatch.setattr(main, "require_user", lambda authorization=None: USER)
    monkeypatch.setattr(billing, "read_entitlement", lambda uid: dict(_ENT))
    monkeypatch.setattr(billing, "SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", SERVICE_KEY)
    monkeypatch.setattr(team_membership, "fetch_caller_teams", fetch)


def test_account_route_includes_teams_key(monkeypatch):
    seen = {}

    def fake_fetch(token, user_id, supabase):
        seen["token"] = token
        seen["user_id"] = user_id
        seen["supabase"] = supabase
        return {
            "status": "ok",
            "items": [{"team_id": "t-acme", "team_name": "Acme", "role": "owner"}],
            "truncated": False,
        }

    _patch_account_deps(monkeypatch, fake_fetch)
    from app.main import account, app

    route = next(r for r in app.routes if getattr(r, "path", None) == "/api/account")
    assert "GET" in route.methods

    body = account(user=USER, authorization=f"Bearer {CALLER_TOKEN}")
    assert body["teams"] == {
        "status": "ok",
        "items": [{"team_id": "t-acme", "team_name": "Acme", "role": "owner"}],
        "truncated": False,
    }
    assert seen["token"] == CALLER_TOKEN
    assert seen["user_id"] == USER_ID
    assert seen["supabase"] == SUPABASE


def test_account_route_survives_team_read_failure(monkeypatch):
    def fake_fetch(*_a, **_kw):
        return {"status": "unavailable", "items": [], "truncated": False}

    _patch_account_deps(monkeypatch, fake_fetch)
    from app.main import account

    body = account(user=USER, authorization=f"Bearer {CALLER_TOKEN}")
    assert body["teams"] == {"status": "unavailable", "items": [], "truncated": False}
    # Pre-existing payload is intact — a team-read miss is not a 500 and not an empty list.
    assert body["authenticated"] is True
    assert body["email"] == USER["email"]
    assert body["name"] == "Ada"
    assert body["tier"] == "essential"
    assert body["plan_label"] == "Essential"
    assert body["status"] == "active"
    assert body["features"] == ["site_full"]
    assert body["current_period_end"] == _ENT["current_period_end"]
    assert body["interval"] == "monthly"
    assert body["prefs"] == {"lang": "en", "theme": "dark"}
    assert body["plans_url"] == "/plans.html"


def test_account_route_survives_team_read_raise(monkeypatch):
    def boom(*_a, **_kw):
        raise RuntimeError("postgrest exploded")

    _patch_account_deps(monkeypatch, boom)
    from app.main import account

    body = account(user=USER, authorization=f"Bearer {CALLER_TOKEN}")
    assert body["teams"] == {"status": "unavailable", "items": [], "truncated": False}
    assert body["email"] == USER["email"]
    assert body["tier"] == "essential"
    assert body["prefs"]["lang"] == "en"


# --------------------------------------------------------------------------- #
# 13. Seat ruling R2 — the fail-closed result is a FRESH object at every site.
#     A shared module dict shallow-copied with dict() would alias one `items`
#     list into every response for the life of the process, so one .append in a
#     future consumer would poison every subsequent caller.
# --------------------------------------------------------------------------- #
def _unavailable_from(monkeypatch, site: str) -> dict:
    """Produce an `unavailable` result through one of the three fail-closed sites."""
    if site == "falsy-guard":  # lib/team_membership.py — the pre-flight guard
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: None)
        return team_membership.fetch_caller_teams(None, USER_ID, SUPABASE)
    if site == "network-fault":  # the except arm
        result, _t = _fetch(monkeypatch, error=OSError("supabase unreachable"))
        return result
    if site == "non-list-body":  # the shape guard after a successful read
        result, _t = _fetch(monkeypatch, body=b'{"error":"not a list"}')
        return result
    raise AssertionError(f"unknown site {site!r}")


@pytest.mark.parametrize("site", ["falsy-guard", "network-fault", "non-list-body"])
def test_unavailable_is_a_fresh_object_at_every_site(monkeypatch, site):
    first = _unavailable_from(monkeypatch, site)
    assert first == {"status": "unavailable", "items": [], "truncated": False}

    # Mutate the caller's copy exactly as a future consumer might.
    first["items"].append({"team_id": "t-poison", "team_name": "Poison", "role": "owner"})
    first["truncated"] = True
    first["status"] = "ok"

    second = _unavailable_from(monkeypatch, site)
    assert second == {"status": "unavailable", "items": [], "truncated": False}
    assert second is not first
    assert second["items"] is not first["items"]


def test_unavailable_sites_do_not_share_one_items_list(monkeypatch):
    """Cross-site: the guard's list and the network arm's list are different objects."""
    guard = _unavailable_from(monkeypatch, "falsy-guard")
    network = _unavailable_from(monkeypatch, "network-fault")
    assert guard["items"] is not network["items"]


# --------------------------------------------------------------------------- #
# 14. Seat ruling R3 — every shape PostgREST can return for the `teams(name)`
#     embed is handled explicitly. In each case the MEMBERSHIP is kept (team_id
#     and role are the fact /api/account answers) and the status stays "ok";
#     only the display name degrades to "".
# --------------------------------------------------------------------------- #
def _row_with_embed(embed) -> dict:
    row = {"team_id": "t-acme", "role": "owner"}
    if embed is not _ABSENT:
        row["teams"] = embed
    return row


_ABSENT = object()


@pytest.mark.parametrize(
    "embed,expected_name",
    [
        ({"name": "Acme"}, "Acme"),                       # to-one, current PostgREST
        ([{"name": "Acme"}], "Acme"),                     # to-many / older to-one shape
        ([{"name": "Acme"}, {"name": "Second"}], "Acme"),  # first dict wins
        ([], ""),                                         # embed present but empty
        (["Acme"], ""),                                   # list of non-dicts
        (None, ""),                                       # JSON null embed
        (_ABSENT, ""),                                    # key absent entirely
        ("Acme", ""),                                     # bare scalar, not an object
        ({"name": None}, ""),                             # null name inside the object
        ({"name": 42}, ""),                               # non-string name
        ({}, ""),                                         # object without a name key
    ],
    ids=["dict", "list-one", "list-many", "list-empty", "list-of-scalars", "null",
         "absent", "scalar", "null-name", "int-name", "empty-dict"],
)
def test_team_name_embed_shapes_degrade_to_empty_name_not_a_dropped_row(
    monkeypatch, embed, expected_name
):
    result, _transport = _fetch(monkeypatch, rows=[_row_with_embed(embed)])
    assert result["status"] == "ok"          # a name we cannot read is not an outage
    assert result["truncated"] is False
    assert result["items"] == [
        {"team_id": "t-acme", "team_name": expected_name, "role": "owner"},
    ]
    assert isinstance(result["items"][0]["team_name"], str)


# --------------------------------------------------------------------------- #
# 15. Seat ruling R3 — the own-row filter value is FULLY percent-encoded
#     (quote(..., safe="")), so no character in a user id can leak out of the
#     PostgREST filter value.
# --------------------------------------------------------------------------- #
def test_user_id_is_fully_percent_encoded_including_slash(monkeypatch):
    hostile = "a/b?c&d=e#f"
    _result, transport = _fetch(monkeypatch, user_id=hostile)
    url = transport.calls[0].get_full_url()
    assert f"user_id=eq.{urllib.parse.quote(hostile, safe='')}" in url
    assert "user_id=eq.a%2Fb" in url        # the slash is escaped, not passed through
    assert "a/b" not in url.split("user_id=eq.", 1)[1]


# --------------------------------------------------------------------------- #
# 16. Seat ruling R4 — the upstream call is bounded exactly like the auth path
#     it sits beside: a 4-second timeout and a non-blocking semaphore that SHEDS
#     to `unavailable` rather than queueing on the shared worker threadpool.
# --------------------------------------------------------------------------- #
def test_upstream_timeout_is_four_seconds_like_the_bounded_auth_call(monkeypatch):
    _result, transport = _fetch(monkeypatch)
    assert transport.timeouts == [4]
    assert team_membership._TIMEOUT == 4


def test_upstream_semaphore_sheds_instead_of_pinning_the_threadpool(monkeypatch):
    called = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
    held = 0
    try:
        while team_membership._UPSTREAM_SEM.acquire(blocking=False):
            held += 1
        result = team_membership.fetch_caller_teams(CALLER_TOKEN, USER_ID, SUPABASE)
    finally:
        for _ in range(held):
            team_membership._UPSTREAM_SEM.release()
    assert held == team_membership._UPSTREAM_LIMIT
    assert result == {"status": "unavailable", "items": [], "truncated": False}
    assert called == []  # shed BEFORE the network call, never queued behind it


def test_semaphore_is_released_after_a_failing_read(monkeypatch):
    """A shed path that leaked a permit would degrade the route permanently."""
    before = _drain_and_restore()
    _result, _t = _fetch(monkeypatch, error=OSError("supabase unreachable"))
    assert _drain_and_restore() == before


def _drain_and_restore() -> int:
    held = 0
    while team_membership._UPSTREAM_SEM.acquire(blocking=False):
        held += 1
    for _ in range(held):
        team_membership._UPSTREAM_SEM.release()
    return held


# --------------------------------------------------------------------------- #
# 17. Seat ruling R1 (the MAJOR) — the handler's two lazy imports live INSIDE
#     the guard, so the degraded state main.py already models for
#     app.account_prefs (its router mount is wrapped in try/except) degrades the
#     `teams` field to unavailable instead of 500-ing GET /api/account.
#
#     builtins.__import__ is the only lever that reaches these: both modules are
#     already in sys.modules (this file imports lib.team_membership at the top),
#     so every in-handler import is a cache hit and patching the module object
#     cannot simulate the module failing to import.
# --------------------------------------------------------------------------- #
def _block_import(monkeypatch, blocked: str):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        parts = tuple(fromlist or ())
        if name == blocked:
            raise ImportError(f"simulated: cannot import {blocked}")
        if blocked == "lib.team_membership" and name == "lib" and "team_membership" in parts:
            raise ImportError("simulated: cannot import name 'team_membership' from 'lib'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)


@pytest.mark.parametrize("blocked", ["lib.team_membership", "app.account_prefs"])
def test_account_route_survives_a_lazy_import_failure(monkeypatch, blocked):
    reached = []

    def fake_fetch(*_a, **_kw):
        reached.append(1)
        return {"status": "ok", "items": [], "truncated": False}

    _patch_account_deps(monkeypatch, fake_fetch)
    from app.main import account

    _block_import(monkeypatch, blocked)
    try:
        body = account(user=USER, authorization=f"Bearer {CALLER_TOKEN}")
    finally:
        monkeypatch.undo()  # restore __import__ before pytest itself imports anything

    assert body["teams"] == {"status": "unavailable", "items": [], "truncated": False}
    if blocked == "lib.team_membership":
        assert reached == []  # the read is never attempted when its module is gone
    # The rest of the payload is untouched — an import fault degrades one field, not the route.
    assert body["authenticated"] is True
    assert body["email"] == USER["email"]
    assert body["name"] == "Ada"
    assert body["tier"] == "essential"
    assert body["plan_label"] == "Essential"
    assert body["prefs"] == {"lang": "en", "theme": "dark"}
    assert body["plans_url"] == "/plans.html"
