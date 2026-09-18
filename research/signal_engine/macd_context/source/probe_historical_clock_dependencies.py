"""Read-only clock-dependency experiment; not a replay or a production clock owner.
Runs two exact archived functions against unchanged retained inputs at four declared
metadata dates. No board build, outcomes, provider calls, or canonical-store writes.
"""
import ast
import builtins
import datetime as dt
import hashlib
import json
import logging
import subprocess
from pathlib import Path
from types import SimpleNamespace
import pandas as pd

VINTAGE = 'ff745b1ab54256b0188688cc5815e6675e4edef5'
ROOT = Path('/Users/chriswong/Documents/Cluade/macro-main')
STUDY = Path('/Volumes/Mastermind/Mastermind/artifacts/macd-context-first-look-20260915-c3/cycle_extension_v2')
TREE = STUDY / 'owner_replay_control_20260717_r1' / ('vintage-' + VINTAGE[:12])
DATES = ('2026-07-15', '2026-07-17', '2026-09-15', '2026-09-16')
NAMES = {'_next_monthly_opex_days', 'current_risk_overlay'}


def source(path):
    return subprocess.run(['git', '-C', str(ROOT), 'show', VINTAGE + ':' + path],
                          capture_output=True, check=True, timeout=90).stdout


def main():
    builder = source('scripts/build_stock_library.py')
    catalyst = source('engine/catalyst_tone.py')
    functions = [n for n in ast.parse(builder).body if isinstance(n, ast.FunctionDef) and n.name in NAMES]
    assert {n.name for n in functions} == NAMES
    assignments = [n for n in ast.parse(catalyst).body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == '_FOMC_MEETINGS' for t in n.targets)]
    assert len(assignments) == 1
    calendar = ast.literal_eval(assignments[0].value)
    code = compile(ast.Module(body=functions, type_ignores=[]), 'archived-build-stock-library', 'exec')
    paths = ('data/yahoo/_VIX.parquet', 'data/regime/latest.json')
    input_hashes = {p: hashlib.sha256((TREE / p).read_bytes()).hexdigest() for p in paths}
    rows = []
    for day in DATES:
        class FixedDate(dt.date):
            @classmethod
            def today(cls):
                return cls.fromisoformat(day)
        def imports(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'datetime':
                return SimpleNamespace(date=FixedDate, timedelta=dt.timedelta)
            if name == 'engine.catalyst_tone':
                return SimpleNamespace(_FOMC_MEETINGS=calendar)
            return builtins.__import__(name, globals, locals, fromlist, level)
        ns = {'__builtins__': {**vars(builtins), '__import__': imports},
              'pd': pd, 'json': json, 'config': SimpleNamespace(data_dir=lambda: TREE / 'data'),
              'log': logging.getLogger('archived-clock-probe')}
        exec(code, ns)
        rows.append({'calendar_date': day, 'opex_days': ns['_next_monthly_opex_days'](),
                     'risk_overlay': ns['current_risk_overlay']()})
    assert input_hashes == {p: hashlib.sha256((TREE / p).read_bytes()).hexdigest() for p in paths}
    receipt = {'kind': 'EXACT_ARCHIVED_FUNCTION_CLOCK_SENSITIVITY', 'vintage_sha': VINTAGE,
               'builder_sha256': hashlib.sha256(builder).hexdigest(),
               'catalyst_sha256': hashlib.sha256(catalyst).hexdigest(),
               'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'input_hashes': input_hashes, 'inputs_unchanged': True, 'rows': rows,
               'board_rebuilt': False, 'outcomes_computed': False,
               'runtime_clock_certified': False,
               'limitations': 'Function-level sensitivity only. Parent log dates lack timezone; the two September dates are diagnostics, not selected replay clocks.'}
    output = STUDY / 'replay_input_repair_20260916_r2/clock_sensitivity.json'
    with output.open('x') as f:
        json.dump(receipt, f, indent=2)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
