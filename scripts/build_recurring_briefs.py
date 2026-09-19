"""Entry point for the recurring briefs producer (F11 packet B-F11-7b).

    python -m scripts.build_recurring_briefs --cadence daily_after_us_close|weekly_saturday
        [--dry-run] [--run-date YYYY-MM-DD]

Dormant by default (F08 / thesis-monitor precedent): only writes real rows when
RECURRING_BRIEFS_ENABLE=1 is set in the environment; otherwise forces --dry-run.
Always exits 0: a missing table, missing credentials, or an unmerged
migration is a known deployment state, not a build failure.

Slot source (R4 + slot-clock fix): the published artifact's asof is the slot.
A weekly artifact built this Saturday run carries Friday market state but
was generated on the run_date — the binding clock is the artifact's
``generated_at``, so ``weekly_saturday`` does not false-degrade every Saturday.
Same rule lets a daily nightly that crosses UTC midnight pass.

Dry-run still writes nothing (frozen-spec item 2). It DOES print what it
would write (planned/duplicate counts and one line per row), and surfaces
write failures the same way the thesis monitor does.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import recurring_briefs as rb  # noqa: E402


def _parse_run_date(raw: str | None) -> date:
    if not raw:
        return datetime.now(timezone.utc).date()
    return date.fromisoformat(raw)


def _row_summary(row: dict) -> str:
    body = row.get("body") or {}
    sub_id = str(row.get("subscription_id") or "?")[:8]
    target_name = (
        ((body.get("target") or {}).get("name") or "?")
        if isinstance(body.get("target"), dict)
        else "?"
    )
    sentences = body.get("market_read") or []
    head = sentences[0]["sentence_en"] if sentences and isinstance(sentences[0], dict) else ""
    head = head.replace("\n", " ")
    return (
        f"-- subscription {sub_id}... "
        f"slot {row.get('slot_asof')} state {row.get('state')} "
        f"reason={row.get('degraded_reason') or '-'} "
        f"target={target_name!r} | {head[:90]}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cadence",
        required=True,
        choices=list(rb.CADENCES),
        help="daily_after_us_close or weekly_saturday",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be written; write nothing",
    )
    parser.add_argument("--run-date", default=None, help="YYYY-MM-DD (tests / seat)")
    args = parser.parse_args(argv)

    enabled = os.environ.get("RECURRING_BRIEFS_ENABLE") == "1"
    dry_run = args.dry_run or not enabled
    if not enabled:
        print(
            "recurring briefs: DORMANT (RECURRING_BRIEFS_ENABLE unset) — "
            "decisions only, no writes",
            flush=True,
        )

    run_date = _parse_run_date(args.run_date)
    result = rb.run(
        cadence=args.cadence,
        dry_run=dry_run,
        run_date=run_date,
    )

    slot = result.slot.isoformat() if result.slot else run_date.isoformat()
    line = (
        f"recurring briefs: {result.subscription_n} subscriptions, "
        f"{result.ready_n} ready, {result.degraded_n} degraded, slot {slot}"
    )
    print(line, flush=True)
    print(f"::notice title=recurring-briefs::{line}", flush=True)

    # H7: dry-run prints what it would write — planned/duplicate counts plus
    # one summary line per row the producer would write. Writes remain off
    # (frozen-spec item 2). The R6 summary line and ::notice above stay.
    if dry_run:
        print(
            f"recurring briefs (dry-run): {result.planned_n} planned, "
            f"{result.duplicate_n} duplicate",
            flush=True,
        )
        for row in result.planned_rows:
            print(_row_summary(row), flush=True)

    # H8: write failures visible. Persistent 500/RLS/network errors MUST
    # surface as a ::warning line so the workflow's ``|| echo "::warning::…"``
    # can fire. Mirrors scripts/run_thesis_condition_monitor.py:50.
    if result.error_n > 0:
        print(
            f"::warning title=recurring-briefs-write-error::"
            f"{result.error_n} write error(s) — outcome=write_error "
            f"ready={result.ready_n} degraded={result.degraded_n} run incomplete",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
