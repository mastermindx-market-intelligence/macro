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


def _fast_lens_nonfatal() -> int:
    """Run the XSR fast-lens builder without ever voiding the generation (ruling 28).

    scripts.build_us_sector_rotation.main already returns 0 on its own errors,
    but run_steps treats an escaping exception — and any non-zero rc — as fatal.
    The lens is additive: when it fails, the page keeps its stale-lens copy with
    the input date, so both outcomes are logged and normalized to 0 HERE only.
    Every other step keeps its fatal behaviour.
    """
    from scripts import build_us_sector_rotation

    try:
        rc = build_us_sector_rotation.main()
    except Exception as exc:  # noqa: BLE001 - additive lens must never block the generation
        log.exception("sector intelligence step scripts.build_us_sector_rotation raised (non-fatal): %s", exc)
        return 0
    if rc:
        log.error("sector intelligence step scripts.build_us_sector_rotation failed with rc=%s (non-fatal)", rc)
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
        # Ruling 28: refresh the fast lens in our own chain, immediately before
        # sector central reads it. Non-fatal on its own — see _fast_lens_nonfatal.
        ("scripts.build_us_sector_rotation", _fast_lens_nonfatal),
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
