#!/usr/bin/env python3
"""FIF V0-a offline latency benchmark: measured distributions, declared budgets.

Builds the forensics router in-process over a LOCAL publisher-built production
store, overrides the entitlement dependency exactly the way
tests/test_fundamental_forensics_production_api_chain.py does, drives every
configured route through ``TestClient``, and writes the measured snapshot plus
the SLO evaluation. No network, no real credentials, never R2 or SEC: the
dataset store is a local directory and the ASGI client opens no socket.

Every response's status code is counted per route in the output; a response
outside its route's expected set fails the run, and failed responses never
enter the latency budget — the budget is computed from the recorder's
success-only (2xx/3xx) window.

Exit codes: 0 within budget, 1 when any configured route exercised here is in
breach, 2 when the store or its issuers cannot be resolved, 3 when any
response carries a status outside its route's expected set.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_ITERATIONS = 200
_LATEST_GLOB = "fundamental_forensics/production-datasets/v1/issuers/*/latest.json"
_SLO_CONFIG = ROOT / "config" / "fundamental_forensics" / "slo.v1.json"
_QUERY_SCHEMA = "fundamental_forensics.financial_query_request/v1"
_REVISION_SCHEMA = "fundamental_forensics.financial_revision_request/v1"
_PACKET_SCHEMA = "fundamental_forensics.financial_packet_request/v1"
_STATEMENT_SCHEMA = "fundamental_forensics.financial_statement_request/v1"
# FY2024 revenue duration, the benchmark's stand-in request shape.
_REVENUE_PERIOD = {
    "kind": "duration",
    "start": "2023-10-01",
    "end": "2024-09-28",
    "label": "FY2024",
}
# MAJOR-2: every exercised route's lawful response set. A status outside its
# route's set fails the benchmark (exit 3) and never becomes a latency sample.
_EXPECTED_STATUS_BY_ROUTE: dict[str, frozenset[int]] = {
    path: frozenset({200})
    for path in (
        "/api/forensics/health",
        "/api/forensics/state",
        "/api/forensics/v1/attested-history/latest",
        "/api/forensics/v1/financial/query",
        "/api/forensics/v1/financial/query.xlsx",
        "/api/forensics/v1/financial/query.csv",
        "/api/forensics/v1/financial/query.parquet",
        "/api/forensics/v1/financial/revisions",
        "/api/forensics/v1/financial/packet",
        "/api/forensics/v1/financial/statements",
    )
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline FIF per-route latency benchmark against a local production store."
    )
    parser.add_argument(
        "--local-store",
        required=True,
        help="publisher-built local production dataset store directory",
    )
    parser.add_argument(
        "--issuer",
        action="append",
        dest="issuers",
        help="issuer entity id (repeatable; default: every issuer in the store)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"iterations over the route set (default {DEFAULT_ITERATIONS})",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="write the JSON report to this path (default: stdout)",
    )
    return parser.parse_args(argv)


def _discover_issuers(store_dir: Path) -> list[str]:
    return sorted(path.parent.name for path in store_dir.glob(_LATEST_GLOB))


def _issuer_profiles(store: Any, issuers: list[str]) -> list[dict[str, Any]]:
    from engine.fundamental_forensics.production_datasets import (
        latest_generation_summary,
        load_generation,
    )

    profiles: list[dict[str, Any]] = []
    for issuer in issuers:
        summary = latest_generation_summary(store, issuer)
        if summary is None:
            print(f"warning: no published generation for {issuer}; skipping", file=sys.stderr)
            continue
        generation = load_generation(store, issuer, summary["dataset_generation_id"])
        accessions = generation.statement_accessions()
        profiles.append(
            {
                "entity_id": issuer,
                "accession": accessions[0] if accessions else None,
                "recorded_at": summary["admitted_at"],
            }
        )
    return profiles


def _policy_body(schema: str, profile: dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "schema": schema,
            "entity_id": profile["entity_id"],
            "policy": {
                "selection": "latest_known_as_of",
                "source_snapshot_at": "2025-12-31T23:59:59Z",
                "recorded_at": profile["recorded_at"],
            },
            "metric_ids": ["revenue"],
            "periods": [dict(_REVENUE_PERIOD)],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _exercise(client: Any, profile: dict[str, Any]) -> dict[str, Counter]:
    """One pass over every configured route for one issuer profile.

    Returns the per-route response-status counts observed on this pass. A
    status outside its route's expected set is a benchmark failure (exit 3),
    and failed responses never enter the latency budget: the in-process
    recorder's window only ever holds success samples.
    """
    status_counts: dict[str, Counter] = {}
    json_headers = {"content-type": "application/json"}

    def _record_status(path: str, status_code: int) -> None:
        status_counts.setdefault(path, Counter())[status_code] += 1

    for path in (
        "/api/forensics/health",
        "/api/forensics/state",
        "/api/forensics/v1/attested-history/latest",
    ):
        _record_status(path, client.get(path).status_code)
    for path, schema in (
        ("/api/forensics/v1/financial/query", _QUERY_SCHEMA),
        ("/api/forensics/v1/financial/query.xlsx", _QUERY_SCHEMA),
        ("/api/forensics/v1/financial/query.csv", _QUERY_SCHEMA),
        ("/api/forensics/v1/financial/query.parquet", _QUERY_SCHEMA),
        ("/api/forensics/v1/financial/revisions", _REVISION_SCHEMA),
        ("/api/forensics/v1/financial/packet", _PACKET_SCHEMA),
    ):
        response = client.post(
            path, content=_policy_body(schema, profile), headers=json_headers
        )
        _record_status(path, response.status_code)
    if profile["accession"] is not None:
        statements_path = "/api/forensics/v1/financial/statements"
        statements_body = json.dumps(
            {
                "schema": _STATEMENT_SCHEMA,
                "entity_id": profile["entity_id"],
                "accession": profile["accession"],
            },
            separators=(",", ":"),
        ).encode("utf-8")
        response = client.post(
            statements_path, content=statements_body, headers=json_headers
        )
        _record_status(statements_path, response.status_code)
    return status_counts


def _unexpected_status_counts(
    status_counts: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    """Per-route counts of statuses outside that route's expected set."""
    unexpected: dict[str, dict[str, int]] = {}
    for path, counts in status_counts.items():
        expected = {str(status) for status in _EXPECTED_STATUS_BY_ROUTE.get(path, ())}
        outside = {status: n for status, n in counts.items() if status not in expected}
        if outside:
            unexpected[path] = outside
    return unexpected


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    store_dir = Path(args.local_store).resolve()
    if not store_dir.is_dir():
        print(f"local store not found: {store_dir}", file=sys.stderr)
        return 2
    if args.iterations < 1:
        print("--iterations must be >= 1", file=sys.stderr)
        return 2

    # Own process only: production mode over the local store, never a fetch.
    os.environ["FIF_FINANCIAL_DATASET_MODE"] = "production"
    os.environ["FIF_PRODUCTION_DATASET_LOCAL_STORE"] = str(store_dir)

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.forensics as forensics_api
    from engine.fundamental_forensics.latency import RECORDER, evaluate_slo, load_slo_config
    from engine.fundamental_forensics.production_datasets import (
        build_production_dataset_store,
    )

    forensics_api.REPO = ROOT
    forensics_api._reset_production_provider_cache()
    RECORDER.reset()

    store = build_production_dataset_store(store_dir)
    issuers = list(args.issuers or _discover_issuers(store_dir))
    if not issuers:
        print(
            "no issuers resolved: pass --issuer or point --local-store at a published store",
            file=sys.stderr,
        )
        return 2
    profiles = _issuer_profiles(store, issuers)
    if not profiles:
        print("none of the named issuers have a published generation", file=sys.stderr)
        return 2

    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    per_route_statuses: dict[str, Counter] = {}
    with TestClient(app, raise_server_exceptions=False) as client:
        for _ in range(args.iterations):
            for profile in profiles:
                for path, counts in _exercise(client, profile).items():
                    per_route_statuses.setdefault(path, Counter()).update(counts)

    forensics_api._reset_production_provider_cache()
    snapshot = RECORDER.snapshot()
    config = load_slo_config(_SLO_CONFIG)
    evaluation = evaluate_slo(snapshot, config)
    status_counts = {
        path: {str(status): count for status, count in sorted(counter.items())}
        for path, counter in per_route_statuses.items()
    }
    report = {
        "schema": "fif_latency_benchmark.v1",
        "iterations": args.iterations,
        "status_counts": status_counts,
        "snapshot": snapshot,
        "evaluation": evaluation,
    }
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(payload)

    unexpected = _unexpected_status_counts(status_counts)
    if unexpected:
        print(
            "unexpected response statuses: " + json.dumps(unexpected, sort_keys=True),
            file=sys.stderr,
        )
        return 3
    breaches = sorted(
        template
        for template, row in evaluation["routes"].items()
        if row["window_n"] > 0 and row["state"] == "breach"
    )
    if breaches:
        print("SLO breach: " + ", ".join(breaches), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
