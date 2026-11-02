"""scripts/ops_train_flow_score.py — FS-4 flow-score trainer (ops lane, off-render).

OPS-LANE ONLY. NEVER wired into daily.yml or config/dag.yml.
Run manually after cohort stores are populated (FS-1 prerequisite).
Follows scripts/ops_flow_cohorts.py pattern incl. FLOW_SIGNALS_DIR env override.

CLI:
  python -m scripts.ops_train_flow_score --bucket {0_7,8_90,90p}
  python -m scripts.ops_train_flow_score --all
  python -m scripts.ops_train_flow_score --bucket 0_7 --dry-run
  python -m scripts.ops_train_flow_score --bucket 0_7 --verbose

PREREQUISITES:
  - config/flow_score.yml present and valid.
  - Cohort stores populated by scripts/ops_flow_cohorts.py:
      data/flow_signals/cohort_tape_recon.parquet (source='tape_recon')
      data/flow_signals/cohort_eod_proxy.parquet  (source='eod_proxy')
  - Grade store populated by engine/flow_signals_grade.py:
      data/flow_signals/grades.parquet
  - FLOW_SIGNALS_DIR env var overrides the default data/flow_signals/ path.

POPULATION SPEC (amendment §3.3):
  - Index-rooted events excluded unless prior-session OI > 500 (T-1, PIT).
  - 0DTE index excluded from 0_7 entirely.
  - Sources NEVER pooled; load_cohort() guards enforce single-source frames.

COHORT ROLES (amendment §3.1):
  - eod_proxy = pre-training/priors ONLY: may seed model priors via warm-start
    but NEVER appears in any calibration fit or holdout metric.
  - live_feed + tape_recon = serving-distribution cohorts; used for CV and
    calibration.

FEATURES (amendment §3.4 / FS-R9):
  - Ledger event-time columns only.
  - Quote-rule execution features legal (FS-R6(a)).
  - NO tape-signed direction feature or label.
  - NO outcome/grade-derived features (PIT).
  - Crowdedness features admitted as within-root/interaction inputs.

LABELS (amendment §2.1):
  - Decision ruler = excess-vs-SPY basis (spy_excess_{h} columns).
  - If spy_excess column absent, trainer HALTS — never silently substitutes
    absolute return.
  - Label = 1 if spy_excess > 0 on the primary horizon, else 0.

CV (amendment §4):
  - FS-5 selection executes the frozen 15 CPCV paths, C(6, 2), on v2 blocks.
  - Embargo H is max(BUCKET_HORIZONS[bucket]): 5, 21, or 126. Both sides of
    each held block. A v1 spec has no frozen CPCV geometry and does not fit.
  - Root exclusion, native-interval purge, and the embargo run before features.
  - Uniqueness for accepted FS-5 populations is uniqueness_weights_nyse_intervals.
    The legacy calendar helper remains for unrelated callers only.
  - Deflated statistics and the empirical gauntlet are not claimed here.

CALIBRATION (amendment §5):
  - Per-bucket isotonic on a TEMPORAL holdout from serving cohorts only.
  - ECE < 0.05 (10 equal-mass bins).
  - Brier < base-rate Brier.
  - Reliability monotone is necessary but not sufficient. scoring.enabled false,
    or an incomplete gauntlet, keeps deployable false. This trainer does not
    claim the gauntlet.
  - n floors stay 30 per population and 20 per era. Below either floor is a
    no-fit before features. effective_n is the native weight sum, never the
    raw row count.

ARTIFACT (data/flow_signals/models/flow_score_{bucket}_v{N}/):
  - model.joblib, calibrator.joblib, manifest.json
  - Manifest schema: flow_score.model_manifest/v1
  - GITIGNORED — never committed (A4).

VERDICT LAW:
  - This trainer prints NO gauntlet verdicts.
  - Never writes "validated" anywhere (CI-guarded).
  - manifest kill_eval is evidence, not a published verdict (FS-5 owns verdicts).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from lib.nyse_calendar import sessions_between
from lib.flow_score_geometry import (
    GeometryError,
    BUCKET_HORIZONS,
    CpcvPath,
    registered_bucket_horizons,
    assign_time_blocks,
    build_geometry_plan,
    bind_greeks_era,
    canonical_intervals,
    frozen_embargo_sessions,
    make_no_fit_health,
    parse_frozen_train_blocks,
    preflight_cpcv_paths,
    validate_population_partition,
    validate_split_geometry,
)
from lib.flow_score_admission import (
    AdmissionError,
    INDEX_ROOTS as _INDEX_ROOTS,
    SPEC_SCHEMA_V2,
    apply_population_filter,
    canonical_index_root,
    derived_model_bucket,
    validate_admission_study_identity,
    validate_admission_receipt,
    verify_raw_stage_receipts,
)

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

log = logging.getLogger(__name__)


# ── repo / path helpers ───────────────────────────────────────────────────────


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _flow_signals_dir() -> Path:
    env = os.environ.get("FLOW_SIGNALS_DIR")
    if env:
        p = Path(env)
    else:
        p = _repo_root() / "data" / "flow_signals"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _models_dir(cfg: dict) -> Path:
    md = cfg.get("models_dir", "data/flow_signals/models")
    p = _repo_root() / md if not Path(md).is_absolute() else Path(md)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── config loader ─────────────────────────────────────────────────────────────


def _load_config() -> dict:
    import yaml
    cfg_path = _repo_root() / "config" / "flow_score.yml"
    with cfg_path.open() as f:
        return yaml.safe_load(f)


def _available_grade_horizons(grades_df: pd.DataFrame) -> set[str]:
    return set(grades_df.columns)


def _registered_horizons(bucket: str) -> tuple[int, ...]:
    try:
        return BUCKET_HORIZONS[bucket]
    except KeyError as exc:
        raise GeometryError(f"identity_unknown_model_bucket:{bucket}") from exc


def _configured_horizons(cfg: dict) -> dict[str, tuple[int, ...]]:
    configured = cfg.get("bucket_horizons")
    if configured is None:
        return dict(BUCKET_HORIZONS)
    return {
        str(bucket): tuple(int(horizon) for horizon in horizons)
        for bucket, horizons in configured.items()
    }


def _detector_version() -> str:
    try:
        import yaml
        p = _repo_root() / "config" / "flow_detector.yml"
        with p.open() as f:
            return str(yaml.safe_load(f).get("version", "unknown"))
    except Exception:
        return "unknown"


# ── git sha helper ─────────────────────────────────────────────────────────────


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(_repo_root()), "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


# ── sha256 file hash ──────────────────────────────────────────────────────────


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── population filter ─────────────────────────────────────────────────────────
# Amendment §3.3 — Table-H index-root prefilter.

def _is_index_root(root: str | None) -> bool:
    """Return True if the canonical stripped root is an index instrument."""
    if root is None:
        return False
    return canonical_index_root(root) in _INDEX_ROOTS


# ── cohort loaders ─────────────────────────────────────────────────────────────
# Reuse ops_flow_cohorts.py load_cohort for single-source guard.


def _load_serving_cohorts(
    flow_dir: Path, bucket: str, cfg: dict, *, source: str, detector_version: str
) -> pd.DataFrame:
    """Load exactly the externally declared serving source and detector version."""
    from scripts.ops_flow_cohorts import load_cohort

    if source == "tape_recon":
        selected = load_cohort(flow_dir / "cohort_tape_recon.parquet")
    elif source == "live_feed":
        ledger_path = flow_dir / "ledger.parquet"
        selected = pd.read_parquet(ledger_path) if ledger_path.exists() else pd.DataFrame()
    else:
        raise AdmissionError("admission_source_unknown:" + source)
    if selected.empty:
        return pd.DataFrame()
    if "source" not in selected or "detector_version" not in selected:
        raise AdmissionError("admission_source_identity_fields_missing")
    # Identity is set by the externally accepted study, never by the frame.
    # Other source/version rows remain outside this selected immutable universe.
    return selected.loc[
        selected["source"].astype(str).eq(source)
        & selected["detector_version"].astype(str).eq(detector_version)
    ].copy()


def _load_eod_proxy(flow_dir: Path) -> pd.DataFrame:
    """Load eod_proxy cohort (priors only — NEVER in calibration/OOS, amendment §3.1)."""
    from scripts.ops_flow_cohorts import load_cohort

    path = flow_dir / "cohort_eod_proxy.parquet"
    df = load_cohort(path)
    if not df.empty and "source" in df.columns:
        sources = df["source"].unique().tolist()
        if sources != ["eod_proxy"]:
            raise ValueError(
                f"ops_train: unexpected sources in eod_proxy cohort: {sources}"
            )
    return df


def _check_no_eod_proxy_in_calibration(df: pd.DataFrame, context: str) -> None:
    """Raise if eod_proxy source is present in a calibration or OOS frame (amendment §3.1)."""
    if df.empty:
        return
    if "source" in df.columns and "eod_proxy" in df["source"].values:
        raise ValueError(
            f"ops_train: eod_proxy detected in {context}. "
            "eod_proxy must NEVER appear in calibration/holdout frames (amendment §3.1 / FS-R4)."
        )


# ── feature / label assembly ───────────────────────────────────────────────────


def _feature_columns(cfg: dict, bucket: str) -> list[str]:
    """Return the feature column list for a bucket, adding DTE interaction if configured."""
    cols = list(cfg.get("feature_columns", []))
    dte_interaction = cfg.get("dte_interaction", {})
    if dte_interaction.get(bucket, False):
        # DTE interaction term for 8_90 (amendment §2.1)
        # Computed as dte × premium_z (a cross-feature)
        if "dte_X_premium_z" not in cols:
            cols = cols + ["dte_X_premium_z"]
    return cols


# OA-1T — event-time measurements the live serving cohort must actually carry.
# Presence only. Adequacy (how many, how well calibrated) belongs to FS-5.
MEASURED_LIVE_FIELDS = (
    "at_ask_share",
    "at_bid_share",
    "aggression_share",
    "vol_gt_oi_ratio",
)


def _assert_live_feed_measured_features(
    df: pd.DataFrame, feature_cols: list[str],
) -> None:
    """Refuse to train when the live serving cohort carries no measured truth.

    ``_build_features`` fills an absent column with NaN. That is right for a
    sparse observation and dangerous for a whole cohort: the model trains, the
    metrics look ordinary, and the very features the config declares were never
    present. This is a structural presence check — no minimum N, percentage,
    AUC or ECE, and it enables nothing.
    """
    if "source" not in df.columns:
        return
    live = df[df["source"] == "live_feed"]
    if live.empty:
        return
    required = [name for name in MEASURED_LIVE_FIELDS if name in feature_cols]
    missing = [name for name in required if name not in live.columns]
    all_null = [
        name for name in required
        if name in live.columns and live[name].notna().sum() == 0
    ]
    if missing or all_null:
        raise ValueError(
            "ops_train: live_feed measured feature preflight failed "
            f"missing={missing} all_null={all_null}"
        )


def _build_features(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Build feature matrix from DataFrame.

    Delegates to lib.flow_score.build_interaction_features so the feature
    construction logic is shared between trainer and scorer (FS4-01 fix).

    - Computes dte_X_premium_z if present in feature_cols (treated as enabled).
    - All columns coerced to float; missing columns filled with NaN.
    - HistGradientBoostingClassifier handles NaN natively (no imputation leakage).
    - NO outcome/grade-derived features permitted (FS-R9 / amendment §3.4).
    - NO tape-signed direction features (FS-R6).
    """
    from lib.flow_score import build_interaction_features
    # dte_X_premium_z is in feature_cols only when dte_interaction is enabled for
    # this bucket (set by _feature_columns).  Pass dte_interaction_enabled=True so
    # the shared helper computes it — it checks column presence internally.
    dte_interaction_enabled = "dte_X_premium_z" in feature_cols
    return build_interaction_features(df, feature_cols, dte_interaction_enabled=dte_interaction_enabled)


