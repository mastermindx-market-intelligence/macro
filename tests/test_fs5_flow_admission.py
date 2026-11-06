from __future__ import annotations
import hashlib
import json
import importlib.util
from pathlib import Path
import sys
import types
import pandas as pd
import pytest
import lib.flow_score_admission as admission
from lib.flow_score_admission import (
    AdmissionError,
    _digest,
    _endpoints,
    build_admission_receipt,
    closed_source_projection,
    index_population_excluded_mask,
    source_census_descriptor,
    validate_admission_receipt as _validate_admission_receipt,
    verify_raw_stage_receipts,
)

STAGE_BYTES: dict[str, bytes] = {}


def validate_admission_receipt(*args, **kwargs):
    kwargs.setdefault("stage_receipt_resolver", lambda key: STAGE_BYTES[key])
    kwargs.setdefault("validation_at", "2026-10-03T18:00:00Z")
    return _validate_admission_receipt(*args, **kwargs)


def _row(eid, root, day):
    event = {
        "id": eid,
        "root": root,
        "ts": f"2026-01-{day:02d}T14:00:00Z",
        "observed_at": f"2026-01-{day:02d}T14:00:00Z",
        "decision_at": f"2026-01-{day:02d}T14:00:00Z",
    }
    key = f"live_flow/events/2026-01-{day:02d}.jsonl"
    records = [
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "decision",
            "event_id": eid,
            "event": event,
        },
        {
            "schema": "live_flow.event_stage/v1",
            "kind": "availability",
            "event_id": eid,
            "available_at": f"2026-01-{day:02d}T14:01:00Z",
        },
    ]
    raw = b"".join(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for record in records
    )
    STAGE_BYTES[key] = raw
    from lib.live_flow_event_stage import parse_stage_bytes

    proof = parse_stage_bytes(
        raw, expected_session_date=key[-16:-6], source_stage_key=key
    )[0]
    return {
        "event_id": eid,
        "root": root,
        "source": "live_feed",
        "detector_version": "detector-v1",
        "model_bucket": "8_90",
        "dte_bucket": "8_30d",
        "prior_oi": 1000,
        "zerodte": False,
        "decision_at": proof["decision_at"],
        "available_at": proof["available_at"],
        "source_stage_observed_at": f"2026-01-{day:02d}T14:02:00Z",
        "source_stage_key": key,
        "source_stage_schema": proof["source_stage_schema"],
        "source_stage_prefix_records": proof["source_stage_prefix_records"],
        "source_stage_prefix_sha256": proof["source_stage_prefix_sha256"],
    }


