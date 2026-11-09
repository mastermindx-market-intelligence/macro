#!/usr/bin/env python3
"""Operator qualification of a closed public request -> search -> source opening.

This is not a customer chat route. It stores nothing and never changes provider or
credentials after a refusal. Tests may explicitly inject an offline adapter.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.neuralweb.public_research import (
    EVIDENCE_NEEDS, SOURCE_PREFERENCES, PUBLIC_QUERY_SCOPE,
    PublicEvidenceRequest, PublicResearchAdapter, investigate_public,
)
from engine.neuralweb.public_search_tavily import TavilyAdapter


class _ClosedParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        # argparse normally repeats invalid raw arguments. Emit only the typed
        # machine receipt below, never a private/free-form argument or its value.
        raise ValueError("invalid_public_research_request")


def main(argv: list[str] | None = None, *, adapter: PublicResearchAdapter | None = None) -> int:
    parser = _ClosedParser(description="Probe structured public search and source opening.")
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--listing", required=True)
    parser.add_argument("--evidence-need", choices=tuple(EVIDENCE_NEEDS), required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--information-cutoff", required=True)
    parser.add_argument("--source-preference", choices=tuple(SOURCE_PREFERENCES), required=True)
    parser.add_argument("--open-top", type=int, default=3)
    parser.add_argument("--max-results", type=int, default=6)
    parser.add_argument("--topic", choices=("finance", "news", "general"), default="finance")
    parser.add_argument("--search-depth", choices=("advanced", "basic", "fast", "ultra-fast"), default="advanced")
    parser.add_argument("--time-range", choices=("day", "week", "month", "year", "d", "w", "m", "y"))
    parser.add_argument("--include-domain", action="append", default=[])
    parser.add_argument("--exclude-domain", action="append", default=[])
    parser.add_argument("--filter-by-published-date", action="store_true")
    try:
        args = parser.parse_args(argv)
    except ValueError:
        result = investigate_public({}, query_scope=PUBLIC_QUERY_SCOPE)
    else:
        request = PublicEvidenceRequest(
            issuer=args.issuer, ticker=args.ticker, listing=args.listing,
            evidence_need=args.evidence_need, start_date=args.start_date, end_date=args.end_date,
            information_cutoff=args.information_cutoff, source_preference=args.source_preference,
        )
        selected_adapter = adapter if adapter is not None else TavilyAdapter(
            topic=args.topic, search_depth=args.search_depth, time_range=args.time_range,
            include_domains=args.include_domain, exclude_domains=args.exclude_domain,
            filter_by_published_date=args.filter_by_published_date,
        )
        result = investigate_public(
            request, adapter=selected_adapter, query_scope=PUBLIC_QUERY_SCOPE,
            open_top=args.open_top, max_results=args.max_results,
        )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    if result.get("status") == "available":
        return 0
    if result.get("status") == "partial":
        return 3
    if result.get("error") in {"public_search_not_configured", "public_source_open_not_configured"}:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
