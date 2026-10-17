"""V12 fixed-entry, state-aware exits. Research only; no network or broker.
Known setup levels are immutable. Close signals fill at the next daily open.
Completed native lower/weekly inputs are read from the verified V11 cache.
"""
from pathlib import Path
import json,sys,hashlib
import numpy as np
import pandas as pd
V11=Path('/tmp/mmx_defensive_empirical_v11_20261011')
sys.path.insert(0,str(V11))
import empirical as e
R=Path(__file__).resolve().parent;O=R/'results'
POLICIES=['HOLD','ATR3','ATR6','STRUCTURE_ATR6','STRUCTURE_MOMENTUM_ATR6','STAGED_ATR6']

def setup_floor(d,arm_i,signal_i,atr):
    if not 0<=arm_i<=signal_i<len(d) or not np.isfinite(atr) or atr<=0:raise ValueError('Known arm/signal/ATR required')
    return float(d.low.iloc[max(0,arm_i-20):signal_i+1].min()-.5*atr)

def features(cache,frame):
    d=cache['daily'];lo=cache['lower'][frame+'_0'];w=cache['slow']['confirmed_W']
    tr=pd.concat([d.high-d.low,(d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()],axis=1).max(axis=1)
    bear=w.fresh&(w.k<w.d)&(w.k.shift()>=w.d.shift())
    return pd.DataFrame({'atr':e.original.rma(tr,14),'lower_hist':lo['hist'],'weekly_fresh':w.fresh,'weekly_k':w.k,'weekly_stoch_bear':bear},index=d.index)

def simulate(d,f,signal_i,arm_i,endpoint_i,policy,fee=.0005,marked=False):
    if policy not in POLICIES:raise ValueError('Unknown policy')
    if not d.index.equals(f.index):raise ValueError('Feature/date mismatch')
    if endpoint_i>=len(d):return {'status':'INCOMPLETE'}
    if not 0<=arm_i<=signal_i<endpoint_i:raise ValueError('Invalid causal indices')
    atr=float(f.atr.iloc[signal_i]);floor=setup_floor(d,arm_i,signal_i,atr)
    j=signal_i+1;entry=float(d.open.iloc[j]);shares=1/(entry*(1+fee))
    stop=0. if policy=='HOLD' else max(0.,entry-(3 if policy=='ATR3' else 6)*atr)
    pending=None;extended=False;minimum=entry;maximum=entry;marks=[];reason='ENDPOINT';exit_i=endpoint_i;price=float(d.close.iloc[endpoint_i]);decision=None
    bars=d[['open','high','low','close']].to_numpy(float)
    hist=f.lower_hist.to_numpy(float);fresh=f.weekly_fresh.to_numpy(bool);wk=f.weekly_k.to_numpy(float);wb=f.weekly_stoch_bear.to_numpy(bool)
    for i in range(j,endpoint_i+1):
        op,hi,low,cl=bars[i];out=False
        if op<=stop:price=op;reason='STOP_GAP';out=True
        elif pending is not None:price=op;reason=pending;out=True
        if out:
            minimum=min(minimum,op);maximum=max(maximum,op)
            marks.append((i,shares*price*(1-fee),shares*op,False));exit_i=i;break
        if low<=stop:
            price=stop;reason='STOP_INTRADAY';minimum=min(minimum,price);maximum=max(maximum,op)
            marks.append((i,shares*price*(1-fee),shares*price,False));exit_i=i;break
        minimum=min(minimum,low);maximum=max(maximum,hi)
        if fresh[i] and np.isfinite(wk[i]) and wk[i]>=80:extended=True
        trigger=None
        if policy=='STRUCTURE_ATR6' and cl<floor:trigger='STRUCTURE_LOSS'
        if policy in ['STRUCTURE_MOMENTUM_ATR6','STAGED_ATR6'] and cl<floor and np.isfinite(hist[i]) and hist[i]<0:trigger='STRUCTURE_MOMENTUM_LOSS'
        if trigger is None and policy=='STAGED_ATR6' and extended and fresh[i] and wb[i]:trigger='WEEKLY_CYCLE'
        if i==endpoint_i:
            price=cl;reason='ENDPOINT';marks.append((i,shares*price*(1-fee),shares*low,False))
        else:
            marks.append((i,shares*cl,shares*low,True))
            if trigger is not None:pending=trigger;decision=i
    net=shares*price*(1-fee)-1
    row={'status':'FILLED','policy':policy,'entry_i':j,'exit_i':exit_i,'decision_i':decision,'entry_date':str(d.index[j].date()),'exit_date':str(d.index[exit_i].date()),'endpoint_date':str(d.index[endpoint_i].date()),'entry_price':entry,'exit_price':price,'net':net,'reason':reason,'held_sessions':exit_i-j+1,'mae':minimum/entry-1,'mfe':maximum/entry-1,'signal_atr_pct':atr/entry,'structure_floor':floor,'structure_distance':1-floor/entry,'hard_stop_distance':None if stop==0 else 1-stop/entry,'baseline':float(d.close.iloc[endpoint_i]/entry*(1-fee)/(1+fee)-1),'weekly_extended_in_trade':extended}
    row['incremental']=net-row['baseline']
    if marked:row['marks']=marks
    return row

def summary(g):
    return {'n':len(g),'positive':int((g.net>0).sum()),'win':float((g.net>0).mean()),'mean':float(g.net.mean()),'median':float(g.net.median()),'mean_mae':float(g.mae.mean()),'worst_mae':float(g.mae.min()),'mean_mfe':float(g.mfe.mean()),'mean_sessions':float(g.held_sessions.mean()),'incremental_vs_hold':float(g.incremental.mean()),'stop_exits':int(g.reason.str.startswith('STOP').sum()),'structural_exits':int(g.reason.str.startswith('STRUCTURE').sum()),'cycle_exits':int(g.reason.eq('WEEKLY_CYCLE').sum()),'p10':float(g.net.quantile(.1))}

def run():
    source=pd.read_csv(V11/'results'/'primary_labeled_events.csv')
    source=source[(source['mode']=='confirmed')&source.frame.isin(['1D','2D'])&(source.horizon==126)]
    rows=[];reconcile=[]
    for sym in e.STOCKS:
        cache=pd.read_pickle(V11/'results'/f'{sym}_cache.pkl');d=cache['daily'];ix=d.index
        for frame in ['1D','2D']:
            f=features(cache,frame)
            g=source[(source.symbol==sym)&(source.frame==frame)&(source.status=='FILLED')]
            for t in g.itertuples():
                signal=int(ix.get_loc(pd.Timestamp(t.signal_date)));arm=int(ix.get_loc(pd.Timestamp(t.arm_date)));z=int(ix.get_loc(pd.Timestamp(t.exit_date)))
                for p in POLICIES:
                    x=simulate(d,f,signal,arm,z,p)
                    x.update(symbol=sym,panel='CORE5' if sym in e.CORE else 'PEERS13',frame=frame,episode=int(t.episode),arm_date=t.arm_date,signal_date=t.signal_date,regime_signal=t.regime_signal,rates_signal=t.rates_signal,period='2018_2022' if pd.Timestamp(t.signal_date).year<=2022 else '2023_2026')
                    rows.append(x)
                    if p=='HOLD':reconcile.append(abs(x['net']-float(t.net)))
        print('V12',sym,flush=True)
    result=pd.DataFrame(rows);result.to_csv(O/'event_policies.csv',index=False)
    out=[];stock=[];era=[]
    for keys,g in result.groupby(['panel','frame','policy']):out.append(dict(zip(['panel','frame','policy'],keys))|summary(g))
    for keys,g in result.groupby(['symbol','frame','policy']):stock.append(dict(zip(['symbol','frame','policy'],keys))|summary(g))
    for keys,g in result.groupby(['panel','frame','period','policy']):era.append(dict(zip(['panel','frame','period','policy'],keys))|summary(g))
    pd.DataFrame(out).to_csv(O/'event_summary.csv',index=False);pd.DataFrame(stock).to_csv(O/'by_stock.csv',index=False);pd.DataFrame(era).to_csv(O/'era_summary.csv',index=False)
    source[source.status!='FILLED'].to_csv(O/'retained_unfilled_watches.csv',index=False)
    qa={'hold_v11_comparisons':len(reconcile),'max_hold_v11_error':max(reconcile),'original_watches_including_unknown':len(source),'filled_base_events':len(result)//len(POLICIES),'scenario_rows':len(result),'no_entry_selection':True,'input_source_unchanged':all(hashlib.sha256((V11/n).read_bytes()).hexdigest()==v for n,v in json.loads((R/'spec.json').read_text())['v11_hashes'].items())}
    assert qa['max_hold_v11_error']<1e-12 and qa['input_source_unchanged']
    (O/'verification.json').write_text(json.dumps(qa,indent=2))
    print('CORE1D',pd.DataFrame(out).query("panel=='CORE5' and frame=='1D'").round(6).to_json(orient='records'),flush=True)
    print('PEERS1D',pd.DataFrame(out).query("panel=='PEERS13' and frame=='1D'").round(6).to_json(orient='records'),flush=True)
    print('VERIFIED',json.dumps(qa),flush=True)

if __name__=='__main__':run()
