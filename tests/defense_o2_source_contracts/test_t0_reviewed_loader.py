import os
from pathlib import Path
from copy import deepcopy
import importlib.util,sys,json
from hashlib import sha256
import pytest
R=Path(__file__).parent;REPO=Path(os.environ.get('DEFENSE_REPO_ROOT') or next((str(p) for p in Path(__file__).resolve().parents if (p/'engine/government_revenue').is_dir()), str(Path(__file__).resolve().parents[1])))
spec=importlib.util.spec_from_file_location('theme_budget_loader_candidate',(R/'program_theme_context.budget_candidate.py' if (R/'program_theme_context.budget_candidate.py').exists() else Path(__import__('engine.government_revenue.program_theme_context',fromlist=['__file__']).__file__)));t=importlib.util.module_from_spec(spec);sys.modules[spec.name]=t;spec.loader.exec_module(t);t._SCHEMA_ROOT=REPO/'contracts/government_revenue'
NOW='2026-10-13T08:00:00+00:00'

def review_fixture(root):
 snap=json.loads((R/'theme-context-with-reviewed-quartet.json').read_bytes());assignments={x['theme_id']:x['rails'] for x in snap['themes']};files={'fms':'fms_case_graph.json','ontology':'program_ontology.json','atlas':'identity_atlas.json','quartet_economics':'accepted_quartet_economics.json'};owners={}
 for key,file in files.items():
  source=R/file if key=='quartet_economics' else R/'fixtures'/file
  b=source.read_bytes();p=root/'data/government_revenue'/file;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);binding=snap['owner_bindings'][key]
  owners[key]=dict(owner_kind=binding['owner_kind'],path=str(p.relative_to(root)),sha256=sha256(b).hexdigest(),available_at=binding['available_at'],admission_ref=binding['admission_ref'],rights_state=binding['rights_state'])
 review=dict(contract=t.THEME_REVIEW_CONTRACT,schema_version='1.0.0',reviewed_at=NOW,reviewer='O2 actual source-only fixture review',owners=owners,assignments=assignments)
 p=root/t.THEME_REVIEW_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(review));return p,review

def test_builder_reads_configured_exact_owner_bytes_and_review_not_request(tmp_path):
 p,r=review_fixture(tmp_path);x=t.build_reviewed_program_theme_context(tmp_path,generated_at=NOW,as_of=NOW)
 owners=t.load_reviewed_program_theme_inputs(tmp_path)[1];assert t.validate_program_theme_context(x,owners=owners)
 assert sum(len(x['themes'][i]['rails']['economics']['references']) for i in(1,2))==11
 assert all(row['research_state']=='EVIDENCE_INSUFFICIENT' for row in x['themes'])
 assert 'value' not in str(x) and 'program_workshare' not in str(x)

@pytest.mark.parametrize('mutate',[
 lambda r:r['owners']['fms'].update({'sha256':'a'*64}),
 lambda r:r['owners']['fms'].update({'path':'../outside.json'}),
 lambda r:r['owners']['fms'].update({'path':'/etc/passwd'}),
 lambda r:r['owners']['fms'].update({'available_at':'2026-12-01T00:00:00Z'}),
 lambda r:r['owners']['fms'].update({'rights_state':'unqualified'}),
 lambda r:r['owners']['fms'].update({'admission_ref':''}),
 lambda r:r.update({'private_body':'SECRET'}),
 lambda r:r.update({'reviewed_at':'2026-01-01T00:00:00Z'}),
])
def test_review_or_owner_tamper_refuses_before_composition(tmp_path,mutate):
 p,r=review_fixture(tmp_path);mutate(r);p.write_text(json.dumps(r))
 with pytest.raises((ValueError,FileNotFoundError)):t.build_reviewed_program_theme_context(tmp_path,generated_at=NOW,as_of=NOW)

def test_current_owner_correction_requires_exact_review_binding(tmp_path):
 p,r=review_fixture(tmp_path);held=tmp_path/r['owners']['fms']['path'];held.write_bytes(held.read_bytes()+b'\n')
 with pytest.raises(ValueError,match='owner_hash_mismatch'):t.build_reviewed_program_theme_context(tmp_path,generated_at=NOW,as_of=NOW)

def test_nato_unhashable_reference_list_is_governed_error():
 spec=importlib.util.spec_from_file_location('nato_guard_candidate',(R/'program_ontology.guard_candidate.py' if (R/'program_ontology.guard_candidate.py').exists() else Path(__import__('engine.government_revenue.program_ontology',fromlist=['__file__']).__file__)));po=importlib.util.module_from_spec(spec);sys.modules[spec.name]=po;spec.loader.exec_module(po)
 p=json.loads((R/'fixtures/program_ontology.json').read_bytes());p['schema_version']='1.1.0';p['programs'][0]['evidence_refs']=[{'untrusted':'dictionary'}]
 with pytest.raises(po.OntologyInputError):po.load_program_ontology_graph(p)

@pytest.mark.parametrize('field,value',[('claim_scopes',[{'bad':'scope'}]),('claim_scopes',[['nested']]),('evidence_refs',[['nested']])])
def test_nato_malformed_nested_reference_shapes_return_governed_error(field,value):
 spec=importlib.util.spec_from_file_location('nato_guard_shape_candidate',(R/'program_ontology.guard_candidate.py' if (R/'program_ontology.guard_candidate.py').exists() else Path(__import__('engine.government_revenue.program_ontology',fromlist=['__file__']).__file__)));po=importlib.util.module_from_spec(spec);sys.modules[spec.name]=po;spec.loader.exec_module(po)
 p=json.loads((R/'fixtures/program_ontology.json').read_bytes());p['schema_version']='1.1.0'
 row=p['evidence'][0] if field=='claim_scopes' else p['programs'][0];row[field]=value
 with pytest.raises(po.OntologyInputError):po.load_program_ontology_graph(p)
