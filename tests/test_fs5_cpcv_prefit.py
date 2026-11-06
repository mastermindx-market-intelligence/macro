"""Synthetic FS-5 pre-fit CPCV. No market tape, no real fit, no grade association."""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.flow_score import build_interaction_features, uniqueness_weights, uniqueness_weights_nyse_intervals
from lib.flow_score_admission import (
    SPEC_SCHEMA,
    SPEC_SCHEMA_V2,
    AdmissionError,
    _digest,
    _endpoints,
    _member,
    build_admission_receipt,
    source_census_descriptor,
    validate_admission_receipt,
)
from lib.flow_score_geometry import (
    FS5_EVALUATION_SPEC_VERSION,
    FS5_STUDY_SPEC_SCHEMA_V2,
    GeometryError,
    assert_source_only_cpcv_feasible,
    frozen_embargo_sessions,
    merged_inclusive_union,
    parse_frozen_train_blocks,
    preflight_cpcv_paths,
)
from lib.nyse_calendar import is_session, sessions_between
from test_fs5_flow_admission import STAGE_BYTES, _expected, _receipt, _rows

ROOTS = ("AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOG")
PYTEST_VENV_NOTE = "synthetic only"


def _sessions(start: date, count: int) -> list[date]:
    found: list[date] = []
    day = start
    while len(found) < count:
        if is_session(day):
            found.append(day)
        day += timedelta(days=1)
    return found


def _block_schedule(start: date, length: int, roots=ROOTS) -> tuple[list[date], list[dict]]:
    sessions = _sessions(start, length * 6)
    blocks = []
    for block_id in range(6):
        chunk = sessions[block_id * length : (block_id + 1) * length]
        blocks.append(
            {
                "id": block_id,
                "first_session": chunk[0].isoformat(),
                "last_session": chunk[-1].isoformat(),
                "roots": [roots[block_id]],
            }
        )
    return sessions, blocks


def _parse(blocks, sessions, roots):
    return parse_frozen_train_blocks(
        blocks,
        outer_first=sessions[0],
        outer_last=sessions[-1],
        train_roots=set(roots),
    )


def _identity(bucket: str) -> dict:
    return {
        "evaluation_spec_version": FS5_EVALUATION_SPEC_VERSION,
        "source": "tape_recon",
        "detector_version": "test-detector",
        "model_bucket": bucket,
    }


def _event(eid, root, session, block, label, bucket="0_7", fill=None, end=None):
    fill = fill or session
    end = end or fill
    return {
        "event_id": eid,
        "root": root,
        "session_date": session.isoformat(),
        "fill_date": fill.isoformat(),
        "outcome_end_session": end.isoformat(),
        "train_block": block,
        "label": label,
        **_identity(bucket),
    }


def _paired_frame(blocks, sessions, length: int, bucket="0_7") -> pd.DataFrame:
    rows = []
    for block in blocks:
        chunk = sessions[block["id"] * length : (block["id"] + 1) * length]
        root = block["roots"][0]
        rows.append(_event(f"b{block['id']}-0", root, chunk[0], block["id"], 0, bucket))
        rows.append(_event(f"b{block['id']}-1", root, chunk[1], block["id"], 1, bucket))
    return pd.DataFrame(rows)


def _paths(frame, blocks, sessions, embargo, roots=ROOTS):
    parsed = _parse(blocks, sessions, roots)
    return preflight_cpcv_paths(frame, parsed, embargo, label_column="label")


def _grid():
    rates = [0.02, 0.05, 0.1, 0.2]
    iterations = [200, 400]
    leaves = [15, 31, 63]
    return [
        {"learning_rate": rate, "max_iter": rounds, "max_leaf_nodes": nodes}
        for rate in rates
        for rounds in iterations
        for nodes in leaves
    ]


def _premium_scores(features):
    """Module-level so the stand-in model can be written with joblib."""
    return np.clip(features["premium"].to_numpy(dtype=float), 0.05, 0.95)


class _ConstantModel:
    def __init__(self, scores):
        self.scores = scores

    def predict_proba(self, features):
        if callable(self.scores):
            positive = np.asarray(self.scores(features), dtype=float)
        else:
            positive = np.full(len(features), float(self.scores))
        return np.column_stack([1.0 - positive, positive])


def test_study_schema_v2_is_not_a_new_evaluation_version():
    assert FS5_EVALUATION_SPEC_VERSION == "fs5-v1"
    assert FS5_STUDY_SPEC_SCHEMA_V2 == "flow_signals.fs5_admission_spec/v2"
    assert SPEC_SCHEMA == "flow_signals.fs5_admission_spec/v1"
    assert SPEC_SCHEMA_V2 == FS5_STUDY_SPEC_SCHEMA_V2
    assert SPEC_SCHEMA != SPEC_SCHEMA_V2


def test_embargo_is_pinned_to_the_longest_registered_horizon():
    assert frozen_embargo_sessions("0_7") == 5
    assert frozen_embargo_sessions("8_90") == 21
    assert frozen_embargo_sessions("90p") == 126
    with pytest.raises(GeometryError, match="identity_unknown_model_bucket"):
        frozen_embargo_sessions("63")


def test_six_literal_blocks_cover_the_outer_window_without_a_calendar_gap():
    sessions, blocks = _block_schedule(date(2026, 7, 1), 12)
    parsed = _parse(blocks, sessions, ROOTS)
    assert [block.id for block in parsed] == list(range(6))
    covered = []
    for block in parsed:
        covered.extend(sessions_between(block.first_session, block.last_session))
    assert covered == sessions
    # Independence Day 2026 is observed on Friday 3 July, inside this span.
    assert date(2026, 7, 3) not in covered
    assert date(2026, 7, 4) not in covered
    assert_source_only_cpcv_feasible(parsed, 5)


