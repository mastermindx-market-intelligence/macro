import os
import importlib.util,json,sys
from pathlib import Path
from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator
r=Path(__file__).parent
spec=importlib.util.spec_from_file_location('ontology_nato_candidate',(r/'program_ontology.candidate.py' if (r/'program_ontology.candidate.py').exists() else Path(__import__('engine.government_revenue.program_ontology',fromlist=['__file__']).__file__)));po=importlib.util.module_from_spec(spec);sys.modules[spec.name]=po;spec.loader.exec_module(po)

def fixture(version='1.1.0'):
 p=json.loads((r/'fixtures/program_ontology.json').read_bytes());p['schema_version']=version
 receipts=json.loads((r/'primary-byte-receipts.json').read_text());n=next(x for x in receipts if x['reference_label']=='nato_hague')
 row=dict(evidence_id='ev:'+n['sha256'][:12],evidence_class='official_alliance_policy',sha256=n['sha256'],source_url=n['requested_url'],retrieved_from_url=n['resolved_url'],retrieved_at=n['retrieved_at'].split('.')[0]+'+00:00',known_at=n['retrieved_at'].split('.')[0]+'+00:00',claim_scopes=['policy_context'])
 p['evidence'].append(row);p['graph_known_at']=row['known_at'];p['graph_effective_at']=row['known_at'];return p,row

def test_actual_nato_source_bytes_can_be_policy_context_only():
 p,e=fixture();loaded=po.load_program_ontology_graph(p)
 assert loaded['programs']==json.loads((r/'fixtures/program_ontology.json').read_bytes())['programs']
 Draft202012Validator(json.loads((r/'government_program_ontology.v1_1.schema.json').read_text())).validate(p)
 assert e['sha256']==__import__('hashlib').sha256((r/'nato_hague.html').read_bytes()).hexdigest()

def test_v1_engine_and_schema_remain_strict():
 old=json.loads((r/'fixtures/program_ontology.json').read_bytes());assert po.load_program_ontology_graph(old)
 p,_=fixture('1.0.0')
 with pytest.raises(po.OntologyInputError):po.load_program_ontology_graph(p)
 original=Path(os.environ.get('DEFENSE_REPO_ROOT') or next((str(p) for p in Path(__file__).resolve().parents if (p/'engine/government_revenue').is_dir()), str(Path(__file__).resolve().parents[1])))/'contracts/government_revenue/government_program_ontology.v1.schema.json'
 assert list(Draft202012Validator(json.loads(original.read_text())).iter_errors(p))

@pytest.mark.parametrize('mutator',[
 lambda p,e:e.update({'claim_scopes':['role']}),
 lambda p,e:e.update({'claim_scopes':['policy_context','program_identity']}),
 lambda p,e:e.update({'source_url':'https://nato.int/en/example'}),
 lambda p,e:e.update({'source_url':'https://www.cbo.gov/publication/example'}),
 lambda p,e:e.update({'retrieved_from_url':'https://mirror.example/nato'}),
 lambda p,e:e.update({'evidence_class':'official_program_page'}),
 lambda p,e:p['programs'][0]['evidence_refs'].append(e['evidence_id']),
 lambda p,e:p['role_assertions'][0]['evidence_refs'].append(e['evidence_id']),
 lambda p,e:p['programs'][0]['source_identities'].append(dict(system='official_program_page',native_identifier='Golden Dome',evidence_ref=e['evidence_id'])),
 lambda p,e:p['milestones'][0]['evidence_refs'].append(e['evidence_id']),
])
def test_no_policy_host_or_identity_laundering(mutator):
 p,e=fixture();mutator(p,e)
 with pytest.raises(po.OntologyInputError):po.load_program_ontology_graph(p)

def test_explicit_existing_curate_seam_migrates_only_when_requested(tmp_path,monkeypatch):
 spec=importlib.util.spec_from_file_location('curate_nato_candidate',(r/'curate_program_ontology.candidate.py' if (r/'curate_program_ontology.candidate.py').exists() else Path(__import__('scripts.curate_government_program_ontology',fromlist=['__file__']).__file__)));curate=importlib.util.module_from_spec(spec);spec.loader.exec_module(curate);monkeypatch.setattr(curate,'po',po)
 p,e=fixture();target=tmp_path/'program_ontology.json';target.write_bytes((r/'fixtures/program_ontology.json').read_bytes())
 w=tmp_path/'worksheet.json';w.write_text(json.dumps(dict(contract=po.WORKSHEET_CONTRACT,schema_version=po.WORKSHEET_SCHEMA_VERSION,reviewed_at=e['known_at'],reviewer='O2 bounded curation proposal',coverage=[],rows=[dict(action='admit',target_kind='evidence',candidate_row=e)])))
 before=target.read_bytes();curate.curate_worksheet(w,target_path=target,check_only=True,schema_version='1.1.0');assert target.read_bytes()==before
 result=curate.curate_worksheet(w,target_path=target,schema_version='1.1.0');out=json.loads(target.read_text());assert out['schema_version']=='1.1.0' and any(x['evidence_id']==e['evidence_id'] for x in out['evidence'])
 assert out['programs']==json.loads(before)['programs']
 # Default producer and worksheet remain v1, avoiding silent migration.
 assert po.SCHEMA_VERSION=='1.0.0' and po.WORKSHEET_SCHEMA_VERSION=='1.0.0'
