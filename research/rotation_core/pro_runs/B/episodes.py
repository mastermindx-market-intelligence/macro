"""Frozen retrospective episode anchors and descriptive diagnostics."""
import numpy as np
import pandas as pd
from inference import maxdd
from engine import RULES

WINDOWS=[('1929-32','1929-01-01','1932-12-31'),('1937','1937-01-01','1937-12-31'),('1962','1962-01-01','1962-12-31'),('1966','1966-01-01','1966-12-31'),('1969-70','1969-01-01','1970-12-31'),('1973-74','1973-01-01','1974-12-31'),('1980-82','1980-01-01','1982-12-31'),('1987','1987-01-01','1987-12-31'),('1990','1990-01-01','1990-12-31'),('2000-02','2000-01-01','2002-12-31'),('2007-09','2007-01-01','2009-12-31'),('late2018','2018-07-01','2018-12-31')]
ERAS=[('1926-1959','1926-07-01','1959-12-31'),('1960-1989','1960-01-01','1989-12-31'),('1990-2019','1990-01-01','2019-12-31')]

def total(series):return float(np.expm1(np.log1p(series).sum())) if len(series) and series.notna().all() else np.nan

def anchors(data):
    p=data['price'].M;idx=p.index;out=[]
    for name,start,end in WINDOWS:
        sub=p.loc[start:end];draw=sub/sub.cummax()-1
        trough=draw.idxmin();peak=sub.loc[:trough].idxmax()
        pi=idx.get_loc(peak);ti=idx.get_loc(trough);ei=min(ti+252,len(idx)-1)
        out.append({'episode':name,'window_start':start,'window_end':end,'peak':peak,'trough':trough,'peak_i':pi,'trough_i':ti,'recovery_end':idx[ei],'recovery_i':ei,'recovery_n':ei-ti,'truncated':ei-ti<252,'market_drawdown':float(draw.loc[trough])})
    return out

def calm_stats(data,choices,paths):
    m=data['gross'].M;executed=choices.shift(1)
    excluded=set()
    for _,a,b in WINDOWS:excluded.update(range(int(a[:4]),int(b[:4])+1))
    calm=[y for y,r in m.groupby(m.index.year) if y>=1927 and y not in excluded and maxdd(r)>-.10]
    rows=[]
    for era,a,b in ERAS+[('ALL','1926-07-01','2019-12-31')]:
        for rid in RULES:
            on=executed[rid].eq('M' if rid in ['R1','R2','R3','R4'] else 'C')
            off=executed[rid].eq('RF' if rid in ['R1','R2','R3','R4'] else 'D')
            transition=on.shift(1,fill_value=False)&off
            eligible=[y for y in calm if int(a[:4])<=y<=int(b[:4]) and paths[rid]['return'].loc[str(y)].notna().all()]
            count=int(transition[transition.index.year.isin(eligible)].sum())
            rows.append({'era':era,'rule':rid,'calm_years':len(eligible),'false_pivots':count,'false_pivots_per_calm_year':count/len(eligible) if eligible else np.nan})
    return pd.DataFrame(rows),calm

