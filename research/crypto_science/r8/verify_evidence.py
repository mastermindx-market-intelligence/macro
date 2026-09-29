"""Independent numerical expression of R8; same session, not external review."""
from pathlib import Path
import json,hashlib,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent;H=pd.Timedelta(hours=1)
FIELDS=['x_return1','x_return6','x_return24','x_trend720','x_structure','x_lows','x_log_sigma','x_exposure']
PERIODS={'full':('2016-01-01','2027-01-01'),'2016_2019':('2016-01-01','2020-01-01'),
         '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def eq(a,b):
    if a is None or pd.isna(a):assert b is None or pd.isna(b),(a,b)
    else:assert np.isclose(a,b,atol=1e-10,rtol=1e-8),(a,b)
def arr(a,b):assert np.allclose(a,b,atol=1e-10,rtol=1e-8,equal_nan=True)

def inventory(prices,targets,initial,terminal,bps,action):
    cash=1-initial;coins=initial/prices[0];last=initial;marks=[1.];turn=0.;pre=None
    for k,(price,target) in enumerate(zip(prices[:-1],targets)):
        wealth=cash+coins*price;marks.append(wealth);d=np.array(marks)
        if k==action:pre=[wealth-1,float(np.min(d/np.maximum.accumulate(d)-1)),coins*price/wealth,float(d.max())]
        if target!=last:
            move=abs(target-coins*price/wealth);wealth*=1-bps/10000*move;turn+=move
            cash=wealth*(1-target);coins=wealth*target/price;last=target;marks.append(wealth)
    wealth=cash+coins*prices[-1];marks.append(wealth);move=abs(terminal-coins*prices[-1]/wealth)
    wealth*=1-bps/10000*move;turn+=move;marks.append(wealth);marks=np.array(marks)
    return [wealth-1,float(np.min(marks/np.maximum.accumulate(marks)-1)),turn],pre

def clean(w):
    z=w[['open','high','low','close']].to_numpy(float)
    return np.isfinite(z).all() and (z>0).all() and (z[:,1]>=np.max(z,axis=1)).all() and (z[:,2]<=np.min(z,axis=1)).all()

def interval(f,key):
    f=f.dropna(subset=[key])
    if f.empty:return None
    ix=((pd.to_datetime(f.anchor)-pd.Timestamp('2016-01-01'))/pd.Timedelta(days=90)).astype(int)
    if ix.nunique()<2:return None
    domain=np.arange(ix.min(),ix.max()+1);v=f[key].to_numpy()
    totals=np.array([v[ix==k].sum() for k in domain]);n=np.array([(ix==k).sum() for k in domain])
    draw=np.random.default_rng(20260928).integers(0,len(domain),(1000,len(domain)))
    den=n[draw].sum(axis=1);num=totals[draw].sum(axis=1);return np.quantile(num[den>0]/den[den>0],[.025,.975]).tolist()
def check_stat(f,k,s):
    v=pd.to_numeric(f[k],errors='coerce').dropna();assert len(v)==s['n'];eq(v.mean(),s['mean']);eq(v.median(),s['median'])
    ci=interval(f,k)
    if ci is None:assert s['block95'] is None
    else:arr(ci,s['block95'])
def period(f,name):
    lo,hi=map(pd.Timestamp,PERIODS[name]);return f.loc[(pd.to_datetime(f.anchor)>=lo)&(pd.to_datetime(f.anchor)<hi)].copy()


def main():
    r=json.loads((HERE/'results.json').read_text());data=Path(config.data_dir())
    assert r['plan_commit']=='89b6876ba0937691270b7b042427ea6fc4c2e042'
    for key in ['prior_evidence','inherited_sources','sources']:assert all(sha(ROOT/p)==h for p,h in r[key].items()),key
    assert all((sha(data/p) if (data/p).exists() else None)==h for p,h in r['inputs'].items())
    assert all(sha(data/p)==h for p,h in r['gates'].items())
    a=pd.read_csv(HERE/'accounts.csv');p=pd.read_csv(HERE/'predictions.csv');policy=pd.read_csv(HERE/'policies.csv')
    for f in [a,p,policy]:
        for c in ['anchor','issue','end']:
            if c in f:f[c]=pd.to_datetime(f[c])
    h=pd.read_parquet(data/'coinbase/btc_hourly.parquet');b=pd.read_csv(HERE.parent/'r4/incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    count=0;features=0
    for x in a.drop_duplicates(['anchor','lag_hours','landmark']).itertuples():
        s=x.anchor+x.landmark*H;assert x.issue==s+H
        w=h.reindex(pd.date_range(s-720*H,periods=721,freq='h'));available=b.index+pd.Timedelta(hours=24+x.lag_hours)
        pos=available.searchsorted(x.issue,side='right')-1
        target=float(b.iloc[pos]) if pos>=0 and x.issue-available[pos]<24*H else np.nan
        if not clean(w):assert x.feature_status=='price_unknown';continue
        if not np.isfinite(target):assert x.feature_status=='exposure_unknown';continue
        prior=h.close.reindex(pd.date_range(s-73*H,periods=73,freq='h')).to_numpy()
        sig=np.std(np.log(prior[1:]/prior[:-1]),ddof=1)
        if sig<=0:assert x.feature_status=='price_unknown';continue
        vals=[np.log(w.close.iloc[-1]/w.close.iloc[-lag-1])/(sig*np.sqrt(lag)) for lag in [1,6,24,720]]
        low=h.low.reindex(pd.date_range(s-72*H,periods=72,freq='h')).min()
        l1=h.low.reindex(pd.date_range(s-5*H,periods=3,freq='h')).min();l2=h.low.reindex(pd.date_range(s-2*H,periods=3,freq='h')).min()
        vals += [np.log(w.close.iloc[-1]/low)/(sig*np.sqrt(6)),np.log(l2/l1)/(sig*np.sqrt(3)),np.log(sig),target]
        assert x.feature_status=='ok';arr(vals,[getattr(x,c) for c in FIELDS]);features+=1
    for x in a.itertuples():
        origin=x.anchor+(1+x.lag_hours)*H;end=origin+24*H;action=x.issue+x.lag_hours*H
        assert pd.Timestamp(x.origin)==origin and x.end==end and pd.Timestamp(x.action_time)==action
        ix=pd.date_range(origin,end,freq='h');prices=h.open.reindex(ix).to_numpy();avail=b.index+pd.Timedelta(hours=24+x.lag_hours)
        pos=avail.searchsorted(ix,side='right')-1;target=b.iloc[np.maximum(pos,0)].to_numpy();known=(pos>=0)&((ix-avail.take(np.maximum(pos,0)))<24*H)&np.isfinite(target)
        w=h.reindex(ix[:-1]);complete=clean(w) and np.isfinite(prices[-1]) and prices[-1]>0 and known.all()
        assert (x.account_status=='ok')==complete
        if not complete:continue
        cash=target[:-1].copy();cash[ix[:-1]>=action]=0.
        inc,pre=inventory(prices,target[:-1],target[0],target[-1],x.cost_bps,x.landmark)
        alternative,pre2=inventory(prices,cash,target[0],target[-1],x.cost_bps,x.landmark)
        arr(pre,pre2);arr(inc,[x.inc_r,x.inc_dd,x.inc_turnover]);arr(alternative,[x.cash_r,x.cash_dd,x.cash_turnover])
        arr(pre,[x.pre_return,x.pre_drawdown,x.action_weight,x.pre_highwater]);eq(target[0],x.initial_target)
        eq(alternative[0]-inc[0],x.dr);eq(max(-inc[1]-.05,0)-max(-alternative[1]-.05,0),x.dx)
        later=prices[x.landmark:];eq(later.min()/later[0]-1,x.post_price_worst);eq(later.max()/later[0]-1,x.post_price_best)
        recent=h.reindex(pd.date_range(x.issue-25*H,periods=25,freq='h'))
        eq(recent.close.iloc[-1]/recent.close.iloc[0]-1 if clean(recent) else None,x.price_return24)
        count+=2
    print('R8 independent features/accounts',features,count,flush=True)
    fits={f['id']:f for f in r['fits']};eligiblefits=0
    for z in r['fits']:
        q=pd.Timestamp(z['time']);g=a.loc[(a.landmark==z['landmark'])&(a.lag_hours==z['lag_hours'])&(a.cost_bps==z['cost_bps'])]
        ok=(g.issue<q)&(g.end+24*H<q)&np.isfinite(g[FIELDS+['dr','dx']].to_numpy()).all(axis=1);t=g.loc[ok];m=z['fit']
        assert m['train_indices']==t.index.tolist();assert m['n']==len(t);assert m['positive_gain']==sum(t.dr>1e-12);assert m['negative_gain']==sum(t.dr< -1e-12)
        ready=len(t)>=80 and min(sum(t.dr>1e-12),sum(t.dr< -1e-12))>=15;assert (m['status']=='ok')==ready
        if not ready:continue
        x=t[FIELDS].to_numpy();y=t[['dr','dx']].to_numpy();mu=x.mean(axis=0);scale=x.std(axis=0);scale[scale<=1e-12]=1.
        design=np.c_[np.ones(len(t)),np.clip((x-mu)/scale,-5,5)]
        aug=np.vstack([design,np.sqrt(.05*len(t))*np.c_[np.zeros(len(FIELDS)),np.eye(len(FIELDS))]])
        yy=np.vstack([y,np.zeros((len(FIELDS),2))]);beta=np.linalg.lstsq(aug,yy,rcond=None)[0]
        arr(mu,m['mean']);arr(scale,m['scale']);arr(beta,m['coef']);arr(y.mean(axis=0),m['target_mean'])
        arr(np.mean((design@beta-y)**2,axis=0),m['objective']);assert m['normal_residual']<1e-10;eligiblefits+=1
    print('R8 training identities/augmented least-squares',len(fits),eligiblefits,flush=True)
    ai=a.set_index(['anchor','landmark','lag_hours','cost_bps']);pi=p.set_index(['anchor','landmark','lag_hours','cost_bps'])
    for x in p.itertuples():
        old=ai.loc[(x.anchor,x.landmark,x.lag_hours,x.cost_bps)];m=fits[x.fit_id]['fit'];expected=old.feature_status if old.feature_status!='ok' else m['status']
        assert x.prediction_status==expected;eq(x.dr,old.dr);eq(x.dx,old.dx)
        if expected!='ok':continue
        design=np.r_[1,np.clip((old[FIELDS].to_numpy(float)-np.array(m['mean']))/np.array(m['scale']),-5,5)]
        arr(design@np.array(m['coef']),[x.ridge_dr,x.ridge_dx]);arr(m['target_mean'],[x.mean_dr,x.mean_dx])
    for x in policy.itertuples():
        pred=pi.loc[(x.anchor,x.landmark,x.lag_hours,x.cost_bps)];old=ai.loc[(x.anchor,x.landmark,x.lag_hours,x.cost_bps)]
        er=pred[x.model+'_dr'];ed=pred[x.model+'_dx'];eu=er+x.lam*ed;act=eu>0 and er>=-.002
        eq(er,x.expected_r);eq(ed,x.expected_dx);eq(eu,x.expected_u);assert bool(x.action)==act
        if old.account_status!='ok':assert x.policy_status==old.account_status;continue
        assert x.policy_status=='scored';eq(old.dr,x.dr);eq(old.dx,x.dx)
        eq(old.dr if act else 0,x.gain_r);eq(old.dr+x.lam*old.dx if act else 0,x.gain_u)
        eq(old.cash_dd if act else old.inc_dd,x.policy_dd);eq(old.inc_dd,x.inc_dd)
        eq(old.dx if act else 0,x.excess_reduction);eq(old.cash_turnover-old.inc_turnover if act else 0,x.turnover_delta)
    for _,v in policy.loc[policy.policy_status=='scored'].groupby(['fit_id','lam','model']):
        q=v.action.mean();arr(v.quarter_frequency,np.full(len(v),q));arr(v.frequency_r,(v.action.astype(float)-q)*v.dr);arr(v.frequency_u,(v.action.astype(float)-q)*(v.dr+v.lam*v.dx))
    print('R8 predictions/actions verified',len(p),len(policy),flush=True)
    for s in r['opportunity_summaries']:
        f=period(a,s['period']);f=f.loc[(f.landmark==s['landmark'])&(f.lag_hours==s['lag_hours'])&(f.cost_bps==s['cost_bps'])];v=f.loc[f.account_status=='ok'].copy()
        assert len(f)==s['n_parents'] and len(v)==s['n'];assert f.account_status.value_counts().to_dict()==s['status_counts']
        for name,col in [('pre_tail','pre_drawdown'),('inc_tail','inc_dd'),('cash_tail','cash_dd')]:assert sum(v[col]<-.05)==s[name]
        assert sum(v.action_weight.abs()<1e-12)==s['action_weight_zero'];assert sum(v.initial_target.abs()<1e-12)==s['initial_target_zero']
        assert sum(v.dr>1e-12)==s['cash_gain_positive'];assert sum(v.dr< -1e-12)==s['cash_gain_negative']
        for name,sr in s['stats'].items():
            if name.startswith('du_') or name.startswith('hindsight_'):
                lam=int(name.split('_')[-1]);v['z']=v.dr+lam*v.dx
                if name.startswith('hindsight'):v['z']=v.z.clip(lower=0)
                check_stat(v,'z',sr)
            else:check_stat(v,name,sr)
    for s in r['cash_timing']:
        v=period(a,s['period']);v=v.loc[(v.lag_hours==s['lag_hours'])&(v.cost_bps==s['cost_bps'])&(v.account_status=='ok')]
        e=v.loc[v.landmark==0].set_index('anchor');l=v.loc[v.landmark==6].set_index('anchor');ix=e.index.intersection(l.index)
        eu=e.loc[ix,'dr']+s['lam']*e.loc[ix,'dx'];lu=l.loc[ix,'dr']+s['lam']*l.loc[ix,'dx']
        f=pd.DataFrame({'anchor':ix,'d':(eu-lu).to_numpy(),'oracle':(eu.clip(lower=0)-lu.clip(lower=0)).to_numpy()})
        assert len(f)==s['n'];check_stat(f,'d',s['early_minus_late_cash']);check_stat(f,'oracle',s['early_minus_late_hindsight'])
    for s in r['score_summaries']:
        f=period(p,s['period']);f=f.loc[(f.landmark==s['landmark'])&(f.lag_hours==s['lag_hours'])&(f.cost_bps==s['cost_bps'])]
        v=f.loc[f.prediction_status=='ok'].dropna(subset=['dr','dx']);assert len(f)==s['rows'] and len(v)==s['n']
        assert f.prediction_status.value_counts().to_dict()==s['status_counts']
        for key,sr in s['scores'].items():
            target=key.split('_')[-1];err=v[key]-v[target]
            for val,name in [(np.mean(err**2),'mse'),(np.mean(np.abs(err)),'mae'),(err.mean(),'bias'),(v[key].mean(),'mean_prediction'),(v[target].mean(),'mean_observed')]:eq(val,sr[name])
    for s in r['utility_summaries']:
        f=period(policy,s['period']);f=f.loc[(f.landmark==s['landmark'])&(f.lag_hours==s['lag_hours'])&(f.cost_bps==s['cost_bps'])&(f.lam==s['lam'])&(f.model==s['model'])]
        v=f.loc[f.policy_status=='scored'];acts=v.loc[v.action==True]
        assert len(f)==s['rows'] and len(v)==s['n'] and len(acts)==s['actions'];assert f.policy_status.value_counts().to_dict()==s['status_counts']
        assert sum(acts.dr.abs()>1e-12)==s['economically_different'];assert sum(v.inc_dd<-.05)==s['inc_tail'];assert sum(v.policy_dd<-.05)==s['policy_tail']
        eq(acts.loc[acts.dr>0,'dr'].sum(),s['avoided_loss_sum']);eq(-acts.loc[acts.dr<0,'dr'].sum(),s['missed_rebound_sum'])
        for key,sr in s['stats'].items():check_stat(v,key,sr)
        for year,mean in s['leave_year_out_u'].items():eq(v.loc[v.anchor.dt.year!=int(year),'gain_u'].mean(),mean)
    for s in r['model_timing']:
        f=period(policy,s['period']);f=f.loc[(f.lag_hours==s['lag_hours'])&(f.cost_bps==s['cost_bps'])&(f.lam==s['lam'])&(f.model==s['model'])&(f.policy_status=='scored')]
        e=f.loc[f.landmark==0].set_index('anchor');l=f.loc[f.landmark==6].set_index('anchor');ix=e.index.intersection(l.index)
        v=pd.DataFrame({'anchor':ix,'r':(e.loc[ix,'gain_r']-l.loc[ix,'gain_r']).to_numpy(),'u':(e.loc[ix,'gain_u']-l.loc[ix,'gain_u']).to_numpy()})
        assert len(v)==s['n'];assert int(e.loc[ix,'action'].sum())==s['early_actions'];assert int(l.loc[ix,'action'].sum())==s['late_actions']
        check_stat(v,'r',s['early_minus_late_r']);check_stat(v,'u',s['early_minus_late_u'])
    # Preregistered M1-minus-M0 paired statistics supplement the per-model table.
    contrasts=[]
    for name in PERIODS:
        f=period(policy,name);f=f.loc[f.policy_status=='scored']
        for (k,lag,cost,lam),g in f.groupby(['landmark','lag_hours','cost_bps','lam']):
            m=g.loc[g.model=='mean'].set_index('anchor');v=g.loc[g.model=='ridge'].set_index('anchor');ix=m.index.intersection(v.index)
            paired=pd.DataFrame({'anchor':ix,'dr':(v.loc[ix,'gain_r']-m.loc[ix,'gain_r']).to_numpy(),'du':(v.loc[ix,'gain_u']-m.loc[ix,'gain_u']).to_numpy()})
            contrasts.append({'period':name,'landmark':int(k),'lag_hours':int(lag),'cost_bps':int(cost),'lam':int(lam),'n':len(ix),
                              'ridge_minus_mean_return':float(paired.dr.mean()),'ridge_minus_mean_utility':float(paired.du.mean()),
                              'return_block95':interval(paired,'dr'),'utility_block95':interval(paired,'du')})
    dest=HERE/'paired_method_contrasts.json'
    if dest.exists():assert json.loads(dest.read_text())==contrasts,'Existing contrast evidence differs'
    else:dest.write_text(json.dumps(contrasts,indent=2,allow_nan=False)+'\n')
    print('R8_VERIFIED',features,'independent features;',count,'inventory paths;',len(fits),'training snapshots;',len(p),'prediction rows;',len(policy),'policy rows;',len(r['utility_summaries']),'utility summaries;',len(contrasts),'paired method contrasts.')
    print('R8_HASHES',len(r['inputs']),'inputs;',len(r['gates']),'gates;',len(r['prior_evidence']),'prior artifacts unchanged. Arithmetic is SAME-session, not independent review.')

if __name__=='__main__':main()