def _build_label(df: pd.DataFrame, grades_df: pd.DataFrame, bucket: str, cfg: dict) -> pd.Series:
    """Build binary label from grades store (excess-vs-SPY basis, amendment §2.1).

    Decision ruler column per bucket (from config label_columns):
      0_7  → spy_excess_5
      8_90 → spy_excess_21
      90p  → spy_excess_63

    If the spy_excess column is absent from grades, HALTS with ValueError —
    never silently substitutes absolute return (amendment §2.1 deviation note).

    Returns pd.Series of 0.0/1.0 indexed by event_id, with NaN for rows where
    the grade is not yet available or is null.
    """
    label_cols = cfg.get("label_columns", {})
    label_col = label_cols.get(bucket)
    if not label_col:
        raise ValueError(f"ops_train: no label_column configured for bucket={bucket}")

    if grades_df.empty:
        return pd.Series(dtype=float)

    # Verify the column exists
    if label_col not in grades_df.columns:
        raise ValueError(
            f"ops_train: grade store missing label column '{label_col}' for bucket={bucket}. "
            f"Available columns: {list(grades_df.columns)}. "
            "DO NOT silently substitute absolute return — this is a registered deviation "
            "that must be recorded in the trainer manifest (amendment §2.1)."
        )

    # Join grades to events on event_id
    event_ids = df["event_id"] if "event_id" in df.columns else df.index.to_series()
    grade_sub = grades_df[["event_id", label_col, "graded_ok"]].copy()
    merged = pd.merge(
        pd.DataFrame({"event_id": event_ids}),
        grade_sub,
        on="event_id",
        how="left",
    )

    # Only use graded_ok=True rows
    ok_mask = merged["graded_ok"].fillna(False).astype(bool)
    excess = pd.to_numeric(merged[label_col], errors="coerce")
    # Label = 1 if excess > 0 (outperformed SPY), else 0
    label = (excess > 0).astype(float)
    label[~ok_mask | excess.isna()] = float("nan")
    label.index = merged["event_id"].values
    label.name = "label"
    return label


