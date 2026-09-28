#!/usr/bin/env python3
"""Conservative self-heal for persistent GitHub Actions listeners on the M2 Studio.

This closes the process-alive / service-offline failure mode where Runner.Listener
stays alive after a broker/acquire-job transport failure, so launchd sees a healthy
process while GitHub has stopped routing work to the runner.

Safety law:
- GitHub API blindness never triggers a restart.
- A runner must be explicitly offline twice, separated by a confirmation delay.
- The configured launchd service must still be loaded; an intentionally unloaded
  service is treated as maintenance and is never restarted.
- A live Runner.Worker process suppresses restart.
- No runner labels, registrations, workflow routes, or credentials are changed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DEFAULT_REPO = "mastermindx-market-intelligence/macro"
GH_BIN = os.environ.get("GH_BIN", "/opt/homebrew/bin/gh")
LAUNCHCTL = "/bin/launchctl"
PS = "/bin/ps"


@dataclass(frozen=True)
class RunnerSpec:
    name: str
    service: str
    root: Path


def default_specs(home: Path | None = None) -> tuple[RunnerSpec, ...]:
    home = home or Path.home()
    return (
        RunnerSpec(
            "mac-builder-3",
            "actions.runner.mastermindx-market-intelligence-macro.mac-builder-3",
            home / "actions-runner-3",
        ),
        RunnerSpec(
            "mac-builder-4",
            "actions.runner.chriswong6031-creator-macro.mac-builder-4",
            home / "actions-runner",
        ),
        RunnerSpec(
            "mac-builder-5",
            "actions.runner.chriswong6031-creator-macro.mac-builder-5",
            home / "actions-runner-2",
        ),
        RunnerSpec(
            "mac-builder-light",
            "actions.runner.chriswong6031-creator-macro.mac-builder-light",
            home / "actions-runner-4",
        ),
    )


def log(message: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"{now} {message}", flush=True)


def _run(argv: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def github_snapshot(repo: str) -> dict[str, dict] | None:
    """Return runner rows by name. None means API/auth/network blindness."""
    try:
        proc = _run(
            [GH_BIN, "api", f"repos/{repo}/actions/runners?per_page=100"],
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"INDETERMINATE github runner census failed: {exc}")
        return None
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().replace("\n", " ")[:400]
        log(f"INDETERMINATE github runner census rc={proc.returncode}: {detail}")
        return None
    try:
        payload = json.loads(proc.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        log(f"INDETERMINATE github runner census JSON invalid: {exc}")
        return None
    rows = payload.get("runners")
    if not isinstance(rows, list):
        log("INDETERMINATE github runner census has no runners list")
        return None
    return {
        str(row.get("name")): row
        for row in rows
        if isinstance(row, dict) and row.get("name")
    }


def service_loaded(spec: RunnerSpec, uid: int | None = None) -> bool:
    uid = os.getuid() if uid is None else uid
    proc = _run([LAUNCHCTL, "print", f"gui/{uid}/{spec.service}"], timeout=10)
    return proc.returncode == 0


def worker_active(spec: RunnerSpec) -> bool:
    """Fail safe: unreadable process census means active, so do not restart."""
    try:
        proc = _run([PS, "-axo", "command="], timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return True
    if proc.returncode != 0:
        return True
    root = str(spec.root)
    return any(
        root in line and "Runner.Worker" in line
        for line in proc.stdout.splitlines()
    )


def restart_candidates(
    snapshot: dict[str, dict],
    specs: Iterable[RunnerSpec],
    *,
    loaded: dict[str, bool],
    workers: dict[str, bool],
) -> list[RunnerSpec]:
    """Pure admission rule used by production and tests."""
    candidates: list[RunnerSpec] = []
    for spec in specs:
        row = snapshot.get(spec.name)
        if not isinstance(row, dict):
            continue
        if row.get("status") != "offline":
            continue
        if bool(row.get("busy")):
            continue
        if not loaded.get(spec.name, False):
            continue
        if workers.get(spec.name, True):
            continue
        candidates.append(spec)
    return candidates


def local_state(specs: Iterable[RunnerSpec]) -> tuple[dict[str, bool], dict[str, bool]]:
    loaded: dict[str, bool] = {}
    workers: dict[str, bool] = {}
    for spec in specs:
        loaded[spec.name] = service_loaded(spec)
        workers[spec.name] = worker_active(spec)
    return loaded, workers


def kickstart(spec: RunnerSpec, uid: int | None = None) -> bool:
    uid = os.getuid() if uid is None else uid
    proc = _run(
        [LAUNCHCTL, "kickstart", "-k", f"gui/{uid}/{spec.service}"],
        timeout=30,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().replace("\n", " ")[:400]
        log(f"ERROR {spec.name} kickstart failed rc={proc.returncode}: {detail}")
        return False
    log(f"REPAIRED {spec.name}: launchd kickstart issued")
    return True


def verify_online(repo: str, runner_name: str, seconds: int) -> bool:
    deadline = time.monotonic() + max(0, seconds)
    while True:
        snap = github_snapshot(repo)
        if snap is not None:
            row = snap.get(runner_name) or {}
            if row.get("status") == "online":
                log(f"VERIFIED {runner_name}: GitHub reports online")
                return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(5, max(0.1, deadline - time.monotonic())))


def run_watchdog(
    repo: str,
    specs: tuple[RunnerSpec, ...],
    *,
    confirm_seconds: int,
    verify_seconds: int,
    dry_run: bool,
) -> int:
    first = github_snapshot(repo)
    if first is None:
        return 0

    loaded1, workers1 = local_state(specs)
    first_candidates = restart_candidates(
        first, specs, loaded=loaded1, workers=workers1
    )
    if not first_candidates:
        log("HEALTHY no loaded idle M2 runner is GitHub-offline")
        return 0

    names = ",".join(spec.name for spec in first_candidates)
    log(f"SUSPECT offline candidate(s): {names}; confirming before repair")
    if confirm_seconds > 0:
        time.sleep(confirm_seconds)

    second = github_snapshot(repo)
    if second is None:
        return 0
    loaded2, workers2 = local_state(first_candidates)
    confirmed = restart_candidates(
        second, first_candidates, loaded=loaded2, workers=workers2
    )
    if not confirmed:
        log("RECOVERED candidates cleared during confirmation window; no action")
        return 0
    if len(confirmed) > 1:
        names = ",".join(spec.name for spec in confirmed)
        log(
            "INDETERMINATE multiple M2 runners remain offline "
            f"({names}); refusing fleet-wide restart"
        )
        return 0

    failures = 0
    for spec in confirmed:
        if dry_run:
            log(f"DRY-RUN would kickstart {spec.name} ({spec.service})")
            continue
        if not kickstart(spec):
            failures += 1
            continue
        if not verify_online(repo, spec.name, verify_seconds):
            log(f"ERROR {spec.name}: did not return online within {verify_seconds}s")
            failures += 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--confirm-seconds", type=int, default=30)
    parser.add_argument("--verify-seconds", type=int, default=90)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Restrict to one or more configured runner names.",
    )
    args = parser.parse_args(argv)

    specs = default_specs()
    if args.only:
        wanted = set(args.only)
        specs = tuple(spec for spec in specs if spec.name in wanted)
        missing = wanted - {spec.name for spec in specs}
        if missing:
            parser.error(f"unknown runner(s): {','.join(sorted(missing))}")
    if not specs:
        parser.error("no runners selected")

    return run_watchdog(
        args.repo,
        specs,
        confirm_seconds=max(0, args.confirm_seconds),
        verify_seconds=max(0, args.verify_seconds),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
