"""Authenticated admin projection of the incumbent router's bounded snapshot."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import stat
import time

from .capacity_fabric_schema import MAX_BYTES, TOKEN_FIELDS, clean_snapshot

DEFAULT_PATH = Path("/var/lib/macro-admin/capacity-router.json")


def _percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * p
    lo, hi = math.floor(position), math.ceil(position)
    return round(values[lo] + (values[hi] - values[lo]) * (position - lo), 1)


def panel(minutes=15, *, path=None, now=None):
    now = time.time() if now is None else now
    try:
        minutes = int(minutes)
    except (ValueError, TypeError):
        minutes = 15
    minutes = minutes if minutes in (5, 15, 60, 120) else 15
    path = Path(path or os.environ.get("CAPACITY_OBSERVATORY_PATH", str(DEFAULT_PATH)))
    unavailable = {"ok": False, "state": "disconnected", "generated_at": None, "age_s": None,
        "message": "Waiting for Capacity Fabric telemetry. The router may still be serving requests.",
        "routes": [], "active": [], "recent": [], "series": [], "aliases": {}, "window_minutes": minutes}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_BYTES:
                raise ValueError("invalid snapshot file")
            raw = os.read(fd, MAX_BYTES + 1)
        finally:
            os.close(fd)
        decoded = json.loads(raw)
        data = clean_snapshot(decoded)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return unavailable
    age = now - data["generated_at"]
    if age < -10:
        unavailable["message"] = "The router and admin clocks disagree. Live telemetry is paused."
        return unavailable
    age = max(0, age)
    data.update(ok=True, state="live" if age <= 15 else "stale", age_s=round(age, 1),
                window_minutes=minutes, received_at=decoded.get("received_at"))
    start = now - minutes * 60
    recent = [r for r in data["recent"] if (r["ended_at"] or 0) >= start]
    data["recent"] = recent
    data["series"] = [b for b in data["series"] if b["at"] + 60 > start]
    completed = sum(b["completed"] for b in data["series"])
    failed = sum(b["failed"] for b in data["series"])
    known = sum(b["usage_known"] for b in data["series"])
    totals = {k: sum(b[k] for b in data["series"]) for k in TOKEN_FIELDS}
    observed_s = max(1, min(minutes * 60, data["generated_at"] - data["started_at"]))
    latencies = [(r["first_content_at"] - r["started_at"]) * 1000 for r in recent
                 if r["first_content_at"] is not None and r["started_at"] is not None]
    consumers = {r["agent_id"] or r["session_id"] for r in data["active"] if r["agent_id"] or r["session_id"]}
    active_unknown = sum(not (r["agent_id"] or r["session_id"]) for r in data["active"])
    data["summary"] = {
        "active_requests": len(data["active"]) + data["totals"]["overflow_active"],
        "tracked_active_requests": len(data["active"]), "active_consumers": len(consumers),
        "unattributed_active": active_unknown,
        "awaiting_output": sum(r["first_content_at"] is None for r in data["active"]),
        "completed": completed, "failed": failed, "usage_known": known,
        "usage_coverage_pct": round(100 * known / (completed + failed), 1) if completed + failed else None,
        "output_tokens_per_s": round(totals["output_tokens"] / observed_s, 2) if known else None,
        "input_tokens": totals["input_tokens"] if any(b["input_tokens_known"] for b in data["series"]) else None,
        "output_tokens": totals["output_tokens"] if known else None,
        "cache_read_tokens": totals["cache_read_tokens"] if any(b["cache_read_tokens_known"] for b in data["series"]) else None,
        "p50_first_content_ms": _percentile(latencies, .5), "p95_first_content_ms": _percentile(latencies, .95),
        "first_content_samples": len(latencies), "observed_s": round(observed_s),
        "ready_routes": sum(not r["cooling"] for r in data["routes"]),
        "cooling_routes": sum(r["cooling"] for r in data["routes"]),
        "providers": len({r["provider"] for r in data["routes"]}),
        "models": len({m for r in data["routes"] for m in r["models"]}),
        "attributed_recent": sum(bool(r["agent_id"] or r["session_id"]) for r in recent),
        "recent_count": len(recent),
        "overflowing_families": sum(f["overflowing"] for f in (data.get("overflow") or {}).get("families", {}).values()),
        "over_target_keys": sum(k["over_target"] for k in (data.get("overflow") or {}).get("keys", {}).values()),
        "benched_lanes": sum(
            1 for a in (data.get("claude") or {}).get("accounts", [])
            for lane in a["families"].values()
            if lane["cooldown_until"] is not None and lane["cooldown_until"] > now),
        "peak_active": bool((data.get("peak") or {}).get("active")),
    }
    return data
