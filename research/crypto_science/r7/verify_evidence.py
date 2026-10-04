"""Independent numerical expression of R7 evidence; same session, not review."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import pandas as pd
from scipy.special import expit,logit
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent
H=pd.Timedelta(hours=1)
BINS=np.array([0,.1,.2,.3,.5,.75,1.])
MODELS=['r6_rate','raw_price','raw_volume','oot_rate','recent_rate','cal_price','cal_volume']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def eq(a,b):
    if a is None or pd.isna(a):assert b is None or pd.isna(b),(a,b)
    else:assert np.isclose(a,b,atol=1e-10,rtol=1e-8),(a,b)

def inventory(prices,targets,initial,terminal,bps):
    cash=1-initial;coins=initial/prices[0];last=initial;marks=[1.];turn=0.;fee=bps/10000.
    for price,target in zip(prices[:-1],targets):
        wealth=cash+coins*price;marks.append(wealth)
        if target!=last:
            amount=abs(target-coins*price/wealth);wealth*=1-fee*amount;turn+=amount
            coins=wealth*target/price;cash=wealth*(1-target);last=target;marks.append(wealth)
    wealth=cash+coins*prices[-1];marks.append(wealth)
    amount=abs(terminal-coins*prices[-1]/wealth);wealth*=1-fee*amount;turn+=amount;marks.append(wealth)
    marks=np.array(marks);dd=np.min(marks/np.maximum.accumulate(marks)-1)
    return wealth-1,dd,turn

def mixture_map(y,g,w):
    ok=np.isin(y,[0,1])&np.isfinite(g)&np.isfinite(w)&(w>0);y=y[ok];g=g[ok];w=w[ok]
    if min(sum(y==0),sum(y==1))<15:return None
    allmean=sum(w*g)/sum(w)
    return {'n':len(y),'n0':int(sum(y==0)),'n1':int(sum(y==1)),'mean':allmean,
            'mu0':(sum((w*g)[y==0])+10*allmean)/(sum(w[y==0])+10),
            'mu1':(sum((w*g)[y==1])+10*allmean)/(sum(w[y==1])+10)}

def interval(frame,column):
    f=frame.dropna(subset=[column]);v=f[column].to_numpy()
    if f.empty:return None
    ix=((pd.to_datetime(f.anchor)-pd.Timestamp('2016-01-01'))/pd.Timedelta(days=90)).astype(int)
    if ix.nunique()<2:return None
    domain=np.arange(ix.min(),ix.max()+1)
    sums=np.array([v[ix==k].sum() for k in domain]);n=np.array([(ix==k).sum() for k in domain])
    d=np.random.default_rng(20260928).integers(0,len(domain),(1000,len(domain)))
    den=n[d].sum(axis=1);means=sums[d].sum(axis=1)[den>0]/den[den>0]
    return np.quantile(means,[.025,.975]).tolist()

def main():
    r=json.loads((HERE/'results.json').read_text());data=Path(config.data_dir())
    assert r['plan_commit']=='2e8709464b643a33a5bca53b53999f53ad4756f5'
    for key in ['prior_evidence','inherited_sources','sources']:
        assert all(sha(ROOT/p)==h for p,h in r[key].items()),key
    assert all((sha(data/p) if (data/p).exists() else None)==h for p,h in r['inputs'].items())
    assert all(sha(data/p)==h for p,h in r['gates'].items())
    accounts=pd.read_csv(HERE/'accounts.csv');accounts.anchor=pd.to_datetime(accounts.anchor)
    preds=pd.read_csv(HERE/'predictions.csv');policy=pd.read_csv(HERE/'policies.csv')
    old=pd.read_csv(HERE.parent/'r6/predictions.csv');old=old.loc[old.family=='downside'].copy()
    for f in [old,preds,policy]:
        for c in ['issue','anchor']:f[c]=pd.to_datetime(f[c])
    old.end=pd.to_datetime(old.end)
    hourly=pd.read_parquet(data/'coinbase/btc_hourly.parquet')
    base=pd.read_csv(HERE.parent/'r4/incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    count=0
    for x in accounts.itertuples():
        if x.status!='ok':continue
        ix=pd.date_range(x.origin,x.end,freq='h');prices=hourly.open.reindex(ix).to_numpy(float)
        available=base.index+pd.Timedelta(hours=24+x.lag_hours);where=available.searchsorted(ix,side='right')-1
        assert (where>=0).all() and ((ix-available.take(where))<pd.Timedelta(days=1)).all()
        targets=base.iloc[where].to_numpy();late=targets[:-1].copy();late[ix[:-1]>=pd.Timestamp(x.action_time)]=0.
        i=inventory(prices,targets[:-1],targets[0],targets[-1],x.cost_bps)
        d=inventory(prices,late,targets[0],targets[-1],x.cost_bps)
        for a,b in zip(i,[x.inc_r,x.inc_dd,x.inc_turnover]):eq(a,b)
        for a,b in zip(d,[x.cash_r,x.cash_dd,x.cash_turnover]):eq(a,b)
        count+=2
    print('Independent cash/coin accounts',count,flush=True)
    ai=accounts.set_index(['anchor','lag_hours','cost_bps']);fits={x['id']:x for x in r['fits']}
    for fit in r['fits']:
        q=pd.Timestamp(fit['fit_time']);g=old.loc[old.lag_hours==fit['lag_hours']]
        num=g[['p1','p2','y']].apply(pd.to_numeric,errors='coerce')
        ok=(g.issue<q)&(g.end+24*H<q)&g.forecast_status.eq('ok')&np.isfinite(num).all(axis=1)&num.y.isin([0,1])&num.p1.between(0,1)&num.p2.between(0,1)
        t=g.loc[ok];w=2.**(-((q-t.issue)/pd.Timedelta(days=1)).to_numpy()/365.);f=fit['calibration']
        assert f['train_indices']==t.index.tolist();assert f['n']==len(t);assert f['positives']==int(t.y.sum())
        assert np.allclose(w,f['weights']);ess=sum(w)**2/sum(w*w) if len(w) else 0;eq(ess,f['effective_n'])
        ready=len(t)>=80 and min(t.y.sum(),len(t)-t.y.sum())>=15 and ess>=40
        assert (f['status']=='ok')==ready
        if not ready:continue
        eq((t.y.sum()+1)/(len(t)+2),f['oot_rate']);eq((sum(w*t.y)+1)/(sum(w)+2),f['recent_rate'])
        for name,col in [('price','p1'),('volume','p2')]:
            b=f[name]['offset'];score=logit(np.clip(t[col].to_numpy(),1e-6,1-1e-6))+b
            gradient=sum(w*(expit(score)-t.y))/sum(w)+.01*b
            assert abs(gradient)<1e-9
            eq(sum(w*(np.logaddexp(0,score)-t.y*score))/sum(w)+.005*b*b,f[name]['objective'])
        for key,mp in fit['mappings'].items():
            cost,lam=map(int,key.split('|'));ac=ai.reindex(pd.MultiIndex.from_arrays([t.anchor,np.full(len(t),fit['lag_hours']),np.full(len(t),cost)],names=ai.index.names))
            dr=ac.cash_r.to_numpy()-ac.inc_r.to_numpy()
            du=dr-lam*(np.maximum(-ac.cash_dd.to_numpy()-.05,0)-np.maximum(-ac.inc_dd.to_numpy()-.05,0))
            for k,gain in [('returns',dr),('utility',du)]:
                expected=mixture_map(t.y.to_numpy(),gain,w)
                if expected is None:assert mp[k] is None
                else:
                    for k2,v in expected.items():eq(v,mp[k][k2])
    print('Training memberships, offsets and mappings checked',len(fits),flush=True)
    prior=old.set_index(['anchor','lag_hours']);eligible={}
    for x in preds.itertuples():
        o=prior.loc[(x.anchor,x.lag_hours)];f=fits[x.fit_id]['calibration']
        for a,b in [(x.y,o.y),(x.r6_rate,o.p0),(x.raw_price,o.p1),(x.raw_volume,o.p2)]:eq(a,b)
        expected=o.forecast_status if o.forecast_status!='ok' else f['status'];assert x.calibration_status==expected
        if expected!='ok':continue
        eq(x.oot_rate,f['oot_rate']);eq(x.recent_rate,f['recent_rate'])
        eq(x.cal_price,expit(logit(np.clip(o.p1,1e-6,1-1e-6))+f['price']['offset']))
        eq(x.cal_volume,expit(logit(np.clip(o.p2,1e-6,1-1e-6))+f['volume']['offset']))
        eligible[(x.anchor,x.lag_hours)]=x
    for x in policy.itertuples():
        pr=eligible[(x.anchor,x.lag_hours)];mp=fits[x.fit_id]['mappings'][f'{x.cost_bps}|{x.lam}']
        ac=ai.loc[(x.anchor,x.lag_hours,x.cost_bps)];p=getattr(pr,x.model);eq(p,x.probability)
        if mp['utility'] is None or mp['returns'] is None:
            assert x.policy_status=='mapping_unavailable';continue
        eu=p*mp['utility']['mu1']+(1-p)*mp['utility']['mu0'];er=p*mp['returns']['mu1']+(1-p)*mp['returns']['mu0']
        eq(eu,x.expected_u);eq(er,x.expected_r);act=eu>0 and er>=-.002;assert bool(x.action)==act
        if ac.status!='ok':assert x.policy_status=='account_unavailable';continue
        assert x.policy_status=='scored'
        dr=ac.cash_r-ac.inc_r;du=dr-x.lam*(max(-ac.cash_dd-.05,0)-max(-ac.inc_dd-.05,0))
        eq(dr,x.cash_delta_r);eq(du,x.cash_delta_u);eq(act*dr,x.gain_r);eq(act*du,x.gain_u)
        dd=ac.cash_dd if act else ac.inc_dd;eq(dd,x.policy_dd);eq(ac.inc_dd,x.inc_dd)
        eq(max(-ac.inc_dd-.05,0)-max(-dd-.05,0),x.excess_reduction)
        eq((ac.cash_turnover-ac.inc_turnover) if act else 0,x.turnover_delta)
    for _,g in policy.loc[policy.policy_status=='scored'].groupby(['fit_id','cost_bps','lam','model']):
        q=g.action.mean();assert np.allclose(g.matched_frequency,q)
        assert np.allclose(g.frequency_r,(g.action.astype(float)-q)*g.cash_delta_r)
        assert np.allclose(g.frequency_u,(g.action.astype(float)-q)*g.cash_delta_u)
    print('All probability/action/frequency rows checked',len(preds),len(policy),flush=True)
    periods={'all_issued':('2018-01-01','2027-01-01'),'2018_2019':('2018-01-01','2020-01-01'),
             '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}
    for s in r['forecast_summaries']:
        lo,hi=map(pd.Timestamp,periods[s['period']]);f=preds.loc[(preds.lag_hours==s['lag_hours'])&(preds.issue>=lo)&(preds.issue<hi)]
        assert len(f)==s['candidates'] and f.calibration_status.value_counts().to_dict()==s['statuses']
        v=f.loc[f.calibration_status=='ok'].dropna(subset=['y']+MODELS).copy();y=v.y.to_numpy(float)
        for model in MODELS:
            p=v[model].to_numpy();m=s['scores'][model];assert m['n']==len(v)
            if not len(y):continue
            eq(np.mean((p-y)**2),m['brier']);q=np.clip(p,1e-12,1-1e-12)
            eq(-np.mean(y*np.log(q)+(1-y)*np.log1p(-q)),m['log_loss'])
            eq(p.mean(),m['mean_probability']);eq(y.mean(),m['event_fraction']);assert y.sum()==m['positive']
            pos=p[y==1];neg=p[y==0]
            auc=np.mean([(np.sum(x>neg)+.5*np.sum(x==neg))/len(neg) for x in pos]) if len(pos) and len(neg) else None
            eq(auc,m['auc']);binid=np.digitize(p,BINS[1:-1]);rel=res=0
            for j,b in enumerate(m['reliability_bins']):
                z=binid==j;assert z.sum()==b['n']
                if not z.any():continue
                eq(p[z].mean(),b['mean_probability']);eq(y[z].mean(),b['event_fraction'])
                rel+=z.mean()*(p[z].mean()-y[z].mean())**2;res+=z.mean()*(y[z].mean()-y.mean())**2
            eq(rel,m['reliability']);eq(res,m['resolution']);eq(y.mean()*(1-y.mean()),m['uncertainty'])
            eq(m['brier'],m['uncertainty']-res+rel+m['within_bin_residual'])
        for name,a,b in [('cal_price_minus_recent','cal_price','recent_rate'),('cal_price_minus_raw','cal_price','raw_price'),
                         ('cal_volume_minus_cal_price','cal_volume','cal_price'),('raw_price_minus_recent','raw_price','recent_rate')]:
            c=s['contrasts'][name];v['d']=(v[a]-v.y)**2-(v[b]-v.y)**2;eq(v.d.mean(),c['mean'])
            ci=interval(v,'d');assert ci is None and c['block95'] is None or np.allclose(ci,c['block95'])
            years=v.issue.dt.year
            for year,mean in c['leave_year_out'].items():eq(v.loc[years!=int(year),'d'].mean(),mean)
    for s in r['utility_summaries']:
        lo,hi=map(pd.Timestamp,periods[s['period']]);f=policy.loc[(policy.lag_hours==s['lag_hours'])&(policy.cost_bps==s['cost_bps'])&(policy.lam==s['lam'])&(policy.model==s['model'])&(policy.issue>=lo)&(policy.issue<hi)]
        assert len(f)==s['rows'] and f.policy_status.value_counts().to_dict()==s['statuses']
        v=f.loc[f.policy_status=='scored'];a=v.loc[v.action==True]
        assert len(v)==s['n'] and len(a)==s['cash_actions']
        assert (a.cash_delta_r.abs()>1e-12).sum()==s['actions_economically_different']
        assert (a.cash_delta_r<-.002).sum()==s['actual_mean_sacrifice_breaches']
        eq(a.loc[a.cash_delta_r>0,'cash_delta_r'].sum(),s['selected_loss_avoided_sum'])
        eq(-a.loc[a.cash_delta_r<0,'cash_delta_r'].sum(),s['selected_rebound_forgone_sum'])
        assert (v.inc_dd<-.05).sum()==s['inc_drawdown_exceed_count']
        assert (v.policy_dd<-.05).sum()==s['policy_drawdown_exceed_count']
        for k,d in s['stats'].items():
            eq(v[k].mean(),d['mean']);eq(v[k].median(),d['median']);ci=interval(v,k)
            assert ci is None and d['block95'] is None or np.allclose(ci,d['block95'])
        years=v.issue.dt.year
        for year,mean in s['leave_year_out_utility'].items():eq(v.loc[years!=int(year),'gain_u'].mean(),mean)
    print('R7_VERIFIED:',count,'cash/coin paths;',len(fits),'training snapshots;',len(preds),'prediction rows;',len(policy),'policy rows;',len(r['utility_summaries']),'utility summaries; all score bins, decompositions and paired intervals.')
    print('R7_HASHES:',len(r['inputs']),'input identities;',len(r['gates']),'gates;',len(r['prior_evidence']),'prior evidence unchanged. Same-session numerical verification, not independent review.')


if __name__=='__main__':main()
