import gzip,hashlib,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
SOURCE=Path('/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009')
ROOT=Path('/Volumes/Mastermind/market-data/tiingo')
OUT=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
RUN='tiingo-boats-raw-20261012-01a12ab6'
sys.path.insert(0,str(SOURCE))
from scripts.tiingo_materialize import verified_raw
from lib.dataos.tiingo_boats_tape import audit_boats_tape
from scripts.build_ext_quotes import BoatsLastTrade
q=json.loads((OUT/(RUN+'-qualified.json')).read_text())
refs=[];frames=[];case_counts=Counter();targets=Counter();clock_range={}
for record in q['selected_receipts']:
 r=json.loads((ROOT/record['receipt_path']).read_text());raw=verified_raw(ROOT,r)
 refs.append((r['first_received_at_utc'][:10],r['raw_sha256']))
 for line in raw.splitlines():
  w=json.loads(line);m=json.loads(w['raw_message']);data=m.get('data')
  frames.append((w['received_at'],w['raw_message']))
  if not isinstance(data,list) or not data or data[0] not in ('Q','T','B'):continue
  symbol=data[3];case_counts['lowercase' if symbol==symbol.lower() else 'other']+=1
  if symbol.lower() in ('aapl','msft','amzn','googl','meta','nvda','tsla','spy','qqq'):targets[symbol]+=1
  c=clock_range.setdefault(data[0],{'min_event_at':data[1],'max_event_at':data[1]});c['min_event_at']=min(c['min_event_at'],data[1]);c['max_event_at']=max(c['max_event_at'],data[1])
frames.sort(key=lambda x:x[0])
reducer=BoatsLastTrade(['AAPL','MSFT','AMZN','GOOGL','META','NVDA','TSLA','SPY','QQQ'],'offline-authentic-replay')
reducer.reset('connected',1)
for received,raw in frames:reducer.consume(raw,received)
assert reducer.quotes=={} and reducer.watermarks=={},'original casing mismatch must reproduce'
cutoff=datetime.now(timezone.utc).isoformat();audits={}
for symbol in ('aapl','msft','amzn','googl','meta','nvda','tsla','spy','qqq'):
 audits[symbol]=audit_boats_tape(refs,vendor_symbol=symbol,start_event_at_utc='2026-10-12T00:00:00+00:00',end_event_at_utc=q['last_received_at_utc'],observed_before_utc=cutoff,root=ROOT,max_captures=32,max_events_per_capture=2000,max_observations=20000,max_examples=0)
proof={'schema':'tiingo_boats_exact_vendor_case_replay.v1','observed_at_utc':cutoff,'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'original_qualified_sha256':hashlib.sha256((OUT/(RUN+'-qualified.json')).read_bytes()).hexdigest(),'original_producer_sha256':hashlib.sha256((SOURCE/'scripts/build_ext_quotes.py').read_bytes()).hexdigest(),'exact_vendor_target_symbols_and_counts':dict(targets),'market_frame_case_counts':dict(case_counts),'per_kind_event_clocks':clock_range,'original_display_replay_quotes':len(reducer.quotes),'original_display_replay_watermarks':len(reducer.watermarks),'original_display_casing_rejection_reproduced':True,'original_zero_uppercase_research_queries_preserved':True,'exact_lowercase_vendor_audits':audits,'raw_frames_modified':False,'canonical_identity_admitted':False,'public_publication':False}
assert not (OUT/(RUN+'-vendor-case-replay.json')).exists()
(OUT/(RUN+'-vendor-case-replay.json')).write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:proof[k] for k in ('exact_vendor_target_symbols_and_counts','market_frame_case_counts','per_kind_event_clocks','original_display_casing_rejection_reproduced')},indent=2))
print(json.dumps({s:{k:a[k] for k in ('status','selected_kind_counts','trade_quote_age_diagnostics','quality_flags')} for s,a in audits.items()},indent=2))
