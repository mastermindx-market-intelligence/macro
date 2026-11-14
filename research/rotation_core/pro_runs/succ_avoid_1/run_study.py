"""Frozen SUCC-AVOID-1 research harness; source data are not committed."""
from pathlib import Path
import json, hashlib, warnings
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA, OUT = ROOT/'data', ROOT/'results'
B = 2000
SEED = 1101401
RULES = ['OLD']+[f'C{i}' for i in range(1,9)]
COHORTS = ['FF12','ETF','FF49','ALL']
CHILDREN = {
 'NoDur':'Agric Food Soda Beer Smoke Hshld Clths Txtls', 'Durbl':'Toys Autos',
 'Manuf':'BldMt Steel FabPr Mach ElcEq Aero Ships Guns Paper Boxes', 'Enrgy':'Coal Oil',
 'Chems':'Chems Rubbr', 'BusEq':'Hardw Softw Chips LabEq', 'Telcm':'Telcm','Utils':'Util',
 'Shops':'Whlsl Rtail Meals', 'Hlth':'Hlth MedEq Drugs','Money':'Banks Insur RlEst Fin',
 'Other':'Fun Books Cnstr Gold Mines PerSv BusSv Trans Other'}
METRICS = ['fake10','fake21','fake45','mdd63','avoid63','return_gap']

def read(name):
    df = pd.read_csv(DATA/f'{name}.csv',index_col=0,parse_dates=True)
    assert df.index.min()>=pd.Timestamp('2013-01-02') and df.index.max()<=pd.Timestamp('2023-12-29')
    assert not df.index.has_duplicates
    return df

def ema_seed(df,n):
    a=df.to_numpy(float); out=np.full(a.shape,np.nan)
    for j in range(a.shape[1]):
        seed=[]; prev=np.nan
        for i,x in enumerate(a[:,j]):
            if not np.isfinite(x): seed=[];prev=np.nan;continue
            if np.isnan(prev):
                seed.append(x)
                if len(seed)==n: prev=float(np.mean(seed));out[i,j]=prev
            else: prev=prev+(2/(n+1))*(x-prev);out[i,j]=prev
    return pd.DataFrame(out,index=df.index,columns=df.columns)

def rsi_wilder(df,n=14):
    a=df.to_numpy(float);out=np.full(a.shape,np.nan)
    for j in range(a.shape[1]):
        seed=[]; ag=al=np.nan
        for i in range(1,len(a)):
            if not np.isfinite(a[i,j]) or not np.isfinite(a[i-1,j]):seed=[];ag=al=np.nan;continue
            d=a[i,j]-a[i-1,j];g=max(d,0);l=max(-d,0)
            if np.isnan(ag):
                seed.append((g,l))
                if len(seed)<n:continue
                ag,al=np.mean(seed,axis=0)
            else:ag=((n-1)*ag+g)/n;al=((n-1)*al+l)/n
            out[i,j]=50 if ag==al==0 else 100 if al==0 else 0 if ag==0 else 100-100/(1+ag/al)
    return pd.DataFrame(out,index=df.index,columns=df.columns)

def oscillator(df):
    rsi=rsi_wilder(df);macd=ema_seed(rsi,14)-ema_seed(rsi,60);h=macd-ema_seed(macd,5)
    lo=rsi.rolling(14).min();hi=rsi.rolling(14).max()
    raw=100*(rsi-lo)/(hi-lo).replace(0,np.nan)
    k=raw.rolling(3).mean();d=k.rolling(3).mean()
    top=(k.shift()>80)&(k.shift()>=d.shift())&(k<d)&(h<h.shift())
    bottom=(k.shift()<20)&(k.shift()<=d.shift())&(k>d)&(h>h.shift())
    return {'rsi':rsi,'h':h,'hp':h.shift(),'k':k,'kp':k.shift(),'d':d,'dp':d.shift(),'top':top,'bottom':bottom}

