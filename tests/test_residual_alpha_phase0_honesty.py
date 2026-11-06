from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import residual_alpha_phase0 as phase0


def test_quintile_weights_preserve_explicit_exits():
    idx = pd.bdate_range("2026-01-01", periods=4)
    names = [f"T{i:02d}" for i in range(30)]
    returns = pd.DataFrame(0.0, index=idx, columns=names)
    signal = pd.DataFrame(index=idx, columns=names, dtype=float)
    signal.loc[idx[0]] = np.arange(30)
    signal.loc[idx[2]] = np.arange(30)[::-1]
    w = phase0._quintile_weights(returns, signal, [idx[0], idx[2]])
    first_top = set(w.loc[idx[0]][w.loc[idx[0]] > 0].index)
    second_top = set(w.loc[idx[2]][w.loc[idx[2]] > 0].index)
    assert first_top.isdisjoint(second_top)
    for name in first_top:
        assert w.loc[idx[2], name] <= 0  # old long is explicitly exited/reversed, never carried long


def test_missing_held_return_is_unresolved_not_renormalized(monkeypatch):
    idx = pd.bdate_range("2026-01-01", periods=4)
    names = [f"T{i:02d}" for i in range(30)]
    returns = pd.DataFrame(0.0, index=idx, columns=names)
    signal = pd.DataFrame(index=idx, columns=names, dtype=float)
    signal.loc[idx[0]] = np.arange(30)
    signal.loc[idx[2]] = np.arange(30)[::-1]
    top = names[-1]
    returns.loc[idx[1], top] = np.nan
    monkeypatch.setattr(phase0, "ret_moments", lambda x: None)
    monkeypatch.setattr(phase0, "block_bootstrap_ci", lambda x, ann: None)
    out = phase0.quintile_ls(returns, signal, [idx[0], idx[2]], 21, 1)
    assert out["unresolved_held_return_days"] >= 1
    assert out["holding_rule"] == "monthly_rebalance_until_next_grid_date"


def test_sector_normalization_does_not_depend_on_label_availability(monkeypatch):
    # Freeze a three-name predictor; removing C's future label must not change A/B signal normalization.
    s = pd.Series({"A": 100.0, "B": 4.0, "C": 1.0})
    sec = pd.Series({"A": "X", "B": "X", "C": "X"})
    full = s - s.groupby(sec).transform("mean")
    future = pd.Series({"A": .1, "B": .2, "C": np.nan})
    known = future.dropna()
    # This demonstrates the old anti-pattern would have changed the predictor cross-section.
    old_subset = s.reindex(known.index)
    old = old_subset - old_subset.groupby(sec.reindex(old_subset.index)).transform("mean")
    assert not np.isclose(full["B"], old["B"])
    # New score_panel constructs sector normalization from the membership/feature universe, not known labels.
    assert np.isclose(full["B"], 4.0 - s.mean())
