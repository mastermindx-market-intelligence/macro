"""First-observed input rows inside the existing Dark Pool ledger namespace.

The existing daily-engine/nightly gate is the sole advancer. This is not a new
signal, event identity, watcher or control plane. No historical reconstruction
is admitted as live evidence; no outcome is inferred or graded here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path

from engine.ledger_lane import nightly_advance_enabled


def record_observation(result: dict, data: Path) -> dict:
    if not nightly_advance_enabled():
        raise PermissionError("Only the existing nightly engine may advance Dark Flow observations")
    now = datetime.now(timezone.utc)
    observed = datetime.fromisoformat(result["known_at"])
    if observed.tzinfo is None or abs((now - observed).total_seconds()) > 300:
        raise ValueError("A replay clock or old build cannot become a live observation")
    from collectors.finra_short_volume import expected_available_session
    if result.get("asof") != str(expected_available_session(now)):
        raise ValueError("A historical session cannot be relabeled as a current observation")
    current = result["current"]
    if current.get("value") is None or current.get("date") != result["asof"]:
        return {"state": "NO_COMPLETE_OBSERVATION", "rows_added": 0}
    if result.get("trade_authority") is not False or result.get("tier") != "display":
        raise ValueError("Observation must remain display-only")
    path = data / "darkpool/ledger/index_observations.jsonl"
    row = {"schema": "darkflow_observation.v1", "asof": result["asof"],
           "known_at": result["known_at"], "method": result["method"],
           "generation": result["generation"], "reading": current,
           "sectors": result["sectors"], "attribution_5d": result["attribution_5d"],
           "source_hashes": result["sources"], "context": result["context"],
           "evidence_basis": "observed_at_known_at_not_at_session_close",
           "trade_authority": False}
    payload = json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep-first and bounded local file locking, not another lifecycle/lease owner.
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            handle.seek(0)
            for line in handle:
                if not line.strip():
                    continue
                prior = json.loads(line)  # corruption refuses append; never rewrites history
                if prior.get("asof") == row["asof"] and prior.get("method") == row["method"]:
                    return {"state": "FIRST_OBSERVATION_RETAINED", "rows_added": 0,
                            "retained_generation": prior.get("generation")}
            end = handle.tell()
            if end:
                handle.seek(end - 1)
                if handle.read(1) != "\n":
                    raise ValueError("Existing ledger has an unterminated row; reconcile before append")
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            handle.seek(0, os.SEEK_END)
            position = handle.tell()
            handle.seek(position - len(payload.encode("utf-8")))
            if handle.read() != payload:
                raise RuntimeError("Appended observation readback failed; reconcile the existing file")
            return {"state": "OBSERVATION_RECORDED", "rows_added": 1, "generation": row["generation"]}
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
