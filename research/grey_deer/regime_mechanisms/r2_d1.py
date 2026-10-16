"""R2-D1 research only. No production imports, collectors, ledgers or policy writes.
Run: python r2_d1.py --repo-root /path/to/macro --out /isolated/research/output
The pinned data and preregistration are fixed; refusal is preferable to substitution.
"""
from __future__ import annotations
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata

PIN='f6dae649ee6d32ec65a95ccea411b205d0b0bc45'
PREREG='1d0d0e2c6861e680fe4e0de73f90e74b302752a7'
END='2026-09-25'
SPECS={
'spy':('data/yahoo/SPY.parquet','close','70e78d38834e129ddf48e782b4c633c388479e86484eecb2f4046cc2acd1a4af'),
'move':('data/yahoo/_MOVE.parquet','close','93c4e4aaa87451646312f2643afa07e69d1bdeb56b467924f75c515feb6e2a97'),
'vix':('data/yahoo/_VIX.parquet','close','31a88a0113eb837108ac6c2cf1d2ccb0b9b2a0fa3131a09b42a5a7018dcd5a04'),
'tlt':('data/yahoo/TLT.parquet','close','d69d3f8c54f7e00d305ec358f906f836a458728f8bdd0ee86ea7921811519d38'),
'n2':('data/fred/DGS2.parquet','us2y','aac49f450bb2d70377d2f3f62112f2d5fd38700b83c7ad3dc52e8f7dcf4d2102'),
'n10':('data/fred/DGS10.parquet','us10y','86ff480555fc3de845ff576325d2b96de039034a19a6ffc508829f5efda119cd'),
'r10':('data/fred/DFII10.parquet','us10y_real','8714929802efe9ee634c6d8a3251845aca4e26bada7062d7ef74a5c4dec151fc'),
'oas':('data/fred/BAMLH0A0HYM2.parquet','hy_oas','5a50c7daa61f0ecc6961a84c97b29d227972839e0fe085fad9c5a1b4b41d6168'),
'payroll':('data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet',None,'5fe02dde232efad7799d14b5331bd83d4ba2f849dc82e687bd49ade357debaee'),
'cpi':('data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet',None,'abc6b65a873a3d6de63d85379c86b61f71f99480354f46915c391d506970718b')}
BASE=['n2','n10','r10','real5','real21','nominal2_21','oas','oas21','move_pctile','move_accel',
      'vix_pctile','payroll_yoy','payroll_accel','cpi_yoy','cpi_accel','damage','spy21']
INTER=['real_x_inflation','credit_x_growth','move_x_credit','real_x_damage']


def macro_events(frame, sid):
    d=frame.loc[frame['series'].eq(sid)].copy()
    for k in ['period','realtime_start']: d[k]=pd.to_datetime(d[k]).astype('datetime64[ns]')
    if d.duplicated(['period','realtime_start']).any(): raise ValueError('duplicate vintage/period')
    if not d['source_output_type'].eq(2).all(): raise ValueError('full vintages required')
    if not (np.isfinite(d.value)&(d.value>0)).all(): raise ValueError('invalid macro levels')
    rows=[]
    for release,g in d.groupby('realtime_start',sort=True):
        s=g.set_index('period')['value'].sort_index();p=s.index[-1]
        if p>release: raise ValueError('observation period after release date')
        required=[p,p-pd.DateOffset(months=12),p-pd.DateOffset(months=3),p-pd.DateOffset(months=15)]
        v=s.reindex(required).to_numpy()
        if not np.isfinite(v).all(): continue
        yoy=100*(v[0]/v[1]-1);accel=yoy-100*(v[2]/v[3]-1)
        rows.append({'release_date':release,'yoy':yoy,'accel':accel,'period':p})
    return pd.DataFrame(rows,columns=['release_date','yoy','accel','period']).set_index('release_date')


