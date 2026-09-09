"""tests/test_user_prefs.py — lib/user_prefs.py (Analyst OS W3).

Fully offline: the ONLY seam is ``urllib.request.urlopen`` (the GoTrue admin API).

What this suite pins:
  1. The enum table is CLOSED — an illegal value is dropped on read and refuses the write,
     and an unknown KEY can never reach ``user_metadata`` through this door.
  2. Every write takes a fresh uncached GET, overlays only this writer's keys, and PUTs the
     merged object. A cached ``base`` is ignored, so a Terminal key stored after the auth
     cache filled cannot be reverted by this writer. A FAILED read still REFUSES the write.
  3. Fail-soft everywhere: no configuration, a dead API, or a junk value → False, never a
     raise. A display preference is not worth a 500.
  4. The freeze §8 tz default decides from that same fresh read; None means do not fire.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import user_prefs  # noqa: E402

SB = ("https://proj.supabase.test", "service-role-test-key")
UID = "9c1f-user"

#: What the account already stores for this user besides the prefs. If a write ever drops
#: `display_name`, a real user loses their name to a theme toggle.
STORED = {"display_name": "Ada", "lang": "en", "onboarded": True}


class _Resp:
    def __init__(self, body: bytes = b"{}"):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


class _Api:
    """Records every admin-API call; answers GETs with ``STORED`` by default."""

    def __init__(self, *, metadata: dict | None = None, fail_get=False, fail_put=False,
                 get_body: bytes | None = None):
        self.calls: list[tuple[str, str, dict | None]] = []
        self.headers: list[dict] = []
        self.metadata = STORED if metadata is None else metadata
        self.fail_get = fail_get
        self.fail_put = fail_put
        self.get_body = get_body

    def urlopen(self, req, timeout=None):
        method = req.get_method()
        payload = json.loads(req.data.decode()) if req.data else None
        self.calls.append((method, req.full_url, payload))
        self.headers.append(dict(req.headers))
        if method == "GET":
            if self.fail_get:
                raise OSError("supabase unreachable")
            if self.get_body is not None:
                return _Resp(self.get_body)
            return _Resp(json.dumps({"id": UID, "user_metadata": self.metadata}).encode())
        if self.fail_put:
            raise OSError("supabase unreachable")
        return _Resp()

    @property
    def methods(self) -> list[str]:
        return [c[0] for c in self.calls]

    def payload_of(self, method: str) -> dict:
        return next(c[2] for c in self.calls if c[0] == method)


@pytest.fixture
def api(monkeypatch) -> _Api:
    a = _Api()
    monkeypatch.setattr(urllib.request, "urlopen", a.urlopen)
    return a


def _install(monkeypatch, a: _Api) -> _Api:
    monkeypatch.setattr(urllib.request, "urlopen", a.urlopen)
    return a


# --------------------------------------------------------------------------- #
# 1. the enum table is closed
# --------------------------------------------------------------------------- #
def test_the_three_keys_and_their_value_sets():
    assert set(user_prefs.PREF_VALUES) == {"lang", "theme", "brain_depth"}
    assert user_prefs.PREF_VALUES["lang"] == ("en", "zh")
    assert user_prefs.PREF_VALUES["theme"] == ("light", "dark")
    assert user_prefs.PREF_VALUES["brain_depth"] == ("concise", "standard", "deep")


@pytest.mark.parametrize("key, raw, expect", [
    ("lang", "zh", "zh"),
    ("lang", "ZH", "zh"),          # normalised, not rejected
    ("lang", " en ", "en"),
    ("theme", "Dark", "dark"),
    ("brain_depth", "CONCISE", "concise"),
    ("brain_depth", "standard", "standard"),
    ("brain_depth", "deep", "deep"),
    ("lang", "en-US", None),       # a locale is not one of the two values
    ("lang", "klingon", None),
    ("theme", "sepia", None),
    ("brain_depth", "turbo", None),
    ("brain_depth", "", None),
    ("brain_depth", 5, None),      # a non-string is never a value
    ("brain_depth", None, None),
    ("tier", "pro", None),         # unknown KEY: no fourth preference through this door
])
def test_normalize_pref(key, raw, expect):
    assert user_prefs.normalize_pref(key, raw) == expect


def test_validate_prefs_names_the_rejected_keys_and_skips_absent_ones():
    clean, rejected = user_prefs.validate_prefs(
        {"lang": "ZH", "theme": "sepia", "brain_depth": None, "tier": "pro"})
    assert clean == {"lang": "zh"}
    # `brain_depth: None` is "don't change this", not junk — absent from BOTH lists.
    assert sorted(rejected) == ["theme", "tier"]


def test_validate_prefs_never_raises_on_junk():
    assert user_prefs.validate_prefs(None) == ({}, [])
    assert user_prefs.validate_prefs({}) == ({}, [])


# --------------------------------------------------------------------------- #
# 2. read: zero network, illegal values dropped
# --------------------------------------------------------------------------- #
def test_read_user_prefs_returns_only_legal_values():
    user = {"id": UID, "user_metadata": {
        "display_name": "Ada", "lang": "zh-CN", "theme": "dark",
        "brain_depth": "concise", "tier": "pro"}}
    # 'zh-CN' is not one of the two stored values — dropped, not guessed into 'zh'. Only a
    # value this module itself would WRITE reads back.
    assert user_prefs.read_user_prefs(user) == {"theme": "dark", "brain_depth": "concise"}


def test_read_user_prefs_on_a_guest_and_on_junk():
    assert user_prefs.read_user_prefs({"id": "guest:abc", "email": ""}) == {}
    assert user_prefs.read_user_prefs({"user_metadata": None}) == {}
    assert user_prefs.read_user_prefs({"user_metadata": "nope"}) == {}
    assert user_prefs.read_user_prefs(None) == {}
    assert user_prefs.read_user_prefs("not a dict") == {}


def test_read_user_prefs_makes_no_network_call(monkeypatch):
    def _boom(*a, **kw):
        raise AssertionError("read_user_prefs must never hit the network")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    assert user_prefs.read_user_prefs({"user_metadata": {"lang": "zh"}}) == {"lang": "zh"}


# --------------------------------------------------------------------------- #
# 3. write: fresh GET, then PUT of fresh ∪ own keys. ``base`` is ignored.
# --------------------------------------------------------------------------- #
def test_write_keeps_unrelated_keys_from_the_fresh_read_not_from_a_passed_base(api):
    """Unrelated keys survive because they come from the fresh GET, not from a
    cached ``base`` the caller still happens to pass. (Was
    test_write_with_base_is_one_put_and_keeps_unrelated_keys.)
    """
    stale = {"display_name": "STALE", "lang": "en"}
    ok = user_prefs.write_user_prefs(UID, {"theme": "dark"}, base=stale, supabase=SB)
    assert ok is True
    assert api.methods == ["GET", "PUT"]
    method, url, payload = next(c for c in api.calls if c[0] == "PUT")
    assert url == f"https://proj.supabase.test/auth/v1/admin/users/{UID}"
    assert payload["user_metadata"] == {
        "display_name": "Ada", "lang": "en", "onboarded": True, "theme": "dark"}
    assert payload["user_metadata"]["display_name"] != "STALE"


def test_write_normalises_before_storing(api):
    user_prefs.write_user_prefs(UID, {"brain_depth": " DEEP "}, base={}, supabase=SB)
    assert api.payload_of("PUT")["user_metadata"]["brain_depth"] == "deep"


def test_write_url_quotes_the_user_id(api):
    user_prefs.write_user_prefs("a b/../c", {"lang": "zh"}, base={}, supabase=SB)
    assert "a%20b%2F..%2Fc" in api.calls[0][1]


def test_write_sends_the_service_role_key_both_ways(api):
    """GoTrue's admin endpoints want the key as BOTH `apikey` and a Bearer — sending only
    one gets a 401 that looks like a bad user id."""
    user_prefs.write_user_prefs(UID, {"lang": "zh"}, base={}, supabase=SB)
    headers = {k.lower(): v for k, v in api.headers[0].items()}
    assert headers["apikey"] == SB[1]
    assert headers["authorization"] == f"Bearer {SB[1]}"
    assert headers["content-type"] == "application/json"


# --------------------------------------------------------------------------- #
# 4. every write GETs first; a failed read refuses the write
# --------------------------------------------------------------------------- #
def test_write_without_base_reads_current_metadata_then_merges(api):
    """There is no longer a no-GET path. methods == ["GET", "PUT"] either way."""
    ok = user_prefs.write_user_prefs(UID, {"brain_depth": "concise"}, supabase=SB)
    assert ok is True
    assert api.methods == ["GET", "PUT"]
    assert api.payload_of("PUT")["user_metadata"] == {
        "display_name": "Ada", "lang": "en", "onboarded": True, "brain_depth": "concise"}


def test_a_failed_read_refuses_the_write(monkeypatch):
    """The whole point: we cannot merge what we could not read, and a partial PUT can
    REPLACE the object. Refusing loses a preference; writing loses the user's name."""
    a = _install(monkeypatch, _Api(fail_get=True))
    assert user_prefs.write_user_prefs(UID, {"lang": "zh"}, supabase=SB) is False
    assert a.methods == ["GET"], "no PUT may follow a read we could not complete"


