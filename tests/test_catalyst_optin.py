"""HTTP integration seam and existing authoritative sender/OTP adapters."""
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import catalyst_optin
from engine.marketing.catalyst_lifecycle import PublicRevision, FunnelGate, VerifiedIdentity

UID = "9507e687-116a-4d30-9c30-fdf45c9d91b2"


class Service:
    def __init__(self):
        self.requests = []
        self.verifies = []

    def request(self, **kw):
        self.requests.append(kw)
        return {"status": "verification_requested", "scope": "catalyst_material_event_updates_v1"}

    def verify(self, **kw):
        self.verifies.append(kw)
        return {"status": "verified"}


@pytest.fixture
def web(monkeypatch):
    svc = Service()
    catalyst_optin.configure(svc)
    monkeypatch.setattr(catalyst_optin, "_abuse_guard", lambda req: None)
    app = FastAPI()
    app.include_router(catalyst_optin.router)
    yield TestClient(app), svc
    catalyst_optin.configure(None)


def test_optin_does_not_wall_first_scan_and_requires_checked_scope(web):
    client, service = web
    assert client.get("/api/catalyst/optin/request").status_code == 405
    data = {"email": "investor@example.com", "scan_receipt": "signed", "scope": "catalyst_material_event_updates_v1",
            "consent_checked": True, "form_elapsed_ms": 4000, "first_touch": {"partner_id": "A"}}
    assert client.post("/api/catalyst/optin/request", json=data).json()["status"] == "verification_requested"
    assert len(service.requests) == 1
    data["consent_checked"] = False
    assert client.post("/api/catalyst/optin/request", json=data).status_code == 200  # service decides and rejects; fake only tests routing
    data["scope"] = "all_marketing"
    assert client.post("/api/catalyst/optin/request", json=data).status_code == 400


def test_bots_rejected_before_identity_or_lead_owner(web):
    client, service = web
    d = {"email": "investor@example.com", "scan_receipt": "signed", "consent_checked": True,
         "form_elapsed_ms": 200, "honeypot": ""}
    assert client.post("/api/catalyst/optin/request", json=d).status_code == 400
    d["form_elapsed_ms"] = 4000
    d["honeypot"] = "Filled"
    assert client.post("/api/catalyst/optin/request", json=d).status_code == 400
    assert not service.requests


def test_verify_requires_post_valid_otp_and_safe_unconfigured_gate(web):
    client, service = web
    assert client.post("/api/catalyst/optin/verify", json={
        "email": "investor@example.com", "otp": "123456", "intent": "signed"}).json()["status"] == "verified"
    assert len(service.verifies) == 1
    catalyst_optin.configure(None)
    assert client.post("/api/catalyst/optin/verify", json={
        "email": "investor@example.com", "otp": "123456", "intent": "signed"}).json()["detail"] == "CATALYST_INTEGRATION_NOT_READY"


def test_otp_adapter_verifies_real_gotrue_response_not_just_request_acceptance():
    calls = []
    def transport(path, value):
        calls.append((path, value))
        if path == "/auth/v1/otp":
            return {}
        return {"user": {"id": UID, "email": "INVESTOR@example.com",
                         "email_confirmed_at": "2026-10-09T03:00:00+00:00"}}
    authority = catalyst_optin.SupabaseOtpIdentity(endpoint="https://auth.example.com", anon_key="public", transport=transport)
    assert authority.request_otp("investor@example.com") is True
    got = authority.verify_otp("investor@example.com", "123456")
    assert got.user_id == UID and got.email.lower() == "investor@example.com"
    assert calls[0][0] == "/auth/v1/otp" and calls[1][0] == "/auth/v1/verify"
    assert calls[1][1]["type"] == "email"


def test_otp_unconfigured_or_unconfirmed_never_marked_verified():
    gate = catalyst_optin.SupabaseOtpIdentity(endpoint="https://auth.example.com", anon_key="")
    with pytest.raises(FunnelGate) as e:
        gate.request_otp("test@example.com")
    assert e.value.code == "IDENTITY_VERIFICATION_UNAVAILABLE"
    bad = catalyst_optin.SupabaseOtpIdentity(endpoint="https://auth.example.com", anon_key="public",
                                            transport=lambda path, data: {"user": {"email": data["email"], "id": UID}})
    with pytest.raises(FunnelGate) as e:
        bad.verify_otp("test@example.com", "123456")
    assert e.value.code == "IDENTITY_UNVERIFIED"


class FakeMailer:
    def __init__(self):
        self.calls = []
        self.configured = True
        self.suppressed = False

    def is_configured(self):
        return self.configured

    def unsub_token(self, identity):
        return "signed-by-existing-mailer"

    def _suppression_reason(self, email, uid):
        return "unsubscribe" if self.suppressed else None

    def send(self, **data):
        self.calls.append(data)
        return "sent"


class FakeMarketing:
    @staticmethod
    def unsub_page_url(uid):
        return "https://mastermind-x.com/unsubscribe.html?t=canonical"

    @staticmethod
    def unsub_api_url(uid):
        return "https://mastermind-x.com/api/email/unsubscribe?t=canonical"


