"""Frozen R6 chronological forecast/utility research. Never a live model owner."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.crypto_science import r4_sequence_study as r4, r5_participation_study as r5
H=pd.Timedelta(hours=1)
BASE='3d656d97f8935bccac81299b786e54e3d9868de4'
PLAN='067f0fb76f7fc20239aa4cdeae03b6cf5b279b85'
OUT=Path(__file__).with_name('r6')
PRICE=['x_response','x_structure','x_lows','x_return24','x_trend720','x_log_sigma']
PV=PRICE+['x_volume']


def continuous_features(frame,anchor,family='downside',signal_start=None):
    r5.checked_index(frame);a=pd.Timestamp(anchor)
    if family not in ('downside','recovery'):raise ValueError('Unknown family')
    if family=='recovery' and signal_start is None:
        return dict(status='no_candidate',issue=None,**{k:None for k in PV})
    s=a+6*H if family=='downside' else pd.Timestamp(signal_start)
    result=dict(status='price_unknown',issue=s+H,**{k:None for k in PV})
    history=r5.prices(frame,pd.date_range(s-720*H,periods=721,freq='h'))
    prior_end=a-H if family=='downside' else s-3*H
    prior=r5.prices(frame,pd.date_range(prior_end-72*H,periods=73,freq='h'))
    structure_index=(pd.date_range(a-72*H,periods=72,freq='h') if family=='downside'
                     else pd.date_range(s-6*H,periods=6,freq='h'))
    structure=r5.prices(frame,structure_index)
    if history is None or prior is None or structure is None:return result
    sigma=float(np.std(np.diff(np.log(prior.close)),ddof=1))
    if not np.isfinite(sigma) or sigma<=0:return result
    c=float(history.close.iloc[-1]);ref=float(frame.loc[a if family=='downside' else s-6*H,'close'])
    level=float(structure.low.min() if family=='downside' else structure.high.max())
    last6=history.iloc[-6:];lo1=float(last6.low.iloc[:3].min());lo2=float(last6.low.iloc[-3:].min())
    values=[np.log(c/ref)/(sigma*np.sqrt(6)),np.log(c/level)/(sigma*np.sqrt(6)),
            np.log(lo2/lo1)/(sigma*np.sqrt(3)),np.log(c/history.close.iloc[-25])/(sigma*np.sqrt(24)),
            np.log(c/history.close.iloc[0])/(sigma*np.sqrt(720)),np.log(sigma)]
    result.update(zip(PRICE,map(float,values)))
    active=(pd.date_range(a+H,periods=6,freq='h') if family=='downside'
            else pd.date_range(s-2*H,periods=3,freq='h'))
    refidx=(pd.date_range(a-72*H,periods=72,freq='h') if family=='downside'
            else pd.date_range(s-74*H,periods=72,freq='h'))
    v=r5.participation(frame,active,refidx)
    result.update(status='ok' if v is not None else 'volume_unknown',x_volume=float(np.log1p(v)) if v is not None else None)
    return result


def training_rows(frame,cutoff,columns,embargo_hours):
    f=frame.copy();cut=pd.Timestamp(cutoff)
    numeric=f[columns+['y']].apply(pd.to_numeric,errors='coerce')
    mask=(pd.to_datetime(f.issue)<cut)&(pd.to_datetime(f.end)+embargo_hours*H<cut)
    mask &= np.isfinite(numeric).all(axis=1)&numeric.y.isin([0.,1.])
    return f.loc[mask].copy()


def logistic_objective(beta,z,y,penalty=.05):
    score=beta[0]+z@beta[1:]
    value=np.mean(np.logaddexp(0,score)-y*score)+penalty*.5*np.dot(beta[1:],beta[1:])
    err=expit(score)-y
    grad=np.r_[err.mean(),z.T@err/len(y)+penalty*beta[1:]]
    return float(value),grad


def fit_logistic(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    if x.ndim!=2 or len(x)!=len(y) or not len(y) or not np.isfinite(x).all() or not np.isin(y,[0,1]).all():
        raise ValueError('Invalid finite binary training data')
    mean=x.mean(axis=0);scale=x.std(axis=0);scale=np.where(scale>1e-12,scale,1.)
    z=np.clip((x-mean)/scale,-5,5);prior=(y.sum()+1)/(len(y)+2)
    initial=np.r_[np.log(prior/(1-prior)),np.zeros(x.shape[1])]
    sol=minimize(logistic_objective,initial,args=(z,y),jac=True,method='L-BFGS-B',
                 options={'maxiter':2000,'gtol':1e-9,'ftol':1e-12})
    good=bool(sol.success and np.isfinite(sol.x).all() and np.isfinite(sol.fun))
    return {'status':'ok' if good else 'optimizer_failed','mean':mean.tolist(),'scale':scale.tolist(),
            'coef':sol.x.tolist(),'objective':float(sol.fun),'iterations':int(sol.nit),
            'gradient_max':float(np.max(np.abs(sol.jac))),'message':str(sol.message)}


def predict(model,x):
    if model['status']!='ok':raise ValueError('No fitted model')
    x=np.asarray(x,float)
    if not np.isfinite(x).all():raise ValueError('Unobserved feature')
    z=np.clip((x-np.asarray(model['mean']))/np.asarray(model['scale']),-5,5)
    return expit(model['coef'][0]+z@np.asarray(model['coef'][1:]))


def fit_snapshot(frame,cutoff,columns,embargo_hours):
    f=training_rows(frame,cutoff,columns,embargo_hours)
    y=f.y.to_numpy(float);n=len(y);pos=int(y.sum());neg=n-pos
    result={'status':'insufficient_training','n':n,'positives':pos,'negatives':neg,
            'train_indices':list(map(int,f.index)),
            'last_train_end':str(pd.to_datetime(f.end).max()) if n else None,
            'prevalence':float((pos+1)/(n+2)),'columns':columns}
    if n<80 or min(pos,neg)<15:return result
    result.update(fit_logistic(f[columns].to_numpy(float),y))
    return result


def payoff_mapping(y,gain):
    y=np.asarray(y,float);gain=np.asarray(gain,float)
    known=np.isfinite(gain)&np.isin(y,[0,1]);y=y[known];gain=gain[known]
    counts=[int((y==j).sum()) for j in [0,1]]
    if min(counts)<15:return None
    overall=float(gain.mean())
    return {'n':len(y),'n0':counts[0],'n1':counts[1],'overall':overall,
            'mu0':float((gain[y==0].sum()+10*overall)/(counts[0]+10)),
            'mu1':float((gain[y==1].sum()+10*overall)/(counts[1]+10))}


def probability_metrics(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    if not len(y):return {'n':0}
    if len(y)!=len(p) or not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or (p<0).any() or (p>1).any():
        raise ValueError('Invalid scored outcomes/probabilities')
    n1=int(y.sum());n0=len(y)-n1;q=np.clip(p,1e-12,1-1e-12)
    auc=float((rankdata(p)[y==1].sum()-n1*(n1+1)/2)/(n0*n1)) if n0 and n1 else None
    bins=np.array([0,.1,.2,.3,.5,.75,1.]);which=np.digitize(p,bins[1:-1]);reliability=[]
    for j in range(len(bins)-1):
        mask=which==j;n=int(mask.sum())
        reliability.append({'low':float(bins[j]),'high':float(bins[j+1]),'n':n,
                            'mean_probability':float(p[mask].mean()) if n else None,
                            'event_fraction':float(y[mask].mean()) if n else None})
    return {'n':len(y),'positive':n1,'brier':float(np.mean((p-y)**2)),
            'log_loss':float(-np.mean(y*np.log(q)+(1-y)*np.log1p(-q))),
            'auc':auc,'mean_probability':float(p.mean()),'event_fraction':float(y.mean()),'reliability':reliability}


def finite_record(record):
    out={}
    for k,v in record.items():
        if isinstance(v,pd.Timestamp):v=v.isoformat(sep=' ')
        elif v is pd.NaT:v=None
        elif isinstance(v,(float,np.floating)) and not np.isfinite(v):v=None
        elif isinstance(v,np.generic):v=v.item()
        out[k]=v
    return out


def summarize(predictions,policies):
    periods={'all_issued':('2018-01-01','2027-01-01'),'2018_2019':('2018-01-01','2020-01-01'),
             '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}
    forecast=[];utility=[]
    for period,(lo,hi) in periods.items():
        for (family,lag),raw in predictions.groupby(['family','lag_hours']):
            dates=pd.to_datetime(raw.issue);f=raw.loc[(dates>=lo)&(dates<hi)].copy()
            s={'period':period,'family':family,'lag_hours':int(lag),'candidate_rows':len(f),'status_counts':f.forecast_status.value_counts().to_dict()}
            valid=f.dropna(subset=['y','p0','p1','p2']).copy()
            s['scores']={m:probability_metrics(valid.y,valid[m]) for m in ['p0','p1','p2']}
            for c,a,b in [('brier_m1_minus_m0','p1','p0'),('brier_m2_minus_m1','p2','p1')]:
                valid[c]=(valid[a]-valid.y)**2-(valid[b]-valid.y)**2
                s[c]={'n':len(valid),'mean':r4.number(valid[c].mean()),'block95':r4.interval90(valid,c) if len(valid) else None}
            forecast.append(s)
        if policies.empty:continue
        for (family,lag,cost,model),raw in policies.groupby(['family','lag_hours','cost_bps','model']):
            dates=pd.to_datetime(raw.issue);f=raw.loc[(dates>=lo)&(dates<hi)]
            good=f.loc[f.policy_status=='scored'].copy()
            s={'period':period,'family':family,'lag_hours':int(lag),'cost_bps':int(cost),'model':model,
               'rows':len(f),'n':len(good),'cash_actions':int(good.cash_action.sum()),'status_counts':f.policy_status.value_counts().to_dict()}
            for c in ['marginal_gain','model_minus_price','model_minus_volume','expected_gain']:
                s[c]={'mean':r4.number(good[c].mean()),'median':r4.number(good[c].median()),'block95':r4.interval90(good,c) if len(good) else None}
            acts=good.loc[good.cash_action==True]
            s['cash_positive']=int((acts.actual_cash_gain>0).sum());s['cash_negative']=int((acts.actual_cash_gain<0).sum())
            s['cash_gain_sum']=r4.number(acts.actual_cash_gain.sum());s['actual_cash_mean_if_acted']=r4.number(acts.actual_cash_gain.mean())
            year=pd.to_datetime(good.issue).dt.year
            s['leave_one_year_out_gain']={str(int(y)):r4.number(good.loc[year!=y,'marginal_gain'].mean()) for y in sorted(year.unique())}
            utility.append(s)
    return forecast,utility


def main():
    import scipy
    from lib import config
    OUT.mkdir(exist_ok=True);data=Path(config.data_dir());old=OUT.parent/'r5';r5result=json.loads((old/'results.json').read_text())
    oldr4=json.loads((OUT.parent/'r4/results.json').read_text())
    inputs=dict(r5result['inputs']);flowpath=data/'okx/taker_volume_hourly.parquet'
    inputs['okx/taker_volume_hourly.parquet']=r4.digest(flowpath)
    gates=dict(r5result['gates'])
    prior={str(p.relative_to(ROOT)):r4.digest(p) for directory in ['r2','r3','r4','r5']
           for p in (OUT.parent/directory).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    source_names=['research/crypto_science/r6_probability_study.py','research/CRYPTO_SCIENCE_R6_PROBABILITY_PREREG_2026-09-28.md',
                  'research/crypto_science/r5_participation_study.py','tests/test_btc_impulse_falsifier.py','collectors/okx.py','collectors/coinbase.py']
    sources={name:r4.digest(ROOT/name) for name in source_names}
    inherited_sources=dict(oldr4['sources'])
    def unchanged():
        assert all((r4.digest(data/k) if (data/k).exists() else None)==h for k,h in inputs.items()),'input drift'
        assert all(r4.digest(data/k)==h for k,h in gates.items()),'gate drift'
        assert all(r4.digest(ROOT/k)==h for k,h in prior.items()),'prior evidence drift'
        assert all(r4.digest(ROOT/k)==h for k,h in inherited_sources.items()),'inherited engine drift'
        assert all(r4.digest(ROOT/k)==h for k,h in sources.items()),'candidate source drift'
    unchanged()
    hourly=pd.read_parquet(data/'coinbase/btc_hourly.parquet');r5.checked_index(hourly)
    oldfeatures=pd.read_csv(old/'features.csv');oldfeatures.anchor=pd.to_datetime(oldfeatures.anchor)
    features=[]
    for row in oldfeatures.itertuples():
        signal=(pd.Timestamp(row.signal_start) if row.family=='recovery' and pd.notna(row.signal_start) else None)
        obs=continuous_features(hourly,row.anchor,row.family,signal)
        features.append(finite_record(dict(family=row.family,anchor=row.anchor,**obs)))
    feats=pd.DataFrame(features);feats.anchor=pd.to_datetime(feats.anchor)
    events=pd.read_csv(old/'events.csv');events.anchor=pd.to_datetime(events.anchor)
    # Keep the R5 issue/entry/end; compare the independently recomputed feature cutoff.
    records=events.merge(feats.drop(columns=['issue']),on=['family','anchor'],validate='many_to_one')
    records.issue=pd.to_datetime(records.issue);records.end=pd.to_datetime(records.end)
    records['y']=np.nan
    mature=records.outcome.isin(['lower_first','upper_first','neither'])
    records.loc[mature,'y']=(((records.loc[mature,'family']=='downside')&(records.loc[mature,'outcome']=='lower_first'))|((records.loc[mature,'family']=='recovery')&(records.loc[mature,'outcome']=='upper_first'))).astype(float)
    records['y']=pd.to_numeric(records.y,errors='coerce')
    # Mapping available labels to target does not permit them into current features.
    accounts=pd.read_csv(old/'policies.csv');accounts.anchor=pd.to_datetime(accounts.anchor)
    account_idx=accounts.set_index(['family','anchor','lag_hours','cost_bps'])
    flow=pd.read_parquet(flowpath);idx=pd.date_range(flow.index.min(),flow.index.max(),freq='h')
    flowgrid=flow.reindex(idx);valid=(np.isfinite(flowgrid).all(axis=1)&(flowgrid>=0).all(axis=1)&flowgrid.sum(axis=1).gt(0))
    complete6=valid.astype(int).rolling(6).sum().eq(6)
    qualification={'status':'EXCLUDED_FROM_FORECASTS','reasons':['aggregate unit/mix and exact bucket meaning not established','no first-publication or revision clock in stored frame','CONTRACTS flow is not Coinbase spot'],
      'source_sha256':r4.digest(flowpath),'rows':len(flow),'first':str(flow.index.min()),'last':str(flow.index.max()),
      'missing_hours':int(len(idx)-len(flow)),'complete_six_observed_rows':int(complete6.sum()),'attrs':flow.attrs,
      'candidate_time_overlap':{fam:int(((pd.to_datetime(feats.loc[feats.family==fam,'issue'])>=idx[0]+6*H)&(pd.to_datetime(feats.loc[feats.family==fam,'issue'])<=idx[-1]+H)).sum()) for fam in ['downside','recovery']},
      'official_document_url':'https://www.okx.com/docs-v5/en/','official_document_sha256':'8a08f29d3da3ad1ecec9a6a36704b09dc61834e6fb9116efb51a7bbf4ae8a02c',
      'no_clock_assumption':'The six-row census assumes chronological hourly bins for metadata only, not verified release-time availability or causal flow.'}
    fits=[];preds=[];policy=[]
    for (fam,lag),raw in records.groupby(['family','lag_hours']):
        common=raw.loc[np.isfinite(raw[PV].to_numpy(float)).all(axis=1)].copy()
        embargo=24 if fam=='downside' else 336
        for q in pd.date_range('2018-01-01','2026-07-01',freq='QS'):
            qend=q+pd.offsets.QuarterBegin(startingMonth=1)
            test=raw.loc[(raw.issue>=q)&(raw.issue<qend)]
            if test.empty:continue
            m1=fit_snapshot(common,q,PRICE,embargo);m2=fit_snapshot(common,q,PV,embargo)
            assert m1['train_indices']==m2['train_indices']
            train=common.loc[m1['train_indices']];fit_id=f'{fam}|{int(lag)}|{q.date()}'
            maps={}
            for cost in [0,10,25]:
                yy=[];gg=[]
                for r in train.itertuples():
                    acc=account_idx.loc[(fam,r.anchor,lag,cost)]
                    if fam=='downside':gain=acc.delayed_return-acc.incumbent_return
                    else:gain=acc.price_return-acc.incumbent_return
                    if pd.notna(gain):yy.append(r.y);gg.append(gain)
                maps[str(cost)]=payoff_mapping(yy,gg)
            fits.append({'id':fit_id,'family':fam,'lag_hours':int(lag),'fit_time':str(q),'embargo_hours':embargo,'m1':m1,'m2':m2,'payoffs':maps})
            fit_ok=m1['status']=='ok' and m2['status']=='ok'
            for r in test.itertuples():
                row={'family':fam,'anchor':r.anchor,'issue':r.issue,'end':r.end,'lag_hours':int(lag),'fit_id':fit_id,'y':r.y,
                     'outcome':r.outcome,'feature_status':r.status,'train_n':m1['n'],'train_positives':m1['positives'],
                     'forecast_status':'ok','p0':None,'p1':None,'p2':None}
                if not np.isfinite(np.array([getattr(r,c) for c in PV],float)).all():row['forecast_status']='features_unavailable'
                elif not fit_ok:row['forecast_status']=m1['status'] if m1['status']!='ok' else m2['status']
                else:
                    row['p0']=m1['prevalence'];row['p1']=float(predict(m1,[[getattr(r,c) for c in PRICE]])[0]);row['p2']=float(predict(m2,[[getattr(r,c) for c in PV]])[0])
                preds.append(finite_record(row))
                if row['forecast_status']!='ok':continue
                for cost in [0,10,25]:
                    mapping=maps[str(cost)];acc=account_idx.loc[(fam,r.anchor,lag,cost)]
                    for model in ['p0','p1','p2']:
                        pr=dict(family=fam,anchor=r.anchor,issue=r.issue,end=r.end,lag_hours=int(lag),cost_bps=cost,model=model,fit_id=fit_id,
                          policy_status='scored',probability=row[model],cash_action=False,expected_gain=None,actual_cash_gain=None,
                          marginal_gain=None,model_minus_price=None,model_minus_volume=None)
                        if mapping is None:pr['policy_status']='payoff_training_insufficient'
                        elif pd.isna(r.y) or pd.isna(acc.incumbent_return) or pd.isna(acc.delayed_return):pr['policy_status']='outcome_or_account_unavailable'
                        else:
                            expected=row[model]*mapping['mu1']+(1-row[model])*mapping['mu0'];act=expected>0
                            gain=acc.delayed_return-acc.incumbent_return;result=acc.delayed_return if act else acc.incumbent_return
                            pr.update(cash_action=bool(act),expected_gain=float(expected),actual_cash_gain=float(gain),marginal_gain=float(result-acc.incumbent_return),
                                      model_minus_price=float(result-acc.price_return),model_minus_volume=float(result-acc.volume_return))
                        policy.append(finite_record(pr))
        print(f'Finished {fam} lag={lag}; fixed quarters, no tuning',flush=True)
    predictions=pd.DataFrame(preds);policies=pd.DataFrame(policy)
    forecast,utility=summarize(predictions,policies)
    unchanged()
    for name,frame in [('features',feats),('labelled_records',records),('predictions',predictions),('policies',policies)]:frame.to_csv(OUT/(name+'.csv'),index=False)
    result={'classification':'RETROSPECTIVE_CHRONOLOGICAL_RESEARCH_NOT_LIVE_PROBABILITIES',
      'baseline':BASE,'plan_commit':PLAN,'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'inputs':inputs,'gates':gates,'prior_evidence':prior,'sources':sources,'inherited_sources':inherited_sources,'hashes_unchanged':True,
      'runtime':{'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__,'scipy':scipy.__version__},
      'counts':{'parent_features':len(feats),'event_records':len(records),'quarter_fits':len(fits),'prediction_rows':len(predictions),'policy_rows':len(policies)},
      'flow_qualification':qualification,'fits':fits,'forecast_summaries':forecast,'utility_summaries':utility,
      'limits':['All historical periods previously studied; chronological out-of-training is not untouched research holdout.',
                'Fixed six-hour post-break landmark is continuation, not pre-crash foresight.',
                'Unsigned participation and price/regime features are not identified causal mechanisms.',
                'Logistic outputs require measured calibration; probability score and action policy tested separately.',
                'Conditional-class economic projection is a hypothesis, not probability-to-sizing authority.',
                'Minimum80/15-per-class not relaxed for the small recovery population.',
                'Existing R5 execution/cost/vintage/gap assumptions retained; no live-source or fill certification.']}
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
    print('R6_COMPLETED',json.dumps(result['counts']))


if __name__=='__main__':main()
