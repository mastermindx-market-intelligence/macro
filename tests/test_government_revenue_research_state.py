from __future__ import annotations

import importlib.util
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import pytest

REPO = Path(os.environ.get('MACRO_REPO', Path.cwd()))
OVERLAY = Path(os.environ.get('GRV_Q3_OVERLAY', REPO))
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location('engine.government_revenue.research_state',
    OVERLAY/'engine/government_revenue/research_state.py')
state = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = state
spec.loader.exec_module(state)

from engine.government_revenue.candidate_grader import GRV_FA1, GraderError, _authority, canonical_bytes


def fixture_queue_bytes():
    fixtures=OVERLAY/'tests/fixtures'
    provenance=json.loads((fixtures/'government_revenue_candidate_queue_20260901.provenance.json').read_bytes())
    compressed=(fixtures/'government_revenue_candidate_queue_20260901.json.gz').read_bytes()
    assert len(compressed)<=256*1024 and sha256(compressed).hexdigest()==provenance['compressed_sha256']
    raw=gzip.decompress(compressed)
    assert len(raw)<=2*1024*1024 and sha256(raw).hexdigest()==provenance['source_sha256']
    return raw


def payload():
    queue = json.loads(fixture_queue_bytes())
    return state.build_not_started_state(queue=queue,prereg_path=REPO/GRV_FA1.document,
        generated_at='2026-10-13T03:30:00Z', source_digests={p: 'a'*64 for p in state.SOURCE_PATHS})


def test_real_historical_display_does_not_become_issuance():
    p = payload()
    assert p['state']=='not_started' and p['is_running'] is False
    assert p['input_admission']['considered_n']==173
    assert p['input_admission']['counts']['owner_admitted_input_shape']==12
    assert p['issuance']['issued_n']==0 and p['outcomes']['efficacy'] is None
    assert p['issuance']['line_count']==0
    assert p['registration']['family']['maturity_gate']['min_distinct_source_events']==545
    assert p['registration']['family']['accrual_expiry_date']=='2029-08-06'


@pytest.mark.parametrize('mutation', ['running','issued','efficacy','authority','threshold'])
def test_rehashed_false_claims_still_fail(mutation):
    p = payload()
    if mutation=='running':p['is_running']=True
    if mutation=='issued':p['issuance']['issued_n']=12
    if mutation=='efficacy':p['outcomes']['efficacy']='supported'
    if mutation=='authority':p['authority']['can_originate_signal']=True
    if mutation=='threshold':p['registration']['family']['maturity_gate']['min_distinct_source_events']=12
    p['content_id']=state.content_id(p)
    with pytest.raises(GraderError):state.validate_research_state(p)


def test_future_candidate_generation_is_refused():
    from engine.government_revenue.candidates import candidate_queue_content_id
    queue=json.loads(fixture_queue_bytes())
    queue['generated_at']='2026-10-14T00:00:00Z'
    queue['content_id']=candidate_queue_content_id(queue)
    with pytest.raises(GraderError,match='future'):
        state.build_not_started_state(queue=queue,prereg_path=REPO/GRV_FA1.document,
            generated_at='2026-10-13T03:30:00Z',source_digests={'generation':'a'*64})


def test_bounded_twin_consumer_refuses_tamper_and_oversize(tmp_path):
    paths=tmp_path/'canonical.json',tmp_path/'public.json'
    raw=canonical_bytes(payload())+b'\n'
    for p in paths:p.write_bytes(raw)
    assert state.load_research_state(paths)['state']=='not_started'
    paths[1].write_bytes(raw+b' ')
    with pytest.raises(GraderError,match='twins'):state.load_research_state(paths)
    paths[0].write_bytes(b'x'*(state.MAX_STATE_BYTES+1))
    with pytest.raises(GraderError,match='budget'):state.load_research_state(paths)


