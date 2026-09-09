"""tests/test_account_prefs.py — app/account_prefs.py (SEE W3 / masterplan R4).

Fully offline: no Supabase, no network. Two seams are stubbed —
``urllib.request.urlopen`` (the auth admin API that stores ``user_metadata``) and
``billing._pg`` (the PostgREST upsert that mirrors ``lang`` into ``email_prefs``).

Coverage:
  - identity comes from the BEARER TOKEN only; a client-sent user_id is ignored.
  - lang/theme validation, including "nothing to save".
  - the metadata write MERGES rather than replacing (an unrelated stored key survives).
  - lang mirrors into email_prefs; theme alone does not touch it.
  - fail-soft: a partial failure still 200s with an honest per-sink flag; a total failure
    is an honest 502 rather than a lie.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import account_prefs, billing  # noqa: E402

USER = {"id": "9c1f-user", "email": "reader@example.com",
        "user_metadata": {"display_name": "Ada", "lang": "en"}}


class _Resp:
    def __init__(self, body=b"{}"):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


class _Auth:
    """Records every admin-API call the module makes. GET returns ``metadata``
    so the writer can take a fresh read; PUT is recorded, not applied.
    """

    def __init__(self, fail=False, metadata=None):
        self.calls: list[tuple[str, str, dict]] = []
        self.fail = fail
        self.metadata = dict(USER["user_metadata"] if metadata is None else metadata)

    def urlopen(self, req, timeout=None):
        method = req.get_method()
        payload = json.loads(req.data.decode()) if req.data else {}
        self.calls.append((method, req.full_url, payload))
        if self.fail:
            raise OSError("supabase unreachable")
        if method == "GET":
            return _Resp(json.dumps(
                {"id": USER["id"], "user_metadata": dict(self.metadata)}).encode())
        return _Resp()

    def put(self) -> tuple[str, str, dict]:
        return next(c for c in self.calls if c[0] == "PUT")


class _Store:
    def __init__(self, fail=False):
        self.rows: list[dict] = []
        self.fail = fail

    def pg(self, method, path, body=None, prefer=None, timeout=6):
        if self.fail:
            raise RuntimeError("postgrest down")
        self.rows.append({"method": method, "path": path, "body": body, "prefer": prefer})
        return None


@pytest.fixture
def auth(monkeypatch) -> _Auth:
    a = _Auth()
    monkeypatch.setattr(urllib.request, "urlopen", a.urlopen)
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    monkeypatch.setattr(billing, "SUPABASE_URL", "https://proj.supabase.test")
    return a


@pytest.fixture
def store(monkeypatch) -> _Store:
    s = _Store()
    monkeypatch.setattr(billing, "_pg", s.pg)
    return s


# --------------------------------------------------------------------------- #
# auth
# --------------------------------------------------------------------------- #
def test_identity_comes_from_require_user(monkeypatch):
    """Same secretless verification every authed route uses — no local notion of 'who'."""
    seen = {}
    import app.main as main

    def _verify(authz):
        seen["authz"] = authz
        return USER

    monkeypatch.setattr(main, "require_user", _verify)
    assert account_prefs._current_user("Bearer tok-123") == USER
    assert seen["authz"] == "Bearer tok-123"


def test_unauthed_call_is_401(monkeypatch):
    import app.main as main

    def _reject(authz):
        raise HTTPException(401, "missing bearer token")

    monkeypatch.setattr(main, "require_user", _reject)
    with pytest.raises(HTTPException) as ei:
        account_prefs._current_user(None)
    assert ei.value.status_code == 401


def test_user_without_an_id_is_401(auth, store):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(lang="zh"), user={"email": "x@y.z"})
    assert ei.value.status_code == 401


def test_client_sent_user_id_is_ignored(auth, store):
    """Never trust the client: the write targets the TOKEN's user, whatever the body says."""
    body = account_prefs.PrefsRequest.model_validate(
        {"lang": "zh", "user_id": "attacker-uuid", "id": "attacker-uuid"})
    assert not hasattr(body, "user_id")
    account_prefs.save_prefs(body, user=USER)
    _, url, _ = auth.put()
    assert url.endswith("/auth/v1/admin/users/9c1f-user")
    assert "attacker-uuid" not in url
    assert store.rows[0]["body"][0]["user_id"] == "9c1f-user"


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("payload, bad", [
    ({"lang": "fr"}, "lang"),
    ({"lang": "en-US"}, "lang"),
    ({"theme": "sepia"}, "theme"),
    ({"theme": ""}, "theme"),
    ({"brain_depth": "turbo"}, "brain_depth"),
    ({"brain_depth": "short"}, "brain_depth"),
    ({"brain_depth": ""}, "brain_depth"),
])
def test_unknown_values_are_400(auth, store, payload, bad):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(**payload), user=USER)
    assert ei.value.status_code == 400 and bad in ei.value.detail
    assert auth.calls == [] and store.rows == []


