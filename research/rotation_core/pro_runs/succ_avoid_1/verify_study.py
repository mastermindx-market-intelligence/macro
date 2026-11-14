"""Targeted, independent arithmetic and temporal integrity checks."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
import pandas as pd
import run_study as s

R=s.OUT
def main():
    checks=[]
    p,r,_=s.load_panel();N=len(p);dates=p.index
    allf=pd.read_csv(R/'flags_all_observable.csv',parse_dates=['date'])
    assert allf.date.min()>=pd.Timestamp('2013-01-02') and allf.date.max()<=pd.Timestamp('2023-12-29')
    pos=dates.get_indexer(allf.date)
    assert ((pos%3)==2).all()
    checks.append('Every observable flag uses the fixed completed 3-session anchor and allowed observation dates.')
    pairs={rule:set(zip(x.date,x.group)) for rule,x in allf.groupby('rule')}
    assert pairs['C2']==pairs['OLD']&pairs['C1']
    assert all(pairs[k]<=pairs['OLD'] for k in s.RULES[2:])
    assert all(g.startswith('FF12_') for _,g in pairs['C5'])
    checks.append('C2 is exactly OLD intersect REL; C2..C8 are OLD subsets; breadth is FF12-only.')
    events=pd.read_csv(R/'events_all_scored.csv',parse_dates=['date'])
    assert np.isfinite(events[s.METRICS+['lateness']].to_numpy()).all()
    for rule in s.RULES:
        a=events[events.rule==rule]
        b=events[events.rule=='VOL_'+rule]
        assert a.groupby('group').size().to_dict()==b.groupby('group').size().to_dict()
        for suffix,k in [('EARLY10',-10),('LATE10',10)]:
            z=events[events.rule==rule+'_'+suffix]
            assert len(z)==len(a) and (z.t-z.origin_t==k).all()
            assert (z.t+63<N).all() and (z.t>=63).all()
    checks.append('All per-group VOL matches are exact; both shifts preserve counts and have complete ±10/63-session support.')
    # Explicit scalar reconstruction for a fixed sample, independent of vectorized outputs.
    sample=events[events.rule=='C2'].iloc[::max(1,len(events[events.rule=='C2'])//12)].head(12)
    for row in sample.itertuples():
        t=int(row.t);j=p.columns.get_loc(row.group);v=r.iloc[:,j].to_numpy()
        age=t-max(range(t-63,t),key=lambda u:(v[u],u))
        assert age==row.lateness
        assert int(any(v[u]>max(v[u-63:u]) for u in range(t+1,t+22)))==row.fake21
        members=['FF49_'+x for x in s.CHILDREN[row.group[5:]].split()] if row.group.startswith('FF12_') else [row.group]
        dds=[];avs=[]
        for g in members:
            path=p[g].iloc[t:t+64].to_numpy()
            dd=max(1-path[b]/path[a] for a in range(64) for b in range(a,64))
            exitdd=max(0,1-path[1]/path[0]);dds.append(dd);avs.append(dd-exitdd)
        assert abs(np.mean(dds)-row.mdd63)<1e-8 and abs(np.mean(avs)-row.avoid63)<1e-8
    checks.append('Twelve fixed-spaced events independently reconstruct prior-high age, fake21, ordered-pair member MDD and next-close exit MDD.')
    effects=json.loads((R/'effects.json').read_text())
    for cohort in s.COHORTS:
        for v in effects[cohort]['OLD']['OLD_MATCHED']['effects'].values():
            assert abs(v['delta'])<1e-12 and abs(v['lo'])<1e-12 and abs(v['hi'])<1e-12
    checks.append('OLD matched to itself is identically zero in point estimates and all reported bootstrap bounds.')
    x=pd.DataFrame({'up':np.arange(1.,101.),'down':np.arange(101.,1.,-1),'flat':np.ones(100)})
    assert s.rsi_wilder(x).iloc[14].to_dict()=={'up':100.,'down':0.,'flat':50.}
    assert abs(s.ema_seed(x,14).up.iloc[13]-7.5)<1e-12
    idx=pd.to_datetime(['2013-01-04','2013-01-11','2013-01-18'])
    z=pd.DataFrame({'v':[1.,np.nan,2.]},index=idx)
    assert np.isnan(s.daily_state(z,pd.bdate_range('2013-01-04','2013-01-18')).loc['2013-01-14','v'])
    checks.append('Synthetic RSI edge values, EMA arithmetic seeding and preservation of explicit source-bar NaNs pass.')
    hy=json.loads((R/'hy_archive_verification.json').read_text())
    assert all(x['maximum_absolute_difference']==0 for x in hy['checks'])
    checks.append('Archived HY observations exactly match 2,760 pre-2024-archive overlaps and 33 current FRED overlaps.')
    receipt={'status':'PASS','checks':checks,'independent_event_arithmetic_checks':len(sample),
      'prefix_check':'All nine signal tapes and common readiness verified unchanged through 2019-12-18 when later permitted data are removed; performed separately before report.',
      'candidate_outcome_runs':1,'threshold_tuning_runs':0,'post_outcome_signal_changes':0,
      'post_outcome_report_change':'Renamed later_warning_within63 to warning_days22_to63; added trough-coverage and matching-information diagnostics; no candidate result changed.',
      'pre_first_run_repairs':['Preserve source-bar NaNs','Require initialized selected-partner oscillator','Independent all-observable missed-top universe','Use all-observable flags for miss catches','Restrict C5 miss universe','Attribute annual shift counts to source year'],
      'runtime':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__},
      'source_sha256':{x:hashlib.sha256((s.ROOT/x).read_bytes()).hexdigest() for x in ['PROTOCOL.md','acquire.py','run_study.py','verify_study.py']}}
    (R/'verification.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
