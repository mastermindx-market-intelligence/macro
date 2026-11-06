#!/usr/bin/env python3
"""Fixed same-time and waiting-policy diagnostics; see ROBUSTNESS_PROTOCOL.md."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import study as st
from robustness import fixed_high_rules

def standardized(part, flag, compared, outcome='survive63', draws=2000):
    # Only already-qualified washouts enter this conditional-survival analysis.
    reference=part[part.qualified].copy()
    reference['stratum']=(np.digitize(reference.age,[5,10],right=True)*4+
                         np.digitize(reference.distance,[1],right=True)*2+
                         np.digitize(reference.depth,[6],right=True))
    q=reference[reference[flag] | reference[compared]].copy()
    q['arm']=q[flag].astype(int)
    counts=q.groupby(['stratum','arm']).size().unstack(fill_value=0).reindex(columns=[0,1],fill_value=0)
    common=counts.index[(counts>=5).all(axis=1)]
    z=q[q.stratum.isin(common)]
    result={'qualified_comparison_n':len(q),'common_cells':len(common),'retained_n':len(z),
            'retained_share':len(z)/len(q) if len(q) else np.nan,
            'retained_aligned':int(z.arm.sum()),'retained_comparison':int((1-z.arm).sum()),
            'minimum_cell_n':int(counts.loc[common].min().min()) if len(common) else 0,
            'standardized_aligned':np.nan,'standardized_comparison':np.nan,'standardized_delta':np.nan,
            'delta_ci_low':np.nan,'delta_ci_high':np.nan,'valid_bootstrap_fraction':np.nan,
            'bootstrap_blocks':int(z.halfyear.nunique()),
            'target_retained_n':int(reference.stratum.isin(common).sum()),
            'target_retained_share':float(reference.stratum.isin(common).mean()) if len(reference) else np.nan}
    if not len(common):return result
    weights=reference.groupby('stratum').size().reindex(common).to_numpy(dtype=float);weights/=weights.sum()
    mean=z.groupby(['stratum','arm'])[outcome].mean().unstack().reindex(common)
    aa=float(np.sum(weights*mean[1]));bb=float(np.sum(weights*mean[0]))
    result.update(standardized_aligned=aa,standardized_comparison=bb,standardized_delta=aa-bb)
    blocks=sorted(z.halfyear.unique());cube=np.zeros((len(blocks),len(common),2,2))
    if len(blocks)<2:return result
    bi={v:i for i,v in enumerate(blocks)};si={v:i for i,v in enumerate(common)}
    for (b,s,a),g in z.groupby(['halfyear','stratum','arm']):
        cube[bi[b],si[s],a]=[g[outcome].sum(),len(g)]
    rng=np.random.default_rng(7303);sample=rng.integers(0,len(blocks),size=(draws,len(blocks)))
    total=cube[sample].sum(axis=1);ok=(total[:,:,:,1]>0).all(axis=(1,2))
    result['valid_bootstrap_fraction']=float(ok.mean())
    if ok.sum()>=.8*draws:
        rates=total[ok,:,:,0]/total[ok,:,:,1]
        delta=((rates[:,:,1]-rates[:,:,0])*weights).sum(axis=1)
        result['delta_ci_low'],result['delta_ci_high']=np.quantile(delta,[.025,.975])
    return result

def wait_one(row,d,f,tf,mode):
    side=row.side;sign=1 if side=='bottom' else -1;t=int(row.t);p=int(row.p)
    pivot=float(row.candidate_price);atr=float(row.atr_p)
    extreme=d.low.to_numpy() if sign==1 else d.high.to_numpy()
    cond=f[tf][f'{side}_{mode}'].fillna(False).to_numpy(dtype=bool)
    available=f[tf].valid.fillna(False).to_numpy(dtype=bool)
    ans={'base':row.base,'side':side,'ticker':row.ticker,'asset_class':row.asset_class,'date':row.date,
         'halfyear':row.halfyear,'quarter':row.quarter,'lower_tf':tf,'condition':mode,
         'candidate_date':row.candidate_date,'candidate_price':pivot,'atr_p':atr,
         'original_primary':row.primary63,'original_qualified':bool(row.qualified),
         'original_survival':row.survive63,'status':'no_confirmation','primary63':0.,
         'fixed_end_primary':0.,'qualified':False,'survive63':np.nan,'strict63':np.nan,
         'matched_pivot':'','delay':np.nan,'age':np.nan,'distance':np.nan,'depth':row.depth,
         'confirmation_date':pd.NaT,'signal_close':np.nan,'max_wait_breach_atr':0.}
    for delay in range(11):
        ct=t+delay
        breach=max(0.,float(sign*(pivot-extreme[ct])/atr))
        ans['max_wait_breach_atr']=max(ans['max_wait_breach_atr'],breach)
        # Daily extremes are observed before the close; invalidation has priority.
        if breach>.25:
            ans['status']='invalidated';return ans
        if available[ct] and cond[ct]:
            age=ct-p;dist=float(sign*(d.close.iloc[ct]-pivot)/atr)
            qual=age<=21 and dist<=2 and row.depth>=4
            future=extreme[ct+1:ct+64]
            ex=future.min() if sign==1 else future.max()
            future_breach=float(sign*(pivot-ex)/atr)
            fixed=extreme[ct+1:t+64]
            fx=fixed.min() if sign==1 else fixed.max()
            survived=future_breach<=.25
            ans.update(status='confirmed',delay=delay,age=age,distance=dist,
                       qualified=qual,survive63=float(survived),strict63=float(future_breach<=0),
                       primary63=float(qual and survived),
                       fixed_end_primary=float(qual and sign*(pivot-fx)/atr<=.25),
                       confirmation_date=d.index[ct],signal_close=float(d.close.iloc[ct]),
                       matched_pivot=f'{row.ticker}:{side}:{pd.Timestamp(row.candidate_date).date()}' if age<=21 and dist<=2 else '')
            return ans
    return ans

def main(manifest,out):
    rules=fixed_high_rules();e=pd.read_parquet(out/'base_events.parquet');piv=pd.read_parquet(out/'reference_pivots.parquet')
    selected_bases={r['base'] for r in rules}
    e=e[e.base.isin(selected_bases)&e.split63.eq('test')&~e.asset_class.eq('crypto')].copy()
    _,data,items,eqcal,_=st.load_inputs(manifest)
    waiting=[];augmented=[];waiting_pivots=[];censored={}
    for ticker,d in data.items():
        if items[ticker]['asset_class']=='crypto':continue
        q=e[e.ticker==ticker].copy();f=st.features(d,eqcal)
        pp=piv[(piv.ticker==ticker)&piv['split'].eq('test')].copy()
        pp=pp[pp.t+94<len(d)];waiting_pivots.append(pp)
        for tf in ('1D','2D','3D'):
            q['available_'+tf]=f[tf].valid.fillna(False).to_numpy()[q.t.to_numpy()]
            for mode in (*st.LF_MODES,'opposing_cross'):
                q[f'explicit_opposed_{tf}_{mode}']=False
            for side in st.SIDES:
                where=q.side.eq(side);loc=q.loc[where,'t'].to_numpy();opposite='top' if side=='bottom' else 'bottom'
                for mode in (*st.LF_MODES,'opposing_cross'):
                    if mode=='opposing_cross':
                        opposing=f[tf][f'{side}_macd_cross']
                    else:opposing=f[tf][f'{opposite}_{mode}']
                    q.loc[where,f'explicit_opposed_{tf}_{mode}']=opposing.fillna(False).to_numpy()[loc]
        augmented.append(q)
        eligible=q[q.t+73<len(d)]
        for base,g in q.groupby('base'):
            censored[base]=censored.get(base,0)+int((g.t+73>=len(d)).sum())
        for row in eligible.itertuples():
            for tf in ('1D','2D','3D'):
                for mode in ('both_rising','macd_cross'):
                    waiting.append(wait_one(row,d,f,tf,mode))
        print('MECHANICS',ticker,len(q),flush=True)
    e=pd.concat(augmented,ignore_index=True);w=pd.DataFrame(waiting);wp=pd.concat(waiting_pivots,ignore_index=True)
    e.to_parquet(out/'mechanics_base_events.parquet',index=False)
    w.to_parquet(out/'waiting_events.parquet',index=False)
    std=[];summ=[]
    for r in rules:
        base=e[e.base==r['base']]
        for tf in ('1D','2D','3D'):
            available=base[base['available_'+tf].fillna(False).astype(bool)].copy()
            for mode in (*st.LF_MODES,'opposing_cross'):
                flag=f'lf_{tf}_{mode}';comp=f'explicit_opposed_{tf}_{mode}'
                available['not_aligned']=~available[flag].astype(bool)
                available[comp]=available[comp].fillna(False).astype(bool)
                for typ,other in [('not_aligned','not_aligned'),('explicitly_opposed',comp)]:
                    a=available[available[flag]];b=available[available[other]]
                    result={'rule_id':r['rule_id'],'side':r['side'],'lower_tf':tf,'condition':mode,'comparison':typ,
                            'base_n':len(base),'available_n':len(available),'aligned_n':len(a),'comparison_n':len(b),
                            'aligned_qualified_n':int(a.qualified.sum()),'comparison_qualified_n':int(b.qualified.sum()),
                            'raw_aligned_primary':a.primary63.mean(),'raw_comparison_primary':b.primary63.mean(),
                            'raw_aligned_qualified_survival':a.loc[a.qualified,'survive63'].mean(),
                            'raw_comparison_qualified_survival':b.loc[b.qualified,'survive63'].mean(),
                            **standardized(available,flag,other)}
                    std.append(result)
        for (tf,mode),allw in w[w.base==r['base']].groupby(['lower_tf','condition']):
            c=allw[allw.status.eq('confirmed')]
            bs=base[base[['ticker','date']].apply(tuple,axis=1).isin(set(allw[['ticker','date']].apply(tuple,axis=1)))]
            original=st.summarize(bs,wp,r['side'],'test')
            reference=set(wp.loc[wp.side.eq(r['side']),'pivot_id'])
            detected=set(c.matched_pivot[c.matched_pivot!=''])&reference
            qual=c[c.qualified]
            summ.append({'rule_id':r['rule_id'],'side':r['side'],'lower_tf':tf,'condition':mode,
                         'base_n':len(allw),'administratively_excluded':censored.get(r['base'],0),
                         'confirmed_n':len(c),'invalidated_n':int(allw.status.eq('invalidated').sum()),
                         'unconfirmed_n':int(allw.status.eq('no_confirmation').sum()),
                         'confirmation_rate':len(c)/len(allw),'success_n':int(c.primary63.sum()),
                         'timely_durable_precision':c.primary63.mean(),'timely_durable_yield':c.primary63.sum()/len(allw),
                         'base_timely_durable_rate':original['timely_durable_rate'],
                         'base_qualified_n':original['qualified_n'],'base_qualified_survival':original['qualified_survival63'],
                         'qualified_confirmations':len(qual),'conditional_survival':qual.survive63.mean(),
                         'fixed_end_primary_precision':c.fixed_end_primary.mean(),
                         'median_delay':c.delay.median(),'median_age':c.age.median(),'median_distance':c.distance.median(),
                         'reference_pivots':len(reference),'detected_pivots':len(detected),'recall':len(detected)/len(reference),
                         'base_recall':original['recall'],
                         'missed_original_successes':int(((allw.original_primary==1)&(allw.primary63==0)).sum()),
                         'original_successes':int(allw.original_primary.sum()),
                         'failed_qualified_setups_without_confirmation':int((allw.original_qualified&(allw.original_survival==0)&allw.status.ne('confirmed')).sum())})
    pd.DataFrame(std).to_csv(out/'standardized_alignment.csv',index=False)
    pd.DataFrame(summ).to_csv(out/'waiting_summary.csv',index=False)
    st.dump(out/'mechanics_run.json',{'standardized_rows':len(std),'waiting_policies':len(summ),
        'waiting_event_policy_rows':len(w),'waiting_reference_pivots':len(wp),
        'selection_lock_sha256':st.digest(out/'selection_lock.json'),
        'protocol_sha256':st.digest(Path(__file__).parent/'ROBUSTNESS_PROTOCOL.md')})
    print('MECHANICS_COMPLETE',len(std),len(summ),len(w),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();main(a.manifest,a.out)