def test_fetch_user_metadata_distinguishes_unknown_from_empty(monkeypatch):
    """None means "we could not read it"; {} means "we read it and nothing is stored". The
    write path branches on that difference, so it must not collapse."""
    a = _install(monkeypatch, _Api(fail_get=True))
    assert user_prefs.fetch_user_metadata(UID, supabase=SB) is None   # unknown
    assert a.methods == ["GET"]
    _install(monkeypatch, _Api(get_body=b'{"id":"x"}'))
    assert user_prefs.fetch_user_metadata(UID, supabase=SB) == {}     # known-empty
    _install(monkeypatch, _Api(get_body=b'{"user_metadata":"junk"}'))
    assert user_prefs.fetch_user_metadata(UID, supabase=SB) == {}


def test_write_on_a_user_with_no_stored_metadata_yet(monkeypatch):
    _install(monkeypatch, _Api(metadata={}))
    assert user_prefs.write_user_prefs(UID, {"lang": "zh"}, supabase=SB) is True


# --------------------------------------------------------------------------- #
# 5. fail-soft: junk, no config, dead API
# --------------------------------------------------------------------------- #
def test_a_rejected_value_writes_nothing_at_all(api):
    """Strict on purpose: a caller that wants to report WHICH value was wrong validates
    first. A half-applied patch is the worst of the three outcomes."""
    assert user_prefs.write_user_prefs(UID, {"lang": "zh", "theme": "sepia"},
                                      base={}, supabase=SB) is False
    assert api.calls == []


