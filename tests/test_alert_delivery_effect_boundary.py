"""tests/test_alert_delivery_effect_boundary.py -- the POST-SMTP EFFECT-UNKNOWN boundary.

RED-first. Every test here asserts on the RELAY'S MAILBOX -- the physical effect -- and
never on a counter the system computed about itself. A drain that reports
``fired_n=1 duplicate_n=1`` while the recipient holds two copies of the same alert is
exactly the failure this file exists to catch, and a counter-only assertion cannot see
it (mission: "Tests must detect the current unsafe transition, not merely assert final
counters").

THE DEFECT
    ``app/mailer.py``'s ``send()`` claims an ``email_log`` row as ``'queued'`` BEFORE
    SMTP and PATCHes it to ``'sent'`` AFTER. Between those two writes sits the physical
    delivery. A process death, service timeout, or a swallowed ledger write anywhere in
    that window leaves the durable state ``email_log='queued'`` /
    ``alert_outbox='pending'`` while the email is already in the recipient's inbox.
    ``engine/alert_delivery_drain.py`` reads that ``'queued'``, bumps ``attempts``, and
    the next tick mints a FRESH idempotency key -- which is a licence to deliver the
    same logical alert a second time.

WHAT A DURABLE ``'queued'`` CAN MEAN (the ambiguity being removed)
    (a) transport was never entered           -> provably NOT sent   -> safe to retry
    (b) transport is being entered right now  -> a LIVE writer       -> wait, don't touch
    (c) transport was entered, writer is gone -> EFFECT UNKNOWN      -> never auto-retry

EXACTLY-ONCE IS NOT AVAILABLE
    SMTP cannot prove (c) either way: a connection that drops while the client waits for
    the reply to the terminating '.' may have been queued by the server or discarded. The
    contract these tests pin is therefore AT-MOST-ONCE-PER-LOGICAL-ALERT under
    uncertainty -- preserve the uncertainty, quarantine the row, surface it to an
    operator -- rather than a manufactured certainty in either direction.
"""
from __future__ import annotations

import re
import smtplib
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import mailer
from engine import alert_delivery_drain as drain


# --------------------------------------------------------------------------- #
# Process death
# --------------------------------------------------------------------------- #
class ProcessDied(BaseException):
    """A kill, not an error.

    Subclasses ``BaseException`` ON PURPOSE: ``mailer.send`` and ``drain.drain`` are
    both armoured with bare ``except Exception`` clauses, and a death those clauses
    can catch is not a death -- it would be quietly converted into a tidy 'failed'
    status and none of these tests would model anything real.
    """


# --------------------------------------------------------------------------- #
# The relay: the recipient's MAILBOX is the ground truth
# --------------------------------------------------------------------------- #
class FakeRelay:
    """Records what the SMTP server actually accepted responsibility for.

    ``mailbox`` is the physical effect. ``fault`` selects where the client-visible
    failure happens RELATIVE to that acceptance, which is the whole point: the
    dangerous cases are the ones where the mailbox grows and the client never learns.
    """

    def __init__(self):
        self.mailbox: list = []
        self.sessions: list[str] = []
        self.fault = None          # None | 'connect' | 'login' | 'refuse_rcpt'
                                   # | 'reject_data' | 'unparsed_data_reply'
                                   # | 'drop_during_data' | 'accept_then_drop'
                                   # | 'accept_then_quit_anomaly' | 'accept_then_die'
                                   # | 'drop_after_marker' | 'noop_refused'
                                   # | 'accept_then_uncertain_then_quit_anomaly'

    # -- module-level stand-ins for smtplib.SMTP / smtplib.SMTP_SSL ------------
    def SMTP(self, host, port, timeout=None):  # noqa: N802 -- mirrors the stdlib name
        return _FakeSMTP(self, host, port)

    def SMTP_SSL(self, host, port, timeout=None, context=None):  # noqa: N802
        return _FakeSMTP(self, host, port)


class _FakeSMTP:
    def __init__(self, relay: FakeRelay, host, port):
        self.relay = relay
        if relay.fault == "connect":
            raise smtplib.SMTPConnectError(421, "cannot connect")
        relay.sessions.append(f"{host}:{port}")
        self._accepted = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        # Mirrors CPython's smtplib.SMTP.__exit__: QUIT is issued on the way out and a
        # non-221 reply raises SMTPResponseException AFTER the message was accepted.
        if self.relay.fault == "accept_then_quit_anomaly" and self._accepted:
            raise smtplib.SMTPResponseException(451, b"quit failed")
        if getattr(self, "_quit_anomaly", False):
            raise smtplib.SMTPResponseException(451, b"quit failed")
        return False

    def ehlo(self, *a, **k):
        return (250, b"ok")

    def starttls(self, *a, **k):
        return (220, b"ready")

    def noop(self):
        # The session probe mailer._deliver issues after the marker write.
        if self.relay.fault == "drop_after_marker":
            raise smtplib.SMTPServerDisconnected("relay dropped the idle session")
        if self.relay.fault == "noop_refused":
            return (421, b"service not available")
        return (250, b"ok")

    def login(self, user, password):
        if self.relay.fault == "login":
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")
        return (235, b"ok")

    def send_message(self, msg):
        f = self.relay.fault
        # ---- refusals that happen BEFORE the server ever sees the body ----------
        if f == "refuse_rcpt":
            raise smtplib.SMTPRecipientsRefused({msg["To"]: (550, b"no such user")})
        if f == "reject_data":
            raise smtplib.SMTPDataError(554, b"message rejected")
        if f == "unparsed_data_reply":
            # CPython getreply() yields errcode -1 when a reply line's code does not
            # parse. sendmail then raises SMTPDataError(-1, ...) for the reply to the
            # TERMINATING '.', so the relay may already have committed the message.
            self.relay.mailbox.append(msg)
            self._accepted = True
            raise smtplib.SMTPDataError(-1, b"\xff\xfe garbage")
        if f == "accept_then_uncertain_then_quit_anomaly":
            # The relay commits, the socket then dies mid-acknowledgement (uncertain),
            # and QUIT answers non-221 on the way out -- which Python lets REPLACE the
            # uncertainty unless it was recorded.
            self.relay.mailbox.append(msg)
            self._quit_anomaly = True
            raise smtplib.SMTPServerDisconnected("dropped awaiting the final reply")
        # ---- the body is streamed; the server may or may not commit ------------
        if f == "drop_during_data":
            # The classic irreducible case: the connection dies while the client is
            # waiting for the reply to the terminating '.'. The message is NOT in the
            # mailbox here -- this models the half where the server discarded it --
            # but the CLIENT cannot tell this apart from 'accept_then_drop' below.
            raise smtplib.SMTPServerDisconnected("connection closed during DATA")
        # ---- the server has now accepted responsibility ------------------------
        self.relay.mailbox.append(msg)
        self._accepted = True
        if f == "accept_then_drop":
            # Same client-visible exception as 'drop_during_data', opposite reality.
            raise smtplib.SMTPServerDisconnected("connection closed after 250")
        if f == "accept_then_die":
            raise ProcessDied("killed after the server accepted the message")
        return {}


