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
# Whole-dictionary equality failed on five identified builder additions, not
# changed saved values. Independently reproduce those exact additions; everything
# saved, and every other addition, remains checked recursively without tolerance.
from research.grey_deer.china_render_projection_check import verify_projection
from engine.china_inputs import build_features
expected = {}
cond = saved.get('conditions') or {}
ch = cond.get('charts') or {}
if ch:
    expected['conditions.roro_html'] = build_china._ilx(ch.get('roro'), 'var(--info)', kind='bars', height=170, baseline=0, aria_en='Risk-on/off chart')
    expected['conditions.recession_html'] = build_china._ilx(ch.get('recession'), 'var(--warn)', height=150, aria_en='Slowdown gauge chart')
    expected['conditions.drawdown_html'] = build_china._ilx(ch.get('drawdown'), 'var(--down)', height=150, aria_en='Drawdown gauge chart')
    if saved.get('fear_euphoria') is not None and ch.get('fear_euphoria'):
        bands = [dict(hi=100, lo=70, tint='color-mix(in srgb, var(--warn) 15%, transparent)', label_en='Euphoria', label_zh='亢奋', pos='top'),
                 dict(hi=30, lo=0, tint='color-mix(in srgb, var(--info) 15%, transparent)', label_en='Fear', label_zh='恐惧', pos='bottom')]
        expected['fear_euphoria.chart_html'] = build_china._ilx(ch['fear_euphoria'], '#c08bd8', height=160, bands=bands, value_fmt='{:,.0f}', aria_en='Fear and euphoria gauge chart')
f = build_features()
assert str(f.index[-1].date()) == saved['date'], 'extra breadth must use the same assessment session'
b = f['pct_above_200'].dropna() if 'pct_above_200' in f else None
if b is not None and len(b) >= 60:
    tail = b.tail(252 * 5)
    px = f['510300.SS'].dropna() if '510300.SS' in f else None
    expected['conditions.breadth'] = dict(above200_pctile=float((tail <= tail.iloc[-1]).mean()),
        div=bool(px is not None and len(px)>21 and len(b)>21 and b.iloc[-1]<b.iloc[-22] and px.iloc[-1]>px.iloc[-22]))
projection_proof = verify_projection(saved, vm['latest'], expected_additions=expected)
assert all(sha(p) == digest for p, digest in before.items()), 'post-qualification input drift'

receipt = {'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
           'assessment_date': saved['date'], 'raw_page_sha256': sha(page),
           'raw_page_bytes': page.stat().st_size, 'engine_run_calls': len(run_calls),
           'preserved_input_sha256': before, 'saved_projection_check': projection_proof,
           'risk_score': (vm.get('risk_reading') or {}).get('radar', {}).get('top_score'),
           'copy_present': True, 'fresh_collection': False,
           'browser_proof': False, 'production': False}
(OUT / 'actual-builder-proof.json').write_text(json.dumps(receipt,indent=2)+'\n')
(OUT / 'actual-builder-page.html').write_bytes(page.read_bytes())
print(json.dumps(receipt,indent=2))
