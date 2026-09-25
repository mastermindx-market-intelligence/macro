"""Build the single-name IV-skew context surface.

  1. ACCRUE — upsert today's per-underlying skew into the forward snapshot ledger
     (data/options_skew/snapshots.parquet). This is the apparatus that, run daily,
     eventually gives scripts/validate_options_skew.py the history to earn a verdict.
     `--accrue` resolves the COMPLETE store session (the FULL S panel, never the
     partial newest D), walks backward through the missed sessions, and calls
     `backfill_from_store` on every date in that range. A ledger already caught
     up to the complete session backfills zero rows.
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

# A-F03-W2-8 (2026-09-23). The launchd runner (ops/launchd/run_skew_accrual.sh)
# treats rc 3 as a CAUGHT-UP NO-OP — the store's complete session S is already
# on the ledger, so the daily maintainer's backfill writes zero rows. The seat
# ruling makes that a lawful rc=0 exit at the runner, but the builder's own
# `--accrue`-only invocation still needs a way to surface the no-op distinctly
# from "the builder fell through to its default no-op (rc=0)". This constant
# is the SO PIN — documented here next to the argparse help; the launchd
# runner branches on the literal rc 3 (`accrue_rc == 3`) and
# tests/test_skew_accrual_launchd.py's FAKE_ACCRUE_NOOP exits 3 to pin it.
# exit 3 = accrue leg selected alone and the ledger was already caught up:
# the complete store session is on the ledger, nothing to write.
ACCRUE_NOOP_EXIT = 3


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

    ThetaData branch resolves the COMPLETE store session (the FULL S panel,
    never the partial newest D) and backfills every missed session on the
    path from the ledger's newest complete thetadata row. A caught-up
    ledger — the store's complete session S is already on the ledger so
    the backfill writes zero rows — returns `(0, "caught_up")`. The
    unresolved-store path preserves the existing warning line and skips
    the write entirely.

    A-F03-W2-8 (2026-09-23): the caught-up signal is the backfill
    receipt's `dates_backfilled == len(dates) AND rows_added + rows_replaced == 0`
    — BOTH conjuncts are required. `catch_up_sessions` returning `[]` is
    NOT the signal (the helper always returns at least the target session).
    The strict discriminator excludes store-miss: a backfill with
    `dates_not_in_store > 0` reports `dates_backfilled < len(dates)` and
    falls through to the rc-0 path so the runner's BLOCKER-2 verify step
    still aborts loud on a real failure. A caught-up ledger IS the case
    the verify step's BLOCKER-2 rule was written to refuse, but refusing
    the publish under "nothing to accrue" is the wrong outcome — the
    daily maintainer's session has already landed, the lane did its job,
    and the operator wants a clean rc-0 exit. The launchd runner treats
    rc 3 as a one-line receipt + rc-0 exit, skipping verify AND publish.
    """
    if S._legacy_enabled():
        chain = S._legacy_chain()
        if chain is None:
            return 0, "ledger_only"
        added = S.snapshot(today=today, chain=chain, source="polygon_gex")
        return added, "accrued_today"
    from engine.thetadata_store import resolve_thetadata_store
    td = resolve_thetadata_store(required=False, purpose="options_skew chain")
    if td is None:
        # Keep the existing warning line by calling load_chain() — it prints
        # `::warning title=options-skew-source::` and returns the typed state.
        chain, state = S.load_chain()
        return 0, "ledger_only"
    info = S.complete_store_session(td)
    session = info["session"]
    if session is None:
        return 0, "ledger_only"
    dates = S.catch_up_sessions(session, S.load_history())
    receipt = S.backfill_from_store(dates, store=td)
    rows_touched = receipt["rows_added"] + receipt["rows_replaced"]
    # A-F03-W2-8 (2026-09-23): the rc-3 (caught-up) surface is RESERVED for
    # the byte-equal-COMPLETE-STORE-SESSION-on-the-ledger case. A zero-row
    # backfill alone is NOT enough — a store-miss (`dates_not_in_store > 0`,
    # `dates_backfilled < len(dates)`) also reports zero rows touched, but
    # that outcome is a real failure and must keep the rc-0 path so the
    # runner's BLOCKER-2 verify step can still abort loud. The
    # discriminator: every requested date was found in the store
    # (`dates_backfilled == len(dates)`) AND the backfill was a byte-equal
    # no-op (`rows_touched == 0`). Either signal alone is ambiguous:
    # `rows_touched == 0` is shared by store-miss + weekend-skip +
    # caught-up; `dates_backfilled == len(dates)` is shared by caught-up +
    # real-write (which has rows_touched > 0). Seat round 4: a store that
    # COVERS the session but whose panel yields zero ledger rows (empty
    # `skew_map(chain)`) also reports dates_backfilled == len(dates) with
    # all-zero counts — that is "something to accrue and it did not land",
    # so the no-op additionally requires `rows_unchanged > 0`: the backfill
    # must have COMPARED real rows and found every one byte-equal. Pinned by
    # tests/test_options_skew.py: store-miss, covered-but-empty-panel and
    # bootstrap RED tests.
    if (
        dates
        and receipt["dates_backfilled"] == len(dates)
        and rows_touched == 0
        and receipt["rows_unchanged"] > 0
    ):
        # A-F03-W2-8 (2026-09-23): caught-up ledger is a LAWFUL no-op.
        # The complete store session S is already on the ledger with
        # byte-equal values, so the daily maintainer's backfill wrote
        # zero rows. Bare `print()` — never the logger — so the GitHub
        # annotation parser picks it up at line start
        # (tests/test_gh_annotation_line_start.py).
        print(
            f"::notice title=options-skew-accrual::caught up — complete "
            f"session {session} already on the ledger; nothing to accrue",
            flush=True,
        )
        log.info(
            "options_skew: accrual sessions=%s backfilled=%d added=%d "
            "replaced=%d unchanged=%d not_in_store=%d",
            dates,
            receipt["dates_backfilled"],
            receipt["rows_added"],
            receipt["rows_replaced"],
            receipt["rows_unchanged"],
            receipt["dates_not_in_store"],
        )
        return 0, "caught_up"
    log.info(
        "options_skew: accrual sessions=%s backfilled=%d added=%d replaced=%d "
        "unchanged=%d not_in_store=%d",
        dates,
        receipt["dates_backfilled"],
        receipt["rows_added"],
        receipt["rows_replaced"],
        receipt["rows_unchanged"],
        receipt["dates_not_in_store"],
    )
    return rows_touched, "accrued_today"


