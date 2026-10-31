"""Reuse accepted four-phase proof and reconcile actual raw04/raw05, QA effects, and original unknown returns."""
import os,sys,json,hashlib,importlib.util,tempfile
from pathlib import Path
from datetime import datetime,timezone
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo');ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50'
ORIGINAL='eod-wave15-final-unreserved-20261012-01a12ab6';RUN04='eod-wave15-original-unadmitted-continuation04-20261013-01a12ab6';RUN05='eod-wave15-original-unadmitted-continuation05-20261013-01a12ab6'
key=lambda r:(r['symbol'],r['request_path'])
METADATA_FROZEN={}
def retain_metadata_hash(path,digest):
 path=str(Path(path));assert path not in METADATA_FROZEN or METADATA_FROZEN[path]==digest,'Changed consumed metadata'
 METADATA_FROZEN[path]=digest
def sha(path):
 digest=hashlib.sha256(Path(path).read_bytes()).hexdigest();retain_metadata_hash(path,digest);return digest
SELF_SHA=sha(__file__)
def load(path):
 data=Path(path).read_bytes();retain_metadata_hash(path,hashlib.sha256(data).hexdigest());return json.loads(data)
Q05='eod-wave15-unadmitted-continuation05-prefix01-qualified.json';C05='eod-qualified-catalogue-coverage-wave15-unadmitted-continuation05-prefix01-delta.json';P05='tiingo-wave15-continuation05-disposition-window01-actual-parent-consumption.json'
PINS={'eod-wave15-original-four-phase-final-disposition-partition-accounting.json':'8385307f7518d7d82ad8b1bdb3f0b6ef2280207906ef90dcd856f08bb5c44ea8','tiingo-wave15-original-four-phase-final-disposition-accounting-actual-parent-consumption.json':'e26817746bc017c7bb4190624ba92b6f04662804b9ff6d6cef412d51fd3a1bab','tiingo-wave15-continuation04-disposition-window01-actual-parent-consumption.json':'4639301591e6448de88a62d6e8753a9d1855d6899d3e85596707764289857fb2','tiingo-wave15-continuation04-disposition-window02-recovery-actual-parent-consumption.json':'9a35c4d26deb661a4e92adb3d344a4805acb493800500a2f954bbba2a4918d02','tiingo-wave15-continuation04-prefix03-partial-recovery-actual-parent-consumption.json':'1352560a573fae5a285d6a98d05523702fce565789a139d6e904607c1ef8fe55',Q05:'12bd8681461c238af1441177fc4d94e416e180b4260dc02393813789607f5b4f',C05:'02daf4542a6e192e2e21f2afdcb9d95c140b0d32bd669599d19c71fdd14f3d74',P05:'c155b18c837882ae070807587a29f9a855ae057e85f24dc737a1f3728db18a5c'}
METHOD05='7e734c3bfb9c6b4f79468eb1516a8d86d39361e427cb0dfa8227833acb4e93af';SOURCE05=E/'tiingo-wave15-continuation05-disposition-bound03.py'
assert sys.flags.optimize==0 and os.environ.get('CODEX_THREAD_ID')==ROOT and sys.argv[1:]==['--actual-capture-and-QA-effects-accepted']
for n,digest in PINS.items():assert sha(E/n)==digest
assert sha(SOURCE05)==METHOD05
spec=importlib.util.spec_from_file_location('accepted_qa05_context',SOURCE05);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.context('01');frozen=m.source_freeze();
for n,digest in load(E/m.BASE)['accepted_qualification_files'].items():retain_metadata_hash(E/n,digest)
frozen.update({str(E/n):digest for n,digest in PINS.items()});frozen[str(SOURCE05)]=METHOD05
old=load(E/'eod-wave15-original-four-phase-final-disposition-partition-accounting.json');op=load(E/'tiingo-wave15-original-four-phase-final-disposition-accounting-actual-parent-consumption.json')
assert op['root']==ROOT and op['actual_original_terminal_return_consumed'] is True and op['original_exit_code']==0 and op['actual_accounting_sha256']==PINS['eod-wave15-original-four-phase-final-disposition-partition-accounting.json']
assert old['all_actual_terminal_capture_and_qualification_returns_consumed'] is True and old['all_original_4392_identities_accounted_exactly_once'] is True
# Known lost original qualifiers retain their false terminal facts; actual same-carrier recovery effects are separate.
p1=load(E/'tiingo-wave15-continuation04-disposition-window01-actual-parent-consumption.json');p2=load(E/'tiingo-wave15-continuation04-disposition-window02-recovery-actual-parent-consumption.json');p3=load(E/'tiingo-wave15-continuation04-prefix03-partial-recovery-actual-parent-consumption.json');p5=load(E/P05)
assert p1['root']==ROOT and p1['original_tool_session']==29227 and p1['original_exit_code']==0 and p1['actual_original_terminal_return_consumed'] is True
assert p2['root']==ROOT and p2['original_tool_session']==22925 and p2['original_exit_code'] is None and p2['actual_original_terminal_return_consumed'] is False and p2['all_listed_qualification_effects_verified_and_accepted'] is True and p2['actual_readonly_verifier_terminal_return_consumed'] is True and p2['actual_coverage_terminal_return_consumed'] is True
assert p3['root']==ROOT and p3['original_tool_session']==91287 and p3['original_exit_code'] is None and p3['actual_original_terminal_return_consumed'] is False and p3['all_listed_qualification_effects_verified_and_accepted'] is True and p3['actual_partial_qualifier_native_terminal_consumed'] is True and p3['actual_coverage_native_terminal_consumed'] is True
assert p5['root']==ROOT and p5['core_sha256']==METHOD05 and p5['all_listed_qualification_effects_verified_and_accepted'] is True and p5['all_listed_qualifier_and_coverage_returns_consumed'] is True and p5['actual_preflight_return_consumed'] is True and p5['actual_qualifier_terminal_return_consumed'] is True and p5['actual_coverage_terminal_return_consumed'] is True
qmap=dict(old['qualification_sha256']);cmap=dict(old['coverage_sha256']);windows=dict(old['actual_disposition_window_parent_sha256'])
for pn,p in [('tiingo-wave15-continuation04-disposition-window01-actual-parent-consumption.json',p1),('tiingo-wave15-continuation04-disposition-window02-recovery-actual-parent-consumption.json',p2),('tiingo-wave15-continuation04-prefix03-partial-recovery-actual-parent-consumption.json',p3),(P05,p5)]:
 assert pn not in windows;windows[pn]=sha(E/pn)
 for n,digest in p['qualification_sha256'].items():assert n not in qmap and sha(E/n)==digest;qmap[n]=digest
 for n,digest in p['coverage_sha256'].items():assert n not in cmap and sha(E/n)==digest;cmap[n]=digest
