"""SNI-local DRAFT counter-relation guard contract (A02 dual counters).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
listing-relation records shaped like the Stock Identity owner's records
(relation_id, issuer_id, source_ref, available_at, and members carrying
listing_id, counter_kind, currency) together with a caller request
(issuer_id, left_listing_id, right_listing_id). It does not re-implement
Data OS identity, Company Event/Earnings, FIF, Capital Structure, Stock
Identity, Options, Research Vault, or qledger/Evaluation. Identity ids are
caller-supplied opaque strings owned by Stock Identity / Data OS; this
guard never mints, derives, or guesses canonical HK/US issuer or security
identifiers from a ticker, name, code, or CIK. Unknown identity stays
UNRESOLVED / null. The guard never creates a relation or a listing id; a
verdict's relation_id only echoes a caller-supplied relation_id.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. Two listings are
treated as counters of one issuer only when exactly one owner-sourced
relation, available as of the decision time, contains both listings with
declared counter kinds and currencies; anything else is refused, not
repaired.

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
from typing import Iterable, Mapping

REASONS: tuple[str, ...] = (
    "SAME_LISTING",
    "RELATION_SET_MISSING",
    "RELATION_NOT_AVAILABLE_AS_OF",
    "AMBIGUOUS_RELATION",
    "RELATION_ID_MISSING",
    "RELATION_UNSOURCED",
    "ISSUER_MISMATCH",
    "DUPLICATE_MEMBER",
    "COUNTER_KIND_UNKNOWN",
    "CURRENCY_UNDECLARED",
)

COUNTER_KINDS: tuple[str, ...] = (
    "ordinary",
    "ads",
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

_REASON_SET = frozenset(REASONS)
_COUNTER_KIND_SET = frozenset(COUNTER_KINDS)


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
class CounterRelationVerdict:
    """Descriptive counter-relation refusal. Carries no minted id or link."""

    allowed: bool
    reasons: tuple[str, ...]
    relation_id: str | None

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        for code in self.reasons:
            if code not in _REASON_SET:
                raise ValueError(
                    f"unknown reason code {code!r}; reasons must come from REASONS"
                )
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def relation_key(a: str, b: str) -> tuple[str, str]:
    """Sorted 2-tuple of the two listing ids; never alters either string."""
    return (a, b) if a <= b else (b, a)


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


def _members(relation: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    members = relation.get("members")
    if members is None:
        return ()
    if isinstance(members, (str, bytes, Mapping)):
        raise TypeError("relation members must be a sequence of mappings")
    out: list[Mapping[str, object]] = []
    for member in members:
        if not isinstance(member, Mapping):
            raise TypeError("each relation member must be a Mapping")
        out.append(member)
    return tuple(out)


def _contains_both(
    relation: Mapping[str, object], left: object, right: object
) -> bool:
    listing_ids = [member.get("listing_id") for member in _members(relation)]
    return (left in listing_ids) and (right in listing_ids)


def check_counter_relation(
    request: Mapping[str, object],
    relations: Iterable[Mapping[str, object]],
    *,
    as_of: str,
) -> CounterRelationVerdict:
    """Refuse to treat two listings as counters of one issuer unless exactly
    one owner-sourced relation, available as of the decision time, contains
    both listings with declared counter kinds and currencies.

    Reports every applicable reason, de-duplicated, in REASONS order.
    Swapping left_listing_id and right_listing_id yields an identical
    verdict. The guard never creates a relation or a listing id;
    relation_id comes only from the input. Ids and codes are compared as
    exact strings; a trailing-space or case variant is a mismatch.
    """
    refuse_nonfalse_authority()
    if not isinstance(request, Mapping):
        raise TypeError("request must be a Mapping")
    if relations is None or isinstance(relations, (str, bytes)):
        raise TypeError("relations must be an iterable of relation mappings")
    checked: list[Mapping[str, object]] = []
    for relation in relations:
        if not isinstance(relation, Mapping):
            raise TypeError("each relation must be a Mapping")
        checked.append(relation)

    left = request.get("left_listing_id")
    right = request.get("right_listing_id")
    if left == right:
        return CounterRelationVerdict(
            allowed=False, reasons=("SAME_LISTING",), relation_id=None
        )

    containing = [
        relation for relation in checked if _contains_both(relation, left, right)
    ]
    if not containing:
        return CounterRelationVerdict(
            allowed=False, reasons=("RELATION_SET_MISSING",), relation_id=None
        )
    if len(containing) > 1:
        return CounterRelationVerdict(
            allowed=False, reasons=("AMBIGUOUS_RELATION",), relation_id=None
        )

    relation = containing[0]
    reasons: list[str] = []

    available = _aware_datetime(relation.get("available_at"))
    decision = _aware_datetime(as_of)
    if available is None or decision is None or available > decision:
        reasons.append("RELATION_NOT_AVAILABLE_AS_OF")

    relation_id = relation.get("relation_id")
    if not _text_present(relation_id):
        reasons.append("RELATION_ID_MISSING")
    source_ref = relation.get("source_ref")
    if not _text_present(source_ref):
        reasons.append("RELATION_UNSOURCED")
    # FAMILY TEXT RULE v2: equality only between two present values (X9-04).
    rel_issuer, req_issuer = relation.get("issuer_id"), request.get("issuer_id")
    if not (_text_present(rel_issuer) and _text_present(req_issuer)
            and rel_issuer == req_issuer):
        reasons.append("ISSUER_MISMATCH")

    seen: list[object] = []
    for member in _members(relation):
        listing_id = member.get("listing_id")
        if listing_id in seen:
            reasons.append("DUPLICATE_MEMBER")
        else:
            seen.append(listing_id)
        if member.get("counter_kind") not in _COUNTER_KIND_SET:
            reasons.append("COUNTER_KIND_UNKNOWN")
        currency = member.get("currency")
        if not _text_present(currency):
            reasons.append("CURRENCY_UNDECLARED")

    frozen = _freeze_reasons(reasons)
    echo: str | None
    if _text_present(relation_id):
        echo = relation_id
    else:
        echo = None
    return CounterRelationVerdict(
        allowed=not frozen, reasons=frozen, relation_id=echo
    )