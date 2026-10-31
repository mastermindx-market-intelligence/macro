"""Pure, explicit selection of one newer BOATS whole-window vendor revision.

Raw receipts remain immutable. This changes only a private derived history
document; it performs no IO, provider request, activation or publication.
"""
from __future__ import annotations

import copy
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

CONSTANTS = {
    "schema": "terminal.tiingo_boats_history.v1", "source": "tiingo-boats-rest",
    "venue": "BOATS", "timestamp_basis": "utc", "bar_seconds": 60,
    "price_basis": "vendor_reported_unqualified", "volume_basis": "vendor_reported_shares",
    "coverage": "captured_vendor_bars_only", "complete": False,
}
SHA = re.compile(r"[a-f0-9]{64}")
SYMBOL = re.compile(r"[A-Z][A-Z0-9.-]{0,31}")


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("receipt observation must be a zoned timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("receipt observation lacks timezone")
    return result.timestamp()


def _validate(doc):
    if not isinstance(doc, dict) or any(doc.get(k) != v for k, v in CONSTANTS.items()):
        raise ValueError("incompatible BOATS history contract")
    if doc.get("complete") is not False or type(doc.get("bar_seconds")) is not int:
        raise ValueError("invalid history completeness or interval")
    symbol = doc.get("symbol")
    if not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol):
        raise ValueError("invalid history symbol")
    receipts = doc.get("receipts")
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= 512:
        raise ValueError("invalid receipt budget")
    by_id, clocks = {}, {}
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("invalid receipt")
        rid = receipt.get("receipt_id")
        if not isinstance(rid, str) or not SHA.fullmatch(rid) or rid in by_id:
            raise ValueError("invalid or duplicate receipt identity")
        digest = receipt.get("raw_sha256")
        if not isinstance(digest, str) or not SHA.fullmatch(digest):
            raise ValueError("invalid raw digest")
        request = urlsplit(receipt.get("request_path", ""))
        if request.scheme or request.netloc or request.fragment or request.path != f"/boats/{symbol}/prices":
            raise ValueError("receipt request does not match symbol")
        if parse_qs(request.query).get("resampleFreq") != ["1min"]:
            raise ValueError("receipt is not one-minute history")
        by_id[rid] = receipt
        clocks[rid] = _instant(receipt.get("observed_at_utc"))
    bars, lineage = doc.get("bars"), doc.get("bar_receipt_ids")
    if not isinstance(bars, list) or len(bars) > 100_000 or not isinstance(lineage, list) or len(bars) != len(lineage):
        raise ValueError("invalid bar or lineage budget")
    last = 0
    for bar, ids in zip(bars, lineage):
        if not isinstance(bar, list) or len(bar) != 6 or any(type(v) not in (int, float) or not math.isfinite(v) for v in bar):
            raise ValueError("invalid OHLCV values")
        t, o, h, low, close, volume = bar
        if t % 60 or not 946684800 <= t < 4102444800 or t <= last or min(o, h, low, close) <= 0 or volume < 0 or low > min(o, close) or h < max(o, close):
            raise ValueError("invalid OHLCV order or range")
        if not isinstance(ids, list) or not ids or any(not isinstance(r, str) or r not in by_id for r in ids) or len(ids) != len(set(ids)):
            raise ValueError("invalid bar receipt lineage")
        if any(t > clocks[r] for r in ids):
            raise ValueError("bar later than source observation")
        last = t
    return by_id, clocks


def merge_session_window(prior: dict | None, update: dict, session: str) -> dict:
    """Replace the entire selected overnight window with its new vendor vintage."""
    day = date.fromisoformat(session)
    if day.isoformat() != session:
        raise ValueError("session must be an exact date")
    et = ZoneInfo("America/New_York")
    start = datetime.combine(day - timedelta(days=1), time(20), et).timestamp()
    end = datetime.combine(day, time(4), et).timestamp()
    update_receipts, update_clocks = _validate(update)
    if len(update_receipts) != 1 or len(update["bars"]) > 480:
        raise ValueError("one bounded update receipt required")
    rid, receipt = next(iter(update_receipts.items()))
    query = parse_qs(urlsplit(receipt["request_path"]).query)
    if query.get("startDate") != [session] or query.get("endDate") != [session] or query.get("forceFill", ["false"]) != ["false"]:
        raise ValueError("update must request the exact unfilled session window")
    if any(not start <= bar[0] < end for bar in update["bars"]):
        raise ValueError("update bar outside selected overnight window")
    if prior is None:
        return copy.deepcopy(update)
    old_receipts, clocks = _validate(prior)
    if prior["symbol"] != update["symbol"]:
        raise ValueError("symbol mismatch")
    for key in old_receipts.keys() & update_receipts.keys():
        if old_receipts[key] != update_receipts[key]:
            raise ValueError("same receipt identity with different metadata")
    inside = [(bar, ids) for bar, ids in zip(prior["bars"], prior["bar_receipt_ids"]) if start <= bar[0] < end]
    if inside:
        newest = max(clocks[r] for _, ids in inside for r in ids)
        if update_clocks[rid] < newest:
            raise ValueError("older vendor revision cannot replace newer evidence")
        if update_clocks[rid] == newest and [bar for bar, _ in inside] != update["bars"]:
            raise ValueError("conflicting same-time vendor revisions")
    kept = [(bar, ids) for bar, ids in zip(prior["bars"], prior["bar_receipt_ids"]) if not start <= bar[0] < end]
    merged = sorted(kept + list(zip(update["bars"], update["bar_receipt_ids"])), key=lambda row: row[0][0])
    if len(merged) > 100_000:
        raise ValueError("combined history exceeds bar budget")
    used = {rid} | {r for _, ids in merged for r in ids}
    all_receipts = {**old_receipts, **update_receipts}
    if len(used) > 512:
        raise ValueError("combined history exceeds receipt budget")
    result = {**CONSTANTS, "symbol": update["symbol"],
              "receipts": [all_receipts[r] for r in all_receipts if r in used],
              "bars": [bar for bar, _ in merged], "bar_receipt_ids": [ids for _, ids in merged]}
    return copy.deepcopy(result)
