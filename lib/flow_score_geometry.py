"""Pure FS-5 evaluation geometry validation.

This module owns no data store, model, calibrator, metric or promotion decision.
Its only job is to make invalid fit/evaluation geometry unrepresentable before an
estimator can be reached.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from lib.nyse_calendar import is_session


REQUIRED_ROW_FIELDS = (
    "event_id",
    "evaluation_spec_version",
    "source",
    "detector_version",
    "model_bucket",
    "root",
    "session_date",
    "fill_date",
    "outcome_end_session",
)
REGISTERED_BUCKETS = {"0_7": 5, "8_90": 21, "90p": 63}
SECONDARY_HORIZONS = {126}
FS5_EVALUATION_SPEC_VERSION = "fs5-v1"


class GeometryError(ValueError):
    """A fit/evaluation population has invalid or unknown geometry."""


@dataclass(frozen=True)
class GeometryPlan:
    rows: pd.DataFrame
    session_position: dict[date, int]
    intervals: pd.DataFrame


def _clean_scalar(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _to_session(value: Any, field: str) -> date:
    if value is None or pd.isna(value):
        raise GeometryError(f"{field}_missing")
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_localize(None)
        value = value.date()
    elif isinstance(value, date):
        pass
    else:
        try:
            parsed = pd.Timestamp(value)
        except (TypeError, ValueError) as exc:
            raise GeometryError(f"{field}_invalid:{value!r}") from exc
        if pd.isna(parsed):
            raise GeometryError(f"{field}_invalid:{value!r}")
        value = parsed.date() if parsed.tzinfo is None else parsed.tz_localize(None).date()
    if not is_session(value):
        raise GeometryError(f"{field}_not_nyse_session:{value.isoformat()}")
    return value


def validate_identity(df: pd.DataFrame) -> None:
    """Reject missing row identity and any mixed population identity."""
    missing_fields = [field for field in REQUIRED_ROW_FIELDS if field not in df.columns]
    if missing_fields:
        raise GeometryError("identity_fields_missing:" + ",".join(missing_fields))
    if df.empty:
        raise GeometryError("population_empty")

    for field in REQUIRED_ROW_FIELDS:
        null_mask = df[field].isna()
        if field in {"event_id", "root", "session_date", "fill_date", "outcome_end_session"}:
            null_mask |= df[field].astype("string").str.strip().eq("").fillna(True)
        if bool(null_mask.any()):
            raise GeometryError(f"identity_missing:{field}")

    for field in ("evaluation_spec_version", "source", "detector_version", "model_bucket"):
        values = {value for value in df[field].map(_clean_scalar) if value}
        if len(values) != 1:
            raise GeometryError(f"identity_mixed:{field}:{sorted(values)}")

    spec_version = _clean_scalar(df["evaluation_spec_version"].iloc[0])
    if spec_version != FS5_EVALUATION_SPEC_VERSION:
        raise GeometryError(f"identity_unknown_spec:{spec_version}")

    sources = {_clean_scalar(df["source"].iloc[0])}
    if sources == {"eod_proxy"}:
        raise GeometryError("identity_source_eod_proxy_verdict")
    roots = {value.upper() for value in df["root"].map(_clean_scalar)}
    if roots == {"SPY"}:
        raise GeometryError("identity_benchmark_spy_self")


def canonical_intervals(df: pd.DataFrame) -> pd.DataFrame:
    """Return native fill/end boundaries mapped to canonical NYSE positions."""
    validate_identity(df)

    event_sessions = [_to_session(value, "session_date") for value in df["session_date"]]
    fill_sessions = [_to_session(value, "fill_date") for value in df["fill_date"]]
    end_sessions = [_to_session(value, "outcome_end_session") for value in df["outcome_end_session"]]

    result = pd.DataFrame(
        {
            "event_id": df["event_id"].astype(str).str.strip().values,
            "root": df["root"].astype(str).str.upper().values,
            "event_session": event_sessions,
            "fill_session": fill_sessions,
            "end_session": end_sessions,
        }
    )
    if result["event_id"].duplicated().any():
        raise GeometryError("identity_duplicate_event_id")

    for row in result.itertuples(index=False):
        if row.fill_session < row.event_session:
            raise GeometryError(f"boundary_noncausal_fill:{row.event_id}")
        if row.end_session < row.fill_session:
            raise GeometryError(f"boundary_noncausal_end:{row.event_id}")

    all_sessions = sorted({row.event_session for row in result.itertuples(index=False)}.union(
        {row.fill_session for row in result.itertuples(index=False)},
        {row.end_session for row in result.itertuples(index=False)},
    ))
    position = {session: index for index, session in enumerate(all_sessions)}
    result["event_position"] = result["event_session"].map(position)
    result["fill_position"] = result["fill_session"].map(position)
    result["end_position"] = result["end_session"].map(position)
    return result


def validate_plan_geometry(plan: GeometryPlan) -> None:
    if plan.rows.empty or plan.intervals.empty:
        raise GeometryError("population_empty")

    session_positions = plan.rows["session_date"]
    atomicity = pd.DataFrame({"session": session_positions, "block": plan.rows["time_block"].astype(int)})
    if atomicity.groupby("session")["block"].nunique().ne(1).any():
        raise GeometryError("time_block_splits_session")

    minimum = plan.rows["time_block"].astype(int).min()
    maximum = plan.rows["time_block"].astype(int).max()
    if minimum != 0 or maximum != plan.rows["time_block"].astype(int).nunique() - 1:
        raise GeometryError("time_blocks_not_contiguous")


def assign_time_blocks(
    df: pd.DataFrame,
    n_groups: int,
    date_col: str = "session_date",
) -> pd.Series:
    """Assign complete canonical sessions to contiguous, non-empty blocks."""
    if n_groups < 1:
        raise GeometryError("time_block_count_invalid")
    if date_col not in df.columns:
        raise GeometryError("identity_missing:session_date")

    sessions = sorted({_to_session(value, date_col) for value in df[date_col]})
    if not sessions:
        raise GeometryError("population_empty")
    if n_groups > len(sessions):
        raise GeometryError(f"insufficient_sessions:{len(sessions)}<{n_groups}")

    ordered = np.array_split(np.asarray(sessions, dtype=object), n_groups)
    block_by_session = {
        session: block_index
        for block_index, block in enumerate(ordered)
        for session in block
    }
    return pd.Series(
        [block_by_session[_to_session(value, date_col)] for value in df[date_col]],
        index=df.index,
        name="time_block",
    )


def _has_interval_overlap(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    if left.empty or right.empty:
        return False
    left_roots = np.asarray(left["root"], dtype=object)
    right_roots = np.asarray(right["root"], dtype=object)
    left_start = left["fill_position"].to_numpy(dtype=int)
    right_start = right["fill_position"].to_numpy(dtype=int)
    left_end = left["end_position"].to_numpy(dtype=int)
    right_end = right["end_position"].to_numpy(dtype=int)
    return bool(
        (
            (left_roots[:, None] == right_roots[None, :])
            & (np.maximum(left_start[:, None], right_start[None, :])
               <= np.minimum(left_end[:, None], right_end[None, :]))
        ).any()
    )


def validate_split_geometry(
    rows: pd.DataFrame,
    train_idx: Sequence[int],
    validation_idx: Sequence[int],
    embargo_sessions: int,
    horizon_sessions: int,
    intervals: pd.DataFrame | None = None,
) -> None:
    """Validate one ordered train/validation slice in canonical session units."""
    if len(train_idx) == 0 or len(validation_idx) == 0:
        raise GeometryError("insufficient_root_diversity")
    if embargo_sessions < horizon_sessions:
        raise GeometryError(
            f"embargo_below_registered_horizon:{embargo_sessions}<{horizon_sessions}"
        )

    resolved_intervals = canonical_intervals(rows) if intervals is None else intervals
    train_intervals = resolved_intervals.iloc[np.asarray(train_idx, dtype=int)]
    validation_intervals = resolved_intervals.iloc[np.asarray(validation_idx, dtype=int)]

    if set(train_intervals["root"]).intersection(validation_intervals["root"]):
        raise GeometryError("root_disjointness_violated")
    if _has_interval_overlap(train_intervals, validation_intervals):
        raise GeometryError("label_window_overlap")

    embargo_start = int(validation_intervals["event_position"].min()) - embargo_sessions
    embargo_end = embargo_start + embargo_sessions - 1
    embargo_mask = (
        train_intervals["event_position"].between(embargo_start, embargo_end, inclusive="both")
        & ~train_intervals["root"].isin(validation_intervals["root"])
    )
    if bool(embargo_mask.any()):
        raise GeometryError("embargo_violation")


def build_geometry_plan(
    df: pd.DataFrame,
    *,
    model_bucket: str,
) -> GeometryPlan:
    """Build an immutable, validated geometry plan from explicit grader boundaries."""
    intervals = canonical_intervals(df)
    unique_sessions = sorted({row.event_session for row in intervals.itertuples(index=False)})
    session_position = {session: index for index, session in enumerate(unique_sessions)}
    rows = df.copy()
    rows["session_date"] = [session_position[row] for row in intervals["event_session"]]
    rows["time_block"] = rows["session_date"]
    plan = GeometryPlan(rows=rows, session_position=session_position, intervals=intervals)
    registered_horizons = set(REGISTERED_BUCKETS.values()) | SECONDARY_HORIZONS
    if model_bucket not in REGISTERED_BUCKETS and model_bucket not in registered_horizons:
        raise GeometryError(f"identity_unknown_model_bucket:{model_bucket}")
    return plan


def validate_population_partition(
    plan_by_population: Mapping[str, GeometryPlan],
    ordered_populations: Sequence[str] = ("train", "calibration_fit", "calibration_eval", "final_oos"),
) -> None:
    """Require an explicit, ordered, label-separated population partition receipt."""
    if tuple(plan_by_population) != tuple(ordered_populations):
        raise GeometryError("partition_plan_missing_or_unordered")

    ordered: list[GeometryPlan] = []
    for name in ordered_populations:
        plan = plan_by_population.get(name)
        if plan is None:
            raise GeometryError(f"partition_plan_missing:{name}")
        validate_plan_geometry(plan)
        ordered.append(plan)

    for earlier_index, earlier in enumerate(ordered):
        for later in ordered[earlier_index + 1:]:
            if _has_interval_overlap(earlier.intervals, later.intervals):
                raise GeometryError("partition_label_window_overlap")


def make_no_fit_health(reason: str) -> dict[str, Any]:
    """Return the existing-style explicit no-fit health receipt."""
    return {
        "health": "no_fit",
        "status": "nondeployable",
        "deployable": False,
        "method_geometry": "unavailable",
        "method_geometry_reason": reason,
        "building_history": True,
    }
