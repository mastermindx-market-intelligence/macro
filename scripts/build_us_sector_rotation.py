"""XSR W1 — build US sector fast-rotation artifact.

Thin wrapper around engine.us_sector_rotation.compute_and_write().  Runs AFTER
the parallel band barrier (reads sector_cycles forward_log.parquet which is
written by build_sector_cycles in the band) and BEFORE build_sector_central
(which reads the artifact to re-order the board).

By default a failure logs, annotates the run and exits 0, so the engine step can never
break the daily deploy. With --strict it exits 1. The us_board_ledgers job uses that,
because the artifact landing is the only thing that job is for.

Run: python -m scripts.build_us_sector_rotation [--strict]
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_us_sector_rotation")


def main(argv: list[str] | None = None) -> int:
    strict = "--strict" in (sys.argv[1:] if argv is None else argv)
    try:
        from engine.us_sector_rotation import compute_and_write
        scored = compute_and_write()
    except Exception as e:  # noqa: BLE001 — additive, fatal only under --strict
        log.exception("build_us_sector_rotation: failed: %s", e)
        print(f"::warning title=build_us_sector_rotation::{type(e).__name__}, "
              "so the rotation artifact did not advance")
        return 1 if strict else 0
    if not scored:
        log.error("build_us_sector_rotation: no instruments scored")
        print("::warning title=build_us_sector_rotation::no instruments scored")
        return 1 if strict else 0
    log.info("build_us_sector_rotation: wrote %d instruments", len(scored))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
