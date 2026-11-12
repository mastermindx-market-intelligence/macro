"""Read host load, sampled CPU activity, memory, swap and pressure without sleeps.

Load average is not CPU utilization. Activity is derived from consecutive kernel
counter samples; the first/invalid sample is unknown, never a fabricated zero.
No sampler thread, persistence, privileged calls or additional polling owner.
"""
from __future__ import annotations

import math
import os
import shutil
import threading
import time

_SAMPLE_LOCK = threading.Lock()
_PREVIOUS = None
_LAST_ACTIVITY = None
_MIN_SAMPLE_SECONDS = 0.25


def _meminfo() -> dict | None:
    out: dict[str, int] = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, v = line.partition(":")
                parts = v.strip().split()
                if parts:
                    out[k.strip()] = int(parts[0]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return out


def _uptime_s() -> float | None:
    try:
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def _cpu_counters() -> tuple[int, ...] | None:
    try:
        with open("/proc/stat") as f:
            fields = f.readline().split()
        # guest/guest_nice are already included in user/nice: do not add twice.
        values = tuple(int(v) for v in fields[1:9])
        if fields[0] != "cpu" or len(values) != 8 or min(values) < 0:
            return None
        return values
    except (OSError, ValueError, IndexError):
        return None


def _swap_counters() -> tuple[int, int] | None:
    try:
        values = {}
        with open("/proc/vmstat") as f:
            for line in f:
                fields = line.split()
                if fields and fields[0] in {"pswpin", "pswpout"}:
                    values[fields[0]] = int(fields[1])
        result = values["pswpin"], values["pswpout"]
        return result if min(result) >= 0 else None
    except (OSError, ValueError, IndexError, KeyError):
        return None


def _unknown_activity() -> dict:
    return {"utilization_pct": None, "iowait_pct": None, "steal_pct": None,
            "sample_seconds": None, "swap_in_bytes_per_second": None,
            "swap_out_bytes_per_second": None}


def _activity() -> dict:
    global _PREVIOUS, _LAST_ACTIVITY
    # Serialize the short /proc reads as well as baseline advancement. Otherwise
    # two summary requests can install out-of-order counters and false deltas.
    with _SAMPLE_LOCK:
        now = time.monotonic()
        cpu, swap = _cpu_counters(), _swap_counters()
        result = _unknown_activity()
        if cpu is None:
            _PREVIOUS = _LAST_ACTIVITY = None
            return result
        current = (now, cpu, swap)
        previous = _PREVIOUS
        if previous is None:
            _PREVIOUS = current
            return result
        elapsed = now - previous[0]
        delta = tuple(new - old for new, old in zip(cpu, previous[1]))
        if elapsed <= 0 or any(value < 0 for value in delta):
            _PREVIOUS, _LAST_ACTIVITY = current, None
            return result
        # Repeated callers do not shorten the measurement window to microseconds.
        if elapsed < _MIN_SAMPLE_SECONDS:
            return dict(_LAST_ACTIVITY) if _LAST_ACTIVITY is not None else result
        _PREVIOUS = current
        total = sum(delta)
        if total <= 0:
            _LAST_ACTIVITY = None
            return result
        busy = delta[0] + delta[1] + delta[2] + delta[5] + delta[6]
        result.update(utilization_pct=round(busy / total * 100, 1),
                      iowait_pct=round(delta[4] / total * 100, 1),
                      steal_pct=round(delta[7] / total * 100, 1),
                      sample_seconds=round(elapsed, 3))
        if swap is not None and previous[2] is not None:
            difference = tuple(new - old for new, old in zip(swap, previous[2]))
            try:
                page_size = os.sysconf("SC_PAGE_SIZE")
            except (OSError, ValueError, AttributeError):
                page_size = 0
            if min(difference) >= 0 and page_size > 0:
                result.update(
                    swap_in_bytes_per_second=round(difference[0] * page_size / elapsed, 1),
                    swap_out_bytes_per_second=round(difference[1] * page_size / elapsed, 1))
        _LAST_ACTIVITY = dict(result)
        return result


def _pressure() -> dict:
    out = {}
    for resource in ("cpu", "memory", "io"):
        rows = {}
        try:
            with open(f"/proc/pressure/{resource}") as f:
                for line in f:
                    fields = line.split()
                    if not fields or fields[0] not in {"some", "full"}:
                        continue
                    values = dict(field.split("=", 1) for field in fields[1:])
                    averages = {key: float(values[key])
                                for key in ("avg10", "avg60", "avg300")}
                    if all(math.isfinite(v) and 0 <= v <= 100 for v in averages.values()):
                        rows[fields[0]] = averages
        except (OSError, ValueError, KeyError):
            rows = {}
        out[resource] = rows or None
    return out


def snapshot() -> dict:
    is_linux = os.path.exists("/proc/meminfo")
    try:
        load1, load5, load15 = os.getloadavg()
    except (OSError, AttributeError):
        load1 = load5 = load15 = None
    cpus = os.cpu_count() or 1
    activity = _activity() if is_linux else _unknown_activity()
    mem = _meminfo() or {}
    mem_block = None
    total, avail = mem.get("MemTotal"), mem.get("MemAvailable")
    if total and avail is not None:
        mem_block = {"total": total, "available": avail, "used": total - avail,
                     "used_pct": round((total - avail) / total * 100, 1)}
    swap_total, swap_free = mem.get("SwapTotal"), mem.get("SwapFree")
    swap_block = None
    if swap_total and swap_free is not None and swap_total > 0:
        swap_block = {"total": swap_total, "used": swap_total - swap_free,
                      "used_pct": round((swap_total - swap_free) / swap_total * 100, 1),
                      "in_bytes_per_second": activity["swap_in_bytes_per_second"],
                      "out_bytes_per_second": activity["swap_out_bytes_per_second"]}
    du = shutil.disk_usage("/")
    return {
        "available": is_linux, "now": int(time.time()),
        "cpu": {
            "count": cpus, "load1": load1, "load5": load5, "load15": load15,
            # Compatibility field only; never label this CPU utilization.
            "load1_pct": round(load1 / cpus * 100, 1) if load1 is not None else None,
            "load1_ratio": round(load1 / cpus, 3) if load1 is not None else None,
            **{key: activity[key] for key in
               ("utilization_pct", "iowait_pct", "steal_pct", "sample_seconds")},
        },
        "memory": mem_block, "swap": swap_block,
        "disk": {"total": du.total, "used": du.used, "free": du.free,
                 "used_pct": round(du.used / du.total * 100, 1)},
        "pressure": _pressure() if is_linux else {},
        "uptime_s": _uptime_s(),
    }
