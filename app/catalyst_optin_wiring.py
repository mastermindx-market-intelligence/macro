"""Flag-gated production wiring of the Catalyst opt-in funnel (B1 seam).

``configure_from_environment`` is the only production path that may call
``catalyst_optin.configure`` with a real owner-backed ``FunnelService``.  It
is inert unless BOTH ``CATALYST_PUBLIC_ENABLED`` and ``CATALYST_OPTIN_ENABLED``
are ``"1"``; it then requires the two HMAC secrets the funnel signs with to be
present and at least 32 characters long, a configured GoTrue identity
endpoint, and a consent owner that answers the v2 contract probe.  It injects
the real ``ScanReceiptAuthority`` explicitly — never the ``Unwired`` placeholder
— so a configured service can actually validate a scan receipt.

Every refusal leaves the router unconfigured (``503 CATALYST_INTEGRATION_NOT_
READY``) and logs only a bare reason code or exception type name: no
environment values, keys, URLs or addresses.

What this deliberately does NOT do: it never applies or provisions the consent
RPC contract (that SQL is review-only until its owner gate), never enables
mail delivery (``MAIL_CATALYST_ENABLED`` stays OFF and ``ExistingMailerDelivery``
keeps refusing), and grants no revision/rights authority: the
``RevisionAuthority`` injected here answers "not current / no rights" for every
revision, so ``deliver()`` can never send until the existing publication-rights
owner is explicitly bound (B2).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger("macro.api")

_MIN_SECRET_CHARS = 32
_REQUIRED_SECRETS = ("MAIL_UNSUB_SECRET", "CATALYST_SCAN_RECEIPT_SECRET")


class FailClosedRevisionAuthority:
    """No public revision is current and no rights snapshot exists.

    B2 binds the existing source/publication-rights owner here.  Until then the
    funnel can accept and verify opt-ins but ``deliver()`` refuses every
    revision, which is the fail-closed answer the lifecycle contract expects.
    """

    def is_current(self, event_id: str, generation: int) -> bool:
        return False

    def read_public_rights(self, revision: Any, at_utc: datetime) -> None:
        return None


def _switches_on() -> bool:
    return (os.environ.get("CATALYST_PUBLIC_ENABLED") == "1"
            and os.environ.get("CATALYST_OPTIN_ENABLED") == "1")


def _secret_present(name: str) -> bool:
    """Length-only check; the value is never read into a log or an exception."""
    return len(os.environ.get(name, "")) >= _MIN_SECRET_CHARS


def _identity_configured() -> bool:
    """Shape-only check: an https GoTrue endpoint and a non-empty publishable key
    exist on the same seams the funnel uses. It does not prove GoTrue is
    reachable; each request still fails closed (IDENTITY_VERIFICATION_UNAVAILABLE)."""
    try:
        from app.account_actions import _anon_key, _supabase  # noqa: PLC0415
        url, _service_role = _supabase()
        return bool(_anon_key()) and str(url or "").startswith("https://")
    except Exception:
        return False


def _refuse(reason: str, **fields: str) -> bool:
    from app import catalyst_optin  # noqa: PLC0415
    catalyst_optin.configure(None)
    extra = "".join(f" {key}={value}" for key, value in fields.items())
    logger.warning("catalyst optin wiring refused: reason=%s%s", reason, extra)
    return False


def configure_from_environment() -> bool:
    """Configure the owner-backed funnel when, and only when, production admits it.

    Returns True only when a service was actually injected; every refusal is a
    logged reason code and leaves the router unconfigured (fail closed).
    """
    from app import catalyst_optin  # noqa: PLC0415

    if not _switches_on():
        catalyst_optin.configure(None)
        return False
    for name in _REQUIRED_SECRETS:
        if not _secret_present(name):
            return _refuse("secret_not_configured", name=name)
    if not _identity_configured():
        return _refuse("identity_not_configured")
    try:
        from app.catalyst_scan_authority import ScanReceiptAuthority  # noqa: PLC0415
        service = catalyst_optin.build_existing_owner_service(
            FailClosedRevisionAuthority(), scan=ScanReceiptAuthority())
    except Exception as exc:  # noqa: BLE001
        return _refuse("build_failed", type=type(exc).__name__)
    if isinstance(service.scan, catalyst_optin.UnwiredScanAuthority):
        return _refuse("scan_authority_unwired")
    try:
        consent_ready = bool(service.consent.available())
    except Exception:  # noqa: BLE001
        consent_ready = False
    if not consent_ready:
        return _refuse("consent_owner_not_ready")
    catalyst_optin.configure(service)
    logger.info("catalyst optin wiring configured: scan=receipt_authority "
                "revisions=fail_closed delivery=%s",
                "permitted" if service.sender.permitted() else "refused")
    return True
