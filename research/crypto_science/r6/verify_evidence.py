"""Independent numeric expression of R6 chronology, likelihood and action mapping.
Same-session verification, NOT independent-person scientific review or promotion.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import pandas as pd
from scipy.special import expit
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent;H=pd.Timedelta(hours=1)
COLS=['x_response','x_structure','x_lows','x_return24','x_trend720','x_log_sigma','x_volume']


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def equal(a,b):
    if a is None or pd.isna(a):assert b is None or pd.isna(b),(a,b)
    else:assert np.isclose(a,b,atol=1e-10,rtol=1e-8),(a,b)

def interval(f,col):
    f=f.dropna(subset=[col]);block=((pd.to_datetime(f.anchor)-pd.Timestamp('2016-01-01'))/pd.Timedelta(days=90)).astype(int)
    if f.empty or block.nunique()<2:return None
    domain=np.arange(block.min(),block.max()+1)
    totals=np.array([f.loc[block==b,col].sum() for b in domain]);counts=np.array([(block==b).sum() for b in domain])
    ix=np.random.default_rng(20260928).integers(0,len(domain),(1000,len(domain)))
    den=counts[ix].sum(axis=1);num=totals[ix].sum(axis=1)
    return np.quantile(num[den>0]/den[den>0],[.025,.975])


def main():
    r=json.loads((HERE/'results.json').read_text());data=Path(config.data_dir())
    assert r['plan_commit']=='067f0fb76f7fc20239aa4cdeae03b6cf5b279b85'
    for group in ['sources','inherited_sources','prior_evidence']:
        assert all(sha(ROOT/k)==h for k,h in r[group].items()),group
    assert all((sha(data/k) if (data/k).exists() else None)==h for k,h in r['inputs'].items())
    assert all(sha(data/k)==h for k,h in r['gates'].items())
    features=pd.read_csv(HERE/'features.csv');raw=pd.read_csv(HERE/'labelled_records.csv')
    pred=pd.read_csv(HERE/'predictions.csv');policy=pd.read_csv(HERE/'policies.csv')
    for f in [raw,pred,policy]:
        for c in ['anchor','issue','end']:f[c]=pd.to_datetime(f[c])
    oldevents=pd.read_csv(HERE.parent/'r5/events.csv');oldfeatures=pd.read_csv(HERE.parent/'r5/features.csv')
    oldaccounts=pd.read_csv(HERE.parent/'r5/policies.csv');oldaccounts.anchor=pd.to_datetime(oldaccounts.anchor)
    oldaccounts=oldaccounts.set_index(['family','anchor','lag_hours','cost_bps'])
    h=pd.read_parquet(data/'coinbase/btc_hourly.parquet')
    assert len(raw)==len(oldevents)==1294 and len(features)==647
    for c in ['family','anchor','issue','entry','end','lag_hours','outcome']:
        if c in ['anchor','issue','entry','end']:
            assert pd.to_datetime(raw[c]).equals(pd.to_datetime(oldevents[c])),c
        else:assert raw[c].equals(oldevents[c]),c
    def window(idx):
        w=h.reindex(idx)[['open','high','low','close']];a=w.to_numpy(float)
        good=np.isfinite(a).all() and (a>0).all() and (a[:,1]>=a.max(axis=1)).all() and (a[:,2]<=a.min(axis=1)).all()
        return w if good else None
    feature_count=0
    for item in features.itertuples():
        if item.status=='no_candidate':continue
        s=pd.Timestamp(item.issue)-H;a=pd.Timestamp(item.anchor);down=item.family=='downside'
        long=window(pd.date_range(s-720*H,periods=721,freq='h'))
        pe=a-H if down else s-3*H;prior=window(pd.date_range(pe-72*H,periods=73,freq='h'))
        si=pd.date_range(a-72*H,periods=72,freq='h') if down else pd.date_range(s-6*H,periods=6,freq='h')
        structural=window(si)
        if long is None or prior is None or structural is None:
            assert item.status=='price_unknown';continue
        vol=np.std(np.diff(np.log(prior.close.to_numpy())),ddof=1)
        if not np.isfinite(vol) or vol<=0:assert item.status=='price_unknown';continue
        last=long.close.iloc[-1];reference=h.close.loc[a if down else s-6*H]
        level=structural.low.min() if down else structural.high.max()
        expected=[np.log(last/reference)/(vol*np.sqrt(6)),np.log(last/level)/(vol*np.sqrt(6)),
          np.log(long.low.iloc[-3:].min()/long.low.iloc[-6:-3].min())/(vol*np.sqrt(3)),
          np.log(last/long.close.iloc[-25])/(vol*np.sqrt(24)),np.log(last/long.close.iloc[0])/(vol*np.sqrt(720)),np.log(vol)]
        assert np.allclose(expected,[getattr(item,c) for c in COLS[:-1]],atol=1e-10)
        active=pd.date_range(a+H,periods=6,freq='h') if down else pd.date_range(s-2*H,periods=3,freq='h')
        ri=pd.date_range(a-72*H,periods=72,freq='h') if down else pd.date_range(s-74*H,periods=72,freq='h')
        va=h.volume.reindex(active).to_numpy();vr=h.volume.reindex(ri).to_numpy()
        if np.isfinite(va).all() and np.isfinite(vr).all() and (va>=0).all() and (vr>=0).all() and np.median(vr)>0:
            equal(np.log1p(np.mean(va)/np.median(vr)),item.x_volume);assert item.status=='ok'
        else:assert pd.isna(item.x_volume) and item.status=='volume_unknown'
        feature_count+=1
    fits={x['id']:x for x in r['fits']};checked=0
    for key,fit in fits.items():
        qt=pd.Timestamp(fit['fit_time']);fam=fit['family'];lag=fit['lag_hours']
        subset=raw.loc[(raw.family==fam)&(raw.lag_hours==lag)]
        mask=np.isfinite(subset[COLS+['y']].to_numpy(float)).all(axis=1)&subset.y.isin([0,1])
        mask &=(subset.issue<qt)&(subset.end+fit['embargo_hours']*H<qt)
        train=subset.loc[mask]
        assert train.index.tolist()==fit['m1']['train_indices']==fit['m2']['train_indices']
        for label,columns in [('m1',COLS[:-1]),('m2',COLS)]:
            model=fit[label];y=train.y.to_numpy(float)
            assert model['n']==len(train) and model['positives']==int(y.sum())
            equal((y.sum()+1)/(len(y)+2),model['prevalence'])
            if len(train)<80 or min(y.sum(),len(y)-y.sum())<15:
                assert model['status']=='insufficient_training';continue
            if model['status']!='ok':assert model['status']=='optimizer_failed';continue
            x=train[columns].to_numpy(float);mu=x.mean(axis=0);sd=x.std(axis=0);sd=np.where(sd>1e-12,sd,1.)
            assert np.allclose(mu,model['mean']) and np.allclose(sd,model['scale'])
            z=np.clip((x-mu)/sd,-5,5);coef=np.array(model['coef']);p=expit(coef[0]+z@coef[1:])
            grad=np.r_[np.mean(p-y),z.T@(p-y)/len(y)+.05*coef[1:]]
            assert np.max(np.abs(grad))<1e-5,(key,grad)
            objective=np.mean(np.logaddexp(0,coef[0]+z@coef[1:])-y*(coef[0]+z@coef[1:]))+.025*np.dot(coef[1:],coef[1:])
            equal(objective,model['objective']);checked+=1
        for cost in [0,10,25]:
            ys=[];ds=[]
            for row in train.itertuples():
                acc=oldaccounts.loc[(fam,row.anchor,lag,cost)]
                delta=(acc.delayed_return-acc.incumbent_return if fam=='downside' else acc.price_return-acc.incumbent_return)
                if pd.notna(delta):ys.append(row.y);ds.append(delta)
            ys=np.array(ys);ds=np.array(ds);m=fit['payoffs'][str(cost)]
            n0=int((ys==0).sum());n1=int((ys==1).sum())
            if min(n0,n1)<15:assert m is None;continue
            assert m['n0']==n0 and m['n1']==n1
            equal((ds[ys==0].sum()+10*ds.mean())/(n0+10),m['mu0']);equal((ds[ys==1].sum()+10*ds.mean())/(n1+10),m['mu1'])
    assert not pred.duplicated(['family','anchor','lag_hours']).any()
    rawindex=raw.set_index(['family','anchor','lag_hours'])
    for row in pred.itertuples():
        fit=fits[row.fit_id];qt=pd.Timestamp(fit['fit_time']);assert qt<=row.issue<qt+pd.DateOffset(months=3)
        f=rawindex.loc[(row.family,row.anchor,row.lag_hours)]
        equal(f.y,row.y)
        if row.forecast_status!='ok':assert pd.isna(row.p1) and pd.isna(row.p2);continue
        equal(row.p0,fit['m1']['prevalence'])
        for label,col,columns in [('m1','p1',COLS[:-1]),('m2','p2',COLS)]:
            model=fit[label];z=np.clip((f[columns].to_numpy(float)-model['mean'])/model['scale'],-5,5)
            equal(expit(model['coef'][0]+z@np.array(model['coef'][1:])),getattr(row,col))
    for row in policy.itertuples():
        if row.policy_status!='scored':continue
        m=fits[row.fit_id]['payoffs'][str(row.cost_bps)];e=row.probability*m['mu1']+(1-row.probability)*m['mu0']
        equal(e,row.expected_gain);assert row.cash_action==bool(e>0)
        a=oldaccounts.loc[(row.family,row.anchor,row.lag_hours,row.cost_bps)];delta=a.delayed_return-a.incumbent_return
        equal(delta,row.actual_cash_gain);ret=a.delayed_return if row.cash_action else a.incumbent_return
        equal(ret-a.incumbent_return,row.marginal_gain);equal(ret-a.price_return,row.model_minus_price);equal(ret-a.volume_return,row.model_minus_volume)
    periods={'all_issued':('2018-01-01','2027-01-01'),'2018_2019':('2018-01-01','2020-01-01'),
             '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}
    for s in r['forecast_summaries']:
        lo,hi=periods[s['period']];f=pred.loc[(pred.family==s['family'])&(pred.lag_hours==s['lag_hours'])&(pred.issue>=lo)&(pred.issue<hi)]
        assert len(f)==s['candidate_rows'] and f.forecast_status.value_counts().to_dict()==s['status_counts']
        good=f.dropna(subset=['y','p0','p1','p2']).copy()
        for m,stats in s['scores'].items():
            assert len(good)==stats['n']
            if good.empty:continue
            y=good.y.to_numpy();p=good[m].to_numpy();q=np.clip(p,1e-12,1-1e-12)
            equal(np.mean((p-y)**2),stats['brier']);equal(-np.mean(y*np.log(q)+(1-y)*np.log(1-q)),stats['log_loss'])
            equal(p.mean(),stats['mean_probability']);equal(y.mean(),stats['event_fraction']);assert int(y.sum())==stats['positive']
            positives=p[y==1];negatives=p[y==0]
            auc=(np.greater(positives[:,None],negatives[None,:]).sum()+.5*np.equal(positives[:,None],negatives[None,:]).sum())/(len(positives)*len(negatives)) if len(positives) and len(negatives) else None
            equal(auc,stats['auc'])
            for b in stats['reliability']:
                mask=(p>=b['low'])&((p<b['high']) if b['high']<1 else (p<=1))
                assert int(mask.sum())==b['n']
                equal(p[mask].mean() if mask.any() else None,b['mean_probability']);equal(y[mask].mean() if mask.any() else None,b['event_fraction'])
        for c,a,b in [('brier_m1_minus_m0','p1','p0'),('brier_m2_minus_m1','p2','p1')]:
            good[c]=(good[a]-good.y)**2-(good[b]-good.y)**2
            equal(good[c].mean(),s[c]['mean']);ci=interval(good,c)
            if ci is None:assert s[c]['block95'] is None
            else:assert np.allclose(ci,s[c]['block95'],atol=1e-10)
    for s in r['utility_summaries']:
        lo,hi=periods[s['period']];f=policy.loc[(policy.family==s['family'])&(policy.lag_hours==s['lag_hours'])&(policy.cost_bps==s['cost_bps'])&(policy.model==s['model'])&(policy.issue>=lo)&(policy.issue<hi)]
        assert len(f)==s['rows'] and f.policy_status.value_counts().to_dict()==s['status_counts']
        good=f.loc[f.policy_status=='scored'];assert len(good)==s['n'] and int(good.cash_action.sum())==s['cash_actions']
        for c in ['marginal_gain','model_minus_price','model_minus_volume','expected_gain']:
            equal(good[c].mean(),s[c]['mean']);equal(good[c].median(),s[c]['median']);ci=interval(good,c)
            if ci is None:assert s[c]['block95'] is None
            else:assert np.allclose(ci,s[c]['block95'],atol=1e-10)
        acts=good.loc[good.cash_action==True];assert int((acts.actual_cash_gain>0).sum())==s['cash_positive']
        assert int((acts.actual_cash_gain<0).sum())==s['cash_negative'];equal(acts.actual_cash_gain.sum(),s['cash_gain_sum'])
        yr=good.issue.dt.year
        for year,value in s['leave_one_year_out_gain'].items():equal(good.loc[yr!=int(year),'marginal_gain'].mean(),value)
    assert not any(x['m1']['status']=='ok' for x in r['fits'] if x['family']=='recovery')
    assert r['flow_qualification']['status']=='EXCLUDED_FROM_FORECASTS'
    assert all('taker' not in c and 'flow' not in c for c in COLS)
    print(f'R6_VERIFIED: {feature_count} valid-price continuous feature records; {len(fits)} quarter fits ({checked} fitted likelihoods); {len(pred)} predictions; {len(policy)} policy rows.')
    print(f'All forecast scores/reliability bins/Brier intervals and {len(r["utility_summaries"])} action summary cells independently recomputed. Future cutoff and inherited hash fences hold.')
    print('Same-session independent arithmetic; not independent researcher review or live calibration.')


if __name__=='__main__':main()
