"""SNI-local DRAFT identity-binding-guard contract (A03/A04 listing bind).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
listing, security, and issuer records from Data OS identity / Stock
Identity (caller-supplied opaque listing_id, security_id, issuer_id,
owner_ref, currency, available_at, display_code, display_name). It does
not re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or qledger/Evaluation.
Identity ids are caller-supplied opaque strings owned by Stock Identity /
Data OS; this guard never mints, derives, or guesses canonical HK/US
issuer or security identifiers from a ticker, name, code, or CIK.
Unknown identity stays UNRESOLVED / null. A null issuer stays null: the
verdict issuer_id is never filled from the request, listing, display
fields, or anywhere else.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. A missing or
inconsistent link is refused, not bound.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Every authority flag is literal false. A caller that tries to set any of
them true is refused (raise). Residuals and stress statistics stay
descriptive; this guard makes no causal or news-impact claim (A24). An
unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a signal,
score, or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping

REASONS: tuple[str, ...] = (
    "NULL_ISSUER_REFUSED",
    "LISTING_RECORD_MISSING",
    "SECURITY_RECORD_MISSING",
    "ISSUER_RECORD_MISSING",
    "OWNER_REF_MISSING",
    "LISTING_ID_MISMATCH",
    "LISTING_SECURITY_MISMATCH",
    "SECURITY_ISSUER_MISMATCH",
    "REQUEST_ISSUER_MISMATCH",
    "CURRENCY_MISMATCH",
    "NOT_AVAILABLE_AS_OF",
    "ID_LOOKS_DERIVED",
)

AUTHORITY_FLAGS: Mapping[str, bool] = MappingProxyType(
    {
        "rank_authority": False,
        "gate_authority": False,
        "size_authority": False,
        "signal_authority": False,
        "escalation_authority": False,
        "trade_authority": False,
    }
)

_ID_KEYS: tuple[str, ...] = ("listing_id", "security_id", "issuer_id")
_DISPLAY_KEYS: tuple[str, ...] = ("display_code", "display_name")


def refuse_nonfalse_authority(flags: Mapping[str, object] | None = None) -> None:
    """Refuse any authority flag that is not literal False.

    Idiom copied from research/single_name_intelligence/event_response/s2_seal.py
    (refuse_nonfalse_authority); this module does not import that owner.
    """
    for key, value in AUTHORITY_FLAGS.items():
        if value is not False:
            raise ValueError(
                f"AUTHORITY_FLAGS[{key!r}] is {value!r}; every authority flag "
                "must be literal False"
            )
    if flags is None:
        return
    if not isinstance(flags, Mapping):
        raise ValueError("authority flags is not a mapping")
    for key, value in flags.items():
        if value is not False:
            raise ValueError(
                f"authority_flags[{key!r}] is {value!r}; "
                "every authority flag must be literal False"
            )


@dataclass(frozen=True)
class IdentityBindingVerdict:
    """Descriptive identity-bind refusal. Carries no minted identifier."""

    allowed: bool
    reasons: tuple[str, ...]
    listing_id: str | None
    security_id: str | None
    issuer_id: str | None

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _blank(value: object) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    return False


def _text_present(value: object) -> bool:
    """FAMILY TEXT RULE v2 (seat ruling).

    A field the module documents as an id, ref, code, label, owner
    reference or other opaque text counts as present ONLY when this helper
    returns True. Anything else (None, ``""``, whitespace-only, leading or
    trailing whitespace, int, float, bool, bytes, list, dict, set, or any
    other object) is ABSENT and maps to the SAME refusal reason the module
    already emits for a blank value of that field.

    A string that begins or ends with whitespace is ABSENT, exactly like a
    whitespace-only or empty string, so a padded id can never pass as a
    different valid id. The check uses no normalisation method
    (``.strip()`` / ``.lower()`` / ``.upper()`` / ``.casefold()`` /
    ``.replace()``); its only calls are ``isinstance`` and ``.isspace()``,
    which keeps the family's no-normalisation static scans green.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _present(fact: Mapping[str, object], key: str) -> bool:
    return not _blank(fact.get(key))


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _as_date(text: object) -> date | None:
    if not isinstance(text, str) or len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _as_datetime(text: object) -> datetime | None:
    if not isinstance(text, str) or text == "":
        return None
    if len(text) == 10:
        parsed = _as_date(text)
        if parsed is None:
            return None
        return datetime(parsed.year, parsed.month, parsed.day)
    body = text
    if body.endswith("Z"):
        body = body[:-1]
    try:
        return datetime.fromisoformat(body)
    except ValueError:
        return None


def _aware_datetime(text: object) -> datetime | None:
    """Timezone-aware parse. Naive values, including date-only, refuse."""
    if not isinstance(text, str) or text == "":
        return None
    body: object = text
    if text.endswith("Z"):
        body = text[:-1] + "+00:00"
    parsed = _as_datetime(body)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _available_as_of(available_at: object, as_of: object) -> bool:
    left = _aware_datetime(available_at)
    right = _aware_datetime(as_of)
    if left is None or right is None:
        return False
    return left <= right


def _opaque_id(body: Mapping[str, object] | None, key: str) -> str | None:
    if body is None:
        return None
    value = body.get(key)
    if _text_present(value):
        return value
    return None


def _collected_ids(
    request: Mapping[str, object],
    listing: Mapping[str, object] | None,
    security: Mapping[str, object] | None,
    issuer: Mapping[str, object] | None,
) -> list[str]:
    found: list[str] = []
    for body in (request, listing, security, issuer):
        if not isinstance(body, Mapping):
            continue
        for key in _ID_KEYS:
            value = body.get(key)
            if isinstance(value, str):
                found.append(value)
    return found


