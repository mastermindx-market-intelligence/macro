import os
from pathlib import Path
import importlib.util,sys,json,gzip,os
from copy import deepcopy
import pytest
from hashlib import sha256
try:
 from engine.government_revenue import budget_allocation_context as a
except ImportError:
 import budget_allocation_context as a
R=Path(__file__).parent;REPO=Path(os.environ.get('DEFENSE_REPO_ROOT') or next((str(p) for p in Path(__file__).resolve().parents if (p/'engine/government_revenue').is_dir()), str(Path(__file__).resolve().parents[1])))
NOW='2026-10-13T06:00:00+00:00'
FIXTURE=Path(os.environ.get('DEFENSE_BUDGET_FIXTURE_ROOT',str(R/'fixtures/government_revenue/budget_allocation')))
PROVENANCE=json.loads((FIXTURE/'provenance.json').read_text());REC=dict(requested_url=PROVENANCE['source_url'],resolved_url=PROVENANCE['source_url'],retrieved_at=PROVENANCE['observed_at'])
PDF=gzip.decompress((FIXTURE/'fy2026_mandatory_allocation.pdf.gz').read_bytes());assert sha256(PDF).hexdigest()==PROVENANCE['source_sha256']

def receipt():return a.build_allocation_plan_receipt(source_url=REC['requested_url'],final_url=REC['resolved_url'],pdf_bytes=PDF,observed_at=REC['retrieved_at'],known_at=REC['retrieved_at'],source_document_date='2026-05-04')[0]
@pytest.fixture(scope='module')
def doc():return a.project_allocation_document(receipt(),pdf_bytes=PDF,sections=('20002','20003','20004'))

def test_actual_section20003_replays_edition_page_span_and_source_units(doc):
 r=receipt();assert a.validate_allocation_document(doc,receipt=r,pdf_bytes=PDF)
 row=next(x for x in doc['allocations'] if x['section']=='SEC. 20003');assert [x['value'] for x in row['amounts']]==['34.0','24379.0',None,None,None,'24413.0']
 assert row['source_span']['pdf_page_1based']==5 and row['source_span']['printed_page_label']=='1'
 assert row['program_key'] is row['issuer_ref'] is row['economic_weight'] is None
 assert row['amounts'][-1]['amount_kind']=='printed_section_total'
 assert doc['source_published_at'] is None and doc['source_document_date']=='2026-05-04'
 assert doc['observed_at']==REC['retrieved_at'] and doc['known_at']==REC['retrieved_at']
 assert r['storage_state']=='local_evidence_only' and r['storage_receipt'] is None

@pytest.mark.parametrize('mutator',[
 lambda d:d.update({'content_sha256':'a'*64}),
 lambda d:d.update({'document_stage':'appropriation_enacted'}),
 lambda d:d.update({'exhibit':'p1'}),
 lambda d:d['allocations'][1].update({'program_key':'dod-program:invented'}),
 lambda d:d['allocations'][1]['amounts'][1].update({'currency':'EUR'}),
 lambda d:d['allocations'][1]['amounts'][1].update({'unit':'USD_billion'}),
 lambda d:d['allocations'][1]['amounts'][1].update({'fiscal_year':2027}),
 lambda d:d['allocations'][1]['amounts'][1].update({'value':'99999.0'}),
 lambda d:d['allocations'][1]['source_span'].update({'span_start_byte':0}),
 lambda d:d['allocations'][1]['source_span'].update({'text_sha256':'b'*64}),
 lambda d:d['allocations'][1].update({'issuer_ref':'central:LMT'}),
 lambda d:d.update({'source_published_at':'2026-05-07T09:12:10-04:00'}),
])
def test_context_rehash_does_not_admit_wrong_currency_year_stage_span_identity(doc,mutator):
 d=deepcopy(doc);mutator(d);d['context_id']=a.context_id(d)
 with pytest.raises(ValueError):a.validate_allocation_document(d,receipt=receipt(),pdf_bytes=PDF)

