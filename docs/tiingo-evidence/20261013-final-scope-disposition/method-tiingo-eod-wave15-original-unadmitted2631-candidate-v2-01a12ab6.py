"""One finite continuation; unchanged collector, stable credential, no failed retries."""
import hashlib,json,os,subprocess,sys,time,shutil,urllib.error,re,importlib.util
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009');sys.path.insert(0,str(C))
from collectors.tiingo_archive import Archive,collect_one,read_key,request_path,validate_receipt,require_external_root,require_space,TiingoArchiveError
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
RUN='eod-wave15-original-unadmitted-continuation01-20261013-01a12ab6'
EXPECTED_PLAN_SHA='1fcaf8614d1df2ef31c1de353b4056755038a578f95ed2fe389969747b9ceec0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,o):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(o,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 assert os.environ.get('CODEX_THREAD_ID')=='01a12ab6-92cb-7c42-a711-42673ebb6b50'
 plan_path=E/(RUN+'-planned-refresh02.json');assert sha(plan_path)==EXPECTED_PLAN_SHA
 plan=json.loads(plan_path.read_text());assert plan['request_cap']==2631 and plan['max_inflight']==4
 assert subprocess.check_output(['git','-C',str(C),'rev-parse','HEAD'],text=True).strip()==plan['calling_carrier_sha']
 for rel,digest in plan['loaded_source_sha256'].items():assert sha(C/rel)==digest
 assert require_external_root(R)==R;require_space(R,floor=40*1024**3)
 coveragep=E/plan['coverage_file'];assert sha(coveragep)==plan['coverage_sha256']
 for name,digest in plan['failure_evidence_sha256'].items():assert sha(E/name)==digest
 for name,digest in plan['reserved_prior_selection_files_sha256'].items():assert sha(E/name)==digest
 original_scope=E/'eod-wave15-final-unreserved-20261012-01a12ab6-scope.json';original_result=E/'eod-wave15-final-unreserved-20261012-01a12ab6-result.json'
 assert sha(original_scope)=='667cdddc5f468129459fd45040f8fe69e938ed40b8da0766b0cad7a3c929d7b3' and sha(original_result)=='1ef688ee4589509a0bfb21d6515be77d422c28974d0d75174a82112d02b7e03f'
 original_planp=E/'eod-wave15-final-unreserved-20261012-01a12ab6-planned.json';assert sha(original_planp)=='d120cc13ecbb675fa45a67b32697f7f43fa506a9406e62de29f5edafe57abbe9'
 original_plan=json.loads(original_planp.read_text());prior=json.loads(original_result.read_text());settled=True
 assert prior['phase']=='settled' and prior['fatal_exception_type'] is None and not prior['all_selected_captured']
 assert prior['capture']['attempted']==1761 and prior['capture']['ok']==1758 and prior['capture']['failed']==3
 assert {r['symbol'] for r in prior['capture']['errors']}=={'TACI','TACJF','TAER'} and all(r['transport_reason_class']=='TimeoutError' for r in prior['capture']['errors'])
 captureparent=E/'tiingo-wave15-original-capture-actual-terminal-parent-consumption.json';assert sha(captureparent)=='063e448cec92e6231c6d09560fc169b7d83d4baddb92fd9063127ee90c7aed69'
 accounting_path=E/'eod-wave15-original-final-disposition-partition-accounting.json';assert sha(accounting_path)==plan['actual_original_disposition_accounting_sha256'];accounting=json.loads(accounting_path.read_text())
 acceptedp=E/'tiingo-wave15-original-final-disposition-accounting-actual-parent-consumption.json';assert sha(acceptedp)==plan['actual_accounting_parent_consumption_sha256'];accepted=json.loads(acceptedp.read_text())
 assert accepted['actual_original_terminal_return_consumed'] and accepted['original_exit_code']==0 and accepted['actual_accounting_sha256']==sha(accounting_path)
 assert accounting['actual_original_capture_terminal_return_consumed'] and accounting['all_listed_qualification_writer_returns_consumed'] and accounting['all_original_4392_identities_accounted_exactly_once'] and accounting['all_captured_successes_partitioned_between_valid_and_quality']
 assert accounting['actual_original_terminal_parent_sha256']==sha(captureparent) and accounting['successful_requests']==1758 and accounting['never_admitted_count']==2631
 assert len(accounting['held_attempted_failures'])==3 and accounting['prior_failures_retried'] is False
 assert plan['selected']==accounting['never_admitted_requests']
 admitted_indices={r['selection_index'] for r in prior['actual_local_admissions']};assert len(admitted_indices)==1761
 expected=[r for i,r in enumerate(original_plan['selected']) if i not in admitted_indices];assert plan['selected']==expected
 assert plan['raw_budget_bytes']==original_plan['raw_budget_bytes']-prior['capture']['bytes'] and plan['raw_budget_bytes']>0
 for mapping in [accounting['qualification_sha256'],accounting['coverage_sha256'],accounting['actual_disposition_window_parent_sha256']]:
  for name,digest in mapping.items():assert sha(E/name)==digest
 holds=sorted(set(json.loads(original_scope.read_text())['held_symbols_excluded'])|{r['symbol'] for r in accounting['held_attempted_failures']}|{r['symbol'] for r in accounting['quarantined_receipts']})
 assert holds==plan['all_prior_failed_or_quality_symbols_excluded']
 remaining=[];symbols=set();pairs=set()
 for row in plan['selected']:
  params={'startDate':row['request_start'],'endDate':row['request_end']};path=request_path('eod-bars',row['symbol'],params)
  assert path==row['request_path'] and row['symbol'] not in symbols and row['symbol'] not in holds and row['request_start']<=row['request_end']
  symbols.add(row['symbol']);pairs.add((row['symbol'],path));remaining.append({'symbol':row['symbol'],'request_path':path,'params':params})
 assert len(remaining)==len(symbols)==len(pairs)==2631
 assert not symbols&{r['symbol'] for r in prior['all_started_tasks']}
 for p in (R/'receipts/eod-bars').glob('*/*.json'):
  rec=json.loads(p.read_text())
  if rec['symbol'] in symbols:
   validate_receipt(rec);raise AssertionError('Never-admitted continuation overlaps an existing EOD symbol; reconcile its owner')
 module_path=E/'tiingo-finite-admission-reviewed-3d204f2e.py'
 assert sha(module_path)=='3d204f2e7a6ebc5d3693606a7b59b665be8f53546314c0b8053bee2be4154926'
 accepted_path=E/'tiingo-finite-admission-canonical-source-accepted.json'
 if '--preflight' not in sys.argv:
  accepted=json.loads(accepted_path.read_text())
  assert accepted['actual_merged'] and accepted['source_ci_conclusion']=='success' and accepted['independent_review_conclusion']=='PASS'
  assert accepted['module_sha256']==sha(module_path)
 if '--preflight' in sys.argv:
  print(json.dumps({'selected_original_never_admitted_symbols':2631,'source_pins_verified':True,'held_symbols_excluded':len(holds),'existing_eod_symbol_collisions':0,'original_run_settled':settled,'credentials_read':False,'network_requests':0}));return
 quota_path=E/plan['quota_preflight_file'];assert sha(quota_path)==plan['quota_preflight_sha256'];quota=json.loads(quota_path.read_text())
 assert quota['intended_signed_in_account_verified'] and quota['account_username']=='mastermindx6031' and quota['source_url']=='https://www.tiingo.com/account/api/usage' and quota['hourly_requests_remaining']>=10000 and quota['daily_requests_remaining']>=50000 and quota['monthly_gb_remaining']>=60
 assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(quota['observed_at_utc'])).total_seconds()<=900
 out=E/(RUN+'-result.json');assert not out.exists()
 prepared={'schema':'tiingo_new_disjoint_finite_eod_scope/v1','run_id':RUN,'started_at_utc':datetime.now(timezone.utc).isoformat(),'method_sha256':sha(Path(__file__)),'plan_sha256':sha(plan_path),'prior_original_settlement_sha256':sha(original_result),'quota_proof_sha256':sha(quota_path),'request_cap':2631,'held_symbols_excluded':holds,'prior_original_combined_accounting_sha256':sha(accounting_path),'prior_original_4392_success_not_claimed':True,'max_inflight':4,'admission_policy':'rolling local wrapper admissions s_i-s_(i-4)>=5 seconds','minimum_initial_prior_wave_delay_seconds':5,'minimum_rolling_admission_window_seconds':5,'reviewed_module_sha256':sha(module_path),'canonical_module_source_acceptance_sha256':sha(accepted_path),'reviewed_integration_parent_sha256':'5871b796fc640549deb51584c55693ec314634b7d3692548cdc51fe20fe0c942','raw_budget_is_stop_threshold':True,'maximum_already_admitted_raw_overshoot_bytes':4*512*1024**2,'maximum_own_requests_per_hour':2880,'raw_budget_bytes':plan['raw_budget_bytes'],'reserve_gib':35,'inflight_headroom_gib':5,'collector_unchanged':True,'credential_file_unchanged':True,'all_selected_original_never_admitted_requests':True,'complete_attempt_ledger_claimed':False,'stop_first_error_and_settle_already_started_batch':True,'no_new_collector_service_retry_queue_or_publication':True}
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
  assert result.complete==(totals['ok']==2631 and totals['failed']==0 and fatal is None)
 except BaseException as error:fatal=type(error).__name__
 proof={'schema':'tiingo_disjoint_finite_eod_settlement/v1','run_id':RUN,'phase':'settled' if fatal is None else 'same_operation_reconciliation_required','settled_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-started,3),'scope_sha256':sha(E/(RUN+'-scope.json')),'capture':totals,'successful_requests':successes,'all_started_tasks':attempted_tasks,'actual_local_admissions':local_admissions,'stop_reason':stop_reason,'nonadmitted_submissions_are_never_provider_attempts':True,'all_selected_captured':totals['ok']==totals['attempted']==2631 and totals['failed']==0 and fatal is None,'fatal_exception_type':fatal,'prior_failures_retried':False,'research_only':True,'pit_backtest_eligible':False}
 save(out,proof);print(json.dumps({k:v for k,v in proof.items() if k not in ('successful_requests','all_started_tasks')},indent=2),flush=True)
 raise SystemExit(1 if fatal or totals['failed'] else 0)
if __name__=='__main__':main()
