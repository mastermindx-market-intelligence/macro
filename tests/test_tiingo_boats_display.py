"""Offline tests of a proposed archive-bound single-venue last-trade display."""
from datetime import datetime, timedelta, timezone
import json
import pytest
from scripts.build_ext_quotes import BoatsLastTrade, boats_session_date

NOW=datetime(2026,10,12,0,1,tzinfo=timezone.utc)

def frame(kind='T',offset=0,symbol='AMD',price=100,size=10,conditions=None):
 dt=NOW+timedelta(seconds=offset)
 ns=int(dt.timestamp())*1_000_000_000+dt.microsecond*1000
 data=[kind,dt.isoformat(),ns,symbol,price,size,*(conditions if conditions is not None else ['', '', '', ''])]
 if kind=='Q': data=[kind,dt.isoformat(),ns,symbol,10,99,100,101,20]
 return json.dumps({'service':'boats','data':data})

def reducer():
 r=BoatsLastTrade(['AMD','AAPL'],'offline-fixture')
 r.reset('connected',1)
 return r

def consume(r,raw,offset=0):
 r.consume(raw,(NOW+timedelta(seconds=offset)).isoformat())


def test_only_archived_trade_age_can_qualify_and_quotes_do_not_refresh():
 r=reducer();consume(r,frame())
 q=r.snapshot(NOW)['quotes']['AMD']
 assert q['extPrice']==100 and q['extSource']=='tiingo_boats'
 assert q['extVenue']=='BOATS' and q['extPriceKind']=='LAST_TRADE'
 assert q['nbbo'] is False and q['venue_scope']=='single_ats'
 consume(r,frame('Q',20),20)
 assert r.snapshot(NOW+timedelta(seconds=31))['quotes']=={}


