"""Hermetic contracts. Fake owner models an ATOMIC secure Supabase consent port."""
import json
import hmac
import secrets
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from engine.marketing.catalyst_lifecycle import (
    Confirmation, ConsentRecord, FunnelGate, FunnelService, PublicRevision, ScanEvidence,
    SCOPE, VerifiedIdentity, analytics_receipt, first_touch, format_revision,
)

NOW = datetime(2026, 10, 9, 3, 0, tzinfo=timezone.utc)
UID = "9507e687-116a-4d30-9c30-fdf45c9d91b2"
EMAIL = "investor+events@example.com"
SECRET = "s" * 40


class Scan:
    def require_public_scan(self, receipt):
        if receipt != "scan-public-verified":
            raise FunnelGate("SCAN_PROOF_REQUIRED", 400)
        return ScanEvidence("event-123", ("NVDA", "AMD"), "2026-10-08T10:00:00+00:00", True)


class Otp:
    def __init__(self):
        self.requests = []
        self.checks = []
        self.fail = False

    def request_otp(self, email):
        self.requests.append(email)
        return not self.fail

    def verify_otp(self, email, code):
        self.checks.append((email, code))
        if code != "123456":
            raise FunnelGate("IDENTITY_UNVERIFIED", 403)
        return VerifiedIdentity(UID, email, NOW.isoformat())


class Store:
    def __init__(self):
        self.records = {}
        self.by_nonce = {}
        self.pending = {}
        self.ready = True
        self.raise_on_confirm = False

    def available(self):
        return self.ready

    def begin_pending_intent(self, intent, email_tag, expires_at_utc):
        ref = "opaque_" + secrets.token_urlsafe(20)
        self.pending[ref] = (intent, email_tag, expires_at_utc)
        return ref

    def resolve_pending_intent(self, public_ref, email_tag):
        row = self.pending.get(public_ref)
        if not row or not hmac.compare_digest(row[1], email_tag):
            raise FunnelGate("INVALID_VERIFICATION_INTENT", 400)
        return row[0]

    def confirm(self, rec):
        if self.raise_on_confirm:
            raise RuntimeError("db offline with secret personally identifiable data")
        key = (rec.user_id, rec.event_id)
        orig = self.records.get(key)
        if orig:
            if orig.revoked_at_utc:  # never reactivate by replay
                raise FunnelGate("CONSENT_REVOKED", 403)
            return Confirmation(orig, False)
        if rec.intent_id in self.by_nonce:
            raise FunnelGate("CONSENT_REPLAY", 403)
        self.records[key] = rec
        self.by_nonce[rec.intent_id] = key
        return Confirmation(rec, True)

    def interested(self, event_id, limit):
        return [r for r in self.records.values() if r.event_id == event_id][:limit]

    def current(self, user_id, event_id):
        return self.records.get((user_id, event_id))

    def revoke(self, user_id, event_id, at_utc):
        k = (user_id, event_id)
        if k not in self.records or self.records[k].revoked_at_utc:
            return False
        self.records[k] = replace(self.records[k], revoked_at_utc=at_utc)
        return True


class Suppression:
    def __init__(self):
        self.blocked = False
        self.down = False

    def is_suppressed(self, email, user_id):
        if self.down:
            raise ConnectionError("owner down")
        return self.blocked


class Revisions:
    def __init__(self):
        self.generation = 2

    def is_current(self, event_id, generation):
        return event_id == "event-123" and generation == self.generation


class Sender:
    def __init__(self):
        self.ready = True
        self.status = "sent"
        self.calls = []

    def permitted(self):
        return self.ready

    def deliver(self, record, revision, key):
        self.calls.append((record.user_id, revision.generation, key))
        return self.status


def make():
    otp, store, suppression, revision, sender = Otp(), Store(), Suppression(), Revisions(), Sender()
    service = FunnelService(secret=SECRET, scan=Scan(), identity=otp, consent=store,
                            suppression=suppression, revisions=revision, sender=sender)
    return service, otp, store, suppression, revision, sender


def consented(service, email=EMAIL, touch=None, now=NOW):
    return service.request(email=email, checked=True, scan_receipt="scan-public-verified",
                           touch=touch or {"partner_id": "partner-A", "utm_source": "letter"}, now=now)


def verified(service, touch=None):
    intent = consented(service, touch=touch)
    return service.verify(email=EMAIL, otp="123456", public_ref=intent["public_ref"], now=NOW)


