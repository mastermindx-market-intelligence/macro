"""Combine only independently accepted original and physical continuation returns."""
from pathlib import Path
import os,sys,json,hashlib
from datetime import datetime,timezone
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50'
ORIGINAL='eod-wave15-final-unreserved-20261012-01a12ab6';PHYSICAL='eod-wave15-original-unadmitted-continuation01-20261013-01a12ab6'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def key(r):return r['symbol'],r['request_path']
assert sys.flags.optimize==0 and os.environ.get('CODEX_THREAD_ID')==ROOT and sys.argv[1:]==['--actual-two-phase-returns-consumed']
oldp=E/'eod-wave15-original-final-disposition-partition-accounting.json';assert sha(oldp)=='2df8e075d3ed6962c19163fef91e88184709a430942cf282a7698f5d087960fb';old=load(oldp)
oldparent=E/'tiingo-wave15-original-final-disposition-accounting-actual-parent-consumption.json';assert sha(oldparent)=='1db7d1ca0c7711add656f47f9928620fd8a0dbcc827eaaddcd58599102f3bcde';op=load(oldparent)
assert op['actual_original_terminal_return_consumed'] and op['original_exit_code']==0 and op['actual_accounting_sha256']==sha(oldp)
newp=E/'eod-wave15-continuation01-final-disposition-partition-accounting.json';new=load(newp)
parentp=E/'tiingo-wave15-continuation01-final-disposition-accounting-actual-parent-consumption.json';parent=load(parentp)
assert parent['root']==ROOT and parent['actual_original_terminal_return_consumed'] and parent['original_exit_code']==0 and parent['actual_accounting_sha256']==sha(newp)
assert parent['accounting_method_sha256']==new['method_sha256']=='7560a0b20d17ebabad0085920305f76de08aedb65a654769e3b0ddcaf7b248a1'
assert new['run_id']==PHYSICAL and new['core_sha256']=='3094d258d52260a4e14802ec4c8108299b3b4c289c766133d19ae23bbae30916'
planp=E/(ORIGINAL+'-planned.json');assert sha(planp)=='d120cc13ecbb675fa45a67b32697f7f43fa506a9406e62de29f5edafe57abbe9';plan=load(planp)
physicalp=E/(PHYSICAL+'-planned-refresh02.json');assert sha(physicalp)=='1fcaf8614d1df2ef31c1de353b4056755038a578f95ed2fe389969747b9ceec0';physical=load(physicalp)
assert physical['selected']==old['never_admitted_requests'] and physical['raw_budget_bytes']==plan['raw_budget_bytes']-old['all_captured_raw_bytes']
expected={key(r) for r in plan['selected']};physical_expected={key(r) for r in physical['selected']};assert len(expected)==4392 and len(physical_expected)==2631 and physical_expected<=expected
valid=set();quality=set();qfiles={};cfiles={};windows={}
for account in [old,new]:
 assert account['all_captured_successes_partitioned_between_valid_and_quality'] and account['actual_original_capture_terminal_return_consumed'] and account['all_listed_qualification_writer_returns_consumed'] and not account['prior_failures_retried']
 for n,h in account['qualification_sha256'].items():
  assert n not in qfiles and sha(E/n)==h;q=load(E/n);v={key(r) for r in q['receipts']};b={key(r) for r in q['quality_quarantines']}
  assert len(v)==len(q['receipts']) and len(b)==len(q['quality_quarantines']) and not v&b and not (v|b)&(valid|quality)
  if account is new:assert (v|b)<=physical_expected
  else:assert not (v|b)&physical_expected
  valid|=v;quality|=b;qfiles[n]=h
 for n,h in account['coverage_sha256'].items():assert n not in cfiles and sha(E/n)==h;cfiles[n]=h
 for n,h in account['actual_disposition_window_parent_sha256'].items():assert n not in windows and sha(E/n)==h;windows[n]=h