def prior_join(index, frame, max_sessions=None):
    idx=pd.DatetimeIndex(index).astype('datetime64[ns]')
    if idx.has_duplicates or not idx.is_monotonic_increasing: raise ValueError('ordered unique calendar required')
    r=frame.copy();r.index=pd.DatetimeIndex(r.index).astype('datetime64[ns]')
    if r.index.has_duplicates: raise ValueError('duplicate source dates')
    r=r.sort_index().rename_axis('source_date').reset_index()
    out=pd.merge_asof(pd.DataFrame({'date':idx}),r,left_on='date',right_on='source_date',
                      direction='backward',allow_exact_matches=False).set_index('date')
    if max_sessions is not None:
        good=out.source_date.notna()
        ages=np.full(len(idx),np.inf)
        ages[good]=np.flatnonzero(good)-idx.searchsorted(out.loc[good,'source_date'],side='right')+1
        out.loc[ages>max_sessions,frame.columns]=np.nan
    return out


def vol_features(s):
    s=s.sort_index().where(np.isfinite(s)&(s>0))
    def midrank(a):
        if not np.isfinite(a[-1]): return np.nan
        v=a[np.isfinite(a)];return 100*((v<a[-1]).sum()+.5*(v==a[-1]).sum())/len(v)
    pctile=s.rolling(504,min_periods=252).apply(midrank,raw=True)
    good=s.notna().rolling(21,min_periods=21).sum().eq(21)
    gap=s.index.to_series().diff().dt.days.rolling(20,min_periods=1).max().gt(7)
    fast=((s/s.shift(5)-1>=.20)&(s-s.shift(5)>=10))|((s/s.shift(20)-1>=.30)&(s-s.shift(20)>=15))
    return pd.DataFrame({'pctile':pctile,'accel':fast.astype(float)}).where((good&~gap),axis=0)


def forward_event(s,horizon,threshold):
    f=pd.concat([s.shift(-i) for i in range(1,horizon+1)],axis=1)
    complete=f.notna().all(axis=1)&s.notna()&(s>0)
    return (f.min(axis=1,skipna=False)/s-1<=-threshold).astype(float).where(complete)


def fit_ridge(X,y,C):
    X=np.asarray(X,float);y=np.asarray(y,float)
    if X.ndim!=2 or len(X)!=len(y) or not np.isfinite(X).all() or not np.isfinite(y).all(): raise ValueError('invalid fit data')
    if set(np.unique(y))!={0.,1.}: raise ValueError('two outcome classes required')
    mean=X.mean(axis=0);scale=X.std(axis=0);scale=np.where(scale>1e-12,scale,1.)
    Z=np.column_stack([np.ones(len(X)),(X-mean)/scale])
    def objective(b):
        z=Z@b;loss=np.logaddexp(0,z).sum()-y@z+(.5/C)*(b[1:]@b[1:])
        grad=Z.T@(expit(z)-y);grad[1:]+=b[1:]/C
        return loss,grad
    start=np.zeros(Z.shape[1]);start[0]=np.log((y.sum()+.5)/(len(y)-y.sum()+.5))
    opt=minimize(objective,start,jac=True,method='L-BFGS-B',options={'maxiter':1200,'ftol':1e-13,'gtol':1e-7})
    grad=float(np.max(abs(objective(opt.x)[1])))
    if not opt.success or grad>1e-3: raise RuntimeError(f'optimizer refused: {opt.message}; gradient={grad}')
    return {'mean':mean,'scale':scale,'coef':opt.x,'C':float(C),'gradient_inf':grad,'iterations':int(opt.nit)}


def predict(model,X):
    Z=(np.asarray(X,float)-model['mean'])/model['scale']
    return expit(model['coef'][0]+Z@model['coef'][1:])


