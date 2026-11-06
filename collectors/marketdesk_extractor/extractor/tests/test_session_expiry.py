"""Tests for lapsed-session detection (the 2026-08-07 → 08-11 silent outage).

MarketDesk never answers a logged-out client with 401/403 — it returns **200**
everywhere. That single fact is what let a dead session masquerade as a healthy,
quota-capped one for four days: the feeds returned ``{"success": false}`` (and
``list()`` of a dict yields its keys, so the log read ``latest=1 picks=1 saved=1``),
and ``/files/<id>/blob`` returned a 2,185-byte landing page that byte-sniffed
identically to the ~146KB over-cap app-shell.

These tests pin the discriminator that byte-sniffing cannot provide: the session
probe. NO network, NO Playwright — a fake transport serves the exact payloads
observed in production.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from marketdesk_extractor import db, discover, trickle
from marketdesk_extractor.config import Config
from marketdesk_extractor.marketdesk import (
    DownloadCapExhausted,
    MarketDeskClient,
    MarketDeskError,
    SessionExpired,
    _as_id_list,
)
from marketdesk_extractor.schemas import Status

NOW = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)

# The two HTML bodies, at their observed sizes. Both start "<!doctype html>";
# only the session probe separates them.
LANDING_PAGE = (
    b'<!doctype html><html><head><meta charset="utf-8">'
    b"<title>MarketDesk: Landing</title></head><body></body></html>"
)
LANDING_PAGE += b"<!-- " + b"x" * (2185 - len(LANDING_PAGE) - 9) + b" -->"
APP_SHELL = b"<!DOCTYPE html><html><body>" + b"y" * (145993 - 41) + b"</body></html>"

LOGGED_OUT_PAYLOAD = {"success": False}   # verbatim, from an anonymous curl


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, *, status=200, body=b"", payload=None):
        self.status = status
        self._body = body
        self._payload = payload

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def body(self) -> bytes:
        return self._body

    def json(self):
        return self._payload


class FakeRequest:
    """Playwright ``context.request`` stand-in.

    ``blob_body`` answers GETs for /blob; ``feed_payload`` answers everything
    else (both the feed endpoints and the session probe's POST).
    """

    def __init__(self, *, blob_body=b"%PDF-1.4\ndata\n", feed_payload=None):
        self.blob_body = blob_body
        self.feed_payload = [] if feed_payload is None else feed_payload
        self.probe_calls = 0
        self.consent_calls = 0

    def get(self, url, **kw):
        if url.endswith("/blob"):
            return FakeResponse(body=self.blob_body)
        return FakeResponse(payload=self.feed_payload)

    def post(self, url, **kw):
        if url.endswith("/terms/consent"):
            self.consent_calls += 1
            return FakeResponse(payload={"success": True})
        if url.endswith("latest/latest"):
            self.probe_calls += 1
        return FakeResponse(payload=self.feed_payload)


class FakeContext:
    def __init__(self, request):
        self.request = request


def _cfg(tmp_path, monkeypatch) -> Config:
    env = {
        "DATABASE_URL": str(tmp_path / "db" / "t.sqlite"),
        "OUTPUT_DIR": str(tmp_path / "data"),
        "RAW_PDF_DIR": str(tmp_path / "data" / "raw_pdfs"),
        "MARKDOWN_DIR": str(tmp_path / "data" / "markdown"),
        "METADATA_DIR": str(tmp_path / "data" / "metadata"),
        "MANIFEST_DIR": str(tmp_path / "data" / "manifests"),
        "LOG_DIR": str(tmp_path / "logs"),
        "MARKETDESK_PROFILE_DIR": str(tmp_path / "prof"),
        "R2_ENABLED": "false",
        "DROPBOX_ENABLED": "false",
        "VAULT_ENABLED": "false",
        "PARSER_BACKEND": "none",
        "DOWNLOAD_CAP_PER_ACCOUNT_24H": "70",
        "NEW_WINDOW_HOURS": "48",
        "MARKETDESK_PROFILES": "",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    cfg = Config.from_env()
    cfg.ensure_dirs()
    return cfg


def _client(cfg, **kw) -> MarketDeskClient:
    return MarketDeskClient(FakeContext(FakeRequest(**kw)), cfg)


# ---------------------------------------------------------------------------
# _as_id_list — a dict payload is a dead session, never a one-item feed
# ---------------------------------------------------------------------------
def test_as_id_list_passes_a_real_array_through():
    assert _as_id_list(["a", "b"], "latest") == ["a", "b"]


def test_as_id_list_treats_none_as_empty():
    assert _as_id_list(None, "latest") == []


def test_as_id_list_rejects_the_logged_out_object():
    with pytest.raises(SessionExpired) as e:
        _as_id_list(LOGGED_OUT_PAYLOAD, "picks")
    assert "lapsed" in str(e.value)


def test_logged_out_dict_would_have_looked_like_one_item():
    """Pin the original defect: bare list() of the payload is truthy and len 1."""
    assert list(LOGGED_OUT_PAYLOAD) == ["success"]


# ---------------------------------------------------------------------------
# session_alive — the probe the whole fix hangs on
# ---------------------------------------------------------------------------
def test_session_alive_true_on_an_array(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    assert _client(cfg, feed_payload=["id1"]).session_alive() is True


def test_session_alive_false_on_the_logged_out_object(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    assert _client(cfg, feed_payload=LOGGED_OUT_PAYLOAD).session_alive() is False


# ---------------------------------------------------------------------------
# download_blob — same HTML head, opposite verdicts, decided by the probe
# ---------------------------------------------------------------------------
def test_landing_page_with_a_dead_probe_is_session_expired(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    client = _client(cfg, blob_body=LANDING_PAGE, feed_payload=LOGGED_OUT_PAYLOAD)
    with pytest.raises(SessionExpired) as e:
        client.download_blob("7adJu9ueyoy")
    assert "NOT a download cap" in str(e.value)
    assert "2185" in str(e.value)


def test_app_shell_with_a_live_probe_is_still_a_cap_bounce(tmp_path, monkeypatch):
    """The real cap path must survive the fix — this is the regression it risks."""
    cfg = _cfg(tmp_path, monkeypatch)
    client = _client(cfg, blob_body=APP_SHELL, feed_payload=["still", "logged", "in"])
    with pytest.raises(DownloadCapExhausted):
        client.download_blob("7adJu9ueyoy")


def test_the_two_html_bodies_are_indistinguishable_by_head():
    """Why the probe is required: byte-sniffing alone cannot separate them."""
    assert LANDING_PAGE[:15].lower() == APP_SHELL[:15].lower()
    assert len(LANDING_PAGE) == 2185
    assert len(APP_SHELL) == 145993


def test_a_healthy_pdf_never_probes_the_session(tmp_path, monkeypatch):
    """The probe costs a request; it must fire only on the HTML branch."""
    cfg = _cfg(tmp_path, monkeypatch)
    client = _client(cfg)
    assert client.download_blob("ok").startswith(b"%PDF-")
    assert client.ctx.request.probe_calls == 0


# ---------------------------------------------------------------------------
# feeds + discovery — the signal must not be swallowed on the way up
# ---------------------------------------------------------------------------
def test_feeds_raise_rather_than_returning_a_one_item_list(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    client = _client(cfg, feed_payload=LOGGED_OUT_PAYLOAD)
    for feed in (client.latest, client.picks, client.saved, client.browse_current):
        with pytest.raises(SessionExpired):
            feed()


def test_feed_flags_propagates_session_expired(tmp_path, monkeypatch):
    """_feed_flags is best-effort for a FLAKY feed, not for a dead session."""
    cfg = _cfg(tmp_path, monkeypatch)
    client = _client(cfg, feed_payload=LOGGED_OUT_PAYLOAD)
    with pytest.raises(SessionExpired):
        discover._feed_flags(client)


def test_feed_flags_still_swallows_an_ordinary_feed_error(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    client = _client(cfg, feed_payload=["a"])
    monkeypatch.setattr(
        client, "picks", lambda: (_ for _ in ()).throw(RuntimeError("flaky"))
    )
    latest, picks, saved = discover._feed_flags(client)
    assert latest == {"a"} and picks == set()


# ---------------------------------------------------------------------------
# trickle — a lapsed login parks the account instead of faking a cooldown
# ---------------------------------------------------------------------------
class ExpiredSession:
    def __init__(self, cfg, headless=None):
        self.cfg = cfg
        self.context = object()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def is_authenticated(self):
        return True          # authed at OPEN; the session dies mid-flight


class ExpiringClient:
    def __init__(self, context, cfg):
        self.cfg = cfg

    def download_blob(self, blob_id: str) -> bytes:
        raise SessionExpired(f"blob {blob_id}: login has LAPSED")


def test_session_expiry_parks_the_account_and_sets_no_cooldown(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url)
    db.init_db(conn)
    conn.execute(
        "INSERT INTO papers (blob_id, article_url, blob_url, title, institution, "
        "published_at, status) VALUES (?,?,?,?,?,?,?)",
        ("wants_download", "u", "b", "T", "JPM",
         (NOW - timedelta(hours=1)).isoformat(), Status.DISCOVERED.value),
    )
    conn.commit()

    monkeypatch.setattr(trickle, "BrowserSession", ExpiredSession)
    monkeypatch.setattr(trickle, "MarketDeskClient", ExpiringClient)
    monkeypatch.setattr(trickle, "_refresh_queue", lambda *a, **k: None)

    states = [trickle.AccountState(profile=p) for p in cfg.profiles]
    trickle._open_sessions(cfg, states)
    tick = trickle.run_tick(cfg, conn, states, NOW, dry_run=False)

    assert tick.session_expired == 1
    assert tick.cap_bounces == 0, "a lapsed login must never read as a cap bounce"
    assert states[0].authed is False, "the account must be parked, loudly"
    assert states[0].cooldown_until is None, "a cooldown would silently re-arm forever"
    # the paper never got a fair try, so it goes back in the queue
    assert db.get_by_blob_id(conn, "wants_download")["status"] == Status.DISCOVERED.value
    # and the parked account announces itself on every later plan line
    assert "NOT AUTHENTICATED" in trickle.plan_account(
        cfg, conn, states[0], NOW
    ).describe()


def test_run_trickle_persists_auth_required_after_midflight_expiry(
        tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    conn = db.connect(cfg.database_url)
    db.init_db(conn)
    conn.execute(
        "INSERT INTO papers (blob_id, article_url, blob_url, title, institution, "
        "published_at, status) VALUES (?,?,?,?,?,?,?)",
        ("expires_in_loop", "u2", "b2", "T2", "JPM",
         (NOW - timedelta(hours=1)).isoformat(), Status.DISCOVERED.value),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(trickle, "BrowserSession", ExpiredSession)
    monkeypatch.setattr(trickle, "MarketDeskClient", ExpiringClient)
    monkeypatch.setattr(trickle, "_refresh_queue", lambda *a, **k: None)

    result = trickle.run_trickle(
        cfg,
        once=True,
        dry_run=False,
        now_fn=lambda: NOW,
        sleep_fn=lambda _s: None,
    )
    assert result[0].session_expired == 1

    conn = db.connect(cfg.database_url)
    health = db.producer_auth_health(conn)
    conn.close()
    assert health == {
        "state": db.AUTH_REQUIRED,
        "observed_at": NOW.isoformat(),
        "required_at": NOW.isoformat(),
        "reason": "NO_AUTHENTICATED_PROFILE",
    }


def test_run_trickle_records_authenticated_without_inventing_download_activity(
        tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    monkeypatch.setattr(trickle, "BrowserSession", ExpiredSession)
    monkeypatch.setattr(trickle, "MarketDeskClient", ExpiringClient)
    monkeypatch.setattr(trickle, "_refresh_queue", lambda *a, **k: None)

    trickle.run_trickle(
        cfg,
        once=True,
        dry_run=False,
        now_fn=lambda: NOW,
        sleep_fn=lambda _s: None,
    )

    conn = db.connect(cfg.database_url)
    health = db.producer_auth_health(conn)
    conn.close()
    assert health["state"] == db.AUTHENTICATED
    assert health["observed_at"] == NOW.isoformat()
    assert health["required_at"] == ""


# Metadata rejection must not become an empty or partially hydrated report set.
class _ProvisionResponsesRequest(FakeRequest):
    def __init__(self, responses, *, authenticated=True):
        super().__init__(feed_payload=[] if authenticated else LOGGED_OUT_PAYLOAD)
        self.responses = iter(responses)
        self.provision_calls = 0
        self._last_provision = None

    def post(self, url, **kwargs):
        if url.endswith("items/provision"):
            self.provision_calls += 1
            try:
                payload = next(self.responses)
                self._last_provision = payload
            except StopIteration:
                payload = self._last_provision
            return FakeResponse(payload=payload)
        return super().post(url, **kwargs)


@pytest.mark.parametrize("payload", [LOGGED_OUT_PAYLOAD, None, {}, "invalid", 7])
@pytest.mark.parametrize("authenticated", [True, False])
def test_provision_rejection_uses_one_fresh_auth_control(
    tmp_path, monkeypatch, payload, authenticated,
):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _ProvisionResponsesRequest([payload], authenticated=authenticated)
    client = MarketDeskClient(FakeContext(request), cfg)
    monkeypatch.setattr("marketdesk_extractor.marketdesk.jitter_sleep", lambda: None)
    expected = MarketDeskError if authenticated else SessionExpired

    with pytest.raises(expected) as error:
        client.provision(["report-1"])

    assert type(error.value) is expected
    assert "items/provision" in str(error.value)
    if authenticated:
        assert request.consent_calls == 1
        assert request.provision_calls == 2
        assert request.probe_calls == 2
    else:
        assert request.consent_calls == 0
        assert request.provision_calls == 1
        assert request.probe_calls == 1


@pytest.mark.parametrize("payload", [[], [{"pathId": "report-1", "name": "Report"}]])
def test_provision_valid_array_has_no_extra_auth_request(tmp_path, monkeypatch, payload):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _ProvisionResponsesRequest([payload])
    client = MarketDeskClient(FakeContext(request), cfg)
    monkeypatch.setattr("marketdesk_extractor.marketdesk.jitter_sleep", lambda: None)

    assert client.provision(["report-1"]) == payload
    assert request.provision_calls == 1
    assert request.probe_calls == 0


def test_provision_later_chunk_rejection_does_not_return_partial_metadata(
    tmp_path, monkeypatch,
):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _ProvisionResponsesRequest([
        [{"pathId": "report-0", "name": "Earlier chunk"}],
        LOGGED_OUT_PAYLOAD,
    ])
    client = MarketDeskClient(FakeContext(request), cfg)
    monkeypatch.setattr("marketdesk_extractor.marketdesk.jitter_sleep", lambda: None)

    with pytest.raises(MarketDeskError) as error:
        client.provision([f"report-{index}" for index in range(51)])

    assert type(error.value) is MarketDeskError
    assert request.consent_calls == 1
    assert request.provision_calls == 3
    assert request.probe_calls == 2


_ID_READERS = [
    ("latest", (), "latest/latest"),
    ("picks", (), "latest/picks"),
    ("saved", (), "latest/saved"),
    ("viewed", (), "latest/viewed"),
    ("browse_current", (), "library/browse/current"),
    ("browse", ("folder-1",), "library/browse/folder-1"),
]


class _EndpointControlRequest:
    def __init__(
        self, endpoint_payload, *, authenticated=True, endpoint_status=200,
        retry_payload=None,
    ):
        self.endpoint_payload = endpoint_payload
        self.retry_payload = (
            endpoint_payload if retry_payload is None else retry_payload
        )
        self.control_payload = [] if authenticated else LOGGED_OUT_PAYLOAD
        self.endpoint_status = endpoint_status
        self.calls = []
        self.consent_calls = 0
        self._non_consent = 0

    def _response(self, method, url, kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith("/terms/consent"):
            self.consent_calls += 1
            return FakeResponse(payload={"success": True})
        self._non_consent += 1
        n = self._non_consent
        if n == 1:
            return FakeResponse(
                payload=self.endpoint_payload, status=self.endpoint_status,
            )
        if self.endpoint_status != 200:
            raise AssertionError("HTTP error path must not continue after the first call")
        if n % 2 == 0:
            assert method == "post" and url.endswith("latest/latest")
            return FakeResponse(payload=self.control_payload)
        return FakeResponse(payload=self.retry_payload)

    def get(self, url, **kwargs):
        return self._response("get", url, kwargs)

    def post(self, url, **kwargs):
        return self._response("post", url, kwargs)


@pytest.mark.parametrize("method,args,endpoint", _ID_READERS)
@pytest.mark.parametrize("authenticated", [True, False])
def test_id_reader_rejection_classifies_one_fresh_control(
    tmp_path, monkeypatch, method, args, endpoint, authenticated,
):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _EndpointControlRequest(LOGGED_OUT_PAYLOAD, authenticated=authenticated)
    client = MarketDeskClient(FakeContext(request), cfg)
    expected = MarketDeskError if authenticated else SessionExpired

    with pytest.raises(expected) as error:
        getattr(client, method)(*args)

    assert type(error.value) is expected
    assert request.calls[0][1] == cfg.api(endpoint)
    if authenticated:
        assert request.consent_calls == 1
        assert request._non_consent == 4
        assert "endpoint failure" in str(error.value)
        assert request.calls[1][0:2] == ("post", cfg.api("latest/latest"))
        assert request.calls[2][1] == cfg.terms_consent_url()
    else:
        assert request.consent_calls == 0
        assert request._non_consent == 2
        assert request.calls[1][0:2] == ("post", cfg.api("latest/latest"))


@pytest.mark.parametrize("method,args,endpoint", _ID_READERS)
@pytest.mark.parametrize("payload", [[], ["report-1"], None])
def test_id_reader_valid_legacy_payload_has_no_extra_control(
    tmp_path, monkeypatch, method, args, endpoint, payload,
):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _EndpointControlRequest(payload)
    client = MarketDeskClient(FakeContext(request), cfg)

    assert getattr(client, method)(*args) == (payload or [])
    assert len(request.calls) == 1
    assert request.calls[0][1] == cfg.api(endpoint)


def test_id_reader_http_error_does_not_issue_auth_control(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _EndpointControlRequest(LOGGED_OUT_PAYLOAD, endpoint_status=403)
    client = MarketDeskClient(FakeContext(request), cfg)

    with pytest.raises(MarketDeskError) as error:
        client.browse_current()

    assert type(error.value) is MarketDeskError
    assert len(request.calls) == 1


@pytest.mark.parametrize("authenticated", [True, False])
def test_discovery_rejection_parks_only_after_negative_control(
    tmp_path, monkeypatch, authenticated,
):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _EndpointControlRequest(LOGGED_OUT_PAYLOAD, authenticated=authenticated)
    client = MarketDeskClient(FakeContext(request), cfg)
    state = trickle.AccountState(profile=cfg.profiles[0], authed=True, client=client)

    def rejected_discovery(cfg, conn, client, **kwargs):
        client.browse_current()
        raise AssertionError("rejected discovery must not return a success summary")

    monkeypatch.setattr(discover, "discover", rejected_discovery)
    trickle._refresh_queue(cfg, None, [state])

    assert state.authed is authenticated
    if authenticated:
        assert request.consent_calls == 1
        assert request._non_consent == 4
    else:
        assert request.consent_calls == 0
        assert request._non_consent == 2


def test_browse_terms_consent_heals_and_returns_ids(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _EndpointControlRequest(
        LOGGED_OUT_PAYLOAD, retry_payload=["year-2026"],
    )
    client = MarketDeskClient(FakeContext(request), cfg)

    assert client.browse_current() == ["year-2026"]
    assert request.consent_calls == 1
    assert request._non_consent == 3
    assert request.calls[2][1] == cfg.terms_consent_url()


def test_terms_consent_not_attempted_when_session_dead(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _EndpointControlRequest(LOGGED_OUT_PAYLOAD, authenticated=False)
    client = MarketDeskClient(FakeContext(request), cfg)

    with pytest.raises(SessionExpired):
        client.browse_current()

    assert request.consent_calls == 0
    assert request._non_consent == 2


def test_terms_consent_attempted_only_once(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    request = _EndpointControlRequest(LOGGED_OUT_PAYLOAD)
    client = MarketDeskClient(FakeContext(request), cfg)

    with pytest.raises(MarketDeskError):
        client.browse_current()
    assert request.consent_calls == 1
    with pytest.raises(MarketDeskError):
        client.browse_current()
    assert request.consent_calls == 1


def test_provision_terms_consent_heals_metadata(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    healed = [{"pathId": "report-1", "name": "Healed", "type": "application/pdf"}]
    request = _ProvisionResponsesRequest([LOGGED_OUT_PAYLOAD, healed])
    client = MarketDeskClient(FakeContext(request), cfg)
    monkeypatch.setattr("marketdesk_extractor.marketdesk.jitter_sleep", lambda: None)

    assert client.provision(["report-1"]) == healed
    assert request.consent_calls == 1
    assert request.provision_calls == 2
    assert request.probe_calls == 1


def test_silent_relogin_is_noop_without_a_page(tmp_path, monkeypatch):
    from marketdesk_extractor.auth import try_silent_relogin

    cfg = _cfg(tmp_path, monkeypatch)
    assert try_silent_relogin(FakeContext(FakeRequest()), cfg) is False


class _LibraryHealRequest:
    """Browse starts rejected; latest/latest stays an ID array; consent unblocks browse."""

    def __init__(self):
        self.browse_calls = 0
        self.consent_calls = 0

    def get(self, url, **kwargs):
        if url.endswith("library/browse/current"):
            self.browse_calls += 1
            if self.browse_calls == 1:
                return FakeResponse(payload=LOGGED_OUT_PAYLOAD)
            return FakeResponse(payload=["year-2026"])
        return FakeResponse(payload=[])

    def post(self, url, **kwargs):
        if url.endswith("/terms/consent"):
            self.consent_calls += 1
            return FakeResponse(payload={"success": True})
        return FakeResponse(payload=["latest-id"])


def test_library_ready_true_after_terms_heal(tmp_path, monkeypatch):
    from marketdesk_extractor.auth import library_ready

    cfg = _cfg(tmp_path, monkeypatch)
    request = _LibraryHealRequest()
    assert library_ready(FakeContext(request), cfg) is True
    assert request.consent_calls == 1
    assert request.browse_calls == 2


def test_auth_parser_exposes_force_flag():
    from marketdesk_extractor.cli import build_parser

    args = build_parser().parse_args(["auth", "--force", "--timeout", "12"])
    assert args.force is True
    assert args.timeout == 12
