"""Nightly grader for the Grey Deer SPY pullback forward log.

Reads ``forward_log.jsonl`` and appends one grade row per issued row whose
horizon has fully matured. Grades are append-only and keep-first. This module
does not edit the issue log and does not grade an immature row.

Labels come from :func:`lib.observed_moves.forward_max_loss` and
:func:`lib.observed_moves.loss_event` at the stage-1 threshold. The math is
not copied here.
"""
from __future__ import annotations

import hashlib
import json
import operator
import os
import re
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from engine import grey_deer_pullback_forward as fwd
from lib import observed_moves as om
from lib.nyse_calendar import sessions_between
from scripts.research import grey_deer_pullback_stage1 as s1

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = REPO_ROOT / "data" / "grey_deer_pullback"

ISSUE_LOG_NAME = "forward_log.jsonl"
GRADE_LOG_NAME = "forward_log_graded.jsonl"
REFUSAL_LOG_NAME = "forward_log_refusals.jsonl"

ISSUE_SCHEMA = "grey_deer_pullback_forward_issue.v1"
GRADE_SCHEMA = "grey_deer_pullback_forward_grade.v1"
REFUSAL_SCHEMA = "grey_deer_pullback_forward_refusal.v1"

EVIDENCE_ISSUED = "GENUINELY_ISSUED"
EVIDENCE_GRADE = "GRADE"
GRADER_LANE = "nightly"
IDENTITY_PIN = "daily.yml:engine"
LANE_ENV = "COLLECT_LANE"
IDENTITY_ENV = "GREY_DEER_PULLBACK_GRADER_IDENTITY"

_HEX40 = re.compile(r"[0-9a-f]{40}")
_COUNT_KEYS = (
    "graded",
    "already_graded",
    "immature",
    "asof_missing",
    "prereg_mismatch",
    "malformed",
    "skipped_non_issued",
)


def _utc_now() -> str:
    """UTC ISO-8601 with seconds and a numeric offset. Tests monkeypatch this."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_head() -> str:
    """``git rev-parse HEAD`` at the repo root, or ``""`` when git fails."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return proc.stdout.strip()


def _summary(refusals: list[dict] | None = None, **counts: int) -> dict:
    out: dict = {key: 0 for key in _COUNT_KEYS}
    out.update(counts)
    out["refusals"] = list(refusals or [])
    return out


