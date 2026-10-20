from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from engine import vol_fitted_har as m


def _synthetic_close(n: int = 1400, seed: int = 7) -> pd.Series:
    """Hermetic GARCH-like price path on an integer index (no calendar dates)."""
    rng = np.random.default_rng(seed)
    var = np.empty(n)
    r = np.empty(n)
    var[0] = 1e-4
    r[0] = 0.0
    for t in range(1, n):
        var[t] = 2e-6 + 0.08 * r[t - 1] ** 2 + 0.9 * var[t - 1]
        r[t] = math.sqrt(var[t]) * rng.standard_normal()
    close = 100.0 * np.exp(np.cumsum(r))
    return pd.Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------------ requirement 1
def test_req1_fit_and_forecast_use_only_information_at_cutoff():
    close = _synthetic_close()
    r = m.log_returns(close)
    h = 21
    base = m.har_forecast_path(r, h, min_train=300)
    s = 1000  # a forecast session
    perturbed = r.copy()
    perturbed.iloc[s + 1:] = perturbed.iloc[s + 1:] * 5.0  # change everything after s
    alt = m.har_forecast_path(perturbed, h, min_train=300)
    assert np.isfinite(base["forecast"].iloc[s])
    assert base["forecast"].iloc[: s + 1].equals(alt["forecast"].iloc[: s + 1])
    assert int(base["cutoff_pos"].iloc[s]) <= s


def test_req1_controls_are_causal():
    r = m.log_returns(_synthetic_close())
    s = 900
    pert = r.copy()
    pert.iloc[s + 1:] = 0.5
    for fn in (lambda x: m.trailing_msr(x, 22), m.ewma_variance):
        a, b = fn(r), fn(pert)
        assert a.iloc[: s + 1].equals(b.iloc[: s + 1])
    close = _synthetic_close()
    pc = close.copy()
    pc.iloc[s + 1:] = pc.iloc[s + 1:] * 3.0
    assert m.incumbent_blend_vol(close).iloc[: s + 1].equals(m.incumbent_blend_vol(pc).iloc[: s + 1])


# ------------------------------------------------------------------ requirement 2
def test_req2_forward_windows_excluded_from_training():
    n, h, c = 200, 21, 150
    mask = m.training_mask(n, c, h, np.ones(n, dtype=bool))
    assert mask[: c - h + 1].all()
    assert not mask[c - h + 1:].any()


def test_req2_unmatured_targets_cannot_move_the_fit():
    r = m.log_returns(_synthetic_close())
    h, c = 21, 1000
    X = m.har_features(r).to_numpy()
    y = m.forward_target(r, h).values.to_numpy()
    fit = m.fit_log_har(X, y, c, h, min_train=300)
    y2 = y.copy()
    y2[c - h + 1:] = 1.0  # rows whose forward window is still open at the cutoff
    fit2 = m.fit_log_har(X, y2, c, h, min_train=300)
    assert fit == fit2
    y3 = y.copy()
    y3[c - h] = y3[c - h] * 50.0  # last matured row DOES enter
    assert m.fit_log_har(X, y3, c, h, min_train=300) != fit


def test_req2_back_transform_uses_training_residuals_only():
    r = m.log_returns(_synthetic_close())
    h, c = 21, 1000
    X = m.har_features(r).to_numpy()
    y = m.forward_target(r, h).values.to_numpy()
    fit = m.fit_log_har(X, y, c, h, min_train=300)
    assert fit.smear > 1.0  # Jensen correction on log scale
    y_eval_changed = y.copy()
    y_eval_changed[c:] = y_eval_changed[c:] * 10.0
    assert m.fit_log_har(X, y_eval_changed, c, h, min_train=300).smear == fit.smear


def _relabel(target: m.LabeledTarget, values: np.ndarray) -> m.LabeledTarget:
    return m.LabeledTarget(values=pd.Series(values, index=target.values.index),
                           label=target.label, horizon=target.horizon)


