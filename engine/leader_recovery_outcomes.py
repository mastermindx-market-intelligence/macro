"""Finite-horizon research outcomes, never inputs to the live recovery projection.

Forward returns cover all observed valid decision states. Barrier first-passage
labels have a SEPARATE risk-set gate: dropping already-breached failed repairs
from the return sample would systematically remove the losing comparison arm.
No finite window proves that an issuer will never regain leadership.
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
    result = {'decision_on': cut.isoformat(), 'horizon_sessions': horizon,
              'status': 'UNAVAILABLE', 'first_event': None, 'first_event_on': None,
              'event_status': 'NOT_AT_RISK', 'event_reason': None,
              'return': None, 'excess_return': None, 'relative_return': None,
              'mae_close': None, 'mfe_close': None, 'observed_sessions': 0,
              'reason': None, 'label_only': True}
    if descriptor.get('state') == 'UNAVAILABLE':
        return {**result, 'reason': 'decision_evidence_unavailable'}
    try:
        c, b = _source(close, through), _source(benchmark, through)
    except (TypeError, ValueError, OverflowError):
        return {**result, 'reason': 'invalid_outcome_source'}
    entry, bench_entry = c.get(cut), b.get(cut)
    if not _finite(entry) or not _finite(bench_entry):
        return {**result, 'reason': 'missing_decision_close'}
    ep = descriptor.get('episode') or {}
    target = ep.get('price_high_water', ep.get('peak_price'))
    floor = ep.get('repair_floor') or ep.get('trough_price')
    at_risk = _finite(target) and _finite(floor) and floor < entry < target
    if at_risk:
        result['event_status'] = 'OBSERVING'
    else:
        result['event_reason'] = 'decision_outside_unresolved_price_interval'
    start = days.index(cut)
    future = days[start + 1:start + 1 + horizon]
    observed = [d for d in future if d <= through]
    values = []
    for day in observed:
        price, bench = c.get(day), b.get(day)
        if not _finite(price) or not _finite(bench):
            if at_risk and result['first_event'] is None:
                result['event_status'] = 'DATA_GAP'
            return {**result, 'status': 'DATA_GAP', 'reason': 'missing_completed_session',
                    'observed_sessions': len(values)}
        values.append(price)
        if at_risk and result['first_event'] is None:
            event = ('FLOOR_BROKEN_FIRST' if price < floor else
                     'PRICE_RECOVERED_FIRST' if price >= target else None)
            if event:
                result.update(first_event=event, first_event_on=day.isoformat(),
                              event_status='OBSERVED')
    result['observed_sessions'] = len(observed)
    if len(observed) < horizon:
        if at_risk and result['first_event'] is None:
            result['event_status'] = 'RIGHT_CENSORED'
        return {**result, 'status': 'RIGHT_CENSORED', 'reason': 'horizon_not_observed'}
    end = observed[-1]
    stock_return = c[end] / entry - 1
    benchmark_return = b[end] / bench_entry - 1
    result.update(status='COMPLETE', reason=None,
                  excess_return=_number(stock_return - benchmark_return),
                  relative_return=_number((1 + stock_return) / (1 + benchmark_return) - 1),
                  mae_close=_number(min([0.] + [p / entry - 1 for p in values])),
                  mfe_close=_number(max([0.] + [p / entry - 1 for p in values])))
    result['return'] = _number(stock_return)
    if at_risk and result['first_event'] is None:
        result.update(first_event='NO_RESOLUTION_BY_HORIZON', event_status='OBSERVED')
    return result
