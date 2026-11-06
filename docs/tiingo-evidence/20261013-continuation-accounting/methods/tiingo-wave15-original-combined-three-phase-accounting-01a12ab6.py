"""Read-only extension of consumed two-phase accounting; no retry or archive writes."""
from pathlib import Path
import os,sys,json,hashlib
from datetime import datetime,timezone
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50'
ORIGINAL='eod-wave15-final-unreserved-20261012-01a12ab6';PHYSICAL='eod-wave15-original-unadmitted-continuation02-20261013-01a12ab6'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def key(r):return r['symbol'],r['request_path']
assert sys.flags.optimize==0 and os.environ.get('CODEX_THREAD_ID')==ROOT and sys.argv[1:]==['--actual-three-phase-returns-consumed']
oldp=E/'eod-wave15-original-two-phase-final-disposition-partition-accounting.json';assert sha(oldp)=='1ae5e94b56cf3d0ed97f2f82e45d16a019baf17702f1e82a3b944668edaeb774';old=load(oldp)
oldparent=E/'tiingo-wave15-original-two-phase-final-disposition-accounting-actual-parent-consumption.json';assert sha(oldparent)=='a8e053d087e84146d312d49d97e132eef16688788d95bf15b842d9b04ef64939';op=load(oldparent)
assert op['root']==ROOT and op['actual_original_terminal_return_consumed'] and op['original_exit_code']==0 and op['actual_accounting_sha256']==sha(oldp)
assert old['all_actual_terminal_capture_and_qualification_returns_consumed'] and old['all_original_4392_identities_accounted_exactly_once']
newp=E/'eod-wave15-continuation02-final-disposition-partition-accounting.json';new=load(newp)
parentp=E/'tiingo-wave15-continuation02-final-disposition-accounting-actual-parent-consumption.json';parent=load(parentp)
assert parent['root']==ROOT and parent['actual_original_terminal_return_consumed'] and parent['original_exit_code']==0 and parent['actual_accounting_sha256']==sha(newp)
assert parent['accounting_method_sha256']==new['method_sha256']=='cb89aef29025589ab3b7e99d317285d26e4a4a1396e9835dfcb64e2166ded3c5'
assert new['run_id']==PHYSICAL and new['core_sha256']=='c6932707a653fd825256a51531b1e320661b2561ef1633edc52880fd8412cebd' and new['all_physical_2015_identities_accounted_exactly_once']
planp=E/(ORIGINAL+'-planned.json');assert sha(planp)=='d120cc13ecbb675fa45a67b32697f7f43fa506a9406e62de29f5edafe57abbe9';plan=load(planp)
physicalp=E/(PHYSICAL+'-planned.json');assert sha(physicalp)=='9ce4a829152152d6558c4170bf7033817453f5207c5faa02e72718371ee1e3fb';physical=load(physicalp)
assert physical['selected']==old['never_admitted_requests'] and physical['raw_budget_bytes']==plan['raw_budget_bytes']-old['all_captured_raw_bytes']
expected={key(r) for r in plan['selected']};physical_expected={key(r) for r in physical['selected']};assert len(expected)==4392 and len(physical_expected)==2015 and physical_expected<=expected
valid=set();quality=set();qfiles={};cfiles={};windows={}
for account in [old,new]:
 assert account['all_captured_successes_partitioned_between_valid_and_quality']
 assert not account.get('prior_failures_retried',account.get('failed_requests_retried'))
 if account is new:assert account['actual_original_capture_terminal_return_consumed'] and account['all_listed_qualification_writer_returns_consumed']
 for n,h in account['qualification_sha256'].items():
  assert n not in qfiles and sha(E/n)==h;q=load(E/n);v={key(r) for r in q['receipts']};b={key(r) for r in q['quality_quarantines']}
  assert len(v)==len(q['receipts']) and len(b)==len(q['quality_quarantines']) and not v&b and not (v|b)&(valid|quality)
  if account is new:assert (v|b)<=physical_expected
  else:assert not (v|b)&physical_expected
  valid|=v;quality|=b;qfiles[n]=h
 for n,h in account['coverage_sha256'].items():assert n not in cfiles and sha(E/n)==h;cfiles[n]=h
 for n,h in account['actual_disposition_window_parent_sha256'].items():assert n not in windows and sha(E/n)==h;windows[n]=h
