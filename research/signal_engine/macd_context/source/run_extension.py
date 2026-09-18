#!/usr/bin/env python3
"""Second exploratory look on frozen MACD data; no production or registry writes."""
from __future__ import annotations
import os, sys
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
sys.dont_write_bytecode = True
import argparse, hashlib, importlib.util, json, math, time
from pathlib import Path
import numpy as np
import pandas as pd
CALENDAR_H = (5, 10, 15, 21, 42, 63, 126, 252)
NATIVE_H = (3, 5, 10, 20)
FAMILIES = ('price_fast', 'rsi_fast', 'price_slow', 'rsi_slow')
TFS = ('1D', '2D', '3D', '1W')
POLICIES = [f'cal_{h}' for h in CALENDAR_H] + [f'native_{h}' for h in NATIVE_H] + ['opposite_252']
EXPECTED_LEGACY_HASH = '6354a5ab3b5276b1ccd74ce173cadce055364634ad5f80a38ab8e5bca8f9968d'

def alpha_for(span, ratio=1.0):
    return 1.0 - (1.0 - 2.0/(span+1.0))**ratio

def transformed(c, use_rsi, ratio):
    if not use_rsi:
        return c
    a = 1.0 - (1.0 - 1.0/14.0)**ratio
    minimum = math.ceil(1.0/a - 1e-10)
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=a, min_periods=minimum).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=a, min_periods=minimum).mean()
    return 100.0 - 100.0/(1.0 + up/dn.replace(0, np.nan))

def indicator(c, family, ratio=1.0):
    use_rsi = family.startswith('rsi')
    slow = family.endswith('slow')
    spans = (14, 60, 5) if slow else (12, 26, 9)
    x = transformed(c, use_rsi, ratio)
    def ema(s, span):
        a = alpha_for(span, ratio)
        minimum = math.ceil(2.0/a - 1.0 - 1e-10)
        return s.ewm(alpha=a, adjust=slow, min_periods=minimum).mean()
    m = ema(x, spans[0]) - ema(x, spans[1])
    h = m - ema(m, spans[2])
    scale_n, scale_min = math.ceil(126/ratio), math.ceil(63/ratio)
    z = m / m.abs().rolling(scale_n, min_periods=scale_min).median().shift(1).replace(0, np.nan)
    zone = np.select([z<=-1.5, (z>-1.5)&(z<-.1), (z>=-.1)&(z<=.1),
                      (z>.1)&(z<=1.5), z>1.5],
                     ['deep_negative','negative','near_zero','positive','high_positive'], default='unknown')
    dh = h.diff()
    phase = np.select([(h<0)&(dh<0), (h<0)&(dh>=0), (h>0)&(dh>0), (h>0)&(dh<=0)],
                      ['bear_strengthening','bear_weakening','bull_strengthening','bull_weakening'], default='unknown')
    return pd.DataFrame({'macd':m, 'hist':h, 'zone_z':z, 'zone':zone, 'phase':phase,
                         'up':(h>0)&(h.shift(1)<=0), 'down':(h<0)&(h.shift(1)>=0)}, index=c.index)

def values_at(values, positions):
    values, positions = np.asarray(values), np.asarray(positions)
    out = np.full(len(positions), np.nan)
    good = (positions>=0)&(positions<len(values))
    out[good] = values[positions[good]]
    return out

def payoff(c, bench, entry, exit_pos, beta, paths=False):
    cp, bp = c.to_numpy(), bench.to_numpy()
    valid = (entry<len(cp))&(exit_pos>=entry)&(exit_pos<len(cp))
    r = values_at(cp,exit_pos)/values_at(cp,entry)-1
    b = values_at(bp,exit_pos)/values_at(bp,entry)-1
    r[~valid], b[~valid] = np.nan, np.nan
    duration = np.where(valid,exit_pos-entry,np.nan)
    out = {'r':r, 'net':(1+r)*(.999/1.001)-1, 'x':r-b, 'bx':r-beta*b, 'dur':duration}
    if paths:
        mae, mfe = np.full(len(entry),np.nan), np.full(len(entry),np.nan)
        for j in np.flatnonzero(valid):
            p = cp[entry[j]:exit_pos[j]+1]/cp[entry[j]]-1
            mae[j], mfe[j] = p.min(), p.max()
        out.update(mae=mae, mfe=mfe)
    return out

