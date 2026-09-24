"""Contract tests for the preregistered China Risk Radar revalidation harness."""
from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


try:
    SUBJECT = importlib.import_module("scripts.research.cn_risk_radar_revalidation")
except ModuleNotFoundError:
    SUBJECT = None


def _fn(name: str):
    assert SUBJECT is not None, "revalidation module does not exist"
    fn = getattr(SUBJECT, name, None)
    assert callable(fn), f"missing callable: {name}"
    return fn


def test_forward_max_drawdown_uses_future_sessions_only_and_excludes_immature_rows():
    idx = pd.bdate_range("2024-01-02", periods=7)
    close = pd.Series([90.0, 100.0, 94.0, 96.0, 92.0, 101.0, 99.0], index=idx)

    result = _fn("forward_max_drawdown")(close, horizon=3)

    # The low current close at t0 must not enter its own future window.
    assert result.loc[idx[0]] == pytest.approx(0.0)
    assert result.loc[idx[1]] == pytest.approx(-0.08)
    assert result.loc[idx[2]] == pytest.approx((92.0 / 94.0) - 1.0)
    assert result.iloc[-3:].isna().all()


def test_binary_outcome_uses_inclusive_threshold_and_preserves_immaturity():
    idx = pd.bdate_range("2024-01-02", periods=5)
    drawdown = pd.Series([-0.0499, -0.05, -0.10, np.nan, 0.0], index=idx)

    result = _fn("binary_outcome")(drawdown, threshold=0.05)

    assert result.iloc[0] == 0
    assert result.iloc[1] == 1
    assert result.iloc[2] == 1
    assert pd.isna(result.iloc[3])
    assert result.iloc[4] == 0


def test_reconstruct_states_applies_exact_bands_and_context_cap():
    idx = pd.bdate_range("2024-01-02", periods=6)
    composite = pd.Series([0.57, 0.5801, 0.7201, 0.84, 0.92, 0.92], index=idx)
    gate = pd.Series([True, True, True, False, False, True], index=idx)

    result = _fn("reconstruct_states")(
        composite,
        gate,
        bands={"watch": 58.0, "caution": 72.0, "elevated": 83.0, "risk_off": 91.0},
    )

    assert result["state_ungated"].tolist() == [
        "calm", "watch", "caution", "elevated", "risk-off", "risk-off"
    ]
    assert result["state"].tolist() == [
        "calm", "watch", "caution", "caution", "caution", "risk-off"
    ]
    assert result["score"].tolist() == pytest.approx([57.0, 58.01, 72.01, 84.0, 92.0, 92.0])


def test_episode_ids_use_benchmark_session_distance_not_calendar_days():
    idx = pd.bdate_range("2024-01-02", periods=60)
    qualifying = pd.Series(False, index=idx)
    qualifying.iloc[[0, 1, 3, 46, 47]] = True

    ids = _fn("episode_ids")(qualifying, max_gap_sessions=42)

    assert ids.dropna().astype(int).tolist() == [0, 0, 0, 1, 1]
    assert ids.loc[~qualifying].isna().all()


def test_episode_summary_reports_rows_episodes_hits_and_effective_ceiling():
    idx = pd.bdate_range("2024-01-02", periods=100)
    condition = pd.Series(False, index=idx)
    condition.iloc[[0, 1, 2, 50, 51, 99]] = True
    outcome = pd.Series(0.0, index=idx)
    outcome.iloc[[1, 50]] = 1.0

    result = _fn("episode_summary") (
        condition=condition,
        outcome=outcome,
        horizon=21,
        episode_gap=42,
    )

    assert result == {
        "rows": 6,
        "episodes": 3,
        "hit_episodes": 2,
        "nonhit_episodes": 1,
        "nonoverlap_ceiling": 4,
        "effective_n_ceiling": 3,
    }


def test_core_discrimination_and_brier_metrics_have_known_values():
    idx = pd.bdate_range("2024-01-02", periods=4)
    outcome = pd.Series([0.0, 1.0, 0.0, 1.0], index=idx)
    probability = pd.Series([0.1, 0.9, 0.2, 0.8], index=idx)
    score = probability.copy()

    assert _fn("brier_score")(probability, outcome) == pytest.approx(0.025)
    assert _fn("brier_skill")(probability, outcome, baseline_probability=0.5) == pytest.approx(0.9)
    assert _fn("roc_auc")(score, outcome) == pytest.approx(1.0)
    assert _fn("average_precision")(score, outcome) == pytest.approx(1.0)


def test_lift_summary_uses_conditional_rate_over_full_base_rate():
    idx = pd.bdate_range("2024-01-02", periods=4)
    outcome = pd.Series([0.0, 1.0, 1.0, 1.0], index=idx)
    condition = pd.Series([False, True, False, True], index=idx)

    result = _fn("lift_summary")(condition, outcome)

    assert result["rows"] == 2
    assert result["hits"] == 2
    assert result["conditional_rate"] == pytest.approx(1.0)
    assert result["base_rate"] == pytest.approx(0.75)
    assert result["lift"] == pytest.approx(4.0 / 3.0)


