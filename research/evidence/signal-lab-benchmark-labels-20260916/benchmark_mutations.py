"""Inject faults in child-process memory; never edit product files or market data."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
TARGET='tests/test_sf_benchmark_labels.py::'
CASES=[
 ('asset_as_benchmark','harness','_build_target','matched = benchmark.reindex(asset.index)',
  'matched = asset','test_explicit_benchmark_computes_simple_return_difference'),
 ('benchmark_row_stride','harness','_build_target','matched = benchmark.reindex(asset.index)',
  'matched = benchmark','test_benchmark_endpoints_use_asset_timestamps_not_benchmark_row_stride'),
 ('benchmark_fill','harness','_build_target','matched = benchmark.reindex(asset.index)',
  'matched = benchmark.reindex(asset.index).ffill()','test_missing_benchmark_endpoints_are_not_forward_filled_or_zeroed'),
 ('column_fallback','harness','_load_raw_price','    if strict:\n','    if False and strict:\n',
  'test_requested_column_is_not_silently_replaced_by_a_fallback[asset.csv]'),
 ('self_reference','spec','excess_return_contract',"if same and asset['column'] == comparison['column']:",
  'if False:','test_ambiguous_or_unsafe_benchmark_is_refused_by_validation_and_screen[same_reference]'),
 ('unknown_benchmark_fields','spec','excess_return_contract','set(benchmark) != {"path", "column"}',
  'not {"path", "column"}.issubset(benchmark)',
  'test_ambiguous_or_unsafe_benchmark_is_refused_by_validation_and_screen[unknown_benchmark_key]'),
 ('unversioned_receipt','spec','excess_return_contract','"version": EXCESS_TARGET_VERSION',
  '"version": "old-unversioned"','test_result_and_trial_identity_bind_benchmark_and_label_version'),
 ('nonfinite_arithmetic','harness','_build_target',
  'if any(np.isinf(s.to_numpy()).any() for s in (asset_return, benchmark_return, excess)):',
  'if False:','test_nonfinite_derived_return_is_not_a_numeric_target'),
]
CHILD=r"""
import importlib, inspect, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
case=json.loads(sys.argv[2]); module=importlib.import_module('engine.signal_foundry.'+case[1])
body=inspect.getsource(getattr(module,case[2])); assert body.count(case[3])==1, case[0]
exec(compile(body.replace(case[3],case[4]),'<in-memory-fault>','exec'),module.__dict__)
# The consumers import the contract explicitly; point those process-local references
# at the same faulty contract for a faithful negative-control deployment.
if case[1]=='spec':
 for name in ('harness','screen'):
  m=importlib.import_module('engine.signal_foundry.'+name)
  m.excess_return_contract=module.excess_return_contract
import pytest
out=Path(sys.argv[3])
sys.exit(pytest.main([sys.argv[4],'-q','--tb=short',
 '--basetemp='+str(out/'temp'),'--junitxml='+str(out/'result.xml')]))
"""

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True);args=ap.parse_args()
    out=(ROOT/args.output).resolve();private=(ROOT/'.pytest_cache').resolve()
    if not out.is_relative_to(private) or out==private or out.exists():
        ap.error('output must be a new child of this worktree pytest cache')
    paths=['engine/signal_foundry/spec.py','engine/signal_foundry/harness.py',
           'engine/signal_foundry/screen.py','tests/test_sf_benchmark_labels.py']
    hashes=lambda:{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    before=hashes();out.mkdir(parents=True);records=[]
    for case in CASES:
        dest=out/case[0];dest.mkdir()
        proc=subprocess.run([sys.executable,'-c',CHILD,str(ROOT),json.dumps(case),str(dest),TARGET+case[5]],
                            cwd=ROOT,text=True,capture_output=True,timeout=120)
        log=proc.stdout+proc.stderr;(dest/'pytest.log').write_text(log)
        xml=dest/'result.xml'; failures=errors=0
        if xml.exists():
            suites=ET.parse(xml).getroot().iter('testsuite')
            for suite in suites:
                failures+=int(suite.get('failures',0));errors+=int(suite.get('errors',0))
        record={'case':case[0],'exit_code':proc.returncode,'assertion_failures':failures,
                'errors':errors,'caught':proc.returncode==1 and failures>0 and errors==0,
                'log_sha256':hashlib.sha256(log.encode()).hexdigest()}
        records.append(record);print(json.dumps(record),flush=True)
    assert before==hashes(),'product source changed during negative controls'
    result={'scope':'isolated in-memory negative controls, not independent review',
            'source_sha256':before,'cases':records,'all_caught':all(r['caught'] for r in records)}
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['all_caught'] else 1

if __name__=='__main__':
    sys.exit(main())
