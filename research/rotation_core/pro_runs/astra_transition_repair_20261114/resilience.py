"""Adaptive pre-2003 exploratory follow-up. See FOLLOWUP_PROTOCOL.md.
Not a proprietary-dot test, not untouched confirmation, not a live strategy.
Run beside pilot.py: python resilience.py --out RESILIENCE_RESULTS.json
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pilot


def exposure_features(y: np.ndarray, x: np.ndarray, t: int) -> dict | None:
    if t < 272:
        return None
    train_y, train_x = y[t-272:t-20], x[t-272:t-20]
    new_y, new_x = y[t-20:t+1], x[t-20:t+1]
    assert len(train_y) == 252 and len(new_y) == 21
    if not all(np.isfinite(a).all() for a in [train_y, train_x, new_y, new_x]):
        return None
    dx = train_x - train_x.mean()
    denominator = float(dx @ dx)
    if denominator <= 0:
        return None
    beta = float(dx @ (train_y - train_y.mean()) / denominator)
    alpha = float(train_y.mean() - beta * train_x.mean())
    training_residual = train_y - alpha - beta * train_x
    sigma = float(np.std(training_residual, ddof=2))
    neg, pos = new_x < 0, new_x > 0
    if neg.sum() < 5 or pos.sum() < 5 or not np.isfinite(sigma) or sigma <= 0:
        return None
    residual = new_y - alpha - beta * new_x
    down_score = float(residual[neg].mean() / sigma)
    up_score = float(residual[pos].mean() / sigma)
    return {'beta': beta, 'down_score': down_score, 'up_score': up_score,
            'S': int(down_score > 0), 'U': int(up_score > 0), 'B': int(beta >= 1),
            'M': int(x[t-62:t+1].sum() < 0), 'r21': float(new_y.sum()),
            'negative_days': int(neg.sum()), 'positive_days': int(pos.sum())}


def match(df: pd.DataFrame, months: pd.PeriodIndex, weights: np.ndarray) -> dict:
    cols = ['sigma63', 'drawdown126', 'distance21low', 'relative126', 'r21', 'beta']
    x = df[cols].copy()
    x['sigma63'] = np.log(x['sigma63'])
    sd = x.std()
    if (sd <= 0).any():
        raise ValueError('Degenerate matching feature')
    z = (x - x.mean()) / sd
    pairs = []
    for _, group in df.groupby(['month', 'R']):
        a = group.index[group.S.eq(1)].to_numpy()
        b = group.index[group.S.eq(0)].to_numpy()
        if not len(a) or not len(b):
            continue
        distance = np.sqrt(((z.loc[a].to_numpy()[:, None] - z.loc[b].to_numpy()[None]) ** 2).sum(axis=2))
        for i, ai in enumerate(a):
            j = int(np.argmin(distance[i]))
            if distance[i, j] <= 1.0:
                pairs.append((int(ai), int(b[j]), float(distance[i, j])))
    out = {}
    for subset in ['all', 'R_only']:
        pp = pairs if subset == 'all' else [p for p in pairs if df.loc[p[0], 'R'] == 1]
        if not pp:
            out[subset] = {'pairs': 0}
            continue
        aa, bb = [p[0] for p in pp], [p[1] for p in pp]
        diff = df.loc[aa, pilot.METRICS].reset_index(drop=True) - df.loc[bb, pilot.METRICS].reset_index(drop=True)
        diff['month'] = df.loc[aa, 'month'].to_numpy()
        ss, nn = pilot.aggregates(diff, months)
        denominator = weights @ nn
        good = denominator > 0
        boots = (weights[good] @ ss) / denominator[good, None]
        eligible = df.S.eq(1) if subset == 'all' else df.S.eq(1) & df.R.eq(1)
        out[subset] = {'pairs': len(pp), 'months': int(diff.month.nunique()),
            'unique_controls': len(set(bb)), 'retention': len(pp) / int(eligible.sum()),
            'mean_distance': float(np.mean([p[2] for p in pp])),
            'balance_standardized': ((x.loc[aa].mean() - x.loc[bb].mean()) / sd).to_dict(),
            'positive': pilot.summarize(df.loc[aa]), 'negative': pilot.summarize(df.loc[bb]),
            'delta': {k: {'estimate': float(diff[k].mean()),
                         'ci95': np.quantile(boots[:, j], [.025, .975]).tolist()}
                      for j, k in enumerate(pilot.METRICS)}}
    return out


def run(out: Path) -> None:
    r, ri = pilot.download('industries')
    ff, fi = pilot.download('factors')
    expected = {'industries': 'b9d36d571e968d71f7b03207e7fed6398554f953719b8c1bf3ee3ad8d00e7520',
                'factors': '96c23b88e651cbfff3740a53f8225e59ee39893371e96385a1d8125ec2cd9c89'}
    assert ri['download_sha256'] == expected['industries']
    assert fi['download_sha256'] == expected['factors']
    idx = r.index.intersection(ff.index)
    r = r.loc[idx]
    market = (ff['Mkt-RF'] + ff['RF']).loc[idx]
    f = pilot.features(r, market)
    events, base_exclusions = pilot.build_events(r, market, f, lag=1)
    lr, lm = f['lr'].to_numpy(), f['lm'].to_numpy()
    assert len(events) == 8902
    retained = []
    prefix_checks = 0
    for i, row in events.iterrows():
        t = int(r.index.get_loc(pd.Timestamp(row.date)))
        g = int(r.columns.get_loc(row.industry))
        item = exposure_features(lr[:, g], lm, t)
        if item is None:
            continue
        if i % 251 == 0:
            prefix = exposure_features(lr[:t+1, g], lm[:t+1], t)
            assert prefix is not None
            for k in item:
                np.testing.assert_allclose(item[k], prefix[k], rtol=0, atol=0)
            prefix_checks += 1
        retained.append({**row.to_dict(), **item})
    df = pd.DataFrame(retained).reset_index(drop=True)
    assert not df.duplicated(['date', 'industry']).any()
    assert prefix_checks > 0
    months = pd.period_range(df.month.min(), df.month.max(), freq='M')
    weights = pilot.block_weights(months)
    comp = {
        'S_within_R_primary': pilot.contrast(df, df.S.eq(1) & df.R.eq(1), df.S.eq(0) & df.R.eq(1), months, weights),
        'S_all_secondary': pilot.contrast(df, df.S.eq(1), df.S.eq(0), months, weights),
        'U_within_R_comparator': pilot.contrast(df, df.U.eq(1) & df.R.eq(1), df.U.eq(0) & df.R.eq(1), months, weights),
    }
    cells = {f'S{s}_R{rr}_M{m}': pilot.summarize(df[(df.S == s) & (df.R == rr) & (df.M == m)])
             for s in [0, 1] for rr in [0, 1] for m in [0, 1]}
    beta_cells = {f'S{s}_B{b}': pilot.summarize(df[(df.S == s) & (df.B == b) & (df.R == 1)])
                  for s in [0, 1] for b in [0, 1]}
    eras = {}
    for lo, hi in [(1927, 1962), (1963, 1982), (1983, 2002)]:
        eras[f'{lo}_{hi}'] = {str(s): pilot.summarize(df[df.year.between(lo, hi) & df.R.eq(1) & df.S.eq(s)]) for s in [0, 1]}
    matched = match(df, months, weights)
    result = {'status': 'ADAPTIVE_EXPLORATORY_NO_NEW_HOLDOUT', 'inputs': {'industries': ri, 'factors': fi},
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'pilot_code_sha256': hashlib.sha256(Path(pilot.__file__).read_bytes()).hexdigest(),
        'events_base': len(events), 'events_retained': len(df), 'months': int(df.month.nunique()),
        'feature_exclusions': len(events) - len(df), 'base_exclusions': base_exclusions,
        'prefix_checks': prefix_checks, 'primary_and_secondary': comp, 'full_cells': cells,
        'beta_cells_within_R': beta_cells, 'eras_within_R': eras, 'matching': matched,
        'limitations': ['Already-examined exploratory pre-2003 outcomes; not untouched confirmation.',
            'Industry-level return proxies, not stock-level dots or fundamental DNA.',
            'Unadjusted dependent comparisons; same-month matching is imperfect and not causal.',
            'Missing fundamentals, true flows, actual economic peers and point-in-time macro shocks.']}
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print('SAVED', str(out), hashlib.sha256(out.read_bytes()).hexdigest())
    print('COUNTS', len(df), df.month.nunique(), 'PREFIX', prefix_checks)
    for name, v in comp.items():
        print(name, json.dumps({k: v['delta'][k] for k in ['bad10', 'excess63', 'win', 'lower_first']}))
        print('CELLS', name, json.dumps({k: v[k] for k in ['positive', 'negative']}))
    print('MATCH_R', json.dumps(matched['R_only']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('RESILIENCE_RESULTS.json'))
    run(parser.parse_args().out)
