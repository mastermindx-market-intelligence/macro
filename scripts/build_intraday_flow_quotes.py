"""Publish the Intraday Flow board's quotes from the VPS full snapshot.

This is a transport filter, not a second quote engine: the snapshot lane has
already fetched the vendor data into ``quotes_full.json``.  The public board
gets only the symbols already disclosed by its nightly ``base.json``.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PUBLIC_QUOTE_FIELDS = (
    "price", "ts", "source", "basis", "prevClose", "changePct", "currency",
    "delayMin", "tsSynthetic", "vol", "hi", "lo",
)


def _has_price(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        return math.isfinite(float(value.get("price")))
    except (TypeError, ValueError):
        return False


def _observed_quote_clock_ms(quote: Any) -> int | float | None:
    """Epoch milliseconds of a real quote clock.

    Synthetic stamps and missing or non-finite ``ts`` values do not qualify.
    A missing ``ts`` is excluded, never treated as zero.
    """
    if not isinstance(quote, dict) or quote.get("tsSynthetic") is True:
        return None
    ts = quote.get("ts")
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return None
    if not math.isfinite(ts) or ts <= 0:
        return None
    return ts


def _median_quote_source_asof(quotes: dict[str, Any]) -> str | None:
    """UTC ISO-8601 median of observed quote clocks, or None when none qualify.

    ``statistics.median_low`` stays on a clock a quote actually carried.
    """
    clocks = [
        ms for ms in (_observed_quote_clock_ms(quote) for quote in quotes.values())
        if ms is not None
    ]
    if not clocks:
        return None
    median_ms = statistics.median_low(clocks)
    return datetime.fromtimestamp(median_ms / 1000, tz=timezone.utc).isoformat()


def build_payload(base: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    leaders = base.get("leaders") or []
    symbols = sorted(
        {
            str(row.get("ticker") or "").strip().upper()
            for row in leaders
            if isinstance(row, dict) and row.get("ticker")
        }
    )
    if not symbols:
        raise ValueError("Intraday Flow base contains no leader symbols")
    source_quotes = snapshot.get("quotes") or {}
    if not isinstance(source_quotes, dict):
        raise ValueError("full quote snapshot has no quote map")
    quotes = {
        # The full snapshot may contain server-only provenance. Publish only
        # existing public fields, preserving their values and optional absence.
        symbol: {field: source_quotes[symbol][field]
                 for field in PUBLIC_QUOTE_FIELDS if field in source_quotes[symbol]}
        for symbol in symbols
        if symbol in source_quotes and _has_price(source_quotes[symbol])
    }
    now = datetime.now(timezone.utc)
    upstream_meta = snapshot.get("meta") or {}
    return {
        "ts": snapshot.get("ts"),
        "asof": snapshot.get("asof"),
        "source": "snapshot:intraday_flow",
        "quotes": quotes,
        "meta": {
            "requested": len(symbols),
            "resolved": len(quotes),
            "coverage": round(len(quotes) / len(symbols), 6),
            "upstream_asof": snapshot.get("asof"),
            "upstream_source": snapshot.get("source"),
            "upstream_requested": upstream_meta.get("requested"),
            "upstream_resolved": upstream_meta.get("resolved"),
            "built_at": now.isoformat(),
            "source_asof": _median_quote_source_asof(quotes),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--quotes", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    payload = build_payload(
        json.loads(args.base.read_text(encoding="utf-8")),
        json.loads(args.quotes.read_text(encoding="utf-8")),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
