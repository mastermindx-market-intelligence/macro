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


# Native published-owner shape with deliberately different coverage denominators.
# No metrics are reconstructed or acquired by these tests.
SPACE_NOW='2026-10-20T08:00:00+00:00'
SPACE_PULSE={'schema': 'group_pulse.v1', 'authority': 'context_only', 'generated_at': '2026-10-19T11:57:05+00:00', 'basket_id': 'space_economy', 'as_of': '2026-10-14', 'n_members': 15, 'n_covered': 15, 'participation': {'activity_share': 0.4, 'activity_n': 6, 'trend_share_50d': 0.0667, 'trend_n_50d': 15, 'trend_share_200d': 0.0714, 'trend_n_200d': 14, 'activity_basis': {'ret_only': 0, 'ret_and_volume': 6}}, 'direction': {'agreement_pct': 1.0, 'n_active': 6, 'sign': 'down', 'median_move_spy_adj': -0.05713, 'cohesion': 0.5655, 'leader': {'ticker': 'BKSY', 'kind': 'activity'}, 'strongest': {'ticker': 'KRMN', 'ret': 0.0105}, 'weakest': {'ticker': 'BKSY', 'ret': -0.0942}}, 'arc': {'state': 'washout_complete_awaiting_reclaim', 'washed_out_share': 1.0, 'washed_out_n': 12, 'washout_readable_n': 12, 'reclaimed_20d_share': 0.0, 'reclaimed_readable_n': 12, 'capitulation_median_age_d': 27, 'stage2_share': 0.3846, 'stage4_share': 0.3846, 'staged_n': 13, 'drawdown_pctile_own_history': 1.0, 'null_disclosure': 'oracle_p8'}, 'episode': {'active_now': False, 'current_start': None, 'sessions_active': 0, 'state_change': 'quiet'}, 'coverage_warnings': []}

def space_context_bundle(root):
 from hashlib import sha256
 from engine.government_revenue import defense_participation_context as ctx
 names=['RKLB','FLY','ASTS','IRDM','VSAT','PL','BKSY','LUNR','RDW','KTOS','KRMN','MDA','SPCX','VOYG','SATL']
 members=[dict(ticker=n,added='2023-05-09',removed=None,curated_added='2026-06-19') for n in names]
 membership=dict(version='2026-08-07',history_note='Current roster back-projected over available price history.',baskets={'space_economy':dict(created='2026-06-19',curated='2026-06-22',members=members)})
 observation=dict(effective_as_of='2026-10-14',configured_members=names,configured_n=15,observed_members=[n for n in names if n!='KRMN'],observed_n=14,coverage=14/15,missing_at_asof=['KRMN'],basis='exact_close_at_effective_as_of')
 baskets=dict(as_of='2026-10-14',baskets=[dict(id='space_economy',observation=observation)])
 for path,value in zip(ctx.OWNER_PATHS[:3],(membership,{'space_economy':deepcopy(SPACE_PULSE)},baskets)):
  file=root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps(value))
 return dict(basket_id='space_economy',source_commit='a'*40,verified_at=SPACE_NOW,decision_ref='test integration decision only',sources={p:sha256((root/p).read_bytes()).hexdigest() for p in ctx.OWNER_PATHS[:3]})

def test_builder_consumes_direct_commercial_space_without_quartet_substitution(tmp_path):
 r,path=reviewed(tmp_path)
 before=b.build_public_theme_candidate(tmp_path,generated_at=SPACE_NOW,as_of=SPACE_NOW)
 r['commercial_space_context']=space_context_bundle(tmp_path);path.write_text(json.dumps(r))
 after=b.build_public_theme_candidate(tmp_path,generated_at=SPACE_NOW,as_of=SPACE_NOW)
 assert after['optional_context']['state']=='verified_native_published_context'
 assert after['reference_snapshot']==before['reference_snapshot']
 for old,new in zip(before['public_disclosure']['themes'],after['public_disclosure']['themes']):
  assert old['rail_states']==new['rail_states'] and old['research_state']==new['research_state']
  if old['theme_id']!='space':assert old==new
 space=after['public_disclosure']['themes'][2]
 assert 'Commercial-space basket context (space_economy; stale)' in space['known_en']
 assert 'pulse coverage 15/15 at 2026-10-14' in space['known_en']
 assert 'exact-close coverage 14/15 at 2026-10-14 (missing: KRMN)' in space['known_en']
 assert 'back-projected' in space['known_en'] and 'not a government-space portfolio' in space['known_en']
 assert '商业航天' in space['known_zh'] and '脉冲覆盖15/15' in space['known_zh'] and '精确收盘覆盖14/15' in space['known_zh']
 sources=[s for s in space['sources'] if s['owner_key']=='commercial_space_context']
 assert len(sources)==3 and all(s['issuer_id'] is None and s['security_id'] is None and s['source_available_at'] is None for s in sources)
 assert all(s['house_known_at']==SPACE_NOW and s['url'].startswith('https://github.com/mastermindx-market-intelligence/macro/blob/'+'a'*40+'/') for s in sources)
 assert all(r['research_state']=='EVIDENCE_INSUFFICIENT' for r in after['public_disclosure']['themes'])
 assert d.validate_public_theme_disclosure(after['public_disclosure'])

