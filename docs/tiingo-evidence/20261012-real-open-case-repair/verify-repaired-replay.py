import hashlib,json,sys,uuid
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
SOURCE=Path('/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/tiingo-ci-continuation-20261011-476f2cbd5f9b6dec')
ROOT=Path('/Volumes/Mastermind/market-data/tiingo')
OUT=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
RUN='tiingo-boats-raw-20261012-01a12ab6'
sys.path.insert(0,str(SOURCE))
from scripts.tiingo_materialize import verified_raw
from scripts.build_ext_quotes import BoatsLastTrade,public_boats_payload
q=json.loads((OUT/(RUN+'-qualified.json')).read_text());scope=json.loads((OUT/(RUN+'-scope.json')).read_text());settled=json.loads((OUT/(RUN+'-result.json')).read_text())
assert hashlib.sha256((SOURCE/'scripts/build_ext_quotes.py').read_bytes()).hexdigest()=='25e2866a24562e50fe5ba3bf996e83c1c021b9bc9599e7cce98be6cd29877476'
frames=[];references=[];conditions=Counter();eligible=Counter();exact_by_symbol={}
for record in q['selected_receipts']:
 p=ROOT/record['receipt_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==record['receipt_sha256']
 r=json.loads(p.read_text());raw=verified_raw(ROOT,r);references.append(r['raw_sha256'])
 for line in raw.splitlines():
  w=json.loads(line);frames.append((w['received_at'],w['raw_message']))
  d=json.loads(w['raw_message']).get('data')
  if isinstance(d,list) and len(d)==10 and d[0]=='T':
   c=tuple(d[6:10]);conditions[c]+=1
   allowed=all(type(v) is str and v in a for v,a in zip(c,({'','@'},{'','F'},{'','T'},{''})))
   if allowed:
    eligible[d[3]]+=1;exact_by_symbol.setdefault(d[3].upper(),[]).append((d,w['received_at'],hashlib.sha256(w['raw_message'].encode()).hexdigest(),r['raw_sha256']))
frames.sort(key=lambda x:x[0]);r=BoatsLastTrade(['AAPL','MSFT','AMZN','GOOGL','META','NVDA','TSLA','SPY','QQQ'],str(uuid.uuid4()));r.reset('connected',1)
for received,raw in frames:r.consume(raw,received)
view_time=datetime.fromisoformat(settled['settled_at_utc']);payload=r.snapshot(view_time);assert public_boats_payload(payload,view_time)==payload
assert set(payload['quotes'])=={'AAPL'},'genuine selected sample admits only qualified AAPL; no forced positive from odd lots or absent targets'
output=[]
for symbol,entry in payload['quotes'].items():
 matches=[(d,a,sha,segment) for d,a,sha,segment in exact_by_symbol[symbol] if entry['extPrice']==d[4] and entry['extTs']==d[2]/1_000_000_000 and entry['extReceivedAt']==datetime.fromisoformat(a).isoformat()]
 assert len(matches)==1
 d,a,sha,segment=matches[0]
 output.append({'display_symbol':symbol,'exact_vendor_symbol':d[3],'event_at_utc':entry['extEventAt'],'received_at_utc':entry['extReceivedAt'],'raw_message_sha256':sha,'raw_segment_sha256':segment,'raw_price_and_event_lineage_verified':True,'sale_conditions':d[6:10]})
proof={'schema':'tiingo_boats_repaired_authentic_offline_replay.v1','observed_at_utc':datetime.now(timezone.utc).isoformat(),'replay_snapshot_clock':view_time.isoformat(),'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((SOURCE/'scripts/build_ext_quotes.py').read_bytes()).hexdigest(),'original_qualification_sha256':hashlib.sha256((OUT/(RUN+'-qualified.json')).read_bytes()).hexdigest(),'source_segments':len(references),'original_frames':len(frames),'raw_frames_modified':False,'sale_condition_counts':[{'conditions':k,'count':v} for k,v in conditions.items()],'condition_eligible_T_count':sum(eligible.values()),'condition_eligible_aapl_T_count':eligible['aapl'],'qualified_display_symbols':sorted(payload['quotes']),'qualified_display_lineage':output,'public_allowlist_unchanged_and_passed':True,'unqualified_odd_lots_not_promoted':True,'fixture_or_live_prices_published':False,'network':False,'credentials_read':False,'publication':False,'production_consumer_acceptance':False,'historical_replay_not_fresh_market_snapshot':True}
assert not (OUT/(RUN+'-repaired-replay.json')).exists()
(OUT/(RUN+'-repaired-replay.json')).write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');print(json.dumps(proof,indent=2))
