"""Controlled Tiingo L0 ingestion for existing Mastermind Data OS.

Examples (NO calls in plan/catalog):
  python -m scripts.tiingo_ingest catalog
  python -m scripts.tiingo_ingest plan --sources eod-bars,fund-statements,fund-daily \
      --symbols AAPL,NVDA --start 2010-01-01 --end 2026-10-08
  python -m scripts.tiingo_ingest collect --sources eod-bars --symbols AAPL \
      --start 2010-01-01 --end 2026-10-08 --max-requests 50
  python -m scripts.tiingo_ingest boats-stream --max-seconds 600

Operator admission before enabling network: confirm actual dataset entitlements,
licensed storage/redistribution terms, drive reserve, account rate limits.
No CLI switch establishes these permissions. No production consumer is auto-enrolled.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import math
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.tiingo_archive import (
    Archive, BOATS_WS, DEFAULT_ARCHIVE, SOURCES, TiingoArchiveError,
    collect_one, decode_boats, read_key, request_path, symbol_path, utc_now,
)

LOG = logging.getLogger("tiingo_ingest")
BAR_SOURCES = frozenset({"eod-bars", "boats-bars", "equity-intraday-bars",
                         "iex-bars", "crypto-bars", "forex-bars"})
GLOBAL_SOURCES = frozenset(name for name, s in SOURCES.items() if not s.symbol)
BAR_CHUNKS = {"eod-bars": 366, "boats-bars": 7, "equity-intraday-bars": 7,
              "iex-bars": 7, "crypto-bars": 7, "forex-bars": 7}
MAX_SYMBOLS = 12000
MAX_TASKS = 120000


@dataclass(frozen=True)
class Task:
    source: str
    symbol: str | None
    params: dict[str, Any]


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def date_ranges(start: date, end: date, span_days: int) -> Iterator[tuple[date, date]]:
    if type(start) is not date or type(end) is not date or end < start:
        raise ValueError("valid ordered date bounds are required")
    if type(span_days) is not int or not 1 <= span_days <= 366:
        raise ValueError("invalid chunk span")
    cursor = start
    while cursor <= end:
        upper = cursor + timedelta(days=min(span_days - 1, (end - cursor).days))
        yield cursor, upper
        if upper == end:
            break
        cursor = upper + timedelta(days=1)


def load_symbols(spec: str, symbol_file: str | None) -> list[str]:
    raw = spec.split(",") if spec else []
    if symbol_file:
        # Bounded line-oriented text. No external API names or "today's top N" implied.
        path = Path(symbol_file)
        if path.stat().st_size > 2_000_000:
            raise ValueError("symbol file exceeds bounded size")
        raw.extend(path.read_text(encoding="utf-8").splitlines())
    found: list[str] = []
    seen = set()
    for line in raw:
        val = line.strip()
        if not val or val.startswith("#"):
            continue
        symbol_path(val)
        # Preserve the vendor identifier verbatim; permaTicker is not just a
        # presentation ticker and may have case-sensitive future namespaces.
        key = val
        if key not in seen:
            found.append(val)
            seen.add(key)
    if len(found) > MAX_SYMBOLS:
        raise ValueError("max 12000 symbols per run")
    return found


def _symbol_groups(symbols: list[str], max_chars: int = 150) -> list[str]:
    """Respect the current source adapter's query bound without changing it."""
    groups: list[str] = []
    current = ""
    for symbol in symbols:
        symbol_path(symbol)
        candidate = current + ("," if current else "") + symbol
        if len(candidate) > max_chars:
            if not current:
                raise ValueError("symbol exceeds query bound")
            groups.append(current)
            current = symbol
        else:
            current = candidate
    if current:
        groups.append(current)
    return groups


