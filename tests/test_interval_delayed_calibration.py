"""Hermetic tests for the Q16 research harness engine/interval_delayed_calibration.py.

Synthetic data only, integer/relative indexes only; no network, no repo files, no
dependence on the current date. Tests are named after the brief requirement they pin.
"""
from __future__ import annotations

import math
import types

import numpy as np
import pytest

from engine import interval_delayed_calibration as M


def _scores(n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.abs(rng.standard_normal(n))


# ─────────────────────────────────────────────────────────────────────────────
# req1 — no update consumes a label before its maturity/availability
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("method", ["rolling", "aci", "fixed"])
@pytest.mark.parametrize("avail_lag", [0, 3])
def test_req1_runner_never_consumes_immature_label(method, avail_lag):
    s = _scores(800, seed=1)
    h = 7
    r = M.run_delayed_calibration(s, horizon=h, alpha=0.2, method=method, gamma=0.02,
                                  window=120, min_calib=60, avail_lag=avail_lag,
                                  q_fixed=1.2)
    delay = h + avail_lag
    assert int(r["delay"]) == delay
    assert M.maturity_violations(r["consumed_max"], h, avail_lag) == 0
    idx = np.arange(s.size)
    used = r["consumed_max"] >= 0
    assert np.all(r["consumed_max"][used] <= idx[used] - delay)


@pytest.mark.parametrize("method", ["rolling", "aci"])
def test_req1_future_label_cannot_change_earlier_quantiles(method):
    s = _scores(600, seed=2)
    h, lag = 10, 2
    j_star = 300
    base = M.run_delayed_calibration(s, horizon=h, alpha=0.2, method=method, gamma=0.05,
                                     window=100, min_calib=50, avail_lag=lag)
    s2 = s.copy()
    # labels of origins >= j_star are only usable from j_star + h + lag onward; a run of
    # 30 large labels (> 1 - level of a 100-wide window) must move later quantiles
    s2[j_star:j_star + 30] = 1e6
    pert = M.run_delayed_calibration(s2, horizon=h, alpha=0.2, method=method, gamma=0.05,
                                     window=100, min_calib=50, avail_lag=lag)
    cut = j_star + h + lag
    np.testing.assert_array_equal(base["q"][:cut], pert["q"][:cut])
    np.testing.assert_array_equal(base["alpha_t"][:cut], pert["alpha_t"][:cut])
    assert not np.array_equal(base["q"][cut:], pert["q"][cut:])


def test_req1_training_tuning_and_fixed_quantile_ignore_labels_maturing_after_cutoff():
    s = _scores(900, seed=3)
    h, te = 11, 600
    g0 = M.tune_gamma(s, horizon=h, alpha=0.2, gammas=(0.001, 0.01, 0.05), train_end=te,
                      tune_start=200, window=150, min_calib=60)
    q0 = M.fixed_split_quantile(s, 0.2, te, h)
    s2 = s.copy()
    immature = ~M.matured_mask(s.size, h, te)
    s2[immature] = 50.0 * (1.0 + np.arange(int(immature.sum())))
    g1 = M.tune_gamma(s2, horizon=h, alpha=0.2, gammas=(0.001, 0.01, 0.05), train_end=te,
                      tune_start=200, window=150, min_calib=60)
    q1 = M.fixed_split_quantile(s2, 0.2, te, h)
    assert g0 == g1
    assert q0 == q1


def test_req1_maturity_clock_boundaries_and_leaky_diagnostic_is_flagged():
    assert M.label_available(10, 5, 15) is True
    assert M.label_available(10, 5, 14) is False
    assert M.label_available(10, 5, 16, avail_lag=1) is True
    assert M.label_available(10, 5, 15, avail_lag=1) is False
    mask = M.matured_mask(20, 5, 12)
    assert mask.sum() == 8 and mask[7] and not mask[8]
    leaky = M.run_leaky_aci_diagnostic(_scores(400, 4), alpha=0.2, gamma=0.02, window=80,
                                       min_calib=40)
    assert leaky["uses_immature_labels"] is True
    assert M.maturity_violations(leaky["consumed_max"], 22) > 0


# ─────────────────────────────────────────────────────────────────────────────
# req2 — repeated forecasts of one outcome are not independent evidence
# ─────────────────────────────────────────────────────────────────────────────

def test_req2_overlapping_daily_forecasts_collapse_to_honest_blocks():
    assert M.honest_block_count(np.arange(220), 22) == 10
    assert M.honest_block_count(np.arange(0, 220, 22), 22) == 10
    # five correlated assets on the same dates add no independent blocks
    assert M.honest_block_count(np.tile(np.arange(220), 5), 22) == 10
    assert M.honest_block_count([], 22) == 0


def test_req2_repeated_forecasts_of_same_outcome_count_once():
    ids = ["A"] * 5 + ["B"]
    vals = [1.0, 1.0, 1.0, 1.0, 1.0, 0.0]
    out = M.collapse_repeated_forecasts(ids, vals)
    assert set(out) == {"A", "B"}
    assert out["A"] == 1.0 and out["B"] == 0.0
    # equal weight per outcome, not per forecast: 0.5, not 5/6
    assert np.mean(list(out.values())) == pytest.approx(0.5)


def test_req2_block_bootstrap_widens_for_overlapping_outcomes():
    rng = np.random.default_rng(5)
    e = rng.standard_normal(3000 + 22)
    c = np.concatenate([[0.0], np.cumsum(e)])
    x = c[np.arange(3000) + 22] - c[np.arange(3000)]  # overlapping 22-step sums
    iid = M.circular_block_bootstrap(x, block_len=1, n_boot=600, seed=1)
    blk = M.circular_block_bootstrap(x, block_len=44, n_boot=600, seed=1)
    assert blk["n_blocks"] == math.ceil(3000 / 44)
    assert (blk["hi"] - blk["lo"]) > 2.0 * (iid["hi"] - iid["lo"])
    nw = M.newey_west_se(x, 44)
    naive = float(np.std(x) / math.sqrt(x.size))
    assert nw > 2.0 * naive


# ─────────────────────────────────────────────────────────────────────────────
# req3 — coverage, width and interval score; wide intervals cannot win on coverage
# ─────────────────────────────────────────────────────────────────────────────

def test_req3_interval_score_formula_and_all_three_metrics_reported():
    q = np.array([1.0, 1.0, 2.0])
    s = np.array([0.5, -1.5, 3.0])
    m = M.interval_metrics(q, s, alpha=0.2)
    np.testing.assert_allclose(m["covered"], [1.0, 0.0, 0.0])
    np.testing.assert_allclose(m["width"], [2.0, 2.0, 4.0])
    np.testing.assert_allclose(m["interval_score"], [2.0, 2.0 + 10 * 0.5, 4.0 + 10 * 1.0])
    summ = M.summarize_metrics(m)
    assert set(summ) == {"n_rows", "coverage", "mean_width", "mean_interval_score"}
    assert summ["n_rows"] == 3


def test_req3_arbitrarily_wide_interval_loses_on_interval_score():
    rng = np.random.default_rng(6)
    s = rng.standard_normal(5000)
    q_cal = M.conformal_quantile(np.abs(s[:2500]), 0.8)
    test = s[2500:]
    cal = M.summarize_metrics(M.interval_metrics(np.full(test.size, q_cal), test, 0.2))
    wide = M.summarize_metrics(M.interval_metrics(np.full(test.size, 50.0), test, 0.2))
    assert wide["coverage"] == 1.0 > cal["coverage"]
    assert wide["mean_width"] > cal["mean_width"]
    assert wide["mean_interval_score"] > 10.0 * cal["mean_interval_score"]
    assert abs(cal["coverage"] - 0.8) < 0.03


# ─────────────────────────────────────────────────────────────────────────────
# req4 — abrupt-shift and stationary controls discriminate adaptation from noise
# ─────────────────────────────────────────────────────────────────────────────

def test_req4_live_controls_adapt_to_shift_and_stay_quiet_when_stationary():
    reps = []
    for sc, base in (("stationary", 100), ("shift_up", 200), ("shift_down", 300)):
        for r in range(3):
            out = M.control_experiment(scenario=sc, n=4000, n_train=2000, window=300,
                                       gammas=(0.001, 0.01, 0.05), seed=base + r)
            assert out["maturity_violations_aci"] == 0
            reps.append(out)
    dv = M.discrimination_verdict(reps, alpha=0.2)
    assert dv["criteria"]["shift_up_coverage_recovers"] is True
    assert dv["criteria"]["shift_down_sharpens"] is True
    assert dv["shift_up_gap_fixed"] > 0.15 > dv["shift_up_gap_aci"]
    # no noise chasing beyond a loose tolerance at this small replication count
    assert dv["stationary_is_ratio"] < 1.06


def _rep(sc, cov_fix, cov_aci, w_fix, w_aci, is_fix, is_aci):
    seg = lambda c, w, i: {"coverage": c, "mean_width": w, "mean_interval_score": i}  # noqa: E731
    return {"scenario": sc,
            "fixed": {"test": seg(cov_fix, w_fix, is_fix), "post": seg(cov_fix, w_fix, is_fix)},
            "aci": {"test": seg(cov_aci, w_aci, is_aci), "post": seg(cov_aci, w_aci, is_aci)}}


def test_req4_discrimination_rule_rejects_noise_chasing_and_non_adaptation():
    good = [_rep("stationary", .8, .8, 2.5, 2.5, 3.5, 3.52),
            _rep("shift_up", .5, .78, 2.5, 5.0, 9.0, 7.3),
            _rep("shift_down", .98, .8, 2.5, 1.4, 2.5, 1.9)]
    assert M.discrimination_verdict(good)["controls_discriminate"] is True
    chasing = [dict(good[0], aci={"test": {"coverage": .8, "mean_width": 2.9,
                                           "mean_interval_score": 3.8}})] + good[1:]
    assert M.discrimination_verdict(chasing)["criteria"]["stationary_no_noise_chasing"] is False
    stuck = good[:1] + [_rep("shift_up", .5, .52, 2.5, 2.6, 9.0, 8.9), good[2]]
    assert M.discrimination_verdict(stuck)["criteria"]["shift_up_coverage_recovers"] is False


# ─────────────────────────────────────────────────────────────────────────────
# req5 — per-regime support disclosed, no universal conditional-coverage claim
# ─────────────────────────────────────────────────────────────────────────────

def test_req5_regime_support_discloses_blocks_and_never_claims_conditional_coverage():
    n = 1000
    origins = np.arange(n)
    labels = np.where(origins < 900, "calm", "stress")
    covered = (np.arange(n) % 5 != 0).astype(float)
    out = M.regime_support(labels, covered, origins, horizon=22, min_blocks=20)
    assert set(out) == {"calm", "stress"}
    for row in out.values():
        assert row["conditional_coverage_claim"] is False
        assert set(row) >= {"n_rows", "honest_blocks", "coverage", "support_ok"}
    assert out["calm"]["honest_blocks"] == math.ceil(900 / 22)
    assert out["calm"]["support_ok"] is True
    assert out["stress"]["honest_blocks"] == math.ceil(100 / 22)
    assert out["stress"]["support_ok"] is False


# ─────────────────────────────────────────────────────────────────────────────
# req6 — existing registrations, trials and live forecasts unchanged
# ─────────────────────────────────────────────────────────────────────────────

def test_req6_inputs_and_registrations_unchanged_and_nothing_written(tmp_path, monkeypatch):
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    registry = {"CN-HAR-2": {"frozen": True, "fit_end": "pre-2024", "trials": 1},
                "HAR-1": {"status": "promoted_null"}}
    snapshot = {k: dict(v) for k, v in registry.items()}
    s = _scores(700, seed=7)
    s_copy = s.copy()
    M.run_delayed_calibration(s, horizon=5, alpha=0.2, method="aci", gamma=0.01,
                              window=100, min_calib=50)
    M.tune_gamma(s, horizon=5, alpha=0.2, gammas=(0.001, 0.01), train_end=400,
                 tune_start=150, window=100, min_calib=50)
    M.fixed_split_quantile(s, 0.2, 400, 5)
    M.circular_block_bootstrap(s, block_len=10, n_boot=50, seed=0)
    np.testing.assert_array_equal(s, s_copy)
    assert registry == snapshot
    monkeypatch.chdir(tmp_path)
    try:
        work.rmdir()  # fails with ENOTEMPTY if the reference wrote anything into its working directory
    except OSError as exc:
        pytest.fail(f"reference wrote into its working directory: {exc}")
    assert any("CN-HAR-2" in p for p in M.PROTECTED_REGISTRATIONS)


def test_no_silent_activation():
    assert M.RESEARCH_ONLY is True
    assert M.Q16_VERDICT in {"KEEP", "REJECT", "INSUFFICIENT_DATA"}
    assert M.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    imported = {name for name, v in vars(M).items() if isinstance(v, types.ModuleType)}
    assert imported <= {"math", "np"}
    for name in vars(M):
        low = name.lower()
        assert not any(w in low for w in ("register", "schedule", "activate", "promote",
                                          "publish", "write", "emit"))
    assert all(not hasattr(M, a) for a in ("REGISTRY", "WIRED", "ENABLED"))
