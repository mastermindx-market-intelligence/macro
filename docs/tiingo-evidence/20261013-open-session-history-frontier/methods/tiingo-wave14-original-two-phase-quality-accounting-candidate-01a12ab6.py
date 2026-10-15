"""Account for 4,998 qualified successes and one retained quality quarantine and the held original failure after actual settlement."""
import hashlib,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo');RUN='eod-wave14-new-unreserved-20261012-01a12ab6';PHASE='eod-wave14-original-unadmitted-continuation01-20261012-01a12ab6';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert os.environ.get('CODEX_THREAD_ID')=='01a12ab6-92cb-7c42-a711-42673ebb6b50'
assert sys.argv[1:]==['--parent-consumed-41115-exit1-and-40732-exit0-and-all-qualifier-returns']
pins={RUN+'-planned.json':'6ce216888a99b244f18fb76910d5e73a3984eace5f9df7ae3c44270ed5bb4d0a',RUN+'-scope.json':'5a3864bfed6561da598799e3f4eccb7da3c385757e80162027716460baa862cf',RUN+'-result.json':'3c339b48e8b6faa028743c7725ab4b835755c8f13bffb16dbc699baf7012620e',PHASE+'-planned.json':'a584b99f91869de4f9bd234cae53e3374f133359d658b7c1c93e692239785e4d',PHASE+'-scope.json':'d4522213d7a9c26f3dfba38361c2c48cff3cb12773a91e3acf9dd631d0ead31f','eod-wave14-original-partial-qualified-outcome-partition.json':'ed98a04d034fb267a411a4f8cacef6d01ad30bcdd469b479cc79df58b5410a53'}
for name,h in pins.items():assert sha(E/name)==h
DIAG=E/'eod-wave14-prefix16-settled-quality-and-partial-custody-diagnosis.json';assert sha(DIAG)=='72ed522bf0c81fe29bde3a61078886627f04c0616487870afc5778a72e01e7cf';diag=json.loads(DIAG.read_text());assert len(diag['offenders'])==1;bad=diag['offenders'][0];assert bad['symbol']=='RBGPF' and bad['rows']==4751 and bad['raw_bytes']==1163554
quality={(bad['symbol'],bad['request_path'])};assert bad['invalid_volume_fields']==[{'market_date':'2017-08-16','field':'volume','value':-124,'python_type':'int','reason':'share volume must be a nonnegative int64'},{'market_date':'2017-08-16','field':'adjVolume','value':-114,'python_type':'int','reason':'share volume must be a nonnegative int64'}]
assert sha(R/bad['receipt_file'])==bad['receipt_file_sha256']
for rel,h in diag['retained_partial_artifact_sha256'].items():assert sha(R/rel)==h
parentp=E/'tiingo-wave14-quality-reconciliation-actual-parent-acceptance.json';parent=json.loads(parentp.read_text());assert parent['original_terminal_return_consumed'] and parent['original_exit_code']==0 and parent['method_sha256']=='cc5cfab5ee198d81b274f940ea89b081bb7e01e90a7b766659c1c458a96985b0'
assert parent['all_qualification_writer_returns_consumed'] and parent['raw_or_projection_rebuilt']==False and parent['actual_diagnosis_sha256']==sha(DIAG)
assert parent['qualification_sha256']==sha(E/'eod-wave14-prefix17-qualified.json') and parent['coverage_sha256']==sha(E/'eod-qualified-catalogue-coverage-wave14-prefix17-delta.json')
assert not (E/'eod-wave14-prefix16-qualified.json').exists()
plan=json.loads((E/(RUN+'-planned.json')).read_text());original=json.loads((E/(RUN+'-result.json')).read_text());scope=json.loads((E/(RUN+'-scope.json')).read_text());phase_plan=json.loads((E/(PHASE+'-planned.json')).read_text());phase_scope=json.loads((E/(PHASE+'-scope.json')).read_text());phasep=E/(PHASE+'-result.json');phase=json.loads(phasep.read_text());partition=json.loads((E/'eod-wave14-original-partial-qualified-outcome-partition.json').read_text())
assert not original['all_selected_captured'] and original['capture']['ok']==1688 and original['capture']['attempted']==1689 and original['capture']['failed']==1
assert original['phase']=='settled' and original['fatal_exception_type'] is None and original['scope_sha256']==pins[RUN+'-scope.json']
assert partition['actual_terminal_return_consumed'] and partition['original_tool_session']==41115 and partition['original_exit_code']==1
assert phase_scope['plan_sha256']==pins[PHASE+'-planned.json'] and phase_scope['method_sha256']=='289ae8ce2dcb520f0269ea934bb4993c8cfc9c4e231fb5184d9d87ac8d487d67'
assert phase['run_id']==PHASE and phase['scope_sha256']==pins[PHASE+'-scope.json'] and phase['phase']=='settled' and phase['fatal_exception_type'] is None
assert phase['all_selected_captured'] and phase['capture']['ok']==phase['capture']['attempted']==3311 and phase['capture']['failed']==0 and not phase['capture']['errors']
assert phase_plan['selected']==partition['never_admitted_original_requests'] and phase_plan['raw_budget_bytes']==25036691707
selected=[(r['symbol'],r['request_path']) for r in plan['selected']];selected_set=set(selected);assert len(selected)==len(selected_set)==5000
started=set();success=set();failure={(r['symbol'],r['request_path']) for r in original['capture']['errors']};assert len(failure)==1 and next(iter(failure))[0]=='MYRUF';trace=[]
for pp,ss,rr,count in [(plan,scope,original,1689),(phase_plan,phase_scope,phase,3311)]:
 pairs=[(r['symbol'],r['request_path']) for r in pp['selected']];admissions=rr['actual_local_admissions'];indices=[r['selection_index'] for r in admissions];tasks=[(r['symbol'],r['request_path']) for r in rr['all_started_tasks']]
 assert len(indices)==len(set(indices))==count and all(0<=i<len(pairs) for i in indices)
 assert tasks==[pairs[i] for i in indices] and not started&set(tasks);started.update(tasks)
 good=[(r['symbol'],r['request_path']) for r in rr['successful_requests']];assert len(good)==len(set(good))==rr['capture']['ok'] and set(good)<=set(tasks) and not success&set(good);success.update(good)
 gaps=[admissions[i]['admitted_monotonic']-admissions[i-4]['admitted_monotonic'] for i in range(4,len(admissions))];assert min(gaps)>=5
 assert ss['started_at_utc']<=rr['settled_at_utc'];trace.append({'run_id':rr['run_id'],'admitted':len(indices),'minimum_four_admission_gap_seconds':min(gaps)})