# --------------------------------------------------------------------------- #
# One durable store, shared by the mailer and the drain -- because in production
# they are one Postgres. The boundary defect lives in the handoff BETWEEN them, so a
# test that gives each its own fake store cannot observe it.
# --------------------------------------------------------------------------- #
class EstateDB:
    def __init__(self):
        self.email_log: dict[str, dict] = {}
        self.outbox: list[dict] = []
        self.users: dict[str, dict] = {}
        self.runs: dict[str, dict] = {}
        # Faults are aimed at ONE of the two email_log writes. The marker PATCH
        # (status stays 'queued') and the terminal PATCH (status becomes sent/failed)
        # sit on opposite sides of the physical delivery, so a test that cannot tell
        # them apart cannot model this boundary at all.
        self.ledger_patch_fault = None   # None | 'die' | 'error'  -> TERMINAL patch
        self.marker_patch_fault = None   # None | 'error'          -> MARKER patch
        self.patched_keys: list[str] = []
        self.marker_writes: list[str] = []

    # -- app/mailer.py seam ---------------------------------------------------
    def mailer_pg(self, method, path, body=None, prefer=None, timeout=6):
        path = urllib.parse.unquote(path)
        if method == "POST" and path.startswith("email_log"):
            row = dict((body or [{}])[0])
            key = row.get("idem_key")
            if key in self.email_log:
                raise mailer.DuplicateKey("duplicate key value violates unique constraint")
            self.email_log[key] = row
            return None
        if method == "PATCH" and path.startswith("email_log"):
            key = path.split("idem_key=eq.", 1)[1].split("&", 1)[0]
            self.patched_keys.append(key)
            is_marker = (body or {}).get("status") == "queued"
            if is_marker:
                self.marker_writes.append(key)
                if self.marker_patch_fault == "error":
                    raise RuntimeError("supabase 503 on the marker write")
            else:
                if self.ledger_patch_fault == "die":
                    raise ProcessDied("killed while writing the email_log terminal status")
                if self.ledger_patch_fault == "error":
                    raise RuntimeError("supabase 503")
            if key in self.email_log:
                self.email_log[key].update(body or {})
                if prefer == "return=representation":
                    return [dict(self.email_log[key])]
            elif prefer == "return=representation":
                return []
            return None
        if method == "GET" and path.startswith("email_suppression"):
            return []
        if method == "GET" and path.startswith("email_prefs"):
            return []
        raise AssertionError(f"unexpected mailer PostgREST call {method} {path}")

    # -- engine/alert_delivery_drain.py seam ----------------------------------
    def drain_pg(self, method, path, body=None, prefer=None, timeout=6):
        if path.startswith("alert_outbox") and method == "GET":
            return [r for r in self.outbox if _selected(r, path)]
        if path.startswith("alert_outbox") and method == "PATCH":
            row_id = re.search(r"id=eq\.([^&]+)", path).group(1)
            for r in self.outbox:
                if str(r["id"]) == urllib.parse.unquote(row_id):
                    r.update(body)
            return None
        if path.startswith("alert_runs") and method == "POST":
            self.runs[body[0]["id"]] = dict(body[0])
            return None
        if path.startswith("alert_runs") and method == "PATCH":
            rid = re.search(r"id=eq\.([^&]+)", path).group(1)
            self.runs.setdefault(rid, {}).update(body)
            return None
        if path.startswith("email_log") and method == "GET":
            key = urllib.parse.unquote(re.search(r"idem_key=eq\.([^&]+)", path).group(1))
            row = self.email_log.get(key)
            if row is None:
                return []
            # Honour PostgREST's select= projection so a test can never read a column
            # the production query does not actually ask for.
            sel = re.search(r"select=([^&]+)", path)
            cols = sel.group(1).split(",") if sel else list(row)
            return [{c: row.get(c) for c in cols}]
        if path.startswith("email_suppression"):
            return []
        if path.startswith("user_entitlements"):
            return []
        raise AssertionError(f"unexpected drain PostgREST call {method} {path}")


