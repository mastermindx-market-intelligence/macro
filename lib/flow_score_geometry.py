"""Pure FS-5 evaluation geometry validation.

This module owns no data store, model, calibrator, metric or promotion decision.
Its only job is to make invalid fit/evaluation geometry unrepresentable before an
estimator can be reached.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from itertools import combinations
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from lib.nyse_calendar import is_session
from lib.nyse_calendar import session_n_back
from lib.nyse_calendar import session_n_forward
from lib.nyse_calendar import sessions_between
from lib.nyse_calendar import sessions_strictly_between


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
BUCKET_HORIZONS = {
    "0_7": (REGISTERED_BUCKETS["0_7"],),
    "8_90": (REGISTERED_BUCKETS["8_90"],),
    "90p": (REGISTERED_BUCKETS["90p"], 126),
}
FS5_EVALUATION_SPEC_VERSION = "fs5-v1"
# Study-spec schema v2 is the frozen block schedule. It is not a new target,
# horizon, or evaluation_spec_version (that stays fs5-v1).
FS5_STUDY_SPEC_SCHEMA_V2 = "flow_signals.fs5_admission_spec/v2"
FROZEN_TRAIN_BLOCK_COUNT = 6
FROZEN_CPCV_TEST_GROUPS = 2
# Registered floors stay 30 per population and 20 per era. A length-6 native
# window makes effective N = covered sessions / 6; that is a consequence of the
# weight, not a new numerical floor.
TRAIN_BLOCK_KEYS = ("id", "first_session", "last_session", "roots")
# Greeks/IV era partition (era-partition amendment §3.1) and the flow-score
# verdict registry (flow-score amendment §6.2). 2017-19 is reservable and
# unbooked. 2020-22 is booked but only partially covered (2022-only). 2023+
# is the booked primary era. Labels are the canonical recognized strings.
GREEKS_ERA_REGISTRY = (
    {
        "era": "2017-19",
        "year_start": 2017,
        "year_end": 2019,
        "booked": False,
        "reservable": True,
        "partial": None,
    },
    {
        "era": "2020-22",
        "year_start": 2020,
        "year_end": 2022,
        "booked": True,
        "reservable": False,
        "partial": "2022-only",
    },
    {
        "era": "2023+",
        "year_start": 2023,
        "year_end": None,
        "booked": True,
        "reservable": False,
        "partial": None,
    },
)
CANONICAL_GREEKS_ERAS = frozenset(item["era"] for item in GREEKS_ERA_REGISTRY)
NEWEST_GREEKS_ERA = "2023+"


def registered_bucket_horizons() -> dict[str, tuple[int, ...]]:
    return {bucket: horizons for bucket, horizons in BUCKET_HORIZONS.items()}


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

    boundary_dates = [
        row.event_session
        for row in result.itertuples(index=False)
    ] + [
        row.fill_session
        for row in result.itertuples(index=False)
    ] + [
        row.end_session
        for row in result.itertuples(index=False)
    ]
    minimum_boundary = min(boundary_dates)
    maximum_boundary = max(boundary_dates)
    position = {
        session: index
        for index, session in enumerate(
            sessions_between(minimum_boundary, maximum_boundary)
        )
    }
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
    left_start = left["fill_session"].to_numpy(dtype="datetime64[D]")
    right_start = right["fill_session"].to_numpy(dtype="datetime64[D]")
    left_end = left["end_session"].to_numpy(dtype="datetime64[D]")
    right_end = right["end_session"].to_numpy(dtype="datetime64[D]")
    return bool(
        (
            np.maximum(left_start[:, None], right_start[None, :])
            <= np.minimum(left_end[:, None], right_end[None, :])
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
    """Build an immutable, validated geometry plan from explicit grader boundaries.

    Bind the canonical requested bucket consistently. Reject any frame whose
    source bucket contradicts the requested bucket — silent laundering is a
    display-tier authority leak (a 0_7 frame cannot become an 90p 126-horizon
    plan, and an 8_90 frame cannot be claimed for 90p primary/secondary).
    """
    if model_bucket not in BUCKET_HORIZONS:
        raise GeometryError(f"identity_unknown_model_bucket:{model_bucket}")
    intervals = canonical_intervals(df)
    if "model_bucket" in df.columns and len(df) > 0:
        frame_bucket = _clean_scalar(df["model_bucket"].iloc[0])
        if frame_bucket and frame_bucket != model_bucket:
            raise GeometryError(
                f"frame_bucket_mismatch:{frame_bucket}!={model_bucket}"
            )
    unique_sessions = sorted({row.event_session for row in intervals.itertuples(index=False)})
    session_position = {session: index for index, session in enumerate(unique_sessions)}
    rows = df.copy()
    rows["session_date"] = [session_position[row] for row in intervals["event_session"]]
    rows["time_block"] = rows["session_date"]
    plan = GeometryPlan(rows=rows, session_position=session_position, intervals=intervals)
    return plan


def validate_population_partition(
    plan_by_population: Mapping[str, GeometryPlan],
    ordered_populations: Sequence[str] = ("train", "calibration_fit", "calibration_eval", "final_oos"),
    requested_bucket: str | None = None,
    horizon_columns: set[str] | None = None,
) -> None:
    """Require an explicit, ordered, label-separated population partition receipt."""
    ordered: list[GeometryPlan] = []
    for name, plan in plan_by_population.items():
        if plan is None:
            raise GeometryError(f"partition_plan_missing:{name}")
        validate_plan_geometry(plan)
        ordered.append(plan)

    # Global cross-root inclusive label-window union purge — independent of
    # dict ordering. This is the hard no-fit any pair-wise overlap must hit,
    # including the cross-population case where two non-adjacent populations
    # hold shared label dates. Checked BEFORE chronology because a violated
    # label-window overlap is a hard no-fit regardless of population order.
    for earlier_index, earlier in enumerate(ordered):
        for later in ordered[earlier_index + 1:]:
            if _has_interval_overlap(earlier.intervals, later.intervals):
                raise GeometryError("partition_label_window_overlap")

    if [name for name in plan_by_population] != list(ordered_populations):
        raise GeometryError("partition_plan_missing_or_unordered")

    actual_order = [
        name
        for name, _plan in sorted(
            plan_by_population.items(),
            key=lambda item: (
                min(item[1].intervals["fill_session"]),
                max(item[1].intervals["fill_session"]),
            ),
        )
    ]
    if actual_order != list(ordered_populations):
        raise GeometryError("partition_not_chronological")

    first = ordered[0]
    identity_fields = (
        "evaluation_spec_version",
        "source",
        "detector_version",
        "model_bucket",
    )
    for field in identity_fields:
        reference = first.rows[field].map(_clean_scalar).unique().tolist()
        if len(reference) != 1:
            raise GeometryError(f"population_identity_mixed:{field}:{reference}")
        reference_value = reference[0]
        for population in ordered[1:]:
            values = population.rows[field].map(_clean_scalar).unique().tolist()
            if values != [reference_value]:
                raise GeometryError(
                    f"population_identity_mismatch:{field}:{reference_value}!={values}"
                )

    all_roots: set[str] = set()
    shared_roots: set[str] = set()
    for population in ordered:
        roots = {value.upper() for value in population.rows["root"].map(_clean_scalar)}
        shared_roots.update(roots & all_roots)
        all_roots.update(roots)
    if len(all_roots) < 2:
        raise GeometryError("insufficient_root_diversity")
    if shared_roots:
        raise GeometryError("population_roots_not_disjoint")

    requested = requested_bucket or _clean_scalar(first.rows["model_bucket"].iloc[0])
    if requested not in BUCKET_HORIZONS:
        raise GeometryError(f"identity_unknown_model_bucket:{requested}")
    frame_bucket = _clean_scalar(first.rows["model_bucket"].iloc[0])
    if frame_bucket != requested:
        raise GeometryError(f"requested_bucket_mismatch:{frame_bucket}!={requested}")

    required_horizons = BUCKET_HORIZONS[requested]
    if requested == "90p":
        available = horizon_columns or set()
        missing = [
            f"spy_excess_{horizon}"
            for horizon in required_horizons
            if f"spy_excess_{horizon}" not in available
        ]
        if missing:
            raise GeometryError(
                f"bucket_horizon_mismatch:{requested}:{','.join(missing)}"
            )

    for earlier_index, earlier in enumerate(ordered[:-1]):
        later = ordered[earlier_index + 1]
        earlier_terminal = max(earlier.intervals["end_session"])
        later_initial = min(later.intervals["fill_session"])
        if max(earlier.intervals["fill_session"]) > later_initial:
            raise GeometryError("partition_not_chronological")
        if earlier_terminal >= later_initial:
            raise GeometryError("partition_not_chronological")
        required_gap = max(required_horizons)
        gap_sessions = len(sessions_between(earlier_terminal, later_initial)) - 1
        if gap_sessions < required_gap:
            raise GeometryError(
                f"partition_embargo_violation:{gap_sessions}<{required_gap}"
            )

    for earlier_index, earlier in enumerate(ordered):
        for later in ordered[earlier_index + 1:]:
            if _has_interval_overlap(earlier.intervals, later.intervals):
                raise GeometryError("partition_label_window_overlap")


@dataclass(frozen=True)
class TrainBlock:
    """One externally frozen root-by-NYSE-subwindow train block."""

    id: int
    first_session: date
    last_session: date
    roots: frozenset[str]


@dataclass(frozen=True)
class CpcvPath:
    """One lexical held-pair assignment after root exclusion, purge, and embargo."""

    held: tuple[int, int]
    train_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]


def frozen_embargo_sessions(bucket: str) -> int:
    """Pin H to max(BUCKET_HORIZONS[bucket]): 5, 21, or 126.

    90p uses the secondary 126-session horizon. 63 alone is not the embargo.
    """
    try:
        horizons = BUCKET_HORIZONS[bucket]
    except KeyError as exc:
        raise GeometryError(f"identity_unknown_model_bucket:{bucket}") from exc
    embargo = max(int(horizon) for horizon in horizons)
    if embargo not in (5, 21, 126):
        raise GeometryError(f"frozen_embargo_invalid:{embargo}")
    return embargo


def _exact_session_day(value: Any, field: str) -> date:
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_convert("America/New_York").date()
        else:
            value = value.date()
    elif isinstance(value, date):
        pass
    elif isinstance(value, str):
        text = value.strip()
        try:
            value = date.fromisoformat(text[:10])
        except ValueError as exc:
            raise GeometryError(f"{field}_invalid:{value!r}") from exc
    else:
        raise GeometryError(f"{field}_invalid:{value!r}")
    if not is_session(value):
        raise GeometryError(f"{field}_not_nyse_session:{value.isoformat()}")
    return value


def _exact_block_id(value: Any) -> int:
    if isinstance(value, bool) or isinstance(value, np.bool_):
        raise GeometryError("train_block_id_invalid")
    if isinstance(value, (int, np.integer)):
        number = int(value)
    elif isinstance(value, float) and value.is_integer():
        # pandas nullable-int columns can surface as floats; the value is still
        # the integer assigned from the external spec.
        number = int(value)
    else:
        raise GeometryError("train_block_id_invalid")
    if number not in range(FROZEN_TRAIN_BLOCK_COUNT):
        raise GeometryError("train_block_id_invalid")
    return number


def _exact_binary_label(value: Any) -> int:
    if isinstance(value, bool) or isinstance(value, np.bool_) or value is None:
        raise GeometryError("label_invalid")
    try:
        if pd.isna(value):
            raise GeometryError("label_invalid")
    except TypeError:
        pass
    if isinstance(value, (int, np.integer)):
        number = int(value)
    elif isinstance(value, float) and float(value).is_integer():
        number = int(value)
    else:
        raise GeometryError("label_invalid")
    if number not in (0, 1):
        raise GeometryError("label_invalid")
    return number


def greeks_era_for_year(year: int) -> str:
    """Canonical greeks-era label. Years before 2017 are outside the partition."""
    if 2017 <= year <= 2019:
        return "2017-19"
    if 2020 <= year <= 2022:
        return "2020-22"
    if year >= 2023:
        return "2023+"
    raise GeometryError(f"greeks_era_outside_partition:{year}")


def _era_is_explicit_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def bind_greeks_era(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive the greeks era from admission-bound session_date.

    A missing era column is derived. An explicit null contradicts the source
    clock and is rejected. A supplied label must be exactly the canonical
    string for that session; arbitrary text is not trusted and rows are not
    dropped.
    """
    if "session_date" not in frame.columns:
        raise GeometryError("greeks_era_session_missing")
    derived: list[str] = []
    for value in frame["session_date"].tolist():
        session = _to_session(value, "session_date")
        derived.append(greeks_era_for_year(session.year))
    if "era" in frame.columns:
        for raw, canonical in zip(frame["era"].tolist(), derived):
            if _era_is_explicit_null(raw):
                raise GeometryError("greeks_era_null_contradiction")
            if not isinstance(raw, str) or raw != canonical:
                raise GeometryError("greeks_era_not_canonical")
    bound = frame.copy()
    bound["era"] = derived
    return bound