def _receipt(rows):
    names = ("train", "calibration_fit", "calibration_eval", "final_oos")
    pops = {}
    for name, row in zip(names, rows):
        decision = pd.Timestamp(row["decision_at"])
        opened, fill, ends = _endpoints(decision, "8_90")
        day = decision.day
        pops[name] = {
            "window": {
                "start": f"2026-01-{day:02d}T00:00:00Z",
                "end": f"2026-01-{day:02d}T23:59:00Z",
            },
            "members": [
                {
                    **row,
                    "planned_fill_open": opened,
                    "planned_fill_date": fill,
                    "planned_outcome_end_sessions": ends,
                }
            ],
        }
    study = {
        "study_ref": "FS5-EXTERNAL-TEST",
        "evaluation_spec_version": "fs5-v1",
        "source": "live_feed",
        "detector_version": "detector-v1",
        "model_bucket": "8_90",
        "calendar": "NYSE-rule-calendar/v1",
        "horizons": [21],
        "frozen_at": "2026-01-01T00:00:00Z",
        "availability_cutoff": "2026-01-31T00:00:00Z",
        "admitted_at": "2026-02-01T00:00:00Z",
        "source_census": source_census_descriptor(
            rows,
            sealed_at="2026-01-31T12:00:00Z",
            bucket="8_90",
            availability_cutoff="2026-01-31T00:00:00Z",
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
    spec["fixed_availability_cutoff"] = study["availability_cutoff"]
    spec["populations"] = {
        name: {"roots": [declared["members"][0]["root"]], "window": declared["window"]}
        for name, declared in pops.items()
    }
    return build_admission_receipt(
        study=study, study_spec=spec, populations=pops, exclusions={}
    )


def _rows():
    return [
        _row(e, r, d)
        for e, r, d in (
            ("a", "AAPL", 2),
            ("b", "MSFT", 5),
            ("c", "NVDA", 6),
            ("d", "TSLA", 7),
        )
    ]


def _expected(receipt):
    return {
        key: receipt["study"][key]
        for key in ("study_ref", "spec_digest", "frozen_at", "source_census")
    }


def test_valid_four_root_ordered_source_admission_is_outcome_blind():
    receipt = _receipt(_rows())
    admitted = validate_admission_receipt(
        receipt, pd.DataFrame(_rows()), bucket="8_90", expected_study=_expected(receipt)
    )
    assert admitted.population.tolist() == [
        "train",
        "calibration_fit",
        "calibration_eval",
        "final_oos",
    ]


@pytest.mark.parametrize(
    "change, reason",
    [
        (
            lambda receipt, source: receipt.update(schema="old"),
            "admission_schema_unknown",
        ),
        (
            lambda receipt, source: receipt["populations"]["train"]["members"][0].__setitem__(
                "source_stage_prefix_sha256", "0" * 64
            ),
            "admission_source_receipt_changed",
        ),
    ],
)
def test_bad_receipts_fail_before_outcomes(change, reason):
    rows = _rows()
    receipt = _receipt(rows)
    source = pd.DataFrame(rows)
    change(receipt, source)
    with pytest.raises(AdmissionError, match=reason):
        validate_admission_receipt(
            receipt, source, bucket="8_90", expected_study=_expected(receipt)
        )


def test_root_overlap_and_late_observed_clock_reject_after_valid_spec_binding():
    rows = _rows()
    rows[1]["root"] = "AAPL"
    receipt = _receipt(rows)
    source = pd.DataFrame(rows)
    receipt["populations"]["calibration_fit"]["members"][0]["root"] = "AAPL"
    receipt["study_spec"]["populations"]["calibration_fit"]["roots"] = ["AAPL"]
    receipt["study"]["spec_digest"] = _digest(receipt["study_spec"])
    with pytest.raises(AdmissionError, match="roots_not_globally_disjoint"):
        validate_admission_receipt(
            receipt, source, bucket="8_90", expected_study=_expected(receipt)
        )
    rows = _rows()
    receipt = _receipt(rows)
    source = pd.DataFrame(rows)
    # The original census stays sealed. Moving the observation past the cutoff
    # changes the closed projection, so the seal fails before the window check.
    receipt["populations"]["train"]["members"][0][
        "source_stage_observed_at"
    ] = "2026-02-02T15:00:00Z"
    source.loc[source.event_id == "a", "source_stage_observed_at"] = (
        "2026-02-02T15:00:00Z"
    )
    receipt["study"]["spec_digest"] = _digest(receipt["study_spec"])
    with pytest.raises(AdmissionError, match="source_census_mismatch"):
        validate_admission_receipt(
            receipt, source, bucket="8_90", expected_study=_expected(receipt)
        )


def test_shifted_fill_or_90p_endpoint_cannot_be_declared():
    rows = _rows()
    receipt = _receipt(rows)
    receipt["populations"]["train"]["members"][0]["planned_fill_date"] = "2026-01-02"
    receipt["study"]["spec_digest"] = _digest(receipt["study_spec"])
    with pytest.raises(AdmissionError, match="calendar_boundary"):
        validate_admission_receipt(
            receipt,
            pd.DataFrame(rows),
            bucket="8_90",
            expected_study=_expected(receipt),
        )
    receipt = _receipt(rows)
    receipt["study"]["model_bucket"] = "90p"
    receipt["study"]["horizons"] = [63, 126]
    with pytest.raises(AdmissionError, match="spec_identity"):
        validate_admission_receipt(
            receipt, pd.DataFrame(rows), bucket="90p", expected_study=_expected(receipt)
        )


def test_source_with_grade_column_is_refused():
    source = pd.DataFrame(_rows())
    source["spy_excess_21"] = 0.1
    receipt = _receipt(_rows())
    with pytest.raises(AdmissionError, match="source_rows_include_outcomes"):
        validate_admission_receipt(
            receipt, source, bucket="8_90", expected_study=_expected(receipt)
        )


def test_self_consistent_receipt_is_not_external_preregistration():
    receipt = _receipt(_rows())
    with pytest.raises(AdmissionError, match="expected_study_missing"):
        validate_admission_receipt(receipt, pd.DataFrame(_rows()), bucket="8_90")
    expected = _expected(receipt)
    expected["study_ref"] = "other"
    with pytest.raises(AdmissionError, match="expected_study_mismatch"):
        validate_admission_receipt(
            receipt, pd.DataFrame(_rows()), bucket="8_90", expected_study=expected
        )


def test_raw_stage_prefix_is_reparsed_not_trusted_as_nonnull():
    row = _rows()[0]
    with pytest.raises(AdmissionError, match="resolver_unavailable"):
        verify_raw_stage_receipts(pd.DataFrame([row]), None)
    assert (
        verify_raw_stage_receipts(pd.DataFrame([row]), lambda key: STAGE_BYTES[key])
        is None
    )
    row["source_stage_prefix_sha256"] = "0" * 64
    with pytest.raises(AdmissionError, match="raw_stage_receipt_mismatch"):
        verify_raw_stage_receipts(pd.DataFrame([row]), lambda key: STAGE_BYTES[key])


@pytest.mark.parametrize(
    "bucket,horizons", [("0_7", (5,)), ("8_90", (21,)), ("90p", (63, 126))]
)
def test_join_grade_boundaries_requires_all_exact_native_endpoints(bucket, horizons):
    module_path = Path(__file__).parents[1] / "scripts" / "ops_train_flow_score.py"
    spec = importlib.util.spec_from_file_location("fs5_grade_boundaries", module_path)
    trainer = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(trainer)
    _, fill, ends = _endpoints(pd.Timestamp("2026-01-02T14:00:00Z"), bucket)
    admitted = pd.DataFrame(
        [
            {
                "event_id": "e",
                "planned_fill_date": "2026-01-05",
                "planned_outcome_end_sessions": {
                    str(h): ends[str(h)] for h in horizons
                },
            }
        ]
    )
    grade = {
        "event_id": "e",
        "graded_ok": True,
        "fill_date": "2026-01-05",
        "spy_excess_5": 0.1,
        "spy_excess_21": 0.1,
        "spy_excess_63": 0.1,
        "spy_excess_126": 0.1,
    }
    for h in horizons:
        grade[f"outcome_end_session_{h}"] = ends[str(h)]
    cfg = {"label_columns": {bucket: f"spy_excess_{horizons[0]}"}}
    joined = trainer._join_grade_boundaries(
        admitted, pd.DataFrame([grade]), bucket, cfg
    )
    expected_end = 126 if bucket == "90p" else horizons[0]
    assert joined["outcome_end_session"].iloc[0] == ends[str(expected_end)]
    if bucket == "90p":
        assert joined["outcome_end_session_126"].iloc[0] == ends["126"]
    bad = pd.DataFrame([grade])
    bad[f"outcome_end_session_{horizons[-1]}"] = "shifted"
    with pytest.raises(ValueError, match="actual_outcome_end_session_mismatch"):
        trainer._join_grade_boundaries(admitted, bad, bucket, cfg)
    bad = pd.DataFrame([grade])
    bad["fill_date"] = "shifted"
    with pytest.raises(ValueError, match="actual_fill_date_mismatch"):
        trainer._join_grade_boundaries(admitted, bad, bucket, cfg)

    if bucket == "90p":
        bad = dict(grade)
        bad["spy_excess_126"] = float("nan")
        assert (
            trainer._join_grade_boundaries(admitted, pd.DataFrame([bad]), bucket, cfg)[
                "_label"
            ]
            .isna()
            .all()
        )
    with pytest.raises(ValueError, match="registered_label_mismatch"):
        trainer._join_grade_boundaries(
            admitted,
            pd.DataFrame([grade]),
            bucket,
            {"label_columns": {bucket: "fwd_ret_21"}},
        )


def test_join_grade_boundaries_rejects_duplicate_or_missing_native_grade_fields():
    module_path = Path(__file__).parents[1] / "scripts" / "ops_train_flow_score.py"
    spec = importlib.util.spec_from_file_location("fs5_grade_negative", module_path)
    trainer = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(trainer)
    admitted = pd.DataFrame(
        [
            {
                "event_id": "e",
                "planned_fill_date": "2026-01-05",
                "planned_outcome_end_sessions": {"21": "2026-02-21"},
            }
        ]
    )
    grade = {
        "event_id": "e",
        "graded_ok": True,
        "fill_date": "2026-01-05",
        "spy_excess_21": 0.1,
        "outcome_end_session_21": "2026-02-21",
    }
    cfg = {"label_columns": {"8_90": "spy_excess_21"}}
    with pytest.raises(ValueError, match="duplicate_grade_event_id"):
        trainer._join_grade_boundaries(
            admitted, pd.DataFrame([grade, grade]), "8_90", cfg
        )
    for field in ("graded_ok", "outcome_end_session_21"):
        bad = dict(grade)
        bad.pop(field)
        with pytest.raises(ValueError, match="grade boundaries missing"):
            trainer._join_grade_boundaries(admitted, pd.DataFrame([bad]), "8_90", cfg)
    for value, ok in ((float("nan"), True), (0.1, "true")):
        bad = dict(grade)
        bad["spy_excess_21"] = value
        bad["graded_ok"] = ok
        joined = trainer._join_grade_boundaries(
            admitted, pd.DataFrame([bad]), "8_90", cfg
        )
        assert pd.isna(joined["_label"].iloc[0])


@pytest.mark.parametrize(
    "receipt_kind",
    ("absent", "malformed", "mutated", "source_tampered", "raw_mutated", "late"),
)
def test_trainer_admission_failure_never_opens_grades_features_or_models(
    tmp_path, monkeypatch, receipt_kind
):
    module_path = Path(__file__).parents[1] / "scripts" / "ops_train_flow_score.py"
    module_spec = importlib.util.spec_from_file_location(
        "fs5_proposal_trainer", module_path
    )
    trainer = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(trainer)
    flow_dir = tmp_path / "flow_signals"
    flow_dir.mkdir()
    rows = _rows()
    receipt = _receipt(rows)
    expected = _expected(receipt)
    source = pd.DataFrame(rows)
    source["dte_bucket"] = "8_30d"
    source["prior_oi"] = 1000.0
    source["zerodte"] = False
    if receipt_kind == "mutated":
        receipt["populations"]["train"]["members"][0][
            "source_stage_prefix_sha256"
        ] = "0" * 64
    if receipt_kind == "source_tampered":
        source.loc[source.event_id == "a", "source_stage_prefix_sha256"] = "0" * 64
    if receipt_kind == "raw_mutated":
        key = rows[0]["source_stage_key"]
        STAGE_BYTES[key] = STAGE_BYTES[key].replace(b"{", b"{ ", 1)
    if receipt_kind == "late":
        source.loc[source.event_id == "a", "source_stage_observed_at"] = (
            "2026-01-05T15:00:00Z"
        )
        receipt["populations"]["train"]["members"][0][
            "source_stage_observed_at"
        ] = "2026-01-05T15:00:00Z"
    if receipt_kind == "malformed":
        (flow_dir / "fs5_partition.json").write_text("{")
    elif receipt_kind != "absent":
        (flow_dir / "fs5_partition.json").write_text(json.dumps(receipt))
    monkeypatch.setattr(trainer, "_load_serving_cohorts", lambda *_a, **_k: source)
    statted: list[str] = []
    real_exists = Path.exists

    def spy_exists(self: Path) -> bool:
        if self.name == "grades.parquet":
            statted.append(self.name)
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", spy_exists)
    monkeypatch.setattr(
        trainer.pd,
        "read_parquet",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("grades read")),
    )
    monkeypatch.setattr(
        trainer,
        "_build_features",
        lambda *_: (_ for _ in ()).throw(AssertionError("features built")),
    )
    monkeypatch.setattr(
        trainer,
        "_fit_model",
        lambda *_: (_ for _ in ()).throw(AssertionError("model fit")),
    )
    monkeypatch.setattr(
        "sklearn.isotonic.IsotonicRegression.fit",
        lambda *_: (_ for _ in ()).throw(AssertionError("calibrator fit")),
    )
    cfg = {
        "model_bucket_map": {"8_30d": "8_90"},
        "label_columns": {"8_90": "spy_excess_21"},
        "fs5_admission_studies": {"8_90": expected},
    }
    result = trainer.train_bucket(
        "8_90", cfg, flow_dir, stage_receipt_resolver=lambda key: STAGE_BYTES[key]
    )
    assert result["health"] == "no_fit"
    expected_reason = {
        "mutated": "source_receipt_changed",
        "source_tampered": "source_census_mismatch",
        "raw_mutated": "raw_stage_prefix_mismatch",
        "late": "source_census_mismatch",
    }.get(receipt_kind)
    if expected_reason:
        assert expected_reason in result["method_geometry_reason"]
    assert statted == []
    assert receipt["study"]["source_census"]["row_count"] == 4


def test_independently_sealed_census_covers_the_original_universe():
    rows = _rows()
    receipt = _receipt(rows)
    census = receipt["study"]["source_census"]
    assert census["schema"] == "flow_signals.fs5_source_census/v1"
    assert census["row_count"] == 4
    assert len(census["anchors"]) == 4
    anchors = {anchor["source_stage_key"]: anchor for anchor in census["anchors"]}
    assert set(anchors) == {row["source_stage_key"] for row in rows}
    for row in rows:
        anchor = anchors[row["source_stage_key"]]
        assert set(anchor) == {
            "source_stage_key",
            "source_stage_schema",
            "prefix_records",
            "prefix_sha256",
        }
        assert anchor["source_stage_schema"] == row["source_stage_schema"]
        assert anchor["prefix_records"] == str(row["source_stage_prefix_records"])
        assert anchor["prefix_sha256"] == row["source_stage_prefix_sha256"]
    admitted = validate_admission_receipt(
        receipt, pd.DataFrame(rows), bucket="8_90", expected_study=_expected(receipt)
    )
    assert admitted.event_id.tolist() == ["a", "b", "c", "d"]


def test_dual_omission_of_a0_fails_while_its_raw_prefix_remains():
    rows = _rows()
    first = rows[0]
    key = first["source_stage_key"]
    original = STAGE_BYTES[key]
    STAGE_BYTES[key] = original.replace(b'"a"', b'"a0"') + original
    from lib.live_flow_event_stage import parse_stage_bytes

    parsed_rows = parse_stage_bytes(
        STAGE_BYTES[key], expected_session_date="2026-01-02", source_stage_key=key
    )
    parsed = {item["event"]["id"]: item for item in parsed_rows}
    assert [item["event"]["id"] for item in parsed_rows] == ["a0", "a"]
    a0 = dict(first)
    a0["event_id"] = "a0"
    for field in (
        "decision_at",
        "available_at",
        "source_stage_prefix_records",
        "source_stage_prefix_sha256",
    ):
        a0[field] = parsed["a0"][field]
        rows[0][field] = parsed["a"][field]
    complete = [a0, *rows]
    receipt = _receipt(rows)
    receipt["study"]["source_census"] = source_census_descriptor(
        complete,
        sealed_at="2026-01-31T12:00:00Z",
        bucket="8_90",
        availability_cutoff="2026-01-31T00:00:00Z",
    )
    expected = _expected(receipt)
    member_ids = [
        member["event_id"]
        for population in receipt["populations"].values()
        for member in population["members"]
    ]
    assert "a0" not in member_ids
    with pytest.raises(AdmissionError, match="source_census_mismatch"):
        validate_admission_receipt(
            receipt, pd.DataFrame(rows), bucket="8_90", expected_study=expected
        )


def test_omitting_every_row_of_one_anchor_fails():
    rows = _rows()
    receipt = _receipt(rows)
    expected = _expected(receipt)
    anchor_key = rows[1]["source_stage_key"]
    kept = [row for row in rows if row["source_stage_key"] != anchor_key]
    receipt["populations"]["calibration_fit"]["members"] = []
    with pytest.raises(AdmissionError, match="source_census_mismatch"):
        validate_admission_receipt(
            receipt, pd.DataFrame(kept), bucket="8_90", expected_study=expected
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("prior_oi", 10),
        ("oi", 10),
        ("open_interest", 10),
        ("zerodte", True),
        ("dte_bucket", "0d"),
    ],
)
def test_each_selection_input_tamper_fails_the_sealed_census(field, value):
    rows = _rows()
    receipt = _receipt(rows)
    expected = _expected(receipt)
    source = pd.DataFrame(rows)
    source.loc[source.event_id == "a", field] = value
    with pytest.raises(AdmissionError, match="source_census_mismatch"):
        validate_admission_receipt(
            receipt, source, bucket="8_90", expected_study=expected
        )


