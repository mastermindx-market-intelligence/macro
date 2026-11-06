"""Reproduce pinned QQQ-minus-SPY label arithmetic without running a signal.

Extracts only two committed price files into a new private test-only Git directory.
Never edits original data, invokes a provider, grades a signal or writes trial history.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
DEFAULT_INPUT_COMMIT='3daf739affa12a43a6b3a0feb3b4c57154587756'
INPUTS=('data/yahoo/QQQ.parquet','data/yahoo/SPY.parquet')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-commit',default=DEFAULT_INPUT_COMMIT)
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',args.input_commit):
        ap.error('input-commit must be an immutable full commit SHA')
    out=(ROOT/args.output).resolve();private=(ROOT/'.pytest_cache').resolve()
    if not out.is_relative_to(private) or out==private or out.exists():
        ap.error('output must be a new child of this worktree pytest cache')
    # Resolve before creating any output; a missing source fails closed.
    subprocess.run(['git','-C',str(ROOT),'cat-file','-e',args.input_commit+'^{commit}'],
                   check=True,capture_output=True,timeout=30)
    (out/'data/yahoo').mkdir(parents=True)
    inputs={}
    for path in INPUTS:
        data=subprocess.check_output(['git','-C',str(ROOT),'show',args.input_commit+':'+path],timeout=30)
        (out/path).write_bytes(data)
        inputs[path]=hashlib.sha256(data).hexdigest()
    for command in (['init'],['add','data']):
        subprocess.run(['git','-C',str(out),*command],check=True,capture_output=True,timeout=15)
    sys.path.insert(0,str(ROOT))
    import numpy as np
    import pandas as pd
    from engine.signal_foundry.harness import _build_target
    from engine.signal_foundry.spec import excess_return_contract,TargetContractError
    asset=pd.read_parquet(out/INPUTS[0])['close_price']
    benchmark=pd.read_parquet(out/INPUTS[1])['close_price']
    records=[]
    for horizon in (5,10,21,63,126):
        spec={'target':{'path':INPUTS[0],'column':'close_price','kind':'excess_return',
                       'horizon_d':horizon,'benchmark':{'path':INPUTS[1],'column':'close_price'}},
              'baseline':'buy_and_hold'}
        actual=_build_target(spec,out,asset.index)
        manual={}
        for i in range(len(asset)-horizon):
            start,end=asset.index[i],asset.index[i+horizon]
            if start in benchmark.index and end in benchmark.index and pd.notna(benchmark.loc[start]) and pd.notna(benchmark.loc[end]):
                manual[start]=float(asset.iloc[i+horizon])/float(asset.iloc[i])-float(benchmark.loc[end])/float(benchmark.loc[start])
        expected=pd.Series(manual)
        assert actual.index.equals(expected.index) and len(actual)>0
        error=float(np.max(np.abs(actual.to_numpy()-expected.to_numpy())))
        assert error<1e-12
        records.append({'horizon_bars':horizon,'label_count':len(actual),
                        'max_abs_scalar_parity_error':error,'last_label_start':str(actual.index[-1])})
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',args.input_commit+':data/signal_foundry/candidates.jsonl'],timeout=30)
    legacy=[]
    for line in raw.decode().splitlines():
        spec=json.loads(line)
        if spec.get('target',{}).get('kind')=='excess_return' and 'benchmark' not in spec['target']:
            try:
                excess_return_contract(spec)
            except TargetContractError as error:
                legacy.append({'id':spec['id'],'refused':True,'reason':str(error)})
            else:
                raise AssertionError('ambiguous legacy target admitted')
    assert inputs=={p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in INPUTS}
    receipt={'source_input_commit':args.input_commit,'input_sha256':inputs,
             'declared_column':'close_price','observed_input_end':str(min(asset.index.max(),benchmark.index.max())),
             'label_checks':records,'legacy_ambiguities':legacy,'inputs_unchanged':True,
             'market_signal_evaluated':False,'trial_ledger_written':False,
             'qualification':'Stored price-return arithmetic, not total-return/PIT certification, alpha or production acceptance.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
