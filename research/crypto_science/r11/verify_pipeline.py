"""R11 synthetic entry-to-store proof plus independent elapsed-window arithmetic.
No live HTTP, collector scheduling, source-data write or policy/gate update.
"""
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
from tempfile import TemporaryDirectory
import hashlib
import json
import math
import subprocess
import sys

import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from lib import config,store
from collectors import okx,bgeo,base,_crypto_observations as obs
from engine import btc_intraday_cvd as cvd
HERE=Path(__file__).resolve().parent


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def equal(x,y):
    if y is None:assert x is None,(x,y)
    else:assert math.isclose(float(x),float(y),rel_tol=1e-10,abs_tol=1e-10),(x,y)


class Response:
    status_code=200
    headers={}
    def __init__(self,url,data):
        self.url=url;self.data=data;self.content=json.dumps(data,separators=(',',':')).encode()
    def json(self):return json.loads(self.content)
    def raise_for_status(self):pass


def expected_window(h,clock):
    """Direct timestamp membership, not the engine's backwards segmentation."""
    clock=pd.Timestamp(clock).tz_convert('UTC').tz_localize(None)
    h=h.loc[h.index<=clock]
    last=h.index.max();observed={}
    for t,b,s in h[['taker_buy_vol','taker_sell_vol']].itertuples():
        if isinstance(b,(bool,np.bool_)) or isinstance(s,(bool,np.bool_)):continue
        if not np.isfinite([b,s]).all() or b<0 or s<0:continue
        observed[t]=(float(b),float(s))
    n=0;t=last
    while t in observed:n+=1;t-=pd.Timedelta(hours=1)
    out={'n_hours':n}
    for k in [24,72]:
        ix=[last-pd.Timedelta(hours=j) for j in range(k)]
        good=all(t in observed for t in ix)
        out[f'window_{k}h_complete']=good
        out[f'net_flow_{k}h_native']=sum(observed[t][0]-observed[t][1] for t in ix) if good else None
    if out['window_24h_complete']:
        b=sum(observed[last-pd.Timedelta(hours=j)][0] for j in range(24))
        s=sum(observed[last-pd.Timedelta(hours=j)][1] for j in range(24))
        out['buy_share_24h']=b/(b+s) if b+s else None
    else:out['buy_share_24h']=None
    return out


