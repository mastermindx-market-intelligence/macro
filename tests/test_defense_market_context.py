"""Portable synthetic owner-snapshot mutation tests; never live-source proof."""
from copy import deepcopy
from hashlib import sha256,md5
from io import BytesIO
from pathlib import Path
import importlib.util,json,os
import pandas as pd
import pytest
from engine.company_intelligence.contracts import canonical_json_bytes
from engine.government_revenue.defense_economics import COHORT
if os.environ.get('DFE_ADAPTER_PATH'):
 spec=importlib.util.spec_from_file_location('adapter_subject',os.environ['DFE_ADAPTER_PATH']);subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
else:
 from engine.government_revenue import defense_market_context as subject
NOW='2026-10-13T03:00:00Z'
CIKS={'LMT':'0000936468','RTX':'0000101829','NOC':'0001133421','LHX':'0000202058'}
def hash_bytes(x):return sha256(x).hexdigest()
def parquet(frame):
 b=BytesIO();frame.to_parquet(b,index=True);return b.getvalue()
def seal_row(financial,ticker):
 event=financial['manifest']['aliases'][ticker+'/2026Q2'];row=financial['rows'][event]['workspace'];digest=hash_bytes(canonical_json_bytes(row));financial['rows'][event]['sha256']=digest;financial['manifest']['files']['workspaces/'+event+'.json']={'sha256':digest};financial['manifest_sha256']=hash_bytes(canonical_json_bytes(financial['manifest']))
def fixture():
 manifest={'dir':'massive_stock_day','count':4,'files':[t+'.parquet' for t in COHORT],'store':{'latest_date':'2026-10-09','updated_at':'2026-10-12T02:00:00Z'}};raw=canonical_json_bytes(manifest)
 before={'key':'massive_stock_day/_manifest.json','sha256':hash_bytes(raw),'etag':md5(raw).hexdigest(),'last_modified':'2026-10-12T03:00:00Z','observed_at':'2026-10-13T00:00:00Z','content_length':len(raw)};after={**before,'observed_at':'2026-10-13T01:00:00Z'}
 receipt={'state':'STABLE_CANONICAL_SNAPSHOT_READ','manifest_before':before,'manifest_after':after,'objects':{}};prices={'manifest_bytes':raw,'receipt':receipt,'parquet_bytes':{}}
 security=[];aliases=[];fin={'manifest':{'generation_id':'synthetic-g1','aliases':{},'files':{}},'manifest_sha256':'','rows':{}}
 for ticker in COHORT:
  frame=pd.DataFrame({'close':[100.0,100.0],'volume':[10.0,10.0]},index=pd.DatetimeIndex(['2026-10-08','2026-10-09'],name='date'));body=parquet(frame);prices['parquet_bytes'][ticker]=body
  receipt['objects'][ticker]={'state':'STABLE_BYTE_READ','key':'massive_stock_day/'+ticker+'.parquet','sha256':hash_bytes(body),'etag':md5(body).hexdigest(),'last_modified':'2026-10-10T09:00:00Z','observed_at':'2026-10-13T00:30:00Z','content_length':len(body)}
  sec='SEC:US-XNYS-'+ticker;iss='ISS:US-XNYS-'+ticker;cik=CIKS[ticker];security.append({'security_id':sec,'issuer_id':iss,'issuer_state':'RESOLVED','listing_key':'US-XNYS-'+ticker,'issuer_cik':cik})
  aliases.append({'vendor':'store','vendor_symbol':ticker,'security_id':sec,'valid_from':None,'valid_to':None})
  event='evt_cik'+cik+'_2026q2_results';row={'event_id':event,'generation_id':'synthetic-g1','issuer':{'company_id':'cik:'+cik,'listings':[{'security_id':'xnys:'+ticker,'ticker':ticker,'mic':'XNYS','share_class':'common','is_primary':True,'valid_from':'1970-01-01','valid_to':None}]},'sources':[{'kind':'issuer_release','filing_key':{'cik':cik},'receipt_state':'byte_replayed','document_id':'synthetic-'+ticker}],'lifecycle':{'observed_at':'2026-10-13T00:00:00Z','source_available_at':'2026-07-01T00:00:00Z'}}
  fin['manifest']['aliases'][ticker+'/2026Q2']=event;fin['rows'][event]={'workspace':row,'sha256':''};seal_row(fin,ticker)
 refs={'security_master_bytes':parquet(pd.DataFrame(security)),'vendor_aliases_bytes':parquet(pd.DataFrame(aliases)),'issuer_master_bytes':parquet(pd.DataFrame({'issuer_id':['synthetic-unused']})),'receipt_bytes':canonical_json_bytes({'authority':{'identity_authority':'canonical_exact_identity'}}),'owner_refs':{}}
 for field,path in subject._REFERENCE_FILES.items():refs['owner_refs'][path]=hash_bytes(refs[field])
 for path in ('engine/stock_technicals.py','lib/nyse_calendar.py','lib/dataos/identity.py','lib/dataos/price.py','config/dataset_registry.yml','engine/company_intelligence/identity.py','research/licenses/MASSIVE_ENTITLEMENT_RECORD.md'):refs['owner_refs'][path]='c'*64
 rights={'path':'research/licenses/MASSIVE_ENTITLEMENT_RECORD.md','sha256':'c'*64,'derived_display_qualified':True,'debrand_required':True}
 return prices,fin,refs,rights

