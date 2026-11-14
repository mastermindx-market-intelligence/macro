"""Stress-conditioned factor covariance (WRI W1).

The math that must hold: (1) the orthogonalization transform can be FIT on one window
and APPLIED to another, reproducing the in-window orthogonalization exactly and keeping
extended data in the SAME orthogonal basis (so the client's b'·F_stress·b never mixes
bases); (2) a stress covariance estimated on worst-quartile market days captures
tail-only co-movement that calm-day covariance misses; (3) the emit is strictly additive
— every pre-existing key survives, the new keys are well-formed and symmetric, n_stress
is consistent with the quantile; (4) a scrap sample emits stress_meta.available=False and
no covariance rather than shipping noise. Pure-math on synthetic data; the real export is
smoke-checked opportunistically. (engine/factor_exposure.py::factor_cov_stress.)
"""
from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import factor_exposure as fe


def _idx(n: int):
    return pd.date_range("2016-01-01", periods=n, freq="B")


# --------------------------------------------------------------------------- #
# 1. synthetic positive control — down-day-only co-movement
# --------------------------------------------------------------------------- #
def test_stress_offdiag_exceeds_calm_when_comovement_is_tail_only():
    """Two factors uncorrelated on normal days but strongly co-moving on down-market
    days: the stress-window covariance off-diagonal must dwarf the calm off-diagonal.

    Construction: `mkt` is the market. On down-market days (mkt<0) `oil` and `btc` both
    pick up a large SHARED shock of FIXED variance (gated on down days, uncorrelated with
    the size of the market move so it does not leak into the mkt column); on up days they
    are independent noise. The transform is fit on the calm-ish trailing 252 window where
    oil/btc barely co-move, so oil's peel of btc is ~0 and the tail co-movement survives
    into the orthogonal residuals — visible only when the covariance is conditioned on the
    worst quartile of market days. (btc follows oil in FACTOR_ORDER, so this is also the
    honest test that a tail-only shared component is NOT removed by the calm-fit peel.)"""
    rng = np.random.default_rng(11)
    n = 900
    m = rng.normal(0, 0.011, n)
    down = m < 0
    shock = rng.normal(0, 0.02, n)                        # fixed-variance shared tail shock
    common = np.where(down, shock, 0.0)                   # present ONLY on down days
    oil = common + rng.normal(0, 0.004, n)
    btc = common + rng.normal(0, 0.004, n)
    F = pd.DataFrame({"mkt": m, "oil": oil, "btc": btc}, index=_idx(n))

    calm = fe.factor_cov(F, window=n)                     # covariance on ALL days (annualized)
    stress = fe.factor_cov_stress(F, fit_window=252, stress_window=756,
                                  quantile=0.25, min_stress_rows=400, min_stress_days=60)
    assert stress["available"] is True
    assert stress["n_stress"] == 189                      # 25% of 756 (masterplan anchor)
    scov = stress["cov"]

    calm_ob = abs(float(calm.loc["oil", "btc"]))
    stress_ob = float(scov.loc["oil", "btc"])
    # tail-only co-movement, the core product claim:
    #  (a) a materially POSITIVE stress off-diagonal...
    assert stress_ob > 0.002
    #  (b) ...an order of magnitude above the near-zero calm off-diagonal (the whole
    #      point: co-movement measured on all days evaporates vs the worst days)...
    assert stress_ob > 10.0 * calm_ob
    #  (c) ...landing on the oil/btc pair, not smeared into the (peeled-out) market column.
    assert stress_ob > 3.0 * abs(float(scov.loc["mkt", "oil"]))


