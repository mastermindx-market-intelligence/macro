"""Fixed, retrospective ETF event study; see ETF_PILOT_SPEC.md before running.

No Prophet ledger/outcome access, provider calls, model fit, production import or
canonical write. CLI consumes the existing Snapshot reader; output is exclusive-
create. Historical source bytes are not point-in-time delivery proof.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import types

import numpy as np
import pandas as pd

SOURCE = 'b4f95f98ef80b8cbb4636afbd723b5091658e1f1'
SPEC_COMMIT = '8bc732d4c15c020bcafe068a9fad8a096e9d6e5e'
CANDIDATES = ('QQQ', 'IWM', 'SOXX')
HORIZON = 10
COST_PP = .20
START, END, INPUT_END = '2006-01-03', '2025-12-31', '2026-01-31'
AUTHORITY = {k: False for k in ('rank', 'entry', 'size', 'trade', 'promotion')}


def normalize(s: pd.Series) -> pd.Series:
    s=s.copy();s.index=pd.DatetimeIndex(s.index).as_unit('ns')
    if s.index.tz is not None or s.index.has_duplicates:
        raise ValueError('unique daily timezone-naive source dates required')
    s=s.sort_index().astype(float).loc[:INPUT_END]
    if np.isinf(s.to_numpy()).any():raise ValueError('infinite source value')
    return s


def features(prices: dict[str,pd.Series], real: pd.Series) -> pd.DataFrame:
    cal=prices['SPY'].index
    real=real.dropna()
    union=cal.union(real.index).sort_values()
    aligned=real.reindex(union).ffill().reindex(cal)
    last=pd.Series(real.index,index=real.index).reindex(union).ffill().reindex(cal)
    age=np.full(len(cal),np.nan)
    valid=last.notna().to_numpy()
    age[valid]=np.flatnonzero(valid)-cal.searchsorted(pd.DatetimeIndex(last[valid]),side='left')
    aligned=aligned.where(age<=3)
    rsp=prices['RSP'].reindex(cal);spy=prices['SPY']
    return pd.DataFrame({'real_change_5':aligned.diff(5),
        'participation_5':rsp.pct_change(5,fill_method=None)-spy.pct_change(5,fill_method=None),
        'real_age_sessions':age},index=cal)


def event_regime(label: pd.Timestamp, f: pd.DataFrame) -> tuple[str,str|None]:
    # Strictly prior SPY session, including a calendar-Friday holiday label.
    pos=f.index.searchsorted(label,side='left')-1
    if pos<0:return 'unknown',None
    a,b=f.iloc[pos][['real_change_5','participation_5']]
    used=f.index[pos].date().isoformat()
    if not (np.isfinite(a) and np.isfinite(b)):return 'unknown',used
    if a>0 and b<0:return 'hidden_fragility',used
    if a<=0 and b>=0:return 'relief_broadening',used
    return 'mixed',used


def grade(label, ticker, prices, horizon=HORIZON, cost_pp=COST_PP) -> dict:
    cal=prices['SPY'].index;entry=cal.searchsorted(label,side='right');exit_=entry+horizon
    if exit_>=len(cal):return {'graded':False,'reason':'unmatured'}
    en,ex=cal[entry],cal[exit_]
    values=[prices[t].get(d,np.nan) for t in (ticker,'SPY') for d in (en,ex)]
    if not all(np.isfinite(x) and x>0 for x in values):
        return {'graded':False,'reason':'missing_exact_price'}
    a,b,c,d=values;ret=100*(b/a-1);benchmark=100*(d/c-1)
    return {'graded':True,'entry_date':en.date().isoformat(),'exit_date':ex.date().isoformat(),
            'quarter':str(en.to_period('Q')),'month':str(en.to_period('M')),
            'asset_return_pct':ret,'spy_return_pct':benchmark,
            'net_asset_return_pct':ret-cost_pp,'net_excess_pct':ret-benchmark-cost_pp}


def native_functions(snapshot):
    # Reuse the existing Snapshot/owner approach. Extract exact pure definitions;
    # no signal_gate/analyze or ambient current washout file is substituted.
    lib=types.ModuleType('lib');lib.__path__=[];sys.modules['lib']=lib
    lib.nyse_calendar=snapshot.module('lib.nyse_calendar','lib/nyse_calendar.py')
    anchor=snapshot.module('pilot_session_anchor','engine/session_anchor.py')
    ns={'pd':pd,'np':np,'session_positions':anchor.session_positions}
    for path,names in [('engine/technicals.py',{'rsi','macd_hist'}),
        ('engine/confluence_tiers.py',{'_ema','_rsi_macd','_tf_bars','_completed_resample'})]:
        tree=ast.parse(snapshot.read(path));nodes=[];found=set()
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name in names:
                nodes.append(node);found.add(node.name)
            elif path.endswith('confluence_tiers.py') and isinstance(node,ast.Assign):
                ids={x.id for x in ast.walk(node.targets[0]) if isinstance(x,ast.Name)}
                if ids=={'RSI_LEN','FAST_LEN','BASE_LEN','SIG_LEN'}:nodes.append(node)
        if found!=names:raise ValueError('native owner definition absent')
        exec(compile(ast.Module(body=nodes,type_ignores=[]),snapshot.ref+':'+path,'exec'),ns)
    if tuple(ns[k] for k in ('RSI_LEN','FAST_LEN','BASE_LEN','SIG_LEN'))!=(14,14,60,5):
        raise ValueError('native parameter identity changed')
    return ns,anchor


def event_rows(prices, f, ns) -> list[dict]:
    rows=[]
    for ticker in CANDIDATES:
        c=prices[ticker].dropna()
        for grain in ('1D','2D','3D','1W'):
            if grain=='1D':bars=c;known=pd.Series(c.index,index=c.index)
            elif grain=='1W':bars,known=ns['_completed_resample'](c,'W-FRI')
            else:
                bars=ns['_tf_bars'](c,int(grain[0]))[0]
                known=pd.Series(bars.index,index=bars.index)
            for family in ('price_macd','rsi_macd'):
                if family=='price_macd':hist=ns['macd_hist'](bars)
                else:
                    m,s=ns['_rsi_macd'](bars);hist=m-s
                fire=(hist>0)&(hist.shift(1)<=0)&hist.notna()&hist.shift(1).notna()
                for label in hist.index[fire]:
                    if not (pd.Timestamp(START)<=label<=pd.Timestamp(END)):continue
                    state,regdate=event_regime(label,f)
                    row={'ticker':ticker,'family':family,'grain':grain,
                         'signal_date':label.date().isoformat(),
                         'observation_end':pd.Timestamp(known.loc[label]).date().isoformat(),
                         'regime':state,'regime_input_end':regdate}
                    if row['observation_end']>row['signal_date']:raise ValueError('future bar support')
                    row.update(grade(label,ticker,prices));rows.append(row)
    return rows


def cell_stats(rows: list[dict]) -> dict:
    ok=[x for x in rows if x['graded']]
    result={'events':len(rows),'graded':len(ok),'ungraded':len(rows)-len(ok),
        'unique_signal_dates':len({r['signal_date'] for r in rows}),
        'entry_months':len({r['month'] for r in ok}),'entry_quarters':len({r['quarter'] for r in ok}),
        'ungraded_reasons':dict(Counter(r['reason'] for r in rows if not r['graded']))}
    for field in ('net_asset_return_pct','net_excess_pct'):
        a=np.array([r[field] for r in ok],dtype=float)
        result['mean_'+field]=float(a.mean()) if len(a) else None
        result['median_'+field]=float(np.median(a)) if len(a) else None
    result['positive_net_asset_fraction']=sum(r['net_asset_return_pct']>0 for r in ok)/len(ok) if ok else None
    return result


def block_means(rows, quarters, weights):
    sums=np.zeros(len(quarters));counts=np.zeros(len(quarters));pos={q:i for i,q in enumerate(quarters)}
    for r in rows:sums[pos[r['quarter']]]+=r['net_excess_pct'];counts[pos[r['quarter']]]+=1
    den=weights@counts;out=np.full(len(weights),np.nan)
    np.divide(weights@sums,den,out=out,where=den>0)
    return out


def contrasts(rows,period_start,period_end,draws=1000,seed=20261003):
    quarters=pd.period_range(period_start,period_end,freq='Q').astype(str).tolist()
    weights=np.random.default_rng(seed).multinomial(len(quarters),np.ones(len(quarters))/len(quarters),size=draws)
    values={};summary=[]
    for family in ('price_macd','rsi_macd'):
        for grain in ('1D','2D','3D','1W'):
            states={s:[r for r in rows if r['graded'] and r['family']==family and r['grain']==grain and r['regime']==s]
                    for s in ('hidden_fragility','relief_broadening')}
            enough=all(len({r['month'] for r in rs})>=12 and len({r['quarter'] for r in rs})>=4 for rs in states.values())
            out={'family':family,'grain':grain,'contrast':'hidden_minus_relief','qualified':False}
            if enough:
                bad,good=states.values();delta=block_means(bad,quarters,weights)-block_means(good,quarters,weights)
                value=float(np.mean([r['net_excess_pct'] for r in bad])-np.mean([r['net_excess_pct'] for r in good]))
                valid=np.isfinite(delta);out['valid_bootstrap_draws']=int(valid.sum())
                if valid.sum()>=.95*draws:
                    out.update(qualified=True,mean_difference_pp=value,
                               interval95_pp=np.quantile(delta[valid],[.025,.975]).tolist())
                    values[(family,grain)]=(value,delta)
                else:out['reason']='insufficient_bootstrap_support'
            else:out['reason']='insufficient_state_contrast'
            summary.append(out)
        key1,key3=(family,'1D'),(family,'3D')
        out={'family':family,'contrast':'3D_minus_1D_of_hidden_minus_relief','qualified':False}
        if key1 in values and key3 in values:
            a,da=values[key3];b,db=values[key1];d=da-db;valid=np.isfinite(d)
            out['valid_bootstrap_draws']=int(valid.sum())
            if valid.sum()>=.95*draws:
                out.update(qualified=True,mean_difference_pp=a-b,
                           interval95_pp=np.quantile(d[valid],[.025,.975]).tolist())
            else:out['reason']='insufficient_bootstrap_support'
        else:out['reason']='insufficient_state_contrast'
        summary.append(out)
    return summary


def summarize(rows):
    results={}
    for name,a,b in [('early','2006-01-03','2014-12-31'),('later','2015-01-01','2025-12-31'),('combined',START,END)]:
        part=[r for r in rows if a<=r['signal_date']<=b];cells=[]
        for family in ('price_macd','rsi_macd'):
            for grain in ('1D','2D','3D','1W'):
                for state in ('hidden_fragility','relief_broadening','mixed','unknown'):
                    xs=[r for r in part if (r['family'],r['grain'],r['regime'])==(family,grain,state)]
                    cells.append(dict(family=family,grain=grain,regime=state,**cell_stats(xs)))
        # Entry occurs in the next session; final December signals can enter in January.
        max_entry=max((r['entry_date'] for r in part if r['graded']),default=b)
        results[name]={'all':cell_stats(part),'cells':cells,'contrasts':contrasts(part,a,max(b,max_entry))}
    return results


def run(snapshot):
    if snapshot.ref!=SOURCE:raise ValueError('pilot source differs from pre-analysis specification')
    names=('SPY','RSP',*CANDIDATES)
    prices={t:normalize(snapshot.frame(f'data/yahoo/{t}.parquet',['close'])['close']) for t in names}
    real=normalize(snapshot.frame('data/fred/DFII10.parquet',['us10y_real'])['us10y_real'])
    ns,anchor=native_functions(snapshot);cal=prices['SPY'].index
    check=cal[(cal>=START)&(cal<=END)]
    gaps=np.diff(anchor.session_positions(check,'US'))
    if (gaps!=1).any():raise ValueError('SPY grid is not contiguous under native US calendar')
    for t,p in prices.items():
        x=p.reindex(check)
        if x.isna().any() or (x<=0).any():raise ValueError(t+': incomplete or nonpositive common input support')
    f=features(prices,real);rows=event_rows(prices,f,ns)
    return {'schema':'prophet.etf_mechanism_pilot/v1','authority':dict(AUTHORITY),
        'source_commit':SOURCE,'spec_commit':SPEC_COMMIT,
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'basis':'saved historical source; NOT full-vintage PIT, delivered Prophet, or prospective evidence',
        'spec':{'candidates':list(CANDIDATES),'horizon_spy_sessions':HORIZON,'round_trip_cost_pp':COST_PP,
                'input_end':INPUT_END,'event_start':START,'event_end':END,
                'bar_policy':'completed_only','bootstrap':'1000 jointly sampled entry-quarter blocks; seed 20261003'},
        'input_coverage':{t:{'rows':len(p),'start':p.index.min().date().isoformat(),'end':p.index.max().date().isoformat()}
                          for t,p in prices.items()},
        'source_receipts':snapshot.receipts(),'results':summarize(rows),'events':rows,
        'limitations':['Three survivor ETFs; not a stock or thematic candidate universe.',
            'Native timeframe changes also change memory; policy contrast, not pure grain.',
            'Current-vintage historical macro and price adjustments are not PIT-certified.',
            'Raw completed crossings are not validated Prophet take or live provisional decisions.',
            'Prior-session lag does not certify provider release/capture availability.',
            'Quarter-bootstrap intervals are descriptive; no multiple-cell selection or promotion.',
            'No portfolio, intraday path, position sizing or optimal-clock conclusion.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args()
    from run_snapshot_audit import Snapshot
    report=run(Snapshot(args.repo,SOURCE))
    with Path(args.out).open('x') as fh:json.dump(report,fh,indent=2,sort_keys=True,allow_nan=False)
    print(json.dumps({'output':args.out,'events':len(report['events']),
          'source_files':len(report['source_receipts']),'authority':report['authority']}))
