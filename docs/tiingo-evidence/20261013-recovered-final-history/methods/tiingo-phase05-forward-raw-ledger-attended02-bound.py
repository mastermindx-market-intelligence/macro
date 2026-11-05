"""One finite continuation; unchanged collector, stable credential, no failed retries."""
import hashlib,json,os,subprocess,sys,time,shutil,urllib.error,re,importlib.util,select,stat
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009');sys.path.insert(0,str(C))
from collectors.tiingo_archive import Archive,collect_one,read_key,request_path,validate_receipt,require_external_root,require_space,TiingoArchiveError
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
RUN='eod-wave15-original-unadmitted-continuation05-20261013-01a12ab6'
EXPECTED_PLAN_SHA='462f48cb52d0b19853bf1b6e62e69c5b803f4baaa8124115445eb988fbedb62a'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,o):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(o,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def namespace_snapshot():
 root=R/'receipts/eod-bars';assert root.is_dir() and not root.is_symlink();values={}
 def add(p):
  st=p.stat(follow_symlinks=False);assert not stat.S_ISLNK(st.st_mode) and (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode))
  values[str(p.relative_to(root))]=[st.st_dev,st.st_ino,st.st_mode,st.st_nlink,st.st_size,st.st_mtime_ns,st.st_ctime_ns]
 add(root)
 def walk_error(error):raise error
 for directory,dirs,files in os.walk(root,followlinks=False,onerror=walk_error):
  for name in sorted(dirs+files):add(Path(directory)/name)
 return values
def bounded_gate_line(wait_seconds=300,absolute_deadline=None):
 fd=sys.stdin.fileno();blocking=os.get_blocking(fd);deadline=time.monotonic()+wait_seconds if absolute_deadline is None else absolute_deadline;buffer=bytearray()
 os.set_blocking(fd,False)
 try:
  while True:
   left=deadline-time.monotonic();assert left>0,'Attended quota input deadline expired before provider admission'
   assert select.select([fd],[],[],left)[0],'Attended quota input deadline expired before provider admission'
   try:chunk=os.read(fd,8193-len(buffer))
   except BlockingIOError:continue
   assert chunk,'Attended quota EOF before complete binding'
   buffer.extend(chunk);assert len(buffer)<=8192,'Attended quota binding oversized'
   if b'\n' in buffer:
    assert buffer.endswith(b'\n') and buffer.count(b'\n')==1,'More than one attended quota binding'
    return bytes(buffer).decode('utf-8')
 finally:os.set_blocking(fd,blocking)