def matching_train_block(
    blocks: Sequence[TrainBlock],
    session: date,
    root: str,
) -> int | None:
    """Return the single block id whose window contains ``session`` and lists ``root``."""
    cleaned = str(root).strip().upper()
    matches = [
        block.id
        for block in blocks
        if block.first_session <= session <= block.last_session and cleaned in block.roots
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def parse_frozen_train_blocks(
    raw: Any,
    *,
    outer_first: date,
    outer_last: date,
    train_roots: set[str],
) -> tuple[TrainBlock, ...]:
    """Accept only six literal, ordered, contiguous NYSE blocks.

    Block ids, sessions, and roots come from the external spec. Nothing here
    splits sessions by row count or by a future outcome quantile.
    """
    if not isinstance(raw, list) or len(raw) != FROZEN_TRAIN_BLOCK_COUNT:
        raise GeometryError("train_block_ids_invalid")
    parsed: list[TrainBlock] = []
    for entry in raw:
        if not isinstance(entry, Mapping) or set(entry) != set(TRAIN_BLOCK_KEYS):
            raise GeometryError("train_block_schema_invalid")
        block_id = entry.get("id")
        if type(block_id) is not int:
            raise GeometryError("train_block_ids_invalid")
        first = _exact_session_day(entry.get("first_session"), "train_block_first_session")
        last = _exact_session_day(entry.get("last_session"), "train_block_last_session")
        if first > last:
            raise GeometryError("train_block_window_mismatch")
        roots_raw = entry.get("roots")
        if not isinstance(roots_raw, list) or not roots_raw:
            raise GeometryError("train_block_roots_missing")
        roots: list[str] = []
        for root in roots_raw:
            if not isinstance(root, str) or not root.strip() or root != root.strip():
                raise GeometryError("train_block_roots_missing")
            roots.append(root.upper())
        if len(set(roots)) != len(roots):
            raise GeometryError("train_block_roots_missing")
        parsed.append(
            TrainBlock(
                id=block_id,
                first_session=first,
                last_session=last,
                roots=frozenset(roots),
            )
        )
    parsed.sort(key=lambda block: block.id)
    if [block.id for block in parsed] != list(range(FROZEN_TRAIN_BLOCK_COUNT)):
        raise GeometryError("train_block_ids_invalid")

    covered: list[date] = []
    for block in parsed:
        block_sessions = sessions_between(block.first_session, block.last_session)
        if not block_sessions or block_sessions[0] != block.first_session:
            raise GeometryError("train_block_not_nyse")
        if covered and block_sessions[0] <= covered[-1]:
            raise GeometryError("train_block_overlap_or_unordered")
        if covered:
            if sessions_strictly_between(covered[-1], block_sessions[0]):
                raise GeometryError("train_block_gap")
            nxt = session_n_forward(covered[-1], 1)
            if nxt != block_sessions[0]:
                raise GeometryError("train_block_gap")
        covered.extend(block_sessions)

    outer = sessions_between(outer_first, outer_last)
    if not outer or covered != outer:
        raise GeometryError("train_block_window_mismatch")
    # A session in two blocks would repeat inside ``covered`` and fail equality.
    if len(covered) != len(set(covered)):
        raise GeometryError("train_block_session_split")

    union: set[str] = set()
    for block in parsed:
        union |= set(block.roots)
    expected_roots = {str(root).strip().upper() for root in train_roots}
    if not expected_roots or union != expected_roots:
        raise GeometryError("train_block_root_union_mismatch")
    return tuple(parsed)


def embargo_bounds_for_block(block: TrainBlock, embargo_h: int) -> tuple[date, date]:
    """Inclusive NYSE span covering H sessions on both sides of this one block.

    The span is per block. Callers must not replace two held blocks with the
    min start and max end of the pair.
    """
    if embargo_h not in (5, 21, 126):
        raise GeometryError(f"frozen_embargo_invalid:{embargo_h}")
    left = session_n_back(block.first_session, embargo_h)
    right = session_n_forward(block.last_session, embargo_h)
    if left is None or right is None:
        raise GeometryError("embargo_calendar_unavailable")
    return left, right


def assert_source_only_cpcv_feasible(
    blocks: Sequence[TrainBlock],
    embargo_h: int,
) -> None:
    """Reject a block schedule that root exclusion, purge, or embargo empties.

    Uses only the literal root×session schedule. Observed rows, labels, and
    class support are later no-fit gates, not evidence for this check.
    """
    if embargo_h not in (5, 21, 126):
        raise GeometryError(f"frozen_embargo_invalid:{embargo_h}")
    if [block.id for block in blocks] != list(range(FROZEN_TRAIN_BLOCK_COUNT)):
        raise GeometryError("train_block_ids_invalid")
    first = min(block.first_session for block in blocks)
    last = max(block.last_session for block in blocks)
    pad_left, _ = embargo_bounds_for_block(
        TrainBlock(0, first, first, frozenset({"PAD"})), embargo_h
    )
    _, pad_right = embargo_bounds_for_block(
        TrainBlock(0, last, last, frozenset({"PAD"})), embargo_h
    )
    sessions = sessions_between(pad_left, pad_right)
    position = {session: index for index, session in enumerate(sessions)}
    by_id = {block.id: block for block in blocks}
    for held in combinations(range(FROZEN_TRAIN_BLOCK_COUNT), FROZEN_CPCV_TEST_GROUPS):
        held_roots: set[str] = set()
        embargo_zones: list[tuple[int, int]] = []
        purge_zones: list[tuple[int, int]] = []
        for block_id in held:
            block = by_id[block_id]
            held_roots |= set(block.roots)
            left, right = embargo_bounds_for_block(block, embargo_h)
            embargo_zones.append((position[left], position[right]))
            purge_zones.append(
                (position[block.first_session], position[block.last_session])
            )
        survived = False
        for block_id, block in by_id.items():
            if block_id in held or not (set(block.roots) - held_roots):
                continue
            for session in sessions_between(block.first_session, block.last_session):
                index = position[session]
                if any(start <= index <= end for start, end in embargo_zones):
                    continue
                if any(start <= index <= end for start, end in purge_zones):
                    continue
                survived = True
                break
            if survived:
                break
        if not survived:
            raise GeometryError(
                f"cpcv_path_deterministically_empty:{held[0]},{held[1]}"
            )


def merged_inclusive_union(spans: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge inclusive overlaps. Adjacent non-overlapping sessions stay split."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if start > end:
            raise GeometryError("native_interval_invalid")
        if not merged or start > merged[-1][1]:
            merged.append((int(start), int(end)))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], int(end)))
    return merged