def test_empty_body_is_400(auth, store):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(), user=USER)
    assert ei.value.status_code == 400
    assert auth.calls == [] and store.rows == []


@pytest.mark.parametrize("value, expected", [("ZH", "zh"), (" en ", "en")])
def test_values_are_normalised(auth, store, value, expected):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(lang=value), user=USER)
    assert out["prefs"]["lang"] == expected


# --------------------------------------------------------------------------- #
# storage
# --------------------------------------------------------------------------- #
def test_metadata_write_merges_and_does_not_drop_other_keys(auth, store):
    """A partial user_metadata body has replaced the whole object on some GoTrue versions —
    the merge happens here, from a fresh admin GET, never the cached identity snapshot."""
    account_prefs.save_prefs(account_prefs.PrefsRequest(theme="dark"), user=USER)
    method, url, payload = auth.put()
    assert method == "PUT"
    assert url == "https://proj.supabase.test/auth/v1/admin/users/9c1f-user"
    assert payload["user_metadata"] == {"display_name": "Ada", "lang": "en", "theme": "dark"}
    assert [c[0] for c in auth.calls] == ["GET", "PUT"]


def test_lang_mirrors_into_email_prefs(auth, store):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(lang="zh"), user=USER)
    assert out == {"ok": True, "prefs": {"lang": "zh"}, "metadata": True, "email_prefs": True}
    row = store.rows[0]
    assert row["method"] == "POST"
    assert row["path"] == "email_prefs?on_conflict=user_id"
    assert row["prefer"] == "resolution=merge-duplicates,return=minimal"
    assert row["body"][0]["user_id"] == "9c1f-user"
    assert row["body"][0]["lang"] == "zh"
    assert row["body"][0]["updated_at"].startswith("20")


def test_theme_only_does_not_touch_email_prefs(auth, store):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(theme="light"), user=USER)
    assert out["email_prefs"] is False
    assert store.rows == []


def test_both_keys_in_one_call(auth, store):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(lang="en", theme="dark"), user=USER)
    assert out["prefs"] == {"lang": "en", "theme": "dark"}
    assert auth.put()[2]["user_metadata"]["theme"] == "dark"
    assert store.rows[0]["body"][0]["lang"] == "en"


# --------------------------------------------------------------------------- #
# brain_depth (Analyst OS W3) — the chat answer-length preference
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value, expected", [
    ("concise", "concise"), ("standard", "standard"), ("DEEP", "deep"), (" deep ", "deep"),
])
def test_brain_depth_is_accepted_and_normalised(auth, store, value, expected):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(brain_depth=value), user=USER)
    assert out["prefs"] == {"brain_depth": expected}
    assert auth.put()[2]["user_metadata"] == {
        "display_name": "Ada", "lang": "en", "brain_depth": expected}


def test_brain_depth_alone_does_not_touch_email_prefs(auth, store):
    """The email mirror exists for LANGUAGE. A depth change must not write a row."""
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(brain_depth="deep"), user=USER)
    assert out["email_prefs"] is False
    assert store.rows == []


def test_all_three_keys_in_one_call(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(lang="zh", theme="dark", brain_depth="concise"), user=USER)
    assert out["prefs"] == {"lang": "zh", "theme": "dark", "brain_depth": "concise"}
    assert auth.put()[2]["user_metadata"] == {
        "display_name": "Ada", "lang": "zh", "theme": "dark", "brain_depth": "concise"}
    assert store.rows[0]["body"][0]["lang"] == "zh"


def test_stale_cached_snapshot_never_reaches_the_put(auth, store):
    """Seat R3: USER.user_metadata is the identity-cache snapshot (lang=en). The
    fresh GET returns Terminal keys the cache has not seen. Those land on the PUT;
    the stale lang/theme do not.
    """
    auth.metadata = {
        "lang": "zh", "theme": "dark", "market_focus": ["us", "hk"],
        "never_seen_key": "keep-me", "display_name": "Ada",
    }
    stale_user = {
        "id": USER["id"], "email": USER["email"],
        "user_metadata": {"lang": "en", "theme": "light", "display_name": "Ada"},
    }
    account_prefs.save_prefs(
        account_prefs.PrefsRequest(brain_depth="concise"), user=stale_user)
    assert [c[0] for c in auth.calls] == ["GET", "PUT"]
    meta = auth.put()[2]["user_metadata"]
    assert meta["lang"] == "zh"
    assert meta["theme"] == "dark"
    assert meta["market_focus"] == ["us", "hk"]
    assert meta["never_seen_key"] == "keep-me"
    assert meta["brain_depth"] == "concise"


