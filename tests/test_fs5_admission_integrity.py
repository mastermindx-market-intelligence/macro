"""Adversarial coverage of actual stage bytes and frozen-source admission."""

import copy
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from lib.flow_score_admission import (
    AdmissionError,
    SOURCE_FIELDS,
    validate_admission_receipt,
    write_admission_receipt,
)
from lib.live_flow_event_stage import parse_stage_bytes

# Sibling fixture import must work when pytest does not put tests/ on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_fs5_flow_admission import STAGE_BYTES, _expected, _receipt, _rows  # noqa: E402

NOW = "2026-10-03T18:00:00Z"


def prepared():
    rows = _rows()
    receipt = _receipt(rows)
    # Pin the external owner's binding before any prospective receipt mutation.
    expected = copy.deepcopy(_expected(receipt))
    return rows, receipt, expected


def admit(rows, receipt, expected):
    return validate_admission_receipt(
        receipt,
        pd.DataFrame(rows),
        bucket="8_90",
        validation_at=NOW,
        expected_study=expected,
        stage_receipt_resolver=lambda key: STAGE_BYTES[key],
    )


def test_real_raw_prefix_mutation_rejected_but_later_append_preserves_receipt():
    rows, receipt, expected = prepared()
    key = rows[0]["source_stage_key"]
    first = STAGE_BYTES[key]
    # Alter only raw whitespace: decoded economics stay identical, prefix proof does not.
    STAGE_BYTES[key] = first.replace(b"{", b"{ ", 1)
    with pytest.raises(AdmissionError, match="raw_stage_receipt_mismatch"):
        admit(rows, receipt, expected)
    STAGE_BYTES[key] = first + first.replace(b'"a"', b'"later-unobserved"')
    accepted = admit(rows, receipt, expected)
    assert accepted.event_id.tolist() == ["a", "b", "c", "d"]
    assert accepted.evaluation_spec_version.eq("fs5-v1").all()
    assert accepted.session_date.tolist() == [
        "2026-01-02",
        "2026-01-05",
        "2026-01-06",
        "2026-01-07",
    ]


def test_multiple_events_for_same_root_within_one_population_are_required():
    rows, receipt, expected = prepared()
    key = rows[0]["source_stage_key"]
    STAGE_BYTES[key] += STAGE_BYTES[key].replace(b'"a"', b'"a2"')
    evidence = parse_stage_bytes(
        STAGE_BYTES[key], expected_session_date="2026-01-02", source_stage_key=key
    )[1]
    second = {
        **rows[0],
        **{f: evidence[f] for f in SOURCE_FIELDS[2:] if f in evidence},
        "event_id": "a2",
    }
    rows.append(second)
    with pytest.raises(AdmissionError, match="eligible_member_omitted"):
        admit(rows, receipt, expected)
    member = {**receipt["populations"]["train"]["members"][0], **second}
    receipt["populations"]["train"]["members"].append(member)
    result = admit(rows, receipt, expected)
    assert result.loc[result.population == "train", "event_id"].tolist() == ["a", "a2"]


def test_parquet_null_legacy_rows_never_restamp_or_block_valid_frozen_rows(tmp_path):
    rows, receipt, expected = prepared()
    legacy = {**rows[0], "event_id": "old"}
    legacy.update({f: None for f in SOURCE_FIELDS[2:]})
    rows.append(legacy)
    receipt["exclusions"]["old"] = "ineligible_legacy"
    path = tmp_path / "source.parquet"
    pd.DataFrame(rows).to_parquet(path)
    loaded = pd.read_parquet(path)
    assert loaded.source_stage_prefix_records.iloc[0] == 2.0
    output = admit(loaded.to_dict("records"), receipt, expected)
    assert len(output) == 4
    assert pd.isna(loaded.loc[loaded.event_id == "old", "decision_at"]).all()
    receipt_path = tmp_path / "fs5_partition.json"
    write_admission_receipt(receipt_path, receipt)
    assert len(admit(rows, json.loads(receipt_path.read_text()), expected)) == 4


