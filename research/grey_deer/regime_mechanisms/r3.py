"""Pure research reconstruction adapters. No new regime model or live authority.

A passed time contract is not source-vintage qualification or predictive skill.
The endpoint callback is owned by the existing regime producer.
"""
from __future__ import annotations
import hashlib
import json
from typing import Callable
import numpy as np
import pandas as pd

QUADS=('Q1','Q2','Q3','Q4')
SCORE_COLS=['growth_score','inflation_score','quad']


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def archive_asof(frame: pd.DataFrame, series: str, decision_date: str) -> dict:
    """Latest valid value per period strictly before a date-only decision.

    No cross-period initial-print stitching. Only the selected knowledge enters
    its digest; a full-archive digest belongs in run provenance, not this ID.
    """
    required={'series','period','realtime_start','realtime_end','value','source_output_type'}
    if not required.issubset(frame): raise ValueError('missing archive columns')
    day=pd.Timestamp(decision_date)
    if day.tz is not None or day!=day.normalize(): raise ValueError('date-only decision required')
    d=frame.loc[frame['series'].eq(series)].copy()
    d['realtime_start']=pd.to_datetime(d['realtime_start'],errors='raise')
    d=d.loc[d.realtime_start<day].copy()
    empty={'status':'unavailable','decision_date':day.date().isoformat(),'series':series,
           'levels':{},'knowledge_sha256':None,'last_publication_date':None}
    if d.empty:return empty
    d['period']=pd.to_datetime(d['period'],errors='raise')
    if d[['period','realtime_start']].isna().any().any():raise ValueError('invalid dates')
    if d.duplicated(['period','realtime_start']).any():raise ValueError('duplicate vintage/period')
    if not d.source_output_type.eq(2).all():raise ValueError('full vintages required')
    if (d.period>d.realtime_start).any():raise ValueError('future observation period')
    if any(isinstance(v,(bool,np.bool_)) for v in d.value):raise ValueError('boolean value')
    d['value']=pd.to_numeric(d['value'],errors='raise')
    if not (np.isfinite(d.value)&d.value.gt(0)).all():raise ValueError('invalid macro value')
    # ISO date strings handle the ALFRED open-ended 9999-12-31 sentinel.
    from datetime import date
    ends=d.realtime_end.map(lambda v: date.fromisoformat(str(v)[:10]).isoformat())
    starts=d.realtime_start.dt.strftime('%Y-%m-%d')
    if (ends<starts).any():raise ValueError('invalid validity interval')
    cutoff=(day-pd.Timedelta(days=1)).date().isoformat()
    d=d.assign(_end=ends).sort_values(['period','realtime_start']).drop_duplicates('period',keep='last')
    d=d.loc[d._end>=cutoff]
    if d.empty:return empty
    selected=[{'period':p.date().isoformat(),'released':r.date().isoformat(),'value':float(v)}
              for p,r,v in zip(d.period,d.realtime_start,d.value)]
    return {'status':'ok','decision_date':day.date().isoformat(),'series':series,
            'levels':{r['period']:r['value'] for r in selected},
            'knowledge_sha256':digest({'series':series,'selected':selected}),
            'last_publication_date':d.realtime_start.max().date().isoformat()}


