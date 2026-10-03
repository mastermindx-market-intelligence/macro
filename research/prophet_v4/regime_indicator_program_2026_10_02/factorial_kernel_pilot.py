"""Exploratory follow-on only: fixed input x kernel policies, no promotion.

See KERNEL_FACTORIAL_SPEC.md. The original pilot's events are reused without
recalculation; only price+B and RSI+A are added. No new datasets are allowed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import etf_mechanism_pilot as pilot

PARENT_SHA = 'ce0abe8268301b7f3ac9dee5dc6807e79d1644dd689007b29b2195197a402b9e'
PILOT_CODE_SHA = '11aca84c03bb6ffed4baedba35c81048d918aeff79379f5e484933b468f87abf'
SPEC_COMMIT = '3ebbf18df3e1f359e08df1f6690409aa7247fa3c'
KERNELS = {'A': (12,26,9), 'B': (14,60,5)}
POLICIES = (('A','price_macd'),('B','price_macd'),('A','rsi_macd'),('B','rsi_macd'))


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def read_parent(path: Path) -> dict:
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PARENT_SHA:
        raise ValueError('parent bytes do not match the frozen pilot')
    parent=json.loads(raw)
    if parent['source_commit']!=pilot.SOURCE or any(parent['authority'].values()):
        raise ValueError('parent source or authority mismatch')
    return parent


def require_sources(expected: dict, actual: dict) -> None:
    if actual!=expected:
        raise ValueError('source set or content differs from parent; no new datasets')


def histogram_parts(close, *, transform: str, kernel: str, native: dict):
    if transform not in ('price_macd','rsi_macd') or kernel not in KERNELS:
        raise ValueError('policy outside frozen two-by-two factorial')
    values=close if transform=='price_macd' else native['rsi'](close,14)
    fast,slow,signal=KERNELS[kernel]
    macd=native['_ema'](values,fast)-native['_ema'](values,slow)
    return macd,native['_ema'](macd,signal)


def added_namespace(native):
    ns=dict(native)
    def price_b(c):
        m,s=histogram_parts(c,transform='price_macd',kernel='B',native=native)
        return m-s
    def rsi_a(c):
        return histogram_parts(c,transform='rsi_macd',kernel='A',native=native)
    ns['macd_hist']=price_b
    ns['_rsi_macd']=rsi_a
    return ns


def assemble(parent_rows, added_rows):
    """Two summary-compatible groups; existing rows remain byte-equivalent data."""
    groups={k:[] for k in KERNELS}
    for origin,rows in (('parent',parent_rows),('added',added_rows)):
        for r in rows:
            if r['family'] not in ('price_macd','rsi_macd'):
                raise ValueError('unrecognized input family')
            k='A' if ((r['family']=='price_macd')==(origin=='parent')) else 'B'
            groups[k].append(dict(r))
    for k,rows in groups.items():
        ids=[(r['ticker'],r['family'],r['grain'],r['signal_date']) for r in rows]
        if len(ids)!=len(set(ids)):
            raise ValueError('duplicate event within a fixed policy')
    return groups


def supported(rows):
    return len({r['month'] for r in rows})>=12 and len({r['quarter'] for r in rows})>=4


def joint_differences(groups, start, end, draws=1000, seed=20261003):
    """Bootstrap component means jointly before differencing, never CI endpoints."""
    if isinstance(draws,bool) or not isinstance(draws,int) or draws<1:
        raise ValueError('positive integer bootstrap draws required')
    allrows=[r for rs in groups.values() for r in rs if r['graded']]
    last=max([end]+[r['entry_date'] for r in allrows])
    quarters=pd.period_range(start,last,freq='Q').astype(str).tolist()
    weights=np.random.default_rng(seed).multinomial(len(quarters),np.ones(len(quarters))/len(quarters),size=draws)
    ds={};support=[]
    for kernel,family in POLICIES:
        point=0.;samples=np.zeros(draws);ok=True;cells=[]
        for grain,state,sign in (('3D','hidden_fragility',1),('3D','relief_broadening',-1),
                                 ('1D','hidden_fragility',-1),('1D','relief_broadening',1)):
            rs=[r for r in groups[kernel] if r['graded'] and
                (r['family'],r['grain'],r['regime'])==(family,grain,state)]
            enough=supported(rs)
            cells.append({'grain':grain,'regime':state,'events':len(rs),
                          'months':len({r['month'] for r in rs}),
                          'quarters':len({r['quarter'] for r in rs}),'supported':enough})
            if not enough:ok=False;continue
            point+=sign*float(np.mean([r['net_excess_pct'] for r in rs]))
            samples+=sign*pilot.block_means(rs,quarters,weights)
        valid=np.isfinite(samples)
        ok=ok and int(valid.sum())>=.95*draws
        support.append({'kernel':kernel,'input':family,'qualified':bool(ok),'cells':cells})
        if ok:ds[(kernel,family)]=(point,samples)
    definitions=[('kernel_B_minus_A_on_price',('B','price_macd'),('A','price_macd')),
                 ('kernel_B_minus_A_on_RSI',('B','rsi_macd'),('A','rsi_macd')),
                 ('RSI_minus_price_on_A',('A','rsi_macd'),('A','price_macd')),
                 ('RSI_minus_price_on_B',('B','rsi_macd'),('B','price_macd'))]
    results=[]
    for name,left,right in definitions:
        out={'contrast':name,'qualified':False}
        if left not in ds or right not in ds:
            out['reason']='insufficient_component_support'
        else:
            lp,ls=ds[left];rp,rs=ds[right];delta=ls-rs;valid=np.isfinite(delta)
            out['valid_bootstrap_draws']=int(valid.sum())
            if valid.sum()<.95*draws:out['reason']='insufficient_bootstrap_support'
            else:out.update(qualified=True,mean_difference_pp=lp-rp,
                            interval95_pp=np.quantile(delta[valid],[.025,.975]).tolist())
        results.append(out)
    return {'component_support':support,'contrasts':results,'entry_quarters':len(quarters)}


def analyze(groups):
    summaries={k:pilot.summarize(v) for k,v in groups.items()}
    cross={}
    for name,a,b in [('early',pilot.START,'2014-12-31'),('later','2015-01-01','2025-12-31'),
                     ('combined',pilot.START,pilot.END)]:
        xs={k:[r for r in v if a<=r['signal_date']<=b] for k,v in groups.items()}
        cross[name]=joint_differences(xs,a,b)
    return summaries,cross


def run(snapshot,parent_path: Path):
    before=parent_path.read_bytes()
    parent=read_parent(parent_path)
    code=Path(pilot.__file__).read_bytes()
    if hashlib.sha256(code).hexdigest()!=PILOT_CODE_SHA:
        raise ValueError('pilot dependency changed from executed parent code')
    if snapshot.ref!=pilot.SOURCE:raise ValueError('source commit mismatch')
    prices={t:pilot.normalize(snapshot.frame(f'data/yahoo/{t}.parquet',['close'])['close'])
            for t in ('SPY','RSP',*pilot.CANDIDATES)}
    real=pilot.normalize(snapshot.frame('data/fred/DFII10.parquet',['us10y_real'])['us10y_real'])
    native,anchor=pilot.native_functions(snapshot)
    require_sources(parent['source_receipts'],snapshot.receipts())
    # Parent verified identical price-support/calendar bytes. Keep the guard active
    # for the same event subperiod, without repairing or re-anchoring the calendar.
    cal=prices['SPY'].index;check=cal[(cal>=pilot.START)&(cal<=pilot.END)]
    if (np.diff(anchor.session_positions(check,'US'))!=1).any():
        raise ValueError('native calendar no longer matches the frozen event grid')
    added=pilot.event_rows(prices,pilot.features(prices,real),added_namespace(native))
    groups=assemble(parent['events'],added)
    summary,cross=analyze(groups)
    if parent_path.read_bytes()!=before:raise ValueError('parent artifact changed during read')
    retained=[r for r in groups['A'] if r['family']=='price_macd']+[
        r for r in groups['B'] if r['family']=='rsi_macd']
    expected=[r for f in ('price_macd','rsi_macd') for r in parent['events'] if r['family']==f]
    if digest(retained)!=digest(expected):raise ValueError('parent event data changed')
    return {'schema':'prophet.kernel_factorial_pilot/v1','authority':dict(pilot.AUTHORITY),
            'basis':'exploratory already-inspected saved-source panel; no independent or causal validation',
            'source_commit':snapshot.ref,'spec_commit':SPEC_COMMIT,'parent_sha256':PARENT_SHA,
            'pilot_dependency_sha256':PILOT_CODE_SHA,
            'executed_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'runtime':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__},
            'kernels':{k:list(v) for k,v in KERNELS.items()},
            'parent_events_reused':len(parent['events']),'parent_reuse_semantic_sha256':digest(retained),
            'added_events_count':len(added),'source_receipts':snapshot.receipts(),
            'results_by_kernel':summary,'joint_factorial_contrasts':cross,
            'added_events':[{**r,'kernel':'B' if r['family']=='price_macd' else 'A'} for r in added],
            'limitations':['Already-inspected historical ETF panel, not untouched OOS or production Prophet.',
                'Policy event populations differ; macro is current-vintage, not full information-time evidence.',
                'Crossed kernels are research variants, not promoted definitions in a production catalog.',
                'All quarters sampled jointly; intervals descriptive and not multiplicity adjusted.',
                'Same 2007-start amendment and unresolved historical calendar version obligation apply.',
                'No policy argmax, portfolio return, sizing, recommendation or promotion is authorized.']}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--parent',required=True);p.add_argument('--out',required=True)
    a=p.parse_args()
    from run_snapshot_audit import Snapshot
    report=run(Snapshot(a.repo,pilot.SOURCE),Path(a.parent))
    with Path(a.out).open('x') as fh:json.dump(report,fh,sort_keys=True,indent=2,allow_nan=False)
    print(json.dumps({'output':a.out,'reused':report['parent_events_reused'],'added':report['added_events_count'],
                      'authority':report['authority']}))
