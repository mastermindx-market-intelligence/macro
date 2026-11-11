"""Frozen-event benchmark sensitivity. Research-only; no canonical-store writes."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import pandas as pd
BENCHMARKS = ('SPY','RSP','MDY','IWM','QQQ')
CUTOFF = pd.Timestamp('2025-12-31')
EVENT_HASH = '9db1b4f87dda46f177906fcb979e297cbccdd0cbf415f16c67ea4c215ee5f62c'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def endpoint_return(series, entries, exits):
    if not series.index.is_unique: raise ValueError('Duplicate benchmark dates')
    a = series.reindex(pd.DatetimeIndex(entries)).to_numpy(dtype=float)
    b = series.reindex(pd.DatetimeIndex(exits)).to_numpy(dtype=float)
    valid = np.isfinite(a)&np.isfinite(b)&(a>0)&(b>0)
    return np.divide(b,a,out=np.full(len(a),np.nan),where=valid)-1

def market_states(prices):
    ma = prices[['SPY','RSP']].rolling(200,min_periods=200).mean()
    known = prices[['SPY','RSP']].notna().all(axis=1)&ma.notna().all(axis=1)
    s, r = prices.SPY>=ma.SPY, prices.RSP>=ma.RSP
    state = np.select([known&s&r,known&s&~r,known&~s&r,known&~s&~r],
                      ['both_above','cap_above_equal_below','cap_below_equal_above','both_below'],default='unknown')
    p = prices[['SPY','RSP']].pct_change(21,fill_method=None)
    known = p.notna().all(axis=1)
    s, r = p.SPY>=0,p.RSP>=0
    momentum = np.select([known&s&r,known&s&~r,known&~s&r,known&~s&~r],
                         ['both_up','cap_up_equal_down','cap_down_equal_up','both_down'],default='unknown')
    return pd.DataFrame({'market200':state,'market21':momentum},index=prices.index)

def overlay(events,prices):
    states = market_states(prices)
    out = []
    for h in (21,63):
        v = events.copy()
        v['horizon'] = h
        v['raw_return'] = v[f'return_{h}']
        v['net_return'] = (1+v.raw_return)*(.999/1.001)-1
        for b in BENCHMARKS:
            br = endpoint_return(prices[b],v.entry_date,v[f'exit_{h}'])
            v[b+'_return'] = br
            v[b+'_excess'] = v.raw_return-br
        np.testing.assert_allclose(v.SPY_excess,v[f'excess_{h}'],atol=1e-10,rtol=0,equal_nan=True)
        for col in states:
            v[col] = states[col].reindex(pd.DatetimeIndex(v.event_date)).to_numpy()
        v['common_benchmarks'] = v[[b+'_return' for b in BENCHMARKS]].notna().all(axis=1)&v.raw_return.notna()
        valid = v.common_benchmarks
        np.testing.assert_allclose((v.loc[valid,'RSP_excess']-v.loc[valid,'SPY_excess']).to_numpy(),
                                   (v.loc[valid,'SPY_return']-v.loc[valid,'RSP_return']).to_numpy(),atol=1e-14)
        out.append(v)
    return pd.concat(out,ignore_index=True)

def summarize(data,groups):
    rows = []
    for keys,g in data.groupby(groups,dropna=False,observed=True,sort=True):
        keys = keys if isinstance(keys,tuple) else (keys,)
        v = g[g.common_benchmarks]
        row = dict(zip(groups,keys))
        row.update(eligible_n=len(g),n=len(v),dates=v.event_date.nunique(),tickers=v.ticker.nunique(),
                   positive_rate=(v.raw_return>0).mean(),net_positive_rate=(v.net_return>0).mean(),mean_return=v.raw_return.mean())
        for b in BENCHMARKS:
            row[b+'_hit'] = (v[b+'_excess']>0).mean()
            row[b+'_mean_excess'] = v[b+'_excess'].mean()
            row[b+'_date_mean_excess'] = v.groupby('event_date')[b+'_excess'].mean().mean()
        row['SPY_RSP_hit_disagreement'] = ((v.SPY_excess>0)!=(v.RSP_excess>0)).mean()
        row['beat_SPY_not_RSP'] = ((v.SPY_excess>0)&(v.RSP_excess<=0)).mean()
        row['beat_RSP_not_SPY'] = ((v.RSP_excess>0)&(v.SPY_excess<=0)).mean()
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    if a.output.exists(): raise FileExistsError('Refusing to replace an evidence run')
    assert digest(a.source/'events.parquet')==EVENT_HASH
    amendment = Path(__file__).with_name('BENCHMARK_AMENDMENT_20260915.md')
    if not amendment.exists(): raise FileNotFoundError('Declared benchmark amendment missing')
    events = pd.read_parquet(a.source/'events.parquet')
    clock = pd.DatetimeIndex(pd.read_csv(a.source/'market_session_clock.csv',parse_dates=['date'])['date'])
    clock = clock[clock<=CUTOFF]
    frozen = pd.read_parquet(a.source/'adjusted_close_snapshot.parquet')['__BENCHMARK_SPY__']
    prices = pd.DataFrame({'SPY':frozen.reindex(clock)},index=clock)
    inputs = {'events.parquet':EVENT_HASH,'adjusted_close_snapshot.parquet':digest(a.source/'adjusted_close_snapshot.parquet')}
    coverage = []
    for b in BENCHMARKS:
        path = a.repo/'data/yahoo'/(b+'.parquet')
        raw = pd.read_parquet(path)
        if not raw.index.is_unique: raise ValueError(b+' duplicate index')
        s = pd.to_numeric(raw['close'],errors='coerce').sort_index()
        inputs[str(path)] = digest(path)
        coverage.append(dict(benchmark=b,source_last=str(s.index.max().date()),source_first=str(s.index.min().date()),rows=len(s)))
        if b!='SPY': prices[b] = s.reindex(clock)
    combined = overlay(events,prices)
    repair = combined[combined.timeframe.eq('3D')&combined.zone.eq('deep_negative')&combined['1W_phase'].eq('bear_weakening')&combined.market_above_200.eq(0)]
    tables = {'all_crosses':summarize(combined,['family','timeframe','horizon']),
              'cross_location':summarize(combined,['family','timeframe','zone','horizon']),
              'market200':summarize(combined,['family','timeframe','market200','horizon']),
              'market21':summarize(combined,['family','timeframe','market21','horizon']),
              'original_repair_crosses':summarize(repair,['family','horizon'])}
    controls = pd.read_parquet(a.source/'selected_context_observations.parquet')
    idx = clock.get_indexer(pd.DatetimeIndex(controls.event_date))
    assert (idx>=0).all()
    dates = pd.Series(clock)
    controls['entry_date'] = dates.reindex(idx+1).to_numpy()
    for h in (21,63): controls[f'exit_{h}'] = dates.reindex(idx+h+1).to_numpy()
    control_overlay = overlay(controls,prices)
    tables['original_repair_controls'] = summarize(control_overlay,['family','cross','horizon'])
    market = market_states(prices).loc['2010-01-01':]
    tables['market_date_census'] = market.groupby(['market200','market21']).size().rename('market_dates').reset_index()
    tables['coverage'] = pd.DataFrame(coverage)
    a.output.mkdir(parents=True,exist_ok=False)
    for name,table in tables.items(): table.to_csv(a.output/(name+'.csv'),index=False)
    prices.to_parquet(a.output/'benchmark_close_snapshot.parquet')
    assert digest(a.source/'events.parquet')==EVENT_HASH
    receipt = dict(status='PASS_EXPLORATORY_BENCHMARK_OVERLAY',authority='none',
                   event_rows=len(events),label_cutoff=str(CUTOFF.date()),benchmarks=list(BENCHMARKS),
                   matured_by_horizon={str(h):int(combined.loc[combined.horizon.eq(h),'raw_return'].notna().sum()) for h in (21,63)},
                   common_by_horizon={str(h):int(combined.loc[combined.horizon.eq(h),'common_benchmarks'].sum()) for h in (21,63)},
                   summary_cells=sum(len(t) for t in tables.values()),
                   original_stock_returns_recomputed=False,SPY_parity=True,
                   input_sha256=inputs,script_sha256=digest(__file__),amendment_sha256=digest(amendment),
                   trial_ledger_status='unapplied retrospective reconciliation; new look must be added',
                   limitations=['survivor-biased equity sample','retrospectively adjusted prices','overlapping events','unadjusted multiple looks','no causal or current-market forecast'])
    receipt['output_sha256'] = {p.name:digest(p) for p in a.output.iterdir() if p.is_file()}
    (a.output/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:receipt[k] for k in ['status','event_rows','common_by_horizon','summary_cells','SPY_parity']}),flush=True)
if __name__ == '__main__': main()
