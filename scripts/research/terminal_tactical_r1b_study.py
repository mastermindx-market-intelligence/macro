#!/usr/bin/env python3
"""Run the frozen TTI R1-B v4 corrected-history study offline.

Admission is fail-closed and precedes every market-input read.  This consumer
uses existing D0/Radar owners; it opens no network/provider path and has no live
rank, alert, sizing, event-emission, options or trade authority.

The attempt ledger lives under a disclosed local path (default: passwd-database
home, not ``$HOME``).  One registered outcome per study id is enforced against
that ledger; the operator anchors receipts externally (for example the PR
carrier).  This runner does not claim stronger off-machine enforcement.

If a run dies after the outcome stage begins, inspect the attempt receipt:
``outcome_values_persisted`` stays ``null`` and a later run is refused with
``prior_attempt_unfinalized`` until the holding authority (Sol) authorises a
fresh study id.  A receipt that never left pre-input admission does not block.
A receipt with ``outcome_values_persisted: true`` blocks forever by design.

The registered test receipt must be produced at the reviewed commit with::

    pytest -o junit_suite_name=<code_sha> --junitxml=<file> \\
        tests/test_tactical_research.py tests/test_tactical_research_cli.py \\
        tests/test_tactical_r1b_pools.py tests/test_tactical_r1b_aggregate.py \\
        tests/test_tactical_r1b_run.py
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import platform
import pwd
import re
import socket
import statistics
import subprocess
import sys
import traceback
import xml.etree.ElementTree as ElementTree
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.entry_radar import tactical_exhaustion as te  # noqa: E402
from engine.session_digest import session_window_et  # noqa: E402
from lib.nyse_calendar import is_session  # noqa: E402
from scripts.research import terminal_tactical_r1_study as r1  # noqa: E402
from scripts.research import terminal_tactical_r1b_aggregate as agg  # noqa: E402
from scripts.research import terminal_tactical_r1b_pools as pools  # noqa: E402

CONFIG_PATH = ROOT / "research/species/tti_r1b/config_v4.json"
PREREG_PATH = ROOT / "research/species/TTI_R1B_V4_PREREG.md"
RECEIPT_PATH = ROOT / "research/species/tti_r1b/REGISTRATION_RECEIPT_V4.json"
LEDGER_PATH = ROOT / "data/trial_ledger.jsonl"
STUDY_ID = "tti-r1b-exhaustion-reclaim-v4"
PREREG_SHA256 = "a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3"
GRID_SHA256 = "151c0cb20af85537287413b4ecdeaf2ccad18232ed4eb0a20091cbd46cdb6b17"
R1B_ROWS_SHA256 = "8fc5a844886cfa2d69ec25f38fd6948b4a4556e01829bea76338e94570def281"
TRIAL_FAMILY = "entry_radar"
STUDY_ROWS = 60
UTC = timezone.utc
RULINGS_PATH = ROOT / "research/species/tti_r1b/ANALYSIS_RULINGS_V4.md"
RULINGS_SHA256 = "73e1713f19f0edfe886b414f0cf90b5f829b29cf4662d0993c61d351c4230c84"
TERMINAL_PINNED_FILES = (
    "ingest/intraday_qualification.py",
    "terminal/lib/usEquitySessionProjection.json",
)
RESULT_PATH = ROOT / "research/species/tti_r1b/RESULT_V4.json"
REPORT_PATH = ROOT / "research/species/TTI_R1B_V4_REPORT.md"
D0_MANIFEST_SHA256 = "59c50ed405bd76c083a1d2beb20cf25edd6f4bd892c3e55fd38d21a66bef642b"
RESULT_SCHEMA = "mastermind.tti.r1b.result.v5"
ATTEMPT_ROOT = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".mastermind" / "tti_r1b" / STUDY_ID
ATTEMPT_SCHEMA = "mastermind.tti.r1b.attempt.v4"
CODE_FILES = (
    "scripts/research/terminal_tactical_r1b_study.py",
    "scripts/research/terminal_tactical_r1b_pools.py",
    "scripts/research/terminal_tactical_r1b_aggregate.py",
    "scripts/research/terminal_tactical_r1_study.py",
    "engine/entry_radar/tactical_exhaustion.py",
    "engine/entry_radar/tactical_research.py",
    "engine/session_digest.py",
    "lib/nyse_calendar.py",
)
STAGES = ("arguments", "admission", "inputs", "construction", "pools", "preflight",
          "outcomes", "aggregate", "persist")
PRE_INPUT_STAGES = ("arguments", "admission")
OUTCOME_STAGES = ("outcomes", "aggregate", "persist")
D0_ROW_CAP = 60000
PREFIX_BREAKING = ("off_grid_or_unordered_bar", "missing_bar", "duplicate_bar", "invalid_ohlcv")
REQUIRED_TEST_MODULES = (
    "tests.test_tactical_research",
    "tests.test_tactical_research_cli",
    "tests.test_tactical_r1b_pools",
    "tests.test_tactical_r1b_aggregate",
    "tests.test_tactical_r1b_run",
)
TEST_FILES = tuple(m.replace(".", "/") + ".py" for m in REQUIRED_TEST_MODULES)
TEST_PINNED_FILES = TEST_FILES + ("tests/conftest.py", "tests/__init__.py")
_COLLECT_LINE = re.compile(r"^(tests/\S+?\.py)::(.+)$")
_REFUSAL_STDERR = re.compile(r"^(code_identity_[a-z_]+|terminal_dependency_[a-z_]+)(:|$)")
_COLLECT_ENV_SKIP = frozenset({
    "POLYGON_API_KEY", "PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONPATH",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
})
# One of this runner's own refusal codes: lower-case words joined by underscores, then an
# optional ":SYMBOL".  A bare number or free text never matches.
_REFUSAL_CODE = re.compile(r"[a-z][a-z0-9]*(_[a-z0-9]+)+(:[A-Z][A-Z0-9.]{0,9})?")
_OHLCV = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
_DESCRIPTIVE = ("raw_return", "net_return", "benchmark_return", "beta_residual",
                "net_beta_residual", "mfe", "mae", "candidate_delay_atr",
                "episode_delay_atr", "remaining_to_prior_close_atr")
_STATUS_FIELDS = ("touch", "lod_status", "candidate_lod_status", "candidate_lod_survives",
                  "episode_lod_status", "episode_lod_survives")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_env() -> dict[str, str]:
    return {**os.environ, "GIT_NO_LAZY_FETCH": "1"}


def _git_cmd(repo: Path, *args: str) -> list[str]:
    return ["git", "--no-replace-objects", "-C", str(repo), *args]


def _object_local(repo: Path, sha: str) -> bool:
    """Return whether ``sha`` is present locally without promisor lazy-fetch."""
    proc = subprocess.run(
        _git_cmd(repo, "rev-list", "--missing=print", "--objects", "--no-walk", sha),
        capture_output=True,
        env=_git_env(),
    )
    if proc.returncode != 0:
        return False
    tokens = proc.stdout.decode().split()
    if not tokens:
        return False
    if tokens[0].startswith("?"):
        return False
    return True


def _blob_oid_at_tree(repo: Path, tree_sha: str, path: str) -> str:
    """Resolve a path's blob oid at ``tree_sha`` using only local tree objects."""
    proc = subprocess.run(
        _git_cmd(repo, "ls-tree", tree_sha, "--", path),
        capture_output=True,
        env=_git_env(),
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise ValueError(f"code_identity_commit_unreadable:{path}")
    fields = proc.stdout.decode().strip().split()
    if len(fields) < 3 or fields[1] != "blob":
        raise ValueError(f"code_identity_commit_unreadable:{path}")
    return fields[2]


def _git_show_blob(repo: Path, blob_oid: str) -> bytes:
    """Read blob bytes for a locally-present object oid."""
    proc = subprocess.run(
        _git_cmd(repo, "cat-file", "blob", blob_oid),
        capture_output=True,
        env=_git_env(),
    )
    if proc.returncode != 0:
        raise ValueError(f"code_identity_commit_unreadable:{blob_oid[:12]}")
    return proc.stdout


def _passwd_home_attempt_root() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir) / ".mastermind" / "tti_r1b" / STUDY_ID