def stress_spells(spy):
    ma = spy.rolling(200,min_periods=200).mean()
    below = (spy<ma)&ma.notna()
    ids, active, streak, next_id = [], 0, 0, 0
    for low in below:
        if low:
            if not active:
                next_id += 1
                active = next_id
            streak = 0
        elif active:
            streak += 1
            if streak >= 10: active = 0
        ids.append(active)
    return pd.DataFrame({'below200':below, 'stress_spell':ids},index=spy.index)

def build_name(ticker, c, study, market):
    bench = study.spy.reindex(c.index)
    yr, xr = c.pct_change(fill_method=None), bench.pct_change(fill_method=None)
    beta_all = yr.rolling(126,min_periods=63).cov(xr)/xr.rolling(126,min_periods=63).var()
    vol = yr.rolling(20,min_periods=20).std()
    drawdown = c/c.rolling(63,min_periods=63).max()-1
    output = []
    for family in FAMILIES:
        states = {tf:indicator(study.native(c,tf),family) for tf in (*TFS,'1M')}
        jobs = [(tf,1.0,states[tf],family) for tf in TFS]
        if family in ('price_fast','rsi_slow'):
            jobs.append(('2D',2/3,indicator(study.native(c,'2D'),family,2/3),family+'_3Dmemory'))
        for tf, ratio, state, name in jobs:
            mask = state['up']&(state.index>=pd.Timestamp('2010-01-01'))
            native_pos = np.flatnonzero(mask.to_numpy())
            idx = state.index[native_pos]
            daily_pos = c.index.get_indexer(idx)
            entry = daily_pos+1
            beta = beta_all.reindex(idx).to_numpy()
            weekly = states['1W'].reindex(idx,method='ffill')
            monthly = states['1M'].reindex(idx,method='ffill')
            for htf in ('1W','1M'):
                known = pd.Series(states[htf].index,index=states[htf].index).reindex(idx,method='ffill').dropna()
                assert (known<=known.index).all(), 'Future higher-timeframe context'
            fields = {'ticker':ticker, 'family':name, 'timeframe':tf, 'event_date':idx,
                      'zone':state.loc[idx,'zone'].to_numpy(), 'zone_z':state.loc[idx,'zone_z'].to_numpy()}
            cutoff_pos = c.index.searchsorted(pd.Timestamp('2025-12-31'),side='right')
            fields.update(beta126=beta,vol20=vol.reindex(idx).to_numpy(),
                          drawdown63=drawdown.reindex(idx).to_numpy(),
                          common252=entry+252<cutoff_pos,
                          entry_date=pd.Series(c.index).reindex(entry).to_numpy(),
                          weekly_phase=weekly['phase'].fillna('unknown').to_numpy(),
                          monthly_phase=monthly['phase'].fillna('unknown').to_numpy())
            common = indicator(study.native(c,tf),'price_fast').reindex(idx)
            common_week = indicator(study.native(c,'1W'),'price_fast').reindex(idx,method='ffill')
            fields.update(common_price_zone=common['zone'].to_numpy(),
                          common_price_weekly_phase=common_week['phase'].fillna('unknown').to_numpy())
            for column in market:
                fields[column] = market[column].reindex(idx).to_numpy()
            native_daily = c.index.get_indexer(state.index)
            exits = {f'cal_{h}':entry+h for h in CALENDAR_H}
            for h in NATIVE_H:
                end = native_pos+h
                safe = np.minimum(end,len(state)-1)
                exits[f'native_{h}'] = np.where(end<len(state),native_daily[safe]+1,len(c))
            down = np.flatnonzero(state['down'].to_numpy())
            where = np.searchsorted(down,native_pos,side='right')
            first_down = np.full(len(idx),len(c),dtype=int)
            has_down = where<len(down)
            first_down[has_down] = native_daily[down[where[has_down]]]+1
            exits['opposite_252'] = np.minimum(first_down,entry+252)
            for policy, exit_pos in exits.items():
                exit_pos = np.where(exit_pos<cutoff_pos,exit_pos,len(c))
                metrics = payoff(c,bench,entry,exit_pos,beta,paths=policy in ('cal_21','cal_63','native_10','opposite_252'))
                fields.update({policy+'_'+k:v for k,v in metrics.items()})
                fields[policy+'_exit_date'] = pd.Series(c.index).reindex(exit_pos).to_numpy()
            frame = pd.DataFrame(fields)
            frame = frame.loc[frame.event_date.le(pd.Timestamp('2025-12-31'))]
            output.append(frame)
    return pd.concat(output,ignore_index=True)

