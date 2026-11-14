"""Bounded synthetic local compositor benchmark, not latency/production attestation."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import platform
import statistics
import time
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.market_navigator import Condition, Observation, Receipt, Scenario, compose


def benchmark(n: int = 200) -> dict:
    r=Receipt('fixture:benchmark','v1','2026-10-21T20:00:00Z','2026-10-21T20:00:01Z','2026-10-21T20:00:02Z','2026-10-21T20:05:00Z')
    rows=tuple(Observation(f'p{i}','SPY:ARCX','price',773.09,'USD',('intraday',),r) for i in range(128))
    scenarios=tuple(Scenario(key=f's{i}',subject='SPY:ARCX',horizon='intraday',
        definition_available_at='2026-10-21T19:00:00Z',definition_ref='fixture:benchmark-rule-v1',
        deadline='2026-10-21T20:04:00Z',triggers=tuple(Condition(f'p{j}','gt',770,'USD') for j in range(16)),
        invalidations=tuple(Condition(f'p{j}','lt',765,'USD') for j in range(16))) for i in range(12))
    kwargs=dict(subject='SPY:ARCX',horizon='intraday',as_of='2026-10-21T20:01:00Z',observations=rows,scenarios=scenarios)
    for _ in range(20): compose(**kwargs)
    timings=[]
    for _ in range(n):
        start=time.perf_counter(); result=compose(**kwargs)
        timings.append(1000*(time.perf_counter()-start))
    return {'schema':'market_navigator.local_benchmark/v1','evidence_class':'SYNTHETIC_LOCAL_COMPOSITION_ONLY',
        'python':platform.python_version(),'system':platform.system(),'machine':platform.machine(),
        'observations':128,'scenarios':12,'conditions_per_scenario':32,'runs':n,'warmup_runs':20,
        'median_ms':statistics.median(timings),'p95_ms':sorted(timings)[math.ceil(.95*n)-1],
        'max_ms':max(timings),'serialized_bytes':len(json.dumps(result).encode()),
        'includes_network_or_source_fetch':False,'production_latency_proven':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    result=benchmark();args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
