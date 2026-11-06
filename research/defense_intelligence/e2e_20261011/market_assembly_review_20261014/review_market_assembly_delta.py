from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256,sha1
import json,sys,copy,re,subprocess
R=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main');P=Path(__file__).parent;sys.path.insert(0,str(R))
from engine.government_revenue import program_theme_reviewed_builder as b
from engine.government_revenue import program_theme_context as t
from engine.government_revenue.defense_participation_context import participation_input_paths
oldraw=(P/'approved_defense_economics.json').read_bytes();newraw=(R/'data/government_revenue/defense_economics.json').read_bytes();assert sha256(oldraw).hexdigest()=='9d80423c7de3ad9a7c0c3b93b714bc6559c101467b2e3795d18c91452cb5e2e0';old=json.loads(oldraw);new=json.loads(newraw)
reviewraw=(R/t.THEME_REVIEW_PATH).read_bytes();review=json.loads(reviewraw);candidate=copy.deepcopy(review);decl=review['owners']['quartet_economics'];now=datetime.now(timezone.utc).isoformat()
def owner(raw):
 payload=json.loads(raw);available=max([t._instant(decl['available_at'])]+list(t._clocks(payload))).isoformat();return t.OwnerSnapshot('defense_economics',raw,available,decl['admission_ref'],decl['rights_state'])
oldowner=owner(oldraw);newowner=owner(newraw);oldowner.payload();newowner.payload()
oldpulse=json.loads((P/'approved_pulse.json').read_bytes());newpulse=json.loads((R/'site/basketdata/pulse.json').read_bytes());assert sha256((P/'approved_pulse.json').read_bytes()).hexdigest()==old['source_bindings'][old['profiles'][0]['axes']['participation']['owner_ref']]['sha256'];assert sha256((R/'site/basketdata/pulse.json').read_bytes()).hexdigest()==new['source_bindings'][new['profiles'][0]['axes']['participation']['owner_ref']]['sha256']
assert {k:v for k,v in oldpulse['defense'].items() if k!='generated_at'}=={k:v for k,v in newpulse['defense'].items() if k!='generated_at'},'material_market_semantics_changed'
# The approved projection consumed the exact old native pulse and same member/
# benchmark bytes. Verify all 26 inputs against its original checkpoint tree.
paths=participation_input_paths(R);rawtree=subprocess.run(['git','ls-tree','-r','27eb11189fa9','--',*paths],cwd=R,capture_output=True,check=True,env={**__import__('os').environ,'GIT_OPTIONAL_LOCKS':'0'}).stdout.decode();oids={line.split('\t')[1]:line.split()[2] for line in rawtree.splitlines()};changed_native=[]
for path in paths:
 raw=(R/path).read_bytes();oid=sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
 if oid!=oids.get(path):changed_native.append(path)
assert changed_native==['site/basketdata/pulse.json'],changed_native
changes=[]
for theme,rails in review['assignments'].items():
 item=rails['market_context'];assert len(item['references'])==1;ref=item['references'][0];assert ref['owner_key']=='quartet_economics' and ref['row_id']=='cik:0000936468' and ref['pointer'].endswith('/axes/participation');token=f'{theme}/market_context/0';prior=b.stable_reference(ref,oldowner);current=b.stable_reference(ref,newowner);fpold=b.reference_fingerprint(prior,'market_context',oldowner,now,version=review['schema_version']);fpnew=b.reference_fingerprint(current,'market_context',newowner,now,version=review['schema_version']);assert fpold==review['reference_fingerprints'][token],'old_selected_approval_mismatch';assert fpold!=fpnew
 a=old['profiles'][0]['axes']['participation'];c=new['profiles'][0]['axes']['participation'];allowed={'evidence_refs','owner_ref','observed_at','summary_en','summary_zh'};assert {k:v for k,v in a.items() if k not in allowed}=={k:v for k,v in c.items() if k not in allowed}
 for language in ('en','zh'):
  summary=a['summary_'+language].replace(oldpulse['defense']['generated_at'],newpulse['defense']['generated_at']);assert summary==c['summary_'+language],'narrative_semantics_changed'
 for oldref in a['evidence_refs']:
  kind=oldref.split(':')[2];newref=next(x for x in c['evidence_refs'] if x.split(':')[2]==kind);x=old['source_bindings'][oldref];y=new['source_bindings'][newref];exclude={'observed_at'}|({'sha256','content_id'} if kind=='pulse' else set());assert {k:v for k,v in x.items() if k not in exclude}=={k:v for k,v in y.items() if k not in exclude},'source_identity_rights_subject_or_basis_changed'
 candidate['reference_fingerprints'][token]=fpnew;candidate['assignments'][theme]['market_context']['references'][0]=current;changes.append({'token':token,'old_fingerprint':fpold,'new_fingerprint':fpnew,'state_preserved':item['state'],'reason_preserved':item['reason_code']})
assert len(changes)==6
assert candidate['assignments']==review['assignments']
changedtokens={x['token'] for x in changes};assert all(candidate['reference_fingerprints'][key]==value for key,value in review['reference_fingerprints'].items() if key not in changedtokens)
candidate['owners']['quartet_economics'].update(sha256=sha256(newraw).hexdigest(),available_at=newowner.available_at);candidate['reviewed_at']=now;candidate['reviewer']=review['reviewer']+'; coordinator01a13839 explicit6marketassemblyreceipt review under root01a13300, rootintegrationreviewrequired'
receipt={'schema':'defense.explicit_market_assembly_leaf_review.v1','state':'QUALIFIED_EXPLICIT_REVIEW_CANDIDATE_NOT_PROMOTED','source_head':'7c8069a604c77a63ef4c048263cef45f262d0bdc','approved_financial_sha256':sha256(oldraw).hexdigest(),'current_financial_sha256':sha256(newraw).hexdigest(),'original_review_sha256':sha256(reviewraw).hexdigest(),'reviewed_at':now,'old_pulse_sha256':sha256((P/'approved_pulse.json').read_bytes()).hexdigest(),'new_pulse_sha256':sha256((R/'site/basketdata/pulse.json').read_bytes()).hexdigest(),'native_defense_changed_fields':['generated_at'],'native_input_inventory_count':len(paths),'changed_native_input_paths':changed_native,'selected_leaf_changed_fields':['evidence_refs','owner_ref','observed_at','summary_en','summary_zh'],'material_market_semantics_unchanged':True,'source_identity_rights_subject_basis_unchanged':True,'old_market_as_of':oldpulse['defense']['as_of'],'current_market_as_of':newpulse['defense']['as_of'],'no_freshness_promotion':True,'six_changed_tokens':changes,'unrelated_fingerprints_preserved':len(review['reference_fingerprints'])-len(changes),'old_review_history_preserved':True,'code_normalizer_changed':False,'root_integration_review_required':True}
(P/'EXPLICIT_MARKET_ASSEMBLY_REVIEW.json').write_text(json.dumps(receipt,indent=2));(P/'program_theme_assignments.market-review-candidate.json').write_text(json.dumps(candidate,indent=2));(P/'approved_program_theme_assignments.json').write_bytes(reviewraw);print(json.dumps({k:v for k,v in receipt.items() if k!='six_changed_tokens'},indent=2))