@pytest.mark.parametrize('field,value',[('content_sha256','f'*64),('page_count',90),('document_stage','obligation'),('source_document_date','2026-05-07'),('known_at','2026-05-04T00:00:00Z')])
def test_receipt_rehash_cannot_change_source_edition_or_clocks(field,value):
 r=receipt();r[field]=value;r['receipt_id']=a.receipt_id(r)
 with pytest.raises(ValueError):a.validate_allocation_plan_receipt(r,pdf_bytes=PDF)

def test_wrong_edition_and_unreviewed_host_refuse():
 r=receipt()
 with pytest.raises(ValueError,match='unreviewed_edition'):a.validate_allocation_plan_receipt(r,pdf_bytes=PDF+b'\n')
 with pytest.raises(ValueError,match='source_invalid'):a.build_allocation_plan_receipt(source_url='https://mirror.example/plan.pdf',final_url=REC['resolved_url'],pdf_bytes=PDF,observed_at=REC['retrieved_at'],known_at=REC['retrieved_at'],source_document_date='2026-05-04')

@pytest.fixture
def budget_candidate(tmp_path, monkeypatch):
 # Use the incumbent module object. The module guard checks every case, so
 # a module-scoped sys.modules swap cannot be made safe by late restoration.
 from engine.government_revenue import budget_program as p
 root=tmp_path/'budget-validation';contracts=root/'contracts/government_revenue';contracts.mkdir(parents=True)
 for name in ('government_budget_line.v1.schema.json','government_budget_edge.v1.schema.json','government_budget_program_graph.v1.schema.json'):
  (contracts/name).symlink_to(REPO/'contracts/government_revenue'/name)
 (contracts/'government_budget_program_graph.v1_1.schema.json').write_bytes((REPO/'contracts/government_revenue/government_budget_program_graph.v1_1.schema.json').read_bytes())
 monkeypatch.setattr(p,'_root',lambda supplied=None:root if supplied is None else Path(supplied))
 return p

@pytest.fixture
def graph(budget_candidate):
 base=json.loads(gzip.decompress((FIXTURE/'accepted_budget_graph.v1.json.gz').read_bytes()));assert budget_candidate.is_valid_budget_program_graph(base)
 out=a.compose_allocation_context_graph(base,receipt=receipt(),pdf_bytes=PDF,sections=('20002','20003','20004'),generated_at=NOW,as_of='2026-10-13',require_storage=False)
 return base,out

def test_existing_canonical_graph_extended_without_new_line_or_program_truth(graph,budget_candidate):
 base,out=graph
 assert out['schema_version']=='1.1.0' and budget_candidate.is_valid_budget_program_graph(out)
 for key in ('lines','programs','edges'):assert out[key]==base[key]
 assert out['documents'][:-1]==base['documents']
 for key in base['source_coverage']:assert out['source_coverage'][key]==base['source_coverage'][key]
 assert out['source_coverage']['appropriation_enacted']['status']=='uncollected'
 assert out['source_coverage']['execution']['status']=='uncollected'
 assert out['source_coverage']['legislative_allocations']['status']=='partial'
 from jsonschema import Draft202012Validator
 old=json.loads((REPO/'contracts/government_revenue/government_budget_program_graph.v1.schema.json').read_text())
 assert list(Draft202012Validator(old,registry=budget_candidate._schema_registry()).iter_errors(out))

def test_existing_publication_requires_real_object_write_readback(graph):
 base,_=graph
 with pytest.raises(ValueError,match='existing_object_write_readback_required'):a.compose_allocation_context_graph(base,receipt=receipt(),pdf_bytes=PDF,generated_at=NOW,as_of='2026-10-13')
 r=receipt();storage=dict(state='owner_object_verified',object_key=r['immutable_object_key'],sha256='c'*64,byte_count=len(PDF),verified_at=r['known_at'])
 with pytest.raises(ValueError,match='storage_binding_invalid'):a.build_allocation_plan_receipt(source_url=REC['requested_url'],final_url=REC['resolved_url'],pdf_bytes=PDF,observed_at=r['observed_at'],known_at=r['known_at'],source_document_date='2026-05-04',storage_receipt=storage)

