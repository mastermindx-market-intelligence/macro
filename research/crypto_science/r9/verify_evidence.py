"""Same-session independent numerical expression of R9; not external review."""
from pathlib import Path
import json,hashlib,sys
import numpy as np
import pandas as pd
from scipy.special import expit
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent
H=pd.Timedelta(hours=1)
FIELDS=['x_return1','x_return6','x_return24','x_trend720','x_structure','x_lows','x_log_sigma','x_exposure']
PERIODS={'all_issued':('2018-01-01','2027-01-01'),'2018_2019':('2018-01-01','2020-01-01'),'2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def eq(a,b):
    if a is None or pd.isna(a):assert b is None or pd.isna(b),(a,b)
    else:assert np.isclose(a,b,atol=1e-10,rtol=1e-8),(a,b)
def part(f,p,col='issue'):
    lo,hi=map(pd.Timestamp,PERIODS[p]);return f.loc[(f[col]>=lo)&(f[col]<hi)].copy()
def interval(f,k):
    f=f.dropna(subset=[k]);v=f[k].to_numpy()
    if f.empty:return None
    ids=((f.anchor-pd.Timestamp('2016-01-01'))/pd.Timedelta(days=90)).astype(int)
    if ids.nunique()<2:return None
    domain=np.arange(ids.min(),ids.max()+1);ss=np.array([v[ids==j].sum() for j in domain]);nn=np.array([(ids==j).sum() for j in domain])
    draw=np.random.default_rng(20260928).integers(0,len(domain),(1000,len(domain)));n=nn[draw].sum(axis=1)
    return np.quantile(ss[draw].sum(axis=1)[n>0]/n[n>0],[.025,.975]).tolist()
def cieq(a,b):
    if a is None:assert b is None
    else:assert np.allclose(a,b,atol=1e-10,rtol=1e-8),(a,b)
def inventory(prices,targets,initial,terminal,cost):
    cash=1-initial;coin=initial/prices[0];last=initial;marks=[1.];turn=0.;fee=cost/10000
    for price,target in zip(prices[:-1],targets):
        wealth=cash+coin*price;marks.append(wealth)
        if target!=last:
            change=abs(target-coin*price/wealth);wealth*=1-fee*change;turn+=change
            coin=wealth*target/price;cash=wealth*(1-target);last=target;marks.append(wealth)
    wealth=cash+coin*prices[-1];marks.append(wealth);change=abs(terminal-coin*prices[-1]/wealth)
    wealth*=1-fee*change;marks.append(wealth);turn+=change
    a=np.array(marks);return wealth-1,float(np.min(a/np.maximum.accumulate(a)-1)),turn


def main():
    r=json.loads((HERE/'results.json').read_text());data=Path(config.data_dir())
    for k in ['prior_evidence','inherited_sources','sources']:assert all(sha(p)==h for p,h in r[k].items()),k
    assert all((sha(data/p) if (data/p).exists() else None)==h for p,h in r['inputs'].items())
    assert all(sha(data/p)==h for p,h in r['gates'].items())
    rec=pd.read_csv(HERE/'clock_records.csv');pred=pd.read_csv(HERE/'predictions.csv');warn=pd.read_csv(HERE/'warnings.csv')
    events=pd.read_csv(HERE/'events.csv');matches=pd.read_csv(HERE/'event_matches.csv');accounts=pd.read_csv(HERE/'warning_accounts.csv')
    monthly=pd.read_csv(HERE/'monthly_burden.csv')
    for f in [rec,pred,warn,events,accounts]:
        for col in ['issue','anchor','entry','end','break_issue','confirm']:
            if col in f:f[col]=pd.to_datetime(f[col])
    h=pd.read_parquet(data/'coinbase/btc_hourly.parquet');index=pd.date_range(h.index.min(),h.index.max(),freq='h');v=h.reindex(index)[['open','high','low','close']].to_numpy(float)
    valid=np.isfinite(v).all(axis=1)&(v>0).all(axis=1)&(v[:,1]>=v.max(axis=1))&(v[:,2]<=v.min(axis=1))
    d0=np.full(len(index),np.nan)
    for j in range(73,len(index)):
        if valid[j-73:j+1].all() and np.std(np.diff(v[j-25:j,3])/v[j-25:j-1,3],ddof=1)>0:d0[j]=float(v[j,3]<v[j-72:j,2].min())
    base=pd.read_csv(HERE.parent/'r4/incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    def target(t,lag):
        available=base.index+pd.Timedelta(hours=24+lag);ix=available.searchsorted(t,side='right')-1
        if ix<0 or pd.Timestamp(t)-available[ix]>=pd.Timedelta(days=1):return np.nan
        z=float(base.iloc[ix]);return z if np.isfinite(z) and 0<=z<=1 else np.nan
    def label(entry):
        j=index.get_indexer([entry])[0]
        if j<0 or j+24>=len(index) or not valid[j:j+24].all() or not np.isfinite(v[j+24,0]) or v[j+24,0]<=0:return 'censored',None,None
        ref=v[j,0];lo=.95*ref;hi=1.03*ref
        for k,b in enumerate(v[j:j+24]):
            o,high,low,_=b
            if o<=lo:cat='lower_first'
            elif o>=hi:cat='upper_first'
            elif low<=lo and high>=hi:cat='ambiguous'
            elif low<=lo:cat='lower_first'
            elif high>=hi:cat='upper_first'
            else:continue
            return cat,1. if cat=='lower_first' else 0. if cat=='upper_first' else None,k
        return 'neither',0.,None
    expected_issues=index[(index+H).hour%6==0]+H
    nfeat=0
    for lag,g in rec.groupby('lag_hours'):
        assert pd.DatetimeIndex(g.issue).equals(expected_issues)
        for x in g.itertuples():
            j=index.get_indexer([x.issue-H])[0];history=d0[max(0,j-23):j+1]
            watch='history_unknown' if len(history)!=24 or not np.isfinite(history).all() else 'recent_break' if history.any() else 'prebreak'
            assert x.watch_status==watch
            exp=target(x.issue,lag);status='price_unknown'
            if j>=720 and valid[j-720:j+1].all():
                logs=np.log(v[j-720:j+1,3]);sigma=np.std(np.diff(logs[-74:-1]),ddof=1)
                if np.isfinite(sigma) and sigma>0:
                    status='ok' if np.isfinite(exp) else 'exposure_unknown'
                    if status=='ok':
                        vals=[(logs[-1]-logs[-k-1])/(sigma*np.sqrt(k)) for k in [1,6,24,720]]
                        vals += [(logs[-1]-np.log(v[j-72:j,2].min()))/(sigma*np.sqrt(6)),np.log(v[j-2:j+1,2].min()/v[j-5:j-2,2].min())/(sigma*np.sqrt(3)),np.log(sigma),exp]
                        assert np.allclose(vals,[getattr(x,k) for k in FIELDS],atol=1e-9,rtol=1e-8);nfeat+=1
            assert x.feature_status==status
            c,y,k=label(x.entry);assert c==x.category;eq(y,x.y);eq(k,x.barrier_hour)
    print('R9 independent clock/features/labels',len(rec),nfeat,flush=True)
    anchors=[]
    for j in range(1,len(index)):
        if d0[j]==1 and d0[j-1]==0 and (not anchors or index[j]-anchors[-1]>24*H):anchors.append(index[j])
    for lag,g in events.groupby('lag_hours'):
        assert pd.DatetimeIndex(g.anchor).equals(pd.DatetimeIndex(anchors))
        for x in g.itertuples():
            c,y,k=label(x.entry);assert c==x.category;eq(y,x.y);eq(k,x.barrier_hour)
            if c=='lower_first':assert x.confirm==x.entry+(k+1)*H
    fits={f['id']:f for f in r['fits']}
    for f in r['fits']:
        q=pd.Timestamp(f['quarter']);g=rec.loc[rec.lag_hours==f['lag_hours']];n=g[FIELDS+['y']].apply(pd.to_numeric,errors='coerce')
        m=(g.issue<q)&(g.end+24*H<q)&g.watch_status.eq('prebreak')&g.feature_status.eq('ok')&np.isfinite(n).all(axis=1)&n.y.isin([0,1]);t=g.loc[m];fit=f['fit']
        assert fit['train_indices']==t.index.tolist() and fit['n']==len(t) and fit['positive']==t.y.sum()
        ready=len(t)>=1000 and t.y.sum()>=30 and (len(t)-t.y.sum())>=300
        if not ready:assert fit['status']=='insufficient_training';continue
        model=fit['model'];xx=t[FIELDS].to_numpy();mean=xx.mean(axis=0);scale=xx.std(axis=0);scale[scale<=1e-12]=1
        assert np.allclose(mean,model['mean']) and np.allclose(scale,model['scale'])
        z=np.c_[np.ones(len(t)),np.clip((xx-mean)/scale,-5,5)];b=np.array(model['coef']);score=z@b;y=t.y.to_numpy()
        grad=z.T@(expit(score)-y)/len(t)+.05*np.r_[0,b[1:]];assert np.max(np.abs(grad))<2e-6,grad
        eq(np.mean(np.logaddexp(0,score)-y*score)+.025*np.dot(b[1:],b[1:]),model['objective'])
        w=np.exp2(-((q-t.issue)/pd.Timedelta(days=1)).to_numpy()/365);eq((sum(w*y)+1)/(sum(w)+2),fit['recent_rate'])
    for x in pred.itertuples():
        a=rec.loc[x.row_id];fit=fits[x.fit_id]['fit']
        status=a.watch_status if a.watch_status!='prebreak' else a.feature_status if a.feature_status!='ok' else fit['status'];assert status==x.forecast_status
        eq(a.y,x.y)
        if status=='ok':
            md=fit['model'];z=np.clip((a[FIELDS].to_numpy(float)-md['mean'])/md['scale'],-5,5);eq(expit(md['coef'][0]+np.dot(z,md['coef'][1:])),x.price);eq(fit['recent_rate'],x.recent)
    print('R9 chronological memberships, gradients and predictions verified',len(fits),len(pred),flush=True)
    for lag,g in pred.groupby('lag_hours'):
        for method in ['recent','price']:
            chosen=[];until=None
            for x in g.sort_values('issue').itertuples():
                if x.forecast_status=='ok' and getattr(x,method)>=.1 and (until is None or x.issue>=until):
                    chosen.append(f'{lag}|{method}|{x.Index}');until=x.end
            w=warn.loc[(warn.lag_hours==lag)&warn.model.eq(method)];assert chosen==w.warning_id.tolist()
            e=events.loc[(events.lag_hours==lag)&events.category.eq('lower_first')];used=set();expected=[]
            for x in w.itertuples():
                allowed=e.loc[(e.break_issue>x.issue)&(e.break_issue<=x.issue+24*H)&(e.break_issue>x.entry)&(e.confirm<=x.end)&~e.event_id.isin(used)]
                if len(allowed):
                    a=allowed.sort_values('break_issue').iloc[0];used.add(a.event_id);expected.append((x.warning_id,a.event_id,(a.break_issue-x.issue)/H,(a.break_issue-x.entry)/H))
            got=matches.loc[(matches.lag_hours==lag)&matches.model.eq(method)]
            assert expected==list(got[['warning_id','event_id','lead_issue_h','lead_action_h']].itertuples(index=False,name=None))
        cand=g.loc[g.forecast_status=='ok']
        for e in events.loc[(events.lag_hours==lag)&events.category.eq('lower_first')].itertuples():
            z=cand.loc[(cand.issue<e.break_issue)&(cand.issue>=e.break_issue-24*H)&(cand.entry<e.break_issue)&(cand.end>=e.confirm)]
            assert e.supported==bool(len(z)) and e.eligible_watches==len(z)
    count=0
    for x in accounts.itertuples():
        j=index.get_indexer([x.entry])[0];good=j>=0 and j+24<len(index) and valid[j:j+24].all() and np.isfinite(v[j+24,0]) and v[j+24,0]>0
        t=np.array([target(u,x.lag_hours) for u in pd.date_range(x.entry,periods=25,freq='h')]);good &= np.isfinite(t).all()
        if not good:assert x.status=='account_unavailable';continue
        p=v[j:j+25,0];i=inventory(p,t[:-1],t[0],t[-1],x.cost_bps);c=inventory(p,np.zeros(24),t[0],t[-1],x.cost_bps)
        for a,b in zip(i,[x.inc_r,x.inc_dd,x.inc_turnover]):eq(a,b)
        for a,b in zip(c,[x.cash_r,x.cash_dd,x.cash_turnover]):eq(a,b)
        eq(c[0]-i[0],x.dr);eq(max(-i[1]-.05,0)-max(-c[1]-.05,0),x.dx);eq(x.dr+x.dx,x.du);eq(t[0],x.initial_exposure);count+=2
    print('R9 warnings/event matching and independent inventory paths',len(warn),len(matches),count,flush=True)
    for s in r['forecast_summaries']:
        f=part(pred.loc[pred.lag_hours==s['lag_hours']],s['period']);assert len(f)==s['clock_rows'] and f.forecast_status.value_counts().to_dict()==s['statuses']
        a=f.loc[f.forecast_status=='ok'].dropna(subset=['y','recent','price']).copy();y=a.y.to_numpy(float)
        for model in ['recent','price']:
            p=a[model].to_numpy(float);d=s[model];assert d['n']==len(a)
            if not len(a):continue
            eq(np.mean((p-y)**2),d['brier']);q=np.clip(p,1e-12,1-1e-12);eq(-np.mean(y*np.log(q)+(1-y)*np.log1p(-q)),d['log_loss'])
            eq(p.mean(),d['mean_probability']);eq(y.mean(),d['event_fraction']);assert sum(y)==d['positive']
            pos=p[y==1];neg=np.sort(p[y==0]);auc=float(np.mean((np.searchsorted(neg,pos,'left')+.5*(np.searchsorted(neg,pos,'right')-np.searchsorted(neg,pos,'left')))/len(neg))) if len(pos) and len(neg) else None
            eq(auc,d['auc'])
            bins=pd.DataFrame({'p':p,'y':y}).groupby('p').y.agg(['sum','count']).sort_index(ascending=False)
            ap=float(np.sum(bins['sum']/sum(y)*bins['sum'].cumsum()/bins['count'].cumsum())) if sum(y) else None;eq(ap,d['average_precision'])
            for b in d['reliability']:
                z=(p>=b['lo'])&((p<b['hi']) if b['hi']<1 else (p<=b['hi']))
                assert sum(z)==b['n'];eq(p[z].mean() if z.any() else None,b['p']);eq(y[z].mean() if z.any() else None,b['y'])
        a['difference']=(a.price-a.y)**2-(a.recent-a.y)**2
        eq(a.difference.mean(),s['brier_price_minus_recent']['mean']);cieq(interval(a,'difference'),s['brier_price_minus_recent']['block95'])
    def check_alarm(d,w,n):
        y=pd.to_numeric(w.y,errors='coerce');k=y.isin([0,1]);pos=y.eq(1).sum();neg=y.eq(0).sum();months=n*6/(24*30.4375)
        assert len(w)==d['issued'] and k.sum()==d['scored'] and (~k).sum()==d['unknown']
        assert pos==d['true_window'] and neg==d['false_window'];eq(pos/k.sum() if k.sum() else None,d['precision'])
        eq(months,d['watch_equivalent_months']);eq(neg/months if months else None,d['false_per_watch_month']);eq(len(w)/months if months else None,d['warnings_per_watch_month'])
    for s in r['alarm_summaries']:
        f=part(pred.loc[pred.lag_hours==s['lag_hours']],s['period']);a=f.loc[f.forecast_status=='ok'].dropna(subset=['y','recent','price'])
        w=part(warn.loc[(warn.lag_hours==s['lag_hours'])&warn.model.eq(s['model'])],s['period']);check_alarm(s,w,len(a))
        assert f.loc[f.forecast_status=='ok',s['model']].ge(.1).sum()==s['raw_high_scores']
        e=part(events.loc[(events.lag_hours==s['lag_hours'])&events.category.eq('lower_first')],s['period'],'break_issue')
        m=matches.loc[(matches.lag_hours==s['lag_hours'])&matches.model.eq(s['model'])];hits=m.loc[m.event_id.isin(e.event_id)]
        assert len(e)==s['all_damaging_events'] and e.supported.sum()==s['supported_damaging_events'] and len(hits)==s['matched_events']
        eq(len(hits)/len(e) if len(e) else None,s['all_event_recall']);eq(len(hits)/e.supported.sum() if e.supported.sum() else None,s['supported_event_recall'])
        assert m.warning_id.isin(w.warning_id).sum()==s['warnings_matched_event']
        eq(hits.lead_issue_h.median(),s['issue_lead_median_h']);eq(hits.lead_action_h.median(),s['action_lead_median_h']);eq(hits.lead_issue_h.min(),s['lead_min_h']);eq(hits.lead_issue_h.max(),s['lead_max_h'])
    for x in monthly.to_dict('records'):
        f=pred.loc[(pred.lag_hours==x['lag_hours'])&pred.issue.dt.to_period('M').astype(str).eq(x['month'])]
        a=f.loc[f.forecast_status.eq('ok')&f.y.notna()];w=warn.loc[(warn.lag_hours==x['lag_hours'])&warn.model.eq(x['model'])&warn.issue.dt.to_period('M').astype(str).eq(x['month'])]
        assert len(f)==x['clock_rows'] and len(a)==x['eligible_rows'];check_alarm(x,w,len(a))
    for s in r['economic_summaries']:
        f=part(accounts.loc[(accounts.lag_hours==s['lag_hours'])&accounts.model.eq(s['model'])&(accounts.cost_bps==s['cost_bps'])],s['period'])
        a=f.loc[f.status=='ok'].copy();a['turnover_delta']=a.cash_turnover-a.inc_turnover
        assert len(f)==s['issued'] and len(a)==s['usable'] and len(f)-len(a)==s['unknown']
        assert a.initial_exposure.eq(0).sum()==s['already_cash'] and a.dr.abs().gt(1e-12).sum()==s['economically_different']
        assert a.inc_dd.lt(-.05).sum()==s['inc_tail_count'] and a.cash_dd.lt(-.05).sum()==s['cash_tail_count']
        eq(a.loc[a.dr>0,'dr'].sum(),s['avoided_loss_sum']);eq(-a.loc[a.dr<0,'dr'].sum(),s['missed_rebound_sum'])
        for k,d in s['stats'].items():
            assert len(a)==d['n'];eq(a[k].mean(),d['mean']);eq(a[k].median(),d['median']);cieq(interval(a,k),d['block95'])
    print('R9_VERIFIED:',len(rec),'calendar rows;',nfeat,'features;',len(fits),'training snapshots;',len(pred),'predictions;',len(warn),'warnings;',len(events),'catalogue events;',len(matches),'strict advance matches;',count,'inventory paths; all forecast/alarm/monthly/economic summaries.')
    print('R9_HASHES:',len(r['inputs']),'inputs;',len(r['gates']),'gates;',len(r['prior_evidence']),'prior artifacts unchanged. SAME-session arithmetic, not independent review.')


if __name__=='__main__':main()
