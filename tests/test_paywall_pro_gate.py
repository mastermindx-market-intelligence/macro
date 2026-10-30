"""Contract tests for the Pro-only host gate in front of bot.mastermind-x.com.

Two halves, and the second is the one that carries the feature:

* /api/paywall/check_pro (app/paywall.py) -- WHO the caller is, on every path, with
  no classification against config/site_access.yml (that file describes the MACRO
  site's URL space; the bot desk is a different application);
* the Caddy wiring (app/deploy/Caddyfile) that calls it, and the /health hole that
  keeps admin/uptime_board.py able to see an outage rather than a locked door.

"Anonymous is blocked" is the cheap half. The assertions that matter are ESSENTIAL
being blocked -- the tier below the floor, held by real paying customers -- and the
unknown-tier and broken-catalog paths denying rather than guessing.
"""
from __future__ import annotations

import base64
import http.client
import json
import re
import shutil
import ssl
import subprocess
import time
import urllib.error
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import paywall
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
CADDY = (ROOT / "app" / "deploy" / "Caddyfile").read_text(encoding="utf-8")

client = TestClient(app, follow_redirects=False)
UID = "22222222-2222-2222-2222-222222222222"
EMAIL = "member@example.com"
OPERATOR = "ops@mastermind-x.com"


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.delenv("PAYWALL_ENABLED", raising=False)
    monkeypatch.delenv("PAYWALL_GRACE_SECONDS", raising=False)
    monkeypatch.delenv("PAYWALL_ENTITLEMENT_CACHE_SECONDS", raising=False)
    # Never inherit a real operator grant from the developer's shell: with this set,
    # every "free is locked" assertion below could pass for the wrong reason.
    monkeypatch.delenv("BRAIN_UNLIMITED_ALLOWLIST", raising=False)
    paywall._AUTH_CACHE.clear()
    paywall._ENT_CACHE.clear()
    paywall._CONFIG_CACHE = None
    paywall._PLANS_CACHE = None


def _check(path="/api/positions", headers=None, cookies=None):
    """A bot-host subrequest. Default path is an API lane -> the JSON deny branch."""
    hdrs = {"X-Original-Uri": path}
    hdrs.update(headers or {})
    return client.get("/api/paywall/check_pro", headers=hdrs, cookies=cookies or {})


def _signed_in(monkeypatch, email=EMAIL):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "tok")
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(UID, email, {"id": UID}, "ok"),
    )


def _row(monkeypatch, tier, status="active", features=("site_full",), email=EMAIL):
    _signed_in(monkeypatch, email)
    monkeypatch.setattr(
        paywall,
        "_store_entitlement",
        lambda uid: ({"tier": tier, "status": status, "features": list(features)}, True),
    )


def _jwt(exp: float) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": exp, "sub": UID}).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"header.{payload}.signature"


# ---------------------------------------------------------------------------
# Who gets in
# ---------------------------------------------------------------------------
def test_anonymous_is_locked(monkeypatch):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: None)
    r = _check()
    assert r.status_code == 403
    assert r.json() == {
        "locked": True,
        "tier": "anon",
        "required_tier": "pro",
        "upgrade_url": "/plans.html?upgrade=1&plan=pro",
    }


def test_signed_in_but_verifiably_invalid_token_requires_reauthentication(monkeypatch):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "tok")
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(None, "", None, "invalid"),
    )
    r = _check()
    assert r.status_code == 401
    assert r.headers["x-paywall"] == "session-refresh"
    assert r.json()["error"] == "session_reverification_required"
    assert "upgrade_url" not in r.json()


