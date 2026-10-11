"""Read-only comparison of an exact Tiingo request plan with stored raw evidence.

This is NOT a collector, resumable execution owner, integrity repair, canonical
reader or permission gate. It writes nothing and performs no network/key access.
An intact stored response is not proof of complete history, account entitlement,
source authenticity, point-in-time availability, or canonical security identity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import sys
import zlib
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.tiingo_archive import DEFAULT_ARCHIVE, require_external_root, request_path
from lib.dataos.temporal import utc
from lib.dataos.tiingo_views import _date as _view_date_label
from scripts.tiingo_ingest import Task, load_symbols, plan, plan_page
from scripts.tiingo_materialize import verified_raw

MAX_RECEIPT_BYTES = 1_000_000
MAX_TASKS = 20_000
DEFAULT_READ_BUDGET = 256 * 1024 * 1024


def strict_json(raw: str | bytes) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("non-finite JSON number")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _date_label(value: Any) -> str:
    # Share the read-only view contract; do not silently normalize bad dates.
    return _view_date_label(value)


def summarize_records(raw: bytes, task: Task) -> dict[str, Any]:
    payload = strict_json(raw)
    source = task.source
    if source == "eod-metadata":
        if not isinstance(payload, dict) or payload.get("ticker") != task.symbol:
            raise ValueError("metadata ticker does not match requested symbol")
        return {"records": 1, "kind": "METADATA_ONLY", "dates": 0,
                "first_date": None, "last_date": None, "outside_requested_range": 0}
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError("source did not return an array of records")
    if source == "crypto-bars":
        requested = set(str(task.params.get("tickers", "")).split(","))
        records = []
        returned = set()
        for pair in payload:
            ticker = pair.get("ticker")
            if ticker not in requested or ticker in returned:
                raise ValueError("crypto pair missing/duplicated/unrequested")
            returned.add(ticker)
            inner = pair.get("priceData")
            if not isinstance(inner, list) or any(not isinstance(row, dict) for row in inner):
                raise ValueError("crypto priceData is not an array")
            records.extend(inner)
        missing_pairs = len(requested - returned)
    else:
        records = payload
        missing_pairs = 0
    date_key = "exDate" if source in {"distributions", "splits"} else "date"
    if source == "fund-fee-history":
        date_key = "prospectusDate"
    dated = source in {
        "eod-bars", "boats-bars", "iex-bars", "equity-intraday-bars", "crypto-bars",
        "forex-bars", "fund-statements", "fund-daily", "distributions", "splits", "fund-fee-history", "distribution-yield",
    }
    dates = [_date_label(row.get(date_key)) for row in records] if dated else []
    lo = task.params.get("startDate", task.params.get("startExDate"))
    hi = task.params.get("endDate", task.params.get("endExDate"))
    outside = sum((lo is not None and day < lo) or (hi is not None and day > hi) for day in dates)
    return {"records": len(records), "kind": "DATED_RECORDS" if dated else "UNQUALIFIED_RECORDS",
            "dates": len(set(dates)), "first_date": min(dates) if dates else None,
            "last_date": max(dates) if dates else None,
            "outside_requested_range": outside, "missing_crypto_pairs": missing_pairs}


def audit_corpus(tasks: list[Task], *, root: Path = DEFAULT_ARCHIVE,
                 observed_before: str, max_receipts: int = 1000,
                 read_budget: int = DEFAULT_READ_BUDGET, detail_limit: int = 25,
                 check_mount: bool = True) -> dict[str, Any]:
    if len(tasks) > MAX_TASKS or type(max_receipts) is not int or not 1 <= max_receipts <= 100_000:
        raise ValueError("audit budget requires a smaller request cohort")
    if type(read_budget) is not int or not 0 < read_budget <= 1024**3:
        raise ValueError("invalid read budget")
    if type(detail_limit) is not int or not 0 <= detail_limit <= 1000:
        raise ValueError("invalid detail budget")
    base = require_external_root(root, check_mount=check_mount)
    cutoff = utc(observed_before)
    expected = {}
    for task in tasks:
        path = request_path(task.source, task.symbol, task.params)
        if path in expected:
            raise ValueError("duplicate expected request")
        expected[path] = task
    metrics = Counter()
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid_paths = set()
    invalid_observations: dict[str, list[datetime | None]] = defaultdict(list)
    all_inspected = True
    receipts = base / "receipts"
    for file in receipts.rglob("*.json") if receipts.exists() else []:
        if metrics["receipts_scanned"] >= max_receipts:
            all_inspected = False
            break
        metrics["receipts_scanned"] += 1
        path = None
        when = None
        try:
            if not file.resolve().is_relative_to(base) or file.stat().st_size > MAX_RECEIPT_BYTES:
                raise ValueError("receipt escapes audit bounds")
            receipt = strict_json(file.read_bytes())
            if not isinstance(receipt, dict):
                raise ValueError("not a source receipt")
            path = receipt.get("request_path")
            if not isinstance(path, str) or path not in expected:
                metrics["unrelated_receipts"] += 1
                continue
            task = expected[path]
            if (receipt.get("schema") != "mastermind.tiingo.raw_receipt.v1"
                    or receipt.get("vendor") != "tiingo"
                    or receipt.get("source") != task.source
                    or receipt.get("symbol") != task.symbol
                    or type(receipt.get("http_status")) is not int
                    or receipt.get("http_status") != 200):
                raise ValueError("source context/status mismatch")
            when = utc(receipt.get("observed_at_utc"))
            if when > cutoff:
                metrics["after_observation_cutoff"] += 1
                continue
            size = receipt.get("raw_bytes")
            if type(size) is not int or size < 0:
                raise ValueError("invalid source size")
            if size > read_budget - metrics["raw_bytes_read"]:
                metrics["read_budget_skips"] += 1
                all_inspected = False
                continue
            raw = verified_raw(base, receipt)
            metrics["raw_bytes_read"] += len(raw)
            if metrics["raw_bytes_read"] > read_budget:
                all_inspected = False
                break
            if len(raw) != size:
                raise ValueError("source size disagrees with receipt")
            summary = summarize_records(raw, task)
            candidates[path].append({**summary, "observed_at_utc": when.isoformat(),
                                     "raw_sha256": receipt["raw_sha256"]})
            metrics["verified_raw_responses"] += 1
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, EOFError, zlib.error):
            metrics["invalid_receipts_or_payloads"] += 1
            if isinstance(path, str) and path in expected:
                invalid_paths.add(path)
                invalid_observations[path].append(when)
    statuses = Counter()
    details = []
    source_statuses: dict[str, Counter] = defaultdict(Counter)
    for path, task in expected.items():
        views = candidates.get(path, [])
        summary = None
        if not views:
            status = "INVALID_CAPTURE" if path in invalid_paths else "NOT_FOUND"
        else:
            latest = max(utc(v["observed_at_utc"]) for v in views)
            at_latest = [v for v in views if utc(v["observed_at_utc"]) == latest]
            rejected_times = invalid_observations.get(path, [])
            if any(instant is None for instant in rejected_times):
                status = "INVALID_UNORDERED_CAPTURE"
            elif rejected_times and max(rejected_times) >= latest:
                # A failed latest vintage must never disappear behind an older
                # successful response. This diagnoses evidence; it repairs nothing.
                status = "INVALID_LATEST_CAPTURE"
            elif len({v["raw_sha256"] for v in at_latest}) > 1:
                status = "AMBIGUOUS_LATEST_CAPTURE"
            else:
                summary = at_latest[0]
                status = "RAW_RECORDS_CAPTURED" if summary["records"] else "EMPTY_CAPTURED"
                if summary.get("outside_requested_range") or summary.get("missing_crypto_pairs"):
                    status = "PARTIAL_OR_OUT_OF_RANGE"
        if not all_inspected and summary is not None:
            status = "UNCONFIRMED_LATEST_PARTIAL_SCAN"
        statuses[status] += 1
        source_statuses[task.source][status] += 1
        if len(details) < detail_limit:
            details.append({"source": task.source, "symbol": task.symbol,
                            "request_path": path, "status": status,
                            "stored_response_count": len(views), "latest_capture": summary})
    plan_digest = plan_page(tasks, limit=1)["plan_sha256"]
    return {"schema": "mastermind.tiingo.corpus_audit.v2", "network": False,
            "writes": False, "execution_authorized": False,
            "archive_exists": base.is_dir(), "all_receipts_inspected": all_inspected,
            "observed_before_utc": cutoff.isoformat(), "expected_requests": len(expected),
            "plan_sha256": plan_digest, "request_status_counts": dict(statuses),
            "by_source": {s: dict(counts) for s, counts in sorted(source_statuses.items())},
            "scan": dict(metrics), "requests": details, "detail_limit": detail_limit,
            "complete_history_proven": False, "backtest_admission": "NOT_GRANTED",
            "canonical_identity_admitted": False, "source_authenticity_proven": False,
            "field_semantics_validated": False,
            "caveat": "Checks stored bytes/context only. NOT_FOUND under a partial scan is inconclusive; captured date bounds do not prove gap-free sessions or as-of availability."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True)
    parser.add_argument("--symbols", default="")
    parser.add_argument("--symbol-file")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--observed-before", required=True)
    parser.add_argument("--max-receipts", type=int, default=1000)
    parser.add_argument("--detail-limit", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        tasks = plan(args.sources.split(","), load_symbols(args.symbols, args.symbol_file),
                     date.fromisoformat(args.start) if args.start else None,
                     date.fromisoformat(args.end) if args.end else None)
        result = audit_corpus(tasks, observed_before=args.observed_before,
                              max_receipts=args.max_receipts, detail_limit=args.detail_limit)
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "REFUSED", "reason": type(exc).__name__}))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
