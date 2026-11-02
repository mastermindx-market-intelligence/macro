"""B1 seam: flag-gated production wiring of the Catalyst opt-in funnel.

Every refusal must leave ``catalyst_optin`` unconfigured (503), must log only a
reason code (never a secret value), and a configured service must carry the
real ``ScanReceiptAuthority``, a fail-closed ``RevisionAuthority`` and a
delivery adapter that still refuses while ``MAIL_CATALYST_ENABLED`` is OFF.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app import catalyst_optin
from app import catalyst_optin_wiring as wiring
from app.catalyst_scan_authority import ScanReceiptAuthority
from engine.marketing.catalyst_lifecycle import SCOPE, FunnelGate, FunnelService

REPO = Path(__file__).resolve().parents[1]
MAIL_SECRET = "m" * 40
SCAN_SECRET = "s" * 40


def _contract_ok(method, path, body=None, **_kw):
    assert method == "POST" and path == "rpc/catalyst_consent_contract"
    return [{"owner": "email_consent", "version": 2}]


def _contract_down(method, path, body=None, **_kw):
    raise RuntimeError("consent owner unreachable")


@pytest.fixture
def env(monkeypatch):
    """Production-shaped environment with dummy test secrets; funnel reset after."""
    import app.account_actions as account_actions
    import app.mailer as mailer
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setenv("CATALYST_OPTIN_ENABLED", "1")
    monkeypatch.setenv("MAIL_UNSUB_SECRET", MAIL_SECRET)
    monkeypatch.setenv("CATALYST_SCAN_RECEIPT_SECRET", SCAN_SECRET)
    monkeypatch.delenv("MAIL_CATALYST_ENABLED", raising=False)
    monkeypatch.setattr(account_actions, "_supabase",
                        lambda: ("https://project.example.test", "service-role-test"))
    monkeypatch.setattr(account_actions, "_anon_key", lambda: "anon-test-key")
    monkeypatch.setattr(mailer, "_pg", _contract_ok)
    monkeypatch.setattr(catalyst_optin.SupabaseOtpIdentity, "_post",
                        lambda self, path, payload: pytest.fail("identity reached: " + path))
    catalyst_optin.configure(None)
    yield monkeypatch
    catalyst_optin.configure(None)


def _unconfigured() -> bool:
    try:
        catalyst_optin._active()
    except Exception as exc:  # HTTPException 503
        return getattr(exc, "status_code", None) == 503 and \
            getattr(exc, "detail", None) == "CATALYST_INTEGRATION_NOT_READY"
    return False


def test_switches_off_leave_the_router_unconfigured(env):
    env.delenv("CATALYST_OPTIN_ENABLED")
    assert wiring.configure_from_environment() is False
    assert _unconfigured()
    env.setenv("CATALYST_OPTIN_ENABLED", "1")
    env.delenv("CATALYST_PUBLIC_ENABLED")
    assert wiring.configure_from_environment() is False
    assert _unconfigured()


@pytest.mark.parametrize("name", ["MAIL_UNSUB_SECRET", "CATALYST_SCAN_RECEIPT_SECRET"])
def test_short_or_missing_secret_refuses_without_logging_its_value(env, caplog, name):
    env.setenv(name, "short-secret")
    with caplog.at_level(logging.WARNING, logger="macro.api"):
        assert wiring.configure_from_environment() is False
    assert _unconfigured()
    assert f"reason=secret_not_configured name={name}" in caplog.text
    assert "short-secret" not in caplog.text
    env.delenv(name)
    assert wiring.configure_from_environment() is False
    assert _unconfigured()


def test_identity_endpoint_missing_refuses(env, caplog):
    import app.account_actions as account_actions
    env.setattr(account_actions, "_supabase", lambda: ("", ""))
    with caplog.at_level(logging.WARNING, logger="macro.api"):
        assert wiring.configure_from_environment() is False
    assert _unconfigured()
    assert "reason=identity_not_configured" in caplog.text
    env.setattr(account_actions, "_supabase", lambda: ("http://plain.example.test", "k"))
    assert wiring.configure_from_environment() is False
    assert _unconfigured()


def test_consent_owner_not_answering_the_contract_refuses(env, caplog):
    import app.mailer as mailer
    env.setattr(mailer, "_pg", _contract_down)
    with caplog.at_level(logging.WARNING, logger="macro.api"):
        assert wiring.configure_from_environment() is False
    assert _unconfigured()
    assert "reason=consent_owner_not_ready" in caplog.text
    env.setattr(mailer, "_pg", lambda *a, **k: [{"owner": "email_consent", "version": 1}])
    assert wiring.configure_from_environment() is False
    assert _unconfigured()


def test_build_failure_refuses_with_type_name_only(env, caplog):
    def boom(*_a, **_k):
        raise KeyError("secret-looking detail must never be logged")
    env.setattr(catalyst_optin, "build_existing_owner_service", boom)
    with caplog.at_level(logging.WARNING, logger="macro.api"):
        assert wiring.configure_from_environment() is False
    assert _unconfigured()
    assert "reason=build_failed type=KeyError" in caplog.text
    assert "secret-looking" not in caplog.text


def test_configured_service_carries_real_scan_and_fail_closed_authorities(env, caplog):
    with caplog.at_level(logging.INFO, logger="macro.api"):
        assert wiring.configure_from_environment() is True
    service = catalyst_optin._active()
    assert isinstance(service, FunnelService)
    assert isinstance(service.scan, ScanReceiptAuthority)
    assert not isinstance(service.scan, catalyst_optin.UnwiredScanAuthority)
    assert isinstance(service.consent, catalyst_optin.SupabaseConsentRpcOwner)
    assert isinstance(service.identity, catalyst_optin.SupabaseOtpIdentity)
    assert isinstance(service.revisions, wiring.FailClosedRevisionAuthority)
    now = datetime.now(timezone.utc)
    assert service.revisions.is_current("ev-1", 1) is False
    assert service.revisions.read_public_rights(object(), now) is None
    assert service.sender.permitted() is False  # MAIL_CATALYST_ENABLED is OFF
    assert "catalyst optin wiring configured" in caplog.text
    assert "delivery=refused" in caplog.text
    assert MAIL_SECRET not in caplog.text and SCAN_SECRET not in caplog.text


def test_unwired_scan_authority_is_never_accepted(env):
    real = catalyst_optin.build_existing_owner_service

    def drop_scan(revisions, *, scan=None, **kw):
        return real(revisions, scan=None, **kw)
    env.setattr(catalyst_optin, "build_existing_owner_service", drop_scan)
    assert wiring.configure_from_environment() is False
    assert _unconfigured()


def test_request_gate_stops_before_identity_when_consent_goes_away(env):
    import app.mailer as mailer
    assert wiring.configure_from_environment() is True
    env.setattr(mailer, "_pg", _contract_down)  # owner lost after boot
    body = {"email": "person@example.test", "scope": SCOPE, "consent_checked": True,
            "scan_receipt": "abcdefgh.ijklmnop", "honeypot": "", "form_elapsed_ms": 5000}
    with pytest.raises(FunnelGate) as gate:
        catalyst_optin.request_optin(body)
    assert gate.value.code == "CONSENT_OWNER_NOT_READY"
    assert gate.value.status == 503


def test_scan_receipt_is_validated_by_the_real_authority(env):
    assert wiring.configure_from_environment() is True
    body = {"email": "person@example.test", "scope": SCOPE, "consent_checked": True,
            "scan_receipt": "abcdefgh.ijklmnop", "honeypot": "", "form_elapsed_ms": 5000}
    with pytest.raises(FunnelGate) as gate:
        catalyst_optin.request_optin(body)
    # Consent owner answered, so the forged receipt reaches the real HMAC check
    # and is refused there — never SCAN_AUTHORITY_NOT_WIRED, never GoTrue.
    assert (gate.value.code, gate.value.status) == ("INVALID_SCAN_PROOF", 400)


@pytest.mark.parametrize("break_it", ["switch_off", "short_secret", "consent_down"])
def test_a_later_refusal_clears_a_previously_configured_service(env, break_it):
    import app.mailer as mailer
    assert wiring.configure_from_environment() is True
    assert isinstance(catalyst_optin._active(), FunnelService)
    if break_it == "switch_off":
        env.delenv("CATALYST_OPTIN_ENABLED")
    elif break_it == "short_secret":
        env.setenv("MAIL_UNSUB_SECRET", "short")
    else:
        env.setattr(mailer, "_pg", _contract_down)
    assert wiring.configure_from_environment() is False
    assert _unconfigured()


def test_app_boot_hook_runs_after_the_router_mount_and_fails_closed():
    src = (REPO / "app" / "main.py").read_text(encoding="utf-8")
    mount = src.index("app.include_router(catalyst_secure_optin_router)")
    hook = src.index("from app.catalyst_optin_wiring import (")
    assert mount < hook
    assert src.index("_catalyst_optin_router_mounted = True") < hook
    block = src[hook - 120:hook + 700]
    assert "if not _catalyst_optin_router_mounted:" in block
    assert "_configure_catalyst_optin()" in block
    assert re.search(r"except Exception as _catalyst_optin_wiring_exc", block)
    assert "type(_catalyst_optin_wiring_exc).__name__" in block


def test_importing_the_app_with_flags_unset_configures_nothing_and_opens_no_socket():
    """Runs the real boot hook in a fresh interpreter: no network, no service."""
    import os
    import subprocess
    import sys
    probe = (
        "import urllib.request, socket\n"
        "calls=[]\n"
        "def deny(*a, **k): calls.append('net'); raise OSError('network disabled by test')\n"
        "urllib.request.urlopen = deny\n"
        "socket.socket.connect = deny\n"
        "import app.main\n"
        "from app import catalyst_optin\n"
        "print('service_none', catalyst_optin._service is None, 'net_calls', len(calls))\n"
    )
    clean = {k: v for k, v in os.environ.items()
             if k not in ("CATALYST_PUBLIC_ENABLED", "CATALYST_OPTIN_ENABLED",
                          "CATALYST_UX_ENABLED", "SUPABASE_SERVICE_ROLE_KEY")}
    out = subprocess.run([sys.executable, "-c", probe], cwd=str(REPO), env=clean,
                         capture_output=True, text=True, timeout=240)
    assert out.returncode == 0, out.stderr[-800:]
    assert "service_none True net_calls 0" in out.stdout
