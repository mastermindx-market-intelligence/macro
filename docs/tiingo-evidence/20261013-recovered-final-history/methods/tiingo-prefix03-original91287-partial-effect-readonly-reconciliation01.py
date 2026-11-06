"""Reconcile original91287 footprint without replaying any archive writer."""
import json,hashlib,importlib.util,os,sys,subprocess
from pathlib import Path
from datetime import datetime,timezone
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50'
CORE=E/'tiingo-wave15-continuation04-settled-success-prefix03-bound01.py'
CORE_SHA='49c3e277752add221fa1a6848cee0ffdea88ed057d224f5859e22c8a09884a64'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
SELF_SHA=sha(__file__)
assert sys.flags.optimize==0 and os.environ.get('CODEX_THREAD_ID')==ROOT and sha(CORE)==CORE_SHA
spec=importlib.util.spec_from_file_location('original91287_reconciliation_core',CORE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
log=E/'eod-wave15-unadmitted-continuation04-prefix03-settled-success-qualify-original.log'
assert sha(log)=='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' and not m.name('03','qualified').exists() and not m.cov('03').exists()
def holder_check():
 r=subprocess.run(['lsof','-nP',str(log)],text=True,capture_output=True)
 assert r.returncode==1 and r.stdout=='' and r.stderr=='','Scoped original log holder check unavailable or held'
holder_check()
pfp=m.name('03','disposition-preflight');pcp=m.name('03','preflight-parent-consumption')
assert sha(pcp)=='fb2ef7fda589d824ed72d97462278cb554ca09cd1ab9d600e2e5229f28783170'
pf=load(pfp);pc=load(pcp)
assert pf['method_sha256']==pc['method_sha256']==CORE_SHA and pc['actual_preflight_return_consumed'] and pc['original_preflight_exit_code']==0 and pc['preflight_sha256']==sha(pfp)
plan,scope,expected,prior,base,proofs,seen,ranges,successful,settled=m.context('03')
assert pf['selected_responses']==pf['valid_count']==862 and pf['quality_count']==0
assert pf['prior_coverage_file']==prior.name and sha(prior)==pf['prior_coverage_sha256'] and pf['reused_accepted_proofs']==proofs
sp=E/pf['exclusive_unvalidated_snapshot_file'];assert sha(sp)==pf['exclusive_unvalidated_snapshot_sha256']
items={m.key(r):r for r in pf['records']};assert set(items)==successful-seen and len(items)==862
frozen={str(CORE):CORE_SHA,str(Path(__file__)):SELF_SHA,str(log):sha(log),str(pfp):sha(pfp),str(pcp):sha(pcp),str(sp):sha(sp),str(prior):sha(prior),**{str(E/n):h for n,h in m.PINS.items()},**{str(E/n):h for n,h in proofs.items()},**{str(m.C/n):h for n,h in {**plan['loaded_source_sha256'],**load(E/'tiingo-current-original-physical-qualification-source-20261012T2336.json')['sha256']}.items()}}
for path,h in frozen.items():assert sha(path)==h
protected=pf['retained_partial_artifact_sha256'].copy();observed={};footprint=[];complete=absent=bars=0
for pair,item in items.items():
 rp=m.R/item['receipt_file'];assert sha(rp)==item['receipt_file_sha256'];r=load(rp);identity=m.validate_receipt(r)
 assert identity==item['receipt_id'] and m.key(r)==pair and r['raw_sha256']==item['raw_sha256'] and r['observed_at_utc']==item['observed_at_utc']
 assert pair in successful and scope['started_at_utc']<=r['observed_at_utc']<=min(pf['snapshot_before_utc'],settled)
 raw=m.verified_raw(m.R,r);dates,invalid=m.scalar_check(raw,r,expected[pair],ranges)
 assert len(raw)==item['raw_bytes'] and len(dates)==item['rows'] and invalid==item['invalid_volume_fields']==[] and item['disposition']=='VALID'
 hashes,found=m.artifacts(r,identity,dates,invalid)
 for rel,h in hashes.items():
  assert rel not in protected or protected[rel]==h
  assert rel not in observed or observed[rel]==h;observed[rel]=h
 if found:
  expected_rows=m.research_rows(raw,r);view=m.read_research_view('eod-bars',r['observed_at_utc'][:10],identity,root=m.R,max_rows=1000000)
  assert list(view.rows)==expected_rows;complete+=1;status='COMPLETE_RAW_AND_FULL_READER_VERIFIED';bars+=len(view.rows)
 else:
  assert not (m.R/'manifests/eod-bars'/r['observed_at_utc'][:10]/(identity+'.json')).exists() and not (m.R/'normalized/eod-bars'/r['observed_at_utc'][:10]/(identity+'.parquet')).exists()
  absent+=1;status='CURRENT_IDENTITY_PROJECTION_ABSENT'
 footprint.append({'symbol':pair[0],'request_path':pair[1],'receipt_id':identity,'receipt_file':item['receipt_file'],'receipt_file_sha256':sha(rp),'status':status,'artifact_sha256':hashes,'current_owned_artifacts':found})
for rel,h in {**protected,**observed}.items():assert sha(m.R/rel)==h
for path,h in frozen.items():assert sha(path)==h
assert not m.name('03','qualified').exists() and not m.cov('03').exists();holder_check()
assert complete+absent==862
out={'schema':'tiingo.interrupted_qualification_original_frozen_selection_partial_effect_readonly_reconciliation/v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'root':ROOT,'method_sha256':SELF_SHA,'original_core_sha256':CORE_SHA,'original_tool_session':91287,'original_tool_exit_code':None,'actual_original_terminal_return_consumed':False,'original_terminal_chunk':None,'original_exclusive_log_sha256':sha(log),'original_qualified_summary_absent':True,'original_coverage_absent':True,'original_preflight_sha256':sha(pfp),'original_preflight_actual_parent_sha256':sha(pcp),'original_frozen_snapshot_sha256':sha(sp),'predecessor_coverage_sha256':sha(prior),'selected_responses':862,'complete_current_projections':complete,'absent_current_projections':absent,'verified_current_projection_bars':bars,'all862_raw_scalar_window_identity_and_success_ledger_bounds_verified':True,'all_existing_current_reader_rows_equal_raw_normalization':True,'all_observed_and_protected_artifact_hashes_unchanged':True,'orphan_or_corrupt_or_foreign_identity_artifact_observed':False,'scoped_original_log_no_holder_before_and_after':True,'universal_writer_absence_claimed':False,'writer_resume_authorized_by_this_readonly_proof':False,'frozen_input_sha256':frozen,'observed_projection_artifact_sha256':observed,'footprint':footprint,'provider_requests':0,'archive_writes':0,'credentials_read':False,'original_writer_replayed':False}
p=E/'tiingo-prefix03-original91287-partial-effect-readonly-reconciliation.json';m.save(p,out)
print(json.dumps({k:v for k,v in out.items() if k not in {'frozen_input_sha256','observed_projection_artifact_sha256','footprint'}},indent=2),flush=True)
