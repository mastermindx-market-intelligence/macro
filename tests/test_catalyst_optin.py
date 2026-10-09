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


def test_session00_private_request_requires_signed_proof_and_explicit_consent(web):
    client, service = web
    assert client.post("/api/catalyst/optin/request", json={}).status_code == 404
    # Structurally signed-looking only: the fake service below is not the
    # canonical HMAC verifier. Production must inject 00.ScanReceiptAuthority.
    signed = "eyJ2IjoxLCJldmVudF9pZCI6ImV2ZW50LTEyMyJ9." + "b" * 43
    data = {"email": "investor@example.com", "scan_receipt": signed,
            "consent_checked": True, "scope": catalyst_optin.SCOPE,
            "form_elapsed_ms": 3000, "honeypot": "",
            "first_touch": {"utm_content": "post-02", "utm_medium": "partner-1"}}
    out = catalyst_optin.request_optin(data)
    assert out == {"status": "VERIFICATION_REQUIRED", "public_ref": "opaque_testref_1234"}
    assert len(service.requests) == 1
    assert service.requests[0]["touch"] == data["first_touch"]
    assert service.requests[0]["checked"] is True
    assert service.requests[0]["scan_receipt"] == signed
    for bad in (
        {**data, "consent_checked": False},
        {**data, "scope": "all_marketing"},
        {**data, "scan_receipt": '{"event_id":"event-123","tickers":["NVDA"]}'},
        {**data, "scan_receipt": "not-a-signature"},
        {**data, "honeypot": "robot"},
        {**data, "form_elapsed_ms": 2999},
        {**data, "form_elapsed_ms": True},
        {**data, "form_elapsed_ms": 86_400_001},
        {**data, "event_id": "event-123"},
        {**data, "tickers": ["NVDA"]},
        {**data, "first_touch": {"comment": "x" * 4200}},
    ):
        with pytest.raises(FunnelGate):
            catalyst_optin.request_optin(bad)
    assert len(service.requests) == 1


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


@pytest.mark.parametrize("bad_reply", [
    {"error": "email sending disabled"},
    {"error_code": "over_email_send_rate_limit"},
    {"error_description": "OTP service not ready"},
    {"status": "error"},
    [],
    None,
    "opaque response",
])
def test_otp_adapter_never_reports_request_accepted_on_provider_semantic_rejection(bad_reply):
    identity = catalyst_optin.SupabaseOtpIdentity(
        endpoint="https://auth.example.com", anon_key="public",
        transport=lambda path, data: bad_reply)
    with pytest.raises(FunnelGate) as exc:
        identity.request_otp("investor@example.com")
    assert exc.value.code == "IDENTITY_VERIFICATION_UNAVAILABLE"


def test_anonymous_suppression_uses_incumbent_address_level_owner():
    called = []
    class Mailer:
        @staticmethod
        def _suppression_reason(email, user_id):
            called.append((email, user_id))
            return "bounce"
    authority = catalyst_optin.ExistingMailerSuppression(mailer=Mailer())
    assert authority.is_suppressed("investor@example.com", None) is True
    assert called == [("investor@example.com", None)]


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


@pytest.mark.parametrize("mutation", [
    lambda row: row.update(tickers=["AMD"]),
    lambda row: row.update(tickers=["NVDA", "NVDA"]),
    lambda row: row.update(tickers="NVDA"),
    lambda row: row.update(tickers=["NVDA?"]),
    lambda row: row.update(first_touch={"partner_id": "different"}),
    lambda row: row.update(first_touch={"email": "secret@example.com"}),
    lambda row: row.update(intent_id="unrelated-nonce"),
])
def test_consent_rpc_refuses_mismatched_new_grant_or_untrusted_projection(mutation):
    from engine.marketing.catalyst_lifecycle import ConsentRecord, SCOPE
    record = ConsentRecord(UID, "investor@example.com", "event-123", ("NVDA",),
                           SCOPE, "2026-10-09T03:00:00+00:00", "nonce-A",
                           {"partner_id": "original"})
    row = dict(record.__dict__)
    mutation(row)
    owner = catalyst_optin.SupabaseConsentRpcOwner(
        pg=lambda method, path, body: {"created": True, "record": row})
    with pytest.raises(FunnelGate) as error:
        owner.confirm(record)
    assert error.value.code == "CONSENT_OWNER_PROTOCOL_MISMATCH"


