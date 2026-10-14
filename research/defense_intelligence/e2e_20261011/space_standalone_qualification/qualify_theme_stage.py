from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from copy import deepcopy
import sys,json,shutil
C=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/pr-9066-e4ea65fadb39fb56');W=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main');D=Path(__file__).parent;S=D/'theme-stage';S.mkdir(exist_ok=False);sys.path.insert(0,str(C))
from engine.government_revenue import program_theme_context as t,program_theme_reviewed_builder as b,program_theme_disclosure as d
review_path=Path('config/government_revenue/program_theme_assignments.v1.json');original=(W/review_path).read_bytes();review=json.loads(original);assert (C/review_path).read_bytes()==original
for key,ref in review['owners'].items():
 if ref['owner_kind']=='company_intelligence':continue
 target=S/ref['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((W/ref['path']).read_bytes())
shutil.copytree(D.parent/'isolated-owner-consumer/data/company_intelligence',S/'data/company_intelligence')
q=S/review_path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(original)
clock=datetime.now(timezone.utc).isoformat();_,before_assignments,before_owners=b.load_current_reviewed_theme_inputs(W,as_of=clock)
(S/review['owners']['quartet_economics']['path']).write_bytes((D/'FULL_ECONOMICS_STAGE.json').read_bytes())
_,staged_assignments,owners=b.load_current_reviewed_theme_inputs(S,as_of=clock)
# Existing semantic approvals must survive the new generation before selecting anything new.
comparison={};failed=[]
for theme,rails in review['assignments'].items():
 for rail,item in rails.items():
  for i,ref in enumerate(item['references']):
   token=f'{theme}/{rail}/{i}';key=ref['owner_key'];resolved=b.stable_reference(ref,owners[key])
   try:actual=b.reference_fingerprint(resolved,rail,owners[key],clock,version=review['schema_version']);same=actual==review['reference_fingerprints'][token]
   except ValueError:same=False
   comparison[token]=same
   if not same:failed.append(token)
(D/'SPACE_THEME_EXISTING_FINGERPRINTS.json').write_text(json.dumps({'count':len(comparison),'matches':comparison,'failures':failed},indent=2)+'\n')
assert all('/market_context/' in token for token in failed),failed
# Current broad-basket revisions retain stale review state; no market leaf is reminted.
p=owners['quartet_economics'].payload();refs=[];expected={'issuer_space_segment_'+x+suffix for x in ('sales','operating_profit','margin') for suffix in ('','_prior')}|{'issuer_space_gem63xl_unfavorable_eac'}
for pi,profile in enumerate(p['profiles']):
 if profile['ticker_display']!='NOC':continue
 for fi,fact in enumerate(profile['axes']['economics']['facts']):
  prefix='evt_cik0001133421_2026q2_results:'
  if fact['fact_id'].startswith(prefix) and fact['fact_id'][len(prefix):] in expected:refs.append(dict(owner_key='quartet_economics',pointer=f'/profiles/{pi}/axes/economics/facts/{fi}',row_id=fact['fact_id']))
assert len(refs)==7
# Explicit parent source review is limited to these seven exact source-backed leaves.
updated=deepcopy(review);oldrail=updated['assignments']['space']['economics'];assert len(oldrail['references'])==6
updated['assignments']['space']['economics']={'state':'partial','reason_code':'issuer_segment_context_no_program_allocation','references':refs}
for i,ref in enumerate(refs):updated['reference_fingerprints'][f'space/economics/{i}']=b.reference_fingerprint(ref,'economics',owners['quartet_economics'],clock,version=review['schema_version'])
updated['reviewed_at']=clock;updated['reviewer']='assigned-principal:01a13300:exact-Space-source-review';updated['owners']['quartet_economics']['sha256']=sha256(owners['quartet_economics'].raw_bytes).hexdigest();updated['owners']['quartet_economics']['available_at']=owners['quartet_economics'].available_at
q.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+'\n')
result=b.build_public_theme_candidate(S,generated_at=clock,as_of=clock);assert result['state']=='qualified_partial'
row=next(x for x in result['public_disclosure']['themes'] if x['theme_id']=='space');assert row['rail_states']['economics']=='partial' and row['rail_states']['contrary_case']=='partial';assert row['research_state']=='EVIDENCE_INSUFFICIENT';assert '2753' in row['known_en'] and '2646' in row['known_en'] and 'sales rose' in row['missing_en'];assert 'Defense Systems' not in row['known_en'];assert 'L3Harris' in row['known_en'];assert '91' in row['known_en'] and 'GEM63XL' in row['known_en'];assert 'estimated completion costs' in row['missing_en'];assert len([x for x in row['sources'] if ':issuer_space_' in x['row_id']])==7
for rail in ('exposure','funding_stage','next_event'):assert row['rail_states'][rail]=='source_unavailable'
assert updated['assignments']['space']['contrary_case']==review['assignments']['space']['contrary_case']
assert (W/review_path).read_bytes()==original and (C/review_path).read_bytes()==original
(S/'theme-public-disclosure.json').write_text(json.dumps(result['public_disclosure'],indent=2,ensure_ascii=False)+'\n');(S/'theme-reference-snapshot.json').write_text(json.dumps(result['reference_snapshot'],indent=2,ensure_ascii=False)+'\n')
r={'state':'STAGED_SPACE_SOURCE_TO_THEME_VERIFIED','existing_fingerprints_checked':len(comparison),'existing_fingerprints_preserved_before_change':sum(comparison.values()),'preexisting_market_leaves_not_reminted':failed,'new_space_economic_references':refs,'only_selected_seven_fingerprints_changed':True,'space_rail_states':row['rail_states'],'all_six_theme_research_states':{x['theme_id']:x['research_state'] for x in result['public_disclosure']['themes']},'canonical_config_unchanged':True,'canonical_financial_owner_unchanged':True,'publication':False,'stage':str(S),'reviewed_at':clock,'new_config_sha256':sha256(q.read_bytes()).hexdigest(),'display_sha256':sha256((S/'theme-public-disclosure.json').read_bytes()).hexdigest()};(D/'SPACE_THEME_STAGE_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