def test_stress_and_calm_agree_when_no_tail_comovement():
    """Negative control: with NO regime-dependent co-movement (oil/btc independent on all
    days), BOTH the calm and stress oil/btc off-diagonals sit near zero — the stress lens
    invents nothing when there is no tail structure to find."""
    rng = np.random.default_rng(12)
    n = 900
    m = rng.normal(0, 0.011, n)
    F = pd.DataFrame({"mkt": m,
                      "oil": rng.normal(0, 0.012, n),      # independent of btc, all regimes
                      "btc": rng.normal(0, 0.02, n)}, index=_idx(n))
    calm = fe.factor_cov(F, window=n)
    stress = fe.factor_cov_stress(F, fit_window=252, stress_window=756, quantile=0.25)
    scov = stress["cov"]
    calm_corr = abs(float(calm.loc["oil", "btc"])) / np.sqrt(
        float(calm.loc["oil", "oil"]) * float(calm.loc["btc", "btc"]))
    stress_corr = abs(float(scov.loc["oil", "btc"])) / np.sqrt(
        float(scov.loc["oil", "oil"]) * float(scov.loc["btc", "btc"]))
    assert calm_corr < 0.15 and stress_corr < 0.25        # both ~uncorrelated, no blow-up


# --------------------------------------------------------------------------- #
# 2. basis consistency — fit on a window, apply to extended data
# --------------------------------------------------------------------------- #
def test_fit_apply_reproduces_in_window_orthogonalization_exactly():
    """orthogonalize_apply(F, fit(F)) == orthogonalize_factors(F) to machine precision,
    and applying a window-fit transform to an EXTENDED frame reproduces the in-window
    orthogonalization on the overlap — the invariant that keeps the stress cov in the
    shipped-betas basis."""
    rng = np.random.default_rng(13)
    n = 800
    m = rng.normal(0, 0.01, n)
    F = pd.DataFrame({
        "mkt": m,
        "growth": 0.9 * m + rng.normal(0, 0.003, n),
        "size": 0.7 * m + rng.normal(0, 0.004, n),
        "oil": rng.normal(0, 0.012, n),
    }, index=_idx(n))

    # (a) fit+apply on the SAME frame is byte-identical to the convenience wrapper
    direct = fe.orthogonalize_factors(F)
    applied = fe.orthogonalize_apply(F, fe.orthogonalize_fit(F))
    assert float((direct - applied).abs().to_numpy().max()) < 1e-12

    # (b) fit on trailing 252, apply to trailing 756: the last-252 overlap reproduces the
    #     in-window orthogonalization EXACTLY (same fixed transform, not a re-fit)
    win, sw = 252, 756
    transform = fe.orthogonalize_fit(F.tail(win))
    g_ext = fe.orthogonalize_apply(F.tail(sw), transform)
    g_in = fe.orthogonalize_factors(F.tail(win))
    assert float((g_ext.tail(win) - g_in).abs().to_numpy().max()) < 1e-12

    # (c) in-window columns are pairwise orthogonal
    c = g_in.corr().abs().to_numpy().copy()
    np.fill_diagonal(c, 0.0)
    assert float(c.max()) < 1e-9

    # (d) re-fitting on the 756 window gives a DIFFERENT basis (the trap the design avoids)
    refit = fe.orthogonalize_apply(F.tail(sw), fe.orthogonalize_fit(F.tail(sw)))
    assert float((refit.tail(win) - g_in).abs().to_numpy().max()) > 1e-6


def test_fit_returns_sequential_coefficients_in_factor_order():
    """The fitted transform exposes coeffs per FACTOR_ORDER: mkt (first) has no priors;
    each later factor carries a slope against every already-orthogonalized prior."""
    rng = np.random.default_rng(14)
    n = 400
    m = rng.normal(0, 0.01, n)
    F = pd.DataFrame({"mkt": m, "growth": 0.8 * m + rng.normal(0, 0.003, n),
                      "size": 0.5 * m + rng.normal(0, 0.004, n)}, index=_idx(n))
    tr = fe.orthogonalize_fit(F)
    assert tr["order"] == ["mkt", "growth", "size"]
    assert tr["coeffs"]["mkt"] == {}                      # market stays raw
    assert set(tr["coeffs"]["growth"]) == {"mkt"}
    assert set(tr["coeffs"]["size"]) == {"mkt", "growth"}
    # growth's fitted slope on mkt recovers the ~0.8 loading
    assert abs(tr["coeffs"]["growth"]["mkt"] - 0.8) < 0.1


