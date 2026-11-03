import sys, json, hashlib, subprocess
from pathlib import Path
from datetime import date, datetime, timezone
from collections import Counter
root=Path('/opt/macro'); sys.path.insert(0,str(root))
from engine.chronicle import spine
from engine.press import desk_planner as p
paths=list(spine.REBUILD_SOURCES)+['data/market_state/latest.json','data/gex/latest.json','site/basketdata/breadth_split.json','site/basketdata/fear_greed.json','config/press.yml','data/press/published.jsonl','data/chronicle/events.jsonl','site/marketdata/sp500_heatmap.json','data/marketing/hot_tape_pack.json']
def head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
def hashes(): return {x:hashlib.sha256((root/x).read_bytes()).hexdigest() if (root/x).is_file() else None for x in paths}
h=head(); before=hashes(); day=date(2026,10,14)
events,report=spine.build_events(root,as_of=day)
candidates=p._event_candidates(events,day,3)
own=[e for e in candidates if e.get('source') in p._FIRST_PARTY_CHRONICLE_SOURCES]
facts=p.engine_stat_facts(root,as_of=day); movers=p.mover_facts(root,as_of=day)
committed=p._chronicle_events(root); committed_candidates=p._event_candidates(committed,day,3)
output={'observed_at':datetime.now(timezone.utc).isoformat(),'head':h,'stable_head':head()==h,'input_hashes':before,'inputs_unchanged':before==hashes(),'candidate_method':'installed desk_planner._event_candidates over pure spine.build_events','source_counts':dict(Counter(e.get('source') for e in candidates)),'own_current_events':own,'committed_source_counts':dict(Counter(e.get('source') for e in committed_candidates)),'committed_own_events':[e for e in committed_candidates if e.get('source') in p._FIRST_PARTY_CHRONICLE_SOURCES],'engine_facts':facts,'mover_facts':movers,'report':report,'provider_calls':0,'staging_or_producer_writes':0}
print(json.dumps(output,indent=2))
assert output['stable_head'] and output['inputs_unchanged']
