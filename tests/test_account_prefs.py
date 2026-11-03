"""tests/test_account_prefs.py — app/account_prefs.py (SEE W3 / masterplan R4).

Fully offline: no Supabase, no network. Two seams are stubbed —
``urllib.request.urlopen`` (the auth admin API that stores ``user_metadata``) and
``billing._pg`` (the PostgREST upsert that mirrors ``lang`` into ``email_prefs``).

Coverage:
  - identity comes from the BEARER TOKEN only; a client-sent user_id is ignored.
  - lang/theme validation, including "nothing to save".
  - the metadata write MERGES rather than replacing (an unrelated stored key survives),
    and it merges onto a FRESH read — the cached identity snapshot never reaches the PUT.
  - an unreadable fresh read refuses the write: no PUT, and a 502 when nothing else stored.
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


def test_browser_pending_preferences_account_and_snapshot_fences():
    """Actual controller/consumer code, with storage and provider I/O mocked."""
    import subprocess

    subprocess.run(["node", "--test", str(Path(__file__).resolve().parent / "js" /
                                       "onboarding_pending_prefs.test.cjs")], check=True,
                   capture_output=True, text=True)


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
    assert ei.value.status_code == 400
    assert ei.value.detail["field"] == bad
    assert ei.value.detail["en"] and ei.value.detail["zh"]
    assert auth.calls == [] and store.rows == []


def test_empty_body_is_400(auth, store):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(), user=USER)
    assert ei.value.status_code == 400
    assert auth.calls == [] and store.rows == []


# --------------------------------------------------------------------------- #
# B-F08-1a: alert delivery preferences (email opt-in, category, tz, quiet hours)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value, expected", [
    (True, True), (False, False), ("true", True), ("off", False), ("1", True), ("0", False),
])
def test_alert_email_optin_accepts_bool_and_strings(auth, store, value, expected):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(alert_email_optin=value), user=USER)
    # Turning alerts ON with no tz already known (USER carries none) also applies the
    # server-side default_tz_for_lang default (Meta-CEO B ruling, macro#6907 round 2;
    # see tests/test_alert_prefs.py::
    # test_alerts_on_with_no_tz_defaults_and_round_trips_on_get for the dedicated
    # coverage) -- turning them off never touches tz at all.
    want = {"alert_email_optin": expected}
    if expected:
        want["tz"] = "UTC"
    assert out["prefs"] == want


def test_alert_email_optin_bad_value_is_400(auth, store):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(alert_email_optin="maybe"), user=USER)
    assert ei.value.status_code == 400
    assert ei.value.detail["field"] == "alert_email_optin"
    assert auth.calls == [] and store.rows == []


def test_alert_categories_legal_subset_stored_sorted_deduped(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(alert_categories=["thesis_window", "Holdings_Material_Change",
                                                       "thesis_window"]),
        user=USER)
    assert out["prefs"]["alert_categories"] == ["holdings_material_change", "thesis_window"]


def test_alert_categories_empty_list_is_legal(auth, store):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(alert_categories=[]), user=USER)
    assert out["prefs"]["alert_categories"] == []


def test_alert_categories_unknown_member_rejects_whole_value(auth, store):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(
            account_prefs.PrefsRequest(alert_categories=["holdings_material_change", "wat"]),
            user=USER)
    assert ei.value.status_code == 400
    assert ei.value.detail["field"] == "alert_categories"
    assert auth.calls == [] and store.rows == []


def test_tz_stored_verbatim(auth, store):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(tz="Asia/Hong_Kong"), user=USER)
    assert out["prefs"]["tz"] == "Asia/Hong_Kong"


@pytest.mark.parametrize("bad_tz", ["Mars/Olympus", "asia/hong_kong", ""])
def test_tz_bad_values_are_400(auth, store, bad_tz):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(tz=bad_tz), user=USER)
    assert ei.value.status_code == 400
    assert ei.value.detail["field"] == "tz"
    assert auth.calls == [] and store.rows == []


def test_quiet_hours_stored_as_pair(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(quiet_hours={"start": "22:00", "end": "07:00"}), user=USER)
    assert out["prefs"]["quiet_hours"] == {"start": "22:00", "end": "07:00"}


def test_quiet_hours_off_sentinel_clears(auth, store):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(quiet_hours="off"), user=USER)
    assert out["prefs"]["quiet_hours"] is None


def test_quiet_hours_equal_start_end_normalizes_to_none(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(quiet_hours={"start": "09:00", "end": "09:00"}), user=USER)
    assert out["prefs"]["quiet_hours"] is None


@pytest.mark.parametrize("bad_qh", [
    {"start": "22:00"},
    {"start": "25:00", "end": "07:00"},
    {"start": "22:00", "end": "07:00", "x": 1},
])
def test_quiet_hours_bad_shapes_are_400(auth, store, bad_qh):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(quiet_hours=bad_qh), user=USER)
    assert ei.value.status_code == 400
    assert ei.value.detail["field"] == "quiet_hours"
    assert auth.calls == [] and store.rows == []


def test_alert_prefs_never_touch_email_prefs(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(alert_email_optin=True, tz="UTC"), user=USER)
    assert out["email_prefs"] is False
    assert store.rows == []


def test_all_four_alert_fields_in_one_call(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(alert_email_optin=True,
                                    alert_categories=["thesis_window"],
                                    tz="Asia/Hong_Kong",
                                    quiet_hours={"start": "22:00", "end": "07:00"}),
        user=USER)
    assert out["prefs"] == {
        "alert_email_optin": True, "alert_categories": ["thesis_window"],
        "tz": "Asia/Hong_Kong", "quiet_hours": {"start": "22:00", "end": "07:00"},
    }
    # Main's writer always pays a fresh GET before the PUT (auth-cache clobber close).
    # This request sends tz, so the freeze-§8 extra GET on the route does not fire.
    assert [c[0] for c in auth.calls] == ["GET", "PUT"]


def test_get_prefs_readback(auth, store):
    account_prefs.save_prefs(account_prefs.PrefsRequest(tz="Asia/Hong_Kong"), user=USER)
    user_with_tz = dict(USER, user_metadata=dict(USER["user_metadata"], tz="Asia/Hong_Kong"))
    out = account_prefs.read_prefs(user=user_with_tz)
    assert out["ok"] is True
    assert out["prefs"]["tz"] == "Asia/Hong_Kong"
    assert "alert_email_optin" in out["unset"]
    # DR3 adds the defensive-rotation observation category to the legal-value list. It
    # is offered here and chosen by nobody: the account panel draws its own rows.
    assert out["categories_available"] == ["holdings_material_change", "thesis_window",
                                           "fif_saved_issuer", "options_exposure_node",
                                           "sector_rotation_relative"]


def test_get_prefs_route_is_registered():
    paths_methods = {(r.path, m) for r in account_prefs.router.routes for m in r.methods}
    assert ("/api/account/prefs", "GET") in paths_methods


@pytest.mark.parametrize("value, expected", [("ZH", "zh"), (" en ", "en")])
def test_values_are_normalised(auth, store, value, expected):
    out = account_prefs.save_prefs(account_prefs.PrefsRequest(lang=value), user=USER)
    assert out["prefs"]["lang"] == expected


def test_lang_theme_brain_depth_bad_value_uses_default_error(auth, store):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(account_prefs.PrefsRequest(lang="fr"), user=USER)
    assert ei.value.detail["en"] == "We don't recognise that choice."


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


def test_the_route_merges_from_the_fresh_reader_not_the_cached_snapshot(auth, store,
                                                                        monkeypatch):
    """Seat R2: the route-boundary contract, driven through the REAL handler with the
    fresh reader itself mocked (not merely the socket). ``save_prefs`` must reach
    ``fetch_user_metadata`` with the token-derived id, and the object that reader
    returns — never the caller's cached ``user_metadata`` — must be what the PUT is
    built from. (Replaces test_tz_default_on_the_route_uses_a_fresh_read_not_the_cache,
    which never called save_prefs and asserted a list it had appended to itself.)
    """
    seen: list[tuple[str, object]] = []

    def _fresh(user_id, *, supabase=None):
        seen.append((user_id, supabase))
        return {"lang": "zh", "theme": "dark", "market_focus": ["us", "hk"],
                "never_seen_key": "keep-me"}

    monkeypatch.setattr(account_prefs.user_prefs, "fetch_user_metadata", _fresh)
    stale_user = {
        "id": USER["id"], "email": USER["email"],
        "user_metadata": {"lang": "en", "theme": "light", "display_name": "Ada"},
    }
    account_prefs.save_prefs(
        account_prefs.PrefsRequest(brain_depth="concise"), user=stale_user)

    assert [uid for uid, _ in seen] == ["9c1f-user"], "the route must take a fresh read"
    # The GET is the mocked reader's, so the only thing left on the wire is the PUT.
    assert [c[0] for c in auth.calls] == ["PUT"]
    meta = auth.put()[2]["user_metadata"]
    assert meta["lang"] == "zh"
    assert meta["theme"] == "dark"
    assert meta["market_focus"] == ["us", "hk"]
    assert meta["never_seen_key"] == "keep-me"
    assert meta["brain_depth"] == "concise"
    assert "display_name" not in meta, "the cached snapshot is not the merge base"


def test_an_unreadable_fresh_read_makes_no_put_and_502s(auth, monkeypatch):
    """Seat R3 at the route boundary, and the packet's KNOWN LIMIT in one test.

    ``fetch_user_metadata`` is None when the read could not be completed OR could not
    be made sense of (a 200 whose ``user_metadata`` is absent or not an object). The
    writer refuses, so NO PUT goes out; a brain_depth-only save has no email mirror to
    fall back on, so the route answers 502 "could not save preferences, please try
    again" on a save that succeeded on one PUT before this packet.
    """
    monkeypatch.setattr(account_prefs.user_prefs, "fetch_user_metadata",
                        lambda *a, **k: None)
    monkeypatch.setattr(billing, "_pg", _Store().pg)
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(
            account_prefs.PrefsRequest(brain_depth="concise"), user=USER)
    assert ei.value.status_code == 502
    assert auth.calls == [], "no PUT may follow a read we could not use"


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


# --------------------------------------------------------------------------- #
# Defensive-rotation observations (DR3): the opt-in surface
# --------------------------------------------------------------------------- #
def test_the_new_category_is_a_legal_member_and_is_not_opted_in_by_default(auth, store):
    from lib import user_prefs
    assert "sector_rotation_relative" in user_prefs.ALERT_CATEGORIES
    # Membership in the closed list is what makes a VALUE legal. It is not consent:
    # an account with no stored alert_categories still has none.
    clean, rejected = user_prefs.validate_prefs(
        {"alert_categories": ["sector_rotation_relative"]})
    assert clean["alert_categories"] == ["sector_rotation_relative"] and rejected == []
    assert user_prefs.read_user_prefs(USER) == {"lang": "en"}


def test_saving_the_new_category_alone_writes_exactly_that_value(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(alert_categories=["sector_rotation_relative"]),
        user=USER)
    assert out["prefs"]["alert_categories"] == ["sector_rotation_relative"]
    _, _, body = auth.put()
    assert body["user_metadata"]["alert_categories"] == ["sector_rotation_relative"]


def test_the_new_category_mixes_with_the_legacy_ones_and_dedupes_and_sorts(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(alert_categories=[
            "thesis_window", "sector_rotation_relative", "Sector_Rotation_Relative",
            "holdings_material_change"]), user=USER)
    assert out["prefs"]["alert_categories"] == [
        "holdings_material_change", "sector_rotation_relative", "thesis_window"]


def test_the_new_category_still_refuses_to_broaden_a_bad_neighbour(auth, store):
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(
            account_prefs.PrefsRequest(
                alert_categories=["sector_rotation_relative", "wat"]), user=USER)
    assert ei.value.status_code == 400
    assert ei.value.detail["field"] == "alert_categories"
    assert auth.calls == [] and store.rows == []


def test_clearing_the_new_category_still_clears_everything(auth, store):
    out = account_prefs.save_prefs(
        account_prefs.PrefsRequest(alert_categories=[]), user=USER)
    assert out["prefs"]["alert_categories"] == []


def test_the_readback_offers_the_new_category_but_does_not_choose_it(auth, store):
    """``categories_available`` is the legal-value list the UI may draw from. The account
    panel is HARDCODED and does not auto-render it, so offering the value here must not
    produce a stored preference -- these are two separate surfaces and stay separate."""
    ticked = dict(USER, user_metadata=dict(
        USER["user_metadata"], alert_categories=["sector_rotation_relative"]))
    out = account_prefs.read_prefs(user=ticked)
    assert "sector_rotation_relative" in out["categories_available"]
    assert out["prefs"]["alert_categories"] == ["sector_rotation_relative"]
    assert "alert_categories" not in out["unset"]
    # A reader who never ticks it has not consented to it: the value is OFFERED and
    # unset, which is what the account panel's own row reads to draw an unchecked switch.
    fresh = account_prefs.read_prefs(user=USER)
    assert "sector_rotation_relative" in fresh["categories_available"]
    assert "alert_categories" in fresh["unset"] and "alert_categories" not in fresh["prefs"]
    assert "alert_email_optin" not in fresh["prefs"]


def test_an_unreadable_fresh_read_still_refuses_a_save_of_the_new_category(auth, monkeypatch):
    auth.fail = True
    with pytest.raises(HTTPException) as ei:
        account_prefs.save_prefs(
            account_prefs.PrefsRequest(alert_categories=["sector_rotation_relative"]),
            user=USER)
    assert ei.value.status_code == 502
    assert [c for c in auth.calls if c[0] == "PUT"] == []


# --------------------------------------------------------------------------- #
# Executable account-panel checkbox contract (node executes the real builder)
# --------------------------------------------------------------------------- #
# A source-substring assertion cannot tell a checkbox that RENDERS from one that is
# merely mentioned. These tests extract the real alertPrefsGroupHTML from the shipped
# account.js and RUN it under node against a minimal DOM, so the EN and ZH labels, the
# data-cat identity and the initial on/off state are observed rather than grepped.

def _account_js_harness():
    """Build and execute the account panel's alert-prefs group under node.

    Returns a callable ``render(prefs, unset, lang) -> html``. The slice runs from
    ``function lang(`` (which owns the language switch) through the end of
    ``alertPrefsGroupHTML``; the few document/window members those helpers touch are
    stubbed. Anything else in the file -- mounting, network, theme -- is deliberately
    outside the slice.
    """
    import json
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    node = shutil.which("node")
    assert node is not None, "Node is required for the executable account preference contract"

    src = (Path(__file__).resolve().parent.parent / "templates" / "account.js").read_text()
    start = src.index("function lang(")
    m_start = src.index("function alertPrefsGroupHTML(")
    m_end = src.index("\n  }\n", m_start)
    slice_js = src[start:m_end + len("\n  }\n")]

    driver = """
const fs = require('fs');
const vm = require('vm');
const SLICE = %s;
const current = { lang: 'en' };
const doc = {
  documentElement: { getAttribute: (k) => (k === 'data-lang' ? current.lang : null) },
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  addEventListener: () => {},
};
const ctx = vm.createContext({ document: doc, window: {}, Intl });
vm.runInContext(SLICE + '\\nglobalThis.__group = alertPrefsGroupHTML;', ctx);
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
current.lang = req.lang;
process.stdout.write(String(ctx.__group(req.prefs, req.unset)));
""" % json.dumps(slice_js)

    tmp = Path(tempfile.mkdtemp(prefix="account-harness-"))
    script = tmp / "harness.js"
    script.write_text(driver)

    def render(prefs, unset=(), lang="en"):
        proc = subprocess.run([node, str(script)], capture_output=True, text=True,
                              input=json.dumps({"prefs": prefs, "unset": list(unset),
                                                "lang": lang}), timeout=60)
        assert proc.returncode == 0, proc.stderr
        return proc.stdout

    return render


@pytest.fixture(scope="module")
def account_group():
    return _account_js_harness()


def _switch_row(html, category):
    """The rendered ``[data-act=alert-cat]`` element for one category."""
    import re
    match = re.search(r'<button[^>]*data-cat="%s"[^>]*>' % re.escape(category), html)
    return match.group(0) if match else None


def test_the_new_category_renders_as_a_real_switch_row(account_group):
    html = account_group({"alert_email_optin": True, "alert_categories": [],
                          "tz": "UTC"})
    row = _switch_row(html, "sector_rotation_relative")
    assert row is not None and 'data-act="alert-cat"' in row
    assert html.count('data-act="alert-cat"') == 3      # the two legacy rows + this one


def test_the_new_row_is_unchecked_when_the_reader_has_not_ticked_it(account_group):
    html = account_group({"alert_email_optin": True, "alert_categories": ["thesis_window"],
                          "tz": "UTC"})
    row = _switch_row(html, "sector_rotation_relative")
    assert row is not None and 'aria-checked="false"' in row


def test_the_new_row_is_checked_when_it_is_stored(account_group):
    html = account_group({"alert_email_optin": True,
                          "alert_categories": ["sector_rotation_relative"], "tz": "UTC"})
    row = _switch_row(html, "sector_rotation_relative")
    assert row is not None and 'aria-checked="true"' in row


def test_the_new_row_appears_alongside_both_legacy_rows(account_group):
    html = account_group({"alert_email_optin": True, "alert_categories": [], "tz": "UTC"})
    for cat in ("holdings_material_change", "thesis_window", "sector_rotation_relative"):
        assert _switch_row(html, cat) is not None, cat


def test_the_new_label_is_executably_bilingual(account_group):
    import re
    for lang, want in (("en", "Defensive leadership changes"),
                       ("zh", "防御板块领导力变化")):
        html = account_group({"alert_email_optin": True, "alert_categories": [],
                              "tz": "UTC"}, lang=lang)
        assert want in html, (lang, want)
        # The label is the switch's accessible name, not only loose body text.
        m = re.search(r'<span class="mmacc-k">(.*?)</span>\s*<button[^>]*'
                      r'data-cat="sector_rotation_relative"', html, re.S)
        assert m is not None and want in m.group(1), (lang, "aria label")


def test_the_two_legacy_labels_are_unchanged_by_the_new_row(account_group):
    en = account_group({"alert_email_optin": True, "alert_categories": [], "tz": "UTC"},
                       lang="en")
    assert "A position I hold moves on real news" in en
    assert "A market view I’m watching starts or ends" in en


def test_the_no_categories_hint_still_appears_only_when_none_are_ticked(account_group):
    empty = account_group({"alert_email_optin": True, "alert_categories": [], "tz": "UTC"})
    ticked = account_group({"alert_email_optin": True,
                            "alert_categories": ["sector_rotation_relative"], "tz": "UTC"})
    assert "mmacc-hint-none" in empty
    assert "mmacc-hint-none" not in ticked


def test_the_template_and_the_rendered_site_copy_are_byte_identical():
    """House law: the account panel ships as a paired textual artifact. The new row
    must reach both, or one of the two properties silently loses the opt-in."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    tmpl = (root / "templates" / "account.js").read_text()
    site = (root / "site" / "account.js").read_text()
    assert tmpl == site
    # Twice per file: the row identity and the membership test that sets its
    # initial state. Any other count means a stray or duplicated occurrence.
    assert tmpl.count("sector_rotation_relative") == 2
    assert site.count("sector_rotation_relative") == 2
