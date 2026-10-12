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
 assert result['publication']=={'requested':True,'attempted':2,'succeeded':1,'failed':1,'final_invalidation_delivered':False}

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
