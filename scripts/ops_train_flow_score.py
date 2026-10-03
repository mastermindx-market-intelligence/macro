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
  - Purged K-fold K=5 (FS-R7).
  - Embargo >= per-bucket horizon days.
  - Group folds by BOTH underlying AND calendar time_block.
  - Selection: 5-fold purged group CV, max mean-OOF-AUC over hparam_grid.
    NOTE (CPCV-DECLARED-NOT-RUN): full combinatorial CPCV path enumeration and
    deflated-Sharpe correction per §4.3/§4.5 are NOT implemented in this wave.
    C(n_groups, k_test) = n_cpcv_paths is used only for N_trials accounting.
    Deferred to FS-5.
  - Uniqueness sample-weights (lib/flow_score.py uniqueness_weights).

CALIBRATION (amendment §5):
  - Per-bucket isotonic on a TEMPORAL holdout from serving cohorts only.
  - ECE < 0.05 (10 equal-mass bins).
  - Brier < base-rate Brier.
  - Reliability monotone => deployable:true, else deployable:false + reason.
  - n floors (amendment §7): below floor → deployable:false, reason=ERA-SPARSE/BELOW-FLOOR.

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
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from lib.flow_score_geometry import (
    GeometryError,
    BUCKET_HORIZONS,
    registered_bucket_horizons,
    assign_time_blocks,
    build_geometry_plan,
    canonical_intervals,
    make_no_fit_health,
    validate_population_partition,
    validate_split_geometry,
)
from lib.flow_score_admission import (
    AdmissionError,
    INDEX_ROOTS as _INDEX_ROOTS,
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
    graded_ok = joined["graded_ok"].map(lambda value: type(value) is bool and value)
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


def train_bucket(
    bucket: str,
    cfg: dict,
    flow_dir: Path,
    dry_run: bool = False,
    stage_receipt_resolver: Callable[[str], bytes] | None = None,
) -> dict | None:
    """Train and calibrate a flow-score model for one bucket.

    Returns manifest dict on success, None on failure.

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

    configured_horizons = _configured_horizons(cfg)
    if configured_horizons != dict(BUCKET_HORIZONS):
        raise GeometryError(
            "bucket_horizon_contract_mismatch:"
            f"{configured_horizons}!={BUCKET_HORIZONS}"
        )
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

    y_all = labeled["_label"].astype(float).values
    base_rate = float(y_all.mean())
    log.info("ops_train[%s]: labeled rows=%d, base_rate=%.4f", bucket, len(labeled), base_rate)

    # ── build features (amendment §3.4) ──────────────────────────────────────
    feature_cols = _feature_columns(cfg, bucket)
    # Serving cohort and population filter are settled by here; nothing has been
    # turned into a model feature yet. Halt before that if the live cohort has no
    # measured truth to learn from.
    _assert_live_feed_measured_features(labeled, feature_cols)
    X_all = _build_features(labeled, feature_cols)

    # ── n floor check — raw count (amendment §7) ──────────────────────────────
    n_floors = cfg.get("n_floors", {})
    bucket_floor = int(n_floors.get("bucket", 30))
    if len(labeled) < bucket_floor:
        log.warning(
            "ops_train[%s]: below n_floor (n=%d < floor=%d) — deployable=False / ERA-SPARSE",
            bucket, len(labeled), bucket_floor,
        )
        # We still write the artifact but with deployable=False
        deploy_reason = f"BELOW-FLOOR: n={len(labeled)} < bucket_floor={bucket_floor}"
        return _write_artifact(
            bucket=bucket,
            cfg=cfg,
            flow_dir=flow_dir,
            model=None,
            calibrator=None,
            deployable=False,
            deploy_reason=deploy_reason,
            serving_df=serving_df,
            labeled=labeled,
            pop_stats=pop_stats,
            base_rate=base_rate,
            calibration_metrics={},
            kill_eval={},
            n_trials=0,
            feature_cols=feature_cols,
            dry_run=dry_run,
        )

    cal_df = pd.concat([cal_fit_df, cal_eval_df], ignore_index=True)

    # Guard: eod_proxy must never appear in calibration
    _check_no_eod_proxy_in_calibration(cal_df, context="calibration holdout (train_bucket)")

    log.info("ops_train[%s]: train_n=%d, cal_n=%d", bucket, len(train_df), len(cal_df))

    if len(train_df) == 0:
        log.warning("ops_train[%s]: empty training set after holdout split", bucket)
        return make_no_fit_health("method_geometry_unavailable:empty_train_population")

    # ── uniqueness weights (amendment §4.4) ───────────────────────────────────
    from lib.flow_score import uniqueness_weights as _uw

    # embargo_days already set during holdout split above
    w_series = _uw(train_df, horizon_days=embargo_days)
    # Align weights to train_df event_ids
    if "event_id" in train_df.columns:
        sample_weights = w_series.reindex(train_df["event_id"].values).fillna(1.0).values
    else:
        sample_weights = np.ones(len(train_df))
    sample_weights = np.where(np.isfinite(sample_weights) & (sample_weights > 0), sample_weights, 1.0)

    # ── effective n (from uniqueness weights) ─────────────────────────────────
    effective_n = float(sample_weights.sum())
    log.info("ops_train[%s]: effective_n=%.1f (raw_n=%d)", bucket, effective_n, len(train_df))

    # Check effective n floor
    if effective_n < bucket_floor:
        deploy_reason = f"BELOW-FLOOR: effective_n={effective_n:.1f} < bucket_floor={bucket_floor}"
        log.warning("ops_train[%s]: %s", bucket, deploy_reason)
        return _write_artifact(
            bucket=bucket, cfg=cfg, flow_dir=flow_dir,
            model=None, calibrator=None,
            deployable=False, deploy_reason=deploy_reason,
            serving_df=serving_df, labeled=labeled, pop_stats=pop_stats,
            base_rate=base_rate, calibration_metrics={}, kill_eval={},
            n_trials=0, feature_cols=feature_cols, dry_run=dry_run,
        )

    # ── CV: hyperparameter grid (amendment §4.3 / §4.5) ──────────────────────
    hparam_grid = _expand_grid(cfg.get("hyperparameter_grid", {}))
    dte_interaction = cfg.get("dte_interaction", {})
    # For 8_90: DTE-interaction on/off adds ×2 to N_trials
    n_interaction_variants = 2 if dte_interaction.get(bucket, False) else 1
    k_folds = cfg.get("k_folds", 5)
    n_groups = cfg.get("n_groups", 6)
    k_test = cfg.get("k_test", 2)
    n_cpcv_paths = _cpcv_path_count(n_groups, k_test)
    # Registered N_trials per amendment §4.5
    n_trials = len(hparam_grid) * n_interaction_variants * n_cpcv_paths
    log.info(
        "ops_train[%s]: N_trials=%d (grid=%d, interaction_variants=%d, cpcv_paths=%d)",
        bucket, n_trials, len(hparam_grid), n_interaction_variants, n_cpcv_paths,
    )

    # Monotone constraints (mechanism-known only, amendment §4.5)
    monotone_cfg = cfg.get("monotone_constraints", {})
    random_seed = cfg.get("random_seed", 42)

    # Count distinct roots in training set (used for split fallback diagnostic)
    _underlying_col_cv = "root" if "root" in train_df.columns else "underlying"
    _n_unique_roots_train = (
        int(train_df[_underlying_col_cv].nunique())
        if _underlying_col_cv in train_df.columns
        else 0
    )

    # Generate CV splits (amendment §4.1 / §4.2)
    try:
        splits = _group_fold_splits(
            train_df,
            k_folds=k_folds,
            embargo=embargo_days,
            n_groups=n_groups,
            underlying_col=_underlying_col_cv,
            date_col="session_date" if "session_date" in train_df.columns else "session_date",
            random_seed=random_seed,
        )
    except GeometryError as exc:
        # Invalid CV geometry is terminal: no fit/calibrator/feature build is
        # ever produced. The fold partition was never emitted, so we never
        # produced a model and we never touched any estimator or calibrator.
        log.warning(
            "ops_train[%s]: invalid fold geometry — building history/no-fit: %s",
            bucket, exc,
        )
        return make_no_fit_health(f"method_geometry_unavailable:{exc}")

    X_train_all = _build_features(train_df, feature_cols)
    y_train_all = train_df["_label"].astype(float).values

    if len(splits) == 0 and not dry_run:
        # No valid CV splits after all purge/embargo/underlying filters.
        # Amendment §4.1-§4.5 requires CV for model selection; without splits
        # the selection machinery is dead.  Mark as not deployable instead of
        # silently falling through to hparam_grid[0].
        deploy_reason = (
            f"NO-VALID-CV-SPLITS: _group_fold_splits returned 0 splits "
            f"(n_roots={_n_unique_roots_train}, "
            f"k_folds={k_folds}, embargo={embargo_days}). "
            "Cannot run amendment §4.1-§4.5 selection machinery."
        )
        log.warning("ops_train[%s]: %s", bucket, deploy_reason)
        return make_no_fit_health("method_geometry_unavailable:no_valid_cv_splits")

    if dry_run:
        log.info("ops_train[%s]: dry_run — skipping grid search", bucket)
        # Pick first param set for dry-run
        best_params = hparam_grid[0] if hparam_grid else {}
        best_auc = float("nan")
    else:
        # CV grid search: pick best params by mean OOF AUC
        best_auc = -1.0
        best_params = hparam_grid[0]
        for params in hparam_grid:
            fold_aucs = []
            for train_idx, val_idx in splits:
                X_tr = X_train_all.iloc[train_idx]
                y_tr = y_train_all[train_idx]
                w_tr = sample_weights[train_idx]
                X_va = X_train_all.iloc[val_idx]
                y_va = y_train_all[val_idx]
                if len(np.unique(y_va)) < 2:
                    continue
                try:
                    m = _fit_model(X_tr, y_tr, w_tr, params, monotone_cfg, feature_cols, random_seed)
                    p = m.predict_proba(X_va)[:, 1]
                    fold_aucs.append(_auc_score(y_va, p))
                except Exception as e:
                    log.debug("ops_train[%s]: fold fit failed: %s", bucket, e)
            if fold_aucs:
                mean_auc = float(np.nanmean(fold_aucs))
                if mean_auc > best_auc:
                    best_auc = mean_auc
                    best_params = params

    log.info("ops_train[%s]: best_params=%s, cv_auc=%.4f", bucket, best_params, best_auc)

    # ── final model fit on full training set ─────────────────────────────────
    if dry_run:
        log.info("ops_train[%s]: dry_run — skipping final model fit and artifact write", bucket)
        return {"bucket": bucket, "dry_run": True, "n_trials": n_trials}

    final_model = _fit_model(
        X_train_all, y_train_all, sample_weights,
        best_params, monotone_cfg, feature_cols, random_seed,
    )

    # ── calibration on temporal holdout (amendment §5) ────────────────────────
    calibration_metrics: dict = {}
    kill_eval: dict = {}
    deployable = False
    deploy_reason = ""

    if cal_fit_df.empty or cal_eval_df.empty:
        deploy_reason = "BELOW-FLOOR: empty calibration holdout"
        log.warning("ops_train[%s]: %s", bucket, deploy_reason)
    else:
        _check_no_eod_proxy_in_calibration(cal_fit_df, context="calibration fit")
        _check_no_eod_proxy_in_calibration(cal_eval_df, context="calibration evaluation")
        X_cal = _build_features(cal_fit_df, feature_cols)
        y_cal = cal_fit_df["_label"].astype(float).values

        try:
            p_raw_cal = final_model.predict_proba(X_cal)[:, 1]
        except Exception as e:
            deploy_reason = f"calibration predict_proba failed: {e}"
            p_raw_cal = None

        if p_raw_cal is not None and len(p_raw_cal) > 0:
            from sklearn.isotonic import IsotonicRegression
            from lib.flow_score import ece as _ece, brier as _brier, reliability_table as _rel, is_reliability_monotone as _mono

            n_bins = cfg.get("n_bins", 10)
            ece_threshold = cfg.get("ece_threshold", 0.05)

            p_raw_eval = final_model.predict_proba(
                _build_features(cal_eval_df, feature_cols)
            )[:, 1]
            y_eval = cal_eval_df["_label"].astype(float).values

            ir = IsotonicRegression(out_of_bounds="clip")
            if len(np.unique(y_cal)) >= 2:
                ir.fit(p_raw_cal, y_cal)
            else:
                ir = None

            if ir is None or len(p_raw_eval) == 0:
                # Calibration holdout too small to split — cannot honestly evaluate
                deploy_reason = "BELOW-FLOOR: calibration holdout too small to split for honest eval"
                log.warning("ops_train[%s]: %s", bucket, deploy_reason)
                ir = None
                p_raw_eval = pd.Series(dtype=float)

        if p_raw_eval is not None and len(p_raw_eval) > 0 and ir is not None:
            # Evaluate on the DISJOINT outer slice — not on the calibrator's fit data
            p_cal_outer = ir.predict(p_raw_eval)

            ece_val = _ece(p_cal_outer, y_eval, n_bins=n_bins, equal_mass=True)
            brier_val = _brier(p_cal_outer, y_eval)
            # base_rate_brier uses the outer-slice base rate (matches the evaluation slice)
            outer_base_rate = float(y_eval.mean()) if len(y_eval) > 0 else base_rate
            base_rate_brier = float(outer_base_rate * (1.0 - outer_base_rate))
            rel_table = _rel(p_cal_outer, y_eval, n_bins=n_bins, equal_mass=True)
            monotone = _mono(rel_table)

            # Kill-eval: AUC in newest era (amendment §8 #1)
            # Use raw predictions on the outer slice (before isotonic calibration)
            # to measure discriminative skill independently of calibration.
            era_col = "era" if "era" in cal_eval_df.columns else None
            newest_era_auc = float("nan")
            if era_col:
                eras = cal_eval_df[era_col].dropna().unique()
                if len(eras) > 0:
                    newest_era = sorted(eras)[-1]
                    newest_mask = cal_eval_df[era_col] == newest_era
                    if newest_mask.sum() >= 2:
                        y_new = y_eval[newest_mask.values]
                        p_new = p_raw_eval[newest_mask.values]
                        newest_era_auc = _auc_score(y_new, p_new)
            else:
                # No era column — use full cal set for AUC (raw predictions)
                newest_era_auc = _auc_score(y_eval, p_raw_eval)

            calibration_metrics = {
                "ece": float(ece_val),
                "brier": float(brier_val),
                "base_rate": float(outer_base_rate),
                "base_rate_brier": float(base_rate_brier),
                "reliability_table": rel_table,
                "monotone": bool(monotone),
                "n_cal_fit": int(len(y_cal)),
                "n_cal_eval": int(len(y_eval)),
            }
            kill_eval = {
                "auc_newest_era": float(newest_era_auc),
                "ece_pass": bool(ece_val < ece_threshold),
                "monotone_pass": bool(monotone),
            }

            # Deployable criteria (amendment §5):
            # ECE < threshold AND Brier < base_rate_brier AND monotone
            reasons: list[str] = []
            if not (ece_val < ece_threshold):
                reasons.append(f"ECE={ece_val:.4f} >= threshold={ece_threshold}")
            if not (brier_val < base_rate_brier):
                reasons.append(
                    f"Brier={brier_val:.4f} >= base_rate_brier={base_rate_brier:.4f}"
                )
            if not monotone:
                reasons.append("reliability curve non-monotone")

            if reasons:
                deploy_reason = "; ".join(reasons)
                deployable = False
            else:
                deployable = True
                calibrator = ir

        else:
            deploy_reason = "calibration skipped (no predictions)"
            ir = None

    if not deployable:
        ir = None  # Do not ship calibrator when not deployable

    # ── artifact write ────────────────────────────────────────────────────────
    return _write_artifact(
        bucket=bucket, cfg=cfg, flow_dir=flow_dir,
        model=final_model, calibrator=ir,
        deployable=deployable, deploy_reason=deploy_reason,
        serving_df=serving_df, labeled=labeled, pop_stats=pop_stats,
        base_rate=base_rate,
        calibration_metrics=calibration_metrics,
        kill_eval=kill_eval,
        n_trials=n_trials,
        feature_cols=feature_cols,
        best_params=best_params,
        dry_run=dry_run,
    )


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
) -> dict:
    """Write model artifact directory: model.joblib, calibrator.joblib, manifest.json.

    Manifest schema: flow_score.model_manifest/v1 (amendment §4 artifact spec).
    NEVER writes the word "validated" (CI-guarded).
    """
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
                "effective_n": float(len(grp)),  # raw here; effective computed in training
                "eras": int(grp["era"].nunique()) if "era" in grp.columns else None,
            }

    # CV params for manifest
    k_folds = cfg.get("k_folds", 5)
    n_groups = cfg.get("n_groups", 6)
    k_test = cfg.get("k_test", 2)
    hparam_grid = _expand_grid(cfg.get("hyperparameter_grid", {}))
    dte_interaction = cfg.get("dte_interaction", {})
    n_interaction_variants = 2 if dte_interaction.get(bucket, False) else 1
    n_cpcv_paths = _cpcv_path_count(n_groups, k_test)

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
            "base_rate": float(base_rate),
        },
        "population": pop_stats,
        "cv_params": {
            "k_folds": k_folds,
            "embargo_days": cfg.get("embargo_days", {}).get(bucket, 21),
            "n_groups": n_groups,
            "k_test": k_test,
            "n_cpcv_paths": n_cpcv_paths,
            "feature_columns": feature_cols,
            "best_params": best_params or {},
            "dte_interaction_enabled": bool(dte_interaction.get(bucket, False)),
        },
        "n_trials": {
            "grid_cardinality": len(hparam_grid),
            "interaction_variants": n_interaction_variants,
            "cpcv_paths": n_cpcv_paths,
            "total": n_trials,
            "note": (
                "N_trials = grid × interaction_variants × CPCV_paths per amendment §4.5. "
                "Expanding the grid requires amending N_trials in the amendment doc. "
                "DEVIATION (CPCV-DECLARED-NOT-RUN): model selection is 5-fold purged group CV "
                "picking max mean-OOF-AUC over hparam_grid — NOT full combinatorial CPCV "
                "enumeration. n_cpcv_paths counts C(n_groups, k_test) paths for N_trials "
                "accounting purposes but combinatorial path enumeration and deflated-Sharpe "
                "correction are not yet implemented. Selection bias correction deferred to FS-5."
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