def validation():
 assert os.environ.get('CODEX_THREAD_ID')=='01a12ab6-92cb-7c42-a711-42673ebb6b50'
 plan_path=E/(RUN+'-planned-raw-ledger-attended01.json');assert sha(plan_path)==EXPECTED_PLAN_SHA
 plan=json.loads(plan_path.read_text());assert plan['request_cap']==121 and plan['max_inflight']==4
 assert subprocess.check_output(['git','-C',str(C),'rev-parse','HEAD'],text=True).strip()==plan['calling_carrier_sha']
 for rel,digest in plan['loaded_source_sha256'].items():assert sha(C/rel)==digest
 assert require_external_root(R)==R;require_space(R,floor=80*1024**3)
 coveragep=E/plan['coverage_file'];assert sha(coveragep)==plan['coverage_sha256']
 for name,digest in plan['failure_evidence_sha256'].items():assert sha(E/name)==digest
 for name,digest in plan['reserved_prior_selection_files_sha256'].items():assert sha(E/name)==digest
 original_scope=E/'eod-wave15-final-unreserved-20261012-01a12ab6-scope.json';original_planp=E/'eod-wave15-final-unreserved-20261012-01a12ab6-planned.json'
 assert sha(original_scope)=='667cdddc5f468129459fd45040f8fe69e938ed40b8da0766b0cad7a3c929d7b3' and sha(original_planp)=='d120cc13ecbb675fa45a67b32697f7f43fa506a9406e62de29f5edafe57abbe9'
 original_plan=json.loads(original_planp.read_text())
 accounting_path=E/plan['raw_admission_basis_file'];assert sha(accounting_path)==plan['raw_admission_basis_sha256'];accounting=json.loads(accounting_path.read_text())
 acceptedp=E/plan['raw_basis_parent_file'];assert sha(acceptedp)==plan['raw_basis_parent_sha256'];accepted=json.loads(acceptedp.read_text())
 assert accepted['root']=='01a12ab6-92cb-7c42-a711-42673ebb6b50' and accepted['actual_original_terminal_return_consumed'] is True and accepted['original_exit_code']==0 and accepted['actual_admission_basis_sha256']==sha(accounting_path)
 assert accepted['basis_method_sha256']==accounting['method_sha256']=='b0c2a79756684927eb3312d0f65a470ba5723afaf9a58810a34187e824b38574'
 assert accounting['root']==accepted['root'] and accounting['all_five_actual_capture_terminal_returns_consumed'] is True and accounting['every_prior_started_request_excluded'] is True
 assert accounting['started_count']==4271 and accounting['captured_success_count']==4261 and accounting['held_attempted_failure_count']==10 and accounting['never_admitted_count']==121
 assert accounting['current_phase04_qualification_complete_claimed'] is False and accounting['final_five_phase_disposition_accepted'] is False
 assert plan['selected']==accounting['never_admitted_requests']
 original_result=E/'eod-wave15-original-unadmitted-continuation04-20261013-01a12ab6-result.json';assert sha(original_result)==accounting['actual_capture_result_sha256'][original_result.name]
 started_pairs=set()
 for name,digest in accounting['actual_capture_result_sha256'].items():
  assert sha(E/name)==digest;r=json.loads((E/name).read_text());assert r['phase']=='settled' and r['fatal_exception_type'] is None
  current={(v['symbol'],v['request_path']) for v in r['all_started_tasks']};assert not started_pairs&current;started_pairs|=current
 for mapping in [accounting['actual_capture_parent_sha256'],accounting['actual_capture_plan_sha256']]:
  for name,digest in mapping.items():assert sha(E/name)==digest
 assert len(started_pairs)==4271 and plan['selected']==[r for r in original_plan['selected'] if (r['symbol'],r['request_path']) not in started_pairs]
 assert 0<plan['raw_budget_bytes']<=min(1024**3,accounting['remaining_original_raw_budget_bytes'])
 assert plan['joint_pending_QA_budget_allowance_gib']==40 and plan['minimum_archive_free_gib']==80 and plan['raw_maximum_inflight_overshoot_bytes']==4*512*1024**2
 holds=accounting['all_prior_failed_or_quality_symbols_excluded']
 assert holds==plan['all_identified_prior_failed_or_quality_symbols_excluded'] and len(holds)==35
 remaining=[];symbols=set();pairs=set()
 for row in plan['selected']:
  params={'startDate':row['request_start'],'endDate':row['request_end']};path=request_path('eod-bars',row['symbol'],params)
  assert path==row['request_path'] and row['symbol'] not in symbols and row['symbol'] not in holds and row['request_start']<=row['request_end']
  symbols.add(row['symbol']);pairs.add((row['symbol'],path));remaining.append({'symbol':row['symbol'],'request_path':path,'params':params})
 assert len(remaining)==len(symbols)==len(pairs)==121
 assert not {(r['symbol'],r['request_path']) for r in plan['selected']}&started_pairs
 before=namespace_snapshot()
 for p in (R/'receipts/eod-bars').glob('*/*.json'):
  rec=json.loads(p.read_text())
  if rec['symbol'] in symbols:
   validate_receipt(rec);raise AssertionError('Never-admitted continuation overlaps an existing EOD symbol; reconcile its owner')
 after=namespace_snapshot();assert before==after,'EOD receipt namespace changed during collision validation'
 module_path=E/'tiingo-finite-admission-reviewed-3d204f2e.py'
 assert sha(module_path)=='3d204f2e7a6ebc5d3693606a7b59b665be8f53546314c0b8053bee2be4154926'
 accepted_path=E/'tiingo-finite-admission-canonical-source-accepted.json'
 acceptance_bytes=accepted_path.read_bytes();accepted=json.loads(acceptance_bytes);acceptance_sha=hashlib.sha256(acceptance_bytes).hexdigest()
 assert accepted['actual_merged'] and accepted['source_ci_conclusion']=='success' and accepted['independent_review_conclusion']=='PASS'
 assert accepted['module_sha256']==sha(module_path)
 return plan,plan_path,accounting_path,acceptedp,original_result,holds,remaining,module_path,accepted_path,acceptance_sha,after

