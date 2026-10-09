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
        return {"status": "verification_requested", "public_ref": "opaque_testref_1234"}

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


def test_optin_request_is_disabled_until_admitted_and_requires_explicit_scan_proof(web, monkeypatch):
    client, service = web
    receipt = "signed.public-scan-receipt-" + "x" * 64
    data = {"email": "investor@example.com", "scan_receipt": receipt,
            "consent_checked": True, "scope": catalyst_optin.SCOPE,
            "first_touch": {"utm_content": "post-02", "utm_medium": "partner-1"},
            "form_elapsed_ms": 4000}
    # Registered but always inert unless BOTH public and opt-in feature gates pass.
    assert client.post("/api/catalyst/optin/request", json=data).status_code == 503
    assert service.requests == []
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setenv("CATALYST_OPTIN_ENABLED", "1")
    reply = client.post("/api/catalyst/optin/request", json=data)
    assert reply.status_code == 202
    assert reply.json() == {"status": "VERIFICATION_REQUIRED", "public_ref": "opaque_testref_1234"}
    assert len(service.requests) == 1
    assert service.requests[0]["scan_receipt"] == receipt
    assert service.requests[0]["touch"] == data["first_touch"]
    assert service.requests[0]["checked"] is True
    assert "investor@example.com" not in str(reply.json())

    # Even the internal adapter cannot synthesize a receipt from event/ticker hints.
    with pytest.raises(FunnelGate) as absent:
        catalyst_optin.request_optin({"email": data["email"], "event_id": "event-123",
                                     "tickers": ["NVDA"], "scope": catalyst_optin.SCOPE,
                                     "consent": True})
    assert absent.value.code == "SCAN_PROOF_REQUIRED"
    bad_inputs = (
        {**data, "consent_checked": False},
        {**data, "consent_checked": "true"},
        {**data, "scope": "all_marketing"},
        {**data, "scan_receipt": ""},
        {**data, "honeypot": "bot-filled"},
        {**data, "form_elapsed_ms": 100},
        {**data, "extra_private_parameter": "no"},
    )
    for bad in bad_inputs:
        assert client.post("/api/catalyst/optin/request", json=bad).status_code == 400
    assert len(service.requests) == 1


def test_optin_request_bounds_body_and_requires_json_before_owner_call(web, monkeypatch):
    client, service = web
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setenv("CATALYST_OPTIN_ENABLED", "1")
    oversized = {"email": "investor@example.com", "scan_receipt": "a" * 64,
                 "consent_checked": True, "form_elapsed_ms": 4000,
                 "first_touch": {"untrusted": "x" * 5000}}
    assert client.post("/api/catalyst/optin/request", json=oversized).status_code == 413
    assert client.post("/api/catalyst/optin/request", data='{"email":"investor@example.com"}',
                       headers={"Content-Type": "text/plain"}).status_code == 415
    assert not service.requests


def test_no_signed_scan_authority_refuses_descriptor_without_identity_side_effects(web, monkeypatch):
    client, _ = web
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setenv("CATALYST_OPTIN_ENABLED", "1")

    class NoScanAuthorityService:
        def __init__(self):
            self.called = 0

        def request(self, **kw):
            self.called += 1
            return catalyst_optin.UnwiredScanAuthority().require_public_scan(kw["scan_receipt"])

    service = NoScanAuthorityService()
    catalyst_optin.configure(service)
    data = {"email": "investor@example.com",
            "scan_receipt": '{"event_id":"event-123","tickers":["NVDA"]}',
            "consent_checked": True, "scope": catalyst_optin.SCOPE,
            "form_elapsed_ms": 4000}
    response = client.post("/api/catalyst/optin/request", json=data)
    assert response.status_code == 503
    assert response.json()["detail"] == "SIGNED_SCAN_AUTHORITY_NOT_READY"
    assert service.called == 1


def test_bots_rejected_before_otp_verification_owner(web):
    client, service = web
    d = {"email": "investor@example.com", "otp": "123456",
         "public_ref": "opaque_testref_1234", "honeypot": "filled"}
    assert client.post("/api/catalyst/optin/verify", json=d).status_code == 400
    assert not service.verifies


