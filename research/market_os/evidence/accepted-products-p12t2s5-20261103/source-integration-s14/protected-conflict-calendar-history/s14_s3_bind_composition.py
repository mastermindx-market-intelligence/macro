import json,hashlib,subprocess,re
from pathlib import Path
r=Path('/Volumes/Mastermind/evidence/accepted-products-p12t2s5-20261103');base='52abe2e183833a216267942a99513e6c9cbe062f';own='90c0b08fca5b45a261a7093cc46ac21aaa872544';cal='ed2529fc91d580a479ec797d5c31ed62053d6541'
def raw(ref,p):return subprocess.check_output(['git','show',ref+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
oldr=json.loads((r/'s14-fault-composed-native-business-emission.json').read_text());newr=json.loads((r/'s14-s3-native-business-emission.json').read_text())
a=raw(own,'site/macro_business_activity.html').decode();b=Path('site/macro_business_activity.html').read_text();oldstamp=oldr['actual_document_rendered_at'];newstamp=newr['actual_document_rendered_at'];assert a.count(oldstamp)==b.count(newstamp)==2
assert a.replace(oldstamp,newstamp)==b,'Business unexpected non-document-time delta'
assert oldr['input_sha256']==newr['input_sha256'] and oldr['asset_hashes']==newr['asset_hashes']
x=raw(base,'site/bonds.html').decode();y=Path('site/bonds.html').read_text();oldhref=re.findall(r'assets/css/[0-9a-f]{8}\.css\?v=[0-9a-f]{8}',x);newhref=re.findall(r'assets/css/[0-9a-f]{8}\.css\?v=[0-9a-f]{8}',y);assert len(oldhref)==len(newhref); differing=[(a,b) for a,b in zip(oldhref,newhref) if a!=b]; assert len(differing)==1; oldhref,newhref=map(lambda v:[v],differing[0])
assert x.replace(oldhref[0],newhref[0])==y,'Bonds financial body or clocks drifted'
assert raw(base,'site/commodities.html')==Path('site/commodities.html').read_bytes()
d=json.loads((r/'s14-commodity-final-composition.json').read_text());entries=[]
for line in d['git_entries']:
 mode_blob,p=line.split('\t');mode,_,oldblob=mode_blob.split();current=subprocess.check_output(['git','ls-files','-s','--',p],text=True).strip().split();blob=hashlib.sha1(b'blob '+str(len(Path(p).read_bytes())).encode()+b'\0'+Path(p).read_bytes()).hexdigest()
 assert current[0]==mode,p
 if p not in ['.github/ci/legacy-jobs.yml','site/commodities.html','site/macro_business_activity.html']:assert oldblob==blob,p
 entries.append({'path':p,'mode':mode,'blob':blob,'sha256':sha(Path(p).read_bytes()),'equals_reviewed_90':oldblob==blob})
cm=json.loads(Path('/Volumes/Mastermind/evidence/history-retained-classification-p12t45-20261104/combined-release-input.json').read_text())
for p,v in cm['paths'].items():
 assert sha(Path(p).read_bytes())==v['sha256'];assert subprocess.check_output(['git','ls-files','-s','--',p],text=True).split()[0]==v['mode']
 if not any(e['path']==p for e in entries):entries.append({'path':p,**v})
fixtures=subprocess.check_output(['git','ls-tree','-r',own,'--','tests/fixtures/macro_suite_t11'],text=True)
assert fixtures==subprocess.check_output(['git','ls-files','-s','tests/fixtures/macro_suite_t11'],text=True).replace(' 0\t','\t').replace('100644 ','100644 blob '),'frozen fixtures changed'
record={'task':'P12.T2.S14.S3','source_before':own,'protected_base':base,'calendar_history':cal,'review_scope':'semantic merge conflict and exact reviewed cohort integration only; reuse prior source/copy/model/material reviews','actual_conflict_paths':['site/macro_business_activity.html'],'business':{'native_report_sha256':sha((r/'s14-s3-native-business-emission.json').read_bytes()),'raw_inputs_and_assets_exact_prior_qualified_stage':True,'only_delta_vs_reviewed_90':'exactly two actual document render timestamps','old_rendered_at':oldstamp,'new_rendered_at':newstamp,'values_reference_periods_31_and_clock_qualification_preserved':True,'html_sha256':sha(b.encode())},'bonds':{'protected_body_and_all_clocks_exact_except_canonical_css_href':True,'protected_href':oldhref[0],'candidate_href':newhref[0]},'commodity':{'protected_current_page_exact':True,'sha256':sha(Path('site/commodities.html').read_bytes()),'new_input_cut_claim':'preserved current protected emission only; no producer, PIT, current economic or served claim'},'company_bound_paths':len(d['git_entries']),'unchanged_90_paths':sum(e['equals_reviewed_90'] for e in entries if 'equals_reviewed_90' in e),'frozen_T11_all_modes_blobs_exact_90':True,'calendar_history_all_six_modes_blobs_exact_reviewed_input':True,'postimages':entries,'holds':['browser','provider/acquisition','full financial producer','PIT/source authenticity','host/served'],'not_inherited':['old proof against new base','prior native current-Commodity cut','changed visual or hosted CI']}
(r/'S14_S3_COMPOSITION_MANIFEST.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k not in ['postimages']}))