def test_source_declared_model_bucket_is_not_trusted():
    rows = _rows()
    receipt = _receipt(rows)
    expected = _expected(receipt)
    source = pd.DataFrame(rows)
    source.loc[source.event_id == "a", "model_bucket"] = "0_7"
    with pytest.raises(AdmissionError, match="model_bucket_contradicts"):
        validate_admission_receipt(
            receipt, source, bucket="8_90", expected_study=expected
        )


def test_post_cutoff_ledger_row_and_raw_tail_stay_outside_the_seal():
    rows = _rows()
    receipt = _receipt(rows)
    expected = _expected(receipt)
    key = rows[0]["source_stage_key"]
    STAGE_BYTES[key] = STAGE_BYTES[key] + STAGE_BYTES[key].replace(b'"a"', b'"later"')
    extra = dict(rows[0])
    extra["event_id"] = "later"
    extra["source_stage_observed_at"] = "2026-02-02T14:00:00Z"
    admitted = validate_admission_receipt(
        receipt,
        pd.DataFrame([*rows, extra]),
        bucket="8_90",
        expected_study=expected,
    )
    assert admitted.event_id.tolist() == ["a", "b", "c", "d"]


def test_null_legacy_clock_is_not_backfilled_from_the_receipt():
    rows = _rows()
    receipt = _receipt(rows)
    expected = _expected(receipt)
    source = pd.DataFrame(rows)
    for field in ("decision_at", "available_at", "source_stage_observed_at"):
        source.loc[source.event_id == "a", field] = None
    with pytest.raises(AdmissionError, match="source_census_mismatch"):
        validate_admission_receipt(
            receipt, source, bucket="8_90", expected_study=expected
        )
    assert source.loc[source.event_id == "a", "decision_at"].isna().all()
    assert source.loc[source.event_id == "a", "source_stage_observed_at"].isna().all()


