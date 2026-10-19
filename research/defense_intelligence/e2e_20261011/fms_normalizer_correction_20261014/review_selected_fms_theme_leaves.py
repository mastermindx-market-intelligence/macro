"""Explicit selected-FMS-leaf review; never bulk fingerprint restamping."""
from pathlib import Path
import json,sys,hashlib,copy
from datetime import datetime,timezone
R=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main');P=Path(__file__).parent;sys.path.insert(0,str(R))
from engine.government_revenue import program_theme_reviewed_builder as b
from engine.government_revenue import program_theme_context as t
reviewraw=(R/t.THEME_REVIEW_PATH).read_bytes();review=json.loads(reviewraw);D=P/'retained-correction-current-availability/projection';out=copy.deepcopy(review);now=datetime.now(timezone.utc).isoformat();changes=[];unchanged=[];refusals=[]
for key,decl in review['owners'].items():
 if decl['owner_kind']!='fms':continue
 oldraw=(D/'original_fms_case_graph.json').read_bytes();newraw=(D/'fms_case_graph.json').read_bytes()
 def snapshot(raw):
  payload=json.loads(raw);available=max([t._instant(decl['available_at'])]+list(t._clocks(payload))).isoformat();return t.OwnerSnapshot('fms',raw,available,decl['admission_ref'],decl['rights_state'])
 oldowner=snapshot(oldraw);newowner=snapshot(newraw)
 for theme,rails in review['assignments'].items():
  for rail,item in rails.items():
   for i,ref in enumerate(item['references']):
    if ref['owner_key']!=key:continue
    token=f'{theme}/{rail}/{i}';prior=b.stable_reference(ref,oldowner);current=b.stable_reference(ref,newowner);oldfp=b.reference_fingerprint(prior,rail,oldowner,now,version=review['schema_version']);newfp=b.reference_fingerprint(current,rail,newowner,now,version=review['schema_version']);expected=review['reference_fingerprints'][token]
    if oldfp!=expected:refusals.append({'token':token,'reason':'prior_selected_FMS_approval_mismatch','expected':expected,'old':oldfp});continue
    if oldfp==newfp:unchanged.append(token);continue
    if ref['row_id']!='fms:transmittal:25-104':refusals.append({'token':token,'reason':'unrelated_FMS_leaf_changed'});continue
    rowold,nodeold=t._ref(prior,rail,{key:oldowner},t._instant(now));rownew,nodenew=t._ref(current,rail,{key:newowner},t._instant(now));rowfields=[k for k in rowold if rowold[k]!=rownew[k]]
    if set(rowfields)!={'contractors','observations'}:refusals.append({'token':token,'reason':'unapproved_case_semantics_change','fields':rowfields});continue
    # Narrow review admits a four-contractor print correction only. It confers
    # no reviewed contractor identity, workshare, stage or amount promotion.
    assert all(c['identity_state']=='not_reviewed' and c['issuer_ref'] is None for c in rownew['contractors'])
    changes.append({'token':token,'rail':rail,'row_id':ref['row_id'],'selected_pointer_old':prior['pointer'],'selected_pointer_current':current['pointer'],'old_fingerprint':oldfp,'new_fingerprint':newfp,'row_changed_fields':rowfields,'selected_node_changed':nodeold!=nodenew,'approval_basis':'only reviewed contractor count/location/grammatical-separator correction plus appended current-known interpretation observation; no stage/amount/identitypromotion'})
    out['assignments'][theme][rail]['references'][i]=current;out['reference_fingerprints'][token]=newfp
 out['owners'][key].update(sha256=hashlib.sha256(newraw).hexdigest(),available_at=newowner.available_at)
status='QUALIFIED_EXPLICIT_FMS_LEAF_REVIEW_CANDIDATE' if not refusals else 'REFUSED_REVIEW_CANDIDATE'
assert all(out['reference_fingerprints'][k]==v for k,v in review['reference_fingerprints'].items() if k not in {x['token'] for x in changes})
receipt={'schema':'defense.fms_selected_theme_leaf_review.v1','state':status,'review_time':now,'current_reviewer_native_coordinator':'01a13839-ad49-7001-b84c-288e98477b95','original_root':'01a13300-c75b-79c3-83f9-79b3b4c01dc7','original_review_sha256':hashlib.sha256(reviewraw).hexdigest(),'changed_tokens':changes,'unchanged_FMS_tokens':unchanged,'refusals':refusals,'unrelated_reference_fingerprints_preserved':True,'bulk_reapproval':False,'root_review_before_promotion':True}
(D/'SELECTED_FMS_THEME_LEAF_REVIEW.json').write_text(json.dumps(receipt,indent=2));(D/'original_program_theme_assignments.v1.json').write_bytes(reviewraw)
if not refusals:
 out['reviewed_at']=now;out['reviewer']='Root01a13300 commissioned coordinator01a13839 bounded F100 normalizer review; root integration review required';(D/'program_theme_assignments.review-candidate.json').write_text(json.dumps(out,indent=2))
print(json.dumps(receipt,indent=2))
