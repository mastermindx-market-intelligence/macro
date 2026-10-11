"""Finite-horizon research labels for recovery observations, never live inputs.

Outcomes consume a descriptor frozen at the decision cut. A failure means a
close breached THAT attempt's floor, not that the issuer can never recover.
"""
from __future__ import annotations
from datetime import date
import pandas as pd
from engine.leader_recovery import _date, _source, _finite, _number


def label_recovery_outcome(close: pd.Series, benchmark: pd.Series, *,
                           descriptor: dict, sessions: list[date], horizon: int,
                           available_through: date) -> dict:
    if type(horizon) is not int or horizon < 1:
        raise ValueError('horizon_must_be_positive_integer')
    cut, through = _date(descriptor['as_of']), _date(available_through)
    days = [_date(d) for d in sessions]
    if days != sorted(set(days)) or cut not in days or through < cut:
        raise ValueError('invalid_outcome_calendar')
    initial = {'decision_on': cut.isoformat(), 'horizon_sessions': horizon,
               'status': 'UNAVAILABLE', 'first_event': None, 'first_event_on': None,
               'return': None, 'excess_return': None, 'relative_return': None,
               'mae_close': None, 'mfe_close': None, 'observed_sessions': 0,
               'reason': None, 'label_only': True}
    ep = descriptor.get('episode') or {}
    target = ep.get('price_high_water', ep.get('peak_price'))
    floor = ep.get('repair_floor') or ep.get('trough_price')
    if descriptor.get('state')=='UNAVAILABLE' or not _finite(target) or not _finite(floor):
        return {**initial,'reason':'missing_frozen_reference'}
    c,b = _source(close,through), _source(benchmark,through)
    entry, bench_entry = c.get(cut), b.get(cut)
    if not _finite(entry) or not _finite(bench_entry) or not floor < entry < target:
        return {**initial,'reason':'decision_outside_unresolved_price_interval'}
    start=days.index(cut)
    future=days[start+1:start+1+horizon]
    observed=[d for d in future if d<=through]
    vals=[]
    for day in observed:
        cp,bp=c.get(day),b.get(day)
        if not _finite(cp) or not _finite(bp):
            return {**initial,'status':'DATA_GAP','reason':'missing_completed_session',
                    'observed_sessions':len(vals)}
        vals.append(cp)
        if initial['first_event'] is None:
            kind=('FLOOR_BROKEN_FIRST' if cp < floor else
                  'PRICE_RECOVERED_FIRST' if cp >= target else None)
            if kind:
                initial['first_event']=kind
                initial['first_event_on']=day.isoformat()
    initial['observed_sessions']=len(observed)
    if len(observed)<horizon:
        return {**initial,'status':'RIGHT_CENSORED','reason':'horizon_not_observed'}
    end=observed[-1]
    ret=c[end]/entry-1
    benchret=b[end]/bench_entry-1
    initial.update(status='COMPLETE',reason=None,
                   return_=_number(ret),excess_return=_number(ret-benchret),
                   relative_return=_number((1+ret)/(1+benchret)-1),
                   mae_close=_number(min([0.]+[p/entry-1 for p in vals])),
                   mfe_close=_number(max([0.]+[p/entry-1 for p in vals])))
    initial['return']=initial.pop('return_')
    if initial['first_event'] is None:
        initial['first_event']='NO_RESOLUTION_BY_HORIZON'
    return initial
