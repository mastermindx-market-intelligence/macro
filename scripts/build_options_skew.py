"""Build the single-name IV-skew context surface.

  1. ACCRUE — upsert today's per-underlying skew into the forward snapshot ledger
     (data/options_skew/snapshots.parquet). This is the apparatus that, run daily,
     eventually gives scripts/validate_options_skew.py the history to earn a verdict.
  2. EMIT — site/options_skew/latest.json from that ledger (display-only context;
     the gate stays closed until the panel is wide/long enough).

No flag runs both legs, which is what today's callers do. `--accrue` and `--emit`
run one leg. EMIT never opens a chain store. When the ThetaData store does not
resolve, ACCRUE prints the source warning and does not touch the ledger.
"""
from __future__ import annotations

import argparse
import json
import logging

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import options_skew as S  # noqa: E402
from lib import config  # noqa: E402

log = logging.getLogger("build_options_skew")


def _legs(argv: list[str] | None) -> tuple[bool, bool]:
    ap = argparse.ArgumentParser(prog="scripts.build_options_skew")
    ap.add_argument("--accrue", action="store_true",
                    help="upsert the snapshot ledger and do not write latest.json")
    ap.add_argument("--emit", action="store_true",
                    help="write latest.json from the ledger and do not open a chain")
    args = ap.parse_args(argv)
    if args.accrue and not args.emit:
        return True, False
    if args.emit and not args.accrue:
        return False, True
    return True, True


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
    do_accrue, do_emit = _legs(argv)
    added = 0
    accrual_state = "ledger_only"
    if do_accrue:
        added, accrual_state = accrue()
    payload = emit(accrual_state=accrual_state) if do_emit else None
    if payload is not None:
        log.info("options_skew: accrued %d rows, emitted %d names (scored=%s, %s)",
                 added, payload["n"], payload["scored"], payload["gate_status"])
    else:
        log.info("options_skew: accrued %d rows (emit skipped)", added)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