assert qmap[Q05]==PINS[Q05] and cmap[C05]==PINS[C05]
valid=set();quality=set();rows=valid_raw=quality_raw=empty=nonempty=0;quarantines=[];phase_stats={}
for n,digest in qmap.items():
 assert sha(E/n)==digest;q=load(E/n);vv={key(r) for r in q['receipts']};bb={key(r) for r in q['quality_quarantines']};assert len(vv)==len(q['receipts']) and len(bb)==len(q['quality_quarantines']) and not vv&bb and not (vv|bb)&(valid|quality)
 if n.startswith('eod-wave15-unadmitted-continuation04-'):
  assert q['run_scope_sha256']=='1ec636d0f27fe20e81dfc72a0853980e91c8af6522507d19269d67eea36eeb28'
  if n.endswith('prefix03-qualified.json'):assert q['method_sha256']=='4931c2c2b8445e30d6af95b6536e1e6898f41ff22e4088b906229ba2ab715cc3' and q['preflight_method_sha256']=='49c3e277752add221fa1a6848cee0ffdea88ed057d224f5859e22c8a09884a64' and q['reused_accepted_interrupted_outputs']==536 and q['new_materializer_calls']==326
  else:assert q['method_sha256']=='f4a3c65db22325f9755b7ebaa6d425819f41aefdc916f0733341f35f06727ccc'
 elif n==Q05:assert q['method_sha256']==METHOD05 and q['run_scope_sha256']==m.SCOPE_SHA
 for row in q['receipts']:
  assert row['raw_checksum_verified'] and row['old_economic_dates_disjoint'] and sha(R/row['receipt_file'])==row['receipt_file_sha256']
  rec=load(R/row['receipt_file']);assert m.validate_receipt(rec)==row['receipt_id'] and key(rec)==key(row) and rec['raw_sha256']==row['raw_sha256'] and rec['observed_at_utc']==row['observed_at_utc']
  assert (row['projection_lineage_verified'] if row['projected_rows'] else row['raw_empty_response_verified']);rows+=row['projected_rows'];valid_raw+=row['raw_bytes'];nonempty+=bool(row['projected_rows']);empty+=not bool(row['projected_rows'])
 for row in q['quality_quarantines']:
  assert row['whole_invalid_receipt_retained_without_projection'] and not row['projection_admitted'] and row['provider_retry_authorized'] is False and sha(R/row['receipt_file'])==row['receipt_file_sha256'];quality_raw+=row['raw_bytes'];quarantines.append({k:row[k] for k in ['symbol','request_path','receipt_id','receipt_file','receipt_file_sha256','raw_sha256','raw_bytes','rows']})
 valid|=vv;quality|=bb
