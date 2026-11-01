"""One finite max-one later diagnostic per separately reviewed settled transport window; originals retained."""
import hashlib,json,os,subprocess,sys,time,shutil,urllib.error,re,importlib.util,select,stat,plistlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009');sys.path.insert(0,str(C))
from collectors.tiingo_archive import Archive,collect_one,read_key,request_path,validate_receipt,require_external_root,require_space,TiingoArchiveError
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
RUN='eod-fourteen-settled-transport-later-diagnostic01-20261014-01a12ab6'
GATE_PHASE='entry';PUBLISHED_READY=None
EXPECTED_RECON_SHA='ef53c54aeba4d2134bac51b27b841d3a1a8f2c76ef6e3153e8d113897842df74'
EXPECTED_PLAN_SHA='0ff1630cf6497d3ef2114509e0b6d4f06d93f94e27a9da258b1d55acd9b99ebb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,o):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(o,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def namespace_snapshot(root=None):
 root=R/'receipts/eod-bars' if root is None else root;assert root.is_dir() and not root.is_symlink();values={}
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

def require_true_absence(path):
 try:path.lstat()
 except FileNotFoundError:return
 raise AssertionError('Occupied or symlinked control/output slot requires same-operation reconciliation')

def require_original_binding():
 import collectors.tiingo_archive as collector
 assert Path(collector.__file__).resolve()==(C/'collectors/tiingo_archive.py').resolve() and collector.API_ORIGIN=='https://api.tiingo.com'
 assert os.environ.get('TIINGO_API_KEY') is None and collector.DEFAULT_KEY_FILE==Path('/Volumes/Mastermind/.mastermind_private/tiingo/api_key') and read_key.__defaults__==(collector.DEFAULT_KEY_FILE,)
 key=collector.DEFAULT_KEY_FILE;st=key.stat(follow_symlinks=False);assert stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid() and not st.st_mode&0o077
 info=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/Mastermind']));assert info['VolumeUUID']=='7EE5D196-8BB6-4E6D-B1D7-AFEA5DEB172A' and info['MountPoint']=='/Volumes/Mastermind'
 assert collector.DEFAULT_ARCHIVE==R and require_external_root(R)==R