def test_cutoff_cannot_expand_and_later_ledger_growth_does_not_expand_membership():
    rows, receipt, expected = prepared()
    added = {
        **rows[0],
        "event_id": "future",
        "source_stage_observed_at": "2026-02-02T14:00:00Z",
    }
    result = admit(rows + [added], receipt, expected)
    assert len(result) == 4
    changed = copy.deepcopy(receipt)
    changed["study"]["availability_cutoff"] = "2026-02-03T00:00:00Z"
    with pytest.raises(AdmissionError, match="cutoff_not_bound"):
        admit(rows, changed, expected)


def test_late_remote_observation_before_endpoint_is_ineligible():
    rows, receipt, expected = prepared()
    rows[0]["source_stage_observed_at"] = "2026-01-05T15:00:00Z"
    receipt["populations"]["train"]["members"][0]["source_stage_observed_at"] = rows[0][
        "source_stage_observed_at"
    ]
    with pytest.raises(AdmissionError, match="observed_after_planned_fill_open"):
        admit(rows, receipt, expected)


@pytest.mark.parametrize("value", [None, [], 1, True, "garbage"])
def test_malformed_documents_are_explicit_admission_errors(value):
    rows, _, expected = prepared()
    with pytest.raises(AdmissionError):
        admit(rows, value, expected)


@pytest.mark.parametrize(
    "clock", ["2026-01-01", ["2026-01-01T00:00:00Z"], "not-a-clock"]
)
def test_unaware_or_malformed_clock_is_not_assumed_utc(clock):
    rows, receipt, expected = prepared()
    receipt["study"]["admitted_at"] = clock
    with pytest.raises(AdmissionError):
        admit(rows, receipt, expected)


def test_future_receipt_and_scalar_member_are_rejected():
    rows, receipt, expected = prepared()
    receipt["study"]["admitted_at"] = "2027-01-01T00:00:00Z"
    with pytest.raises(AdmissionError, match="study_clocks_invalid"):
        admit(rows, receipt, expected)
    receipt = _receipt(rows)
    receipt["populations"]["train"]["members"] = [1]
    with pytest.raises(AdmissionError, match="member_invalid"):
        admit(rows, receipt, expected)


@pytest.mark.parametrize("count", [True, 2.5, float("inf")])
def test_invalid_prefix_counts_are_not_coerced_to_an_integer(count):
    rows, receipt, expected = prepared()
    rows[0]["source_stage_prefix_records"] = count
    receipt["populations"]["train"]["members"][0]["source_stage_prefix_records"] = count
    with pytest.raises(AdmissionError, match="prefix_records_invalid"):
        admit(rows, receipt, expected)


@pytest.mark.parametrize("immature", [False, True])
def test_every_frozen_member_must_mature_before_geometry_or_features(
    tmp_path, monkeypatch, immature
):
    from scripts import ops_train_flow_score as trainer

    rows, receipt, expected = prepared()
    source = pd.DataFrame(rows)
    source["dte_bucket"] = "8_30d"
    source["prior_oi"] = 1000.0
    source["zerodte"] = False
    grades = []
    for population in receipt["populations"].values():
        member = population["members"][0]
        grades.append(
            {
                "event_id": member["event_id"],
                "graded_ok": True,
                "spy_excess_21": 0.1,
                "fill_date": member["planned_fill_date"],
                "outcome_end_session_21": member["planned_outcome_end_sessions"]["21"],
            }
        )
    if immature:
        grades[-1]["spy_excess_21"] = None
    (tmp_path / "fs5_partition.json").write_text(json.dumps(receipt))
    (tmp_path / "grades.parquet").touch()
    observed = []
    monkeypatch.setattr(trainer, "_load_serving_cohorts", lambda *_a, **_k: source)

    def read_grades(path):
        observed.append(Path(path).name)
        return pd.DataFrame(grades)

    from pathlib import Path

    monkeypatch.setattr(trainer.pd, "read_parquet", read_grades)

    class GeometryReached(RuntimeError):
        pass

    def stop_at_geometry(*_args, **_kwargs):
        raise GeometryReached

    monkeypatch.setattr(trainer, "build_geometry_plan", stop_at_geometry)
    monkeypatch.setattr(
        trainer,
        "_build_features",
        lambda *_: pytest.fail("features must not be constructed"),
    )
    cfg = {
        "model_bucket_map": {"8_30d": "8_90"},
        "label_columns": {"8_90": "spy_excess_21"},
        "fs5_admission_studies": {"8_90": expected},
    }
    if immature:
        result = trainer.train_bucket(
            "8_90", cfg, tmp_path, stage_receipt_resolver=lambda key: STAGE_BYTES[key]
        )
        assert result["health"] == "no_fit"
        assert "frozen_cohort_not_fully_mature" in result["method_geometry_reason"]
    else:
        with pytest.raises(GeometryReached):
            trainer.train_bucket(
                "8_90",
                cfg,
                tmp_path,
                stage_receipt_resolver=lambda key: STAGE_BYTES[key],
            )
    assert observed == ["grades.parquet"]


