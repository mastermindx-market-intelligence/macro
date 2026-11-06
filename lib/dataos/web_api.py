"""Narrow JSON dispatch shared by the web workflow and optional MCP transports.

Transport authorization and host configuration remain outside request arguments.
This adapter runs only catalog Lab recipes, never caller-supplied code or SQL.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid
from typing import Any

from lib.dataos.web_workspace import DataWorkspace, WorkspaceError, MAX_RESPONSE_BYTES

MAX_REQUEST_BYTES = 16384
MAX_LAB_WALL_SECONDS = 60


def _fields(request: dict, allowed: set[str], required: set[str] = frozenset()) -> dict:
    if set(request) - allowed or required - set(request):
        raise WorkspaceError("INVALID_REQUEST_FIELDS")
    return request


def _lab():
    # Catalog discovery stays optional for data-only installations.
    from lib.dataos import web_lab
    return web_lab


def validate_request(raw: Any) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("action"), str):
        raise WorkspaceError("INVALID_REQUEST")
    try:
        encoded = json.dumps(raw, allow_nan=False, separators=(",", ":")).encode()
    except (TypeError, ValueError, OverflowError) as exc:
        raise WorkspaceError("INVALID_REQUEST") from exc
    if len(encoded) > MAX_REQUEST_BYTES:
        raise WorkspaceError("REQUEST_TOO_LARGE")
    return raw


def _lab_execution_request(raw: dict) -> dict:
    _fields(raw, {"request", "time_column", "column_map", "start", "end", "expected_versions", "bar_frequency"},
            {"request", "time_column", "column_map", "bar_frequency"})
    if raw["bar_frequency"] != "daily":
        raise WorkspaceError("LAB_DAILY_BARS_REQUIRED")
    req = raw["request"]
    if not isinstance(req, dict):
        raise WorkspaceError("INVALID_LAB_REQUEST")
    _fields(req, {"signal_id", "refs", "horizon_bars", "cost_bps", "n_configs_searched"},
            {"signal_id", "refs", "n_configs_searched"})
    planned = _lab().plan(**req)
    if not planned["execution_ready"]:
        raise WorkspaceError("LAB_PLAN_NOT_EXECUTABLE")
    time_column, columns = raw["time_column"], raw["column_map"]
    if not isinstance(time_column, str) or not time_column or len(time_column) > 256:
        raise WorkspaceError("INVALID_TIME_COLUMN")
    if (not isinstance(columns, dict) or not columns or "close" not in columns
            or set(columns) - {"open", "high", "low", "close", "volume"}
            or any(not isinstance(v, str) or not v or len(v) > 256 for v in columns.values())
            or len(set(columns.values())) != len(columns)
            or time_column in columns.values()):
        raise WorkspaceError("INVALID_OHLCV_COLUMN_MAP")
    versions = raw.get("expected_versions", {})
    if (not isinstance(versions, dict) or set(versions) - set(req["refs"])
            or any(not isinstance(v, str) or not v.startswith("statv1:") or len(v) != 71
                   for v in versions.values())):
        raise WorkspaceError("INVALID_SOURCE_VERSIONS")
    for key in ("start", "end"):
        if raw.get(key) is not None and (not isinstance(raw[key], str) or len(raw[key]) > 64):
            raise WorkspaceError("INVALID_DATE_BOUND")
    return {**raw, "request": planned["request"], "expected_versions": versions}


def _host_test_root(config_path: Path) -> Path:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    binding = raw.get("test_workspace")
    if (not isinstance(binding, dict) or set(binding) != {"path", "required_mount"}
            or not isinstance(binding["path"], str)
            or not isinstance(binding["required_mount"], str)):
        raise WorkspaceError("TEST_WORKSPACE_NOT_BOUND")
    root, mount = Path(binding["path"]), Path(binding["required_mount"])
    if not root.is_absolute() or not mount.is_absolute() or root == mount or mount not in root.parents:
        raise WorkspaceError("INVALID_TEST_WORKSPACE_BINDING")
    if not os.path.ismount(mount):
        raise WorkspaceError("REQUIRED_VOLUME_NOT_MOUNTED")
    # Host configuration may create only this explicit external artifact directory.
    current = mount
    for part in root.relative_to(mount).parts:
        if part in {"", ".", ".."} or part.startswith("."):
            raise WorkspaceError("INVALID_TEST_WORKSPACE_BINDING")
        current = current / part
        if current.is_symlink():
            raise WorkspaceError("TEST_WORKSPACE_SYMLINK_REFUSED")
        current.mkdir(mode=0o700, exist_ok=True)
        if not current.is_dir():
            raise WorkspaceError("TEST_WORKSPACE_NOT_DIRECTORY")
    return root


def _write_json(path: Path, payload: dict) -> None:
    value = json.dumps(payload, separators=(",", ":"), allow_nan=False, ensure_ascii=False)
    if len(value.encode()) > MAX_RESPONSE_BYTES:
        raise WorkspaceError("RESULT_TOO_LARGE")
    with path.open("x", encoding="utf-8") as out:
        out.write(value)
        out.write("\n")


def run_lab(workspace: DataWorkspace, config_path: Path, args: dict) -> dict:
    """One bounded synchronous worker; the run folder is an artifact, not a queue."""
    execution = _lab_execution_request(args)
    # Resolve refs before creating any test artifacts.
    for ref in execution["request"]["refs"]:
        workspace._split_ref(ref)
    root = _host_test_root(config_path)
    run_id = "run-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    run_dir = root / run_id
    run_dir.mkdir(mode=0o700)
    request_sha = hashlib.sha256(json.dumps(execution, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    _write_json(run_dir / "request.json", {
        "schema_version": "mastermind.web_lab_request/v1", "run_id": run_id,
        "implementation_revision": workspace.source_revision,
        "request_sha256": request_sha, "execution": execution,
        "source_access": "read_only", "effects": "writes test artifacts and the canonical temporary declared-budget TrialLedger",
    })
    worker = Path(__file__).resolve().parents[2] / "scripts" / "data_workspace.py"
    env = {
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(run_dir), "TMP": str(run_dir), "TEMP": str(run_dir),
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    }
    outcome, code, process, failure = "FAILED", None, None, None
    try:
        with (run_dir / "worker.stdout").open("xb") as stdout, (run_dir / "worker.stderr").open("xb") as stderr:
            process = subprocess.Popen(
                [sys.executable, "-B", str(worker), "--config", str(config_path.resolve()),
                 "--lab-worker", str(run_dir)],
                stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, cwd=run_dir, env=env,
                start_new_session=True,
            )
            try:
                process.communicate(json.dumps(execution, allow_nan=False).encode(),
                                    timeout=MAX_LAB_WALL_SECONDS)
                code = process.returncode
                outcome = "SUCCEEDED" if code == 0 else "FAILED"
            except subprocess.TimeoutExpired:
                outcome = "TIMED_OUT"
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    process.communicate(timeout=5)
                    code = process.returncode
                except subprocess.TimeoutExpired:
                    outcome = "TERMINATION_UNCONFIRMED"
                    failure = "LAB_PROCESS_RECONCILIATION_REQUIRED"
    except OSError:
        outcome = "FAILED" if process is None or process.poll() is not None else "TERMINATION_UNCONFIRMED"
        failure = "LAB_PROCESS_LAUNCH_FAILED" if process is None else "LAB_PROCESS_RECONCILIATION_REQUIRED"
        code = process.returncode if process is not None else None
    status = {
        "schema_version": "mastermind.web_lab_run/v1", "run_id": run_id,
        "state": outcome, "exit_code": code, "request_sha256": request_sha,
        "process_id": process.pid if process is not None else None,
        "failure_code": failure,
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "execution": "synchronous_bounded_existing_lab_recipe",
        "wall_limit_seconds": MAX_LAB_WALL_SECONDS,
        "artifact_files": ["request.json", "status.json", "worker.stdout", "worker.stderr"],
        "ledger_owner": "engine.trial_ledger.TrialLedger.with_declared_budget",
        "production_ledger_written": False,
    }
    result_path = run_dir / "result.json"
    result = {"error": failure or "LAB_RESULT_UNAVAILABLE"}
    try:
        if result_path.is_file() and not result_path.is_symlink() and result_path.stat().st_size <= MAX_RESPONSE_BYTES:
            candidate = json.loads(result_path.read_text(encoding="utf-8"))
            if not isinstance(candidate, dict):
                raise ValueError("invalid result shape")
            result = candidate
            status["artifact_files"].append("result.json")
    except (OSError, ValueError):
        result = {"error": "LAB_RESULT_INVALID"}
    if "error" in result and status["state"] == "SUCCEEDED":
        status["state"] = "FAILED"
        status["failure_code"] = result["error"]
    _write_json(run_dir / "status.json", status)
    return workspace._result(action="lab_run", run=status, result=result,
        artifact_root_alias=next((r.alias for r in workspace.roots.values() if r.path == root), None),
        research_only=True,
        effects="test workspace artifacts and canonical temporary declared-budget ledger; no collector, deployment, or production ledger write")


def dispatch(workspace: DataWorkspace, request: dict, *, config_path: Path) -> dict:
    request = validate_request(request)
    action = request["action"]
    args = {k: v for k, v in request.items() if k != "action"}
    if action == "search":
        return workspace.search(**_fields(args, {"query", "limit"}))
    if action == "browse":
        return workspace.browse(**_fields(args,
            {"root", "path", "offset", "limit", "expected_directory_version"}, {"root"}))
    if action == "describe":
        return workspace.describe(**_fields(args, {"ref"}, {"ref"}))
    if action == "read" and "view" in args:
        return workspace.read_view(**_fields(args,
            {"ref", "columns", "time_column", "start", "end", "equals", "offset", "limit", "expected_version", "view"},
            {"ref", "view"}))
    if action == "read":
        return workspace.read(**_fields(args,
            {"ref", "columns", "time_column", "start", "end", "equals", "offset", "limit", "expected_version"},
            {"ref"}))
    if action == "tiingo_compare_statements":
        from lib.dataos.tiingo_workspace import compare_statements
        return compare_statements(workspace, **_fields(args,
            {"root", "vendor_symbol", "as_reported_capture", "restated_capture",
             "start", "end", "observed_before", "acknowledge_hindsight", "offset", "limit"},
            {"root", "vendor_symbol", "as_reported_capture", "restated_capture",
             "start", "end", "observed_before", "acknowledge_hindsight"}))
    if action == "history_dossier":
        from lib.dataos.web_history import history_dossier
        return history_dossier(workspace, **_fields(args,
            {"ref", "manifest_sha256", "date", "macro_ref", "macro_sha256", "reveal_outcomes",
             "filings_ref", "filings_sha256", "filings_offset",
             "transcripts_ref", "transcripts_version", "transcripts_offset"},
            {"ref", "manifest_sha256", "date"}))
    if action == "history_transcript":
        from lib.dataos.web_history import history_transcript
        return history_transcript(workspace, **_fields(args,
            {"ref", "expected_version", "row_position", "expected_metadata_sha256", "paragraph_offset",
             "character_offset", "max_chars", "expected_record_sha256"},
            {"ref", "expected_version", "row_position", "expected_metadata_sha256"}))
    if action == "lab_signals":
        return workspace._result(action=action, **_lab().list_signals(
            **_fields(args, {"query", "limit"})))
    if action == "lab_plan":
        return workspace._result(action=action, **_lab().plan(
            **_fields(args, {"signal_id", "refs", "horizon_bars", "cost_bps", "n_configs_searched"},
                      {"signal_id", "refs"})))
    if action == "lab_run":
        return run_lab(workspace, config_path, args)
    if action == "capabilities":
        _fields(args, set())
        return workspace._result(action=action,
            actions=["search", "browse", "describe", "read", "lab_signals", "lab_plan", "lab_run", "history_dossier", "history_transcript", "tiingo_compare_statements"],
            tiingo_statement_comparison={
                "root": "existing_host_bound_canonical_tiingo_archive_only",
                "capture_selection": "exact_day_and_receipt_id_or_source_sha256_per_dimension",
                "max_rows_per_capture": 20000, "max_keys_per_page": 50,
                "max_response_bytes": MAX_RESPONSE_BYTES,
                "mode": "RETROSPECTIVE_EXPLORATORY", "point_in_time_eligible": False,
                "network": False, "writes": False, "credentials": False,
            },
            supported_formats=["parquet", "csv", "json", "jsonl", "ndjson"],
            unsupported_formats="metadata only; use the existing owner decoder",
            max_response_bytes=MAX_RESPONSE_BYTES, max_rows_per_read=200,
            max_scan_rows_per_read=100000, max_request_bytes=MAX_REQUEST_BYTES,
            read_view={"modes": ["CURRENT"], "refused_modes": ["RECONSTRUCT", "REPLAY"],
                       "refusal_prefix": "VIEW_REFUSED_", "generation_token": "statv1",
                       "generation_basis": "statv1_file_version_not_a_producer_generation"},
            lab={"max_refs": 8, "max_rows_per_ref": 20000, "max_total_rows": 80000,
                 "wall_limit_seconds": MAX_LAB_WALL_SECONDS,
                 "bar_frequency": "daily", "canonical_annualization_periods": 252,
                 "execution": "canonical catalog recipes only; no arbitrary code or shell"},
            history={"source_access":"existing_descriptor_confined_roots",
                     "mode":"RETROSPECTIVE_EXPLORATORY","point_in_time_eligible":False,
                     "max_proxy_symbols":64,"max_macro_records_per_date":100,
                     "max_price_file_bytes":256*1024*1024,
                     "max_decoded_price_file_bytes":64*1024*1024,
                     "budget_is_peak_process_memory_limit":False,
                     "provenance":"compact per-source digests; full source detail in the retained manifest",
                     "required_evidence":"exact manifest digest; paired optional JSON macro reference and digest",
                     "filings":{"source_kind":"retained_item_202_filing_metadata",
                                "required_source_filename":"earnings_8k_dates.parquet",
                                "requires_exact_sha256":True,"max_records_per_date_page":50,
                                "max_source_bytes":16*1024*1024,"max_decoded_bytes":32*1024*1024,
                                "max_source_rows":250000,"intraday_publication_time_verified":False,
                                "identity":"canonical CIK/accession; ticker is an unqualified source label"},
                     "transcripts":{"required_source_filename":"stock_earning_call_transcripts.parquet",
                                    "requires_expected_file_version":True,"file_version_is_content_hash":False,
                                    "default_body_read":False,"date_page_records":50,"source_rows_max":500000,
                                    "date_basis":"stored_report_date_not_verified_publication_time",
                                    "body_action":"history_transcript","body_identity":"same_version_row_and_metadata_digest",
                                    "max_page_chars":12000,"max_page_fragment_json_bytes":48*1024,
                                    "speaker_roles_verified":False,"point_in_time_eligible":False},
                     "outcomes":"excluded unless explicitly revealed"},
            freshness="stored data clocks where available; filesystem mtime is not freshness",
            access="host bindings and the existing Studio account-scoped transport")
    raise WorkspaceError("UNKNOWN_ACTION")
