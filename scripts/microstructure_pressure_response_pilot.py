"""Offline R0 driver for qualified equity T/Q JSON; no network or public writes.

Run privately at the source-owning host with qualified source receipts. A fully
synthetic test frame is not evidence of real market observation. Diagnostics
containing print/quote IDs never go to this driver's stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.market_microstructure.pressure_response import measure_window

INPUT_SCHEMA = "equity.pressure_response_input/v0"
MAX_INPUT_BYTES = 16 * 1024 * 1024  # bounded research file; no market-wide tape dumps
_PUBLIC_FIELDS = frozenset({
    "schema", "authority", "state", "reason", "ticker", "session", "start_ns",
    "end_ns", "window_end_ns", "decision_ns", "watermark_ns", "watermark_seen_ns",
    "watermark_receipt", "source_manifest", "evidence_mode", "max_quote_age_ns",
    "condition_policy_refs", "n_active_prints", "n_excluded_revisions_or_conditions",
    "n_unclassified", "buy_proxy_notional_usd", "sell_proxy_notional_usd",
    "unknown_notional_usd", "gross_active_notional_usd", "classified_notional_coverage",
    "pressure_balance", "midpoint_response_bps", "response_null_reason",
    "bid_size_recovery", "ask_size_recovery", "interpretation", "absorption_signal",
})


def summarize(payload: object) -> dict:
    """Apply the pure calculation, projecting away native print diagnostics."""
    if not isinstance(payload, dict) or payload.get("contract") != INPUT_SCHEMA:
        raise ValueError("unrecognized R0 input contract")
    if set(payload) != {"contract", "measurement"} or not isinstance(payload["measurement"], dict):
        raise ValueError("R0 input requires only a measurement object")
    measurement = payload["measurement"]
    allowed = {"ticker", "session", "start_ns", "end_ns", "decision_ns",
               "watermark_ns", "watermark_seen_ns", "watermark_receipt",
               "source_manifest", "evidence_mode", "max_quote_age_ns", "trades", "quotes"}
    if set(measurement) != allowed:
        raise ValueError("R0 measurement fields must match the frozen input contract")
    output = measure_window(**measurement)
    if set(output) - (_PUBLIC_FIELDS | {"print_diagnostics_private_only"}):
        raise ValueError("unknown derived output fields; refusing stdout projection")
    # The source owner still decides whether ANY downstream publication is licensed
    # and authorized. Stdout is a private CLI result, not a frontend/API contract.
    return {key: value for key, value in output.items() if key in _PUBLIC_FIELDS}


def bounded_json(path: Path) -> object:
    if path.suffix.lower() != ".json":
        raise ValueError("R0 input must be a private JSON file")
    with path.open("rb") as fh:
        data = fh.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("R0 input exceeds the bounded file budget")
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("R0 input must be valid UTF-8 JSON") from exc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Research-only equity pressure-response offline measurement")
    parser.add_argument("--input", required=True, type=Path, help="Source-qualified private T/Q JSON")
    args = parser.parse_args(argv)
    try:
        result = summarize(bounded_json(args.input))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"R0 measurement refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