def endpoints(dates,kind):
    if kind=='3d':return np.arange(2,len(dates),3)
    span=7 if kind=='w' else 14
    ids=((dates-pd.Timestamp('2012-12-31')).days//span).to_numpy()
    ends=np.r_[np.where(ids[1:]!=ids[:-1])[0],len(dates)-1]
    # Do not treat an incomplete terminal calendar bar as complete.
    final_end=pd.Timestamp('2012-12-31')+pd.Timedelta(days=int(ids[-1])*span+span-3)
    if final_end>dates[-1]:ends=ends[:-1]
    return ends

def daily_state(x,dates):return x.reindex(dates,method='ffill')
def daily_event(x,dates):return x.reindex(dates,fill_value=False)

def load_panel():
    spy=read('SPY')['adjclose'];dates=spy.index
    ff12=read('ff12').reindex(dates);ff49=read('ff49').reindex(dates)
    assert ff12.notna().all().all() and ff49.notna().all().all()
    ff12=(1+ff12).cumprod().add_prefix('FF12_');ff49=(1+ff49).cumprod().add_prefix('FF49_')
    tickers='XLB XLE XLF XLI XLK XLP XLU XLV XLY XLRE XLC'.split()
    etf=pd.DataFrame({t:read(t)['adjclose'] for t in tickers}).reindex(dates)
    p=pd.concat([ff12,ff49,etf],axis=1).sort_index(axis=1)
    return p,p.div(spy,axis=0),spy

def construct(p,r):
    dates=p.index;gcols=p.columns;N,G=p.shape
    a3=oscillator(p.iloc[endpoints(dates,'3d')]);r3=oscillator(r.iloc[endpoints(dates,'3d')])
    wpx=p.iloc[endpoints(dates,'w')];bpx=p.iloc[endpoints(dates,'2w')]
    aw=oscillator(wpx);ab=oscillator(bpx)
    old=daily_event(a3['top'],dates);rel=daily_event(r3['top'],dates)
    wr=(aw['k']<aw['d'])&(aw['h']<aw['hp'])&(aw['kp']>=50)&(wpx>=.9*wpx.rolling(26).max())
    br=(ab['k']<ab['d'])&(ab['h']<ab['hp'])&(ab['kp']>=50)&(bpx>=.9*bpx.rolling(13).max())
    # Events are evaluated on 3-day endpoints; only completed higher bars are forward-filled.
    candidates={'OLD':old,'C1':rel,'C2':old&rel,'C3':old&daily_state(wr,dates).fillna(False),
                'C4':old&daily_state(br,dates).fillna(False)}
    c5=pd.DataFrame(False,index=dates,columns=gcols)
    breadth_records=[]
    for parent,codes in CHILDREN.items():
        child=['FF49_'+x for x in codes.split()];g='FF12_'+parent
        share_top=old[child].rolling(9,min_periods=9).max().mean(axis=1)
        share_below=(p[child]<p[child].rolling(50).mean()).mean(axis=1)
        c5[g]=old[g]&((share_top>=.4)|(share_below>=.6))
        breadth_records.append(pd.DataFrame({'date':dates,'group':g,'recent_top_share':share_top.values,'below50_share':share_below.values}))
    candidates['C5']=c5
    lr=np.log(r).diff().shift(1)
    recentbottom=daily_event(r3['bottom'],dates).rolling(6,min_periods=6).max().fillna(0).astype(bool)
    bottom_ready=pd.DataFrame(True,index=dates,columns=gcols)
    for key in ['h','hp','k','kp','d','dp']:
        bottom_ready &= daily_state(r3[key],dates).notna()
    bottom_ready=bottom_ready.rolling(6,min_periods=6).min().fillna(0).astype(bool)
    partner_ready=pd.DataFrame(False,index=dates,columns=gcols)
    c6=partner_ready.copy();partnerrows=[]
    for cohort in ['FF12','FF49','ETF']:
        cols=[g for g in gcols if cohort_of(g)==cohort]
        z=lr[cols]
        for g in cols:
            corr=z.rolling(126,min_periods=126).corr(z[g]);corr[g]=np.nan
            a=corr.to_numpy();safe=np.where(np.isfinite(a),a,np.inf)
            mins=safe.min(axis=1);valid=np.isfinite(mins)
            # columns sorted: choose first code within 1e-12 of actual minimum.
            ties=safe<=mins[:,None]+1e-12;chosen=ties.argmax(axis=1)
            peer_ready=bottom_ready[cols].to_numpy()[np.arange(N),chosen]
            partner_ready[g]=valid & peer_ready
            bottoms=recentbottom[cols].to_numpy()[np.arange(N),chosen]
            c6[g]=old[g] & valid & peer_ready & (mins<=-.25) & bottoms
            partnerrows.append(pd.DataFrame({'date':dates,'group':g,'partner':np.array(cols)[chosen],
                                             'correlation':np.where(valid,mins,np.nan)}))
    candidates['C6']=c6
    logr=np.log(p).diff();rv21=logr.rolling(21).std(ddof=1)*np.sqrt(252);rv63=logr.rolling(63).std(ddof=1)*np.sqrt(252)
    lowq=rv21.shift(22).rolling(252).quantile(.4)
    macros={s:read(s).iloc[:,0].reindex(dates).ffill(limit=5) for s in ['DGS2','DGS10','BAMLH0A0HYM2','DTWEXB','DTWEXBGS','VIXCLS']}
    vix=macros['VIXCLS'].shift(1)
    vstate=(vix>=20)|((vix-vix.shift(5))>=2)
    candidates['C7']=old&(rv21>=1.25*rv21.shift(21))&(rv21.shift(21)<=lowq)
    candidates['C7']=candidates['C7'].mul(vstate,axis=0).astype(bool)
    y10=macros['DGS10'].shift(1);y2=macros['DGS2'].shift(1);hy=macros['BAMLH0A0HYM2'].shift(1)
    usdold=macros['DTWEXB'].shift(5);usdnew=macros['DTWEXBGS'].shift(5)
    usdchg=(usdold/usdold.shift(63)-1).where(dates<pd.Timestamp('2020-01-01'),usdnew/usdnew.shift(63)-1)
    mdata=pd.DataFrame({'curve':y10-y2,'yield63':y10-y10.shift(63),'dollar63':usdchg,'hy21':hy-hy.shift(21)},index=dates)
    mscore=((mdata['curve']<0).astype(int)+(mdata['yield63']>=.5).astype(int)+(mdata['dollar63']>=.02).astype(int)+(mdata['hy21']>=.25).astype(int))
    mok=mdata.notna().all(axis=1)
    candidates['C8']=old.mul((mscore>=2)&mok,axis=0).astype(bool)
    ready=pd.DataFrame(True,index=dates,columns=gcols)
    for features in [a3,r3,aw,ab]:
        for key in ['h','hp','k','kp','d']:
            ready &= daily_state(features[key],dates).notna()
    ready &= daily_state(wpx.rolling(26).max(),dates).notna()
    ready &= daily_state(bpx.rolling(13).max(),dates).notna()
    ready &= lowq.notna() & rv21.shift(21).notna() & rv63.notna() & partner_ready
    ready=ready.mul(mok & vix.notna() & vix.shift(5).notna(),axis=0).astype(bool)
    eligibility=ready.copy();eligibility.iloc[-73:]=False;eligibility.iloc[:73]=False
    # Full data support for shifted event outcomes, relative windows, and all members.
    eligibility &= p.notna() & r.notna()
    return candidates,eligibility,ready,rv63,{'macro':mdata,'breadth':pd.concat(breadth_records),'partners':pd.concat(partnerrows)}

def cohort_of(g):return 'FF12' if g.startswith('FF12_') else 'FF49' if g.startswith('FF49_') else 'ETF'

def outcomes(p,r):
    N,G=p.shape;pv=p.to_numpy();rv=r.to_numpy()
    highs=(r>r.shift(1).rolling(63).max()).to_numpy()
    result={k:np.full((N,G),np.nan) for k in METRICS+['lateness','relative_gain21','absolute_gain21','first_high21']}
    for t in range(63,N):
        hist=rv[t-63:t];finite=np.isfinite(hist).all(axis=0)
        lag=1+np.argmax(np.where(np.isfinite(hist[::-1]),hist[::-1],-np.inf),axis=0)
        result['lateness'][t]=np.where(finite,lag,np.nan)
    for h in [10,21,45]:
        for t in range(N-h):result[f'fake{h}'][t]=highs[t+1:t+h+1].any(axis=0).astype(float)
    own_mdd=np.full((N,G),np.nan);own_avoid=own_mdd.copy();own_gap=own_mdd.copy()
    for t in range(N-63):
        path=pv[t:t+64];valid=np.isfinite(path).all(axis=0)
        with np.errstate(invalid='ignore',divide='ignore'):
            mdd=(1-path/np.maximum.accumulate(path,axis=0)).max(axis=0)
            exitdd=np.maximum(0,1-pv[t+1]/pv[t]);gap=(pv[t+1]-pv[t+63])/pv[t]
        own_mdd[t]=np.where(valid,mdd,np.nan);own_avoid[t]=np.where(valid,mdd-exitdd,np.nan);own_gap[t]=np.where(valid,gap,np.nan)
    result['mdd63']=own_mdd.copy();result['avoid63']=own_avoid.copy();result['return_gap']=own_gap.copy()
    for parent,children in CHILDREN.items():
        j=p.columns.get_loc('FF12_'+parent);idx=[p.columns.get_loc('FF49_'+c) for c in children.split()]
        for metric,arr in [('mdd63',own_mdd),('avoid63',own_avoid),('return_gap',own_gap)]:
            result[metric][:,j]=arr[:,idx].mean(axis=1)
    for t in range(N-21):
        with np.errstate(invalid='ignore',divide='ignore'):
            result['relative_gain21'][t]=(rv[t+1:t+22]/rv[t]-1).max(axis=0)
            result['absolute_gain21'][t]=(pv[t+1:t+22]/pv[t]-1).max(axis=0)
        first=highs[t+1:t+22].argmax(axis=0)+1
        result['first_high21'][t]=np.where(highs[t+1:t+22].any(axis=0),first,np.nan)
    return result,highs

def event_frame(mask,p,outs,rule,source=None):
    ti,gi=np.where(mask.to_numpy())
    if source is not None:raise ValueError('Use shifted_frame')
    df=pd.DataFrame({'rule':rule,'t':ti,'g':gi,'date':p.index[ti],'group':p.columns[gi]})
    df['cohort']=[cohort_of(g) for g in df['group']]
    for k,v in outs.items():df[k]=v[ti,gi]
    df['origin_t']=ti;df['month']=df['date'].dt.strftime('%Y-%m')
    return df

def shifted_frame(df,k,p,outs):
    out=df.copy();ti=df.t.to_numpy()+k;gi=df.g.to_numpy()
    out['t']=ti;out['date']=p.index[ti];out['rule']=df['rule']+('_EARLY10' if k<0 else '_LATE10')
    # Retain origin month to resample pairs together.
    for name,a in outs.items():out[name]=a[ti,gi]
    assert np.isfinite(out[METRICS+['lateness']].to_numpy()).all()
    return out

def monthly_arrays(df,months,metrics=METRICS):
    counts=df.groupby('month').size().reindex(months,fill_value=0).to_numpy(float)
    sums=df.groupby('month')[metrics].sum().reindex(months,fill_value=0).to_numpy(float)
    return counts,sums

def basic_contrast(a,b,months,W):
    if len(a)==0 or len(b)==0:return {'n':len(a),'support':0,'effects':{}}
    ac,ay=monthly_arrays(a,months);bc,by=monthly_arrays(b,months)
    an=W@ac;bn=W@bc
    with np.errstate(invalid='ignore',divide='ignore'):delta=(W@ay)/an[:,None]-(W@by)/bn[:,None]
    point=a[METRICS].mean().to_numpy()-b[METRICS].mean().to_numpy()
    effects={}
    for j,k in enumerate(METRICS):
        v=delta[:,j];v=v[np.isfinite(v)]
        effects[k]={'delta':float(point[j]),'lo':float(np.quantile(v,.05)) if len(v) else None,
                    'hi':float(np.quantile(v,.95)) if len(v) else None,'valid_bootstrap':len(v)}
    return {'n':len(a),'support':1.,'effects':effects}

def matched_old(a,b,months,W):
    if a.empty or b.empty:return {'n':len(a),'support':0,'effects':{}}
    a=a.copy();b=b.copy();a['cell']=a['group']+'|'+a['lateness'].astype(int).astype(str);b['cell']=b['group']+'|'+b['lateness'].astype(int).astype(str)
    cells=sorted(set(a.cell)&set(b.cell));original=len(a);a=a[a.cell.isin(cells)];b=b[b.cell.isin(cells)]
    if a.empty:return {'n':original,'support':0,'effects':{}}
    def matrix(df,col=None):
        z=df.groupby(['month','cell']).size() if col is None else df.groupby(['month','cell'])[col].sum()
        return z.unstack(fill_value=0).reindex(index=months,columns=cells,fill_value=0).fillna(0).to_numpy(float)
    ac=matrix(a);bc=matrix(b);an=W@ac;bn=W@bc;support=(an>0)&(bn>0);weights=np.where(support,an,0);den=weights.sum(axis=1)
    ac0=ac.sum(axis=0);bc0=bc.sum(axis=0);effects={}
    for metric in METRICS:
        ay=matrix(a,metric);by=matrix(b,metric)
        point=((ay.sum(axis=0)/ac0-by.sum(axis=0)/bc0)*ac0).sum()/ac0.sum()
        with np.errstate(invalid='ignore',divide='ignore'):
            dif=(W@ay)/an-(W@by)/bn;draw=np.nansum(np.where(support,dif*weights,0),axis=1)/den
        v=draw[np.isfinite(draw)]
        effects[metric]={'delta':float(point),'lo':float(np.quantile(v,.05)) if len(v) else None,
                        'hi':float(np.quantile(v,.95)) if len(v) else None,'valid_bootstrap':len(v)}
    return {'n':original,'matched_n':len(a),'support':len(a)/original,'cells':len(cells),'effects':effects}

def summary(df,elig,cohort,rule,cuts):
    cols=[g for g in elig if cohort=='ALL' or cohort_of(g)==cohort]
    if rule.startswith('C5') or rule.startswith('VOL_C5'):cols=[g for g in cols if cohort_of(g)=='FF12']
    den=int(elig[cols].to_numpy().sum()) if cols else 0
    d=df if cohort=='ALL' else df[df.cohort==cohort]
    row={'cohort':cohort,'rule':rule,'n':len(d),'groups':int(d.group.nunique()),'eligible_group_days':den,
         'on_share':len(d)/den if den else None,'flags_per_group_year':len(d)*252/den if den else None,
         'median_lateness':float(d.lateness.median()) if len(d) else None}
    row.update({k:float(d[k].mean()) if len(d) else None for k in METRICS})
    for i in range(3):
        s=d[d.tercile==i+1];row[f't{i+1}_n']=len(s);row[f't{i+1}_fake21']=float(s.fake21.mean()) if len(s) else None
    return row

def mdd(path):
    return float(np.max(1-path/np.maximum.accumulate(path)))

def continuous(df,p,elig,rule):
    records=[]
    for g in p.columns:
        if rule.startswith('C5') or rule.startswith('VOL_C5'):
            if cohort_of(g)!='FF12':continue
        valid=np.flatnonzero(elig[g].to_numpy())
        if not len(valid):continue
        start,end=valid[0],valid[-1]
        flat=np.zeros(len(p),bool)
        for t in df.loc[df.group==g,'t'].astype(int):flat[max(0,t+2):min(len(p),t+64)]=True
        ret=p[g].pct_change(fill_method=None).to_numpy()[start+1:end+1]
        mask=flat[start+1:end+1]
        bh=np.r_[1,np.cumprod(1+ret)];policy=np.r_[1,np.cumprod(1+np.where(mask,0,ret))]
        records.append({'rule':rule,'group':g,'cohort':cohort_of(g),'flat_share':float(mask.mean()),
                        'hold_mdd':mdd(bh),'policy_mdd':mdd(policy),'dd_reduction':mdd(bh)-mdd(policy),
                        'hold_return':float(bh[-1]-1),'policy_return':float(policy[-1]-1),'return_gap':float(policy[-1]-bh[-1])})
    return records

def main():
    warnings.filterwarnings('ignore',category=FutureWarning)
    OUT.mkdir(exist_ok=True)
    p,r,spy=load_panel();dates=p.index
    print('Constructing frozen features',p.shape,flush=True)
    candidates,elig,ready,rv63,features=construct(p,r)
    if elig.to_numpy().sum()<10000:raise RuntimeError('Insufficient common eligibility; investigate input coverage before any outcome analysis')
    print('Feature eligibility established',int(elig.to_numpy().sum()),flush=True)
    outs,highs=outcomes(p,r)
    tapes={k:event_frame(v&elig,p,outs,k) for k,v in candidates.items()}
    old=tapes['OLD']
    cuts=np.quantile(old.lateness,[1/3,2/3],method='inverted_cdf').astype(int).tolist()
    volmask=rv63.ge(rv63.quantile(2/3),axis=1)&elig
    tapes['VOL33']=event_frame(volmask,p,outs,'VOL33')
    for rule in RULES:
        target=tapes[rule];mask=pd.DataFrame(False,index=dates,columns=p.columns)
        for group,count in target.groupby('group').size().items():
            poss=np.flatnonzero(volmask[group].to_numpy())
            if len(poss)<count:raise RuntimeError('Infeasible exact volatility match '+rule+' '+group)
            ranked=sorted(poss,key=lambda t:hashlib.sha256(f'SUCC-AVOID-1|VOL|{group}|{dates[t]:%Y-%m-%d}'.encode()).hexdigest())
            mask.loc[dates[ranked[:count]],group]=True
        tapes['VOL_'+rule]=event_frame(mask,p,outs,'VOL_'+rule)
        tapes[rule+'_EARLY10']=shifted_frame(target,-10,p,outs)
        tapes[rule+'_LATE10']=shifted_frame(target,10,p,outs)
    for df in tapes.values():df['tercile']=np.searchsorted(cuts,df.lateness.to_numpy(),side='left')+1
    assert all(len(tapes[r])==len(tapes['VOL_'+r])==len(tapes[r+'_EARLY10'])==len(tapes[r+'_LATE10']) for r in RULES)
    months=sorted(set(dates[elig.any(axis=1)].strftime('%Y-%m')))
    W=np.random.default_rng(SEED).multinomial(len(months),np.ones(len(months))/len(months),size=B).astype(float)
    summaries=[];effects={};policies=[]
    for rule,df in tapes.items():
        for cohort in COHORTS:summaries.append(summary(df,elig,cohort,rule,cuts))
        policies.extend(continuous(df,p,elig,rule))
    for cohort in COHORTS:
        effects[cohort]={}
        select=lambda x:x if cohort=='ALL' else x[x.cohort==cohort]
        o=select(tapes['OLD'])
        for rule in RULES:
            a=select(tapes[rule]);effects[cohort][rule]={}
            effects[cohort][rule]['OLD_MATCHED']=matched_old(a,o,months,W)
            effects[cohort][rule]['VOL_MATCHED']=basic_contrast(a,select(tapes['VOL_'+rule]),months,W)
            effects[cohort][rule]['EARLY10']=basic_contrast(a,select(tapes[rule+'_EARLY10']),months,W)
            effects[cohort][rule]['LATE10']=basic_contrast(a,select(tapes[rule+'_LATE10']),months,W)
        print('Bootstrap cohort complete',cohort,flush=True)
    sdf=pd.DataFrame(summaries);sdf.to_csv(OUT/'summary.csv',index=False,float_format='%.10g')
    pd.DataFrame(policies).to_csv(OUT/'continuous_policy.csv',index=False,float_format='%.10g')
    (OUT/'effects.json').write_text(json.dumps(effects,indent=2,allow_nan=False))
    all_events=pd.concat(tapes.values(),ignore_index=True);all_events.to_csv(OUT/'events_all_scored.csv',index=False,float_format='%.10g',date_format='%Y-%m-%d')
    raw=[]
    for rule,mask in candidates.items():
        ti,gi=np.where(mask.to_numpy());raw.append(pd.DataFrame({'rule':rule,'date':dates[ti],'group':p.columns[gi],
            'scored':elig.to_numpy()[ti,gi],'unscored_reason':np.where(elig.to_numpy()[ti,gi],'',np.where(ready.to_numpy()[ti,gi],'incomplete_forward_support','feature_warmup_or_missing'))}))
    pd.concat(raw).to_csv(OUT/'flags_all_observable.csv',index=False,date_format='%Y-%m-%d')
    coverage=[];annual=[]
    for g in p:
        e=dates[elig[g]];coverage.append({'group':g,'cohort':cohort_of(g),'first_price':str(p[g].first_valid_index().date()),
            'first_scored':str(e.min().date()) if len(e) else None,'last_scored':str(e.max().date()) if len(e) else None,'eligible_days':len(e)})
    for cohort in COHORTS:
        for rule,df in tapes.items():
            cols=[g for g in p if cohort=='ALL' or cohort_of(g)==cohort]
            if rule.startswith('C5') or rule.startswith('VOL_C5'):cols=[g for g in cols if cohort_of(g)=='FF12']
            d=df if cohort=='ALL' else df[df.cohort==cohort]
            for y in range(2013,2024):
                den=int(elig.loc[dates.year==y,cols].to_numpy().sum()) if cols else 0
                source_year=p.index[d.origin_t.to_numpy()].year
                n=int((source_year==y).sum())
                annual.append({'cohort':cohort,'rule':rule,'year':y,'flags':n,'eligible_group_days':den,'on_share':n/den if den else None})
    pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual_counts.csv',index=False)
    finalists=[]
    for rule in RULES[1:]:
        a=tapes[rule];a=a[a.cohort=='FF12']
        if len(a)>=30 and a.group.nunique()>=4:
            e=effects['FF12'][rule];finalists.append((e['OLD_MATCHED']['effects']['fake21']['delta'],-e['VOL_MATCHED']['effects']['avoid63']['delta'],rule))
    best=[x[2] for x in sorted(finalists)[:2]]
    if len(best)<2:
        best+=sorted([r for r in RULES[1:] if r not in best],key=lambda rule:(-len(tapes[rule]),rule))[:2-len(best)]
    bestdf=tapes[best[0]]
    worst=bestdf[bestdf.fake21==1].sort_values(['relative_gain21','absolute_gain21','group','date'],ascending=[False,False,True,True]).head(10)
    worst.to_csv(OUT/'worst_fakes.csv',index=False,date_format='%Y-%m-%d',float_format='%.10g')
    missed=[];episodes=[]
    for j,g in enumerate(p):
        if best[0]=='C5' and cohort_of(g)!='FF12':continue
        vals=p[g].to_numpy();flagdates=set(np.flatnonzero(candidates[best[0]][g].to_numpy()))
        proposals={}
        for t in np.flatnonzero(highs[:,j]):
            if t+63>=len(p) or not np.isfinite(vals[t:t+64]).all():continue
            trough=t+1+int(np.argmin(vals[t+1:t+64]));decline=1-vals[trough]/vals[t]
            if decline<.10:continue
            # Latest relative high for a shared trough.
            if trough not in proposals or t>proposals[trough]['t']:
                proposals[trough]={'t':int(t),'trough_t':int(trough),'decline':float(decline)}
        kept=[]
        for item in sorted(proposals.values(),key=lambda x:(-x['decline'],x['t'])):
            if any(not(item['trough_t']<x['t'] or item['t']>x['trough_t']) for x in kept):continue
            kept.append(item)
            t=item['t'];tr=item['trough_t'];caught=any(t<=f<=min(t+21,tr-1) for f in flagdates)
            later=any(t+21<f<=t+63 for f in flagdates)
            active_prior=any(f+2<=t<=f+63 for f in flagdates)
            row={'group':g,'cohort':cohort_of(g),'high_date':str(dates[t].date()),'trough_date':str(dates[tr].date()),
                'decline':item['decline'],'caught_timely':caught,'warning_days22_to63':later,'exit_already_active_at_high':active_prior,
                'member_mdd63':float(outs['mdd63'][t,j]),'peak_in_scored_panel':bool(elig.iloc[t,j]),
                'common_features_available_at_peak':bool(ready.iloc[t,j])}
            episodes.append(row)
            if not caught:missed.append(row)
    missed=sorted(missed,key=lambda x:(-x['decline'],x['high_date'],x['group']))
    pd.DataFrame(missed[:10]).to_csv(OUT/'largest_missed.csv',index=False,float_format='%.10g')
    pd.DataFrame(episodes).to_csv(OUT/'real_top_episodes.csv',index=False,float_format='%.10g')
    chosen=pd.concat([tapes[x] for x in ['OLD']+best]);chosen.to_csv(OUT/'old_and_finalist_flags.csv',index=False,date_format='%Y-%m-%d',float_format='%.10g')
    # Retain only derived input audit features on flag dates; raw macro/price data stay local.
    context=features['partners'].merge(chosen[['date','group']].drop_duplicates(),on=['date','group'],how='inner')
    context.to_csv(OUT/'flag_partner_audit.csv',index=False,date_format='%Y-%m-%d',float_format='%.10g')
    meta={'run':'SUCC-AVOID-1','protocol_commit':'2a1924f0092a4bb0f4a3f4d85d129b9eaf2c3c6e','seed':SEED,'bootstrap_draws':B,
          'observations':len(p),'groups':len(p.columns),'old_lateness_tercile_boundaries':cuts,'bootstrap_months':months,
          'best_two_by_frozen_reporting_rank':best,'candidate_count':8,'candidate_threshold_tuning_runs':0,
          'original_rule_count':1,'volatility_tapes':10,'shifted_tapes':18,'tapes_total':len(tapes),
          'fake_horizons':[10,21,45],'primary_fake_horizon':21,'hypothesis_specs_dropped':0,
          'feature_eligibility_group_days':int(elig.to_numpy().sum()),'real_top_episodes':len(episodes),'missed_top_episodes':len(missed),
          'scoring_first':str(dates[elig.any(axis=1)].min().date()),'scoring_last':str(dates[elig.any(axis=1)].max().date()),
          'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()}
    (OUT/'run_metadata.json').write_text(json.dumps(meta,indent=2))
    # LOCAL ONLY audit checkpoint: includes vendor levels; NEVER publish this NPZ.
    np.savez_compressed(OUT/'audit_arrays.npz',dates=dates.strftime('%Y-%m-%d').to_numpy(dtype=str),groups=p.columns.to_numpy(dtype=str),
                        prices=p.to_numpy(),relative=r.to_numpy(),eligibility=elig.to_numpy(),**{f'signal_{k}':v.to_numpy() for k,v in candidates.items()})
    print(json.dumps(meta),flush=True)
    print(sdf[(sdf.cohort=='FF12')&sdf.rule.isin(RULES)][['rule','n','fake21','median_lateness','mdd63','avoid63']].to_string(index=False),flush=True)

if __name__=='__main__':main()
