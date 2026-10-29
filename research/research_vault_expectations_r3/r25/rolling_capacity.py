"""Disposable research model of rolling acquisition capacity, NOT a runtime allocator.

No network, credentials, collection, model call, purchase, or production mutation.
Uses an optimistic FIFO service control; production priority policy is not replayed.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Sequence
import numpy as np

@dataclass(frozen=True)
class Result:
    service: np.ndarray
    accounts: np.ndarray


def _after_outage(t: int, intervals: Sequence[tuple[int, int]]) -> int:
    for start, end in intervals:
        if start <= t < end:
            t = end
    return t


def simulate(arrivals: Sequence[int], accounts: int, cap: int = 70,
             window: int = 1440, outages: Sequence[tuple[int, int]] = (),
             cooldown: int = 0) -> Result:
    """Earliest FIFO service, per-account cap in (t-window,t].

    Capacity history is per account. Common outages delay all service. Ties prefer
    least-used account then stable index. Jobs are never dropped or expired.
    """
    if any(type(x) is not int or x <= 0 for x in (accounts, cap, window)):
        raise ValueError('accounts, cap and window must be positive integers')
    if type(cooldown) is not int or cooldown < 0:
        raise ValueError('cooldown must be a nonnegative integer')
    a = np.asarray(arrivals)
    if a.size and (a.ndim != 1 or not np.issubdtype(a.dtype, np.integer)):
        raise ValueError('arrival minutes must be integers')
    if a.size and (np.any(a < 0) or np.any(a[1:] < a[:-1])):
        raise ValueError('arrival minutes must be sorted and nonnegative')
    intervals = list(outages)
    if any(type(s) is not int or type(e) is not int or not (0 <= s < e)
           for s,e in intervals):
        raise ValueError('invalid outage interval')
    if intervals != sorted(intervals) or any(intervals[i][0] < intervals[i-1][1]
                                           for i in range(1,len(intervals))):
        raise ValueError('outages must be sorted and non-overlapping')
    history = [deque() for _ in range(accounts)]
    last = [-cooldown] * accounts
    service = np.empty(a.size,dtype=np.int64)
    used = np.empty(a.size,dtype=np.int64)
    cursor = 0
    for i,arrival in enumerate(a):
        now = max(int(arrival), cursor)
        choices=[]
        for k,q in enumerate(history):
            while q and q[0] <= now-window:
                q.popleft()
            candidate=max(now,last[k]+cooldown)
            if len(q) >= cap:
                candidate=max(candidate,q[0]+window)
            candidate=_after_outage(candidate,intervals)
            choices.append((candidate,len(q),k))
        when,_,account=min(choices)
        q=history[account]
        while q and q[0] <= when-window:
            q.popleft()
        if len(q) >= cap:
            raise AssertionError('internal rolling cap violation')
        q.append(when)
        last[account]=when
        cursor=when
        service[i]=when;used[i]=account
    return Result(service,used)


def make_arrivals(profile: dict, seed: int, daily_cv: float=0.0,
                  eligible: float=1.0, smooth: bool=False) -> np.ndarray:
    """Synthetic arrivals. Gamma shock has mean 1; Poisson adds count variation."""
    if not 0 < eligible <= 1 or not math.isfinite(daily_cv) or daily_cv<0:
        raise ValueError('invalid sensitivity input')
    rng=np.random.default_rng(seed)
    days=profile['arrival_days'];parts=[];cumulative=0.0
    for d in range(days):
        rates=profile['weekday'] if d%7<5 else profile['weekend']
        shock=rng.gamma(1/daily_cv**2,daily_cv**2) if daily_cv else 1.0
        for h,rate in enumerate(rates):
            if smooth:
                # Constant within-hour expected arrival mass, deterministic rounding.
                for minute in range(60):
                    previous=int(math.floor(cumulative+1e-10))
                    cumulative+=rate*eligible/60
                    count=int(math.floor(cumulative+1e-10))-previous
                    if count:parts.extend([d*1440+h*60+minute]*count)
            else:
                count=int(rng.poisson(rate*shock))
                # Independent thinning retains the same full-flow arrivals by seed.
                offsets=rng.integers(0,60,count)
                keep=rng.random(count)<eligible
                parts.extend((d*1440+h*60+offsets[keep]).tolist())
    return np.sort(np.asarray(parts,dtype=np.int64))


def summarize(arrivals: np.ndarray,result: Result,start: int,end: int) -> dict:
    mask=(arrivals>=start)&(arrivals<end)
    waits=result.service[mask]-arrivals[mask]
    within=lambda t:float(np.mean(waits<=t)*100) if len(waits) else None
    def backlog(t):
        return int(np.searchsorted(arrivals,t,side='right')-
                   np.searchsorted(result.service,t,side='right'))
    target=arrivals[mask]
    queue=(np.searchsorted(arrivals,target,side='right')-
           np.searchsorted(result.service,target,side='right')) if len(target) else np.array([0])
    return {'target_reports':int(mask.sum()),'within_1h_pct':within(60),
            'within_6h_pct':within(360),'within_24h_pct':within(1440),
            'within_48h_pct':within(2880),
            'p95_delay_hours':float(np.percentile(waits,95)/60) if len(waits) else None,
            'mean_delay_hours':float(np.mean(waits)/60) if len(waits) else None,
            'backlog_at_measurement_start':backlog(start),
            'backlog_at_measurement_end':backlog(end),
            'peak_waiting_backlog_in_window':int(max(queue.max(),backlog(start))),
            'backlog_change':backlog(end)-backlog(start)}


def run(profile: dict) -> dict:
    assert len(profile['weekday'])==len(profile['weekend'])==24
    assert math.isclose(sum(profile['weekday']),206.5,abs_tol=1e-8)
    assert math.isclose(sum(profile['weekend']),85.2,abs_tol=1e-8)
    start=profile['warmup_days']*1440
    end=start+profile['measurement_days']*1440
    scenarios=[
      {'name':'smooth_full_profile','smooth':True,'cv':0.,'eligible':1.},
      {'name':'poisson_full_profile','smooth':False,'cv':0.,'eligible':1.},
      {'name':'mild_variable_day_full_profile','smooth':False,'cv':.15,'eligible':1.},
      {'name':'variable_day_full_profile','smooth':False,'cv':.35,'eligible':1.},
      {'name':'high_variable_day_full_profile','smooth':False,'cv':.6,'eligible':1.},
      {'name':'poisson_80pct_eligible','smooth':False,'cv':0.,'eligible':.8},
      {'name':'variable_day_80pct_eligible','smooth':False,'cv':.35,'eligible':.8},
      {'name':'poisson_full_12h_common_outage','smooth':False,'cv':0.,'eligible':1.,
       'outages':[(start+5*60,start+17*60)]},
      {'name':'poisson_full_4min_spacing','smooth':False,'cv':0.,'eligible':1.,'cooldown':4},
    ]
    rows=[]
    for s in scenarios:
        seeds=profile['seeds'][:1] if s['smooth'] else profile['seeds']
        for seed in seeds:
            arr=make_arrivals(profile,seed,s['cv'],s['eligible'],s['smooth'])
            for n in (1,2,3,4):
                result=simulate(arr,n,profile['cap_per_account'],
                                profile['rolling_window_minutes'],s.get('outages',()),s.get('cooldown',0))
                rows.append({'scenario':s['name'],'seed':seed,'accounts':n,
                             **summarize(arr,result,start,end)})
    aggregates=[]
    for s in scenarios:
        for n in (1,2,3,4):
            group=[r for r in rows if r['scenario']==s['name'] and r['accounts']==n]
            metrics={}
            for k in ('target_reports','within_1h_pct','within_6h_pct','within_24h_pct','within_48h_pct',
                      'p95_delay_hours','mean_delay_hours','backlog_change','backlog_at_measurement_end',
                      'peak_waiting_backlog_in_window'):
                vals=np.array([g[k] for g in group],dtype=float)
                metrics[k]={'mean':float(vals.mean()),'min':float(vals.min()),'max':float(vals.max())}
            aggregates.append({'scenario':s['name'],'accounts':n,'trace_count':len(group),'metrics':metrics})
    return {'schema':'research_vault.rolling_capacity_study.r25',
            'state':'MODEL_SENSITIVITY_NOT_REAL_FEED_REPLAY',
            'observation_unit':'one synthetic 28-day measurement window after 28-day warmup',
            'common_random_trace_comparison':True,'confidence_intervals_claimed':False,
            'raw_rows':rows,'aggregates':aggregates,'scenarios':scenarios,
            'runtime_allocator_executed':False,'real_downloads':0,
            'scope':'Optimistic FIFO capacity control; not a fitted stochastic model or production performance guarantee.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,default=Path(__file__).with_name('capacity_inputs.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Refusing to overwrite existing result')
    raw=args.inputs.read_bytes();profile=json.loads(raw)
    result=run(profile)
    result['inputs_sha256']=hashlib.sha256(raw).hexdigest()
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['numpy_version']=np.__version__
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'traces':len(result['raw_rows']),'groups':len(result['aggregates']),
                      'output':str(args.output)},indent=2))
