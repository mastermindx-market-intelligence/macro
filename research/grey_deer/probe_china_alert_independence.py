"""Read-only dependence diagnostic of the incumbent audit; no policy or ledger writes.
Synthetic prices test the evidence gate, not market performance or forecast accuracy.
"""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import risk_radar_intl_audit as audit


def examine():
    path = ROOT / 'data/risk_radar_intl/cn_forward_log.jsonl'
    ledger_bytes = path.read_bytes()
    rows = [json.loads(line) for line in ledger_bytes.decode().splitlines() if line.strip()]
    def no_write(*args, **kwargs):
        raise AssertionError('diagnostic attempted a persistent write')
    def evaluate(sample):
        with patch.object(audit, '_path', return_value=path), \
             patch.object(audit, '_read', return_value=sample), \
             patch.object(audit, '_write', side_effect=no_write), \
             patch.object(audit, '_log_can_force_governance', side_effect=no_write):
            return audit.scorecard('cn', log_governance=False)
    actual = evaluate(rows)
    end = pd.Timestamp.now(tz='UTC').tz_localize(None).normalize()
    dates = pd.bdate_range(end=end, periods=151)
    # One uninterrupted decline. Early quiet windows never reach the decline.
    px = pd.Series([100.0] * 90 + [100.0 * .99 ** i for i in range(61)], index=dates)
    def entry(i, alert):
        row = dict(asof=str(dates[i].date()), market='cn', alert=alert,
                   state='risk-off' if alert else 'calm', dominant_scare='synthetic')
        row['graded'] = audit._grade_entry(row, px)
        assert row['graded'] is not None
        return row
    quiet = [entry(i, False) for i in range(60)]
    alerts = [entry(i, True) for i in range(90, 130)]
    assert not any(r['graded']['any_dd5_within_h21'] for r in quiet)
    assert all(r['graded']['any_dd5_within_h21'] for r in alerts)
    one = evaluate(quiet + alerts[:1])
    dense = evaluate(quiet + alerts)
    nonoverlap = []; previous_end = -1
    for i in range(90, 130):
        if i + 1 > previous_end:
            nonoverlap.append(i); previous_end = i + 21
    actual_alerts = [r for r in rows if r.get('alert') and r.get('graded')]
    result = {
        'kind': 'read-only validation-dependence diagnostic; no market backtest',
        'ledger_sha256': hashlib.sha256(ledger_bytes).hexdigest(),
        'actual_recorded': {k: actual.get(k) for k in ('n_graded', 'n_alerts',
            'alert_precision', 'can_force', 'grant_reason', 'asof_range')},
        'actual_graded_alert_dates': [r['asof'] for r in actual_alerts],
        'synthetic': {'single_continuous_decline': True, 'quiet_calls': 60,
            'daily_alert_calls': 40, 'distinct_decline_paths': 1,
            'maximum_disjoint_21_session_alert_windows': len(nonoverlap),
            'one_alert': one, 'dense_daily_alerts': dense},
        'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in ('engine/risk_radar_intl_audit.py', 'engine/neuralweb/constitution.py')},
        'source_or_policy_changed': False, 'forecast_validated': False,
        'production': False,
    }
    assert path.read_bytes() == ledger_bytes, 'ledger changed during read-only diagnostic'
    return result


if __name__ == '__main__':
    result = examine()
    target = Path(sys.argv[1])
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'actual': result['actual_recorded'],
        'synthetic_one_alert_granted': result['synthetic']['one_alert']['can_force'],
        'synthetic_40_correlated_alerts_granted': result['synthetic']['dense_daily_alerts']['can_force'],
        'disjoint_windows': result['synthetic']['maximum_disjoint_21_session_alert_windows'],
        'ledger_unchanged': True, 'production': False}))