def plan(sources: list[str], symbols: list[str], start: date | None,
         end: date | None, *, chunk_override: int | None = None,
         as_reported: bool = True, search_query: str | None = None) -> list[Task]:
    """Pure, bounded request construction. Does not authorize or execute imports.

    Corporate action filters follow the vendor's ex-date contract. Crypto/FX
    minute resolution is explicit instead of relying on changing defaults.
    Reference: Tiingo corporate-actions/dividends, splits, crypto, forex docs.
    """
    sources = list(dict.fromkeys(s.strip() for s in sources))
    symbols = list(dict.fromkeys(symbols))
    if not sources or any(x not in SOURCES for x in sources):
        raise ValueError("select known Tiingo sources")
    if len(symbols) > MAX_SYMBOLS:
        raise ValueError("symbol cohort must be partitioned before planning")
    for symbol in symbols:
        symbol_path(symbol)
    if (start is None) != (end is None):
        raise ValueError("start/end must both be supplied")
    if start is not None and (type(start) is not date or type(end) is not date or end < start):
        raise ValueError("valid ordered date bounds are required")
    if chunk_override is not None and (type(chunk_override) is not int or not 1 <= chunk_override <= 366):
        raise ValueError("invalid chunk span")
    if type(as_reported) is not bool:
        raise ValueError("as_reported must be boolean")
    result: list[Task] = []

    def add(src: str, ticker: str | None, params: dict[str, Any]) -> None:
        if len(result) >= MAX_TASKS:
            raise ValueError("plan exceeds bounded task limit; partition the cohort")
        request_path(src, ticker, params)
        result.append(Task(src, ticker, params))

    for src in sources:
        source = SOURCES[src]
        if (source.symbol or src == "crypto-bars") and not symbols:
            raise ValueError(f"{src} requires symbols")
        if src == "security-search" and not search_query:
            raise ValueError("security-search requires --search-query")
        targets: list[str | None] = symbols if source.symbol else [None]
        for ticker in targets:
            if src in BAR_SOURCES:
                if start is None or end is None:
                    raise ValueError(f"{src} requires start/end")
                chunk = min(chunk_override or BAR_CHUNKS[src], BAR_CHUNKS[src])
                groups = _symbol_groups(symbols) if src == "crypto-bars" else [None]
                for group in groups:
                    for lo, hi in date_ranges(start, end, chunk):
                        params: dict[str, Any] = {"startDate": lo.isoformat(), "endDate": hi.isoformat()}
                        if src != "eod-bars":
                            params["resampleFreq"] = "1min"
                        if src == "boats-bars":
                            params["columns"] = "open,high,low,close,volume"
                        if src == "crypto-bars":
                            params["tickers"] = group
                        add(src, ticker, params)
            else:
                params = {}
                if start and src in {"fund-statements", "fund-daily", "news"}:
                    params.update(startDate=start.isoformat(), endDate=end.isoformat())
                if start and src in {"distributions", "splits"}:
                    params.update(startExDate=start.isoformat(), endExDate=end.isoformat())
                if src == "fund-statements":
                    params["asReported"] = "true" if as_reported else "false"
                if src == "security-search":
                    params["query"] = search_query
                if src == "news":
                    params["limit"] = 100
                    for group in (_symbol_groups(symbols) or [None]):
                        scoped = dict(params)
                        if group is not None:
                            scoped["tickers"] = group
                        add(src, ticker, scoped)
                else:
                    add(src, ticker, params)
    return result


