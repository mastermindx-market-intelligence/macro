"""Bounded producer metadata carried beside a normalized quote.

These are the producer's declarations, not authenticated vendor identity, an
arrival-time receipt, a canonical security join or permission to use a quote.
They never replace the consumer's price, timestamp, basis or freshness inputs.
Old points without this metadata remain unknown; no historical backfill.
"""
from __future__ import annotations

import math
import re

SCHEMA = "quote_native_metadata.v1"
FIELDS = ("source", "basis", "ts", "quote_ts", "quote_ts_synthetic", "tsSynthetic")


def copy_native_metadata(value: object) -> dict | None:
    """Copy only the closed scalar shape; malformed context never gates price."""
    if type(value) is not dict or set(value) != {"schema", *FIELDS} or value.get("schema") != SCHEMA:
        return None
    source = value["source"]
    if type(source) is not str or re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", source) is None:
        return None
    for field, limit in (("basis", 64), ("quote_ts", 96)):
        item = value[field]
        if item is not None and (type(item) is not str or not 0 < len(item) <= limit
                                 or any(ord(c) < 32 or ord(c) == 127 for c in item)):
            return None
    stamp = value["ts"]
    if stamp is not None and (type(stamp) not in (int, float)
                              or not 0 <= stamp <= 2**53 - 1 or not math.isfinite(stamp)):
        return None
    if any(value[field] is not None and type(value[field]) is not bool
           for field in ("quote_ts_synthetic", "tsSynthetic")):
        return None
    return dict(value)


def from_native_quote(row: dict) -> dict | None:
    """Retain exact declared fields; absence stays null and clocks stay distinct."""
    return copy_native_metadata({"schema": SCHEMA, **{field: row.get(field) for field in FIELDS}})