def build_purge_starts(merged: Sequence[tuple[int, int]]) -> tuple[int, ...]:
    """Start positions of an already-merged inclusive union.

    Callers build this once per held path and reuse it for every bisect.
    """
    return tuple(int(item[0]) for item in merged)


def _overlaps_merged_union(
    start: int,
    end: int,
    merged: Sequence[tuple[int, int]],
    starts: Sequence[int],
) -> bool:
    if start > end:
        raise GeometryError("native_interval_invalid")
    if len(starts) != len(merged):
        raise GeometryError("purge_index_mismatch")
    if not merged:
        return False
    import bisect

    index = bisect.bisect_right(starts, end) - 1
    if index < 0:
        return False
    union_start, union_end = merged[index]
    return start <= union_end and end >= union_start


def preflight_cpcv_paths(
    rows: pd.DataFrame,
    blocks: Sequence[TrainBlock],
    embargo_h: int,
    *,
    label_column: str = "label",
) -> tuple[CpcvPath, ...]:
    """Validate all 15 held pairs before any feature builder or estimator.

    Root exclusion uses the frozen roots of each held block, including roots
    with no observed held row. Purge tests the merged union of actual native
    fill/end intervals. Embargo is H NYSE sessions on both sides of each held
    block, not one span from the earliest to the latest held block.
    """
    if embargo_h not in (5, 21, 126):
        raise GeometryError(f"frozen_embargo_invalid:{embargo_h}")
    if label_column not in rows.columns or "train_block" not in rows.columns:
        raise GeometryError("cpcv_fields_missing")
    if [block.id for block in blocks] != list(range(FROZEN_TRAIN_BLOCK_COUNT)):
        raise GeometryError("train_block_ids_invalid")

    intervals = canonical_intervals(rows)
    if len(intervals) != len(rows):
        raise GeometryError("cpcv_row_alignment_invalid")
    labels = [_exact_binary_label(value) for value in rows[label_column].tolist()]
    groups = [_exact_block_id(value) for value in rows["train_block"].tolist()]
    by_id = {block.id: block for block in blocks}

    bound_dates = [
        session
        for block in blocks
        for session in embargo_bounds_for_block(block, embargo_h)
    ]
    bound_dates.extend(intervals["event_session"].tolist())
    bound_dates.extend(intervals["fill_session"].tolist())
    bound_dates.extend(intervals["end_session"].tolist())
    position = {
        session: index
        for index, session in enumerate(sessions_between(min(bound_dates), max(bound_dates)))
    }

    event_pos: list[int] = []
    fill_pos: list[int] = []
    end_pos: list[int] = []
    for offset, interval in enumerate(intervals.itertuples(index=False)):
        expected = matching_train_block(blocks, interval.event_session, interval.root)
        if expected is None or expected != groups[offset]:
            raise GeometryError("group_window_root_mismatch")
        try:
            event_pos.append(position[interval.event_session])
            fill_pos.append(position[interval.fill_session])
            end_pos.append(position[interval.end_session])
        except KeyError as exc:
            raise GeometryError("embargo_calendar_unavailable") from exc

    if any(groups.count(block_id) == 0 for block_id in range(FROZEN_TRAIN_BLOCK_COUNT)):
        raise GeometryError("cpcv_block_missing")

    event_ids = [str(event_id) for event_id in intervals["event_id"].tolist()]
    roots = [str(root) for root in intervals["root"].tolist()]
    paths: list[CpcvPath] = []
    for held in combinations(range(FROZEN_TRAIN_BLOCK_COUNT), FROZEN_CPCV_TEST_GROUPS):
        held_ids = set(held)
        held_roots: set[str] = set()
        embargo_zones: list[tuple[int, int]] = []
        for block_id in held:
            block = by_id[block_id]
            held_roots |= set(block.roots)
            left, right = embargo_bounds_for_block(block, embargo_h)
            embargo_zones.append((position[left], position[right]))
        validation_index = [index for index, group in enumerate(groups) if group in held_ids]
        if not validation_index:
            raise GeometryError("empty_path")
        union = merged_inclusive_union(
            [(fill_pos[index], end_pos[index]) for index in validation_index]
        )
        # One merged-span index per held path. Row queries only bisect it.
        purge_starts = build_purge_starts(union)
        train_index: list[int] = []
        for index, group in enumerate(groups):
            if group in held_ids or roots[index] in held_roots:
                continue
            if any(start <= event_pos[index] <= end for start, end in embargo_zones):
                continue
            if _overlaps_merged_union(
                fill_pos[index], end_pos[index], union, purge_starts
            ):
                continue
            train_index.append(index)
        if not train_index:
            raise GeometryError("empty_path")
        if (
            len({labels[index] for index in train_index}) != 2
            or len({labels[index] for index in validation_index}) != 2
        ):
            raise GeometryError("one_class_path")
        paths.append(
            CpcvPath(
                held=(held[0], held[1]),
                train_ids=tuple(event_ids[index] for index in train_index),
                validation_ids=tuple(event_ids[index] for index in validation_index),
            )
        )
    if len(paths) != 15 or [path.held for path in paths] != list(
        combinations(range(FROZEN_TRAIN_BLOCK_COUNT), FROZEN_CPCV_TEST_GROUPS)
    ):
        raise GeometryError("cpcv_path_set_invalid")
    return tuple(paths)


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