# --------------------------------------------------------------------------- #
# 3. stress-day selection consistency
# --------------------------------------------------------------------------- #
def test_stress_days_match_raw_mkt_quantile():
    """n_stress and mkt_cut_daily are consistent with the raw-mkt quantile over the
    stress window: the cut equals the empirical quantile and n_stress equals the count
    at-or-below it (≈ quantile × window)."""
    rng = np.random.default_rng(15)
    n = 900
    F = pd.DataFrame({"mkt": rng.normal(0, 0.011, n),
                      "oil": rng.normal(0, 0.012, n),
                      "btc": rng.normal(0, 0.02, n)}, index=_idx(n))
    sw, q = 756, 0.25
    stress = fe.factor_cov_stress(F, fit_window=252, stress_window=sw, quantile=q)
    mkt_win = F["mkt"].tail(sw)
    assert stress["window_d"] == sw
    assert abs(stress["mkt_cut_daily"] - round(float(mkt_win.quantile(q)), 5)) < 1e-9
    assert stress["n_stress"] == int((mkt_win <= float(mkt_win.quantile(q))).sum())
    # roughly a quarter of the window
    assert 0.20 * sw <= stress["n_stress"] <= 0.30 * sw


# --------------------------------------------------------------------------- #
# 4. schema / backward-compat on the real export
# --------------------------------------------------------------------------- #
def test_compute_exposure_schema_strictly_additive():
    """The stress emit is strictly additive: every pre-existing key is still present and
    unchanged in shape, the new keys are well-formed, the stress matrix is symmetric and
    shares the factor_cov key order, and stress_meta is consistent with the quantile."""
    out = fe.compute_exposure()
    if out is None:                                       # no store in this env — skip
        return
    # (a) every pre-existing top-level key survives
    for k in ("as_of", "window_d", "n", "note", "factors", "factor_vol_ann",
              "factor_cov", "betas", "most_idiosyncratic"):
        assert k in out, f"pre-existing key {k!r} dropped"
    # (b) stress_meta ALWAYS present (available true/false)
    assert "stress_meta" in out and "available" in out["stress_meta"]

    if not out["stress_meta"]["available"]:               # guard path in this env
        assert "factor_cov_stress" not in out and "factor_vol_stress_ann" not in out
        assert "reason" in out["stress_meta"]
        return

    keys = list(out["factor_cov"].keys())
    scov = out["factor_cov_stress"]
    svol = out["factor_vol_stress_ann"]
    meta = out["stress_meta"]

    # (c) stress cov shares the factor_cov key set / order and is square + symmetric
    assert list(scov.keys()) == keys
    for a in keys:
        assert list(scov[a].keys()) == keys
        for b in keys:
            assert abs(scov[a][b] - scov[b][a]) < 1e-9
    # (d) stress vols are the sqrt of the stress-cov diagonal (rounding-tolerant)
    for k in keys:
        assert abs(svol[k] - round(float(np.sqrt(max(scov[k][k], 0.0))), 4)) < 5e-4
    # (e) meta is self-consistent
    assert meta["quantile"] == 0.25
    assert isinstance(meta["n_stress"], int) and meta["n_stress"] >= 60
    assert meta["n_stress"] <= meta["window_d"]
    assert "worst-quartile" in meta["note"] and "idiosyncratic" in meta["note"]
    # n_stress must be ~a quarter of the actual window (quantile selection)
    assert 0.15 * meta["window_d"] <= meta["n_stress"] <= 0.35 * meta["window_d"]


# --------------------------------------------------------------------------- #
# 5. small-sample guard
# --------------------------------------------------------------------------- #
def test_guard_abstains_on_tiny_history():
    """A stress window with too few rows / stress days emits stress_meta.available=False
    and NO covariance — never a matrix fit on a scrap sample."""
    rng = np.random.default_rng(16)
    n = 120                                               # far below any usable window
    F = pd.DataFrame({"mkt": rng.normal(0, 0.011, n),
                      "oil": rng.normal(0, 0.012, n)}, index=_idx(n))
    stress = fe.factor_cov_stress(F, fit_window=252, stress_window=756,
                                  quantile=0.25, min_stress_rows=400, min_stress_days=60)
    assert stress["available"] is False
    assert "cov" not in stress
    assert stress["window_d"] == n                        # window shrunk to what exists
    assert "reason" in stress


