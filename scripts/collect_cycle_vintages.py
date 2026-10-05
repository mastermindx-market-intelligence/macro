"""Collect full ALFRED vintages for the Cycle (a) diagnostic series."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from scripts.collect_release_target_vintages import (
    collect_release_target_vintages,
)

log = logging.getLogger(__name__)
CYCLE_SERIES: tuple[str, ...] = ("NEWORDER", "ISRATIO", "INDPRO")
_REALTIME_START = "1997-01-01"


def collect_cycle_vintages(
    *,
    repo_root: str | Path,
    series_ids: Sequence[str] = CYCLE_SERIES,
    realtime_start: str = _REALTIME_START,
    api_key: str | None = None,
    dry_run: bool = False,
    fetcher: Callable[..., Any] | None = None,
    publisher: Callable[[Path, Path], None] | None = None,
) -> dict[str, Any]:
    return collect_release_target_vintages(
        repo_root=repo_root,
        series_ids=series_ids,
        target_subdir="cycle_vintages",
        supported_series=CYCLE_SERIES,
        manifest_schema="cycle_vintage_collection.v1",
        realtime_start=realtime_start,
        api_key=api_key,
        dry_run=dry_run,
        fetcher=fetcher,
        publisher=publisher,
        missing_key_warning=(
            "[cycle_vintages] The FRED API key is absent, so the cycle vintage stores are untouched."
        ),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect ALFRED full-vintage stores for the Cycle (a) series"
    )
    parser.add_argument(
        "--series",
        nargs="+",
        default=list(CYCLE_SERIES),
        help="Cycle (a) FRED series IDs (space- or comma-separated)",
    )
    parser.add_argument(
        "--realtime-start",
        default=_REALTIME_START,
        help="Earliest ALFRED real-time date (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Fetch and validate, do not write"
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    args = _parse_args()
    result = collect_cycle_vintages(
        repo_root=Path(__file__).resolve().parent.parent,
        series_ids=args.series,
        realtime_start=args.realtime_start,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("status") not in {"ok", "dry_run", "skipped"}:
        raise SystemExit(1)