@pytest.mark.parametrize(
    "mutate, reason",
    [
        ("gap", "train_block_gap"),
        ("overlap", "train_block_overlap_or_unordered"),
        ("weekend", "not_nyse_session"),
        ("union", "train_block_root_union_mismatch"),
        ("count", "train_block_ids_invalid"),
        ("bool_id", "train_block_ids_invalid"),
    ],
)
def test_invalid_block_schedule_is_rejected(mutate, reason):
    sessions, blocks = _block_schedule(date(2024, 1, 2), 6)
    roots = set(ROOTS)
    if mutate == "gap":
        # Move block 3 one session later than the contiguous boundary and shorten it
        # so it no longer meets block 2.
        shifted = _sessions(date.fromisoformat(blocks[3]["first_session"]) + timedelta(days=1), 6)
        blocks[3]["first_session"] = shifted[1].isoformat()
        blocks[3]["last_session"] = shifted[-1].isoformat()
    elif mutate == "overlap":
        blocks[2]["last_session"] = blocks[3]["first_session"]
    elif mutate == "weekend":
        blocks[0]["first_session"] = "2024-01-06"  # Saturday
    elif mutate == "union":
        roots = set(ROOTS) | {"TSLA"}
    elif mutate == "count":
        blocks = blocks[:-1]
    elif mutate == "bool_id":
        blocks[0]["id"] = True
    with pytest.raises(GeometryError, match=reason):
        _parse(blocks, sessions, roots)


def test_length_one_blocks_are_deterministically_empty_under_the_real_embargo():
    sessions, blocks = _block_schedule(date(2024, 1, 2), 1)
    parsed = _parse(blocks, sessions, ROOTS)
    with pytest.raises(GeometryError, match=r"cpcv_path_deterministically_empty:0,1"):
        assert_source_only_cpcv_feasible(parsed, 5)


def test_preflight_returns_the_fifteen_lexical_held_pairs():
    sessions, blocks = _block_schedule(date(2024, 1, 2), 12)
    frame = _paired_frame(blocks, sessions, 12)
    paths = _paths(frame, blocks, sessions, 5)
    assert [path.held for path in paths] == list(combinations(range(6), 2))
    assert len(paths) == 15
    for path in paths:
        assert path.train_ids and path.validation_ids
        assert set(path.train_ids).isdisjoint(path.validation_ids)


def test_held_block_roots_are_excluded_even_when_that_root_has_no_held_row():
    sessions, blocks = _block_schedule(date(2024, 1, 2), 12)
    blocks[0]["roots"] = ["AAPL", "MSFT"]
    blocks[3]["roots"] = ["MSFT", "META"]
    roots = []
    for block in blocks:
        roots.extend(block["roots"])
    frame = _paired_frame(blocks, sessions, 12)
    # The held block lists MSFT, but no observed held row uses it.
    frame = frame.loc[frame["event_id"] != "b0-1"].copy()
    frame.loc[frame["event_id"] == "b0-0", "label"] = 0
    extra = _event("b0-class", "AAPL", sessions[6], 0, 1)
    msft = _event("msft-train", "MSFT", sessions[3 * 12 + 6], 3, 0)
    meta = _event("meta-train", "META", sessions[3 * 12 + 7], 3, 1)
    frame = pd.concat([frame, pd.DataFrame([extra, msft, meta])], ignore_index=True)
    paths = _paths(frame, blocks, sessions, 5, roots=roots)
    held = next(path for path in paths if path.held == (0, 1))
    assert "msft-train" not in held.train_ids
    assert "meta-train" in held.train_ids


def _center_frame(blocks, sessions, length: int) -> pd.DataFrame:
    rows = []
    for block in blocks:
        chunk = sessions[block["id"] * length : (block["id"] + 1) * length]
        root = block["roots"][0]
        rows.append(_event(f"c{block['id']}-0", root, chunk[5], block["id"], 0))
        rows.append(_event(f"c{block['id']}-1", root, chunk[6], block["id"], 1))
    return pd.DataFrame(rows)


def test_purge_is_an_inclusive_merged_union_not_a_pairwise_matrix():
    assert merged_inclusive_union([(0, 0), (1, 1)]) == [(0, 0), (1, 1)]
    assert merged_inclusive_union([(0, 2), (2, 4), (6, 6)]) == [(0, 4), (6, 6)]
    sessions, blocks = _block_schedule(date(2024, 1, 2), 12)
    frame = _center_frame(blocks, sessions, 12)
    # The held row's native end touches one later fill. Center rows sit past
    # that endpoint and past a 5-session embargo, so the other 14 paths stay
    # nonempty. The touched row is still removed.
    shared = sessions[3 * 12]
    delayed = _event("delayed-held", "AAPL", sessions[0], 0, 1, fill=sessions[2], end=shared)
    overlap = _event("shared-end", "AMZN", shared, 3, 0, fill=shared, end=shared)
    frame = pd.concat([frame, pd.DataFrame([delayed, overlap])], ignore_index=True)
    paths = _paths(frame, blocks, sessions, 5)
    held = next(path for path in paths if path.held == (0, 1))
    assert "shared-end" not in held.train_ids
    assert "c3-0" in held.train_ids
    assert "delayed-held" in held.validation_ids