def test_canonical_mailer_used_marketing_with_strict_ledger_and_one_click():
    mailer = FakeMailer()
    sender = catalyst_optin.ExistingMailerDelivery(mailer, FakeMarketing(), enabled=lambda: True)
    assert sender.permitted()
    from engine.marketing.catalyst_lifecycle import ConsentRecord
    record = ConsentRecord(UID, "investor@example.com", "event-123", ("NVDA",),
                           "catalyst_material_event_updates_v1", "2026-10-09T02:00:00+00:00", "nonce",
                           {"partner_id": "A"})
    revision = PublicRevision("event-123", 1, "2026-10-09T03:00:00+00:00",
                              "2026-10-09T02:00:00+00:00", "NVDA", "Material update", "Guidance changed",
                              ("https://www.sec.gov/",), True, True, True, True)
    assert sender.deliver(record, revision, "catalyst:event-123:1:" + UID) == "sent"
    sent = mailer.calls[0]
    assert sent["cls"] == "marketing" and sent["strict_ledger"] is True
    assert sent["user_id"] == UID and sent["headers"]["unsubscribe_url"].endswith("canonical")
    mailer.configured = False
    assert not sender.permitted()
    assert sender.deliver(record, revision, "next") == "skipped_no_smtp"
    assert len(mailer.calls) == 1  # not even a failed ledger claim; won't burn idem key


def test_live_mailer_fail_closed_on_exceptions_not_fake_success():
    mailer = FakeMailer()
    mailer.send = lambda **kw: (_ for _ in ()).throw(RuntimeError("unknown delivery effect"))
    sender = catalyst_optin.ExistingMailerDelivery(mailer, FakeMarketing(), enabled=lambda: True)
    from engine.marketing.catalyst_lifecycle import ConsentRecord
    record = ConsentRecord(UID, "investor@example.com", "event-123", ("NVDA",),
                           "catalyst_material_event_updates_v1", "2026-10-09T02:00:00+00:00", "nonce", {})
    revision = PublicRevision("event-123", 1, "2026-10-09T03:00:00+00:00",
                              "2026-10-09T02:00:00+00:00", "NVDA", "Material update", "Changed",
                              ("https://www.sec.gov/",), True, True, True, True)
    assert sender.deliver(record, revision, "same-key") == "effect_unknown"


def test_unwired_durable_consent_port_fails_closed():
    port = catalyst_optin.UnwiredConsentOwner()
    assert port.available() is False
    with pytest.raises(FunnelGate) as e:
        port.confirm(object())
    assert e.value.code == "CONSENT_OWNER_NOT_READY"


def test_supabase_consent_owner_rpc_contract_and_first_touch_are_exact():
    from engine.marketing.catalyst_lifecycle import ConsentRecord, SCOPE
    record = ConsentRecord(UID, "investor@example.com", "event-123", ("NVDA",),
                           SCOPE, "2026-10-09T03:00:00+00:00", "nonce-A", {"partner_id": "partnerA"})
    row = dict(record.__dict__)
    calls = []

    def pg(method, path, body):
        calls.append((method, path, body))
        if path.endswith("contract"):
            return {"owner": "email_consent", "version": 1}
        if path.endswith("confirm"):
            return {"created": True, "record": row}
        if path.endswith("current"):
            return row
        if path.endswith("interested"):
            return [row]
        if path.endswith("revoke"):
            return {"changed": True}
        raise AssertionError(path)

    owner = catalyst_optin.SupabaseConsentRpcOwner(pg=pg)
    assert owner.available()
    assert owner.confirm(record).record.first_touch == {"partner_id": "partnerA"}
    assert owner.current(UID, "event-123") == record
    assert owner.interested("event-123", 1) == [record]
    assert owner.revoke(UID, "event-123", "2026-10-09T06:00:00+00:00")
    payload = next(c[2] for c in calls if c[1].endswith("confirm"))
    assert payload["p_first_touch"] == {"partner_id": "partnerA"}
    assert "email" not in str(payload).lower() and "investor@example.com" not in str(payload)
    assert all(m == "POST" and path.startswith("rpc/catalyst_consent_") for m, path, _ in calls)


def test_consent_rpc_missing_owner_version_bad_reply_or_leaky_email_is_fail_closed():
    owner = catalyst_optin.SupabaseConsentRpcOwner(pg=lambda method, path, body: {"owner": "email_consent", "version": 2})
    assert owner.available() is False
    owner = catalyst_optin.SupabaseConsentRpcOwner(pg=lambda method, path, body: None)
    assert owner.available() is False
    from engine.marketing.catalyst_lifecycle import ConsentRecord, SCOPE
    rec = ConsentRecord(UID, "investor@example.com", "event-123", ("NVDA",), SCOPE,
                        "2026-10-09T03:00:00+00:00", "nonce", {})
    owner = catalyst_optin.SupabaseConsentRpcOwner(pg=lambda method, path, body: {"created": True, "record": {
        "user_id": UID, "email": "other@example.com", "event_id": "event-123", "tickers": ["NVDA"],
        "scope": SCOPE, "verified_at_utc": rec.verified_at_utc, "intent_id": "nonce", "first_touch": {}}})
    with pytest.raises(FunnelGate) as error:
        owner.confirm(rec)
    assert error.value.code == "CONSENT_OWNER_PROTOCOL_MISMATCH"


def test_first_value_router_and_consent_check_are_separate(web):
    client, svc = web
    # Neither opt-in route accepts scan input or requires an auth session; the
    # first actual public scan is owned by the independent scan service/UI.
    assert client.get("/api/catalyst/scan").status_code == 404
    result = client.post("/api/catalyst/optin/request", json={
        "email": "investor@example.com", "scan_receipt": "valid", "consent_checked": False,
        "form_elapsed_ms": 3000}).json()
    assert result["status"] == "verification_requested"  # fake HTTP fixture only
    assert svc.requests[0]["checked"] is False
