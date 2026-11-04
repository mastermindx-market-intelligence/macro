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


def test_authenticated_choice_and_two_account_nights_feed_the_digest(estate, monkeypatch):
    from fastapi import Response
    from app import account_prefs

    pref, ledger, smtp = estate
    pref["portfolio_digest_opt_in"] = False
    pref["portfolio_digest_revision"] = "00000000-0000-4000-8000-000000000201"
    writes = []
    def store(method, path, body=None, prefer=None):
        if method == "POST":
            assert path == "rpc/portfolio_digest_consent_set_v1" and prefer is None
            assert body == {"p_user_id": UID, "p_enabled": body["p_enabled"],
                            "p_expected_revision": pref["portfolio_digest_revision"] if body["p_enabled"] else None}
            pref["portfolio_digest_opt_in"] = body["p_enabled"]
            pref["portfolio_digest_revision"] = "00000000-0000-4000-8000-" + f"{202+len(writes):012d}"
            writes.append(body["p_enabled"])
            return {"status": "applied", "state": dict(pref)}
        assert method == "GET" and f"user_id=eq.{UID}" in path
        return [dict(pref)]
    monkeypatch.setattr(account_prefs, "_digest_pref_store", store)
    monkeypatch.setenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", "1")
    response = Response()
    def save(value):
        return account_prefs.set_portfolio_digest_choice(
            account_prefs.PortfolioDigestChoice(enabled=value,
                expected_revision=pref["portfolio_digest_revision"] if value else None),
            response, {"id": UID})
    assert save(True) == {"enabled": True, "marketing_opt_out": False,
                          "revision": pref["portfolio_digest_revision"]}
    assert response.headers["Cache-Control"] == "private, no-store"
    assert account_prefs.get_portfolio_digest_choice(response, {"id": UID})["enabled"]

    night = ["2026-10-30"]
    def context():
        return {"schema": "portfolio_ctx.v2", "asof": night[0], "tickers": {
            "SYN": {"stage": {"n": 2 if night[0] < DAY else 3}},
            "OTHER": {"stage": {"n": 4}}}}
    def holdings(uid):
        assert uid == UID
        return [{"ticker": "SYN", "shares": 1234, "entry_price": 99.9}], "positions"
    monkeypatch.setattr(job, "_capture_day", lambda: night[0])
    monkeypatch.setattr(job, "_nightly_context", context)
    monkeypatch.setattr(job, "_account_holdings", holdings)
    prior = job.capture_digest_night(UID, night[0], enabled=True)
    assert set(prior.snapshot["names"]) == {"SYN"}
    assert "shares" not in json.dumps(prior.snapshot)
    night[0] = DAY
    def read_prior(uid, cutoff):
        assert (uid, cutoff) == (UID, DAY)
        return prior
    assert job.deliver_digest(UID, DAY, enabled=True, read_previous=read_prior) == "sent"
    assert job.deliver_digest(UID, DAY, enabled=True, read_previous=read_prior) == "duplicate"
    monkeypatch.delenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED")
    assert save(False)["enabled"] is False
    assert writes == [True, False]
    assert job.deliver_digest(UID, DAY, enabled=True, read_previous=read_prior) == "not_opted_in"
    assert len(ledger.inserts) == 1 and len(smtp.connections) == 1


def test_missing_or_foreign_cursor_is_unavailable_before_reading_holdings(estate, monkeypatch):
    _, ledger, smtp = estate
    def never(uid):
        pytest.fail("private holdings read before cursor ownership was established")
    monkeypatch.setattr(job, "_account_holdings", never)
    for prior in (None, {}, "a hash without a capture",
                  job.NightlyCapture("00000000-0000-4000-8000-000000000102", "2026-11-01",
                                     "positions", {"names": {}})):
        assert job.deliver_digest(UID, DAY, enabled=True, read_previous=lambda uid, day: prior) == "source_unavailable"
    assert job.deliver_digest(UID, DAY, enabled=True) == "source_unavailable"
    assert not ledger.inserts and not smtp.connections


def test_capture_cannot_backdate_current_holdings_or_claim_an_unknown_book(estate, monkeypatch):
    monkeypatch.setattr(job, "_capture_day", lambda: DAY)
    def never(uid):
        pytest.fail("backdated holdings read")
    monkeypatch.setattr(job, "_account_holdings", never)
    with pytest.raises(ValueError):
        job.capture_digest_night(UID, "2026-10-30", enabled=True)
    ctx = {"schema": "portfolio_ctx.v2", "asof": DAY, "tickers": {}}
    monkeypatch.setattr(job, "_nightly_context", lambda: {**ctx, "asof": "2026-10-30"})
    with pytest.raises(ValueError):
        job.capture_digest_night(UID, DAY, enabled=True)
    monkeypatch.setattr(job, "_nightly_context", lambda: ctx)
    monkeypatch.setattr(job, "_account_holdings", lambda uid: ([], "unspecified"))
    with pytest.raises(ValueError):
        job.capture_digest_night(UID, DAY, enabled=True)