def validation():
 require_original_binding()
 assert os.environ.get('CODEX_THREAD_ID')=='01a12ab6-92cb-7c42-a711-42673ebb6b50' and sys.flags.optimize==0
 pp=E/(RUN+'-planned01.json');assert sha(pp)==EXPECTED_PLAN_SHA;plan=json.loads(pp.read_text());assert plan['root']==os.environ['CODEX_THREAD_ID'] and plan['request_cap']==14 and plan['maximum_additional_attempts_per_request']==1 and plan['max_inflight']==4
 assert subprocess.check_output(['git','-C',str(C),'rev-parse','HEAD'],text=True).strip()==plan['calling_carrier_sha']
 for rel,digest in plan['loaded_source_sha256'].items():assert sha(C/rel)==digest
 assert require_external_root(R)==R;require_space(R,floor=80*1024**3)
 for n,digest in plan['evidence_sha256'].items():assert sha(E/n)==digest
 for fn,hk in [('accounting_file','accounting_sha256'),('accounting_parent_file','accounting_parent_sha256'),('coverage_file','coverage_sha256')]:assert sha(E/plan[fn])==plan[hk]
 account=json.loads((E/plan['accounting_file']).read_text());parent=json.loads((E/plan['accounting_parent_file']).read_text());coverage=json.loads((E/plan['coverage_file']).read_text())
 assert parent['root']==os.environ['CODEX_THREAD_ID'] and parent['actual_accounting_native_exit_code']==0 and parent['actual_accounting_native_terminal_consumed'] is True and parent['actual_accounting_sha256']==plan['accounting_sha256']
 assert account['never_admitted_count']==0 and account['all_actual_capture_terminal_returns_consumed'] is True and account['all_qualification_effects_verified_and_accepted'] is True and account['all_original_qualification_terminal_returns_consumed'] is False and account['unknown_original_qualifier_sessions']==[22925,91287]
 control=E/'tiingo-fourteen-one-attempt-diagnostic-proposal-control.json';assert sha(control)=='d3069b2d379bde69ce9ce79feced2fe44317141a83ee50eef551045ccbf3ca2a'
 ruling=json.loads(control.read_text());assert ruling['ruling'].startswith('CONDITIONAL_PASS_CONCRETE_FOURTEEN_ONE_LATER_ATTEMPT_PROPOSAL') and ruling['conditional_scope']['maximum_total_additional_admissions']==14
 original=json.loads((E/'tiingo-remaining-fourteen-original-failure-control-classification.json').read_text());eligible=original['original_attempts']
 failures={(x['symbol'],x['request_path']):x for x in eligible};assert len(failures)==14 and {x['symbol'] for x in eligible}==set(ruling['conditional_scope']['symbols'])
 assert len(original['ordinary_timeout_candidates'])==3 and len(original['generic_unclassified_held'])==11
 for failure in eligible:
  assert failure['original_error_fields']['reason']=='Tiingo transport unavailable' and failure['classification'] in ['GENERIC_URLERROR_CAUSE_UNRETAINED_HOLD','PROVEN_ORDINARY_TIMEOUT_CANDIDATE_FOR_BOUNDED_LATER_REPAIR']
  previous=json.loads((E/failure['original_phase_result']).read_text());assert previous['phase']=='settled' and sha(E/failure['original_phase_result'])==failure['result_sha256'] and sha(E/failure['scope_file'])==failure['scope_sha256']
 latest=json.loads((E/'tiingo-eleven-later-repair-actual-final-parent-consumption.json').read_text());assert latest['root']==os.environ['CODEX_THREAD_ID']
 remaining=[];symbols=set();missing={r['ticker']:r for r in coverage['missing_request_windows']}
 for row in plan['selected']:
  params={'startDate':row['request_start'],'endDate':row['request_end']};path=request_path('eod-bars',row['symbol'],params);assert path==row['request_path'] and (row['symbol'],path) in failures and row['symbol'] not in symbols and row['maximum_additional_attempts']==1 and missing[row['symbol']]['missing_request_windows']==[[row['request_start'],row['request_end']]]
  assert row['original_classification']==failures[(row['symbol'],path)]['classification'] and row['old_reason_class_not_reconstructed']==(row['original_classification']=='GENERIC_URLERROR_CAUSE_UNRETAINED_HOLD')
  symbols.add(row['symbol']);remaining.append({'symbol':row['symbol'],'request_path':path,'params':params})
 assert len(remaining)==len(symbols)==14
 # Three complete metadata namespaces, including partial leaves, remain exact across collision parse.
 roots=[R/'receipts/eod-bars',R/'raw/eod-bars',R/'normalized/eod-bars',R/'manifests/eod-bars'];before={str(root):namespace_snapshot(root) for root in roots}
 for root,snapshot in before.items():
  assert not any(Path(rel).name.startswith(('.incoming-','.parquet-')) for rel in snapshot),'Unclassified retained partial requires same-carrier reconciliation; no cleanup'
 for p in (R/'receipts/eod-bars').glob('*/*.json'):
  rec=json.loads(p.read_text())
  if rec['symbol'] in symbols:
   validate_receipt(rec);raise AssertionError('Existing receipt on repair symbol requires owner/collision reconciliation')
 after={str(root):namespace_snapshot(root) for root in roots};assert before==after
 module=E/'tiingo-finite-admission-reviewed-3d204f2e.py';assert sha(module)=='3d204f2e7a6ebc5d3693606a7b59b665be8f53546314c0b8053bee2be4154926'
 accepted=E/'tiingo-finite-admission-canonical-source-accepted.json';a=json.loads(accepted.read_text());assert a['actual_merged'] and a['source_ci_conclusion']=='success' and a['independent_review_conclusion']=='PASS' and a['module_sha256']==sha(module)
 return plan,pp,remaining,module,accepted,sha(accepted),after

