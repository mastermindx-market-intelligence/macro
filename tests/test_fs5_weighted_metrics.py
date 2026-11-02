"""Synthetic checks for FS5 weighted binary metrics. Arrays only."""

from math import fsum

import numpy as np
import pytest

from lib.flow_score import (
    reliability_table,
    strict_weighted_binary_inputs,
    weighted_binary_metrics,
)


def test_weighted_metrics_match_hand_computed_values():
    pred = np.array([0.25, 0.75, 0.5, 1.0])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    weights = np.array([0.5, 0.25, 0.125, 0.125])

    metrics = weighted_binary_metrics(pred, y, weights)

    assert set(metrics) == {"brier", "base_rate", "base_rate_brier", "auc"}
    assert all(type(value) is float for value in metrics.values())
    assert metrics["brier"] == 0.203125
    assert metrics["base_rate"] == 0.25
    assert metrics["base_rate_brier"] == 0.1875
    assert metrics["auc"] == 5 / 6


def test_duplicating_one_unit_into_1000_equal_weight_prints_preserves_metrics():
    """One synthetic root/session print, split into 1000 equal weights.

    The second row is a different unit and keeps the other label class so
    AUC stays defined. Total weight of the duplicated unit is unchanged.
    """
    pred = np.array([0.25, 0.75])
    y = np.array([0.0, 1.0])
    weights = np.array([0.5, 0.5])
    base = weighted_binary_metrics(pred, y, weights)

    duplicated = weighted_binary_metrics(
        np.concatenate([np.full(1000, 0.25), np.array([0.75])]),
        np.concatenate([np.zeros(1000), np.array([1.0])]),
        np.concatenate([np.full(1000, 0.5 / 1000.0), np.array([0.5])]),
    )

    assert base["brier"] == 0.0625
    assert base["base_rate"] == 0.5
    assert base["base_rate_brier"] == 0.25
    assert base["auc"] == 1.0
    # 0.5/1000 is not a dyadic, so the split sum differs by a few ulps.
    assert duplicated["brier"] == pytest.approx(base["brier"], abs=1e-12)
    assert duplicated["base_rate"] == pytest.approx(base["base_rate"], abs=1e-12)
    assert duplicated["base_rate_brier"] == pytest.approx(
        base["base_rate_brier"], abs=1e-12
    )
    assert duplicated["auc"] == pytest.approx(base["auc"], abs=1e-12)


def test_weighted_isotonic_predict_is_invariant_for_sklearn_at_least_1_4():
    """Integration contract only: sklearn >= 1.4 accepts sample_weight."""
    import sklearn
    from sklearn.isotonic import IsotonicRegression

    version = []
    for piece in sklearn.__version__.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if not digits:
            continue
        version.append(int(digits))
        if len(version) == 2:
            break
    assert tuple(version) >= (1, 4)

    x = np.array([0.1, 0.4, 0.7, 0.9])
    y = np.array([0.0, 0.2, 0.8, 1.0])
    weights = np.array([0.4, 0.2, 0.2, 0.2])
    fitted = IsotonicRegression(out_of_bounds="clip").fit(x, y, sample_weight=weights)
    original = fitted.predict(x)

    exploded = IsotonicRegression(out_of_bounds="clip").fit(
        np.concatenate([np.full(1000, x[0]), x[1:]]),
        np.concatenate([np.full(1000, y[0]), y[1:]]),
        sample_weight=np.concatenate(
            [np.full(1000, weights[0] / 1000.0), weights[1:]]
        ),
    )
    np.testing.assert_allclose(exploded.predict(x), original, rtol=0.0, atol=1e-12)
    repeated = exploded.predict(np.full(1000, x[0]))
    assert np.all(repeated == repeated[0])


