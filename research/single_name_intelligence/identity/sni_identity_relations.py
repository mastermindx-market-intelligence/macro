"""SNI-local DRAFT identity RELATIONSHIP contract.

This module consumes owner-supplied counter fields and receipts. It does not
re-implement Stock Identity, Data OS identity, Company Event/Earnings, FIF,
Capital Structure, Options, Research Vault, or qledger/Evaluation. Canonical
issuer and security identifiers are caller-supplied opaque strings owned by
Stock Identity / Data OS; this module never constructs, mints, derives, or
guesses them from a ticker, name, code, or CIK. Unknown identity stays
unresolved (null).

R1-gated DRAFT: not registered, no product surface. Every authority flag stays
false. Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path; callers that try to set an authority flag true are refused.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Iterable

_AUTHORITY_FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

AUTHORITY_FLAGS = {
    "rank_authority": False,
    "gate_authority": False,
    "size_authority": False,
    "signal_authority": False,
    "escalation_authority": False,
    "trade_authority": False,
}

_HEX = "0123456789abcdef"


class RelationRefused(Exception):
    """Raised when a relation, receipt, or id-dependent op is refused."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def refuse_authority(**flags: bool) -> None:
    """Refuse any attempt to set an authority flag true."""
    for name in _AUTHORITY_FLAG_NAMES:
        if flags.get(name, False):
            raise RelationRefused(
                "AUTHORITY_FORBIDDEN",
                f"{name} must stay false; this draft does not feed that path",
            )
    extra = set(flags) - set(_AUTHORITY_FLAG_NAMES)
    if extra:
        raise RelationRefused(
            "AUTHORITY_FORBIDDEN",
            "unknown authority flag: " + ", ".join(sorted(extra)),
        )


@dataclass(frozen=True)
class CounterRef:
    """One trading counter as the owner stated it.

    Equality is the full tuple. local_code is stored verbatim: no padding,
    alias, or exchange normalization. security_id is an opaque caller-supplied
    string or None (unresolved); this type never fills it in.
    """

    venue_mic: str
    local_code: str
    currency: str
    security_id: str | None
    security_id_owner: str

    def key(self) -> tuple:
        return (
            self.venue_mic,
            self.local_code,
            self.currency,
            self.security_id,
            self.security_id_owner,
        )


class RelationKind(Enum):
    ADS_OF = "ADS_OF"
    DUAL_COUNTER_OF = "DUAL_COUNTER_OF"
    SAME_ISSUER_GROUP = "SAME_ISSUER_GROUP"
    ALIAS_OF = "ALIAS_OF"

    def is_symmetric(self) -> bool:
        return self in (RelationKind.DUAL_COUNTER_OF, RelationKind.SAME_ISSUER_GROUP)

    def is_directed(self) -> bool:
        return self in (RelationKind.ADS_OF, RelationKind.ALIAS_OF)


@dataclass(frozen=True)
class Receipt:
    """Owner-issued receipt. digest is 64 lowercase hex; never computed here
    from an identity string.
    """

    receipt_id: str
    source_owner: str
    issued_at_utc: str
    expires_at_utc: str | None
    digest: str


@dataclass(frozen=True)
class Relation:
    kind: RelationKind
    a: CounterRef
    b: CounterRef
    ratio: Fraction | None
    receipt: Receipt
    valid_from_utc: str
    valid_to_utc: str | None


@dataclass
class StoredRow:
    """Append-only registry row. The Relation payload is never rewritten;
    supersession only fills superseded_by / supersede_reason.
    """

    record_id: str
    relation: Relation
    superseded_by: str | None = None
    supersede_reason: str | None = None


def _parse_utc(stamp: str) -> datetime.datetime:
    text = stamp
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def _endpoint_lists(rel: Relation) -> list[list]:
    a_list = list(rel.a.key())
    b_list = list(rel.b.key())
    if rel.kind.is_symmetric():
        def sort_key(item: list) -> tuple:
            return tuple("" if part is None else part for part in item)
        return sorted([a_list, b_list], key=sort_key)
    return [a_list, b_list]


