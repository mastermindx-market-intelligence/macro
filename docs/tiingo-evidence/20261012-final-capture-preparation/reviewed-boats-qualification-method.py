"""Qualify the original finite BOATS outcome; no connection or public publication."""
import hashlib,json,os,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
C=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009');R=Path('/Volumes/Mastermind/market-data/tiingo');E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');RUN='tiingo-boats-raw-20261013-01a12ab6';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(C))
from collectors.tiingo_archive import validate_receipt,decode_boats,require_space
from scripts.tiingo_materialize import verified_raw,materialize_one
from lib.dataos.tiingo_reader import read_research_view
from lib.dataos.tiingo_boats_tape import audit_boats_tape
scopep=E/(RUN+'-scope.json');scope=json.loads(scopep.read_text());assert scope['method_sha256']=='5354cc084fb6a8e65653894b0306c9bf89dd940dcfa19cfa779523f5a648933d';assert scope['owner_thread']=='01a12ab6-92cb-7c42-a711-42673ebb6b50'
assert scope['max_seconds']==600 and scope['max_messages']==2000000 and scope['first_gap_stops_without_reconnection'] and not scope['r2_publication']
for rel,h in scope['loaded_source_sha256'].items():assert sha(C/rel)==h
baselinep=E/'tiingo-boats-20261013-prior-partition-binding.json';assert sha(baselinep)==scope['prior_partition_binding_sha256']=='12af3577d0c1591457b2a051c997cbb03922db02ddf929de929a723b84146998';baseline=json.loads(baselinep.read_text())
assert scope['prior_boats_receipts']==baseline['prior_receipt_sha256']
for rel,h in baseline['prior_receipt_sha256'].items():assert sha(R/rel)==h
normalp=E/(RUN+'-result.json');failedp=E/(RUN+'-failure.json');assert normalp.exists()!=failedp.exists();settlep=normalp if normalp.exists() else failedp;settle=json.loads(settlep.read_text());normal=normalp.exists()
assert settle['run_id']==RUN and not settle['r2_publication'];assert settle['settled_at_utc']>=scope['started_at_utc'];observer=settle['observer_outcome']
if normal:assert settle['connections']==1 and settle['transport_breaks']==0 and observer['stop_reason'] is None
else:assert settle['original_receipt_reconciliation_required'] and settle['partial_archive_preserved']
out=E/(RUN+'-qualified.json');assert not out.exists();require_space(R,floor=40*1024**3)
records=[];counts=Counter();controls=Counter();symbols=set();raw_bytes=0;refs=[];materialization=Counter()
for p in sorted((R/'receipts/boats-firehose').glob('*/*.json')):
 rel=str(p.relative_to(R))
 if rel in baseline['prior_receipt_sha256']:continue
 rec=json.loads(p.read_text());assert scope['started_at_utc']<=rec['first_received_at_utc']<=rec['last_received_at_utc']<=settle['settled_at_utc'],'unreconciled new BOATS custody outside this owned scope'
 identity=validate_receipt(rec);raw=verified_raw(R,rec);actual=Counter()
 for line in raw.splitlines():
  wrapper=json.loads(line);message=json.loads(wrapper['raw_message']);event=decode_boats(message,wrapper['received_at']);actual[event['kind'] if event else 'other']+=1
  if event:symbols.add(event['ticker'])
  else:controls[(str(message.get('messageType')),message.get('response',{}).get('code'))]+=1
 assert dict(actual)=={k:v for k,v in rec['counts'].items() if v}
 mat=materialize_one(R,rec,free_floor=40*1024**3,dry_run=False);assert mat['status'] in ('WRITTEN','EXISTS','EMPTY_NORMALIZED','REPAIRED_MANIFEST');materialization[mat['status']]+=1
 market=sum(actual[k] for k in ('Q','T','B'));day=rec['first_received_at_utc'][:10]
 if market:
  view=read_research_view('boats-firehose',day,rec['raw_sha256'],root=R,max_rows=20000)
  assert len(view.rows)==market and all(row['source_sha256']==rec['raw_sha256'] and row['source_receipt_id']==identity for row in view.rows)
  refs.append((day,rec['raw_sha256']))
 else:assert mat['status']=='EMPTY_NORMALIZED'
 records.append({'receipt_path':rel,'receipt_sha256':sha(p),'raw_sha256':rec['raw_sha256'],'raw_bytes':len(raw),'counts':rec['counts'],'first_received_at_utc':rec['first_received_at_utc'],'last_received_at_utc':rec['last_received_at_utc'],'projection_rows':market,'raw_verified':True,'reader_lineage_verified':True if market else None,'reader_status':'VERIFIED' if market else 'NOT_APPLICABLE_CONTROL_ONLY','tape_status':'SELECTED_FOR_BOUNDED_AUDIT' if market else 'NOT_APPLICABLE_CONTROL_ONLY'})
 counts.update(actual);raw_bytes+=len(raw)
assert raw_bytes==observer['archived_bytes'] and len(records)==observer['archived_segments']
if normal:assert raw_bytes==settle['bytes'] and len(records)==settle['segments'] and sum(counts.values())==settle['raw_messages']
# The existing audit contract limits each independent report to 32 captures.
# Bound reports explicitly; do not join cross-chunk quote/trade context or claim continuity.
audits=[];cutoff=datetime.now(timezone.utc).isoformat()
for offset in range(0,len(refs),32):
 chunk=refs[offset:offset+32];reports={}
 for symbol in ('AAPL','MSFT','AMZN','GOOGL','META','NVDA','TSLA','SPY','QQQ'):
  reports[symbol]=audit_boats_tape(chunk,vendor_symbol=symbol,start_event_at_utc='2026-10-13T00:00:00+00:00',end_event_at_utc=settle['settled_at_utc'],observed_before_utc=cutoff,root=R,max_captures=32,max_events_per_capture=2000,max_observations=100000,max_examples=0)
 audits.append({'first_market_receipt_index':offset,'receipt_count':len(chunk),'reports':reports,'cross_chunk_quote_context_joined':False})
proof={'schema':'tiingo.owned_finite_boats_raw_and_reader_qualification/v1','run_id':RUN,'recorded_at_utc':cutoff,'method_sha256':sha(Path(__file__)),'scope_sha256':sha(scopep),'actual_settlement_sha256':sha(settlep),'actual_settlement_file':settlep.name,'normal_completion':normal,'actual_observer_outcome':observer,'all_original_raw_and_receipt_counts_verified':True,'all_new_projection_reader_lineage_verified':True,'prior_receipts_preserved':True,'selected_receipts':records,'messages':sum(counts.values()),'counts':dict(counts),'raw_bytes':raw_bytes,'distinct_vendor_symbols':len(symbols),'materialization_status_counts':dict(materialization),'control_counts':[{'message_type':k[0],'response_code':k[1],'count':v} for k,v in sorted(controls.items(),key=lambda item:(item[0][0],str(item[0][1])))],'bounded_chunk_audits':audits,'cross_chunk_continuity_claimed':False,'full_session_coverage':False,'canonical_identity_admitted':False,'pit_backtest_eligible':False,'r2_publication':False,'production_consumer_acceptance':False,'provider_requests':0,'credentials_read':False}
with os.fdopen(os.open(out,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in proof.items() if k not in ('selected_receipts','bounded_chunk_audits')}))
