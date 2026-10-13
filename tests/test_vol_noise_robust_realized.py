from __future__ import annotations

# Q15 requirement tests for engine.vol_noise_robust_realized (hermetic, synthetic only).
#
# Each test is named after the acceptance requirement it proves (req1..req6). No
# network, no repository data, no file scanning and no dependence on the date.

import builtins
import importlib
import math
import types

import numpy as np
import pytest

from engine import vol_noise_robust_realized as m

N = 4680
IV = 1e-4


def _mc(regimes, reps, n=N, stochastic_vol=False):
    rows = m.monte_carlo_bias_table(n=n, iv=IV, reps=reps, seed=15, regimes=regimes,
                                    stochastic_vol=stochastic_vol)
    return {(r["regime"], r["estimator"]): r for r in rows}


# --------------------------------------------------------------------------- req1
def test_req1_noise_free_synthetic_controls_recover_integrated_variance_target():
    # Known-IV path: the simulator's per-step variance sums exactly to the target.
    x, iv = m.simulate_efficient_path(N, IV, seed=1)
    assert iv == pytest.approx(IV, rel=1e-12)
    assert x.size == N + 1 and x[0] == 0.0

    # Exact algebra on a deterministic path.
    r = np.array([0.01, -0.02, 0.005, 0.0, 0.015])
    assert m.realized_variance(r) == pytest.approx(float(np.sum(r ** 2)), rel=1e-15)
    assert m.realized_kernel(r, 0) == pytest.approx(m.realized_variance(r), rel=1e-15)
    w = m.parzen_weight(np.array([0.0, 0.5, 1.0, 1.5]))
    assert w[0] == 1.0 and w[1] == pytest.approx(0.25) and w[2] == 0.0 and w[3] == 0.0

    # Monte Carlo recovery with no noise (constant-shape and stochastic vol).
    for sv in (False, True):
        t = _mc({"none": 0.0}, reps=60, stochastic_vol=sv)
        assert abs(t[("none", "tick_rv")]["rel_bias"]) < 0.02
        assert abs(t[("none", "realized_kernel")]["rel_bias"]) < 0.03
        assert abs(t[("none", "preaveraged")]["rel_bias"]) < 0.06
        assert abs(t[("none", "sparse_rv")]["rel_bias"]) < 0.06


# --------------------------------------------------------------------------- req2
def test_req2_bid_ask_bounce_is_not_read_uncritically_as_economic_variance():
    xi2 = 1e-4
    omega = math.sqrt(xi2 * IV)
    excess, rk_rel, flags, clean_flags, qual = [], [], [], [], []
    for k in range(30):
        x, iv = m.simulate_efficient_path(N, IV, seed=100 + k)
        y = m.add_noise(x, omega, seed=900 + k, kind="roll")
        rv = m.realized_variance(np.diff(y))
        excess.append((rv - iv) / (2 * N * omega ** 2))
        out = m.noise_aware_variance(y, sparse_step=60)
        rk_rel.append(out["value"] / iv - 1.0)
        flags.append(out["noise_dominated"])
        assert out["raw_rv_includes_noise"] == pytest.approx(rv)
        qual.append(m.jump_decomposition(np.diff(y))["noise_qualified"])
        clean_flags.append(m.noise_aware_variance(x, sparse_step=60)["noise_dominated"])
    # Raw RV is inflated by the bounce by the theoretical 2*n*omega^2 ...
    assert 0.9 < float(np.mean(excess)) < 1.1
    # ... the noise-aware estimate stays on the economic target ...
    assert abs(float(np.mean(rk_rel))) < 0.08
    # ... and the bounce is flagged rather than silently counted.
    assert all(flags)
    assert all(qual)
    assert not any(clean_flags)


# --------------------------------------------------------------------------- req3
def test_req3_gaps_irregular_times_halts_and_overnight_have_declared_treatment():
    assert "no interpolation" in m.GAP_POLICY

    # Two sessions separated by an overnight gap, plus a mid-session halt.
    t = np.array([0, 1, 2, 3, 4, 20, 21, 22, 30, 31], dtype=float)
    p = np.log(np.array([100, 101, 100.5, 101.2, 101.0, 103.0, 102.5, 103.1, 99.0, 99.4]))
    dec = m.session_variance_decomposition(t, p, max_gap=5.0)
    assert dec["n_sessions"] == 3 and dec["n_gap_returns"] == 2
    s1 = np.diff(p[0:5])
    s2 = np.diff(p[5:8])
    s3 = np.diff(p[8:10])
    intra = float(np.sum(s1 ** 2) + np.sum(s2 ** 2) + np.sum(s3 ** 2))
    gaps = (p[5] - p[4]) ** 2 + (p[8] - p[7]) ** 2
    assert dec["intraday_variance"] == pytest.approx(intra, rel=1e-12)
    assert dec["overnight_variance"] == pytest.approx(gaps, rel=1e-12)
    assert dec["total_variance"] == pytest.approx(intra + gaps, rel=1e-12)
    # The gap returns never enter the intraday estimator.
    assert dec["intraday_variance"] < m.realized_variance(np.diff(p))

    # Irregular ticks: previous-tick sampling, no back-fill, stale points counted.
    ticks_t = np.array([2.5, 3.1, 7.9])
    ticks_p = np.array([1.0, 2.0, 3.0])
    s = m.previous_tick_sample(ticks_t, ticks_p, grid=np.arange(0.0, 10.0, 1.0))
    assert s["dropped_before_first_tick"] == 3
    assert list(s["log_prices"]) == [1.0, 2.0, 2.0, 2.0, 2.0, 3.0, 3.0]
    assert s["stale_returns"] == 4

    # Missing values are not silently filled: they must be declared as gaps.
    with pytest.raises(ValueError):
        m.realized_variance([0.01, float("nan")])
    with pytest.raises(ValueError):
        m.previous_tick_sample([2.0, 1.0], [0.0, 0.0], [3.0])

    # Labels report overnight variance separately from intraday variance.
    lab = m.build_versioned_label(t, t, p, 0.0, 31.0, asof=31.0, max_gap=5.0)
    assert lab["overnight_variance"] == pytest.approx(gaps, rel=1e-12)
    assert lab["fixed_interval_rv_intraday"] == pytest.approx(intra, rel=1e-12)
    assert lab["n_gap_returns"] == 2