def test_req2_c3_scale_uses_matured_training_targets_only():
    r = m.log_returns(_synthetic_close())
    h, c, refit = 21, 1008, 21  # c is on the refit grid
    f = m.trailing_msr(r, 22)
    t = m.forward_target(r, h)
    y = t.values.to_numpy()
    base = m.scaled_forecast_path(f, t, h, refit_every=refit, min_train=300)
    seg = slice(c, c + refit)
    assert np.isfinite(base.iloc[seg]).all()
    y_future = y.copy()
    y_future[c - h + 1:] = y_future[c - h + 1:] * 7.0  # unmatured and evaluation-period targets
    alt = m.scaled_forecast_path(f, _relabel(t, y_future), h, refit_every=refit, min_train=300)
    assert base.iloc[seg].equals(alt.iloc[seg])
    y_train = y.copy()
    y_train[: c - h + 1] = y_train[: c - h + 1] * 2.0  # matured training targets DO move k
    moved = m.scaled_forecast_path(f, _relabel(t, y_train), h, refit_every=refit, min_train=300)
    np.testing.assert_allclose(moved.iloc[seg].to_numpy(), 2.0 * base.iloc[seg].to_numpy(), rtol=1e-12)


def test_req2_interval_quantiles_use_matured_training_targets_only():
    r = m.log_returns(_synthetic_close())
    h, c, refit = 21, 1008, 21
    f = m.trailing_msr(r, 22)
    t = m.forward_target(r, h)
    y = t.values.to_numpy()
    base = m.empirical_interval_path(f, t, h, refit_every=refit, min_train=300)
    seg = slice(c, c + refit)
    assert np.isfinite(base.iloc[seg].to_numpy()).all()
    y_future = y.copy()
    y_future[c - h + 1:] = y_future[c - h + 1:] * 7.0
    alt = m.empirical_interval_path(f, _relabel(t, y_future), h, refit_every=refit, min_train=300)
    pd.testing.assert_frame_equal(base.iloc[seg], alt.iloc[seg], check_exact=True)
    y_train = y.copy()
    y_train[: c - h + 1] = y_train[: c - h + 1] * 2.0
    moved = m.empirical_interval_path(f, _relabel(t, y_train), h, refit_every=refit, min_train=300)
    np.testing.assert_allclose(moved.iloc[seg].to_numpy(), 2.0 * base.iloc[seg].to_numpy(), rtol=1e-9)


# ------------------------------------------------------------------ requirement 3
def test_req3_daily_and_hf_labels_never_mix_silently():
    r = m.log_returns(_synthetic_close())
    t = m.forward_target(r, 21)
    assert t.label == m.LABEL_DAILY_CC
    with pytest.raises(m.LabelMismatchError):
        m.forward_target(r, 21, label="HF_INTEGRATED_VARIANCE")
    hf = m.LabeledTarget(values=t.values, label="HF_INTEGRATED_VARIANCE", horizon=21)
    with pytest.raises(m.LabelMismatchError):
        m.require_label(hf)
    with pytest.raises(m.LabelMismatchError):
        m.assert_single_label([t, hf])
    with pytest.raises(m.LabelMismatchError):
        m.require_label(t.values)  # an unlabelled series is refused
    assert m.assert_single_label([t, t]) == m.LABEL_DAILY_CC


# ------------------------------------------------------------------ requirement 4
def test_req4_qlike_zero_variance_handling_is_declared_and_finite():
    y = np.array([0.0, 1e-12, 1e-4, 2e-4])
    f = np.array([1e-4, 0.0, 1e-4, 1e-4])
    q = m.qlike(y, f, m.DEFAULT_FLOOR)
    assert np.isfinite(q).all() and (q >= 0).all()
    assert q[2] == pytest.approx(0.0)
    assert m.qlike(1e-4, 1e-4) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        m.qlike(y, f, 0.0)
    assert m.DEFAULT_FLOOR in m.FLOOR_SENSITIVITY and len(m.FLOOR_SENSITIVITY) >= 3


def test_req4_floor_sensitivity_reports_every_declared_floor():
    y = np.array([0.0, 1e-9, 1e-4, 3e-4])
    out = m.floor_sensitivity(y, {"a": np.full(4, 1e-4), "b": np.full(4, 2e-4)})
    assert set(out) == {repr(x) for x in m.FLOOR_SENSITIVITY}
    for row in out.values():
        assert set(row) == {"a", "b"} and all(np.isfinite(v) for v in row.values())
    assert out[repr(1e-10)]["a"] != out[repr(1e-6)]["a"]  # the floor genuinely matters