def main():
    target=HERE/'pipeline_proof.json'
    if target.exists():raise RuntimeError('Proof exists; verify/read back, do not overwrite it')
    prior=json.loads((HERE.parent/'r10/results.json').read_text());data=Path(config.data_dir())
    inputs={k:(digest(data/k) if (data/k).exists() else None) for k in prior['inputs']}
    gates={k:digest(data/k) for k in prior['gates']}
    assert inputs==prior['inputs'] and gates==prior['gates'],'Underlying data/gates changed before proof'
    untouched={k:digest(ROOT/k) for k in prior['prior_evidence']}
    assert untouched==prior['prior_evidence']
    source_paths=['collectors/_crypto_observations.py','collectors/_first_seen_store.py','collectors/okx.py',
                  'collectors/bgeo.py','engine/btc_intraday_cvd.py','scripts/build_vector.py',
                  'tests/test_crypto_collectors.py','tests/test_btc_intraday_cvd.py']
    sources={k:digest(ROOT/k) for k in source_paths}
    present={str(p.relative_to(data)):(digest(p) if p.exists() else None) for p in
             [data/'okx/source_observations.parquet',data/'bgeo/source_observations.parquet']}
    events=[];requests_seen=[];receipts=[]
    ix=pd.date_range('2026-01-01',periods=200,freq='h')
    flow=pd.DataFrame({'taker_buy_vol':2.,'taker_sell_vol':1.},index=ix)
    latest={'time':'2026-01-09T08:00:00Z','actual':'.00021'}
    def response(url,**kw):
        params=dict(kw['params']);requests_seen.append({'url':url,'params':params})
        if 'funding-rate-history' in url:
            val={'code':'0','data':[{'instId':'BTC-USDT-SWAP','instType':'SWAP',
                'fundingTime':'1767283200000','fundingRate':'.00020','realizedRate':latest['actual'],
                'method':'current_period','formulaType':'withRate'}]}
        elif 'taker-volume' in url:
            subset=flow if params['period']=='1H' else flow.iloc[-1:]
            val={'code':'0','data':[[str(int(t.value//10**6)),str(s),str(b)] for t,b,s in subset.itertuples()]}
        else:raise AssertionError('Unexpected endpoint; no network is available in this proof')
        return Response(url,val)
    with TemporaryDirectory(prefix='r11-proof-') as tmp,ExitStack() as stack:
        root=Path(tmp)
        stack.enter_context(patch.object(config,'data_dir',return_value=root))
        stack.enter_context(patch.object(obs,'now_utc',side_effect=lambda:latest['time']))
        stack.enter_context(patch.object(okx,'MAX_PAGES_FIRST_RUN',1))
        stack.enter_context(patch.object(okx.time,'sleep',lambda _:None))
        a=okx.OkxAdapter();a.http_get=response
        for name in ['_open_interest','_ls_account_ratio']:
            stack.enter_context(patch.object(a,name,return_value=None))
        stack.enter_context(patch.object(a,'_spot_candles',return_value=None))
        before=a._funding(False);plain_requests=list(requests_seen);requests_seen.clear()
        assert not obs.capture_path('okx_funding').exists()
        run_states=[]
        for time,actual in [('2026-01-09T08:00:00Z','.00021'),('2026-01-09T09:00:00Z','.00031'),
                            ('2026-01-09T10:00:00Z','.00021'),('2026-01-09T10:00:00Z','.00021')]:
            latest.update(time=time,actual=actual)
            result=base.run_adapter(a,stale_after_days=10000)
            assert result.status=='ok'
            pd.testing.assert_frame_equal(store.read('okx','funding_rate'),before,check_freq=False)
            captured=obs.load_asof('okx_funding','2026-01-10T00:00:00Z')
            run_states.append({'received_at':time,'capture_count':len(captured),'statuses':list(a.source_capture_status)})
        assert [r['capture_count'] for r in run_states]==[1,2,3,3]
        rows=obs.load_asof('okx_funding','2026-01-10T00:00:00Z')
        for time,expected in [('2026-01-09T07:59:00Z',None),('2026-01-09T08:30:00Z',.00021),
                              ('2026-01-09T09:30:00Z',.00031),('2026-01-09T10:30:00Z',.00021)]:
            view=obs.funding_asof(rows,time)
            if expected is None:assert not view
            else:
                equal(view[0]['settled_rate'],expected);equal(view[0]['predicted_rate'],.0002)
                assert view[0]['interval_hours'] is None and view[0]['annualized_settled_pct'] is None
            events.append({'as_of':time,'event':view})
        for row in obs.fss.read_store(obs.capture_path('okx_funding'),obs.COLUMNS).to_dict('records'):
            # Re-express the JSON and hash contract rather than calling checked().
            material={k:row[k] for k in obs.COLUMNS if k!='capture_id'}
            for k,v in list(material.items()):
                if isinstance(v,float) and math.isnan(v):material[k]=None
            raw=json.dumps(material,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
            assert hashlib.sha256(raw.encode()).hexdigest()==row['capture_id']
            assert hashlib.sha256(row['payload_json'].encode()).hexdigest()==row['payload_sha256']
            assert row['received_at']==row['first_seen']==row['fetched_at']
            assert row['provider_first_published_at'] is None
            receipts.append({'capture_id':row['capture_id'],'source_id':row['source_id'],
                             'received_at':row['received_at'],'payload_sha256':row['payload_sha256']})
        assert len(receipts)==9
        first_count=len(requests_seen)
        path=obs.capture_path('okx_funding');original=path.read_bytes()
        with patch.object(obs,'persist_capture',return_value={'status':'unavailable','error_type':'OSError'}):
            result=base.run_adapter(a,stale_after_days=10000)
        assert result.status=='stale' and path.read_bytes()==original
        pd.testing.assert_frame_equal(store.read('okx','funding_rate'),before,check_freq=False)
        assert len(requests_seen)==first_count+3
        # BGeometrics receives exactly one normal response; no extra HTTP calls.
        bg=[{'d':'2026-01-08T16:00:00Z','unixTs':'1767888000','fundingRate':'-.0001',
             'markPrice':90000,'delayed':True,'message':'synthetic delayed response'}]
        bgcalls=[]
        def bgget(url,**kw):bgcalls.append(kw['params']);return Response(url,bg)
        stack.enter_context(patch.object(bgeo.requests,'get',side_effect=bgget))
        b=bgeo.BgeoAdapter();b.cfg={**b.cfg,'metrics':{'funding-rate':'funding_rate'}}
        plain=b._fetch_metric('funding-rate','funding_rate',b.cfg['window_start']);bgcalls.clear()
        bout=b.fetch();pd.testing.assert_frame_equal(plain,bout['funding_rate']);assert len(bgcalls)==1
        br=obs.load_asof('bgeo_funding','2026-01-10T00:00:00Z');assert len(br)==1
        value=json.loads(br.iloc[0].payload_json)[0]
        assert value['d']==bg[0]['d'] and value['unixTs']==bg[0]['unixTs'] and value['delayed'] is True
        assert value['message']==bg[0]['message']
        print('R11 fake public fetch -> normal numerical storage + keep-first evidence -> as-of revisions verified',flush=True)
    # Distinct scalar/index-membership calculation over complete, gapped,
    # invalid and zero-activity histories. Labels are not claimed publication.
    window_cases=[]
    bad=flow.copy();bad.iloc[-1,0]=np.nan
    zero=flow*0;balanced=flow.copy();balanced['taker_buy_vol']=1.
    samples={'complete':flow,'late_gap':flow.drop(ix[-20]),'earlier_gap':flow.drop(ix[50]),
             'invalid_tail':bad,'zero_activity':zero,'balanced':balanced}
    for name,h in samples.items():
        for hour in [22,23,24,70,71,100,190,199,253]:
            at=(ix[0]+pd.Timedelta(hours=hour)).tz_localize('UTC')
            px=pd.DataFrame({'close':100.},index=ix)
            with patch.object(cvd.store,'read',side_effect=lambda group,nm:h.copy() if group=='okx' else px.copy()):
                actual=cvd.compute(as_of=at)
            expected=expected_window(h,at)
            for k,v in expected.items():
                if isinstance(v,bool):assert actual[k] is v,(name,hour,k,actual[k],v)
                else:equal(actual[k],v)
            assert actual['ok']==(expected['n_hours']>=24)
            assert actual['causally_qualified'] is False and actual['volume_unit'] is None
            assert actual['net_flow_24h_mn'] is None and actual['cvd_last_bn'] is None
            if hour==253:assert actual['stale'] and actual['flow_state']=='unavailable'
            window_cases.append({'case':name,'clock':str(at),'expected':expected,'stale':actual['stale']})
    stored=store.read('okx','taker_volume_hourly');cut=stored.index[-1].tz_localize('UTC')
    actual=cvd.compute(as_of=cut);expected=expected_window(stored,cut)
    for k,v in expected.items():
        if isinstance(v,bool):assert actual[k] is v
        else:equal(actual[k],v)
    old_snapshot=cvd.compute(as_of='2026-09-29T12:00:00Z')
    assert old_snapshot['stale'] and old_snapshot['hours_behind_ref']==0.
    assert old_snapshot['flow_state']=='unavailable'
    result={'classification':'SOURCE_REPAIR_SYNTHETIC_PIPELINE_NOT_LIVE_COLLECTION_OR_ALPHA',
            'implementation_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'sources':sources,'inputs':inputs,'gates':gates,'prior_evidence':untouched,
            'old_live_observation_files':present,
            'okx_runs':run_states,'asof_cases':events,'capture_digests':receipts,
            'request_count':len(requests_seen),'request_signature':requests_seen[:3],
            'bgeo_public_fetch_requests':1,'failure_retains_numerics_and_reports_stale':True,
            'elapsed_cases':window_cases,'stored_snapshot_check':expected,
            'stored_snapshot_clock_staleness':{'as_of':'2026-09-29T12:00:00Z','hours_behind_clock':old_snapshot['hours_behind_clock'],
                                             'hours_behind_ref':old_snapshot['hours_behind_ref'],'stale':True},
            'limits':['All HTTP responses in adapter integration were synthetic; no provider API request or new live collection.',
                      'First received means this collector received this response, not provider first publication or causal proof.',
                      'Actual stored-history check is a source arithmetic diagnostic, not a rerun of forecasts or PnL.',
                      'Same-session separate arithmetic; independent code/science review and live deployment remain open.']}
    assert all((digest(data/k) if (data/k).exists() else None)==h for k,h in inputs.items())
    assert all(digest(data/k)==h for k,h in gates.items())
    assert all(digest(ROOT/k)==h for k,h in untouched.items())
    assert all(digest(ROOT/k)==h for k,h in sources.items())
    assert all((digest(data/k) if (data/k).exists() else None)==h for k,h in present.items())
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('R11_PIPELINE_VERIFIED: normal adapter entry/storage; 9 receipt identities; 4 as-of views; 54 elapsed cases; 2 stored snapshot checks; failure status; no live data writes.')
    print('R11_HASHES: 57 inputs,18 gates,137 prior artifacts and all candidate source identities unchanged during proof.')


if __name__=='__main__':main()
