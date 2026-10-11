#!/usr/bin/env python3
"""Pure JSON machine projection for engine.options_scenario_surface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.options_scenario_surface import build_scenario_surface  # noqa: E402


def _load(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="snapshot JSON path or - for stdin")
    parser.add_argument("--output", default="-", help="output JSON path or - for stdout")
    args = parser.parse_args()

    payload = _load(args.input)
    out = build_scenario_surface(
        payload.get("contracts", []),
        root=payload["root"],
        observed_at=payload["observed_at"],
        spot=payload["spot"],
        price_grid=payload["price_grid"],
        horizons_minutes=payload["horizons_minutes"],
        expiry_scope=payload.get("expiry_scope"),
        max_dte_days=payload.get("max_dte_days"),
        oi_vintage=payload.get("oi_vintage"),
        iv_observed_at=payload.get("iv_observed_at"),
        vol_map=payload.get("vol_map", "sticky_strike"),
        iv_source=payload.get("iv_source", "provided_iv"),
    )
    encoded = json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    if args.output == "-":
        sys.stdout.write(encoded)
    else:
        Path(args.output).write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