def test_expired_shared_cookie_recovers_with_canonical_auth_client(monkeypatch):
    # An expired access JWT from a durable parent-domain cookie is renewal-needed,
    # not proof that the paid entitlement was revoked.
    monkeypatch.setattr(
        "app.main._mm_supabase_access_token",
        lambda request: _jwt(time.time() - 180),
    )
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: (_ for _ in ()).throw(AssertionError("expired JWT reached upstream")),
    )
    r = _check("/desk?symbol=AAPL", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 401
    assert r.headers["x-paywall"] == "session-refresh"
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["vary"] == "Cookie"
    assert 'name="mm-bot-renew" content="yes"' in r.text
    assert '<base href="https://www.mastermind-x.com/">' in r.text
    assert 'src="https://www.mastermind-x.com/theme.js?bot-recovery=1"' in r.text
    assert "var broker = window.getSupabaseClient;" in r.text
    assert "sb.auth.getSession()" in r.text
    assert "location.reload()" in r.text
    assert "sessionStorage" in r.text
    assert "upgrade=1" not in r.text
    assert "Your membership hasn't been classified as unpaid" in r.text


@pytest.mark.parametrize("cookie_form", ["single", "chunked"])
def test_real_shared_cookie_decoder_reaches_expired_session_recovery(monkeypatch, cookie_form):
    """Use the actual app.main cookie reader, not a patched token accessor.

    Parent-domain cookie values are the same base64url JSON shape written by
    theme.js. Unverified exp only selects denied recovery; it never admits Pro.
    """
    from app import main as app_main

    token = _jwt(time.time() - 180)
    session = {"access_token": token, "refresh_token": "synthetic-not-functional"}
    if cookie_form == "chunked":
        session["non_auth_padding"] = "x" * 4100
    raw = "base64-" + base64.urlsafe_b64encode(
        json.dumps(session, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    name = app_main._SB_STORAGE_KEY
    cookies = ({name: raw} if cookie_form == "single" else {
        f"{name}.{i // 3180}": raw[i:i + 3180]
        for i in range(0, len(raw), 3180)
    })
    # A false-positive bypass of _mm_supabase_access_token would call upstream.
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda value: (_ for _ in ()).throw(AssertionError("expired JWT reached upstream")),
    )
    response = _check("/desk?symbol=AAPL", headers={"Sec-Fetch-Dest": "document"}, cookies=cookies)
    assert response.status_code == 401
    assert response.headers["x-paywall"] == "session-refresh"
    assert response.headers["cache-control"] == "private, no-store"
    assert 'name="mm-bot-renew" content="yes"' in response.text
    assert "Mastermind Bot comes with Pro" not in response.text


def test_legacy_null_stripe_feature_does_not_erase_verified_paid_entitlement(monkeypatch):
    """text[] permits NULL elements even though the column is NOT NULL."""
    from app import billing

    _signed_in(monkeypatch)
    monkeypatch.setattr(billing, "_pg", _pg_result([{
        "tier": "pro", "status": "active",
        "features": [None, paywall._PRO_FEATURE],
    }]))
    assert _check().status_code == 204
    paywall._ENT_CACHE.clear()
    monkeypatch.setattr(billing, "_pg", _pg_result([{
        "tier": "pro", "status": "active", "features": [None],
    }]))
    assert _check().status_code == 403  # A null never grants a feature.


def test_stripe_null_lookup_keys_are_filtered_before_storing_entitlement(monkeypatch):
    """Exercise _compute_entitlement's actual Stripe-like object path."""
    from types import SimpleNamespace as NS
    from app import billing

    provider = NS(
        Subscription=NS(list=lambda **kw: NS(data=[NS(status="active")])),
        entitlements=NS(ActiveEntitlement=NS(list=lambda **kw: NS(data=[
            NS(lookup_key=None), NS(lookup_key=paywall._PRO_FEATURE),
        ]))),
    )
    monkeypatch.setattr(billing, "_stripe", lambda: provider)
    monkeypatch.setattr(billing, "_sub_tier", lambda sub: "pro")
    monkeypatch.setattr(billing, "_sub_period_end", lambda sub: None)
    monkeypatch.setattr(billing, "_sub_interval", lambda sub: "monthly")
    row = billing._compute_entitlement("cus-synthetic")
    assert row["features"] == [paywall._PRO_FEATURE]
    _signed_in(monkeypatch)
    monkeypatch.setattr(billing, "_pg", _pg_result([row]))
    assert _check().status_code == 204


def test_bot_renewal_csp_restricts_transitive_third_party_scripts(monkeypatch):
    """The shared Macro theme injects Umami; Bot's cookie-bearing 401 must block it."""
    monkeypatch.setattr(
        "app.main._mm_supabase_access_token",
        lambda request: _jwt(time.time() - 180),
    )
    a = _check("/desk?symbol=AAPL", headers={"Sec-Fetch-Dest": "document"})
    b = _check("/desk?symbol=AAPL", headers={"Sec-Fetch-Dest": "document"})
    assert a.status_code == b.status_code == 401
    csp = a.headers["content-security-policy"]
    match = re.search(r"nonce=\"([a-f0-9]{32})\"", a.text)
    assert match, "the recovery script must carry its server-generated CSP nonce"
    assert f"script-src 'nonce-{match.group(1)}' https://www.mastermind-x.com;" in csp
    assert "default-src 'none'" in csp
    assert "connect-src https://fsldfzlxyavsuwqbceod.supabase.co" in csp
    assert "base-uri https://www.mastermind-x.com" in csp
    assert "frame-ancestors 'none'" in csp
    script_src = csp.split("script-src ", 1)[1].split(";", 1)[0]
    assert "'unsafe-inline'" not in script_src
    assert "cloud.umami.is" not in csp
    assert "www.googletagmanager.com" not in csp
    assert "__MM_BOT_CSP_NONCE__" not in a.text
    assert f"nonce=\"{match.group(1)}\"" not in b.text, "per-response nonces must rotate"
    assert a.headers["referrer-policy"] == "no-referrer"
    assert a.headers["cache-control"] == "private, no-store"


def test_broken_csp_or_missing_template_fails_closed_without_scripts(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.main._mm_supabase_access_token",
        lambda request: _jwt(time.time() - 180),
    )
    broken = tmp_path / "bad-renewal.html"
    broken.write_text("<!doctype html><script>danger()</script>", encoding="utf-8")
    monkeypatch.setattr(paywall, "PRO_SESSION_RENEW", broken)
    r = _check("/", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 401
    assert "danger()" not in r.text
    assert "Sign in again" in r.text
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert "script-src" not in r.headers["content-security-policy"]


def test_legacy_browser_deep_link_still_gets_renewal_html(monkeypatch):
    """Some browsers omit Sec-Fetch-Dest; Accept: text/html is a safe fallback."""
    monkeypatch.setattr(
        "app.main._mm_supabase_access_token",
        lambda request: _jwt(time.time() - 180),
    )
    r = _check("/desk?symbol=AAPL", headers={"Accept": "text/html"})
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("text/html")
    assert "content-security-policy" in r.headers
    assert "mm-bot-renew" in r.text


@pytest.mark.parametrize(
    "path,headers",
    [
        ("/api/positions", {"Accept": "text/html"}),
        ("/desk", {"Accept": "text/html", "Sec-Fetch-Dest": "script"}),
        ("/desk", {"Accept": "text/html", "X-Original-Kind": "asset"}),
        ("/assets/bot.js", {"Accept": "text/html"}),
    ],
)
def test_bot_api_asset_or_explicit_fetch_never_confused_with_document(
    monkeypatch, path, headers,
):
    monkeypatch.setattr(
        "app.main._mm_supabase_access_token",
        lambda request: _jwt(time.time() - 180),
    )
    r = _check(path, headers=headers)
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["error"] == "session_reverification_required"


def test_expired_api_session_refuses_without_upgrade_offer(monkeypatch):
    monkeypatch.setattr(
        "app.main._mm_supabase_access_token",
        lambda request: _jwt(time.time() - 180),
    )
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: (_ for _ in ()).throw(AssertionError("expired JWT reached upstream")),
    )
    r = _check("/api/positions")
    assert r.status_code == 401
    assert r.json() == {
        "error": "session_reverification_required",
        "sign_in_url": "https://www.mastermind-x.com/?signin=1",
    }
    assert r.headers["x-paywall"] == "session-refresh"


def test_session_near_expiry_also_renews_without_granting_pro(monkeypatch):
    monkeypatch.setattr(
        "app.main._mm_supabase_access_token",
        lambda request: _jwt(time.time() + 2),
    )
    r = _check()
    assert r.status_code == 401
    assert r.json()["error"] == "session_reverification_required"


def test_syntactically_valid_future_jwt_is_not_treated_as_authorization(monkeypatch):
    monkeypatch.setattr(
        "app.main._mm_supabase_access_token",
        lambda request: _jwt(time.time() + 3600),
    )
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(None, "", None, "invalid"),
    )
    r = _check()
    assert r.status_code == 401
    assert r.json()["error"] == "session_reverification_required"
    assert "upgrade_url" not in r.json()


def test_invalid_token_document_has_no_automatic_sdk_retry(monkeypatch):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "bogus")
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(None, "", None, "invalid"),
    )
    r = _check("/", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 401
    assert 'name="mm-bot-renew" content="no"' in r.text
    assert "Sign in" in r.text
    assert "Mastermind Bot comes with Pro" not in r.text


def test_busy_vendor_never_autoretries_the_shared_auth_semaphore(monkeypatch):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "tok")
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(None, "", None, "busy"),
    )
    r = _check("/", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 503
    assert 'name="mm-bot-service-retry" content="disabled"' in r.text
    assert r.headers["retry-after"] == "5"


def test_reachable_store_without_entitlement_row_is_unpaid_not_unavailable(monkeypatch):
    _signed_in(monkeypatch)
    monkeypatch.setattr(paywall, "_store_entitlement", lambda uid: (None, True))
    r = _check()
    assert r.status_code == 403
    assert r.json()["tier"] == "free"


@pytest.mark.parametrize("status", ["outage", "busy"])
def test_temporary_auth_failure_is_not_an_unpaid_verdict(monkeypatch, status):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "tok")
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(None, "", None, status),
    )
    r = _check()
    assert r.status_code == 503
    assert r.json()["error"] == "membership_check_unavailable"
    assert r.headers["retry-after"] == "5"
    assert r.json()["retryable"] is (status != "busy")
    assert r.headers["x-paywall"] == "unavailable"
    assert r.headers["cache-control"] == "private, no-store"


def test_entitlement_backend_outage_is_not_reported_as_free(monkeypatch):
    _signed_in(monkeypatch)
    monkeypatch.setattr(paywall, "_store_entitlement", lambda uid: (None, False))
    r = _check()
    assert r.status_code == 503
    assert r.json()["error"] == "membership_check_unavailable"


def test_entitlement_backend_outage_preserves_confirmed_pro_grace(monkeypatch):
    _row(monkeypatch, "pro")
    assert _check().status_code == 204
    monkeypatch.setattr(paywall, "_store_entitlement", lambda uid: (None, False))
    # Expire the fresh read but retain the accepted grace window.
    v = paywall._ENT_CACHE[UID]
    from dataclasses import replace
    paywall._ENT_CACHE[UID] = replace(v, fetched_at=v.fetched_at - 200)
    assert _check().status_code == 204