@pytest.mark.parametrize(
    ("pred", "y", "weights"),
    [
        (np.ones((2, 2)), np.array([0.0, 1.0]), np.array([0.5, 0.5])),
        (np.array([0.2]), np.array([0.0, 1.0]), np.array([0.5, 0.5])),
        (np.zeros((2, 1)), np.array([[0.0], [1.0]]), np.ones((2, 1))),
        (np.array([]), np.array([]), np.array([])),
        (0.2, 0.0, 1.0),
        (np.array([0.2, np.nan]), np.array([0.0, 1.0]), np.array([0.5, 0.5])),
        (np.array([0.2, np.inf]), np.array([0.0, 1.0]), np.array([0.5, 0.5])),
        (np.array([-0.01, 0.8]), np.array([0.0, 1.0]), np.array([0.5, 0.5])),
        (np.array([1.01, 0.2]), np.array([0.0, 1.0]), np.array([0.5, 0.5])),
        (np.array([0.2, 0.8]), np.array([0.0, np.nan]), np.array([0.5, 0.5])),
        (np.array([0.2, 0.8]), np.array([0.0, 0.5]), np.array([0.5, 0.5])),
        (np.array([0.2, 0.8]), np.array([0.0, 2.0]), np.array([0.5, 0.5])),
        (np.array([0.2, 0.8]), np.array([-1.0, 1.0]), np.array([0.5, 0.5])),
        (np.array([0.2, 0.8]), np.array([0.0, 1.0]), np.array([0.0, 1.0])),
        (np.array([0.2, 0.8]), np.array([0.0, 1.0]), np.array([-0.2, 0.5])),
        (np.array([0.2, 0.8]), np.array([0.0, 1.0]), np.array([0.5, np.nan])),
        (np.array([0.2, 0.8]), np.array([0.0, 1.0]), np.array([0.5, np.inf])),
    ],
)
def test_invalid_weighted_inputs_raise_and_are_not_filtered(pred, y, weights):
    with pytest.raises(ValueError):
        strict_weighted_binary_inputs(pred, y, weights)
    with pytest.raises(ValueError):
        weighted_binary_metrics(pred, y, weights)
    with pytest.raises(ValueError):
        reliability_table(pred, y, weights=weights)


def test_one_class_is_accepted_by_the_helper_and_rejected_by_metrics():
    pred = np.array([0.2, 0.8])
    y = np.array([1.0, 1.0])
    weights = np.array([0.25, 0.75])

    checked_pred, checked_y, checked_w = strict_weighted_binary_inputs(pred, y, weights)
    assert checked_pred.shape == checked_y.shape == checked_w.shape == (2,)

    with pytest.raises(ValueError):
        weighted_binary_metrics(pred, y, weights)

    table = reliability_table(pred, y, weights=weights, n_bins=2)
    assert table
    assert fsum(row["n_eff"] for row in table) == fsum(weights.tolist())
    assert all(row["emp_rate"] == 1.0 for row in table)


def test_reliability_reports_fsum_n_eff_for_explicit_weights():
    pred = np.array([0.1, 0.2, 0.8, 0.9])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    weights = np.array([0.25, 0.25, 0.125, 0.375])

    table = reliability_table(pred, y, weights=weights, n_bins=2)

    by_mean = sorted(table, key=lambda row: row["pred_mean"])
    assert len(by_mean) == 2
    assert by_mean[0]["n_eff"] == fsum([0.25, 0.25]) == 0.5
    assert by_mean[1]["n_eff"] == fsum([0.125, 0.375]) == 0.5
    assert fsum(row["n_eff"] for row in table) == fsum(weights.tolist()) == 1.0
    assert by_mean[0]["emp_rate"] == 0.0
    assert by_mean[1]["emp_rate"] == 1.0


def test_unweighted_reliability_keeps_legacy_drop_and_empty_result():
    assert reliability_table([], []) == []
    table = reliability_table(
        np.array([0.1, np.nan, 0.9]),
        np.array([0.0, 1.0, 1.0]),
        n_bins=2,
    )
    assert sum(row["n_eff"] for row in table) == 2.0


def test_boundary_probabilities_and_unit_weight_are_kept():
    pred, y, weights = strict_weighted_binary_inputs(
        np.array([0.0, 1.0]),
        np.array([0, 1]),
        np.array([1.0, 1.0]),
    )
    assert pred.tolist() == [0.0, 1.0]
    assert y.tolist() == [0.0, 1.0]
    assert weights.tolist() == [1.0, 1.0]
    assert len(pred) == 2


def test_generic_weighted_api_preserves_positive_non_native_weights():
    pred, y, weights = strict_weighted_binary_inputs([.2, .8], [0, 1], [2., 3.])
    assert weighted_binary_metrics(pred, y, weights)["base_rate"] == pytest.approx(.6)
    assert sum(row["n_eff"] for row in reliability_table(pred, y, weights=weights, n_bins=2)) == 5.