def attempt_root(args: argparse.Namespace | Any) -> tuple[Path, str]:
    """Resolved attempt ledger root and how it was chosen."""
    cli = getattr(args, "attempt_root", None)
    if cli is not None:
        return Path(cli).resolve(), "cli"
    root = ATTEMPT_ROOT.resolve()
    if root != _passwd_home_attempt_root().resolve():
        return root, "override"
    return root, "passwd_home"


def code_digest(code_files: Mapping[str, str], pinned_test_blobs: Mapping[str, str]) -> str:
    lines: list[str] = []
    for path in sorted(set(code_files) | set(pinned_test_blobs)):
        blob = code_files.get(path) if path in code_files else pinned_test_blobs[path]
        lines.append(f"{path}\0{blob}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def _pinned_test_blob(name: str, code_sha: str) -> str:
    """Hash a pinned test path at ``code_sha``, refusing unknown or remote-only blobs."""
    path = ROOT / name
    if path.is_file():
        return _sha(path)
    if not _object_local(ROOT, code_sha):
        raise ValueError(f"code_identity_object_unknown:{code_sha[:12]}")
    blob_oid = _blob_oid_at_tree(ROOT, code_sha, name)
    if not _object_local(ROOT, blob_oid):
        raise ValueError(f"code_identity_blob_not_local:{code_sha[:12]}:{name}")
    return hashlib.sha256(_git_show_blob(ROOT, blob_oid)).hexdigest()


def _pinned_test_blobs_on_disk(code_sha: str) -> dict[str, str]:
    return {name: _pinned_test_blob(name, code_sha) for name in TEST_PINNED_FILES}


def _pytest_config_path() -> Path | None:
    ini = ROOT / "pytest.ini"
    if ini.is_file():
        return ini
    toml = ROOT / "pyproject.toml"
    if toml.is_file():
        return toml
    return None


def _terminal_dependency_probe(terminal_root: Path, sha: str) -> dict[str, Any]:
    """Probe Terminal worktree cleanliness and pinned blobs at a local commit."""
    status = subprocess.run(
        _git_cmd(terminal_root, "status", "--porcelain"),
        capture_output=True,
        env=_git_env(),
    )
    if status.returncode != 0:
        raise ValueError("terminal_dependency_probe_failed:status")
    porcelain = status.stdout.decode()
    toplevel_proc = subprocess.run(
        _git_cmd(terminal_root, "rev-parse", "--show-toplevel"),
        capture_output=True,
        env=_git_env(),
    )
    if toplevel_proc.returncode != 0:
        raise ValueError("terminal_dependency_probe_failed:toplevel")
    toplevel = toplevel_proc.stdout.decode().strip()
    if not _object_local(terminal_root, sha):
        raise ValueError("terminal_dependency_probe_failed:commit")
    blobs: dict[str, str] = {}
    for path in TERMINAL_PINNED_FILES:
        try:
            blob_oid = _blob_oid_at_tree(terminal_root, sha, path)
        except ValueError:
            raise ValueError(f"terminal_dependency_probe_failed:{path}") from None
        if not _object_local(terminal_root, blob_oid):
            raise ValueError(f"terminal_dependency_probe_failed:{path}")
        blobs[path] = hashlib.sha256(_git_show_blob(terminal_root, blob_oid)).hexdigest()
    return {"porcelain": porcelain, "toplevel": toplevel, "blobs": blobs}


def _loaded_root_modules() -> dict[str, str]:
    root = ROOT.resolve()
    collected: dict[str, str] = {}
    for module in list(sys.modules.values()):
        file = getattr(module, "__file__", None)
        if file is None:
            continue
        path = Path(file).resolve()
        if not path.is_relative_to(root):
            continue
        name = path.relative_to(root).as_posix()
        if name.startswith("tests/") or name.endswith("conftest.py"):
            continue
        if "/site-packages/" in str(path) or "/.venv/" in str(path):
            continue
        collected[name] = _sha(ROOT / name)
    return dict(sorted(collected.items()))


def _reviewed_blob_sha256(code_sha: str, name: str) -> str:
    """Return the sha256 of ``name`` as recorded at local commit ``code_sha``."""
    if not _object_local(ROOT, code_sha):
        raise ValueError(f"code_identity_object_unknown:{code_sha[:12]}")
    blob_oid = _blob_oid_at_tree(ROOT, code_sha, name)
    if not _object_local(ROOT, blob_oid):
        raise ValueError(f"code_identity_blob_not_local:{code_sha[:12]}:{name}")
    return hashlib.sha256(_git_show_blob(ROOT, blob_oid)).hexdigest()


def _grid_cells(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"study_id": cfg["study_id"], "selector": selector,
         "horizon": horizon, "round_trip_cost_bps": int(cost)}
        for selector in cfg["selectors"]
        for horizon in cfg["horizons"]
        for cost in cfg["round_trip_cost_bps"]
    ]


def _grid_sha256(cfg: Mapping[str, Any]) -> str:
    parts = sorted(
        json.dumps(x, sort_keys=True, separators=(",", ":")) for x in _grid_cells(cfg)
    )
    return hashlib.sha256(("\n".join(parts) + "\n").encode("utf-8")).hexdigest()


def _pairs_flagging_duplicates(flag: list[bool]) -> Callable[[list[tuple[str, Any]]], dict[str, Any]]:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                flag.append(True)
            out[key] = value
        return out
    return hook


def registered_rows(raw_ledger: bytes) -> list[bytes]:
    study_id_b = STUDY_ID.encode("utf-8")
    selected: list[bytes] = []
    for chunk in raw_ledger.split(b"\n"):
        if not chunk.strip():
            continue
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("registered_row_unparseable") from None
        duplicated: list[bool] = []
        try:
            row = json.loads(text, object_pairs_hook=_pairs_flagging_duplicates(duplicated))
        except json.JSONDecodeError:
            if study_id_b in chunk:
                raise ValueError("registered_row_unparseable") from None
            continue
        if duplicated and study_id_b in chunk:
            raise ValueError("registered_row_duplicate_key")
        if not isinstance(row, dict):
            if study_id_b in chunk:
                raise ValueError("registered_row_unparseable")
            continue
        value = row.get("config")
        if isinstance(value, dict) and value.get("study_id") == STUDY_ID:
            selected.append(chunk)
    return selected


def _registered_rows_sha256(rows: Sequence[bytes]) -> str:
    return hashlib.sha256(b"".join(line + b"\n" for line in rows)).hexdigest()


