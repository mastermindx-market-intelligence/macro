"""Selected historical contracts do not become a root alias or PIT evidence."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,io,json
import pandas as pd
import pytest
from engine.intelligence_workspace.entity import IdentityArtifactRead,IdentityResolutionError
from engine.intelligence_workspace.options_contract_identity import resolve_dated_spy_contract_identity,validate_dated_contract_identity
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

def test_bound_actual_scope_has_separate_effective_and_known_clocks_no_alias(listing):
 g,oi,ctx,obs,args=setup(listing);bound=resolve_dated_spy_contract_identity(g,oi,**args).receipt
 assert bound['scope']=='selected_contracts' and len(bound['contract_keys'])==2
 assert bound['effective_from']==DAY and bound['effective_to']=='2026-10-20'
 assert bound['known_at']=='2026-10-20T09:00:00+00:00' and not bound['root_alias_created']
 assert not bound['historical_first_availability_established']
 assert len(validate_dated_contract_identity(bound,root='SPY',source_session=DAY,input_sha256=args['input_sha256'],cutoff=NOW))==2
 with pytest.raises(IdentityResolutionError):validate_dated_contract_identity(bound,root='SPY',source_session=DAY,input_sha256=args['input_sha256'],cutoff='2026-10-19T21:00:00Z')

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
