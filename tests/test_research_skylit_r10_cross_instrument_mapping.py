from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from scripts import research_skylit_r10_cross_instrument_mapping as r10


BASE = datetime(2026, 9, 18, 13, 30, tzinfo=timezone.utc)


def _pairs(source_values, target_values, *, seconds=60):
    rows = []
    for i, (source, target) in enumerate(zip(source_values, target_values)):
        ts = BASE + timedelta(seconds=i * seconds)
        rows.append({
            "source_ts": ts.isoformat(),
            "target_ts": ts.isoformat(),
            "source_price": float(source),
            "target_price": float(target),
        })
    return pd.DataFrame(rows)


def test_constant_additive_basis_has_zero_holdout_error():
    source = [100 + i for i in range(20)]
    target = [x + 5 for x in source]
    got = r10.calibrate_mapping(
        _pairs(source, target),
        source_instrument="SPX",
        target_instrument="ES",
        target_contract="ESZ6",
        horizon_seconds=120,
        match_tolerance_seconds=0,
    )
    assert got["status"] == "MAPPING_CALIBRATION_COMPLETE"
    assert got["outcome_labels_opened"] is False
    assert got["target_native_positioning_claim"] is False
    assert got["methods"]["additive_basis"]["test_mae_target_points"] == pytest.approx(0)
    assert got["methods"]["additive_basis"]["train_abs_error_q90_target_points"] == pytest.approx(0)
    assert got["methods"]["multiplicative_ratio"]["test_mae_target_points"] > 0


def test_constant_ratio_has_zero_holdout_error():
    source = [100 + i * 2 for i in range(20)]
    target = [x * 1.05 for x in source]
    got = r10.calibrate_mapping(
        _pairs(source, target),
        source_instrument="SPY",
        target_instrument="ES",
        horizon_seconds=120,
        match_tolerance_seconds=0,
    )
    assert got["methods"]["multiplicative_ratio"]["test_mae_target_points"] == pytest.approx(0)
    assert got["methods"]["multiplicative_ratio"]["train_abs_error_q90_target_points"] == pytest.approx(0)
    assert got["methods"]["additive_basis"]["test_mae_target_points"] > 0


def test_temporal_split_does_not_leak_holdout_basis_shock_into_train_interval():
    source = [100 + i for i in range(30)]
    target = []
    for i, x in enumerate(source):
        target.append(x + (5 if i < 18 else 25))
    got = r10.calibrate_mapping(
        _pairs(source, target),
        source_instrument="SPX",
        target_instrument="ES",
        horizon_seconds=60,
        match_tolerance_seconds=0,
        train_fraction=0.60,
    )
    additive = got["methods"]["additive_basis"]
    assert additive["train_abs_error_q90_target_points"] == pytest.approx(0)
    assert additive["test_mae_target_points"] > 0
    assert additive["test_q90_interval_coverage"] < 1
    assert got["input_contract"]["purge_cross_boundary_pairs"] is True


def test_timestamp_skew_beyond_gate_refuses():
    frame = _pairs(range(100, 112), range(105, 117))
    frame.loc[3, "target_ts"] = (BASE + timedelta(seconds=3 * 60 + 10)).isoformat()
    with pytest.raises(r10.R10Refusal, match="timestamp skew exceeds gate"):
        r10.calibrate_mapping(
            frame,
            source_instrument="SPX",
            target_instrument="ES",
            max_skew_seconds=2,
            horizon_seconds=60,
        )


def test_mapping_example_is_explicitly_not_native_target_positioning():
    source = [100 + i for i in range(20)]
    target = [x + 5 for x in source]
    got = r10.calibrate_mapping(
        _pairs(source, target),
        source_instrument="SPX",
        target_instrument="ES",
        target_contract="ESZ6",
        horizon_seconds=60,
        match_tolerance_seconds=0,
        source_level=125,
    )
    assert got["mapping_example"]["additive_basis"]["mapped_target_level"] == pytest.approx(130)
    assert got["target_native_positioning_claim"] is False
    assert "not on native target options positioning" in got["mapping_example"]["warning"]


def test_duplicate_effective_timestamp_refuses():
    frame = _pairs(range(100, 112), range(105, 117))
    frame.loc[2, "source_ts"] = frame.loc[1, "source_ts"]
    frame.loc[2, "target_ts"] = frame.loc[1, "target_ts"]
    with pytest.raises(r10.R10Refusal, match="duplicate synchronized"):
        r10.calibrate_mapping(
            frame,
            source_instrument="SPX",
            target_instrument="ES",
            horizon_seconds=60,
        )