def test_embargo_is_applied_to_each_held_block_not_the_pair_span():
    sessions, blocks = _block_schedule(date(2024, 1, 2), 12)
    frame = _paired_frame(blocks, sessions, 12)
    right_of_zero = _event("right-of-0", "MSFT", sessions[12], 1, 0)
    left_of_five = _event("left-of-5", "META", sessions[5 * 12 - 1], 4, 1)
    middle = _event("middle-safe", "NVDA", sessions[2 * 12 + 6], 2, 0)
    frame = pd.concat(
        [frame, pd.DataFrame([right_of_zero, left_of_five, middle])],
        ignore_index=True,
    )
    paths = _paths(frame, blocks, sessions, 5)
    held = next(path for path in paths if path.held == (0, 5))
    assert "right-of-0" not in held.train_ids
    assert "left-of-5" not in held.train_ids
    assert "middle-safe" in held.train_ids


@pytest.mark.parametrize(
    "mutate, reason",
    [
        ("missing", "cpcv_block_missing"),
        ("duplicate", "identity_duplicate_event_id"),
        ("label", "label_invalid"),
        ("bool_label", "label_invalid"),
        ("weekend", "not_nyse_session"),
        ("mismatch", "group_window_root_mismatch"),
        ("noncausal", "boundary_noncausal_fill"),
        ("one_class", "one_class_path"),
        ("same_roots", "empty_path"),
    ],
)
def test_invalid_path_raises_before_any_feature_builder(mutate, reason, monkeypatch):
    sessions, blocks = _block_schedule(date(2024, 1, 2), 12)
    frame = _paired_frame(blocks, sessions, 12)
    if mutate == "missing":
        frame = frame.loc[frame["train_block"] != 5].copy()
    elif mutate == "duplicate":
        frame.loc[frame.index[-1], "event_id"] = frame.iloc[0]["event_id"]
    elif mutate == "label":
        frame.loc[frame.index[0], "label"] = 2
    elif mutate == "bool_label":
        frame["label"] = frame["label"].astype(object)
        frame.loc[frame.index[0], "label"] = True
    elif mutate == "weekend":
        frame.loc[frame.index[0], "session_date"] = "2024-01-06"
        frame.loc[frame.index[0], "fill_date"] = "2024-01-06"
        frame.loc[frame.index[0], "outcome_end_session"] = "2024-01-08"
    elif mutate == "mismatch":
        frame.loc[frame.index[0], "train_block"] = 4
    elif mutate == "noncausal":
        frame.loc[frame.index[1], "fill_date"] = sessions[0].isoformat()
    elif mutate == "one_class":
        frame["label"] = 1
    elif mutate == "same_roots":
        for block in blocks:
            block["roots"] = list(ROOTS)
        frame["root"] = "AAPL"
    def fail_features(*_args, **_kwargs):
        raise AssertionError("feature builder ran on an invalid path")

    monkeypatch.setattr(
        "scripts.ops_train_flow_score._build_features", fail_features
    )
    with pytest.raises(GeometryError, match=reason):
        _paths(frame, blocks, sessions, 5)


def test_source_census_reports_raw_rows_and_not_an_effective_n():
    rows = _rows()
    census = source_census_descriptor(
        rows,
        sealed_at="2026-01-31T12:00:00Z",
        bucket="8_90",
        availability_cutoff="2026-01-31T00:00:00Z",
    )
    assert census["row_count"] == len(rows)
    assert "effective_n" not in census
    assert set(census) == {
        "schema",
        "sealed_at",
        "row_count",
        "projection_sha256",
        "anchors",
    }


def test_injected_source_group_is_rejected_before_grade_io():
    rows = _rows()
    receipt = _receipt(rows)
    assert receipt["study_spec"]["schema"] == SPEC_SCHEMA
    # Constructor stays on a valid v1 schedule. The read sees an explicit
    # schema hand-tamper plus the matching spec digest, still without blocks.
    receipt["study_spec"]["schema"] = SPEC_SCHEMA_V2
    receipt["study"]["spec_digest"] = _digest(receipt["study_spec"])
    source = pd.DataFrame(rows)
    source["train_block"] = 0
    with pytest.raises(AdmissionError, match="admission_source_group_injected"):
        validate_admission_receipt(
            receipt,
            source,
            bucket="8_90",
            expected_study=_expected(receipt),
            validation_at="2026-10-03T18:00:00Z",
            stage_receipt_resolver=lambda key: STAGE_BYTES[key],
        )


def test_member_cannot_inject_a_group_field():
    with pytest.raises(AdmissionError, match="admission_source_group_injected"):
        _member({"event_id": "a", "group": "0"}, "0_7")


def _stage_row(eid: str, root: str, session: date, bucket: str) -> dict:
    day = session.isoformat()
    event = {
        "id": eid,
        "root": root,
        "ts": f"{day}T15:00:00Z",
        "observed_at": f"{day}T15:00:00Z",
        "decision_at": f"{day}T15:00:00Z",
    }
    key = f"live_flow/events/{day}.jsonl"
    records = [
        {"schema": "live_flow.event_stage/v1", "kind": "decision", "event_id": eid, "event": event},
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "availability",
            "event_id": eid,
            "available_at": f"{day}T15:01:00Z",
        },
    ]
    raw = b"".join(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for record in records
    )
    STAGE_BYTES[key] = raw
    from lib.live_flow_event_stage import parse_stage_bytes

    proof = parse_stage_bytes(raw, expected_session_date=day, source_stage_key=key)[0]
    dte = {"0_7": "1_7d", "8_90": "8_30d", "90p": "90p"}[bucket]
    return {
        "event_id": eid,
        "root": root,
        "source": "live_feed",
        "detector_version": "detector-v1",
        "model_bucket": bucket,
        "dte_bucket": dte,
        "prior_oi": 1000,
        "zerodte": False,
        "decision_at": proof["decision_at"],
        "available_at": proof["available_at"],
        "source_stage_observed_at": f"{day}T15:02:00Z",
        "source_stage_key": key,
        "source_stage_schema": proof["source_stage_schema"],
        "source_stage_prefix_records": proof["source_stage_prefix_records"],
        "source_stage_prefix_sha256": proof["source_stage_prefix_sha256"],
    }


