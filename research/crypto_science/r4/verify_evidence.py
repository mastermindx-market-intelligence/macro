"""Independently verify R4 dates, counts, target ordering and account arithmetic.

A pass verifies this retrospective evidence; it does not approve a strategy.
"""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent
H=pd.Timedelta(hours=1)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_wealth(prices,targets,initial,terminal,bps):
    prices=np.asarray(prices,float); cash=1-initial; coins=initial/prices[0]; last=initial
    fee=bps/10000
    for price,target in zip(prices[:-1],targets):
        if target!=last:
            wealth=cash+coins*price
            before=coins*price/wealth
            wealth*=1-fee*abs(target-before)
            coins=wealth*target/price;cash=wealth*(1-target);last=target
    wealth=cash+coins*prices[-1]
    return wealth*(1-fee*abs(terminal-coins*prices[-1]/wealth))


def main():
    r=json.loads((HERE/'results.json').read_text())
    assert r['plan_commit']=='c458e016b094bbf28f6e4d89f5e622a56e92e697'
    assert r['hashes_unchanged'] is True
    data=Path(config.data_dir())
    assert all(sha(ROOT/p)==h for p,h in r['sources'].items())
    assert all((sha(data/p) if (data/p).exists() else None)==h for p,h in r['input_hashes'].items())
    assert all(sha(data/p)==h for p,h in r['gate_hashes'].items())
    assert all(sha(ROOT/p)==h for p,h in r['prior_evidence_hashes'].items())
    events={f:pd.read_csv(HERE/(f+'_events.csv')) for f in ['downside','recovery']}
    policy=pd.read_csv(HERE/'policy_events.csv')
    bounds={'full':('2016-01-01','2027-01-01'),'2016_2019':('2016-01-01','2020-01-01'),
            '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}
    for family,f in events.items():
        assert not f.duplicated(['rule','anchor','lag_hours']).any()
        for _,row in f.iterrows():
            anchor=pd.Timestamp(row.anchor);issue=pd.Timestamp(row.issue)
            assert issue==anchor+(H if family=='downside' else pd.Timedelta(days=1))
            if family=='downside' or row.rule=='u0':
                assert pd.Timestamp(row.entry)==issue+row.lag_hours*H
            if family=='recovery' and row.rule=='u1' and pd.notna(row.entry):
                assert pd.Timestamp(row.entry)==pd.Timestamp(row.confirmation_date)+pd.Timedelta(days=1)+row.lag_hours*H
                assert anchor<pd.Timestamp(row.confirmation_date)<=anchor+pd.Timedelta(days=7)
        for (_,lag),g in f.groupby(['rule','lag_hours']):
            spacing=pd.to_datetime(g.anchor).sort_values().diff().dropna()
            assert (spacing>(24*H if family=='downside' else pd.Timedelta(days=14))).all()
    for s in r['event_summaries']:
        f=events[s['family']];lo,hi=map(pd.Timestamp,bounds[s['period']]);a=pd.to_datetime(f.anchor)
        g=f.loc[(a>=lo)&(a<hi)&(f.rule==s['rule'])&(f.lag_hours==s['lag_hours'])].copy()
        g.loc[pd.to_datetime(g.end)>=hi,'category']='censored'
        assert len(g)==s['parents']
        assert {str(k):int(v) for k,v in g.category.value_counts().items()}==s['categories']
        mature=g.loc[~g.category.isin(['censored','no_entry'])]
        target='lower_first' if s['family']=='downside' else 'upper_first'
        assert len(mature)==s['mature_entries'] and mature.category.eq(target).sum()==s['successes']
        if len(mature): assert np.isclose(mature.category.eq(target).mean(),s['hit_fraction'])
    for s in r['policy_summaries']:
        lo,hi=map(pd.Timestamp,bounds[s['period']]);a=pd.to_datetime(policy.anchor)
        g=policy.loc[(policy.family==s['family'])&(policy.rule==s['rule'])&(policy.lag_hours==s['lag_hours'])
                     &(policy.cost_bps==s['cost_bps'])&(a>=lo)&(a<hi)&(pd.to_datetime(policy.end)<hi)]
        assert len(g)==s['n_parents']
        for k,stats in s['stats'].items():
            vals=g[k].dropna();assert len(vals)==stats['n']
            if len(vals):
                assert np.isclose(vals.mean(),stats['mean'],atol=1e-12)
                assert np.isclose(vals.median(),stats['median'],atol=1e-12)
    f=policy.loc[policy.family=='recovery']
    assert np.allclose(f.candidate_minus_immediate,f.candidate_return-f.immediate_return,atol=1e-12)
    assert np.allclose(f.candidate_minus_matched_ex_post,f.candidate_return-f.matched_duration_return_ex_post,atol=1e-12)
    assert np.allclose(f.loc[f.confirmation_state=='no_entry','candidate_return'],0.)
    assert f.duration_matched_fraction_ex_post.between(0,1).all()
    f=policy.dropna(subset=['candidate_minus_incumbent'])
    assert np.allclose(f.candidate_minus_incumbent,f.candidate_return-f.incumbent_return,atol=1e-12)
    hourly=pd.read_parquet(data/'coinbase/btc_hourly.parquet')
    checked=0
    for family,f in events.items():
        for _,row in f.iterrows():
            if pd.isna(row.entry):
                continue
            entry=pd.Timestamp(row.entry);hours=24 if family=='downside' else 168
            ix=pd.date_range(entry,periods=hours+1,freq='h')
            w=hourly.reindex(ix)[['open','high','low','close']]
            held=w.iloc[:-1]
            ok=(np.isfinite(held).all().all() and (held>0).all().all()
                and np.isfinite(w.open.iloc[-1]) and w.open.iloc[-1]>0
                and (held.high>=held[['open','low','close']].max(axis=1)).all()
                and (held.low<=held[['open','high','close']].min(axis=1)).all())
            if not ok:
                assert row.category=='censored';continue
            ref=w.open.iloc[0];lower=ref*(.95 if family=='downside' else .97)
            upper=ref*(1.03 if family=='downside' else 1.05)
            category='neither'
            for b in held.itertuples():
                if b.open<=lower:category='lower_first'
                elif b.open>=upper:category='upper_first'
                elif b.low<=lower and b.high>=upper:category='ambiguous'
                elif b.low<=lower:category='lower_first'
                elif b.high>=upper:category='upper_first'
                else:continue
                break
            assert row.category==category,(row.anchor,row.rule,row.lag_hours)
            assert np.isclose(row.terminal_return,w.open.iloc[-1]/ref-1,atol=1e-12)
            checked+=1
    baseline=pd.read_csv(HERE/'incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    account_checks=0
    for row in policy.itertuples():
        idx=pd.date_range(row.entry,row.end,freq='h');p=hourly.open.reindex(idx).to_numpy()
        dates=(idx-pd.Timedelta(hours=row.lag_hours)).normalize()-pd.Timedelta(days=1)
        target=baseline.reindex(dates).to_numpy();fee=row.cost_bps;n=len(p)-1
        if row.family=='downside':
            inc=independent_wealth(p,target[:-1],target[0],target[-1],fee)
            cash=independent_wealth(p,np.zeros(n),target[0],target[-1],fee)
            fixed=independent_wealth(p,np.full(n,target[0]),target[0],target[0],fee)
            assert np.isclose(inc-1,row.incumbent_return,atol=1e-10)
            assert np.isclose(cash-1,row.candidate_return,atol=1e-10)
            assert np.isclose(fixed-1,row.fixed_initial_return,atol=1e-10)
        else:
            held=np.zeros(n) if pd.isna(row.candidate_entry) else (idx[:-1]>=pd.Timestamp(row.candidate_entry)).astype(float)
            cand=independent_wealth(p,held,0,0,fee)
            full=independent_wealth(p,np.ones(n),0,0,fee)
            matched=independent_wealth(p,np.full(n,held.mean()),0,0,fee)
            assert np.isclose(cand-1,row.candidate_return,atol=1e-10)
            assert np.isclose(full-1,row.immediate_return,atol=1e-10)
            assert np.isclose(matched-1,row.matched_duration_return_ex_post,atol=1e-10)
            if np.isfinite(target).all():
                inc=independent_wealth(p,target[:-1],0,0,fee)
                assert np.isclose(inc-1,row.incumbent_return,atol=1e-10)
        account_checks+=1
    print(f'R4_PATHS_VERIFIED: {checked} mature first-passage paths; {account_checks} cash/coin-account checks independent of the research weight recurrence.')
    print(f'R4_COUNTS_VERIFIED: {sum(map(len,events.values()))} event rows; {len(policy)} account rows; all summary arithmetic agrees.')
    print(f'R4_HASHES_VERIFIED: {len(r["input_hashes"])} input identities, {len(r["gate_hashes"])} gates and {len(r["prior_evidence_hashes"])} prior evidence files unchanged.')
    print('RETROSPECTIVE ONLY: no whole-portfolio performance, calibrated probability, independent review or live acceptance implied.')


if __name__=='__main__': main()
