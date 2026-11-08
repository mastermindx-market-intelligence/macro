"""Synthetic, reproducible measurement controls. No market data or trading rules.

Run from repository root:
  python3 research/rotation_intelligence/intraday_sessions_20261013/measurement_controls.py

Writes only JSON to stdout. Imports the actual heatmap and session helpers.
This is a research witness, not another production detector or calendar.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import pandas as pd
from engine.sp500_heatmap import intraday_returns
from engine.session_digest import session_window_et
from lib.nyse_calendar import is_session


def log_change(start: float, end: float) -> float:
    if start <= 0 or end <= 0 or not all(map(math.isfinite, (start, end))):
        raise ValueError('positive finite prices required')
    return math.log(end / start)


def decomposition(previous: float, opening: float, current: float) -> dict:
    gap = log_change(previous, opening)
    intraday = log_change(opening, current)
    total = log_change(previous, current)
    assert math.isclose(gap + intraday, total, abs_tol=1e-12)
    gross = abs(gap) + abs(intraday)
    return {'gap_log_return': gap, 'regular_log_return': intraday,
            'total_log_return': total,
            'cancellation_share': None if gross == 0 else 1 - abs(total) / gross}


def run() -> dict:
    checks = []

    a, b = decomposition(100, 102, 100), decomposition(100, 99, 100)
    assert a['total_log_return'] == b['total_log_return'] == 0
    relative_gap = a['gap_log_return'] - b['gap_log_return']
    relative_regular = a['regular_log_return'] - b['regular_log_return']
    assert relative_gap > 0 and relative_regular < 0
    assert math.isclose(relative_gap + relative_regular, 0, abs_tol=1e-12)
    checks.append({'name': 'daily_flat_hides_opposing_session_leadership',
                   'a': a, 'b': b, 'gap_relative_log_bps': relative_gap * 10000,
                   'regular_relative_log_bps': relative_regular * 10000, 'passed': True})

    flat = decomposition(100,100,100)
    assert flat['cancellation_share'] is None
    checks.append({'name': 'no_movement_is_not_cancellation', 'result': flat, 'passed': True})

    # X is log(group / benchmark). A negative return leaves the rolling window,
    # while the arriving five-minute interval is flat: apparent acceleration only.
    x_m20, x_m15, x_m5, x_now = 0., -.02, -.02, -.02
    old15, new15 = x_m5 - x_m20, x_now - x_m15
    arriving, expiring = x_now - x_m5, x_m15 - x_m20
    assert math.isclose(new15-old15, arriving-expiring, abs_tol=1e-12)
    assert new15-old15 > 0 and arriving == 0
    checks.append({'name': 'rolling_window_expiry_is_not_new_demand',
                   'apparent_acceleration_log_bps': (new15-old15)*10000,
                   'arriving_return_log_bps': arriving*10000,
                   'expiring_return_log_bps': expiring*10000, 'passed': True})

    # No security changes its price between snapshots. Only availability changes.
    individual = {'A': .04, 'B': -.04}
    seen_old, seen_new = {'B'}, {'A'}
    naive_change = sum(individual[k] for k in seen_new)/len(seen_new) - sum(individual[k] for k in seen_old)/len(seen_old)
    common = seen_old & seen_new
    assert naive_change == .08 and not common
    checks.append({'name': 'coverage_swap_is_not_rotation',
                   'naive_change_percentage_points': naive_change*100,
                   'common_cohort_n': len(common), 'comparable_change': None, 'passed': True})

    w1, w2 = {'A': .7,'B': .3}, {'A': .7,'C': .3}
    overlap = sum(min(w1.get(k,0),w2.get(k,0)) for k in w1.keys() | w2.keys())
    effective_n = 1/sum(v*v for v in w1.values())
    assert math.isclose(overlap,.7)
    checks.append({'name': 'overlapping_baskets_are_not_independent_votes',
                   'shared_weight': overlap, 'weight_effective_member_n': effective_n,
                   'independence_established': False, 'passed': True})

    relative_bid = log_change(100,98) - log_change(100,97)
    assert relative_bid > 0
    checks.append({'name': 'relative_winner_can_still_be_falling',
                   'asset_simple_return_pct': -2., 'benchmark_simple_return_pct': -3.,
                   'relative_log_bps': relative_bid*10000,
                   'direct_fund_flow_observed': False, 'passed': True})

    for name, times, wanted in [
        ('two_hour_gap',['2026-10-12T14:00Z','2026-10-12T16:00Z'],{'X':{'2H':5.0}}),
        ('weekend_gap',['2026-10-09T19:00Z','2026-10-12T14:00Z'],{}),
        ('five_minute_rows',['2026-10-12T14:00Z','2026-10-12T14:05Z'],{'X':{'5M':5.0}}),
    ]:
        frame = pd.DataFrame({'close':[100.,105.]},index=pd.to_datetime(times))
        result = intraday_returns({'X': frame})
        assert result == wanted
        checks.append({'name': name, 'actual_engine_result': result, 'passed': True})

    summer_open, _ = session_window_et(date(2026,10,12))
    winter_open, early_close = session_window_et(date(2026,11,27))
    assert summer_open.astimezone(timezone.utc).hour == 13
    assert winter_open.astimezone(timezone.utc).hour == 14
    assert early_close.hour == 13 and not is_session(date(2026,7,3))
    checks.append({'name':'reuse_calendar_dst_early_close_and_holiday',
                   'oct_open_utc':summer_open.astimezone(timezone.utc).isoformat(),
                   'nov_open_utc':winter_open.astimezone(timezone.utc).isoformat(),
                   'nov27_close_et':early_close.isoformat(),
                   'july3_is_session':is_session(date(2026,7,3)), 'passed':True})

    eligible_end = datetime(2026,10,12,14,5,tzinfo=timezone.utc)
    seen_at = datetime(2026,10,12,14,20,tzinfo=timezone.utc)
    delay_seconds = (seen_at-eligible_end).total_seconds()
    assert delay_seconds == 900
    checks.append({'name':'five_minute_window_does_not_remove_feed_delay',
                   'window_minutes':5,'source_delay_seconds':delay_seconds,
                   'market_endpoint':eligible_end.isoformat(),'first_observed_at':seen_at.isoformat(),
                   'passed':True})

    paths = ['engine/sp500_heatmap.py','engine/session_digest.py','lib/nyse_calendar.py']
    return {'schema':'rotation_intraday_research_controls.v1',
            'data_kind':'synthetic_only','market_performance_test':False,
            'production_proof':False,'checks_passed':len(checks),
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'checks':checks}


if __name__ == '__main__':
    print(json.dumps(run(),sort_keys=True,indent=2,allow_nan=False))
