"""Qualify the reviewed P2 dependency through the existing China consumer.

Read-only ledger replay and in-memory real-builder observation. The inherited
render-write defect is intercepted, not fixed or authorized by this diagnostic.
"""
from pathlib import Path
from unittest.mock import patch
import copy
import hashlib
import json
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import market_state, risk_radar_intl_audit as audit
from research.grey_deer.probe_china_alert_independence import examine
from research.grey_deer.probe_china_render_effects import observe

PICKUP = 'f23d67e1524953afad92b564f2a4e862022c7df9'
P2 = '5d6ae511c7b82b05e175ba7ea36e2fc5003b6502'

def digest(path):
    p = ROOT / path
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def forbidden_write(*args, **kwargs):
    raise AssertionError('read-only integration attempted a ledger write')

def main(import_path, target):
    imported = json.loads(Path(import_path).read_text())
    before = {p: digest(p) for p in imported['protected_paths']}
    assert before == imported['protected_paths']
    legacy = types.ModuleType('frozen_parent_intl_audit')
    source = subprocess.check_output(['git', 'show', PICKUP + ':engine/risk_radar_intl_audit.py'], cwd=ROOT)
    exec(compile(source, 'risk_radar_intl_audit.py@' + PICKUP, 'exec'), legacy.__dict__)
    stable = ('n_graded', 'n_alerts', 'base_rate_dd5_h21', 'alert_precision',
              'alert_hit_rate', 'force_lift', 'by_state', 'realized_odds',
              'recent_mistakes', 'asof_range')
    keys = ('n_total_graded_rows', 'n_loud_rows', 'n_row_hits',
            'n_independent_episodes', 'n_loud_episodes', 'n_episode_hits',
            'n_unmatured_loud_episodes', 'can_force', 'authority_contract')
    markets = {}
    with patch.object(audit, '_write', side_effect=forbidden_write), \
         patch.object(audit, '_log_can_force_governance', side_effect=forbidden_write):
        for market in ('cn', 'hk', 'ca'):
            old = legacy.scorecard(market, root=str(ROOT), log_governance=False)
            new = audit.scorecard(market, root=str(ROOT), log_governance=False)
            assert all(old.get(k) == new.get(k) for k in stable), market
            assert not new['can_force'] or old['can_force'], market
            markets[market] = {k: new.get(k) for k in keys}
            markets[market]['legacy_diagnostics_unchanged'] = True
        density = examine()
    dense = density['synthetic']['dense_daily_alerts']
    assert dense['can_force'] is False and dense['n_loud_episodes'] == 1
    assert density['synthetic']['daily_alert_calls'] == 40
    consumer = []
    original_snapshot = market_state.market_state_snapshot
    def snapshot(latest, *args, **kwargs):
        incoming = copy.deepcopy((latest.get('risk_radar') or {}).get('forward_log') or {})
        result = original_snapshot(latest, *args, **kwargs)
        emitted = copy.deepcopy(((result or {}).get('radar') or {}).get('forward_log') or {})
        assert incoming.get('authority_contract') == 'risk_radar_intl.authority.v2'
        assert all(emitted.get(k) == incoming.get(k) for k in keys)
        consumer.append({'incoming': {k: incoming.get(k) for k in keys},
                         'emitted': {k: emitted.get(k) for k in keys},
                         'market_state_score': (result or {}).get('score'),
                         'binding': ((result or {}).get('radar') or {}).get('binding'),
                         'risk_score': ((result or {}).get('radar') or {}).get('top_score')})
        return result
    with patch.object(market_state, 'market_state_snapshot', side_effect=snapshot):
        builder = observe('RENDER_NO_DRIP', '')
    assert len(consumer) == 1
    assert {p: digest(p) for p in before} == before
    for p in ('engine/risk_radar_intl_audit.py', 'engine/risk_radar_intl_evidence.py'):
        assert (ROOT / p).read_bytes() == subprocess.check_output(['git', 'show', P2 + ':' + p], cwd=ROOT)
    receipt = {'source_base': PICKUP, 'import_head': P2, 'markets': markets,
        'density': {k: dense.get(k) for k in keys},
        'synthetic_daily_alerts': 40, 'synthetic_declines': 1,
        'synthetic_disjoint_alert_windows': density['synthetic']['maximum_disjoint_21_session_alert_windows'],
        'consumer': consumer, 'builder': builder, 'protected_paths': before,
        'product_source_exact_p2': True, 'ledger_writes': 0,
        'production': False, 'browser_proof': False, 'fresh_collection': False,
        'render_write_guards_fixed': False, 'forecast_or_sizing_validated': False}
    Path(target).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'markets': markets, 'density': receipt['density'],
                      'consumer': consumer, 'protected_count': len(before), 'production': False}, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: probe_china_episode_integration.py IMPORT_RECEIPT OUTPUT_RECEIPT')
    main(sys.argv[1], sys.argv[2])
