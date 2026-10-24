"""Offline receipt-bound BOATS minute-bar export for Terminal's existing chart path.

Only explicitly selected immutable research views are read. No provider access,
archive mutation, source-contract promotion or publication occurs. Output is a
private delivery candidate; the consumer's calendar remains session authority.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collectors.tiingo_archive import DEFAULT_ARCHIVE, receipt_identity, require_external_root
from lib.dataos.tiingo_reader import TiingoViewRefusal, _unique_raw_context, read_research_view

SCHEMA = "terminal.tiingo_boats_history.v1"
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,31}$")
SHA = re.compile(r"^[a-f0-9]{64}$")
MAX_BARS = 100_000
MAX_PARTITIONS = 512
ET = ZoneInfo("America/New_York")


def _number(value, *, volume=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise TiingoViewRefusal("missing or non-finite vendor OHLCV")
    if value < 0 or (not volume and value == 0):
        raise TiingoViewRefusal("invalid vendor OHLCV range")
    return value


def build_chart_history(symbol: str, refs: list[tuple[str, str]], *,
                        root: Path = DEFAULT_ARCHIVE, check_mount: bool = True,
                        receipt_paths: dict[tuple[str, str], Path] | None = None) -> dict:
    """Assemble selected captures, refusing conflicting revisions and unknown volume.

    Absence of a bar never proves no trade. No gap filling, quote/trade-tape
    aggregation, adjustment-factor construction or full-session claim is made.
    """
    if not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol):
        raise TiingoViewRefusal("exact uppercase vendor ticker required")
    if not isinstance(refs, (list, tuple)) or not 1 <= len(refs) <= MAX_PARTITIONS:
        raise TiingoViewRefusal("one to 512 explicit capture references required")
    if any(not isinstance(r, (list, tuple)) or len(r) != 2
           or not all(isinstance(x, str) for x in r) or not SHA.fullmatch(r[1]) for r in refs):
        raise TiingoViewRefusal("invalid capture reference")
    if len(set(map(tuple, refs))) != len(refs):
        raise TiingoViewRefusal("duplicate capture references")
    if receipt_paths is not None and set(receipt_paths) != set(map(tuple, refs)):
        raise TiingoViewRefusal("receipt hints must match every selected capture")
    base = require_external_root(root, check_mount=check_mount)
    receipts, bars, lineage = [], {}, {}
    input_rows = 0
    for day, selected_id in refs:
        receipt_path = receipt_paths[(day, selected_id)] if receipt_paths is not None else None
        view = read_research_view("boats-bars", day, selected_id, root=base,
                                  max_rows=MAX_BARS, check_mount=check_mount,
                                  receipt_path=receipt_path)
        context = _unique_raw_context(base, "boats-bars", day, view.source_sha256,
                                      receipt_id=selected_id, receipt_path=receipt_path)
        if context.get("symbol") != symbol or receipt_identity(context) != selected_id:
            raise TiingoViewRefusal("capture does not identify requested ticker/receipt")
        request = view.source_request_path or ""
        url = urlsplit(request)
        query = parse_qs(url.query)
        if (url.path != f"/boats/{symbol}/prices" or url.scheme or url.netloc
                or query.get("resampleFreq") != ["1min"]):
            raise TiingoViewRefusal("only explicitly requested BOATS one-minute prices supported")
        input_rows += len(view.rows)
        if input_rows > MAX_BARS:
            raise TiingoViewRefusal("bounded input row budget exceeded")
        receipts.append({"receipt_id": selected_id, "raw_sha256": view.source_sha256,
                         "observed_at_utc": view.source_observed_at_utc, "request_path": request})
        seen = set()
        for row in view.rows:
            if (row.get("ticker_vendor") != symbol or row.get("venue") != "BOATS"
                    or row.get("venue_scope") != "single_ats"
                    or row.get("source_receipt_id") != selected_id
                    or row.get("source_sha256") != view.source_sha256
                    or row.get("volume_unit_vendor") != "shares"
                    or row.get("volume_available") is not True
                    or row.get("requested_resample_frequency") != "1min"):
                raise TiingoViewRefusal("BOATS source lineage, interval or volume unavailable")
            instant = datetime.fromisoformat(row["bar_at_vendor"].replace("Z", "+00:00"))
            if instant.tzinfo is None:
                raise TiingoViewRefusal("bar lacks source timezone")
            epoch = instant.timestamp()
            if not 946684800 <= epoch < 4102444800 or epoch % 60:
                raise TiingoViewRefusal("bar is not a bounded UTC minute boundary")
            local = instant.astimezone(ET)
            if 4 <= local.hour < 20:
                raise TiingoViewRefusal("BOATS bar outside overnight wall-clock window")
            values = [_number(row.get("vendor_" + k)) for k in ("open", "high", "low", "close")]
            o, h, l, c = values
            if l > min(o, c) or h < max(o, c) or l > h:
                raise TiingoViewRefusal("inconsistent vendor OHLC")
            values.append(_number(row.get("vendor_volume"), volume=True))
            key = int(epoch)
            if key in seen:
                raise TiingoViewRefusal("duplicate timestamp within source partition")
            seen.add(key)
            if key in bars and bars[key] != values:
                raise TiingoViewRefusal("conflicting BOATS revisions require explicit resolution")
            bars[key] = values
            lineage.setdefault(key, []).append(selected_id)
    epochs = sorted(bars)
    return {"schema": SCHEMA, "symbol": symbol, "source": "tiingo-boats-rest", "venue": "BOATS",
            "timestamp_basis": "utc", "bar_seconds": 60,
            "price_basis": "vendor_reported_unqualified", "volume_basis": "vendor_reported_shares",
            "coverage": "captured_vendor_bars_only", "complete": False,
            "receipts": receipts, "bars": [[t, *bars[t]] for t in epochs],
            "bar_receipt_ids": [lineage[t] for t in epochs]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", required=True)
    p.add_argument("--refs", type=Path, required=True, help="JSON array of [capture-day, exact-receipt-id]")
    p.add_argument("--root", type=Path, default=DEFAULT_ARCHIVE)
    p.add_argument("--output", type=Path, required=True, help="new private candidate file; never overwrites")
    args = p.parse_args(argv)
    if args.refs.stat().st_size > 100_000:
        p.error("capture reference file exceeds limit")
    result = build_chart_history(args.symbol, json.loads(args.refs.read_text()), root=args.root)
    # Refuse an accidental public-tree export. Deployment remains the assigning
    # principal's separate action after consumer checks and exact-data selection.
    target = args.output.resolve()
    if "public" in target.parts or "site" in target.parts:
        p.error("output must be a private delivery candidate")
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf8") as fp:
        json.dump(result, fp, separators=(",", ":"), allow_nan=False)
        fp.write("\n")
    print(json.dumps({"schema": SCHEMA, "symbol": args.symbol, "bars": len(result["bars"]),
                      "receipts": len(result["receipts"]), "complete": False, "output": str(target)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
