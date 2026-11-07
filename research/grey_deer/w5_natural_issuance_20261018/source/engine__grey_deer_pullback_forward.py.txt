"""Prospective issuance writer for the Grey Deer SPY pullback forward log.

One nightly call appends one row per (horizon, P-all config) for the latest
closed session in the close series it was given. Rows are append-only and
keep-first: a key that is already on ``forward_log.jsonl`` is left byte-for-byte
and the second attempt is a ``DUPLICATE_KEY`` refusal. This module does not
register itself with the nightly job.

The fit for a test block is recomputed every night from the frozen training
index set (warm origins strictly before the block, purged so ``idx + h <= s0``).
Recomputation is deterministic, so every asof in a block sees the same fit
unless a vendor revised a training bar. That revision is visible through
``inputs_digest``, which binds the asof close, the asof feature vector, the
training-prefix end (``training_end_asof``), the ticker, and the store identity.
A later night with a different digest does not rewrite the issued row.

The prospective block id never merges a short final block. That differs from
``build_fold_calendar``, which folds a tail shorter than 63 sessions into its
predecessor. Issuance uses the unmerged block so a night inside a short tail
does not inherit the previous block's fit.

Scoring is ``score_asof``. It has no I/O, no clock, no git, and no environment
reads. ``ticker`` and ``store_identity`` are keyword-only because the digest
formula binds them; omitting both leaves ``inputs_digest`` null and is the
pure parity call. The appender is ``issue``.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import subprocess
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.nyse_calendar import ET, expected_last_session, is_session, sessions_between
from scripts.research import grey_deer_pullback_stage1 as s1

REPO_ROOT = Path(__file__).resolve().parents[1]

ISSUE_SCHEMA = "grey_deer_pullback_forward_issue.v1"
REFUSAL_SCHEMA = "grey_deer_pullback_forward_refusal.v1"
EPOCH = "grey_deer_pullback_prospective.v1"
WRITER_LANE = "nightly"
WRITER_IDENTITY = "daily.yml:engine"
LANE_ENV = "COLLECT_LANE"
IDENTITY_ENV = "GREY_DEER_PULLBACK_WRITER_IDENTITY"
FORWARD_LOG_NAME = "forward_log.jsonl"
REFUSAL_LOG_NAME = "forward_log_refusals.jsonl"
POPULATION = "P-all"

# Closed source list for recipe_fingerprint. PREREG_PATH is the frozen prereg
# whose blob is also appended as the trailing ``prereg_blob`` line.
RECIPE_FILES = (
    "engine/grey_deer_pullback_forward.py",
    "scripts/research/grey_deer_pullback_stage1.py",
    "lib/observed_moves.py",
    "lib/nyse_calendar.py",
    "engine/vol_forecast.py",  # stage 1: ``from engine.vol_forecast import realized_vol``
    s1.PREREG_PATH,
)

_GATE_IDS = frozenset({"M3-ALL@C=1.0", "Q3-ALL"})
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_SETTLE = time(17, 0)
_OPEN = time(9, 30)
_GRADING_FIELDS = ("realized_A", "Y", "graded_at", "grader_sha")


class _DigestMissing(Exception):
    """inputs_digest cannot be formed (empty store identity or a non-finite value)."""


def _issued_config_id(stage_id: str) -> str:
    if stage_id == "M3-ALL":
        return "M3-ALL@C=1.0"
    if stage_id == "M3-ALL-C0.1":
        return "M3-ALL@C=0.1"
    return stage_id


def _date_str(value) -> str:
    """Calendar date the stamp already displays, with no timezone conversion."""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def naive_session_index(index) -> pd.DatetimeIndex:
    """Naive midnights of each stamp's own ``YYYY-MM-DD``.

    Shared with the grader. A UTC-aware stamp keeps the date in its own
    zone: both 21:00Z and 00:00Z on that UTC date stay on that date.
    """
    stamps = pd.DatetimeIndex(pd.to_datetime(index))
    return pd.DatetimeIndex(pd.to_datetime(stamps.strftime("%Y-%m-%d")))


def _as_date(value) -> date:
    return date.fromisoformat(_date_str(value))


def _prepare_close(close: pd.Series) -> pd.Series:
    """Window at ``WINDOW_START`` and return a positional session series.

    The index must be strictly increasing and unique. A DatetimeIndex (any
    timezone) or date strings parsable by ``pd.Timestamp`` are accepted. Rows
    before the frozen window are dropped, matching stage 1's ``main`` path,
    and the remaining rows are indexed ``0 .. n-1``.
    """
    if not isinstance(close, pd.Series):
        raise TypeError("close must be a pandas Series")
    stamps = naive_session_index(close.index)
    values = np.asarray(close.to_numpy(dtype=float), dtype=float)
    if len(stamps) == 0:
        raise ValueError("close series is empty")
    if len(stamps) != len(values):
        raise ValueError("close index length does not match values")
    if len(stamps) >= 2 and np.any(np.diff(stamps.asi8) <= 0):
        raise ValueError("close index must be strictly increasing and unique")
    start = pd.Timestamp(s1.WINDOW_START)
    keep = stamps >= start
    stamps = stamps[keep]
    values = values[keep]
    if len(stamps) == 0:
        raise ValueError(f"close series has no rows on or after {s1.WINDOW_START}")
    return pd.Series(values, index=stamps, dtype=float)


def _prospective_block(t: int, h: int, window: pd.Series) -> dict:
    """Unmerged block containing positional index ``t`` for horizon ``h``.

    ``k = (t - FIRST_TEST_IDX) // BLOCK_LEN + 1`` and the block starts at
    ``s0 = FIRST_TEST_IDX + BLOCK_LEN * (k - 1)``. A short tail stays its own
    block. ``training_end_asof`` is the session at ``s0 - h``, the last origin
    whose label is knowable under the purge ``idx + h <= s0``.
    """
    k = (t - s1.FIRST_TEST_IDX) // s1.BLOCK_LEN + 1
    s0 = s1.FIRST_TEST_IDX + s1.BLOCK_LEN * (k - 1)
    end_pos = s0 - int(h)
    if end_pos < 0 or end_pos >= len(window):
        raise ValueError(f"training end position {end_pos} is outside the window")
    return {
        "k": int(k),
        "s0": int(s0),
        "fit_block_id": f"b{k}",
        "training_end_asof": _date_str(window.index[end_pos]),
    }


def _design_matrices(cfg: dict, feat_matrix: dict, train_idx: np.ndarray, test_idx: np.ndarray):
    """Standardised train/test designs. ``None`` when a training std is 0.

    Binary callers add the intercept column. Quantile callers use the returned
    matrices as stage 1 does: no intercept column (the LP adds its own).
    """
    cols = [feat_matrix[name] for name in cfg["features"]]
    x_tr_raw = np.column_stack(cols)[train_idx]
    x_te_raw = np.column_stack(cols)[test_idx]
    _mean, std, x_tr, x_te = s1._standardise(x_tr_raw, x_te_raw)
    if (std == 0).any():
        return None
    return x_tr, x_te


def _score_config(
    cfg: dict,
    *,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    a_tr: np.ndarray,
    y_tr: np.ndarray,
    thin: bool,
    feat_matrix: dict,
    rv20_raw: np.ndarray,
) -> tuple[float | None, dict | None, str | None]:
    """One config at one test row. Returns (probability, quantile, reason).

    Mirrors the per-config branch of ``run_fits`` for ``test_idx`` of length 1.
    An issued binary returns a probability and a null quantile; an issued
    quantile returns the three clipped (Q3) or raw (Q0/Q1) levels and a null
    probability. An abstention returns nulls and the stage-1 reason string.
    """
    if thin and cfg["id"] != "B0":
        return None, None, "TRAINING_FOLD_THIN"
    try:
        if cfg["id"] == "B0":
            return float(s1.fit_b0(y_tr)), None, None
        if cfg["kind"] == "binary":
            designed = _design_matrices(cfg, feat_matrix, train_idx, test_idx)
            if designed is None:
                return None, None, "FEATURE_DEGENERATE"
            x_tr, x_te = designed
            design_tr = np.column_stack([np.ones(len(train_idx)), x_tr])
            design_te = np.column_stack([np.ones(len(test_idx)), x_te])
            beta = s1.fit_logistic(design_tr, y_tr, cfg["params"]["C"])
            probability = s1.expit(design_te @ beta)
            return float(probability[0]), None, None
        if cfg["id"] == "Q0":
            q0 = s1.fit_q0(a_tr)
            return None, {str(tau): float(q0[tau]) for tau in s1.TAUS}, None
        if cfg["id"] == "Q1":
            q0 = s1.fit_q0(a_tr)
            preds, _fb = s1.fit_q1(rv20_raw[train_idx], a_tr, rv20_raw[test_idx], q0)
            return None, {str(tau): float(preds[tau][0]) for tau in s1.TAUS}, None
        if cfg["id"] == "Q3-ALL":
            designed = _design_matrices(cfg, feat_matrix, train_idx, test_idx)
            if designed is None:
                return None, None, "FEATURE_DEGENERATE"
            x_tr, x_te = designed
            q_unclipped = {}
            for tau in s1.TAUS:
                intercept, beta = s1.fit_quantile_lp(x_tr, a_tr, tau)
                q_unclipped[tau] = x_te @ beta + intercept
            issued, clipped, reasons = s1.quantile_output_policy(
                q_unclipped[0.5], q_unclipped[0.8], q_unclipped[0.9]
            )
            if not bool(issued[0]):
                return None, None, str(reasons[0])
            q50, q80, q90 = clipped
            return None, {"0.5": float(q50[0]), "0.8": float(q80[0]), "0.9": float(q90[0])}, None
        raise AssertionError(f"unhandled configuration {cfg['id']}")
    except s1._FitFailure as exc:
        return None, None, exc.type


def score_asof(
    close: pd.Series,
    *,
    ticker: str | None = None,
    store_identity: str | None = None,
) -> list[dict]:
    """Score the last row of ``close`` for every horizon and issued config.

    No I/O, clock, git, or environment read. Pass ``ticker`` and
    ``store_identity`` to fill ``inputs_digest``; omit both for a pure parity
    call (the digest is null). An empty ``store_identity`` raises
    ``_DigestMissing``. ``t < FIRST_TEST_IDX`` raises ``ValueError``.
    """
    want_digest = ticker is not None or store_identity is not None
    if want_digest and (not isinstance(store_identity, str) or store_identity == ""):
        raise _DigestMissing("store_identity is empty")

    window = _prepare_close(close)
    t = len(window) - 1
    if t < s1.FIRST_TEST_IDX:
        raise ValueError(
            f"asof index t={t} is before FIRST_TEST_IDX={s1.FIRST_TEST_IDX}"
        )

    features = s1.build_features(window)
    labels = s1.build_labels(window)
    feat_matrix = {name: features[name].to_numpy(dtype=float) for name in s1.FEATURE_COLUMNS}
    rv20_raw = features["rv20"].to_numpy(dtype=float)
    idx_all = np.arange(len(window))
    rows: list[dict] = []

    for h in s1.HORIZONS:
        block = _prospective_block(t, h, window)
        s0 = block["s0"]
        candidates = idx_all[(idx_all >= s1.WARM_IDX) & (idx_all < s0) & (idx_all <= t - h)]
        train_idx = s1.purged_training_indices(s0, h, candidates)
        y = labels[h]["Y"].to_numpy(dtype=float, na_value=np.nan)
        a = labels[h]["A"].to_numpy(dtype=float)
        y_tr = y[train_idx]
        a_tr = a[train_idx]
        thin, _stats = s1.training_fold_is_thin(train_idx, y_tr)
        test_idx = np.array([t])
        digest = None
        if want_digest:
            digest = inputs_digest(
                window, t, h, ticker, store_identity, block["training_end_asof"]
            )
        for cfg in s1.CONFIGURATIONS:
            probability, quantile, reason = _score_config(
                cfg,
                train_idx=train_idx,
                test_idx=test_idx,
                a_tr=a_tr,
                y_tr=y_tr,
                thin=bool(thin),
                feat_matrix=feat_matrix,
                rv20_raw=rv20_raw,
            )
            config_id = _issued_config_id(cfg["id"])
            rows.append(
                {
                    "horizon": int(h),
                    "config_id": config_id,
                    "kind": cfg["kind"],
                    "is_gate": config_id in _GATE_IDS,
                    "population": POPULATION,
                    "probability": probability,
                    "quantile": quantile,
                    "abstention_reason": reason,
                    "fit_block_id": block["fit_block_id"],
                    "training_end_asof": block["training_end_asof"],
                    "inputs_digest": digest,
                }
            )
    return rows


def inputs_digest_payload(
    close_window: pd.Series,
    t: int,
    h: int,
    ticker: str,
    store_identity: str,
    training_end_asof: str,
) -> dict:
    """Canonical inputs_digest document. Raises ``_DigestMissing`` when it cannot.

    ``close`` and each feature value are ``repr(float(...))`` strings, matching
    the byte-for-byte formula the grader lane reimplements.
    """
    if not isinstance(store_identity, str) or store_identity == "":
        raise _DigestMissing("store_identity is empty")
    features = s1.build_features(close_window)
    close_at_t = float(close_window.iloc[t])
    if not math.isfinite(close_at_t):
        raise _DigestMissing("close is non-finite")
    feature_reprs: dict[str, str] = {}
    for name in s1.FEATURE_COLUMNS:
        value = float(features[name].iloc[t])
        if not math.isfinite(value):
            raise _DigestMissing(f"feature {name} is non-finite")
        feature_reprs[name] = repr(float(value))
    return {
        "asof": _date_str(close_window.index[t]),
        "close": repr(float(close_at_t)),
        "features": feature_reprs,
        "horizon": int(h),
        "store_identity": store_identity,
        "ticker": ticker,
        "training_end_asof": str(training_end_asof),
    }


def inputs_digest(
    close_window: pd.Series,
    t: int,
    h: int,
    ticker: str,
    store_identity: str,
    training_end_asof: str,
) -> str:
    """sha256 of the canonical inputs payload (sorted keys, compact separators)."""
    payload = inputs_digest_payload(close_window, t, h, ticker, store_identity, training_end_asof)
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_blob_sha(data: bytes) -> str:
    """Git blob object id of ``data``, computed in-process (no subprocess)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def recipe_fingerprint() -> str:
    """sha256 of the sorted ``path\\tblob`` listing plus the frozen prereg blob.

    File bytes are read from ``REPO_ROOT`` (tests may monkeypatch that global).
    """
    entries: list[tuple[str, str]] = []
    root = Path(REPO_ROOT)
    for rel in RECIPE_FILES:
        entries.append((rel, _git_blob_sha((root / rel).read_bytes())))
    entries.sort(key=lambda item: item[0])
    text = "".join(f"{path}\t{blob}\n" for path, blob in entries)
    text += f"prereg_blob\t{s1.PREREG_BLOB}\n"
    return hashlib.sha256(text.encode()).hexdigest()


