"""Separate arithmetic/condition reproduction of R5; not independent-person review."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config
from research.crypto_science.r4.verify_evidence import independent_wealth
HERE=Path(__file__).resolve().parent;H=pd.Timedelta(hours=1)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def good_price(w):
    x=w[['open','high','low','close']].to_numpy(float)
    return (np.isfinite(x).all() and (x>0).all() and
            (x[:,1]>=x.max(axis=1)).all() and (x[:,2]<=x.min(axis=1)).all())


def vol_ratio(hourly,active,ref):
    a=hourly.volume.reindex(active).to_numpy(float);b=hourly.volume.reindex(ref).to_numpy(float)
    if not (np.isfinite(a).all() and np.isfinite(b).all() and (a>=0).all() and (b>=0).all()):return np.nan
    m=np.median(b)
    return a.sum()/len(a)/m if m>0 else np.nan


def equal(a,b):
    assert (pd.isna(a) and pd.isna(b)) or np.isclose(a,b,atol=1e-10,rtol=1e-9),(a,b)


def main():
    r=json.loads((HERE/'results.json').read_text());data=Path(config.data_dir())
    assert r['plan_commit']=='3cc4e46d2b7827ba5fce746d5b4bcd1875fb80c6'
    for key in ['prior_evidence','sources']:
        assert all(sha(ROOT/p)==h for p,h in r[key].items()),key
    assert all((sha(data/p) if (data/p).exists() else None)==h for p,h in r['inputs'].items())
    assert all(sha(data/p)==h for p,h in r['gates'].items())
    old=json.loads((HERE.parent/'r4/results.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in old['sources'].items()), 'Inherited R4 engine/config source drift'
    hourly=pd.read_parquet(data/'coinbase/btc_hourly.parquet')
    features=pd.read_csv(HERE/'features.csv');events=pd.read_csv(HERE/'events.csv');policy=pd.read_csv(HERE/'policies.csv')
    assert not features.duplicated(['family','anchor']).any()
    assert not events.duplicated(['family','anchor','lag_hours']).any()
    assert not policy.duplicated(['family','anchor','lag_hours','cost_bps']).any()
    assert len(events)==r['counts']['events'] and len(policy)==r['counts']['policies']
    for row in features.itertuples():
        a=pd.Timestamp(row.anchor)
        if row.family=='downside':
            ref=pd.date_range(a-72*H,periods=72,freq='h');cur=pd.date_range(a+H,periods=6,freq='h')
            x=hourly.reindex(ref);y=hourly.reindex(cur)
            state='unknown'
            if good_price(x) and good_price(y):
                state='reclaimed' if y.close.iloc[-1]>=x.low.min() else ('persistent' if y.low.iloc[3:].min()<y.low.iloc[:3].min() else 'stalled_below')
            assert row.state==state
            assert pd.Timestamp(row.issue)==a+7*H
            equal(row.volume_ratio,vol_ratio(hourly,cur,ref))
        else:
            state='no_entry';date=None;ratio=np.nan;vs='not_needed'
            for k in range(6,48):
                t=a+(24+k)*H;w=hourly.reindex(pd.date_range(t-6*H,periods=7,freq='h'))
                if not good_price(w):state='unknown';break
                if w.close.iloc[-1]>w.high.iloc[:-1].max() and w.low.iloc[-3:].min()>=w.low.iloc[-6:-3].min():
                    state='confirmed';date=t
                    ratio=vol_ratio(hourly,pd.date_range(t-2*H,periods=3,freq='h'),pd.date_range(t-74*H,periods=72,freq='h'))
                    vs='unknown' if pd.isna(ratio) else ('accepted' if ratio>=1 else 'rejected')
                    break
            assert row.price_status==state and row.volume_status==vs
            assert pd.isna(row.signal_start) if date is None else pd.Timestamp(row.signal_start)==date
            equal(row.volume_ratio,ratio)
    barrier_checks=0
    for row in events.itertuples():
        a=pd.Timestamp(row.anchor);origin=a+(1 if row.family=='downside' else 24)*H+row.lag_hours*H
        assert pd.Timestamp(row.origin)==origin
        assert pd.Timestamp(row.end)==origin+(24 if row.family=='downside' else 336)*H
        if pd.isna(row.entry):continue
        entry=pd.Timestamp(row.entry);hours=18 if row.family=='downside' else 168
        assert entry==pd.Timestamp(row.issue)+row.lag_hours*H
        w=hourly.reindex(pd.date_range(entry,periods=hours+1,freq='h'))
        if not good_price(w.iloc[:-1]) or not np.isfinite(w.open.iloc[-1]) or w.open.iloc[-1]<=0:
            assert row.outcome=='censored';continue
        ref=w.open.iloc[0];lo=ref*(.95 if row.family=='downside' else .97);hi=ref*(1.03 if row.family=='downside' else 1.05)
        category='neither'
        for b in w.iloc[:-1].itertuples():
            if b.open<=lo:category='lower_first'
            elif b.open>=hi:category='upper_first'
            elif b.low<=lo and b.high>=hi:category='ambiguous'
            elif b.low<=lo:category='lower_first'
            elif b.high>=hi:category='upper_first'
            else:continue
            break
        assert row.outcome==category
        barrier_checks+=1
    baseline=pd.read_csv(HERE.parent/'r4/incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    accounting=0
    for row in policy.itertuples():
        if pd.isna(row.incumbent_return) and pd.isna(row.price_return):continue
        ix=pd.date_range(row.origin,row.end,freq='h');p=hourly.open.reindex(ix).to_numpy(float);n=len(p)-1
        dates=(ix-pd.Timedelta(hours=row.lag_hours)).normalize()-pd.Timedelta(days=1)
        target=baseline.reindex(dates).to_numpy(float);cost=row.cost_bps
        if row.family=='downside':
            inc=independent_wealth(p,target[:-1],target[0],target[-1],cost)-1
            ct=target[:-1].copy();ct[ix[:-1]>=pd.Timestamp(row.entry)]=0
            late=independent_wealth(p,ct,target[0],target[-1],cost)-1
            equal(inc,row.incumbent_return);equal(late,row.delayed_return)
            pc=(late if row.price_action else inc) if row.state!='unknown' else np.nan
            vc=(late if row.volume_action else inc) if row.status not in ['price_unknown','volume_unknown'] else np.nan
        else:
            held=np.zeros(n) if pd.isna(row.entry) else (ix[:-1]>=pd.Timestamp(row.entry)).astype(float)
            pc=independent_wealth(p,held,0,0,cost)-1
            vh=held if row.volume_action else np.zeros(n)
            vc=independent_wealth(p,vh,0,0,cost)-1 if row.volume_status!='unknown' else np.nan
            imm=independent_wealth(p,np.ones(n),0,0,cost)-1
            equal(imm,row.immediate_return)
            if np.isfinite(target).all():equal(independent_wealth(p,target[:-1],0,0,cost)-1,row.incumbent_return)
        equal(pc,row.price_return);equal(vc,row.volume_return);equal(vc-pc,row.volume_minus_price)
        accounting+=1
    bounds={'full':('2016-01-01','2026-09-27'),'2016_2019':('2016-01-01','2020-01-01'),
            '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2026-09-27')}
    for s in r['policy_summaries']:
        lo,hi=map(pd.Timestamp,bounds[s['period']]);a=pd.to_datetime(policy.anchor);e=pd.to_datetime(policy.end)
        f=policy.loc[(policy.family==s['family'])&(policy.lag_hours==s['lag_hours'])&(policy.cost_bps==s['cost_bps'])&(a>=lo)&(a<hi)&(e<hi)]
        assert len(f)==s['parents']
        for col,v in s['stats'].items():
            x=f[col].dropna();assert len(x)==v['n'];equal(x.mean(),v['mean']);equal(x.median(),v['median'])
            valid=f.dropna(subset=[col])
            if valid.empty:
                assert v['block95'] is None
                continue
            block=((pd.to_datetime(valid.anchor)-pd.Timestamp('2016-01-01'))/pd.Timedelta(days=90)).astype(int)
            if block.nunique()<2:
                assert v['block95'] is None
            else:
                domain=np.arange(block.min(),block.max()+1)
                totals=np.array([valid.loc[block==b,col].sum() for b in domain])
                sizes=np.array([(block==b).sum() for b in domain])
                draw=np.random.default_rng(20260928).integers(0,len(domain),(1000,len(domain)))
                ns=sizes[draw].sum(axis=1);sums=totals[draw].sum(axis=1)
                ci=np.quantile(sums[ns>0]/ns[ns>0],[.025,.975])
                assert np.allclose(ci,v['block95'],atol=1e-10)
    for s in r['event_summaries']:
        lo,hi=map(pd.Timestamp,bounds[s['period']]);a=pd.to_datetime(events.anchor);e=pd.to_datetime(events.end)
        f=events.loc[(events.family==s['family'])&(events.lag_hours==s['lag_hours'])&(events.state==s['state'])&(a>=lo)&(a<hi)&(e<hi)]
        assert len(f)==s['n']
        assert f.price_category.value_counts().to_dict()==s['price_categories']
        assert f.volume_category.value_counts().to_dict()==s['volume_categories']
    print(f'R5_VERIFIED: {len(features)} parent observations, {barrier_checks} mature barrier paths, {accounting} independent inventory accounts, {len(r["policy_summaries"])} policy summaries including all block intervals and event groups.')
    print(f'R5_HASHES: {len(r["inputs"])} input identities, {len(r["gates"])} gates, {len(r["prior_evidence"])} prior evidence files unchanged.')
    print('Same-session independent arithmetic, not independent-review or production acceptance.')


if __name__=='__main__':main()