def test_rpc_replay_preserves_first_admitted_attribution_not_second_claim():
    from engine.marketing.catalyst_lifecycle import ConsentRecord, SCOPE
    record = ConsentRecord(UID, "investor@example.com", "event-123", ("NVDA",),
                           SCOPE, "2026-10-09T03:00:00+00:00", "new-nonce",
                           {"partner_id": "attempted-second-credit"})
    saved = {**record.__dict__, "intent_id": "original-nonce",
             "first_touch": {"partner_id": "genuine-first-credit"}}
    owner = catalyst_optin.SupabaseConsentRpcOwner(
        pg=lambda method, path, body: {"created": False, "record": saved})
    out = owner.confirm(record)
    assert out.created is False
    assert out.record.first_touch == {"partner_id": "genuine-first-credit"}
    assert out.record.intent_id == "original-nonce"


def test_first_value_scan_is_owned_by_00_no_email_wall_or_duplicate_route(web):
    client, svc = web
    assert client.get("/api/catalyst/scan").status_code == 404
    assert client.post("/api/catalyst/optin", json={}).status_code == 404
    assert client.post("/api/catalyst/optin/request", json={}).status_code == 404
    assert svc.requests == []


def test_unsigned_scan_descriptor_never_falls_back_to_unmerged_integration_module():
    with pytest.raises(FunnelGate) as err:
        catalyst_optin.UnwiredScanAuthority().require_public_scan(
            '{"event_id":"event-123","tickers":["NVDA"]}')
    assert err.value.code == "SCAN_AUTHORITY_NOT_WIRED"
    assert err.value.status == 503
    # No sibling module import is needed until Session 00 explicitly injects
    # its HMAC signer/verifier backed by a rights-qualified current producer.


def test_private_delivery_summary_exposes_rights_hold_after_partial_provider_acceptance():
    """A blocked subscriber must not be hidden by an earlier successful send."""
    class Source:
        @staticmethod
        def load_public_revision(event_id, generation):
            return PublicRevision(
                event_id, generation, "2026-10-09T04:00:00+00:00",
                "2026-10-09T03:00:00+00:00", "NVDA", "Revised source",
                "Qualified correction", ("https://www.sec.gov/",),
                True, True, True, True)

    class SimulatedBatch:
        revisions = Source()
        states = ()
        def deliver(self, revision, now):
            return [
                {"user_ref": "u_no_pii_" + str(i), "state": state}
                for i, state in enumerate(self.states)
            ]

    fake = SimulatedBatch()
    catalyst_optin.configure(fake)
    try:
        for states, expected in (
            (("PROVIDER_ACCEPTED", "SOURCE_RIGHTS_NOT_CURRENT"), "SOURCE_RIGHTS_HELD"),
            (("SOURCE_RIGHTS_UNAVAILABLE",), "SOURCE_RIGHTS_HELD"),
            (("PROVIDER_ACCEPTED", "EFFECT_UNKNOWN"), "EFFECT_UNKNOWN"),
            (("PROVIDER_ACCEPTED",), "PROVIDER_ACCEPTED"),
            (("SUPPRESSED",), "NO_CONFIRMED_DELIVERY"),
        ):
            fake.states = states
            res = catalyst_optin.deliver_update("event-123", 2)
            assert res["status"] == expected
            assert [item["state"] for item in res["receipts"]] == list(states)
    finally:
        catalyst_optin.configure(None)


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
