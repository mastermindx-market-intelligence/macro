"""Additive opt-in routes for the anonymous-first Catalyst Scan.

The public request route is OWNED by Session 00, which calls our synchronous
``request_optin(body: dict)``; this module exposes only a separately gated OTP
verification router. No second public opt-in route, auth, mail service or DB.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from engine.marketing.catalyst_lifecycle import (
    Confirmation, ConsentOwner, ConsentRecord, DeliveryAuthority, FunnelGate,
    FunnelService, OtpIdentityAuthority, PublicRevision, SCOPE, ScanAuthority,
    SuppressionAuthority, VerifiedIdentity,
    format_revision, normalize_email,
)

router = APIRouter(tags=["catalyst-optin"])
_service: FunnelService | None = None


class VerifyOptin(BaseModel):
    email: str = Field(max_length=254)
    otp: str = Field(max_length=12)
    public_ref: str = Field(min_length=8, max_length=128)
    honeypot: str = Field(default="", max_length=100)

class RequestOptin(BaseModel):
    email: str = Field(max_length=254)
    scan_receipt: str = Field(min_length=32, max_length=1024)
    consent_checked: bool
    scope: str = Field(default=SCOPE)
    first_touch: dict[str, str] = Field(default_factory=dict)
    honeypot: str = Field(default="", max_length=100)
    form_elapsed_ms: int = Field(default=0, ge=0, le=600_000)


def configure(service: FunnelService | None) -> None:
    """Integration owner mounts this router and injects only approved authorities."""
    global _service
    _service = service


def _active() -> FunnelService:
    if _service is None:
        raise HTTPException(status_code=503, detail="CATALYST_INTEGRATION_NOT_READY")
    return _service


def _abuse_guard(request: Request) -> None:
    """Use the SAME application abuse owner as public support, not a shadow limiter.

    Production Caddy must overwrite x-mm-peer; app.support already has a bounded
    per-client + trusted-peer window. Deployment admission confirms that invariant.
    """
    try:
        from app import support  # lazy, no global main/supabase import
        if support._rate_ok(support._client_ip(request), request.headers.get("x-mm-peer", "")):
            return
    except Exception:
        raise HTTPException(status_code=503, detail="RATE_GUARD_UNAVAILABLE") from None
    raise HTTPException(status_code=429, detail="RATE_LIMITED", headers={"Retry-After": "3600"})


def _safe_gate(exc: FunnelGate) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.code)


def request_optin(body: dict) -> dict:
    """Secure private owner seam. The caller MUST provide the signed 00 scan receipt.

    A browser's event/tickers are not evidence of a prior result. The injected
    ScanAuthority must authenticate the token and re-check public source rights
    and the current generation before any identity or consent effect.
    """
    if not isinstance(body, dict) or body.get("scope") != SCOPE or body.get("consent") is not True:
        raise FunnelGate("EXPLICIT_CONSENT_REQUIRED", 400)
    receipt = body.get("scan_receipt")
    if not isinstance(receipt, str) or not 32 <= len(receipt) <= 1024:
        raise FunnelGate("SCAN_PROOF_REQUIRED", 400)
    accepted = _active().request(email=body.get("email"), checked=True,
                                 scan_receipt=receipt, touch=body.get("attribution"),
                                 now=datetime.now(timezone.utc))
    ref = accepted.get("public_ref") if isinstance(accepted, dict) else None
    if (not isinstance(ref, str) or
            not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", ref)):
        raise FunnelGate("PENDING_CONSENT_PROTOCOL_MISMATCH")
    return {"status": "VERIFICATION_REQUIRED", "public_ref": ref}


async def _read_bounded_optin_json(request: Request) -> dict:
    """Bound body before JSON parsing or a GoTrue/consent owner operation."""
    data = bytearray()
    async for part in request.stream():
        if len(data) + len(part) > 4096:
            raise HTTPException(413, "REQUEST_TOO_LARGE")
        data.extend(part)
    try:
        body = json.loads(data)
    except (ValueError, TypeError, UnicodeError):
        raise HTTPException(400, "INVALID_JSON") from None
    allowed = {"email", "scan_receipt", "consent_checked", "scope",
               "first_touch", "honeypot", "form_elapsed_ms"}
    if not isinstance(body, dict) or set(body) - allowed:
        raise HTTPException(400, "INVALID_OPTIN_REQUEST")
    return body


@router.post("/api/catalyst/optin/request", status_code=202)
async def public_request_optin(request: Request) -> dict:
    """Only opt-in request endpoint. Never grant consent or claim inbox delivery."""
    if (os.environ.get("CATALYST_PUBLIC_ENABLED") != "1"
            or os.environ.get("CATALYST_OPTIN_ENABLED") != "1"):
        raise HTTPException(503, "CATALYST_OPTIN_DISABLED")
    _abuse_guard(request)
    raw = await _read_bounded_optin_json(request)
    try:
        body = RequestOptin(**raw)
    except (ValueError, TypeError):
        raise HTTPException(400, "INVALID_OPTIN_REQUEST") from None
    if body.honeypot or body.form_elapsed_ms < 3000:
        raise HTTPException(400, "ABUSE_CHECK_FAILED")
    if body.scope != SCOPE or body.consent_checked is not True:
        raise HTTPException(400, "EXPLICIT_CONSENT_REQUIRED")
    try:
        return request_optin({"email": body.email, "scan_receipt": body.scan_receipt,
                              "scope": body.scope, "consent": True,
                              "attribution": body.first_touch})
    except FunnelGate as exc:
        raise _safe_gate(exc) from None

class CanonicalPublicScanAuthority(ScanAuthority):
    """Re-use 00's actual serializer/rights/freshness gate; no duplicate feed.

    The event/ticker 'receipt' is an internal lookup descriptor, *not* a signed
    visitor proof: 00 deliberately does not freeze a public scan receipt token.
    We therefore RE-READ 00's current public scan rather than trust this JSON.
    """

    def require_public_scan(self, receipt: str):
        from engine.marketing.catalyst_lifecycle import ScanEvidence
        try:
            descriptor = json.loads(receipt)
            if not isinstance(descriptor, dict) or set(descriptor) != {"event_id", "tickers"}:
                raise ValueError("bad descriptor")
            from app import catalyst_integration as bridge
            tickers = bridge.normalize_tickers(descriptor["tickers"])
            event_id = descriptor["event_id"]
            scan = bridge.scan_with_reader(tickers, event_id=event_id)
            if (scan.get("event_id") != event_id or
                    scan.get("publication_state") not in ("PUBLIC_QUALIFIED", "PARTIAL") or
                    any(row.get("status") != "SUPPORTED" for row in scan.get("results", [])) or
                    len(scan.get("results", [])) != len(tickers)):
                raise ValueError("not currently public-qualified")
            return ScanEvidence(event_id, tuple(tickers), scan["as_of_utc"], True)
        except Exception:
            raise FunnelGate("SCAN_NOT_PUBLIC_SAFE", 403) from None



class UnwiredScanAuthority:
    """No signed source authority has been admitted: fail closed, not a JSON fallback."""

    def require_public_scan(self, receipt: str):
        raise FunnelGate("SIGNED_SCAN_AUTHORITY_NOT_READY", 503)


@router.post("/api/catalyst/optin/verify")
def verify_optin(body: VerifyOptin, request: Request) -> dict:
    if body.honeypot:
        raise HTTPException(status_code=400, detail="ABUSE_CHECK_FAILED")
    _abuse_guard(request)
    try:
        return _active().verify(email=body.email, otp=body.otp,
                                public_ref=body.public_ref, now=datetime.now(timezone.utc))
    except FunnelGate as exc:
        raise _safe_gate(exc) from None


class SupabaseOtpIdentity(OtpIdentityAuthority):
    """GoTrue email OTP, not a new identity provider or verification database.

    With auth service unconfigured, fail closed. A successful /otp response is
    merely provider acceptance; only /verify + GoTrue's confirmed email is a
    verified identity. Connection failures never report a successful delivery.
    """

    def __init__(self, *, endpoint: str, anon_key: str,
                 transport: Callable[[str, dict], dict] | None = None):
        self.endpoint = endpoint.rstrip("/")
        self.anon_key = anon_key
        self._transport = transport or self._post

    def _post(self, path: str, payload: dict) -> dict:
        if not self.anon_key or not self.endpoint.startswith("https://"):
            raise FunnelGate("IDENTITY_VERIFICATION_UNAVAILABLE")
        req = urllib.request.Request(
            self.endpoint + path,
            data=json.dumps(payload, separators=(",", ":")).encode(),
            headers={"apikey": self.anon_key, "Authorization": f"Bearer {self.anon_key}",
                     "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                body = resp.read(64_000)
            return json.loads(body or b"{}")
        except (urllib.error.URLError, ValueError, OSError):
            # Do not log the provider body: error messages may include addresses/tokens.
            raise FunnelGate("IDENTITY_VERIFICATION_UNAVAILABLE") from None

    def request_otp(self, email: str) -> bool:
        if not self.anon_key or not self.endpoint.startswith("https://"):
            raise FunnelGate("IDENTITY_VERIFICATION_UNAVAILABLE")
        try:
            self._transport("/auth/v1/otp", {"email": normalize_email(email),
                                             "create_user": True})
            return True  # OTP request accepted; not a claim that an inbox received it
        except FunnelGate:
            raise
        except Exception:
            raise FunnelGate("IDENTITY_VERIFICATION_UNAVAILABLE") from None

    def verify_otp(self, email: str, code: str) -> VerifiedIdentity:
        if not self.anon_key or not self.endpoint.startswith("https://"):
            raise FunnelGate("IDENTITY_VERIFICATION_UNAVAILABLE")
        try:
            result = self._transport("/auth/v1/verify", {"type": "email", "email":
                                     normalize_email(email), "token": code})
            user = result.get("user")
            if not isinstance(user, dict):
                raise ValueError("missing user")
            confirmed = user.get("email_confirmed_at")
            if not confirmed or not user.get("id") or normalize_email(user.get("email")) != normalize_email(email):
                raise ValueError("not confirmed")
            # The GoTrue verification endpoint proves possession of this OTP.
            return VerifiedIdentity(user_id=user["id"], email=user["email"],
                                    verified_at_utc=confirmed)
        except Exception:
            raise FunnelGate("IDENTITY_UNVERIFIED", 403) from None


class ExistingMailerSuppression(SuppressionAuthority):
    def __init__(self, mailer: Any | None = None):
        self._mailer = mailer

    def is_suppressed(self, email: str, user_id: str) -> bool:
        if self._mailer is not None:
            owner = self._mailer
        else:
            from app import mailer
            owner = mailer
        # Failure from canonical lookup must stop both consent and delivery.
        return owner._suppression_reason(email, user_id) is not None


class ExistingMailerDelivery(DeliveryAuthority):
    """Strict-claim mail adapter. Never substitutes Gmail or a marketing outbox.

    MAIL_CATALYST_ENABLED defaults OFF; all public source-rights approval is
    separately required by FunnelService before this adapter is reached.
    """

    def __init__(self, mailer: Any | None = None, marketing: Any | None = None,
                 enabled: Callable[[], bool] | None = None):
        self._mailer, self._marketing = mailer, marketing
        self._enabled = enabled or (lambda: os.environ.get("MAIL_CATALYST_ENABLED", "") == "1")

    def _owners(self) -> tuple[Any, Any]:
        mailer, marketing = self._mailer, self._marketing
        if mailer is None:
            from app import mailer as default_mailer
            mailer = default_mailer
        if marketing is None:
            from app import marketing_emails
            marketing = marketing_emails
        return mailer, marketing

    def permitted(self) -> bool:
        try:
            mailer, marketing = self._owners()
            return (self._enabled() and mailer.is_configured() and
                    bool(mailer.unsub_token("00000000-0000-4000-8000-000000000000")) and
                    callable(marketing.unsub_page_url) and callable(marketing.unsub_api_url))
        except Exception:
            return False

    def deliver(self, record: Any, revision: PublicRevision, idem_key: str) -> str:
        if not self.permitted():
            return "skipped_no_smtp"
        mailer, marketing = self._owners()
        footer = marketing.unsub_page_url(record.user_id)
        one_click = marketing.unsub_api_url(record.user_id)
        if not footer.startswith("https://") or not one_click.startswith("https://"):
            return "skipped_no_smtp"
        subject, body, plain = format_revision(revision, footer)
        try:
            return mailer.send(template="catalyst_material_revision", cls="marketing",
                               to_email=record.email, user_id=record.user_id,
                               subject=subject, html=body, text=plain,
                               idem_key=idem_key, headers={"unsubscribe_url": one_click},
                               strict_ledger=True)
        except Exception:
            return "effect_unknown"  # downstream may have fired; never assert non-delivery


class SupabaseConsentRpcOwner(ConsentOwner):
    """Adapter to *existing Supabase email-consent owner's* service-role RPC.

    Contract version 2 (not currently provisioned at main's email_prefs schema):
      POST rpc/catalyst_consent_contract {} -> {owner:"email_consent", version:2}
      POST rpc/catalyst_consent_begin {p_intent,p_email_tag,p_expires_at_utc}
        -> {public_ref:opaque 8..128 char handle, CSPRNG >=128-bit}
      POST rpc/catalyst_consent_resolve {p_public_ref,p_email_tag}
        -> {intent:original signed intent}, only while pending and unexpired
      POST rpc/catalyst_consent_confirm {p_user_id,p_event_id,p_scope,
          p_tickers,p_intent_id,p_verified_at_utc,p_first_touch}
        -> {created:bool,record:{user_id,email,event_id,tickers,scope,
             intent_id,verified_at_utc,first_touch,revoked_at_utc}}
      POST rpc/catalyst_consent_current {p_user_id,p_event_id} -> record|null
      POST rpc/catalyst_consent_interested {p_event_id,p_limit} -> [record]
      POST rpc/catalyst_consent_revoke {p_user_id,p_event_id,p_revoked_at_utc}
        -> {changed:bool}

    The canonical consent/DB owner must implement these atomic SECURITY DEFINER
    functions with service-role-only EXECUTE and deny-all RLS, own the positive
    grants under the current email estate, enforce immutable first-touch and
    unique intent nonce, and read address only from auth.users. This adapter
    NEVER creates tables, auth users, or an independent contact store. An absent,
    unapproved, or incompatible function leaves the entire lane SEND_BLOCKED.
    """

    def __init__(self, pg: Callable[..., Any] | None = None):
        self._pg_override = pg

    def _rpc(self, name: str, payload: dict) -> Any:
        if self._pg_override is not None:
            pg = self._pg_override
        else:
            from app import mailer
            pg = mailer._pg
        return pg("POST", "rpc/" + name, body=payload)

    @staticmethod
    def _one(result: Any) -> dict:
        if isinstance(result, list) and len(result) == 1:
            result = result[0]
        if not isinstance(result, dict):
            raise FunnelGate("CONSENT_OWNER_PROTOCOL_MISMATCH")
        return result

    def available(self) -> bool:
        try:
            result = self._one(self._rpc("catalyst_consent_contract", {}))
            return result.get("owner") == "email_consent" and result.get("version") == 2
        except Exception:
            return False

    def begin_pending_intent(self, intent: str, email_tag: str, expires_at_utc: str) -> str:
        result = self._one(self._rpc("catalyst_consent_begin", {
            "p_intent": intent, "p_email_tag": email_tag,
            "p_expires_at_utc": expires_at_utc}))
        ref = result.get("public_ref")
        if not isinstance(ref, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", ref):
            raise FunnelGate("PENDING_CONSENT_PROTOCOL_MISMATCH")
        return ref

    def resolve_pending_intent(self, public_ref: str, email_tag: str) -> str:
        result = self._one(self._rpc("catalyst_consent_resolve", {
            "p_public_ref": public_ref, "p_email_tag": email_tag}))
        intent = result.get("intent")
        if not isinstance(intent, str) or not 1 <= len(intent) <= 4096:
            raise FunnelGate("PENDING_CONSENT_UNAVAILABLE")
        return intent

    @staticmethod
    def _record(raw: Any) -> ConsentRecord:
        try:
            if not isinstance(raw, dict) or raw.get("scope") != SCOPE:
                raise ValueError("not scoped")
            obj = ConsentRecord(user_id=str(raw["user_id"]), email=normalize_email(raw["email"]),
                                event_id=str(raw["event_id"]), tickers=tuple(raw["tickers"]),
                                scope=raw["scope"], verified_at_utc=str(raw["verified_at_utc"]),
                                intent_id=str(raw["intent_id"]),
                                first_touch=dict(raw["first_touch"]),
                                revoked_at_utc=raw.get("revoked_at_utc"))
            if not obj.tickers or not obj.intent_id:
                raise ValueError("not populated")
            return obj
        except (KeyError, TypeError, ValueError, FunnelGate) as exc:
            raise FunnelGate("CONSENT_OWNER_PROTOCOL_MISMATCH") from exc

    def confirm(self, record: ConsentRecord) -> Confirmation:
        # Email intentionally NOT sent in payload; existing GoTrue owner owns address.
        body = {"p_user_id": record.user_id, "p_event_id": record.event_id,
                "p_tickers": list(record.tickers), "p_scope": record.scope,
                "p_intent_id": record.intent_id, "p_verified_at_utc": record.verified_at_utc,
                "p_first_touch": record.first_touch}
        result = self._one(self._rpc("catalyst_consent_confirm", body))
        saved = self._record(result.get("record"))
        if (saved.user_id != record.user_id or saved.email != record.email or
                saved.event_id != record.event_id or saved.scope != record.scope or
                type(result.get("created")) is not bool):
            raise FunnelGate("CONSENT_OWNER_PROTOCOL_MISMATCH")
        return Confirmation(saved, result["created"])

    def current(self, user_id: str, event_id: str) -> ConsentRecord | None:
        result = self._rpc("catalyst_consent_current", {"p_user_id": user_id, "p_event_id": event_id})
        if result is None or result == []:
            return None
        row = self._record(self._one(result))
        if row.user_id != user_id or row.event_id != event_id:
            raise FunnelGate("CONSENT_OWNER_PROTOCOL_MISMATCH")
        return row

    def interested(self, event_id: str, limit: int) -> list[ConsentRecord]:
        result = self._rpc("catalyst_consent_interested", {"p_event_id": event_id,
                                                             "p_limit": limit})
        if not isinstance(result, list) or len(result) > limit:
            raise FunnelGate("CONSENT_OWNER_PROTOCOL_MISMATCH")
        records = [self._record(row) for row in result]
        if any(r.event_id != event_id or r.revoked_at_utc for r in records):
            raise FunnelGate("CONSENT_OWNER_PROTOCOL_MISMATCH")
        return records

    def revoke(self, user_id: str, event_id: str, at_utc: str) -> bool:
        result = self._one(self._rpc("catalyst_consent_revoke",
                                     {"p_user_id": user_id, "p_event_id": event_id,
                                      "p_revoked_at_utc": at_utc}))
        if type(result.get("changed")) is not bool:
            raise FunnelGate("CONSENT_OWNER_PROTOCOL_MISMATCH")
        return result["changed"]


class UnwiredConsentOwner(ConsentOwner):
    """Fail-closed until the EXISTING consent/SQL owner approves its durable port."""

    def available(self) -> bool:
        return False

    def begin_pending_intent(self, intent, email_tag, expires_at_utc):
        raise FunnelGate("CONSENT_OWNER_NOT_READY")

    def resolve_pending_intent(self, public_ref, email_tag):
        raise FunnelGate("CONSENT_OWNER_NOT_READY")

    def confirm(self, record):
        raise FunnelGate("CONSENT_OWNER_NOT_READY")

    def current(self, user_id, event_id):
        raise FunnelGate("CONSENT_OWNER_NOT_READY")

    def interested(self, event_id, limit):
        raise FunnelGate("CONSENT_OWNER_NOT_READY")

    def revoke(self, user_id, event_id, at_utc):
        raise FunnelGate("CONSENT_OWNER_NOT_READY")


def build_existing_owner_service(revisions: Any, *, scan: ScanAuthority | None = None,
                                 consent: ConsentOwner | None = None,
                                 identity: OtpIdentityAuthority | None = None) -> FunnelService:
    """Explicit integration seam. Does NOT install/mount/start anything itself."""
    from app.account_actions import _anon_key, _supabase
    url, _service_role = _supabase()
    return FunnelService(secret=os.environ.get("MAIL_UNSUB_SECRET", ""),
                         scan=scan if scan is not None else UnwiredScanAuthority(),
                         identity=identity or SupabaseOtpIdentity(endpoint=url, anon_key=_anon_key()),
                         consent=consent if consent is not None else SupabaseConsentRpcOwner(),
                         suppression=ExistingMailerSuppression(), revisions=revisions,
                         sender=ExistingMailerDelivery())


def deliver_update(event_id: str, generation: int) -> dict:
    """EXACT frozen 00 private seam. No public email-trigger route.

    Revision source remains with the existing qualified producer. This adapter
    refuses to infer content from ticker/news or construct an approval receipt.
    """
    service = _active()
    if not isinstance(event_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", event_id):
        raise FunnelGate("INVALID_SCAN_EVENT", 400)
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        raise FunnelGate("INVALID_REVISION", 400)
    loader = getattr(service.revisions, "load_public_revision", None)
    if not callable(loader):
        raise FunnelGate("REVISION_OWNER_NOT_READY")
    revision = loader(event_id, generation)
    if not isinstance(revision, PublicRevision) or revision.event_id != event_id or revision.generation != generation:
        raise FunnelGate("REVISION_OWNER_PROTOCOL_MISMATCH")
    receipts = service.deliver(revision, now=datetime.now(timezone.utc))
    # All receipts are opaque and attribution-only; no recipient PII. Provider
    # acceptance is deliberately NOT called inbox delivery.
    states = {x["state"] for x in receipts}
    return {"event_id": event_id, "generation": generation, "receipts": receipts,
            "status": "EFFECT_UNKNOWN" if "EFFECT_UNKNOWN" in states else
                      "PROVIDER_ACCEPTED" if "PROVIDER_ACCEPTED" in states else
                      "NO_CONFIRMED_DELIVERY"}