def compose(data):return subject.compose_defense_market_context(*data,generated_at=NOW)
def reseal_manifest(prices,manifest):
 raw=canonical_json_bytes(manifest);prices['manifest_bytes']=raw
 for key in ('manifest_before','manifest_after'):prices['receipt'][key].update(sha256=hash_bytes(raw),etag=md5(raw).hexdigest(),content_length=len(raw))
def reseal_frame(prices,frame,ticker='LMT'):
 raw=parquet(frame);prices['parquet_bytes'][ticker]=raw;prices['receipt']['objects'][ticker].update(sha256=hash_bytes(raw),etag=md5(raw).hexdigest(),content_length=len(raw))
def test_real_zero_and_stale_clock_are_preserved():
 x=compose(fixture());assert len(x['recognition_by_ticker'])==4
 for ticker,axis in x['recognition_by_ticker'].items():
  leg=axis['price_response'];assert leg['state']=='stale' and leg['sessions_behind']==1 and leg['return_pct']==0;assert leg['market_as_of']=='2026-10-09' and leg['previous_session']=='2026-10-08';assert leg['security_id']=='xnys:'+ticker
  assert axis['expectations_kind']=='not_observed' and axis['valuation_scenario']['state']=='missing_owner';assert 'relative_return_pct' not in leg and 'benchmark' not in leg;assert 'massive' not in (axis['summary_en']+axis['summary_zh']).lower()
@pytest.mark.parametrize('field,value',[('sha256','0'*64),('etag','0'*32),('content_length',1),('key','other/LMT.parquet'),('state','UNQUALIFIED')])
def test_object_identity_fault_refuses(field,value):
 d=fixture();d[0]['receipt']['objects']['LMT'][field]=value
 with pytest.raises(ValueError):compose(d)
@pytest.mark.parametrize('fault',['body','version','missing_quartet','future_read','vintage_after_read','future_manifest','count'])
def test_sealed_source_faults_refuse(fault):
 d=fixture();p=d[0]
 if fault=='body':p['parquet_bytes']['LMT']+=b'x'
 elif fault=='version':p['receipt']['manifest_after']['etag']='0'*32
 elif fault=='missing_quartet':p['parquet_bytes'].pop('LHX')
 elif fault=='future_read':p['receipt']['objects']['LMT']['observed_at']='2027-01-01T00:00:00Z'
 elif fault=='vintage_after_read':p['receipt']['objects']['LMT']['last_modified']='2026-10-13T02:00:00Z'
 elif fault=='future_manifest':p['receipt']['manifest_before']['last_modified']='2027-01-01T00:00:00Z'
 else:
  m=json.loads(p['manifest_bytes']);m['count']=0;reseal_manifest(p,m)
 with pytest.raises((ValueError,KeyError)):compose(d)
@pytest.mark.parametrize('fault',['gap','future','boolean','duplicate','negative'])
def test_calendar_and_bar_value_faults_refuse(fault):
 d=fixture();p=d[0];frame=pd.read_parquet(BytesIO(p['parquet_bytes']['LMT']))
 if fault=='gap':frame.index=pd.DatetimeIndex(['2026-10-07','2026-10-09'],name='date')
 elif fault=='future':frame.index=pd.DatetimeIndex(['2026-10-12','2026-10-13'],name='date')
 elif fault=='duplicate':frame.index=pd.DatetimeIndex(['2026-10-09','2026-10-09'],name='date')
 elif fault=='boolean':frame['close']=True
 else:frame.iloc[-1,frame.columns.get_loc('close')]=-1.0
 reseal_frame(p,frame)
 with pytest.raises(ValueError):compose(d)