def test_trainer_selects_external_live_source_before_loading_mixed_cohorts(
    tmp_path, monkeypatch
):
    from scripts import ops_train_flow_score as trainer

    rows, receipt, expected = prepared()
    source = pd.DataFrame(rows)
    source["dte_bucket"] = "8_30d"
    source["prior_oi"] = 1000.0
    source["zerodte"] = False
    flow_dir = tmp_path / "flow_signals"
    flow_dir.mkdir()
    source.to_parquet(flow_dir / "ledger.parquet", index=False)
    pd.DataFrame(
        [{"event_id": "tape-only", "source": "tape_recon", "detector_version": "detector-v1"}]
    ).to_parquet(flow_dir / "cohort_tape_recon.parquet", index=False)
    (flow_dir / "fs5_partition.json").write_text(json.dumps(receipt))
    grades = [
        {"event_id": member["event_id"], "graded_ok": True, "spy_excess_21": 0.1,
         "fill_date": member["planned_fill_date"],
         "outcome_end_session_21": member["planned_outcome_end_sessions"]["21"]}
        for population in receipt["populations"].values()
        for member in population["members"]
    ]
    pd.DataFrame(grades).to_parquet(flow_dir / "grades.parquet", index=False)

    class GeometryReached(RuntimeError):
        pass

    monkeypatch.setattr(trainer, "build_geometry_plan", lambda *_a, **_k: (_ for _ in ()).throw(GeometryReached()))
    cfg = {"model_bucket_map": {"8_30d": "8_90"}, "label_columns": {"8_90": "spy_excess_21"}, "fs5_admission_studies": {"8_90": expected}}
    with pytest.raises(GeometryReached):
        trainer.train_bucket("8_90", cfg, flow_dir, stage_receipt_resolver=lambda key: STAGE_BYTES[key])


def test_selected_live_source_filters_cross_source_rows_before_admission(tmp_path):
    from scripts import ops_train_flow_score as trainer

    rows, _, _ = prepared()
    source = pd.DataFrame(rows)
    source.loc[0, "source"] = "tape_recon"
    flow_dir = tmp_path / "flow_signals"
    flow_dir.mkdir()
    source.to_parquet(flow_dir / "ledger.parquet", index=False)
    selected = trainer._load_serving_cohorts(
        flow_dir, "8_90", {}, source="live_feed", detector_version="detector-v1"
    )
    assert selected.event_id.tolist() == ["b", "c", "d"]
    assert selected.source.eq("live_feed").all()


@pytest.mark.parametrize("case", ("external_digest_changed", "unknown_source"))
def test_unbound_or_unknown_source_fails_before_any_cohort_or_grade_read(tmp_path, monkeypatch, case):
    from lib.flow_score_admission import _digest
    from scripts import ops_train_flow_score as trainer

    _rows_value, receipt, expected = prepared()
    if case == "external_digest_changed":
        expected["spec_digest"] = "0" * 64
    else:
        receipt["study"]["source"] = "foreign_source"
        receipt["study_spec"]["source"] = "foreign_source"
        receipt["study"]["spec_digest"] = _digest(receipt["study_spec"])
        expected = _expected(receipt)
    flow_dir = tmp_path / "flow_signals"
    flow_dir.mkdir()
    (flow_dir / "fs5_partition.json").write_text(json.dumps(receipt))
    monkeypatch.setattr(trainer.pd, "read_parquet", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("source or grades read")))
    result = trainer.train_bucket("8_90", {"fs5_admission_studies": {"8_90": expected}}, flow_dir)
    assert result["health"] == "no_fit"
    reason = "expected_study_mismatch:spec_digest" if case == "external_digest_changed" else "source_unknown:foreign_source"
    assert reason in result["method_geometry_reason"]
