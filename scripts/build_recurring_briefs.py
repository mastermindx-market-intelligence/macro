"""Entry point for the recurring briefs producer (F11 packet B-F11-7b).

    python -m scripts.build_recurring_briefs --cadence daily_after_us_close|weekly_saturday
        [--dry-run] [--run-date YYYY-MM-DD]

Dormant by default (F08 / thesis-monitor precedent): when
RECURRING_BRIEFS_ENABLE=1 is NOT set, the CLI exits 0 BEFORE any subscription
read, BEFORE rb.run(), and BEFORE any user-authored target/body text is
printed — only a DORMANT line plus a ::notice. This is the Sol #7106 review
(2026-09-19, REQUEST_CHANGES) hotfix (merged as #7411): a dormant workflow
run must not leak subscription target/body text into the Actions log. The
repair round on top of this path (aggregate-only diagnostics, NYSE-session
gate, typed read state) is in the same branch.

When RECURRING_BRIEFS_ENABLE=1 is set the CLI runs rb.run() as usual.
Always exits 0: a missing table, missing credentials, or an unmerged
migration is a known deployment state, not a build failure.

Slot source (R4 + slot-clock fix): the published artifact's asof is the slot.
A weekly artifact built this Saturday run carries Friday market state but
was generated on the run_date — the binding clock is the artifact's
``generated_at``, so ``weekly_saturday`` does not false-degrade every Saturday.
Same rule lets a daily nightly that crosses UTC midnight pass.

With RECURRING_BRIEFS_ENABLE unset the CLI is DORMANT: it returns before
any subscription read, decision or write and prints one aggregate line plus a
``::notice``. When enabled, ``--dry-run`` writes nothing and prints
aggregate-only diagnostics — subscription, ready, degraded, planned,
duplicate, error counts plus the slot; without ``--dry-run`` it writes. Never
a per-row line and never subscription text; aggregate-only is the F11-7b
repair-round contract. Persistent write failures surface the same way the
thesis monitor does.
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
        # Sol #7106 review (2026-09-19, REQUEST_CHANGES): a dormant run must not
        # read subscriptions and must not print user-authored target/body text
        # into workflow logs. The privacy/session/read-state repair lives in this
        # carrier; DORMANT means zero reads, zero decisions, zero writes, zero user text.
        print(
            "recurring briefs: DORMANT (RECURRING_BRIEFS_ENABLE unset) — "
            "no subscription read, no decisions, no writes",
            flush=True,
        )
        print(
            "::notice title=recurring-briefs::DORMANT (RECURRING_BRIEFS_ENABLE unset)"
            " — 0 reads, 0 writes",
            flush=True,
        )
        return 0

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

    # H7 (Round 6 aggregate-only contract): dry-run prints aggregate
    # planned/duplicate counts plus the slot. NO per-row summary line —
    # _row_summary used to leak the subscription's user-authored target
    # name and market_read[0].sentence_en into stdout/stderr (Sol #7106
    # REQUEST_CHANGES blocker 1). Writes remain off (frozen-spec item 2).
    # The R6 summary line and ::notice above stay.
    if dry_run:
        print(
            f"recurring briefs (dry-run): {result.planned_n} planned, "
            f"{result.duplicate_n} duplicate",
            flush=True,
        )

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
    # Round 6 (h_7106_r6, Sol #7106 blocker 3): a non-ok read state is a
    # non-calm outcome. Mirror H8 with a `::warning
    # title=recurring-briefs-read-unavailable::` line so the workflow's
    # `|| echo "::warning::…"` can fire. Healthy empty (state=ok + rows=())
    # stays a quiet zero — no warning. read_error carries the typed
    # diagnostic (no secrets, no row content).
    if getattr(result, "read_state", rb.READ_STATE_OK) != rb.READ_STATE_OK:
        diag = getattr(result, "read_error", None) or "unspecified"
        print(
            f"::warning title=recurring-briefs-read-unavailable::"
            f"read state={result.read_state} ({diag}) — "
            f"outcome=read_unavailable 0 subscriptions 0 ready 0 degraded "
            f"no writes (run incomplete)",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