@pytest.mark.parametrize('fault',['cik','mic','class','ambiguous','rowhash','generation','future'])
def test_current_owner_subject_join_faults_refuse(fault):
 d=fixture();fin=d[1];row=fin['rows'][fin['manifest']['aliases']['LMT/2026Q2']]['workspace']
 if fault=='cik':row['sources'][0]['filing_key']['cik']='0000101829'
 elif fault=='mic':row['issuer']['listings'][0]['mic']='XNAS'
 elif fault=='class':row['issuer']['listings'][0]['share_class']='preferred'
 elif fault=='ambiguous':row['issuer']['listings'].append(deepcopy(row['issuer']['listings'][0]))
 elif fault=='generation':row['generation_id']='synthetic-other'
 elif fault=='future':row['lifecycle']['observed_at']='2027-01-01T00:00:00Z'
 else:fin['rows'][fin['manifest']['aliases']['LMT/2026Q2']]['sha256']='0'*64
 if fault!='rowhash':seal_row(fin,'LMT')
 with pytest.raises(ValueError):compose(d)
@pytest.mark.parametrize('fault',['reference_hash','authority','rights','rights_hash'])
def test_reference_or_display_grant_faults_refuse(fault):
 d=fixture()
 if fault=='reference_hash':d[2]['owner_refs']['data/reference/security_master.parquet']='0'*64
 elif fault=='authority':
  d[2]['receipt_bytes']=canonical_json_bytes({'authority':{'identity_authority':'unqualified'}});d[2]['owner_refs']['data/reference/_receipt.json']=hash_bytes(d[2]['receipt_bytes'])
 elif fault=='rights':d[3]['derived_display_qualified']=False
 else:d[3]['sha256']='0'*64
 with pytest.raises(ValueError):compose(d)
def test_change_in_actual_source_bytes_changes_owner_binding():
 d=fixture();first=compose(d);frame=pd.read_parquet(BytesIO(d[0]['parquet_bytes']['LMT']));frame.iloc[-1,frame.columns.get_loc('close')]=101;reseal_frame(d[0],frame);second=compose(d)
 assert first['recognition_by_ticker']['LMT']['owner_ref']!=second['recognition_by_ticker']['LMT']['owner_ref']
def test_distinct_before_after_observation_clocks_are_not_forged_equal():
 d=fixture();before=d[0]['receipt']['manifest_before']['observed_at'];after=d[0]['receipt']['manifest_after']['observed_at'];assert before!=after;compose(d)
@pytest.mark.parametrize('fault',['ancestor_symlink','dangling_receipt','non_directory'])
def test_loader_refuses_unsafe_paths_before_read(tmp_path,fault):
 root=tmp_path/'root';root.mkdir();rights={'path':'research/licenses/MASSIVE_ENTITLEMENT_RECORD.md','sha256':'c'*64,'derived_display_qualified':True,'debrand_required':True}
 if fault=='ancestor_symlink':
  other=tmp_path/'other';other.mkdir();(root/'data').symlink_to(other,target_is_directory=True)
 elif fault=='non_directory':(root/'data').write_text('not a directory')
 else:
  scratch=root/'data/massive_stock_day/.defense_read';scratch.mkdir(parents=True);(scratch/'manifest.json').symlink_to(tmp_path/'missing.json')
 with pytest.raises(ValueError):subject.load_defense_market_inputs(root,rights_ref=rights)

@pytest.mark.parametrize('fault',['issuer_id','security_id'])
def test_existing_financial_namespace_fields_cannot_be_relabelled(fault):
 d=fixture();f=d[1];row=f['rows'][f['manifest']['aliases']['LMT/2026Q2']]['workspace']
 if fault=='issuer_id':row['issuer']['company_id']='cik:0000101829'
 else:row['issuer']['listings'][0]['security_id']='xnys:RTX'
 seal_row(f,'LMT')
 with pytest.raises(ValueError,match='existing_financial_identity_namespace_mismatch'):compose(d)
def test_current_archive_has_zero_calendar_lag_and_supported_state():
 d=fixture();p=d[0];manifest=json.loads(p['manifest_bytes']);manifest['store']['latest_date']='2026-10-12';reseal_manifest(p,manifest)
 for t in COHORT:
  f=pd.read_parquet(BytesIO(p['parquet_bytes'][t]));f.index=pd.DatetimeIndex(['2026-10-09','2026-10-12'],name='date');reseal_frame(p,f,t);p['receipt']['objects'][t]['last_modified']='2026-10-12T23:00:00Z'
 view=compose(d)
 assert all(a['price_response']['state']=='supported' and a['price_response']['sessions_behind']==0 for a in view['recognition_by_ticker'].values())
