"""Entry point for the recurring briefs producer (F11 packet B-F11-7b).

    python -m scripts.build_recurring_briefs --cadence daily_after_us_close|weekly_saturday
        [--dry-run] [--run-date YYYY-MM-DD]

Dormant by default (F08 / thesis-monitor precedent): only writes real rows when
RECURRING_BRIEFS_ENABLE=1 is set in the environment; otherwise forces --dry-run.
Always exits 0: a missing table, missing credentials, or an unmerged
migration is a known deployment state, not a build failure.

Slot source (R4): daily reads site/intelligence/briefing.json `as_of`;
weekly reads site/master_brief.json `state_asof`.
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
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