def episode_tables(data,choices,paths):
    idx=data['index'];executed=choices.shift(1);rows=[];relative=[];lead=[]
    passivegross=data['gross'];market=passivegross.M
    for a in anchors(data):
        name=a['episode'];pi=a['peak_i'];ti=a['trough_i'];ei=a['recovery_i']
        down=idx[pi+1:ti+1];up=idx[ti+1:ei+1]
        c=total(passivegross.C.loc[down]);d=total(passivegross.D.loc[down])
        cu=total(passivegross.C.loc[up]);du=total(passivegross.D.loc[up])
        rr={**a,'C_down':c,'D_down':d,'D_minus_C_down':d-c,'C_recovery':cu,'D_recovery':du,'D_minus_C_recovery':du-cu}
        for field in ['nominal','real','spread','nominal_high','real_high','credit','bill_yield','curve_inverted']:
            rr[field+'_peak']=data['macro'].iloc[pi][field]
            rr[field+'_trough']=data['macro'].iloc[ti][field]
        for group in ['C','D']:
            rr[group+'_members_peak']=int(data['counts'].iloc[pi][group])
        if len(data['spx']):
            sp=data['spx'].reindex(idx).ffill()
            rr['spx_peak_level']=sp.iloc[pi];rr['spx_trough_level']=sp.iloc[ti]
            rr['spx_price_return_same_dates']=sp.iloc[ti]/sp.iloc[pi]-1
        relative.append(rr)
        for rid in RULES:
            s=executed[rid];onasset='M' if rid in ['R1','R2','R3','R4'] else 'C';offasset='RF' if onasset=='M' else 'D'
            on=s.eq(onasset);off=s.eq(offasset)
            exits=np.flatnonzero((on.shift(1,fill_value=False)&off).to_numpy())
            entries=np.flatnonzero((off.shift(1,fill_value=False)&on).to_numpy())
            r=paths[rid]['return']
            row={'episode':name,'rule':rid,'peak':str(a['peak'].date()),'trough':str(a['trough'].date()),'exit_status':'NA','exit_days':np.nan,'exit_date':None,'entry_status':'NA','entry_days':np.nan,'entry_date':None,'drawdown_avoided':np.nan,'upside_missed':np.nan,'recovery_n':a['recovery_n']}
            if s.iloc[pi] in [onasset,offasset] and r.iloc[pi:ei+1].notna().all():
                if off.iloc[pi]:
                    row['exit_status']='PRE';pool=exits[exits<=pi];exit_i=int(pool[-1]) if len(pool) else None
                else:
                    pool=exits[(exits>pi)&(exits<=ti)];exit_i=int(pool[0]) if len(pool) else None
                    row['exit_status']='EXIT' if exit_i is not None else 'NONE'
                if exit_i is not None:row.update(exit_days=exit_i-pi,exit_date=str(idx[exit_i].date()))
                if on.iloc[ti]:
                    row['entry_status']='ON';pool=entries[entries<=ti];entry_i=int(pool[-1]) if len(pool) else None
                else:
                    pool=entries[(entries>ti)&(entries<=ei)];entry_i=int(pool[0]) if len(pool) else None
                    row['entry_status']='ENTRY' if entry_i is not None else 'NONE'
                if entry_i is not None:row.update(entry_days=entry_i-ti,entry_date=str(idx[entry_i].date()))
                row['drawdown_avoided']=maxdd(r.loc[down])-maxdd(market.loc[down])
                row['upside_missed']=total(market.loc[up])-total(r.loc[up])
            rows.append(row)
            # Every transition in the calendar window, not only the selected exit.
            for j in exits:
                if not pd.Timestamp(a['window_start'])<=idx[j]<=pd.Timestamp(a['window_end']):continue
                if j<63 or j+63>=len(idx):continue
                before=idx[j-62:j+1];after=idx[j+1:j+64]
                cb=total(passivegross.C.loc[before]);db=total(passivegross.D.loc[before]);ca=total(passivegross.C.loc[after]);da=total(passivegross.D.loc[after])
                prior=db-cb;future=da-ca
                verdict='anticipator' if prior<=0 and future>0 else ('follower' if prior>0 and future>0 else 'no_forward_defensive_lead')
                lead.append({'episode':name,'rule':rid,'execution':str(idx[j].date()),'days_from_peak':int(j-pi),'D_minus_C_prior63':prior,'D_minus_C_next63':future,'description':verdict})
    return pd.DataFrame(rows),pd.DataFrame(relative),pd.DataFrame(lead)

def rate_diagnostics(data):
    idx=data['index'];g=data['gross'];mac=data['macro'];rows=[]
    monthends=pd.Series(np.arange(len(idx)),index=idx).groupby(idx.to_period('M')).last().to_numpy()
    for i in monthends:
        if i+63>=len(idx):continue
        f=g.iloc[i+1:i+64]
        if not f[['C','D']].notna().all().all():continue
        delta=total(f.D)-total(f.C)
        era=next(e for e,a,b in ERAS if pd.Timestamp(a)<=idx[i]<=pd.Timestamp(b))
        ep=next((e for e,a,b in WINDOWS if pd.Timestamp(a)<=idx[i]<=pd.Timestamp(b)),None)
        for feature in ['nominal_high','real_high','credit','curve_inverted']:
            v=mac.iloc[i][feature]
            if pd.isna(v):continue
            rows.append({'era':era,'feature':feature,'state':int(v),'forward63':delta,'episode':ep})
    frame=pd.DataFrame(rows);out=[]
    for key,df in frame.groupby(['era','feature','state']):
        out.append(dict(zip(['era','feature','state'],key))|{'months':len(df),'distinct_named_episodes':int(df.episode.dropna().nunique()),'mean_D_minus_C_next63':df.forward63.mean(),'median_D_minus_C_next63':df.forward63.median()})
    return pd.DataFrame(out)
