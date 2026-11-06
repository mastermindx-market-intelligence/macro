"""Read-only Chronicle event frontier; no producer, provider, staging or writes."""
import sys,json,hashlib,subprocess
from pathlib import Path
from datetime import date,datetime,timezone
from collections import Counter
root=Path('/opt/macro');sys.path.insert(0,str(root))
from engine.chronicle import spine
from engine.press import desk_planner as p
as_of=date(2026,10,14)
closure=list(spine.REBUILD_SOURCES)+['data/chronicle/events.jsonl','config/press.yml','engine/chronicle/adapters.py','engine/chronicle/earnings_calls.py','engine/chronicle/spine.py','engine/chronicle/state_log.py','engine/press/desk_planner.py']
def head():return subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
def hashes():return {r:hashlib.sha256((root/r).read_bytes()).hexdigest() if (root/r).is_file() else None for r in closure}
def stamp(e):
 try:return date.fromisoformat(str(e.get('date','')))
 except (ValueError,TypeError):return None
def brief(e):return {k:e.get(k) for k in ('id','source','source_ref','date','kind','title','tickers','weight_hint')}
h=head();before=hashes();events,report=spine.build_events(root,as_of=as_of)
candidates=p._event_candidates(events,as_of,3);accepted={e['id'] for e in candidates}
summary={}
for source in sorted({e.get('source','unknown') for e in events}):
 rows=[e for e in events if e.get('source')==source]
 valid=[e for e in rows if stamp(e) is not None]
 current=[e for e in valid if 0 <= (as_of-stamp(e)).days <= 3]
 past=[e for e in valid if stamp(e)<=as_of]
 summary[source]={'total':len(rows),'malformed_dates':len(rows)-len(valid),'future_count':sum(stamp(e)>as_of for e in valid),'raw_in_window':len(current),'canonical_in_window':sum(e['id'] in accepted for e in current),'latest_past_date':max((e['date'] for e in past),default=None),'last_three_events':[brief(e) for e in sorted(past,key=lambda e:(e['date'],e['id']))[-3:]],'current_excluded':[brief(e) for e in current if e['id'] not in accepted][:10]}
def jsonl(rel):
 rows=[]
 for line in (root/rel).read_text().splitlines():
  if not line.strip() or line.startswith('#'):continue
  try:r=json.loads(line)
  except ValueError:continue
  if isinstance(r,dict):rows.append(r)
 return rows
radar=jsonl('data/risk_radar/forward_log.jsonl')
release=jsonl('data/release_forecast/forward_ledger.jsonl')
state=jsonl('data/chronicle/state_log.jsonl')
recent_radar=[{k:r.get(k) for k in ('asof','state','dominant_scare','top_score')} for r in sorted(radar,key=lambda r:str(r.get('asof','')))[-6:]]
macro={kind:{'rows':len(rs),'latest_release_date':max((str(r.get('release_date','')) for r in rs),default=None)} for kind in sorted({str(r.get('row_type','')) for r in release}) for rs in [[r for r in release if str(r.get('row_type',''))==kind]]}
result={'observed_at':datetime.now(timezone.utc).isoformat(),'head':h,'as_of':as_of.isoformat(),'window_days':3,'sources':summary,'adapter_report':report,'recent_radar':recent_radar,'macro_rows':macro,'state_log_last_rows':state[-3:],'input_sha256':before,'head_after':head(),'inputs_unchanged':before==hashes(),'provider_calls':0,'runtime_writes':0,'source_or_rights_admission':False}
result['stable_head']=result['head_after']==h
assert result['stable_head'] and result['inputs_unchanged']
print(json.dumps(result,indent=2))
