"""Dedicated bounded execution of an existing catalog Lab recipe.

The audit hook is defense against accidental side effects in trusted catalog code,
not a sandbox for arbitrary Python. Caller-supplied code is never accepted.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import resource
import re
import sys
from typing import Any

from lib.dataos.web_workspace import DataWorkspace, WorkspaceError, MAX_RESPONSE_BYTES

MAX_ROWS_PER_REF = 20000
MAX_TOTAL_ROWS = 80000
MAX_SCANNED_PER_REF = 500000


def _side_effect_guard(run_dir: Path) -> None:
    run_dir = run_dir.resolve()
    def within_run(value: Any) -> bool:
        if isinstance(value, int):
            # Existing descriptors are opened by the trusted runner before this hook.
            return True
        if not isinstance(value, (str, bytes, os.PathLike)):
            return False
        path = Path(os.fsdecode(value)).resolve()
        return path == run_dir or run_dir in path.parents

    def hook(event: str, args: tuple) -> None:
        if (event.startswith("socket.") or event.startswith("subprocess.")
                or event in {"os.system", "os.posix_spawn", "os.posix_spawnp", "os.exec", "pty.spawn"}):
            raise PermissionError("LAB_NETWORK_OR_SUBPROCESS_REFUSED")
        if event == "open":
            path, mode, flags = args
            if not isinstance(path, int):
                parts = Path(os.fsdecode(path)).parts
                if any(p == ".env" or p.startswith(".env.") or p in {".aws", ".ssh"} for p in parts):
                    raise PermissionError("LAB_PRIVATE_CONFIGURATION_REFUSED")
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
            if writing and not within_run(path):
                raise PermissionError("LAB_WRITE_OUTSIDE_RUN_REFUSED")
        if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.truncate"}:
            if not within_run(args[0]):
                raise PermissionError("LAB_MUTATION_OUTSIDE_RUN_REFUSED")
        if event in {"os.rename", "os.link", "os.symlink"}:
            if not within_run(args[0]) or not within_run(args[1]):
                raise PermissionError("LAB_MUTATION_OUTSIDE_RUN_REFUSED")
        if event in {"os.chdir", "os.fchdir"} and not within_run(args[0]):
            raise PermissionError("LAB_CWD_CHANGE_REFUSED")
    sys.addaudithook(hook)


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (45, 46))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))


def _materialize(workspace: DataWorkspace, execution: dict):
    import pandas as pd

    universe, sources, total = {}, [], 0
    columns = [execution["time_column"], *execution["column_map"].values()]
    for ref in execution["request"]["refs"]:
        offset, scanned, rows, source = 0, 0, [], None
        expected = execution["expected_versions"].get(ref)
        while offset is not None:
            page = workspace.read(
                ref=ref, columns=columns, time_column=execution["time_column"],
                start=execution.get("start"), end=execution.get("end"),
                offset=offset, limit=200, expected_version=expected,
            )
            source = page["source"]
            expected = source["file_version"]
            result = page["result"]
            rows.extend(result["rows"])
            scanned += result["scanned_rows"]
            if len(rows) > MAX_ROWS_PER_REF or total + len(rows) > MAX_TOTAL_ROWS:
                raise WorkspaceError("LAB_INPUT_TOO_LARGE_NARROW_DATE_RANGE")
            if scanned > MAX_SCANNED_PER_REF:
                raise WorkspaceError("LAB_SCAN_TOO_LARGE_USE_EXISTING_BATCH_OWNER")
            next_offset = result["next_offset"]
            if next_offset is not None and next_offset <= offset:
                raise WorkspaceError("INVALID_READER_CONTINUATION")
            offset = next_offset
        if not rows:
            raise WorkspaceError("LAB_SOURCE_HAS_NO_MATCHING_ROWS")
        frame = pd.DataFrame.from_records(rows)
        time_values = frame.pop(execution["time_column"])
        iso_date = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})?)?$")
        if any(not isinstance(value, str) or not iso_date.fullmatch(value) for value in time_values):
            raise WorkspaceError("LAB_TIME_COLUMN_REQUIRES_ISO_DATES")
        precision = {len(value) == 10 for value in time_values}
        awareness = {bool(re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value)) for value in time_values}
        if len(precision) != 1 or len(awareness) != 1:
            raise WorkspaceError("LAB_MIXED_TIME_ENCODING")
        try:
            index = pd.DatetimeIndex(pd.to_datetime(time_values, format="ISO8601", errors="raise"))
        except (ValueError, TypeError):
            raise WorkspaceError("LAB_INVALID_DATE_INDEX") from None
        if index.hasnans or index.has_duplicates or not index.is_monotonic_increasing:
            raise WorkspaceError("LAB_DATE_INDEX_MUST_BE_UNIQUE_AND_ASCENDING")
        if not pd.Index(index.date).is_unique:
            raise WorkspaceError("LAB_DAILY_BARS_REQUIRED")
        frame.index = index
        frame.index.name = execution["time_column"]
        frame = frame.rename(columns={v: k for k, v in execution["column_map"].items()})
        try:
            for column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="raise")
        except (ValueError, TypeError):
            raise WorkspaceError("LAB_NON_NUMERIC_OHLCV") from None
        total += len(frame)
        universe[ref] = frame
        sources.append({
            **source, "loaded_rows": len(frame), "scanned_rows": scanned,
            "first_stored_time": index[0].isoformat(), "last_stored_time": index[-1].isoformat(),
            "column_map": execution["column_map"], "time_column": execution["time_column"],
            "date_bounds": {"start": execution.get("start"), "end": execution.get("end")},
            "price_basis": "preserved as stored; no rebasing, filling or corporate-action repair",
        })
    return universe, sources


def execute_worker(workspace: DataWorkspace, run_dir: Path, execution: dict) -> int:
    run_dir = run_dir.resolve(strict=True)
    if Path.cwd().resolve() != run_dir or Path(os.environ.get("TMPDIR", "")).resolve() != run_dir:
        raise WorkspaceError("DEDICATED_LAB_RUN_DIRECTORY_REQUIRED")
    sys.dont_write_bytecode = True
    _limits()
    _side_effect_guard(run_dir)
    try:
        # Keep canonical diagnostic text separate from the one JSON result.
        with contextlib.redirect_stdout(sys.stderr):
            from lib.dataos.web_api import _lab_execution_request
            from lib.dataos.web_lab import execute
            execution = _lab_execution_request(execution)
            universe, sources = _materialize(workspace, execution)
            result = execute(universe, execution["request"])
        ledgers = []
        for path in run_dir.glob("_declbudget_*.jsonl"):
            if path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
                raise WorkspaceError("INVALID_TEMPORARY_LEDGER")
            data = path.read_bytes()
            ledgers.append({"file": path.name, "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                            "owner": "engine.trial_ledger.TrialLedger.with_declared_budget"})
        payload = {
            "schema_version": "mastermind.web_lab_result/v1",
            "implementation_revision": workspace.source_revision,
            "request": execution, "sources": sources, "trial": result,
            "temporary_ledger_artifacts": ledgers,
            "research_only": True,
            "production_ledger_written": False,
            "limitations": [
                "Selected-symbol history retains canonical survivorship bias.",
                "Stored date filters do not reconstruct point-in-time availability.",
                "horizon_bars measures forward-return IC; it is not a fixed holding period.",
                "Daily bars only; canonical statistics use 252 annualization periods.",
                "The existing Lab verdict is research evidence, not production admission.",
            ],
        }
        code = 0
    except Exception as exc:
        payload = {"schema_version": "mastermind.web_lab_result/v1",
                   "error": getattr(exc, "code", "LAB_EXECUTION_FAILED"),
                   "error_type": type(exc).__name__,
                   "research_only": True, "production_ledger_written": False}
        code = 1
    encoded = json.dumps(payload, allow_nan=False, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode()) > MAX_RESPONSE_BYTES - 8192:
        encoded = json.dumps({"error": "LAB_RESULT_TOO_LARGE", "research_only": True})
        code = 1
    with (run_dir / "result.json").open("x", encoding="utf-8") as out:
        out.write(encoded)
        out.write("\n")
    return code