def test_guard_fires_when_stress_days_below_floor():
    """Enough rows but the stress-day floor is not met → abstain (no cov)."""
    rng = np.random.default_rng(17)
    n = 500
    F = pd.DataFrame({"mkt": rng.normal(0, 0.011, n),
                      "oil": rng.normal(0, 0.012, n)}, index=_idx(n))
    # quantile 0.25 of 500 rows ≈ 125 stress days, so force the floor high to trip it
    stress = fe.factor_cov_stress(F, fit_window=252, stress_window=500,
                                  quantile=0.25, min_stress_rows=400, min_stress_days=200)
    assert stress["available"] is False and "cov" not in stress


def test_guard_path_through_compute_exposure_synthetic(monkeypatch):
    """End-to-end guard: a tiny synthetic factor frame drives compute_exposure() to emit
    stress_meta.available=False with no stress-cov key, while the pre-existing keys still
    ship. Patches factor_frame + the close matrix so the whole export runs on ~130 rows."""
    rng = np.random.default_rng(18)
    n = 130
    idx = _idx(n)
    F = pd.DataFrame({"mkt": rng.normal(0, 0.011, n),
                      "growth": rng.normal(0, 0.01, n),
                      "oil": rng.normal(0, 0.012, n)}, index=idx)
    # a small close matrix aligned to F so stock_betas has enough obs at min_obs floor
    px = pd.DataFrame({f"S{i}": (1 + rng.normal(0, 0.02, n)).cumprod() for i in range(6)},
                      index=idx)

    monkeypatch.setattr(fe, "factor_frame", lambda asof=None: F)
    monkeypatch.setattr(fe, "_closes", lambda: px)
    monkeypatch.setattr(fe, "_etf_panels", lambda: (pd.DataFrame(), pd.DataFrame()))
    monkeypatch.setattr(fe, "_names_sectors", lambda: {})
    # loosen the min-obs floors so betas estimate on the short synthetic window
    monkeypatch.setattr(fe, "_cfg", lambda: {
        "window_d": 120, "min_obs": 100, "min_factor_obs": 120, "max_abs_beta": 5.0,
        "top_n_idio": 3, "stress_window_d": 756, "stress_quantile": 0.25})

    out = fe.compute_exposure()
    assert out is not None
    assert out["stress_meta"]["available"] is False
    assert "factor_cov_stress" not in out and "factor_vol_stress_ann" not in out
    # pre-existing contract intact even on the guard path
    for k in ("factor_cov", "factor_vol_ann", "betas", "factors"):
        assert k in out


def test_issue11016_stock_and_covariance_share_factor_window_without_price_dates():
    rng = np.random.default_rng(11024)
    idx = _idx(650)
    m = rng.normal(0, 0.01, len(idx))
    factors = pd.DataFrame({"mkt": m, "growth": np.linspace(-1, 1, len(idx)) * m
                            + rng.normal(0, 0.005, len(idx))}, index=idx)
    closes = pd.DataFrame({"A": 100 * (1 + 0.8*m + 0.3*factors.growth).cumprod()},
                          index=idx).drop(idx[-60::3])
    window = factors.tail(252)
    basis = fe.orthogonalize_factors(window)
    returns = closes.pct_change(fill_method=None).reindex(window.index)
    mask = np.isfinite(returns.A)
    design = np.column_stack([np.ones(mask.sum()), basis.loc[mask].to_numpy()])
    coef = np.linalg.lstsq(design, returns.loc[mask, "A"], rcond=None)[0]
    rec = fe.stock_betas(closes, factors, window=252, min_obs=126,
                         max_abs=5.0)["betas"]["A"]
    assert [rec["mkt"], rec["growth"]] == [round(float(x), 3) for x in coef[1:]]
    pd.testing.assert_frame_equal(fe.factor_cov(factors, window=252), basis.cov()*252)
    stress = fe.factor_cov_stress(factors, fit_window=252, stress_window=600, quantile=.25)
    history = factors.tail(600)
    fixed = fe.orthogonalize_apply(history, fe.orthogonalize_fit(window))
    stress_days = history.mkt <= history.mkt.quantile(.25)
    pd.testing.assert_frame_equal(stress["cov"], fixed.loc[stress_days].cov()*252)


