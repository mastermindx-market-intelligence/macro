"""Portfolio factor-exposure engine. The math that must hold: orthogonalization
actually decorrelates the factors (so betas don't double-count); the joint betas
RECOVER known loadings; portfolio aggregation sums betas by weight, splits risk to
~1, and flags a one-factor book. Pure-math on synthetic data; snapshot() smoke-tested
vs the store. (engine/factor_exposure.py; validated in reports/factor-exposure-phase0.md.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import factor_exposure as fe


def _idx(n: int):
    return pd.date_range("2018-01-01", periods=n, freq="B")


def test_orthogonalize_removes_collinearity():
    rng = np.random.default_rng(0)
    n = 600
    m = rng.normal(0, 0.01, n)
    F = pd.DataFrame({                                  # growth/size highly collinear with market
        "mkt": m,
        "growth": 0.9 * m + rng.normal(0, 0.003, n),
        "size": 0.8 * m + rng.normal(0, 0.004, n),
    }, index=_idx(n))
    assert F.corr().loc["mkt", "growth"] > 0.85        # raw: badly collinear
    G = fe.orthogonalize_factors(F)
    off = G.corr().abs().to_numpy()[~np.eye(3, dtype=bool)]
    assert off.max() < 1e-9                             # mutually orthogonal after transform
    assert np.corrcoef(G["mkt"], F["mkt"])[0, 1] > 0.999   # market (first) is untouched


def test_betas_recover_known_loadings():
    rng = np.random.default_rng(1)
    n = 500
    F = pd.DataFrame({"mkt": rng.normal(0, 0.01, n), "growth": rng.normal(0, 0.008, n),
                      "size": rng.normal(0, 0.009, n)}, index=_idx(n))
    G = fe.orthogonalize_factors(F)
    true = {"AAA": {"mkt": 1.2, "growth": 0.5, "size": -0.3},
            "BBB": {"mkt": 0.7, "growth": -0.4, "size": 0.8}}
    R = pd.DataFrame({t: sum(b[k] * G[k] for k in b) + rng.normal(0, 0.0008, n)
                      for t, b in true.items()}, index=_idx(n))
    res = fe._betas_on_window(R, G, minp=100, max_abs=5.0)["betas"]
    for t, b in true.items():
        for k, v in b.items():
            assert abs(res[t][k] - v) < 0.05           # recovered
        assert res[t]["r2"] > 0.95                      # low-noise construction


def test_univariate_raw_betas_double_count_vs_orthogonal():
    # a stock that is PURE market should read ~1 market and ~0 elsewhere in the
    # orthogonal model, but the univariate growth/size betas are inflated by the
    # market collinearity — the double-count the orthogonalization removes.
    rng = np.random.default_rng(2)
    n = 600
    m = rng.normal(0, 0.01, n)
    F = pd.DataFrame({"mkt": m, "growth": 0.9 * m + rng.normal(0, 0.003, n),
                      "size": 0.8 * m + rng.normal(0, 0.004, n)}, index=_idx(n))
    px = pd.DataFrame({"PUREMKT": (1 + m).cumprod()}, index=_idx(n))
    orth = fe.stock_betas(px, F, window=n, min_obs=100, max_abs=5.0)["betas"]["PUREMKT"]
    raw = fe.raw_betas(px, F, window=n, min_obs=100, max_abs=5.0)["PUREMKT"]
    assert abs(orth["mkt"] - 1.0) < 0.05 and abs(orth["growth"]) < 0.1 and abs(orth["size"]) < 0.1
    assert raw["growth"] > 0.5 and raw["size"] > 0.5    # univariate over-attributes the market move


def test_portfolio_exposure_aggregates_and_flags_concentration():
    keys = fe.FACTOR_ORDER
    fcov = pd.DataFrame(np.diag([0.15 ** 2] * len(keys)), index=keys, columns=keys)
    betas = {"A": {k: 0.0 for k in keys}, "B": {k: 0.0 for k in keys}}
    betas["A"]["mkt"] = betas["B"]["mkt"] = 1.0         # two names, both pure market = ONE bet
    out = fe.portfolio_exposure({"A": 0.5, "B": 0.5}, betas, fcov)
    assert abs(out["betas"]["mkt"] - 1.0) < 1e-9
    assert out["top_factor"] == "mkt" and out["top_share"] > 0.99
    assert out["verdict"] == "concentrated"
    rc = out["risk_contrib"]
    assert abs(sum(v for v in rc.values() if v is not None) - 1.0) < 1e-6   # risk splits to 1


def test_portfolio_exposure_balanced_book():
    keys = fe.FACTOR_ORDER
    fcov = pd.DataFrame(np.diag([0.12 ** 2] * len(keys)), index=keys, columns=keys)
    # one name loads market, the other loads oil — genuinely two different bets
    betas = {"A": {k: 0.0 for k in keys}, "B": {k: 0.0 for k in keys}}
    betas["A"]["mkt"] = 1.0
    betas["B"]["oil"] = 1.0
    out = fe.portfolio_exposure({"A": 0.5, "B": 0.5}, betas, fcov)
    assert out["top_share"] < 0.7                       # not a single dominating factor


def test_snapshot_smoke():
    snap = fe.snapshot()
    assert isinstance(snap, dict)
    if "betas" in snap:                                 # store has data in CI
        assert snap["n"] > 0 and "factor_cov" in snap and snap["factors"]
        mk = [r["mkt"] for r in snap["betas"].values() if r.get("mkt") is not None]
        assert 0.6 < float(np.median(mk)) < 1.2         # market beta cross-section ~ centered on 1
        assert {f["key"] for f in snap["factors"]} <= set(fe.FACTOR_ORDER)
        # the client relies on confidence tiers being attached to factor metadata
        assert all("tier" in f and "scope" in f for f in snap["factors"])
    else:
        assert snap.get("verdict") == "unknown"


def test_compute_exposure_covers_etfs_self_consistently():
    out = fe.compute_exposure()
    if out is None:                                     # no store in this env — skip
        return
    b = out["betas"]
    # the factor proxies, as ETF holdings, must recover beta=1 to their own factor
    if "SPY" in b:
        assert b["SPY"]["is_etf"] is True and abs(b["SPY"]["mkt"] - 1.0) < 0.1
    if "TLT" in b:
        assert abs(b["TLT"]["rates"] - 1.0) < 0.15      # TLT IS the rates factor
    if "XLE" in b:
        assert b["XLE"]["oil"] > 0                       # energy ETF loads positively on oil
    if "FXI" in b and b["FXI"].get("china") is not None:
        assert b["FXI"]["china"] > 0.6                   # FXI IS the china factor proxy
    # every record carries the client-required fields
    rec = next(iter(b.values()))
    assert {"name", "sector", "is_etf", "raw", "r2", "idio_vol"} <= set(rec)


def test_compute_exposure_covers_crypto_with_sane_shape():
    """Crypto universe extension (W6.1): the cached crypto names ship betas like any ETF,
    tagged 'Crypto' (not 'ETF'), and read the honest way — btc-heavy with a real
    idiosyncratic-vol sleeve (crypto is its own bet, low R² on equity factors is correct).
    Would fail if crypto were dropped from the universe, mis-tagged, or if the
    orthogonalization mangled a near-pure-crypto name into NaNs."""
    out = fe.compute_exposure()
    if out is None:                                      # no store in this env — skip
        return
    b = out["betas"]
    # at least ONE cached crypto name must be modeled (BTC-USD is the deepest series and
    # is also the `btc` factor source, so it is present whenever the emit is)
    present = [t for t in fe.CRYPTO_NAMES if t in b]
    assert present, "no crypto names in emit despite cached BTC-USD/ETH-USD/COIN series"

    for t in present:
        rec = b[t]
        # (a) tagged as its own sleeve, not lumped with ETFs
        assert rec["sector"] == "Crypto", f"{t} sector={rec['sector']!r}, expected 'Crypto'"
        assert rec["name"] == fe.CRYPTO_NAMES[t]
        # (b) client-required fields present + a real idio sleeve (crypto is its own bet)
        assert {"name", "sector", "is_etf", "raw", "r2", "idio_vol"} <= set(rec)
        assert rec["idio_vol"] is not None
        # BTC is its own factor source; a correct same-horizon full fit has no
        # residual sleeve. Other crypto holdings retain their measured noise.
        if t == "BTC-USD":
            assert rec["idio_vol"] == 0.0 and rec["r2"] == 1.0
        else:
            assert rec["idio_vol"] > 0.0
        # (c) btc beta present and substantial — a crypto name reads as the crypto bet.
        #     Threshold 0.5 is loose: the real coins run ~0.9–1.1, COIN/ETFs ~0.9.
        assert rec.get("btc") is not None, f"{t} has no btc beta"
        assert rec["btc"] > 0.5, f"{t} btc beta {rec['btc']} unexpectedly low for a crypto name"
        # NO RANK OR CO-LEADER-BAND PIN HERE — deliberately, and this is the second
        # attempt at it.  #3538 required btc in the TOP-2 non-market loadings; #5032
        # loosened that to a 10% co-leader band (`btc >= second * 0.90`) after the top-2
        # form rotted.  MEASURED: replaying compute_exposure(asof=…) across 2026, the 0.90
        # band is red on 10 of 27 (asof × name) windows — every reading Jan-Apr 2026, with
        # ETHA's ratio as low as 0.358 (btc 0.730 vs growth 3.004 / size 2.041) — so it
        # passes today by 7 points on a quantity measured between 0.358 and 2.890.  Both
        # forms pin the ORDER of a 251-day ROLLING regression on live prices, and that
        # order is a reading, not an invariant: ETHA's btc rank was 3 (Jan/Mar/Apr), 3
        # (May), 4 (Jun), 2 (Jul), 3 (Aug).  Any threshold on it is a scheduled red.
        # Evidence table: PR #5036.  The claim both forms were reaching for — "a
        # spot-crypto name reads btc-heavy" — is pinned where it is actually decidable, on
        # a constructed book: `test_crypto_shaped_holding_reads_btc_heavy` below.  Do not
        # re-add a live ordering assertion in any form.

    # BTC-USD specifically: it IS the btc factor series → its btc beta must be ≈1
    # (self-consistency, the same check SPY→mkt gets in the sibling test)
    if "BTC-USD" in b and b["BTC-USD"].get("btc") is not None:
        assert abs(b["BTC-USD"]["btc"] - 1.0) < 0.2, \
            f"BTC-USD btc beta {b['BTC-USD']['btc']} should be ~1 (it is the btc factor)"


def test_crypto_shaped_holding_reads_btc_heavy():
    """A spot-crypto holding must attribute to `btc`, not smear across equity factors.

    The hermetic half of `test_compute_exposure_covers_crypto_with_sane_shape`, and the
    replacement for the two live ordering pins that rotted there (#3538's top-2, #5032's
    10% band).  That test can only assert what a live rolling window happens to produce;
    here the book is CONSTRUCTED — one unit of the crypto factor plus a tape sleeve — so
    "btc-heavy" is a decidable property of the estimator instead of a reading of this
    quarter's data, and it cannot drift.

    Fails if the sequential orthogonalization (btc is 8th in FACTOR_ORDER, so its column
    is btc ⟂ {mkt, growth, size, rates, usd, oil, china}) leaks the crypto move into an
    equity factor, or mangles a near-pure-crypto name into NaNs — the two failures the
    live ordering assertions were actually trying to catch.
    """
    rng = np.random.default_rng(6)
    n = 1500                                            # ~6y daily: enough that the residual
    keys = fe.FACTOR_ORDER                              # betas are signal, not sampling noise
    mkt = rng.normal(0, 0.010, n)
    btc = 0.6 * mkt + rng.normal(0, 0.025, n)           # crypto: some tape, mostly its own bet
    cols = {}
    for j, k in enumerate(keys):
        if k == "mkt":
            cols[k] = mkt
        elif k == "btc":
            cols[k] = btc
        else:                                           # equity/macro factors: tape + own sleeve
            cols[k] = (0.4 + 0.1 * j) * mkt + rng.normal(0, 0.010, n)
    F = pd.DataFrame(cols, index=_idx(n))

    # spot-ETH-ETF shaped: beta 1 to the crypto factor, 0.4 to the tape, thin idio
    r = 1.0 * btc + 0.4 * mkt + rng.normal(0, 0.004, n)
    px = pd.DataFrame({"ETHZ": (1 + r).cumprod()}, index=_idx(n))
    rec = fe.stock_betas(px, F, window=n, min_obs=200, max_abs=5.0)["betas"]["ETHZ"]

    assert all(rec[k] is not None for k in keys), f"NaN loading in a crypto-shaped book: {rec}"
    assert abs(rec["btc"] - 1.0) < 0.05, f"btc loading not recovered: {rec['btc']}"
    others = {k: abs(rec[k]) for k in keys if k not in ("mkt", "btc")}
    worst = max(others, key=others.get)
    # DOMINATES, not merely leads: outside the tape the constructed exposure is btc-only, so
    # a comparable equity loading means the peel leaked.  3× is the honest bar — a high-vol
    # asset regressed on a low-variance orthogonal column carries real sampling noise (~0.07
    # here), so demanding ~0 would be pinning the RNG.  Measured across 12 seeds: btc
    # recovered to 1.000 ± 0.006 and dominance 6.7×–18.1×, so 3× is not a lucky margin.
    assert abs(rec["btc"]) > 3 * others[worst], (
        f"crypto exposure smeared into equity factors: btc={rec['btc']} vs "
        f"{worst}={rec[worst]} (all: { {k: rec[k] for k in keys} })"
    )
    assert rec["idio_vol"] is not None and rec["idio_vol"] > 0.0


def _issue11016_prices(returns: pd.DataFrame) -> pd.DataFrame:
    """Include the real predecessor of the first return; never compress its clock."""
    first = returns.index[0] - pd.offsets.BDay()
    prior = pd.DataFrame(100.0, index=[first], columns=returns.columns)
    return pd.concat([prior, 100.0 * (1.0 + returns).cumprod()])


@pytest.mark.parametrize("stride", [1, 2, 4])
def test_issue11016_self_tracker_keeps_daily_horizon_and_first_return(stride):
    rng = np.random.default_rng(11016)
    market = pd.DataFrame({"mkt": rng.normal(0.0002, 0.012, 500)}, index=_idx(500))
    closes = _issue11016_prices(market.rename(columns={"mkt": "SAME"}))
    factors = market.iloc[::stride]
    rec = fe.stock_betas(closes, factors, window=80, min_obs=80,
                         max_abs=5.0)["betas"]["SAME"]
    raw = fe.raw_betas(closes, factors, window=80, min_obs=80, max_abs=5.0)
    assert rec == {"mkt": 1.0, "r2": 1.0, "idio_vol": 0.0, "n": 80}
    assert raw == {"SAME": {"mkt": 1.0}}


def test_issue11016_recent_listing_ignores_factor_variance_before_listing():
    rng = np.random.default_rng(11017)
    m = np.r_[rng.normal(0, 0.04, 126), rng.normal(0, 0.003, 126)]
    factors = pd.DataFrame({"mkt": m}, index=_idx(252))
    closes = _issue11016_prices(factors.rename(columns={"mkt": "RECENT"}))
    closes.loc[closes.index < factors.index[125], "RECENT"] = np.nan
    changed = factors.copy()
    changed.iloc[:126] *= 13.0
    for frame in (factors, changed):
        rec = fe.stock_betas(closes, frame, window=252, min_obs=126,
                             max_abs=5.0)["betas"]["RECENT"]
        assert rec == {"mkt": 1.0, "r2": 1.0, "idio_vol": 0.0, "n": 126}
        assert fe.raw_betas(closes, frame, window=252, min_obs=126,
                            max_abs=5.0)["RECENT"]["mkt"] == 1.0


def test_issue11016_joint_fit_uses_fixed_basis_on_ticker_support():
    rng = np.random.default_rng(11018)
    m = rng.normal(0, 0.01, 252)
    growth = np.r_[2 * m[:126], -2 * m[126:]] + rng.normal(0, 0.003, 252)
    factors = pd.DataFrame({"mkt": m, "growth": growth}, index=_idx(252))
    basis = fe.orthogonalize_factors(factors)
    returns = factors[["mkt"]].rename(columns={"mkt": "RECENT"})
    returns.iloc[:126] = np.nan
    assert abs(basis.corr().loc["mkt", "growth"]) < 1e-10
    assert abs(basis.iloc[126:].corr().loc["mkt", "growth"]) > 0.9
    rec = fe._betas_on_window(returns, basis, 126, 5.0)["betas"]["RECENT"]
    assert rec == {"mkt": 1.0, "growth": 0.0, "r2": 1.0,
                   "idio_vol": 0.0, "n": 126}


def test_issue11016_finite_support_controls_fit_count_and_diagnostics():
    rng = np.random.default_rng(11019)
    factors = pd.DataFrame({"mkt": rng.normal(0, 0.01, 160),
                            "growth": rng.normal(0, 0.006, 160)}, index=_idx(160))
    returns = pd.DataFrame({"A": 0.003 + 1.2 * factors.mkt - 0.4 * factors.growth
                            + rng.normal(0, 0.001, 160)}, index=factors.index)
    factors.iloc[6, 0], factors.iloc[7, 1] = np.nan, np.inf
    returns.iloc[8, 0], returns.iloc[9, 0] = np.nan, -np.inf
    mask = np.isfinite(factors).all(axis=1) & np.isfinite(returns.A)
    # Independent full intercept design, not the production centered/scaled solve.
    x = np.column_stack([np.ones(mask.sum()), factors.loc[mask].to_numpy()])
    y = returns.loc[mask, "A"].to_numpy()
    coef = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ coef
    expected = {"mkt": round(float(coef[1]), 3), "growth": round(float(coef[2]), 3),
                "r2": round(float(1 - np.var(resid) / np.var(y)), 3),
                "idio_vol": round(float(np.std(resid) * np.sqrt(252)), 3), "n": 156}
    result = fe._betas_on_window(returns, factors, 156, 5.0)
    assert result["betas"]["A"] == expected
    assert result["n"] == {"A": 156}
    assert fe._betas_on_window(returns, factors, 157, 5.0)["betas"] == {}


def test_issue11016_rank_deficient_subset_is_unmodeled():
    rng = np.random.default_rng(11020)
    m = rng.normal(0, 0.01, 252)
    growth = np.r_[rng.normal(0, 0.02, 126), 2 * m[126:]]
    factors = pd.DataFrame({"mkt": m, "growth": growth}, index=_idx(252))
    basis = fe.orthogonalize_factors(factors)
    returns = factors[["mkt"]].rename(columns={"mkt": "UNIDENTIFIED"})
    returns.iloc[:126] = np.nan
    assert np.linalg.matrix_rank(basis.to_numpy()) == 2
    assert np.linalg.matrix_rank(basis.iloc[126:].to_numpy()) == 1
    assert fe._betas_on_window(returns, basis, 126, 5.0)["betas"] == {}


def test_issue11016_constant_factor_and_target_keep_honest_nulls():
    factors = pd.DataFrame({"mkt": np.linspace(-0.02, 0.02, 160), "rates": 0.0},
                           index=_idx(160))
    returns = pd.DataFrame({"SAME": factors.mkt, "CONSTANT": 0.002}, index=factors.index)
    result = fe._betas_on_window(returns, factors, 126, 5.0)["betas"]
    assert result["SAME"] == {"mkt": 1.0, "rates": None, "r2": 1.0,
                              "idio_vol": 0.0, "n": 160}
    assert result["CONSTANT"] == {"mkt": 0.0, "rates": None, "r2": None,
                                  "idio_vol": 0.0, "n": 160}
    assert fe._betas_on_window(returns, factors * 0, 126, 5.0)["betas"] == {}


@pytest.mark.parametrize("sign", [-1, 1])
def test_issue11016_cap_diagnostics_describe_exported_coefficients(sign):
    rng = np.random.default_rng(11021)
    factors = pd.DataFrame({"mkt": rng.normal(0.002, 0.01, 160),
                            "growth": rng.normal(0, 0.005, 160)}, index=_idx(160))
    y = 0.004 + sign * 9 * factors.mkt + 3 * factors.growth
    result = fe._betas_on_window(y.to_frame("A"), factors, 126, 5.0)["betas"]["A"]
    capped = np.array([sign * 5.0, 3.0])
    fitted = factors.to_numpy() @ capped
    fitted += y.mean() - fitted.mean()
    resid = y.to_numpy() - fitted
    assert result["mkt"] == sign * 5.0 and result["growth"] == 3.0
    assert result["r2"] == round(float(1 - np.var(resid) / np.var(y)), 3)
    assert result["idio_vol"] == round(float(np.std(resid) * np.sqrt(252)), 3)


def test_issue11016_raw_shocks_remain_univariate_on_pairwise_support():
    rng = np.random.default_rng(11022)
    m = rng.normal(0, 0.01, 300)
    factors = pd.DataFrame({"mkt": m, "growth": 0.9 * m + rng.normal(0, 0.004, 300)},
                           index=_idx(300))
    closes = _issue11016_prices(factors[["mkt"]].rename(columns={"mkt": "A"}))
    closes.iloc[::13, 0] = np.nan
    returns = closes.pct_change(fill_method=None).reindex(factors.index)
    raw = fe.raw_betas(closes, factors, window=300, min_obs=126, max_abs=5.0)["A"]
    for key in factors:
        pair = pd.concat([returns.A, factors[key]], axis=1).dropna()
        expected = pair.iloc[:, 0].cov(pair.iloc[:, 1]) / pair.iloc[:, 1].var()
        assert raw[key] == round(float(expected), 3)
    assert raw["mkt"] == 1.0 and raw["growth"] > 0.5


def test_issue11016_raw_dot_overflow_cannot_fabricate_a_capped_shock():
    # Every price and daily return is finite. Direct centered x@y overflows,
    # even though the exactly constructed univariate coefficient is only 1.5.
    closes = pd.DataFrame({"A": np.r_[np.tile([1e-153, 2.7], 80), 1e-153]},
                          index=_idx(161))
    factors = (closes.pct_change(fill_method=None).iloc[1:] / 1.5).rename(columns={"A": "mkt"})
    raw = fe.raw_betas(closes, factors, window=160, min_obs=126, max_abs=5.0)
    assert raw == {"A": {"mkt": 1.5}}


def test_issue11016_factor_frame_rejects_nonfinite_returns(monkeypatch):
    idx = _idx(300)
    prices = pd.DataFrame({"close": 100.0 + np.arange(300)}, index=idx)
    prices.iloc[150, 0] = 0.0
    prices.iloc[200, 0] = np.inf
    monkeypatch.setattr(fe.store, "read", lambda group, sid: prices if sid == "SPY" else None)
    frame = fe.factor_frame()
    expected = prices.close.pct_change(fill_method=None)
    expected = expected[np.isfinite(expected)]
    assert frame.index.equals(expected.index)
    assert np.isfinite(frame.to_numpy()).all()


@pytest.mark.parametrize("magnitude,modeled", [(1e150, True), (1e153, False), (1e200, False)])
def test_issue11016_finite_returns_cannot_export_overflowed_risk(magnitude, modeled):
    import json

    factors = pd.DataFrame({"mkt": np.linspace(-.01, .01, 160)}, index=_idx(160))
    returns = pd.DataFrame({"A": np.tile([-magnitude, magnitude], 80)}, index=factors.index)
    out = fe._betas_on_window(returns, factors, 126, 5.0)
    assert ("A" in out["betas"]) is modeled
    json.dumps(out, allow_nan=False)
    if modeled:
        assert np.isfinite(out["betas"]["A"]["idio_vol"] ** 2)


def test_issue11016_phase0_preserves_returns_future_boundary_and_basis(monkeypatch):
    from scripts import factor_exposure_phase0 as phase

    rng = np.random.default_rng(11023)
    idx = _idx(800)
    m = rng.normal(0, 0.01, 800)
    factors = pd.DataFrame({"mkt": m, "growth": np.linspace(-1, 1, 800) * m
                            + rng.normal(0, 0.004, 800)}, index=idx).iloc[::2]
    daily = pd.DataFrame({f"A{i}": (0.5 + i / 20) * m + rng.normal(0, 0.002, 800)
                          for i in range(20)}, index=idx)
    closes = _issue11016_prices(daily)
    decisions = list(factors.index[[100, 160, 220, 280]])
    monkeypatch.setattr(phase, "month_grid", lambda *args, **kwargs: decisions)
    monkeypatch.setattr(phase, "RNG", np.random.default_rng(7))
    calls = []
    native = fe._betas_on_window

    def capture(returns, basis, minp, max_abs):
        calls.append((returns.copy(), basis.copy(), minp))
        return native(returns, basis, minp, max_abs)

    monkeypatch.setattr(fe, "_betas_on_window", capture)
    result = phase.stability(factors, closes, win=80, horizon=40, minp=50,
                             max_abs=5.0, basket_sizes=[1, 5], n_baskets=12)
    assert result["rebalances"] == 4 and len(calls) == 8
    all_returns = closes.pct_change(fill_method=None)
    for j, date in enumerate(decisions):
        before = factors.loc[factors.index <= date].tail(80)
        future = factors.loc[factors.index > date].head(40)
        transform = fe.orthogonalize_fit(before)
        for call, frame, floor in ((calls[2*j], before, 50), (calls[2*j+1], future, 20)):
            returns, basis, minp = call
            pd.testing.assert_frame_equal(returns, all_returns.reindex(frame.index))
            pd.testing.assert_frame_equal(basis, fe.orthogonalize_apply(frame, transform))
            assert minp == floor and len(basis) == len(frame)
        assert calls[2*j+1][1].index.min() > date


@pytest.mark.parametrize("constant", [0.0, 0.1])
def test_issue11016_support_constant_factor_is_unmodeled(constant):
    idx = _idx(252)
    market = pd.Series(np.tile([-.01, .01], 126), index=idx)
    growth = pd.Series(np.r_[np.tile([.02, -.01], 63), np.full(126, constant)], index=idx)
    returns = market.where(np.arange(252) >= 126).to_frame("UNIDENTIFIED")
    result = fe._betas_on_window(returns, pd.DataFrame({"mkt": market, "growth": growth}), 126, 5)
    assert result == {"betas": {}, "n": {}}


def test_issue11016_solver_failure_omits_only_failed_ticker(monkeypatch):
    factors = pd.DataFrame({"mkt": np.linspace(-.02, .02, 160)}, index=_idx(160))
    returns = pd.DataFrame({"FAILED": factors.mkt, "GOOD": 2 * factors.mkt})
    native = np.linalg.lstsq
    calls = []

    def fail_first(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise np.linalg.LinAlgError("controlled nonconvergence")
        return native(*args, **kwargs)

    monkeypatch.setattr(np.linalg, "lstsq", fail_first)
    result = fe._betas_on_window(returns, factors, 126, 5.0)
    assert len(calls) == 2
    assert result["n"] == {"GOOD": 160}
    assert result["betas"] == {"GOOD": {"mkt": 2.0, "r2": 1.0, "idio_vol": 0.0, "n": 160}}


def test_phase0_does_not_count_calendar_dates_without_stock_fits():
    from scripts import factor_exposure_phase0 as phase

    idx = pd.bdate_range("2020-01-01", periods=700)
    factors = pd.DataFrame({"mkt": np.tile([-.01, .01], 350)}, index=idx)
    closes = pd.DataFrame({"MISSING": np.nan}, index=idx[-500:])
    result = phase.stability(factors, closes, win=80, horizon=40, minp=40,
                             max_abs=5, basket_sizes=[1], n_baskets=0)
    assert result["rebalances"] == 0
    assert result["error"] == "too few fitted rebalances (0)"


def test_issue11016_phase0_counts_only_successfully_fitted_dates(monkeypatch):
    from scripts import factor_exposure_phase0 as phase

    rng = np.random.default_rng(11028)
    idx = _idx(800)
    market = pd.Series(rng.normal(0, .01, len(idx)), index=idx)
    factors = market.to_frame("mkt").iloc[::2]
    closes = pd.DataFrame({f"S{i}": 100 * (1 + (.5 + i/20) * market).cumprod()
                           for i in range(12)})
    closes.iloc[:221] = np.nan
    decisions = list(factors.index[[60, 100, 160, 220, 280, 340]])
    monkeypatch.setattr(phase, "month_grid", lambda *args, **kwargs: decisions)
    result = phase.stability(factors, closes, win=80, horizon=40, minp=50,
                             max_abs=5, basket_sizes=[1], n_baskets=0)
    assert result["planned_rebalances"] == 6
    assert result["rebalances"] == 4
    assert result["span"] == f"{decisions[2].date()}..{decisions[-1].date()}"
    assert result["per_stock"]["mkt"] == {"persist": 1.0, "n": 4}


def test_issue11016_short_grid_has_no_fitted_rebalances(monkeypatch):
    from scripts import factor_exposure_phase0 as phase

    factors = pd.DataFrame({"mkt": np.linspace(-.01, .01, 200)}, index=_idx(200))
    closes = _issue11016_prices(factors.rename(columns={"mkt": "SAME"}))
    monkeypatch.setattr(phase, "month_grid", lambda *args, **kwargs: list(factors.index[[80, 100, 120]]))
    result = phase.stability(factors, closes, win=80, horizon=40, minp=40,
                             max_abs=5, basket_sizes=[1], n_baskets=0)
    assert result["rebalances"] == 0 and result["planned_rebalances"] == 3
    assert result["error"] == "grid too short (3)"