def test_temporary_auth_failure_document_retries_without_paywall_message(monkeypatch):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "tok")
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(None, "", None, "outage"),
    )
    r = _check("/", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 503
    assert "text/html" in r.headers["content-type"]
    assert r.headers["cache-control"] == "private, no-store"
    assert "retry" in r.text.lower()
    assert "Mastermind Bot comes with Pro" not in r.text
    assert "sessionStorage" in r.text
    assert 'name="mm-bot-service-retry" content="enabled"' in r.text
    assert "attempts >= 2" in r.text
    assert "5000 * Math.pow(2" in r.text


# ---------------------------------------------------------------------------
# What the store actually answered: app.billing._pg and below
#
# These drive the seam BELOW _store_entitlement, so the real classification is
# under test rather than a stubbed verdict. The line being defended: real I/O
# trouble stays a retryable 503, while a configuration or protocol fault is
# never retried and is NEVER recorded as "free" -- not even for a caller who
# was a paying customer a minute ago.
# ---------------------------------------------------------------------------


def _pg_result(result):
    """A stand-in for app.billing._pg that answers with `result`."""

    def _call(*args, **kwargs):
        return result

    return _call


def _pg_raises(exc):
    def _call(*args, **kwargs):
        raise exc

    return _call


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://postgrest.invalid/rest/v1/user_entitlements", code, "boom", {}, None,
    )


def _blank_service_role(monkeypatch) -> None:
    """Exactly the state a missing SUPABASE_SERVICE_ROLE_KEY leaves behind."""
    from app import billing  # noqa: PLC0415

    monkeypatch.setattr(billing, "SUPABASE_SERVICE_ROLE_KEY", "")


def _pro_row():
    return [{"tier": "pro", "status": "active", "features": [paywall._PRO_FEATURE]}]


def _stale_fresh_read() -> None:
    """Expire the freshness window while keeping the accepted grace window."""
    from dataclasses import replace  # noqa: PLC0415

    v = paywall._ENT_CACHE[UID]
    paywall._ENT_CACHE[UID] = replace(v, fetched_at=v.fetched_at - 200)


def test_the_read_still_asks_only_for_the_three_entitlement_columns(monkeypatch):
    seen = {}

    def _call(method, path, **kwargs):
        seen["method"] = method
        seen["path"] = path
        return []

    monkeypatch.setattr("app.billing._pg", _call)
    assert paywall._store_entitlement(UID) == (None, True)
    assert seen["method"] == "GET"
    assert seen["path"] == f"user_entitlements?user_id=eq.{UID}&select=tier,features,status"


_TRANSPORT_FAULTS = [
    urllib.error.URLError("connection refused"),
    urllib.error.URLError("name or service not known"),
    TimeoutError("read timed out"),
    ConnectionResetError("reset by peer"),
    ConnectionRefusedError("connection refused"),
    http.client.RemoteDisconnected("closed without response"),
    http.client.IncompleteRead(b"partial"),
    http.client.BadStatusLine("not an http response"),
]


@pytest.mark.parametrize(
    "fault",
    [
        FileNotFoundError("missing trusted CA bundle"),
        PermissionError("service configuration unreadable"),
        ssl.SSLCertVerificationError("certificate verification failed"),
        urllib.error.URLError(ssl.SSLCertVerificationError("untrusted CA")),
        urllib.error.URLError(FileNotFoundError("missing CA bundle")),
        urllib.error.URLError(ValueError("invalid local URL configuration")),
    ],
    ids=[
        "missing-local-file", "denied-local-config", "direct-tls-verification",
        "wrapped-tls-verification", "wrapped-missing-file", "wrapped-invalid-url",
    ],
)
def test_local_configuration_errors_never_become_retryable_vendor_outages(monkeypatch, fault):
    monkeypatch.setattr("app.billing._pg", _pg_raises(fault))
    with pytest.raises(paywall._EntitlementStoreInvalid):
        paywall._store_entitlement(UID)
    _signed_in(monkeypatch)
    response = _check()
    assert response.status_code == 500
    assert response.json()["error"] == "membership_verification_error"
    assert response.headers["x-paywall"] == "error"
    assert "retry-after" not in response.headers
    assert UID not in paywall._ENT_CACHE


@pytest.mark.parametrize(
    "fault",
    _TRANSPORT_FAULTS,
    ids=[
        "urlerror-refused", "urlerror-dns", "timeout", "reset", "refused",
        "remote-disconnected", "incomplete-read", "bad-status-line",
    ],
)
def test_real_io_trouble_is_the_only_thing_that_counts_as_an_outage(monkeypatch, fault):
    monkeypatch.setattr("app.billing._pg", _pg_raises(fault))
    assert paywall._store_entitlement(UID) == (None, False)
    _signed_in(monkeypatch)
    r = _check()
    assert r.status_code == 503
    assert r.json()["error"] == "membership_check_unavailable"
    assert r.headers["retry-after"] == "5"
    assert r.headers["x-paywall"] == "unavailable"
    assert UID not in paywall._ENT_CACHE


@pytest.mark.parametrize("code", [408, 429, 500, 502, 503, 504])
def test_transient_http_status_keeps_the_existing_outage_contract(monkeypatch, code):
    monkeypatch.setattr("app.billing._pg", _pg_raises(_http_error(code)))
    assert paywall._store_entitlement(UID) == (None, False)
    _signed_in(monkeypatch)
    r = _check()
    assert r.status_code == 503
    assert r.json()["retryable"] is True
    assert UID not in paywall._ENT_CACHE


@pytest.mark.parametrize("code", [400, 401, 402, 403, 404, 405, 409, 415, 422, 451])
def test_non_transient_http_status_is_a_configuration_fault(monkeypatch, code):
    monkeypatch.setattr("app.billing._pg", _pg_raises(_http_error(code)))
    with pytest.raises(paywall._EntitlementStoreInvalid):
        paywall._store_entitlement(UID)
    assert UID not in paywall._ENT_CACHE
    _signed_in(monkeypatch)
    r = _check()
    assert r.status_code == 500
    assert r.json()["error"] == "membership_verification_error"
    assert r.headers["x-paywall"] == "error"
    assert r.headers["cache-control"] == "private, no-store"
    assert UID not in paywall._ENT_CACHE


_MALFORMED_BODIES = [
    None,                                             # empty body, or a JSON null
    {},                                               # an object, not an array
    {"message": 'relation "user_entitlements" does not exist'},
    {"code": "PGRST200", "details": "no such table"},  # an error envelope, 200
    {"tier": "pro", "status": "active", "features": ["site_full"]},
    "[]",                                             # a JSON string, not an array
    0,
    True,
    [None],
    ["a row"],
    [[{"tier": "pro"}]],
    [{}],                                             # missing selected columns
    [{"tier": "pro"}],
    [{"tier": "pro", "status": "active", "features": "site_full"}],
    [{"tier": "pro", "status": "active", "features": [7]}],
    [{"tier": 7, "status": "active", "features": []}],
    [{"tier": "pro", "status": {}, "features": []}],
    _pro_row() * 2,                                    # user_id is a primary key
]


