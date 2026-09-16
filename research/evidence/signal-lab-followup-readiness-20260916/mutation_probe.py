"""Fault-injection replay in isolated Python processes; never edits product source."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    ("calendar_creates_result", "engine.experiment_followup",
     'review_due = days is not None and days <= 0 and not closed',
     'review_due = days is not None and days <= 0 and not closed\n    result = result or review_due',
     'test_due_seed_does_not_manufacture_results'),
    ("legacy_ready_trusted", "engine.experiment_followup",
     'result = current and reader == "observed" and record.get("result_ready") is True',
     'result = record.get("ready") is True or record.get("result_ready") is True',
     'test_admin_does_not_trust_legacy_combined_ready'),
    ("closed_date_reopened", "engine.experiment_followup",
     'review_due = days is not None and days <= 0 and not closed',
     'review_due = days is not None and days <= 0',
     'test_concluded_records_do_not_reopen_on_a_calendar_date'),
    ("attention_double_counted", "engine.experiment_followup",
     '"attention_count": sum(e.get("attention_required") is True for e in records)',
     '"attention_count": sum((e.get("result_ready") is True) + (e.get("review_due") is True) for e in records)',
     'test_admin_summary_counts_attention_once_and_exposes_both_reasons'),
    ("qledger_truthy_string", "engine.experiments_registry",
     'ready = best.get("ready") is True', 'ready = bool(best.get("ready"))',
     'test_qledger_reader_does_not_convert_truthy_strings_to_readiness'),
    ("reader_truthy_string", "engine.experiments_registry",
     'result_ready=reader_status == "observed" and hook_out.get("ready") is True',
     'result_ready=reader_status == "observed" and bool(hook_out.get("ready"))',
     'test_reader_readiness_must_be_a_boolean'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    allowed = (ROOT / '.pytest_cache').resolve()
    if not output.is_relative_to(allowed) or output == allowed or output.exists():
        parser.error('output must be a new child of this worktree pytest cache')
    output.mkdir(parents=True)
    paths = ['engine/experiment_followup.py','engine/experiments_registry.py','admin/experiments.py']
    original_hashes = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    results = []
    for name, module, old, new, test in CASES:
        runner = r"""
import importlib,json,sys,pathlib
root,module,old,new,test,temp=json.loads(sys.argv[1])
sys.path.insert(0,root)
m=importlib.import_module(module)
source=pathlib.Path(m.__file__).read_text()
assert source.count(old)==1, (module,old,source.count(old))
exec(compile(source.replace(old,new),m.__file__,'exec'),m.__dict__)
import pytest
raise SystemExit(pytest.main(['tests/test_experiment_followup.py','-k',test,
 '--basetemp='+temp,'-q','--tb=short']))
"""
        params = [str(ROOT), module, old, new.replace('\\n','\n'), test, str(output/name)]
        process = subprocess.run([sys.executable,'-c',runner,json.dumps(params)],cwd=ROOT,
                                 text=True,capture_output=True,timeout=45)
        log = process.stdout + process.stderr
        (output/(name+'.log')).write_text(log)
        count = re.search(r'(\d+) failed',log)
        killed = process.returncode == 1 and count is not None and 'ERROR at setup' not in log
        result = {'fault':name,'test':test,'exit_code':process.returncode,
                  'caught':killed,'failed_tests':int(count.group(1)) if count else None,
                  'log_sha256':hashlib.sha256(log.encode()).hexdigest()}
        results.append(result)
        print(name,'CAUGHT',killed,'RC',process.returncode,flush=True)
    final_hashes = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    assert final_hashes == original_hashes, 'Fault injection modified source bytes'
    report = {'source_sha256':original_hashes,'source_unchanged':True,'cases':results,
              'all_caught':all(row['caught'] for row in results),'production_proven':False}
    (output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print('MUTATION_RECEIPT',output/'receipt.json')
    return 0 if report['all_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