@pytest.mark.parametrize('mutation',[
 lambda g:g['documents'][-1]['allocations'][0]['amounts'][0].update({'currency':'EUR'}),
 lambda g:g['documents'][-1]['allocations'][0]['amounts'][0].update({'fiscal_year':2027}),
 lambda g:g['documents'][-1]['allocations'][0].update({'program_key':'dod-program:guessed'}),
 lambda g:g['documents'][-1].update({'document_stage':'obligation'}),
 lambda g:g['documents'][-1]['allocations'].append(deepcopy(g['documents'][-1]['allocations'][0])),
])
def test_graph_reader_refuses_semantic_drift_after_both_hashes_recomputed(graph,budget_candidate,mutation):
 _,g=graph;g=deepcopy(g);mutation(g);g['documents'][-1]['context_id']=a.context_id(g['documents'][-1]);g['content_id']=budget_candidate.budget_program_graph_content_id(g)
 assert not budget_candidate.is_valid_budget_program_graph(g)

def test_public_context_adapter_cannot_drop_or_relabel_section20003(doc):
 display=a.allocation_context_display(doc)
 assert display['stage']=='allocation_plan' and display['label_en']=='Legislative allocation plan — documentary context'
 assert 'SEC. 20003' in [x['section'] for x in display['section_refs']]
 assert display['source_published_at'] is None
 assert 'obligation' in display['limitation_en'] and display['label_zh']
 bad=deepcopy(doc);bad['document_stage']='contract';bad['context_id']=a.context_id(bad)
 with pytest.raises(ValueError):a.allocation_context_display(bad)

def test_theme_owner_selects_exact_minor_schema_and_refuses_stage_promotion(graph,budget_candidate):
 name='budget_theme_minor_candidate';spec=importlib.util.spec_from_file_location(name,Path(os.environ.get('DEFENSE_THEME_MODULE',str(REPO/'engine/government_revenue/program_theme_context.py'))));t=importlib.util.module_from_spec(spec);sys.modules[name]=t;spec.loader.exec_module(t);t._SCHEMA_ROOT=budget_candidate._root()/'contracts/government_revenue'
 _,g=graph;b=json.dumps(g).encode();x=t.OwnerSnapshot('budget',b,NOW,'O2local_document_context_structural_test','qualified_public_display');assert x.payload()['schema_version']=='1.1.0'
 doc=g['documents'][-1];ref=dict(owner_key='budget',pointer='/documents/2/allocations/1',row_id=doc['context_id']);a1={'golden_dome':{'funding_stage':dict(state='partial',reason_code='allocation_plan_only',references=[ref])}}
 p=t.compose_program_theme_context(a1,owners={'budget':x},generated_at=NOW,as_of=NOW);assert t.validate_program_theme_context(p,owners={'budget':x})
 assert p['themes'][0]['rails']['funding_stage']['state']=='partial' and '24379' not in str(p)
 a1['golden_dome']['funding_stage']['state']='supported'
 with pytest.raises(ValueError,match='allocation_stage_promotion'):t.compose_program_theme_context(a1,owners={'budget':x},generated_at=NOW,as_of=NOW)

def test_daily_same_context_is_idempotent_and_revision_is_explicit(graph,budget_candidate):
 base,out=graph;replay=a.compose_allocation_context_graph(out,receipt=receipt(),pdf_bytes=PDF,sections=('20002','20003','20004'),generated_at=NOW,as_of='2026-10-13',require_storage=False)
 assert replay==out and len(replay['documents'])==len(base['documents'])+1
 r=receipt();r['known_at']='2026-10-13T04:00:00+00:00';r['receipt_id']=a.receipt_id(r)
 with pytest.raises(ValueError,match='revision_requires_review'):a.compose_allocation_context_graph(out,receipt=r,pdf_bytes=PDF,sections=('20002','20003','20004'),generated_at=NOW,as_of='2026-10-13',require_storage=False)

