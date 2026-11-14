"""Feature-only regime measurement audit, not a return-prediction trial.
Fixed design before these feature diagnostics are read: pre-2003 French49,
monthly decisions, 252-session intercept/beta fit ending t-21, latest21 log
returns, >=20 eligible industries. High state exceeds the prior120 monthly
80th percentile, all120 months required. Compare state overlap and exact
variance identity; inspect no future outcome. No claim to identify fund flows.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pilot


def main() -> None:
    r, ri = pilot.download('industries')
    ff, fi = pilot.download('factors')
    assert ri['download_sha256'] == 'b9d36d571e968d71f7b03207e7fed6398554f953719b8c1bf3ee3ad8d00e7520'
    assert fi['download_sha256'] == '96c23b88e651cbfff3740a53f8225e59ee39893371e96385a1d8125ec2cd9c89'
    dates = r.index.intersection(ff.index)
    y = np.log1p(r.loc[dates]).to_numpy()
    x = np.log1p((ff['Mkt-RF'] + ff['RF']).loc[dates]).to_numpy()
    month_ends = pd.Series(np.arange(len(dates)), index=dates).groupby(dates.to_period('M')).last()
    rows = []
    max_identity_error = 0.0
    for t in month_ends.to_numpy():
        if t < 272:
            continue
        train_y, train_x = y[t-272:t-20], x[t-272:t-20]
        new_y, new_x = y[t-20:t+1], x[t-20:t+1]
        good = np.isfinite(train_y).all(axis=0) & np.isfinite(new_y).all(axis=0)
        if good.sum() < 20 or not np.isfinite(train_x).all() or not np.isfinite(new_x).all():
            continue
        ty, ny = train_y[:, good], new_y[:, good]
        dx = train_x - train_x.mean()
        denom = float(dx @ dx)
        if denom <= 0:
            continue
        beta = (dx[:, None] * (ty - ty.mean(axis=0))).sum(axis=0) / denom
        alpha = ty.mean(axis=0) - beta * train_x.mean()
        ret = ny.sum(axis=0)
        market = float(new_x.sum())
        rel = ret - market
        residual = ret - (21 * alpha + beta * market)
        # Exact identity absorbs the intercept in e. This is not a causal attribution.
        e = ret - beta * market
        raw_var = float(np.var(ret, ddof=0))
        beta_component = float(market ** 2 * np.var(beta, ddof=0))
        e_component = float(np.var(e, ddof=0))
        cross = float(2 * market * np.mean((beta - beta.mean()) * (e - e.mean())))
        err = abs(raw_var - beta_component - e_component - cross)
        max_identity_error = max(max_identity_error, err)
        np.testing.assert_allclose(np.std(rel, ddof=0), np.std(ret, ddof=0), rtol=1e-12, atol=1e-14)
        np.testing.assert_allclose(raw_var, beta_component + e_component + cross, rtol=1e-10, atol=1e-14)
        rows.append({'month': str(dates[t].to_period('M')), 'n_industries': int(good.sum()),
            'raw_dispersion': float(np.sqrt(raw_var)),
            'beta_adjusted_dispersion': float(np.std(residual, ddof=0)),
            'market_log21': market, 'abs_market_log21': abs(market),
            'beta_variance_term': beta_component, 'residual_variance_term': e_component,
            'covariance_term': cross})
    df = pd.DataFrame(rows).set_index('month')
    full_months = pd.period_range(df.index.min(), df.index.max(), freq='M').astype(str)
    df = df.reindex(full_months)
    for source, prefix in [('raw_dispersion', 'raw'), ('beta_adjusted_dispersion', 'adjusted')]:
        df[prefix + '_threshold'] = df[source].shift(1).rolling(120, min_periods=120).quantile(.8)
    eligible = df.dropna().copy()
    eligible['raw_high'] = eligible.raw_dispersion > eligible.raw_threshold
    eligible['adjusted_high'] = eligible.beta_adjusted_dispersion > eligible.adjusted_threshold
    counts = {f'raw_{int(a)}_adjusted_{int(b)}': int(((eligible.raw_high == a) & (eligible.adjusted_high == b)).sum())
              for a in [False, True] for b in [False, True]}
    raw_n = int(eligible.raw_high.sum())
    adj_n = int(eligible.adjusted_high.sum())
    both = int((eligible.raw_high & eligible.adjusted_high).sum())
    groups = {}
    for a in [False, True]:
        for b in [False, True]:
            g = eligible[(eligible.raw_high == a) & (eligible.adjusted_high == b)]
            groups[f'raw_{int(a)}_adjusted_{int(b)}'] = {'months': len(g),
                'mean_abs_market_log21': float(g.abs_market_log21.mean()),
                'median_abs_market_log21': float(g.abs_market_log21.median()),
                'mean_raw_dispersion': float(g.raw_dispersion.mean()),
                'mean_adjusted_dispersion': float(g.beta_adjusted_dispersion.mean())}
    # Demonstrate known-time threshold calculation cannot use later feature values.
    cut = eligible.index[len(eligible) // 2]
    p = df.loc[:cut, 'raw_dispersion'].shift(1).rolling(120, min_periods=120).quantile(.8)
    np.testing.assert_allclose(p.iloc[-1], df.loc[cut, 'raw_threshold'], rtol=0, atol=0)
    result = {'status': 'FEATURE_ONLY_AUDIT_NOT_RETURN_TEST',
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'cutoff': '2002-12-31', 'numeric_future_outcomes_read': False,
        'first_eligible_month': str(eligible.index.min()), 'last_eligible_month': str(eligible.index.max()),
        'eligible_months': len(eligible), 'counts': counts,
        'raw_high_months': raw_n, 'adjusted_high_months': adj_n, 'both_high_months': both,
        'raw_high_not_adjusted_high_share': (raw_n - both) / raw_n,
        'adjusted_high_not_raw_high_share': (adj_n - both) / adj_n,
        'raw_adjusted_pearson': float(eligible.raw_dispersion.corr(eligible.beta_adjusted_dispersion)),
        'raw_adjusted_spearman': float(eligible.raw_dispersion.corr(eligible.beta_adjusted_dispersion, method='spearman')),
        'variance_identity_max_abs_error': max_identity_error,
        'prefix_threshold_check_month': str(cut), 'group_diagnostics': groups,
        'limitations': ['Return-regression residuals include omitted factors, alpha estimation error and news.',
            'Neither measure identifies fund flows, causal sector rotation, or a profitable gate.',
            'Both measures are across industry portfolios, not within-sector single-stock dispersion.',
            'High thresholds are predetermined conventions, not calibrated optimal regime boundaries.',
            'No future trade outcome was evaluated; no claim that adjusted dispersion predicts better.',
            'Current-vintage French data, not original-vintage archives.']}
    out = Path(__file__).with_name('DISPERSION_AUDIT_RESULTS.json')
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result))
    print('RESULT_SHA256', hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
