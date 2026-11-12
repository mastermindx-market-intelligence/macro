#!/usr/bin/env python3
"""Nightly governed outcome evaluator for HK/CA Prophet discovery observations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import prophet_discovery_grade  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Grade governed HK/CA Prophet discovery observations."
    )
    parser.add_argument(
        "--nightly",
        action="store_true",
        help=(
            "Explicitly request the persistent nightly grading path. The engine "
            "still independently requires the canonical nightly ledger lane."
        ),
    )
    parser.add_argument(
        "--market",
        type=str.upper,
        choices=prophet_discovery_grade.MARKETS,
        help="Grade only the market whose producer just persisted.",
    )
    parser.add_argument(
        "--source-asof",
        help=(
            "Require a healthy producer discovery receipt for this exact owner session "
            "(YYYY-MM-DD). Valid only with --market."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args([] if argv is None else argv)
    if not args.nightly:
        parser.error("--nightly is required for persistent discovery grading")
    if args.source_asof and not args.market:
        parser.error("--source-asof requires --market")
    if args.market and not args.source_asof:
        parser.error("--market requires --source-asof")

    if args.market:
        try:
            receipt = prophet_discovery_grade.grade_market(
                args.market,
                expected_source_asof=args.source_asof,
            )
        except Exception as exc:  # noqa: BLE001 — preserve market-scoped failure
            receipt = {
                "market": args.market,
                "available": False,
                "state": "ERROR",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        result = {args.market: receipt}
    else:
        try:
            result = prophet_discovery_grade.grade_all()
        except Exception as exc:  # noqa: BLE001 — scheduler receipt must be truthful
            result = {
                "available": False,
                "state": "ERROR",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            print(json.dumps(result, sort_keys=True, default=str))
            return 1

    print(json.dumps(result, sort_keys=True, default=str))
    has_market_error = any(
        isinstance(receipt, dict) and receipt.get("state") == "ERROR"
        for receipt in result.values()
    )
    return 1 if has_market_error else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