def _selected(row: dict, path: str) -> bool:
    """Mirrors drain.drain's own ``or=(...)`` predicate, so a row that production
    would never re-select cannot be re-selected here either."""
    status = row.get("status")
    if status == "pending":
        return True
    if status == "failed":
        m = re.search(r"attempts\.lt\.(\d+)", path)
        cap = int(m.group(1)) if m else drain.ALERT_RETRY_ATTEMPTS_CAP
        return int(row.get("attempts") or 0) < cap
    if status == "deferred":
        m = re.search(r"deliver_after\.lte\.([^&)]+)", path)
        if not m:
            return False
        return bool(row.get("deliver_after")) and str(row["deliver_after"]) <= urllib.parse.unquote(m.group(1))
    return False


OPTED_IN = {"email": "reader@example.com",
            "user_metadata": {"alert_email_optin": "true",
                              "alert_categories": ["thesis_window"], "lang": "en"}}


def _outbox_row(**kw):
    base = dict(id=str(uuid.uuid4()), user_id="u1", alert_id="a1", fire_event_id="fe1",
                status="pending", attempts=0, deliver_after=None, delivered_at=None,
                last_error=None,
                payload={"subject": "AAPL moved", "ticker": "AAPL",
                         "category": "thesis_window",
                         "summary_plain": "It moved a lot today.",
                         "condition_plain": "the price crossed your level",
                         "evidence_url": "https://example.com/e",
                         "fired_at": "2026-09-18T14:00:00Z"})
    base.update(kw)
    return base


@pytest.fixture
def estate(monkeypatch):
    """Wire the mailer and the drain to ONE durable store and ONE relay."""
    db, relay = EstateDB(), FakeRelay()
    db.outbox.append(_outbox_row())
    db.users["u1"] = OPTED_IN

    monkeypatch.setenv("SUPABASE_URL", "https://db.example.com")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setenv("MAIL_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("MAIL_SMTP_PORT", "587")
    monkeypatch.setenv("MAIL_SMTP_USER", "u")
    monkeypatch.setenv("MAIL_SMTP_PASS", "p")
    monkeypatch.setenv("MAIL_FROM", "alerts@example.com")

    monkeypatch.setattr(mailer, "_pg", db.mailer_pg)
    monkeypatch.setattr(mailer, "smtplib", relay)
    monkeypatch.setattr(mailer.time, "sleep", lambda s: None)
    monkeypatch.setattr(drain, "_pg", db.drain_pg)
    monkeypatch.setattr(drain, "fetch_user_record",
                        lambda uid: (drain.READ_OK, db.users.get(str(uid)))
                        if db.users.get(str(uid)) else (drain.READ_UNAVAILABLE, None))
    return db, relay


def _tick(db, *, now, expect_death=False):
    """Run one drain tick against the real ``mailer.send_alert``.

    ``expect_death=True`` lets a ``ProcessDied`` escape the drain the way a real SIGKILL
    would: the tick's remaining writes simply never happen.
    """
    try:
        return drain.drain(send_fn=mailer.send_alert, now_utc=now, limit=10)
    except ProcessDied:
        if not expect_death:
            raise
        return None


T0 = datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc)


# ============================================================================ #
# The six required termination points
# ============================================================================ #
def test_p1_death_immediately_before_smtp_is_provably_not_sent_and_stays_retryable(estate):
    """POINT 1 -- killed after the ledger claim, before the message reaches the wire.

    PROVABLE: nothing was delivered. No write-ahead marker was ever persisted, and the
              marker is written at the last instant before DATA -- so its ABSENCE is
              itself the proof that the message never went out.
    UNKNOWN:  nothing.
    Therefore this is the one shape that MUST stay retryable, and the retry must
    actually put the mail in the mailbox.
    """
    db, relay = estate

    def die_before_transport(msg, before_data=None):
        raise ProcessDied("killed before SMTP")

    # Kill inside _smtp_send's caller frame but before any relay contact.
    import app.mailer as m
    original = m._smtp_send
    m._smtp_send = die_before_transport
    try:
        _tick(db, now=T0, expect_death=True)
    finally:
        m._smtp_send = original

    assert relay.sessions == [], "no SMTP session may have been opened"
    assert relay.mailbox == [], "nothing may have been delivered"
    key = mailer.alert_idem_key("fe1", attempt=0)
    assert db.email_log[key]["status"] == "queued"

    # The recovery must deliver, exactly once. It costs two ticks, not one: tick 1
    # RESOLVES the orphaned claim (the same idem_key is still claimed, so the mailer
    # answers 'duplicate') and mints the next attempt; tick 2 sends under that fresh
    # key. That two-step is correct here precisely BECAUSE the row is provably unsent.
    for i in range(1, 4):
        _tick(db, now=T0 + timedelta(minutes=5 * i))
    assert len(relay.mailbox) == 1, "a provably-unsent alert must still be delivered"
    assert db.outbox[0]["status"] == "sent"