def test_v2_assigns_train_block_from_the_spec_and_rejects_a_bad_schedule_before_grades(tmp_path):
    sessions, blocks = _block_schedule(date(2024, 1, 2), 12)
    later = _sessions(sessions[-1] + timedelta(days=1), 3)
    members = [
        _stage_row(f"train-{block['id']}", block["roots"][0], date.fromisoformat(block["first_session"]), "0_7")
        for block in blocks
    ]
    outside = _stage_row("outside-root", "MSFT", sessions[1], "0_7")
    others = [
        _stage_row("cal-fit", "TSLA", later[0], "0_7"),
        _stage_row("cal-eval", "AMD", later[1], "0_7"),
        _stage_row("oos", "NFLX", later[2], "0_7"),
    ]
    source_rows = members + [outside] + others

    def _window(day: date) -> dict:
        return {"start": f"{day.isoformat()}T00:00:00Z", "end": f"{day.isoformat()}T23:59:00Z"}

    def _population(rows, roots, window):
        declared = []
        for row in rows:
            decision = pd.Timestamp(row["decision_at"])
            opened, fill, ends = _endpoints(decision, "0_7")
            declared.append(
                {
                    **row,
                    "planned_fill_open": opened,
                    "planned_fill_date": fill,
                    "planned_outcome_end_sessions": ends,
                }
            )
        return {
            "window": window,
            "roots": list(roots),
            "members": declared,
        }

    train_window = {
        "start": f"{sessions[0].isoformat()}T00:00:00Z",
        "end": f"{sessions[-1].isoformat()}T23:59:00Z",
    }
    populations = {
        "train": _population(members, ROOTS, train_window),
        "calibration_fit": _population([others[0]], ["TSLA"], _window(later[0])),
        "calibration_eval": _population([others[1]], ["AMD"], _window(later[1])),
        "final_oos": _population([others[2]], ["NFLX"], _window(later[2])),
    }
    # populations passed to the receipt keep members; the spec keeps roots and window.
    receipt_populations = {
        name: {"window": item["window"], "members": item["members"]}
        for name, item in populations.items()
    }
    study = {
        "study_ref": "FS5-PREFIT-TEST",
        "evaluation_spec_version": "fs5-v1",
        "source": "live_feed",
        "detector_version": "detector-v1",
        "model_bucket": "0_7",
        "calendar": "NYSE-rule-calendar/v1",
        "horizons": [5],
        "frozen_at": "2024-01-01T00:00:00Z",
        "availability_cutoff": "2024-06-01T00:00:00Z",
        "admitted_at": "2024-06-02T00:00:00Z",
        "source_census": source_census_descriptor(
            source_rows,
            sealed_at="2024-06-01T12:00:00Z",
            bucket="0_7",
            availability_cutoff="2024-06-01T00:00:00Z",
        ),
    }
    spec = {
        key: study[key]
        for key in (
            "evaluation_spec_version",
            "source",
            "detector_version",
            "model_bucket",
            "calendar",
            "horizons",
        )
    }
    spec["schema"] = SPEC_SCHEMA_V2
    spec["fixed_availability_cutoff"] = study["availability_cutoff"]
    spec["train_blocks"] = blocks
    spec["populations"] = {
        name: {"roots": item["roots"], "window": item["window"]}
        for name, item in populations.items()
    }
    receipt = build_admission_receipt(
        study=study,
        study_spec=spec,
        populations=receipt_populations,
        exclusions={"outside-root": "outside_declared_root_block"},
    )
    assert receipt["study"]["evaluation_spec_version"] == "fs5-v1"
    assert receipt["study_spec"]["schema"] == SPEC_SCHEMA_V2
    admitted = validate_admission_receipt(
        receipt,
        pd.DataFrame(source_rows),
        bucket="0_7",
        expected_study=_expected(receipt),
        validation_at="2024-06-03T00:00:00Z",
        stage_receipt_resolver=lambda key: STAGE_BYTES[key],
    )
    assigned = {
        str(row.event_id): row.train_block
        for row in admitted.itertuples(index=False)
        if row.population == "train"
    }
    assert assigned == {f"train-{block_id}": block_id for block_id in range(6)}
    assert "outside-root" not in set(admitted["event_id"])

    broken = json.loads(json.dumps(receipt))
    broken["study_spec"]["train_blocks"] = broken["study_spec"]["train_blocks"][:-1]
    broken["study"]["spec_digest"] = __import__(
        "lib.flow_score_admission", fromlist=["_digest"]
    )._digest(broken["study_spec"])
    flow_dir = tmp_path / "flow"
    flow_dir.mkdir()
    pd.DataFrame(source_rows).to_parquet(flow_dir / "ledger.parquet", index=False)
    (flow_dir / "fs5_partition.json").write_text(json.dumps(broken))
    import scripts.ops_train_flow_score as trainer

    result = trainer.train_bucket(
        "0_7",
        {
            "fs5_admission_studies": {"0_7": _expected(broken)},
            "label_columns": {"0_7": "spy_excess_5"},
        },
        flow_dir,
        dry_run=False,
        stage_receipt_resolver=lambda key: STAGE_BYTES[key],
    )
    assert result["health"] == "no_fit"
    assert "admission_train_block_ids_invalid" in result["method_geometry_reason"]
    assert not (flow_dir / "grades.parquet").exists()


