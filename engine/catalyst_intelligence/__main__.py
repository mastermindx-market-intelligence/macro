"""Replay one research request from stdin; emits JSON, writes no source stores.

Usage: python -m engine.catalyst_intelligence < request.json > assessment.json
The caller controls research files. This is not a runtime publisher or live API.
"""
from __future__ import annotations

import json
import sys

from .assessment import build_stock_assessment
from .assessment_v2 import INPUT_SCHEMA as V2_INPUT_SCHEMA, build_stock_assessment_v2
from .peer_context import canonical

MAX_INPUT_BYTES = 4 * 1024 * 1024


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        print("research input exceeds 4 MiB", file=sys.stderr)
        return 2
    try:
        request = json.loads(raw)
        builder = (build_stock_assessment_v2 if isinstance(request, dict)
                   and request.get("schema") == V2_INPUT_SCHEMA else build_stock_assessment)
        packet = builder(request)
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        # Local replay diagnostics only; this executable is not a public route.
        print(f"research input refused: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(canonical(packet) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