def test_an_empty_patch_writes_nothing(api):
    assert user_prefs.write_user_prefs(UID, {}, base={}, supabase=SB) is False
    assert user_prefs.write_user_prefs(UID, {"lang": None}, base={}, supabase=SB) is False
    assert api.calls == []


def test_unconfigured_supabase_no_ops(api, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    # No env and no injected pair: a service-role PUT must never be aimed at a guessed
    # project, so the write no-ops rather than defaulting.
    assert user_prefs.write_user_prefs(UID, {"lang": "zh"}, base={}) is False
    assert user_prefs.fetch_user_metadata(UID) is None
    assert api.calls == []
    # ...and a half-configured pair is still unconfigured.
    assert user_prefs.write_user_prefs(UID, {"lang": "zh"}, base={},
                                       supabase=("https://x.test", "")) is False
    assert api.calls == []


def test_missing_user_id_no_ops(api):
    assert user_prefs.write_user_prefs("", {"lang": "zh"}, base={}, supabase=SB) is False
    assert api.calls == []


def test_env_supplies_the_pair_when_no_caller_injects_one(api, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://env.supabase.test/")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "env-key")
    assert user_prefs.write_user_prefs(UID, {"lang": "zh"}, base={}) is True
    # trailing slash stripped — one slash, not two
    assert api.calls[0][1] == f"https://env.supabase.test/auth/v1/admin/users/{UID}"


def test_a_dead_api_is_false_never_a_raise(monkeypatch):
    _install(monkeypatch, _Api(fail_put=True))
    assert user_prefs.write_user_prefs(UID, {"lang": "zh"}, base={}, supabase=SB) is False


def test_an_unserialisable_stored_value_is_false_not_a_raise(api, monkeypatch):
    """The fresh read is somebody else's dict. A value json cannot encode must come
    back False — this is a fire-and-forget preference write, not a place to raise.
    (Junk used to live on ``base``, which is no longer encoded.)
    """
    monkeypatch.setattr(
        user_prefs, "fetch_user_metadata", lambda *a, **k: {"weird": object()})
    assert user_prefs.write_user_prefs(UID, {"lang": "zh"}, supabase=SB) is False


def test_a_junk_base_is_ignored_and_the_write_still_reads_fresh(api):
    """``base`` is no longer the merge source (was test_a_non_dict_base_refuses_the_write).
    A non-dict base must not refuse a write we can complete from a fresh read.
    """
    assert user_prefs.write_user_prefs(UID, {"lang": "zh"}, base="nope", supabase=SB) is True
    assert api.methods == ["GET", "PUT"]


# --------------------------------------------------------------------------- #
# B-F08-7a: fresh read, key-scoped merge, Terminal keys survive (seat R1/R3)
# --------------------------------------------------------------------------- #
#: Keys the Terminal writes that this module has never validated. A macro PUT
#: that re-sends a stale snapshot of these is the clobber in the frozen spec §1.3.
_TERMINAL_STATE = {
    "lang": "en",
    "theme": "dark",
    "market_focus": ["us"],
    "markets": {"home": "us", "enabled": ["us"]},
    "terminal": {"start_tf": "D", "updown": "west"},
    "trade_types": ["stocks"],
    "display_name": "Ada",
    "never_seen_key": "keep-me",
}


class _ReplaceGoTrue:
    """Fake GoTrue that REPLACES user_metadata wholesale on PUT (the vendor
    behaviour this writer must survive without assuming a merge). GET returns
    the live store; the caller can mutate ``state`` between the cache fill and
    the write to model the §1.3 interleaving.
    """

    def __init__(self, state: dict):
        self.state = dict(state)
        self.calls: list[tuple[str, dict | None]] = []

    def urlopen(self, req, timeout=None):
        method = req.get_method()
        payload = json.loads(req.data.decode()) if req.data else None
        self.calls.append((method, payload))
        if method == "GET":
            return _Resp(json.dumps({"id": UID, "user_metadata": dict(self.state)}).encode())
        self.state = dict((payload or {}).get("user_metadata") or {})
        return _Resp()

    @property
    def methods(self) -> list[str]:
        return [c[0] for c in self.calls]

    def put_body(self) -> dict:
        return next(c[1] for c in self.calls if c[0] == "PUT")


def test_write_of_a_pref_preserves_unknown_terminal_keys(monkeypatch):
    """Seat R3: a write of brain_depth must leave lang, theme, market_focus, and a
    never-seen key intact. RED against today's writer when it is handed a stale
    ``base`` that predates those Terminal values.
    """
    stale = {"lang": "en", "theme": "light", "display_name": "Ada"}
    live = dict(_TERMINAL_STATE)
    live["lang"] = "zh"
    live["theme"] = "dark"
    live["market_focus"] = ["us", "hk"]
    fake = _ReplaceGoTrue(live)
    monkeypatch.setattr(urllib.request, "urlopen", fake.urlopen)

    ok = user_prefs.write_user_prefs(
        UID, {"brain_depth": "concise"}, base=dict(stale), supabase=SB)
    assert ok is True
    assert fake.methods[0] == "GET", "the write path must call the fresh reader"
    body = fake.put_body()["user_metadata"]
    assert body["lang"] == "zh"
    assert body["theme"] == "dark"
    assert body["market_focus"] == ["us", "hk"]
    assert body["never_seen_key"] == "keep-me"
    assert body["brain_depth"] == "concise"
    # Stale cached values must not be what landed.
    assert body["theme"] != "light"


def test_merge_modelling_fake_keeps_a_key_the_writer_never_saw(monkeypatch):
    """§2.2 case 2: fake starts from a state the writer has NOT seen (unknown
    Terminal key added after any cached base was read). End state keeps it.
    """
    stale = {"lang": "en", "display_name": "Ada"}
    live = {"lang": "en", "display_name": "Ada", "never_seen_key": "keep-me",
            "market_focus": ["us"]}
    fake = _ReplaceGoTrue(live)
    monkeypatch.setattr(urllib.request, "urlopen", fake.urlopen)

    assert user_prefs.write_user_prefs(
        UID, {"brain_depth": "concise"}, base=dict(stale), supabase=SB) is True
    assert fake.state["never_seen_key"] == "keep-me"
    assert fake.state["market_focus"] == ["us"]
    assert fake.state["brain_depth"] == "concise"
    assert fake.state["lang"] == "en"


def test_interleaving_terminal_write_is_not_clobbered(monkeypatch):
    """§2.2 case 4 / spec §1.3: cache filled at T−10s, Terminal writes lang and
    market_focus, then the macro write. Both Terminal choices must survive.
    """
    stale = dict(_TERMINAL_STATE)  # T−10 s snapshot
    live = dict(_TERMINAL_STATE)
    live["lang"] = "zh"
    live["market_focus"] = ["us", "hk"]
    fake = _ReplaceGoTrue(live)
    monkeypatch.setattr(urllib.request, "urlopen", fake.urlopen)

    assert user_prefs.write_user_prefs(
        UID, {"brain_depth": "concise"}, base=dict(stale), supabase=SB) is True
    assert fake.state["lang"] == "zh"
    assert fake.state["market_focus"] == ["us", "hk"]
    assert fake.state["brain_depth"] == "concise"


def test_stale_cached_snapshot_never_reaches_the_put(monkeypatch):
    """Seat R3: the write path calls the fresh reader; a cached snapshot passed
    as ``base`` is not what gets PUT.
    """
    stale = {"lang": "en", "theme": "light", "secret_from_cache": "stale"}
    live = {"lang": "zh", "theme": "dark", "never_seen_key": "keep-me"}
    fake = _ReplaceGoTrue(live)
    monkeypatch.setattr(urllib.request, "urlopen", fake.urlopen)

    assert user_prefs.write_user_prefs(
        UID, {"theme": "dark"}, base=dict(stale), supabase=SB) is True
    assert fake.methods == ["GET", "PUT"]
    body = fake.put_body()["user_metadata"]
    assert "secret_from_cache" not in body
    assert body["lang"] == "zh"
    assert body["never_seen_key"] == "keep-me"


def test_write_always_pays_a_fresh_get_even_when_base_is_passed(api):
    """A caller holding the identity-cache record still must not skip the GET."""
    ok = user_prefs.write_user_prefs(
        UID, {"theme": "dark"}, base=dict(STORED), supabase=SB)
    assert ok is True
    assert api.methods[0] == "GET"
    assert "PUT" in api.methods


def test_apply_tz_default_does_not_overwrite_a_present_tz():
    """Seat R2/R3: a tz already in the fresh read is left alone."""
    patch = {"alert_email_optin": True}
    user_prefs.apply_tz_default(patch, {"tz": "Asia/Hong_Kong", "lang": "en"})
    assert "tz" not in patch


def test_apply_tz_default_none_fresh_does_not_fire():
    """Seat R2: None means 'we do not know' — the rule does not fire."""
    patch = {"alert_email_optin": True, "lang": "zh"}
    user_prefs.apply_tz_default(patch, None)
    assert "tz" not in patch


def test_apply_tz_default_request_tz_wins_over_fresh_and_empty():
    """A tz present in the request still wins over both a stored zone and None."""
    patch = {"alert_email_optin": True, "tz": "Europe/London"}
    user_prefs.apply_tz_default(patch, {"tz": "UTC"})
    assert patch["tz"] == "Europe/London"
    patch2 = {"alert_email_optin": True, "tz": "Europe/London"}
    user_prefs.apply_tz_default(patch2, None)
    assert patch2["tz"] == "Europe/London"


def test_apply_tz_default_fires_from_fresh_lang_when_alerts_turn_on():
    patch = {"alert_email_optin": True}
    user_prefs.apply_tz_default(patch, {"lang": "zh"})
    assert patch["tz"] == "Asia/Shanghai"
    patch_en = {"alert_email_optin": True}
    user_prefs.apply_tz_default(patch_en, {"lang": "en"})
    assert patch_en["tz"] == "UTC"