def main():
 global GATE_PHASE,PUBLISHED_READY
 GATE_PHASE='initial_reconciliation'
 reconcile=E/'tiingo-fourteen-original-validation-expiry-same-operation-reconciliation01.json';assert sha(reconcile)==EXPECTED_RECON_SHA
 recovery=json.loads(reconcile.read_text());assert recovery['run_id']==RUN and recovery['provider_attempts_reachable']==0 and recovery['binding_delivery'] is False and recovery['original_terminal_return_consumed'] is False
 assert sys.argv[1:]==['--attended-one-shot-quota-gate'] and sys.flags.optimize==0
 GATE_PHASE='read_only_validation'
 method=sha(Path(__file__));plan,pp,remaining,module,accepted,accepted_sha,snapshot=validation();assert sha(Path(__file__))==method and sha(reconcile)==EXPECTED_RECON_SHA
 out=E/(RUN+'-result.json');scopep=E/(RUN+'-scope.json');executionp=E/(RUN+'-execution.log')
 for slot in [out,scopep,executionp]:require_true_absence(slot)
 snapshotp=E/(RUN+'-validation-namespace02.json');save(snapshotp,snapshot);snapshot_sha=sha(snapshotp);ready_path=E/(RUN+'-validation-ready02.json');deadline=time.monotonic()+3600
 ready={'schema':'tiingo.actual_validation_completed_awaiting_fresh_quota/v1','run_id':RUN,'root':os.environ['CODEX_THREAD_ID'],'process_id':os.getpid(),'validated_at_utc':datetime.now(timezone.utc).isoformat(),'method_sha256':method,'plan_sha256':EXPECTED_PLAN_SHA,'preadmission_rearm_reconciliation_sha256':EXPECTED_RECON_SHA,'original_validation90730_terminal_not_reconstructed':True,'validation_function_returned_successfully':True,'process_terminal_exit_code':None,'quota_wait_seconds':3600,'quota_wait_absolute_monotonic_deadline':deadline,'request_count':14,'namespace_snapshot_file':snapshotp.name,'namespace_snapshot_sha256':snapshot_sha,'namespace_entry_count':sum(len(v) for v in snapshot.values()),'complete_receipt_raw_projection_namespace_stable_with_no_unknown_partial':True,'no_receipt_for_any_selected_symbol':True,'original_failures_kept_historical':True,'all_previous_raw_returns_and_QA_effects_consumed':True,'previous_unknown_original_QA_terminals_preserved':[22925,91287],'credentials_read':False,'provider_requests':0,'archive_writes':0,'universal_writer_absence_claimed':False}
 assert sha(reconcile)==EXPECTED_RECON_SHA
 save(ready_path,ready);ready_sha=sha(ready_path);PUBLISHED_READY={'file':ready_path.name,'sha256':ready_sha};GATE_PHASE='awaiting_fresh_quota_binding';print(json.dumps({'phase':'validation_completed_awaiting_fresh_quota','ready_file':ready_path.name,'ready_sha256':ready_sha,'process_id':os.getpid(),'process_terminal_exit_code':None,'provider_requests':0,'credentials_read':False}),flush=True)
 gate=json.loads(bounded_gate_line(3600,deadline));GATE_PHASE='received_binding_final_validation';assert isinstance(gate,dict) and set(gate)=={'ready_sha256','parent_consumption_file','parent_consumption_sha256','quota_preflight_file','quota_preflight_sha256'} and gate['ready_sha256']==ready_sha
 def bound(n,digest):
  assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,180}',n) and re.fullmatch(r'[0-9a-f]{64}',digest);p=E/n;assert not p.is_symlink();data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest;return json.loads(data)
 parent=bound(gate['parent_consumption_file'],gate['parent_consumption_sha256']);quota=bound(gate['quota_preflight_file'],gate['quota_preflight_sha256'])
 assert parent['schema']=='tiingo.attended_validation_READY_actual_parent_consumption/v1' and parent['actual_ready_return_consumed'] is True and parent['revised_validation_gate_explicitly_accepted'] is True and parent['method_sha256']==method and parent['plan_sha256']==EXPECTED_PLAN_SHA and parent['root']==os.environ['CODEX_THREAD_ID'] and parent['run_id']==RUN and parent['ready_sha256']==ready_sha and parent['original_process_id']==os.getpid() and parent['process_terminal_exit_code'] is None
 ready_time=datetime.fromisoformat(ready['validated_at_utc']);quota_time=datetime.fromisoformat(quota['observed_at_utc']);parent_time=datetime.fromisoformat(parent['recorded_at_utc']);assert all(v.tzinfo is not None and v.utcoffset()==timezone.utc.utcoffset(v) for v in [ready_time,quota_time,parent_time]) and ready_time<=quota_time and ready_time<=parent_time
 assert quota['schema']=='tiingo.visible_authenticated_usage_preflight/v1' and quota['intended_signed_in_account_verified'] is True and quota['page_reload_and_visible_dom_observed'] is True and quota['account_username']=='mastermindx6031' and quota['source_url']=='https://www.tiingo.com/account/api/usage' and quota['hourly_requests_remaining']>=10000 and quota['daily_requests_remaining']>=50000 and quota['monthly_gb_remaining']>=60
 assert {root:namespace_snapshot(Path(root)) for root in snapshot}==snapshot
 assert sha(reconcile)==EXPECTED_RECON_SHA
 assert sha(pp)==EXPECTED_PLAN_SHA and sha(Path(__file__))==method and sha(ready_path)==ready_sha and sha(snapshotp)==snapshot_sha and sha(module)=='3d204f2e7a6ebc5d3693606a7b59b665be8f53546314c0b8053bee2be4154926' and sha(accepted)==accepted_sha
 assert subprocess.check_output(['git','-C',str(C),'rev-parse','HEAD'],text=True).strip()==plan['calling_carrier_sha']
 for rel,digest in plan['loaded_source_sha256'].items():assert sha(C/rel)==digest
 for n,digest in plan['evidence_sha256'].items():assert sha(E/n)==digest
 for fn,hk in [('accounting_file','accounting_sha256'),('accounting_parent_file','accounting_parent_sha256'),('coverage_file','coverage_sha256')]:assert sha(E/plan[fn])==plan[hk]
 assert sha(E/'tiingo-fourteen-one-attempt-diagnostic-proposal-control.json')=='d3069b2d379bde69ce9ce79feced2fe44317141a83ee50eef551045ccbf3ca2a'
 assert require_external_root(R)==R;require_space(R,floor=80*1024**3);assert 0<=(datetime.now(timezone.utc)-quota_time).total_seconds()<=900
 for slot in [out,scopep,executionp]:require_true_absence(slot)
 GATE_PHASE='exclusive_scope_publication'
 execution_log=executionp.open('x');prepared={'schema':'tiingo.separate_finite_settled_transport_later_diagnostic_scope/v1','run_id':RUN,'root':os.environ['CODEX_THREAD_ID'],'started_at_utc':datetime.now(timezone.utc).isoformat(),'method_sha256':method,'plan_sha256':EXPECTED_PLAN_SHA,'actual_validation_ready_sha256':ready_sha,'actual_ready_parent_sha256':gate['parent_consumption_sha256'],'quota_proof_sha256':gate['quota_preflight_sha256'],'validation_namespace_snapshot_sha256':snapshot_sha,'request_cap':14,'maximum_additional_attempts_per_request':1,'raw_budget_is_stop_threshold':True,'raw_budget_bytes':plan['raw_budget_bytes'],'maximum_already_admitted_raw_overshoot_bytes':2147483648,'max_inflight':4,'minimum_rolling_admission_window_seconds':5,'minimum_initial_delay_seconds':5,'maximum_own_requests_per_hour':2880,'original_collector_and_strict_TLS_and_30s_timeout_unchanged':True,'credential_file_and_account_unchanged':True,'standing_floor_gib':40,'pending_QA_allowance_gib':40,'free_space_floor_gib':80,'original_six_phase_accounting_sha256':plan['accounting_sha256'],'original_six_phase_actual_root_sha256':plan['accounting_parent_sha256'],'original_attempt_failures_retained':True,'automatic_next_repair':False,'old_refused_operations_excluded':True,'complete_vendor_history_claimed':False}
 save(scopep,prepared);print(json.dumps(prepared),file=execution_log,flush=True)
 module_path=module
 spec=importlib.util.spec_from_file_location('tiingo_reviewed_finite_admission',module_path)
 admission=importlib.util.module_from_spec(spec);sys.modules[spec.name]=admission;spec.loader.exec_module(admission)
 GATE_PHASE='capture_scope_published_before_key';assert sha(reconcile)==EXPECTED_RECON_SHA
 require_original_binding();api_key=read_key();archive=Archive(root=R,free_floor=80*1024**3);started=time.monotonic()
 totals={'attempted':0,'ok':0,'new':0,'failed':0,'row_hints':0,'bytes':0,'errors':[]};successes=[];fatal=None;attempted_tasks=[];local_admissions=[];stop_reason=None;admission_ledger_available=False
 def diagnose(task,error):
  context=error.__context__;detail={'source':'eod-bars','symbol':task['symbol'],'request_path':task['request_path'],'exception_class':type(error).__name__,'context_class':type(context).__name__ if context is not None else None,'raw_exception_string_retained':False,'response_body_read':False}
  if isinstance(context,urllib.error.HTTPError):
   detail['http_status']=context.code;detail['explicit_access_denial']=context.code in [401,403];detail['provider_rate_limit']=context.code==429
  if isinstance(context,urllib.error.URLError) and not isinstance(context,urllib.error.HTTPError):
   reason=context.reason;detail['transport_reason_class']=type(reason).__name__
   if isinstance(getattr(reason,'errno',None),int):detail['transport_errno']=reason.errno
   if isinstance(getattr(reason,'verify_code',None),int):detail['tls_verify_code']=reason.verify_code
   detail['transport_message_retained']=False
  return detail

 try:
  result=admission.run_finite_capture(remaining,lambda task:collect_one(archive,'eod-bars',task['symbol'],api_key,task['params']),lambda:require_space(R,floor=80*1024**3),raw_budget_bytes=plan['raw_budget_bytes'])
  admission_ledger_available=True
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
  assert result.complete==(totals['ok']==14 and totals['failed']==0 and fatal is None)
 except BaseException as error:fatal=type(error).__name__
 proof={'schema':'tiingo.separate_finite_settled_transport_later_diagnostic_settlement/v1','run_id':RUN,'phase':'settled' if fatal is None else 'same_operation_reconciliation_required','settled_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-started,3),'scope_sha256':sha(E/(RUN+'-scope.json')),'capture':totals,'successful_requests':successes,'all_started_tasks':attempted_tasks,'actual_local_admissions':local_admissions,'stop_reason':stop_reason,'nonadmitted_submissions_are_never_provider_attempts':True,'all_selected_captured':totals['ok']==totals['attempted']==14 and totals['failed']==0 and fatal is None,'fatal_exception_type':fatal,'never_admitted_count':len(remaining)-len(local_admissions) if admission_ledger_available else None,'placeholder_counts_and_task_lists_authoritative':admission_ledger_available,'old_unknown_reason_classes_not_reconstructed':True,'prior_failures_retried':bool(local_admissions) if admission_ledger_available else None,'actual_admission_ledger_available':admission_ledger_available,'separate_later_repair_scope':True,'maximum_additional_attempts_per_request':1,'original_failed_attempts_retained':True,'automatic_successor_repair':False,'research_only':True,'pit_backtest_eligible':False}
 save(out,proof);print(json.dumps({k:v for k,v in proof.items() if k not in ('successful_requests','all_started_tasks')},indent=2),file=execution_log,flush=True)
 raise SystemExit(1 if fatal or totals['failed'] else 0)
if __name__=='__main__':
 try:main()
 except SystemExit as result:
  print(json.dumps({'original_attended_capture_exit_code':result.code,'run_id':RUN}),flush=True);raise
 except BaseException as error:
  scope=E/(RUN+'-scope.json');log=E/(RUN+'-execution.log')
  def truly_absent(path):
   try:path.lstat()
   except FileNotFoundError:return True
   except OSError:return False
   return False
  if truly_absent(scope) and truly_absent(log):
   save(E/(RUN+'-preadmission-abort02.json'),{'schema':'tiingo.foreground_preadmission_abort/v1','run_id':RUN,'root':os.environ.get('CODEX_THREAD_ID'),'process_id':os.getpid(),'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'method_sha256':sha(Path(__file__)),'exception_class':type(error).__name__,'process_local_gate_phase':GATE_PHASE,'published_READY':PUBLISHED_READY,'scope_and_execution_log_lstat_absent':True,'raw_exception_string_retained':False,'provider_requests_reachable':0,'credentials_read':False,'original_native_terminal_consumption_not_claimed':True})
  raise