@pytest.mark.parametrize("body", _MALFORMED_BODIES, ids=lambda b: type(b).__name__)
def test_a_body_the_select_could_not_have_produced_is_never_an_answer(monkeypatch, body):
    monkeypatch.setattr("app.billing._pg", _pg_result(body))
    with pytest.raises(paywall._EntitlementStoreInvalid):
        paywall._store_entitlement(UID)
    assert UID not in paywall._ENT_CACHE
    _signed_in(monkeypatch)
    r = _check()
    assert r.status_code == 500
    assert r.json()["error"] == "membership_verification_error"
    # No malformed caching: nothing about this user was learned, so the next
    # caller is not told "free" either -- and a site caller still just denies.
    assert UID not in paywall._ENT_CACHE
    assert paywall._entitled(UID, paywall._PRO_FEATURE) == (False, "free")
    assert UID not in paywall._ENT_CACHE


def test_a_well_formed_empty_array_is_a_verified_absence(monkeypatch):
    monkeypatch.setattr("app.billing._pg", _pg_result([]))
    assert paywall._store_entitlement(UID) == (None, True)
    _signed_in(monkeypatch)
    r = _check()
    assert r.status_code == 403
    assert r.json()["locked"] is True
    assert r.json()["tier"] == "free"
    assert r.headers["x-paywall"] == "deny"
    # A REACHABLE verdict is still cached. Unchanged, intended behavior.
    assert paywall._ENT_CACHE[UID].allowed is False


@pytest.mark.parametrize("status", ["active", "trialing"])
def test_verified_active_or_trialing_pro_is_still_admitted(monkeypatch, status):
    monkeypatch.setattr(
        "app.billing._pg",
        _pg_result([{"tier": "pro", "status": status, "features": [paywall._PRO_FEATURE]}]),
    )
    _signed_in(monkeypatch)
    assert paywall._entitled(UID, paywall._PRO_FEATURE) == (True, "pro")
    r = _check()
    assert r.status_code == 204
    assert r.headers["x-paywall"].startswith("allow-")


@pytest.mark.parametrize(
    "row,why",
    [
        ({"tier": "free", "status": "active", "features": ["site_full"]}, "free-tier"),
        ({"tier": "pro", "status": "canceled", "features": ["site_full"]}, "canceled"),
        ({"tier": "pro", "status": "past_due", "features": ["site_full"]}, "past-due"),
        ({"tier": "pro", "status": "active", "features": ["seats"]}, "feature-absent"),
        ({"tier": "mystery", "status": "active", "features": ["site_full"]}, "unknown-tier"),
    ],
    ids=["free-tier", "canceled", "past-due", "feature-absent", "unknown-tier"],
)
def test_well_formed_rows_still_deny_exactly_when_they_did_before(monkeypatch, row, why):
    monkeypatch.setattr("app.billing._pg", _pg_result([row]))
    _signed_in(monkeypatch)
    assert _check().status_code == 403, why


def test_null_required_columns_are_a_protocol_fault_not_an_unpaid_verdict(monkeypatch):
    """The entitlement schema declares all three selected columns NOT NULL."""
    monkeypatch.setattr("app.billing._pg", _pg_result([
        {"tier": None, "features": None, "status": None},
    ]))
    _signed_in(monkeypatch)
    assert _check().status_code == 500
    assert UID not in paywall._ENT_CACHE


def test_a_missing_service_role_is_permanent_not_a_retryable_blip(monkeypatch):
    from app import billing  # noqa: PLC0415

    _blank_service_role(monkeypatch)
    # The real guard fires before any socket, so no stand-in for _pg stands in.
    with pytest.raises(RuntimeError):
        billing._pg("GET", "user_entitlements?select=tier", timeout=4)
    with pytest.raises(paywall._EntitlementStoreInvalid):
        paywall._store_entitlement(UID)
    assert UID not in paywall._ENT_CACHE
    _signed_in(monkeypatch)
    r = _check()
    assert r.status_code == 500
    assert r.json()["error"] == "membership_verification_error"
    assert r.headers["x-paywall"] == "error"
    assert UID not in paywall._ENT_CACHE


def test_a_missing_service_role_never_reaches_the_network(monkeypatch):
    def _no_socket(*args, **kwargs):
        raise AssertionError("the missing-role guard must fire before urlopen")

    _blank_service_role(monkeypatch)
    monkeypatch.setattr("urllib.request.urlopen", _no_socket)
    with pytest.raises(paywall._EntitlementStoreInvalid):
        paywall._store_entitlement(UID)


def test_a_confirmed_pro_survives_a_real_transport_blip(monkeypatch):
    monkeypatch.setattr("app.billing._pg", _pg_result(_pro_row()))
    _signed_in(monkeypatch)
    assert _check().status_code == 204
    monkeypatch.setattr("app.billing._pg", _pg_raises(urllib.error.URLError("reset")))
    _stale_fresh_read()
    assert _check().status_code == 204


@pytest.mark.parametrize("fault", ["malformed-body", "missing-role"], ids=str)
def test_outage_grace_never_covers_a_fault_the_store_can_never_fix(monkeypatch, fault):
    from app import billing
    real_pg = billing._pg
    monkeypatch.setattr("app.billing._pg", _pg_result(_pro_row()))
    _signed_in(monkeypatch)
    assert _check().status_code == 204
    _stale_fresh_read()
    if fault == "malformed-body":
        monkeypatch.setattr("app.billing._pg", _pg_result({"code": "PGRST116"}))
    else:
        monkeypatch.setattr(billing, "_pg", real_pg)
        _blank_service_role(monkeypatch)
    r = _check()
    assert r.status_code == 500
    assert r.json()["error"] == "membership_verification_error"
    # The stale positive is neither honoured nor rewritten into a "free" verdict.
    assert paywall._ENT_CACHE[UID].allowed is True
    assert paywall._ENT_CACHE[UID].tier == "pro"


def test_a_fresh_positive_is_served_without_reading_the_store(monkeypatch):
    monkeypatch.setattr("app.billing._pg", _pg_result(_pro_row()))
    _signed_in(monkeypatch)
    assert _check().status_code == 204
    monkeypatch.setattr(
        "app.billing._pg", _pg_raises(AssertionError("a fresh verdict must not re-read")),
    )
    assert _check().status_code == 204


@pytest.mark.parametrize(
    "fault", ["outage", "missing-role", "malformed-body"], ids=str,
)
def test_ordinary_site_callers_stay_fail_closed_and_uncached(monkeypatch, fault):
    if fault == "outage":
        monkeypatch.setattr("app.billing._pg", _pg_raises(urllib.error.URLError("down")))
    elif fault == "malformed-body":
        monkeypatch.setattr("app.billing._pg", _pg_result(None))
    else:
        _blank_service_role(monkeypatch)
    assert paywall._entitled(UID, paywall._PRO_FEATURE) == (False, "free")
    assert UID not in paywall._ENT_CACHE


def test_an_ordinary_site_caller_still_sees_a_real_paid_row(monkeypatch):
    monkeypatch.setattr("app.billing._pg", _pg_result(_pro_row()))
    assert paywall._entitled(UID, paywall._PRO_FEATURE) == (True, "pro")


def test_a_configuration_fault_can_never_be_caught_as_a_vendor_blip():
    assert issubclass(paywall._EntitlementStoreUnavailable, RuntimeError)
    assert issubclass(paywall._EntitlementStoreInvalid, RuntimeError)
    assert not issubclass(paywall._EntitlementStoreInvalid, paywall._EntitlementStoreUnavailable)


