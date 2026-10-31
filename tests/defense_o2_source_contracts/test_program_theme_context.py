import os
from pathlib import Path
import sys,json
from copy import deepcopy
from datetime import datetime
import pytest
from jsonschema import Draft202012Validator
try:
 from engine.government_revenue import program_theme_context as t
except ImportError:
 import program_theme_context as t
ROOT=Path(os.environ.get('DEFENSE_REPO_ROOT') or next((str(p) for p in Path(__file__).resolve().parents if (p/'engine/government_revenue').is_dir()), str(Path(__file__).resolve().parents[1])))
t._SCHEMA_ROOT=ROOT/'contracts/government_revenue'
FIX=Path(__file__).parent/'fixtures'
NOW='2026-10-13T08:00:00+00:00';ASOF='2026-10-13T06:00:00+00:00'

def snapshot(key,file,kind):
 b=(FIX/file).read_bytes();p=json.loads(b)
 clocks=list(t._clocks(p));available=max(clocks).isoformat()
 return t.OwnerSnapshot(kind,b,available,'existing:'+file,'qualified_public_display')
def owners():
 return {'fms':snapshot('fms','fms_case_graph.json','fms'),'ontology':snapshot('ontology','program_ontology.json','program_ontology'),'atlas':snapshot('atlas','identity_atlas.json','identity_atlas'),'dossier':snapshot('dossier','program_dossier.json','program_dossier')}
def assignment():
 p=json.loads((FIX/'fms_case_graph.json').read_bytes());idx=next(i for i,x in enumerate(p['cases']) if x['case_key']=='fms:transmittal:25-104')
 ref=dict(owner_key='fms',pointer=f'/cases/{idx}',row_id=p['cases'][idx]['case_key'])
 o=json.loads((FIX/'program_ontology.json').read_bytes());role=o['role_assertions'][0]
 return {'nato_fms_demand':{'funding_stage':dict(state='partial',reason_code='congressional_notification_only',references=[ref]),'exposure':dict(state='unreviewed',reason_code='contractor_identity_not_reviewed',references=[{**ref,'pointer':f'/cases/{idx}/contractors/0'}]),'next_event':dict(state='partial',reason_code='condition_not_scheduled_date',references=[{**ref,'pointer':f'/cases/{idx}/advancement_condition'}])},'shipbuilding':{'exposure':dict(state='supported',reason_code='reviewed_program_participation',references=[dict(owner_key='ontology',pointer='/role_assertions/0',row_id=role['id']),dict(owner_key='atlas',pointer='/issuers/4/entities/1',row_id='legal:gd:electric-boat-corp')])}}
def compose(a=None,o=None): return t.compose_program_theme_context(assignment() if a is None else a,owners=owners() if o is None else o,generated_at=NOW,as_of=ASOF)

def test_actual_accepted_fms_ontology_owner_refs_no_copied_truth():
 o=owners();a=assignment();before=deepcopy(a);p=compose(a,o)
 assert a==before and t.validate_program_theme_context(p,owners=o)
 Draft202012Validator(json.loads((Path(__file__).parent/'government_program_theme_context.v1.schema.json').read_text())).validate(p)
 assert [x['theme_id'] for x in p['themes']]==list(t.THEMES)
 assert all(x['research_state']=='EVIDENCE_INSUFFICIENT' for x in p['themes'])
 assert 'estimated_notification_value' not in str(p) and 'economic_weight' not in str(p)
 assert p['themes'][3]['rails']['exposure']['state']=='unreviewed'
 assert 'atlas' in p['owner_bindings'] and 'dossier' not in p['owner_bindings']

@pytest.mark.parametrize('mutation',[
 lambda a:a.update({'invented_program_id':{}}),
 lambda a:a['shipbuilding'].update({'workshare':0.5}),
 lambda a:a['shipbuilding']['exposure'].update({'amount':123}),
 lambda a:a['shipbuilding']['exposure']['references'][0].update({'program_id':'acq-program:golden-dome'}),
 lambda a:a['shipbuilding']['exposure']['references'][0].update({'owner_key':'missing'}),
 lambda a:a['shipbuilding']['exposure']['references'][0].update({'row_id':'made-up'}),
 lambda a:a['shipbuilding']['exposure']['references'][0].update({'pointer':'/programs/0'}),
 lambda a:a['shipbuilding']['exposure']['references'].clear(),
 lambda a:a['shipbuilding']['exposure']['references'].append(deepcopy(a['shipbuilding']['exposure']['references'][0])),
 lambda a:a['nato_fms_demand']['exposure'].update({'state':'supported'}),
])
def test_hostile_assignments_refuse(mutation):
 a=assignment();mutation(a)
 with pytest.raises(ValueError):compose(a)

