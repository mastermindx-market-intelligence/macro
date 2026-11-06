"""Attended, two-stage whole-receipt disposition; never edits source payloads."""
import hashlib,json,os,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
R=Path('/Volumes/Mastermind/market-data/tiingo')
sys.path.insert(0,str(C))
from collectors.tiingo_archive import validate_receipt,require_external_root,require_space
from scripts.tiingo_materialize import verified_raw,materialize_one
from lib.dataos.tiingo_reader import read_research_view
from lib.dataos.tiingo_views import research_rows,_research_json,receipt_context,_source_symbol,_required_rows,_response_identity,_date,_number,_integer_volume,EOD_FIELDS
RUN='eod-wave15-final-unreserved-20261012-01a12ab6'
BASE='eod-qualified-catalogue-coverage-wave14-prefix17-delta.json'
BASE_SHA='92d68dfc407715a3a85bf44194d9d54c59d069f7c2f8b0b9a492ace9655182e9'
SCOPE_SHA='667cdddc5f468129459fd45040f8fe69e938ed40b8da0766b0cad7a3c929d7b3'
PINS={'tiingo-wave15-actual-prefix01-failure-and-diagnosis.json':'bd0b843372877690a15711a540d0530f31fc48a2d107ec6e417baff771ea4eb3',BASE:BASE_SHA,RUN+'-planned.json':'d120cc13ecbb675fa45a67b32697f7f43fa506a9406e62de29f5edafe57abbe9',RUN+'-scope.json':SCOPE_SHA,'tiingo-current-original-physical-qualification-source-20261012T2336.json':'896f3058eab032dcd84e3fe4e5f54f608e4ef36e76b7ed057a1305c350b0788e','eod-wave15-prefix01-materialization-scope.json':'9755e026856dc0cd81742165838ca05b1dfa7b08d1697ba69f975fbb03ffb1f1','eod-wave15-prefix01-original-quality-and-partial-custody-diagnosis.json':'3bd995522fd3ecf0630e45b63f6f0a593627295f84a3fc0a3eb71c945818e73b'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def load(p):return json.loads(Path(p).read_text())
def save(p,value):
 with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
  json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def name(prefix,suffix):return E/f'eod-wave15-prefix{prefix}-{suffix}.json'
def cov(prefix):return E/f'eod-qualified-catalogue-coverage-wave15-prefix{prefix}-delta.json'
def key(r):return r['symbol'],r['request_path']
def context(prefix=None):
 assert sys.flags.optimize==0
 for n,h in PINS.items():assert sha(E/n)==h
 plan=load(E/(RUN+'-planned.json'));scope=load(E/(RUN+'-scope.json'))
 assert scope['plan_sha256']==PINS[RUN+'-planned.json'] and scope['request_cap']==4392 and scope['method_sha256']=='ae045dcd41ea78e6e5e9d5b7da59d917c59d7c94c250d3b5aacfbac6c431e051'
 binding=load(E/'tiingo-current-original-physical-qualification-source-20261012T2336.json')
 for rel,h in {**plan['loaded_source_sha256'],**binding['sha256']}.items():assert sha(C/rel)==h
 assert require_external_root(R)==R
 expected={key(r):r for r in plan['selected']};assert len(expected)==4392
 assert not {s for s,p in expected}&set(scope['held_symbols_excluded'])
 assert len(scope['held_symbols_excluded'])==24
 assert not name('01','qualified').exists()
 diagnosis_parent=load(E/'tiingo-wave15-actual-prefix01-failure-and-diagnosis.json')
 assert diagnosis_parent['diagnosis_original_terminal_return_consumed'] and diagnosis_parent['diagnosis_original_exit_code']==0 and diagnosis_parent['actual_diagnosis_sha256']==PINS['eod-wave15-prefix01-original-quality-and-partial-custody-diagnosis.json']
 prior=E/BASE if prefix is None or int(prefix)==2 else cov(f'{int(prefix)-1:02d}')
 base=load(prior);old=[];proofs=base['accepted_qualification_files'].copy();seen=set()
 for n,h in proofs.items():
  assert sha(E/n)==h;q=load(E/n)
  if n.startswith('eod-wave15-'):
   assert q['all_completed_response_dispositions_verified'] and q['method_sha256']==sha(__file__) and q['run_scope_sha256']==SCOPE_SHA
   valid={key(r) for r in q['receipts']};bad={key(r) for r in q['quality_quarantines']};assert len(valid)==len(q['receipts']) and len(bad)==len(q['quality_quarantines']) and not valid&bad
   assert not seen&(valid|bad);seen|=valid|bad
  else:assert q.get('all_selected_raw_and_reader_lineage_verified') or (n=='eod-wave6-final-qualified-archive.json' and q['all_eod_raw_and_projection_lineage_verified'])
  old.extend(r for r in q['receipts'] if r.get('source','eod-bars')=='eod-bars')
 # A q without its successfully produced coverage is an unsettled stage, never selectable again.
 for p in E.glob('eod-wave15-prefix*-qualified.json'):
  assert p.name in proofs, 'qualification exists without accepted predecessor coverage'
 ranges={}
 for r in old:
  if r.get('projected_rows',0):ranges.setdefault(r['symbol'],[]).append((r['first_date'],r['last_date']))
 return plan,scope,expected,prior,base,proofs,seen,ranges

def scalar_check(raw,rec,expected,ranges):
 # Use the producer's lossless JSON parser. No modified/shadow payload is created.
 payload=_research_json(raw);receipt_context(rec);sym=_source_symbol(rec)
 assert sym==expected['symbol'];dates=[];date_set=set();invalid=[]
 for item in _required_rows(payload):
  _response_identity(item,sym);d=_date(item.get('date'));assert d not in date_set;date_set.add(d);dates.append(d)
  assert expected['request_start']<=d<=expected['request_end']
  assert all(not(a<=d<=b) for a,b in ranges.get(sym,[]))
  for field in EOD_FIELDS:
   value=item.get(field)
   if field in {'volume','adjVolume'}:
    try:_integer_volume(value)
    except ValueError as err:
     assert type(value) is int and -(2**63)<=value<0 and str(err)=='share volume must be a nonnegative int64', 'quality outside reviewed negative JSON-int policy'
     invalid.append({'market_date':d,'field':field,'value':value,'python_type':'int'})
   else:_number(value)
 if invalid:
  try:research_rows(raw,rec)
  except ValueError as err:assert str(err)=='share volume must be a nonnegative int64'
  else:raise AssertionError('unchanged producer did not reject invalid volume')
 else:
  rows=research_rows(raw,rec);assert isinstance(rows,list) and len(rows)==len(dates)
 return dates,invalid

def artifacts(rec,identity,dates,invalid):
 hashes={};found=[];day=rec['observed_at_utc'][:10]
 for selector in dict.fromkeys([identity,rec['raw_sha256']]):
  mf=R/'manifests/eod-bars'/day/(selector+'.json');pf=R/'normalized/eod-bars'/day/(selector+'.parquet')
  assert mf.exists()==pf.exists(), 'orphan projection requires separate reconciliation'
  if mf.exists():
   assert not invalid and dates,'invalid or empty receipt has an existing projection'
   m=load(mf);assert m['source_receipt_id']==identity and m['source_sha256']==rec['raw_sha256'] and m['output_sha256']==sha(pf)
   view=read_research_view('eod-bars',day,selector,root=R,max_rows=1000000)
   assert len(view.rows)==len(dates) and {r['market_date'] for r in view.rows}==set(dates)
   assert all(r['source_receipt_id']==identity and r['source_sha256']==rec['raw_sha256'] for r in view.rows)
   for p in [mf,pf]:hashes[str(p.relative_to(R))]=sha(p);found.append(str(p.relative_to(R)))
 return hashes,found

def preflight(prefix):
 assert 2<=int(prefix)<=100
 plan,scope,expected,prior,base,proofs,seen,ranges=context(prefix)
 cutoff=load(E/'eod-wave15-prefix01-materialization-scope.json')['snapshot_before_utc'] if prefix=='02' else now()
 selected={}
 for p in (R/'receipts/eod-bars').glob('*/*.json'):
  r=load(p);pair=key(r)
  if pair in expected and pair not in seen and scope['started_at_utc']<=r['observed_at_utc']<=cutoff:
   assert pair not in selected;selected[pair]=(p,r)
 assert selected
 diag=load(E/'eod-wave15-prefix01-original-quality-and-partial-custody-diagnosis.json')
 if prefix=='02':
  assert len(selected)==253 and set(selected)=={key(r) for r in diag['remaining_receipts']}
  diagnosed={key(r):r for r in diag['remaining_receipts']};assert len(diagnosed)==253
  for pair,(p,r) in selected.items():
   d=diagnosed[pair]
   assert str(p.relative_to(R))==d['receipt_file'] and sha(p)==d['receipt_file_sha256']
   assert validate_receipt(r)==d['receipt_id'] and r['raw_sha256']==d['raw_sha256'] and r['observed_at_utc']==d['observed_at_utc']
  assert diag['actual_original_window01_return_consumed'] and diag['original_window01_exit_code']==1
 records=[];partial={}
 for pair,(p,r) in sorted(selected.items()):
  identity=validate_receipt(r);raw=verified_raw(R,r);dates,invalid=scalar_check(raw,r,expected[pair],ranges)
  hashes,found=artifacts(r,identity,dates,invalid);partial.update(hashes)
  records.append({'source':'eod-bars','symbol':pair[0],'request_path':pair[1],'receipt_id':identity,'receipt_file':str(p.relative_to(R)),'receipt_file_sha256':sha(p),'raw_sha256':r['raw_sha256'],'raw_bytes':len(raw),'observed_at_utc':r['observed_at_utc'],'rows':len(dates),'first_date':min(dates) if dates else None,'last_date':max(dates) if dates else None,'disposition':'QUALITY_QUARANTINE' if invalid else 'VALID','invalid_volume_fields':invalid,'existing_artifact_files':found,'raw_checksum_verified':True,'requested_window_verified':True,'old_economic_dates_disjoint':True,'all_other_normalizer_inputs_verified':True})
 if prefix=='02':assert partial==diag['retained_partial_artifact_sha256'] and len(partial)==342
 proof={'schema':'tiingo.completed_snapshot_two_stage_quality_preflight/v1','recorded_at_utc':now(),'prefix':prefix,'method_sha256':sha(__file__),'run_scope_sha256':SCOPE_SHA,'base_coverage_sha256':BASE_SHA,'prior_coverage_file':prior.name,'prior_coverage_sha256':sha(prior),'snapshot_before_utc':cutoff,'input_sha256':PINS,'reused_accepted_proofs':proofs,'selected_responses':len(records),'records':records,'retained_partial_artifact_sha256':partial,'valid_count':sum(r['disposition']=='VALID' for r in records),'quality_count':sum(r['disposition']=='QUALITY_QUARANTINE' for r in records),'all_normalizer_inputs_verified':True,'narrow_negative_json_int_volume_policy':True,'source_payload_modified':False,'archive_writes':0,'provider_requests':0,'credentials_read':False,'capture_settlement_claimed':False}
 save(name(prefix,'disposition-preflight'),proof)
 print(json.dumps({k:v for k,v in proof.items() if k not in {'records','retained_partial_artifact_sha256','reused_accepted_proofs'}}),flush=True)

def qualify(prefix):
 pfpath=name(prefix,'disposition-preflight');pf=load(pfpath);parentpath=name(prefix,'preflight-parent-consumption');parent=load(parentpath)
 assert parent['original_preflight_exit_code']==0 and parent['actual_preflight_return_consumed'] and parent['preflight_sha256']==sha(pfpath) and parent['method_sha256']==sha(__file__)
 assert pf['method_sha256']==sha(__file__) and pf['all_normalizer_inputs_verified'] and pf['input_sha256']==PINS and pf['prefix']==prefix
 plan,scope,expected,prior,base,proofs,seen,ranges=context(prefix)
 assert pf['prior_coverage_file']==prior.name and pf['prior_coverage_sha256']==sha(prior) and pf['reused_accepted_proofs']==proofs
 assert len({key(r) for r in pf['records']})==pf['selected_responses'] and not {key(r) for r in pf['records']}&seen
 assert require_external_root(R)==R;require_space(R,floor=40*1024**3)
 for rel,h in pf['retained_partial_artifact_sha256'].items():assert sha(R/rel)==h
 records=[];quality=[];statuses=Counter()
 for item in pf['records']:
  pair=key(item);p=R/item['receipt_file'];assert sha(p)==item['receipt_file_sha256'];rec=load(p);identity=validate_receipt(rec)
  assert key(rec)==pair and identity==item['receipt_id'] and rec['raw_sha256']==item['raw_sha256'] and rec['observed_at_utc']==item['observed_at_utc']
  assert scope['started_at_utc']<=rec['observed_at_utc']<=pf['snapshot_before_utc']
  raw=verified_raw(R,rec);assert len(raw)==item['raw_bytes'];dates,invalid=scalar_check(raw,rec,expected[pair],ranges)
  assert invalid==item['invalid_volume_fields'] and len(dates)==item['rows'];hashes,found=artifacts(rec,identity,dates,invalid)
  assert found==item['existing_artifact_files'] and all(pf['retained_partial_artifact_sha256'].get(rel)==h for rel,h in hashes.items())
  if invalid:
   assert item['disposition']=='QUALITY_QUARANTINE' and not found
   quality.append({**item,'whole_invalid_receipt_retained_without_projection':True,'provider_retry_authorized':False,'projection_admitted':False});continue
  assert item['disposition']=='VALID'
  result=materialize_one(R,rec,dry_run=False);assert result['status'] in ('WRITTEN','EXISTS','EMPTY_NORMALIZED');statuses[result['status']]+=1
  row={k:v for k,v in item.items() if k not in {'invalid_volume_fields','existing_artifact_files','disposition','rows'}}
  row.update(projected_rows=len(dates),materialization_status=result['status'])
  if dates:
   day=rec['observed_at_utc'][:10];selector=identity if (R/'manifests/eod-bars'/day/(identity+'.json')).exists() else rec['raw_sha256']
   view=read_research_view('eod-bars',day,selector,root=R,max_rows=1000000)
   assert len(view.rows)==len(dates) and {r['market_date'] for r in view.rows}==set(dates) and all(r['source_receipt_id']==identity and r['source_sha256']==rec['raw_sha256'] for r in view.rows)
   row.update(projection_lineage_verified=True,split_events=sum(r['split_factor'] not in (None,1) for r in view.rows),dividend_events=sum(r['dividend_cash'] not in (None,0) for r in view.rows),raw_adjusted_different_dates=sum(r['close_raw']!=r['close_tradj'] for r in view.rows))
  else:row['raw_empty_response_verified']=True
  records.append(row)
 for rel,h in pf['retained_partial_artifact_sha256'].items():assert sha(R/rel)==h
 validkeys={key(r) for r in records};badkeys={key(r) for r in quality};assert not validkeys&badkeys and validkeys|badkeys=={key(r) for r in pf['records']}
 new_symbols={r['symbol'] for r in records if r['projected_rows']}-ranges.keys();bars=sum(r['projected_rows'] for r in records)
 out={'schema':'tiingo.completed_response_valid_qualification_and_whole_quality_disposition/v1','settled_at_utc':now(),'snapshot_before_utc':pf['snapshot_before_utc'],'method_sha256':sha(__file__),'preflight_sha256':sha(pfpath),'actual_preflight_parent_consumption_sha256':sha(parentpath),'run_scope_sha256':SCOPE_SHA,'base_coverage_sha256':BASE_SHA,'prior_coverage_sha256':sha(prior),'selected_receipts':len(records),'completed_response_dispositions':len(records)+len(quality),'receipts':records,'quality_quarantines':quality,'materialization_status_counts':dict(statuses),'all_completed_response_dispositions_verified':True,'all_selected_raw_and_reader_lineage_verified':bool(records),'all_valid_response_lineage_verified':bool(records),'empty_valid_set_not_reader_acceptance':not bool(records),'new_nonempty_histories':len(new_symbols),'new_disjoint_bars':bars,'distinct_eod_histories_in_qualified_base_and_prefix':base['accepted_nonempty_ticker_histories']+len(new_symbols),'distinct_eod_bars_in_qualified_base_and_prefix':base['accepted_distinct_bars']+bars,'all_partial_artifact_hashes_unchanged':True,'source_payload_modified':False,'provider_requests':0,'credentials_read':False,'complete_original_capture_proven':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False}
 save(name(prefix,'qualified'),out);print(json.dumps({k:v for k,v in out.items() if k not in {'receipts','quality_quarantines'}}),flush=True)

def coverage(prefix):
 # The q is now present, so load the exact prior census without treating the q as a prior stage.
 qpath=name(prefix,'qualified');q=load(qpath);prior=E/BASE if prefix=='02' else cov(f'{int(prefix)-1:02d}');base=load(prior)
 assert q['method_sha256']==sha(__file__) and q['run_scope_sha256']==SCOPE_SHA and q['prior_coverage_sha256']==sha(prior) and q['all_completed_response_dispositions_verified']
 pfpath=name(prefix,'disposition-preflight');pf=load(pfpath);assert q['preflight_sha256']==sha(pfpath)
 assert q['completed_response_dispositions']==len(q['receipts'])+len(q['quality_quarantines'])==pf['selected_responses']
 valid={key(r) for r in q['receipts']};bad={key(r) for r in q['quality_quarantines']};assert len(valid)==len(q['receipts']) and len(bad)==len(q['quality_quarantines']) and not valid&bad and valid|bad=={key(r) for r in pf['records']}
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
 save(cov(prefix),base);print(json.dumps({'proof_sha256':sha(cov(prefix)),'valid_responses':count,'new_quality_quarantines':qcount,'histories':base['accepted_nonempty_ticker_histories'],'bars':base['accepted_distinct_bars'],'candidate_status':status}),flush=True)

def progress():
 paths=sorted(E.glob('eod-qualified-catalogue-coverage-wave15-prefix*-delta.json'));prefix=f'{int(paths[-1].name.split("-prefix")[1][:2])+1:02d}' if paths else '02'
 plan,scope,expected,prior,base,proofs,accepted,ranges=context(prefix);seen=set();cutoff=now()
 for p in (R/'receipts/eod-bars').glob('*/*.json'):
  r=load(p);pair=key(r)
  if pair in expected and scope['started_at_utc']<=r['observed_at_utc']<=cutoff:
   validate_receipt(r);assert pair not in seen;seen.add(pair)
 assert accepted<=seen
 result=E/(RUN+'-result.json')
 print(json.dumps({'observed_at_utc':cutoff,'owned_completed_response_receipts':len(seen),'selected_scope':len(expected),'accepted_dispositions':len(accepted),'new_unqualified_responses':len(seen-accepted),'settlement_file_observed':result.exists(),'actual_capture_terminal_return_consumed':False,'provider_requests':0,'credentials_read':False,'next_prefix':prefix}),flush=True)

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='progress':progress()
 else:
  prefix=sys.argv[2];assert prefix==f'{int(prefix):02d}' and 2<=int(prefix)<=100
  {'preflight':preflight,'qualify':qualify,'coverage':coverage}[mode](prefix)
