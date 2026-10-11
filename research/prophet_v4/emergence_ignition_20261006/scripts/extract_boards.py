#!/usr/bin/env python3
"""Extract compact immutable discovery board histories. Read Git; write isolated output only."""
import argparse, subprocess, json, hashlib, datetime, collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--pin',default='731a23fb64b9f6f1a321c77618f927f1a58d2d41');p.add_argument('--out',required=True);a=p.parse_args()
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
PATH='site/factordata/us_standouts.json'
def git(*args): return subprocess.check_output(['git','-C',a.repo,*args])
def get(d,*ks):
 for k in ks:
  if not isinstance(d,dict): return None
  d=d.get(k)
 return d
def compact(r):
 c={k:v for k,v in r.items() if k not in ['spark_svg','dossier','conviction','entry_signal'] and not k.endswith('_zh')}
 cv=r.get('conviction') or {}; es=r.get('entry_signal') or {}
 c['conviction']={k:cv.get(k) for k in ['score','composite_z','score_edge','score_timing','rank_pctile','regime','risk','alignment','axes','spotlight','gex_confirm','iv_spread_confirm']}
 c['entry_signal']={k:es.get(k) for k in ['status','act_level','confluence_gated','buy_zone','chase_above','stop','spot','atr_pct']}
 return c
logs=git('log','--since=2026-08-01','--format=%H %cI',a.pin,'--',PATH).decode().splitlines()
variants=[]; bad=[]
for line in logs:
 sha,at=line.split()
 try:
  raw=git('show',sha+':'+PATH);b=json.loads(raw)
 except (subprocess.CalledProcessError,json.JSONDecodeError) as e:
  bad.append({'sha':sha,'error':str(e)});continue
 date=str(b.get('as_of',''))
 if not ('2026-08-01'<=date<='2026-10-06'): continue
 v={k:b.get(k) for k in ['as_of','rank_by','board_definition','ranking','staleness','emit','eligible','universe','candidate_pool','lane_counts','dispersion_regime']}
 for lane in ['buy','watch','leaders','laggards','ran']: v[lane]=[compact(r) for r in b.get(lane,[]) if isinstance(r,dict)]
 v.update({'source_commit':sha,'source_commit_at':at,'source_blob':hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest(),'source_sha256':hashlib.sha256(raw).hexdigest()})
 variants.append(v)
print('extracted variants',len(variants),'dates',len(set(v['as_of'] for v in variants)),flush=True)
bydate=collections.defaultdict(list)
for v in variants: bydate[v['as_of']].append(v)
latest=[];first=[]
for d,vs in sorted(bydate.items()):
 vs.sort(key=lambda v:(datetime.datetime.fromisoformat(v['source_commit_at']),v['source_commit']))
 latest.append(vs[-1]);first.append(vs[0])
manifest=[{k:v[k] for k in ['as_of','rank_by','source_commit','source_commit_at','source_blob','source_sha256']} for v in variants]
for n,o in [('boards_latest',latest),('boards_first',first),('board_source_manifest',manifest)]:
 (out/(n+'.json')).write_text(json.dumps(o,sort_keys=True,separators=(',',':')))
summary={'pin':a.pin,'source_path':PATH,'variants':len(variants),'dates':len(bydate),'dates_v3':[v['as_of'] for v in latest if v['rank_by']=='us_prophet_v3'],'versions_by_date':{d:len(v) for d,v in sorted(bydate.items())},'bad':bad}
(out/'extraction_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))