# ------------------------------------------------------------------ requirement 5
def test_req5_block_bootstrap_detects_real_gain_and_not_noise():
    rng = np.random.default_rng(3)
    n = 2000
    ctrl = 1.0 + 0.3 * rng.standard_normal(n)
    better = ctrl - 0.1 + 0.05 * rng.standard_normal(n)
    noise = ctrl + 0.3 * rng.standard_normal(n)
    good = m.paired_block_bootstrap(ctrl, better, block_len=63, n_boot=500, seed=1)
    null = m.paired_block_bootstrap(ctrl, noise, block_len=63, n_boot=500, seed=1)
    assert good["diff_ci"][0] > 0 and good["rel_improvement"] > 0.05
    assert null["diff_ci"][0] < 0 < null["diff_ci"][1]
    assert good["honest_n_blocks"] == n // 63
    assert m.newey_west_tstat(ctrl - better, lag=21) > 3


def test_req5_keep_requires_beating_every_simple_control_by_the_bar():
    win = {"rel_improvement": 0.06, "diff_ci": [0.001, 0.01]}
    small = {"rel_improvement": 0.01, "diff_ci": [0.0001, 0.002]}
    wide = {"rel_improvement": 0.06, "diff_ci": [-0.001, 0.01]}
    kw = dict(bar=0.03, n_blocks=37, min_blocks=30, n_assets=13, min_assets=5, floor_flip=False)
    assert m.decide({"a": win, "b": win}, **kw) == "KEEP"
    assert m.decide({"a": win, "b": small}, **kw) == "REJECT"  # complexity bar not cleared
    assert m.decide({"a": win, "b": wide}, **kw) == "REJECT"  # uncertainty not cleared
    assert m.decide({"a": win}, **{**kw, "floor_flip": True}) == "REJECT"
    assert m.decide({"a": win}, **{**kw, "n_blocks": 10}) == "INSUFFICIENT_DATA"


# ------------------------------------------------------------------ requirement 6
def test_req6_research_success_changes_no_production_effect():
    for v in m.VERDICTS:
        eff = m.production_effects(v)
        assert set(eff) == {"cone_probability_changed", "model_promoted",
                            "portfolio_budget_changed", "live_forecast_default_changed"}
        assert not any(eff.values())
    with pytest.raises(ValueError):
        m.production_effects("PROMOTE")


def test_no_silent_activation_module_contract():
    assert m.RESEARCH_ONLY is True
    assert m.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    public = {k for k in dir(m) if not k.startswith("_")}
    for forbidden in ("register", "activate", "schedule", "promote", "wire", "main", "run"):
        assert forbidden not in public
    # pure functions: calling them leaves inputs untouched and the module state unchanged
    close = _synthetic_close(600)
    snapshot = close.copy()
    before = {k: getattr(m, k) for k in ("RESEARCH_ONLY", "DEFAULT_FLOOR", "HAR_COMPONENTS", "EWMA_LAMBDA")}
    m.har_forecast_path(m.log_returns(close), 21, min_train=200)
    assert close.equals(snapshot)
    assert before == {k: getattr(m, k) for k in before}


def test_incumbent_reimplementation_matches_reference_formula():
    close = _synthetic_close(400)
    ret = close.pct_change(fill_method=None)
    ref = pd.concat([ret.rolling(L, min_periods=min(L, max(2, L // 2))).std(ddof=0)
                     for L in (2, 5, 22, 66)], axis=1).mean(axis=1)
    pd.testing.assert_series_equal(m.incumbent_blend_vol(close), ref)


def test_bounded_inputs_are_enforced():
    with pytest.raises(ValueError):
        m.trailing_msr(pd.Series(np.zeros(m.MAX_ROWS + 1)), 5)
    with pytest.raises(ValueError):
        m.log_returns(pd.Series([1.0, -1.0]))
