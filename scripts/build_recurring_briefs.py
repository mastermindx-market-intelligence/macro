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

Dry-run still writes nothing (frozen-spec item 2). It prints aggregate
counts plus one privacy-safe row summary (slot/state only) per planned row;
target names, IDs and body text never enter workflow logs. Read failures and
write failures are surfaced explicitly.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import recurring_briefs as rb  # noqa: E402


def _parse_run_date(raw: str | None) -> date:
    if not raw:
        return rb.owner_run_date()
    return date.fromisoformat(raw)


def _row_summary(row: dict) -> str:
    """Privacy-safe dry-run summary: never log subscription/target/body content."""
    return f"-- planned row slot {row.get('slot_asof')} state {row.get('state')}"


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

    if result.skipped_non_session:
        line = (
            f"recurring briefs: not due — no US cash-equity session on "
            f"{run_date.isoformat()} (cadence={args.cadence})"
        )
        print(line, flush=True)
        print(f"::notice title=recurring-briefs::{line}", flush=True)
        return 0

    slot = result.slot.isoformat() if result.slot else run_date.isoformat()
    line = (
        f"recurring briefs: {result.subscription_n} subscriptions, "
        f"{result.ready_n} ready, {result.degraded_n} degraded, slot {slot}"
    )
    print(line, flush=True)
    print(f"::notice title=recurring-briefs::{line}", flush=True)

    if result.subscription_read_state == "unavailable":
        error_class = result.subscription_read_error or "unknown"
        print(
            f"::warning title=recurring-briefs-subscription-read-unavailable::"
            f"subscription read unavailable ({error_class}); "
            f"no target objects were read and no rows were written",
            flush=True,
        )
    elif result.read_unavailable > 0:
        print(
            f"::warning title=recurring-briefs-target-read-unavailable::"
            f"{result.read_unavailable} target read(s) unavailable; "
            f"honest degraded rows written without inferring deletion",
            flush=True,
        )

    # H7: dry-run prints aggregate counts plus one privacy-safe slot/state
    # line per planned row. Writes remain off (frozen-spec item 2).
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