for n,digest in cmap.items():assert sha(E/n)==digest
capture_results=dict(old['actual_capture_result_sha256']);capture_parents=dict(old['actual_capture_parent_sha256'])
for run,parent_name in [(RUN04,'tiingo-wave15-continuation04-capture-actual-terminal-parent-consumption.json'),(RUN05,'tiingo-wave15-continuation05-capture-actual-terminal-parent-consumption.json')]:
 rp=E/(run+'-result.json');pp=E/parent_name;cp=load(pp);assert cp['root']==ROOT and cp['actual_original_terminal_return_consumed'] is True and cp['actual_result_sha256']==sha(rp);capture_results[rp.name]=sha(rp);capture_parents[parent_name]=sha(pp)
phaseplans={ORIGINAL:(ORIGINAL+'-planned.json','d120cc13ecbb675fa45a67b32697f7f43fa506a9406e62de29f5edafe57abbe9',43992),
'eod-wave15-original-unadmitted-continuation01-20261013-01a12ab6':('eod-wave15-original-unadmitted-continuation01-20261013-01a12ab6-planned-refresh02.json','1fcaf8614d1df2ef31c1de353b4056755038a578f95ed2fe389969747b9ceec0',33372),
'eod-wave15-original-unadmitted-continuation02-20261013-01a12ab6':('eod-wave15-original-unadmitted-continuation02-20261013-01a12ab6-planned.json','9ce4a829152152d6558c4170bf7033817453f5207c5faa02e72718371ee1e3fb',57125),
'eod-wave15-original-unadmitted-continuation03-20261013-01a12ab6':('eod-wave15-original-unadmitted-continuation03-20261013-01a12ab6-planned-refresh02.json','23499857c88ec5e32996db7d2aa566ee96ee96a264f1ea4c488741e0ae581418',85004),
RUN04:(RUN04+'-planned-attended-recovery03.json','eb75c83b6f5de511ea41377844f622a20a1ac5ff5656f81607d1daacb6b92aa5',81573),RUN05:(RUN05+'-planned-raw-ledger-attended01.json','462f48cb52d0b19853bf1b6e62e69c5b803f4baaa8124115445eb988fbedb62a',24428)}
original_plan=load(E/phaseplans[ORIGINAL][0]);expected={key(r) for r in original_plan['selected']};assert len(expected)==4392
assert len(capture_results)==len(capture_parents)==len(phaseplans)==6
started=set();success=set();failed=set();failrows=[];raw_total=hint_total=0;previous_never=expected.copy();source_bounds={}
for run,(plan_name,plan_sha,session) in phaseplans.items():
 assert sha(E/plan_name)==plan_sha;plan=load(E/plan_name);selected=[key(row) for row in plan['selected']];assert len(selected)==len(set(selected)) and set(selected)==previous_never
 rp=E/(run+'-result.json');r=load(rp);assert sha(rp)==capture_results[rp.name] and r['run_id']==run and r['phase']=='settled' and r['fatal_exception_type'] is None and r['prior_failures_retried'] is False
 parent_matches=[(pn,load(E/pn)) for pn in capture_parents if load(E/pn)['actual_result_sha256']==sha(rp)];assert len(parent_matches)==1;pn,cp=parent_matches[0]
 assert sha(E/pn)==capture_parents[pn] and cp['root']==ROOT and cp['original_tool_session']==session and cp['actual_original_terminal_return_consumed'] is True and cp['original_exit_code']==(1 if r['capture']['failed'] else 0)
 admissions=r['actual_local_admissions'];indices=[row['selection_index'] for row in admissions];tasks=[key(row) for row in r['all_started_tasks']]
 assert len(indices)==len(set(indices))==len(tasks)==r['capture']['attempted'] and all(0<=i<len(selected) for i in indices) and tasks==[selected[i] for i in indices] and not started&set(tasks)
 gaps=[admissions[i]['admitted_monotonic']-admissions[i-4]['admitted_monotonic'] for i in range(4,len(admissions))];assert not gaps or min(gaps)>=5
 ss={key(row) for row in r['successful_requests']};ff={key(row) for row in r['capture']['errors']};assert len(ss)==r['capture']['ok'] and len(ff)==r['capture']['failed'] and not ss&ff and ss|ff==set(tasks)
 started|=set(tasks);success|=ss;failed|=ff;failrows.extend(r['capture']['errors']);raw_total+=r['capture']['bytes'];hint_total+=r['capture']['row_hints'];previous_never=set(selected)-set(tasks)
 scope=load(E/(run+'-scope.json'));assert sha(E/(run+'-scope.json'))==r['scope_sha256'];source_bounds[run]=(ss,scope['started_at_utc'],r['settled_at_utc'])
 phase_stats[run]={'planned':len(selected),'attempted':len(tasks),'success':len(ss),'failed':len(ff),'never':len(previous_never),'raw_bytes':r['capture']['bytes'],'row_hints':r['capture']['row_hints'],'minimum_four_admission_gap_seconds':min(gaps) if gaps else None}
