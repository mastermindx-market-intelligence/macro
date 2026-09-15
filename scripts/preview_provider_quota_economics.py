#!/usr/bin/env python3
"""One-shot, offline quota-economics preview; no credentials or worker dispatch."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.provider_quota_economics import QuotaEconomicsError, preview_document


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise QuotaEconomicsError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Authoring input JSON path, or - for stdin")
    args = parser.parse_args(argv)
    try:
        if args.input == "-":
            raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        else:
            with Path(args.input).open("rb") as handle:
                raw = handle.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise QuotaEconomicsError("INPUT_TOO_LARGE")
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
        result = preview_document(document)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except QuotaEconomicsError as exc:
        print(json.dumps({"error": str(exc), "live_admission": False}), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError):
        print('{"error":"INPUT_UNREADABLE_OR_INVALID","live_admission":false}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
