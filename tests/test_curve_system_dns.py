from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.rates_direction import curve_system_dns as c


def _synthetic_panel(n: int = 1900) -> pd.DataFrame:
    idx = pd.bdate_range("2010-01-04", periods=n)
    x = np.arange(n, dtype=float)
    beta = np.column_stack(
        [
            4.0 + 0.00015 * x + 0.08 * np.sin(x / 70.0),
            -1.2 + 0.18 * np.sin(x / 45.0),
            0.5 + 0.12 * np.cos(x / 33.0),
        ]
    )
    yields = beta @ c.DESIGN.T
    return pd.DataFrame(yields, index=idx, columns=c.TENORS)


def test_fixed_nelson_siegel_design_is_three_factor_and_finite():
    assert c.DESIGN.shape == (6, 3)
    assert np.isfinite(c.DESIGN).all()
    assert np.linalg.matrix_rank(c.DESIGN) == 3
    assert np.allclose(c.DESIGN[:, 0], 1.0)
    assert np.all(c.DESIGN[:, 1] > 0)


def test_factor_extraction_reconstructs_exact_synthetic_curve():
    panel = _synthetic_panel(100)
    factors = c.extract_factors(panel)
    reconstructed = factors.to_numpy() @ c.DESIGN.T
    assert np.max(np.abs(reconstructed - panel.to_numpy())) < 1e-10
    assert np.max(
        np.abs(c.reconstruct_10y(factors.to_numpy()) - panel["10"].to_numpy())
    ) < 1e-10


def test_target_qualification_rejects_large_calendar_gap():
    panel = _synthetic_panel(30)
    shifted = panel.copy()
    idx = shifted.index.to_list()
    for i in range(12, len(idx)):
        idx[i] = idx[i] + pd.Timedelta(days=10)
    shifted.index = pd.DatetimeIndex(idx)
    ok = c._target_ok(shifted, 5, 4)
    assert ok[:7].all()
    assert not ok[7]


def test_walk_forward_is_purged_and_probabilities_are_normalized():
    panel = _synthetic_panel()
    result = c.walk_forward(panel, 20)
    assert result["rows"]
    assert result["factor_reconstruction_rmse_bp"] < 1e-7

    by_origin = {}
    for row in result["rows"]:
        by_origin.setdefault(row["origin"], []).append(row)
        assert pd.Timestamp(row["fit_target_end"]) < pd.Timestamp(row["calibration_start"])
        assert pd.Timestamp(row["calibration_target_end"]) < pd.Timestamp(row["origin"])
        assert row["authority"] is False
        assert row["historical_availability_qualified"] is False
        assert row["fit_n"] >= c.SPEC["fit_min"]
        assert row["calibration_n"] >= c.SPEC["calibration_min"]
        probs = [row["p_down"], row["p_flat"], row["p_up"]]
        assert all(0.0 < value < 1.0 for value in probs)
        assert sum(probs) == pytest.approx(1.0)

    for rows in by_origin.values():
        assert {r["model"] for r in rows} == set(c.MODELS)
        no_change = next(r for r in rows if r["model"] == "no_change")
        assert no_change["forecast_bp"] == 0.0


def test_future_mutation_cannot_change_earlier_forecasts():
    panel = _synthetic_panel()
    first = c.walk_forward(panel, 20)
    mutated = panel.copy()
    cutoff = 1750
    mutated.iloc[cutoff:, :] += np.linspace(0.2, 0.8, len(mutated) - cutoff)[:, None]
    second = c.walk_forward(mutated, 20)

    def prefix(rows):
        return {
            (r["origin"], r["model"]): (
                r["forecast_bp"],
                r["p_down"],
                r["p_flat"],
                r["p_up"],
                r["fit_start"],
                r["fit_target_end"],
                r["calibration_start"],
                r["calibration_target_end"],
            )
            for r in rows
            if r["origin_position"] < cutoff - 20
        }

    a = prefix(first["rows"])
    b = prefix(second["rows"])
    assert a.keys() == b.keys()
    for key in a:
        left, right = a[key], b[key]
        assert left[4:] == right[4:]
        assert np.allclose(left[:4], right[:4], rtol=0, atol=1e-12)


def test_direct_models_share_common_forecast_origins():
    panel = _synthetic_panel()
    result = c.walk_forward(panel, 5)
    origins = {
        model: [r["origin"] for r in result["rows"] if r["model"] == model]
        for model in c.MODELS
    }
    assert origins["no_change"]
    assert all(origins[model] == origins["no_change"] for model in c.MODELS)