def test_existing_collected_input_reads_stored_body_only_and_validates_receipt(tmp_path):
 assert a.load_collected_allocation_context_input(tmp_path,store=object()) is None
 r=receipt();storage=dict(state='owner_object_verified',object_key=r['immutable_object_key'],sha256=r['content_sha256'],byte_count=len(PDF),verified_at=r['known_at'])
 r,_=a.build_allocation_plan_receipt(source_url=REC['requested_url'],final_url=REC['resolved_url'],pdf_bytes=PDF,observed_at=r['observed_at'],known_at=r['known_at'],source_document_date='2026-05-04',storage_receipt=storage)
 p=tmp_path/a.ALLOCATION_RECEIPT_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r))
 class OwnerReadStore:
  def __init__(self,body):self.body=body;self.calls=[]
  def get_bytes_strict_bounded(self,key,**kwargs):self.calls.append((key,kwargs));return self.body
 store=OwnerReadStore(PDF);loaded=a.load_collected_allocation_context_input(tmp_path,store=store)
 assert loaded==(r,PDF) and store.calls==[(r['immutable_object_key'],dict(expected_byte_length=len(PDF),max_byte_length=len(PDF)))]
 with pytest.raises(ValueError):a.load_collected_allocation_context_input(tmp_path,store=OwnerReadStore(PDF+b'\n'))

AG_FIRST='2026-10-18T04:10:00+00:00'
AG_GRAPH='2026-10-18T04:20:00+00:00'
AG_ASOF='2026-10-18T05:00:00+00:00'

def _agreement_graph():
 from tests.test_government_program_public_agreement import graph as ag_graph, claim as ag_claim
 g=ag_graph();g['public_agreement_assertions']=[ag_claim(g)]
 return g

def _mixed_theme_module(budget_candidate):
 name='budget_theme_minor_candidate_mixed'
 spec=importlib.util.spec_from_file_location(name,Path(os.environ.get('DEFENSE_THEME_MODULE',str(REPO/'engine/government_revenue/program_theme_context.py'))))
 t=importlib.util.module_from_spec(spec);sys.modules[name]=t;spec.loader.exec_module(t)
 t._SCHEMA_ROOT=budget_candidate._root()/'contracts/government_revenue'
 (t._SCHEMA_ROOT/'government_program_theme_public_disclosure.v1_1.schema.json').symlink_to(REPO/'contracts/government_revenue/government_program_theme_public_disclosure.v1_1.schema.json')
 return t

def _mixed_setup(budget_candidate,monkeypatch,graph_pair,ag_g):
 _,graph_data=graph_pair
 # One candidate context module instance owns every OwnerSnapshot so disclosure
 # recomposition sees the same classes; the disclosure file itself is unpatched.
 t=_mixed_theme_module(budget_candidate)
 owners={'budget':t.OwnerSnapshot('budget',json.dumps(graph_data).encode(),NOW,'O2local_document_context_structural_test','qualified_public_display'),
         'ontology':t.OwnerSnapshot('program_ontology',json.dumps(ag_g).encode(),AG_GRAPH,'synthetic-reviewed-source-only','qualified_public_display')}
 bref=dict(owner_key='budget',pointer='/documents/2/allocations/1',row_id=graph_data['documents'][-1]['context_id'])
 aref=dict(owner_key='ontology',pointer='/public_agreement_assertions/0',row_id=ag_g['public_agreement_assertions'][0]['id'])
 monkeypatch.setitem(sys.modules,'program_theme_context',t)
 spec=importlib.util.spec_from_file_location('budget_theme_disclosure_candidate_mixed',Path(os.environ.get('DEFENSE_DISCLOSURE_MODULE',str(REPO/'engine/government_revenue/program_theme_disclosure.py'))))
 d=importlib.util.module_from_spec(spec);sys.modules['budget_theme_disclosure_candidate_mixed']=d;spec.loader.exec_module(d)
 return t,d,owners,bref,aref

