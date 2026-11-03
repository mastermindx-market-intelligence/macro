"""SNI-local DRAFT entitlement-guard contract (A18 pre-access refusal).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
entitlement records shaped like the Research Vault owner's entitlement
and full-text store (engine/research_vault/) together with
caller-supplied opaque account and document ids. It does not
re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation. Account and document ids are caller-supplied
opaque strings owned by their owners; this guard never mints, derives,
or guesses canonical HK/US issuer or security identifiers from a
ticker, name, code, or CIK. Unknown identity stays UNRESOLVED / null.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, index, redact, or repair any document. Access is decided
BEFORE any private document payload is loaded: the caller-supplied
loader runs exactly once, only on a private surface, and only after
every check has run and the verdict is allowed. A public surface never
receives full text; the loader is never called on public and never on
any refusal. Timestamps are ISO-8601 strings compared as timezone-aware
instants; a naive or unparseable timestamp refuses fail-closed and
never widens access (valid_to=None means the window is unbounded).

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path. Every authority flag is literal false. A caller that tries to set
any of them true is refused (raise). Residuals and stress statistics
stay descriptive; this guard makes no causal or news-impact claim
(A24). An unestimable family is outside this module; the guard never
invents a default 50/50 (A25). This is a descriptive refusal contract,
not a signal, score, or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from types import MappingProxyType
from typing import Callable, Mapping

SURFACES: tuple[str, ...] = ("private", "public")

REASONS: tuple[str, ...] = (
    "SURFACE_UNKNOWN",
    "AS_OF_INVALID",
    "PUBLIC_FULL_TEXT_FORBIDDEN",
    "ENTITLEMENT_MISSING",
    "ENTITLEMENT_REF_MISSING",
    "ACCOUNT_MISMATCH",
    "DOCUMENT_NOT_ENTITLED",
    "ENTITLEMENT_NOT_YET_VALID",
    "ENTITLEMENT_EXPIRED",
    "ENTITLEMENT_REVOKED",
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

_DOCUMENT_ID_CONTAINERS = (list, tuple, frozenset, set)


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
class AccessVerdict:
    """Descriptive entitlement refusal. Carries no entitlement record.

    payload is the loader's return value on a private allow; repr(verdict)
    never prints it.
    """

    allowed: bool
    reasons: tuple[str, ...]
    payload: object = field(default=None, repr=False)

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)
        if frozen and self.payload is not None:
            raise ValueError("a refused verdict cannot carry a payload")

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """True iff ``value`` is a non-empty ``str`` with no leading or trailing
    Unicode whitespace character (``str.isspace()``); equivalent to the
    standard leading / trailing whitespace predicate without hand-rolling
    an ASCII whitespace set."""
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _blank(value: object) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    return False


def _present(body: Mapping[str, object], key: str) -> bool:
    value = body.get(key)
    return isinstance(value, str) and not _blank(value)


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


def _document_entitled(document_id: object, document_ids: object) -> bool:
    if not isinstance(document_id, str) or _blank(document_id):
        return False
    if not isinstance(document_ids, _DOCUMENT_ID_CONTAINERS):
        return False
    return document_id in document_ids


def _add_window_reasons(
    reasons: list[str], entitlement: Mapping[str, object], as_of_dt: datetime
) -> None:
    valid_from = _aware_datetime(entitlement.get("valid_from"))
    if valid_from is None or as_of_dt < valid_from:
        reasons.append("ENTITLEMENT_NOT_YET_VALID")
    valid_to_raw = entitlement.get("valid_to")
    if valid_to_raw is not None:
        valid_to = _aware_datetime(valid_to_raw)
        if valid_to is None or as_of_dt >= valid_to:
            reasons.append("ENTITLEMENT_EXPIRED")
    revoked_raw = entitlement.get("revoked_at")
    if revoked_raw is not None:
        revoked_at = _aware_datetime(revoked_raw)
        if revoked_at is None or as_of_dt >= revoked_at:
            reasons.append("ENTITLEMENT_REVOKED")


def gate_access(
    request: Mapping[str, object],
    entitlement: Mapping[str, object] | None,
    *,
    as_of: str,
    loader: Callable[[object], object],
) -> AccessVerdict:
    """Refuse access before any private document payload is loaded.

    Every applicable reason is reported, de-duplicated, in REASONS
    order. The loader runs exactly once, only on a private surface and
    only on an allow; it is never called on public, never on any
    refusal, and never before every check has run.
    """
    refuse_nonfalse_authority()
    if not isinstance(request, Mapping):
        raise TypeError("request must be a Mapping")
    if entitlement is not None and not isinstance(entitlement, Mapping):
        raise TypeError("entitlement must be a Mapping or None")
    if not callable(loader):
        raise TypeError("loader must be callable")

    surface = request.get("surface")
    document_id = request.get("document_id")
    account_id = request.get("account_id")
    want_full_text = request.get("want_full_text")

    reasons: list[str] = []
    if surface not in SURFACES:
        reasons.append("SURFACE_UNKNOWN")

    as_of_dt = _aware_datetime(as_of)
    if as_of_dt is None:
        reasons.append("AS_OF_INVALID")

    if surface == "public":
        if want_full_text is not False:
            reasons.append("PUBLIC_FULL_TEXT_FORBIDDEN")
    elif surface == "private":
        if entitlement is None:
            reasons.append("ENTITLEMENT_MISSING")
        else:
            if not _text_present(entitlement.get("entitlement_ref")):
                reasons.append("ENTITLEMENT_REF_MISSING")
            entitlement_account_id = entitlement.get("account_id")
            account_match = (
                _text_present(account_id)
                and _text_present(entitlement_account_id)
                and account_id == entitlement_account_id
            )
            if not account_match:
                reasons.append("ACCOUNT_MISMATCH")
            if not _document_entitled(document_id, entitlement.get("document_ids")):
                reasons.append("DOCUMENT_NOT_ENTITLED")
            if as_of_dt is not None:
                _add_window_reasons(reasons, entitlement, as_of_dt)

    frozen = _freeze_reasons(reasons)
    payload = None
    if not frozen and surface == "private":
        payload = loader(document_id)
    return AccessVerdict(allowed=not frozen, reasons=frozen, payload=payload)