#!/usr/bin/env python3
"""Operator probe for the provider-qualified public search -> source-open path.

This is a qualification consumer, not a customer chat route. It stores nothing,
performs no model synthesis, and never falls back to another credential/provider.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.neuralweb.public_research import PUBLIC_QUERY_SCOPE, investigate_public


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe public search and source opening.")
    parser.add_argument("query", help="Minimal PUBLIC research query. Never pass private notes/portfolio text.")
    parser.add_argument("--open-top", type=int, default=3)
    parser.add_argument("--max-results", type=int, default=6)
    parser.add_argument("--topic", choices=("finance", "news", "general"), default="finance")
    parser.add_argument(
        "--search-depth",
        choices=("advanced", "basic", "fast", "ultra-fast"),
        default="advanced",
    )
    parser.add_argument("--time-range", choices=("day", "week", "month", "year", "d", "w", "m", "y"))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--include-domain", action="append", default=[])
    parser.add_argument("--exclude-domain", action="append", default=[])
    parser.add_argument("--filter-by-published-date", action="store_true")
    args = parser.parse_args(argv)

    result = investigate_public(
        args.query,
        query_scope=PUBLIC_QUERY_SCOPE,
        open_top=args.open_top,
        max_results=args.max_results,
        topic=args.topic,
        search_depth=args.search_depth,
        time_range=args.time_range,
        start_date=args.start_date,
        end_date=args.end_date,
        include_domains=args.include_domain,
        exclude_domains=args.exclude_domain,
        filter_by_published_date=args.filter_by_published_date,
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    if result.get("status") == "available":
        return 0
    if result.get("status") == "partial":
        return 3
    if result.get("error") in {
        "public_search_not_configured",
        "public_source_open_not_configured",
    }:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
