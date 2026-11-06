"""SNI-local DRAFT share-class duplicate guard (A36 class-duplicate refusal).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
pack members and owner-declared share-class pairs shaped like the Stock
Identity owner's issuer/security/share-class records. It does not
re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation. Identity ids are caller-supplied opaque strings
owned by Stock Identity / Data OS; this guard never mints, derives, or
guesses canonical HK/US issuer or security identifiers from a ticker,
name, code, or CIK. Two securities of one issuer count as one economic
exposure only when an owner-declared pair covers exactly those
securities and declares dedup true; the guard never decides sameness
itself. Unknown identity stays UNRESOLVED / null, and a blank issuer_id
is never filled from a pair, a sibling member, or anything else.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. An undeclared
same-issuer duplicate is refused, not silently de-duplicated.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path. Every authority flag is literal false, and a caller that tries to
set any of them true is refused (raise). This guard makes no causal or
news-impact claim (A24), invents no default exposure or probability
(A25), and is a descriptive refusal contract, not a signal, score, or
forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

REASONS: tuple[str, ...] = (
    "PACK_MISSING",
    "MEMBER_UNSOURCED",
    "SECURITY_ID_MISSING",
    "ISSUER_ID_MISSING",
    "DUPLICATE_SECURITY",
    "PAIR_UNSOURCED",
    "PAIR_INVALID",
    "ISSUER_DUPLICATE_UNDECLARED",
    "PAIR_ISSUER_MISMATCH",
    "PAIR_NOT_DEDUPLICATED",
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
class ClassDuplicateVerdict:
    """Descriptive duplicate refusal. Carries no weight, score, or exposure."""

    allowed: bool
    reasons: tuple[str, ...]
    duplicate_issuers: tuple[str, ...]
    counted_security_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)
        object.__setattr__(self, "duplicate_issuers", tuple(self.duplicate_issuers))
        if frozen:
            object.__setattr__(self, "counted_security_ids", ())
        else:
            object.__setattr__(
                self, "counted_security_ids", tuple(self.counted_security_ids)
            )

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """An opaque-text id / ref is present iff it is a non-empty string
    that does not begin or end with whitespace. None, ``""``, ``"  "``, ``1``, ``True``,
    ``1.0``, ``b"id"``, ``["id"]``, and any other object are ABSENT and
    never match each other. Applied to member ``security_id`` /
    ``issuer_id`` / ``owner_ref`` and pair ``pair_id`` / ``owner_ref``;
    numbers (the ``dedup`` bool flag), the security-id tuple container,
    and the pack/dedup container keep their existing checks and are NOT
    routed through this helper.

    FAMILY TEXT RULE v2 (seat ruling): a string that begins or ends with
    whitespace is ABSENT, exactly like a whitespace-only string, so a
    padded id can never pass as a different valid id. The check uses no
    normalisation method (``.strip()`` / ``.lower()`` / ``.upper()`` /
    ``.casefold()`` / ``.replace()``), which keeps the family's
    no-normalisation static scans green.
    """
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


def _pair_shape_ok(sids: object) -> bool:
    """security_ids must be exactly two distinct non-blank strings."""
    if not isinstance(sids, (tuple, list)):
        return False
    if len(sids) != 2:
        return False
    for sid in sids:
        if not _text_present(sid):
            return False
    return sids[0] != sids[1]


def check_class_duplicates(
    pack: Sequence[Mapping[str, object]] | None,
    *,
    share_class_pairs: Sequence[Mapping[str, object]],
) -> ClassDuplicateVerdict:
    """Refuse a pack or aggregate holding two or more securities of one
    issuer unless an owner-declared share-class pair covers exactly those
    securities and declares them one economic exposure (dedup true).

    Reports which securities to count: the pack-order tuple of member
    security ids with the non-primary security of every applied declared
    pair dropped. duplicate_issuers lists every issuer carried by more
    than one member whether or not the duplicate is declared. The verdict
    is invariant to the order of share_class_pairs; a structurally bad
    pair record refuses even when it covers no pack member, and three
    classes of one issuer can never be covered by a two-security pair,
    so they always refuse.
    """
    refuse_nonfalse_authority()
    if pack is not None and not isinstance(pack, (list, tuple)):
        raise TypeError("pack must be a list, a tuple, or None")
    if not isinstance(share_class_pairs, (list, tuple)):
        raise TypeError("share_class_pairs must be a list or tuple")

    reasons: list[str] = []
    member_security_ids: list[object] = []
    issuer_groups: dict[str, list[object]] = {}

    if pack is None or len(pack) == 0:
        reasons.append("PACK_MISSING")
    else:
        seen: set[str] = set()
        for member in pack:
            if not isinstance(member, Mapping):
                raise TypeError("pack member must be a Mapping")
            security_id = member.get("security_id")
            issuer_id = member.get("issuer_id")
            owner_ref = member.get("owner_ref")
            if not _text_present(owner_ref):
                reasons.append("MEMBER_UNSOURCED")
            if not _text_present(security_id):
                reasons.append("SECURITY_ID_MISSING")
            else:
                if security_id in seen:
                    reasons.append("DUPLICATE_SECURITY")
                seen.add(security_id)
            member_security_ids.append(security_id)
            if not _text_present(issuer_id):
                reasons.append("ISSUER_ID_MISSING")
            else:
                issuer_groups.setdefault(issuer_id, []).append(security_id)

    covering: dict[str, list[Mapping[str, object]]] = {}
    for pair in share_class_pairs:
        if not isinstance(pair, Mapping):
            raise TypeError("share class pair must be a Mapping")
        pair_id = pair.get("pair_id")
        pair_owner_ref = pair.get("owner_ref")
        unsourced = not _text_present(pair_id) or not _text_present(pair_owner_ref)
        if unsourced:
            reasons.append("PAIR_UNSOURCED")
        sids = pair.get("security_ids")
        shape_ok = _pair_shape_ok(sids)
        primary = pair.get("primary_security_id")
        primary_ok = shape_ok and _text_present(primary) and primary in sids
        if not shape_ok or not primary_ok:
            reasons.append("PAIR_INVALID")
        if unsourced or not shape_ok or not primary_ok:
            continue
        sid_set = frozenset(sids)
        for issuer_id, group in issuer_groups.items():
            if len(group) > 1 and frozenset(group) == sid_set:
                covering.setdefault(issuer_id, []).append(pair)

    dropped: set[str] = set()
    for issuer_id in sorted(issuer_groups):
        group = issuer_groups[issuer_id]
        if len(group) < 2:
            continue
        covered = covering.get(issuer_id, ())
        if not covered:
            reasons.append("ISSUER_DUPLICATE_UNDECLARED")
            continue
        for pair in covered:
            if pair.get("issuer_id") != issuer_id:
                reasons.append("PAIR_ISSUER_MISMATCH")
                continue
            if pair.get("dedup") is not True:
                reasons.append("PAIR_NOT_DEDUPLICATED")
                continue
            sids = pair.get("security_ids")
            primary = pair.get("primary_security_id")
            for sid in sids:
                if sid != primary:
                    dropped.add(sid)

    frozen = _freeze_reasons(reasons)
    duplicate_issuers = tuple(
        sorted(iss for iss, group in issuer_groups.items() if len(group) > 1)
    )
    counted: tuple[str, ...]
    if frozen:
        counted = ()
    else:
        counted = tuple(sid for sid in member_security_ids if sid not in dropped)
    return ClassDuplicateVerdict(
        allowed=not frozen,
        reasons=frozen,
        duplicate_issuers=duplicate_issuers,
        counted_security_ids=counted,
    )