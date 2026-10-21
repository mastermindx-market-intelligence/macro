"""Source-only counterexamples for the frozen FS5 method boundary."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scripts.ops_train_flow_score as trainer
from lib.flow_score_geometry import GeometryError, bind_greeks_era
from lib.flow_score_admission import (
    AdmissionError, POPULATIONS, SPEC_SCHEMA_V2,
    build_admission_receipt, validate_admission_receipt,
)
from test_fs5_flow_admission import STAGE_BYTES, _expected, _receipt, _rows
from test_fs5_cpcv_prefit import _block_schedule, _execution_frame, _paths, _grid, _ConstantModel


@pytest.mark.parametrize(("key", "bad"), [
    ("n_groups", 5), ("k_test", 1), ("random_seed", 7), ("n_bins", 9),
    ("ece_threshold", .1), ("n_floors", {"bucket": 1, "era_cell": 1}),
    ("dte_interaction", {"0_7": False, "8_90": False, "90p": False}),
    ("hyperparameter_grid", {"learning_rate": [.1]}),
])
def test_registered_config_drift_is_rejected(key, bad):
    cfg = trainer._load_config()
    trainer._validate_frozen_fit_config(cfg)
    cfg[key] = bad
    with pytest.raises(GeometryError, match="frozen_config_drift"):
        trainer._validate_frozen_fit_config(cfg)


@pytest.mark.parametrize("field", ["learning_rate", "min_samples_leaf", "max_bins", "early_stopping", "class_weight"])
def test_fixed_estimator_and_grid_values_are_pinned(field):
    cfg = trainer._load_config()
    cfg["hyperparameter_grid"][field] = None
    with pytest.raises(GeometryError, match="hyperparameter_grid"):
        trainer._validate_frozen_fit_config(cfg)


@pytest.mark.parametrize("bucket", ["0_7", "8_90", "90p"])
def test_embargo_cannot_drift_even_upward(bucket):
    cfg = trainer._load_config()
    cfg["embargo_days"][bucket] += 1
    with pytest.raises(GeometryError, match="embargo_days"):
        trainer._validate_frozen_fit_config(cfg)


def test_era_boundaries_and_explicit_nulls():
    # Use actual sessions immediately around the registered calendar boundaries.
    frame = pd.DataFrame({"session_date": ["2019-12-31", "2020-01-02", "2022-12-30", "2023-01-03"]})
    assert bind_greeks_era(frame)["era"].tolist() == ["2017-19", "2020-22", "2020-22", "2023+"]
    for raw in (None, np.nan, pd.NA, "2024", "2023+"):
        with pytest.raises(GeometryError, match="greeks_era"):
            bind_greeks_era(frame.iloc[:1].assign(era=raw))


def test_admission_derives_v1_era_from_sealed_source_session():
    rows = _rows()
    receipt = _receipt(rows)
    kwargs = dict(bucket="8_90", expected_study=_expected(receipt),
                  validation_at="2026-10-03T18:00:00Z",
                  stage_receipt_resolver=lambda key: STAGE_BYTES[key])
    admitted = validate_admission_receipt(receipt, pd.DataFrame(rows), **kwargs)
    assert set(admitted["era"]) == {"2023+"}
    for raw in (None, "2024", "2020-22"):
        with pytest.raises(AdmissionError, match="admission_greeks_era"):
            validate_admission_receipt(receipt, pd.DataFrame(rows).assign(era=raw), **kwargs)


@pytest.mark.parametrize(("length", "remove", "reason"), [
    (1, False, "cpcv_path_deterministically_empty"),
    (12, True, "train_block_ids_invalid"),
])
def test_v2_receipt_constructor_refuses_geometry_before_seal(length, remove, reason):
    sessions, blocks = _block_schedule(date(2024, 1, 2), length)
    spec = {"schema": SPEC_SCHEMA_V2,
            "train_blocks": blocks[:-1] if remove else blocks,
            "populations": {"train": {
                "window": {"start": f"{sessions[0]}T00:00:00Z",
                           "end": f"{sessions[-1]}T23:59:00Z"},
                "roots": [block["roots"][0] for block in blocks]}}}
    with pytest.raises(AdmissionError, match=reason):
        build_admission_receipt(study={"model_bucket": "0_7"}, study_spec=spec,
                                populations={name: {} for name in POPULATIONS}, exclusions={})


def test_v2_constructor_accepts_source_only_feasible_blocks():
    sessions, blocks = _block_schedule(date(2024, 1, 2), 12)
    spec = {"schema": SPEC_SCHEMA_V2, "train_blocks": blocks,
            "populations": {"train": {
                "window": {"start": f"{sessions[0]}T00:00:00Z",
                           "end": f"{sessions[-1]}T23:59:00Z"},
                "roots": [block["roots"][0] for block in blocks]}}}
    receipt = build_admission_receipt(study={"model_bucket": "0_7"}, study_spec=spec,
                                     populations={name: {} for name in POPULATIONS}, exclusions={})
    assert receipt["study"]["spec_digest"]
    assert receipt["study_spec"]["train_blocks"] == blocks


class ProbabilityModel:
    def predict_proba(self, features):
        p = features["premium"].to_numpy(dtype=float)
        return np.column_stack((1 - p, p))


def calibration_frame():
    return pd.DataFrame({"premium": [.1, .2, .7, .8],
                         "_label": [0, 1, 0, 1],
                         "session_date": ["2024-01-02"] * 4,
                         "source": ["tape_recon"] * 4})


def test_weighted_isotonic_and_diagnostics_ignore_print_multiplicity():
    frame = calibration_frame()
    weights = np.array([1., .25, .5, .75])
    original = trainer._weighted_calibration_diagnostics(
        ProbabilityModel(), frame, frame, ["premium"], weights, weights)
    burst = pd.concat([frame.iloc[:1]] * 1000 + [frame.iloc[1:]], ignore_index=True)
    burst_weights = np.r_[np.repeat(weights[0] / 1000, 1000), weights[1:]]
    repeated = trainer._weighted_calibration_diagnostics(
        ProbabilityModel(), burst, burst, ["premium"], burst_weights, burst_weights)
    for key in ("brier", "base_rate", "base_rate_brier", "auc", "auc_newest_era",
                "effective_n_cal_fit", "effective_n_cal_eval"):
        assert repeated[key] == pytest.approx(original[key])
    assert original["ece"] is None
    assert original["calibration_ready"] is False
    assert original["ece_status"] == "weighted_bin_method_unavailable"


@pytest.mark.parametrize("newest_rows", [0, 1])
def test_newest_auc_does_not_fall_back_to_pooled_auc(newest_rows):
    frame = calibration_frame()
    frame["session_date"] = ["2022-12-30"] * 4
    if newest_rows:
        frame.loc[3, "session_date"] = "2024-01-02"  # newest has only class one
    result = trainer._weighted_calibration_diagnostics(
        ProbabilityModel(), frame, frame, ["premium"], np.ones(4), np.ones(4))
    assert np.isfinite(result["auc"])
    assert result["auc_newest_era"] is None
    assert result["auc_newest_era_status"] == "unavailable"


def test_registered_era_registry_keeps_unfilled_cells_explicit():
    frame = pd.DataFrame({"session_date": ["2024-01-02", "2024-01-03"],
                          "fill_date": ["2024-01-02", "2024-01-03"], "root": ["AAPL", "AAPL"]})
    result = trainer._population_support(frame, np.ones(2), 20)
    eras = {cell["era"]: cell for cell in result["eras"]}
    assert eras["2017-19"]["booked"] is False
    assert eras["2020-22"]["status"] == "building_history_unfilled"
    assert eras["2020-22"]["effective_n"] == 0
    assert eras["2020-22"]["era_sparse"] is False
    assert eras["2023+"]["era_sparse"] is True


def test_fit_failure_preserves_attempted_and_completed_counts(monkeypatch):
    sessions, blocks, frame, embargo = _execution_frame("0_7", 12)
    paths = _paths(frame, blocks, sessions, embargo)
    attempts = []
    def fit(*args):
        attempts.append(True)
        if len(attempts) == 3:
            raise RuntimeError("synthetic third fit failure")
        return _ConstantModel(.5)
    monkeypatch.setattr(trainer, "_fit_model", fit)
    receipt = {}
    with pytest.raises(RuntimeError, match="third fit"):
        trainer._run_cpcv_selection(frame.assign(_label=frame["label"]), paths,
                                    [("off", ["premium"])], _grid(), np.ones(len(frame)),
                                    {}, 42, receipt=receipt)
    assert receipt["attempted_fits"] == 3
    assert receipt["executed_fits"] == receipt["evaluated_fits"] == 2
    assert receipt["executed_paths"] == 2
    assert receipt["planned_fits"] == 360
    assert "selected_params" not in receipt


def test_legacy_artifact_writer_cannot_arm_an_incomplete_gauntlet(tmp_path):
    cfg = trainer._load_config()
    cfg["models_dir"] = str(tmp_path / "models")
    cfg["scoring"]["enabled"] = True
    result = trainer._write_artifact(
        bucket="0_7", cfg=cfg, flow_dir=tmp_path, model=None, calibrator=None,
        deployable=True, deploy_reason="", serving_df=pd.DataFrame(),
        labeled=pd.DataFrame(), pop_stats={}, base_rate=.5, calibration_metrics={},
        kill_eval={}, n_trials=360, feature_cols=[], dry_run=True)
    assert result["deployable"] is False


@pytest.mark.parametrize(("key", "bucket", "bad"), [
    ("bucket_horizons", "0_7", ["5"]),
    ("bucket_horizons", "0_7", [5.0]),
    ("embargo_days", "0_7", 5.0),
    ("embargo_days", "0_7", "5"),
])
def test_frozen_clock_values_are_not_coerced(key, bucket, bad):
    cfg = trainer._load_config()
    cfg[key][bucket] = bad
    with pytest.raises(GeometryError, match=f"frozen_config_drift:{key}"):
        trainer._validate_frozen_fit_config(cfg)

def test_fs5_receipt_cannot_serialize_or_upload_an_unready_model(tmp_path, monkeypatch):
    cfg = trainer._load_config()
    cfg["models_dir"] = str(tmp_path / "models")
    def forbidden(*args, **kwargs):
        raise AssertionError("unready artifact side effect")
    monkeypatch.setattr(trainer, "_models_dir", forbidden)
    monkeypatch.setattr(trainer, "_try_r2_upload", forbidden)
    receipt = {"executed_fits": 360, "executed_paths": 15, "executed_variants": 1}
    result = trainer._write_artifact(
        bucket="0_7", cfg=cfg, flow_dir=tmp_path, model=object(), calibrator=object(),
        deployable=True, deploy_reason="", serving_df=pd.DataFrame(),
        labeled=pd.DataFrame(), pop_stats={}, base_rate=.5, calibration_metrics={},
        kill_eval={}, n_trials=360, feature_cols=[], selection_receipt=receipt)
    assert result["deployable"] is False
    assert result["selection_receipt"] == receipt
    assert result["executed_fits"] == 360
    assert not (tmp_path / "models").exists()
