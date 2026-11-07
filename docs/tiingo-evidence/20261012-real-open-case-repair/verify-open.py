import hashlib,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
SOURCE=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
ROOT=Path('/Volumes/Mastermind/market-data/tiingo')
OUT=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
RUN='tiingo-boats-raw-20261012-01a12ab6'
sys.path.insert(0,str(SOURCE))
from collectors.tiingo_archive import validate_receipt,decode_boats
from scripts.tiingo_materialize import verified_raw,materialize_many
from lib.dataos.tiingo_boats_tape import audit_boats_tape
scope=json.loads((OUT/(RUN+'-scope.json')).read_text())
result=json.loads((OUT/(RUN+'-result.json')).read_text())
assert result['segments']==20 and result['raw_messages']==20000 and result['transport_breaks']==0
for rel,sha in scope['loaded_source_sha256'].items():assert hashlib.sha256((SOURCE/rel).read_bytes()).hexdigest()==sha
for rel,sha in scope['prior_boats_receipts'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==sha
assert not (OUT/(RUN+'-qualified.json')).exists()
selected=[]; counts=Counter(); controls=Counter(); refs=[]; symbols=set(); total_raw=0
for p in sorted((ROOT/'receipts'/'boats-firehose').rglob('*.json')):
 r=json.loads(p.read_text())
 if r['first_received_at_utc']<scope['started_at_utc']:continue
 assert r['last_received_at_utc']<=result['settled_at_utc'],'new custody artifact outside this capture'
 validate_receipt(r);raw=verified_raw(ROOT,r);actual=Counter()
 for line in raw.splitlines():
  w=json.loads(line);m=json.loads(w['raw_message']);d=decode_boats(m,w['received_at'])
  actual[d['kind'] if d else 'other']+=1
  if d:symbols.add(d['ticker'])
  else:controls[(str(m.get('messageType')),m.get('response',{}).get('code'))]+=1
 assert dict(actual)=={k:v for k,v in r['counts'].items() if v},'original per-kind counts differ'
 counts.update(actual);total_raw+=len(raw)
 refs.append((r['first_received_at_utc'][:10],r['raw_sha256']))
 selected.append({'receipt_path':str(p.relative_to(ROOT)),'receipt_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'raw_sha256':r['raw_sha256'],'raw_bytes':len(raw),'counts':r['counts'],'first_received_at_utc':r['first_received_at_utc'],'last_received_at_utc':r['last_received_at_utc']})
assert len(selected)==result['segments'] and sum(counts.values())==result['raw_messages']
mat=materialize_many(ROOT,max_receipts=100,source_filter='boats-firehose',dry_run=False)
assert mat['refused']==0 and mat['errors']==[]
cutoff=datetime.now(timezone.utc).isoformat()
audits={}
for symbol in ('AAPL','MSFT','AMZN','GOOGL','META','NVDA','TSLA','SPY','QQQ'):
 audits[symbol]=audit_boats_tape(refs,vendor_symbol=symbol,start_event_at_utc='2026-10-12T00:00:00+00:00',end_event_at_utc=result['settled_at_utc'],observed_before_utc=cutoff,root=ROOT,max_captures=32,max_events_per_capture=2000,max_observations=20000,max_examples=0)
proof={'schema':'tiingo_boats_real_open_qualification.v1','run_id':RUN,'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope_sha256':hashlib.sha256((OUT/(RUN+'-scope.json')).read_bytes()).hexdigest(),'result_sha256':hashlib.sha256((OUT/(RUN+'-result.json')).read_bytes()).hexdigest(),'observed_at_utc':cutoff,'source_head':scope['source_head'],'source_hashes':scope['loaded_source_sha256'],'all_original_raw_and_receipt_counts_verified':True,'prior_boats_receipts_preserved':True,'materialization':mat,'selected_receipts':selected,'raw_bytes':total_raw,'messages':sum(counts.values()),'counts':dict(counts),'distinct_symbols_in_capture':len(symbols),'control_counts':[{'message_type':k[0],'response_code':k[1],'count':v} for k,v in sorted(controls.items())],'first_received_at_utc':min(r['first_received_at_utc'] for r in selected),'last_received_at_utc':max(r['last_received_at_utc'] for r in selected),'stopped_at_message_cap':True,'max_collection_seconds':120,'r2_publication':False,'continuous_session_coverage':False,'production_consumer_acceptance':False,'symbol_audits':audits}
(OUT/(RUN+'-qualified.json')).write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:proof[k] for k in ('run_id','all_original_raw_and_receipt_counts_verified','messages','counts','distinct_symbols_in_capture','first_received_at_utc','last_received_at_utc','materialization','control_counts')},indent=2))
print(json.dumps({s:{k:a[k] for k in ('status','selected_kind_counts','trade_quote_age_diagnostics','quality_flags')} for s,a in audits.items()},indent=2))