def _join_grade_boundaries(
    df: pd.DataFrame, grades_df: pd.DataFrame, bucket: str, cfg: dict
) -> pd.DataFrame:
    """Open grades only after source admission and bind the native bucket end."""
    label_col = cfg.get("label_columns", {}).get(bucket)
    if not label_col:
        raise ValueError(f"ops_train: no label_column configured for bucket={bucket}")
    horizons = _registered_horizons(bucket)
    if label_col != f"spy_excess_{horizons[0]}":
        raise ValueError("ops_train: registered_label_mismatch")
    end_cols = tuple(f"outcome_end_session_{horizon}" for horizon in horizons)
    excess_cols = tuple(f"spy_excess_{horizon}" for horizon in horizons)
    required = ("event_id", *excess_cols, "graded_ok", "fill_date", *end_cols)
    missing = [column for column in required if column not in grades_df.columns]
    if missing:
        raise ValueError("ops_train: grade boundaries missing: " + ",".join(missing))
    grade_subset = grades_df[list(required)].copy()
    if grade_subset["event_id"].astype(str).duplicated().any():
        raise ValueError("ops_train: duplicate_grade_event_id")
    joined = df.merge(grade_subset, on="event_id", how="left", suffixes=("", "_grade"))
    excess = pd.to_numeric(joined[label_col], errors="coerce")
    joined["_label"] = (excess > 0).astype(float)
    graded_ok = joined["graded_ok"].map(
        lambda value: (type(value) is bool or type(value) is np.bool_) and bool(value)
    )
    all_horizons_mature = pd.Series(True, index=joined.index)
    for column in excess_cols:
        all_horizons_mature &= np.isfinite(
            pd.to_numeric(joined[column], errors="coerce")
        )
    joined.loc[~graded_ok | ~all_horizons_mature, "_label"] = float("nan")
    # Receipt plans the existing registered convention; a grader may not shift
    # dates after the fact to rescue a late source receipt.
    if (
        "planned_fill_date" not in joined
        or "planned_outcome_end_sessions" not in joined
    ):
        raise ValueError("ops_train: admitted receipt missing planned boundaries")
    if (
        not joined["fill_date"]
        .astype(str)
        .eq(joined["planned_fill_date"].astype(str))
        .all()
    ):
        raise ValueError("ops_train: actual_fill_date_mismatch")
    for horizon, end_col in zip(horizons, end_cols):
        planned = joined["planned_outcome_end_sessions"].map(
            lambda value: value.get(str(horizon)) if isinstance(value, dict) else None
        )
        if not joined[end_col].astype(str).eq(planned.astype(str)).all():
            raise ValueError(
                f"ops_train: actual_outcome_end_session_mismatch:{horizon}"
            )
    joined["outcome_end_session"] = joined[f"outcome_end_session_{max(horizons)}"]
    return joined


# ── CV geometry ───────────────────────────────────────────────────────────────


def _assign_time_blocks(df: pd.DataFrame, n_groups: int, date_col: str = "session_date") -> pd.Series:
    """Assign complete canonical sessions to contiguous blocks or fail closed."""
    return assign_time_blocks(df, n_groups, date_col)


