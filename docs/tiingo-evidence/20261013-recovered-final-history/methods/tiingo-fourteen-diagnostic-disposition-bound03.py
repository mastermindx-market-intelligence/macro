"""Qualify fourteen separately reviewed later diagnostic successes; preserve original failures."""
import os,sys,json,hashlib,ast,stat,tempfile,importlib.util
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import parse_qs,urlsplit
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo');C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50';RUN='eod-fourteen-settled-transport-later-diagnostic01-20261014-01a12ab6'
CORE=E/'tiingo-wave15-continuation04-settled-success-prefix03-bound01.py';CORE_SHA='49c3e277752add221fa1a6848cee0ffdea88ed057d224f5859e22c8a09884a64'
FS=E/'tiingo-prefix03-stable-selector-inventory-bound02.py';FS_SHA='74f7320d0a2ccf1cbc13225dfd8345dcb3b85b5ac4c07721b10905fbf41b33c2'
Q04='eod-eleven-strict-timeout-later-repair-prefix01-qualified.json';Q04_SHA='085c4147fc7e24579869398955a01242f5da6e6cdc2c3bb314dea9cbeabdf26e'
BASE='eod-qualified-current-census-after-eleven-later-repair01.json';BASE_SHA='c54a2c3c070d14c2a98ad5bd874de919e1704d177bcf0723ed203af67d03ea96'
P04='tiingo-eleven-later-repair-actual-final-parent-consumption.json';P04_SHA='d9e6b93445b5ade0fb8295e47ef6c2d2a878ff7f5e979184aec5122685411561'
Q04_METHOD='58b408064550e95966618e8f482761cf8dbae115e0c4a13b46b64dd86e438a61'
PLAN=RUN+'-planned01.json';SCOPE_SHA='37eba6b7326041799ef306f377eaa9d027c9ed7b4474d0055039cbae51e8c30f'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text());now=lambda:datetime.now(timezone.utc).isoformat()
PREVIOUS=E/'tiingo-eleven-strict-timeout-later-repair-disposition-bound01.py';assert sha(PREVIOUS)==Q04_METHOD
prevspec=importlib.util.spec_from_file_location('accepted_qa05_context_for_repair',PREVIOUS);prev=importlib.util.module_from_spec(prevspec);prevspec.loader.exec_module(prev)
SELF_SHA=sha(__file__);assert os.environ.get('CODEX_THREAD_ID')==ROOT and sys.flags.optimize==0 and sha(CORE)==CORE_SHA and sha(FS)==FS_SHA
spec=importlib.util.spec_from_file_location('immutable_qa04_primitives',CORE);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for n in ['validate_receipt','require_external_root','require_space','verified_raw','materialize_one','read_research_view','research_rows','_research_json','receipt_context','_source_symbol','_required_rows','_response_identity','_date','_number','_integer_volume','EOD_FIELDS']:globals()[n]=getattr(h,n)
fsdefs=[n for n in ast.parse(FS.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in {'directory_identity','check_ancestors','regular_state','sha'}];assert len(fsdefs)==4
fs={'Path':Path,'os':os,'stat':stat,'hashlib':hashlib};exec(compile(ast.Module(body=fsdefs,type_ignores=[]),str(FS),'exec'),fs);regular_state=fs['regular_state'];safe_sha=fs['sha'];directory_identity=fs['directory_identity']
PINS={PLAN:'0ff1630cf6497d3ef2114509e0b6d4f06d93f94e27a9da258b1d55acd9b99ebb',RUN+'-scope.json':SCOPE_SHA,RUN+'-result.json':'6a58cb292c0e70108eb52b5020ce9608e7b6e913cb28b5593fe30d515bc25a60','tiingo-fourteen-diagnostic-capture-actual-parent-consumption.json':'f30f3579d44dec5a97fc710d528a02f9766c51e9174d783c42bfe6091809c0b3','tiingo-current-original-physical-qualification-source-20261012T2336.json':'896f3058eab032dcd84e3fe4e5f54f608e4ef36e76b7ed057a1305c350b0788e',Q04:Q04_SHA,BASE:BASE_SHA,P04:P04_SHA}
PINS['tiingo-fourteen-preflight01-actual-failure-and-day-directory-remedy01.json']='eacacc40f8d11145cb6c49139cfb8509b2c32b5d9bfc564d702f1137556e9249'
ACCEPTED_ROWS={}
def key(r):return r['symbol'],r['request_path']
def name(prefix,suffix):
 assert prefix=='01'
 attempt='02' if suffix in {'materialization-scope','disposition-preflight','preflight-parent-consumption'} else ''
 return E/f'eod-fourteen-settled-transport-later-diagnostic-prefix{prefix}-{suffix}{attempt}.json'
def cov(prefix):assert prefix=='01';return E/f'eod-qualified-catalogue-coverage-fourteen-settled-transport-later-diagnostic-prefix{prefix}-delta.json'
def prior_coverage(prefix=None):assert prefix in {None,'01'} and safe_sha(E/BASE)==BASE_SHA;return E/BASE
def save(p,value):
 fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.control-',dir=str(E))
 with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.link(tmp,p);d=os.open(E,os.O_RDONLY);os.fsync(d);os.close(d);Path(tmp).unlink()
def keep_hash(mapping,path,digest):
 assert path not in mapping or mapping[path]==digest,'Conflicting immutable path hash'
 mapping[path]=digest
def selector_state(rec,identity):
 states={};day=rec['observed_at_utc'][:10]
 for selector in dict.fromkeys([identity,rec['raw_sha256']]):
  for directory,suffix in [('manifests','.json'),('normalized','.parquet')]:
   rel=f'{directory}/eod-bars/{day}/{selector}{suffix}';states[rel]=regular_state(R/rel)[0]
 return states
def freeze(mapping):
 for p,digest in mapping.items():assert safe_sha(Path(p))==digest

def actual_capture04():
 # Compatibility name for the reused coverage primitive: this gate validates the separate fourteen-window diagnostic only.
 for n,digest in PINS.items():assert safe_sha(E/n)==digest
 r=load(E/(RUN+'-result.json'));p=load(E/'tiingo-fourteen-diagnostic-capture-actual-parent-consumption.json')
 assert p['root']==ROOT and p['original_tool_session']==83517 and p['original_exit_code']==0 and p['actual_original_terminal_return_consumed'] is True and p['actual_result_sha256']==PINS[RUN+'-result.json']
 assert r['run_id']==RUN and r['scope_sha256']==SCOPE_SHA and r['phase']=='settled' and r['fatal_exception_type'] is None and r['capture']['attempted']==r['capture']['ok']==r['capture']['new']==14 and r['capture']['failed']==0 and r['all_selected_captured'] is True
 assert r['prior_failures_retried'] is True and r['actual_admission_ledger_available'] is True and r['maximum_additional_attempts_per_request']==1 and r['automatic_successor_repair'] is False
 successful={key(v) for v in r['successful_requests']};assert len(successful)==14
 return successful,r['settled_at_utc']

def source_freeze():
 frozen=prev.source_freeze();frozen={p:digest for p,digest in frozen.items() if p!=str(PREVIOUS)}
 for n,digest in {**h.PINS,**prev.PINS,**PINS}.items():keep_hash(frozen,str(E/n),digest)
 keep_hash(frozen,str(PREVIOUS),Q04_METHOD);frozen.update({str(CORE):CORE_SHA,str(FS):FS_SHA,str(Path(__file__)):SELF_SHA})
 binding=load(E/'tiingo-current-original-physical-qualification-source-20261012T2336.json');plan=load(E/PLAN)
 for rel,digest in {**plan['loaded_source_sha256'],**binding['sha256']}.items():keep_hash(frozen,str(C/rel),digest)
 freeze(frozen);return frozen

def context(prefix=None):
 assert prefix in {None,'01'};source_freeze();prev.context('01');plan=load(E/PLAN);scope=load(E/(RUN+'-scope.json'));successful,settled=actual_capture04()
 assert scope['root']==ROOT and scope['plan_sha256']==PINS[PLAN] and scope['request_cap']==14 and scope['method_sha256']=='da26100f39e78fd35f842ab62032444b9c490f662b83a94b7f6525e622bf4c7f' and scope['maximum_additional_attempts_per_request']==1 and scope['automatic_next_repair'] is False
 expected={key(r):r for r in plan['selected']};assert len(expected)==14 and expected.keys()==successful and all(r['original_classification'] in ['GENERIC_URLERROR_CAUSE_UNRETAINED_HOLD','PROVEN_ORDINARY_TIMEOUT_CANDIDATE_FOR_BOUNDED_LATER_REPAIR'] and r['maximum_additional_attempts']==1 for r in expected.values())
 prior=prior_coverage(prefix);base=load(prior);parent=load(E/P04);q04=load(E/Q04)
 assert parent['schema']=='tiingo.later_repair_actual_parent_consumption_and_conservation/v1' and parent['root']==ROOT and parent['all_this_repair_pipeline_returns_consumed'] is True and parent['current_census_sha256']==BASE_SHA and parent['qualified_successes']==11 and parent['failed_requests']==parent['never_admitted']==0
 assert q04['method_sha256']==Q04_METHOD and q04['all_completed_response_dispositions_verified'] is True and base['accepted_qualification_files'][Q04]==Q04_SHA
 assert base['accepted_nonempty_ticker_histories']==47550 and base['accepted_distinct_bars']==100592522
 proofs=base['accepted_qualification_files'].copy();ranges={};ACCEPTED_ROWS.clear()
 for n,digest in proofs.items():
  assert safe_sha(E/n)==digest;q=load(E/n);valid=q['receipts'];bad=q.get('quality_quarantines',[])
  assert q.get('all_selected_raw_and_reader_lineage_verified') or (n=='eod-wave6-final-qualified-archive.json' and q['all_eod_raw_and_projection_lineage_verified'])
  assert not ({key(r) for r in valid}|{key(r) for r in bad})&successful
  for row in valid:
   if row.get('source','eod-bars')!='eod-bars':continue
   ACCEPTED_ROWS.setdefault(row['receipt_id'],[]).append((n,digest,row))
   if row.get('projected_rows',0):ranges.setdefault(row['symbol'],[]).append((row['first_date'],row['last_date']))
 missing={r['ticker']:r for r in base['missing_request_windows']}
 for (symbol,path),item in expected.items():assert missing[symbol]['missing_request_windows']==[[item['request_start'],item['request_end']]]
 assert require_external_root(R)==R
 return plan,scope,expected,prior,base,proofs,set(),ranges,successful,settled

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
  if not mf.exists():continue
  assert not invalid and dates,'invalid or empty receipt has an occupied selector'
  m=load(mf);assert m['source_sha256']==rec['raw_sha256'] and m['output_sha256']==sha(pf) and m['output_path']==str(pf.relative_to(R))
  foreign=m['source_receipt_id']!=identity
  if foreign:
   assert selector==rec['raw_sha256'], 'foreign owner at current identity selector'
   matches=[(n,h,r) for n,h,r in ACCEPTED_ROWS.get(m['source_receipt_id'],[]) if r['raw_sha256']==rec['raw_sha256'] and r['observed_at_utc']==m['source_observed_at_utc']]
   assert matches,'foreign content path lacks exact accepted predecessor owner'
   n,h,prior=matches[0];assert sha(E/n)==h and sha(R/prior['receipt_file'])==prior['receipt_file_sha256']
   prior_rec=load(R/prior['receipt_file']);assert validate_receipt(prior_rec)==prior['receipt_id'] and prior_rec['raw_sha256']==rec['raw_sha256']
   assert prior_rec['observed_at_utc']==m['source_observed_at_utc'] and key(prior_rec)==key(prior)
   view=read_research_view('eod-bars',day,prior['receipt_id'],root=R,max_rows=1000000)
   assert len(view.rows)==prior['projected_rows'] and all(r['source_receipt_id']==prior['receipt_id'] and r['source_sha256']==rec['raw_sha256'] for r in view.rows)
   # Foreign bytes are protected custody, never credited to the current receipt.
  else:
   assert m['source_observed_at_utc']==rec['observed_at_utc']
   view=read_research_view('eod-bars',day,identity,root=R,max_rows=1000000)
   assert len(view.rows)==len(dates) and {r['market_date'] for r in view.rows}==set(dates)
   assert all(r['source_receipt_id']==identity and r['source_sha256']==rec['raw_sha256'] for r in view.rows)
   found.extend(str(p.relative_to(R)) for p in [mf,pf])
  for p in [mf,pf]:hashes[str(p.relative_to(R))]=sha(p)
 return hashes,found

def preflight(prefix):
 assert prefix=='01' and regular_state(name(prefix,'disposition-preflight'))[0] is None and regular_state(name(prefix,'materialization-scope'))[0] is None
 frozen_source=source_freeze()
 plan,scope,expected,prior,base,proofs,seen,ranges,successful,capture_settled=context(prefix)
 cutoff=now()
 selected={}
 for p in (R/'receipts/eod-bars').glob('*/*.json'):
  r=load(p);pair=key(r)
  if pair in expected and pair in successful and pair not in seen and scope['started_at_utc']<=r['observed_at_utc']<=min(cutoff,capture_settled):
   assert pair not in selected;selected[pair]=(p,r)
 assert set(selected)==successful-seen and len(selected)==14
 snapshot_path=name(prefix,'materialization-scope')
 selection=[{'symbol':r['symbol'],'request_path':r['request_path'],'receipt_file':str(p.relative_to(R)),'receipt_file_sha256':sha(p),'receipt_id':validate_receipt(r),'raw_sha256':r['raw_sha256'],'observed_at_utc':r['observed_at_utc']} for pair,(p,r) in sorted(selected.items())]
 save(snapshot_path,{'schema':'tiingo.exact_owned_selection_before_disposition_validation/v1','method_sha256':sha(__file__),'cutoff_utc':cutoff,'selected_receipts':selection,'prior_coverage_sha256':sha(prior),'run_scope_sha256':SCOPE_SHA,'selected_count':len(selection),'preflight_acceptance_claimed':False,'normalization_or_artifact_validation_completed':False,'archive_writer_started':False,'archive_writes':0,'provider_requests':0})
 records=[];partial={};slots={};directories={};raw_hashes={}
 for pair,(p,r) in sorted(selected.items()):
  identity=validate_receipt(r);raw=verified_raw(R,r);dates,invalid=scalar_check(raw,r,expected[pair],ranges)
  hashes,found=artifacts(r,identity,dates,invalid);assert not found,'Unexpected current projection requires same-owner reconciliation'
  for rel,digest in hashes.items():keep_hash(partial,rel,digest)
  for rel,digest in selector_state(r,identity).items():
   if rel in slots:assert slots[rel]==digest
   slots[rel]=digest;directory=R/Path(rel).parent;directories[str(directory)]=list(directory_identity(directory))
  keep_hash(raw_hashes,r['raw_path'],safe_sha(R/r['raw_path']))
  records.append({'source':'eod-bars','symbol':pair[0],'request_path':pair[1],'receipt_id':identity,'receipt_file':str(p.relative_to(R)),'receipt_file_sha256':sha(p),'raw_sha256':r['raw_sha256'],'raw_bytes':len(raw),'observed_at_utc':r['observed_at_utc'],'rows':len(dates),'first_date':min(dates) if dates else None,'last_date':max(dates) if dates else None,'disposition':'QUALITY_QUARANTINE' if invalid else 'VALID','invalid_volume_fields':invalid,'existing_artifact_files':found,'raw_checksum_verified':True,'requested_window_verified':True,'old_economic_dates_disjoint':True,'all_other_normalizer_inputs_verified':True})
 proof={'schema':'tiingo.completed_snapshot_two_stage_quality_preflight/v1','recorded_at_utc':now(),'prefix':prefix,'method_sha256':sha(__file__),'run_scope_sha256':SCOPE_SHA,'base_coverage_sha256':BASE_SHA,'exclusive_unvalidated_snapshot_sha256':sha(snapshot_path),'exclusive_unvalidated_snapshot_file':snapshot_path.name,'prior_coverage_file':prior.name,'prior_coverage_sha256':sha(prior),'snapshot_before_utc':cutoff,'input_sha256':PINS,'reused_accepted_proofs':proofs,'selected_responses':len(records),'records':records,'retained_partial_artifact_sha256':partial,'selector_path_state':slots,'ancestor_directory_identity':directories,'raw_compressed_path_sha256':raw_hashes,'valid_count':sum(r['disposition']=='VALID' for r in records),'quality_count':sum(r['disposition']=='QUALITY_QUARANTINE' for r in records),'all_normalizer_inputs_verified':True,'narrow_negative_json_int_volume_policy':True,'source_payload_modified':False,'archive_writes':0,'provider_requests':0,'credentials_read':False,'capture_settlement_claimed':False}
 for rel,digest in slots.items():assert regular_state(R/rel)[0]==digest
 for directory,identity in directories.items():assert list(directory_identity(Path(directory)))==identity
 for rel,digest in raw_hashes.items():assert safe_sha(R/rel)==digest
 freeze(frozen_source)
 save(name(prefix,'disposition-preflight'),proof)
 print(json.dumps({k:v for k,v in proof.items() if k not in {'records','retained_partial_artifact_sha256','reused_accepted_proofs'}}),flush=True)

def qualify(prefix):
 assert prefix=='01' and regular_state(name(prefix,'qualified'))[0] is None
 frozen_source=source_freeze()
 pfpath=name(prefix,'disposition-preflight');pf=load(pfpath);parentpath=name(prefix,'preflight-parent-consumption');parent=load(parentpath)
 assert parent['original_preflight_exit_code']==0 and parent['actual_preflight_return_consumed'] and parent['preflight_sha256']==sha(pfpath) and parent['method_sha256']==sha(__file__)
 assert pf['method_sha256']==sha(__file__) and pf['all_normalizer_inputs_verified'] and pf['input_sha256']==PINS and pf['prefix']==prefix
 plan,scope,expected,prior,base,proofs,seen,ranges,successful,capture_settled=context(prefix)
 assert sha(E/pf['exclusive_unvalidated_snapshot_file'])==pf['exclusive_unvalidated_snapshot_sha256']
 frozen=load(E/pf['exclusive_unvalidated_snapshot_file']);assert frozen['cutoff_utc']==pf['snapshot_before_utc'] and frozen['method_sha256']==sha(__file__)
 assert {key(r) for r in frozen['selected_receipts']}=={key(r) for r in pf['records']}
 assert pf['prior_coverage_file']==prior.name and pf['prior_coverage_sha256']==sha(prior) and pf['reused_accepted_proofs']==proofs
 assert len({key(r) for r in pf['records']})==pf['selected_responses'] and not {key(r) for r in pf['records']}&seen
 assert require_external_root(R)==R;require_space(R,floor=40*1024**3)
 for rel,h in pf['retained_partial_artifact_sha256'].items():assert sha(R/rel)==h
 for rel,digest in pf['selector_path_state'].items():assert regular_state(R/rel)[0]==digest
 for directory,identity in pf['ancestor_directory_identity'].items():assert list(directory_identity(Path(directory)))==identity
 records=[];quality=[];statuses=Counter();new_hashes={}
 for item in pf['records']:
  pair=key(item);p=R/item['receipt_file'];assert sha(p)==item['receipt_file_sha256'];rec=load(p);identity=validate_receipt(rec)
  assert key(rec)==pair and identity==item['receipt_id'] and rec['raw_sha256']==item['raw_sha256'] and rec['observed_at_utc']==item['observed_at_utc']
  assert pair in successful and scope['started_at_utc']<=rec['observed_at_utc']<=min(pf['snapshot_before_utc'],capture_settled)
  raw=verified_raw(R,rec);assert len(raw)==item['raw_bytes'];dates,invalid=scalar_check(raw,rec,expected[pair],ranges)
  assert invalid==item['invalid_volume_fields'] and len(dates)==item['rows'];hashes,found=artifacts(rec,identity,dates,invalid)
  assert found==item['existing_artifact_files'] and all(pf['retained_partial_artifact_sha256'].get(rel)==h for rel,h in hashes.items())
  if invalid:
   assert item['disposition']=='QUALITY_QUARANTINE' and not found
   quality.append({**item,'whole_invalid_receipt_retained_without_projection':True,'provider_retry_authorized':False,'projection_admitted':False});continue
  assert item['disposition']=='VALID'
  result=materialize_one(R,rec,dry_run=False);assert result['status'] in ('WRITTEN','EMPTY_NORMALIZED');statuses[result['status']]+=1
  row={k:v for k,v in item.items() if k not in {'invalid_volume_fields','existing_artifact_files','disposition','rows'}}
  row.update(projected_rows=len(dates),materialization_status=result['status'])
  if dates:
   day=rec['observed_at_utc'][:10];selector=identity if (R/'manifests/eod-bars'/day/(identity+'.json')).exists() else rec['raw_sha256']
   view=read_research_view('eod-bars',day,selector,root=R,max_rows=1000000)
   assert list(view.rows)==research_rows(raw,rec) and len(view.rows)==len(dates) and {r['market_date'] for r in view.rows}==set(dates) and all(r['source_receipt_id']==identity and r['source_sha256']==rec['raw_sha256'] for r in view.rows)
   pp=R/result['path'];mp=R/'manifests/eod-bars'/day/(pp.stem+'.json');m=load(mp);assert m['source_receipt_id']==identity and m['output_sha256']==safe_sha(pp)
   for path in [pp,mp]:keep_hash(new_hashes,str(path.relative_to(R)),safe_sha(path))
   row.update(projection_lineage_verified=True,split_events=sum(r['split_factor'] not in (None,1) for r in view.rows),dividend_events=sum(r['dividend_cash'] not in (None,0) for r in view.rows),raw_adjusted_different_dates=sum(r['close_raw']!=r['close_tradj'] for r in view.rows))
  else:row['raw_empty_response_verified']=True
  records.append(row)
 assert new_hashes.keys()<=pf['selector_path_state'].keys() and all(pf['selector_path_state'][rel] is None for rel in new_hashes)
 for rel,digest in pf['selector_path_state'].items():assert regular_state(R/rel)[0]==(digest if digest is not None else new_hashes.get(rel))
 for rel,digest in pf['raw_compressed_path_sha256'].items():assert safe_sha(R/rel)==digest
 for directory,identity in pf['ancestor_directory_identity'].items():assert list(directory_identity(Path(directory)))==identity
 for row in records+quality:assert safe_sha(R/row['receipt_file'])==row['receipt_file_sha256']
 for rel,h in pf['retained_partial_artifact_sha256'].items():assert sha(R/rel)==h
 validkeys={key(r) for r in records};badkeys={key(r) for r in quality};assert not validkeys&badkeys and validkeys|badkeys=={key(r) for r in pf['records']}
 new_symbols={r['symbol'] for r in records if r['projected_rows']}-ranges.keys();bars=sum(r['projected_rows'] for r in records)
 out={'schema':'tiingo.completed_response_valid_qualification_and_whole_quality_disposition/v1','settled_at_utc':now(),'snapshot_before_utc':pf['snapshot_before_utc'],'method_sha256':sha(__file__),'preflight_sha256':sha(pfpath),'actual_preflight_parent_consumption_sha256':sha(parentpath),'run_scope_sha256':SCOPE_SHA,'base_coverage_sha256':BASE_SHA,'prior_coverage_sha256':sha(prior),'selected_receipts':len(records),'completed_response_dispositions':len(records)+len(quality),'receipts':records,'quality_quarantines':quality,'materialization_status_counts':dict(statuses),'all_completed_response_dispositions_verified':True,'all_selected_raw_and_reader_lineage_verified':bool(records),'all_valid_response_lineage_verified':bool(records),'empty_valid_set_not_reader_acceptance':not bool(records),'new_nonempty_histories':len(new_symbols),'new_disjoint_bars':bars,'distinct_eod_histories_in_qualified_base_and_prefix':base['accepted_nonempty_ticker_histories']+len(new_symbols),'distinct_eod_bars_in_qualified_base_and_prefix':base['accepted_distinct_bars']+bars,'all_partial_artifact_hashes_unchanged':True,'source_payload_modified':False,'provider_requests':0,'credentials_read':False,'complete_original_capture_proven':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False}
 freeze(frozen_source)
 save(name(prefix,'qualified'),out);print(json.dumps({k:v for k,v in out.items() if k not in {'receipts','quality_quarantines'}}),flush=True)

def coverage(prefix):
 assert prefix=='01' and regular_state(cov(prefix))[0] is None
 frozen_source=source_freeze()
 # The q is now present, so load the exact prior census without treating the q as a prior stage.
 qpath=name(prefix,'qualified');q=load(qpath);prior=prior_coverage(prefix);base=load(prior);successful,capture_settled=actual_capture04()
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
 base.update(observed_at_utc=now(),historical_predecessor_eleven_later_repair_result_sha256=base['later_repair_result_sha256'],later_repair_result_sha256=PINS[RUN+'-result.json'],original_census_file=BASE,original_census_sha256=BASE_SHA,prior_census_sha256=sha(prior),incremental_delta_qualification_sha256={qpath.name:sha(qpath)},delta_qualification_sha256=sha(qpath),failed_vendor_requests_not_retried=False,known_uncaptured_attempted_candidates=[r for r in base['known_uncaptured_attempted_candidates'] if r['ticker'] in missing],original_failed_attempts_retained=True,method_sha256=sha(__file__),missing_candidate_count=len(missing),missing_request_windows=list(missing.values()),all_own_raw_operations_settled=False,complete_vendor_history_proven=False)
 freeze(frozen_source)
 save(cov(prefix),base);print(json.dumps({'proof_sha256':sha(cov(prefix)),'valid_responses':count,'new_quality_quarantines':qcount,'histories':base['accepted_nonempty_ticker_histories'],'bars':base['accepted_distinct_bars'],'candidate_status':status}),flush=True)

if __name__=='__main__':
 assert len(sys.argv)==3 and sys.argv[2]=='01' and sys.argv[1] in {'preflight','qualify','coverage'}
 {'preflight':preflight,'qualify':qualify,'coverage':coverage}[sys.argv[1]]('01')