def test_v1_receipt_does_not_fit_without_frozen_geometry(tmp_path, monkeypatch):
    import scripts.ops_train_flow_score as trainer

    flow_dir = tmp_path / "flow"
    flow_dir.mkdir()
    (flow_dir / "fs5_partition.json").write_text(
        json.dumps({"study_spec": {"schema": SPEC_SCHEMA}, "study": {}})
    )
    populations = ("train", "calibration_fit", "calibration_eval", "final_oos")
    admitted = pd.DataFrame(
        {
            "event_id": [f"e-{name}" for name in populations],
            "population": list(populations),
            "planned_fill_date": ["2024-01-02"] * 4,
            "planned_outcome_end_sessions": [{"5": "2024-01-09"}] * 4,
        }
    )
    pd.DataFrame(
        {
            "event_id": admitted["event_id"],
            "graded_ok": [True, True, True, True],
            "spy_excess_5": [0.1, -0.1, 0.2, -0.2],
            "fill_date": ["2024-01-02"] * 4,
            "outcome_end_session_5": ["2024-01-09"] * 4,
        }
    ).to_parquet(flow_dir / "grades.parquet", index=False)
    monkeypatch.setattr(
        trainer,
        "validate_admission_study_identity",
        lambda *_a, **_k: {"source": "tape_recon", "detector_version": "test-detector"},
    )
    monkeypatch.setattr(
        trainer,
        "_load_serving_cohorts",
        lambda *_a, **_k: pd.DataFrame(
            {"event_id": ["e"], "source": ["tape_recon"], "dte_bucket": ["1_7d"]}
        ),
    )
    monkeypatch.setattr(trainer, "validate_admission_receipt", lambda *_a, **_k: admitted.copy())
    # Maturity still runs. Geometry is the next law; this test stops the fit
    # there by letting that law pass and proving CPCV never starts.
    monkeypatch.setattr(trainer, "build_geometry_plan", lambda *_a, **_k: object())
    monkeypatch.setattr(trainer, "validate_population_partition", lambda *_a, **_k: None)
    monkeypatch.setattr(
        trainer,
        "_build_features",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("features")),
    )
    monkeypatch.setattr(
        trainer,
        "_fit_model",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("fit")),
    )
    result = trainer.train_bucket(
        "0_7",
        {"label_columns": {"0_7": "spy_excess_5"}},
        flow_dir,
        dry_run=False,
    )
    assert result["health"] == "no_fit"
    assert result["method_geometry_reason"].endswith("frozen_cpcv_geometry_missing")
    assert not (tmp_path / "models").exists()


def _execution_frame(bucket: str, length: int):
    embargo = frozen_embargo_sessions(bucket)
    sessions, blocks = _block_schedule(date(2024, 1, 2), length)
    frame = _paired_frame(blocks, sessions, length, bucket=bucket)
    frame["premium"] = np.where(frame["label"].to_numpy() == 1, 1.0, 0.0)
    frame["premium_z"] = frame["premium"]
    frame["dte"] = 30.0
    return sessions, blocks, frame, embargo


def test_selection_executes_360_and_720_and_keeps_the_earlier_tie(monkeypatch):
    import scripts.ops_train_flow_score as trainer

    calls: list[tuple] = []

    def spy(features, labels, weights, params, monotone, columns, seed):
        calls.append((tuple(columns), dict(params), features.copy()))
        return _ConstantModel(0.5)

    monkeypatch.setattr(trainer, "_fit_model", spy)
    sessions, blocks, frame, embargo = _execution_frame("0_7", 12)
    paths = _paths(frame, blocks, sessions, embargo)
    grid = _grid()
    assert len(grid) == 24
    selected = trainer._run_cpcv_selection(
        frame.assign(_label=frame["label"]),
        paths,
        [("off", ["premium"])],
        grid,
        np.ones(len(frame)),
        {},
        42,
    )
    assert selected["executed_fits"] == 360
    assert selected["planned_fits"] == 360
    assert len(calls) == 360
    assert selected["selected_params"] == grid[0]
    assert selected["selected_feature_columns"] == ["premium"]

    calls.clear()
    sessions, blocks, frame, embargo = _execution_frame("8_90", 30)
    paths = _paths(frame, blocks, sessions, embargo)
    selected = trainer._run_cpcv_selection(
        frame.assign(_label=frame["label"]),
        paths,
        [("off", ["premium"]), ("on", ["premium", "dte_X_premium_z"])],
        grid,
        np.ones(len(frame)),
        {},
        42,
    )
    assert selected["executed_fits"] == 720
    assert selected["planned_fits"] == 720
    off = [item for item in calls if "dte_X_premium_z" not in item[0]]
    on = [item for item in calls if item[0][-1] == "dte_X_premium_z"]
    assert len(off) == 360 and len(on) == 360
    assert "dte_X_premium_z" not in off[0][2].columns
    assert list(on[0][2].columns) == ["premium", "dte_X_premium_z"]
    assert not np.allclose(
        on[0][2]["dte_X_premium_z"].to_numpy(),
        on[0][2]["premium"].to_numpy(),
    )
    # Equal scores keep the earlier setting: OFF, then the first grid point.
    assert selected["selected_variant"] == "off"
    assert selected["selected_params"] == grid[0]

    calls.clear()

    def better(features, labels, weights, params, monotone, columns, seed):
        calls.append(dict(params))
        if params["learning_rate"] == 0.2:
            return _ConstantModel(_premium_scores)
        return _ConstantModel(0.5)

    monkeypatch.setattr(trainer, "_fit_model", better)
    narrow = [{"learning_rate": 0.1, "max_iter": 20}, {"learning_rate": 0.2, "max_iter": 20}]
    chosen = trainer._run_cpcv_selection(
        frame.assign(_label=frame["label"]),
        paths,
        [("off", ["premium"])],
        narrow,
        np.ones(len(frame)),
        {},
        42,
    )
    assert chosen["selected_params"]["learning_rate"] == 0.2
    calls.clear()
    monkeypatch.setattr(trainer, "_fit_model", spy)
    tied = trainer._run_cpcv_selection(
        frame.assign(_label=frame["label"]),
        paths,
        [("off", ["premium"])],
        narrow,
        np.ones(len(frame)),
        {},
        42,
    )
    assert tied["selected_params"] == narrow[0]


