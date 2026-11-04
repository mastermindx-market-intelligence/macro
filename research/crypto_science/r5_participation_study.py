"""Frozen R5 same-parent participation study. No production signal or gate writes."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.crypto_science import r4_sequence_study as r4
H=pd.Timedelta(hours=1)
BASE='bf879ff6a26d2369d970dc583d89ba2aadab5e62'
PLAN='3cc4e46d2b7827ba5fce746d5b4bcd1875fb80c6'
OUT=Path(__file__).with_name('r5')


def checked_index(frame):
    i=frame.index
    if (not isinstance(i,pd.DatetimeIndex) or i.tz is not None or i.has_duplicates
            or not i.is_monotonic_increasing or not i.equals(i.floor('h'))):
        raise ValueError('Require unique chronological naive-UTC whole-hour observations')
    if not set(r4.OHLC).issubset(frame):
        raise ValueError('Missing required price fields')


def prices(frame,index):
    w=frame.reindex(index)[r4.OHLC].apply(pd.to_numeric,errors='coerce')
    valid=(np.isfinite(w).all(axis=1)&(w>0).all(axis=1)
           &(w.high>=w[['open','low','close']].max(axis=1))
           &(w.low<=w[['open','high','close']].min(axis=1)))
    return w if valid.all() else None


def participation(frame,active,reference):
    if 'volume' not in frame:return None
    v=pd.to_numeric(frame.volume,errors='coerce')
    a=v.reindex(active);b=v.reindex(reference)
    if not (np.isfinite(a).all() and np.isfinite(b).all() and (a>=0).all() and (b>=0).all()):return None
    denom=float(b.median())
    return float(a.mean()/denom) if denom>0 else None


def downside_observation(frame,anchor):
    checked_index(frame);a=pd.Timestamp(anchor)
    refidx=pd.date_range(a-72*H,periods=72,freq='h')
    active=pd.date_range(a+H,periods=6,freq='h')
    ref=prices(frame,refidx);w=prices(frame,active)
    result={'issue':a+7*H,'state':'unknown','volume_ratio':participation(frame,active,refidx),
            'broken_level':None,'last_close':None,'first3_low':None,'last3_low':None}
    if ref is None or w is None:return result
    level=float(ref.low.min());c=float(w.close.iloc[-1])
    lo1=float(w.low.iloc[:3].min());lo2=float(w.low.iloc[3:].min())
    state='reclaimed' if c>=level else ('persistent' if lo2<lo1 else 'stalled_below')
    result.update(state=state,broken_level=level,last_close=c,first3_low=lo1,last3_low=lo2)
    return result


def early_reclaim(frame,anchor):
    checked_index(frame);T=pd.Timestamp(anchor)+24*H
    out={'price_status':'unknown','signal_start':None,'issue':None,
         'volume_ratio':None,'volume_status':'not_needed'}
    for k in range(6,48):
        t=T+k*H;idx=pd.date_range(t-6*H,periods=7,freq='h');w=prices(frame,idx)
        if w is None:return out
        if w.close.iloc[-1]>w.high.iloc[:-1].max() and w.low.iloc[-3:].min()>=w.low.iloc[-6:-3].min():
            v=participation(frame,pd.date_range(t-2*H,periods=3,freq='h'),
                            pd.date_range(t-74*H,periods=72,freq='h'))
            return {'price_status':'confirmed','signal_start':t,'issue':t+H,'volume_ratio':v,
                    'volume_status':'unknown' if v is None else ('accepted' if v>=1 else 'rejected')}
    out['price_status']='no_entry'
    return out


def cash_after(target,action):
    out=target.copy(deep=True)
    out.loc[out.index>=pd.Timestamp(action)]=0.
    return out


def number(x):return r4.number(x)


def scalar_records(rows):
    return [{k:(v.isoformat(sep=' ') if isinstance(v,pd.Timestamp) else v) for k,v in row.items()} for row in rows]


def period_rows(frame,start,end):
    a=pd.to_datetime(frame.anchor);e=pd.to_datetime(frame.end)
    return frame.loc[(a>=pd.Timestamp(start))&(a<pd.Timestamp(end))&(e<pd.Timestamp(end))].copy()


def mean_stat(f,column):
    v=pd.to_numeric(f[column],errors='coerce').dropna()
    return {'n':len(v),'mean':number(v.mean()),'median':number(v.median()),
            'block95':r4.interval90(f,column) if len(v) else None}


def summarize(policy,events):
    periods={'full':('2016-01-01','2026-09-27'),'2016_2019':('2016-01-01','2020-01-01'),
             '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2026-09-27')}
    stats=[];groups=[]
    columns=['volume_minus_price','price_minus_incumbent','volume_minus_incumbent',
             'delayed_minus_incumbent','price_minus_immediate','price_minus_daily',
             'price_return','volume_return','incumbent_return']
    for period,(start,end) in periods.items():
        for (family,lag,cost),raw in policy.groupby(['family','lag_hours','cost_bps']):
            f=period_rows(raw,start,end)
            s={'period':period,'family':family,'lag_hours':int(lag),'cost_bps':int(cost),'parents':len(f),
               'stats':{c:mean_stat(f,c) for c in columns if c in f},
               'status_counts':f.status.value_counts(dropna=False).to_dict()}
            valid=f.dropna(subset=['volume_minus_price'])
            yrs=pd.to_datetime(valid.anchor).dt.year
            s['per_year_n']= {str(int(k)):int(v) for k,v in yrs.value_counts().sort_index().items()}
            s['leave_one_year_out_primary_mean']={str(int(y)):number(valid.loc[yrs!=y,'volume_minus_price'].mean()) for y in sorted(yrs.unique())}
            stats.append(s)
        for (family,lag),raw in events.groupby(['family','lag_hours']):
            f=period_rows(raw,start,end)
            for state,sf in f.groupby('state',dropna=False):
                groups.append({'period':period,'family':family,'lag_hours':int(lag),'state':str(state),
                               'n':len(sf),'price_categories':sf.price_category.value_counts().to_dict(),
                               'volume_categories':sf.volume_category.value_counts().to_dict()})
    return stats,groups


def main():
    from lib import config
    OUT.mkdir(exist_ok=True);data=Path(config.data_dir());prior=OUT.parent/'r4'
    old=json.loads((prior/'results.json').read_text())
    # Use the exact previously verified incumbent, not a newly spliced snapshot.
    for name,expected in old['input_hashes'].items():
        p=data/name;actual=r4.digest(p) if p.exists() else None
        if actual!=expected:raise RuntimeError('R4 input drift: '+name)
    for name,expected in old['sources'].items():
        if r4.digest(ROOT/name)!=expected:raise RuntimeError('R4 source drift: '+name)
    inputs={name:value for name,value in old['input_hashes'].items()}
    gates={str(p.relative_to(data)):r4.digest(p) for p in (data/'vector').iterdir() if p.suffix in ['.json','.jsonl']}
    evidence={str(p.relative_to(ROOT)):r4.digest(p) for parent in ['r1','r2','r3','r4']
              for p in (OUT.parent/parent).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    source_paths=['research/crypto_science/r5_participation_study.py',
                  'research/CRYPTO_SCIENCE_R5_PARTICIPATION_PREREG_2026-09-28.md',
                  'tests/test_btc_impulse_falsifier.py','collectors/okx.py','collectors/coinbase.py']
    source_hashes={p:r4.digest(ROOT/p) for p in source_paths}
    hourly=pd.read_parquet(data/'coinbase/btc_hourly.parquet');checked_index(hourly)
    daily=pd.read_parquet(data/'coinbase/btc_daily.parquet')
    base=pd.read_csv(prior/'incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    old_down=pd.read_csv(prior/'downside_events.csv');old_rec=pd.read_csv(prior/'recovery_events.csv')
    old_policy=pd.read_csv(prior/'policy_events.csv')
    old_policy.anchor=pd.to_datetime(old_policy.anchor)
    old_policy=old_policy.set_index(['family','rule','anchor','lag_hours','cost_bps'])
    down_anchors=pd.DatetimeIndex(pd.to_datetime(old_down.loc[old_down.rule=='d0','anchor'].unique())).sort_values()
    rec_anchors=pd.DatetimeIndex(pd.to_datetime(old_rec.anchor.unique())).sort_values()
    fresh_down=r4.onsets(r4.hourly_conditions(hourly).d0,step='1h',separation='24h')
    fresh_rec=r4.onsets(r4.daily_conditions(daily).washout,step='1D',separation='14D')
    assert fresh_down.equals(down_anchors)
    assert fresh_rec[fresh_rec>=pd.Timestamp('2016-01-01')].equals(rec_anchors)
    index=pd.date_range(hourly.index[0],hourly.index[-1],freq='h')
    maps={lag:r4.incumbent_targets(base,index,delay_hours=lag) for lag in [1,6]}
    events=[];policy=[];features=[]
    for a in down_anchors:
        obs=downside_observation(hourly,a);features.append(dict(family='downside',anchor=a,**obs))
        for lag in [1,6]:
            origin=a+(1+lag)*H;action=obs['issue']+lag*H;end=origin+24*H
            label=r4.barrier_label(hourly,action,hours=18,lower=-.05,upper=.03)
            price_known=obs['state']!='unknown';price_action=obs['state']=='persistent'
            vol_known=(not price_action) or obs['volume_ratio'] is not None
            vol_action=price_action and vol_known and obs['volume_ratio']>=1
            ev={'family':'downside','anchor':a,'origin':origin,'issue':obs['issue'],'entry':action,'end':end,
                'lag_hours':lag,'state':obs['state'],'volume_ratio':obs['volume_ratio'],
                'price_action':price_action,'volume_action':vol_action,'outcome':label['category'],
                'price_category':label['category'] if price_action else ('no_action' if price_known else 'unknown'),
                'volume_category':label['category'] if vol_action else ('no_action' if price_known and vol_known else 'unknown')}
            events.append(ev)
            w=r4.complete_window(hourly,origin,24)
            ix=pd.date_range(origin,end,freq='h');target=maps[lag].reindex(ix)
            status='incomplete_price_window' if w is None else ('incumbent_unavailable' if target.isna().any() else 'comparable')
            for cost in [0,10,25]:
                row=dict(ev,cost_bps=cost,status=status)
                if status!='comparable':policy.append(row);continue
                inc=r4.account_path(w.open,target.iloc[:-1],initial_weight=float(target.iloc[0]),terminal_weight=float(target.iloc[-1]),cost_bps=cost)
                late=r4.account_path(w.open,cash_after(target.iloc[:-1],action),initial_weight=float(target.iloc[0]),terminal_weight=float(target.iloc[-1]),cost_bps=cost)
                pc=(late if price_action else inc) if price_known else None
                vc=(late if vol_action else inc) if price_known and vol_known else None
                row.update(initial_exposure=float(target.iloc[0]),incumbent_return=inc['return'],
                           delayed_return=late['return'],delayed_minus_incumbent=late['return']-inc['return'],
                           price_return=pc['return'] if pc else None,volume_return=vc['return'] if vc else None,
                           price_minus_incumbent=pc['return']-inc['return'] if pc else None,
                           volume_minus_incumbent=vc['return']-inc['return'] if vc else None,
                           volume_minus_price=vc['return']-pc['return'] if pc and vc else None,
                           price_drawdown=pc['max_drawdown'] if pc else None,
                           volume_drawdown=vc['max_drawdown'] if vc else None,
                           incumbent_drawdown=inc['max_drawdown'],price_turnover=pc['turnover'] if pc else None,
                           volume_turnover=vc['turnover'] if vc else None)
                if not price_known:row['status']='price_unknown'
                elif not vol_known:row['status']='volume_unknown'
                key=('downside','d0',a,lag,cost)
                if key in old_policy.index:assert np.isclose(inc['return'],old_policy.loc[key].incumbent_return,atol=1e-12)
                policy.append(row)
    print(f'Downside evaluated on {len(down_anchors)} unchanged parents',flush=True)
    for a in rec_anchors:
        obs=early_reclaim(hourly,a);features.append(dict(family='recovery',anchor=a,**obs))
        for lag in [1,6]:
            origin=a+(24+lag)*H;end=origin+336*H
            action=obs['issue']+lag*H if obs['price_status']=='confirmed' else None
            accepted=obs['volume_status']=='accepted'
            label=(r4.barrier_label(hourly,action,hours=168,lower=-.03,upper=.05) if action is not None
                   else {'category':'no_entry' if obs['price_status']=='no_entry' else 'censored'})
            ev={'family':'recovery','anchor':a,'origin':origin,'issue':obs['issue'],'entry':action,'end':end,
                'lag_hours':lag,'state':obs['price_status'],'volume_ratio':obs['volume_ratio'],
                'volume_status':obs['volume_status'],'price_action':action is not None,'volume_action':accepted,
                'outcome':label['category'],'price_category':label['category'],
                'volume_category':label['category'] if accepted else ('unknown' if obs['price_status']=='unknown' or obs['volume_status']=='unknown' else 'no_entry')}
            events.append(ev);w=r4.complete_window(hourly,origin,336)
            ix=pd.date_range(origin,end,freq='h');target=maps[lag].reindex(ix)
            state='incomplete_price_window' if w is None else ('price_unknown' if obs['price_status']=='unknown' else 'comparable')
            for cost in [0,10,25]:
                row=dict(ev,cost_bps=cost,status=state)
                if state!='comparable':policy.append(row);continue
                held=np.zeros(336) if action is None else (ix[:-1]>=action).astype(float)
                vh=held if accepted else np.zeros(336)
                pc=r4.account_path(w.open,held,cost_bps=cost)
                vc=None if obs['volume_status']=='unknown' else r4.account_path(w.open,vh,cost_bps=cost)
                immediate=r4.account_path(w.open,np.ones(336),cost_bps=cost)
                inc=r4.account_path(w.open,target.iloc[:-1],cost_bps=cost) if not target.isna().any() else None
                key=('recovery','u1',a,lag,cost)
                oldrow=old_policy.loc[key] if key in old_policy.index else None
                if oldrow is not None:
                    assert np.isclose(immediate['return'],oldrow.immediate_return,atol=1e-12)
                    if inc:assert np.isclose(inc['return'],oldrow.incumbent_return,atol=1e-12)
                row.update(incumbent_return=inc['return'] if inc else None,
                           immediate_return=immediate['return'],daily_return=float(oldrow.candidate_return) if oldrow is not None else None,
                           price_return=pc['return'],volume_return=vc['return'] if vc else None,
                           price_minus_immediate=pc['return']-immediate['return'],
                           price_minus_daily=pc['return']-float(oldrow.candidate_return) if oldrow is not None else None,
                           price_minus_incumbent=pc['return']-inc['return'] if inc else None,
                           volume_minus_incumbent=vc['return']-inc['return'] if vc and inc else None,
                           volume_minus_price=vc['return']-pc['return'] if vc else None,
                           price_drawdown=pc['max_drawdown'],volume_drawdown=vc['max_drawdown'] if vc else None,
                           incumbent_drawdown=inc['max_drawdown'] if inc else None,
                           price_turnover=pc['turnover'],volume_turnover=vc['turnover'] if vc else None,
                           waiting_hours=float((action-origin)/H) if action is not None else None)
                if vc is None:row['status']='volume_unknown'
                policy.append(row)
    pframe=pd.DataFrame(scalar_records(policy));eframe=pd.DataFrame(scalar_records(events))
    fframe=pd.DataFrame(scalar_records(features));stats,groups=summarize(pframe,eframe)
    for name,expected in inputs.items():
        p=data/name;assert (r4.digest(p) if p.exists() else None)==expected,name
    assert gates=={p:r4.digest(data/p) for p in gates}
    assert evidence=={p:r4.digest(ROOT/p) for p in evidence}
    assert source_hashes=={p:r4.digest(ROOT/p) for p in source_hashes}
    for name,frame in [('features',fframe),('events',eframe),('policies',pframe)]:frame.to_csv(OUT/(name+'.csv'),index=False)
    result={'classification':'RETROSPECTIVE_SAME_PARENT_PARTICIPATION_NOT_LIVE_STRATEGY',
            'plan_commit':PLAN,'baseline':BASE,'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'inputs':inputs,'gates':gates,'prior_evidence':evidence,'sources':source_hashes,'hashes_unchanged':True,
            'counts':{'downside_parents':len(down_anchors),'recovery_parents':len(rec_anchors),'events':len(events),'policies':len(policy)},
            'policy_summaries':stats,'event_summaries':groups,
            'limitations':['Unsigned Coinbase spot volume is participation, not measured absorption.',
                           'OKX CONTRACTS aggressor flow is not interchangeable with spot; not included.',
                           'Historical bars/target vintages and execution assumptions are not live proof.',
                           'Same parents repeated across costs/delays; no independent-sample inflation.',
                           'All periods previously used; no fresh holdout or calibrated current probability.']}
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
    print(json.dumps({'counts':result['counts'],'summary_rows':len(stats),'hashes_unchanged':True},indent=2))


if __name__=='__main__':main()
