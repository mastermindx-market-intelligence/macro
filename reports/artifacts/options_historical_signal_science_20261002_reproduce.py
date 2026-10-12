#!/usr/bin/env python3
"""Read-only reproduction artifact; never writes to the supplied Macro repo."""
import argparse, hashlib, json, math, statistics, subprocess, sys, tempfile, time
from collections import defaultdict
from pathlib import Path

COMMIT='dc4fd0766709188cba8d16a9fc16479c0e9c110f'
PROTOCOL_SHA256='ae3576837efdc66ef47d4cfdcf288c63a3b9938599c83d87d13c356af42b4ae8'
DATA=['data/options_signal_episode/episodes.jsonl','data/options_signal_episode/outcomes_h60.jsonl','data/options_signal_episode/outcomes_session.jsonl']
SOURCE=['engine/options_signal_episode.py','engine/options_signal_episode_contract.py','engine/ledger_lane.py','engine/session_digest.py','lib/nyse_calendar.py','contracts/options/options.signal_episode.v1.schema.json','contracts/options/options.signal_episode_outcome.v1.schema.json','contracts/options/options.signal_episode_session_outcome.v1.schema.json']
def run(*args, text=False): return subprocess.run(args,check=True,capture_output=True,text=text).stdout
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(repo,path): return run('git','-C',str(repo),'rev-parse',f'{COMMIT}:{path}',text=True).strip()
def show(repo,path): return run('git','-C',str(repo),'show',f'{COMMIT}:{path}')
def put(root,path,raw):
 p=root/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)
def rows(raw):
 if raw and not raw.endswith(b'\n'): raise ValueError('torn JSONL')
 return [json.loads(x) for x in raw.splitlines() if x]
def checked(fn, xs):
 start=time.monotonic(); errors=[]; total=0
 for i,x in enumerate(xs,1):
  try: fn(x)
  except Exception as e:
   total+=1
   if len(errors)<10: errors.append({'row':i,'error':f'{type(e).__name__}: {e}'})
 return {'rows':len(xs),'validated':len(xs)-total,'error_count':total,'error_samples':errors,'elapsed_seconds':round(time.monotonic()-start,3)}
def quantile(xs,q):
 xs=sorted(xs); pos=(len(xs)-1)*q; lo=int(pos); hi=min(lo+1,len(xs)-1)
 return xs[lo]+(xs[hi]-xs[lo])*(pos-lo)
def cell_stats(rs, episodes):
 vals=[r['underlying']['ret'] for r in rs]
 if not vals:return {'count':0,'mean':None,'median':None,'q10':None,'q90':None,'equal_session_mean':None,'eligible_session_count':0,'eligible_ticker_count':0}
 if not all(type(x) in (int,float) and not isinstance(x,bool) and math.isfinite(x) for x in vals): raise ValueError('non-finite return')
 by_session=defaultdict(list)
 for r in rs: by_session[episodes[r['episode_id']]['session_date']].append(r['underlying']['ret'])
 return {'count':len(vals),'mean':sum(vals)/len(vals),'median':statistics.median(vals),'q10':quantile(vals,.1),'q90':quantile(vals,.9),'equal_session_mean':sum(sum(v)/len(v) for v in by_session.values())/len(by_session),'eligible_session_count':len(by_session),'eligible_ticker_count':len({episodes[r['episode_id']]['ticker'] for r in rs})}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True,type=Path); ap.add_argument('--protocol',required=True,type=Path); a=ap.parse_args()
 if run('git','-C',str(a.repo),'rev-parse',f'{COMMIT}^{{commit}}',text=True).strip()!=COMMIT: raise ValueError('pinned commit unavailable')
 protocol_raw=a.protocol.read_bytes()
 if sha(protocol_raw)!=PROTOCOL_SHA256: raise ValueError('frozen protocol SHA-256 mismatch')
 protocol=json.loads(protocol_raw)
 if protocol.get('source_commit')!=COMMIT: raise ValueError('protocol source_commit mismatch')
 with tempfile.TemporaryDirectory(prefix='options-descriptive-dc4-') as td:
  root=Path(td); raw={}
  for path in DATA+SOURCE:
   b=show(a.repo,path); put(root,path,b)
   if path in DATA: raw[path]=b
  sys.path.insert(0,str(root))
  from engine.options_signal_episode import validate_episode,validate_outcome_against_episode,validate_session_outcome_against_episode
  eps,h60,sess=(rows(raw[p]) for p in DATA); ep={x['episode_id']:x for x in eps}
  if len(ep)!=len(eps): raise ValueError('duplicate episode IDs')
  validators={'episode_full_schema_and_semantics':checked(validate_episode,eps),'h60_full_schema_metric_evidence_and_episode_join':checked(lambda x:validate_outcome_against_episode(x,ep[x['episode_id']]),h60),'session_full_schema_metric_evidence_and_episode_join':checked(lambda x:validate_session_outcome_against_episode(x,ep[x['episode_id']]),sess)}
  if any(v['error_count'] for v in validators.values()): raise ValueError('full canonical validation failed')
  horizon={'h60':h60,**{h:[] for h in protocol['horizons'] if h!='h60'}}
  for r in sess: horizon[r['horizon']].append(r)
  cells=[]
  for h in protocol['horizons']:
   for s in protocol['strata']:
    members=[e for e in eps if s=='ALL' or e['contract']['right']==s]; ids={e['episode_id'] for e in members}; observed=[r for r in horizon[h] if r['episode_id'] in ids]
    if len({r['episode_id'] for r in observed}) != len(observed): raise ValueError(f'duplicate {h} outcome')
    complete=[r for r in observed if r['status']=='complete']; incomplete=[r for r in observed if r['status']=='incomplete']
    for r in complete:
     if r['label_authority']!='research_only' or r['option']['status']!='unavailable' or r['option']['ret'] is not None: raise ValueError('authority/option invariant')
    for aligned in protocol['alignment_strata']:
     eligible=[r for r in complete if r['measurement']['target_aligned'] is aligned]
     cells.append({'horizon':h,'stratum':s,'target_aligned':aligned,'all_source_episodes':len(ids),'outcome_rows_observed':len(observed),'complete':len(complete),'terminal_incomplete':len(incomplete),'absent_at_source_snapshot':len(ids)-len(observed),'complete_target_aligned':len(eligible),'statistics_decimal_underlying_proxy':cell_stats(eligible,ep)})
  pins={p:{'git_blob':blob(a.repo,p),'sha256':sha(show(a.repo,p))} for p in DATA+SOURCE}
  out={'schema':'options.science.episode_descriptive_reproduction/v1','source_commit':COMMIT,'protocol_sha256':sha(protocol_raw),'source_pins':pins,'validation_provenance':{'meaning':'Full validators check stored schema, clocks, retained price-evidence arithmetic, receipt fields and path commitments; they do not reopen/replay source price parquet or authenticate source-file bytes/digests.','validators':validators},'cells':cells}
  print(json.dumps(out,sort_keys=True,indent=2))
if __name__=='__main__': main()
