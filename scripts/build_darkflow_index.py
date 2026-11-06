"""Build the independent off-exchange ratio projection from existing local stores.

Nightly owns production publication after its existing raw-price mirror restore.
No downloads, new scheduler, model calls, price fallback, or trade authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import logging
from pathlib import Path

from engine.darkflow_publish import SourceUnavailable, build_from_store, publish
from lib import config

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.data_dir())
    parser.add_argument("--site-dir", type=Path, default=config.site_dir())
    parser.add_argument("--now", help="Explicit timezone-bearing replay clock; never an outcome date")
    parser.add_argument("--record-observation", action="store_true", help="Nightly-only first-observed evidence, never replay")
    args = parser.parse_args(argv)
    if args.record_observation:
        from engine.ledger_lane import nightly_advance_enabled
        if args.now or not nightly_advance_enabled():
            parser.error("record-observation requires the existing nightly lane and no replay clock")
    now = datetime.fromisoformat(args.now) if args.now else None
    try:
        result = build_from_store(args.data_dir, now=now)
        observation = {"state": "NOT_REQUESTED", "rows_added": 0}
        if args.record_observation:
            from engine.darkflow_observations import record_observation
            observation = record_observation(result, args.data_dir)
        summary = publish(result, args.site_dir)
    except (SourceUnavailable, ValueError) as exc:
        log.error("darkflow publication retained, not refreshed: %s", exc)
        return 2
    print(json.dumps({"schema": summary["schema"], "generation": summary["generation"],
                      "asof": summary["asof"], "current": summary["current"],
                      "last_complete": summary["last_complete"], "trade_authority": False, "observation": observation}))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
