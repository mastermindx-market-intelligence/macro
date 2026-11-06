"""Pure, source-clock-preserving bindings for the existing bottom-sensor producer.

No network, indicator recomputation, signal selection or inferred first-seen time.
The incumbent negative distance-below-high becomes a labelled positive magnitude.
"""
from __future__ import annotations

from datetime import date, datetime
import math
from numbers import Real
import re
from typing import Any


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _day(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Real):
        try:
            number = float(value)
            return number if math.isfinite(number) else None
        except (ValueError, OverflowError):
            return None
    return None


def _availability(*values: Any) -> str | None:
    """Later genuine receipt wins; invalid supplied receipt must not become unknown."""
    parsed: list[tuple[datetime, str]] = []
    for value in values:
        if value is None:
            continue
        if not isinstance(value, str):
            return "invalid"
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                return "invalid"
            parsed.append((stamp, value))
        except (ValueError, TypeError):
            return "invalid"
    return max(parsed, key=lambda item: item[0])[1] if parsed else None


def build_pivot_observations(
    symbol: str, *, signal_gate: dict | None, standout: dict | None,
    standouts_as_of: str | None, price_context: dict | None = None,
) -> list[dict]:
    """Bind each observation to its own actual daily vintage, never a build clock."""
    gate = _mapping(signal_gate)
    row = _mapping(standout)
    if not isinstance(symbol, str) or row.get("ticker") != symbol:
        row = {}
    signal = _mapping(row.get("signal"))
    coiled = _mapping(row.get("coiled"))
    hold = _mapping(row.get("hold"))
    alignment = _mapping(_mapping(row.get("conviction")).get("alignment"))
    prices = _mapping(price_context)
    container_day = _day(standouts_as_of)
    signal_day = _day(signal.get("asof"))
    row_day = _day(row.get("as_of")) if "as_of" in row else signal_day

    def contained(day: str | None) -> str | None:
        return day if container_day and day and day <= container_day else None

    sg_source = "factordata/signal_gate.json"
    st_source = "factordata/us_standouts.json"
    safe_symbol = symbol if isinstance(symbol, str) and re.fullmatch(r"[A-Za-z0-9._^\-]{1,40}", symbol) else "<invalid>"
    out: list[dict] = []

    def add(field: str, value: Any, source: str, as_of: str | None, available_at: str | None) -> None:
        out.append({"field": field, "value": _value(value), "source": source,
                    "as_of": as_of, "available_at": available_at})

    gate_day = _day(gate.get("asof"))
    gate_available = _availability(gate.get("available_at"))
    add("trigger_tier", gate.get("tier_cascade"), sg_source, gate_day, gate_available)
    add("trigger_age_ticks", gate.get("ticks"), sg_source, gate_day, gate_available)
    # Preserve genuine integer counts, including zero, without converting bools.
    if isinstance(gate.get("ticks"), int) and not isinstance(gate.get("ticks"), bool):
        out[-1]["value"] = gate["ticks"]
    row_available = _availability(row.get("available_at"))
    for field, key in (("coiled", "coiled"), ("star", "star"), ("coiled_fire", "fire")):
        add(field, coiled.get(key), st_source, contained(row_day), row_available)
    add("above200", signal.get("above200"), st_source, contained(signal_day),
        _availability(row.get("available_at"), signal.get("available_at")))
    for field, key in (("hold_state", "state"), ("hold_days_basing", "days_basing"),
                       ("hold_ret_since_anchor_pct", "ret_since_anchor_pct")):
        add(field, hold.get(key), st_source, contained(row_day), row_available)
        if field == "hold_days_basing" and isinstance(hold.get(key), int) and not isinstance(hold.get(key), bool):
            out[-1]["value"] = hold[key]
    add("knife_score", alignment.get("knife"), st_source, contained(row_day), row_available)
    pday, pavailable = _day(prices.get("as_of")), _availability(prices.get("available_at"))
    psource = f"data/stocks/{safe_symbol}.parquet"
    add("dist_21d_low_pct", prices.get("dist_21d_low_pct"), psource, pday, pavailable)
    signed = prices.get("dist_126d_high_pct")
    signed = _value(signed)
    magnitude = -signed if isinstance(signed, (int, float)) and not isinstance(signed, bool) and signed <= 0 else None
    add("dist_126d_high_pct", magnitude, psource, pday, pavailable)
    return out
