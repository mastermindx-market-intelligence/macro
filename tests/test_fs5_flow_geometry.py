"""Fit-free FS-5 evaluation geometry tests.

All dates are synthetic NYSE session labels. No market outcome, production store,
model fit, calibration fit or promotion authority is exercised.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from lib.flow_score_geometry import (
    FS5_EVALUATION_SPEC_VERSION,
    GeometryError,
    registered_bucket_horizons,
    assign_time_blocks,
    build_geometry_plan,
    canonical_intervals,
    _has_interval_overlap,
    make_no_fit_health,
    validate_population_partition,
    validate_split_geometry,
)
from lib.nyse_calendar import is_session


def nyse_sessions(start: date, count: int) -> list[date]:
    sessions: list[date] = []
    current = start
    while len(sessions) < count:
        if is_session(current):
            sessions.append(current)
        current += timedelta(days=1)
    return sessions


SESSIONS = nyse_sessions(date(2025, 1, 2), 700)


def sessions_with_gap(offset: int, gap_days: int) -> date:
    return SESSIONS[offset] + timedelta(days=gap_days)


def row(
    event_id: str,
    root: str,
    event_offset: int,
    fill_offset: int,
    end_offset: int,
    *,
    source: str = "live_feed",
    detector_version: str = "detector-v1",
    model_bucket: str = "0_7",
) -> dict:
    return {
        "event_id": event_id,
        "evaluation_spec_version": FS5_EVALUATION_SPEC_VERSION,
        "source": source,
        "detector_version": detector_version,
        "model_bucket": model_bucket,
        "root": root,
        "session_date": SESSIONS[event_offset],
        "fill_date": SESSIONS[fill_offset],
        "outcome_end_session": SESSIONS[end_offset],
    }


def frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def identity_mismatch_plan(field: str, value: str) -> dict:
    valid = [
        row("t", "AAPL", 0, 0, 2),
        row("f", "MSFT", 30, 30, 32),
        row("e", "NVDA", 60, 60, 62),
        row("o", "TSLA", 90, 90, 92),
    ]
    names = ("train", "calibration_fit", "calibration_eval", "final_oos")
    plans = {
        name: build_geometry_plan(frame([item]), model_bucket="0_7")
        for name, item in zip(names, valid)
    }
    plans["calibration_eval"].rows[field] = value
    return plans


def plan(rows: list[dict], bucket: str = "0_7"):
    return build_geometry_plan(frame(rows), model_bucket=bucket)


def test_inclusive_shared_endpoint_is_overlap() -> None:
    held_out = row("val", "AAPL", 0, 10, 15)
    train = row("train", "AAPL", 8, 15, 20)
    intervals = canonical_intervals(frame([held_out, train]))
    assert _has_interval_overlap(intervals.iloc[[1]], intervals.iloc[[0]])
    with pytest.raises(GeometryError, match="root_disjointness_violated"):
        validate_split_geometry(frame([held_out, train]), [1], [0], 5, 5)


def test_sparse_rows_cannot_compress_session_ordinal_distance() -> None:
    intervals = canonical_intervals(frame([
        row("earlier", "AAPL", 0, 0, 1),
        row("later", "MSFT", 3, 3, 4),
    ]))
    earlier_end = intervals.loc[
        intervals["event_id"] == "earlier", "end_position"
    ].item()
    later_fill = intervals.loc[
        intervals["event_id"] == "later", "fill_position"
    ].item()
    assert later_fill - earlier_end > 1


def test_cross_root_overlap_and_shared_endpoint_are_purged() -> None:
    held_out = row("val", "AAPL", 0, 10, 15)
    overlap = row("train-overlap", "MSFT", 8, 14, 20)
    shared_end = row("train-end", "NVDA", 8, 15, 21)
    intervals = canonical_intervals(frame([held_out, overlap, shared_end]))

    assert _has_interval_overlap(
        intervals.iloc[[0]], intervals.iloc[[1]]
    )
    assert _has_interval_overlap(
        intervals.iloc[[0]], intervals.iloc[[2]]
    )


def test_delayed_held_out_fill_blocks_event_only_control() -> None:
    held_out = row("val", "AAPL", 0, 10, 15)
    delayed = row("train", "AAPL", 14, 14, 19)
    intervals = canonical_intervals(frame([held_out, delayed]))
    assert _has_interval_overlap(intervals.iloc[[1]], intervals.iloc[[0]])


def test_non_overlapping_control_passes_geometry_only() -> None:
    held_out = row("val", "AAPL", 0, 10, 15)
    train = row("train", "MSFT", 21, 21, 23)
    validate_split_geometry(frame([held_out, train]), [1], [0], 5, 5)


def test_embargo_uses_sessions_not_calendar_days() -> None:
    assert SESSIONS[2].weekday() == 0 and SESSIONS[3].weekday() == 1
    # Calendar rows omit the Jan 9 holiday, so event offsets 2 and 3 are adjacent sessions.
    val = row("val", "MSFT", 2, 2, 3)
    train = row("train", "NVDA", 1, 1, 2)
    with pytest.raises(GeometryError, match="label_window_overlap"):
        validate_split_geometry(frame([val, train]), [1], [0], 2, 1)
    with pytest.raises(GeometryError, match="label_window_overlap"):
        validate_split_geometry(frame([val, train]), [1], [0], 3, 1)

    # A training event three sessions before validation is outside a two-session embargo.
    further = row("further", "NVDA", 0, 0, 1)
    validate_split_geometry(frame([val, further]), [1], [0], 1, 1)


def test_same_session_is_one_atomic_block() -> None:
    rows = [row("a", "AAPL", 0, 0, 2), row("b", "AAPL", 0, 0, 2), row("c", "AAPL", 1, 1, 3)]
    blocks = assign_time_blocks(frame(rows), 2)
    assert blocks.iloc[0] == blocks.iloc[1]
    assert blocks.iloc[0] != blocks.iloc[2]


def test_one_root_refuses_fit_fold() -> None:
    held_out = row("val", "AAPL", 0, 0, 2)
    train = row("train", "AAPL", 10, 10, 12)
    with pytest.raises(GeometryError, match="root_disjointness_violated"):
        validate_split_geometry(frame([held_out, train]), [1], [0], 5, 5)


@pytest.mark.parametrize("field", ["root", "session_date", "fill_date", "outcome_end_session"])
def test_missing_identity_or_boundary_refuses(field: str) -> None:
    valid = row("val", "AAPL", 0, 0, 2)
    invalid = row("train", "AAPL", 10, 10, 12)
    invalid[field] = None
    with pytest.raises(GeometryError, match=f"identity_missing:{field}"):
        canonical_intervals(frame([valid, invalid]))


def test_missing_outcome_end_is_not_inferred_from_event_or_horizon() -> None:
    valid = row("val", "AAPL", 0, 0, 2)
    invalid = row("train", "AAPL", 10, 10, 12)
    invalid["outcome_end_session"] = None
    with pytest.raises(GeometryError, match=r"identity_missing:outcome_end_session"):
        canonical_intervals(frame([valid, invalid]))


@pytest.mark.parametrize(
    ("field", "values", "expected"),
    [
        ("source", ["live_feed", "tape_recon"], "identity_mixed:source"),
        ("detector_version", ["detector-v1", "detector-v2"], "identity_mixed:detector_version"),
        ("model_bucket", ["0_7", "8_90"], "identity_mixed:model_bucket"),
        (
            "evaluation_spec_version",
            [FS5_EVALUATION_SPEC_VERSION, "unknown-spec"],
            "identity_mixed:evaluation_spec_version",
        ),
    ],
)
def test_mixed_population_identity_refuses(field: str, values: list[str], expected: str) -> None:
    first = row("a", "AAPL", 0, 0, 2)
    second = row("b", "AAPL", 1, 1, 3)
    first[field] = values[0]
    second[field] = values[1]
    with pytest.raises(GeometryError, match=expected.replace(":", ":")):
        canonical_intervals(frame([first, second]))


def test_unknown_spec_refuses() -> None:
    rows = [row("a", "AAPL", 0, 0, 2), row("b", "AAPL", 1, 1, 3)]
    for value in rows:
        value["evaluation_spec_version"] = "unknown"
    with pytest.raises(GeometryError, match="identity_unknown_spec:unknown"):
        canonical_intervals(frame(rows))


def test_eod_proxy_cannot_serve_verdict() -> None:
    rows = [row("a", "AAPL", 0, 0, 2, source="eod_proxy")]
    with pytest.raises(GeometryError, match="identity_source_eod_proxy_verdict"):
        canonical_intervals(frame(rows))


def test_spy_self_benchmark_refuses() -> None:
    rows = [row("a", "SPY", 0, 0, 2), row("b", "SPY", 1, 1, 3)]
    with pytest.raises(GeometryError, match="identity_benchmark_spy_self"):
        canonical_intervals(frame(rows))


def test_holiday_is_not_a_canonical_session() -> None:
    rows = [row("a", "AAPL", 0, 0, 2), row("b", "AAPL", 1, 1, 3)]
    rows[1]["session_date"] = date(2025, 1, 20)
    with pytest.raises(GeometryError, match="session_date_not_nyse_session"):
        canonical_intervals(frame(rows))


def test_holiday_and_weekend_do_not_compress_true_session_distance() -> None:
    # Friday 2025-01-17 is followed by the weekend and MLK Day.
    assert SESSIONS[10] == date(2025, 1, 17)
    assert SESSIONS[11] == date(2025, 1, 21)
    intervals = canonical_intervals(frame([
        row("before", "AAPL", 10, 10, 10),
        row("after", "MSFT", 11, 11, 11),
    ]))
    positions = intervals.set_index("event_id")["fill_position"]
    assert positions["after"] - positions["before"] == 1


def test_ordered_disjoint_partition_receipt_passes() -> None:
    ordered = frame([
        row("t1", "AAPL", 0, 0, 2),
        row("c1", "MSFT", 12, 12, 14),
        row("c2", "NVDA", 24, 24, 26),
        row("o", "TSLA", 36, 36, 38),
    ])
    by_population = {
        "train": build_geometry_plan(ordered.iloc[[0]], model_bucket="0_7"),
        "calibration_fit": build_geometry_plan(ordered.iloc[[1]], model_bucket="0_7"),
        "calibration_eval": build_geometry_plan(ordered.iloc[[2]], model_bucket="0_7"),
        "final_oos": build_geometry_plan(ordered.iloc[[3]], model_bucket="0_7"),
    }
    validate_population_partition(by_population)


def test_out_of_order_partition_refuses() -> None:
    valid = frame([
        row("t1", "AAPL", 0, 0, 2),
        row("c1", "MSFT", 4, 4, 6),
        row("c2", "NVDA", 8, 8, 10),
        row("o", "TSLA", 12, 12, 14),
    ])
    by_population = {
        "train": build_geometry_plan(valid.iloc[[0]], model_bucket="0_7"),
        "calibration_fit": build_geometry_plan(valid.iloc[[1]], model_bucket="0_7"),
        "final_oos": build_geometry_plan(valid.iloc[[2]], model_bucket="0_7"),
        "calibration_eval": build_geometry_plan(valid.iloc[[3]], model_bucket="0_7"),
    }
    with pytest.raises(GeometryError, match="partition_plan_missing_or_unordered"):
        validate_population_partition(by_population)


def test_reversed_nonoverlapping_populations_refuse() -> None:
    rows = [
        row("o", "AAPL", 12, 12, 14),
        row("e", "MSFT", 8, 8, 10),
        row("f", "NVDA", 4, 4, 6),
        row("t", "TSLA", 0, 0, 2),
    ]
    names = ("final_oos", "calibration_eval", "calibration_fit", "train")
    plans = {
        name: build_geometry_plan(frame([item]), model_bucket="0_7")
        for name, item in zip(names, rows)
    }
    with pytest.raises(GeometryError, match="partition_plan_missing_or_unordered"):
        validate_population_partition(plans)

    ordered_names = ("train", "calibration_fit", "calibration_eval", "final_oos")
    reversed_plans = {
        name: build_geometry_plan(frame([item]), model_bucket="0_7")
        for name, item in zip(
            ordered_names,
            [row("r-o", "TSLA", 36, 36, 38), row("r-e", "NVDA", 24, 24, 26), row("r-f", "MSFT", 12, 12, 14), row("r-t", "AAPL", 0, 0, 2)],
        )
    }
    with pytest.raises(GeometryError, match="partition_not_chronological"):
        validate_population_partition(reversed_plans)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evaluation_spec_version", "other-spec"),
        ("source", "tape_recon"),
        ("detector_version", "detector-v2"),
        ("model_bucket", "8_90"),
    ],
)
def test_population_identity_must_match_exactly(field, value):
    plans = identity_mismatch_plan(field, value)
    with pytest.raises(GeometryError, match=f"population_identity_mismatch:{field}"):
        validate_population_partition(plans)


def test_shared_root_across_populations_refuses() -> None:
    rows = [
        row("t", "AAPL", 0, 0, 2),
        row("f", "AAPL", 4, 4, 6),
        row("e", "MSFT", 8, 8, 10),
        row("o", "NVDA", 12, 12, 14),
    ]
    names = ("train", "calibration_fit", "calibration_eval", "final_oos")
    plans = {
        name: build_geometry_plan(frame([item]), model_bucket="0_7")
        for name, item in zip(names, rows)
    }
    with pytest.raises(GeometryError, match="population_roots_not_disjoint"):
        validate_population_partition(plans)


def test_requested_bucket_must_match_population_bucket() -> None:
    rows = [
        row("t", "AAPL", 0, 0, 2, model_bucket="8_90"),
        row("f", "MSFT", 30, 30, 31, model_bucket="8_90"),
        row("e", "NVDA", 60, 60, 61, model_bucket="8_90"),
        row("o", "TSLA", 90, 90, 91, model_bucket="8_90"),
    ]
    names = ("train", "calibration_fit", "calibration_eval", "final_oos")
    names_reversed = ("final_oos", "calibration_eval", "calibration_fit", "train")
    plans = {
        name: build_geometry_plan(frame([item]), model_bucket="8_90")
        for name, item in zip(names_reversed, list(reversed(rows)))
    }
    with pytest.raises(GeometryError, match="partition_plan_missing_or_unordered"):
        validate_population_partition(plans, requested_bucket="8_90")

    ordered_plans = {
        name: build_geometry_plan(frame([item]), model_bucket="8_90")
        for name, item in zip(names, rows)
    }
    with pytest.raises(GeometryError, match="requested_bucket_mismatch:8_90!=0_7"):
        validate_population_partition(ordered_plans, requested_bucket="0_7")


def test_build_geometry_plan_refuses_frame_bucket_mismatch() -> None:
    """A 0_7 frame cannot be claimed as an 8_90 or 90p plan; binding is rejected
    rather than silently laundered. 90p secondary (126) cannot ride on a 0_7 ruler."""
    base = row("e", "AAPL", 0, 0, 2, model_bucket="0_7")
    with pytest.raises(GeometryError, match="frame_bucket_mismatch:0_7!=8_90"):
        build_geometry_plan(frame([base]), model_bucket="8_90")
    with pytest.raises(GeometryError, match="frame_bucket_mismatch:0_7!=90p"):
        build_geometry_plan(frame([base]), model_bucket="90p")


def test_build_geometry_plan_refuses_8_90_frame_for_90p_secondary() -> None:
    """Spoofed input: caller asks for 90p (126 secondary) but the frame is 8_90.
    A 90p plan without an explicit 63-session primary AND 126 secondary is a
    promotion-display leak. Reject at build time."""
    base = row("e", "AAPL", 0, 0, 2, model_bucket="8_90")
    with pytest.raises(GeometryError, match="frame_bucket_mismatch:8_90!=90p"):
        build_geometry_plan(frame([base]), model_bucket="90p")


def test_90p_requires_primary_and_secondary_horizons() -> None:
    # 90p secondary 126-session embargo requires each consecutive pair to span
    # at least 126 NYSE sessions between end_session and fill_session.
    valid = [
        row("t", "AAPL", 0, 0, 62, model_bucket="90p"),
        row("f", "MSFT", 189, 189, 251, model_bucket="90p"),
        row("e", "NVDA", 378, 378, 440, model_bucket="90p"),
        row("o", "TSLA", 567, 567, 629, model_bucket="90p"),
    ]
    names = ("train", "calibration_fit", "calibration_eval", "final_oos")
    names_reversed = ("final_oos", "calibration_eval", "calibration_fit", "train")
    plans = {
        name: build_geometry_plan(frame([item]), model_bucket="90p")
        for name, item in zip(names_reversed, valid)
    }
    assert registered_bucket_horizons()["90p"] == (63, 126)
    with pytest.raises(GeometryError, match="partition_plan_missing_or_unordered"):
        validate_population_partition(
            plans,
            requested_bucket="90p",
            horizon_columns={"spy_excess_63", "spy_excess_126"},
        )
    with pytest.raises(GeometryError, match="bucket_horizon_mismatch:90p:spy_excess_126"):
        validate_population_partition(
            {name: plan for name, plan in zip(names, list(plans.values()))},
            requested_bucket="90p",
            horizon_columns={"spy_excess_63"},
        )
    ordered_plans = {
        name: build_geometry_plan(frame([item]), model_bucket="90p")
        for name, item in zip(names, valid)
    }
    validate_population_partition(
        ordered_plans,
        requested_bucket="90p",
        horizon_columns={"spy_excess_63", "spy_excess_126"},
    )


def test_calibration_crossing_refuses() -> None:
    by_population = {
        "train": build_geometry_plan(frame([row("t", "AAPL", 0, 0, 4)]), model_bucket="0_7"),
        "calibration_fit": build_geometry_plan(frame([row("f", "MSFT", 30, 30, 32)]), model_bucket="0_7"),
        "calibration_eval": build_geometry_plan(frame([row("e", "NVDA", 34, 34, 36)]), model_bucket="0_7"),
        "final_oos": build_geometry_plan(frame([row("o", "TSLA", 28, 28, 30)]), model_bucket="0_7"),
    }
    with pytest.raises(GeometryError, match="partition_label_window_overlap"):
        validate_population_partition(by_population)


def test_missing_partition_is_building_history_no_fit() -> None:
    health = make_no_fit_health("building_history/method_geometry_unavailable")
    assert health == {
        "health": "no_fit",
        "status": "nondeployable",
        "deployable": False,
        "method_geometry": "unavailable",
        "method_geometry_reason": "building_history/method_geometry_unavailable",
        "building_history": True,
    }


def test_canary_estimator_and_calibrator_throw_on_invalid_geometry() -> None:
    class CanaryEstimator:
        called = False

        def fit(self, *_args, **_kwargs):
            self.called = True

    class CanaryCalibrator:
        called = False

        def fit(self, *_args, **_kwargs):
            self.called = True

    invalid = row("a", "AAPL", 0, 0, 2)
    invalid["fill_date"] = None
    estimator = CanaryEstimator()
    calibrator = CanaryCalibrator()
    with pytest.raises(GeometryError):
        canonical_intervals(frame([invalid]))


def test_one_root_total_is_insufficient_not_a_time_only_partition() -> None:
    rows = [
        row("t", "AAPL", 0, 0, 2),
        row("f", "AAPL", 12, 12, 14),
        row("e", "AAPL", 24, 24, 26),
        row("o", "AAPL", 36, 36, 38),
    ]
    names = ("train", "calibration_fit", "calibration_eval", "final_oos")
    plans = {
        name: build_geometry_plan(frame([item]), model_bucket="0_7")
        for name, item in zip(names, rows)
    }
    with pytest.raises(GeometryError, match="insufficient_root_diversity"):
        validate_population_partition(plans)
