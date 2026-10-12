#!/usr/bin/env python3
"""Read-only live parent-chain census for Mastermind Fabric controller launches.

Observes a single host's `ps` snapshot, *not* Executive jobs, billed tokens,
accepted tasks, provider execution or historical usage. No persistent state.
Ancestor uncertainty is UNKNOWN, never inferred from source packet names.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    elapsed: str
    command: str


_LAUNCH = re.compile(
    r"^(?:/bin/bash|bash|/usr/bin/bash)\s+(?:\S*/)?remote_sub\.sh\s+"
    r"(?P<host>[A-Za-z0-9_.:-]+)\s+(?P<mode>[A-Za-z0-9_.:-]+)(?:\s|$)"
)


def parse_ps(text: str) -> dict[int, Process]:
    processes: dict[int, Process] = {}
    for line in text.splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) != 4:
            continue
        try:
            pid, ppid = int(fields[0]), int(fields[1])
        except ValueError:
            continue
        if pid <= 0 or ppid < 0 or pid in processes:
            continue
        processes[pid] = Process(pid, ppid, fields[2], fields[3])
    return processes


def _harness(command: str) -> str | None:
    # The CLI/host executable is evidence; arbitrary packet/branch names are not.
    if "/.claude/remote/ccd-cli/" in command or re.search(
        r"(?:^|/)(?:claude|claude-code)\s+--(?:output-format|input-format)", command
    ):
        return "CLAUDE"
    if re.search(r"(?:^|/)(?:codex|CodexCLI)(?:\s|$)", command) or (
        "codex app-server" in command
    ):
        return "CODEX"
    return None


def trace_parent(processes: dict[int, Process], ppid: int) -> tuple[str, int]:
    matches: set[str] = set()
    visited: set[int] = set()
    depth = 0
    pid = ppid
    while pid in processes and pid not in visited and pid > 1 and depth < 16:
        visited.add(pid)
        parent = processes[pid]
        kind = _harness(parent.command)
        if kind:
            matches.add(kind)
        pid = parent.ppid
        depth += 1
    if len(matches) > 1:
        return "CONFLICTING", depth
    if matches:
        return next(iter(matches)), depth
    return "UNKNOWN", depth


def census(processes: dict[int, Process]) -> dict:
    launches: list[dict] = []
    for p in processes.values():
        match = _LAUNCH.match(p.command)
        if not match:
            continue
        attribution, hops = trace_parent(processes, p.ppid)
        launches.append({
            "pid": p.pid,
            "host": match.group("host"),
            "mode": match.group("mode"),
            "parent_harness": attribution,
            "ancestor_hops": hops,
        })
    launches.sort(key=lambda p: p["pid"])
    return {
        "schema": "mastermind.fabric_launcher_parent_census.v1",
        "observation": "single_host_process_snapshot",
        "limitations": "controller_processes_only_not_worker_start_or_historical_usage",
        "controller_processes": len(launches),
        "by_parent_harness": dict(sorted(Counter(p["parent_harness"] for p in launches).items())),
        "by_target_host": dict(sorted(Counter(p["host"] for p in launches).items())),
        "by_requested_mode": dict(sorted(Counter(p["mode"] for p in launches).items())),
        "launches": launches,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ps-file", type=Path, help="read an existing ps snapshot; no subprocess")
    g.add_argument("--live", action="store_true", help="read one bounded local ps snapshot (default)")
    args = ap.parse_args()
    if args.ps_file is not None:
        raw = args.ps_file.read_text(encoding="utf-8")
    else:
        run = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,etime=,command="],
            check=False, capture_output=True, text=True, timeout=6,
        )
        if run.returncode or not run.stdout:
            raise RuntimeError("local_process_census_unavailable")
        raw = run.stdout
    report = census(parse_ps(raw))
    report["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