def test_existing_paid_router_consumer_over_http(tmp_path,monkeypatch):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app import government_revenue as api
    paths=tmp_path/'canonical.json',tmp_path/'public.json'
    for path in paths:path.write_bytes(canonical_bytes(payload()))
    # Exercise the sole installed handler, including its real loader and entitlement dependency.
    monkeypatch.setattr(api,'_RESEARCH_STATE_PATHS',paths)
    app=FastAPI();app.include_router(api.router)
    client=TestClient(app)
    assert client.get('/api/government-revenue/research-state').status_code==401
    from app import main, paywall
    monkeypatch.setattr(main,'require_user',lambda authorization:{'id':'fixture_user'})
    monkeypatch.setattr(paywall,'_load_config',lambda:{'premium':{'required_feature':'site_full'}})
    monkeypatch.setattr(paywall,'_entitled',lambda user_id,feature:(False,'essential'))
    assert client.get('/api/government-revenue/research-state',headers={'Authorization':'Bearer synthetic'}).status_code==403
    monkeypatch.setattr(paywall,'_entitled',lambda user_id,feature:(True,'premium'))
    response=client.get('/api/government-revenue/research-state')
    assert response.status_code==200 and response.json()['state']=='not_started'
    paths[1].write_bytes(b'{}')
    assert client.get('/api/government-revenue/research-state').status_code==503
    bad=payload();bad['input_admission']['counts']['owner_admitted_input_shape']='12'
    bad['content_id']=state.content_id(bad)
    for path in paths:path.write_bytes(canonical_bytes(bad))
    assert client.get('/api/government-revenue/research-state').status_code==503
    for path in paths:path.write_bytes(b'['*3000+b']'*3000)
    assert client.get('/api/government-revenue/research-state').status_code==503


def test_publisher_prepares_before_final_proof_without_creating_log(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('q3_state_publisher',
        OVERLAY/'scripts/build_government_revenue_research_state.py')
    publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
    for name in publisher.INPUT_PATHS:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((REPO/name).read_bytes())
    # A controlled old queue proves zero issuance independently of production's advancing generation.
    (tmp_path/'data/government_revenue/candidate_queue.json').write_bytes(fixture_queue_bytes())
    prereg=tmp_path/GRV_FA1.document;prereg.parent.mkdir(parents=True,exist_ok=True)
    prereg.write_bytes((REPO/GRV_FA1.document).read_bytes())
    # Sourceproof is independently exercised by its existing owner tests; this
    # fixture proves this publisher honors the verified seam and writes zero log.
    calls=[]
    def verify(root,**kw):
        assert kw['mirror_public'] is False
        calls.append(1);return {'status':'ok','generation':'verified_fixture'}
    monkeypatch.setattr(publisher,'verify_candidate_artifacts',verify)
    result=publisher.project_research_state(tmp_path,generated_at='2026-10-13T03:30:00Z')
    assert result['requires_new_final_generation_proof'] is True and len(calls)==2
    assert not (tmp_path/'data/government_revenue/candidate_issuance_log.jsonl').exists()
    assert state.load_research_state((tmp_path/'data/government_revenue/candidate_research_state.json',
        tmp_path/'site/government-revenue-data/research-state.json'))['issuance']['append_count_this_generation']==0


@pytest.mark.parametrize('mutation', ['hidden_source','bad_sha','bool_zero','bad_count','hidden_reason','future_asof','hidden_issuance','hidden_family'])
def test_closed_nested_contract(mutation):
    p=payload()
    if mutation=='hidden_source':p['sources']['private_personal_data']='a'*64
    if mutation=='bad_sha':p['sources'][next(iter(p['sources']))]='x'*64
    if mutation=='bool_zero':p['issuance']['issued_n']=False
    if mutation=='bad_count':p['input_admission']['counts']['owner_admitted_input_shape']='12'
    if mutation=='hidden_reason':p['input_admission']['counts']['secret_note']=0
    if mutation=='future_asof':p['as_of']='2030-01-01'
    if mutation=='hidden_issuance':p['issuance']['hidden']='personal information'
    if mutation=='hidden_family':p['registration']['family']['extra']='personal information'
    p['content_id']=state.content_id(p)
    with pytest.raises(GraderError):state.validate_research_state(p)


def test_builder_consumes_incumbent_queue_validator():
    q=json.loads(fixture_queue_bytes())
    q['content_id']='forged'
    with pytest.raises(GraderError,match='candidate input'):
        state.build_not_started_state(queue=q,prereg_path=REPO/GRV_FA1.document,
            generated_at='2026-10-13T03:30:00Z',source_digests={p:'a'*64 for p in state.SOURCE_PATHS})
