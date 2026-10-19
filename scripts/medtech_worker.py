#!/usr/bin/env python3
"""Acquire a bounded FDA decision cohort and publish one validated product snapshot."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.medtech.openfda import fetch_batch
from engine.medtech.events import MedTechError, utc
from engine.medtech.publication import publish_snapshot, read_snapshot, record_attempt
from engine.medtech.store import EventStore


def run(*, state_db: Path, public_root: Path, datasets: list[str],
        start: str, end: str, max_records: int = 10000) -> dict:
    private, public = state_db.resolve(), public_root.resolve()
    # Private evidence can never be nested in the API's readable publication directory.
    if private.is_relative_to(public) or public.is_relative_to(private.parent):
        raise MedTechError("PRIVATE_PUBLIC_ROOTS_OVERLAP")
    if len(set(datasets)) != len(datasets):
        raise MedTechError("DUPLICATE_DATASET")
    receipts = []
    try:
        with EventStore(state_db, create=True) as store:
            for dataset in datasets:
                batch = fetch_batch(dataset, start=start, end=end, max_records=max_records)
                receipts.append({"dataset": dataset, **store.ingest(batch)})
            generated_at = utc(datetime.now(timezone.utc).isoformat())
            payload = store.snapshot(as_of=generated_at)
            generation = publish_snapshot(public_root, payload)
        record_attempt(public_root, observed_at=generated_at, status="succeeded")
        return {"state": "published", "snapshot_id": generation,
                "generated_at": generated_at, "events": len(payload["events"]),
                "acquisitions": receipts}
    except Exception as exc:
        code = str(exc) if isinstance(exc, MedTechError) else "WORKER_FAILED"
        checked_at = utc(datetime.now(timezone.utc).isoformat())
        try:
            record_attempt(public_root, observed_at=checked_at, status="failed", code=code)
        except Exception:
            pass  # A health-write failure must not obscure the original failed operation.
        raise MedTechError(code) from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-db", required=True, type=Path)
    parser.add_argument("--public-root", required=True, type=Path)
    parser.add_argument("--dataset", choices=("510k", "pma"), action="append")
    parser.add_argument("--start", required=True, help="Inclusive FDA decision date, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Inclusive FDA decision date, YYYY-MM-DD")
    parser.add_argument("--max-records", type=int, default=10000)
    args = parser.parse_args()
    try:
        result = run(state_db=args.state_db, public_root=args.public_root,
                     datasets=args.dataset or ["510k", "pma"], start=args.start,
                     end=args.end, max_records=args.max_records)
        print(json.dumps(result, sort_keys=True))
        return 0
    except MedTechError as exc:
        retained = False
        try:
            read_snapshot(args.public_root)
            retained = True
        except MedTechError:
            pass
        print(json.dumps({"state": "failed", "code": str(exc),
                          "prior_snapshot_retained": retained}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