def test_p1c_death_in_the_residual_window_is_conservatively_quarantined(estate):
    """POINT 1, the residual window -- killed AFTER the marker persisted but BEFORE
    ``send_message`` was entered.

    PROVABLE (to an outside observer): nothing was delivered.
    PROVABLE (to this system): nothing. The marker is on disk and the writer is gone,
              which is byte-identical to a death mid-DATA.
    So this is over-approximated as effect-unknown and quarantined. The window is a
    few local instructions wide -- it is the price of having any durable marker at all,
    and it errs toward an operator-visible under-delivery rather than a silent
    duplicate. Pinned here so the cost is a stated property, not a surprise.
    """
    db, relay = estate

    real_deliver = mailer._deliver

    def die_after_marker(s, msg, before_data=None):
        if before_data is not None:
            before_data()                      # the marker lands
        raise ProcessDied("killed between the marker and DATA")

    mailer._deliver = die_after_marker
    try:
        _tick(db, now=T0, expect_death=True)
    finally:
        mailer._deliver = real_deliver

    assert relay.mailbox == [], "precondition: nothing actually went out"
    key = mailer.alert_idem_key("fe1", attempt=0)
    assert drain.SMTP_ATTEMPT_MARKER in str(db.email_log[key]["detail"])

    for i in range(1, 4):
        _tick(db, now=T0 + timedelta(minutes=5 * i))

    assert relay.mailbox == [], "an unprovable state must not be resolved by guessing"
    assert db.outbox[0]["status"] == "failed"
    assert db.outbox[0]["last_error"] == drain.EFFECT_UNKNOWN_LAST_ERROR


def test_p2_death_during_smtp_is_effect_unknown_and_is_never_auto_resent(estate):
    """POINT 2 -- the connection dies while the body is in flight.

    PROVABLE: the transport was entered; the message left this process.
    UNKNOWN:  whether the server committed it. ``drop_during_data`` and
              ``accept_then_drop`` raise the IDENTICAL exception and differ only in
              reality -- see the paired test below.
    Therefore: never a fresh send under a new identity.
    """
    db, relay = estate
    relay.fault = "drop_during_data"

    _tick(db, now=T0)
    delivered_after_first = len(relay.mailbox)
    relay.fault = None            # the relay recovers; only the uncertainty persists

    for i in range(1, 6):                      # five further ticks -- well past the cap
        _tick(db, now=T0 + timedelta(minutes=5 * i))

    assert len(relay.mailbox) == delivered_after_first, (
        "an effect-unknown alert was re-delivered: the mailbox grew from "
        f"{delivered_after_first} to {len(relay.mailbox)}")
    assert db.outbox[0]["status"] != "sent", "an unknown effect must not be claimed as sent"


def test_p3_death_after_server_acceptance_before_ledger_finish_never_resends(estate):
    """POINT 3 -- THE headline case. The server took the message; the process died
    before ``_ledger_finish`` could record it.

    PROVABLE: the email is in the recipient's inbox.
    UNKNOWN:  nothing about the delivery -- but the DURABLE state knows nothing, which
              is the same thing from the drain's point of view.
    """
    db, relay = estate
    relay.fault = "accept_then_die"

    _tick(db, now=T0, expect_death=True)

    assert len(relay.mailbox) == 1, "precondition: the server accepted exactly one message"
    key = mailer.alert_idem_key("fe1", attempt=0)
    assert db.email_log[key]["status"] == "queued", "precondition: the ledger never learned"
    assert db.outbox[0]["status"] == "pending", "precondition: the outbox never learned"

    # The crash was a one-off. Every later tick runs on a HEALTHY process against a
    # HEALTHY relay -- which is precisely why a re-send here would really land.
    relay.fault = None
    for i in range(1, 6):
        _tick(db, now=T0 + timedelta(minutes=5 * i))

    assert len(relay.mailbox) == 1, (
        "THE DEFECT: an already-delivered alert was sent again -- the recipient holds "
        f"{len(relay.mailbox)} copies of one logical alert")


def test_p4_death_during_the_email_log_sent_patch_never_resends(estate):
    """POINT 4 -- the server accepted and the process died mid-PATCH.

    PROVABLE: delivered.
    UNKNOWN:  whether the PATCH landed server-side (the client never read a reply).
    Either way a second send is unsafe.
    """
    db, relay = estate
    db.ledger_patch_fault = "die"

    _tick(db, now=T0, expect_death=True)
    assert len(relay.mailbox) == 1
    db.ledger_patch_fault = None

    for i in range(1, 6):
        _tick(db, now=T0 + timedelta(minutes=5 * i))

    assert len(relay.mailbox) == 1, (
        "a delivered alert whose ledger PATCH was interrupted was re-delivered")


def test_p4b_swallowed_ledger_patch_error_does_not_lose_the_send(estate):
    """POINT 4, the non-fatal half: the PATCH raises but the PROCESS SURVIVES.

    ``_ledger_finish`` is best-effort by design, so ``send()`` still returns 'sent' and
    the in-process return value -- not the ledger -- is the truth for this tick. The
    outbox must converge on that, and no second delivery may follow.
    """
    db, relay = estate
    db.ledger_patch_fault = "error"

    _tick(db, now=T0)
    assert len(relay.mailbox) == 1
    assert db.outbox[0]["status"] == "sent", (
        "send() returned 'sent'; a swallowed ledger write must not lose that fact")

    db.ledger_patch_fault = None
    for i in range(1, 4):
        _tick(db, now=T0 + timedelta(minutes=5 * i))
    assert len(relay.mailbox) == 1


def test_p4c_an_unwritable_attempt_marker_refuses_to_send_at_all(estate):
    """The write-ahead marker is fail-closed: if the boundary cannot be made durable,
    the boundary is not crossed.

    PROVABLE: nothing was delivered -- the transport was never entered.
    UNKNOWN:  whether the marker PATCH landed server-side despite the error. If it did,
              the drain will later quarantine a message that was never sent. That is
              the deliberate direction of the asymmetry: a visible under-delivery an
              operator can release, never an invisible double-delivery.
    """
    db, relay = estate
    db.marker_patch_fault = "error"

    _tick(db, now=T0)
    assert relay.mailbox == [], "no marker means no message on the wire"
    # A session IS opened first: the marker is written at the last instant before DATA
    # (see app/mailer.py::_deliver), which is what keeps connect/TLS/AUTH failures
    # provably-unsent instead of conservatively quarantined. Aborting after AUTH costs
    # one wasted session and buys a much narrower uncertainty window.
    assert relay.sessions == ["smtp.example.com:587"]

    db.marker_patch_fault = None
    for i in range(1, 4):
        _tick(db, now=T0 + timedelta(minutes=5 * i))
    assert len(relay.mailbox) == 1, "and once the ledger recovers, it must still deliver"


