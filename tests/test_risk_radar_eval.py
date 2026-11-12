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


def test_loss_avoided_and_costs():
    px = _dip(depth=0.12)
    idx = px.index
    alert = pd.Series(False, index=idx)
    alert.iloc[34:40] = True          # mid-decline through trough (trough at idx 39)
    r = S.score(alert, px=px, outcomes_through=idx[-1], depths=(0.10,), horizons=(5,),
                sealed_from=None)
    h = r["episode_level"]["dd10"]["by_h"]["h5"]
    ep = h["per_episode"][0]
    # first alert at idx 34: price there is partway down; share of decline after it is in (0,1)
    assert 0.3 < ep["loss_avoided_share"] < 0.8
    assert h["loss_avoided_sum"] > 0
    assert h["rebound_forgone_sum"] > 0          # out on the session after the trough
    assert h["outside_return_forgone_sum"] == 0
    assert ep["trough_to_all_clear"] == 1
    lo, hi = h["share_caught_by_breach_ci90"]
    assert lo < 1.0 <= hi + 1e-9


def test_interval_is_wide_for_nine_cases():
    from engine.risk_radar_eval.scorecard import _cp
    lo, hi = _cp(3, 9)
    assert hi - lo > 0.45


# ---- pivot scorecard -------------------------------------------------------------------------
from engine.risk_radar_eval import pivots as P


def _pivot_setup(on_from, on_to, depth=0.12):
    px = _dip(depth=depth)                 # peak idx 29, trough idx 39, recovery ~ idx 59
    idx = px.index
    eps = L.drawdown_episodes(px, 0.10, outcomes_through=idx[-1])
    alert = pd.Series(False, index=idx)
    alert.iloc[on_from:on_to] = True
    return px, idx, eps, alert


def test_pivot_late_call_counts_with_delay():
    px, idx, eps, alert = _pivot_setup(33, 42)       # on 4 after top, off 3 after trough
    r = P.score_pivots(alert, turns=P.turns_from_episodes(eps), episodes=eps,
                       outcomes_through=idx[-1], pre=21, post=10, sealed_from=None)
    assert r["top"]["flagged"] == 1 and r["top"]["delays"] == [4]
    assert r["bottom"]["flagged"] == 1 and r["bottom"]["delays"] == [3]
    assert r["false_risk_off"] == 0 and r["premature_all_clear"] == 0


def test_pivot_false_signal_and_premature_all_clear():
    px, idx, eps, alert = _pivot_setup(31, 34)       # on then off before the trough (idx 39)
    alert.iloc[75:78] = True                          # after recovery, near no turn
    r = P.score_pivots(alert, turns=P.turns_from_episodes(eps), episodes=eps,
                       outcomes_through=idx[-1], pre=3, post=3, sealed_from=None)
    assert r["top"]["flagged"] == 1
    assert r["bottom"]["flagged"] == 0
    assert r["premature_all_clear"] == 1
    assert r["false_risk_off"] == 1


def test_pivot_censoring_and_open_episode():
    px, idx, eps, alert = _pivot_setup(33, 42)
    cut = idx[45]                                     # before recovery: episode open
    eps_open = L.drawdown_episodes(px, 0.10, outcomes_through=cut)
    turns = P.turns_from_episodes(eps_open)
    assert [t.kind for t in turns] == ["top"]          # no bottom until recovery
    a = alert.loc[:cut]
    r = P.score_pivots(a, turns=turns, episodes=eps_open, outcomes_through=cut,
                       pre=21, post=20, sealed_from=None)
    assert r["top"]["n_turns"] == 0 and r["top"]["censored"] == 1   # window passes the cutoff


def test_pivot_refuses_missing_sessions():
    px, idx, eps, alert = _pivot_setup(33, 42)
    alert = alert.astype(object); alert.iloc[5] = None
    with pytest.raises(ValueError):
        P.score_pivots(alert, turns=[], episodes=eps, outcomes_through=idx[-1], sealed_from=None)


def test_pivot_off_flicker_is_not_an_all_clear():
    px, idx, eps, alert = _pivot_setup(32, 45)
    alert.iloc[36] = False                            # one-session flicker before the trough
    r = P.score_pivots(alert, turns=P.turns_from_episodes(eps), episodes=eps,
                       outcomes_through=idx[-1], pre=21, post=10, sealed_from=None)
    assert r["bottom"]["delays"] == [6]               # off at idx 45, trough idx 39
    assert r["premature_all_clear"] == 1 and r["n_calls"]["off_flickers"] == 1


def test_pivot_clusters_and_per_asset_alerts():
    px, idx, eps, alert = _pivot_setup(33, 42)
    t = P.turns_from_episodes(eps)
    turns = ([P.Turn(x.kind, x.date, x.depth, asset="A", cluster_id=f"c{x.kind}") for x in t]
             + [P.Turn(x.kind, x.date, x.depth, asset="B", cluster_id=f"c{x.kind}") for x in t]
             + [P.Turn("top", idx[29], asset="C")])
    quiet = pd.Series(False, index=idx)
    r = P.score_pivots_multi(turns, {"A": alert, "B": quiet}, {"A": eps, "B": eps},
                             outcomes_through=idx[-1], posts=(10,), sealed_from=None)
    top = r["by_post"]["post10"]["top"]
    assert top["n_turns"] == 2 and top["flagged"] == 1          # A flagged, B not
    assert top["n_clusters"] == 1 and top["clusters_flagged"] == 1
    assert r["no_alert"] == ["C"]


def test_placebo_near_high_beats_unconditional_on_tops():
    px, idx, eps, _ = _pivot_setup(0, 0)
    turns = P.turns_from_episodes(eps)
    alert = pd.Series(False, index=idx); alert.iloc[26:29] = True
    kw = dict(px=px, turns=turns, episodes=eps, outcomes_through=idx[-1], n_draws=200,
              sealed_from=None, pre=5, post=2)
    u = P.placebo(alert, near=None, **kw)
    h = P.placebo(alert, near="high", **kw)
    assert h["top"]["placebo_mean"] > u["top"]["placebo_mean"]
    assert h["eligible_share"] < 1.0 and u["top"]["observed"] == 1.0


def test_beyond_reference_literal_and_strict():
    from engine.risk_radar_eval.pivots import beyond_reference
    t = lambda d, f, dl: {"kind": "top", "date": d, "status": "scored", "flagged": f, "delay": dl}
    sig = {"false_risk_off_per_year": 0.5, "turns": [t("2021-01-04", True, -5), t("2021-06-01", True, -3),
                                                      t("2022-01-03", True, 4), t("2022-06-01", False, None)]}
    ref_hi = {"false_risk_off_per_year": 6.0, "turns": [t("2021-01-04", True, -1), t("2021-06-01", False, None),
                                                         t("2022-01-03", True, 0), t("2022-06-01", True, -2)]}
    r = beyond_reference(sig, ref_hi)
    assert (r["n_turns"], r["early_catches"], r["also_caught_by_reference"]) == (4, 2, 1)
    assert r["incremental_literal"] == 2 and r["incremental_strict"] == 1
    assert r["incremental_strict_dates"] == ["2021-06-01"]
    ref_lo = dict(ref_hi, false_risk_off_per_year=0.2)
    assert beyond_reference(sig, ref_lo)["incremental_literal"] == 1
