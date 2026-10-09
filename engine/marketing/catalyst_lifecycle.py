"""Consent-safe Catalyst Scan follow-up adapter (MMX-ACQ-CATALYST-FUNNEL-20261008).

No account is required to RECEIVE THE SCAN. Only a later, separately checked
request enters this module. Identity proof belongs to existing Supabase GoTrue;
positive opt-in and revocation belong to the existing Supabase email/consent owner;
actual email and its exactly-once ledger belong to app.mailer. This module has
NO database, shadow contact list, queue or background scheduler.

The ConsentOwner protocol is deliberately fail-closed until the incumbent email
owner exposes an atomic scoped-consent operation: email_prefs currently stores
opt-outs but NOT a positive, time-stamped, event-scoped grant. A JSONL ledger,
account creation or an email_log entry cannot substitute for positive consent.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import binascii
import hmac
import html
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import UUID

SCOPE = "catalyst_event_updates/v1"
INTENT_TTL = timedelta(minutes=20)
# A verified generation may still be ancient. Match the public scan freshness
# ceiling until the source owner admits a stricter event-specific validity window.
PUBLIC_REVISION_MAX_AGE = timedelta(days=7)
_TOKEN_PREFIX = b"mastermind.catalyst.intent.v1\x00"
_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
_EVENT_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_TICKER = re.compile(r"[A-Z][A-Z0-9.\-]{0,9}\Z")
_TOUCH_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "partner_id")


class FunnelGate(Exception):
    """Public-safe error; neither a token nor an address may appear in its message."""

    def __init__(self, code: str, status: int = 503):
        self.code, self.status = code, status
        super().__init__(code)


def _utc(dt: datetime) -> datetime:
    if not isinstance(dt, datetime) or dt.tzinfo is None:
        raise FunnelGate("INVALID_UTC_TIME", 400)
    return dt.astimezone(timezone.utc)


def _timestamp(value: str) -> datetime:
    try:
        return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except (TypeError, ValueError, AttributeError) as exc:
        raise FunnelGate("INVALID_SOURCE_TIME", 400) from exc


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise FunnelGate("INVALID_EMAIL", 400)
    value = email.strip().lower()
    if len(value) > 254 or not _EMAIL.fullmatch(value) or ".." in value:
        raise FunnelGate("INVALID_EMAIL", 400)
    return value


def first_touch(values: dict[str, Any] | None) -> dict[str, str]:
    """UTM is a sanitized referral *claim*, never an authenticated partner payout."""
    values = values or {}
    if not isinstance(values, dict):
        raise FunnelGate("INVALID_ATTRIBUTION", 400)
    clean: dict[str, str] = {}
    for key in _TOUCH_KEYS:
        value = values.get(key)
        if value is None or value == "":
            continue
        if not isinstance(value, str) or len(value) > 96 or not _ID.fullmatch(value):
            raise FunnelGate("INVALID_ATTRIBUTION", 400)
        clean[key] = value
    return clean


def _event_id(value: str) -> str:
    if not isinstance(value, str) or not _EVENT_ID.fullmatch(value):
        raise FunnelGate("INVALID_SCAN_EVENT", 400)
    return value


def _uuid(value: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise FunnelGate("IDENTITY_UNVERIFIED", 403) from exc


@dataclass(frozen=True)
class ScanEvidence:
    """Returned by the canonical PUBLIC scan owner, not asserted by a web form."""

    event_id: str
    tickers: tuple[str, ...]
    as_of_utc: str
    public_safe: bool


@dataclass(frozen=True)
class VerifiedIdentity:
    user_id: str
    email: str
    verified_at_utc: str


@dataclass(frozen=True)
class ConsentRecord:
    """Immutable snapshot read/written through the existing secure consent owner."""

    user_id: str
    email: str  # private owner only; NEVER serialized into public result or attribution
    event_id: str
    tickers: tuple[str, ...]
    scope: str
    verified_at_utc: str
    intent_id: str
    first_touch: dict[str, str]
    revoked_at_utc: str | None = None


@dataclass(frozen=True)
class PublicRevision:
    """Current rights-qualified producer revision, confirmed by revision authority."""

    event_id: str
    generation: int
    as_of_utc: str
    published_at_utc: str
    ticker: str
    headline: str
    what_changed: str
    source_urls: tuple[str, ...]
    material: bool
    public_safe: bool
    external_rights_confirmed: bool
    operator_approved: bool
    correction: str = "none"  # none / corrected / retracted
    correction_note: str = ""


class ScanAuthority(Protocol):
    def require_public_scan(self, receipt: str) -> ScanEvidence: ...


class OtpIdentityAuthority(Protocol):
    def request_otp(self, email: str) -> bool: ...
    def verify_otp(self, email: str, code: str) -> VerifiedIdentity: ...


@dataclass(frozen=True)
class Confirmation:
    record: ConsentRecord
    created: bool


class ConsentOwner(Protocol):
    """Owned by the CURRENT Supabase consent system, NOT a local marketing ledger.

    confirm must atomically CAS unique (user_id, event_id, scope, intent_id),
    preserve original verified first-touch and block reactivation of revoked
    grants unless a FRESH verification supersedes them. Duplicate confirmation
    returns the ORIGINAL record, not an overwritten acquisition. All operations
    must be durable across workers/restarts; fail closed on unavailable stores.
    """

    def available(self) -> bool: ...
    def begin_pending_intent(self, intent: str, email_tag: str,
                             expires_at_utc: str) -> str: ...
    def resolve_pending_intent(self, public_ref: str, email_tag: str) -> str: ...
    def confirm(self, record: ConsentRecord) -> Confirmation: ...
    def current(self, user_id: str, event_id: str) -> ConsentRecord | None: ...
    def interested(self, event_id: str, limit: int) -> list[ConsentRecord]: ...
    def revoke(self, user_id: str, event_id: str, at_utc: str) -> bool: ...


class SuppressionAuthority(Protocol):
    def is_suppressed(self, email: str, user_id: str) -> bool: ...


class RevisionAuthority(Protocol):
    def is_current(self, event_id: str, generation: int) -> bool: ...


class DeliveryAuthority(Protocol):
    def permitted(self) -> bool: ...
    def deliver(self, record: ConsentRecord, revision: PublicRevision, idem_key: str) -> str: ...


def _email_tag(secret: str, email: str) -> str:
    return hmac.new(secret.encode(), b"email\x00" + email.encode(), hashlib.sha256).hexdigest()


def _sign(secret: str, payload: dict) -> str:
    if not secret or len(secret) < 32:
        raise FunnelGate("CONSENT_SECRET_UNAVAILABLE")
    packed = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    body = _b64(packed)
    signature = hmac.new(secret.encode(), _TOKEN_PREFIX + body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def _open_intent(secret: str, token: str, email: str, now: datetime) -> dict:
    if not secret or len(secret) < 32:
        raise FunnelGate("CONSENT_SECRET_UNAVAILABLE")
    if not isinstance(token, str) or len(token) > 4096 or token.count(".") != 1:
        raise FunnelGate("INVALID_VERIFICATION_INTENT", 400)
    body, sig = token.split(".")
    expected = hmac.new(secret.encode(), _TOKEN_PREFIX + body.encode(), hashlib.sha256).digest()
    try:
        received = _unb64(sig)
        if not hmac.compare_digest(expected, received):
            raise ValueError("bad MAC")
        payload = json.loads(_unb64(body))
    except (ValueError, TypeError, UnicodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise FunnelGate("INVALID_VERIFICATION_INTENT", 400) from exc
    if not isinstance(payload, dict) or payload.get("v") != 1 or payload.get("scope") != SCOPE:
        raise FunnelGate("INVALID_VERIFICATION_INTENT", 400)
    try:
        issued = _timestamp(payload["issued_at"])
        _event_id(payload["event_id"])
        if not isinstance(payload["nonce"], str) or len(payload["nonce"]) < 20:
            raise ValueError("bad nonce")
        tickers = payload["tickers"]
        if not isinstance(tickers, list) or not 1 <= len(tickers) <= 10 or not all(
            isinstance(t, str) and _TICKER.fullmatch(t) for t in tickers
        ) or len(set(tickers)) != len(tickers):
            raise ValueError("bad tickers")
        first_touch(payload["first_touch"])
    except (KeyError, ValueError, TypeError, FunnelGate) as exc:
        raise FunnelGate("INVALID_VERIFICATION_INTENT", 400) from exc
    if issued > now + timedelta(seconds=30) or now - issued > INTENT_TTL:
        raise FunnelGate("EXPIRED_VERIFICATION_INTENT", 400)
    if not hmac.compare_digest(str(payload.get("email_tag", "")), _email_tag(secret, email)):
        raise FunnelGate("INVALID_VERIFICATION_INTENT", 400)
    return payload


def _validate_scan(scan: ScanEvidence) -> None:
    _event_id(scan.event_id)
    if scan.public_safe is not True:
        raise FunnelGate("SCAN_NOT_PUBLIC_SAFE", 403)
    if not 1 <= len(scan.tickers) <= 10 or any(
        not isinstance(t, str) or not _TICKER.fullmatch(t) for t in scan.tickers
    ) or len(set(scan.tickers)) != len(scan.tickers):
        raise FunnelGate("INVALID_SCAN_TICKERS", 400)
    _timestamp(scan.as_of_utc)


def _validate_revision(rev: PublicRevision) -> None:
    _event_id(rev.event_id)
    if not isinstance(rev.generation, int) or isinstance(rev.generation, bool) or rev.generation < 1:
        raise FunnelGate("INVALID_REVISION", 400)
    if not all((rev.material is True, rev.public_safe is True,
                rev.external_rights_confirmed is True, rev.operator_approved is True)):
        raise FunnelGate("REVISION_NOT_APPROVED", 403)
    observed, published = _timestamp(rev.as_of_utc), _timestamp(rev.published_at_utc)
    if observed < published:
        raise FunnelGate("REVISION_TIME_INCONSISTENT", 400)
    if rev.correction not in ("none", "corrected", "retracted"):
        raise FunnelGate("INVALID_REVISION", 400)
    if rev.correction != "none" and not rev.correction_note.strip():
        raise FunnelGate("CORRECTION_NOTE_REQUIRED", 400)
    if (not _TICKER.fullmatch(rev.ticker) or not rev.headline.strip() or not rev.what_changed.strip()
            or any("\r" in x or "\n" in x for x in (rev.headline, rev.what_changed, rev.correction_note))):
        raise FunnelGate("INVALID_REVISION", 400)
    if len(rev.headline) > 180 or len(rev.what_changed) > 1200 or len(rev.correction_note) > 500:
        raise FunnelGate("INVALID_REVISION", 400)
    if not rev.source_urls or len(rev.source_urls) > 8:
        raise FunnelGate("SOURCE_RIGHTS_UNPROVEN", 403)
    for url in rev.source_urls:
        if not isinstance(url, str) or len(url) > 1024:
            raise FunnelGate("SOURCE_RIGHTS_UNPROVEN", 403)
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise FunnelGate("SOURCE_RIGHTS_UNPROVEN", 403)
        # Public provider must have already checked rights; don't emit internal or local URLs.
        if parsed.hostname in ("localhost",) or parsed.hostname.endswith((".local", ".internal")):
            raise FunnelGate("SOURCE_RIGHTS_UNPROVEN", 403)
        try:
            if not ipaddress.ip_address(parsed.hostname).is_global:
                raise FunnelGate("SOURCE_RIGHTS_UNPROVEN", 403)
        except ValueError:
            pass
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in url):
            raise FunnelGate("SOURCE_RIGHTS_UNPROVEN", 403)


def analytics_receipt(rec: ConsentRecord) -> dict[str, str]:
    """Explicit allowlist for existing D07 owner; no address, IP, token or OTP."""
    from engine.marketing.attribution import user_ref  # existing D07 canonical hash shape

    receipt = {"schema": "catalyst.funnel.receipt/v1", "user_ref": user_ref(rec.user_id),
               "event_id": rec.event_id, "scope": rec.scope,
               "verified_at_utc": rec.verified_at_utc}
    receipt.update(first_touch(rec.first_touch))
    return receipt


class FunnelService:
    """One opt-in request -> OTP proof -> secured grant -> eligible second-value mail."""

    def __init__(self, *, secret: str, scan: ScanAuthority, identity: OtpIdentityAuthority,
                 consent: ConsentOwner, suppression: SuppressionAuthority,
                 revisions: RevisionAuthority, sender: DeliveryAuthority):
        self.secret = secret
        self.scan = scan
        self.identity = identity
        self.consent = consent
        self.suppression = suppression
        self.revisions = revisions
        self.sender = sender

    def request(self, *, email: str, checked: bool, scan_receipt: str,
                touch: dict[str, Any] | None, now: datetime) -> dict[str, str]:
        """After anonymous scan only; does not register or grant consent."""
        if checked is not True:
            raise FunnelGate("EXPLICIT_CONSENT_REQUIRED", 400)
        addr, now = normalize_email(email), _utc(now)
        if not self.consent.available():
            raise FunnelGate("CONSENT_OWNER_NOT_READY")
        if not isinstance(scan_receipt, str) or not 1 <= len(scan_receipt) <= 1024:
            raise FunnelGate("SCAN_PROOF_REQUIRED", 400)
        scan = self.scan.require_public_scan(scan_receipt)
        _validate_scan(scan)
        data = {"v": 1, "scope": SCOPE, "nonce": secrets.token_urlsafe(24),
                "email_tag": _email_tag(self.secret, addr),
                "issued_at": now.isoformat(), "event_id": scan.event_id,
                "tickers": list(scan.tickers), "first_touch": first_touch(touch)}
        intent = _sign(self.secret, data)
        # Durable *pending* intent, not an early grant or another auth database.
        # The existing consent owner returns the short opaque handle frozen by 00.
        # It is written BEFORE GoTrue sends OTP; a failed claim cannot leave a
        # useless confirmation email in the person's inbox.
        try:
            public_ref = self.consent.begin_pending_intent(
                intent, _email_tag(self.secret, addr), (now + INTENT_TTL).isoformat())
        except FunnelGate:
            raise
        except Exception as exc:
            raise FunnelGate("PENDING_CONSENT_NOT_DURABLE") from exc
        if (not isinstance(public_ref, str) or
                not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", public_ref)):
            raise FunnelGate("PENDING_CONSENT_PROTOCOL_MISMATCH")
        # GoTrue is the existing email-identity owner. Accepted request != inbox receipt.
        if self.identity.request_otp(addr) is not True:
            raise FunnelGate("IDENTITY_VERIFICATION_UNAVAILABLE")
        return {"status": "verification_requested", "public_ref": public_ref,
                "scope": SCOPE, "expires_at_utc": (now + INTENT_TTL).isoformat()}

    def verify(self, *, email: str, otp: str, public_ref: str, now: datetime) -> dict[str, Any]:
        now = _utc(now)
        addr = normalize_email(email)
        if not self.consent.available():  # BEFORE consuming a one-use GoTrue code
            raise FunnelGate("CONSENT_OWNER_NOT_READY")
        if not isinstance(public_ref, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", public_ref):
            raise FunnelGate("INVALID_VERIFICATION_REF", 400)
        try:
            intent = self.consent.resolve_pending_intent(public_ref, _email_tag(self.secret, addr))
        except FunnelGate:
            raise
        except Exception as exc:
            raise FunnelGate("PENDING_CONSENT_UNAVAILABLE") from exc
        payload = _open_intent(self.secret, intent, addr, now)
        if not isinstance(otp, str) or not re.fullmatch(r"[0-9]{6,8}", otp):
            raise FunnelGate("INVALID_VERIFICATION_CODE", 400)
        who = self.identity.verify_otp(addr, otp)
        uid = _uuid(who.user_id)
        if normalize_email(who.email) != addr or _timestamp(who.verified_at_utc) > now + timedelta(seconds=30):
            raise FunnelGate("IDENTITY_UNVERIFIED", 403)
        try:
            if self.suppression.is_suppressed(addr, uid):
                raise FunnelGate("ADDRESS_SUPPRESSED", 403)
        except FunnelGate:
            raise
        except Exception as exc:
            raise FunnelGate("SUPPRESSION_CHECK_UNAVAILABLE") from exc
        record = ConsentRecord(user_id=uid, email=addr, event_id=payload["event_id"],
                               tickers=tuple(payload["tickers"]), scope=SCOPE,
                               verified_at_utc=now.isoformat(), intent_id=payload["nonce"],
                               first_touch=first_touch(payload["first_touch"]))
        try:
            confirmation = self.consent.confirm(record)
            confirmed = confirmation.record
        except FunnelGate:
            raise
        except Exception as exc:
            raise FunnelGate("CONSENT_WRITE_UNCONFIRMED") from exc
        if (confirmed.user_id != uid or confirmed.event_id != record.event_id or
                confirmed.scope != SCOPE or confirmed.revoked_at_utc):
            raise FunnelGate("CONSENT_WRITE_UNCONFIRMED")
        return {"status": "verified" if confirmation.created else "already_verified",
                "event_id": confirmed.event_id, "scope": SCOPE,
                "attribution": analytics_receipt(confirmed)}

    def revoke(self, *, user_id: str, event_id: str, now: datetime) -> dict[str, str]:
        """Called AFTER existing signed unsubscribe verifier; never trusts public user_id."""
        uid, event_id = _uuid(user_id), _event_id(event_id)
        if not self.consent.available():
            raise FunnelGate("CONSENT_OWNER_NOT_READY")
        try:
            changed = self.consent.revoke(uid, event_id, _utc(now).isoformat())
        except Exception as exc:
            raise FunnelGate("CONSENT_REVOKE_UNCONFIRMED") from exc
        return {"status": "unsubscribed", "event_id": event_id,
                "changed": "yes" if changed else "no"}

    def deliver(self, revision: PublicRevision, *, limit: int = 50, now: datetime) -> list[dict[str, str]]:
        """Explicit call by existing approved scheduler/producer; NEVER a public route.

        No retry on uncertain sender effects. The incumbent mailer email_log unique
        idem_key is the only delivery claim, so a restarter cannot double-send.
        """
        now = _utc(now)
        _validate_revision(revision)
        revision_as_of = _timestamp(revision.as_of_utc)
        if revision_as_of > now + timedelta(seconds=30):
            raise FunnelGate("FUTURE_SOURCE_REVISION", 400)
        # RevisionAuthority.is_current() attests the latest known generation,
        # not its age. Never send an old issuer observation as a new update.
        if now - revision_as_of > PUBLIC_REVISION_MAX_AGE:
            raise FunnelGate("STALE_SOURCE_REVISION", 409)
        if not 1 <= limit <= 100:
            raise FunnelGate("INVALID_BATCH_LIMIT", 400)
        if not self.consent.available():
            raise FunnelGate("CONSENT_OWNER_NOT_READY")
        if not self.sender.permitted():
            raise FunnelGate("SEND_BLOCKED")
        try:
            if self.revisions.is_current(revision.event_id, revision.generation) is not True:
                raise FunnelGate("OUTDATED_OR_UNVERIFIED_REVISION", 409)
            subscribers = self.consent.interested(revision.event_id, limit)
        except FunnelGate:
            raise
        except Exception as exc:
            raise FunnelGate("DELIVERY_ROSTER_UNAVAILABLE") from exc
        out: list[dict[str, str]] = []
        for rec in subscribers[:limit]:
            try:
                current = self.consent.current(rec.user_id, revision.event_id)
                if (current is None or current.revoked_at_utc or current.scope != SCOPE or
                        current.intent_id != rec.intent_id or revision.ticker not in current.tickers):
                    state = "SUPPRESSED"
                elif _timestamp(current.verified_at_utc) >= _timestamp(revision.as_of_utc):
                    state = "NOT_SECOND_VALUE"
                elif self.suppression.is_suppressed(normalize_email(current.email), _uuid(current.user_id)):
                    state = "SUPPRESSED"
                elif self.revisions.is_current(revision.event_id, revision.generation) is not True:
                    state = "OUTDATED_OR_UNVERIFIED_REVISION"
                else:
                    idem = f"catalyst:{revision.event_id}:{revision.generation}:{current.user_id}"
                    raw = self.sender.deliver(current, revision, idem)
                    state = {"sent": "PROVIDER_ACCEPTED", "duplicate": "ALREADY_CLAIMED",
                             "suppressed": "SUPPRESSED", "skipped_no_smtp": "SEND_BLOCKED",
                             "queued": "QUEUED_NOT_SENT", "failed": "SEND_FAILED",
                             "effect_unknown": "EFFECT_UNKNOWN"}.get(raw, "SEND_UNCONFIRMED")
            except Exception:  # transport could have fired; never call it a safe failure
                state = "EFFECT_UNKNOWN"
            out.append({"user_ref": analytics_receipt(rec)["user_ref"], "state": state,
                        "event_id": revision.event_id, "generation": str(revision.generation),
                        **first_touch(rec.first_touch)})
            if state == "EFFECT_UNKNOWN":  # hold batch until original ledger reconciles
                break
        return out


def format_revision(rev: PublicRevision, unsubscribe_url: str) -> tuple[str, str, str]:
    """Pure rights-qualified copy; correction/retraction never reuses old claims."""
    _validate_revision(rev)
    if not unsubscribe_url.startswith("https://"):
        raise FunnelGate("UNSUBSCRIBE_LINK_UNAVAILABLE")
    message = (rev.correction_note if rev.correction == "retracted" else
               f"{rev.correction_note} — {rev.what_changed}" if rev.correction == "corrected"
               else rev.what_changed)
    heading = ("Correction: " if rev.correction != "none" else "Update: ") + rev.headline
    lines = [heading, message, f"Evidence as of {rev.as_of_utc}", "Sources:"]
    lines.extend(rev.source_urls)
    lines.append("Unsubscribe: " + unsubscribe_url)
    safe_text = "\n".join(lines)
    links = "".join(f'<li><a href="{html.escape(link, quote=True)}">Source</a></li>'
                    for link in rev.source_urls)
    safe_html = (f"<h2>{html.escape(heading)}</h2><p>{html.escape(message)}</p>"
                 f"<p>Evidence as of {html.escape(rev.as_of_utc)}</p><ul>{links}</ul>"
                 f'<p><a href="{html.escape(unsubscribe_url, quote=True)}">Unsubscribe</a></p>')
    return heading, safe_html, safe_text
