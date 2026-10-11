"""Read-only inspection of exact existing Options Hub payload bytes.

The incumbent caller supplies artifact receipts and source selection. Hashes prove
byte identity, not authenticity or licensing. Legacy vol/v1 never qualifies IV30,
quote quality or portfolio risk, even if ad-hoc certification fields are appended.
No I/O, collector, chain cache, publisher, clock service or source selector lives here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from math import fsum
from typing import Mapping

from engine.options_basket_aggregation import _aware, _digest, _number, _text


@dataclass(frozen=True)
class ArtifactReceipt:
    source_ref: str
    source_sha256: str
    known_at: datetime | None


_MAX_BYTES = 2 * 1024 * 1024
_REFUSAL = ["SOURCE_QUOTE_QUALITY_AND_CLOCKS_NOT_SUPPLIED", "CONSTANT_MATURITY_METHOD_NOT_CERTIFIED"]


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("nonfinite JSON constant")


def _decode(raw: bytes, receipt: ArtifactReceipt) -> dict:
    if not isinstance(raw, bytes) or not raw or len(raw) > _MAX_BYTES:
        raise ValueError("bounded nonempty immutable source bytes required")
    if not isinstance(receipt, ArtifactReceipt) or not _text(receipt.source_ref) or not _digest(receipt.source_sha256):
        raise ValueError("typed artifact identity required")
    if hashlib.sha256(raw).hexdigest() != receipt.source_sha256:
        raise ValueError("artifact digest mismatch")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid source JSON") from error
    if not isinstance(value, dict): raise ValueError("source must be an object")
    return value


def _day(value) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("source day must be YYYY-MM-DD")
    try: result = date.fromisoformat(value)
    except ValueError as error: raise ValueError("invalid source day") from error
    if result.isoformat() != value: raise ValueError("noncanonical source day")
    return result


def _known(receipt: ArtifactReceipt, asof: datetime) -> bool:
    return _aware(receipt.known_at) and receipt.known_at <= asof


def inspect_legacy_vol(raw: bytes, *, requested_root: str,
                       receipt: ArtifactReceipt, asof: datetime) -> dict:
    """Preserve unqualified legacy value only when the artifact was known by asof.

    artifact_known_at is NOT an observation/quote publication clock. Nothing here
    grants market-data rights or turns the source's date into a precise timestamp.
    """
    if not _aware(asof): raise ValueError("aware request clock required")
    payload = _decode(raw, receipt)
    if payload.get("schema") != "options_hub.vol/v1": raise ValueError("unsupported legacy schema")
    if not _text(requested_root) or payload.get("root") != requested_root: raise ValueError("root binding mismatch")
    source_day = _day(payload.get("asof"))
    reasons = list(_REFUSAL)
    known = _known(receipt, asof)
    if not known: reasons.append("ARTIFACT_NOT_KNOWN_ASOF")
    if source_day > asof.date():
        known = False
        reasons.append("REPORTED_ASOF_AFTER_REQUEST")
    try: value = _number(payload.get("atm_iv"), "legacy ATM IV", 0)/100 if known else None
    except ValueError: value = None
    if value is None: reasons.append("LEGACY_IV_UNAVAILABLE")
    return {
        "root":requested_root, "legacy_atm_iv_decimal":value,
        "legacy_label":"unqualified source-reported constituent IV; tenor not certified",
        "reported_asof":source_day.isoformat(),
        "artifact_ref":receipt.source_ref,"artifact_sha256":receipt.source_sha256,
        "artifact_known_at":receipt.known_at.isoformat() if _aware(receipt.known_at) else None,
        "source_bytes":len(raw), "qualified_iv30":None,"qualified_known_at":None,
        "eligible_for_hybrid_risk":False,"reasons":reasons,
    }


def legacy_house_view(raw_definition: bytes, *, definition_receipt: ArtifactReceipt,
                      basket_id: str, payloads: Mapping[str, bytes],
                      receipts: Mapping[str, ArtifactReceipt], asof: datetime) -> dict:
    """Current equal-weight house membership plus exact legacy payload inspection.

    The registry is hindsight-curated; added/removed dates select effective rows
    but do not certify historical membership knowledge. No current-to-PIT upgrade.
    Every member stays in the denominator. Unqualified descriptive values are
    named separately from the qualified statistics produced by the native leaf.
    """
    if not _aware(asof): raise ValueError("aware request clock required")
    document = _decode(raw_definition, definition_receipt)
    if not _known(definition_receipt, asof): raise ValueError("definition not known asof")
    if not _text(basket_id): raise ValueError("basket identity required")
    baskets = document.get("baskets")
    if not isinstance(baskets, dict) or basket_id not in baskets: raise ValueError("basket not present")
    basket = baskets[basket_id]
    if not isinstance(basket, dict) or basket.get("weighting") != "equal":
        raise ValueError("this adapter supports explicit equal-weight house definitions only")
    raw_members = basket.get("members")
    if not isinstance(raw_members, list) or not raw_members: raise ValueError("empty or invalid registry membership")
    roots, seen = [], set()
    for row in raw_members:
        if not isinstance(row, dict) or not _text(row.get("ticker")): raise ValueError("invalid member")
        root = row["ticker"]
        if root in seen: raise ValueError("duplicate registry identity")
        seen.add(root)
        added = _day(row.get("added"))
        removed = _day(row["removed"]) if row.get("removed") is not None else None
        if removed is not None and removed <= added: raise ValueError("invalid membership interval")
        if added <= asof.date() and (removed is None or asof.date() < removed): roots.append(root)
    roots.sort()
    if not roots: raise ValueError("no effective house members")
    if not isinstance(payloads, Mapping) or not isinstance(receipts, Mapping): raise ValueError("root-keyed mappings required")
    if set(payloads) != set(receipts) or not set(payloads).issubset(set(roots)):
        raise ValueError("payload/receipt identities must match effective membership")
    rows=[]
    for root in roots:
        if root in payloads:
            row=inspect_legacy_vol(payloads[root],requested_root=root,receipt=receipts[root],asof=asof)
        else:
            row={"root":root,"legacy_atm_iv_decimal":None,"qualified_iv30":None,
                 "eligible_for_hybrid_risk":False,"reasons":["OWNER_PAYLOAD_MISSING"]}
        rows.append({"weight":1/len(roots),**row})
    values=[r["legacy_atm_iv_decimal"] for r in rows if r["legacy_atm_iv_decimal"] is not None]
    return {
        "schema":"options_hub.factor_legacy_inspection/v1","basket_id":basket_id,
        "population_basis":"current_registry_membership_not_pit_backtest",
        "asof":asof.isoformat(),
        "definition":{"source_ref":definition_receipt.source_ref,
                      "sha256":definition_receipt.source_sha256,
                      "known_at":definition_receipt.known_at.isoformat()},
        "coverage":{"total_count":len(roots),"payload_count":len(payloads),
                    "reported_value_count":len(values),"reported_weight":len(values)/len(roots),
                    "qualified_count":0,"qualified_weight":0},
        "legacy_covered_mean_iv":fsum(values)/len(values) if values else None,
        "legacy_label":"unqualified mean of reported IV values; not certified IV30 or whole-basket risk",
        "qualified_mean_iv30":None,"hybrid_expected_move":None,
        "members":rows,"reasons":list(_REFUSAL),
        "authority":{"display_only":True,"publication":False,"prophet":False,"position_sizing":False},
    }