def test_one_failing_fit_does_not_return_a_partial_selection(monkeypatch):
    import scripts.ops_train_flow_score as trainer

    def boom(features, labels, weights, params, monotone, columns, seed):
        raise RuntimeError("fit-broke")

    monkeypatch.setattr(trainer, "_fit_model", boom)
    sessions, blocks, frame, embargo = _execution_frame("0_7", 12)
    paths = _paths(frame, blocks, sessions, embargo)
    with pytest.raises(RuntimeError, match="fit-broke"):
        trainer._run_cpcv_selection(
            frame.assign(_label=frame["label"]),
            paths,
            [("off", ["premium"])],
            [{"learning_rate": 0.1}],
            np.ones(len(frame)),
            {},
            42,
        )


_BLOCK_EVENTS = 12
_CAL_EVENTS = 30
_POPULATION_GAP = 6


def _flow_cfg(tmp_path) -> dict:
    import yaml

    cfg = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "config" / "flow_score.yml").read_text()
    )
    assert cfg["n_groups"] == 6
    assert cfg["k_test"] == 2
    assert cfg["random_seed"] == 42
    assert cfg["n_bins"] == 10
    assert cfg["n_floors"] == {"bucket": 30, "era_cell": 20}
    assert cfg["dte_interaction"] == {"0_7": False, "8_90": True, "90p": False}
    grid = cfg["hyperparameter_grid"]
    assert grid["learning_rate"] == [0.02, 0.05, 0.1, 0.2]
    assert grid["max_iter"] == [200, 400]
    assert grid["max_leaf_nodes"] == [15, 31, 63]
    cfg = dict(cfg)
    cfg["models_dir"] = str(tmp_path / "models")
    cfg["feature_columns"] = ["premium"]
    return cfg


def _prior_era_start(prior_sessions: int = _BLOCK_EVENTS) -> date:
    probe = _sessions(date(2022, 11, 1), 80)
    first_new = next(index for index, day in enumerate(probe) if day.year >= 2023)
    return probe[first_new - prior_sessions]


def _materialize_world(tmp_path, bucket, sessions, blocks, rows, name):
    import scripts.ops_train_flow_score as trainer

    admitted = pd.DataFrame(rows)
    admitted["premium"] = np.where(admitted["label"].to_numpy() == 1, 1.0, 0.0)
    admitted["premium_z"] = admitted["premium"]
    admitted["dte"] = 30.0
    admitted["planned_fill_date"] = admitted["fill_date"]
    horizon = {"0_7": "5", "8_90": "21", "90p": "126"}[bucket]
    admitted["planned_outcome_end_sessions"] = [
        {horizon: end} for end in admitted["outcome_end_session"].astype(str)
    ]
    admitted["train_block"] = pd.array(
        [
            None
            if value is None or (isinstance(value, float) and np.isnan(value))
            else int(value)
            for value in admitted["train_block"]
        ],
        dtype="Int64",
    )
    grades = pd.DataFrame(
        {
            "event_id": admitted["event_id"].astype(str),
            f"spy_excess_{horizon}": np.where(admitted["label"].to_numpy() == 1, 0.02, -0.02),
            "graded_ok": [True] * len(admitted),
            "fill_date": admitted["fill_date"].astype(str),
            f"outcome_end_session_{horizon}": admitted["outcome_end_session"].astype(str),
        }
    )
    if bucket == "90p":
        grades["spy_excess_63"] = grades["spy_excess_126"]
        grades["outcome_end_session_63"] = grades["outcome_end_session_126"]
    flow = tmp_path / name
    flow.mkdir()
    grades.to_parquet(flow / "grades.parquet", index=False)
    spec = {
        "schema": SPEC_SCHEMA_V2,
        "populations": {
            "train": {
                "window": {
                    "start": f"{sessions[0].isoformat()}T00:00:00Z",
                    "end": f"{sessions[-1].isoformat()}T23:59:00Z",
                },
                "roots": list(ROOTS),
            }
        },
        "train_blocks": blocks,
    }
    (flow / "fs5_partition.json").write_text(json.dumps({"study_spec": spec}))
    return trainer, flow, _flow_cfg(tmp_path), admitted


