"""Synthetic numerical witnesses, never empirical pilot acceptance."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from scripts.options_pilot_identity_offset import (
    OffsetRefusal, fit_identity_offset, predict_identity_offset,
)

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def inputs():
    return dict(pilot="P2", covariates=np.eye(8).tolist(),
                targets=list(range(8)), baselines=[0] * 8,
                weights=list(range(1, 9)), target_matured_at=[T - timedelta(days=1)] * 8,
                fit_cutoff=T)


def forecast(fit, **changes):
    args = dict(covariates=[1] * 8, baseline=0, decision_at=T,
                feature_available_at=T)
    args.update(changes)
    return predict_identity_offset(fit, **args)


def test_closed_form_diagonal_ridge_and_weight_scale_invariance():
    args = inputs()
    fit = fit_identity_offset(**args)
    w = np.arange(1, 9) / 36
    expected = w * np.arange(8) / (w + .01)
    np.testing.assert_allclose(fit.coefficients, expected, rtol=1e-13, atol=1e-15)
    assert forecast(fit) == pytest.approx(expected.sum())
    args["weights"] = [x * 100 for x in args["weights"]]
    np.testing.assert_allclose(fit_identity_offset(**args).coefficients, expected)
    assert fit.training_rows == 8 and fit.constant_columns == ()
    with pytest.raises(FrozenInstanceError):
        fit.pilot = "P3"


def test_ridge_admits_collinearity_and_records_constant_columns():
    args = inputs()
    args.update(covariates=[[1] * 8] * 8, weights=[1] * 8, targets=[2] * 8)
    fit = fit_identity_offset(**args)
    np.testing.assert_allclose(fit.coefficients, [2 / 8.01] * 8, rtol=1e-12)
    assert fit.constant_columns == tuple(range(8))


def test_zero_residual_keeps_baseline_exact_and_has_no_extra_intercept():
    args = inputs()
    args["baselines"] = args["targets"]
    fit = fit_identity_offset(**args)
    assert fit.coefficients == (0.,) * 8
    assert forecast(fit, baseline=3.5) == 3.5
    assert fit.relative_residual == 0


@pytest.mark.parametrize("pilot", ["P1", "P2", "P4", "P6"])
def test_only_p1_projects_negative_forecast(pilot):
    args = inputs()
    args.update(pilot=pilot, targets=[0] * 8, baselines=[1] * 8)
    fit = fit_identity_offset(**args)
    answer = forecast(fit)
    assert answer == 0 if pilot == "P1" else answer < 0


@pytest.mark.parametrize("field,value,code", [
    ("pilot", "P3", "PILOT_UNSUPPORTED"),
    ("weights", [0] * 8, "WEIGHT_DOMAIN"),
    ("weights", [-1] * 8, "WEIGHT_DOMAIN"),
    ("weights", [1e308] * 8, "NUMERIC_FAILURE"),
    ("targets", [float("nan")] * 8, "NUMERIC_DOMAIN"),
    ("baselines", [float("inf")] * 8, "NUMERIC_DOMAIN"),
    ("targets", [True] * 8, "NUMERIC_DOMAIN"),
    ("targets", ["1"] * 8, "NUMERIC_DOMAIN"),
    ("targets", [1], "SHAPE_MISMATCH"),
    ("covariates", [[1] * 7] * 8, "SHAPE_MISMATCH"),
    ("covariates", [], "SHAPE_MISMATCH"),
    ("target_matured_at", [T] * 8, "TARGET_NOT_MATURE"),
    ("target_matured_at", [T.replace(tzinfo=None)] * 8, "CLOCK_UNQUALIFIED"),
    ("covariates", [[1e308] * 8] * 8, "NUMERIC_FAILURE"),
])
def test_invalid_inputs_refuse_without_dropping_rows(field, value, code):
    args = inputs()
    args[field] = value
    with pytest.raises(OffsetRefusal) as caught:
        fit_identity_offset(**args)
    assert caught.value.code == code


def test_clocks_and_frozen_prediction_domain():
    fit = fit_identity_offset(**inputs())
    for changes, code in [
        ({"decision_at": T - timedelta(seconds=1)}, "FIT_NOT_AVAILABLE"),
        ({"feature_available_at": T + timedelta(seconds=1)}, "FEATURE_NOT_AVAILABLE"),
        ({"decision_at": T.replace(tzinfo=None)}, "CLOCK_UNQUALIFIED"),
        ({"baseline": True}, "NUMERIC_DOMAIN"),
        ({"covariates": [1e308] * 8}, "NUMERIC_FAILURE"),
    ]:
        with pytest.raises(OffsetRefusal) as caught:
            forecast(fit, **changes)
        assert caught.value.code == code
    assert forecast(fit) == forecast(fit)
    with pytest.raises(OffsetRefusal):
        forecast(replace(fit, coefficients=(float("nan"),) * 8))


def test_solver_failure_and_bad_residual_are_not_fallbacks(monkeypatch):
    def fail(_):
        raise np.linalg.LinAlgError("witness")
    with monkeypatch.context() as patch:
        patch.setattr(np.linalg, "cholesky", fail)
        with pytest.raises(OffsetRefusal, match="NUMERIC_FAILURE"):
            fit_identity_offset(**inputs())
    monkeypatch.setattr(np.linalg, "solve", lambda a, b: np.ones(8) * 42)
    with pytest.raises(OffsetRefusal, match="SOLVE_RESIDUAL"):
        fit_identity_offset(**inputs())


def test_p1_range_domain_is_not_applied_to_signed_return_targets():
    args = inputs()
    args.update(pilot="P1", targets=[-1] * 8)
    with pytest.raises(OffsetRefusal, match="RANGE_DOMAIN"):
        fit_identity_offset(**args)
    args["pilot"] = "P2"
    assert forecast(fit_identity_offset(**args)) < 0


def test_dst_fold_is_ordered_by_instant_not_wall_clock():
    zone = ZoneInfo("America/Los_Angeles")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    second = datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1)
    args = inputs()
    args.update(fit_cutoff=first, target_matured_at=[second] * 8)
    with pytest.raises(OffsetRefusal, match="TARGET_NOT_MATURE"):
        fit_identity_offset(**args)
    args["target_matured_at"] = [first - timedelta(days=1)] * 8
    fit = fit_identity_offset(**args)
    assert forecast(fit, decision_at=second, feature_available_at=first) > 0