def test_census_includes_index_rows_the_population_filter_later_drops():
    rows = _rows()
    index_row = _row("ix", "SPX", 8)
    index_row["prior_oi"] = 100
    receipt = _receipt(rows)
    receipt["study"]["source_census"] = source_census_descriptor(
        [*rows, index_row],
        sealed_at="2026-01-31T12:00:00Z",
        bucket="8_90",
        availability_cutoff="2026-01-31T00:00:00Z",
    )
    expected = _expected(receipt)
    assert expected["source_census"]["row_count"] == 5
    admitted = validate_admission_receipt(
        receipt,
        pd.DataFrame([*rows, index_row]),
        bucket="8_90",
        expected_study=expected,
    )
    assert admitted.event_id.tolist() == ["a", "b", "c", "d"]
    assert "ix" not in admitted.event_id.tolist()
    with pytest.raises(AdmissionError, match="source_census_mismatch"):
        validate_admission_receipt(
            receipt, pd.DataFrame(rows), bucket="8_90", expected_study=expected
        )


def test_receipt_census_cannot_authorize_itself():
    rows = _rows()
    receipt = _receipt(rows)
    expected = _expected(receipt)
    receipt["study"]["source_census"] = {
        **receipt["study"]["source_census"],
        "row_count": receipt["study"]["source_census"]["row_count"] - 1,
    }
    with pytest.raises(AdmissionError, match="source_census_not_external"):
        validate_admission_receipt(
            receipt, pd.DataFrame(rows), bucket="8_90", expected_study=expected
        )


