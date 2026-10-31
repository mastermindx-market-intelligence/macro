from pathlib import Path
import json
from copy import deepcopy
from hashlib import sha256
import pytest
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
from scripts import build_government_revenue as builder
from app import government_revenue as api
from engine.government_revenue import (
 program_theme_reviewed_builder as rb,
 program_theme_disclosure as d,
 program_theme_publication as publication,
 program_theme_context as t,
 budget_allocation_context as a,
)
incumbent_rb = rb
B = Path(__file__).parent / 'fixtures' / 'runtime_wiring'
NOW='2026-10-13T08:00:00+00:00'

def allocation_graph_fixture():
 # Exact retained allocation document; the API envelope intentionally needs no
 # unrelated programme/line graph, and refusal checks never compose a graph.
 return {'contract':'government_budget_program_graph.v1','schema_version':'1.1.0','documents':[json.loads((B/'allocation-document.json').read_bytes())]}

def pair():return (json.loads((B/'current-reference-snapshot.json').read_bytes()),json.loads((B/'current-public-disclosure.json').read_bytes()))

def test_current_explicit_owner883_refs12plus8_and_closed_precomputed_pair():
 r,p=pair();assert publication.validate_precomputed_theme_pair(r,p)
 assert [len(r['themes'][i]['rails']['economics']['references']) for i in (1,2,5)]==[6,6,8]
 assert all(x['rail_states']['market_context']=='projection_missing' for x in p['themes'])
 assert all(x['research_state']=='EVIDENCE_INSUFFICIENT' for x in p['themes'])

@pytest.mark.parametrize('tamper',['source_ref','reference_content','public_binding','public_promotion'])
def test_rehashed_pair_tamper_cannot_add_reference_or_promote(tamper):
 r,p=pair()
 if tamper=='source_ref':p['themes'][5]['sources'][0]['row_id']='not-an-approved-source'
 elif tamper=='reference_content':r['themes'][0]['rails']['funding_stage']['reason_code']='invented'
 elif tamper=='public_binding':p['theme_content_id']='gptc1-'+'a'*24
 else:p['themes'][0]['rail_states']['funding_stage']='supported'
 p['content_id']=d.disclosure_content_id(p)
 with pytest.raises(ValueError):publication.validate_precomputed_theme_pair(r,p)

def test_builder_writes_exact_four_twins_and_site_only_reads_no_source(tmp_path,monkeypatch):
 r,p=pair();rr=builder._canonical_json(r);pr=builder._canonical_json(p);builder._write_program_theme_twins(tmp_path,rr,pr)
 assert (tmp_path/'site/government-revenue-data/theme-context.json').read_text()==pr
 monkeypatch.setattr(incumbent_rb,'build_public_theme_candidate',lambda *x,**k:pytest.fail('site-only must not rebuild'))
 builder._project_committed_program_themes(tmp_path)
 assert (tmp_path/'data/government_revenue/program_theme_context.json').read_text()==rr
 (tmp_path/'data/government_revenue/program_theme_public_disclosure.json').unlink()
 with pytest.raises(ValueError,match='partial'):builder._project_committed_program_themes(tmp_path)

def test_missing_theme_review_publishes_closed_unavailable_without_candidate_failure(tmp_path,monkeypatch):
 monkeypatch.setattr(incumbent_rb,'build_public_theme_candidate',rb.build_public_theme_candidate)
 out=builder._publish_reviewed_program_themes(tmp_path,generated_at=NOW,as_of=NOW)
 assert out['state']=='source_unavailable'
 assert (tmp_path/'site/government-revenue-data/theme-context.json').is_file()

def api_paths(tmp_path,monkeypatch):
 r,p=pair();builder._write_program_theme_twins(tmp_path,builder._canonical_json(r),builder._canonical_json(p))
 monkeypatch.setattr(api,'_THEME_REFERENCE_PATHS',(tmp_path/'data/government_revenue/program_theme_context.json',tmp_path/'site/government-revenue-data/program-theme-context.json'))
 monkeypatch.setattr(api,'_THEME_PUBLIC_PATHS',(tmp_path/'data/government_revenue/program_theme_public_disclosure.json',tmp_path/'site/government-revenue-data/theme-context.json'))
 return r,p

def test_entitled_api_returns_only_precomputed_public_pair_without_owner_join(tmp_path,monkeypatch):
 r,p=api_paths(tmp_path,monkeypatch)
 monkeypatch.setattr(incumbent_rb,'build_public_theme_candidate',lambda *x,**k:pytest.fail('API must not rebuild'))
 monkeypatch.setattr(t.OwnerSnapshot,'payload',lambda *x,**k:pytest.fail('API must not join source owners'))
 app=FastAPI();app.include_router(api.router);app.dependency_overrides[api.require_site_full_user]=lambda:{'sub':'local-entitled-fixture'}
 with TestClient(app) as c:response=c.get('/api/government-revenue/theme-context')
 assert response.status_code==200 and response.json()==p and 'owner_bindings' not in response.json()


