"""One-time (resumable) backfill of the massive.com whole-market daily OHLCV store.

URGENCY: massive.com's entitlement is a ROLLING ~5-year→present window (probed
2026-07-03: floor = 2021-07-06).  Each month of delay permanently loses a month of
history.  Run this ASAP on a machine with MASSIVE_S3_* credentials.

The backfill is RESUMABLE and GAP-AWARE: it records every processed day in
data/massive_stock_day/_backfill_state.json (processed_days, v2), so a killed run
restarts on exactly the missing days — including interior holes, not just the tip.

Expected run time: ~40 s per trading day (the ~12k-parquet per-day upsert dominates,
  not the ~0.8 MB download) ≈ 4-5 h per captured year.  Total download ≈ 200 MB/yr.

Usage:
  # Full backfill (earliest-first, resumable):
  python -m scripts.backfill_massive_stock_day

  # Smoke test: just the most-recent 3 days (verify credentials + schema):
  python -m scripts.backfill_massive_stock_day --smoke

  # Limit to N days (for a partial run in this session):
  python -m scripts.backfill_massive_stock_day --max-days 30

  # Force restart (ignore resume state, NOT for missing ticker bars):
  python -m scripts.backfill_massive_stock_day --force

  # Explicit original-store owner repair for a processed day missing three
  # constituent bars. ONLY on the restored source-host store, serialized against
  # the nightly restore/collect/publish lane; no global resume-state reset:
  python -m scripts.backfill_massive_stock_day --repair-day 2026-08-18 --repair-tickers GOOGL,MSFT,TSLA

  # First verify each original restored ticker/day and the correction receipt.
  # Any PARTIAL/REFUSED result needs same-owner reconciliation; do not publish.

After completion, publish to R2:
  python -m scripts.publish_r2 --dirs massive_stock_day
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("backfill_massive_stock_day")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true",
                    help="3-day smoke test: capture just the 3 most-recent entitled days")
    ap.add_argument("--max-days", type=int, default=None,
                    help="stop after N trading days (for partial runs)")
    ap.add_argument("--start", default=None,
                    help="override start date YYYY-MM-DD (default: 2025-01-02)")
    ap.add_argument("--end", default=None,
                    help="override end date YYYY-MM-DD (default: latest_available())")
    ap.add_argument("--force", action="store_true",
                    help="ignore resume state and restart from --start")
    ap.add_argument("--repair-day", default=None,
                    help="operator-only processed NYSE day with missing member bars")
    ap.add_argument("--repair-tickers", default=None,
                    help="1..16 comma-delimited existing uppercase source tickers")
    ap.add_argument("--pace", type=float, default=0.05,
                    help="sleep seconds between day fetches (default 0.05)")
    args = ap.parse_args()

    from collectors.massive_stock_day import (
        backfill, repair_processed_day_missing_members,
        _store_dir, _backfill_state_path, _manifest_path, EARLIEST_ENTITLED,
    )
    from collectors.massive_flatfiles import latest_available, enabled

    if args.repair_day is not None or args.repair_tickers is not None:
        # --force deletes the global state. NEVER combine it with an isolated
        # member-hole repair. Ordinary backfill/smoke/pace options are a
        # different source operation and cannot silently change this request.
        if (not args.repair_day or not args.repair_tickers or args.force or args.smoke
                or args.max_days is not None or args.start is not None
                or args.end is not None or args.pace != 0.05):
            ap.error("--repair-day and --repair-tickers require an isolated request")
        try:
            day = date.fromisoformat(args.repair_day)
            if day.isoformat() != args.repair_day:
                raise ValueError("noncanonical date")
            tickers = tuple(args.repair_tickers.split(","))
            result = repair_processed_day_missing_members(day, tickers)
        except ValueError:
            ap.error("invalid operator-only repair day or ticker set")
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in {"REPAIRED", "ALREADY_PRESENT"} else 1

    if not enabled():
        log.error(
            "MASSIVE_S3_* credentials not set.  Export:\n"
            "  MASSIVE_S3_ENDPOINT=https://files.massive.com\n"
            "  MASSIVE_S3_ACCESS_KEY_ID=<key>\n"
            "  MASSIVE_S3_SECRET_ACCESS_KEY=<secret>\n"
            "  MASSIVE_S3_BUCKET=flatfiles\n"
            "or source the project .env file."
        )
        return 1

    if args.force:
        state_p = _backfill_state_path()
        if state_p.exists():
            state_p.unlink()
            log.info("Resume state cleared (--force)")

    start = date.fromisoformat(args.start) if args.start else EARLIEST_ENTITLED
    end = date.fromisoformat(args.end) if args.end else None

    if args.smoke:
        entitled = latest_available("stock_day", lookback=7)
        if not entitled:
            log.error("Cannot determine latest entitled date — check credentials")
            return 1
        start = entitled - timedelta(days=6)
        end = entitled
        args.max_days = 3
        log.info("SMOKE TEST: capturing up to 3 days (%s → %s)", start, end)

    result = backfill(
        start=start,
        end=end,
        max_days=args.max_days,
        pace_s=args.pace,
    )

    print(json.dumps(result, indent=2))

    if result.get("blocked"):
        return 1

    # Report remaining work if we stopped early (backfill() counts it exactly now)
    remaining = int(result.get("days_remaining", 0) or 0)
    if remaining:
        secs_per_day = 40 + args.pace   # observed ~40 s/day (per-day 12k-parquet upsert)
        log.info(
            "Partial run: %d day(s) fetched, %d still missing in the window.  "
            "Estimated remaining: %d days × ~%.0fs ≈ %.1f h — re-run to resume.",
            result["days_fetched"], remaining, remaining,
            secs_per_day, remaining * secs_per_day / 3600,
        )

    log.info("Store location: %s", _store_dir())
    log.info("Manifest:       %s", _manifest_path())
    log.info(
        "\nNext step (when complete):\n"
        "  python -m scripts.publish_r2 --dirs massive_stock_day --force-manifest"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
