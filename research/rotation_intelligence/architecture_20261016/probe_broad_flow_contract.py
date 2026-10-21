"""Exact-source, synthetic-only witness. No provider calls, product imports or writes."""
from __future__ import annotations
import argparse, ast, builtins, datetime as dt, hashlib, json, logging, types
from pathlib import Path
import pandas as pd

EXPECTED_BLOB = '8832230059f46b3b7db04f0977d49e346f511711'
SYMBOLS = ('SPY','QQQ','IWM','RSP','DIA')

def run(source: Path) -> dict:
    raw=source.read_bytes()
    blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    if blob != EXPECTED_BLOB: raise ValueError('Source changed; re-review required')
    tree=ast.parse(raw.decode())
    nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BroadFlowAdapter']
    if len(nodes)!=1: raise ValueError('Exact class not found')
    code=compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec')
    cases=[]
    for name,today,nav in [('missing_nav',dt.date(2026,10,16),None),('stale_source_clock',dt.date(2026,10,16),100.0),('weekend',dt.date(2026,10,18),100.0)]:
        fixture={'navPrice':nav,'regularMarketPrice':103.0,'totalAssets':10000000.0,
                 'sharesOutstanding':100000,'regularMarketTime':int(dt.datetime(2026,10,14,20,tzinfo=dt.timezone.utc).timestamp())}
        calls=[]
        class Ticker:
            def __init__(self,symbol): calls.append(symbol)
            @property
            def info(self): return dict(fixture)
        fake=types.SimpleNamespace(Ticker=Ticker)
        def importer(name,globals=None,locals=None,fromlist=(),level=0):
            if name=='yfinance': return fake
            raise RuntimeError('Undeclared import in extracted code: '+name)
        class Clock:
            @staticmethod
            def today(): return today
        safe_builtins=dict(vars(builtins));safe_builtins['__import__']=importer
        env={'__builtins__':safe_builtins,'__name__':'synthetic_broad_flow_probe','Adapter':type('Adapter',(),{}),
             'pd':pd,'date':Clock,'BROAD_ETF_TICKERS':SYMBOLS,'log':logging.getLogger('synthetic_probe')}
        exec(code,env)
        frames=env['BroadFlowAdapter']().fetch()
        frame=frames['SPY']; row={'case':name,'retrieval_date':today.isoformat(),
            'provider_market_timestamp_utc':'2026-10-14T20:00:00+00:00','official_nav_supplied':nav is not None,
            'stored_date':str(frame.index[0].date()),'stored_nav':float(frame.iloc[0]['nav']),
            'columns':list(frame.columns),'mock_calls':len(calls),'real_provider_calls':0}
        assert len(calls)==5 and set(calls)==set(SYMBOLS)
        if name=='missing_nav': assert row['stored_nav']==103.0 and not row['official_nav_supplied']
        if name=='stale_source_clock': assert row['stored_date']=='2026-10-16'
        if name=='weekend': assert frame.index[0].weekday()==6
        row['source_behavior_reproduced']=True
        cases.append(row)
    return {'scope':'source_contract_failure_witnesses_not_fix_or_production_incidence',
        'source_git_blob':blob,'source_sha256':hashlib.sha256(raw).hexdigest(),
        'source_commit':'3ab3382af89242c7b7fe8c65360bd883a7dd3504','path':'collectors/sponsors.py',
        'class_lines':[nodes[0].lineno,nodes[0].end_lineno],
        'cases':cases,'market_outcomes_read':False,'network_calls':0,'product_module_imports':0,
        'desired_investment_input_contract_satisfied':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path)
    print(json.dumps(run(p.parse_args().source),indent=2,sort_keys=True,allow_nan=False))