def test_authentication_rejection_precedes_artifact_read(tmp_path,monkeypatch):
 api_paths(tmp_path,monkeypatch)
 def refused():raise HTTPException(status_code=403,detail='entitlement required')
 app=FastAPI();app.include_router(api.router);app.dependency_overrides[api.require_site_full_user]=refused
 monkeypatch.setattr(api,'_THEME_REFERENCE_PATHS',())
 monkeypatch.setattr(api,'_THEME_PUBLIC_PATHS',())
 with TestClient(app) as c:response=c.get('/api/government-revenue/theme-context')
 assert response.status_code==403

@pytest.mark.parametrize('change',['missing','torn','binding'])
def test_api_partial_torn_or_unbound_pair_is503(tmp_path,monkeypatch,change):
 r,p=api_paths(tmp_path,monkeypatch)
 if change=='missing':api._THEME_REFERENCE_PATHS[1].unlink()
 elif change=='torn':api._THEME_PUBLIC_PATHS[1].write_bytes(b'{}')
 else:
  p['theme_content_id']='gptc1-'+'a'*24;p['content_id']=d.disclosure_content_id(p)
  for path in api._THEME_PUBLIC_PATHS:path.write_text(builder._canonical_json(p))
 with pytest.raises(HTTPException) as error:api.theme_context()
 assert error.value.status_code==503


def test_native_allocation_context_is_not_dropped_or_labeled_request():
 graph=allocation_graph_fixture();out=api._public_budget_graph_envelope(graph);doc=next(x for x in out['documents'] if x.get('document_kind')=='legislative_allocation_spend_plan')
 assert doc['exhibit'] is None and doc['document_stage']=='allocation_plan'
 assert doc['document_context']['stage']=='allocation_plan' and 'obligation' in doc['document_context']['limitation_en']
 assert 'allocations' not in doc and 'immutable_object_key' not in str(out)


def test_optional_allocation_source_denial_retains_other_valid_graph_without_retry(tmp_path,monkeypatch):
 graph=allocation_graph_fixture();path=tmp_path/a.ALLOCATION_RECEIPT_PATH;path.parent.mkdir(parents=True);path.write_text('{}');calls=[]
 class ExactRefusal(Exception):response={'Error':{'Code':'AccessDenied'},'ResponseMetadata':{'HTTPStatusCode':403}}
 def denied(*x,**k):calls.append(1);raise ExactRefusal()
 monkeypatch.setattr(a,'load_collected_allocation_context_input',denied)
 assert builder._extend_budget_allocation_context(tmp_path,graph,dossier={},generated_at=NOW,as_of=NOW)==graph and len(calls)==1


def test_exact_subdaily_allocation_cutoff_never_backdates_known_source(tmp_path,monkeypatch):
 graph=allocation_graph_fixture();path=tmp_path/a.ALLOCATION_RECEIPT_PATH;path.parent.mkdir(parents=True);path.write_text('{}');receipt=json.loads((B/'allocation-receipt.json').read_bytes());receipt['known_at']='2026-10-13T07:00:00Z'
 monkeypatch.setattr(a,'load_collected_allocation_context_input',lambda *x:(receipt,b''))
 assert builder._extend_budget_allocation_context(tmp_path,graph,dossier={},generated_at=NOW,as_of='2026-10-13T06:00:00Z')==graph


def test_real_generation_qualified_reference_replay_keeps_native_fact_and_event():
 reference,_=pair();ref=reference['themes'][1]['rails']['economics']['references'][0];binding=reference['owner_bindings']['quartet_economics'];old=t.OwnerSnapshot('defense_economics',(B/'current-defense-economics.json').read_bytes(),binding['available_at'],binding['admission_ref'],binding['rights_state']);body=old.payload();expected=rb.reference_fingerprint(ref,'economics',old,NOW)
 previous='883fb5c69607c3d248b45f7e';nextgen='a'*24;raw=json.dumps(body).replace(previous,nextgen);changed=json.loads(raw)
 from engine.government_revenue.defense_economics import defense_economics_content_id
 changed['content_id']=defense_economics_content_id(changed);new=t.OwnerSnapshot(old.owner_kind,json.dumps(changed).encode(),NOW,old.admission_ref,old.rights_state)
 assert new.payload() and rb.reference_fingerprint(ref,'economics',new,NOW)==expected
 row=t._pointer(changed,ref['pointer'])[0];row['value']+=1
 changed['content_id']=defense_economics_content_id(changed)
 corrected=t.OwnerSnapshot(old.owner_kind,json.dumps(changed).encode(),NOW,old.admission_ref,old.rights_state)
 assert rb.reference_fingerprint(ref,'economics',corrected,NOW)!=expected