def test_golden_dome_mixed_allocation_and_agreement_keeps_both_partial_sources(budget_candidate,graph,monkeypatch):
 ag_g=_agreement_graph();t,d,owners,bref,aref=_mixed_setup(budget_candidate,monkeypatch,graph,ag_g)
 a1={'golden_dome':{'funding_stage':dict(state='partial',reason_code='mixed_allocation_and_prototype_agreement',references=[bref,aref]),
                    'next_event':dict(state='partial',reason_code='reported_launch_availability_target',references=[aref])}}
 p=t.compose_program_theme_context(a1,owners=owners,generated_at=AG_ASOF,as_of=AG_ASOF)
 assert t.validate_program_theme_context(p,owners=owners)
 rail=p['themes'][0]['rails']['funding_stage']
 assert rail['state']=='partial' and [r['row_id'] for r in rail['references']]==[bref['row_id'],aref['row_id']]
 assert set(p['owner_bindings'])=={'budget','ontology'} and '24379' not in json.dumps(p)
 receipts={k:dict(state='available',sha256=sha256(v.raw_bytes).hexdigest(),owner_alias_state='unchanged') for k,v in owners.items()}
 public=d.disclose_program_themes(p,owners=owners,current_owner_receipts=receipts)
 golden=public['themes'][0]
 assert public['schema_version']=='1.1.0'
 assert golden['rail_states']['funding_stage']=='partial' and golden['rail_states']['next_event']=='partial'
 assert golden['research_state']=='EVIDENCE_INSUFFICIENT'
 by={s['owner_key']:s for s in golden['sources']}
 assert set(by)=={'budget','ontology'}
 assert by['budget']['pointer']=='/documents/2/allocations/1' and by['ontology']['pointer']=='/public_agreement_assertions/0'
 assert by['budget']['documentary_class']=='allocation_plan'
 assert by['ontology']['documentary_class']=='prototype_agreement' and by['ontology']['source_publication_date']=='2026-07-13'
 assert 'allocation-plan' in golden['known_en'] and 'prototype agreement' in golden['known_en']
 assert '955' in golden['known_en'] and '1.75' in golden['known_en']
 assert 'do not add it to named-party values' in golden['known_en']
 assert '2028' in golden['next_en']

@pytest.mark.parametrize('field,expected',[
 ('drop_budget','mixed_allocation_agreement_classes_required'),
 ('drop_agreement','mixed_allocation_agreement_classes_required'),
 ('double_budget','mixed_allocation_agreement_classes_required'),
 ('double_agreement','mixed_allocation_agreement_classes_required'),
 ('stale_state','mixed_allocation_agreement_scope_invalid'),
 ('wrong_documentary_class','policy_context_reference_required'),
 ('wrong_theme','mixed_allocation_agreement_scope_invalid'),
 ('wrong_rail','mixed_allocation_agreement_scope_invalid'),
 ('wrong_state','mixed_allocation_agreement_scope_invalid'),
 ('allocation_reason','prototype_agreement_stage_promotion'),
 ('agreement_reason','allocation_stage_promotion'),
 ('nato_mixed_code','mixed_documentary_context_scope_invalid'),
])
def test_mixed_allocation_agreement_scope_and_class_negatives(budget_candidate,graph,monkeypatch,field,expected):
 ag_g=_agreement_graph();t,_,owners,bref,aref=_mixed_setup(budget_candidate,monkeypatch,graph,ag_g)
 rail=dict(state='partial',reason_code='mixed_allocation_and_prototype_agreement',references=[bref,aref])
 if field=='drop_budget':rail['references']=[aref]
 elif field=='drop_agreement':rail['references']=[bref]
 elif field=='double_budget':rail['references']=[bref,dict(bref)]
 elif field=='double_agreement':rail['references']=[bref,aref,dict(aref)]
 elif field=='stale_state':rail['state']='stale'
 elif field=='wrong_documentary_class':rail['references']=[bref,dict(owner_key='ontology',pointer='/evidence/0',row_id=ag_g['evidence'][0]['evidence_id'])]
 elif field=='wrong_theme':assignments={'nato_fms_demand':{'funding_stage':rail}}
 elif field=='wrong_rail':assignments={'golden_dome':{'exposure':rail}}
 elif field=='wrong_state':rail['state']='supported'
 elif field=='allocation_reason':rail['reason_code']='allocation_plan_only'
 elif field=='agreement_reason':rail['reason_code']='prototype_agreement_only'
 elif field=='nato_mixed_code':rail['reason_code']='mixed_documentary_context'
 if field not in ('wrong_theme','wrong_rail'):assignments={'golden_dome':{'funding_stage':rail}}
 with pytest.raises(ValueError,match=expected):
  t.compose_program_theme_context(assignments,owners=owners,generated_at=AG_ASOF,as_of=AG_ASOF)