def update(**kwargs):
    values = dict(event_id="event-123", generation=2, as_of_utc="2026-10-09T04:00:00+00:00",
                  published_at_utc="2026-10-09T03:00:00+00:00", ticker="NVDA",
                  headline="Company updates outlook", what_changed="Management revised guidance.",
                  source_urls=("https://www.sec.gov/Archives/edgar/example",),
                  material=True, public_safe=True, external_rights_confirmed=True,
                  operator_approved=True)
    values.update(kwargs)
    return PublicRevision(**values)


def fails(code, fn):
    with pytest.raises(FunnelGate) as e:
        fn()
    assert e.value.code == code


def test_anonymous_first_scan_stays_separate_from_registration():
    service, otp, store, *_ = make()
    scan = service.scan.require_public_scan("scan-public-verified")
    assert scan.public_safe and scan.event_id == "event-123"
    assert not otp.requests and not store.records  # first value available without signup
    fails("EXPLICIT_CONSENT_REQUIRED", lambda: service.request(
        email=EMAIL, checked=False, scan_receipt="scan-public-verified", touch={}, now=NOW))
    assert not otp.requests


def test_invalid_address_and_unverified_never_becomes_a_lead():
    service, otp, store, *_ = make()
    for bad in ("bad", "a@b", "a@b.com\nBcc:other@example.com", "x" * 256 + "@e.com"):
        fails("INVALID_EMAIL", lambda: service.request(
            email=bad, checked=True, scan_receipt="scan-public-verified", touch={}, now=NOW))
    token = consented(service)["public_ref"]
    assert store.records == {}
    fails("IDENTITY_UNVERIFIED", lambda: service.verify(email=EMAIL, otp="000000", public_ref=token, now=NOW))
    assert store.records == {}


def test_signed_intent_binds_email_time_scope_and_attribution_without_email_leak():
    service, _, store, *_ = make()
    req = consented(service, touch={"utm_source": "letter", "utm_campaign": "earnings",
                                           "utm_content": "post01", "partner_id": "partner-A"})
    token = req["public_ref"]
    assert EMAIL not in token and EMAIL not in str(req)
    assert req["status"] == "verification_requested"
    fails("INVALID_VERIFICATION_INTENT", lambda: service.verify(email="other@example.com", otp="123456", public_ref=token, now=NOW))
    fails("INVALID_VERIFICATION_INTENT", lambda: service.verify(email=EMAIL, otp="123456", public_ref=token[:-2] + "AA", now=NOW))
    fails("EXPIRED_VERIFICATION_INTENT", lambda: service.verify(email=EMAIL, otp="123456", public_ref=token, now=NOW + timedelta(minutes=21)))
    assert service.verify(email=EMAIL, otp="123456", public_ref=token, now=NOW)["status"] == "verified"
    row = next(iter(store.records.values()))
    assert row.scope == SCOPE and row.first_touch["partner_id"] == "partner-A"
    assert row.verified_at_utc and row.intent_id
    safe = analytics_receipt(row)
    assert safe["user_ref"].startswith("u_") and EMAIL not in json.dumps(safe)
    assert UID not in json.dumps(safe) and "intent" not in safe
    assert safe["utm_campaign"] == "earnings"


def test_duplicate_verification_is_idempotent_and_immutable_first_touch():
    service, *_ = make()
    first = consented(service, touch={"partner_id": "partner-A"})
    assert service.verify(email=EMAIL, otp="123456", public_ref=first["public_ref"], now=NOW)["status"] == "verified"
    assert service.verify(email=EMAIL, otp="123456", public_ref=first["public_ref"], now=NOW)["status"] == "already_verified"
    later = consented(service, touch={"partner_id": "partner-B"})
    assert service.verify(email=EMAIL, otp="123456", public_ref=later["public_ref"], now=NOW)["status"] == "already_verified"
    assert service.consent.current(UID, "event-123").first_touch == {"partner_id": "partner-A"}


def test_secure_owner_down_does_not_consume_otp_or_forge_success():
    service, otp, store, *_ = make()
    store.ready = False
    fails("CONSENT_OWNER_NOT_READY", lambda: consented(service))
    assert otp.requests == []
    store.ready = True
    intent = consented(service)["public_ref"]
    store.ready = False
    fails("CONSENT_OWNER_NOT_READY", lambda: service.verify(email=EMAIL, otp="123456", public_ref=intent, now=NOW))
    assert otp.checks == []
    store.ready = True
    store.raise_on_confirm = True
    fails("CONSENT_WRITE_UNCONFIRMED", lambda: service.verify(email=EMAIL, otp="123456", public_ref=intent, now=NOW))


def test_suppressed_or_unavailable_suppression_refuses_grant():
    service, otp, _, suppression, *_ = make()
    token = consented(service)["public_ref"]
    suppression.blocked = True
    fails("ADDRESS_SUPPRESSED", lambda: service.verify(email=EMAIL, otp="123456", public_ref=token, now=NOW))
    suppression.blocked = False
    suppression.down = True
    fails("SUPPRESSION_CHECK_UNAVAILABLE", lambda: service.verify(email=EMAIL, otp="123456", public_ref=token, now=NOW))


