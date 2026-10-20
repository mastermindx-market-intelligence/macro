"""Selected historical contracts do not become a root alias or PIT evidence."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,io,json
import pandas as pd
import pytest
from engine.intelligence_workspace.entity import IdentityArtifactRead,IdentityResolutionError
from engine.intelligence_workspace.options_contract_identity import resolve_dated_spy_contract_identity,validate_dated_contract_identity,resolve_observed_spy_contract_identity,_sha
from engine.options_exposure_projection import compose_native_exposure_context,build_exposure_projection,exposure_input_digest
from lib.options_source_receipts import ACQUISITION_COLUMN,theta_acquisition,THETA_ENDPOINTS
from lib import symbol_directory_receipts as R
from tests.test_options_dated_projection import dated_book

DAY='2026-10-19';NOW='2026-10-20T10:00:00Z';READ='2026-10-20T09:00:00Z'
def captured(raw,at=READ):return IdentityArtifactRead(raw,hashlib.sha256(raw).hexdigest(),at)
def parquet(frame):
 out=io.BytesIO();frame.to_parquet(out,index=False);return out.getvalue()
def master(**changes):
 row=dict(security_id='SEC:US-ARCX-SPY',listing_key='US-ARCX-SPY',country='US',mic='ARCX',inception_code='SPY',effective_at=pd.Timestamp('2026-10-15'),ingested_at=pd.Timestamp('2026-10-15T12:00:00'),security_state=None,superseded_by=None)
 row.update(changes);return captured(parquet(pd.DataFrame([row])))

@pytest.fixture(scope='module')
def listing(tmp_path_factory):
 root=tmp_path_factory.mktemp('scoped-identity');n,o=5000,6500
 frame=pd.DataFrame(dict(date=['2026-10-15']*(n+o),symbol=[f'N{i}' for i in range(n)]+[f'O{i}' for i in range(o-1)]+['SPY'],security_name=['Synthetic']*(n+o),exchange=['NASDAQ']*n+['N']*(o-1)+['P'],etf=[False]*(n+o-1)+[True],test_issue=[False]*(n+o),is_preferred=[False]*(n+o),source=['nasdaqlisted']*n+['otherlisted']*o))
 p=root/'snapshots'/'2026-10-15.parquet';p.parent.mkdir();frame.to_parquet(p,index=False)
 sources=[]
 for sid,url in [(R.NASDAQ_LISTED_SOURCE_ID,'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'),(R.OTHER_LISTED_SOURCE_ID,'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt')]:
  sources.append((sid,R.SourceFetch(value='synthetic',content=b'synthetic',requested_url=url,started_at='2026-10-15T01:00:00.000000Z',completed_at='2026-10-15T01:00:01.000000Z')))
 receipt=R.build_symbol_directory_completion_receipt(kind='listing_snapshot',observation_date='2026-10-15',artifact_path=p,source_fetches=sources,collector_started_at='2026-10-15T00:59:59.000000Z',collector_completed_at='2026-10-15T01:00:02.000000Z',pre_dedupe_rows=n+o,duplicate_occurrences=0,duplicate_key_count=0,source_row_counts=((R.NASDAQ_LISTED_SOURCE_ID,n),(R.OTHER_LISTED_SOURCE_ID,o)),pre_dedupe_spy_occurrences=({'source_id':R.OTHER_LISTED_SOURCE_ID,'symbol':'SPY','security_name':'Synthetic','exchange':'P','etf':True,'test_issue':False,'is_preferred':False},),non_authoritative_footers=tuple(R.footer_diagnostic(source_id=sid,text='File Creation Time: 10/15/2026 01:00:00') for sid,_ in sources))
 return captured(p.read_bytes()),captured(json.dumps(receipt,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n')

def setup(listing):
 g,oi,ctx=dated_book()
 for f,kind in ((g,'greeks'),(oi,'oi')):
  f['date']=pd.Timestamp(DAY)
  params=dict(symbol='SPY',expiration='20261023',start_date=20261019,end_date=20261019,right='both',strike_range=5,format='csv')
  if kind=='greeks':params['version']='1'
  f[ACQUISITION_COLUMN]=theta_acquisition(THETA_ENDPOINTS[kind],params,b'synthetic',origin='http://theta-test:25503',received_at='2026-10-20T08:00:00Z')
 contracts=[dict(ticker=f'O:SPY261023{s}00100000',underlying_ticker='SPY',contract_type='call' if s=='C' else 'put',expiration_date='2026-10-23',strike_price=100,exercise_style='american',shares_per_contract=100) for s in ('C','P')]
 obs=dict(schema='options_reference_capability_observation/v1',state='response_observed',origin='https://api.polygon.io',path='/v3/reference/options/contracts',params=dict(as_of=DAY,underlying_ticker='SPY',expiration_date='2026-10-23'),capability=dict(http_status=200,verdict='entitled'),contracts=contracts,payload_sha256='a'*64,completed_at='2026-10-20T08:05:00Z',historical_first_availability_established=False)
 args=dict(source_session=DAY,input_sha256=exposure_input_digest(g,oi,DAY,'SPY'),reference=captured(json.dumps(obs).encode()),security_master=master(),listing=listing[0],listing_receipt=listing[1],decision_at=NOW)
 return g,oi,ctx,obs,args


def observed_setup(listing,count=120):
 g,oi,ctx,_,args=setup(listing)
 g=pd.concat([g.iloc[[i%2]] for i in range(count)],ignore_index=True)
 oi=pd.concat([oi.iloc[[i%2]] for i in range(count)],ignore_index=True)
 exps=['2026-10-23','2026-10-30','2026-11-06']
 for frame,kind in ((g,'greeks'),(oi,'oi')):
  frame['strike']=[100+i//2 for i in range(count)]
  frame['expiration']=[exps[(i//2)%3] for i in range(count)]
  params=dict(symbol='SPY',expiration='*',start_date=20261019,end_date=20261019,right='both',format='csv')
  if kind=='greeks':params['version']='1'
  frame[ACQUISITION_COLUMN]=theta_acquisition(THETA_ENDPOINTS[kind],params,b'synthetic-full-book',origin='http://theta-test:25503',received_at='2026-10-20T08:00:00Z')
 contracts=[]
 for row in g.to_dict('records'):
  stamp=pd.Timestamp(row['expiration']).strftime('%y%m%d');right=row['right'];strike=row['strike']
  contracts.append(dict(ticker=f'O:SPY{stamp}{right}{int(strike*1000):08d}',underlying_ticker='SPY',contract_type='call' if right=='C' else 'put',expiration_date=row['expiration'],strike_price=strike,exercise_style='american',shares_per_contract=100))
 scope=dict(underlying_ticker='SPY',as_of=DAY,**{'expiration_date.gte':DAY},expired='false',order='asc',sort='ticker',limit=1000)
 page=dict(schema='options_reference_page_observation/v1',state='response_observed',origin='https://api.polygon.io',path='/v3/reference/options/contracts',params=scope,capability=dict(http_status=200,verdict='entitled',evidence=dict(response_sha256='a'*64,response_bytes=123456,completed_at='2026-10-20T08:05:00Z')),payload_sha256='a'*64,completed_at='2026-10-20T08:05:00Z',contracts=contracts,next_params=None)
 obs=dict(schema='options_reference_population_observation/v1',state='COMPLETE',root='SPY',source_session=DAY,origin=page['origin'],path=page['path'],initial_params=scope,pages=[page],historical_first_availability_established=False)
 args.update(reference=captured(json.dumps(obs).encode()),input_sha256=exposure_input_digest(g,oi,DAY,'SPY'))
 return g,oi,ctx,obs,args


def test_observed_population_binds_many_expiries_without_shrinking_missing_terms(listing):
 g,oi,ctx,obs,args=observed_setup(listing)
 # One missing exact reference member has zero OI. It is still unbound/missing.
 obs['pages'][0]['contracts'].pop();oi.loc[len(oi)-1,'open_interest']=0
 args.update(reference=captured(json.dumps(obs).encode()),input_sha256=exposure_input_digest(g,oi,DAY,'SPY'))
 bound=resolve_observed_spy_contract_identity(g,oi,**args).receipt
 assert len(bound['observed_contract_keys'])==120 and len(bound['contract_keys'])==119
 assert len(validate_dated_contract_identity(bound,root='SPY',source_session=DAY,input_sha256=args['input_sha256'],cutoff=NOW))==119
 ctx.update(security_id=None,clocks=dict(option_observed_at=None,underlying_observed_at=None),contract_terms=[],term_policy='occ_standard_spy_etf/v1',contract_reference_populations=[obs],input_sha256=args['input_sha256'],dated_population_identity_inputs={k:v for k,v in args.items() if k not in ('source_session','input_sha256')})
 ctx['valuation']['source_session']=DAY
 out=compose_native_exposure_context(g,oi,DAY,'SPY',context=ctx)
 out['greek_provenance']['gamma']['source_ref']=out['source_snapshot_ref']
 p=build_exposure_projection(g,oi,DAY,'SPY',context=out)
 assert p['metrics']['gamma']['expected'] is None and p['metrics']['gamma']['received']==120
 assert p['metrics']['gamma']['qualified']==119 and p['metrics']['gamma']['missing']==1
 assert p['metrics']['gamma']['gross'] is None and p['metrics']['gamma']['known_gross']>0
 assert p['metrics']['gamma']['exclusions']=={'contract_identity_scope_unknown':1}
 from engine.options_exposure_projection import CELL_FIELDS,METRIC_FIELDS
 assert sum(c[CELL_FIELDS.index('metrics')][0][METRIC_FIELDS.index('qualified')]+c[CELL_FIELDS.index('metrics')][0][METRIC_FIELDS.index('missing')] for c in p['cells'])==120
 per_coordinate={}
 for expiry,strike,right in bound['contract_keys']:
  per_coordinate[(expiry,float(strike))]=per_coordinate.get((expiry,float(strike)),0)+1
 for cell in p['cells']:
  expiry=p['expiry_terms'][cell[0]][0];limit=per_coordinate.get((expiry,cell[1]),0)
  assert all(m[METRIC_FIELDS.index('qualified')]<=limit for m in cell[3])
  assert cell[4][2]<=limit
 assert p['metrics']['vanna']['qualified']==0 and p['metrics']['charm']['qualified']==0


@pytest.mark.parametrize('mode',['partial','unfinished','root','date','capture_after_read','scope','missing_target','duplicate_observed'])
def test_observed_identity_negative_inputs(listing,mode):
 g,oi,ctx,obs,args=observed_setup(listing,24)
 if mode=='partial':obs['state']='STOPPED'
 if mode=='unfinished':obs['pages'][0]['next_params']={'cursor':'more'}
 if mode=='root':obs['root']='QQQ'
 if mode=='date':obs['source_session']='2026-10-18'
 if mode=='capture_after_read':args['reference']=captured(json.dumps(obs).encode(),at='2026-10-20T07:00:00Z')
 if mode=='scope':obs['initial_params']['as_of']='2026-10-18'
 if mode=='missing_target':args['security_master']=master(security_id='SEC:US-XNAS-QQQ',listing_key='US-XNAS-QQQ',mic='XNAS',inception_code='QQQ')
 if mode=='duplicate_observed':g=pd.concat([g,g.iloc[[0]]],ignore_index=True)
 if mode!='capture_after_read':args['reference']=captured(json.dumps(obs).encode())
 args['input_sha256']=exposure_input_digest(g,oi,DAY,'SPY')
 with pytest.raises(IdentityResolutionError):resolve_observed_spy_contract_identity(g,oi,**args)


def test_observed_receipt_rejects_cursor_repeat_even_when_scope_echo_changes(listing):
 g,oi,ctx,obs,args=observed_setup(listing,24)
 receipt=resolve_observed_spy_contract_identity(g,oi,**args).receipt
 p=deepcopy(receipt['reference_pages'][0]);p['params']={'cursor':'same'}
 q=deepcopy(p);q['params']={'cursor':'same','limit':'1000'}
 receipt['reference_pages'] += [p,q]
 receipt['binding_sha256']=_sha({k:v for k,v in receipt.items() if k!='binding_sha256'})
 with pytest.raises(IdentityResolutionError):validate_dated_contract_identity(receipt,root='SPY',source_session=DAY,input_sha256=args['input_sha256'],cutoff=NOW)


def test_retained_full_pair_proves_identity_read_not_original_greek_acquisition(listing):
 g,oi,ctx,obs,args=observed_setup(listing,24)
 g=g.drop(columns=ACQUISITION_COLUMN);oi=oi.drop(columns=ACQUISITION_COLUMN)
 args.update(input_sha256=exposure_input_digest(g,oi,DAY,'SPY'),retained_inputs=dict(greeks=captured(parquet(g)),oi=captured(parquet(oi))))
 receipt=resolve_observed_spy_contract_identity(g,oi,**args).receipt
 assert receipt['source_evidence_basis']=='retained_native_store_read' and len(receipt['source_input_artifacts'])==2
 assert not receipt['historical_first_availability_established']
 ctx.update(root='SPY',security_id=receipt['security_id'],contract_identity=receipt,input_sha256=args['input_sha256'])
 ctx['clocks'].update(source_session=DAY,oi_report_date=DAY,available_at=NOW,greeks_available_at=READ,oi_available_at=READ)
 ctx['valuation']['source_session']=DAY
 p=build_exposure_projection(g,oi,DAY,'SPY',context=ctx)
 assert p['metrics']['gamma']['qualified']==0 and p['metrics']['gamma']['missing']==24

def test_bound_actual_scope_has_separate_effective_and_known_clocks_no_alias(listing):
 g,oi,ctx,obs,args=setup(listing);bound=resolve_dated_spy_contract_identity(g,oi,**args).receipt
 assert bound['scope']=='selected_contracts' and len(bound['contract_keys'])==2
 assert bound['effective_from']==DAY and bound['effective_to']=='2026-10-20'
 assert bound['known_at']=='2026-10-20T09:00:00+00:00' and not bound['root_alias_created']
 assert not bound['historical_first_availability_established']
 assert len(validate_dated_contract_identity(bound,root='SPY',source_session=DAY,input_sha256=args['input_sha256'],cutoff=NOW))==2
 with pytest.raises(IdentityResolutionError):validate_dated_contract_identity(bound,root='SPY',source_session=DAY,input_sha256=args['input_sha256'],cutoff='2026-10-19T21:00:00Z')

@pytest.mark.parametrize('mode',['completed_after_session','receipt_read_before_completion'])
def test_listing_completion_must_be_known_and_precede_source_session(listing,mode):
 g,oi,ctx,obs,args=setup(listing)
 receipt=json.loads(args['listing_receipt'].body)
 if mode=='completed_after_session':
  # Valid incumbent receipt semantics permit a long collection interval;
  # this dated adapter cannot use post-session completion as session evidence.
  receipt['clocks']['collector_completed_at']='2026-10-20T01:00:00.000000Z'
  receipt['receipt_id']=R._receipt_id(receipt)
  raw=R._canonical_json_bytes(receipt)+b'\n'
  R.validate_symbol_directory_completion_receipt_bytes(receipt,raw,args['listing'].body,expected_kind='listing_snapshot')
  args['listing_receipt']=captured(raw)
 else:
  args['listing_receipt']=captured(args['listing_receipt'].body,at='2026-10-15T01:00:01Z')
 with pytest.raises(IdentityResolutionError,match='Listing observation'):
  resolve_dated_spy_contract_identity(g,oi,**args)

@pytest.mark.parametrize('mode',['root','asof','asof_absent','series','adjusted','extra_deliverable','canonical_missing','canonical_listing','canonical_retired','canonical_late','before_known','native_date','scope_widen','reference_digest','listing_digest'])
def test_adversarial_identity_inputs_fail_closed(listing,mode):
 g,oi,ctx,obs,args=setup(listing)
 if mode=='root':obs['params']['underlying_ticker']='QQQ'
 elif mode=='asof':obs['params']['as_of']='2026-10-18'
 elif mode=='asof_absent':obs['params'].pop('as_of')
 elif mode=='series':obs['contracts'][0]['ticker']='O:SPY261023C00101000'
 elif mode=='adjusted':obs['contracts'][0]['shares_per_contract']=150
 elif mode=='extra_deliverable':obs['contracts'][0]['additional_underlyings']=[dict(type='currency',underlying='USD',amount=1)]
 elif mode=='canonical_missing':args['security_master']=master(security_id='SEC:US-ARCX-OTHER',listing_key='US-ARCX-OTHER',inception_code='OTHER')
 elif mode=='canonical_listing':args['security_master']=master(mic='XNAS')
 elif mode=='canonical_retired':args['security_master']=master(security_state='retired')
 elif mode=='canonical_late':args['security_master']=master(effective_at=pd.Timestamp('2026-10-20'),ingested_at=pd.Timestamp('2026-10-20'))
 elif mode=='before_known':args['decision_at']='2026-10-19T23:00:00Z'
 elif mode=='native_date':g['date']=pd.Timestamp('2026-10-18')
 elif mode=='scope_widen':g=pd.concat([g,g.iloc[:1].assign(strike=101)],ignore_index=True)
 elif mode=='listing_digest':args['listing']=IdentityArtifactRead(args['listing'].body,'0'*64,READ)
 args['reference']=captured(json.dumps(obs).encode())
 if mode=='reference_digest':args['reference']=IdentityArtifactRead(args['reference'].body,'0'*64,READ)
 args['input_sha256']=exposure_input_digest(g,oi,DAY,'SPY')
 with pytest.raises(IdentityResolutionError):resolve_dated_spy_contract_identity(g,oi,**args)

def test_native_composition_qualifies_only_bound_gamma_and_rejects_scope_reuse(listing):
 g,oi,ctx,obs,args=setup(listing)
 ctx.update(security_id=None,clocks=dict(option_observed_at=None,underlying_observed_at=None),contract_terms=[],term_policy='occ_standard_spy_etf/v1',contract_reference_observations=[obs],input_sha256=args['input_sha256'],dated_identity_inputs={k:v for k,v in args.items() if k not in ('source_session','input_sha256')})
 ctx['valuation']['source_session']=DAY
 out=compose_native_exposure_context(g,oi,DAY,'SPY',context=ctx)
 out['greek_provenance']['gamma']['source_ref']=out['source_snapshot_ref']
 p=build_exposure_projection(g,oi,DAY,'SPY',context=out)
 assert p['metrics']['gamma']['qualified']==2 and p['metrics']['vanna']['qualified']==0
 assert p['contract_identity']['scope']=='selected_contracts' and not p['contract_identity']['root_alias_created']
 changed=g.copy();changed.loc[0,'strike']=101
 out['input_sha256']=exposure_input_digest(changed,oi,DAY,'SPY')
 assert build_exposure_projection(changed,oi,DAY,'SPY',context=out)['metrics']['gamma']['qualified']==0
 out['contract_identity']['scope']='root_alias'
 assert build_exposure_projection(g,oi,DAY,'SPY',context=out)['metrics']['gamma']['qualified']==0


def test_expected_unbound_coordinate_stays_missing_before_totals(listing):
 g,oi,ctx,obs,args=setup(listing)
 ctx.update(security_id=None,clocks=dict(option_observed_at=None,underlying_observed_at=None),contract_terms=[],term_policy='occ_standard_spy_etf/v1',contract_reference_observations=[obs],input_sha256=args['input_sha256'],dated_identity_inputs={k:v for k,v in args.items() if k not in ('source_session','input_sha256')})
 ctx['valuation']['source_session']=DAY
 out=compose_native_exposure_context(g,oi,DAY,'SPY',context=ctx)
 out['greek_provenance']['gamma']['source_ref']=out['source_snapshot_ref']
 out['expected_contracts']=g.to_dict('records')+[dict(root='SPY',expiration='2026-10-23',strike=101,right='C')]
 p=build_exposure_projection(g,oi,DAY,'SPY',context=out)
 assert p['metrics']['gamma']['expected']==3 and p['metrics']['gamma']['qualified']==2
 assert p['metrics']['gamma']['missing']==1 and p['metrics']['gamma']['gross'] is None
 assert p['metrics']['gamma']['exclusions']=={'contract_identity_scope_unknown':1}
 assert len(p['contract_identity']['contract_keys'])==2 and not p['contract_identity']['root_alias_created']


def native_bundle(listing,tmp_path):
 g,oi,ctx,obs,args=setup(listing)
 ctx.update(security_id=None,clocks=dict(option_observed_at=None,underlying_observed_at=None),contract_terms=[],term_policy='occ_standard_spy_etf/v1',contract_reference_observations=[obs],input_sha256=args['input_sha256'],dated_identity_inputs={k:v for k,v in args.items() if k not in ('source_session','input_sha256')})
 ctx['valuation']['source_session']=DAY
 ctx=compose_native_exposure_context(g,oi,DAY,'SPY',context=ctx)
 ctx['greek_provenance']['gamma']['source_ref']=ctx['source_snapshot_ref']
 g.to_parquet(tmp_path/'selected-greeks.parquet',index=False);oi.to_parquet(tmp_path/'selected-oi.parquet',index=False)
 ctx['root']='SPY'
 ctx['source_inputs']=dict(schema='options_hub.projection_inputs/v1',greeks='selected-greeks.parquet',oi='selected-oi.parquet')
 manifest=dict(schema='options_hub.exposure_contexts/v1',roots={'SPY':ctx})
 path=tmp_path/'context.json';path.write_text(json.dumps(manifest))
 return g,oi,path,manifest


@pytest.mark.parametrize("legacy_empty",[False,True])
def test_native_builder_optional_capture_preserves_full_legacy_book(listing,tmp_path,monkeypatch,legacy_empty):
 from scripts import build_options_hub_nightly as b
 from engine.options_hub import compute_gex
 g,oi,path,manifest=native_bundle(listing,tmp_path)
 contexts=b.load_exposure_contexts(str(path))
 all_g=pd.concat([g,g.iloc[:1].assign(strike=101,gamma=.02)],ignore_index=True)
 all_oi=pd.concat([oi,oi.iloc[:1].assign(strike=101)],ignore_index=True)
 if legacy_empty:all_g=all_g.iloc[:0]
 baseline=compute_gex(all_g,all_oi,DAY,'SPY')
 monkeypatch.setattr(b,'_load_greeks',lambda *a:all_g)
 monkeypatch.setattr(b,'_load_oi_for_date',lambda *a:all_oi)
 monkeypatch.setattr(b,'_load_yahoo',lambda *a:None)
 monkeypatch.setattr(b,'compute_vol',lambda *a:{})
 monkeypatch.setattr(b,'compute_vex',lambda *a,**kw:{})
 _,published,_=b.build_root('SPY',DAY,None,exposure_context=contexts['SPY'])
 assert {k:v for k,v in published.items() if k not in ('exposure_projection','exposure_projection_input')}=={k:v for k,v in baseline.items() if k!='exposure_projection'}
 assert published['exposure_projection']['metrics']['gamma']['qualified']==2
 assert published['exposure_projection']['population']['observed_contracts']==2
 assert published['coverage']['n_contracts']==(0 if legacy_empty else 3)
 if legacy_empty:assert published['spot_ref'] is None and published['exposure_projection']['underlying_reference']['value']==100
 assert published['exposure_projection_input']['source_session']==DAY
 assert published['exposure_projection_input']['legacy_source_session']==DAY
 assert '_projection_inputs' in contexts['SPY'] # caller/context reusable, no mutation


@pytest.mark.parametrize('mode',['traversal','symlink','wrong_digest','oversize_rows','missing','no_identity'])
def test_native_capture_manifest_refuses_unsafe_or_mismatched_inputs(listing,tmp_path,mode):
 from scripts.build_options_hub_nightly import load_exposure_contexts
 g,oi,path,manifest=native_bundle(listing,tmp_path)
 ctx=manifest['roots']['SPY'];spec=ctx['source_inputs']
 if mode=='traversal':spec['greeks']='../selected-greeks.parquet'
 elif mode=='symlink':(tmp_path/'linked.parquet').symlink_to(tmp_path/'selected-greeks.parquet');spec['greeks']='linked.parquet'
 elif mode=='wrong_digest':g.loc[0,'gamma']=.123;g.to_parquet(tmp_path/'selected-greeks.parquet',index=False)
 elif mode=='oversize_rows':pd.concat([g]*33,ignore_index=True).to_parquet(tmp_path/'selected-greeks.parquet',index=False)
 elif mode=='missing':spec['greeks']='missing.parquet'
 elif mode=='no_identity':ctx.pop('contract_identity')
 path.write_text(json.dumps(manifest))
 with pytest.raises((ValueError,OSError)):load_exposure_contexts(str(path))


def test_stale_capture_does_not_replace_current_legacy_or_carry_old_identity(listing,tmp_path,monkeypatch):
 from scripts import build_options_hub_nightly as b
 from engine.options_hub import compute_gex
 g,oi,path,manifest=native_bundle(listing,tmp_path)
 context=b.load_exposure_contexts(str(path))['SPY']
 day='2026-10-20';g=g.assign(date=pd.Timestamp(day));oi=oi.assign(date=pd.Timestamp(day))
 baseline=compute_gex(g,oi,day,'SPY')
 monkeypatch.setattr(b,'_load_greeks',lambda *a:g)
 monkeypatch.setattr(b,'_load_oi_for_date',lambda *a:oi)
 monkeypatch.setattr(b,'_load_yahoo',lambda *a:None)
 monkeypatch.setattr(b,'compute_vol',lambda *a:{})
 monkeypatch.setattr(b,'compute_vex',lambda *a,**kw:{})
 _,out,_=b.build_root('SPY',day,None,exposure_context=context)
 assert {k:v for k,v in out.items() if k!='exposure_projection_input'}==baseline
 assert out['exposure_projection']['cells_status']=='source_unqualified'
 assert out['exposure_projection_input']['state']=='withheld_source_session_mismatch'


@pytest.mark.parametrize('mode',['rows','columns','decoded_bytes'])
def test_retained_metadata_is_rejected_before_decoding(listing,monkeypatch,mode):
 import pyarrow.parquet as pq
 from types import SimpleNamespace
 g,oi,ctx,obs,args=observed_setup(listing,24)
 g=g.drop(columns=ACQUISITION_COLUMN);oi=oi.drop(columns=ACQUISITION_COLUMN)
 args.update(input_sha256=exposure_input_digest(g,oi,DAY,'SPY'),retained_inputs=dict(greeks=captured(parquet(g)),oi=captured(parquet(oi))))
 class GuardedParquet:
  schema_arrow=SimpleNamespace(names=['x']*(65 if mode=='columns' else 1))
  metadata=SimpleNamespace(num_rows=100001 if mode=='rows' else 24,num_row_groups=1,
    row_group=lambda i:SimpleNamespace(total_byte_size=128*1024*1024+1 if mode=='decoded_bytes' else 128))
  def read(self):raise AssertionError('Decoded before metadata admission')
 monkeypatch.setattr(pq,'ParquetFile',lambda *a,**kw:GuardedParquet())
 with pytest.raises(IdentityResolutionError,match='decoded bound'):
  resolve_observed_spy_contract_identity(g,oi,**args)


@pytest.mark.parametrize('mode',['nested_artifact','bad_decimal','nested_decimal','empty_pages','bound_exceeds_page_count'])
def test_malformed_v2_receipt_refuses_as_lane_local_identity_error(listing,mode):
 g,oi,ctx,obs,args=observed_setup(listing,24)
 receipt=resolve_observed_spy_contract_identity(g,oi,**args).receipt
 if mode=='nested_artifact':
  receipt['source_evidence_basis']='retained_native_store_read';receipt['source_input_artifacts']=[None,None]
 if mode=='bad_decimal':receipt['observed_contract_keys'][0][1]='not-a-number'
 if mode=='nested_decimal':receipt['observed_contract_keys'][0][1]=['nested']
 if mode=='empty_pages':receipt['reference_pages']=[]
 if mode=='bound_exceeds_page_count':receipt['reference_pages'][0]['contracts']=23
 receipt['binding_sha256']=_sha({k:v for k,v in receipt.items() if k!='binding_sha256'})
 with pytest.raises(IdentityResolutionError):
  validate_dated_contract_identity(receipt,root='SPY',source_session=DAY,input_sha256=args['input_sha256'],cutoff=NOW)
