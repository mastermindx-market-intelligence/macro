#!/usr/bin/env python3
"""FIF V0-a offline latency benchmark: measured distributions, declared budgets.

Builds the forensics router in-process over a LOCAL publisher-built production
store, overrides the entitlement dependency exactly the way
tests/test_fundamental_forensics_production_api_chain.py does, drives every
configured route through ``TestClient``, and writes the measured snapshot plus
the SLO evaluation. No network, no real credentials, never R2 or SEC: the
dataset store is a local directory and the ASGI client opens no socket.

Exit codes: 0 within budget, 1 when any configured route exercised here is in
breach, 2 when the store or its issuers cannot be resolved.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
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


def _exercise(client: Any, profile: dict[str, Any]) -> None:
    """One pass over every configured route for one issuer profile."""
    json_headers = {"content-type": "application/json"}
    for path in (
        "/api/forensics/health",
        "/api/forensics/state",
        "/api/forensics/v1/attested-history/latest",
    ):
        client.get(path)
    for path, schema in (
        ("/api/forensics/v1/financial/query", _QUERY_SCHEMA),
        ("/api/forensics/v1/financial/query.xlsx", _QUERY_SCHEMA),
        ("/api/forensics/v1/financial/query.csv", _QUERY_SCHEMA),
        ("/api/forensics/v1/financial/query.parquet", _QUERY_SCHEMA),
        ("/api/forensics/v1/financial/revisions", _REVISION_SCHEMA),
        ("/api/forensics/v1/financial/packet", _PACKET_SCHEMA),
    ):
        client.post(path, content=_policy_body(schema, profile), headers=json_headers)
    if profile["accession"] is not None:
        client.post(
            "/api/forensics/v1/financial/statements",
            content=json.dumps(
                {
                    "schema": _STATEMENT_SCHEMA,
                    "entity_id": profile["entity_id"],
                    "accession": profile["accession"],
                },
                separators=(",", ":"),
            ).encode("utf-8"),
            headers=json_headers,
        )


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
    with TestClient(app, raise_server_exceptions=False) as client:
        for _ in range(args.iterations):
            for profile in profiles:
                _exercise(client, profile)

    forensics_api._reset_production_provider_cache()
    snapshot = RECORDER.snapshot()
    config = load_slo_config(_SLO_CONFIG)
    evaluation = evaluate_slo(snapshot, config)
    report = {
        "schema": "fif_latency_benchmark.v1",
        "iterations": args.iterations,
        "snapshot": snapshot,
        "evaluation": evaluation,
    }
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(payload)

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
