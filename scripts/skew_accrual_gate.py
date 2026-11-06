"""Freshness gate for the ThetaData skew-accrual lane (MO-PAID-013 W2-2).

The skew-accrual runner (`ops/launchd/run_skew_accrual.sh`) calls this script
once per retry. We extract the gate into a Python helper rather than embedding
the parquet read in shell because the gate is the load-bearing logic the rest of
the lane depends on: the ledger can never be allowed to accrue from a stale
chain (a stale accrual corrupts the validation panel the lane is accruing
toward), and a unit-testable surface is the only thing that makes that
guarantee enforceable from CI.

SCOPE
  Only the freshness check. The accrual itself is owned by
  scripts/build_options_skew.py (W2-1b): `--accrue` flag, source-stamped ledger
  upsert. The runner calls that script once the gate says FRESH.

CONTRACT
  The store resolves from --store (THETADATA_STORE equivalent on the lane host);
  default is the canonical path on the M1 ops host. Reads only the 'date' column
  of one SPY EOD year shard — column-pruned, never loads the full store. The
  latest date in the shard is compared to lib.nyse_calendar.expected_last_session()
  via last_session_on_or_before() (T+1 plane: the EOD store at run time carries
  the session BEFORE today, which is the required floor).

  Exit 0 = FRESH (latest >= required).
  Exit 1 = STALE (latest < required or shard absent / empty).
  Exit 2 = RESOLVE_ERROR (store path missing the EOD tier entirely).
  Exit 3 = USAGE_ERROR (bad CLI args).

USAGE
  scripts/skew_accrual_gate.py [--store PATH] [--repo PATH] [--root SPY]
                                [--tier eod] [--required-date YYYY-MM-DD]

  Either `--required-date` OR a `--repo` pointing at a tree carrying
  lib.nyse_calendar.expected_last_session is required. When both are given,
  --required-date wins (operator override).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date as _date, timedelta
from pathlib import Path

# Repo-root pin so `lib.nyse_calendar` resolves under both `python -m` and bare
# invocation from the runner. Mirrors the strong-pin idiom enforced by
# `tests/test_check_script_import_pinning.py` for every scripts/** entry.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Exit codes are part of the contract — the runner's retry loop reads them.
EXIT_OK = 0
EXIT_STALE = 1
EXIT_RESOLVE_ERROR = 2
EXIT_USAGE_ERROR = 3

# A name without an EOD shard is a STORE PATH ERROR, not a stale store: the
# fresh gate cannot return a verdict on an empty tier, so the runner must treat
# this as fatal (and the operator must fix the store path) rather than retry.
TIER_DIRS = ("eod", "oi", "greeks")

# The runner's column-pruned read stays narrow: only the SPY EOD shard's date
# column is needed. A full shard is MB-class; the gate is intentionally cheap.
DATE_COLUMN = "date"


def _resolve_required(required_iso: str | None, repo: Path | None) -> _date | None:
    """Return the floor date the EOD shard must satisfy.

    Precedence: explicit --required-date > lib.nyse_calendar.expected_last_session
    resolved from --repo. None means USAGE_ERROR (the runner cannot reason about
    freshness without a floor).
    """
    if required_iso:
        try:
            return _date.fromisoformat(required_iso)
        except ValueError:
            return None
    if repo is None:
        return None
    # Resolve lib.nyse_calendar from the repo. The repo is the same checkout the
    # accrual will run in, so this never strands a stale lib pin.
    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    try:
        from lib.nyse_calendar import expected_last_session, last_session_on_or_before
    except Exception:  # noqa: BLE001
        return None
    try:
        expected = expected_last_session()
    except Exception:  # noqa: BLE001
        return None
    # The EOD store is a T+1 plane: at run time it holds the session BEFORE the
    # expected last session. Demanding same-evening EOD would unsatisfy the gate
    # for every run in the hours between market close and the next-morning
    # backfill settle.
    return last_session_on_or_before(expected - timedelta(days=1))


def _latest_date(store: Path, root: str, tier: str) -> tuple[str | None, str]:
    """Latest date in {store}/{tier}/{root}/*.parquet (column-pruned).

    Returns (date_iso_or_None, reason). reason is one of:
      'ok'         — a date was located and returned
      'no_tier'    — the tier directory does not exist (store path error)
      'no_shard'   — no year shard under the root
      'no_rows'    — shard exists but is empty
      'read_error' — shard could not be read (broken parquet, IO error)
    """
    base = store / tier / root
    if not base.is_dir():
        return None, "no_tier"
    shards = sorted(p for p in base.glob("*.parquet") if p.is_file())
    if not shards:
        return None, "no_shard"
    # pyarrow is in the repo requirements (every test_*.py imports it). Importing
    # it lazily here keeps the helper importable in environments without the
    # full parquet stack (e.g., a minimal CI lint box).
    try:
        import pyarrow.parquet as pq  # noqa: PLC0415
    except ImportError:
        return None, "read_error"
    # Use the NEWEST shard, not a union — a partial-year store can still satisfy
    # the gate with its latest completed year, which is exactly what we want.
    latest_path = shards[-1]
    try:
        tbl = pq.read_table(str(latest_path), columns=[DATE_COLUMN])
    except Exception:  # noqa: BLE001
        return None, "read_error"
    if tbl.num_rows == 0:
        return None, "no_rows"
    raw = tbl.column(DATE_COLUMN).to_pylist()[-1]
    latest = raw.date() if hasattr(raw, "date") else raw
    if hasattr(latest, "isoformat"):
        return latest.isoformat(), "ok"
    if isinstance(latest, str):
        return latest[:10], "ok"
    return str(latest)[:10], "ok"


def check(store: Path, repo: Path | None, root: str = "SPY",
          tier: str = "eod", required_iso: str | None = None
          ) -> tuple[int, str, dict]:
    """Run the gate.

    Returns (exit_code, status_word, info_dict).
    """
    info: dict = {"store": str(store), "root": root, "tier": tier}
    required = _resolve_required(required_iso, repo)
    if required is None:
        return EXIT_USAGE_ERROR, "USAGE_ERROR", {
            **info, "reason": "could not resolve required floor (need --required-date "
                              "or --repo pointing at a tree with lib.nyse_calendar)"}
    if not store.exists() or not any((store / t).is_dir() for t in TIER_DIRS):
        return EXIT_RESOLVE_ERROR, "RESOLVE_ERROR", {
            **info, "reason": (f"store path {store} does not exist or carries no tier "
                              f"({', '.join(TIER_DIRS)})")}

    latest_iso, reason = _latest_date(store, root, tier)
    info["latest"] = latest_iso
    info["latest_reason"] = reason
    info["required"] = required.isoformat()
    if reason != "ok":
        return EXIT_RESOLVE_ERROR, "RESOLVE_ERROR", {
            **info, "reason": f"tier read failed: {reason}"}

    # >= rather than == : a store that is ahead of the calendar (e.g., a
    # post-holiday correction) should not false-fail; the calendar date is
    # the floor, not the ceiling.
    if _date.fromisoformat(latest_iso) >= required:
        return EXIT_OK, "FRESH", info
    return EXIT_STALE, "STALE", info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scripts.skew_accrual_gate",
        description=("ThetaData EOD freshness gate for the skew-accrual lane. "
                     "Exit 0=fresh, 1=stale, 2=resolve error, 3=usage error."),
    )
    ap.add_argument("--store", default=None,
                    help="ThetaData EOD store root (default: $THETADATA_STORE)")
    ap.add_argument("--repo", default=None,
                    help="Repo checkout carrying lib.nyse_calendar (for floor resolution)")
    ap.add_argument("--root", default="SPY",
                    help="Underlying to read the EOD shard for (default: SPY)")
    ap.add_argument("--tier", default="eod", choices=TIER_DIRS,
                    help="Tier directory under the store (default: eod)")
    ap.add_argument("--required-date", default=None,
                    help="Override the calendar-derived floor (YYYY-MM-DD)")
    args = ap.parse_args(argv)
    store = Path(args.store) if args.store else Path(
        os.environ.get("THETADATA_STORE", "/Users/chriswong/theta-ops-wt/data/thetadata_eod"))
    repo = Path(args.repo) if args.repo else None
    code, status, info = check(store, repo, root=args.root, tier=args.tier,
                                required_iso=args.required_date)
    # ONE physical line on stdout so the runner's `status=$(_check_freshness)`
    # captures exactly the status word. The receipt writer emits EXACTLY one
    # physical line on stderr (MINOR-2 fix, 2026-09-22): a dict's str() can
    # span multiple lines, embedded newlines in a `reason` value can spill
    # them too. Flatten with repr() + newline-strip so an operator greppinng
    # the launchd log for `::gate-info::` always sees exactly one line per
    # call (the runner logs each `::gate-info::` line line-by-line, and a
    # multi-line receipt would anchor two log rows to one receipt call —
    # silent green / doubled entries).
    print(status)
    info_one_line = repr(info).replace("\n", " ").replace("\r", " ")
    print(f"::gate-info:: {info_one_line}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())