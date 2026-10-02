#!/usr/bin/env python3
"""Recycle a PC CI listener only after GitHub has made its bound job terminal.

This is an ephemeral child of the existing systemd runner service, not a second
scheduler or service supervisor. The job-start hook launches one copy after host
admission. A normal --once listener exit tears this process down with the service
cgroup. If GitHub loses the runner and marks the exact bound job terminal while
the local listener remains alive, two terminal reads trigger SIGTERM of that
same listener identity; the existing systemd KillMode=control-group and
Restart=always contract performs cleanup and restart.

The GitHub API read is intentionally unauthenticated. macro is public and job
state is public; no candidate job receives an Actions token through this helper.
API ambiguity, rate limiting, private-repository migration, process-identity
drift, or any other read failure is fail-safe: do not signal the listener.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Iterable

REPOSITORY = "mastermindx-market-intelligence/macro"
RUNNER_ROOT_RE = re.compile(r"/opt/mastermind-ci/runner-[1-4]")
ACTIVE_STATUSES = {"queued", "in_progress"}
API_TIMEOUT_SECONDS = 10
INITIAL_BIND_DELAY_SECONDS = 10
BIND_ATTEMPTS = 4
BIND_RETRY_SECONDS = 15
POLL_SECONDS = 300
TERMINAL_CONFIRM_SECONDS = 30
TERM_GRACE_SECONDS = 20
MAX_LIFETIME_SECONDS = 4 * 60 * 60


def _emit(log_path: Path | None, event: str, **fields: object) -> None:
    if log_path is None:
        return
    row = {
        "schema": "runner.terminal_watchdog.v1",
        "ts_unix": round(time.time(), 3),
        "event": event,
        **fields,
    }
    try:
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(log_path, flags, 0o600)
        try:
            os.write(fd, (json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except OSError:
        pass


def _proc_status(pid: int, proc_root: Path) -> tuple[int, int] | None:
    try:
        fields: dict[str, str] = {}
        for line in (proc_root / str(pid) / "status").read_text(encoding="utf-8").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value.strip()
        return int(fields["Pid"]), int(fields["PPid"])
    except (KeyError, OSError, ValueError):
        return None


def _proc_start_ticks(pid: int, proc_root: Path) -> int | None:
    try:
        raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
        close = raw.rfind(")")
        if close < 0:
            return None
        after = raw[close + 2 :].split()
        # /proc/<pid>/stat field 22 is starttime; 'after' starts at field 3.
        return int(after[19])
    except (IndexError, OSError, ValueError):
        return None


def _proc_cmdline(pid: int, proc_root: Path) -> str:
    try:
        return (
            (proc_root / str(pid) / "cmdline")
            .read_bytes()
            .replace(b"\0", b" ")
            .decode("utf-8", errors="replace")
            .strip()
        )
    except OSError:
        return ""


def find_listener_identity(ancestor_pid: int, proc_root: Path = Path("/proc")) -> tuple[int, int] | None:
    """Bind the exact Runner.Listener ancestor by PID and kernel start ticks."""

    pid = ancestor_pid
    seen: set[int] = set()
    for _ in range(12):
        if pid <= 1 or pid in seen:
            return None
        seen.add(pid)
        status = _proc_status(pid, proc_root)
        if status is None or status[0] != pid:
            return None
        cmdline = _proc_cmdline(pid, proc_root)
        if "Runner.Listener" in cmdline and "run" in cmdline and "--once" in cmdline:
            ticks = _proc_start_ticks(pid, proc_root)
            return (pid, ticks) if ticks is not None else None
        pid = status[1]
    return None


def listener_matches(identity: tuple[int, int], proc_root: Path = Path("/proc")) -> bool:
    pid, start_ticks = identity
    return (
        _proc_start_ticks(pid, proc_root) == start_ticks
        and "Runner.Listener" in _proc_cmdline(pid, proc_root)
        and "--once" in _proc_cmdline(pid, proc_root)
    )


def open_listener_pidfd(
    identity: tuple[int, int],
    proc_root: Path = Path("/proc"),
    *,
    opener: Callable[[int, int], int] = os.pidfd_open,
    closer: Callable[[int], None] = os.close,
) -> int | None:
    """Bind an instance-stable handle and re-prove the Listener after open."""

    pid, _start_ticks = identity
    try:
        pidfd = opener(pid, 0)
    except OSError:
        return None
    if listener_matches(identity, proc_root):
        return pidfd
    try:
        closer(pidfd)
    except OSError:
        pass
    return None


def close_pidfd(pidfd: int, closer: Callable[[int], None] = os.close) -> None:
    try:
        closer(pidfd)
    except OSError:
        pass


def fetch_jobs(repository: str, run_id: int, run_attempt: int) -> list[dict]:
    if repository != REPOSITORY or run_id <= 0 or run_attempt <= 0:
        raise ValueError("watchdog is repository-bound")
    quoted = urllib.parse.quote(repository, safe="/")
    url = (
        f"https://api.github.com/repos/{quoted}/actions/runs/{run_id}"
        f"/attempts/{run_attempt}/jobs?per_page=100"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "mastermind-pc-ci-terminal-watchdog/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("malformed jobs response")
    total = payload.get("total_count")
    if not isinstance(total, int) or total > 100:
        raise ValueError("jobs response is incomplete or oversized")
    return [job for job in payload["jobs"] if isinstance(job, dict)]


def select_active_job(jobs: Iterable[dict], runner_name: str) -> int | None:
    matches = []
    for job in jobs:
        if job.get("runner_name") != runner_name:
            continue
        if job.get("status") not in ACTIVE_STATUSES:
            continue
        job_id = job.get("id")
        if isinstance(job_id, int) and job_id > 0:
            matches.append(job_id)
    return matches[0] if len(matches) == 1 else None


def bound_job_is_terminal(jobs: Iterable[dict], job_id: int, runner_name: str) -> bool:
    matches = [
        job
        for job in jobs
        if job.get("id") == job_id and job.get("runner_name") == runner_name
    ]
    return len(matches) == 1 and matches[0].get("status") == "completed"


def monitor(
    *,
    repository: str,
    run_id: int,
    run_attempt: int,
    runner_name: str,
    ancestor_pid: int,
    runner_root: Path,
    proc_root: Path = Path("/proc"),
    fetcher: Callable[[str, int, int], list[dict]] = fetch_jobs,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    pidfd_opener: Callable[[int, int], int] = os.pidfd_open,
    pidfd_signaler: Callable[[int, int], None] = signal.pidfd_send_signal,
    pidfd_closer: Callable[[int], None] = os.close,
    initial_delay: float = INITIAL_BIND_DELAY_SECONDS,
    bind_attempts: int = BIND_ATTEMPTS,
    bind_retry: float = BIND_RETRY_SECONDS,
    poll_seconds: float = POLL_SECONDS,
    confirm_seconds: float = TERMINAL_CONFIRM_SECONDS,
    term_grace_seconds: float = TERM_GRACE_SECONDS,
    max_lifetime_seconds: float = MAX_LIFETIME_SECONDS,
) -> int:
    root_text = str(runner_root)
    if repository != REPOSITORY or not RUNNER_ROOT_RE.fullmatch(root_text):
        return 64
    if run_id <= 0 or run_attempt <= 0 or not runner_name:
        return 64

    log_path = runner_root / "_diag" / "runner-terminal-watchdog.jsonl"
    listener = find_listener_identity(ancestor_pid, proc_root)
    if listener is None:
        _emit(log_path, "listener_unbound", run_id=run_id, runner_name=runner_name)
        return 0

    listener_pidfd = open_listener_pidfd(
        listener,
        proc_root,
        opener=pidfd_opener,
        closer=pidfd_closer,
    )
    if listener_pidfd is None:
        _emit(log_path, "listener_pidfd_unbound", run_id=run_id, runner_name=runner_name)
        return 0

    _emit(
        log_path,
        "armed",
        run_id=run_id,
        run_attempt=run_attempt,
        runner_name=runner_name,
        listener_pid=listener[0],
        listener_start_ticks=listener[1],
    )
    if initial_delay:
        sleeper(initial_delay)

    bound_job_id: int | None = None
    for attempt in range(max(bind_attempts, 1)):
        try:
            bound_job_id = select_active_job(fetcher(repository, run_id, run_attempt), runner_name)
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            _emit(log_path, "bind_read_failed", attempt=attempt + 1, error=type(exc).__name__)
        if bound_job_id is not None:
            break
        if attempt + 1 < max(bind_attempts, 1) and bind_retry:
            sleeper(bind_retry)

    if bound_job_id is None:
        _emit(log_path, "job_unbound", run_id=run_id, runner_name=runner_name)
        close_pidfd(listener_pidfd, pidfd_closer)
        return 0

    _emit(log_path, "job_bound", run_id=run_id, job_id=bound_job_id, runner_name=runner_name)
    deadline = monotonic() + max_lifetime_seconds
    while monotonic() < deadline:
        if poll_seconds:
            sleeper(poll_seconds)
        try:
            first = fetcher(repository, run_id, run_attempt)
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            _emit(log_path, "poll_failed", job_id=bound_job_id, error=type(exc).__name__)
            continue
        if not bound_job_is_terminal(first, bound_job_id, runner_name):
            continue

        _emit(log_path, "terminal_observed", job_id=bound_job_id)
        if confirm_seconds:
            sleeper(confirm_seconds)
        try:
            second = fetcher(repository, run_id, run_attempt)
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            _emit(log_path, "confirm_failed", job_id=bound_job_id, error=type(exc).__name__)
            continue
        if not bound_job_is_terminal(second, bound_job_id, runner_name):
            _emit(log_path, "terminal_not_confirmed", job_id=bound_job_id)
            continue
        if not listener_matches(listener, proc_root):
            _emit(log_path, "listener_identity_changed", job_id=bound_job_id)
            close_pidfd(listener_pidfd, pidfd_closer)
            return 0

        _emit(log_path, "recycle_sigterm", job_id=bound_job_id, listener_pid=listener[0])
        try:
            pidfd_signaler(listener_pidfd, signal.SIGTERM)
        except (OSError, PermissionError):
            _emit(log_path, "recycle_sigterm_failed", job_id=bound_job_id)
            close_pidfd(listener_pidfd, pidfd_closer)
            return 0

        if term_grace_seconds:
            sleeper(term_grace_seconds)
        if listener_matches(listener, proc_root):
            _emit(log_path, "recycle_sigkill", job_id=bound_job_id, listener_pid=listener[0])
            try:
                pidfd_signaler(listener_pidfd, signal.SIGKILL)
            except (OSError, PermissionError):
                _emit(log_path, "recycle_sigkill_failed", job_id=bound_job_id)
        close_pidfd(listener_pidfd, pidfd_closer)
        return 0

    _emit(log_path, "watch_expired", run_id=run_id, job_id=bound_job_id)
    close_pidfd(listener_pidfd, pidfd_closer)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--runner-name", required=True)
    parser.add_argument("--ancestor-pid", required=True, type=int)
    parser.add_argument("--runner-root", required=True, type=Path)
    args = parser.parse_args(argv)
    return monitor(
        repository=args.repository,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        runner_name=args.runner_name,
        ancestor_pid=args.ancestor_pid,
        runner_root=args.runner_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