def test_p5_death_after_ledger_sent_before_outbox_sent_converges_to_sent(estate):
    """POINT 5 -- ``email_log='sent'`` but the outbox PATCH never happened.

    PROVABLE: delivered, and the ledger proves it.
    UNKNOWN:  nothing.
    Therefore the row must CONVERGE to 'sent' -- not be retried, and not be stranded.
    """
    db, relay = estate

    real_patch = drain._patch_outbox
    calls = {"n": 0}

    def die_on_outbox_patch(row_id, body):
        calls["n"] += 1
        raise ProcessDied("killed between the ledger write and the outbox write")

    drain._patch_outbox = die_on_outbox_patch
    try:
        _tick(db, now=T0, expect_death=True)
    finally:
        drain._patch_outbox = real_patch

    assert len(relay.mailbox) == 1
    key = mailer.alert_idem_key("fe1", attempt=0)
    assert db.email_log[key]["status"] == "sent", "precondition: the ledger DID learn"
    assert db.outbox[0]["status"] == "pending", "precondition: the outbox did not"

    _tick(db, now=T0 + timedelta(minutes=5))
    assert len(relay.mailbox) == 1, "a known-sent alert must never be re-delivered"
    assert db.outbox[0]["status"] == "sent", "a known-sent row must converge to sent"


def test_p6_sigterm_mid_drain_decomposes_into_the_other_points(estate):
    """POINT 6 -- a service timeout / SIGTERM mid-drain.

    A signal is not a distinct failure MODE: it lands at some instruction, and that
    instruction is in one of points 1-5. What this pins is that the decomposition is
    real for the two-row case -- a kill after row A is fully resolved and before row B
    is touched leaves A durable and B untouched, and the recovery tick delivers B once
    and A never again.
    """
    db, relay = estate
    db.outbox.append(_outbox_row(fire_event_id="fe2", alert_id="a2"))

    real_send = mailer.send_alert
    seen = []

    def send_then_sigterm(**kw):
        if kw["fire_event_id"] in seen:
            raise AssertionError("row re-entered within one tick")
        seen.append(kw["fire_event_id"])
        if len(seen) == 2:                     # SIGTERM as row 2 begins
            raise ProcessDied("SIGTERM")
        return real_send(**kw)

    try:
        drain.drain(send_fn=send_then_sigterm, now_utc=T0, limit=10)
    except ProcessDied:
        pass

    assert len(relay.mailbox) == 1
    assert db.outbox[0]["status"] == "sent"
    assert db.outbox[1]["status"] == "pending"

    _tick(db, now=T0 + timedelta(minutes=5))
    assert len(relay.mailbox) == 2, "the untouched row must still be delivered"
    recipients = [m["Subject"] for m in relay.mailbox]
    assert len(recipients) == len(relay.mailbox)
    assert db.outbox[1]["status"] == "sent"

    for i in range(2, 5):
        _tick(db, now=T0 + timedelta(minutes=5 * i))
    assert len(relay.mailbox) == 2, "neither row may be delivered twice"


# ============================================================================ #
# The two in-process duplicate paths -- no process death required
# ============================================================================ #
def test_a_disconnect_during_data_is_not_retried_inside_one_send_call(estate):
    """``send()`` retries once on a transient failure. A disconnect DURING the body is
    transient-looking but is NOT proof of non-delivery, so retrying it inside a single
    ``send()`` call can deliver the same message twice with no crash anywhere.

    Modelled with the reality where the server DID commit before dropping.
    """
    db, relay = estate
    relay.fault = "accept_then_drop"

    mailer.send_alert(fire_event_id="fe1", to_email="reader@example.com",
                      payload=db.outbox[0]["payload"], lang="en", user_id="u1", attempt=0)

    assert len(relay.mailbox) == 1, (
        "one send() call delivered the message twice: the in-process retry crossed the "
        "transport boundary again after the server had already accepted it")


def test_b_quit_anomaly_after_acceptance_is_sent_not_failed(estate):
    """CPython's ``smtplib.SMTP.__exit__`` swallows ``SMTPServerDisconnected`` on QUIT
    but RE-RAISES ``SMTPResponseException`` on a non-221 reply -- after the server has
    already accepted the message. Treating that as a failure marks a delivered alert
    'failed', which the drain then retries under a fresh key: a guaranteed duplicate
    from a message that was never in doubt.
    """
    db, relay = estate
    relay.fault = "accept_then_quit_anomaly"

    status = mailer.send_alert(fire_event_id="fe1", to_email="reader@example.com",
                               payload=db.outbox[0]["payload"], lang="en",
                               user_id="u1", attempt=0)

    assert len(relay.mailbox) == 1
    assert status == "sent", (
        "the server accepted the message; a QUIT anomaly on the way out cannot "
        f"un-deliver it, but send() reported {status!r}")


