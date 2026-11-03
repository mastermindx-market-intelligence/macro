"""Read-only acceptance of Press radar receipt wording over historical fixtures.

python -B probe.py REPO REVIEWED_SOURCE_MANIFEST
No producer, writer, staging, publication, package installation or network calls.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
expected = json.loads(Path(sys.argv[2]).read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert {p: sha(root / p) for p in expected} == expected, 'reviewed source manifest drift'
sys.path.insert(0, str(root))
from engine.press import desk_planner as P


def head():
    return subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()


def snapshot():
    paths = [root / p for _, p in P._ENGINE_ARTIFACTS]
    paths += [root / 'data/press/published.jsonl', root / 'config/press.yml']
    paths += list((root / 'data/press/staging').glob('*.json'))
    return {str(p.relative_to(root)): sha(p) for p in paths if p.is_file()}


before_head, before = head(), snapshot()
row = {'asof': '2026-10-12', 'state': 'caution', 'dominant_scare': 'rates',
       'top_score': 70.3, 'can_force': False, 'authority_tier': 'advisory',
       'drawdown_prob': {'h21': 0.19, 'h10': 0.1, 'h5': 0.042,
           'calibration_evidence': {'schema': 'risk_radar_probability_evidence.v1',
               'evidence_class': 'reconstructed_historical', 'precision_grade': False,
               'target': {'depth': 0.05, 'horizons': [5, 10, 21],
                          'price_path': 'native SPY closing observations'},
               'horizons': {'h21': {'matched': True, 'displayed_probability': 0.19}}}}}

def read(value):
    original = copy.deepcopy(value)
    fact, = P._risk_radar_facts([value], 'data/risk_radar/forward_log.jsonl')
    # json preserves NaN spelling, making this an identity check for that control too.
    assert json.dumps(value, sort_keys=True) == json.dumps(original, sort_keys=True)
    return fact


controls = []
fact = read(row)
assert all(s in fact['text'] for s in ['SPY closing prices', 'at least 5%', '21-session',
    '0.19', 'reconstructed historical', 'not independent episodes', 'not precision-grade', 'advisory'])
assert fact['values'] == ['70.3', '0.19', '5'] and P._press_safe(fact['text'])
assert fact['dated'] == row['asof'] and fact['tier'] == 'first_party'
controls.append('target-calibration-and-advisory-context')

for raw in [None, [], {}, {'h21': 0.19}, {'calibration_evidence': None}]:
    bad = copy.deepcopy(row); bad['drawdown_prob'] = raw
    fact = read(bad)
    assert 'probability' not in fact['text'] and fact['values'] == ['70.3']
controls.append('legacy-and-malformed-evidence-omitted')

for field, value in [('schema', 'unknown'), ('evidence_class', 'unknown'), ('precision_grade', True)]:
    bad = copy.deepcopy(row); bad['drawdown_prob']['calibration_evidence'][field] = value
    assert read(bad)['values'] == ['70.3']
controls.append('unrecognized-calibration-contract-omitted')

for field, value in [('depth', 0.1), ('price_path', 'QQQ intraday lows'), ('horizons', [5, 10])]:
    bad = copy.deepcopy(row); bad['drawdown_prob']['calibration_evidence']['target'][field] = value
    assert read(bad)['values'] == ['70.3']
controls.append('different-loss-target-omitted')

for value in [True, float('nan'), float('inf'), -0.1, 1.1, 10**1000]:
    bad = copy.deepcopy(row); bad['drawdown_prob']['h21'] = value
    assert read(bad)['values'] == ['70.3']
controls.append('nonprobability-values-omitted')

for field, value in [('matched', False), ('displayed_probability', 0.2), ('displayed_probability', True)]:
    bad = copy.deepcopy(row); bad['drawdown_prob']['calibration_evidence']['horizons']['h21'][field] = value
    assert read(bad)['values'] == ['70.3']
controls.append('unmatched-evidence-cell-omitted')

zero = copy.deepcopy(row); zero['drawdown_prob']['h21'] = 0
zero['drawdown_prob']['calibration_evidence']['horizons']['h21']['displayed_probability'] = 0
assert 'probability 0' in read(zero)['text']
controls.append('explicit-zero-is-valid')

assert before == snapshot() and before_head == head()
assert {p: sha(root / p) for p in expected} == expected
print(json.dumps({'probe_passed': True, 'controls': controls, 'head': before_head,
    'execution_location': 'installed_vps' if root == Path('/opt/macro') else 'local_source',
    'checked_source_sha256': expected, 'real_provider_calls': 0,
    'production_inputs_unchanged': True, 'production_staging_writes': 0,
    'public_writes': 0, 'd14_credit': 0,
    'scope': 'Historical receipt-consumer fixtures; no model, story or publication approval'}, indent=2))
