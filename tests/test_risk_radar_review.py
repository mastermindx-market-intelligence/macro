"""Tests for engine/risk_radar_review.py — the Opus self-correction loop.

Hermetic: the LLM `call` and the do-no-harm `compare` are injected. Focus on the CODE clamp
(proposals stay on the rails), and that a proposal is APPLIED only when the backtest says it
improves — otherwise rejected and logged.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from engine import risk_radar as rr
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



def _prob_guard_setup(monkeypatch, *, proposed_brier=0.09, base_brier=0.10,
                      proposed_partition=None, base_partition=None):
    import copy
    from engine import risk_radar_backtest as bt

    base = _calib()
    proposed = copy.deepcopy(base)
    proposed["prob_cal"]["h21"]["elevated"] = min(
        0.6, float(proposed["prob_cal"]["h21"]["elevated"]) + 0.01
    )

    monkeypatch.setattr(bt, "detect_events", lambda: [])
    monkeypatch.setattr(
        bt,
        "state_accuracy",
        lambda calib, **kwargs: {
            "f1": 0.42 if calib is proposed else 0.40,
            "evaluation": {"outcomes_sha256": "state-pop"},
        },
    )
    monkeypatch.setattr(
        bt,
        "gate_report",
        lambda **kwargs: {
            leg: {"lift_2020": 1.5} for leg in proposed.get("legs", {})
        },
    )

    bp = base_partition or {
        "calm": False, "watch": False, "caution": False,
        "elevated": True, "risk-off": True,
    }
    pp = proposed_partition or dict(bp)

    def probability_report(calib, **kwargs):
        is_proposed = calib is proposed
        brier = proposed_brier if is_proposed else base_brier
        partition = pp if is_proposed else bp
        rows = {}
        for horizon in ("h5", "h10", "h21"):
            rows[horizon] = {
                "full": {
                    "brier_score": brier,
                    "n_days": 1000,
                    "evaluation": {"outcomes_sha256": f"{horizon}-full"},
                },
                "y2020": {
                    "brier_score": brier,
                    "n_days": 500,
                    "evaluation": {"outcomes_sha256": f"{horizon}-y2020"},
                },
            }
        return {
            "horizons": rows,
            "authority_partition_h21": partition,
        }

    monkeypatch.setattr(bt, "probability_quality_report", probability_report)
    return bt, base, proposed


def test_probability_guard_rejects_brier_harm_even_when_alert_f1_improves(monkeypatch):
    bt, base, proposed = _prob_guard_setup(
        monkeypatch, proposed_brier=0.11, base_brier=0.10
    )
    verdict = bt.compare_calib(proposed, base)
    assert verdict["probability_gate"]["required"] is True
    assert verdict["probability_gate"]["brier_nonworse"] is False
    assert verdict["probability_gate"]["passes"] is False
    assert verdict["improves"] is False


def test_probability_guard_allows_nonworse_surface_with_strict_brier_gain(monkeypatch):
    bt, base, proposed = _prob_guard_setup(
        monkeypatch, proposed_brier=0.09, base_brier=0.10
    )
    verdict = bt.compare_calib(proposed, base)
    assert verdict["probability_gate"]["required"] is True
    assert verdict["probability_gate"]["brier_nonworse"] is True
    assert verdict["probability_gate"]["strict_brier_improvement"] is True
    assert verdict["probability_gate"]["authority_partition_ok"] is True
    assert verdict["probability_gate"]["passes"] is True
    assert verdict["improves"] is True


def test_probability_guard_rejects_authority_partition_change(monkeypatch):
    changed = {
        "calm": False, "watch": False, "caution": True,
        "elevated": True, "risk-off": True,
    }
    bt, base, proposed = _prob_guard_setup(
        monkeypatch, proposed_brier=0.09, base_brier=0.10,
        proposed_partition=changed,
    )
    verdict = bt.compare_calib(proposed, base)
    assert verdict["probability_gate"]["brier_nonworse"] is True
    assert verdict["probability_gate"]["authority_partition_ok"] is False
    assert verdict["probability_gate"]["passes"] is False
    assert verdict["improves"] is False


def test_probability_guard_is_not_required_for_non_probability_proposal(monkeypatch):
    import copy
    from engine import risk_radar_backtest as bt

    base = _calib()
    proposed = copy.deepcopy(base)
    proposed["bands"]["elevated"] -= 1.0

    monkeypatch.setattr(bt, "detect_events", lambda: [])
    monkeypatch.setattr(
        bt,
        "state_accuracy",
        lambda calib, **kwargs: {
            "f1": 0.42 if calib is proposed else 0.40,
            "evaluation": {"outcomes_sha256": "state-pop"},
        },
    )
    monkeypatch.setattr(
        bt,
        "gate_report",
        lambda **kwargs: {
            leg: {"lift_2020": 1.5} for leg in proposed.get("legs", {})
        },
    )
    monkeypatch.setattr(
        bt, "probability_quality_report",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("probability report must not run without prob_cal delta")
        ),
        raising=False,
    )

    verdict = bt.compare_calib(proposed, base)
    assert verdict["probability_gate"] == {
        "required": False,
        "passes": True,
        "reason": "prob_cal_unchanged",
    }
    assert verdict["improves"] is True



def test_probability_quality_report_scores_actual_displayed_surface(monkeypatch):
    from engine import risk_radar as rr
    from engine import risk_radar_backtest as bt

    calib = _calib()
    idx = pd.bdate_range("2026-01-02", periods=30)
    spy_idx = pd.bdate_range("2026-01-02", periods=60)
    spy = pd.Series(100.0, index=spy_idx)
    spy.iloc[12:15] = [98.0, 94.0, 96.0]

    sigs = pd.DataFrame({"dummy": np.linspace(0.0, 1.0, len(idx))}, index=idx)
    tier_a = [
        scare for scare, spec in calib["scares"].items()
        if spec.get("tier") == "A"
    ]
    subs = pd.DataFrame({scare: 60.0 for scare in tier_a}, index=idx)
    states = pd.Series("caution", index=idx)

    monkeypatch.setattr(rr, "leading_signals", lambda: sigs)
    monkeypatch.setattr(rr, "subscore_series", lambda _sigs, _calib: subs)
    monkeypatch.setattr(bt, "state_series", lambda _subs, _calib, sigs=None: states)
    monkeypatch.setattr(bt, "_spy", lambda drop_missing=False: spy)
    monkeypatch.setattr(
        rr,
        "_drawdown_prob",
        lambda state, nhot, calib=None: {"h5": 0.03, "h10": 0.08, "h21": 0.16},
    )

    report = bt.probability_quality_report(calib)
    assert report["ready"] is True
    for hkey in ("h5", "h10", "h21"):
        assert report["horizons"][hkey]["full"]["n_days"] == 30
        assert report["horizons"][hkey]["y2020"]["n_days"] == 30
        assert 0 <= report["horizons"][hkey]["full"]["brier_score"] <= 1
        assert report["horizons"][hkey]["full"]["evaluation"]["outcomes_sha256"]
    assert report["authority_partition_h21"] == {
        "calm": False,
        "watch": False,
        "caution": False,
        "elevated": True,
        "risk-off": True,
    }


def test_review_result_preserves_probability_gate_evidence(tmp_path, monkeypatch):
    gate = {
        "required": True,
        "passes": False,
        "reason": "probability_brier_worse",
        "brier_nonworse": False,
        "authority_partition_ok": True,
    }
    monkeypatch.setattr(rev, "_gov_proposal", lambda *a, **k: None)
    monkeypatch.setattr(rev, "_gov_reject", lambda *a, **k: None)
    sc = {"n_graded": 100, "alert_precision": 0.3, "recall_dd5_h21": 0.4,
          "recent_mistakes": []}
    out = rev.run(
        force=True,
        persist=False,
        root=tmp_path,
        scorecard=sc,
        call=lambda s, u: _proposal(prob_cal={"h21": {"elevated": 0.26}}),
        compare=lambda p: {
            "improves": False,
            "legs_ok": True,
            "comparison_ready": True,
            "alert_gate": True,
            "probability_gate": gate,
            "base": {},
            "proposed": {},
        },
    )
    assert out["applied"] is False
    assert out["degraded_reason"] == "rejected_by_do_no_harm"
    assert out["backtest"]["probability_gate"] == gate
    assert "Brier" in rev._A6_GATE_SPEC
    assert "authority partition" in rev._A6_GATE_SPEC



def _integrity_signals(*, eligible_last=float("nan"), display_last=0.0):
    idx = pd.bdate_range("2026-08-03", periods=32)
    return pd.DataFrame(
        {
            "growth_defensives": 0.3,
            "growth_cyc_def": 0.3,
            "nh_contraction": [0.9] * 31 + [eligible_last],
            "ai_breadth_divergence": [0.0] * 31 + [display_last],
        },
        index=idx,
    )


def test_current_reading_ineligible_only_preserves_arithmetic_but_is_unavailable():
    out = rr.compute(sigs=_integrity_signals(), gate={"met": False})
    row = next(s for s in out["scares"] if s["scare"] == "internals")

    assert row["score"] == 0.0
    assert row["band"] == "calm"
    assert row["n_legs_resolved"] == 0
    assert row["weight_coverage"] == 0.0

    assert row.get("reading_state") == "UNAVAILABLE"
    assert row.get("display_score") is None
    assert row.get("display_band") is None
    assert out["deescalation"]["receding_scare"] != "internals"
    assert "internals" not in {
        r["key"] for r in out["deescalation"].get("deescalated", [])
    }


def test_current_reading_real_zero_eligible_stays_available_and_calm():
    out = rr.compute(
        sigs=_integrity_signals(eligible_last=0.0, display_last=float("nan")),
        gate={"met": False},
    )
    row = next(s for s in out["scares"] if s["scare"] == "internals")
    assert row["score"] == 0.0
    assert row["n_legs_resolved"] == 1
    assert row.get("reading_state") == "AVAILABLE"
    assert row.get("display_score") == 0.0
    assert row.get("display_band") == "calm"


def test_current_reading_missing_today_cannot_reuse_yesterday_for_recovery():
    idx = pd.bdate_range("2026-08-03", periods=32)
    subs = pd.DataFrame(
        {
            "growth": [80.0] * 20 + [60.0] * 11 + [float("nan")],
            "credit": [30.0] * 32,
        },
        index=idx,
    )
    calib = {
        "bands": {
            "watch": 55.0,
            "caution": 68.0,
            "elevated": 78.0,
            "risk_off": 88.0,
        },
        "legs": {},
        "scares": {
            "growth": {"tier": "A", "legs": []},
            "credit": {"tier": "A", "legs": []},
        },
        "alert_from": "elevated",
    }

    traj = rr.trajectory(subs=subs, calib=calib, sigs=pd.DataFrame(index=idx))
    drivers = (traj or {}).get("drivers") or {}
    for field in ("faded", "warm"):
        assert "growth" not in {x["key"] for x in drivers.get(field, [])}

    deesc = rr._deescalation("growth", subs, traj, {"h21": 0.13})
    assert deesc["receding_scare"] != "growth"
    assert deesc["dominant_velocity"] is None