def _group_fold_splits(
    df: pd.DataFrame,
    k_folds: int,
    embargo: int,
    n_groups: int,
    underlying_col: str = "root",
    date_col: str = "session_date",
    random_seed: int = 42,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Produce root-disjoint, label-purged, session-embargoed ordered folds."""
    del random_seed
    if underlying_col != "root":
        raise GeometryError("identity_missing:root")
    if date_col != "session_date":
        raise GeometryError("identity_missing:session_date")
    if k_folds < 1 or n_groups < 1:
        raise GeometryError("fold_geometry_invalid")

    working = df.reset_index(drop=True).copy()
    working["time_block"] = _assign_time_blocks(working, n_groups, date_col)
    unique_sessions = sorted(set(pd.to_datetime(working[date_col]).dt.date))
    if len(unique_sessions) < k_folds:
        raise GeometryError(f"insufficient_sessions:{len(unique_sessions)}<{k_folds}")

    session_blocks = (
        working.assign(_session=pd.to_datetime(working[date_col]).dt.date)
        .groupby("_session", sort=False)["time_block"]
        .first()
        .sort_index()
    )
    ordered_blocks = list(dict.fromkeys(session_blocks.tolist()))
    if len(ordered_blocks) < k_folds:
        raise GeometryError(f"insufficient_time_blocks:{len(ordered_blocks)}<{k_folds}")
    block_fold = [
        fold_index * len(ordered_blocks) // k_folds
        for fold_index, block in enumerate(ordered_blocks)
    ]
    working["_fold"] = working["time_block"].map(dict(zip(ordered_blocks, block_fold)))

    intervals = canonical_intervals(working)
    model_buckets = set(working["model_bucket"].astype(str))
    if len(model_buckets) != 1:
        raise GeometryError(f"identity_mixed:model_bucket:{sorted(model_buckets)}")
    horizon_sessions = max(_registered_horizons(next(iter(model_buckets))))
    embargo_sessions = max(int(embargo), horizon_sessions)
    splits: list[tuple[np.ndarray, np.ndarray]] = []
    for fold_index in range(k_folds):
        validation_idx = np.flatnonzero(working["_fold"].eq(fold_index).to_numpy())
        if len(validation_idx) == 0:
            continue
        candidate_idx = np.flatnonzero(working["_fold"].ne(fold_index).to_numpy())
        validation_roots = set(intervals.iloc[validation_idx]["root"])
        train_idx = candidate_idx[
            ~intervals.iloc[candidate_idx]["root"]
            .isin(validation_roots)
            .to_numpy()
        ]
        validation_fill = intervals.iloc[validation_idx]["fill_session"].to_numpy(
            dtype="datetime64[D]"
        )
        validation_end = intervals.iloc[validation_idx]["end_session"].to_numpy(
            dtype="datetime64[D]"
        )
        train_fill = intervals.iloc[train_idx]["fill_session"].to_numpy(
            dtype="datetime64[D]"
        )
        train_end = intervals.iloc[train_idx]["end_session"].to_numpy(
            dtype="datetime64[D]"
        )
        train_overlap = (
            np.maximum(train_fill[:, None], validation_fill[None, :])
            <= np.minimum(train_end[:, None], validation_end[None, :])
        ).any(axis=1)
        train_idx = train_idx[~train_overlap]
        validation_union_start = int(
            intervals.iloc[validation_idx]["fill_position"].min()
        )
        train_idx = train_idx[
            intervals.iloc[train_idx]["end_position"].to_numpy(dtype=int)
            < validation_union_start - embargo_sessions
        ]
        if len(train_idx) == 0:
            continue
        validate_split_geometry(
            working,
            train_idx,
            validation_idx,
            embargo_sessions=embargo_sessions,
            horizon_sessions=horizon_sessions,
            intervals=intervals,
        )
        splits.append((train_idx, validation_idx))
    return splits


# ── CPCV paths counter ─────────────────────────────────────────────────────────


def _cpcv_path_count(n_groups: int, k_test: int) -> int:
    """C(n_groups, k_test) = number of CPCV selection paths."""
    from math import comb
    return comb(n_groups, k_test)


# ── model fit helper ──────────────────────────────────────────────────────────


def _fit_model(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    sample_weight: np.ndarray,
    params: dict,
    monotone_cols: dict[str, int] | None,
    feature_cols: list[str],
    random_seed: int,
) -> Any:
    """Fit a HistGradientBoostingClassifier.

    LAZY sklearn import (FS-R7).
    Monotone constraints applied only for mechanism-known features (amendment §4.5).
    """
    from sklearn.ensemble import HistGradientBoostingClassifier

    # Build monotone_cst: +1 or -1 per feature position; 0 = unconstrained.
    mono_cst = None
    if monotone_cols:
        mono_array = []
        for col in feature_cols:
            if col in monotone_cols:
                mono_array.append(monotone_cols[col])
            else:
                mono_array.append(0)
        if any(m != 0 for m in mono_array):
            mono_cst = tuple(mono_array)

    model_params = dict(params)
    model_params["random_state"] = random_seed
    if mono_cst is not None:
        model_params["monotonic_cst"] = mono_cst

    model = HistGradientBoostingClassifier(**model_params)
    model.fit(X_train, y_train, sample_weight=sample_weight)
    return model


# ── training loop ─────────────────────────────────────────────────────────────


def _expand_grid(grid: dict) -> list[dict]:
    """Expand a hyperparameter grid dict into a list of param dicts."""
    import itertools
    keys = list(grid.keys())
    values = [grid[k] if isinstance(grid[k], list) else [grid[k]] for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def _auc_score(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Compute AUC-ROC. Lazy sklearn import."""
    from sklearn.metrics import roc_auc_score
    try:
        if len(np.unique(y_true)) < 2:
            return float("nan")
        return float(roc_auc_score(y_true, y_score))
    except Exception:
        return float("nan")


def _strict_auc(y_true: np.ndarray, y_score: np.ndarray, sample_weights=None) -> float:
    """Two-class native-weighted AUC; invalid rows are never filtered."""
    from lib.flow_score import weighted_binary_metrics
    if sample_weights is None:
        sample_weights = np.ones(len(y_true), dtype=float)
    try:
        return weighted_binary_metrics(y_score, y_true, sample_weights)["auc"]
    except ValueError as exc:
        reason = "one_class_path" if len(np.unique(y_true)) < 2 else "cpcv_nonfinite_prediction"
        raise GeometryError(reason) from exc


def _validate_frozen_fit_config(cfg: dict) -> None:
    """A changed registration is a no-fit, never a smaller or different search."""
    expected = {
        "n_groups": 6, "k_test": 2, "random_seed": 42,
        "n_bins": 10, "ece_threshold": 0.05,
        "bucket_horizons": {"0_7": [5], "8_90": [21], "90p": [63, 126]},
        "embargo_days": {"0_7": 5, "8_90": 21, "90p": 126, "90p_secondary": 126},
        "n_floors": {"bucket": 30, "era_cell": 20},
        "monotone_constraints": {},
        "dte_interaction": {"0_7": False, "8_90": True, "90p": False},
        "hyperparameter_grid": {
            "learning_rate": [0.02, 0.05, 0.1, 0.2], "max_iter": [200, 400],
            "max_leaf_nodes": [15, 31, 63], "min_samples_leaf": 20,
            "max_bins": 255, "early_stopping": False, "class_weight": "balanced",
        },
    }
    for key, value in expected.items():
        # JSON comparison distinguishes booleans from numeric lookalikes.
        if json.dumps(cfg.get(key), sort_keys=True) != json.dumps(value, sort_keys=True):
            raise GeometryError(f"frozen_config_drift:{key}")


def _cpcv_variants(cfg: dict, bucket: str) -> list[tuple[str, list[str]]]:
    """Frozen feature variants. 8_90 executes OFF and ON; other buckets execute one."""
    base = [
        column
        for column in list(cfg.get("feature_columns") or [])
        if column != "dte_X_premium_z"
    ]
    if cfg.get("dte_interaction", {}).get(bucket, False):
        return [("off", list(base)), ("on", list(base) + ["dte_X_premium_z"])]
    return [("off", list(base))]


def _align_native_weights(frame: pd.DataFrame, weights: pd.Series) -> np.ndarray:
    """Align native weights to rows. Missing or non-finite weights are a no-fit."""
    event_ids = frame["event_id"].astype(str)
    aligned = weights.reindex(event_ids.to_numpy())
    values = pd.to_numeric(aligned, errors="coerce").to_numpy(dtype=float)
    if (
        len(values) != len(frame)
        or not np.isfinite(values).all()
        or (values <= 0).any()
        or (values > 1).any()
    ):
        raise GeometryError("uniqueness_weight_nonfinite")
    return values


def _population_support(
    frame: pd.DataFrame, weights: np.ndarray, era_floor: int,
) -> dict[str, Any]:
    """Native support and the explicit booked registry; no pooled era substitute."""
    from lib.flow_score import strict_weighted_binary_inputs
    frame = bind_greeks_era(frame)
    _, _, weights = strict_weighted_binary_inputs(
        np.zeros(len(frame)), np.zeros(len(frame)), weights,
    )
    sessions = pd.to_datetime(frame["session_date"], errors="raise").dt.date
    roots = frame["root"].astype(str).str.strip().str.upper()
    fills = pd.to_datetime(frame["fill_date"], errors="raise").dt.date
    record = {
        "raw_rows": int(len(frame)),
        "distinct_sessions": int(sessions.nunique()),
        "distinct_root_sessions": int(pd.Series(list(zip(fills, roots))).nunique()),
        "effective_n": math.fsum(weights), "eras": [],
    }
    for era in ("2017-19", "2020-22", "2023+"):
        mask = frame["era"].eq(era).to_numpy()
        n = math.fsum(weights[mask])
        present = bool(mask.any())
        record["eras"].append({
            "era": era, "booked": era != "2017-19",
            "coverage": ("partial_2022_only" if era == "2020-22" else
                         "unbooked_reservable" if era == "2017-19" else "registered"),
            "status": ("present" if present else
                       "building_history_unfilled" if era != "2017-19" else "unbooked"),
            "raw_rows": int(mask.sum()),
            "distinct_sessions": int(sessions[mask].nunique()),
            "distinct_root_sessions": int(pd.Series(list(zip(fills[mask], roots[mask]))).nunique()),
            "effective_n": n,
            "era_sparse": present and n < era_floor,
        })
    return record


def _run_cpcv_selection(
    train_df: pd.DataFrame,
    paths: tuple[CpcvPath, ...] | list[CpcvPath],
    variants: list[tuple[str, list[str]]],
    grid: list[dict],
    sample_weights: np.ndarray,
    monotone_cfg: dict[str, int] | None,
    random_seed: int,
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fit every frozen setting on every path. Any failure aborts the search.

    Tie break is the frozen order: variant OFF before ON, then grid order.
    An equal AUC does not replace the earlier setting. No path is skipped.
    """
    if receipt is None:
        receipt = {}
    receipt.update({
        "attempted_fits": 0, "executed_fits": 0, "evaluated_fits": 0,
        "executed_paths": 0, "executed_variants": 0, "held_sets": [],
        "planned_fits": len(grid) * len(variants) * len(paths),
        "planned_paths": len(paths), "planned_variants": len(variants),
        "grid_cardinality": len(grid),
    })
    if len(paths) != 15:
        raise GeometryError("cpcv_path_set_invalid")
    if not grid or not variants:
        raise GeometryError("cpcv_grid_empty")
    event_ids = train_df["event_id"].astype(str).tolist()
    position = {event_id: index for index, event_id in enumerate(event_ids)}
    if len(position) != len(event_ids):
        raise GeometryError("identity_duplicate_event_id")
    labels = train_df["_label"].to_numpy(dtype=float)
    from lib.flow_score import strict_weighted_binary_inputs
    _, labels, sample_weights = strict_weighted_binary_inputs(
        np.zeros(len(labels)), labels, sample_weights,
    )
    best: dict[str, Any] | None = None
    executed_variants: set[str] = set()
    executed_paths: set[tuple[int, ...]] = set()
    for variant_name, columns in variants:
        features = _build_features(train_df, columns)
        if list(features.columns) != list(columns):
            raise GeometryError("cpcv_feature_order_mismatch")
        for params in grid:
            path_aucs: list[float] = []
            for path in paths:
                try:
                    train_index = np.asarray([position[event_id] for event_id in path.train_ids], dtype=int)
                    validation_index = np.asarray(
                        [position[event_id] for event_id in path.validation_ids], dtype=int
                    )
                except KeyError as exc:
                    raise GeometryError("cpcv_path_id_missing") from exc
                receipt["attempted_fits"] += 1
                model = _fit_model(
                    features.iloc[train_index],
                    labels[train_index],
                    sample_weights[train_index],
                    params,
                    monotone_cfg,
                    columns,
                    random_seed,
                )
                receipt["executed_fits"] += 1
                executed_paths.add(tuple(path.held))
                executed_variants.add(variant_name)
                receipt["executed_paths"] = len(executed_paths)
                receipt["executed_variants"] = len(executed_variants)
                receipt["held_sets"] = [list(held) for held in sorted(executed_paths)]
                probabilities = np.asarray(model.predict_proba(features.iloc[validation_index]))
                if probabilities.ndim != 2 or probabilities.shape[1] < 2:
                    raise GeometryError("cpcv_nonfinite_prediction")
                positive = np.asarray(probabilities[:, 1], dtype=float)
                path_aucs.append(_strict_auc(labels[validation_index], positive, sample_weights[validation_index]))
                receipt["evaluated_fits"] += 1
            executed_variants.add(variant_name)
            mean_auc = math.fsum(path_aucs) / len(path_aucs)
            if not math.isfinite(mean_auc):
                raise GeometryError("cpcv_nonfinite_auc")
            if best is None or mean_auc > best["mean_auc"]:
                best = {
                    "variant": variant_name,
                    "params": dict(params),
                    "feature_columns": list(columns),
                    "mean_auc": mean_auc,
                }
    if best is None:
        raise GeometryError("cpcv_selection_empty")
    receipt.update({
        "selected_variant": best["variant"],
        "selected_params": best["params"],
        "selected_feature_columns": best["feature_columns"],
        "selected_mean_auc": best["mean_auc"],
    })
    return receipt



def train_bucket(
    bucket: str,
    cfg: dict,
    flow_dir: Path,
    dry_run: bool = False,
    stage_receipt_resolver: Callable[[str], bytes] | None = None,
) -> dict | None:
    """Train and calibrate a flow-score model for one bucket.

    Returns an explicit health/selection receipt. The unresolved weighted-bin
    method cannot write a model artifact or claim calibration readiness.

    Source-only admission and original stage verification precede grades.
    Every frozen member must mature at its predeclared native fill/end sessions.
    The four ordered root-disjoint populations then pass unchanged FS-5
    geometry, embargo, N-floor, calibration and final-OOS laws before fitting.
    """
    log.info("ops_train: starting bucket=%s, dry_run=%s", bucket, dry_run)

    partition_path = flow_dir / "fs5_partition.json"
    if not partition_path.exists():
        log.warning("ops_train[%s]: no FS-5 partition receipt — building history/no-fit", bucket)
        return make_no_fit_health("building_history/method_geometry_unavailable")

    # The external frozen binding chooses the complete source universe before
    # any cohort is loaded or combined.  Disk contents cannot choose a source.
    try:
        partition = json.loads(partition_path.read_text())
        expected_study = cfg.get("fs5_admission_studies", {}).get(bucket)
        study = validate_admission_study_identity(
            partition,
            bucket=bucket,
            validation_at=pd.Timestamp.now(tz="UTC"),
            expected_study=expected_study,
        )
        serving_df = _load_serving_cohorts(
            flow_dir,
            bucket,
            cfg,
            source=str(study["source"]),
            detector_version=str(study["detector_version"]),
        )
    except (AdmissionError, ValueError, json.JSONDecodeError) as exc:
        log.warning("ops_train[%s]: source identity unavailable: %s", bucket, exc)
        return make_no_fit_health(f"method_geometry_unavailable:{exc}")
    if serving_df.empty:
        log.warning("ops_train[%s]: selected serving source is empty", bucket)
        return make_no_fit_health("building_history/selected_source_unavailable")
    _check_no_eod_proxy_in_calibration(serving_df, context="serving cohort (train_bucket)")

    if "dte_bucket" not in serving_df.columns:
        return make_no_fit_health(
            "method_geometry_unavailable:source_dte_bucket_missing"
        )
    source_df = serving_df

    # The receipt is the outcome-blind gate. Census comparison uses the full
    # declared source, before the DTE slice and the index population filter.
    # Do not stat or read grades until that gate passes.
    try:
        if stage_receipt_resolver is None:

            def stage_receipt_resolver(key: str) -> bytes:
                # Lazily reached only after structural membership validation;
                # reread raw bytes and never restamp source_stage_observed_at.
                from collectors.flow_signals import _r2_bucket, _r2_client

                source_client, source_bucket = _r2_client(), _r2_bucket()
                if source_client is None:
                    raise AdmissionError("admission_raw_stage_resolver_unavailable")
                return source_client.get_object(Bucket=source_bucket, Key=key)[
                    "Body"
                ].read()

        admitted = validate_admission_receipt(
            partition,
            source_df,
            bucket=bucket,
            validation_at=pd.Timestamp.now(tz="UTC"),
            expected_study=expected_study,
            stage_receipt_resolver=stage_receipt_resolver,
        )
    except (AdmissionError, ValueError, json.JSONDecodeError) as exc:
        log.warning("ops_train[%s]: source admission unavailable: %s", bucket, exc)
        return make_no_fit_health(f"method_geometry_unavailable:{exc}")

    # Artifact stats keep the incumbent DTE slice and index filter. The model
    # bucket is the derived one. A contradictory source column is not trusted.
    serving_df = source_df.loc[
        source_df["dte_bucket"].map(derived_model_bucket).eq(bucket)
    ].copy()
    if "model_bucket" in serving_df.columns:
        declared = serving_df["model_bucket"].map(
            lambda value: "" if value is None or pd.isna(value) else str(value).strip()
        )
        if declared.ne("").any() and not declared.loc[declared.ne("")].eq(bucket).all():
            return make_no_fit_health(
                "method_geometry_unavailable:source_model_bucket_mismatch"
            )
    else:
        serving_df["model_bucket"] = bucket
    if serving_df.empty:
        log.warning("ops_train[%s]: no rows after dte_bucket filter — skipping", bucket)
        return None
    serving_df, pop_stats = apply_population_filter(serving_df, bucket)
    log.info(
        "ops_train[%s]: population filter: input=%d, excluded_index=%d, "
        "readmitted_oi=%d, output=%d",
        bucket, pop_stats["total_input"], pop_stats["index_excluded_n"],
        pop_stats["oi_readmitted_n"], pop_stats["total_output"],
    )

    # Source admission must pass first; configuration drift cannot reach grade,
    # feature, estimator or calibration I/O for a v2 study.
    if partition.get("study_spec", {}).get("schema") == SPEC_SCHEMA_V2:
        try:
            _validate_frozen_fit_config(cfg)
        except (GeometryError, ValueError, TypeError) as exc:
            return make_no_fit_health(f"method_geometry_unavailable:{exc}")
    try:
        configured_horizons = _configured_horizons(cfg)
        if configured_horizons != dict(BUCKET_HORIZONS):
            raise GeometryError("bucket_horizon_contract_mismatch")
    except (GeometryError, ValueError, TypeError, AttributeError) as exc:
        return make_no_fit_health(f"method_geometry_unavailable:{exc}")
    required_horizons = _registered_horizons(bucket)
    embargo_days = max(
        int(cfg.get("embargo_days", {}).get(bucket, 0)),
        max(required_horizons),
    )
    grades_path = flow_dir / "grades.parquet"
    if not grades_path.exists():
        return make_no_fit_health("building_history/grades_unavailable")
    grades_df = pd.read_parquet(grades_path)
    try:
        labeled = _join_grade_boundaries(admitted, grades_df, bucket, cfg)
    except ValueError as exc:
        return make_no_fit_health(f"method_geometry_unavailable:{exc}")
    # Complete prospective cohort only: no mature-member dropping or expansion.
    if labeled["_label"].isna().any():
        return make_no_fit_health("building_history/frozen_cohort_not_fully_mature")
    train_df = labeled[labeled["population"] == "train"].copy()
    cal_fit_df = labeled[labeled["population"] == "calibration_fit"].copy()
    cal_eval_df = labeled[labeled["population"] == "calibration_eval"].copy()
    final_oos_df = labeled[labeled["population"] == "final_oos"].copy()

    # Existing immutable FS-5 geometry remains the final interval/embargo law.
    try:
        plans = {
            name: build_geometry_plan(frame, model_bucket=bucket)
            for name, frame in (
                ("train", train_df),
                ("calibration_fit", cal_fit_df),
                ("calibration_eval", cal_eval_df),
                ("final_oos", final_oos_df),
            )
        }
        validate_population_partition(
            plans,
            requested_bucket=bucket,
            horizon_columns=_available_grade_horizons(grades_df),
        )
    except GeometryError as exc:
        log.warning(
            "ops_train[%s]: invalid FS-5 partition — building history/no-fit: %s",
            bucket,
            exc,
        )
        return make_no_fit_health(f"method_geometry_unavailable:{exc}")

    # v1 receipts stay admissible through maturity and the existing geometry
    # law, then fail closed. Exact frozen CPCV blocks are required before
    # features, calibrators, selection, or a final model.
    study_spec = partition.get("study_spec") if isinstance(partition, dict) else None
    if (
        not isinstance(study_spec, dict)
        or study_spec.get("schema") != SPEC_SCHEMA_V2
    ):
        return make_no_fit_health(
            "method_geometry_unavailable:frozen_cpcv_geometry_missing"
        )

    bucket_floor, era_floor = 30, 20
    population_support: dict[str, Any] = {}
    sample_weights: np.ndarray
    paths: tuple[CpcvPath, ...]
    try:
        from lib.flow_score import uniqueness_weights_nyse_intervals

        embargo_h = frozen_embargo_sessions(bucket)
        train_window = study_spec["populations"]["train"]["window"]
        window_start = pd.Timestamp(train_window["start"])
        window_end = pd.Timestamp(train_window["end"])
        if window_start.tzinfo is None or window_end.tzinfo is None:
            raise GeometryError("train_block_window_mismatch")
        outer = [
            session
            for session in sessions_between(
                window_start.tz_convert("UTC").date(),
                window_end.tz_convert("UTC").date(),
            )
        ]
        if not outer:
            raise GeometryError("train_block_window_mismatch")
        blocks = parse_frozen_train_blocks(
            study_spec.get("train_blocks"),
            outer_first=outer[0],
            outer_last=outer[-1],
            train_roots={
                str(root).strip().upper()
                for root in study_spec["populations"]["train"]["roots"]
            },
        )
        paths = preflight_cpcv_paths(
            train_df, blocks, embargo_h, label_column="_label"
        )
        weight_frames = {
            "train": train_df,
            "calibration_fit": cal_fit_df,
            "calibration_eval": cal_eval_df,
            "final_oos": final_oos_df,
        }
        aligned: dict[str, np.ndarray] = {}
        for name, frame in weight_frames.items():
            aligned[name] = _align_native_weights(
                frame, uniqueness_weights_nyse_intervals(frame)
            )
            population_support[name] = _population_support(
                frame, aligned[name], era_floor
            )
            effective = population_support[name]["effective_n"]
            if effective < bucket_floor:
                raise GeometryError(
                    "BELOW-FLOOR:"
                    f"{name}:effective_n={effective:.6f}<bucket_floor={bucket_floor}"
                )
            for era in population_support[name]["eras"]:
                if era["era_sparse"]:
                    raise GeometryError(
                        "ERA-SPARSE:"
                        f"{name}:{era['era']}:effective_n={era['effective_n']:.6f}"
                        f"<era_floor={era_floor}"
                    )
        sample_weights = aligned["train"]
    except (GeometryError, ValueError) as exc:
        health = make_no_fit_health(f"method_geometry_unavailable:{exc}")
        health["population_support"] = population_support
        return health

    variants = _cpcv_variants(cfg, bucket)
    hparam_grid = _expand_grid(cfg.get("hyperparameter_grid", {}))
    planned_fits = len(hparam_grid) * len(variants) * 15
    if dry_run:
        log.info(
            "ops_train[%s]: dry_run — executed_fits=0 planned_fits=%d",
            bucket,
            planned_fits,
        )
        return {
            "bucket": bucket,
            "dry_run": True,
            "health": "dry_run",
            "status": "not_executed",
            "deployable": False,
            "building_history": True,
            "gauntlet_complete": False,
            "executed_fits": 0,
            "planned_fits": planned_fits,
            "planned_paths": 15,
            "planned_variants": len(variants),
            "population_support": population_support,
        }

    monotone_cfg = cfg.get("monotone_constraints", {})
    random_seed = int(cfg.get("random_seed", 42))
    selection: dict[str, Any] = {"executed_fits": 0, "attempted_fits": 0}
    try:
        _assert_live_feed_measured_features(
            labeled, [column for _, columns in variants for column in columns]
        )
        selection = _run_cpcv_selection(
            train_df,
            paths,
            variants,
            hparam_grid,
            sample_weights,
            monotone_cfg,
            random_seed,
            receipt=selection,
        )
    except Exception as exc:
        health = make_no_fit_health(f"method_geometry_unavailable:cpcv_selection_failed:{exc}")
        health["population_support"] = population_support
        health["selection_receipt"] = selection
        health["executed_fits"] = selection["executed_fits"]
        return health

    feature_cols = list(selection["selected_feature_columns"])
    best_params = dict(selection["selected_params"])
    best_auc = float(selection["selected_mean_auc"])
    n_trials = int(selection["executed_fits"])
    log.info(
        "ops_train[%s]: selected variant=%s params=%s mean_auc=%.6f executed_fits=%d",
        bucket,
        selection["selected_variant"],
        best_params,
        best_auc,
        n_trials,
    )

    # ── final model fit on full training set ─────────────────────────────────
    selection["final_fit_attempted"] = True
    selection["final_fit_complete"] = False
    try:
        X_train_all = _build_features(train_df, feature_cols)
        y_train_all = train_df["_label"].astype(float).values
        final_model = _fit_model(
            X_train_all, y_train_all, sample_weights,
            best_params, monotone_cfg, feature_cols, random_seed,
        )
        selection["final_fit_complete"] = True
    except Exception as exc:
        health = make_no_fit_health(f"method_geometry_unavailable:final_fit_failed:{exc}")
        health["population_support"] = population_support
        health["selection_receipt"] = selection
        health["executed_fits"] = selection["executed_fits"]
        return health

    # The weighted-bin/tie convention has no registered closure. Report
    # diagnostics with the actual native weights, but produce no model artifact.
    try:
        diagnostics = _weighted_calibration_diagnostics(
            final_model, cal_fit_df, cal_eval_df, feature_cols,
            aligned["calibration_fit"], aligned["calibration_eval"],
        )
        reason = "CALIBRATION_INSUFFICIENT:weighted_bin_method_unavailable"
    except Exception as exc:
        diagnostics = {}
        reason = f"CALIBRATION_INSUFFICIENT:calibration_failed:{exc}"
    health = make_no_fit_health(reason)
    health.update({
        "health": "calibration_insufficient", "calibration_ready": False,
        "gauntlet_complete": False, "calibration": diagnostics,
        "population_support": population_support, "selection_receipt": selection,
        "executed_fits": selection["executed_fits"],
        "planned_fits": selection["planned_fits"],
        "executed_paths": selection["executed_paths"],
        "executed_variants": selection["executed_variants"],
    })
    return health


def _weighted_calibration_diagnostics(model, fit_frame, eval_frame, columns, fit_weights, eval_weights):
    """Diagnostic-only isotonic and metrics; no unresolved ECE gate is asserted."""
    from sklearn.isotonic import IsotonicRegression
    from lib.flow_score import strict_weighted_binary_inputs, weighted_binary_metrics
    _check_no_eod_proxy_in_calibration(fit_frame, context="calibration fit")
    _check_no_eod_proxy_in_calibration(eval_frame, context="calibration evaluation")
    fit_frame, eval_frame = bind_greeks_era(fit_frame), bind_greeks_era(eval_frame)
    fit_pred, fit_y, fit_weights = strict_weighted_binary_inputs(
        model.predict_proba(_build_features(fit_frame, columns))[:, 1],
        fit_frame["_label"].to_numpy(), fit_weights,
    )
    eval_pred, eval_y, eval_weights = strict_weighted_binary_inputs(
        model.predict_proba(_build_features(eval_frame, columns))[:, 1],
        eval_frame["_label"].to_numpy(), eval_weights,
    )
    if len(np.unique(fit_y)) != 2 or len(np.unique(eval_y)) != 2:
        raise GeometryError("one_class_calibration_population")
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(fit_pred, fit_y, sample_weight=fit_weights)
    calibrated = calibrator.predict(eval_pred)
    metrics = weighted_binary_metrics(calibrated, eval_y, eval_weights)
    newest = eval_frame["era"].eq("2023+").to_numpy()
    newest_auc = None
    if newest.any() and len(np.unique(eval_y[newest])) == 2:
        newest_auc = _strict_auc(eval_y[newest], eval_pred[newest], eval_weights[newest])
    return {
        **metrics, "ece": None, "ece_status": "weighted_bin_method_unavailable",
        "calibration_ready": False, "auc_newest_era": newest_auc,
        "auc_newest_era_status": "available" if newest_auc is not None else "unavailable",
        "n_cal_fit": len(fit_y), "n_cal_eval": len(eval_y),
        "effective_n_cal_fit": math.fsum(fit_weights),
        "effective_n_cal_eval": math.fsum(eval_weights),
    }


def _write_artifact(
    *,
    bucket: str,
    cfg: dict,
    flow_dir: Path,
    model: Any,
    calibrator: Any,
    deployable: bool,
    deploy_reason: str,
    serving_df: pd.DataFrame,
    labeled: pd.DataFrame,
    pop_stats: dict,
    base_rate: float,
    calibration_metrics: dict,
    kill_eval: dict,
    n_trials: int,
    feature_cols: list[str],
    best_params: dict | None = None,
    dry_run: bool = False,
    population_support: dict | None = None,
    selection_receipt: dict | None = None,
) -> dict:
    """Write model artifact directory: model.joblib, calibrator.joblib, manifest.json.

    Manifest schema: flow_score.model_manifest/v1 (amendment §4 artifact spec).
    NEVER writes the word "validated" (CI-guarded).
    """
    # Legacy research callers retain their non-serving artifact format. An
    # FS5 selection receipt must never enter it while calibration is unresolved,
    # even if a future caller accidentally restores the old trainer call.
    if selection_receipt is not None:
        health = make_no_fit_health("CALIBRATION_INSUFFICIENT:weighted_bin_method_unavailable")
        health.update({
            "calibration_ready": False, "gauntlet_complete": False,
            "selection_receipt": dict(selection_receipt),
            "executed_fits": int(selection_receipt.get("executed_fits", 0)),
        })
        return health
    deployable = False
    calibrator = None
    deploy_reason = "; ".join(filter(None, (deploy_reason, "gauntlet_incomplete")))
    models_dir = _models_dir(cfg)

    # Find next version number
    prefix = f"flow_score_{bucket}_v"
    existing_versions = []
    for d in models_dir.iterdir() if models_dir.exists() else []:
        if d.is_dir() and d.name.startswith(prefix):
            try:
                existing_versions.append(int(d.name[len(prefix):]))
            except ValueError:
                continue
    version = (max(existing_versions) + 1) if existing_versions else 1

    artifact_dir = models_dir / f"{prefix}{version}"

    if dry_run:
        log.info("ops_train[%s]: dry_run — would write artifact to %s", bucket, artifact_dir)
        return {
            "bucket": bucket,
            "model_version": version,
            "deployable": deployable,
            "dry_run": True,
        }

    import joblib

    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.joblib"
    calibrator_path = artifact_dir / "calibrator.joblib"

    # Save model
    model_sha: str = ""
    if model is not None:
        joblib.dump(model, model_path)
        model_sha = _sha256_file(model_path)
    else:
        # Write a null placeholder so artifact dir is complete
        joblib.dump({"null_model": True, "reason": deploy_reason}, model_path)
        model_sha = _sha256_file(model_path)

    # Save calibrator
    cal_sha: str = ""
    if calibrator is not None:
        joblib.dump(calibrator, calibrator_path)
        cal_sha = _sha256_file(calibrator_path)
    else:
        joblib.dump({"null_calibrator": True}, calibrator_path)
        cal_sha = _sha256_file(calibrator_path)

    # Cohort summary
    source_summary: dict = {}
    if "source" in serving_df.columns:
        for src, grp in serving_df.groupby("source"):
            source_summary[str(src)] = {
                "rows": int(len(grp)),
                "raw_rows": int(len(grp)),
                "eras": int(grp["era"].nunique()) if "era" in grp.columns else None,
            }

    # CV params for manifest. The selected column list, not the config flag,
    # decides whether the interaction term is on. The scorer reads both and
    # they have to agree.
    k_folds = cfg.get("k_folds", 5)
    n_groups = cfg.get("n_groups", 6)
    k_test = cfg.get("k_test", 2)
    hparam_grid = _expand_grid(cfg.get("hyperparameter_grid", {}))
    dte_interaction = cfg.get("dte_interaction", {})
    n_interaction_variants = 2 if dte_interaction.get(bucket, False) else 1
    n_cpcv_paths = _cpcv_path_count(n_groups, k_test)
    declared_total = len(hparam_grid) * n_interaction_variants * n_cpcv_paths
    executed_fits = 0
    planned_fits = declared_total
    reported_total = n_trials
    selected_interaction = "dte_X_premium_z" in feature_cols

    manifest: dict = {
        "schema": "flow_score.model_manifest/v1",
        "bucket": bucket,
        "model_version": version,
        "detector_version": _detector_version(),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "cohort_summary": {
            "source": source_summary,
            "total_labeled_rows": int(len(labeled)),
            "raw_rows": int(len(labeled)),
            "base_rate": float(base_rate),
            "population_support": population_support or {},
        },
        "population": pop_stats,
        "cv_params": {
            "k_folds": k_folds,
            "embargo_days": cfg.get("embargo_days", {}).get(bucket, 21),
            "n_groups": n_groups,
            "k_test": k_test,
            "n_cpcv_paths": n_cpcv_paths,
            "feature_columns": list(feature_cols),
            "best_params": best_params or {},
            "dte_interaction_enabled": selected_interaction,
        },
        "selection_receipt": dict(selection_receipt or {}),
        "executed_paths": int((selection_receipt or {}).get("executed_paths", 0)),
        "executed_variants": int((selection_receipt or {}).get("executed_variants", 0)),
        "executed_fits": executed_fits,
        "planned_fits": planned_fits,
        "planned_paths": n_cpcv_paths,
        "planned_variants": n_interaction_variants,
        "gauntlet_complete": False,
        "n_trials": {
            "grid_cardinality": len(hparam_grid),
            "interaction_variants": n_interaction_variants,
            "cpcv_paths": n_cpcv_paths,
            "total": reported_total,
            "executed_fits": executed_fits,
            "planned_fits": planned_fits,
            "planned_paths": n_cpcv_paths,
            "planned_variants": n_interaction_variants,
            "note": (
                "total is the declared search size: grid × interaction variants × "
                "C(n_groups, k_test). executed_fits is the completed selection receipt "
                "and is 0 when this manifest was written without one. planned_fits "
                "repeats the declared size. A count is not a gauntlet result and is "
                "not a deflated statistic."
            ),
        },
        "calibration": calibration_metrics,
        "kill_eval": kill_eval,
        "deployable": deployable,
        "deploy_reason": deploy_reason if not deployable else "",
        "hashes": {
            "model_sha256": model_sha,
            "calibrator_sha256": cal_sha,
        },
        # PRE-GATE LAW note
        "pre_gate_note": (
            "Score is display-only. It may not feed any ranker, sizer, sorter, or gate "
            "anywhere. gate.json 'scored' stays false until FS-5 gauntlet passes (FS-R3)."
        ),
    }

    # SAFETY: never write "validated" in user-facing claims (CI-guarded)
    # manifest does not contain "validated" — all outcome language is evidence, not verdicts.

    manifest_path = artifact_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info(
        "ops_train[%s]: artifact written to %s (deployable=%s)", bucket, artifact_dir, deployable
    )

    # Optional R2 upload (silently skipped when unconfigured)
    _try_r2_upload(artifact_dir, bucket, version, cfg)

    return manifest


def _try_r2_upload(artifact_dir: Path, bucket: str, version: int, cfg: dict) -> None:
    """Optionally upload artifact to R2. Silently skipped when R2 env vars are absent."""
    r2_cfg = cfg.get("r2_upload", {})
    enabled_env = r2_cfg.get("enabled_env", "R2_ENDPOINT")
    if not os.environ.get(enabled_env):
        return
    try:
        import boto3
        ep = os.environ.get("R2_ENDPOINT")
        ak = os.environ.get("R2_ACCESS_KEY_ID")
        sk = os.environ.get("R2_SECRET_ACCESS_KEY")
        bkt = os.environ.get("R2_BUCKET", "mastermindx")
        prefix = r2_cfg.get("prefix", "flow_signals/models")
        if not (ep and ak and sk):
            return
        s3 = boto3.client("s3", endpoint_url=ep, aws_access_key_id=ak, aws_secret_access_key=sk)
        for f in artifact_dir.iterdir():
            key = f"{prefix}/flow_score_{bucket}_v{version}/{f.name}"
            s3.upload_file(str(f), bkt, key)
            log.info("ops_train: uploaded %s to R2 %s", f.name, key)
    except Exception as e:
        log.warning("ops_train: R2 upload skipped: %s", e)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="FS-4 flow-score trainer (ops lane, off-render)"
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--bucket", choices=["0_7", "8_90", "90p"], help="Train one bucket")
    grp.add_argument("--all", action="store_true", help="Train all three buckets")
    parser.add_argument("--dry-run", action="store_true", help="No writes; print what would happen")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = _load_config()

    # Kill-switch check (P3.6 pattern / amendment §9)
    if not cfg.get("scoring", {}).get("enabled", False):
        log.info(
            "ops_train: scoring.enabled=false in config/flow_score.yml. "
            "Training may proceed (trainer is an ops tool). "
            "The trained artifact's 'deployable' status controls whether "
            "the score surfaces — it does not gate the trainer itself."
        )

    flow_dir = _flow_signals_dir()
    buckets = ["0_7", "8_90", "90p"] if args.all else [args.bucket]

    exit_code = 0
    for bkt in buckets:
        try:
            result = train_bucket(bkt, cfg, flow_dir, dry_run=args.dry_run)
            if result is None:
                log.warning("ops_train: bucket=%s returned None (skipped)", bkt)
                exit_code = 1
            else:
                log.info(
                    "ops_train: bucket=%s complete — deployable=%s",
                    bkt, result.get("deployable"),
                )
        except Exception as e:
            log.exception("ops_train: bucket=%s FAILED: %s", bkt, e)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
