#!/usr/bin/env python3
"""Run each FIF class-A kernel file in its own interpreter.

Hosted dispatch 41580998932 ran this suite as one pytest process for 73m50s.
A shared two-worker pytest-xdist run (41601828795, head b0003bd) finished the
same 4030 tests in 22m52s, then failed two of them on gw1:

- tests/test_fif_excel_refresh_harness.py::test_build_app_does_not_import_app_main
  saw app.main imported by another file in that worker.
- tests/test_fundamental_forensics_financial_packet_api.py::test_default_provider_returns_503
  received 400 from the production provider instead of the default 503.

``--dist loadfile`` keeps a file's own tests together. It does not give the
file a clean process. Serial CI already proved the file list in one
interpreter per file. This runner keeps that contract and runs two files at
once. A non-zero pytest status fails the step. Nothing is retried.

Hosted run 41613020910 (head 1d44a8f7bddfd) measured the isolated two-worker
step at 46m01s. The two longest files ran back to back:

- tests/test_fundamental_forensics_production_publisher.py ~1018s
- tests/test_fif_coverage_manifest.py ~959s

ThreadPoolExecutor starts the first ``--workers`` submissions immediately and
queues the rest FIFO. Sorting by pinned hosted durations (longest first) puts
those two on opposite workers at t=0 instead of serializing them after the
shorter prefix drains unevenly.
"""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKERS = 2

# Hosted seconds from run 41613020910 / job 125840711020. Unknown files keep
# weight 1 so they fill after the measured heavies. Update only from a new
# hosted measurement of this same runner.
FILE_WEIGHTS: dict[str, int] = {
    "tests/test_fundamental_forensics_production_publisher.py": 1018,
    "tests/test_fif_coverage_manifest.py": 959,
    "tests/test_fif_a18_publish_fault_drill.py": 426,
    "tests/test_fif_specialist_packs.py": 366,
}


class UsageError(Exception):
    """The runner was asked to do something other than two isolated files."""


def validate_invocation(workers: int, files: list[str]) -> None:
    if workers != WORKERS:
        raise UsageError(f"--workers must be {WORKERS}")
    if not files:
        raise UsageError("at least one tests/*.py file is required")
    seen: set[str] = set()
    for path in files:
        if path in seen:
            raise UsageError(f"duplicate file {path}")
        seen.add(path)
        parent, sep, name = path.partition("/")
        if sep != "/" or parent != "tests" or "/" in name or not name.endswith(".py"):
            raise UsageError(f"refusing non-file target {path}")


def schedule_files(files: list[str]) -> list[str]:
    """Longest-processing-time-first order from pinned hosted weights."""
    indexed = list(enumerate(files))
    indexed.sort(key=lambda item: (-FILE_WEIGHTS.get(item[1], 1), item[0]))
    return [path for _, path in indexed]


def _run_file(path: str) -> tuple[str, int]:
    print(f"FIF kernel file: {path}", flush=True)
    completed = subprocess.run([sys.executable, "-m", "pytest", "-q", path])
    return path, completed.returncode


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] != "--workers":
        print("fif kernel runner: usage is --workers 2 tests/<file>.py ...", file=sys.stderr)
        return 2
    if len(args) < 2:
        print("fif kernel runner: --workers requires a value", file=sys.stderr)
        return 2
    try:
        workers = int(args[1])
    except ValueError:
        print("fif kernel runner: --workers must be 2", file=sys.stderr)
        return 2
    files = args[2:]
    try:
        validate_invocation(workers, files)
    except UsageError as exc:
        print(f"fif kernel runner: {exc}", file=sys.stderr)
        return 2

    ordered = schedule_files(files)
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_file, path) for path in ordered]
        for future in as_completed(futures):
            path, code = future.result()
            if code != 0:
                failures.append(f"{path} exit {code}")
    if failures:
        print("FIF kernel file failures:", file=sys.stderr)
        for item in sorted(failures):
            print(item, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