assert success==valid|quality and failed.isdisjoint(success) and started==success|failed and previous_never==expected-started
assert valid|quality|failed|previous_never==expected and len(valid)+len(quality)+len(failed)+len(previous_never)==4392
for n in qmap:
 q=load(E/n)
 for row in q['receipts']+q['quality_quarantines']:
  matches=[(lo,hi) for ss,lo,hi in source_bounds.values() if key(row) in ss];assert len(matches)==1 and matches[0][0]<=row['observed_at_utc']<=matches[0][1]
assert valid_raw+quality_raw==raw_total and rows+sum(r['rows'] for r in quarantines)==hint_total and nonempty+empty==len(valid)
latest=load(E/C05);assert latest['accepted_qualification_files'][Q05]==PINS[Q05] and latest['accepted_nonempty_ticker_histories']==old['global_histories']+sum(load(E/n)['new_nonempty_histories'] for n in qmap if n not in old['qualification_sha256']) and latest['accepted_distinct_bars']==old['global_bars']+sum(load(E/n)['new_disjoint_bars'] for n in qmap if n not in old['qualification_sha256']) and sum(latest['candidate_capture_status_counts'].values())==47689
for path,digest in METADATA_FROZEN.items():m.keep_hash(frozen,path,digest)
m.freeze(frozen)
proof={'schema':'tiingo.original_six_physical_phase_qualified_quality_failure_never_partition/v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'root':ROOT,'run_id':ORIGINAL,'method_sha256':SELF_SHA,'prior_combined_four_phase_sha256':PINS['eod-wave15-original-four-phase-final-disposition-partition-accounting.json'],'prior_combined_four_phase_actual_parent_sha256':PINS['tiingo-wave15-original-four-phase-final-disposition-accounting-actual-parent-consumption.json'],'actual_capture_result_sha256':capture_results,'actual_capture_parent_sha256':capture_parents,'all_actual_capture_terminal_returns_consumed':True,'all_qualification_effects_verified_and_accepted':True,'all_original_qualification_terminal_returns_consumed':False,'unknown_original_qualifier_sessions':[22925,91287],'all_original_4392_identities_accounted_exactly_once':True,'successful_requests':len(success),'qualified_successes':len(valid),'source_quality_quarantined_successes':len(quality),'held_attempted_failure_count':len(failed),'held_attempted_failures':failrows,'never_admitted_count':len(previous_never),'never_admitted_requests':[],'quarantined_receipts':quarantines,'qualified_nonempty_responses':nonempty,'qualified_empty_responses':empty,'qualified_disjoint_bars':rows,'qualified_raw_bytes':valid_raw,'quarantined_raw_bytes':quality_raw,'all_captured_raw_bytes':raw_total,'qualification_sha256':qmap,'coverage_sha256':cmap,'actual_disposition_window_parent_sha256':windows,'physical_phase_accounting':phase_stats,'last_coverage_file':C05,'last_coverage_sha256':PINS[C05],'global_histories':latest['accepted_nonempty_ticker_histories'],'global_bars':latest['accepted_distinct_bars'],'global_candidate_status':latest['candidate_capture_status_counts'],'all_captured_successes_partitioned_between_valid_and_quality':True,'all_selected_captured':not failed and not previous_never,'all_captured_successes_reader_qualified':not quality,'prior_failures_retried':False,'provider_requests':0,'credentials_read':False,'archive_writes':0,'full_vendor_history_proven':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False,'programme_acceptance_claimed':False}
p=E/'eod-wave15-original-six-phase-final-disposition-partition-accounting.json';fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.control-',dir=str(E))
with os.fdopen(fd,'w') as f:json.dump(proof,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
os.link(tmp,p);d=os.open(E,os.O_RDONLY);os.fsync(d);os.close(d);Path(tmp).unlink()
print(json.dumps({k:v for k,v in proof.items() if k not in {'qualification_sha256','coverage_sha256','actual_capture_result_sha256','actual_capture_parent_sha256','actual_disposition_window_parent_sha256','held_attempted_failures','quarantined_receipts','physical_phase_accounting'}}),flush=True)