def test_missing_external_census_is_explicit_no_fit_before_grades(tmp_path, monkeypatch):
    module_path = Path(__file__).parents[1] / "scripts" / "ops_train_flow_score.py"
    module_spec = importlib.util.spec_from_file_location(
        "fs5_missing_census_trainer", module_path
    )
    trainer = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(trainer)
    rows = _rows()
    receipt = _receipt(rows)
    expected = _expected(receipt)
    expected.pop("source_census")
    flow_dir = tmp_path / "flow_signals"
    flow_dir.mkdir()
    (flow_dir / "fs5_partition.json").write_text(json.dumps(receipt))
    (flow_dir / "grades.parquet").touch()
    statted: list[str] = []
    real_exists = Path.exists

    def spy_exists(self: Path) -> bool:
        if self.name == "grades.parquet":
            statted.append(self.name)
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", spy_exists)
    monkeypatch.setattr(
        trainer.pd,
        "read_parquet",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("grades read")),
    )
    monkeypatch.setattr(
        trainer,
        "_build_features",
        lambda *_: (_ for _ in ()).throw(AssertionError("features built")),
    )
    monkeypatch.setattr(
        trainer,
        "_fit_model",
        lambda *_: (_ for _ in ()).throw(AssertionError("model fit")),
    )
    result = trainer.train_bucket(
        "8_90",
        {"fs5_admission_studies": {"8_90": expected}},
        flow_dir,
    )
    assert result["health"] == "no_fit"
    assert "source_census_missing" in result["method_geometry_reason"]
    assert statted == []