def test_a_browser_document_config_fault_is_not_a_retry_page(monkeypatch):
    _blank_service_role(monkeypatch)
    _signed_in(monkeypatch)
    r = _check("/", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 500
    assert "text/html" in r.headers["content-type"]
    assert r.headers["cache-control"] == "private, no-store"
    assert "sessionStorage" not in r.text
    assert "retry" not in r.text.lower()
    assert "Mastermind Bot comes with Pro" not in r.text


def test_invalid_token_does_not_receive_cached_positive_grace(monkeypatch):
    paywall._ENT_CACHE[UID] = paywall._EntitlementVerdict(
        True, "pro", "active", 1.0, 10**12,
    )
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "tok-invalid")
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(None, "", None, "invalid"),
    )
    assert _check().status_code == 401


def test_missing_temporary_outage_document_fails_closed_with_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "tok")
    monkeypatch.setattr(
        paywall, "_resolve_identity",
        lambda token: paywall._Identity(None, "", None, "busy"),
    )
    monkeypatch.setattr(paywall, "PRO_UNAVAILABLE", tmp_path / "missing.html")
    r = _check("/", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 503
    assert "Membership check temporarily unavailable" in r.text
    assert "Upgrade" not in r.text


def test_free_is_locked(monkeypatch):
    _row(monkeypatch, "free", features=())
    r = _check()
    assert r.status_code == 403
    assert r.json()["tier"] == "free"


def test_essential_is_locked(monkeypatch):
    """THE feature. A paying Essential member holds site_full and is still not Pro.

    Without the tier comparison this row is `allowed=True` from _entitled() and the
    desk opens to the whole paid base -- a gate that only stops anonymous visitors.
    """
    _row(monkeypatch, "essential")
    r = _check()
    assert r.status_code == 403
    assert r.json()["tier"] == "essential"
    assert r.json()["required_tier"] == "pro"


def test_pre_rename_essential_row_is_locked_and_reported_as_essential(monkeypatch):
    """`insider` is the permanent legacy spelling of `essential` (lib/tiers.py).

    Both halves are load-bearing: it must not pass, and it must be REPORTED as the
    tier the customer actually holds. Un-normalized it would rank nowhere -- same
    403, but the body would name a tier the catalog no longer sells.
    """
    _row(monkeypatch, "insider")
    r = _check()
    assert r.status_code == 403
    assert r.json()["tier"] == "essential"


def test_pro_is_allowed(monkeypatch):
    _row(monkeypatch, "pro")
    r = _check()
    assert r.status_code == 204
    assert r.headers["x-paywall"] == "allow-pro"
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["vary"] == "Cookie"
    assert not r.content


def test_trialing_pro_is_allowed(monkeypatch):
    _row(monkeypatch, "pro", status="trialing")
    assert _check().status_code == 204


def test_unlimited_operator_tier_is_allowed(monkeypatch):
    """`unlimited` is surfaced by /api/me off the brain-gateway allowlist and is NOT in
    tier_rank. Unknown-denies would lock the operator out of his own desk."""
    _row(monkeypatch, "unlimited")
    r = _check()
    assert r.status_code == 204
    assert r.headers["x-paywall"] == "allow-unlimited"


@pytest.mark.parametrize("tier", ["platinum", "founding", "pro_plus", "PRO-MAX", ""])
def test_tier_outside_the_catalog_is_locked(monkeypatch, tier):
    """Unknown => deny. These rows carry site_full and an active status, so _entitled()
    says yes; the only thing refusing them is the rank lookup."""
    _row(monkeypatch, tier)
    assert _check().status_code == 403


@pytest.mark.parametrize("status", ["past_due", "canceled", "incomplete", "none", "paused"])
def test_pro_tier_without_an_active_subscription_is_locked(monkeypatch, status):
    _row(monkeypatch, "pro", status=status)
    r = _check()
    assert r.status_code == 403
    assert r.json()["tier"] == "pro"


def test_pro_row_missing_the_feature_is_locked(monkeypatch):
    _row(monkeypatch, "pro", features=())
    assert _check().status_code == 403


# ---------------------------------------------------------------------------
# The operator bypass -- BRAIN_UNLIMITED_ALLOWLIST, the same grant /api/me reads
#
# /api/me computes the real tier and then OVERWRITES it to `unlimited` off this
# allowlist, without ever touching user_entitlements. So the row of an operator whose
# account card says "Unlimited" may well say `free`, and a gate that reads only the row
# would lock him out of his own desk while the pill claims otherwise. These tests pin
# the two surfaces to one answer.
# ---------------------------------------------------------------------------
def test_allowlisted_operator_with_a_free_row_is_allowed(monkeypatch):
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", OPERATOR)
    _row(monkeypatch, "free", status="none", features=(), email=OPERATOR)
    r = _check()
    assert r.status_code == 204
    assert r.headers["x-paywall"] == "allow-unlimited"


def test_allowlisted_operator_with_no_entitlement_row_at_all_is_allowed(monkeypatch):
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", OPERATOR)
    _signed_in(monkeypatch, OPERATOR)
    monkeypatch.setattr(paywall, "_store_entitlement", lambda uid: (None, True))
    assert _check().status_code == 204


def test_allowlisted_operator_never_reads_the_entitlement_store(monkeypatch):
    """The bypass runs BEFORE the entitlement read, so a store outage cannot lock the
    operator out either. Proven by making any read explode."""
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", OPERATOR)
    _signed_in(monkeypatch, OPERATOR)
    monkeypatch.setattr(
        paywall, "_store_entitlement", lambda uid: (_ for _ in ()).throw(AssertionError("read!"))
    )
    assert _check().status_code == 204


def test_non_allowlisted_email_with_a_free_row_is_locked(monkeypatch):
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", OPERATOR)
    _row(monkeypatch, "free", status="none", features=(), email="someone.else@example.com")
    assert _check().status_code == 403


@pytest.mark.parametrize("value", ["", "   ", ","])
def test_empty_or_unset_allowlist_grants_nobody_anything(monkeypatch, value):
    """The allowlist is an env-only operator grant (never committed). With nothing in
    it the gate must behave exactly as if the bypass did not exist."""
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", value)
    _row(monkeypatch, "free", status="none", features=(), email=OPERATOR)
    assert _check().status_code == 403
    paywall._ENT_CACHE.clear()
    _row(monkeypatch, "pro", email=OPERATOR)
    assert _check().status_code == 204


def test_unset_allowlist_grants_nobody_anything(monkeypatch):
    _row(monkeypatch, "free", status="none", features=(), email=OPERATOR)
    assert _check().status_code == 403
    paywall._ENT_CACHE.clear()
    _row(monkeypatch, "pro", email=OPERATOR)
    assert _check().status_code == 204


@pytest.mark.parametrize(
    "stored,presented",
    [
        (OPERATOR, "  OPS@Mastermind-X.com "),
        ("  Ops@Mastermind-X.com , other@x.io", OPERATOR),
        ("a@x.io,ops@mastermind-x.com", "OPS@MASTERMIND-X.COM"),
    ],
)
def test_allowlist_matching_is_case_and_whitespace_insensitive(monkeypatch, stored, presented):
    """Delegated to brain_gateway._unlimited_allowed, which strips+lowers both sides.
    Pinned here because a second, stricter copy of the parsing in this module is
    exactly the drift this bypass is routed through the shared accessor to avoid."""
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", stored)
    _row(monkeypatch, "free", status="none", features=(), email=presented)
    assert _check().status_code == 204


def test_identity_without_an_email_gets_no_bypass_and_the_normal_tier_check(monkeypatch):
    """A Supabase response carrying no email cannot match any allowlist entry -- and
    must not short-circuit into one either (_unlimited_allowed returns False on '')."""
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", OPERATOR)
    _row(monkeypatch, "free", status="none", features=(), email="")
    assert _check().status_code == 403
    paywall._ENT_CACHE.clear()
    _row(monkeypatch, "pro", email="")
    assert _check().status_code == 204


class _Boom:
    def _unlimited_allowed(self, email):
        raise RuntimeError("brain gateway exploded")


class _Renamed:
    """The upstream helper renamed out from under us -> AttributeError."""


@pytest.mark.parametrize(
    "broken",
    [
        lambda: (_ for _ in ()).throw(RuntimeError("brain_gateway unavailable")),
        lambda: _Boom(),
        lambda: _Renamed(),
    ],
    ids=["import-raises", "call-raises", "helper-renamed"],
)
def test_a_broken_allowlist_lookup_falls_through_cleanly(monkeypatch, broken):
    """It must be neither the reason a Pro member is denied nor the reason a Free
    visitor is admitted -- the verdict falls back to the ordinary tier check."""
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", OPERATOR)
    monkeypatch.setattr("app.main._brain_module", broken)
    _row(monkeypatch, "pro", email=OPERATOR)
    assert _check().status_code == 204, "a broken allowlist denied a paying Pro member"
    paywall._ENT_CACHE.clear()
    _row(monkeypatch, "free", status="none", features=(), email=OPERATOR)
    assert _check().status_code == 403, "a broken allowlist admitted an unpaid visitor"


def test_the_bypass_uses_the_same_accessor_api_me_uses(monkeypatch):
    """Not a mock-shaped restatement of the code: this asserts the call actually lands
    on app.main._brain_module() -> brain_gateway._unlimited_allowed, which is what
    keeps the account pill and this door from drifting apart."""
    seen = []
    real = paywall._operator_unlimited

    def spy():
        from engine.neuralweb import brain_gateway

        seen.append(brain_gateway)
        return brain_gateway

    monkeypatch.setattr("app.main._brain_module", spy)
    monkeypatch.setenv("BRAIN_UNLIMITED_ALLOWLIST", OPERATOR)
    assert real(OPERATOR) is True
    assert real("nobody@example.com") is False
    assert seen, "the bypass did not go through app.main._brain_module()"
    assert seen[0]._unlimited_allowed(OPERATOR) is True


# ---------------------------------------------------------------------------
# _fresh_identity -- one upstream call, both fields, one expiry
# ---------------------------------------------------------------------------
class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_supabase(monkeypatch, payload, calls):
    def urlopen(req, timeout=None):
        calls.append(getattr(req, "full_url", None))
        return _FakeResp(payload)

    monkeypatch.setattr(paywall.urllib.request, "urlopen", urlopen)


def test_identity_reads_uid_and_email_from_a_single_supabase_call(monkeypatch):
    calls: list = []
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": 9_999_999_999}).encode("utf-8")
    ).decode("ascii").rstrip("=")
    token = f"header.{payload}.signature"
    _fake_supabase(monkeypatch, {"id": UID, "email": "  Ops@Mastermind-X.com "}, calls)
    assert paywall._fresh_identity(token) == (UID, "ops@mastermind-x.com")
    assert len(calls) == 1
    # Cached together: neither accessor issues a second request, and they cannot
    # disagree about which verification the pair came from.
    assert paywall._fresh_uid(token) == UID
    assert paywall._fresh_identity(token) == (UID, "ops@mastermind-x.com")
    assert len(calls) == 1


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"id": UID}, (UID, "")),
        ({"id": UID, "email": None}, (UID, "")),
        ({"id": UID, "email": 42}, (UID, "")),
        ({"id": "not-a-uuid", "email": "x@y.z"}, (None, "")),
        ({"email": "x@y.z"}, (None, "")),
        ({}, (None, "")),
    ],
)
def test_identity_degrades_to_empty_email_and_never_a_bogus_uid(monkeypatch, payload, expected):
    _fake_supabase(monkeypatch, payload, [])
    assert paywall._fresh_identity("tok-shape") == expected


