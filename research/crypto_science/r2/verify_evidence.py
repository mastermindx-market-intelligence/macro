"""Verify the exact paired replay receipt and unchanged inputs, not forecasting skill."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import config
from research.crypto_science.r2_replay import metric
HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    result = json.loads((HERE/'paired_replay.json').read_text())
    assert result['candidate_head'] == 'a5a2d98cbb192f02113fc957fba28f40f37deff2'
    assert result['baseline_ref'] == '060c6bab567a7e45e6aad73393ade9aff9a55016'
    assert sha(HERE/'paired_replay.json') == 'd220c97cee4c2d4386d597c128ea3d8bfa8d18ef205b62461e837c41bb2f6494'
    assert result['inputs_gates_source_unchanged'] is True
    data = Path(config.data_dir())
    for name,digest in result['input_sha256'].items():
        p=data/name
        assert (sha(p) if p.exists() else None) == digest, name
    for name,digest in result['protected_gate_sha256'].items():
        assert sha(data/name) == digest, name
    for name,digest in result['source_sha256'].items():
        assert sha(ROOT/name) == digest, name
    assert result['frame_rows']==4393 and result['frame_columns']==197
    assert len(result['changed_columns'])==9
    assert all(r['column']=='bottom_pressure' or r['column'].startswith('alloc_') for r in result['changed_columns'])
    assert all(r['different_rows']==0 and r['availability_changed']==0 for r in result['stored_baseline_parity'])
    rows=pd.read_csv(HERE/'prefix_all_dates.csv')
    assert len(rows)==4393 and rows.date.nunique()==4393
    assert int((rows.old_delta.abs()>1e-12).sum())==54
    assert (rows.new_delta.abs()<=1e-12).all()
    assert int((rows.prefix_observations<200).sum())==199
    assert result['latest']['old_final_exposure_pct']==result['latest']['new_final_exposure_pct']==100
    assert len(result['diagnostic_metrics'])==96
    for leg in ['d2','d3','u1']:
        old=result['old_impulse_verdict']['legs'][leg]
        new=result['new_impulse_verdict']['legs'][leg]
        assert old['status']==new['status'] and new['pass'] is False
    # Preserve initial R1 research bytes, including its documented correction.
    names=['r1_audit.json','r1_audit_initial.json','r1_prefix_cutoffs.csv','r1_prefix_cutoffs_initial.csv','r1_label_boundary_exploratory.json']
    for name in names:
        p=HERE.parent/name
        original=subprocess.check_output(['git','show',f"{result['baseline_ref']}:research/crypto_science/{name}"],cwd=ROOT)
        assert p.read_bytes()==original, name
    # Independent arithmetic oracle for lag and turnover accounting.
    close=pd.Series([100.,100.,110.,99.],index=pd.date_range('2026-01-01',periods=4))
    alloc=pd.Series([0.,1.,1.,0.],index=close.index)
    assert np.isclose(metric(close,alloc,close.index[0],0)['terminal_equity_multiple'],.99)
    assert np.isclose(metric(close,alloc,close.index[0],100)['terminal_equity_multiple'],.981)
    assert np.isclose(metric(close,alloc,close.index[0],0)['max_drawdown_pct'],-10)
    alloc.iloc[1]=np.nan
    assert metric(close,alloc,close.index[0],0)['available'] is False
    print('R2_EVIDENCE_VERIFIED: 4393 cutoffs; 0 candidate repaint; 55 input,18 gate,9 source hashes unchanged; R1 retained.')
    print('DIAGNOSTIC ONLY: no live-gate write, no independent review, no out-of-sample or production acceptance.')


if __name__=='__main__': main()
