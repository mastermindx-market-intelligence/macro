"""Exploratory mechanism pilot; NOT a dot backtest or deployable strategy.
See PROTOCOL.md. Raw vendor data stays in memory, never in output files.
Python 3.10+, numpy and pandas. Run: python pilot.py --out RESULTS.json
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

CUTOFF = 20021231
SEED = 20261114
REPS = 2000
COST = 0.002
URLS = {
    'industries': 'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_daily_CSV.zip',
    'factors': 'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip',
}
METRICS = ['win', 'bad10', 'net63', 'excess63', 'net21', 'mae63', 'upper_first', 'lower_first', 'unresolved']


def parse_first_daily_table(text: str) -> pd.DataFrame:
    """Discard later dates as strings BEFORE numerical value parsing."""
    header = None
    rows: list[str] = []
    started = False
    for line in text.splitlines():
        line = line.strip()
        token = line.split(',')[0].strip()
        is_date = len(token) == 8 and token.isdigit()
        if is_date:
            started = True
            if int(token) <= CUTOFF:
                rows.append(line)
        elif started:
            break
        elif line.startswith(','):
            header = line
    if not rows or header is None:
        raise ValueError('No first daily table found')
    df = pd.read_csv(io.StringIO(header + '\n' + '\n'.join(rows)), index_col=0)
    df.index = pd.to_datetime(df.index.astype(str), format='%Y%m%d')
    df.columns = [str(c).strip() for c in df.columns]
    df = df.replace([-99.99, -999.0], np.nan).astype(float) / 100.0
    assert df.index.is_unique and df.index.is_monotonic_increasing
    assert df.index.max() <= pd.Timestamp('2002-12-31')
    assert (df.dropna(how='all').min().dropna() > -1).all()
    return df


def download(name: str) -> tuple[pd.DataFrame, dict]:
    request = urllib.request.Request(URLS[name], headers={'User-Agent': 'Research replication'})
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = response.read()
    z = zipfile.ZipFile(io.BytesIO(payload))
    names = [n for n in z.namelist() if n.lower().endswith('.csv')]
    if len(names) != 1:
        raise ValueError('Unexpected archive members')
    text = z.read(names[0]).decode('utf-8-sig')
    df = parse_first_daily_table(text)
    meta = {'url': URLS[name], 'download_sha256': hashlib.sha256(payload).hexdigest(),
            'archive_bytes': len(payload), 'archive_member': names[0],
            'header': text.splitlines()[0], 'parsed_first': str(df.index.min().date()),
            'parsed_last': str(df.index.max().date()), 'parsed_rows': len(df),
            'parsed_csv_sha256': hashlib.sha256(df.to_csv().encode()).hexdigest()}
    return df, meta


def features(r: pd.DataFrame, market: pd.Series) -> dict:
    lr = np.log1p(r)
    lm = np.log1p(market)
    p = lr.cumsum()
    r21 = lr.rolling(21, min_periods=21).sum()
    r126 = lr.rolling(126, min_periods=126).sum()
    m21 = lm.rolling(21, min_periods=21).sum()
    m126 = lm.rolling(126, min_periods=126).sum()
    leader = lr.rolling(231, min_periods=231).sum().shift(22)
    leader = leader.sub(lm.rolling(231, min_periods=231).sum().shift(22), axis=0)
    return {'lr': lr, 'lm': lm, 'p': p, 'r21': r21,
            'relative21': r21.sub(m21, axis=0),
            'relative126': r126.sub(m126, axis=0),
            'drawdown126': np.expm1(p - p.rolling(126, min_periods=126).max()),
            'distance21low': p - p.rolling(21, min_periods=21).min(),
            'sigma63': lr.rolling(63, min_periods=63).std(),
            'history_ok': r.rolling(253, min_periods=253).count().eq(253),
            'leader': leader,
            'vol21': lm.rolling(21, min_periods=21).std(),
            'vol63': lm.rolling(63, min_periods=63).std()}


def build_events(r: pd.DataFrame, market: pd.Series, f: dict, lag: int) -> tuple[pd.DataFrame, dict]:
    month_end = pd.Series(np.arange(len(r)), index=r.index).groupby(r.index.to_period('M')).last()
    records = []
    excluded = {'candidate_before_future_check': 0, 'incomplete_future': 0, 'missing_forward': 0,
                'insufficient_donor_universe': 0}
    lr = f['lr'].to_numpy()
    lm = f['lm'].to_numpy()
    for t in month_end.to_numpy():
        current = f['history_ok'].iloc[t] & (f['relative126'].iloc[t] < 0) & (f['drawdown126'].iloc[t] <= -0.10)
        for g in np.flatnonzero(current.to_numpy()):
            excluded['candidate_before_future_check'] += 1
            e = t + lag
            if e + 63 >= len(r):
                excluded['incomplete_future'] += 1
                continue
            if not (np.isfinite(lr[t:e+64, g]).all() and np.isfinite(lm[t:e+64]).all()):
                excluded['missing_forward'] += 1
                continue
            leader = f['leader'].iloc[t].copy()
            leader.iloc[g] = np.nan
            valid = leader.dropna().sort_values(ascending=False, kind='stable')
            if len(valid) < 20:
                excluded['insufficient_donor_universe'] += 1
                continue
            leaders = valid.index[:math.ceil(len(valid) / 3)]
            donor_returns = f['relative21'].iloc[t].reindex(leaders)
            if donor_returns.isna().any():
                excluded['insufficient_donor_universe'] += 1
                continue
            # Exclude the return into entry close, then include exactly 63 future sessions.
            path = np.cumsum(lr[e+1:e+64, g])
            market_path = np.cumsum(lm[e+1:e+64])
            sig = float(f['sigma63'].iloc[t, g])
            barrier = 2 * sig * math.sqrt(21)
            if not np.isfinite(barrier) or barrier <= 0:
                raise ValueError('Invalid barrier')
            up = np.flatnonzero(path >= barrier)
            down = np.flatnonzero(path <= -barrier)
            first_up = int(up[0]) if len(up) else 64
            first_down = int(down[0]) if len(down) else 64
            net63 = float(np.expm1(path[-1]) - COST)
            mae = float(min(0.0, np.expm1(path).min()))
            date = r.index[t]
            records.append({'date': str(date.date()), 'month': str(date.to_period('M')),
                'industry': r.columns[g], 'year': int(date.year),
                'R': int(f['r21'].iloc[t, g] > 0 and f['relative21'].iloc[t, g] > 0),
                'D': int(donor_returns.mean() < 0), 'V': int(f['vol21'].iloc[t] < f['vol63'].iloc[t]),
                'donor_n': len(leaders), 'sigma63': sig,
                'drawdown126': float(f['drawdown126'].iloc[t, g]),
                'distance21low': float(f['distance21low'].iloc[t, g]),
                'relative126': float(f['relative126'].iloc[t, g]),
                'win': float(net63 > 0), 'bad10': float(mae <= -0.10), 'net63': net63,
                'excess63': float(net63 - np.expm1(market_path[-1])),
                'net21': float(np.expm1(path[20]) - COST), 'mae63': mae,
                'upper_first': float(first_up < first_down), 'lower_first': float(first_down < first_up),
                'unresolved': float(first_up == first_down)})
    out = pd.DataFrame.from_records(records)
    assert not out.duplicated(['date', 'industry']).any()
    assert np.allclose(out[['upper_first', 'lower_first', 'unresolved']].sum(axis=1), 1)
    return out, excluded


def summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {'n': 0, 'months': 0}
    return {'n': len(df), 'months': int(df.month.nunique()),
            **{k: float(df[k].mean()) for k in METRICS}}


def block_weights(months: pd.PeriodIndex) -> np.ndarray:
    rng = np.random.default_rng(SEED)
    n = len(months)
    size = 12
    weights = np.zeros((REPS, n), dtype=np.int16)
    for i in range(REPS):
        starts = rng.integers(0, n - size + 1, size=math.ceil(n / size))
        idx = (starts[:, None] + np.arange(size)[None, :]).ravel()[:n]
        weights[i] = np.bincount(idx, minlength=n)
    return weights


def aggregates(df: pd.DataFrame, months: pd.PeriodIndex) -> tuple[np.ndarray, np.ndarray]:
    sums = df.groupby('month')[METRICS].sum().reindex(months.astype(str), fill_value=0)
    counts = df.groupby('month').size().reindex(months.astype(str), fill_value=0)
    return sums.to_numpy(), counts.to_numpy()


def contrast(df: pd.DataFrame, pos: np.ndarray, neg: np.ndarray,
             months: pd.PeriodIndex, weights: np.ndarray) -> dict:
    a, b = df.loc[pos], df.loc[neg]
    sa, na = aggregates(a, months)
    sb, nb = aggregates(b, months)
    wa, wb = weights @ na, weights @ nb
    valid = (wa > 0) & (wb > 0)
    boots = (weights[valid] @ sa) / wa[valid, None] - (weights[valid] @ sb) / wb[valid, None]
    return {'positive': summarize(a), 'negative': summarize(b),
            'delta': {k: {'estimate': float(a[k].mean() - b[k].mean()),
                         'ci95': np.quantile(boots[:, j], [0.025, 0.975]).tolist()}
                      for j, k in enumerate(METRICS)}, 'valid_bootstrap_reps': int(valid.sum())}


def matched_diagnostic(df: pd.DataFrame, months: pd.PeriodIndex, weights: np.ndarray) -> dict:
    """Declared robustness only: same-month nearest geometry match, with replacement.
    Standardize features without using labels. Caliper = 1 Euclidean SD unit.
    Reports descriptive balance and retention; not causal identification.
    """
    cols = ['sigma63', 'drawdown126', 'distance21low', 'relative126']
    x = df[cols].copy()
    x['sigma63'] = np.log(x['sigma63'])
    sd = x.std().replace(0, np.nan)
    z = (x - x.mean()) / sd
    pairs = []
    for _, group in df.groupby('month'):
        a = group.index[group.R.eq(1)].to_numpy()
        b = group.index[group.R.eq(0)].to_numpy()
        if not len(a) or not len(b):
            continue
        distances = np.sqrt(((z.loc[a].to_numpy()[:, None, :] - z.loc[b].to_numpy()[None, :, :]) ** 2).sum(axis=2))
        for i, index in enumerate(a):
            j = int(np.argmin(distances[i]))
            if distances[i, j] <= 1.0:
                pairs.append((int(index), int(b[j]), float(distances[i, j])))
    if not pairs:
        return {'pairs': 0}
    aa, bb = [p[0] for p in pairs], [p[1] for p in pairs]
    diff = df.loc[aa, METRICS].reset_index(drop=True) - df.loc[bb, METRICS].reset_index(drop=True)
    diff['month'] = df.loc[aa, 'month'].to_numpy()
    ss, nn = aggregates(diff, months)
    den = weights @ nn
    valid = den > 0
    boots = (weights[valid] @ ss) / den[valid, None]
    return {'pairs': len(pairs), 'months': int(diff.month.nunique()), 'unique_controls': len(set(bb)),
            'treated_retention': len(pairs) / int(df.R.sum()),
            'mean_match_distance': float(np.mean([p[2] for p in pairs])),
            'balance_after_standardized_difference': ((x.loc[aa].mean() - x.loc[bb].mean()) / sd).to_dict(),
            'positive': summarize(df.loc[aa]), 'negative': summarize(df.loc[bb]),
            'delta': {k: {'estimate': float(diff[k].mean()),
                         'ci95': np.quantile(boots[:, j], [0.025, 0.975]).tolist()}
                      for j, k in enumerate(METRICS)}}


def run(out: Path) -> dict:
    synthetic = ',A\n19991231,1.0\n20000103,-99.99\n20030101,NOT_A_NUMBER\n\n'
    parsed = parse_first_daily_table(synthetic)
    assert len(parsed) == 2 and parsed.iloc[0, 0] == .01 and pd.isna(parsed.iloc[1, 0])
    r, ri = download('industries')
    ff, fi = download('factors')
    idx = r.index.intersection(ff.index)
    r = r.loc[idx]
    market = (ff['Mkt-RF'] + ff['RF']).loc[idx]
    if market.isna().any():
        raise ValueError('Missing market returns')
    f = features(r, market)
    checked = []
    for date in ['1950-12-29', '1982-12-31', '2001-12-31']:
        prefix_r = r.loc[:date]
        prefix = features(prefix_r, market.loc[prefix_r.index])
        t = prefix_r.index[-1]
        for name in f:
            np.testing.assert_allclose(np.asarray(f[name].loc[t], dtype=float),
                                       np.asarray(prefix[name].loc[t], dtype=float), equal_nan=True)
        checked.append(str(t.date()))
    events, excluded = build_events(r, market, f, lag=1)
    sensitivity, excluded2 = build_events(r, market, f, lag=2)
    months = pd.period_range(events.month.min(), events.month.max(), freq='M')
    weights = block_weights(months)
    compare = {
        'R_repair_vs_no_repair': contrast(events, events.R.eq(1), events.R.eq(0), months, weights),
        'D_incremental_within_R': contrast(events, events.R.eq(1) & events.D.eq(1), events.R.eq(1) & events.D.eq(0), months, weights),
        'V_incremental_within_R': contrast(events, events.R.eq(1) & events.V.eq(1), events.R.eq(1) & events.V.eq(0), months, weights),
    }
    cells = {f'R{rr}_D{dd}_V{vv}': summarize(events[(events.R == rr) & (events.D == dd) & (events.V == vv)])
             for rr in [0, 1] for dd in [0, 1] for vv in [0, 1]}
    eras = {}
    for lo, hi in [(1927, 1962), (1963, 1982), (1983, 2002)]:
        era = events[events.year.between(lo, hi)]
        eras[f'{lo}_{hi}'] = {str(k): summarize(g) for k, g in era.groupby('R')}
    # Consecutive eligible months per industry are spells, not independent trials.
    temp = events.sort_values(['industry', 'month']).copy()
    temp['ord'] = pd.PeriodIndex(temp.month, freq='M').asi8
    temp['new_spell'] = temp.groupby('industry')['ord'].diff().ne(1)
    result = {'status': 'EXPLORATORY_NOT_DOT_VALIDATION',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'cutoff': CUTOFF,
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'inputs': {'industries': ri, 'factors': fi},
        'unit_checks': {'cutoff_before_numeric_parse': True, 'percent_conversion': True,
                        'missing_sentinel': True, 'prefix_invariance_dates': checked,
                        'unique_event_keys': True, 'barrier_partition': True},
        'all': summarize(events), 'first_event': events.date.min(), 'last_event': events.date.max(),
        'eligible_industry_spells': int(temp.new_spell.sum()), 'exclusions': excluded,
        'primary_contrasts': compare, 'full_cells': cells, 'eras': eras,
        'matched_R_robustness': matched_diagnostic(events, months, weights),
        'two_session_delay': {'all': summarize(sensitivity), 'R_cells': {str(k): summarize(g) for k, g in sensitivity.groupby('R')},
                              'exclusions': excluded2},
        'limitations': ['Current-vintage industry histories, not original historical vintages.',
            'Industry portfolios, not single stocks or proprietary dot/tier signals.',
            'Observational association; overlapping horizons and correlated industries.',
            'Bootstrap intervals are descriptive and not multiplicity-adjusted.',
            'Event averages are not portfolio returns or live implementable performance.',
            '10% adverse-excursion label uses closes, not intraday lows.',
            '20bp cost is an assumption, not an estimated realizable transaction cost.',
            'No fundamental revisions, holdings, true flows, OHLC or macro vintages used.']}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'saved': str(out), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
                      'events': len(events), 'months': events.month.nunique(), 'prefix_checks': checked}))
    for name, value in compare.items():
        print(name, json.dumps({k: value['delta'][k] for k in ['win', 'bad10', 'excess63', 'lower_first']}))
    print('MATCHED', json.dumps({k: result['matched_R_robustness'][k] for k in ['pairs', 'months', 'treated_retention', 'delta']}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('RESULTS.json'))
    args = parser.parse_args()
    run(args.out)
