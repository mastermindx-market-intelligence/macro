#!/usr/bin/env python3
"""Offline qualification probe for Brain progressive tool visibility.

No model call, provider call, entitlement mutation, tool dispatch or gateway behavior.
It consumes the existing task-profile candidate and current authorized schema builder
to measure the exact model-visible payload a future gateway intersection would produce.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.neuralweb import ask_brain as _ab
from engine.neuralweb import brain_gateway as _bg


def _compact_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _schema_chars(schemas: list[dict]) -> int:
    return len(_compact_json(schemas))


def _profile_projection(profile: str, full: list[dict]) -> dict[str, Any]:
    full_chars = _schema_chars(full)
    if profile == "ambiguous":
        selected = full
        missing: list[str] = []
        byte_equivalent = _compact_json(selected) == _compact_json(full)
    else:
        wanted = _ab._TASK_PROFILE_TOOL_NAMES[profile]
        wanted_set = set(wanted)
        selected = [row for row in full if row.get("name") in wanted_set]
        found = {str(row.get("name") or "") for row in selected}
        missing = [name for name in wanted if name not in found]
        byte_equivalent = False
    chars = _schema_chars(selected)
    reduction = 0.0 if not full_chars else round((1.0 - chars / full_chars) * 100.0, 1)
    return {
        "profile": profile,
        "tool_count": len(selected),
        "schema_chars": chars,
        "reduction_pct": reduction,
        "missing_tools": missing,
        "tool_names": [str(row.get("name") or "") for row in selected],
        "byte_equivalent_full": byte_equivalent,
    }


def build_report(root: Path) -> dict[str, Any]:
    full = _bg._all_brain_tool_schemas(
        Path(root), page="", internals_allowed=False, user_id=""
    )
    rows = [
        _profile_projection(name, full)
        for name in (*_ab._TASK_PROFILE_TOOL_NAMES.keys(), "ambiguous")
    ]
    strict_passed = all(
        not row["missing_tools"]
        and (
            row["byte_equivalent_full"]
            if row["profile"] == "ambiguous"
            else row["reduction_pct"] >= 70.0
        )
        for row in rows
    )
    return {
        "schema": "brain.task_profile_qualification.v1",
        "authority": "qualification_only",
        "gateway_enforcement": False,
        "full": {
            "tool_count": len(full),
            "schema_chars": _schema_chars(full),
            "tool_names": [str(row.get("name") or "") for row in full],
        },
        "profiles": rows,
        "strict_passed": strict_passed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(Path(args.root))
    print(_compact_json(report))
    return 0 if (not args.strict or report["strict_passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
