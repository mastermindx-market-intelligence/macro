"""R7 frozen calibration/protection diagnostic; never a live forecast owner."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit,logit
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.crypto_science import r4_sequence_study as r4, r5_participation_study as r5, r6_probability_study as r6
H=pd.Timedelta(hours=1)
BASE='b445029abd6c84a66cadc572929e0beb702be4b7'
PLAN='2e8709464b643a33a5bca53b53999f53ad4756f5'
OUT=Path(__file__).with_name('r7')
MODELS=['r6_rate','raw_price','raw_volume','oot_rate','recent_rate','cal_price','cal_volume']
BINS=np.array([0,.1,.2,.3,.5,.75,1.])
PERIODS={'all_issued':('2018-01-01','2027-01-01'),'2018_2019':('2018-01-01','2020-01-01'),
         '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}


def training_frame(frame,cutoff):
    q=pd.Timestamp(cutoff);num=frame[['p1','p2','y']].apply(pd.to_numeric,errors='coerce')
    ok=(pd.to_datetime(frame.issue)<q)&(pd.to_datetime(frame.end)+24*H<q)&frame.forecast_status.eq('ok')
    ok &= np.isfinite(num).all(axis=1)&num.y.isin([0,1])&num.p1.between(0,1)&num.p2.between(0,1)
    return frame.loc[ok].copy()


def decayed_weights(dates,cutoff):
    age=(pd.Timestamp(cutoff)-pd.DatetimeIndex(dates))/pd.Timedelta(days=1)
    if not np.isfinite(age).all() or (age<0).any():raise ValueError('Future or invalid calibration timestamps')
    return np.exp2(-np.asarray(age,float)/365.)


def apply_offset(p,offset):
    x=np.asarray(p,float)
    if not np.isfinite(x).all() or (x<0).any() or (x>1).any() or not np.isfinite(offset):
        raise ValueError('Invalid probability/offset')
    return expit(logit(np.clip(x,1e-6,1-1e-6))+offset)


def offset_fit(p,y,w):
    p=np.asarray(p,float);y=np.asarray(y,float);w=np.asarray(w,float)
    if len(p)!=len(y) or len(p)!=len(w) or not len(y) or not np.isin(y,[0,1]).all() or not np.isfinite(w).all() or (w<=0).any():
        raise ValueError('Invalid calibration sample')
    apply_offset(p,0.)
    def grad(b):return float(np.dot(w,apply_offset(p,b)-y)/w.sum()+.01*b)
    b=float(brentq(grad,-50,50,xtol=1e-12));s=logit(np.clip(p,1e-6,1-1e-6))+b
    obj=float(np.dot(w,np.logaddexp(0,s)-y*s)/w.sum()+.005*b*b)
    return {'offset':b,'gradient':grad(b),'objective':obj}


def fit_calibrator(frame,cutoff):
    f=training_frame(frame,cutoff);w=decayed_weights(f.issue,cutoff);n=len(f);pos=int(f.y.sum());neg=n-pos
    ess=float(w.sum()**2/np.dot(w,w)) if n else 0.
    result={'status':'insufficient_training','n':n,'positives':pos,'negatives':neg,'effective_n':ess,
            'train_indices':list(map(int,f.index)),'weights':w.tolist(),
            'last_train_end':str(pd.to_datetime(f.end).max()) if n else None}
    if n<80 or min(pos,neg)<15 or ess<40:return result
    result.update(status='ok',oot_rate=float((pos+1)/(n+2)),
                  recent_rate=float((np.dot(w,f.y)+1)/(w.sum()+2)),
                  price=offset_fit(f.p1,f.y,w),volume=offset_fit(f.p2,f.y,w))
    return result


def brier_decomposition(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    if not len(y):return {'n':0}
    score=r6.probability_metrics(y,p);idx=np.digitize(p,BINS[1:-1]);base=float(y.mean())
    rel=res=0.
    for j in range(len(BINS)-1):
        m=idx==j
        if m.any():
            rel+=float(m.mean()*(p[m].mean()-y[m].mean())**2)
            res+=float(m.mean()*(y[m].mean()-base)**2)
    unc=base*(1-base);binned=unc-res+rel
    return dict(score,reliability_bins=score['reliability'],reliability=rel,resolution=res,
                uncertainty=unc,binned_brier=binned,within_bin_residual=score['brier']-binned)


def protection_utility(returns,drawdown,lam):
    r=np.asarray(returns,float);d=np.asarray(drawdown,float)
    if lam not in (0,1,2):raise ValueError('Undeclared utility penalty')
    return r-lam*np.maximum(np.maximum(-d,0)-.05,0)


def gain_map(y,gain,w):
    y=np.asarray(y,float);g=np.asarray(gain,float);w=np.asarray(w,float)
    ok=np.isfinite(g)&np.isin(y,[0,1])&np.isfinite(w)&(w>0)
    y=y[ok];g=g[ok];w=w[ok];n0=int((y==0).sum());n1=int((y==1).sum())
    if min(n0,n1)<15:return None
    mu=float(np.dot(w,g)/w.sum());d={'n':len(y),'n0':n0,'n1':n1,'mean':mu}
    for j in (0,1):
        m=y==j;d['mu'+str(j)]=float((np.dot(w[m],g[m])+10*mu)/(w[m].sum()+10))
    return d


def choose_cash(p,utility_map,return_map):
    if not np.isfinite(p) or not 0<=p<=1:raise ValueError('Invalid action probability')
    if utility_map is None or return_map is None:return {'status':'mapping_unavailable','action':False,'expected_u':None,'expected_r':None}
    eu=p*utility_map['mu1']+(1-p)*utility_map['mu0'];er=p*return_map['mu1']+(1-p)*return_map['mu0']
    return {'status':'ok','action':bool(eu>0 and er>=-.002),'expected_u':float(eu),'expected_r':float(er)}


def frequency_adjust(actions,contrast):
    a=np.asarray(actions,bool);d=np.asarray(contrast,float)
    if not len(a) or len(a)!=len(d) or not np.isfinite(d).all():raise ValueError('Invalid diagnostic sample')
    q=float(a.mean());return (a.astype(float)-q)*d,q


def rebuild_accounts(hourly,base,prior):
    """Add delayed-cash drawdown from existing account timing, not a new policy."""
    rows=[];index=pd.date_range(hourly.index[0],hourly.index[-1],freq='h')
    maps={lag:r4.incumbent_targets(base,index,delay_hours=lag) for lag in [1,6]}
    f=prior.loc[prior.family=='downside']
    for (anchor,lag),group in f.groupby(['anchor','lag_hours']):
        a=pd.Timestamp(anchor);lag=int(lag);origin=a+(1+lag)*H;action=a+(7+lag)*H;end=origin+24*H
        w=r4.complete_window(hourly,origin,24);ix=pd.date_range(origin,end,freq='h');t=maps[lag].reindex(ix)
        good=w is not None and t.notna().all()
        for cost in [0,10,25]:
            row={'anchor':str(a),'lag_hours':lag,'cost_bps':cost,'origin':str(origin),'action_time':str(action),'end':str(end),
                 'status':'ok' if good else 'account_unavailable'}
            if good:
                i=r4.account_path(w.open,t.iloc[:-1],initial_weight=float(t.iloc[0]),terminal_weight=float(t.iloc[-1]),cost_bps=cost)
                d=r4.account_path(w.open,r5.cash_after(t.iloc[:-1],action),initial_weight=float(t.iloc[0]),terminal_weight=float(t.iloc[-1]),cost_bps=cost)
                old=group.loc[group.cost_bps==cost].iloc[0]
                for k,key in [('incumbent_return','return'),('incumbent_drawdown','max_drawdown')]:
                    assert np.isclose(i[key],old[k],atol=1e-12)
                assert np.isclose(d['return'],old.delayed_return,atol=1e-12)
                row.update(inc_r=i['return'],cash_r=d['return'],inc_dd=i['max_drawdown'],cash_dd=d['max_drawdown'],
                           inc_turnover=i['turnover'],cash_turnover=d['turnover'],initial_exposure=float(t.iloc[0]))
            rows.append(row)
    return pd.DataFrame(rows)


def period_frame(f,lo,hi):
    return f.loc[(pd.to_datetime(f.issue)>=pd.Timestamp(lo))&(pd.to_datetime(f.issue)<pd.Timestamp(hi))].copy()


def score_summaries(preds):
    out=[]
    for period,(lo,hi) in PERIODS.items():
        for lag,g in preds.groupby('lag_hours'):
            f=period_frame(g,lo,hi);v=f.loc[f.calibration_status=='ok'].dropna(subset=['y']+MODELS).copy()
            s={'period':period,'lag_hours':int(lag),'candidates':len(f),'statuses':f.calibration_status.value_counts().to_dict(),
               'scores':{m:brier_decomposition(v.y,v[m]) for m in MODELS},'contrasts':{}}
            for name,a,b in [('cal_price_minus_recent','cal_price','recent_rate'),('cal_price_minus_raw','cal_price','raw_price'),
                             ('cal_volume_minus_cal_price','cal_volume','cal_price'),('raw_price_minus_recent','raw_price','recent_rate')]:
                v['difference']=(v[a]-v.y)**2-(v[b]-v.y)**2;yrs=pd.to_datetime(v.issue).dt.year
                s['contrasts'][name]={'n':len(v),'mean':r4.number(v.difference.mean()),'block95':r4.interval90(v,'difference'),
                     'leave_year_out':{str(y):r4.number(v.loc[yrs!=y,'difference'].mean()) for y in sorted(yrs.unique())}}
            out.append(s)
    return out


def policy_summaries(frame):
    f=frame.copy()
    if f.empty:return f,[]
    # Match cash propensity within each issued-quarter cohort. This uses only
    # the observed action frequency, not a searched alternative policy.
    for _,ix in f.loc[f.policy_status=='scored'].groupby(['fit_id','cost_bps','lam','model']).groups.items():
        g=f.loc[ix]
        for col,delta in [('frequency_r','cash_delta_r'),('frequency_u','cash_delta_u')]:
            val,q=frequency_adjust(g.action,g[delta]);f.loc[ix,col]=val
        f.loc[ix,'matched_frequency']=q
    out=[]
    for period,(lo,hi) in PERIODS.items():
        for (lag,cost,lam,model),g in f.groupby(['lag_hours','cost_bps','lam','model']):
            raw=period_frame(g,lo,hi);v=raw.loc[raw.policy_status=='scored'].copy();act=v.loc[v.action==True]
            s={'period':period,'lag_hours':int(lag),'cost_bps':int(cost),'lam':int(lam),'model':model,
               'rows':len(raw),'n':len(v),'statuses':raw.policy_status.value_counts().to_dict(),'cash_actions':len(act),
               'actions_economically_different':int((act.cash_delta_r.abs()>1e-12).sum()),
               'actual_mean_sacrifice_breaches':int((act.cash_delta_r<-.002).sum()),
               'selected_loss_avoided_sum':r4.number(act.loc[act.cash_delta_r>0,'cash_delta_r'].sum()),
               'selected_rebound_forgone_sum':r4.number(-act.loc[act.cash_delta_r<0,'cash_delta_r'].sum()),
               'inc_drawdown_exceed_count':int((v.inc_dd<-.05).sum()),'policy_drawdown_exceed_count':int((v.policy_dd<-.05).sum()),'stats':{}}
            for c in ['gain_r','gain_u','excess_reduction','turnover_delta','frequency_r','frequency_u']:
                s['stats'][c]={'mean':r4.number(v[c].mean()),'median':r4.number(v[c].median()),'block95':r4.interval90(v,c)}
            yrs=pd.to_datetime(v.issue).dt.year
            s['leave_year_out_utility']={str(y):r4.number(v.loc[yrs!=y,'gain_u'].mean()) for y in sorted(yrs.unique())}
            out.append(s)
    return f,out


def main():
    from lib import config
    OUT.mkdir(exist_ok=True)
    if (OUT/'results.json').exists():raise RuntimeError('R7 results already exist; reconcile rather than replay')
    data=Path(config.data_dir());old=OUT.parent/'r6';r=json.loads((old/'results.json').read_text())
    inputs=r['inputs'];gates=r['gates']
    prior={str(p.relative_to(ROOT)):r4.digest(p) for d in ['r1','r2','r3','r4','r5','r6']
           for p in (OUT.parent/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    inherited=dict(r['inherited_sources'])
    inherited.update({k:v for k,v in r['sources'].items() if k!='tests/test_btc_impulse_falsifier.py'})
    names=['research/crypto_science/r7_calibration_study.py','research/CRYPTO_SCIENCE_R7_CALIBRATION_PREREG_2026-09-29.md','tests/test_btc_impulse_falsifier.py']
    sources={n:r4.digest(ROOT/n) for n in names}
    prior_test=subprocess.check_output(['git','show',BASE+':tests/test_btc_impulse_falsifier.py'],cwd=ROOT)
    assert (ROOT/'tests/test_btc_impulse_falsifier.py').read_bytes().startswith(prior_test),'Earlier scientific tests rewritten'
    def unchanged():
        assert all((r4.digest(data/k) if (data/k).exists() else None)==h for k,h in inputs.items()),'input drift'
        assert all(r4.digest(data/k)==h for k,h in gates.items()),'gate drift'
        assert all(r4.digest(ROOT/k)==h for k,h in prior.items()),'prior evidence drift'
        assert all(r4.digest(ROOT/k)==h for k,h in inherited.items()),'inherited source drift'
        assert all(r4.digest(ROOT/k)==h for k,h in sources.items()),'candidate source drift'
    unchanged()
    p=pd.read_csv(old/'predictions.csv');p=p.loc[p.family=='downside'].copy()
    for k in ['anchor','issue','end']:p[k]=pd.to_datetime(p[k])
    oldacc=pd.read_csv(OUT.parent/'r5/policies.csv');oldacc.anchor=pd.to_datetime(oldacc.anchor)
    hourly=pd.read_parquet(data/'coinbase/btc_hourly.parquet')
    base=pd.read_csv(OUT.parent/'r4/incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    accounts=rebuild_accounts(hourly,base,oldacc);accounts.anchor=pd.to_datetime(accounts.anchor)
    ai=accounts.set_index(['anchor','lag_hours','cost_bps']);print('R7 account basis reconstructed and matched to R5',flush=True)
    fits=[];rows=[];policies=[]
    for lag,group in p.groupby('lag_hours'):
        for q in pd.date_range('2018-01-01','2026-07-01',freq='QS'):
            qe=q+pd.offsets.QuarterBegin(startingMonth=1);test=group.loc[(group.issue>=q)&(group.issue<qe)]
            if test.empty:continue
            f=fit_calibrator(group,q);fid=f'{int(lag)}|{q.date()}';tr=group.loc[f['train_indices']];maps={}
            if f['status']=='ok':
                for cost in [0,10,25]:
                    ac=ai.reindex(pd.MultiIndex.from_arrays([tr.anchor,np.full(len(tr),lag),np.full(len(tr),cost)],names=ai.index.names))
                    dr=ac.cash_r.to_numpy()-ac.inc_r.to_numpy();rm=gain_map(tr.y,dr,f['weights'])
                    for lam in [0,1,2]:
                        du=protection_utility(ac.cash_r,ac.cash_dd,lam)-protection_utility(ac.inc_r,ac.inc_dd,lam)
                        maps[f'{cost}|{lam}']={'returns':rm,'utility':gain_map(tr.y,du,f['weights'])}
            fits.append(dict(id=fid,fit_time=str(q),lag_hours=int(lag),calibration=f,mappings=maps))
            for x in test.itertuples():
                status=x.forecast_status if x.forecast_status!='ok' else f['status']
                row={'anchor':x.anchor,'issue':x.issue,'end':x.end,'lag_hours':int(lag),'fit_id':fid,'y':x.y,'calibration_status':status,
                     'r6_rate':x.p0,'raw_price':x.p1,'raw_volume':x.p2,'oot_rate':None,'recent_rate':None,'cal_price':None,'cal_volume':None}
                if status=='ok':
                    row.update(oot_rate=f['oot_rate'],recent_rate=f['recent_rate'],cal_price=float(apply_offset(x.p1,f['price']['offset'])),
                               cal_volume=float(apply_offset(x.p2,f['volume']['offset'])))
                rows.append(r6.finite_record(row))
                if status!='ok':continue
                for cost in [0,10,25]:
                    ac=ai.loc[(x.anchor,lag,cost)]
                    for lam in [0,1,2]:
                        mp=maps[f'{cost}|{lam}']
                        for model in MODELS:
                            action=choose_cash(row[model],mp['utility'],mp['returns'])
                            pr={'anchor':x.anchor,'issue':x.issue,'fit_id':fid,'lag_hours':int(lag),'cost_bps':cost,'lam':lam,'model':model,
                                'probability':row[model],'action':action['action'],'expected_u':action['expected_u'],'expected_r':action['expected_r'],
                                'policy_status':action['status'],'future_label_known':bool(pd.notna(x.y))}
                            if action['status']=='ok' and ac.status!='ok':pr['policy_status']='account_unavailable'
                            elif action['status']=='ok':
                                inc_u=float(protection_utility(ac.inc_r,ac.inc_dd,lam));cash_u=float(protection_utility(ac.cash_r,ac.cash_dd,lam))
                                act=action['action'];rr=ac.cash_r if act else ac.inc_r;dd=ac.cash_dd if act else ac.inc_dd
                                pr.update(policy_status='scored',gain_r=float(rr-ac.inc_r),gain_u=float((cash_u-inc_u) if act else 0.),
                                          cash_delta_r=float(ac.cash_r-ac.inc_r),cash_delta_u=cash_u-inc_u,inc_dd=float(ac.inc_dd),policy_dd=float(dd),
                                          excess_reduction=float(max(-ac.inc_dd-.05,0)-max(-dd-.05,0)),
                                          turnover_delta=float(ac.cash_turnover-ac.inc_turnover) if act else 0.)
                            policies.append(r6.finite_record(pr))
        print(f'R7 completed chronological lag={lag}',flush=True)
    preds=pd.DataFrame(rows);policy=pd.DataFrame(policies)
    forecasts=score_summaries(preds);policy,summaries=policy_summaries(policy)
    unchanged()
    for name,frame in [('predictions',preds),('policies',policy),('accounts',accounts)]:frame.to_csv(OUT/(name+'.csv'),index=False)
    result={'classification':'RETROSPECTIVE_CALIBRATION_PROTECTION_RESEARCH_NOT_LIVE_POLICY','baseline':BASE,'plan_commit':PLAN,
            'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'inputs':inputs,'gates':gates,'prior_evidence':prior,'inherited_sources':inherited,'sources':sources,'unchanged':True,
            'counts':{'quarter_fits':len(fits),'prediction_rows':len(preds),'policy_rows':len(policy),'account_rows':len(accounts)},
            'fits':fits,'forecast_summaries':forecasts,'utility_summaries':summaries,
            'constants':{'half_life_days':365,'min_n':80,'min_class_n':15,'min_effective_n':40,'ridge_offset':.01,
                         'drawdown_allowance':.05,'expected_sacrifice_floor':-.002,'shrink_observations':10},
            'limits':['Calibration reuses earlier out-of-fit retrospective predictions, never in-fit forecasts; not live issuance.',
                      'Intercept-only adjustment preserves within-quarter rank; probability score is not policy value.',
                      'Five-percent allowance and utility penalties are declared research assumptions, not user risk consent.',
                      'Frequency-matched control is retrospective expected random assignment, not executable equal-risk strategy.',
                      'R6 underlying features, costs, missingness and source-time limitations remain; no recovery fit or signed-flow predictor.']}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('R7_COMPLETED',json.dumps(result['counts']),flush=True)


if __name__=='__main__':main()
