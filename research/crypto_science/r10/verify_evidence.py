"""Independent R10 index-membership and arithmetic checks, same-session review."""
from pathlib import Path
import hashlib,json,subprocess,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config
HERE=Path(__file__).resolve().parent
H=pd.Timedelta(hours=1)
COLS=['taker_buy_vol','taker_sell_vol']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def equal(a,b):
    if a is None or pd.isna(a):assert b is None or pd.isna(b),(a,b)
    else:assert np.isclose(a,b,rtol=1e-10,atol=1e-10),(a,b)


def main():
    r=json.loads((HERE/'results.json').read_text());old=json.loads((HERE/'initial/results.json').read_text());data=Path(config.data_dir())
    assert r['plan_commit']=='38b8f6d2f2580730993e81de95ef1b7fa34e2a14'
    for key in ['inputs','gates']:
        for p,h in r[key].items():assert (sha(data/p) if (data/p).exists() else None)==h,(key,p)
    for key in ['prior_evidence','inherited_sources','sources']:
        for p,h in r[key].items():assert sha(ROOT/p)==h,(key,p)
    assert sha(HERE/'initial/r10_source_qualification.py')==old['sources']['research/crypto_science/r10_source_qualification.py']
    assert sha(HERE/'initial/test_btc_impulse_falsifier.py.txt')==old['sources']['tests/test_btc_impulse_falsifier.py']
    assert (ROOT/'tests/test_btc_impulse_falsifier.py').read_bytes().startswith(subprocess.check_output(['git','show',r['baseline']+':tests/test_btc_impulse_falsifier.py'],cwd=ROOT))
    for key in ['census','flow_grid','row_vs_elapsed','r9_coverage_scenarios','strict_qualification','current_display_snapshot','funding_field_overlap','synthetic_gap_probe','offline_collector_probe']:
        assert r[key]==old[key],('amendment changed real-data result',key)
    for name in ['flow_gaps.csv','flow_window_validity.csv','r9_clock_coverage.csv']:
        assert (HERE/name).read_bytes()==(HERE/'initial'/name).read_bytes(),name
    frames={p:pd.read_parquet(data/p) for p in r['census']}
    for p,f in frames.items():
        c=r['census'][p];ix=pd.DatetimeIndex(f.index)
        assert c['rows']==len(f) and c['columns']==list(f)
        assert c['first']==str(ix.min()) and c['last']==str(ix.max())
        assert c['duplicate_labels']==sum(ix.duplicated()) and c['off_hour_labels']==sum(ix!=ix.floor('h'))
        equal(c['max_label_gap_hours'],max((b-a).total_seconds()/3600 for a,b in zip(ix[:-1],ix[1:])))
        assert c['metadata_keys']==sorted(map(str,f.attrs))
        for col,z in c['fields'].items():
            v=pd.to_numeric(f[col],errors='coerce');ok=np.isfinite(v)
            assert z['nonnull']==v.notna().sum() and z['finite']==ok.sum()
            assert z['zero']==sum(v[ok]==0) and z['negative']==sum(v[ok]<0)
            assert z['first_valid']==(str(v[ok].index.min()) if ok.any() else None)
            assert z['last_valid']==(str(v[ok].index.max()) if ok.any() else None)
    f=frames['okx/taker_volume_hourly.parquet'];ix=f.index
    values={t:(float(b),float(s)) for t,b,s in zip(ix,f[COLS[0]],f[COLS[1]]) if np.isfinite([b,s]).all() and b>=0 and s>=0}
    grid=pd.date_range(ix.min(),ix.max(),freq='h');runs=[];n=0
    for t in grid:
        if t in values:n+=1
        elif n:runs.append(n);n=0
    if n:runs.append(n)
    c=r['flow_grid'];assert c['grid_hours']==len(grid) and c['missing_hours']==len(set(grid)-set(ix))
    assert c['invalid_or_missing_hours']==len(grid)-len(values) and c['max_contiguous_valid_hours']==max(runs) and c['continuous_runs']==len(runs)
    expected_gaps=[]
    for a,b in zip(ix[:-1],ix[1:]):
        if b-a>H:expected_gaps.append({'after':str(a),'before':str(b),'missing_hours':int((b-a)/H)-1})
    gaps=pd.read_csv(HERE/'flow_gaps.csv').to_dict('records')
    assert gaps==expected_gaps and len(gaps)==c['gap_events']
    w=pd.read_csv(HERE/'flow_window_validity.csv');checked=0
    def member(last,hours):
        idx=[last-j*H for j in range(hours)]
        if any(t not in values for t in idx):return False,None,None
        buy=sum(values[t][0] for t in idx);sell=sum(values[t][1] for t in idx)
        return True,buy-sell,buy+sell
    for x in w.itertuples():
        good,net,gross=member(pd.Timestamp(x.label),x.hours);assert bool(x.complete)==good
        equal(net,x.net_provider_units);equal(gross,x.gross_provider_units);checked+=1
    for hours in [24,72]:
        spans=[int((b-a)/H)+1 for a,b in zip(ix[:-hours+1],ix[hours-1:])];v=r['row_vs_elapsed'][str(hours)]
        assert v['row_windows']==len(spans) and v['bridged_gap_windows']==sum(x>hours for x in spans)
        equal(v['max_covered_hours'],max(spans));equal(v['last_row_window_covered_hours'],spans[-1])
        assert v['last_exact_window_complete']==member(ix[-1],hours)[0]
        assert v['strict_grid_complete_windows']==sum(member(t,hours)[0] for t in grid)
    clocks=pd.read_csv(HERE/'r9_clock_coverage.csv');clocks.issue=pd.to_datetime(clocks.issue)
    ref=pd.read_csv(HERE.parent/'r9/clock_records.csv',usecols=['issue','lag_hours','watch_status','feature_status']);ref=ref.loc[ref.lag_hours==1]
    assert clocks.issue.astype(str).tolist()==pd.to_datetime(ref.issue).astype(str).tolist()
    base=pd.read_csv(HERE.parent/'r9/predictions.csv',usecols=['issue','lag_hours','forecast_status']);base=base.loc[base.lag_hours==1];base.issue=pd.to_datetime(base.issue)
    status=dict(zip(base.issue,base.forecast_status));goodclocks=np.array([status.get(t)=='ok' for t in clocks.issue])
    count=0
    for s in r['r9_coverage_scenarios']:
        label=s['label_assumption'];lag=s['additional_delay_hours'];hours=s['window_hours'];key=f'{label}_lag{lag}_h{hours}'
        results=[]
        for t in clocks.issue:
            last=t-lag*H-(H if label=='start' else 0*H)
            results.append(False if last<ix[0] or last>ix[-1] else member(last,hours)[0])
        results=np.array(results);assert np.array_equal(results,clocks[key].to_numpy())
        assert s['clock_count']==len(clocks) and s['mechanically_complete_clocks']==results.sum()
        assert s['r9_forecast_qualified_clocks']==goodclocks.sum() and s['overlap_mechanical_and_r9']==sum(results&goodclocks)
        assert s['causally_qualified_clocks']==0;count+=len(clocks)
    q=r['strict_qualification'];assert not q['causally_usable'] and q['mechanically_complete']
    assert set(q['reasons'])=={'unit_unverified','timestamp_role_unverified','contract_unverified','finality_unverified','vintage_unverified','first_available_missing'}
    # Verify original display arithmetic without calling its implementation.
    delta=f[COLS[0]]-f[COLS[1]];d=r['current_display_snapshot']
    equal(round(delta.tail(24).sum()/1e6,1),d['net_flow_24h_mn']);equal(round(delta.tail(72).sum()/1e6,1),d['net_flow_72h_mn'])
    equal(round(delta.sum()/1e9,3),d['cvd_last_bn']);assert d['n_hours']==len(f)
    assert d['gap_detected']==any((b-a)/H>720 for a,b in zip(ix[:-1],ix[1:]))
    px=pd.read_parquet(data/'coinbase/btc_hourly.parquet');behind=round((px.index.max()-ix[-1])/H,1)
    equal(behind,d['hours_behind_ref']);assert d['stale']==(behind>48)
    funding=frames['bgeo/funding_rate.parquet'];both=funding[['funding_rate','funding_rate_fundingRate']].dropna();o=r['funding_field_overlap'][0]
    assert o['overlap_rows']==len(both) and o['equal_numeric_rows']==np.isclose(both.iloc[:,0],both.iloc[:,1]).sum()
    probe=r['offline_collector_probe'];equal(probe['okx_daily_predicted_mean'],(.0001+.0002+.0003)/3);equal(probe['actual_settlement_mean'],(.00011+.00021+.00031)/3)
    assert probe['last_settlement']=='2026-01-01 16:00:00' and probe['okx_date_label']=='2026-01-01 00:00:00'
    assert probe['okx_retained_columns']==['funding_rate_okx'] and probe['bgeo_retained_unix_timestamp'] is False and probe['bgeo_delay_value']==1
    print('R10_VERIFIED:',len(frames),'source frames;',checked,'elapsed-window rows;',count,'clock-convention masks; funding projections and inherited-display arithmetic checked.')
    print('R10_AMENDMENT: all real-data findings equal; three derived CSVs byte-identical. Impossible-receipt repair affects synthetic qualification only.')
    print('R10_HASHES:',len(r['inputs']),'input identities;',len(r['gates']),'gates;',len(r['prior_evidence']),'prior evidence; inherited sources unchanged. Same-session arithmetic, not independent researcher approval.')


if __name__=='__main__':main()
