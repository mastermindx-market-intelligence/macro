from pathlib import Path
import json
from copy import deepcopy
import pytest
try:
 from engine.government_revenue import program_theme_reviewed_builder as b
 from engine.government_revenue import program_theme_context as t
 from engine.government_revenue import program_theme_disclosure as d
except ImportError:
 import program_theme_reviewed_builder as b,program_theme_context as t,program_theme_disclosure as d
from test_program_theme_disclosure import inputs
NOW='2026-10-13T08:00:00+00:00'
R=Path(__file__).parent

def reviewed(root):
 p,o,c=inputs();r=json.loads((R/'program_theme_assignments.v1.json').read_bytes());r['assignments']={x['theme_id']:x['rails'] for x in p['themes']}
 for k,ref in r['owners'].items():
  file=root/ref['path'];file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(o[k].raw_bytes)
 r=b.make_reviewed_leaf_config(r,o,as_of=NOW)
 path=root/t.THEME_REVIEW_PATH;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(r));return r,path

def test_unchanged_reviewed_leaves_survive_byte_generation_change(tmp_path):
 r,path=reviewed(tmp_path);file=tmp_path/r['owners']['fms']['path'];file.write_bytes(file.read_bytes()+b'\n')
 review,a,o=b.load_current_reviewed_theme_inputs(tmp_path,as_of=NOW)
 assert a['nato_fms_demand']['funding_stage']['state']=='partial'
 assert review==r and len(a['munitions_replenishment']['economics']['references'])==6

def test_stable_id_relocates_approved_row_without_admitting_new_rows(tmp_path):
 r,path=reviewed(tmp_path);file=tmp_path/r['owners']['fms']['path'];p=json.loads(file.read_bytes());p['cases'].reverse();file.write_text(json.dumps(p))
 _,a,o=b.load_current_reviewed_theme_inputs(tmp_path,as_of=NOW)
 ref=a['nato_fms_demand']['funding_stage']['references'][0]
 assert t._pointer(o['fms'].payload(),ref['pointer'])[0]['case_key']==ref['row_id']
 assert a['nato_fms_demand']['funding_stage']['state']=='partial'

def test_material_source_row_correction_degrades_only_affected_rail(tmp_path):
 r,path=reviewed(tmp_path);file=tmp_path/r['owners']['fms']['path'];p=json.loads(file.read_bytes());row=next(x for x in p['cases'] if x['case_key']=='fms:transmittal:25-104');row['capability_title']+=' corrected';file.write_text(json.dumps(p))
 _,a,o=b.load_current_reviewed_theme_inputs(tmp_path,as_of=NOW)
 assert a['nato_fms_demand']['funding_stage']['state']=='stale' and a['nato_fms_demand']['funding_stage']['references']==[]
 assert a['munitions_replenishment']['economics']['state']=='partial'

def test_missing_theme_source_does_not_block_other_candidate_publication(tmp_path):
 r,path=reviewed(tmp_path);(tmp_path/r['owners']['fms']['path']).unlink()
 out=b.build_public_theme_candidate(tmp_path,generated_at=NOW,as_of=NOW)
 assert d.validate_public_theme_disclosure(out['public_disclosure'])
 assert out['public_disclosure']['themes'][3]['rail_states']['funding_stage']=='source_unavailable'
 path.unlink();out=b.build_public_theme_candidate(tmp_path,generated_at=NOW,as_of=NOW)
 assert out['state']=='source_unavailable' and len(out['public_disclosure']['themes'])==6

def test_reviewed_new_reference_cannot_enter_without_matching_fingerprint(tmp_path):
 r,path=reviewed(tmp_path);r['assignments']['space']['economics']['references'].append(deepcopy(r['assignments']['space']['economics']['references'][0]));path.write_text(json.dumps(r))
 with pytest.raises(ValueError,match='fingerprint_missing'):b.load_current_reviewed_theme_inputs(tmp_path,as_of=NOW)

def test_public_disclosure_has_own_identity_and_investor_copy():
 p,o,c=inputs();x=d.disclose_program_themes(p,owners=o,current_owner_receipts=c)
 assert d.validate_public_theme_disclosure(x) and x['content_id'].startswith('gptd1-')
 assert '所有者接纳' not in str(x) and 'owner must admit' not in str(x)
 assert '主承包商' in x['themes'][5]['known_zh']
 y=deepcopy(x);y['themes'][0]['known_en']='Invented evidence'
 with pytest.raises(ValueError,match='identity'):d.validate_public_theme_disclosure(y)
 y=deepcopy(x);y['themes'][0]['research_state']='SOURCE_CONTEXT_COMPLETE';y['content_id']=d.disclosure_content_id(y)
 with pytest.raises(ValueError,match='state'):d.validate_public_theme_disclosure(y)

