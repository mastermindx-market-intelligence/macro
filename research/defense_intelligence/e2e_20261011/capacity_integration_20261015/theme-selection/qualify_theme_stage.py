from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from copy import deepcopy
import sys,json,shutil
C=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/pr-9066-e4ea65fadb39fb56');W=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/pr-9066-e4ea65fadb39fb56');D=Path(__file__).parent;S=D/'theme-stage';S.mkdir(exist_ok=False);sys.path.insert(0,str(C))
from engine.government_revenue import program_theme_context as t,program_theme_reviewed_builder as b,program_theme_disclosure as d
review_path=Path('config/government_revenue/program_theme_assignments.v1.json');original=(W/review_path).read_bytes();review=json.loads(original);assert (C/review_path).read_bytes()==original
for key,ref in review['owners'].items():
 if ref['owner_kind']=='company_intelligence':continue
 target=S/ref['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((W/ref['path']).read_bytes())
shutil.copytree(W/'data/company_intelligence',S/'data/company_intelligence')
q=S/review_path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(original)
clock=datetime.now(timezone.utc).isoformat();_,before_assignments,before_owners=b.load_current_reviewed_theme_inputs(W,as_of=clock)
(S/review['owners']['quartet_economics']['path']).write_bytes((W/'data/government_revenue/defense_economics.json').read_bytes())
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
# The native ontology fingerprint intentionally binds the complete review-coverage
# collection. New PAC-3 coverage invalidates three otherwise unchanged old references.
# Adjudicate precisely this additive dependency against the still-qualified release owner.
RELEASE=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main')
release_review,_,release_owners=b.load_current_reviewed_theme_inputs(RELEASE,as_of=clock)
assert release_review==review
allowed={'nato_fms_demand/funding_stage/1','shipbuilding/exposure/0','shipbuilding/next_event/0'}
assert set(x for x in failed if '/market_context/' not in x)==allowed,failed
assert comparison['shipbuilding/exposure/1'], 'listing evidence must remain approved after exact sparse-input materialization'
ontology_requalification=[]
for token in sorted(allowed):
 theme,rail,index=token.split('/');ref=review['assignments'][theme][rail]['references'][int(index)];key=ref['owner_key'];old_owner=release_owners[key];new_owner=owners[key]
 assert old_owner.owner_kind==new_owner.owner_kind=='program_ontology'
 old_payload=old_owner.payload();new_payload=new_owner.payload()
 additions=[row for row in new_payload['review_coverage'] if row not in old_payload['review_coverage']]
 assert len(additions)==2 and {row['scope'] for row in additions}=={'program_identity','public_capacity'}
 assert all(row['subject_type']=='program' and row['subject_id']=='acq-program:pac-3-mse' for row in additions)
 assert all(row in new_payload['review_coverage'] for row in old_payload['review_coverage'])
 assert old_payload['overrides']==new_payload['overrides']
 prior=b.stable_reference(ref,old_owner);current=b.stable_reference(ref,new_owner)
 prior_row,prior_node=t._ref(prior,rail,{key:old_owner},t._instant(clock));current_row,current_node=t._ref(current,rail,{key:new_owner},t._instant(clock))
 assert prior_row==current_row and prior_node==current_node,token
 approved=b.reference_fingerprint(prior,rail,old_owner,clock,version=review['schema_version']);assert approved==review['reference_fingerprints'][token]
 shadow=deepcopy(new_payload);shadow['review_coverage']=old_payload['review_coverage']
 shadow_owner=t.OwnerSnapshot(new_owner.owner_kind,(json.dumps(shadow,ensure_ascii=False,indent=2)+'\n').encode(),new_owner.available_at,new_owner.admission_ref,new_owner.rights_state)
 assert b.reference_fingerprint(current,rail,shadow_owner,clock,version=review['schema_version'])==approved,token
 actual=b.reference_fingerprint(current,rail,new_owner,clock,version=review['schema_version'])
 ontology_requalification.append({'token':token,'old_fingerprint':approved,'new_fingerprint':actual,'selected_row_node_and_exact_source_dependencies_unchanged':True,'only_fingerprint_dependency_change':'two reviewed PAC-3 coverage rows added','new_coverage':additions})
 review['reference_fingerprints'][token]=actual
(D/'ONTOLOGY_REFERENCE_REQUALIFICATION.json').write_text(json.dumps({'state':'EXPLICIT_PARENT_REVIEW_OF_THREE_ADDITIVE_DEPENDENCY_CHANGES','independent_review':False,'rows':ontology_requalification,'market_fingerprints_rewritten':False,'original_stage_refusal_preserved':str(D.parent/'space-selection/qualification.log')},indent=2)+'\n')
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
updated['reviewed_at']=clock;updated['reviewer']='assigned-principal:01a13300:exact-Space-source-and-additive-PAC3-coverage-review';updated['owners']['quartet_economics']['sha256']=sha256(owners['quartet_economics'].raw_bytes).hexdigest();updated['owners']['quartet_economics']['available_at']=owners['quartet_economics'].available_at
q.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+'\n')
result=b.build_public_theme_candidate(S,generated_at=clock,as_of=clock);assert result['state']=='qualified_partial'
row=next(x for x in result['public_disclosure']['themes'] if x['theme_id']=='space');assert row['rail_states']['economics']=='partial' and row['rail_states']['contrary_case']=='partial';assert row['research_state']=='EVIDENCE_INSUFFICIENT';assert '2753' in row['known_en'] and '2646' in row['known_en'] and 'sales rose' in row['missing_en'];assert 'Defense Systems' not in row['known_en'];assert 'L3Harris' in row['known_en'];assert '91' in row['known_en'] and 'GEM63XL' in row['known_en'];assert 'estimated completion costs' in row['missing_en'];assert len([x for x in row['sources'] if ':issuer_space_' in x['row_id']])==7
for rail in ('exposure','funding_stage','next_event'):assert row['rail_states'][rail]=='source_unavailable'
assert updated['assignments']['space']['contrary_case']==review['assignments']['space']['contrary_case']
assert (W/review_path).read_bytes()==original and (C/review_path).read_bytes()==original
(S/'theme-public-disclosure.json').write_text(json.dumps(result['public_disclosure'],indent=2,ensure_ascii=False)+'\n');(S/'theme-reference-snapshot.json').write_text(json.dumps(result['reference_snapshot'],indent=2,ensure_ascii=False)+'\n')
r={'state':'STAGED_SPACE_SOURCE_TO_THEME_VERIFIED','existing_fingerprints_checked':len(comparison),'existing_fingerprints_preserved_before_change':sum(comparison.values()),'preexisting_market_leaves_not_reminted':[x for x in failed if '/market_context/' in x],'new_space_economic_references':refs,'only_selected_seven_and_three_explicitly_requalified_ontology_fingerprints_changed':True,'space_rail_states':row['rail_states'],'all_six_theme_research_states':{x['theme_id']:x['research_state'] for x in result['public_disclosure']['themes']},'canonical_config_unchanged':True,'canonical_financial_owner_unchanged':True,'publication':False,'stage':str(S),'reviewed_at':clock,'new_config_sha256':sha256(q.read_bytes()).hexdigest(),'display_sha256':sha256((S/'theme-public-disclosure.json').read_bytes()).hexdigest()};(D/'SPACE_THEME_STAGE_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
