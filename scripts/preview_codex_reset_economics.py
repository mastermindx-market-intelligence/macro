#!/usr/bin/env python3
"""Read-only limits/decision viewer for explicit owner-supplied JSON evidence.

No provider requests, credential discovery, purchases, resets, dispatch or timers.
A displayed balance is supplied evidence, not a newly authenticated observation.
"""
from __future__ import annotations

import argparse
from dataclasses import MISSING, fields
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.provider_codex_reset_economics import (
    AccountObservation, BankedReset, PreviewPolicy, ResetEconomicsError,
    TaskQuote, Window, preview_codex_resets,
)

MAX_INPUT_BYTES = 524288
REQUEST_SCHEMA = "mastermind.codex_reset_request/v1"


def _record(cls, value: Any):
    if not isinstance(value, dict):
        raise ResetEconomicsError("record must be an object")
    known = {f.name for f in fields(cls)}
    required = {f.name for f in fields(cls) if f.default is MISSING and f.default_factory is MISSING}
    if set(value) - known or required - set(value):
        raise ResetEconomicsError("record has unexpected or missing fields")
    return cls(**value)


def parse_request(raw: Any) -> dict:
    required = {"schema", "now", "first_lawful_tier", "observations"}
    optional = {"preferred_account_id", "policy"}
    if not isinstance(raw, dict) or set(raw) - required - optional or required - set(raw):
        raise ResetEconomicsError("invalid request envelope")
    if raw["schema"] != REQUEST_SCHEMA:
        raise ResetEconomicsError("unsupported request schema")
    if not isinstance(raw["observations"], list) or len(raw["observations"]) > 32:
        raise ResetEconomicsError("invalid observation list")
    observations = []
    for item in raw["observations"]:
        if not isinstance(item, dict):
            raise ResetEconomicsError("invalid observation")
        row = dict(item)
        row["short"] = _record(Window, row.get("short"))
        row["weekly"] = _record(Window, row.get("weekly"))
        for name, cls, limit in (("banked_resets", BankedReset, 8), ("tasks", TaskQuote, 12)):
            if not isinstance(row.get(name), list) or len(row[name]) > limit:
                raise ResetEconomicsError("invalid bounded evidence list")
            row[name] = tuple(_record(cls, x) for x in row[name])
        observations.append(_record(AccountObservation, row))
    return dict(observations=tuple(observations), now=raw["now"],
                first_lawful_tier=raw["first_lawful_tier"],
                preferred_account_id=raw.get("preferred_account_id"),
                policy=_record(PreviewPolicy, raw.get("policy", {})))


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ResetEconomicsError("duplicate JSON field")
        result[key] = value
    return result


def load_request(path: Path) -> dict:
    with path.open("rb") as stream:
        payload = stream.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise ResetEconomicsError("input exceeds bounded size")
    return parse_request(json.loads(payload, object_pairs_hook=reject_duplicate_keys))


def render_text(preview: dict) -> str:
    lines = ["CODEX LIMITS / RESET PREVIEW", "Supplied observations only; no live reads or effects.",
             "Status: " + preview["status"],
             "Selected: " + str(preview["selected_account_id"] or "none"),
             "Action: " + preview["proposed_action"], ""]
    for row in preview["candidates"]:
        lines.append(row["account_id"] + " / " + row["provider_model"])
        lines.append("  Weekly: {weekly_remaining}/{weekly_capacity}; short: {short_remaining}/{short_capacity} native units".format(**row))
        lines.append("  Weekly reset Unix: {weekly_reset_at}; known unexpired resets: {banked_reset_count}".format(**row))
        lines.append("  " + (row["reason"] or "Eligible in forecast; native revalidation and claim still required."))
        lines.append("  Forecast jobs: {completed_tasks_forecast}; resets spent: {banked_resets_spent_forecast}".format(**row))
    lines.extend(["", "Input digest: " + preview["input_digest"],
                  "Preview digest: " + preview["preview_digest"],
                  "No reset execution is authorized by this output."])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="explicit redacted owner evidence JSON")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    try:
        request = load_request(args.input)
        preview = preview_codex_resets(**request)
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        # Never echo input JSON or arbitrary exceptions: either may contain secrets.
        print("Invalid or unavailable reset-preview evidence.", file=sys.stderr)
        return 2
    print(json.dumps(preview, sort_keys=True, indent=2) if args.format == "json" else render_text(preview), end="\n" if args.format == "json" else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
