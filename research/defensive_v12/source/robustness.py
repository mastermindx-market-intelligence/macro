"""V12 paired diagnostics. Reuses the previously tested shared-quarter block
interval routine; no threshold fitting or multiplicity-adjusted alpha claim.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
import cycle_failure as c
sys.path.insert(0,str(c.V11))
from regime_audit import block_interval
R=Path(__file__).resolve().parent;O=R/'results'
KEY=['symbol','frame','episode']

def paired(events,a,b):
    left=events[events.policy==a].copy();right=events[events.policy==b][KEY+['net','mae']]
    g=left.merge(right,on=KEY,validate='one_to_one',suffixes=('','_reference'))
    if len(g)!=len(left):raise ValueError('Different opportunity coverage')
    g['paired_delta']=g.net-g.net_reference;return g

def run():
    event=pd.read_csv(O/'event_policies.csv');diag=[];stock=[]
    pairs=[('ATR6','ATR3'),('STRUCTURE_ATR6','ATR6'),('STRUCTURE_MOMENTUM_ATR6','STRUCTURE_ATR6'),('STRUCTURE_MOMENTUM_ATR6','ATR6'),('STAGED_ATR6','ATR6'),('STAGED_ATR6','STRUCTURE_MOMENTUM_ATR6'),('SLOW_STAGE_ATR6','STAGED_ATR6'),('SLOW_STAGE_ATR6','ATR6')]
    for a,b in pairs:
        g=paired(event,a,b)
        for (panel,frame),x in g.groupby(['panel','frame']):
            z=block_interval(x,column='paired_delta',rep=3000)
            years=pd.to_datetime(x.arm_date).dt.year;loo=[]
            for y in sorted(years.unique()):
                other=x[years!=y]
                if len(other):loo.append(float(other.paired_delta.mean()))
            ls=[float(x[x.symbol!=s].paired_delta.mean()) for s in x.symbol.unique() if (x.symbol!=s).any()]
            diag.append({'panel':panel,'frame':frame,'policy':a,'reference':b,'n':len(x),'mean_delta':x.paired_delta.mean(),'mae_difference':float((x.mae-x.mae_reference).mean()),'active_quarters':z['quarters'],'block_low':z['low'],'block_high':z['high'],'leave_year_min':min(loo),'leave_year_max':max(loo),'leave_stock_min':min(ls),'leave_stock_max':max(ls),'better_at_endpoint':int((x.paired_delta>1e-12).sum()),'worse_at_endpoint':int((x.paired_delta<-1e-12).sum()),'unchanged':int((x.paired_delta.abs()<=1e-12).sum())})
        for (sym,frame),x in g.groupby(['symbol','frame']):stock.append({'symbol':sym,'frame':frame,'policy':a,'reference':b,'n':len(x),'mean_delta':float(x.paired_delta.mean()),'median_delta':float(x.paired_delta.median())})
    pd.DataFrame(diag).to_csv(O/'paired_diagnostics.csv',index=False);pd.DataFrame(stock).to_csv(O/'paired_by_stock.csv',index=False)
    accounts=pd.read_csv(O/'account_summary.csv');core=accounts[(accounts.panel=='CORE5')&(accounts.cost_bps==10)];expensive=accounts[(accounts.panel=='CORE5')&(accounts.cost_bps==30)]
    merged=core.merge(expensive,on=['symbol','frame','policy'],suffixes=('_10','_30'),validate='one_to_one')
    merged[['symbol','frame','policy','cagr_10','cagr_30','max_drawdown_10','max_drawdown_30','entries_10','entries_30']].to_csv(O/'cost_sensitivity.csv',index=False)
    # A known-at-reentry audit, not a gate fitted to the outcomes.
    retries=pd.read_csv(O/'reclaim_event_results.csv');retries=retries[retries.attempt_count==2].copy()
    for sym,g in retries.groupby('symbol'):
        cache=pd.read_pickle(c.V11/'results'/f'{sym}_cache.pkl')
        for i,row in g.iterrows():
            t=pd.Timestamp(row.retry_signal_date);w=cache['slow']['confirmed_W'].loc[t];b=cache['slow']['confirmed_2W_0'].loc[t]
            retries.loc[i,'retry_market_regime']=cache['regime'].loc[t,'market_regime'];retries.loc[i,'retry_weekly_hist']=w['hist'];retries.loc[i,'retry_weekly_hist_change']=w['change'];retries.loc[i,'retry_two_week_hist']=b['hist'];retries.loc[i,'retry_two_week_k']=b['k']
    retries.to_csv(O/'reclaim_context_audit.csv',index=False)
    # Every modified-source completed event must still reconcile to its original output.
    maxerr=0.;checks=0
    for sym in c.e.CORE:
        cache=pd.read_pickle(c.V11/'results'/f'{sym}_cache.pkl');d=cache['daily']
        for frame in ['1D','2D']:
            f=c.features(cache,frame)
            for t in event[(event.symbol==sym)&(event.frame==frame)].itertuples():
                sig=int(d.index.get_loc(pd.Timestamp(t.signal_date)));arm=int(d.index.get_loc(pd.Timestamp(t.arm_date)));end=int(d.index.get_loc(pd.Timestamp(t.endpoint_date)))
                r=c.simulate(d,f,sig,arm,end,t.policy);maxerr=max(maxerr,abs(r['net']-t.net));checks+=1
    assert maxerr<1e-12
    qa={'completed_event_version_checks':checks,'max_final_source_vs_original_event_error':maxerr,'paired_intervals':'four-consecutive-calendar-quarter bootstrap,3000draws; descriptive, overlapping outcomes, unadjusted for8contrasts and prior research','source_artifact':'final V12 source only; no original data changes','reentry_note':'isolated-watch events, not an account; common-market dependence and7core daily retries limit inference','v11_source_unchanged':all(hashlib.sha256((c.V11/n).read_bytes()).hexdigest()==v for n,v in json.loads((R/'spec.json').read_text())['v11_hashes'].items())}
    (O/'robustness_verification.json').write_text(json.dumps(qa,indent=2))
    print('CORE_DAILY_PAIRED',pd.DataFrame(diag).query("panel=='CORE5' and frame=='1D'").round(6).to_json(orient='records'),flush=True)
    print('VERIFICATION',json.dumps(qa),flush=True)

if __name__=='__main__':run()