# --------------------------------------------------------------------------- req4
def test_req4_bias_variance_measured_against_simple_controls_across_fixed_noise_regimes():
    t = _mc(m.NOISE_REGIMES, reps=40)
    regimes = set(m.NOISE_REGIMES)
    ests = {"tick_rv", "sparse_rv", "realized_kernel", "preaveraged"}
    assert {k[0] for k in t} == regimes and {k[1] for k in t} == ests
    for row in t.values():
        for f in ("rel_bias", "rel_sd", "rel_rmse"):
            assert math.isfinite(row[f])
        assert row["rel_rmse"] ** 2 == pytest.approx(
            row["rel_bias"] ** 2 + row["rel_sd"] ** 2 * (row["reps"] - 1) / row["reps"], rel=1e-6)
    # Simple control's bias tracks the 2*n*omega^2 theory.
    for reg in ("medium", "high"):
        row = t[(reg, "tick_rv")]
        assert row["rel_bias"] == pytest.approx(row["theory_rv_bias_rel"], rel=0.1)
    # Noise-aware estimator beats both simple controls once noise matters ...
    for reg in ("medium", "high"):
        assert t[(reg, "realized_kernel")]["rel_rmse"] < t[(reg, "tick_rv")]["rel_rmse"]
        assert t[(reg, "realized_kernel")]["rel_rmse"] < t[(reg, "sparse_rv")]["rel_rmse"]
    # ... but costs efficiency when there is no noise (honest trade-off).
    assert t[("none", "tick_rv")]["rel_rmse"] <= t[("none", "realized_kernel")]["rel_rmse"]


# --------------------------------------------------------------------------- req5
def test_req5_historical_corrected_tape_cannot_alter_earlier_forecast_inputs():
    rng = np.random.default_rng(5)
    n = 200
    et = np.arange(n, dtype=float)
    kt = et.copy()  # each print known when it happens
    p = np.cumsum(rng.standard_normal(n) * 1e-3)
    asof_1 = 250.0
    lab1 = m.build_versioned_label(et, kt, p, 0.0, 199.0, asof=asof_1, max_gap=5.0)

    # A correction of an in-window print arrives later (knowledge time 300).
    et2 = np.concatenate([et, [50.0]])
    kt2 = np.concatenate([kt, [300.0]])
    p2 = np.concatenate([p, [p[50] + 0.05]])
    again = m.build_versioned_label(et2, kt2, p2, 0.0, 199.0, asof=asof_1, max_gap=5.0)
    assert m.label_unchanged(lab1, again)
    assert again["version_id"] == lab1["version_id"]

    later = m.build_versioned_label(et2, kt2, p2, 0.0, 199.0, asof=300.0, max_gap=5.0)
    assert later["version_id"] != lab1["version_id"]
    assert later["fixed_interval_rv_intraday"] != lab1["fixed_interval_rv_intraday"]
    assert not m.label_unchanged(lab1, later)

    # The as-of tape keeps the latest revision known at the cutoff only.
    e, v = m.asof_tape(et2, kt2, p2, cutoff=asof_1)
    assert e.size == n and v[50] == p[50]
    e, v = m.asof_tape(et2, kt2, p2, cutoff=300.0)
    assert e.size == n and v[50] == p2[-1]

    # A label may not be built before its window has closed.
    with pytest.raises(ValueError):
        m.build_versioned_label(et, kt, p, 0.0, 199.0, asof=150.0, max_gap=5.0)


# --------------------------------------------------------------------------- req6
def test_req6_no_raw_capture_forecast_gate_or_accepted_label_is_silently_activated(monkeypatch):
    assert m.RESEARCH_ONLY is True
    assert m.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    assert set(m.ACTIVATION) >= {"raw_data_capture", "variance_forecast", "gate",
                                 "accepted_outcome_label"}
    assert not any(m.ACTIVATION.values())

    # Imported modules are limited to stdlib/numpy (no I/O, network or engine deps).
    mods = {v.__name__.split(".")[0] for v in vars(m).values() if isinstance(v, types.ModuleType)}
    assert mods <= {"hashlib", "json", "math", "numpy"}

    # No public symbol suggests registration, scheduling, publication or forecasting.
    banned = ("register", "schedule", "publish", "promote", "gate", "forecast", "fetch",
              "download", "write", "save", "upload", "activate")
    public = [k for k, v in vars(m).items() if callable(v) and not k.startswith("_")
              and getattr(v, "__module__", "") == m.__name__]
    assert public
    assert not [k for k in public if any(b in k.lower() for b in banned)]

    # Labels are research-only, never accepted, never a forecast.
    t = np.arange(10, dtype=float)
    lab = m.build_versioned_label(t, t, np.linspace(0, 0.01, 10), 0.0, 9.0, asof=9.0, max_gap=2.0)
    assert lab["research_only"] is True and lab["accepted_label"] is False
    assert lab["is_forecast"] is False

    # Import performs no file I/O.
    def _no_open(*a, **k):
        raise AssertionError("module opened a file at import")

    monkeypatch.setattr(builtins, "open", _no_open)
    importlib.reload(m)
    assert m.RESEARCH_ONLY is True