def summarize(events, groups, policies=POLICIES):
    rows = []
    for keys,g in events.groupby(groups,dropna=False,observed=True,sort=True):
        keys = keys if isinstance(keys,tuple) else (keys,)
        identity = dict(zip(groups,keys))
        for policy in policies:
            v = g.dropna(subset=[policy+'_r',policy+'_x'])
            r,net,x = (v[policy+'_'+k] for k in ('r','net','x'))
            bx = v[policy+'_bx'].dropna()
            row = dict(identity,policy=policy,eligible_n=len(g),n=len(v),censored_n=len(g)-len(v),
                       tickers=v.ticker.nunique(),event_dates=v.event_date.nunique(),
                       positive_rate=(r>0).mean(),net_positive_rate=(net>0).mean(),
                       mean_return=r.mean(),median_return=r.median(),mean_net=net.mean(),
                       p05_return=r.quantile(.05),p95_return=r.quantile(.95),
                       mean_win=r[r>0].mean(),mean_loss=r[r<=0].mean(),
                       beats_spy_rate=(x>0).mean(),mean_excess=x.mean(),
                       beta_adjusted_n=len(bx),mean_beta_adjusted_excess=bx.mean(),
                       median_duration=v[policy+'_dur'].median())
            date_means = v.groupby('event_date')[[policy+'_r',policy+'_x']].mean()
            row['date_weighted_return'] = date_means[policy+'_r'].mean()
            row['date_weighted_excess'] = date_means[policy+'_x'].mean()
            for metric in ('mae','mfe'):
                if policy+'_'+metric in v: row['median_'+metric] = v[policy+'_'+metric].median()
            rows.append(row)
    return pd.DataFrame(rows)