assert len(valid)==old['qualified_successes']+new['qualified_successes'] and len(quality)==old['source_quality_quarantined_successes']+new['source_quality_quarantined_successes']
failrows=old['held_attempted_failures']+new['held_attempted_failures'];failed={key(r) for r in failrows};never={key(r) for r in new['never_admitted_requests']}
assert len(failed)==len(failrows) and len(never)==new['never_admitted_count']
assert not (valid|quality)&(failed|never) and not valid&quality and not failed&never
assert valid|quality|failed|never==expected and len(valid)+len(quality)+len(failed)+len(never)==4392
capture_parents=dict(old['actual_capture_parent_sha256']);capture_results=dict(old['actual_capture_result_sha256'])
newresult=E/(PHYSICAL+'-result.json');newcaptureparent=E/'tiingo-wave15-continuation02-capture-actual-terminal-parent-consumption.json'
assert sha(newresult)==new['actual_original_result_sha256'] and sha(newcaptureparent)==new['actual_original_terminal_parent_sha256']
assert newresult.name not in capture_results and newcaptureparent.name not in capture_parents
capture_results[newresult.name]=sha(newresult);capture_parents[newcaptureparent.name]=sha(newcaptureparent)
expected_sessions={ORIGINAL:43992,'eod-wave15-original-unadmitted-continuation01-20261013-01a12ab6':33372,PHYSICAL:57125}
raw_total=bar_total=0;started=set();success=set();allfail=set()
for n,h in capture_results.items():
 rp=E/n;assert sha(rp)==h;r=load(rp);run=r['run_id'];assert run in expected_sessions and r['phase']=='settled' and r['fatal_exception_type'] is None and not r['prior_failures_retried']
 parents=[(pn,load(E/pn)) for pn,ph in capture_parents.items() if load(E/pn)['actual_result_sha256']==h];assert len(parents)==1;pn,cp=parents[0]
 assert sha(E/pn)==capture_parents[pn] and cp['root']==ROOT and cp['actual_original_terminal_return_consumed'] and cp['original_tool_session']==expected_sessions[run] and cp['original_exit_code']==(1 if r['capture']['failed'] else 0)
 phaseplan=plan if run==ORIGINAL else load(E/(run+('-planned-refresh02.json' if expected_sessions[run]==33372 else '-planned.json')))
 indices=[row['selection_index'] for row in r['actual_local_admissions']];tasks=[key(row) for row in r['all_started_tasks']]
 assert len(indices)==len(set(indices))==len(tasks)==r['capture']['attempted'] and all(0<=i<len(phaseplan['selected']) for i in indices)
 assert tasks==[key(phaseplan['selected'][i]) for i in indices] and not started&set(tasks);started.update(tasks)
 ss={key(row) for row in r['successful_requests']};ff={key(row) for row in r['capture']['errors']}
 assert len(ss)==r['capture']['ok'] and len(ff)==r['capture']['failed'] and not ss&ff and ss|ff==set(tasks)
 success|=ss;allfail|=ff;raw_total+=r['capture']['bytes'];bar_total+=r['capture']['row_hints']
assert success==valid|quality and allfail==failed and started==valid|quality|failed and never==expected-started
quarantines=old['quarantined_receipts']+new['quarantined_receipts'];assert len(quarantines)==len(quality) and {key(r) for r in quarantines}==quality
rows=old['qualified_disjoint_bars']+new['qualified_disjoint_bars'];assert rows+sum(r['rows'] for r in quarantines)==bar_total
assert raw_total==old['all_captured_raw_bytes']+new['all_captured_raw_bytes']==old['qualified_raw_bytes']+new['qualified_raw_bytes']+old['quarantined_raw_bytes']+new['quarantined_raw_bytes']
latestp=E/new['last_coverage_file'];assert sha(latestp)==new['last_coverage_sha256'];latest=load(latestp)
assert latest['candidate_capture_status_counts']==new['global_candidate_status'] and sum(latest['candidate_capture_status_counts'].values())==47689
assert latest['accepted_nonempty_ticker_histories']==old['global_histories']+new['qualified_nonempty_responses'] and latest['accepted_distinct_bars']==old['global_bars']+new['qualified_disjoint_bars']
proof={'schema':'tiingo.original_three_phase_qualified_quality_failure_never_partition/v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'run_id':ORIGINAL,'physical_continuation_run':PHYSICAL,'method_sha256':sha(__file__),'prior_combined_accounting_sha256':sha(oldp),'prior_combined_accounting_actual_parent_sha256':sha(oldparent),'continuation_accounting_sha256':sha(newp),'continuation_accounting_actual_parent_sha256':sha(parentp),'actual_capture_parent_sha256':capture_parents,'actual_capture_result_sha256':capture_results,'all_actual_terminal_capture_and_qualification_returns_consumed':True,'all_original_4392_identities_accounted_exactly_once':True,'qualified_successes':len(valid),'source_quality_quarantined_successes':len(quality),'held_attempted_failure_count':len(failed),'held_attempted_failures':failrows,'never_admitted_count':len(never),'never_admitted_requests':[r for r in plan['selected'] if key(r) in never],'quarantined_receipts':quarantines,'qualified_disjoint_bars':rows,'qualified_raw_bytes':old['qualified_raw_bytes']+new['qualified_raw_bytes'],'quarantined_raw_bytes':old['quarantined_raw_bytes']+new['quarantined_raw_bytes'],'all_captured_raw_bytes':raw_total,'qualification_sha256':qfiles,'coverage_sha256':cfiles,'actual_disposition_window_parent_sha256':windows,'last_coverage_file':latestp.name,'last_coverage_sha256':sha(latestp),'global_histories':latest['accepted_nonempty_ticker_histories'],'global_bars':latest['accepted_distinct_bars'],'global_candidate_status':latest['candidate_capture_status_counts'],'all_captured_successes_partitioned_between_valid_and_quality':True,'all_selected_captured':not failed and not never,'all_captured_successes_reader_qualified':not quality,'failed_requests_retried':False,'provider_requests':0,'credentials_read':False,'archive_writes':0,'full_vendor_history_proven':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False,'programme_acceptance_claimed':False}
p=E/'eod-wave15-original-three-phase-final-disposition-partition-accounting.json'
with os.fdopen(os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:json.dump(proof,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({k:v for k,v in proof.items() if k not in {'held_attempted_failures','never_admitted_requests','quarantined_receipts','qualification_sha256','coverage_sha256','actual_disposition_window_parent_sha256'}},indent=2),flush=True)
