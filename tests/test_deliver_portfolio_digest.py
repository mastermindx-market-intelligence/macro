"""Synthetic Portfolio §19.5 job, mail ledger and RFC 8058 route integration."""
from __future__ import annotations

import asyncio
import io
import json
import socket
from urllib.parse import urlsplit

import pytest
from starlette.requests import Request

from app import mailer, marketing_emails, unsubscribe
from scripts import deliver_portfolio_digest as job
from tests.test_mailer import _FakeSmtplib, _Ledger, _mail_on

UID = "00000000-0000-4000-8000-000000000101"
DAY = "2026-11-02"
ADDRESS = "reader@example.invalid"


def book(uid, day):
    previous = {"asof": "2026-10-30", "names": {"SYN": {"stage": 2}}}
    current = {"asof": day, "names": {"SYN": {"stage": 3}}}
    return {"user_id": uid, "asof": day, "previous": previous,
            "current": current, "population": "positions"}


@pytest.fixture
def estate(monkeypatch):
    # Every transport and persistence operation stays inside this test.
    def no_network(*args, **kwargs):
        pytest.fail("external socket attempted")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setenv("MAIL_MARKETING_ENABLED", "1")
    monkeypatch.setenv("MAIL_UNSUB_SECRET", "synthetic-signing-key")
    monkeypatch.setenv("MAIL_SITE_BASE", "https://example.invalid")
    _mail_on(monkeypatch)
    ledger, smtp = _Ledger(), _FakeSmtplib()
    pref = {"user_id": UID, "portfolio_digest_opt_in": True, "marketing_opt_out": False}
    monkeypatch.setattr(mailer, "_pg", ledger.pg)
    monkeypatch.setattr(mailer, "smtplib", smtp)

    def read_pref(method, path):
        assert (method, path) == ("GET", f"email_prefs?user_id=eq.{UID}&select=*")
        return [dict(pref)]
    monkeypatch.setattr(marketing_emails, "_pg", read_pref)
    monkeypatch.setattr(marketing_emails, "_key", lambda: "fixture-key")

    def account(opener, req, **kwargs):
        assert req.full_url.endswith("/auth/v1/admin/users/" + UID)
        response = io.BytesIO(json.dumps({"id": UID, "email": ADDRESS,
                                          "email_confirmed_at": "2026-10-01"}).encode())
        response.status = 200
        return response
    monkeypatch.setattr(job.OpenerDirector, "open", account)
    return pref, ledger, smtp


def run(day=DAY, loader=book, **kwargs):
    return job.deliver_digest(UID, day, load_book=loader, enabled=True, **kwargs)