def _sha256_json(payload: dict) -> str:
    blob = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _append_jsonl(path: Path, row: dict) -> None:
    """One ``O_APPEND`` write of one canonical JSON line. A torn tail is dropped first."""
    payload = json.dumps(
        row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8") + b"\n"
    fwd._append_payload(path, payload)


def _raw_lines(path: Path) -> list[bytes]:
    """Complete JSON lines. A trailing partial is ignored and not returned."""
    data = fwd.durable_jsonl_prefix(path.read_bytes())
    if not data:
        return []
    parts = data.split(b"\n")
    if parts[-1] == b"":
        parts = parts[:-1]
    return [part for part in parts if part != b""]


def _window_close(close: pd.Series) -> pd.Series:
    """Dates on or after ``WINDOW_START``, positional, chronological.

    The caller passes one ticker's session closes. Stage 1 drops earlier rows
    only after its own hash; the grader receives an already-loaded series and
    applies the same date cut before any positional label.
    """
    if not isinstance(close, pd.Series):
        raise TypeError("close must be a pandas Series")
    idx = fwd.naive_session_index(close.index)
    values = close.to_numpy(dtype=float, copy=True)
    window = pd.Series(values, index=idx).sort_index(kind="mergesort")
    start = pd.Timestamp(s1.WINDOW_START)
    return window.loc[window.index >= start]


def _horizon_labels(close_window: pd.Series) -> dict[int, tuple[pd.Series, pd.Series]]:
    """Stage-1 pair: ``forward_max_loss`` then ``loss_event`` at ``THRESHOLD``."""
    out: dict[int, tuple[pd.Series, pd.Series]] = {}
    for horizon in s1.HORIZONS:
        h = int(horizon)
        series_a = om.forward_max_loss(close_window, h)
        out[h] = (series_a, om.loss_event(series_a, threshold=s1.THRESHOLD))
    return out


def _is_issued(row: dict) -> bool:
    return fwd.issued_row_admitted(row)


def _issue_key(row: dict) -> tuple[str, str, int, str] | None:
    asof = row.get("asof")
    ticker = row.get("ticker")
    horizon = row.get("horizon")
    config_id = row.get("config_id")
    if not isinstance(asof, str) or not isinstance(ticker, str) or not isinstance(config_id, str):
        return None
    if isinstance(horizon, bool) or not isinstance(horizon, int):
        return None
    if horizon not in s1.HORIZONS:
        return None
    return (asof, ticker, horizon, config_id)


def _mapping_key(source: dict) -> tuple[str, str, int, str] | None:
    asof = source.get("asof")
    ticker = source.get("ticker")
    horizon = source.get("horizon")
    config_id = source.get("config_id")
    if not isinstance(asof, str) or not isinstance(ticker, str) or not isinstance(config_id, str):
        return None
    if isinstance(horizon, bool) or not isinstance(horizon, int):
        return None
    return (asof, ticker, int(horizon), config_id)


def _grade_key(row: dict) -> tuple[str, str, int, str] | None:
    """Join key. Top-level §2.2 fields win; a legacy nested ``key`` still matches."""
    top = _mapping_key(row)
    if top is not None:
        return top
    nested = row.get("key")
    if isinstance(nested, dict):
        return _mapping_key(nested)
    return None


def _horizon_sessions_aligned(close_window: pd.Series, pos: int, asof: str, horizon: int) -> bool:
    """True when ``index[pos + i]`` is the i-th NYSE session after ``asof``, for i = 1..h."""
    if horizon < 1 or pos < 0 or pos + horizon >= len(close_window):
        return False
    try:
        origin = date.fromisoformat(asof)
    except ValueError:
        return False
    upcoming = sessions_between(origin + timedelta(days=1), origin + timedelta(days=horizon * 3 + 21))
    if len(upcoming) < horizon:
        return False
    for step in range(1, horizon + 1):
        stamp = pd.Timestamp(close_window.index[pos + step]).strftime("%Y-%m-%d")
        if stamp != upcoming[step - 1].isoformat():
            return False
    return True


def _load_grades(path: Path) -> dict[tuple[str, str, int, str], dict]:
    found: dict[tuple[str, str, int, str], dict] = {}
    if not path.is_file():
        return found
    for raw in _raw_lines(path):
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        key = _grade_key(obj)
        if key is not None and key not in found:
            found[key] = obj
    return found


def _same_float(left: object, right: object) -> bool:
    try:
        a = float(left)  # type: ignore[arg-type]
        b = float(right)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if a != a or b != b:  # NaN
        return False
    return a == b


def _inputs_digest(asof: str, closes: list[str], horizon: int, store_identity: object, ticker: str) -> str:
    payload = {
        "asof": asof,
        "closes": closes,
        "horizon": horizon,
        "store_identity": store_identity,
        "ticker": ticker,
    }
    return _sha256_json(payload)


def _refusal(
    refused_at: str,
    reason: str,
    *,
    writer_lane: str,
    attempt: dict,
    asof: str | None = None,
    ticker: str | None = None,
    horizon: int | None = None,
    config_id: str | None = None,
) -> dict:
    return {
        "schema": REFUSAL_SCHEMA,
        "refused_at": refused_at,
        "reason": reason,
        "asof": asof,
        "ticker": ticker,
        "horizon": horizon,
        "config_id": config_id,
        "writer_lane": writer_lane,
        "attempt_digest": _sha256_json(attempt),
    }


def _gate_refusal(refused_at: str) -> dict | None:
    """Lane then identity. The first failure is returned in memory and not written."""
    lane = os.environ.get(LANE_ENV)
    if lane != GRADER_LANE:
        claimed = lane if isinstance(lane, str) and lane else "absent"
        return _refusal(
            refused_at,
            "LANE",
            writer_lane=claimed,
            attempt={"collect_lane": lane, "reason": "LANE"},
        )
    identity = os.environ.get(IDENTITY_ENV)
    if identity != IDENTITY_PIN:
        return _refusal(
            refused_at,
            "IDENTITY",
            writer_lane=GRADER_LANE,
            attempt={"identity": identity, "reason": "IDENTITY"},
        )
    return None


def _position(close_window: pd.Series, asof: str) -> int | None:
    """Positional index of ``asof`` in the window, or None when it is absent.

    A duplicate timestamp (``get_loc`` returns a slice or an array) is treated
    as absent. Only a scalar integer location is a session we can grade.
    """
    try:
        stamp = pd.Timestamp(asof)
    except (ValueError, TypeError, OverflowError):
        return None
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("UTC").tz_localize(None)
    stamp = stamp.normalize()
    try:
        loc = close_window.index.get_loc(stamp)
    except KeyError:
        return None
    if isinstance(loc, slice):
        return None
    try:
        pos = operator.index(loc)
    except TypeError:
        return None
    if not 0 <= pos < len(close_window):
        return None
    return pos


def grade(
    close: pd.Series,
    *,
    ticker: str,
    store_identity: object,
    log_dir: Path | str | None = None,
    recompute_inputs_digest=None,
) -> dict:
    """Grade matured issue rows for ``ticker`` into the sibling grade log.

    ``recompute_inputs_digest``, when given, is
    ``(close_window_prefix, i, h, ticker, store_identity, training_end_asof) -> str``.
    ``revision_flag`` is null when the callable is omitted. When it is given,
    the flag is whether the recomputed digest differs from the issue row's
    ``inputs_digest``.

    Off-lane calls (``COLLECT_LANE`` not exactly ``nightly``, or
    ``GREY_DEER_PULLBACK_GRADER_IDENTITY`` not exactly ``daily.yml:engine``)
    return a refusal and write nothing. A ``_git_head()`` that is not 40
    lowercase hex appends one ``SHA_MISMATCH`` refusal and grades nothing.
    """
    refused_at = _utc_now()
    blocked = _gate_refusal(refused_at)
    if blocked is not None:
        return _summary([blocked])

    directory = DEFAULT_LOG_DIR if log_dir is None else Path(log_dir)
    issue_path = directory / ISSUE_LOG_NAME
    if not issue_path.is_file():
        return _summary()

    head = _git_head()
    if _HEX40.fullmatch(head) is None:
        refusal = _refusal(
            refused_at,
            "SHA_MISMATCH",
            writer_lane=GRADER_LANE,
            attempt={"grader_sha": head, "reason": "SHA_MISMATCH"},
        )
        _append_jsonl(directory / REFUSAL_LOG_NAME, refusal)
        return _summary([refusal])

    close_window = _window_close(close)
    labels = _horizon_labels(close_window)
    existing = _load_grades(directory / GRADE_LOG_NAME)
    counts = {key: 0 for key in _COUNT_KEYS}
    refusals: list[dict] = []

    for raw in _raw_lines(issue_path):
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            counts["malformed"] += 1
            continue
        if not isinstance(parsed, dict):
            counts["malformed"] += 1
            continue
        if parsed.get("ticker") != ticker:
            continue
        if not _is_issued(parsed):
            counts["skipped_non_issued"] += 1
            continue
        if parsed.get("prereg_blob") != s1.PREREG_BLOB:
            counts["prereg_mismatch"] += 1
            key = _issue_key(parsed)
            if key is None:
                asof_r = parsed.get("asof") if isinstance(parsed.get("asof"), str) else None
                ticker_r = parsed.get("ticker") if isinstance(parsed.get("ticker"), str) else None
                horizon_r = parsed.get("horizon")
                if isinstance(horizon_r, bool) or not isinstance(horizon_r, int):
                    horizon_r = None
                config_r = parsed.get("config_id") if isinstance(parsed.get("config_id"), str) else None
            else:
                asof_r, ticker_r, horizon_r, config_r = key
            mismatch = _refusal(
                refused_at,
                "PREREG_MISMATCH",
                writer_lane=GRADER_LANE,
                attempt={"prereg_blob": parsed.get("prereg_blob"), "reason": "PREREG_MISMATCH"},
                asof=asof_r,
                ticker=ticker_r,
                horizon=horizon_r,
                config_id=config_r,
            )
            _append_jsonl(directory / REFUSAL_LOG_NAME, mismatch)
            refusals.append(mismatch)
            continue
        key = _issue_key(parsed)
        if key is None:
            counts["skipped_non_issued"] += 1
            continue
        asof, row_ticker, horizon, config_id = key
        pos = _position(close_window, asof)
        if pos is None:
            counts["asof_missing"] += 1
            continue
        if not _horizon_sessions_aligned(close_window, pos, asof, horizon):
            counts["immature"] += 1
            continue
        series_a, series_y = labels[horizon]
        realized = series_a.iloc[pos]
        if pd.isna(realized):
            counts["immature"] += 1
            continue
        realized_a = float(realized)
        if realized_a != realized_a or realized_a in (float("inf"), float("-inf")):
            counts["immature"] += 1
            continue
        y_raw = series_y.iloc[pos]
        if pd.isna(y_raw):
            counts["immature"] += 1
            continue
        y_value = 1 if bool(y_raw) else 0
        path = [repr(float(c)) for c in close_window.iloc[pos:pos + horizon + 1]]
        digest = _inputs_digest(asof, path, horizon, store_identity, ticker)
        if recompute_inputs_digest is None:
            revision_flag = None
        else:
            prefix = close_window.iloc[: pos + 1].copy()
            recomputed = recompute_inputs_digest(
                prefix,
                pos,
                horizon,
                ticker,
                store_identity,
                parsed.get("training_end_asof"),
            )
            revision_flag = recomputed != parsed.get("inputs_digest")
        grade_row = {
            "schema": GRADE_SCHEMA,
            "asof": asof,
            "ticker": row_ticker,
            "horizon": horizon,
            "config_id": config_id,
            "issue_line_sha256": hashlib.sha256(raw).hexdigest(),
            "prereg_blob": parsed.get("prereg_blob"),
            "realized_A": realized_a,
            "Y": y_value,
            "graded_at": refused_at,
            "grader_sha": head,
            "grader_lane": GRADER_LANE,
            "grade_inputs_digest": digest,
            "revision_flag": revision_flag,
            "evidence_class": EVIDENCE_GRADE,
        }
        previous = existing.get(key)
        if previous is not None:
            same_line = previous.get("issue_line_sha256") == grade_row["issue_line_sha256"]
            same_a = _same_float(previous.get("realized_A"), realized_a)
            if same_line and same_a:
                counts["already_graded"] += 1
                continue
            conflict = _refusal(
                refused_at,
                "DUPLICATE_KEY",
                writer_lane=GRADER_LANE,
                attempt=grade_row,
                asof=asof,
                ticker=row_ticker,
                horizon=horizon,
                config_id=config_id,
            )
            _append_jsonl(directory / REFUSAL_LOG_NAME, conflict)
            refusals.append(conflict)
            continue
        _append_jsonl(directory / GRADE_LOG_NAME, grade_row)
        existing[key] = grade_row
        counts["graded"] += 1

    return _summary(refusals, **counts)