def endpoint_at(frame: pd.DataFrame, decision_at: str, endpoint: Callable) -> dict:
    """Invoke only the source-native endpoint on the knowledge available then.

    Rows may contain later revisions, selected by their available_at timestamps.
    Never publishes callback history. This does not certify the caller's clocks.
    """
    t=pd.Timestamp(decision_at)
    if t.tz is None:raise ValueError('timezone required for decision')
    t=t.tz_convert('UTC')
    if not set(SCORE_COLS+['available_at']).issubset(frame):raise ValueError('missing score fields')
    d=frame.copy(deep=True)
    av=pd.to_datetime(d.available_at,errors='raise')
    if av.dt.tz is None:raise ValueError('timezone required for availability')
    d['available_at']=av.dt.tz_convert('UTC')
    if d.available_at.isna().any():raise ValueError('missing availability')
    d=d.loc[d.available_at<=t].copy()
    base={'schema':'regime_replay.research.v1','decision_at':t.isoformat(),
          'status':'unavailable','score_asof':None,'fit_cutoff':None,
          'knowledge_sha256':None,'probabilities':None,
          'input_qualification':'NOT_ESTABLISHED',
          'authority':{'rank':False,'size':False,'gate':False,'execute':False}}
    if d.empty:return base
    idx=pd.DatetimeIndex(d.index)
    if idx.tz is not None or idx.isna().any() or not (idx==idx.normalize()).all():raise ValueError('daily score dates required')
    d['_score_date']=idx
    if (d._score_date.dt.date>d.available_at.dt.date).any():raise ValueError('score after publication')
    if d.duplicated(['_score_date','available_at']).any():raise ValueError('duplicate score revision')
    d=d.sort_values(['_score_date','available_at']).drop_duplicates('_score_date',keep='last').set_index('_score_date')
    # Source-native missing rows remain missing; unavailable emissions are not zero.
    for c in SCORE_COLS[:2]:d[c]=pd.to_numeric(d[c],errors='raise')
    if np.isinf(d[SCORE_COLS[:2]].to_numpy()).any():raise ValueError('infinite score')
    if not d.quad.dropna().isin(QUADS).all():raise ValueError('invalid quad')
    records=[]
    for day,row in d.iterrows():
        records.append({'date':day.date().isoformat(),'available_at':row.available_at.isoformat(),
                        **{c:(None if pd.isna(row[c]) else float(row[c])) for c in SCORE_COLS[:2]},
                        'quad':None if pd.isna(row.quad) else str(row.quad)})
    base['knowledge_sha256']=digest(records)
    valid=d[SCORE_COLS].dropna()
    if valid.empty:return base
    base['score_asof']=valid.index[-1].date().isoformat();base['fit_cutoff']=base['score_asof']
    r=endpoint(d[SCORE_COLS].copy(deep=True))
    if r is None:return base
    if r.get('asof')!=base['score_asof']:raise ValueError('endpoint asof mismatch')
    p=r.get('regime_probs_filtered')
    if not isinstance(p,dict) or set(p)!=set(QUADS):raise ValueError('invalid probability keys')
    if any(isinstance(p[k],(bool,np.bool_)) for k in QUADS):raise ValueError('boolean probability')
    a=np.asarray([p[k] for k in QUADS],float)
    if not np.isfinite(a).all() or (a<0).any() or (a>1).any() or abs(a.sum()-1)>.001:raise ValueError('invalid probability values')
    base.update(status='ok',probabilities={k:float(p[k]) for k in QUADS})
    return base


def future_path(series: pd.Series, horizon: int=21, threshold: float=.05) -> pd.DataFrame:
    """Full-horizon close-loss target; no current-loss credit or missing-as-safe."""
    if not isinstance(horizon,int) or horizon<1 or not 0<threshold<1:raise ValueError('invalid horizon/threshold')
    s=series.copy().astype(float)
    if s.index.has_duplicates or not s.index.is_monotonic_increasing:raise ValueError('ordered unique calendar required')
    s=s.where(np.isfinite(s)&s.gt(0))
    future=pd.concat([s.shift(-i) for i in range(1,horizon+1)],axis=1)
    valid=s.notna()&future.notna().all(axis=1)
    low=(future.min(axis=1,skipna=False)/s-1).where(valid)
    last=(s.shift(-horizon)/s-1).where(valid)
    return pd.DataFrame({'future_min_return':low,'terminal_return':last,
                         'event':low.le(-threshold).astype(float).where(valid),
                         'current_drawdown':s/s.rolling(252,min_periods=252).max()-1})


def cross_table(broad: pd.Series, recipient: pd.Series) -> dict:
    d=pd.concat([broad.rename('b'),recipient.rename('r')],axis=1).dropna()
    if not d.isin([0.,1.]).all().all():raise ValueError('binary outcomes required')
    return {'n':len(d),'both':int((d.b.eq(1)&d.r.eq(1)).sum()),
            'broad_only':int((d.b.eq(1)&d.r.eq(0)).sum()),
            'recipient_only':int((d.b.eq(0)&d.r.eq(1)).sum()),
            'neither':int((d.b.eq(0)&d.r.eq(0)).sum())}
