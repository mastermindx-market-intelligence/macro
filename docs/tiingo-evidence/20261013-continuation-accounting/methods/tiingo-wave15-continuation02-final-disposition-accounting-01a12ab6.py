"""Read-only final request/quality accounting after actual original returns."""
import hashlib,importlib.util,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
RUN='eod-wave15-original-unadmitted-continuation02-20261013-01a12ab6';ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50'
CORE=Path('/private/tmp/tiingo-wave15-continuation02-disposition-pipeline-01a12ab6.py');CORE_SHA='c6932707a653fd825256a51531b1e320661b2561ef1633edc52880fd8412cebd'
ACCEPTED_METHODS={CORE_SHA}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def key(r):return r['symbol'],r['request_path']
assert sys.flags.optimize==0 and os.environ.get('CODEX_THREAD_ID')==ROOT
assert sys.argv[1:]==['--actual-original-returns-consumed']
assert sha(CORE)==CORE_SHA
spec=importlib.util.spec_from_file_location('disposition_core',CORE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for n,h in m.PINS.items():assert sha(E/n)==h
plan=load(E/m.PLAN);scope=load(E/(RUN+'-scope.json'));resultpath=E/(RUN+'-result.json');result=load(resultpath)
binding=load(E/'tiingo-current-original-physical-qualification-source-20261012T2336.json')
for mapping in [plan['loaded_source_sha256'],binding['sha256']]:
 for rel,h in mapping.items():assert sha(m.C/rel)==h
parentpath=E/'tiingo-wave15-continuation02-capture-actual-terminal-parent-consumption.json';parent=load(parentpath)
assert parent['original_tool_session']==57125 and parent['actual_original_terminal_return_consumed'] and parent['actual_result_sha256']==sha(resultpath) and parent['capture_method_sha256']==scope['method_sha256']
assert result['run_id']==RUN and result['scope_sha256']==m.SCOPE_SHA and result['phase']=='settled' and result['fatal_exception_type'] is None and result['prior_failures_retried'] is False
assert parent['original_exit_code']==(1 if result['fatal_exception_type'] or result['capture']['failed'] else 0)
assert result['all_selected_captured']==(result['capture']['ok']==result['capture']['attempted']==2015 and result['capture']['failed']==0 and result['fatal_exception_type'] is None)
selected=[key(r) for r in plan['selected']];selected_set=set(selected);assert len(selected)==len(selected_set)==2015
admissions=result['actual_local_admissions'];indices=[r['selection_index'] for r in admissions];tasks=[key(r) for r in result['all_started_tasks']]
assert len(indices)==len(set(indices))==len(tasks)==result['capture']['attempted'] and all(0<=i<2015 for i in indices)
assert tasks==[selected[i] for i in indices];started=set(tasks)
gaps=[admissions[i]['admitted_monotonic']-admissions[i-4]['admitted_monotonic'] for i in range(4,len(admissions))];assert not gaps or min(gaps)>=5
success=[key(r) for r in result['successful_requests']];successful=set(success);failures={key(r) for r in result['capture']['errors']}
assert len(success)==len(successful)==result['capture']['ok'] and len(failures)==result['capture']['failed']
assert not successful&failures and successful|failures==started
never=selected_set-started;assert not (successful|failures)&never and successful|failures|never==selected_set
# Only actual terminal controller returns recorded by the assigning root may authorize q reuse.
windowproofs={};acceptedq={};acceptedc={}
for pp in sorted(E.glob('tiingo-wave15-continuation02-disposition-window*-actual-parent-consumption.json')):
 p=load(pp);assert p['root']==ROOT and p['actual_original_terminal_return_consumed'] and p['core_sha256'] in ACCEPTED_METHODS
 assert p['all_listed_qualifier_and_coverage_returns_consumed']
 assert len(p['completed_prefixes'])==len(p['qualification_sha256'])==len(p['coverage_sha256'])
 for n,h in p['qualification_sha256'].items():assert n not in acceptedq and sha(E/n)==h and load(E/n)['method_sha256']==p['core_sha256'];acceptedq[n]=h
 for n,h in p['coverage_sha256'].items():assert n not in acceptedc and sha(E/n)==h;acceptedc[n]=h
 windowproofs[pp.name]=sha(pp)
assert acceptedq
assert acceptedq.keys()=={p.name for p in E.glob('eod-wave15-unadmitted-continuation02-prefix*-qualified.json')}
qualified=set();quality=set();qfiles={};cfiles={};rows=raw_bytes=bad_bytes=empty=nonempty=0;quarantines=[];lastcov=None;prior=E/m.BASE
for n,h in sorted(acceptedq.items()):
 qp=E/n;q=load(qp);prefix=n.split('-prefix')[1][:2];cp=m.cov(prefix);c=load(cp);pfpath=m.name(prefix,'disposition-preflight');pf=load(pfpath);consumption=m.name(prefix,'preflight-parent-consumption');pc=load(consumption)
 assert cp.name in acceptedc and sha(cp)==acceptedc[cp.name] and c['accepted_qualification_files'][n]==h
 assert q['method_sha256']==pf['method_sha256']==c['method_sha256'] and q['method_sha256'] in ACCEPTED_METHODS and q['run_scope_sha256']==m.SCOPE_SHA
 assert q['all_completed_response_dispositions_verified'] and q['all_partial_artifact_hashes_unchanged'] and q['base_coverage_sha256']==m.BASE_SHA and q['prior_coverage_sha256']==sha(prior)
 if q['method_sha256']==CORE_SHA:
  frozenpath=E/pf['exclusive_unvalidated_snapshot_file'];assert sha(frozenpath)==pf['exclusive_unvalidated_snapshot_sha256']
  frozen=load(frozenpath);assert frozen['cutoff_utc']==q['snapshot_before_utc'] and frozen['method_sha256']==CORE_SHA and {key(r) for r in frozen['selected_receipts']}=={key(r) for r in pf['records']}
 assert q['preflight_sha256']==sha(pfpath) and q['actual_preflight_parent_consumption_sha256']==sha(consumption) and pc['actual_preflight_return_consumed'] and pc['original_preflight_exit_code']==0 and pc['preflight_sha256']==sha(pfpath)
 valid={key(r) for r in q['receipts']};bad={key(r) for r in q['quality_quarantines']}
 assert len(valid)==len(q['receipts'])==q['selected_receipts'] and len(bad)==len(q['quality_quarantines']) and not valid&bad
 assert valid|bad=={key(r) for r in pf['records']} and len(valid|bad)==pf['selected_responses']==q['completed_response_dispositions']
 assert not (qualified|quality)&(valid|bad) and valid|bad<=successful
 assert q['all_selected_raw_and_reader_lineage_verified']==bool(valid) and q['all_valid_response_lineage_verified']==bool(valid) and q['empty_valid_set_not_reader_acceptance']==(not bool(valid))
 for r in q['receipts']:
  assert r['raw_checksum_verified'] and r['requested_window_verified'] and r['old_economic_dates_disjoint'] and r['all_other_normalizer_inputs_verified']
  assert sha(R/r['receipt_file'])==r['receipt_file_sha256']
  rec=load(R/r['receipt_file']);assert m.validate_receipt(rec)==r['receipt_id'] and rec['raw_sha256']==r['raw_sha256'] and key(rec)==key(r)
  assert scope['started_at_utc']<=r['observed_at_utc']<=min(q['snapshot_before_utc'],result['settled_at_utc'])
  if r['projected_rows']:assert r['projection_lineage_verified'];nonempty+=1
  else:assert r['projected_rows']==0 and r['raw_empty_response_verified'];empty+=1
  rows+=r['projected_rows'];raw_bytes+=r['raw_bytes']
 for r in q['quality_quarantines']:
  assert r['whole_invalid_receipt_retained_without_projection'] and r['all_other_normalizer_inputs_verified'] and not r['projection_admitted'] and not r['provider_retry_authorized']
  assert sha(R/r['receipt_file'])==r['receipt_file_sha256'];rec=load(R/r['receipt_file']);assert m.validate_receipt(rec)==r['receipt_id'] and rec['raw_sha256']==r['raw_sha256'] and key(rec)==key(r)
  assert scope['started_at_utc']<=r['observed_at_utc']<=min(q['snapshot_before_utc'],result['settled_at_utc'])
  raw=m.verified_raw(R,rec);original=next(x for x in plan['selected'] if key(x)==key(r));dates,invalid=m.scalar_check(raw,rec,original,{})
  assert invalid==r['invalid_volume_fields'] and len(dates)==r['rows'] and len(raw)==r['raw_bytes']
  hashes,found=m.artifacts(rec,r['receipt_id'],dates,invalid);assert not hashes and not found
  bad_bytes+=r['raw_bytes'];quarantines.append({k:r[k] for k in ['symbol','request_path','receipt_id','receipt_file','receipt_file_sha256','raw_sha256','raw_bytes','observed_at_utc','rows']}|{'whole_raw_retained_without_projection':True,'reviewed_preflight_sha256':sha(pfpath),'invalid_field_count':len(invalid),'market_rows_copied':False})
 for rel,digest in pf['retained_partial_artifact_sha256'].items():assert sha(R/rel)==digest
 assert sum(r['projected_rows'] for r in q['receipts'])==q['new_disjoint_bars']
 qualified|=valid;quality|=bad;qfiles[n]=h;cfiles[cp.name]=sha(cp);lastcov=cp;prior=cp
assert qualified|quality==successful and not qualified&quality and len(qualified)+len(quality)+len(failures)+len(never)==2015
assert nonempty+empty==len(qualified) and raw_bytes+bad_bytes==result['capture']['bytes']
assert rows+sum(r['rows'] for r in quarantines)==result['capture']['row_hints']
if result['all_selected_captured']:assert len(successful)==len(started)==2015 and not failures and not never
latest=load(lastcov);status=latest['candidate_capture_status_counts'];assert sum(status.values())==47689 and latest['accepted_distinct_bars']==load(E/m.BASE)['accepted_distinct_bars']+rows
proof={'schema':'tiingo.physical_continuation_qualified_quality_failure_never_accounting/v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'run_id':RUN,'method_sha256':sha(__file__),'core_sha256':CORE_SHA,'accepted_qualification_method_sha256':sorted(ACCEPTED_METHODS),'actual_original_result_sha256':sha(resultpath),'actual_original_terminal_parent_sha256':sha(parentpath),'actual_disposition_window_parent_sha256':windowproofs,'all_physical_2015_identities_accounted_exactly_once':True,'actual_original_capture_terminal_return_consumed':True,'all_listed_qualification_writer_returns_consumed':True,'successful_requests':len(successful),'qualified_successes':len(qualified),'source_quality_quarantined_successes':len(quality),'held_attempted_failures':result['capture']['errors'],'never_admitted_count':len(never),'never_admitted_requests':[r for r in plan['selected'] if key(r) in never],'quarantined_receipts':quarantines,'all_captured_successes_partitioned_between_valid_and_quality':True,'all_qualified_nonempty_reader_lineage_verified':True,'all_captured_successes_reader_qualified':not bool(quality),'all_selected_captured':result['all_selected_captured'],'qualified_nonempty_responses':nonempty,'qualified_empty_responses':empty,'qualified_disjoint_bars':rows,'qualified_raw_bytes':raw_bytes,'quarantined_raw_bytes':bad_bytes,'all_captured_raw_bytes':raw_bytes+bad_bytes,'qualification_sha256':qfiles,'coverage_sha256':cfiles,'last_coverage_file':lastcov.name,'last_coverage_sha256':sha(lastcov),'global_candidate_status':status,'global_histories':latest['accepted_nonempty_ticker_histories'],'global_bars':latest['accepted_distinct_bars'],'minimum_four_admission_gap_seconds':min(gaps) if gaps else None,'prior_failures_retried':False,'provider_requests':0,'credentials_read':False,'archive_writes':0,'source_payloads_modified':False,'complete_vendor_history_proven':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False,'programme_acceptance_claimed':False}
m.save(E/'eod-wave15-continuation02-final-disposition-partition-accounting.json',proof)
print(json.dumps({k:v for k,v in proof.items() if k not in {'qualification_sha256','coverage_sha256','quarantined_receipts','never_admitted_requests'}},indent=2),flush=True)