def test_current_owner_receipt_revision_preserves_exact_approved_financial_fact():
 p,o,c=inputs();ref=p['themes'][1]['rails']['economics']['references'][0];old=o[ref['owner_key']]
 expected=b.reference_fingerprint(ref,'economics',old,NOW)
 body=deepcopy(old.payload());body['generated_at']='2026-10-13T05:00:00+00:00'
 for binding in body['source_bindings'].values():binding['sha256']='a'*64;binding['content_id']='updated_owner_generation';binding['owner_admission_ref']='new_verified_existing_generation'
 from engine.government_revenue.defense_economics import defense_economics_content_id
 body['content_id']=defense_economics_content_id(body)
 newer=t.OwnerSnapshot(old.owner_kind,json.dumps(body).encode(),NOW,old.admission_ref,old.rights_state)
 assert newer.payload() and b.reference_fingerprint(ref,'economics',newer,NOW)==expected

def mixed_fixture():
 p,o,c=inputs();source=Path(__file__).parent/'primary-byte-receipts.json';receipt=next(x for x in json.loads(source.read_text()) if x['reference_label']=='nato_hague')
 graph=deepcopy(o['ontology'].payload());graph['schema_version']='1.1.0';clock=receipt['retrieved_at'].split('.')[0]+'+00:00';e=dict(evidence_id='ev:'+receipt['sha256'][:12],evidence_class='official_alliance_policy',sha256=receipt['sha256'],source_url=receipt['requested_url'],retrieved_from_url=receipt['resolved_url'],retrieved_at=clock,known_at=clock,claim_scopes=['policy_context']);graph['evidence'].append(e);graph['graph_known_at']=graph['graph_effective_at']=clock
 old=o['ontology'];o['ontology']=t.OwnerSnapshot(old.owner_kind,json.dumps(graph).encode(),NOW,old.admission_ref,old.rights_state)
 a={x['theme_id']:deepcopy(x['rails']) for x in p['themes']};item=a['nato_fms_demand']['funding_stage'];item['reason_code']='mixed_documentary_context';item['references'].append(dict(owner_key='ontology',pointer=f"/evidence/{len(graph['evidence'])-1}",row_id=e['evidence_id']))
 c['ontology']['sha256']=__import__('hashlib').sha256(o['ontology'].raw_bytes).hexdigest()
 return a,o,c

def test_mixed_documentary_native_classes_remain_distinct_and_partial():
 a,o,c=mixed_fixture();p=t.compose_program_theme_context(a,owners=o,generated_at=NOW,as_of=NOW);x=d.disclose_program_themes(p,owners=o,current_owner_receipts=c);row=x['themes'][3]
 assert row['rail_states']['funding_stage']=='partial'
 assert 'estimated upper bound' in row['known_en'] and 'spending commitment is policy context' in row['known_en']
 classes={(s['documentary_class'],s['native_reason_code']) for s in row['sources']}
 assert ('congressional_notification','congressional_notification_only') in classes and ('alliance_policy','policy_commitment_only') in classes
 assert all(s['house_known_at'] for s in row['sources']) and 'contracted' in row['known_en']

@pytest.mark.parametrize('mutation',['supported','wrong_theme','single_class','wrong_native_reason'])
def test_invalid_mixed_context_never_upgrades_or_silently_drops_class(mutation):
 a,o,c=mixed_fixture();rail=a['nato_fms_demand']['funding_stage']
 if mutation=='supported':rail['state']='supported'
 elif mutation=='wrong_theme':a['golden_dome']['funding_stage']=rail;a['nato_fms_demand']['funding_stage']=dict(state='source_unavailable',reason_code='absent',references=[])
 elif mutation=='single_class':rail['references']=rail['references'][:1]
 else:rail['reason_code']='policy_commitment_only'
 with pytest.raises(ValueError):t.compose_program_theme_context(a,owners=o,generated_at=NOW,as_of=NOW)

def test_changed_leaf_public_state_stale_does_not_discard_other_themes(tmp_path):
 r,path=reviewed(tmp_path);file=tmp_path/r['owners']['fms']['path'];p=json.loads(file.read_bytes());next(x for x in p['cases'] if x['case_key']=='fms:transmittal:25-104')['capability_title']+=' corrected';file.write_text(json.dumps(p))
 out=b.build_public_theme_candidate(tmp_path,generated_at=NOW,as_of=NOW)
 assert out['state']=='qualified_partial'
 assert out['public_disclosure']['themes'][3]['rail_states']['funding_stage']=='stale'
 assert 'Virginia' in out['public_disclosure']['themes'][5]['known_en']
 assert out['reference_snapshot']['themes'][3]['rails']['funding_stage']['reason_code']=='reviewed_leaf_changed'

def test_rehashed_mixed_display_cannot_mislabel_native_class_or_promote_stage():
 a,o,c=mixed_fixture();p=t.compose_program_theme_context(a,owners=o,generated_at=NOW,as_of=NOW);out=d.disclose_program_themes(p,owners=o,current_owner_receipts=c)
 for change in ('class','stage'):
  x=deepcopy(out);row=x['themes'][3]
  if change=='class':next(s for s in row['sources'] if s['documentary_class']=='alliance_policy')['native_reason_code']='congressional_notification_only'
  else:row['rail_states']['funding_stage']='supported'
  x['content_id']=d.disclosure_content_id(x)
  with pytest.raises(ValueError):d.validate_public_theme_disclosure(x)
