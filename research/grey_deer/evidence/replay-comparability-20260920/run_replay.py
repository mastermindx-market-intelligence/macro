"""Read-only current-calibration replay; reconstructed history, not a validation trial."""
from pathlib import Path
import hashlib, json, subprocess, sys, types
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from lib import config, store
from engine import risk_radar as rr, risk_radar_backtest as bt
assert config.data_dir().resolve() == (ROOT / 'data').resolve()
OUT = Path(__file__).resolve().parent
BASE = '78ef3b7b9d50deb02ac06ec7e655b7e892bfd40c'
original = types.ModuleType('original_replay')
raw = subprocess.check_output(['git', 'show', BASE + ':engine/risk_radar_backtest.py'], cwd=ROOT)
exec(compile(raw, '<original-replay>', 'exec'), original.__dict__)
inputs = {}
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
read = store.read
def observed_read(group, name):
    p = store._path(group, name)
    before = digest(p)
    result = read(group, name)
    assert digest(p) == before
    inputs[str(p.relative_to(ROOT))] = before
    return result
with patch.object(store, 'read', side_effect=observed_read):
    calibration = rr._calib(root=ROOT)
    sigs = rr.leading_signals()
    subs = rr.subscore_series(sigs, calibration)
    assert not sigs.empty and not subs.empty, 'Historical inputs unavailable'
    results = []
    with patch.object(rr, 'leading_signals', return_value=sigs), \
         patch.object(rr, 'subscore_series', return_value=subs):
        for H in (5, 10, 21):
            for label, lo in [('full', None), ('since2020', '2020-01-01')]:
                before = original.state_accuracy(calibration, H=H, dd=.05, lo=lo)
                after = bt.state_accuracy(calibration, H=H, dd=.05, lo=lo)
                results.append({'window': label, 'H': H, 'before': before, 'after': after})
                print(label, H, json.dumps(after), flush=True)
for relative, expected in inputs.items():
    assert digest(ROOT / relative) == expected, 'Source changed during replay: ' + relative
receipt = {
    'kind': 'reconstructed_current_calibration_replay',
    'protocol_commit': 'a3f85ff7b88c9361956f3f618915fea8f1b18201',
    'base': BASE, 'calibration': calibration,
    'radar_source_sha256': digest(ROOT / 'engine/risk_radar.py'),
    'replay_source_sha256': digest(ROOT / 'engine/risk_radar_backtest.py'),
    'signal_rows': len(sigs), 'signal_columns': list(sigs.columns),
    'first_date': str(sigs.index.min()), 'last_date': str(sigs.index.max()),
    'read_inputs': inputs, 'missing_inputs': [p for p, sha in inputs.items() if sha is None],
    'results': results, 'live_model_changed': False, 'publication_timing_verified': False,
    'out_of_sample_validation': False,
    'limits': ['Current code and current calibration reconstructed over stored history.',
               'Overlapping daily outcomes are not independent episodes.',
               'No probability, calibration, policy or ledger modification.']}
(OUT / 'real-input-replay.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('REAL_REPLAY_COMPLETE', len(results), 'cells;', len(inputs), 'input paths; no source mutation')