def test_fresh_uid_contract_is_unchanged_by_the_refactor(monkeypatch):
    """The macro wall still calls _fresh_uid; its signature and answers must not move."""
    calls: list = []
    _fake_supabase(monkeypatch, {"id": UID, "email": EMAIL}, calls)
    assert paywall._fresh_uid("tok-1") == UID
    paywall._AUTH_CACHE.clear()
    _fake_supabase(monkeypatch, {"id": "garbage"}, calls)
    assert paywall._fresh_uid("tok-2") is None


# ---------------------------------------------------------------------------
# Fail closed
# ---------------------------------------------------------------------------
def test_auth_lookup_raising_remains_closed_but_is_not_a_paywall(monkeypatch):
    monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: "tok")
    monkeypatch.setattr(
        paywall,
        "_resolve_identity",
        lambda token: (_ for _ in ()).throw(RuntimeError("supabase down")),
    )
    r = _check()
    assert r.status_code == 500
    assert r.json()["error"] == "membership_verification_error"
    assert r.headers["x-paywall"] == "error"


def test_entitlement_store_raising_returns_recoverable_closed_response(monkeypatch):
    _signed_in(monkeypatch)
    monkeypatch.setattr(
        paywall,
        "_store_entitlement",
        lambda uid: (_ for _ in ()).throw(RuntimeError("postgrest down")),
    )
    r = _check()
    assert r.status_code == 500
    assert r.json()["error"] == "membership_verification_error"


def test_unreadable_catalog_denies_everyone_including_the_uncapped_tier(monkeypatch):
    """The rank order is read BEFORE the uncapped exception, deliberately: one rule."""
    monkeypatch.setattr(
        paywall, "_load_plans", lambda: (_ for _ in ()).throw(ValueError("no catalog"))
    )
    for tier in ("pro", "unlimited"):
        _row(monkeypatch, tier)
        paywall._ENT_CACHE.clear()
        assert _check().status_code == 500, tier


def test_catalog_that_no_longer_sells_pro_denies(monkeypatch, tmp_path):
    """`.index('pro')` raising is the intended behaviour, not an oversight: a catalog
    without the floor tier must not silently admit the next-best thing."""
    cat = tmp_path / "plans.yml"
    cat.write_text("tier_rank: [free, essential]\n", encoding="utf-8")
    monkeypatch.setattr(paywall, "PLANS_CONFIG", cat)
    _row(monkeypatch, "pro")
    assert _check().status_code == 500


@pytest.mark.parametrize("body", ["tier_rank: []\n", "tier_rank: pro\n", "[]\n", "\n"])
def test_shapeless_catalog_denies(monkeypatch, tmp_path, body):
    cat = tmp_path / "plans.yml"
    cat.write_text(body, encoding="utf-8")
    monkeypatch.setattr(paywall, "PLANS_CONFIG", cat)
    _row(monkeypatch, "pro")
    assert _check().status_code == 500


@pytest.mark.parametrize("path", ["//evil.test/x", "/a/../secret", "/bad%00", "/a\\b", ""])
def test_odd_original_uri_never_opens_the_door_and_never_crashes(monkeypatch, path):
    """The URI is read for ONE reason -- picking the deny body's shape. Identity is the
    authority, and Caddy forwards the ORIGINAL request to the origin, so this endpoint
    never authorizes a path and cannot be path-confused into doing so.

    Hence the contract is the pair below: a weird URI can neither admit a non-Pro
    caller nor produce a 5xx (a 5xx is not 2xx, so Caddy would deny -- but it would
    deny by crashing, with no interstitial and a stack trace in the log).
    """
    _row(monkeypatch, "essential")
    assert _check(path).status_code == 403
    paywall._ENT_CACHE.clear()
    _row(monkeypatch, "pro")
    assert _check(path).status_code in (204, 403)