def load_study(source):
    path = source/'reproduce_study.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==EXPECTED_LEGACY_HASH
    spec = importlib.util.spec_from_file_location('frozen_original',path)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    study = original.Study(source)
    clock = pd.read_csv(source/'market_session_clock.csv',parse_dates=['date'])
    frame = pd.DataFrame({'date':study.clock},index=study.clock)
    study.bounds['2D'] = frame.groupby(clock['absolute_session_position'].to_numpy()//2)['date'].agg(['min','max'])
    for ticker,c in study.prices.items():
        assert c.index.max()<=pd.Timestamp('2025-12-31'), 'Undeclared future stock data'
        assert c.index.equals(study.clock[(study.clock>=c.index.min())&(study.clock<=c.index.max())]), 'Missing market sessions'
    return study

def check_parity(events, source):
    previous = pd.read_parquet(source/'events.parquet')
    mapping = {'price_fast':'price_macd_12_26_9','rsi_slow':'prophet_rsi_macd_14_14_60_5'}
    current = events[events.family.isin(mapping)&events.timeframe.isin(['1D','3D','1W'])].copy()
    current['family'] = current.family.map(mapping)
    keys = ['ticker','family','timeframe','event_date']
    joined = current.merge(previous,on=keys,how='outer',indicator=True,suffixes=('_new','_old'),validate='one_to_one')
    assert joined['_merge'].eq('both').all(), 'Original event population changed'
    for h in (21,63):
        np.testing.assert_allclose(joined[f'cal_{h}_r'],joined[f'return_{h}'],equal_nan=True,atol=1e-12)
        np.testing.assert_allclose(joined[f'cal_{h}_x'],joined[f'excess_{h}'],equal_nan=True,atol=1e-12)
    assert joined.zone_new.eq(joined.zone_old).all(), 'Original depth bins changed'
    return {'original_event_rows':len(joined),'event_population_parity':True,'original_21_63_outcome_parity':True}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    source, output = args.study_dir.resolve(), args.output.resolve()
    if output.exists(): raise FileExistsError('Refusing to overwrite an existing evidence run')
    amendment = Path(__file__).parent/'RESUMPTION_AMENDMENT.md'
    if not amendment.exists(): raise FileNotFoundError('Missing pre-outcome amendment')
    study = load_study(source)
    market = stress_spells(study.spy)
    mw = indicator(study.native(study.spy,'1W'),'price_fast')
    market['market_weekly_phase'] = mw['phase'].reindex(market.index,method='ffill').fillna('unknown')
    output.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    chunks = []
    for i,(ticker,c) in enumerate(sorted(study.prices.items()),1):
        chunks.append(build_name(ticker,c,study,market))
        if i%40==0: print(json.dumps({'phase':'build','names_complete':i}),flush=True)
    events = pd.concat(chunks,ignore_index=True)
    assert not events.duplicated(['ticker','family','timeframe','event_date']).any()
    proof = check_parity(events,source)
    for policy in POLICIES:
        dates = events[policy+'_exit_date'].dropna()
        assert (dates<=pd.Timestamp('2025-12-31')).all()
    events.to_parquet(output/'events.parquet',index=False)
    tables = {'all_crosses':summarize(events,['family','timeframe']),
              'cross_location':summarize(events,['family','timeframe','zone']),
              'common252_cross_location':summarize(events[events.common252],['family','timeframe','zone']),
              'common_price_location':summarize(events,['family','timeframe','common_price_zone'])}
    repair = events[events.zone.eq('deep_negative')&events.weekly_phase.eq('bear_weakening')&events.below200.eq(True)].copy()
    repair['year'] = repair.event_date.dt.year
    tables['repair_context'] = summarize(repair,['family','timeframe'])
    tables['repair_years'] = summarize(repair,['family','timeframe','year'],['cal_21','cal_63'])
    tables['repair_spells'] = summarize(repair,['family','timeframe','stress_spell'],['cal_21','cal_63'])
    for name,table in tables.items(): table.to_csv(output/(name+'.csv'),index=False)
    proof.update(status='PASS_RESEARCH_ONLY',event_rows=len(events),tickers=events.ticker.nunique(),
                 event_start=str(events.event_date.min().date()),event_end=str(events.event_date.max().date()),
                 label_cutoff='2025-12-31',elapsed_seconds=round(time.monotonic()-started,2),
                 skillpack_sha='e1f752a58df8f874efa12e30957d911627a0c4f8',
                 macro_review_sha='76a2c0c8573272ce582c1a42e5b27b199b605744',
                 pandas=pd.__version__,numpy=np.__version__,authority='none',
                 trial_ledger_status='Prior and current exploratory look reconciliation pending; no promotion-bearing inference',
                 limitations=['current-universe survivorship','retrospectively adjusted prices','overlapping events',
                              'close-only fills and path extrema','selected contexts','no untouched-holdout claim'])
    proof['input_sha256'] = {p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in
                             ('adjusted_close_snapshot.parquet','market_session_clock.csv','events.parquet','reproduce_study.py')}
    proof['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    proof['amendment_sha256'] = hashlib.sha256(amendment.read_bytes()).hexdigest()
    proof['output_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    (output/'receipt.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps({k:proof[k] for k in ('status','event_rows','tickers','elapsed_seconds','original_event_rows')}),flush=True)

if __name__ == '__main__': main()