def verify_admission(
    *, config_path: Path = CONFIG_PATH, prereg_path: Path = PREREG_PATH,
    receipt_path: Path = RECEIPT_PATH, ledger_path: Path = LEDGER_PATH,
    before_input: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Verify frozen scientific identity and 60-cell registration before inputs."""
    receipt = json.loads(receipt_path.read_text())
    config_bytes = config_path.read_bytes()
    cfg = json.loads(config_bytes)
    if cfg.get("study_id") != STUDY_ID:
        raise ValueError("study_id_mismatch")
    config_sha = hashlib.sha256(config_bytes).hexdigest()
    prereg_sha = _sha(prereg_path)
    if config_sha != receipt.get("config_sha256") or config_sha != te.CONFIG_SHA256:
        raise ValueError("config_sha256_mismatch")
    if prereg_sha != PREREG_SHA256 or prereg_sha != receipt.get("prereg_sha256"):
        raise ValueError("prereg_sha256_mismatch")
    grid_sha = _grid_sha256(cfg)
    if grid_sha != GRID_SHA256 or receipt.get("grid_sha256") != GRID_SHA256:
        raise ValueError("grid_sha256_mismatch")
    if receipt.get("study_id") != STUDY_ID or receipt.get("family") != cfg.get("trial_family"):
        raise ValueError("registration_receipt_identity_mismatch")
    if cfg.get("trial_family") != TRIAL_FAMILY:
        raise ValueError("registration_receipt_identity_mismatch")
    if receipt.get("prefix_preserved") is not True:
        raise ValueError("registration_prefix_not_preserved")
    if receipt.get("market_outcomes_opened_before_registration") is not False:
        raise ValueError("registration_precedes_outcomes_not_proven")
    wanted = {json.dumps(x, sort_keys=True, separators=(",", ":")) for x in _grid_cells(cfg)}
    if len(wanted) != int(cfg.get("full_grid_size", -1)) or len(wanted) != STUDY_ROWS:
        raise ValueError("frozen_grid_size_mismatch")
    raw_ledger = ledger_path.read_bytes()
    ledger_lines = sum(1 for chunk in raw_ledger.split(b"\n") if chunk.strip())
    rows = registered_rows(raw_ledger)
    if len(rows) != STUDY_ROWS:
        raise ValueError(f"registered_grid_row_count_mismatch:{len(rows)}/{STUDY_ROWS}")
    found: set[str] = set()
    for line in rows:
        row = json.loads(line)
        if row.get("family") != TRIAL_FAMILY:
            raise ValueError("registered_row_family_mismatch")
        value = row.get("config")
        if isinstance(value, dict):
            found.add(json.dumps(value, sort_keys=True, separators=(",", ":")))
    if found != wanted:
        raise ValueError(f"registered_grid_mismatch:{len(found)}/{len(wanted)}")
    registered_rows_sha256 = _registered_rows_sha256(rows)
    if registered_rows_sha256 != R1B_ROWS_SHA256:
        raise ValueError("registered_rows_sha256_mismatch")
    if int(receipt.get("study_rows", -1)) != len(wanted):
        raise ValueError("registration_receipt_cell_count_mismatch")
    chunks = [chunk for chunk in raw_ledger.split(b"\n") if chunk.strip()]
    try:
        prefix_lines = int(receipt.get("ledger_lines_after")) - STUDY_ROWS
    except (TypeError, ValueError):
        prefix_lines = -1
    prefix_matches = prefix_lines >= 0 and hashlib.sha256(
        b"".join(chunk + b"\n" for chunk in chunks[:prefix_lines])
    ).hexdigest() == receipt.get("ledger_prefix_sha256")
    if before_input is not None:
        before_input()
    return {
        "study_id": STUDY_ID,
        "ledger_prefix_matches_receipt": bool(prefix_matches),
        "study_cells": len(wanted),
        "registration_commit": receipt.get("registration_commit"),
        "config_sha256": config_sha,
        "prereg_sha256": prereg_sha,
        "grid_sha256": grid_sha,
        "registered_rows_sha256": registered_rows_sha256,
        "ledger_sha256": hashlib.sha256(raw_ledger).hexdigest(),
        "ledger_lines": ledger_lines,
        "market_outcomes_opened_before_registration": False,
        "market_data_read": False,
        "outcomes_computed": False,
    }


def qqq_open_to_decision_sign(
    frame: pd.DataFrame, decision_at: pd.Timestamp | datetime,
    *, expected_start: pd.Timestamp | datetime | None = None,
) -> int | None:
    """Candidate-time QQQ sign from an exact positive-volume five-minute prefix."""
    if not isinstance(frame, pd.DataFrame) or any(c not in frame.columns for c in
            ("open", "high", "low", "close", "volume")):
        return None
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None or frame.index.hasnans:
        return None
    decision = pd.Timestamp(decision_at)
    if decision.tzinfo is None:
        return None
    start = pd.Timestamp(expected_start) if expected_start is not None else (frame.index[0] if len(frame) else None)
    if start is None or start.tzinfo is None:
        return None
    frame_tz = frame.index.tz
    decision = decision.tz_convert(frame_tz)
    start = start.tz_convert(frame_tz)
    if decision <= start:
        return None
    expected = list(pd.date_range(start, decision - pd.Timedelta(minutes=5), freq="5min"))
    rows = frame[(frame.index >= start) & (frame.index < decision)]
    if len(rows) != len(expected) or list(rows.index) != expected or rows.index.has_duplicates:
        return None
    values: list[tuple[float, float]] = []
    for _, row in rows.iterrows():
        raw = [row[c] for c in ("open", "high", "low", "close", "volume")]
        try:
            o, h, low, c, v = map(float, raw)
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(x) for x in (o, h, low, c, v)) or min(o, h, low, c) <= 0 or v <= 0:
            return None
        if not low <= min(o, c) <= max(o, c) <= h:
            return None
        values.append((o, c))
    if not values:
        return None
    change = values[-1][1] - values[0][0]
    return 1 if change > 0 else -1 if change < 0 else 0



def construct_one_day(
    symbol: str, session: date, stock_frame: pd.DataFrame,
    benchmark_frame: pd.DataFrame, stock_daily: pd.DataFrame,
    benchmark_daily: pd.DataFrame, *, config_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Compose frozen v4 normalization + construction for one symbol/session."""
    frozen = CONFIG_PATH.read_bytes() if config_bytes is None else config_bytes
    normalization = te.build_prior_normalization(
        stock_daily, benchmark_daily, session=session, config_bytes=frozen)
    empty = {"normalization": normalization, "construction": None,
             "events": [], "controls": [], "anchors": {}}
    if normalization.get("availability") != "AVAILABLE":
        return empty
    prior_text = normalization.get("prior_session")
    if not isinstance(prior_text, str):
        return empty
    start, close = session_window_et(session)
    construction = te.construct_session(
        stock_frame, symbol=symbol, session=session,
        prior_session=date.fromisoformat(prior_text),
        prior_close=float(normalization["prior_close"]),
        prior_atr=float(normalization["prior_atr"]), asof=close,
        config_bytes=frozen, price_basis="adjusted")
    anchors = {str(row["anchor_id"]): dict(row)
               for row in construction.get("anchors", [])
               if isinstance(row, dict) and isinstance(row.get("anchor_id"), str)}
    events: list[dict[str, Any]] = []
    for raw in construction.get("events", []):
        event = dict(raw)
        candidate_at = pd.Timestamp(event["candidate_at"])
        sign = qqq_open_to_decision_sign(
            benchmark_frame, candidate_at, expected_start=start)
        event.update(symbol=symbol, session=session.isoformat(),
                     qqq_open_to_decision_sign=sign,
                     beta=normalization.get("beta") if normalization.get("beta_available") else None,
                     market_outcomes_computed=False)
        events.append(event)
    controls: list[dict[str, Any]] = []
    for raw in construction.get("control_census", []):
        control = dict(raw)
        candidate_at = pd.Timestamp(control["candidate_at"])
        control["qqq_open_to_decision_sign"] = qqq_open_to_decision_sign(
            benchmark_frame, candidate_at, expected_start=start)
        controls.append(control)
    return {"normalization": normalization, "construction": construction,
            "events": events, "controls": controls, "anchors": anchors}


def measure_event_grid(
    event: Mapping[str, Any], stock_frame: pd.DataFrame,
    benchmark_frame: pd.DataFrame, *, session: date,
    config_bytes: bytes | None = None,
) -> list[dict[str, Any]]:
    """Measure all 4×3 registered v4 cells for one already-fired event."""
    frozen = CONFIG_PATH.read_bytes() if config_bytes is None else config_bytes
    cfg = json.loads(frozen)
    rows: list[dict[str, Any]] = []
    beta = event.get("beta")
    beta_value = float(beta) if isinstance(beta, (int, float)) and not isinstance(beta, bool) and math.isfinite(float(beta)) else None
    for horizon in cfg["horizons"]:
        for cost in cfg["round_trip_cost_bps"]:
            measured = te.measure_event_outcome(
                stock_frame, benchmark_frame, event=dict(event), session=session,
                horizon=str(horizon), beta=beta_value, cost_bps=int(cost),
                config_bytes=frozen)
            row = dict(measured)
            row.update(symbol=event.get("symbol"), date=session.isoformat(),
                       qqq_open_to_decision_sign=event.get("qqq_open_to_decision_sign"))
            rows.append(row)
    return rows


# --------------------------------------------------------------------------- registered run
# Everything below implements the single registered run (analysis rulings 17 and 19-40).
# Order is the contract: admission -> inputs -> construction -> pools written and hashed
# -> preflight -> outcomes (in memory) -> aggregate -> one persist.


@contextlib.contextmanager
def no_network() -> Iterator[None]:
    """Refuse every socket path while the run is in progress (ruling 22)."""
    def refused(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("network_path_refused")

    class _RefusedSocket(socket.socket):
        """Still a socket class (isinstance/subclassing keep working); it can never be opened."""
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("network_path_refused")

    saved = (socket.socket, socket.create_connection, socket.getaddrinfo)
    socket.socket = _RefusedSocket  # type: ignore[misc]
    socket.create_connection = refused  # type: ignore[assignment]
    socket.getaddrinfo = refused  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket, socket.create_connection, socket.getaddrinfo = saved  # type: ignore[misc]


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _jsonl(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(_canonical(row) for row in rows)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _collected_test_ids(files: Sequence[str]) -> set[str]:
    env = {k: v for k, v in os.environ.items() if k not in _COLLECT_ENV_SKIP}
    cmd: list[str] = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--collect-only", "-q",
                      f"--rootdir={ROOT}"]
    config = _pytest_config_path()
    if config is not None:
        cmd.extend(["-c", str(config)])
    cmd.extend(files)
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        env=env,
    )
    if proc.returncode != 0:
        raise ValueError("test_collection_failed")
    collected: set[str] = set()
    for line in proc.stdout.decode().splitlines():
        match = _COLLECT_LINE.match(line.strip())
        if not match:
            continue
        path, rest = match.group(1), match.group(2)
        base = path[:-3].replace("/", ".")
        parts = rest.split("::")
        if len(parts) == 1:
            classname, name = base, parts[0]
        else:
            classname = base + "." + ".".join(parts[:-1])
            name = parts[-1]
        collected.add(f"{classname}::{name}")
    return collected


def junit_receipt(junit: Path, code_sha: str) -> dict[str, Any]:
    """JUnit receipt for every collected case; refuse anything but all-passed.

    The suite ``name`` is an operator-set label (conventionally the reviewed commit);
    trust comes from scrubbed collection, pinned conftest/init, and case-set equality.
    """
    raw = junit.read_bytes()
    root = ElementTree.fromstring(raw)
    suites = [el for el in root.iter("testsuite") if el.tag == "testsuite"]
    suite_names = [el.get("name") for el in suites]
    if not suite_names or any(name != code_sha for name in suite_names):
        raise ValueError("test_receipt_not_bound_to_head")
    cases: list[tuple[str, str]] = []
    for case in root.iter("testcase"):
        outcome = "passed"
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                outcome = child.tag
        cases.append((f'{case.get("classname")}::{case.get("name")}', outcome))
    if not cases or any(outcome != "passed" for _, outcome in cases):
        raise ValueError("test_receipt_not_clean")
    modules = sorted({name.split("::")[0] for name, _ in cases})
    for required in REQUIRED_TEST_MODULES:
        if not any(m == required or m.startswith(required + ".") for m in modules):
            raise ValueError("test_receipt_missing_suite")
    return {"sha256": _digest(raw), "tests": len(cases), "all_passed": True,
            "modules": modules, "cases": sorted(name for name, _ in cases)}


def _admission_input_pins(manifest: Path, terminal_root: Path,
                          cfg: Mapping[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Manifest and Terminal pins before any licensed bar is read (pre-input admission)."""
    manifest_sha = _sha(manifest)
    if manifest_sha != D0_MANIFEST_SHA256:
        raise ValueError("input_manifest_sha256_mismatch")
    head = r1._git_head(terminal_root)
    if head != cfg["terminal_dependency_sha"]:
        raise ValueError("terminal_dependency_head_mismatch")
    probe = _terminal_dependency_probe(terminal_root, cfg["terminal_dependency_sha"])
    if probe["porcelain"].strip():
        raise ValueError("terminal_dependency_dirty")
    if Path(probe["toplevel"]).resolve() != Path(terminal_root).resolve():
        raise ValueError("terminal_dependency_not_a_root")
    for path in TERMINAL_PINNED_FILES:
        if _sha(terminal_root / path) != probe["blobs"][path]:
            raise ValueError(f"terminal_dependency_blob_mismatch:{path}")
    return manifest_sha, head, probe


def load_inputs(input_dir: Path, manifest: Path, terminal_root: Path,
                cfg: Mapping[str, Any], *, pins: tuple[str, str, dict[str, Any]] | None = None
                ) -> dict[str, Any]:
    """Read the pinned D0 capture through the accepted R1-A loader.  Local files only."""
    if pins is None:
        manifest_sha, head, probe = _admission_input_pins(manifest, terminal_root, cfg)
    else:
        manifest_sha, head, probe = pins
    d0 = r1._load_terminal_module(terminal_root)
    calendar = d0.CalendarProjection.load(terminal_root / "terminal/lib/usEquitySessionProjection.json")
    rows = r1._manifest_map(manifest)
    frames: dict[str, pd.DataFrame] = {}
    receipts: dict[str, Any] = {}
    for symbol in [*cfg["symbols"], cfg["benchmark"]]:
        meta = rows.get((symbol, "5m"))
        if not meta or meta.get("status") not in {"captured", "previously_captured"} or not meta.get("sha256"):
            raise ValueError(f"manifest_5m_missing:{symbol}")
        path = input_dir / f"{symbol}.5m.json"
        qualification = d0.qualify_store(path, symbol, "5m", calendar, cfg["start"], cfg["end"],
                                         None, "corrected_history")
        errors = qualification.get("errors") or {}
        if (qualification.get("status") in {"missing", "unreadable", "malformed", "empty"}
                or set(errors) - {"invalid_bar"}):
            raise ValueError(f"input_qualification_failed:{symbol}")
        frames[symbol] = r1._load_symbol(path, symbol, meta["sha256"], d0)
        receipts[symbol] = {
            "sha256": meta["sha256"], "rows": int(len(frames[symbol])),
            "manifest_rows": meta.get("rows"), "manifest_status": meta.get("status"),
            "whole_file_diagnostics": {str(k): v for k, v in sorted(errors.items())},
        }
    return {
        "frames": frames, "receipts": receipts, "calendar": calendar,
        "manifest_sha256": manifest_sha,
        "terminal": {
            "head": head,
            "qualification_module_sha256": _sha(terminal_root / "ingest/intraday_qualification.py"),
            "calendar_sha256": calendar.sha256,
            "pinned_blobs": probe["blobs"],
            "worktree_clean": True,
            "toplevel": probe["toplevel"],
        },
    }


def scheduled_sessions(calendar: Any, cfg: Mapping[str, Any]) -> list[str]:
    """Scheduled sessions of the frozen window; the two calendars must agree on every date."""
    sessions = r1._scheduled_days(calendar, cfg["start"], cfg["end"])
    first = date.fromisoformat(cfg["start"])
    last = date.fromisoformat(cfg["end"])
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        window = calendar.window(day.isoformat())
        if is_session(day) != (window is not None):
            raise ValueError("session_calendar_disagreement")
        if window is None:
            continue
        start, close = session_window_et(day)
        if (start.hour * 60 + start.minute, close.hour * 60 + close.minute) != tuple(window):
            raise ValueError("session_calendar_disagreement")
    return sessions


def _minutes_by_day(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    return {str(day): group["minute"].to_numpy(dtype="int64")
            for day, group in frame.groupby("date", sort=False)}


def session_frame(frame: pd.DataFrame, minutes_by_day: Mapping[str, np.ndarray], day: str,
                  window: tuple[int, int]) -> pd.DataFrame:
    """Every loaded bar whose true start lies in the session's regular window, in file order.

    Nothing is sorted, filled or de-duplicated.  The true-clock slice must be exactly the
    rows the capture's wall clock places in that session, or the run refuses.
    """
    start, close = session_window_et(date.fromisoformat(day))
    index = frame.index.to_numpy(dtype="int64")
    left = int(np.searchsorted(index, int(start.timestamp()), side="left"))
    right = int(np.searchsorted(index, int(close.timestamp()), side="left"))
    rows = frame.iloc[left:right]
    wall = minutes_by_day.get(day)
    wall_count = 0 if wall is None else int(((wall >= window[0]) & (wall < window[1])).sum())
    inside = (rows["date"] == day) & (rows["minute"] >= window[0]) & (rows["minute"] < window[1])
    if wall_count != len(rows) or not bool(inside.all()):
        raise ValueError("session_clock_disagreement")
    out = rows.loc[:, list(_OHLCV)].rename(columns=_OHLCV)
    out.index = pd.to_datetime(index[left:right], unit="s", utc=True).tz_convert(start.tzinfo)
    return out


def daily_table(frame: pd.DataFrame, sessions: Sequence[str], calendar: Any) -> tuple[pd.DataFrame, list[str]]:
    """One (high, low, close) row per COMPLETE regular session; an incomplete session has no row."""
    complete: list[str] = []
    values: list[tuple[float, float, float]] = []
    for day in sessions:
        regular = r1._regular(frame, day, calendar)
        if regular is None:
            continue
        complete.append(day)
        values.append((float(regular["h"].max()), float(regular["l"].min()),
                       float(regular["c"].iloc[-1])))
    table = pd.DataFrame(values, columns=["high", "low", "close"],
                         index=pd.DatetimeIndex(pd.to_datetime(complete)))
    return table, complete


def build_days(frames: Mapping[str, pd.DataFrame], sessions: Sequence[str], calendar: Any,
               cfg: Mapping[str, Any], *, config_bytes: bytes
               ) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, list[str]]]:
    """Frozen normalization + construction for every symbol and scheduled session."""
    benchmark = cfg["benchmark"]
    minutes = {symbol: _minutes_by_day(frame) for symbol, frame in frames.items()}
    daily: dict[str, pd.DataFrame] = {}
    complete: dict[str, list[str]] = {}
    for symbol, frame in frames.items():
        daily[symbol], complete[symbol] = daily_table(frame, sessions, calendar)
    days: dict[tuple[str, str], dict[str, Any]] = {}
    for day in sessions:
        window = calendar.window(day)
        bench = session_frame(frames[benchmark], minutes[benchmark], day, window)
        for symbol in cfg["symbols"]:
            stock = session_frame(frames[symbol], minutes[symbol], day, window)
            built = construct_one_day(symbol, date.fromisoformat(day), stock, bench,
                                      daily[symbol], daily[benchmark], config_bytes=config_bytes)
            built["stock_frame"] = stock
            built["benchmark_frame"] = bench
            days[(symbol, day)] = built
    return days, complete


def refuse_outcome_flags(events: Sequence[Mapping[str, Any]], census: Sequence[Mapping[str, Any]],
                         days: Mapping[tuple[str, str], Mapping[str, Any]]) -> None:
    """Every constructed row must itself say that no outcome or future label went into it."""
    if any(row.get("future_family_labels_used") is not False for row in census):
        raise ValueError("census_future_label_flag")
    if any(event.get("market_outcomes_computed") is not False for event in events):
        raise ValueError("event_outcome_flag")
    for built in days.values():
        if built["normalization"].get("market_outcomes_computed") is not False:
            raise ValueError("normalization_outcome_flag")
        if (built["construction"] is not None
                and built["construction"].get("market_outcomes_computed") is not False):
            raise ValueError("construction_outcome_flag")


def refuse_pool_flags(built_pools: Sequence[Mapping[str, Any]]) -> None:
    """Every pool must say that it used no outcome and no fallback."""
    if any(pool.get("market_outcomes_computed") is not False or pool.get("fallback_used") is not False
           for pool in built_pools):
        raise ValueError("pool_outcome_flag")


def _tally(values: Iterable[Any]) -> dict[str, int]:
    return {str(k): int(v) for k, v in sorted(Counter(str(v) for v in values).items())}


def coverage_report(days: Mapping[tuple[str, str], Mapping[str, Any]],
                    frames: Mapping[str, pd.DataFrame], receipts: Mapping[str, Any],
                    sessions: Sequence[str], complete: Mapping[str, Sequence[str]],
                    calendar: Any, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Coverage, exclusions and construction counts.  Built from inputs and candidate-time facts only."""
    shortened = [day for day in sessions
                 if calendar.window(day)[1] - calendar.window(day)[0] != 390]
    report: dict[str, Any] = {
        "scheduled_sessions": len(sessions),
        "first_scheduled_session": sessions[0] if sessions else None,
        "last_scheduled_session": sessions[-1] if sessions else None,
        "shortened_sessions_excluded_from_decisions": shortened,
        "input_row_cap": D0_ROW_CAP,
        "symbols": {},
    }
    for symbol in [*cfg["symbols"], cfg["benchmark"]]:
        frame = frames[symbol]
        done = list(complete[symbol])
        done_set = set(done)
        date_set = set(frame["date"].tolist())
        dates = sorted(date_set)
        first_bar = dates[0] if dates else None
        entry: dict[str, Any] = {
            "rows": int(len(frame)),
            "manifest_rows": receipts[symbol]["manifest_rows"],
            "file_row_cap_reached": int(len(frame)) >= D0_ROW_CAP,
            "first_bar_date": first_bar,
            "last_bar_date": dates[-1] if dates else None,
            "scheduled_sessions_before_first_bar": sum(1 for day in sessions
                                                       if first_bar is None or day < first_bar),
            "sessions_with_any_bar": sum(1 for day in sessions if day in date_set),
            "complete_regular_sessions": len(done),
            "first_complete_session": done[0] if done else None,
            "last_complete_session": done[-1] if done else None,
            "incomplete_sessions": [day for day in sessions if day not in done_set],
        }
        if symbol != cfg["benchmark"]:
            built = [days[(symbol, day)] for day in sessions]
            norms = [b["normalization"] for b in built]
            constructions = [b["construction"] for b in built if b["construction"] is not None]
            broken = [c["session"] for c in constructions
                      if any(d["reason"] in PREFIX_BREAKING for d in c["diagnostics"])]
            entry.update({
                "normalization": _tally(
                    n["availability"] if n["reason"] is None else f'{n["availability"]}:{n["reason"]}'
                    for n in norms),
                "beta": _tally("available" if n["beta_available"] else f'unavailable:{n["beta_reason"]}'
                               for n in norms),
                "atr_unavailable_sessions": [n["session"] for n in norms if n["availability"] != "AVAILABLE"],
                "beta_unavailable_sessions": [n["session"] for n in norms if not n["beta_available"]],
                "construction": _tally(
                    c["availability"] if c["reason"] is None else f'{c["availability"]}:{c["reason"]}'
                    for c in constructions),
                "sessions_not_constructed": len(built) - len(constructions),
                "diagnostics": _tally(d["reason"] for c in constructions for d in c["diagnostics"]),
                "prefix_incomplete_sessions": len(broken),
                "prefix_incomplete_session_dates": broken,
                "anchors": sum(len(b["anchors"]) for b in built),
                "census_rows": sum(len(b["controls"]) for b in built),
                "events": _tally(e["selector"] for b in built for e in b["events"]),
            })
        report["symbols"][symbol] = entry
    return report


def descriptive(outcomes: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Event-weighted description of the selected events' own outcomes, every registered cell."""
    grouped: dict[tuple[str, str, int], list[Mapping[str, Any]]] = {}
    for row in outcomes:
        grouped.setdefault((row["selector"], row["horizon"], row["cost_bps"]), []).append(row)
    out: dict[str, Any] = {}
    for selector in cfg["selectors"]:
        for horizon in cfg["horizons"]:
            for cost in cfg["round_trip_cost_bps"]:
                cell = grouped.get((selector, horizon, int(cost)), [])
                available = [row for row in cell if row["status"] == "available"]
                entry: dict[str, Any] = {
                    "events": len(cell), "available": len(available),
                    "censored": len(cell) - len(available),
                    "censor_reasons": _tally(row["reason"] for row in cell if row["status"] != "available"),
                }
                for field in _DESCRIPTIVE:
                    values = [float(row[field]) for row in available if row[field] is not None]
                    entry[field] = {
                        "n": len(values),
                        "mean": math.fsum(values) / len(values) if values else None,
                        "median": float(statistics.median(values)) if values else None,
                    }
                for field in _STATUS_FIELDS:
                    entry[field] = _tally(row[field] for row in cell)
                out[f"{selector}|{horizon}|{cost}"] = entry
    return out


def next_attempt_number(attempt_dir: Path) -> int:
    highest = 0
    for path in attempt_dir.glob("attempt-*.json"):
        stem = path.stem
        if stem.startswith("attempt-") and stem[8:].isdigit():
            highest = max(highest, int(stem[8:]))
    return highest + 1


def create_attempt_receipt_exclusive(attempt_dir: Path, receipt: Mapping[str, Any]) -> Path:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    attempt = int(receipt["attempt"])
    final = attempt_dir / f"attempt-{attempt:03d}.json"
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    try:
        with open(final, "x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        raise ValueError(f"attempt_number_collision:{final.name}")
    return final


def write_receipt(attempt_dir: Path, receipt: Mapping[str, Any]) -> Path:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    attempt = int(receipt["attempt"])
    final = attempt_dir / f"attempt-{attempt:03d}.json"
    scratch = attempt_dir / f".attempt-{attempt:03d}.scratch"
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    scratch.write_text(payload)
    with scratch.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(scratch, final)
    with final.open("rb") as handle:
        os.fsync(handle.fileno())
    fd = os.open(attempt_dir, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return final


def _read_receipt(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _prior_receipts(attempt_dir: Path, *, current_attempt: int) -> list[dict[str, Any]]:
    if not attempt_dir.is_dir():
        return []
    prior: list[dict[str, Any]] = []
    for path in sorted(attempt_dir.glob("attempt-*.json")):
        receipt = json.loads(path.read_text())
        if int(receipt.get("attempt", -1)) == current_attempt:
            continue
        prior.append(receipt)
    return prior


def _attempt_listing_sha256(attempt_dir: Path) -> str:
    if not attempt_dir.is_dir():
        names: list[str] = []
    else:
        names = sorted(path.name for path in attempt_dir.iterdir() if path.is_file())
    return hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()


def _merge_receipt(path: Path, **fields: Any) -> None:
    receipt = _read_receipt(path)
    receipt.update(fields)
    write_receipt(path.parent, receipt)


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _markdown(result: Mapping[str, Any]) -> str:
    cfg_selectors = result["grid"]["selectors"]
    horizons = result["grid"]["horizons"]
    costs = result["grid"]["round_trip_cost_bps"]
    aggregate = result["aggregate"]
    primary = result["grid"]["primary_selector"]
    lines = [
        "# TTI R1-B v4 — registered retrospective result",
        "",
        f"Disposition: **{result['disposition']}**",
        "",
        "Corrected-history exploratory research only. No rank, alert, sizing or trade authority; "
        "no production signal can be promoted from this batch regardless of outcome.",
        "",
        "## Identity",
        "",
    ]
    for key in ("study_id", "code_sha", "prereg_sha256", "config_sha256", "rulings_sha256",
                "grid_sha256", "registered_rows_sha256", "input_manifest_sha256"):
        lines.append(f"- {key}: `{result['identity'][key]}`")
    lines += [f"- prior attempts before this run: {len(result['attempts'])}", "",
              f"## Gate — {primary} at {result['grid']['primary_horizon']} / "
              f"{result['grid']['primary_cost_bps']} bp, all four readings", "",
              "| reading | fires with delta | dates | tickers | statistic | interval low | interval high | "
              "early | late | counts | interval > 0 | same sign | concentration | mechanical pass |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    gate = aggregate["gates"][primary]
    for reading in aggregate["readings"]:
        g = gate["readings"][reading]
        s = g["summary"]
        interval = s["interval"] or [None, None]
        lines.append("| " + " | ".join([
            reading, _fmt(s["fires_delta"]), _fmt(s["dates_delta"]), _fmt(s["tickers_delta"]),
            _fmt(s["statistic"]), _fmt(interval[0]), _fmt(interval[1]),
            _fmt(s["early_statistic"]), _fmt(s["late_statistic"]),
            _fmt(g["bullet_1_counts"]), _fmt(g["bullet_2_interval"]),
            _fmt(g["bullet_3_partition_sign"]), _fmt(g["bullet_4_concentration"]),
            _fmt(g["mechanical_pass"])]) + " |")
    lines += ["", "Gate bullet 5 (no systematic admission artifact) is not mechanical: "
              "`REQUIRES_ADJUDICATION` by an independent reviewer.", "",
              "## Matched delta, stated once per selector and horizon", "",
              "The selected event and its controls carry the same round-trip cost, so the matched "
              "delta does not depend on the cost cell. The last column prints whether that held.", "",
              "| selector | horizon | " + " | ".join(aggregate["readings"]) + " | identical across costs |",
              "|---|---|" + "---|" * (len(aggregate["readings"]) + 1)]
    for key, entry in result["matched_delta_once"].items():
        selector, horizon = key.split("|")
        lines.append("| " + " | ".join(
            [selector, horizon] + [_fmt(entry[r]["statistic"]) for r in aggregate["readings"]]
            + ["/".join(_fmt(entry[r]["identical_across_costs"]) for r in aggregate["readings"])]) + " |")
    lines += ["", "## All 60 registered cells", "",
              "Counts are per cell; the selected events' own net beta-residual mean is event-weighted "
              "and descriptive. Reading shown for the delta columns: L-A.", "",
              "| selector | horizon | cost bp | fires | available | censored | no control | "
              "fires with delta | mean net return | mean net beta residual | matched delta |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for selector in cfg_selectors:
        for horizon in horizons:
            for cost in costs:
                key = f"{selector}|{horizon}|{cost}"
                cell = aggregate["cells"][key]["L-A"]
                desc = result["descriptive"][key]
                lines.append("| " + " | ".join([
                    selector, horizon, str(cost), _fmt(cell["fires_raw"]), _fmt(desc["available"]),
                    _fmt(desc["censored"]), _fmt(cell["no_control"]), _fmt(cell["fires_delta"]),
                    _fmt(desc["net_return"]["mean"]), _fmt(desc["net_beta_residual"]["mean"]),
                    _fmt(cell["statistic"])]) + " |")
    lines += ["", "## Coverage", "",
              "| symbol | rows | complete sessions | incomplete | prefix-incomplete | "
              "row cap reached | sessions before first bar |",
              "|---|---|---|---|---|---|---|"]
    for symbol, entry in result["coverage"]["symbols"].items():
        lines.append("| " + " | ".join([
            symbol, _fmt(entry["rows"]), _fmt(entry["complete_regular_sessions"]),
            _fmt(len(entry["incomplete_sessions"])), _fmt(entry.get("prefix_incomplete_sessions")),
            _fmt(entry["file_row_cap_reached"]),
            _fmt(entry["scheduled_sessions_before_first_bar"])]) + " |")
    lines += ["", "## Limits", "",
              "- Retrospective, current-universe, eight tickers; survivorship and composition limits apply.",
              "- Historical per-bar availability, live fills and contemporaneous quotes are not proven.",
              "- The 10/25/50 bp costs are sensitivities, not measured spreads.",
              "- The early/late split is a stability split, not an untouched holdout.",
              "- Event-, outcome- and match-level files and every licensed bar stay outside Git.", ""]
    return "\n".join(lines)


def execute(*, input_dir: Path, manifest: Path, terminal_root: Path, output_dir: Path,
            code_sha: str, junit: Path, state: dict[str, Any],
            run_root: Path, run_root_source: str) -> dict[str, Any]:
    """The single registered run.  ``state`` reports the stage reached to the attempt recorder."""
    attempt_dir = run_root / "attempts"
    attempt = next_attempt_number(attempt_dir)
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    receipt: dict[str, Any] = {
        "schema": ATTEMPT_SCHEMA,
        "study_id": STUDY_ID,
        "attempt": attempt,
        "stage": "arguments",
        "code_sha": code_sha,
        "attempt_root": str(run_root.resolve()),
        "started_at": started_at,
        "finalized": False,
        "completed": False,
        "outcome_stage_started": False,
        "outcome_values_persisted": None,
        "exception_type": None,
        "frames": [],
    }
    attempt_path = create_attempt_receipt_exclusive(attempt_dir, receipt)
    state["attempt_path"] = attempt_path
    state["persisted"] = False
    state["stage"] = "arguments"

    def stage(name: str, note: str = "") -> None:
        state["stage"] = name
        fields: dict[str, Any] = {"stage": name}
        if name == "outcomes":
            fields["outcome_stage_started"] = True
        _merge_receipt(attempt_path, **fields)
        print(f"[r1b] {name}{(' ' + note) if note else ''}", file=sys.stderr, flush=True)

    stage("arguments")
    if not re.fullmatch(r"[0-9a-f]{40}", code_sha or ""):
        raise ValueError("code_sha_invalid")
    expected_output_root = run_root / "output"
    if output_dir.parent.resolve() != expected_output_root.resolve():
        raise ValueError("output_directory_outside_run_root")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    git_probe = subprocess.run(
        _git_cmd(output_dir.parent, "rev-parse", "--show-toplevel"),
        capture_output=True,
        env=_git_env(),
    )
    if git_probe.returncode == 0:
        raise ValueError("output_directory_inside_git")
    if output_dir.exists():
        raise ValueError("output_directory_exists")
    if RESULT_PATH.exists() or REPORT_PATH.exists():
        raise ValueError("results_artifact_exists")
    prior = _prior_receipts(attempt_dir, current_attempt=attempt)
    if any(receipt.get("outcome_values_persisted") is True for receipt in prior):
        raise ValueError("registered_run_already_persisted")
    for old in prior:
        if old.get("outcome_values_persisted") is None and old.get("stage") in OUTCOME_STAGES:
            num = int(old.get("attempt", 0))
            raise ValueError(f"prior_attempt_unfinalized:attempt-{num:03d}.json")
    tests = junit_receipt(junit, code_sha)
    expected = _collected_test_ids(TEST_FILES)
    if set(tests["cases"]) != expected:
        raise ValueError("test_receipt_case_set_mismatch")
    tests["expected_cases_sha256"] = hashlib.sha256(
        "\n".join(sorted(expected)).encode("utf-8")
    ).hexdigest()
    tests["collected_from"] = list(TEST_FILES)
    pinned_blobs = _pinned_test_blobs_on_disk(code_sha)
    for path in TEST_PINNED_FILES:
        if _reviewed_blob_sha256(code_sha, path) != pinned_blobs[path]:
            raise ValueError(f"code_identity_not_at_reviewed_head:{path}")
    code_files = _loaded_root_modules()
    digest = code_digest(code_files, pinned_blobs)
    _merge_receipt(attempt_path, code_digest=digest)
    if any(receipt.get("stage") not in PRE_INPUT_STAGES
           and receipt.get("code_digest") == digest for receipt in prior):
        raise ValueError("rerun_without_reviewed_fix")

    stage("admission")
    admitted = verify_admission()
    config_bytes = CONFIG_PATH.read_bytes()
    cfg = json.loads(config_bytes)
    if int(cfg["bootstrap_repetitions"]) != 4000 or int(cfg["seed"]) != 20260917:
        raise ValueError("frozen_bootstrap_identity_mismatch")
    for name in CODE_FILES:
        if name not in code_files:
            raise ValueError(f"code_identity_missing_required:{name}")
    for name, blob in code_files.items():
        if _reviewed_blob_sha256(code_sha, name) != blob:
            raise ValueError(f"code_identity_not_at_reviewed_head:{name}")
    if _sha(RULINGS_PATH) != RULINGS_SHA256:
        raise ValueError("rulings_sha_mismatch")
    input_pins = _admission_input_pins(manifest, terminal_root, cfg)
    identity = {
        "study_id": STUDY_ID, "code_sha": code_sha,
        "prereg_sha256": admitted["prereg_sha256"], "config_sha256": admitted["config_sha256"],
        "rulings_sha256": _sha(RULINGS_PATH), "grid_sha256": admitted["grid_sha256"],
        "registered_rows_sha256": admitted["registered_rows_sha256"],
        "registration_commit": admitted["registration_commit"],
        "ledger_sha256": admitted["ledger_sha256"], "ledger_lines": admitted["ledger_lines"],
        "ledger_prefix_matches_receipt": admitted["ledger_prefix_matches_receipt"],
        "input_manifest_sha256": D0_MANIFEST_SHA256,
        "code_files": code_files,
        "code_files_required": list(CODE_FILES),
    }

    stage("inputs")
    loaded = load_inputs(input_dir, manifest, terminal_root, cfg, pins=input_pins)
    frames, calendar = loaded["frames"], loaded["calendar"]
    sessions = scheduled_sessions(calendar, cfg)

    stage("construction", f"sessions={len(sessions)}")
    days, complete = build_days(frames, sessions, calendar, cfg, config_bytes=config_bytes)
    events = [event for day in sessions for symbol in cfg["symbols"]
              for event in days[(symbol, day)]["events"]]
    census = [row for day in sessions for symbol in cfg["symbols"]
              for row in days[(symbol, day)]["controls"]]
    refuse_outcome_flags(events, census, days)
    coverage = coverage_report(days, frames, loaded["receipts"], sessions, complete, calendar, cfg)

    stage("pools", f"events={len(events)} census={len(census)}")
    usable, rejected = pools.split_census(census)
    ordered = sorted(events, key=lambda e: (e["selector"], e["symbol"], e["session"], e["anchor_id"]))
    built_pools = pools.build_pools(ordered, usable, config_bytes=config_bytes)
    refuse_pool_flags(built_pools)
    pre_files = {
        "coverage.json": _canonical(coverage),
        "events.jsonl": _jsonl(ordered),
        "census.jsonl": _jsonl(census),
        "pools.jsonl": _jsonl(built_pools),
    }
    pre_hashes = {name: _digest(raw) for name, raw in pre_files.items()}
    pre_hashes["pools_digest"] = pools.pools_digest(built_pools)
    output_dir.mkdir(parents=True)
    for name, raw in pre_files.items():
        (output_dir / name).write_bytes(raw)

    stage("preflight")
    preflight = pools.preflight(ordered, built_pools, days, config_bytes=config_bytes)
    excluded_total: Counter[str] = Counter()
    for pool in built_pools:
        excluded_total.update(pool["excluded_counts"])
    counts = {
        "scheduled_sessions": len(sessions), "symbol_sessions": len(days),
        "events_total": len(ordered), "events": _tally(e["selector"] for e in ordered),
        "census_rows": len(census), "census_null_sign_rejected": int(rejected),
        "census_usable": len(usable),
        "pools": {selector: _tally(
            p["availability"] if p["reason"] is None else f'{p["availability"]}:{p["reason"]}'
            for p in built_pools if p["selector"] == selector) for selector in cfg["selectors"]},
        "matched_controls_total": sum(len(p["matched_controls"]) for p in built_pools),
        "excluded_counts": {str(k): int(v) for k, v in sorted(excluded_total.items())},
        "preflight": {k: int(v) for k, v in preflight.items()},
    }
    pre_receipt = {"schema": "mastermind.tti.r1b.pre_outcome.v4", "study_id": STUDY_ID,
                   "code_sha": code_sha, "hashes": pre_hashes, "counts": counts,
                   "market_outcomes_computed": False}
    (output_dir / "pre_outcome_receipt.json").write_bytes(_canonical(pre_receipt))

    stage("outcomes")
    by_key = {(pool["selector"], pool["anchor_id"]): pool for pool in built_pools}
    cache: dict[tuple, float | None] = {}
    rows: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    for event in ordered:
        own = days[(event["symbol"], event["session"])]
        cells = pools.measure_rows(event, by_key[(event["selector"], event["anchor_id"])], days,
                                   config_bytes=config_bytes, cache=cache)
        grid = measure_event_grid(event, own["stock_frame"], own["benchmark_frame"],
                                  session=date.fromisoformat(event["session"]),
                                  config_bytes=config_bytes)
        lookup = {(g["horizon"], g["cost_bps"]): g for g in grid}
        for row in cells:
            measured = lookup[(row["horizon"], row["cost_bps"])]
            if (measured["status"] != row["selected_status"]
                    or measured["net_beta_residual"] != row["selected_return"]):
                raise ValueError("selected_outcome_mismatch")
        rows.extend(cells)
        outcomes.extend(grid)

    stage("aggregate")
    summary = agg.summarize(rows, cfg=cfg)
    for selector in cfg["selectors"]:
        expected = sum(1 for event in ordered if event["selector"] == selector)
        for horizon in cfg["horizons"]:
            for cost in cfg["round_trip_cost_bps"]:
                for reading in agg.READINGS:
                    cell = summary["cells"][f"{selector}|{horizon}|{cost}"][reading]
                    union = cell["no_control"] + cell["selected_censored"] - cell["no_control_and_censored"]
                    if (cell["fires_raw"] != expected or cell["control_evidence_unavailable"] < 0
                            or cell["fires_raw"] != cell["fires_delta"]
                            + cell["control_evidence_unavailable"] + union):
                        raise ValueError("event_accounting_identity_violated")
    matched_once = {
        f"{selector}|{horizon}": {
            reading: {
                "statistic": summary["cells"][f"{selector}|{horizon}|{cfg['primary_cost_bps']}"][reading]["statistic"],
                "identical_across_costs": summary["cost_invariance"][f"{selector}|{horizon}"][reading],
            } for reading in agg.READINGS}
        for selector in cfg["selectors"] for horizon in cfg["horizons"]}
    private = {"rows.jsonl": _jsonl(rows), "outcomes.jsonl": _jsonl(outcomes)}
    result = {
        "schema": RESULT_SCHEMA, "study_id": STUDY_ID,
        "attempt_root": str(run_root.resolve()),
        "attempt_root_source": run_root_source,
        "code_digest": digest,
        "authority": "retrospective_research_only",
        "may_rank": False, "may_alert": False, "may_size": False, "may_trade": False,
        "research_admission": cfg["research_admission"],
        "disposition": summary["gates"][cfg["primary_selector"]]["disposition"],
        "identity": identity,
        "grid": {"selectors": list(cfg["selectors"]), "horizons": list(cfg["horizons"]),
                 "round_trip_cost_bps": [int(c) for c in cfg["round_trip_cost_bps"]],
                 "primary_selector": cfg["primary_selector"],
                 "primary_horizon": cfg["primary_horizon"],
                 "primary_cost_bps": int(cfg["primary_cost_bps"]), "cells": STUDY_ROWS},
        "window": {"start": cfg["start"], "end": cfg["end"],
                   "early_partition_end": cfg["early_partition_end"],
                   "late_partition_start": cfg["late_partition_start"]},
        "inputs": {"manifest_sha256": loaded["manifest_sha256"], "receipts": loaded["receipts"],
                   "terminal_dependency": loaded["terminal"]},
        "coverage": coverage, "counts": counts,
        "aggregate": summary, "matched_delta_once": matched_once,
        "descriptive": descriptive(outcomes, cfg),
        "leak_audit": {
            "pre_outcome_hashes": pre_hashes,
            "private_file_hashes": {name: _digest(raw) for name, raw in private.items()},
            "code_sha": code_sha, "code_files": identity["code_files"],
            "code_files_required": identity["code_files_required"],
            "code_files_late": identity.get("code_files_late", []),
            "test_receipt": tests,
            "census_rows_checked": len(census), "census_future_family_labels_used": False,
            "pools_checked": len(built_pools), "pools_market_outcomes_computed": False,
            "pools_fallback_used": False,
            "events_market_outcomes_computed_at_construction": False,
            "rejections": {"census_null_sign": int(rejected),
                           "match_excluded_by_reason": counts["excluded_counts"],
                           "pools": counts["pools"]},
            "overlap": {"per_selector": pools.overlap(built_pools),
                        "all_selectors": pools.overlap_all(built_pools)},
            "preflight": counts["preflight"],
            "control_outcomes_cached": len(cache),
            "ledger_prefix_matches_receipt": admitted["ledger_prefix_matches_receipt"],
            "network_refused": True,
            "versions": {"python": platform.python_version(), "numpy": np.__version__,
                         "pandas": pd.__version__},
        },
        "attempts": prior,
        "attempt_listing_sha256": _attempt_listing_sha256(attempt_dir),
    }
    files = {"result.json": (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"),
             "report.md": _markdown(result).encode("utf-8"), **private}

    final = _loaded_root_modules()
    for name, digest in identity["code_files"].items():
        if final.get(name) != digest:
            raise ValueError(f"code_identity_drift:{name}")
    late = sorted(set(final) - set(identity["code_files"]))
    for name in late:
        if _reviewed_blob_sha256(code_sha, name) != final[name]:
            raise ValueError(f"code_identity_not_at_reviewed_head:{name}")
    identity["code_files"] = final
    identity["code_files_late"] = late
    result["identity"] = identity
    result["leak_audit"]["code_files"] = identity["code_files"]
    result["leak_audit"]["code_files_required"] = identity["code_files_required"]
    result["leak_audit"]["code_files_late"] = identity["code_files_late"]
    files["result.json"] = (
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")

    stage("persist")
    _merge_receipt(attempt_path, stage="persist", outcome_values_persisted=True)
    state["persisted"] = True
    for name, raw in files.items():
        (output_dir / name).write_bytes(raw)
    finished_at = datetime.now(UTC).isoformat(timespec="seconds")
    _merge_receipt(attempt_path, finalized=True, completed=True, finished_at=finished_at)
    return {"status": "completed", "output_dir": str(output_dir),
            "result_sha256": _digest(files["result.json"])}


def _finalize_attempt_on_failure(
    *, attempt_dir: Path, attempt_path: Path | None, state: Mapping[str, Any],
    exc: BaseException, code_sha: str | None,
) -> None:
    frames = [f"{Path(frame.filename).name}:{frame.lineno}"
              for frame in traceback.extract_tb(exc.__traceback__)]
    persisted = state.get("persisted", False)
    stage_name = state.get("stage", "arguments")
    fields = {
        "finalized": True,
        "completed": False,
        "stage": stage_name,
        "exception_type": type(exc).__name__,
        "frames": frames,
        "outcome_values_persisted": bool(state.get("persisted", False)),
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if attempt_path is not None and attempt_path.is_file():
        _merge_receipt(attempt_path, **fields)
        return
    attempt = next_attempt_number(attempt_dir)
    receipt = {
        "schema": ATTEMPT_SCHEMA,
        "study_id": STUDY_ID,
        "attempt": attempt,
        "stage": stage_name,
        "code_sha": code_sha,
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "finalized": True,
        "completed": False,
        "outcome_stage_started": stage_name in OUTCOME_STAGES,
        "outcome_values_persisted": bool(state.get("persisted", False)),
        "exception_type": type(exc).__name__,
        "frames": frames,
        "finished_at": fields["finished_at"],
    }
    write_receipt(attempt_dir, receipt)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--terminal-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--code-sha")
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--attempt-root", type=Path, default=None, dest="attempt_root")
    args = parser.parse_args(argv)
    if args.verify_only:
        try:
            print(json.dumps(verify_admission(), sort_keys=True))
            return 0
        except Exception as exc:
            print(f"R1-B study refused: {exc}", file=sys.stderr)
            return 2
    state: dict[str, Any] = {"stage": "arguments", "persisted": False, "attempt_path": None}
    run_root, run_root_source = attempt_root(args)
    attempt_dir = run_root / "attempts"
    try:
        if None in (args.input_dir, args.manifest, args.terminal_root, args.output_dir,
                    args.code_sha, args.junit):
            raise ValueError("full_run_requires_input_manifest_terminal_output_code_sha_junit")
        with no_network():
            done = execute(input_dir=args.input_dir, manifest=args.manifest,
                           terminal_root=args.terminal_root, output_dir=args.output_dir,
                           code_sha=args.code_sha, junit=args.junit,
                           state=state, run_root=run_root, run_root_source=run_root_source)
        print(json.dumps(done, sort_keys=True))
        return 0
    except BaseException as exc:
        _finalize_attempt_on_failure(
            attempt_dir=attempt_dir,
            attempt_path=state.get("attempt_path"),
            state=state,
            exc=exc,
            code_sha=args.code_sha,
        )
        reached = state["stage"]
        text = str(exc)
        if (reached in PRE_INPUT_STAGES or _REFUSAL_STDERR.match(text)
                or (reached not in OUTCOME_STAGES and _REFUSAL_CODE.fullmatch(text))):
            print(f"R1-B study refused: {text}", file=sys.stderr)
        else:
            print(f"R1-B study aborted during {reached}: {type(exc).__name__}", file=sys.stderr)
        if not isinstance(exc, Exception):
            raise
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
