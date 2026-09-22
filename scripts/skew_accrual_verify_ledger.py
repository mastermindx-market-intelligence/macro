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

A zero-row accrue means the ledger on disk is identical to before — the
accrue is a no-op. The runner MUST NOT publish in that case: the R2 leg
would advertise the unchanged ledger but the launchd log would say
"accrue completed" and "publish completed", which is misleading and risks
overwriting an already-good R2 manifest with a no-op put. The verify
helper gates publish on the ledger having at least one row after the
accrue step.

DETECTION
─────────
Reads data/options_skew/snapshots.parquet with pandas; checks the file
exists, is non-empty (size > 0), and has at least one row. The check is
testable in isolation under tmp_path fixtures (synthetic parquet → no real
chain dependency).

EXIT CODES (load-bearing — the runner reads them)
  0  EXIT_OK          — ledger exists, non-empty, has rows; safe to publish.
  5  EXIT_NO_LEDGER   — ledger missing / empty / zero rows; runner must
                        abort loudly with the named reason. Reversibility:
                        the next run that produces a non-empty ledger
                        passes this check.

USAGE
  scripts/skew_accrual_verify_ledger.py --ledger PATH
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_NO_LEDGER = 5


def check(ledger: Path) -> tuple[int, dict]:
    """Run the verify.

    Returns (exit_code, info_dict). The info_dict's `reason` is the named
    operator-actionable message — the runner prints it verbatim.
    """
    info: dict = {"ledger": str(ledger)}
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
    info["reason"] = "ledger has content"
    return EXIT_OK, info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scripts.skew_accrual_verify_ledger",
        description=("Verify data/options_skew/snapshots.parquet has at "
                     "least one row after the accrue step. Exit 0=ok, "
                     "5=no-ledger.")
    )
    ap.add_argument("--ledger", required=True,
                    help="Path to the ledger parquet")
    args = ap.parse_args(argv)
    code, info = check(Path(args.ledger))
    status_word = "OK" if code == EXIT_OK else "NO_LEDGER"
    # One line on stdout so the runner can capture the status word.
    print(status_word)
    for k, v in info.items():
        print(f"  {k}={v}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())