"""Local read-only access to verified Tiingo research captures.

No vendor calls, credentials, local corpus writes, scheduler or canonical Data
OS identity authority. This CLI exposes the incumbent Tiingo research readers;
source-capture timestamps are NOT historical point-in-time availability.

Examples (when a qualified archive exists):
  python -m scripts.tiingo_research_query discover --source eod-bars --symbol AMD
  python -m scripts.tiingo_research_query query --source eod-bars --symbol AMD \
      --capture 2026-10-09:0123...(64-hex) --start 2019-01-01 --end 2019-12-31 \
      --observed-before 2026-10-10T00:00:00Z --acknowledge-hindsight

Output is bounded JSON to stdout; no output files are created.
"""
from __future__ import annotations

import argparse
from datetime import date
import itertools
import json
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.tiingo_archive import DEFAULT_ARCHIVE, require_external_root
from lib.dataos.tiingo_reader import (
    TiingoViewRefusal, read_research_history,
    read_research_statement_timeline, read_research_view,
)
from lib.dataos.temporal import utc

RESEARCH_SOURCES = ("eod-bars", "fund-daily", "fund-statements")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
MAX_SCAN = 2048
MAX_RESULTS = 200
MAX_JSON_BYTES = 8_000_000


def capture_ref(text: str) -> tuple[str, str]:
    """A full exact reference, never a ticker, fuzzy lookup, or latest alias."""
    if not isinstance(text, str) or ":" not in text:
        raise ValueError("capture must be DAY:full-lowercase-SHA256")
    observed_day, sha = text.split(":", 1)
    if not DIGEST.fullmatch(sha):
        raise ValueError("capture requires exact 64-hex SHA256")
    parsed = date.fromisoformat(observed_day)
    if observed_day != parsed.isoformat():
        raise ValueError("capture observation day must be canonical")
    return observed_day, sha