def test_choice_fails_closed_on_unauthorized_input_and_unconfirmed_write(monkeypatch):
    from fastapi import HTTPException, Response
    from pydantic import ValidationError
    from app import account_prefs as prefs

    assert any(route.endpoint == prefs.set_portfolio_digest_choice
               and "PUT" in route.methods for route in prefs.router.routes)
    assert prefs.set_portfolio_digest_choice.__defaults__[-1].dependency is prefs._current_user
    for body in ({"enabled": "true"}, {"enabled": True, "user_id": UID}):
        with pytest.raises(ValidationError):
            prefs.PortfolioDigestChoice(**body)
    calls = []
    def store(method, path, **kwargs):
        calls.append(method)
        if method == "GET":
            return []
        return {"status": "applied", "state": {"user_id": "wrong-user",
            "portfolio_digest_opt_in": True, "marketing_opt_out": False,
            "portfolio_digest_revision": "00000000-0000-4000-8000-000000000202"}}
    monkeypatch.setattr(prefs, "_digest_pref_store", store)
    monkeypatch.delenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", raising=False)
    body = prefs.PortfolioDigestChoice(enabled=True, expected_revision=None)
    for user, expected in [({}, 401), ({"id": UID}, 503)]:
        with pytest.raises(HTTPException) as err:
            prefs.set_portfolio_digest_choice(body, Response(), user)
        assert err.value.status_code == expected
    assert calls == []
    monkeypatch.setenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", "1")
    with pytest.raises(HTTPException) as err:
        prefs.set_portfolio_digest_choice(body, Response(), {"id": UID})
    assert err.value.status_code == 503 and calls == ["POST"]


def test_consent_readback_is_per_account_and_preserves_global_opt_out(monkeypatch):
    from fastapi import HTTPException, Response
    from app import account_prefs as prefs

    other = "00000000-0000-4000-8000-000000000102"
    revision = "00000000-0000-4000-8000-000000000201"
    rows = {uid: {"user_id": uid, "portfolio_digest_opt_in": True,
                  "portfolio_digest_revision": revision, "marketing_opt_out": uid == other}
            for uid in (UID, other)}
    def store(method, path, body=None, **kwargs):
        if method == "GET":
            uid = path.split("user_id=eq.", 1)[1].split("&", 1)[0]
            return [rows[uid].copy()]
        assert method == "POST" and path == "rpc/portfolio_digest_consent_set_v1"
        assert set(body) == {"p_user_id", "p_enabled", "p_expected_revision"}
        selected = rows[body["p_user_id"]]
        selected["portfolio_digest_opt_in"] = body["p_enabled"]
        selected["portfolio_digest_revision"] = "00000000-0000-4000-8000-000000000202"
        return {"status": "applied", "state": selected.copy()}
    monkeypatch.setattr(prefs, "_digest_pref_store", store)
    monkeypatch.delenv("PORTFOLIO_DIGEST_ENROLLMENT_ENABLED", raising=False)
    assert prefs.set_portfolio_digest_choice(prefs.PortfolioDigestChoice(enabled=False),
                                             Response(), {"id": UID})["enabled"] is False
    assert prefs.get_portfolio_digest_choice(Response(), {"id": other}) == {
        "enabled": True, "marketing_opt_out": True, "revision": revision}
    def schema_missing(*args, **kwargs):
        raise RuntimeError("column unavailable")
    monkeypatch.setattr(prefs, "_digest_pref_store", schema_missing)
    with pytest.raises(HTTPException) as err:
        prefs.get_portfolio_digest_choice(Response(), {"id": UID})
    assert err.value.status_code == 503


def test_native_capture_uses_configured_nightly_path_and_exact_account(tmp_path, estate, monkeypatch):
    import sys
    from types import ModuleType

    # Supply the exact host interfaces used by the already-mounted portfolio
    # endpoint while isolating the test from the web app's startup and stores.
    native = ModuleType("app.main")
    native.REPO = tmp_path
    native._PORTFOLIO_CTX_PATH = "fixture-ctx.json"
    path = tmp_path / native._PORTFOLIO_CTX_PATH
    path.write_text(json.dumps({"schema": "portfolio_ctx.v2", "asof": DAY,
                                "tickers": {"SYN": {"stage": {"n": 2}}, "FOREIGN": {"stage": {"n": 3}}}}))
    seen = []
    def holdings(uid):
        seen.append(uid)
        return [{"ticker": "SYN"}], "watchlist_union"
    native._portfolio_load_holdings = holdings
    monkeypatch.setitem(sys.modules, "app.main", native)
    monkeypatch.setattr(job, "_capture_day", lambda: DAY)
    result = job.capture_digest_night(UID, DAY, enabled=True)
    assert seen == [UID] and result.user_id == UID and result.population == "watchlist_union"
    assert set(result.snapshot["names"]) == {"SYN"}
