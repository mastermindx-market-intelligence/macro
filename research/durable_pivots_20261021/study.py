#!/usr/bin/env python3
"""Completed-bar, signal-first durable pivot research. See PROTOCOL.md.

Research only. Selection reads development/validation summaries; test tables are
written only after the selected configuration identities have been frozen.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

SIDES=('bottom','top')
MACD_MODES=('deep','deep_rising','deep_falling','cross','deep_then_cross','deep_or_cross')
LF_MODES=('hist_rising','hist_sign','macd_cross','stoch_rising','both_rising')
AUX=('price_ema10','daily_rsi','weekly_rsi','adx_easing','volume_reversal','sma200')
CUTOFF=pd.Timestamp('2026-10-08')
SPLITS={'development':('1995-01-01','2013-12-31'),
        'validation':('2014-01-01','2019-12-31'),
        'test':('2020-01-01','2026-10-08')}

def dump(path, obj):
    path.write_text(json.dumps(obj,indent=2,default=str,allow_nan=False))

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def rma(values, n=14):
    a=np.asarray(values,dtype=float);out=np.full(len(a),np.nan)
    start=None;run=0
    for i,v in enumerate(a):
        if not np.isfinite(v): run=0;start=None;continue
        run+=1
        if run==n:
            out[i]=a[i-n+1:i+1].mean();start=i
        elif start is not None: out[i]=(out[i-1]*(n-1)+v)/n
    return pd.Series(out,index=values.index)

def basic_indicators(d, quantile_window=None):
    c,h,l=d.close,d.high,d.low
    change=c.diff();gain=change.clip(lower=0);loss=(-change).clip(lower=0)
    ag,al=rma(gain),rma(loss)
    rsi=100-100/(1+ag/al)
    rsi=rsi.mask((ag==0)&(al==0),50).mask((ag>0)&(al==0),100)
    rmin=rsi.rolling(14).min();span=rsi.rolling(14).max()-rmin
    raw=100*(rsi-rmin)/span.replace(0,np.nan)
    k=raw.rolling(3).mean();dd=k.rolling(3).mean()
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=rma(tr)
    m=c.ewm(span=12,adjust=False,min_periods=12).mean()-c.ewm(span=26,adjust=False,min_periods=26).mean()
    signal=m.ewm(span=9,adjust=False,min_periods=9).mean();hist=m-signal
    up=h.diff();down=-l.diff()
    plus=up.where((up>down)&(up>0),0.0);minus=down.where((down>up)&(down>0),0.0)
    pdi=100*rma(plus)/atr;mdi=100*rma(minus)/atr
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan);adx=rma(dx)
    z=pd.DataFrame({'k':k,'d':dd,'rsi':rsi,'drsi':rsi.diff(),'atr':atr,
                    'hist':hist,'dh':hist.diff(),'dk':k.diff(),'macd':m,'adx':adx,
                    'dadx':adx.diff(),'ema10':c.ewm(span=10,adjust=False,min_periods=10).mean(),
                    'sma200':c.rolling(200).mean(),'volume_ratio':d.volume/d.volume.rolling(20).mean()},index=d.index)
    z['sma200_slope']=z.sma200.diff(20)
    z['hnorm']=hist/atr.replace(0,np.nan)
    if quantile_window:
        q=z.hnorm.rolling(quantile_window,min_periods=quantile_window)
        z['q20']=q.quantile(.2).shift(1);z['q80']=q.quantile(.8).shift(1)
        z['valid']=z[['k','d','q20','q80','atr']].notna().all(axis=1)
    else:
        z['q20']=np.nan;z['q80']=np.nan;z['valid']=z[['k','d','atr']].notna().all(axis=1)
    for side,sign in [('bottom',1),('top',-1)]:
        wash=(k.rolling(3).min()<=20) if sign==1 else (k.rolling(3).max()>=80)
        cap=(k<60) if sign==1 else (k>40)
        kd=(sign*(k-dd)>0)&(sign*(k.shift()-dd.shift())<=0)
        z[f'{side}_curl']=wash&cap&(sign*k.diff()>0)
        z[f'{side}_kcross']=wash&cap&(sign*(k-dd)>0)&kd.rolling(2).max().fillna(0).astype(bool)
        cross=(sign*hist>0)&(sign*hist.shift()<=0)
        fresh=cross.rolling(2).max().fillna(0).astype(bool)&(sign*hist>0)
        deep=(hist<0)&(z.hnorm<=z.q20) if sign==1 else (hist>0)&(z.hnorm>=z.q80)
        z[f'{side}_deep']=deep
        z[f'{side}_deep_rising']=deep&(sign*hist.diff()>0)
        z[f'{side}_deep_falling']=deep&(sign*hist.diff()<0)
        z[f'{side}_cross']=fresh
        z[f'{side}_deep_then_cross']=fresh&deep.shift(1).rolling(6).max().fillna(0).astype(bool)
        z[f'{side}_deep_or_cross']=deep|fresh
        z[f'{side}_hist_rising']=sign*hist.diff()>0
        z[f'{side}_hist_sign']=sign*hist>0
        z[f'{side}_macd_cross']=fresh
        z[f'{side}_stoch_rising']=sign*k.diff()>0
        z[f'{side}_both_rising']=(sign*hist.diff()>0)&(sign*k.diff()>0)
        z[f'{side}_opposing_cross']=((sign*hist<0)&(sign*hist.shift()>=0)).rolling(2).max().fillna(0).astype(bool)&(sign*hist<0)
    return z

def group_keys(idx, tf, calendar, phases=(0,0,0), crypto=False):
    phase2,phase3,phasew=phases
    if tf in ('2D','3D'):
        n=int(tf[0]);phase=phase2 if n==2 else phase3
        ordinal=calendar.get_indexer(idx)
        if (ordinal<0).any(): raise ValueError('input date outside fixed reference calendar')
        return (ordinal-phase)//n
    anchor=pd.Timestamp('2000-01-02' if crypto else '2000-01-07')
    freq='W-SUN' if crypto else 'W-FRI'
    ending=idx.to_period(freq).end_time.normalize()
    wk=np.asarray((ending-anchor).days//7)
    return wk if tf=='1W' else (wk-phasew)//2

def aggregate_bars(d,tf,calendar,phases=(0,0,0),crypto=False):
    if tf=='1D': return d.copy()
    key=group_keys(d.index,tf,calendar,phases,crypto)
    ck=group_keys(calendar,tf,calendar,phases,crypto)
    expected=pd.DataFrame({'date':calendar,'key':ck}).groupby('key').date.agg(['count','max'])
    x=d.assign(_key=key,_date=d.index)
    bars=x.groupby('_key').agg(open=('open','first'),high=('high','max'),low=('low','min'),
                             close=('close','last'),volume=('volume','sum'),count=('close','count'),end=('_date','max'))
    ex=expected.reindex(bars.index)
    keep=(bars['count']==ex['count'])&(bars.end==ex['max'])
    if tf in ('2D','3D'): keep &= bars['count']==int(tf[0])
    else:
        anchor=pd.Timestamp('2000-01-02' if crypto else '2000-01-07')
        end_week=bars.index.to_numpy() if tf=='1W' else bars.index.to_numpy()*2+phases[2]+1
        nominal=anchor+pd.to_timedelta(end_week*7,unit='D')
        keep &= nominal<=calendar.max()
    bars=bars.loc[keep]
    bars.index=pd.DatetimeIndex(bars.pop('end'));bars.index.name='date'
    return bars.drop(columns='count')

def features(d,calendar,phases=(0,0,0),crypto=False):
    out={}
    for tf in ('1D','2D','3D','1W','2W'):
        bars=aggregate_bars(d,tf,calendar,phases,crypto)
        z=basic_indicators(bars,156 if tf=='1W' else 78 if tf=='2W' else None)
        # Only already completed bars are projected to the decision date.
        out[tf]=z.reindex(d.index,method='ffill')
        out[tf]['bar_date']=pd.Series(bars.index,index=bars.index).reindex(d.index,method='ffill')
    return out

def future_extreme(s,n,kind):
    r=s.shift(-1).iloc[::-1].rolling(n,min_periods=n)
    return (r.min() if kind=='min' else r.max()).iloc[::-1]

def split_labels(dates, horizon_end):
    out=np.full(len(dates),'excluded',dtype=object)
    for name,(a,b) in SPLITS.items():
        mask=(dates>=pd.Timestamp(a))&(dates<=pd.Timestamp(b))&(horizon_end<=pd.Timestamp(b))&~pd.isna(horizon_end)
        out[mask]=name
    return out

def labels(d,f,side,symbol,group):
    n=len(d);ix=np.arange(n);sign=1 if side=='bottom' else -1
    daily=f['1D'];atr=daily.atr.to_numpy();price=d.low.to_numpy() if sign==1 else d.high.to_numpy()
    opposite=d.high if sign==1 else d.low
    p=np.full(n,-1,dtype=int)
    if n>=63:
        windows=np.lib.stride_tricks.sliding_window_view(sign*price,63)
        rev=np.argmin(windows[:,::-1],axis=1)
        p[62:]=np.arange(62,n)-rev
    safe=np.maximum(p,0);pp=price[safe];ap=atr[safe]
    approach=opposite.shift(1).rolling(63).max() if sign==1 else opposite.shift(1).rolling(63).min()
    depth=sign*(approach.to_numpy()[safe]-pp)/ap
    distance=sign*(d.close.to_numpy()-pp)/ap
    valid=f['1W'].valid.fillna(False).astype(bool)&f['2W'].valid.fillna(False).astype(bool)
    valid &= np.isfinite(ap)&(ap>0)&(p>=63)
    z=pd.DataFrame({'date':d.index,'t':ix,'p':p,'candidate_date':d.index[safe],
                    'candidate_price':pp,'signal_close':d.close.to_numpy(),'atr_p':ap,
                    'age':ix-p,'distance':distance,'depth':depth,'valid':valid.to_numpy(),
                    'ticker':symbol,'asset_class':group,'side':side},index=d.index)
    z['qualified']=(z.age<=21)&(z.distance<=2)&(z.depth>=4)&z.valid
    z['own_regime']=np.where((d.close>daily.sma200)&(daily.sma200_slope>0),'up',
                            np.where((d.close<daily.sma200)&(daily.sma200_slope<0),'down','mixed'))
    for horizon in (21,63,126):
        ext=future_extreme(d.low if sign==1 else d.high,horizon,'min' if sign==1 else 'max')
        fav=future_extreme(d.high if sign==1 else d.low,horizon,'max' if sign==1 else 'min')
        end=pd.Series(d.index,index=d.index).shift(-horizon)
        breach=sign*(pp-ext.to_numpy())/ap
        z[f'breach{horizon}']=breach.clip(min=0)
        z[f'survive{horizon}']=np.where(ext.notna(),breach<=.25,np.nan)
        z[f'strict{horizon}']=np.where(ext.notna(),breach<=0,np.nan)
        z[f'mfe{horizon}']=sign*(fav.to_numpy()-d.close.to_numpy())/ap
        z[f'return{horizon}']=sign*(d.close.shift(-horizon).to_numpy()/d.close.to_numpy()-1)
        z[f'primary{horizon}']=z.qualified.astype(float)*z[f'survive{horizon}']
        z[f'split{horizon}']=split_labels(d.index,pd.DatetimeIndex(end))
    for tf,ff in f.items():
        for mode in (*LF_MODES,'opposing_cross'):
            z[f'lf_{tf}_{mode}']=ff[f'{side}_{mode}'].fillna(False).astype(bool).to_numpy()
    z['aux_price_ema10']=sign*(d.close-daily.ema10)>0
    z['aux_daily_rsi']=(sign*daily.drsi>0)&((daily.rsi>30) if sign==1 else (daily.rsi<70))
    weekly=f['1W']
    z['aux_weekly_rsi']=(sign*weekly.drsi>0)&((weekly.rsi<50) if sign==1 else (weekly.rsi>50))
    z['aux_adx_easing']=daily.dadx<0
    z['aux_volume_reversal']=(daily.volume_ratio>=1.5)&(sign*d.close.diff()>0)
    z['aux_sma200']=sign*(d.close-daily.sma200)>0
    # Outcome-only reference pivot catalogue. Future fields never enter a signal.
    before=pd.Series(price,index=d.index).shift(1).rolling(63)
    past=before.min() if sign==1 else before.max()
    after=future_extreme(pd.Series(price,index=d.index),63,'min' if sign==1 else 'max')
    reject=future_extreme(opposite,63,'max' if sign==1 else 'min')
    ap0=atr
    approach0=sign*(approach.to_numpy()-price)/ap0
    rejection=sign*(reject.to_numpy()-price)/ap0
    piv=(sign*(price-past.to_numpy())<=0)&(sign*(price-after.to_numpy())<0)&(approach0>=4)&(rejection>=4)&valid.to_numpy()
    outcome_end=pd.Series(d.index,index=d.index).shift(-84)
    psplit=split_labels(d.index,pd.DatetimeIndex(outcome_end))
    piv &= psplit!='excluded'
    ids={int(t):f'{symbol}:{side}:{d.index[t].date()}' for t in np.flatnonzero(piv)}
    z['matched_pivot']=[ids.get(int(pp),'') if age<=21 and dist<=2 else '' for pp,age,dist in zip(p,z.age,z.distance)]
    z['halfyear']=[f'{v.year}H{1 if v.month<=6 else 2}' for v in d.index]
    z['quarter']=[str(v.to_period('Q')) for v in d.index]
    catalog=pd.DataFrame([{'pivot_id':ids[t],'ticker':symbol,'asset_class':group,'side':side,
                           'date':d.index[t],'t':t,'price':price[t],'atr':atr[t],
                           'depth':approach0[t],'rejection':rejection[t], 'split':psplit[t]} for t in ids])
    return z,catalog

def base_rules():
    result=[]
    for side in SIDES:
        for stf,mode in itertools.product(('1W','2W'),('curl','kcross')):
            result.append({'side':side,'stoch_tf':stf,'stoch_mode':mode,'macd_tf':'none','macd_mode':'none',
                           'base':f'{side}|S{stf}:{mode}|Mnone'})
            for mtf,mm in itertools.product(('1W','2W'),MACD_MODES):
                result.append({'side':side,'stoch_tf':stf,'stoch_mode':mode,'macd_tf':mtf,'macd_mode':mm,
                               'base':f'{side}|S{stf}:{mode}|M{mtf}:{mm}'})
        for name in ('price_turn','rsi_recovery','stoch_daily'):
            result.append({'side':side,'stoch_tf':'1D','stoch_mode':name,'macd_tf':'none','macd_mode':'none',
                           'base':f'{side}|BASE:{name}'})
    return result

def catalog_rules(bases):
    out=[]
    for b in bases:
        out.append({**b,'filter':'none','rule_id':b['base']+'|none'})
        if 'BASE:' in b['base']:continue
        tfs=['1D','2D','3D']
        if b['stoch_tf']=='2W' and b['macd_tf'] in ('2W','none'): tfs+=['1W']
        for tf,mode in itertools.product(tfs,LF_MODES):
            out.append({**b,'filter':f'lf_{tf}_{mode}','rule_id':b['base']+f'|{tf}:{mode}'})
        for aux in AUX:
            out.append({**b,'filter':f'aux_{aux}','rule_id':b['base']+f'|aux:{aux}'})
    return out

def event_indices(state,valid,cooldown=21):
    a=np.asarray(state,dtype=bool);v=np.asarray(valid,dtype=bool)
    rising=a&~np.r_[False,a[:-1]]&v
    take=[];last=-100000
    for t in np.flatnonzero(rising):
        if t-last>=cooldown:take.append(t);last=t
    return np.asarray(take,dtype=int)

def base_state(b,f,d,z):
    s=b['side'];sign=1 if s=='bottom' else -1
    if 'BASE:' in b['base']:
        mode=b['stoch_mode'];daily=f['1D']
        if mode=='price_turn':return (z.age<=5)&(sign*d.close.diff()>0)
        if mode=='rsi_recovery':
            return (daily.rsi>30)&(daily.rsi.shift()<=30) if sign==1 else (daily.rsi<70)&(daily.rsi.shift()>=70)
        return daily[f'{s}_curl'].fillna(False)
    state=f[b['stoch_tf']][f'{s}_{b["stoch_mode"]}'].fillna(False).astype(bool)
    if b['macd_tf']!='none':state &= f[b['macd_tf']][f'{s}_{b["macd_mode"]}'].fillna(False).astype(bool)
    return state

def load_inputs(manifest_path,basis='price'):
    meta=json.loads(manifest_path.read_text());data={};items={}
    for item in meta['assets']:
        if item['status']!='OK':continue
        p=Path(item['path'])
        if not p.exists():p=manifest_path.parent/'prices'/p.name
        if digest(p)!=item['parquet_sha256']:raise ValueError('price hash mismatch '+item['ticker'])
        d=pd.read_parquet(p).sort_index().loc[:CUTOFF]
        if basis=='total_return':
            factor=d.adjclose/d.close
            if not np.isfinite(factor).all() or (factor<=0).any():raise ValueError('invalid adjustment factor')
            for col in ('open','high','low','close'):d[col]=d[col]*factor
        data[item['ticker']]=d;items[item['ticker']]=item
    if 'SPY' not in data:raise ValueError('SPY reference calendar unavailable')
    spy=data['SPY'].index
    early=pd.DatetimeIndex([])
    for s,d in data.items():
        if items[s]['asset_class']!='crypto':early=early.union(d.index[d.index<spy.min()])
    equity_calendar=early.union(spy).sort_values()
    crypto_calendar=pd.date_range('1980-01-01',CUTOFF,freq='D')
    return meta,data,items,equity_calendar,crypto_calendar

def build_events(manifest_path,bases,phases=(0,0,0),basis='price',quiet=False):
    meta,data,items,eqcal,ccal=load_inputs(manifest_path,basis)
    rows=[];pivots=[];coverage=[];daily_cache={}
    spy=basic_indicators(data['SPY']);mc=data['SPY'].close
    mr=pd.Series(np.where((mc>spy.sma200)&(spy.sma200_slope>0),'up',
                         np.where((mc<spy.sma200)&(spy.sma200_slope<0),'down','mixed')),index=spy.index)
    for ticker,d in data.items():
        group=items[ticker]['asset_class'];crypto=group=='crypto'
        f=features(d,ccal if crypto else eqcal,phases,crypto)
        daily_cache[ticker]=(d,f)
        for side in SIDES:
            z,ps=labels(d,f,side,ticker,group)
            z['market_regime']=mr.reindex(d.index,method='ffill').fillna('unknown')
            if len(ps):pivots.append(ps)
            valid_dates=z.index[z.valid]
            coverage.append({'ticker':ticker,'asset_class':group,'side':side,'first_valid':str(valid_dates.min()),
                             'last':str(d.index.max()),'valid_bars':int(z.valid.sum()),'source_rows':len(d)})
            for b in bases:
                if b['side']!=side:continue
                state=base_state(b,f,d,z)
                at=event_indices(state,z.valid)
                if len(at):
                    ev=z.iloc[at].copy();ev['base']=b['base'];rows.append(ev.reset_index(drop=True))
        if not quiet:print('FEATURES',ticker,len(d),flush=True)
    events=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()
    piv=pd.concat(pivots,ignore_index=True) if pivots else pd.DataFrame()
    return events,piv,pd.DataFrame(coverage),daily_cache

def select_events(events,rule,split='test',pool='primary'):
    q=events[(events.base==rule['base'])&(events.split63==split)]
    q=q[q.asset_class.eq('crypto') if pool=='crypto' else ~q.asset_class.eq('crypto')]
    if rule['filter']!='none':q=q[q[rule['filter']].fillna(False).astype(bool)]
    return q

def summarize(q,piv,side,split,pool='primary'):
    ps=piv[(piv.side==side)&(piv['split']==split)]
    ps=ps[ps.asset_class.eq('crypto') if pool=='crypto' else ~ps.asset_class.eq('crypto')]
    available=set(ps.pivot_id)
    matched=set(q.matched_pivot[q.matched_pivot!=''])&available if len(q) else set()
    n=len(q);qualified=int(q.qualified.sum()) if n else 0
    wins=float(q.primary63.sum()) if n else 0
    precision=wins/n if n else np.nan;recall=len(matched)/len(ps) if len(ps) else np.nan
    balance=2*precision*recall/(precision+recall) if n and precision+recall>0 else 0.0
    return {'n':n,'assets':q.ticker.nunique() if n else 0,'groups':q.asset_class.nunique() if n else 0,
            'quarters':q.quarter.nunique() if n else 0,'halfyears':q.halfyear.nunique() if n else 0,
            'qualified_n':qualified,'timely_durable_n':int(wins),'timely_durable_rate':precision,
            'qualified_survival63':float(q.loc[q.qualified,'survive63'].mean()) if qualified else np.nan,
            'survival63':float(q.survive63.mean()) if n else np.nan,
            'strict_survival63':float(q.strict63.mean()) if n else np.nan,
            'median_age':float(q.age.median()) if n else np.nan,
            'median_distance_atr':float(q.distance.median()) if n else np.nan,
            'median_depth_atr':float(q.depth.median()) if n else np.nan,
            'median_breach63_atr':float(q.breach63.median()) if n else np.nan,
            'p90_breach63_atr':float(q.breach63.quantile(.9)) if n else np.nan,
            'median_mfe63_atr':float(q.mfe63.median()) if n else np.nan,
            'median_directional_return63':float(q.return63.median()) if n else np.nan,
            'reference_pivots':len(ps),'detected_pivots':len(matched),'recall':recall,'balance_score':balance}

def summarize_catalog(events,piv,rules,splits=('development','validation'),pool='primary'):
    out=[]
    grouped={k:v for k,v in events.groupby('base',sort=False)}
    for rule in rules:
        base=grouped.get(rule['base'],events.iloc[:0])
        for split in splits:
            q=select_events(base,rule,split,pool)
            out.append({**rule,'split':split,'pool':pool,**summarize(q,piv,rule['side'],split,pool)})
    return pd.DataFrame(out)

def choose_finalists(val,rules):
    chosen={};byid={r['rule_id']:r for r in rules}
    def keep(rid,why):
        if rid in byid:chosen.setdefault(rid,{'rule':byid[rid],'selection_reasons':[]})['selection_reasons'].append(why)
    for side in SIDES:
        q=val[(val.side==side)&(val['split']=='validation')&(val.n>=100)&(val.assets>=12)].copy()
        q=q.sort_values(['balance_score','timely_durable_rate','n','rule_id'],ascending=[False,False,False,True])
        subsets={'overall':q,'high_only':q[q['filter']=='none'],
                 'early':q[q.macd_mode.isin(['deep','deep_rising','deep_falling'])],
                 'cross':q[q.macd_mode.isin(['cross','deep_then_cross'])],
                 'auxiliary':q[q['filter'].str.startswith('aux_')]}
        for kind,v in subsets.items():
            if len(v):keep(v.iloc[0].rule_id,'validation_'+kind)
        for stf,mtf in itertools.product(('1W','2W'),repeat=2):
            for mode in ('deep_rising','cross'):
                keep(f'{side}|S{stf}:curl|M{mtf}:{mode}|none','fixed_timeframe_hypothesis')
        for tf,lower in [('1W','1D'),('2W','3D')]:
            keep(f'{side}|S{tf}:curl|M{tf}:deep_rising|{lower}:both_rising','fixed_user_pair')
            keep(f'{side}|S{tf}:curl|Mnone|none','stoch_only_baseline')
        for name in ('price_turn','rsi_recovery','stoch_daily'):keep(f'{side}|BASE:{name}|none','simple_baseline')
    return list(chosen.values())

def interval(q,field='primary63',cluster='halfyear',draws=2000,seed=7301):
    if not len(q):return [np.nan,np.nan]
    if cluster=='year':q=q.assign(year=q.date.dt.year)
    g=q.groupby(cluster)[field].agg(['sum','count'])
    if len(g)<2:return [np.nan,np.nan]
    rng=np.random.default_rng(seed);ix=rng.integers(0,len(g),size=(draws,len(g)))
    num=g['sum'].to_numpy()[ix].sum(axis=1);den=g['count'].to_numpy()[ix].sum(axis=1)
    return list(np.nanquantile(num/den,[.025,.975]))

def delta_interval(q,base,field='primary63',draws=2000,seed=7302):
    ix=sorted(set(q.halfyear)|set(base.halfyear))
    if len(ix)<2 or not len(q):return [np.nan,np.nan,np.nan]
    def cells(x):
        z=x.groupby('halfyear')[field].agg(['sum','count']).reindex(ix,fill_value=0)
        return z['sum'].to_numpy(),z['count'].to_numpy()
    a,an=cells(q);b,bn=cells(base);rng=np.random.default_rng(seed)
    draw=rng.integers(0,len(ix),size=(draws,len(ix)))
    with np.errstate(divide='ignore',invalid='ignore'):delta=a[draw].sum(axis=1)/an[draw].sum(axis=1)-b[draw].sum(axis=1)/bn[draw].sum(axis=1)
    lo,hi=np.nanquantile(delta,[.025,.975])
    return [float(q[field].mean()-base[field].mean()),float(lo),float(hi)]

def final_tables(events,piv,finalists,rules,out):
    selected=[v['rule'] for v in finalists];rows=[];groups=[];assets=[];regimes=[];sens=[];conflicts=[]
    grouped={k:v for k,v in events.groupby('base',sort=False)}
    for r in selected:
        base=grouped.get(r['base'],events.iloc[:0])
        for pool in ('primary','crypto'):
            q=select_events(base,r,'test',pool)
            s=summarize(q,piv,r['side'],'test',pool)
            ci=interval(q);aci=interval(q,cluster='ticker');yci=interval(q,cluster='year')
            raw=select_events(base,{**r,'filter':'none'},'test',pool)
            delta=delta_interval(q,raw)
            rows.append({**r,'pool':pool,**s,'ci_low':ci[0],'ci_high':ci[1],
                         'asset_ci_low':aci[0],'asset_ci_high':aci[1],
                         'year_ci_low':yci[0],'year_ci_high':yci[1],
                         'delta_vs_high_base':delta[0],'delta_ci_low':delta[1],'delta_ci_high':delta[2],
                         'broad_evidence_floor':s['n']>=60 and s['assets']>=12 and s['groups']>=3 and s['quarters']>=20,
                         'conditional_survival_n_at_least40':s['qualified_n']>=40})
            if pool=='crypto':continue
            for field,target in [('asset_class',groups),('ticker',assets),('market_regime',regimes),('own_regime',regimes)]:
                universe=piv[~piv.asset_class.eq('crypto')]
                keys=sorted(universe[field].unique()) if field in ('asset_class','ticker') else ['up','down','mixed']
                for key in keys:
                    part=q[q[field]==key]
                    # Keep all eligible members, including assets with zero signals.
                    pp=universe[universe[field]==key] if field in ('asset_class','ticker') else universe
                    stats=summarize(part,pp,r['side'],'test')
                    if field in ('market_regime','own_regime'):
                        # Pivot regime is not the signal-date regime: no false conditional recall.
                        for name in ('recall','balance_score','reference_pivots','detected_pivots'):stats[name]=np.nan
                    target.append({'rule_id':r['rule_id'],'side':r['side'],'dimension':field,'value':key,**stats})
            for age in (10,21,42):
                for dist in (1.,2.,3.):
                    qual=(q.age<=age)&(q.distance<=dist)&(q.depth>=4)
                    sens.append({'rule_id':r['rule_id'],'side':r['side'],'sensitivity':'age_distance','age_max':age,'distance_max':dist,
                                 'n':len(q),'qualified_n':int(qual.sum()),'rate':float((qual*q.survive63).mean()) if len(q) else np.nan})
            for horizon in (21,63,126):
                qq=base[(base[f'split{horizon}']=='test')&~base.asset_class.eq('crypto')]
                if r['filter']!='none':qq=qq[qq[r['filter']].fillna(False).astype(bool)]
                sens.append({'rule_id':r['rule_id'],'side':r['side'],'sensitivity':'horizon','horizon':horizon,'n':len(qq),
                             'rate':float(qq[f'primary{horizon}'].mean()) if len(qq) else np.nan,
                             'survival':float(qq[f'survive{horizon}'].mean()) if len(qq) else np.nan})
            for depth in (3.,5.):
                qual=(q.age<=21)&(q.distance<=2)&(q.depth>=depth)
                sens.append({'rule_id':r['rule_id'],'side':r['side'],'sensitivity':'depth','depth_min':depth,'n':len(q),
                             'rate':float((qual*q.survive63).mean()) if len(q) else np.nan})
            for name,qq in [('exclude2020',q[q.date.dt.year!=2020]),('exclude_semiconductors',q[~q.ticker.isin(['NVDA','AMD','INTC','MU','SOXX'])])]:
                sens.append({'rule_id':r['rule_id'],'side':r['side'],'sensitivity':name,'n':len(qq),
                             'rate':float(qq.primary63.mean()) if len(qq) else np.nan})
        # Conflict test is on the unfiltered, same-time high base events.
        if r['filter']=='none' and 'BASE:' not in r['base']:
            q=select_events(base,r,'test')
            for tf in ('1D','2D','3D'):
                for mode in ('hist_rising','hist_sign','macd_cross','stoch_rising','both_rising','opposing_cross'):
                    flag=f'lf_{tf}_{mode}'
                    for state in (True,False):
                        part=q[q[flag]==state]
                        conflicts.append({'rule_id':r['rule_id'],'side':r['side'],'lower_tf':tf,'condition':mode,'state':state,
                                          **summarize(part,piv,r['side'],'test')})
    for filename,records in [('final_results.csv',rows),('by_asset_group.csv',groups),('by_asset.csv',assets),
                              ('by_regime.csv',regimes),('outcome_sensitivity.csv',sens),('timeframe_conflicts.csv',conflicts)]:
        pd.DataFrame(records).to_csv(out/filename,index=False)
    return pd.DataFrame(rows)

def log_catalog(rules,out):
    # Reuse the repository's canonical TrialLedger class, confined to this study.
    repo=Path(__file__).resolve().parents[2]
    if (repo/'engine/trial_ledger.py').exists():
        sys.path.insert(0,str(repo))
        from engine.trial_ledger import TrialLedger
        ledger=TrialLedger(path=out/'trial_ledger.jsonl',family='durable_pivot_confluence_20261021')
        ledger.log_grid(rules,info_cutoff=str(CUTOFF.date()),note='Pre-evaluation full catalog; research local, no production ledger')
        return {'owner':'engine.trial_ledger.TrialLedger','literal_configs':len(rules),'effective_n':ledger.effective_n()}
    raise RuntimeError('Canonical trial ledger owner unavailable; no substitute ledger created')

def verify_synthetic():
    rng=np.random.default_rng(93);idx=pd.bdate_range('1980-01-01',periods=1700)
    c=100*np.exp(np.cumsum(rng.normal(0,.012,len(idx))))
    d=pd.DataFrame({'open':c,'close':c,'high':c*1.014,'low':c*.986,'volume':np.full(len(c),100.)},index=idx)
    ff=features(d,idx)
    prefix=1327;fp=features(d.iloc[:prefix],idx)
    checks=[]
    for tf in ff:
        for col in ['k','d','hist','q20','q80','bottom_curl','top_cross']:
            a=ff[tf][col].iloc[:prefix];b=fp[tf][col]
            if a.dtype==bool or col.startswith(('bottom','top')):
                assert a.fillna(False).equals(b.fillna(False)),(tf,col,'prefix changed')
            else:assert np.allclose(a,b,equal_nan=True),(tf,col,'prefix changed')
        checks.append('prefix_invariance_'+tf)
    mutated=d.copy();mutated.loc[idx[prefix]:,['open','high','low','close']]*=1.75
    fm=features(mutated,idx)
    for tf in ff:assert np.allclose(ff[tf]['hist'].iloc[:prefix],fm[tf]['hist'].iloc[:prefix],equal_nan=True)
    checks.append('future_perturbation_no_signal_change')
    series=pd.Series(np.arange(150.),index=idx[:150]);fm0=future_extreme(series,63,'min')
    assert fm0.iloc[0]==1 and fm0.iloc[86]==87 and pd.isna(fm0.iloc[87])
    checks.append('future_window_excludes_signal_and_requires_full_horizon')
    v=rma(pd.Series([np.nan,1.,2.,3.,4.]),3)
    assert v.iloc[3]==2 and np.isclose(v.iloc[4],8/3)
    checks.append('wilder_seed_arithmetic')
    for side,sign in [('bottom',1),('top',-1)]:
        z,_=labels(d,ff,side,'TEST','us_stock')
        eligible=np.flatnonzero(z.qualified.to_numpy()&(np.arange(len(d))>600)&(np.arange(len(d))<1400))
        assert len(eligible)>0
        t=int(eligible[0]);pp=float(z.candidate_price.iloc[t]);ap=float(z.atr_p.iloc[t])
        dd=d.copy();future=idx[t+1:t+64]
        dd.loc[future,'close']=pp+sign*2*ap;dd.loc[future,'open']=dd.loc[future,'close']
        dd.loc[future,'high']=pp+(3*ap if sign==1 else -.5*ap)
        dd.loc[future,'low']=pp+(.5*ap if sign==1 else -3*ap)
        col='low' if sign==1 else 'high'
        dd.loc[idx[t+20],col]=pp-sign*.1*ap
        near,_=labels(dd,ff,side,'TEST','us_stock')
        assert near.p.iloc[t]==z.p.iloc[t] and near.qualified.iloc[t]==z.qualified.iloc[t]
        assert near.survive63.iloc[t]==1 and near.strict63.iloc[t]==0 and near.primary63.iloc[t]==1
        dd.loc[idx[t+20],col]=pp-sign*.35*ap
        far,_=labels(dd,ff,side,'TEST','us_stock')
        assert far.p.iloc[t]==z.p.iloc[t] and far.distance.iloc[t]==z.distance.iloc[t]
        assert far.survive63.iloc[t]==0 and far.primary63.iloc[t]==0
        checks.append(side+'_frozen_candidate_and_tolerance_label_test')
    ss=split_labels(pd.DatetimeIndex(['2013-12-15','2014-01-02']),pd.DatetimeIndex(['2014-03-01','2014-04-01']))
    assert list(ss)==['excluded','validation'];checks.append('split_boundary_purge')
    a=event_indices([False,True,True,False,True],[True]*5,21)
    assert a.tolist()==[1];checks.append('activation_and_cooldown')
    assert len({r['rule_id'] for r in catalog_rules(base_rules())})==len(catalog_rules(base_rules()))
    checks.append('unique_trial_catalog')
    return checks

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--self-test',action='store_true');parser.add_argument('--reuse-cache',action='store_true')
    parser.add_argument('--features-only',action='store_true')
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    checks=verify_synthetic();dump(a.out/'verification.json',{'checks_passed':checks,'count':len(checks)})
    if a.self_test:print('VERIFIED',len(checks));return
    bases=base_rules();rules=catalog_rules(bases)
    dump(a.out/'rule_catalog.json',rules);ledger=log_catalog(rules,a.out)
    if a.reuse_cache:
        events=pd.read_parquet(a.out/'base_events.parquet');piv=pd.read_parquet(a.out/'reference_pivots.parquet')
        coverage=pd.read_csv(a.out/'coverage.csv')
    else:
        events,piv,coverage,_=build_events(a.manifest,bases)
        events.to_parquet(a.out/'base_events.parquet',index=False);piv.to_parquet(a.out/'reference_pivots.parquet',index=False)
        coverage.to_csv(a.out/'coverage.csv',index=False)
    print('EVENTS',len(events),'PIVOTS',len(piv),'RULES',len(rules),flush=True)
    if a.features_only:return
    dev=summarize_catalog(events,piv,rules);dev.to_csv(a.out/'development_validation.csv',index=False)
    finalists=choose_finalists(dev,rules)
    lock={'selection_only':'2014-2019','test_start':'2020-01-01','selected':finalists,
          'catalog_sha256':digest(a.out/'rule_catalog.json'),'code_sha256':digest(Path(__file__)),
          'protocol_sha256':digest(Path(__file__).parent/'PROTOCOL.md'),
          'created_at':pd.Timestamp.now(tz='UTC').isoformat(),'trial_accounting':ledger}
    dump(a.out/'selection_lock.json',lock)
    print('SELECTION_FROZEN',len(finalists),digest(a.out/'selection_lock.json'),flush=True)
    final=final_tables(events,piv,finalists,rules,a.out)
    summary={'events':len(events),'pivots':len(piv),'catalog_configs':len(rules),'selected':len(finalists),
             'selection_lock_sha256':digest(a.out/'selection_lock.json'),'checks_passed':len(checks),
             'evidence_state':'RETROSPECTIVE_EXPLORATORY_WITH_CHRONOLOGICAL_TEST',
             'final_rows':len(final),'source_manifest_sha256':digest(a.manifest),
             'sources_ok':int(coverage.ticker.nunique()),'no_production_signal_or_trade_admission':True}
    dump(a.out/'run_summary.json',summary)
    print('COMPLETE',json.dumps(summary),flush=True)

if __name__=='__main__':main()