def _trainer_world(tmp_path, bucket="0_7", *, sufficient=True, start=None, name="flow"):
    """Synthetic one-session label intervals. No production tape and no real fit.

    ``sufficient`` places six blocks of 12 events and three later populations of
    30, separated by six NYSE sessions. The small fixture stays below the
    registered floors on purpose.
    """
    if not sufficient:
        sessions, blocks, frame, embargo = _execution_frame(bucket, 12)
        after = _sessions(sessions[-1] + timedelta(days=3), 40)
        cursor = 0

        def take(count, root, population):
            nonlocal cursor
            chosen = after[cursor : cursor + count]
            cursor = cursor + count + embargo + 1
            return [
                _event(
                    f"{population}-{offset}",
                    root,
                    day,
                    None,
                    offset % 2,
                    bucket=bucket,
                )
                for offset, day in enumerate(chosen)
            ]

        extra = (
            take(4, "TSLA", "calibration_fit")
            + take(4, "AMD", "calibration_eval")
            + take(2, "NFLX", "final_oos")
        )
        train = frame.to_dict("records")
    else:
        if start is None:
            start = date(2024, 1, 2)
        length = _BLOCK_EVENTS
        sessions, blocks = _block_schedule(start, length)
        train = []
        for block in blocks:
            chunk = sessions[block["id"] * length : (block["id"] + 1) * length]
            root = block["roots"][0]
            for offset, day in enumerate(chunk):
                train.append(
                    _event(
                        f"b{block['id']}-{offset}",
                        root,
                        day,
                        block["id"],
                        offset % 2,
                        bucket,
                    )
                )
        gap = max(_POPULATION_GAP, frozen_embargo_sessions(bucket))
        tail = _sessions(sessions[-1] + timedelta(days=1), _CAL_EVENTS * 3 + gap * 4)
        cursor = gap - 1
        extra = []
        for count, root, population in (
            (_CAL_EVENTS, "TSLA", "calibration_fit"),
            (_CAL_EVENTS, "AMD", "calibration_eval"),
            (_CAL_EVENTS, "NFLX", "final_oos"),
        ):
            chosen = tail[cursor : cursor + count]
            if len(chosen) != count:
                raise RuntimeError("synthetic calendar exhausted")
            extra.extend(
                _event(f"{population}-{offset}", root, day, None, offset % 2, bucket)
                for offset, day in enumerate(chosen)
            )
            cursor = cursor + count - 1 + gap
    for row in train:
        row["population"] = "train"
    for row in extra:
        row["population"] = row["event_id"].rsplit("-", 1)[0]
    return _materialize_world(tmp_path, bucket, sessions, blocks, train + extra, name)


def _patch_admission(monkeypatch, trainer, admitted):
    monkeypatch.setattr(
        trainer,
        "validate_admission_study_identity",
        lambda *_a, **_k: {"source": "tape_recon", "detector_version": "test-detector"},
    )
    monkeypatch.setattr(
        trainer,
        "_load_serving_cohorts",
        lambda *_a, **_k: admitted.drop(columns=["population", "train_block", "label"], errors="ignore").assign(
            dte_bucket="1_7d" if admitted["model_bucket"].iloc[0] == "0_7" else "8_30d"
        ),
    )
    monkeypatch.setattr(trainer, "validate_admission_receipt", lambda *_a, **_k: admitted.copy())


def test_trainer_dry_run_floor_and_invalid_path_never_build_features(tmp_path, monkeypatch):
    trainer, flow, cfg, admitted = _trainer_world(tmp_path)
    assert cfg["n_floors"] == {"bucket": 30, "era_cell": 20}
    assert cfg["n_groups"] == 6 and cfg["k_test"] == 2
    _patch_admission(monkeypatch, trainer, admitted)
    built: list[str] = []
    fitted: list[str] = []
    monkeypatch.setattr(trainer, "_build_features", lambda *a, **k: built.append("features") or (_ for _ in ()).throw(AssertionError("features")))
    monkeypatch.setattr(trainer, "_fit_model", lambda *a, **k: fitted.append("fit") or (_ for _ in ()).throw(AssertionError("fit")))
    dry = trainer.train_bucket("0_7", cfg, flow, dry_run=True)
    # The monkeypatched builder raises if called. A clean dry run never calls it.
    assert built == [] and fitted == []
    assert dry["executed_fits"] == 0
    assert dry["planned_fits"] == 360
    assert dry["planned_paths"] == 15
    assert dry["planned_variants"] == 1
    assert dry["gauntlet_complete"] is False
    assert dry["deployable"] is False
    assert "train" in dry["population_support"]
    train_support = dry["population_support"]["train"]
    assert train_support["raw_rows"] == 72
    assert train_support["distinct_sessions"] >= 72
    assert train_support["effective_n"] >= 72
    assert {"distinct_sessions", "distinct_root_sessions", "effective_n"} <= set(train_support)
    for name in ("calibration_fit", "calibration_eval", "final_oos"):
        support = dry["population_support"][name]
        assert support["raw_rows"] >= 30
        assert support["distinct_sessions"] >= 30
        assert support["effective_n"] >= 30

    keep = admitted["train_block"].isna() | admitted["train_block"].ne(5)
    missing = admitted.loc[keep].copy()
    monkeypatch.setattr(trainer, "validate_admission_receipt", lambda *_a, **_k: missing)
    invalid = trainer.train_bucket("0_7", cfg, flow, dry_run=False)
    assert invalid["health"] == "no_fit"
    assert "cpcv_block_missing" in invalid["method_geometry_reason"]
    assert built == [] and fitted == []
    assert not (tmp_path / "models").exists()


def test_default_floors_stop_before_features(tmp_path, monkeypatch):
    trainer, flow, cfg, admitted = _trainer_world(tmp_path, sufficient=False)
    assert cfg["n_floors"] == {"bucket": 30, "era_cell": 20}
    _patch_admission(monkeypatch, trainer, admitted)
    monkeypatch.setattr(
        trainer,
        "_build_features",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("features")),
    )
    result = trainer.train_bucket("0_7", cfg, flow, dry_run=False)
    assert result["health"] == "no_fit"
    assert "BELOW-FLOOR" in result["method_geometry_reason"]
    assert "bucket_floor=30" in result["method_geometry_reason"]
    support = result["population_support"]["train"]
    assert support["raw_rows"] == 12
    assert support["effective_n"] < 30
    assert {"distinct_sessions", "distinct_root_sessions"} <= set(support)