def test_verify_requires_post_valid_otp_and_safe_unconfigured_gate(web):
    client, service = web
    assert client.post("/api/catalyst/optin/verify", json={
        "email": "investor@example.com", "otp": "123456", "public_ref": "opaque_testref_1234"}).json()["status"] == "verified"
    assert len(service.verifies) == 1
    catalyst_optin.configure(None)
    assert client.post("/api/catalyst/optin/verify", json={
        "email": "investor@example.com", "otp": "123456", "public_ref": "opaque_testref_1234"}).json()["detail"] == "CATALYST_INTEGRATION_NOT_READY"


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
                           "catalyst_event_updates/v1", "2026-10-09T02:00:00+00:00", "nonce",
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
                           "catalyst_event_updates/v1", "2026-10-09T02:00:00+00:00", "nonce", {})
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
            return {"owner": "email_consent", "version": 2}
        if path.endswith("begin"):
            return {"public_ref": "opaque_testref_1234"}
        if path.endswith("resolve"):
            return {"intent": "signed-long-private-intent"}
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
    assert owner.begin_pending_intent("signed-long-private-intent", "email_hmac", "2026-10-09T03:20:00+00:00") == "opaque_testref_1234"
    assert owner.resolve_pending_intent("opaque_testref_1234", "email_hmac") == "signed-long-private-intent"
    assert owner.confirm(record).record.first_touch == {"partner_id": "partnerA"}
    assert owner.current(UID, "event-123") == record
    assert owner.interested("event-123", 1) == [record]
    assert owner.revoke(UID, "event-123", "2026-10-09T06:00:00+00:00")
    payload = next(c[2] for c in calls if c[1].endswith("confirm"))
    assert payload["p_first_touch"] == {"partner_id": "partnerA"}
    assert "email" not in str(payload).lower() and "investor@example.com" not in str(payload)
    assert all(m == "POST" and path.startswith("rpc/catalyst_consent_") for m, path, _ in calls)


def test_consent_rpc_missing_owner_version_bad_reply_or_leaky_email_is_fail_closed():
    owner = catalyst_optin.SupabaseConsentRpcOwner(pg=lambda method, path, body: {"owner": "email_consent", "version": 1})
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


def test_first_value_scan_is_owned_by_00_no_email_wall_or_duplicate_route(web):
    client, svc = web
    assert client.get("/api/catalyst/scan").status_code == 404
    assert client.post("/api/catalyst/optin", json={}).status_code == 404
    assert client.post("/api/catalyst/optin/request", json={}).status_code == 503
    assert svc.requests == []


def test_reuses_exact_00_public_scan_rights_and_freshness_gate(monkeypatch):
    import json
    import sys
    from types import SimpleNamespace
    from app import catalyst_optin
    seen = []
    def read(tickers, *, event_id):
        seen.append((tickers, event_id))
        return {"event_id": event_id, "as_of_utc": "2026-10-09T03:00:00+00:00",
                "publication_state": "PUBLIC_QUALIFIED",
                "results": [{"ticker": t, "status": "SUPPORTED"} for t in tickers]}
    owner = SimpleNamespace(scan_with_reader=read, normalize_tickers=lambda ts: ts)
    monkeypatch.setitem(sys.modules, "app.catalyst_integration", owner)
    from app import catalyst_optin as app_module
    monkeypatch.setattr(__import__("app"), "catalyst_integration", owner, raising=False)
    adapter = catalyst_optin.CanonicalPublicScanAuthority()
    rec = json.dumps({"event_id": "event-123", "tickers": ["NVDA", "AMD"]})
    evidence = adapter.require_public_scan(rec)
    assert evidence.public_safe and evidence.event_id == "event-123"
    assert evidence.tickers == ("NVDA", "AMD")
    assert seen == [(["NVDA", "AMD"], "event-123")]
    owner.scan_with_reader = lambda ts, *, event_id: {
        "event_id": event_id, "as_of_utc": "2026-10-09T03:00:00+00:00",
        "publication_state": "PARTIAL",
        "results": [{"ticker": "NVDA", "status": "SUPPORTED"},
                    {"ticker": "AMD", "status": "RIGHTS_BLOCKED"}]}
    with pytest.raises(FunnelGate) as error:
        adapter.require_public_scan(rec)
    assert error.value.code == "SCAN_NOT_PUBLIC_SAFE"


def test_00_private_delivery_seam_needs_an_authoritative_revision_loader():
    from engine.marketing.catalyst_lifecycle import PublicRevision
    class Loader:
        def load_public_revision(self, event_id, generation):
            return PublicRevision(event_id, generation, "2026-10-09T04:00:00+00:00",
                                  "2026-10-09T03:00:00+00:00", "NVDA", "Material update",
                                  "New source update", ("https://www.sec.gov/",), True, True, True, True)
    class ServiceStub:
        def __init__(self): self.revisions, self.calls = Loader(), []
        def deliver(self, revision, now):
            self.calls.append((revision, now))
            return [{"user_ref": "u_opaque", "state": "PROVIDER_ACCEPTED", "event_id": revision.event_id}]
    from app import catalyst_optin
    service=ServiceStub()
    catalyst_optin.configure(service)
    try:
        result=catalyst_optin.deliver_update("event-123", 2)
        assert result["status"] == "PROVIDER_ACCEPTED" and result["generation"] == 2
        assert result["receipts"][0]["user_ref"] == "u_opaque" and service.calls
        service.revisions=object()
        with pytest.raises(FunnelGate) as error:
            catalyst_optin.deliver_update("event-123", 2)
        assert error.value.code == "REVISION_OWNER_NOT_READY"
    finally:
        catalyst_optin.configure(None)
