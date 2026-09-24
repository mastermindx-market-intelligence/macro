"""Read-only comparison of the descriptive window repair with its exact predecessor."""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pandas as pd
from engine import china_participation as pc
from tests.test_china_participation import _price_context_fixture

ROOT = Path(__file__).resolve().parents[2]
BASE = 'b810694952776f58ff882e3174592555d82cdf4f'
PATH = 'engine/china_participation.py'
old_source = subprocess.check_output(['git','show',f'{BASE}:{PATH}'],cwd=ROOT,text=True)
node = next(n for n in ast.parse(old_source).body
            if isinstance(n,ast.FunctionDef) and n.name == 'price_breadth_context')
namespace = dict(pc.__dict__)
exec(compile(ast.Module(body=[node],type_ignores=[]),f'{PATH}@{BASE}','exec'),namespace)
old = namespace['price_breadth_context']

def summarize(result):
    return {key: {field: w.get(field) for field in
        ('status','start','end','eligible','median_return_pct','benchmark_return_pct','calendar_gaps')}
        for key,w in result['windows'].items()}

p,b,names = _price_context_fixture()
p.iloc[-22] = 50.; p.iloc[-21] = 100.; p.iloc[-1] = 90.
missing = b.index[-7]
kwargs = dict(members=names,asof='2026-09-18')
complete = old(p,b,**kwargs)
broken_old = old(p,b.drop(missing),**kwargs)
broken_new = pc.price_breadth_context(p,b.drop(missing),**kwargs)
assert complete == pc.price_breadth_context(p,b,**kwargs)
assert broken_old['windows']['20']['median_return_pct'] > 0
assert complete['windows']['20']['median_return_pct'] < 0
assert broken_new['windows']['20']['median_return_pct'] is None
assert broken_new['windows']['5'] == complete['windows']['5']
paths = ['data/china_search/closes.parquet','data/china/510300.SS.parquet',
         'data/china_regime/latest.json','data/risk_radar_intl/cn_forward_log.jsonl']
def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
before = {path:sha(path) for path in paths}
prices = pd.read_parquet(ROOT/paths[0])
benchmark = pd.read_parquet(ROOT/paths[1])['close']
assessment = json.loads((ROOT/paths[2]).read_text())['date']
pattern = r'(?:6[08]\d{4}\.SS|(?:00|30)\d{4}\.SZ)'
names = [n for n in prices.columns if isinstance(n,str) and re.fullmatch(pattern,n)]
kwargs = dict(members=names,asof=assessment)
actual_old = old(prices,benchmark,**kwargs)
actual_new = pc.price_breadth_context(prices,benchmark,**kwargs)
assert all(sha(path)==digest for path,digest in before.items())
# A complete-input control must stay byte-for-byte equal after JSON encoding.
json.dumps(actual_new,allow_nan=False)
receipt = {'base':BASE,'source_sha256':sha(PATH),
    'scope':'descriptive observed-date consistency; no complete exchange-calendar certification',
    'synthetic':{'removed_benchmark_date':str(missing.date()),
        'complete':summarize(complete),'old_missing_row':summarize(broken_old),
        'repaired_missing_row':summarize(broken_new)},
    'stored_input':{'assessment':assessment,'members':len(names),
        'before':summarize(actual_old),'after':summarize(actual_new),
        'exact_complete_result_equal':actual_old==actual_new,
        'trend_before':actual_old['trend'],'trend_after':actual_new['trend']},
    'protected_input_sha256':before,'inputs_unchanged':True,
    'collection':False,'risk_model_modified':False,'production':False}
output = ROOT/'research/grey_deer/CHINA_WINDOW_INTEGRITY_20260924.json'
output.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
print(json.dumps({'synthetic_complete_median':complete['windows']['20']['median_return_pct'],
    'synthetic_broken_median':broken_old['windows']['20']['median_return_pct'],
    'repaired_status':broken_new['windows']['20']['status'],
    'actual_assessment':assessment,'actual_members':len(names),
    'actual_exact_result_equal':actual_old==actual_new,'inputs_unchanged':True,
    'production':False},indent=2))