def test_one_change_one_message_then_one_click_stops_the_next_day(estate, monkeypatch):
    pref, ledger, smtp = estate
    assert run() == "sent"
    assert run() == "duplicate"
    [connection] = smtp.connections
    [msg] = connection["messages"]
    assert msg["To"] == ADDRESS
    assert msg["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    link = urlsplit(str(msg["List-Unsubscribe"]).strip("<>"))
    assert link.scheme == "https" and link.netloc == "example.invalid"
    assert link.path == "/api/email/unsubscribe"
    assert "/unsubscribe.html?t=" in msg.get_body(preferencelist=("html",)).get_content()
    [claim] = ledger.inserts
    assert claim["class"] == "marketing" and claim["idem_key"] == f"psi_digest:{UID}:{DAY}"
    assert "SYN" not in str((ledger.inserts, ledger.patches))

    def unsubscribe_store(method, path, body=None, **kwargs):
        assert method == "POST"
        row = body[0]
        if path == "email_suppression":
            assert row["email"] == ADDRESS
            ledger.suppressed[ADDRESS] = row["reason"]
        else:
            assert path == "email_prefs" and row["user_id"] == UID
            pref["marketing_opt_out"] = row["marketing_opt_out"]
    monkeypatch.setattr(unsubscribe, "_pg", unsubscribe_store)
    monkeypatch.setattr(unsubscribe, "_user_email", lambda uid: ADDRESS if uid == UID else None)
    assert any(route.path == link.path and route.endpoint == unsubscribe.unsubscribe
               for route in unsubscribe.router.routes)
    async def receive():
        return {"type": "http.request", "body": b"List-Unsubscribe=One-Click", "more_body": False}
    request = Request({"type": "http", "method": "POST", "path": link.path,
                       "query_string": link.query.encode(), "headers": [
                           (b"content-type", b"application/x-www-form-urlencoded")]}, receive)
    assert asyncio.run(unsubscribe.unsubscribe(request))["state"] == "unsubscribed"
    assert run("2026-11-03") == "not_opted_in"
    assert len(smtp.connections) == 1 and len(ledger.inserts) == 1


def test_quiet_or_mail_off_never_submits_a_message(estate, monkeypatch):
    _, ledger, smtp = estate
    def quiet(uid, day):
        row = book(uid, day)
        row["current"]["names"] = row["previous"]["names"]
        return row
    assert run(loader=quiet) == "quiet"
    monkeypatch.delenv("MAIL_SMTP_PASS")
    assert run() == "skipped_no_smtp"
    assert not ledger.inserts and not smtp.connections


def test_marketing_suppression_and_ledger_uncertainty_prevent_transport(estate, monkeypatch):
    _, ledger, smtp = estate
    ledger.suppressed[ADDRESS] = "complaint"
    assert run() == "suppressed"
    def unavailable(*args, **kwargs):
        raise OSError("fixture ledger unavailable")
    monkeypatch.setattr(mailer, "_ledger_insert", unavailable)
    assert run("2026-11-03") == "failed"
    assert not smtp.connections


def test_digest_opt_in_must_still_hold_after_composition(estate):
    pref, ledger, smtp = estate
    def revoke(uid, day):
        pref["portfolio_digest_opt_in"] = False
        return book(uid, day)
    assert run(loader=revoke) == "not_opted_in"
    assert not ledger.inserts and not smtp.connections


@pytest.mark.parametrize("account", [
    {"id": "00000000-0000-4000-8000-000000000102", "email": ADDRESS, "email_confirmed_at": DAY},
    {"id": UID, "email": ADDRESS, "email_confirmed_at": None},
    {"id": UID, "email": "first@example.invalid, second@example.invalid", "email_confirmed_at": DAY},
])
def test_auth_record_must_confirm_one_mailbox_for_this_account(estate, monkeypatch, account):
    _, ledger, smtp = estate
    def reply(*args, **kwargs):
        response = io.BytesIO(json.dumps(account).encode())
        response.status = 200
        return response
    monkeypatch.setattr(job.OpenerDirector, "open", reply)
    assert run() in {"source_unavailable", "recipient_unavailable"}
    assert not ledger.inserts and not smtp.connections


def test_unavailable_signing_secret_stops_before_ledger(estate, monkeypatch):
    _, ledger, smtp = estate
    monkeypatch.delenv("MAIL_UNSUB_SECRET")
    assert run() == "unsubscribe_unavailable"
    assert not ledger.inserts and not smtp.connections


def test_default_off_requires_no_dependencies(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("disabled job touched a dependency")
    monkeypatch.setattr(marketing_emails, "marketing_enabled", unexpected)
    monkeypatch.setattr(job, "_load_pref", unexpected)
    assert job.deliver_digest(UID, DAY, load_book=unexpected, send_fn=unexpected) == "disabled"


@pytest.mark.parametrize("patch", [
    {}, {"portfolio_digest_opt_in": False}, {"portfolio_digest_opt_in": "true"},
    {"portfolio_digest_opt_in": True, "marketing_opt_out": True},
    {"portfolio_digest_opt_in": True, "user_id": "00000000-0000-4000-8000-000000000102"},
])
def test_specific_consent_required_before_book_read(estate, monkeypatch, patch):
    row = {"user_id": UID, "marketing_opt_out": False, **patch}
    monkeypatch.setattr(job, "_load_pref", lambda uid: row)
    def forbidden(*args):
        pytest.fail("book read without consent")
    assert run(loader=forbidden) == "not_opted_in"


@pytest.mark.parametrize("patch", [
    {"user_id": "00000000-0000-4000-8000-000000000102"}, {"asof": "2026-11-01"},
    {"current": {"names": {}, "asof": "2026-11-01"}},
])
def test_mismatched_snapshot_cannot_reach_another_mailbox(estate, patch):
    _, ledger, smtp = estate
    assert run(loader=lambda uid, day: {**book(uid, day), **patch}) == "source_unavailable"
    assert not ledger.inserts and not smtp.connections