def _prereg_matches() -> bool:
    path = Path(REPO_ROOT) / s1.PREREG_PATH
    try:
        blob = _git_blob_sha(path.read_bytes())
    except OSError:
        return False
    return blob == s1.PREREG_BLOB


def _utc_now() -> datetime:
    """Aware UTC clock. Tests monkeypatch this; callers never pass a timestamp."""
    return datetime.now(timezone.utc)


def _git_head() -> str:
    """``git rev-parse HEAD`` at ``REPO_ROOT``, or ``""`` when git cannot answer."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _stamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("clock must be timezone-aware")
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _next_session(asof: date) -> date:
    found = sessions_between(asof + timedelta(days=1), asof + timedelta(days=14))
    if not found:
        raise ValueError(f"no NYSE session within 14 days after {asof.isoformat()}")
    return found[0]


def _outside_issue_window(asof: date, issued_at: datetime) -> bool:
    """True when ``issued_at`` is before 17:00 ET on asof or at/after the next open.

    The next open is 09:30 America/New_York on the next date ``is_session``
    accepts. The stamp is never clamped into the window.
    """
    issued_et = issued_at.astimezone(ET)
    earliest = datetime.combine(asof, _SETTLE, tzinfo=ET)
    latest = datetime.combine(_next_session(asof), _OPEN, tzinfo=ET)
    return issued_et < earliest or issued_et >= latest


def _canonical_dumps(row: dict) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_obj(obj) -> str:
    encoded = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def durable_jsonl_prefix(data: bytes) -> bytes:
    """Bytes through the last complete, JSON-parsed line.

    A trailing partial — no terminating newline, or a final line that is not
    JSON — is excluded. Earlier lines are returned byte for byte.
    """
    if not data:
        return data
    if data.endswith(b"\n"):
        kept = data
    else:
        nl = data.rfind(b"\n")
        kept = b"" if nl < 0 else data[: nl + 1]
    if not kept:
        return kept
    body = kept[:-1]
    prev = body.rfind(b"\n")
    last = body[prev + 1 :]
    if not last.strip():
        return kept
    try:
        json.loads(last.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return b"" if prev < 0 else kept[: prev + 1]
    return kept


def _read_fd(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        block = os.read(fd, 1024 * 1024)
        if not block:
            break
        chunks.append(block)
    return b"".join(chunks)


def _keys_from_durable(data: bytes) -> set[tuple]:
    """Issue keys in a durable prefix. A line that does not parse is ignored."""
    keys: set[tuple] = set()
    for line in data.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(row, dict):
            continue
        try:
            horizon = row["horizon"]
            if isinstance(horizon, bool):
                continue
            keys.add((row["asof"], row["ticker"], int(horizon), row["config_id"]))
        except (KeyError, TypeError, ValueError):
            continue
    return keys


def _append_payload(path: Path, payload: bytes) -> None:
    """One ``O_APPEND`` ``os.write`` under an exclusive lock, after a torn-tail repair."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        raw = _read_fd(fd)
        durable = durable_jsonl_prefix(raw)
        if len(durable) != len(raw):
            os.ftruncate(fd, len(durable))
        if payload:
            written = os.write(fd, payload)
            if written != len(payload):
                raise OSError(f"short append on {path}: wrote {written} of {len(payload)} bytes")
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _append_line(path: Path, row: dict) -> None:
    """Append one canonical JSON line. A torn tail on ``path`` is truncated first."""
    _append_payload(path, (_canonical_dumps(row) + "\n").encode("utf-8"))