def plan_page(tasks: list[Task], *, offset: int = 0, limit: int = 25,
              expected_digest: str | None = None) -> dict[str, Any]:
    """Stateless offline navigation, not a job queue or execution checkpoint.

    The exact request order and dimensions bind the digest. An offset alone is
    never accepted as proof of progress, vendor download, or completed history.
    """
    if type(offset) is not int or not 0 <= offset <= len(tasks):
        raise ValueError("plan offset out of range")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("plan page limit must be 1..1000")
    hasher = hashlib.sha256(b"tiingo.offline_plan.v1\n")
    items = []
    counts: dict[str, int] = {}
    for index, task in enumerate(tasks):
        entry = {"ordinal": index, "source": task.source, "symbol": task.symbol,
                 "request_path": request_path(task.source, task.symbol, task.params)}
        hasher.update((json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n").encode())
        counts[task.source] = counts.get(task.source, 0) + 1
        if offset <= index < offset + limit:
            items.append(entry)
    digest = hasher.hexdigest()
    if expected_digest is not None and expected_digest != digest:
        raise ValueError("plan changed; cursor cannot be reused")
    return {"schema": "mastermind.tiingo.offline_plan.v1", "network": False,
            "execution_authorized": False, "execution_progress": "NOT_OBSERVED",
            "plan_sha256": digest, "tasks": len(tasks), "total_tasks": len(tasks),
            "source_counts": counts, "offset": offset, "items": items,
            "next_offset": offset + len(items) if offset + len(items) < len(tasks) else None,
            "complete_history_proven": False}


def collect(tasks: Iterable[Task], *, max_requests: int,
            pause_seconds: float, archive: Archive | None = None) -> dict[str, Any]:
    if max_requests < 1:
        raise ValueError("max_requests must be positive")
    if not 0.1 <= pause_seconds <= 120:
        raise ValueError("pause must be between 0.1 and 120 seconds")
    # Once per bounded run. Not printed, retained, or included in errors.
    key = read_key()
    archive = archive or Archive()
    totals: dict[str, Any] = {"attempted": 0, "ok": 0, "new": 0, "failed": 0,
                              "row_hints": 0, "bytes": 0, "errors": []}
    for item in tasks:
        if totals["attempted"] >= max_requests:
            break
        totals["attempted"] += 1
        try:
            saved = collect_one(archive, item.source, item.symbol, key, item.params)
        except TiingoArchiveError as err:
            totals["failed"] += 1
            # Error is sanitized upstream; do NOT dump URLs, HTTP bodies, tokens.
            reason = str(err)
            totals["errors"].append({"source": item.source, "symbol": item.symbol,
                                     "reason": reason})
            # 401/403 or 429: halt, not a costly loop; no automatic token failover.
            if any(s in reason for s in ("401", "403", "429", "space reserve")):
                break
        else:
            totals["ok"] += 1
            totals["new"] += int(saved["new_raw"])
            totals["row_hints"] += saved["rows_hint"] or 0
            totals["bytes"] += saved["raw_bytes"]
        if totals["attempted"] < max_requests:
            time.sleep(pause_seconds)
    return totals


def boats_subscribe_message(token: str) -> str:
    """Vendor-required BOATS firehose threshold 3; never log this message."""
    return json.dumps({"eventName": "subscribe", "authorization": token,
                       "eventData": {"thresholdLevel": 3}},
                      separators=(",", ":"))


def boats_stream(*, max_seconds: int, max_messages: int,
                 batch_messages: int, flush_seconds: float,
                 archive: Archive | None = None) -> dict[str, Any]:
    if not 1 <= max_seconds <= 3600:
        raise ValueError("a bounded 1-3600s stream is required")
    if not 1 <= max_messages <= 10_000_000:
        raise ValueError("a bounded message budget is required")
    if not 100 <= batch_messages <= 50000 or not 1 <= flush_seconds <= 60:
        raise ValueError("unsafe batch bounds")
    try:
        import websocket  # type: ignore[import-not-found]
    except ImportError as err:
        raise TiingoArchiveError(
            "install optional websocket-client package to enable BOATS stream") from err

    key = read_key()
    archive = archive or Archive()
    end_at = time.monotonic() + max_seconds
    counts: dict[str, Any] = {"connections": 0, "transport_breaks": 0,
                              "raw_messages": 0, "segments": 0, "bytes": 0,
                              "coverage_proven": False}
    buffer: list[tuple[str, str]] = []
    buffer_bytes = 0
    last_flush = time.monotonic()

    def flush() -> None:
        nonlocal buffer_bytes, last_flush
        if not buffer:
            return
        saved = archive.store_boats_batch(buffer)
        counts["segments"] += int(saved["new_raw"])
        counts["bytes"] += saved["raw_bytes"]
        buffer.clear()
        buffer_bytes = 0
        last_flush = time.monotonic()

    # A short bounded run is not a background daemon. A continuous service
    # requires existing authorized runtime orchestration, independent admission
    # and a durable return/effects path; we do not self-register one here.
    attempts = 0
    try:
        while time.monotonic() < end_at and counts["raw_messages"] < max_messages:
            attempts += 1
            if attempts > 5:
                break
            sock = None
            try:
                sock = websocket.create_connection(BOATS_WS, timeout=8,
                                                    enable_multithread=True)
                counts["connections"] += 1
                sock.settimeout(3)
                sock.send(boats_subscribe_message(key))
                while (time.monotonic() < end_at
                       and counts["raw_messages"] < max_messages):
                    try:
                        raw = sock.recv()
                    except websocket.WebSocketTimeoutException:
                        flush()
                        continue
                    if not isinstance(raw, str):
                        continue
                    if key in raw:
                        raise TiingoArchiveError(
                            "websocket response included sensitive authentication material")
                    # Entitlement/authentication rejection is terminal, not an
                    # ordinary market-data frame. Never echo the vendor body.
                    try:
                        envelope = json.loads(raw)
                    except (ValueError, TypeError):
                        envelope = None
                    if isinstance(envelope, dict) and (
                        envelope.get("messageType") in {"E", "error"}
                        or envelope.get("eventName") == "error"
                        or envelope.get("service") == "error"
                    ):
                        raise TiingoArchiveError("BOATS subscription rejected by vendor")
                    received = utc_now()
                    # Raw first: never rewrite the original event timestamp.
                    buffer.append((received, raw))
                    buffer_bytes += len(raw.encode("utf-8"))
                    counts["raw_messages"] += 1
                    if (len(buffer) >= batch_messages or buffer_bytes >= 8_000_000
                            or time.monotonic() - last_flush >= flush_seconds):
                        flush()
            except TiingoArchiveError:
                raise
            except (OSError, websocket.WebSocketException):
                counts["transport_breaks"] += 1
                flush()
                # Explicit gap, bounded retry. No inference of continuity.
                if time.monotonic() < end_at and attempts < 5:
                    time.sleep(min(2**attempts, 12))
            finally:
                if sock is not None:
                    sock.close()
                flush()
    finally:
        flush()
    return counts


def archive_inventory(root: Path, *, verify_hash: bool = False,
                      max_receipts: int = 1000, check_mount: bool = True) -> dict[str, Any]:
    from collectors.tiingo_archive import require_external_root
    base = require_external_root(root, check_mount=check_mount)
    receipts = base / "receipts"
    state: dict[str, Any] = {"receipts": 0, "raw_bytes": 0,
                             "missing": 0, "invalid": 0, "by_source": {}}
    if not receipts.exists():
        return state
    for path in sorted(receipts.rglob("*.json")):
        if state["receipts"] >= max_receipts:
            state["truncated"] = True
            break
        try:
            receipt = json.loads(path.read_text())
            raw = base / receipt["raw_path"]
            if not raw.resolve().is_relative_to(base.resolve()) or not raw.is_file():
                state["missing"] += 1
            elif verify_hash and hashlib.sha256(gzip.decompress(raw.read_bytes())).hexdigest() != receipt["raw_sha256"]:
                state["invalid"] += 1
            state["raw_bytes"] += receipt["raw_bytes"]
            name = receipt.get("source", "boats-firehose")
            state["by_source"][name] = state["by_source"].get(name, 0) + 1
            state["receipts"] += 1
        except (ValueError, KeyError, OSError, EOFError):
            state["invalid"] += 1
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("catalog", help="offline supported source families")
    for verb in ("plan", "collect"):
        p = sub.add_parser(verb, help="plan is offline; collect accesses vendor")
        p.add_argument("--sources", required=True, help="comma-separated source IDs")
        p.add_argument("--symbols", default="", help="comma-separated symbol/permaTickers")
        p.add_argument("--symbol-file", help="one vendor symbol per line")
        p.add_argument("--start", help="inclusive YYYY-MM-DD")
        p.add_argument("--end", help="inclusive YYYY-MM-DD")
        p.add_argument("--chunk-days", type=int, help="max days per bar request")
        p.add_argument("--search-query", help="security-search text; no symbol required")
        p.add_argument("--latest-restated", action="store_true",
                       help="statement restatements, NOT point-in-time as-reported")
        if verb == "plan":
            p.add_argument("--plan-offset", type=int, default=0)
            p.add_argument("--plan-limit", type=int, default=25)
            p.add_argument("--expect-plan-sha256")
        if verb == "collect":
            p.add_argument("--max-requests", type=int, default=25)
            p.add_argument("--pause-seconds", type=float, default=1.25)
    stream = sub.add_parser("boats-stream", help="bounded real BOATS websocket capture")
    stream.add_argument("--max-seconds", type=int, default=600)
    stream.add_argument("--max-messages", type=int, default=100000)
    stream.add_argument("--batch-messages", type=int, default=5000)
    stream.add_argument("--flush-seconds", type=float, default=10.0)
    check = sub.add_parser("inventory", help="offline archive receipt inventory")
    check.add_argument("--verify-hash", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "catalog":
            print(json.dumps({"catalog": {
                key: {"group": value.group, "requires_symbol": value.symbol}
                for key, value in SOURCES.items()}, "network": False}, indent=2))
            return 0
        if args.cmd in {"plan", "collect"}:
            begin = parse_day(args.start) if args.start else None
            finish = parse_day(args.end) if args.end else None
            targets = load_symbols(args.symbols, args.symbol_file)
            tasks = plan(args.sources.split(","), targets, begin, finish,
                         chunk_override=args.chunk_days,
                         as_reported=not args.latest_restated,
                         search_query=args.search_query)
            if args.cmd == "plan":
                page = plan_page(tasks, offset=args.plan_offset, limit=args.plan_limit,
                                 expected_digest=args.expect_plan_sha256)
                page["symbols"] = len(targets)
                print(json.dumps(page, indent=2))
                return 0
            out = collect(tasks, max_requests=args.max_requests,
                          pause_seconds=args.pause_seconds)
            print(json.dumps(out, indent=2))
            return 0 if out["failed"] == 0 else 2
        if args.cmd == "boats-stream":
            print(json.dumps(boats_stream(
                max_seconds=args.max_seconds, max_messages=args.max_messages,
                batch_messages=args.batch_messages, flush_seconds=args.flush_seconds), indent=2))
            return 0
        if args.cmd == "inventory":
            print(json.dumps(archive_inventory(DEFAULT_ARCHIVE,
                                                verify_hash=args.verify_hash), indent=2))
            return 0
    except (ValueError, FileNotFoundError, TiingoArchiveError) as err:
        LOG.error("Tiingo archive: %s", err)
        return 2
    return 2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