def quality(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    if not len(y): return {'n':0}
    positives=int(y.sum());negatives=len(y)-positives
    auc=float((rankdata(p)[y==1].sum()-positives*(positives+1)/2)/(positives*negatives)) if positives and negatives else None
    order=np.argsort(-p,kind='stable');a=y[order];scores=p[order];ends=np.r_[np.flatnonzero(scores[:-1]!=scores[1:]),len(scores)-1]
    tp=np.cumsum(a)[ends];recall=tp/positives if positives else np.zeros(len(tp))
    ap=float(np.sum(np.diff(np.r_[0,recall])*(tp/(ends+1)))) if positives else None
    clipped=np.clip(p,1e-12,1-1e-12)
    return {'n':len(y),'events':positives,'base_rate':float(y.mean()),'brier':float(np.mean((p-y)**2)),
            'log_loss':float(-np.mean(y*np.log(clipped)+(1-y)*np.log1p(-clipped))),
            'auc':auc,'average_precision':ap,'mean_probability':float(p.mean())}


def anchors(flags,known):
    out=np.zeros(len(flags),dtype=bool);armed=True;quiet=0
    for i,(f,k) in enumerate(zip(flags,known)):
        if not k: quiet=0;continue
        if f: out[i]=armed;armed=False;quiet=0
        else:
            quiet+=1
            if quiet>=21: armed=True
    return out


def training_mask(index,test_start,purge=63):
    idx=pd.DatetimeIndex(index);pos=int(idx.searchsorted(test_start))-purge
    return (idx<idx[max(pos,0)])&(idx>=pd.Timestamp('2007-01-01'))


def load_inputs(repo):
    data={};manifest=[]
    for name,(path,col,expected) in SPECS.items():
        raw=subprocess.check_output(['git','-C',str(repo),'show',PIN+':'+path]);h=hashlib.sha256(raw).hexdigest()
        if h!=expected: raise ValueError('source hash mismatch: '+path)
        frame=pd.read_parquet(BytesIO(raw))
        manifest.append({'name':name,'path':path,'sha256':h,'bytes':len(raw),'rows':len(frame),'columns':list(frame.columns)})
        if col:
            s=frame[col].copy();s.index=pd.DatetimeIndex(s.index).astype('datetime64[ns]');s=s.sort_index().loc[:END]
            if s.index.has_duplicates: raise ValueError('duplicate market date: '+path)
            data[name]=s
        else: data[name]=frame
    return data,manifest


def build_panel(data):
    spy=data['spy'];idx=spy.index;f=pd.DataFrame(index=idx);lineage={}
    for name in ['n2','n10','r10','oas']:
        joined=prior_join(idx,data[name].to_frame(name),3);f[name]=joined[name];lineage[name]=joined.source_date
    for name in ['move','vix']:
        v=vol_features(data[name]);joined=prior_join(idx,v,3)
        f[name+'_pctile']=joined.pctile;lineage[name]=joined.source_date
        if name=='move':f['move_accel']=joined.accel
    for key,sid in [('payroll','PAYEMS'),('cpi','CPIAUCSL')]:
        events=macro_events(data[key],sid);j=prior_join(idx,events)
        valid=((j.index-j.source_date).dt.days<=60)&((j.index-j.period).dt.days<=95)
        f[key+'_yoy']=j.yoy.where(valid);f[key+'_accel']=j.accel.where(valid);lineage[key]=j.source_date
    f['real5']=f.r10.diff(5);f['real21']=f.r10.diff(21);f['nominal2_21']=f.n2.diff(21);f['oas21']=f.oas.diff(21)
    f['damage']=100*(spy/spy.rolling(252,min_periods=252).max()-1);f['spy21']=100*(spy/spy.shift(21)-1)
    f['real_x_inflation']=f.real21*f.cpi_accel;f['credit_x_growth']=f.oas21*(-f.payroll_accel)
    f['move_x_credit']=f.move_accel*f.oas21;f['real_x_damage']=f.real21*(-f.damage)
    f['Y21']=forward_event(spy,21,.05);f['Y63']=forward_event(spy,63,.10)
    tlt=data['tlt'].reindex(idx);future=pd.concat([tlt.shift(-i) for i in range(1,22)],axis=1)
    complete=future.notna().all(axis=1)&tlt.notna()&f.Y21.notna()
    f['JOINT21']=((spy.shift(-21)/spy-1<0)&(tlt.shift(-21)/tlt-1<0)).astype(float).where(complete)
    f['backdrop']=np.where(f.payroll_accel>0,'employment_accelerating','employment_slowing')+'__'+np.where(f.cpi_accel>0,'inflation_accelerating','inflation_slowing')
    f.loc[(f.payroll_accel==0)|(f.cpi_accel==0),'backdrop']='flat_axis'
    lineage=pd.DataFrame(lineage,index=idx)
    if not ((lineage.lt(pd.Series(idx,index=idx),axis=0))|lineage.isna()).all().all():raise ValueError('same/future source joined')
    return f,lineage


def select_c(panel,cols,target,year,eligible):
    # Hyperparameter selection obeys the OUTER fold's availability cutoff too.
    outer_dates=panel.index[panel.index.year==year]
    if not len(outer_dates): raise ValueError('outer test year missing')
    outer_known=training_mask(panel.index,outer_dates[0])
    scores=[]
    for C in [.1,1.,10.]:
        errors=[]
        for inner in [year-2,year-1]:
            dates=panel.index[panel.index.year==inner]
            if not len(dates):continue
            train=training_mask(panel.index,dates[0])&eligible;test=(panel.index.year==inner)&eligible&outer_known
            if train.sum()<300 or test.sum()==0 or panel.loc[train,target].nunique()<2:continue
            model=fit_ridge(panel.loc[train,cols],panel.loc[train,target],C)
            errors.append(np.mean((predict(model,panel.loc[test,cols])-panel.loc[test,target])**2))
        scores.append((float(np.mean(errors)) if errors else np.inf,C))
    return sorted(scores)[0][1] if np.isfinite(min(v[0] for v in scores)) else 1.


def run_models(panel,target):
    eligible=np.isfinite(panel[BASE+INTER]).all(axis=1)&panel[target].notna()
    pred=pd.DataFrame(index=panel.index,columns=['D0','D1','D2'],dtype=float);folds=[];warn={}
    for key in ['D1','D2']:
        for burden in [.05,.10,.20]:warn[(key,burden)]=pd.Series(np.nan,index=panel.index)
    for year in range(2015,2027):
        dates=panel.index[panel.index.year==year]
        if not len(dates):continue
        tr=training_mask(panel.index,dates[0])&eligible;te=(panel.index.year==year)&eligible
        if tr.sum()<300 or te.sum()==0 or panel.loc[tr,target].nunique()<2:continue
        y=panel.loc[tr,target];pred.loc[te,'D0']=(y.sum()+.5)/(len(y)+1)
        receipt={'year':year,'n_train':int(tr.sum()),'n_test':int(te.sum()),'train_last':str(panel.index[tr][-1].date()),'models':{}}
        for name,cols in [('D1',BASE),('D2',BASE+INTER)]:
            C=select_c(panel,cols,target,year,eligible);model=fit_ridge(panel.loc[tr,cols],y,C)
            p=predict(model,panel.loc[te,cols]);pred.loc[te,name]=p
            ptr=predict(model,panel.loc[tr,cols]);thresholds={}
            for burden in [.05,.10,.20]:
                q=float(np.quantile(ptr,1-burden,method='higher'));warn[(name,burden)].loc[te]=(p>=q).astype(float);thresholds[str(burden)]=q
            receipt['models'][name]={'C':C,'gradient_inf':model['gradient_inf'],'iterations':model['iterations'],'thresholds':thresholds}
        folds.append(receipt);print(target,year,'train',int(tr.sum()),'test',int(te.sum()),flush=True)
    return pred,warn,folds,eligible


def paired_blocks(delta,length,draws=2000):
    a=np.asarray(delta,float);n=len(a);rng=np.random.default_rng(20260927+length);out=[]
    if n<length: return None
    for _ in range(draws):
        starts=rng.integers(0,n-length+1,size=int(np.ceil(n/length)))
        sample=a[(starts[:,None]+np.arange(length)).ravel()[:n]]
        if np.isfinite(sample).any():out.append(float(np.nanmean(sample)))
    return {'block_sessions':length,'draws':len(out),'mean_delta':float(np.nanmean(a)),
            'ci95':[float(v) for v in np.quantile(out,[.025,.975])]}


def summarize(panel,target,pred,warn,folds,eligible):
    ok=pred.notna().all(axis=1)&panel[target].notna();y=panel.loc[ok,target]
    report={'n':int(ok.sum()),'first_test':str(panel.index[ok][0].date()),'last_test':str(panel.index[ok][-1].date()),
            'pooled':{k:quality(y,pred.loc[ok,k]) for k in pred},'annual':[], 'backdrops':{},'warning_metrics':{},'fold_receipts':folds}
    for year in range(2015,2027):
        m=ok&(panel.index.year==year)
        if m.any(): report['annual'].append({'year':year,**{k:quality(panel.loc[m,target],pred.loc[m,k]) for k in pred}})
    for backdrop in sorted(panel.loc[ok,'backdrop'].unique()):
        m=ok&panel.backdrop.eq(backdrop);report['backdrops'][backdrop]={k:quality(panel.loc[m,target],pred.loc[m,k]) for k in pred}
    report['calibration']={}
    for name in pred:
        bins=[]
        for lo in np.arange(0,1,.1):
            m=ok&(pred[name]>=lo)&(pred[name]<(lo+.1 if lo<.9 else 1.000001))
            if m.any():bins.append({'low':round(float(lo),1),'n':int(m.sum()),'mean_p':float(pred.loc[m,name].mean()),'observed':float(panel.loc[m,target].mean())})
        report['calibration'][name]=bins
    delta=((pred.D2-panel[target])**2-(pred.D1-panel[target])**2).where(ok)
    test_delta=delta.loc['2015-01-01':report['last_test']]
    report['paired_brier_D2_minus_D1']=[paired_blocks(test_delta,L) for L in [21,63,126]]
    for (name,burden),w in warn.items():
        known=w.notna()&panel[target].notna();fires=w.fillna(0).astype(bool);a=pd.Series(anchors(fires.to_numpy(),known.to_numpy()),index=panel.index)&known
        n=int((fires&known).sum());hits=int(((panel[target]==1)&fires&known).sum());ea=int(a.sum());eh=int(((panel[target]==1)&a).sum())
        report['warning_metrics'][name+'_'+str(burden)]={'target_training_burden':burden,'realized_test_burden':n/int(known.sum()),'fired_dates':n,'precision':hits/n if n else None,'recall':hits/int((panel.loc[known,target]==1).sum()) if panel.loc[known,target].sum() else None,'episode_anchors':ea,'episode_hits':eh,'episode_precision':eh/ea if ea else None}
    windows={'2007_09':('2007-01-01','2009-12-31'),'2011':('2011-01-01','2011-12-31'),'2015_16':('2015-01-01','2016-12-31'),'2018':('2018-01-01','2018-12-31'),'2020':('2020-01-01','2020-12-31'),'2022':('2022-01-01','2022-12-31'),'banks_2023':('2023-03-01','2023-05-31'),'august_2024':('2024-08-01','2024-08-31'),'april_2025':('2025-04-01','2025-04-30')}
    report['aggregation_exclusions_not_refits']={}
    for label,(lo,hi) in windows.items():
        removed=ok&(panel.index>=lo)&(panel.index<=hi);kept=ok&~removed
        report['aggregation_exclusions_not_refits'][label]={'removed_dates':int(removed.sum()),'delta_brier':float(delta.loc[kept].mean())}
    return report


def main(repo,out):
    out.mkdir(parents=True,exist_ok=True);data,manifest=load_inputs(repo);panel,lineage=build_panel(data)
    panel.to_csv(out/'research_panel.csv',float_format='%.12g');lineage.to_csv(out/'source_date_lineage.csv')
    study={'schema':'r2_d1.v1','data_pin':PIN,'prereg_commit':PREREG,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'authority':'NONE','evidence':'archived macro vintages plus date-lagged current market snapshots; not full vendor-vintage PIT',
           'incumbent_comparison':'NOT_RUN','inputs':manifest,'feature_columns':BASE,'interactions':INTER,
           'eligibility':{'total_calendar_dates':len(panel),'common_feature_dates_2007_on':int((np.isfinite(panel[BASE+INTER]).all(axis=1)&(panel.index>='2007-01-01')).sum()),'missing_by_feature_2007_on':panel.loc['2007-01-01':,BASE].isna().sum().to_dict()},'targets':{}}
    for target in ['Y21','Y63','JOINT21']:
        pred,warn,folds,eligible=run_models(panel,target)
        study['targets'][target]=summarize(panel,target,pred,warn,folds,eligible)
        pd.concat([panel[[target,'backdrop']],pred],axis=1).to_csv(out/(target+'_predictions.csv'),float_format='%.12g')
        (out/'results.json').write_text(json.dumps(study,indent=2,allow_nan=False)+'\n')
        print('TARGET_COMPLETE',target,{k:study['targets'][target]['pooled'][k]['brier'] for k in ['D0','D1','D2']},flush=True)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='output_manifest.json'}
    (out/'output_manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('FINISHED',json.dumps(hashes),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();main(args.repo_root,args.out)