def test_issue11016_covariance_uses_same_finite_factor_rows():
    rng = np.random.default_rng(11025)
    factors = pd.DataFrame({"mkt": rng.normal(0, .01, 700),
                            "growth": rng.normal(0, .005, 700)}, index=_idx(700))
    factors.iloc[-10, 0] = np.inf
    factors.iloc[-20, 1] = np.nan
    clean = factors.replace([np.inf, -np.inf], np.nan).dropna()
    pd.testing.assert_frame_equal(fe.factor_cov(factors, window=252),
                                   fe.factor_cov(clean, window=252))
    a = fe.factor_cov_stress(factors, fit_window=252, stress_window=600, quantile=.25)
    b = fe.factor_cov_stress(clean, fit_window=252, stress_window=600, quantile=.25)
    assert a["available"] and a["n_stress"] == b["n_stress"]
    pd.testing.assert_frame_equal(a["cov"], b["cov"])


def _issue11016_native_consumers(data, weights):
    """Execute complete shipped programs; only external DOM/fetch seams are supplied."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not on PATH: native FactorExposure/RiskCore proof unavailable")
    script = r"""
const fs = require('fs');
const path = require('path');
const root = process.argv[1];
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
process.on('unhandledRejection', error => { console.error(error); process.exit(1); });
const RiskCore = require(path.join(root, 'templates/risk_core.js'));
let language = 'en';
const panel = {style: {display: ''}, innerHTML: ''};
const events = [];
global.window = global;
global.WS = {prov: () => ({gen: 3})};
global.document = {
  documentElement: {getAttribute: k => k === 'data-lang' ? language
    : k === 'data-ws-mode' ? 'portfolio' : null},
  getElementById: id => id === 'fx_panel' ? panel : null,
  addEventListener: () => {},
  dispatchEvent: e => events.push(e.detail)
};
global.CustomEvent = function(type, init) {this.type = type; this.detail = init.detail;};
global.localStorage = {getItem: () => null, setItem: () => {}};
global.fetch = async url => {
  if (url !== 'factor_betas.json') throw Error('unexpected fetch ' + url);
  return {ok: true, json: async () => payload.data};
};
require(path.join(root, 'templates/factor_exposure.js'));
const flush = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  const read = RiskCore.read(payload.data, payload.weights);
  FX.setAutoWeights(payload.weights); await flush();
  const en = panel.innerHTML;
  const populated = FX.currentWeights();
  language = 'zh'; FX.refresh(); await flush();
  const zh = panel.innerHTML;
  const first = Object.keys(payload.weights)[0];
  FX.setAutoWeights({[first]: 1}); await flush();
  const thin = {display: panel.style.display, html: panel.innerHTML,
    weights: FX.currentWeights(), risk: RiskCore.book(payload.data, {[first]: 1}, 'calm')};
  FX.setAutoWeights({}); await flush();
  const empty = {display: panel.style.display, html: panel.innerHTML,
    weights: FX.currentWeights()};
  process.stdout.write(JSON.stringify({read, en, zh, populated, thin, empty, events}));
})().catch(error => {console.error(error); process.exit(1);});
"""
    result = subprocess.run([node, "-e", script, str(Path(__file__).resolve().parents[1])],
                            input=json.dumps({"data": data, "weights": weights}, allow_nan=False),
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("days,gaps", [(700, False), (700, True), (1000, True)])
def test_issue11016_real_export_and_native_consumers_preserve_market_identity(monkeypatch, days, gaps):
    rng = np.random.default_rng(11026)
    idx = _idx(days)
    spy = pd.DataFrame({"close": 100*(1+rng.normal(.0002, .01, days)).cumprod()}, index=idx)
    tlt = pd.DataFrame({"close": 100.0}, index=idx)
    if gaps:
        tlt.iloc[::4] = np.nan
    prices = {"SPY": spy, "TLT": tlt}
    monkeypatch.setattr(fe.store, "read", lambda group, sid: prices.get(sid) if group == "yahoo" else None)
    monkeypatch.setattr(fe, "_names_sectors", lambda: {})
    out = fe.compute_exposure(closes=spy.rename(columns={"close": "SAME"}))
    assert out is not None
    for ticker in ("SPY", "SAME"):
        rec = out["betas"][ticker]
        assert rec["mkt"] == 1.0 and rec["raw"]["mkt"] == 1.0
        assert rec["r2"] == 1.0 and rec["idio_vol"] == 0.0 and rec["n"] == 252
    assert out["stress_meta"]["available"] is (not gaps or days == 1000)
    # JSON serialization is part of the producer→consumer boundary, not a retyped beta fixture.
    result = _issue11016_native_consumers(json.loads(json.dumps(out, allow_nan=False)),
                                          {"SPY": 600, "SAME": 400})
    for lens in ("calm", "stress"):
        book = result["read"][lens]
        if lens == "stress" and not out["stress_meta"]["available"]:
            assert book is None
            continue
        covariance = out["factor_cov_stress" if lens == "stress" else "factor_cov"]
        assert book["ok"] and book["bookBeta"]["mkt"] == 1.0
        assert book["idioVar"] == 0.0
        assert book["variance"] == pytest.approx(covariance["mkt"]["mkt"])
        assert book["coverage"]["unmodeled"] == []
    for language, label in (("en", "S&P 500 −5%"), ("zh", "标普 −5%")):
        assert label in html.unescape(result[language]) and "-5.0%" in result[language]
    assert "Confidence categories are provisional." in result["en"]
    assert "置信度分类为暂定。" in result["zh"]
    assert result["populated"]["prov"] == {"scope": "portfolio", "gen": 3}
    assert result["thin"]["display"] == "none" and result["thin"]["html"] == ""
    assert result["thin"]["risk"]["reason"] == "thin"
    assert result["empty"]["display"] == "none" and result["empty"]["html"] == ""
    assert result["empty"]["weights"]["universe"] == []
    assert result["events"][-1]["universe"] == []


@pytest.mark.parametrize("support_loss", ["collinear", "constant_zero", "constant_nonzero"])
def test_issue11016_unidentified_record_cannot_become_modeled_zero_risk(support_loss):
    rng = np.random.default_rng(11027)
    m = rng.normal(0, .01, 252)
    raw = pd.DataFrame({"mkt": m, "growth": np.r_[rng.normal(0, .01, 126), 2*m[126:]]},
                       index=_idx(252))
    basis = fe.orthogonalize_factors(raw)
    if support_loss != "collinear":
        constant = .1 if support_loss == "constant_nonzero" else 0.0
        basis["growth"] = np.r_[rng.normal(0, .01, 126), np.full(126, constant)]
    returns = pd.DataFrame({"GOOD": m, "UNIDENTIFIED": np.r_[np.full(126, np.nan), m[126:]]},
                           index=raw.index)
    betas = fe._betas_on_window(returns, basis, 126, 5.0)["betas"]
    covariance = basis.cov()*252
    data = {"factors": [{"key": k} for k in basis], "betas": betas,
            "factor_cov": covariance.to_dict(), "stress_meta": {"available": False}}
    result = _issue11016_native_consumers(data, {"GOOD": 1, "UNIDENTIFIED": 1})
    assert result["read"]["calm"]["ok"] is False
    assert result["read"]["calm"]["reason"] == "thin"
    assert result["read"]["calm"]["coverage"]["unmodeled"] == ["UNIDENTIFIED"]
    assert result["en"] == result["zh"] == ""


def _native_calendar_export(monkeypatch, factor_holes=True):
    """Source-calendar regression from #11053; execute the native exporter."""
    rng = np.random.default_rng(316)
    sessions = pd.bdate_range("2023-01-02", periods=700)
    days = pd.date_range(sessions.min(), sessions.max())
    market = pd.Series(100 * np.cumprod(1 + rng.normal(.0003, .009, len(sessions))), index=sessions)
    btc_returns = rng.normal(.0004, .018, len(days))
    btc = pd.Series(100 * np.cumprod(1 + btc_returns), index=days)
    eth = pd.Series(100 * np.cumprod(1 + 1.2 * btc_returns + rng.normal(0, .003, len(days))), index=days)
    bonds = pd.Series(100.0, index=sessions)
    if factor_holes:
        bonds.iloc[1::4] = np.nan
    inputs = {"SPY": market.to_frame("close"), "TLT": bonds.to_frame("close"),
              "BTC-USD": btc.to_frame("close"), "ETH-USD": eth.to_frame("close")}
    monkeypatch.setattr(fe.store, "read", lambda group, name: inputs.get(name) if group == "yahoo" else None)
    monkeypatch.setattr(fe.config, "load", lambda: {})
    monkeypatch.setattr(fe, "_names_sectors", lambda: {})
    out = fe.compute_exposure(closes=pd.DataFrame({"SAME": market, "TWIN": market}))
    assert out is not None
    return json.loads(json.dumps(out, allow_nan=False))