assert started==selected_set and len(success)==4999 and success.isdisjoint(failure) and success|failure==selected_set
original_pairs={(r['symbol'],r['request_path']) for r in original['successful_requests']};phase_pairs={(r['symbol'],r['request_path']) for r in phase['successful_requests']}
projected=set();qfiles={};cfiles={};rows=raw_bytes=empty=nonempty=0;last_cov=None
for p in sorted(E.glob('eod-wave14-prefix[0-9][0-9]-qualified.json')):
 q=json.loads(p.read_text());assert q['run_scope_sha256']==pins[RUN+'-scope.json'] and q['base_coverage_sha256']=='47705a4a900d3b75cb3bfefcfa02bbe00c35010b4e563a30f47fb8c7ac7833a4' and q['all_selected_raw_and_reader_lineage_verified']
 prefix=int(p.name.split('-prefix')[1][:2]);physical=prefix>=9
 if physical:
  assert prefix in [9,10,11,12,13,14,15,17]
  assert q['method_sha256']==('cc5cfab5ee198d81b274f940ea89b081bb7e01e90a7b766659c1c458a96985b0' if prefix==17 else '070411ac3940d675e3011110a21be6465683823c8413474ce24fd692330df898') and q['physical_capture_scope_sha256']==pins[PHASE+'-scope.json'] and q['physical_capture_plan_sha256']==pins[PHASE+'-planned.json']
  if prefix==17:assert q['source_quality_quarantine_diagnosis_sha256']==sha(DIAG) and q['whole_invalid_receipt_retained_without_projection'] and q['existing_partial_projection_count_preserved']==758 and q['all_partial_artifact_hashes_unchanged']
 else:assert q['method_sha256']=='380aa9abc80da62dda0d738e9fb7058d02827ed3cd7330822b7eed13e6e41048' and partition['qualification_sha256'][p.name]==sha(p)
 own_scope,own_result,own_success=(phase_scope,phase,phase_pairs) if physical else (scope,original,original_pairs)
 assert len(q['receipts'])==q['selected_receipts']
 cp=E/f'eod-qualified-catalogue-coverage-wave14-prefix{prefix:02d}-delta.json';cov=json.loads(cp.read_text());assert cov['accepted_qualification_files'][p.name]==sha(p);qfiles[p.name]=sha(p);cfiles[cp.name]=sha(cp);last_cov=cp
 for row in q['receipts']:
  pair=(row['symbol'],row['request_path']);assert pair in own_success and pair not in projected;projected.add(pair)
  assert row['raw_checksum_verified'] and row['requested_window_verified'] and row['old_economic_dates_disjoint'] and sha(R/row['receipt_file'])==row['receipt_file_sha256']
  assert own_scope['started_at_utc']<=row['observed_at_utc']<=own_result['settled_at_utc']
  if row['projected_rows']>0:assert row['projection_lineage_verified'];nonempty+=1
  else:assert row['projected_rows']==0 and row['raw_empty_response_verified'];empty+=1
  rows+=row['projected_rows'];raw_bytes+=row['raw_bytes']
 assert sum(row['projected_rows'] for row in q['receipts'])==q['new_disjoint_bars']