def main():
 assert sys.argv[1:]==['--attended-one-shot-quota-gate'] and sys.flags.optimize==0
 validated_method_sha=sha(Path(__file__))
 plan,plan_path,accounting_path,acceptedp,original_result,holds,remaining,module_path,accepted_path,acceptance_sha,snapshot=validation()
 assert sha(Path(__file__))==validated_method_sha
 assert isinstance(plan['admission_control_proof_sha256'],dict) and plan['admission_control_proof_sha256']
 for name,digest in plan['admission_control_proof_sha256'].items():assert sha(E/name)==digest
 out=E/(RUN+'-result.json');assert not out.exists() and not (E/(RUN+'-scope.json')).exists()
 snapshotp=E/(RUN+'-raw-ledger-attended01-validation-namespace.json');save(snapshotp,snapshot);validated_snapshot_sha=sha(snapshotp)
 ready_path=E/(RUN+'-raw-ledger-attended01-validation-ready.json')
 wait_deadline=time.monotonic()+300
 ready={'schema':'tiingo.actual_validation_completed_awaiting_fresh_quota/v1','run_id':RUN,'root':os.environ['CODEX_THREAD_ID'],'process_id':os.getpid(),'validated_at_utc':datetime.now(timezone.utc).isoformat(),'method_sha256':validated_method_sha,'plan_sha256':EXPECTED_PLAN_SHA,'validation_function_returned_successfully':True,'process_terminal_exit_code':None,'quota_wait_seconds':300,'quota_wait_absolute_monotonic_deadline':wait_deadline,'request_count':121,'holds_excluded':len(holds),'namespace_snapshot_file':snapshotp.name,'namespace_snapshot_sha256':validated_snapshot_sha,'namespace_entry_count':len(snapshot),'full_collision_parse_between_equal_complete_namespace_snapshots':True,'credentials_read':False,'provider_requests':0,'archive_writes':0,'no_competing_EOD_writer_identified_in_reconciled_mission_scope':True,'universal_writer_absence_claimed':False,'original_preflight20348_return_relabelled':False}
 save(ready_path,ready);validated_ready_sha=sha(ready_path);print(json.dumps({'phase':'validation_completed_awaiting_fresh_quota','ready_file':ready_path.name,'ready_sha256':validated_ready_sha,'process_id':os.getpid(),'process_terminal_exit_code':None,'provider_requests':0,'credentials_read':False}),flush=True)
 line=bounded_gate_line(300,wait_deadline)
 gate=json.loads(line);assert isinstance(gate,dict) and set(gate)=={'ready_sha256','parent_consumption_file','parent_consumption_sha256','quota_preflight_file','quota_preflight_sha256'}
 assert gate['ready_sha256']==validated_ready_sha
 def bound(name,digest):
  assert isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,180}',name) and isinstance(digest,str) and re.fullmatch(r'[0-9a-f]{64}',digest)
  path=E/name;assert not path.is_symlink();data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==digest;return path,json.loads(data)
 parentp,parent=bound(gate['parent_consumption_file'],gate['parent_consumption_sha256'])
 assert parent['schema']=='tiingo.attended_validation_READY_actual_parent_consumption/v1' and parent['actual_ready_return_consumed'] is True and parent['revised_validation_gate_explicitly_accepted'] is True
 assert parent['method_sha256']==validated_method_sha and parent['plan_sha256']==EXPECTED_PLAN_SHA
 assert parent['root']==os.environ['CODEX_THREAD_ID'] and parent['run_id']==RUN and parent['actual_ready_return_consumed'] and parent['ready_sha256']==validated_ready_sha and parent['original_process_id']==os.getpid() and parent['process_terminal_exit_code'] is None and parent['revised_validation_gate_explicitly_accepted']
 quota_path,quota=bound(gate['quota_preflight_file'],gate['quota_preflight_sha256'])
 assert quota['schema']=='tiingo.visible_authenticated_usage_preflight/v1' and quota['intended_signed_in_account_verified'] is True and quota['page_reload_and_visible_dom_observed'] is True
 quota_time=datetime.fromisoformat(quota['observed_at_utc']);ready_time=datetime.fromisoformat(ready['validated_at_utc']);parent_time=datetime.fromisoformat(parent['recorded_at_utc'])
 assert all(v.tzinfo is not None and v.utcoffset()==timezone.utc.utcoffset(v) for v in [quota_time,ready_time,parent_time])
 assert ready_time<=quota_time and ready_time<=parent_time
 assert namespace_snapshot()==snapshot,'EOD receipt namespace changed after READY; reconcile original scope'
 assert subprocess.check_output(['git','-C',str(C),'rev-parse','HEAD'],text=True).strip()==plan['calling_carrier_sha']
 for rel,digest in plan['loaded_source_sha256'].items():assert sha(C/rel)==digest
 assert sha(plan_path)==EXPECTED_PLAN_SHA and not out.exists() and not (E/(RUN+'-scope.json')).exists()
 for name,digest in {**plan['failure_evidence_sha256'],**plan['reserved_prior_selection_files_sha256'],**plan['admission_control_proof_sha256']}.items():assert sha(E/name)==digest
 assert sha(accounting_path)==plan['raw_admission_basis_sha256'] and sha(acceptedp)==plan['raw_basis_parent_sha256'] and sha(E/plan['coverage_file'])==plan['coverage_sha256']
 assert sha(Path(__file__))==validated_method_sha and sha(ready_path)==validated_ready_sha and sha(snapshotp)==validated_snapshot_sha
 assert sha(module_path)=='3d204f2e7a6ebc5d3693606a7b59b665be8f53546314c0b8053bee2be4154926' and sha(accepted_path)==acceptance_sha
 assert require_external_root(R)==R;require_space(R,floor=80*1024**3)
 assert quota['intended_signed_in_account_verified'] and quota['account_username']=='mastermindx6031' and quota['source_url']=='https://www.tiingo.com/account/api/usage' and quota['hourly_requests_remaining']>=10000 and quota['daily_requests_remaining']>=50000 and quota['monthly_gb_remaining']>=60
 assert 0<=(datetime.now(timezone.utc)-quota_time).total_seconds()<=900
 execution_log=(E/(RUN+'-raw-ledger-attended01-execution.log')).open('x')
 prepared={'schema':'tiingo_new_disjoint_finite_eod_scope/v1','run_id':RUN,'started_at_utc':datetime.now(timezone.utc).isoformat(),'method_sha256':validated_method_sha,'plan_sha256':EXPECTED_PLAN_SHA,'prior_physical_settlement_sha256':sha(original_result),'quota_proof_sha256':gate['quota_preflight_sha256'],'actual_validation_ready_sha256':validated_ready_sha,'actual_ready_parent_consumption_sha256':gate['parent_consumption_sha256'],'validation_namespace_snapshot_sha256':validated_snapshot_sha,'revised_validation_stage_gate_used':True,'original_terminal_preflight_not_relabelled':True,'request_cap':121,'held_symbols_excluded':holds,'prior_raw_ledger_admission_basis_sha256':plan['raw_admission_basis_sha256'],'prior_raw_basis_actual_parent_sha256':plan['raw_basis_parent_sha256'],'all_prior_capture_returns_consumed':True,'phase04_qualification_complete_claimed':False,'joint_pending_QA_budget_allowance_gib':40,'joint_free_space_floor_gib':80,'prior_original_4392_success_not_claimed':True,'max_inflight':4,'admission_policy':'rolling local wrapper admissions s_i-s_(i-4)>=5 seconds','minimum_initial_prior_wave_delay_seconds':5,'minimum_rolling_admission_window_seconds':5,'reviewed_module_sha256':sha(module_path),'canonical_module_source_acceptance_sha256':acceptance_sha,'reviewed_integration_parent_sha256':'5871b796fc640549deb51584c55693ec314634b7d3692548cdc51fe20fe0c942','raw_budget_is_stop_threshold':True,'maximum_already_admitted_raw_overshoot_bytes':4*512*1024**2,'maximum_own_requests_per_hour':2880,'raw_budget_bytes':plan['raw_budget_bytes'],'reserve_gib':35,'inflight_headroom_gib':5,'additional_pending_QA_reserve_gib':40,'collector_unchanged':True,'credential_file_unchanged':True,'all_selected_original_never_admitted_requests':True,'complete_attempt_ledger_claimed':False,'stop_first_error_and_settle_already_started_batch':True,'no_new_collector_service_retry_queue_or_publication':True}
 save(E/(RUN+'-scope.json'),prepared);print(json.dumps(prepared),file=execution_log,flush=True)
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
  result=admission.run_finite_capture(remaining,lambda task:collect_one(archive,'eod-bars',task['symbol'],api_key,task['params']),lambda:require_space(R,floor=80*1024**3),raw_budget_bytes=plan['raw_budget_bytes'])
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
  assert result.complete==(totals['ok']==121 and totals['failed']==0 and fatal is None)
 except BaseException as error:fatal=type(error).__name__
 proof={'schema':'tiingo_disjoint_finite_eod_settlement/v1','run_id':RUN,'phase':'settled' if fatal is None else 'same_operation_reconciliation_required','settled_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-started,3),'scope_sha256':sha(E/(RUN+'-scope.json')),'capture':totals,'successful_requests':successes,'all_started_tasks':attempted_tasks,'actual_local_admissions':local_admissions,'stop_reason':stop_reason,'nonadmitted_submissions_are_never_provider_attempts':True,'all_selected_captured':totals['ok']==totals['attempted']==121 and totals['failed']==0 and fatal is None,'fatal_exception_type':fatal,'prior_failures_retried':False,'research_only':True,'pit_backtest_eligible':False}
 save(out,proof);print(json.dumps({k:v for k,v in proof.items() if k not in ('successful_requests','all_started_tasks')},indent=2),file=execution_log,flush=True)
 raise SystemExit(1 if fatal or totals['failed'] else 0)
if __name__=='__main__':
 try:main()
 except SystemExit as result:
  print(json.dumps({'original_attended_capture_exit_code':result.code,'run_id':RUN}),flush=True);raise
