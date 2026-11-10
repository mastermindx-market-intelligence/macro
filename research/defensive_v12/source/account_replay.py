"""Single-position V12 policy accounts using the frozen original first signals.
No resurrected busy signals, portfolio allocation, leverage or live orders.
Cash earns zero. Open sample-end positions remain marked, not sold.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import cycle_failure as c
R=Path(__file__).resolve().parent;O=R/'results'

def account(d,f,watches,policy,horizon=126,start_i=0,fee=.0005):
    ids=d.index;value=np.ones(len(d));low_value=np.ones(len(d));exposed=np.zeros(len(d),bool)
    capital=1.;last_exit=start_i-1;trades=[];busy=0;pending=0;untriggered=0
    for watch in watches:
        raw=watch.get('signal_i')
        if raw is None or not np.isfinite(raw):untriggered+=1;continue
        signal=int(raw);arm=int(watch['arm_i']);j=signal+1
        if arm<start_i:continue
        if signal<last_exit or (trades and trades[-1]['status']=='OPEN'):busy+=1;continue
        r=c.simulate(d,f,signal,arm,arm+horizon,policy,fee=fee,marked=True,allow_open_end=True)
        if r['status']=='PENDING_ENTRY':pending+=1;continue
        if r['status']=='INCOMPLETE':raise AssertionError('Account must handle incomplete endpoint')
        before=capital;marks=r.pop('marks')
        for i,mark,low,in_position in marks:
            value[i]=before*mark;low_value[i]=before*low;exposed[i]=in_position
        capital=before*(1+r['net']);last_exit=r['exit_i']
        value[last_exit+1:]=capital;low_value[last_exit+1:]=capital
        r.update(episode=int(watch['episode']),signal_date=str(ids[signal].date()),arm_date=str(ids[arm].date()),capital_before=before,capital_after=capital)
        trades.append(r)
    q=pd.DataFrame({'value':value,'low_mark':low_value,'exposed':exposed},index=ids).iloc[start_i:]
    peak=np.maximum.accumulate(q.value.to_numpy());dd=q.value.to_numpy()/peak-1
    # The conservative day-low comparison uses only the prior close peak, not an
    # unknowable intraday high-before-low path.
    priorpeak=np.r_[1.,peak[:-1]];low_dd=q.low_mark.to_numpy()/priorpeak-1
    years=max((ids[-1]-ids[start_i]).days/365.25,1/365.25);ret=q.value.pct_change().fillna(0)
    closed=[t for t in trades if t['status']=='FILLED']
    s={'ending_equity':capital,'cagr':capital**(1/years)-1,'max_drawdown':float(min(0,dd.min())),'conservative_low_drawdown':float(min(0,low_dd.min())),'volatility':float(ret.std(ddof=1)*np.sqrt(252)),'exposure':float(q.exposed.mean()),'entries':len(trades),'closed':len(closed),'closed_win':float(np.mean([t['net']>0 for t in closed])) if closed else None,'busy_signals':busy,'pending_entries':pending,'untriggered_watches':untriggered,'open_positions':sum(t['status']=='OPEN' for t in trades)}
    q['drawdown']=dd
    return {'summary':s,'trades':trades,'equity':q}

def run():
    sums=[];ledger=[];equity={};eras=[]
    for sym in c.e.STOCKS:
        cache=pd.read_pickle(c.V11/'results'/f'{sym}_cache.pkl');d=cache['daily'];start=int(d.index.searchsorted('2018-01-01'))
        w=pd.read_csv(c.V11/'results'/f'{sym}_watches.csv')
        w=w[(w['mode']=='confirmed')&(w.two_week_phase==0)&(w.lower_phase==0)&(w.warmup==200)]
        for frame in ['1D','2D']:
            f=c.features(cache,frame);watches=w[w.frame==frame].sort_values('arm_i').to_dict('records')
            for policy in c.POLICIES:
                for bps in ([10,30] if sym in c.e.CORE else [10]):
                    x=account(d,f,watches,policy,start_i=start,fee=bps/20000)
                    tag={'symbol':sym,'panel':'CORE5' if sym in c.e.CORE else 'PEERS13','frame':frame,'policy':policy,'cost_bps':bps}
                    sums.append(tag|x['summary']);ledger.extend([tag|t for t in x['trades']]);q=x['equity']
                    if bps==10:
                        equity['|'.join([sym,frame,policy])]=q
                        for label,a,b in [('2018_2022','2018-01-01','2022-12-31'),('2023_2026','2023-01-01','2026-10-08')]:
                            sub=q.loc[a:b];first=q.index.get_indexer([sub.index[0]])[0];initial=1. if first==0 else q.value.iloc[first-1];yrs=(sub.index[-1]-sub.index[0]).days/365.25
                            z=sub.value/initial;pk=np.maximum.accumulate(np.r_[1.,z.to_numpy()])[1:]
                            eras.append(tag|{'period':label,'return':float(z.iloc[-1]-1),'cagr':float(z.iloc[-1]**(1/yrs)-1),'max_drawdown':float((z.to_numpy()/pk-1).min()),'exposure':float(sub.exposed.mean())})
        print('ACCOUNT',sym,flush=True)
    pd.DataFrame(sums).to_csv(O/'account_summary.csv',index=False);pd.DataFrame(ledger).to_csv(O/'account_trades.csv',index=False);pd.DataFrame(eras).to_csv(O/'account_era.csv',index=False);pd.to_pickle(equity,O/'account_equities.pkl')
    s=pd.DataFrame(sums);print('CORE_DAILY',s[(s.panel=='CORE5')&(s.frame=='1D')&(s.cost_bps==10)][['symbol','policy','cagr','max_drawdown','volatility','exposure','entries','closed','closed_win','busy_signals','open_positions']].round(5).to_json(orient='records'),flush=True)
    print('ACCOUNTS',len(s),'trade records',len(ledger),flush=True)

if __name__=='__main__':run()