assert quality<=phase_pairs and projected==success-quality and nonempty+empty==4998 and raw_bytes+bad['raw_bytes']==original['capture']['bytes']+phase['capture']['bytes'] and last_cov is not None
sys.path.insert(0,'/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
from collectors.tiingo_archive import validate_receipt
from scripts.tiingo_materialize import verified_raw
rec=json.loads((R/bad['receipt_file']).read_text());assert validate_receipt(rec)==bad['receipt_id'] and rec['raw_sha256']==bad['raw_sha256'];payload=json.loads(verified_raw(R,rec));assert len(payload)==4751
assert [(r['date'][:10],r.get('volume'),r.get('adjVolume')) for r in payload if r.get('volume',0)<0 or r.get('adjVolume',0)<0]==[('2017-08-16',-124,-114)]
for selector in (bad['receipt_id'],bad['raw_sha256']):
 for directory,suffix in [('manifests','.json'),('normalized','.parquet')]:assert not (R/directory/'eod-bars'/rec['observed_at_utc'][:10]/(selector+suffix)).exists()
proof={'schema':'tiingo.original_two_phase_qualified_outcome_accounting/v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'run_id':RUN,'method_sha256':sha(Path(__file__)),'all_contributing_execution_phases_settled':True,'actual_original_tool_return_consumed':True,'original_tool_session':41115,'original_exit_code':1,'actual_continuation_tool_return_consumed':True,'continuation_tool_session':40732,'continuation_exit_code':0,'all_qualification_writer_returns_consumed':True,'terminal_consumption_facts_supplied_by_actual_assigning_parent':True,'original_plan_sha256':pins[RUN+'-planned.json'],'original_scope_sha256':pins[RUN+'-scope.json'],'actual_original_settlement_sha256':pins[RUN+'-result.json'],'continuation_plan_sha256':pins[PHASE+'-planned.json'],'continuation_scope_sha256':pins[PHASE+'-scope.json'],'actual_continuation_settlement_sha256':sha(phasep),'original_partial_partition_sha256':pins['eod-wave14-original-partial-qualified-outcome-partition.json'],'all_original_5000_identities_accounted_exactly_once':True,'successful_requests':4999,'qualified_successes':4998,'source_quality_quarantined_successes':1,'source_quality_quarantine_diagnosis_sha256':sha(DIAG),'quarantined_receipts':[bad],'all_qualified_successful_request_receipts_and_reader_lineage_verified':True,'all_captured_successes_partitioned_between_qualified_and_quality':True,'actual_reconciliation_parent_acceptance_sha256':sha(parentp),'held_attempted_failures':original['capture']['errors'],'never_admitted':0,'all_successful_request_receipts_and_reader_lineage_verified':False,'initial_all_selected_captured_remains_false':True,'all_5000_success_claimed':False,'prior_failures_retried':False,'qualified_nonempty_responses':nonempty,'qualified_empty_responses':empty,'qualified_disjoint_bars':rows,'raw_bytes':raw_bytes,'quarantined_raw_bytes':bad['raw_bytes'],'all_captured_raw_bytes':raw_bytes+bad['raw_bytes'],'qualification_sha256':qfiles,'coverage_sha256':cfiles,'last_coverage_file':last_cov.name,'last_coverage_sha256':sha(last_cov),'local_admission_trace_by_phase':trace,'raw_or_projection_rebuilt_for_accounting':False,'complete_vendor_history_proven':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False,'provider_requests':0,'credentials_read':False}
out=E/'eod-wave14-original-two-phase-quality-partition-accounting.json'
with os.fdopen(os.open(out,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in proof.items() if k not in ('qualification_sha256','coverage_sha256')}))
