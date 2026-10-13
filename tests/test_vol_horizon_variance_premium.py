from __future__ import annotations

__doc__ = """Hermetic tests for engine/vol_horizon_variance_premium.py (brief Q14).

Each test is named after the acceptance requirement it proves (req1..req6). Synthetic
inputs only: integer day offsets, seeded random numbers, no repo data, no network,
no wall clock.
"""

import importlib
import math
import types

import numpy as np
import pytest

import engine.vol_horizon_variance_premium as vp


def _basis(h: int = 30, day_count: str = "calendar365", session: str = "S") -> vp.HorizonBasis:
    return vp.HorizonBasis(horizon_calendar_days=h, day_count=day_count, session_close=session)


def _phys(value: float = 0.004, basis: vp.HorizonBasis | None = None, kind: str = "forecast",
          asof: int = 100, info: int = 100) -> vp.PhysicalLeg:
    return vp.PhysicalLeg(value, basis or _basis(), kind, asof, info,
                          vp.realized_coverage("close_to_close"), method="synthetic")


def _bs_price(s: float, k: float, t: float, r: float, sig: float, call: bool) -> float:
    def n(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    f = s * math.exp(r * t)
    d1 = (math.log(f / k) + 0.5 * sig * sig * t) / (sig * math.sqrt(t))
    d2 = d1 - sig * math.sqrt(t)
    df = math.exp(-r * t)
    if call:
        return df * (f * n(d1) - k * n(d2))
    return df * (k * n(-d2) - f * n(-d1))


def _chain(sig: float, t: float, r: float = 0.02, lo: float = 0.3, hi: float = 2.5,
           step: float = 0.005, zero_below: float | None = None):
    s = 100.0
    f = s * math.exp(r * t)
    ks = np.round(np.arange(lo * s, hi * s + 1e-9, step * s), 6)
    c = np.array([_bs_price(s, k, t, r, sig, True) for k in ks])
    p = np.array([_bs_price(s, k, t, r, sig, False) for k in ks])
    pb = p.copy()
    if zero_below is not None:
        pb[ks < zero_below] = 0.0
    return ks, c, c, pb, p, f


# ───────────────────────────── req1: shared basis ─────────────────────────────

def test_req1_vol_index_converts_to_calendar_horizon_variance_not_vol_points():
    v = vp.vol_index_to_horizon_variance(20.0, 30, 365.0)
    assert v == pytest.approx(0.04 * 30.0 / 365.0)
    back = vp.horizon_variance_to_annualized_vol(v, 30, 365.0)
    assert back == pytest.approx(0.20)
    # math witness: IV 0.30 vs forecast 0.20 is a 0.05 annual-variance premium, not 0.10
    rec = vp.build_premium(vp.atm_proxy_leg(0.30, _basis(), 100),
                           _phys(0.20 ** 2 * 30 / 365.0))
    view = rec.annualized_vol_view()
    assert view["premium_variance_ann"] == pytest.approx(0.05)
    assert view["implied_vol_ann"] - view["physical_vol_ann"] == pytest.approx(0.10)


def test_req1_daily_variance_scales_by_expected_trading_days_in_horizon():
    assert vp.daily_variance_to_horizon_variance(1e-4, 30, 252.0) == pytest.approx(1e-4 * 252 * 30 / 365)


def test_req1_trading252_basis_is_expected_trading_days_and_consistent_with_calendar365():
    # audit M4: trading252 measures the horizon in expected trading days 252*h/365, so the
    # year fraction, the ATM-proxy horizon variance and the annualized view agree with calendar365
    cal, trd = _basis(30, "calendar365"), _basis(30, "trading252")
    assert cal.basis_days == pytest.approx(30.0)
    assert trd.basis_days == pytest.approx(252.0 * 30.0 / 365.0)
    assert trd.year_fraction == pytest.approx(cal.year_fraction) == pytest.approx(30.0 / 365.0)
    v_cal = vp.atm_proxy_leg(0.25, cal, 7).value
    v_trd = vp.atm_proxy_leg(0.25, trd, 7).value
    assert v_trd == pytest.approx(v_cal) == pytest.approx(0.0625 * 30.0 / 365.0)
    daily = 0.25 ** 2 / 252.0
    assert vp.daily_variance_to_horizon_variance(daily, 30, 252.0) == pytest.approx(v_trd)
    rec = vp.build_premium(vp.atm_proxy_leg(0.30, trd, 9),
                           _phys(0.20 ** 2 * 30 / 365.0, basis=trd, asof=9, info=9))
    view = rec.annualized_vol_view()
    assert view["implied_vol_ann"] == pytest.approx(0.30)
    assert view["physical_vol_ann"] == pytest.approx(0.20)
    assert view["premium_variance_ann"] == pytest.approx(0.05)
    with pytest.raises(ValueError, match="day_count"):
        vp.basis_days(30, "act360")


def test_req1_premium_refuses_mismatched_horizon_daycount_session_or_asof():
    imp = vp.atm_proxy_leg(0.2, _basis(30), 100)
    with pytest.raises(ValueError, match="horizon"):
        vp.build_premium(imp, _phys(basis=_basis(21)))
    with pytest.raises(ValueError, match="day-count"):
        vp.build_premium(imp, _phys(basis=_basis(30, "trading252")))
    with pytest.raises(ValueError, match="as-of"):
        vp.build_premium(imp, _phys(asof=101, info=101))
    other_session = _basis(30, session="T")
    with pytest.raises(ValueError, match="session"):
        vp.build_premium(imp, _phys(basis=other_session))
    rec = vp.build_premium(imp, _phys(basis=other_session), acknowledge_session_offset=True)
    assert "acknowledged" in rec.session_note
    assert rec.units == "horizon_variance" and rec.horizon_calendar_days == 30


def test_req1_basis_rejects_non_variance_units_and_unbounded_horizon():
    with pytest.raises(ValueError):
        vp.HorizonBasis(horizon_calendar_days=30, units="vol_points")
    with pytest.raises(ValueError):
        vp.HorizonBasis(horizon_calendar_days=0)
    with pytest.raises(ValueError):
        vp.HorizonBasis(horizon_calendar_days=99999)


# ───────────────────────────── req2: no label leakage ─────────────────────────────

def test_req2_forward_label_cannot_enter_ex_ante_premium():
    imp = vp.atm_proxy_leg(0.2, _basis(), 100)
    label = _phys(kind="forward_label", info=130)
    with pytest.raises(ValueError, match="req2"):
        vp.build_premium(imp, label)
    with pytest.raises(ValueError, match="req2"):
        vp.build_premium(imp, _phys(info=101))
    post = vp.ex_post_premium(imp, label)
    assert post.timing == "ex_post" and post.physical_kind == "forward_label"
    with pytest.raises(ValueError):
        vp.ex_post_premium(imp, _phys())


def test_req2_forward_label_uses_only_returns_after_asof_and_trailing_only_before():
    rng = np.random.default_rng(1)
    n = 400
    day = np.cumsum(rng.choice([1, 1, 1, 1, 3], size=n)).astype(np.int64)
    r = rng.normal(0, 0.01, n)
    r[0] = np.nan
    fwd = vp.forward_realized_variance(r, day, 30)
    trl = vp.trailing_realized_variance(r, day, 30)
    t = 200
    r_past = r.copy()
    r_past[: t + 1] = rng.normal(0, 0.05, t + 1)
    assert vp.forward_realized_variance(r_past, day, 30)[t] == pytest.approx(fwd[t])
    r_fut = r.copy()
    r_fut[t + 1:] = rng.normal(0, 0.05, n - t - 1)
    assert vp.trailing_realized_variance(r_fut, day, 30)[t] == pytest.approx(trl[t])
    window = (day > day[t]) & (day <= day[t] + 30)
    assert fwd[t] == pytest.approx(float(np.sum(r[window] ** 2)))
    # incomplete label windows are NaN, never truncated sums
    assert np.all(np.isnan(fwd[day + 30 > day[-1]]))
    assert np.all(np.isnan(trl[day - 30 < day[0]]))


def test_req2_missing_return_inside_window_voids_both_legs():
    day = np.arange(100, dtype=np.int64)
    r = np.full(100, 0.01)
    r[0] = np.nan
    r[50] = np.nan
    assert np.isnan(vp.forward_realized_variance(r, day, 10)[45])
    assert np.isnan(vp.trailing_realized_variance(r, day, 10)[55])
    assert vp.forward_realized_variance(r, day, 10)[60] == pytest.approx(10 * 1e-4)


# ───────────────────────────── req3: explicit coverage ─────────────────────────────

def test_req3_overnight_coverage_is_explicit_for_each_sampling():
    assert vp.realized_coverage("close_to_close")["overnight"] == "included"
    assert vp.realized_coverage("open_to_close")["overnight"] == "excluded"
    with pytest.raises(ValueError):
        vp.realized_coverage("tick")
    with pytest.raises(ValueError, match="req3"):
        vp.PhysicalLeg(0.004, _basis(), "forecast", 1, 1, {"sampling": "close_to_close"})
    with pytest.raises(ValueError, match="req3"):
        vp.ImpliedLeg(0.004, _basis(), "strip", 1, {"tail_strikes": "unknown_unstated", "overnight": "x"})
    with pytest.raises(ValueError, match="req3"):
        vp.ImpliedLeg(0.004, _basis(), "strip", 1, None)  # type: ignore[arg-type]


def test_req3_tail_strike_truncation_is_flagged_and_biases_strip_down():
    t = 30 / 365.0
    fk, fcb, fca, fpb, fpa, ff = _chain(0.25, t, lo=0.6, hi=1.6)
    full = vp.strip_variance(fk, fcb, fca, fpb, fpa, ff, 0.02, t)
    ks, cb, ca, pb, pa, f = _chain(0.25, t, lo=0.6, hi=1.6, zero_below=80.0)
    cut = vp.strip_variance(ks, cb, ca, pb, pa, f, 0.02, t)
    assert not full.put_wing_stopped_by_zero_bids
    assert cut.put_wing_stopped_by_zero_bids
    assert cut.variance_annual < full.variance_annual
    assert cut.k_low_over_forward > full.k_low_over_forward
    leg = vp.strip_leg(cut, _basis(30), 5)
    assert leg.coverage["tail_strikes"] == "strip_truncated"
    assert leg.coverage["jump_correction"] == "none"
    proxy = vp.atm_proxy_leg(0.25, _basis(30), 5)
    assert proxy.coverage["tail_strikes"] == "single_strike_none"


# ───────────────────────────── req4: no silent mixing ─────────────────────────────

def test_req4_strip_recovers_flat_vol_and_is_labelled_strip_not_proxy():
    t = 30 / 365.0
    ks, cb, ca, pb, pa, f = _chain(0.20, t)
    res = vp.strip_variance(ks, cb, ca, pb, pa, f, 0.02, t)
    assert res.measure_kind == "strip"
    assert res.variance_annual == pytest.approx(0.04, rel=0.01)
    assert res.variance_horizon == pytest.approx(0.04 * t, rel=0.01)
    with pytest.raises(ValueError, match="maturity"):
        vp.strip_leg(res, _basis(45), 1)


def test_req4_history_refuses_mixed_strip_and_proxy_unless_segmented():
    b = _basis()
    t = 30 / 365.0
    ks, cb, ca, pb, pa, f = _chain(0.20, t)
    strip = vp.strip_leg(vp.strip_variance(ks, cb, ca, pb, pa, f, 0.02, t), b, 1)
    r1 = vp.build_premium(strip, _phys(asof=1, info=1))
    r2 = vp.build_premium(vp.atm_proxy_leg(0.2, b, 2), _phys(asof=2, info=2))
    with pytest.raises(ValueError, match="req4"):
        vp.assemble_history([r2, r1])
    seg = vp.assemble_history([r2, r1], segment_by_kind=True)
    assert set(seg) == {"strip", "atm_proxy"} and len(seg["strip"]) == 1
    assert vp.assemble_history([r2]) == [r2]
    other = vp.build_premium(vp.atm_proxy_leg(0.2, _basis(21), 3), _phys(basis=_basis(21), asof=3, info=3))
    with pytest.raises(ValueError, match="horizon"):
        vp.assemble_history([r2, other], segment_by_kind=True)
    post = vp.ex_post_premium(vp.atm_proxy_leg(0.2, b, 4), _phys(kind="forward_label", asof=4, info=40))
    with pytest.raises(ValueError, match="timing"):
        vp.assemble_history([r2, post])


# ───────────────────────────── req5: dependence-aware incremental test ─────────────────────────────

def _ar1(n: int, phi: float, rng: np.random.Generator) -> np.ndarray:
    e = rng.normal(size=n)
    x = np.empty(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def test_req5_informative_extra_leg_is_kept_and_noise_leg_is_rejected():
    rng = np.random.default_rng(7)
    n = 3000
    iv = _ar1(n, 0.95, rng)
    z = _ar1(n, 0.9, rng)
    y = 1.0 + 0.5 * iv + 0.8 * z + rng.normal(size=n) * 0.5
    noise = rng.normal(size=n)
    xc = np.column_stack([iv])
    tr, te = slice(0, 2000), slice(2000, n)
    kw = dict(block=60, n_boot=400, seed=3, hac_lags=40, practical_bar=0.05)
    good = vp.incremental_comparison(y[tr], xc[tr], np.column_stack([iv, z])[tr],
                                     y[te], xc[te], np.column_stack([iv, z])[te], **kw)
    assert good["keep_predictive_upgrade"] is True
    assert good["loss_diff_bootstrap"]["lo"] > 0
    bad = vp.incremental_comparison(y[tr], xc[tr], np.column_stack([iv, noise])[tr],
                                    y[te], xc[te], np.column_stack([iv, noise])[te], **kw)
    assert bad["keep_predictive_upgrade"] is False
    assert bad["authority"] == "none"


def test_req5_coefficients_are_fit_on_training_rows_only():
    rng = np.random.default_rng(11)
    n = 600
    x = rng.normal(size=(n, 2))
    y = x @ np.array([1.0, -0.5]) + rng.normal(size=n)
    kw = dict(block=20, n_boot=200, seed=1, hac_lags=10, practical_bar=0.05)
    a = vp.incremental_comparison(y[:400], x[:400, :1], x[:400], y[400:], x[400:, :1], x[400:], **kw)
    y2 = y.copy()
    y2[400:] = rng.normal(size=200) * 100
    b = vp.incremental_comparison(y2[:400], x[:400, :1], x[:400], y2[400:], x[400:, :1], x[400:], **kw)
    assert a["beta_augmented"] == pytest.approx(b["beta_augmented"])
    assert a["beta_controls"] == pytest.approx(b["beta_controls"])


def test_req5_block_bootstrap_and_hac_widen_under_serial_dependence():
    rng = np.random.default_rng(5)
    d = _ar1(4000, 0.9, rng) * 0.1
    iid_se = d.std() / math.sqrt(d.size)
    hac = vp.newey_west_mean(d, 60)
    assert hac["se"] > 2.0 * iid_se
    boot = vp.moving_block_bootstrap_mean(d, 100, 500, 2)
    assert (boot["hi"] - boot["lo"]) > 2.0 * 1.96 * iid_se
    assert boot["lo"] <= boot["mean"] <= boot["hi"]
    with pytest.raises(ValueError):
        vp.moving_block_bootstrap_mean(d, 0, 500, 2)


def test_req5_qlike_is_zero_at_the_truth_and_positive_elsewhere():
    y = np.array([0.01, 0.02, 0.03])
    assert np.allclose(vp.qlike(y, y), 0.0)
    assert np.all(vp.qlike(y, y * 1.5) > 0) and np.all(vp.qlike(y, y * 0.5) > 0)


# ───────────────────────────── req6: no authority ─────────────────────────────

def test_req6_records_carry_no_profit_probability_trade_or_short_vol_authority():
    rec = vp.build_premium(vp.atm_proxy_leg(0.2, _basis(), 1), _phys(asof=1, info=1))
    out = rec.to_dict()
    assert out["authority"] == "none"
    assert not (set(map(str.lower, out)) & vp.FORBIDDEN_OUTPUT_KEYS)
    for bad in ({"expected_profit": 1.0}, {"x": [{"win_probability": 0.6}]},
                {"short_vol": True}, {"authority": "trade"}, {"trade_signal": "sell"}):
        with pytest.raises(ValueError, match="req6"):
            vp.assert_no_authority(bad)
    public = {n for n in dir(vp) if not n.startswith("_")}
    for word in ("signal", "trade", "position", "size", "sell", "rank"):
        assert not any(word in n.lower() for n in public if callable(getattr(vp, n)))


# ───────────────────────────── no silent activation ─────────────────────────────

def test_no_silent_activation_module_contract():
    mod = importlib.reload(vp)
    assert mod.RESEARCH_ONLY is True
    assert mod.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    assert "VERDICT" in mod.__doc__
    imported = {v.__name__ for v in vars(mod).values() if isinstance(v, types.ModuleType)}
    assert imported <= {"math", "numpy"}
    for name in ("register", "REGISTRY", "schedule", "main", "run", "activate", "publish"):
        assert not hasattr(mod, name)
    assert mod.AUTHORITY == "none"
