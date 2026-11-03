"""Fresh Macro authentication/product checks for the Options use consumer.

No HTTP route, rights authority or Save grant is created here. The server supplies
the access token and a genuine source-use callback. Normal paywall caches/grace
are deliberately untouched. Each check uses the existing uncached, semaphore-
bounded Auth reader and the existing billing read; no refresh token is used.

``auth_epoch`` is the session_id claim of the token accepted by Auth, not a
fabricated observation time. getUser acceptance is NOT an immediate sign-out
revocation guarantee: that requires a separate auth.sessions check. These reads
are sequential observations, not an atomic authorization transaction.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import re
import time
from typing import Any
from urllib.parse import urlsplit
import uuid

from engine.intelligence_workspace.options_use import (
    OptionUseRefused, OptionUseRequest, resolve_authorized_option_selection,
)

_JWT = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\Z")


@dataclass(frozen=True, slots=True)
class OptionsPrincipal:
    principal_id: str
    principal_issuer: str
    auth_epoch: str
    expires_at: int


def _issuer() -> str:
    from app.main import SUPABASE_URL

    if type(SUPABASE_URL) is not str:
        raise ValueError("issuer unavailable")
    root = SUPABASE_URL.rstrip("/")
    parsed = urlsplit(root)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path
            or any(c.isspace() for c in root) or not root.isprintable() or len(root) > 240):
        raise ValueError("issuer unavailable")
    return root + "/auth/v1"


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("ambiguous claims")
        out[key] = value
    return out


def _nonfinite(_):
    raise ValueError("invalid claims")


def _uuid(value: Any) -> str:
    if type(value) is not str or str(uuid.UUID(value)) != value:
        raise ValueError("invalid identity")
    return value


def _authenticate(access_token: str):
    """Trust claims only AFTER the same token succeeds at the configured Auth."""
    try:
        if (type(access_token) is not str or not 1 <= len(access_token) <= 16384
                or not _JWT.fullmatch(access_token)):
            raise ValueError("invalid token")
        issuer = _issuer()
        from app import paywall

        ident = paywall._fetch_supabase_user(access_token)
        if ident.status != "ok" or type(ident.record) is not dict:
            raise ValueError("authentication unavailable")
        subject = _uuid(ident.uid)
        if (ident.record.get("id") != subject
                or ident.record.get("is_anonymous", False) is not False):
            raise ValueError("invalid identity")
        payload = access_token.split(".")[1]
        claims = json.loads(base64.b64decode(payload + "=" * (-len(payload) % 4),
                                           altchars=b"-_", validate=True).decode("utf-8"),
                            object_pairs_hook=_unique, parse_constant=_nonfinite)
        if type(claims) is not dict:
            raise ValueError("invalid claims")
        if (claims.get("sub") != subject or claims.get("iss") != issuer
                or claims.get("role") != "authenticated"
                or claims.get("is_anonymous", False) is not False):
            raise ValueError("identity mismatch")
        session = _uuid(claims.get("session_id"))
        expiry = claims.get("exp")
        if type(expiry) is not int or expiry <= time.time():
            raise ValueError("expired token")
        return OptionsPrincipal(subject, issuer, session, expiry), ident.email
    except Exception:
        # Never echo JWTs, records, upstream errors or local claim values.
        raise OptionUseRefused("authentication_unavailable") from None


def resolve_options_principal(access_token: str) -> OptionsPrincipal:
    """One uncached Auth observation; no entitlement, rights or returned token."""
    return _authenticate(access_token)[0]


def fresh_options_entitlement(request: OptionUseRequest, *, access_token: str) -> bool:
    """Fresh check of this exact subject/issuer/session, no cache/outage grace.

    The product predicate matches Terminal optionsReadAccess: the exact feature
    or the private unlimited tier/allowlist. Status and paid-tier guesses do not
    replace the existing product authority. This answers product access ONLY.
    """
    try:
        if type(request) is not OptionUseRequest:
            return False
        principal, email = _authenticate(access_token)
        if (request.principal_id != principal.principal_id
                or request.principal_issuer != principal.principal_issuer
                or request.auth_epoch != principal.auth_epoch):
            return False
        return _fresh_product_allowed(principal, email)
    except Exception:
        return False


def _fresh_product_allowed(principal: OptionsPrincipal, email: str) -> bool:
    """The existing uncached Terminal Options predicate, shared by read consumers."""
    from app import billing, paywall

    entitlement = billing.read_entitlement(principal.principal_id)
    if type(entitlement) is not dict:
        return False
    features = entitlement.get("features")
    tier = entitlement.get("tier")
    allowed = ((type(features) is list and "terminal_live_options" in features)
               or (type(tier) is str and tier.strip().lower() == "unlimited")
               or (type(email) is str and bool(email)
                   and paywall._operator_unlimited(email) is True))
    return bool(allowed and time.time() < principal.expires_at)


def resolve_entitled_options_principal(access_token: str) -> OptionsPrincipal:
    """Fresh existing Auth + Options product access for a private read.

    This grants no matrix/source-use permission, Save, quote, or trading action.
    The same product predicate is used by fresh_options_entitlement above.
    """
    principal, email = _authenticate(access_token)
    try:
        if _fresh_product_allowed(principal, email):
            return principal
    except Exception:
        pass
    raise OptionUseRefused("entitlement_unavailable") from None


def resolve_authenticated_option_selection(
    ref, matrix, selection, *, access_token: str, vendor: str, action: str, aliases,
    security_master, root_evidence, source_use_decision=None, clock=None,
):
    """Compose server auth with the landed exact-selection/source-use consumer.

    The caller supplies the real server rights interface, never a browser policy.
    Missing rights stays closed before any auth call. Authentication is repeated
    inside the entitlement callback after selection validation; a session change,
    denial or provider failure cannot borrow the earlier observation's success.
    """
    if not callable(source_use_decision):
        raise OptionUseRefused("callback_invalid")
    principal = resolve_options_principal(access_token)
    return resolve_authorized_option_selection(
        ref, matrix, selection, vendor=vendor,
        principal_id=principal.principal_id,
        principal_issuer=principal.principal_issuer, auth_epoch=principal.auth_epoch,
        action=action, aliases=aliases, security_master=security_master,
        root_evidence=root_evidence, clock=clock,
        fresh_entitlement=lambda request: fresh_options_entitlement(
            request, access_token=access_token),
        source_use_decision=source_use_decision,
    )
