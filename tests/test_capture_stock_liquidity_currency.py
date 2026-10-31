"""No live calls: intake limits, refusal preservation and credential hygiene."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace
import pandas as pd
import pytest
from scripts.capture_stock_liquidity_currency import capture
from engine.liquidity_profile import _expected_sessions
from datetime import date

NOW=datetime(2026,10,20,7,tzinfo=timezone.utc)

@pytest.fixture
def source(tmp_path):
 p=tmp_path/'massive_stock_day'/'MU.parquet';p.parent.mkdir()
 days=_expected_sessions(date(2026,10,16),20)
 pd.DataFrame({'close':[100.0]*20,'volume':[1000000]*20},index=pd.DatetimeIndex(days)).to_parquet(p)
 return tmp_path

def client(base='https://api.polygon.io',key='test-synthetic-secret'):
 return SimpleNamespace(base=base,key=key,enabled=lambda:bool(key))

class Response:
 status_code=200
 def __init__(self,body): self.body=body
 def __enter__(self): return self
 def __exit__(self,*args): pass
 def iter_content(self,n): yield self.body

def test_twenty_dated_reads_then_existing_window_is_reused(source):
 calls=[]
 def get(url,**kw):
  calls.append((url,kw))
  return Response(json.dumps({'status':'OK','results':{'ticker':'MU','currency_name':'usd'}}).encode())
 result=capture('MU',data_root=source,client=client(),get=get,clock=lambda:NOW)
 assert result=={'status':'CAPTURED','requests_sent':20,'source_asof':'2026-10-16'}
 assert [c[1]['params']['date'] for c in calls]==[d.isoformat() for d in _expected_sessions(date(2026,10,16),20)]
 assert all(c[1]['allow_redirects'] is False and c[1]['stream'] is True for c in calls)
 again=capture('MU',data_root=source,client=client(),get=get,clock=lambda:NOW)
 assert again['requests_sent']==0 and len(calls)==20
 raw=(source/'stock_currency'/'MU.json').read_text()
 assert client().key not in raw
 assert 'valid_from' not in raw and 'known_at' not in raw

@pytest.mark.parametrize('status',[301,401,403,429,500])
def test_first_non200_stops_without_retry_or_overwriting_prior(source,status):
 p=source/'stock_currency'/'MU.json';p.parent.mkdir();p.write_text('{"retained":"prior"}')
 calls=[]
 def get(*a,**kw):
  calls.append(1);r=Response(b'');r.status_code=status;return r
 r=capture('MU',data_root=source,client=client(),get=get,clock=lambda:NOW)
 assert r['status']=='PROVIDER_STOP' and r['http_status']==status
 assert len(calls)==1 and p.read_text()=='{"retained":"prior"}'

@pytest.mark.parametrize('body,status',[(b'x'*131073,'RESPONSE_OVER_BOUND'),(b'test-synthetic-secret','RESPONSE_SECRET_REFUSED'),(b'{"status":"OK","results":{"ticker":"MU","currency_name":"EUR"}}','SOURCE_CONTRACT_REFUSED')])
def test_response_bound_secret_and_wrongcurrency(source,body,status):
 r=capture('MU',data_root=source,client=client(),get=lambda *a,**k:Response(body),clock=lambda:NOW)
 assert r['status']==status and r['requests_sent']==1
 assert not (source/'stock_currency').exists()

@pytest.mark.parametrize('base',['http://api.polygon.io','https://evil.example','https://api.polygon.io@evil.example','https://api.polygon.io?x=1','https://api.polygon.io:8443','https://api.polygon.io:invalid'])
def test_only_configured_legitimate_origin(source,base):
 r=capture('MU',data_root=source,client=client(base),get=lambda *a,**k:pytest.fail('no network'),clock=lambda:NOW)
 assert r['requests_sent']==0

def test_unadmitted_ticker_no_call(source):
 assert capture('AAPL',data_root=source,client=client(),get=None,clock=lambda:NOW)['status']=='NOT_ADMITTED'

def test_secret_exception_text_never_returned(source):
 def get(*a,**kw): raise RuntimeError('URL?apiKey=test-synthetic-secret')
 result=capture('MU',data_root=source,client=client(),get=get,clock=lambda:NOW)
 assert result['status']=='SOURCE_READ_FAILED'
 assert 'secret' not in json.dumps(result)


def test_existing_engine_binding_precedes_stock_builder():
 from pathlib import Path
 import yaml
 root=Path(__file__).resolve().parents[1]
 steps=yaml.safe_load((root/'.github/workflows/daily.yml').read_text())['jobs']['engine']['steps']
 captures=[(i,s) for i,s in enumerate(steps) if 'scripts.capture_stock_liquidity_currency' in s.get('run','')]
 builders=[i for i,s in enumerate(steps) if 'scripts/ci/daily_engine_regime_dashboard.sh' in s.get('run','')]
 assert len(captures)==1 and captures[0][0] < min(builders)
 assert set(captures[0][1]['env'])=={'POLYGON_API_KEY','MASSIVE_API_KEY'}
