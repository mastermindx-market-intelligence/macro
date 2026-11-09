#!/usr/bin/env python3
"""Read one bounded JSON request from stdin and return one JSON result.

Examples:
  data_workspace.py --config /host/data-bindings.json < request.json
  data_workspace.py --config /host/data-bindings.json --capabilities

The configuration is host-owned, never a JSON request field. This CLI can run over
the existing Studio Direct process tool or behind an authenticated MCP transport.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.dont_write_bytecode = True

from lib.dataos.web_api import dispatch, MAX_REQUEST_BYTES
from lib.dataos.web_workspace import load_workspace_config, WorkspaceError


def _revision() -> str:
    if not (REPO_ROOT / ".git").exists():
        try:
            release_path = REPO_ROOT / "RELEASE.json"
            if release_path.stat().st_size > 65536:
                return "INVALID_RELEASE_MANIFEST"
            release = json.loads(release_path.read_text(encoding="utf-8"))
            commit = release.get("source_commit")
            if (release.get("schema_version") == "mastermind.data_workspace_release/v1"
                    and isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit)):
                return commit
        except (OSError, ValueError, TypeError):
            pass
        return "UNKNOWN_SOURCE_REVISION"
    try:
        result = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                                check=True, capture_output=True, text=True, timeout=3)
        revision = result.stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=normal",
             "--", "lib/dataos/web_workspace.py", "lib/dataos/web_readers.py",
             "lib/dataos/web_api.py", "lib/dataos/web_lab.py", "lib/dataos/web_lab_worker.py",
             "engine/lab.py", "scripts/data_workspace.py"],
            check=True, capture_output=True, text=True, timeout=3,
        ).stdout
        return revision + ("+working-tree-changes" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN_SOURCE_REVISION"


def _input() -> dict:
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES:
        raise WorkspaceError("REQUEST_TOO_LARGE")
    if not raw.strip():
        raise WorkspaceError("REQUEST_REQUIRED")
    try:
        return json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        raise WorkspaceError("INVALID_REQUEST_JSON") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Explicit host-owned binding JSON")
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--lab-worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        workspace = load_workspace_config(args.config, source_revision=_revision())
        if args.lab_worker is not None:
            from lib.dataos.web_lab_worker import execute_worker
            return execute_worker(workspace, args.lab_worker, _input())
        request = {"action": "capabilities"} if args.capabilities else _input()
        result = dispatch(workspace, request, config_path=args.config)
        print(json.dumps(result, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as exc:
        # Do not serialize arbitrary exception strings, OS paths, source values or tracebacks.
        code = getattr(exc, "code", None)
        if not isinstance(code, str):
            code = "INVALID_ARGUMENT_OR_HOST_CONFIGURATION" if isinstance(
                exc, (ValueError, KeyError, TypeError, FileNotFoundError)) else "DATA_WORKSPACE_FAILED"
        print(json.dumps({"schema_version": "mastermind.data_workspace/v1",
                          "error": code, "error_type": type(exc).__name__},
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