def test_optout_prevents_delivery_and_old_code_cannot_reactivate():
    service, _, store, _, _, sender = make()
    token = consented(service)["public_ref"]
    verified(service)  # same event, different request
    assert service.revoke(user_id=UID, event_id="event-123", now=NOW)["status"] == "unsubscribed"
    assert service.revoke(user_id=UID, event_id="event-123", now=NOW)["changed"] == "no"
    fails("CONSENT_REVOKED", lambda: service.verify(email=EMAIL, otp="123456", public_ref=token, now=NOW))
    out = service.deliver(update(), now=NOW + timedelta(hours=1))
    assert out[0]["state"] == "SUPPRESSED" and sender.calls == []


def test_sender_preflight_unverified_no_send_outdated_no_send_and_marketing_suppression():
    service, _, store, suppression, revision, sender = make()
    assert service.deliver(update(), now=NOW + timedelta(hours=2)) == []  # no verified leads
    verified(service)
    sender.ready = False
    fails("SEND_BLOCKED", lambda: service.deliver(update(), now=NOW + timedelta(hours=2)))
    assert not sender.calls
    sender.ready = True
    revision.generation = 3
    fails("OUTDATED_OR_UNVERIFIED_REVISION", lambda: service.deliver(update(), now=NOW + timedelta(hours=2)))
    revision.generation = 2
    suppression.blocked = True
    assert service.deliver(update(), now=NOW + timedelta(hours=2))[0]["state"] == "SUPPRESSED"
    assert not sender.calls


def test_second_value_requires_new_evidence_and_source_rights_and_correct_ticker():
    service, _, store, _, _, sender = make()
    verified(service)
    for rev in (update(public_safe=False), update(external_rights_confirmed=False),
                update(operator_approved=False), update(material=False)):
        fails("REVISION_NOT_APPROVED", lambda: service.deliver(rev, now=NOW))
    fails("SOURCE_RIGHTS_UNPROVEN", lambda: service.deliver(update(source_urls=("http://private",)), now=NOW))
    fails("SOURCE_RIGHTS_UNPROVEN", lambda: service.deliver(update(source_urls=("https://127.0.0.1/report",)), now=NOW))
    fails("INVALID_REVISION", lambda: service.deliver(update(generation=0), now=NOW))
    out = service.deliver(update(as_of_utc=NOW.isoformat()), now=NOW)
    assert out[0]["state"] == "NOT_SECOND_VALUE" and not sender.calls


def test_send_receipt_idempotency_and_uncertainty_not_claimed_success():
    service, *_parts, sender = make()
    verified(service)
    assert service.deliver(update(), now=NOW + timedelta(hours=2))[0]["state"] == "PROVIDER_ACCEPTED"
    assert sender.calls[0][2] == "catalyst:event-123:2:NVDA:" + UID
    for state, label in (("duplicate", "ALREADY_CLAIMED"), ("failed", "SEND_FAILED"),
                         ("queued", "QUEUED_NOT_SENT"), ("effect_unknown", "EFFECT_UNKNOWN"),
                         ("skipped_no_smtp", "SEND_BLOCKED")):
        sender.status = state
        assert service.deliver(update(), now=NOW + timedelta(hours=2))[0]["state"] == label
    assert len(set(x[2] for x in sender.calls)) == 1  # same canonical sender ledger key


def test_same_event_different_ticker_delivery_keys_do_not_collide():
    service, *_rest, sender = make()
    verified(service)
    assert service.deliver(update(ticker="NVDA"), now=NOW + timedelta(hours=2))[0]["state"] == "PROVIDER_ACCEPTED"
    assert service.deliver(update(ticker="AMD"), now=NOW + timedelta(hours=2))[0]["state"] == "PROVIDER_ACCEPTED"
    first_key, second_key = sender.calls[0][2], sender.calls[1][2]
    assert first_key == "catalyst:event-123:2:NVDA:" + UID
    assert second_key == "catalyst:event-123:2:AMD:" + UID
    assert first_key != second_key
    service.deliver(update(ticker="AMD"), now=NOW + timedelta(hours=2))
    assert sender.calls[2][2] == second_key


@pytest.mark.parametrize("elapsed_days", [8, 30, 90])
def test_stale_public_revision_is_never_sent_even_when_generation_is_current(elapsed_days):
    service, _, _, _, revisions, sender = make()
    verified(service)
    assert revisions.is_current("event-123", 2) is True
    fails("STALE_SOURCE_REVISION", lambda: service.deliver(update(), now=NOW + timedelta(days=elapsed_days)))
    assert sender.calls == []


