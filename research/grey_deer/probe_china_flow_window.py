"""Synthetic read-only diagnosis; not a market result or an installed repair."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import math
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import china_internals as ci


def examine():
    source = ROOT / 'engine/china_internals.py'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    dates = pd.bdate_range(end='2026-09-21', periods=21)
    base = pd.DataFrame({'net': [-5.0] * 21}, index=dates)
    base.iloc[0, 0] = 200.0
    cases = {'complete21': base, 'internal_null': base.copy(),
             'missing_latest': base.copy(), 'one_observation': base.iloc[-1:]}
    cases['internal_null'].iloc[-5, 0] = None
    cases['missing_latest'].iloc[-1, 0] = None
    results, nonfinite = {}, []
    for name, frame in cases.items():
        original = frame.copy(deep=True)
        with patch.object(ci.store, 'read', side_effect=lambda group, key, f=frame:
                          f if key == 'southbound' else None):
            result = ci.southbound_flow()
        pd.testing.assert_frame_equal(frame, original)
        results[name] = {}
        for key in ('net', 'net_z', 'cum_20d', 'pos_days_20', 'asof'):
            value = result.get(key) if result else None
            if isinstance(value, float) and not math.isfinite(value):
                nonfinite.append(name + '.' + key)
                value = None
            results[name][key] = value
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    return {'kind': 'synthetic read-only flow-window diagnostic',
            'source_sha256': before, 'cases': results,
            'nonfinite_values_encoded_as_null': nonfinite,
            'source_and_fixture_inputs_unchanged': True,
            'product_repair': False, 'production': False, 'fresh_collection': False,
            'currency_units_qualified': False,
            'scope': 'stored-row integrity, not exchange-session completeness'}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: probe_china_flow_window.py <evidence-json>')
    evidence = examine()
    destination = Path(sys.argv[1])
    destination.write_text(json.dumps(evidence, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'cases': evidence['cases'],
        'nonfinite': evidence['nonfinite_values_encoded_as_null'],
        'product_repair': False}, allow_nan=False))
