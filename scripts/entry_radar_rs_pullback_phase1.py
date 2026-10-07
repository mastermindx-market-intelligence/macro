#!/usr/bin/env python3
"""Reproduce RS Pullback Phase-1 admission or build supplied offline input frames.

No network, vendor access, live-source mutation, detector registration or ledger
write. Default output is stdout. A supplied output path is an explicit research
artifact; it is not a new runtime or experimental sink.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine.entry_radar.replay.rs_pullback_launch_data import (  # noqa: E402
    InputContractError, assess_source_census, build_input_panel,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--census", type=Path, help="frozen existing-owner source census JSON")
    mode.add_argument("--input-panel", type=Path, help="immutable offline input bundle JSON")
    parser.add_argument("--output", type=Path, help="write an explicit research artifact")
    args = parser.parse_args(argv)
    if args.output:
        allowed = (REPO / "research/live_entry_radar/rs_pullback_launch").resolve()
        if not args.output.resolve().is_relative_to(allowed):
            parser.error("--output must be under research/live_entry_radar/rs_pullback_launch; use stdout otherwise")
    try:
        source = args.census or args.input_panel
        raw = json.loads(source.read_text(encoding="utf-8"))
        result = assess_source_census(raw) if args.census else build_input_panel(raw)
        rendered = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    except (InputContractError, ValueError, TypeError, KeyError, OSError) as exc:
        print(f"Phase-1 input refused: {exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    # A negative admission is a successful diagnostic, not a crashed research run.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
