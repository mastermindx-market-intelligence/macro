#!/usr/bin/env python3
"""Exact B1 source relationship and committed RP1 coverage audit. No identity fabrication."""
import argparse,csv,hashlib,json,subprocess,collections,datetime
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--pin',default='731a23fb64b9f6f1a321c77618f927f1a58d2d41');p.add_argument('--boards',type=Path,required=True);p.add_argument('--baselines',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
manifest=[]
def read(path,lines=False):
    raw=subprocess.check_output(['git','-C',a.repo,'show',a.pin+':'+path])
    manifest.append(dict(pin=a.pin,path=path,git_blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    return [json.loads(x) for x in raw.splitlines() if x.strip() and not x.lstrip().startswith(b'#')] if lines else json.loads(raw)
head=read('data/us_prophet_rank/episodes/HEAD.json');prefix='data/us_prophet_rank/episodes/generations/'+head['generation_id']+'/'
gm=read(prefix+'manifest.json');registry=read(prefix+'all_candidates.json');receipt=read(prefix+'latest_receipt.json')
events=[];suppressions=[]
for n in gm['files']:
    if n.startswith('events/'):events+=read(prefix+n,True)
    if n.startswith('suppressions/'):suppressions+=read(prefix+n,True)
for r in manifest:
    if r['path'].startswith(prefix) and r['path'][len(prefix):] in gm['files']:
        expected=gm['files'][r['path'][len(prefix):]]['sha256'].removeprefix('sha256:')
        assert r['sha256']==expected, (r['path'],'generation digest mismatch')
episodes={r['episode_id']:r for r in registry['episodes']}
bykey=collections.defaultdict(lambda:dict(events=[],suppressions=[]))
def sourcekey(r):
    # Parse an EXISTING source-event ID; do not manufacture candidate or episode IDs.
    sid=r.get('source_event_id','')
    if not sid.startswith('candidate:'):return None
    x=sid.split(':')
    return tuple(x[1:4]) if len(x)==4 else None
for e in events:
    k=sourcekey(e)
    if k:bykey[k]['events'].append(e)
for s in suppressions:
    k=sourcekey(s)
    if k:bykey[k]['suppressions'].append(s)
def relation(date,ticker,definition,cut=None):
    rows=bykey.get((date,ticker,definition),dict(events=[],suppressions=[]))
    accepted=[e for e in rows['events'] if e.get('episode_id') in episodes]
    ids=sorted(set(e['episode_id'] for e in accepted))
    reasons=sorted(set(s['reason'] for s in rows['suppressions']))
    if len(ids)==1:state='PRESENT'
    elif len(ids)>1:state='UNAVAILABLE_AMBIGUOUS_CANONICAL_RELATION'
    elif 'MISSING_STRUCTURAL_ANCHOR' in reasons:state='NOT_YET_ANCHORED'
    elif reasons:state='UNAVAILABLE_'+','.join(reasons)
    else:state='UNAVAILABLE_NO_EXACT_SOURCE_RELATION'
    earliest=min((e['recorded_at'] for e in accepted),default=None)
    atcut=None
    if cut and earliest:
        atcut=datetime.datetime.fromisoformat(earliest.replace('Z','+00:00'))<=datetime.datetime.fromisoformat(cut.replace('Z','+00:00'))
    return dict(b1_state=state,canonical_episode_ids=ids,source_event_ids=sorted(set(e['source_event_id'] for e in accepted)|set(s['source_event_id'] for s in rows['suppressions'])),
        suppression_reasons=reasons,first_relation_recorded_at=earliest,relation_recorded_by_selected_board_commit=atcut)
bs=json.loads(a.boards.read_text());bydate={b['as_of']:b for b in bs}
baselines=list(csv.DictReader(a.baselines.open()))
rels=[]
for e in baselines:
    b=bydate[e['as_of']];r=relation(e['as_of'],e['ticker'],e['board_definition'],e['source_commit_at'])
    pool=(b.get('candidate_pool') or {}).get('rows')
    rels.append(dict(ticker=e['ticker'],as_of=e['as_of'],board_source_sha256=e['source_sha256'],
        b03_pool_existed_at_selected_snapshot=pool is not None,b03_pool_contains_at_selected_snapshot=any(x.get('ticker')==e['ticker'] for x in pool) if pool is not None else None,
        later_valid_confirmation=bool(e['first_valid_confirmation']),**r))
pools=[];pool_relations=[]
for b in bs:
    pool=(b.get('candidate_pool') or {}).get('rows')
    if pool is None:continue
    rows=[]
    for r in pool:
        rel=relation(b['as_of'],r['ticker'],b.get('board_definition'),b['source_commit_at'])
        rows.append(dict(as_of=b['as_of'],ticker=r['ticker'],pool_lane=r.get('lane'),pool_rank=r.get('pool_rank'),**rel))
    counts=collections.Counter(r['b1_state'] for r in rows)
    pools.append(dict(as_of=b['as_of'],pool_rows=len(rows),definition=b.get('board_definition'),counts=dict(counts),
        eligible=(b.get('candidate_pool') or {}).get('eligible'),source_sha256=b['source_sha256']))
    pool_relations+=rows
rp1=read('data/entry_radar/ledger_state.json')
def rpobjects(o):
    if isinstance(o,dict):
        if o.get('schema')=='mastermind.research_priority.v1':yield o
        for v in o.values():yield from rpobjects(v)
    elif isinstance(o,list):
        for v in o:yield from rpobjects(v)
rp1_count=sum(1 for b in bs for _ in rpobjects(b))
out=dict(pin=a.pin,generation_id=head['generation_id'],generation_manifest_sha256=manifest[1]['sha256'],canonical_episode_count=len(episodes),
    latest_reconcile_receipt=receipt,exposed_baseline_count=len(rels),exposed_relation_counts=dict(collections.Counter(r['b1_state'] for r in rels)),
    exposed_b03_pool_present=sum(r['b03_pool_contains_at_selected_snapshot'] is True for r in rels),
    exposed_b03_pool_historical_unavailable=sum(r['b03_pool_existed_at_selected_snapshot'] is False for r in rels),
    exposed_relation_recorded_by_selected_commit=sum(r['relation_recorded_by_selected_board_commit'] is True for r in rels),
    relation_outcome_association={s:{'n':len(xs),'later_observed_valid_confirmations':sum(r['later_valid_confirmation'] for r in xs)} for s in sorted(set(r['b1_state'] for r in rels)) for xs in [[r for r in rels if r['b1_state']==s]]},
    pool_coverage=pools,rp1_committed_ledger_state=rp1,rp1_exact_objects_in_selected_board_snapshots=rp1_count,
    rp1_empirical_orthogonality={'status':'NOT_ESTIMABLE_NO_EXACT_JOINABLE_RP1_OBJECTS','observed_correlation':None,'not_assumed_zero':True},
    cautions=['B1 relation is exact source-event to accepted canonical episode, not ticker/date episode synthesis.',
       'Current registry can prove a later exact relation; it is not proof that relation existed at historical decision cut.',
       'UNAVAILABLE does not mean NOT_YET_ANCHORED; only explicit MISSING_STRUCTURAL_ANCHOR supports that classification.',
       'No exact source-event relation means missing coverage, not absence of an episode elsewhere.',
       'No live runtime was queried and no runtime RP1 absence is asserted beyond these committed artifacts.'])
def csvwrite(name,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (a.out/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()})
csvwrite('b1_emergence_relations.csv',rels);csvwrite('b03_pool_b1_relations.csv',pool_relations);csvwrite('b1_rp1_source_manifest.csv',manifest)
(a.out/'b1_rp1_coverage_summary.json').write_text(json.dumps(out,indent=2,sort_keys=True))
print(json.dumps({k:out[k] for k in ['canonical_episode_count','exposed_baseline_count','exposed_relation_counts','exposed_b03_pool_present','exposed_b03_pool_historical_unavailable','exposed_relation_recorded_by_selected_commit','relation_outcome_association','rp1_exact_objects_in_selected_board_snapshots']},indent=2))
print('pool coverage',json.dumps(pools))

