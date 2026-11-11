"""Portfolio factor-exposure engine. The math that must hold: orthogonalization
actually decorrelates the factors (so betas don't double-count); the decoupled betas
RECOVER known loadings; portfolio aggregation sums betas by weight, splits risk to
~1, and flags a one-factor book. Pure-math on synthetic data; snapshot() smoke-tested
vs the store. (engine/factor_exposure.py; validated in reports/factor-exposure-phase0.md.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import json
from html import unescape
from pathlib import Path
import shutil
import subprocess

from engine import factor_exposure as fe


def test_missing_stock_history_uses_one_estimation_sample():
    idx = pd.bdate_range('2025-01-01', periods=252)
    market = pd.Series(np.r_[np.tile([-.04, .04], 63), np.tile([-.01, .01], 63)], index=idx)
    returns = pd.DataFrame({'FULL': market, 'RECENT': market.where(np.arange(252) >= 126)})
    out = fe._betas_on_window(returns, market.to_frame('mkt'), 126, 5)['betas']
    for ticker, count in [('FULL', 252), ('RECENT', 126)]:
        assert out[ticker] == {'mkt': 1.0, 'r2': 1.0, 'idio_vol': 0.0, 'n': count}


@pytest.mark.parametrize('seed', [4, 17, 52, 91])
def test_masked_multifactor_fit_recovers_known_joint_loadings(seed):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range('2024-01-01', periods=300)
    raw = pd.DataFrame(rng.normal(0, .01, (300, 2)), index=idx, columns=['mkt', 'growth'])
    basis = fe.orthogonalize_factors(raw)
    # Selection induces correlation in the shared basis; the generating model
    # remains exactly known and includes a nonzero intercept.
    selected = (basis.mkt * basis.growth > 0).to_numpy()
    y = (1.25 * basis.mkt - .75 * basis.growth + .002).where(selected)
    out = fe._betas_on_window(y.to_frame('KNOWN'), basis, 100, 5)['betas']['KNOWN']
    assert out == {'mkt': 1.25, 'growth': -.75, 'r2': 1.0, 'idio_vol': 0.0,
                   'n': int(selected.sum())}


@pytest.mark.parametrize('method', ['stock_betas', 'raw_betas'])
def test_factor_date_holes_do_not_compound_stock_returns(method):
    idx = pd.bdate_range('2024-01-01', periods=701)
    daily = pd.Series(np.tile([.05, -.01, .03, -.02], 176)[:701], index=idx)
    prices = (100 * (1 + daily).cumprod()).to_frame('SAME')
    factors = prices.SAME.pct_change(fill_method=None).to_frame('mkt').dropna().iloc[::2]
    out = getattr(fe, method)(prices, factors, window=252, min_obs=126, max_abs=5)
    record = out['betas']['SAME'] if method == 'stock_betas' else out['SAME']
    assert record['mkt'] == 1.0
    if method == 'stock_betas':
        assert (record['n'], record['r2'], record['idio_vol']) == (252, 1.0, 0.0)


def test_first_window_return_keeps_its_predecessor():
    idx = pd.bdate_range('2025-01-01', periods=127)
    prices = pd.Series(100 * np.cumprod(1 + np.tile([.02, -.01], 64)[:127]), index=idx)
    factors = prices.pct_change(fill_method=None).dropna().to_frame('mkt')
    out = fe.stock_betas(prices.to_frame('SAME'), factors, window=126, min_obs=126, max_abs=5)
    assert out['betas']['SAME'] == {'mkt': 1.0, 'r2': 1.0, 'idio_vol': 0.0, 'n': 126}


def test_rank_loss_on_ticker_support_abstains_from_modeled_coverage():
    idx = pd.bdate_range('2025-01-01', periods=252)
    market = pd.Series(np.tile([-.01, .01], 126), index=idx)
    growth = market * np.r_[np.ones(126), -np.ones(126)]
    basis = pd.DataFrame({'mkt': market, 'growth': growth})
    returns = pd.DataFrame({'FULL': 2 * market, 'AMBIGUOUS': (2 * market).where(np.arange(252) < 126)})
    out = fe._betas_on_window(returns, basis, 126, 5)
    assert out['betas']['FULL']['mkt'] == 2.0
    assert 'AMBIGUOUS' not in out['betas']
    assert 'AMBIGUOUS' not in out['n']


def test_finite_common_support_controls_observation_admission():
    idx = pd.bdate_range('2025-01-01', periods=252)
    market = pd.Series(np.tile([-.01, .01], 126), index=idx)
    returns = market.copy()
    returns.iloc[:3] = [np.inf, -np.inf, np.nan]
    factor = market.copy()
    factor.iloc[3] = np.inf
    out = fe._betas_on_window(returns.to_frame('SAME'), factor.to_frame('mkt'), 248, 5)
    assert out['betas']['SAME'] == {'mkt': 1.0, 'r2': 1.0, 'idio_vol': 0.0, 'n': 248}
    assert not fe._betas_on_window(returns.to_frame('SAME'), factor.to_frame('mkt'), 249, 5)['betas']


def test_zero_variance_factor_does_not_poison_identified_model():
    idx = pd.bdate_range('2025-01-01', periods=252)
    market = pd.Series(np.tile([-.01, .01], 126), index=idx)
    basis = pd.DataFrame({'mkt': market, 'rates': 0.0}, index=idx)
    out = fe._betas_on_window(market.to_frame('SAME'), basis, 126, 5)['betas']['SAME']
    assert out == {'mkt': 1.0, 'rates': None, 'r2': 1.0, 'idio_vol': 0.0, 'n': 252}


def test_support_induced_constant_factor_is_not_modeled_as_zero_risk():
    idx = pd.bdate_range('2025-01-01', periods=252)
    market = pd.Series(np.tile([-.01, .01], 126), index=idx)
    growth = pd.Series(np.r_[np.tile([.02, -.01], 63), np.zeros(126)], index=idx)
    returns = market.where(np.arange(252) >= 126).to_frame('UNIDENTIFIED')
    out = fe._betas_on_window(returns, pd.DataFrame({'mkt': market, 'growth': growth}), 126, 5)
    assert not out['betas']
    assert not out['n']


@pytest.mark.skipif(shutil.which('node') is None, reason='node not on PATH')
@pytest.mark.parametrize('support_loss', ['collinear', 'constant'])
def test_unidentified_native_fit_reaches_risk_core_as_unmodeled(support_loss):
    idx = pd.bdate_range('2025-01-01', periods=252)
    market = pd.Series(np.tile([-.01, .01], 126), index=idx)
    growth = (market * np.r_[np.ones(126), -np.ones(126)] if support_loss == 'collinear'
              else pd.Series(np.r_[np.zeros(126), np.tile([.02, -.01], 63)], index=idx))
    returns = pd.DataFrame({'FULL': 2 * market,
                            'UNIDENTIFIED': (2 * market).where(np.arange(252) < 126)})
    native = fe._betas_on_window(returns, pd.DataFrame({'mkt': market, 'growth': growth}), 126, 5)
    risk = Path(__file__).resolve().parents[1] / 'templates/risk_core.js'
    program = "const fs=require('node:fs'), r=require(process.argv[1]); " \
              "const data=JSON.parse(fs.readFileSync(0,'utf8')); " \
              "process.stdout.write(JSON.stringify(r.coverage(data,{FULL:100,UNIDENTIFIED:200})));"
    result = subprocess.run(['node', '-e', program, str(risk)],
                            input=json.dumps({'betas': native['betas']}, allow_nan=False),
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    coverage = json.loads(result.stdout)
    assert coverage['modeled'] == ['FULL']
    assert coverage['unmodeled'] == ['UNIDENTIFIED']
    assert coverage['unmodeledFrac'] == pytest.approx(2 / 3)
    assert coverage['abstain'] is True


def test_capped_coefficients_determine_residual_statistics():
    idx = pd.bdate_range('2025-01-01', periods=252)
    market = pd.Series(np.tile([-.01, .01], 126), index=idx)
    out = fe._betas_on_window((4 * market + .01).to_frame('CAPPED'), market.to_frame('mkt'), 126, 2)['betas']['CAPPED']
    assert out == {'mkt': 2.0, 'r2': .75, 'idio_vol': round(.02 * np.sqrt(252), 3), 'n': 252}


def _native_calendar_export(monkeypatch, factor_holes=True):
    """Native producer with only its external prices/config/name I/O controlled."""
    rng = np.random.default_rng(316)
    sessions = pd.bdate_range('2023-01-02', periods=700)
    days = pd.date_range(sessions.min(), sessions.max())
    market = pd.Series(100 * np.cumprod(1 + rng.normal(.0003, .009, len(sessions))), index=sessions)
    btc_returns = rng.normal(.0004, .018, len(days))
    btc = pd.Series(100 * np.cumprod(1 + btc_returns), index=days)
    eth = pd.Series(100 * np.cumprod(1 + 1.2 * btc_returns + rng.normal(0, .003, len(days))), index=days)
    bonds = pd.Series(100.0, index=sessions)
    if factor_holes:
        bonds.iloc[1::4] = np.nan
    inputs = {'SPY': market.to_frame('close'), 'TLT': bonds.to_frame('close'),
              'BTC-USD': btc.to_frame('close'), 'ETH-USD': eth.to_frame('close')}
    monkeypatch.setattr(fe.store, 'read', lambda group, name: inputs.get(name) if group == 'yahoo' else None)
    monkeypatch.setattr(fe.config, 'load', lambda: {})
    monkeypatch.setattr(fe, '_names_sectors', lambda: {})
    out = fe.compute_exposure(closes=pd.DataFrame({'SAME': market, 'TWIN': market}))
    assert out is not None
    # Exercise the actual serialized payload boundary too: no NaN/Infinity escapes.
    return json.loads(json.dumps(out, allow_nan=False))


@pytest.mark.parametrize('factor_holes', [False, True])
def test_native_export_preserves_equity_and_crypto_return_calendars(monkeypatch, factor_holes):
    out = _native_calendar_export(monkeypatch, factor_holes)
    for ticker in ['SAME', 'TWIN', 'SPY']:
        rec = out['betas'][ticker]
        assert (rec['mkt'], rec['raw']['mkt'], rec['r2'], rec['idio_vol'], rec['n']) == (1.0, 1.0, 1.0, 0.0, 252)
    btc = out['betas']['BTC-USD']
    assert (btc['btc'], btc['raw']['btc'], btc['r2'], btc['idio_vol'], btc['n']) == (1.0, 1.0, 1.0, 0.0, 252)
    assert out['betas']['ETH-USD']['idio_vol'] > 0
    assert list(out['factor_cov']) == [f['key'] for f in out['factors']]


def test_phase0_keeps_native_returns_and_reports_only_fitted_dates(monkeypatch):
    from scripts import factor_exposure_phase0 as phase0
    rng = np.random.default_rng(91)
    idx = pd.bdate_range('2020-01-01', periods=1100)
    market = pd.Series(rng.normal(0, .01, len(idx)), index=idx)
    # Factor availability has holes, and factor history starts before the stock panel.
    factors = market.to_frame('mkt').iloc[::2]
    stock_index = idx[-700:]
    closes = pd.DataFrame({f'S{i}': 100 * (1 + (.5 + i / 20) * market.loc[stock_index]).cumprod()
                           for i in range(12)})
    calls = []
    native = fe.stock_betas
    def observe(prices, frame, **kwargs):
        result = native(prices, frame, **kwargs)
        calls.append((frame.index.copy(), result))
        return result
    monkeypatch.setattr(fe, 'stock_betas', observe)
    grid = phase0.month_grid(factors.index.intersection(stock_index), warmup=80, horizon=40)
    result = phase0.stability(factors, closes, win=80, horizon=40, minp=40,
                             max_abs=5, basket_sizes=[1], n_baskets=0)
    assert result['rebalances'] == len(grid)
    assert result['span'] == f'{grid[0].date()}..{grid[-1].date()}'
    assert result['per_stock']['mkt'] == {'persist': 1.0, 'n': len(grid)}
    assert len(calls) == 2 * len(grid)
    for anchor, (insample, before), (forward, after) in zip(grid, calls[::2], calls[1::2]):
        assert insample.max() == anchor
        assert forward.min() > anchor
        assert len(insample) == 80 and len(forward) == 40
        for ticker, loading in [('S0', .5), ('S11', 1.05)]:
            assert before['betas'][ticker]['mkt'] == loading
            assert after['betas'][ticker]['mkt'] == loading
            assert before['betas'][ticker]['n'] == 80
            assert after['betas'][ticker]['n'] == 40


def test_phase0_does_not_count_calendar_dates_without_stock_fits():
    from scripts import factor_exposure_phase0 as phase0
    idx = pd.bdate_range('2020-01-01', periods=700)
    factors = pd.DataFrame({'mkt': np.tile([-.01, .01], 350)}, index=idx)
    closes = pd.DataFrame({'MISSING': np.nan}, index=idx[-500:])
    result = phase0.stability(factors, closes, win=80, horizon=40, minp=40,
                             max_abs=5, basket_sizes=[1], n_baskets=0)
    assert result['rebalances'] == 0
    assert result['error'] == 'too few fitted rebalances (0)'


@pytest.mark.skipif(shutil.which('node') is None, reason='node not on PATH')
@pytest.mark.parametrize('language,label', [('en', 'S&P 500 −5%'), ('zh', '标普 −5%')])
def test_native_export_reaches_risk_core_and_bilingual_shock_rows(monkeypatch, language, label):
    out = _native_calendar_export(monkeypatch)
    root = Path(__file__).resolve().parents[1]
    program = r'''
const fs = require('node:fs'), vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const panel = {style: {}, innerHTML: '', querySelectorAll(){return [];}, querySelector(){return null;}};
const events = [];
const document = {documentElement: {getAttribute(k){return k==='data-lang'?input.language:k==='data-ws-mode'?'portfolio':'';}},
  getElementById(id){return id==='fx_panel'?panel:null;}, addEventListener(){}, dispatchEvent(e){events.push(e.detail);}};
const context = {document, window:{WS:{prov(){return {gen:7};}}}, console,
  localStorage:{getItem(){return null;},setItem(){}}, setTimeout,
  CustomEvent:function(name,opts){this.type=name;this.detail=opts.detail;},
  fetch:async()=>({ok:true,json:async()=>input.data})};
vm.runInNewContext(fs.readFileSync(input.controller,'utf8'), context);
context.window.FX.setAutoWeights({SAME:100,TWIN:100});
setImmediate(()=>{
  const RiskCore=require(input.risk);
  const book=RiskCore.book(input.data,{SAME:100,TWIN:100});
  process.stdout.write(JSON.stringify({html:panel.innerHTML,weights:context.window.FX.currentWeights(),
    bookBeta:book.bookBeta,coverage:book.coverage,events}));
});
'''
    result = subprocess.run(['node', '-e', program], input=json.dumps({
        'data': out, 'language': language, 'controller': str(root / 'site/factor_exposure.js'),
        'risk': str(root / 'templates/risk_core.js')}), text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert label in unescape(observed['html'])
    assert '-5.0%' in observed['html']
    assert observed['bookBeta']['mkt'] == 1.0
    assert observed['coverage']['unmodeledFrac'] == 0
    assert observed['weights']['prov'] == {'scope': 'portfolio', 'gen': 7}
    assert observed['weights']['universe'] == ['SAME', 'TWIN']


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
    tagged 'Crypto' (not 'ETF'), with finite nonnegative idiosyncratic volatility.
    BTC itself is a factor, so its correctly aligned self-fit can have zero residual.
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
        # (b) client-required fields present + a valid residual-risk estimate
        assert {"name", "sector", "is_etf", "raw", "r2", "idio_vol"} <= set(rec)
        # BTC is itself a model factor; a self-factor tracker can have zero idio.
        assert rec["idio_vol"] is not None and rec["idio_vol"] >= 0.0
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