@pytest.mark.parametrize('quote_offset', [1.025, -60])
def test_quote_clock_failure_cannot_erase_or_refresh_a_valid_trade(quote_offset):
 r=reducer();consume(r,frame())
 original=r.snapshot(NOW)['quotes']['AMD'].copy()
 watermark=r.watermarks['AMD']
 consume(r,frame('Q',quote_offset),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']['AMD']==original
 assert r.watermarks['AMD']==watermark
 assert r.snapshot(NOW+timedelta(seconds=31))['quotes']=={}


@pytest.mark.parametrize('kind', ['Q', 'T', 'B'])
def test_invalid_identity_remains_fail_closed_for_every_message_kind(kind):
 r=reducer();consume(r,frame())
 obj=json.loads(frame(kind,1));obj['data'][3]=123
 consume(r,json.dumps(obj),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']=={}


def test_malformed_quote_clock_does_not_change_last_trade_state():
 r=reducer();consume(r,frame())
 original=r.snapshot(NOW)['quotes']['AMD'].copy()
 quote=json.loads(frame('Q',1));quote['data'][1]='invalid-clock'
 consume(r,json.dumps(quote),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']['AMD']==original


def test_break_invalidates_even_without_matching_price_or_size():
 r=reducer();consume(r,frame())
 consume(r,frame('B',1,price=77,size=3),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']=={}
 consume(r,frame(offset=0),2)
 assert r.snapshot(NOW+timedelta(seconds=2))['quotes']=={}
 consume(r,frame(offset=3),3)
 assert 'AMD' in r.snapshot(NOW+timedelta(seconds=3))['quotes']


@pytest.mark.parametrize('mutate',[
 lambda d:d.__setitem__(2,str(d[2])),
 lambda d:d.__setitem__(2,d[2]+1_000_000),
 lambda d:d.__setitem__(3,123),
 lambda d:d.__setitem__(4,float('nan')),
 lambda d:d.__setitem__(4,0),
 lambda d:d.__setitem__(5,-1),
 lambda d:d.pop(),
])
def test_malformed_trade_never_promotes_or_preserves_a_current_trade(mutate):
 r=reducer();consume(r,frame())
 obj=json.loads(frame(offset=1));mutate(obj['data'])
 consume(r,json.dumps(obj),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']=={}


def test_ignored_other_symbol_does_not_destroy_covered_state():
 r=reducer();consume(r,frame());consume(r,frame(symbol='MSFT'))
 assert set(r.snapshot(NOW)['quotes'])=={'AMD'}


def test_late_and_future_frames_do_not_rejuvenate():
 r=reducer();consume(r,frame());consume(r,frame(offset=-31))
 assert r.snapshot(NOW)['quotes']=={}
 consume(r,frame(offset=2),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']=={}


def test_full_replace_and_gap_generation_reset():
 r=reducer();consume(r,frame())
 assert r.snapshot(NOW)['snapshot_mode']=='full_replace'
 r.reset('gap')
 assert r.snapshot(NOW)['quotes']=={}
 r.reset('connected',2)
 assert r.snapshot(NOW)['connection_generation']==2
 assert r.snapshot(NOW)['quotes']=={}
 r.reset('ended')
 assert r.snapshot(NOW)['stream_status']=='ended'


def test_session_boundary_and_sunday_open():
 assert boats_session_date(NOW)=='2026-10-12'
 assert boats_session_date(datetime(2026,10,12,8,tzinfo=timezone.utc)) is None
 assert boats_session_date(datetime(2026,10,10,0,tzinfo=timezone.utc)) is None
 assert reducer().snapshot(NOW)['expires_at_utc']==(NOW+timedelta(seconds=30)).isoformat()


def test_submicrosecond_future_event_is_rejected_before_float_precision_loss():
 r=reducer();obj=json.loads(frame());obj['data'][2]+=1
 consume(r,json.dumps(obj))
 assert r.snapshot(NOW)['quotes']=={}

def test_invalid_kind_does_not_crash_material_frame_handling():
 r=reducer();consume(r,frame());obj=json.loads(frame());obj['data'][0]={}
 consume(r,json.dumps(obj))
 assert r.snapshot(NOW)['quotes']=={}


@pytest.mark.parametrize('conditions', [['@','F','T',''], ['@','','T',''], ['','','','']])
def test_documented_regular_sale_conditions_qualify(conditions):
 r=reducer();consume(r,frame(conditions=conditions))
 assert 'AMD' in r.snapshot(NOW)['quotes']

@pytest.mark.parametrize('conditions', [['@','F','T','I'], ['@','F','T','H'], ['@','F','T','X'], ['Z','','',''], ['', '@','',''], ['', '', 'F',''], ['', '', '',None]])
def test_unknown_or_excluded_sale_condition_cannot_rejuvenate(conditions):
 r=reducer();consume(r,frame());consume(r,frame(offset=29,conditions=conditions),29)
 assert r.snapshot(NOW+timedelta(seconds=29))['quotes']['AMD']['extTs']==NOW.timestamp()
 assert r.snapshot(NOW+timedelta(seconds=31))['quotes']=={}

def test_break_conditions_never_exempt_invalidation():
 r=reducer();consume(r,frame());consume(r,frame('B',1,conditions=['Z','@','F','X']),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']=={}


def test_boats_smoke_is_rejected_before_any_collector_or_publisher(monkeypatch):
 import scripts.build_ext_quotes as builder
 monkeypatch.setattr(builder.sys,'argv',['build_ext_quotes','--boats','--smoke','--publish'])
 def forbidden(**_):
  pytest.fail('smoke entered a live publisher')
 monkeypatch.setattr(builder,'publish_boats_stream',forbidden)
 with pytest.raises(SystemExit) as error:
  builder.main()
 assert error.value.code==2

def test_publishing_failure_is_machine_readable_and_final_invalidation_separate(monkeypatch):
 import scripts.build_ext_quotes as builder
 import scripts.tiingo_ingest as ing
 def stream(**kw):
  ob=kw['observer'];ob('connected',{'connection':1})
  ob('ended',{})
  return {'raw_messages':0,'segments':0}
 monkeypatch.setattr(ing,'boats_stream',stream)
 delivered=iter([True,False])
 monkeypatch.setattr(builder,'_publish_r2',lambda _:next(delivered))
 result=builder.publish_boats_stream(publish=True)
 assert result['publication_ok'] is False
 assert result['publication']=={'requested':True,'attempted':2,'succeeded':1,'failed':1,'final_invalidation_delivered':False,'access_denied':False}

def test_requested_publication_success_requires_terminal_empty_delivery(monkeypatch):
 import scripts.build_ext_quotes as builder
 import scripts.tiingo_ingest as ing
 snapshots=[]
 def stream(**kw):
  kw['observer']('connected',{'connection':1})
  kw['observer']('ended',{})
  return {'raw_messages':0,'segments':0}
 monkeypatch.setattr(ing,'boats_stream',stream)
 monkeypatch.setattr(builder,'_publish_r2',lambda raw:snapshots.append(json.loads(raw)) or True)
 result=builder.publish_boats_stream(publish=True)
 assert result['publication_ok'] is True
 assert snapshots[-1]['stream_status']=='ended' and snapshots[-1]['quotes']=={}


def public_snapshot():
 r=BoatsLastTrade(['AMD'],'12345678-1234-1234-1234-123456789abc')
 r.reset('connected',1);consume(r,frame())
 return r.snapshot(NOW)


def test_public_allowlist_constructs_only_current_single_venue_trades():
 from scripts.build_ext_quotes import public_boats_payload
 p=public_snapshot()
 assert public_boats_payload(p,NOW)==p
 p['quotes']={};p['stream_status']='ended'
 assert public_boats_payload(p,NOW)['quotes']=={}


@pytest.mark.parametrize('mutation',[
 lambda p:p.__setitem__('source','yahoo-chart (grey)'),
 lambda p:p.__setitem__('schema','flow.ext_quotes/v1'),
 lambda p:p.__setitem__('raw_message','synthetic raw fixture'),
 lambda p:p['quotes']['AMD'].__setitem__('raw_message','synthetic raw fixture'),
 lambda p:p['quotes']['AMD'].__setitem__('extSource','webull'),
 lambda p:p['quotes']['AMD'].__setitem__('extBasis','UNOFFICIAL'),
 lambda p:p['quotes']['AMD'].__setitem__('nbbo',True),
 lambda p:p['quotes']['AMD'].__setitem__('extPrice',float('nan')),
 lambda p:p['quotes']['AMD'].__setitem__('extReceivedAt',(NOW+timedelta(seconds=1)).isoformat()),
 lambda p:p.__setitem__('stream_status','ended'),
 lambda p:p.__setitem__('capture_id','guessed-id'),
 lambda p:p.__setitem__('session_date','2026-10-11'),
])
def test_public_allowlist_rejects_unapproved_fields_sources_and_clock_claims(mutation):
 from scripts.build_ext_quotes import public_boats_payload
 p=public_snapshot();mutation(p)
 with pytest.raises((ValueError,TypeError)):
  public_boats_payload(p,NOW)


def test_legacy_publication_is_refused_before_client_or_credentials(monkeypatch):
 import scripts.build_ext_quotes as builder
 monkeypatch.setattr(builder,'_r2_client',lambda:pytest.fail('unapproved payload reached R2 client'))
 assert builder._publish_r2(json.dumps({'schema':'flow.ext_quotes/v1','quotes':{}})) is False
 monkeypatch.setattr(builder.sys,'argv',['build_ext_quotes','--publish'])
 monkeypatch.setattr(builder,'build_ext_quotes',lambda **_:pytest.fail('unapproved CLI started a collector'))
 with pytest.raises(SystemExit) as error:builder.main()
 assert error.value.code==2


def test_approved_empty_invalidation_uses_same_object_and_disables_cache(monkeypatch):
 import scripts.build_ext_quotes as builder
 now=datetime.now(timezone.utc)
 r=BoatsLastTrade(['AMD'],'12345678-1234-1234-1234-123456789abc');r.reset('ended',1)
 writes=[]
 class Client:
  def put_object(self,**kw):writes.append(kw)
 monkeypatch.setattr(builder,'_r2_client',lambda:Client())
 assert builder._publish_r2(json.dumps(r.snapshot(now))) is True
 assert writes[0]['Key']=='live_flow/ext_quotes.json'
 assert writes[0]['CacheControl']=='no-store, max-age=0'
 assert json.loads(writes[0]['Body'])['quotes']=={}


@pytest.mark.parametrize('status,code',[(401,'Unauthorized'),(403,'AccessDenied'),
                                      (400,'InvalidAccessKeyId'),(400,'SignatureDoesNotMatch'),
                                      (None,'403'),(None,'Forbidden'),(None,'AccessForbidden')])
def test_storage_denial_blocks_later_callbacks_without_interrupting_cleanup(monkeypatch,caplog,status,code):
 import scripts.build_ext_quotes as builder
 import scripts.tiingo_ingest as ing
 calls=[];settled=[]
 class Denial(Exception):
  response={'ResponseMetadata':{'HTTPStatusCode':status},'Error':{'Code':code,'Message':'SECRET_PROVIDER_BODY'}}
 class Client:
  def put_object(self,**kw):
   calls.append(kw)
   raise Denial('SECRET_PROVIDER_BODY')
 def stream(**kw):
  observer=kw['observer']
  observer('connected',{'connection':1})
  observer('archived',{'active':True,'connection':1,'frames':[]})
  observer('tick',{})
  observer('gap',{})
  observer('disconnected',{})
  observer('connected',{'connection':2})
  observer('ended',{})
  settled.append(True)
  return {'raw_messages':0,'segments':0}
 monkeypatch.setattr(builder,'_r2_client',lambda:Client())
 monkeypatch.setattr(ing,'boats_stream',stream)
 result=builder.publish_boats_stream(publish=True)
 assert settled==[True] and len(calls)==1
 assert result['publication_ok'] is False
 assert result['publication']=={'requested':True,'attempted':1,'succeeded':0,'failed':1,
                               'final_invalidation_delivered':False,'access_denied':True}
 assert 'publication stopped for this invocation' in caplog.text
 assert 'SECRET_PROVIDER_BODY' not in caplog.text


def test_transient_storage_failure_remains_distinct_from_access_denial(monkeypatch,caplog):
 import scripts.build_ext_quotes as builder
 class Transient(Exception):
  response={'ResponseMetadata':{'HTTPStatusCode':503},'Error':{'Code':'ServiceUnavailable'}}
 class Client:
  def put_object(self,**kw):raise Transient('SECRET_PROVIDER_BODY')
 monkeypatch.setattr(builder,'_r2_client',lambda:Client())
 r=BoatsLastTrade(['AMD'],'12345678-1234-1234-1234-123456789abc');r.reset('ended',1)
 assert builder._publish_r2(json.dumps(r.snapshot(datetime.now(timezone.utc)))) is False
 assert 'SECRET_PROVIDER_BODY' not in caplog.text


def test_lowercase_live_vendor_trade_preserves_source_and_public_uppercase_key():
 from collectors.tiingo_archive import decode_boats
 from scripts.build_ext_quotes import public_boats_payload
 r=BoatsLastTrade(['AMD'],'12345678-1234-1234-1234-123456789abc')
 r.reset('connected',1)
 raw=frame(symbol='amd',conditions=['@','','',''])
 consume(r,raw)
 assert json.loads(raw)['data'][3]=='amd'
 assert decode_boats(json.loads(raw),NOW.isoformat())['ticker']=='amd'
 payload=r.snapshot(NOW)
 assert set(payload['quotes'])=={'AMD'}
 assert payload['coverage_symbols']==['AMD']
 assert public_boats_payload(payload,NOW)==payload


def test_case_variants_share_one_trade_watermark():
 r=reducer();consume(r,frame(symbol='amd',offset=2,price=102),2)
 consume(r,frame(symbol='AMD',offset=1,price=101),3)
 consume(r,frame(symbol='aMd',offset=2,price=99),3)
 assert r.snapshot(NOW+timedelta(seconds=3))['quotes']['AMD']['extPrice']==102
 assert set(r.watermarks)=={'AMD'}
 assert r.watermarks['AMD']==int((NOW+timedelta(seconds=2)).timestamp())*1_000_000_000


def test_lowercase_break_invalidates_and_only_newer_case_variant_restores():
 r=reducer();consume(r,frame())
 consume(r,frame('B',1,symbol='amd',conditions=['Z','@','F','X']),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']=={}
 assert set(r.watermarks)=={'AMD'}
 consume(r,frame(offset=1,symbol='AMD'),2)
 assert r.snapshot(NOW+timedelta(seconds=2))['quotes']=={}
 consume(r,frame(offset=3,symbol='aMd'),3)
 assert set(r.snapshot(NOW+timedelta(seconds=3))['quotes'])=={'AMD'}


def test_lowercase_quote_cannot_erase_refresh_or_advance_a_trade():
 r=reducer();consume(r,frame())
 before=dict(r.watermarks)
 consume(r,frame('Q',20,symbol='amd'),20)
 assert r.watermarks==before
 assert r.snapshot(NOW+timedelta(seconds=20))['quotes']['AMD']['extTs']==NOW.timestamp()
 assert r.snapshot(NOW+timedelta(seconds=31))['quotes']=={}


@pytest.mark.parametrize('kind',['Q','T','B'])
def test_uncovered_lowercase_frame_preserves_covered_quotes_and_watermarks(kind):
 r=reducer();consume(r,frame())
 quotes=dict(r.quotes);watermarks=dict(r.watermarks)
 consume(r,frame(kind,1,symbol='msft'),1)
 assert r.quotes==quotes and r.watermarks==watermarks


@pytest.mark.parametrize('symbol',[None,True,123,[],{},' amd','amd ','amd\n','aｍd','ＡＭＤ','amd_','amd/','a'*33])
def test_invalid_identity_is_refused_before_case_mapping(symbol):
 r=reducer();consume(r,frame())
 consume(r,frame(offset=1,symbol=symbol),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']=={}


@pytest.mark.parametrize('denied', [True, False])
def test_client_initialization_failure_is_scrubbed_and_denial_stops_callbacks(monkeypatch, caplog, denied):
 import sys, types
 import scripts.build_ext_quotes as builder
 import scripts.tiingo_ingest as ing
 calls=[]
 class Failure(Exception):
  response={'Error':{'Code':'Forbidden' if denied else 'ServiceUnavailable'}}
 def client(*args,**kwargs):
  calls.append(True)
  raise Failure('SECRET_PROVIDER_BODY')
 monkeypatch.setitem(sys.modules,'boto3',types.SimpleNamespace(client=client))
 monkeypatch.setitem(sys.modules,'botocore.config',types.SimpleNamespace(Config=lambda **kwargs:object()))
 for name in ('R2_ENDPOINT','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY'):
  monkeypatch.setenv(name,'offline-fixture')
 if not denied:
  assert builder._r2_client() is None
  assert 'R2 client build failed (Failure)' in caplog.text
 else:
  def stream(**kwargs):
   for kind,payload in [('connected',{'connection':1}),('tick',{}),('ended',{})]:
    kwargs['observer'](kind,payload)
   return {'raw_messages':0,'segments':0}
  monkeypatch.setattr(ing,'boats_stream',stream)
  result=builder.publish_boats_stream(publish=True)
  assert result['publication']['access_denied'] is True
  assert result['publication']['final_invalidation_delivered'] is False
  assert 'publication stopped for this invocation' in caplog.text
 assert calls==[True]
 assert 'SECRET_PROVIDER_BODY' not in caplog.text


# ── coverage capacity: MAX_BOATS_SYMBOLS raises the 500-symbol display bound ──

def capacity_symbols(count, first=None):
 symbols=[f"Z{index:05d}" for index in range(count)]
 if first is not None:
  symbols[0]=first
 return symbols

def capacity_reducer(count):
 r=BoatsLastTrade(capacity_symbols(count,first='AMD'),'12345678-1234-1234-1234-123456789abc')
 r.reset('connected',1)
 return r

def test_full_observed_universe_of_15380_valid_covered_names_is_accepted_and_delivered():
 from scripts.build_ext_quotes import public_boats_payload
 r=capacity_reducer(15380)
 assert len(r.symbols)==15380
 assert r.symbols[0]=='AMD' and r.symbols[-1]=='Z15379'
 # Stable coverage ordering survives the capacity lift.
 assert list(r.symbols)==capacity_symbols(15380,first='AMD')
 consume(r,frame(offset=1),1)
 consume(r,frame(offset=2,symbol='Z00600',price=101),2)
 consume(r,frame(offset=3,symbol='z15379',price=102),3)
 payload=r.snapshot(NOW+timedelta(seconds=3))
 assert set(payload['quotes'])=={'AMD','Z00600','Z15379'}
 assert payload['coverage_symbols'][600]=='Z00600' and payload['coverage_symbols'][-1]=='Z15379'
 # Names above the previous 500-symbol bound are validated and delivered.
 assert public_boats_payload(payload,NOW+timedelta(seconds=3))==payload
 assert public_boats_payload(payload,NOW+timedelta(seconds=3))['quotes']['Z15379']['extPrice']==102

def test_hard_boundary_accepts_20000_and_refuses_20001():
 from scripts.build_ext_quotes import public_boats_payload, MAX_BOATS_SYMBOLS
 assert capacity_reducer(MAX_BOATS_SYMBOLS).snapshot(NOW)['coverage_symbols'].__len__()==20_000
 with pytest.raises(ValueError):
  BoatsLastTrade(capacity_symbols(20_001),'12345678-1234-1234-1234-123456789abc')
 p=public_snapshot();p['quotes']={};p['stream_status']='ended'
 exact=dict(p);exact['coverage_symbols']=capacity_symbols(20_000,first='AMD')
 assert public_boats_payload(exact,NOW)['coverage_symbols'].__len__()==20_000
 over=dict(p);over['coverage_symbols']=capacity_symbols(20_001,first='AMD')
 with pytest.raises(ValueError):
  public_boats_payload(over,NOW)

def test_duplicate_coverage_is_rejected_at_either_bound():
 from scripts.build_ext_quotes import public_boats_payload
 with pytest.raises(ValueError):
  BoatsLastTrade(['AMD','AMD'],'12345678-1234-1234-1234-123456789abc')
 with pytest.raises(ValueError):
  BoatsLastTrade(capacity_symbols(20_000,first='AMD')[:-1]+['AMD'],'12345678-1234-1234-1234-123456789abc')
 p=public_snapshot();p['quotes']={}
 duplicated=dict(p);duplicated['coverage_symbols']=['AMD','AMD']
 with pytest.raises(ValueError):
  public_boats_payload(duplicated,NOW)

def test_uncovered_rows_are_rejected_at_full_universe_coverage():
 from scripts.build_ext_quotes import public_boats_payload
 r=capacity_reducer(15380)
 consume(r,frame(offset=1),1)
 consume(r,frame(offset=2,symbol='MSFT'),2)  # uncovered vendor symbol
 payload=r.snapshot(NOW+timedelta(seconds=2))
 assert set(payload['quotes'])=={'AMD'}
 stranger=dict(payload);stranger['quotes']={'ZZZZZ':payload['quotes']['AMD']}
 with pytest.raises(ValueError):
  public_boats_payload(stranger,NOW+timedelta(seconds=2))

def test_stale_and_gap_invalidation_are_unchanged_at_capacity():
 r=capacity_reducer(15380)
 consume(r,frame(offset=1),1)
 assert r.snapshot(NOW+timedelta(seconds=1))['quotes']
 # Stale trades still age out at the same 30-second deadline.
 assert r.snapshot(NOW+timedelta(seconds=32))['quotes']=={}
 consume(r,frame(offset=2),2)
 assert 'AMD' in r.snapshot(NOW+timedelta(seconds=2))['quotes']
 consume(r,frame('B',3,symbol='AMD'),3)
 assert r.snapshot(NOW+timedelta(seconds=3))['quotes']=={}
 # A gap still clears every covered symbol without touching coverage.
 r.reset('gap')
 assert r.snapshot(NOW+timedelta(seconds=3))['quotes']=={}
 assert len(r.snapshot(NOW+timedelta(seconds=3))['coverage_symbols'])==15380
