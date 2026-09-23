"""Build the single-name IV-skew context surface.

  1. ACCRUE — upsert today's per-underlying skew into the forward snapshot ledger
     (data/options_skew/snapshots.parquet). This is the apparatus that, run daily,
     eventually gives scripts/validate_options_skew.py the history to earn a verdict.
  2. EMIT — site/options_skew/latest.json from that ledger (display-only context;
     the gate stays closed until the panel is wide/long enough).
  3. BACKFILL — recompute an inclusive date range from the ThetaData store into
     that ledger. A thetadata row replaces a polygon_gex row for the same date
     and name. Weekend dates are skipped, not moved onto a neighbouring session.

No flag runs ACCRUE and EMIT, which is what today's callers do. `--accrue` and
`--emit` run one leg. `--backfill FROM TO` runs only the backfill leg unless
`--accrue` or `--emit` is also passed. EMIT never opens a chain store. When the
ThetaData store does not resolve, ACCRUE and BACKFILL print the source warning
and do not fail the lane.
"""
from __future__ import annotations

import argparse
import json
import logging

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import options_skew as S  # noqa: E402
from lib import config  # noqa: E402

log = logging.getLogger("build_options_skew")


def _parse(argv: list[str] | None):
    ap = argparse.ArgumentParser(prog="scripts.build_options_skew")
    ap.add_argument("--accrue", action="store_true",
                    help="upsert the snapshot ledger and do not write latest.json")
    ap.add_argument("--emit", action="store_true",
                    help="write latest.json from the ledger and do not open a chain")
    ap.add_argument("--backfill", nargs=2, metavar=("FROM", "TO"), default=None,
                    help="recompute this inclusive date range from the ThetaData store")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --backfill, count what would change and do not write")
    ap.add_argument("--roots", default=None,
                    help="optional comma-separated root list for --backfill")
    ap.add_argument("--ledger", default=None,
                    help="parquet ledger path (default: the data-dir snapshots file)")
    return ap.parse_args(argv)


def _selected(args) -> tuple[bool, bool, bool]:
    """Return (accrue, emit, backfill). Bare argv still runs accrue and emit."""
    if args.backfill is None and not args.accrue and not args.emit:
        return True, True, False
    return bool(args.accrue), bool(args.emit), args.backfill is not None


def _inclusive_iso_dates(start: str, end: str) -> list[str]:
    try:
        first = date.fromisoformat(start)
        last = date.fromisoformat(end)
    except ValueError as exc:
        raise ValueError(
            "The backfill dates must be real calendar dates written as YYYY-MM-DD. "
            "回补日期必须写成 YYYY-MM-DD 形式的真实日期。"
        ) from exc
    if last < first:
        raise ValueError(
            "The backfill start date must be on or before the end date. "
            "回补的开始日期必须不晚于结束日期。"
        )
    days: list[str] = []
    cursor = first
    while cursor <= last:
        days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return days


def _parse_roots(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    roots = [part.strip() for part in str(raw).split(",") if part.strip()]
    return roots or None


def _pin_ledger(path: str) -> None:
    """Point the ledger reader and writer at `path` for this process."""
    target = Path(path).expanduser()

    def _pinned() -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    S._snap_path = _pinned


def accrue(today=None) -> tuple[int, str]:
    """Upsert the ledger. Returns (rows_changed, accrual_state).

    `thetadata_store_unresolved` prints the existing warning (inside load_chain)
    and skips the write entirely — no empty row, no rewrite.
    """
    if S._legacy_enabled():
        chain = S._legacy_chain()
        if chain is None:
            return 0, "ledger_only"
        added = S.snapshot(today=today, chain=chain, source="polygon_gex")
        return added, "accrued_today"
    chain, state = S.load_chain()
    if state == "thetadata_store_unresolved" or chain is None:
        return 0, "ledger_only"
    added = S.snapshot(today=today, chain=chain, source="thetadata")
    return added, "accrued_today"


def emit(today=None, accrual_state: str = "ledger_only") -> dict:
    """Write site/options_skew/latest.json from the ledger. No chain provider."""
    payload = S.emit_from_ledger(today=today, accrual_state=accrual_state)
    out = config.site_dir() / "options_skew"
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(
        json.dumps(payload, separators=(",", ":"), default=float)
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse(argv)
    previous_snap = S._snap_path
    try:
        if args.ledger:
            _pin_ledger(args.ledger)
        do_accrue, do_emit, do_backfill = _selected(args)
        if do_backfill:
            try:
                dates = _inclusive_iso_dates(args.backfill[0], args.backfill[1])
            except ValueError as exc:
                print(str(exc), flush=True)
                return 2
            receipt = S.backfill_from_store(
                dates, roots=_parse_roots(args.roots), dry_run=bool(args.dry_run),
            )
            print(json.dumps(receipt, separators=(",", ":")), flush=True)
        added = 0
        accrual_state = "ledger_only"
        if do_accrue:
            added, accrual_state = accrue()
        payload = emit(accrual_state=accrual_state) if do_emit else None
        if payload is not None:
            # A-F03-W2-4c · the source_windows count surfaces the source break
            # in the lane's summary log so an operator skimming build_options_skew
            # output can tell at a glance whether this run mixed vendors.
            log.info("options_skew: accrued %d rows, emitted %d names (scored=%s, %s, windows=%d)",
                     added, payload["n"], payload["scored"], payload["gate_status"],
                     len(payload.get("source_windows") or []))
        elif do_accrue:
            log.info("options_skew: accrued %d rows (emit skipped)", added)
        return 0
    finally:
        S._snap_path = previous_snap


if __name__ == "__main__":
    raise SystemExit(main())
