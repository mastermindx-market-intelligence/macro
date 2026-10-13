"""Frozen R9 fixed-clock pre-break research. No live forecast/alert/policy owner."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.crypto_science import r4_sequence_study as r4,r6_probability_study as r6,r8_action_value_study as r8
H=pd.Timedelta(hours=1)
OUT=Path(__file__).with_name('r9')
BASE='27b97a4ff4807656e66df3707664300953d72221'
PLAN='3821bcdade52648ea1c18667b538a032c4c1808c'
FIELDS=r8.FIELDS
BINS=np.array([0,.025,.05,.1,.2,.4,1.])
PERIODS={'all_issued':('2018-01-01','2027-01-01'),'2018_2019':('2018-01-01','2020-01-01'),
         '2020_2023':('2020-01-01','2024-01-01'),'reused_2024plus':('2024-01-01','2027-01-01')}
MODELS=['recent','price']


def clock_features(hourly,exposure):
    g,valid=r4.checked_grid(hourly,'h');c=np.log(g.close)
    sigma=c.diff().shift(1).rolling(72).std(ddof=1)
    complete=valid.astype(int).rolling(721).sum().eq(721)&sigma.gt(0)&np.isfinite(sigma)
    f=pd.DataFrame(index=g.index)
    for k,name in [(1,'x_return1'),(6,'x_return6'),(24,'x_return24'),(720,'x_trend720')]:
        f[name]=(c-c.shift(k))/(sigma*np.sqrt(k))
    f['x_structure']=(c-np.log(g.low.shift(1).rolling(72).min()))/(sigma*np.sqrt(6))
    f['x_lows']=np.log(g.low.rolling(3).min()/g.low.shift(3).rolling(3).min())/(sigma*np.sqrt(3))
    f['x_log_sigma']=np.log(sigma);f['issue']=f.index+H
    f['x_exposure']=exposure.reindex(pd.DatetimeIndex(f.issue)).to_numpy()
    exposure_ok=np.isfinite(f.x_exposure)&f.x_exposure.between(0,1)
    f['feature_status']=np.where(~complete,'price_unknown',np.where(exposure_ok,'ok','exposure_unknown'))
    f.loc[~complete,FIELDS[:-1]]=np.nan;f.loc[~exposure_ok,'x_exposure']=np.nan
    d0=r4.hourly_conditions(g).d0;known=d0.notna().astype(int).rolling(24).sum().eq(24)
    anybreak=d0.fillna(False).astype(int).rolling(24).max().eq(1)
    f['watch_status']=np.where(~known,'history_unknown',np.where(anybreak,'recent_break','prebreak'))
    f['return24']=np.expm1(c-c.shift(24))
    f=f.loc[f.issue.dt.hour%6==0].copy();f['anchor']=f.issue
    return f.reset_index(drop=True)


def outcome(hourly,entry):
    x=r4.barrier_label(hourly,entry,hours=24,lower=-.05,upper=.03)
    y=1. if x['category']=='lower_first' else 0. if x['category'] in ['upper_first','neither'] else None
    return dict(x,y=y)


def fit_watch(frame,cutoff):
    q=pd.Timestamp(cutoff);num=frame[FIELDS+['y']].apply(pd.to_numeric,errors='coerce')
    good=frame.watch_status.eq('prebreak')&frame.feature_status.eq('ok')
    good&=(pd.to_datetime(frame.issue)<q)&(pd.to_datetime(frame.end)+24*H<q)&np.isfinite(num).all(axis=1)&num.y.isin([0,1])
    t=frame.loc[good];y=t.y.to_numpy(float);n=len(t);pos=int(y.sum())
    m={'status':'insufficient_training','n':n,'positive':pos,'negative':n-pos,'train_indices':list(map(int,t.index))}
    if n<1000 or pos<30 or n-pos<300:return m
    w=np.exp2(-np.asarray((q-pd.to_datetime(t.issue))/pd.Timedelta(days=1),float)/365)
    model=r6.fit_logistic(t[FIELDS].to_numpy(float),y)
    m.update(status=model['status'],recent_rate=float((np.dot(w,y)+1)/(w.sum()+2)),model=model,
             last_train_end=str(pd.to_datetime(t.end).max()))
    return m


def emit_warnings(frame,model):
    selected=[];expiry=None
    for x in frame.sort_values('issue').itertuples():
        p=getattr(x,model)
        if x.forecast_status!='ok' or not np.isfinite(p) or p<.10:continue
        if expiry is not None and x.issue<expiry:continue
        selected.append(x.Index);expiry=pd.Timestamp(x.end)
    return selected


def match_events(warnings,events):
    used=set();matches=[]
    for x in warnings.sort_values('issue').itertuples():
        for e in events.sort_values('break_issue').itertuples():
            if e.event_id in used:continue
            if (x.issue<e.break_issue<=x.issue+24*H and x.entry<e.break_issue and e.confirm<=x.end):
                matches.append({'warning_index':x.Index,'event_id':e.event_id,
                  'lead_issue_h':float((e.break_issue-x.issue)/H),'lead_action_h':float((e.break_issue-x.entry)/H)})
                used.add(e.event_id);break
    return matches


def alarm_counts(warnings,watch_rows):
    y=pd.to_numeric(warnings.y,errors='coerce');known=y.isin([0,1]);months=watch_rows*6/(24*30.4375)
    pos=int(y.eq(1).sum());neg=int(y.eq(0).sum())
    return {'issued':len(warnings),'scored':int(known.sum()),'unknown':int((~known).sum()),'true_window':pos,'false_window':neg,
            'precision':float(pos/known.sum()) if known.sum() else None,'watch_equivalent_months':months,
            'false_per_watch_month':float(neg/months) if months else None,'warnings_per_watch_month':float(len(warnings)/months) if months else None}


def warning_account(hourly,targets,entry,cost):
    w=r4.complete_window(hourly,entry,24);ix=pd.date_range(entry,periods=25,freq='h');t=targets.reindex(ix)
    if w is None or not t.notna().all():return {'status':'account_unavailable'}
    i=r4.account_path(w.open,t.iloc[:-1],initial_weight=float(t.iloc[0]),terminal_weight=float(t.iloc[-1]),cost_bps=cost)
    c=r4.account_path(w.open,np.zeros(24),initial_weight=float(t.iloc[0]),terminal_weight=float(t.iloc[-1]),cost_bps=cost)
    dr=c['return']-i['return'];dx=max(-i['max_drawdown']-.05,0)-max(-c['max_drawdown']-.05,0)
    return {'status':'ok','inc_r':i['return'],'cash_r':c['return'],'inc_dd':i['max_drawdown'],'cash_dd':c['max_drawdown'],
            'inc_turnover':i['turnover'],'cash_turnover':c['turnover'],'initial_exposure':float(t.iloc[0]),'dr':dr,'dx':dx,'du':dr+dx}


def average_precision(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    if len(y)!=len(p) or not np.isin(y,[0,1]).all() or not np.isfinite(p).all():raise ValueError('Invalid scored observations')
    if not y.sum():return None
    order=np.argsort(-p,kind='stable');y=y[order];p=p[order]
    ends=np.r_[np.flatnonzero(p[1:]!=p[:-1]),len(p)-1]
    tp=np.cumsum(y)[ends];precision=tp/(ends+1)
    return float(np.sum(np.diff(np.r_[0,tp])/y.sum()*precision))


def proper_scores(frame,model):
    v=frame.dropna(subset=['y',model]);s=r6.probability_metrics(v.y,v[model])
    if not len(v):return s
    s['average_precision']=average_precision(v.y,v[model])
    bins=[];ix=np.digitize(v[model],BINS[1:-1])
    for j in range(len(BINS)-1):
        m=ix==j;bins.append({'lo':float(BINS[j]),'hi':float(BINS[j+1]),'n':int(m.sum()),
             'p':r4.number(v.loc[m,model].mean()),'y':r4.number(v.loc[m,'y'].mean())})
    s['reliability']=bins;return s


def part(f,period,column='issue'):
    lo,hi=map(pd.Timestamp,PERIODS[period]);return f.loc[(pd.to_datetime(f[column])>=lo)&(pd.to_datetime(f[column])<hi)].copy()


def summaries(records,preds,warnings,events,matches,accounts):
    forecast=[];alarms=[];economics=[];months=[]
    for period in PERIODS:
        for lag,g in preds.groupby('lag_hours'):
            f=part(g,period);v=f.loc[f.forecast_status=='ok'].dropna(subset=['y','recent','price']).copy()
            v['brier_delta']=(v.price-v.y)**2-(v.recent-v.y)**2
            forecast.append({'period':period,'lag_hours':int(lag),'clock_rows':len(f),'statuses':f.forecast_status.value_counts().to_dict(),
                'recent':proper_scores(v,'recent'),'price':proper_scores(v,'price'),
                'brier_price_minus_recent':{'n':len(v),'mean':r4.number(v.brier_delta.mean()),'block95':r4.interval90(v,'brier_delta')}})
            for model in MODELS:
                wg=warnings.loc[(warnings.lag_hours==lag)&(warnings.model==model)];w=part(wg,period)
                e=part(events.loc[(events.lag_hours==lag)&events.category.eq('lower_first')],period,'break_issue')
                eg=events.loc[(events.lag_hours==lag)&events.category.eq('lower_first')]
                selected=matches.loc[(matches.lag_hours==lag)&(matches.model==model)]
                hit=selected.loc[selected.event_id.isin(e.event_id)]
                inperiod_warn=selected.loc[selected.warning_id.isin(w.warning_id)]
                ycounts=alarm_counts(w,len(v));candidate=f.loc[f.forecast_status=='ok']
                alarms.append(dict(period=period,lag_hours=int(lag),model=model,**ycounts,
                    raw_high_scores=int(candidate[model].ge(.1).sum()),calendar_months=int(f.issue.dt.to_period('M').nunique()),
                    all_damaging_events=len(e),supported_damaging_events=int(e.supported.sum()),matched_events=len(hit),
                    all_event_recall=float(len(hit)/len(e)) if len(e) else None,
                    supported_event_recall=float(len(hit)/e.supported.sum()) if e.supported.sum() else None,
                    warnings_matched_event=len(inperiod_warn),
                    issue_lead_median_h=r4.number(hit.lead_issue_h.median()),action_lead_median_h=r4.number(hit.lead_action_h.median()),
                    lead_min_h=r4.number(hit.lead_issue_h.min()),lead_max_h=r4.number(hit.lead_issue_h.max())))
                for month,mg in f.groupby(f.issue.dt.to_period('M')):
                    mw=w.loc[w.issue.dt.to_period('M')==month];vv=mg.loc[mg.forecast_status.eq('ok')&mg.y.notna()]
                    if period=='all_issued':months.append(dict(month=str(month),lag_hours=int(lag),model=model,clock_rows=len(mg),eligible_rows=len(vv),**alarm_counts(mw,len(vv))))
                for cost in [0,10,25]:
                    raw=accounts.loc[(accounts.lag_hours==lag)&(accounts.model==model)&(accounts.cost_bps==cost)]
                    a=part(raw,period);ok=a.loc[a.status=='ok'].copy()
                    if len(ok):ok['turnover_delta']=ok.cash_turnover-ok.inc_turnover
                    else:ok['turnover_delta']=pd.Series(dtype=float)
                    stats={k:{'n':len(ok),'mean':r4.number(ok[k].mean()),'median':r4.number(ok[k].median()),'block95':r4.interval90(ok,k)} for k in ['dr','dx','du','turnover_delta']}
                    economics.append({'period':period,'lag_hours':int(lag),'model':model,'cost_bps':cost,'issued':len(a),'usable':len(ok),
                        'unknown':len(a)-len(ok),'already_cash':int(ok.initial_exposure.eq(0).sum()),
                        'economically_different':int(ok.dr.abs().gt(1e-12).sum()),'inc_tail_count':int(ok.inc_dd.lt(-.05).sum()),'cash_tail_count':int(ok.cash_dd.lt(-.05).sum()),
                        'avoided_loss_sum':r4.number(ok.loc[ok.dr>0,'dr'].sum()),'missed_rebound_sum':r4.number(-ok.loc[ok.dr<0,'dr'].sum()),'stats':stats})
    return forecast,alarms,economics,pd.DataFrame(months)


def main():
    from lib import config
    OUT.mkdir(exist_ok=True)
    if (OUT/'results.json').exists():raise RuntimeError('R9 results exist; reconcile instead of replay')
    data=Path(config.data_dir());old=json.loads((OUT.parent/'r8/results.json').read_text());inputs=old['inputs'];gates=old['gates']
    inherited=dict(old['inherited_sources']);inherited.update({k:v for k,v in old['sources'].items() if k!='tests/test_btc_impulse_falsifier.py'})
    prior={str(p.relative_to(ROOT)):r4.digest(p) for d in [f'r{i}' for i in range(1,9)] for p in (OUT.parent/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    names=['research/crypto_science/r9_prebreak_study.py','research/CRYPTO_SCIENCE_R9_PREBREAK_PREREG_2026-09-29.md','tests/test_btc_impulse_falsifier.py']
    sources={k:r4.digest(ROOT/k) for k in names}
    assert (ROOT/names[-1]).read_bytes().startswith(subprocess.check_output(['git','show',BASE+':'+names[-1]],cwd=ROOT))
    def unchanged():
        assert all((r4.digest(data/k) if (data/k).exists() else None)==h for k,h in inputs.items()),'input drift'
        assert all(r4.digest(data/k)==h for k,h in gates.items()),'gate drift'
        for group in [inherited,prior,sources]:assert all(r4.digest(ROOT/k)==h for k,h in group.items()),'source/evidence drift'
    unchanged()
    hourly=pd.read_parquet(data/'coinbase/btc_hourly.parquet');g,_=r4.checked_grid(hourly,'h')
    base=pd.read_csv(OUT.parent/'r4/incumbent_replay_targets.csv',parse_dates=['date']).set_index('date').alloc_optimal
    index=pd.date_range(g.index[0],g.index[-1]+H,freq='h');maps={lag:r4.incumbent_targets(base,index,delay_hours=lag) for lag in [1,6]}
    saved=pd.read_csv(OUT.parent/'r4/downside_events.csv');anchors=pd.DatetimeIndex(pd.to_datetime(saved.loc[saved.rule=='d0','anchor'].unique())).sort_values()
    assert r4.onsets(r4.hourly_conditions(hourly).d0,step='1h',separation='24h').equals(anchors)
    record=[];events=[]
    for lag in [1,6]:
        f=clock_features(hourly,maps[lag]);f['lag_hours']=lag;f['entry']=f.issue+lag*H;f['end']=f.entry+24*H
        outcomes=[outcome(hourly,t) for t in f.entry]
        for k in ['y','category','barrier_hour']:f[k]=[v[k] for v in outcomes]
        record.append(f)
        for a in anchors:
            bi=a+H;entry=bi+lag*H;label=outcome(hourly,entry)
            events.append({'event_id':f'{lag}|{a}','anchor':a,'lag_hours':lag,'break_issue':bi,'entry':entry,'end':entry+24*H,
                           **label,'confirm':entry+(int(label['barrier_hour'])+1)*H if label['category']=='lower_first' else None})
        print('R9 clock/target pass',lag,len(f),flush=True)
    records=pd.concat(record,ignore_index=True);events=pd.DataFrame(events);events.confirm=pd.to_datetime(events.confirm)
    fits=[];pred=[]
    for lag,g in records.groupby('lag_hours'):
        for q in pd.date_range('2018-01-01','2026-07-01',freq='QS'):
            qe=q+pd.offsets.QuarterBegin(startingMonth=1);test=g.loc[(g.issue>=q)&(g.issue<qe)]
            if test.empty:continue
            fit=fit_watch(g,q);fid=f'{lag}|{q.date()}';fits.append(dict(id=fid,lag_hours=int(lag),quarter=str(q),fit=fit))
            for x in test.itertuples():
                status=x.watch_status if x.watch_status!='prebreak' else x.feature_status if x.feature_status!='ok' else fit['status']
                row={k:getattr(x,k) for k in ['anchor','issue','entry','end','lag_hours','watch_status','feature_status','y','category','barrier_hour']}
                row.update(row_id=x.Index,fit_id=fid,forecast_status=status,recent=None,price=None)
                if status=='ok':
                    row.update(recent=fit['recent_rate'],price=float(r6.predict(fit['model'],np.array([getattr(x,k) for k in FIELDS]))))
                pred.append(r6.finite_record(row))
        print('R9 chronological fit pass',lag,flush=True)
    preds=pd.DataFrame(pred)
    for k in ['issue','entry','end','anchor']:preds[k]=pd.to_datetime(preds[k])
    # Only the model object is passed to its original predictor.
    warnings=[]
    for lag,g in preds.groupby('lag_hours'):
        for model in MODELS:
            for ix in emit_warnings(g,model):
                x=preds.loc[ix];warnings.append(dict(x,warning_id=f'{lag}|{model}|{ix}',model=model,probability=float(x[model])))
    warnings=pd.DataFrame(warnings,columns=list(preds.columns)+['warning_id','model','probability'])
    for k in ['issue','entry','end','anchor']:warnings[k]=pd.to_datetime(warnings[k])
    events['supported']=False;events['eligible_watches']=0;matchrows=[]
    for lag,g in preds.groupby('lag_hours'):
        candidates=g.loc[g.forecast_status=='ok']
        for ix,e in events.loc[(events.lag_hours==lag)&events.category.eq('lower_first')].iterrows():
            can=candidates.loc[(candidates.issue<e.break_issue)&(candidates.issue>=e.break_issue-24*H)&(candidates.entry<e.break_issue)&(candidates.end>=e.confirm)]
            events.loc[ix,'supported']=len(can)>0;events.loc[ix,'eligible_watches']=len(can)
        es=events.loc[(events.lag_hours==lag)&events.category.eq('lower_first')]
        for model in MODELS:
            w=warnings.loc[(warnings.lag_hours==lag)&warnings.model.eq(model)]
            for m in match_events(w,es):matchrows.append(dict(m,warning_id=warnings.loc[m['warning_index'],'warning_id'],lag_hours=int(lag),model=model))
    matches=pd.DataFrame(matchrows,columns=['warning_index','event_id','lead_issue_h','lead_action_h','warning_id','lag_hours','model'])
    acc=[]
    for x in warnings.itertuples():
        for cost in [0,10,25]:
            d=warning_account(hourly,maps[x.lag_hours],x.entry,cost)
            acc.append(dict(warning_id=x.warning_id,issue=x.issue,anchor=x.issue,entry=x.entry,end=x.end,lag_hours=x.lag_hours,model=x.model,cost_bps=cost,**d))
    account_columns=['warning_id','issue','anchor','entry','end','lag_hours','model','cost_bps','status','inc_r','cash_r','inc_dd','cash_dd','inc_turnover','cash_turnover','initial_exposure','dr','dx','du']
    accounts=pd.DataFrame(acc,columns=account_columns)
    for k in ['issue','anchor','entry','end']:accounts[k]=pd.to_datetime(accounts[k])
    forecast,alarm,economic,monthly=summaries(records,preds,warnings,events,matches,accounts)
    unchanged()
    for name,f in [('clock_records',records),('predictions',preds),('warnings',warnings),('events',events),('event_matches',matches),('warning_accounts',accounts),('monthly_burden',monthly)]:f.to_csv(OUT/(name+'.csv'),index=False)
    result={'classification':'RETROSPECTIVE_FIXED_CLOCK_PREBREAK_RESEARCH_NOT_LIVE_WARNING','baseline':BASE,'plan_commit':PLAN,
        'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'inputs':inputs,'gates':gates,'prior_evidence':prior,'inherited_sources':inherited,'sources':sources,'unchanged':True,
        'counts':{'clock_rows':len(records),'fits':len(fits),'prediction_rows':len(preds),'warnings':len(warnings),'events':len(events),'matches':len(matches),'account_rows':len(accounts)},
        'fits':fits,'forecast_summaries':forecast,'alarm_summaries':alarm,'economic_summaries':economic,
        'constants':{'clock_hours':6,'prebreak_lookback_h':24,'threshold':.1,'horizon_h':24,'lower':-.05,'upper':.03,'min_n':1000,'min_positive':30,'min_negative':300,'half_life_d':365},
        'limitations':['Clock windows overlap; not independent trials. Warnings deduplicate prospectively, targets never select their issue.',
        'Prebreak uses past states only; eligible-hour months are exposure-adjusted, not total calendar months.',
        'Episode matching concerns the fixed D0 catalogue and requires action before break plus damage before warning expiry; it is not the primary price-path target.',
        'Hourly source timestamps and opens do not prove publication/execution parity; inherited data and signed-flow limits remain.',
        'All history repeatedly inspected; no untouched holdout or live policy change. Independent arithmetic is not independent review.']}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('R9_COMPLETE',json.dumps(result['counts']),flush=True)


if __name__=='__main__':main()
