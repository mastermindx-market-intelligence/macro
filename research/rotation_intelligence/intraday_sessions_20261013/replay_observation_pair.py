"""Synthetic replay of the actual Basket Pulse -> JSON -> grounding path.

No provider requests, production files, outcomes, trades, alerts or ledger writes.
Nightly-only contextual attachments are isolated; the new measurement, serialization,
last-good baseline, packet reader and digest renderer are the real application code.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import build_basket_pulse as bp
from engine.neuralweb import market_packet as mp


def main() -> dict:
    first = datetime(2026, 10, 13, 15, 0, tzinfo=timezone.utc)
    second = first + timedelta(minutes=30)
    membership = {'baskets': {
        'ai_semiconductors': {'members': [{'ticker': 'SYNTH_A', 'removed': None}]},
        'us_sector_health': {'members': [{'ticker': 'SYNTH_B', 'removed': None}]},
    }}

    def quotes(prices: dict, now: datetime) -> dict:
        return {'quotes': {symbol: {
            'price': value, 'prevClose': 100.0, 'changePct': (value / 100 - 1) * 100,
            'ts': int((now - timedelta(minutes=1)).timestamp() * 1000),
            'delayMin': 1, 'currency': 'USD', 'source': 'synthetic-control',
            'basis': 'regular',
        } for symbol, value in prices.items()}}

    with TemporaryDirectory(prefix='rotation-observation-replay-') as temp:
        root = Path(temp)
        live = root / 'site' / 'live'
        live.mkdir(parents=True)
        qpath, mpath = root / 'quotes.json', root / 'membership.json'
        mpath.write_text(json.dumps(membership))
        with (patch.dict(os.environ, {'LIVE_QUOTES_PATH': str(qpath), mp._LIVE_DIR_ENV: str(live)}),
              patch.object(bp, '_cum_2d', return_value=None),
              patch.object(bp, '_load_market_drivers', return_value=None),
              patch.object(bp, '_attach_day_flow', return_value=None)):
            qpath.write_text(json.dumps(quotes({'SYNTH_A':102, 'SYNTH_B':99, 'SPY':100}, first)))
            seed = bp.build(quotes_path=qpath, membership_path=mpath, now=first, out_dir=live)
            qpath.write_text(json.dumps(quotes({'SYNTH_A':100, 'SYNTH_B':100, 'SPY':100}, second)))
            measured = bp.build(quotes_path=qpath, membership_path=mpath, now=second, out_dir=live)
            (live / 'basket_pulse.json').write_text(json.dumps(measured, allow_nan=False))
            packet = mp.build_packet(root, now=second)
            digest = mp.render_digest(packet)
            aged = bp.build(quotes_path=qpath, membership_path=mpath,
                            now=second + timedelta(minutes=30), out_dir=live)
        assert all(row['live_ew_chg_pct'] == 0 for row in measured['baskets'])
        assert len(packet['leaders']['intraday']) == 2
        assert 'since prior observation' in digest and 'not fund flows' in digest
        assert aged['mode'] == 'delayed' and aged['delay_min_median'] == 31
        assert all(row['intraday_comparison']['status'] == 'benchmark_nonadvancing'
                   for row in aged['baskets'])
        return {
            'proof_kind': 'synthetic_actual_code_path_not_production_or_market_backtest',
            'code_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
                'scripts/build_basket_pulse.py', 'engine/neuralweb/market_packet.py')},
            'seed_statuses': [r['intraday_comparison']['status'] for r in seed['baskets']],
            'measured_rows': [{'id': r['id'], 'daily_change_pct': r['live_ew_chg_pct'],
                               'intraday_comparison': r['intraday_comparison']} for r in measured['baskets']],
            'grounding_digest': digest,
            'unchanged_snapshot_later': {'mode': aged['mode'],
                'age_minutes': aged['delay_min_median'], 'source_asof': aged['source_asof'],
                'statuses': [r['intraday_comparison']['status'] for r in aged['baskets']]},
            'production_verified': False, 'financial_edge_tested': False,
        }


if __name__ == '__main__':
    print(json.dumps(main(), indent=2, sort_keys=True, allow_nan=False))
