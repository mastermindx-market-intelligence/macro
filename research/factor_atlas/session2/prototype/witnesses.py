"""Finite original synthetic witnesses and a local resource measurement.

This CLI uses only fabricated prices. It neither reads a feed nor establishes
market accuracy, entitlement, archival availability, or production capacity.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import resource
import sys
import time
import numpy
import scipy
from pressure import Bar, Segment, BVCConfig, bvc_series, digest

T = 1780320600

def identifiability_witness() -> dict:
    segment=Segment('2026-06-01','RTH',T,T+390*60,'SYNTHETIC_CALENDAR','FULL')
    prices=(100.,101.,100.,102.,101.)
    bars=[]; tape_a=[]; tape_b=[]
    for i,close in enumerate(prices):
        prints=[(close-.02,100.),(close+.02,150.),(close,200.)]
        for j,(p,size) in enumerate(prints):
            ts=(T+i*60+10+j*10)*1000
            tape_a.append(dict(trade_ms=ts,quote_ms=ts-200,price=p,size=size,bid=p-.02,ask=p))
            tape_b.append(dict(trade_ms=ts,quote_ms=ts-200,price=p,size=size,bid=p,ask=p+.02))
        volume=sum(q for p,q in prints); vwap=sum(p*q for p,q in prints)/volume
        bars.append(Bar('SYNTHETIC:A',segment,T+i*60,T+(i+1)*60,T+(i+1)*60+2,
                        close,volume,vwap,'unadjusted/USD','SYNTHETIC_REV','SYNTHETIC_RIGHTS'))
    # Explicit hypothetical best-quote benchmark; not a generic production signer.
    assert all(x['price']==x['ask'] for x in tape_a)
    assert all(x['price']==x['bid'] for x in tape_b)
    common=lambda tape:[(x['trade_ms'],x['price'],x['size']) for x in tape]
    a=bvc_series(bars,BVCConfig(min_returns=2),cutoff_utc_s=T+302)
    b=bvc_series(tuple(bars),BVCConfig(min_returns=2),cutoff_utc_s=T+302)
    gross=math.fsum(x['price']*x['size'] for x in tape_a)
    return dict(source='SYNTHETIC',empirical_accuracy_measured=False,
                n_trades=len(tape_a),n_bars=len(a),all_quote_ages_ms=200,
                bar_input_equal=common(tape_a)==common(tape_b),bar_pressure_equal=a==b,
                gross_usd=gross,quote_net_a_usd=gross,quote_net_b_usd=-gross,
                available_bvc_net_usd=math.fsum(x.net_usd for x in a if x.net_usd is not None),
                unclassified_bvc_bars=sum(x.net_usd is None for x in a),
                identical_prints_sha256=digest(common(tape_a)),
                bar_pressure_sha256=digest([asdict(x) for x in a]),
                conclusion='OHLCV and VWAP alone do not identify aggressor-side notional.')


def mechanical_benchmark(names: int=30) -> dict:
    if not 1<=names<=100:
        raise ValueError('bounded_synthetic_names_required')
    start=T-330*60
    segments=(Segment('2026-06-01','PRE',start,T,'SYNTHETIC_CALENDAR','FULL'),
              Segment('2026-06-01','RTH',T,T+390*60,'SYNTHETIC_CALENDAR','FULL'),
              Segment('2026-06-01','AH',T+390*60,T+630*60,'SYNTHETIC_CALENDAR','FULL'))
    bars=[]
    for n in range(names):
        for segment in segments:
            for j,t in enumerate(range(segment.start_utc_s,segment.end_utc_s,60)):
                c=100.+n+math.sin(j*.17+n)*.8+j*.0002
                bars.append(Bar(f'SYNTHETIC:{n:04d}',segment,t,t+60,t+62,c,
                    1000.+(j*71+n*17)%2000,None,'unadjusted/USD','SYNTHETIC_REV','SYNTHETIC_RIGHTS'))
    before=time.perf_counter()
    result=bvc_series(bars,BVCConfig(),cutoff_utc_s=T+630*60+2)
    elapsed=time.perf_counter()-before
    h=digest([asdict(x) for x in result])
    # Complete reversed-input replay also proves the deterministic sorting boundary.
    replay=bvc_series(reversed(bars),BVCConfig(),cutoff_utc_s=T+630*60+2)
    replay_hash=digest([asdict(x) for x in replay])
    assert h==replay_hash
    compact=[[b.security_id,b.start_utc_s,b.end_utc_s,b.available_at_utc_s,b.close,b.volume,b.vwap,
              b.segment.phase,b.source_revision] for b in bars]
    raw=json.dumps(compact,separators=(',',':'),allow_nan=False).encode()
    compressed=gzip.compress(raw,mtime=0)
    return dict(source='SYNTHETIC',measured_at_utc=datetime.now(timezone.utc).isoformat(),
        python=platform.python_version(),platform=platform.platform(),numpy=numpy.__version__,scipy=scipy.__version__,
        names=names,slots_per_name=960,rows=len(bars),bvc_seconds=elapsed,rows_per_second=len(bars)/elapsed,
        peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        rss_scope='whole process after input/output/replay/serialization; Linux KiB; not incremental kernel RAM',
        compact_json_bytes=len(raw),compact_gzip_bytes=len(compressed),
        gzip_bytes_per_row=len(compressed)/len(bars),
        compact_row_schema=['security_id','start_utc_s','end_utc_s','available_at_utc_s','close','volume','vwap','phase','source_revision'],
        production_schema_complete=False,parquet_or_vendor_compression_measured=False,
        output_sha256=h,reversed_input_sha256=replay_hash,replay_equal=h==replay_hash,
        source_sha256=hashlib.sha256(Path(__file__).with_name('pressure.py').read_bytes()).hexdigest(),
        benchmark_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        authority={'may_publish':False,'may_trade':False,'may_start_daemon':False})


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark',action='store_true')
    parser.add_argument('--names',type=int,default=30)
    args=parser.parse_args()
    result=mechanical_benchmark(args.names) if args.benchmark else identifiability_witness()
    print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))

if __name__=='__main__':
    main()
