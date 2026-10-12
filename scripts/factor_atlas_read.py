#!/usr/bin/env python3
"""Recompute one Factor Atlas candidate from explicit retained owner projections.

Reads one bounded local JSON input and emits strict JSON to stdout. It neither
collects data nor writes a source store, publishes a feed, grants rights or changes
rank/portfolio state. Use shell redirection only to an explicitly chosen evidence
artifact, never an incumbent data/ or site/ path.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import jsonschema  # noqa: E402
from engine.factor_atlas_read import build_factor_read, canonical_bytes  # noqa: E402

MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
SCHEMA = ROOT / "contracts" / "factor_atlas_read.v1.schema.json"


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value: str):
    raise ValueError(f"nonfinite JSON constant: {value}")


def read_input(path: Path) -> dict:
    with path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 16 MiB; no truncation or partial population is permitted")
    value = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
    if not isinstance(value, dict) or set(value) != {"request", "owner_inputs"}:
        raise ValueError("input must contain exactly request and owner_inputs")
    return value


def validate_output(value: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(value)
    request = value["request"]
    if (value["basket_id"] != request["basket_id"] or value["history_mode"] != request["history_mode"]
            or value["as_of"] != request["end"] or value["anchor"]["date"] != request["start"]):
        raise ValueError("result identity or window disagrees with its request")
    core = {key: item for key, item in value.items() if key != "result_digest"}
    actual = hashlib.sha256(canonical_bytes(core)).hexdigest()
    if not hmac.compare_digest(actual, value["result_digest"]):
        raise ValueError("result digest does not match its finite canonical JSON core")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="bounded local JSON owner-projection input")
    args = parser.parse_args(argv)
    try:
        data = read_input(args.input)
        result = build_factor_read(data["request"], owner_inputs=data["owner_inputs"])
        validate_output(result)
        encoded = canonical_bytes(result) + b"\n"
        if len(encoded) > MAX_OUTPUT_BYTES:
            raise ValueError("result exceeds the 4 MiB candidate transport bound; narrow the explicit request")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, jsonschema.ValidationError) as exc:
        detail = exc.message if isinstance(exc, jsonschema.ValidationError) else str(exc)
        print(f"factor_atlas: {detail[:240]}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