def test_tz_default_on_the_route_uses_a_fresh_read_not_the_cache(auth, store, monkeypatch):
    """Seat R2/R3: when the tz-default rule is about to fire, the route re-reads.
    A tz present in the fresh read is not overwritten; a None fresh read does
    not fire. Exercised through the helper the route calls, because this branch
    of PrefsRequest has no alert_email_optin on origin/main (that field lands
    with #6907).
    """
    seen = []

    def _fetch(user_id, *, supabase=None):
        seen.append((user_id, supabase))
        return {"tz": "Asia/Hong_Kong", "lang": "en"}

    monkeypatch.setattr(account_prefs.user_prefs, "fetch_user_metadata", _fetch)
    patch = {"alert_email_optin": True}
    # Mimic the route's "about to fire" gate, then the helper.
    fresh = account_prefs.user_prefs.fetch_user_metadata("9c1f-user", supabase=("u", "k"))
    account_prefs.user_prefs.apply_tz_default(patch, fresh)
    assert seen and "tz" not in patch

    patch_none = {"alert_email_optin": True, "lang": "zh"}
    account_prefs.user_prefs.apply_tz_default(patch_none, None)
    assert "tz" not in patch_none

    patch_req = {"alert_email_optin": True, "tz": "Europe/London"}
    account_prefs.user_prefs.apply_tz_default(patch_req, {"tz": "UTC"})
    assert patch_req["tz"] == "Europe/London"


def test_the_enum_table_is_the_libs(auth, store):
    """One table, shared with the chat tool — a value the route accepts is a value the
    gateway's set_chat_preference accepts, because there is only one list."""
    from lib import user_prefs

    assert account_prefs.LANGS is user_prefs.PREF_VALUES["lang"]
    assert account_prefs.THEMES is user_prefs.PREF_VALUES["theme"]
    assert account_prefs.DEPTHS is user_prefs.PREF_VALUES["brain_depth"]


def test_the_route_pays_a_fresh_get_then_a_put(auth, store):
    """The cached identity snapshot is never the merge base. Every prefs write
    takes an uncached admin GET, then PUTs. (Was
    test_the_route_still_makes_exactly_one_network_call.)
    """
    account_prefs.save_prefs(account_prefs.PrefsRequest(brain_depth="concise"), user=USER)
    assert [c[0] for c in auth.calls] == ["GET", "PUT"]


# --------------------------------------------------------------------------- #
# fail-soft
# --------------------------------------------------------------------------- #
def test_partial_failure_is_reported_honestly(monkeypatch, store):
    """The mirror is not load-bearing — a metadata write that landed is still a success,
    and the response says which sink took it rather than claiming both did."""
    failing = _Auth(fail=True)
    monkeypatch.setattr(urllib.request, "urlopen", failing.urlopen)
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(lang="zh"), user=USER)
    assert out == {"ok": True, "prefs": {"lang": "zh"}, "metadata": False, "email_prefs": True}


def test_total_failure_is_a_502_not_a_lie(monkeypatch):
    failing = _Auth(fail=True)
    monkeypatch.setattr(urllib.request, "urlopen", failing.urlopen)
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    monkeypatch.setattr(billing, "_pg", _Store(fail=True).pg)
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(lang="zh"), user=USER)
    assert ei.value.status_code == 502


def test_unconfigured_service_role_skips_the_metadata_write(monkeypatch, store):
    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "")
    called = []
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **kw: called.append(1) or _Resp())
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(lang="en"), user=USER)
    assert called == [] and out["metadata"] is False and out["email_prefs"] is True


# --------------------------------------------------------------------------- #
# the route is actually mounted
# --------------------------------------------------------------------------- #
def test_route_is_registered_on_the_router():
    paths = {r.path for r in account_prefs.router.routes}
    assert "/api/account/prefs" in paths
    route = next(r for r in account_prefs.router.routes if r.path == "/api/account/prefs")
    assert "POST" in route.methods