def _ratio_token(ratio: Fraction | None) -> str | None:
    if ratio is None:
        return None
    return f"{ratio.numerator}/{ratio.denominator}"


def record_id(rel: Relation) -> str:
    payload = {
        "endpoints": _endpoint_lists(rel),
        "kind": rel.kind.value,
        "ratio": _ratio_token(rel.ratio),
        "receipt_id": rel.receipt.receipt_id,
        "valid_from": rel.valid_from_utc,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _endpoint_identity(rel: Relation):
    if rel.kind.is_symmetric():
        return (rel.kind, frozenset((rel.a.key(), rel.b.key())))
    return (rel.kind, (rel.a.key(), rel.b.key()))


def _check_digest(digest: str) -> None:
    if len(digest) != 64 or any(ch not in _HEX for ch in digest):
        raise RelationRefused("BAD_DIGEST", "receipt digest must be 64 lowercase hex characters")


def validate(rel: Relation) -> None:
    refuse_authority()
    if rel.a == rel.b:
        raise RelationRefused("SELF_RELATION", "a relation cannot bind a counter to itself")

    same_venue = rel.a.venue_mic == rel.b.venue_mic
    same_currency = rel.a.currency == rel.b.currency
    kind = rel.kind

    if kind is RelationKind.ALIAS_OF:
        if not same_venue:
            raise RelationRefused(
                "CROSS_BIND_VENUE",
                "ALIAS_OF requires the same venue_mic on both endpoints",
            )
        if not same_currency:
            raise RelationRefused(
                "CROSS_BIND_CURRENCY",
                "ALIAS_OF requires the same currency on both endpoints",
            )
        if rel.a.local_code != rel.b.local_code:
            stripped_a = rel.a.local_code.lstrip("0")
            stripped_b = rel.b.local_code.lstrip("0")
            if stripped_a == stripped_b:
                if rel.receipt.source_owner != "stock_identity":
                    raise RelationRefused(
                        "PADDING_MISMATCH",
                        "ALIAS_OF on zero-padded local_code variants is refused unless "
                        "receipt.source_owner is stock_identity; ids stay as the receipt carries them",
                    )
    elif kind is RelationKind.ADS_OF:
        if same_venue:
            raise RelationRefused(
                "CROSS_BIND_VENUE",
                "ADS_OF requires different venue_mic on the two endpoints",
            )
    elif kind is RelationKind.DUAL_COUNTER_OF:
        if not same_venue:
            raise RelationRefused(
                "CROSS_BIND_VENUE",
                "DUAL_COUNTER_OF requires the same venue_mic on both endpoints",
            )
        if same_currency:
            raise RelationRefused(
                "CROSS_BIND_CURRENCY",
                "DUAL_COUNTER_OF requires different currencies on the two endpoints",
            )

    if kind is RelationKind.ADS_OF:
        if rel.ratio is None:
            raise RelationRefused("RATIO_REQUIRED", "ADS_OF requires a ratio")
        if not isinstance(rel.ratio, Fraction) or rel.ratio <= 0:
            raise RelationRefused("RATIO_REQUIRED", "ADS_OF ratio must be a Fraction > 0")
    else:
        if rel.ratio is not None:
            raise RelationRefused(
                "RATIO_FORBIDDEN",
                f"{kind.value} forbids a ratio",
            )

    _check_digest(rel.receipt.digest)

    if rel.receipt.expires_at_utc is not None:
        if _parse_utc(rel.receipt.expires_at_utc) < _parse_utc(rel.valid_from_utc):
            raise RelationRefused(
                "RECEIPT_EXPIRED",
                "receipt.expires_at_utc is before relation valid_from_utc",
            )


def require_issuer_id(issuer_id: str | None, *, op: str) -> str:
    """Id-dependent operations refuse on null. Nothing substitutes a derived id."""
    if issuer_id is None:
        raise RelationRefused(
            "ISSUER_ID_REQUIRED",
            f"issuer_id is required for op={op}; unknown identity stays unresolved and is not derived",
        )
    return issuer_id


class RelationRegistry:
    """Append-only store of validated relations. Authority flags stay false."""

    rank_authority = False
    gate_authority = False
    size_authority = False
    signal_authority = False
    escalation_authority = False
    trade_authority = False

    def __init__(self) -> None:
        self._rows: list[StoredRow] = []
        self._by_id: dict[str, StoredRow] = {}
        for name in _AUTHORITY_FLAG_NAMES:
            object.__setattr__(self, name, False)

    def __setattr__(self, name: str, value: object) -> None:
        if name in _AUTHORITY_FLAG_NAMES and value:
            raise RelationRefused(
                "AUTHORITY_FORBIDDEN",
                f"{name} must stay false; this draft does not feed that path",
            )
        object.__setattr__(self, name, value)

    def rows(self) -> tuple[StoredRow, ...]:
        return tuple(self._rows)

    def row(self, rec_id: str) -> StoredRow:
        found = self._by_id.get(rec_id)
        if found is None:
            raise RelationRefused("UNKNOWN_RECORD", f"no row with record_id={rec_id}")
        return found

    def add(self, rel: Relation, **flags: bool) -> str:
        refuse_authority(**flags)
        validate(rel)
        rec_id = record_id(rel)
        if rec_id in self._by_id:
            raise RelationRefused("DUPLICATE", "same record_id already exists (count-once)")
        self._check_conflict(rel, ignore_record_id=None)
        return self._append(rel, rec_id)

    def supersede(self, old_record_id: str, new_rel: Relation, *, reason: str, **flags: bool) -> str:
        refuse_authority(**flags)
        old = self.row(old_record_id)
        if old.superseded_by is not None:
            raise RelationRefused(
                "ALREADY_SUPERSEDED",
                f"record {old_record_id} already superseded_by={old.superseded_by}",
            )
        validate(new_rel)
        new_id = record_id(new_rel)
        if new_id in self._by_id:
            raise RelationRefused("DUPLICATE", "same record_id already exists (count-once)")
        self._check_conflict(new_rel, ignore_record_id=old_record_id)
        old.superseded_by = new_id
        old.supersede_reason = reason
        self._append(new_rel, new_id)
        return new_id

    def active(self, as_of_utc: str) -> list[Relation]:
        as_of = _parse_utc(as_of_utc)
        out: list[Relation] = []
        for stored in self._rows:
            if stored.superseded_by is not None:
                continue
            rel = stored.relation
            if _parse_utc(rel.valid_from_utc) > as_of:
                continue
            if rel.valid_to_utc is not None and _parse_utc(rel.valid_to_utc) <= as_of:
                continue
            expires = rel.receipt.expires_at_utc
            if expires is not None and _parse_utc(expires) <= as_of:
                continue
            out.append(rel)
        return out

    def history(self, endpoint_key: tuple) -> list[Relation]:
        return [
            stored.relation
            for stored in self._rows
            if stored.relation.a.key() == endpoint_key or stored.relation.b.key() == endpoint_key
        ]

    def _append(self, rel: Relation, rec_id: str) -> str:
        stored = StoredRow(record_id=rec_id, relation=rel)
        self._rows.append(stored)
        self._by_id[rec_id] = stored
        return rec_id

    def _check_conflict(self, rel: Relation, ignore_record_id: str | None) -> None:
        ident = _endpoint_identity(rel)
        as_of = rel.valid_from_utc
        as_of_dt = _parse_utc(as_of)
        for stored in self._rows:
            if ignore_record_id is not None and stored.record_id == ignore_record_id:
                continue
            if stored.superseded_by is not None:
                continue
            other = stored.relation
            if _parse_utc(other.valid_from_utc) > as_of_dt:
                continue
            if other.valid_to_utc is not None and _parse_utc(other.valid_to_utc) <= as_of_dt:
                continue
            expires = other.receipt.expires_at_utc
            if expires is not None and _parse_utc(expires) <= as_of_dt:
                continue
            if _endpoint_identity(other) != ident:
                continue
            if other.ratio != rel.ratio or other.receipt.digest != rel.receipt.digest:
                raise RelationRefused(
                    "CONFLICT",
                    "an active relation of the same kind over the same endpoint set "
                    "exists with a different ratio or different receipt digest",
                )


def _counter_to_dict(counter: CounterRef) -> dict:
    return {
        "currency": counter.currency,
        "local_code": counter.local_code,
        "security_id": counter.security_id,
        "security_id_owner": counter.security_id_owner,
        "venue_mic": counter.venue_mic,
    }


def _counter_from_dict(payload: dict) -> CounterRef:
    return CounterRef(
        venue_mic=payload["venue_mic"],
        local_code=payload["local_code"],
        currency=payload["currency"],
        security_id=payload["security_id"],
        security_id_owner=payload["security_id_owner"],
    )


def _receipt_to_dict(receipt: Receipt) -> dict:
    return {
        "digest": receipt.digest,
        "expires_at_utc": receipt.expires_at_utc,
        "issued_at_utc": receipt.issued_at_utc,
        "receipt_id": receipt.receipt_id,
        "source_owner": receipt.source_owner,
    }


def _receipt_from_dict(payload: dict) -> Receipt:
    return Receipt(
        receipt_id=payload["receipt_id"],
        source_owner=payload["source_owner"],
        issued_at_utc=payload["issued_at_utc"],
        expires_at_utc=payload["expires_at_utc"],
        digest=payload["digest"],
    )


def _row_to_dict(row: StoredRow) -> dict:
    rel = row.relation
    return {
        "a": _counter_to_dict(rel.a),
        "b": _counter_to_dict(rel.b),
        "kind": rel.kind.value,
        "ratio": _ratio_token(rel.ratio),
        "receipt": _receipt_to_dict(rel.receipt),
        "record_id": row.record_id,
        "supersede_reason": row.supersede_reason,
        "superseded_by": row.superseded_by,
        "valid_from_utc": rel.valid_from_utc,
        "valid_to_utc": rel.valid_to_utc,
    }


def _relation_from_dict(payload: dict) -> Relation:
    ratio_raw = payload.get("ratio")
    ratio = None if ratio_raw is None else Fraction(ratio_raw)
    return Relation(
        kind=RelationKind(payload["kind"]),
        a=_counter_from_dict(payload["a"]),
        b=_counter_from_dict(payload["b"]),
        ratio=ratio,
        receipt=_receipt_from_dict(payload["receipt"]),
        valid_from_utc=payload["valid_from_utc"],
        valid_to_utc=payload["valid_to_utc"],
    )


def to_jsonl(registry: RelationRegistry) -> str:
    lines = []
    for row in sorted(registry.rows(), key=lambda item: item.record_id):
        lines.append(json.dumps(_row_to_dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def from_jsonl(text: str) -> RelationRegistry:
    registry = RelationRegistry()
    loaded: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        loaded.append(json.loads(line))
    loaded.sort(key=lambda item: item["record_id"])
    seen: set[str] = set()
    for payload in loaded:
        rel = _relation_from_dict(payload)
        validate(rel)
        rec_id = record_id(rel)
        stored_id = payload["record_id"]
        if stored_id != rec_id:
            raise RelationRefused(
                "BAD_DIGEST",
                "stored record_id does not match the canonical hash of the relation",
            )
        if rec_id in seen:
            raise RelationRefused("DUPLICATE", "same record_id already exists (count-once)")
        seen.add(rec_id)
        stored = StoredRow(
            record_id=rec_id,
            relation=rel,
            superseded_by=payload.get("superseded_by"),
            supersede_reason=payload.get("supersede_reason"),
        )
        registry._rows.append(stored)
        registry._by_id[rec_id] = stored
    return registry


def iter_record_ids(registry: RelationRegistry) -> Iterable[str]:
    return (row.record_id for row in registry.rows())
