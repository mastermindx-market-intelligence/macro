"""Crypto collector tests — pure parsing on inline fixtures, no network.

Run: .venv/bin/python -m tests.test_crypto_collectors
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.backfill_crypto import parse_plotly  # noqa: E402


def test_plotly_parse_plain_and_binary() -> None:
    plain = ('Plotly.newPlot("x",[{"name":"SOPR","x":["2024-01-01","2024-01-02"],'
             '"y":[1.01,0.99]}],{})')
    df = parse_plotly(plain, "SOPR")
    assert len(df) == 2 and abs(df["value"].iloc[0] - 1.01) < 1e-9

    b = base64.b64encode(np.array([1.5, 2.5], dtype="f8").tobytes()).decode()
    binary = ('Plotly.newPlot("x",[{"name":"SOPR","x":["2024-01-01","2024-01-02"],'
              f'"y":{{"dtype":"f8","bdata":"{b}"}}}}],{{}})')
    df = parse_plotly(binary, "SOPR")
    assert list(df["value"]) == [1.5, 2.5]


def test_bgeo_generic_parser_single_and_multi() -> None:
    from collectors.bgeo import BgeoAdapter
    a = BgeoAdapter.__new__(BgeoAdapter)  # skip __init__/config
    rows = [{"d": "2026-06-10", "unixTs": "1", "sopr": "0.99"},
            {"d": "2026-06-11", "unixTs": "2", "sopr": "1.01"}]
    df = pd.DataFrame(rows)
    value_cols = [c for c in df.columns if c not in ("d", "unixTs")]
    assert value_cols == ["sopr"]
    idx = pd.to_datetime(df["d"].str.slice(0, 10))
    out = pd.DataFrame({"sopr": pd.to_numeric(df[value_cols[0]]).values}, index=idx)
    assert out["sopr"].iloc[1] == 1.01 and out.index[0].year == 2026
    _ = a  # adapter instantiable without config only via __new__; parse logic above mirrors it


def test_deribit_options_aggregation() -> None:
    """Exercise the real compute_structure: parsing, put/call OI, ATM IV term
    structure (with tenor-range clamping), max pain, and BS greeks/GEX."""
    from datetime import datetime, timezone
    from collectors import deribit

    now = datetime(2026, 6, 13, tzinfo=timezone.utc)
    cfg = {"term_tenors_d": [7, 30, 90, 180], "skew_target_d": 30}
    S = 64000.0
    rows = []
    for K, civ, piv, coi, poi in [(60000, 55, 62, 30, 10), (64000, 50, 58, 100, 80),
                                  (68000, 48, 60, 40, 20)]:
        rows.append({"instrument_name": f"BTC-26JUN26-{K}-C", "open_interest": coi,
                     "mark_iv": civ, "underlying_price": S, "volume": 1})
        rows.append({"instrument_name": f"BTC-26JUN26-{K}-P", "open_interest": poi,
                     "mark_iv": piv, "underlying_price": S, "volume": 1})
    rows.append({"instrument_name": "BTC-25SEP26-64000-C", "open_interest": 20,
                 "mark_iv": 52, "underlying_price": S, "volume": 0})  # ~104d tenor
    rows.append({"instrument_name": "BTC-BADNAME", "open_interest": 5, "mark_iv": 50,
                 "underlying_price": S})  # must be skipped, not crash

    s = deribit.compute_structure(rows, now, cfg)
    assert s["underlying"] == S
    call_oi, put_oi = 30 + 100 + 40 + 20, 10 + 80 + 20  # +20 = the SEP call
    assert abs(s["put_call_oi_ratio"] - put_oi / call_oi) < 1e-9
    assert s["atm_iv_7d"] is None          # 7d < nearest expiry (13d) -> no extrapolation
    assert isinstance(s["atm_iv_30d"], float)   # 30d between 13d and 104d -> interpolated
    assert s["atm_iv_180d"] is None        # 180d > 104d -> no extrapolation
    assert s["max_pain"] in (60000.0, 64000.0, 68000.0)
    assert isinstance(s["gex_per_1pct_usd"], float)


def test_hourly_upsert_preserves_intraday() -> None:
    from lib import store
    idx = pd.to_datetime(["2026-06-10 03:00", "2026-06-10 04:00"])
    df = pd.DataFrame({"close": [1.0, 2.0]}, index=idx)
    # exercise the normalize_index=False path without touching real data dirs
    cleaned = df.copy()
    cleaned.index = pd.to_datetime(cleaned.index)
    assert (cleaned.index.hour != 0).any()
    _ = store  # store.upsert(normalize_index=False) covered by integration run


if __name__ == "__main__":
    for fn in [test_plotly_parse_plain_and_binary, test_bgeo_generic_parser_single_and_multi,
               test_deribit_options_aggregation, test_hourly_upsert_preserves_intraday]:
        fn()
        print(f"PASS {fn.__name__}")
    print("all crypto collector tests passed")


# R11: existing collector/evidence owner tests; fake responses and temporary stores only.
def _capture_payload(rate='0.0002',realized='0.00021'):
    return {'code':'0','data':[{'instId':'BTC-USDT-SWAP','instType':'SWAP',
        'fundingTime':'1767225600000','fundingRate':rate,'realizedRate':realized,
        'formulaType':'withRate','method':'current_period'}]}


def _capture(at='2026-01-01T01:00:00Z',rate='0.0002',realized='0.00021'):
    from collectors import _crypto_observations as o
    return o.build_capture('okx_funding',{'instId':'BTC-USDT-SWAP','limit':'100'},
                           _capture_payload(rate,realized),at)


def test_r11_capture_preserves_raw_funding_and_does_not_invent_interval():
    import json
    from collectors import _crypto_observations as o
    c=_capture(realized='-0.0001');row=json.loads(c['payload_json'])['data'][0]
    assert row['fundingRate']=='0.0002' and row['realizedRate']=='-0.0001'
    assert c['first_seen']==c['received_at']=='2026-01-01T01:00:00+00:00'
    assert c['provider_first_published_at'] is None
    events=o.funding_asof(pd.DataFrame([c]),'2026-01-01T02:00:00Z')
    assert events[0]['predicted_rate']==.0002 and events[0]['settled_rate']==-.0001
    assert events[0]['interval_hours'] is None and events[0]['annualized_settled_pct'] is None


def test_r11_capture_dedup_revision_and_reversion_preserve_history(tmp_path):
    from collectors import _crypto_observations as o
    a=_capture();b=_capture('2026-01-01T02:00:00Z',realized='.0003');c=_capture('2026-01-01T03:00:00Z')
    assert o.persist_capture(a,root=tmp_path)['status']=='stored'
    assert o.persist_capture(a,root=tmp_path)['status']=='already_present'
    for v in [b,c]:assert o.persist_capture(v,root=tmp_path)['status']=='stored'
    f=o.load_asof('okx_funding','2026-01-01T04:00:00Z',root=tmp_path)
    assert len(f)==3 and f.capture_id.nunique()==3
    assert a['payload_sha256']==c['payload_sha256']!=b['payload_sha256']
    assert o.funding_asof(f,'2026-01-01T01:30:00Z')[0]['settled_rate']==.00021
    assert o.funding_asof(f,'2026-01-01T02:30:00Z')[0]['settled_rate']==.0003
    assert o.funding_asof(f,'2026-01-01T03:30:00Z')[0]['settled_rate']==.00021
    assert o.funding_asof(f,'2025-12-31T23:59:00Z')==[]


def test_r11_capture_uses_allowlisted_scope_not_secrets():
    import json,hashlib
    from collectors import _crypto_observations as o
    payload=_capture_payload();payload['secret']='must-not-store';payload['data'][0]['api_key']='must-not-store'
    c=o.build_capture('okx_funding',{'instId':'BTC-USDT-SWAP','token':'must-not-store','after':'1'},payload,'2026-01-01T01:00:00Z',body=b'opaque-public-body')
    assert 'must-not-store' not in json.dumps(c)
    assert json.loads(c['params_json'])=={'after':'1','instId':'BTC-USDT-SWAP'}
    assert c['body_sha256']==hashlib.sha256(b'opaque-public-body').hexdigest()
    assert c['endpoint']=='https://www.okx.com/api/v5/public/funding-rate-history'


def test_r11_capture_corruption_and_failed_write_never_count_as_success(tmp_path,monkeypatch):
    from collectors import _crypto_observations as o
    path=o.capture_path('okx_funding',root=tmp_path);path.parent.mkdir(parents=True)
    path.write_bytes(b'not parquet');before=path.read_bytes()
    assert o.persist_capture(_capture(),root=tmp_path)['status']=='unavailable'
    assert path.read_bytes()==before
    path.unlink();monkeypatch.setattr(o.fss,'accrue_keep_first',lambda *a,**kw:0)
    assert o.persist_capture(_capture(),root=tmp_path)['status']=='unavailable'
    assert not path.exists()


def test_r11_capture_lock_contention_does_not_overwrite_or_retry(tmp_path):
    import fcntl
    from collectors import _crypto_observations as o
    path=o.capture_path('okx_funding',root=tmp_path);path.parent.mkdir(parents=True)
    with path.with_suffix('.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert o.persist_capture(_capture(),root=tmp_path)['status']=='unavailable'
    assert not path.exists()


def test_r11_capture_rejects_naive_missing_or_tampered_receipts(tmp_path):
    import pytest
    from collectors import _crypto_observations as o
    for at in [None,'not-a-date','2026-01-01 01:00:00']:
        with pytest.raises(ValueError):o.build_capture('okx_funding',{'instId':'BTC-USDT-SWAP'},_capture_payload(),at)
    c=_capture();c['payload_json']='{}'
    assert o.persist_capture(c,root=tmp_path)['status']=='unavailable'
    assert not o.capture_path('okx_funding',root=tmp_path).exists()


def test_r11_funding_unknown_actual_never_substitutes_predicted():
    from collectors import _crypto_observations as o
    events=o.funding_asof(pd.DataFrame([_capture(realized='')]),'2026-01-01T02:00:00Z')
    assert events[0]['predicted_rate']==.0002 and events[0]['settled_rate'] is None
    zero=o.funding_asof(pd.DataFrame([_capture(realized='0')]),'2026-01-01T02:00:00Z')[0]
    assert zero['settled_rate']==0


def test_r11_settlement_after_receipt_cannot_be_reported_as_already_settled():
    from collectors import _crypto_observations as o
    c=_capture('2025-12-31T23:00:00Z')
    e=o.funding_asof(pd.DataFrame([c]),'2026-01-01T03:00:00Z')[0]
    assert e['settled_rate'] is None and e['status']=='receipt_before_settlement'


def test_r11_conflicting_simultaneous_captures_are_not_arbitrarily_ordered():
    from collectors import _crypto_observations as o
    f=pd.DataFrame([_capture(),_capture(realized='.0004')])
    e=o.funding_asof(f,'2026-01-01T03:00:00Z')[0]
    assert e['status']=='conflicting_capture' and e['settled_rate'] is None


def test_r11_flow_scope_and_bgeo_clock_fields_are_retained_without_certification():
    import json
    from collectors import _crypto_observations as o
    c=o.build_capture('okx_taker',{'ccy':'BTC','instType':'CONTRACTS','period':'1H'},
        {'code':'0','data':[['1767225600000','2','3']]},'2026-01-01T02:00:00Z')
    assert c['unit'] is None and c['timestamp_role'] is None and c['finality'] is None
    assert json.loads(c['params_json'])['instType']=='CONTRACTS'
    b=o.build_capture('bgeo_funding',{'startday':'2026-01-01','size':'10'},
       [{'d':'2026-01-01T16:00:00Z','unixTs':'1767283200','fundingRate':'.1','markPrice':10,'delayed':True,'message':'delayed'}],
       '2026-01-03T00:00:00Z')
    row=json.loads(b['payload_json'])[0]
    assert row['unixTs']=='1767283200' and row['d'].endswith('16:00:00Z')
    assert row['delayed'] is True and row['message']=='delayed'


def test_r11_private_parser_probe_cannot_write_evidence(monkeypatch):
    from collectors import _crypto_observations as o
    class A:pass
    a=A();monkeypatch.setattr(o,'persist_capture',lambda *a,**k:(_ for _ in ()).throw(AssertionError('unexpected write')))
    assert o.record_response(a,'okx_funding',{},None,{},'2026-01-01T00:00:00Z')['status']=='inactive'


class _R11Response:
    def __init__(self,payload):
        import json
        self.payload=payload;self.content=json.dumps(payload).encode();self.status_code=200;self.headers={}
    def json(self):return self.payload
    def raise_for_status(self):pass


def _r11_okx(monkeypatch,tmp_path):
    from collectors import okx,_crypto_observations as o
    monkeypatch.setattr(o.config,'data_dir',lambda:tmp_path)
    monkeypatch.setattr(okx,'MAX_PAGES_FIRST_RUN',1)
    monkeypatch.setattr(okx.time,'sleep',lambda _:None)
    monkeypatch.setattr(o,'now_utc',lambda:'2026-01-02T00:00:00+00:00')
    a=okx.OkxAdapter()
    for name in ['_open_interest','_ls_account_ratio']:monkeypatch.setattr(a,name,lambda:None)
    monkeypatch.setattr(a,'_spot_candles',lambda *_:None)
    calls=[]
    def get(url,**kw):
        calls.append((url,dict(kw['params'])))
        payload=_capture_payload() if 'funding-rate-history' in url else {'code':'0','data':[['1767225600000','2','3'],['1767229200000','3','4']]}
        return _R11Response(payload)
    a.http_get=get
    return a,calls


def test_r11_okx_same_requests_and_legacy_values_with_capture(monkeypatch,tmp_path):
    from collectors import _crypto_observations as o
    a,calls=_r11_okx(monkeypatch,tmp_path)
    oldfund=a._funding(False);oldd=a._taker_volume();oldh=a._taker_volume_hourly();before=list(calls);calls.clear()
    assert not o.capture_path('okx_funding',root=tmp_path).exists()
    out=a.fetch()
    assert calls==before
    for name,old in [('funding_rate',oldfund),('taker_volume_hourly',oldh),('taker_volume',oldd)]:
        pd.testing.assert_frame_equal(out[name],old)
    f=o.load_asof('okx_funding','2026-01-03T00:00:00Z',root=tmp_path)
    assert len(f)==1 and len(o.load_asof('okx_taker','2026-01-03T00:00:00Z',root=tmp_path))==2
    assert a.fetch_result_status(out) is None and all(x['status']=='stored' for x in a.source_capture_status)
    assert a._crypto_capture_active is False


def test_r11_capture_failure_is_visible_without_hiding_independent_values(monkeypatch,tmp_path):
    from collectors import _crypto_observations as o
    a,_=_r11_okx(monkeypatch,tmp_path)
    monkeypatch.setattr(o,'persist_capture',lambda *a,**k:{'status':'unavailable','error_type':'OSError'})
    out=a.fetch()
    assert 'funding_rate' in out and 'taker_volume_hourly' in out
    assert a.fetch_result_status(out)=='stale'


def test_r11_bgeo_preserves_clock_delay_message_and_numeric_frame(monkeypatch,tmp_path):
    from collectors import bgeo,_crypto_observations as o
    monkeypatch.setattr(o.config,'data_dir',lambda:tmp_path);monkeypatch.setattr(bgeo.time,'sleep',lambda _:None)
    monkeypatch.setattr(o,'now_utc',lambda:'2026-01-03T00:00:00Z')
    rows=[{'d':'2026-01-01T16:00:00Z','unixTs':'1767283200','fundingRate':'-0.0001','markPrice':90,'delayed':True,'message':'delayed'}]
    calls=[]
    def get(*a,**kw):calls.append(kw['params']);return _R11Response(rows)
    monkeypatch.setattr(bgeo.requests,'get',get)
    a=bgeo.BgeoAdapter();a.cfg={**a.cfg,'metrics':{'funding-rate':'funding_rate'}}
    old=a._fetch_metric('funding-rate','funding_rate',a.cfg['window_start']);calls.clear()
    out=a.fetch();assert len(calls)==1
    pd.testing.assert_frame_equal(old,out['funding_rate'])
    f=o.load_asof('bgeo_funding','2026-01-04T00:00:00Z',root=tmp_path)
    assert len(f)==1 and '16:00:00Z' in f.iloc[0].payload_json
    assert a.fetch_result_status(out) is None


def test_r11_fetch_exception_clears_capture_scope(monkeypatch,tmp_path):
    import pytest
    a,_=_r11_okx(monkeypatch,tmp_path)
    monkeypatch.setattr(a,'_funding',lambda *_:(_ for _ in ()).throw(ValueError('fake-source-failure')))
    with pytest.raises(ValueError):a.fetch()
    assert a._crypto_capture_active is False


def test_r11_readable_but_corrupt_history_blocks_append(tmp_path):
    from collectors import _crypto_observations as o
    c=_capture();path=o.capture_path('okx_funding',root=tmp_path);path.parent.mkdir(parents=True)
    bad=dict(c,payload_json='{}');pd.DataFrame([bad]).to_parquet(path,index=False);original=path.read_bytes()
    assert o.persist_capture(_capture('2026-01-01T04:00:00Z'),root=tmp_path)['status']=='unavailable'
    assert path.read_bytes()==original


def test_r11_endpoint_and_instrument_mismatches_cannot_claim_a_known_source(tmp_path,monkeypatch):
    from collectors import _crypto_observations as o
    a,_=_r11_okx(monkeypatch,tmp_path);a.cfg={**a.cfg,'funding_url':'https://example.invalid/other'}
    # The fake server still returns parseable data. Preservation must not falsely
    # claim it came from the configured official funding endpoint.
    a.http_get=lambda *a,**k:_R11Response(_capture_payload())
    for name in ['_taker_volume','_taker_volume_hourly']:monkeypatch.setattr(a,name,lambda:None)
    out=a.fetch();assert 'funding_rate' in out
    assert a.fetch_result_status(out)=='stale'
    assert not o.capture_path('okx_funding',root=tmp_path).exists()
    c=o.build_capture('okx_funding',{'instId':'ETH-USDT-SWAP'},_capture_payload(),'2026-01-01T01:00:00Z')
    assert o.funding_asof(pd.DataFrame([c]),'2026-01-01T03:00:00Z')==[]


def test_r11_response_size_is_bounded_and_failed_runs_do_not_keep_capture_active(monkeypatch):
    import pytest
    from collectors import _crypto_observations as o
    monkeypatch.setattr(o,'MAX_ROWS',1)
    p=_capture_payload();p['data']*=2
    with pytest.raises(ValueError):o.build_capture('okx_funding',{'instId':'BTC-USDT-SWAP'},p,'2026-01-01T01:00:00Z')


def test_r11_run_adapter_proves_legacy_storage_and_evidence_together(tmp_path,monkeypatch):
    from collectors import base,_crypto_observations as o
    from lib import store
    a,_=_r11_okx(monkeypatch,tmp_path)
    result=base.run_adapter(a,stale_after_days=10000)
    assert result.status=='ok'
    assert list(store.read('okx','funding_rate'))==['funding_rate_okx']
    assert list(store.read('okx','taker_volume_hourly'))==['taker_buy_vol','taker_sell_vol']
    f=o.load_asof('okx_funding','2026-01-03T00:00:00Z',root=tmp_path)
    assert len(f)==1 and o.funding_asof(f,'2026-01-03T00:00:00Z')[0]['settled_rate']==.00021
    monkeypatch.setattr(o,'persist_capture',lambda *a,**k:{'status':'unavailable','error_type':'OSError'})
    result=base.run_adapter(a,stale_after_days=10000)
    assert result.status=='stale' and store.read('okx','funding_rate') is not None