def test_trainer_uses_native_weights_and_a_failed_fit_writes_no_artifact(tmp_path, monkeypatch):
    trainer, flow, cfg, admitted = _trainer_world(tmp_path)
    _patch_admission(monkeypatch, trainer, admitted)

    def legacy(*_args, **_kwargs):
        raise AssertionError("legacy uniqueness_weights was called")

    monkeypatch.setattr("lib.flow_score.uniqueness_weights", legacy)
    calls = {"n": 0}

    def counting_fit(features, labels, weights, params, monotone, columns, seed):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("fit-broke")
        return _ConstantModel(0.5)

    monkeypatch.setattr(trainer, "_fit_model", counting_fit)
    failed = trainer.train_bucket("0_7", cfg, flow, dry_run=False)
    assert failed["health"] == "no_fit"
    assert failed["executed_fits"] == 1
    assert failed["selection_receipt"]["attempted_fits"] == 2
    assert failed["selection_receipt"]["executed_fits"] == 1
    assert "fit-broke" in failed["method_geometry_reason"]
    assert calls["n"] == 2
    assert not (tmp_path / "models").exists()

    calls["n"] = 0

    def complete_fit(features, labels, weights, params, monotone, columns, seed):
        calls["n"] += 1
        return _ConstantModel(_premium_scores)

    monkeypatch.setattr(trainer, "_fit_model", complete_fit)
    result = trainer.train_bucket("0_7", cfg, flow, dry_run=False)
    assert result["health"] == "calibration_insufficient"
    assert result["method_geometry_reason"] == (
        "CALIBRATION_INSUFFICIENT:weighted_bin_method_unavailable"
    )
    assert result["calibration"]["ece_status"] == "weighted_bin_method_unavailable"
    assert result["calibration_ready"] is False
    assert result["deployable"] is False
    assert result["gauntlet_complete"] is False
    assert result["executed_fits"] == 360
    selection = result["selection_receipt"]
    assert selection["executed_fits"] == 360
    assert selection["planned_fits"] == 360
    assert selection["attempted_fits"] == 360
    assert selection["final_fit_attempted"] is True
    assert selection["final_fit_complete"] is True
    assert selection["selected_feature_columns"] == ["premium"]
    assert calls["n"] == 360 + 1
    assert not (tmp_path / "models").exists()
    assert list(tmp_path.rglob("*.joblib")) == []
    assert list(tmp_path.rglob("manifest.json")) == []
    columns = selection["selected_feature_columns"]
    served = build_interaction_features(admitted, columns, dte_interaction_enabled=False)
    trained = trainer._build_features(admitted, columns)
    assert list(served.columns) == list(trained.columns) == columns
    eras = [item["era"] for item in result["population_support"]["train"]["eras"]]
    assert eras == ["2017-19", "2020-22", "2023+"]
    present = [
        item["era"]
        for item in result["population_support"]["train"]["eras"]
        if item["status"] == "present"
    ]
    assert present == ["2023+"]


def test_era_floor_and_nonfinite_weight_do_not_fall_back_to_one(tmp_path, monkeypatch):
    trainer, flow, cfg, admitted = _trainer_world(tmp_path, sufficient=False, name="arbitrary")
    admitted = admitted.copy()
    admitted["era"] = "2024"
    _patch_admission(monkeypatch, trainer, admitted)
    monkeypatch.setattr(
        trainer,
        "_build_features",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("features")),
    )
    arbitrary = trainer.train_bucket("0_7", cfg, flow, dry_run=False)
    assert arbitrary["health"] == "no_fit"
    assert "greeks_era_not_canonical" in arbitrary["method_geometry_reason"]

    missing = admitted.drop(columns=["era"]).copy()
    missing["era"] = None
    _patch_admission(monkeypatch, trainer, missing)
    null_era = trainer.train_bucket("0_7", cfg, flow, dry_run=False)
    assert null_era["health"] == "no_fit"
    assert "greeks_era_null_contradiction" in null_era["method_geometry_reason"]

    trainer, flow, cfg, admitted = _trainer_world(
        tmp_path, start=_prior_era_start(), name="sparse"
    )
    _patch_admission(monkeypatch, trainer, admitted)
    sparse = trainer.train_bucket("0_7", cfg, flow, dry_run=False)
    assert sparse["health"] == "no_fit"
    assert "ERA-SPARSE" in sparse["method_geometry_reason"]
    assert "2020-22" in sparse["method_geometry_reason"]
    assert "era_floor=20" in sparse["method_geometry_reason"]
    assert "BELOW-FLOOR" not in sparse["method_geometry_reason"]

    trainer, flow, cfg, admitted = _trainer_world(tmp_path, sufficient=False, name="nonfinite")
    _patch_admission(monkeypatch, trainer, admitted)

    def nonfinite(frame):
        return pd.Series(np.nan, index=frame["event_id"].astype(str))

    monkeypatch.setattr("lib.flow_score.uniqueness_weights_nyse_intervals", nonfinite)
    fallen = trainer.train_bucket("0_7", cfg, flow, dry_run=False)
    assert fallen["health"] == "no_fit"
    assert "uniqueness_weight_nonfinite" in fallen["method_geometry_reason"]


def test_burst_of_prints_does_not_inflate_support_and_legacy_helper_still_exists():
    frame = pd.DataFrame(
        [
            _event(f"burst-{index}", "AAPL", date(2024, 1, 2), 0, index % 2)
            for index in range(6)
        ]
    )
    weights = uniqueness_weights_nyse_intervals(frame)
    assert float(weights.sum()) == pytest.approx(1.0)
    assert len(weights) == 6
    from scripts.ops_train_flow_score import _population_support

    support = _population_support(frame, weights.to_numpy(), era_floor=20)
    assert support["raw_rows"] == 6
    assert support["effective_n"] == pytest.approx(1.0)
    assert support["effective_n"] != support["raw_rows"]
    legacy = uniqueness_weights(
        pd.DataFrame({"event_id": ["only"], "session_date": [date(2024, 1, 2)], "root": ["AAPL"]}),
        horizon_days=5,
    )
    assert float(legacy.iloc[0]) == pytest.approx(1.0)
