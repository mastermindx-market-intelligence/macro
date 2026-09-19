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

from engine.entry_radar.tactical_exhaustion import construct_session
from engine.session_digest import session_window_et
from lib.nyse_calendar import session_n_back

ROOT = Path(__file__).resolve().parents[2]


def synthetic_examples() -> dict:
    day = date(2026, 9, 17)
    start, _ = session_window_et(day)
    config = (ROOT/'research/species/tti_r1b/config_v4.json').read_bytes()
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
    for name, tail in paths.items():
        rows = common + tail
        frame = pd.DataFrame(rows, index=pd.date_range(start, periods=len(rows), freq='5min'),
                             columns=['open', 'high', 'low', 'close', 'volume'])
        report = construct_session(frame, symbol='AMD', session=day,
                 prior_session=session_n_back(day, 1), prior_close=100.0,
                 prior_atr=2.0, asof=start+timedelta(minutes=30), config_bytes=config)
        examples.append({'name': name, 'construction': report})
    return {'evidence_class': 'SYNTHETIC_ONLY', 'market_data_read': False,
            'outcomes_computed': False, 'trial_registration_claimed': False,
            'live_authority': False, 'examples': examples}


def markdown(payload: dict) -> str:
    lines = ['# R1-B v4 synthetic construction replay', '',
             '**SYNTHETIC ONLY — not market data, trading results, or live signals.**', '',
             'No edge or probability is estimated. Values are fabricated test inputs.',
             'An earliest entry is a scheduled reference time, not an available quote or fill.',
             'Times below are UTC; all session calculations use the existing exchange calendar.', '']
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
    lines += ['## Still held', '',
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
