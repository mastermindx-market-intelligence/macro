"""Verify ledger content after the W2-1b accrue step.

WHY THIS EXISTS
───────────────
The W2-1b sibling's `engine.options_skew.snapshot()` can return 0 without
writing rows to data/options_skew/snapshots.parquet:

  - `chain is None` (no chain in the store, or no chain for today's keys)
    → return 0 without writing.
  - `not rows` after skew_map() (the chain parsed but no per-underlying
    verdict landed) → return 0 without writing.
  - dedup: every (date, underlying) key already exists in the prior ledger
    → return 0 without writing.
  - `_ledger_unchanged(prev, proposed)` (the dedup-ed frame equals the
    previous one byte-for-byte after atomic rewrite) → return 0 without
    writing.

A zero-row OR no-op accrue means the ledger on disk is identical to before —
the accrue contributed nothing new. The runner MUST NOT publish in that
case: the R2 leg would advertise an unchanged ledger but the launchd log
would say "accrue completed" and "publish completed", which is misleading
and risks overwriting an already-good R2 manifest with a no-op put. The
verify helper gates publish on the ledger ACTUALLY GROWING under the
accrue step.

DETECTION
─────────
Reads data/options_skew/snapshots.parquet with pandas; checks the file
exists, is non-empty (size > 0), has at least one row, AND has MORE rows
than the pre-accrue snapshot recorded by the runner (--pre-rows). The
pre-rows contract is what BLOCKER-2 actually fixed: an idempotent rerun
that finds the ledger populated by the bootstrap (the tracked 238,595-byte
12,375-row W2-1b-pre merge seed) used to satisfy the old "ledger has
rows" check by carrying a no-op accrue straight through to publish —
the tracked bootstrap counted as "non-empty", the accrue returned 0, and
the launchd log reported "publish completed" for a ledger whose bytes
had not changed. The new --pre-rows argument pins the runner to record
the row count BEFORE the accrue step so the verify can compare against
it and refuse a non-growth outcome as a no-op.

EXIT CODES (load-bearing — the runner reads them)
  0  EXIT_OK          — ledger exists, non-empty, has rows, AND grew
                        under the accrue step (or --pre-rows omitted,
                        in which case the post-state check alone pins
                        the contract).
  5  EXIT_NO_LEDGER   — ledger missing / empty / zero rows / no growth;
                        runner must abort loudly with the named reason.
                        Reversibility: the next run that produces a
                        strictly larger ledger passes this check.

USAGE
  scripts/skew_accrual_verify_ledger.py --ledger PATH [--pre-rows N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo-root pin so `lib.*` / `engine.*` / `scripts.*` would resolve from
# THIS repo under bare `python scripts/skew_accrual_verify_ledger.py ...`
# (the post-merge audit-style smoke the operator runs from the lane
# checkout) exactly the same way `python -m ...` resolves them. Mirrors
# the strong-pin idiom enforced by
# `tests/test_check_script_import_pinning.py` for every scripts/** entry.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

EXIT_OK = 0
EXIT_NO_LEDGER = 5


def check(ledger: Path, pre_rows: int | None = None) -> tuple[int, dict]:
    """Run the verify.

    Returns (exit_code, info_dict). The info_dict's `reason` is the named
    operator-actionable message — the runner prints it verbatim.

    pre_rows is the row count the runner recorded BEFORE the accrue step.
    None means the runner did not record a pre-state (legacy / first run);
    the post-state checks alone pin the contract in that case.
    """
    info: dict = {"ledger": str(ledger)}
    if pre_rows is not None:
        info["pre_rows"] = pre_rows
    if not ledger.is_file():
        info["reason"] = "ledger file does not exist (accrue never wrote one)"
        return EXIT_NO_LEDGER, info
    try:
        size = ledger.stat().st_size
    except OSError as exc:
        info["reason"] = f"stat failed: {exc}"
        return EXIT_NO_LEDGER, info
    info["bytes"] = size
    if size == 0:
        info["reason"] = "ledger file is empty (0 bytes after accrue)"
        return EXIT_NO_LEDGER, info
    try:
        import pandas as pd  # noqa: PLC0415
        df = pd.read_parquet(ledger)
    except Exception as exc:  # noqa: BLE001
        info["reason"] = f"parquet read failed: {exc}"
        return EXIT_NO_LEDGER, info
    n = int(len(df))
    info["rows"] = n
    if n == 0:
        info["reason"] = ("ledger has 0 rows after accrue — the W2-1b "
                          "snapshot() returned 0 (chain=None, no rows, or "
                          "dedup-only). Refusing to publish a no-op ledger.")
        return EXIT_NO_LEDGER, info
    # BLOCKER-2: refuse a no-op accrue. The pre_rows argument is recorded
    # by the runner BEFORE the accrue step; if the post-accrue row count
    # has NOT strictly grown, the accrue contributed nothing and we must
    # not publish (the R2 leg would advertise an unchanged ledger under
    # a fresh Last-Modified stamp, polluting audit_r2's freshness anchor).
    if pre_rows is not None and n <= pre_rows:
        info["reason"] = (
            f"ledger did not grow under accrue — pre_rows={pre_rows}, "
            f"post_rows={n} (no-op snapshot: chain=None, no rows, "
            f"dedup-only, or byte-equal rewrite). Refusing to publish."
        )
        return EXIT_NO_LEDGER, info
    info["reason"] = "ledger has content"
    return EXIT_OK, info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scripts.skew_accrual_verify_ledger",
        description=("Verify data/options_skew/snapshots.parquet has at "
                     "least one row after the accrue step (and grew if "
                     "--pre-rows was recorded). Exit 0=ok, 5=no-ledger.")
    )
    ap.add_argument("--ledger", required=True,
                    help="Path to the ledger parquet")
    ap.add_argument("--pre-rows", type=int, default=None,
                    help="Row count recorded BEFORE the accrue step "
                         "(the runner writes a `.skew_pre_rows` sidecar "
                         "from step_precheck_w21b; this flag passes it "
                         "back here so the verify can refuse a no-op "
                         "accrue on a pre-populated bootstrap ledger).")
    args = ap.parse_args(argv)
    code, info = check(Path(args.ledger), pre_rows=args.pre_rows)
    status_word = "OK" if code == EXIT_OK else "NO_LEDGER"
    # One line on stdout so the runner can capture the status word.
    print(status_word)
    for k, v in info.items():
        print(f"  {k}={v}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())