"""Accept content-free snapshots on the existing SSH channel; no listening socket."""
from __future__ import annotations

import fcntl
import json
import os
import sqlite3
from pathlib import Path
import sys
import tempfile
import time

from .capacity_fabric_schema import MAX_BYTES, clean_snapshot
from . import capacity_history, capacity_control_transport

SNAPSHOT_PATH = Path("/var/lib/macro-admin/capacity-router.json")


def ingest(raw, path=SNAPSHOT_PATH, *, now=None, recorder=None, _decoded=None):
    now = time.time() if now is None else now
    if len(raw) > MAX_BYTES:
        raise ValueError("snapshot exceeds bound")
    snapshot = clean_snapshot(json.loads(raw) if _decoded is None else _decoded)
    if snapshot["generated_at"] > now + 10 or snapshot["started_at"] > snapshot["generated_at"]:
        raise ValueError("invalid observation clock")
    if now - snapshot["generated_at"] > 120:
        return False
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("snapshot destination is not regular")
    lock_fd = os.open(path.with_suffix(".lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    temp_path = None
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        previous = None
        try:
            with open(path, "rb") as stream:
                previous = json.loads(stream.read(MAX_BYTES + 1))
        except (OSError, ValueError):
            pass
        if isinstance(previous, dict):
            if previous.get("epoch") == snapshot["epoch"]:
                if snapshot["sequence"] <= previous.get("sequence", -1):
                    return False
            elif snapshot["started_at"] <= previous.get("started_at", 0):
                # An old draining process must never replace the new process.
                return False
        # The incumbent ingestion owner persists a derived ledger, not a second
        # router or quota store. Storage failure must not interrupt live telemetry.
        try:
            if recorder is not None:
                recorder.record(snapshot, now=now)
            else:
                capacity_history.record(snapshot, path=capacity_history.database_path(path), now=now)
            history_state = "recorded"
        except (OSError, sqlite3.Error, ValueError, TypeError):
            history_state = "degraded"
        snapshot["history_state"] = history_state
        snapshot["received_at"] = now
        body = json.dumps(snapshot, separators=(",", ":"), allow_nan=False).encode()
        if len(body) > MAX_BYTES:
            raise ValueError("sanitized snapshot exceeds bound")
        fd, temp_path = tempfile.mkstemp(prefix=".capacity-", dir=path.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
        os.replace(temp_path, path)
        temp_path = None
        return True
    finally:
        if temp_path:
            os.unlink(temp_path)
        os.close(lock_fd)


def main():
    recorder = capacity_history.Recorder(capacity_history.database_path(SNAPSHOT_PATH))
    delivered = set()
    try:
        while True:
            raw = sys.stdin.buffer.readline(MAX_BYTES + 1)
            if not raw:
                return
            if len(raw) > MAX_BYTES or not raw.endswith(b"\n"):
                raise SystemExit("invalid observation frame")
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, dict) and set(decoded) == {"control_result"}:
                    capacity_control_transport.accept_result(decoded["control_result"])
                    continue
                accepted = ingest(raw, recorder=recorder, _decoded=decoded)
                if accepted:
                    request = capacity_control_transport.next_request(decoded["epoch"])
                    identity = (request.get("request_id") or request["operation_id"]) if request else None
                    if request and identity not in delivered:
                        print(json.dumps({"control_request": request}, separators=(",", ":")), flush=True)
                        delivered.add(identity)
                        if len(delivered) > 128:
                            delivered = {identity}
            except (ValueError, TypeError, KeyError, OSError):
                # Never echo a rejected payload or an exception containing source data.
                print("observation frame rejected", file=sys.stderr)
    finally:
        recorder.close()


if __name__ == "__main__":
    main()
