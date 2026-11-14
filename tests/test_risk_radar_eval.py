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


# ---- walk-forward harness (prereg §5) -------------------------------------------------------
from engine import risk_radar as rr
from engine.risk_radar_eval import walkforward as W
from engine.risk_radar_eval import inputs as I


def _calib_fixture():
    """Two Tier-A scares, one validated leg each (minimal but structurally real)."""
    return {
        "bands": {"watch": 55.0, "caution": 68.0, "elevated": 78.0, "risk_off": 88.0},
        "legs": {"legA": {"lift_2020": 1.5, "thr_pct": 0.90},
                 "legB": {"lift_2020": 1.5, "thr_pct": 0.90}},
        "scares": {"credit": {"tier": "A", "legs": [("legA", 1.0)]},
                   "rates": {"tier": "A", "legs": [("legB", 1.0)]}},
        "alert_from": "elevated",
    }


def _wf_fixture(n=40):
    idx = pd.bdate_range("2020-01-02", periods=n)
    subs = pd.DataFrame({"credit": 80.0, "rates": 10.0}, index=idx)
    sigs = pd.DataFrame({"legA": 0.95, "legB": 0.10}, index=idx)
    return idx, subs, sigs


def test_walkforward_label_maturity():
    """A top whose window passes the cutoff, and a bottom whose recovery passes it, are refused."""
    up = np.linspace(100, 110, 40)              # peak at 39
    down = np.linspace(110, 99.0, 11)[1:]       # trough at 49
    rec = np.linspace(99.0, 111.0, 20)[1:]      # recovery ~67
    flat = np.linspace(111, 112, 30)
    peak2 = np.linspace(112, 113, 6)[1:]        # second peak at 104
    down2 = np.linspace(113, 105.5, 11)[1:]     # breaches before the cutoff, never recovers
    tail = np.linspace(105.5, 106.0, 15)
    px = _px(np.concatenate([up, down, rec, flat, peak2, down2, tail]), start="2020-01-02")
    cut = px.index[112]                         # between the second breach and its window end
    eps, turns = W.fit_labels(px, cut)
    kinds = [(t.kind, t.date) for t in turns]
    assert ("top", px.index[39]) in kinds
    assert ("bottom", px.index[49]) in kinds
    late = [e for e in eps if e.peak >= px.index[100]]
    assert late, "the second episode exists at the cutoff"
    assert not any(t.date == late[0].peak for t in turns), "top window passes fit_end"
    # the second episode is still open at the cutoff -> no bottom turn for it
    assert [t.kind for t in turns].count("bottom") == 1
    # moving the cutoff back before the first recovery drops its bottom too
    _, early = W.fit_labels(px, px.index[60])
    assert [t.kind for t in early] == ["top"]


def test_walkforward_parameter_intervention(monkeypatch):
    """g changes the gate series and Delta changes the bands; both change states."""
    idx, subs, sigs = _wf_fixture()
    calib = _calib_fixture()
    always_on = pd.Series(True, index=idx)
    always_off = pd.Series(False, index=idx)

    s_gate_on = W.states_for(subs, sigs, calib, always_on, 0.0)
    s_gate_off = W.states_for(subs, sigs, calib, always_off, 0.0)
    assert s_gate_on.iloc[0] == "elevated"       # 80 >= 78
    assert s_gate_off.iloc[0] == "caution"       # gate caps the loud state
    assert not s_gate_on.equals(s_gate_off)

    s_dn = W.states_for(subs, sigs, calib, always_on, -10.0)
    s_dp = W.states_for(subs, sigs, calib, always_on, 10.0)
    assert s_dn.iloc[0] == "risk-off" and s_dp.iloc[0] == "caution"
    assert not s_dn.equals(s_dp)
    # delta is a pure band shift, not a calibration mutation
    assert calib["bands"]["elevated"] == 78.0

    # the harness injects its gate and never reads the module gate constant
    def _boom(*a, **k):
        raise AssertionError("states_for must not call context_gate_series")
    monkeypatch.setattr(rr, "context_gate_series", _boom)
    W.states_for(subs, sigs, calib, always_on, 0.0)


