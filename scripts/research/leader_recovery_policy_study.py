"""Exploratory policy study: one first-damaged landmark per ticker/episode/month.

Uses current-survivor membership and current adjusted prices, not historical PIT.
Same endpoint, next-close observation delay, all no-entry cases, and explicit costs.
Run: python -m scripts.research.leader_recovery_policy_study --out /tmp/policy.json
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from datetime import date
import hashlib,json,statistics,sys,time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.leader_recovery import RecoverySpec,replay_recovery,_source
from engine.leader_recovery_policy_research import compare_at_landmark,POLICIES
from lib import config
from lib.nyse_calendar import sessions_between
from scripts.build_leader_radar import _resolve_universe,_load_spy,_load_ohlcv


def study(*,as_of:date|None=None,start:date=date(2024,1,1)) -> dict:
    began=time.monotonic();root=config.data_dir();universe,_=_resolve_universe(root,config.load())
    extras=['PYPL','PTON','DOCU','UPST','INTC'];names=sorted(set(universe)|set(extras))
    spy=_load_spy(root)
    if spy is None or spy.empty:raise ValueError('benchmark_missing')
    cut=as_of or spy.index.max().date()
    if cut>spy.index.max().date():raise ValueError('requested_cut_not_available')
    cal=sessions_between(spy.index.min().date(),cut);bench=_source(spy,cut);spec=RecoverySpec()
    records=[];failed=[];fingerprints={};landmark_count=0
    for ticker in names:
        bars=_load_ohlcv(ticker,root)
        if bars is None:failed.append(ticker);continue
        close=bars['close'];prices=_source(close,cut)
        fingerprints[ticker]=hashlib.sha256(json.dumps([(str(k),v) for k,v in sorted(prices.items())],sort_keys=True).encode()).hexdigest()
        replay=replay_recovery(close,spy,as_of=cut,sessions=cal,spec=spec)
        observations={date.fromisoformat(row['as_of']):row for row in replay}
        seen=set();landmarks=[]
        for row in replay:
            ep=row.get('episode') or {};day=date.fromisoformat(row['as_of'])
            if day<start or row['state']!='DAMAGED' or not ep:continue
            key=(ep['opened_on'],row['as_of'][:7])
            if key in seen:continue
            seen.add(key);landmarks.append(day)
        landmark_count+=len(landmarks)
        for day in landmarks:
            for horizon in (21,63,126):
                for cost in (20.,50.):
                    results=compare_at_landmark(prices,bench,observations,sessions=cal,landmark=day,
                        horizon=horizon,available_through=cut,round_trip_cost_bps=cost,spec=spec)
                    for row in results:row['ticker']=ticker;records.append(row)
    groups=defaultdict(list)
    for row in records:groups[(row['horizon_sessions'],row['round_trip_cost_bps'],row['policy'])].append(row)
    summary=[]
    for (horizon,cost,policy),rows in sorted(groups.items()):
        complete=[x for x in rows if x['status']=='COMPLETE']
        entered=[x for x in complete if x['entry_status']=='ENTERED']
        summary.append({'horizon_sessions':horizon,'cost_bps':cost,'policy':policy,
            'n':len(rows),'n_complete':len(complete),'n_tickers':len({x['ticker'] for x in complete}),
            'status_counts':dict(Counter(x['status'] for x in rows)),
            'entry_rate':len(entered)/len(complete) if complete else None,
            'median_net_return':statistics.median(x['net_return'] for x in complete) if complete else None,
            'median_excess_spy_common_endpoint':statistics.median(x['excess_common_endpoint'] for x in complete) if complete else None,
            'median_mae_all':statistics.median(x['mae_close'] for x in complete) if complete else None,
            'median_mae_entered':statistics.median(x['mae_close'] for x in entered) if entered else None,
            'mean_time_in_market':statistics.mean(x['held_sessions']/horizon for x in complete) if complete else None})
    lookup={(x['ticker'],x['landmark'],x['horizon_sessions'],x['round_trip_cost_bps'],x['policy']):x for x in records}
    paired=[]
    for horizon in (21,63,126):
        for cost in (20.,50.):
            for treatment in ('repair','reignition'):
                for control in ('immediate','wait_5','wait_10','ma50_only'):
                    pairs=[]
                    for x in groups[(horizon,cost,treatment)]:
                        key=(x['ticker'],x['landmark'],horizon,cost,control);other=lookup[key]
                        if x['status']=='COMPLETE' and other['status']=='COMPLETE':
                            pairs.append((x['ticker'],x['landmark'][:4],x['net_return']-other['net_return'],x['mae_close']-other['mae_close']))
                    if not pairs:continue
                    by_issuer=defaultdict(list)
                    for t,y,delta,mae in pairs:by_issuer[t].append(delta)
                    paired.append({'horizon_sessions':horizon,'cost_bps':cost,'treatment':treatment,'control':control,
                        'n_pairs':len(pairs),'n_issuers':len(by_issuer),
                        'median_paired_return_delta':statistics.median(x[2] for x in pairs),
                        'mean_paired_return_delta':statistics.mean(x[2] for x in pairs),
                        'median_paired_mae_improvement':statistics.median(x[3] for x in pairs),
                        'equal_issuer_mean_return_delta':statistics.mean(statistics.mean(v) for v in by_issuer.values()),
                        'year_median_deltas':{y:statistics.median(x[2] for x in pairs if x[1]==y) for y in sorted({x[1] for x in pairs})}})
    return {'schema':'leader_recovery_policy_study.v1','source_cut':str(cut),'start':str(start),
        'n_names':len(names),'failed_sources':failed,'n_landmarks':landmark_count,'record_count':len(records),
        'landmark_rule':'first observed DAMAGED day per ticker, episode, calendar month; no future filters',
        'membership_basis':'CURRENT_SURVIVOR_UNIVERSE_NOT_PIT','source_fingerprints':fingerprints,
        'definition_sha256':spec.digest,
        'policy_code_sha256':hashlib.sha256(Path(__import__('engine.leader_recovery_policy_research',fromlist=['x']).__file__).read_bytes()).hexdigest(),
        'core_code_sha256':hashlib.sha256(Path(__import__('engine.leader_recovery',fromlist=['x']).__file__).read_bytes()).hexdigest(),
        'summary':summary,'paired':paired,
        'pltr_landmarks':[x for x in records if x['ticker']=='PLTR' and x['round_trip_cost_bps']==20 and x['horizon_sessions']==63],
        'records':records,'elapsed_seconds':round(time.monotonic()-began,3),
        'limitations':['exploratory definitions chosen after example was known','survivor and current-vintage bias',
            'overlapping correlated monthly landmarks','cash return assumed zero','next-close references are not executable fill proof',
            'costs are scenarios, not observed quotes','no causal or prospective predictive qualification',
            'source rights and delisted historical membership not newly qualified']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--as-of',type=date.fromisoformat);args=parser.parse_args()
    if any(p in {'data','site','site_full'} for p in args.out.parts):raise ValueError('research_output_only')
    result=study(as_of=args.as_of);args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    summary={k:v for k,v in result.items() if k not in {'records','source_fingerprints'}}
    summary['full_result_sha256']=hashlib.sha256(args.out.read_bytes()).hexdigest()
    args.out.with_name('POLICY_SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False))
    print(json.dumps({k:v for k,v in summary.items() if k not in {'summary','paired','pltr_landmarks'}},indent=2))


if __name__=='__main__':main()
