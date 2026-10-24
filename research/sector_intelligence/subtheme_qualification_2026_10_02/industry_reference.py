"""Public, revised-vintage industry reference study. Not a live/PIT strategy.

Uses only explicitly supplied French-library ZIP files; never downloads or reads
Mastermind stores. All specifications are fixed, and all authority stays false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata

NAMES = ('mom20', 'mom60', 'mom252_skip21', 'accel5_20', 'persistence20', 'efficiency20')
PERIODS = {'development': ('1990-01-01', '2009-12-31'),
           'validation': ('2010-01-01', '2015-12-31'),
           'evaluation': ('2016-01-01', '2025-12-31')}
CAPS = {k: False for k in ('can_rank', 'can_gate', 'can_size', 'can_trade', 'can_promote')}


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_table(text: str, marker: str, ncols: int) -> pd.DataFrame:
    """Parse exactly one first-party daily table without filling missing values."""
    lines = text.splitlines()
    starts = [i for i, s in enumerate(lines) if marker in s]
    if len(starts) != 1:
        raise ValueError('TABLE_MARKER_NOT_UNIQUE')
    pos = starts[0] + (1 if marker.startswith('Average') else 0)
    while pos < len(lines) and not lines[pos].strip():
        pos += 1
    columns = lines[pos].split()
    if len(columns) != ncols or len(set(columns)) != ncols:
        raise ValueError('COLUMN_COUNT_OR_DUPLICATE')
    rows, dates = [], []
    for line in lines[pos + 1:]:
        fields = line.split()
        if not fields or not re.fullmatch(r'\d{8}', fields[0]):
            if dates:
                break
            continue
        if len(fields) != ncols + 1:
            raise ValueError('ROW_COLUMN_COUNT')
        dates.append(pd.to_datetime(fields[0], format='%Y%m%d'))
        row = [float(x) for x in fields[1:]]
        rows.append([np.nan if x in (-99.99, -999.0) else x / 100 for x in row])
    idx = pd.DatetimeIndex(dates)
    if not len(idx) or idx.has_duplicates or not idx.is_monotonic_increasing:
        raise ValueError('DATES_EMPTY_DUPLICATED_OR_UNORDERED')
    df = pd.DataFrame(rows, columns=columns, index=idx)
    if np.isinf(df.to_numpy()).any():
        raise ValueError('INFINITE_RETURN')
    return df


def load_zip(path: Path, marker: str, ncols: int) -> tuple[pd.DataFrame, dict]:
    raw = path.read_bytes()
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != 1 or not names[0].lower().endswith('.txt'):
            raise ValueError('UNEXPECTED_ARCHIVE')
        data = z.read(names[0])
    text = data.decode('utf-8-sig')
    df = parse_table(text, marker, ncols)
    return df, {'zip_sha256': digest(raw), 'text_sha256': digest(data),
                'zip_bytes': len(raw), 'header': text.splitlines()[0],
                'rows': len(df), 'first': str(df.index[0].date()),
                'last': str(df.index[-1].date())}


def features(r: pd.DataFrame, market: pd.Series) -> dict[str, pd.DataFrame]:
    if not r.index.equals(market.index) or (r <= -1).any().any() or (market <= -1).any():
        raise ValueError('CALENDAR_OR_RETURN_BASIS')
    x = np.log1p(r).sub(np.log1p(market), axis=0)
    sum20 = x.rolling(20, min_periods=20).sum()
    positive = (x > 0).astype(float).where(x.notna())
    return {'mom20': sum20, 'mom60': x.rolling(60, min_periods=60).sum(),
            'mom252_skip21': x.shift(21).rolling(231, min_periods=231).sum(),
            'accel5_20': x.rolling(5, min_periods=5).mean() - x.shift(5).rolling(15, min_periods=15).mean(),
            'persistence20': positive.rolling(20, min_periods=20).mean(),
            'efficiency20': sum20 / x.abs().rolling(20, min_periods=20).sum().replace(0, np.nan)}


def forward_returns(r: pd.DataFrame, h: int) -> pd.DataFrame:
    if isinstance(h, bool) or not isinstance(h, int) or h <= 0:
        raise ValueError('POSITIVE_INTEGER_HORIZON_REQUIRED')
    if (r <= -1).any().any():
        raise ValueError('LOG_RETURN_UNDEFINED')
    # At t this is the product of returns on t+1 through t+h, not t.
    return np.expm1(np.log1p(r).rolling(h, min_periods=h).sum().shift(-h))


def cs_ic(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    if x.shape != y.shape or x.ndim != 2:
        raise ValueError('IC_SHAPE')
    a, b = rankdata(x, axis=1), rankdata(y, axis=1)
    a, b = a - a.mean(axis=1, keepdims=True), b - b.mean(axis=1, keepdims=True)
    den = np.sqrt((a*a).sum(axis=1) * (b*b).sum(axis=1))
    return np.divide((a*b).sum(axis=1), den, out=np.full(len(x), np.nan), where=den > 0)


def top_mask(x: np.ndarray, k: int = 10) -> np.ndarray:
    if x.ndim != 2 or not np.isfinite(x).all() or not 0 < k <= x.shape[1]:
        raise ValueError('TOP_K_INPUT')
    out = np.zeros_like(x)
    ids = np.argsort(-x, axis=1, kind='stable')[:, :k]
    np.put_along_axis(out, ids, 1.0/k, axis=1)
    return out


def hac_summary(values: np.ndarray, lag: int) -> dict:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return {'n': n, 'mean': None, 'se': None, 'ci95': None, 'p_two_sided': None}
    mu = float(x.mean())
    a = x - mu
    L = min(lag, n - 1)
    v = np.dot(a, a)/n
    for k in range(1, L+1):
        v += 2*(1-k/(L+1))*np.dot(a[k:], a[:-k])/n
    se = float(np.sqrt(max(float(v), 0)/n))
    p = float(2*norm.sf(abs(mu/se))) if se else (1.0 if mu == 0 else 0.0)
    return {'n': n, 'mean': mu, 'se': se, 'ci95': [mu-1.96*se, mu+1.96*se],
            'p_two_sided': p, 'hac_lag': L}


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    result, previous = {}, 0.0
    order = sorted(pvalues, key=pvalues.get)
    for i, key in enumerate(order):
        previous = max(previous, min(1.0, (len(order)-i)*pvalues[key]))
        result[key] = previous
    return result


def common_mask(fs: dict[str, pd.DataFrame], y: pd.DataFrame) -> np.ndarray:
    ok = np.isfinite(y.to_numpy()).all(axis=1)
    for f in fs.values():
        if not f.index.equals(y.index) or not f.columns.equals(y.columns):
            raise ValueError('FEATURE_TARGET_AXES')
        ok &= np.isfinite(f.to_numpy()).all(axis=1)
    return ok


def evaluate(fs: dict[str, pd.DataFrame], r: pd.DataFrame, market: pd.Series, h: int) -> tuple[dict, pd.DataFrame]:
    fwd = forward_returns(r, h)
    bm = forward_returns(market.to_frame('market'), h).iloc[:, 0]
    y = fwd.sub(bm, axis=0)
    ok = common_mask(fs, y) & np.isfinite(bm.to_numpy())
    ids = np.flatnonzero(ok)
    dates = r.index[ids]
    out, daily = {}, pd.DataFrame(index=dates)
    yy = y.to_numpy()[ids]
    future_top = top_mask(yy)
    for name, f in fs.items():
        xx = f.to_numpy()[ids]
        mask = top_mask(xx)
        ic = cs_ic(xx, yy)
        daily[name+'_ic'] = ic
        daily[name+'_top_excess'] = (mask*yy).sum(axis=1)
        daily[name+'_overlap'] = ((mask > 0) & (future_top > 0)).sum(axis=1)/10
        # Frozen initial industry weights, daily-close adverse excursion; no intraday claim.
        worst = np.zeros(len(ids))
        cum = np.ones_like(yy)
        for k in range(1, h+1):
            cum *= 1+r.to_numpy()[ids+k]
            worst = np.minimum(worst, (mask*(cum-1)).sum(axis=1))
        daily[name+'_mae'] = worst
    # Every IC comparison uses the same finite-IC dates for every feature.
    cols = [name+'_ic' for name in fs]
    daily = daily.loc[np.isfinite(daily[cols]).all(axis=1)]
    for period, (start, end) in PERIODS.items():
        d = daily.loc[start:end]
        models = {}
        for name in fs:
            a = d[name+'_ic'].to_numpy()
            delta = a-d['mom60_ic'].to_numpy()
            models[name] = {'ic': hac_summary(a, 2*h), 'delta_ic_vs_mom60': hac_summary(delta, 2*h),
                            'mean_top10_market_excess': float(d[name+'_top_excess'].mean()),
                            'top10_future_overlap': float(d[name+'_overlap'].mean()),
                            'mean_close_mae': float(d[name+'_mae'].mean())}
        if h == 10:
            p = {n: models[n]['delta_ic_vs_mom60']['p_two_sided'] for n in fs if n != 'mom60'}
            adjusted = holm({n: v for n, v in p.items() if v is not None})
            for n, val in adjusted.items():
                models[n]['holm_p_primary_family'] = val
        out[period] = {'dates': len(d), 'first': str(d.index[0].date()) if len(d) else None,
                       'last': str(d.index[-1].date()) if len(d) else None, 'models': models}
    return out, daily


def ridge_walkforward(fs: dict[str, pd.DataFrame], r: pd.DataFrame, market: pd.Series) -> dict:
    y = forward_returns(r, 10).sub(forward_returns(market.to_frame('market'), 10).iloc[:,0], axis=0)
    valid = common_mask(fs, y)
    names = ('mom60', 'mom20', 'accel5_20', 'persistence20', 'efficiency20')
    x = np.stack([rankdata(fs[n].to_numpy(), axis=1)/r.shape[1]-.5 for n in names], axis=2)
    yy = y.to_numpy()
    yy = yy - yy.mean(axis=1, keepdims=True)
    predictions = {n: np.full(r.shape, np.nan) for n in ('baseline', 'challenger')}
    folds = []
    for year in range(2010, 2026):
        boundary = int(np.searchsorted(r.index, pd.Timestamp(year,1,1)))
        pos = np.arange(len(r))
        train = valid & (r.index >= '1990-01-01') & (pos < boundary-20) & (pos+10 < boundary)
        test = valid & (r.index.year == year)
        if not train.any() or not test.any():
            continue
        z = yy[train].ravel()
        beta = {}
        for name, nfeatures in [('baseline',1), ('challenger',5)]:
            xx = x[train,:,:nfeatures].reshape(-1,nfeatures)
            b = np.linalg.solve(xx.T@xx/len(z)+np.eye(nfeatures), xx.T@z/len(z))
            predictions[name][test] = x[test,:,:nfeatures]@b
            beta[name] = b.tolist()
        last = np.flatnonzero(train)[-1]
        folds.append({'test_year': year, 'training_dates': int(train.sum()),
                      'last_training_signal': str(r.index[last].date()),
                      'last_training_outcome': str(r.index[last+10].date()),
                      'first_test': str(r.index[np.flatnonzero(test)[0]].date()), 'coefficients': beta})
    ok = np.isfinite(predictions['baseline']).all(axis=1) & np.isfinite(predictions['challenger']).all(axis=1)
    a, b = cs_ic(predictions['baseline'][ok], yy[ok]), cs_ic(predictions['challenger'][ok], yy[ok])
    d = pd.DataFrame({'baseline_ic':a,'challenger_ic':b,'delta':b-a}, index=r.index[ok])
    return {'ridge_penalty_normalized_gram': 1.0, 'folds': folds,
            'metrics': {name: {k: hac_summary(d.loc[start:end,k].to_numpy(),20) for k in d}
                        for name,(start,end) in PERIODS.items() if name != 'development'}}


def book(r: np.ndarray, rf: np.ndarray, target: np.ndarray, bps: float) -> dict:
    """Signal close t -> target at close t+1 -> first earned return t+2.

    Proportional buy/sell costs are solved against post-cost target holdings.
    Complete return matrix is mandatory; initial cash and final liquidation explicit.
    """
    if r.shape != target.shape or len(rf) != len(r) or not np.isfinite(r).all() or not np.isfinite(rf).all():
        raise ValueError('BOOK_DATA')
    if not np.isfinite(target).all() or (target < 0).any() or not np.allclose(target.sum(axis=1),1):
        raise ValueError('BOOK_TARGET')
    if bps < 0 or bps > 1000 or (r <= -1).any():
        raise ValueError('BOOK_BASIS')
    weights = np.zeros(r.shape[1]); cash = 1.0; wealth = 1.0
    path, traded, dollar_traded = [], 0.0, 0.0
    c = bps/10000
    for t in range(len(r)):
        g = float(weights@(1+r[t]) + cash*(1+rf[t]))
        before = weights*(1+r[t])/g
        prewealth = wealth*g
        desired = target[t-1] if 0 < t < len(r)-1 else np.zeros(r.shape[1])
        x = 1.0
        for _ in range(60):
            nx = 1-c*float(np.abs(x*desired-before).sum())
            if abs(nx-x) < 1e-14:
                x = nx; break
            x = nx
        turn = float(np.abs(x*desired-before).sum())
        wealth = prewealth*x
        weights = desired.copy(); cash = 1-float(weights.sum())
        traded += turn; dollar_traded += prewealth*turn
        path.append(wealth)
    equity = np.array([1.0]+path)
    returns = equity[1:]/equity[:-1]-1
    dd = equity/np.maximum.accumulate(equity)-1
    return {'days': len(r), 'terminal_wealth': wealth, 'cagr': float(wealth**(252/len(r))-1),
            'annual_volatility': float(np.std(returns,ddof=1)*np.sqrt(252)),
            'max_drawdown': float(dd.min()), 'annual_gross_turnover': traded*252/len(r),
            'gross_traded_notional_per_initial_wealth': dollar_traded, 'cost_bps': bps}


def run(industry_zip: Path, factors_zip: Path) -> dict:
    r, im = load_zip(industry_zip, 'Average Value Weighted Returns -- Daily',49)
    ff, fm = load_zip(factors_zip,'Mkt-RF',4)
    r = r.loc['1988-01-01':'2025-12-31'].sort_index(axis=1)
    ff = ff.loc[r.index[0]:r.index[-1]]
    if not r.index.equals(ff.index):
        raise ValueError('PROVIDER_CALENDAR_MISMATCH')
    market, rf = ff['Mkt-RF']+ff['RF'], ff['RF']
    fs = features(r,market)
    horizons = {str(h): evaluate(fs,r,market,h)[0] for h in (5,10,20)}
    nested = ridge_walkforward(fs,r,market)
    # The book uses common-feature dates, not a model-specific population.
    valid = common_mask(fs,r) & (r.index >= '1990-01-01')
    rr, ff_rf = r.loc[valid], rf.loc[valid]
    if not rr.index.equals(r.loc['1990-01-01':].index):
        raise ValueError('BOOK_CALENDAR_GAP_REQUIRES_DISCLOSED_HANDLING')
    portfolios = {}
    for period,(start,end) in PERIODS.items():
        mask = (rr.index >= start)&(rr.index <= end)
        rets = rr.loc[mask].to_numpy(); rates = ff_rf.loc[mask].to_numpy()
        portfolios[period] = {}
        for name in fs:
            target = top_mask(fs[name].loc[rr.index[mask]].to_numpy())
            portfolios[period][name] = {str(c):book(rets,rates,target,c) for c in (0,5,10,25)}
        target = np.full_like(rets,1/rets.shape[1])
        portfolios[period]['equal49'] = {str(c):book(rets,rates,target,c) for c in (0,10)}
        m = market.loc[rr.index[mask]].to_numpy()[:,None]
        portfolios[period]['market'] = {'0':book(m,rates,np.ones_like(m),0)}
    # Prespecified shuffle diagnostic, not a tuning criterion or calibrated p-value.
    y = forward_returns(r,10).sub(forward_returns(market.to_frame('m'),10).iloc[:,0],axis=0)
    ok = common_mask(fs,y)&(r.index >= '2016-01-01')
    x, yy = fs['mom60'].to_numpy()[ok], y.to_numpy()[ok]
    rng = np.random.default_rng(20261002)
    controls = [float(np.nanmean(cs_ic(x, np.take_along_axis(yy,np.argsort(rng.random(yy.shape),axis=1),axis=1)))) for _ in range(25)]
    return {'schema':'mastermind.public_industry_reference.v1', 'authority':CAPS,
            'data':{'industries':im,'factors':fm,'used_start':str(r.index[0].date()),
                    'used_end':str(r.index[-1].date()),'industry_count':len(r.columns),
                    'industry_names':list(r.columns),'missing_cells':int(r.isna().sum().sum())},
            'horizons':horizons, 'ridge':nested, 'portfolios':portfolios,
            'shuffle_control':{'repetitions':25,'mean_ic':float(np.mean(controls)),
                               'min_ic':min(controls),'max_ic':max(controls),'seed':20261002},
            'limitations':['Current provider-revised vintage; not historical capture or PIT microtheme proof.',
                           'No issuer breadth, fundamental, social, economic-exposure or institutional-flow test.',
                           'Hypothetical industry portfolio exposures, not available tradable products.',
                           'Costs are scenario assumptions, not constituent execution or capacity estimates.',
                           'Daily-close adverse excursion excludes intraday path and gaps before execution.',
                           'No production promotion or trading authority.']}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('industries',type=Path); p.add_argument('factors',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=run(args.industries,args.factors)
    result['code_sha256']=digest(Path(__file__).read_bytes())
    result['environment']={'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(args.output),'sha256':digest(args.output.read_bytes()),
                      'industry_dates':result['data'],'primary_evaluation':result['horizons']['10']['evaluation'],
                      'ridge_evaluation':result['ridge']['metrics']['evaluation'],
                      'shuffle':result['shuffle_control']},indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
