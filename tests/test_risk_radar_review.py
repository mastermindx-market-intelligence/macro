"""Tests for engine/risk_radar_review.py — the Opus self-correction loop.

Hermetic: the LLM `call` and the do-no-harm `compare` are injected. Focus on the CODE clamp
(proposals stay on the rails), and that a proposal is APPLIED only when the backtest says it
improves — otherwise rejected and logged.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from engine import risk_radar_review as rev
from engine.risk_radar import _calib


def _proposal(**deltas):
    return json.dumps({"analysis": "too many FPs from vol", "deltas": deltas,
                       "rationale": "nudge bands up"})


def test_clamp_keeps_bands_on_rails_and_ordered():
    base = _calib()
    # absurd proposal: elevated band to 999, watch above caution -> must clamp + reorder
    p = rev._clamp({"bands": {"elevated": 999.0, "watch": 95.0}}, base, rev._DEFAULTS)
    b = p["bands"]
    assert b["watch"] < b["caution"] < b["elevated"] < b["risk_off"]
    # within +/- band_max_delta of the baked default
    from engine.risk_radar import _DEFAULT_BANDS
    assert abs(b["elevated"] - _DEFAULT_BANDS["elevated"]) <= rev._DEFAULTS["band_max_delta"] + 1e-9


def test_clamp_thr_pct_and_alert_from_rails():
    base = _calib()
    p = rev._clamp({"legs": {"credit_oas_roc": {"thr_pct": 0.40}},   # below floor
                    "alert_from": "calm"}, base, rev._DEFAULTS)        # not allowed
    assert p["legs"]["credit_oas_roc"]["thr_pct"] >= rev._THR_LO
    assert p["alert_from"] in rev._ALERT_ALLOWED                       # 'calm' rejected -> keeps base


def test_clamp_prob_cal_monotonic():
    base = _calib()
    p = rev._clamp({"prob_cal": {"h21": {"calm": 0.5, "risk-off": 0.1}}}, base, rev._DEFAULTS)
    h = p["prob_cal"]["h21"]
    assert h["calm"] <= h["watch"] <= h["caution"] <= h["elevated"] <= h["risk-off"]


def test_applies_only_when_backtest_improves(tmp_path):
    sc = {"n_graded": 100, "alert_precision": 0.3, "recall_dd5_h21": 0.4, "recent_mistakes": []}
    out = rev.run(force=True, root=tmp_path, scorecard=sc,
                  call=lambda s, u: _proposal(bands={"elevated": 74.0}),
                  compare=lambda p: {"improves": True, "legs_ok": True,
                                     "base": {}, "proposed": {}})
    assert out["applied"] is True
    assert (tmp_path / "data" / "risk_radar" / "calibration.json").exists()


def test_rejects_when_backtest_does_not_improve(tmp_path):
    sc = {"n_graded": 100, "alert_precision": 0.3, "recall_dd5_h21": 0.4, "recent_mistakes": []}
    out = rev.run(force=True, root=tmp_path, scorecard=sc,
                  call=lambda s, u: _proposal(bands={"elevated": 60.0}),
                  compare=lambda p: {"improves": False, "legs_ok": True, "base": {}, "proposed": {}})
    assert out["applied"] is False
    assert out["degraded_reason"] == "rejected_by_do_no_harm"
    assert not (tmp_path / "data" / "risk_radar" / "calibration.json").exists()
    # but the rejected proposal IS logged (full audit trail)
    assert (tmp_path / "data" / "risk_radar" / "review_log.jsonl").exists()


def test_insufficient_graded_degrades(tmp_path):
    out = rev.run(force=True, root=tmp_path, scorecard={"n_graded": 5},
                  call=lambda s, u: _proposal(bands={}), compare=lambda p: {"improves": True})
    assert out["applied"] is False
    assert out["degraded_reason"] == "insufficient_graded"


def test_explicit_disable(monkeypatch):
    monkeypatch.setattr(rev, "_cfg", lambda: {**rev._DEFAULTS, "enabled": False})
    out = rev.run(force=False, scorecard={"n_graded": 100})
    assert out["applied"] is False and out["degraded_reason"] == "disabled"


def test_no_token_is_noop(tmp_path):
    # enabled (config) but no token + no injected call -> safe no-op, never applies
    out = rev.run(force=True, root=tmp_path, scorecard={"n_graded": 100, "recent_mistakes": []})
    assert out["applied"] is False
    assert out["degraded_reason"] in ("no_client_or_key", "no_usable_proposal")


def test_no_proposal_degrades(tmp_path):
    out = rev.run(force=True, root=tmp_path, scorecard={"n_graded": 100, "recent_mistakes": []},
                  call=lambda s, u: "not json", compare=lambda p: {"improves": True})
    assert out["applied"] is False
    assert out["degraded_reason"] == "no_usable_proposal"



def test_state_ladder_native_labels_preserve_invalid_price_windows():
    from scripts.research import risk_radar_state_ladder_calibration as sl

    idx = pd.bdate_range("2026-01-01", periods=6)
    spy = pd.Series([100., np.nan, 94., 100., 100., 100.], index=idx)
    out = sl.native_forward_labels(spy, idx, horizon=2, depth=.05)
    assert idx[0] not in out.index
    assert idx[1] not in out.index
    assert idx[2] in out.index
    assert bool(out.loc[idx[2], "event"]) is False


def test_state_ladder_block_sampler_is_deterministic():
    from scripts.research import risk_radar_state_ladder_calibration as sl

    a = sl._moving_block_indices(17, 5, np.random.default_rng(123))
    b = sl._moving_block_indices(17, 5, np.random.default_rng(123))
    assert np.array_equal(a, b)
    assert len(a) == 17
    assert ((a >= 0) & (a < 17)).all()



def _state_ladder_fixture(event_rates):
    from scripts.research import risk_radar_state_ladder_calibration as sl

    idx = pd.bdate_range("2026-01-01", periods=100)
    states = []
    events = []
    for name, rate in zip(sl._ORDER, event_rates):
        states.extend([name] * 20)
        hits = int(round(rate * 20))
        events.extend([True] * hits + [False] * (20 - hits))
    state = pd.Series(states, index=idx)
    labels = pd.DataFrame({
        "end": idx,
        "loss": [-.06 if e else -.01 for e in events],
        "event": events,
    }, index=idx)
    configured = {name: .10 + i * .05 for i, name in enumerate(sl._ORDER)}
    return sl, state, labels, configured


def test_state_ladder_summary_reports_monotonic_order_and_deltas():
    sl, state, labels, configured = _state_ladder_fixture([.05, .10, .20, .30, .40])
    out = sl.summarize_window(state, labels, configured, block=5, seed=7)
    assert out["point_estimate_monotonic"] is True
    assert out["states"]["risk-off"]["event_rate"] == .4
    assert out["states"]["caution"]["configured_state_probability"] == .2
    assert out["adjacent_differences"]["watch->caution"]["difference"] == .1



def test_state_ladder_summary_exposes_nonmonotonic_step():
    sl, state, labels, configured = _state_ladder_fixture([.05, .20, .10, .30, .40])
    out = sl.summarize_window(state, labels, configured, block=5, seed=11)
    assert out["point_estimate_monotonic"] is False
    assert out["adjacent_differences"]["watch->caution"]["difference"] == -.1


def test_state_ladder_thin_cells_are_disclosed():
    sl, state, labels, configured = _state_ladder_fixture([.05, .10, .20, .30, .40])
    out = sl.summarize_window(state, labels, configured, block=5, seed=13)
    assert all(out["states"][name]["thin"] for name in sl._ORDER)


def test_state_ladder_population_fingerprint_binds_outcomes():
    from scripts.research import risk_radar_state_ladder_calibration as sl

    idx = pd.bdate_range("2026-01-01", periods=3)
    a = pd.DataFrame({"end": idx, "loss": [-.01, -.06, -.01],
                      "event": [False, True, False]}, index=idx)
    b = a.copy()
    b.loc[idx[2], "loss"] = -.07
    b.loc[idx[2], "event"] = True
    assert sl._fingerprint(a) != sl._fingerprint(b)



def test_displayed_probability_audit_calls_canonical_probability_surface(monkeypatch):
    from scripts.research import risk_radar_displayed_probability_audit as dp

    idx = pd.bdate_range("2026-01-01", periods=2)
    state = pd.Series(["watch", "caution"], index=idx)
    hot = pd.Series([2, 3], index=idx)
    calls = []

    def fake(state_name, nhot, calib):
        calls.append((state_name, nhot, calib))
        return {"h5": .11 + nhot / 100, "h10": .22, "h21": .33}

    monkeypatch.setattr(dp, "_drawdown_prob", fake)
    calib = {"sentinel": True}
    out = dp.displayed_probability_series(state, hot, calib, 5)
    assert calls == [("watch", 2, calib), ("caution", 3, calib)]
    assert out.tolist() == [.13, .14]


def test_displayed_probability_audit_preserves_shipped_conjunction_bump():
    from scripts.research import risk_radar_displayed_probability_audit as dp

    calib = _calib()
    idx = pd.bdate_range("2026-01-01", periods=3)
    state = pd.Series(["caution"] * 3, index=idx)
    hot = pd.Series([1, 2, 3], index=idx)
    out = dp.displayed_probability_series(state, hot, calib, 21)
    assert out.iloc[1] - out.iloc[0] == dp._CONJ_BUMP["h21"]
    assert out.iloc[2] - out.iloc[1] == dp._CONJ_BUMP["h21"]


def test_displayed_probability_audit_exact_cell_keeps_state_count_composition():
    from scripts.research import risk_radar_displayed_probability_audit as dp

    calib = _calib()
    idx = pd.bdate_range("2026-01-01", periods=4)
    state = pd.Series(["watch", "caution", "watch", "caution"], index=idx)
    hot = pd.Series([2, 1, 2, 1], index=idx)
    probability = dp.displayed_probability_series(state, hot, calib, 21)
    assert probability.nunique() == 1
    labels = pd.DataFrame({
        "end": idx,
        "loss": [-.06, -.01, -.06, -.01],
        "event": [True, False, True, False],
    }, index=idx)
    out = dp.summarize_window(
        state, hot, probability, labels, block=2, seed=17
    )
    cell = next(iter(out["cells"].values()))
    assert cell["n"] == 4
    assert cell["observed_rate"] == .5
    assert {tuple((c["state"], c["hot_count"], c["n"])) for c in cell["composition"]} == {
        ("watch", 2, 2), ("caution", 1, 2)
    }


def test_displayed_probability_audit_hot_count_only_counts_tier_a_at_caution():
    from scripts.research import risk_radar_displayed_probability_audit as dp

    idx = pd.bdate_range("2026-01-01", periods=2)
    subs = pd.DataFrame({
        "credit": [70., 67.],
        "rates": [80., 70.],
        "vol": [99., 99.],
    }, index=idx)
    calib = {
        "bands": {"watch": 55., "caution": 68., "elevated": 78., "risk_off": 88.},
        "scares": {
            "credit": {"tier": "A", "legs": []},
            "rates": {"tier": "A", "legs": []},
            "vol": {"tier": "B", "legs": []},
        },
    }
    out = dp.hot_tier_a_count(subs, calib)
    assert out.tolist() == [2, 1]



def test_probability_recal_oos_pav_pools_only_violating_neighbors():
    from scripts.research import risk_radar_probability_recal_oos as rc

    out = rc.weighted_pav([.10, .20, .15, .40, .50], [10, 10, 10, 10, 10])
    assert out == [.10, .175, .175, .40, .50]


def test_probability_recal_oos_fit_ignores_holdout_outcomes():
    from scripts.research import risk_radar_probability_recal_oos as rc

    idx = pd.bdate_range("2019-12-20", periods=20)
    states = pd.Series(
        (["calm", "watch", "caution", "elevated", "risk-off"] * 4), index=idx
    )
    labels = pd.DataFrame({
        "end": idx,
        "loss": [-.06 if i % 3 == 0 else -.01 for i in range(len(idx))],
        "event": [i % 3 == 0 for i in range(len(idx))],
    }, index=idx)
    by_h = {h: labels.copy() for h in rc.HORIZONS}
    a, _ = rc.fit_state_surface(states, by_h)
    mutated = {h: frame.copy() for h, frame in by_h.items()}
    for frame in mutated.values():
        frame.loc[frame.index >= rc.TRAIN_END, "event"] = ~frame.loc[
            frame.index >= rc.TRAIN_END, "event"
        ]
    b, _ = rc.fit_state_surface(states, mutated)
    assert a == b


def test_probability_recal_oos_candidate_keeps_shipped_conjunction_bump():
    from scripts.research import risk_radar_probability_recal_oos as rc

    idx = pd.bdate_range("2026-01-01", periods=3)
    states = pd.Series(["caution"] * 3, index=idx)
    hot = pd.Series([1, 2, 3], index=idx)
    surface = {
        h: {state: .10 + i * .04 for i, state in enumerate(rc._STATE_ORDER)}
        for h in ("h5", "h10", "h21")
    }
    out = rc.candidate_probability_series(states, hot, surface, 21)
    assert round(out.iloc[1] - out.iloc[0], 12) == rc._CONJ_BUMP["h21"]
    assert round(out.iloc[2] - out.iloc[1], 12) == rc._CONJ_BUMP["h21"]


def test_probability_recal_oos_authority_partition_is_hard_gate():
    from scripts.research import risk_radar_probability_recal_oos as rc

    good = {
        "h5": {s: .02 + i * .01 for i, s in enumerate(rc._STATE_ORDER)},
        "h10": {s: .05 + i * .02 for i, s in enumerate(rc._STATE_ORDER)},
        "h21": {
            "calm": .10, "watch": .12, "caution": .16,
            "elevated": .25, "risk-off": .35,
        },
    }
    assert rc.authority_partition(good)["preserved"] is True
    bad = {h: dict(v) for h, v in good.items()}
    bad["h21"]["caution"] = .19
    assert rc.authority_partition(bad)["preserved"] is False


def test_probability_recal_oos_paired_brier_delta_is_deterministic():
    from scripts.research import risk_radar_probability_recal_oos as rc

    idx = pd.bdate_range("2026-01-01", periods=30)
    labels = pd.DataFrame({
        "end": idx,
        "loss": [-.06 if i % 5 == 0 else -.01 for i in range(30)],
        "event": [i % 5 == 0 for i in range(30)],
    }, index=idx)
    current = pd.Series(.30, index=idx)
    candidate = pd.Series(.20, index=idx)
    a = rc.paired_brier_delta(current, candidate, labels, block=5, seed=7, draws=100)
    b = rc.paired_brier_delta(current, candidate, labels, block=5, seed=7, draws=100)
    assert a == b
    assert a["delta"] < 0


def test_probability_recal_oos_surface_validity_rejects_nonmonotone_or_overrail():
    from scripts.research import risk_radar_probability_recal_oos as rc

    good = {
        h: {s: .05 + i * .05 for i, s in enumerate(rc._STATE_ORDER)}
        for h in ("h5", "h10", "h21")
    }
    assert rc.surface_valid(good)["valid"] is True
    bad = {h: dict(v) for h, v in good.items()}
    bad["h10"]["elevated"] = .01
    assert rc.surface_valid(bad)["valid"] is False
    bad2 = {h: dict(v) for h, v in good.items()}
    bad2["h21"]["risk-off"] = .61
    assert rc.surface_valid(bad2)["valid"] is False


def test_probability_recal_oos_promotion_gate_requires_h21_uncertainty():
    from scripts.research import risk_radar_probability_recal_oos as rc

    def summary(brier=.10, wace=.05):
        return {"brier_score": brier, "weighted_absolute_calibration_error": wace}
    result = {
        "authority_partition": {"preserved": True},
        "surface_validity": {"valid": True},
        "holdout": {
            h: {
                "current": summary(),
                "candidate": summary(.09, .04),
                "paired_brier_delta": {"ci90": [-.02, -.001] if h == "h21" else [-.02, .001]},
                "accepted_population_match": True,
            }
            for h in ("h5", "h10", "h21")
        },
    }
    assert rc.promotion_verdict(result)["promotion_eligible"] is True
    result["holdout"]["h21"]["paired_brier_delta"]["ci90"] = [-.02, .003]
    assert rc.promotion_verdict(result)["promotion_eligible"] is False
