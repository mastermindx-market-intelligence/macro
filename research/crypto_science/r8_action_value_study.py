"""R8 preregistered timing/action-value study; no live model or gate writes."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.crypto_science import r4_sequence_study as r4, r5_participation_study as r5, r6_probability_study as r6
H=pd.Timedelta(hours=1)
BASE='4409729ed99f62e0f2127798ffc234953fb8f0e9'
PLAN='89b6876ba0937691270b7b042427ea6fc4c2e042'
OUT=Path(__file__).with_name('r8')
FIELDS=['x_return1','x_return6','x_return24','x_trend720','x_structure','x_lows','x_log_sigma','x_exposure']
PERIODS={'full':('2016-01-01','2027-01-01'),'2016_2019':('2016-01-01','2020-01-01'),
         '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}


def features_at(frame,anchor,landmark,exposure):
    r5.checked_index(frame)
    if landmark not in (0,6):raise ValueError('Unregistered landmark')
    a=pd.Timestamp(anchor);s=a+landmark*H
    out=dict(issue=s+H,status='price_unknown',return24=None,**{k:None for k in FIELDS})
    w=r5.prices(frame,pd.date_range(s-720*H,periods=721,freq='h'))
    if w is None:return out
    if not np.isfinite(exposure) or not 0<=exposure<=1:
        out['status']='exposure_unknown';return out
    prior=w.close.iloc[-74:-1].to_numpy();sigma=float(np.std(np.diff(np.log(prior)),ddof=1))
    if not np.isfinite(sigma) or sigma<=0:return out
    c=float(w.close.iloc[-1]);r=[]
    for lag in (1,6,24,720):r.append(float(np.log(c/w.close.iloc[-lag-1])/(sigma*np.sqrt(lag))))
    level=float(w.low.iloc[-73:-1].min());last=w.low.iloc[-6:]
    r.extend([float(np.log(c/level)/(sigma*np.sqrt(6))),float(np.log(last.iloc[-3:].min()/last.iloc[:3].min())/(sigma*np.sqrt(3))),float(np.log(sigma)),float(exposure)])
    out.update(zip(FIELDS,r));out.update(status='ok',return24=c/float(w.close.iloc[-25])-1)
    return out


def trace_account(prices,targets,initial,terminal,bps,action_step):
    p=np.asarray(prices,float);t=np.asarray(targets,float)
    if len(p)<2 or len(t)!=len(p)-1 or not 0<=action_step<len(t) or not np.isfinite(p).all() or (p<=0).any() or not np.isfinite(t).all() or (t<0).any() or (t>1).any() or not(0<=initial<=1 and 0<=terminal<=1 and 0<=bps<10000):
        raise ValueError('Invalid account path')
    wealth=1.;weight=float(initial);last=float(initial);turn=0.;high=1.;dd=0.;pre={};fee=bps/10000.
    for k,target in enumerate(t):
        if k==action_step:pre={'pre_return':wealth-1,'pre_drawdown':dd,'action_weight':weight,'pre_highwater':high}
        if target!=last:
            change=abs(target-weight);wealth*=1-fee*change;turn+=change;dd=min(dd,wealth/high-1);weight=float(target);last=float(target)
        ret=p[k+1]/p[k]-1;factor=1+weight*ret;wealth*=factor;weight=weight*(1+ret)/factor
        high=max(high,wealth);dd=min(dd,wealth/high-1)
    change=abs(terminal-weight);wealth*=1-fee*change;turn+=change;dd=min(dd,wealth/high-1)
    return dict(wealth=wealth,**{'return':wealth-1},max_drawdown=dd,turnover=turn,**pre)


def fit_ridge(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    if x.ndim!=2 or y.shape!=(len(x),2) or not len(x) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Invalid multioutput fit sample')
    mean=x.mean(axis=0);scale=x.std(axis=0);scale=np.where(scale>1e-12,scale,1.)
    z=np.c_[np.ones(len(x)),np.clip((x-mean)/scale,-5,5)];pen=np.diag(np.r_[0.,np.full(x.shape[1],.05)])
    lhs=z.T@z/len(x)+pen;rhs=z.T@y/len(x);beta=np.linalg.solve(lhs,rhs)
    residue=float(np.max(np.abs(lhs@beta-rhs)))
    return {'status':'ok','mean':mean.tolist(),'scale':scale.tolist(),'coef':beta.tolist(),
            'target_mean':y.mean(axis=0).tolist(),'normal_residual':residue,
            'objective':np.mean((z@beta-y)**2,axis=0).tolist(),'penalty':.05}


def predict_value(model,x):
    a=np.asarray(x,float)
    if model['status']!='ok' or a.ndim!=2 or not np.isfinite(a).all():raise ValueError('Unknown value predictor')
    z=np.c_[np.ones(len(a)),np.clip((a-np.array(model['mean']))/np.array(model['scale']),-5,5)]
    return z@np.array(model['coef'])


def value_snapshot(frame,cutoff):
    q=pd.Timestamp(cutoff);num=frame[FIELDS+['dr','dx']].apply(pd.to_numeric,errors='coerce')
    ok=(pd.to_datetime(frame.issue)<q)&(pd.to_datetime(frame.end)+24*H<q)&np.isfinite(num).all(axis=1)
    t=frame.loc[ok];n=len(t);pos=int((t.dr>1e-12).sum());neg=int((t.dr< -1e-12).sum())
    out={'status':'insufficient_training','n':n,'positive_gain':pos,'negative_gain':neg,'train_indices':list(map(int,t.index)),
         'last_train_end':str(pd.to_datetime(t.end).max()) if n else None}
    if n<80 or min(pos,neg)<15:return out
    out.update(fit_ridge(t[FIELDS].to_numpy(),t[['dr','dx']].to_numpy()));return out


def action_from_value(dr,dx,lam):
    if lam not in (0,1,2) or not np.isfinite([dr,dx]).all():raise ValueError('Invalid value inputs')
    u=float(dr+lam*dx)
    return {'action':bool(u>0 and dr>=-.002),'expected_u':u,'expected_r':float(dr)}


def hindsight_value(delta):
    return np.maximum(np.asarray(delta,float),0)


def period_rows(f,lo,hi):
    return f.loc[(pd.to_datetime(f.anchor)>=pd.Timestamp(lo))&(pd.to_datetime(f.anchor)<pd.Timestamp(hi))].copy()


def stat(f,key):
    v=pd.to_numeric(f[key],errors='coerce').dropna()
    return {'n':len(v),'mean':r4.number(v.mean()),'median':r4.number(v.median()),'block95':r4.interval90(f,key)}


def opportunity_summaries(accounts):
    summaries=[];paired=[]
    for period,(lo,hi) in PERIODS.items():
        for (lag,cost,k),g in accounts.groupby(['lag_hours','cost_bps','landmark']):
            raw=period_rows(g,lo,hi);v=raw.loc[raw.account_status=='ok'].copy()
            row={'period':period,'lag_hours':int(lag),'cost_bps':cost,'landmark':int(k),'n_parents':len(raw),'n':len(v),
                 'status_counts':raw.account_status.value_counts().to_dict(),'pre_tail':int((v.pre_drawdown<-.05).sum()),
                 'inc_tail':int((v.inc_dd<-.05).sum()),'cash_tail':int((v.cash_dd<-.05).sum()),
                 'action_weight_zero':int((v.action_weight.abs()<1e-12).sum()),'initial_target_zero':int((v.initial_target.abs()<1e-12).sum()),
                 'cash_gain_positive':int((v.dr>1e-12).sum()),'cash_gain_negative':int((v.dr< -1e-12).sum()),'stats':{}}
            for col in ['dr','dx','pre_return','pre_drawdown','action_weight','pre_highwater','price_return24','post_price_worst','post_price_best']:
                row['stats'][col]=stat(v,col)
            for lam in (0,1,2):
                v['u']=v.dr+lam*v.dx;v['oracle']=hindsight_value(v.u)
                row['stats'][f'du_{lam}']=stat(v,'u');row['stats'][f'hindsight_{lam}']=stat(v,'oracle')
            summaries.append(row)
        for (lag,cost),g in accounts.groupby(['lag_hours','cost_bps']):
            f=period_rows(g,lo,hi);e=f.loc[(f.landmark==0)&(f.account_status=='ok')].set_index('anchor')
            l=f.loc[(f.landmark==6)&(f.account_status=='ok')].set_index('anchor');ix=e.index.intersection(l.index);e=e.loc[ix];l=l.loc[ix]
            for lam in (0,1,2):
                v=pd.DataFrame({'anchor':ix,'difference':(e.dr+lam*e.dx-l.dr-lam*l.dx).to_numpy(),
                               'oracle_difference':(np.maximum(e.dr+lam*e.dx,0)-np.maximum(l.dr+lam*l.dx,0)).to_numpy()})
                paired.append({'period':period,'lag_hours':int(lag),'cost_bps':int(cost),'lam':lam,'n':len(v),
                               'early_minus_late_cash':stat(v,'difference'),'early_minus_late_hindsight':stat(v,'oracle_difference')})
    return summaries,paired


def model_summaries(preds,policies):
    scores=[];summaries=[];timing=[];f=policies.copy()
    if f.empty:return f,scores,summaries,timing
    # Same-quarter frequency control is descriptive, not live assignment.
    for _,ix in f.loc[f.policy_status=='scored'].groupby(['fit_id','model','lam']).groups.items():
        g=f.loc[ix];q=float(g.action.mean());f.loc[ix,'quarter_frequency']=q
        f.loc[ix,'frequency_r']=(g.action.astype(float)-q)*g.dr
        f.loc[ix,'frequency_u']=(g.action.astype(float)-q)*(g.dr+g.lam*g.dx)
    for period,(lo,hi) in PERIODS.items():
        for (k,lag,cost),g in preds.groupby(['landmark','lag_hours','cost_bps']):
            raw=period_rows(g,lo,hi);v=raw.loc[raw.prediction_status=='ok'].dropna(subset=['dr','dx']).copy()
            row={'period':period,'landmark':int(k),'lag_hours':int(lag),'cost_bps':int(cost),'rows':len(raw),'n':len(v),
                 'status_counts':raw.prediction_status.value_counts().to_dict(),'scores':{}}
            for target in ['dr','dx']:
                for model in ['mean','ridge']:
                    err=v[f'{model}_{target}']-v[target]
                    row['scores'][f'{model}_{target}']={'mse':r4.number((err**2).mean()),'mae':r4.number(err.abs().mean()),
                         'bias':r4.number(err.mean()),'mean_prediction':r4.number(v[f'{model}_{target}'].mean()),'mean_observed':r4.number(v[target].mean())}
            scores.append(row)
        for (k,lag,cost,lam,model),g in f.groupby(['landmark','lag_hours','cost_bps','lam','model']):
            raw=period_rows(g,lo,hi);v=raw.loc[raw.policy_status=='scored'].copy();acts=v.loc[v.action==True]
            row={'period':period,'landmark':int(k),'lag_hours':int(lag),'cost_bps':int(cost),'lam':int(lam),'model':model,
                 'rows':len(raw),'n':len(v),'status_counts':raw.policy_status.value_counts().to_dict(),'actions':len(acts),
                 'economically_different':int((acts.dr.abs()>1e-12).sum()),'inc_tail':int((v.inc_dd<-.05).sum()),'policy_tail':int((v.policy_dd<-.05).sum()),
                 'avoided_loss_sum':float(acts.loc[acts.dr>0,'dr'].sum()),'missed_rebound_sum':float(-acts.loc[acts.dr<0,'dr'].sum()),
                 'stats':{c:stat(v,c) for c in ['gain_r','gain_u','excess_reduction','turnover_delta','frequency_r','frequency_u']}}
            years=pd.to_datetime(v.anchor).dt.year
            row['leave_year_out_u']={str(y):r4.number(v.loc[years!=y,'gain_u'].mean()) for y in sorted(years.unique())}
            summaries.append(row)
        for (lag,cost,lam,model),g in f.groupby(['lag_hours','cost_bps','lam','model']):
            v=period_rows(g,lo,hi);e=v.loc[(v.landmark==0)&(v.policy_status=='scored')].set_index('anchor')
            l=v.loc[(v.landmark==6)&(v.policy_status=='scored')].set_index('anchor');ix=e.index.intersection(l.index);e=e.loc[ix];l=l.loc[ix]
            paired=pd.DataFrame({'anchor':ix,'difference_r':(e.gain_r-l.gain_r).to_numpy(),'difference_u':(e.gain_u-l.gain_u).to_numpy()})
            timing.append({'period':period,'lag_hours':int(lag),'cost_bps':int(cost),'lam':int(lam),'model':model,'n':len(paired),
                           'early_n':len(e),'early_actions':int(e.action.sum()),'late_actions':int(l.action.sum()),
                           'early_minus_late_r':stat(paired,'difference_r'),'early_minus_late_u':stat(paired,'difference_u')})
    return f,scores,summaries,timing


def main():
    from lib import config
    OUT.mkdir(exist_ok=True)
    if (OUT/'results.json').exists():raise RuntimeError('R8 results exist; reconcile instead of replaying')
    data=Path(config.data_dir());r7=json.loads((OUT.parent/'r7/results.json').read_text())
    inputs=r7['inputs'];gates=r7['gates'];inherited=dict(r7['inherited_sources'])
    inherited.update({k:v for k,v in r7['sources'].items() if k!='tests/test_btc_impulse_falsifier.py'})
    prior={str(p.relative_to(ROOT)):r4.digest(p) for d in ['r1','r2','r3','r4','r5','r6','r7'] for p in (OUT.parent/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    names=['research/crypto_science/r8_action_value_study.py','research/CRYPTO_SCIENCE_R8_ACTION_VALUE_PREREG_2026-09-29.md','tests/test_btc_impulse_falsifier.py']
    sources={k:r4.digest(ROOT/k) for k in names}
    assert (ROOT/names[-1]).read_bytes().startswith(subprocess.check_output(['git','show',BASE+':'+names[-1]],cwd=ROOT))
    def unchanged():
        assert all((r4.digest(data/k) if (data/k).exists() else None)==h for k,h in inputs.items()),'input drift'
        assert all(r4.digest(data/k)==h for k,h in gates.items()),'gate drift'
        for group in [inherited,prior,sources]:assert all(r4.digest(ROOT/k)==h for k,h in group.items()),'source/evidence drift'
    unchanged()
    hourly=pd.read_parquet(data/'coinbase/btc_hourly.parquet');r5.checked_index(hourly)
    base=pd.read_csv(OUT.parent/'r4/incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    saved=pd.read_csv(OUT.parent/'r4/downside_events.csv');anchors=pd.DatetimeIndex(pd.to_datetime(saved.loc[saved.rule=='d0','anchor'].unique())).sort_values()
    assert r4.onsets(r4.hourly_conditions(hourly).d0,step='1h',separation='24h').equals(anchors)
    index=pd.date_range(hourly.index[0],hourly.index[-1],freq='h');maps={lag:r4.incumbent_targets(base,index,delay_hours=lag) for lag in [1,6]}
    old=pd.read_csv(OUT.parent/'r7/accounts.csv');old.anchor=pd.to_datetime(old.anchor);old=old.set_index(['anchor','lag_hours','cost_bps'])
    rows=[]
    for a in anchors:
        for lag in [1,6]:
            origin=a+(1+lag)*H;end=origin+24*H;w=r4.complete_window(hourly,origin,24);ix=pd.date_range(origin,end,freq='h');t=maps[lag].reindex(ix)
            account_ok=w is not None and t.notna().all()
            for k in [0,6]:
                issue=a+(1+k)*H;act=issue+lag*H;feat=features_at(hourly,a,k,maps[lag].get(issue,np.nan))
                for cost in [0,10,25]:
                    row={'anchor':a,'origin':origin,'issue':issue,'action_time':act,'end':end,'landmark':k,'lag_hours':lag,'cost_bps':cost,
                         'feature_status':feat['status'],'account_status':'ok' if account_ok else 'account_unavailable',
                         **{x:feat[x] for x in FIELDS}}
                    if account_ok:
                        cash=t.iloc[:-1].copy();cash.loc[cash.index>=act]=0.
                        inc=trace_account(w.open,t.iloc[:-1],float(t.iloc[0]),float(t.iloc[-1]),cost,k)
                        late=trace_account(w.open,cash,float(t.iloc[0]),float(t.iloc[-1]),cost,k)
                        for name in ['pre_return','pre_drawdown','action_weight','pre_highwater']:assert np.isclose(inc[name],late[name],atol=1e-12)
                        prev=old.loc[(a,lag,cost)]
                        assert np.isclose(inc['return'],prev.inc_r,atol=1e-12)
                        if k==6:
                            assert np.isclose(late['return'],prev.cash_r,atol=1e-12)
                            assert np.isclose(late['max_drawdown'],prev.cash_dd,atol=1e-12)
                        p=w.open.loc[act:];recent=r5.prices(hourly,pd.date_range(issue-25*H,periods=25,freq='h'))
                        row.update(inc_r=inc['return'],cash_r=late['return'],inc_dd=inc['max_drawdown'],cash_dd=late['max_drawdown'],
                                   inc_turnover=inc['turnover'],cash_turnover=late['turnover'],initial_target=float(t.iloc[0]),
                                   dr=late['return']-inc['return'],dx=max(-inc['max_drawdown']-.05,0)-max(-late['max_drawdown']-.05,0),
                                   post_price_worst=float(p.min()/p.iloc[0]-1),post_price_best=float(p.max()/p.iloc[0]-1),
                                   price_return24=float(recent.close.iloc[-1]/recent.close.iloc[0]-1) if recent is not None else None,
                                   **{x:inc[x] for x in ['pre_return','pre_drawdown','action_weight','pre_highwater']})
                    rows.append(r6.finite_record(row))
    accounts=pd.DataFrame(rows)
    for k in ['anchor','issue','end']:accounts[k]=pd.to_datetime(accounts[k])
    anatomy,paired=opportunity_summaries(accounts);print('R8 anatomy complete; same parent identities and old account values match',flush=True)
    fits=[];preds=[];policies=[]
    for (k,lag,cost),g in accounts.groupby(['landmark','lag_hours','cost_bps']):
        for q in pd.date_range('2018-01-01','2026-07-01',freq='QS'):
            qe=q+pd.offsets.QuarterBegin(startingMonth=1);test=g.loc[(g.issue>=q)&(g.issue<qe)]
            if test.empty:continue
            model=value_snapshot(g,q);fid=f'{int(k)}|{int(lag)}|{int(cost)}|{q.date()}'
            fits.append({'id':fid,'landmark':int(k),'lag_hours':int(lag),'cost_bps':int(cost),'time':str(q),'fit':model})
            for x in test.itertuples():
                status=x.feature_status if x.feature_status!='ok' else model['status']
                row={'anchor':x.anchor,'issue':x.issue,'end':x.end,'landmark':int(k),'lag_hours':int(lag),'cost_bps':int(cost),'fit_id':fid,
                     'prediction_status':status,'account_status':x.account_status,'dr':x.dr,'dx':x.dx,
                     'mean_dr':None,'mean_dx':None,'ridge_dr':None,'ridge_dx':None}
                if status=='ok':
                    z=predict_value(model,[[getattr(x,c) for c in FIELDS]])[0]
                    row.update(mean_dr=model['target_mean'][0],mean_dx=model['target_mean'][1],ridge_dr=float(z[0]),ridge_dx=float(z[1]))
                preds.append(r6.finite_record(row))
                if status!='ok':continue
                for kind in ['mean','ridge']:
                    for lam in [0,1,2]:
                        choice=action_from_value(row[kind+'_dr'],row[kind+'_dx'],lam)
                        pr={'anchor':x.anchor,'issue':x.issue,'landmark':int(k),'lag_hours':int(lag),'cost_bps':int(cost),'lam':lam,
                            'model':kind,'fit_id':fid,**choice,'expected_dx':row[kind+'_dx'],'policy_status':x.account_status}
                        if x.account_status=='ok':
                            action=choice['action'];dd=x.cash_dd if action else x.inc_dd
                            pr.update(policy_status='scored',dr=x.dr,dx=x.dx,gain_r=float(x.dr) if action else 0.,
                                      gain_u=float(x.dr+lam*x.dx) if action else 0.,inc_dd=x.inc_dd,policy_dd=dd,
                                      excess_reduction=x.dx if action else 0.,turnover_delta=(x.cash_turnover-x.inc_turnover) if action else 0.)
                        policies.append(r6.finite_record(pr))
        print('R8 fits complete',int(k),int(lag),int(cost),flush=True)
    predictions=pd.DataFrame(preds);policies=pd.DataFrame(policies)
    policies,score,util,timing=model_summaries(predictions,policies)
    unchanged()
    for name,f in [('accounts',accounts),('predictions',predictions),('policies',policies)]:f.to_csv(OUT/(name+'.csv'),index=False)
    result={'classification':'RETROSPECTIVE_ACTION_VALUE_RESEARCH_NOT_LIVE_STRATEGY','baseline':BASE,'plan_commit':PLAN,
            'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'inputs':inputs,'gates':gates,'inherited_sources':inherited,'prior_evidence':prior,'sources':sources,'hashes_unchanged':True,
            'counts':{'parents':len(anchors),'accounts':len(accounts),'fits':len(fits),'prediction_rows':len(predictions),'policy_rows':len(policies)},
            'opportunity_summaries':anatomy,'cash_timing':paired,'fits':fits,'score_summaries':score,'utility_summaries':util,'model_timing':timing,
            'limits':['Same original breakdown parents; k0 is earlier than k6 but is not pre-shock detection.',
                      'Counterfactual cash-or-incumbent maximum is hindsight, not achievable forecasting.',
                      'Known target at issue is a feature; future drifted action exposure is diagnostic only.',
                      'Direct marginal return/drawdown estimates are not crash probabilities or user-approved sizing.',
                      'Historical source timing, hourly-open fill/mark limitations and prior-used holdouts remain.',
                      'No signed-flow/recovery learner, production mutation or promotion.']}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('R8_COMPLETE',json.dumps(result['counts']),flush=True)


if __name__=='__main__':main()