def discover(
    root: Path,
    *,
    source: str,
    vendor_symbol: str,
    max_scan: int = 500,
    max_results: int = 50,
    observed_before: str | None = None,
    max_rows_per_partition: int = 20_000,
    check_mount: bool = True,
) -> dict[str, Any]:
    """Bounded discovery of local artifacts; not a certification of archive coverage.

    A listing is incomplete whenever the scan cap is reached before exhausting
    the manifest iterator. Every reported candidate passes the *existing*
    research view's receipt, row-lineage and artifact-hash validation.
    """
    if source not in RESEARCH_SOURCES:
        raise ValueError("unsupported research source")
    if not isinstance(vendor_symbol, str) or not vendor_symbol or len(vendor_symbol) > 96:
        raise ValueError("exact research vendor identifier is required")
    if (type(max_scan) is not int or not 1 <= max_scan <= MAX_SCAN
            or type(max_results) is not int or not 1 <= max_results <= MAX_RESULTS
            or type(max_rows_per_partition) is not int
            or not 1 <= max_rows_per_partition <= 1_000_000):
        raise ValueError("invalid bounded discovery budget")
    cutoff = utc(observed_before) if observed_before else None
    base = require_external_root(root, check_mount=check_mount)
    folder = base / "manifests" / source
    out = {
        "schema": "mastermind.tiingo.research_query.v1",
        "status": "NO_LOCAL_ARCHIVE" if not base.is_dir() else "LOCAL_RESEARCH_DISCOVERY",
        "source": source,
        "vendor_symbol": vendor_symbol,
        "archive_exists": base.is_dir(),
        "source_manifest_directory_exists": folder.is_dir(),
        "cutoff_utc": cutoff.isoformat() if cutoff else None,
        "network": False, "writes": False, "key_read": False,
        "historical_identity_admitted": False,
        "pit_backtest_eligible": False, "redistribution_admitted": False,
        "complete_history_proven": False,
        "scan_complete": False,
        "manifests_scanned": 0,
        "verified_candidates": [],
        "rejected_local_artifacts": 0,
        "not_for_production": True,
    }
    if not base.is_dir() or not folder.is_dir():
        # An absent archive does not mean a historical product lacks coverage.
        return out

    candidate_files = folder.glob("*/*.json")
    # Consume only the bounded prefix and one lookahead; do not materialize the
    # entire directory or claim a complete scan from a truncated iterator.
    listing = itertools.islice(candidate_files, max_scan + 1)
    for index, file in enumerate(listing):
        if index >= max_scan:
            out["scan_complete"] = False
            break
        out["manifests_scanned"] += 1
        try:
            if file.is_symlink() or not file.resolve().is_relative_to(base.resolve()):
                raise TiingoViewRefusal("untrusted local research manifest path")
            if not file.is_file() or file.stat().st_size > 1_000_000:
                raise TiingoViewRefusal("unbounded or missing research manifest")
            day, digest = capture_ref(file.parent.name + ":" + file.stem)
            view = read_research_view(
                source, day, digest, root=base, check_mount=check_mount,
                max_rows=max_rows_per_partition,
            )
            if not view.rows:
                raise TiingoViewRefusal("no research rows can identify the vendor security")
            field = "ticker_vendor" if source == "eod-bars" else "ticker_or_permaticker_vendor"
            symbols = {row.get(field) for row in view.rows}
            if symbols != {vendor_symbol}:
                continue
            if cutoff is not None:
                if view.source_observed_at_utc is None:
                    raise TiingoViewRefusal("capture clock missing")
                if utc(view.source_observed_at_utc) > cutoff:
                    continue
            if len(out["verified_candidates"]) < max_results:
                out["verified_candidates"].append({
                    "capture_day": day,
                    "source_sha256": digest,
                    "observed_at_utc": view.source_observed_at_utc,
                    "rows": len(view.rows),
                    "research_artifact_locally_verified": True,
                    "vendor_authenticity_established": False,
                    "historically_known_at_established": False,
                })
            else:
                out["result_limit_hit"] = True
        except (OSError, ValueError, TypeError, OverflowError):
            out["rejected_local_artifacts"] += 1
    else:
        out["scan_complete"] = True
    # Listing is useful for explicit ref selection only, not for inferring
    # active/delisted universes, as-of admissibility or the full vendor corpus.
    if not out["scan_complete"]:
        out["status"] = "PARTIAL_LOCAL_RESEARCH_DISCOVERY"
    if out.get("result_limit_hit"):
        out["status"] = "TRUNCATED_LOCAL_RESEARCH_DISCOVERY"
    out["verified_candidates"].sort(key=lambda x: (x["capture_day"], x["source_sha256"]))
    return out


def query(
    root: Path,
    *,
    source: str,
    vendor_symbol: str,
    captures: list[str],
    start: str,
    end: str,
    observed_before: str,
    as_reported: str | None = None,
    acknowledge_hindsight: bool,
    max_rows: int = 20_000,
    max_partitions: int = 100,
    check_mount: bool = True,
) -> dict[str, Any]:
    """Explicit studies from real receipt-bound partitions; no implicit latest."""
    if source not in RESEARCH_SOURCES:
        raise ValueError("unsupported research source")
    if type(max_rows) is not int or not 1 <= max_rows <= 100_000:
        raise ValueError("invalid row limit")
    if type(max_partitions) is not int or not 1 <= max_partitions <= 256:
        raise ValueError("invalid partition limit")
    if not isinstance(captures, list) or not 1 <= len(captures) <= max_partitions:
        raise ValueError("exact bounded capture list is required")
    refs = [capture_ref(text) for text in captures]
    if len(refs) != len(set(refs)):
        raise ValueError("duplicate exact capture references")
    if source == "fund-statements":
        if as_reported not in ("true", "false"):
            raise ValueError("statement query must select asReported=true or false")
        result = read_research_statement_timeline(
            vendor_symbol, refs, start, end, observed_before,
            as_reported=as_reported == "true", root=root,
            acknowledge_hindsight=acknowledge_hindsight,
            max_partitions=max_partitions, max_rows=max_rows, check_mount=check_mount,
        )
    else:
        if as_reported is not None:
            raise ValueError("asReported applies only to financial statements")
        result = read_research_history(
            source, vendor_symbol, refs, start, end, observed_before,
            root=root, acknowledge_hindsight=acknowledge_hindsight,
            max_partitions=max_partitions, max_rows=max_rows, check_mount=check_mount,
        )
    return {
        "schema": "mastermind.tiingo.research_query.v1",
        "status": "RETROSPECTIVE_EXPLORATORY",
        "network": False, "writes": False, "key_read": False,
        "source_authenticity_proven": False,
        "market_time_availability_proven": False,
        "pit_backtest_eligible": False, "redistribution_admitted": False,
        "complete_history_proven": False,
        "metadata": result.metadata(),
        "rows": list(result.rows),
    }


