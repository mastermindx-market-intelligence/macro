"""R10 research-only source/clock qualifier. No provider or production writes."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
H=pd.Timedelta(hours=1)
COLS=['taker_buy_vol','taker_sell_vol']
OUT=Path(__file__).with_name('r10')
BASE='d636e9c405c0283209eb75b09d477d32003ff827'
PLAN='38b8f6d2f2580730993e81de95ef1b7fa34e2a14'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def number(x):
    if isinstance(x,(bool,np.bool_)):return None
    try:v=float(x)
    except (TypeError,ValueError,OverflowError):return None
    return v if np.isfinite(v) else None


def checked(frame):
    if not isinstance(frame.index,pd.DatetimeIndex) or frame.index.tz is not None:
        raise ValueError('Require naive UTC timestamps')
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing or not frame.index.equals(frame.index.floor('h')):
        raise ValueError('Require ordered unique hourly labels')
    if not set(COLS).issubset(frame):raise ValueError('Both original aggressor fields required')


def flow_window(frame,as_of,hours,label,delay_hours=0):
    checked(frame);a=pd.Timestamp(as_of)
    if a.tz is not None or a!=a.floor('h') or hours not in (24,72) or label not in ('start','end') or delay_hours not in (0,1):
        raise ValueError('Undeclared timing convention/window')
    end=a-delay_hours*H;start=end-hours*H
    idx=pd.date_range(start+(H if label=='end' else 0*H),periods=hours,freq='h')
    f=frame.reindex(idx)[COLS].apply(pd.to_numeric,errors='coerce')
    valid=np.isfinite(f).all(axis=1)&f.ge(0).all(axis=1)
    good=bool(valid.all())
    out={'status':'ok' if good else 'incomplete','as_of':str(a),'label':label,'delay_hours':delay_hours,
         'window_start':str(start),'window_end':str(end),'hours':hours,'missing_hours':int((~valid).sum()),
         'net_units':None,'gross_units':None,'imbalance':None,'buy_share':None,'volume_unit':'UNQUALIFIED_PROVIDER_UNIT'}
    if good:
        buy=float(f[COLS[0]].sum());sell=float(f[COLS[1]].sum());gross=buy+sell
        out.update(net_units=buy-sell,gross_units=gross,imbalance=(buy-sell)/gross if gross>0 else None,buy_share=buy/gross if gross>0 else None)
    return out


def qualification(window,contract,first_available_at):
    """Eligibility under SUPPLIED evidence, never authority to promote a source."""
    reasons=[]
    if window['status']!='ok':reasons.append('window_incomplete')
    if contract.get('scope')!='OKX/BTC/CONTRACTS':reasons.append('scope_unverified')
    if contract.get('unit') not in ('USD','BTC','CONTRACTS'):reasons.append('unit_unverified')
    if contract.get('label')!=window['label']:reasons.append('timestamp_role_unverified')
    for k in ['contract_verified','finality_verified','vintage_verified']:
        if contract.get(k) is not True:reasons.append(k.replace('_verified','_unverified'))
    if first_available_at is None:reasons.append('first_available_missing')
    else:
        stamp=pd.Timestamp(first_available_at)
        if pd.isna(stamp) or stamp.tz is not None:reasons.append('first_available_invalid')
        elif stamp>pd.Timestamp(window['as_of']) or pd.Timestamp(window['window_end'])>pd.Timestamp(window['as_of']):reasons.append('not_yet_available')
    return {'mechanically_complete':window['status']=='ok','causally_usable':not reasons,'reasons':reasons,
            'meaning':'Conditional research eligibility; supplied flags are not an independent review or live admission.'}


def funding_event(raw,received_at,interval_hours=None):
    if raw.get('instId')!='BTC-USDT-SWAP':raise ValueError('Exact configured instrument required')
    t=pd.Timestamp(pd.to_datetime(int(raw['fundingTime']),unit='ms'))
    rec=pd.Timestamp(received_at) if received_at is not None else None
    if rec is not None and (pd.isna(rec) or rec.tz is not None):raise ValueError('Require valid naive UTC receipt')
    interval=number(interval_hours)
    if interval is not None and interval<=0:raise ValueError('Positive separately evidenced settlement interval required')
    expected=number(raw.get('fundingRate'));actual=number(raw.get('realizedRate'))
    observed=bool(actual is not None and rec is not None and rec>=t)
    return {'instrument':raw['instId'],'settlement_time':str(t),'received_at':str(rec) if rec is not None else None,
            'available_at':str(max(t,rec)) if observed else None,'expected_rate':expected,'settled_rate':actual,
            'settled_observed':observed,'interval_hours':interval,'method':raw.get('method'),'formula_type':raw.get('formulaType'),
            'settled_simple_annualized':actual*24/interval*365 if observed and interval is not None else None,
            'limit':'Annualization is a fraction-rate arithmetic convention, not expected return; interval evidence must be supplied separately.'}


def legacy_gap_example():
    from engine import btc_intraday_cvd as cvd
    ix=pd.date_range('2026-01-01',periods=25,freq='h').delete(12)
    f=pd.DataFrame({COLS[0]:2.,COLS[1]:1.},index=ix)
    def read(g,n):
        if (g,n)==('okx','taker_volume_hourly'):return f.copy()
        if (g,n)==('coinbase','btc_hourly'):return pd.DataFrame({'close':[100.]},index=ix[-1:])
        raise AssertionError('Unexpected source')
    with patch.object(cvd.store,'read',side_effect=read):old=cvd.compute()
    strict=flow_window(f,ix[-1]+H,24,'start')
    return {'classification':'OFFLINE_SYNTHETIC_REPRODUCTION_NOT_LIVE_MARKET','stored_rows':len(f),
            'covered_elapsed_hours':int((ix[-1]-ix[0])/H)+1,'incumbent_gap_detected':old['gap_detected'],
            'incumbent_ok':old['ok'],'incumbent_net_units':24.,'strict_window_status':strict['status']}


def collector_probe():
    from collectors import okx,bgeo
    t=pd.Timestamp('2026-01-01')
    rows=[{'instId':'BTC-USDT-SWAP','fundingTime':str((t+i*H).value//10**6),'fundingRate':str(v),
           'realizedRate':str(v+.00001),'formulaType':'withRate','method':'current_period'} for i,v in [(0,.0001),(8,.0002),(16,.0003)]]
    class Response:
        headers={};status_code=200
        def __init__(self,data):self.data=data
        def json(self):return self.data
        def raise_for_status(self):return None
    obj=object.__new__(okx.OkxAdapter);obj.cfg={'inst_id':'BTC-USDT-SWAP','funding_url':'https://example.invalid/funding','retries':0}
    with patch.object(obj,'http_get',side_effect=[Response({'data':rows}),Response({'data':[]})]) as fetch, patch.object(okx.store,'last_date',return_value=None),patch.object(okx.time,'sleep'):
        f=obj._funding(False);assert fetch.call_count==2
    bg=object.__new__(bgeo.BgeoAdapter);bg.cfg={'base_url':'https://example.invalid','page_size':10}
    sample=[{'d':'2026-01-01T16:00:00Z','unixTs':str((t+16*H).value//10**6),'fundingRate':'.0003','markPrice':100.,'delayed':True,'message':'delayed fixture'}]
    with patch.object(bgeo.requests,'get',return_value=Response(sample)) as req,patch.object(bgeo.config,'load',return_value={'sponsors':{'user_agent':'offline-research'}}),patch.object(bgeo.time,'sleep'):
        b=bg._fetch_metric('funding-rate','funding_rate','2026-01-01');assert req.call_count==1
    return {'classification':'OFFLINE_FAKE_HTTP_NO_PROVIDER_CALL','okx_daily_predicted_mean':float(f.iloc[0,0]),
            'actual_settlement_mean':float(np.mean([float(x['realizedRate']) for x in rows])),
            'okx_retained_columns':list(f),'okx_date_label':str(f.index[0]),'last_settlement':str(t+16*H),
            'bgeo_retained_columns':list(b),'bgeo_retained_unix_timestamp':any('unix' in c.lower() for c in b),
            'bgeo_date_label':str(b.index[0]),'bgeo_delay_value':int(b.funding_rate_delayed.iloc[0])}


def frame_census(frame):
    index=pd.DatetimeIndex(frame.index);gaps=index.to_series().diff()/H
    fields={}
    for c in frame:
        v=pd.to_numeric(frame[c],errors='coerce');nz=v.loc[np.isfinite(v)]
        fields[c]={'nonnull':int(v.notna().sum()),'finite':len(nz),'zero':int((nz==0).sum()),'negative':int((nz<0).sum()),
                   'first_valid':str(nz.index.min()) if len(nz) else None,'last_valid':str(nz.index.max()) if len(nz) else None}
    return {'rows':len(frame),'first':str(index.min()),'last':str(index.max()),'columns':list(frame),
            'duplicate_labels':int(index.duplicated().sum()),'off_hour_labels':int((index!=index.floor('h')).sum()),
            'max_label_gap_hours':number(gaps.max()),'fields':fields,
            'metadata_keys':sorted(map(str,frame.attrs))}


def main():
    from lib import config,store
    from engine import btc_intraday_cvd
    OUT.mkdir(exist_ok=True)
    if (OUT/'results.json').exists():raise RuntimeError('R10 result exists: reconcile, do not overwrite')
    r9=OUT.parent/'r9';r=json.loads((r9/'results.json').read_text());data=Path(config.data_dir())
    inputs=dict(r['inputs']);gates=r['gates']
    for p in ['okx/funding_rate.parquet','okx/open_interest.parquet']:
        inputs[p]=sha(data/p) if (data/p).exists() else None
    source={**r['inherited_sources'],**{k:v for k,v in r['sources'].items() if k!='tests/test_btc_impulse_falsifier.py'}}
    for p in ['collectors/okx.py','collectors/bgeo.py','engine/btc_intraday_cvd.py','lib/store.py','collectors/base.py','config.yml']:
        source[p]=sha(ROOT/p)
    prior={**r['prior_evidence'],**{str(p.relative_to(ROOT)):sha(p) for p in r9.iterdir() if p.is_file()}}
    names=['research/crypto_science/r10_source_qualification.py','research/CRYPTO_SCIENCE_R10_SOURCE_QUALIFICATION_PLAN_2026-09-29.md','tests/test_btc_impulse_falsifier.py']
    own={p:sha(ROOT/p) for p in names}
    assert (ROOT/names[-1]).read_bytes().startswith(subprocess.check_output(['git','show',BASE+':'+names[-1]],cwd=ROOT))
    def guard():
        assert all((sha(data/p) if (data/p).exists() else None)==h for p,h in inputs.items()),'data drift'
        assert all(sha(data/p)==h for p,h in gates.items()),'gate drift'
        for g in [source,prior,own]:assert all(sha(ROOT/p)==h for p,h in g.items()),'source/evidence drift'
    guard()
    paths=['okx/taker_volume_hourly.parquet','okx/taker_volume.parquet','okx/funding_rate.parquet','bgeo/funding_rate.parquet','okx/open_interest.parquet']
    frames={p:pd.read_parquet(data/p) for p in paths if (data/p).exists()}
    census={p:frame_census(f) for p,f in frames.items()}
    flow=frames[paths[0]];checked(flow);full=pd.date_range(flow.index[0],flow.index[-1],freq='h')
    g=flow[COLS].apply(pd.to_numeric,errors='coerce').reindex(full)
    valid=np.isfinite(g).all(axis=1)&g.ge(0).all(axis=1)
    seg=(~valid).cumsum();runs=[int(v.sum()) for _,v in valid.groupby(seg) if v.any()]
    missing=full.difference(flow.index);gap_rows=[]
    for last,gap in (flow.index.to_series().diff()/H).items():
        if pd.notna(gap) and gap>1:gap_rows.append({'after':str(last-gap*H),'before':str(last),'missing_hours':int(gap-1)})
    row_summary={};window_rows=[]
    # Rolling on an explicit hourly grid, never on sparse observation counts.
    for hours in [24,72]:
        complete=valid.astype(int).rolling(hours,min_periods=hours).sum().eq(hours)
        totals=g.where(valid).sum(axis=1,min_count=2).rolling(hours,min_periods=hours).sum()
        net=(g[COLS[0]]-g[COLS[1]]).where(valid).rolling(hours,min_periods=hours).sum()
        ix=flow.index;spans=(ix[hours-1:]-ix[:len(ix)-hours+1])/H+1
        counted=flow[COLS].tail(hours);last_span=float((counted.index[-1]-counted.index[0])/H+1)
        row_summary[str(hours)]={'row_windows':len(spans),'bridged_gap_windows':int((spans>hours).sum()),'max_covered_hours':float(max(spans)),
                                 'last_row_window_covered_hours':last_span,'last_exact_window_complete':bool(complete.iloc[-1]),
                                 'strict_grid_complete_windows':int(complete.sum())}
        for t in ix:
            window_rows.append({'label':str(t),'hours':hours,'complete':bool(complete.loc[t]),
                                'net_provider_units':number(net.loc[t]) if complete.loc[t] else None,
                                'gross_provider_units':number(totals.loc[t]) if complete.loc[t] else None})
    clocks=pd.read_csv(r9/'clock_records.csv',usecols=['issue','lag_hours','watch_status','feature_status'])
    clocks=clocks.loc[clocks.lag_hours==1].copy();clocks.issue=pd.to_datetime(clocks.issue)
    preds=pd.read_csv(r9/'predictions.csv',usecols=['issue','lag_hours','forecast_status'])
    preds=preds.loc[preds.lag_hours==1].copy();preds.issue=pd.to_datetime(preds.issue)
    clocks=clocks.merge(preds[['issue','forecast_status']],on='issue',how='left',validate='one_to_one')
    summaries=[]
    for label in ['start','end']:
        for delay in [0,1]:
            for hours in [24,72]:
                key=f'{label}_lag{delay}_h{hours}';end=clocks.issue-delay*H;last=end-(H if label=='start' else 0*H)
                rolling=valid.astype(int).rolling(hours,min_periods=hours).sum().eq(hours)
                matches=rolling.reindex(pd.DatetimeIndex(last)).fillna(False).to_numpy(bool)
                clocks[key]=matches
                supported=clocks.forecast_status.eq('ok')
                summaries.append({'label_assumption':label,'additional_delay_hours':delay,'window_hours':hours,'clock_count':len(clocks),
                                  'mechanically_complete_clocks':int(matches.sum()),'r9_forecast_qualified_clocks':int(supported.sum()),
                                  'overlap_mechanical_and_r9':int((matches&supported).sum()),'causally_qualified_clocks':0})
    contract={'scope':'OKX/BTC/CONTRACTS','unit':None,'label':None,'contract_verified':False,'finality_verified':False,'vintage_verified':False}
    last=flow_window(flow,flow.index[-1]+H,24,'start')
    strict=qualification(last,contract,None)
    current=btc_intraday_cvd.compute();keep=['ok','asof','n_hours','stale','hours_behind_ref','gap_detected','accruing','flow_state','net_flow_24h_mn','net_flow_72h_mn','cvd_last_bn']
    observed={k:current.get(k) for k in keep};observed['scope']='Stored snapshot display output, not a live market or qualified flow statement'
    # Exact field overlap is a compatibility diagnostic, NOT an economic association.
    bg=frames['bgeo/funding_rate.parquet'];cols=list(bg);overlap=[]
    for a in cols:
        for b in cols:
            if a>=b or a not in ['funding_rate','funding_rate_fundingRate'] or b not in ['funding_rate','funding_rate_fundingRate']:continue
            z=bg[[a,b]].dropna();overlap.append({'left':a,'right':b,'overlap_rows':len(z),'equal_numeric_rows':int(np.isclose(z[a],z[b]).sum())})
    guard()
    pd.DataFrame(gap_rows).to_csv(OUT/'flow_gaps.csv',index=False)
    pd.DataFrame(window_rows).to_csv(OUT/'flow_window_validity.csv',index=False)
    clocks.to_csv(OUT/'r9_clock_coverage.csv',index=False)
    result={'classification':'SOURCE_QUALIFICATION_DIAGNOSTIC_NOT_ALPHA_STUDY','baseline':BASE,'plan_commit':PLAN,
            'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'inputs':inputs,'gates':gates,'inherited_sources':source,'prior_evidence':prior,'sources':own,'unchanged':True,
            'census':census,'flow_grid':{'rows':len(flow),'grid_hours':len(full),'missing_hours':len(missing),
                                      'invalid_or_missing_hours':int((~valid).sum()),'gap_events':len(gap_rows),
                                      'max_contiguous_valid_hours':max(runs),'continuous_runs':len(runs)},
            'row_vs_elapsed':row_summary,'r9_coverage_scenarios':summaries,
            'supplied_contract':contract,'strict_qualification':strict,'current_display_snapshot':observed,
            'funding_field_overlap':overlap,'synthetic_gap_probe':legacy_gap_example(),'offline_collector_probe':collector_probe(),
            'limits':['No new future labels, returns, PnL, calibration or forecast fit were inspected/computed.',
                      'Clock coverage under start/end and zero/one-hour delay is hypothetical timing sensitivity, not a historical publish receipt.',
                      'Observed provider schema has no unit or bucket-start/end guarantee for aggregate taker volume.',
                      'Funding predicted/settled fields and timestamp loss are reproduced offline; no live data request or source write.']}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['flow_grid','row_vs_elapsed','r9_coverage_scenarios','strict_qualification','funding_field_overlap','offline_collector_probe']},indent=2))


if __name__=='__main__':main()