@pytest.mark.parametrize('field,value',[('rights_state','unqualified'),('admission_ref',''),('available_at','2026-01-01T00:00:00+00:00')])
def test_unqualified_or_backdated_owner_refuses(field,value):
 o=owners();x=o['fms'];o['fms']=t.OwnerSnapshot(**{**x.__dict__,field:value})
 with pytest.raises(ValueError):compose(o=o)

def test_future_owner_or_source_known_cannot_be_historical_first_seen():
 with pytest.raises(ValueError):t.compose_program_theme_context(assignment(),owners=owners(),generated_at=NOW,as_of='2026-08-27T00:00:00+00:00')

def test_raw_corrupt_owner_refuses_even_with_new_exact_digest():
 o=owners();x=o['fms'];p=json.loads(x.raw_bytes);p['cases'][0]['private_body']='SECRET';o['fms']=t.OwnerSnapshot(**{**x.__dict__,'raw_bytes':json.dumps(p).encode()})
 with pytest.raises(ValueError):compose(o=o)

def test_tampered_hash_and_state_do_not_certify():
 o=owners();p=compose(o=o);p['themes'][0]['research_state']='SOURCE_CONTEXT_COMPLETE';p['content_id']=t.content_id(p)
 with pytest.raises(ValueError):t.validate_program_theme_context(p,owners=o)
 p=compose(o=o);p['owner_bindings']['fms']['sha256']='a'*64;p['content_id']=t.content_id(p)
 with pytest.raises(ValueError):t.validate_program_theme_context(p,owners=o)

def test_generation_clock_does_not_refresh_source_identity():
 o=owners();p=compose(o=o);later=t.compose_program_theme_context(assignment(),owners=o,generated_at='2026-10-14T08:00:00+00:00',as_of=ASOF)
 assert later['content_id']==p['content_id'] and later['owner_bindings']==p['owner_bindings']

def test_empty_themes_are_explicit_and_never_six_theme_acceptance():
 p=compose({});assert p['owner_bindings']=={}
 assert all(x['research_state']=='EVIDENCE_INSUFFICIENT' and all(r['state']=='source_unavailable' for r in x['rails'].values()) for x in p['themes'])

def test_read_validation_replays_refs_and_digest_against_exact_owner_bytes():
 o=owners();p=compose(o=o);x=o['fms'];o['fms']=t.OwnerSnapshot(**{**x.__dict__,'raw_bytes':x.raw_bytes+b'\n'})
 with pytest.raises(ValueError):t.validate_program_theme_context(p,owners=o)

def test_next_event_conditions_are_owner_text_not_new_schedule():
 p=compose();r=p['themes'][3]['rails']['next_event'];assert r['reason_code']=='condition_not_scheduled_date';assert set(r)=={'state','reason_code','references'}

def test_v1_dossier_stays_exact_and_unchanged():
 b=(FIX/'program_dossier.json').read_bytes();o=owners();compose(o=o);assert (FIX/'program_dossier.json').read_bytes()==b

def company_owner():
 b=(FIX/'lmt_event_workspace.json').read_bytes();p=json.loads(b);return t.OwnerSnapshot('company_intelligence',b,max(t._clocks(p)).isoformat(),'prepared-owner-fixture:ADMISSION_HELD_NOT_PRODUCTION','qualified_public_display')
def company_assignment(owner=None):
 x=company_owner() if owner is None else owner;fid='evt_cik0000936468_2026q2_results:defense_segment_sales'
 return {'munitions_replenishment':{'economics':dict(state='partial',reason_code='prepared_owner_reference_structural_test',references=[t.financial_fact_reference('company',x,fid)])}}

def test_actual_prepared_eventworkspace_reference_capability_does_not_copy_amounts():
 # Structural reference test only. This fixture's owner acceptance is held.
 x=company_owner();p=compose(company_assignment(x),{'company':x});assert t.validate_program_theme_context(p,owners={'company':x})
 assert p['owner_bindings']['company']['house_observed_at']=='2026-10-13T02:42:07Z'
 assert p['owner_bindings']['company']['source_available_at']=='2026-07-23T10:30:57Z'
 assert '4,101' not in str(p) and '4101' not in str(p)
 assert json.loads((Path(__file__).parent/'event-workspace-fixture-admission.json').read_text())['status']=='structure_verified_local_owner_prepared_admission_held'