@pytest.mark.parametrize("factor_holes", [False, True])
def test_native_export_preserves_equity_and_crypto_return_calendars(monkeypatch, factor_holes):
    out = _native_calendar_export(monkeypatch, factor_holes)
    for ticker in ["SAME", "TWIN", "SPY"]:
        rec = out["betas"][ticker]
        assert (rec["mkt"], rec["raw"]["mkt"], rec["r2"], rec["idio_vol"], rec["n"]) == (1.0, 1.0, 1.0, 0.0, 252)
    btc = out["betas"]["BTC-USD"]
    assert (btc["btc"], btc["raw"]["btc"], btc["r2"], btc["idio_vol"], btc["n"]) == (1.0, 1.0, 1.0, 0.0, 252)
    assert out["betas"]["ETH-USD"]["idio_vol"] > 0
    assert list(out["factor_cov"]) == [f["key"] for f in out["factors"]]
    result = _issue11016_native_consumers(out, {"SAME": 600, "TWIN": 400})
    for lens in ("calm", "stress"):
        book = result["read"][lens]
        if lens == "stress" and not out["stress_meta"]["available"]:
            assert book is None
            continue
        covariance = out["factor_cov_stress" if lens == "stress" else "factor_cov"]
        assert book["ok"] and book["bookBeta"]["mkt"] == 1.0
        assert book["idioVar"] == 0.0 and book["variance"] == pytest.approx(covariance["mkt"]["mkt"])
        assert book["coverage"]["unmodeled"] == []
    for language, label in (("en", "S&P 500 −5%"), ("zh", "标普 −5%")):
        assert label in html.unescape(result[language]) and "-5.0%" in result[language]
    assert result["populated"]["prov"] == {"scope": "portfolio", "gen": 3}


