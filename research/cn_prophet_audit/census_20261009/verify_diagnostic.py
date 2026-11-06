#!/usr/bin/env python3
"""Focused invariants for research arithmetic; synthetic values are unit checks only."""
import ast
from pathlib import Path
import numpy as np
import pandas as pd

source=ast.parse(Path(__file__).with_name('autopsy.py').read_text())
main=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='main')
selected=[n for n in main.body if isinstance(n,ast.FunctionDef) and n.name in ('cc_row','top6')]
cal=pd.DatetimeIndex(['2026-01-01','2026-01-02','2026-01-05'])
env={'pd':pd,'np':np,'cal':cal,'bclose':pd.Series([100.,100.,100.],index=cal)}
exec(compile(ast.Module(body=selected,type_ignores=[]),'audited_pure_functions','exec'),env)
prices=pd.DataFrame({'close':[100.,100.,101.],'high':[101.,101.,102.],'low':[99.,99.,100.],'volume':[1.,1.,1.]},index=cal)
r=env['cc_row'](prices,'TEST','2026-01-01',1,{})
assert r['entry_date']=='2026-01-02' and r['exit_date']=='2026-01-05'
assert abs(r['pnl_cc']-1)<1e-9 and r['mae_close']==0
assert env['cc_row'](prices.drop(cal[1]),'TEST','2026-01-01',1,{})['status']=='missing_exact_session'
assert env['cc_row'](prices,'TEST','2026-01-01',3,{})['status']=='immature'
pool=pd.DataFrame({'ticker':[f'T{i}' for i in range(8)],'sector':['A','B']*4,'prophet_score':list(range(100,92,-1)),'status':['missing_exact_session']+['observed']*7})
frozen=env['top6'](pool,'prophet_score');post=env['top6'](pool[pool.status=='observed'],'prophet_score')
assert set(frozen.ticker)=={f'T{i}' for i in range(6)}
assert set(post.ticker)=={f'T{i}' for i in range(1,7)}
assert not bool((frozen.status=='observed').all())
print('PASS: market-session horizon, non-positive close-MAE, missing-session refusal, age gate, and frozen selection without replacement.')
