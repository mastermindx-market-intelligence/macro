#!/usr/bin/env python3
"""Acquire a bounded FDA decision cohort and publish one validated product snapshot."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from collectors.medtech.openfda import fetch_batch
from engine.medtech.events import MedTechError, utc
from engine.medtech.publication import publish_snapshot, read_snapshot, record_attempt
from engine.medtech.store import EventStore

MAX_FREE_BYTES = 1024 ** 4


def _check_storage_headroom(state_db: Path, public_root: Path, minimum: int) -> None:
    if isinstance(minimum, bool) or not isinstance(minimum, int) or not 0 <= minimum <= MAX_FREE_BYTES:
        raise MedTechError("INVALID_FREE_SPACE_FLOOR")
    if minimum == 0:
        return  # Existing isolated qualifications need no production-sized disk.
    for target in (state_db.parent, public_root):
        # A first run may have no directory yet. Check its actual filesystem
        # without creating state before refusal; production roots are provisioned.
        existing = target.resolve()
        while not existing.exists():
            existing = existing.parent
        if not existing.is_dir():
            raise MedTechError("INVALID_STORAGE_ROOT")
        if shutil.disk_usage(existing).free < minimum:
            raise MedTechError("STORAGE_HEADROOM_LOW")


def run(*, state_db: Path, public_root: Path, datasets: list[str],
        start: str, end: str, max_records: int = 10000,
        min_free_bytes: int = 0) -> dict:
    private, public = state_db.resolve(), public_root.resolve()
    # Private evidence can never be nested in the API's readable publication directory.
    if private.is_relative_to(public) or public.is_relative_to(private.parent):
        raise MedTechError("PRIVATE_PUBLIC_ROOTS_OVERLAP")
    if len(set(datasets)) != len(datasets):
        raise MedTechError("DUPLICATE_DATASET")
    receipts = []
    try:
        if isinstance(max_records, bool) or not isinstance(max_records, int) or not 1 <= max_records <= 10000:
            raise MedTechError("INVALID_MAX_RECORDS")
        _check_storage_headroom(state_db, public_root, min_free_bytes)
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


def _free_bytes(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer byte count") from None
    if not 0 <= number <= MAX_FREE_BYTES:
        raise argparse.ArgumentTypeError(f"must be between 0 and {MAX_FREE_BYTES} bytes")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-db", required=True, type=Path)
    parser.add_argument("--public-root", required=True, type=Path)
    parser.add_argument("--dataset", choices=("510k", "pma"), action="append")
    parser.add_argument("--start", required=True, help="Inclusive FDA decision date, YYYY-MM-DD")
    end = parser.add_mutually_exclusive_group(required=True)
    end.add_argument("--end", help="Inclusive FDA decision date, YYYY-MM-DD")
    end.add_argument("--through-today", action="store_true", help="End on the current UTC date")
    parser.add_argument("--max-records", type=int, default=10000)
    parser.add_argument("--min-free-bytes", type=_free_bytes, default=0,
                        help="Required available bytes on each storage filesystem (0 disables)")
    args = parser.parse_args()
    try:
        result = run(state_db=args.state_db, public_root=args.public_root,
                     datasets=args.dataset or ["510k", "pma"], start=args.start,
                     end=datetime.now(timezone.utc).date().isoformat() if args.through_today else args.end,
                     max_records=args.max_records, min_free_bytes=args.min_free_bytes)
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
