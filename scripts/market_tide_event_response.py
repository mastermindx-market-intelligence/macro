"""Read-only JSON interface for Market Tide's point-in-time event-response composer.

No collector, publisher, scheduler, model inference, alert, or trade effect.
Existing pipeline owners supply admitted source-bound observations.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# File-path entrypoints must resolve this repository before ambient installs.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.market_tide_event_response import compose

MAX_INPUT_BYTES = 2_000_000


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON member: {key}")
        out[key] = value
    return out


def _invalid_constant(value: str):
    raise ValueError(f"invalid JSON constant: {value}")


def run(payload: str) -> dict:
    if len(payload.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("JSON input exceeds 2 MB limit")
    data = json.loads(payload, object_pairs_hook=_unique_object,
                      parse_constant=_invalid_constant)
    return compose(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose source-qualified event response to stdout")
    parser.add_argument("--input", default="-", help="JSON request file or - for stdin")
    args = parser.parse_args(argv)
    try:
        if args.input == "-":
            raw = sys.stdin.read(MAX_INPUT_BYTES + 1)
        else:
            path = Path(args.input)
            if path.stat().st_size > MAX_INPUT_BYTES:
                raise ValueError("JSON input exceeds 2 MB limit")
            raw = path.read_text(encoding="utf-8")
        output = run(raw)
        sys.stdout.write(json.dumps(output, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False) + "\n")
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"market_tide_event_response: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
