"""Synthetic load verifier for the qbus ticker-news hot path.

This is implementation evidence, not provider or production proof. It drives the
real normalization + transactional SQLite/index path with generated observations,
then opens the real read-only store from concurrent reader threads.

Default shape mirrors the R1 engineering envelope without sleeping in real time:
- 10 revisions/s x 60 scheduled seconds,
- 100 revisions/s x 60 scheduled seconds,
- 100 simultaneous snapshot readers.

The run measures service capacity and per-observation/store-read latency on the host
that executes it. It makes no source-publication, network, browser, licensing, or
natural-market latency claim.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import platform
import sys
import tempfile
import threading
import time
from typing import Sequence

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.qbus_news_contract import normalize_news
from engine.qbus_news_store import (
    NewsReadRights,
    NewsStore,
    RoutedRevision,
)

SCHEMA = "ticker_news.synthetic_verification.v1"
SOURCE_KEY = "benzinga-rest"
UNIVERSE_REVISION = "synthetic-load-r1"
INITIAL_PAGE_LIMIT = 20


@dataclass(frozen=True, slots=True)
class VerificationTargets:
    commit_p95_ms: float = 250.0
    commit_p99_ms: float = 1000.0
    reader_p95_ms: float = 500.0
    minimum_service_rate: float = 100.0


class VerificationError(ValueError):
    pass


def _percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, min(len(ordered) - 1, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return ordered[index]


def _validate_shape(
    *,
    sustained_seconds: int,
    sustained_rate: int,
    burst_seconds: int,
    burst_rate: int,
    readers: int,
    security_count: int,
) -> None:
    for name, value in (
        ("sustained_seconds", sustained_seconds),
        ("sustained_rate", sustained_rate),
        ("burst_seconds", burst_seconds),
        ("burst_rate", burst_rate),
        ("readers", readers),
        ("security_count", security_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise VerificationError("invalid_load_shape")
    if readers > 512 or security_count > 10_000:
        raise VerificationError("invalid_load_shape")


def _routed_revision(index: int, *, security_count: int) -> RoutedRevision:
    bucket = index % security_count
    ticker = f"SYN{bucket:04d}"
    security_id = f"SEC:SYN:{bucket:04d}"
    updated = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
        microseconds=index * 10 + 1
    )
    payload = {
        "id": 1_000_000 + index,
        "created": (updated - timedelta(microseconds=1)).isoformat(),
        "updated": updated.isoformat(),
        "title": f"Synthetic isolated event {index:06d} marker {index * 7919 + 17}",
        "url": f"https://example.invalid/news/{index}",
        "stocks": [{"name": ticker}],
        "channels": [{"name": "Synthetic"}],
        "tags": [],
    }
    revision = normalize_news(
        payload,
        transport="benzinga_rest",
        received_at=updated + timedelta(microseconds=1),
    )
    return RoutedRevision(
        revision=revision,
        security_ids=(security_id,),
        universe_revision=UNIVERSE_REVISION,
    )


def _reader_probe(
    *,
    database: Path,
    barrier: threading.Barrier,
    security_index: int,
) -> tuple[float, int]:
    barrier.wait(timeout=30)
    started = time.perf_counter()
    with NewsStore.open_readonly(database, source_key=SOURCE_KEY) as store:
        snapshot = store.snapshot(
            f"SEC:SYN:{security_index:04d}",
            limit=INITIAL_PAGE_LIMIT,
            cursor=None,
            rights=NewsReadRights.all_internal(),
        )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return elapsed_ms, len(snapshot.rows)


def run_verification(
    *,
    database: Path | str,
    sustained_seconds: int = 60,
    sustained_rate: int = 10,
    burst_seconds: int = 60,
    burst_rate: int = 100,
    readers: int = 100,
    security_count: int = 100,
    targets: VerificationTargets = VerificationTargets(),
) -> dict[str, object]:
    _validate_shape(
        sustained_seconds=sustained_seconds,
        sustained_rate=sustained_rate,
        burst_seconds=burst_seconds,
        burst_rate=burst_rate,
        readers=readers,
        security_count=security_count,
    )
    db = Path(database)
    if db.exists():
        raise VerificationError("database_already_exists")
    db.parent.mkdir(parents=True, exist_ok=True)

    sustained_count = sustained_seconds * sustained_rate
    burst_count = burst_seconds * burst_rate
    scheduled = sustained_count + burst_count
    commit_latencies: list[float] = []
    committed = 0

    load_started = time.perf_counter()
    with NewsStore(db, source_key=SOURCE_KEY) as store:
        for index in range(scheduled):
            started = time.perf_counter()
            routed = _routed_revision(index, security_count=security_count)
            receipt = store.commit_observations((routed,))
            commit_latencies.append((time.perf_counter() - started) * 1000.0)
            committed += receipt.inserted_revisions
        counts = store.counts()
    load_elapsed = time.perf_counter() - load_started
    capacity = committed / load_elapsed if load_elapsed > 0 else float("inf")

    barrier = threading.Barrier(readers)
    reader_latencies: list[float] = []
    reader_rows = 0
    reader_failures = 0
    reader_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=readers) as pool:
        futures = [
            pool.submit(
                _reader_probe,
                database=db,
                barrier=barrier,
                security_index=index % security_count,
            )
            for index in range(readers)
        ]
        for future in as_completed(futures):
            try:
                latency, rows = future.result()
            except Exception:
                reader_failures += 1
                continue
            reader_latencies.append(latency)
            reader_rows += rows
    reader_elapsed = time.perf_counter() - reader_started

    commit_p95 = _percentile(commit_latencies, 95)
    commit_p99 = _percentile(commit_latencies, 99)
    reader_p95 = _percentile(reader_latencies, 95)
    dropped = scheduled - committed

    target_dict = asdict(targets)
    passed = (
        dropped == 0
        and counts["revisions"] == scheduled
        and counts["states"] == scheduled
        and counts["changes"] == scheduled
        and reader_failures == 0
        and len(reader_latencies) == readers
        and commit_p95 <= targets.commit_p95_ms
        and commit_p99 <= targets.commit_p99_ms
        and reader_p95 <= targets.reader_p95_ms
        and capacity >= targets.minimum_service_rate
    )

    return {
        "schema": SCHEMA,
        "synthetic_only": True,
        "scope": {
            "provider_network": False,
            "production_database": False,
            "browser_client": False,
            "licensing_proof": False,
            "natural_market_proof": False,
        },
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "load": {
            "sustained_rate": sustained_rate,
            "sustained_seconds": sustained_seconds,
            "burst_rate": burst_rate,
            "burst_seconds": burst_seconds,
            "scheduled_revisions": scheduled,
            "committed_revisions": committed,
            "dropped_revisions": dropped,
            "processing_seconds": round(load_elapsed, 6),
            "service_capacity_rps": round(capacity, 3),
            "commit_p50_ms": round(_percentile(commit_latencies, 50), 3),
            "commit_p95_ms": round(commit_p95, 3),
            "commit_p99_ms": round(commit_p99, 3),
            "commit_max_ms": round(max(commit_latencies, default=0.0), 3),
        },
        "readers": {
            "requested": readers,
            "page_limit": INITIAL_PAGE_LIMIT,
            "completed": len(reader_latencies),
            "failures": reader_failures,
            "rows_returned": reader_rows,
            "wall_seconds": round(reader_elapsed, 6),
            "snapshot_p50_ms": round(_percentile(reader_latencies, 50), 3),
            "snapshot_p95_ms": round(reader_p95, 3),
            "snapshot_p99_ms": round(_percentile(reader_latencies, 99), 3),
            "snapshot_max_ms": round(max(reader_latencies, default=0.0), 3),
        },
        "database": {
            "revisions": counts["revisions"],
            "states": counts["states"],
            "security_index": counts["security_index"],
            "changes": counts["changes"],
            "legacy_items": counts["legacy_items"],
        },
        "result": {
            "passed": passed,
            "targets": target_dict,
        },
    }


def write_report(path: Path | str, report: dict[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        report,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
    ) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as fh:
        temp = Path(fh.name)
        fh.write(payload)
        fh.flush()
    temp.replace(destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run synthetic qbus ticker-news load/read verification."
    )
    parser.add_argument("--database", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sustained-seconds", type=int, default=60)
    parser.add_argument("--sustained-rate", type=int, default=10)
    parser.add_argument("--burst-seconds", type=int, default=60)
    parser.add_argument("--burst-rate", type=int, default=100)
    parser.add_argument("--readers", type=int, default=100)
    parser.add_argument("--security-count", type=int, default=100)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _validate_shape(
            sustained_seconds=args.sustained_seconds,
            sustained_rate=args.sustained_rate,
            burst_seconds=args.burst_seconds,
            burst_rate=args.burst_rate,
            readers=args.readers,
            security_count=args.security_count,
        )
    except VerificationError as exc:
        print(json.dumps({"schema": SCHEMA, "ok": False, "error": str(exc)}))
        return 2

    if args.database is not None:
        try:
            report = run_verification(
                database=args.database,
                sustained_seconds=args.sustained_seconds,
                sustained_rate=args.sustained_rate,
                burst_seconds=args.burst_seconds,
                burst_rate=args.burst_rate,
                readers=args.readers,
                security_count=args.security_count,
            )
        except VerificationError as exc:
            print(json.dumps({"schema": SCHEMA, "ok": False, "error": str(exc)}))
            return 2
    else:
        with tempfile.TemporaryDirectory(prefix="ticker-news-verify-") as tmp:
            report = run_verification(
                database=Path(tmp) / "qbus.sqlite3",
                sustained_seconds=args.sustained_seconds,
                sustained_rate=args.sustained_rate,
                burst_seconds=args.burst_seconds,
                burst_rate=args.burst_rate,
                readers=args.readers,
                security_count=args.security_count,
            )

    if args.output is not None:
        write_report(args.output, report)
    print(json.dumps({**report, "ok": True}, sort_keys=True))
    return 0 if bool(report["result"]["passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