@pytest.mark.parametrize("asof_offset", [None, -20])
def test_native_source_missing_prices_are_not_bridged(monkeypatch, asof_offset):
    rng = np.random.default_rng(11029)
    sessions = pd.bdate_range("2023-01-02", periods=400)
    days = pd.date_range(sessions.min(), sessions.max())
    market = pd.Series(100 * np.cumprod(1 + rng.normal(.0003, .009, len(sessions))), index=sessions)
    gapped = market.copy()
    gapped.iloc[-50] = np.nan
    btc = pd.Series(100 * np.cumprod(1 + rng.normal(0, .02, len(days))), index=days)
    inputs = {"SPY": market.to_frame("close"), "IWD": gapped.to_frame("close"),
              "BTC-USD": btc.to_frame("close")}
    monkeypatch.setattr(fe.store, "read", lambda group, name: inputs.get(name) if group == "yahoo" else None)
    monkeypatch.setattr(fe.config, "load", lambda: {})
    monkeypatch.setattr(fe, "_names_sectors", lambda: {})
    asof = None if asof_offset is None else sessions[asof_offset]
    # An explicit stock-panel duplicate must retain the same precedence in both
    # prices and returns; the complete cached SPY series must not replace it.
    prices = pd.DataFrame({"STOCK": gapped, "SPY": gapped})
    out = fe.compute_exposure(closes=prices, asof=asof)
    assert out is not None
    json.dumps(out, allow_nan=False)
    frame = fe.factor_frame(asof=asof).tail(252)
    expected_returns = gapped.pct_change(fill_method=None).reindex(frame.index)
    assert expected_returns.isna().sum() == 2
    for ticker in ("STOCK", "SPY", "IWD"):
        rec = out["betas"][ticker]
        assert (rec["mkt"], rec["raw"]["mkt"], rec["r2"], rec["idio_vol"], rec["n"]) == (1.0, 1.0, 1.0, 0.0, 250)
    assert out["as_of"] == str(frame.index.max().date())
