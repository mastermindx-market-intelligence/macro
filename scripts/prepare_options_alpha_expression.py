#!/usr/bin/env python3
"""Prepare research expression source bindings, without capture or activation.

Read an outcome-blind pre-enrichment candidate feed and its incumbent campaign
ledger. Optionally corroborate identity with an already-retained Theta contracts
response. Emit an inactive preparation to stdout; never write a ledger or create
an eligible OA3 expression. All source/read/decision clocks below are actual local
observations, not inferred source publication or durable expression availability.
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import options_nbbo_cohort as cohort  # noqa: E402
from engine import options_signal_campaign as campaigns  # noqa: E402
from engine.options_alpha_expression_formation import (  # noqa: E402
    prepare_expression_sources,
)


def _read(path: Path, limit: int) -> bytes:
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        meta = os.fstat(stream.fileno())
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > limit:
            raise ValueError("bounded regular source file required")
        raw = stream.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValueError("bounded nonempty source file required")
    return raw


def _clock() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--candidate-feed", required=True, type=Path)
    parser.add_argument("--campaign-ledger", required=True, type=Path)
    parser.add_argument("--theta-contracts", type=Path)
    args = parser.parse_args(argv)
    try:
        raw_feed = _read(args.candidate_feed, 16 * 1024 * 1024)
        source_observed = _clock()
        raw_campaigns = _read(args.campaign_ledger, 128 * 1024 * 1024)
        campaigns_observed = _clock()
        snapshot = campaigns._snapshot_from_raw(
            args.campaign_ledger, campaigns.CAMPAIGNS_PATH, raw_campaigns)
        raw_catalog, catalog_observed = None, None
        if args.theta_contracts:
            raw_catalog = _read(args.theta_contracts, 16 * 1024 * 1024)
            catalog_observed = _clock()
        selection_started = _clock()
        result = prepare_expression_sources(
            raw_feed, campaigns=snapshot, source_observed_at=source_observed,
            campaigns_observed_at=campaigns_observed,
            selection_started_at=selection_started, decision_at=_clock(),
            theta_contracts_raw=raw_catalog, catalog_observed_at=catalog_observed,
        )
        output = cohort.canonical_json_bytes(result)
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print("error: unavailable or invalid expression preparation source", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
