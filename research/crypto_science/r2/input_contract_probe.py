"""Bounded read-only follow-up to R1's funding coverage discrepancy.
No coalescing, rescaling, provider call, data write or live gate update.
"""
import hashlib
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import config


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    data = Path(config.data_dir())
    path = data / 'bgeo/funding_rate.parquet'
    source = ROOT / 'engine/btc_inputs.py'
    before = digest(path)
    frame = pd.read_parquet(path)
    rows = []
    for name in frame.columns:
        valid = frame[name].dropna()
        rows.append({'column': name, 'nonnull': len(valid),
                     'first': str(valid.index.min()) if len(valid) else None,
                     'last': str(valid.index.max()) if len(valid) else None})
    assert before == digest(path), 'Input changed during probe'
    source_text = source.read_text()
    assert 's = df[col] if col else df.iloc[:, 0]' in source_text
    assert '"funding": _col("bgeo", "funding_rate")' in source_text
    gate_path = data / 'vector/impulse_legs_gate.json'
    gate = json.loads(gate_path.read_text()) if gate_path.exists() else None
    result = {'classification':'EXPLORATORY_SOURCE_CONTRACT_FINDING_NOT_A_PATCH',
              'source_sha256':digest(source),'input_sha256':before,
              'input_unchanged':True,'stored_rows':len(frame),
              'column_order':list(frame.columns),'column_coverage':rows,
              'observed_selection':'btc_inputs._col with no explicit field chooses first physical column',
              'finding':'Only 80 recent source rows enter funding via current selection; the older 1089-row field is not selected. The derived 83-row coverage includes a 3-day forward-fill.',
              'unresolved':['Old/new funding units, exchange coverage, funding interval and revision identity are not proven equivalent.',
                            'Do not concatenate fields merely to maximize apparent backtest length.'],
              'stored_impulse_gate':({'asof':gate.get('asof'),'statuses':{k:v.get('status') for k,v in gate.get('legs',{}).items()},'sha256':digest(gate_path)} if gate else None),
              'gate_effect':'Read only; no validate/main/write_gate invocation in this probe.'}
    target=Path(__file__).with_name('input_contract_findings.json')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
