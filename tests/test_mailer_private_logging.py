"""Regression: marketing/transactional mail failure logs must never expose identities.

All effects are hermetic: no Supabase request, SMTP attempt, real consent or email.
The canonical email_log still retains the real private idempotency key internally;
only diagnostic log messages are redacted.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import mailer  # noqa: E402


ADDRESS = "Catalyst.Private+123@example.invalid"
USER_ID = "9507e687-116a-4d30-9c30-fdf45c9d91b2"
IDEM_KEY = "catalyst:event-abc:2:" + USER_ID


def _db_down(*args, **kwargs):
    raise RuntimeError("database unavailable")


def _assert_no_private_log_values(caplog):
    text = caplog.text
    assert ADDRESS.lower() not in text.lower()
    assert USER_ID not in text
    assert IDEM_KEY not in text


def test_suppression_address_lookup_failure_redacts_email_and_fails_closed(monkeypatch, caplog):
    monkeypatch.setattr(mailer, "_pg", _db_down)
    with caplog.at_level(logging.WARNING, logger="macro.mailer"):
        with pytest.raises(mailer.SuppressionUnavailable):
            mailer._suppression_reason(ADDRESS, None)
    assert "address suppression lookup failed" in caplog.text
    _assert_no_private_log_values(caplog)


def test_suppression_preference_failure_redacts_user_id_and_fails_closed(monkeypatch, caplog):
    def fail_prefs(method, path, **kwargs):
        if path.startswith("email_suppression?"):
            return []
        raise RuntimeError("preferences unavailable")

    monkeypatch.setattr(mailer, "_pg", fail_prefs)
    with caplog.at_level(logging.WARNING, logger="macro.mailer"):
        with pytest.raises(mailer.SuppressionUnavailable):
            mailer._suppression_reason(ADDRESS, USER_ID)
    assert "marketing preference lookup failed" in caplog.text
    _assert_no_private_log_values(caplog)


def test_ledger_error_and_lost_race_logs_redact_idempotency_key(monkeypatch, caplog):
    monkeypatch.setattr(mailer, "_pg", _db_down)
    with caplog.at_level(logging.INFO, logger="macro.mailer"):
        assert mailer._ledger_finish(IDEM_KEY, "failed") is None
        assert not mailer._ledger_finish_if_current(
            IDEM_KEY, "failed", None, expected_status="queued"
        )
        assert not mailer._ledger_mark_attempting(IDEM_KEY)
    assert "ledger finish to failed failed" in caplog.text
    assert "could not mark outbound attempt" in caplog.text
    _assert_no_private_log_values(caplog)


def test_ledger_duplicate_does_not_log_raw_key_or_send(monkeypatch, caplog):
    def duplicate(**kwargs):
        raise mailer.DuplicateKey()

    monkeypatch.setattr(mailer, "_ledger_insert", duplicate)
    with caplog.at_level(logging.INFO, logger="macro.mailer"):
        status = mailer.send(
            template="catalyst_material_revision", cls="marketing",
            to_email=ADDRESS, user_id=USER_ID,
            subject="fixture", html="<p>fixture</p>", text="fixture",
            idem_key=IDEM_KEY, strict_ledger=True,
        )
    assert status == "duplicate"
    assert "duplicate idempotency claim" in caplog.text
    _assert_no_private_log_values(caplog)


def test_transport_uncertain_stops_and_logs_no_upstream_message(monkeypatch, caplog):
    monkeypatch.setattr(mailer, "_ledger_insert", lambda **kw: None)
    monkeypatch.setattr(mailer, "_suppression_reason", lambda *args: None)
    monkeypatch.setattr(mailer, "is_configured", lambda: True)
    monkeypatch.setattr(mailer, "_build_message", lambda **kw: object())

    def uncertain(*args, **kwargs):
        raise mailer.TransportUncertain(RuntimeError(ADDRESS))

    monkeypatch.setattr(mailer, "_smtp_send", uncertain)
    with caplog.at_level(logging.WARNING, logger="macro.mailer"):
        status = mailer.send(
            template="catalyst_material_revision", cls="marketing",
            to_email=ADDRESS, user_id=USER_ID,
            subject="fixture", html="<p>fixture</p>", text="fixture",
            idem_key=IDEM_KEY, strict_ledger=True,
        )
    assert status == mailer.EFFECT_UNKNOWN
    assert "EFFECT UNKNOWN" in caplog.text
    _assert_no_private_log_values(caplog)