def test_walkforward_gate_none_is_always_true():
    idx, subs, sigs = _wf_fixture()
    calib = _calib_fixture()
    assert W.states_for(subs, sigs, calib, None, 0.0).iloc[0] == "elevated"
    assert W.loud_share(W.states_for(subs, sigs, calib, pd.Series(False, index=idx), 0.0)) == 0.0


def test_walkforward_feature_prefix_invariance(monkeypatch):
    """Truncating every store frame at t leaves leading_signals() unchanged at and before t."""
    from lib import store
    t = pd.Timestamp("2024-06-03")
    full = rr.leading_signals()
    assert not full.empty
    orig = store.read

    def truncating(group, name):
        df = orig(group, name)
        return None if df is None else df.loc[:t]

    monkeypatch.setattr(store, "read", truncating)
    cut = rr.leading_signals()
    assert cut.index.max() <= t
    a = full.loc[full.index <= t]
    b = cut.reindex(a.index)
    common = [c for c in a.columns if c in b.columns]
    pd.testing.assert_frame_equal(a[common], b[common], check_freq=False, check_names=False)


def test_walkforward_calendar_refuses_nan():
    """The walk-forward scoring path refuses an alert with a missing session."""
    px = _dip(depth=0.12)
    idx = px.index
    eps = L.drawdown_episodes(px, 0.10, outcomes_through=idx[-1])
    loud = pd.Series(False, index=idx)
    loud.iloc[30:40] = True
    loud = loud.astype(object)
    loud.iloc[5] = None
    with pytest.raises(ValueError):
        W._series_block({"wf": loud}, eps, idx[-1])


def test_walkforward_effective_state_hash_fields():
    calib = _calib_fixture()
    rec = W.effective_state("F22", 0.40, 2.0, calib)
    for k in ("fold", "g", "delta", "bands", "code_commit", "prereg_sha256",
              "effective_state_sha256"):
        assert k in rec
    assert rec["bands"]["elevated"] == 80.0
    assert rec["g"] == 0.40 and rec["delta"] == 2.0
    # the hash actually tracks the parameters
    assert rec["effective_state_sha256"] != W.effective_state("F22", 0.40, 4.0, calib)[
        "effective_state_sha256"]
    hdr = W.build_header([{"effective_state": rec}])
    assert hdr["folds"][0]["effective_state_sha256"] == rec["effective_state_sha256"]
    for k in ("prereg_sha256", "code_commit", "generated_utc", "input_last_dates", "folds"):
        assert k in hdr


def test_walkforward_prefix_invariance_lagged_inputs_gate_and_state(monkeypatch):
    """Prereg §5.2 in full: lagged legs, gate inputs, sub-scores and state at <= t are unchanged
    when every store frame is truncated at t."""
    from lib import store
    t = pd.Timestamp("2024-06-03")
    calib = rr._calib()

    def build():
        sg = I.incumbent_signals()
        gc = I.gate_components()
        sb = rr.subscore_series(sg, calib)
        win = sb.index[(sb.index > t - pd.Timedelta(days=120)) & (sb.index <= t)]
        gate = I.gate_series(gc, 0.40).reindex(sb.index).fillna(False)
        st = W.states_for(sb.loc[win], sg, calib, gate, 0.0)
        return sg, gc, sb, st

    full = build()
    assert len(full[0].loc[:t]) > 500 and len(full[3]) > 50
    assert full[0].index.max() > t and full[2].index.max() > t  # something was truncated
    orig = store.read
    monkeypatch.setattr(store, "read",
                        lambda g, n: (lambda df: None if df is None else df.loc[:t])(orig(g, n)))
    cut = build()
    for a, b in zip(full[:3], cut[:3]):
        a = a.loc[a.index <= t]
        b = b.reindex(a.index)
        cols = [c for c in a.columns if c in b.columns]
        pd.testing.assert_frame_equal(a[cols], b[cols], check_freq=False, check_names=False)
    pd.testing.assert_series_equal(full[3], cut[3].reindex(full[3].index), check_names=False)


