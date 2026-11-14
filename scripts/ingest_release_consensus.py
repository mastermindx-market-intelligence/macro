"""Capture authorized economist polls into MRI's existing evidence directory.

Defaults to validation only. --commit stamps actual ingestion time and uses the
incumbent durable receipt append. It never purchases data, fetches a provider,
backdates possession, or rewrites existing snapshots. A backfill recorded after
release remains ineligible for point-in-time signal reconstruction.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from engine.release_surprise_confirmation import (
    CONSENSUS_PATH, EvidenceError, digest, normalize_consensus, read_jsonl,
)
from scripts.reconcile_release_actuals import append_receipts


class ConsensusAppendUncertain(EvidenceError):
    """Inspect the original target before retrying an interrupted append."""


def _snapshot_identity(row: dict) -> str:
    return digest({k: v for k, v in row.items() if k not in {"receipt_id", "observed_at", "recorded_at"}})


def ingest(source: Path, root: Path, *, commit: bool = False) -> dict:
    inputs, meta = read_jsonl(source)
    if meta["status"] not in {"ready", "empty"}:
        raise EvidenceError("consensus_input_" + meta["status"])
    recorded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows = []
    for raw in inputs:
        # The collector owns possession clocks. Supplied/backfilled clocks are
        # deliberately not trusted as evidence of historical system possession.
        candidate = {k: v for k, v in raw.items() if k != "receipt_id"}
        candidate.update({"observed_at": recorded_at, "recorded_at": recorded_at})
        rows.append(normalize_consensus(candidate))
    out = root / CONSENSUS_PATH

    def novel_rows(*, fd: int | None = None):
        existing, existing_meta = read_jsonl(out, fd=fd)
        if existing_meta["status"] not in {"ready", "empty", "missing"}:
            raise EvidenceError("consensus_ledger_" + existing_meta["status"])
        known = {_snapshot_identity(normalize_consensus(row)) for row in existing}
        novel = []
        for row in rows:
            identity = _snapshot_identity(row)
            if identity not in known:
                novel.append(row)
                known.add(identity)
        return novel, existing_meta

    if commit:
        out.parent.mkdir(parents=True, exist_ok=True)
        # One owner file lock, not a separate queue or lock registry. Nonblocking:
        # contention is explicit; the caller never starts an automatic retry loop.
        fd = os.open(out, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            novel, previous = novel_rows(fd=fd)
            bound = os.fstat(fd)
            live = out.stat(follow_symlinks=False)
            if (bound.st_dev, bound.st_ino) != (live.st_dev, live.st_ino):
                raise EvidenceError("consensus_target_binding_changed_before_append")
            try:
                # Creation mode does not narrow a pre-existing archive. Keep
                # private evidence private even after an older manual import.
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "a", encoding="utf-8", closefd=False) as handle:
                    appended = append_receipts(out, novel, handle=handle)
                live = out.stat(follow_symlinks=False)
                if (bound.st_dev, bound.st_ino) != (live.st_dev, live.st_ino):
                    raise EvidenceError("consensus_target_binding_changed_after_append")
                readback, after = read_jsonl(out, fd=fd)
                ids = {row["receipt_id"] for row in readback}
                if after["status"] not in {"ready", "empty"} or any(row["receipt_id"] not in ids for row in novel):
                    raise EvidenceError("consensus_append_readback_unqualified")
                live = out.stat(follow_symlinks=False)
                if (bound.st_dev, bound.st_ino) != (live.st_dev, live.st_ino):
                    raise EvidenceError("consensus_target_binding_changed_after_readback")
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise ConsensusAppendUncertain("Inspect original " + CONSENSUS_PATH + " before any replay") from exc
        finally:
            os.close(fd)
    else:
        novel, previous = novel_rows()
        appended, after = 0, previous
    return {"schema": "release_consensus_ingest.v1", "committed": commit,
            "input_sha256": meta["sha256"], "input_rows": len(inputs), "novel_rows": len(novel),
            "appended": appended, "recorded_at": recorded_at, "ledger_sha256": after["sha256"],
            "receipt_ids": [row["receipt_id"] for row in novel],
            "clock_policy": "ingestion_time_not_caller_supplied", "path": CONSENSUS_PATH}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Authorized local JSONL economist polls")
    parser.add_argument("--root", type=Path, default=_ROOT)
    parser.add_argument("--commit", action="store_true", help="Append qualified snapshots with current capture clocks")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(ingest(args.source, args.root, commit=args.commit), sort_keys=True, allow_nan=False))
        return 0
    except ConsensusAppendUncertain as exc:
        print(json.dumps({"status": "effect_unknown", "retry_allowed": False, "reason": str(exc)}), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