def bounded_json(result: dict[str, Any], max_bytes: int = 2_000_000) -> str:
    if type(max_bytes) is not int or not 256 <= max_bytes <= MAX_JSON_BYTES:
        raise ValueError("invalid bounded output cap")
    serialized = json.dumps(result, sort_keys=True, allow_nan=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > max_bytes:
        raise ValueError("requested research output exceeds byte cap; narrow the study")
    return serialized


def main(
    argv: list[str] | None = None,
    *,
    root: Path = DEFAULT_ARCHIVE,
    check_mount: bool = True,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_subparsers(dest="command", required=True)
    for mode in ("discover", "query"):
        sub = cmd.add_parser(mode)
        sub.add_argument("--source", required=True, choices=RESEARCH_SOURCES)
        sub.add_argument("--symbol", required=True, help="exact current Tiingo vendor ID; NOT a resolved canonical historical identity")
        sub.add_argument("--max-rows", type=int, default=20_000)
        sub.add_argument("--observed-before", help="timezone-aware source CAPTURE cutoff, not historical known-at")
        if mode == "discover":
            sub.add_argument("--max-scan", type=int, default=500)
            sub.add_argument("--max-results", type=int, default=50)
        else:
            sub.add_argument("--capture", action="append", required=True, help="repeat DAY:full-64-hex-SHA256")
            sub.add_argument("--start", required=True, help="YYYY-MM-DD market date or vendor release label")
            sub.add_argument("--end", required=True, help="YYYY-MM-DD market date or vendor release label")
            sub.add_argument("--as-reported", choices=("true", "false"),
                             help="required for fund-statements; forbidden for other products")
            sub.add_argument("--acknowledge-hindsight", action="store_true", required=True)
            sub.add_argument("--max-partitions", type=int, default=100)
    parser.add_argument("--max-output-bytes", type=int, default=2_000_000)
    args = parser.parse_args(argv)
    try:
        if args.command == "discover":
            result = discover(
                root, source=args.source, vendor_symbol=args.symbol,
                max_scan=args.max_scan, max_results=args.max_results,
                max_rows_per_partition=args.max_rows, observed_before=args.observed_before,
                check_mount=check_mount,
            )
        else:
            if not args.observed_before:
                raise ValueError("--observed-before is required for query")
            result = query(
                root, source=args.source, vendor_symbol=args.symbol,
                captures=args.capture, start=args.start, end=args.end,
                observed_before=args.observed_before, as_reported=args.as_reported,
                acknowledge_hindsight=args.acknowledge_hindsight,
                max_rows=args.max_rows, max_partitions=args.max_partitions,
                check_mount=check_mount,
            )
        print(bounded_json(result, max_bytes=args.max_output_bytes))
        return 0
    except (ValueError, OSError, TypeError, OverflowError):
        # Do not expose original paths, source bodies, account secrets or
        # malformed requests in logs from a research-source utility.
        print(json.dumps({
            "schema": "mastermind.tiingo.research_query.v1",
            "status": "REFUSED",
            "network": False, "writes": False,
            "source_authenticity_proven": False,
            "pit_backtest_eligible": False,
            "redistribution_admitted": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
