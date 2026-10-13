"""One finite continuation; unchanged collector, stable credential, no failed retries."""
import hashlib,json,os,subprocess,sys,time,shutil,urllib.error,re,importlib.util
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009');sys.path.insert(0,str(C))
from collectors.tiingo_archive import Archive,collect_one,read_key,request_path,validate_receipt,require_external_root,require_space,TiingoArchiveError
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
RUN='eod-wave15-final-unreserved-20261012-01a12ab6'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,o):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(o,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 assert os.environ.get('CODEX_THREAD_ID')=='01a12ab6-92cb-7c42-a711-42673ebb6b50'
 plan_path=E/(RUN+'-planned.json');assert sha(plan_path)=='d120cc13ecbb675fa45a67b32697f7f43fa506a9406e62de29f5edafe57abbe9'
 plan=json.loads(plan_path.read_text());assert plan['request_cap']==4392 and plan['max_inflight']==4
 assert subprocess.check_output(['git','-C',str(C),'rev-parse','HEAD'],text=True).strip()==plan['calling_carrier_sha']
 for rel,digest in plan['loaded_source_sha256'].items():assert sha(C/rel)==digest
 assert require_external_root(R)==R;require_space(R,floor=40*1024**3)
 assert sha(E/'eod-qualified-catalogue-coverage-wave12-prefix19-delta.json')==plan['coverage_sha256']
 for name,digest in plan['failure_evidence_sha256'].items():assert sha(E/name)==digest
 for name,digest in plan['reserved_prior_selection_files_sha256'].items():assert sha(E/name)==digest
 remaining=[];symbols=set();pairs=set()
 for row in plan['selected']:
  params={'startDate':row['request_start'],'endDate':row['request_end']};path=request_path('eod-bars',row['symbol'],params)
  assert path==row['request_path'] and row['symbol'] not in symbols and row['symbol'] not in plan['all_prior_failed_symbols_excluded']
  assert row['request_start']<=row['request_end'];symbols.add(row['symbol']);pairs.add((row['symbol'],path))
  remaining.append({'symbol':row['symbol'],'request_path':path,'params':params})
 assert len(remaining)==len(symbols)==len(pairs)==4392
 original_scope=E/'eod-wave14-new-unreserved-20261012-01a12ab6-scope.json';original_result=E/'eod-wave14-new-unreserved-20261012-01a12ab6-result.json'
 assert sha(original_scope)=='5a3864bfed6561da598799e3f4eccb7da3c385757e80162027716460baa862cf' and sha(original_result)=='3c339b48e8b6faa028743c7725ab4b835755c8f13bffb16dbc699baf7012620e'
 prior_scope=json.loads(original_scope.read_text());prior=json.loads(original_result.read_text())
 assert prior_scope['method_sha256']=='320a8f2e46d1fa9a2655c172fc215a031fbbcde37ea9de504c0ea085dd10bf13' and not prior['all_selected_captured']
 error=prior['capture']['errors'][0];assert prior['capture']['failed']==1 and error['symbol']=='MYRUF' and error['transport_reason_class']=='TimeoutError' and error['reason']=='Tiingo transport unavailable'
 original_planp=E/'eod-wave14-new-unreserved-20261012-01a12ab6-planned.json';assert sha(original_planp)==prior_scope['plan_sha256']=='6ce216888a99b244f18fb76910d5e73a3984eace5f9df7ae3c44270ed5bb4d0a'
 original_plan=json.loads(original_planp.read_text());selected_pairs=[(r['symbol'],r['request_path']) for r in original_plan['selected']];assert len(selected_pairs)==len(set(selected_pairs))==5000
 phase='eod-wave14-original-unadmitted-continuation01-20261012-01a12ab6';phase_planp=E/(phase+'-planned.json');phase_scopep=E/(phase+'-scope.json');phase_resultp=E/(phase+'-result.json')
 assert sha(phase_planp)=='a584b99f91869de4f9bd234cae53e3374f133359d658b7c1c93e692239785e4d' and sha(phase_scopep)=='d4522213d7a9c26f3dfba38361c2c48cff3cb12773a91e3acf9dd631d0ead31f'
 accounting_path=E/'eod-wave14-original-two-phase-quality-partition-accounting.json';settled=phase_resultp.is_file() and accounting_path.is_file()
 if settled:
  accounting=json.loads(accounting_path.read_text());last=json.loads(phase_resultp.read_text())
  assert accounting['method_sha256']=='116e3826b712ecd7262f62aa4cf2696e41c8e3221dd1523d68d24177a3728cea'
  assert accounting['original_plan_sha256']==sha(original_planp) and accounting['original_scope_sha256']==sha(original_scope) and accounting['actual_original_settlement_sha256']==sha(original_result)
  assert accounting['continuation_plan_sha256']==sha(phase_planp) and accounting['continuation_scope_sha256']==sha(phase_scopep) and accounting['actual_continuation_settlement_sha256']==sha(phase_resultp)
  assert accounting['actual_original_tool_return_consumed'] and accounting['original_tool_session']==41115 and accounting['original_exit_code']==1
  assert accounting['actual_continuation_tool_return_consumed'] and accounting['continuation_tool_session']==40732 and accounting['continuation_exit_code']==0 and accounting['all_qualification_writer_returns_consumed']
  assert accounting['all_contributing_execution_phases_settled'] and accounting['all_original_5000_identities_accounted_exactly_once'] and accounting['never_admitted']==0
  assert not accounting['all_successful_request_receipts_and_reader_lineage_verified'] and accounting['all_qualified_successful_request_receipts_and_reader_lineage_verified'] and accounting['successful_requests']==4999 and accounting['qualified_successes']==4998 and accounting['source_quality_quarantined_successes']==1 and accounting['all_captured_successes_partitioned_between_qualified_and_quality']
  diagp=E/'eod-wave14-prefix16-settled-quality-and-partial-custody-diagnosis.json';assert sha(diagp)==accounting['source_quality_quarantine_diagnosis_sha256']=='72ed522bf0c81fe29bde3a61078886627f04c0616487870afc5778a72e01e7cf';diag=json.loads(diagp.read_text());assert len(diag['offenders'])==1 and accounting['quarantined_receipts']==diag['offenders'];bad=diag['offenders'][0]
  assert bad['symbol']=='RBGPF' and bad['receipt_id']=='fbc8e27fa55a315b86159989b328c73d4dc11334cbfa916e05084c310c537dbd' and bad['raw_sha256']=='fe36f5c36f07be21d1838bf09574d0a3bd46086377b3309d6c04c77d86bc06cc'
  assert sha(R/bad['receipt_file'])==bad['receipt_file_sha256']
  for selector in (bad['receipt_id'],bad['raw_sha256']):
   for directory,suffix in [('manifests','.json'),('normalized','.parquet')]:assert not (R/directory/'eod-bars'/bad['observed_at_utc'][:10]/(selector+suffix)).exists()
  quality={(bad['symbol'],bad['request_path'])};assert not quality&set((r['symbol'],r['request_path']) for r in plan['selected'])
  assert accounting['held_attempted_failures']==prior['capture']['errors'] and accounting['initial_all_selected_captured_remains_false'] and not accounting['all_5000_success_claimed'] and not accounting['prior_failures_retried']
  assert last['phase']=='settled' and last['fatal_exception_type'] is None and last['all_selected_captured']
  assert last['capture']['attempted']==last['capture']['ok']==3311 and last['capture']['failed']==0 and not last['capture']['errors']
  all_started=set();success=set()
  for pp,rr,count in [(original_plan,prior,1689),(json.loads(phase_planp.read_text()),last,3311)]:
   pairs=[(r['symbol'],r['request_path']) for r in pp['selected']];admissions=rr['actual_local_admissions'];indices=[r['selection_index'] for r in admissions]
   assert len(indices)==len(set(indices))==count and all(0<=i<len(pairs) for i in indices)
   tasks=[(r['symbol'],r['request_path']) for r in rr['all_started_tasks']];assert tasks==[pairs[i] for i in indices] and not all_started&set(tasks);all_started.update(tasks)
   good=[(r['symbol'],r['request_path']) for r in rr['successful_requests']];assert len(good)==len(set(good))==rr['capture']['ok'] and set(good)<=set(tasks) and not success&set(good);success.update(good)
   assert all(admissions[i]['admitted_monotonic']-admissions[i-4]['admitted_monotonic']>=5 for i in range(4,len(admissions)))
  failed={(error['symbol'],error['request_path'])};assert len(success)==4999 and success.isdisjoint(failed) and success|failed==all_started==set(selected_pairs)
  projected=set()
  for name,digest in accounting['qualification_sha256'].items():
   assert sha(E/name)==digest;q=json.loads((E/name).read_text());assert q['run_scope_sha256']==sha(original_scope) and q['all_selected_raw_and_reader_lineage_verified']
   for row in q['receipts']:
    pair=(row['symbol'],row['request_path']);assert pair not in projected;projected.add(pair)
    assert row['raw_checksum_verified'] and row['requested_window_verified'] and row['old_economic_dates_disjoint']
    if row['projected_rows']>0:assert row['projection_lineage_verified']
    else:assert row['projected_rows']==0 and row['raw_empty_response_verified']
    assert sha(R/row['receipt_file'])==row['receipt_file_sha256']
  assert projected==success-quality and len(projected)==4998
 else:assert '--preflight' in sys.argv,'Original wave14 two-phase actual qualified outcome is incomplete'
 holds=sorted(set(plan['all_prior_failed_symbols_excluded'])|set(prior_scope['held_symbols_excluded'])|{'MYRUF','RBGPF'})
 assert not symbols&set(holds)
 for p in (R/'receipts/eod-bars').glob('*/*.json'):
  rec=json.loads(p.read_text())
  if rec['symbol'] in symbols:
   validate_receipt(rec);raise AssertionError('New capture overlaps an existing symbol; reconcile its existing owner')
 module_path=E/'tiingo-finite-admission-reviewed-3d204f2e.py'
 assert sha(module_path)=='3d204f2e7a6ebc5d3693606a7b59b665be8f53546314c0b8053bee2be4154926'
 accepted_path=E/'tiingo-finite-admission-canonical-source-accepted.json'
 if '--preflight' not in sys.argv:
  accepted=json.loads(accepted_path.read_text())
  assert accepted['actual_merged'] and accepted['source_ci_conclusion']=='success' and accepted['independent_review_conclusion']=='PASS'
  assert accepted['module_sha256']==sha(module_path)
 if '--preflight' in sys.argv:
  print(json.dumps({'selected_unreserved_symbols':4392,'source_pins_verified':True,'held_symbols_excluded':len(holds),'existing_eod_symbol_collisions':0,'original_run_settled':settled,'credentials_read':False,'network_requests':0}));return
 quota_path=E/'eod-wave15-account-quota-preflight-01.json';quota=json.loads(quota_path.read_text())
 assert quota['intended_signed_in_account_verified'] and quota['hourly_requests_remaining']>=10000 and quota['daily_requests_remaining']>=50000 and quota['monthly_gb_remaining']>=60
 assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(quota['observed_at_utc'])).total_seconds()<=900
 out=E/(RUN+'-result.json');assert not out.exists()
 prepared={'schema':'tiingo_new_disjoint_finite_eod_scope/v1','run_id':RUN,'started_at_utc':datetime.now(timezone.utc).isoformat(),'method_sha256':sha(Path(__file__)),'plan_sha256':sha(plan_path),'prior_original_settlement_sha256':sha(original_result),'quota_proof_sha256':sha(quota_path),'request_cap':4392,'held_symbols_excluded':holds,'prior_original_qualified_outcome_accounting_sha256':sha(accounting_path),'prior_original_5000_identities_accounted_with_held_failure':True,'max_inflight':4,'admission_policy':'rolling local wrapper admissions s_i-s_(i-4)>=5 seconds','minimum_initial_prior_wave_delay_seconds':5,'minimum_rolling_admission_window_seconds':5,'reviewed_module_sha256':sha(module_path),'canonical_module_source_acceptance_sha256':sha(accepted_path),'reviewed_integration_parent_sha256':'5871b796fc640549deb51584c55693ec314634b7d3692548cdc51fe20fe0c942','raw_budget_is_stop_threshold':True,'maximum_already_admitted_raw_overshoot_bytes':4*512*1024**2,'maximum_own_requests_per_hour':2880,'raw_budget_bytes':plan['raw_budget_bytes'],'reserve_gib':35,'inflight_headroom_gib':5,'collector_unchanged':True,'credential_file_unchanged':True,'all_selected_previously_uncaptured_and_unreserved':True,'complete_attempt_ledger_claimed':False,'stop_first_error_and_settle_already_started_batch':True,'no_new_collector_service_retry_queue_or_publication':True}
 save(E/(RUN+'-scope.json'),prepared);print(json.dumps(prepared),flush=True)
 spec=importlib.util.spec_from_file_location('tiingo_reviewed_finite_admission',module_path)
 admission=importlib.util.module_from_spec(spec);sys.modules[spec.name]=admission;spec.loader.exec_module(admission)
 api_key=read_key();archive=Archive();started=time.monotonic()
 totals={'attempted':0,'ok':0,'new':0,'failed':0,'row_hints':0,'bytes':0,'errors':[]};successes=[];fatal=None;attempted_tasks=[];local_admissions=[];stop_reason=None
 def diagnose(task,error):
  detail={'source':'eod-bars','symbol':task['symbol'],'request_path':task['request_path'],'reason':str(error)}
  context=error.__context__
  if isinstance(context,urllib.error.URLError) and not isinstance(context,urllib.error.HTTPError):
   reason=context.reason;detail['transport_reason_class']=type(reason).__name__
   if isinstance(getattr(reason,'errno',None),int):detail['transport_errno']=reason.errno
   if isinstance(getattr(reason,'verify_code',None),int):detail['tls_verify_code']=reason.verify_code
   detail['transport_message_retained']=False
  if isinstance(context,urllib.error.HTTPError):
   # Read only the already-received refusal body, no second provider call.
   try:
    body=context.read(16385);detail['refusal_body_sha256']=hashlib.sha256(body).hexdigest();detail['refusal_body_bytes_bounded']=len(body)
    parsed=json.loads(body) if len(body)<=16384 else None
    text_values=[parsed] if isinstance(parsed,str) else [parsed.get(k) for k in ['detail','message','error'] if isinstance(parsed.get(k),str)] if isinstance(parsed,dict) else []
    cleaned=[]
    for value in text_values:
     value=value.replace(api_key,'[credential redacted]');value=re.sub(r'https?://\S+','[URL removed]',value);value=re.sub(r'[\w.+-]+@[\w.-]+','[address removed]',value);value=re.sub(r'[A-Za-z0-9_+/-]{24,}','[long identifier removed]',value)
     cleaned.append(''.join(c for c in value if c.isprintable())[:512])
    detail['sanitized_vendor_refusal_messages']=cleaned;detail['raw_refusal_body_retained']=False
   except Exception as diagnostic:detail['refusal_body_diagnostic_error_class']=type(diagnostic).__name__
  return detail
 try:
  result=admission.run_finite_capture(remaining,lambda task:collect_one(archive,'eod-bars',task['symbol'],api_key,task['params']),lambda:require_space(R,floor=40*1024**3),raw_budget_bytes=plan['raw_budget_bytes'])
  local_admissions=[{'selection_index':i,'admitted_monotonic':stamp} for i,stamp in result.admissions]
  attempted_tasks=[{'symbol':remaining[i]['symbol'],'request_path':remaining[i]['request_path']} for i,stamp in result.admissions];totals['attempted']=len(attempted_tasks)
  stop_reason=result.stop_reason
  if result.orchestration_error is not None:fatal=type(result.orchestration_error).__name__
  for outcome in result.outcomes:
   task=remaining[outcome.index]
   if outcome.admitted_at is None:
    if outcome.error is not None:fatal=fatal or type(outcome.error).__name__
    continue
   if outcome.error is not None:
    totals['failed']+=1
    if isinstance(outcome.error,TiingoArchiveError):totals['errors'].append(diagnose(task,outcome.error))
    else:
     fatal=fatal or type(outcome.error).__name__
     totals['errors'].append({'source':'eod-bars','symbol':task['symbol'],'request_path':task['request_path'],'exception_class':type(outcome.error).__name__,'effect_requires_same_operation_reconciliation':True})
   else:
    captured=outcome.value;totals['ok']+=1;totals['new']+=int(captured['new_raw']);totals['row_hints']+=captured['rows_hint'] or 0;totals['bytes']+=captured['raw_bytes']
    successes.append({'symbol':task['symbol'],'request_path':task['request_path']})
  assert len(result.admissions)==totals['attempted']==len(attempted_tasks)
  assert totals['bytes']==result.raw_bytes
  assert all(local_admissions[i]['admitted_monotonic']-local_admissions[i-4]['admitted_monotonic']>=5 for i in range(4,len(local_admissions)))
  assert result.complete==(totals['ok']==4392 and totals['failed']==0 and fatal is None)
 except BaseException as error:fatal=type(error).__name__
 proof={'schema':'tiingo_disjoint_finite_eod_settlement/v1','run_id':RUN,'phase':'settled' if fatal is None else 'same_operation_reconciliation_required','settled_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-started,3),'scope_sha256':sha(E/(RUN+'-scope.json')),'capture':totals,'successful_requests':successes,'all_started_tasks':attempted_tasks,'actual_local_admissions':local_admissions,'stop_reason':stop_reason,'nonadmitted_submissions_are_never_provider_attempts':True,'all_selected_captured':totals['ok']==totals['attempted']==4392 and totals['failed']==0 and fatal is None,'fatal_exception_type':fatal,'prior_failures_retried':False,'research_only':True,'pit_backtest_eligible':False}
 save(out,proof);print(json.dumps({k:v for k,v in proof.items() if k not in ('successful_requests','all_started_tasks')},indent=2),flush=True)
 raise SystemExit(1 if fatal or totals['failed'] else 0)
if __name__=='__main__':main()