@pytest.mark.parametrize("d", ["2020-03-18", "2022-06-15", "2024-08-07", "2025-04-09"])
def test_pit_replay_matches_production_engine_at_d(monkeypatch, d):
    """Addendum 3: each replayed FRED leg at session d equals what engine/risk_radar.leading_signals
    computes when the store holds only what was released by d (production at d's nightly run)."""
    from lib import store
    from engine.risk_radar_eval import availability as A
    d = pd.Timestamp(d)
    full = rr.leading_signals()
    pit = A.pit_signals(full)
    orig = store.read

    def as_of(group, name):
        df = orig(group, name)
        if df is None:
            return None
        df = df.copy()
        ix = pd.to_datetime(df.index)
        if group == "fred" and name in ("DEXJPUS", "DFII10", "BAMLH0A0HYM2"):
            rel = A.release_dates(name, ix)
            return df[(rel.values <= np.datetime64(d))]
        return df[ix <= d]

    monkeypatch.setattr(store, "read", as_of)
    prod = rr.leading_signals()
    for col in A.LEGS:
        assert abs(prod.at[d, col] - pit.at[d, col]) < 1e-12, col


def test_release_rules():
    from engine.risk_radar_eval import availability as A
    # rule only (dates outside the observed table): DEXJPUS Tue 2018-05-22 -> Mon 2018-05-28 is
    # Memorial Day -> Tue 2018-05-29; DFII10 Fri 2018-06-29 -> Mon 2018-07-02
    r = A.release_dates("DEXJPUS", pd.DatetimeIndex(["2018-05-22"]))
    assert r.iloc[0] == pd.Timestamp("2018-05-29")
    assert A.release_dates("DFII10", pd.DatetimeIndex(["2018-06-29"])).iloc[0] == pd.Timestamp("2018-07-02")
    # observed table wins: the 2021-03-12 DEXJPUS anomaly was released 2021-03-22
    assert A.release_dates("DEXJPUS", pd.DatetimeIndex(["2021-03-12"])).iloc[0] == pd.Timestamp("2021-03-22")


def test_walkforward_seen_history_follows_score_window():
    # #11137 review: F24 fits through 2023-12-29 but scores 2024 -> seen history
    seen = {f["name"]: W.score_window_seen(f) for f in W.FOLDS}
    assert seen == {"F22": False, "F23": False, "F24": True, "F25": True, "F26": True}


def test_hy_baseline_uses_release_rule_on_holiday_monday():
    # #11137 review: obs Fri 2019-10-11 is released Tue 2019-10-15 (Mon 10-14 is Columbus Day)
    from engine.risk_radar_eval import inputs as I
    raw = pd.Series({pd.Timestamp("2019-10-09"): 4.30, pd.Timestamp("2019-10-10"): 4.26,
                     pd.Timestamp("2019-10-11"): 4.10, pd.Timestamp("2019-10-14"): 4.08,
                     pd.Timestamp("2019-10-15"): 4.00})
    sessions = pd.DatetimeIndex(["2019-10-11", "2019-10-14", "2019-10-15", "2019-10-16"])
    h = I.hy_oas_known(raw, sessions)
    assert h.loc["2019-10-11"] == 4.26     # Thursday's value, released Friday
    assert h.loc["2019-10-14"] == 4.26     # Friday's value is NOT yet known on the holiday
    assert h.loc["2019-10-15"] == 4.08     # Fri + Mon released Tue; latest obs is Mon
    assert h.loc["2019-10-16"] == 4.00
