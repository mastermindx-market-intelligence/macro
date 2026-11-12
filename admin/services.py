"""Read core-service resources and failed systemd jobs using structured output.

No service starts/stops, journal payloads, credentials or process command lines.
Missing inspection is unknown, not an empty successful inventory.
"""
from __future__ import annotations

import json
import shutil
import subprocess

SERVICES = [
    ("caddy.service", "Caddy — web server / TLS"),
    ("macro-api.service", "macro API — FastAPI :8000"),
    ("admin.service", "Admin console — this panel"),
    ("terminal.service", "Mastermind Terminal — Next.js :3000"),
    ("mastermind.service", "Brain dashboard — :8001"),
]
_PROPS = ("LoadState", "ActiveState", "SubState", "UnitFileState",
          "ExecMainStartTimestamp", "MemoryCurrent", "MemorySwapCurrent",
          "MemoryPeak", "NRestarts", "Result")
_FAILED_LIMIT = 25


def _show(unit: str) -> dict:
    try:
        out = subprocess.run(
            ["systemctl", "show", unit, "--no-pager",
             "--property=" + ",".join(_PROPS)],
            capture_output=True, text=True, timeout=8)
        if out.returncode != 0:
            return {"_error": "systemctl show failed"}
    except (OSError, subprocess.SubprocessError):
        return {"_error": "systemctl show unavailable"}
    return dict(line.split("=", 1) for line in out.stdout.splitlines() if "=" in line)


def _failed_units() -> dict:
    unavailable = {"available": False, "count": None, "units": [], "truncated": False}
    try:
        out = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=failed",
             "--no-pager", "--no-legend", "--plain", "--output=json"],
            capture_output=True, text=True, timeout=5)
        if out.returncode != 0 or len(out.stdout) > 1024 * 1024:
            return unavailable
        items = json.loads(out.stdout)
        if not isinstance(items, list):
            return unavailable
        rows = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("unit"), str):
                return unavailable
            if item.get("active") != "failed" or not item["unit"].endswith(".service"):
                return unavailable
            rows.append({"unit": item["unit"],
                         "description": str(item.get("description") or "")[:500],
                         "active": "failed", "sub": str(item.get("sub") or "")[:80]})
        rows.sort(key=lambda row: row["unit"])
        return {"available": True, "count": len(rows), "units": rows[:_FAILED_LIMIT],
                "truncated": len(rows) > _FAILED_LIMIT}
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return unavailable


def _uint(value) -> int | None:
    # systemd's unset/unlimited sentinel must not become an exabyte memory value.
    if not isinstance(value, str) or not value.isdigit():
        return None
    try:
        number = int(value)
    except ValueError:
        return None
    return number if number < 2 ** 63 else None


def status() -> dict:
    if not shutil.which("systemctl"):
        return {"available": False, "services": [],
                "reason": "systemctl not found (not running on the VPS)"}
    rows = []
    for unit, label in SERVICES:
        d = _show(unit)
        active = d.get("ActiveState")
        memory, swap = _uint(d.get("MemoryCurrent")), _uint(d.get("MemorySwapCurrent"))
        rows.append({
            "unit": unit, "label": label,
            "loaded": d.get("LoadState") == "loaded",
            "active": active, "sub": d.get("SubState"),
            "enabled": d.get("UnitFileState"), "ok": active == "active",
            "since": d.get("ExecMainStartTimestamp") or None,
            "memory": memory, "swap_memory": swap,
            "memory_peak": _uint(d.get("MemoryPeak")),
            "memory_including_swap": memory + swap if memory is not None and swap is not None else None,
            "restarts": _uint(d.get("NRestarts")), "result": d.get("Result"),
            "inspection_error": d.get("_error"),
        })
    failures = _failed_units()
    core_known = all(not row["inspection_error"] and row["active"] is not None for row in rows)
    core_healthy = all(row["loaded"] and row["ok"] for row in rows) if core_known else None
    # Any observed failure is actionable; missing inspection is never green.
    healthy = None
    known_core_failure = any(not row["inspection_error"] and row["active"] is not None
                             and (not row["loaded"] or not row["ok"]) for row in rows)
    if known_core_failure or (failures["available"] and failures["count"] > 0):
        healthy = False
    elif core_known and failures["available"]:
        healthy = core_healthy
    return {
        "available": True, "services": rows,
        "ok_count": sum(1 for row in rows if row["ok"]), "total": len(rows),
        "healthy": healthy, "core_healthy": core_healthy, "failed_jobs": failures,
    }
