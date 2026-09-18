#!/usr/bin/env python3
"""Declared descriptive contrasts over frozen replay; no production/ledger writes."""
from __future__ import annotations
import os, sys
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
sys.dont_write_bytecode = True
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
YEARS = np.arange(2010, 2026)

def ratio(numerator, denominator):
    return np.divide(numerator, denominator, out=np.full_like(numerator, np.nan, dtype=float), where=denominator>0)

def interval(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return (np.quantile(values, [.025, .975]).tolist() if len(values) else [np.nan, np.nan]), len(values)

def compare(data, metric, reps=5000, seed=20260915):
    if reps < 1: raise ValueError('reps must be positive')
    d = data[['event_date', 'arm', metric]].copy()
    d['event_date'] = pd.to_datetime(d.event_date)
    d = d[d[metric].notna() & np.isfinite(d[metric])].copy()
    if not set(d.arm).issubset({'A', 'B'}): raise ValueError('Unexpected arm')
    d['year'] = d.event_date.dt.year
    if not d.year.isin(YEARS).all(): raise ValueError('Outcome outside declared era')
    a, b = d[d.arm.eq('A')], d[d.arm.eq('B')]
    if a.empty or b.empty: raise ValueError('Both arms need finite observations')
    weights = np.random.default_rng(seed).multinomial(len(YEARS), np.full(len(YEARS), 1/len(YEARS)), size=reps)
    def cluster(g, column):
        v = g.groupby('year')[column].agg(['sum', 'count']).reindex(YEARS, fill_value=0)
        return ratio(weights @ v['sum'].to_numpy(), weights @ v['count'].to_numpy())
    pooled = cluster(a, metric) - cluster(b, metric)
    ci, valid = interval(pooled)
    daily = d.groupby(['event_date', 'arm'])[metric].mean().unstack('arm').reindex(columns=['A', 'B'])
    shared = (daily['A']-daily['B']).dropna().rename('difference').reset_index()
    shared['year'] = shared.event_date.dt.year
    if len(shared):
        date_ci, date_valid = interval(cluster(shared, 'difference'))
    else:
        date_ci, date_valid = [np.nan, np.nan], 0
    return dict(n_a=len(a), n_b=len(b), dates_a=a.event_date.nunique(), dates_b=b.event_date.nunique(),
                years_a=a.year.nunique(), years_b=b.year.nunique(), shared_dates=len(shared),
                shared_years=shared.year.nunique(), mean_a=a[metric].mean(), mean_b=b[metric].mean(),
                pooled_difference=a[metric].mean()-b[metric].mean(), ci95_low=ci[0], ci95_high=ci[1],
                shared_date_difference=shared.difference.mean(), shared_ci95_low=date_ci[0], shared_ci95_high=date_ci[1],
                valid_pooled_draws=valid, valid_shared_draws=date_valid, declared_calendar_clusters=len(YEARS),
                bootstrap_draws=reps, bootstrap_seed=seed)

CONTRASTS = [
    ('price_vs_rsi_fast_3D', ('price_fast','3D'), ('rsi_fast','3D')),
    ('price_vs_rsi_slow_3D', ('price_slow','3D'), ('rsi_slow','3D')),
    ('price_3D_vs_2D_memory', ('price_fast','3D'), ('price_fast_3Dmemory','2D')),
    ('rsi_3D_vs_2D_memory', ('rsi_slow','3D'), ('rsi_slow_3Dmemory','2D')),
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Refusing to overwrite research evidence')
    receipt = json.loads((args.replay_dir/'receipt.json').read_text())
    source = args.replay_dir/'events.parquet'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != receipt['output_sha256']['events.parquet']: raise ValueError('Frozen output hash changed')
    columns = ['ticker','family','timeframe','event_date','zone','common_price_zone']
    columns += [f'cal_{h}_{m}' for h in (21,63) for m in ('r','x')]
    data = pd.read_parquet(source, columns=columns)
    rows = []
    for name, arm_a, arm_b in CONTRASTS:
        for depth in ('zone','common_price_zone'):
            parts = []
            for label, (family, timeframe) in [('A', arm_a), ('B', arm_b)]:
                p = data[data.family.eq(family)&data.timeframe.eq(timeframe)&data[depth].eq('deep_negative')].copy()
                p['arm'] = label
                parts.append(p)
            selected = pd.concat(parts, ignore_index=True)
            for horizon in (21,63):
                for kind in ('positive','return','excess'):
                    column = f'cal_{horizon}_' + ('x' if kind=='excess' else 'r')
                    d = selected[['event_date','arm',column]].rename(columns={column:'value'}).copy()
                    if kind=='positive': d['value'] = (d.value>0).astype(float).where(d.value.notna())
                    rows.append(dict(contrast=name, depth=depth, horizon=horizon, metric=kind, **compare(d,'value')))
    result = pd.DataFrame(rows)
    if len(result)!=48: raise AssertionError('Declared contrast grid changed')
    args.output.mkdir(parents=True,exist_ok=False)
    result.to_csv(args.output/'contrasts.csv',index=False)
    proof = dict(status='PASS_DESCRIPTIVE_CONTRASTS_ONLY',authority='none',rows=len(result),
                 input_sha256=digest,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 contrast_sha256=hashlib.sha256((args.output/'contrasts.csv').read_bytes()).hexdigest(),
                 uncertainty='joint calendar-year bootstrap; shared dates are descriptive, not opportunity matching',
                 multiplicity='not adjusted; exposed research family and owner reconciliation remain pending')
    (args.output/'receipt.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps(proof),flush=True)
    selected = result[result.depth.eq('zone')&result.horizon.eq(21)&result.metric.eq('positive')]
    columns = ['contrast','n_a','n_b','pooled_difference','ci95_low','ci95_high','shared_dates','shared_date_difference','shared_ci95_low','shared_ci95_high']
    print(selected[columns].round(6).to_string(index=False),flush=True)

if __name__ == '__main__': main()
