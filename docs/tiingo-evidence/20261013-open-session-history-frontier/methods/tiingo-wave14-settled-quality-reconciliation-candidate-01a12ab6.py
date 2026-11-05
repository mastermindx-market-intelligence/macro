"""Qualify only completed new wave-fourteen responses with the existing producer."""
import hashlib,json,os,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009');sys.path.insert(0,str(C))
from collectors.tiingo_archive import validate_receipt,request_path,require_external_root,require_space
from scripts.tiingo_materialize import verified_raw,materialize_one
from lib.dataos.tiingo_reader import read_research_view
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
RUN='eod-wave14-new-unreserved-20261012-01a12ab6'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 prefix=sys.argv[1];assert prefix=='17'
 out=E/('eod-wave14-prefix'+prefix+'-qualified.json');assert not out.exists()
 diagp=E/'eod-wave14-prefix16-settled-quality-and-partial-custody-diagnosis.json';assert sha(diagp)=='72ed522bf0c81fe29bde3a61078886627f04c0616487870afc5778a72e01e7cf';diag=json.loads(diagp.read_text())
 assert diag['actual_original_window05_return_consumed'] and diag['original_window05_session']==31547 and diag['original_window05_exit_code']==1 and diag['actual_physical_return_consumed'] and diag['physical_session']==40732 and diag['physical_exit_code']==0
 assert diag['remaining_responses']==1570 and diag['partition_counts']['failed_snapshot']==1341 and diag['partition_counts']['later_tail']==229 and diag['partition_counts']['existing_valid_projection']==758
 assert len(diag['offenders'])==1;bad=diag['offenders'][0];assert bad['symbol']=='RBGPF' and not bad['existing_artifact_files']
 assert [(x['market_date'],x['field'],x['value']) for x in bad['invalid_volume_fields']]==[('2017-08-16','volume',-124),('2017-08-16','adjVolume',-114)]
 bindingp=E/'tiingo-current-original-physical-qualification-source-20261012T2336.json';assert sha(bindingp)=='896f3058eab032dcd84e3fe4e5f54f608e4ef36e76b7ed057a1305c350b0788e';binding=json.loads(bindingp.read_text());assert binding['calling_carrier_sha']=='2a08250fe61aa59ad3e1581149f0b93e9d5a17cf'
 for rel,h in binding['sha256'].items():assert sha(C/rel)==h
 for rel,h in diag['retained_partial_artifact_sha256'].items():assert sha(R/rel)==h
 for n,h in diag['accepted_qualification_sha256'].items():assert sha(E/n)==h
 assert not (E/'eod-wave14-prefix16-qualified.json').exists()
 failedp=E/'eod-wave14-prefix16-materialization-scope.json';assert sha(failedp)=='8b09fb2df889e2157f5b631db3f5ed451aef0cce90ef7e7bed77e2bf333c7ba5'
 settledp=E/'eod-wave14-original-unadmitted-continuation01-20261012-01a12ab6-result.json';assert sha(settledp)=='3b10f9f9eae457d850c497f45de4691c09d6ee6b2ac66bae459891a640367cdc';settled=json.loads(settledp.read_text());assert settled['all_selected_captured'] and settled['capture']['ok']==3311 and settled['capture']['failed']==0
 base_path=E/'eod-qualified-catalogue-coverage-wave13-prefix28-delta.json';assert sha(base_path)=='47705a4a900d3b75cb3bfefcfa02bbe00c35010b4e563a30f47fb8c7ac7833a4'
 base=json.loads(base_path.read_text());old=[];proofs={}
 for name,digest in base['accepted_qualification_files'].items():
  p=E/name;assert sha(p)==digest;q=json.loads(p.read_text());assert q.get('all_selected_raw_and_reader_lineage_verified') or (name=='eod-wave6-final-qualified-archive.json' and q['all_eod_raw_and_projection_lineage_verified']);old.extend(r for r in q['receipts'] if r.get('source','eod-bars')=='eod-bars');proofs[name]=digest
 plan_path=E/(RUN+'-planned.json');assert sha(plan_path)=='6ce216888a99b244f18fb76910d5e73a3984eace5f9df7ae3c44270ed5bb4d0a';plan=json.loads(plan_path.read_text())
 run_scope_path=E/(RUN+'-scope.json');assert sha(run_scope_path)=='5a3864bfed6561da598799e3f4eccb7da3c385757e80162027716460baa862cf';scope=json.loads(run_scope_path.read_text())
 assert scope['method_sha256']=='320a8f2e46d1fa9a2655c172fc215a031fbbcde37ea9de504c0ea085dd10bf13' and scope['plan_sha256']==sha(plan_path) and scope['request_cap']==5000
 assert require_external_root(R)==R;require_space(R,floor=40*1024**3)
 for rel,digest in plan['loaded_source_sha256'].items():assert sha(C/rel)==digest
 histories=base['accepted_nonempty_ticker_histories'];bars=base['accepted_distinct_bars']
 for p in sorted(E.glob('eod-wave14-prefix*-qualified.json')):
  q=json.loads(p.read_text());assert q['all_selected_raw_and_reader_lineage_verified'] and q['run_scope_sha256']==sha(run_scope_path)
  old.extend(q['receipts']);proofs[p.name]=sha(p);histories+=q['new_nonempty_histories'];bars+=q['new_disjoint_bars']
 prior_keys={(r['symbol'],r['request_path']) for r in old};ranges={}
 for r in old:
  if r.get('projected_rows',0):ranges.setdefault(r['symbol'],[]).append((r['first_date'],r['last_date']))
 physical_planp=E/('eod-wave14-original-unadmitted-continuation01-20261012-01a12ab6'+'-planned.json');physical_scopep=E/('eod-wave14-original-unadmitted-continuation01-20261012-01a12ab6'+'-scope.json')
 assert sha(physical_planp)=='a584b99f91869de4f9bd234cae53e3374f133359d658b7c1c93e692239785e4d' and sha(physical_scopep)=='d4522213d7a9c26f3dfba38361c2c48cff3cb12773a91e3acf9dd631d0ead31f'
 physical_plan=json.loads(physical_planp.read_text());physical_scope=json.loads(physical_scopep.read_text())
 assert physical_scope['method_sha256']=='289ae8ce2dcb520f0269ea934bb4993c8cfc9c4e231fb5184d9d87ac8d487d67' and physical_scope['plan_sha256']==sha(physical_planp) and physical_scope['request_cap']==3311
 assert sha(E/'eod-wave14-original-partial-qualified-outcome-partition.json')=='ed98a04d034fb267a411a4f8cacef6d01ad30bcdd469b479cc79df58b5410a53'
 partition=json.loads((E/'eod-wave14-original-partial-qualified-outcome-partition.json').read_text());assert physical_plan['selected']==partition['never_admitted_original_requests']
 expected={(r['symbol'],r['request_path']):r for r in physical_plan['selected']};assert len(expected)==3311
 assert not {symbol for symbol,path in expected}&set(physical_scope['held_symbols_excluded'])
 cutoff=settled['settled_at_utc'];selected={}
 for p in (R/'receipts/eod-bars').glob('*/*.json'):
  rec=json.loads(p.read_text());pair=(rec['symbol'],rec['request_path'])
  if pair in expected and pair not in prior_keys and physical_scope['started_at_utc']<=rec['observed_at_utc']<=cutoff:
   assert pair not in selected and rec['symbol'] not in physical_scope['held_symbols_excluded'];selected[pair]=(p,rec,validate_receipt(rec))
 assert len(selected)==1570 and set(selected)=={(r['symbol'],r['request_path']) for r in diag['remaining_receipts']}
 for r in diag['remaining_receipts']:
  pp,rr,ii=selected[(r['symbol'],r['request_path'])];assert sha(pp)==r['receipt_file_sha256'] and rr['raw_sha256']==r['raw_sha256'] and ii==r['receipt_id']
 rejected=selected.pop((bad['symbol'],bad['request_path']));assert rejected[2]==bad['receipt_id'] and rejected[1]['raw_sha256']==bad['raw_sha256']
 for selector in (bad['receipt_id'],bad['raw_sha256']):
  for directory,suffix in [('manifests','.json'),('normalized','.parquet')]:assert not (R/directory/'eod-bars'/bad['observed_at_utc'][:10]/(selector+suffix)).exists()
 assert len(selected)==1569
 save(E/('eod-wave14-prefix'+prefix+'-materialization-scope.json'),{'schema':'tiingo_new_owned_completed_response_snapshot/v1','run_scope_sha256':sha(run_scope_path),'physical_capture_scope_sha256':sha(physical_scopep),'physical_capture_plan_sha256':sha(physical_planp),'snapshot_before_utc':cutoff,'method_sha256':sha(Path(__file__)),'selected_receipts':len(selected),'reused_accepted_proofs':proofs,'new_l1_views_only':True,'raw_writer_may_still_be_running':False,'complete_capture_not_claimed':True,'actual_quality_diagnosis_sha256':sha(diagp),'failed_original_prefix16_snapshot_sha256':sha(failedp),'actual_physical_result_sha256':sha(settledp),'reconciliation_of_exact_remaining_scope':True})
 records=[];statuses=Counter()
 for pair,(p,rec,identity) in sorted(selected.items()):
  original=expected[pair];raw=verified_raw(R,rec);payload=json.loads(raw);assert isinstance(payload,list)
  dates=[r['date'][:10] for r in payload];assert len(dates)==len(set(dates)) and all(original['request_start']<=d<=original['request_end'] for d in dates)
  assert all(not(a<=d<=b) for a,b in ranges.get(pair[0],[]) for d in dates)
  result=materialize_one(R,rec,dry_run=False);statuses[result['status']]+=1
  assert result['status'] in ('WRITTEN','EXISTS','EMPTY_NORMALIZED','REPAIRED_MANIFEST')
  row={'source':'eod-bars','symbol':pair[0],'request_path':pair[1],'receipt_id':identity,'receipt_file':str(p.relative_to(R)),'receipt_file_sha256':sha(p),'raw_sha256':rec['raw_sha256'],'observed_at_utc':rec['observed_at_utc'],'raw_bytes':len(raw),'projected_rows':len(dates),'materialization_status':result['status'],'raw_checksum_verified':True,'requested_window_verified':True,'old_economic_dates_disjoint':True}
  if dates:
   day=rec['observed_at_utc'][:10];selector=identity if (R/'manifests/eod-bars'/day/(identity+'.json')).is_file() else rec['raw_sha256']
   view=read_research_view('eod-bars',day,selector,root=R,max_rows=1000000)
   assert len(view.rows)==len(dates) and {r['market_date'] for r in view.rows}==set(dates)
   assert all(r['source_receipt_id']==identity and r['source_sha256']==rec['raw_sha256'] for r in view.rows)
   row.update(first_date=min(dates),last_date=max(dates),projection_lineage_verified=True,split_events=sum(r['split_factor'] not in (None,1) for r in view.rows),dividend_events=sum(r['dividend_cash'] not in (None,0) for r in view.rows),raw_adjusted_different_dates=sum(r['close_raw']!=r['close_tradj'] for r in view.rows))
  else:row['raw_empty_response_verified']=True
  records.append(row)
 new_symbols={r['symbol'] for r in records if r['projected_rows']>0}-ranges.keys();new_bars=sum(r['projected_rows'] for r in records)
 result={'schema':'tiingo_new_disjoint_completed_response_qualification/v1','settled_at_utc':datetime.now(timezone.utc).isoformat(),'snapshot_before_utc':cutoff,'run_scope_sha256':sha(run_scope_path),'physical_capture_scope_sha256':sha(physical_scopep),'physical_capture_plan_sha256':sha(physical_planp),'base_coverage_sha256':sha(base_path),'method_sha256':sha(Path(__file__)),'selected_receipts':len(records),'receipts':records,'materialization_status_counts':dict(statuses),'all_selected_raw_and_reader_lineage_verified':True,'new_nonempty_histories':len(new_symbols),'new_disjoint_bars':new_bars,'distinct_eod_histories_in_qualified_base_and_prefix':histories+len(new_symbols),'distinct_eod_bars_in_qualified_base_and_prefix':bars+new_bars,'complete_original_capture_proven':False,'whole_wave_fourteen_accepted':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False,'credentials_read':False,'network_requests':0}
 for rel,h in diag['retained_partial_artifact_sha256'].items():assert sha(R/rel)==h
 assert len(records)==1569 and new_bars==3131121
 result.update(source_quality_quarantined_response_count=1,source_quality_quarantine_diagnosis_sha256=sha(diagp),quarantined_receipt_id=bad['receipt_id'],quarantined_raw_sha256=bad['raw_sha256'],quarantined_raw_bytes=bad['raw_bytes'],original_remaining_response_count=1570,failed_original_prefix16_snapshot_sha256=sha(failedp),failed_original_window05_exit_code=1,actual_physical_result_sha256=sha(settledp),existing_partial_projection_count_preserved=758,all_partial_artifact_hashes_unchanged=True,reconciliation_of_exact_remaining_scope=True,whole_invalid_receipt_retained_without_projection=True)
 save(out,result);print(json.dumps({k:v for k,v in result.items() if k!='receipts'},indent=2),flush=True)
if __name__=='__main__':main()
