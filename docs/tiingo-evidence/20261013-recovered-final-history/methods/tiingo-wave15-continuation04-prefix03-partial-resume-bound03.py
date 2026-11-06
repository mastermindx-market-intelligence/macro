"""Continue exact prefix03: reuse accepted536 outputs, materialize missing326 only."""
import os,sys,json,hashlib,importlib.util,ast,stat,tempfile
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from urllib.parse import parse_qs,urlsplit
import pyarrow.parquet as pq
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50';RUN='eod-wave15-original-unadmitted-continuation04-20261013-01a12ab6'
CORE=E/'tiingo-wave15-continuation04-settled-success-prefix03-bound01.py';CORE_SHA='49c3e277752add221fa1a6848cee0ffdea88ed057d224f5859e22c8a09884a64'
INVENTORY_METHOD=E/'tiingo-prefix03-stable-selector-inventory-bound02.py';INVENTORY_METHOD_SHA='74f7320d0a2ccf1cbc13225dfd8345dcb3b85b5ac4c07721b10905fbf41b33c2'
INV=E/'tiingo-prefix03-original91287-stable-selector-and-launch-descriptor-proof.json';INV_SHA='f1b329c4eca28e4fa480cc355d73873879a2c576c8994a2dc219b751b6698c4f'
INVP=E/'tiingo-prefix03-inventory02-actual-root-acceptance.json';INVP_SHA='1b02fc6c1b35b8fd4931e56639521b738ce5526fa9a111f7bd14ee6b6ff98c31'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
now=lambda:datetime.now(timezone.utc).isoformat()
SELF_SHA=sha(__file__)
assert os.environ.get('CODEX_THREAD_ID')==ROOT and sys.flags.optimize==0 and sha(CORE)==CORE_SHA and sha(INVENTORY_METHOD)==INVENTORY_METHOD_SHA
# Reuse only the exact reviewed filesystem primitives, not the inventory's executing main body.
fsdefs=[n for n in ast.parse(INVENTORY_METHOD.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in {'directory_identity','check_ancestors','regular_state','sha'}];assert len(fsdefs)==4
fs={'Path':Path,'os':os,'stat':stat,'hashlib':hashlib};exec(compile(ast.Module(body=fsdefs,type_ignores=[]),str(INVENTORY_METHOD),'exec'),fs)
regular_state=fs['regular_state'];safe_sha=fs['sha'];directory_identity=fs['directory_identity']
spec=importlib.util.spec_from_file_location('accepted_prefix03_core',CORE);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
name=h.name;cov=h.cov;key=h.key;BASE_SHA=h.BASE_SHA;SCOPE_SHA=h.SCOPE_SHA;actual_capture04=h.actual_capture04;prior_coverage=h.prior_coverage
pins={'tiingo-prefix03-original91287-partial-effect-readonly-reconciliation.json':'77b8699971806bc63f839fec280e2ba41d1d3bda669087acfa3c1f293cce7254','tiingo-prefix03-readonly52142-completed-actual-parent-acceptance.json':'86c4b2662826a7df698aea904bed0238259fb346b8b2d3e9af7e349734863c68','eod-wave15-unadmitted-continuation04-prefix03-disposition-preflight.json':'e2b64b983473b4ac16df9626fee8b04fb2630b57786210feb5102172de157bee','eod-wave15-unadmitted-continuation04-prefix03-preflight-parent-consumption.json':'fb2ef7fda589d824ed72d97462278cb554ca09cd1ab9d600e2e5229f28783170'}
def save(p,value):
 fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.control-',dir=str(E))
 with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.link(tmp,p);d=os.open(E,os.O_RDONLY);os.fsync(d);os.close(d);Path(tmp).unlink()
def freeze(mapping):
 for p,hsh in mapping.items():assert safe_sha(Path(p))==hsh

def keep_hash(mapping,path,digest):
 assert path not in mapping or mapping[path]==digest,'Conflicting immutable path hash'
 mapping[path]=digest

def qualify(prefix):
 assert prefix=='03' and regular_state(name(prefix,'qualified'))[0] is None and regular_state(cov(prefix))[0] is None
 assert safe_sha(INV)==INV_SHA and safe_sha(INVP)==INVP_SHA
 inv=load(INV);ip=load(INVP);recon=load(E/'tiingo-prefix03-original91287-partial-effect-readonly-reconciliation.json');accepted=load(E/'tiingo-prefix03-readonly52142-completed-actual-parent-acceptance.json')
 assert inv['method_sha256']==INVENTORY_METHOD_SHA and inv['same_prefix_continuation_stable_footprint_qualified'] is True and inv['unexpected_temporary_artifact_count']==0 and inv['readonly_reconciliation_sha256']==pins['tiingo-prefix03-original91287-partial-effect-readonly-reconciliation.json']
 assert ip['root']==ROOT and ip['actual_inventory_native_exit_code']==0 and ip['actual_inventory_native_terminal_consumed'] is True and ip['inventory_sha256']==INV_SHA
 assert accepted['root']==ROOT and accepted['actual_readonly_native_exit_code']==0 and accepted['actual_readonly_native_terminal_consumed'] is True and accepted['readonly_reconciliation_sha256']==inv['readonly_reconciliation_sha256']
 assert recon['complete_current_projections']==536 and recon['absent_current_projections']==326 and recon['all_existing_current_reader_rows_equal_raw_normalization'] is True and recon['all862_raw_scalar_window_identity_and_success_ledger_bounds_verified'] is True
 assert recon['original_tool_session']==91287 and recon['original_tool_exit_code'] is None and recon['actual_original_terminal_return_consumed'] is False
 for n,digest in pins.items():assert safe_sha(E/n)==digest
 frozen=dict(inv['frozen_input_sha256'])
 for p,digest in [(str(Path(__file__)),SELF_SHA),(str(INV),INV_SHA),(str(INVP),INVP_SHA),(str(INVENTORY_METHOD),INVENTORY_METHOD_SHA)]:assert p not in frozen or frozen[p]==digest;frozen[p]=digest
 freeze(frozen)
 for p,identity in inv['ancestor_directory_identity'].items():assert list(directory_identity(Path(p)))==identity
 for rel,digest in inv['selector_path_state'].items():assert regular_state(R/rel)[0]==digest
 plan,scope,expected,prior,base,proofs,seen,ranges,successful,settled=h.context('03')
 pfpath=name(prefix,'disposition-preflight');pf=load(pfpath);pcpath=name(prefix,'preflight-parent-consumption');pc=load(pcpath)
 assert pf['method_sha256']==pc['method_sha256']==CORE_SHA and pc['actual_preflight_return_consumed'] is True and pc['original_preflight_exit_code']==0 and pc['preflight_sha256']==safe_sha(pfpath)
 assert pf['input_sha256']==h.PINS and pf['prior_coverage_sha256']==safe_sha(prior) and pf['reused_accepted_proofs']==proofs and pf['valid_count']==pf['selected_responses']==862 and pf['quality_count']==0
 snapshot=E/pf['exclusive_unvalidated_snapshot_file'];assert safe_sha(snapshot)==pf['exclusive_unvalidated_snapshot_sha256']
 items={key(r):r for r in pf['records']};footprints={key(r):r for r in recon['footprint']}
 assert len(items)==862 and items.keys()==footprints.keys()==successful-seen and len({r['symbol'] for r in pf['records']})==862
 assert len([r for r in footprints.values() if r['status']=='COMPLETE_RAW_AND_FULL_READER_VERIFIED'])==536
 assert len([r for r in footprints.values() if r['status']=='CURRENT_IDENTITY_PROJECTION_ABSENT'])==326
 assert h.require_external_root(R)==R;h.require_space(R,floor=40*1024**3)
 records=[];statuses=Counter();new_hashes={};raw_hashes={};written=reused=0
 for index,(pair,item) in enumerate(items.items(),1):
  footprint=footprints[pair];rp=R/item['receipt_file'];assert safe_sha(rp)==item['receipt_file_sha256']==footprint['receipt_file_sha256'];rec=load(rp);identity=h.validate_receipt(rec)
  assert key(rec)==pair and identity==item['receipt_id']==footprint['receipt_id'] and rec['raw_sha256']==item['raw_sha256'] and rec['observed_at_utc']==item['observed_at_utc']
  assert pair in successful and scope['started_at_utc']<=rec['observed_at_utc']<=min(pf['snapshot_before_utc'],settled)
  raw=h.verified_raw(R,rec);assert len(raw)==item['raw_bytes'];keep_hash(raw_hashes,rec['raw_path'],safe_sha(R/rec['raw_path']))
  assert item['disposition']=='VALID' and item['invalid_volume_fields']==[] and item['existing_artifact_files']==[]
  row={k:v for k,v in item.items() if k not in {'invalid_volume_fields','existing_artifact_files','disposition','rows'}}
  if footprint['status']=='COMPLETE_RAW_AND_FULL_READER_VERIFIED':
   owned=footprint['current_owned_artifacts'];assert len(owned)==2 and len([x for x in owned if x.startswith('manifests/')])==len([x for x in owned if x.startswith('normalized/')])==1
   for rel in owned:assert safe_sha(R/rel)==footprint['artifact_sha256'][rel]==inv['selector_path_state'][rel]
   mp=R/next(x for x in owned if x.startswith('manifests/'));pp=R/next(x for x in owned if x.startswith('normalized/'));manifest=load(mp)
   assert manifest['source_sha256']==rec['raw_sha256'] and manifest['source_receipt_id']==identity and manifest['source_observed_at_utc']==rec['observed_at_utc'] and manifest['output_path']==str(pp.relative_to(R)) and manifest['output_sha256']==safe_sha(pp) and manifest['rows']==item['rows']
   rows=pq.read_table(pp,columns=['split_factor','dividend_cash','close_raw','close_tradj']).to_pylist();assert len(rows)==item['rows'];status='REUSED_ACCEPTED_INTERRUPTED_OUTPUT';reused+=1
   row['accepted_full_reader_reconciliation_sha256']=inv['readonly_reconciliation_sha256']
  else:
   # These identities had no accepted current projection. The original producer is the only writer.
   dates,invalid=h.scalar_check(raw,rec,expected[pair],ranges);assert invalid==[] and len(dates)==item['rows']
   result=h.materialize_one(R,rec,dry_run=False);assert result['status'] in {'WRITTEN','EMPTY_NORMALIZED'},'Unexpected occupied/repaired output requires same-operation reconciliation';status=result['status'];written+=1
   assert result['rows']==item['rows']
   if dates:
    day=rec['observed_at_utc'][:10];selector=identity if regular_state(R/'manifests/eod-bars'/day/(identity+'.json'))[0] is not None else rec['raw_sha256']
    view=h.read_research_view('eod-bars',day,selector,root=R,max_rows=1000000);rows=list(view.rows)
    assert rows==h.research_rows(raw,rec) and {r['market_date'] for r in rows}==set(dates) and all(r['source_receipt_id']==identity and r['source_sha256']==rec['raw_sha256'] for r in rows)
    pp=R/result['path'];mp=R/'manifests/eod-bars'/day/(pp.stem+'.json');manifest=load(mp);assert manifest['source_receipt_id']==identity and manifest['output_sha256']==safe_sha(pp)
    for p in [mp,pp]:keep_hash(new_hashes,str(p.relative_to(R)),safe_sha(p))
   else:rows=[]
  statuses[status]+=1;row.update(projected_rows=item['rows'],materialization_status=status)
  if rows:row.update(projection_lineage_verified=True,split_events=sum(r['split_factor'] not in (None,1) for r in rows),dividend_events=sum(r['dividend_cash'] not in (None,0) for r in rows),raw_adjusted_different_dates=sum(r['close_raw']!=r['close_tradj'] for r in rows))
  else:row['raw_empty_response_verified']=True
  records.append(row)
  if index%64==0:print(json.dumps({'phase':'same_prefix03_partial_continuation','processed':index,'reused_accepted':reused,'newly_materialized':written,'selected':862}),flush=True)
 assert reused==536 and written==326 and len(records)==862
 assert new_hashes.keys()<=inv['selector_path_state'].keys()
 assert all(inv['selector_path_state'][rel] is None for rel in new_hashes)
 for rel,digest in inv['selector_path_state'].items():
  expected_digest=digest if digest is not None else new_hashes.get(rel)
  assert regular_state(R/rel)[0]==expected_digest,'Unexpected selector publication or changed protected artifact'
 assert not raw_hashes.keys()&new_hashes.keys()
 for rel,digest in {**raw_hashes,**new_hashes}.items():assert safe_sha(R/rel)==digest
 for r in records:assert safe_sha(R/r['receipt_file'])==r['receipt_file_sha256']
 for p,identity in inv['ancestor_directory_identity'].items():assert list(directory_identity(Path(p)))==identity
 freeze(frozen)
 bars=sum(r['projected_rows'] for r in records);new_symbols={r['symbol'] for r in records if r['projected_rows']}-ranges.keys()
 out={'schema':'tiingo.completed_response_valid_qualification_and_whole_quality_disposition/v1','settled_at_utc':now(),'snapshot_before_utc':pf['snapshot_before_utc'],'method_sha256':SELF_SHA,'preflight_method_sha256':CORE_SHA,'preflight_sha256':safe_sha(pfpath),'actual_preflight_parent_consumption_sha256':safe_sha(pcpath),'run_scope_sha256':SCOPE_SHA,'base_coverage_sha256':BASE_SHA,'prior_coverage_sha256':safe_sha(prior),'selected_receipts':862,'completed_response_dispositions':862,'receipts':records,'quality_quarantines':[],'materialization_status_counts':dict(statuses),'all_completed_response_dispositions_verified':True,'all_selected_raw_and_reader_lineage_verified':True,'all_valid_response_lineage_verified':True,'empty_valid_set_not_reader_acceptance':False,'new_nonempty_histories':len(new_symbols),'new_disjoint_bars':bars,'distinct_eod_histories_in_qualified_base_and_prefix':base['accepted_nonempty_ticker_histories']+len(new_symbols),'distinct_eod_bars_in_qualified_base_and_prefix':base['accepted_distinct_bars']+bars,'all_partial_artifact_hashes_unchanged':True,'reused_accepted_interrupted_outputs':reused,'new_materializer_calls':written,'interrupted_original_qualifier_session':91287,'interrupted_original_qualifier_exit_code':None,'interrupted_original_qualifier_terminal_consumed':False,'accepted_reconciliation_sha256':inv['readonly_reconciliation_sha256'],'accepted_reconciliation_actual_root_sha256':pins['tiingo-prefix03-readonly52142-completed-actual-parent-acceptance.json'],'stable_inventory_sha256':INV_SHA,'stable_inventory_actual_root_sha256':INVP_SHA,'source_payload_modified':False,'provider_requests':0,'credentials_read':False,'complete_original_capture_proven':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False}
 save(name(prefix,'qualified'),out);print(json.dumps({k:v for k,v in out.items() if k not in {'receipts','quality_quarantines'}}),flush=True)

def coverage(prefix):
 assert prefix=='03' and regular_state(cov(prefix))[0] is None
 assert safe_sha(INV)==INV_SHA and safe_sha(INVP)==INVP_SHA
 coverage_frozen={str(E/n):digest for n,digest in h.PINS.items()}
 coverage_frozen.update({str(E/n):digest for n,digest in pins.items()})
 coverage_frozen.update({str(CORE):CORE_SHA,str(INVENTORY_METHOD):INVENTORY_METHOD_SHA,str(INV):INV_SHA,str(INVP):INVP_SHA,str(Path(__file__)):SELF_SHA})
 binding=load(E/'tiingo-current-original-physical-qualification-source-20261012T2336.json');plan=load(E/h.PLAN)
 for rel,digest in {**plan['loaded_source_sha256'],**binding['sha256']}.items():keep_hash(coverage_frozen,str(h.C/rel),digest)
 freeze(coverage_frozen)
 # The q is now present, so load the exact prior census without treating the q as a prior stage.
 qpath=name(prefix,'qualified');q=load(qpath);prior=prior_coverage(prefix);base=load(prior);successful,capture_settled=actual_capture04()
 keep_hash(coverage_frozen,str(qpath),safe_sha(qpath));keep_hash(coverage_frozen,str(prior),safe_sha(prior))
 assert q['method_sha256']==sha(__file__) and q['run_scope_sha256']==SCOPE_SHA and q['prior_coverage_sha256']==sha(prior) and q['all_completed_response_dispositions_verified']
 pfpath=name(prefix,'disposition-preflight');pf=load(pfpath);assert q['preflight_sha256']==sha(pfpath)
 assert q['completed_response_dispositions']==len(q['receipts'])+len(q['quality_quarantines'])==pf['selected_responses']
 valid={key(r) for r in q['receipts']};bad={key(r) for r in q['quality_quarantines']};assert len(valid)==len(q['receipts']) and len(bad)==len(q['quality_quarantines']) and not valid&bad and valid|bad=={key(r) for r in pf['records']}
 assert valid|bad<=successful and all(load(E/(RUN+'-scope.json'))['started_at_utc']<=r['observed_at_utc']<=capture_settled for r in q['receipts']+q['quality_quarantines'])
 missing={r['ticker']:r for r in base['missing_request_windows']};histories=empty=bars=0
 for r in q['receipts']:
  assert r['raw_checksum_verified'] and r['old_economic_dates_disjoint'] and sha(R/r['receipt_file'])==r['receipt_file_sha256']
  candidate=missing.pop(r['symbol']);params=parse_qs(urlsplit(r['request_path']).query)
  assert candidate['missing_request_windows']==[[params['startDate'][0],params['endDate'][0]]]
  bars+=r['projected_rows']
  if r['projected_rows']:
   assert r['projection_lineage_verified'];histories+=1;ex=candidate['exchange'];base['nonempty_candidates_by_exchange'][ex]=base['nonempty_candidates_by_exchange'].get(ex,0)+1
  else:assert r['raw_empty_response_verified'];empty+=1
 existing=base['additional_source_quality_quarantines'];ids={r['receipt_id'] for r in existing}|{base['source_quality_quarantine']['receipt_id']}
 for r in q['quality_quarantines']:
  assert r['whole_invalid_receipt_retained_without_projection'] and r['all_other_normalizer_inputs_verified'] and not r['projection_admitted'] and r['receipt_id'] not in ids
  assert r['symbol'] in missing and sha(R/r['receipt_file'])==r['receipt_file_sha256']
  params=parse_qs(urlsplit(r['request_path']).query);assert missing[r['symbol']]['missing_request_windows']==[[params['startDate'][0],params['endDate'][0]]]
  for selector in [r['receipt_id'],r['raw_sha256']]:
   for directory,suffix in [('manifests','.json'),('normalized','.parquet')]:assert not (R/directory/'eod-bars'/r['observed_at_utc'][:10]/(selector+suffix)).exists()
  existing.append({k:r[k] for k in ['symbol','receipt_id','raw_sha256'] }|{'diagnosis_sha256':sha(pfpath),'raw_retained':True,'projection_admitted':False,'provider_retry_authorized':False});ids.add(r['receipt_id'])
 count=len(valid);qcount=len(bad);base['accepted_nonempty_ticker_histories']+=histories;base['accepted_distinct_bars']+=bars;base['projected_rows_across_receipts']+=bars;base['accepted_receipts']+=count
 assert base['accepted_nonempty_ticker_histories']==q['distinct_eod_histories_in_qualified_base_and_prefix'] and base['accepted_distinct_bars']==q['distinct_eod_bars_in_qualified_base_and_prefix']
 status=base['candidate_capture_status_counts'];status['NONEMPTY_DESIRED_REQUEST_WINDOWS_CAPTURED']+=histories;status['CAPTURED_EMPTY_RESPONSE']+=empty;status['UNCAPTURED_CATALOGUE_WINDOW']-=count+qcount;status['CAPTURED_SOURCE_QUALITY_QUARANTINED']+=qcount
 assert status['CAPTURED_SOURCE_QUALITY_QUARANTINED']==len(ids) and len(missing)==status['UNCAPTURED_CATALOGUE_WINDOW']+status['CAPTURED_SOURCE_QUALITY_QUARANTINED'] and sum(status.values())==47689
 base['accepted_qualification_files'][qpath.name]=sha(qpath)
 base.update(observed_at_utc=now(),prior_census_sha256=sha(prior),incremental_delta_qualification_sha256={qpath.name:sha(qpath)},method_sha256=sha(__file__),missing_candidate_count=len(missing),missing_request_windows=list(missing.values()),all_own_raw_operations_settled=False,complete_vendor_history_proven=False)
 freeze(coverage_frozen)
 save(cov(prefix),base);print(json.dumps({'proof_sha256':sha(cov(prefix)),'valid_responses':count,'new_quality_quarantines':qcount,'histories':base['accepted_nonempty_ticker_histories'],'bars':base['accepted_distinct_bars'],'candidate_status':status}),flush=True)

if __name__=='__main__':
 assert len(sys.argv)==3 and sys.argv[2]=='03' and sys.argv[1] in {'qualify','coverage'}
 {'qualify':qualify,'coverage':coverage}[sys.argv[1]]('03')
