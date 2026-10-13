#!/usr/bin/env python3
"""Reproduce RS Pullback Phase-1 admission or build supplied offline input frames.

No network, vendor access, live-source mutation, detector registration or ledger
write. Default output is stdout. A supplied output path is an explicit research
artifact; it is not a new runtime or experimental sink.
"""
from __future__ import annotations

import argparse
import hashlib
import time
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from engine.entry_radar.replay.rs_pullback_launch_data import (  # noqa: E402
    InputContractError, assess_source_census, build_input_panel, bind_calendar_projection,
    CALENDAR_MAX_BYTES, CALENDAR_READ_SCHEMA, CALENDAR_ARTIFACT_REF,
    CALENDAR_SOURCE_REVISION, CALENDAR_SOURCE_FILES, digest,
)



def read_calendar_projection(path: Path) -> dict:
    """One bounded acquisition using actual clock readings; no clock override.

    The receipt attests what this reader observed, not vendor authenticity.
    The returned snapshot must be retained with the original input bundle for
    exact replay. Re-reading the path creates a later receipt, never history.
    """
    source_ref = str(path.resolve())
    started = time.time_ns()
    with path.open("rb") as source:
        payload = source.read(CALENDAR_MAX_BYTES + 1)
    completed = time.time_ns()
    if completed < started:
        raise InputContractError("calendar read clock moved backwards")
    receipt = {
        "schema": CALENDAR_READ_SCHEMA, "source_ref": source_ref,
        "byte_sha256": hashlib.sha256(payload).hexdigest(), "byte_length": len(payload),
        "read_started_at_utc_ns": started, "read_completed_at_utc_ns": completed,
        "artifact_ref": CALENDAR_ARTIFACT_REF,
        "source_revision": CALENDAR_SOURCE_REVISION,
        "source_files": dict(CALENDAR_SOURCE_FILES),
    }
    receipt["receipt_sha256"] = digest(receipt)
    return bind_calendar_projection(payload, receipt)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--census", type=Path, help="frozen existing-owner source census JSON")
    mode.add_argument("--input-panel", type=Path, help="immutable offline input bundle JSON")
    parser.add_argument("--calendar-projection", type=Path,
                        help="read the accepted owner projection now; retain output snapshot for replay")
    parser.add_argument("--output", type=Path, help="write an explicit research artifact")
    args = parser.parse_args(argv)
    if args.calendar_projection and not args.input_panel:
        parser.error("--calendar-projection requires --input-panel")
    if args.output:
        allowed = (REPO / "research/live_entry_radar/rs_pullback_launch").resolve()
        if not args.output.resolve().is_relative_to(allowed):
            parser.error("--output must be under research/live_entry_radar/rs_pullback_launch; use stdout otherwise")
    try:
        source = args.census or args.input_panel
        raw = json.loads(source.read_text(encoding="utf-8"))
        if args.calendar_projection:
            raw["calendar"] = read_calendar_projection(args.calendar_projection)
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
