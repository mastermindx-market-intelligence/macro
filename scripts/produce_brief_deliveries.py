"""scripts/produce_brief_deliveries.py -- entry point for the brief deliveries producer.

    python -m scripts.produce_brief_deliveries [--dry-run] [--now ISO8601]

Dormant by default (F08 precedent): only writes real rows when BRIEF_DELIVERIES_ENABLE=1
is set in the environment; otherwise forces --dry-run and prints a DORMANT line.
Imports ONLY engine.brief_delivery_producer -- never app.mailer, never engine.capital_structure.
Always exits 0: a missing table, missing credentials, or an unmerged migration is a known
deployment state, not a build failure.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import brief_delivery_producer as producer  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--now", default=None, help="ISO8601 override, for tests/ops.")
    args = parser.parse_args(argv)

    enabled = os.environ.get("BRIEF_DELIVERIES_ENABLE") == "1"
    dry_run = args.dry_run or not enabled
    if not enabled:
        print(
            "brief-deliveries: DORMANT (BRIEF_DELIVERIES_ENABLE unset) — "
            "decisions only, no writes",
            flush=True,
        )

    result = producer.run(now_utc=args.now, dry_run=dry_run, limit=500)

    if result.read_state == producer.READ_UNAVAILABLE:
        print(
            "::warning title=brief-deliveries-read-unavailable::"
            "%s (%s) — %d written so far, run incomplete"
            % (producer.READ_UNAVAILABLE, result.error_class, result.written_n),
            flush=True,
        )

    written_label = "planned" if dry_run else "written"
    written_n = result.planned_n if dry_run else result.written_n

    print(
        "brief-deliveries: outcome=%s read_state=%s planned=%d %s=%d "
        "duplicate=%d dry_run=%s run_id=%s"
        % (
            result.outcome,
            result.read_state,
            result.planned_n,
            written_label,
            written_n,
            result.duplicate_n,
            dry_run,
            result.run_id,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
