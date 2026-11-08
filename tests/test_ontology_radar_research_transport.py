"""Private Macro reading of existing native Radar output, never a new run."""
import pytest

from engine.entry_radar import research_read as rr
from tests.test_entry_radar_research_read import published
from tests.test_ontology_explorer_transport import _api, _client
from tests.test_ontology_research_transport import private

ROUTE='/api/ontology/explorer/radar-research/v1'
REQUEST={'schema':'ontology_radar_research_request.v1','episode_id':None}


def test_private_list_then_exact_native_case(published,monkeypatch,tmp_path):
    root,_,_,episode=published
    reads=[]
    def read(eid):
        reads.append(eid)
        return rr.read_published_research(root,episode_id=eid)
    monkeypatch.setattr(_api(),'read_radar_research',read)
    with _client(monkeypatch,tmp_path) as client:
        listing=client.post(ROUTE,json=REQUEST)
        selected=client.post(ROUTE,json={**REQUEST,'episode_id':episode.episode_id})
    assert listing.status_code==200 and selected.status_code==200
    private(listing);private(selected)
    assert reads==[None,episode.episode_id]
    assert selected.json()['case']['episode_id']==episode.episode_id


@pytest.mark.parametrize('authed,entitled,status',[(False,True,401),(True,False,403)])
def test_authority_precedes_body_and_io(monkeypatch,tmp_path,authed,entitled,status):
    monkeypatch.setattr(_api(),'read_radar_research',lambda _:pytest.fail('unauthorized IO'))
    with _client(monkeypatch,tmp_path,authed=authed,entitled=entitled) as client:
        response=client.post(ROUTE,content=b'not-json',headers={'Content-Type':'application/json'})
    assert response.status_code==status;private(response)


@pytest.mark.parametrize('patch',[{'episode_id':'../../secret'},{'episode_id':[]},{'path':'/secret'},{'schema':'wrong'}])
def test_bad_selection_does_not_read(monkeypatch,tmp_path,patch):
    monkeypatch.setattr(_api(),'read_radar_research',lambda _:pytest.fail('invalid IO'))
    with _client(monkeypatch,tmp_path) as client:response=client.post(ROUTE,json={**REQUEST,**patch})
    assert response.status_code==400;private(response)


@pytest.mark.parametrize('reason,status',[('candidate_not_found',404),('radar_research_unavailable',503),('secret-owner-bytes',503)])
def test_refusal_contains_no_owner_content(monkeypatch,tmp_path,reason,status):
    def fail(_):raise rr.ResearchReadUnavailable(reason)
    monkeypatch.setattr(_api(),'read_radar_research',fail)
    with _client(monkeypatch,tmp_path) as client:response=client.post(ROUTE,json=REQUEST)
    assert response.status_code==status;private(response)
    assert 'secret-owner-bytes' not in response.text


@pytest.mark.parametrize('method',['GET','HEAD','PUT','PATCH','DELETE','OPTIONS'])
def test_method_refusal_stays_private(monkeypatch,tmp_path,method):
    with _client(monkeypatch,tmp_path) as client:response=client.request(method,ROUTE)
    assert response.status_code==405 and response.headers['allow']=='POST';private(response)