# ---------------------------------------------------------------------------
# Shape of the answer
# ---------------------------------------------------------------------------
def test_browser_document_denial_is_html_and_uncacheable(monkeypatch):
    _row(monkeypatch, "essential")
    r = _check("/desk", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 403
    assert "text/html" in r.headers["content-type"]
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["vary"] == "Cookie"
    assert r.text.lstrip().lower().startswith("<!doctype html")


def test_bot_root_without_fetch_metadata_still_reads_as_a_document(monkeypatch):
    _row(monkeypatch, "free", features=())
    r = _check("/")
    assert r.status_code == 403
    assert "text/html" in r.headers["content-type"]


def test_non_document_denial_is_json_naming_the_required_tier(monkeypatch):
    _row(monkeypatch, "essential")
    r = _check("/api/positions")
    assert r.status_code == 403
    assert "application/json" in r.headers["content-type"]
    assert r.json()["required_tier"] == "pro"
    assert r.json()["upgrade_url"] == "/plans.html?upgrade=1&plan=pro"


def test_interstitial_file_is_what_a_denied_browser_receives(monkeypatch, tmp_path):
    """The page body is owned by app/paywall_pro_interstitial.html. Pinned through a
    temp file so this suite is green whether or not that file has landed yet."""
    page = tmp_path / "paywall_pro_interstitial.html"
    page.write_text("<!doctype html><title>x</title>PRO-INTERSTITIAL-SENTINEL", encoding="utf-8")
    monkeypatch.setattr(paywall, "PRO_INTERSTITIAL", page)
    _row(monkeypatch, "free", features=())
    r = _check("/", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 403
    assert "PRO-INTERSTITIAL-SENTINEL" in r.text


def test_missing_interstitial_still_denies_with_a_self_contained_page(monkeypatch, tmp_path):
    monkeypatch.setattr(paywall, "PRO_INTERSTITIAL", tmp_path / "does_not_exist.html")
    _row(monkeypatch, "free", features=())
    r = _check("/", headers={"Sec-Fetch-Dest": "document"})
    assert r.status_code == 403
    assert r.text.lstrip().lower().startswith("<!doctype html")
    # Absolute: this page renders on bot.mastermind-x.com, where /plans.html is not served.
    assert "https://mastermind-x.com/plans.html?upgrade=1&amp;plan=pro" in r.text
    assert "http://" not in r.text.replace("https://", "")


# ---------------------------------------------------------------------------
# What this endpoint deliberately does NOT do
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("switch", ["0", "1"])
def test_verdict_does_not_depend_on_the_macro_site_paywall_switch(monkeypatch, switch):
    """PAYWALL_ENABLED stages the MACRO wall. The bot desk is Pro-only either way --
    including while the switch is off, which is the state this ships into."""
    monkeypatch.setenv("PAYWALL_ENABLED", switch)
    _row(monkeypatch, "essential")
    assert _check().status_code == 403
    paywall._ENT_CACHE.clear()
    _row(monkeypatch, "pro")
    assert _check().status_code == 204


def test_no_path_classification_happens(monkeypatch):
    """The bot app owns its own URL space. A path the MACRO policy would 404 or wave
    through must get the same identity verdict as any other path on this host."""
    _row(monkeypatch, "pro")
    for path in (
        "/_mockup_research_vault.html",  # macro policy: deny -> 404 on the sibling
        "/plans.html",                   # macro policy: public -> 204 on the sibling
        "/desk",                         # exists only on the bot app
        "/api/positions",
    ):
        paywall._ENT_CACHE.clear()
        assert _check(path).status_code == 204, path
    monkeypatch.setattr(paywall, "_store_entitlement",
                        lambda uid: ({"tier": "free", "status": "none", "features": []}, True))
    for path in ("/_mockup_research_vault.html", "/plans.html", "/desk"):
        paywall._ENT_CACHE.clear()
        assert _check(path).status_code == 403, path


def test_sibling_macro_wall_is_unchanged_by_this_endpoint(monkeypatch):
    """Add, don't refactor: /api/paywall/check keeps classifying and keeps staging."""
    r = client.get(
        "/api/paywall/check",
        headers={"X-Original-Uri": "/neuralwebdata/ruling_graph.json", "X-Original-Kind": "asset"},
    )
    assert r.status_code == 204
    assert r.headers["x-paywall"] == "off"


# ---------------------------------------------------------------------------
# The wiring. A perfect endpoint nobody calls gates nothing.
# ---------------------------------------------------------------------------
def _bot_block() -> str:
    m = re.search(r"^bot\.mastermind-x\.com \{\n(.*?)^\}$", CADDY, flags=re.S | re.M)
    assert m, "the bot.mastermind-x.com site block is gone from app/deploy/Caddyfile"
    return m.group(1)


def test_caddy_routes_the_bot_host_through_the_pro_gate():
    body = _bot_block()
    assert "rewrite /api/paywall/check_pro" in body, (
        "bot.mastermind-x.com no longer issues the Pro auth subrequest -- the desk is "
        "open to anyone again"
    )
    assert "reverse_proxy 127.0.0.1:8000 {" in body, "the subrequest must go to macro-api"
    assert "header_up X-Original-Uri {http.request.uri}" in body
    assert re.search(r"@\w+ status 2xx\n\t+handle_response @\w+ \{\n\t+\}", body), (
        "the 2xx continue-to-origin matcher is missing; without it every request is "
        "answered by the auth response"
    )


def test_health_is_handled_ahead_of_the_gate_and_ungated():
    body = _bot_block()
    health = body.index("handle /health {")
    gate = body.index("/api/paywall/check_pro")
    assert health < gate, (
        "handle /health must precede the gated route -- admin/uptime_board.py probes it "
        "to tell 'the service is down' from 'you are not Pro'"
    )
    hblock = re.search(r"handle /health \{\n(.*?)\n\t\}", body, flags=re.S).group(1)
    assert "reverse_proxy 127.0.0.1:8001" in hblock
    assert "paywall" not in hblock, "/health must not be gated"


def test_gated_branch_is_never_shared_cache_material():
    """This host is orange-clouded; a Pro-only body in Cloudflare's cache is a leak."""
    body = _bot_block()
    gate = body.index("/api/paywall/check_pro")
    cache = body.index('header Cache-Control "private, no-store"')
    vary = body.index('header Vary "Cookie"')
    origin = body.index("reverse_proxy 127.0.0.1:8001", vary)
    assert gate < cache < vary < origin, (
        "the gated branch must set private/no-store + Vary: Cookie after the auth "
        "subrequest and before falling through to the bot origin"
    )


def test_bot_block_keeps_its_sni_and_robots_contract():
    """The block predates the gate and must not lose the reasons it existed."""
    body = _bot_block()
    assert "tls internal" in body, "removing this returns the origin handshake to HTTP 525"
    assert 'X-Robots-Tag "noindex, nofollow, noarchive"' in body
    assert "encode zstd gzip" in body


def test_uptime_probe_watches_the_open_health_path_with_a_real_assertion():
    """A None-expectation probe against a gated root collects a 403 and calls it up."""
    from admin.uptime_board import TARGETS

    bot = [t for t in TARGETS if t[1].startswith("https://bot.mastermind-x.com")]
    assert bot == [("Brain bot", "https://bot.mastermind-x.com/health", 200)], bot


# Shipped Bot expired-cookie renewal script: repeatable Node harness
DOCUMENT = ROOT / "app" / "paywall_pro_session_refresh.html"


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
@pytest.mark.parametrize(
    "case,mode,result,prior,has_broker,storage_off,expected_calls,expected_reload",
    [
        ("renewed", "yes", "fresh", False, True, False, 1, 1),
        ("refresh_error", "yes", "none", False, True, False, 1, 0),
        ("null_auth_envelope", "yes", "null_envelope", False, True, False, 1, 0),
        ("stale_session", "yes", "stale", False, True, False, 1, 0),
        ("invalid_credentials", "no", "fresh", False, True, False, 0, 0),
        ("bounded_repeat", "yes", "fresh", True, True, False, 0, 0),
        ("missing_sdk", "yes", "fresh", False, False, False, 0, 0),
        ("storage_unavailable", "yes", "fresh", False, True, True, 0, 0),
        ("auth_timeout", "yes", "pending", False, True, False, 1, 0),
        ("script_load_stall", "yes", "dom_stall", False, True, False, 0, 0),
    ],
)
def test_shipping_session_renewal_behavior(
    case: str,
    mode: str,
    result: str,
    prior: bool,
    has_broker: bool,
    storage_off: bool,
    expected_calls: int,
    expected_reload: int,
) -> None:
    html = DOCUMENT.read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?:\s+[^>]*)?>(.*?)</script>", html, re.S)
    actual = next((s for s in scripts if "function refresh()" in s), "")
    assert actual, "shipping recovery code missing"
    fixture = json.dumps(
        {"mode": mode, "result": result, "prior": prior, "hasBroker": has_broker,
         "storageOff": storage_off}
    )
    harness = r"""
const vm = require('node:vm');
const fixture = __FIXTURE__;
const javascript = __SOURCE__;
let calls = 0, reloads = 0, status = {textContent:''};
const timers = new Map();let nextTimerId = 0;
function armTimer(fn,ms){let id=++nextTimerId;timers.set(id,{fn,ms});return id;}
function disarmTimer(id){timers.delete(id);}
const key = 'mm.bot.session-renew.v1';
const memory = new Map();
if (fixture.prior) memory.set(key, String(Date.now() - 800));
let onDomReady = null;
const document = {
  readyState:fixture.result==='dom_stall' ? 'loading' : 'complete',
  addEventListener(name, callback) {
    if(name==='DOMContentLoaded') onDomReady = callback;
  },
  getElementById(name) { return name==='mm-bot-renew-status' ? status : {addEventListener(){}}; },
  querySelector(selector) {
    if(selector!=='meta[name="mm-bot-renew"]') throw Error('Unrecognized selector');
    return {content:fixture.mode};
  }
};
const window = {addEventListener(){}};
if(fixture.hasBroker) window.getSupabaseClient = () => {
  calls++;
  let session = fixture.result === 'none' ? null : {
    access_token:'test-only-not-authenticated',
    expires_at:Date.now()/1000 + (fixture.result==='fresh' ? 3600 : -300)
  };
  return Promise.resolve({auth:{getSession:()=>fixture.result==='pending'
    ? new Promise(()=>{}) : fixture.result==='null_envelope'
      ? Promise.resolve(null) : Promise.resolve({
      data:{session},error:fixture.result==='none'?{message:'no session'}:null
    })}});
};
if(window.getSupabaseClient) {
  window.getSupabaseClient.botRecoveryVersion = 1;
  window.getSupabaseClient.acceptRecoverySession = s =>
    !!(s && s.access_token && Number(s.expires_at)>Date.now()/1000+15);
}
vm.runInNewContext(javascript, {
  window,document,location:{reload(){reloads++;}},
  sessionStorage:{
    getItem(k){if(fixture.storageOff)throw Error('storage unavailable');return memory.get(k)||null;},
    setItem(k,v){if(fixture.storageOff)throw Error('storage unavailable');memory.set(k,v);}
  },
  Date,Number,JSON,Math,Promise,AbortController,console,setTimeout:armTimer,clearTimeout:disarmTimer
});
setImmediate(()=>{
  if(fixture.result==='pending' || fixture.result==='dom_stall'){
    const timeout=[...timers.values()].find(x=>x.ms===12000);
    if(!timeout)throw Error('Missing 12s deadline, including script load');
    timeout.fn(); // deterministic fake clock, even without DOMContentLoaded.
    if(fixture.result==='dom_stall' && onDomReady) onDomReady();
  }
  setImmediate(()=>{
    process.stdout.write(JSON.stringify({calls,reloads,prompt:status.textContent.includes('Please sign in again')}));
  });
});
""".replace("__SOURCE__", json.dumps(actual)).replace("__FIXTURE__", fixture)
    result_proc = subprocess.run(
        ["node", "-e", harness], text=True, capture_output=True, timeout=10, check=False
    )
    assert result_proc.returncode == 0, (case, result_proc.stderr)
    row = json.loads(result_proc.stdout)
    assert row["calls"] == expected_calls, case
    assert row["reloads"] == expected_reload, case
    assert row["prompt"] is (expected_reload == 0), case


def test_recovery_assets_are_first_party_and_no_unclean_redirects() -> None:
    html = DOCUMENT.read_text(encoding="utf-8")
    assert '<base href="https://www.mastermind-x.com/">' in html
    assert '<script src="https://www.mastermind-x.com/theme.js?bot-recovery=1" defer>' in html
    assert "supabase.co/auth/v1/token" not in html
    assert "document.cookie" not in html
    assert "window.location.href =" not in html
    assert "location.reload()" in html  # Same original URL, re-gated.
    assert "sessionStorage" in html  # Bounded renewal, no unbounded loop.


@pytest.mark.parametrize("path", ["/", "/desk.html"])
@pytest.mark.parametrize("headers", [
    {"Sec-Fetch-Dest": "empty", "Accept": "text/html"},
    {"X-Original-Kind": "asset", "Sec-Fetch-Dest": "document", "Accept": "text/html"},
])
@pytest.mark.parametrize("state", ["expired", "outage", "free", "config"])
def test_explicit_fetch_metadata_wins_over_document_shaped_bot_paths(
    monkeypatch, path, headers, state,
):
    _signed_in(monkeypatch)
    if state == "expired":
        monkeypatch.setattr("app.main._mm_supabase_access_token", lambda request: _jwt(1))
        expected = 401
    elif state == "outage":
        monkeypatch.setattr("app.billing._pg", _pg_raises(TimeoutError("synthetic timeout")))
        expected = 503
    elif state == "config":
        _blank_service_role(monkeypatch)
        expected = 500
    else:
        monkeypatch.setattr("app.billing._pg", _pg_result([]))
        expected = 403
    r = _check(path, headers=headers)
    assert r.status_code == expected
    assert r.headers["content-type"].startswith("application/json")
    assert isinstance(r.json(), dict)


@pytest.mark.parametrize("fault", [
    http.client.InvalidURL("synthetic bad URL"),
    json.JSONDecodeError("synthetic invalid JSON", "x", 0),
    ValueError("synthetic application defect"),
])
def test_non_transport_store_fault_is_not_retried_or_cached(monkeypatch, fault):
    monkeypatch.setattr("app.billing._pg", _pg_raises(fault))
    _signed_in(monkeypatch)
    r = _check()
    assert r.status_code == 500
    assert "retry-after" not in r.headers
    assert UID not in paywall._ENT_CACHE