# ============================================================================ #
# The acceptance criteria that must NOT regress
# ============================================================================ #
def test_genuine_known_failures_remain_retryable(estate):
    """Proof-of-non-delivery failures keep their retry. A refused recipient and a
    rejected body are both decided BEFORE/AT the server's verdict on the message, so
    the retry can never duplicate."""
    db, relay = estate
    relay.fault = "refuse_rcpt"

    _tick(db, now=T0)
    assert relay.mailbox == []
    assert db.outbox[0]["status"] == "failed"
    assert int(db.outbox[0]["attempts"]) == 1, "a known failure must consume an attempt"

    relay.fault = None
    _tick(db, now=T0 + timedelta(minutes=5))
    assert len(relay.mailbox) == 1, "a known-failed alert must be retried and delivered"
    assert db.outbox[0]["status"] == "sent"


def test_connect_failure_remains_retryable(estate):
    db, relay = estate
    relay.fault = "connect"

    _tick(db, now=T0)
    assert relay.mailbox == []

    relay.fault = None
    _tick(db, now=T0 + timedelta(minutes=5))
    assert len(relay.mailbox) == 1


def test_suppression_park_queued_stays_distinguishable_from_transport_uncertainty(estate):
    """A marketing suppression-lookup outage parks a row at ``email_log='queued'`` with
    ``detail='suppression_lookup_failed'``. That is PROVABLY pre-send and must keep its
    retry -- it must never be swept up by the effect-unknown quarantine, and the two
    must stay distinguishable in the durable record."""
    db, relay = estate
    key = "campaign:2026-09-18:reader@example.com"
    db.email_log[key] = {"idem_key": key, "status": "queued",
                         "detail": "suppression_lookup_failed"}

    assert drain.classify_ledger_queued(
        db.email_log[key]["detail"], now_utc=T0) == "pre_send"
    assert drain.classify_ledger_queued(
        f"{drain.SMTP_ATTEMPT_MARKER}@{(T0 - timedelta(hours=1)).isoformat()}",
        now_utc=T0) == "effect_unknown"


def test_in_flight_marker_within_grace_is_left_alone_not_quarantined(estate):
    """A marker younger than the grace window may belong to a LIVE writer -- a slow
    relay in the previous tick that has not returned yet. Quarantining it would strand
    a send that is still in progress; retrying it would double-send. Do neither."""
    db, relay = estate
    fresh = (T0 - timedelta(seconds=5)).isoformat()
    assert drain.classify_ledger_queued(
        f"{drain.SMTP_ATTEMPT_MARKER}@{fresh}", now_utc=T0) == "in_flight"

    key = mailer.alert_idem_key("fe1", attempt=0)
    db.email_log[key] = {"idem_key": key, "status": "queued",
                         "detail": f"{drain.SMTP_ATTEMPT_MARKER}@{fresh}"}
    before = dict(db.outbox[0])

    _tick(db, now=T0)

    assert relay.mailbox == [], "an in-flight send must not be duplicated"
    assert db.outbox[0]["status"] == before["status"] == "pending"
    assert int(db.outbox[0]["attempts"]) == int(before["attempts"] or 0), (
        "bumping attempts on an in-flight row mints a fresh key next tick -- the exact "
        "licence to double-send this boundary exists to withhold")


