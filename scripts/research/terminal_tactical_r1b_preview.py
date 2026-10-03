#!/usr/bin/env python3
"""Synthetic-only consumer of the frozen R1-B candidate/confirmation engine.

No provider, historical-input or output-file option exists. JSON/Markdown goes
only to stdout. This is executable construction evidence, never strategy results.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from engine.entry_radar.tactical_exhaustion import (
    build_prior_normalization, construct_session, match_controls,
)
from engine.session_digest import session_window_et
from lib.nyse_calendar import session_n_back

ROOT = Path(__file__).resolve().parents[2]


def synthetic_examples() -> dict:
    day = date(2026, 9, 17)
    start, _ = session_window_et(day)
    config = (ROOT/'research/species/tti_r1b/config_v4.json').read_bytes()
    prior_days = [session_n_back(day, n) for n in range(70, 0, -1)]
    q, stock = 100.0, 100.0
    q_closes, stock_closes = [], []
    for i, _prior_day in enumerate(prior_days):
        r = (0.0004 + (i % 7) * 0.0001) * (1 if i % 2 == 0 else -1)
        q *= 1.0 + r
        stock *= 1.0 + 2.0 * r
        q_closes.append(q)
        stock_closes.append(stock)
    stock_daily = pd.DataFrame({
        'high': [x + 1.0 for x in stock_closes],
        'low': [x - 1.0 for x in stock_closes],
        'close': stock_closes,
    }, index=pd.DatetimeIndex(prior_days))
    qqq_daily = pd.DataFrame({'close': q_closes}, index=pd.DatetimeIndex(prior_days))
    normalization = build_prior_normalization(
        stock_daily, qqq_daily, session=day, config_bytes=config)
    assert normalization['availability'] == 'AVAILABLE'
    common = [[100, 100.2, 99, 99.4, 100],
              [99.4, 99.5, 98.8, 99, 100],
              [99, 99.1, 98.6, 98.98, 100]]
    paths = {
        'reclaim': [[98.98, 99.1, 98.55, 98.95, 100],
                    [98.95, 99.2, 98.8, 99.1, 100],
                    [99.1, 99.5, 99, 99.4, 100]],
        'continuation': [[98.6, 98.7, 97.9, 98, 100],
                         [98, 99.1, 97.8, 98.95, 100],
                         [98.95, 99.3, 98.8, 99.2, 100]],
        'expiry': [[98.7, 98.8, 98.6, 98.7, 100]] * 3,
    }
    examples = []
    reclaim_report = None
    for name, tail in paths.items():
        rows = common + tail
        frame = pd.DataFrame(rows, index=pd.date_range(start, periods=len(rows), freq='5min'),
                             columns=['open', 'high', 'low', 'close', 'volume'])
        report = construct_session(frame, symbol='AMD', session=day,
                 prior_session=date.fromisoformat(normalization['prior_session']),
                 prior_close=normalization['prior_close'], prior_atr=normalization['prior_atr'],
                 asof=start+timedelta(minutes=30), config_bytes=config)
        examples.append({'name': name, 'construction': report})
        if name == 'reclaim':
            reclaim_report = report
    assert reclaim_report is not None
    selected = next(e for e in reclaim_report['events']
                    if e['selector'] == 'EXHAUSTION_RECLAIM')
    control_dates = ['2026-07-13','2026-07-14','2026-07-15','2026-07-16','2026-07-17',
                     '2026-07-20','2026-07-21','2026-07-22','2026-07-23','2026-07-24']
    controls = [{
        'anchor_id': f'AMD:{d}:synthetic-control',
        'candidate_at': f'{d}T13:45:00+00:00',
        'symbol': 'AMD', 'session': d, 'clock_bin': 19,
        'displacement_bucket': 0, 'displacement_atr': 0.6,
        'qqq_open_to_decision_sign': 1, 'future_family_labels_used': False,
    } for d in control_dates]
    controls += [
        dict(controls[0], anchor_id='NVDA:2026-07-27:decoy', symbol='NVDA', session='2026-07-27', candidate_at='2026-07-27T13:45:00+00:00'),
        dict(controls[0], anchor_id='AMD:2026-07-28:wrong-bin', session='2026-07-28', candidate_at='2026-07-28T13:45:00+00:00', clock_bin=20),
        dict(controls[0], anchor_id='AMD:2026-07-29:wrong-market', session='2026-07-29', candidate_at='2026-07-29T13:45:00+00:00', qqq_open_to_decision_sign=-1),
    ]
    available = match_controls(
        selected, selected_symbol='AMD', selected_session=day, selected_qqq_sign=1,
        control_census=controls, config_bytes=config)
    no_control = match_controls(
        selected, selected_symbol='AMD', selected_session=day, selected_qqq_sign=1,
        control_census=controls[:9], config_bytes=config)
    return {'evidence_class': 'SYNTHETIC_ONLY', 'market_data_read': False,
            'outcomes_computed': False, 'trial_registration_claimed': False,
            'normalization': normalization,
            'live_authority': False, 'examples': examples,
            'matching': {'selected_selector': selected['selector'],
                         'available': available, 'no_control': no_control}}


def markdown(payload: dict) -> str:
    lines = ['# R1-B v4 synthetic construction replay', '',
             '**SYNTHETIC ONLY — not market data, trading results, or live signals.**', '',
             'No edge or probability is estimated. Values are fabricated test inputs.',
             'An earliest entry is a scheduled reference time, not an available quote or fill.',
             'Times below are UTC; all session calculations use the existing exchange calendar.', '',
             '## Prior-only normalization', '',
             f"Synthetic ATR20: **{payload['normalization']['prior_atr']:.4f}** across {payload['normalization']['atr_sessions']} prior sessions. "
             f"Prior-only beta: **{payload['normalization']['beta']:.4f}** from {payload['normalization']['beta_pairs']} paired prior returns.",
             'Current-session daily values are excluded; these are synthetic engineering inputs, not market outcomes.', '']
    for example in payload['examples']:
        r = example['construction']
        lines += [f"## {example['name'].title()}", '',
                  '| Selector | Candidate | Confirmation / decision | Earliest entry | Candidate low | Episode low |',
                  '|---|---|---|---|---:|---:|']
        for e in r['events']:
            clock = lambda k: e[k][11:19]
            lines.append(f"| {e['selector']} | {clock('candidate_at')} | {clock('decision_at')} | "
                         f"{clock('entry_reference_at')} | {e['candidate_low']:.2f} | {e['episode_low']:.2f} |")
        first = r['anchors'][0]
        lines += ['', f"First candidate: **{first['race']}**. "
                  f"Frozen reclaim level: {first['reclaim_level']:.2f}; "
                  f"continuation level: {first['continuation_level']:.2f}.",
                  f"Independent control anchors: {len(r['control_census'])}. "
                  'Future family labels never select the controls.', '']
    matching = payload['matching']
    lines += ['## Matched-control demonstration', '',
              'The synthetic selected event is matched only on the frozen candidate-time covariates: same ticker, retrospective partition, 30-minute time bin, displacement bucket, QQQ open-to-decision sign, and confirmation-delay treatment; the selected date is excluded.', '',
              f"Lawful synthetic pool: **{matching['available']['matched_count']}** controls => **{matching['available']['availability']}**. "
              f"Below-floor pool: **{matching['no_control']['matched_count']}** controls => **{matching['no_control']['availability']}**; no widening fallback is used.", '',
              'Every matched control receives the same confirmation delay and five-minute processing latency as the selected event. Future family labels never select or exclude controls.', '',
              '## Still held', '',
              'Empirical TrialLedger registration, market-outcome runs, independent review, '
              'deployment and live alert integration remain separate gates. This report unlocks '
              'review of executable mechanics; it establishes no accuracy or profitability.', '']
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', choices=('json', 'markdown'), default='json')
    args = parser.parse_args()
    result = synthetic_examples()
    print(json.dumps(result, indent=2, allow_nan=False) if args.format == 'json' else markdown(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