@pytest.mark.parametrize('field,value',[('period','2025Q2'),('event_id','evt_cik0000405333_2026q2_results'),('value',99999),('typed_absence',{'reason':'missing'})])
def test_eventworkspace_wrong_fact_subject_period_literal_and_absence_refuse(field,value):
 x=company_owner();p=json.loads(x.raw_bytes);fact=next(f for f in p['facts'] if f.get('metric')=='defense_segment_sales');fact[field]=value;y=t.OwnerSnapshot(**{**x.__dict__,'raw_bytes':json.dumps(p).encode()})
 with pytest.raises(ValueError):compose(company_assignment(y),{'company':y})

@pytest.mark.parametrize('field,value',[('rights_profile','private'),('receipt_state','address_only'),('text_sha256','a'*64),('document_id','wrong_document')])
def test_eventworkspace_unsafe_rights_or_span_refuses(field,value):
 x=company_owner();p=json.loads(x.raw_bytes);fact=next(f for f in p['facts'] if f.get('metric')=='defense_segment_sales');fact['source_span'][field]=value;y=t.OwnerSnapshot(**{**x.__dict__,'raw_bytes':json.dumps(p).encode()})
 with pytest.raises(ValueError):compose(company_assignment(y),{'company':y})

def test_fact_pointer_is_refreshed_by_stable_id_not_pinned_index():
 x=company_owner();p=json.loads(x.raw_bytes);fid='evt_cik0000936468_2026q2_results:defense_segment_sales';before=t.financial_fact_reference('company',x,fid);p['facts'].reverse();y=t.OwnerSnapshot(**{**x.__dict__,'raw_bytes':json.dumps(p).encode()});after=t.financial_fact_reference('company',y,fid)
 assert before['pointer']!=after['pointer'] and before['row_id']==after['row_id']
 assert compose(company_assignment(y),{'company':y})
 p['facts'].append(deepcopy(next(f for f in p['facts'] if f.get('fact_id')==fid)));z=t.OwnerSnapshot(**{**x.__dict__,'raw_bytes':json.dumps(p).encode()})
 with pytest.raises(ValueError,match='not_unique'):t.financial_fact_reference('company',z,fid)

def test_stale_finance_ref_never_becomes_current_by_theme_generation():
 b=(FIX/'defense_economics.json').read_bytes();p=json.loads(b);i=next(i for i,v in enumerate(p['profiles']) if v['ticker_display']=='LMT');axis=p['profiles'][i]['axes']['economics'];axis['state']='stale'
 from engine.government_revenue.defense_economics import defense_economics_content_id
 p['content_id']=defense_economics_content_id(p);x=t.OwnerSnapshot('defense_economics',json.dumps(p).encode(),max(t._clocks(p)).isoformat(),'prepared-structural-fixture','qualified_public_display');ref=t.financial_fact_reference('econ',x,axis['facts'][0]['fact_id']);a={'munitions_replenishment':{'economics':dict(state='supported',reason_code='wrong_stale_promotion',references=[ref])}}
 with pytest.raises(ValueError,match='stale_finance_promotion'):compose(a,{'econ':x})
 a['munitions_replenishment']['economics']['state']='stale';assert compose(a,{'econ':x})

def test_current_exposure_requires_exact_reviewed_entity_path():
 a=assignment();a['shipbuilding']['exposure']['references']=a['shipbuilding']['exposure']['references'][:1]
 with pytest.raises(ValueError,match='identity_path_missing'):compose(a)
 a=assignment();a['shipbuilding']['exposure']['references'][1]['pointer']='/issuers/4/entities/0';a['shipbuilding']['exposure']['references'][1]['row_id']='legal:gd:bath-iron-works-corp'
 with pytest.raises(ValueError,match='identity_path_missing'):compose(a)

def test_notification_stage_cannot_be_presented_as_funded_demand():
 a=assignment();a['nato_fms_demand']['funding_stage']['state']='supported';a['nato_fms_demand']['funding_stage']['reason_code']='funded_demand'
 with pytest.raises(ValueError,match='notification_stage_promotion'):compose(a)

def test_next_event_cannot_reference_country_or_program_identity():
 a=assignment();ref=a['nato_fms_demand']['next_event']['references'][0];ref['pointer']=ref['pointer'].replace('/advancement_condition','/customer_country')
 with pytest.raises(ValueError,match='condition_reference_required'):compose(a)
 o=owners();g=json.loads(o['ontology'].raw_bytes);a={'shipbuilding':{'next_event':dict(state='supported',reason_code='not_a_milestone',references=[dict(owner_key='ontology',pointer='/programs/0',row_id=g['programs'][0]['id'])])}}
 with pytest.raises(ValueError,match='milestone_reference_required'):compose(a,o)