def _oi_universe():
    """Index row readmitted through oi because the prior_oi column is absent."""
    rows = []
    for row in _rows():
        row["oi"] = row.pop("prior_oi")
        rows.append(row)
    index_row = _row("ix", "SPX", 8)
    index_row["oi"] = index_row.pop("prior_oi")
    index_row["dte_bucket"] = "8_30d"
    rows.append(index_row)
    return rows


def _project(frame: pd.DataFrame, bucket: str = "8_90"):
    return closed_source_projection(
        frame, bucket=bucket, availability_cutoff="2026-01-31T00:00:00Z"
    )


def test_closed_projection_parses_clock_order_and_keeps_observed():
    rows = _rows()
    projected = {item["event_id"]: item for item in _project(pd.DataFrame(rows))}
    observed = rows[0]["source_stage_observed_at"]
    assert projected["a"]["source_stage_observed_at"] == observed
    assert projected["a"]["available_at"] != observed
    assert (
        projected["a"]["decision_at"]
        <= projected["a"]["available_at"]
        <= projected["a"]["source_stage_observed_at"]
    )
    receipt = _receipt(rows)
    source = pd.DataFrame(rows)
    source.loc[source.event_id == "a", "available_at"] = "2026-01-02T13:00:00Z"
    with pytest.raises(AdmissionError, match="source_clocks_invalid"):
        validate_admission_receipt(
            receipt, source, bucket="8_90", expected_study=_expected(receipt)
        )
    assert source.loc[source.event_id == "a", "source_stage_observed_at"].iloc[0] == observed


