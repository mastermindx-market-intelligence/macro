"""Exercise the actual page-only builder without publishing a new assessment.

Run from the repository root with the two incumbent page-only flags and
CHINA_VM_DUMP=1. This proof writes normal generated page outputs; run in an owned
worktree and reconcile those exact outputs afterwards. No browser or collection.
"""
import hashlib
import json
import os
import pickle
import subprocess
from pathlib import Path
from engine import china_run
from scripts import build_china

ROOT = Path.cwd()
OUT = Path(os.environ['CHINA_RENDER_PROOF_DIR'])
OUT.mkdir(parents=True, exist_ok=True)
assert os.environ.get('RENDER_NO_DRIP') == '1'
assert os.environ.get('CHINA_FAST_RENDER') == '1'
assert os.environ.get('CHINA_VM_DUMP') == '1'
paths = ['data/china_regime/latest.json', 'data/china_regime/regime_history.parquet',
         'data/china_market_state/score_log.parquet',
         'data/risk_radar_intl/cn_forward_log.jsonl',
         'data/yahoo/HG_F.parquet', 'data/yahoo/GC_F.parquet',
         'data/yahoo/CL_F.parquet', 'data/yahoo/DX-Y.NYB.parquet']
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
before = {p: sha(p) for p in paths}
saved = json.loads(Path(paths[0]).read_text())
page = ROOT / 'site/china.html'
previous_page = sha(page)
run_calls = []
original_run = china_run.run
def forbidden_run():
    run_calls.append(True)
    raise AssertionError('page-only builder invoked analytical publication')
china_run.run = forbidden_run
try:
    code = build_china.main()
finally:
    china_run.run = original_run
assert code == 0 and not run_calls
assert all(sha(p) == digest for p, digest in before.items()), 'assessment/ledger/input drift'
html = page.read_text()
assert sha(page) != previous_page, 'builder must emit the new copy, not keep an old page'
assert 'positive regime prior' in html and '周期先验' in html
assert 'measured best contrarian bottom' not in html and '~70% hit' not in html
assert 'Economic slowdown' in html and 'Historical stress' in html
assert 'cnx-participation' in html and 'cnx-index-members' in html
with open(ROOT / 'data/_dev_china_vm.pkl', 'rb') as handle:
    vm = pickle.load(handle)  # this invocation's local debug output only
fields = ['conditions', 'fear_euphoria', 'market_drivers']
assert all(vm['latest'][k] == saved[k] for k in fields)
receipt = {'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
           'assessment_date': saved['date'], 'raw_page_sha256': sha(page),
           'raw_page_bytes': page.stat().st_size, 'engine_run_calls': len(run_calls),
           'preserved_input_sha256': before, 'saved_fields_equal_in_view_model': fields,
           'risk_score': (vm.get('risk_reading') or {}).get('radar', {}).get('top_score'),
           'copy_present': True, 'fresh_collection': False,
           'browser_proof': False, 'production': False}
(OUT / 'actual-builder-proof.json').write_text(json.dumps(receipt,indent=2)+'\n')
(OUT / 'actual-builder-page.html').write_bytes(page.read_bytes())
print(json.dumps(receipt,indent=2))
