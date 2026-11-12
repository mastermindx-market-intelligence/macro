"""Leak and definition tests for engine.risk_radar_eval (synthetic prices; no store access)."""
import numpy as np
import pandas as pd
import pytest

from engine.risk_radar_eval import labels as L
from engine.risk_radar_eval import scorecard as S


def _px(values, start="2019-01-02"):
    idx = pd.bdate_range(start, periods=len(values))
    return pd.Series(np.asarray(values, dtype=float), index=idx)


def _dip(n_pre=30, depth=0.12, n_down=10, n_up=20, n_post=30):
    up = np.linspace(100, 110, n_pre)
    down = np.linspace(110, 110 * (1 - depth), n_down + 1)[1:]
    rec = np.linspace(110 * (1 - depth), 111, n_up + 1)[1:]
    post = np.linspace(111, 115, n_post)
    return _px(np.concatenate([up, down, rec, post]))


def test_outcomes_through_is_required():
    with pytest.raises(L.LabelLeakError):
        L.forward_loss_labels(_dip(), 5, outcomes_through=None)
    with pytest.raises(L.LabelLeakError):
        L.drawdown_episodes(_dip(), 0.05, outcomes_through=None)


def test_forward_labels_never_use_closes_after_cutoff():
    px = _dip()
    cut = px.index[35]
    lab = L.forward_loss_labels(px, 10, 0.05, outcomes_through=cut)
    assert lab["end"].max() <= cut
    # perturbing closes after the cutoff cannot change any label
    px2 = px.copy()
    px2.loc[px2.index > cut] = 1.0
    lab2 = L.forward_loss_labels(px2, 10, 0.05, outcomes_through=cut)
    pd.testing.assert_frame_equal(lab, lab2)


def test_episode_definition_onset_breach_recovery():
    px = _dip(depth=0.12)
    (ep,) = L.drawdown_episodes(px, 0.10, outcomes_through=px.index[-1])
    assert ep.peak == px.index[29]
    assert ep.onset == px.index[30]          # session after the peak
    assert px[ep.breach] <= px[ep.peak] * 0.90
    assert ep.recovery is not None and px[ep.recovery] >= px[ep.peak]
    assert ep.max_loss == pytest.approx(-0.12, abs=1e-3)


def test_episode_after_cutoff_does_not_exist():
    px = _dip(depth=0.12)
    eps = L.drawdown_episodes(px, 0.10, outcomes_through=px.index[32])
    assert eps == []


def test_merge_within_gap():
    a = np.concatenate([np.linspace(100, 110, 20), [104, 98], np.linspace(99, 111, 6),
                        np.linspace(111, 112, 5), [105, 99], np.linspace(100, 113, 6),
                        np.linspace(113, 115, 40)])
    px = _px(a)
    eps = L.drawdown_episodes(px, 0.08, outcomes_through=px.index[-1], merge_gap=21)
    assert len(eps) == 1
    eps_nomerge = L.drawdown_episodes(px, 0.08, outcomes_through=px.index[-1], merge_gap=0)
    assert len(eps_nomerge) == 2


def test_sealed_window_refused_unless_seen_history():
    idx = pd.bdate_range("2023-12-20", periods=10)
    with pytest.raises(L.LabelLeakError):
        L.check_scoring_window(idx)
    L.check_scoring_window(idx, seen_history_ok=True)


def test_scorecard_episode_catch_and_false_alarm():
    px = _dip(depth=0.12)
    idx = px.index
    alert = pd.Series(False, index=idx)
    alert.iloc[25:28] = True          # before onset (idx 30) -> caught, lead 5 at h=5..10
    alert.iloc[70:72] = True          # after recovery, no later onset -> false alarm
    r = S.score(alert, px=px, outcomes_through=idx[-1], depths=(0.10,), horizons=(5, 10),
                sealed_from=None)
    h10 = r["episode_level"]["dd10"]["by_h"]["h10"]
    assert r["episode_level"]["dd10"]["n_episodes"] == 1
    assert h10["caught_at_onset"] == 1 and h10["median_lead_to_onset"] == 5
    assert h10["runs_true"] == 1 and h10["false_alarms"] == 1
    assert r["budget"] == pytest.approx(5 / len(idx), abs=1e-4)


def test_alert_past_outcomes_refused():
    px = _dip()
    alert = pd.Series(True, index=px.index)
    with pytest.raises(L.LabelLeakError):
        S.score(alert, px=px, outcomes_through=px.index[10], sealed_from=None)