def test_original_seal_rejects_selection_mutations_without_reseal(tmp_path, monkeypatch):
    module_path = Path(__file__).parents[1] / "scripts" / "ops_train_flow_score.py"
    module_spec = importlib.util.spec_from_file_location(
        "fs5_selection_collision_trainer", module_path
    )
    trainer = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(trainer)
    statted: list[str] = []
    real_exists = Path.exists

    def spy_exists(self: Path) -> bool:
        if self.name == "grades.parquet":
            statted.append(self.name)
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", spy_exists)
    monkeypatch.setattr(
        trainer.pd,
        "read_parquet",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("grades read")),
    )
    monkeypatch.setattr(
        trainer,
        "_build_features",
        lambda *_: (_ for _ in ()).throw(AssertionError("features built")),
    )
    monkeypatch.setattr(
        trainer,
        "_fit_model",
        lambda *_: (_ for _ in ()).throw(AssertionError("model fit")),
    )

    def reject(name: str, rows: list[dict], mutated: pd.DataFrame) -> None:
        receipt = _receipt(rows)
        original = pd.DataFrame(rows)
        before = index_population_excluded_mask(original, "8_90")
        after = index_population_excluded_mask(mutated, "8_90")
        if name == "null_prior_oi":
            ix = original.event_id == "ix"
            assert not bool(before.loc[ix].iloc[0])
            assert bool(after.loc[mutated.event_id == "ix"].iloc[0])
        assert _project(original) != _project(mutated)
        with pytest.raises(AdmissionError, match="source_census_mismatch"):
            validate_admission_receipt(
                receipt,
                mutated,
                bucket="8_90",
                expected_study=_expected(receipt),
            )
        flow_dir = tmp_path / name
        flow_dir.mkdir()
        (flow_dir / "fs5_partition.json").write_text(json.dumps(receipt))
        monkeypatch.setattr(
            trainer, "_load_serving_cohorts", lambda *_a, **_k: mutated
        )
        result = trainer.train_bucket(
            "8_90",
            {"fs5_admission_studies": {"8_90": _expected(receipt)}},
            flow_dir,
            stage_receipt_resolver=lambda key: STAGE_BYTES[key],
        )
        assert result["health"] == "no_fit"
        assert "source_census_mismatch" in result["method_geometry_reason"]
        assert statted == []
        statted.clear()

    oi_rows = _oi_universe()
    oi_frame = pd.DataFrame(oi_rows)
    oi_mutated = oi_frame.copy()
    oi_mutated["prior_oi"] = None
    reject("null_prior_oi", oi_rows, oi_mutated)

    bare = []
    for row in _rows():
        row.pop("zerodte", None)
        bare.append(row)
    bare_frame = pd.DataFrame(bare)
    null_zerodte = bare_frame.copy()
    null_zerodte["zerodte"] = None
    zero = _row("z", "SPX", 9)
    zero.pop("zerodte", None)
    zero["dte_bucket"] = "0d"
    zero["model_bucket"] = "0_7"
    zero["prior_oi"] = 10000
    absent_zero = pd.DataFrame([zero])
    present_zero = absent_zero.copy()
    present_zero["zerodte"] = None
    assert bool(index_population_excluded_mask(absent_zero, "0_7").iloc[0])
    assert not bool(index_population_excluded_mask(present_zero, "0_7").iloc[0])
    assert _project(absent_zero, "0_7") != _project(present_zero, "0_7")
    reject("null_zerodte", bare, null_zerodte)

    flagged = _rows()
    flagged_frame = pd.DataFrame(flagged)
    string_false = flagged_frame.copy()
    string_false["zerodte"] = ["false"] * len(string_false)
    bool_false = pd.DataFrame(
        [{"root": "SPX", "dte_bucket": "0d", "prior_oi": 10000, "zerodte": False}]
    )
    text_false = bool_false.copy()
    text_false["zerodte"] = ["false"]
    assert not bool(index_population_excluded_mask(bool_false, "0_7").iloc[0])
    assert bool(index_population_excluded_mask(text_false, "0_7").iloc[0])
    reject("string_false", flagged, string_false)


def test_root_whitespace_matches_original_seal_only_when_filter_matches():
    rows = _rows()
    index_row = _row("ix", "SPX", 12)
    index_row["prior_oi"] = 100
    rows.append(index_row)
    receipt = _receipt(rows)
    original = pd.DataFrame(rows)
    mutated = original.copy()
    mutated.loc[mutated.event_id == "ix", "root"] = " SPX "
    same_filter = index_population_excluded_mask(original, "8_90").reset_index(
        drop=True
    ).equals(
        index_population_excluded_mask(mutated, "8_90").reset_index(drop=True)
    )
    same_projection = _project(original) == _project(mutated)
    if same_filter:
        assert same_projection
        admitted = validate_admission_receipt(
            receipt, mutated, bucket="8_90", expected_study=_expected(receipt)
        )
        assert admitted.event_id.tolist() == ["a", "b", "c", "d"]
        assert "ix" not in admitted.event_id.tolist()
    else:
        with pytest.raises(AdmissionError, match="source_census_mismatch"):
            validate_admission_receipt(
                receipt, mutated, bucket="8_90", expected_study=_expected(receipt)
            )
