"""Exploratory 252-session horizon sensitivity using unchanged V12 policies.
No new entries or economic filters. Matched mature-episode126-vs252 comparison
is retained separately from open-ended single-position account simulations.
"""
from pathlib import Path
import json,datetime
import numpy as np
import pandas as pd
import cycle_failure as c
from account_replay import account
R=Path(__file__).resolve().parent;O=R/'results'

def run():
    spec={'status':'Added after126-session results, exploratory, no blind-holdout claim','reason':'A slow2W recovery may need more than sixmonths; avoid concluding exitclock fitness solely from126-session cap','change':'Only arm-anchored horizon126 versus252; fixed original first-fresh entries and all7policies','event_comparability':'Use only episodes with252 complete sessions for BOTH horizon comparisons; no outcome-value selection','account':'All known original watches, single position,0cashyield,10bpcost; mark open ends, do not force liquidation','frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (R/'horizon_spec.json').write_text(json.dumps(spec,indent=2))
    event=[];accounts=[]
    for sym in c.e.STOCKS:
        cache=pd.read_pickle(c.V11/'results'/f'{sym}_cache.pkl');d=cache['daily'];start=int(d.index.searchsorted('2018-01-01'))
        w=pd.read_csv(c.V11/'results'/f'{sym}_watches.csv');w=w[(w['mode']=='confirmed')&(w.two_week_phase==0)&(w.lower_phase==0)&(w.warmup==200)]
        for frame in ['1D','2D']:
            f=c.features(cache,frame);ws=w[w.frame==frame].sort_values('arm_i').to_dict('records')
            for policy in c.POLICIES:
                a=account(d,f,ws,policy,horizon=252,start_i=start)
                accounts.append({'symbol':sym,'panel':'CORE5' if sym in c.e.CORE else 'PEERS13','frame':frame,'policy':policy,'horizon':252}|a['summary'])
            for t in ws:
                if pd.isna(t['signal_i']) or int(t['arm_i'])+252>=len(d):continue
                si=int(t['signal_i']);arm=int(t['arm_i'])
                for h in [126,252]:
                    for policy in c.POLICIES:
                        x=c.simulate(d,f,si,arm,arm+h,policy)
                        event.append({'symbol':sym,'panel':'CORE5' if sym in c.e.CORE else 'PEERS13','frame':frame,'policy':policy,'episode':int(t['episode']),'arm_date':str(d.index[arm].date()),'horizon':h}|x)
        print('HORIZON',sym,flush=True)
    ev=pd.DataFrame(event);ev.to_csv(O/'matched_horizon_events.csv',index=False);s=[]
    for keys,g in ev.groupby(['panel','frame','policy','horizon']):s.append(dict(zip(['panel','frame','policy','horizon'],keys))|c.summary(g))
    pd.DataFrame(s).to_csv(O/'matched_horizon_summary.csv',index=False);ac=pd.DataFrame(accounts);ac.to_csv(O/'account_horizon252.csv',index=False)
    print('CORE_DAILY_HORIZON252',ac[(ac.panel=='CORE5')&(ac.frame=='1D')][['symbol','policy','cagr','max_drawdown','exposure','entries','busy_signals']].round(5).to_json(orient='records'),flush=True)
    print('CORE_MATCHED_EVENT',pd.DataFrame(s).query("panel=='CORE5' and frame=='1D'")[['policy','horizon','n','mean','mean_mae','worst_mae','mean_sessions']].round(6).to_json(orient='records'),flush=True)

if __name__=='__main__':run()
