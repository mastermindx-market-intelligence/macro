"""Private native capture -> K1/K3 -> research case, through the actual router."""
import json
import pytest
from engine.price_pressure import research
from tests.test_price_pressure_research import snapshot
from tests.test_ontology_explorer_transport import _api, _client

ROUTE = '/api/ontology/explorer/research/v1'
SELECTION = {'schema': 'ontology_drl_research_request.v1', 'date':'2026-10-15', 'ticker':'ACWI', 'side':'down'}


def private(response):
    assert response.headers['cache-control']=='private, no-store'
    assert response.headers['vary']=='Authorization, Cookie'
    assert response.headers['x-content-type-options']=='nosniff'
    assert response.headers['x-robots-tag']=='noindex, noarchive'


def test_research_route_reads_once_and_composes_actual_native_receipts(snapshot, monkeypatch, tmp_path):
    root, path, _ = snapshot
    original=research._read; reads=[]
    def read_once(root):
        reads.append(root)
        return original(root)
    monkeypatch.setattr(research,'_read',read_once)
    with _client(monkeypatch,tmp_path,root=root) as client:
        response=client.post(ROUTE,json=SELECTION)
    assert response.status_code==200,response.text
    private(response)
    value=response.json()
    assert reads==[root]
    assert value['capture']['native_identity']=={k:SELECTION[k] for k in ('date','ticker','side')}
    assert value['case']['evidence_binding']['state']=='exact_owner_native_event'
    assert value['case']['inputs']['vector']['asof']['value']==value['capture']['capture']['captured_at']
    assert value['case']['permitted_consumers']==['research_session']
    assert value['case']['company_context']['state']=='unavailable'


@pytest.mark.parametrize('authed,entitled,status',[(False,True,401),(True,False,403)])
def test_research_auth_precedes_body_and_owner_io(snapshot,monkeypatch,tmp_path,authed,entitled,status):
    root,_,_=snapshot
    def forbidden(*args,**kwargs):raise AssertionError('owner read before authorization')
    monkeypatch.setattr(_api(),'read_drl_research',forbidden)
    with _client(monkeypatch,tmp_path,root=root,authed=authed,entitled=entitled) as client:
        response=client.post(ROUTE,content=b'not-json',headers={'Content-Type':'application/json'})
    assert response.status_code==status
    private(response)


@pytest.mark.parametrize('change',[{'date':'2026-02-30'},{'ticker':'../../secret'},{'ticker':'acwi'},{'side':[]},{'path':'secret'}, {'schema':'other'}])
def test_research_invalid_selection_never_reads(snapshot,monkeypatch,tmp_path,change):
    root,_,_=snapshot
    def forbidden(*args,**kwargs):raise AssertionError('invalid selection read owner')
    monkeypatch.setattr(_api(),'read_drl_research',forbidden)
    with _client(monkeypatch,tmp_path,root=root) as client:
        response=client.post(ROUTE,json={**SELECTION,**change})
    assert response.status_code==400
    private(response)


@pytest.mark.parametrize('mode,status',[('missing_event',404),('missing_snapshot',503),('unexpected',503)])
def test_research_failures_are_private_and_do_not_echo_body(snapshot,monkeypatch,tmp_path,mode,status):
    root,path,body=snapshot
    if mode=='missing_event':
        body['open_events']=[];path.write_text(json.dumps(body))
    elif mode=='missing_snapshot':path.unlink()
    else:
        def broken(*args,**kwargs):raise RuntimeError('sensitive-native-body-123')
        monkeypatch.setattr(_api(),'read_drl_research',broken)
    with _client(monkeypatch,tmp_path,root=root) as client:
        response=client.post(ROUTE,json=SELECTION)
    assert response.status_code==status
    private(response)
    assert 'sensitive-native-body' not in response.text and 'capture' not in response.json().get('detail',{})


@pytest.mark.parametrize('method',['GET','HEAD','PUT','PATCH','DELETE','OPTIONS'])
def test_research_unsupported_methods_refuse_privately(snapshot,monkeypatch,tmp_path,method):
    root,_,_=snapshot
    with _client(monkeypatch,tmp_path,root=root) as client:
        response=client.request(method,ROUTE)
    assert response.status_code==405 and response.headers['allow']=='POST'
    private(response)