def _before_issued_append(rows: list[dict]) -> None:
    """Invoked after tonight's issue rows exist in memory and before they hit disk.

    The issue file has not been truncated or extended yet. Tests replace this
    to simulate a crash between those two moments.
    """
    del rows


def _append_issue_rows(path: Path, pending: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep-first append of one night. Key read and the single write share one lock.

    Returns ``(written, duplicates)``. A raise from ``_before_issued_append``
    leaves the file bytes unchanged.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        raw = _read_fd(fd)
        durable = durable_jsonl_prefix(raw)
        keys = _keys_from_durable(durable)
        fresh: list[dict] = []
        dupes: list[dict] = []
        for row in pending:
            key = (row["asof"], row["ticker"], int(row["horizon"]), row["config_id"])
            if key in keys:
                dupes.append(row)
                continue
            keys.add(key)
            fresh.append(row)
        _before_issued_append(fresh)
        if len(durable) != len(raw):
            os.ftruncate(fd, len(durable))
        if fresh:
            payload = b"".join((_canonical_dumps(row) + "\n").encode("utf-8") for row in fresh)
            written = os.write(fd, payload)
            if written != len(payload):
                raise OSError(f"short append on {path}: wrote {written} of {len(payload)} bytes")
        return fresh, dupes
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _parse_issued_at(value: object) -> datetime | None:
    if not isinstance(value, str) or value == "":
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment


def issued_row_admitted(row: object) -> bool:
    """Design §1.1. One failure excludes the row. No clock read and no git."""
    if not isinstance(row, dict):
        return False
    if row.get("schema") != ISSUE_SCHEMA:
        return False
    if row.get("evidence_class") != "GENUINELY_ISSUED":
        return False
    if row.get("writer_lane") != WRITER_LANE:
        return False
    if row.get("collect_lane_env") != WRITER_LANE:
        return False
    if row.get("writer_identity") != WRITER_IDENTITY:
        return False
    for flag in ("backfill", "rerun", "intraday"):
        if row.get(flag) is not False:
            return False
    code_sha = row.get("code_sha")
    if not isinstance(code_sha, str) or _SHA40.fullmatch(code_sha) is None:
        return False
    prereg = row.get("prereg_blob")
    if not isinstance(prereg, str) or _SHA40.fullmatch(prereg) is None:
        return False
    digest = row.get("inputs_digest")
    if not isinstance(digest, str) or _SHA64.fullmatch(digest) is None:
        return False
    asof_raw = row.get("asof")
    try:
        asof = date.fromisoformat(asof_raw) if isinstance(asof_raw, str) else None
    except ValueError:
        asof = None
    if asof is None or not is_session(asof):
        return False
    issued_at = _parse_issued_at(row.get("issued_at"))
    if issued_at is None or _outside_issue_window(asof, issued_at):
        return False
    for name in _GRADING_FIELDS:
        if row.get(name) is not None:
            return False
    return True


def _gate_attempt(
    *,
    asof: str | None,
    ticker: str,
    horizon: int | None,
    config_id: str | None,
    store_identity: str,
    reason: str,
) -> dict:
    return {
        "asof": asof,
        "ticker": ticker,
        "horizon": horizon,
        "config_id": config_id,
        "store_identity": store_identity,
        "reason": reason,
    }


def _refusal_row(
    *,
    reason: str,
    refused_at: str,
    asof: str | None,
    ticker: str,
    horizon: int | None,
    config_id: str | None,
    writer_lane: str,
    attempt: dict,
    population: str | None = None,
) -> dict:
    row = {
        "schema": REFUSAL_SCHEMA,
        "refused_at": refused_at,
        "reason": reason,
        "asof": asof,
        "ticker": ticker,
        "horizon": horizon,
        "config_id": config_id,
        "writer_lane": writer_lane,
        "attempt_digest": _sha256_obj(attempt),
    }
    # The P-active observer refusal names its population. Other refusals stay
    # on the §2.3 field set (no probability, no quantile).
    if population is not None:
        row["population"] = population
    return row


def _issue_row(
    payload: dict,
    *,
    asof: str,
    ticker: str,
    code_sha: str,
    fingerprint: str,
    issued_at: str,
    collect_lane: str,
) -> dict:
    return {
        "schema": ISSUE_SCHEMA,
        "evidence_class": "GENUINELY_ISSUED",
        "asof": asof,
        "ticker": ticker,
        "horizon": int(payload["horizon"]),
        "config_id": payload["config_id"],
        "population": POPULATION,
        "kind": payload["kind"],
        "is_gate": bool(payload["is_gate"]),
        "probability": payload["probability"],
        "quantile": payload["quantile"],
        "abstention_reason": payload["abstention_reason"],
        "inputs_digest": payload["inputs_digest"],
        "code_sha": code_sha,
        "recipe_fingerprint": fingerprint,
        "prereg_blob": s1.PREREG_BLOB,
        "prereg_path": s1.PREREG_PATH,
        "issued_at": issued_at,
        "writer_lane": WRITER_LANE,
        "writer_identity": WRITER_IDENTITY,
        "collect_lane_env": collect_lane,
        "backfill": False,
        "rerun": False,
        "intraday": False,
        "fit_block_id": payload["fit_block_id"],
        "training_end_asof": payload["training_end_asof"],
        "issue_receipt": {
            "contract": ISSUE_SCHEMA,
            "epoch": EPOCH,
            "issued_at": issued_at,
            "ledger_lane": WRITER_LANE,
            "first_writer_wins": True,
        },
        "realized_A": None,
        "Y": None,
        "graded_at": None,
        "grader_sha": None,
    }


def _summary(issued: int, duplicates: int, refusals: list[str], out_dir: Path) -> dict:
    return {
        "issued": int(issued),
        "duplicates": int(duplicates),
        "refusals": list(refusals),
        "out_dir": str(out_dir),
    }


def _asof_or_none(close) -> str | None:
    try:
        window = _prepare_close(close)
    except Exception:
        return None
    return _date_str(window.index[-1])


def _unwritten_refusal(
    *,
    reason: str,
    close,
    ticker: str,
    store_identity: str,
    writer_lane: str,
) -> dict:
    """§2.3 refusal returned to the caller. Nothing is created on disk."""
    asof = _asof_or_none(close)
    attempt = _gate_attempt(
        asof=asof,
        ticker=ticker,
        horizon=None,
        config_id=None,
        store_identity=store_identity,
        reason=reason,
    )
    return _refusal_row(
        reason=reason,
        refused_at=_stamp(_utc_now()),
        asof=asof,
        ticker=ticker,
        horizon=None,
        config_id=None,
        writer_lane=writer_lane,
        attempt=attempt,
    )


def issue(
    close: pd.Series,
    *,
    ticker: str,
    store_identity: str,
    out_dir: str | Path | None = None,
    code_sha: str | None = None,
) -> dict:
    """Append tonight's rows, or one whole-night refusal.

    ``code_sha`` is accepted only so a caller-supplied value can be refused.
    The recorded sha is always ``_git_head()``. The clock is ``_utc_now()``,
    read once immediately before the appends that follow a passing gate, and
    reused for every row and refusal in that call.

    Gates ``LANE`` and ``IDENTITY`` return a §2.3 refusal dict and do not
    create ``out_dir``. Later gates append one refusal and issue nothing.
    A call that passes the gates appends the issue rows (keep-first) and then
    exactly one ``OBSERVER_NOT_ON_MAIN`` refusal for the unissued P-active
    configs. INC is not issued and gets no row.
    """
    lane = os.environ.get(LANE_ENV)
    if lane != WRITER_LANE:
        return _unwritten_refusal(
            reason="LANE",
            close=close,
            ticker=ticker,
            store_identity=store_identity,
            writer_lane=lane if lane else "absent",
        )
    if os.environ.get(IDENTITY_ENV) != WRITER_IDENTITY:
        return _unwritten_refusal(
            reason="IDENTITY",
            close=close,
            ticker=ticker,
            store_identity=store_identity,
            writer_lane=WRITER_LANE,
        )
    # US_LANE=nightly does not arm this ledger. Any other value refuses.
    us_lane = os.environ.get("US_LANE")
    if us_lane is not None and us_lane != WRITER_LANE:
        return _unwritten_refusal(
            reason="LANE",
            close=close,
            ticker=ticker,
            store_identity=store_identity,
            writer_lane=us_lane if us_lane else "absent",
        )

    dest = Path(out_dir) if out_dir is not None else Path(REPO_ROOT) / "data" / "grey_deer_pullback"
    window = _prepare_close(close)
    asof = _as_date(window.index[-1])
    asof_s = asof.isoformat()
    reasons: list[str] = []

    def _write_refusal(
        reason: str,
        *,
        horizon: int | None = None,
        config_id: str | None = None,
        attempt: dict | None = None,
        population: str | None = None,
        refused_at: str | None = None,
    ) -> None:
        if attempt is None:
            attempt = _gate_attempt(
                asof=asof_s,
                ticker=ticker,
                horizon=horizon,
                config_id=config_id,
                store_identity=store_identity,
                reason=reason,
            )
        stamp = refused_at if refused_at is not None else _stamp(_utc_now())
        row = _refusal_row(
            reason=reason,
            refused_at=stamp,
            asof=asof_s,
            ticker=ticker,
            horizon=horizon,
            config_id=config_id,
            writer_lane=WRITER_LANE,
            attempt=attempt,
            population=population,
        )
        # The directory is created only once an append is about to happen.
        dest.mkdir(parents=True, exist_ok=True)
        _append_line(dest / REFUSAL_LOG_NAME, row)
        reasons.append(reason)

    if ticker != "SPY":
        _write_refusal("UNFROZEN_PANEL")
        return _summary(0, 0, reasons, dest)
    if not _prereg_matches():
        _write_refusal("PREREG_MISMATCH")
        return _summary(0, 0, reasons, dest)

    head = _git_head()
    if code_sha is not None or _SHA40.fullmatch(head) is None:
        _write_refusal("SHA_MISMATCH")
        return _summary(0, 0, reasons, dest)
    if not is_session(asof):
        _write_refusal("NOT_A_SESSION")
        return _summary(0, 0, reasons, dest)

    try:
        payloads = score_asof(window, ticker=ticker, store_identity=store_identity)
    except (_DigestMissing, s1.Blocked):
        _write_refusal("DIGEST_MISSING")
        return _summary(0, 0, reasons, dest)

    # One clock read for every row and refusal that follows, including a
    # backfill or clock refusal. Do not read it again and do not clamp it.
    issued_dt = _utc_now()
    issued_at = _stamp(issued_dt)
    if asof < expected_last_session(issued_dt):
        _write_refusal("BACKFILL_ASOF", refused_at=issued_at)
        return _summary(0, 0, reasons, dest)
    if _outside_issue_window(asof, issued_dt):
        _write_refusal("CLOCK", refused_at=issued_at)
        return _summary(0, 0, reasons, dest)

    fingerprint = recipe_fingerprint()
    pending = [
        _issue_row(
            payload,
            asof=asof_s,
            ticker=ticker,
            code_sha=head,
            fingerprint=fingerprint,
            issued_at=issued_at,
            collect_lane=lane,
        )
        for payload in payloads
    ]
    fresh, dupes = _append_issue_rows(dest / FORWARD_LOG_NAME, pending)
    for row in dupes:
        _write_refusal(
            "DUPLICATE_KEY",
            horizon=row["horizon"],
            config_id=row["config_id"],
            attempt=row,
            refused_at=issued_at,
        )
    issued_n = len(fresh)
    dup_n = len(dupes)

    blocked = [
        {"id": row["id"], "kind": row["kind"], "population": row["population"]}
        for row in s1.BLOCKED_CONFIG_ROWS
        if row.get("type") == "OBSERVER_NOT_ON_MAIN"
    ]
    _write_refusal(
        "OBSERVER_NOT_ON_MAIN",
        population="P-active",
        refused_at=issued_at,
        attempt={
            "asof": asof_s,
            "ticker": ticker,
            "horizon": None,
            "config_id": None,
            "population": "P-active",
            "blocked_configs": blocked,
        },
    )
    return _summary(issued_n, dup_n, reasons, dest)