assert len(valid)==old['qualified_successes']+new['qualified_successes'] and len(quality)==old['source_quality_quarantined_successes']+new['source_quality_quarantined_successes']
assert old['all_original_4392_identities_accounted_exactly_once'] and new['all_physical_2631_identities_accounted_exactly_once']
failrows=old['held_attempted_failures']+new['held_attempted_failures'];failed={key(r) for r in failrows};never={key(r) for r in new['never_admitted_requests']}
assert len(failed)==len(failrows) and len(never)==new['never_admitted_count']
assert not (valid|quality)&(failed|never) and not valid&quality and not failed&never
assert valid|quality|failed|never==expected and len(valid)+len(quality)+len(failed)+len(never)==4392
raw_total=bar_total=0;capture_parents={};capture_results={}
for run,account in [(ORIGINAL,old),(PHYSICAL,new)]:
 rp=E/(run+'-result.json');r=load(rp);assert sha(rp)==account['actual_original_result_sha256'] and r['phase']=='settled' and r['fatal_exception_type'] is None
 cp=E/('tiingo-wave15-original-capture-actual-terminal-parent-consumption.json' if run==ORIGINAL else 'tiingo-wave15-continuation01-capture-actual-terminal-parent-consumption.json');c=load(cp)
 assert sha(cp)==account['actual_original_terminal_parent_sha256'] and c['actual_original_terminal_return_consumed'] and c['actual_result_sha256']==sha(rp)
 assert c['original_tool_session']==(43992 if run==ORIGINAL else 33372) and c['original_exit_code']==(1 if r['capture']['failed'] else 0)
 assert r['capture']['ok']==account['qualified_successes']+account['source_quality_quarantined_successes'] and r['capture']['bytes']==account['qualified_raw_bytes']+account['quarantined_raw_bytes']
 raw_total+=r['capture']['bytes'];bar_total+=r['capture']['row_hints'];capture_parents[cp.name]=sha(cp);capture_results[rp.name]=sha(rp)
quarantines=old['quarantined_receipts']+new['quarantined_receipts'];assert len(quarantines)==len(quality) and {key(r) for r in quarantines}==quality
rows=old['qualified_disjoint_bars']+new['qualified_disjoint_bars'];assert rows+sum(r['rows'] for r in quarantines)==bar_total
latestp=E/new['last_coverage_file'];assert sha(latestp)==new['last_coverage_sha256'];latest=load(latestp)
assert latest['candidate_capture_status_counts']==new['global_candidate_status'] and sum(latest['candidate_capture_status_counts'].values())==47689
assert latest['accepted_nonempty_ticker_histories']==old['global_histories']+new['qualified_nonempty_responses'] and latest['accepted_distinct_bars']==old['global_bars']+new['qualified_disjoint_bars']
proof={'schema':'tiingo.original_two_phase_qualified_quality_failure_never_partition/v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'run_id':ORIGINAL,'physical_continuation_run':PHYSICAL,'method_sha256':sha(__file__),'original_accounting_sha256':sha(oldp),'original_accounting_actual_parent_sha256':sha(oldparent),'continuation_accounting_sha256':sha(newp),'continuation_accounting_actual_parent_sha256':sha(parentp),'actual_capture_parent_sha256':capture_parents,'actual_capture_result_sha256':capture_results,'all_actual_terminal_capture_and_qualification_returns_consumed':True,'all_original_4392_identities_accounted_exactly_once':True,'qualified_successes':len(valid),'source_quality_quarantined_successes':len(quality),'held_attempted_failure_count':len(failed),'held_attempted_failures':failrows,'never_admitted_count':len(never),'never_admitted_requests':[r for r in plan['selected'] if key(r) in never],'quarantined_receipts':quarantines,'qualified_disjoint_bars':rows,'qualified_raw_bytes':old['qualified_raw_bytes']+new['qualified_raw_bytes'],'quarantined_raw_bytes':old['quarantined_raw_bytes']+new['quarantined_raw_bytes'],'all_captured_raw_bytes':raw_total,'qualification_sha256':qfiles,'coverage_sha256':cfiles,'actual_disposition_window_parent_sha256':windows,'last_coverage_file':latestp.name,'last_coverage_sha256':sha(latestp),'global_histories':latest['accepted_nonempty_ticker_histories'],'global_bars':latest['accepted_distinct_bars'],'global_candidate_status':latest['candidate_capture_status_counts'],'all_captured_successes_partitioned_between_valid_and_quality':True,'all_selected_captured':not failed and not never,'all_captured_successes_reader_qualified':not quality,'failed_requests_retried':False,'provider_requests':0,'credentials_read':False,'archive_writes':0,'full_vendor_history_proven':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False,'programme_acceptance_claimed':False}
p=E/'eod-wave15-original-two-phase-final-disposition-partition-accounting.json'
with os.fdopen(os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:json.dump(proof,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({k:v for k,v in proof.items() if k not in {'held_attempted_failures','never_admitted_requests','quarantined_receipts','qualification_sha256','coverage_sha256','actual_disposition_window_parent_sha256'}},indent=2),flush=True)