def emit(today=None, accrual_state: str = "ledger_only") -> dict:
    """Write site/options_skew/latest.json from the ledger. No chain provider.

    The payload carries the A-F03-W2-4c additive keys `source_windows`,
    `source_break`, and `source_break_date` (round-5 coverage-span model
    — one span per source present on the ledger, plus the first session
    date strictly after the older source's last_date).  Schema string
    (`options_skew.v1`) is unchanged; downstream consumers that pre-date
    the additive keys stay silent on the source_break gate.

    `accrual_state` accepts the builder's internal vocabulary
    (`accrued_today` | `caught_up` | `ledger_only`); `caught_up` is mapped
    to `ledger_only` here because the engine contract is the legacy two-way
    one (`accrued_today | ledger_only` — emit_from_ledger raises on any
    other value). The mapping happens in the BUILDER, not the engine.
    """
    engine_state = "ledger_only" if accrual_state == "caught_up" else accrual_state
    payload = S.emit_from_ledger(today=today, accrual_state=engine_state)
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
        # A-F03-W2-8 (2026-09-23): caught-up ledger on the sole-leg `--accrue`
        # call returns ACCRUE_NOOP_EXIT (3) so the launchd runner can branch
        # on it (one-line receipt + skip verify/publish + exit 0). The
        # render hosts and the regional desk builders always run `--emit`
        # (with or without `--accrue`), and they MUST keep seeing rc 0 on a
        # caught-up ledger — `emit()`'s `accrual_state="caught_up"` maps to
        # `ledger_only` so the payload contract is unchanged. So the rc-3
        # surface is strictly `--accrue` alone.
        if (
            do_accrue
            and not do_emit
            and not do_backfill
            and accrual_state == "caught_up"
        ):
            return ACCRUE_NOOP_EXIT
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
