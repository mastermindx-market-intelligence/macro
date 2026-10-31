"""Read scoped retained metering only. No dispatch, ledger or session writes."""
from pathlib import Path
import datetime, hashlib, json
ROOT='01a13300-c75b-79c3-83f9-79b3b4c01dc7'
OUT=Path(__file__).resolve().parent
native=[]
for day in ('12','13','14'):
 for p in Path('/Users/chriswong/.codex/sessions/2026/10/'+day).glob('*.jsonl'):
  try:
   with p.open() as f:m=json.loads(next(f))['payload']
  except (OSError,ValueError,KeyError,StopIteration):continue
  if m.get('id')!=ROOT and m.get('session_id')!=ROOT and m.get('parent_thread_id')!=ROOT:continue
  models=set();usage=None;usage_at=None
  for line in p.open():
   try:x=json.loads(line)
   except ValueError:continue
   if x.get('type')=='turn_context':
    q=x.get('payload',{});models.add((q.get('model'),q.get('effort') or q.get('reasoning_effort')))
   if x.get('type')=='event_msg' and x.get('payload',{}).get('type')=='token_count':
    usage=(x['payload'].get('info') or {}).get('total_token_usage');usage_at=x.get('timestamp')
  native.append({'thread_id':m.get('id'),'parent_thread_id':m.get('parent_thread_id'),'role':m.get('agent_role'),'agent_path':m.get('agent_path'),'observed_models_and_effort':sorted(models),'usage_observed_at':usage_at,'total_token_usage':usage})
ledger=Path('/Users/chriswong/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/orch/fabric/ledger.jsonl')
latest={};metered={};rows=0
for line in ledger.open():
 try:x=json.loads(line)
 except ValueError:continue
 if x.get('root_id')==ROOT:
  rows+=1
  latest[x['run_id']]=x
  if type(x.get('tokens')) is int and x['tokens']>=0:metered[x['run_id']]=x
fields=('run_id','root_id','parent_run_id','kind','pool','model','rc','signal','accepted_by','review_rejected','scope_violation','wall_s','tokens','input_tokens','cached_tokens','output_tokens','credits','usage_source','ts')
fabric=[{k:x.get(k) for k in fields} for x in latest.values()]
accepted=[x for x in fabric if x.get('accepted_by') in ('reviewer','deterministic') and x.get('review_rejected') is not True]
known=list(metered.values())
keys=('input_tokens','cached_input_tokens','cache_write_input_tokens','output_tokens','reasoning_output_tokens','total_tokens')
totals={k:sum((x.get('total_token_usage') or {}).get(k,0) for x in native) for k in keys}
receipt={'schema':'defense_retained_cost_observation.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_root':ROOT,'capture_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_head':__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),'native_sessions':sorted(native,key=lambda x:x['thread_id']),'native_observed_totals':totals,'fabric_scoped_ledger_rows':rows,'fabric_unique_observed_runs':sorted(fabric,key=lambda x:x['run_id']),'metered_execution_observations':[{k:x.get(k) for k in fields} for x in sorted(known,key=lambda x:x['run_id'])],'fabric_summary':{'unique_runs_with_ledger_rows':len(fabric),'accepted_runs':len(accepted),'usage_known_runs':len(known),'usage_unknown_runs':len(fabric)-len(known),'known_total_tokens':sum(x['tokens'] for x in known),'wall_s_sum_observed_once_per_run':sum(x['wall_s'] for x in fabric if isinstance(x.get('wall_s'),(int,float))),'usd_total':None,'effective_usd_per_accepted_outcome':None},'limitations':['Snapshot is incomplete while work continues; missing original-run ledger records and unsettled effects are not zero cost.','Latest outcome row and latest metered execution observation are retained separately per stable run; reviewer rows cannot erase observed usage. Each run is counted once; no acceptance inferred from process exit.','Native token counters are observed cumulative usage, including cached input; reasoning output is a subset, not an additive charge.','Actual contracted billing, provider usage for unmetered runs, local compute, source licensing and installed serve distributions remain unavailable.','No current pricing estimate or model default is substituted for an actual invoice or missing metering.','Native lineage is read from session metadata and model/effort from actual turn_context; role labels alone are not model evidence.'],'mission_complete':False}
(OUT/'OBSERVATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'native_sessions':len(native),'native_totals':totals,'fabric_summary':receipt['fabric_summary'],'receipt_sha256':hashlib.sha256((OUT/'OBSERVATION.json').read_bytes()).hexdigest()}))
