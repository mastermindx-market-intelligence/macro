"""Build one coherent US Sector Intelligence generation end to end."""
from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

log = logging.getLogger("build_sector_intelligence")
Step = tuple[str, Callable[[], int | None]]


def run_steps(steps: Iterable[Step]) -> int:
    """Run producers in order and stop at the first incomplete generation."""
    for name, invoke in steps:
        log.info("sector intelligence step start: %s", name)
        try:
            rc = invoke()
        except Exception as exc:  # noqa: BLE001 - one failed producer voids the generation
            log.exception("sector intelligence step %s raised: %s", name, exc)
            return 1
        rc = 0 if rc is None else int(rc)
        if rc != 0:
            log.error("sector intelligence step %s failed with rc=%d", name, rc)
            return rc
        log.info("sector intelligence step complete: %s", name)
    return 0


def default_steps() -> list[Step]:
    from scripts import build_baskets
    from scripts import build_sector_action_board
    from scripts import build_sector_central
    from scripts import check_sector_intelligence_freshness

    return [
        (
            "scripts.build_baskets",
            lambda: build_baskets.main(sector_intelligence_only=True),
        ),
        ("scripts.build_sector_action_board", build_sector_action_board.main),
        (
            "scripts.build_sector_central",
            lambda: build_sector_central.main(strict=True),
        ),
        ("scripts.check_sector_intelligence_freshness",
         lambda: check_sector_intelligence_freshness.main([])),
    ]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return run_steps(default_steps())


if __name__ == "__main__":
    raise SystemExit(main())