@pytest.mark.parametrize('fault',['missing','changed_hash','wrong_basket','future_clock','coverage','missing_coverage','wrong_cutoff','bool_count','symlink','binding_shape','coverage_nan','coverage_inf','coverage_bool','source_shape','pulse_shape','observation_shape'])
def test_invalid_optional_group_is_local_and_drops_every_new_claim(tmp_path,fault):
 from hashlib import sha256
 from engine.government_revenue import defense_participation_context as ctx
 r,path=reviewed(tmp_path);before=b.build_public_theme_candidate(tmp_path,generated_at=SPACE_NOW,as_of=SPACE_NOW)
 binding=space_context_bundle(tmp_path);file=tmp_path/ctx.OWNER_PATHS[1]
 if fault=='missing':file.unlink()
 elif fault=='changed_hash':file.write_bytes(file.read_bytes()+b' ')
 elif fault=='symlink':
  target=tmp_path/'pulse-copy.json';target.write_bytes(file.read_bytes());file.unlink();file.symlink_to(target)
 elif fault=='binding_shape':binding['sources']['other.json']='a'*64
 elif fault=='source_shape':binding['sources']=None
 else:
  relative=ctx.OWNER_PATHS[1] if fault in ('wrong_basket','future_clock','pulse_shape') else ctx.OWNER_PATHS[2]
  file=tmp_path/relative;value=json.loads(file.read_bytes())
  if fault=='wrong_basket':value['space_economy']['basket_id']='defense'
  elif fault=='future_clock':value['space_economy']['generated_at']='2999-01-01T00:00:00Z'
  elif fault=='coverage':value['baskets'][0]['observation']['coverage']=1.0
  elif fault=='missing_coverage':del value['baskets'][0]['observation']['coverage']
  elif fault=='wrong_cutoff':value['as_of']='2026-10-13'
  elif fault=='bool_count':value['baskets'][0]['observation']['observed_n']=True
  elif fault=='coverage_nan':value['baskets'][0]['observation']['coverage']=float('nan')
  elif fault=='coverage_inf':value['baskets'][0]['observation']['coverage']=float('inf')
  elif fault=='coverage_bool':value['baskets'][0]['observation']['coverage']=True
  elif fault=='pulse_shape':value['space_economy']=[]
  elif fault=='observation_shape':value['baskets'][0]['observation']=None
  file.write_text(json.dumps(value));binding['sources'][relative]=sha256(file.read_bytes()).hexdigest()
 r['commercial_space_context']=binding;path.write_text(json.dumps(r))
 after=b.build_public_theme_candidate(tmp_path,generated_at=SPACE_NOW,as_of=SPACE_NOW)
 assert after['optional_context']['state']=='source_unavailable' and after['optional_context']['reason']
 assert after['reference_snapshot']==before['reference_snapshot']
 assert after['public_disclosure']==before['public_disclosure']


def test_optional_context_keeps_distinct_dates_and_localized_empty_missing(tmp_path):
 from hashlib import sha256
 from engine.government_revenue import defense_participation_context as ctx
 r,path=reviewed(tmp_path);binding=space_context_bundle(tmp_path)
 file=tmp_path/ctx.OWNER_PATHS[2];value=json.loads(file.read_bytes());value['as_of']='2026-10-15'
 observation=value['baskets'][0]['observation'];observation.update(effective_as_of='2026-10-15',observed_members=observation['configured_members'],observed_n=15,coverage=1.0,missing_at_asof=[])
 file.write_text(json.dumps(value));binding['sources'][ctx.OWNER_PATHS[2]]=sha256(file.read_bytes()).hexdigest()
 r['commercial_space_context']=binding;path.write_text(json.dumps(r))
 out=b.build_public_theme_candidate(tmp_path,generated_at=SPACE_NOW,as_of=SPACE_NOW)
 assert out['optional_context']['state']=='verified_native_published_context'
 row=out['public_disclosure']['themes'][2]
 assert 'pulse coverage 15/15 at 2026-10-14' in row['known_en']
 assert 'exact-close coverage 15/15 at 2026-10-15' in row['known_en']
 assert '缺失：无' in row['known_zh'] and 'none' not in row['known_zh']
 assert 'recomputing' not in row['known_en'] and '重新计算' not in row['known_zh']
 assert {s['title'] for s in row['sources'] if s['owner_key']=='commercial_space_context'}=={'Space Economy membership','Space Economy pulse','Space Economy exact-close coverage'}
