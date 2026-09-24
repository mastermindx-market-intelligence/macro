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
