"""One bounded reclaim attempt inside a fixed original watch outcome window.
This is an isolated-event comparison, NOT an account allocator: other-watch
order competition during the reclaim wait is deliberately not modeled.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import cycle_failure as c
R=Path(__file__).resolve().parent;O=R/'results'

def simulate(d,f,signal_i,arm_i,endpoint_i,policy,fee=.0005,marked=False):
    if policy not in ['STRUCTURE_MOMENTUM_ATR6','STAGED_ATR6']:raise ValueError('Declared reclaim policies only')
    first=c.simulate(d,f,signal_i,arm_i,endpoint_i,policy,fee=fee,marked=True)
    if first['status']!='FILLED':return first
    marks=first.pop('marks');leg1=first.copy();result=first.copy();result['attempt_count']=1;result['legs']=[leg1];result['without_reentry']=first['net'];result['retry_signal_date']=None
    if first['reason'].startswith(('STOP','STRUCTURE')):
        floor=first['structure_floor'];exit_i=first['exit_i'];retry=None
        for i in range(exit_i+1,min(exit_i+20,endpoint_i-1,len(d)-2)+1):
            if bool(f.lower_bull.iloc[i]) and d.close.iloc[i]>floor and np.isfinite(f.weekly_k.iloc[i]) and f.weekly_k.iloc[i]<80:
                retry=i;break
        if retry is not None:
            second=c.simulate(d,f,retry,arm_i,endpoint_i,policy,fee=fee,marked=True,fixed_floor=floor)
            m2=second.pop('marks');capital=1+first['net']
            marks += [(i,capital,capital,False) for i in range(exit_i+1,retry+1)]
            marks += [(i,capital*v,capital*low,exposed) for i,v,low,exposed in m2]
            result.update(attempt_count=2,net=capital*(1+second['net'])-1,exit_i=second['exit_i'],exit_date=second['exit_date'],reason='REENTRY_'+second['reason'],held_sessions=first['held_sessions']+second['held_sessions'],retry_signal_date=str(d.index[retry].date()))
            result['legs'].append(second)
    result['incremental']=result['net']-result['baseline'];result['reentry_delta']=result['net']-result['without_reentry']
    result['capital_mae']=min(0,min(z[2] for z in marks)-1);result['close_peak']=max(0,max(z[1] for z in marks)-1)
    if marked:result['marks']=marks
    return result

def run():
    base=pd.read_csv(O/'event_policies.csv');base=base[base.policy=='HOLD'];rows=[];legs=[]
    for sym in c.e.STOCKS:
        cache=pd.read_pickle(c.V11/'results'/f'{sym}_cache.pkl');d=cache['daily']
        for frame in ['1D','2D']:
            f=c.features(cache,frame)
            for t in base[(base.symbol==sym)&(base.frame==frame)].itertuples():
                signal=int(d.index.get_loc(pd.Timestamp(t.signal_date)));arm=int(d.index.get_loc(pd.Timestamp(t.arm_date)));endpoint=int(d.index.get_loc(pd.Timestamp(t.endpoint_date)))
                for policy in ['STRUCTURE_MOMENTUM_ATR6','STAGED_ATR6']:
                    x=simulate(d,f,signal,arm,endpoint,policy);ll=x.pop('legs')
                    tag={'symbol':sym,'panel':t.panel,'frame':frame,'episode':t.episode,'arm_date':t.arm_date,'signal_date':t.signal_date,'policy':policy}
                    rows.append(tag|x);legs.extend([tag|leg|{'attempt':i+1} for i,leg in enumerate(ll)])
    result=pd.DataFrame(rows);result.to_csv(O/'reclaim_event_results.csv',index=False);pd.DataFrame(legs).to_csv(O/'reclaim_legs.csv',index=False)
    out=[]
    for keys,g in result.groupby(['panel','frame','policy']):
        out.append(dict(zip(['panel','frame','policy'],keys))|{'n':len(g),'two_attempt_events':int(g.attempt_count.eq(2).sum()),'win':float(g.net.gt(0).mean()),'mean':float(g.net.mean()),'no_reentry_mean':float(g.without_reentry.mean()),'mean_reentry_delta':float(g.reentry_delta.mean()),'mean_incremental_vs_hold':float(g.incremental.mean()),'mean_capital_mae':float(g.capital_mae.mean()),'worst_capital_mae':float(g.capital_mae.min()),'rescued_positive':int(((g.without_reentry<=0)&(g.net>0)).sum()),'worsened_to_loss':int(((g.without_reentry>0)&(g.net<=0)).sum())})
    s=pd.DataFrame(out);s.to_csv(O/'reclaim_summary.csv',index=False)
    print('RECLAIM_DAILY',s[s.frame=='1D'].round(6).to_json(orient='records'),flush=True)

if __name__=='__main__':run()
