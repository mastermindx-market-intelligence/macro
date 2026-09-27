#!/usr/bin/env python3
"""Prepare an inactive Options Context Audit v2 plan.

This CLI only exercises the successor scanner. It never resolves trusted
context, writes a receipt, changes a ledger, or activates a service. A refusal
is printed as machine-readable JSON and exits 2; a prepared plan exits 0.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.options_market_memory_context_v2 import (
    AuditPlan,
    Refusal,
    SourceManifest,
    SourceSpec,
    build_audit_plan,
    validate_audit_plan,
)


def _source(value: str, *, root: Path, consumed: bool, reason: str | None = None) -> SourceSpec:
    if "=" not in value:
        raise argparse.ArgumentTypeError("source must be PATH=ROLE")
    path_text, role = value.split("=", 1)
    if not path_text.strip() or not role.strip():
        raise argparse.ArgumentTypeError("source PATH and ROLE must be non-empty")
    return SourceSpec(
        root / path_text,
        role.strip(),
        consumed=consumed,
        exclusion_reason=reason,
    )


def _plan_payload(plan: AuditPlan) -> dict[str, object]:
    return {
        "status": "PREPARED",
        "schema": plan.schema,
        "trusted_context": plan.trusted_context,
        "published": plan.published,
        "row_count": plan.row_count,
        "stream_sha256": plan.stream_sha256,
        "snapshots": [snapshot.as_dict() for snapshot in plan.snapshots],
        "excluded": list(plan.excluded),
        "run_paths": [path.as_posix() for path in plan.run_paths if path.exists()],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--source", action="append", required=True, metavar="PATH=ROLE")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATH=REASON",
        help="explicitly classify an adjacent artifact without consuming it",
    )
    parser.add_argument("--run-directory", type=Path)
    parser.add_argument("--max-rows-per-run", type=int, default=1024)
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    try:
        consumed = tuple(_source(item, root=root, consumed=True) for item in args.source)
        excluded = tuple(
            _source(item, root=root, consumed=False, reason=item.split("=", 1)[1])
            for item in args.exclude
        )
        manifest = SourceManifest(consumed, excluded)
        result = build_audit_plan(
            manifest,
            args.run_directory,
            max_rows_per_run=args.max_rows_per_run,
        )
    except (ValueError, OSError) as exc:
        print(
            json.dumps(
                {"status": "REFUSED", "code": "SOURCE_MANIFEST_INCOMPLETE", "message": str(exc)},
                sort_keys=True,
            )
        )
        return 2
    if isinstance(result, Refusal):
        print(json.dumps({"status": "REFUSED", "refusal": result.as_dict()}, sort_keys=True))
        return 2
    validation = validate_audit_plan(result)
    if validation is not None:
        print(json.dumps({"status": "REFUSED", "refusal": validation.as_dict()}, sort_keys=True))
        return 2
    print(json.dumps(_plan_payload(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