def test_circular_moving_block_indices_are_seeded_and_locally_contiguous():
    sampler = _fn("circular_moving_block_indices")
    first = sampler(n=17, block_length=5, seed=7)
    second = sampler(n=17, block_length=5, seed=7)

    assert np.array_equal(first, second)
    assert len(first) == 17
    assert np.all((first[:4] + 1) % 17 == first[1:5])
    assert np.all((first[5:9] + 1) % 17 == first[6:10])


def test_moving_block_bootstrap_constant_statistic_has_degenerate_interval():
    frame = pd.DataFrame({"x": np.arange(30, dtype=float)})
    result = _fn("moving_block_bootstrap")(
        frame,
        statistic=lambda sample: 3.25,
        block_length=7,
        reps=100,
        seed=11,
    )

    assert result["estimate"] == pytest.approx(3.25)
    assert result["ci_low"] == pytest.approx(3.25)
    assert result["ci_high"] == pytest.approx(3.25)
    assert result["valid_reps"] == 100
    assert result["invalid_reps"] == 0


def test_block_permutation_is_reproducible_and_detects_strong_alignment():
    n = 240
    idx = pd.bdate_range("2020-01-02", periods=n)
    condition = pd.Series(False, index=idx)
    outcome = pd.Series(0.0, index=idx)
    for start in (20, 80, 140, 200):
        condition.iloc[start : start + 10] = True
        outcome.iloc[start : start + 10] = 1.0

    fn = _fn("circular_shift_permutation")
    first = fn(condition, outcome, reps=399, min_shift=42, seed=19)
    second = fn(condition, outcome, reps=399, min_shift=42, seed=19)

    assert first == second
    assert first["observed"] == pytest.approx(6.0)
    assert first["p_value"] <= 0.05
    assert first["valid_reps"] == 399


def test_state_calibration_table_preserves_fixed_state_order_and_probabilities():
    states = []
    probabilities = []
    outcomes = []
    for state, probability, hits in (
        ("calm", 0.2, 4),
        ("watch", 0.4, 8),
        ("caution", 0.6, 12),
        ("elevated", 0.7, 14),
        ("risk-off", 0.8, 16),
    ):
        states.extend([state] * 20)
        probabilities.extend([probability] * 20)
        outcomes.extend([1.0] * hits + [0.0] * (20 - hits))
    idx = pd.bdate_range("2020-01-02", periods=len(states))

    table = _fn("state_calibration_table")(
        pd.Series(states, index=idx),
        pd.Series(probabilities, index=idx),
        pd.Series(outcomes, index=idx),
        horizon=21,
        episode_gap=0,
    )

    assert [row["state"] for row in table] == [
        "calm", "watch", "caution", "elevated", "risk-off"
    ]
    assert [row["forecast"] for row in table] == pytest.approx([0.2, 0.4, 0.6, 0.7, 0.8])
    assert [row["observed"] for row in table] == pytest.approx([0.2, 0.4, 0.6, 0.7, 0.8])
    assert all(row["rows"] == 20 for row in table)


def test_detect_probability_inversions_requires_material_negative_step():
    table = [
        {"state": "calm", "observed": 0.20},
        {"state": "watch", "observed": 0.28},
        {"state": "caution", "observed": 0.34},
        {"state": "elevated", "observed": 0.50},
        {"state": "risk-off", "observed": 0.39},
    ]

    result = _fn("detect_probability_inversions")(table, material_delta=0.05)

    assert result == [
        {
            "lower_state": "elevated",
            "higher_state": "risk-off",
            "difference": pytest.approx(-0.11),
            "material": True,
        }
    ]


def test_calibration_intercept_slope_recovers_exact_grouped_calibration():
    probabilities = []
    outcomes = []
    for probability, hits in ((0.2, 20), (0.5, 50), (0.8, 80)):
        probabilities.extend([probability] * 100)
        outcomes.extend([1.0] * hits + [0.0] * (100 - hits))
    idx = pd.bdate_range("2020-01-02", periods=300)

    result = _fn("calibration_intercept_slope")(
        pd.Series(probabilities, index=idx),
        pd.Series(outcomes, index=idx),
    )

    assert result["qualified"] is True
    assert result["intercept"] == pytest.approx(0.0, abs=1e-5)
    assert result["slope"] == pytest.approx(1.0, abs=1e-5)


def test_crisis_exclusion_mask_embargoes_signals_whose_forward_window_intersects_crisis():
    idx = pd.bdate_range("2024-01-02", periods=12)
    mask = _fn("crisis_exclusion_mask")(
        idx,
        crisis_start=pd.Timestamp("2024-01-09"),
        crisis_end=pd.Timestamp("2024-01-11"),
        horizon=3,
    )

    # Jan 4 looks forward to Jan 5/8/9, so it must be excluded; Jan 3 does not intersect.
    assert bool(mask.loc[pd.Timestamp("2024-01-03")]) is True
    assert bool(mask.loc[pd.Timestamp("2024-01-04")]) is False
    assert bool(mask.loc[pd.Timestamp("2024-01-09")]) is False
    assert bool(mask.loc[pd.Timestamp("2024-01-12")]) is True


def test_chronological_split_half_is_deterministic_and_exhaustive():
    idx = pd.bdate_range("2024-01-02", periods=9)
    first, second = _fn("chronological_split_half")(idx)

    assert list(first) == list(idx[:4])
    assert list(second) == list(idx[4:])
    assert set(first).isdisjoint(set(second))
