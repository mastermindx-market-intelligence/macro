"""Bounded current-owner story tests; no source acquisition or promotion."""
import json,os,importlib.util,gzip
from pathlib import Path
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import pytest
from engine.government_revenue import program_theme_context as t
if os.environ.get('THEME_DISCLOSURE_PATH'):
 s=importlib.util.spec_from_file_location('engine.government_revenue.theme_disclosure_candidate',os.environ['THEME_DISCLOSURE_PATH']);d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
else:
 from engine.government_revenue import program_theme_disclosure as d
ROOT=Path(os.environ.get('DEFENSE_REPO_ROOT',Path(__file__).resolve().parents[1]))
FIXTURE=Path(os.environ.get('THEME_OWNER_FIXTURE',ROOT/'tests/fixtures/government_revenue/theme_interpretation_owner_inputs.json.gz'))

class RetainedTestOwner(t.OwnerSnapshot):
 @lru_cache(maxsize=16)
 def payload(self):
  # Validate each immutable actual fixture once; no production cache changes.
  return super().payload()

@lru_cache(maxsize=1)
def _held_inputs():
 held=json.loads(gzip.decompress(FIXTURE.read_bytes()));review=held['review'];owners={};current={}
 for key,r in review['owners'].items():
  raw=held['owner_json'][key].encode();assert sha256(raw).hexdigest()==r['sha256']
  owners[key]=RetainedTestOwner(r['owner_kind'],raw,r['available_at'],r['admission_ref'],r['rights_state']);current[key]={'state':'available','sha256':r['sha256'],'owner_alias_state':'unchanged'}
 p=t.compose_program_theme_context(review['assignments'],owners=owners,generated_at=review['reviewed_at'],as_of=review['reviewed_at'])
 return p,owners,current

def actual_inputs():
 p,o,c=_held_inputs();return p,o,deepcopy(c)

@lru_cache(maxsize=1)
def result():
 p,o,c=actual_inputs();return d.disclose_program_themes(p,owners=o,current_owner_receipts=c)

def test_six_differentiated_bilingual_conditional_stories_with_no_promotion():
 p,o,c=actual_inputs();before=deepcopy(p);out=d.disclose_program_themes(p,owners=o,current_owner_receipts=c)
 for original,row in zip(p['themes'],out['themes']):
  assert 'Conditional:' in row['missing_en'] and '条件情景：' in row['missing_zh']
  assert 'Invalidation:' in row['next_en'] and '失效条件：' in row['next_zh']
  assert row['rail_states']=={k:v['state'] for k,v in original['rails'].items()}
  assert row['research_state']=='EVIDENCE_INSUFFICIENT'
 assert len({r['missing_en'] for r in out['themes']})==6 and p==before
 assert d.validate_public_theme_disclosure(out)

def test_exact_issuer_baselines_not_theme_revenue():
 out=result();m=out['themes'][1];space=out['themes'][2]
 assert all(s in m['known_en'] for s in ('4101','594','14.5','8269','1042','12.6','2026Q2','USD million'))
 assert 'not munitions revenue' in m['missing_en']
 assert 'Defense Systems' in space['known_en'] and 'Missile Solutions' in space['known_en']
 assert 'not space-program revenue' in space['missing_en'] and '7.5' in space['known_en'] and '130' in space['known_en']

def test_marine_backlog_categories_preserved_not_summed_or_virginia_capture():
 row=result()['themes'][5]
 assert all(v in row['known_en'] for v in ('4660','342','7.3','42356','22826','65182','7442','72624'))
 assert all(v in row['known_en'] for v in ('funded backlog','unfunded backlog','total backlog','estimated potential contracts','total estimated contracts'))
 assert 'not separate amounts to add' in row['missing_en']
 assert 'broader segment' in row['missing_en'] and 'Virginia workshare and shareholder cash remain unknown' in row['missing_en']

