#!/usr/bin/env python3
"""Read-first Linux fleet disk sentinel; never deletes workspaces or Git data.

This companion to scripts/worktree_gc.py is deliberately NOT a second
worktree GC.  It provides host-disk and CI admission visibility, catches
rapid scratch growth, and optionally caps archived journald logs only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

GIB = 1024 ** 3
# Exact enrolled Linux host -> pytest fixture owner. No implicit other-host grants.
PYTEST_TEMP_OWNER = {
    "ubuntu0-MS-A2": "ubuntu0",
    "mastermind-pc": "longr",
    "ubuntu2": "ubuntu2",
    "ubuntu3-MS-7E61": "ubuntu3",
}
DEFAULT_RECEIPT = "/var/lib/mastermind-storage-guard/latest.json"
SCHEMA = "mastermind.ubuntu_storage_guard.v1"


def pressure(available_bytes: int, total_bytes: int) -> tuple[str, list[str], float]:
    if total_bytes <= 0 or available_bytes < 0 or available_bytes > total_bytes:
        raise ValueError("invalid filesystem capacity")
    used = 100.0 * (1.0 - available_bytes / total_bytes)
    reasons = []
    if used >= 92 or available_bytes < 35 * GIB:
        level = "EMERGENCY"
    elif used >= 85 or available_bytes < 100 * GIB:
        level = "CRITICAL"
    elif used >= 80 or available_bytes < 180 * GIB:
        level = "WARNING"
    else:
        level = "HEALTHY"
    if used >= 85:
        reasons.append("ci_disk_used_ceiling_85pct")
    if available_bytes < 100 * GIB:
        reasons.append("ci_disk_free_floor_100gib")
    if level != "HEALTHY" and not reasons:
        reasons.append("early_warning_margin")
    return level, reasons, round(used, 2)


def disk_status(root: str = "/") -> dict:
    fs = os.statvfs(root)
    total = fs.f_blocks * fs.f_frsize
    available = fs.f_bavail * fs.f_frsize
    level, reasons, used_pct = pressure(available, total)
    return {
        "mount": root,
        "total_bytes": total,
        "available_bytes": available,
        "available_gib": round(available / GIB, 2),
        "used_percent": used_pct,
        "level": level,
        "reasons": reasons,
    }


def systemd_units() -> dict[str, str]:
    names = [
        f"actions.runner.mastermindx-market-intelligence-macro.pc-ci-{n}.service"
        for n in range(1, 5)
    ]
    try:
        p = subprocess.run(
            ["systemctl", "list-unit-files", "--no-pager", "--no-legend"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"runner_inventory": "unavailable"}
    installed = {line.split()[0] for line in p.stdout.splitlines() if line.strip()}
    if not any(name in installed for name in names):
        return {"runner_inventory": "not_this_host"}
    out: dict[str, str] = {}
    for n, name in enumerate(names, 1):
        if name not in installed:
            out[f"pc-ci-{n}"] = "missing"
            continue
        try:
            s = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True, text=True, timeout=3, check=False,
            )
            out[f"pc-ci-{n}"] = s.stdout.strip() or "unavailable"
        except (OSError, subprocess.TimeoutExpired):
            out[f"pc-ci-{n}"] = "unavailable"
    return out


def scratch_snapshot(root: str = "/tmp/fif-shipprep") -> dict:
    target = Path(root)
    if not target.is_dir() or target.is_symlink():
        return {"present": False}
    now = time.time()
    dirs = 0
    materialized = 0
    old = 0
    newest = None
    try:
        for item in os.scandir(target):
            if not item.is_dir(follow_symlinks=False):
                continue
            dirs += 1
            st = item.stat(follow_symlinks=False)
            newest = max(newest or 0, st.st_mtime)
            if now - st.st_mtime > 24 * 3600:
                old += 1
            if os.path.isdir(item.path + "/tree") and not os.path.islink(item.path + "/tree"):
                materialized += 1
    except OSError:
        return {"present": True, "inventory": "incomplete"}
    return {
        "present": True,
        "subdirs": dirs,
        "materialized_tree_dirs": materialized,
        "older_than_24h": old,
        "newest_age_minutes": (
            round((now - newest) / 60, 1) if newest else None
        ),
    }


def compute_growth(previous: dict | None, observed: dict, now: float) -> dict:
    if not previous or previous.get("schema") != SCHEMA:
        return {"available_gib_per_hour": None, "trend": "no_previous_sample"}
    prev = previous.get("disk") or {}
    old_time = previous.get("observed_epoch")
    old_avail = prev.get("available_bytes")
    if not isinstance(old_time, (int, float)) or not isinstance(old_avail, int):
        return {"available_gib_per_hour": None, "trend": "previous_invalid"}
    seconds = now - old_time
    if seconds < 300 or seconds > 172800:
        return {"available_gib_per_hour": None, "trend": "interval_out_of_range"}
    rate = ((observed["available_bytes"] - old_avail) / GIB) / (seconds / 3600)
    return {
        "available_gib_per_hour": round(rate, 2),
        "trend": "rapid_filling" if rate <= -8 else (
            "filling" if rate <= -2 else "stable_or_recovering"
        ),
    }


def load_previous(path: Path) -> dict | None:
    try:
        if path.is_symlink():
            return None
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except (OSError, ValueError):
        return None


def save_receipt(path: Path, data: dict) -> None:
    if path.is_symlink():
        raise RuntimeError("refuse symlink receipt")
    parent = path.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.is_symlink():
        raise RuntimeError("refuse symlink receipt directory")
    os.chmod(parent, 0o700)
    tmp = parent / (".storage-status-" + str(os.getpid()) + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def vacuum_archived_journals() -> dict:
    """Only accepted automatic destructive operation: archived system journals."""
    try:
        p = subprocess.run(
            ["journalctl", "--vacuum-size=800M"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, timeout=40,
        )
        return {"attempted": True, "exit_code": p.returncode,
                "detail": p.stderr[-300:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"attempted": True, "error": type(e).__name__}


def run(args: argparse.Namespace) -> dict:
    now = time.time()
    path = Path(args.receipt)
    previous = load_previous(path)
    disk = disk_status()
    health = {
        "schema": SCHEMA,
        "observed_epoch": now,
        "observed_utc": dt.datetime.fromtimestamp(
            now, dt.timezone.utc
        ).isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "disk": disk,
        "growth": compute_growth(previous, disk, now),
        "runners": systemd_units(),
        "scratch": scratch_snapshot(),
        "gc_mode": "read_only",
        "source_delete_enabled": False,
    }
    if args.vacuum and disk["level"] in {"WARNING", "CRITICAL", "EMERGENCY"}:
        health["journal_maintenance"] = vacuum_archived_journals()
        health["disk"] = disk_status()
    else:
        health["journal_maintenance"] = {"attempted": False}
    # OFF by default and intentionally absent from the installed systemd unit.
    # This is not a new scheduler: future admission may add this exact flag
    # to the existing sentinel after source review and host canary.
    health["pytest_reclaim"] = {"attempted": False}
    if getattr(args, "reclaim_pytest_garbage", False):
        owner = PYTEST_TEMP_OWNER.get(socket.gethostname())
        if not owner:
            health["pytest_reclaim"] = {
                "attempted": False, "status": "REFUSED_UNENROLLED_HOST",
            }
        elif health["disk"]["level"] not in {"CRITICAL", "EMERGENCY"}:
            health["pytest_reclaim"] = {
                "attempted": False, "status": "HEALTHY_OR_WARNING",
            }
        else:
            health["gc_mode"] = "pytest_garbage_only"
            try:
                from ubuntu_pytest_temp_reclaim import reclaim
                result = reclaim(owner, apply=True, min_age_hours=24, max_dirs=3)
                health["pytest_reclaim"] = {"attempted": True, **result}
            except Exception as exc:
                # A failed subordinate delete may already have moved a source
                # leaf. Its own append-only ledger is the reconciliation owner.
                # Never convert this into a repeat or cross-host fallback.
                health["pytest_reclaim"] = {
                    "attempted": True,
                    "status": "RECONCILE_ORIGINAL_RECLAIM_LEDGER",
                    "reason": type(exc).__name__,
                }
            health["disk"] = disk_status()
    save_receipt(path, health)
    return health


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", default=DEFAULT_RECEIPT)
    parser.add_argument("--vacuum", action="store_true",
                        help="cap archived journald logs only under disk pressure")
    parser.add_argument("--reclaim-pytest-garbage", action="store_true",
                        help="opt-in guarded pytest garbage cleanup (never Git worktrees)")
    args = parser.parse_args(argv)
    report = run(args)
    print(json.dumps({
        "host": report["host"], "status": report["disk"]["level"],
        "used_pct": report["disk"]["used_percent"],
        "free_gib": report["disk"]["available_gib"],
        "growth": report["growth"]["trend"],
        "runner_status": report["runners"],
        "journal_maintenance": report["journal_maintenance"],
        "source_deletes": False,
        "pytest_reclaim": report["pytest_reclaim"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