def _display_needles(listing: Mapping[str, object]) -> list[str]:
    needles: list[str] = []
    for key in _DISPLAY_KEYS:
        value = listing.get(key)
        if isinstance(value, str) and len(value) >= 3:
            needles.append(value)
    return needles


def _id_pair_equal(left: object, right: object) -> bool:
    """Equality check for two caller-supplied ids (X8C-12 FAMILY TEXT RULE).

    Equality is evaluated only after both sides pass ``_text_present``. A
    non-text side is ABSENT and never equal to anything (so ``1``, ``True``
    and ``1.0`` never match each other and never collide). Two ABSENT sides
    are also not equal, which keeps a record whose value is missing/mistyped
    from being treated as matching the rest of the chain.
    """
    if not _text_present(left) or not _text_present(right):
        return False
    return left == right


def _id_looks_derived(
    request: Mapping[str, object],
    listing: Mapping[str, object] | None,
    security: Mapping[str, object] | None,
    issuer: Mapping[str, object] | None,
) -> bool:
    """Substring match against ``_collected_ids``.

    SEAT RULING (X8C-02): the matcher uses a substring rule with a 3-character
    minimum needle length; this is intentional, not a defect. Owner ids are
    opaque caller-supplied strings owned by Stock Identity / Data OS, and an
    id that embeds a display code or display-name substring goes to human
    review rather than auto-pass — false refusals are the fail-closed direction
    under program law. A 2-character display code never enters the needle set
    (see ``_display_needles``). False positives are accepted by design.
    """
    if listing is None:
        return False
    needles = _display_needles(listing)
    if not needles:
        return False
    for ident in _collected_ids(request, listing, security, issuer):
        for needle in needles:
            if needle in ident:
                return True
    return False


def _verdict(
    reasons: list[str],
    listing_id: str | None,
    security_id: str | None,
    issuer_id: str | None,
) -> IdentityBindingVerdict:
    frozen = _freeze_reasons(reasons)
    return IdentityBindingVerdict(
        allowed=not frozen,
        reasons=frozen,
        listing_id=listing_id,
        security_id=security_id,
        issuer_id=issuer_id,
    )


def bind_identity(
    request: Mapping[str, object],
    *,
    listing: Mapping[str, object] | None,
    security: Mapping[str, object] | None,
    issuer: Mapping[str, object] | None,
    as_of: object,
) -> IdentityBindingVerdict:
    """Refuse a listing-to-security-to-issuer bind unless every link is an
    owner record, the chain is consistent, currencies match, and a null
    issuer stays null.

    Reports every applicable reason, de-duplicated, in REASONS order.
    Verdict issuer_id is taken only from the security record (or None when
    the security record is missing). It is never filled from the request,
    listing, or display fields.
    """
    refuse_nonfalse_authority()
    if not isinstance(request, Mapping):
        raise TypeError("request must be a Mapping")
    if listing is not None and not isinstance(listing, Mapping):
        raise TypeError("listing must be a Mapping or None")
    if security is not None and not isinstance(security, Mapping):
        raise TypeError("security must be a Mapping or None")
    if issuer is not None and not isinstance(issuer, Mapping):
        raise TypeError("issuer must be a Mapping or None")

    reasons: list[str] = []
    needs_issuer = request.get("operation_needs_issuer", True)
    sec_issuer_id: object = None
    if security is not None:
        sec_issuer_id = security.get("issuer_id")

    if security is not None and sec_issuer_id is None and needs_issuer is not False:
        reasons.append("NULL_ISSUER_REFUSED")
    if listing is None:
        reasons.append("LISTING_RECORD_MISSING")
    if security is None:
        reasons.append("SECURITY_RECORD_MISSING")
    if issuer is None and security is not None and sec_issuer_id is not None:
        reasons.append("ISSUER_RECORD_MISSING")

    for record in (listing, security, issuer):
        if record is not None and not _text_present(record.get("owner_ref")):
            reasons.append("OWNER_REF_MISSING")

    if listing is not None:
        if not _id_pair_equal(request.get("listing_id"), listing.get("listing_id")):
            reasons.append("LISTING_ID_MISMATCH")
    if listing is not None and security is not None:
        if not _id_pair_equal(listing.get("security_id"), security.get("security_id")):
            reasons.append("LISTING_SECURITY_MISMATCH")
    if security is not None and issuer is not None:
        if not _id_pair_equal(security.get("issuer_id"), issuer.get("issuer_id")):
            reasons.append("SECURITY_ISSUER_MISMATCH")
    if security is not None:
        request_issuer_id = request.get("issuer_id")
        if request_issuer_id is not None and not _id_pair_equal(request_issuer_id, sec_issuer_id):
            reasons.append("REQUEST_ISSUER_MISMATCH")
    if listing is not None:
        if not _id_pair_equal(request.get("currency"), listing.get("currency")):
            reasons.append("CURRENCY_MISMATCH")

    for record in (listing, security, issuer):
        if record is not None and not _available_as_of(record.get("available_at"), as_of):
            reasons.append("NOT_AVAILABLE_AS_OF")

    if _id_looks_derived(request, listing, security, issuer):
        reasons.append("ID_LOOKS_DERIVED")

    listing_id = _opaque_id(listing, "listing_id")
    security_id = _opaque_id(security, "security_id")
    issuer_id: str | None
    if security is None:
        issuer_id = None
    else:
        raw_issuer = security.get("issuer_id")
        if _text_present(raw_issuer):
            issuer_id = raw_issuer
        else:
            issuer_id = None

    return _verdict(reasons, listing_id, security_id, issuer_id)
