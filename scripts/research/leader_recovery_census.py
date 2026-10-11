"""Read-only source census; explicit research output only, never data/site writes.

Run: python -m scripts.research.leader_recovery_census --out /tmp/recovery.json
The current membership and current adjusted price vintages are NOT historical PIT.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.leader_recovery import RecoverySpec, describe_recovery, replay_recovery
from engine.leader_recovery_outcomes import label_recovery_outcome
from lib import config
from lib.nyse_calendar import sessions_between
from scripts.build_leader_radar import _resolve_universe, _load_spy, _load_ohlcv


def run(*, data_root: Path, study_start: date, extras: tuple[str, ...] = ()) -> dict:
    started = time.monotonic()
    universe, _ = _resolve_universe(data_root, config.load())
    spy = _load_spy(data_root)
    if spy is None or spy.empty:
        raise ValueError('benchmark_unavailable')
    cut = spy.index.max().date()
    cal = sessions_between(spy.index.min().date(), cut)
    spec = RecoverySpec()
    events, current, missing, source_hashes = [], [], [], {}
    selected = sorted(set(universe) | set(extras))
    wanted = {'DAMAGED','REBUILDING','REIGNITING','FAILED_REPAIR'}
    for ticker in selected:
        bars = _load_ohlcv(ticker, data_root)
        if bars is None:
            missing.append(ticker)
            continue
        close = bars['close']
        descriptor = describe_recovery(close, spy, as_of=cut, sessions=cal,
                                       source_ref=f'data/baskets/ohlcv/{ticker}.parquet')
        source_hashes[ticker] = descriptor['source_fingerprint_sha256']
        current.append({'ticker':ticker,'state':descriptor['state'],
                        'entry_context':descriptor['entry_context'],
                        'episode':descriptor['episode'],'transitions':descriptor['transitions']})
        rows = replay_recovery(close, spy, as_of=cut, sessions=cal)
        seen = set()
        for row in rows:
            ep = row.get('episode')
            if row['as_of'] < study_start.isoformat() or row['state'] not in wanted or not ep:
                continue
            key = (ep['peak_on'], row['state'])
            if key in seen:
                continue
            seen.add(key)
            day = date.fromisoformat(row['as_of'])
            i = cal.index(day)
            stop = cal[min(i + 63, len(cal)-1)]
            for horizon in (21,63):
                result = label_recovery_outcome(
                    close.loc[str(day):str(stop)], spy.loc[str(day):str(stop)],
                    descriptor=row,sessions=cal,horizon=horizon,available_through=cut)
                events.append({'ticker':ticker,'state':row['state'],
                               'peak_on':ep['peak_on'],'decision_on':row['as_of'],
                               'legacy_episode':ep['peak_on'] < study_start.isoformat(),
                               **result})
    cells = defaultdict(list)
    for event in events:
        cells[(event['state'],event['horizon_sessions'])].append(event)
    summary=[]
    for (state,horizon), members in sorted(cells.items()):
        completed=[r for r in members if r['status']=='COMPLETE']
        summary.append({'state':state,'horizon_sessions':horizon,'n_total':len(members),
                        'n_complete':len(completed),'n_tickers':len({r['ticker'] for r in members}),
                        'status_counts':dict(Counter(r['status'] for r in members)),
                        'event_status_counts':dict(Counter(r['event_status'] for r in members)),
                        'n_event_observed':sum(r['event_status']=='OBSERVED' for r in completed),
                        'first_event_counts':dict(Counter(r['first_event'] for r in completed if r['first_event'] is not None)),
                        'legacy_episode_count':sum(r['legacy_episode'] for r in members),
                        'median_excess_return':statistics.median(r['excess_return'] for r in completed) if completed else None,
                        'median_mae_close':statistics.median(r['mae_close'] for r in completed) if completed else None,
                        'median_mfe_close':statistics.median(r['mfe_close'] for r in completed) if completed else None})
    return {'schema':'leader_recovery_census.v1','source_cut':str(cut),
            'study_start':str(study_start),'definition_sha256':spec.digest,
            'code_sha256':hashlib.sha256(Path(__import__('engine.leader_recovery',fromlist=['x']).__file__).read_bytes()).hexdigest(),
            'outcome_code_sha256':hashlib.sha256(Path(__import__('engine.leader_recovery_outcomes',fromlist=['x']).__file__).read_bytes()).hexdigest(),
            'membership_basis':'CURRENT_SURVIVOR_UNIVERSE_NOT_PIT',
            'n_incumbent_universe':len(universe),'extras':list(extras),'missing':missing,
            'n_current':len(current),'state_counts':dict(Counter(r['state'] for r in current)),
            'summary':summary,'cases':current,'events':events,'source_hashes':source_hashes,
            'limits':['not historical first-seen','not delisting-complete','overlapping correlated events',
                      'not a causal timing comparison','no transaction costs','no predictive qualification',
                      'current source corrections may revise reconstructed history','close-only outcomes'],
            'elapsed_seconds':round(time.monotonic()-started,3)}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--study-start',type=date.fromisoformat,default=date(2024,1,1))
    parser.add_argument('--extra',default='PYPL,DOCU,PTON,UPST,INTC')
    args=parser.parse_args()
    if any(p in {'data','site','site_full'} for p in args.out.parts):
        raise ValueError('research_must_not_write_operational_store')
    result=run(data_root=config.data_dir(),study_start=args.study_start,
               extras=tuple(x.strip() for x in args.extra.split(',') if x.strip()))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in {'cases','events','source_hashes'}},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
