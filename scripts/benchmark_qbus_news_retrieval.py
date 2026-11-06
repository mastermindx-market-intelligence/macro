#!/usr/bin/env python3
"""Reproducible local qbus fixture measurements; never a production latency SLA.

Uses temporary databases only. --tree selects the exact source tree to import so
the same harness can compare a baseline archive and a candidate on one host.
Duplicate timings include the entire writer commit, not just candidate lookup.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# File-path execution first pins this checkout; --tree explicitly takes precedence
# before the deferred benchmark imports so baseline comparisons stay source-bound.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

T0 = datetime(2026, 10, 5, 15, tzinfo=timezone.utc)
TABLES = ("news_clusters", "news_cluster_members", "news_cluster_fingerprints",
          "news_cluster_postings", "news_shingle_df")


def summary(samples):
    values = sorted(samples)
    return {"n": len(values), "min_ms": round(values[0], 3),
            "median_ms": round(values[len(values) // 2], 3),
            "max_ms": round(values[-1], 3),
            "samples_ms": [round(x, 3) for x in samples]}


def file_bytes(path):
    return {suffix or "main": Path(str(path) + suffix).stat().st_size
            if Path(str(path) + suffix).exists() else 0
            for suffix in ("", "-wal", "-shm")}


def evidence(conn):
    columns = {r[1] for r in conn.execute("PRAGMA table_info(news_cluster_members)")}
    if "retrieval_json" not in columns:
        return {"available": False}
    rows = [json.loads(r[0]) for r in conn.execute(
        "SELECT retrieval_json FROM news_cluster_members WHERE retrieval_json IS NOT NULL")]
    result = {"available": True, "assignments": len(rows),
              "truncated_assignments": sum(bool(r.get("retrieval_truncated")) for r in rows)}
    for key in ("postings_examined", "probes_executed", "frequency_rows_read",
                "candidates_surfaced", "candidates_fingerprinted", "candidates_returned"):
        values = [r[key] for r in rows if key in r]
        if values:
            result[key] = {"max": max(values)}
    return result


def counts(conn):
    present = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return {name: conn.execute("SELECT COUNT(*) FROM " + name).fetchone()[0]
            if name in present else None for name in TABLES}


def plans(conn):
    statements = {
        "incumbent_recency": (
            "SELECT cluster_id FROM news_clusters WHERE anchor_observed_at BETWEEN ? AND ? "
            "AND EXISTS (SELECT 1 FROM json_each(news_clusters.subject_ids_json) "
            "WHERE value IN (SELECT value FROM json_each(?))) "
            "ORDER BY anchor_observed_at DESC,cluster_id LIMIT 129",
            ((T0 - timedelta(hours=6)).isoformat(),
             (T0 + timedelta(hours=6)).isoformat(), '["sec-NVDA"]')),
        "bounded_posting_time": (
            "SELECT cluster_id FROM news_cluster_postings WHERE security_id=? AND shingle=? "
            "AND anchor_observed_us BETWEEN ? AND ? LIMIT 257",
            ("sec-NVDA", "nv", int(T0.timestamp() * 1000000),
             int((T0 + timedelta(hours=6)).timestamp() * 1000000))),
        "reverse_posting_repair": (
            "SELECT security_id,shingle FROM news_cluster_postings WHERE cluster_id=?", ("fixture",)),
    }
    out = {}
    for name, (statement, args) in statements.items():
        try:
            out[name] = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + statement, args)]
        except sqlite3.OperationalError:
            out[name] = None
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", default="128,512,2048")
    parser.add_argument("--startup-clusters", type=int, default=6000)
    parser.add_argument("--label", default="candidate")
    args = parser.parse_args()
    tree = args.tree.resolve()
    sys.path.insert(0, str(tree))
    from engine import qbus_news_store as m
    from engine.qbus_news_contract import normalize_news

    # An incomplete --tree must not silently fall back to this checkout (or a
    # preloaded module) while its artifact describes a different source tree.
    for module_name in ("engine.qbus_news_store", "engine.qbus_news_contract",
                        "engine.qbus_news_cluster", "engine.qbus_news_retrieval"):
        module = sys.modules.get(module_name)
        if module is None:  # Older baselines do not have the retrieval module.
            continue
        expected = tree.joinpath(*module_name.split(".")).with_suffix(".py").resolve()
        actual = getattr(module, "__file__", None)
        if actual is None or Path(actual).resolve() != expected:
            raise RuntimeError("selected source tree mismatch: " + module_name)

    def routed(item_id, title, second=0, security_ids=("sec-NVDA",)):
        updated = T0 + timedelta(seconds=second)
        revision = normalize_news({
            "id": item_id, "created": (updated - timedelta(seconds=1)).isoformat(),
            "updated": updated.isoformat(), "title": title,
            "url": "https://www.benzinga.com/news/" + item_id,
            "stocks": [{"name": "NVDA"}], "channels": [{"name": "News"}], "tags": [],
        }, transport="benzinga_rest", received_at=updated + timedelta(seconds=2))
        return m.RoutedRevision(revision=revision, security_ids=tuple(security_ids),
                                universe_revision="benchmark-fixture")

    source_hashes = {}
    for name in ("engine/qbus_news_store.py", "engine/qbus_news_cluster.py",
                 "engine/qbus_news_retrieval.py"):
        path = tree / name
        source_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    result = {
        "schema": "qbus-news-retrieval.fixture-benchmark.v1",
        "label": args.label, "fixture_clock": T0.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Temporary local SQLite fixtures. No network or production writes.",
        "measurement": "Full writer commit timings; not ingestion-to-browser latency.",
        "host_class": {"os": platform.system(), "machine": platform.machine(),
                       "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                       "cpu_count": os.cpu_count()},
        "source_sha256": source_hashes, "sizes": {},
    }
    with tempfile.TemporaryDirectory(prefix="qbus-retrieval-benchmark-") as directory:
        for n in (int(value) for value in args.sizes.split(",") if value):
            path = Path(directory) / f"burst-{n}.sqlite3"
            rows = [routed("anchor", "Nvidia launches new AI accelerator")]
            rows += [routed(f"n{i}", f"Other company announces contract {i} for services {i}",
                            second=i+1) for i in range(n)]
            batches = []
            started = time.perf_counter()
            with m.NewsStore(path, source_key="benzinga-rest") as store:
                for offset in range(0, len(rows), 256):
                    t = time.perf_counter()
                    store.commit_observations(rows[offset:offset+256])
                    batches.append((time.perf_counter() - t) * 1000)
                ingest_ms = (time.perf_counter() - started) * 1000
                duplicates = []
                for k in range(10):
                    item = routed(f"dup{k}", "Nvidia launches its new AI accelerator",
                                  second=n+2+k)
                    t = time.perf_counter()
                    store.commit_observations([item])
                    duplicates.append((time.perf_counter() - t) * 1000)
                value = {
                    "initial_items": len(rows), "batch_size_max": 256,
                    "initial_ingest_including_open_ms": round(ingest_ms, 3),
                    "batch_commit": summary(batches),
                    "duplicate_full_commit": summary(duplicates),
                    "table_counts": counts(store._conn), "query_plans": plans(store._conn),
                    "retrieval_evidence": evidence(store._conn),
                    "bytes_before_close": file_bytes(path),
                }
            value["bytes_after_close"] = file_bytes(path)
            result["sizes"][str(n)] = value
            print(json.dumps({"label": args.label, "size": n,
                              "ingest_ms": value["initial_ingest_including_open_ms"],
                              "duplicate_median_ms": value["duplicate_full_commit"]["median_ms"]}),
                  flush=True)

        n = args.startup_clusters
        if n > 0:
            path = Path(directory) / "startup.sqlite3"
            with m.NewsStore(path, source_key="benzinga-rest") as store:
                for offset in range(0, n, 256):
                    store.commit_observations([
                        routed(f"startup{i}", f"Company announces contract {i} for project {i}",
                               second=i, security_ids=("sec-NVDA",) if i < n*3//5 else ())
                        for i in range(offset, min(offset+256, n))])
                before = counts(store._conn)
            # Fixture-only removal of reproducible derived indexes simulates an
            # existing canonical database on its first indexed writer open.
            with sqlite3.connect(path) as conn:
                for table in ("news_cluster_postings", "news_shingle_df", "news_cluster_fingerprints"):
                    conn.execute("DROP TABLE IF EXISTS " + table)
            cold = time.perf_counter()
            with m.NewsStore(path, source_key="benzinga-rest") as store:
                cold_ms = (time.perf_counter() - cold) * 1000
                after = counts(store._conn)
                cold_bytes = file_bytes(path)
            warm = []
            for _ in range(3):
                started = time.perf_counter()
                with m.NewsStore(path, source_key="benzinga-rest"):
                    warm.append((time.perf_counter() - started) * 1000)
            assert before["news_clusters"] == after["news_clusters"] == n
            result["startup"] = {
                "clusters": n, "one_security_fraction": 0.6,
                "remaining_subjects": "empty",
                "cold_writer_open_after_derived_index_removal_ms": round(cold_ms, 3),
                "warm_writer_open": summary(warm), "counts_before": before, "counts_after": after,
                "bytes_after_cold_open": cold_bytes, "bytes_after_warm_close": file_bytes(path),
                "close_and_checkpoint_time_excluded_from_open": True,
            }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"label": args.label, "complete": True,
                      "startup": result.get("startup")}), flush=True)


if __name__ == "__main__":
    main()
