"""Run the frozen PRO-RUN B study; outputs contain only small derived tables.

Usage: python acquire.py; python -m unittest -v test_integrity; python run_study.py
Raw inputs remain in ./raw and must never be committed.
"""
from pathlib import Path
import json,hashlib,platform
import numpy as np
import pandas as pd
from inputs import load,coverage,manifest,french,CUTOFF
from engine import run_rules,RULES
from inference import metrics,contrast,holm,years,maxdd
from episodes import ERAS,WINDOWS,calm_stats,episode_tables,rate_diagnostics

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'out'

def identified_segment(frame):
    """Longest contiguous known-return segment; selection uses only missingness."""
    valid=frame['return'].notna().to_numpy()
    best=(0,0);start=None
    for i,ok in enumerate(np.r_[valid,False]):
        if ok and start is None:start=i
        elif not ok and start is not None:
            if i-start>best[1]-best[0]:best=(start,i)
            start=None
    return frame.iloc[best[0]:best[1]]

def main():
    OUT.mkdir(exist_ok=True)
    print('loading cutoff-filtered public inputs',flush=True)
    data=load()
    assert data['index'].max()<=CUTOFF
    print('simulating frozen rules and identical-path cost stress',flush=True)
    choices,paths,stress,b3,passive,targets=run_rules(data)
    cov=coverage(data);cov.to_csv(OUT/'coverage.csv',index=False)
    pd.DataFrame(data['missing_records']).to_csv(OUT/'missing_observations.csv',index=False)
    rows=[];passive_rows=[]
    for era,a,b in ERAS+[('ALL','1926-07-01','2019-12-31')]:
        print('paired bootstrap',era,flush=True)
        for rid in RULES:
            first=paths[rid]['return'].first_valid_index()
            frame=paths[rid].loc[max(pd.Timestamp(a),first):b] if first is not None else paths[rid].iloc[:0]
            missing=int(frame['return'].isna().sum())
            path=identified_segment(frame);idx=path.index
            if len(path)<252:
                rows.append({'era':era,'rule':rid,'n':len(path),'status':'insufficient','p_raw':1.})
                continue
            m=data['gross'].M.reindex(idx);e=data['E49'].reindex(idx)
            exposure=b3[rid].reindex(idx)
            row={'era':era,'rule':rid,'name':RULES[rid],'coverage_status':'FULL_AVAILABLE' if missing==0 else 'PARTIAL_SEGMENT','unknown_sessions_in_era':missing,**metrics(path,m)}
            refs={'M':m,'B3':exposure['return']}
            if e.notna().all():refs['E49']=e
            comparisons=contrast(path['return'],refs)
            for ref,vals in comparisons.items():
                for key,value in vals.items():row[ref+'_'+key]=value
            row['B2_exact_EW']='UNAVAILABLE'
            row['B3_equity']=exposure.equity.mean()
            row['market_cagr']=np.expm1(np.log1p(m).sum()/years(idx))
            row['E49_cagr']=np.expm1(np.log1p(e).sum()/years(idx)) if e.notna().all() else np.nan
            row['B3_cagr']=np.expm1(np.log1p(exposure['return']).sum()/years(idx))
            stressed=metrics(stress[rid].loc[idx],m)
            for field in ['cagr','vol','maxdd','up_capture','down_capture','turnover']:
                row['stress_'+field]=stressed[field]
            if rid not in ['R1','R2','R3','R4']:
                p=passive['MIX'].loc[idx,'return']
                if p.notna().all():
                    cmp=contrast(path['return'],{'MIX':p})['MIX']
                    for key,value in cmp.items():row['MIX_'+key]=value
            row['primary_p_raw']=row['B3_p_raw'] if missing==0 else 1.
            rows.append(row)
        for name,path in passive.items():
            frame=path.loc[a:b];first=frame['return'].first_valid_index()
            frame=frame.loc[first:] if first is not None else frame.iloc[:0]
            p=identified_segment(frame);idx=p.index
            if len(p):passive_rows.append({'era':era,'reference':name,'coverage_status':'FULL_AVAILABLE' if frame['return'].notna().all() else 'PARTIAL_SEGMENT',**metrics(p,data['gross'].M.reindex(idx))})
    results=pd.DataFrame(rows)
    selected=results.era.ne('ALL')
    assert selected.sum()==30
    results.loc[selected,'p_holm30']=holm(results.loc[selected,'primary_p_raw'].fillna(1).to_numpy())
    results.to_csv(OUT/'results.csv',index=False,float_format='%.10g')
    primary=results.loc[selected].copy()
    partial=primary.coverage_status.eq('PARTIAL_SEGMENT')
    preserve=['era','rule','name','coverage_status','unknown_sessions_in_era','B2_exact_EW','primary_p_raw','p_holm30']
    primary.loc[partial,[c for c in primary.columns if c not in preserve]]=np.nan
    primary.to_csv(OUT/'primary_era_results.csv',index=False,float_format='%.10g')
    results.loc[selected&results.coverage_status.eq('PARTIAL_SEGMENT')].to_csv(OUT/'partial_segments.csv',index=False,float_format='%.10g')
    pd.DataFrame(passive_rows).to_csv(OUT/'passive_references.csv',index=False,float_format='%.10g')
    print('common-sample H1 comparisons',flush=True)
    h1=[]
    returns=pd.DataFrame({r:paths[r]['return'] for r in ['R1','R2','R3','R4']})
    for era,a,b in ERAS:
        common=returns.loc[a:b].dropna()
        if len(common)<252:continue
        cmp=contrast(common.R4,{r:common[r] for r in ['R1','R2','R3']})
        for rid,values in cmp.items():h1.append({'era':era,'R4_minus':rid,'n':len(common),'start':str(common.index[0].date()),**values,'R4_maxdd':maxdd(common.R4),'single_maxdd':maxdd(common[rid])})
    pd.DataFrame(h1).to_csv(OUT/'h1_common_sample.csv',index=False,float_format='%.10g')
    calm,calm_years=calm_stats(data,choices,paths)
    calm.to_csv(OUT/'false_pivots.csv',index=False,float_format='%.10g')
    ep,rel,lead=episode_tables(data,choices,paths)
    ep.to_csv(OUT/'episodes.csv',index=False,float_format='%.10g')
    rel.to_csv(OUT/'episode_relative.csv',index=False,float_format='%.10g')
    lead.to_csv(OUT/'episode_transitions.csv',index=False,float_format='%.10g')
    rate_diagnostics(data).to_csv(OUT/'rate_conditions.csv',index=False,float_format='%.10g')
    factor_rows=[]
    mom=french('momentum')[0][1].iloc[:,0]
    for era,a,b in ERAS:
        f=data['factors'].loc[a:b].join(mom.rename('Mom'))
        for name in ['C','D']:
            z=f.join((data['gross'][name]-data['factors'].RF).rename('y')).dropna()
            design=np.column_stack([np.ones(len(z)),z[['Mkt-RF','SMB','HML','Mom']]])
            coef=np.linalg.lstsq(design,z.y,rcond=None)[0]
            factor_rows.append({'era':era,'sleeve':name,'n':len(z),'alpha_daily_descriptive':coef[0],'beta_M':coef[1],'beta_SMB':coef[2],'beta_HML':coef[3],'beta_Mom':coef[4]})
    pd.DataFrame(factor_rows).to_csv(OUT/'factor_diagnostics.csv',index=False,float_format='%.10g')
    summary={'rule_count':10,'primary_family':30,'bootstrap_resamples':5000,'block_sessions':252,'seed':20261111,'cutoff':str(CUTOFF.date()),'data_sessions':len(data['index']),'calm_years':calm_years,'strict_stock_equal_weight_market':'unavailable; E49 is explicitly only an equal-industry proxy','vintages':'current-vintage conservatively lagged, not real-time','source_manifest':manifest(),'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')},'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()}
    (OUT/'run_manifest.json').write_text(json.dumps(summary,indent=2))
    # Local audit cache is derived, excluded from publication like the raw inputs.
    audit={'market':data['gross'].M,'E49':data['E49']}
    for rid in RULES:
        audit[rid]=paths[rid]['return'];audit[rid+'_B3']=b3[rid]['return']
    pd.DataFrame(audit).to_pickle(ROOT/'audit_paths.pkl')
    choices.to_pickle(ROOT/'audit_choices.pkl')
    print('COMPLETE: 40 rule/segment rows, 30 primary family slots; all dates <=2019-12-31',flush=True)

if __name__=='__main__':main()
