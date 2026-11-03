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
"""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKERS = 2


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

    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_file, path) for path in files]
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