def test_revision_freshness_boundary_matches_public_scan_ceiling():
    service, *_rest, sender = make()
    verified(service)
    at_ceiling = datetime.fromisoformat(update().as_of_utc) + timedelta(days=7)
    assert service.deliver(update(), now=at_ceiling)[0]["state"] == "PROVIDER_ACCEPTED"
    assert len(sender.calls) == 1


def test_correction_and_retraction_print_latest_and_never_recycle_old_claims():
    retraction = update(correction="retracted", correction_note="Original projection withdrawn.",
                        what_changed="OUTDATED AND WRONG guidance")
    subject, body, txt = format_revision(retraction, "https://mastermind-x.com/unsubscribe.html?t=token")
    assert "Correction" in subject and "Original projection withdrawn" in txt
    assert "OUTDATED AND WRONG" not in txt and "OUTDATED AND WRONG" not in body
    corrected = update(correction="corrected", correction_note="Earlier publication misstated units.",
                       what_changed="New approved units")
    assert "Earlier publication misstated units" in format_revision(corrected, "https://mastermind-x.com/unsubscribe.html")[2]
    fails("CORRECTION_NOTE_REQUIRED", lambda: format_revision(update(correction="corrected"), "https://mastermind-x.com/u"))


def test_user_input_html_escaped_and_never_enters_headers_as_multiline():
    hostile = update(what_changed="<script>alert(1)</script>")
    _, body, _ = format_revision(hostile, "https://mastermind-x.com/unsubscribe.html")
    assert "<script>" not in body and "&lt;script&gt;" in body
    fails("INVALID_REVISION", lambda: format_revision(update(headline="hi\nBcc: evasion"), "https://mastermind-x.com"))


@pytest.mark.parametrize("source_url", [
    "https://www.sec.gov/Archives/edgar/example?email=reader%40example.com",
    "https://www.sec.gov/Archives/edgar/example?key=reader%2540example.com",
    "https://www.sec.gov/Archives/edgar/example#session=private-session",
    "https://www.sec.gov/Archives/edgar/example?api%5Fkey=restricted",
    "https://www.sec.gov/Archives/edgar/example?access_token=credential",
    "https://www.sec.gov:8443/Archives/edgar/example",
    "https://www.sec.gov/Archives/edgar/example?note=%0aBcc:bad",
])
def test_followup_links_never_expose_identity_credentials_or_headers(source_url):
    fails("SOURCE_RIGHTS_UNPROVEN", lambda: format_revision(
        update(source_urls=(source_url,)),
        "https://www.mastermind-x.com/unsubscribe.html"))


def test_source_provenance_links_with_public_accession_parameters_remain_valid():
    link = "https://www.sec.gov/Archives/edgar/data/123/filing.htm?accession=000123&view=public"
    subject, html, plain = format_revision(
        update(source_urls=(link,)),
        "https://www.mastermind-x.com/unsubscribe.html")
    assert link in html and link in plain
    assert subject.startswith("Update:")


def test_attribution_strictly_allows_only_non_pii_tagged_first_touch():
    assert first_touch({"utm_source": "letter", "evil_email": EMAIL}) == {"utm_source": "letter"}
    fails("INVALID_ATTRIBUTION", lambda: first_touch({"partner_id": EMAIL}))
    fails("INVALID_ATTRIBUTION", lambda: first_touch({"utm_medium": "utm value containing spaces"}))
    fails("INVALID_ATTRIBUTION", lambda: first_touch({"partner_id": "203.0.113.5"}))


def test_future_source_and_wrong_ticker_are_not_delivered():
    service, *_rest, sender = make()
    verified(service)
    fails("FUTURE_SOURCE_REVISION", lambda: service.deliver(update(), now=NOW))
    assert not sender.calls
    result = service.deliver(update(ticker="TSLA"), now=NOW + timedelta(hours=2))
    assert result[0]["state"] == "SUPPRESSED" and not sender.calls


def test_delivery_receipts_keep_first_touch_without_email_or_user_identity():
    service, *_rest, sender = make()
    req = consented(service, touch={"partner_id": "partnerA", "utm_source": "newsletter"})
    service.verify(email=EMAIL, otp="123456", public_ref=req["public_ref"], now=NOW)
    out = service.deliver(update(), now=NOW + timedelta(hours=2))[0]
    assert out["state"] == "PROVIDER_ACCEPTED" and out["partner_id"] == "partnerA"
    assert out["utm_source"] == "newsletter" and EMAIL not in json.dumps(out)
    assert UID not in json.dumps(out)
