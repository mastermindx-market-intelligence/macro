"""Project committed earnings-call events into the canonical marketing outbox.

This is the missing runtime caller for :mod:`engine.marketing.earnings_call_lane`.
It does not publish to X and it creates no new queue: the only write path is the
existing tracked `data/marketing/outbox/*` owned by the Marketing system.

The runner deliberately loads `config/marketing.yml` and passes it into the lane.
Without that, `wire_routing.route(..., cfg=None)` falls back to its config-less
historical default instead of the operator-owned earnings route.

Usage:
    python -m scripts.marketing_earnings_call_projection
    python -m scripts.marketing_earnings_call_projection --dry-run

Exit policy:
    0  healthy projection, including quiet/duplicate/correction-held passes
    2  committed Chronicle ledger failed integrity validation

Corrections and per-event refusals are GitHub annotations but do not abort the whole
batch. The lane already fails those events closed; the workflow can still commit any
other safe queued rows from the same pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.marketing import earnings_call_lane as lane  # noqa: E402


def _repo_root() -> Path:
    return _ROOT


def _load_marketing_config(root: Path) -> dict[str, Any]:
    """Load the operator-owned route or fail closed before any enqueue work."""

    path = root / "config" / "marketing.yml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path}: root must be a mapping")

    wire = data.get("wire_routing")
    classes = wire.get("classes") if isinstance(wire, dict) else None
    earnings_owner = classes.get("earnings") if isinstance(classes, dict) else None
    if not str(earnings_owner or "").strip():
        raise RuntimeError(
            f"{path}: wire_routing.classes.earnings is required; "
            "refusing config-less fallback routing"
        )
    return data


def _compact(result: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "input_rows",
        "eligible_rows",
        "stale_rows",
        "capped_rows",
        "gap",
        "integrity_blocked",
        "config_blocked",
        "queued",
        "dry_run",
        "duplicates",
        "corrections_required",
    )
    out = {key: result.get(key) for key in keys}
    out["results"] = [
        {
            key: row.get(key)
            for key in ("event_id", "status", "reason", "prior_item_id", "prior_status")
            if row.get(key) not in (None, "")
        }
        for row in result.get("results", [])
        if isinstance(row, dict)
    ]
    return out


def run(
    *,
    root: Path,
    dry_run: bool,
    max_call_age_days: int,
    max_events: int,
) -> tuple[dict[str, Any], int]:
    try:
        cfg = _load_marketing_config(root)
    except RuntimeError as exc:
        result = {
            "input_rows": 0,
            "eligible_rows": 0,
            "stale_rows": 0,
            "capped_rows": 0,
            "gap": None,
            "integrity_blocked": False,
            "config_blocked": True,
            "results": [],
            "queued": 0,
            "dry_run": 0,
            "duplicates": 0,
            "corrections_required": 0,
        }
        print(
            "::error title=earnings-call-marketing-config-invalid::" + str(exc),
            flush=True,
        )
        return result, 2

    result = lane.run_ledger(
        root=root,
        cfg=cfg,
        dry_run=dry_run,
        spool=False,
        max_call_age_days=max_call_age_days,
        max_events=max_events,
    )

    print(
        "[earnings-call-projection] "
        + json.dumps(_compact(result), sort_keys=True, separators=(",", ":")),
        flush=True,
    )

    if result.get("integrity_blocked"):
        print(
            "::error title=earnings-call-ledger-integrity::"
            + str(result.get("gap") or "committed Chronicle ledger is not safe to read"),
            flush=True,
        )
        return result, 2

    for row in result.get("results", []):
        if not isinstance(row, dict):
            continue
        event_id = str(row.get("event_id") or "unknown")
        status = str(row.get("status") or "")
        reason = str(row.get("reason") or "")
        if status == "correction_required":
            print(
                "::warning title=earnings-call-correction-held::"
                f"{event_id}: prior revision remains authoritative until an explicit "
                f"correction supersede is performed"
                + (f" ({reason})" if reason else ""),
                flush=True,
            )
        elif status in {"invalid", "refused", "media_unhosted"}:
            print(
                "::warning title=earnings-call-projection-refused::"
                f"{event_id}: {status}"
                + (f" ({reason})" if reason else ""),
                flush=True,
            )

    return result, 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project recent committed earnings-call events into the Marketing outbox."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_repo_root(),
        help="Repository root (defaults to the checkout containing this script).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the full projection without writing media or outbox rows.",
    )
    parser.add_argument(
        "--max-call-age-days",
        type=int,
        default=lane.DEFAULT_MAX_CALL_AGE_DAYS,
        help="Oldest call_date admitted into this pass.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=lane.DEFAULT_MAX_EVENTS,
        help="Maximum recent eligible events processed in one pass.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _result, code = run(
        root=args.root.resolve(),
        dry_run=bool(args.dry_run),
        max_call_age_days=max(0, int(args.max_call_age_days)),
        max_events=max(0, int(args.max_events)),
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
