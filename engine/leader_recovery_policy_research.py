"""Exploratory common-endpoint timing references, not live trade signals.

All policies observe the same horizon, act at the NEXT session close, and retain
no-entry cash results. Fractional unit returns are research, not position sizing.
"""
from __future__ import annotations
from datetime import date
import math
from typing import Mapping
from engine.leader_recovery import RecoverySpec

POLICIES = ('immediate', 'wait_5', 'wait_10', 'ma50_only', 'repair', 'reignition')


def compare_at_landmark(prices: Mapping[date, float], benchmark: Mapping[date, float],
                        observations: Mapping[date, dict], *, sessions: list[date],
                        landmark: date, horizon: int, available_through: date,
                        round_trip_cost_bps: float = 20.0,
                        spec: RecoverySpec | None = None) -> list[dict]:
    spec = spec or RecoverySpec()
    if type(horizon) is not int or horizon < 2:
        raise ValueError('invalid_horizon')
    if type(round_trip_cost_bps) not in (int,float) or not math.isfinite(round_trip_cost_bps) or round_trip_cost_bps < 0:
        raise ValueError('invalid_cost')
    if sessions != sorted(set(sessions)) or landmark not in sessions:
        raise ValueError('invalid_calendar')
    start = sessions.index(landmark)
    end = start + horizon
    seed = observations.get(landmark) or {}
    episode = seed.get('episode') or {}
    if seed.get('state') == 'UNAVAILABLE' or not episode.get('opened_on'):
        raise ValueError('invalid_landmark_observation')
    common = {'landmark': landmark.isoformat(), 'horizon_sessions': horizon,
              'round_trip_cost_bps': round_trip_cost_bps, 'return_basis': 'next_close_reference',
              'definition_sha256': spec.digest,
              'episode_opened_on': episode['opened_on'], 'entry_on': None,
              'net_return': None, 'excess_common_endpoint': None,
              'mae_close': None, 'mfe_close': None, 'held_sessions': None,
              'status': 'RIGHT_CENSORED'}
    if end >= len(sessions) or sessions[end] > available_through:
        return [{**common, 'policy': p} for p in POLICIES]
    for day in sessions[start:end + 1]:
        values = (prices.get(day), benchmark.get(day))
        if any(v is None or not math.isfinite(v) or v <= 0 for v in values):
            return [{**common, 'policy': p, 'status': 'DATA_GAP'} for p in POLICIES]
        if day not in observations or observations[day].get('state') == 'UNAVAILABLE':
            return [{**common, 'policy': p, 'status': 'OBSERVATION_GAP'} for p in POLICIES]
    endpoint = sessions[end]
    common['endpoint'] = endpoint.isoformat()
    bench_return = benchmark[endpoint] / benchmark[sessions[start + 1]] - 1
    signals = {'immediate': start, 'wait_5': start + 5, 'wait_10': start + 10}
    for index in range(start, end):
        row = observations[sessions[index]]
        ep = row.get('episode') or {}
        if ep.get('opened_on') != episode['opened_on']:
            continue
        fast = row.get('ma_fast')
        if fast is not None and prices[sessions[index]] > fast:
            signals.setdefault('ma50_only', index)
        rebound = ep.get('rebound_from_low')
        if rebound is not None and rebound >= spec.rebound_fraction and row.get('fast_confirmation_sessions', 0) >= spec.confirm_sessions:
            signals.setdefault('repair', index)
            if row.get('slow_confirmation_sessions', 0) >= spec.confirm_sessions:
                signals.setdefault('reignition', index)
    results = []
    for policy in POLICIES:
        signal_index = signals.get(policy)
        entry_index = signal_index + 1 if signal_index is not None else None
        result = {**common, 'policy': policy, 'status': 'COMPLETE'}
        if entry_index is None or entry_index >= end:
            result.update(entry_status='NO_ENTRY', net_return=0.,
                          excess_common_endpoint=-bench_return,
                          mae_close=0., mfe_close=0., held_sessions=0)
        else:
            entry_day = sessions[entry_index]
            entry_price = prices[entry_day]
            marks = [prices[d] / entry_price - 1 for d in sessions[entry_index:end + 1]]
            net = prices[endpoint] / entry_price - 1 - round_trip_cost_bps / 10000
            result.update(entry_status='ENTERED', signal_on=sessions[signal_index].isoformat(),
                          entry_on=entry_day.isoformat(), net_return=net,
                          excess_common_endpoint=net - bench_return,
                          mae_close=min(0., min(marks)), mfe_close=max(0., max(marks)),
                          held_sessions=end - entry_index)
        results.append(result)
    return results