def test_in_flight_cannot_outlive_a_bounded_clock_skew():
    """A marker stamped in the FUTURE must not be 'fresh' forever.

    The mailer stamps the marker from the app host; this drain reads it from its own.
    Under a skewed clock a marker can sit younger-than-grace indefinitely -- never
    resent (safe) but never resolved and never surfaced, which is a silent livelock.
    Modest skew stays in-flight; implausible skew fails closed so a human sees it.
    """
    marker = drain.SMTP_ATTEMPT_MARKER

    modest = (T0 + timedelta(seconds=drain.MAX_CLOCK_SKEW_S // 2)).isoformat()
    assert drain.classify_ledger_queued(f"{marker}@{modest}", now_utc=T0) == "in_flight"

    absurd = (T0 + timedelta(seconds=drain.MAX_CLOCK_SKEW_S + 60)).isoformat()
    assert drain.classify_ledger_queued(f"{marker}@{absurd}", now_utc=T0) == drain.EFFECT_UNKNOWN

    # And the state always terminates: past grace + skew, every marker resolves.
    beyond = T0 + timedelta(seconds=drain.EFFECT_UNKNOWN_GRACE_S + drain.MAX_CLOCK_SKEW_S + 1)
    assert drain.classify_ledger_queued(
        f"{marker}@{T0.isoformat()}", now_utc=beyond) == drain.EFFECT_UNKNOWN


def test_naive_marker_timestamp_is_read_as_utc_not_as_local():
    """email_log.detail is free text, so a naive stamp is possible. It must be read as
    UTC -- guessing local time would shift the age by whole hours and could push an
    aged-out marker back inside the grace window."""
    naive = T0.replace(tzinfo=None).isoformat()
    assert drain.classify_ledger_queued(
        f"{drain.SMTP_ATTEMPT_MARKER}@{naive}", now_utc=T0) == "in_flight"
    assert drain.classify_ledger_queued(
        f"{drain.SMTP_ATTEMPT_MARKER}@{naive}",
        now_utc=T0 + timedelta(seconds=drain.EFFECT_UNKNOWN_GRACE_S + 1)) == drain.EFFECT_UNKNOWN


def test_malformed_marker_fails_closed_to_effect_unknown():
    """An unparseable marker timestamp is not an excuse to retry."""
    for detail in (drain.SMTP_ATTEMPT_MARKER,
                   f"{drain.SMTP_ATTEMPT_MARKER}@",
                   f"{drain.SMTP_ATTEMPT_MARKER}@not-a-timestamp"):
        assert drain.classify_ledger_queued(detail, now_utc=T0) == "effect_unknown", detail


def test_quarantine_is_bounded_and_leaves_the_retry_predicate(estate):
    """The quarantined row must drop out of the drain's own selection predicate, so the
    retry cap stays bounded and the row can never silently reappear."""
    db, relay = estate
    relay.fault = "accept_then_die"
    _tick(db, now=T0, expect_death=True)
    relay.fault = None

    _tick(db, now=T0 + timedelta(minutes=10))
    row = db.outbox[0]
    assert row["status"] == "failed"
    assert str(row["last_error"]) == "effect_unknown_after_smtp", (
        "the durable record must preserve the uncertainty, not relabel it as an "
        "ordinary failure")
    assert int(row["attempts"]) >= drain.ALERT_RETRY_ATTEMPTS_CAP
    path = ("alert_outbox?channel=eq.email&or=(status.eq.pending,"
            f"and(status.eq.failed,attempts.lt.{drain.ALERT_RETRY_ATTEMPTS_CAP}))")
    assert _selected(row, path) is False, "a quarantined row must never be re-selected"


def test_effect_unknown_is_never_reported_as_a_successful_run(estate):
    db, relay = estate
    relay.fault = "accept_then_die"
    _tick(db, now=T0, expect_death=True)
    relay.fault = None
    result = _tick(db, now=T0 + timedelta(minutes=10))
    assert result.outcome != "success"
    assert result.effect_unknown_n == 1
    assert result.fired_n == 0


def test_marker_constants_are_pinned_across_the_layering_seam():
    """``engine/`` may not import ``app/``, so the marker token is duplicated. A drift
    between the two silently turns every effect-unknown row back into a retryable one."""
    assert drain.SMTP_ATTEMPT_MARKER == mailer.SMTP_ATTEMPT_MARKER
    assert drain.EFFECT_UNKNOWN == mailer.EFFECT_UNKNOWN
    # The grace window must outlast the longest possible in-process transport.
    assert drain.EFFECT_UNKNOWN_GRACE_S > (
        mailer._SEND_ATTEMPTS * 6 * mailer._SMTP_TIMEOUT + mailer._RETRY_BACKOFF_SEC)


def test_engine_still_does_not_import_app():
    """The layering law this packet must not break."""
    src = (drain.__file__)
    with open(src, "r", encoding="utf-8") as fh:
        body = fh.read()
    assert "import app" not in body
    assert "from app" not in body


# ============================================================================ #
# Adversarial-review findings (2026-09-18). Each of these delivered the same
# logical alert twice, or lost one, before the fix named in its docstring.
# ============================================================================ #
def test_a_lost_insert_reply_does_not_disable_the_boundary(estate):
    """An alert INSERT that commits but loses its reply never crosses SMTP.

    The caller cannot distinguish this from a failure before commit.  Strict alert
    delivery therefore refuses both, and the bounded drain later retries under a fresh
    key.  The orphaned bare claim is safe because no transport was entered for it.
    """
    db, relay = estate
    key = mailer.alert_idem_key("fe1", attempt=0)
    real_pg = db.mailer_pg

    def insert_commits_then_loses_its_reply(method, path, body=None, prefer=None, timeout=6):
        if method == "POST" and path.startswith("email_log"):
            real_pg(method, path, body, prefer, timeout)      # it COMMITS ...
            raise RuntimeError("URLError: timed out")          # ... and the reply is lost
        return real_pg(method, path, body, prefer, timeout)

    import app.mailer as m
    m._pg = insert_commits_then_loses_its_reply
    try:
        _tick(db, now=T0)
    finally:
        m._pg = real_pg

    assert relay.sessions == []
    assert relay.mailbox == []
    assert drain.SMTP_ATTEMPT_MARKER not in str(db.email_log[key].get("detail") or "")

    for i in range(1, 5):
        _tick(db, now=T0 + timedelta(minutes=5 * i))
    assert len(relay.mailbox) == 1, "the provably-unsent alert must retry exactly once"
    assert db.outbox[0]["status"] == "sent"


def test_alert_insert_failure_before_commit_never_crosses_smtp_and_is_bounded(estate):
    db, relay = estate
    real_pg = db.mailer_pg

    def fail_before_commit(method, path, body=None, prefer=None, timeout=6):
        if method == "POST" and path.startswith("email_log"):
            raise RuntimeError("database unavailable before commit")
        return real_pg(method, path, body, prefer, timeout)

    mailer._pg = fail_before_commit
    try:
        _tick(db, now=T0)
    finally:
        mailer._pg = real_pg

    assert db.email_log == {}
    assert relay.sessions == [] and relay.mailbox == []
    assert db.outbox[0]["status"] == "failed"
    assert db.outbox[0]["attempts"] == 1

    _tick(db, now=T0 + timedelta(minutes=5))
    assert len(relay.mailbox) == 1
    assert db.outbox[0]["status"] == "sent"


def test_alert_marker_patch_zero_matches_never_crosses_smtp(estate):
    db, relay = estate
    real_pg = db.mailer_pg

    def marker_matches_zero(method, path, body=None, prefer=None, timeout=6):
        if (method == "PATCH" and path.startswith("email_log")
                and (body or {}).get("status") == "queued"):
            assert prefer == "return=representation"
            return []
        return real_pg(method, path, body, prefer, timeout)

    mailer._pg = marker_matches_zero
    try:
        _tick(db, now=T0)
    finally:
        mailer._pg = real_pg

    assert relay.sessions == ["smtp.example.com:587"]  # marker follows connect/AUTH
    assert relay.mailbox == [], "zero matched marker rows must stop before SMTP DATA"
    assert db.outbox[0]["status"] == "failed"
    assert db.outbox[0]["attempts"] == 1

    _tick(db, now=T0 + timedelta(minutes=5))
    assert len(relay.mailbox) == 1
    assert db.outbox[0]["status"] == "sent"


def test_b_quit_anomaly_cannot_destroy_an_in_flight_uncertainty(estate):
    """MAJOR: Python replaces a propagating exception with whatever `__exit__` raises,
    and smtplib's `__exit__` raises SMTPResponseException on a non-221 QUIT. Since that
    subclasses OSError it lands in `_TRANSIENT` -- so an unrecorded TransportUncertain
    would be slept on and RETRIED, re-entering DATA for a message already committed.
    """
    db, relay = estate
    relay.fault = "accept_then_uncertain_then_quit_anomaly"

    status = mailer.send_alert(fire_event_id="fe1", to_email="reader@example.com",
                               payload=db.outbox[0]["payload"], lang="en",
                               user_id="u1", attempt=0)

    assert len(relay.mailbox) == 1, (
        "the uncertainty was destroyed by the QUIT anomaly and the message was "
        f"re-sent in-process: mailbox={len(relay.mailbox)}")
    assert status == mailer.EFFECT_UNKNOWN, (
        f"uncertainty must outrank teardown noise, got {status!r}")


def test_c_unparsed_reply_to_the_terminating_dot_is_not_a_refusal(estate):
    """MAJOR: `SMTPDataError(-1, ...)` means the reply to the terminating '.' did not
    PARSE -- not that the server said no. The relay may have committed. Treating it as
    a refusal marks a delivered alert 'failed', which the drain retries under a fresh
    key: a guaranteed duplicate.
    """
    db, relay = estate
    relay.fault = "unparsed_data_reply"

    _tick(db, now=T0)
    assert len(relay.mailbox) == 1, "precondition: the relay committed it"
    relay.fault = None

    for i in range(1, 6):
        _tick(db, now=T0 + timedelta(minutes=5 * i))
    assert len(relay.mailbox) == 1, (
        "an unparsed final reply was treated as proof of non-delivery and the message "
        "was sent again")
    assert db.outbox[0]["status"] == "failed"
    assert db.outbox[0]["last_error"] == drain.EFFECT_UNKNOWN_LAST_ERROR


def test_d_a_parsed_rejection_is_still_a_refusal_and_stays_retryable(estate):
    """The other side of the same line: a REAL non-2xx code is an explicit 'no', and
    must keep its retry rather than being quarantined as unknowable."""
    db, relay = estate
    relay.fault = "reject_data"

    _tick(db, now=T0)
    assert relay.mailbox == []
    assert db.outbox[0]["status"] == "failed"
    assert db.outbox[0]["last_error"] != drain.EFFECT_UNKNOWN_LAST_ERROR

    relay.fault = None
    for i in range(1, 3):
        _tick(db, now=T0 + timedelta(minutes=5 * i))
    assert len(relay.mailbox) == 1, "a genuine rejection must stay retryable"


def test_e_session_lost_during_the_marker_write_is_retryable_not_quarantined(estate):
    """MAJOR: the marker's own round trip leaves the SMTP session idle, so the relay
    may drop it. That drop surfaces from inside sendmail()'s MAIL FROM -- before RCPT,
    before DATA, with zero body bytes on the wire -- and is provably not delivered.
    Quarantining it would lose an alert that certainly never went out, and the design's
    own choice to do an HTTP round trip inside the session makes it MORE likely.
    """
    db, relay = estate
    relay.fault = "drop_after_marker"

    _tick(db, now=T0)
    assert relay.mailbox == []
    assert db.outbox[0]["last_error"] != drain.EFFECT_UNKNOWN_LAST_ERROR, (
        "a pre-body session drop is provably not delivered -- it must not be "
        "quarantined as effect-unknown")

    relay.fault = None
    for i in range(1, 4):
        _tick(db, now=T0 + timedelta(minutes=5 * i))
    assert len(relay.mailbox) == 1, "and it must still be delivered"


def test_f_overlapping_drain_ticks_do_not_duplicate_a_fresh_claim(estate):
    """MAJOR: the outbox row stays 'pending' with `attempts` unchanged for the WHOLE
    duration of send_fn, and nothing leases it. A second tick that resolves the first
    tick's fresh, not-yet-marked claim as an abandoned pre-send bumps `attempts` and
    mints a fresh key for a send still under way -- a duplicate needing no crash.

    `email_log.created_at` is the claim time, so a claim younger than the grace window
    is a live writer, not an abandonment.
    """
    db, relay = estate
    key = mailer.alert_idem_key("fe1", attempt=0)

    # Tick A has claimed the row and is inside connect/AUTH -- no marker yet.
    db.email_log[key] = {"idem_key": key, "status": "queued", "detail": None,
                         "created_at": (T0 - timedelta(seconds=3)).isoformat()}
    assert drain.classify_ledger_queued(
        None, now_utc=T0, created_at=db.email_log[key]["created_at"]) == "in_flight"

    before = dict(db.outbox[0])
    _tick(db, now=T0)                       # tick B, overlapping

    assert relay.mailbox == [], "tick B must not send over a live tick A"
    assert int(db.outbox[0]["attempts"]) == int(before["attempts"] or 0), (
        "bumping attempts here mints a fresh key next tick -- the duplicate licence")

    # An ABANDONED bare claim, however, is still retryable once it ages out.
    assert drain.classify_ledger_queued(
        None, now_utc=T0,
        created_at=(T0 - timedelta(seconds=drain.EFFECT_UNKNOWN_GRACE_S + 60)).isoformat()
    ) == "pre_send"
    # and an unreadable/absent created_at keeps the original behaviour.
    assert drain.classify_ledger_queued(None, now_utc=T0) == "pre_send"