@pytest.mark.parametrize('theme,owner',[('golden_dome','budget'),('munitions_replenishment','quartet_economics'),('space','quartet_economics'),('nato_fms_demand','fms'),('fleet_sustainment_upgrades','fms'),('shipbuilding','gd_company_economics')])
def test_changed_owner_cannot_keep_current_baseline_or_conditional_case(theme,owner):
 p,o,c=actual_inputs();c[owner]={'state':'available','sha256':'0'*64,'owner_alias_state':'advanced'}
 out=d.disclose_program_themes(p,owners=o,current_owner_receipts=c);r=next(r for r in out['themes'] if r['theme_id']==theme)
 assert 'Conditional:' not in r['missing_en']
 if owner in ('quartet_economics','gd_company_economics'):assert 'reported baseline:' not in r['known_en']
 assert r['research_state']=='EVIDENCE_INSUFFICIENT'

def test_no_current_receipts_no_source_grounded_story():
 p,o,c=actual_inputs();out=d.disclose_program_themes(p,owners=o,current_owner_receipts={})
 assert all(not r['sources'] and 'Conditional:' not in r['missing_en'] and 'reported baseline:' not in r['known_en'] for r in out['themes'])

def test_wrong_allocation_section_cannot_ground_dome_story():
 p,o,c=actual_inputs();budget=o['budget'];data=budget.payload();node=data['documents'][2]['allocations'][1]
 assert d._theme_economic_story('golden_dome',[('funding_stage','budget',{**node,'section':'SEC. 20004'},budget)]) is None

def test_no_notification_sum_no_dated_loa_prediction():
 rows=result()['themes'];n=rows[3];f=rows[4]
 assert 'notification ceiling is not issuer revenue' in n['missing_en'] and 'no advancement date is asserted' in n['next_en']
 assert 'No contractor mix or issuer capture is established' in f['missing_en']
 assert n['rail_states']['exposure']=='unreviewed' and f['rail_states']['exposure']=='unreviewed'

def test_original_source_identities_and_clocks_are_unchanged():
 p,o,c=actual_inputs();out=d.disclose_program_themes(p,owners=o,current_owner_receipts=c)
 for row in out['themes']:
  permitted={(r['owner_key'],r['row_id'],r['pointer']) for rail in next(x for x in p['themes'] if x['theme_id']==row['theme_id'])['rails'].values() for r in rail['references']}
  assert all((s['owner_key'],s['row_id'],s['pointer']) in permitted for s in row['sources'])
 assert out['as_of']==p['as_of'] and out['theme_content_id']==p['content_id'] and out['authority']==p['authority']


def test_nato_policy_wording_requires_actual_current_policy_anchor():
 p,o,c=actual_inputs();fms=o['fms'];case=fms.payload()['cases'][3]
 refs=[('funding_stage','fms',case,fms)]
 assert d._theme_economic_story('nato_fms_demand',refs) is None
 assert d._theme_economic_story('fleet_sustainment_upgrades',refs) is not None
 ontology=o['ontology'];policy=next(e for e in ontology.payload()['evidence'] if e.get('evidence_class')=='official_alliance_policy')
 assert d._theme_economic_story('nato_fms_demand',refs+[('funding_stage','program_ontology',policy,ontology)]) is not None


def test_named_electric_boat_case_requires_exact_reviewed_prime_role():
 p,o,c=actual_inputs();budget=o['budget'];gd=o['gd_company_economics'];ontology=o['ontology']
 refs=[('funding_stage','budget',budget.payload()['documents'][2]['allocations'][0],budget),('economics','company_intelligence',gd.payload()['facts'][1],gd)]
 role=ontology.payload()['role_assertions'][0]
 assert d._theme_economic_story('shipbuilding',refs+[('exposure','program_ontology',role,ontology)]) is not None
 for field,wrong in [('entity_id','legal:other'),('role','supplier'),('verification_state','unreviewed')]:
  assert d._theme_economic_story('shipbuilding',refs+[('exposure','program_ontology',{**role,field:wrong},ontology)]) is None
